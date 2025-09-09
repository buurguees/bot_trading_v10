"""
🧠 AutonomousDecisionEngine - Motor de Decisiones Autónomas

Motor que permite al agente tomar decisiones de trading de forma completamente
autónoma, basándose en análisis de mercado, predicciones ML y reglas de negocio.

Características:
- Análisis autónomo del estado del mercado
- Toma de decisiones basada en múltiples factores
- Evaluación de riesgo y oportunidad
- Generación de reasoning explicable
- Adaptación dinámica a condiciones cambiantes

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Imports del sistema existente
from config.config_loader import user_config
from models.predictor import predictor
from trading.risk_manager import risk_manager

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Tipos de decisiones que puede tomar el agente"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_POSITION = "close_position"
    REDUCE_POSITION = "reduce_position"
    INCREASE_POSITION = "increase_position"

class MarketCondition(Enum):
    """Condiciones del mercado"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    TRENDING = "trending"
    RANGING = "ranging"

@dataclass
class MarketAnalysis:
    """Análisis completo del estado del mercado"""
    trend_direction: str
    trend_strength: float
    volatility_level: str
    volume_profile: str
    support_resistance: Dict
    technical_indicators: Dict
    market_regime: str
    opportunity_score: float
    risk_level: str
    confidence: float

@dataclass
class DecisionContext:
    """Contexto para la toma de decisiones"""
    market_analysis: MarketAnalysis
    current_position: Optional[Dict]
    account_balance: float
    recent_performance: Dict
    market_conditions: Dict
    risk_tolerance: float
    time_horizon: str

