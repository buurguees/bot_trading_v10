"""
🧠 prediction_engine.py - Motor de Predicciones en Tiempo Real

Motor principal que genera predicciones de trading en tiempo real,
integrando con el sistema de ML y proporcionando confianza y métricas.

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

# Imports del proyecto
from core.ml.legacy.neural_network import TradingModel
from core.data.preprocessor import data_preprocessor
from core.data.database import db_manager
from core.config.config_loader import user_config

logger = logging.getLogger(__name__)

class PredictionEngine:
    """
    Motor de predicciones en tiempo real para el sistema de trading.
    
    Responsabilidades:
    - Generar predicciones de trading en tiempo real
    - Estimar confianza de las predicciones
    - Integrar con el sistema de ML existente
    - Proporcionar métricas de performance
    - Manejar fallbacks y errores
    """
    
    def __init__(self):
        self.config = user_config
        self.model = None
        self.model_loaded = False
        self.last_prediction_time = None
        self.prediction_cache = {}
        self.cache_ttl = 30  # 30 segundos de caché
        
        # Configuración de predicción
        self.prediction_config = self.config.get_value(['ai_model_settings'], {})
        self.min_confidence = self.prediction_config.get('confidence', {}).get('min_confidence_to_trade', 0.65)
        self.high_confidence_threshold = self.prediction_config.get('confidence', {}).get('high_confidence_threshold', 0.80)
        
        # Inicializar modelo
        self._initialize_model()
        
        logger.info("PredictionEngine inicializado")
    
    def _initialize_model(self):
        """Inicializa el modelo de ML"""
        try:
            # Crear instancia del modelo
            self.model = TradingModel()
            
            # Intentar cargar modelo existente
            model_path = self._find_best_model()
            if model_path:
                self.model.load_model(model_path)
                self.model_loaded = True
                logger.info(f"Modelo cargado desde: {model_path}")
            else:
                logger.warning("⚠️ No se encontró modelo entrenado. Usando modelo por defecto.")
                self.model_loaded = False
                
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo: {e}")
            self.model_loaded = False
    
    def _find_best_model(self) -> Optional[str]:
        """Encuentra el mejor modelo disponible"""
        try:
            models_dir = Path("models/saved_models")
            if not models_dir.exists():
                return None
            
            # Buscar archivos de modelo
            model_files = list(models_dir.glob("**/*.h5"))
            if not model_files:
                return None
            
            # Ordenar por fecha de modificación (más reciente primero)
            model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Buscar modelo con "best" en el nombre
            for model_file in model_files:
                if "best" in model_file.name.lower():
                    return str(model_file)
            
            # Si no hay "best", usar el más reciente
            return str(model_files[0])
            
        except Exception as e:
            logger.error(f"Error buscando modelo: {e}")
            return None
    
    async def predict(self, symbol: str, features: np.ndarray) -> Dict[str, Any]:
        """
        Genera predicción para un símbolo y features dados
        
        Args:
            symbol: Símbolo de trading (ej: BTCUSDT)
            features: Array de features para predicción
            
        Returns:
            Dict con predicción, confianza y métricas
        """
        try:
            # Verificar caché
            cache_key = f"{symbol}_{hash(features.tobytes())}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"📋 Usando predicción en caché para {symbol}")
                return self.prediction_cache[cache_key]
            
            # Validar entrada
            if not self._validate_input(symbol, features):
                return self._create_error_prediction("Input inválido")
            
            # Generar predicción
            prediction = await self._generate_prediction(symbol, features)
            
            # Actualizar caché
            self.prediction_cache[cache_key] = prediction
            self.last_prediction_time = datetime.now()
            
            logger.info(f"🔮 Predicción generada para {symbol}: {prediction['action']} (confianza: {prediction['confidence']:.2%})")
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Error generando predicción para {symbol}: {e}")
            return self._create_error_prediction(f"Error interno: {str(e)}")
    
    async def _generate_prediction(self, symbol: str, features: np.ndarray) -> Dict[str, Any]:
        """Genera la predicción real usando el modelo"""
        try:
            if not self.model_loaded:
                return self._create_fallback_prediction(symbol, features)
            
            # Preparar features para el modelo
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # Generar predicción del modelo
            model_output = self.model.predict(features)
            
            # Procesar salida del modelo
            action_probs = model_output.get('action_probabilities', [0.33, 0.34, 0.33])
            confidence = model_output.get('confidence', 0.5)
            expected_return = model_output.get('expected_return', 0.0)
            
            # Determinar acción
            action_idx = np.argmax(action_probs)
            actions = ['SELL', 'HOLD', 'BUY']
            action = actions[action_idx]
            
            # Calcular confianza ajustada
            adjusted_confidence = self._adjust_confidence(confidence, action_probs)
            
            # Crear predicción
            prediction = {
                'symbol': symbol,
                'action': action,
                'action_probabilities': {
                    'SELL': float(action_probs[0]),
                    'HOLD': float(action_probs[1]),
                    'BUY': float(action_probs[2])
                },
                'confidence': adjusted_confidence,
                'expected_return': float(expected_return),
                'risk_level': self._calculate_risk_level(adjusted_confidence, expected_return),
                'time_horizon': self._estimate_time_horizon(action, adjusted_confidence),
                'market_regime': self._detect_market_regime(features),
                'timestamp': datetime.now().isoformat(),
                'model_version': self._get_model_version(),
                'features_used': features.shape[1] if features.ndim > 1 else len(features)
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error en generación de predicción: {e}")
            return self._create_fallback_prediction(symbol, features)
    
    def _create_fallback_prediction(self, symbol: str, features: np.ndarray) -> Dict[str, Any]:
        """Crea predicción de fallback cuando el modelo no está disponible"""
        logger.warning(f"⚠️ Usando predicción de fallback para {symbol}")
        
        # Predicción conservadora basada en reglas simples
        action = 'HOLD'
        confidence = 0.3
        
        # Análisis básico de tendencia si hay suficientes features
        if len(features) >= 3:
            # Simular análisis de tendencia básico
            if features[-1] > features[-2] > features[-3]:
                action = 'BUY'
                confidence = 0.4
            elif features[-1] < features[-2] < features[-3]:
                action = 'SELL'
                confidence = 0.4
        
        return {
            'symbol': symbol,
            'action': action,
            'action_probabilities': {
                'SELL': 0.3 if action == 'SELL' else 0.2,
                'HOLD': 0.4 if action == 'HOLD' else 0.3,
                'BUY': 0.3 if action == 'BUY' else 0.2
            },
            'confidence': confidence,
            'expected_return': 0.0,
            'risk_level': 3,  # Riesgo medio
            'time_horizon': 2.0,  # 2 horas
            'market_regime': 'unknown',
            'timestamp': datetime.now().isoformat(),
            'model_version': 'fallback',
            'features_used': len(features),
            'fallback': True
        }
    
    def _create_error_prediction(self, error_message: str) -> Dict[str, Any]:
        """Crea predicción de error"""
        return {
            'symbol': 'UNKNOWN',
            'action': 'HOLD',
            'action_probabilities': {'SELL': 0.33, 'HOLD': 0.34, 'BUY': 0.33},
            'confidence': 0.0,
            'expected_return': 0.0,
            'risk_level': 5,  # Máximo riesgo
            'time_horizon': 0.0,
            'market_regime': 'error',
            'timestamp': datetime.now().isoformat(),
            'model_version': 'error',
            'features_used': 0,
            'error': error_message
        }
    
    def _validate_input(self, symbol: str, features: np.ndarray) -> bool:
        """Valida la entrada para predicción"""
        if not symbol or not isinstance(symbol, str):
            return False
        
        if features is None or len(features) == 0:
            return False
        
        if not isinstance(features, np.ndarray):
            return False
        
        return True
    
    def _adjust_confidence(self, raw_confidence: float, action_probs: List[float]) -> float:
        """Ajusta la confianza basada en la distribución de probabilidades"""
        try:
            # Calcular entropía de la distribución
            entropy = -sum(p * np.log(p + 1e-8) for p in action_probs)
            max_entropy = np.log(len(action_probs))
            normalized_entropy = entropy / max_entropy
            
            # Ajustar confianza basada en entropía
            # Menor entropía = mayor confianza
            entropy_factor = 1.0 - normalized_entropy
            
            # Ajustar confianza
            adjusted_confidence = raw_confidence * entropy_factor
            
            # Asegurar que esté en rango [0, 1]
            return max(0.0, min(1.0, adjusted_confidence))
            
        except Exception as e:
            logger.warning(f"Error ajustando confianza: {e}")
            return raw_confidence
    
    def _calculate_risk_level(self, confidence: float, expected_return: float) -> int:
        """Calcula nivel de riesgo (1-5)"""
        try:
            # Base: confianza inversa
            risk_base = 5 - int(confidence * 4)
            
            # Ajustar por expected return
            if expected_return > 0.05:  # >5% expected return
                risk_base = max(1, risk_base - 1)
            elif expected_return < -0.03:  # <-3% expected return
                risk_base = min(5, risk_base + 1)
            
            return max(1, min(5, risk_base))
            
        except Exception as e:
            logger.warning(f"Error calculando riesgo: {e}")
            return 3  # Riesgo medio por defecto
    
    def _estimate_time_horizon(self, action: str, confidence: float) -> float:
        """Estima horizonte temporal de la predicción en horas"""
        try:
            base_horizon = {
                'BUY': 4.0,
                'SELL': 3.0,
                'HOLD': 1.0
            }.get(action, 2.0)
            
            # Ajustar por confianza
            confidence_factor = 0.5 + (confidence * 0.5)  # 0.5 a 1.0
            
            return base_horizon * confidence_factor
            
        except Exception as e:
            logger.warning(f"Error estimando horizonte: {e}")
            return 2.0
    
    def _detect_market_regime(self, features: np.ndarray) -> str:
        """Detecta régimen de mercado basado en features"""
        try:
            if len(features) < 3:
                return 'unknown'
            
            # Análisis básico de volatilidad
            recent_values = features[-3:]
            volatility = np.std(recent_values)
            
            # Análisis de tendencia
            trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
            
            if volatility > 0.1:  # Alta volatilidad
                return 'high_volatility'
            elif trend > 0.01:  # Tendencia alcista
                return 'bull'
            elif trend < -0.01:  # Tendencia bajista
                return 'bear'
            else:
                return 'sideways'
                
        except Exception as e:
            logger.warning(f"Error detectando régimen: {e}")
            return 'unknown'
    
    def _get_model_version(self) -> str:
        """Obtiene versión del modelo"""
        if self.model_loaded and hasattr(self.model, 'version'):
            return self.model.version
        return 'unknown'
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el caché es válido"""
        if cache_key not in self.prediction_cache:
            return False
        
        if self.last_prediction_time is None:
            return False
        
        time_diff = (datetime.now() - self.last_prediction_time).total_seconds()
        return time_diff < self.cache_ttl
    
    async def get_prediction_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de predicciones recientes"""
        try:
            return {
                'model_loaded': self.model_loaded,
                'last_prediction_time': self.last_prediction_time.isoformat() if self.last_prediction_time else None,
                'cache_size': len(self.prediction_cache),
                'min_confidence_threshold': self.min_confidence,
                'high_confidence_threshold': self.high_confidence_threshold,
                'model_version': self._get_model_version()
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {'error': str(e)}
    
    async def clear_cache(self):
        """Limpia el caché de predicciones"""
        self.prediction_cache.clear()
        self.last_prediction_time = None
        logger.info("🧹 Caché de predicciones limpiado")
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica salud del motor de predicciones"""
        try:
            health = {
                'status': 'healthy',
                'model_loaded': self.model_loaded,
                'cache_size': len(self.prediction_cache),
                'last_prediction': self.last_prediction_time.isoformat() if self.last_prediction_time else None,
                'config_loaded': bool(self.prediction_config),
                'errors': []
            }
            
            # Verificar modelo
            if not self.model_loaded:
                health['errors'].append("Modelo no cargado")
                health['status'] = 'degraded'
            
            # Verificar configuración
            if not self.prediction_config:
                health['errors'].append("Configuración no cargada")
                health['status'] = 'degraded'
            
            return health
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Instancia global del motor de predicciones
prediction_engine = PredictionEngine()

# Funciones de conveniencia
async def predict(symbol: str, features: np.ndarray) -> Dict[str, Any]:
    """Función de conveniencia para generar predicciones"""
    return await prediction_engine.predict(symbol, features)

async def get_prediction_summary() -> Dict[str, Any]:
    """Función de conveniencia para obtener resumen"""
    return await prediction_engine.get_prediction_summary()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await prediction_engine.health_check()
