# Ruta: core/deployment/phase_manager.py
#!/usr/bin/env python3
"""
Gestor de Fases Enterprise - Coordinación de Dependencias
========================================================

Este módulo gestiona el ciclo de vida y dependencias de cada fase
(infraestructura, entrenamiento, trading, monitoreo) del sistema enterprise.

Características:
- Gestión de dependencias entre fases
- Validación de prerrequisitos
- Control de estado de fases
- Recuperación automática de errores
- Logging detallado de progreso

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

from config.enterprise_config import EnterpriseConfigManager

logger = logging.getLogger(__name__)

class PhaseStatus(Enum):
    """Estados de las fases"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class PhasePriority(Enum):
    """Prioridades de las fases"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class PhaseResult:
    """Resultado de ejecución de una fase"""
    phase_name: str
    status: PhaseStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    dependencies_satisfied: bool = True

class PhaseManager:
    """Gestor de fases del sistema enterprise"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config_manager = EnterpriseConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Definir fases y sus dependencias
        self.phases = {
            'infrastructure': {
                'dependencies': [],
                'priority': PhasePriority.CRITICAL,
                'timeout_minutes': 30,
                'retry_attempts': 3,
                'status': PhaseStatus.PENDING,
                'description': 'Configuración de infraestructura (DB, Redis, Kafka)'
            },
            'data_collection': {
                'dependencies': ['infrastructure'],
                'priority': PhasePriority.HIGH,
                'timeout_minutes': 60,
                'retry_attempts': 2,
                'status': PhaseStatus.PENDING,
                'description': 'Recolección de datos históricos'
            },
            'training': {
                'dependencies': ['infrastructure', 'data_collection'],
                'priority': PhasePriority.HIGH,
                'timeout_minutes': 480,  # 8 horas
                'retry_attempts': 1,
                'status': PhaseStatus.PENDING,
                'description': 'Entrenamiento de modelos ML'
            },
            'trading': {
                'dependencies': ['infrastructure', 'training'],
                'priority': PhasePriority.CRITICAL,
                'timeout_minutes': 60,
                'retry_attempts': 3,
                'status': PhaseStatus.PENDING,
                'description': 'Motor de trading en tiempo real'
            },
            'monitoring': {
                'dependencies': ['infrastructure'],
                'priority': PhasePriority.MEDIUM,
                'timeout_minutes': 30,
                'retry_attempts': 2,
                'status': PhaseStatus.PENDING,
                'description': 'Sistema de monitoreo y alertas'
            },
            'compliance': {
                'dependencies': ['infrastructure', 'trading'],
                'priority': PhasePriority.HIGH,
                'timeout_minutes': 15,
                'retry_attempts': 2,
                'status': PhaseStatus.PENDING,
                'description': 'Sistema de cumplimiento regulatorio'
            }
        }
        
        # Estado del gestor
        self.is_running = False
        self.current_phase = None
        self.phase_results = {}
        self.execution_order = []
        
        # Configuración de logging
        self.setup_logging()
        
        logger.info("🏗️ PhaseManager enterprise inicializado")
    
    def setup_logging(self):
        """Configura el logging para el gestor de fases"""
        log_dir = Path("logs/enterprise/deployment")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logger específico para fases
        phase_logger = logging.getLogger('phase_manager')
        phase_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_dir / 'phase_manager.log')
        file_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        phase_logger.addHandler(file_handler)
    
    def calculate_execution_order(self) -> List[str]:
        """Calcula el orden de ejecución basado en dependencias y prioridades"""
        try:
            # Algoritmo de ordenamiento topológico
            visited = set()
            temp_visited = set()
            order = []
            
            def visit(phase_name):
                if phase_name in temp_visited:
                    raise ValueError(f"Dependencia circular detectada: {phase_name}")
                if phase_name in visited:
                    return
                
                temp_visited.add(phase_name)
                
                # Visitar dependencias primero
                for dep in self.phases[phase_name]['dependencies']:
                    if dep in self.phases:
                        visit(dep)
                
                temp_visited.remove(phase_name)
                visited.add(phase_name)
                order.append(phase_name)
            
            # Visitar todas las fases
            for phase_name in self.phases:
                if phase_name not in visited:
                    visit(phase_name)
            
            # Ordenar por prioridad dentro del mismo nivel
            priority_order = sorted(order, key=lambda x: self.phases[x]['priority'].value)
            
            self.execution_order = priority_order
            logger.info(f"📋 Orden de ejecución calculado: {priority_order}")
            return priority_order
            
        except Exception as e:
            logger.error(f"❌ Error calculando orden de ejecución: {e}")
            return []
    
    async def validate_phase_dependencies(self, phase_name: str) -> Tuple[bool, List[str]]:
        """Valida que las dependencias de una fase estén completadas"""
        try:
            if phase_name not in self.phases:
                return False, [f"Fase desconocida: {phase_name}"]
            
            missing_deps = []
            phase_info = self.phases[phase_name]
            
            for dep in phase_info['dependencies']:
                if dep not in self.phases:
                    missing_deps.append(f"Dependencia inexistente: {dep}")
                elif self.phases[dep]['status'] != PhaseStatus.COMPLETED:
                    missing_deps.append(f"Dependencia {dep} no completada (estado: {self.phases[dep]['status'].value})")
            
            is_valid = len(missing_deps) == 0
            
            if is_valid:
                logger.info(f"✅ Dependencias validadas para fase: {phase_name}")
            else:
                logger.warning(f"⚠️ Dependencias faltantes para {phase_name}: {missing_deps}")
            
            return is_valid, missing_deps
            
        except Exception as e:
            logger.error(f"❌ Error validando dependencias de {phase_name}: {e}")
            return False, [str(e)]
    
    async def execute_phase(self, phase_name: str, mode: str = "production") -> PhaseResult:
        """Ejecuta una fase específica"""
        try:
            if phase_name not in self.phases:
                raise ValueError(f"Fase desconocida: {phase_name}")
            
            phase_info = self.phases[phase_name]
            start_time = datetime.now()
            
            logger.info(f"🚀 Iniciando fase: {phase_name} ({phase_info['description']})")
            
            # Validar dependencias
            deps_valid, missing_deps = await self.validate_phase_dependencies(phase_name)
            if not deps_valid:
                return PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.FAILED,
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=0,
                    success=False,
                    error_message=f"Dependencias faltantes: {missing_deps}",
                    dependencies_satisfied=False
                )
            
            # Actualizar estado
            self.phases[phase_name]['status'] = PhaseStatus.RUNNING
            self.current_phase = phase_name
            
            # Ejecutar fase con timeout y reintentos
            result = await self._execute_phase_with_retry(phase_name, mode, phase_info)
            
            # Actualizar estado final
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            phase_result = PhaseResult(
                phase_name=phase_name,
                status=result['status'],
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=result['success'],
                error_message=result.get('error_message'),
                metrics=result.get('metrics', {}),
                dependencies_satisfied=True
            )
            
            # Guardar resultado
            self.phase_results[phase_name] = phase_result
            self.phases[phase_name]['status'] = result['status']
            
            # Log resultado
            if result['success']:
                logger.info(f"✅ Fase {phase_name} completada en {duration:.2f}s")
            else:
                logger.error(f"❌ Fase {phase_name} falló: {result.get('error_message', 'Error desconocido')}")
            
            return phase_result
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando fase {phase_name}: {e}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = PhaseResult(
                phase_name=phase_name,
                status=PhaseStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
                dependencies_satisfied=False
            )
            
            self.phase_results[phase_name] = result
            self.phases[phase_name]['status'] = PhaseStatus.FAILED
            return result
    
    async def _execute_phase_with_retry(self, phase_name: str, mode: str, phase_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una fase con reintentos y timeout"""
        retry_attempts = phase_info['retry_attempts']
        timeout_minutes = phase_info['timeout_minutes']
        
        for attempt in range(retry_attempts + 1):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{retry_attempts + 1} para fase {phase_name}")
                
                # Ejecutar fase con timeout
                result = await asyncio.wait_for(
                    self._run_phase_implementation(phase_name, mode),
                    timeout=timeout_minutes * 60
                )
                
                return result
                
            except asyncio.TimeoutError:
                error_msg = f"Timeout después de {timeout_minutes} minutos"
                logger.error(f"⏰ {error_msg} en fase {phase_name}")
                
                if attempt < retry_attempts:
                    logger.info(f"🔄 Reintentando fase {phase_name}...")
                    await asyncio.sleep(5)  # Esperar 5 segundos antes del reintento
                else:
                    return {
                        'status': PhaseStatus.FAILED,
                        'success': False,
                        'error_message': error_msg
                    }
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error en intento {attempt + 1} de fase {phase_name}: {error_msg}")
                
                if attempt < retry_attempts:
                    logger.info(f"🔄 Reintentando fase {phase_name}...")
                    await asyncio.sleep(5)
                else:
                    return {
                        'status': PhaseStatus.FAILED,
                        'success': False,
                        'error_message': error_msg
                    }
        
        return {
            'status': PhaseStatus.FAILED,
            'success': False,
            'error_message': f"Falló después de {retry_attempts + 1} intentos"
        }
    
    async def _run_phase_implementation(self, phase_name: str, mode: str) -> Dict[str, Any]:
        """Implementación específica de cada fase"""
        try:
            if phase_name == 'infrastructure':
                return await self._run_infrastructure_phase(mode)
            elif phase_name == 'data_collection':
                return await self._run_data_collection_phase(mode)
            elif phase_name == 'training':
                return await self._run_training_phase(mode)
            elif phase_name == 'trading':
                return await self._run_trading_phase(mode)
            elif phase_name == 'monitoring':
                return await self._run_monitoring_phase(mode)
            elif phase_name == 'compliance':
                return await self._run_compliance_phase(mode)
            else:
                raise ValueError(f"Implementación no encontrada para fase: {phase_name}")
                
        except Exception as e:
            logger.error(f"❌ Error en implementación de fase {phase_name}: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_infrastructure_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de infraestructura"""
        try:
            logger.info("🏗️ Configurando infraestructura...")
            
            # Simular configuración de infraestructura
            # En implementación real, aquí se configurarían DB, Redis, Kafka, etc.
            await asyncio.sleep(2)
            
            # Verificar servicios
            services_status = {
                'database': True,
                'redis': True,
                'kafka': True,
                'prometheus': True,
                'grafana': True
            }
            
            logger.info("✅ Infraestructura configurada correctamente")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': {
                    'services_configured': len(services_status),
                    'services_status': services_status
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de infraestructura: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_data_collection_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de recolección de datos"""
        try:
            logger.info("📊 Iniciando recolección de datos...")
            
            # Simular recolección de datos
            await asyncio.sleep(3)
            
            # Simular métricas de recolección
            data_metrics = {
                'symbols_processed': 10,
                'timeframes_collected': 4,
                'total_candles': 100000,
                'data_quality_score': 95.5
            }
            
            logger.info("✅ Recolección de datos completada")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': data_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de recolección de datos: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_training_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de entrenamiento"""
        try:
            logger.info("🧠 Iniciando entrenamiento de modelos...")
            
            # Simular entrenamiento (más largo)
            await asyncio.sleep(5)
            
            # Simular métricas de entrenamiento
            training_metrics = {
                'models_trained': 3,
                'training_accuracy': 87.3,
                'validation_accuracy': 84.1,
                'training_time_minutes': 5,
                'best_model': 'lstm_attention_v2'
            }
            
            logger.info("✅ Entrenamiento de modelos completado")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': training_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de entrenamiento: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_trading_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de trading"""
        try:
            logger.info("💰 Iniciando motor de trading...")
            
            # Simular inicialización del motor de trading
            await asyncio.sleep(2)
            
            # Simular métricas de trading
            trading_metrics = {
                'engine_initialized': True,
                'symbols_configured': 10,
                'strategies_loaded': 4,
                'risk_limits_set': True,
                'api_connected': True
            }
            
            logger.info("✅ Motor de trading inicializado")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': trading_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de trading: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_monitoring_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de monitoreo"""
        try:
            logger.info("📊 Iniciando sistema de monitoreo...")
            
            # Simular configuración de monitoreo
            await asyncio.sleep(1)
            
            # Simular métricas de monitoreo
            monitoring_metrics = {
                'prometheus_configured': True,
                'grafana_dashboards_loaded': 4,
                'alert_rules_active': 12,
                'health_checks_passing': True
            }
            
            logger.info("✅ Sistema de monitoreo configurado")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': monitoring_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de monitoreo: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def _run_compliance_phase(self, mode: str) -> Dict[str, Any]:
        """Ejecuta la fase de cumplimiento"""
        try:
            logger.info("⚖️ Configurando sistema de cumplimiento...")
            
            # Simular configuración de cumplimiento
            await asyncio.sleep(1)
            
            # Simular métricas de cumplimiento
            compliance_metrics = {
                'audit_logging_enabled': True,
                'mifid2_compliance': True,
                'gdpr_compliance': True,
                'retention_policy_set': True,
                'encryption_enabled': True
            }
            
            logger.info("✅ Sistema de cumplimiento configurado")
            
            return {
                'status': PhaseStatus.COMPLETED,
                'success': True,
                'metrics': compliance_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error en fase de cumplimiento: {e}")
            return {
                'status': PhaseStatus.FAILED,
                'success': False,
                'error_message': str(e)
            }
    
    async def execute_all_phases(self, mode: str = "production", phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ejecuta todas las fases en orden"""
        try:
            logger.info(f"🚀 Iniciando ejecución de fases en modo {mode}")
            
            self.is_running = True
            start_time = datetime.now()
            
            # Calcular orden de ejecución
            execution_order = self.calculate_execution_order()
            if not execution_order:
                raise ValueError("No se pudo calcular el orden de ejecución")
            
            # Filtrar fases si se especifica
            if phases:
                execution_order = [p for p in execution_order if p in phases]
                logger.info(f"📋 Ejecutando fases específicas: {execution_order}")
            else:
                logger.info(f"📋 Ejecutando todas las fases: {execution_order}")
            
            # Ejecutar cada fase
            completed_phases = []
            failed_phases = []
            
            for phase_name in execution_order:
                if not self.is_running:
                    logger.warning("⏹️ Ejecución cancelada por el usuario")
                    break
                
                try:
                    result = await self.execute_phase(phase_name, mode)
                    
                    if result.success:
                        completed_phases.append(phase_name)
                    else:
                        failed_phases.append(phase_name)
                        
                        # Si es una fase crítica, detener la ejecución
                        if self.phases[phase_name]['priority'] == PhasePriority.CRITICAL:
                            logger.error(f"❌ Fase crítica {phase_name} falló, deteniendo ejecución")
                            break
                
                except Exception as e:
                    logger.error(f"❌ Error ejecutando fase {phase_name}: {e}")
                    failed_phases.append(phase_name)
            
            # Calcular resultados finales
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            overall_success = len(failed_phases) == 0
            success_rate = len(completed_phases) / len(execution_order) * 100
            
            results = {
                'overall_success': overall_success,
                'success_rate': success_rate,
                'total_duration_seconds': total_duration,
                'phases_executed': len(execution_order),
                'phases_completed': len(completed_phases),
                'phases_failed': len(failed_phases),
                'completed_phases': completed_phases,
                'failed_phases': failed_phases,
                'phase_results': self.phase_results,
                'execution_summary': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'mode': mode
                }
            }
            
            # Log resumen
            if overall_success:
                logger.info(f"✅ Todas las fases completadas exitosamente en {total_duration:.2f}s")
            else:
                logger.warning(f"⚠️ Ejecución completada con errores: {len(failed_phases)} fases fallaron")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en ejecución de fases: {e}")
            return {
                'overall_success': False,
                'error': str(e),
                'phases_completed': [],
                'phases_failed': list(self.phases.keys())
            }
        finally:
            self.is_running = False
    
    def get_phase_status(self, phase_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una fase específica"""
        if phase_name not in self.phases:
            return None
        
        phase_info = self.phases[phase_name].copy()
        if phase_name in self.phase_results:
            phase_info['result'] = self.phase_results[phase_name]
        
        return phase_info
    
    def get_all_phases_status(self) -> Dict[str, Any]:
        """Obtiene el estado de todas las fases"""
        return {
            'is_running': self.is_running,
            'current_phase': self.current_phase,
            'execution_order': self.execution_order,
            'phases': {name: self.get_phase_status(name) for name in self.phases},
            'summary': {
                'total_phases': len(self.phases),
                'completed_phases': len([p for p in self.phases.values() if p['status'] == PhaseStatus.COMPLETED]),
                'failed_phases': len([p for p in self.phases.values() if p['status'] == PhaseStatus.FAILED]),
                'pending_phases': len([p for p in self.phases.values() if p['status'] == PhaseStatus.PENDING])
            }
        }
    
    async def cancel_execution(self):
        """Cancela la ejecución actual"""
        logger.info("⏹️ Cancelando ejecución de fases...")
        self.is_running = False
        
        if self.current_phase:
            self.phases[self.current_phase]['status'] = PhaseStatus.CANCELLED
            logger.info(f"⏹️ Fase {self.current_phase} cancelada")
    
    async def reset_phases(self):
        """Reinicia el estado de todas las fases"""
        logger.info("🔄 Reiniciando estado de fases...")
        
        for phase_name in self.phases:
            self.phases[phase_name]['status'] = PhaseStatus.PENDING
        
        self.phase_results.clear()
        self.current_phase = None
        self.is_running = False
        
        logger.info("✅ Estado de fases reiniciado")

# Instancia global
phase_manager = PhaseManager()
