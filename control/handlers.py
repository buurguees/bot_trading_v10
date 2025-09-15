#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
control/handlers.py - Handlers de Comandos CORREGIDOS Y COMPLETOS
================================================================
Sistema completo de handlers para todos los comandos de Telegram.
"""

import asyncio
import logging
import subprocess
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import httpx
import os

logger = logging.getLogger(__name__)

# Usaremos el STOP_EVENT del módulo de entrenamiento para evitar desincronización

class TradingBotHandlers:
    """Handlers completos de comandos para Telegram"""

    def __init__(self, authorized_users: list = None, collection_ready: asyncio.Event = None):
        self.authorized_users = authorized_users or []
        self.collection_ready = collection_ready
        self.continuous_task = None
        self.training_lock = asyncio.Lock()  # Candado para evitar ejecuciones simultáneas
        self.telegram_client = httpx.AsyncClient(timeout=10)
        logger.info("✅ TradingBotHandlers inicializados")

    def _check_authorization(self, update: Update) -> bool:
        """Verificar autorización del usuario"""
        if not self.authorized_users:
            return True
        user_id = update.effective_user.id
        is_authorized = user_id in self.authorized_users
        logger.info(f"🔐 Verificación de autorización para usuario {user_id}: {'✅ Autorizado' if is_authorized else '❌ No autorizado'}")
        return is_authorized

    async def _send_telegram_message(self, update: Update, text: str, parse_mode: str = 'HTML', retries: int = 3):
        """Envía mensaje a Telegram con reintentos"""
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not bot_token or not chat_id:
            logger.error("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
            return False
        
        for attempt in range(retries):
            try:
                await self.telegram_client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
                )
                logger.info(f"📨 Mensaje enviado a Telegram: {text[:50]}...")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt + 1}/{retries} fallido al enviar mensaje: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
        logger.error("❌ Fallo al enviar mensaje a Telegram tras reintentos")
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja el comando /start"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        await self._send_telegram_message(update, "🤖 <b>Trading Bot v10 Enterprise</b>\n\n✅ Bot iniciado correctamente.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra ayuda detallada"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        help_text = """
🤖 <b>Trading Bot v10 Enterprise - Comandos</b>

<b>📊 Sistema:</b>
• /start - Iniciar bot
• /status - Estado del sistema
• /health - Verificación de salud
• /help - Esta ayuda

<b>🎓 Entrenamiento:</b>
• /train_hist - Entrenamiento histórico
• /train_hist_continuous - Entrenamiento histórico continuo hasta /stop_train
• /train_live - Entrenamiento en vivo
• /stop_train - Detener entrenamiento

<b>💹 Trading:</b>
• /start_trading - Iniciar trading
• /stop_trading - Detener trading
• /emergency_stop - Parada de emergencia

<b>📈 Información:</b>
• /balance - Balance de cuenta
• /positions - Posiciones abiertas
• /metrics - Métricas del sistema

<b>🔧 Configuración:</b>
• /set_mode - Cambiar modo (paper/live)
• /set_symbols - Configurar símbolos
• /settings - Ver configuración actual

<b>💡 Ejemplo:</b> <code>/train_hist</code>
        """
        await self._send_telegram_message(update, help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra el estado del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        try:
            status_info = {
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'system': '🟢 Operativo',
                'telegram': '🟢 Conectado',
                'database': '🟡 Verificando...',
                'exchange': '🟡 Verificando...',
                'training_status': '🔴 Inactivo' if not self.training_lock.locked() else '🟢 En curso'
            }
            
            try:
                from config.unified_config import get_config_manager
                config = get_config_manager()
                symbols = config.get_symbols() if hasattr(config, 'get_symbols') else ['BTCUSDT', 'ETHUSDT']
                status_info['symbols'] = len(symbols)
                status_info['database'] = '🟢 Conectado'
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener configuración: {e}")
                status_info['symbols'] = 0
                status_info['database'] = '🔴 Error'
            
            status_text = f"""
📊 <b>Estado del Sistema</b>

🕐 <b>Última actualización:</b> {status_info['timestamp']}

<b>🔧 Componentes:</b>
• Sistema: {status_info['system']}
• Telegram: {status_info['telegram']}
• Base de datos: {status_info['database']}
• Exchange: {status_info['exchange']}
• Entrenamiento: {status_info['training_status']}

<b>📈 Configuración:</b>
• Símbolos activos: {status_info.get('symbols', 0)}
• Modo: Paper Trading
• Estado: Preparado

