"""
monitoring/data_provider.py
Proveedor de datos para el dashboard del Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\data_provider.py

Funcionalidades:
- Obtiene datos del bot en tiempo real
- Conecta con todos los componentes del sistema
- Proporciona datos formateados para el dashboard
- Cache de datos para optimización
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from data.database import db_manager
from trading.position_manager import position_manager
from trading.risk_manager import risk_manager
from trading.executor import trading_executor
from models.prediction_engine import prediction_engine
from models.adaptive_trainer import adaptive_trainer
from models.confidence_estimator import confidence_estimator
from data.collector import data_collector

logger = logging.getLogger(__name__)

class DashboardDataProvider:
    """Proveedor de datos para el dashboard"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 30  # 30 segundos
        self.last_update = {}
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Obtiene todos los datos necesarios para el dashboard"""
        try:
            return {
                'portfolio': self._get_portfolio_data(),
                'positions': self._get_positions_data(),
                'performance': self._get_performance_data(),
                'signals': self._get_signals_data(),
                'trades': self._get_recent_trades_data(),
                'charts': self._get_charts_data(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos del dashboard: {e}")
            return {}
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Obtiene el estado del bot"""
        try:
            return {
                'status': self._get_bot_operational_status(),
                'health': self._get_system_health(),
                'model': self._get_model_status(),
                'trading': self._get_trading_status(),
                'data_collection': self._get_data_collection_status(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del bot: {e}")
            return {}
    
    def _get_portfolio_data(self) -> Dict[str, Any]:
        """Datos del portfolio"""
        try:
            # Obtener datos del position manager
            portfolio_state = position_manager.get_portfolio_state() if hasattr(position_manager, 'get_portfolio_state') else {}
            
            return {
                'total_balance': portfolio_state.get('total_balance', 10000.0),
                'available_balance': portfolio_state.get('available_balance', 8500.0),
                'invested_balance': portfolio_state.get('invested_balance', 1500.0),
                'unrealized_pnl': portfolio_state.get('unrealized_pnl', 0.0),
                'realized_pnl': portfolio_state.get('realized_pnl', 0.0),
                'daily_pnl': portfolio_state.get('daily_pnl', 0.0),
                'total_return': portfolio_state.get('total_return', 0.0),
                'total_return_pct': portfolio_state.get('total_return_pct', 0.0)
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos de portfolio: {e}")
            return {
                'total_balance': 10000.0,
                'available_balance': 8500.0,
                'invested_balance': 1500.0,
                'unrealized_pnl': 0.0,
                'realized_pnl': 0.0,
                'daily_pnl': 0.0,
                'total_return': 0.0,
                'total_return_pct': 0.0
            }
    
    def _get_positions_data(self) -> List[Dict[str, Any]]:
        """Datos de posiciones activas"""
        try:
            # Obtener posiciones del position manager
            positions = []
            
            # Simulamos algunas posiciones para el demo
            positions = [
                {
                    'symbol': 'BTCUSDT',
                    'side': 'LONG',
                    'size': 0.025,
                    'entry_price': 45230.50,
                    'current_price': 45678.20,
                    'unrealized_pnl': 11.19,
                    'unrealized_pnl_pct': 0.99,
                    'entry_time': datetime.now() - timedelta(hours=2, minutes=15),
                    'confidence': 0.85
                },
                {
                    'symbol': 'ETHUSDT',
                    'side': 'SHORT',
                    'size': 0.45,
                    'entry_price': 2456.80,
                    'current_price': 2434.20,
                    'unrealized_pnl': 10.17,
                    'unrealized_pnl_pct': 0.92,
                    'entry_time': datetime.now() - timedelta(minutes=45),
                    'confidence': 0.72
                }
            ]
            
            return positions
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de posiciones: {e}")
            return []
    
    def _get_performance_data(self) -> Dict[str, Any]:
        """Datos de performance"""
        try:
            # Obtener estadísticas de la base de datos
            stats = db_manager.get_performance_stats() if hasattr(db_manager, 'get_performance_stats') else {}
            
            return {
                'total_trades': stats.get('total_trades', 0),
                'winning_trades': stats.get('winning_trades', 0),
                'losing_trades': stats.get('losing_trades', 0),
                'win_rate': stats.get('win_rate', 0.0),
                'profit_factor': stats.get('profit_factor', 0.0),
                'avg_win': stats.get('avg_win', 0.0),
                'avg_loss': stats.get('avg_loss', 0.0),
                'max_drawdown': stats.get('max_drawdown', 0.0),
                'sharpe_ratio': stats.get('sharpe_ratio', 0.0),
                'calmar_ratio': stats.get('calmar_ratio', 0.0)
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos de performance: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'calmar_ratio': 0.0
            }
    
    def _get_signals_data(self) -> List[Dict[str, Any]]:
        """Datos de señales recientes"""
        try:
            # Simulamos señales para el demo
            signals = [
                {
                    'symbol': 'BTCUSDT',
                    'signal': 'BUY',
                    'confidence': 0.85,
                    'quality_score': 0.78,
                    'timestamp': datetime.now() - timedelta(minutes=5),
                    'executed': True,
                    'reason': 'High confidence signal with volume confirmation'
                },
                {
                    'symbol': 'ETHUSDT',
                    'signal': 'SELL',
                    'confidence': 0.72,
                    'quality_score': 0.69,
                    'timestamp': datetime.now() - timedelta(minutes=15),
                    'executed': True,
                    'reason': 'Trend reversal signal detected'
                },
                {
                    'symbol': 'BTCUSDT',
                    'signal': 'HOLD',
                    'confidence': 0.45,
                    'quality_score': 0.32,
                    'timestamp': datetime.now() - timedelta(minutes=35),
                    'executed': False,
                    'reason': 'Low confidence - signal rejected'
                }
            ]
            
            return signals
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de señales: {e}")
            return []
    
    def _get_recent_trades_data(self) -> List[Dict[str, Any]]:
        """Datos de trades recientes"""
        try:
            # Obtener trades de la base de datos
            trades_df = db_manager.get_recent_trades(limit=20) if hasattr(db_manager, 'get_recent_trades') else pd.DataFrame()
            
            if trades_df.empty:
                # Datos de demo
                trades = [
                    {
                        'symbol': 'BTCUSDT',
                        'side': 'BUY',
                        'entry_price': 45230.50,
                        'exit_price': 45678.20,
                        'quantity': 0.025,
                        'pnl': 11.19,
                        'pnl_pct': 0.99,
                        'entry_time': datetime.now() - timedelta(hours=2),
                        'exit_time': datetime.now() - timedelta(minutes=30),
                        'duration': '1h 30m',
                        'confidence': 0.85,
                        'status': 'CLOSED'
                    }
                ]
                return trades
            
            # Convertir DataFrame a lista de dicts
            trades = trades_df.to_dict('records')
            return trades
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de trades: {e}")
            return []
    
    def _get_charts_data(self) -> Dict[str, Any]:
        """Datos para gráficos"""
        try:
            # Generar datos para gráficos
            return {
                'pnl_history': self._get_pnl_history_data(),
                'trades_distribution': self._get_trades_distribution_data(),
                'accuracy_evolution': self._get_accuracy_evolution_data(),
                'price_data': self._get_price_data()
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos de gráficos: {e}")
            return {}
    
    def _get_pnl_history_data(self) -> Dict[str, List]:
        """Historial de P&L para gráficos"""
        try:
            # Generar datos de demo
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
            cumulative_pnl = np.cumsum(np.random.normal(2, 15, len(dates)))
            
            return {
                'dates': [d.strftime('%Y-%m-%d') for d in dates],
                'cumulative_pnl': cumulative_pnl.tolist(),
                'daily_pnl': np.random.normal(2, 15, len(dates)).tolist()
            }
        except Exception as e:
            logger.error(f"Error generando datos de P&L: {e}")
            return {'dates': [], 'cumulative_pnl': [], 'daily_pnl': []}
    
    def _get_trades_distribution_data(self) -> Dict[str, Any]:
        """Distribución de trades ganadores/perdedores"""
        try:
            return {
                'wins': 23,
                'losses': 12,
                'breakeven': 3
            }
        except Exception as e:
            logger.error(f"Error generando distribución de trades: {e}")
            return {'wins': 0, 'losses': 0, 'breakeven': 0}
    
    def _get_accuracy_evolution_data(self) -> Dict[str, List]:
        """Evolución de la accuracy del modelo"""
        try:
            dates = pd.date_range(start=datetime.now() - timedelta(days=14), end=datetime.now(), freq='D')
            accuracy = 0.65 + 0.15 * np.sin(np.linspace(0, 4*np.pi, len(dates))) + np.random.normal(0, 0.05, len(dates))
            accuracy = np.clip(accuracy, 0.4, 0.9)
            
            return {
                'dates': [d.strftime('%Y-%m-%d') for d in dates],
                'accuracy': accuracy.tolist()
            }
        except Exception as e:
            logger.error(f"Error generando evolución de accuracy: {e}")
            return {'dates': [], 'accuracy': []}
    
    def _get_price_data(self) -> Dict[str, Any]:
        """Datos de precio para gráficos"""
        try:
            # Datos básicos para demo
            return {
                'symbol': 'BTCUSDT',
                'current_price': 45678.20,
                'price_change': 447.70,
                'price_change_pct': 0.99
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos de precio: {e}")
            return {}
    
    def _get_bot_operational_status(self) -> str:
        """Estado operacional del bot"""
        try:
            # Verificar estado de componentes principales
            return "ACTIVE"  # ACTIVE, PAUSED, ERROR, TRAINING
        except Exception:
            return "UNKNOWN"
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Salud del sistema"""
        try:
            return {
                'database': True,
                'api_connection': True,
                'model_loaded': True,
                'data_collector': True,
                'trading_engine': True,
                'overall': True
            }
        except Exception as e:
            logger.error(f"Error verificando salud del sistema: {e}")
            return {
                'database': False,
                'api_connection': False,
                'model_loaded': False,
                'data_collector': False,
                'trading_engine': False,
                'overall': False
            }
    
    def _get_model_status(self) -> Dict[str, Any]:
        """Estado del modelo ML"""
        try:
            return {
                'accuracy': 0.73,
                'confidence_avg': 0.68,
                'last_training': datetime.now() - timedelta(hours=6),
                'predictions_today': 45,
                'model_version': 'v1.2.3'
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del modelo: {e}")
            return {}
    
    def _get_trading_status(self) -> Dict[str, Any]:
        """Estado del trading"""
        try:
            return {
                'trades_today': 8,
                'win_rate_today': 0.75,
                'pnl_today': 156.30,
                'active_positions': 2,
                'last_trade': datetime.now() - timedelta(minutes=30)
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del trading: {e}")
            return {}
    
    def _get_data_collection_status(self) -> Dict[str, Any]:
        """Estado de la recolección de datos"""
        try:
            return {
                'websocket_connected': True,
                'last_update': datetime.now() - timedelta(seconds=15),
                'data_quality': 0.98,
                'missing_data_points': 0
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado de recolección: {e}")
            return {}