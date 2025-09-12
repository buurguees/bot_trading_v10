#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Agent - Bot Trading v10 Enterprise
==========================================
Agente de trading individual que opera un símbolo específico.
Cada agente mantiene su propia base de conocimiento y estrategias.

Características:
- Memoria de estrategias exitosas y fallidas
- Análisis técnico avanzado por timeframe
- Gestión de riesgo individual
- Registro detallado de decisiones
- Evolución de estrategias mediante ML

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)

class TradeAction(Enum):
    """Acciones de trading"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

class ConfidenceLevel(Enum):
    """Niveles de confianza"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

@dataclass
class TradingDecision:
    """Decisión de trading del agente"""
    timestamp: datetime
    action: TradeAction
    confidence: ConfidenceLevel
    price: float
    quantity: float
    timeframe: str
    strategy_used: str
    features_analyzed: Dict[str, float]
    reasoning: str
    expected_outcome: str
    risk_reward_ratio: float

@dataclass
class TradeResult:
    """Resultado de un trade ejecutado"""
    decision_id: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float
    pnl_pct: float
    duration_minutes: int
    was_successful: bool
    actual_outcome: str
    strategy_effectiveness: float

@dataclass
class Strategy:
    """Estrategia de trading"""
    id: str
    name: str
    description: str
    timeframes: List[str]
    indicators_used: List[str]
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    risk_parameters: Dict[str, float]
    success_rate: float
    avg_return: float
    max_drawdown: float
    total_trades: int
    last_used: datetime
    performance_score: float