class AutonomousDecisionEngine:
    """
    🧠 Motor de Decisiones Autónomas
    
    Permite al agente tomar decisiones de trading de forma completamente
    independiente, analizando múltiples factores y generando reasoning
    explicable para cada decisión.
    """
    
    def __init__(self):
        """Inicializa el motor de decisiones"""
        self.config = user_config
        self.decision_config = self.config.get_value(['ai_agent', 'decision_engine'], {})
        
        # Parámetros de decisión
        self.min_confidence = self.decision_config.get('min_confidence', 0.7)
        self.risk_tolerance = self.decision_config.get('risk_tolerance', 0.5)
        self.opportunity_threshold = self.decision_config.get('opportunity_threshold', 0.6)
        
        # Pesos para diferentes factores
        self.factor_weights = {
            'ml_prediction': 0.4,
            'technical_analysis': 0.3,
            'risk_assessment': 0.2,
            'market_context': 0.1
        }
        
        # Historial de decisiones
        self.decision_history = []
        self.performance_tracking = {}
        
        logger.info("🧠 AutonomousDecisionEngine inicializado")
    
    async def initialize(self) -> None:
        """Inicializa el motor de decisiones"""
        try:
            # Cargar configuración avanzada
            await self._load_decision_parameters()
            
            # Inicializar modelos de análisis
            await self._initialize_analysis_models()
            
            logger.info("✅ Motor de decisiones inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando motor de decisiones: {e}")
            raise
    
    async def analyze_market_state(self, market_data: Dict) -> MarketAnalysis:
        """
        Analiza el estado actual del mercado
        
        Args:
            market_data: Datos del mercado (klines, features, prediction, etc.)
            
        Returns:
            MarketAnalysis: Análisis completo del mercado
        """
        try:
            klines = market_data.get('klines', [])
            features = market_data.get('features')
            prediction = market_data.get('prediction', {})
            
            if not klines or len(klines) < 20:
                raise ValueError("Datos insuficientes para análisis")
            
            # Análisis de tendencia
            trend_analysis = await self._analyze_trend(klines)
            
            # Análisis de volatilidad
            volatility_analysis = await self._analyze_volatility(klines)
            
            # Análisis de volumen
            volume_analysis = await self._analyze_volume(klines)
            
            # Análisis técnico
            technical_analysis = await self._analyze_technical_indicators(klines, features)
            
            # Análisis de soporte y resistencia
            support_resistance = await self._analyze_support_resistance(klines)
            
            # Detección de régimen de mercado
            market_regime = await self._detect_market_regime(klines, features)
            
            # Cálculo de score de oportunidad
            opportunity_score = await self._calculate_opportunity_score(
                trend_analysis, volatility_analysis, technical_analysis, prediction
            )
            
            # Evaluación de riesgo
            risk_level = await self._assess_risk_level(
                volatility_analysis, market_regime, opportunity_score
            )
            
            # Confianza general del análisis
            confidence = await self._calculate_analysis_confidence(
                trend_analysis, technical_analysis, prediction
            )
            
            return MarketAnalysis(
                trend_direction=trend_analysis['direction'],
                trend_strength=trend_analysis['strength'],
                volatility_level=volatility_analysis['level'],
                volume_profile=volume_analysis['profile'],
                support_resistance=support_resistance,
                technical_indicators=technical_analysis,
                market_regime=market_regime,
                opportunity_score=opportunity_score,
                risk_level=risk_level,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Error analizando mercado: {e}")
            raise
    
    async def make_decision(self, analysis: MarketAnalysis) -> Optional[Dict]:
        """
        Toma una decisión basada en el análisis del mercado
        
        Args:
            analysis: Análisis del mercado
            
        Returns:
            Dict: Decisión tomada con reasoning
        """
        try:
            # Verificar confianza mínima
            if analysis.confidence < self.min_confidence:
                logger.debug(f"Confianza insuficiente: {analysis.confidence:.2f} < {self.min_confidence}")
                return None
            
            # Evaluar oportunidad
            if analysis.opportunity_score < self.opportunity_threshold:
                logger.debug(f"Oportunidad insuficiente: {analysis.opportunity_score:.2f}")
                return None
            
            # Generar opciones de decisión
            decision_options = await self._generate_decision_options(analysis)
            
            # Evaluar cada opción
            evaluated_options = []
            for option in decision_options:
                score = await self._evaluate_decision_option(option, analysis)
                evaluated_options.append((option, score))
            
            # Seleccionar mejor opción
            if not evaluated_options:
                return None
            
            best_option, best_score = max(evaluated_options, key=lambda x: x[1])
            
            # Generar reasoning
            reasoning = await self._generate_decision_reasoning(best_option, analysis, best_score)
            
            # Crear decisión final
            decision = {
                'action': best_option['action'],
                'confidence': analysis.confidence,
                'reasoning': reasoning,
                'expected_return': best_option.get('expected_return', 0.0),
                'risk_assessment': analysis.risk_level,
                'market_context': {
                    'regime': analysis.market_regime,
                    'trend': analysis.trend_direction,
                    'volatility': analysis.volatility_level
                },
                'timestamp': datetime.now(),
                'decision_id': f"DEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            # Guardar en historial
            self.decision_history.append(decision)
            
            logger.info(f"🎯 Decisión tomada: {decision['action']} (confianza: {decision['confidence']:.2f})")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error tomando decisión: {e}")
            return None
    
    async def _analyze_trend(self, klines: List[Dict]) -> Dict:
        """Analiza la tendencia del mercado"""
        try:
            closes = [float(k['close']) for k in klines[-50:]]
            
            # Análisis de tendencia a corto plazo (5 períodos)
            short_trend = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
            
            # Análisis de tendencia a medio plazo (20 períodos)
            medium_trend = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
            
            # Análisis de tendencia a largo plazo (50 períodos)
            long_trend = (closes[-1] - closes[0]) / closes[0] if len(closes) >= 50 else 0
            
            # Calcular fuerza de la tendencia
            trend_strength = abs(short_trend) + abs(medium_trend) + abs(long_trend)
            
            # Determinar dirección
            if short_trend > 0.01 and medium_trend > 0.01:
                direction = "bullish"
            elif short_trend < -0.01 and medium_trend < -0.01:
                direction = "bearish"
            else:
                direction = "sideways"
            
            return {
                'direction': direction,
                'strength': min(trend_strength, 1.0),
                'short_term': short_trend,
                'medium_term': medium_trend,
                'long_term': long_trend
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando tendencia: {e}")
            return {'direction': 'unknown', 'strength': 0.0}
    
    async def _analyze_volatility(self, klines: List[Dict]) -> Dict:
        """Analiza la volatilidad del mercado"""
        try:
            closes = [float(k['close']) for k in klines[-20:]]
            returns = np.diff(closes) / closes[:-1]
            
            # Volatilidad histórica
            historical_vol = np.std(returns)
            
            # Volatilidad reciente vs histórica
            recent_vol = np.std(returns[-5:]) if len(returns) >= 5 else historical_vol
            
            # Clasificar nivel de volatilidad
            if historical_vol > 0.05:  # 5%
                level = "high"
            elif historical_vol > 0.02:  # 2%
                level = "medium"
            else:
                level = "low"
            
            return {
                'level': level,
                'historical': historical_vol,
                'recent': recent_vol,
                'ratio': recent_vol / historical_vol if historical_vol > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando volatilidad: {e}")
            return {'level': 'unknown', 'historical': 0.0, 'recent': 0.0, 'ratio': 1.0}
    
    async def _analyze_volume(self, klines: List[Dict]) -> Dict:
        """Analiza el perfil de volumen"""
        try:
            volumes = [float(k['volume']) for k in klines[-20:]]
            avg_volume = np.mean(volumes)
            recent_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else avg_volume
            
            # Clasificar perfil de volumen
            if recent_volume > avg_volume * 1.5:
                profile = "high"
            elif recent_volume < avg_volume * 0.5:
                profile = "low"
            else:
                profile = "normal"
            
            return {
                'profile': profile,
                'average': avg_volume,
                'recent': recent_volume,
                'ratio': recent_volume / avg_volume if avg_volume > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando volumen: {e}")
            return {'profile': 'unknown', 'average': 0.0, 'recent': 0.0, 'ratio': 1.0}
    
    async def _analyze_technical_indicators(self, klines: List[Dict], features: np.ndarray) -> Dict:
        """Analiza indicadores técnicos"""
        try:
            closes = [float(k['close']) for k in klines[-20:]]
            
            # RSI
            rsi = self._calculate_rsi(closes)
            
            # MACD
            macd = self._calculate_macd(closes)
            
            # Bollinger Bands
            bb = self._calculate_bollinger_bands(closes)
            
            # Análisis de señales
            signals = {
                'rsi_oversold': rsi < 30,
                'rsi_overbought': rsi > 70,
                'macd_bullish': macd['macd'] > macd['signal'],
                'macd_bearish': macd['macd'] < macd['signal'],
                'bb_squeeze': bb['width'] < 0.1,
                'price_above_bb_upper': closes[-1] > bb['upper'],
                'price_below_bb_lower': closes[-1] < bb['lower']
            }
            
            return {
                'rsi': rsi,
                'macd': macd,
                'bollinger_bands': bb,
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando indicadores técnicos: {e}")
            return {}
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calcula RSI"""
        try:
            if len(closes) < period + 1:
                return 50.0
            
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except:
            return 50.0
    
    def _calculate_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calcula MACD"""
        try:
            if len(closes) < slow:
                return {'macd': 0, 'signal': 0, 'histogram': 0}
            
            # Calcular EMAs
            ema_fast = self._calculate_ema(closes, fast)
            ema_slow = self._calculate_ema(closes, slow)
            
            macd_line = ema_fast - ema_slow
            
            # Signal line (EMA del MACD)
            macd_values = [macd_line]  # Simplificado
            signal_line = self._calculate_ema(macd_values, signal)
            
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
    
    def _calculate_ema(self, values: List[float], period: int) -> float:
        """Calcula EMA"""
        try:
            if len(values) < period:
                return values[-1] if values else 0.0
            
            multiplier = 2 / (period + 1)
            ema = values[0]
            
            for value in values[1:]:
                ema = (value * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except:
            return values[-1] if values else 0.0
    
    def _calculate_bollinger_bands(self, closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        """Calcula Bollinger Bands"""
        try:
            if len(closes) < period:
                return {'upper': closes[-1], 'middle': closes[-1], 'lower': closes[-1], 'width': 0}
            
            recent_closes = closes[-period:]
            middle = np.mean(recent_closes)
            std = np.std(recent_closes)
            
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            width = (upper - lower) / middle
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'width': width
            }
            
        except:
            return {'upper': closes[-1], 'middle': closes[-1], 'lower': closes[-1], 'width': 0}
    
    async def _analyze_support_resistance(self, klines: List[Dict]) -> Dict:
        """Analiza niveles de soporte y resistencia"""
        try:
            highs = [float(k['high']) for k in klines[-50:]]
            lows = [float(k['low']) for k in klines[-50:]]
            closes = [float(k['close']) for k in klines[-50:]]
            
            current_price = closes[-1]
            
            # Encontrar niveles de soporte y resistencia
            resistance_levels = self._find_resistance_levels(highs)
            support_levels = self._find_support_levels(lows)
            
            # Calcular distancia a niveles clave
            nearest_resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.1)
            nearest_support = max([s for s in support_levels if s < current_price], default=current_price * 0.9)
            
            return {
                'resistance_levels': resistance_levels,
                'support_levels': support_levels,
                'nearest_resistance': nearest_resistance,
                'nearest_support': nearest_support,
                'resistance_distance': (nearest_resistance - current_price) / current_price,
                'support_distance': (current_price - nearest_support) / current_price
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando soporte/resistencia: {e}")
            return {}
    
    def _find_resistance_levels(self, highs: List[float]) -> List[float]:
        """Encuentra niveles de resistencia"""
        try:
            # Simplificado: encontrar máximos locales
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                    resistance_levels.append(highs[i])
            
            return sorted(set(resistance_levels))[-5:]  # Top 5 niveles
            
        except:
            return []
    
    def _find_support_levels(self, lows: List[float]) -> List[float]:
        """Encuentra niveles de soporte"""
        try:
            # Simplificado: encontrar mínimos locales
            support_levels = []
            for i in range(2, len(lows) - 2):
                if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                    support_levels.append(lows[i])
            
            return sorted(set(support_levels))[-5:]  # Top 5 niveles
            
        except:
            return []
    
    async def _detect_market_regime(self, klines: List[Dict], features: np.ndarray) -> str:
        """Detecta el régimen actual del mercado"""
        try:
            closes = [float(k['close']) for k in klines[-20:]]
            
            # Análisis de tendencia
            trend = (closes[-1] - closes[0]) / closes[0]
            
            # Análisis de volatilidad
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns)
            
            # Clasificar régimen
            if volatility > 0.05:  # Alta volatilidad
                return "volatile"
            elif trend > 0.02:  # Tendencia alcista
                return "bull"
            elif trend < -0.02:  # Tendencia bajista
                return "bear"
            else:
                return "sideways"
                
        except Exception as e:
            logger.error(f"❌ Error detectando régimen: {e}")
            return "unknown"
    
    async def _calculate_opportunity_score(self, trend_analysis: Dict, volatility_analysis: Dict, 
                                         technical_analysis: Dict, prediction: Dict) -> float:
        """Calcula el score de oportunidad"""
        try:
            score = 0.0
            
            # Factor de tendencia (40%)
            trend_score = 0.0
            if trend_analysis['direction'] == 'bullish':
                trend_score = trend_analysis['strength']
            elif trend_analysis['direction'] == 'bearish':
                trend_score = trend_analysis['strength']
            else:
                trend_score = 0.3  # Neutral
            
            score += trend_score * 0.4
            
            # Factor de volatilidad (20%)
            vol_score = 0.0
            if volatility_analysis['level'] == 'medium':
                vol_score = 0.8  # Volatilidad media es ideal
            elif volatility_analysis['level'] == 'high':
                vol_score = 0.6  # Alta volatilidad puede ser arriesgada
            else:
                vol_score = 0.4  # Baja volatilidad, menos oportunidad
            
            score += vol_score * 0.2
            
            # Factor de predicción ML (30%)
            ml_score = prediction.get('confidence', 0.5)
            score += ml_score * 0.3
            
            # Factor técnico (10%)
            tech_score = 0.5  # Simplificado
            if technical_analysis.get('signals', {}):
                signals = technical_analysis['signals']
                bullish_signals = sum([1 for s in signals.values() if s])
                tech_score = min(bullish_signals / len(signals), 1.0)
            
            score += tech_score * 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Error calculando oportunidad: {e}")
            return 0.0
    
    async def _assess_risk_level(self, volatility_analysis: Dict, market_regime: str, opportunity_score: float) -> str:
        """Evalúa el nivel de riesgo"""
        try:
            risk_score = 0.0
            
            # Factor de volatilidad
            if volatility_analysis['level'] == 'high':
                risk_score += 0.4
            elif volatility_analysis['level'] == 'medium':
                risk_score += 0.2
            
            # Factor de régimen
            if market_regime == 'volatile':
                risk_score += 0.3
            elif market_regime in ['bear', 'bull']:
                risk_score += 0.1
            
            # Factor de oportunidad (inversa)
            risk_score += (1.0 - opportunity_score) * 0.3
            
            # Clasificar riesgo
            if risk_score > 0.7:
                return "high"
            elif risk_score > 0.4:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"❌ Error evaluando riesgo: {e}")
            return "medium"
    
    async def _calculate_analysis_confidence(self, trend_analysis: Dict, technical_analysis: Dict, prediction: Dict) -> float:
        """Calcula la confianza del análisis"""
        try:
            confidence = 0.0
            
            # Confianza de tendencia
            trend_confidence = min(trend_analysis['strength'] * 2, 1.0)
            confidence += trend_confidence * 0.3
            
            # Confianza de predicción ML
            ml_confidence = prediction.get('confidence', 0.5)
            confidence += ml_confidence * 0.5
            
            # Confianza técnica
            tech_confidence = 0.5  # Simplificado
            confidence += tech_confidence * 0.2
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Error calculando confianza: {e}")
            return 0.5
    
    async def _generate_decision_options(self, analysis: MarketAnalysis) -> List[Dict]:
        """Genera opciones de decisión basadas en el análisis"""
        try:
            options = []
            
            # Opción HOLD (siempre disponible)
            options.append({
                'action': 'HOLD',
                'expected_return': 0.0,
                'risk_level': 'low',
                'reasoning': 'Mantener posición actual'
            })
            
            # Opciones basadas en análisis
            if analysis.trend_direction == 'bullish' and analysis.opportunity_score > 0.6:
                options.append({
                    'action': 'BUY',
                    'expected_return': analysis.opportunity_score * 0.05,  # 5% máximo
                    'risk_level': analysis.risk_level,
                    'reasoning': 'Tendencia alcista con buena oportunidad'
                })
            
            if analysis.trend_direction == 'bearish' and analysis.opportunity_score > 0.6:
                options.append({
                    'action': 'SELL',
                    'expected_return': analysis.opportunity_score * 0.05,
                    'risk_level': analysis.risk_level,
                    'reasoning': 'Tendencia bajista con buena oportunidad'
                })
            
            return options
            
        except Exception as e:
            logger.error(f"❌ Error generando opciones: {e}")
            return []
    
    async def _evaluate_decision_option(self, option: Dict, analysis: MarketAnalysis) -> float:
        """Evalúa una opción de decisión"""
        try:
            score = 0.0
            
            # Score base de la opción
            score += option.get('expected_return', 0.0) * 10  # Escalar return
            
            # Factor de confianza del análisis
            score += analysis.confidence * 5
            
            # Factor de oportunidad
            score += analysis.opportunity_score * 3
            
            # Penalización por riesgo
            risk_penalty = {
                'high': 0.3,
                'medium': 0.1,
                'low': 0.0
            }.get(analysis.risk_level, 0.1)
            
            score -= risk_penalty * 2
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"❌ Error evaluando opción: {e}")
            return 0.0
    
    async def _generate_decision_reasoning(self, option: Dict, analysis: MarketAnalysis, score: float) -> str:
        """Genera reasoning explicable para la decisión"""
        try:
            reasoning_parts = []
            
            # Reasoning de la acción
            reasoning_parts.append(f"Acción: {option['action']}")
            
            # Reasoning del análisis
            reasoning_parts.append(f"Tendencia: {analysis.trend_direction} (fuerza: {analysis.trend_strength:.2f})")
            reasoning_parts.append(f"Volatilidad: {analysis.volatility_level}")
            reasoning_parts.append(f"Régimen: {analysis.market_regime}")
            
            # Reasoning de oportunidad y riesgo
            reasoning_parts.append(f"Oportunidad: {analysis.opportunity_score:.2f}")
            reasoning_parts.append(f"Riesgo: {analysis.risk_level}")
            reasoning_parts.append(f"Confianza: {analysis.confidence:.2f}")
            
            # Reasoning del score
            reasoning_parts.append(f"Score de decisión: {score:.2f}")
            
            return " | ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Error generando reasoning: {e}")
            return f"Decisión: {option.get('action', 'UNKNOWN')}"
    
    async def _load_decision_parameters(self) -> None:
        """Carga parámetros de decisión desde configuración"""
        try:
            # Cargar pesos de factores
            factor_weights = self.decision_config.get('factor_weights', {})
            if factor_weights:
                self.factor_weights.update(factor_weights)
            
            # Cargar umbrales
            self.min_confidence = self.decision_config.get('min_confidence', self.min_confidence)
            self.risk_tolerance = self.decision_config.get('risk_tolerance', self.risk_tolerance)
            self.opportunity_threshold = self.decision_config.get('opportunity_threshold', self.opportunity_threshold)
            
            logger.info("📊 Parámetros de decisión cargados")
            
        except Exception as e:
            logger.error(f"❌ Error cargando parámetros: {e}")
    
    async def _initialize_analysis_models(self) -> None:
        """Inicializa modelos de análisis"""
        try:
            # TODO: Inicializar modelos específicos si es necesario
            logger.info("🔧 Modelos de análisis inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando modelos: {e}")
    
    def get_decision_statistics(self) -> Dict:
        """Obtiene estadísticas de decisiones"""
        try:
            if not self.decision_history:
                return {}
            
            total_decisions = len(self.decision_history)
            actions = [d['action'] for d in self.decision_history]
            
            action_counts = {}
            for action in actions:
                action_counts[action] = action_counts.get(action, 0) + 1
            
            avg_confidence = np.mean([d['confidence'] for d in self.decision_history])
            
            return {
                'total_decisions': total_decisions,
                'action_distribution': action_counts,
                'average_confidence': avg_confidence,
                'recent_decisions': self.decision_history[-10:]  # Últimas 10
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
