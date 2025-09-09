# __init__.py - Módulo de scripts de entrenamiento enterprise
# Ubicación: C:\TradingBot_v10\training_scripts\enterprise\__init__.py

"""
Módulo de scripts de entrenamiento enterprise para Trading Bot v10.

Este módulo proporciona:
- Scripts de entrenamiento de 8 horas
- Entrenamiento distribuido
- Optimización de hiperparámetros
- Evaluación de modelos
- Deployment de modelos
- Monitoreo de entrenamiento
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Enterprise Team"

# Imports principales
from .start_8h_training import EightHourTrainingManager
from .start_distributed_training import DistributedTrainingManager
from .hyperparameter_optimization import HyperparameterOptimizationManager

# Exports principales
__all__ = [
    "EightHourTrainingManager",
    "DistributedTrainingManager", 
    "HyperparameterOptimizationManager"
]
