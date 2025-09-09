# Ruta: scripts/history/__init__.py
"""
History Scripts - Bot Trading v10 Enterprise
===========================================

Scripts para gestión de datos históricos.

Scripts disponibles:
- download_history: Descarga datos históricos
- inspect_history: Inspecciona datos existentes
- repair_history: Repara datos corruptos
"""

from .download_history import *
from .inspect_history import *
from .repair_history import *

__all__ = [
    'download_history',
    'inspect_history', 
    'repair_history'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
