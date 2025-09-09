# Ruta: core/monitoring/enterprise/pnl_tracker.py
#!/usr/bin/env python3
"""
Tracker de PnL Enterprise - Tiempo Real
======================================

Este módulo implementa seguimiento detallado de PnL con análisis
de performance por posición, símbolo y estrategia.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.core import CollectorRegistry

from core.trading.bitget_client import bitget_client
from core.config.config_loader import user_config

logger = logging.getLogger(__name__)

@dataclass
class PnLRecord:
    """Registro de PnL individual"""
    timestamp: datetime
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percentage: float
    duration_minutes: int
    strategy: str
    leverage: float
    fees: float
    net_pnl: float

@dataclass
class PnLSummary:
    """Resumen de PnL"""
    timestamp: datetime
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    total_fees: float
    net_pnl: float
    pnl_by_symbol: Dict[str, float]
    pnl_by_strategy: Dict[str, float]
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float

class PnLTracker:
    """Tracker de PnL enterprise en tiempo real"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = user_config.get_value(['pnl_tracking'], {})
        self.bitget_client = bitget_client
        
        # Métricas de Prometheus
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Estado del tracker
        self.is_running = False
        self.start_time = None
        self.last_summary = None
        self.pnl_records = []
        self.max_records = 50000
        
        # Configuración
        self.update_interval = self.config.get('update_interval', 10)  # segundos
        self.symbols = self.config.get('symbols', [])
        
        # Directorios
        self.setup_directories()
        
        logger.info("💰 PnLTracker enterprise inicializado")
    
    def _setup_prometheus_metrics(self):
        """Configura las métricas de Prometheus"""
        # Métricas de PnL total
        self.total_pnl_gauge = Gauge('pnl_total', 'Total PnL in USDT', registry=self.registry)
        self.realized_pnl_gauge = Gauge('pnl_realized', 'Realized PnL in USDT', registry=self.registry)
        self.unrealized_pnl_gauge = Gauge('pnl_unrealized', 'Unrealized PnL in USDT', registry=self.registry)
        self.net_pnl_gauge = Gauge('pnl_net', 'Net PnL in USDT', registry=self.registry)
        
        # Métricas de trades
        self.total_trades_gauge = Gauge('pnl_total_trades', 'Total number of trades', registry=self.registry)
        self.winning_trades_gauge = Gauge('pnl_winning_trades', 'Number of winning trades', registry=self.registry)
        self.losing_trades_gauge = Gauge('pnl_losing_trades', 'Number of losing trades', registry=self.registry)
        self.win_rate_gauge = Gauge('pnl_win_rate', 'Win rate percentage', registry=self.registry)
        
        # Métricas de performance
        self.avg_win_gauge = Gauge('pnl_avg_win', 'Average winning trade', registry=self.registry)
        self.avg_loss_gauge = Gauge('pnl_avg_loss', 'Average losing trade', registry=self.registry)
        self.largest_win_gauge = Gauge('pnl_largest_win', 'Largest winning trade', registry=self.registry)
        self.largest_loss_gauge = Gauge('pnl_largest_loss', 'Largest losing trade', registry=self.registry)
        self.profit_factor_gauge = Gauge('pnl_profit_factor', 'Profit factor', registry=self.registry)
        
        # Métricas de fees
        self.total_fees_gauge = Gauge('pnl_total_fees', 'Total fees paid', registry=self.registry)
        
        # Métricas por símbolo
        self.pnl_by_symbol_gauge = Gauge('pnl_by_symbol', 'PnL by symbol', ['symbol'], registry=self.registry)
        
        # Métricas por estrategia
        self.pnl_by_strategy_gauge = Gauge('pnl_by_strategy', 'PnL by strategy', ['strategy'], registry=self.registry)
        
        # Métricas temporales
        self.daily_pnl_gauge = Gauge('pnl_daily', 'Daily PnL', registry=self.registry)
        self.weekly_pnl_gauge = Gauge('pnl_weekly', 'Weekly PnL', registry=self.registry)
        self.monthly_pnl_gauge = Gauge('pnl_monthly', 'Monthly PnL', registry=self.registry)
        
        # Histogramas
        self.pnl_histogram = Histogram('pnl_distribution', 'PnL distribution', 
                                     buckets=[-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000], 
                                     registry=self.registry)
        
        self.trade_duration_histogram = Histogram('pnl_trade_duration_minutes', 'Trade duration in minutes',
                                                buckets=[1, 5, 10, 30, 60, 120, 240, 480, 720, 1440], 
                                                registry=self.registry)
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/pnl_tracking',
            'data/enterprise/pnl_tracking',
            'backups/enterprise/pnl_tracking'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Inicializa el tracker de PnL"""
        try:
            logger.info("🔧 Inicializando PnLTracker...")
            
            # Cargar historial de PnL
            await self.load_pnl_history()
            
            logger.info("✅ PnLTracker inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando PnLTracker: {e}")
            return False
    
    async def start_tracking(self):
        """Inicia el seguimiento de PnL"""
        try:
            logger.info("🚀 Iniciando seguimiento de PnL...")
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Loop principal de seguimiento
            while self.is_running:
                try:
                    # Recopilar métricas de PnL
                    summary = await self.collect_pnl_summary()
                    
                    # Actualizar métricas de Prometheus
                    self.update_prometheus_metrics(summary)
                    
                    # Guardar resumen
                    self.last_summary = summary
                    
                    # Guardar en archivo
                    await self.save_pnl_summary_to_file(summary)
                    
                    # Esperar antes de la siguiente actualización
                    await asyncio.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error en loop de seguimiento de PnL: {e}")
                    await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"❌ Error en seguimiento de PnL: {e}")
        finally:
            self.is_running = False
    
    async def collect_pnl_summary(self) -> PnLSummary:
        """Recopila resumen de PnL en tiempo real"""
        try:
            # Obtener posiciones actuales
            positions = await self.bitget_client.get_positions()
            
            # Calcular PnL total
            total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            realized_pnl = 0  # Se calcularía desde el historial de trades
            unrealized_pnl = total_pnl
            
            # Calcular métricas de trades
            total_trades = len(self.pnl_records)
            winning_trades = len([r for r in self.pnl_records if r.pnl > 0])
            losing_trades = len([r for r in self.pnl_records if r.pnl < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calcular métricas de performance
            if self.pnl_records:
                wins = [r.pnl for r in self.pnl_records if r.pnl > 0]
                losses = [r.pnl for r in self.pnl_records if r.pnl < 0]
                
                avg_win = np.mean(wins) if wins else 0
                avg_loss = np.mean(losses) if losses else 0
                largest_win = max(wins) if wins else 0
                largest_loss = min(losses) if losses else 0
                
                total_wins = sum(wins)
                total_losses = abs(sum(losses))
                profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            else:
                avg_win = avg_loss = largest_win = largest_loss = profit_factor = 0
            
            # Calcular fees totales
            total_fees = sum(r.fees for r in self.pnl_records)
            net_pnl = total_pnl - total_fees
            
            # Calcular PnL por símbolo
            pnl_by_symbol = {}
            for symbol in self.symbols:
                symbol_pnl = sum(r.pnl for r in self.pnl_records if r.symbol == symbol)
                pnl_by_symbol[symbol] = symbol_pnl
            
            # Calcular PnL por estrategia
            pnl_by_strategy = {}
            strategies = set(r.strategy for r in self.pnl_records)
            for strategy in strategies:
                strategy_pnl = sum(r.pnl for r in self.pnl_records if r.strategy == strategy)
                pnl_by_strategy[strategy] = strategy_pnl
            
            # Calcular PnL temporal
            daily_pnl = await self.calculate_daily_pnl()
            weekly_pnl = await self.calculate_weekly_pnl()
            monthly_pnl = await self.calculate_monthly_pnl()
            
            # Crear resumen
            summary = PnLSummary(
                timestamp=datetime.now(),
                total_pnl=total_pnl,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                profit_factor=profit_factor,
                total_fees=total_fees,
                net_pnl=net_pnl,
                pnl_by_symbol=pnl_by_symbol,
                pnl_by_strategy=pnl_by_strategy,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl,
                monthly_pnl=monthly_pnl
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error recopilando resumen de PnL: {e}")
            # Retornar resumen por defecto
            return PnLSummary(
                timestamp=datetime.now(),
                total_pnl=0, realized_pnl=0, unrealized_pnl=0,
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                avg_win=0, avg_loss=0, largest_win=0, largest_loss=0, profit_factor=0,
                total_fees=0, net_pnl=0, pnl_by_symbol={}, pnl_by_strategy={},
                daily_pnl=0, weekly_pnl=0, monthly_pnl=0
            )
    
    async def calculate_daily_pnl(self) -> float:
        """Calcula el PnL diario"""
        try:
            today = datetime.now().date()
            daily_records = [r for r in self.pnl_records if r.timestamp.date() == today]
            return sum(r.pnl for r in daily_records)
        except Exception as e:
            logger.error(f"Error calculando PnL diario: {e}")
            return 0.0
    
    async def calculate_weekly_pnl(self) -> float:
        """Calcula el PnL semanal"""
        try:
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            weekly_records = [r for r in self.pnl_records if r.timestamp.date() >= week_start]
            return sum(r.pnl for r in weekly_records)
        except Exception as e:
            logger.error(f"Error calculando PnL semanal: {e}")
            return 0.0
    
    async def calculate_monthly_pnl(self) -> float:
        """Calcula el PnL mensual"""
        try:
            today = datetime.now().date()
            month_start = today.replace(day=1)
            monthly_records = [r for r in self.pnl_records if r.timestamp.date() >= month_start]
            return sum(r.pnl for r in monthly_records)
        except Exception as e:
            logger.error(f"Error calculando PnL mensual: {e}")
            return 0.0
    
    def add_pnl_record(self, record: PnLRecord):
        """Añade un nuevo registro de PnL"""
        try:
            self.pnl_records.append(record)
            
            # Mantener solo los últimos registros
            if len(self.pnl_records) > self.max_records:
                self.pnl_records.pop(0)
            
            logger.info(f"💰 PnL registrado: {record.symbol} {record.side} ${record.pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error añadiendo registro de PnL: {e}")
    
    def update_prometheus_metrics(self, summary: PnLSummary):
        """Actualiza las métricas de Prometheus"""
        try:
            # PnL total
            self.total_pnl_gauge.set(summary.total_pnl)
            self.realized_pnl_gauge.set(summary.realized_pnl)
            self.unrealized_pnl_gauge.set(summary.unrealized_pnl)
            self.net_pnl_gauge.set(summary.net_pnl)
            
            # Trades
            self.total_trades_gauge.set(summary.total_trades)
            self.winning_trades_gauge.set(summary.winning_trades)
            self.losing_trades_gauge.set(summary.losing_trades)
            self.win_rate_gauge.set(summary.win_rate)
            
            # Performance
            self.avg_win_gauge.set(summary.avg_win)
            self.avg_loss_gauge.set(summary.avg_loss)
            self.largest_win_gauge.set(summary.largest_win)
            self.largest_loss_gauge.set(summary.largest_loss)
            self.profit_factor_gauge.set(summary.profit_factor)
            
            # Fees
            self.total_fees_gauge.set(summary.total_fees)
            
            # PnL por símbolo
            for symbol, pnl in summary.pnl_by_symbol.items():
                self.pnl_by_symbol_gauge.labels(symbol=symbol).set(pnl)
            
            # PnL por estrategia
            for strategy, pnl in summary.pnl_by_strategy.items():
                self.pnl_by_strategy_gauge.labels(strategy=strategy).set(pnl)
            
            # PnL temporal
            self.daily_pnl_gauge.set(summary.daily_pnl)
            self.weekly_pnl_gauge.set(summary.weekly_pnl)
            self.monthly_pnl_gauge.set(summary.monthly_pnl)
            
            # Histogramas
            for record in self.pnl_records[-100:]:  # Últimos 100 registros
                self.pnl_histogram.observe(record.pnl)
                self.trade_duration_histogram.observe(record.duration_minutes)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de Prometheus: {e}")
    
    async def save_pnl_summary_to_file(self, summary: PnLSummary):
        """Guarda el resumen de PnL en archivo"""
        try:
            summary_file = Path("data/enterprise/pnl_tracking/pnl_summary.json")
            
            # Convertir resumen a diccionario
            summary_dict = {
                'timestamp': summary.timestamp.isoformat(),
                'total_pnl': summary.total_pnl,
                'realized_pnl': summary.realized_pnl,
                'unrealized_pnl': summary.unrealized_pnl,
                'total_trades': summary.total_trades,
                'winning_trades': summary.winning_trades,
                'losing_trades': summary.losing_trades,
                'win_rate': summary.win_rate,
                'avg_win': summary.avg_win,
                'avg_loss': summary.avg_loss,
                'largest_win': summary.largest_win,
                'largest_loss': summary.largest_loss,
                'profit_factor': summary.profit_factor,
                'total_fees': summary.total_fees,
                'net_pnl': summary.net_pnl,
                'pnl_by_symbol': summary.pnl_by_symbol,
                'pnl_by_strategy': summary.pnl_by_strategy,
                'daily_pnl': summary.daily_pnl,
                'weekly_pnl': summary.weekly_pnl,
                'monthly_pnl': summary.monthly_pnl
            }
            
            # Guardar en archivo
            with open(summary_file, 'w') as f:
                json.dump(summary_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando resumen de PnL: {e}")
    
    async def load_pnl_history(self):
        """Carga el historial de PnL"""
        try:
            # Implementar carga de historial
            pass
        except Exception as e:
            logger.error(f"Error cargando historial de PnL: {e}")
    
    async def stop_tracking(self):
        """Detiene el seguimiento de PnL"""
        try:
            logger.info("⏹️ Deteniendo seguimiento de PnL...")
            self.is_running = False
            
            # Guardar resumen final
            if self.last_summary:
                await self.save_pnl_summary_to_file(self.last_summary)
            
            logger.info("✅ Seguimiento de PnL detenido correctamente")
            
        except Exception as e:
            logger.error(f"Error deteniendo seguimiento de PnL: {e}")
    
    def get_current_summary(self) -> Optional[PnLSummary]:
        """Obtiene el resumen actual de PnL"""
        return self.last_summary
    
    def get_pnl_records(self) -> List[PnLRecord]:
        """Obtiene todos los registros de PnL"""
        return self.pnl_records.copy()

# Instancia global
pnl_tracker = PnLTracker()
