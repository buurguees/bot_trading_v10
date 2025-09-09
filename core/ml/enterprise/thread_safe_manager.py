# Ruta: core/ml/enterprise/thread_safe_manager.py
"""
models/enterprise/thread_safe_manager.py - Thread-Safe Model Management System
Sistema de gestión de modelos thread-safe para entornos de producción enterprise
"""

import threading
import asyncio
import time
import logging
from typing import Dict, Any, Optional, ContextManager, Union, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import weakref
import gc
from pathlib import Path
import pickle
import hashlib
import json

logger = logging.getLogger(__name__)

class ReadWriteLock:
    """Reader-writer lock implementation for concurrent access"""
    
    def __init__(self):
        self._read_ready = threading.Condition(threading.RLock())
        self._readers = 0
        self._writers = 0
        self._write_requests = 0
        
    @contextmanager
    def reader(self):
        """Context manager for read access"""
        self._read_ready.acquire()
        try:
            while self._writers > 0 or self._write_requests > 0:
                self._read_ready.wait()
            self._readers += 1
        finally:
            self._read_ready.release()
            
        try:
            yield
        finally:
            self._read_ready.acquire()
            try:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notifyAll()
            finally:
                self._read_ready.release()
    
    @contextmanager
    def writer(self):
        """Context manager for write access"""
        self._read_ready.acquire()
        try:
            self._write_requests += 1
            while self._readers > 0 or self._writers > 0:
                self._read_ready.wait()
            self._write_requests -= 1
            self._writers += 1
        finally:
            self._read_ready.release()
            
        try:
            yield
        finally:
            self._read_ready.acquire()
            try:
                self._writers -= 1
                self._read_ready.notifyAll()
            finally:
                self._read_ready.release()

@dataclass
class ModelMetadata:
    """Metadata for model tracking and management"""
    model_id: str
    version: str
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    memory_usage_mb: float = 0.0
    file_size_mb: float = 0.0
    checksum: str = ""
    tags: List[str] = field(default_factory=list)
    status: str = "active"  # active, deprecated, archived, error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'model_id': self.model_id,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'performance_metrics': self.performance_metrics,
            'memory_usage_mb': self.memory_usage_mb,
            'file_size_mb': self.file_size_mb,
            'checksum': self.checksum,
            'tags': self.tags,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary"""
        return cls(
            model_id=data['model_id'],
            version=data['version'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            access_count=data['access_count'],
            performance_metrics=data['performance_metrics'],
            memory_usage_mb=data['memory_usage_mb'],
            file_size_mb=data['file_size_mb'],
            checksum=data['checksum'],
            tags=data['tags'],
            status=data['status']
        )

@dataclass
class AccessMetrics:
    """Metrics for model access tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0
    last_access: Optional[datetime] = None
    error_rate: float = 0.0
    
    def update_success(self, latency_ms: float):
        """Update metrics for successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.last_access = datetime.now()
        self._update_average_latency(latency_ms)
        self._update_error_rate()
    
    def update_failure(self, latency_ms: float):
        """Update metrics for failed request"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_access = datetime.now()
        self._update_average_latency(latency_ms)
        self._update_error_rate()
    
    def _update_average_latency(self, latency_ms: float):
        """Update rolling average latency"""
        if self.total_requests == 1:
            self.average_latency_ms = latency_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.average_latency_ms = (alpha * latency_ms + 
                                     (1 - alpha) * self.average_latency_ms)
    
    def _update_error_rate(self):
        """Update error rate"""
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests

class ModelCache:
    """LRU cache for models with memory management"""
    
    def __init__(self, max_size_mb: float = 1000.0, max_models: int = 10):
        self.max_size_mb = max_size_mb
        self.max_models = max_models
        self.current_size_mb = 0.0
        self._access_order = deque()
        self._models = {}
        self._lock = threading.RLock()
    
    def get(self, model_id: str) -> Optional[Any]:
        """Get model from cache"""
        with self._lock:
            if model_id in self._models:
                # Move to end (most recently used)
                self._access_order.remove(model_id)
                self._access_order.append(model_id)
                return self._models[model_id]
            return None
    
    def put(self, model_id: str, model: Any, size_mb: float) -> bool:
        """Add model to cache"""
        with self._lock:
            # Remove if already exists
            if model_id in self._models:
                self._remove(model_id)
            
            # Check if we need to evict
            while (self.current_size_mb + size_mb > self.max_size_mb or 
                   len(self._models) >= self.max_models):
                if not self._evict_lru():
                    return False  # Cannot fit even after eviction
            
            # Add model
            self._models[model_id] = model
            self._access_order.append(model_id)
            self.current_size_mb += size_mb
            return True
    
    def _remove(self, model_id: str):
        """Remove model from cache"""
        if model_id in self._models:
            del self._models[model_id]
            self._access_order.remove(model_id)
            # Note: size_mb should be tracked separately for accurate removal
    
    def _evict_lru(self) -> bool:
        """Evict least recently used model"""
        if not self._access_order:
            return False
        
        lru_model_id = self._access_order.popleft()
        if lru_model_id in self._models:
            del self._models[lru_model_id]
            return True
        return False
    
    def clear(self):
        """Clear all models from cache"""
        with self._lock:
            self._models.clear()
            self._access_order.clear()
            self.current_size_mb = 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'current_size_mb': self.current_size_mb,
                'max_size_mb': self.max_size_mb,
                'current_models': len(self._models),
                'max_models': self.max_models,
                'utilization': self.current_size_mb / self.max_size_mb
            }

