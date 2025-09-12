# control/handlers.py - Actualizado para eliminar comandos de datos y mantener solo entrenamiento

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

logger = logging.getLogger(__name__)

class TradingBotHandlers:
    """Handlers de comandos para Telegram, solo entrenamiento y estado"""

    def __init__(self, authorized_users: list = None, collection_ready: asyncio.Event = None):
        self.authorized_users = authorized_users or []
        self.collection_ready = collection_ready
        logger.info("✅ Handlers inicializados para comandos de entrenamiento")

    def _check_authorization(self, update: Update) -> bool:
        """Verificar autorización del usuario"""
        if not self.authorized_users:
            return True
        user_id = update.effective_user.id
        return user_id in self.authorized_users

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja el comando /start"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        await update.message.reply_text(
            "🤖 <b>Trading Bot v10 Enterprise</b>\n"
            "✅ Bot iniciado. Usa /help para ver comandos disponibles.",
            parse_mode='HTML'
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra el estado del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        try:
            from core.data.database import db_manager
            from config.unified_config import get_config_manager
            cfg = get_config_manager()
            symbols = cfg.get_symbols()
            status = "📊 <b>Estado del Sistema</b>\n"
            for symbol in symbols:
                last_ts = db_manager.get_last_timestamp(symbol, "1h")
                if last_ts:
                    last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    status += f"• {symbol}: Último dato {last_date}\n"
                else:
                    status += f"• {symbol}: Sin datos\n"
            await update.message.reply_text(status, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estado: {e}", parse_mode='HTML')

    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra la salud del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        try:
            health = "🩺 <b>Salud del Sistema</b>\n"
            health += "• Bot: Activo\n"
            health += f"• Colección en tiempo real: {'Activa' if self.collection_ready.is_set() else 'Inactiva'}\n"
            await update.message.reply_text(health, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Error verificando salud: {e}", parse_mode='HTML')

    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia entrenamiento histórico"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        try:
            progress_id = str(uuid.uuid4())
            process = subprocess.Popen(
                ["python", "scripts/training/train_historical.py", "--progress_id", progress_id],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
            )
            await update.message.reply_text(f"🚀 Iniciando entrenamiento histórico (ID: {progress_id})...", parse_mode='HTML')
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                result = json.loads(stdout)
                await update.message.reply_text(
                    f"✅ <b>Entrenamiento histórico completado</b>\n{result.get('report', '')}",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(f"❌ <b>Error en entrenamiento</b>\n{stderr}", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Error en entrenamiento: {e}", parse_mode='HTML')

    async def train_live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia entrenamiento en vivo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        await update.message.reply_text("🚀 Iniciando entrenamiento en vivo...", parse_mode='HTML')

    async def stop_train_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detiene el entrenamiento"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        await update.message.reply_text("🛑 Entrenamiento detenido.", parse_mode='HTML')

    def register_handlers(self, application):
        """Registrar handlers de entrenamiento y estado"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("train_hist", self.train_hist_command))
        application.add_handler(CommandHandler("train_live", self.train_live_command))
        application.add_handler(CommandHandler("stop_train", self.stop_train_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("health", self.health_command))
        logger.info("✅ Handlers de entrenamiento y estado registrados")