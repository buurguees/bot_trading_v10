"""
models/predictor.py
Sistema de predicciones en tiempo real para trading
Ubicación: C:\\TradingBot_v10\\models\\predictor.py

Funcionalidades:
- Predicciones en tiempo real con múltiples modelos
- Cálculo de confianza y incertidumbre (Monte Carlo Dropout)
- Agregación inteligente de predicciones (ensemble)
- Análisis de contexto de mercado
- Calibración de probabilidades
- Cache inteligente para optimización
- Sistema de alertas por confianza
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
import pickle
from pathlib import Path
from collections import deque
import warnings
warnings.filterwarnings('ignore')

from .neural_network import TradingModel, create_model
from .trainer import MarketRegimeDetector
from data.preprocessor import data_preprocessor
from data.database import db_manager
from config.config_loader import user_config
from config.settings import MODELS_DIR

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Resultado completo de predicción"""
    # Predicción principal
    signal: int  # 0=SELL, 1=HOLD, 2=BUY
    confidence: float  # 0-1
    probabilities: List[float]  # [prob_sell, prob_hold, prob_buy]
    
    # Predicciones adicionales
    expected_return: float  # Retorno esperado %
    expected_return_range: Tuple[float, float]  # Rango de confianza
    risk_score: float  # Puntuación de riesgo 0-1
    volatility_forecast: float  # Volatilidad esperada
    
    # Metadata
    timestamp: datetime
    symbol: str
    model_version: str
    models_used: List[str]
    features_importance: Dict[str, float]
    
    # Contexto de mercado
    market_regime: str = "unknown"
    market_context: Dict[str, Any] = field(default_factory=dict)
    
    # Reasoning explicable
    reasoning: Dict[str, Any] = field(default_factory=dict)
    technical_signals: Dict[str, float] = field(default_factory=dict)
    
    # Alertas y recomendaciones
    alerts: List[str] = field(default_factory=list)
    action_strength: str = "weak"  # weak, moderate, strong
    suggested_position_size: float = 0.0  # % del balance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {
            'signal': self.signal,
            'signal_name': ['SELL', 'HOLD', 'BUY'][self.signal],
            'confidence': self.confidence,
            'probabilities': self.probabilities,
            'expected_return': self.expected_return,
            'expected_return_range': self.expected_return_range,
            'risk_score': self.risk_score,
            'volatility_forecast': self.volatility_forecast,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'model_version': self.model_version,
            'models_used': self.models_used,
            'market_regime': self.market_regime,
            'market_context': self.market_context,
            'reasoning': self.reasoning,
            'technical_signals': self.technical_signals,
            'alerts': self.alerts,
            'action_strength': self.action_strength,
            'suggested_position_size': self.suggested_position_size,
            'features_importance': self.features_importance
        }

@dataclass
class MarketContext:
    """Contexto completo de mercado para predicciones"""
    # Métricas básicas
    volatility: float
    trend_strength: float
    volume_profile: str  # "low", "normal", "high", "extreme"
    
    # Sesiones de mercado
    market_session: str  # "asian", "european", "us", "overlap", "closed"
    session_activity: float  # 0-1, actividad de la sesión
    
    # Momentum y tendencia
    recent_momentum: float  # -1 a 1
    momentum_strength: float  # 0-1
    trend_consistency: float  # 0-1
    
    # Soporte y resistencia
    support_resistance_levels: Dict[str, float]
    distance_to_support: float
    distance_to_resistance: float
    
    # Indicadores técnicos clave
    rsi: float
    macd_signal: float
    bollinger_position: float  # Posición en Bollinger Bands
    
    # Análisis de volumen
    volume_trend: str  # "increasing", "decreasing", "stable"
    volume_anomaly: bool  # Volumen inusual
    
    # Contexto temporal
    time_of_day: int  # Hora UTC
    day_of_week: int
    is_news_period: bool  # Período típico de noticias
    
    # Condiciones de riesgo
    market_stress: float  # 0-1, nivel de estrés del mercado
    liquidity_score: float  # 0-1, estimación de liquidez

