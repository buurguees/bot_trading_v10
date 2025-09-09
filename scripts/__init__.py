"""
Scripts Module - Bot Trading v10 Enterprise
===========================================

Scripts de ejecución y mantenimiento enterprise.
Cada script maneja un comando específico de Telegram.

Submódulos:
- history: Scripts de gestión de datos históricos
- trading: Scripts de trading (live, paper, emergency)
- training: Scripts de entrenamiento
- deployment: Scripts de despliegue
- maintenance: Scripts de mantenimiento
"""

from .history import *
from .trading import *
from .training import *
from .deployment import *
from .maintenance import *

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
