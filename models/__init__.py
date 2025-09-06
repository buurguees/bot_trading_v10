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

# Componentes core implementados
from .prediction_engine import prediction_engine, predict, get_prediction_summary, health_check as prediction_health_check
from .adaptive_trainer import adaptive_trainer, train_initial_model, online_learning_update, get_training_status, health_check as trainer_health_check
from .model_evaluator import model_evaluator, evaluate_model_performance, get_evaluation_summary, health_check as evaluator_health_check
from .confidence_estimator import confidence_estimator, estimate_confidence, update_calibration_data, get_confidence_statistics, get_calibration_quality, health_check as confidence_health_check

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
    
    # Componentes core implementados
    'prediction_engine',
    'predict',
    'get_prediction_summary',
    'prediction_health_check',
    'adaptive_trainer',
    'train_initial_model',
    'online_learning_update',
    'get_training_status',
    'trainer_health_check',
    'model_evaluator',
    'evaluate_model_performance',
    'get_evaluation_summary',
    'evaluator_health_check',
    'confidence_estimator',
    'estimate_confidence',
    'update_calibration_data',
    'get_confidence_statistics',
    'get_calibration_quality',
    'confidence_health_check',
    
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