class ConfidenceCalculator:
    """Calculador avanzado de confianza para predicciones"""
    
    def __init__(self):
        self.historical_accuracy = {}
        self.volatility_adjustments = {}
        self.model_reliability_scores = {}
        
        # Configuración
        self.ai_settings = user_config.get_ai_model_settings()
        
    def calculate_prediction_confidence(
        self, 
        model_probabilities: np.ndarray,
        market_context: MarketContext,
        model_versions: List[str],
        ensemble_agreement: float = 1.0,
        monte_carlo_uncertainty: float = 0.0
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcula confianza de predicción basada en múltiples factores
        Retorna: (confianza_final, breakdown_factores)
        """
        try:
            breakdown = {}
            
            # 1. Confianza base del modelo (entropía inversa)
            base_confidence = self._calculate_base_confidence(model_probabilities)
            breakdown['base_model'] = base_confidence
            
            # 2. Factor de accuracy histórica
            accuracy_factor = self._get_historical_accuracy_factor(model_versions)
            breakdown['historical_accuracy'] = accuracy_factor
            
            # 3. Ajuste por contexto de mercado
            market_factor = self._calculate_market_context_factor(market_context)
            breakdown['market_context'] = market_factor
            
            # 4. Factor de acuerdo entre modelos (si es ensemble)
            ensemble_factor = min(ensemble_agreement, 1.0)
            breakdown['ensemble_agreement'] = ensemble_factor
            
            # 5. Penalización por incertidumbre (Monte Carlo)
            uncertainty_penalty = 1.0 - min(monte_carlo_uncertainty, 0.5)
            breakdown['uncertainty_penalty'] = uncertainty_penalty
            
            # 6. Factor de volatilidad
            volatility_factor = self._get_volatility_adjustment(market_context.volatility)
            breakdown['volatility_adjustment'] = volatility_factor
            
            # 7. Factor de liquidez y condiciones de mercado
            liquidity_factor = self._get_liquidity_factor(market_context)
            breakdown['liquidity_factor'] = liquidity_factor
            
            # 8. Factor temporal (ciertas horas son más predecibles)
            temporal_factor = self._get_temporal_factor(market_context)
            breakdown['temporal_factor'] = temporal_factor
            
            # Combinación ponderada de factores
            weights = {
                'base_model': 0.25,
                'historical_accuracy': 0.20,
                'market_context': 0.15,
                'ensemble_agreement': 0.15,
                'uncertainty_penalty': 0.10,
                'volatility_adjustment': 0.10,
                'liquidity_factor': 0.03,
                'temporal_factor': 0.02
            }
            
            final_confidence = sum(
                breakdown[factor] * weight 
                for factor, weight in weights.items()
            )
            
            # Normalizar entre 0 y 1
            final_confidence = np.clip(final_confidence, 0.0, 1.0)
            
            # Añadir confianza final al breakdown
            breakdown['final_confidence'] = final_confidence
            
            return final_confidence, breakdown
            
        except Exception as e:
            logger.error(f"Error calculando confianza: {e}")
            return 0.5, {'error': True}
    
    def _calculate_base_confidence(self, probabilities: np.ndarray) -> float:
        """Calcula confianza base usando entropía y max probability"""
        try:
            # Máxima probabilidad
            max_prob = np.max(probabilities)
            
            # Entropía normalizada (menor entropía = mayor confianza)
            entropy = -np.sum(probabilities * np.log(probabilities + 1e-8))
            max_entropy = np.log(len(probabilities))
            normalized_entropy = entropy / max_entropy
            confidence_from_entropy = 1.0 - normalized_entropy
            
            # Combinar max_prob y entropy
            base_confidence = (max_prob * 0.7) + (confidence_from_entropy * 0.3)
            
            return base_confidence
            
        except Exception as e:
            logger.error(f"Error calculando confianza base: {e}")
            return 0.5
    
    def _get_historical_accuracy_factor(self, model_versions: List[str]) -> float:
        """Factor basado en accuracy histórica de los modelos"""
        try:
            accuracies = []
            
            for version in model_versions:
                if version in self.historical_accuracy:
                    accuracies.append(self.historical_accuracy[version])
                else:
                    # Buscar en base de datos
                    latest_metrics = db_manager.get_latest_model_metrics()
                    if latest_metrics:
                        accuracy = latest_metrics.accuracy
                        self.historical_accuracy[version] = accuracy
                        accuracies.append(accuracy)
            
            if accuracies:
                avg_accuracy = np.mean(accuracies)
                # Convertir accuracy (0.5-1.0) a factor de confianza (0-1)
                return (avg_accuracy - 0.5) * 2.0
            
            return 0.6  # Default
            
        except Exception as e:
            logger.error(f"Error obteniendo factor de accuracy: {e}")
            return 0.6
    
    def _calculate_market_context_factor(self, context: MarketContext) -> float:
        """Factor basado en condiciones favorables del mercado"""
        try:
            factor = 1.0
            
            # Ajuste por fuerza de tendencia
            if context.trend_strength > 0.7:
                factor *= 1.15  # Tendencias fuertes son más predecibles
            elif context.trend_strength < 0.3:
                factor *= 0.85  # Mercados laterales menos predecibles
            
            # Ajuste por consistencia de momentum
            factor *= (0.8 + (context.momentum_strength * 0.4))
            
            # Ajuste por estrés del mercado
            factor *= (1.0 - (context.market_stress * 0.3))
            
            # Ajuste por sesión de mercado
            if context.market_session in ["overlap"]:
                factor *= 1.1  # Sesiones activas más predecibles
            elif context.market_session == "closed":
                factor *= 0.7  # Mercados cerrados menos confiables
            
            # Ajuste por anomalías de volumen
            if context.volume_anomaly:
                factor *= 0.9  # Volumen anómalo reduce confianza
            
            return np.clip(factor, 0.3, 1.3)
            
        except Exception as e:
            logger.error(f"Error calculando factor de contexto: {e}")
            return 1.0
    
    def _get_volatilidad_adjustment(self, volatility: float) -> float:
        """Ajuste por volatilidad del mercado"""
        if volatility > 0.08:  # Volatilidad muy alta
            return 0.6
        elif volatility > 0.05:  # Volatilidad alta
            return 0.75
        elif volatility > 0.03:  # Volatilidad normal
            return 1.0
        elif volatility > 0.01:  # Volatilidad baja
            return 1.05
        else:  # Volatilidad muy baja (posible baja liquidez)
            return 0.8
    
    def _get_liquidity_factor(self, context: MarketContext) -> float:
        """Factor basado en liquidez estimada"""
        return 0.8 + (context.liquidity_score * 0.4)
    
    def _get_temporal_factor(self, context: MarketContext) -> float:
        """Factor basado en momento temporal"""
        # Horas de mayor actividad (UTC)
        active_hours = [7, 8, 9, 13, 14, 15, 16, 20, 21]  # Aperturas Europa y US
        
        if context.time_of_day in active_hours:
            return 1.05
        elif context.is_news_period:
            return 0.9  # Períodos de noticias menos predecibles
        else:
            return 1.0

class MarketContextAnalyzer:
    """Analizador de contexto de mercado en tiempo real"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutos
        
    def analyze_market_context(self, symbol: str, lookback_periods: int = 100) -> MarketContext:
        """Analiza contexto completo del mercado"""
        try:
            # Verificar cache
            cache_key = f"{symbol}_{int(time.time() / self.cache_timeout)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Obtener datos recientes
            recent_data = db_manager.get_latest_market_data(symbol, lookback_periods)
            
            if recent_data.empty:
                return self._get_default_context()
            
            # Calcular métricas del contexto
            context = MarketContext(
                volatility=self._calculate_volatility(recent_data),
                trend_strength=self._calculate_trend_strength(recent_data),
                volume_profile=self._analyze_volume_profile(recent_data),
                market_session=self._get_market_session(),
                session_activity=self._calculate_session_activity(),
                recent_momentum=self._calculate_momentum(recent_data),
                momentum_strength=self._calculate_momentum_strength(recent_data),
                trend_consistency=self._calculate_trend_consistency(recent_data),
                support_resistance_levels=self._find_support_resistance(recent_data),
                distance_to_support=0.0,  # Se calcula después
                distance_to_resistance=0.0,  # Se calcula después
                rsi=self._calculate_rsi(recent_data),
                macd_signal=self._calculate_macd_signal(recent_data),
                bollinger_position=self._calculate_bollinger_position(recent_data),
                volume_trend=self._analyze_volume_trend(recent_data),
                volume_anomaly=self._detect_volume_anomaly(recent_data),
                time_of_day=datetime.now().hour,
                day_of_week=datetime.now().weekday(),
                is_news_period=self._is_news_period(),
                market_stress=self._calculate_market_stress(recent_data),
                liquidity_score=self._estimate_liquidity(recent_data)
            )
            
            # Calcular distancias a soporte/resistencia
            current_price = recent_data['close'].iloc[-1]
            sr_levels = context.support_resistance_levels
            
            if 'support' in sr_levels:
                context.distance_to_support = (current_price - sr_levels['support']) / current_price
            if 'resistance' in sr_levels:
                context.distance_to_resistance = (sr_levels['resistance'] - current_price) / current_price
            
            # Guardar en cache
            self.cache[cache_key] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Error analizando contexto de mercado: {e}")
            return self._get_default_context()
    
    def _get_default_context(self) -> MarketContext:
        """Contexto por defecto en caso de error"""
        return MarketContext(
            volatility=0.03,
            trend_strength=0.5,
            volume_profile="normal",
            market_session="unknown",
            session_activity=0.5,
            recent_momentum=0.0,
            momentum_strength=0.5,
            trend_consistency=0.5,
            support_resistance_levels={},
            distance_to_support=0.0,
            distance_to_resistance=0.0,
            rsi=50.0,
            macd_signal=0.0,
            bollinger_position=0.5,
            volume_trend="stable",
            volume_anomaly=False,
            time_of_day=datetime.now().hour,
            day_of_week=datetime.now().weekday(),
            is_news_period=False,
            market_stress=0.3,
            liquidity_score=0.7
        )
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calcula volatilidad reciente"""
        returns = data['close'].pct_change().dropna()
        return returns.rolling(20).std().iloc[-1] if len(returns) > 20 else 0.03
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calcula fuerza de la tendencia"""
        try:
            if len(data) < 50:
                return 0.5
            
            sma_20 = data['close'].rolling(20).mean()
            sma_50 = data['close'].rolling(50).mean()
            
            # Diferencia entre SMAs como indicador de tendencia
            trend_diff = abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1]
            
            # Normalizar a 0-1
            return min(trend_diff * 20, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando fuerza de tendencia: {e}")
            return 0.5
    
    def _analyze_volume_profile(self, data: pd.DataFrame) -> str:
        """Analiza perfil de volumen"""
        try:
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            
            ratio = current_volume / avg_volume
            
            if ratio > 2.0:
                return "extreme"
            elif ratio > 1.5:
                return "high"
            elif ratio < 0.5:
                return "low"
            else:
                return "normal"
                
        except Exception as e:
            logger.error(f"Error analizando volumen: {e}")
            return "normal"
    
    def _get_market_session(self) -> str:
        """Determina sesión de mercado actual"""
        hour_utc = datetime.now().hour
        
        # Sesiones aproximadas (UTC)
        if 23 <= hour_utc or hour_utc <= 8:
            return "asian"
        elif 7 <= hour_utc <= 16:
            return "european"
        elif 13 <= hour_utc <= 22:
            return "us"
        elif 13 <= hour_utc <= 16:  # Overlap Europe-US
            return "overlap"
        else:
            return "closed"
    
    def _calculate_session_activity(self) -> float:
        """Calcula nivel de actividad de la sesión"""
        session = self._get_market_session()
        activity_levels = {
            "overlap": 1.0,
            "us": 0.9,
            "european": 0.8,
            "asian": 0.6,
            "closed": 0.3
        }
        return activity_levels.get(session, 0.5)
    
    def _calculate_momentum(self, data: pd.DataFrame) -> float:
        """Calcula momentum reciente"""
        try:
            if len(data) < 10:
                return 0.0
            
            # ROC (Rate of Change) de 10 períodos
            roc = (data['close'].iloc[-1] - data['close'].iloc[-10]) / data['close'].iloc[-10]
            
            # Normalizar a -1, 1
            return np.clip(roc * 10, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando momentum: {e}")
            return 0.0
    
    def _calculate_momentum_strength(self, data: pd.DataFrame) -> float:
        """Calcula fuerza del momentum"""
        try:
            momentum = abs(self._calculate_momentum(data))
            return min(momentum, 1.0)
        except Exception as e:
            return 0.5
    
    def _calculate_trend_consistency(self, data: pd.DataFrame) -> float:
        """Calcula consistencia de la tendencia"""
        try:
            if len(data) < 20:
                return 0.5
            
            # Porcentaje de velas en dirección de la tendencia
            sma = data['close'].rolling(10).mean()
            trend_up = sma.diff() > 0
            
            consistency = trend_up.rolling(10).mean().iloc[-1]
            
            # Convertir a 0-1 donde 0.5 es neutral
            return abs(consistency - 0.5) * 2
            
        except Exception as e:
            return 0.5
    
    def _find_support_resistance(self, data: pd.DataFrame) -> Dict[str, float]:
        """Encuentra niveles de soporte y resistencia"""
        try:
            if len(data) < 50:
                return {}
            
            # Niveles simples basados en máximos y mínimos recientes
            recent_high = data['high'].rolling(20).max().iloc[-1]
            recent_low = data['low'].rolling(20).min().iloc[-1]
            
            return {
                'resistance': recent_high,
                'support': recent_low
            }
            
        except Exception as e:
            return {}
    
    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calcula RSI"""
        try:
            if len(data) < period + 1:
                return 50.0
            
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            return 50.0
    
    def _calculate_macd_signal(self, data: pd.DataFrame) -> float:
        """Calcula señal MACD"""
        try:
            if len(data) < 26:
                return 0.0
            
            ema_12 = data['close'].ewm(span=12).mean()
            ema_26 = data['close'].ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            
            macd_histogram = macd - signal
            
            return macd_histogram.iloc[-1] if not np.isnan(macd_histogram.iloc[-1]) else 0.0
            
        except Exception as e:
            return 0.0
    
    def _calculate_bollinger_position(self, data: pd.DataFrame) -> float:
        """Calcula posición en Bollinger Bands"""
        try:
            if len(data) < 20:
                return 0.5
            
            sma = data['close'].rolling(20).mean()
            std = data['close'].rolling(20).std()
            
            upper_band = sma + (2 * std)
            lower_band = sma - (2 * std)
            
            current_price = data['close'].iloc[-1]
            
            # Posición relativa en las bandas (0 = banda inferior, 1 = banda superior)
            position = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
            
            return np.clip(position, 0.0, 1.0)
            
        except Exception as e:
            return 0.5
    
    def _analyze_volume_trend(self, data: pd.DataFrame) -> str:
        """Analiza tendencia del volumen"""
        try:
            if len(data) < 10:
                return "stable"
            
            volume_sma_short = data['volume'].rolling(5).mean()
            volume_sma_long = data['volume'].rolling(10).mean()
            
            if volume_sma_short.iloc[-1] > volume_sma_long.iloc[-1] * 1.1:
                return "increasing"
            elif volume_sma_short.iloc[-1] < volume_sma_long.iloc[-1] * 0.9:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            return "stable"
    
    def _detect_volume_anomaly(self, data: pd.DataFrame) -> bool:
        """Detecta anomalías en el volumen"""
        try:
            current_volume = data['volume'].iloc[-1]
            volume_mean = data['volume'].rolling(20).mean().iloc[-1]
            volume_std = data['volume'].rolling(20).std().iloc[-1]
            
            # Anomalía si está más de 2 desviaciones estándar de la media
            z_score = abs(current_volume - volume_mean) / volume_std
            
            return z_score > 2.0
            
        except Exception as e:
            return False
    
    def _is_news_period(self) -> bool:
        """Determina si es período típico de noticias"""
        hour_utc = datetime.now().hour
        
        # Períodos típicos de noticias importantes (UTC)
        news_hours = [8, 9, 13, 14, 15, 21, 22]  # Aperturas y cierres principales
        
        return hour_utc in news_hours
    
    def _calculate_market_stress(self, data: pd.DataFrame) -> float:
        """Calcula nivel de estrés del mercado"""
        try:
            # Basado en volatilidad y movimientos extremos
            volatility = self._calculate_volatility(data)
            
            # Movimientos extremos recientes
            returns = data['close'].pct_change().dropna()
            extreme_moves = (abs(returns) > 0.03).rolling(10).mean().iloc[-1]
            
            # Combinar factores
            stress = (volatility * 10) + (extreme_moves * 0.5)
            
            return np.clip(stress, 0.0, 1.0)
            
        except Exception as e:
            return 0.3
    
    def _estimate_liquidity(self, data: pd.DataFrame) -> float:
        """Estima liquidez del mercado"""
        try:
            # Basado en volumen y spread estimado
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            # Spread estimado basado en high-low
            spreads = (data['high'] - data['low']) / data['close']
            avg_spread = spreads.rolling(10).mean().iloc[-1]
            
            # Liquidez inversamente proporcional al spread
            liquidity_from_spread = 1.0 - min(avg_spread * 50, 1.0)
            
            # Liquidez proporcional al volumen
            liquidity_from_volume = min(current_volume / avg_volume, 2.0) / 2.0
            
            # Combinar factores
            liquidity = (liquidity_from_spread * 0.6) + (liquidity_from_volume * 0.4)
            
            return np.clip(liquidity, 0.0, 1.0)
            
        except Exception as e:
            return 0.7

class RealTimePredictor:
    """Predictor en tiempo real con capacidades avanzadas"""
    
    def __init__(self):
        self.models = {}
        self.ensemble_weights = {}
        self.confidence_calculator = ConfidenceCalculator()
        self.market_analyzer = MarketContextAnalyzer()
        self.regime_detector = MarketRegimeDetector()
        
        # Cache para optimización
        self.prediction_cache = {}
        self.cache_timeout = 60  # 1 minuto
        
        # Threading para predicciones asíncronas
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Configuración
        self.ai_settings = user_config.get_ai_model_settings()
        self.min_confidence = self.ai_settings['confidence']['min_confidence_to_trade'] / 100.0
        
        # Tracking de predicciones
        self.prediction_history = deque(maxlen=1000)
        
        logger.info("RealTimePredictor inicializado")
    
    def load_models(self, model_paths: List[str] = None, auto_discover: bool = True):
        """Carga modelos entrenados"""
        try:
            loaded_count = 0
            
            if auto_discover and model_paths is None:
                # Buscar modelos automáticamente
                model_paths = list(MODELS_DIR.glob("*.h5"))
                logger.info(f"Auto-descubrimiento encontró {len(model_paths)} modelos")
            
            for path in (model_paths or []):
                try:
                    # Intentar determinar tipo de modelo desde metadata
                    metadata_path = Path(path).with_suffix('.json')
                    model_type = "lstm"  # Default
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            model_type = metadata.get('model_type', 'lstm')
                    
                    model = create_model(model_type)
                    
                    if model.load_model(str(path)):
                        self.models[model.model_version] = model
                        
                        # Calcular peso inicial basado en métricas históricas
                        self._calculate_model_weight(model.model_version)
                        
                        loaded_count += 1
                        logger.info(f"Modelo cargado: {model.model_version}")
                    
                except Exception as e:
                    logger.warning(f"Error cargando modelo {path}: {e}")
            
            logger.info(f"Modelos cargados exitosamente: {loaded_count}")
            
            # Normalizar pesos del ensemble
            self._normalize_ensemble_weights()
            
        except Exception as e:
            logger.error(f"Error cargando modelos: {e}")
    
    def _calculate_model_weight(self, model_version: str):
        """Calcula peso del modelo basado en performance histórica"""
        try:
            # Obtener métricas desde base de datos
            latest_metrics = db_manager.get_latest_model_metrics()
            
            if latest_metrics and latest_metrics.model_version == model_version:
                # Peso basado en accuracy, f1_score y otros factores
                accuracy = latest_metrics.accuracy
                f1_score = latest_metrics.f1_score
                
                # Obtener Sharpe ratio si está disponible
                hyperparams = latest_metrics.hyperparameters
                sharpe_ratio = 0.0
                if isinstance(hyperparams, dict):
                    sharpe_ratio = hyperparams.get('sharpe_ratio', 0.0)
                
                # Calcular peso combinado
                weight = (accuracy * 0.4 + f1_score * 0.3 + 
                         min(max(sharpe_ratio / 2.0, 0), 1) * 0.3)
                
                self.ensemble_weights[model_version] = max(weight, 0.1)  # Peso mínimo
            else:
                # Peso por defecto
                self.ensemble_weights[model_version] = 0.5
                
        except Exception as e:
            logger.error(f"Error calculando peso del modelo: {e}")
            self.ensemble_weights[model_version] = 0.5
    
    def _normalize_ensemble_weights(self):
        """Normaliza pesos del ensemble para que sumen 1"""
        try:
            if not self.ensemble_weights:
                return
            
            total_weight = sum(self.ensemble_weights.values())
            if total_weight > 0:
                for model_version in self.ensemble_weights:
                    self.ensemble_weights[model_version] /= total_weight
                    
        except Exception as e:
            logger.error(f"Error normalizando pesos: {e}")
    
    async def predict(
        self, 
        symbol: str = "BTCUSDT",
        use_cache: bool = True,
        explain_prediction: bool = True
    ) -> Optional[PredictionResult]:
        """Hace predicción completa para el símbolo dado"""
        try:
            start_time = time.time()
            
            # Verificar cache
            cache_key = f"{symbol}_{int(time.time() / self.cache_timeout)}"
            if use_cache and cache_key in self.prediction_cache:
                logger.debug(f"Predicción desde cache para {symbol}")
                return self.prediction_cache[cache_key]
            
            # Verificar que hay modelos cargados
            if not self.models:
                logger.warning("No hay modelos cargados para predicción")
                return None
            
            # 1. Obtener y preparar datos
            prediction_data = await self._prepare_prediction_data(symbol)
            if prediction_data is None or prediction_data.shape[0] == 0:
                logger.warning(f"No se pudieron preparar datos para predicción de {symbol}")
                return None
            
            # 2. Analizar contexto de mercado
            market_context = self.market_analyzer.analyze_market_context(symbol)
            market_regime = self.regime_detector.get_current_regime(symbol)
            
            # 3. Ejecutar predicciones de todos los modelos
            model_predictions = await self._execute_ensemble_predictions(prediction_data)
            
            if not model_predictions:
                logger.warning("No se pudieron obtener predicciones de los modelos")
                return None
            
            # 4. Agregar predicciones (ensemble)
            aggregated_prediction = self._aggregate_predictions(model_predictions)
            
            # 5. Calcular confianza
            confidence, confidence_breakdown = self._calculate_ensemble_confidence(
                model_predictions, market_context, aggregated_prediction
            )
            
            # 6. Generar predicción de retorno esperado
            expected_return, return_range = self._predict_expected_return(
                model_predictions, market_context
            )
            
            # 7. Calcular métricas de riesgo
            risk_score = self._calculate_risk_score(market_context, confidence)
            volatility_forecast = self._forecast_volatility(symbol, market_context)
            
            # 8. Determinar señal final
            signal = np.argmax(aggregated_prediction['probabilities'])
            
            # 9. Análisis de features importantes
            feature_importance = self._analyze_feature_importance(model_predictions)
            
            # 10. Generar señales técnicas explicables
            technical_signals = self._generate_technical_signals(market_context)
            
            # 11. Determinar fuerza de la acción y tamaño sugerido
            action_strength, suggested_size = self._determine_action_strength(
                confidence, aggregated_prediction['probabilities'], risk_score
            )
            
            # 12. Generar alertas
            alerts = self._generate_alerts(signal, confidence, market_context, risk_score)
            
            # 13. Crear resultado final
            result = PredictionResult(
                signal=signal,
                confidence=confidence,
                probabilities=aggregated_prediction['probabilities'].tolist(),
                expected_return=expected_return,
                expected_return_range=return_range,
                risk_score=risk_score,
                volatility_forecast=volatility_forecast,
                timestamp=datetime.now(),
                symbol=symbol,
                model_version=f"ensemble_{len(self.models)}",
                models_used=list(self.models.keys()),
                features_importance=feature_importance,
                market_regime=market_regime,
                market_context=market_context.__dict__,
                reasoning=confidence_breakdown if explain_prediction else {},
                technical_signals=technical_signals,
                alerts=alerts,
                action_strength=action_strength,
                suggested_position_size=suggested_size
            )
            
            # 14. Guardar en cache y tracking
            if use_cache:
                self.prediction_cache[cache_key] = result
            
            self.prediction_history.append({
                'timestamp': result.timestamp,
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'prediction_time_ms': (time.time() - start_time) * 1000
            })
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Predicción completada para {symbol}: {['SELL', 'HOLD', 'BUY'][signal]} "
                       f"(conf: {confidence:.3f}) en {processing_time:.1f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en predicción para {symbol}: {e}")
            return None
    
    async def _prepare_prediction_data(self, symbol: str) -> Optional[np.ndarray]:
        """Prepara datos para predicción usando el preprocessor"""
        try:
            # Obtener datos recientes (más de los necesarios para el lookback)
            recent_data = db_manager.get_latest_market_data(symbol, 150)
            
            if recent_data.empty:
                logger.warning(f"No hay datos históricos para {symbol}")
                return None
            
            # Usar el preprocessor para preparar datos
            prediction_array = data_preprocessor.prepare_prediction_data(recent_data)
            
            return prediction_array
            
        except Exception as e:
            logger.error(f"Error preparando datos de predicción: {e}")
            return None
    
    async def _execute_ensemble_predictions(self, prediction_data: np.ndarray) -> List[Dict[str, Any]]:
        """Ejecuta predicciones de todos los modelos en paralelo"""
        try:
            prediction_tasks = []
            
            for model_version, model in self.models.items():
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._single_model_prediction,
                    model,
                    prediction_data,
                    model_version
                )
                prediction_tasks.append(task)
            
            # Ejecutar todas las predicciones en paralelo
            results = await asyncio.gather(*prediction_tasks, return_exceptions=True)
            
            # Filtrar resultados exitosos
            valid_predictions = []
            for result in results:
                if isinstance(result, dict) and 'probabilities' in result:
                    valid_predictions.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Error en predicción de modelo: {result}")
            
            return valid_predictions
            
        except Exception as e:
            logger.error(f"Error ejecutando predicciones ensemble: {e}")
            return []
    
    def _single_model_prediction(
        self, 
        model: TradingModel, 
        prediction_data: np.ndarray,
        model_version: str
    ) -> Dict[str, Any]:
        """Ejecuta predicción de un solo modelo con Monte Carlo Dropout"""
        try:
            # Predicción estándar
            predictions = model.predict(prediction_data)
            
            # Manejar múltiples outputs
            if isinstance(predictions, list):
                classification_probs = predictions[0][0]  # Primera muestra
                regression_output = predictions[1][0] if len(predictions) > 1 else np.array([0.0])
                confidence_output = predictions[2][0] if len(predictions) > 2 else np.array([0.5])
            else:
                classification_probs = predictions[0]
                regression_output = np.array([0.0])
                confidence_output = np.array([0.5])
            
            # Monte Carlo Dropout para incertidumbre
            mc_uncertainty = 0.0
            try:
                mc_predictions = []
                for _ in range(20):  # 20 simulaciones MC
                    mc_pred = model.predict(prediction_data)
                    if isinstance(mc_pred, list):
                        mc_predictions.append(mc_pred[0][0])
                    else:
                        mc_predictions.append(mc_pred[0])
                
                mc_predictions = np.array(mc_predictions)
                mc_uncertainty = np.std(mc_predictions, axis=0).mean()
                
            except Exception as e:
                logger.debug(f"Error en Monte Carlo Dropout: {e}")
            
            return {
                'model_version': model_version,
                'probabilities': classification_probs,
                'regression_output': regression_output,
                'model_confidence': confidence_output,
                'mc_uncertainty': mc_uncertainty,
                'weight': self.ensemble_weights.get(model_version, 0.5)
            }
            
        except Exception as e:
            logger.error(f"Error en predicción de modelo {model_version}: {e}")
            return {}
    
    def _aggregate_predictions(self, model_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Agrega predicciones de múltiples modelos usando pesos"""
        try:
            if not model_predictions:
                return {'probabilities': np.array([0.33, 0.34, 0.33])}
            
            # Extraer probabilidades y pesos
            all_probs = []
            weights = []
            
            for pred in model_predictions:
                all_probs.append(pred['probabilities'])
                weights.append(pred['weight'])
            
            all_probs = np.array(all_probs)
            weights = np.array(weights)
            
            # Normalizar pesos
            weights = weights / np.sum(weights)
            
            # Agregación ponderada
            weighted_probs = np.average(all_probs, axis=0, weights=weights)
            
            # Calcular acuerdo entre modelos
            ensemble_agreement = self._calculate_ensemble_agreement(all_probs)
            
            # Agregación de outputs de regresión
            regression_outputs = [pred.get('regression_output', np.array([0.0])) for pred in model_predictions]
            weighted_regression = np.average(regression_outputs, axis=0, weights=weights)
            
            return {
                'probabilities': weighted_probs,
                'regression_output': weighted_regression,
                'ensemble_agreement': ensemble_agreement,
                'models_count': len(model_predictions)
            }
            
        except Exception as e:
            logger.error(f"Error agregando predicciones: {e}")
            return {'probabilities': np.array([0.33, 0.34, 0.33])}
    
    def _calculate_ensemble_agreement(self, all_predictions: np.ndarray) -> float:
        """Calcula acuerdo entre modelos del ensemble"""
        try:
            if len(all_predictions) < 2:
                return 1.0
            
            # Calcular desviación estándar promedio entre predicciones
            std_per_class = np.std(all_predictions, axis=0)
            avg_std = np.mean(std_per_class)
            
            # Convertir a score de acuerdo (menor std = mayor acuerdo)
            agreement = 1.0 - min(avg_std * 2, 1.0)
            
            return agreement
            
        except Exception as e:
            logger.error(f"Error calculando acuerdo ensemble: {e}")
            return 0.5
    
    def _calculate_ensemble_confidence(
        self,
        model_predictions: List[Dict[str, Any]],
        market_context: MarketContext,
        aggregated_prediction: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Calcula confianza del ensemble"""
        try:
            probabilities = aggregated_prediction['probabilities']
            ensemble_agreement = aggregated_prediction.get('ensemble_agreement', 1.0)
            
            # Calcular incertidumbre MC promedio
            mc_uncertainties = [pred.get('mc_uncertainty', 0.0) for pred in model_predictions]
            avg_mc_uncertainty = np.mean(mc_uncertainties)
            
            # Versiones de modelos
            model_versions = [pred['model_version'] for pred in model_predictions]
            
            return self.confidence_calculator.calculate_prediction_confidence(
                probabilities,
                market_context,
                model_versions,
                ensemble_agreement,
                avg_mc_uncertainty
            )
            
        except Exception as e:
            logger.error(f"Error calculando confianza ensemble: {e}")
            return 0.5, {'error': True}
    
    def _predict_expected_return(
        self,
        model_predictions: List[Dict[str, Any]],
        market_context: MarketContext
    ) -> Tuple[float, Tuple[float, float]]:
        """Predice retorno esperado y rango de confianza"""
        try:
            # Usar outputs de regresión si están disponibles
            regression_outputs = []
            for pred in model_predictions:
                reg_out = pred.get('regression_output', np.array([0.0]))
                if hasattr(reg_out, '__len__') and len(reg_out) > 0:
                    regression_outputs.append(reg_out[0])
                else:
                    regression_outputs.append(float(reg_out))
            
            if regression_outputs:
                expected_return = np.mean(regression_outputs)
                return_std = np.std(regression_outputs)
            else:
                # Fallback: estimar desde probabilidades
                # Asumir retornos típicos por clase
                class_returns = [-0.02, 0.0, 0.02]  # SELL, HOLD, BUY
                
                avg_probs = np.mean([pred['probabilities'] for pred in model_predictions], axis=0)
                expected_return = np.sum(avg_probs * class_returns)
                return_std = market_context.volatility
            
            # Ajustar por volatilidad de mercado
            volatility_adjustment = market_context.volatility / 0.03  # Normalizar
            expected_return *= volatility_adjustment
            return_std *= volatility_adjustment
            
            # Rango de confianza (±1 desviación estándar)
            return_range = (
                expected_return - return_std,
                expected_return + return_std
            )
            
            return expected_return, return_range
            
        except Exception as e:
            logger.error(f"Error prediciendo retorno esperado: {e}")
            return 0.0, (0.0, 0.0)
    
    def _calculate_risk_score(self, market_context: MarketContext, confidence: float) -> float:
        """Calcula score de riesgo"""
        try:
            # Factores de riesgo
            volatility_risk = min(market_context.volatility / 0.05, 1.0)  # Normalizar
            liquidity_risk = 1.0 - market_context.liquidity_score
            market_stress_risk = market_context.market_stress
            confidence_risk = 1.0 - confidence
            
            # Riesgo por sesión de mercado
            session_risk = {
                'overlap': 0.1,
                'us': 0.2,
                'european': 0.3,
                'asian': 0.4,
                'closed': 0.8
            }.get(market_context.market_session, 0.5)
            
            # Combinar factores de riesgo
            risk_score = (
                volatility_risk * 0.3 +
                liquidity_risk * 0.2 +
                market_stress_risk * 0.2 +
                confidence_risk * 0.2 +
                session_risk * 0.1
            )
            
            return np.clip(risk_score, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando risk score: {e}")
            return 0.5
    
    def _forecast_volatility(self, symbol: str, market_context: MarketContext) -> float:
        """Predice volatilidad futura"""
        try:
            # Volatilidad base actual
            current_vol = market_context.volatility
            
            # Ajustes por contexto
            if market_context.volume_anomaly:
                current_vol *= 1.2  # Volumen anómalo aumenta volatilidad
            
            if market_context.market_stress > 0.6:
                current_vol *= 1.3  # Alto estrés aumenta volatilidad
            
            if market_context.market_session == 'closed':
                current_vol *= 0.7  # Mercados cerrados menor volatilidad
            
            # Tendencia de volatilidad
            recent_data = db_manager.get_latest_market_data(symbol, 50)
            if not recent_data.empty:
                vol_series = recent_data['close'].pct_change().rolling(10).std()
                vol_trend = vol_series.diff().iloc[-1]
                
                if not np.isnan(vol_trend):
                    current_vol += vol_trend * 0.5  # Incorporar tendencia
            
            return max(current_vol, 0.005)  # Volatilidad mínima
            
        except Exception as e:
            logger.error(f"Error prediciendo volatilidad: {e}")
            return market_context.volatility
    
    def _analyze_feature_importance(self, model_predictions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analiza importancia de features (simplified)"""
        try:
            # Por ahora, usar importancias configuradas por el usuario
            feature_weights = user_config.get_value(['ai_model_settings', 'feature_importance'], {})
            
            return {
                'price_action': feature_weights.get('price_action', 0.3),
                'technical_indicators': feature_weights.get('technical_indicators', 0.4),
                'volume_analysis': feature_weights.get('volume_analysis', 0.2),
                'market_sentiment': feature_weights.get('market_sentiment', 0.1)
            }
            
        except Exception as e:
            logger.error(f"Error analizando importancia de features: {e}")
            return {'technical_indicators': 0.5, 'price_action': 0.5}
    
    def _generate_technical_signals(self, market_context: MarketContext) -> Dict[str, float]:
        """Genera señales técnicas explicables"""
        try:
            signals = {}
            
            # RSI Signal
            if market_context.rsi > 70:
                signals['rsi'] = -0.7  # Sobrecomprado
            elif market_context.rsi < 30:
                signals['rsi'] = 0.7   # Sobrevendido
            else:
                signals['rsi'] = 0.0
            
            # MACD Signal
            signals['macd'] = np.clip(market_context.macd_signal * 10, -1.0, 1.0)
            
            # Bollinger Signal
            if market_context.bollinger_position > 0.8:
                signals['bollinger'] = -0.6  # Cerca banda superior
            elif market_context.bollinger_position < 0.2:
                signals['bollinger'] = 0.6   # Cerca banda inferior
            else:
                signals['bollinger'] = 0.0
            
            # Trend Signal
            if market_context.trend_strength > 0.7:
                signals['trend'] = market_context.recent_momentum * 0.8
            else:
                signals['trend'] = 0.0
            
            # Volume Signal
            if market_context.volume_profile == 'high' and market_context.recent_momentum > 0:
                signals['volume'] = 0.5
            elif market_context.volume_profile == 'low':
                signals['volume'] = -0.2
            else:
                signals['volume'] = 0.0
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generando señales técnicas: {e}")
            return {}
    
    def _determine_action_strength(
        self,
        confidence: float,
        probabilities: np.ndarray,
        risk_score: float
    ) -> Tuple[str, float]:
        """Determina fuerza de la acción y tamaño de posición sugerido"""
        try:
            max_prob = np.max(probabilities)
            
            # Determinar fuerza
            if confidence > 0.8 and max_prob > 0.7:
                strength = "strong"
                base_size = 0.03  # 3% del balance
            elif confidence > 0.65 and max_prob > 0.6:
                strength = "moderate"
                base_size = 0.02  # 2% del balance
            elif confidence > 0.5 and max_prob > 0.5:
                strength = "weak"
                base_size = 0.01  # 1% del balance
            else:
                strength = "very_weak"
                base_size = 0.005  # 0.5% del balance
            
            # Ajustar por riesgo
            risk_adjustment = 1.0 - risk_score
            suggested_size = base_size * risk_adjustment
            
            # Límites de seguridad
            max_size = user_config.get_capital_settings()['max_risk_per_trade'] / 100.0
            suggested_size = min(suggested_size, max_size)
            
            return strength, suggested_size
            
        except Exception as e:
            logger.error(f"Error determinando fuerza de acción: {e}")
            return "weak", 0.01
    
    def _generate_alerts(
        self,
        signal: int,
        confidence: float,
        market_context: MarketContext,
        risk_score: float
    ) -> List[str]:
        """Genera alertas basadas en condiciones"""
        alerts = []
        
        try:
            # Alerta por baja confianza
            if confidence < self.min_confidence:
                alerts.append(f"⚠️ Confianza baja ({confidence:.1%}) - bajo threshold mínimo")
            
            # Alerta por alto riesgo
            if risk_score > 0.7:
                alerts.append(f"🚨 Alto riesgo detectado ({risk_score:.1%})")
            
            # Alerta por volatilidad extrema
            if market_context.volatility > 0.08:
                alerts.append(f"📈 Volatilidad extrema ({market_context.volatility:.1%})")
            
            # Alerta por condiciones de mercado
            if market_context.market_session == 'closed':
                alerts.append("🌙 Mercados principales cerrados - liquidez reducida")
            
            if market_context.volume_anomaly:
                alerts.append("📊 Volumen anómalo detectado")
            
            if market_context.market_stress > 0.8:
                alerts.append("😰 Alto estrés de mercado")
            
            # Alerta por RSI extremo
            if market_context.rsi > 80:
                alerts.append(f"📊 RSI sobrecomprado ({market_context.rsi:.1f})")
            elif market_context.rsi < 20:
                alerts.append(f"📊 RSI sobrevendido ({market_context.rsi:.1f})")
            
            # Alerta por proximidad a soporte/resistencia
            if abs(market_context.distance_to_resistance) < 0.01:
                alerts.append("🔴 Cerca de resistencia clave")
            elif abs(market_context.distance_to_support) < 0.01:
                alerts.append("🟢 Cerca de soporte clave")
            
        except Exception as e:
            logger.error(f"Error generando alertas: {e}")
        
        return alerts
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del predictor"""
        try:
            if not self.prediction_history:
                return {'total_predictions': 0}
            
            recent_predictions = list(self.prediction_history)[-100:]  # Últimas 100
            
            # Distribución de señales
            signals = [p['signal'] for p in recent_predictions]
            signal_distribution = {
                'sell': signals.count(0),
                'hold': signals.count(1),
                'buy': signals.count(2)
            }
            
            # Confianza promedio
            confidences = [p['confidence'] for p in recent_predictions]
            avg_confidence = np.mean(confidences)
            
            # Tiempo de predicción promedio
            times = [p['prediction_time_ms'] for p in recent_predictions]
            avg_prediction_time = np.mean(times)
            
            return {
                'total_predictions': len(self.prediction_history),
                'recent_predictions': len(recent_predictions),
                'signal_distribution': signal_distribution,
                'avg_confidence': avg_confidence,
                'avg_prediction_time_ms': avg_prediction_time,
                'models_loaded': len(self.models),
                'ensemble_weights': self.ensemble_weights.copy(),
                'cache_size': len(self.prediction_cache)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Limpia cache de predicciones"""
        self.prediction_cache.clear()
        logger.info("Cache de predicciones limpiado")
    
    def __del__(self):
        """Cleanup al destruir el objeto"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

class TradingPredictor(RealTimePredictor):
    """Alias para compatibilidad hacia atrás"""
    pass

# Instancia global del predictor
predictor = None

def get_predictor() -> RealTimePredictor:
    """Obtiene instancia global del predictor"""
    global predictor
    if predictor is None:
        predictor = RealTimePredictor()
    return predictor

async def quick_prediction(symbol: str = "BTCUSDT") -> Optional[PredictionResult]:
    """Función helper para predicción rápida"""
    try:
        pred = get_predictor()
        if not pred.models:
            pred.load_models()  # Auto-cargar modelos
        
        return await pred.predict(symbol, use_cache=True, explain_prediction=False)
        
    except Exception as e:
        logger.error(f"Error en predicción rápida: {e}")
        return None