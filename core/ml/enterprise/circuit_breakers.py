# Ruta: core/ml/enterprise/circuit_breakers.py
"""
models/enterprise/circuit_breakers.py - Circuit Breaker Pattern for ML Services
Sistema de circuit breakers y fallbacks para servicios de ML enterprise
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from collections import deque
import threading
import random
import numpy as np

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

class FailureType(Enum):
    """Types of failures"""
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    INVALID_RESPONSE = "invalid_response"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # for half-open state
    timeout_duration: float = 30.0  # seconds
    max_requests_half_open: int = 5
    monitoring_window: int = 300  # seconds
    
    # Advanced settings
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_timeout: bool = True
    retry_on_exception: bool = True

@dataclass
class FailureRecord:
    """Record of a failure"""
    timestamp: datetime
    failure_type: FailureType
    error_message: str
    request_id: Optional[str] = None
    response_time: float = 0.0

@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    failure_rate: float = 0.0

class MLCircuitBreaker:
    """Circuit breaker for ML model operations"""
    
    def __init__(self, 
                 name: str,
                 config: CircuitBreakerConfig = None,
                 failure_callback: Optional[Callable] = None,
                 success_callback: Optional[Callable] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.failure_callback = failure_callback
        self.success_callback = success_callback
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Failure tracking
        self.failure_history = deque(maxlen=1000)
        self.request_history = deque(maxlen=1000)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = CircuitBreakerStats()
        
        logger.info(f"Circuit breaker '{name}' initialized")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpenError: When circuit is open
            Various exceptions: From the wrapped function
        """
        with self._lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Last failure: {self.last_failure_time}"
                    )
            
            # Check half-open limits
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.max_requests_half_open:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' HALF_OPEN request limit exceeded"
                    )
        
        # Execute function with timeout
        start_time = time.time()
        request_id = kwargs.get('request_id', f"req_{int(time.time() * 1000)}")
        
        try:
            # Add timeout if specified
            if self.config.timeout_duration > 0:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_duration
                )
            else:
                result = await func(*args, **kwargs)
            
            # Record success
            response_time = time.time() - start_time
            self._record_success(request_id, response_time)
            
            return result
            
        except asyncio.TimeoutError:
            self._record_failure(
                FailureType.TIMEOUT,
                f"Function call timed out after {self.config.timeout_duration}s",
                request_id,
                time.time() - start_time
            )
            raise
            
        except Exception as e:
            self._record_failure(
                FailureType.EXCEPTION,
                str(e),
                request_id,
                time.time() - start_time
            )
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout
    
    def _record_success(self, request_id: str, response_time: float):
        """Record successful request"""
        with self._lock:
            self.success_count += 1
            self.failure_count = 0
            self.last_success_time = datetime.now()
            
            # Update statistics
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.last_success = self.last_success_time
            self._update_failure_rate()
            
            # Record request
            self.request_history.append({
                'timestamp': datetime.now(),
                'request_id': request_id,
                'success': True,
                'response_time': response_time
            })
            
            # Check if circuit should close
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.stats.circuit_closes += 1
                    logger.info(f"Circuit breaker '{self.name}' closed after {self.success_count} successes")
                    
                    if self.success_callback:
                        try:
                            self.success_callback(self.name, request_id)
                        except Exception as e:
                            logger.error(f"Error in success callback: {e}")
    
    def _record_failure(self, failure_type: FailureType, error_message: str, 
                       request_id: str, response_time: float):
        """Record failed request"""
        with self._lock:
            self.failure_count += 1
            self.success_count = 0
            self.last_failure_time = datetime.now()
            
            # Update statistics
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.last_failure = self.last_failure_time
            self._update_failure_rate()
            
            # Record failure
            failure_record = FailureRecord(
                timestamp=datetime.now(),
                failure_type=failure_type,
                error_message=error_message,
                request_id=request_id,
                response_time=response_time
            )
            self.failure_history.append(failure_record)
            
            # Record request
            self.request_history.append({
                'timestamp': datetime.now(),
                'request_id': request_id,
                'success': False,
                'response_time': response_time,
                'failure_type': failure_type.value
            })
            
            # Check if circuit should open
            if self.failure_count >= self.config.failure_threshold:
                if self.state != CircuitState.OPEN:
                    self.state = CircuitState.OPEN
                    self.stats.circuit_opens += 1
                    logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")
                    
                    if self.failure_callback:
                        try:
                            self.failure_callback(self.name, failure_record)
                        except Exception as e:
                            logger.error(f"Error in failure callback: {e}")
    
    def _update_failure_rate(self):
        """Update failure rate based on recent requests"""
        if self.stats.total_requests == 0:
            self.stats.failure_rate = 0.0
        else:
            self.stats.failure_rate = self.stats.failed_requests / self.stats.total_requests
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics"""
        with self._lock:
            self.stats.current_state = self.state
            return self.stats
    
    def reset(self):
        """Manually reset circuit breaker"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_failure_history(self, limit: int = 100) -> List[FailureRecord]:
        """Get recent failure history"""
        with self._lock:
            return list(self.failure_history)[-limit:]

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class GracefulDegradationHandler:
    """Handles graceful service degradation with fallback strategies"""
    
    def __init__(self):
        self.fallback_strategies = {
            'prediction': [
                self._simple_momentum_fallback,
                self._technical_indicator_fallback,
                self._conservative_hold_fallback,
                self._random_fallback
            ],
            'confidence': [
                self._historical_confidence_fallback,
                self._fixed_low_confidence_fallback
            ],
            'model_loading': [
                self._load_cached_model,
                self._load_previous_version,
                self._load_default_model
            ]
        }
        
        self.fallback_stats = {
            'total_fallbacks': 0,
            'successful_fallbacks': 0,
            'fallback_by_type': {}
        }
    
    async def handle_prediction_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle prediction service failure with fallbacks
        
        Args:
            context: Context information for fallback
        
        Returns:
            Fallback prediction result
        """
        self.fallback_stats['total_fallbacks'] += 1
        
        for strategy in self.fallback_strategies['prediction']:
            try:
                result = await strategy(context)
                if result:
                    self.fallback_stats['successful_fallbacks'] += 1
                    self._record_fallback_success('prediction', strategy.__name__)
                    return result
            except Exception as e:
                logger.warning(f"Fallback strategy {strategy.__name__} failed: {e}")
                continue
        
        # Ultimate fallback
        return await self._emergency_safe_mode(context)
    
    async def handle_confidence_failure(self, context: Dict[str, Any]) -> float:
        """Handle confidence calculation failure"""
        self.fallback_stats['total_fallbacks'] += 1
        
        for strategy in self.fallback_strategies['confidence']:
            try:
                result = await strategy(context)
                if result is not None:
                    self.fallback_stats['successful_fallbacks'] += 1
                    self._record_fallback_success('confidence', strategy.__name__)
                    return result
            except Exception as e:
                logger.warning(f"Confidence fallback strategy {strategy.__name__} failed: {e}")
                continue
        
        # Default low confidence
        return 0.1
    
    async def _simple_momentum_fallback(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simple momentum-based fallback prediction"""
        try:
            features = context.get('features', [])
            if len(features) < 2:
                return None
            
            # Simple momentum calculation
            recent_prices = features[-10:] if len(features) >= 10 else features
            momentum = np.mean(np.diff(recent_prices))
            
            if momentum > 0.01:
                action = 'buy'
                confidence = min(0.6, abs(momentum) * 10)
            elif momentum < -0.01:
                action = 'sell'
                confidence = min(0.6, abs(momentum) * 10)
            else:
                action = 'hold'
                confidence = 0.3
            
            return {
                'prediction': action,
                'confidence': confidence,
                'fallback_method': 'momentum',
                'metadata': {'momentum': float(momentum)}
            }
        except Exception as e:
            logger.error(f"Momentum fallback error: {e}")
            return None
    
    async def _technical_indicator_fallback(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Technical indicator-based fallback"""
        try:
            features = context.get('features', [])
            if len(features) < 20:
                return None
            
            # Simple RSI calculation
            prices = features[-20:]
            gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
            losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # RSI-based decision
            if rsi < 30:
                action = 'buy'
                confidence = 0.5
            elif rsi > 70:
                action = 'sell'
                confidence = 0.5
            else:
                action = 'hold'
                confidence = 0.4
            
            return {
                'prediction': action,
                'confidence': confidence,
                'fallback_method': 'rsi',
                'metadata': {'rsi': float(rsi)}
            }
        except Exception as e:
            logger.error(f"Technical indicator fallback error: {e}")
            return None
    
    async def _conservative_hold_fallback(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Conservative hold fallback"""
        return {
            'prediction': 'hold',
            'confidence': 0.2,
            'fallback_method': 'conservative_hold',
            'metadata': {'reason': 'conservative_fallback'}
        }
    
    async def _random_fallback(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Random fallback (last resort)"""
        actions = ['buy', 'sell', 'hold']
        action = random.choice(actions)
        confidence = 0.1
        
        return {
            'prediction': action,
            'confidence': confidence,
            'fallback_method': 'random',
            'metadata': {'reason': 'random_fallback'}
        }
    
    async def _historical_confidence_fallback(self, context: Dict[str, Any]) -> Optional[float]:
        """Historical confidence fallback"""
        try:
            # Get historical confidence for similar conditions
            symbol = context.get('symbol', 'UNKNOWN')
            # This would typically query a database
            # For now, return a reasonable default
            return 0.4
        except Exception as e:
            logger.error(f"Historical confidence fallback error: {e}")
            return None
    
    async def _fixed_low_confidence_fallback(self, context: Dict[str, Any]) -> float:
        """Fixed low confidence fallback"""
        return 0.1
    
    async def _load_cached_model(self, context: Dict[str, Any]) -> Optional[Any]:
        """Load cached model fallback"""
        try:
            model_id = context.get('model_id')
            if not model_id:
                return None
            
            # Try to load from cache
            from models.enterprise.thread_safe_manager import model_manager
            with model_manager.read_model(model_id) as model:
                return model
        except Exception as e:
            logger.error(f"Cache model fallback error: {e}")
            return None
    
    async def _load_previous_version(self, context: Dict[str, Any]) -> Optional[Any]:
        """Load previous model version fallback"""
        try:
            model_id = context.get('model_id')
            if not model_id:
                return None
            
            # Try to load previous version
            from models.enterprise.thread_safe_manager import model_manager
            metadata = model_manager.get_model_metadata(model_id)
            if metadata and metadata.version != "1.0.0":
                # Load previous version logic here
                pass
            return None
        except Exception as e:
            logger.error(f"Previous version fallback error: {e}")
            return None
    
    async def _load_default_model(self, context: Dict[str, Any]) -> Optional[Any]:
        """Load default model fallback"""
        try:
            # Load a simple default model
            # This would typically be a very basic model
            return None
        except Exception as e:
            logger.error(f"Default model fallback error: {e}")
            return None
    
    async def _emergency_safe_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency safe mode fallback"""
        logger.critical("All fallback strategies failed, entering emergency safe mode")
        
        return {
            'prediction': 'hold',
            'confidence': 0.05,
            'fallback_method': 'emergency_safe_mode',
            'metadata': {
                'reason': 'all_fallbacks_failed',
                'timestamp': datetime.now().isoformat(),
                'critical': True
            }
        }
    
    def _record_fallback_success(self, fallback_type: str, strategy_name: str):
        """Record successful fallback"""
        if fallback_type not in self.fallback_stats['fallback_by_type']:
            self.fallback_stats['fallback_by_type'][fallback_type] = {}
        
        if strategy_name not in self.fallback_stats['fallback_by_type'][fallback_type]:
            self.fallback_stats['fallback_by_type'][fallback_type][strategy_name] = 0
        
        self.fallback_stats['fallback_by_type'][fallback_type][strategy_name] += 1
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback statistics"""
        return self.fallback_stats.copy()

class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, MLCircuitBreaker] = {}
        self.degradation_handler = GracefulDegradationHandler()
    
    def create_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> MLCircuitBreaker:
        """Create a new circuit breaker"""
        if name in self.circuit_breakers:
            logger.warning(f"Circuit breaker '{name}' already exists, replacing")
        
        circuit_breaker = MLCircuitBreaker(
            name=name,
            config=config,
            failure_callback=self._on_circuit_failure,
            success_callback=self._on_circuit_success
        )
        
        self.circuit_breakers[name] = circuit_breaker
        logger.info(f"Created circuit breaker '{name}'")
        
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[MLCircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers"""
        return {name: cb.get_stats() for name, cb in self.circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")
    
    def _on_circuit_failure(self, name: str, failure_record: FailureRecord):
        """Handle circuit breaker failure"""
        logger.warning(f"Circuit breaker '{name}' failure: {failure_record.error_message}")
        
        # Trigger fallback if available
        context = {
            'circuit_breaker': name,
            'failure_type': failure_record.failure_type.value,
            'error_message': failure_record.error_message
        }
        
        # This would typically trigger appropriate fallback strategies
        asyncio.create_task(self._handle_circuit_failure_fallback(context))
    
    def _on_circuit_success(self, name: str, request_id: str):
        """Handle circuit breaker success"""
        logger.info(f"Circuit breaker '{name}' recovered successfully")
    
    async def _handle_circuit_failure_fallback(self, context: Dict[str, Any]):
        """Handle circuit breaker failure with fallbacks"""
        try:
            # Determine appropriate fallback based on circuit breaker name
            if 'prediction' in context['circuit_breaker']:
                await self.degradation_handler.handle_prediction_failure(context)
            elif 'confidence' in context['circuit_breaker']:
                await self.degradation_handler.handle_confidence_failure(context)
        except Exception as e:
            logger.error(f"Error handling circuit failure fallback: {e}")

# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()

# Convenience functions
def create_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> MLCircuitBreaker:
    """Create a circuit breaker"""
    return circuit_breaker_manager.create_circuit_breaker(name, config)

def get_circuit_breaker(name: str) -> Optional[MLCircuitBreaker]:
    """Get a circuit breaker"""
    return circuit_breaker_manager.get_circuit_breaker(name)

def get_all_circuit_stats() -> Dict[str, CircuitBreakerStats]:
    """Get all circuit breaker statistics"""
    return circuit_breaker_manager.get_all_stats()

def get_fallback_stats() -> Dict[str, Any]:
    """Get fallback statistics"""
    return circuit_breaker_manager.degradation_handler.get_fallback_stats()