class ThreadSafeModelManager:
    """Thread-safe model management with reader-writer locks"""
    
    def __init__(self, 
                 cache_size_mb: float = 1000.0,
                 max_models: int = 10,
                 metadata_file: str = "models/metadata.json"):
        self._model_lock = ReadWriteLock()
        self._models: Dict[str, Any] = {}
        self._model_metadata: Dict[str, ModelMetadata] = {}
        self._access_metrics: Dict[str, AccessMetrics] = defaultdict(AccessMetrics)
        self._cache = ModelCache(cache_size_mb, max_models)
        self._metadata_file = Path(metadata_file)
        self._metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self._load_metadata()
        
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
        logger.info(f"ThreadSafeModelManager initialized with {len(self._model_metadata)} models")
    
    @contextmanager
    def read_model(self, model_id: str) -> ContextManager[Optional[Any]]:
        """Context manager for read-only model access"""
        with self._model_lock.reader():
            # Update access metrics
            start_time = time.time()
            try:
                model = self._get_model(model_id)
                if model:
                    self._update_access_metrics(model_id, True, start_time)
                yield model
            except Exception as e:
                self._update_access_metrics(model_id, False, start_time)
                logger.error(f"Error accessing model {model_id}: {e}")
                raise
    
    @contextmanager
    def write_model(self, model_id: str) -> ContextManager[Dict[str, Any]]:
        """Context manager for model updates"""
        with self._model_lock.writer():
            yield self._models
    
    def atomic_model_swap(self, old_model_id: str, new_model: Any, 
                         new_metadata: ModelMetadata) -> bool:
        """Atomic model replacement without service interruption"""
        try:
            with self._model_lock.writer():
                # Validate new model
                if not self._validate_model(new_model):
                    logger.error(f"Invalid model for {old_model_id}")
                    return False
                
                # Calculate model size
                model_size_mb = self._calculate_model_size(new_model)
                
                # Store old model temporarily
                old_model = self._models.get(old_model_id)
                old_metadata = self._model_metadata.get(old_model_id)
                
                # Update model and metadata atomically
                self._models[old_model_id] = new_model
                self._model_metadata[old_model_id] = new_metadata
                
                # Update cache
                self._cache.put(old_model_id, new_model, model_size_mb)
                
                # Save metadata
                self._save_metadata()
                
                logger.info(f"Successfully swapped model {old_model_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error in atomic model swap: {e}")
            # Rollback if possible
            if old_model and old_metadata:
                self._models[old_model_id] = old_model
                self._model_metadata[old_model_id] = old_metadata
            return False
    
    def register_model(self, model_id: str, model: Any, 
                      version: str = "1.0.0", tags: List[str] = None) -> bool:
        """Register a new model"""
        try:
            if not self._validate_model(model):
                logger.error(f"Invalid model for registration: {model_id}")
                return False
            
            model_size_mb = self._calculate_model_size(model)
            checksum = self._calculate_model_checksum(model)
            
            metadata = ModelMetadata(
                model_id=model_id,
                version=version,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                memory_usage_mb=model_size_mb,
                file_size_mb=model_size_mb,
                checksum=checksum,
                tags=tags or [],
                status="active"
            )
            
            with self._model_lock.writer():
                self._models[model_id] = model
                self._model_metadata[model_id] = metadata
                self._cache.put(model_id, model, model_size_mb)
                self._save_metadata()
            
            logger.info(f"Registered model {model_id} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering model {model_id}: {e}")
            return False
    
    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model"""
        try:
            with self._model_lock.writer():
                if model_id in self._models:
                    del self._models[model_id]
                    del self._model_metadata[model_id]
                    self._cache._remove(model_id)
                    self._save_metadata()
                    logger.info(f"Unregistered model {model_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error unregistering model {model_id}: {e}")
            return False
    
    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        with self._model_lock.reader():
            return self._model_metadata.get(model_id)
    
    def list_models(self, status: str = None, tags: List[str] = None) -> List[ModelMetadata]:
        """List models with optional filtering"""
        with self._model_lock.reader():
            models = list(self._model_metadata.values())
            
            if status:
                models = [m for m in models if m.status == status]
            
            if tags:
                models = [m for m in models if any(tag in m.tags for tag in tags)]
            
            return sorted(models, key=lambda x: x.last_accessed, reverse=True)
    
    def get_access_metrics(self, model_id: str) -> Optional[AccessMetrics]:
        """Get access metrics for a model"""
        with self._model_lock.reader():
            return self._access_metrics.get(model_id)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        with self._model_lock.reader():
            total_models = len(self._models)
            active_models = sum(1 for m in self._model_metadata.values() if m.status == "active")
            total_requests = sum(m.total_requests for m in self._access_metrics.values())
            total_errors = sum(m.failed_requests for m in self._access_metrics.values())
            
            cache_stats = self._cache.get_stats()
            
            return {
                'total_models': total_models,
                'active_models': active_models,
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0.0,
                'cache_stats': cache_stats,
                'memory_usage_mb': sum(m.memory_usage_mb for m in self._model_metadata.values())
            }
    
    def cleanup_inactive_models(self, max_age_hours: int = 24) -> int:
        """Clean up models that haven't been accessed recently"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._model_lock.writer():
            models_to_remove = []
            
            for model_id, metadata in self._model_metadata.items():
                if (metadata.last_accessed < cutoff_time and 
                    metadata.status != "active"):
                    models_to_remove.append(model_id)
            
            for model_id in models_to_remove:
                if self.unregister_model(model_id):
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} inactive models")
        return cleaned_count
    
    def _get_model(self, model_id: str) -> Optional[Any]:
        """Get model from cache or load from storage"""
        # Try cache first
        model = self._cache.get(model_id)
        if model:
            return model
        
        # Load from storage if not in cache
        if model_id in self._models:
            model = self._models[model_id]
            metadata = self._model_metadata.get(model_id)
            if metadata:
                self._cache.put(model_id, model, metadata.memory_usage_mb)
            return model
        
        return None
    
    def _validate_model(self, model: Any) -> bool:
        """Validate model structure and integrity"""
        try:
            # Basic validation - check if model has required methods
            if hasattr(model, 'predict'):
                # Test prediction with dummy data
                import numpy as np
                dummy_input = np.random.random((1, 10))
                _ = model.predict(dummy_input)
                return True
            return False
        except Exception as e:
            logger.warning(f"Model validation failed: {e}")
            return False
    
    def _calculate_model_size(self, model: Any) -> float:
        """Calculate model size in MB"""
        try:
            import sys
            size_bytes = sys.getsizeof(model)
            return size_bytes / (1024 * 1024)
        except Exception:
            return 0.0
    
    def _calculate_model_checksum(self, model: Any) -> str:
        """Calculate checksum for model integrity"""
        try:
            model_bytes = pickle.dumps(model)
            return hashlib.sha256(model_bytes).hexdigest()
        except Exception:
            return ""
    
    def _update_access_metrics(self, model_id: str, success: bool, start_time: float):
        """Update access metrics for a model"""
        latency_ms = (time.time() - start_time) * 1000
        
        if success:
            self._access_metrics[model_id].update_success(latency_ms)
        else:
            self._access_metrics[model_id].update_failure(latency_ms)
        
        # Update model metadata
        if model_id in self._model_metadata:
            self._model_metadata[model_id].last_accessed = datetime.now()
            self._model_metadata[model_id].access_count += 1
    
    def _load_metadata(self):
        """Load metadata from file"""
        try:
            if self._metadata_file.exists():
                with open(self._metadata_file, 'r') as f:
                    data = json.load(f)
                    for model_data in data.get('models', []):
                        metadata = ModelMetadata.from_dict(model_data)
                        self._model_metadata[metadata.model_id] = metadata
        except Exception as e:
            logger.warning(f"Error loading metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to file"""
        try:
            data = {
                'models': [metadata.to_dict() for metadata in self._model_metadata.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self._metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    self.cleanup_inactive_models()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self._cleanup_task = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_task.start()
    
    def shutdown(self):
        """Shutdown the model manager"""
        if self._cleanup_task:
            self._cleanup_task.join(timeout=5)
        self._save_metadata()
        logger.info("ThreadSafeModelManager shutdown complete")

# Global instance
model_manager = ThreadSafeModelManager()

# Convenience functions
def get_model(model_id: str) -> ContextManager[Optional[Any]]:
    """Get model with thread-safe access"""
    return model_manager.read_model(model_id)

def register_model(model_id: str, model: Any, version: str = "1.0.0", tags: List[str] = None) -> bool:
    """Register a new model"""
    return model_manager.register_model(model_id, model, version, tags)

def unregister_model(model_id: str) -> bool:
    """Unregister a model"""
    return model_manager.unregister_model(model_id)

def get_model_metadata(model_id: str) -> Optional[ModelMetadata]:
    """Get model metadata"""
    return model_manager.get_model_metadata(model_id)

def list_models(status: str = None, tags: List[str] = None) -> List[ModelMetadata]:
    """List models with optional filtering"""
    return model_manager.list_models(status, tags)

def get_system_stats() -> Dict[str, Any]:
    """Get system-wide statistics"""
    return model_manager.get_system_stats()
