"""
🤖 agents/ - Sistema de Agentes de IA para Trading

Este módulo contiene el agente principal de trading que integra:
- Toma de decisiones autónoma
- Aprendizaje continuo y autodidacta
- Autocorrección y adaptación
- Integración con todo el sistema ML y trading

Autor: Alex B
Fecha: 2025-01-07
"""

from .trading_agent import TradingAgent
from .autonomous_decision_engine import AutonomousDecisionEngine
from .self_learning_system import SelfLearningSystem
from .self_correction_mechanism import SelfCorrectionMechanism

__all__ = [
    'TradingAgent',
    'AutonomousDecisionEngine', 
    'SelfLearningSystem',
    'SelfCorrectionMechanism'
]

__version__ = "1.0.0"