class TradingAgent:
    """
    Agente de Trading Individual
    ===========================
    
    Cada agente opera un símbolo específico y mantiene su propia
    base de conocimiento, estrategias y memoria de decisiones.
    """
    
    def __init__(self, symbol: str, initial_balance: float = 1000.0):
        """
        Inicializa el agente de trading
        
        Args:
            symbol: Símbolo a operar (ej: BTCUSDT)
            initial_balance: Balance inicial
        """
        self.symbol = symbol
        self.agent_id = f"agent_{symbol}_{uuid.uuid4().hex[:8]}"
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        
        # Estado del agente
        self.is_active = True
        self.current_position = None
        self.open_orders = []
        
        # Memoria y aprendizaje
        self.strategy_library = {}
        self.decision_history = []
        self.trade_results = []
        self.feature_importance = {}
        
        # Configuración
        self.max_risk_per_trade = 0.02  # 2% máximo por trade
        self.max_daily_trades = 10
        self.confidence_threshold = ConfidenceLevel.MEDIUM
        
        # Métricas de rendimiento
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        
        # Directorio de datos del agente
        self.agent_dir = Path(f"data/agents/{self.symbol}")
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar estado previo si existe
        self._load_agent_state()
        
        logger.info(f"🤖 Agente {self.agent_id} inicializado para {symbol}")
    
    def _load_agent_state(self):
        """Carga estado previo del agente"""
        try:
            state_file = self.agent_dir / "agent_state.json"
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                # Restaurar estado básico
                self.current_balance = state.get('current_balance', self.initial_balance)
                self.peak_balance = state.get('peak_balance', self.initial_balance)
                self.total_trades = state.get('total_trades', 0)
                self.winning_trades = state.get('winning_trades', 0)
                self.losing_trades = state.get('losing_trades', 0)
                
                logger.info(f"📚 Estado del agente {self.symbol} cargado")
            
            # Cargar biblioteca de estrategias
            self._load_strategy_library()
            
        except Exception as e:
            logger.error(f"❌ Error cargando estado del agente {self.symbol}: {e}")
    
    def _load_strategy_library(self):
        """Carga biblioteca de estrategias"""
        try:
            strategies_file = self.agent_dir / "strategies.json"
            
            if strategies_file.exists():
                with open(strategies_file, 'r') as f:
                    strategies_data = json.load(f)
                
                for strategy_data in strategies_data.get('strategies', []):
                    strategy = Strategy(**strategy_data)
                    self.strategy_library[strategy.id] = strategy
                
                logger.info(f"📋 {len(self.strategy_library)} estrategias cargadas para {self.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando estrategias de {self.symbol}: {e}")
    
    async def analyze_market(self, market_data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """
        Analiza el mercado y genera features técnicos
        
        Args:
            market_data: Datos OHLCV
            timeframe: Timeframe analizado
            
        Returns:
            Diccionario con análisis técnico
        """
        try:
            if market_data.empty or len(market_data) < 20:
                return {"status": "insufficient_data"}
            
            features = {}
            
            # Indicadores técnicos básicos
            features.update(self._calculate_trend_indicators(market_data))
            features.update(self._calculate_momentum_indicators(market_data))
            features.update(self._calculate_volatility_indicators(market_data))
            features.update(self._calculate_volume_indicators(market_data))
            
            # Análisis de patrones
            features.update(self._analyze_patterns(market_data))
            
            # Análisis de soporte/resistencia
            features.update(self._analyze_support_resistance(market_data))
            
            # Score de confluencia
            features['confluence_score'] = self._calculate_confluence_score(features)
            
            # Timestamp del análisis
            features['analysis_timestamp'] = datetime.now().isoformat()
            features['timeframe'] = timeframe
            features['symbol'] = self.symbol
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error analizando mercado para {self.symbol}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores de tendencia"""
        try:
            features = {}
            
            # Medias móviles
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # Posición del precio respecto a medias
            current_price = df['close'].iloc[-1]
            features['price_vs_sma20'] = (current_price / df['sma_20'].iloc[-1] - 1) * 100
            features['price_vs_sma50'] = (current_price / df['sma_50'].iloc[-1] - 1) * 100
            
            # MACD
            macd = df['ema_12'] - df['ema_26']
            signal = macd.ewm(span=9).mean()
            features['macd'] = macd.iloc[-1]
            features['macd_signal'] = signal.iloc[-1]
            features['macd_histogram'] = (macd - signal).iloc[-1]
            
            # Tendencia (pendiente de SMA20)
            if len(df) >= 5:
                sma20_slope = (df['sma_20'].iloc[-1] - df['sma_20'].iloc[-5]) / 5
                features['trend_strength'] = sma20_slope / current_price * 10000  # En basis points
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores de tendencia: {e}")
            return {}
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores de momentum"""
        try:
            features = {}
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = 100 - (100 / (1 + rs.iloc[-1]))
            
            # Stochastic
            lowest_low = df['low'].rolling(window=14).min()
            highest_high = df['high'].rolling(window=14).max()
            k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            features['stoch_k'] = k_percent.iloc[-1]
            features['stoch_d'] = k_percent.rolling(3).mean().iloc[-1]
            
            # Williams %R
            features['williams_r'] = -100 * ((highest_high.iloc[-1] - df['close'].iloc[-1]) / 
                                            (highest_high.iloc[-1] - lowest_low.iloc[-1]))
            
            # Rate of Change
            if len(df) >= 10:
                features['roc_10'] = ((df['close'].iloc[-1] / df['close'].iloc[-10]) - 1) * 100
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores de momentum: {e}")
            return {}
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores de volatilidad"""
        try:
            features = {}
            
            # Bollinger Bands
            sma20 = df['close'].rolling(20).mean()
            std20 = df['close'].rolling(20).std()
            bb_upper = sma20 + (std20 * 2)
            bb_lower = sma20 - (std20 * 2)
            
            current_price = df['close'].iloc[-1]
            features['bb_position'] = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
            features['bb_width'] = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / sma20.iloc[-1] * 100
            
            # Average True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            features['atr'] = true_range.rolling(14).mean().iloc[-1]
            features['atr_pct'] = (features['atr'] / current_price) * 100
            
            # Volatilidad histórica
            returns = df['close'].pct_change().dropna()
            features['volatility_20d'] = returns.rolling(20).std().iloc[-1] * np.sqrt(365) * 100
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores de volatilidad: {e}")
            return {}
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores de volumen"""
        try:
            features = {}
            
            # Volume Moving Average
            vma20 = df['volume'].rolling(20).mean()
            features['volume_ratio'] = df['volume'].iloc[-1] / vma20.iloc[-1]
            
            # On Balance Volume
            obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
            features['obv_slope'] = (obv.iloc[-1] - obv.iloc[-5]) / 5 if len(obv) >= 5 else 0
            
            # Volume Price Trend
            vpt = ((df['close'].diff() / df['close'].shift()) * df['volume']).fillna(0).cumsum()
            features['vpt'] = vpt.iloc[-1]
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores de volumen: {e}")
            return {}
    
    def _analyze_patterns(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analiza patrones de precio"""
        try:
            features = {}
            
            if len(df) < 10:
                return features
            
            # Patrones de velas
            recent_candles = df.tail(5)
            
            # Doji pattern
            doji_threshold = 0.001
            body_size = abs(recent_candles['close'] - recent_candles['open']) / recent_candles['close']
            features['doji_count'] = (body_size < doji_threshold).sum()
            
            # Hammer/Shooting star
            upper_shadow = recent_candles['high'] - np.maximum(recent_candles['open'], recent_candles['close'])
            lower_shadow = np.minimum(recent_candles['open'], recent_candles['close']) - recent_candles['low']
            body = abs(recent_candles['close'] - recent_candles['open'])
            
            hammer_pattern = (lower_shadow > 2 * body) & (upper_shadow < 0.5 * body)
            features['hammer_count'] = hammer_pattern.sum()
            
            # Consecutive candles
            consecutive_green = 0
            consecutive_red = 0
            for i in range(len(recent_candles)):
                if recent_candles['close'].iloc[i] > recent_candles['open'].iloc[i]:
                    consecutive_green += 1
                    consecutive_red = 0
                else:
                    consecutive_red += 1
                    consecutive_green = 0
            
            features['consecutive_green'] = consecutive_green
            features['consecutive_red'] = consecutive_red
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error analizando patrones: {e}")
            return {}
    
    def _analyze_support_resistance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analiza niveles de soporte y resistencia"""
        try:
            features = {}
            
            if len(df) < 50:
                return features
            
            # Pivots simples
            recent_data = df.tail(50)
            highs = recent_data['high']
            lows = recent_data['low']
            current_price = df['close'].iloc[-1]
            
            # Resistencias (máximos locales)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Soportes (mínimos locales)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            # Distancia a niveles clave
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))
                features['resistance_distance'] = (nearest_resistance - current_price) / current_price * 100
            
            if support_levels:
                nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
                features['support_distance'] = (current_price - nearest_support) / current_price * 100
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error analizando soporte/resistencia: {e}")
            return {}
    
    def _calculate_confluence_score(self, features: Dict[str, float]) -> float:
        """Calcula score de confluencia basado en múltiples señales"""
        try:
            score = 0.0
            max_score = 0.0
            
            # RSI confluence
            rsi = features.get('rsi', 50)
            if rsi < 30:
                score += 2  # Oversold
            elif rsi > 70:
                score -= 2  # Overbought
            max_score += 2
            
            # MACD confluence
            macd = features.get('macd', 0)
            macd_signal = features.get('macd_signal', 0)
            if macd > macd_signal:
                score += 1
            else:
                score -= 1
            max_score += 1
            
            # Bollinger Bands confluence
            bb_position = features.get('bb_position', 0.5)
            if bb_position < 0.2:
                score += 1  # Near lower band
            elif bb_position > 0.8:
                score -= 1  # Near upper band
            max_score += 1
            
            # Volume confluence
            volume_ratio = features.get('volume_ratio', 1)
            if volume_ratio > 1.5:
                score += 1  # High volume
            max_score += 1
            
            # Trend confluence
            trend_strength = features.get('trend_strength', 0)
            if abs(trend_strength) > 5:
                score += 1 if trend_strength > 0 else -1
            max_score += 1
            
            # Normalizar score (-1 a 1)
            confluence_score = score / max_score if max_score > 0 else 0
            return confluence_score
            
        except Exception as e:
            logger.error(f"❌ Error calculando confluence score: {e}")
            return 0.0
    
    async def make_trading_decision(self, market_data: pd.DataFrame, timeframe: str) -> Optional[TradingDecision]:
        """
        Toma decisión de trading basada en análisis
        
        Args:
            market_data: Datos de mercado
            timeframe: Timeframe analizado
            
        Returns:
            Decisión de trading o None
        """
        try:
            # Análisis técnico
            features = await self.analyze_market(market_data, timeframe)
            
            if features.get('status') == 'error':
                return None
            
            # Buscar estrategia aplicable
            applicable_strategy = self._find_best_strategy(features, timeframe)
            
            if not applicable_strategy:
                return None
            
            # Evaluar condiciones de entrada
            action, confidence = self._evaluate_entry_conditions(features, applicable_strategy)
            
            if action == TradeAction.HOLD or confidence.value < self.confidence_threshold.value:
                return None
            
            # Calcular tamaño de posición y riesgo
            current_price = market_data['close'].iloc[-1]
            position_size = self._calculate_position_size(current_price, features)
            risk_reward = self._calculate_risk_reward(features, applicable_strategy)
            
            # Crear decisión
            decision = TradingDecision(
                timestamp=datetime.now(),
                action=action,
                confidence=confidence,
                price=current_price,
                quantity=position_size,
                timeframe=timeframe,
                strategy_used=applicable_strategy.name,
                features_analyzed=features,
                reasoning=self._generate_reasoning(features, applicable_strategy),
                expected_outcome=self._predict_outcome(features, applicable_strategy),
                risk_reward_ratio=risk_reward
            )
            
            # Guardar decisión en historial
            self.decision_history.append(decision)
            
            # Actualizar uso de estrategia
            applicable_strategy.last_used = datetime.now()
            
            logger.info(f"🎯 Decisión de trading para {self.symbol}: {action.value} con confianza {confidence.name}")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error tomando decisión de trading para {self.symbol}: {e}")
            return None
    
    def _find_best_strategy(self, features: Dict[str, float], timeframe: str) -> Optional[Strategy]:
        """Encuentra la mejor estrategia aplicable"""
        try:
            applicable_strategies = []
            
            for strategy in self.strategy_library.values():
                if timeframe in strategy.timeframes:
                    # Verificar si las condiciones de la estrategia se cumplen
                    if self._strategy_conditions_met(features, strategy):
                        applicable_strategies.append(strategy)
            
            if not applicable_strategies:
                return None
            
            # Ordenar por performance score
            applicable_strategies.sort(key=lambda s: s.performance_score, reverse=True)
            
            return applicable_strategies[0]
            
        except Exception as e:
            logger.error(f"❌ Error encontrando estrategia: {e}")
            return None
    
    def _strategy_conditions_met(self, features: Dict[str, float], strategy: Strategy) -> bool:
        """Verifica si se cumplen las condiciones de una estrategia"""
        try:
            entry_conditions = strategy.entry_conditions
            
            for condition, threshold in entry_conditions.items():
                feature_value = features.get(condition)
                
                if feature_value is None:
                    continue
                
                # Evaluar condición (esto es simplificado, en realidad sería más complejo)
                if isinstance(threshold, dict):
                    min_val = threshold.get('min', float('-inf'))
                    max_val = threshold.get('max', float('inf'))
                    if not (min_val <= feature_value <= max_val):
                        return False
                elif isinstance(threshold, (int, float)):
                    if abs(feature_value - threshold) > abs(threshold * 0.1):  # 10% tolerance
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error evaluando condiciones de estrategia: {e}")
            return False
    
    def _evaluate_entry_conditions(self, features: Dict[str, float], strategy: Strategy) -> Tuple[TradeAction, ConfidenceLevel]:
        """Evalúa condiciones de entrada y determina acción"""
        try:
            confluence_score = features.get('confluence_score', 0)
            
            # Determinar acción basada en confluence score
            if confluence_score > 0.6:
                action = TradeAction.BUY
                confidence = ConfidenceLevel.HIGH if confluence_score > 0.8 else ConfidenceLevel.MEDIUM
            elif confluence_score < -0.6:
                action = TradeAction.SELL
                confidence = ConfidenceLevel.HIGH if confluence_score < -0.8 else ConfidenceLevel.MEDIUM
            else:
                action = TradeAction.HOLD
                confidence = ConfidenceLevel.LOW
            
            # Ajustar confianza basada en performance de estrategia
            if strategy.success_rate > 0.7:
                confidence = ConfidenceLevel(min(confidence.value + 1, 5))
            elif strategy.success_rate < 0.4:
                confidence = ConfidenceLevel(max(confidence.value - 1, 1))
            
            return action, confidence
            
        except Exception as e:
            logger.error(f"❌ Error evaluando condiciones de entrada: {e}")
            return TradeAction.HOLD, ConfidenceLevel.VERY_LOW
    
    def _calculate_position_size(self, price: float, features: Dict[str, float]) -> float:
        """Calcula tamaño de posición basado en riesgo"""
        try:
            # Risk per trade
            risk_amount = self.current_balance * self.max_risk_per_trade
            
            # ATR para stop loss
            atr = features.get('atr', price * 0.02)  # Fallback: 2% del precio
            stop_distance = atr * 2  # 2 ATR como stop loss
            
            # Position size
            position_size = risk_amount / stop_distance
            
            # Limitar tamaño máximo (ej: 50% del balance)
            max_position_value = self.current_balance * 0.5
            max_quantity = max_position_value / price
            
            return min(position_size, max_quantity)
            
        except Exception as e:
            logger.error(f"❌ Error calculando tamaño de posición: {e}")
            return 0.0
    
    def _calculate_risk_reward(self, features: Dict[str, float], strategy: Strategy) -> float:
        """Calcula ratio riesgo/recompensa"""
        try:
            atr = features.get('atr', 0)
            
            if atr == 0:
                return 1.0
            
            # Stop loss: 2 ATR
            risk = atr * 2
            
            # Target: basado en resistencia o 3 ATR
            resistance_distance = features.get('resistance_distance', 3.0)
            target = max(atr * 3, abs(resistance_distance))
            
            risk_reward = target / risk if risk > 0 else 1.0
            
            return risk_reward
            
        except Exception as e:
            logger.error(f"❌ Error calculando risk/reward: {e}")
            return 1.0
    
    def _generate_reasoning(self, features: Dict[str, float], strategy: Strategy) -> str:
        """Genera razonamiento para la decisión"""
        try:
            reasoning_parts = []
            
            # Confluence score
            confluence = features.get('confluence_score', 0)
            if confluence > 0.5:
                reasoning_parts.append(f"Confluencia bullish fuerte ({confluence:.2f})")
            elif confluence < -0.5:
                reasoning_parts.append(f"Confluencia bearish fuerte ({confluence:.2f})")
            
            # RSI
            rsi = features.get('rsi', 50)
            if rsi < 30:
                reasoning_parts.append("RSI en sobreventa")
            elif rsi > 70:
                reasoning_parts.append("RSI en sobrecompra")
            
            # Estrategia utilizada
            reasoning_parts.append(f"Estrategia '{strategy.name}' con {strategy.success_rate:.1%} éxito")
            
            return "; ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Error generando razonamiento: {e}")
            return "Análisis técnico estándar"
    
    def _predict_outcome(self, features: Dict[str, float], strategy: Strategy) -> str:
        """Predice resultado esperado"""
        try:
            avg_return = strategy.avg_return
            confidence = features.get('confluence_score', 0)
            
            expected_return = avg_return * (1 + abs(confidence))
            
            if expected_return > 0:
                return f"Ganancia esperada: {expected_return:.2%}"
            else:
                return f"Pérdida esperada: {expected_return:.2%}"
            
        except Exception as e:
            logger.error(f"❌ Error prediciendo resultado: {e}")
            return "Resultado incierto"
    
    async def record_trade_result(self, decision_id: str, exit_price: float, exit_time: datetime):
        """Registra resultado de un trade"""
        try:
            # Buscar decisión original
            decision = None
            for d in self.decision_history:
                if hasattr(d, 'id') and d.id == decision_id:
                    decision = d
                    break
            
            if not decision:
                logger.error(f"❌ Decisión {decision_id} no encontrada")
                return
            
            # Calcular resultado
            if decision.action == TradeAction.BUY:
                pnl = (exit_price - decision.price) * decision.quantity
            else:  # SELL
                pnl = (decision.price - exit_price) * decision.quantity
            
            pnl_pct = (pnl / (decision.price * decision.quantity)) * 100
            duration = (exit_time - decision.timestamp).total_seconds() / 60
            
            # Crear resultado
            result = TradeResult(
                decision_id=decision_id,
                entry_time=decision.timestamp,
                exit_time=exit_time,
                entry_price=decision.price,
                exit_price=exit_price,
                quantity=decision.quantity,
                pnl=pnl,
                pnl_pct=pnl_pct,
                duration_minutes=duration,
                was_successful=pnl > 0,
                actual_outcome=f"{'Ganancia' if pnl > 0 else 'Pérdida'}: {pnl_pct:.2f}%",
                strategy_effectiveness=self._calculate_strategy_effectiveness(decision, pnl_pct)
            )
            
            # Actualizar métricas del agente
            self._update_agent_metrics(result)
            
            # Guardar resultado
            self.trade_results.append(result)
            
            # Actualizar performance de estrategia
            self._update_strategy_performance(decision.strategy_used, result.was_successful, pnl_pct)
            
            logger.info(f"📊 Trade resultado registrado para {self.symbol}: {pnl_pct:.2f}%")
            
        except Exception as e:
            logger.error(f"❌ Error registrando resultado de trade: {e}")
    
    def _calculate_strategy_effectiveness(self, decision: TradingDecision, actual_pnl: float) -> float:
        """Calcula efectividad de la estrategia utilizada"""
        try:
            # Comparar resultado real vs expectativa
            expected_direction = 1 if "Ganancia" in decision.expected_outcome else -1
            actual_direction = 1 if actual_pnl > 0 else -1
            
            direction_accuracy = 1.0 if expected_direction == actual_direction else 0.0
            
            # Factor de confianza
            confidence_factor = decision.confidence.value / 5.0
            
            effectiveness = (direction_accuracy * 0.7) + (confidence_factor * 0.3)
            
            return effectiveness
            
        except Exception as e:
            logger.error(f"❌ Error calculando efectividad de estrategia: {e}")
            return 0.5
    
    def _update_agent_metrics(self, result: TradeResult):
        """Actualiza métricas del agente"""
        try:
            # Actualizar balance
            self.current_balance += result.pnl
            
            # Actualizar peak y drawdown
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
                self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
            
            # Actualizar contadores
            self.total_trades += 1
            if result.was_successful:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # PnL diario
            self.daily_pnl += result.pnl
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas del agente: {e}")
    
    def _update_strategy_performance(self, strategy_name: str, was_successful: bool, pnl_pct: float):
        """Actualiza performance de una estrategia"""
        try:
            for strategy in self.strategy_library.values():
                if strategy.name == strategy_name:
                    strategy.total_trades += 1
                    
                    # Actualizar success rate
                    if was_successful:
                        strategy.success_rate = ((strategy.success_rate * (strategy.total_trades - 1)) + 1) / strategy.total_trades
                    else:
                        strategy.success_rate = (strategy.success_rate * (strategy.total_trades - 1)) / strategy.total_trades
                    
                    # Actualizar return promedio
                    strategy.avg_return = ((strategy.avg_return * (strategy.total_trades - 1)) + pnl_pct) / strategy.total_trades
                    
                    # Recalcular performance score
                    strategy.performance_score = (strategy.success_rate * 0.6) + (strategy.avg_return * 0.4)
                    
                    break
            
        except Exception as e:
            logger.error(f"❌ Error actualizando performance de estrategia: {e}")
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas actuales del agente"""
        try:
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            return {
                "agent_id": self.agent_id,
                "symbol": self.symbol,
                "current_balance": self.current_balance,
                "initial_balance": self.initial_balance,
                "total_pnl": self.current_balance - self.initial_balance,
                "total_pnl_pct": ((self.current_balance / self.initial_balance) - 1) * 100,
                "daily_pnl": self.daily_pnl,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": win_rate,
                "current_drawdown": self.current_drawdown * 100,
                "max_drawdown": self.max_drawdown * 100,
                "strategies_count": len(self.strategy_library),
                "last_decision": self.decision_history[-1].timestamp.isoformat() if self.decision_history else None,
                "is_active": self.is_active
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas del agente: {e}")
            return {}
    
    async def save_agent_state(self):
        """Guarda estado del agente"""
        try:
            # Estado básico
            state = {
                "agent_id": self.agent_id,
                "symbol": self.symbol,
                "current_balance": self.current_balance,
                "peak_balance": self.peak_balance,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "max_drawdown": self.max_drawdown,
                "last_saved": datetime.now().isoformat()
            }
            
            state_file = self.agent_dir / "agent_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Guardar estrategias
            strategies_data = {
                "strategies": [asdict(strategy) for strategy in self.strategy_library.values()],
                "last_updated": datetime.now().isoformat()
            }
            
            strategies_file = self.agent_dir / "strategies.json"
            with open(strategies_file, 'w') as f:
                json.dump(strategies_data, f, indent=2, default=str)
            
            # Guardar historial de trades recientes (últimos 1000)
            recent_results = self.trade_results[-1000:] if len(self.trade_results) > 1000 else self.trade_results
            results_data = {
                "results": [asdict(result) for result in recent_results],
                "total_results": len(self.trade_results),
                "last_updated": datetime.now().isoformat()
            }
            
            results_file = self.agent_dir / "trade_results.json"
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            logger.info(f"💾 Estado del agente {self.symbol} guardado")
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado del agente: {e}")
    
    async def cleanup(self):
        """Limpia recursos del agente"""
        try:
            await self.save_agent_state()
            self.is_active = False
            
            logger.info(f"🧹 Agente {self.symbol} limpiado")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando agente: {e}")

# Factory function
def create_trading_agent(symbol: str, initial_balance: float = 1000.0) -> TradingAgent:
    """Crea una instancia de TradingAgent"""
    return TradingAgent(symbol, initial_balance)