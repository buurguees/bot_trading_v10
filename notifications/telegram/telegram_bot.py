#!/usr/bin/env python3
"""
Telegram Bot para Trading Bot v10 Enterprise
============================================

Bot de Telegram para monitoreo y control del sistema de trading.
Permite enviar métricas en tiempo real y controlar el bot desde móvil.

Características:
- Envío de métricas periódicas
- Control de trading (start/stop)
- Consulta de posiciones y estado
- Alertas automáticas
- Seguridad con Chat ID restringido

Uso:
    from notifications.telegram.telegram_bot import TelegramBot
    
    bot = TelegramBot()
    await bot.start_polling()

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import logging
import asyncio
import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pydantic import BaseModel, ValidationError
from cryptography.fernet import Fernet

# Agregar src al path para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from notifications.telegram.handlers import Handlers

logger = logging.getLogger(__name__)

class TelegramConfig(BaseModel):
    """Configuración del bot de Telegram"""
    bot_token: str
    chat_id: str
    enabled: bool
    metrics_interval: int
    alert_thresholds: Dict[str, float]

class TelegramBot:
    """Bot de Telegram para Trading Bot v10"""
    
    def __init__(self, config_path: str = 'notifications/telegram/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.bot_token = self._decrypt_token(self.config['telegram']['bot_token'])
        self.chat_id = self.config['telegram']['chat_id']
        self.enabled = self.config['telegram']['enabled']
        self.metrics_interval = self.config['telegram']['metrics_interval']
        self.alert_thresholds = self.config['telegram']['alert_thresholds']
        
        # Inicializar componentes
        self.handlers = Handlers(self)
        self.is_running = False
        self.application = None
        self.controller = None  # Se establecerá después
        
        logger.info("🤖 TelegramBot inicializado")
    
    def set_controller(self, controller):
        """Establece la referencia al controlador principal"""
        self.controller = controller
        self.handlers.set_controller(controller)
        logger.info("✅ Controlador establecido en TelegramBot")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Validar configuración
            TelegramConfig(**config['telegram'])
            return config
            
        except FileNotFoundError:
            logger.error(f"❌ Archivo de configuración no encontrado: {self.config_path}")
            raise
        except ValidationError as e:
            logger.error(f"❌ Configuración inválida: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            raise
    
    def _decrypt_token(self, token: str) -> str:
        """Desencripta el token del bot"""
        try:
            # Si el token está encriptado (empieza con gAAAAA)
            if token.startswith('gAAAAA'):
                encryption_key = os.getenv('ENCRYPTION_KEY')
                if not encryption_key:
                    logger.warning("⚠️ ENCRYPTION_KEY no encontrada, usando token sin encriptar")
                    return token
                
                fernet = Fernet(encryption_key.encode())
                return fernet.decrypt(token.encode()).decode()
            else:
                # Token sin encriptar
                return token
                
        except Exception as e:
            logger.error(f"❌ Error desencriptando token: {e}")
            return token
    
    async def start_polling(self):
        """Inicia el polling del bot de Telegram"""
        if not self.enabled:
            logger.info("⏸️ Bot de Telegram deshabilitado")
            return
        
        try:
            logger.info("🚀 Iniciando bot de Telegram...")
            
            # Crear aplicación
            self.application = Application.builder().token(self.bot_token).build()
            
            # Agregar handlers
            self._setup_handlers()
            
            # Marcar como ejecutándose
            self.is_running = True
            
            logger.info("✅ Bot de Telegram iniciado correctamente")
            logger.info(f"📱 Chat ID autorizado: {self.chat_id}")
            
            # Iniciar polling sin crear nuevo loop
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Mantener el bot corriendo
            while self.is_running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Error iniciando bot de Telegram: {e}")
            raise
    
    def _setup_handlers(self):
        """Configura los handlers del bot"""
        # Comandos principales
        self.application.add_handler(CommandHandler("start", self.handlers.start_command))
        self.application.add_handler(CommandHandler("help", self.handlers.help_command))
        self.application.add_handler(CommandHandler("status", self.handlers.status_command))
        self.application.add_handler(CommandHandler("metrics", self.handlers.metrics_command))
        self.application.add_handler(CommandHandler("positions", self.handlers.positions_command))
        
        # Comandos de control
        self.application.add_handler(CommandHandler("start_trading", self.handlers.start_trading_command))
        self.application.add_handler(CommandHandler("stop_trading", self.handlers.stop_trading_command))
        self.application.add_handler(CommandHandler("emergency_stop", self.handlers.emergency_stop_command))
        
        # Comandos de información
        self.application.add_handler(CommandHandler("balance", self.handlers.balance_command))
        self.application.add_handler(CommandHandler("health", self.handlers.health_command))
        self.application.add_handler(CommandHandler("settings", self.handlers.settings_command))
        
        # Comandos de control avanzado
        self.application.add_handler(CommandHandler("train", self.handlers.train_command))
        self.application.add_handler(CommandHandler("stop_training", self.handlers.stop_training_command))
        self.application.add_handler(CommandHandler("trade", self.handlers.trade_command))
        self.application.add_handler(CommandHandler("stop_trading", self.handlers.stop_trading_command))
        self.application.add_handler(CommandHandler("set_mode", self.handlers.set_mode_command))
        self.application.add_handler(CommandHandler("set_symbols", self.handlers.set_symbols_command))
        self.application.add_handler(CommandHandler("shutdown", self.handlers.shutdown_command))
        
        # Comandos de Agentes y ML
        self.application.add_handler(CommandHandler("agents", self.handlers.agents_command))
        self.application.add_handler(CommandHandler("agent_status", self.handlers.agent_status_command))
        self.application.add_handler(CommandHandler("retrain", self.handlers.retrain_command))
        self.application.add_handler(CommandHandler("model_info", self.handlers.model_info_command))
        self.application.add_handler(CommandHandler("training_status", self.handlers.training_status_command))
        
        # Comandos de Entrenamiento Avanzado
        self.application.add_handler(CommandHandler("train_hist", self.handlers.train_hist_command))
        self.application.add_handler(CommandHandler("train_live", self.handlers.train_live_command))
        self.application.add_handler(CommandHandler("stop_train", self.handlers.stop_train_command))
        
        # Comandos de Datos y Análisis
        self.application.add_handler(CommandHandler("download_data", self.handlers.download_data_command))
        self.application.add_handler(CommandHandler("analyze_data", self.handlers.analyze_data_command))
        self.application.add_handler(CommandHandler("align_data", self.handlers.align_data_command))
        self.application.add_handler(CommandHandler("data_status", self.handlers.data_status_command))
        self.application.add_handler(CommandHandler("backtest", self.handlers.backtest_command))
        
        # Comandos de Trading Avanzado
        self.application.add_handler(CommandHandler("close_position", self.handlers.close_position_command))
        
        # Comandos de Reportes
        self.application.add_handler(CommandHandler("performance_report", self.handlers.performance_report_command))
        self.application.add_handler(CommandHandler("agent_analysis", self.handlers.agent_analysis_command))
        self.application.add_handler(CommandHandler("risk_report", self.handlers.risk_report_command))
        self.application.add_handler(CommandHandler("trades_history", self.handlers.trades_history_command))
        
        # Comandos de Mantenimiento
        self.application.add_handler(CommandHandler("restart_system", self.handlers.restart_system_command))
        self.application.add_handler(CommandHandler("clear_cache", self.handlers.clear_cache_command))
        self.application.add_handler(CommandHandler("update_models", self.handlers.update_models_command))
        
        # Comandos de Configuración Adicional
        self.application.add_handler(CommandHandler("set_leverage", self.handlers.set_leverage_command))
        
        # Handler para mensajes de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.echo_command))
        
        logger.info("✅ Handlers configurados correctamente")
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Envía un mensaje al chat configurado"""
        if not self.enabled or not self.chat_id:
            logger.warning("⚠️ Bot deshabilitado o chat_id no configurado")
            return False
        
        try:
            bot = Bot(token=self.bot_token)
            
            # Si el parse_mode es HTML pero el mensaje no contiene HTML, usar Markdown
            if parse_mode == "HTML" and not ("<" in message and ">" in message):
                parse_mode = "Markdown"
            
            await bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                parse_mode=parse_mode
            )
            logger.info(f"📤 Mensaje enviado: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            # Intentar sin parse_mode si falla
            try:
                bot = Bot(token=self.bot_token)
                await bot.send_message(
                    chat_id=self.chat_id, 
                    text=message
                )
                logger.info(f"📤 Mensaje enviado (sin formato): {message[:50]}...")
                return True
            except Exception as e2:
                logger.error(f"❌ Error enviando mensaje sin formato: {e2}")
                return False
    
    async def send_alert(self, message: str, severity: str = "WARNING") -> bool:
        """Envía una alerta con formato especial"""
        alert_message = f"🚨 <b>[{severity}]</b>\n\n{message}"
        return await self.send_message(alert_message)
    
    async def send_metrics(self) -> bool:
        """Envía métricas del sistema"""
        try:
            from notifications.telegram.metrics_sender import MetricsSender
            sender = MetricsSender(self, self.config['telegram'])
            metrics = await sender.get_current_metrics()
            message = sender.format_metrics_message(metrics)
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error enviando métricas: {e}")
            return False
    
    async def start_metrics_sender(self):
        """Inicia el envío periódico de métricas"""
        try:
            from notifications.telegram.metrics_sender import MetricsSender
            sender = MetricsSender(self, self.config['telegram'])
            
            # Crear tareas para métricas y alertas
            asyncio.create_task(sender.start_sending_metrics())
            asyncio.create_task(sender.start_alert_monitoring())
            
            logger.info("📊 Envío de métricas iniciado")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando envío de métricas: {e}")
    
    def stop(self):
        """Detiene el bot de Telegram"""
        self.is_running = False
        if self.application:
            try:
                # Usar asyncio.create_task en lugar de asyncio.run
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.application.stop())
                else:
                    asyncio.run(self.application.stop())
            except Exception as e:
                logger.error(f"❌ Error deteniendo bot: {e}")
        
        logger.info("🛑 Bot de Telegram detenido")
    
    def is_authorized(self, chat_id: int) -> bool:
        """Verifica si el chat_id está autorizado"""
        return str(chat_id) == self.chat_id
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración del bot"""
        return self.config
    
    def update_config(self, new_config: Dict[str, Any]):
        """Actualiza la configuración del bot"""
        try:
            self.config = new_config
            self.chat_id = new_config['telegram']['chat_id']
            self.enabled = new_config['telegram']['enabled']
            self.metrics_interval = new_config['telegram']['metrics_interval']
            self.alert_thresholds = new_config['telegram']['alert_thresholds']
            
            logger.info("✅ Configuración actualizada")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando configuración: {e}")

# Función de conveniencia para inicializar el bot
async def start_telegram_bot(config_path: str = 'notifications/telegram/config.yaml'):
    """Función de conveniencia para iniciar el bot"""
    bot = TelegramBot(config_path)
    await bot.start_polling()

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/telegram_bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Ejecutar bot
    asyncio.run(start_telegram_bot())
