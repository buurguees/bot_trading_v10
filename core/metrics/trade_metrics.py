#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/metrics/trade_metrics.py
=============================
Sistema de Métricas Detalladas por Trade Individual

Proporciona tracking granular de cada trade ejecutado por los agentes,
incluyendo análisis técnico, contexto de mercado y métricas de calidad.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import json

class TradeAction(Enum):
    """Acciones de trading"""
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"
    HOLD = "HOLD"

class ConfidenceLevel(Enum):
    """Niveles de confianza del agente"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class MarketRegime(Enum):
    """Regímenes de mercado"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"

class ExitReason(Enum):
    """Razones de salida del trade"""
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TIME_LIMIT = "TIME_LIMIT"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    MANUAL_CLOSE = "MANUAL_CLOSE"

@dataclass
class DetailedTradeMetric:
    """Métrica detallada de cada trade individual para reporte completo"""
    
    # === IDENTIFICACIÓN ===
    trade_id: str
    agent_symbol: str
    timestamp: datetime
    cycle_id: int
    
    # === DETALLES DEL TRADE ===
    action: TradeAction
    entry_price: float
    exit_price: float
    quantity: float
    leverage: float
    
    # === DURACIÓN ===
    entry_time: datetime
    exit_time: datetime
    duration_candles: int  # Número de velas
    duration_hours: float
    
    # === RESULTADOS FINANCIEROS ===
    pnl_usdt: float
    pnl_percentage: float
    balance_used: float  # Capital utilizado
    balance_after: float  # Balance después del trade
    
    # === ANÁLISIS TÉCNICO USADO ===
    confidence_level: ConfidenceLevel
    strategy_name: str
    confluence_score: float
    risk_reward_ratio: float
    
    # === CONTEXTO DEL MERCADO ===
    market_regime: MarketRegime
    volatility_level: float
    volume_confirmation: bool
    
    # === MÉTRICAS DE CALIDAD ===
    was_successful: bool
    follow_plan: bool  # Si siguió el plan original
    exit_reason: ExitReason
    
    # === ANÁLISIS TÉCNICO DETALLADO ===
    technical_indicators: Dict[str, float]
    support_resistance_levels: Dict[str, float]
    trend_strength: float
    momentum_score: float
    
    # === GESTIÓN DE RIESGO ===
    max_drawdown_during_trade: float
    risk_per_trade_pct: float
    position_size_pct: float
    
    # === CONTEXTO TEMPORAL ===
    timeframe_analyzed: str
    market_session: str  # "ASIAN", "EUROPEAN", "AMERICAN", "OVERLAP"
    news_impact: Optional[str] = None
    
    # === MÉTRICAS DE CALIDAD AVANZADAS ===
    execution_slippage: float = 0.0
    commission_paid: float = 0.0
    net_pnl: float = 0.0  # PnL después de comisiones
    
    def __post_init__(self):
        """Calcula métricas derivadas después de la inicialización"""
        if self.net_pnl == 0.0:
            self.net_pnl = self.pnl_usdt - self.commission_paid
        
        if self.duration_hours == 0.0 and self.entry_time and self.exit_time:
            duration = self.exit_time - self.entry_time
            self.duration_hours = duration.total_seconds() / 3600
    
    @classmethod
    def create_from_trade_data(
        cls,
        trade_data: Dict[str, Any],
        agent_symbol: str,
        cycle_id: int,
        technical_analysis: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> 'DetailedTradeMetric':
        """Crea métrica detallada desde datos de trade"""
        
        # Calcular duración
        entry_time = trade_data.get('entry_time', datetime.now())
        exit_time = trade_data.get('exit_time', datetime.now())
        duration = exit_time - entry_time
        
        # Calcular PnL
        entry_price = trade_data['entry_price']
        exit_price = trade_data['exit_price']
        quantity = trade_data['quantity']
        leverage = trade_data.get('leverage', 1.0)
        
        if trade_data['action'] in ['LONG', 'CLOSE_SHORT']:
            pnl_usdt = (exit_price - entry_price) * quantity * leverage
        else:  # SHORT, CLOSE_LONG
            pnl_usdt = (entry_price - exit_price) * quantity * leverage
        
        pnl_percentage = (pnl_usdt / (entry_price * quantity)) * 100
        
        # Determinar si fue exitoso
        was_successful = pnl_usdt > 0
        
        # Calcular balance después del trade
        balance_before = trade_data.get('balance_before', 1000.0)
        balance_after = balance_before + pnl_usdt
        
        return cls(
            # Identificación
            trade_id=str(uuid.uuid4()),
            agent_symbol=agent_symbol,
            timestamp=datetime.now(),
            cycle_id=cycle_id,
            
            # Detalles del trade
            action=TradeAction(trade_data['action']),
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            leverage=leverage,
            
            # Duración
            entry_time=entry_time,
            exit_time=exit_time,
            duration_candles=trade_data.get('duration_candles', 0),
            duration_hours=duration.total_seconds() / 3600,
            
            # Resultados financieros
            pnl_usdt=pnl_usdt,
            pnl_percentage=pnl_percentage,
            balance_used=entry_price * quantity,
            balance_after=balance_after,
            
            # Análisis técnico usado
            confidence_level=ConfidenceLevel(technical_analysis.get('confidence_level', 'MEDIUM')),
            strategy_name=technical_analysis.get('strategy_name', 'unknown'),
            confluence_score=technical_analysis.get('confluence_score', 0.0),
            risk_reward_ratio=technical_analysis.get('risk_reward_ratio', 1.0),
            
            # Contexto del mercado
            market_regime=MarketRegime(market_context.get('market_regime', 'SIDEWAYS')),
            volatility_level=market_context.get('volatility_level', 0.02),
            volume_confirmation=market_context.get('volume_confirmation', False),
            
            # Métricas de calidad
            was_successful=was_successful,
            follow_plan=trade_data.get('follow_plan', True),
            exit_reason=ExitReason(trade_data.get('exit_reason', 'STRATEGY_SIGNAL')),
            
            # Análisis técnico detallado
            technical_indicators=technical_analysis.get('indicators', {}),
            support_resistance_levels=technical_analysis.get('support_resistance', {}),
            trend_strength=technical_analysis.get('trend_strength', 0.0),
            momentum_score=technical_analysis.get('momentum_score', 0.0),
            
            # Gestión de riesgo
            max_drawdown_during_trade=trade_data.get('max_drawdown', 0.0),
            risk_per_trade_pct=trade_data.get('risk_per_trade_pct', 2.0),
            position_size_pct=trade_data.get('position_size_pct', 10.0),
            
            # Contexto temporal
            timeframe_analyzed=trade_data.get('timeframe', '5m'),
            market_session=market_context.get('market_session', 'UNKNOWN'),
            news_impact=market_context.get('news_impact'),
            
            # Métricas de calidad avanzadas
            execution_slippage=trade_data.get('slippage', 0.0),
            commission_paid=trade_data.get('commission', 0.0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        data = asdict(self)
        
        # Convertir enums a strings
        data['action'] = self.action.value
        data['confidence_level'] = self.confidence_level.value
        data['market_regime'] = self.market_regime.value
        data['exit_reason'] = self.exit_reason.value
        
        # Convertir datetime a ISO string
        data['timestamp'] = self.timestamp.isoformat()
        data['entry_time'] = self.entry_time.isoformat()
        data['exit_time'] = self.exit_time.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetailedTradeMetric':
        """Crea instancia desde diccionario"""
        # Convertir strings de enums de vuelta a enums
        data['action'] = TradeAction(data['action'])
        data['confidence_level'] = ConfidenceLevel(data['confidence_level'])
        data['market_regime'] = MarketRegime(data['market_regime'])
        data['exit_reason'] = ExitReason(data['exit_reason'])
        
        # Convertir strings ISO de vuelta a datetime
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        
        return cls(**data)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de performance del trade"""
        return {
            'trade_id': self.trade_id,
            'agent_symbol': self.agent_symbol,
            'action': self.action.value,
            'pnl_usdt': self.pnl_usdt,
            'pnl_percentage': self.pnl_percentage,
            'duration_hours': self.duration_hours,
            'was_successful': self.was_successful,
            'confidence_level': self.confidence_level.value,
            'strategy_name': self.strategy_name,
            'confluence_score': self.confluence_score,
            'exit_reason': self.exit_reason.value
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de riesgo del trade"""
        return {
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'position_size_pct': self.position_size_pct,
            'max_drawdown_during_trade': self.max_drawdown_during_trade,
            'risk_reward_ratio': self.risk_reward_ratio,
            'leverage': self.leverage,
            'execution_slippage': self.execution_slippage,
            'commission_paid': self.commission_paid,
            'net_pnl': self.net_pnl
        }
    
    def get_market_context(self) -> Dict[str, Any]:
        """Obtiene contexto de mercado del trade"""
        return {
            'market_regime': self.market_regime.value,
            'volatility_level': self.volatility_level,
            'volume_confirmation': self.volume_confirmation,
            'timeframe_analyzed': self.timeframe_analyzed,
            'market_session': self.market_session,
            'news_impact': self.news_impact,
            'trend_strength': self.trend_strength,
            'momentum_score': self.momentum_score
        }
    
    def is_high_quality_trade(self) -> bool:
        """Determina si el trade es de alta calidad"""
        quality_checks = [
            self.was_successful,
            self.follow_plan,
            self.confluence_score >= 0.7,
            self.risk_reward_ratio >= 1.5,
            self.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH],
            self.volume_confirmation,
            self.execution_slippage <= 0.001,  # <= 0.1%
            self.duration_hours >= 0.5  # Al menos 30 minutos
        ]
        
        return sum(quality_checks) >= 6  # Al menos 6 de 8 checks
    
    def get_quality_score(self) -> float:
        """Calcula score de calidad del trade (0-100)"""
        quality_factors = {
            'success': 25 if self.was_successful else 0,
            'follow_plan': 15 if self.follow_plan else 0,
            'confluence': min(20, self.confluence_score * 20),
            'risk_reward': min(15, (self.risk_reward_ratio - 1) * 7.5),
            'confidence': {
                ConfidenceLevel.VERY_LOW: 0,
                ConfidenceLevel.LOW: 5,
                ConfidenceLevel.MEDIUM: 10,
                ConfidenceLevel.HIGH: 15,
                ConfidenceLevel.VERY_HIGH: 20
            }.get(self.confidence_level, 0),
            'volume': 10 if self.volume_confirmation else 0,
            'execution': max(0, 10 - (self.execution_slippage * 10000)),
            'duration': min(5, self.duration_hours * 2)  # Bonus por trades más largos
        }
        
        return sum(quality_factors.values())
