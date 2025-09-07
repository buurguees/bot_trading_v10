"""
monitoring/cycle_tracker.py
Sistema de seguimiento de ciclos cronológicos del bot de trading
Ubicación: C:\TradingBot_v10\monitoring\cycle_tracker.py

Funcionalidades:
- Seguimiento de ciclos de entrenamiento y trading
- Métricas de rendimiento por ciclo
- Top 10 ciclos con mejor PnL diario
- Progreso hacia objetivo por ciclo
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging
from dataclasses import dataclass
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class CycleMetrics:
    """Métricas de un ciclo cronológico"""
    cycle_id: str
    start_time: datetime
    end_time: datetime
    symbol: str
    initial_balance: float
    final_balance: float
    daily_pnl: float
    total_pnl: float
    pnl_percentage: float
    progress_to_target: float
    trades_count: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    status: str  # 'completed', 'running', 'failed'

class CycleTracker:
    """Rastreador de ciclos cronológicos del bot"""
    
    def __init__(self, data_file: str = "data/cycles_history.json"):
        self.data_file = data_file
        self.cycles: List[CycleMetrics] = []
        self.current_cycle = None
        self.load_cycles()
        
        logger.info("CycleTracker inicializado")
    
    def load_cycles(self):
        """Carga ciclos históricos desde archivo"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.cycles = [CycleMetrics(**cycle) for cycle in data]
                logger.info(f"Cargados {len(self.cycles)} ciclos históricos")
            else:
                self.cycles = []
                logger.info("No hay ciclos históricos, iniciando desde cero")
        except Exception as e:
            logger.error(f"Error cargando ciclos: {e}")
            self.cycles = []
    
    def save_cycles(self):
        """Guarda ciclos en archivo"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            data = [cycle.__dict__ for cycle in self.cycles]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, default=str, indent=2)
            logger.info(f"Guardados {len(self.cycles)} ciclos")
        except Exception as e:
            logger.error(f"Error guardando ciclos: {e}")
    
    def start_new_cycle(self, symbol: str, initial_balance: float = 1000.0) -> str:
        """Inicia un nuevo ciclo cronológico"""
        cycle_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"
        
        self.current_cycle = CycleMetrics(
            cycle_id=cycle_id,
            start_time=datetime.now(),
            end_time=None,
            symbol=symbol,
            initial_balance=initial_balance,
            final_balance=initial_balance,
            daily_pnl=0.0,
            total_pnl=0.0,
            pnl_percentage=0.0,
            progress_to_target=0.1,  # 0.1% inicial
            trades_count=0,
            win_rate=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            status='running'
        )
        
        logger.info(f"Nuevo ciclo iniciado: {cycle_id}")
        return cycle_id
    
    def update_cycle_metrics(self, cycle_id: str, metrics: Dict[str, Any]):
        """Actualiza métricas de un ciclo en curso"""
        try:
            cycle = next((c for c in self.cycles if c.cycle_id == cycle_id), None)
            if not cycle:
                # Buscar en ciclo actual
                if self.current_cycle and self.current_cycle.cycle_id == cycle_id:
                    cycle = self.current_cycle
                else:
                    logger.warning(f"Ciclo {cycle_id} no encontrado")
                    return
            
            # Actualizar métricas
            cycle.final_balance = metrics.get('current_balance', cycle.final_balance)
            cycle.daily_pnl = metrics.get('daily_pnl', cycle.daily_pnl)
            cycle.total_pnl = cycle.final_balance - cycle.initial_balance
            cycle.pnl_percentage = (cycle.total_pnl / cycle.initial_balance) * 100
            cycle.progress_to_target = (cycle.final_balance / 1000000.0) * 100
            cycle.trades_count = metrics.get('trades_count', cycle.trades_count)
            cycle.win_rate = metrics.get('win_rate', cycle.win_rate)
            cycle.max_drawdown = metrics.get('max_drawdown', cycle.max_drawdown)
            cycle.sharpe_ratio = metrics.get('sharpe_ratio', cycle.sharpe_ratio)
            
            # Si es el ciclo actual, actualizar también
            if self.current_cycle and self.current_cycle.cycle_id == cycle_id:
                self.current_cycle = cycle
            
            logger.debug(f"Ciclo {cycle_id} actualizado")
            
        except Exception as e:
            logger.error(f"Error actualizando ciclo {cycle_id}: {e}")
    
    def end_cycle(self, cycle_id: str, final_metrics: Dict[str, Any] = None):
        """Finaliza un ciclo cronológico"""
        try:
            cycle = next((c for c in self.cycles if c.cycle_id == cycle_id), None)
            if not cycle:
                if self.current_cycle and self.current_cycle.cycle_id == cycle_id:
                    cycle = self.current_cycle
                else:
                    logger.warning(f"Ciclo {cycle_id} no encontrado")
                    return
            
            # Actualizar métricas finales
            if final_metrics:
                self.update_cycle_metrics(cycle_id, final_metrics)
            
            cycle.end_time = datetime.now()
            cycle.status = 'completed'
            
            # Agregar a lista de ciclos si no está
            if cycle not in self.cycles:
                self.cycles.append(cycle)
            
            # Limpiar ciclo actual
            if self.current_cycle and self.current_cycle.cycle_id == cycle_id:
                self.current_cycle = None
            
            # Guardar
            self.save_cycles()
            
            logger.info(f"Ciclo {cycle_id} finalizado exitosamente")
            
        except Exception as e:
            logger.error(f"Error finalizando ciclo {cycle_id}: {e}")
    
    def get_top_cycles(self, limit: int = 10, metric: str = 'daily_pnl') -> List[CycleMetrics]:
        """Obtiene los top N ciclos según una métrica"""
        try:
            if not self.cycles:
                return []
            
            # Filtrar solo ciclos completados
            completed_cycles = [c for c in self.cycles if c.status == 'completed']
            
            if not completed_cycles:
                return []
            
            # Ordenar por métrica especificada
            if metric == 'daily_pnl':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.daily_pnl, reverse=True)
            elif metric == 'pnl_percentage':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.pnl_percentage, reverse=True)
            elif metric == 'progress_to_target':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.progress_to_target, reverse=True)
            elif metric == 'win_rate':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.win_rate, reverse=True)
            elif metric == 'sharpe_ratio':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.sharpe_ratio, reverse=True)
            else:
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.daily_pnl, reverse=True)
            
            return sorted_cycles[:limit]
            
        except Exception as e:
            logger.error(f"Error obteniendo top ciclos: {e}")
            return []
    
    def get_cycle_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de todos los ciclos"""
        try:
            if not self.cycles:
                return {
                    'total_cycles': 0,
                    'completed_cycles': 0,
                    'running_cycles': 0,
                    'avg_daily_pnl': 0.0,
                    'avg_progress': 0.0,
                    'best_daily_pnl': 0.0,
                    'best_progress': 0.0,
                    'total_pnl': 0.0
                }
            
            completed_cycles = [c for c in self.cycles if c.status == 'completed']
            running_cycles = [c for c in self.cycles if c.status == 'running']
            
            if not completed_cycles:
                return {
                    'total_cycles': len(self.cycles),
                    'completed_cycles': 0,
                    'running_cycles': len(running_cycles),
                    'avg_daily_pnl': 0.0,
                    'avg_progress': 0.0,
                    'best_daily_pnl': 0.0,
                    'best_progress': 0.0,
                    'total_pnl': 0.0
                }
            
            return {
                'total_cycles': len(self.cycles),
                'completed_cycles': len(completed_cycles),
                'running_cycles': len(running_cycles),
                'avg_daily_pnl': np.mean([c.daily_pnl for c in completed_cycles]),
                'avg_progress': np.mean([c.progress_to_target for c in completed_cycles]),
                'best_daily_pnl': max([c.daily_pnl for c in completed_cycles]),
                'best_progress': max([c.progress_to_target for c in completed_cycles]),
                'total_pnl': sum([c.total_pnl for c in completed_cycles])
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de ciclos: {e}")
            return {}
    
    def generate_sample_cycles(self, count: int = 20):
        """Genera ciclos de ejemplo para testing"""
        try:
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            
            for i in range(count):
                symbol = np.random.choice(symbols)
                start_time = datetime.now() - timedelta(days=np.random.randint(1, 365))
                duration = timedelta(hours=np.random.randint(1, 72))
                
                # Generar métricas realistas
                initial_balance = 1000.0
                daily_pnl = np.random.normal(50, 200)  # PnL promedio $50, std $200
                total_pnl = daily_pnl * np.random.randint(1, 10)  # Varios días
                final_balance = initial_balance + total_pnl
                
                cycle = CycleMetrics(
                    cycle_id=f"sample_cycle_{i+1:03d}_{symbol}",
                    start_time=start_time,
                    end_time=start_time + duration,
                    symbol=symbol,
                    initial_balance=initial_balance,
                    final_balance=final_balance,
                    daily_pnl=daily_pnl,
                    total_pnl=total_pnl,
                    pnl_percentage=(total_pnl / initial_balance) * 100,
                    progress_to_target=(final_balance / 1000000.0) * 100,
                    trades_count=np.random.randint(5, 50),
                    win_rate=np.random.uniform(0.3, 0.8),
                    max_drawdown=np.random.uniform(0.05, 0.25),
                    sharpe_ratio=np.random.uniform(0.5, 2.5),
                    status='completed'
                )
                
                self.cycles.append(cycle)
            
            self.save_cycles()
            logger.info(f"Generados {count} ciclos de ejemplo")
            
        except Exception as e:
            logger.error(f"Error generando ciclos de ejemplo: {e}")

# Instancia global del tracker
cycle_tracker = CycleTracker()
