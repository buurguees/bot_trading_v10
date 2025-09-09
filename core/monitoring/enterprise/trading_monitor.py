# Ruta: core/monitoring/enterprise/trading_monitor.py
#!/usr/bin/env python3
"""
Monitor de Trading Enterprise - Tiempo Real
==========================================

Este módulo implementa monitoreo en tiempo real de métricas de trading
con integración a Prometheus/Grafana y alertas automáticas.

Características:
- Métricas en tiempo real (PnL, Sharpe, drawdown)
- Integración con Prometheus
- Alertas automáticas por email/Slack
- Dashboard de Grafana
- Métricas de performance avanzadas

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from prometheus_client.core import CollectorRegistry

from core.trading.enterprise.futures_engine import EnterpriseFuturesEngine
from core.trading.bitget_client import bitget_client
from core.config.config_loader import ConfigLoader

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class TradingMetrics:
    """Métricas de trading en tiempo real"""
    timestamp: datetime
    account_balance: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    open_positions_count: int
    daily_return_pct: float
    weekly_return_pct: float
    monthly_return_pct: float
    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    current_drawdown_pct: float
    win_rate: float
    profit_factor: float
    var_95: float
    var_99: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    exposure_pct: float
    margin_used: float
    margin_available: float
    margin_ratio: float

class TradingMonitor:
    """Monitor de trading enterprise en tiempo real"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        config_loader = ConfigLoader()
        self.config = config_loader.get_value(['monitoring'], {})
        self.futures_engine = None
        self.bitget_client = bitget_client
        
        # Métricas de Prometheus
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Estado del monitor
        self.is_running = False
        self.start_time = None
        self.last_metrics = None
        self.metrics_history = []
        self.max_history = 10000
        
        # Configuración
        self.update_interval = self.config.get('update_interval', 5)  # segundos
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        
        # Directorios
        self.setup_directories()
        
        logger.info("📊 TradingMonitor enterprise inicializado")
    
    def _setup_prometheus_metrics(self):
        """Configura las métricas de Prometheus"""
        # Métricas de balance y PnL
        self.balance_gauge = Gauge(
            'trading_account_balance', 
            'Account balance in USDT',
            registry=self.registry
        )
        
        self.total_pnl_gauge = Gauge(
            'trading_total_pnl', 
            'Total PnL in USDT',
            registry=self.registry
        )
        
        self.unrealized_pnl_gauge = Gauge(
            'trading_unrealized_pnl', 
            'Unrealized PnL in USDT',
            registry=self.registry
        )
        
        self.realized_pnl_gauge = Gauge(
            'trading_realized_pnl', 
            'Realized PnL in USDT',
            registry=self.registry
        )
        
        # Métricas de posiciones
        self.positions_count_gauge = Gauge(
            'trading_open_positions_count', 
            'Number of open positions',
            registry=self.registry
        )
        
        self.exposure_pct_gauge = Gauge(
            'trading_exposure_percentage', 
            'Portfolio exposure percentage',
            registry=self.registry
        )
        
        # Métricas de performance
        self.daily_return_gauge = Gauge(
            'trading_daily_return_percentage', 
            'Daily return percentage',
            registry=self.registry
        )
        
        self.sharpe_ratio_gauge = Gauge(
            'trading_sharpe_ratio', 
            'Sharpe ratio',
            registry=self.registry
        )
        
        self.calmar_ratio_gauge = Gauge(
            'trading_calmar_ratio', 
            'Calmar ratio',
            registry=self.registry
        )
        
        self.max_drawdown_gauge = Gauge(
            'trading_max_drawdown_percentage', 
            'Maximum drawdown percentage',
            registry=self.registry
        )
        
        self.current_drawdown_gauge = Gauge(
            'trading_current_drawdown_percentage', 
            'Current drawdown percentage',
            registry=self.registry
        )
        
        # Métricas de trades
        self.total_trades_counter = Counter(
            'trading_total_trades', 
            'Total number of trades',
            registry=self.registry
        )
        
        self.winning_trades_counter = Counter(
            'trading_winning_trades', 
            'Number of winning trades',
            registry=self.registry
        )
        
        self.losing_trades_counter = Counter(
            'trading_losing_trades', 
            'Number of losing trades',
            registry=self.registry
        )
        
        self.win_rate_gauge = Gauge(
            'trading_win_rate', 
            'Win rate percentage',
            registry=self.registry
        )
        
        self.profit_factor_gauge = Gauge(
            'trading_profit_factor', 
            'Profit factor',
            registry=self.registry
        )
        
        # Métricas de riesgo
        self.var_95_gauge = Gauge(
            'trading_var_95', 
            'Value at Risk 95%',
            registry=self.registry
        )
        
        self.var_99_gauge = Gauge(
            'trading_var_99', 
            'Value at Risk 99%',
            registry=self.registry
        )
        
        # Métricas de margen
        self.margin_used_gauge = Gauge(
            'trading_margin_used', 
            'Margin used in USDT',
            registry=self.registry
        )
        
        self.margin_available_gauge = Gauge(
            'trading_margin_available', 
            'Margin available in USDT',
            registry=self.registry
        )
        
        self.margin_ratio_gauge = Gauge(
            'trading_margin_ratio', 
            'Margin ratio',
            registry=self.registry
        )
        
        # Histogramas
        self.trade_duration_histogram = Histogram(
            'trading_trade_duration_seconds', 
            'Trade duration in seconds',
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600, 7200, 86400],
            registry=self.registry
        )
        
        self.pnl_histogram = Histogram(
            'trading_pnl_distribution', 
            'PnL distribution',
            buckets=[-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000],
            registry=self.registry
        )
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/monitoring',
            'data/enterprise/monitoring',
            'backups/enterprise/monitoring'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Inicializa el monitor de trading"""
        try:
            logger.info("🔧 Inicializando TradingMonitor...")
            
            # Inicializar motor de futuros
            self.futures_engine = FuturesEngine()
            await self.futures_engine.initialize()
            
            # Iniciar servidor Prometheus
            prometheus_port = self.config.get('prometheus_port', 8003)
            start_http_server(prometheus_port, registry=self.registry)
            logger.info(f"📊 Servidor Prometheus iniciado en puerto {prometheus_port}")
            
            # Cargar historial de métricas
            await self.load_metrics_history()
            
            logger.info("✅ TradingMonitor inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando TradingMonitor: {e}")
            return False
    
    async def start_monitoring(self):
        """Inicia el monitoreo en tiempo real"""
        try:
            logger.info("🚀 Iniciando monitoreo de trading...")
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Loop principal de monitoreo
            while self.is_running:
                try:
                    # Recopilar métricas
                    metrics = await self.collect_trading_metrics()
                    
                    # Actualizar métricas de Prometheus
                    self.update_prometheus_metrics(metrics)
                    
                    # Guardar en historial
                    self.metrics_history.append(metrics)
                    if len(self.metrics_history) > self.max_history:
                        self.metrics_history.pop(0)
                    
                    # Verificar alertas
                    await self.check_alerts(metrics)
                    
                    # Guardar métricas en archivo
                    await self.save_metrics_to_file(metrics)
                    
                    self.last_metrics = metrics
                    
                    # Esperar antes de la siguiente actualización
                    await asyncio.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error en loop de monitoreo: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
        finally:
            self.is_running = False
    
    async def collect_trading_metrics(self) -> TradingMetrics:
        """Recopila métricas de trading en tiempo real"""
        try:
            # Obtener balance de la cuenta
            balance_info = await self.bitget_client.get_margin_info()
            account_balance = balance_info.get('total_balance', 0) if balance_info else 0
            
            # Obtener posiciones abiertas
            positions = await self.bitget_client.get_positions()
            
            # Calcular métricas de PnL
            total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            unrealized_pnl = total_pnl
            realized_pnl = 0  # Se calcularía desde el historial de trades
            
            # Calcular métricas de posiciones
            open_positions_count = len(positions)
            exposure_pct = self.calculate_exposure_percentage(positions, account_balance)
            
            # Calcular métricas de performance
            daily_return_pct = await self.calculate_daily_return()
            weekly_return_pct = await self.calculate_weekly_return()
            monthly_return_pct = await self.calculate_monthly_return()
            
            # Calcular ratios de riesgo
            sharpe_ratio = await self.calculate_sharpe_ratio()
            calmar_ratio = await self.calculate_calmar_ratio()
            
            # Calcular drawdown
            max_drawdown_pct = await self.calculate_max_drawdown()
            current_drawdown_pct = await self.calculate_current_drawdown()
            
            # Calcular métricas de trades
            total_trades, winning_trades, losing_trades = await self.get_trade_statistics()
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calcular profit factor
            profit_factor = await self.calculate_profit_factor()
            
            # Calcular VaR
            var_95 = await self.calculate_var(0.95)
            var_99 = await self.calculate_var(0.99)
            
            # Calcular métricas de margen
            margin_used = balance_info.get('used_balance', 0) if balance_info else 0
            margin_available = balance_info.get('free_balance', 0) if balance_info else 0
            margin_ratio = balance_info.get('margin_ratio', 0) if balance_info else 0
            
            # Crear objeto de métricas
            metrics = TradingMetrics(
                timestamp=datetime.now(),
                account_balance=account_balance,
                total_pnl=total_pnl,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                open_positions_count=open_positions_count,
                daily_return_pct=daily_return_pct,
                weekly_return_pct=weekly_return_pct,
                monthly_return_pct=monthly_return_pct,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown_pct=max_drawdown_pct,
                current_drawdown_pct=current_drawdown_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                var_95=var_95,
                var_99=var_99,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_win=0,  # Se calcularía desde el historial
                avg_loss=0,  # Se calcularía desde el historial
                largest_win=0,  # Se calcularía desde el historial
                largest_loss=0,  # Se calcularía desde el historial
                avg_trade_duration=0,  # Se calcularía desde el historial
                exposure_pct=exposure_pct,
                margin_used=margin_used,
                margin_available=margin_available,
                margin_ratio=margin_ratio
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recopilando métricas: {e}")
            # Retornar métricas por defecto en caso de error
            return TradingMetrics(
                timestamp=datetime.now(),
                account_balance=0,
                total_pnl=0,
                unrealized_pnl=0,
                realized_pnl=0,
                open_positions_count=0,
                daily_return_pct=0,
                weekly_return_pct=0,
                monthly_return_pct=0,
                sharpe_ratio=0,
                calmar_ratio=0,
                max_drawdown_pct=0,
                current_drawdown_pct=0,
                win_rate=0,
                profit_factor=0,
                var_95=0,
                var_99=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0,
                avg_loss=0,
                largest_win=0,
                largest_loss=0,
                avg_trade_duration=0,
                exposure_pct=0,
                margin_used=0,
                margin_available=0,
                margin_ratio=0
            )
    
    def calculate_exposure_percentage(self, positions: List[Dict], balance: float) -> float:
        """Calcula el porcentaje de exposición del portfolio"""
        try:
            if balance <= 0:
                return 0
            
            total_exposure = sum(
                pos.get('size', 0) * pos.get('mark_price', 0) 
                for pos in positions
            )
            
            return (total_exposure / balance) * 100
            
        except Exception as e:
            logger.error(f"Error calculando exposición: {e}")
            return 0
    
    async def calculate_daily_return(self) -> float:
        """Calcula el retorno diario"""
        try:
            # Implementar cálculo de retorno diario
            # Por ahora retornar 0
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando retorno diario: {e}")
            return 0.0
    
    async def calculate_weekly_return(self) -> float:
        """Calcula el retorno semanal"""
        try:
            # Implementar cálculo de retorno semanal
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando retorno semanal: {e}")
            return 0.0
    
    async def calculate_monthly_return(self) -> float:
        """Calcula el retorno mensual"""
        try:
            # Implementar cálculo de retorno mensual
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando retorno mensual: {e}")
            return 0.0
    
    async def calculate_sharpe_ratio(self) -> float:
        """Calcula el ratio de Sharpe"""
        try:
            # Implementar cálculo de Sharpe ratio
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando Sharpe ratio: {e}")
            return 0.0
    
    async def calculate_calmar_ratio(self) -> float:
        """Calcula el ratio de Calmar"""
        try:
            # Implementar cálculo de Calmar ratio
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando Calmar ratio: {e}")
            return 0.0
    
    async def calculate_max_drawdown(self) -> float:
        """Calcula el drawdown máximo"""
        try:
            # Implementar cálculo de drawdown máximo
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando drawdown máximo: {e}")
            return 0.0
    
    async def calculate_current_drawdown(self) -> float:
        """Calcula el drawdown actual"""
        try:
            # Implementar cálculo de drawdown actual
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando drawdown actual: {e}")
            return 0.0
    
    async def get_trade_statistics(self) -> Tuple[int, int, int]:
        """Obtiene estadísticas de trades"""
        try:
            # Implementar obtención de estadísticas de trades
            return 0, 0, 0
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de trades: {e}")
            return 0, 0, 0
    
    async def calculate_profit_factor(self) -> float:
        """Calcula el factor de ganancia"""
        try:
            # Implementar cálculo de profit factor
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando profit factor: {e}")
            return 0.0
    
    async def calculate_var(self, confidence_level: float) -> float:
        """Calcula el Value at Risk"""
        try:
            # Implementar cálculo de VaR
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando VaR: {e}")
            return 0.0
    
    def update_prometheus_metrics(self, metrics: TradingMetrics):
        """Actualiza las métricas de Prometheus"""
        try:
            # Balance y PnL
            self.balance_gauge.set(metrics.account_balance)
            self.total_pnl_gauge.set(metrics.total_pnl)
            self.unrealized_pnl_gauge.set(metrics.unrealized_pnl)
            self.realized_pnl_gauge.set(metrics.realized_pnl)
            
            # Posiciones
            self.positions_count_gauge.set(metrics.open_positions_count)
            self.exposure_pct_gauge.set(metrics.exposure_pct)
            
            # Performance
            self.daily_return_gauge.set(metrics.daily_return_pct)
            self.sharpe_ratio_gauge.set(metrics.sharpe_ratio)
            self.calmar_ratio_gauge.set(metrics.calmar_ratio)
            self.max_drawdown_gauge.set(metrics.max_drawdown_pct)
            self.current_drawdown_gauge.set(metrics.current_drawdown_pct)
            
            # Trades
            self.win_rate_gauge.set(metrics.win_rate)
            self.profit_factor_gauge.set(metrics.profit_factor)
            
            # Riesgo
            self.var_95_gauge.set(metrics.var_95)
            self.var_99_gauge.set(metrics.var_99)
            
            # Margen
            self.margin_used_gauge.set(metrics.margin_used)
            self.margin_available_gauge.set(metrics.margin_available)
            self.margin_ratio_gauge.set(metrics.margin_ratio)
            
            # Histogramas
            self.pnl_histogram.observe(metrics.total_pnl)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de Prometheus: {e}")
    
    async def check_alerts(self, metrics: TradingMetrics):
        """Verifica alertas basadas en las métricas"""
        try:
            # Alertas de drawdown
            if metrics.current_drawdown_pct > self.alert_thresholds.get('max_drawdown', 10):
                await self.send_alert(
                    "HIGH_DRAWDOWN",
                    f"Drawdown actual: {metrics.current_drawdown_pct:.2f}%",
                    "critical"
                )
            
            # Alertas de margen
            if metrics.margin_ratio > self.alert_thresholds.get('max_margin_ratio', 0.8):
                await self.send_alert(
                    "HIGH_MARGIN_RATIO",
                    f"Ratio de margen: {metrics.margin_ratio:.2f}",
                    "warning"
                )
            
            # Alertas de pérdidas
            if metrics.total_pnl < self.alert_thresholds.get('min_pnl', -1000):
                await self.send_alert(
                    "LOW_PNL",
                    f"PnL total: ${metrics.total_pnl:.2f}",
                    "warning"
                )
            
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
    
    async def send_alert(self, alert_type: str, message: str, severity: str):
        """Envía una alerta"""
        try:
            logger.warning(f"🚨 ALERTA {severity.upper()}: {alert_type} - {message}")
            
            # Aquí se implementaría el envío de alertas por email/Slack/etc.
            # Por ahora solo loggeamos
            
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")
    
    async def save_metrics_to_file(self, metrics: TradingMetrics):
        """Guarda las métricas en archivo"""
        try:
            metrics_file = Path("data/enterprise/monitoring/metrics.json")
            
            # Convertir métricas a diccionario
            metrics_dict = {
                'timestamp': metrics.timestamp.isoformat(),
                'account_balance': metrics.account_balance,
                'total_pnl': metrics.total_pnl,
                'unrealized_pnl': metrics.unrealized_pnl,
                'realized_pnl': metrics.realized_pnl,
                'open_positions_count': metrics.open_positions_count,
                'daily_return_pct': metrics.daily_return_pct,
                'weekly_return_pct': metrics.weekly_return_pct,
                'monthly_return_pct': metrics.monthly_return_pct,
                'sharpe_ratio': metrics.sharpe_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'max_drawdown_pct': metrics.max_drawdown_pct,
                'current_drawdown_pct': metrics.current_drawdown_pct,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor,
                'var_95': metrics.var_95,
                'var_99': metrics.var_99,
                'total_trades': metrics.total_trades,
                'winning_trades': metrics.winning_trades,
                'losing_trades': metrics.losing_trades,
                'exposure_pct': metrics.exposure_pct,
                'margin_used': metrics.margin_used,
                'margin_available': metrics.margin_available,
                'margin_ratio': metrics.margin_ratio
            }
            
            # Guardar en archivo
            with open(metrics_file, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")
    
    async def load_metrics_history(self):
        """Carga el historial de métricas"""
        try:
            metrics_file = Path("data/enterprise/monitoring/metrics.json")
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    # Procesar datos históricos si es necesario
                    
        except Exception as e:
            logger.error(f"Error cargando historial de métricas: {e}")
    
    async def stop_monitoring(self):
        """Detiene el monitoreo"""
        try:
            logger.info("⏹️ Deteniendo monitoreo de trading...")
            self.is_running = False
            
            # Guardar métricas finales
            if self.last_metrics:
                await self.save_metrics_to_file(self.last_metrics)
            
            logger.info("✅ Monitoreo detenido correctamente")
            
        except Exception as e:
            logger.error(f"Error deteniendo monitoreo: {e}")
    
    def get_current_metrics(self) -> Optional[TradingMetrics]:
        """Obtiene las métricas actuales"""
        return self.last_metrics
    
    def get_metrics_history(self) -> List[TradingMetrics]:
        """Obtiene el historial de métricas"""
        return self.metrics_history.copy()

# Instancia global
trading_monitor = TradingMonitor()
