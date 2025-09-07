"""
🎓 adaptive_trainer.py - Sistema de Entrenamiento Continuo

Sistema de entrenamiento adaptativo que aprende continuamente de los resultados
de trading y se reentrena automáticamente para mejorar performance.

Autor: Alex B
Fecha: 2025-01-07
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
import json
import os
from pathlib import Path
import pickle

# Imports del proyecto
from models.neural_network import TradingModel
from models.prediction_engine import prediction_engine
from data.preprocessor import data_preprocessor
from data.database import db_manager
from config.config_loader import user_config

logger = logging.getLogger(__name__)

class AdaptiveTrainer:
    """
    Sistema de entrenamiento adaptativo para el modelo de ML.
    
    Responsabilidades:
    - Entrenamiento inicial con datos históricos
    - Online learning con nuevos datos de trades
    - Performance monitoring en tiempo real
    - Auto-reentrenamiento basado en resultados
    - A/B testing de diferentes versiones
    - Checkpoint management automático
    """
    
    def __init__(self):
        self.config = user_config
        self.model = None
        self.training_history = []
        self.performance_metrics = {}
        self.retrain_threshold = 0.6  # Reentrenar si accuracy < 60%
        self.min_samples_retrain = 100  # Mínimo 100 muestras para reentrenar
        self.update_frequency = 50  # Actualizar cada 50 trades
        
        # Configuración de entrenamiento
        self.training_config = self.config.get_value(['ai_model_settings', 'training'], {})
        self.initial_epochs = self.training_config.get('initial_epochs', 100)
        self.batch_size = self.training_config.get('batch_size', 64)
        self.learning_rate = self.training_config.get('learning_rate', 0.001)
        
        # Configuración de online learning
        self.online_config = self.config.get_value(['ai_model_settings', 'online_learning'], {})
        self.online_enabled = self.online_config.get('enabled', True)
        self.update_frequency = self.online_config.get('update_frequency', 50)
        self.learning_rate_decay = self.online_config.get('learning_rate_decay', 0.95)
        
        # Directorios
        self.models_dir = Path("models/saved_models")
        self.checkpoints_dir = Path("models/checkpoints")
        self.experiments_dir = Path("models/experiments")
        
        # Crear directorios si no existen
        self._create_directories()
        
        # Inicializar modelo
        self._initialize_model()
        
        logger.info("AdaptiveTrainer inicializado")
    
    def _create_directories(self):
        """Crea directorios necesarios"""
        for directory in [self.models_dir, self.checkpoints_dir, self.experiments_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _initialize_model(self):
        """Inicializa el modelo de ML"""
        try:
            self.model = TradingModel()
            logger.info("Modelo inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo: {e}")
            self.model = None
    
    async def train_initial_model(self, symbol: str, days_back: int = 365) -> Dict[str, Any]:
        """
        Entrena el modelo inicial con datos históricos
        
        Args:
            symbol: Símbolo para entrenar (ej: BTCUSDT)
            days_back: Días de datos históricos a usar
            
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            logger.info(f"Iniciando entrenamiento inicial para {symbol} ({days_back} días)")
            
            if not self.model:
                raise Exception("Modelo no inicializado")
            
            # Preparar datos de entrenamiento
            X, y, df = data_preprocessor.prepare_training_data(
                symbol=symbol,
                days_back=days_back,
                target_method="classification"
            )
            
            if X.shape[0] == 0:
                raise Exception("No hay datos suficientes para entrenamiento")
            
            logger.info(f"Datos preparados: {X.shape[0]} muestras, {X.shape[1]} features")
            
            # Dividir datos
            split_idx = int(0.8 * len(X))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Entrenar modelo
            history = await self._train_model(
                X_train, y_train, X_val, y_val,
                epochs=self.initial_epochs,
                symbol=symbol
            )
            
            # Evaluar modelo
            val_accuracy = self._evaluate_model(X_val, y_val)
            
            # Guardar modelo
            model_path = self._save_model(symbol, "initial")
            
            # Guardar métricas
            training_result = {
                'symbol': symbol,
                'model_type': 'initial',
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'features_count': X.shape[1],
                'epochs_trained': len(history.history['loss']),
                'final_accuracy': history.history['accuracy'][-1],
                'final_loss': history.history['loss'][-1],
                'validation_accuracy': val_accuracy,
                'model_path': model_path,
                'training_time': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            self.training_history.append(training_result)
            self.performance_metrics[symbol] = val_accuracy
            
            logger.info(f"Entrenamiento inicial completado. Accuracy: {val_accuracy:.3f}")
            return training_result
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento inicial: {e}")
            return {
                'symbol': symbol,
                'status': 'failed',
                'error': str(e),
                'training_time': datetime.now().isoformat()
            }
    
    async def online_learning_update(self, new_data: Dict[str, Any], trade_results: List[Dict]) -> Dict[str, Any]:
        """
        Actualización de aprendizaje online con nuevos datos
        
        Args:
            new_data: Nuevos datos de mercado
            trade_results: Resultados de trades recientes
            
        Returns:
            Dict con resultados de la actualización
        """
        try:
            if not self.online_enabled:
                return {'status': 'disabled'}
            
            logger.info(f"🔄 Actualización online learning: {len(trade_results)} trades")
            
            # Verificar si necesitamos reentrenar
            if not self._should_retrain(trade_results):
                return {'status': 'no_retrain_needed'}
            
            # Preparar datos para reentrenamiento
            X_new, y_new = self._prepare_online_data(new_data, trade_results)
            
            if len(X_new) < self.min_samples_retrain:
                return {'status': 'insufficient_data', 'samples': len(X_new)}
            
            # Reentrenar modelo
            retrain_result = await self._retrain_model(X_new, y_new, trade_results)
            
            # Actualizar métricas
            self._update_performance_metrics(trade_results)
            
            logger.info("Online learning update completado")
            return retrain_result
            
        except Exception as e:
            logger.error(f"❌ Error en online learning update: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _train_model(self, X_train: np.ndarray, y_train: np.ndarray, 
                          X_val: np.ndarray, y_val: np.ndarray, 
                          epochs: int, symbol: str) -> Any:
        """Entrena el modelo con los datos proporcionados"""
        try:
            # Configurar callbacks
            callbacks = self._create_callbacks(symbol)
            
            # Entrenar modelo
            history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=self.batch_size,
                callbacks=callbacks,
                verbose=1
            )
            
            return history
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            raise
    
    def _evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        """Evalúa el modelo con datos de test"""
        try:
            if not self.model:
                return 0.0
            
            # Evaluar modelo
            test_loss, test_accuracy = self.model.evaluate(X_test, y_test, verbose=0)
            return test_accuracy
            
        except Exception as e:
            logger.error(f"Error evaluando modelo: {e}")
            return 0.0
    
    def _create_callbacks(self, symbol: str) -> List:
        """Crea callbacks para el entrenamiento"""
        callbacks = []
        
        # Early stopping
        from tensorflow.keras.callbacks import EarlyStopping
        early_stopping = EarlyStopping(
            monitor='val_accuracy',
            patience=15,
            restore_best_weights=True,
            verbose=1
        )
        callbacks.append(early_stopping)
        
        # Model checkpoint
        from tensorflow.keras.callbacks import ModelCheckpoint
        checkpoint_path = self.checkpoints_dir / f"{symbol}_checkpoint.h5"
        checkpoint = ModelCheckpoint(
            str(checkpoint_path),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
        callbacks.append(checkpoint)
        
        # Learning rate scheduler
        from tensorflow.keras.callbacks import ReduceLROnPlateau
        lr_scheduler = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=1e-7,
            verbose=1
        )
        callbacks.append(lr_scheduler)
        
        return callbacks
    
    def _save_model(self, symbol: str, model_type: str) -> str:
        """Guarda el modelo entrenado"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"{symbol}_{model_type}_{timestamp}.h5"
            model_path = self.models_dir / model_filename
            
            # Guardar modelo
            self.model.save(str(model_path))
            
            # Guardar metadatos
            metadata = {
                'symbol': symbol,
                'model_type': model_type,
                'timestamp': timestamp,
                'features_count': self.model.input_shape[1] if hasattr(self.model, 'input_shape') else 0,
                'model_path': str(model_path)
            }
            
            metadata_path = model_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"💾 Modelo guardado: {model_path}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {e}")
            return ""
    
    def _should_retrain(self, trade_results: List[Dict]) -> bool:
        """Determina si el modelo necesita reentrenamiento"""
        try:
            if len(trade_results) < self.update_frequency:
                return False
            
            # Calcular accuracy reciente
            recent_trades = trade_results[-self.update_frequency:]
            correct_predictions = sum(1 for trade in recent_trades if trade.get('prediction_correct', False))
            recent_accuracy = correct_predictions / len(recent_trades)
            
            # Verificar si accuracy está por debajo del threshold
            needs_retrain = recent_accuracy < self.retrain_threshold
            
            logger.info(f"Accuracy reciente: {recent_accuracy:.3f}, Threshold: {self.retrain_threshold}")
            
            return needs_retrain
            
        except Exception as e:
            logger.error(f"Error verificando necesidad de reentrenamiento: {e}")
            return False
    
    def _prepare_online_data(self, new_data: Dict[str, Any], trade_results: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara datos para aprendizaje online"""
        try:
            # Combinar datos de mercado con resultados de trades
            X_list = []
            y_list = []
            
            for trade in trade_results:
                # Obtener features del trade
                features = trade.get('features')
                if features is not None:
                    X_list.append(features)
                    
                    # Crear target basado en resultado
                    pnl = trade.get('pnl', 0)
                    if pnl > 0:
                        y_list.append(2)  # BUY
                    elif pnl < 0:
                        y_list.append(0)  # SELL
                    else:
                        y_list.append(1)  # HOLD
            
            if len(X_list) == 0:
                return np.array([]), np.array([])
            
            X = np.array(X_list)
            y = np.array(y_list)
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparando datos online: {e}")
            return np.array([]), np.array([])
    
    async def _retrain_model(self, X_new: np.ndarray, y_new: np.ndarray, trade_results: List[Dict]) -> Dict[str, Any]:
        """Reentrena el modelo con nuevos datos"""
        try:
            logger.info(f"🔄 Reentrenando modelo con {len(X_new)} nuevas muestras")
            
            # Ajustar learning rate para online learning
            original_lr = self.model.optimizer.learning_rate.numpy()
            new_lr = original_lr * self.learning_rate_decay
            self.model.optimizer.learning_rate.assign(new_lr)
            
            # Reentrenar con nuevos datos
            history = self.model.fit(
                X_new, y_new,
                epochs=20,  # Pocas épocas para online learning
                batch_size=min(self.batch_size, len(X_new)),
                verbose=1
            )
            
            # Guardar modelo actualizado
            model_path = self._save_model("ONLINE", "retrained")
            
            # Restaurar learning rate original
            self.model.optimizer.learning_rate.assign(original_lr)
            
            retrain_result = {
                'status': 'completed',
                'samples_used': len(X_new),
                'epochs': len(history.history['loss']),
                'final_accuracy': history.history['accuracy'][-1],
                'model_path': model_path,
                'retrain_time': datetime.now().isoformat()
            }
            
            logger.info("Reentrenamiento completado")
            return retrain_result
            
        except Exception as e:
            logger.error(f"Error en reentrenamiento: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _update_performance_metrics(self, trade_results: List[Dict]):
        """Actualiza métricas de performance"""
        try:
            # Calcular métricas recientes
            recent_trades = trade_results[-self.update_frequency:]
            
            total_trades = len(recent_trades)
            profitable_trades = sum(1 for trade in recent_trades if trade.get('pnl', 0) > 0)
            win_rate = profitable_trades / total_trades if total_trades > 0 else 0
            
            total_pnl = sum(trade.get('pnl', 0) for trade in recent_trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            # Actualizar métricas
            self.performance_metrics.update({
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'last_update': datetime.now().isoformat()
            })
            
            logger.info(f"Métricas actualizadas: Win rate: {win_rate:.3f}, Avg PnL: {avg_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    async def get_training_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del entrenamiento"""
        try:
            return {
                'model_initialized': self.model is not None,
                'online_learning_enabled': self.online_enabled,
                'retrain_threshold': self.retrain_threshold,
                'min_samples_retrain': self.min_samples_retrain,
                'update_frequency': self.update_frequency,
                'training_history_count': len(self.training_history),
                'performance_metrics': self.performance_metrics,
                'last_training': self.training_history[-1] if self.training_history else None
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica salud del sistema de entrenamiento"""
        try:
            health = {
                'status': 'healthy',
                'model_initialized': self.model is not None,
                'online_learning_enabled': self.online_enabled,
                'directories_exist': all(d.exists() for d in [self.models_dir, self.checkpoints_dir]),
                'training_history_count': len(self.training_history),
                'errors': []
            }
            
            # Verificar modelo
            if not self.model:
                health['errors'].append("Modelo no inicializado")
                health['status'] = 'degraded'
            
            # Verificar directorios
            if not all(d.exists() for d in [self.models_dir, self.checkpoints_dir]):
                health['errors'].append("Directorios de modelos no existen")
                health['status'] = 'degraded'
            
            return health
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Instancia global del entrenador adaptativo
adaptive_trainer = AdaptiveTrainer()

# Funciones de conveniencia
async def train_initial_model(symbol: str, days_back: int = 365) -> Dict[str, Any]:
    """Función de conveniencia para entrenamiento inicial"""
    return await adaptive_trainer.train_initial_model(symbol, days_back)

async def online_learning_update(new_data: Dict[str, Any], trade_results: List[Dict]) -> Dict[str, Any]:
    """Función de conveniencia para actualización online"""
    return await adaptive_trainer.online_learning_update(new_data, trade_results)

async def get_training_status() -> Dict[str, Any]:
    """Función de conveniencia para obtener estado"""
    return await adaptive_trainer.get_training_status()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await adaptive_trainer.health_check()
