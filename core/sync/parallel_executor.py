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
from datetime import datetime, timezone
import json
import psutil
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)

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
        self.metrics = ExecutionMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.running = False
        self.performance_monitor = None
        self.lock = threading.Lock()
        
        # Propiedades para monitoreo de progreso
        self.total_tasks = 0
        self.current_progress = 0
        self.progress_lock = threading.Lock()
        
    async def execute_agents_parallel(self, 
                                    timeline: pd.DataFrame, 
                                    symbols: List[str], 
                                    timeframes: List[str],
                                    agent_function: Callable = None) -> Dict[str, Any]:
        """
        Ejecuta agentes en paralelo con delays controlados
        
        Args:
            timeline: Timeline maestro con timestamps
            symbols: Lista de símbolos a procesar
            timeframes: Lista de timeframes
            agent_function: Función del agente a ejecutar
            
        Returns:
            Dict con resultados de ejecución
        """
        start_time = time.time()
        logger.info(f"🚀 Iniciando ejecución paralela enterprise")
        logger.info(f"📊 Símbolos: {len(symbols)}, Timeframes: {len(timeframes)}")
        logger.info(f"⏱️ Delay entre operaciones: {self.delay_ms}ms")
        
        try:
            # Inicializar métricas
            self.metrics = ExecutionMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            self.running = True
            
            # Iniciar monitor de rendimiento
            self.performance_monitor = threading.Thread(target=self._monitor_performance)
            self.performance_monitor.start()
            
            # Crear tareas de ejecución
            execution_tasks = []
            cycle_results = []
            
            # Procesar cada timestamp del timeline
            for idx, row in timeline.iterrows():
                timestamp = row['timestamp'] if 'timestamp' in row else idx
                
                # Crear tareas para cada combinación símbolo-timeframe
                for symbol in symbols:
                    for timeframe in timeframes:
                        task = {
                            'cycle_id': f"{symbol}_{timeframe}_{timestamp}",
                            'timestamp': timestamp,
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'agent_function': agent_function
                        }
                        execution_tasks.append(task)
            
            logger.info(f"📋 Creadas {len(execution_tasks)} tareas de ejecución")
            
            # Configurar progreso
            with self.progress_lock:
                self.total_tasks = len(execution_tasks)
                self.current_progress = 0
            
            # Ejecutar tareas en paralelo con control de concurrencia
            cycle_results = await self._execute_tasks_with_delay(execution_tasks)
            
            # Calcular métricas finales
            self.metrics.total_execution_time = time.time() - start_time
            self.metrics.total_cycles = len(cycle_results)
            self.metrics.successful_cycles = sum(1 for r in cycle_results if r.status == 'success')
            self.metrics.failed_cycles = self.metrics.total_cycles - self.metrics.successful_cycles
            
            # Calcular métricas de trading
            self._calculate_trading_metrics(cycle_results)
            
            # Detener monitor de rendimiento
            self.running = False
            if self.performance_monitor:
                self.performance_monitor.join(timeout=1)
            
            result = {
                'status': 'success',
                'execution_metrics': asdict(self.metrics),
                'cycle_results': [asdict(r) for r in cycle_results],
                'summary': self._generate_execution_summary(cycle_results),
                'recommendations': self._generate_recommendations(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Ejecución paralela completada en {self.metrics.total_execution_time:.2f}s")
            logger.info(f"📊 Ciclos exitosos: {self.metrics.successful_cycles}/{self.metrics.total_cycles}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en ejecución paralela: {e}")
            self.running = False
            return {
                'status': 'error',
                'message': str(e),
                'execution_metrics': asdict(self.metrics),
                'cycle_results': [],
                'summary': {},
                'recommendations': ["❌ Error crítico en ejecución"]
            }
    
    async def _execute_tasks_with_delay(self, tasks: List[Dict[str, Any]]) -> List[CycleResult]:
        """Ejecuta tareas con delay controlado entre operaciones"""
        try:
            cycle_results = []
            completed_tasks = 0
            
            # Usar ThreadPoolExecutor para control de concurrencia
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Crear futures para todas las tareas
                future_to_task = {}
                
                for task in tasks:
                    future = executor.submit(self._execute_single_cycle, task)
                    future_to_task[future] = task
                
                # Procesar resultados con delay
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    
                    try:
                        result = future.result()
                        cycle_results.append(result)
                        completed_tasks += 1
                        
                        # Actualizar progreso para monitoreo
                        with self.progress_lock:
                            self.current_progress = completed_tasks
                        
                        # Log de progreso
                        if completed_tasks % 10 == 0:
                            logger.info(f"📈 Progreso: {completed_tasks}/{len(tasks)} tareas completadas")
                        
                        # Delay de 100ms para evitar conflictos con API
                        await asyncio.sleep(self.delay_ms / 1000.0)
                        
                    except Exception as e:
                        logger.error(f"❌ Error en tarea {task['cycle_id']}: {e}")
                        cycle_results.append(CycleResult(
                            cycle_id=task['cycle_id'],
                            timestamp=task['timestamp'],
                            symbol=task['symbol'],
                            timeframe=task['timeframe'],
                            execution_time=0,
                            pnl=0,
                            trades_count=0,
                            win_rate=0,
                            strategy_used='error',
                            status='error',
                            error_message=str(e)
                        ))
            
            return cycle_results
            
        except Exception as e:
            logger.error(f"Error ejecutando tareas con delay: {e}")
            return []
    
    def _execute_single_cycle(self, task: Dict[str, Any]) -> CycleResult:
        """Ejecuta un solo ciclo de trading"""
        start_time = time.time()
        
        try:
            cycle_id = task['cycle_id']
            timestamp = task['timestamp']
            symbol = task['symbol']
            timeframe = task['timeframe']
            agent_function = task.get('agent_function')
            
            # Simular ejecución del agente (placeholder)
            # En implementación real, aquí se llamaría a la función del agente
            if agent_function:
                result = agent_function(symbol, timeframe, timestamp)
            else:
                # Simulación básica para testing
                result = self._simulate_agent_execution(symbol, timeframe, timestamp)
            
            execution_time = time.time() - start_time
            
            return CycleResult(
                cycle_id=cycle_id,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                execution_time=execution_time,
                pnl=result.get('pnl', 0.0),
                trades_count=result.get('trades_count', 0),
                win_rate=result.get('win_rate', 0.0),
                strategy_used=result.get('strategy_used', 'default'),
                status='success',
                metadata=result.get('metadata', {})
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error ejecutando ciclo {task['cycle_id']}: {e}")
            
            return CycleResult(
                cycle_id=task['cycle_id'],
                timestamp=task['timestamp'],
                symbol=task['symbol'],
                timeframe=task['timeframe'],
                execution_time=execution_time,
                pnl=0.0,
                trades_count=0,
                win_rate=0.0,
                strategy_used='error',
                status='error',
                error_message=str(e)
            )
    
    def _simulate_agent_execution(self, symbol: str, timeframe: str, timestamp: int) -> Dict[str, Any]:
        """Simula ejecución de agente para testing"""
        import random
        
        # Simulación básica de resultados
        pnl = random.uniform(-100, 200)
        trades_count = random.randint(0, 5)
        win_rate = random.uniform(0.3, 0.8)
        
        return {
            'pnl': pnl,
            'trades_count': trades_count,
            'win_rate': win_rate,
            'strategy_used': f'strategy_{random.randint(1, 3)}',
            'metadata': {
                'confidence': random.uniform(0.5, 0.95),
                'market_condition': random.choice(['bull', 'bear', 'sideways']),
                'volatility': random.uniform(0.1, 0.5)
            }
        }
    
    def _calculate_trading_metrics(self, cycle_results: List[CycleResult]):
        """Calcula métricas de trading"""
        try:
            if not cycle_results:
                return
            
            # Métricas de tiempo
            execution_times = [r.execution_time for r in cycle_results if r.status == 'success']
            if execution_times:
                self.metrics.avg_cycle_time = sum(execution_times) / len(execution_times)
                self.metrics.max_cycle_time = max(execution_times)
                self.metrics.min_cycle_time = min(execution_times)
            
            # Métricas de trading
            successful_results = [r for r in cycle_results if r.status == 'success']
            if successful_results:
                self.metrics.total_trades = sum(r.trades_count for r in successful_results)
                self.metrics.total_pnl = sum(r.pnl for r in successful_results)
                
                # Calcular win rate general
                winning_cycles = sum(1 for r in successful_results if r.pnl > 0)
                self.metrics.win_rate = (winning_cycles / len(successful_results) * 100) if successful_results else 0
            
        except Exception as e:
            logger.error(f"Error calculando métricas de trading: {e}")
    
    def _monitor_performance(self):
        """Monitor de rendimiento en tiempo real"""
        try:
            cpu_usage = []
            memory_usage = []
            
            while self.running:
                try:
                    # Monitorear CPU y memoria
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_info = psutil.virtual_memory()
                    
                    cpu_usage.append(cpu_percent)
                    memory_usage.append(memory_info.used / (1024 * 1024))  # MB
                    
                    # Actualizar métricas
                    with self.lock:
                        if cpu_usage:
                            self.metrics.cpu_usage_avg = sum(cpu_usage) / len(cpu_usage)
                        if memory_usage:
                            self.metrics.memory_peak_mb = max(memory_usage)
                    
                    time.sleep(1)  # Monitorear cada segundo
                    
                except Exception as e:
                    logger.debug(f"Error en monitor de rendimiento: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error en monitor de rendimiento: {e}")
    
    def _generate_execution_summary(self, cycle_results: List[CycleResult]) -> Dict[str, Any]:
        """Genera resumen de ejecución"""
        try:
            successful_results = [r for r in cycle_results if r.status == 'success']
            
            if not successful_results:
                return {
                    'total_cycles': len(cycle_results),
                    'successful_cycles': 0,
                    'success_rate': 0,
                    'total_pnl': 0,
                    'total_trades': 0,
                    'avg_pnl_per_cycle': 0,
                    'best_cycle': None,
                    'worst_cycle': None
                }
            
            # Calcular métricas
            total_pnl = sum(r.pnl for r in successful_results)
            total_trades = sum(r.trades_count for r in successful_results)
            avg_pnl_per_cycle = total_pnl / len(successful_results)
            
            # Encontrar mejor y peor ciclo
            best_cycle = max(successful_results, key=lambda x: x.pnl)
            worst_cycle = min(successful_results, key=lambda x: x.pnl)
            
            return {
                'total_cycles': len(cycle_results),
                'successful_cycles': len(successful_results),
                'success_rate': len(successful_results) / len(cycle_results) * 100,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'avg_pnl_per_cycle': avg_pnl_per_cycle,
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
            return {}
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en métricas"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en éxito
            if self.metrics.successful_cycles < self.metrics.total_cycles * 0.8:
                recommendations.append("🔧 Revisar configuración de agentes - tasa de éxito baja")
            
            # Recomendaciones basadas en rendimiento
            if self.metrics.avg_cycle_time > 5.0:
                recommendations.append("⚡ Optimizar agentes - tiempo de ejecución alto")
            
            # Recomendaciones basadas en trading
            if self.metrics.win_rate < 50:
                recommendations.append("📊 Revisar estrategias - win rate bajo")
            
            if self.metrics.total_pnl < 0:
                recommendations.append("⚠️ Revisar parámetros de trading - PnL negativo")
            
            # Recomendaciones basadas en recursos
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
