# Ruta: core/monitoring/core/data_provider.py
"""
monitoring/core/data_provider.py
Proveedor Centralizado de Datos - Trading Bot v10

Esta clase gestiona toda la obtención, agregación y formateo de datos
para el sistema de monitoreo. Actúa como interfaz única entre el
dashboard y todas las fuentes de datos del bot.
"""

import logging
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import json
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
from contextlib import contextmanager
import traceback

# Importaciones del proyecto
try:
    from core.data.database import DatabaseManager
    from core.trading.position_manager import PositionManager
    from core.ml.legacy.prediction_engine import PredictionEngine
    from core.config.user_config import UserConfig
except ImportError as e:
    logging.warning(f"Algunas importaciones del proyecto no están disponibles: {e}")
    # Fallbacks para desarrollo
    DatabaseManager = None
    PositionManager = None
    PredictionEngine = None
    UserConfig = None

logger = logging.getLogger(__name__)

@dataclass
class SymbolMetrics:
    """Métricas por símbolo para el dashboard"""
    symbol: str
    win_rate: float
    total_runs: int
    avg_pnl: float
    balance_progress: float  # % hacia objetivo
    sharpe_ratio: float
    max_drawdown: float
    current_status: str  # 'active', 'paused', 'error'
    last_signal: str  # 'buy', 'sell', 'hold'
    last_signal_time: datetime
    current_balance: float
    target_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    current_position: Optional[str] = None  # 'long', 'short', None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

@dataclass
class CycleData:
    """Datos de un ciclo de trading"""
    cycle_id: str
    symbol: str
    start_date: datetime
    end_date: Optional[datetime]
    start_balance: float
    end_balance: float
    pnl: float
    pnl_percentage: float
    total_trades: int
    win_rate: float
    avg_daily_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    duration_days: int
    status: str  # 'active', 'completed', 'stopped'
    roi: float = 0.0
    profit_factor: float = 0.0
    leverage_min: float = 1.0
    leverage_max: float = 1.0
    
@dataclass
class TradeData:
    """Datos de un trade individual"""
    trade_id: str
    symbol: str
    side: str  # 'buy', 'sell'
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_percentage: Optional[float]
    duration_minutes: Optional[int]
    status: str  # 'open', 'closed', 'cancelled'
    stop_loss: Optional[float]
    take_profit: Optional[float]
    fees: float = 0.0
    slippage: float = 0.0

@dataclass
class MarketData:
    """Datos de mercado para gráficos"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = '1m'

@dataclass
class ModelMetrics:
    """Métricas del modelo de IA"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    loss: float
    predictions_today: int
    avg_confidence: float
    last_retrain: datetime
    drift_score: float
    model_version: str

