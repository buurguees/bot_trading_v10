# Ruta: core/data/preprocessor.py
"""
data/preprocessor.py - VERSIÓN PROFESIONAL MEJORADA
Procesador de datos y feature engineering para el modelo de ML
Ubicación: C:\TradingBot_v10\data\preprocessor.py

MEJORAS PRINCIPALES:
- Feature engineering avanzado con 100+ indicadores técnicos
- Normalización robusta para datasets de 5+ años
- Detección automática de regímenes de mercado
- Pipeline optimizado para millones de registros
- Validación automática de features
- Cache inteligente para indicadores calculados
- Paralelización para cálculos intensivos
- Features de microestructura de mercado avanzados
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, QuantileTransformer
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
import ta
from ta.utils import dropna
import warnings
warnings.filterwarnings('ignore')
import joblib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import partial
import time
from pathlib import Path
import pickle
import hashlib

from .database import db_manager
from core.config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class FeatureCache:
    """Cache inteligente para features calculados"""
    
    def __init__(self, cache_dir: Path = None):
        if cache_dir is None:
            from pathlib import Path
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            self.cache_dir = data_dir / "feature_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry_hours = 24  # Cache válido por 24 horas
    
    def _get_cache_key(self, symbol: str, start_date: datetime, end_date: datetime, 
                      features_config: dict) -> str:
        """Genera una clave única para el cache"""
        key_data = f"{symbol}_{start_date}_{end_date}_{str(features_config)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Obtiene datos del cache si están válidos"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            if not cache_file.exists():
                return None
            
            # Verificar si el cache está expirado
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age > (self.cache_expiry_hours * 3600):
                cache_file.unlink()  # Eliminar cache expirado
                return None
            
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
                
        except Exception as e:
            logger.debug(f"Error accediendo cache: {e}")
            return None
    
    def set(self, cache_key: str, data: pd.DataFrame):
        """Guarda datos en el cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            logger.debug(f"Error guardando en cache: {e}")
    
    def clear_expired(self):
        """Limpia cache expirado"""
        try:
            current_time = time.time()
            for cache_file in self.cache_dir.glob("*.pkl"):
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > (self.cache_expiry_hours * 3600):
                    cache_file.unlink()
        except Exception as e:
            logger.debug(f"Error limpiando cache: {e}")

