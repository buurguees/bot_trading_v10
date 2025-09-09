# Ruta: core/ml/enterprise/__init__.py
# __init__.py - Módulo de modelos enterprise
# Ubicación: C:\TradingBot_v10\models\enterprise\__init__.py

"""
Módulo de modelos enterprise para Trading Bot v10.

Este módulo proporciona:
- Arquitecturas de modelos avanzadas (LSTM-Attention, Transformer, CNN-LSTM)
- Motor de entrenamiento distribuido con PyTorch Lightning
- Gestión de experimentos con MLflow
- Optimización de hiperparámetros con Optuna
- Callbacks personalizados para monitoreo
- Métricas de trading especializadas
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Enterprise Team"

# Imports principales
from .model_architecture import (
    create_model,
    LSTMAttentionModel,
    TransformerModel,
    CNNLSTMModel,
    GRUSimpleModel,
    EnsembleModel
)

from .training_engine import EnterpriseTrainingEngine
from .distributed_trainer import DistributedTrainer
from .hyperparameter_tuner import HyperparameterTuner
from .experiment_manager import ExperimentManager
from .checkpoint_manager import CheckpointManager
from .model_registry import ModelRegistry
from .data_module import TradingDataModule
from .callbacks import EnterpriseCallbacks
from .metrics_tracker import MetricsTracker

# Exports principales
__all__ = [
    # Modelos
    "create_model",
    "LSTMAttentionModel",
    "TransformerModel", 
    "CNNLSTMModel",
    "GRUSimpleModel",
    "EnsembleModel",
    
    # Entrenamiento
    "EnterpriseTrainingEngine",
    "DistributedTrainer",
    "HyperparameterTuner",
    "ExperimentManager",
    "CheckpointManager",
    "ModelRegistry",
    
    # Datos y utilidades
    "TradingDataModule",
    "EnterpriseCallbacks",
    "MetricsTracker"
]