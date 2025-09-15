# Ruta: scripts/training/__init__.py
"""
Training Scripts - Bot Trading v10 Enterprise
============================================

Scripts para entrenamiento del modelo de IA.

Scripts disponibles:
- train_hist_parallel: Entrenamiento histórico paralelo (principal)
- train_live: Entrenamiento en tiempo real
- state_manager: Gestión de estado del entrenamiento
"""

from .train_hist_parallel import *
from .train_live import *
from .state_manager import *

__all__ = [
    'train_hist_parallel',
    'train_live',
    'state_manager'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
