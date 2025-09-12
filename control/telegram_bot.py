# control/telegram_bot.py - VERSIÓN CORREGIDA QUE FUNCIONA

import os
import logging
import asyncio
from typing import Optional, List
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Bot

# IMPORTAR LOS HANDLERS CORREGIDOS
from control.handlers import TradingBotHandlers

logger = logging.getLogger(__name__)

class TelegramBot:
    """Bot de Telegram que REALMENTE ejecuta comandos"""
    
    def __init__(self, token: str, chat_id: str, authorized_users: List[int] = None):
        if not token:
            raise ValueError("Token de Telegram requerido")
        if not chat_id:
            raise ValueError("Chat ID requerido")
        
        self.token = token
        self.chat_id = chat_id
        self.authorized_users = authorized_users or []
        
        # CREAR BOT Y APPLICATION
        self.bot = Bot(token=token)
        self.application = Application.builder().token(token).build()
        
        # INICIALIZAR HANDLERS REALES
        self.handlers = TradingBotHandlers(authorized_users=self.authorized_users)
        
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
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")
            raise
    
    async def start_polling(self):
        """Iniciar polling del bot"""
        try:
            logger.info("🔄 Iniciando polling de Telegram...")
            
            # ENVIAR MENSAJE DE INICIO
            await self.send_message(
                "🚀 <b>Bot Trading v10 Enterprise</b>\n\n"
                "✅ Sistema iniciado y comandos funcionando\n"
                "📱 Usa /help para ver comandos disponibles\n"
                "🔧 Todos los comandos usan módulos core/ reales"
            )
            
            # INICIAR POLLING
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
            # MANTENER VIVO
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("⚠️ Deteniendo bot por interrupción de usuario...")
                
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            raise
        finally:
            # LIMPIAR RECURSOS
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("✅ Bot detenido correctamente")
            except Exception as e:
                logger.error(f"❌ Error deteniendo bot: {e}")
    
    async def stop(self):
        """Detener el bot"""
        try:
            logger.info("🔄 Deteniendo bot de Telegram...")
            
            await self.send_message(
                "🛑 <b>Bot Detenido</b>\n\n"
                "Sistema desconectado correctamente"
            )
            
            if self.application.updater.running:
                await self.application.updater.stop()
            
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("✅ Bot detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot: {e}")
    
    @classmethod
    def from_env(cls, authorized_users: List[int] = None) -> 'TelegramBot':
        """Crear bot desde variables de entorno"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN no configurado en .env")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID no configurado en .env")
        
        return cls(token=token, chat_id=chat_id, authorized_users=authorized_users)

# ===== FUNCIÓN DE UTILIDAD =====

async def create_and_start_telegram_bot(authorized_users: List[int] = None):
    """Crear e iniciar bot de Telegram desde variables de entorno"""
    try:
        bot = TelegramBot.from_env(authorized_users=authorized_users)
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