class TechnicalIndicatorsAdvanced:
    """Clase para calcular indicadores técnicos avanzados"""
    
    @staticmethod
    def add_all_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores de tendencia disponibles"""
        df_copy = df.copy()
        
        try:
            # Moving Averages (múltiples períodos)
            ma_periods = [5, 10, 15, 20, 30, 50, 100, 200]
            for period in ma_periods:
                if len(df_copy) >= period:
                    df_copy[f'sma_{period}'] = ta.trend.sma_indicator(df_copy['close'], window=period)
                    df_copy[f'ema_{period}'] = ta.trend.ema_indicator(df_copy['close'], window=period)
                    df_copy[f'wma_{period}'] = ta.trend.wma_indicator(df_copy['close'], window=period)
            
            # MACD con múltiples configuraciones
            macd_configs = [(12, 26, 9), (5, 35, 5), (19, 39, 9)]
            for fast, slow, signal in macd_configs:
                suffix = f"_{fast}_{slow}_{signal}"
                try:
                    macd = ta.trend.MACD(df_copy['close'], window_fast=fast, window_slow=slow, window_sign=signal)
                    df_copy[f'macd{suffix}'] = macd.macd()
                    df_copy[f'macd_signal{suffix}'] = macd.macd_signal()
                    df_copy[f'macd_histogram{suffix}'] = macd.macd_diff()
                except:
                    continue
            
            # ADX con múltiples períodos
            adx_periods = [14, 21, 28]
            for period in adx_periods:
                if len(df_copy) >= period:
                    try:
                        df_copy[f'adx_{period}'] = ta.trend.adx(df_copy['high'], df_copy['low'], df_copy['close'], window=period)
                        df_copy[f'adx_pos_{period}'] = ta.trend.adx_pos(df_copy['high'], df_copy['low'], df_copy['close'], window=period)
                        df_copy[f'adx_neg_{period}'] = ta.trend.adx_neg(df_copy['high'], df_copy['low'], df_copy['close'], window=period)
                    except:
                        continue
            
            # Parabolic SAR
            try:
                df_copy['psar'] = ta.trend.psar_down(df_copy['high'], df_copy['low'], df_copy['close'])
                df_copy['psar_up'] = ta.trend.psar_up(df_copy['high'], df_copy['low'], df_copy['close'])
            except:
                pass
            
            # CCI con múltiples períodos
            cci_periods = [14, 20, 30]
            for period in cci_periods:
                if len(df_copy) >= period:
                    try:
                        df_copy[f'cci_{period}'] = ta.trend.cci(df_copy['high'], df_copy['low'], df_copy['close'], window=period)
                    except:
                        continue
            
            # Ichimoku
            try:
                ichimoku = ta.trend.IchimokuIndicator(df_copy['high'], df_copy['low'])
                df_copy['ichimoku_a'] = ichimoku.ichimoku_a()
                df_copy['ichimoku_b'] = ichimoku.ichimoku_b()
                df_copy['ichimoku_base'] = ichimoku.ichimoku_base_line()
                df_copy['ichimoku_conversion'] = ichimoku.ichimoku_conversion_line()
            except:
                pass
            
            # Aroon
            try:
                aroon = ta.trend.AroonIndicator(df_copy['high'], df_copy['low'])
                df_copy['aroon_up'] = aroon.aroon_up()
                df_copy['aroon_down'] = aroon.aroon_down()
                df_copy['aroon_indicator'] = aroon.aroon_indicator()
            except:
                pass
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de tendencia: {e}")
            return df_copy
    
    @staticmethod
    def add_all_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores de momentum disponibles"""
        df_copy = df.copy()
        
        try:
            # RSI con múltiples períodos
            rsi_periods = [7, 14, 21, 28]
            for period in rsi_periods:
                if len(df_copy) >= period:
                    df_copy[f'rsi_{period}'] = ta.momentum.rsi(df_copy['close'], window=period)
            
            # Stochastic con múltiples configuraciones
            stoch_configs = [(14, 3), (5, 3), (21, 5)]
            for k_period, d_period in stoch_configs:
                try:
                    stoch = ta.momentum.StochasticOscillator(
                        df_copy['high'], df_copy['low'], df_copy['close'],
                        window=k_period, smooth_window=d_period
                    )
                    df_copy[f'stoch_k_{k_period}_{d_period}'] = stoch.stoch()
                    df_copy[f'stoch_d_{k_period}_{d_period}'] = stoch.stoch_signal()
                except:
                    continue
            
            # Williams %R con múltiples períodos
            wr_periods = [14, 21, 28]
            for period in wr_periods:
                if len(df_copy) >= period:
                    df_copy[f'williams_r_{period}'] = ta.momentum.williams_r(
                        df_copy['high'], df_copy['low'], df_copy['close'], lbp=period
                    )
            
            # ROC (Rate of Change) con múltiples períodos
            roc_periods = [5, 10, 15, 20]
            for period in roc_periods:
                if len(df_copy) >= period:
                    df_copy[f'roc_{period}'] = ta.momentum.roc(df_copy['close'], window=period)
            
            # TSI (True Strength Index)
            try:
                df_copy['tsi'] = ta.momentum.tsi(df_copy['close'])
            except:
                pass
            
            # Awesome Oscillator
            try:
                df_copy['awesome_oscillator'] = ta.momentum.awesome_oscillator(df_copy['high'], df_copy['low'])
            except:
                pass
            
            # KST (Know Sure Thing)
            try:
                df_copy['kst'] = ta.momentum.kst(df_copy['close'])
                df_copy['kst_signal'] = ta.momentum.kst_sig(df_copy['close'])
            except:
                pass
            
            # Ultimate Oscillator
            try:
                df_copy['ultimate_oscillator'] = ta.momentum.ultimate_oscillator(
                    df_copy['high'], df_copy['low'], df_copy['close']
                )
            except:
                pass
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de momentum: {e}")
            return df_copy
    
    @staticmethod
    def add_all_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores de volatilidad disponibles"""
        df_copy = df.copy()
        
        try:
            # ATR con múltiples períodos
            atr_periods = [7, 14, 21, 28]
            for period in atr_periods:
                if len(df_copy) >= period:
                    df_copy[f'atr_{period}'] = ta.volatility.average_true_range(
                        df_copy['high'], df_copy['low'], df_copy['close'], window=period
                    )
            
            # Bollinger Bands con múltiples configuraciones
            bb_configs = [(20, 2), (20, 2.5), (10, 1.5), (50, 2)]
            for window, std_dev in bb_configs:
                if len(df_copy) >= window:
                    try:
                        bollinger = ta.volatility.BollingerBands(
                            df_copy['close'], window=window, window_dev=std_dev
                        )
                        suffix = f"_{window}_{int(std_dev*10)}"
                        df_copy[f'bb_upper{suffix}'] = bollinger.bollinger_hband()
                        df_copy[f'bb_lower{suffix}'] = bollinger.bollinger_lband()
                        df_copy[f'bb_middle{suffix}'] = bollinger.bollinger_mavg()
                        df_copy[f'bb_width{suffix}'] = bollinger.bollinger_wband()
                        df_copy[f'bb_percent{suffix}'] = bollinger.bollinger_pband()
                    except:
                        continue
            
            # Keltner Channels
            try:
                keltner = ta.volatility.KeltnerChannel(df_copy['high'], df_copy['low'], df_copy['close'])
                df_copy['keltner_upper'] = keltner.keltner_channel_hband()
                df_copy['keltner_lower'] = keltner.keltner_channel_lband()
                df_copy['keltner_middle'] = keltner.keltner_channel_mband()
            except:
                pass
            
            # Donchian Channels con múltiples períodos
            donchian_periods = [10, 20, 50]
            for period in donchian_periods:
                if len(df_copy) >= period:
                    try:
                        donchian = ta.volatility.DonchianChannel(
                            df_copy['high'], df_copy['low'], df_copy['close'], window=period
                        )
                        df_copy[f'donchian_upper_{period}'] = donchian.donchian_channel_hband()
                        df_copy[f'donchian_lower_{period}'] = donchian.donchian_channel_lband()
                        df_copy[f'donchian_middle_{period}'] = donchian.donchian_channel_mband()
                    except:
                        continue
            
            # Ulcer Index
            try:
                df_copy['ulcer_index'] = ta.volatility.ulcer_index(df_copy['close'])
            except:
                pass
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volatilidad: {e}")
            return df_copy
    
    @staticmethod
    def add_all_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores de volumen disponibles"""
        df_copy = df.copy()
        
        try:
            # OBV (On Balance Volume)
            df_copy['obv'] = ta.volume.on_balance_volume(df_copy['close'], df_copy['volume'])
            
            # VWAP con múltiples períodos
            vwap_periods = [14, 30, 50]
            for period in vwap_periods:
                if len(df_copy) >= period:
                    try:
                        df_copy[f'vwap_{period}'] = ta.volume.volume_weighted_average_price(
                            df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume'], window=period
                        )
                    except:
                        continue
            
            # Volume SMA/EMA
            vol_periods = [5, 10, 20, 50]
            for period in vol_periods:
                if len(df_copy) >= period:
                    df_copy[f'volume_sma_{period}'] = ta.trend.sma_indicator(df_copy['volume'], window=period)
                    df_copy[f'volume_ema_{period}'] = ta.trend.ema_indicator(df_copy['volume'], window=period)
            
            # Volume RSI
            try:
                df_copy['volume_rsi'] = ta.momentum.rsi(df_copy['volume'], window=14)
            except:
                pass
            
            # Accumulation/Distribution Line
            try:
                df_copy['ad_line'] = ta.volume.acc_dist_index(
                    df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume']
                )
            except:
                pass
            
            # Chaikin Money Flow con múltiples períodos
            cmf_periods = [14, 21, 30]
            for period in cmf_periods:
                if len(df_copy) >= period:
                    try:
                        df_copy[f'cmf_{period}'] = ta.volume.chaikin_money_flow(
                            df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume'], window=period
                        )
                    except:
                        continue
            
            # Force Index
            try:
                df_copy['force_index'] = ta.volume.force_index(df_copy['close'], df_copy['volume'])
            except:
                pass
            
            # Money Flow Index
            try:
                df_copy['mfi'] = ta.volume.money_flow_index(
                    df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume']
                )
            except:
                pass
            
            # Ease of Movement
            try:
                df_copy['ease_of_movement'] = ta.volume.ease_of_movement(
                    df_copy['high'], df_copy['low'], df_copy['volume']
                )
            except:
                pass
            
            # Volume Price Trend
            try:
                df_copy['vpt'] = ta.volume.volume_price_trend(df_copy['close'], df_copy['volume'])
            except:
                pass
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volumen: {e}")
            return df_copy

