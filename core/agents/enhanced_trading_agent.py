#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/agents/enhanced_trading_agent.py
=====================================
Trading Agent Mejorado con Tracking Detallado

Versión mejorada del TradingAgent con tracking granular de trades,
métricas detalladas por estrategia, estado persistente y análisis
de confluence avanzado.

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

from .trading_agent import TradingAgent, TradeAction, ConfidenceLevel, Strategy, TradingDecision, TradeResult
from ..metrics.trade_metrics import DetailedTradeMetric, MarketRegime, ExitReason

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Estado persistente del agente"""
    symbol: str
    current_balance: float
    peak_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    current_drawdown: float
    max_drawdown: float
    daily_pnl: float
    last_reset: datetime
    strategy_performance: Dict[str, Dict[str, Any]]
    feature_importance: Dict[str, float]
    market_regime_history: List[str]
    quality_scores_history: List[float]

@dataclass
class StrategyMetrics:
    """Métricas detalladas por estrategia"""
    strategy_name: str
    total_trades: int
    winning_trades: int
    total_pnl: float
    avg_pnl: float
    win_rate: float
    avg_duration: float
    avg_quality_score: float
    best_trade: float
    worst_trade: float
    max_drawdown: float
    sharpe_ratio: float
    last_used: datetime
    performance_trend: str  # "IMPROVING", "DECLINING", "STABLE"

class EnhancedTradingAgent(TradingAgent):
    """
    Agente de Trading Mejorado con Tracking Detallado
    =================================================
    
    Extiende el TradingAgent base con capacidades avanzadas:
    - Tracking granular de cada trade individual
    - Métricas detalladas por estrategia
    - Estado persistente entre ciclos
    - Análisis de confluence mejorado
    - Gestión de memoria optimizada
    """
    
    def __init__(self, symbol: str, initial_balance: float = 1000.0):
        """
        Inicializa el agente mejorado
        
        Args:
            symbol: Símbolo a operar
            initial_balance: Balance inicial
        """
        super().__init__(symbol, initial_balance)
        
        # Estado persistente mejorado
        self.agent_state = AgentState(
            symbol=symbol,
            current_balance=initial_balance,
            peak_balance=initial_balance,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            current_drawdown=0.0,
            max_drawdown=0.0,
            daily_pnl=0.0,
            last_reset=datetime.now(),
            strategy_performance={},
            feature_importance={},
            market_regime_history=[],
            quality_scores_history=[]
        )
        
        # Tracking detallado de trades
        self.detailed_trades: List[DetailedTradeMetric] = []
        self.trade_metrics_by_strategy: Dict[str, List[DetailedTradeMetric]] = {}
        
        # Análisis de confluence mejorado
        self.confluence_weights = {
            'technical_indicators': 0.3,
            'market_regime': 0.2,
            'volume_confirmation': 0.15,
            'timeframe_alignment': 0.15,
            'risk_reward_ratio': 0.1,
            'volatility_environment': 0.1
        }
        
        # Configuración de persistencia
        self.state_file = self.agent_dir / "agent_state.json"
        self.trades_file = self.agent_dir / "detailed_trades.json"
        
        # Cargar estado previo
        self._load_persistent_state()
        
        logger.info(f"🤖 EnhancedTradingAgent {self.agent_id} inicializado para {symbol}")
    
    async def execute_trade_with_tracking(
        self, 
        decision: TradingDecision, 
        market_data: pd.DataFrame,
        cycle_id: int
    ) -> Optional[DetailedTradeMetric]:
        """
        Ejecuta trade con tracking detallado completo
        
        Args:
            decision: Decisión de trading
            market_data: Datos de mercado
            cycle_id: ID del ciclo actual
            
        Returns:
            DetailedTradeMetric: Métrica detallada del trade
        """
        try:
            # Simular ejecución del trade (en sistema real sería ejecución real)
            trade_result = await self._simulate_trade_execution(decision, market_data)
            
            if not trade_result:
                return None
            
            # Crear métrica detallada
            detailed_metric = await self._create_detailed_trade_metric(
                decision, trade_result, market_data, cycle_id
            )
            
            # Guardar trade detallado
            self.detailed_trades.append(detailed_metric)
            
            # Actualizar métricas por estrategia
            strategy_name = decision.strategy_used
            if strategy_name not in self.trade_metrics_by_strategy:
                self.trade_metrics_by_strategy[strategy_name] = []
            self.trade_metrics_by_strategy[strategy_name].append(detailed_metric)
            
            # Actualizar estado del agente
            await self._update_agent_state(detailed_metric)
            
            # Guardar estado persistente
            await self._save_persistent_state()
            
            logger.info(f"✅ Trade ejecutado y trackeado: {self.symbol} {decision.action.value} {detailed_metric.pnl_usdt:+.2f} USDT")
            
            return detailed_metric
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trade con tracking: {e}")
            return None
    
    async def _simulate_trade_execution(
        self, 
        decision: TradingDecision, 
        market_data: pd.DataFrame
    ) -> Optional[TradeResult]:
        """Simula ejecución del trade"""
        try:
            # Lógica de simulación simplificada
            entry_price = decision.price
            quantity = decision.quantity
            
            # Simular precio de salida basado en acción
            if decision.action in [TradeAction.BUY, TradeAction.CLOSE_SHORT]:
                # Simular trade LONG
                price_change_pct = np.random.normal(0.02, 0.01)  # +2% promedio, 1% std
                exit_price = entry_price * (1 + price_change_pct)
                pnl = (exit_price - entry_price) * quantity
            else:
                # Simular trade SHORT
                price_change_pct = np.random.normal(-0.02, 0.01)  # -2% promedio, 1% std
                exit_price = entry_price * (1 + price_change_pct)
                pnl = (entry_price - exit_price) * quantity
            
            # Determinar razón de salida
            if pnl > 0:
                exit_reason = "TAKE_PROFIT" if pnl > entry_price * 0.02 else "STRATEGY_SIGNAL"
            else:
                exit_reason = "STOP_LOSS" if pnl < -entry_price * 0.01 else "STRATEGY_SIGNAL"
            
            # Calcular duración (simulada)
            duration_hours = np.random.uniform(0.5, 24.0)  # Entre 30 min y 24h
            
            return TradeResult(
                trade_id=str(uuid.uuid4()),
                symbol=self.symbol,
                action=decision.action,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                pnl=pnl,
                entry_time=decision.timestamp,
                exit_time=decision.timestamp + timedelta(hours=duration_hours),
                duration_hours=duration_hours,
                exit_reason=exit_reason,
                strategy_used=decision.strategy_used,
                was_successful=pnl > 0,
                follow_plan=True,
                strategy_effectiveness=0.8  # Simulado
            )
            
        except Exception as e:
            logger.error(f"❌ Error simulando ejecución: {e}")
            return None
    
    async def _create_detailed_trade_metric(
        self, 
        decision: TradingDecision, 
        trade_result: TradeResult, 
        market_data: pd.DataFrame,
        cycle_id: int
    ) -> DetailedTradeMetric:
        """Crea métrica detallada del trade"""
        try:
            # Análisis técnico detallado
            technical_analysis = await self._analyze_technical_context(market_data, decision)
            
            # Contexto de mercado
            market_context = await self._analyze_market_context(market_data, decision)
            
            # Datos del trade
            trade_data = {
                'action': decision.action.value,
                'entry_price': trade_result.entry_price,
                'exit_price': trade_result.exit_price,
                'quantity': trade_result.quantity,
                'leverage': 1.0,  # Simulado
                'entry_time': trade_result.entry_time,
                'exit_time': trade_result.exit_time,
                'duration_candles': int(trade_result.duration_hours * 12),  # Asumiendo 5m candles
                'balance_before': self.agent_state.current_balance,
                'follow_plan': trade_result.follow_plan,
                'exit_reason': trade_result.exit_reason,
                'slippage': 0.0,  # Simulado
                'commission': trade_result.pnl * 0.001,  # 0.1% comisión
                'timeframe': decision.timeframe
            }
            
            # Crear métrica detallada
            detailed_metric = DetailedTradeMetric.create_from_trade_data(
                trade_data=trade_data,
                agent_symbol=self.symbol,
                cycle_id=cycle_id,
                technical_analysis=technical_analysis,
                market_context=market_context
            )
            
            return detailed_metric
            
        except Exception as e:
            logger.error(f"❌ Error creando métrica detallada: {e}")
            # Crear métrica básica en caso de error
            return DetailedTradeMetric.create_from_trade_data(
                trade_data={
                    'action': decision.action.value,
                    'entry_price': trade_result.entry_price,
                    'exit_price': trade_result.exit_price,
                    'quantity': trade_result.quantity,
                    'leverage': 1.0,
                    'entry_time': trade_result.entry_time,
                    'exit_time': trade_result.exit_time,
                    'duration_candles': 1,
                    'balance_before': self.agent_state.current_balance,
                    'follow_plan': True,
                    'exit_reason': trade_result.exit_reason,
                    'slippage': 0.0,
                    'commission': 0.0,
                    'timeframe': decision.timeframe
                },
                agent_symbol=self.symbol,
                cycle_id=cycle_id,
                technical_analysis={'confidence_level': 'MEDIUM', 'strategy_name': decision.strategy_used},
                market_context={'market_regime': 'SIDEWAYS', 'volatility_level': 0.02}
            )
    
    async def _analyze_technical_context(
        self, 
        market_data: pd.DataFrame, 
        decision: TradingDecision
    ) -> Dict[str, Any]:
        """Analiza contexto técnico detallado"""
        try:
            if market_data.empty:
                return {
                    'confidence_level': 'LOW',
                    'strategy_name': decision.strategy_used,
                    'confluence_score': 0.5,
                    'risk_reward_ratio': 1.0,
                    'indicators': {},
                    'support_resistance': {},
                    'trend_strength': 0.0,
                    'momentum_score': 0.0
                }
            
            # Calcular indicadores técnicos básicos
            current_price = market_data['close'].iloc[-1]
            sma_20 = market_data['close'].rolling(20).mean().iloc[-1]
            rsi = self._calculate_rsi(market_data['close'])
            macd = self._calculate_macd(market_data['close'])
            
            # Análisis de tendencia
            trend_strength = abs(current_price - sma_20) / sma_20 if not pd.isna(sma_20) else 0.0
            
            # Análisis de momentum
            momentum_score = (current_price - market_data['close'].iloc[-5]) / market_data['close'].iloc[-5] if len(market_data) >= 5 else 0.0
            
            # Calcular confluence score
            confluence_score = self._calculate_confluence_score({
                'rsi': rsi,
                'macd': macd,
                'trend_strength': trend_strength,
                'momentum': momentum_score
            })
            
            # Determinar nivel de confianza
            if confluence_score >= 0.8:
                confidence_level = 'VERY_HIGH'
            elif confluence_score >= 0.6:
                confidence_level = 'HIGH'
            elif confluence_score >= 0.4:
                confidence_level = 'MEDIUM'
            else:
                confidence_level = 'LOW'
            
            return {
                'confidence_level': confidence_level,
                'strategy_name': decision.strategy_used,
                'confluence_score': confluence_score,
                'risk_reward_ratio': decision.risk_reward_ratio,
                'indicators': {
                    'rsi': rsi,
                    'macd': macd,
                    'sma_20': sma_20
                },
                'support_resistance': {
                    'support': market_data['low'].rolling(20).min().iloc[-1],
                    'resistance': market_data['high'].rolling(20).max().iloc[-1]
                },
                'trend_strength': trend_strength,
                'momentum_score': momentum_score
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando contexto técnico: {e}")
            return {
                'confidence_level': 'LOW',
                'strategy_name': decision.strategy_used,
                'confluence_score': 0.3,
                'risk_reward_ratio': 1.0,
                'indicators': {},
                'support_resistance': {},
                'trend_strength': 0.0,
                'momentum_score': 0.0
            }
    
    async def _analyze_market_context(
        self, 
        market_data: pd.DataFrame, 
        decision: TradingDecision
    ) -> Dict[str, Any]:
        """Analiza contexto de mercado"""
        try:
            if market_data.empty:
                return {
                    'market_regime': 'SIDEWAYS',
                    'volatility_level': 0.02,
                    'volume_confirmation': False,
                    'market_session': 'UNKNOWN',
                    'news_impact': None
                }
            
            # Análisis de volatilidad
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Volatilidad diaria
            
            # Análisis de volumen
            avg_volume = market_data['volume'].rolling(20).mean().iloc[-1]
            current_volume = market_data['volume'].iloc[-1]
            volume_confirmation = current_volume > avg_volume * 1.2 if not pd.isna(avg_volume) else False
            
            # Determinar régimen de mercado
            price_change = (market_data['close'].iloc[-1] - market_data['close'].iloc[-20]) / market_data['close'].iloc[-20] if len(market_data) >= 20 else 0.0
            
            if volatility > 0.05:
                market_regime = 'HIGH_VOLATILITY'
            elif price_change > 0.05:
                market_regime = 'TRENDING_UP'
            elif price_change < -0.05:
                market_regime = 'TRENDING_DOWN'
            else:
                market_regime = 'SIDEWAYS'
            
            # Determinar sesión de mercado (simplificado)
            current_hour = decision.timestamp.hour
            if 0 <= current_hour < 8:
                market_session = 'ASIAN'
            elif 8 <= current_hour < 16:
                market_session = 'EUROPEAN'
            else:
                market_session = 'AMERICAN'
            
            return {
                'market_regime': market_regime,
                'volatility_level': volatility,
                'volume_confirmation': volume_confirmation,
                'market_session': market_session,
                'news_impact': None  # En sistema real se integraría con feed de noticias
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando contexto de mercado: {e}")
            return {
                'market_regime': 'SIDEWAYS',
                'volatility_level': 0.02,
                'volume_confirmation': False,
                'market_session': 'UNKNOWN',
                'news_impact': None
            }
    
    def _calculate_confluence_score(self, features: Dict[str, float]) -> float:
        """Calcula score de confluence mejorado"""
        try:
            confluence_score = 0.0
            
            # RSI confluence
            rsi = features.get('rsi', 50)
            if 30 <= rsi <= 70:
                confluence_score += 0.2
            elif 20 <= rsi <= 80:
                confluence_score += 0.1
            
            # MACD confluence
            macd = features.get('macd', 0)
            if macd > 0:
                confluence_score += 0.2
            elif macd > -0.001:
                confluence_score += 0.1
            
            # Trend strength confluence
            trend_strength = features.get('trend_strength', 0)
            if trend_strength > 0.02:
                confluence_score += 0.3
            elif trend_strength > 0.01:
                confluence_score += 0.2
            
            # Momentum confluence
            momentum = features.get('momentum', 0)
            if abs(momentum) > 0.01:
                confluence_score += 0.2
            elif abs(momentum) > 0.005:
                confluence_score += 0.1
            
            # Volume confirmation (si está disponible)
            volume_confirmation = features.get('volume_confirmation', False)
            if volume_confirmation:
                confluence_score += 0.1
            
            return min(1.0, confluence_score)
            
        except Exception as e:
            logger.error(f"❌ Error calculando confluence score: {e}")
            return 0.5
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcula RSI"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception:
            return 50.0
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26) -> float:
        """Calcula MACD"""
        try:
            if len(prices) < slow:
                return 0.0
            
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            
            return macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0.0
            
        except Exception:
            return 0.0
    
    async def _update_agent_state(self, trade_metric: DetailedTradeMetric):
        """Actualiza estado del agente con métrica del trade"""
        try:
            # Actualizar balance
            self.agent_state.current_balance += trade_metric.pnl_usdt
            self.agent_state.daily_pnl += trade_metric.pnl_usdt
            
            # Actualizar peak balance y drawdown
            if self.agent_state.current_balance > self.agent_state.peak_balance:
                self.agent_state.peak_balance = self.agent_state.current_balance
                self.agent_state.current_drawdown = 0.0
            else:
                self.agent_state.current_drawdown = (self.agent_state.peak_balance - self.agent_state.current_balance) / self.agent_state.peak_balance
                self.agent_state.max_drawdown = max(self.agent_state.max_drawdown, self.agent_state.current_drawdown)
            
            # Actualizar contadores de trades
            self.agent_state.total_trades += 1
            if trade_metric.was_successful:
                self.agent_state.winning_trades += 1
            else:
                self.agent_state.losing_trades += 1
            
            # Actualizar métricas por estrategia
            strategy_name = trade_metric.strategy_name
            if strategy_name not in self.agent_state.strategy_performance:
                self.agent_state.strategy_performance[strategy_name] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'total_pnl': 0.0,
                    'trades': []
                }
            
            strategy_metrics = self.agent_state.strategy_performance[strategy_name]
            strategy_metrics['total_trades'] += 1
            if trade_metric.was_successful:
                strategy_metrics['winning_trades'] += 1
            strategy_metrics['total_pnl'] += trade_metric.pnl_usdt
            strategy_metrics['trades'].append(trade_metric.trade_id)
            
            # Actualizar historial de calidad
            self.agent_state.quality_scores_history.append(trade_metric.get_quality_score())
            
            # Mantener solo últimos 1000 scores
            if len(self.agent_state.quality_scores_history) > 1000:
                self.agent_state.quality_scores_history = self.agent_state.quality_scores_history[-1000:]
            
            # Actualizar historial de régimen de mercado
            self.agent_state.market_regime_history.append(trade_metric.market_regime.value)
            if len(self.agent_state.market_regime_history) > 100:
                self.agent_state.market_regime_history = self.agent_state.market_regime_history[-100:]
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estado del agente: {e}")
    
    def get_strategy_metrics(self, strategy_name: str) -> Optional[StrategyMetrics]:
        """Obtiene métricas detalladas de una estrategia"""
        try:
            if strategy_name not in self.agent_state.strategy_performance:
                return None
            
            strategy_data = self.agent_state.strategy_performance[strategy_name]
            trades = self.trade_metrics_by_strategy.get(strategy_name, [])
            
            if not trades:
                return None
            
            # Calcular métricas
            total_trades = len(trades)
            winning_trades = sum(1 for trade in trades if trade.was_successful)
            total_pnl = sum(trade.pnl_usdt for trade in trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # Duración promedio
            avg_duration = np.mean([trade.duration_hours for trade in trades])
            
            # Calidad promedio
            avg_quality = np.mean([trade.get_quality_score() for trade in trades])
            
            # Mejor y peor trade
            pnls = [trade.pnl_usdt for trade in trades]
            best_trade = max(pnls) if pnls else 0.0
            worst_trade = min(pnls) if pnls else 0.0
            
            # Drawdown de la estrategia
            strategy_balance = 1000.0  # Balance inicial
            peak_balance = strategy_balance
            max_drawdown = 0.0
            
            for trade in trades:
                strategy_balance += trade.pnl_usdt
                if strategy_balance > peak_balance:
                    peak_balance = strategy_balance
                else:
                    drawdown = (peak_balance - strategy_balance) / peak_balance
                    max_drawdown = max(max_drawdown, drawdown)
            
            # Sharpe ratio simplificado
            returns = [trade.pnl_percentage / 100 for trade in trades]
            if len(returns) > 1:
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # Tendencia de performance
            if len(trades) >= 10:
                recent_trades = trades[-10:]
                recent_pnl = sum(trade.pnl_usdt for trade in recent_trades)
                older_trades = trades[-20:-10] if len(trades) >= 20 else trades[:-10]
                older_pnl = sum(trade.pnl_usdt for trade in older_trades) if older_trades else 0.0
                
                if recent_pnl > older_pnl * 1.1:
                    performance_trend = "IMPROVING"
                elif recent_pnl < older_pnl * 0.9:
                    performance_trend = "DECLINING"
                else:
                    performance_trend = "STABLE"
            else:
                performance_trend = "STABLE"
            
            return StrategyMetrics(
                strategy_name=strategy_name,
                total_trades=total_trades,
                winning_trades=winning_trades,
                total_pnl=total_pnl,
                avg_pnl=avg_pnl,
                win_rate=win_rate,
                avg_duration=avg_duration,
                avg_quality_score=avg_quality,
                best_trade=best_trade,
                worst_trade=worst_trade,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                last_used=trades[-1].timestamp if trades else datetime.now(),
                performance_trend=performance_trend
            )
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas de estrategia {strategy_name}: {e}")
            return None
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """Obtiene resumen completo del agente"""
        try:
            # Métricas básicas
            win_rate = (self.agent_state.winning_trades / self.agent_state.total_trades * 100) if self.agent_state.total_trades > 0 else 0.0
            
            # Calidad promedio
            avg_quality = np.mean(self.agent_state.quality_scores_history) if self.agent_state.quality_scores_history else 0.0
            
            # Régimen de mercado más común
            if self.agent_state.market_regime_history:
                regime_counts = {}
                for regime in self.agent_state.market_regime_history:
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                most_common_regime = max(regime_counts.items(), key=lambda x: x[1])[0]
            else:
                most_common_regime = "UNKNOWN"
            
            # Métricas por estrategia
            strategy_summaries = {}
            for strategy_name in self.agent_state.strategy_performance.keys():
                strategy_metrics = self.get_strategy_metrics(strategy_name)
                if strategy_metrics:
                    strategy_summaries[strategy_name] = {
                        'total_trades': strategy_metrics.total_trades,
                        'win_rate': strategy_metrics.win_rate,
                        'total_pnl': strategy_metrics.total_pnl,
                        'avg_quality': strategy_metrics.avg_quality_score,
                        'performance_trend': strategy_metrics.performance_trend
                    }
            
            return {
                'symbol': self.symbol,
                'agent_id': self.agent_id,
                'current_balance': self.agent_state.current_balance,
                'peak_balance': self.agent_state.peak_balance,
                'total_trades': self.agent_state.total_trades,
                'winning_trades': self.agent_state.winning_trades,
                'losing_trades': self.agent_state.losing_trades,
                'win_rate': win_rate,
                'current_drawdown': self.agent_state.current_drawdown,
                'max_drawdown': self.agent_state.max_drawdown,
                'daily_pnl': self.agent_state.daily_pnl,
                'avg_quality_score': avg_quality,
                'most_common_market_regime': most_common_regime,
                'strategy_summaries': strategy_summaries,
                'last_reset': self.agent_state.last_reset.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen del agente: {e}")
            return {'error': str(e)}
    
    async def _save_persistent_state(self):
        """Guarda estado persistente del agente"""
        try:
            # Guardar estado del agente
            state_data = asdict(self.agent_state)
            state_data['last_reset'] = self.agent_state.last_reset.isoformat()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            # Guardar trades detallados (solo últimos 1000)
            recent_trades = self.detailed_trades[-1000:] if len(self.detailed_trades) > 1000 else self.detailed_trades
            trades_data = [trade.to_dict() for trade in recent_trades]
            
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(trades_data, f, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado persistente: {e}")
    
    def _load_persistent_state(self):
        """Carga estado persistente del agente"""
        try:
            # Cargar estado del agente
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Convertir fechas
                state_data['last_reset'] = datetime.fromisoformat(state_data['last_reset'])
                
                # Actualizar estado
                for key, value in state_data.items():
                    if hasattr(self.agent_state, key):
                        setattr(self.agent_state, key, value)
            
            # Cargar trades detallados
            if self.trades_file.exists():
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    trades_data = json.load(f)
                
                # Convertir a DetailedTradeMetric
                self.detailed_trades = []
                for trade_data in trades_data:
                    try:
                        trade_metric = DetailedTradeMetric.from_dict(trade_data)
                        self.detailed_trades.append(trade_metric)
                    except Exception as e:
                        logger.warning(f"⚠️ Error cargando trade: {e}")
                        continue
                
                # Reorganizar por estrategia
                self.trade_metrics_by_strategy = {}
                for trade in self.detailed_trades:
                    strategy_name = trade.strategy_name
                    if strategy_name not in self.trade_metrics_by_strategy:
                        self.trade_metrics_by_strategy[strategy_name] = []
                    self.trade_metrics_by_strategy[strategy_name].append(trade)
            
            logger.info(f"✅ Estado persistente cargado para {self.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando estado persistente: {e}")
    
    def cleanup_memory(self):
        """Limpia memoria del agente"""
        try:
            # Limpiar trades antiguos (mantener solo últimos 500)
            if len(self.detailed_trades) > 500:
                self.detailed_trades = self.detailed_trades[-500:]
            
            # Limpiar métricas por estrategia
            for strategy_name in self.trade_metrics_by_strategy:
                if len(self.trade_metrics_by_strategy[strategy_name]) > 500:
                    self.trade_metrics_by_strategy[strategy_name] = self.trade_metrics_by_strategy[strategy_name][-500:]
            
            # Limpiar historiales
            if len(self.agent_state.quality_scores_history) > 500:
                self.agent_state.quality_scores_history = self.agent_state.quality_scores_history[-500:]
            
            if len(self.agent_state.market_regime_history) > 100:
                self.agent_state.market_regime_history = self.agent_state.market_regime_history[-100:]
            
            logger.info(f"✅ Memoria limpiada para agente {self.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando memoria: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """Obtiene estado actual del agente para serialización"""
        try:
            return {
                'agent_id': self.agent_id,
                'symbol': self.symbol,
                'is_active': self.is_active,
                'current_balance': self.agent_state.current_balance,
                'total_trades': self.agent_state.total_trades,
                'winning_trades': self.agent_state.winning_trades,
                'strategy_count': len(self.agent_state.strategy_performance),
                'last_trade_time': self.detailed_trades[-1].timestamp.isoformat() if self.detailed_trades else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {'error': str(e)}
