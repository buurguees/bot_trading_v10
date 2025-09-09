#!/usr/bin/env python3
"""
Tests para Telegram Bot - Trading Bot v10 Enterprise
===================================================

Tests unitarios y de integración para el bot de Telegram.
Incluye tests para comandos, envío de mensajes y métricas.

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Agregar src al path para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from notifications.telegram.telegram_bot import TelegramBot
from notifications.telegram.handlers import Handlers
from notifications.telegram.metrics_sender import MetricsSender

class TestTelegramBot:
    """Tests para la clase TelegramBot"""
    
    @pytest.fixture
    def mock_config(self):
        """Configuración mock para testing"""
        return {
            'telegram': {
                'bot_token': 'test_token',
                'chat_id': '123456789',
                'enabled': True,
                'metrics_interval': 60,
                'alert_thresholds': {
                    'pnl_alert': 1000,
                    'risk_alert': 10,
                    'latency_alert': 100
                }
            }
        }
    
    @pytest.fixture
    def telegram_bot(self, mock_config, tmp_path):
        """Instancia de TelegramBot para testing"""
        # Crear archivo de configuración temporal
        config_file = tmp_path / "test_config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(mock_config, f)
        
        return TelegramBot(str(config_file))
    
    @pytest.mark.asyncio
    async def test_telegram_bot_initialization(self, telegram_bot):
        """Test de inicialización del bot"""
        assert telegram_bot.bot_token == 'test_token'
        assert telegram_bot.chat_id == '123456789'
        assert telegram_bot.enabled is True
        assert telegram_bot.metrics_interval == 60
        assert telegram_bot.is_running is False
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, telegram_bot):
        """Test de envío exitoso de mensaje"""
        with patch('notifications.telegram.telegram_bot.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            result = await telegram_bot.send_message("Test message")
            
            assert result is True
            mock_bot.send_message.assert_called_once_with(
                chat_id='123456789',
                text="Test message",
                parse_mode="HTML"
            )
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self, telegram_bot):
        """Test de fallo en envío de mensaje"""
        with patch('notifications.telegram.telegram_bot.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = Exception("Network error")
            mock_bot_class.return_value = mock_bot
            
            result = await telegram_bot.send_message("Test message")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_alert(self, telegram_bot):
        """Test de envío de alerta"""
        with patch.object(telegram_bot, 'send_message') as mock_send:
            mock_send.return_value = True
            
            result = await telegram_bot.send_alert("Test alert", "WARNING")
            
            assert result is True
            mock_send.assert_called_once_with(
                "🚨 <b>[WARNING]</b>\n\nTest alert"
            )
    
    def test_is_authorized(self, telegram_bot):
        """Test de autorización de chat"""
        assert telegram_bot.is_authorized(123456789) is True
        assert telegram_bot.is_authorized(987654321) is False
    
    def test_update_config(self, telegram_bot):
        """Test de actualización de configuración"""
        new_config = {
            'telegram': {
                'bot_token': 'new_token',
                'chat_id': '987654321',
                'enabled': False,
                'metrics_interval': 120,
                'alert_thresholds': {'pnl_alert': 2000}
            }
        }
        
        telegram_bot.update_config(new_config)
        
        assert telegram_bot.chat_id == '987654321'
        assert telegram_bot.enabled is False
        assert telegram_bot.metrics_interval == 120

class TestHandlers:
    """Tests para la clase Handlers"""
    
    @pytest.fixture
    def mock_telegram_bot(self):
        """Bot de Telegram mock para testing"""
        bot = MagicMock()
        bot.chat_id = '123456789'
        bot.is_authorized.return_value = True
        return bot
    
    @pytest.fixture
    def handlers(self, mock_telegram_bot):
        """Instancia de Handlers para testing"""
        return Handlers(mock_telegram_bot)
    
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
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_start_command(self, handlers, mock_update, mock_context):
        """Test del comando /start"""
        await handlers.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Trading Bot v10 Enterprise" in call_args
        assert "/status" in call_args
    
    @pytest.mark.asyncio
    async def test_help_command(self, handlers, mock_update, mock_context):
        """Test del comando /help"""
        await handlers.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Guía de Comandos" in call_args
        assert "/status" in call_args
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, handlers, mock_update, mock_context):
        """Test de acceso no autorizado"""
        handlers.telegram_bot.is_authorized.return_value = False
        
        await handlers.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("❌ Acceso no autorizado.")
    
    @pytest.mark.asyncio
    async def test_status_command_with_mock_data(self, handlers, mock_update, mock_context):
        """Test del comando /status con datos mock"""
        with patch.object(handlers, '_get_system_status') as mock_get_status:
            mock_get_status.return_value = {
                'balance': 10000.0,
                'positions': 2,
                'trades_today': 5,
                'win_rate': 75.0,
                'health_score': 95.0,
                'last_update': '12:00:00'
            }
            
            await handlers.status_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Balance: $10,000.00" in call_args
            assert "Posiciones: 2" in call_args
    
    @pytest.mark.asyncio
    async def test_metrics_command_with_mock_data(self, handlers, mock_update, mock_context):
        """Test del comando /metrics con datos mock"""
        with patch.object(handlers, '_get_system_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                'balance': 10000.0,
                'pnl_today': 250.0,
                'win_rate': 75.0,
                'drawdown': 2.5,
                'latency': 45.0,
                'trades_today': 5
            }
            
            await handlers.metrics_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Balance: $10,000.00" in call_args
            assert "PnL Hoy: $250.00" in call_args
    
    @pytest.mark.asyncio
    async def test_positions_command_empty(self, handlers, mock_update, mock_context):
        """Test del comando /positions sin posiciones"""
        with patch.object(handlers, '_get_open_positions') as mock_get_positions:
            mock_get_positions.return_value = []
            
            await handlers.positions_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once_with("📭 No hay posiciones abiertas.")
    
    @pytest.mark.asyncio
    async def test_positions_command_with_data(self, handlers, mock_update, mock_context):
        """Test del comando /positions con datos"""
        with patch.object(handlers, '_get_open_positions') as mock_get_positions:
            mock_get_positions.return_value = [
                {
                    'symbol': 'BTCUSDT',
                    'side': 'long',
                    'pnl': 150.0,
                    'pnl_pct': 1.5,
                    'size': 0.1,
                    'price': 50000.0
                }
            ]
            
            await handlers.positions_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "BTCUSDT" in call_args
            assert "PnL: $150.00" in call_args

class TestMetricsSender:
    """Tests para la clase MetricsSender"""
    
    @pytest.fixture
    def mock_telegram_bot(self):
        """Bot de Telegram mock para testing"""
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value=True)
        return bot
    
    @pytest.fixture
    def mock_config(self):
        """Configuración mock para testing"""
        return {
            'metrics_interval': 60,
            'alert_thresholds': {
                'pnl_alert': 1000,
                'risk_alert': 10,
                'latency_alert': 100
            }
        }
    
    @pytest.fixture
    def metrics_sender(self, mock_telegram_bot, mock_config):
        """Instancia de MetricsSender para testing"""
        return MetricsSender(mock_telegram_bot, mock_config)
    
    def test_initialization(self, metrics_sender):
        """Test de inicialización del MetricsSender"""
        assert metrics_sender.metrics_interval == 60
        assert metrics_sender.alert_thresholds['pnl_alert'] == 1000
        assert metrics_sender.is_running is False
    
    @pytest.mark.asyncio
    async def test_get_current_metrics_simulated(self, metrics_sender):
        """Test de obtención de métricas simuladas"""
        metrics = await metrics_sender.get_current_metrics()
        
        assert 'balance' in metrics
        assert 'pnl_today' in metrics
        assert 'win_rate' in metrics
        assert 'drawdown' in metrics
        assert 'latency' in metrics
        assert 'trades_today' in metrics
    
    def test_format_metrics_message(self, metrics_sender):
        """Test de formateo de mensaje de métricas"""
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
        
        message = metrics_sender.format_metrics_message(metrics)
        
        assert "Métricas del Sistema" in message
        assert "Balance: $10,000.00" in message
        assert "PnL Hoy: $250.00" in message
        assert "Win Rate: 75.0%" in message
    
    @pytest.mark.asyncio
    async def test_check_pnl_alert_positive(self, metrics_sender):
        """Test de alerta de PnL positivo"""
        metrics = {'pnl_today': 1500.0}
        
        with patch.object(metrics_sender.telegram_bot, 'send_alert') as mock_send_alert:
            await metrics_sender._check_pnl_alert(metrics)
            
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args[0][0]
            assert "¡Excelente PnL!" in call_args
            assert "$1,500.00" in call_args
    
    @pytest.mark.asyncio
    async def test_check_pnl_alert_negative(self, metrics_sender):
        """Test de alerta de PnL negativo"""
        metrics = {'pnl_today': -1500.0}
        
        with patch.object(metrics_sender.telegram_bot, 'send_alert') as mock_send_alert:
            await metrics_sender._check_pnl_alert(metrics)
            
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args[0][0]
            assert "Pérdida significativa" in call_args
            assert "$-1,500.00" in call_args
    
    @pytest.mark.asyncio
    async def test_check_drawdown_alert(self, metrics_sender):
        """Test de alerta de drawdown"""
        metrics = {'drawdown': 15.0}
        
        with patch.object(metrics_sender.telegram_bot, 'send_alert') as mock_send_alert:
            await metrics_sender._check_drawdown_alert(metrics)
            
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args[0][0]
            assert "Drawdown Alto" in call_args
            assert "15.0%" in call_args
    
    @pytest.mark.asyncio
    async def test_check_latency_alert(self, metrics_sender):
        """Test de alerta de latencia"""
        metrics = {'latency': 150.0}
        
        with patch.object(metrics_sender.telegram_bot, 'send_alert') as mock_send_alert:
            await metrics_sender._check_latency_alert(metrics)
            
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args[0][0]
            assert "Latencia Alta" in call_args
            assert "150.0ms" in call_args
    
    def test_should_send_alert_no_history(self, metrics_sender):
        """Test de envío de alerta sin historial"""
        assert metrics_sender._should_send_alert("test_alert") is True
    
    def test_should_send_alert_with_cooldown(self, metrics_sender):
        """Test de envío de alerta con cooldown"""
        from datetime import datetime, timedelta
        
        # Simular alerta enviada hace 1 minuto
        metrics_sender.alert_history["test_alert"] = datetime.now() - timedelta(minutes=1)
        
        assert metrics_sender._should_send_alert("test_alert") is False
    
    def test_should_send_alert_after_cooldown(self, metrics_sender):
        """Test de envío de alerta después del cooldown"""
        from datetime import datetime, timedelta
        
        # Simular alerta enviada hace 10 minutos
        metrics_sender.alert_history["test_alert"] = datetime.now() - timedelta(minutes=10)
        
        assert metrics_sender._should_send_alert("test_alert") is True
    
    def test_record_alert(self, metrics_sender):
        """Test de registro de alerta"""
        metrics_sender._record_alert("test_alert")
        
        assert "test_alert" in metrics_sender.alert_history
        assert isinstance(metrics_sender.alert_history["test_alert"], datetime)
    
    def test_stop(self, metrics_sender):
        """Test de detención del MetricsSender"""
        metrics_sender.is_running = True
        metrics_sender.stop()
        
        assert metrics_sender.is_running is False
    
    def test_update_config(self, metrics_sender):
        """Test de actualización de configuración"""
        new_config = {
            'metrics_interval': 120,
            'alert_thresholds': {'pnl_alert': 2000}
        }
        
        metrics_sender.update_config(new_config)
        
        assert metrics_sender.metrics_interval == 120
        assert metrics_sender.alert_thresholds['pnl_alert'] == 2000
    
    def test_get_status(self, metrics_sender):
        """Test de obtención de estado"""
        metrics_sender.is_running = True
        metrics_sender._record_alert("test_alert")
        
        status = metrics_sender.get_status()
        
        assert status['is_running'] is True
        assert status['metrics_interval'] == 60
        assert status['total_alerts_sent'] == 1

# Tests de integración
class TestTelegramIntegration:
    """Tests de integración para el bot de Telegram"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """Test del flujo completo del bot"""
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
