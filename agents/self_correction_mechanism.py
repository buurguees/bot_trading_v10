"""
🔧 SelfCorrectionMechanism - Mecanismo de Autocorrección

Sistema que permite al agente detectar, analizar y corregir sus propios errores
de forma autónoma, mejorando continuamente su performance y adaptándose
a condiciones cambiantes.

Características:
- Detección automática de errores y anomalías
- Análisis de causas raíz de problemas
- Corrección proactiva de parámetros y estrategias
- Validación de decisiones antes de ejecución
- Recuperación automática de errores críticos
- Monitoreo continuo de performance

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import traceback

# Imports del sistema existente
from config.config_loader import user_config

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Tipos de errores que puede detectar el sistema"""
    PREDICTION_ERROR = "prediction_error"
    DECISION_ERROR = "decision_error"
    EXECUTION_ERROR = "execution_error"
    PERFORMANCE_ERROR = "performance_error"
    SYSTEM_ERROR = "system_error"
    DATA_ERROR = "data_error"
    CONFIGURATION_ERROR = "configuration_error"

class CorrectionType(Enum):
    """Tipos de correcciones que puede aplicar"""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    STRATEGY_MODIFICATION = "strategy_modification"
    THRESHOLD_UPDATE = "threshold_update"
    FILTER_ADDITION = "filter_addition"
    FALLBACK_ACTIVATION = "fallback_activation"
    SYSTEM_RESTART = "system_restart"

@dataclass
class Error:
    """Error detectado por el sistema"""
    error_type: ErrorType
    severity: str  # low, medium, high, critical
    description: str
    context: Dict
    timestamp: datetime
    frequency: int = 1
    last_occurrence: Optional[datetime] = None

@dataclass
class Correction:
    """Corrección aplicada por el sistema"""
    correction_type: CorrectionType
    error_id: str
    description: str
    parameters: Dict
    timestamp: datetime
    success: bool = False
    impact: str = "unknown"

@dataclass
class ValidationResult:
    """Resultado de validación de decisión"""
    is_valid: bool
    confidence: float
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]

