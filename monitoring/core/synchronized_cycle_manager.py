"""
monitoring/core/synchronized_cycle_manager.py
Gestor de ciclos sincronizados que procesa todos los símbolos en paralelo
Ubicación: C:\TradingBot_v10\monitoring\core\synchronized_cycle_manager.py

Funcionalidades:
- Ciclos que procesan todos los símbolos simultáneamente
- Análisis cronológico sincronizado con timestamps alineados
- Decisiones paralelas por símbolo en el mismo instante
- Métricas consolidadas por ciclo multi-símbolo
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class SynchronizedCycleMetrics:
    """Métricas de un ciclo sincronizado multi-símbolo"""
    cycle_id: str
    start_time: datetime
    end_time: datetime
    symbols: List[str]  # Lista de símbolos procesados
    initial_balance: float
    final_balance: float
    total_pnl: float
    daily_pnl: float
    pnl_percentage: float
    progress_to_target: float
    total_trades: int
    avg_win_rate: float
    max_drawdown: float
    avg_sharpe_ratio: float
    symbol_performance: Dict[str, Dict[str, Any]]  # Rendimiento por símbolo
    synchronized_timestamps: List[datetime]  # Timestamps sincronizados
    status: str  # 'completed', 'running', 'failed'
    parallel_decisions: int  # Número de decisiones paralelas tomadas

class SynchronizedCycleManager:
    """Gestor de ciclos sincronizados multi-símbolo"""
    
    def __init__(self, data_file: str = "data/synchronized_cycles.json"):
        self.data_file = data_file
        self.cycles: List[SynchronizedCycleMetrics] = []
        self.current_cycle = None
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        self.load_cycles()
        
        logger.info("SynchronizedCycleManager inicializado")
    
    def load_cycles(self):
        """Carga ciclos sincronizados históricos desde archivo"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.cycles = [SynchronizedCycleMetrics(**cycle) for cycle in data]
                logger.info(f"Cargados {len(self.cycles)} ciclos sincronizados históricos")
            else:
                self.cycles = []
                logger.info("No hay ciclos sincronizados históricos, iniciando desde cero")
        except Exception as e:
            logger.error(f"Error cargando ciclos sincronizados: {e}")
            self.cycles = []
    
    def save_cycles(self):
        """Guarda ciclos sincronizados en archivo"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            data = [cycle.__dict__ for cycle in self.cycles]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, default=str, indent=2)
            logger.info(f"Guardados {len(self.cycles)} ciclos sincronizados")
        except Exception as e:
            logger.error(f"Error guardando ciclos sincronizados: {e}")
    
    def start_synchronized_cycle(self, initial_balance: float = 1000.0) -> str:
        """Inicia un nuevo ciclo sincronizado multi-símbolo"""
        cycle_id = f"sync_cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_cycle = SynchronizedCycleMetrics(
            cycle_id=cycle_id,
            start_time=datetime.now(),
            end_time=None,
            symbols=self.symbols.copy(),
            initial_balance=initial_balance,
            final_balance=initial_balance,
            total_pnl=0.0,
            daily_pnl=0.0,
            pnl_percentage=0.0,
            progress_to_target=0.1,
            total_trades=0,
            avg_win_rate=0.0,
            max_drawdown=0.0,
            avg_sharpe_ratio=0.0,
            symbol_performance={},
            synchronized_timestamps=[],
            status='running',
            parallel_decisions=0
        )
        
        logger.info(f"Nuevo ciclo sincronizado iniciado: {cycle_id} con símbolos: {self.symbols}")
        return cycle_id
    
    def process_synchronized_timestamps(self, start_time: datetime, duration_days: int = 7) -> List[datetime]:
        """Genera timestamps sincronizados para análisis paralelo"""
        try:
            # Generar timestamps cada hora para análisis detallado
            timestamps = []
            current_time = start_time
            end_time = start_time + timedelta(days=duration_days)
            
            while current_time <= end_time:
                timestamps.append(current_time)
                current_time += timedelta(hours=1)
            
            return timestamps
            
        except Exception as e:
            logger.error(f"Error generando timestamps sincronizados: {e}")
            return []
    
    def analyze_symbol_at_timestamp(self, symbol: str, timestamp: datetime, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza un símbolo en un timestamp específico"""
        try:
            # Simular análisis de mercado para el símbolo en el timestamp
            base_price = market_data.get('price', 100000 if symbol == 'BTCUSDT' else 3400)
            volatility = market_data.get('volatility', 0.02)
            
            # Generar señal de trading basada en análisis técnico simulado
            signal_strength = np.random.uniform(0.3, 0.95)
            signal_direction = np.random.choice(['BUY', 'SELL', 'HOLD'], p=[0.4, 0.3, 0.3])
            
            # Calcular PnL potencial
            potential_pnl = 0.0
            if signal_direction != 'HOLD':
                price_change = np.random.normal(0, volatility) * base_price
                potential_pnl = price_change * 0.01  # 1% de la posición
            
            return {
                'symbol': symbol,
                'timestamp': timestamp,
                'price': base_price,
                'signal': signal_direction,
                'confidence': signal_strength,
                'potential_pnl': potential_pnl,
                'volatility': volatility,
                'volume': np.random.uniform(1000, 10000)
            }
            
        except Exception as e:
            logger.error(f"Error analizando símbolo {symbol} en {timestamp}: {e}")
            return {}
    
    def process_parallel_analysis(self, timestamps: List[datetime]) -> Dict[str, List[Dict[str, Any]]]:
        """Procesa análisis paralelo de todos los símbolos en timestamps sincronizados"""
        try:
            symbol_analyses = {symbol: [] for symbol in self.symbols}
            
            # Procesar cada timestamp con todos los símbolos en paralelo
            for timestamp in timestamps:
                # Generar datos de mercado base para el timestamp
                market_data = {
                    'price': np.random.uniform(90000, 120000),  # Precio base BTC
                    'volatility': np.random.uniform(0.01, 0.05),
                    'volume': np.random.uniform(5000, 15000)
                }
                
                # Analizar todos los símbolos en paralelo para este timestamp
                with ThreadPoolExecutor(max_workers=len(self.symbols)) as executor:
                    futures = {
                        executor.submit(self.analyze_symbol_at_timestamp, symbol, timestamp, market_data): symbol
                        for symbol in self.symbols
                    }
                    
                    for future in as_completed(futures):
                        symbol = futures[future]
                        try:
                            analysis = future.result()
                            if analysis:
                                symbol_analyses[symbol].append(analysis)
                        except Exception as e:
                            logger.error(f"Error en análisis paralelo para {symbol}: {e}")
            
            return symbol_analyses
            
        except Exception as e:
            logger.error(f"Error en análisis paralelo: {e}")
            return {}
    
    def consolidate_cycle_metrics(self, symbol_analyses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Consolida métricas del ciclo a partir de análisis paralelos"""
        try:
            total_trades = 0
            total_pnl = 0.0
            win_rates = []
            sharpe_ratios = []
            symbol_performance = {}
            
            for symbol, analyses in symbol_analyses.items():
                if not analyses:
                    continue
                
                # Calcular métricas por símbolo
                symbol_trades = len([a for a in analyses if a.get('signal') != 'HOLD'])
                symbol_pnl = sum([a.get('potential_pnl', 0) for a in analyses])
                symbol_wins = len([a for a in analyses if a.get('potential_pnl', 0) > 0])
                symbol_win_rate = symbol_wins / symbol_trades if symbol_trades > 0 else 0
                
                # Calcular Sharpe ratio simulado
                pnl_series = [a.get('potential_pnl', 0) for a in analyses]
                if len(pnl_series) > 1:
                    sharpe = np.mean(pnl_series) / np.std(pnl_series) if np.std(pnl_series) > 0 else 0
                else:
                    sharpe = 0
                
                symbol_performance[symbol] = {
                    'trades': symbol_trades,
                    'pnl': symbol_pnl,
                    'win_rate': symbol_win_rate,
                    'sharpe_ratio': sharpe,
                    'avg_confidence': np.mean([a.get('confidence', 0) for a in analyses])
                }
                
                total_trades += symbol_trades
                total_pnl += symbol_pnl
                win_rates.append(symbol_win_rate)
                sharpe_ratios.append(sharpe)
            
            # Calcular métricas consolidadas
            avg_win_rate = np.mean(win_rates) if win_rates else 0
            avg_sharpe_ratio = np.mean(sharpe_ratios) if sharpe_ratios else 0
            daily_pnl = total_pnl / 7  # PnL promedio diario para ciclo de 7 días
            
            return {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'daily_pnl': daily_pnl,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe_ratio,
                'symbol_performance': symbol_performance,
                'parallel_decisions': total_trades
            }
            
        except Exception as e:
            logger.error(f"Error consolidando métricas del ciclo: {e}")
            return {}
    
    def end_synchronized_cycle(self, cycle_id: str, consolidated_metrics: Dict[str, Any] = None):
        """Finaliza un ciclo sincronizado"""
        try:
            cycle = next((c for c in self.cycles if c.cycle_id == cycle_id), None)
            if not cycle:
                if self.current_cycle and self.current_cycle.cycle_id == cycle_id:
                    cycle = self.current_cycle
                else:
                    logger.warning(f"Ciclo sincronizado {cycle_id} no encontrado")
                    return
            
            # Actualizar métricas consolidadas
            if consolidated_metrics:
                cycle.total_trades = consolidated_metrics.get('total_trades', 0)
                cycle.total_pnl = consolidated_metrics.get('total_pnl', 0)
                cycle.daily_pnl = consolidated_metrics.get('daily_pnl', 0)
                cycle.avg_win_rate = consolidated_metrics.get('avg_win_rate', 0)
                cycle.avg_sharpe_ratio = consolidated_metrics.get('avg_sharpe_ratio', 0)
                cycle.symbol_performance = consolidated_metrics.get('symbol_performance', {})
                cycle.parallel_decisions = consolidated_metrics.get('parallel_decisions', 0)
            
            cycle.final_balance = cycle.initial_balance + cycle.total_pnl
            cycle.pnl_percentage = (cycle.total_pnl / cycle.initial_balance) * 100
            cycle.progress_to_target = (cycle.final_balance / 1000000.0) * 100
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
            
            logger.info(f"Ciclo sincronizado {cycle_id} finalizado exitosamente")
            
        except Exception as e:
            logger.error(f"Error finalizando ciclo sincronizado {cycle_id}: {e}")
    
    def get_top_synchronized_cycles(self, limit: int = 10, metric: str = 'final_balance') -> List[SynchronizedCycleMetrics]:
        """Obtiene los top N ciclos sincronizados según una métrica"""
        try:
            if not self.cycles:
                return []
            
            # Filtrar solo ciclos completados
            completed_cycles = [c for c in self.cycles if c.status == 'completed']
            
            if not completed_cycles:
                return []
            
            # Ordenar por métrica especificada
            if metric == 'final_balance':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.final_balance, reverse=True)
            elif metric == 'win_rate':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.avg_win_rate, reverse=True)
            elif metric == 'trades_count':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.total_trades, reverse=True)
            elif metric == 'progress_to_target':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.progress_to_target, reverse=True)
            elif metric == 'daily_pnl':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.daily_pnl, reverse=True)
            elif metric == 'sharpe_ratio':
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.avg_sharpe_ratio, reverse=True)
            else:
                sorted_cycles = sorted(completed_cycles, key=lambda x: x.final_balance, reverse=True)
            
            return sorted_cycles[:limit]
            
        except Exception as e:
            logger.error(f"Error obteniendo top ciclos sincronizados: {e}")
            return []
    
    def generate_sample_synchronized_cycles(self, count: int = 15):
        """Genera ciclos sincronizados de ejemplo para testing"""
        try:
            for i in range(count):
                start_time = datetime.now() - timedelta(days=np.random.randint(1, 90))
                duration = timedelta(days=np.random.randint(5, 14))
                
                # Generar métricas consolidadas más realistas
                initial_balance = 1000.0
                
                # PnL total más realista para ciclo multi-símbolo
                total_pnl = np.random.normal(200, 500)  # PnL promedio $200, std $500
                if np.random.random() < 0.25:  # 25% de probabilidad de pérdida
                    total_pnl = np.random.uniform(-300, 0)
                
                final_balance = initial_balance + total_pnl
                daily_pnl = total_pnl / duration.days
                
                # Generar rendimiento por símbolo
                symbol_performance = {}
                for symbol in self.symbols:
                    symbol_pnl = total_pnl / len(self.symbols) + np.random.normal(0, 50)
                    symbol_trades = np.random.randint(5, 20)
                    symbol_wins = int(symbol_trades * np.random.uniform(0.4, 0.8))
                    
                    symbol_performance[symbol] = {
                        'trades': symbol_trades,
                        'pnl': symbol_pnl,
                        'win_rate': symbol_wins / symbol_trades,
                        'sharpe_ratio': np.random.uniform(0.5, 2.0),
                        'avg_confidence': np.random.uniform(0.6, 0.9)
                    }
                
                cycle = SynchronizedCycleMetrics(
                    cycle_id=f"sample_sync_cycle_{i+1:03d}",
                    start_time=start_time,
                    end_time=start_time + duration,
                    symbols=self.symbols.copy(),
                    initial_balance=initial_balance,
                    final_balance=final_balance,
                    total_pnl=total_pnl,
                    daily_pnl=daily_pnl,
                    pnl_percentage=(total_pnl / initial_balance) * 100,
                    progress_to_target=(final_balance / 1000000.0) * 100,
                    total_trades=sum([sp['trades'] for sp in symbol_performance.values()]),
                    avg_win_rate=np.mean([sp['win_rate'] for sp in symbol_performance.values()]),
                    max_drawdown=np.random.uniform(0.05, 0.25),
                    avg_sharpe_ratio=np.mean([sp['sharpe_ratio'] for sp in symbol_performance.values()]),
                    symbol_performance=symbol_performance,
                    synchronized_timestamps=[],
                    status='completed',
                    parallel_decisions=sum([sp['trades'] for sp in symbol_performance.values()])
                )
                
                self.cycles.append(cycle)
            
            self.save_cycles()
            logger.info(f"Generados {count} ciclos sincronizados de ejemplo")
            
        except Exception as e:
            logger.error(f"Error generando ciclos sincronizados de ejemplo: {e}")

# Instancia global del gestor de ciclos sincronizados
synchronized_cycle_manager = SynchronizedCycleManager()
