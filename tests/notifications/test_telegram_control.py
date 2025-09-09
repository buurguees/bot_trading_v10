#!/usr/bin/env python3
"""
Tests para Control de Telegram - Trading Bot v10 Enterprise
==========================================================

Tests para el sistema de control completo de Telegram.
Incluye tests para comandos, seguridad y integración.

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Agregar src al path para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from notifications.telegram.telegram_bot import TelegramBot
from notifications.telegram.handlers import Handlers
from src.core.integration.system_utils import CommandParser, ConfirmationManager, MetricsFormatter
from src.core.security.telegram_security import TelegramSecurity

class TestCommandParser:
    """Tests para el parser de comandos"""
    
    def test_parse_train_command_basic(self):
        """Test de parsing básico de comando train"""
        args = ['BTCUSDT', 'ETHUSDT']
        result = CommandParser.parse_train_command(args)
        
        assert result['symbols'] == ['BTCUSDT', 'ETHUSDT']
        assert result['duration'] == '8h'
        assert result['mode'] == 'enterprise'
    
    def test_parse_train_command_with_options(self):
        """Test de parsing de comando train con opciones"""
        args = ['--symbols', 'BTCUSDT,ETHUSDT,ADAUSDT', '--duration', '4h']
        result = CommandParser.parse_train_command(args)
        
        assert result['symbols'] == ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        assert result['duration'] == '4h'
    
    def test_parse_trade_command_basic(self):
        """Test de parsing básico de comando trade"""
        args = ['--mode', 'paper', '--symbols', 'BTCUSDT,ETHUSDT']
        result = CommandParser.parse_trade_command(args)
        
        assert result['mode'] == 'paper'
        assert result['symbols'] == ['BTCUSDT', 'ETHUSDT']
        assert result['leverage'] == 10
    
    def test_parse_trade_command_live(self):
        """Test de parsing de comando trade en modo live"""
        args = ['--mode', 'live', '--leverage', '20', 'SOLUSDT']
        result = CommandParser.parse_trade_command(args)
        
        assert result['mode'] == 'live'
        assert result['leverage'] == 20
        assert result['symbols'] == ['SOLUSDT']
    
    def test_parse_set_command_mode(self):
        """Test de parsing de comando set mode"""
        args = ['mode', 'live']
        result = CommandParser.parse_set_command(args)
        
        assert result['mode'] == 'live'
    
    def test_parse_set_command_symbols(self):
        """Test de parsing de comando set symbols"""
        args = ['symbols', 'BTCUSDT,ETHUSDT,ADAUSDT']
        result = CommandParser.parse_set_command(args)
        
        assert result['symbols'] == ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']

class TestConfirmationManager:
    """Tests para el manejador de confirmaciones"""
    
    @pytest.fixture
    def confirmation_manager(self):
        """Instancia de ConfirmationManager para testing"""
        return ConfirmationManager(timeout=60)
    
    @pytest.mark.asyncio
    async def test_request_confirmation(self, confirmation_manager):
        """Test de solicitud de confirmación"""
        command = 'trade'
        args = {'mode': 'live', 'symbols': ['BTCUSDT']}
        chat_id = '123456789'
        
        confirmation_id = await confirmation_manager.request_confirmation(
            command, args, chat_id
        )
        
        assert confirmation_id is not None
        assert confirmation_id in confirmation_manager.pending_confirmations
        assert confirmation_manager.pending_confirmations[confirmation_id]['command'] == command
        assert confirmation_manager.pending_confirmations[confirmation_id]['args'] == args
    
    @pytest.mark.asyncio
    async def test_confirm_command(self, confirmation_manager):
        """Test de confirmación de comando"""
        command = 'trade'
        args = {'mode': 'live', 'symbols': ['BTCUSDT']}
        chat_id = '123456789'
        
        # Solicitar confirmación
        confirmation_id = await confirmation_manager.request_confirmation(
            command, args, chat_id
        )
        
        # Confirmar comando
        result = await confirmation_manager.confirm_command(confirmation_id)
        
        assert result is not None
        assert result['command'] == command
        assert result['args'] == args
        assert result['confirmed'] is True
        assert confirmation_id not in confirmation_manager.pending_confirmations
    
    @pytest.mark.asyncio
    async def test_confirm_nonexistent_command(self, confirmation_manager):
        """Test de confirmación de comando inexistente"""
        result = await confirmation_manager.confirm_command('nonexistent_id')
        assert result is None

class TestMetricsFormatter:
    """Tests para el formateador de métricas"""
    
    def test_format_telegram_metrics_positive_pnl(self):
        """Test de formateo de métricas con PnL positivo"""
        metrics = {
            'balance': 10000.0,
            'pnl_today': 250.0,
            'win_rate': 75.0,
            'drawdown': 2.5,
            'latency': 45.0,
            'trades_today': 5,
            'positions': 2,
            'health_score': 95.0
        }
        
        result = MetricsFormatter.format_telegram_metrics(metrics)
        
        assert "📈" in result  # Emoji de PnL positivo
        assert "Balance: $10,000.00" in result
        assert "PnL Hoy: $250.00" in result
        assert "Win Rate: 75.0%" in result
    
    def test_format_telegram_metrics_negative_pnl(self):
        """Test de formateo de métricas con PnL negativo"""
        metrics = {
            'balance': 10000.0,
            'pnl_today': -150.0,
            'win_rate': 60.0,
            'drawdown': 5.0,
            'latency': 80.0,
            'trades_today': 3,
            'positions': 1,
            'health_score': 85.0
        }
        
        result = MetricsFormatter.format_telegram_metrics(metrics)
        
        assert "📉" in result  # Emoji de PnL negativo
        assert "PnL Hoy: $-150.00" in result
    
    def test_format_dashboard_metrics(self):
        """Test de formateo de métricas para dashboard"""
        metrics = {
            'balance': 10000.0,
            'pnl_today': 250.0,
            'win_rate': 75.0,
            'drawdown': 2.5,
            'latency': 45.0,
            'trades_today': 5,
            'positions': 2,
            'health_score': 95.0
        }
        
        result = MetricsFormatter.format_dashboard_metrics(metrics)
        
        assert result['balance'] == 10000.0
        assert result['pnl_today'] == 250.0
        assert result['win_rate'] == 75.0
        assert 'timestamp' in result

class TestTelegramSecurity:
    """Tests para la seguridad de Telegram"""
    
    @pytest.fixture
    def security(self):
        """Instancia de TelegramSecurity para testing"""
        return TelegramSecurity()
    
    def test_validate_chat_id_valid(self, security):
        """Test de validación de chat_id válido"""
        result = security.validate_chat_id('123456789', '123456789')
        assert result is True
    
    def test_validate_chat_id_invalid(self, security):
        """Test de validación de chat_id inválido"""
        result = security.validate_chat_id('123456789', '987654321')
        assert result is False
    
    def test_validate_command_valid(self, security):
        """Test de validación de comando válido"""
        result = security.validate_command('status', [])
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_command_invalid(self, security):
        """Test de validación de comando inválido"""
        result = security.validate_command('invalid_command', [])
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_validate_train_args_valid(self, security):
        """Test de validación de argumentos de train válidos"""
        args = ['--symbols', 'BTCUSDT,ETHUSDT', '--duration', '4h']
        result = security._validate_train_args(args)
        assert len(result['errors']) == 0
    
    def test_validate_train_args_invalid_symbols(self, security):
        """Test de validación de argumentos de train con símbolos inválidos"""
        args = ['--symbols', 'INVALID_SYMBOL', '--duration', '4h']
        result = security._validate_train_args(args)
        assert len(result['errors']) > 0
        assert 'Símbolos inválidos' in result['errors'][0]
    
    def test_validate_trade_args_live_mode(self, security):
        """Test de validación de argumentos de trade en modo live"""
        args = ['--mode', 'live', '--symbols', 'BTCUSDT', '--leverage', '20']
        result = security._validate_trade_args(args)
        assert len(result['errors']) == 0
    
    def test_validate_trade_args_invalid_leverage(self, security):
        """Test de validación de argumentos de trade con leverage inválido"""
        args = ['--mode', 'paper', '--leverage', '50']
        result = security._validate_trade_args(args)
        assert len(result['errors']) > 0
        assert 'Leverage debe estar entre 1 y 30' in result['errors'][0]
    
    def test_is_critical_command(self, security):
        """Test de identificación de comandos críticos"""
        assert security.is_critical_command('trade') is True
        assert security.is_critical_command('shutdown') is True
        assert security.is_critical_command('status') is False
    
    def test_requires_confirmation(self, security):
        """Test de comandos que requieren confirmación"""
        assert security.requires_confirmation('trade') is True
        assert security.requires_confirmation('shutdown') is True
        assert security.requires_confirmation('status') is False
    
    def test_log_command(self, security):
        """Test de registro de comandos"""
        security.log_command('status', [], '123456789', True)
        
        assert len(security.audit_log) == 1
        assert security.audit_log[0]['command'] == 'status'
        assert security.audit_log[0]['success'] is True
    
    def test_generate_security_report(self, security):
        """Test de generación de reporte de seguridad"""
        # Agregar algunos comandos de prueba
        security.log_command('status', [], '123456789', True)
        security.log_command('metrics', [], '123456789', True)
        security.log_command('trade', ['--mode', 'paper'], '123456789', False)
        
        report = security.generate_security_report()
        
        assert 'total_commands' in report
        assert 'successful_commands' in report
        assert 'failed_commands' in report
        assert 'success_rate' in report
        assert 'most_used_commands' in report

class TestTelegramControlIntegration:
    """Tests de integración para el control de Telegram"""
    
    @pytest.fixture
    def mock_controller(self):
        """Controlador mock para testing"""
        controller = MagicMock()
        controller.command_queue = asyncio.Queue()
        controller.is_running = True
        controller.is_training = False
        controller.is_trading = False
        controller.current_mode = "paper"
        controller.current_symbols = ["BTCUSDT", "ETHUSDT"]
        return controller
    
    @pytest.fixture
    def mock_telegram_bot(self):
        """Bot de Telegram mock para testing"""
        bot = MagicMock()
        bot.chat_id = '123456789'
        bot.is_authorized.return_value = True
        bot.send_message = AsyncMock(return_value=True)
        return bot
    
    @pytest.fixture
    def handlers(self, mock_telegram_bot, mock_controller):
        """Handlers con controlador configurado"""
        handlers = Handlers(mock_telegram_bot)
        handlers.controller = mock_controller
        return handlers
    
    @pytest.fixture
    def mock_update(self):
        """Update mock para testing"""
        update = MagicMock()
        update.message.chat_id = 123456789
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Context mock para testing"""
        context = MagicMock()
        context.args = []
        return context
    
    @pytest.mark.asyncio
    async def test_train_command_integration(self, handlers, mock_update, mock_context):
        """Test de integración del comando train"""
        mock_context.args = ['--symbols', 'BTCUSDT,ETHUSDT', '--duration', '4h']
        
        await handlers.train_command(mock_update, mock_context)
        
        # Verificar que se envió respuesta
        mock_update.message.reply_text.assert_called_once()
        
        # Verificar que se agregó comando a la cola
        assert not handlers.controller.command_queue.empty()
    
    @pytest.mark.asyncio
    async def test_trade_command_integration(self, handlers, mock_update, mock_context):
        """Test de integración del comando trade"""
        mock_context.args = ['--mode', 'paper', '--symbols', 'BTCUSDT']
        
        await handlers.trade_command(mock_update, mock_context)
        
        # Verificar que se envió respuesta
        mock_update.message.reply_text.assert_called_once()
        
        # Verificar que se agregó comando a la cola
        assert not handlers.controller.command_queue.empty()
    
    @pytest.mark.asyncio
    async def test_set_mode_command_integration(self, handlers, mock_update, mock_context):
        """Test de integración del comando set_mode"""
        mock_context.args = ['live']
        
        await handlers.set_mode_command(mock_update, mock_context)
        
        # Verificar que se envió respuesta
        mock_update.message.reply_text.assert_called_once()
        
        # Verificar que se agregó comando a la cola
        assert not handlers.controller.command_queue.empty()
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, handlers, mock_update, mock_context):
        """Test de acceso no autorizado"""
        handlers.telegram_bot.is_authorized.return_value = False
        
        await handlers.train_command(mock_update, mock_context)
        
        # Verificar que se envió mensaje de acceso denegado
        mock_update.message.reply_text.assert_called_once_with("❌ Acceso no autorizado.")
    
    @pytest.mark.asyncio
    async def test_controller_not_available(self, handlers, mock_update, mock_context):
        """Test cuando el controlador no está disponible"""
        handlers.controller = None
        
        await handlers.train_command(mock_update, mock_context)
        
        # Verificar que se envió mensaje de error
        mock_update.message.reply_text.assert_called_once_with("❌ Controlador del sistema no disponible.")

class TestSystemIntegration:
    """Tests de integración del sistema completo"""
    
    @pytest.mark.asyncio
    async def test_full_command_flow(self, tmp_path):
        """Test del flujo completo de comandos"""
        # Crear configuración de test
        config = {
            'telegram': {
                'bot_token': 'test_token',
                'chat_id': '123456789',
                'enabled': True,
                'metrics_interval': 60,
                'alert_thresholds': {'pnl_alert': 1000}
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Crear bot
        bot = TelegramBot(str(config_file))
        
        # Mock de la aplicación de Telegram
        with patch('notifications.telegram.telegram_bot.Application') as mock_app:
            mock_application = AsyncMock()
            mock_app.builder.return_value.token.return_value.build.return_value = mock_application
            
            # Test de inicialización
            assert bot.enabled is True
            assert bot.chat_id == '123456789'
            
            # Test de autorización
            assert bot.is_authorized(123456789) is True
            assert bot.is_authorized(987654321) is False

if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v"])
