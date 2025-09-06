"""
💪 confidence_estimator.py - Estimador de Confianza

Sistema que estima la confianza de las predicciones del modelo ML,
proporcionando calibración y estimación de incertidumbre.

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
from collections import defaultdict

# Imports del proyecto
from config.config_loader import user_config

logger = logging.getLogger(__name__)

class ConfidenceEstimator:
    """
    Estimador de confianza para predicciones del modelo ML.
    
    Responsabilidades:
    - Estimar confianza de predicciones individuales
    - Calibrar confianza basada en performance histórica
    - Detectar overconfidence y underconfidence
    - Proporcionar estimación de incertidumbre
    - Ajustar confianza basada en condiciones de mercado
    """
    
    def __init__(self):
        self.config = user_config
        self.confidence_history = []
        self.calibration_data = defaultdict(list)
        self.confidence_thresholds = {
            'low': 0.5,
            'medium': 0.7,
            'high': 0.8,
            'very_high': 0.9
        }
        
        # Configuración de confianza
        self.confidence_config = self.config.get_value(['ai_model_settings', 'confidence'], {})
        self.min_confidence_to_trade = self.confidence_config.get('min_confidence_to_trade', 0.65)
        self.high_confidence_threshold = self.confidence_config.get('high_confidence_threshold', 0.80)
        self.confidence_adjustments = self.confidence_config.get('confidence_adjustments', {
            'low_confidence': 0.5,
            'high_confidence': 1.5
        })
        
        logger.info("💪 ConfidenceEstimator inicializado")
    
    def estimate_confidence(self, prediction_output: Dict[str, Any], market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Estima la confianza de una predicción
        
        Args:
            prediction_output: Salida del modelo ML
            market_context: Contexto del mercado (opcional)
            
        Returns:
            Dict con estimación de confianza y métricas
        """
        try:
            # Extraer datos de la predicción
            action_probs = prediction_output.get('action_probabilities', [0.33, 0.34, 0.33])
            raw_confidence = prediction_output.get('confidence', 0.5)
            
            # Calcular confianza base
            base_confidence = self._calculate_base_confidence(action_probs, raw_confidence)
            
            # Ajustar por contexto de mercado
            adjusted_confidence = self._adjust_for_market_context(base_confidence, market_context)
            
            # Calcular incertidumbre
            uncertainty = self._calculate_uncertainty(action_probs)
            
            # Determinar nivel de confianza
            confidence_level = self._determine_confidence_level(adjusted_confidence)
            
            # Calcular confianza calibrada
            calibrated_confidence = self._calibrate_confidence(adjusted_confidence, action_probs)
            
            # Crear resultado
            confidence_result = {
                'raw_confidence': raw_confidence,
                'base_confidence': base_confidence,
                'adjusted_confidence': adjusted_confidence,
                'calibrated_confidence': calibrated_confidence,
                'confidence_level': confidence_level,
                'uncertainty': uncertainty,
                'entropy': self._calculate_entropy(action_probs),
                'max_probability': max(action_probs),
                'probability_spread': max(action_probs) - min(action_probs),
                'is_tradeable': calibrated_confidence >= self.min_confidence_to_trade,
                'is_high_confidence': calibrated_confidence >= self.high_confidence_threshold,
                'timestamp': datetime.now().isoformat()
            }
            
            # Guardar en historial
            self.confidence_history.append(confidence_result)
            
            logger.debug(f"💪 Confianza estimada: {calibrated_confidence:.3f} ({confidence_level})")
            return confidence_result
            
        except Exception as e:
            logger.error(f"❌ Error estimando confianza: {e}")
            return self._create_error_confidence(str(e))
    
    def _calculate_base_confidence(self, action_probs: List[float], raw_confidence: float) -> float:
        """Calcula confianza base basada en probabilidades de acción"""
        try:
            # Normalizar probabilidades
            probs = np.array(action_probs)
            probs = probs / np.sum(probs)  # Asegurar que sumen 1
            
            # Calcular confianza basada en la distribución
            max_prob = np.max(probs)
            entropy = -np.sum(probs * np.log(probs + 1e-8))
            max_entropy = np.log(len(probs))
            normalized_entropy = entropy / max_entropy
            
            # Confianza base: combinar max_prob con entropía
            # Mayor max_prob y menor entropía = mayor confianza
            entropy_factor = 1 - normalized_entropy
            base_confidence = (max_prob * 0.7) + (entropy_factor * 0.3)
            
            # Combinar con confianza raw del modelo
            combined_confidence = (base_confidence * 0.6) + (raw_confidence * 0.4)
            
            return min(1.0, max(0.0, combined_confidence))
            
        except Exception as e:
            logger.warning(f"Error calculando confianza base: {e}")
            return raw_confidence
    
    def _adjust_for_market_context(self, base_confidence: float, market_context: Dict[str, Any]) -> float:
        """Ajusta confianza basada en contexto de mercado"""
        try:
            if not market_context:
                return base_confidence
            
            adjustment_factor = 1.0
            
            # Ajustar por volatilidad
            volatility = market_context.get('volatility', 0.5)
            if volatility > 0.8:  # Alta volatilidad
                adjustment_factor *= 0.8
            elif volatility < 0.3:  # Baja volatilidad
                adjustment_factor *= 1.1
            
            # Ajustar por régimen de mercado
            market_regime = market_context.get('market_regime', 'unknown')
            if market_regime == 'high_volatility':
                adjustment_factor *= 0.7
            elif market_regime == 'bull':
                adjustment_factor *= 1.05
            elif market_regime == 'bear':
                adjustment_factor *= 0.9
            
            # Ajustar por volumen
            volume_ratio = market_context.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:  # Alto volumen
                adjustment_factor *= 1.05
            elif volume_ratio < 0.5:  # Bajo volumen
                adjustment_factor *= 0.9
            
            # Ajustar por hora del día
            hour = datetime.now().hour
            if 9 <= hour <= 16:  # Horario de mercado activo
                adjustment_factor *= 1.02
            elif 22 <= hour or hour <= 6:  # Horario de baja actividad
                adjustment_factor *= 0.95
            
            adjusted_confidence = base_confidence * adjustment_factor
            return min(1.0, max(0.0, adjusted_confidence))
            
        except Exception as e:
            logger.warning(f"Error ajustando por contexto de mercado: {e}")
            return base_confidence
    
    def _calculate_uncertainty(self, action_probs: List[float]) -> float:
        """Calcula incertidumbre de la predicción"""
        try:
            probs = np.array(action_probs)
            probs = probs / np.sum(probs)  # Normalizar
            
            # Calcular entropía como medida de incertidumbre
            entropy = -np.sum(probs * np.log(probs + 1e-8))
            max_entropy = np.log(len(probs))
            normalized_entropy = entropy / max_entropy
            
            # Calcular varianza de probabilidades
            variance = np.var(probs)
            
            # Combinar entropía y varianza
            uncertainty = (normalized_entropy * 0.7) + (variance * 0.3)
            
            return min(1.0, max(0.0, uncertainty))
            
        except Exception as e:
            logger.warning(f"Error calculando incertidumbre: {e}")
            return 0.5
    
    def _determine_confidence_level(self, confidence: float) -> str:
        """Determina el nivel de confianza"""
        if confidence >= self.confidence_thresholds['very_high']:
            return 'very_high'
        elif confidence >= self.confidence_thresholds['high']:
            return 'high'
        elif confidence >= self.confidence_thresholds['medium']:
            return 'medium'
        elif confidence >= self.confidence_thresholds['low']:
            return 'low'
        else:
            return 'very_low'
    
    def _calibrate_confidence(self, confidence: float, action_probs: List[float]) -> float:
        """Calibra la confianza basada en datos históricos"""
        try:
            # Obtener datos de calibración para esta distribución de probabilidades
            prob_key = self._get_probability_key(action_probs)
            calibration_data = self.calibration_data.get(prob_key, [])
            
            if len(calibration_data) < 10:  # No hay suficientes datos para calibración
                return confidence
            
            # Calcular accuracy histórica para este rango de confianza
            confidence_bin = int(confidence * 10) / 10  # Redondear a décimas
            bin_data = [data for data in calibration_data if abs(data['confidence'] - confidence_bin) < 0.05]
            
            if len(bin_data) < 5:
                return confidence
            
            # Calcular accuracy real
            actual_accuracy = np.mean([data['accuracy'] for data in bin_data])
            
            # Ajustar confianza basada en accuracy real
            calibration_factor = actual_accuracy / confidence if confidence > 0 else 1.0
            calibrated_confidence = confidence * calibration_factor
            
            return min(1.0, max(0.0, calibrated_confidence))
            
        except Exception as e:
            logger.warning(f"Error calibrando confianza: {e}")
            return confidence
    
    def _get_probability_key(self, action_probs: List[float]) -> str:
        """Genera clave para agrupar probabilidades similares"""
        try:
            # Redondear probabilidades a centésimas
            rounded_probs = [round(p, 2) for p in action_probs]
            return str(rounded_probs)
        except Exception as e:
            logger.warning(f"Error generando clave de probabilidad: {e}")
            return "unknown"
    
    def _calculate_entropy(self, action_probs: List[float]) -> float:
        """Calcula entropía de la distribución de probabilidades"""
        try:
            probs = np.array(action_probs)
            probs = probs / np.sum(probs)  # Normalizar
            entropy = -np.sum(probs * np.log(probs + 1e-8))
            return entropy
        except Exception as e:
            logger.warning(f"Error calculando entropía: {e}")
            return 0.0
    
    def update_calibration_data(self, prediction_result: Dict[str, Any], actual_result: str):
        """Actualiza datos de calibración con resultado real"""
        try:
            if 'action_probabilities' not in prediction_result:
                return
            
            action_probs = prediction_result['action_probabilities']
            confidence = prediction_result.get('calibrated_confidence', prediction_result.get('confidence', 0.5))
            
            # Determinar si la predicción fue correcta
            predicted_action = prediction_result.get('action', 'HOLD')
            is_correct = predicted_action == actual_result
            accuracy = 1.0 if is_correct else 0.0
            
            # Guardar datos de calibración
            prob_key = self._get_probability_key(action_probs)
            self.calibration_data[prob_key].append({
                'confidence': confidence,
                'accuracy': accuracy,
                'timestamp': datetime.now().isoformat()
            })
            
            # Limpiar datos antiguos (mantener solo últimos 1000)
            if len(self.calibration_data[prob_key]) > 1000:
                self.calibration_data[prob_key] = self.calibration_data[prob_key][-1000:]
            
            logger.debug(f"📊 Datos de calibración actualizados: {prob_key}")
            
        except Exception as e:
            logger.error(f"Error actualizando datos de calibración: {e}")
    
    def _create_error_confidence(self, error_message: str) -> Dict[str, Any]:
        """Crea estimación de confianza para error"""
        return {
            'raw_confidence': 0.0,
            'base_confidence': 0.0,
            'adjusted_confidence': 0.0,
            'calibrated_confidence': 0.0,
            'confidence_level': 'error',
            'uncertainty': 1.0,
            'entropy': 1.0,
            'max_probability': 0.0,
            'probability_spread': 0.0,
            'is_tradeable': False,
            'is_high_confidence': False,
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }
    
    def get_confidence_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de confianza"""
        try:
            if len(self.confidence_history) == 0:
                return {'message': 'No hay datos de confianza disponibles'}
            
            confidences = [c['calibrated_confidence'] for c in self.confidence_history]
            
            stats = {
                'total_predictions': len(self.confidence_history),
                'mean_confidence': np.mean(confidences),
                'std_confidence': np.std(confidences),
                'min_confidence': np.min(confidences),
                'max_confidence': np.max(confidences),
                'median_confidence': np.median(confidences),
                'tradeable_predictions': sum(1 for c in confidences if c >= self.min_confidence_to_trade),
                'high_confidence_predictions': sum(1 for c in confidences if c >= self.high_confidence_threshold),
                'confidence_distribution': {
                    'very_low': sum(1 for c in confidences if c < self.confidence_thresholds['low']),
                    'low': sum(1 for c in confidences if self.confidence_thresholds['low'] <= c < self.confidence_thresholds['medium']),
                    'medium': sum(1 for c in confidences if self.confidence_thresholds['medium'] <= c < self.confidence_thresholds['high']),
                    'high': sum(1 for c in confidences if self.confidence_thresholds['high'] <= c < self.confidence_thresholds['very_high']),
                    'very_high': sum(1 for c in confidences if c >= self.confidence_thresholds['very_high'])
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def get_calibration_quality(self) -> Dict[str, Any]:
        """Obtiene calidad de calibración"""
        try:
            if not self.calibration_data:
                return {'message': 'No hay datos de calibración disponibles'}
            
            all_data = []
            for prob_key, data in self.calibration_data.items():
                all_data.extend(data)
            
            if len(all_data) < 10:
                return {'message': 'Datos insuficientes para calibración'}
            
            # Agrupar por bins de confianza
            confidence_bins = np.linspace(0, 1, 11)
            bin_stats = []
            
            for i in range(len(confidence_bins) - 1):
                bin_data = [d for d in all_data if confidence_bins[i] <= d['confidence'] < confidence_bins[i + 1]]
                if len(bin_data) >= 3:
                    bin_accuracy = np.mean([d['accuracy'] for d in bin_data])
                    bin_confidence = np.mean([d['confidence'] for d in bin_data])
                    bin_count = len(bin_data)
                    
                    bin_stats.append({
                        'confidence_range': f"{confidence_bins[i]:.1f}-{confidence_bins[i + 1]:.1f}",
                        'mean_confidence': bin_confidence,
                        'mean_accuracy': bin_accuracy,
                        'count': bin_count,
                        'calibration_error': abs(bin_accuracy - bin_confidence)
                    })
            
            # Calcular ECE (Expected Calibration Error)
            ece = np.mean([stat['calibration_error'] for stat in bin_stats])
            
            return {
                'total_calibration_samples': len(all_data),
                'confidence_bins': len(bin_stats),
                'expected_calibration_error': ece,
                'calibration_quality': 'excellent' if ece < 0.05 else 'good' if ece < 0.1 else 'fair' if ece < 0.2 else 'poor',
                'bin_statistics': bin_stats
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo calidad de calibración: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica salud del estimador de confianza"""
        try:
            return {
                'status': 'healthy',
                'confidence_history_count': len(self.confidence_history),
                'calibration_data_count': sum(len(data) for data in self.calibration_data.values()),
                'thresholds_configured': bool(self.confidence_thresholds),
                'min_confidence_to_trade': self.min_confidence_to_trade,
                'high_confidence_threshold': self.high_confidence_threshold
            }
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Instancia global del estimador de confianza
confidence_estimator = ConfidenceEstimator()

# Funciones de conveniencia
def estimate_confidence(prediction_output: Dict[str, Any], market_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Función de conveniencia para estimar confianza"""
    return confidence_estimator.estimate_confidence(prediction_output, market_context)

def update_calibration_data(prediction_result: Dict[str, Any], actual_result: str):
    """Función de conveniencia para actualizar calibración"""
    confidence_estimator.update_calibration_data(prediction_result, actual_result)

def get_confidence_statistics() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas"""
    return confidence_estimator.get_confidence_statistics()

def get_calibration_quality() -> Dict[str, Any]:
    """Función de conveniencia para obtener calidad de calibración"""
    return confidence_estimator.get_calibration_quality()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await confidence_estimator.health_check()