class DataProvider:
    """
    Proveedor centralizado de datos para el sistema de monitoreo
    
    Gestiona la obtención de datos desde múltiples fuentes y proporciona
    una interfaz unificada para el dashboard.
    """
    
    def __init__(self):
        """Inicializa el proveedor de datos"""
        self.db_path = "data/trading_bot.db"
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutos
        self.lock = threading.RLock()
        self._connected = False
        self._database_manager = None
        
        # Configuración
        self.config = {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
            'timeframes': ['1m', '5m', '15m', '1h', '4h'],
            'default_lookback_days': 30,
            'max_trades_query': 1000,
            'performance_calculation_period': 24  # horas
        }
        
        # Inicializar conexión
        self._initialize_connection()
        
        logger.info("DataProvider inicializado correctamente")
    
    def _initialize_connection(self):
        """Inicializa la conexión a la base de datos"""
        try:
            # Crear directorio si no existe
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Intentar usar DatabaseManager del proyecto si está disponible
            if DatabaseManager:
                self._database_manager = DatabaseManager()
                self._connected = self._database_manager.is_connected()
            else:
                # Fallback a conexión SQLite directa
                test_conn = sqlite3.connect(self.db_path)
                test_conn.close()
                self._connected = True
            
            logger.info("Conexión a base de datos establecida")
            
        except Exception as e:
            logger.error(f"Error al conectar con base de datos: {e}")
            self._connected = False
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la base de datos"""
        if self._database_manager:
            with self._database_manager._get_connection() as conn:
                yield conn
        else:
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a la base de datos"""
        return self._connected
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Obtiene datos del cache si están válidos"""
        with self.lock:
            if cache_key in self.cache:
                timestamp = self.cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self.cache_ttl:
                    return self.cache[cache_key]
                else:
                    # Cache expirado, eliminar
                    del self.cache[cache_key]
                    del self.cache_timestamps[cache_key]
            return None
    
    def _set_cached_data(self, cache_key: str, data: Any):
        """Guarda datos en el cache"""
        with self.lock:
            self.cache[cache_key] = data
            self.cache_timestamps[cache_key] = time.time()
    
    def get_symbol_metrics(self, symbol: Optional[str] = None) -> Union[List[SymbolMetrics], SymbolMetrics]:
        """
        Obtiene métricas por símbolo
        
        Args:
            symbol: Símbolo específico o None para todos
            
        Returns:
            Lista de métricas por símbolo o métricas de un símbolo específico
        """
        try:
            cache_key = f"symbol_metrics_{symbol or 'all'}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            symbols_to_query = [symbol] if symbol else self.config['symbols']
            metrics_list = []
            
            for sym in symbols_to_query:
                try:
                    metrics = self._calculate_symbol_metrics(sym)
                    metrics_list.append(metrics)
                except Exception as e:
                    logger.error(f"Error calculando métricas para {sym}: {e}")
                    # Crear métricas por defecto en caso de error
                    metrics_list.append(self._create_default_metrics(sym))
            
            # Cachear resultados
            result = metrics_list[0] if symbol else metrics_list
            self._set_cached_data(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener métricas de símbolos: {e}")
            if symbol:
                return self._create_default_metrics(symbol)
            else:
                return [self._create_default_metrics(sym) for sym in self.config['symbols']]
    
    def _calculate_symbol_metrics(self, symbol: str) -> SymbolMetrics:
        """Calcula métricas para un símbolo específico"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener trades del símbolo
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE symbol = ? AND entry_time >= date('now', '-30 days')
                    ORDER BY entry_time DESC
                """, (symbol,))
                
                trades = cursor.fetchall()
                if not trades:
                    return self._create_default_metrics(symbol)
                
                # Convertir a DataFrame para cálculos
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(trades, columns=columns)
                
                # Calcular métricas básicas
                total_trades = len(df)
                closed_trades = df[df['status'] == 'closed']
                
                if len(closed_trades) == 0:
                    return self._create_default_metrics(symbol)
                
                winning_trades = len(closed_trades[closed_trades['pnl'] > 0])
                losing_trades = len(closed_trades[closed_trades['pnl'] <= 0])
                win_rate = (winning_trades / len(closed_trades)) * 100 if len(closed_trades) > 0 else 0
                
                # PnL promedio
                avg_pnl = closed_trades['pnl'].mean() if len(closed_trades) > 0 else 0
                total_pnl = closed_trades['pnl'].sum() if len(closed_trades) > 0 else 0
                
                # Balance actual y progreso
                current_balance = self._get_current_balance(symbol)
                target_balance = self._get_target_balance(symbol)
                balance_progress = ((current_balance - 1000) / (target_balance - 1000)) * 100 if target_balance > 1000 else 0
                
                # Sharpe ratio y max drawdown
                returns = closed_trades['pnl_percentage'] / 100 if len(closed_trades) > 0 else pd.Series([0])
                sharpe_ratio = self._calculate_sharpe_ratio(returns)
                max_drawdown = self._calculate_max_drawdown(symbol)
                
                # Estado actual y última señal
                current_status = self._get_current_status(symbol)
                last_signal, last_signal_time = self._get_last_signal(symbol)
                
                # Posición actual
                current_position = self._get_current_position(symbol)
                unrealized_pnl = self._get_unrealized_pnl(symbol)
                
                return SymbolMetrics(
                    symbol=symbol,
                    win_rate=win_rate,
                    total_runs=self._get_total_runs(symbol),
                    avg_pnl=avg_pnl,
                    balance_progress=balance_progress,
                    sharpe_ratio=sharpe_ratio,
                    max_drawdown=max_drawdown,
                    current_status=current_status,
                    last_signal=last_signal,
                    last_signal_time=last_signal_time,
                    current_balance=current_balance,
                    target_balance=target_balance,
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    current_position=current_position,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=total_pnl
                )
                
        except Exception as e:
            logger.error(f"Error calculando métricas para {symbol}: {e}")
            return self._create_default_metrics(symbol)
    
    def _create_default_metrics(self, symbol: str) -> SymbolMetrics:
        """Crea métricas por defecto para un símbolo"""
        return SymbolMetrics(
            symbol=symbol,
            win_rate=0.0,
            total_runs=0,
            avg_pnl=0.0,
            balance_progress=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            current_status='paused',
            last_signal='hold',
            last_signal_time=datetime.now(),
            current_balance=1000.0,
            target_balance=2000.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            current_position=None,
            unrealized_pnl=0.0,
            realized_pnl=0.0
        )
    
    def get_market_data(self, symbol: str, timeframe: str = '1m', 
                       limit: int = 500) -> List[MarketData]:
        """
        Obtiene datos de mercado para gráficos
        
        Args:
            symbol: Símbolo a consultar
            timeframe: Marco temporal
            limit: Número máximo de registros
            
        Returns:
            Lista de datos de mercado
        """
        try:
            cache_key = f"market_data_{symbol}_{timeframe}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data 
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (symbol, timeframe, limit))
                
                rows = cursor.fetchall()
                
                market_data = []
                for row in rows:
                    timestamp = datetime.fromtimestamp(row[0]) if isinstance(row[0], (int, float)) else datetime.fromisoformat(row[0])
                    
                    market_data.append(MarketData(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        timeframe=timeframe
                    ))
                
                # Ordenar por timestamp ascendente para gráficos
                market_data.reverse()
                
                self._set_cached_data(cache_key, market_data)
                return market_data
                
        except Exception as e:
            logger.error(f"Error al obtener datos de mercado para {symbol}: {e}")
            return self._generate_mock_market_data(symbol, timeframe, limit)
    
    def get_cycles_data(self, symbol: Optional[str] = None, 
                       limit: int = 20) -> List[CycleData]:
        """
        Obtiene datos de ciclos de trading calculados desde los trades
        
        Args:
            symbol: Símbolo específico o None para todos
            limit: Número máximo de ciclos
            
        Returns:
            Lista de datos de ciclos con leverage min/max
        """
        try:
            cache_key = f"cycles_data_{symbol or 'all'}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Query para obtener trades agrupados por ciclos (por día)
                query = """
                    SELECT 
                        symbol,
                        DATE(entry_time) as cycle_date,
                        MIN(entry_time) as start_time,
                        MAX(COALESCE(exit_time, entry_time)) as end_time,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(COALESCE(pnl, 0)) as total_pnl,
                        AVG(COALESCE(pnl_pct, 0)) as avg_pnl_pct,
                        MIN(leverage) as leverage_min,
                        MAX(leverage) as leverage_max,
                        AVG(leverage) as leverage_avg
                    FROM trades 
                """
                params = []
                
                if symbol:
                    query += " WHERE symbol = ?"
                    params.append(symbol)
                
                query += """
                    GROUP BY symbol, DATE(entry_time)
                    HAVING total_trades > 0
                    ORDER BY cycle_date DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                cycles = []
                for row in rows:
                    cycle_data = self._build_cycle_data_from_trades(row)
                    cycles.append(cycle_data)
                
                self._set_cached_data(cache_key, cycles)
                return cycles
                
        except Exception as e:
            logger.error(f"Error al obtener datos de ciclos: {e}")
            return self._generate_mock_cycles_data(symbol, limit)
    
    def get_active_trades(self, symbol: Optional[str] = None) -> List[TradeData]:
        """
        Obtiene trades activos
        
        Args:
            symbol: Símbolo específico o None para todos
            
        Returns:
            Lista de trades activos
        """
        try:
            cache_key = f"active_trades_{symbol or 'all'}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT trade_id, symbol, side, entry_time, entry_price, 
                           quantity, stop_loss, take_profit, status
                    FROM trades 
                    WHERE status = 'open'
                """
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY entry_time DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    trade_data = self._build_trade_data_from_row(row)
                    trades.append(trade_data)
                
                self._set_cached_data(cache_key, trades)
                return trades
                
        except Exception as e:
            logger.error(f"Error al obtener trades activos: {e}")
            return []
    
    def get_recent_trades(self, symbol: Optional[str] = None, 
                         limit: int = 50) -> List[TradeData]:
        """
        Obtiene trades recientes
        
        Args:
            symbol: Símbolo específico o None para todos
            limit: Número máximo de trades
            
        Returns:
            Lista de trades recientes
        """
        try:
            cache_key = f"recent_trades_{symbol or 'all'}_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT trade_id, symbol, side, entry_time, exit_time, 
                           entry_price, exit_price, quantity, pnl, pnl_percentage,
                           status, stop_loss, take_profit
                    FROM trades 
                """
                params = []
                
                if symbol:
                    query += " WHERE symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY entry_time DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    trade_data = self._build_trade_data_from_row(row, include_exit=True)
                    trades.append(trade_data)
                
                self._set_cached_data(cache_key, trades)
                return trades
                
        except Exception as e:
            logger.error(f"Error al obtener trades recientes: {e}")
            return []
    
    def get_performance_metrics(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento general
        
        Args:
            period_hours: Período en horas para el cálculo
            
        Returns:
            Diccionario con métricas de rendimiento
        """
        try:
            cache_key = f"performance_metrics_{period_hours}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener trades del período
                cursor.execute("""
                    SELECT symbol, pnl, pnl_percentage, entry_time, exit_time
                    FROM trades 
                    WHERE entry_time >= datetime('now', '-{} hours')
                    AND status = 'closed'
                """.format(period_hours))
                
                trades = cursor.fetchall()
                
                if not trades:
                    return self._get_default_performance_metrics()
                
                df = pd.DataFrame(trades, columns=['symbol', 'pnl', 'pnl_percentage', 'entry_time', 'exit_time'])
                
                # Calcular métricas
                total_pnl = df['pnl'].sum()
                total_trades = len(df)
                winning_trades = len(df[df['pnl'] > 0])
                losing_trades = len(df[df['pnl'] <= 0])
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                
                avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
                avg_loss = df[df['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0
                profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 and losing_trades > 0 else 0
                
                # Sharpe ratio
                returns = df['pnl_percentage'] / 100
                sharpe_ratio = self._calculate_sharpe_ratio(returns)
                
                # Drawdown máximo
                cumulative_returns = (1 + returns).cumprod()
                running_max = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - running_max) / running_max
                max_drawdown = drawdown.min() * 100
                
                metrics = {
                    'total_pnl': total_pnl,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'period_hours': period_hours,
                    'symbols_active': df['symbol'].nunique(),
                    'avg_trade_duration': self._calculate_avg_trade_duration(df),
                    'best_symbol': self._get_best_performing_symbol(df),
                    'worst_symbol': self._get_worst_performing_symbol(df)
                }
                
                self._set_cached_data(cache_key, metrics)
                return metrics
                
        except Exception as e:
            logger.error(f"Error al obtener métricas de rendimiento: {e}")
            return self._get_default_performance_metrics()
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Obtiene estado y métricas del modelo de IA
        
        Returns:
            Diccionario con estado del modelo
        """
        try:
            cache_key = "model_status"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Si hay PredictionEngine disponible, usar datos reales
            if PredictionEngine:
                try:
                    # Aquí se integraría con el sistema real de ML
                    model_data = self._get_real_model_data()
                except Exception as e:
                    logger.warning(f"Error obteniendo datos reales del modelo: {e}")
                    model_data = self._generate_mock_model_data()
            else:
                model_data = self._generate_mock_model_data()
            
            self._set_cached_data(cache_key, model_data)
            return model_data
            
        except Exception as e:
            logger.error(f"Error al obtener estado del modelo: {e}")
            return self._generate_mock_model_data()
    
    def get_system_settings(self) -> Dict[str, Any]:
        """
        Obtiene configuraciones del sistema
        
        Returns:
            Diccionario con configuraciones
        """
        try:
            # Intentar cargar desde archivo de configuración
            config_file = Path("config/user_settings.yaml")
            if config_file.exists():
                import yaml
                with open(config_file, 'r') as f:
                    settings = yaml.safe_load(f)
                return settings
            else:
                return self._get_default_system_settings()
                
        except Exception as e:
            logger.error(f"Error al obtener configuraciones del sistema: {e}")
            return self._get_default_system_settings()
    
    def save_system_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Guarda configuraciones del sistema
        
        Args:
            settings: Configuraciones a guardar
            
        Returns:
            True si se guardó correctamente
        """
        try:
            config_file = Path("config/user_settings.yaml")
            config_file.parent.mkdir(exist_ok=True)
            
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(settings, f, default_flow_style=False)
            
            # Invalidar cache de configuraciones
            self._invalidate_cache("system_settings")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar configuraciones: {e}")
            return False
    
    def clear_cache(self):
        """Limpia todo el cache"""
        with self.lock:
            self.cache.clear()
            self.cache_timestamps.clear()
            logger.info("Cache limpiado")
    
    def _invalidate_cache(self, pattern: str):
        """Invalida entradas del cache que coincidan con el patrón"""
        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
                del self.cache_timestamps[key]
    
    # Métodos auxiliares para cálculos
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calcula el ratio de Sharpe"""
        try:
            if len(returns) == 0 or returns.std() == 0:
                return 0.0
            
            excess_returns = returns - (risk_free_rate / 252)  # Tasa libre de riesgo diaria
            return (excess_returns.mean() / returns.std()) * np.sqrt(252)  # Anualizado
            
        except Exception:
            return 0.0
    
    def _calculate_max_drawdown(self, symbol: str) -> float:
        """Calcula el drawdown máximo para un símbolo"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pnl_percentage FROM trades 
                    WHERE symbol = ? AND status = 'closed'
                    ORDER BY exit_time
                """, (symbol,))
                
                returns = [row[0] / 100 for row in cursor.fetchall()]
                
                if not returns:
                    return 0.0
                
                cumulative = np.cumprod([1 + r for r in returns])
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                
                return min(drawdown) * 100 if len(drawdown) > 0 else 0.0
                
        except Exception:
            return 0.0
    
    def _get_current_balance(self, symbol: str) -> float:
        """Obtiene el balance actual para un símbolo"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT balance FROM symbol_balances 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (symbol,))
                
                result = cursor.fetchone()
                return result[0] if result else 1000.0
                
        except Exception:
            return 1000.0
    
    def _get_target_balance(self, symbol: str) -> float:
        """Obtiene el balance objetivo para un símbolo"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT target_balance FROM symbol_config 
                    WHERE symbol = ?
                """, (symbol,))
                
                result = cursor.fetchone()
                return result[0] if result else 2000.0
                
        except Exception:
            return 2000.0
    
    def _get_current_status(self, symbol: str) -> str:
        """Obtiene el estado actual de un símbolo"""
        try:
            # Verificar si hay trades activos
            active_trades = self.get_active_trades(symbol)
            if active_trades:
                return 'active'
            # Si no hay trades, y no hay engine de predicción, pausado por defecto
            if PredictionEngine is None:
                return 'paused'
            return 'active'
        except Exception:
            return 'paused'

    def _get_last_signal(self, symbol: str) -> Tuple[str, datetime]:
        """Obtiene la última señal para un símbolo"""
        try:
            if PredictionEngine:
                # Integración real futura: PredictionEngine.get_last_signal(symbol)
                return ('hold', datetime.now())
            # Fallback a DB si existe tabla de señales
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT signal, timestamp FROM signals
                    WHERE symbol = ?
                    ORDER BY timestamp DESC LIMIT 1
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                if row:
                    ts = datetime.fromtimestamp(row[1]) if isinstance(row[1], (int, float)) else datetime.fromisoformat(str(row[1]))
                    return (str(row[0]), ts)
            return ('hold', datetime.now())
        except Exception:
            return ('hold', datetime.now())

    def _get_current_position(self, symbol: str) -> Optional[str]:
        """Devuelve la posición actual ('long'/'short'/None)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT side FROM trades
                    WHERE symbol = ? AND status = 'open'
                    ORDER BY entry_time DESC LIMIT 1
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                if row:
                    return 'long' if str(row[0]).lower() == 'buy' else 'short'
            return None
        except Exception:
            return None

    def _get_unrealized_pnl(self, symbol: str) -> float:
        """Calcula PnL no realizado de la posición abierta"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT entry_price, quantity, side
                    FROM trades
                    WHERE symbol = ? AND status = 'open'
                    ORDER BY entry_time DESC LIMIT 1
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                if not row:
                    return 0.0
                entry_price, qty, side = float(row[0]), float(row[1]), str(row[2]).lower()
                cursor.execute(
                    """
                    SELECT close FROM market_data
                    WHERE symbol = ?
                    ORDER BY timestamp DESC LIMIT 1
                    """,
                    (symbol,)
                )
                md = cursor.fetchone()
                if not md:
                    return 0.0
                last_price = float(md[0])
                diff = (last_price - entry_price) if side == 'buy' else (entry_price - last_price)
                return diff * qty
        except Exception:
            return 0.0

    def _get_total_runs(self, symbol: str) -> int:
        """Obtiene el total de ciclos/runs del símbolo"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(1) FROM trading_cycles WHERE symbol = ?
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
        except Exception:
            return 0

    # --------- Builders ---------
    def _build_cycle_data_from_trades(self, row: Tuple[Any, ...]) -> CycleData:
        """Construye CycleData desde datos de trades agrupados"""
        symbol, cycle_date, start_time, end_time, total_trades, closed_trades, winning_trades, total_pnl, avg_pnl_pct, leverage_min, leverage_max, leverage_avg = row
        
        # Convertir timestamps
        start_dt = datetime.fromisoformat(str(start_time)) if isinstance(start_time, str) else datetime.fromtimestamp(start_time)
        end_dt = datetime.fromisoformat(str(end_time)) if isinstance(end_time, str) else datetime.fromtimestamp(end_time)
        
        # Calcular métricas
        duration_days = (end_dt - start_dt).days if end_dt else 1
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0
        daily_pnl = total_pnl / max(duration_days, 1)
        
        # Generar cycle_id único
        cycle_id = f"{symbol}_{cycle_date}_{int(start_dt.timestamp())}"
        
        return CycleData(
            cycle_id=cycle_id,
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            start_balance=1000.0,  # Valor base para cálculo
            end_balance=1000.0 + total_pnl,
            pnl=total_pnl,
            pnl_percentage=avg_pnl_pct,
            total_trades=total_trades,
            win_rate=win_rate,
            avg_daily_pnl=daily_pnl,
            max_drawdown=0.0,  # Se calcularía con datos más detallados
            sharpe_ratio=0.0,  # Se calcularía con datos más detallados
            duration_days=duration_days,
            status='completed' if closed_trades == total_trades else 'active',
            roi=avg_pnl_pct,
            profit_factor=1.0,  # Se calcularía con datos más detallados
            leverage_min=float(leverage_min) if leverage_min else 1.0,
            leverage_max=float(leverage_max) if leverage_max else 1.0
        )

    def _build_cycle_data_from_row(self, row: Tuple[Any, ...]) -> CycleData:
        cycle_id, symbol, start_date, end_date, start_balance, end_balance, total_trades, status = row
        start_dt = datetime.fromtimestamp(start_date) if isinstance(start_date, (int, float)) else datetime.fromisoformat(str(start_date))
        end_dt = None
        if end_date:
            end_dt = datetime.fromtimestamp(end_date) if isinstance(end_date, (int, float)) else datetime.fromisoformat(str(end_date))
        pnl = (float(end_balance) - float(start_balance)) if end_dt else 0.0
        duration_days = (end_dt - start_dt).days if end_dt else 0
        pnl_pct = (pnl / float(start_balance) * 100) if float(start_balance) != 0 else 0.0
        return CycleData(
            cycle_id=str(cycle_id),
            symbol=str(symbol),
            start_date=start_dt,
            end_date=end_dt,
            start_balance=float(start_balance),
            end_balance=float(end_balance) if end_dt else float(start_balance),
            pnl=float(pnl),
            pnl_percentage=float(pnl_pct),
            total_trades=int(total_trades or 0),
            win_rate=0.0,
            avg_daily_pnl=(pnl / max(1, duration_days)) if duration_days else 0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            duration_days=int(duration_days),
            status=str(status),
            roi=float(pnl_pct),
            profit_factor=0.0,
        )

    def _build_trade_data_from_row(self, row: Tuple[Any, ...], include_exit: bool = False) -> TradeData:
        if include_exit:
            trade_id, symbol, side, entry_time, exit_time, entry_price, exit_price, quantity, pnl, pnl_percentage, status, stop_loss, take_profit = row
        else:
            trade_id, symbol, side, entry_time, entry_price, quantity, stop_loss, take_profit, status = row
            exit_time = None
            exit_price = None
            pnl = None
            pnl_percentage = None
        entry_dt = datetime.fromtimestamp(entry_time) if isinstance(entry_time, (int, float)) else datetime.fromisoformat(str(entry_time))
        exit_dt = None
        if exit_time:
            exit_dt = datetime.fromtimestamp(exit_time) if isinstance(exit_time, (int, float)) else datetime.fromisoformat(str(exit_time))
        duration = None
        if exit_dt:
            duration = int((exit_dt - entry_dt).total_seconds() // 60)
        return TradeData(
            trade_id=str(trade_id),
            symbol=str(symbol),
            side=str(side),
            entry_time=entry_dt,
            exit_time=exit_dt,
            entry_price=float(entry_price),
            exit_price=float(exit_price) if exit_price is not None else None,
            quantity=float(quantity),
            pnl=float(pnl) if pnl is not None else None,
            pnl_percentage=float(pnl_percentage) if pnl_percentage is not None else None,
            duration_minutes=duration,
            status=str(status),
            stop_loss=float(stop_loss) if stop_loss is not None else None,
            take_profit=float(take_profit) if take_profit is not None else None,
        )

    # --------- Mock generators / fallbacks ---------
    def _generate_mock_market_data(self, symbol: str, timeframe: str, limit: int) -> List[MarketData]:
        now = datetime.now()
        step = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240}.get(timeframe, 1)
        data: List[MarketData] = []
        price = 40000.0 if 'BTC' in symbol else 2000.0
        for i in range(limit):
            ts = now - timedelta(minutes=step * (limit - 1 - i))
            change = np.random.normal(0, price * 0.001)
            open_p = price
            close_p = max(1.0, price + change)
            high_p = max(open_p, close_p) + abs(np.random.normal(0, price * 0.0005))
            low_p = min(open_p, close_p) - abs(np.random.normal(0, price * 0.0005))
            vol = abs(np.random.normal(0, 1000))
            data.append(MarketData(symbol=symbol, timestamp=ts, open=open_p, high=high_p, low=low_p, close=close_p, volume=vol, timeframe=timeframe))
            price = close_p
        return data

    def _generate_mock_cycles_data(self, symbol: Optional[str], limit: int) -> List[CycleData]:
        symbols = [symbol] if symbol else self.config['symbols'][:3]
        cycles: List[CycleData] = []
        for s in symbols:
            for i in range(max(1, limit // max(1, len(symbols)))):
                start = datetime.now() - timedelta(days=np.random.randint(10, 120))
                duration = np.random.randint(5, 60)
                end = start + timedelta(days=duration)
                start_bal = np.random.uniform(800, 1200)
                end_bal = start_bal * np.random.uniform(0.9, 1.2)
                pnl = end_bal - start_bal
                pnl_pct = pnl / start_bal * 100
                
                # Generar leverage min/max realista
                leverage_min = np.random.uniform(1.0, 3.0)
                leverage_max = np.random.uniform(leverage_min, 10.0)
                
                cycles.append(CycleData(
                    cycle_id=f"{s}_{i}",
                    symbol=s,
                    start_date=start,
                    end_date=end,
                    start_balance=start_bal,
                    end_balance=end_bal,
                    pnl=pnl,
                    pnl_percentage=pnl_pct,
                    total_trades=np.random.randint(5, 60),
                    win_rate=np.random.uniform(40, 70),
                    avg_daily_pnl=pnl / max(1, duration),
                    max_drawdown=np.random.uniform(3, 20),
                    sharpe_ratio=np.random.uniform(0.2, 2.0),
                    duration_days=duration,
                    status='completed',
                    leverage_min=leverage_min,
                    leverage_max=leverage_max
                ))
        return cycles[:limit]

    def _get_default_performance_metrics(self) -> Dict[str, Any]:
        return {
            'total_pnl': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'period_hours': 24,
            'symbols_active': 0,
            'avg_trade_duration': 0.0,
            'best_symbol': None,
            'worst_symbol': None,
        }

    def _calculate_avg_trade_duration(self, df: pd.DataFrame) -> float:
        try:
            entry = pd.to_datetime(df['entry_time'])
            exit_ = pd.to_datetime(df['exit_time'])
            durations = (exit_ - entry).dt.total_seconds() / 60.0
            return float(durations.mean()) if len(durations) else 0.0
        except Exception:
            return 0.0

    def _get_best_performing_symbol(self, df: pd.DataFrame) -> Optional[str]:
        try:
            return df.groupby('symbol')['pnl'].sum().idxmax()
        except Exception:
            return None

    def _get_worst_performing_symbol(self, df: pd.DataFrame) -> Optional[str]:
        try:
            return df.groupby('symbol')['pnl'].sum().idxmin()
        except Exception:
            return None

    def _get_real_model_data(self) -> Dict[str, Any]:
        # Placeholder de integración real
        return self._generate_mock_model_data()

    def _generate_mock_model_data(self) -> Dict[str, Any]:
        return {
            'status': 'ready',
            'metrics': {
                'accuracy': 0.72,
                'precision': 0.70,
                'recall': 0.68,
                'f1_score': 0.69,
                'auc_roc': 0.78,
                'loss': 0.45,
                'predictions_today': 124,
                'avg_confidence': 0.66,
                'last_retrain': datetime.now().isoformat(),
                'drift_score': 0.12,
                'model_version': 'v1.0.0'
            }
        }

    def health_check(self) -> Dict[str, Any]:
        try:
            status = {
                'db_connected': self._connected,
                'cache_items': len(self.cache),
                'cache_ttl_sec': self.cache_ttl,
                'symbols': self.config.get('symbols', []),
                'last_updated': datetime.now().isoformat(),
            }
            if self._connected:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return status
        except Exception as e:
            return {'db_connected': False, 'error': str(e), 'last_updated': datetime.now().isoformat()}

    def get_summary(self) -> Dict[str, Any]:
        return {
            'connected': self._connected,
            'symbols_tracked': len(self.config.get('symbols', [])),
            'cache_keys': list(self.cache.keys()),
            'config': self.config,
        }