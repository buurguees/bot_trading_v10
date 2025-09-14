# control/telegram_bot.py - RECTIFICADO

import os
import logging
import asyncio
from typing import Optional, List
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Bot

# IMPORTAR LOS HANDLERS CORREGIDOS
from control.handlers import TradingBotHandlers
from control.message_queue import TelegramMessageQueue

logger = logging.getLogger(__name__)

class TelegramBot:
    """Bot de Telegram que REALMENTE ejecuta comandos"""
    

    async def start_polling_improved(self):
        """Versión mejorada del polling con manejo de errores"""
        try:
            logger.info("🔄 Iniciando polling de Telegram (versión mejorada)...")
            
            # ENVIAR MENSAJE DE INICIO
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\n\n"
                    "✅ Sistema iniciado\n"
                    "🔄 Conectando con exchange..."
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")
            
            # INICIAR POLLING CON MANEJO DE TIMEOUT
            await self.application.initialize()
            await self.application.start()
            
            # Configurar polling con timeout más corto
            await self.application.updater.start_polling(
                timeout=30,
                drop_pending_updates=True,  # Ignorar actualizaciones pendientes
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
            # Mantener el bot activo
            while True:
                await asyncio.sleep(1)
                
        except asyncio.TimeoutError:
            logger.warning("⚠️ Timeout en polling, reintentando...")
            await asyncio.sleep(5)
            await self.start_polling_improved()
            
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            logger.warning("⚠️ Continuando sin Telegram")

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
        
        # INICIALIZAR HANDLERS REALES con event
        self.handlers = TradingBotHandlers(authorized_users=self.authorized_users, collection_ready=collection_ready)
        
        # INICIALIZAR COLA DE MENSAJES
        self.message_queue = TelegramMessageQueue(self, max_queue_size=50, base_delay=3.0)
        
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
    
    async def send_message(self, message: str, parse_mode: str = "HTML", priority: int = 1):
        """Enviar mensaje usando cola inteligente con control de flood"""
        try:
            await self.message_queue.add_message(message, parse_mode, priority)
            logger.debug(f"📝 Mensaje agregado a cola (prioridad {priority}): {message[:50]}...")
        except Exception as e:
            logger.error(f"❌ Error agregando mensaje a cola: {e}")
    
    async def send_message_immediate(self, message: str, parse_mode: str = "HTML"):
        """Enviar mensaje inmediatamente (para casos críticos)"""
        try:
            # Crear una nueva instancia del bot para evitar problemas de I/O
            temp_bot = Bot(token=self.token)
            
            await temp_bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            
            # Cerrar la sesión del bot temporal
            await temp_bot.close()
            
            logger.debug(f"✅ Mensaje enviado inmediatamente: {message[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje inmediato: {e}")
            # Si falla el envío inmediato, agregar a cola
            await self.send_message(message, parse_mode, priority=1)
    
    async def start_polling(self):
        """Iniciar polling del bot con manejo robusto de errores"""
        try:
            logger.info("🔄 Iniciando polling de Telegram...")
            
            # ENVIAR MENSAJE DE INICIO (conectando)
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\n\n"
                    "✅ Sistema iniciado\n"
                    "🔄 Conectando con exchange mientras se descargan datos..."
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje inicial: {e}")
            
            # INICIAR POLLING CON MANEJO DE TIMEOUT
            await self.application.initialize()
            await self.application.start()
            
            # Configurar polling con timeout más largo y manejo de errores
            await self.application.updater.start_polling(
                timeout=60,  # 60 segundos de timeout
                drop_pending_updates=True  # Ignorar actualizaciones pendientes
            )
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
            # Esperar signal y enviar comandos
            if self.collection_ready:
                try:
                    await self.collection_ready.wait()
                    await self.send_message(
                        "🚀 <b>Sistema Completamente Operativo</b>\n\n"
                        "<b>📊 Comandos de Datos (Funcionando)</b>\n"
                        "/download_data — Verificar y descargar histórico\n"
                        "/data_status — Estado de datos y sincronización\n"
                        "/analyze_data — Analizar y reparar datos\n"
                        "/verify_align — Verificar alineación temporal\n"
                        "/repair_history — Reparación completa de datos\n"
                        "/sync_symbols — Sincronización paralela de símbolos\n\n"
                        "<b>🎓 Comandos de Entrenamiento</b>\n"
                        "/train_hist — Entrenamiento histórico paralelo\n"
                        "/train_live — Entrenamiento en tiempo real\n"
                        "/stop_train — Detener entrenamiento\n\n"
                        "<b>🤖 Comandos del Bot</b>\n"
                        "/status — Estado general del sistema\n"
                        "/health — Verificación de salud del bot\n"
                        "/positions — Posiciones abiertas en Bitget\n"
                        "/balance — Balance de la cuenta\n\n"
                        "<b>📈 Comandos de Trading</b>\n"
                        "/start_trading — Iniciar trading automático\n"
                        "/stop_trading — Detener trading\n"
                        "/emergency_stop — Parada de emergencia\n\n"
                        "💡 Usa /help para ver todos los comandos disponibles."
                    )
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo enviar mensaje de comandos: {e}")
            
            # MANTENER VIVO CON MANEJO DE ERRORES
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("⚠️ Deteniendo bot por interrupción de usuario...")
            except Exception as e:
                logger.error(f"❌ Error en bucle principal: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            # No hacer raise para evitar que el bot se detenga completamente
        finally:
            # LIMPIAR RECURSOS DE FORMA SEGURA
            try:
                if hasattr(self.application, 'updater') and self.application.updater.running:
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
    def from_env(cls, authorized_users: List[int] = None, collection_ready: asyncio.Event = None) -> 'TelegramBot':
        """Crear bot desde variables de entorno"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
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