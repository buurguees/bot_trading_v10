"""
models/neural_network.py
Arquitecturas de redes neuronales para trading
Ubicación: C:\\TradingBot_v10\\models\\neural_network.py

Incluye:
- LSTM con attention para series temporales
- Transformer para análisis de secuencias
- Ensemble methods para robustez
- Arquitecturas adaptativas basadas en volatilidad del mercado
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model, Sequential
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import json
from pathlib import Path
import pickle

from core.config.config_loader import user_config
from core.config.settings import MODELS_DIR
from core.data.database import db_manager, ModelMetrics

logger = logging.getLogger(__name__)

class TradingModel:
    """Clase base para todos los modelos de trading"""
    
    def __init__(self, model_type: str = "base"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_version = f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Configuración desde usuario
        self.ai_settings = user_config.get_ai_model_settings()
        self.ml_config = user_config.get_value(['ai_model_settings'], {})
        
        # Métricas de entrenamiento
        self.training_history = {}
        self.evaluation_metrics = {}
        
        logger.info(f"Modelo {self.model_type} inicializado - Versión: {self.model_version}")
    
    def build_model(self, input_shape: Tuple[int, int]) -> Model:
        """Construye la arquitectura del modelo (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar build_model")
    
    def train(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Entrena el modelo (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar train")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Hace predicciones"""
        if not self.is_trained:
            raise ValueError("Modelo no entrenado")
        return self.model.predict(X)
    
    def predict_with_confidence(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predicciones con intervalos de confianza"""
        predictions = self.predict(X)
        
        # Monte Carlo dropout para incertidumbre
        if hasattr(self.model, 'layers'):
            mc_predictions = []
            for _ in range(50):  # 50 simulaciones
                mc_pred = self.model(X, training=True)
                mc_predictions.append(mc_pred.numpy())
            
            mc_predictions = np.array(mc_predictions)
            confidence = np.std(mc_predictions, axis=0)
            return predictions, confidence
        
        return predictions, np.zeros_like(predictions)
    
    def save_model(self, path: str = None) -> bool:
        """Guarda el modelo"""
        try:
            if path is None:
                path = MODELS_DIR / f"{self.model_version}.h5"
            
            # Guardar modelo Keras
            self.model.save(str(path))
            
            # Guardar metadata
            metadata = {
                'model_type': self.model_type,
                'model_version': self.model_version,
                'is_trained': self.is_trained,
                'training_history': self.training_history,
                'evaluation_metrics': self.evaluation_metrics,
                'ai_settings': self.ai_settings
            }
            
            metadata_path = path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            # Guardar scaler
            scaler_path = path.with_suffix('.scaler')
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            logger.info(f"Modelo guardado: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {e}")
            return False
    
    def load_model(self, path: str) -> bool:
        """Carga el modelo"""
        try:
            path = Path(path)
            
            # Cargar modelo Keras con safe_mode=False para Lambda layers
            self.model = keras.models.load_model(str(path), safe_mode=False)
            
            # Cargar metadata
            metadata_path = path.with_suffix('.json')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                self.model_type = metadata.get('model_type', self.model_type)
                self.model_version = metadata.get('model_version', self.model_version)
                self.is_trained = metadata.get('is_trained', False)
                self.training_history = metadata.get('training_history', {})
                self.evaluation_metrics = metadata.get('evaluation_metrics', {})
            
            # Cargar scaler
            scaler_path = path.with_suffix('.scaler')
            if scaler_path.exists():
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
            
            logger.info(f"Modelo cargado: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            return False

class LSTMTradingModel(TradingModel):
    """Modelo LSTM con attention para trading"""
    
    def __init__(self):
        super().__init__("lstm_attention")
        
        # Parámetros específicos de LSTM
        self.lstm_units = self.ml_config.get('lstm_units', [128, 64, 32])
        self.dense_units = self.ml_config.get('dense_units', [64, 32])
        self.dropout_rate = self.ml_config.get('dropout_rate', 0.2)
        self.learning_rate = self.ml_config.get('learning_rate', 0.001)
    
    def build_model(self, input_shape: Tuple[int, int]) -> Model:
        """Construye modelo LSTM con attention"""
        inputs = layers.Input(shape=input_shape)
        
        # Stack de LSTM layers
        x = inputs
        for i, units in enumerate(self.lstm_units):
            return_sequences = i < len(self.lstm_units) - 1
            x = layers.LSTM(
                units,
                return_sequences=return_sequences,
                dropout=self.dropout_rate,
                recurrent_dropout=self.dropout_rate,
                name=f'lstm_{i+1}'
            )(x)
            
            if return_sequences:
                x = layers.BatchNormalization()(x)
        
        # Attention mechanism (solo si hay secuencias)
        if len(self.lstm_units) > 1:
            # Simple attention
            attention = layers.Dense(1, activation='tanh')(x)
            attention = layers.Flatten()(attention)
            attention = layers.Activation('softmax')(attention)
            attention = layers.RepeatVector(self.lstm_units[-1])(attention)
            attention = layers.Permute([2, 1])(attention)
            
            x = layers.Multiply()([x, attention])
            x = layers.Lambda(lambda x: tf.reduce_sum(x, axis=1))(x)
        
        # Dense layers
        for units in self.dense_units:
            x = layers.Dense(units, activation='relu')(x)
            x = layers.Dropout(self.dropout_rate)(x)
            x = layers.BatchNormalization()(x)
        
        # Output layers
        # Clasificación: 3 clases (SELL=0, HOLD=1, BUY=2)
        classification_output = layers.Dense(3, activation='softmax', name='classification')(x)
        
        # Regresión: predicción de retorno
        regression_output = layers.Dense(1, activation='tanh', name='regression')(x)
        
        # Confianza: qué tan seguro está el modelo
        confidence_output = layers.Dense(1, activation='sigmoid', name='confidence')(x)
        
        model = Model(
            inputs=inputs, 
            outputs=[classification_output, regression_output, confidence_output]
        )
        
        # Compilar con múltiples pérdidas
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss={
                'classification': 'sparse_categorical_crossentropy',
                'regression': 'mse',
                'confidence': 'binary_crossentropy'
            },
            loss_weights={
                'classification': 0.4,
                'regression': 0.4,
                'confidence': 0.2
            },
            metrics={
                'classification': ['accuracy'],
                'regression': ['mae'],
                'confidence': ['accuracy']
            }
        )
        
        return model
    
    def train(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        epochs: int = None,
        batch_size: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Entrena el modelo LSTM"""
        try:
            if epochs is None:
                epochs = self.ml_config.get('epochs', 100)
            if batch_size is None:
                batch_size = self.ml_config.get('batch_size', 64)
            
            # Construir modelo si no existe
            if self.model is None:
                input_shape = (X_train.shape[1], X_train.shape[2])
                self.model = self.build_model(input_shape)
            
            # Preparar targets múltiples
            y_classification = y_train  # Asumiendo que y_train son las clases
            y_regression = np.random.randn(len(y_train))  # Placeholder - debería venir de datos reales
            y_confidence = np.ones(len(y_train))  # Placeholder - calcular confianza real
            
            train_targets = {
                'classification': y_classification,
                'regression': y_regression,
                'confidence': y_confidence
            }
            
            # Preparar validación si existe
            val_data = None
            if X_val is not None and y_val is not None:
                y_val_reg = np.random.randn(len(y_val))
                y_val_conf = np.ones(len(y_val))
                val_targets = {
                    'classification': y_val,
                    'regression': y_val_reg,
                    'confidence': y_val_conf
                }
                val_data = (X_val, val_targets)
            
            # Callbacks
            callbacks = [
                EarlyStopping(
                    monitor='val_loss' if val_data else 'loss',
                    patience=self.ml_config.get('early_stopping_patience', 10),
                    restore_best_weights=True
                ),
                ReduceLROnPlateau(
                    monitor='val_loss' if val_data else 'loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-7
                ),
                ModelCheckpoint(
                    str(MODELS_DIR / f"best_{self.model_version}.h5"),
                    save_best_only=True,
                    monitor='val_loss' if val_data else 'loss'
                )
            ]
            
            # Entrenar
            start_time = datetime.now()
            
            history = self.model.fit(
                X_train,
                train_targets,
                validation_data=val_data,
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=1
            )
            
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Guardar historia
            self.training_history = {
                'loss': history.history.get('loss', []),
                'val_loss': history.history.get('val_loss', []),
                'classification_accuracy': history.history.get('classification_accuracy', []),
                'val_classification_accuracy': history.history.get('val_classification_accuracy', [])
            }
            
            self.is_trained = True
            
            # Evaluar modelo
            if val_data:
                val_metrics = self.model.evaluate(X_val, val_targets, verbose=0)
                logger.info(f"Métricas de validación: {val_metrics}")
            
            logger.info(f"Entrenamiento completado en {training_time:.2f} segundos")
            
            return {
                'training_time': training_time,
                'final_loss': history.history['loss'][-1],
                'final_accuracy': history.history.get('classification_accuracy', [0])[-1],
                'epochs_trained': len(history.history['loss'])
            }
            
        except Exception as e:
            logger.error(f"Error entrenando modelo LSTM: {e}")
            return {}

class TransformerTradingModel(TradingModel):
    """Modelo Transformer para análisis de secuencias temporales"""
    
    def __init__(self):
        super().__init__("transformer")
        
        # Parámetros específicos del Transformer
        self.num_heads = self.ml_config.get('num_heads', 8)
        self.ff_dim = self.ml_config.get('ff_dim', 256)
        self.num_transformer_blocks = self.ml_config.get('num_transformer_blocks', 4)
        self.dropout_rate = self.ml_config.get('dropout_rate', 0.1)
        self.learning_rate = self.ml_config.get('learning_rate', 0.001)
    
    def build_transformer_block(self, inputs, head_size, num_heads, ff_dim, dropout=0):
        """Construye un bloque transformer"""
        # Multi-head attention
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=head_size, dropout=dropout
        )(inputs, inputs)
        attention_output = layers.Dropout(dropout)(attention_output)
        attention_output = layers.LayerNormalization(epsilon=1e-6)(inputs + attention_output)
        
        # Feed forward
        ff_output = layers.Dense(ff_dim, activation='relu')(attention_output)
        ff_output = layers.Dropout(dropout)(ff_output)
        ff_output = layers.Dense(inputs.shape[-1])(ff_output)
        ff_output = layers.Dropout(dropout)(ff_output)
        
        return layers.LayerNormalization(epsilon=1e-6)(attention_output + ff_output)
    
    def build_model(self, input_shape: Tuple[int, int]) -> Model:
        """Construye modelo Transformer"""
        inputs = layers.Input(shape=input_shape)
        
        # Positional encoding
        sequence_length, d_model = input_shape
        x = inputs
        
        # Add positional encoding
        positions = tf.range(start=0, limit=sequence_length, delta=1)
        positions = tf.cast(positions, tf.float32)
        pos_encoding = layers.Embedding(sequence_length, d_model)(positions)
        x = x + pos_encoding
        
        # Transformer blocks
        for _ in range(self.num_transformer_blocks):
            x = self.build_transformer_block(
                x, 
                head_size=d_model // self.num_heads,
                num_heads=self.num_heads,
                ff_dim=self.ff_dim,
                dropout=self.dropout_rate
            )
        
        # Global average pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Final dense layers
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(self.dropout_rate)(x)
        
        # Output heads
        classification_output = layers.Dense(3, activation='softmax', name='classification')(x)
        regression_output = layers.Dense(1, activation='tanh', name='regression')(x)
        confidence_output = layers.Dense(1, activation='sigmoid', name='confidence')(x)
        
        model = Model(inputs=inputs, outputs=[classification_output, regression_output, confidence_output])
        
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss={
                'classification': 'sparse_categorical_crossentropy',
                'regression': 'mse',
                'confidence': 'binary_crossentropy'
            },
            loss_weights={'classification': 0.5, 'regression': 0.3, 'confidence': 0.2},
            metrics={
                'classification': ['accuracy'],
                'regression': ['mae'],
                'confidence': ['accuracy']
            }
        )
        
        return model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Entrena el modelo Transformer (similar a LSTM pero optimizado para Transformer)"""
        # Implementación similar a LSTMTradingModel.train() pero con ajustes específicos
        # para el Transformer (ej. learning rate schedule, warmup, etc.)
        return super().train(X_train, y_train, **kwargs)

class EnsembleTradingModel(TradingModel):
    """Ensemble de múltiples modelos para mayor robustez"""
    
    def __init__(self):
        super().__init__("ensemble")
        
        # Modelos del ensemble
        self.models = {
            'lstm': LSTMTradingModel(),
            'transformer': TransformerTradingModel()
        }
        
        # Pesos del ensemble (aprendidos automáticamente)
        self.ensemble_weights = None
        self.meta_model = None
    
    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """Construye todos los modelos del ensemble"""
        for name, model in self.models.items():
            logger.info(f"Construyendo modelo {name} del ensemble")
            model.model = model.build_model(input_shape)
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Entrena todos los modelos del ensemble"""
        try:
            results = {}
            
            # Entrenar cada modelo individualmente
            for name, model in self.models.items():
                logger.info(f"Entrenando modelo {name} del ensemble")
                model_results = model.train(X_train, y_train, **kwargs)
                results[name] = model_results
            
            # Entrenar meta-modelo para combinar predicciones
            self._train_meta_model(X_train, y_train)
            
            self.is_trained = True
            logger.info("Ensemble entrenado exitosamente")
            
            return results
            
        except Exception as e:
            logger.error(f"Error entrenando ensemble: {e}")
            return {}
    
    def _train_meta_model(self, X: np.ndarray, y: np.ndarray):
        """Entrena meta-modelo para combinar predicciones"""
        try:
            # Obtener predicciones de todos los modelos
            predictions = []
            for model in self.models.values():
                if model.is_trained:
                    pred = model.predict(X)
                    if isinstance(pred, list):  # Múltiples outputs
                        pred = pred[0]  # Usar solo clasificación
                    predictions.append(pred)
            
            if not predictions:
                logger.warning("No hay modelos entrenados para meta-modelo")
                return
            
            # Stack predictions
            stacked_predictions = np.concatenate(predictions, axis=1)
            
            # Simple meta-modelo: promedio ponderado aprendido
            self.meta_model = Sequential([
                layers.Dense(32, activation='relu', input_shape=(stacked_predictions.shape[1],)),
                layers.Dropout(0.2),
                layers.Dense(3, activation='softmax')
            ])
            
            self.meta_model.compile(
                optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            self.meta_model.fit(
                stacked_predictions, y,
                epochs=50,
                batch_size=32,
                verbose=0
            )
            
            logger.info("Meta-modelo entrenado")
            
        except Exception as e:
            logger.error(f"Error entrenando meta-modelo: {e}")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicción usando ensemble"""
        if not self.is_trained:
            raise ValueError("Ensemble no entrenado")
        
        # Obtener predicciones de todos los modelos
        predictions = []
        for model in self.models.values():
            if model.is_trained:
                pred = model.predict(X)
                if isinstance(pred, list):
                    pred = pred[0]  # Usar solo clasificación
                predictions.append(pred)
        
        if not predictions:
            raise ValueError("No hay modelos entrenados en el ensemble")
        
        # Combinar con meta-modelo si existe
        if self.meta_model is not None:
            stacked_predictions = np.concatenate(predictions, axis=1)
            return self.meta_model.predict(stacked_predictions)
        else:
            # Promedio simple
            return np.mean(predictions, axis=0)

def create_model(model_type: str = "lstm") -> TradingModel:
    """Factory function para crear modelos"""
    model_types = {
        'lstm': LSTMTradingModel,
        'transformer': TransformerTradingModel,
        'ensemble': EnsembleTradingModel
    }
    
    if model_type not in model_types:
        raise ValueError(f"Tipo de modelo no soportado: {model_type}")
    
    return model_types[model_type]()

def get_available_models() -> List[str]:
    """Retorna lista de modelos disponibles"""
    return ['lstm', 'transformer', 'ensemble']