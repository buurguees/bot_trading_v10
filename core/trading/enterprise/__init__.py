# Ruta: core/trading/enterprise/__init__.py
"""
Módulo Enterprise Trading - Bot Trading v10
==========================================

Este módulo contiene todos los componentes enterprise para trading de futuros
en tiempo real con gestión avanzada de posiciones y señales ML.

Componentes principales:
- FuturesEngine: Motor principal de trading de futuros
- SignalGenerator: Generador de señales ML en tiempo real
- PositionManager: Gestor avanzado de posiciones long/short
- OrderExecutor: Ejecutor de órdenes con múltiples tipos
- LeverageCalculator: Calculadora dinámica de leverage
- MarketAnalyzer: Analizador de condiciones de mercado

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

from .futures_engine import FuturesEngine
from .signal_generator import SignalGenerator
from .position_manager import PositionManager
from .order_executor import OrderExecutor
from .leverage_calculator import LeverageCalculator
from .market_analyzer import MarketAnalyzer
from .trading_signal import TradingSignal, SignalType, SignalStrength
from .position import Position

__all__ = [
    'FuturesEngine',
    'SignalGenerator', 
    'PositionManager',
    'OrderExecutor',
    'LeverageCalculator',
    'MarketAnalyzer',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'Position'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'