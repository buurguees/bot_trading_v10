# Ruta: core/ml/legacy/trainer.py
"""
models/trainer.py
Sistema de entrenamiento adaptativo y aprendizaje por refuerzo
Ubicación: C:\\TradingBot_v10\\models\\trainer.py

Funcionalidades:
- Entrenamiento automático basado en performance
- Reentrenamiento adaptativo
- Optimización de hiperparámetros
- Aprendizaje por refuerzo para trading
- Validación cruzada temporal
- Detección de regímenes de mercado
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
import logging
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import optuna
import tensorflow as tf
from tensorflow.keras.callbacks import Callback
import asyncio
import threading
from dataclasses import dataclass
import json
import pickle
import time
from pathlib import Path

from .neural_network import TradingModel, create_model
from core.data.preprocessor import data_preprocessor
from core.data.database import db_manager, ModelMetrics, TradeRecord
from core.config.config_loader import user_config
from core.config.settings import MODELS_DIR

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuración de entrenamiento"""
    model_type: str = "lstm"
    retrain_frequency: int = 100  # Cada N trades
    min_trades_before_retrain: int = 50
    performance_threshold: float = 0.6  # Reentrenar si accuracy < 60%
    validation_split: float = 0.2
    enable_hyperparameter_optimization: bool = True
    max_optimization_trials: int = 50
    early_stopping_patience: int = 15
    reduce_lr_patience: int = 8
    max_epochs: int = 150

