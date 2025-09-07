"""
monitoring/callbacks/__init__.py
Callbacks organizados por funcionalidad
"""

from .home_callbacks import register_home_callbacks
from .trading_callbacks import register_trading_callbacks
from .chart_callbacks import register_chart_callbacks

__all__ = ['register_home_callbacks', 'register_trading_callbacks', 'register_chart_callbacks']
