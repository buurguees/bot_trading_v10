# Ruta: scripts/training/__init__.py
"""
Training Scripts - Bot Trading v10 Enterprise
============================================

Scripts para entrenamiento del modelo de IA.

Scripts disponibles:
- train_historical: Entrenamiento sobre datos históricos
- train_live: Entrenamiento en tiempo real
- state_manager: Gestión de estado del entrenamiento
"""

from .train_historical import *
from .train_live import *
from .state_manager import *

__all__ = [
    'train_historical',
    'train_live',
    'state_manager'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
