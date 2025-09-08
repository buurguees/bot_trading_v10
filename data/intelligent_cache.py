"""
data/intelligent_cache.py - Sistema de Cache Inteligente con Invalidación Automática
Sistema de cache distribuido con gestión por timeframe y invalidación automática
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import json
import pickle
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
import sqlite3
import shutil
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

class CacheStatus(Enum):
    """Estados del cache"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    MISSING = "missing"

@dataclass
class CacheEntry:
    """Entrada del cache"""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int
    last_accessed: datetime
    size_bytes: int
    metadata: Dict[str, Any]

@dataclass
class CacheConfig:
    """Configuración del sistema de cache"""
    cache_dir: Path = Path("data/cache")
    max_size_mb: int = 1000  # Tamaño máximo del cache en MB
    cleanup_interval: int = 3600  # Intervalo de limpieza en segundos
    max_workers: int = 4  # Workers para operaciones paralelas
    compression_enabled: bool = True
    sqlite_cache: bool = True  # Usar SQLite para metadatos del cache

@dataclass
class CacheStats:
    """Estadísticas del sistema de cache"""
    total_entries: int
    total_size_mb: float
    hit_rate: float
    miss_rate: float
    expired_entries: int
    timeframes_cached: List[str]
    symbols_cached: List[str]
    last_cleanup: datetime

