#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
control/telegram_bot.py - Bot de Telegram CORREGIDO
==================================================
Versión corregida que funciona sin imports circulares.
"""

import os
import logging
import asyncio
from typing import Optional, List
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Bot
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class TelegramBot:
    """Bot de Telegram que REALMENTE funciona"""
    
    def __init__(self, token: str, chat_id: str, authorized_users: List[int] = None, collection_ready: asyncio.Event = None):
        if not token:
            raise ValueError("Token de Telegram requerido")
        if not chat_id:
            raise ValueError("Chat ID requerido")
        
        self.token = token
        self.chat_id = chat_id
        self.authorized_users = authorized_users or []
        self.collection_ready = collection_ready
        
        # CREAR BOT Y APPLICATION
        self.bot = Bot(token=token)
        self.application = Application.builder().token(token).build()
        
        # IMPORTAR HANDLERS AQUÍ (evita import circular)
        from control.handlers import TradingBotHandlers
        self.handlers = TradingBotHandlers(authorized_users=self.authorized_users, collection_ready=collection_ready)
        
        # REGISTRAR HANDLERS
        self._register_handlers()
        
        logger.info(f"✅ TelegramBot inicializado para chat {chat_id}")
    
    def _register_handlers(self):
        """Registrar todos los handlers con el application"""
        try:
            self.handlers.register_handlers(self.application)
            logger.info("✅ Handlers registrados correctamente")
        except Exception as e:
            logger.error(f"❌ Error registrando handlers: {e}")
            raise
    
    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Enviar mensaje al chat configurado"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"✅ Mensaje enviado: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            return False
    
    async def start_polling(self):
        """Iniciar polling del bot con manejo robusto de errores"""
        try:
            logger.info("🔄 Iniciando polling de Telegram...")
            
            # ENVIAR MENSAJE DE INICIO
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\n\n"
                    "✅ Sistema iniciado correctamente\n"
                    "🔄 Esperando comandos...\n\n"
                    "<b>Comandos disponibles:</b>\n"
                    "• /start - Iniciar bot\n"
                    "• /status - Estado del sistema\n"
                    "• /health - Salud del sistema\n"
                    "• /train_hist - Entrenar modelos\n"
                    "• /help - Ver todos los comandos"
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje inicial: {e}")
            
            # INICIALIZAR APPLICATION
            await self.application.initialize()
            await self.application.start()
            
            # INICIAR POLLING
            await self.application.updater.start_polling(
                timeout=30,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
            # Mantener el bot activo
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Bot detenido por usuario")
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            raise
        finally:
            # Cleanup
            if self.application.updater.running:
                await self.application.stop()
    
    @classmethod
    def from_env(cls, authorized_users: List[int] = None, collection_ready: asyncio.Event = None):
        """Crear bot desde variables de entorno"""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN no configurado en .env")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID no configurado en .env")
        
        return cls(token=token, chat_id=chat_id, authorized_users=authorized_users, collection_ready=collection_ready)

# ===== FUNCIÓN DE UTILIDAD =====

async def create_and_start_telegram_bot(authorized_users: List[int] = None, collection_ready: asyncio.Event = None):
    """Crear e iniciar bot de Telegram desde variables de entorno"""
    try:
        bot = TelegramBot.from_env(authorized_users=authorized_users, collection_ready=collection_ready)
        await bot.start_polling()
        return bot
    except Exception as e:
        logger.error(f"❌ Error creando/iniciando bot: {e}")
        raise

if __name__ == "__main__":
    # CONFIGURAR LOGGING
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # EJECUTAR BOT
    asyncio.run(create_and_start_telegram_bot())