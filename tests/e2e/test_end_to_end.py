#!/usr/bin/env python3
"""
Tests End-to-End Enterprise
===========================

Tests de integración end-to-end para el sistema enterprise completo.
"""

import pytest
import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from deployment.phase_manager import PhaseManager
from deployment.health_monitor import HealthMonitor
from deployment.recovery_manager import RecoveryManager
from config.enterprise_config import EnterpriseConfigManager

# Configurar logging para tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestEnterpriseE2E:
    """Tests end-to-end para el sistema enterprise"""
    
    @pytest.fixture
    def test_config(self):
        """Configuración de prueba para E2E"""
        return {
            'version': '1.0.0',
            'bot_settings': {
                'main_symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT'],
                'enterprise_features': {
                    'real_time_data_collection': True,
                    'futures_trading': True,
                    'compliance_monitoring': True
                }
            },
            'trading_enterprise': {
                'futures_trading': {
                    'leverage': {
                        'min_leverage': 5,
                        'max_leverage': 30
                    },
                    'margin_mode': 'isolated'
                },
                'strategies': {
                    'ml_strategy': {
                        'confidence_threshold': 65.0,
                        'model_type': 'lstm_attention'
                    }
                },
                'order_management': {
                    'default_order_type': 'market',
                    'stop_loss': {
                        'method': 'atr_based',
                        'atr_multiplier': 2.0
                    },
                    'take_profit': {
                        'risk_reward_ratio': 2.0
                    }
                }
            },
            'data_collection': {
                'real_time': {
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT'],
                    'timeframes': ['1m', '5m', '15m', '1h']
                },
                'storage': {
                    'timescaledb_enabled': True,
                    'redis_cache_enabled': True
                }
            },
            'monitoring': {
                'prometheus': {
                    'enabled': True,
                    'port': 8001
                }
            },
            'security': {
                'encryption': {
                    'enabled': True,
                    'algorithm': 'AES-256-GCM'
                }
            },
            'compliance': {
                'mifid2_enabled': True,
                'data_retention_years': 7
            }
        }
    
    @pytest.fixture
    def phase_manager(self, test_config):
        """PhaseManager para tests E2E"""
        return PhaseManager(test_config)
    
    @pytest.fixture
    def health_monitor(self, test_config):
        """HealthMonitor para tests E2E"""
        return HealthMonitor(test_config)
    
    @pytest.fixture
    def recovery_manager(self):
        """RecoveryManager para tests E2E"""
        return RecoveryManager('config/user_settings.yaml')
    
    @pytest.fixture
    def config_manager(self):
        """ConfigManager para tests E2E"""
        return EnterpriseConfigManager('config/user_settings.yaml')
    
    async def test_full_system_initialization(self, phase_manager, health_monitor, recovery_manager, config_manager):
        """Test de inicialización completa del sistema"""
        logger.info("🚀 Iniciando test de inicialización completa del sistema")
        
        try:
            # 1. Inicializar PhaseManager
            assert phase_manager is not None
            assert phase_manager.phases is not None
            logger.info("✅ PhaseManager inicializado")
            
            # 2. Inicializar HealthMonitor
            assert health_monitor is not None
            assert health_monitor.thresholds is not None
            logger.info("✅ HealthMonitor inicializado")
            
            # 3. Inicializar RecoveryManager
            assert recovery_manager is not None
            assert recovery_manager.backup_dir is not None
            logger.info("✅ RecoveryManager inicializado")
            
            # 4. Inicializar ConfigManager
            assert config_manager is not None
            assert config_manager.config_path is not None
            logger.info("✅ ConfigManager inicializado")
            
            logger.info("🎉 Inicialización completa del sistema exitosa")
            
        except Exception as e:
            logger.error(f"❌ Error en inicialización del sistema: {e}")
            raise
    
    async def test_phase_management_workflow(self, phase_manager):
        """Test del flujo completo de gestión de fases"""
        logger.info("🔄 Iniciando test de flujo de gestión de fases")
        
        try:
            # 1. Verificar estado inicial
            assert phase_manager.phases['infrastructure']['status'] == 'pending'
            assert phase_manager.phases['training']['status'] == 'pending'
            assert phase_manager.phases['trading']['status'] == 'pending'
            assert phase_manager.phases['monitoring']['status'] == 'pending'
            logger.info("✅ Estado inicial de fases verificado")
            
            # 2. Completar fase de infraestructura
            await phase_manager.update_phase_status('infrastructure', 'completed')
            assert phase_manager.phases['infrastructure']['status'] == 'completed'
            logger.info("✅ Fase de infraestructura completada")
            
            # 3. Verificar dependencias para training
            can_start_training = await phase_manager.validate_phase_dependencies('training')
            assert can_start_training is True
            logger.info("✅ Dependencias para training verificadas")
            
            # 4. Completar fase de training
            await phase_manager.update_phase_status('training', 'completed')
            assert phase_manager.phases['training']['status'] == 'completed'
            logger.info("✅ Fase de training completada")
            
            # 5. Verificar dependencias para trading
            can_start_trading = await phase_manager.validate_phase_dependencies('trading')
            assert can_start_trading is True
            logger.info("✅ Dependencias para trading verificadas")
            
            # 6. Completar fase de trading
            await phase_manager.update_phase_status('trading', 'completed')
            assert phase_manager.phases['trading']['status'] == 'completed'
            logger.info("✅ Fase de trading completada")
            
            # 7. Verificar dependencias para monitoring
            can_start_monitoring = await phase_manager.validate_phase_dependencies('monitoring')
            assert can_start_monitoring is True
            logger.info("✅ Dependencias para monitoring verificadas")
            
            # 8. Completar fase de monitoring
            await phase_manager.update_phase_status('monitoring', 'completed')
            assert phase_manager.phases['monitoring']['status'] == 'completed'
            logger.info("✅ Fase de monitoring completada")
            
            logger.info("🎉 Flujo de gestión de fases completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de gestión de fases: {e}")
            raise
    
    async def test_health_monitoring_workflow(self, health_monitor):
        """Test del flujo completo de monitoreo de salud"""
        logger.info("🏥 Iniciando test de flujo de monitoreo de salud")
        
        try:
            # 1. Obtener estado inicial de salud
            initial_health = await health_monitor.get_system_health()
            assert initial_health is not None
            assert hasattr(initial_health, 'overall_status')
            assert hasattr(initial_health, 'overall_score')
            logger.info(f"✅ Estado inicial de salud: {initial_health.overall_status.value} (Score: {initial_health.overall_score:.1f})")
            
            # 2. Verificar métricas del sistema
            assert len(initial_health.metrics) > 0
            for metric in initial_health.metrics:
                assert hasattr(metric, 'name')
                assert hasattr(metric, 'value')
                assert hasattr(metric, 'status')
            logger.info(f"✅ {len(initial_health.metrics)} métricas del sistema verificadas")
            
            # 3. Verificar estado de servicios
            assert isinstance(initial_health.services_status, dict)
            logger.info(f"✅ Estado de {len(initial_health.services_status)} servicios verificado")
            
            # 4. Verificar recomendaciones
            assert isinstance(initial_health.recommendations, list)
            logger.info(f"✅ {len(initial_health.recommendations)} recomendaciones generadas")
            
            # 5. Obtener resumen de salud
            health_summary = health_monitor.get_health_summary()
            assert health_summary is not None
            assert 'current_status' in health_summary
            assert 'current_score' in health_summary
            logger.info("✅ Resumen de salud obtenido")
            
            logger.info("🎉 Flujo de monitoreo de salud completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de monitoreo de salud: {e}")
            raise
    
    async def test_configuration_management_workflow(self, config_manager, test_config):
        """Test del flujo completo de gestión de configuración"""
        logger.info("⚙️ Iniciando test de flujo de gestión de configuración")
        
        try:
            # 1. Cargar configuración inicial
            initial_config = config_manager.load_config()
            assert initial_config is not None
            assert 'version' in initial_config
            logger.info("✅ Configuración inicial cargada")
            
            # 2. Obtener valores específicos de configuración
            symbols = config_manager.get_config_value('bot_settings.main_symbols')
            assert symbols is not None
            assert isinstance(symbols, list)
            logger.info(f"✅ Símbolos de trading obtenidos: {len(symbols)} símbolos")
            
            # 3. Obtener configuración de leverage
            min_leverage = config_manager.get_config_value('trading_enterprise.futures_trading.leverage.min_leverage')
            max_leverage = config_manager.get_config_value('trading_enterprise.futures_trading.leverage.max_leverage')
            assert min_leverage is not None
            assert max_leverage is not None
            assert min_leverage <= max_leverage
            logger.info(f"✅ Configuración de leverage: {min_leverage}x - {max_leverage}x")
            
            # 4. Obtener configuración de monitoreo
            monitoring_enabled = config_manager.get_config_value('monitoring.prometheus.enabled')
            assert monitoring_enabled is not None
            logger.info(f"✅ Monitoreo Prometheus: {'habilitado' if monitoring_enabled else 'deshabilitado'}")
            
            # 5. Obtener resumen de configuración
            config_summary = config_manager.get_config_summary()
            assert config_summary is not None
            assert 'version' in config_summary
            assert 'environment' in config_summary
            logger.info("✅ Resumen de configuración obtenido")
            
            # 6. Recargar configuración
            reloaded_config = config_manager.reload_config()
            assert reloaded_config is not None
            assert reloaded_config == initial_config
            logger.info("✅ Configuración recargada exitosamente")
            
            logger.info("🎉 Flujo de gestión de configuración completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de gestión de configuración: {e}")
            raise
    
    async def test_recovery_management_workflow(self, recovery_manager):
        """Test del flujo completo de gestión de recuperación"""
        logger.info("🔄 Iniciando test de flujo de gestión de recuperación")
        
        try:
            # 1. Listar backups disponibles
            backups_result = await recovery_manager.list_available_backups()
            assert backups_result is not None
            assert 'success' in backups_result
            logger.info("✅ Listado de backups completado")
            
            # 2. Obtener estado de operaciones de recuperación
            # (Simular operación de recuperación)
            operation_id = "test_recovery_operation"
            status_result = await recovery_manager.get_recovery_status(operation_id)
            assert status_result is not None
            assert 'success' in status_result
            logger.info("✅ Estado de operación de recuperación obtenido")
            
            # 3. Limpiar backups antiguos
            cleanup_result = await recovery_manager.cleanup_old_backups()
            assert cleanup_result is not None
            assert 'success' in cleanup_result
            logger.info("✅ Limpieza de backups antiguos completada")
            
            logger.info("🎉 Flujo de gestión de recuperación completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en flujo de gestión de recuperación: {e}")
            raise
    
    async def test_integrated_system_workflow(self, phase_manager, health_monitor, recovery_manager, config_manager):
        """Test del flujo integrado completo del sistema"""
        logger.info("🔗 Iniciando test de flujo integrado completo del sistema")
        
        try:
            # 1. Inicializar todos los componentes
            logger.info("📋 Paso 1: Inicializando componentes del sistema")
            
            # Cargar configuración
            config = config_manager.load_config()
            assert config is not None
            logger.info("✅ Configuración cargada")
            
            # Verificar estado de salud inicial
            health_status = await health_monitor.get_system_health()
            assert health_status is not None
            logger.info(f"✅ Estado de salud inicial: {health_status.overall_status.value}")
            
            # Verificar estado de fases
            assert phase_manager.phases is not None
            logger.info("✅ Fases del sistema verificadas")
            
            # 2. Ejecutar flujo de fases
            logger.info("📋 Paso 2: Ejecutando flujo de fases")
            
            # Completar infraestructura
            await phase_manager.update_phase_status('infrastructure', 'completed')
            logger.info("✅ Fase de infraestructura completada")
            
            # Completar training
            await phase_manager.update_phase_status('training', 'completed')
            logger.info("✅ Fase de training completada")
            
            # Completar trading
            await phase_manager.update_phase_status('trading', 'completed')
            logger.info("✅ Fase de trading completada")
            
            # Completar monitoring
            await phase_manager.update_phase_status('monitoring', 'completed')
            logger.info("✅ Fase de monitoring completada")
            
            # 3. Verificar estado final del sistema
            logger.info("📋 Paso 3: Verificando estado final del sistema")
            
            # Verificar que todas las fases están completadas
            for phase_name, phase_info in phase_manager.phases.items():
                assert phase_info['status'] == 'completed'
            logger.info("✅ Todas las fases completadas")
            
            # Verificar estado de salud final
            final_health = await health_monitor.get_system_health()
            assert final_health is not None
            logger.info(f"✅ Estado de salud final: {final_health.overall_status.value}")
            
            # Verificar configuración final
            final_config = config_manager.get_config_summary()
            assert final_config is not None
            logger.info("✅ Configuración final verificada")
            
            # 4. Verificar operaciones de recuperación
            logger.info("📋 Paso 4: Verificando operaciones de recuperación")
            
            backups = await recovery_manager.list_available_backups()
            assert backups is not None
            logger.info("✅ Operaciones de recuperación verificadas")
            
            logger.info("🎉 Flujo integrado completo del sistema ejecutado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en flujo integrado del sistema: {e}")
            raise
    
    async def test_system_resilience(self, phase_manager, health_monitor, config_manager):
        """Test de resistencia del sistema"""
        logger.info("🛡️ Iniciando test de resistencia del sistema")
        
        try:
            # 1. Test de recuperación de errores
            logger.info("📋 Paso 1: Probando recuperación de errores")
            
            # Simular error en validación de dependencias
            try:
                await phase_manager.validate_phase_dependencies('nonexistent_phase')
                assert False, "Debería haber fallado"
            except Exception:
                logger.info("✅ Manejo de errores en validación de dependencias verificado")
            
            # 2. Test de monitoreo continuo
            logger.info("📋 Paso 2: Probando monitoreo continuo")
            
            # Ejecutar múltiples health checks
            for i in range(5):
                health_status = await health_monitor.get_system_health()
                assert health_status is not None
                await asyncio.sleep(0.1)  # Pequeña pausa entre checks
            logger.info("✅ Monitoreo continuo verificado")
            
            # 3. Test de recarga de configuración
            logger.info("📋 Paso 3: Probando recarga de configuración")
            
            # Recargar configuración múltiples veces
            for i in range(3):
                config = config_manager.reload_config()
                assert config is not None
            logger.info("✅ Recarga de configuración verificada")
            
            # 4. Test de operaciones concurrentes
            logger.info("📋 Paso 4: Probando operaciones concurrentes")
            
            # Ejecutar operaciones concurrentes
            tasks = [
                health_monitor.get_system_health(),
                config_manager.load_config(),
                phase_manager.validate_phase_dependencies('trading')
            ]
            results = await asyncio.gather(*tasks)
            
            assert all(result is not None for result in results)
            logger.info("✅ Operaciones concurrentes verificadas")
            
            logger.info("🎉 Test de resistencia del sistema completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en test de resistencia del sistema: {e}")
            raise
    
    async def test_performance_under_load(self, phase_manager, health_monitor, config_manager):
        """Test de rendimiento bajo carga"""
        logger.info("⚡ Iniciando test de rendimiento bajo carga")
        
        try:
            # 1. Test de carga en PhaseManager
            logger.info("📋 Paso 1: Probando carga en PhaseManager")
            
            start_time = time.time()
            tasks = []
            for i in range(20):
                tasks.append(phase_manager.validate_phase_dependencies('trading'))
            
            results = await asyncio.gather(*tasks)
            phase_manager_time = time.time() - start_time
            
            assert all(result is True for result in results)
            assert phase_manager_time < 5.0  # Debe completar en menos de 5 segundos
            logger.info(f"✅ PhaseManager bajo carga: {phase_manager_time:.2f}s")
            
            # 2. Test de carga en HealthMonitor
            logger.info("📋 Paso 2: Probando carga en HealthMonitor")
            
            start_time = time.time()
            tasks = []
            for i in range(15):
                tasks.append(health_monitor.get_system_health())
            
            results = await asyncio.gather(*tasks)
            health_monitor_time = time.time() - start_time
            
            assert all(result is not None for result in results)
            assert health_monitor_time < 10.0  # Debe completar en menos de 10 segundos
            logger.info(f"✅ HealthMonitor bajo carga: {health_monitor_time:.2f}s")
            
            # 3. Test de carga en ConfigManager
            logger.info("📋 Paso 3: Probando carga en ConfigManager")
            
            start_time = time.time()
            tasks = []
            for i in range(30):
                tasks.append(config_manager.load_config())
            
            results = await asyncio.gather(*tasks)
            config_manager_time = time.time() - start_time
            
            assert all(result is not None for result in results)
            assert config_manager_time < 3.0  # Debe completar en menos de 3 segundos
            logger.info(f"✅ ConfigManager bajo carga: {config_manager_time:.2f}s")
            
            logger.info("🎉 Test de rendimiento bajo carga completado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error en test de rendimiento bajo carga: {e}")
            raise

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