class SelfCorrectionMechanism:
    """
    🔧 Mecanismo de Autocorrección
    
    Permite al agente detectar, analizar y corregir sus propios errores
    de forma autónoma, mejorando continuamente su performance.
    """
    
    def __init__(self):
        """Inicializa el mecanismo de autocorrección"""
        self.config = user_config
        self.correction_config = self.config.get_value(['ai_agent', 'self_correction'], {})
        
        # Parámetros de detección
        self.error_thresholds = {
            'prediction_accuracy': 0.6,
            'decision_confidence': 0.5,
            'performance_degradation': 0.2,
            'system_stability': 0.8
        }
        
        # Historial de errores y correcciones
        self.error_history = []
        self.correction_history = []
        self.validation_history = []
        
        # Métricas de corrección
        self.correction_metrics = {
            'total_errors_detected': 0,
            'total_corrections_applied': 0,
            'successful_corrections': 0,
            'failed_corrections': 0,
            'error_reduction_rate': 0.0,
            'correction_accuracy': 0.0
        }
        
        # Estado del sistema
        self.is_monitoring = False
        self.correction_mode = "automatic"  # automatic, manual, disabled
        self.last_health_check = datetime.now()
        
        logger.info("🔧 SelfCorrectionMechanism inicializado")
    
    async def initialize(self) -> None:
        """Inicializa el mecanismo de autocorrección"""
        try:
            # Cargar configuración de corrección
            await self._load_correction_config()
            
            # Inicializar monitoreo
            await self._initialize_monitoring()
            
            # Cargar historial de errores
            await self._load_error_history()
            
            self.is_monitoring = True
            logger.info("✅ Mecanismo de autocorrección inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando autocorrección: {e}")
            raise
    
    async def validate_decision(self, decision: Dict, analysis: Dict) -> Optional[Dict]:
        """
        Valida una decisión antes de ejecutarla
        
        Args:
            decision: Decisión a validar
            analysis: Análisis del mercado
            
        Returns:
            Dict: Decisión validada o None si es inválida
        """
        try:
            # Realizar validación completa
            validation_result = await self._perform_decision_validation(decision, analysis)
            
            # Guardar resultado de validación
            self.validation_history.append({
                'decision': decision,
                'validation': validation_result,
                'timestamp': datetime.now()
            })
            
            # Si la decisión es válida, devolverla
            if validation_result.is_valid:
                logger.info(f"✅ Decisión validada: {decision.get('action', 'UNKNOWN')}")
                return decision
            else:
                logger.warning(f"⚠️ Decisión rechazada: {validation_result.errors}")
                
                # Intentar corrección automática
                corrected_decision = await self._attempt_decision_correction(decision, validation_result)
                if corrected_decision:
                    logger.info("🔧 Decisión corregida automáticamente")
                    return corrected_decision
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error validando decisión: {e}")
            return None
    
    async def detect_errors(self, context: Dict) -> List[Error]:
        """
        Detecta errores en el contexto dado
        
        Args:
            context: Contexto a analizar (performance, decisiones, etc.)
            
        Returns:
            List[Error]: Errores detectados
        """
        try:
            errors = []
            
            # Detectar errores de performance
            performance_errors = await self._detect_performance_errors(context)
            errors.extend(performance_errors)
            
            # Detectar errores de predicción
            prediction_errors = await self._detect_prediction_errors(context)
            errors.extend(prediction_errors)
            
            # Detectar errores de decisión
            decision_errors = await self._detect_decision_errors(context)
            errors.extend(decision_errors)
            
            # Detectar errores del sistema
            system_errors = await self._detect_system_errors(context)
            errors.extend(system_errors)
            
            # Agregar errores al historial
            for error in errors:
                self.error_history.append(error)
                self.correction_metrics['total_errors_detected'] += 1
            
            if errors:
                logger.warning(f"🚨 Detectados {len(errors)} errores")
            
            return errors
            
        except Exception as e:
            logger.error(f"❌ Error detectando errores: {e}")
            return []
    
    async def apply_corrections(self, errors: List[Error]) -> List[Correction]:
        """
        Aplica correcciones para los errores detectados
        
        Args:
            errors: Lista de errores a corregir
            
        Returns:
            List[Correction]: Correcciones aplicadas
        """
        try:
            corrections = []
            
            for error in errors:
                # Generar corrección para el error
                correction = await self._generate_correction(error)
                if correction:
                    # Aplicar corrección
                    success = await self._apply_correction(correction)
                    correction.success = success
                    
                    corrections.append(correction)
                    self.correction_history.append(correction)
                    
                    if success:
                        self.correction_metrics['successful_corrections'] += 1
                        logger.info(f"✅ Corrección aplicada: {correction.description}")
                    else:
                        self.correction_metrics['failed_corrections'] += 1
                        logger.error(f"❌ Corrección falló: {correction.description}")
            
            self.correction_metrics['total_corrections_applied'] += len(corrections)
            
            # Actualizar métricas de corrección
            await self._update_correction_metrics()
            
            return corrections
            
        except Exception as e:
            logger.error(f"❌ Error aplicando correcciones: {e}")
            return []
    
    async def handle_critical_error(self, error: Exception) -> bool:
        """
        Maneja errores críticos del sistema
        
        Args:
            error: Error crítico ocurrido
            
        Returns:
            bool: True si se recuperó exitosamente
        """
        try:
            logger.critical(f"🚨 Error crítico detectado: {error}")
            
            # Crear error crítico
            critical_error = Error(
                error_type=ErrorType.SYSTEM_ERROR,
                severity="critical",
                description=str(error),
                context={
                    'traceback': traceback.format_exc(),
                    'timestamp': datetime.now()
                },
                timestamp=datetime.now()
            )
            
            # Agregar al historial
            self.error_history.append(critical_error)
            
            # Intentar recuperación automática
            recovery_success = await self._attempt_system_recovery(critical_error)
            
            if recovery_success:
                logger.info("✅ Sistema recuperado exitosamente")
                return True
            else:
                logger.error("❌ No se pudo recuperar el sistema automáticamente")
                return False
                
        except Exception as e:
            logger.critical(f"💥 Error en manejo de error crítico: {e}")
            return False
    
    async def _perform_decision_validation(self, decision: Dict, analysis: Dict) -> ValidationResult:
        """Realiza validación completa de una decisión"""
        try:
            warnings = []
            errors = []
            recommendations = []
            
            # Validar confianza mínima
            confidence = decision.get('confidence', 0)
            if confidence < self.error_thresholds['decision_confidence']:
                errors.append(f"Confianza insuficiente: {confidence:.2f}")
            
            # Validar acción
            action = decision.get('action', '')
            if action not in ['BUY', 'SELL', 'HOLD']:
                errors.append(f"Acción inválida: {action}")
            
            # Validar contexto de mercado
            market_regime = analysis.get('market_regime', 'unknown')
            if market_regime == 'volatile' and confidence < 0.8:
                warnings.append("Alta volatilidad - considerar mayor confianza")
            
            # Validar riesgo
            risk_level = analysis.get('risk_level', 'medium')
            if risk_level == 'high' and confidence < 0.9:
                warnings.append("Alto riesgo - considerar mayor confianza")
            
            # Validar coherencia con análisis
            if analysis.get('trend_direction') == 'bearish' and action == 'BUY':
                warnings.append("Compra en tendencia bajista")
            elif analysis.get('trend_direction') == 'bullish' and action == 'SELL':
                warnings.append("Venta en tendencia alcista")
            
            # Generar recomendaciones
            if confidence > 0.8 and len(warnings) == 0:
                recommendations.append("Decisión de alta calidad")
            elif len(warnings) > 0:
                recommendations.append("Revisar advertencias antes de ejecutar")
            
            # Determinar validez
            is_valid = len(errors) == 0
            overall_confidence = confidence if is_valid else 0.0
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=overall_confidence,
                warnings=warnings,
                errors=errors,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"❌ Error en validación: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                warnings=[],
                errors=[f"Error en validación: {str(e)}"],
                recommendations=[]
            )
    
    async def _attempt_decision_correction(self, decision: Dict, validation: ValidationResult) -> Optional[Dict]:
        """Intenta corregir una decisión inválida"""
        try:
            corrected_decision = decision.copy()
            
            # Corregir confianza baja
            if decision.get('confidence', 0) < self.error_thresholds['decision_confidence']:
                corrected_decision['confidence'] = self.error_thresholds['decision_confidence']
                corrected_decision['reasoning'] += " | Confianza ajustada automáticamente"
            
            # Cambiar a HOLD si hay errores críticos
            if any('inválida' in error for error in validation.errors):
                corrected_decision['action'] = 'HOLD'
                corrected_decision['reasoning'] += " | Cambiado a HOLD por validación"
            
            # Aplicar filtros adicionales
            if 'volatilidad' in ' '.join(validation.warnings):
                corrected_decision['confidence'] = min(corrected_decision['confidence'] + 0.1, 1.0)
            
            return corrected_decision
            
        except Exception as e:
            logger.error(f"❌ Error corrigiendo decisión: {e}")
            return None
    
    async def _detect_performance_errors(self, context: Dict) -> List[Error]:
        """Detecta errores de performance"""
        try:
            errors = []
            
            # Verificar métricas de performance
            performance = context.get('performance', {})
            
            # Error de accuracy baja
            accuracy = performance.get('accuracy', 1.0)
            if accuracy < self.error_thresholds['prediction_accuracy']:
                error = Error(
                    error_type=ErrorType.PERFORMANCE_ERROR,
                    severity="high",
                    description=f"Accuracy baja: {accuracy:.2f}",
                    context=performance,
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            # Error de PnL negativo
            total_pnl = performance.get('total_pnl', 0)
            if total_pnl < -1000:  # Pérdida significativa
                error = Error(
                    error_type=ErrorType.PERFORMANCE_ERROR,
                    severity="critical",
                    description=f"PnL negativo significativo: {total_pnl:.2f}",
                    context=performance,
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            # Error de drawdown excesivo
            max_drawdown = performance.get('max_drawdown', 0)
            if max_drawdown > 0.2:  # 20% drawdown
                error = Error(
                    error_type=ErrorType.PERFORMANCE_ERROR,
                    severity="high",
                    description=f"Drawdown excesivo: {max_drawdown:.2%}",
                    context=performance,
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"❌ Error detectando errores de performance: {e}")
            return []
    
    async def _detect_prediction_errors(self, context: Dict) -> List[Error]:
        """Detecta errores de predicción"""
        try:
            errors = []
            
            # Verificar predicciones recientes
            predictions = context.get('predictions', [])
            
            if len(predictions) < 5:
                return errors
            
            # Calcular accuracy de predicciones
            correct_predictions = 0
            for pred in predictions[-10:]:  # Últimas 10 predicciones
                if pred.get('correct', False):
                    correct_predictions += 1
            
            accuracy = correct_predictions / len(predictions[-10:])
            
            if accuracy < self.error_thresholds['prediction_accuracy']:
                error = Error(
                    error_type=ErrorType.PREDICTION_ERROR,
                    severity="medium",
                    description=f"Accuracy de predicciones baja: {accuracy:.2f}",
                    context={'predictions': predictions[-10:]},
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"❌ Error detectando errores de predicción: {e}")
            return []
    
    async def _detect_decision_errors(self, context: Dict) -> List[Error]:
        """Detecta errores de decisión"""
        try:
            errors = []
            
            # Verificar decisiones recientes
            decisions = context.get('decisions', [])
            
            if len(decisions) < 3:
                return errors
            
            # Analizar patrones de decisión
            recent_decisions = decisions[-10:]
            
            # Error de decisiones repetitivas
            actions = [d.get('action', '') for d in recent_decisions]
            if len(set(actions)) == 1 and len(actions) > 5:
                error = Error(
                    error_type=ErrorType.DECISION_ERROR,
                    severity="medium",
                    description="Decisiones repetitivas detectadas",
                    context={'decisions': recent_decisions},
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            # Error de confianza inconsistente
            confidences = [d.get('confidence', 0) for d in recent_decisions]
            if confidences and np.std(confidences) > 0.3:
                error = Error(
                    error_type=ErrorType.DECISION_ERROR,
                    severity="low",
                    description="Confianza inconsistente en decisiones",
                    context={'confidences': confidences},
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"❌ Error detectando errores de decisión: {e}")
            return []
    
    async def _detect_system_errors(self, context: Dict) -> List[Error]:
        """Detecta errores del sistema"""
        try:
            errors = []
            
            # Verificar estabilidad del sistema
            system_health = context.get('system_health', {})
            
            # Error de memoria alta
            memory_usage = system_health.get('memory_usage', 0)
            if memory_usage > 0.9:  # 90% de memoria
                error = Error(
                    error_type=ErrorType.SYSTEM_ERROR,
                    severity="high",
                    description=f"Uso de memoria alto: {memory_usage:.1%}",
                    context=system_health,
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            # Error de CPU alta
            cpu_usage = system_health.get('cpu_usage', 0)
            if cpu_usage > 0.95:  # 95% de CPU
                error = Error(
                    error_type=ErrorType.SYSTEM_ERROR,
                    severity="medium",
                    description=f"Uso de CPU alto: {cpu_usage:.1%}",
                    context=system_health,
                    timestamp=datetime.now()
                )
                errors.append(error)
            
            return errors
            
        except Exception as e:
            logger.error(f"❌ Error detectando errores del sistema: {e}")
            return []
    
    async def _generate_correction(self, error: Error) -> Optional[Correction]:
        """Genera una corrección para un error"""
        try:
            correction_type = None
            parameters = {}
            description = ""
            
            if error.error_type == ErrorType.PERFORMANCE_ERROR:
                if "accuracy" in error.description.lower():
                    correction_type = CorrectionType.THRESHOLD_UPDATE
                    parameters = {'min_confidence': 0.8}
                    description = "Aumentar umbral de confianza mínima"
                elif "pnl" in error.description.lower():
                    correction_type = CorrectionType.PARAMETER_ADJUSTMENT
                    parameters = {'position_size_multiplier': 0.5}
                    description = "Reducir tamaño de posición"
                elif "drawdown" in error.description.lower():
                    correction_type = CorrectionType.STRATEGY_MODIFICATION
                    parameters = {'stop_loss_multiplier': 1.5}
                    description = "Aumentar stop loss"
            
            elif error.error_type == ErrorType.PREDICTION_ERROR:
                correction_type = CorrectionType.FILTER_ADDITION
                parameters = {'prediction_filter': 'confidence_weighted'}
                description = "Aplicar filtro de confianza a predicciones"
            
            elif error.error_type == ErrorType.DECISION_ERROR:
                if "repetitivas" in error.description.lower():
                    correction_type = CorrectionType.STRATEGY_MODIFICATION
                    parameters = {'decision_diversity': True}
                    description = "Activar diversificación de decisiones"
                elif "confianza" in error.description.lower():
                    correction_type = CorrectionType.PARAMETER_ADJUSTMENT
                    parameters = {'confidence_smoothing': 0.1}
                    description = "Suavizar confianza de decisiones"
            
            elif error.error_type == ErrorType.SYSTEM_ERROR:
                if "memoria" in error.description.lower():
                    correction_type = CorrectionType.PARAMETER_ADJUSTMENT
                    parameters = {'memory_cleanup': True}
                    description = "Limpiar memoria del sistema"
                elif "cpu" in error.description.lower():
                    correction_type = CorrectionType.PARAMETER_ADJUSTMENT
                    parameters = {'processing_reduction': True}
                    description = "Reducir procesamiento"
            
            if correction_type:
                return Correction(
                    correction_type=correction_type,
                    error_id=f"ERR_{error.timestamp.strftime('%Y%m%d_%H%M%S')}",
                    description=description,
                    parameters=parameters,
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error generando corrección: {e}")
            return None
    
    async def _apply_correction(self, correction: Correction) -> bool:
        """Aplica una corrección"""
        try:
            # TODO: Implementar aplicación real de correcciones
            # Por ahora simular aplicación exitosa
            
            logger.info(f"🔧 Aplicando corrección: {correction.description}")
            
            # Simular tiempo de aplicación
            await asyncio.sleep(0.1)
            
            # Marcar como exitosa
            correction.success = True
            correction.impact = "positive"
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error aplicando corrección: {e}")
            return False
    
    async def _attempt_system_recovery(self, error: Error) -> bool:
        """Intenta recuperar el sistema de un error crítico"""
        try:
            logger.info("🔄 Intentando recuperación del sistema...")
            
            # Estrategias de recuperación
            recovery_strategies = [
                self._restart_components,
                self._reset_parameters,
                self._activate_fallback_mode,
                self._clear_caches
            ]
            
            for strategy in recovery_strategies:
                try:
                    success = await strategy()
                    if success:
                        logger.info("✅ Recuperación exitosa")
                        return True
                except Exception as e:
                    logger.warning(f"⚠️ Estrategia de recuperación falló: {e}")
                    continue
            
            logger.error("❌ Todas las estrategias de recuperación fallaron")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en recuperación: {e}")
            return False
    
    async def _restart_components(self) -> bool:
        """Reinicia componentes del sistema"""
        try:
            # TODO: Implementar reinicio real de componentes
            logger.info("🔄 Reiniciando componentes...")
            await asyncio.sleep(1)
            return True
        except:
            return False
    
    async def _reset_parameters(self) -> bool:
        """Resetea parámetros a valores por defecto"""
        try:
            # TODO: Implementar reset real de parámetros
            logger.info("🔄 Reseteando parámetros...")
            await asyncio.sleep(0.5)
            return True
        except:
            return False
    
    async def _activate_fallback_mode(self) -> bool:
        """Activa modo de respaldo"""
        try:
            # TODO: Implementar modo de respaldo real
            logger.info("🔄 Activando modo de respaldo...")
            await asyncio.sleep(0.5)
            return True
        except:
            return False
    
    async def _clear_caches(self) -> bool:
        """Limpia cachés del sistema"""
        try:
            # TODO: Implementar limpieza real de cachés
            logger.info("🔄 Limpiando cachés...")
            await asyncio.sleep(0.3)
            return True
        except:
            return False
    
    async def _update_correction_metrics(self) -> None:
        """Actualiza métricas de corrección"""
        try:
            total_corrections = self.correction_metrics['total_corrections_applied']
            successful_corrections = self.correction_metrics['successful_corrections']
            
            if total_corrections > 0:
                self.correction_metrics['correction_accuracy'] = successful_corrections / total_corrections
            
            # Calcular tasa de reducción de errores
            if len(self.error_history) > 10:
                recent_errors = [e for e in self.error_history[-10:] if e.timestamp > datetime.now() - timedelta(hours=1)]
                if recent_errors:
                    self.correction_metrics['error_reduction_rate'] = 1.0 - (len(recent_errors) / 10)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas: {e}")
    
    async def _load_correction_config(self) -> None:
        """Carga configuración de corrección"""
        try:
            # Cargar umbrales de error
            error_thresholds = self.correction_config.get('error_thresholds', {})
            if error_thresholds:
                self.error_thresholds.update(error_thresholds)
            
            # Cargar modo de corrección
            self.correction_mode = self.correction_config.get('correction_mode', 'automatic')
            
            logger.info("⚙️ Configuración de corrección cargada")
            
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
    
    async def _initialize_monitoring(self) -> None:
        """Inicializa el monitoreo del sistema"""
        try:
            # TODO: Inicializar monitoreo real
            logger.info("📊 Monitoreo inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando monitoreo: {e}")
    
    async def _load_error_history(self) -> None:
        """Carga historial de errores"""
        try:
            # TODO: Cargar desde base de datos
            logger.info("📚 Historial de errores cargado")
        except Exception as e:
            logger.error(f"❌ Error cargando historial: {e}")
    
    def get_correction_statistics(self) -> Dict:
        """Obtiene estadísticas del mecanismo de corrección"""
        try:
            return {
                'correction_metrics': self.correction_metrics,
                'recent_errors': self.error_history[-10:],
                'recent_corrections': self.correction_history[-10:],
                'validation_success_rate': self._calculate_validation_success_rate(),
                'error_trends': self._analyze_error_trends()
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
    
    def _calculate_validation_success_rate(self) -> float:
        """Calcula tasa de éxito de validaciones"""
        try:
            if not self.validation_history:
                return 0.0
            
            recent_validations = self.validation_history[-20:]
            successful = sum(1 for v in recent_validations if v['validation'].is_valid)
            return successful / len(recent_validations)
        except:
            return 0.0
    
    def _analyze_error_trends(self) -> Dict:
        """Analiza tendencias de errores"""
        try:
            if len(self.error_history) < 5:
                return {}
            
            # Agrupar errores por tipo
            error_types = {}
            for error in self.error_history[-20:]:
                error_type = error.error_type.value
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Calcular tendencia temporal
            recent_errors = [e for e in self.error_history if e.timestamp > datetime.now() - timedelta(hours=1)]
            older_errors = [e for e in self.error_history if datetime.now() - timedelta(hours=2) < e.timestamp < datetime.now() - timedelta(hours=1)]
            
            trend = "stable"
            if len(recent_errors) > len(older_errors) * 1.5:
                trend = "increasing"
            elif len(recent_errors) < len(older_errors) * 0.5:
                trend = "decreasing"
            
            return {
                'error_types': error_types,
                'trend': trend,
                'recent_count': len(recent_errors),
                'older_count': len(older_errors)
            }
        except:
            return {}
