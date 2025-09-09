"""
Multi-Exchange Module - Bot Trading v10 Personal
================================================

Soporte multi-exchange para trading personal con:
- Arbitraje entre Bitget y Binance
- Sincronización de datos en tiempo real
- Gestión de credenciales encriptadas
- Optimización de latencia para HFT
"""

from .exchange_manager import MultiExchangeManager
from .arbitrage_detector import ArbitrageDetector
from .sync_manager import ExchangeSyncManager

__all__ = [
    'MultiExchangeManager',
    'ArbitrageDetector', 
    'ExchangeSyncManager'
]
