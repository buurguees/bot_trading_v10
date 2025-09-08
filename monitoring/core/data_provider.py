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
from typing import Dict, List, Optional, Any, Tuple
import json
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

# Importaciones del proyecto
try:
    from data.database import DatabaseManager
    from trading.position_manager import PositionManager
    from models.prediction_engine import PredictionEngine
    from config.user_config import UserConfig
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

class DataProvider:
    """
    Proveedor centralizado de datos para el sistema de monitoreo
    
    Gestiona la obtención de datos desde múltiples fuentes y proporciona
    una interfaz unificada para el dashboard.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el proveedor de datos
        
        Args:
            config_path (str, optional): Ruta al archivo de configuración
        """
        self.config_path = config_path
        self.db_manager = None
        self.position_manager = None
        self.prediction_engine = None
        self.user_config = None
        
        # Cache de datos
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 60  # TTL en segundos
        
        # Estado de conexión
        self._connected = False
        self._last_error = None
        
        # Lock para thread safety
        self._lock = threading.RLock()
        
        # Inicializar conexiones
        self._initialize_connections()
        
        logger.info("DataProvider inicializado")
    
    def _initialize_connections(self):
        """Inicializa todas las conexiones a fuentes de datos"""
        try:
            # Inicializar configuración de usuario
            if UserConfig:
                self.user_config = UserConfig()
            
            # Inicializar base de datos
            if DatabaseManager:
                self.db_manager = DatabaseManager()
                self.db_manager.initialize()
            
            # Inicializar gestor de posiciones
            if PositionManager:
                self.position_manager = PositionManager()
            
            # Inicializar motor de predicción
            if PredictionEngine:
                self.prediction_engine = PredictionEngine()
            
            self._connected = True
            logger.info("Conexiones del DataProvider inicializadas correctamente")
            
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.error(f"Error al inicializar conexiones: {e}")
    
    def is_connected(self) -> bool:
        """Verifica si el proveedor está conectado a las fuentes de datos"""
        return self._connected
    
    def get_last_error(self) -> Optional[str]:
        """Obtiene el último error ocurrido"""
        return self._last_error
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Obtiene datos del cache si están vigentes"""
        with self._lock:
            if key in self._cache:
                timestamp = self._cache_timestamps.get(key, 0)
                if time.time() - timestamp < self._cache_ttl:
                    return self._cache[key]
                else:
                    # Cache expirado
                    del self._cache[key]
                    del self._cache_timestamps[key]
            return None
    
    def _set_cache(self, key: str, data: Any):
        """Guarda datos en el cache"""
        with self._lock:
            self._cache[key] = data
            self._cache_timestamps[key] = time.time()
    
    def get_configured_symbols(self) -> List[str]:
        """
        Obtiene la lista de símbolos configurados
        
        Returns:
            List[str]: Lista de símbolos configurados
        """
        cache_key = "configured_symbols"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            if self.user_config:
                symbols = self.user_config.get_trading_symbols()
            else:
                # Fallback: símbolos por defecto
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
            
            self._set_cache(cache_key, symbols)
            return symbols
            
        except Exception as e:
            logger.error(f"Error al obtener símbolos configurados: {e}")
            return ['BTCUSDT', 'ETHUSDT']  # Fallback mínimo
    
    def get_symbol_metrics(self, symbol: str) -> SymbolMetrics:
        """
        Obtiene métricas completas para un símbolo específico
        
        Args:
            symbol (str): Símbolo a consultar
            
        Returns:
            SymbolMetrics: Métricas del símbolo
        """
        cache_key = f"symbol_metrics_{symbol}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            # Obtener datos básicos
            trades_data = self._get_symbol_trades(symbol)
            balance_data = self._get_symbol_balance(symbol)
            
            # Calcular métricas
            total_trades = len(trades_data)
            if total_trades > 0:
                winning_trades = len([t for t in trades_data if t.get('pnl', 0) > 0])
                losing_trades = total_trades - winning_trades
                win_rate = (winning_trades / total_trades) * 100
                avg_pnl = np.mean([t.get('pnl', 0) for t in trades_data])
                
                # Calcular Sharpe Ratio simplificado
                pnl_list = [t.get('pnl', 0) for t in trades_data]
                if len(pnl_list) > 1:
                    sharpe_ratio = np.mean(pnl_list) / np.std(pnl_list) if np.std(pnl_list) != 0 else 0
                else:
                    sharpe_ratio = 0
                
                # Calcular Max Drawdown
                balance_series = self._calculate_cumulative_balance(trades_data, balance_data.get('initial_balance', 1000))
                max_drawdown = self._calculate_max_drawdown(balance_series)
            else:
                winning_trades = losing_trades = 0
                win_rate = avg_pnl = sharpe_ratio = max_drawdown = 0
            
            # Obtener estado actual
            current_status = self._get_symbol_status(symbol)
            last_signal_data = self._get_last_signal(symbol)
            
            # Calcular progreso hacia objetivo
            current_balance = balance_data.get('current_balance', 1000)
            target_balance = balance_data.get('target_balance', 2000)
            balance_progress = ((current_balance - balance_data.get('initial_balance', 1000)) / 
                              (target_balance - balance_data.get('initial_balance', 1000))) * 100
            balance_progress = max(0, min(100, balance_progress))  # Limitar entre 0-100%
            
            metrics = SymbolMetrics(
                symbol=symbol,
                win_rate=win_rate,
                total_runs=self._get_total_runs(symbol),
                avg_pnl=avg_pnl,
                balance_progress=balance_progress,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                current_status=current_status,
                last_signal=last_signal_data.get('signal', 'hold'),
                last_signal_time=last_signal_data.get('timestamp', datetime.now()),
                current_balance=current_balance,
                target_balance=target_balance,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades
            )
            
            self._set_cache(cache_key, metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error al obtener métricas para {symbol}: {e}")
            # Retornar métricas por defecto en caso de error
            return SymbolMetrics(
                symbol=symbol,
                win_rate=0,
                total_runs=0,
                avg_pnl=0,
                balance_progress=0,
                sharpe_ratio=0,
                max_drawdown=0,
                current_status='error',
                last_signal='hold',
                last_signal_time=datetime.now(),
                current_balance=1000,
                target_balance=2000,
                total_trades=0,
                winning_trades=0,
                losing_trades=0
            )
    
    def get_all_symbols_metrics(self) -> Dict[str, SymbolMetrics]:
        """
        Obtiene métricas para todos los símbolos configurados
        
        Returns:
            Dict[str, SymbolMetrics]: Diccionario con métricas por símbolo
        """
        symbols = self.get_configured_symbols()
        metrics = {}
        
        for symbol in symbols:
            metrics[symbol] = self.get_symbol_metrics(symbol)
        
        return metrics
    
    def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 1000) -> pd.DataFrame:
        """
        Obtiene datos históricos de precios para un símbolo
        
        Args:
            symbol (str): Símbolo a consultar
            timeframe (str): Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit (int): Número máximo de velas
            
        Returns:
            pd.DataFrame: DataFrame con datos OHLCV
        """
        cache_key = f"historical_data_{symbol}_{timeframe}_{limit}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            if self.db_manager:
                # Obtener desde base de datos
                data = self.db_manager.get_price_data(symbol, timeframe, limit)
            else:
                # Generar datos de ejemplo para desarrollo
                data = self._generate_sample_ohlcv(symbol, limit)
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
            
            self._set_cache(cache_key, df)
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener datos históricos para {symbol}: {e}")
            return pd.DataFrame()
    
    def get_top_cycles(self, limit: int = 20) -> List[CycleData]:
        """
        Obtiene los mejores ciclos de trading ordenados por rendimiento
        
        Args:
            limit (int): Número máximo de ciclos a retornar
            
        Returns:
            List[CycleData]: Lista de ciclos ordenados por rendimiento
        """
        cache_key = f"top_cycles_{limit}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            if self.db_manager:
                cycles_data = self.db_manager.get_top_cycles(limit)
            else:
                # Generar datos de ejemplo
                cycles_data = self._generate_sample_cycles(limit)
            
            cycles = []
            for cycle_raw in cycles_data:
                cycle = CycleData(
                    cycle_id=cycle_raw.get('cycle_id', f"cycle_{len(cycles)}"),
                    symbol=cycle_raw.get('symbol', 'BTCUSDT'),
                    start_date=cycle_raw.get('start_date', datetime.now() - timedelta(days=30)),
                    end_date=cycle_raw.get('end_date'),
                    start_balance=cycle_raw.get('start_balance', 1000),
                    end_balance=cycle_raw.get('end_balance', 1200),
                    pnl=cycle_raw.get('pnl', 200),
                    pnl_percentage=cycle_raw.get('pnl_percentage', 20),
                    total_trades=cycle_raw.get('total_trades', 15),
                    win_rate=cycle_raw.get('win_rate', 65),
                    avg_daily_pnl=cycle_raw.get('avg_daily_pnl', 6.67),
                    max_drawdown=cycle_raw.get('max_drawdown', 5),
                    sharpe_ratio=cycle_raw.get('sharpe_ratio', 1.8),
                    duration_days=cycle_raw.get('duration_days', 30),
                    status=cycle_raw.get('status', 'completed')
                )
                cycles.append(cycle)
            
            # Ordenar por PnL porcentual descendente
            cycles.sort(key=lambda x: x.pnl_percentage, reverse=True)
            
            self._set_cache(cache_key, cycles)
            return cycles
            
        except Exception as e:
            logger.error(f"Error al obtener top cycles: {e}")
            return []
    
    def get_recent_trades(self, symbol: Optional[str] = None, limit: int = 50) -> List[TradeData]:
        """
        Obtiene los trades más recientes
        
        Args:
            symbol (str, optional): Símbolo específico o None para todos
            limit (int): Número máximo de trades
            
        Returns:
            List[TradeData]: Lista de trades recientes
        """
        cache_key = f"recent_trades_{symbol}_{limit}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            if self.db_manager:
                trades_data = self.db_manager.get_recent_trades(symbol, limit)
            else:
                trades_data = self._generate_sample_trades(symbol, limit)
            
            trades = []
            for trade_raw in trades_data:
                trade = TradeData(
                    trade_id=trade_raw.get('trade_id', f"trade_{len(trades)}"),
                    symbol=trade_raw.get('symbol', 'BTCUSDT'),
                    side=trade_raw.get('side', 'buy'),
                    entry_time=trade_raw.get('entry_time', datetime.now()),
                    exit_time=trade_raw.get('exit_time'),
                    entry_price=trade_raw.get('entry_price', 50000),
                    exit_price=trade_raw.get('exit_price'),
                    quantity=trade_raw.get('quantity', 0.01),
                    pnl=trade_raw.get('pnl'),
                    pnl_percentage=trade_raw.get('pnl_percentage'),
                    duration_minutes=trade_raw.get('duration_minutes'),
                    status=trade_raw.get('status', 'open'),
                    stop_loss=trade_raw.get('stop_loss'),
                    take_profit=trade_raw.get('take_profit')
                )
                trades.append(trade)
            
            self._set_cache(cache_key, trades)
            return trades
            
        except Exception as e:
            logger.error(f"Error al obtener trades recientes: {e}")
            return []
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del modelo de IA
        
        Returns:
            Dict[str, Any]: Estado del modelo
        """
        cache_key = "model_status"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            if self.prediction_engine:
                status = self.prediction_engine.get_model_status()
            else:
                # Estado de ejemplo para desarrollo
                status = {
                    'model_loaded': True,
                    'last_training': datetime.now() - timedelta(hours=2),
                    'accuracy': 68.5,
                    'total_predictions': 1247,
                    'successful_predictions': 854,
                    'model_version': '10.2.1',
                    'training_status': 'completed',
                    'next_training': datetime.now() + timedelta(hours=22),
                    'features_count': 47,
                    'model_size_mb': 12.5
                }
            
            self._set_cache(cache_key, status)
            return status
            
        except Exception as e:
            logger.error(f"Error al obtener estado del modelo: {e}")
            return {'error': str(e)}
    
    def _get_symbol_trades(self, symbol: str) -> List[Dict]:
        """Obtiene trades para un símbolo específico"""
        if self.db_manager:
            return self.db_manager.get_symbol_trades(symbol)
        else:
            # Datos de ejemplo
            return [
                {'trade_id': f'{symbol}_1', 'pnl': 15.5, 'timestamp': datetime.now()},
                {'trade_id': f'{symbol}_2', 'pnl': -8.2, 'timestamp': datetime.now()},
                {'trade_id': f'{symbol}_3', 'pnl': 22.1, 'timestamp': datetime.now()}
            ]
    
    def _get_symbol_balance(self, symbol: str) -> Dict:
        """Obtiene información de balance para un símbolo"""
        if self.position_manager:
            return self.position_manager.get_symbol_balance(symbol)
        else:
            return {
                'current_balance': 1150.0,
                'initial_balance': 1000.0,
                'target_balance': 2000.0
            }
    
    def _get_symbol_status(self, symbol: str) -> str:
        """Obtiene el estado actual de un símbolo"""
        if self.position_manager:
            return self.position_manager.get_symbol_status(symbol)
        else:
            return 'active'  # Estado por defecto
    
    def _get_last_signal(self, symbol: str) -> Dict:
        """Obtiene la última señal generada para un símbolo"""
        if self.prediction_engine:
            return self.prediction_engine.get_last_signal(symbol)
        else:
            return {
                'signal': 'buy',
                'timestamp': datetime.now() - timedelta(minutes=15),
                'confidence': 0.75
            }
    
    def _get_total_runs(self, symbol: str) -> int:
        """Obtiene el total de runs ejecutados para un símbolo"""
        if self.db_manager:
            return self.db_manager.get_total_runs(symbol)
        else:
            return np.random.randint(5, 50)  # Valor de ejemplo
    
    def _calculate_cumulative_balance(self, trades: List[Dict], initial_balance: float) -> List[float]:
        """Calcula el balance cumulativo a partir de una lista de trades"""
        balances = [initial_balance]
        current_balance = initial_balance
        
        for trade in trades:
            current_balance += trade.get('pnl', 0)
            balances.append(current_balance)
        
        return balances
    
    def _calculate_max_drawdown(self, balance_series: List[float]) -> float:
        """Calcula el máximo drawdown de una serie de balances"""
        if len(balance_series) < 2:
            return 0
        
        peak = balance_series[0]
        max_dd = 0
        
        for balance in balance_series[1:]:
            if balance > peak:
                peak = balance
            else:
                drawdown = ((peak - balance) / peak) * 100
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _generate_sample_ohlcv(self, symbol: str, limit: int) -> List[Dict]:
        """Genera datos OHLCV de ejemplo para desarrollo"""
        data = []
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.5
        current_time = datetime.now() - timedelta(hours=limit)
        
        for i in range(limit):
            # Generar precio con movimiento aleatorio
            price_change = np.random.normal(0, base_price * 0.002)
            base_price += price_change
            base_price = max(base_price * 0.5, base_price)  # Evitar precios negativos
            
            high = base_price * (1 + abs(np.random.normal(0, 0.005)))
            low = base_price * (1 - abs(np.random.normal(0, 0.005)))
            open_price = base_price + np.random.normal(0, base_price * 0.001)
            close_price = base_price + np.random.normal(0, base_price * 0.001)
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': current_time + timedelta(hours=i),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': round(volume, 2)
            })
        
        return data
    
    def _generate_sample_cycles(self, limit: int) -> List[Dict]:
        """Genera datos de ciclos de ejemplo"""
        cycles = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
        
        for i in range(limit):
            start_date = datetime.now() - timedelta(days=np.random.randint(1, 365))
            duration = np.random.randint(7, 90)
            end_date = start_date + timedelta(days=duration)
            
            start_balance = 1000
            pnl_percentage = np.random.normal(15, 25)  # Media 15%, desviación 25%
            pnl = start_balance * (pnl_percentage / 100)
            end_balance = start_balance + pnl
            
            cycles.append({
                'cycle_id': f'cycle_{i+1:03d}',
                'symbol': np.random.choice(symbols),
                'start_date': start_date,
                'end_date': end_date,
                'start_balance': start_balance,
                'end_balance': end_balance,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'total_trades': np.random.randint(10, 50),
                'win_rate': np.random.uniform(45, 85),
                'avg_daily_pnl': pnl / duration,
                'max_drawdown': np.random.uniform(2, 15),
                'sharpe_ratio': np.random.uniform(0.5, 3.0),
                'duration_days': duration,
                'status': 'completed'
            })
        
        return cycles
    
    def _generate_sample_trades(self, symbol: Optional[str], limit: int) -> List[Dict]:
        """Genera datos de trades de ejemplo"""
        trades = []
        symbols = [symbol] if symbol else ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for i in range(limit):
            trade_symbol = np.random.choice(symbols)
            side = np.random.choice(['buy', 'sell'])
            entry_time = datetime.now() - timedelta(minutes=np.random.randint(0, 10080))  # Última semana
            
            # Determinar si el trade está cerrado
            is_closed = np.random.choice([True, False], p=[0.8, 0.2])
            
            if is_closed:
                duration = np.random.randint(5, 1440)  # 5 min a 24 horas
                exit_time = entry_time + timedelta(minutes=duration)
                pnl = np.random.normal(5, 15)  # PnL normal con media 5
                status = 'closed'
            else:
                exit_time = None
                pnl = None
                duration = None
                status = 'open'
            
            trades.append({
                'trade_id': f'trade_{i+1:05d}',
                'symbol': trade_symbol,
                'side': side,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': np.random.uniform(30000, 70000) if 'BTC' in trade_symbol else np.random.uniform(2000, 4000),
                'exit_price': None if not is_closed else np.random.uniform(30000, 70000),
                'quantity': round(np.random.uniform(0.001, 0.1), 6),
                'pnl': pnl,
                'pnl_percentage': (pnl / 1000) * 100 if pnl else None,
                'duration_minutes': duration,
                'status': status,
                'stop_loss': np.random.uniform(29000, 31000) if 'BTC' in trade_symbol else np.random.uniform(1900, 2100),
                'take_profit': np.random.uniform(69000, 71000) if 'BTC' in trade_symbol else np.random.uniform(3900, 4100)
            })
        
        return trades
    
    def clear_cache(self):
        """Limpia todo el cache de datos"""
        with self._lock:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cache de datos limpiado")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Obtiene información del estado del cache"""
        with self._lock:
            return {
                'cache_size': len(self._cache),
                'cache_keys': list(self._cache.keys()),
                'oldest_entry': min(self._cache_timestamps.values()) if self._cache_timestamps else None,
                'newest_entry': max(self._cache_timestamps.values()) if self._cache_timestamps else None
            }