class ModelTrainer:
    """Entrenador base de modelos"""
    
    def __init__(self, config: TrainingConfig = None):
        self.config = config or TrainingConfig()
        
        # Configuración desde usuario
        self.ai_settings = user_config.get_ai_model_settings()
        self.retraining_config = self.ai_settings.get('retraining', {})
        
        # Estado del entrenamiento
        self.current_model = None
        self.training_history = []
        self.last_retrain_time = None
        self.trades_since_retrain = 0
        self.best_model_score = 0.0
        
        # Optimización de hiperparámetros
        self.study = None
        self.best_hyperparameters = {}
        
        logger.info("ModelTrainer inicializado")
    
    def prepare_training_data(
        self, 
        symbol: str = "BTCUSDT",
        days_back: int = 90
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepara datos para entrenamiento con división temporal"""
        try:
            logger.info(f"Preparando datos de entrenamiento para {symbol}")
            
            # Obtener datos procesados
            X, y, df = data_preprocessor.prepare_training_data(
                symbol=symbol,
                days_back=days_back,
                target_method="classification"
            )
            
            if X.shape[0] == 0:
                raise ValueError("No se pudieron obtener datos de entrenamiento")
            
            # División temporal (más realista para series temporales)
            split_idx = int(X.shape[0] * (1 - self.config.validation_split))
            
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            logger.info(f"Datos preparados: Train={X_train.shape}, Val={X_val.shape}")
            
            return X_train, X_val, y_train, y_val
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento: {e}")
            return np.array([]), np.array([]), np.array([]), np.array([])
    
    def train_model(
        self,
        model: TradingModel = None,
        X_train: np.ndarray = None,
        y_train: np.ndarray = None,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Entrena un modelo con los datos proporcionados"""
        try:
            if model is None:
                model = create_model(self.config.model_type)
            
            if X_train is None or y_train is None:
                X_train, X_val, y_train, y_val = self.prepare_training_data()
            
            if X_train.shape[0] == 0:
                raise ValueError("Datos de entrenamiento vacíos")
            
            logger.info(f"Iniciando entrenamiento de modelo {model.model_type}")
            
            # Usar mejores hiperparámetros si están disponibles
            training_kwargs = kwargs.copy()
            if self.best_hyperparameters:
                training_kwargs.update(self.best_hyperparameters)
            
            # Configurar epochs
            training_kwargs['epochs'] = training_kwargs.get('epochs', self.config.max_epochs)
            
            # Entrenar modelo
            training_results = model.train(
                X_train, y_train, X_val, y_val, **training_kwargs
            )
            
            # Evaluar modelo
            evaluation_results = self.evaluate_model(model, X_val, y_val)
            
            # Guardar métricas en base de datos
            self.save_training_metrics(model, training_results, evaluation_results)
            
            # Actualizar modelo actual si es mejor
            if self.should_update_current_model(evaluation_results):
                self.current_model = model
                self.best_model_score = evaluation_results.get('accuracy', 0)
                # Guardar modelo
                model.save_model()
                logger.info("Modelo actual actualizado y guardado")
            
            self.last_retrain_time = datetime.now()
            self.trades_since_retrain = 0
            
            # Añadir a historial
            self.training_history.append({
                'timestamp': datetime.now(),
                'model_version': model.model_version,
                'training_results': training_results,
                'evaluation_results': evaluation_results
            })
            
            return {
                'training_results': training_results,
                'evaluation_results': evaluation_results,
                'model_updated': self.current_model == model
            }
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            return {}
    
    def evaluate_model(
        self, 
        model: TradingModel, 
        X_test: np.ndarray, 
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """Evalúa el modelo en datos de test"""
        try:
            # Predicciones
            predictions = model.predict(X_test)
            
            # Si hay múltiples outputs, usar el de clasificación
            if isinstance(predictions, list):
                y_pred_proba = predictions[0]
                confidence_scores = predictions[2] if len(predictions) > 2 else None
            else:
                y_pred_proba = predictions
                confidence_scores = None
            
            # Convertir probabilidades a clases
            y_pred = np.argmax(y_pred_proba, axis=1)
            
            # Calcular métricas básicas
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            # Métricas adicionales de trading
            correct_predictions = np.sum(y_pred == y_test)
            total_predictions = len(y_test)
            
            # Confianza promedio (si disponible)
            avg_confidence = 0.0
            if confidence_scores is not None:
                avg_confidence = np.mean(confidence_scores)
            
            # Métricas por clase
            class_accuracy = {}
            for class_label in [0, 1, 2]:  # SELL, HOLD, BUY
                class_mask = y_test == class_label
                if np.sum(class_mask) > 0:
                    class_predictions = y_pred[class_mask]
                    class_accuracy[f'accuracy_class_{class_label}'] = np.mean(class_predictions == class_label)
            
            # Sharpe ratio simulado (basado en predicciones)
            sharpe_ratio = self._calculate_prediction_sharpe(y_pred, y_test, y_pred_proba)
            
            metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'correct_predictions': correct_predictions,
                'total_predictions': total_predictions,
                'avg_confidence': avg_confidence,
                'sharpe_ratio': sharpe_ratio,
                **class_accuracy
            }
            
            logger.info(f"Evaluación completada: Accuracy={accuracy:.3f}, F1={f1:.3f}, Sharpe={sharpe_ratio:.3f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluando modelo: {e}")
            return {}
    
    def _calculate_prediction_sharpe(
        self, 
        y_pred: np.ndarray, 
        y_true: np.ndarray, 
        y_proba: np.ndarray
    ) -> float:
        """Calcula un Sharpe ratio simulado basado en predicciones"""
        try:
            # Simular returns basados en predicciones
            returns = []
            for i in range(len(y_pred)):
                pred_class = y_pred[i]
                true_class = y_true[i]
                confidence = np.max(y_proba[i])
                
                # Simular return basado en si la predicción fue correcta
                if pred_class == true_class:
                    # Predicción correcta: return positivo proporcional a confianza
                    if pred_class == 2:  # BUY correcto
                        return_val = confidence * 0.02  # 2% máximo
                    elif pred_class == 0:  # SELL correcto
                        return_val = confidence * 0.02
                    else:  # HOLD correcto
                        return_val = 0.001  # Small positive return
                else:
                    # Predicción incorrecta: return negativo
                    return_val = -confidence * 0.015  # -1.5% máximo
                
                returns.append(return_val)
            
            returns = np.array(returns)
            
            if len(returns) == 0 or np.std(returns) == 0:
                return 0.0
            
            # Sharpe ratio = (mean return - risk free rate) / std return
            # Asumiendo risk free rate = 0
            sharpe = np.mean(returns) / np.std(returns)
            
            # Anualizar (asumiendo datos horarios)
            sharpe_annualized = sharpe * np.sqrt(365 * 24)
            
            return sharpe_annualized
            
        except Exception as e:
            logger.error(f"Error calculando Sharpe ratio: {e}")
            return 0.0
    
    def should_update_current_model(self, evaluation_results: Dict[str, float]) -> bool:
        """Determina si debe actualizar el modelo actual"""
        if not evaluation_results:
            return False
        
        accuracy = evaluation_results.get('accuracy', 0)
        f1_score = evaluation_results.get('f1_score', 0)
        sharpe_ratio = evaluation_results.get('sharpe_ratio', 0)
        
        # Score combinado
        combined_score = (accuracy * 0.4 + f1_score * 0.3 + 
                         min(max(sharpe_ratio / 2.0, 0), 1) * 0.3)
        
        # Si no hay modelo actual, usar este si es razonable
        if self.current_model is None:
            return combined_score > 0.55  # Al menos 55% score combinado
        
        # Comparar con modelo actual
        improvement_threshold = 0.03  # 3% mejora mínima
        return combined_score > (self.best_model_score + improvement_threshold)
    
    def save_training_metrics(
        self,
        model: TradingModel,
        training_results: Dict[str, Any],
        evaluation_results: Dict[str, float]
    ):
        """Guarda métricas de entrenamiento en base de datos"""
        try:
            if not evaluation_results:
                return
            
            # Crear objeto ModelMetrics
            metrics = ModelMetrics(
                model_version=model.model_version,
                accuracy=evaluation_results.get('accuracy', 0.0),
                precision=evaluation_results.get('precision', 0.0),
                recall=evaluation_results.get('recall', 0.0),
                f1_score=evaluation_results.get('f1_score', 0.0),
                total_predictions=evaluation_results.get('total_predictions', 0),
                correct_predictions=evaluation_results.get('correct_predictions', 0),
                training_time=training_results.get('training_time', 0.0),
                features_used=data_preprocessor.feature_columns[:20],  # Primeras 20 features
                hyperparameters={
                    'model_type': model.model_type,
                    'ai_settings': model.ai_settings,
                    'best_hyperparameters': self.best_hyperparameters,
                    'sharpe_ratio': evaluation_results.get('sharpe_ratio', 0.0)
                }
            )
            
            # Guardar en base de datos
            db_manager.save_model_metrics(metrics)
            logger.info("Métricas de entrenamiento guardadas")
            
        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")
    
    def should_retrain(self) -> bool:
        """Determina si el modelo debe ser reentrenado"""
        try:
            # Verificar frecuencia de reentrenamiento
            frequency = self.retraining_config.get('frequency', 'adaptive')
            
            if frequency == 'fixed':
                min_trades = self.retraining_config.get('min_trades_before_retrain', 50)
                return self.trades_since_retrain >= min_trades
            
            elif frequency == 'performance_based':
                # Reentrenar si performance ha bajado
                return self.check_performance_degradation()
            
            elif frequency == 'adaptive':
                # Combinar ambos criterios
                min_trades_met = self.trades_since_retrain >= self.config.min_trades_before_retrain
                performance_low = self.check_performance_degradation()
                return min_trades_met and performance_low
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando necesidad de reentrenamiento: {e}")
            return False
    
    def check_performance_degradation(self) -> bool:
        """Verifica si la performance del modelo ha degradado"""
        try:
            # Obtener trades recientes
            recent_trades = db_manager.get_trades(
                status='closed',
                start_date=datetime.now() - timedelta(days=7),
                limit=50
            )
            
            if recent_trades.empty:
                return False
            
            # Calcular accuracy reciente
            correct_predictions = 0
            total_predictions = len(recent_trades)
            
            for _, trade in recent_trades.iterrows():
                # Determinar si la predicción fue correcta
                model_pred = trade.get('model_prediction', 0.5)
                pnl = trade.get('pnl', 0)
                
                # Predicción correcta si:
                # - Predicción > 0.6 (BUY) y PnL > 0, o
                # - Predicción < 0.4 (SELL) y PnL < 0, o
                # - 0.4 <= Predicción <= 0.6 (HOLD) y abs(PnL) < threshold
                if ((model_pred > 0.6 and pnl > 0) or
                    (model_pred < 0.4 and pnl < 0) or
                    (0.4 <= model_pred <= 0.6 and abs(pnl) < 0.01)):
                    correct_predictions += 1
            
            recent_accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            threshold = self.retraining_config.get('performance_threshold', 0.6)
            
            logger.debug(f"Accuracy reciente: {recent_accuracy:.3f}, Threshold: {threshold}")
            return recent_accuracy < threshold
            
        except Exception as e:
            logger.error(f"Error verificando degradación de performance: {e}")
            return False
    
    def optimize_hyperparameters(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = None
    ) -> Dict[str, Any]:
        """Optimiza hiperparámetros usando Optuna"""
        try:
            if not self.config.enable_hyperparameter_optimization:
                logger.info("Optimización de hiperparámetros deshabilitada")
                return {}
            
            if n_trials is None:
                n_trials = self.config.max_optimization_trials
            
            logger.info(f"Iniciando optimización de hiperparámetros con {n_trials} trials")
            
            # Crear estudio Optuna
            study_name = f"trading_model_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.study = optuna.create_study(
                direction='maximize',
                study_name=study_name,
                sampler=optuna.samplers.TPESampler(seed=42)
            )
            
            # Función objetivo
            def objective(trial):
                return self._optuna_objective(trial, X_train, y_train, X_val, y_val)
            
            # Optimizar
            self.study.optimize(objective, n_trials=n_trials, timeout=3600)  # 1 hora máximo
            
            # Obtener mejores parámetros
            self.best_hyperparameters = self.study.best_params
            best_score = self.study.best_value
            
            logger.info(f"Optimización completada. Mejor score: {best_score:.4f}")
            logger.info(f"Mejores parámetros: {self.best_hyperparameters}")
            
            return {
                'best_params': self.best_hyperparameters,
                'best_score': best_score,
                'n_trials': len(self.study.trials)
            }
            
        except Exception as e:
            logger.error(f"Error en optimización de hiperparámetros: {e}")
            return {}
    
    def _optuna_objective(
        self, 
        trial, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> float:
        """Función objetivo para Optuna"""
        try:
            # Sugerir hiperparámetros
            params = {
                'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-2, log=True),
                'batch_size': trial.suggest_categorical('batch_size', [16, 32, 64, 128]),
                'epochs': trial.suggest_int('epochs', 30, 100),
                'dropout_rate': trial.suggest_float('dropout_rate', 0.1, 0.5),
            }
            
            # Parámetros específicos según tipo de modelo
            if self.config.model_type == 'lstm':
                params.update({
                    'lstm_units_1': trial.suggest_int('lstm_units_1', 64, 256),
                    'lstm_units_2': trial.suggest_int('lstm_units_2', 32, 128),
                    'dense_units_1': trial.suggest_int('dense_units_1', 32, 128),
                })
            
            # Crear y entrenar modelo con parámetros sugeridos
            model = create_model(self.config.model_type)
            
            # Aplicar parámetros al modelo (esto requeriría modificar las clases de modelo)
            # Por ahora, usar parámetros en training
            training_results = model.train(
                X_train, y_train, X_val, y_val, 
                **params,
                verbose=0  # Silencioso para optimización
            )
            
            if not training_results:
                return 0.0
            
            # Evaluar modelo
            evaluation_results = self.evaluate_model(model, X_val, y_val)
            
            if not evaluation_results:
                return 0.0
            
            # Score combinado (igual que en should_update_current_model)
            accuracy = evaluation_results.get('accuracy', 0)
            f1_score = evaluation_results.get('f1_score', 0)
            sharpe_ratio = evaluation_results.get('sharpe_ratio', 0)
            
            combined_score = (accuracy * 0.4 + f1_score * 0.3 + 
                             min(max(sharpe_ratio / 2.0, 0), 1) * 0.3)
            
            return combined_score
            
        except Exception as e:
            logger.warning(f"Error en trial de optimización: {e}")
            return 0.0
    
    def adaptive_retrain(self) -> bool:
        """Ejecuta reentrenamiento adaptativo si es necesario"""
        try:
            if not self.should_retrain():
                return False
            
            logger.info("Iniciando reentrenamiento adaptativo")
            
            # Preparar datos
            X_train, X_val, y_train, y_val = self.prepare_training_data()
            
            if X_train.shape[0] == 0:
                logger.warning("No hay datos suficientes para reentrenamiento")
                return False
            
            # Optimizar hiperparámetros si está habilitado
            optimization_results = {}
            if self.config.enable_hyperparameter_optimization:
                optimization_results = self.optimize_hyperparameters(
                    X_train, y_train, X_val, y_val,
                    n_trials=min(20, self.config.max_optimization_trials)  # Menos trials para reentrenamiento
                )
            
            # Entrenar nuevo modelo
            training_results = self.train_model(
                X_train=X_train, y_train=y_train,
                X_val=X_val, y_val=y_val
            )
            
            success = bool(training_results.get('model_updated', False))
            
            if success:
                logger.info("Reentrenamiento adaptativo completado exitosamente")
            else:
                logger.warning("Reentrenamiento completado pero modelo no mejoró")
            
            return success
            
        except Exception as e:
            logger.error(f"Error en reentrenamiento adaptativo: {e}")
            return False
    
    def cross_validate_model(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        n_splits: int = 5
    ) -> Dict[str, List[float]]:
        """Realiza validación cruzada temporal"""
        try:
            logger.info(f"Iniciando validación cruzada con {n_splits} splits")
            
            # TimeSeriesSplit para datos temporales
            tscv = TimeSeriesSplit(n_splits=n_splits)
            
            scores = {
                'accuracy': [],
                'precision': [],
                'recall': [],
                'f1_score': [],
                'sharpe_ratio': []
            }
            
            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                logger.info(f"Procesando fold {fold + 1}/{n_splits}")
                
                X_train_fold, X_val_fold = X[train_idx], X[val_idx]
                y_train_fold, y_val_fold = y[train_idx], y[val_idx]
                
                # Crear y entrenar modelo
                model = create_model(self.config.model_type)
                training_results = model.train(
                    X_train_fold, y_train_fold, 
                    X_val_fold, y_val_fold,
                    epochs=50,  # Menos epochs para CV
                    verbose=0
                )
                
                if training_results:
                    # Evaluar
                    evaluation_results = self.evaluate_model(model, X_val_fold, y_val_fold)
                    
                    # Guardar scores
                    for metric in scores.keys():
                        scores[metric].append(evaluation_results.get(metric, 0.0))
            
            # Calcular estadísticas
            cv_results = {}
            for metric, values in scores.items():
                cv_results[f'{metric}_mean'] = np.mean(values)
                cv_results[f'{metric}_std'] = np.std(values)
                cv_results[f'{metric}_scores'] = values
            
            logger.info("Validación cruzada completada")
            for metric in ['accuracy', 'f1_score', 'sharpe_ratio']:
                mean_score = cv_results[f'{metric}_mean']
                std_score = cv_results[f'{metric}_std']
                logger.info(f"{metric}: {mean_score:.3f} ± {std_score:.3f}")
            
            return cv_results
            
        except Exception as e:
            logger.error(f"Error en validación cruzada: {e}")
            return {}
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del estado de entrenamiento"""
        try:
            summary = {
                'current_model_version': self.current_model.model_version if self.current_model else None,
                'last_retrain_time': self.last_retrain_time,
                'trades_since_retrain': self.trades_since_retrain,
                'best_model_score': self.best_model_score,
                'total_training_sessions': len(self.training_history),
                'best_hyperparameters': self.best_hyperparameters,
                'config': {
                    'model_type': self.config.model_type,
                    'retrain_frequency': self.config.retrain_frequency,
                    'performance_threshold': self.config.performance_threshold,
                    'optimization_enabled': self.config.enable_hyperparameter_optimization
                }
            }
            
            # Métricas del modelo actual
            if self.current_model:
                latest_metrics = db_manager.get_latest_model_metrics()
                if latest_metrics:
                    summary['current_model_metrics'] = {
                        'accuracy': latest_metrics.accuracy,
                        'precision': latest_metrics.precision,
                        'recall': latest_metrics.recall,
                        'f1_score': latest_metrics.f1_score,
                        'training_time': latest_metrics.training_time
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de entrenamiento: {e}")
            return {}
    
    def record_trade_result(self, trade_id: int, was_profitable: bool):
        """Registra resultado de un trade para tracking de performance"""
        try:
            self.trades_since_retrain += 1
            
            # Log para debugging
            logger.debug(f"Trade {trade_id} registrado: {'profitable' if was_profitable else 'pérdida'}")
            logger.debug(f"Trades desde último reentrenamiento: {self.trades_since_retrain}")
            
        except Exception as e:
            logger.error(f"Error registrando resultado de trade: {e}")

class AdaptiveTrainer(ModelTrainer):
    """Entrenador adaptativo que ajusta estrategia según condiciones de mercado"""
    
    def __init__(self, config: TrainingConfig = None):
        super().__init__(config)
        self.market_regime_detector = MarketRegimeDetector()
        self.regime_specific_models = {}
        
        logger.info("AdaptiveTrainer inicializado con detección de regímenes")
    
    def train_regime_specific_models(self, symbol: str = "BTCUSDT"):
        """Entrena modelos específicos para diferentes regímenes de mercado"""
        try:
            logger.info("Iniciando entrenamiento de modelos específicos por régimen")
            
            # Obtener datos históricos extendidos
            X, y, df = data_preprocessor.prepare_training_data(
                symbol=symbol,
                days_back=180,  # Más datos para detectar regímenes
                target_method="classification"
            )
            
            if X.shape[0] == 0:
                logger.warning("No hay datos suficientes para entrenamiento por regímenes")
                return
            
            # Detectar regímenes de mercado
            regimes = self.market_regime_detector.detect_regimes(df)
            
            # Entrenar modelo para cada régimen
            for regime in ['bull', 'bear', 'sideways']:
                regime_mask = regimes == regime
                
                if np.sum(regime_mask) < 100:  # Datos insuficientes
                    logger.warning(f"Datos insuficientes para régimen {regime}: {np.sum(regime_mask)} muestras")
                    continue
                
                logger.info(f"Entrenando modelo para régimen {regime} con {np.sum(regime_mask)} muestras")
                
                # Filtrar datos por régimen
                X_regime = X[regime_mask]
                y_regime = y[regime_mask]
                
                # Dividir en train/val
                split_idx = int(X_regime.shape[0] * 0.8)
                X_train, X_val = X_regime[:split_idx], X_regime[split_idx:]
                y_train, y_val = y_regime[:split_idx], y_regime[split_idx:]
                
                # Crear y entrenar modelo para este régimen
                model = create_model(self.config.model_type)
                model.model_version = f"{model.model_type}_{regime}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                training_results = model.train(
                    X_train, y_train, X_val, y_val,
                    epochs=min(80, self.config.max_epochs),  # Menos epochs para modelos específicos
                    verbose=1
                )
                
                if training_results:
                    # Evaluar modelo específico
                    evaluation_results = self.evaluate_model(model, X_val, y_val)
                    
                    if evaluation_results.get('accuracy', 0) > 0.55:  # Solo guardar si es razonablemente bueno
                        self.regime_specific_models[regime] = model
                        # Guardar modelo específico
                        regime_model_path = MODELS_DIR / f"regime_{regime}_{model.model_version}.h5"
                        model.save_model(str(regime_model_path))
                        
                        logger.info(f"Modelo para régimen {regime} entrenado exitosamente: Accuracy={evaluation_results['accuracy']:.3f}")
                    else:
                        logger.warning(f"Modelo para régimen {regime} descartado por baja accuracy: {evaluation_results.get('accuracy', 0):.3f}")
            
            logger.info(f"Entrenamiento por regímenes completado. Modelos exitosos: {len(self.regime_specific_models)}")
            
        except Exception as e:
            logger.error(f"Error entrenando modelos por régimen: {e}")
    
    def get_best_model_for_current_regime(self) -> Optional[TradingModel]:
        """Obtiene el mejor modelo para el régimen de mercado actual"""
        try:
            # Detectar régimen actual
            current_regime = self.market_regime_detector.get_current_regime()
            
            logger.debug(f"Régimen de mercado actual detectado: {current_regime}")
            
            # Retornar modelo específico si existe
            if current_regime in self.regime_specific_models:
                logger.info(f"Usando modelo específico para régimen {current_regime}")
                return self.regime_specific_models[current_regime]
            
            # Fallback al modelo general
            logger.debug("Usando modelo general (no hay modelo específico para régimen actual)")
            return self.current_model
            
        except Exception as e:
            logger.error(f"Error obteniendo modelo para régimen actual: {e}")
            return self.current_model
    
    def adaptive_model_selection(self, symbol: str = "BTCUSDT") -> TradingModel:
        """Selección adaptativa de modelo basada en condiciones actuales"""
        try:
            # Obtener contexto de mercado actual
            market_context = self._get_market_context(symbol)
            
            # Seleccionar modelo basado en contexto
            if market_context['volatility'] > 0.05:  # Alta volatilidad
                # Preferir modelo más conservador o específico para alta volatilidad
                logger.info("Alta volatilidad detectada, priorizando modelo conservador")
                return self.get_best_model_for_current_regime()
            
            elif market_context['trend_strength'] > 0.7:  # Tendencia fuerte
                # Usar modelo optimizado para tendencias
                logger.info("Tendencia fuerte detectada, usando modelo de régimen específico")
                return self.get_best_model_for_current_regime()
            
            else:
                # Condiciones normales, usar mejor modelo general
                return self.current_model or self.get_best_model_for_current_regime()
            
        except Exception as e:
            logger.error(f"Error en selección adaptativa de modelo: {e}")
            return self.current_model
    
    def _get_market_context(self, symbol: str) -> Dict[str, float]:
        """Obtiene contexto actual del mercado"""
        try:
            # Obtener datos recientes
            recent_data = db_manager.get_latest_market_data(symbol, 100)
            
            if recent_data.empty:
                return {'volatility': 0.03, 'trend_strength': 0.5, 'volume_ratio': 1.0}
            
            # Calcular métricas de contexto
            returns = recent_data['close'].pct_change().dropna()
            volatility = returns.std()
            
            # Fuerza de tendencia (basada en SMA)
            sma_20 = recent_data['close'].rolling(20).mean()
            sma_50 = recent_data['close'].rolling(50).mean()
            
            if len(sma_20) > 0 and len(sma_50) > 0:
                trend_strength = abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1]
            else:
                trend_strength = 0.5
            
            # Ratio de volumen
            avg_volume = recent_data['volume'].rolling(20).mean()
            current_volume = recent_data['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1.0
            
            return {
                'volatility': volatility,
                'trend_strength': min(trend_strength, 1.0),
                'volume_ratio': volume_ratio
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto de mercado: {e}")
            return {'volatility': 0.03, 'trend_strength': 0.5, 'volume_ratio': 1.0}

class ReinforcementLearningTrainer(ModelTrainer):
    """Entrenador con aprendizaje por refuerzo para optimizar estrategia de trading"""
    
    def __init__(self, config: TrainingConfig = None):
        super().__init__(config)
        self.action_space = 3  # SELL=0, HOLD=1, BUY=2
        self.state_size = None
        self.q_network = None
        self.target_network = None
        self.experience_buffer = []
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.learning_rate = 0.001
        self.gamma = 0.95  # Discount factor
        self.batch_size = 32
        self.update_target_frequency = 100
        self.steps_done = 0
        
        logger.info("ReinforcementLearningTrainer inicializado")
    
    def build_q_network(self, state_size: int) -> tf.keras.Model:
        """Construye red Q para aprendizaje por refuerzo"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(state_size,)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(self.action_space, activation='linear')
        ])
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse'
        )
        
        return model
    
    def train_with_reinforcement_learning(
        self, 
        env_data: pd.DataFrame,
        episodes: int = 100,
        max_steps_per_episode: int = 1000
    ):
        """Entrena usando aprendizaje por refuerzo"""
        try:
            logger.info(f"Iniciando entrenamiento RL con {episodes} episodios")
            
            # Preparar datos como entorno
            states, rewards, next_states = self.prepare_rl_environment(env_data)
            
            if len(states) == 0:
                logger.warning("No hay datos suficientes para entrenamiento RL")
                return
            
            self.state_size = states.shape[1]
            
            # Inicializar redes Q
            if self.q_network is None:
                self.q_network = self.build_q_network(self.state_size)
                self.target_network = self.build_q_network(self.state_size)
                self.update_target_network()
            
            # Entrenamiento episódico
            episode_rewards = []
            
            for episode in range(episodes):
                total_reward = 0
                steps_in_episode = min(len(states) - 1, max_steps_per_episode)
                
                # Seleccionar punto de inicio aleatorio
                start_idx = np.random.randint(0, max(1, len(states) - steps_in_episode))
                
                for step in range(steps_in_episode):
                    idx = start_idx + step
                    if idx >= len(states) - 1:
                        break
                    
                    state = states[idx]
                    next_state = states[idx + 1]
                    
                    # Seleccionar acción (epsilon-greedy)
                    action = self.select_action(state)
                    
                    # Calcular recompensa basada en acción y resultado real
                    reward = self.calculate_reward(action, rewards[idx], states[idx], next_state)
                    total_reward += reward
                    
                    # Almacenar experiencia
                    is_terminal = (step == steps_in_episode - 1) or (idx == len(states) - 2)
                    self.store_experience(state, action, reward, next_state, is_terminal)
                    
                    # Entrenar si tenemos suficientes experiencias
                    if len(self.experience_buffer) >= self.batch_size:
                        self.replay_experience()
                    
                    self.steps_done += 1
                    
                    # Actualizar red objetivo periódicamente
                    if self.steps_done % self.update_target_frequency == 0:
                        self.update_target_network()
                
                episode_rewards.append(total_reward)
                
                # Actualizar epsilon
                if self.epsilon > self.epsilon_min:
                    self.epsilon *= self.epsilon_decay
                
                # Log progreso
                if episode % 10 == 0:
                    avg_reward = np.mean(episode_rewards[-10:])
                    logger.info(f"Episodio {episode}: Reward promedio (últimos 10) = {avg_reward:.2f}, Epsilon = {self.epsilon:.3f}")
            
            # Guardar modelo RL
            self.save_rl_model()
            
            logger.info("Entrenamiento RL completado")
            return {
                'episode_rewards': episode_rewards,
                'final_epsilon': self.epsilon,
                'total_steps': self.steps_done
            }
            
        except Exception as e:
            logger.error(f"Error en entrenamiento RL: {e}")
            return {}
    
    def prepare_rl_environment(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepara datos como entorno de RL"""
        try:
            # Calcular indicadores técnicos básicos para estados
            data = data.copy()
            
            # Returns y volatilidad
            data['returns'] = data['close'].pct_change()
            data['volatility'] = data['returns'].rolling(10).std()
            
            # Medias móviles
            data['sma_5'] = data['close'].rolling(5).mean()
            data['sma_20'] = data['close'].rolling(20).mean()
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            # Normalizar precio por media móvil
            data['price_normalized'] = data['close'] / data['sma_20']
            data['volume_normalized'] = data['volume'] / data['volume'].rolling(20).mean()
            
            # Crear estados (features normalizadas)
            feature_columns = [
                'returns', 'volatility', 'rsi', 'price_normalized', 'volume_normalized'
            ]
            
            # Limpiar datos
            data_clean = data[feature_columns].dropna()
            
            # Normalizar estados
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            states = scaler.fit_transform(data_clean.values)
            
            # Calcular recompensas (retornos futuros)
            future_returns = data['returns'].shift(-1).dropna()
            
            # Alinear estados y recompensas
            min_length = min(len(states), len(future_returns))
            states = states[:min_length]
            rewards = future_returns.values[:min_length]
            
            # Next states
            next_states = np.roll(states, -1, axis=0)
            next_states[-1] = states[-1]  # Último estado igual al anterior
            
            logger.info(f"Entorno RL preparado: {len(states)} estados, {len(feature_columns)} features")
            
            return states, rewards, next_states
            
        except Exception as e:
            logger.error(f"Error preparando entorno RL: {e}")
            return np.array([]), np.array([]), np.array([])
    
    def select_action(self, state: np.ndarray) -> int:
        """Selecciona acción usando epsilon-greedy"""
        if np.random.random() <= self.epsilon:
            return np.random.choice(self.action_space)
        
        q_values = self.q_network.predict(state.reshape(1, -1), verbose=0)
        return np.argmax(q_values[0])
    
    def calculate_reward(
        self, 
        action: int, 
        market_return: float, 
        current_state: np.ndarray,
        next_state: np.ndarray
    ) -> float:
        """Calcula recompensa basada en acción y retorno del mercado"""
        try:
            # Recompensa base por dirección correcta
            base_reward = 0
            
            if action == 2 and market_return > 0:  # BUY correcto
                base_reward = market_return * 100  # Amplificar recompensa
            elif action == 0 and market_return < 0:  # SELL correcto
                base_reward = abs(market_return) * 100
            elif action == 1:  # HOLD
                # Recompensa pequeña por HOLD, penalización si había oportunidad clara
                if abs(market_return) < 0.005:  # Movimiento pequeño
                    base_reward = 0.1
                else:
                    base_reward = -abs(market_return) * 50  # Penalización por no actuar
            else:  # Acción incorrecta
                base_reward = -abs(market_return) * 100
            
            # Penalizaciones adicionales
            # Penalizar trading excesivo (si la acción anterior también fue trade)
            if hasattr(self, '_last_action') and self._last_action != 1 and action != 1:
                base_reward -= 0.5  # Penalización por overtrading
            
            # Bonificación por consistencia
            if hasattr(self, '_consecutive_correct') and base_reward > 0:
                base_reward *= (1 + self._consecutive_correct * 0.1)
            
            # Actualizar tracking
            self._last_action = action
            if not hasattr(self, '_consecutive_correct'):
                self._consecutive_correct = 0
            
            if base_reward > 0:
                self._consecutive_correct += 1
            else:
                self._consecutive_correct = 0
            
            return np.clip(base_reward, -10, 10)  # Limitar recompensas
            
        except Exception as e:
            logger.error(f"Error calculando recompensa: {e}")
            return 0.0
    
    def store_experience(self, state, action, reward, next_state, done):
        """Almacena experiencia en buffer"""
        self.experience_buffer.append((state, action, reward, next_state, done))
        
        # Mantener buffer de tamaño fijo
        if len(self.experience_buffer) > 10000:
            self.experience_buffer.pop(0)
    
    def replay_experience(self):
        """Entrena red Q con experiencias almacenadas"""
        if len(self.experience_buffer) < self.batch_size:
            return
        
        try:
            # Muestrear batch aleatorio
            indices = np.random.choice(len(self.experience_buffer), self.batch_size, replace=False)
            batch = [self.experience_buffer[i] for i in indices]
            
            states = np.array([e[0] for e in batch])
            actions = np.array([e[1] for e in batch])
            rewards = np.array([e[2] for e in batch])
            next_states = np.array([e[3] for e in batch])
            dones = np.array([e[4] for e in batch])
            
            # Calcular targets Q
            current_q_values = self.q_network.predict(states, verbose=0)
            next_q_values = self.target_network.predict(next_states, verbose=0)
            
            targets = current_q_values.copy()
            
            for i in range(self.batch_size):
                if dones[i]:
                    targets[i][actions[i]] = rewards[i]
                else:
                    targets[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
            
            # Entrenar red Q
            self.q_network.fit(states, targets, epochs=1, verbose=0)
            
        except Exception as e:
            logger.error(f"Error en replay de experiencia: {e}")
    
    def update_target_network(self):
        """Actualiza red objetivo"""
        if self.target_network is not None:
            self.target_network.set_weights(self.q_network.get_weights())
    
    def predict_action(self, state: np.ndarray) -> Tuple[int, float]:
        """Predice acción con confianza"""
        try:
            q_values = self.q_network.predict(state.reshape(1, -1), verbose=0)
            action = np.argmax(q_values[0])
            confidence = np.max(q_values[0]) - np.mean(q_values[0])  # Diferencia con promedio
            
            return action, confidence
            
        except Exception as e:
            logger.error(f"Error prediciendo acción RL: {e}")
            return 1, 0.0  # HOLD por defecto
    
    def save_rl_model(self):
        """Guarda modelo de RL"""
        try:
            rl_model_path = MODELS_DIR / f"rl_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
            self.q_network.save(str(rl_model_path))
            
            # Guardar parámetros RL
            rl_params = {
                'epsilon': self.epsilon,
                'steps_done': self.steps_done,
                'state_size': self.state_size,
                'action_space': self.action_space,
                'learning_rate': self.learning_rate,
                'gamma': self.gamma
            }
            
            params_path = rl_model_path.with_suffix('.json')
            with open(params_path, 'w') as f:
                json.dump(rl_params, f, indent=2)
            
            logger.info(f"Modelo RL guardado: {rl_model_path}")
            
        except Exception as e:
            logger.error(f"Error guardando modelo RL: {e}")

class MarketRegimeDetector:
    """Detector de regímenes de mercado para entrenamiento adaptativo"""
    
    def __init__(self):
        self.regime_cache = {}
        self.cache_timeout = 3600  # 1 hora
        
    def detect_regimes(self, data: pd.DataFrame) -> np.ndarray:
        """Detecta regímenes de mercado en datos históricos"""
        try:
            if len(data) < 50:
                return np.array(['sideways'] * len(data))
            
            data = data.copy()
            
            # Calcular indicadores de régimen
            data['sma_20'] = data['close'].rolling(20).mean()
            data['sma_50'] = data['close'].rolling(50).mean()
            data['volatility'] = data['close'].pct_change().rolling(20).std()
            
            # Bollinger Bands para detectar volatilidad
            data['bb_upper'] = data['sma_20'] + (2 * data['volatility'] * data['sma_20'])
            data['bb_lower'] = data['sma_20'] - (2 * data['volatility'] * data['sma_20'])
            
            regimes = []
            
            for i in range(len(data)):
                if pd.isna(data['sma_50'].iloc[i]) or pd.isna(data['volatility'].iloc[i]):
                    regimes.append('sideways')
                    continue
                
                price = data['close'].iloc[i]
                sma_20 = data['sma_20'].iloc[i]
                sma_50 = data['sma_50'].iloc[i]
                volatility = data['volatility'].iloc[i]
                
                # Criterios mejorados para clasificar regímenes
                price_vs_sma50 = (price - sma_50) / sma_50
                sma_trend = (sma_20 - sma_50) / sma_50
                
                # Bull market: precio > SMA50, SMAs en tendencia alcista, volatilidad moderada
                if (price_vs_sma50 > 0.02 and sma_trend > 0.01 and volatility < 0.05):
                    regimes.append('bull')
                # Bear market: precio < SMA50, SMAs en tendencia bajista
                elif (price_vs_sma50 < -0.02 and sma_trend < -0.01):
                    regimes.append('bear')
                # High volatility regime
                elif volatility > 0.06:
                    regimes.append('high_vol')
                # Sideways: otros casos
                else:
                    regimes.append('sideways')
            
            return np.array(regimes)
            
        except Exception as e:
            logger.error(f"Error detectando regímenes: {e}")
            return np.array(['sideways'] * len(data))
    
    def get_current_regime(self, symbol: str = "BTCUSDT") -> str:
        """Obtiene el régimen de mercado actual"""
        try:
            # Verificar cache
            cache_key = f"{symbol}_{int(time.time() / self.cache_timeout)}"
            if cache_key in self.regime_cache:
                return self.regime_cache[cache_key]
            
            # Obtener datos recientes
            recent_data = db_manager.get_latest_market_data(symbol, 100)
            
            if recent_data.empty:
                return 'sideways'
            
            # Detectar régimen en datos recientes
            regimes = self.detect_regimes(recent_data)
            
            # Retornar régimen más común en últimos 20 períodos
            recent_regimes = regimes[-20:] if len(regimes) >= 20 else regimes
            unique, counts = np.unique(recent_regimes, return_counts=True)
            current_regime = unique[np.argmax(counts)]
            
            # Guardar en cache
            self.regime_cache[cache_key] = current_regime
            
            return current_regime
            
        except Exception as e:
            logger.error(f"Error obteniendo régimen actual: {e}")
            return 'sideways'
    
    def get_regime_statistics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Obtiene estadísticas de distribución de regímenes"""
        try:
            regimes = self.detect_regimes(data)
            unique, counts = np.unique(regimes, return_counts=True)
            
            total = len(regimes)
            statistics = {}
            
            for regime, count in zip(unique, counts):
                statistics[f'{regime}_pct'] = (count / total) * 100
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de régimen: {e}")
            return {}