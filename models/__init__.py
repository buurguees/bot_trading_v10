"""
models/__init__.py
Módulo de Machine Learning para el Trading Bot v10
Ubicación: C:\\TradingBot_v10\\models\\__init__.py

Este módulo contiene toda la arquitectura de ML incluyendo:
- Modelos de deep learning (LSTM, Transformer)
- Sistema de entrenamiento adaptativo
- Evaluación y métricas de performance
- Predicciones en tiempo real
- Sistema de recompensas y aprendizaje por refuerzo
"""

from .neural_network import (
    TradingModel,
    LSTMTradingModel, 
    TransformerTradingModel,
    EnsembleTradingModel
)

from .trainer import (
    ModelTrainer,
    AdaptiveTrainer,
    ReinforcementLearningTrainer
)

from .predictor import (
    TradingPredictor,
    RealTimePredictor,
    ConfidenceCalculator
)

# Archivos que se implementarán en el futuro
# from .evaluator import ModelEvaluator, PerformanceTracker, MetricsCalculator
# from .model_manager import ModelManager, model_manager
# from .reward_system import RewardSystem, TradeReward, LearningReward

__version__ = "1.0.0"
__author__ = "Trading Bot v10"

__all__ = [
    # Modelos base
    'TradingModel',
    'LSTMTradingModel', 
    'TransformerTradingModel',
    'EnsembleTradingModel',
    
    # Entrenamiento
    'ModelTrainer',
    'AdaptiveTrainer', 
    'ReinforcementLearningTrainer',
    
    # Predicción
    'TradingPredictor',
    'RealTimePredictor',
    'ConfidenceCalculator',
    
    # Evaluación (futuro)
    # 'ModelEvaluator',
    # 'PerformanceTracker', 
    # 'MetricsCalculator',
    
    # Gestión (futuro)
    # 'ModelManager',
    # 'model_manager',
    
    # Sistema de recompensas (futuro)
    # 'RewardSystem',
    # 'TradeReward',
    # 'LearningReward'
]