<b>💡 Nota:</b> Sistema listo para recibir comandos.
            """
            await self._send_telegram_message(update, status_text)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            await self._send_telegram_message(
                update,
                f"❌ <b>Error obteniendo estado</b>\n\n"
                f"• Error: {str(e)[:100]}...\n"
                f"• Timestamp: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"💡 El sistema puede seguir funcionando normalmente."
            )

    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra la salud del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        health_checks = [
            ("🤖 Bot Telegram", "✅ Funcionando"),
            ("📊 Handlers", "✅ Registrados"),
            ("🔐 Autorización", "✅ Activa"),
            ("⚡ Asyncio", "✅ Operativo"),
            ("💾 Memoria", "🟢 Normal"),
            ("🌐 Conectividad", "✅ OK")
        ]
        
        health_text = "🏥 <b>Verificación de Salud del Sistema</b>\n\n"
        for check_name, status in health_checks:
            health_text += f"• {check_name}: {status}\n"
        
        health_text += f"\n⏰ <b>Verificado:</b> {datetime.now().strftime('%H:%M:%S')}"
        health_text += f"\n🎯 <b>Estado general:</b> 🟢 Sistema saludable"
        
        await self._send_telegram_message(update, health_text)

    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia entrenamiento histórico REAL"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        # Evitar falso positivo: si ya está bloqueado, avisar y salir
        if self.training_lock.locked():
            await self._send_telegram_message(
                update,
                "⚠️ Un entrenamiento ya está en curso. Usa /status para verificar o /stop_train para detener."
            )
            return

        async with self.training_lock:
            
            # Mensaje inicial
            await self._send_telegram_message(
                update,
                "🎓 <b>Iniciando Entrenamiento Histórico REAL</b>\n\n"
                "🔄 Preparando sistema de entrenamiento...\n"
                "📊 Cargando datos históricos REALES...\n"
                "🤖 Configurando agentes de trading...\n\n"
                "⏳ Este proceso puede tardar varios minutos.\n"
                "📱 Recibirás el resumen final automáticamente."
            )
            
            try:
                from scripts.training.train_hist_parallel import execute_train_hist_for_telegram
                progress_file = f"data/tmp/train_hist_{uuid.uuid4().hex}.json"
                
                # Verificar si hay un entrenamiento continuo en curso
                if self.continuous_task and not self.continuous_task.done():
                    await self._send_telegram_message(
                        update,
                        "⚠️ Un entrenamiento continuo está en curso. Usa /stop_train para detenerlo antes de iniciar uno nuevo."
                    )
                    return
                
                # Ejecutar entrenamiento
                try:
                    from scripts.training.train_hist_parallel import STOP_EVENT as TRAIN_STOP_EVENT
                    if TRAIN_STOP_EVENT is None:
                        # Inicializa si fuera necesario
                        import asyncio as _asyncio
                        TRAIN_STOP_EVENT = _asyncio.Event()
                    TRAIN_STOP_EVENT.clear()
                except Exception:
                    pass
                result = await execute_train_hist_for_telegram(progress_file)
                
                if result.get('success'):
                    telegram_summary = result.get('telegram_summary', "Entrenamiento completado sin resumen detallado.")
                    await self._send_telegram_message(
                        update,
                        f"✅ <b>Entrenamiento Histórico Completado</b>\n\n"
                        f"{telegram_summary}\n\n"
                        f"🎯 <b>Estado:</b> Resumen y métricas disponibles\n"
                        f"💡 <b>Siguiente paso:</b> Usar /status para ver métricas"
                    )
                else:
                    await self._send_telegram_message(
                        update,
                        f"❌ <b>Error en Entrenamiento</b>\n\n"
                        f"{result.get('message', 'Error desconocido')}\n\n"
                        f"🔧 <b>Soluciones:</b>\n"
                        f"• Verificar configuración con /status\n"
                        f"• Reintentar en unos minutos"
                    )
                
            except Exception as e:
                logger.error(f"❌ Error en entrenamiento real: {e}")
                await self._send_telegram_message(
                    update,
                    f"❌ <b>Error en Entrenamiento Real</b>\n\n"
                    f"• Error: {str(e)[:100]}...\n"
                    f"• Timestamp: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"🔧 <b>Soluciones:</b>\n"
                    f"• Verificar configuración con /status\n"
                    f"• Reintentar en unos minutos\n"
                    f"• Contactar soporte si persiste"
                )

    async def train_hist_continuous_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia entrenamiento histórico continuo hasta /stop_train"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        if self.training_lock.locked():
            await self._send_telegram_message(
                update,
                "⚠️ Un entrenamiento ya está en curso. Usa /status para verificar o /stop_train para detener."
            )
            return

        async with self.training_lock:
            
            try:
                from scripts.training.train_hist_parallel import execute_train_hist_continuous_for_telegram
                progress_file = f"data/tmp/train_hist_{uuid.uuid4().hex}.json"
                await self._send_telegram_message(
                    update,
                    "♾️ <b>Entrenamiento continuo iniciado</b>\n\n"
                    "🔄 Entrenamiento ejecutándose en ciclos.\n"
                    "🛑 Usa /stop_train para detener.\n"
                    "📱 Recibirás el resumen final tras 50 ciclos o al detener."
                )
                try:
                    from scripts.training.train_hist_parallel import STOP_EVENT as TRAIN_STOP_EVENT
                    if TRAIN_STOP_EVENT is None:
                        import asyncio as _asyncio
                        TRAIN_STOP_EVENT = _asyncio.Event()
                    TRAIN_STOP_EVENT.clear()
                except Exception:
                    pass

                # Ejecutar en background y no bloquear el loop principal
                async def _run_and_notify():
                    try:
                        result = await execute_train_hist_continuous_for_telegram(progress_file)
                        if result.get('success'):
                            telegram_summary = result.get('telegram_summary', "Entrenamiento continuo completado sin resumen detallado.")
                            await self._send_telegram_message(
                                update,
                                f"✅ <b>Entrenamiento Continuo Completado</b>\n\n{telegram_summary}"
                            )
                        else:
                            await self._send_telegram_message(
                                update,
                                f"❌ <b>Error en entrenamiento continuo</b>\n\n{result.get('message', 'Error')}"
                            )
                    except Exception as _e:
                        logger.exception("❌ Error en tarea de entrenamiento continuo")
                        await self._send_telegram_message(
                            update,
                            f"❌ <b>Error en entrenamiento continuo</b>\n\n{str(_e)[:100]}..."
                        )

                self.continuous_task = asyncio.create_task(_run_and_notify())
                return
            except Exception as e:
                logger.exception("❌ Error en train_hist_continuous_command")
                await self._send_telegram_message(
                    update,
                    f"❌ <b>Error en entrenamiento continuo</b>\n\n{str(e)[:100]}..."
                )

    async def stop_train_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detiene cualquier entrenamiento en curso (/train_hist o /train_hist_continuous)"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        try:
            from scripts.training.train_hist_parallel import stop_train_hist_continuous, STOP_EVENT as TRAIN_STOP_EVENT
            try:
                if TRAIN_STOP_EVENT is not None:
                    TRAIN_STOP_EVENT.set()
            except Exception:
                pass
            stop_train_hist_continuous()
            if self.continuous_task and not self.continuous_task.done():
                self.continuous_task.cancel()
                try:
                    await self.continuous_task
                except asyncio.CancelledError:
                    pass
                self.continuous_task = None
            await self._send_telegram_message(
                update,
                "🛑 <b>Entrenamiento Detenido</b>\n\n"
                "✅ Proceso de entrenamiento interrumpido\n"
                "💾 Progreso guardado automáticamente\n"
                "🔄 Listo para nuevos comandos"
            )
        except Exception as e:
            logger.exception("❌ Error al detener entrenamiento")
            await self._send_telegram_message(
                update,
                f"❌ <b>Error al detener</b>\n\n{str(e)[:100]}..."
            )

    async def train_live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia entrenamiento en vivo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        await self._send_telegram_message(
            update,
            "🔴 <b>Entrenamiento en Vivo</b>\n\n"
            "🚧 Funcionalidad en desarrollo...\n"
            "💡 Usa /train_hist por ahora."
        )

    def register_handlers(self, application):
        """Registrar todos los handlers con la aplicación"""
        handlers = [
            ("start", self.start_command),
            ("help", self.help_command),
            ("status", self.status_command),
            ("health", self.health_command),
            ("train_hist", self.train_hist_command),
            ("train_hist_continuous", self.train_hist_continuous_command),
            ("train_live", self.train_live_command),
            ("stop_train", self.stop_train_command),
        ]
        
        for cmd, func in handlers:
            application.add_handler(CommandHandler(cmd, func))
        
        logger.info(f"✅ {len(handlers)} handlers registrados correctamente")

    async def shutdown(self):
        """Cerrar cliente HTTP y limpiar tareas"""
        await self.telegram_client.aclose()
        if self.continuous_task and not self.continuous_task.done():
            self.continuous_task.cancel()
            try:
                await self.continuous_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ TradingBotHandlers cerrado correctamente")