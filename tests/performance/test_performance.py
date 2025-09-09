#!/usr/bin/env python3
"""
Tests de Performance Enterprise
===============================

Tests de rendimiento para componentes críticos del sistema enterprise.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from deployment.phase_manager import PhaseManager
from deployment.health_monitor import HealthMonitor
from deployment.recovery_manager import RecoveryManager
from config.enterprise_config import EnterpriseConfigManager

@pytest.mark.benchmark
class TestEnterprisePerformance:
    """Tests de performance para componentes enterprise"""
    
    @pytest.fixture
    def config(self):
        """Configuración de prueba"""
        return {
            'version': '1.0.0',
            'bot_settings': {
                'main_symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
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
                }
            },
            'data_collection': {
                'real_time': {
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                    'timeframes': ['1m', '5m', '15m']
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
            }
        }
    
    @pytest.fixture
    def phase_manager(self, config):
        """PhaseManager para tests"""
        return PhaseManager(config)
    
    @pytest.fixture
    def health_monitor(self, config):
        """HealthMonitor para tests"""
        return HealthMonitor(config)
    
    @pytest.fixture
    def recovery_manager(self):
        """RecoveryManager para tests"""
        return RecoveryManager('config/user_settings.yaml')
    
    @pytest.fixture
    def config_manager(self):
        """ConfigManager para tests"""
        return EnterpriseConfigManager('config/user_settings.yaml')
    
    @pytest.mark.asyncio
    async def test_phase_manager_performance(self, benchmark, phase_manager):
        """Test de performance del PhaseManager"""
        async def run_phase_validation():
            return await phase_manager.validate_phase_dependencies('trading')
        
        result = await benchmark(run_phase_validation)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_monitor_performance(self, benchmark, health_monitor):
        """Test de performance del HealthMonitor"""
        async def get_health_status():
            return await health_monitor.get_system_health()
        
        result = await benchmark(get_health_status)
        assert result is not None
        assert hasattr(result, 'overall_status')
        assert hasattr(result, 'overall_score')
    
    @pytest.mark.asyncio
    async def test_recovery_manager_performance(self, benchmark, recovery_manager):
        """Test de performance del RecoveryManager"""
        async def list_backups():
            return await recovery_manager.list_available_backups()
        
        result = await benchmark(list_backups)
        assert result is not None
        assert 'success' in result
    
    def test_config_manager_performance(self, benchmark, config_manager):
        """Test de performance del ConfigManager"""
        def load_config():
            return config_manager.load_config()
        
        result = benchmark(load_config)
        assert result is not None
        assert 'version' in result
    
    def test_config_value_access_performance(self, benchmark, config_manager):
        """Test de performance de acceso a valores de configuración"""
        def get_config_value():
            return config_manager.get_config_value('bot_settings.main_symbols')
        
        result = benchmark(get_config_value)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, health_monitor):
        """Test de health checks concurrentes"""
        async def single_health_check():
            return await health_monitor.get_system_health()
        
        # Ejecutar múltiples health checks concurrentemente
        start_time = time.time()
        tasks = [single_health_check() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todos los checks completaron
        assert len(results) == 10
        assert all(result is not None for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 5.0  # Debe completar en menos de 5 segundos
    
    @pytest.mark.asyncio
    async def test_phase_manager_concurrent_operations(self, phase_manager):
        """Test de operaciones concurrentes del PhaseManager"""
        async def update_phase_status(phase, status):
            await phase_manager.update_phase_status(phase, status)
            return True
        
        # Ejecutar múltiples actualizaciones concurrentemente
        start_time = time.time()
        tasks = [
            update_phase_status('infrastructure', 'completed'),
            update_phase_status('training', 'in_progress'),
            update_phase_status('trading', 'pending'),
            update_phase_status('monitoring', 'pending')
        ]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todas las operaciones completaron
        assert len(results) == 4
        assert all(result is True for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 2.0  # Debe completar en menos de 2 segundos
    
    def test_config_manager_memory_usage(self, config_manager):
        """Test de uso de memoria del ConfigManager"""
        import psutil
        import gc
        
        # Obtener uso de memoria inicial
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Cargar configuración múltiples veces
        for _ in range(100):
            config = config_manager.load_config()
            assert config is not None
        
        # Forzar garbage collection
        gc.collect()
        
        # Obtener uso de memoria final
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verificar que el aumento de memoria es razonable (menos de 10MB)
        assert memory_increase < 10 * 1024 * 1024  # 10MB
    
    @pytest.mark.asyncio
    async def test_health_monitor_metrics_collection(self, health_monitor):
        """Test de recolección de métricas del HealthMonitor"""
        async def collect_metrics():
            health_status = await health_monitor.get_system_health()
            return {
                'cpu_usage': health_status.metrics[0].value if health_status.metrics else 0,
                'memory_usage': health_status.metrics[1].value if len(health_status.metrics) > 1 else 0,
                'overall_score': health_status.overall_score
            }
        
        # Ejecutar recolección de métricas múltiples veces
        start_time = time.time()
        tasks = [collect_metrics() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todas las métricas se recolectaron
        assert len(results) == 20
        assert all('cpu_usage' in result for result in results)
        assert all('memory_usage' in result for result in results)
        assert all('overall_score' in result for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 10.0  # Debe completar en menos de 10 segundos
    
    def test_config_manager_cache_performance(self, config_manager):
        """Test de performance del cache del ConfigManager"""
        # Primera carga (sin cache)
        start_time = time.time()
        config1 = config_manager.load_config()
        first_load_time = time.time() - start_time
        
        # Segunda carga (con cache)
        start_time = time.time()
        config2 = config_manager.load_config()
        second_load_time = time.time() - start_time
        
        # Verificar que la segunda carga es más rápida
        assert second_load_time < first_load_time
        assert config1 == config2
        
        # Verificar que la segunda carga es significativamente más rápida
        speedup = first_load_time / second_load_time
        assert speedup > 2.0  # Al menos 2x más rápido
    
    @pytest.mark.asyncio
    async def test_recovery_manager_backup_listing_performance(self, recovery_manager):
        """Test de performance del listado de backups"""
        async def list_backups():
            return await recovery_manager.list_available_backups()
        
        # Ejecutar listado de backups múltiples veces
        start_time = time.time()
        tasks = [list_backups() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todas las operaciones completaron
        assert len(results) == 5
        assert all('success' in result for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 5.0  # Debe completar en menos de 5 segundos
    
    def test_phase_manager_memory_efficiency(self, phase_manager):
        """Test de eficiencia de memoria del PhaseManager"""
        import psutil
        import gc
        
        # Obtener uso de memoria inicial
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Ejecutar múltiples operaciones
        for _ in range(50):
            phase_manager.phases['infrastructure']['status'] = 'completed'
            phase_manager.phases['training']['status'] = 'in_progress'
            phase_manager.phases['trading']['status'] = 'pending'
            phase_manager.phases['monitoring']['status'] = 'pending'
        
        # Forzar garbage collection
        gc.collect()
        
        # Obtener uso de memoria final
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verificar que el aumento de memoria es mínimo
        assert memory_increase < 1024 * 1024  # Menos de 1MB
    
    @pytest.mark.asyncio
    async def test_health_monitor_alert_performance(self, health_monitor):
        """Test de performance de alertas del HealthMonitor"""
        async def check_alerts():
            health_status = await health_monitor.get_system_health()
            await health_monitor.check_health_alerts(health_status)
            return True
        
        # Ejecutar verificación de alertas múltiples veces
        start_time = time.time()
        tasks = [check_alerts() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todas las operaciones completaron
        assert len(results) == 10
        assert all(result is True for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 3.0  # Debe completar en menos de 3 segundos
    
    def test_config_manager_validation_performance(self, config_manager):
        """Test de performance de validación del ConfigManager"""
        def validate_config():
            config = config_manager.load_config()
            return config_manager.validate_config(config)
        
        # Ejecutar validación múltiples veces
        start_time = time.time()
        results = [validate_config() for _ in range(20)]
        end_time = time.time()
        
        # Verificar que todas las validaciones completaron
        assert len(results) == 20
        assert all(hasattr(result, 'is_valid') for result in results)
        
        # Verificar que el tiempo total es razonable
        total_time = end_time - start_time
        assert total_time < 2.0  # Debe completar en menos de 2 segundos

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