class IntelligentCacheManager:
    """Sistema de cache inteligente con invalidación automática por timeframe"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.logger = logging.getLogger(__name__)
        
        # Configurar directorios
        self.cache_dir = self.config.cache_dir
        self.features_dir = self.cache_dir / "features"
        self.aligned_data_dir = self.cache_dir / "aligned_data"
        self.metadata_dir = self.cache_dir / "metadata"
        
        # Crear directorios
        self._create_directories()
        
        # Configurar timeframes y expiración
        self.timeframe_cache_expiry = {
            '5m': 2,   # 2 horas
            '15m': 6,  # 6 horas
            '1h': 12,  # 12 horas
            '4h': 24,  # 24 horas
            '1d': 72   # 72 horas
        }
        
        # Cache en memoria para acceso rápido
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_metadata: Dict[str, Any] = {}
        
        # Locks para thread safety
        self._lock = threading.RLock()
        self._cleanup_lock = threading.Lock()
        
        # Estadísticas
        self._stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'created': 0
        }
        
        # Configurar SQLite para metadatos si está habilitado
        if self.config.sqlite_cache:
            self._init_sqlite_cache()
        
        # Iniciar limpieza automática
        self._start_cleanup_thread()
        
        self.logger.info(f"IntelligentCacheManager initialized at {self.cache_dir}")
    
    def _create_directories(self):
        """Crea la estructura de directorios del cache"""
        directories = [
            self.cache_dir,
            self.features_dir,
            self.aligned_data_dir,
            self.metadata_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _init_sqlite_cache(self):
        """Inicializa SQLite para metadatos del cache"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        metadata TEXT,
                        status TEXT DEFAULT 'valid'
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at);
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed);
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing SQLite cache: {e}")
    
    def _start_cleanup_thread(self):
        """Inicia hilo de limpieza automática"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.config.cleanup_interval)
                    self.cleanup_expired_cache_by_timeframe()
                except Exception as e:
                    self.logger.error(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def get_aligned_data_cached(
        self, 
        symbols: List[str], 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Obtiene datos alineados del cache
        
        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe de los datos
            start_date: Fecha de inicio
            end_date: Fecha de fin
        
        Returns:
            Optional[Dict[str, pd.DataFrame]]: Datos del cache o None si no están disponibles
        """
        try:
            cache_key = self._generate_cache_key(symbols, timeframe, start_date, end_date)
            
            with self._lock:
                # Verificar cache en memoria primero
                if cache_key in self._memory_cache:
                    entry = self._memory_cache[cache_key]
                    if self._is_entry_valid(entry):
                        entry.access_count += 1
                        entry.last_accessed = datetime.now()
                        self._stats['hits'] += 1
                        self.logger.debug(f"Cache hit for {cache_key}")
                        return entry.data
                    else:
                        # Entrada expirada
                        del self._memory_cache[cache_key]
                        self._stats['expired'] += 1
                
                # Verificar cache en disco
                cached_data = self._load_from_disk_cache(cache_key)
                if cached_data is not None:
                    # Cargar en memoria para acceso rápido
                    self._store_in_memory_cache(cache_key, cached_data, timeframe)
                    self._stats['hits'] += 1
                    self.logger.debug(f"Cache hit from disk for {cache_key}")
                    return cached_data
                
                self._stats['misses'] += 1
                self.logger.debug(f"Cache miss for {cache_key}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting cached data: {e}")
            return None
    
    def set_aligned_data_cache(
        self, 
        symbols: List[str], 
        timeframe: str, 
        data: Dict[str, pd.DataFrame],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Almacena datos alineados en el cache
        
        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe de los datos
            data: Datos a almacenar
            metadata: Metadatos adicionales
        
        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            # Generar clave de cache
            start_date = min(df.index.min() for df in data.values() if not df.empty) if data else datetime.now()
            end_date = max(df.index.max() for df in data.values() if not df.empty) if data else datetime.now()
            cache_key = self._generate_cache_key(symbols, timeframe, start_date, end_date)
            
            with self._lock:
                # Almacenar en memoria
                self._store_in_memory_cache(cache_key, data, timeframe, metadata)
                
                # Almacenar en disco
                self._store_in_disk_cache(cache_key, data, timeframe, metadata)
                
                self._stats['created'] += 1
                self.logger.debug(f"Cached data for {cache_key}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting cache data: {e}")
            return False
    
    def invalidate_timeframe_cache(self, timeframe: str) -> int:
        """
        Invalida todo el cache de un timeframe específico
        
        Args:
            timeframe: Timeframe a invalidar
        
        Returns:
            int: Número de entradas invalidadas
        """
        try:
            invalidated_count = 0
            
            with self._lock:
                # Invalidar cache en memoria
                keys_to_remove = []
                for key, entry in self._memory_cache.items():
                    if entry.metadata.get('timeframe') == timeframe:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._memory_cache[key]
                    invalidated_count += 1
                
                # Invalidar cache en disco
                if self.config.sqlite_cache:
                    invalidated_count += self._invalidate_disk_cache_by_timeframe(timeframe)
                
                self.logger.info(f"Invalidated {invalidated_count} entries for timeframe {timeframe}")
                return invalidated_count
                
        except Exception as e:
            self.logger.error(f"Error invalidating timeframe cache: {e}")
            return 0
    
    def cleanup_expired_cache_by_timeframe(self) -> int:
        """
        Limpia entradas expiradas del cache
        
        Returns:
            int: Número de entradas limpiadas
        """
        try:
            with self._cleanup_lock:
                cleaned_count = 0
                current_time = datetime.now()
                
                # Limpiar cache en memoria
                keys_to_remove = []
                for key, entry in self._memory_cache.items():
                    if current_time > entry.expires_at:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._memory_cache[key]
                    cleaned_count += 1
                
                # Limpiar cache en disco
                if self.config.sqlite_cache:
                    cleaned_count += self._cleanup_disk_cache()
                
                # Limpiar archivos huérfanos
                cleaned_count += self._cleanup_orphaned_files()
                
                self.logger.info(f"Cleaned up {cleaned_count} expired cache entries")
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    def get_cache_statistics(self) -> CacheStats:
        """Obtiene estadísticas del sistema de cache"""
        try:
            with self._lock:
                total_entries = len(self._memory_cache)
                total_size = sum(entry.size_bytes for entry in self._memory_cache.values())
                total_size_mb = total_size / (1024 * 1024)
                
                total_requests = self._stats['hits'] + self._stats['misses']
                hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
                miss_rate = self._stats['misses'] / total_requests if total_requests > 0 else 0.0
                
                # Obtener timeframes y símbolos cacheados
                timeframes_cached = set()
                symbols_cached = set()
                
                for entry in self._memory_cache.values():
                    if 'timeframe' in entry.metadata:
                        timeframes_cached.add(entry.metadata['timeframe'])
                    if 'symbols' in entry.metadata:
                        symbols_cached.update(entry.metadata['symbols'])
                
                return CacheStats(
                    total_entries=total_entries,
                    total_size_mb=total_size_mb,
                    hit_rate=hit_rate,
                    miss_rate=miss_rate,
                    expired_entries=self._stats['expired'],
                    timeframes_cached=list(timeframes_cached),
                    symbols_cached=list(symbols_cached),
                    last_cleanup=datetime.now()
                )
                
        except Exception as e:
            self.logger.error(f"Error getting cache statistics: {e}")
            return CacheStats(
                total_entries=0, total_size_mb=0.0, hit_rate=0.0, miss_rate=0.0,
                expired_entries=0, timeframes_cached=[], symbols_cached=[],
                last_cleanup=datetime.now()
            )
    
    def _generate_cache_key(
        self, 
        symbols: List[str], 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> str:
        """Genera una clave única para el cache"""
        key_data = {
            'symbols': sorted(symbols),
            'timeframe': timeframe,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Verifica si una entrada del cache es válida"""
        return datetime.now() <= entry.expires_at
    
    def _store_in_memory_cache(
        self, 
        key: str, 
        data: Any, 
        timeframe: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena datos en el cache en memoria"""
        try:
            # Calcular tamaño
            size_bytes = len(pickle.dumps(data))
            
            # Calcular expiración
            expiry_hours = self.timeframe_cache_expiry.get(timeframe, 24)
            expires_at = datetime.now() + timedelta(hours=expiry_hours)
            
            # Crear entrada
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                expires_at=expires_at,
                access_count=0,
                last_accessed=datetime.now(),
                size_bytes=size_bytes,
                metadata=metadata or {'timeframe': timeframe}
            )
            
            # Verificar límite de tamaño
            if size_bytes > self.config.max_size_mb * 1024 * 1024:
                self.logger.warning(f"Entry too large for cache: {size_bytes} bytes")
                return
            
            # Almacenar
            self._memory_cache[key] = entry
            
            # Limpiar cache si es necesario
            self._cleanup_memory_cache_if_needed()
            
        except Exception as e:
            self.logger.error(f"Error storing in memory cache: {e}")
    
    def _store_in_disk_cache(
        self, 
        key: str, 
        data: Any, 
        timeframe: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena datos en el cache en disco"""
        try:
            # Crear archivo de cache
            cache_file = self.aligned_data_dir / f"{key}.pkl"
            
            # Comprimir si está habilitado
            if self.config.compression_enabled:
                with gzip.open(f"{cache_file}.gz", 'wb') as f:
                    pickle.dump(data, f)
                cache_file = Path(f"{cache_file}.gz")
            else:
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f)
            
            # Almacenar metadatos en SQLite si está habilitado
            if self.config.sqlite_cache:
                self._store_cache_metadata(key, cache_file, timeframe, metadata)
            
        except Exception as e:
            self.logger.error(f"Error storing in disk cache: {e}")
    
    def _load_from_disk_cache(self, key: str) -> Optional[Any]:
        """Carga datos del cache en disco"""
        try:
            # Buscar archivo de cache
            cache_file = self.aligned_data_dir / f"{key}.pkl"
            compressed_file = self.aligned_data_dir / f"{key}.pkl.gz"
            
            file_to_load = None
            is_compressed = False
            
            if compressed_file.exists():
                file_to_load = compressed_file
                is_compressed = True
            elif cache_file.exists():
                file_to_load = cache_file
                is_compressed = False
            
            if file_to_load is None:
                return None
            
            # Verificar expiración en SQLite si está habilitado
            if self.config.sqlite_cache:
                if not self._is_disk_entry_valid(key):
                    file_to_load.unlink()
                    return None
            
            # Cargar datos
            if is_compressed:
                with gzip.open(file_to_load, 'rb') as f:
                    data = pickle.load(f)
            else:
                with open(file_to_load, 'rb') as f:
                    data = pickle.load(f)
            
            # Actualizar estadísticas de acceso
            if self.config.sqlite_cache:
                self._update_access_stats(key)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading from disk cache: {e}")
            return None
    
    def _store_cache_metadata(
        self, 
        key: str, 
        file_path: Path, 
        timeframe: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena metadatos del cache en SQLite"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                expiry_hours = self.timeframe_cache_expiry.get(timeframe, 24)
                expires_at = datetime.now() + timedelta(hours=expiry_hours)
                
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, file_path, created_at, expires_at, access_count, last_accessed, size_bytes, metadata, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key, str(file_path), datetime.now(), expires_at,
                    0, datetime.now(), file_path.stat().st_size,
                    json.dumps(metadata or {}), 'valid'
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing cache metadata: {e}")
    
    def _is_disk_entry_valid(self, key: str) -> bool:
        """Verifica si una entrada del disco es válida"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                cursor = conn.execute(
                    "SELECT expires_at FROM cache_entries WHERE key = ?", (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    expires_at = datetime.fromisoformat(result[0])
                    return datetime.now() <= expires_at
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking disk entry validity: {e}")
            return False
    
    def _update_access_stats(self, key: str):
        """Actualiza estadísticas de acceso"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                conn.execute("""
                    UPDATE cache_entries 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE key = ?
                """, (datetime.now(), key))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating access stats: {e}")
    
    def _invalidate_disk_cache_by_timeframe(self, timeframe: str) -> int:
        """Invalida cache en disco por timeframe"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                # Obtener entradas a invalidar
                cursor = conn.execute(
                    "SELECT key, file_path FROM cache_entries WHERE metadata LIKE ? AND status = 'valid'",
                    (f'%"timeframe": "{timeframe}"%',)
                )
                entries = cursor.fetchall()
                
                invalidated_count = 0
                for key, file_path in entries:
                    try:
                        # Eliminar archivo
                        Path(file_path).unlink(missing_ok=True)
                        
                        # Marcar como inválido
                        conn.execute(
                            "UPDATE cache_entries SET status = 'invalid' WHERE key = ?",
                            (key,)
                        )
                        invalidated_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Error invalidating {key}: {e}")
                
                conn.commit()
                return invalidated_count
                
        except Exception as e:
            self.logger.error(f"Error invalidating disk cache: {e}")
            return 0
    
    def _cleanup_disk_cache(self) -> int:
        """Limpia cache expirado en disco"""
        try:
            cache_db = self.cache_dir / "cache_metadata.db"
            with sqlite3.connect(cache_db) as conn:
                # Obtener entradas expiradas
                cursor = conn.execute(
                    "SELECT key, file_path FROM cache_entries WHERE expires_at < ? AND status = 'valid'",
                    (datetime.now(),)
                )
                entries = cursor.fetchall()
                
                cleaned_count = 0
                for key, file_path in entries:
                    try:
                        # Eliminar archivo
                        Path(file_path).unlink(missing_ok=True)
                        
                        # Marcar como expirado
                        conn.execute(
                            "UPDATE cache_entries SET status = 'expired' WHERE key = ?",
                            (key,)
                        )
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Error cleaning up {key}: {e}")
                
                conn.commit()
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up disk cache: {e}")
            return 0
    
    def _cleanup_orphaned_files(self) -> int:
        """Limpia archivos huérfanos del cache"""
        try:
            cleaned_count = 0
            
            # Obtener archivos en el directorio de cache
            cache_files = list(self.aligned_data_dir.glob("*.pkl*"))
            
            if self.config.sqlite_cache:
                # Obtener archivos válidos de la base de datos
                cache_db = self.cache_dir / "cache_metadata.db"
                with sqlite3.connect(cache_db) as conn:
                    cursor = conn.execute("SELECT file_path FROM cache_entries WHERE status = 'valid'")
                    valid_files = {Path(row[0]) for row in cursor.fetchall()}
                
                # Eliminar archivos huérfanos
                for file_path in cache_files:
                    if file_path not in valid_files:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                        except Exception as e:
                            self.logger.warning(f"Error removing orphaned file {file_path}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up orphaned files: {e}")
            return 0
    
    def _cleanup_memory_cache_if_needed(self):
        """Limpia cache en memoria si es necesario"""
        try:
            current_size = sum(entry.size_bytes for entry in self._memory_cache.values())
            max_size_bytes = self.config.max_size_mb * 1024 * 1024
            
            if current_size > max_size_bytes:
                # Ordenar por último acceso y eliminar los más antiguos
                sorted_entries = sorted(
                    self._memory_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                # Eliminar 20% de las entradas más antiguas
                entries_to_remove = int(len(sorted_entries) * 0.2)
                
                for key, _ in sorted_entries[:entries_to_remove]:
                    del self._memory_cache[key]
                
                self.logger.info(f"Cleaned up {entries_to_remove} entries from memory cache")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up memory cache: {e}")

# Funciones de conveniencia
def create_cache_manager(config: Optional[CacheConfig] = None) -> IntelligentCacheManager:
    """Crea un gestor de cache inteligente"""
    return IntelligentCacheManager(config)

def quick_cache_data(
    symbols: List[str], 
    timeframe: str, 
    data: Dict[str, pd.DataFrame]
) -> bool:
    """Función de conveniencia para cachear datos rápidamente"""
    manager = IntelligentCacheManager()
    return manager.set_aligned_data_cache(symbols, timeframe, data)

def quick_get_cached_data(
    symbols: List[str], 
    timeframe: str, 
    start_date: datetime, 
    end_date: datetime
) -> Optional[Dict[str, pd.DataFrame]]:
    """Función de conveniencia para obtener datos del cache rápidamente"""
    manager = IntelligentCacheManager()
    return manager.get_aligned_data_cached(symbols, timeframe, start_date, end_date)
