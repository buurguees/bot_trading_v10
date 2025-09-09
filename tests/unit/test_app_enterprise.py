#!/usr/bin/env python3
"""
Tests para app_enterprise_complete.py
"""

import pytest
import asyncio
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from app_enterprise_complete import EnterpriseTradingBotApp, MenuOption, PerformanceMetrics

class TestPerformanceMetrics:
    """Tests para la clase PerformanceMetrics"""
    
    def test_initialization(self):
        """Test inicialización de métricas"""
        metrics = PerformanceMetrics(
            start_time=1000.0,
            operation_times={},
            error_count=0,
            success_count=0
        )
        
        assert metrics.start_time == 1000.0
        assert metrics.operation_times == {}
        assert metrics.error_count == 0
        assert metrics.success_count == 0
    
    def test_add_operation_time(self):
        """Test agregar tiempo de operación"""
        metrics = PerformanceMetrics(
            start_time=1000.0,
            operation_times={},
            error_count=0,
            success_count=0
        )
        
        metrics.add_operation_time("test_operation", 5.5)
        
        assert metrics.operation_times["test_operation"] == 5.5
    
    def test_get_summary(self):
        """Test obtener resumen de métricas"""
        metrics = PerformanceMetrics(
            start_time=1000.0,
            operation_times={"op1": 2.0, "op2": 3.0},
            error_count=1,
            success_count=2
        )
        
        # Mock time.time() para controlar el tiempo total
        with patch('time.time', return_value=1010.0):
            summary = metrics.get_summary()
        
        assert summary["total_runtime"] == 10.0
        assert summary["operations"] == 2
        assert summary["success_rate"] == 2/3
        assert summary["avg_operation_time"] == 2.5
        assert summary["error_count"] == 1
        assert summary["success_count"] == 2

class TestEnterpriseTradingBotApp:
    """Tests para la clase EnterpriseTradingBotApp"""
    
    @pytest.fixture
    def app(self):
        """Fixture para crear instancia de la app"""
        with patch('app_enterprise_complete.setup_logging'):
            return EnterpriseTradingBotApp(headless=True)
    
    def test_initialization(self, app):
        """Test inicialización de la app"""
        assert app.running is True
        assert app.dashboard_process is None
        assert app.headless is True
        assert isinstance(app.metrics, PerformanceMetrics)
        assert len(app.menu_options) == 13
    
    def test_menu_options_structure(self, app):
        """Test estructura de opciones del menú"""
        for key, option in app.menu_options.items():
            assert isinstance(option, MenuOption)
            assert option.key == key
            assert isinstance(option.description, str)
            assert callable(option.handler)
            assert isinstance(option.requires_data, bool)
            assert isinstance(option.requires_ai, bool)
            assert isinstance(option.timeout, int)
    
    def test_show_banner(self, app, capsys):
        """Test mostrar banner"""
        app.show_banner()
        captured = capsys.readouterr()
        
        assert "TRADING BOT v10" in captured.out
        assert "SISTEMA ENTERPRISE" in captured.out
        assert "Headless" in captured.out
    
    def test_show_main_menu(self, app, capsys):
        """Test mostrar menú principal"""
        app.show_main_menu()
        captured = capsys.readouterr()
        
        assert "MENÚ PRINCIPAL ENTERPRISE" in captured.out
        assert "1. 📥 Descargar datos históricos" in captured.out
        assert "13. ❌ Salir" in captured.out
    
    def test_get_user_choice_valid_input(self, app):
        """Test obtener elección válida del usuario"""
        with patch('builtins.input', return_value="1"):
            choice = app.get_user_choice()
            assert choice == "1"
    
    def test_get_user_choice_invalid_input(self, app):
        """Test manejo de input inválido"""
        with patch('builtins.input', side_effect=["invalid", "15", "1"]):
            choice = app.get_user_choice()
            assert choice == "1"
    
    def test_get_user_choice_keyboard_interrupt(self, app):
        """Test manejo de KeyboardInterrupt"""
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            choice = app.get_user_choice()
            assert choice == "13"
    
    def test_is_option_available(self, app):
        """Test verificación de disponibilidad de opciones"""
        # Opción que no requiere prerequisitos
        option = app.menu_options["1"]
        assert app._is_option_available(option) is True
        
        # Opción que requiere datos (mockear db_manager)
        with patch('data.database.db_manager') as mock_db:
            mock_db.get_data_summary_optimized.return_value = {"total_records": 500}
            option = app.menu_options["3"]
            assert app._is_option_available(option) is False
            
            mock_db.get_data_summary_optimized.return_value = {"total_records": 2000}
            assert app._is_option_available(option) is True
    
    def test_cleanup_processes(self, app):
        """Test limpieza de procesos"""
        # Mock proceso activo
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        app.dashboard_process = mock_process
        
        app._cleanup_processes()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=10)
    
    def test_cleanup_processes_timeout(self, app):
        """Test limpieza de procesos con timeout"""
        # Mock proceso que no termina
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("test", 10)
        app.dashboard_process = mock_process
        
        app._cleanup_processes()
        
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_operation_success(self, app):
        """Test ejecución exitosa de operación"""
        async def test_operation():
            return "success"
        
        result = await app._execute_operation(
            "test_operation",
            test_operation,
            timeout=10
        )
        
        assert result == "success"
        assert app.metrics.success_count == 1
        assert "test_operation" in app.metrics.operation_times
    
    @pytest.mark.asyncio
    async def test_execute_operation_failure(self, app):
        """Test ejecución fallida de operación"""
        async def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await app._execute_operation(
                "failing_operation",
                failing_operation,
                timeout=10
            )
        
        assert app.metrics.error_count == 1
        assert "failing_operation" in app.metrics.operation_times
    
    @pytest.mark.asyncio
    async def test_execute_operation_timeout(self, app):
        """Test timeout en operación"""
        async def slow_operation():
            await asyncio.sleep(2)
            return "success"
        
        with pytest.raises(TimeoutError):
            await app._execute_operation(
                "slow_operation",
                slow_operation,
                timeout=1
            )
        
        assert app.metrics.error_count == 1
    
    @pytest.mark.asyncio
    async def test_download_historical_data(self, app):
        """Test descarga de datos históricos"""
        with patch.object(app, '_get_years_input', return_value=2):
            with patch.object(app, '_download_data_async') as mock_download:
                await app.download_historical_data()
                
                mock_download.assert_called_once_with(2)
    
    @pytest.mark.asyncio
    async def test_get_years_input_valid(self, app):
        """Test obtener años válidos"""
        with patch('builtins.input', return_value="3"):
            years = await app._get_years_input()
            assert years == 3
    
    @pytest.mark.asyncio
    async def test_get_years_input_invalid_then_valid(self, app):
        """Test obtener años con input inválido luego válido"""
        with patch('builtins.input', side_effect=["invalid", "6", "2"]):
            years = await app._get_years_input()
            assert years == 2
    
    @pytest.mark.asyncio
    async def test_get_years_input_keyboard_interrupt(self, app):
        """Test obtener años con KeyboardInterrupt"""
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            years = await app._get_years_input()
            assert years == 1
    
    @pytest.mark.asyncio
    async def test_validate_ai_components(self, app):
        """Test validación de componentes IA"""
        # Mock imports
        with patch('models.adaptive_trainer.adaptive_trainer') as mock_trainer, \
             patch('models.prediction_engine.prediction_engine') as mock_engine, \
             patch('models.confidence_estimator.confidence_estimator') as mock_confidence:
            
            # Mock responses
            mock_trainer.get_training_status.return_value = {
                'is_trained': True,
                'last_update': '2024-01-01',
                'accuracy': 0.85
            }
            mock_engine.health_check.return_value = {
                'status': 'healthy',
                'last_prediction': '2024-01-01'
            }
            mock_confidence.health_check.return_value = {
                'is_calibrated': True,
                'last_calibration': '2024-01-01'
            }
            
            await app._validate_ai_components()
            
            mock_trainer.get_training_status.assert_called_once()
            mock_engine.health_check.assert_called_once()
            mock_confidence.health_check.assert_called_once()
    
    def test_signal_handler(self, app):
        """Test manejo de señales"""
        with patch.object(app, '_cleanup_processes'):
            app._signal_handler(signal.SIGINT, None)
            assert app.running is False

