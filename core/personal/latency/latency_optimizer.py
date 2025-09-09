"""
Latency Optimizer - Bot Trading v10 Personal
============================================

Optimizador de latencia para trading de alta frecuencia personal con:
- Latencia objetivo <50ms
- Pre-carga de order books
- Cache inteligente de datos
- Optimización de conexiones
- Métricas de rendimiento en tiempo real
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge
import numpy as np
from collections import deque
import threading

logger = logging.getLogger(__name__)

# Métricas Prometheus
trade_latency = Histogram('trading_bot_trade_latency_seconds', 'Latencia de trades', ['exchange', 'operation'])
order_book_latency = Histogram('trading_bot_order_book_latency_seconds', 'Latencia de order books', ['exchange', 'symbol'])
cache_hits = Counter('trading_bot_cache_hits_total', 'Cache hits', ['cache_type'])
cache_misses = Counter('trading_bot_cache_misses_total', 'Cache misses', ['cache_type'])
optimization_events = Counter('trading_bot_optimization_events_total', 'Eventos de optimización', ['event_type'])

@dataclass
class LatencyMetrics:
    """Métricas de latencia"""
    operation: str
    exchange: str
    latency_ms: float
    timestamp: datetime
    success: bool
    cache_hit: bool = False

@dataclass
class CacheEntry:
    """Entrada de cache"""
    data: Any
    timestamp: datetime
    ttl: int  # Time to live en segundos

class LatencyOptimizer:
    """Optimizador de latencia para HFT personal"""
    
    def __init__(self, exchange_manager, config: Dict[str, Any]):
        self.exchange_manager = exchange_manager
        self.config = config
        self.cache = {}
        self.latency_history = deque(maxlen=1000)
        self.is_running = False
        
        # Configuración de optimización
        self.target_latency_ms = config.get('target_latency_ms', 50)
        self.cache_ttl = config.get('cache_ttl', 1)  # 1 segundo
        self.preload_symbols = config.get('preload_symbols', ['BTCUSDT', 'ETHUSDT'])
        self.optimization_enabled = config.get('optimization_enabled', True)
        
        # Thread para pre-carga
        self.preload_thread = None
        self.preload_running = False
        
        # Estadísticas de rendimiento
        self.performance_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_latency_ms': 0.0,
            'p95_latency_ms': 0.0,
            'p99_latency_ms': 0.0
        }
        
        logger.info("LatencyOptimizer inicializado")
    
    async def start(self):
        """Inicia el optimizador de latencia"""
        try:
            logger.info("Iniciando LatencyOptimizer...")
            self.is_running = True
            
            # Iniciar pre-carga de datos
            if self.optimization_enabled:
                await self._start_preloading()
            
            # Iniciar monitoreo de rendimiento
            asyncio.create_task(self._performance_monitor())
            
            logger.info("LatencyOptimizer iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando LatencyOptimizer: {e}")
            raise
    
    async def stop(self):
        """Detiene el optimizador de latencia"""
        try:
            logger.info("Deteniendo LatencyOptimizer...")
            self.is_running = False
            self.preload_running = False
            
            if self.preload_thread and self.preload_thread.is_alive():
                self.preload_thread.join(timeout=5)
            
            logger.info("LatencyOptimizer detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo LatencyOptimizer: {e}")
    
    async def _start_preloading(self):
        """Inicia la pre-carga de datos"""
        try:
            self.preload_running = True
            self.preload_thread = threading.Thread(target=self._preload_worker)
            self.preload_thread.daemon = True
            self.preload_thread.start()
            
            logger.info("Pre-carga de datos iniciada")
            
        except Exception as e:
            logger.error(f"Error iniciando pre-carga: {e}")
    
    def _preload_worker(self):
        """Worker para pre-carga de datos en thread separado"""
        while self.preload_running:
            try:
                # Pre-cargar order books
                for symbol in self.preload_symbols:
                    asyncio.run(self._preload_order_book(symbol))
                
                time.sleep(0.1)  # Pre-cargar cada 100ms
                
            except Exception as e:
                logger.error(f"Error en pre-carga: {e}")
                time.sleep(1)
    
    async def _preload_order_book(self, symbol: str):
        """Pre-carga el order book de un símbolo"""
        try:
            for exchange_id in self.exchange_manager.get_available_exchanges():
                cache_key = f"order_book_{exchange_id}_{symbol}"
                
                # Verificar si el cache está expirado
                if self._is_cache_expired(cache_key):
                    order_book = await self.exchange_manager.get_order_book(symbol, exchange_id)
                    
                    if order_book:
                        self._cache_data(cache_key, order_book, ttl=self.cache_ttl)
                        
        except Exception as e:
            logger.error(f"Error pre-cargando order book {symbol}: {e}")
    
    async def execute_trade_optimized(self, exchange_id: str, symbol: str, side: str, 
                                    amount: float, order_type: str = 'market') -> Dict[str, Any]:
        """Ejecuta un trade con optimización de latencia"""
        start_time = time.time()
        
        try:
            # Verificar cache para datos relevantes
            cache_key = f"order_book_{exchange_id}_{symbol}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                cache_hits.labels(cache_type='order_book').inc()
                self.performance_stats['cache_hits'] += 1
            else:
                cache_misses.labels(cache_type='order_book').inc()
                self.performance_stats['cache_misses'] += 1
            
            # Ejecutar trade
            result = await self.exchange_manager.execute_trade(
                exchange_id, symbol, side, amount, order_type
            )
            
            # Calcular latencia
            latency_ms = (time.time() - start_time) * 1000
            
            # Registrar métricas
            trade_latency.labels(exchange=exchange_id, operation='execute_trade').observe(latency_ms / 1000)
            
            # Actualizar estadísticas
            self._update_performance_stats(latency_ms, result.get('success', False))
            
            # Log de latencia
            if latency_ms > self.target_latency_ms:
                logger.warning(f"⚠️ Latencia alta: {latency_ms:.2f}ms (objetivo: {self.target_latency_ms}ms)")
                optimization_events.labels(event_type='high_latency').inc()
            
            return {
                **result,
                'latency_ms': latency_ms,
                'cache_hit': cached_data is not None
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando trade optimizado: {e}")
            return {
                'success': False,
                'error': str(e),
                'latency_ms': (time.time() - start_time) * 1000
            }
    
    async def get_order_book_optimized(self, symbol: str, exchange_id: str = None) -> Dict[str, Any]:
        """Obtiene order book con optimización de latencia"""
        start_time = time.time()
        
        try:
            if exchange_id:
                # Obtener de un exchange específico
                cache_key = f"order_book_{exchange_id}_{symbol}"
                cached_data = self._get_cached_data(cache_key)
                
                if cached_data:
                    cache_hits.labels(cache_type='order_book').inc()
                    self.performance_stats['cache_hits'] += 1
                    
                    latency_ms = (time.time() - start_time) * 1000
                    order_book_latency.labels(exchange=exchange_id, symbol=symbol).observe(latency_ms / 1000)
                    
                    return {
                        'success': True,
                        'data': cached_data,
                        'exchange': exchange_id,
                        'latency_ms': latency_ms,
                        'cache_hit': True
                    }
                else:
                    cache_misses.labels(cache_type='order_book').inc()
                    self.performance_stats['cache_misses'] += 1
                    
                    # Obtener datos frescos
                    order_book = await self.exchange_manager.get_order_book(symbol, exchange_id)
                    
                    # Cachear datos
                    self._cache_data(cache_key, order_book, ttl=self.cache_ttl)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    order_book_latency.labels(exchange=exchange_id, symbol=symbol).observe(latency_ms / 1000)
                    
                    return {
                        'success': True,
                        'data': order_book,
                        'exchange': exchange_id,
                        'latency_ms': latency_ms,
                        'cache_hit': False
                    }
            else:
                # Obtener de todos los exchanges
                order_books = await self.exchange_manager.get_order_book(symbol)
                
                latency_ms = (time.time() - start_time) * 1000
                
                return {
                    'success': True,
                    'data': order_books,
                    'latency_ms': latency_ms,
                    'cache_hit': False
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo order book optimizado: {e}")
            return {
                'success': False,
                'error': str(e),
                'latency_ms': (time.time() - start_time) * 1000
            }
    
    def _cache_data(self, key: str, data: Any, ttl: int = 1):
        """Cachea datos con TTL"""
        self.cache[key] = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            ttl=ttl
        )
    
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Obtiene datos del cache si no están expirados"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        if self._is_cache_expired(key):
            del self.cache[key]
            return None
        
        return entry.data
    
    def _is_cache_expired(self, key: str) -> bool:
        """Verifica si una entrada del cache está expirada"""
        if key not in self.cache:
            return True
        
        entry = self.cache[key]
        age = (datetime.now() - entry.timestamp).total_seconds()
        
        return age > entry.ttl
    
    def _update_performance_stats(self, latency_ms: float, success: bool):
        """Actualiza las estadísticas de rendimiento"""
        self.performance_stats['total_operations'] += 1
        
        if success:
            self.performance_stats['successful_operations'] += 1
        
        # Actualizar latencia promedio
        self.latency_history.append(latency_ms)
        
        if self.latency_history:
            latencies = list(self.latency_history)
            self.performance_stats['avg_latency_ms'] = np.mean(latencies)
            self.performance_stats['p95_latency_ms'] = np.percentile(latencies, 95)
            self.performance_stats['p99_latency_ms'] = np.percentile(latencies, 99)
    
    async def _performance_monitor(self):
        """Monitor de rendimiento en tiempo real"""
        while self.is_running:
            try:
                # Verificar si necesitamos optimización
                await self._check_optimization_needs()
                
                # Limpiar cache expirado
                self._cleanup_expired_cache()
                
                await asyncio.sleep(10)  # Verificar cada 10 segundos
                
            except Exception as e:
                logger.error(f"Error en monitor de rendimiento: {e}")
                await asyncio.sleep(30)
    
    async def _check_optimization_needs(self):
        """Verifica si se necesitan optimizaciones"""
        try:
            # Verificar latencia promedio
            if self.performance_stats['avg_latency_ms'] > self.target_latency_ms:
                logger.warning(f"Latencia promedio alta: {self.performance_stats['avg_latency_ms']:.2f}ms")
                optimization_events.labels(event_type='avg_latency_high').inc()
                
                # Ajustar configuración de cache
                if self.cache_ttl > 0.1:
                    self.cache_ttl = max(0.1, self.cache_ttl * 0.9)
                    logger.info(f"Reduciendo TTL de cache a {self.cache_ttl:.2f}s")
            
            # Verificar tasa de éxito
            success_rate = (self.performance_stats['successful_operations'] / 
                          max(1, self.performance_stats['total_operations']))
            
            if success_rate < 0.95:  # Menos del 95% de éxito
                logger.warning(f"Tasa de éxito baja: {success_rate:.2%}")
                optimization_events.labels(event_type='low_success_rate').inc()
            
            # Verificar cache hit rate
            total_cache_ops = self.performance_stats['cache_hits'] + self.performance_stats['cache_misses']
            if total_cache_ops > 0:
                cache_hit_rate = self.performance_stats['cache_hits'] / total_cache_ops
                
                if cache_hit_rate < 0.5:  # Menos del 50% de cache hits
                    logger.warning(f"Cache hit rate bajo: {cache_hit_rate:.2%}")
                    optimization_events.labels(event_type='low_cache_hit_rate').inc()
                    
                    # Aumentar TTL de cache
                    self.cache_ttl = min(5.0, self.cache_ttl * 1.1)
                    logger.info(f"Aumentando TTL de cache a {self.cache_ttl:.2f}s")
                
        except Exception as e:
            logger.error(f"Error verificando optimizaciones: {e}")
    
    def _cleanup_expired_cache(self):
        """Limpia entradas expiradas del cache"""
        expired_keys = []
        
        for key, entry in self.cache.items():
            if self._is_cache_expired(key):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Limpiadas {len(expired_keys)} entradas expiradas del cache")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Obtiene las estadísticas de rendimiento"""
        total_ops = self.performance_stats['total_operations']
        successful_ops = self.performance_stats['successful_operations']
        
        return {
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'success_rate': successful_ops / max(1, total_ops),
            'cache_hits': self.performance_stats['cache_hits'],
            'cache_misses': self.performance_stats['cache_misses'],
            'cache_hit_rate': (self.performance_stats['cache_hits'] / 
                             max(1, self.performance_stats['cache_hits'] + self.performance_stats['cache_misses'])),
            'avg_latency_ms': self.performance_stats['avg_latency_ms'],
            'p95_latency_ms': self.performance_stats['p95_latency_ms'],
            'p99_latency_ms': self.performance_stats['p99_latency_ms'],
            'target_latency_ms': self.target_latency_ms,
            'cache_ttl': self.cache_ttl,
            'cache_size': len(self.cache),
            'is_running': self.is_running
        }
    
    def get_latency_history(self, limit: int = 100) -> List[float]:
        """Obtiene el historial de latencias"""
        return list(self.latency_history)[-limit:]
    
    async def benchmark_latency(self, operations: int = 100) -> Dict[str, Any]:
        """Ejecuta un benchmark de latencia"""
        logger.info(f"Iniciando benchmark de latencia con {operations} operaciones...")
        
        latencies = []
        successes = 0
        
        for i in range(operations):
            start_time = time.time()
            
            try:
                # Simular operación de trading
                await self.get_order_book_optimized('BTCUSDT')
                
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)
                successes += 1
                
            except Exception as e:
                logger.error(f"Error en benchmark {i}: {e}")
        
        if latencies:
            return {
                'operations': operations,
                'successful_operations': successes,
                'success_rate': successes / operations,
                'avg_latency_ms': np.mean(latencies),
                'min_latency_ms': np.min(latencies),
                'max_latency_ms': np.max(latencies),
                'p50_latency_ms': np.percentile(latencies, 50),
                'p95_latency_ms': np.percentile(latencies, 95),
                'p99_latency_ms': np.percentile(latencies, 99),
                'std_latency_ms': np.std(latencies)
            }
        else:
            return {
                'operations': operations,
                'successful_operations': 0,
                'success_rate': 0,
                'error': 'No se pudieron completar operaciones'
            }