class PriceActionFeaturesAdvanced:
    """Clase para features avanzados de price action"""
    
    @staticmethod
    def add_comprehensive_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Añade features comprehensivos de precio"""
        df_copy = df.copy()
        
        try:
            # Returns con múltiples períodos
            return_periods = [1, 2, 3, 5, 8, 13, 21, 34]
            for period in return_periods:
                df_copy[f'return_{period}'] = df_copy['close'].pct_change(period)
                df_copy[f'log_return_{period}'] = np.log(df_copy['close'] / df_copy['close'].shift(period))
            
            # Ratios de precio
            df_copy['hl_ratio'] = df_copy['high'] / df_copy['low']
            df_copy['oc_ratio'] = df_copy['open'] / df_copy['close']
            df_copy['ho_ratio'] = df_copy['high'] / df_copy['open']
            df_copy['lo_ratio'] = df_copy['low'] / df_copy['open']
            df_copy['hc_ratio'] = df_copy['high'] / df_copy['close']
            df_copy['lc_ratio'] = df_copy['low'] / df_copy['close']
            
            # Características de las velas
            df_copy['body_size'] = abs(df_copy['close'] - df_copy['open']) / df_copy['open']
            df_copy['upper_shadow'] = (df_copy['high'] - np.maximum(df_copy['open'], df_copy['close'])) / df_copy['open']
            df_copy['lower_shadow'] = (np.minimum(df_copy['open'], df_copy['close']) - df_copy['low']) / df_copy['open']
            df_copy['total_shadow'] = df_copy['upper_shadow'] + df_copy['lower_shadow']
            df_copy['shadow_ratio'] = df_copy['upper_shadow'] / (df_copy['lower_shadow'] + 1e-8)
            
            # Posición del precio en el rango
            df_copy['price_position'] = (df_copy['close'] - df_copy['low']) / (df_copy['high'] - df_copy['low'] + 1e-8)
            df_copy['open_position'] = (df_copy['open'] - df_copy['low']) / (df_copy['high'] - df_copy['low'] + 1e-8)
            
            # Volatilidad rolling con múltiples ventanas
            vol_windows = [5, 10, 15, 20, 30]
            for window in vol_windows:
                if len(df_copy) >= window:
                    df_copy[f'volatility_{window}'] = df_copy['return_1'].rolling(window).std()
                    df_copy[f'realized_vol_{window}'] = np.sqrt(252) * df_copy[f'volatility_{window}']  # Anualizada
            
            # Aceleración y momentum del precio
            df_copy['price_acceleration'] = df_copy['return_1'].diff()
            df_copy['price_velocity'] = df_copy['return_1'].rolling(3).mean()
            df_copy['momentum_1'] = df_copy['close'] / df_copy['close'].shift(1) - 1
            df_copy['momentum_5'] = df_copy['close'] / df_copy['close'].shift(5) - 1
            
            # Features de gap
            df_copy['gap'] = df_copy['open'] - df_copy['close'].shift(1)
            df_copy['gap_pct'] = df_copy['gap'] / df_copy['close'].shift(1)
            df_copy['has_gap'] = (abs(df_copy['gap_pct']) > 0.001).astype(int)
            
            # True Range y variaciones
            df_copy['true_range'] = np.maximum(
                df_copy['high'] - df_copy['low'],
                np.maximum(
                    abs(df_copy['high'] - df_copy['close'].shift(1)),
                    abs(df_copy['low'] - df_copy['close'].shift(1))
                )
            )
            df_copy['tr_pct'] = df_copy['true_range'] / df_copy['close']
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando features de precio avanzados: {e}")
            return df_copy
    
    @staticmethod
    def add_pattern_recognition_features(df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de reconocimiento de patrones"""
        df_copy = df.copy()
        
        try:
            # Patrones de velas japonesas
            df_copy['doji'] = (abs(df_copy['open'] - df_copy['close']) / (df_copy['high'] - df_copy['low'] + 1e-8) < 0.1).astype(int)
            df_copy['hammer'] = ((df_copy['lower_shadow'] > 2 * df_copy['body_size']) & 
                                (df_copy['upper_shadow'] < df_copy['body_size'])).astype(int)
            df_copy['shooting_star'] = ((df_copy['upper_shadow'] > 2 * df_copy['body_size']) & 
                                       (df_copy['lower_shadow'] < df_copy['body_size'])).astype(int)
            
            # Patrones de múltiples velas
            df_copy['engulfing_bullish'] = ((df_copy['close'] > df_copy['open']) & 
                                           (df_copy['close'].shift(1) < df_copy['open'].shift(1)) &
                                           (df_copy['open'] < df_copy['close'].shift(1)) & 
                                           (df_copy['close'] > df_copy['open'].shift(1))).astype(int)
            
            df_copy['engulfing_bearish'] = ((df_copy['close'] < df_copy['open']) & 
                                           (df_copy['close'].shift(1) > df_copy['open'].shift(1)) &
                                           (df_copy['open'] > df_copy['close'].shift(1)) & 
                                           (df_copy['close'] < df_copy['open'].shift(1))).astype(int)
            
            # Inside/Outside bars
            df_copy['inside_bar'] = ((df_copy['high'] < df_copy['high'].shift(1)) & 
                                    (df_copy['low'] > df_copy['low'].shift(1))).astype(int)
            
            df_copy['outside_bar'] = ((df_copy['high'] > df_copy['high'].shift(1)) & 
                                     (df_copy['low'] < df_copy['low'].shift(1))).astype(int)
            
            # Consecutive patterns
            df_copy['consecutive_up'] = (df_copy['close'] > df_copy['open']).astype(int).rolling(3).sum()
            df_copy['consecutive_down'] = (df_copy['close'] < df_copy['open']).astype(int).rolling(3).sum()
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando patrones: {e}")
            return df_copy
    
    @staticmethod
    def add_support_resistance_advanced(df: pd.DataFrame) -> pd.DataFrame:
        """Añade niveles avanzados de soporte y resistencia"""
        df_copy = df.copy()
        
        try:
            # Soporte y resistencia con múltiples ventanas
            sr_windows = [10, 20, 50, 100]
            for window in sr_windows:
                if len(df_copy) >= window:
                    df_copy[f'resistance_{window}'] = df_copy['high'].rolling(window).max()
                    df_copy[f'support_{window}'] = df_copy['low'].rolling(window).min()
                    df_copy[f'sr_range_{window}'] = df_copy[f'resistance_{window}'] - df_copy[f'support_{window}']
                    df_copy[f'sr_position_{window}'] = (df_copy['close'] - df_copy[f'support_{window}']) / (df_copy[f'sr_range_{window}'] + 1e-8)
                    
                    # Distancia a niveles clave
                    df_copy[f'dist_to_resistance_{window}'] = (df_copy[f'resistance_{window}'] - df_copy['close']) / df_copy['close']
                    df_copy[f'dist_to_support_{window}'] = (df_copy['close'] - df_copy[f'support_{window}']) / df_copy['close']
            
            # Pivots Points (Fibonacci, Camarilla, etc.)
            df_copy['pivot_point'] = (df_copy['high'] + df_copy['low'] + df_copy['close']) / 3
            df_copy['pivot_r1'] = 2 * df_copy['pivot_point'] - df_copy['low']
            df_copy['pivot_s1'] = 2 * df_copy['pivot_point'] - df_copy['high']
            df_copy['pivot_r2'] = df_copy['pivot_point'] + (df_copy['high'] - df_copy['low'])
            df_copy['pivot_s2'] = df_copy['pivot_point'] - (df_copy['high'] - df_copy['low'])
            
            # Fibonacci retracements (usando highs/lows recientes)
            for window in [20, 50]:
                if len(df_copy) >= window:
                    high_window = df_copy['high'].rolling(window).max()
                    low_window = df_copy['low'].rolling(window).min()
                    range_window = high_window - low_window
                    
                    # Niveles de Fibonacci
                    fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
                    for level in fib_levels:
                        level_str = str(level).replace('.', '')
                        df_copy[f'fib_{level_str}_{window}'] = high_window - (range_window * level)
                        df_copy[f'dist_fib_{level_str}_{window}'] = abs(df_copy['close'] - df_copy[f'fib_{level_str}_{window}']) / df_copy['close']
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando soporte/resistencia avanzados: {e}")
            return df_copy

