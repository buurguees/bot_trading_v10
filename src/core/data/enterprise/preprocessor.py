# preprocessor.py - Preprocesador de datos en tiempo real
# Ubicación: C:\TradingBot_v10\data\enterprise\preprocessor.py

"""
Preprocesador de datos en tiempo real para trading enterprise.

Características principales:
- Procesamiento de streaming de datos
- Cálculo de indicadores técnicos optimizado
- Detección de anomalías y gaps
- Cache de features para ML
- Integración con Redis
- Optimización con Numba
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import redis
import json
from dataclasses import dataclass
import asyncio

# Optimización numérica
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Indicadores técnicos calculados"""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    atr: float
    vwap: float
    sma_20: float
    ema_12: float
    ema_26: float
    volume_ratio: float
    price_change_1h: float
    price_change_4h: float
    price_change_24h: float

class DataPreprocessor:
    """
    Preprocesador de datos en tiempo real para trading enterprise
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el preprocesador
        
        Args:
            config: Configuración del preprocesador
        """
        self.config = config or self._default_config()
        
        # Redis para cache
        self.redis_client = None
        self.setup_redis()
        
        # Cache de datos
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.feature_cache: Dict[str, Dict[str, Any]] = {}
        
        # Configuración de indicadores
        self.indicator_config = self.config.get('indicators', {})
        
        # Métricas de performance
        self.processed_candles = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("DataPreprocessor inicializado")
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'indicators': {
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bollinger_period': 20,
                'bollinger_std': 2,
                'atr_period': 14,
                'sma_periods': [20, 50],
                'ema_periods': [12, 26]
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None
            },
            'cache': {
                'ttl_seconds': 3600,  # 1 hora
                'max_size': 10000
            },
            'anomaly_detection': {
                'price_threshold': 3.0,  # 3 desviaciones estándar
                'volume_threshold': 5.0,
                'gap_threshold_minutes': 5
            }
        }
    
    def setup_redis(self):
        """Configura Redis para cache"""
        try:
            redis_config = self.config.get('redis', {})
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password'),
                decode_responses=True
            )
            
            # Verificar conexión
            self.redis_client.ping()
            logger.info("✅ Redis conectado para cache")
            
        except Exception as e:
            logger.warning(f"Redis no disponible: {e}")
            self.redis_client = None
    
    def process_candles(self, candles: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Procesa velas y calcula indicadores técnicos
        
        Args:
            candles: DataFrame con datos OHLCV
            symbol: Símbolo a procesar
            
        Returns:
            DataFrame con indicadores técnicos
        """
        try:
            if len(candles) < 20:  # Mínimo para indicadores
                return candles
            
            # Crear copia para no modificar original
            processed = candles.copy()
            
            # Calcular indicadores técnicos
            processed = self._calculate_technical_indicators(processed)
            
            # Detectar anomalías
            processed = self._detect_anomalies(processed)
            
            # Calcular features para ML
            processed = self._calculate_ml_features(processed)
            
            # Actualizar cache
            self._update_cache(symbol, processed)
            
            # Actualizar métricas
            self.processed_candles += len(processed)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error procesando velas para {symbol}: {e}")
            return candles
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        try:
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'].values, self.indicator_config['rsi_period'])
            
            # MACD
            macd, macd_signal, macd_hist = self._calculate_macd(
                df['close'].values,
                self.indicator_config['macd_fast'],
                self.indicator_config['macd_slow'],
                self.indicator_config['macd_signal']
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
                df['close'].values,
                self.indicator_config['bollinger_period'],
                self.indicator_config['bollinger_std']
            )
            df['bollinger_upper'] = bb_upper
            df['bollinger_middle'] = bb_middle
            df['bollinger_lower'] = bb_lower
            
            # ATR
            df['atr'] = self._calculate_atr(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                self.indicator_config['atr_period']
            )
            
            # VWAP
            df['vwap'] = self._calculate_vwap(df)
            
            # SMA
            for period in self.indicator_config['sma_periods']:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            
            # EMA
            for period in self.indicator_config['ema_periods']:
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # Ratios de volumen
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
            
            # Cambios de precio
            df['price_change_1h'] = df['close'].pct_change(periods=60)  # 1 hora
            df['price_change_4h'] = df['close'].pct_change(periods=240)  # 4 horas
            df['price_change_24h'] = df['close'].pct_change(periods=1440)  # 24 horas
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores técnicos: {e}")
            return df
    
    @jit(nopython=True) if NUMBA_AVAILABLE else lambda x: x
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcula RSI optimizado con Numba"""
        rsi = np.zeros_like(prices)
        
        for i in range(period, len(prices)):
            gains = 0.0
            losses = 0.0
            
            for j in range(i - period + 1, i + 1):
                change = prices[j] - prices[j - 1]
                if change > 0:
                    gains += change
                else:
                    losses -= change
            
            avg_gain = gains / period
            avg_loss = losses / period
            
            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    @jit(nopython=True) if NUMBA_AVAILABLE else lambda x: x
    def _calculate_macd(self, prices: np.ndarray, fast: int, slow: int, signal: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula MACD optimizado con Numba"""
        macd = np.zeros_like(prices)
        macd_signal = np.zeros_like(prices)
        macd_hist = np.zeros_like(prices)
        
        # Calcular EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # MACD = EMA_fast - EMA_slow
        macd = ema_fast - ema_slow
        
        # Señal MACD = EMA del MACD
        macd_signal = self._calculate_ema(macd, signal)
        
        # Histograma = MACD - Señal
        macd_hist = macd - macd_signal
        
        return macd, macd_signal, macd_hist
    
    @jit(nopython=True) if NUMBA_AVAILABLE else lambda x: x
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA optimizado con Numba"""
        ema = np.zeros_like(prices)
        multiplier = 2.0 / (period + 1.0)
        
        # Primer valor
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1.0 - multiplier))
        
        return ema
    
    @jit(nopython=True) if NUMBA_AVAILABLE else lambda x: x
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int, std_dev: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula Bollinger Bands optimizado con Numba"""
        upper = np.zeros_like(prices)
        middle = np.zeros_like(prices)
        lower = np.zeros_like(prices)
        
        for i in range(period - 1, len(prices)):
            # Calcular SMA
            sma = np.mean(prices[i - period + 1:i + 1])
            middle[i] = sma
            
            # Calcular desviación estándar
            std = np.std(prices[i - period + 1:i + 1])
            
            # Calcular bandas
            upper[i] = sma + (std * std_dev)
            lower[i] = sma - (std * std_dev)
        
        return upper, middle, lower
    
    @jit(nopython=True) if NUMBA_AVAILABLE else lambda x: x
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
        """Calcula ATR optimizado con Numba"""
        atr = np.zeros_like(closes)
        
        for i in range(1, len(closes)):
            # True Range
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            tr = max(tr1, tr2, tr3)
            
            if i < period:
                atr[i] = np.mean([max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1])) for j in range(1, i + 1)])
            else:
                atr[i] = ((atr[i - 1] * (period - 1)) + tr) / period
        
        return atr
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calcula VWAP"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            return vwap
        except Exception as e:
            logger.error(f"Error calculando VWAP: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def _detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta anomalías en los datos"""
        try:
            anomaly_config = self.config.get('anomaly_detection', {})
            
            # Detectar gaps de tiempo
            df['time_gap'] = df.index.to_series().diff() > timedelta(minutes=anomaly_config.get('gap_threshold_minutes', 5))
            
            # Detectar anomalías de precio
            price_std = df['close'].rolling(window=20).std()
            price_mean = df['close'].rolling(window=20).mean()
            df['price_anomaly'] = abs(df['close'] - price_mean) > (price_std * anomaly_config.get('price_threshold', 3.0))
            
            # Detectar anomalías de volumen
            volume_std = df['volume'].rolling(window=20).std()
            volume_mean = df['volume'].rolling(window=20).mean()
            df['volume_anomaly'] = abs(df['volume'] - volume_mean) > (volume_std * anomaly_config.get('volume_threshold', 5.0))
            
            # Marcar datos con anomalías
            df['is_anomaly'] = df['time_gap'] | df['price_anomaly'] | df['volume_anomaly']
            
            return df
            
        except Exception as e:
            logger.error(f"Error detectando anomalías: {e}")
            return df
    
    def _calculate_ml_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula features para ML"""
        try:
            # Features de precio normalizado
            df['price_normalized'] = (df['close'] - df['close'].rolling(window=20).mean()) / df['close'].rolling(window=20).std()
            
            # Features de volumen normalizado
            df['volume_normalized'] = (df['volume'] - df['volume'].rolling(window=20).mean()) / df['volume'].rolling(window=20).std()
            
            # Features de volatilidad
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            # Features de momentum
            df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
            
            # Features de tendencia
            df['trend_strength'] = abs(df['close'] - df['sma_20']) / df['sma_20']
            
            # Features de RSI normalizado
            df['rsi_normalized'] = (df['rsi'] - 50) / 50
            
            # Features de MACD normalizado
            df['macd_normalized'] = df['macd'] / df['close']
            
            # Features de Bollinger Bands
            df['bb_position'] = (df['close'] - df['bollinger_lower']) / (df['bollinger_upper'] - df['bollinger_lower'])
            df['bb_width'] = (df['bollinger_upper'] - df['bollinger_lower']) / df['bollinger_middle']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando features ML: {e}")
            return df
    
    def _update_cache(self, symbol: str, data: pd.DataFrame):
        """Actualiza cache de datos"""
        try:
            # Actualizar cache local
            self.data_cache[symbol] = data.tail(1000)  # Mantener últimos 1000 registros
            
            # Actualizar Redis si está disponible
            if self.redis_client:
                cache_key = f"candles:{symbol}"
                cache_data = {
                    'timestamp': data.index[-1].isoformat(),
                    'data': data.tail(100).to_json(orient='records')
                }
                
                self.redis_client.setex(
                    cache_key,
                    self.config['cache']['ttl_seconds'],
                    json.dumps(cache_data, default=str)
                )
            
        except Exception as e:
            logger.error(f"Error actualizando cache: {e}")
    
    async def get_cached_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtiene datos del cache"""
        try:
            # Intentar Redis primero
            if self.redis_client:
                cache_key = f"candles:{symbol}"
                cached = self.redis_client.get(cache_key)
                
                if cached:
                    self.cache_hits += 1
                    data = json.loads(cached)
                    df = pd.read_json(data['data'], orient='records')
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.set_index('timestamp')
                    return df.tail(limit)
            
            # Fallback a cache local
            if symbol in self.data_cache:
                self.cache_hits += 1
                return self.data_cache[symbol].tail(limit)
            
            self.cache_misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo datos del cache: {e}")
            return None
    
    def get_technical_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Extrae indicadores técnicos de un DataFrame"""
        try:
            if len(df) == 0:
                return TechnicalIndicators(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            latest = df.iloc[-1]
            
            return TechnicalIndicators(
                rsi=latest.get('rsi', 0),
                macd=latest.get('macd', 0),
                macd_signal=latest.get('macd_signal', 0),
                macd_histogram=latest.get('macd_histogram', 0),
                bollinger_upper=latest.get('bollinger_upper', 0),
                bollinger_middle=latest.get('bollinger_middle', 0),
                bollinger_lower=latest.get('bollinger_lower', 0),
                atr=latest.get('atr', 0),
                vwap=latest.get('vwap', 0),
                sma_20=latest.get('sma_20', 0),
                ema_12=latest.get('ema_12', 0),
                ema_26=latest.get('ema_26', 0),
                volume_ratio=latest.get('volume_ratio', 0),
                price_change_1h=latest.get('price_change_1h', 0),
                price_change_4h=latest.get('price_change_4h', 0),
                price_change_24h=latest.get('price_change_24h', 0)
            )
            
        except Exception as e:
            logger.error(f"Error extrayendo indicadores técnicos: {e}")
            return TechnicalIndicators(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance"""
        try:
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            
            return {
                'processed_candles': self.processed_candles,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_hit_rate': cache_hit_rate,
                'cached_symbols': len(self.data_cache),
                'redis_connected': self.redis_client is not None,
                'numba_available': NUMBA_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {}
    
    async def cleanup(self):
        """Limpieza de recursos"""
        try:
            if self.redis_client:
                self.redis_client.close()
            
            self.data_cache.clear()
            self.feature_cache.clear()
            
            logger.info("✅ DataPreprocessor cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")
