# Ruta: core/sync/parallel_executor.py
"""
Ejecutor Paralelo Enterprise - Sistema de Trading
Ejecuta agentes en paralelo con delays controlados y métricas avanzadas
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json
import psutil
import threading
from queue import Queue, Empty
import redis
from prometheus_client import Counter, Gauge, Histogram
from control.telegram_bot import telegram_bot

logger = logging.getLogger(__name__)

# Prometheus metrics
execution_cycles_total = Counter('execution_cycles_total', 'Total execution cycles', ['symbol', 'timeframe'])
execution_time_histogram = Histogram('execution_cycle_time_seconds', 'Execution cycle time', ['symbol', 'timeframe'])
pnl_gauge = Gauge('execution_pnl', 'PnL per cycle', ['symbol', 'timeframe'])
trades_total = Counter('execution_trades_total', 'Total trades executed', ['symbol', 'timeframe'])

@dataclass
class ExecutionMetrics:
    """Métricas de ejecución enterprise"""
    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    total_execution_time: float
    avg_cycle_time: float
    max_cycle_time: float
    min_cycle_time: float
    total_trades: int
    total_pnl: float
    win_rate: float
    memory_peak_mb: float
    cpu_usage_avg: float
    api_calls_made: int
    api_errors: int
    cache_hit_rate: float

@dataclass
class CycleResult:
    """Resultado de un ciclo de ejecución"""
    cycle_id: str
    timestamp: int
    symbol: str
    timeframe: str
    execution_time: float
    pnl: float
    trades_count: int
    win_rate: float
    strategy_used: str
    status: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class ParallelExecutor:
    """Ejecutor paralelo enterprise con control de concurrencia y métricas"""
    
    def __init__(self, max_workers: int = 4, delay_ms: int = 100):
        self.max_workers = max_workers
        self.delay_ms = delay_ms
        self.execution_queue = Queue()
        self.results_queue = Queue()
        self.metrics = ExecutionMetrics(0, 0, 0, 0, 0, 0, float('inf'), 0, 0, 0, 0, 0, 0, 0, 0)
        self.running = False
        self.performance_monitor = None
        self.lock = threading.Lock()
        self.total_tasks = 0
        self.current_progress = 0
        self.progress_lock = threading.Lock()
        self.redis_client = None
        self.cache_hits = 0
        self.cache_misses = 0
        self._setup_redis()
        
        logger.info(f"ParallelExecutor inicializado con {max_workers} workers, delay {delay_ms}ms")
    
    def _setup_redis(self):
        """Configura Redis para caching de resultados"""
        try:
            redis_url = 'redis://localhost:6379'
            self.redis_client = redis.Redis.from_url(redis_url)
            logger.info("Conexión a Redis establecida para caching")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
    
    async def execute_agents_parallel(self, 
                                    timeline: pd.DataFrame, 
                                    symbols: List[str], 
                                    timeframes: List[str],
                                    agent_function: Callable = None) -> Dict[str, Any]:
        """
        Ejecuta agentes en paralelo con delays controlados
        
        Args:
            timeline: Timeline maestro con timestamps
            symbols: Lista de símbolos
            timeframes: Lista de timeframes
            agent_function: Función de agente a ejecutar
            
        Returns:
            Dict con resultados y métricas
        """
        try:
            self.running = True
            self.total_tasks = len(symbols) * len(timeframes)
            self.current_progress = 0
            results = []
            
            # Iniciar monitoreo de rendimiento
            self.performance_monitor = threading.Thread(target=self._monitor_performance)
            self.performance_monitor.start()
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for symbol in symbols:
                    for timeframe in timeframes:
                        # Verificar cache
                        if self.redis_client:
                            cache_key = f"cycle_result_{symbol}_{timeframe}_{timeline['timestamp'].iloc[-1]}"
                            cached_result = self.redis_client.get(cache_key)
                            if cached_result:
                                self.cache_hits += 1
                                results.append(CycleResult(**json.loads(cached_result)))
                                continue
                            self.cache_misses += 1
                        
                        futures.append(executor.submit(self._execute_cycle, symbol, timeframe, timeline, agent_function))
                        await asyncio.sleep(self.delay_ms / 1000.0)
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        self.results_queue.put(result)
                        
                        # Actualizar métricas Prometheus
                        execution_cycles_total.labels(symbol=result.symbol, timeframe=result.timeframe).inc()
                        execution_time_histogram.labels(symbol=result.symbol, timeframe=result.timeframe).observe(result.execution_time)
                        pnl_gauge.labels(symbol=result.symbol, timeframe=result.timeframe).set(result.pnl)
                        trades_total.labels(symbol=result.symbol, timeframe=result.timeframe).inc(result.trades_count)
                        
                        # Cachear resultado
                        if self.redis_client:
                            cache_key = f"cycle_result_{result.symbol}_{result.timeframe}_{result.timestamp}"
                            self.redis_client.setex(cache_key, 3600, json.dumps(asdict(result)))
                        
                        with self.progress_lock:
                            self.current_progress += 1
                            progress_pct = (self.current_progress / self.total_tasks) * 100
                            logger.info(f"Progreso: {progress_pct:.1f}% ({self.current_progress}/{self.total_tasks})")
                    
                    except Exception as e:
                        logger.error(f"Error en ciclo: {e}")
                        self.metrics.failed_cycles += 1
                        self.metrics.api_errors += 1
                
                await self._update_metrics(results)
            
            # Enviar recomendaciones via Telegram
            recommendations = self._generate_recommendations()
            for rec in recommendations:
                await telegram_bot.send_message(f"📊 Recomendación: {rec}")
            
            return await self._generate_summary(results)
            
        except Exception as e:
            logger.error(f"Error en ejecución paralela: {e}")
            self.metrics.failed_cycles += 1
            return {'status': 'error', 'message': str(e)}
        finally:
            self.running = False
    
    def _execute_cycle(self, symbol: str, timeframe: str, timeline: pd.DataFrame, agent_function: Callable) -> CycleResult:
        """Ejecuta un ciclo de trading para un símbolo y timeframe"""
        try:
            start_time = time.time()
            cycle_id = f"{symbol}_{timeframe}_{int(time.time())}"
            
            # Ejecutar agente
            result = agent_function(symbol, timeframe, timeline) if agent_function else {'pnl': 0, 'trades': 0, 'win_rate': 0, 'strategy': 'default'}
            
            execution_time = time.time() - start_time
            status = 'success' if result.get('success', True) else 'failed'
            
            cycle_result = CycleResult(
                cycle_id=cycle_id,
                timestamp=int(time.time()),
                symbol=symbol,
                timeframe=timeframe,
                execution_time=execution_time,
                pnl=result.get('pnl', 0.0),
                trades_count=result.get('trades', 0),
                win_rate=result.get('win_rate', 0.0),
                strategy_used=result.get('strategy', 'default'),
                status=status,
                error_message=result.get('error', None),
                metadata=result.get('metadata', {})
            )
            
            with self.lock:
                self.metrics.total_cycles += 1
                if status == 'success':
                    self.metrics.successful_cycles += 1
                else:
                    self.metrics.failed_cycles += 1
                self.metrics.total_execution_time += execution_time
                self.metrics.avg_cycle_time = self.metrics.total_execution_time / self.metrics.total_cycles
                self.metrics.max_cycle_time = max(self.metrics.max_cycle_time, execution_time)
                self.metrics.min_cycle_time = min(self.metrics.min_cycle_time, execution_time)
                self.metrics.total_trades += result.get('trades', 0)
                self.metrics.total_pnl += result.get('pnl', 0.0)
                self.metrics.win_rate = (self.metrics.total_trades / self.metrics.successful_cycles) if self.metrics.successful_cycles > 0 else 0.0
                self.metrics.api_calls_made += result.get('api_calls', 0)
                self.metrics.api_errors += 1 if result.get('error') else 0
            
            return cycle_result
            
        except Exception as e:
            logger.error(f"Error ejecutando ciclo {symbol}/{timeframe}: {e}")
            return CycleResult(
                cycle_id=cycle_id,
                timestamp=int(time.time()),
                symbol=symbol,
                timeframe=timeframe,
                execution_time=time.time() - start_time,
                pnl=0.0,
                trades_count=0,
                win_rate=0.0,
                strategy_used='default',
                status='failed',
                error_message=str(e)
            )
    
    def _monitor_performance(self):
        """Monitorea uso de recursos"""
        cpu_usages = []
        memory_peak = 0
        while self.running:
            try:
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                cpu_usages.append(cpu_usage)
                memory_peak = max(memory_peak, memory_usage)
                
                with self.lock:
                    self.metrics.cpu_usage_avg = np.mean(cpu_usages) if cpu_usages else 0
                    self.metrics.memory_peak_mb = memory_peak
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error en monitoreo de rendimiento: {e}")
    
    async def _update_metrics(self, results: List[CycleResult]):
        """Actualiza métricas basadas en resultados"""
        with self.lock:
            self.metrics.cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
    
    async def _generate_summary(self, results: List[CycleResult]) -> Dict[str, Any]:
        """Genera resumen de ejecución"""
        try:
            if not results:
                return {'status': 'no_results', 'results': []}
            
            best_cycle = max(results, key=lambda x: x.pnl)
            worst_cycle = min(results, key=lambda x: x.pnl)
            
            return {
                'status': 'success',
                'total_cycles': len(results),
                'successful_cycles': sum(1 for r in results if r.status == 'success'),
                'failed_cycles': sum(1 for r in results if r.status == 'failed'),
                'total_pnl': sum(r.pnl for r in results),
                'total_trades': sum(r.trades_count for r in results),
                'avg_execution_time': np.mean([r.execution_time for r in results]) if results else 0,
                'win_rate': np.mean([r.win_rate for r in results if r.trades_count > 0]) if any(r.trades_count > 0 for r in results) else 0,
                'metrics': asdict(self.metrics),
                'best_cycle': {
                    'cycle_id': best_cycle.cycle_id,
                    'symbol': best_cycle.symbol,
                    'timeframe': best_cycle.timeframe,
                    'pnl': best_cycle.pnl,
                    'trades_count': best_cycle.trades_count
                },
                'worst_cycle': {
                    'cycle_id': worst_cycle.cycle_id,
                    'symbol': worst_cycle.symbol,
                    'timeframe': worst_cycle.timeframe,
                    'pnl': worst_cycle.pnl,
                    'trades_count': worst_cycle.trades_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en métricas"""
        try:
            recommendations = []
            
            if self.metrics.successful_cycles < self.metrics.total_cycles * 0.8:
                recommendations.append("🔧 Revisar configuración de agentes - tasa de éxito baja")
            
            if self.metrics.avg_cycle_time > 5.0:
                recommendations.append("⚡ Optimizar agentes - tiempo de ejecución alto")
            
            if self.metrics.win_rate < 50:
                recommendations.append("📊 Revisar estrategias - win rate bajo")
            
            if self.metrics.total_pnl < 0:
                recommendations.append("⚠️ Revisar parámetros de trading - PnL negativo")
            
            if self.metrics.memory_peak_mb > 1000:
                recommendations.append("💾 Considerar optimización de memoria")
            
            if self.metrics.cpu_usage_avg > 80:
                recommendations.append("🖥️ Reducir carga de CPU o aumentar workers")
            
            if not recommendations:
                recommendations.append("✅ Rendimiento óptimo - no se requieren cambios")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return ["❌ Error generando recomendaciones"]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas actuales"""
        with self.lock:
            return asdict(self.metrics)
    
    def stop_execution(self):
        """Detiene la ejecución"""
        self.running = False
        if self.performance_monitor:
            self.performance_monitor.join(timeout=1)