class TestIntegration:
    """Tests de integración"""
    
    @pytest.mark.asyncio
    async def test_app_run_headless(self):
        """Test ejecución completa en modo headless"""
        with patch('app_enterprise_complete.setup_logging'):
            app = EnterpriseTradingBotApp(headless=True)
            
            # Mock get_user_choice para salir inmediatamente
            with patch.object(app, 'get_user_choice', return_value="13"):
                # Ejecutar por un tiempo muy corto
                task = asyncio.create_task(app.run())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    def test_cli_arguments(self):
        """Test argumentos CLI"""
        from app_enterprise_complete import main
        
        # Test help
        with patch('sys.argv', ['app_enterprise_complete.py', '--help']):
            with pytest.raises(SystemExit):
                main()
        
        # Test opción específica
        with patch('sys.argv', ['app_enterprise_complete.py', '--option', '1', '--headless']):
            with patch('asyncio.run'):
                with patch('app_enterprise_complete.EnterpriseTradingBotApp'):
                    main()

# Tests de performance
class TestPerformance:
    """Tests de performance"""
    
    @pytest.mark.asyncio
    async def test_operation_timing(self):
        """Test timing de operaciones"""
        with patch('app_enterprise_complete.setup_logging'):
            app = EnterpriseTradingBotApp(headless=True)
            
            async def test_operation():
                await asyncio.sleep(0.1)
                return "done"
            
            await app._execute_operation("test", test_operation, timeout=1)
            
            assert "test" in app.metrics.operation_times
            assert app.metrics.operation_times["test"] >= 0.1
            assert app.metrics.success_count == 1

# Tests de configuración
class TestConfiguration:
    """Tests de configuración"""
    
    def test_enterprise_integration_available(self):
        """Test integración enterprise disponible"""
        with patch('app_enterprise_complete.setup_logging'):
            with patch('core.enterprise_config.EnterpriseConfigManager'):
                app = EnterpriseTradingBotApp(headless=True)
                assert app.enterprise_config is not None
    
    def test_enterprise_integration_unavailable(self):
        """Test integración enterprise no disponible"""
        with patch('app_enterprise_complete.setup_logging'):
            with patch('core.enterprise_config.EnterpriseConfigManager', side_effect=ImportError):
                app = EnterpriseTradingBotApp(headless=True)
                assert app.enterprise_config is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
