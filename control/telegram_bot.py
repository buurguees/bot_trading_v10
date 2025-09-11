# Ruta: control/telegram_bot.py
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
    from control.telegram_bot import TelegramBot
    
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

# Imports locales
from .handlers import Handlers
from core.config.unified_config import unified_config

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
    
    def __init__(self, config_path: str = 'control/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        telegram_cfg = self.config.get('telegram', {})
        # Cargar desde config o .env (admite múltiples nombres de variables)
        env_bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN') or ''
        env_chat_id = os.getenv('TELEGRAM_CHAT_ID') or os.getenv('CHAT_ID') or ''

        # Prioridad: entorno > config. Además, ignora placeholders tipo "TELEGRAM_BOT_TOKEN"/"TELEGRAM_CHAT_ID"
        cfg_token = telegram_cfg.get('bot_token', '')
        cfg_chat = telegram_cfg.get('chat_id', '')
        if isinstance(cfg_token, str) and cfg_token.strip().upper() == 'TELEGRAM_BOT_TOKEN':
            cfg_token = ''
        if isinstance(cfg_chat, str) and cfg_chat.strip().upper() == 'TELEGRAM_CHAT_ID':
            cfg_chat = ''

        self.bot_token = self._decrypt_token(env_bot_token or cfg_token or '')
        self.chat_id = (env_chat_id or cfg_chat or '')
        if isinstance(self.chat_id, str):
            self.chat_id = self.chat_id.strip()
        # Si no se especifica enabled, activar automáticamente si hay credenciales
        enabled_flag = telegram_cfg.get('enabled')
        if enabled_flag is None:
            self.enabled = bool(self.bot_token) and bool(self.chat_id)
        else:
            self.enabled = bool(enabled_flag) and bool(self.bot_token) and bool(self.chat_id)

        # Logs de diagnóstico
        if not self.enabled:
            missing = []
            if not self.bot_token:
                missing.append('bot_token')
            if not self.chat_id:
                missing.append('chat_id')
            logger.warning(f"⚠️ Bot deshabilitado. Faltan: {', '.join(missing) if missing else 'habilitar= true'}")
        self.metrics_interval = telegram_cfg.get('metrics_interval', 60)
        self.alert_thresholds = telegram_cfg.get('alert_thresholds', {})
        
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
            # 1) Archivo local control/config.yaml
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                TelegramConfig(**config.get('telegram', {}))
                return config
            # 2) Fallback a config/control_config.yaml
            alt = Path('config/control_config.yaml')
            if alt.exists():
                with open(alt, 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f) or {}
                # normalizar al mismo esquema
                if 'telegram' not in cfg and cfg:
                    cfg = {'telegram': cfg.get('telegram', cfg)}
                return cfg
            # 3) Fallback a unified_config
            try:
                uc = unified_config.get_section('control') or {}
                if uc:
                    return {'telegram': uc.get('telegram', uc)}
            except Exception:
                pass
            # 4) Fallback final a variables de entorno
            env_cfg = {
                'telegram': {
                    'bot_token': os.getenv('BOT_TOKEN', ''),
                    'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
                    'enabled': False,
                    'metrics_interval': int(os.getenv('TELEGRAM_METRICS_INTERVAL', '60')),
                    'alert_thresholds': {}
                }
            }
            return env_cfg
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Config no encontrada: {self.config_path}. Usando fallbacks y deshabilitando Telegram.")
            return {'telegram': {'bot_token': '', 'chat_id': '', 'enabled': False, 'metrics_interval': 60, 'alert_thresholds': {}}}
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
            
            # Eliminar webhook existente para evitar conflictos
            try:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("✅ Webhook eliminado correctamente")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar webhook: {e}")
            
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
        def _add(cmd: str, attr: str):
            if hasattr(self.handlers, attr):
                self.application.add_handler(CommandHandler(cmd, getattr(self.handlers, attr)))

        # Comandos principales
        _add("start", "start_command")
        _add("help", "help_command")
        _add("status", "status_command")
        _add("metrics", "metrics_command")
        _add("positions", "positions_command")

        # Control (solo si existen)
        _add("start_trading", "start_trading_command")
        _add("stop_trading", "stop_trading_command")
        _add("emergency_stop", "emergency_stop_command")

        # Información
        _add("balance", "balance_command")
        _add("health", "health_command")
        _add("settings", "settings_command")

        # Control avanzado
        _add("train", "train_command")
        _add("stop_training", "stop_training_command")
        _add("trade", "trade_command")
        _add("set_mode", "set_mode_command")
        _add("set_symbols", "set_symbols_command")

        # Datos históricos
        _add("verify_historical_data", "verify_historical_data_command")
        _add("download_historical_data", "download_historical_data_command")
        _add("historical_data_report", "historical_data_report_command")
        _add("verify_align", "verify_align_command")
        _add("sync_symbols", "sync_symbols_command")

        _add("shutdown", "shutdown_command")

        # Agentes y ML
        _add("agents", "agents_command")
        _add("agent_status", "agent_status_command")
        _add("retrain", "retrain_command")
        _add("model_info", "model_info_command")
        _add("training_status", "training_status_command")

        # Entrenamiento
        _add("train_hist", "train_hist_command")
        _add("train_live", "train_live_command")
        _add("stop_train", "stop_train_command")

        # Datos y análisis
        _add("download_data", "download_data_command")
        _add("analyze_data", "analyze_data_command")
        _add("align_data", "align_data_command")
        _add("data_status", "data_status_command")
        _add("backtest", "backtest_command")

        # Historial
        _add("download_history", "download_history_command")
        _add("inspect_history", "inspect_history_command")
        _add("repair_history", "repair_history_command")

        # Trading avanzado
        _add("close_position", "close_position_command")

        # Reportes
        _add("performance_report", "performance_report_command")
        _add("agent_analysis", "agent_analysis_command")
        _add("risk_report", "risk_report_command")
        _add("trades_history", "trades_history_command")

        # Mantenimiento
        _add("restart_system", "restart_system_command")
        _add("clear_cache", "clear_cache_command")
        _add("update_models", "update_models_command")

        # Configuración adicional
        _add("set_leverage", "set_leverage_command")

        # Extras
        _add("reload_config", "reload_config_command")
        _add("reset_agent", "reset_agent_command")
        _add("strategies", "strategies_command")

        # Handler para mensajes de texto (si existe echo)
        try:
            from telegram.ext import MessageHandler, filters
            if hasattr(self.handlers, 'echo_command'):
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.echo_command))
        except Exception:
            pass

        logger.info("✅ Handlers configurados (solo los disponibles)")
    
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
            from .metrics_sender import MetricsSender
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
            from .metrics_sender import MetricsSender
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

# Objeto de conveniencia para compatibilidad con imports antiguos
# Algunos módulos realizan: from control.telegram_bot import telegram_bot
# Exponemos una interfaz mínima diferida.
class _TelegramBotLazy:
    async def send_message(self, *args, **kwargs):
        # Crea una instancia real bajo demanda si se necesita en el futuro
        logging.getLogger(__name__).warning("telegram_bot (lazy) invocado sin inicialización; mensaje no enviado")
        return False

telegram_bot = _TelegramBotLazy()