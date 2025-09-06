"""
data/preprocessor.py
Procesador de datos y feature engineering para el modelo de ML
Ubicación: C:\TradingBot_v10\data\preprocessor.py

Funcionalidades:
- Feature engineering de indicadores técnicos
- Normalización y escalado de datos
- Preparación de datasets para ML
- Detección de patrones y anomalías
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.impute import SimpleImputer
import ta
from ta.utils import dropna
import warnings
warnings.filterwarnings('ignore')

from .database import db_manager
from config.config_loader import user_config

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Clase para calcular indicadores técnicos"""
    
    @staticmethod
    def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores técnicos básicos"""
        df_copy = df.copy()
        
        try:
            # Moving Averages
            df_copy['sma_5'] = ta.trend.sma_indicator(df_copy['close'], window=5)
            df_copy['sma_10'] = ta.trend.sma_indicator(df_copy['close'], window=10)
            df_copy['sma_20'] = ta.trend.sma_indicator(df_copy['close'], window=20)
            df_copy['sma_50'] = ta.trend.sma_indicator(df_copy['close'], window=50)
            
            # Exponential Moving Averages
            df_copy['ema_12'] = ta.trend.ema_indicator(df_copy['close'], window=12)
            df_copy['ema_26'] = ta.trend.ema_indicator(df_copy['close'], window=26)
            df_copy['ema_50'] = ta.trend.ema_indicator(df_copy['close'], window=50)
            
            # RSI
            df_copy['rsi_14'] = ta.momentum.rsi(df_copy['close'], window=14)
            df_copy['rsi_21'] = ta.momentum.rsi(df_copy['close'], window=21)
            
            # MACD
            macd = ta.trend.MACD(df_copy['close'])
            df_copy['macd'] = macd.macd()
            df_copy['macd_signal'] = macd.macd_signal()
            df_copy['macd_histogram'] = macd.macd_diff()
            
            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df_copy['close'], window=20)
            df_copy['bollinger_upper'] = bollinger.bollinger_hband()
            df_copy['bollinger_lower'] = bollinger.bollinger_lband()
            df_copy['bollinger_middle'] = bollinger.bollinger_mavg()
            df_copy['bollinger_width'] = (df_copy['bollinger_upper'] - df_copy['bollinger_lower']) / df_copy['bollinger_middle']
            df_copy['bollinger_position'] = (df_copy['close'] - df_copy['bollinger_lower']) / (df_copy['bollinger_upper'] - df_copy['bollinger_lower'])
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores básicos: {e}")
            return df_copy
    
    @staticmethod
    def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores de momentum"""
        df_copy = df.copy()
        
        try:
            # Stochastic Oscillator
            stoch = ta.momentum.StochasticOscillator(df_copy['high'], df_copy['low'], df_copy['close'])
            df_copy['stoch_k'] = stoch.stoch()
            df_copy['stoch_d'] = stoch.stoch_signal()
            
            # Williams %R
            df_copy['williams_r'] = ta.momentum.williams_r(df_copy['high'], df_copy['low'], df_copy['close'])
            
            # ROC (Rate of Change)
            df_copy['roc_10'] = ta.momentum.roc(df_copy['close'], window=10)
            df_copy['roc_20'] = ta.momentum.roc(df_copy['close'], window=20)
            
            # TSI (True Strength Index)
            df_copy['tsi'] = ta.momentum.tsi(df_copy['close'])
            
            # Awesome Oscillator
            df_copy['awesome_oscillator'] = ta.momentum.awesome_oscillator(df_copy['high'], df_copy['low'])
            
            # KST (Know Sure Thing)
            df_copy['kst'] = ta.momentum.kst(df_copy['close'])
            df_copy['kst_signal'] = ta.momentum.kst_sig(df_copy['close'])
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de momentum: {e}")
            return df_copy
    
    @staticmethod
    def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores de volatilidad"""
        df_copy = df.copy()
        
        try:
            # ATR (Average True Range)
            df_copy['atr_14'] = ta.volatility.average_true_range(df_copy['high'], df_copy['low'], df_copy['close'], window=14)
            df_copy['atr_21'] = ta.volatility.average_true_range(df_copy['high'], df_copy['low'], df_copy['close'], window=21)
            
            # Keltner Channels
            keltner = ta.volatility.KeltnerChannel(df_copy['high'], df_copy['low'], df_copy['close'])
            df_copy['keltner_upper'] = keltner.keltner_channel_hband()
            df_copy['keltner_lower'] = keltner.keltner_channel_lband()
            df_copy['keltner_middle'] = keltner.keltner_channel_mband()
            
            # Donchian Channels
            donchian = ta.volatility.DonchianChannel(df_copy['high'], df_copy['low'], df_copy['close'])
            df_copy['donchian_upper'] = donchian.donchian_channel_hband()
            df_copy['donchian_lower'] = donchian.donchian_channel_lband()
            df_copy['donchian_middle'] = donchian.donchian_channel_mband()
            
            # Ulcer Index
            df_copy['ulcer_index'] = ta.volatility.ulcer_index(df_copy['close'])
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volatilidad: {e}")
            return df_copy
    
    @staticmethod
    def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores de volumen"""
        df_copy = df.copy()
        
        try:
            # OBV (On Balance Volume)
            df_copy['obv'] = ta.volume.on_balance_volume(df_copy['close'], df_copy['volume'])
            
            # VWAP (Volume Weighted Average Price)
            df_copy['vwap'] = ta.volume.volume_weighted_average_price(
                df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume']
            )
            
            # Volume SMA
            df_copy['volume_sma_10'] = ta.trend.sma_indicator(df_copy['volume'], window=10)
            df_copy['volume_sma_20'] = ta.trend.sma_indicator(df_copy['volume'], window=20)
            
            # Volume RSI
            df_copy['volume_rsi'] = ta.momentum.rsi(df_copy['volume'], window=14)
            
            # Accumulation/Distribution Line
            df_copy['ad_line'] = ta.volume.acc_dist_index(df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume'])
            
            # Chaikin Money Flow
            df_copy['cmf'] = ta.volume.chaikin_money_flow(df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume'])
            
            # Force Index
            df_copy['force_index'] = ta.volume.force_index(df_copy['close'], df_copy['volume'])
            
            # Money Flow Index
            df_copy['mfi'] = ta.volume.money_flow_index(df_copy['high'], df_copy['low'], df_copy['close'], df_copy['volume'])
            
            # Volume relative to moving average
            df_copy['volume_ratio'] = df_copy['volume'] / df_copy['volume_sma_20']
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volumen: {e}")
            return df_copy
    
    @staticmethod
    def add_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores de tendencia"""
        df_copy = df.copy()
        
        try:
            # ADX (Average Directional Index)
            df_copy['adx'] = ta.trend.adx(df_copy['high'], df_copy['low'], df_copy['close'])
            df_copy['adx_pos'] = ta.trend.adx_pos(df_copy['high'], df_copy['low'], df_copy['close'])
            df_copy['adx_neg'] = ta.trend.adx_neg(df_copy['high'], df_copy['low'], df_copy['close'])
            
            # Parabolic SAR
            df_copy['psar'] = ta.trend.psar_down(df_copy['high'], df_copy['low'], df_copy['close'])
            
            # CCI (Commodity Channel Index)
            df_copy['cci'] = ta.trend.cci(df_copy['high'], df_copy['low'], df_copy['close'])
            
            # DPO (Detrended Price Oscillator)
            df_copy['dpo'] = ta.trend.dpo(df_copy['close'])
            
            # KST Oscillator
            df_copy['kst_oscillator'] = ta.trend.kst(df_copy['close'])
            
            # Ichimoku
            ichimoku = ta.trend.IchimokuIndicator(df_copy['high'], df_copy['low'])
            df_copy['ichimoku_a'] = ichimoku.ichimoku_a()
            df_copy['ichimoku_b'] = ichimoku.ichimoku_b()
            df_copy['ichimoku_base'] = ichimoku.ichimoku_base_line()
            df_copy['ichimoku_conversion'] = ichimoku.ichimoku_conversion_line()
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de tendencia: {e}")
            return df_copy

class PriceActionFeatures:
    """Clase para features de price action"""
    
    @staticmethod
    def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de precio"""
        df_copy = df.copy()
        
        try:
            # Returns
            df_copy['return_1'] = df_copy['close'].pct_change(1)
            df_copy['return_5'] = df_copy['close'].pct_change(5)
            df_copy['return_10'] = df_copy['close'].pct_change(10)
            df_copy['return_20'] = df_copy['close'].pct_change(20)
            
            # Log returns
            df_copy['log_return'] = np.log(df_copy['close'] / df_copy['close'].shift(1))
            
            # High-Low ratio
            df_copy['hl_ratio'] = df_copy['high'] / df_copy['low']
            
            # Open-Close ratio
            df_copy['oc_ratio'] = df_copy['open'] / df_copy['close']
            
            # Body size (candlestick)
            df_copy['body_size'] = abs(df_copy['close'] - df_copy['open']) / df_copy['open']
            
            # Upper shadow
            df_copy['upper_shadow'] = (df_copy['high'] - np.maximum(df_copy['open'], df_copy['close'])) / df_copy['open']
            
            # Lower shadow
            df_copy['lower_shadow'] = (np.minimum(df_copy['open'], df_copy['close']) - df_copy['low']) / df_copy['open']
            
            # Price position in range
            df_copy['price_position'] = (df_copy['close'] - df_copy['low']) / (df_copy['high'] - df_copy['low'])
            
            # Volatility (rolling std of returns)
            df_copy['volatility_10'] = df_copy['return_1'].rolling(10).std()
            df_copy['volatility_20'] = df_copy['return_1'].rolling(20).std()
            
            # Price acceleration
            df_copy['price_acceleration'] = df_copy['return_1'].diff()
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando features de precio: {e}")
            return df_copy
    
    @staticmethod
    def add_support_resistance_levels(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Añade niveles de soporte y resistencia"""
        df_copy = df.copy()
        
        try:
            # Rolling max/min para resistencia/soporte
            df_copy['resistance_level'] = df_copy['high'].rolling(window).max()
            df_copy['support_level'] = df_copy['low'].rolling(window).min()
            
            # Distancia a niveles
            df_copy['distance_to_resistance'] = (df_copy['resistance_level'] - df_copy['close']) / df_copy['close']
            df_copy['distance_to_support'] = (df_copy['close'] - df_copy['support_level']) / df_copy['close']
            
            # Pivots (simplified)
            df_copy['pivot'] = (df_copy['high'] + df_copy['low'] + df_copy['close']) / 3
            df_copy['pivot_r1'] = 2 * df_copy['pivot'] - df_copy['low']
            df_copy['pivot_s1'] = 2 * df_copy['pivot'] - df_copy['high']
            
            return df_copy
            
        except Exception as e:
            logger.error(f"Error calculando soporte/resistencia: {e}")
            return df_copy

class DataPreprocessor:
    """Procesador principal de datos"""
    
    def __init__(self):
        self.scaler_type = "robust"  # robust, standard, minmax
        self.scalers = {}
        self.feature_columns = []
        
        # Configuración desde usuario
        self.ai_settings = user_config.get_ai_model_settings()
        self.lookback_window = user_config.get_value(['ai_model_settings', 'lookback_window'], 60)
        
        logger.info("DataPreprocessor inicializado")
    
    def get_raw_data(
        self, 
        symbol: str = "BTCUSDT", 
        days_back: int = 100,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        """Obtiene datos crudos de la base de datos"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            df = db_manager.get_market_data(symbol, start_date, end_date)
            
            if df.empty:
                logger.warning(f"No se encontraron datos para {symbol}")
                return pd.DataFrame()
            
            # Asegurar que tenemos las columnas básicas
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"Faltan columnas requeridas en los datos")
                return pd.DataFrame()
            
            # Limpiar datos
            df = df.dropna()
            df = df[df['volume'] > 0]  # Remover períodos sin volumen
            
            logger.info(f"Datos crudos obtenidos: {len(df)} registros para {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos crudos: {e}")
            return pd.DataFrame()
    
    def add_all_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade todos los indicadores técnicos"""
        try:
            if df.empty:
                return df
            
            logger.info("Calculando indicadores técnicos...")
            
            # Añadir diferentes grupos de indicadores
            df = TechnicalIndicators.add_basic_indicators(df)
            df = TechnicalIndicators.add_momentum_indicators(df)
            df = TechnicalIndicators.add_volatility_indicators(df)
            df = TechnicalIndicators.add_volume_indicators(df)
            df = TechnicalIndicators.add_trend_indicators(df)
            
            # Añadir features de price action
            df = PriceActionFeatures.add_price_features(df)
            df = PriceActionFeatures.add_support_resistance_levels(df)
            
            logger.info(f"Indicadores técnicos calculados. Columnas totales: {len(df.columns)}")
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores técnicos: {e}")
            return df
    
    def add_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features de régimen de mercado"""
        try:
            if df.empty:
                return df
            
            # Volatility regime
            df['volatility_regime'] = pd.cut(
                df['volatility_20'].fillna(0), 
                bins=3, 
                labels=['low_vol', 'medium_vol', 'high_vol']
            )
            
            # Trend regime basado en SMA
            df['trend_regime'] = np.where(
                df['close'] > df['sma_50'], 'uptrend',
                np.where(df['close'] < df['sma_50'], 'downtrend', 'sideways')
            )
            
            # Market strength basado en ADX
            df['market_strength'] = pd.cut(
                df['adx'].fillna(0),
                bins=[0, 25, 50, 100],
                labels=['weak', 'moderate', 'strong']
            )
            
            # One-hot encode categorical features
            regime_dummies = pd.get_dummies(df[['volatility_regime', 'trend_regime', 'market_strength']], 
                                          prefix=['vol', 'trend', 'strength'])
            df = pd.concat([df, regime_dummies], axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error añadiendo features de régimen: {e}")
            return df
    
    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade features temporales"""
        try:
            if df.empty:
                return df
            
            # Asegurar que el índice es datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                return df
            
            # Features de tiempo
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            df['day_of_month'] = df.index.day
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter
            
            # Features cíclicas (para capturar naturaleza cíclica del tiempo)
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            # Es fin de semana
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            
            # Horarios importantes de mercado (UTC)
            df['asian_session'] = ((df['hour'] >= 23) | (df['hour'] <= 8)).astype(int)
            df['european_session'] = ((df['hour'] >= 7) & (df['hour'] <= 16)).astype(int)
            df['us_session'] = ((df['hour'] >= 13) & (df['hour'] <= 22)).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error añadiendo features temporales: {e}")
            return df
    
    def create_target_variable(self, df: pd.DataFrame, method: str = "classification") -> pd.DataFrame:
        """Crea variable objetivo para el modelo"""
        try:
            if df.empty:
                return df
            
            if method == "classification":
                # Clasificación: 0=SELL, 1=HOLD, 2=BUY
                future_return = df['close'].shift(-1) / df['close'] - 1
                
                # Umbrales basados en volatilidad
                volatility = df['return_1'].rolling(20).std()
                upper_threshold = volatility * 0.5  # 0.5x volatilidad para BUY
                lower_threshold = -volatility * 0.5  # -0.5x volatilidad para SELL
                
                df['target'] = np.where(
                    future_return > upper_threshold, 2,  # BUY
                    np.where(future_return < lower_threshold, 0, 1)  # SELL, HOLD
                )
                
            elif method == "regression":
                # Regresión: retorno futuro
                df['target'] = df['close'].shift(-1) / df['close'] - 1
                
            # Remover último registro (no tiene target)
            df = df[:-1]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creando variable objetivo: {e}")
            return df
    
    def clean_and_impute_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia e imputa datos faltantes"""
        try:
            if df.empty:
                return df
            
            # Remover columnas con demasiados NaN (>50%)
            threshold = len(df) * 0.5
            df = df.dropna(axis=1, thresh=threshold)
            
            # Identificar columnas numéricas
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            categorical_columns = df.select_dtypes(exclude=[np.number]).columns
            
            # Imputar valores numéricos
            if len(numeric_columns) > 0:
                imputer_numeric = SimpleImputer(strategy='median')
                df[numeric_columns] = imputer_numeric.fit_transform(df[numeric_columns])
            
            # Imputar valores categóricos
            if len(categorical_columns) > 0:
                imputer_categorical = SimpleImputer(strategy='most_frequent')
                df[categorical_columns] = imputer_categorical.fit_transform(df[categorical_columns])
            
            # Remover infinitos
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # Remover outliers extremos (más de 6 desviaciones estándar)
            for col in numeric_columns:
                if col in df.columns:
                    mean = df[col].mean()
                    std = df[col].std()
                    df[col] = df[col].clip(lower=mean - 6*std, upper=mean + 6*std)
            
            return df
            
        except Exception as e:
            logger.error(f"Error limpiando datos: {e}")
            return df
    
    def scale_features(self, df: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """Escala las features"""
        try:
            if df.empty:
                return df
            
            # Identificar columnas a escalar (excluir target y categóricas)
            exclude_columns = ['target'] + [col for col in df.columns if 'vol_' in col or 'trend_' in col or 'strength_' in col]
            scale_columns = [col for col in df.columns if col not in exclude_columns and df[col].dtype in ['float64', 'int64']]
            
            if not scale_columns:
                return df
            
            # Configurar scaler
            if self.scaler_type == "robust":
                scaler_class = RobustScaler
            elif self.scaler_type == "standard":
                scaler_class = StandardScaler
            else:  # minmax
                scaler_class = MinMaxScaler
            
            if fit_scaler:
                self.scalers['features'] = scaler_class()
                df[scale_columns] = self.scalers['features'].fit_transform(df[scale_columns])
            else:
                if 'features' in self.scalers:
                    df[scale_columns] = self.scalers['features'].transform(df[scale_columns])
                else:
                    logger.warning("Scaler no encontrado, no se escalaron las features")
            
            return df
            
        except Exception as e:
            logger.error(f"Error escalando features: {e}")
            return df
    
    def create_sequences(self, df: pd.DataFrame, lookback: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Crea secuencias para LSTM"""
        try:
            if lookback is None:
                lookback = self.lookback_window
            
            if df.empty or len(df) < lookback + 1:
                logger.warning("Datos insuficientes para crear secuencias")
                return np.array([]), np.array([])
            
            # Separar features y target
            feature_columns = [col for col in df.columns if col != 'target']
            self.feature_columns = feature_columns
            
            X_data = df[feature_columns].values
            y_data = df['target'].values if 'target' in df.columns else None
            
            # Crear secuencias
            X_sequences = []
            y_sequences = []
            
            for i in range(lookback, len(X_data)):
                X_sequences.append(X_data[i-lookback:i])
                if y_data is not None:
                    y_sequences.append(y_data[i])
            
            X_sequences = np.array(X_sequences)
            y_sequences = np.array(y_sequences) if y_sequences else np.array([])
            
            logger.info(f"Secuencias creadas: X shape {X_sequences.shape}, y shape {y_sequences.shape}")
            return X_sequences, y_sequences
            
        except Exception as e:
            logger.error(f"Error creando secuencias: {e}")
            return np.array([]), np.array([])
    
    def prepare_training_data(
        self, 
        symbol: str = "BTCUSDT",
        days_back: int = 100,
        target_method: str = "classification"
    ) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """Pipeline completo de preparación de datos para entrenamiento"""
        try:
            logger.info(f"Preparando datos de entrenamiento para {symbol}")
            
            # 1. Obtener datos crudos
            df = self.get_raw_data(symbol, days_back)
            if df.empty:
                return np.array([]), np.array([]), pd.DataFrame()
            
            # 2. Añadir indicadores técnicos
            df = self.add_all_technical_indicators(df)
            
            # 3. Añadir features de régimen de mercado
            df = self.add_market_regime_features(df)
            
            # 4. Añadir features temporales
            df = self.add_time_features(df)
            
            # 5. Crear variable objetivo
            df = self.create_target_variable(df, target_method)
            
            # 6. Limpiar e imputar
            df = self.clean_and_impute_data(df)
            
            # 7. Escalar features
            df = self.scale_features(df, fit_scaler=True)
            
            # 8. Crear secuencias
            X, y = self.create_sequences(df)
            
            logger.info(f"Datos preparados exitosamente: {X.shape[0]} muestras, {X.shape[2]} features")
            return X, y, df
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento: {e}")
            return np.array([]), np.array([]), pd.DataFrame()
    
    def prepare_prediction_data(self, df: pd.DataFrame) -> np.ndarray:
        """Prepara datos para predicción (sin target)"""
        try:
            if df.empty:
                return np.array([])
            
            # Aplicar mismo pipeline que entrenamiento (sin target)
            df = self.add_all_technical_indicators(df)
            df = self.add_market_regime_features(df)
            df = self.add_time_features(df)
            df = self.clean_and_impute_data(df)
            df = self.scale_features(df, fit_scaler=False)  # Usar scaler ya entrenado
            
            # Crear secuencia para última predicción
            if len(df) >= self.lookback_window:
                # Usar solo las columnas de features conocidas
                if self.feature_columns:
                    feature_data = df[self.feature_columns].tail(self.lookback_window).values
                    return feature_data.reshape(1, self.lookback_window, len(self.feature_columns))
            
            return np.array([])
            
        except Exception as e:
            logger.error(f"Error preparando datos para predicción: {e}")
            return np.array([])
    
    def get_feature_importance_weights(self) -> Dict[str, float]:
        """Obtiene pesos de importancia de features configurados por el usuario"""
        feature_importance = self.ai_settings.get('feature_importance', {})
        
        return {
            'price_action': feature_importance.get('price_action', 0.3),
            'technical_indicators': feature_importance.get('technical_indicators', 0.4),
            'volume_analysis': feature_importance.get('volume_analysis', 0.2),
            'market_sentiment': feature_importance.get('market_sentiment', 0.1)
        }
    
    def get_preprocessing_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del preprocessor"""
        return {
            'scaler_type': self.scaler_type,
            'lookback_window': self.lookback_window,
            'feature_columns_count': len(self.feature_columns),
            'feature_columns': self.feature_columns[:10] if self.feature_columns else [],  # Mostrar solo primeras 10
            'scalers_fitted': list(self.scalers.keys()),
            'feature_importance_weights': self.get_feature_importance_weights()
        }

# Instancia global del preprocessor
data_preprocessor = DataPreprocessor()