class MarketRegimeFeatures:
    """Features avanzados de régimen de mercado"""
    
    @staticmethod
    def add_market_regime_classification(df: pd.DataFrame) -> pd.DataFrame:
        """Clasifica el régimen de mercado usando múltiples métodos"""
        df_copy = df.copy()
        
        try:
            # Régimen de volatilidad (basado en percentiles históricos)
            vol_20 = df_copy['return_1'].rolling(20).std()
            vol_quantiles = vol_20.quantile([0.33, 0.67])
            
            df_copy['volatility_regime'] = pd.cut(
                vol_20,
                bins=[-np.inf, vol_quantiles.iloc[0], vol_quantiles.iloc[1], np.inf],
                labels=['low_vol', 'medium_vol', 'high_vol']
            )
            
            # Régimen de tendencia (basado en múltiples MAs)
            sma_20 = df_copy.get('sma_20', df_copy['close'].rolling(20).mean())
            sma_50 = df_copy.get('sma_50', df_copy['close'].rolling(50).mean())
            sma_200 = df_copy.get('sma_200', df_copy['close'].rolling(200).mean())
            
            trend_conditions = [
                (df_copy['close'] > sma_20) & (sma_20 > sma_50) & (sma_50 > sma_200),  # Strong uptrend
                (df_copy['close'] > sma_20) & (sma_20 > sma_50),  # Uptrend
                (df_copy['close'] < sma_20) & (sma_20 < sma_50) & (sma_50 < sma_200),  # Strong downtrend
                (df_copy['close'] < sma_20) & (sma_20 < sma_50),  # Downtrend
            ]
            trend_labels = ['strong_uptrend', 'uptrend', 'strong_downtrend', 'downtrend']
            
            df_copy['trend_regime'] = 'sideways'  # Default
            for condition, label in zip(trend_conditions, trend_labels):
                df_copy.loc[condition, 'trend_regime'] = label
            
            # Régimen de fuerza del mercado (basado en ADX)
            adx_14 = df_copy.get('adx_14', 50)  # Default si no existe
            df_copy['market_strength'] = pd.cut(
                adx_14,
                bins=[0, 25, 50, 100],
                labels=['weak', 'moderate', 'strong']
            )
            
            # Régimen de liquidez (basado en volumen)
            vol_sma_20 = df_copy['volume'].rolling(20).mean()
            vol_ratio = df_copy['volume'] / vol_sma_20
            vol_quantiles = vol_ratio.quantile([0.33, 0.67])
            
            df_copy['liquidity_regime'] = pd.cut(
                vol_ratio,
                bins=[0, vol_quantiles.iloc[0], vol_quantiles.iloc[1], np.inf],
                labels=['low_liquidity', 'normal_liquidity', 'high_liquidity']
            )
            
            # One-hot encode todas las variables categóricas
            categorical_features = ['volatility_regime', 'trend_regime', 'market_strength', 'liquidity_regime']
            for feature in categorical_features:
                if feature in df_copy.columns:
                    dummies = pd.get_dummies(df_copy[feature], prefix=feature.split('_')[0])
                    df_copy = pd.concat([df_copy, dummies], axis=1)
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error clasificando régimen de mercado: {e}")
            return df_copy
    
    @staticmethod
    def add_market_microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de microestructura de mercado"""
        df_copy = df.copy()
        
        try:
            # Imbalance features
            df_copy['price_imbalance'] = (df_copy['close'] - df_copy['open']) / (df_copy['high'] - df_copy['low'] + 1e-8)
            df_copy['volume_imbalance'] = df_copy['volume'] / df_copy['volume'].rolling(20).mean()
            
            # Tick-level features (simulados)
            df_copy['tick_direction'] = np.sign(df_copy['close'] - df_copy['close'].shift(1))
            df_copy['tick_intensity'] = abs(df_copy['close'] - df_copy['close'].shift(1)) / df_copy['close'].shift(1)
            
            # VPIN (Volume-Synchronized Probability of Informed Trading) - simplificado
            df_copy['buy_volume'] = np.where(df_copy['close'] > df_copy['open'], df_copy['volume'], 0)
            df_copy['sell_volume'] = np.where(df_copy['close'] < df_copy['open'], df_copy['volume'], 0)
            
            window = 20
            df_copy['vpin'] = abs(
                df_copy['buy_volume'].rolling(window).sum() - df_copy['sell_volume'].rolling(window).sum()
            ) / df_copy['volume'].rolling(window).sum()
            
            # Order flow features
            df_copy['aggressive_buying'] = ((df_copy['close'] > df_copy['open']) & 
                                           (df_copy['volume'] > df_copy['volume'].rolling(5).mean())).astype(int)
            df_copy['aggressive_selling'] = ((df_copy['close'] < df_copy['open']) & 
                                            (df_copy['volume'] > df_copy['volume'].rolling(5).mean())).astype(int)
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando microestructura: {e}")
            return df_copy

class TimeBasedFeatures:
    """Features basados en tiempo optimizados"""
    
    @staticmethod
    def add_comprehensive_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """Añade features temporales comprehensivos"""
        df_copy = df.copy()
        
        try:
            if not isinstance(df_copy.index, pd.DatetimeIndex):
                logger.warning("Índice no es DatetimeIndex, saltando features temporales")
                return df_copy
            
            # Features básicos de tiempo
            df_copy['hour'] = df_copy.index.hour
            df_copy['day_of_week'] = df_copy.index.dayofweek
            df_copy['day_of_month'] = df_copy.index.day
            df_copy['month'] = df_copy.index.month
            df_copy['quarter'] = df_copy.index.quarter
            df_copy['year'] = df_copy.index.year
            df_copy['week_of_year'] = df_copy.index.isocalendar().week
            
            # Features cíclicos (codificación circular)
            cyclical_features = [
                ('hour', 24), ('day_of_week', 7), ('day_of_month', 31),
                ('month', 12), ('week_of_year', 52)
            ]
            
            for feature, max_val in cyclical_features:
                if feature in df_copy.columns:
                    df_copy[f'{feature}_sin'] = np.sin(2 * np.pi * df_copy[feature] / max_val)
                    df_copy[f'{feature}_cos'] = np.cos(2 * np.pi * df_copy[feature] / max_val)
            
            # Features de sesiones de trading
            df_copy['is_weekend'] = (df_copy['day_of_week'] >= 5).astype(int)
            df_copy['is_month_end'] = (df_copy['day_of_month'] >= 28).astype(int)
            df_copy['is_quarter_end'] = ((df_copy['month'] % 3 == 0) & (df_copy['day_of_month'] >= 28)).astype(int)
            df_copy['is_year_end'] = ((df_copy['month'] == 12) & (df_copy['day_of_month'] >= 28)).astype(int)
            
            # Sesiones de trading globales (UTC)
            # Estas sesiones pueden ajustarse según el mercado específico
            conditions = [
                ((df_copy['hour'] >= 22) | (df_copy['hour'] <= 8)),  # Asian session
                ((df_copy['hour'] >= 7) & (df_copy['hour'] <= 16)),   # European session
                ((df_copy['hour'] >= 13) & (df_copy['hour'] <= 22)),  # US session
            ]
            sessions = ['asian_session', 'european_session', 'us_session']
            
            for condition, session in zip(conditions, sessions):
                df_copy[session] = condition.astype(int)
            
            # Overlap sessions
            df_copy['asia_europe_overlap'] = ((df_copy['hour'] >= 7) & (df_copy['hour'] <= 8)).astype(int)
            df_copy['europe_us_overlap'] = ((df_copy['hour'] >= 13) & (df_copy['hour'] <= 16)).astype(int)
            
            # Features de estacionalidad avanzada
            df_copy['is_january_effect'] = (df_copy['month'] == 1).astype(int)
            df_copy['is_summer_lull'] = ((df_copy['month'] >= 6) & (df_copy['month'] <= 8)).astype(int)
            df_copy['is_year_end_rally'] = ((df_copy['month'] == 12) & (df_copy['day_of_month'] >= 15)).astype(int)
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando features temporales: {e}")
            return df_copy

class DataPreprocessorAdvanced:
    """Procesador avanzado de datos con optimizaciones profesionales"""
    
    def __init__(self):
        # Configuración de escaladores
        self.scaler_type = "robust"  # robust, standard, minmax, quantile
        self.scalers = {}
        self.feature_columns = []
        self.feature_selector = None
        
        # Cache de features
        self.feature_cache = FeatureCache()
        
        # Configuración desde usuario
        config_loader = ConfigLoader()
        self.ai_settings = config_loader.get_value(['ai_model_settings'], {})
        self.lookback_window = config_loader.get_value(['ai_model_settings', 'lookback_window'], 60)
        
        # Configuración de paralelización
        self.n_jobs = min(4, mp.cpu_count())
        
        # Validación de features
        self.feature_validator = FeatureValidator()
        
        logger.info(f"DataPreprocessorAdvanced inicializado con {self.n_jobs} workers")
    
    def get_raw_data_optimized(
        self, 
        symbol: str = "BTCUSDT", 
        days_back: int = 100,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        """Obtiene datos crudos con optimizaciones"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Usar método optimizado de la base de datos
            df = db_manager.get_market_data_optimized(
                symbol, start_date, end_date,
                columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            if df.empty:
                logger.warning(f"No se encontraron datos para {symbol}")
                return pd.DataFrame()
            
            # Validación y limpieza inicial
            df = self._initial_data_cleaning(df)
            
            logger.info(f"Datos crudos obtenidos: {len(df)} registros para {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos crudos optimizados: {e}")
            return pd.DataFrame()
    
    def get_aligned_data_optimized(
        self, 
        symbol: str = "BTCUSDT", 
        days_back: int = 100,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        """Obtiene datos alineados para entrenamiento multi-símbolo"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Verificar si existen datos alineados
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM aligned_market_data 
                    WHERE symbol = ? AND timeframe = ?
                """, (symbol, timeframe))
                
                aligned_count = cursor.fetchone()[0]
                
                if aligned_count > 0:
                    logger.info(f"Usando datos alineados para {symbol}-{timeframe}: {aligned_count:,} registros")
                    
                    # Obtener datos alineados
                    cursor.execute("""
                        SELECT timestamp, open, high, low, close, volume
                        FROM aligned_market_data 
                        WHERE symbol = ? AND timeframe = ?
                        AND timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp
                    """, (symbol, timeframe, int(start_date.timestamp()), int(end_date.timestamp())))
                    
                    results = cursor.fetchall()
                    
                    if results:
                        # Crear DataFrame
                        df = pd.DataFrame(results, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                        df.set_index('datetime', inplace=True)
                        df.drop('timestamp', axis=1, inplace=True)
                        
                        # Validación y limpieza inicial
                        df = self._initial_data_cleaning(df)
                        
                        logger.info(f"Datos alineados obtenidos para {symbol}: {len(df)} registros")
                        return df
                    else:
                        logger.warning(f"No hay datos alineados en el rango para {symbol}")
                        return self.get_raw_data_optimized(symbol, days_back, timeframe)
                else:
                    logger.info(f"No hay datos alineados para {symbol}-{timeframe}, usando datos normales")
                    return self.get_raw_data_optimized(symbol, days_back, timeframe)
                    
        except Exception as e:
            logger.error(f"Error obteniendo datos alineados para {symbol}: {e}")
            # Fallback a datos normales
            return self.get_raw_data_optimized(symbol, days_back, timeframe)
    
    def _initial_data_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza inicial de datos"""
        try:
            # Remover registros con datos faltantes críticos
            df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            
            # Remover registros con precios <= 0
            df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]
            
            # Remover registros con volumen negativo
            df = df[df['volume'] >= 0]
            
            # Validar relaciones OHLC
            valid_ohlc = (
                (df['high'] >= df['low']) &
                (df['high'] >= df['open']) &
                (df['high'] >= df['close']) &
                (df['low'] <= df['open']) &
                (df['low'] <= df['close'])
            )
            df = df[valid_ohlc]
            
            # Remover outliers extremos (>10 desviaciones estándar)
            for col in ['open', 'high', 'low', 'close']:
                mean_val = df[col].mean()
                std_val = df[col].std()
                df = df[abs(df[col] - mean_val) <= 10 * std_val]
            
            logger.debug(f"Limpieza inicial completada: {len(df)} registros válidos")
            return df
            
        except Exception as e:
            logger.error(f"Error en limpieza inicial: {e}")
            return df
    
    def add_all_technical_indicators_parallel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores técnicos usando paralelización"""
        try:
            if df.empty:
                return df
            
            logger.info("Calculando indicadores técnicos en paralelo...")
            start_time = time.time()
            
            # Verificar cache
            cache_key = self.feature_cache._get_cache_key(
                df.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df.columns else 'UNKNOWN',
                df.index.min(),
                df.index.max(),
                {'indicators': 'all'}
            )
            
            cached_df = self.feature_cache.get(cache_key)
            if cached_df is not None:
                logger.info("Features técnicos obtenidos del cache")
                return cached_df
            
            # Lista de funciones a ejecutar en paralelo
            indicator_functions = [
                TechnicalIndicatorsAdvanced.add_all_trend_indicators,
                TechnicalIndicatorsAdvanced.add_all_momentum_indicators,
                TechnicalIndicatorsAdvanced.add_all_volatility_indicators,
                TechnicalIndicatorsAdvanced.add_all_volume_indicators,
                PriceActionFeaturesAdvanced.add_comprehensive_price_features,
                PriceActionFeaturesAdvanced.add_pattern_recognition_features,
                PriceActionFeaturesAdvanced.add_support_resistance_advanced,
                MarketRegimeFeatures.add_market_regime_classification,
                MarketRegimeFeatures.add_market_microstructure_features,
                TimeBasedFeatures.add_comprehensive_time_features
            ]
            
            # Ejecutar funciones en paralelo
            with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
                # Preparar trabajos
                futures = [executor.submit(func, df.copy()) for func in indicator_functions]
                
                # Recoger resultados
                results = []
                for i, future in enumerate(futures):
                    try:
                        result_df = future.result(timeout=60)  # 60 segundos timeout
                        results.append(result_df)
                        logger.debug(f"Indicador {i+1}/{len(indicator_functions)} completado")
                    except Exception as e:
                        logger.error(f"Error en indicador {i+1}: {e}")
                        results.append(df.copy())  # Fallback al DataFrame original
            
            # Combinar todos los resultados
            combined_df = df.copy()
            for result_df in results:
                # Solo agregar columnas nuevas
                new_columns = [col for col in result_df.columns if col not in combined_df.columns]
                if new_columns:
                    for col in new_columns:
                        combined_df[col] = result_df[col]
            
            # Guardar en cache
            self.feature_cache.set(cache_key, combined_df)
            
            calculation_time = time.time() - start_time
            logger.info(f"Indicadores técnicos calculados en {calculation_time:.2f}s. "
                       f"Features totales: {len(combined_df.columns)}")
            
            return combined_df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores técnicos en paralelo: {e}")
            return df
    
    def create_target_variable_advanced(self, df: pd.DataFrame, 
                                      method: str = "classification",
                                      prediction_horizon: int = 1) -> pd.DataFrame:
        """Crea variable objetivo avanzada con múltiples horizontes"""
        try:
            if df.empty:
                return df
            
            if method == "classification":
                # Clasificación multi-horizonte
                future_returns = {}
                for horizon in [1, 3, 5, prediction_horizon]:
                    future_returns[f'future_return_{horizon}'] = (
                        df['close'].shift(-horizon) / df['close'] - 1
                    )
                
                # Usar volatilidad adaptativa para umbrales
                volatility_window = min(50, len(df) // 4)
                rolling_vol = df['close'].pct_change().rolling(volatility_window).std()
                
                # Umbrales dinámicos basados en volatilidad
                upper_threshold = rolling_vol * 0.75  # 0.75x volatilidad para BUY
                lower_threshold = -rolling_vol * 0.75  # -0.75x volatilidad para SELL
                
                main_return = future_returns[f'future_return_{prediction_horizon}']
                
                # Clasificación mejorada con clase STRONG_BUY/STRONG_SELL
                conditions = [
                    main_return > upper_threshold * 2,    # STRONG_BUY (4)
                    main_return > upper_threshold,        # BUY (3)
                    main_return > lower_threshold,        # HOLD (2)
                    main_return > lower_threshold * 2,    # SELL (1)
                ]
                choices = [4, 3, 2, 1]
                
                df['target'] = np.select(conditions, choices, default=0)  # STRONG_SELL (0)
                
                # Añadir features adicionales para el target
                df['target_confidence'] = np.minimum(
                    abs(main_return) / (rolling_vol + 1e-8), 3.0
                )
                
            elif method == "regression":
                # Regresión con múltiples horizontes
                for horizon in [1, 3, 5]:
                    df[f'target_{horizon}'] = df['close'].shift(-horizon) / df['close'] - 1
                
                # Target principal
                df['target'] = df[f'target_{prediction_horizon}']
                
            elif method == "risk_adjusted":
                # Target ajustado por riesgo (Sharpe ratio local)
                returns = df['close'].pct_change()
                future_returns = returns.shift(-prediction_horizon)
                rolling_vol = returns.rolling(20).std()
                
                df['target'] = future_returns / (rolling_vol + 1e-8)
                
            # Remover filas sin target
            df = df[:-max(prediction_horizon, 5)]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creando variable objetivo avanzada: {e}")
            return df
    
    def feature_selection_advanced(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """Selección avanzada de features usando múltiples métodos"""
        try:
            logger.info("Ejecutando selección avanzada de features...")
            
            # 1. Remover features con baja varianza
            from sklearn.feature_selection import VarianceThreshold
            variance_selector = VarianceThreshold(threshold=0.001)
            X_variance = pd.DataFrame(
                variance_selector.fit_transform(X),
                columns=X.columns[variance_selector.get_support()],
                index=X.index
            )
            
            # 2. Remover features altamente correlacionadas
            correlation_matrix = X_variance.corr().abs()
            upper_triangle = correlation_matrix.where(
                np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
            )
            
            high_corr_features = [
                column for column in upper_triangle.columns 
                if any(upper_triangle[column] > 0.95)
            ]
            X_corr = X_variance.drop(columns=high_corr_features)
            
            # 3. Selección univariada (SelectKBest)
            n_features = min(100, len(X_corr.columns) // 2)  # Máximo 100 features
            
            selector = SelectKBest(score_func=mutual_info_classif, k=n_features)
            X_selected = pd.DataFrame(
                selector.fit_transform(X_corr, y),
                columns=X_corr.columns[selector.get_support()],
                index=X_corr.index
            )
            
            # Guardar el selector para uso futuro
            self.feature_selector = selector
            
            logger.info(f"Selección de features completada: {len(X.columns)} -> {len(X_selected.columns)}")
            return X_selected
            
        except Exception as e:
            logger.error(f"Error en selección de features: {e}")
            return X
    
    def prepare_training_data_advanced(
        self, 
        symbol: str = "BTCUSDT",
        days_back: int = 100,
        target_method: str = "classification",
        prediction_horizon: int = 1,
        use_feature_selection: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame, Dict[str, Any]]:
        """Pipeline completo optimizado para preparación de datos"""
        try:
            logger.info(f"Preparando datos de entrenamiento avanzados para {symbol}")
            start_time = time.time()
            
            # 1. Obtener datos alineados (si están disponibles) o datos normales
            df = self.get_aligned_data_optimized(symbol, days_back)
            if df.empty:
                return np.array([]), np.array([]), pd.DataFrame(), {}
            
            # 2. Añadir todos los indicadores técnicos (paralelizado)
            df = self.add_all_technical_indicators_parallel(df)
            
            # 3. Crear variable objetivo
            df = self.create_target_variable_advanced(df, target_method, prediction_horizon)
            
            # 4. Validación y limpieza final
            df = self.feature_validator.validate_and_clean(df)
            
            # 5. Escalado de features
            df = self.scale_features_advanced(df, fit_scaler=True)
            
            # 6. Separar features y target
            feature_columns = [col for col in df.columns if not col.startswith('target')]
            X = df[feature_columns]
            y = df['target']
            
            # 7. Selección de features (opcional)
            if use_feature_selection and len(X.columns) > 50:
                X = self.feature_selection_advanced(X, y)
            
            # 8. Crear secuencias para LSTM
            X_sequences, y_sequences = self.create_sequences_optimized(X, y)
            
            # 9. Estadísticas de preparación
            preparation_stats = {
                'preparation_time_seconds': time.time() - start_time,
                'original_features': len(feature_columns),
                'selected_features': len(X.columns),
                'total_samples': len(X_sequences),
                'target_distribution': dict(pd.Series(y_sequences).value_counts().sort_index()) if len(y_sequences) > 0 else {},
                'data_quality_score': self.feature_validator.calculate_quality_score(df)
            }
            
            self.feature_columns = list(X.columns)
            
            logger.info(f"Datos preparados exitosamente en {preparation_stats['preparation_time_seconds']:.2f}s")
            logger.info(f"Muestras: {len(X_sequences)}, Features: {len(X.columns)}")
            
            return X_sequences, y_sequences, df, preparation_stats
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento avanzados: {e}")
            return np.array([]), np.array([]), pd.DataFrame(), {'error': str(e)}
    
    def scale_features_advanced(self, df: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """Escalado avanzado de features con diferentes métodos"""
        try:
            if df.empty:
                return df
            
            # Identificar columnas a escalar
            exclude_patterns = ['target', '_regime', '_session', 'is_', 'has_', 'consecutive_']
            exclude_columns = [col for col in df.columns 
                             if any(pattern in col for pattern in exclude_patterns)]
            
            scale_columns = [col for col in df.columns 
                           if col not in exclude_columns and df[col].dtype in ['float64', 'int64']]
            
            if not scale_columns:
                return df
            
            # Configurar scaler según tipo
            scaler_config = {
                "robust": RobustScaler(),
                "standard": StandardScaler(),
                "minmax": MinMaxScaler(),
                "quantile": QuantileTransformer(output_distribution='uniform', n_quantiles=1000)
            }
            
            scaler = scaler_config.get(self.scaler_type, RobustScaler())
            
            if fit_scaler:
                self.scalers['features'] = scaler
                df[scale_columns] = scaler.fit_transform(df[scale_columns])
                logger.debug(f"Scaler {self.scaler_type} ajustado en {len(scale_columns)} columnas")
            else:
                if 'features' in self.scalers:
                    df[scale_columns] = self.scalers['features'].transform(df[scale_columns])
                else:
                    logger.warning("Scaler no encontrado, no se escalaron las features")
            
            return df
            
        except Exception as e:
            logger.error(f"Error escalando features avanzado: {e}")
            return df
    
    def create_sequences_optimized(self, X: pd.DataFrame, y: pd.Series = None, 
                                 lookback: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Crea secuencias optimizadas para LSTM"""
        try:
            if lookback is None:
                lookback = self.lookback_window
            
            if X.empty or len(X) < lookback + 1:
                logger.warning("Datos insuficientes para crear secuencias")
                return np.array([]), np.array([])
            
            # Convertir a numpy para mayor velocidad
            X_values = X.values.astype(np.float32)
            y_values = y.values if y is not None else None
            
            # Pre-allocar arrays para mejor performance
            n_samples = len(X_values) - lookback
            n_features = X_values.shape[1]
            
            X_sequences = np.empty((n_samples, lookback, n_features), dtype=np.float32)
            y_sequences = np.empty(n_samples, dtype=np.float32) if y_values is not None else np.array([])
            
            # Llenar secuencias usando vectorización
            for i in range(n_samples):
                X_sequences[i] = X_values[i:i + lookback]
                if y_values is not None:
                    y_sequences[i] = y_values[i + lookback]
            
            logger.debug(f"Secuencias creadas: X shape {X_sequences.shape}, y shape {y_sequences.shape}")
            return X_sequences, y_sequences
            
        except Exception as e:
            logger.error(f"Error creando secuencias optimizadas: {e}")
            return np.array([]), np.array([])
    
    def get_preprocessing_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas comprehensivas del preprocessing"""
        return {
            'configuration': {
                'scaler_type': self.scaler_type,
                'lookback_window': self.lookback_window,
                'n_jobs': self.n_jobs,
                'cache_enabled': True
            },
            'features': {
                'total_features': len(self.feature_columns),
                'feature_categories': self._categorize_features(),
                'selected_features': self.feature_columns[:20] if self.feature_columns else []
            },
            'scalers': {
                'fitted_scalers': list(self.scalers.keys()),
                'scaler_type': self.scaler_type
            },
            'performance': {
                'cache_stats': self._get_cache_stats(),
                'feature_importance_weights': self.get_feature_importance_weights()
            }
        }
    
    def _categorize_features(self) -> Dict[str, int]:
        """Categoriza features por tipo"""
        categories = {
            'trend': 0, 'momentum': 0, 'volatility': 0, 'volume': 0,
            'price_action': 0, 'patterns': 0, 'support_resistance': 0,
            'market_regime': 0, 'time_based': 0, 'microstructure': 0
        }
        
        category_keywords = {
            'trend': ['sma', 'ema', 'wma', 'macd', 'adx', 'aroon', 'ichimoku'],
            'momentum': ['rsi', 'stoch', 'williams', 'roc', 'tsi', 'awesome', 'kst'],
            'volatility': ['atr', 'bb_', 'bollinger', 'keltner', 'donchian', 'ulcer'],
            'volume': ['obv', 'vwap', 'volume_', 'ad_line', 'cmf', 'mfi', 'force'],
            'price_action': ['return_', 'ratio', 'body_size', 'shadow', 'position'],
            'patterns': ['doji', 'hammer', 'engulfing', 'inside_bar', 'consecutive'],
            'support_resistance': ['resistance', 'support', 'pivot', 'fib_'],
            'market_regime': ['regime', 'strength', 'imbalance', 'vpin'],
            'time_based': ['hour', 'day_', 'month', 'session', 'overlap'],
            'microstructure': ['tick_', 'buy_volume', 'sell_volume', 'aggressive']
        }
        
        for feature in self.feature_columns:
            feature_lower = feature.lower()
            for category, keywords in category_keywords.items():
                if any(keyword in feature_lower for keyword in keywords):
                    categories[category] += 1
                    break
        
        return categories
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        try:
            cache_files = list(self.feature_cache.cache_dir.glob("*.pkl"))
            total_size_mb = sum(f.stat().st_size for f in cache_files) / 1024 / 1024
            
            return {
                'cache_files': len(cache_files),
                'total_size_mb': round(total_size_mb, 2),
                'cache_directory': str(self.feature_cache.cache_dir)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_feature_importance_weights(self) -> Dict[str, float]:
        """Obtiene pesos de importancia de features configurados"""
        feature_importance = self.ai_settings.get('feature_importance', {})
        
        return {
            'price_action': feature_importance.get('price_action', 0.25),
            'technical_indicators': feature_importance.get('technical_indicators', 0.35),
            'volume_analysis': feature_importance.get('volume_analysis', 0.20),
            'market_sentiment': feature_importance.get('market_sentiment', 0.10),
            'time_features': feature_importance.get('time_features', 0.10)
        }

class FeatureValidator:
    """Validador de features con checks comprehensivos"""
    
    def __init__(self):
        self.validation_rules = {
            'max_na_ratio': 0.1,  # Máximo 10% NaN
            'min_variance': 1e-8,  # Varianza mínima
            'max_correlation': 0.98,  # Correlación máxima entre features
            'max_infinite_ratio': 0.01,  # Máximo 1% infinitos
            'min_samples': 100  # Mínimo número de muestras
        }
    
    def validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida y limpia el DataFrame completo"""
        try:
            logger.info("Ejecutando validación y limpieza de features...")
            
            original_shape = df.shape
            
            # 1. Validaciones básicas
            df = self._remove_invalid_features(df)
            
            # 2. Manejo de valores faltantes
            df = self._handle_missing_values(df)
            
            # 3. Manejo de infinitos y outliers
            df = self._handle_infinite_and_outliers(df)
            
            # 4. Verificar mínimo de muestras
            if len(df) < self.validation_rules['min_samples']:
                logger.warning(f"Insuficientes muestras después de limpieza: {len(df)}")
            
            final_shape = df.shape
            logger.info(f"Validación completada: {original_shape} -> {final_shape}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error en validación de features: {e}")
            return df
    
    def _remove_invalid_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remueve features inválidos"""
        try:
            # Identificar columnas numéricas
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            
            features_to_remove = []
            
            for col in numeric_columns:
                # Check NaN ratio
                na_ratio = df[col].isna().sum() / len(df)
                if na_ratio > self.validation_rules['max_na_ratio']:
                    features_to_remove.append(col)
                    continue
                
                # Check variance
                if df[col].var() < self.validation_rules['min_variance']:
                    features_to_remove.append(col)
                    continue
                
                # Check infinite ratio
                inf_ratio = np.isinf(df[col]).sum() / len(df)
                if inf_ratio > self.validation_rules['max_infinite_ratio']:
                    features_to_remove.append(col)
                    continue
            
            if features_to_remove:
                df = df.drop(columns=features_to_remove)
                logger.debug(f"Removidos {len(features_to_remove)} features inválidos")
            
            return df
            
        except Exception as e:
            logger.error(f"Error removiendo features inválidos: {e}")
            return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Maneja valores faltantes de manera inteligente"""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_columns:
                if df[col].isna().any():
                    # Forward fill para series temporales, luego backward fill
                    df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
                    
                    # Si aún hay NaN, usar mediana
                    if df[col].isna().any():
                        df[col] = df[col].fillna(df[col].median())
            
            return df
            
        except Exception as e:
            logger.error(f"Error manejando valores faltantes: {e}")
            return df
    
    def _handle_infinite_and_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Maneja infinitos y outliers"""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_columns:
                # Reemplazar infinitos
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                
                # Llenar infinitos convertidos a NaN
                if df[col].isna().any():
                    df[col] = df[col].fillna(df[col].median())
                
                # Clipear outliers extremos (percentiles 0.1 y 99.9)
                if col not in ['target'] and df[col].std() > 0:
                    lower_bound = df[col].quantile(0.001)
                    upper_bound = df[col].quantile(0.999)
                    df[col] = df[col].clip(lower_bound, upper_bound)
            
            return df
            
        except Exception as e:
            logger.error(f"Error manejando infinitos y outliers: {e}")
            return df
    
    def calculate_quality_score(self, df: pd.DataFrame) -> float:
        """Calcula una puntuación de calidad de los datos"""
        try:
            if df.empty:
                return 0.0
            
            scores = []
            
            # Score de completitud (sin NaN)
            completeness = 1 - df.isna().sum().sum() / (df.shape[0] * df.shape[1])
            scores.append(completeness)
            
            # Score de varianza (features con varianza suficiente)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                variance_score = (df[numeric_cols].var() > self.validation_rules['min_variance']).mean()
                scores.append(variance_score)
            
            # Score de finitud (sin infinitos)
            finite_score = 1 - np.isinf(df.select_dtypes(include=[np.number])).sum().sum() / (df.shape[0] * len(numeric_cols)) if len(numeric_cols) > 0 else 1.0
            scores.append(finite_score)
            
            # Score de tamaño de muestra
            sample_score = min(1.0, len(df) / self.validation_rules['min_samples'])
            scores.append(sample_score)
            
            overall_score = np.mean(scores)
            return round(overall_score, 3)
            
        except Exception as e:
            logger.error(f"Error calculando quality score: {e}")
            return 0.0

# Instancia global del preprocessor
data_preprocessor = DataPreprocessorAdvanced()

# Funciones de utilidad para compatibilidad con código existente
def prepare_training_data(symbol: str = "BTCUSDT", days_back: int = 100, 
                         target_method: str = "classification") -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Función wrapper para compatibilidad"""
    X, y, df, stats = data_preprocessor.prepare_training_data_advanced(
        symbol, days_back, target_method
    )
    return X, y, df

def prepare_multi_symbol_training_data(
    symbols: List[str] = None,
    days_back: int = 100,
    target_method: str = "classification",
    timeframe: str = "1h"
) -> Dict[str, Tuple[np.ndarray, np.ndarray, pd.DataFrame]]:
    """
    Prepara datos de entrenamiento para múltiples símbolos usando datos alineados
    
    Args:
        symbols: Lista de símbolos para entrenar
        days_back: Días de datos históricos
        target_method: Método de creación de target
        timeframe: Timeframe de los datos
        
    Returns:
        Dict con datos de entrenamiento por símbolo
    """
    if symbols is None:
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    logger.info(f"Preparando datos multi-símbolo para {len(symbols)} símbolos")
    
    multi_symbol_data = {}
    
    for symbol in symbols:
        try:
            logger.info(f"Procesando {symbol}...")
            
            # Usar datos alineados
            X, y, df, stats = data_preprocessor.prepare_training_data_advanced(
                symbol, days_back, target_method
            )
            
            if X.shape[0] > 0:
                multi_symbol_data[symbol] = (X, y, df)
                logger.info(f"✅ {symbol}: {X.shape[0]} muestras, {X.shape[1]} features")
            else:
                logger.warning(f"⚠️ {symbol}: Sin datos suficientes")
                multi_symbol_data[symbol] = (np.array([]), np.array([]), pd.DataFrame())
                
        except Exception as e:
            logger.error(f"❌ Error procesando {symbol}: {e}")
            multi_symbol_data[symbol] = (np.array([]), np.array([]), pd.DataFrame())
    
    # Estadísticas del procesamiento multi-símbolo
    successful_symbols = [s for s, (X, y, df) in multi_symbol_data.items() if X.shape[0] > 0]
    logger.info(f"Procesamiento multi-símbolo completado: {len(successful_symbols)}/{len(symbols)} símbolos exitosos")
    
    return multi_symbol_data

def prepare_prediction_data(df: pd.DataFrame) -> np.ndarray:
    """Prepara datos para predicción usando el preprocessor avanzado"""
    try:
        if df.empty:
            return np.array([])
        
        # Aplicar pipeline de features
        df_processed = data_preprocessor.add_all_technical_indicators_parallel(df)
        df_processed = data_preprocessor.feature_validator.validate_and_clean(df_processed)
        df_processed = data_preprocessor.scale_features_advanced(df_processed, fit_scaler=False)
        
        # Usar solo las columnas de features conocidas
        if data_preprocessor.feature_columns:
            available_features = [col for col in data_preprocessor.feature_columns if col in df_processed.columns]
            if available_features:
                feature_data = df_processed[available_features].tail(data_preprocessor.lookback_window).values
                if len(feature_data) == data_preprocessor.lookback_window:
                    return feature_data.reshape(1, data_preprocessor.lookback_window, len(available_features))
        
        return np.array([])
        
    except Exception as e:
        logger.error(f"Error preparando datos para predicción: {e}")
        return np.array([])

# Funciones para análisis y diagnóstico
def analyze_feature_correlation(df: pd.DataFrame, threshold: float = 0.95) -> Dict[str, List[str]]:
    """Analiza correlaciones altas entre features"""
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        correlation_matrix = numeric_df.corr().abs()
        
        # Encontrar pares con alta correlación
        high_corr_pairs = {}
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                if correlation_matrix.iloc[i, j] > threshold:
                    col1, col2 = correlation_matrix.columns[i], correlation_matrix.columns[j]
                    if col1 not in high_corr_pairs:
                        high_corr_pairs[col1] = []
                    high_corr_pairs[col1].append(f"{col2} ({correlation_matrix.iloc[i, j]:.3f})")
        
        return high_corr_pairs
        
    except Exception as e:
        logger.error(f"Error analizando correlaciones: {e}")
        return {}

def get_feature_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Obtiene estadísticas detalladas de features"""
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        
        stats = {
            'total_features': len(df.columns),
            'numeric_features': len(numeric_df.columns),
            'categorical_features': len(df.columns) - len(numeric_df.columns),
            'missing_values': df.isna().sum().sum(),
            'infinite_values': np.isinf(numeric_df).sum().sum(),
            'zero_variance_features': (numeric_df.var() == 0).sum(),
            'feature_ranges': {},
            'feature_distributions': {}
        }
        
        # Estadísticas por feature (solo primeros 20 para no saturar)
        for col in numeric_df.columns[:20]:
            stats['feature_ranges'][col] = {
                'min': float(numeric_df[col].min()),
                'max': float(numeric_df[col].max()),
                'mean': float(numeric_df[col].mean()),
                'std': float(numeric_df[col].std())
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de features: {e}")
        return {'error': str(e)}