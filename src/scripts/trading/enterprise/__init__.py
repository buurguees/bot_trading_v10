"""
Scripts Enterprise Trading - Bot Trading v10
===========================================

Scripts para ejecutar el sistema de trading enterprise en diferentes modos:
- Live Trading: Trading en vivo con dinero real
- Paper Trading: Trading simulado para pruebas
- Emergency Stop: Parada de emergencia del sistema

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

from .start_live_trading import start_live_trading
from .start_paper_trading import start_paper_trading
from .emergency_stop import emergency_stop

__all__ = [
    'start_live_trading',
    'start_paper_trading', 
    'emergency_stop'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'