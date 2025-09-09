# signal_generator.py - Generador de señales ML en tiempo real
# Ubicación: C:\TradingBot_v10\trading\enterprise\signal_generator.py

"""
Generador de señales ML en tiempo real para trading enterprise.

Características principales:
- Inferencia ML <100ms
- Múltiples modelos (LSTM, Transformer, CNN-LSTM)
- Features técnicos en tiempo real
- Confianza y predicciones de volatilidad
- Cache de predicciones
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import threading
from dataclasses import dataclass
import json
from pathlib import Path

# ML imports
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
import joblib

# Imports del proyecto
from trading.enterprise.trading_signal import TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

@dataclass
class ModelPrediction:
    """Predicción de un modelo ML"""
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    predicted_return: float
    predicted_volatility: float
    features_used: Dict[str, float]
    model_name: str
    inference_time: float
    timestamp: datetime

class MLSignalGenerator:
    """
    Generador de señales ML en tiempo real
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el generador de señales ML
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.models = {}
        self.scalers = {}
        self.feature_cache = {}
        self.prediction_cache = {}
        
        # Configuración de modelos
        self.model_config = config.trading.strategies.ml_strategy
        self.signal_config = self.model_config.signals
        
        # Cache de predicciones
        self.cache_ttl_seconds = 30  # 30 segundos
        self.max_cache_size = 1000
        
        # Threading para inferencia asíncrona
        self.inference_queue = asyncio.Queue()
        self.inference_worker = None
        
        # Métricas de performance
        self.inference_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Inicializar modelos
        self.load_models()
        
        # Iniciar worker de inferencia
        self.start_inference_worker()
        
        logger.info("MLSignalGenerator inicializado")
    
    def load_models(self):
        """Carga los modelos ML entrenados"""
        try:
            models_dir = Path("models/trained_models")
            
            # Cargar modelo principal (LSTM + Attention)
            lstm_model_path = models_dir / "lstm_attention" / "best_model.pth"
            if lstm_model_path.exists():
                self.models['lstm_attention'] = self.load_pytorch_model(lstm_model_path)
                logger.info("✅ Modelo LSTM + Attention cargado")
            
            # Cargar modelo Transformer
            transformer_model_path = models_dir / "transformer" / "best_model.pth"
            if transformer_model_path.exists():
                self.models['transformer'] = self.load_pytorch_model(transformer_model_path)
                logger.info("✅ Modelo Transformer cargado")
            
            # Cargar modelo CNN-LSTM
            cnn_lstm_model_path = models_dir / "cnn_lstm" / "best_model.pth"
            if cnn_lstm_model_path.exists():
                self.models['cnn_lstm'] = self.load_pytorch_model(cnn_lstm_model_path)
                logger.info("✅ Modelo CNN-LSTM cargado")
            
            # Cargar scalers
            scalers_dir = models_dir / "scalers"
            for model_name in self.models.keys():
                scaler_path = scalers_dir / f"{model_name}_scaler.pkl"
                if scaler_path.exists():
                    self.scalers[model_name] = joblib.load(scaler_path)
                    logger.info(f"✅ Scaler para {model_name} cargado")
            
            if not self.models:
                logger.warning("⚠️ No se encontraron modelos ML. Usando modelo dummy.")
                self.create_dummy_models()
            
        except Exception as e:
            logger.error(f"Error cargando modelos: {e}")
            self.create_dummy_models()
    
    def load_pytorch_model(self, model_path: Path) -> nn.Module:
        """Carga un modelo PyTorch"""
        try:
            # Cargar checkpoint
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # Crear modelo (simplificado - en producción se usaría la clase real)
            model = self.create_model_architecture(checkpoint.get('model_type', 'lstm_attention'))
            
            # Cargar pesos
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()
            
            return model
            
        except Exception as e:
            logger.error(f"Error cargando modelo PyTorch: {e}")
            return self.create_dummy_model()
    
    def create_model_architecture(self, model_type: str) -> nn.Module:
        """Crea la arquitectura del modelo"""
        if model_type == 'lstm_attention':
            return self.create_lstm_attention_model()
        elif model_type == 'transformer':
            return self.create_transformer_model()
        elif model_type == 'cnn_lstm':
            return self.create_cnn_lstm_model()
        else:
            return self.create_dummy_model()
    
    def create_lstm_attention_model(self) -> nn.Module:
        """Crea modelo LSTM con atención"""
        class LSTMAttentionModel(nn.Module):
            def __init__(self, input_size=20, hidden_size=64, num_layers=2, output_size=3):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.attention = nn.MultiheadAttention(hidden_size, num_heads=8)
                self.fc = nn.Linear(hidden_size, output_size)
                self.dropout = nn.Dropout(0.2)
                
            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
                output = self.fc(self.dropout(attn_out[:, -1, :]))
                return output
        
        return LSTMAttentionModel()
    
    def create_transformer_model(self) -> nn.Module:
        """Crea modelo Transformer"""
        class TransformerModel(nn.Module):
            def __init__(self, input_size=20, d_model=64, nhead=8, num_layers=4, output_size=3):
                super().__init__()
                self.input_projection = nn.Linear(input_size, d_model)
                self.pos_encoding = nn.Parameter(torch.randn(100, d_model))
                encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=256)
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
                self.fc = nn.Linear(d_model, output_size)
                
            def forward(self, x):
                x = self.input_projection(x)
                seq_len = x.size(1)
                x = x + self.pos_encoding[:seq_len, :].unsqueeze(0)
                x = x.transpose(0, 1)  # (seq_len, batch, d_model)
                transformer_out = self.transformer(x)
                output = self.fc(transformer_out[-1])  # Usar última salida
                return output
        
        return TransformerModel()
    
    def create_cnn_lstm_model(self) -> nn.Module:
        """Crea modelo CNN-LSTM"""
        class CNNLSTMModel(nn.Module):
            def __init__(self, input_size=20, cnn_filters=32, lstm_hidden=64, output_size=3):
                super().__init__()
                self.conv1d = nn.Conv1d(input_size, cnn_filters, kernel_size=3, padding=1)
                self.pool = nn.MaxPool1d(2)
                self.lstm = nn.LSTM(cnn_filters, lstm_hidden, batch_first=True)
                self.fc = nn.Linear(lstm_hidden, output_size)
                
            def forward(self, x):
                # x: (batch, seq_len, features)
                x = x.transpose(1, 2)  # (batch, features, seq_len)
                cnn_out = self.pool(torch.relu(self.conv1d(x)))
                cnn_out = cnn_out.transpose(1, 2)  # (batch, seq_len, filters)
                lstm_out, _ = self.lstm(cnn_out)
                output = self.fc(lstm_out[:, -1, :])
                return output
        
        return CNNLSTMModel()
    
    def create_dummy_model(self) -> nn.Module:
        """Crea modelo dummy para testing"""
        class DummyModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(20, 3)
                
            def forward(self, x):
                return self.fc(x[:, -1, :])  # Usar última timestep
        
        return DummyModel()
    
    def create_dummy_models(self):
        """Crea modelos dummy para testing"""
        self.models = {
            'lstm_attention': self.create_dummy_model(),
            'transformer': self.create_dummy_model(),
            'cnn_lstm': self.create_dummy_model()
        }
        
        # Crear scalers dummy
        for model_name in self.models.keys():
            self.scalers[model_name] = StandardScaler()
            # Fit con datos dummy
            dummy_data = np.random.randn(100, 20)
            self.scalers[model_name].fit(dummy_data)
        
        logger.info("✅ Modelos dummy creados para testing")
    
    def start_inference_worker(self):
        """Inicia worker para inferencia asíncrona"""
        def inference_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process_inference_queue():
                while True:
                    try:
                        task = await self.inference_queue.get()
                        if task is None:  # Shutdown signal
                            break
                        
                        symbol, market_data, callback = task
                        result = await self._generate_signal_async(symbol, market_data)
                        if callback:
                            callback(result)
                        
                        self.inference_queue.task_done()
                        
                    except Exception as e:
                        logger.error(f"Error en inference worker: {e}")
            
            loop.run_until_complete(process_inference_queue())
            loop.close()
        
        self.inference_worker = threading.Thread(target=inference_worker, daemon=True)
        self.inference_worker.start()
    
    async def generate_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """
        Genera una señal de trading para un símbolo
        
        Args:
            symbol: Símbolo a analizar
            market_data: Datos de mercado actuales
            
        Returns:
            Señal de trading generada
        """
        try:
            # Verificar cache
            cache_key = f"{symbol}_{int(time.time() // self.cache_ttl_seconds)}"
            if cache_key in self.prediction_cache:
                self.cache_hits += 1
                cached_prediction = self.prediction_cache[cache_key]
                return self._prediction_to_signal(symbol, cached_prediction)
            
            self.cache_misses += 1
            
            # Generar features
            features = await self.extract_features(symbol, market_data)
            if features is None:
                return None
            
            # Generar predicciones con múltiples modelos
            predictions = await self._generate_predictions(symbol, features)
            
            # Agregar al cache
            self.prediction_cache[cache_key] = predictions
            self._cleanup_cache()
            
            # Convertir a señal de trading
            signal = self._predictions_to_signal(symbol, predictions)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generando señal para {symbol}: {e}")
            return None
    
    async def _generate_signal_async(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """Versión asíncrona de generate_signal"""
        return await self.generate_signal(symbol, market_data)
    
    async def extract_features(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """
        Extrae features técnicos de los datos de mercado
        
        Args:
            symbol: Símbolo a analizar
            market_data: Datos de mercado
            
        Returns:
            Array de features normalizado
        """
        try:
            # Obtener datos históricos para calcular indicadores
            historical_data = await self.get_historical_data(symbol, lookback_periods=100)
            if historical_data is None or len(historical_data) < 50:
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Calcular features técnicos
            features = self.calculate_technical_features(df)
            
            # Normalizar features
            if symbol in self.scalers:
                scaler = self.scalers[symbol]
            else:
                # Usar scaler por defecto
                scaler = list(self.scalers.values())[0] if self.scalers else None
            
            if scaler:
                features = scaler.transform(features.reshape(1, -1))
            else:
                features = features.reshape(1, -1)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extrayendo features para {symbol}: {e}")
            return None
    
    def calculate_technical_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Calcula features técnicos de un DataFrame de precios
        
        Args:
            df: DataFrame con columnas OHLCV
            
        Returns:
            Array de features
        """
        try:
            features = []
            
            # Precios
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values
            
            # Moving averages
            sma_10 = pd.Series(close).rolling(10).mean().values
            sma_20 = pd.Series(close).rolling(20).mean().values
            sma_50 = pd.Series(close).rolling(50).mean().values
            
            # Exponential moving averages
            ema_12 = pd.Series(close).ewm(span=12).mean().values
            ema_26 = pd.Series(close).ewm(span=26).mean().values
            
            # RSI
            rsi = self.calculate_rsi(close, 14)
            
            # MACD
            macd, macd_signal, macd_hist = self.calculate_macd(close)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(close, 20, 2)
            
            # ATR
            atr = self.calculate_atr(high, low, close, 14)
            
            # Volume indicators
            volume_sma = pd.Series(volume).rolling(20).mean().values
            volume_ratio = volume / volume_sma
            
            # Price momentum
            price_change_1 = (close[-1] - close[-2]) / close[-2] if len(close) > 1 else 0
            price_change_5 = (close[-1] - close[-6]) / close[-6] if len(close) > 5 else 0
            price_change_20 = (close[-1] - close[-21]) / close[-21] if len(close) > 20 else 0
            
            # Volatility
            volatility_20 = pd.Series(close).rolling(20).std().values[-1] / close[-1]
            
            # Features finales (usar últimos valores)
            features = [
                close[-1] / close[-2] - 1 if len(close) > 1 else 0,  # Price change
                sma_10[-1] / close[-1] - 1 if not np.isnan(sma_10[-1]) else 0,  # Price vs SMA10
                sma_20[-1] / close[-1] - 1 if not np.isnan(sma_20[-1]) else 0,  # Price vs SMA20
                sma_50[-1] / close[-1] - 1 if not np.isnan(sma_50[-1]) else 0,  # Price vs SMA50
                ema_12[-1] / close[-1] - 1 if not np.isnan(ema_12[-1]) else 0,  # Price vs EMA12
                ema_26[-1] / close[-1] - 1 if not np.isnan(ema_26[-1]) else 0,  # Price vs EMA26
                rsi[-1] / 100 - 0.5 if not np.isnan(rsi[-1]) else 0,  # RSI normalized
                macd[-1] if not np.isnan(macd[-1]) else 0,  # MACD
                macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0,  # MACD Signal
                macd_hist[-1] if not np.isnan(macd_hist[-1]) else 0,  # MACD Histogram
                (close[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1]) - 0.5 if not np.isnan(bb_upper[-1]) else 0,  # BB Position
                atr[-1] / close[-1] if not np.isnan(atr[-1]) else 0,  # ATR normalized
                volume_ratio[-1] - 1 if not np.isnan(volume_ratio[-1]) else 0,  # Volume ratio
                price_change_1,  # 1-period change
                price_change_5,  # 5-period change
                price_change_20,  # 20-period change
                volatility_20,  # 20-period volatility
                high[-1] / close[-1] - 1,  # High vs close
                low[-1] / close[-1] - 1,  # Low vs close
                (high[-1] - low[-1]) / close[-1]  # Range normalized
            ]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Error calculando features técnicos: {e}")
            return np.zeros(20, dtype=np.float32)
    
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcula RSI"""
        try:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = pd.Series(gains).rolling(period).mean().values
            avg_losses = pd.Series(losses).rolling(period).mean().values
            
            rs = avg_gains / (avg_losses + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except:
            return np.full(len(prices), 50.0)
    
    def calculate_macd(self, prices: np.ndarray, fast=12, slow=26, signal=9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula MACD"""
        try:
            ema_fast = pd.Series(prices).ewm(span=fast).mean().values
            ema_slow = pd.Series(prices).ewm(span=slow).mean().values
            
            macd = ema_fast - ema_slow
            macd_signal = pd.Series(macd).ewm(span=signal).mean().values
            macd_hist = macd - macd_signal
            
            return macd, macd_signal, macd_hist
        except:
            return np.zeros(len(prices)), np.zeros(len(prices)), np.zeros(len(prices))
    
    def calculate_bollinger_bands(self, prices: np.ndarray, period=20, std_dev=2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula Bollinger Bands"""
        try:
            sma = pd.Series(prices).rolling(period).mean().values
            std = pd.Series(prices).rolling(period).std().values
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return upper, sma, lower
        except:
            return np.full(len(prices), prices[-1]), np.full(len(prices), prices[-1]), np.full(len(prices), prices[-1])
    
    def calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period=14) -> np.ndarray:
        """Calcula Average True Range"""
        try:
            high_low = high - low
            high_close = np.abs(high - np.roll(close, 1))
            low_close = np.abs(low - np.roll(close, 1))
            
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = pd.Series(true_range).rolling(period).mean().values
            
            return atr
        except:
            return np.full(len(close), 0.0)
    
    async def get_historical_data(self, symbol: str, lookback_periods: int = 100) -> Optional[List[Dict]]:
        """
        Obtiene datos históricos para un símbolo
        
        Args:
            symbol: Símbolo a obtener
            lookback_periods: Número de períodos a obtener
            
        Returns:
            Lista de datos históricos
        """
        try:
            # En un sistema real, esto vendría del data collector
            # Por ahora, generar datos dummy
            data = []
            base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.0
            
            for i in range(lookback_periods):
                price = base_price * (1 + np.random.normal(0, 0.02))
                data.append({
                    'timestamp': datetime.now() - timedelta(minutes=lookback_periods-i),
                    'open': price * 0.999,
                    'high': price * 1.001,
                    'low': price * 0.998,
                    'close': price,
                    'volume': np.random.uniform(1000, 10000)
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos para {symbol}: {e}")
            return None
    
    async def _generate_predictions(
        self,
        symbol: str,
        features: np.ndarray
    ) -> Dict[str, ModelPrediction]:
        """
        Genera predicciones con múltiples modelos
        
        Args:
            symbol: Símbolo a predecir
            features: Features normalizados
            
        Returns:
            Diccionario con predicciones de cada modelo
        """
        predictions = {}
        
        for model_name, model in self.models.items():
            try:
                start_time = time.time()
                
                # Preparar input para el modelo
                if len(features.shape) == 2:
                    # Agregar dimensión de secuencia si es necesario
                    features_input = features.reshape(1, 1, -1)
                else:
                    features_input = features
                
                # Convertir a tensor
                features_tensor = torch.FloatTensor(features_input)
                
                # Inferencia
                with torch.no_grad():
                    output = model(features_tensor)
                    
                    # Aplicar softmax para probabilidades
                    probabilities = torch.softmax(output, dim=-1).numpy()[0]
                    
                    # Obtener predicción
                    action_idx = np.argmax(probabilities)
                    actions = ['SELL', 'HOLD', 'BUY']
                    action = actions[action_idx]
                    
                    # Calcular confianza
                    confidence = float(probabilities[action_idx])
                    
                    # Calcular predicciones adicionales
                    predicted_return = float(output[0][action_idx] * 0.1)  # Escalar
                    predicted_volatility = float(np.std(probabilities) * 0.05)  # Basado en incertidumbre
                
                inference_time = time.time() - start_time
                
                # Crear predicción
                prediction = ModelPrediction(
                    action=action,
                    confidence=confidence,
                    predicted_return=predicted_return,
                    predicted_volatility=predicted_volatility,
                    features_used={f'feature_{i}': float(features[0][i]) for i in range(len(features[0]))},
                    model_name=model_name,
                    inference_time=inference_time,
                    timestamp=datetime.now()
                )
                
                predictions[model_name] = prediction
                
                # Actualizar métricas
                self.inference_times.append(inference_time)
                if len(self.inference_times) > 1000:
                    self.inference_times = self.inference_times[-1000:]
                
            except Exception as e:
                logger.error(f"Error generando predicción con {model_name}: {e}")
                continue
        
        return predictions
    
    def _predictions_to_signal(
        self,
        symbol: str,
        predictions: Dict[str, ModelPrediction]
    ) -> TradingSignal:
        """
        Convierte predicciones de modelos en una señal de trading
        
        Args:
            symbol: Símbolo
            predictions: Predicciones de múltiples modelos
            
        Returns:
            Señal de trading consolidada
        """
        try:
            if not predictions:
                # Señal por defecto si no hay predicciones
                return TradingSignal(
                    symbol=symbol,
                    action='HOLD',
                    confidence=0.5,
                    predicted_return=0.0,
                    predicted_volatility=0.02,
                    time_horizon_minutes=60,
                    features_used={},
                    model_version='none',
                    timestamp=datetime.now()
                )
            
            # Agregación de predicciones (promedio ponderado por confianza)
            total_confidence = 0
            weighted_actions = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            weighted_return = 0
            weighted_volatility = 0
            all_features = {}
            
            for model_name, prediction in predictions.items():
                weight = prediction.confidence
                total_confidence += weight
                
                weighted_actions[prediction.action] += weight
                weighted_return += prediction.predicted_return * weight
                weighted_volatility += prediction.predicted_volatility * weight
                
                # Combinar features
                all_features.update(prediction.features_used)
            
            # Normalizar pesos
            if total_confidence > 0:
                for action in weighted_actions:
                    weighted_actions[action] /= total_confidence
                weighted_return /= total_confidence
                weighted_volatility /= total_confidence
            
            # Determinar acción final
            final_action = max(weighted_actions, key=weighted_actions.get)
            final_confidence = weighted_actions[final_action]
            
            # Aplicar umbral de confianza
            if final_confidence < self.signal_config.min_confidence:
                final_action = 'HOLD'
                final_confidence = 0.5
            
            # Crear señal
            signal = TradingSignal(
                symbol=symbol,
                action=final_action,
                confidence=final_confidence,
                predicted_return=weighted_return,
                predicted_volatility=weighted_volatility,
                time_horizon_minutes=self.model_config.model.prediction_horizon_minutes,
                features_used=all_features,
                model_version=f"ensemble_{len(predictions)}",
                timestamp=datetime.now()
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error convirtiendo predicciones a señal: {e}")
            return TradingSignal(
                symbol=symbol,
                action='HOLD',
                confidence=0.5,
                predicted_return=0.0,
                predicted_volatility=0.02,
                time_horizon_minutes=60,
                features_used={},
                model_version='error',
                timestamp=datetime.now()
            )
    
    def _prediction_to_signal(self, symbol: str, prediction: ModelPrediction) -> TradingSignal:
        """Convierte una predicción individual a señal"""
        return TradingSignal(
            symbol=symbol,
            action=prediction.action,
            confidence=prediction.confidence,
            predicted_return=prediction.predicted_return,
            predicted_volatility=prediction.predicted_volatility,
            time_horizon_minutes=self.model_config.model.prediction_horizon_minutes,
            features_used=prediction.features_used,
            model_version=prediction.model_name,
            timestamp=prediction.timestamp
        )
    
    def _cleanup_cache(self):
        """Limpia el cache de predicciones"""
        if len(self.prediction_cache) > self.max_cache_size:
            # Remover entradas más antiguas
            sorted_items = sorted(self.prediction_cache.items(), key=lambda x: x[1].timestamp)
            items_to_remove = len(self.prediction_cache) - self.max_cache_size
            for i in range(items_to_remove):
                del self.prediction_cache[sorted_items[i][0]]
    
    async def get_latest_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Obtiene la última señal generada para un símbolo"""
        # Buscar en cache
        for cache_key, prediction in self.prediction_cache.items():
            if cache_key.startswith(symbol):
                return self._prediction_to_signal(symbol, prediction)
        
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del generador de señales"""
        try:
            # Verificar modelos cargados
            models_loaded = len(self.models) > 0
            
            # Verificar scalers
            scalers_loaded = len(self.scalers) > 0
            
            # Verificar performance de inferencia
            avg_inference_time = np.mean(self.inference_times) if self.inference_times else 0
            max_inference_time = np.max(self.inference_times) if self.inference_times else 0
            
            # Verificar cache
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            
            return {
                'healthy': models_loaded and scalers_loaded and avg_inference_time < 0.1,
                'models_loaded': models_loaded,
                'scalers_loaded': scalers_loaded,
                'avg_inference_time': avg_inference_time,
                'max_inference_time': max_inference_time,
                'cache_hit_rate': cache_hit_rate,
                'cache_size': len(self.prediction_cache),
                'inference_worker_alive': self.inference_worker and self.inference_worker.is_alive()
            }
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {'healthy': False, 'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance del generador"""
        return {
            'avg_inference_time': np.mean(self.inference_times) if self.inference_times else 0,
            'max_inference_time': np.max(self.inference_times) if self.inference_times else 0,
            'min_inference_time': np.min(self.inference_times) if self.inference_times else 0,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'cache_size': len(self.prediction_cache),
            'models_loaded': len(self.models),
            'scalers_loaded': len(self.scalers)
        }
