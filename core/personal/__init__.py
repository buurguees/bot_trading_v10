# Ruta: core/personal/__init__.py
"""
Personal Module - Bot Trading v10 Personal
==========================================

Módulos personalizados para trading individual con:
- Multi-exchange support (Bitget + Binance)
- Arbitraje automático
- Optimización de latencia HFT
- Dashboard personal
- Monitoreo simplificado
"""

from .multi_exchange import *
from .latency import *

__all__ = [
    'MultiExchangeManager',
    'ArbitrageDetector',
    'ExchangeSyncManager',
    'LatencyOptimizer'
]
