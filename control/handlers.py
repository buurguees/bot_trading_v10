#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handlers Enterprise - Nodo de Conexión Ligero entre Telegram y Scripts
Versión: Enterprise - Solo conexión, ejecución y forwarding de resultados.
No lógica de negocio; delega a scripts/.
"""

import asyncio
import os
import subprocess
import json
import logging
import uuid
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from core.config.config_loader import ConfigLoader

# Configurar logging enterprise
logger = logging.getLogger(__name__)

class Handlers:
    """Nodo de conexión enterprise: Telegram → Scripts → Telegram"""
    
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.get_main_config()
        self.long_commands = ['/sync_symbols', '/download_data', '/train_hist', '/repair_data', '/verify_align']  # Comandos con progreso
    
    def _check_authorization(self, update: Update) -> bool:
        """Validación básica de autorización (lee control_config, con fallbacks)"""
        chat_id = str(update.message.chat_id)
        try:
            control_cfg = self.config_loader.get_control_config() or {}
        except Exception:
            control_cfg = {}

        authorized_id = str(
            control_cfg.get("telegram", {}).get("chat_id")
            or self.config.get("telegram", {}).get("chat_id")
            or (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or "")
        )
        if authorized_id and chat_id != authorized_id:
            logger.warning(f"🚫 Acceso no autorizado: {chat_id}")
            return False
        return True
    
    def _generate_progress_id(self) -> str:
        """Genera ID único para progreso temporal"""
        return f"progress_{uuid.uuid4().hex[:8]}_{int(asyncio.get_event_loop().time())}"
    
    def _read_progress_file(self, progress_id: str) -> dict:
        """Lee progreso de archivo temporal (JSON)"""
        progress_path = Path("data/tmp") / f"{progress_id}.json"
        if progress_path.exists():
            try:
                with open(progress_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error leyendo progreso {progress_id}: {e}")
        return {"progress": 0, "current_symbol": "N/A", "bar": "", "status": "starting"}
    
    def _delete_progress_file(self, progress_id: str):
        """Borra archivo de progreso al finalizar"""
        progress_path = Path("data/tmp") / f"{progress_id}.json"
        if progress_path.exists():
            progress_path.unlink()
            Path("data/tmp").rmdir() if not list(Path("data/tmp").iterdir()) else None
    
    def _format_progress_message(self, progress_data: dict, command: str) -> str:
        """Formatea mensaje de progreso en HTML"""
        bar = progress_data.get("bar", "░░░░░░░░░░")
        pct = progress_data.get("progress", 0)
        symbol = progress_data.get("current_symbol", "N/A")
        status = progress_data.get("status", "En curso")
        return f"""
🔄 <b>{command.upper()} - Progreso</b>

📊 Estado: {status}
🎯 Símbolo actual: {symbol}
📈 Progreso: {pct}%
{'█' * int(pct/10)}{bar[int(pct/10):]} (10 bloques = 100%)
        """.strip()
    
    async def _execute_long_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, script_name: str, args: list = []):
        """Ejecuta comando largo con progreso editable"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        chat_id = update.message.chat_id
        progress_id = self._generate_progress_id()
        Path("data/tmp").mkdir(exist_ok=True)
        
        # Mensaje inicial
        initial_msg = await update.message.reply_text(f"🔄 Iniciando {script_name}...", parse_mode='HTML')
        message_id = initial_msg.message_id
        
        try:
            # Ejecutar script con progreso_id como arg
            cmd = ["python", f"scripts/{script_name}.py", "--progress_id", progress_id] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitoreo de progreso (cada 5s)
            monitor_task = asyncio.create_task(self._monitor_progress(progress_id, chat_id, message_id, context))
            
            # Esperar fin del proceso
            stdout, stderr = await process.communicate()
            await monitor_task
            
            if process.returncode == 0:
                # Parsear resultados JSON de stdout
                try:
                    results = json.loads(stdout.decode('utf-8'))
                    if results.get("status") == "success":
                        report = results.get("report", "Completado exitosamente.")
                        # Enviar reportes detallados por símbolo con delay
                        if isinstance(report, list):  # Si es lista por símbolo
                            for i, sym_report in enumerate(report):
                                await context.bot.send_message(chat_id=chat_id, text=sym_report, parse_mode='HTML')
                                if i < len(report) - 1:
                                    await asyncio.sleep(5)  # Delay 5s entre símbolos
                        else:
                            await context.bot.send_message(chat_id=chat_id, text=report, parse_mode='HTML')
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=f"❌ {results.get('message', 'Error desconocido.')}", parse_mode='HTML')
                except json.JSONDecodeError:
                    await context.bot.send_message(chat_id=chat_id, text=f"✅ {script_name} completado.\n{stdout.decode('utf-8', errors='ignore')}", parse_mode='HTML')
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')[-2000:] if stderr else 'Error desconocido'
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Error en {script_name}:\n{error_msg}", parse_mode='HTML')
                logger.error(f"Error en {script_name}: {error_msg}")
        
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Error ejecutando {script_name}: {str(e)}", parse_mode='HTML')
            logger.error(f"Error en {script_name}: {e}")
        finally:
            self._delete_progress_file(progress_id)
    
    async def _monitor_progress(self, progress_id: str, chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Monitorea y actualiza progreso cada 5s"""
        while True:
            try:
                progress_data = self._read_progress_file(progress_id)
                if progress_data.get("status") == "completed":
                    break  # Script terminó
                message = self._format_progress_message(progress_data, progress_id.split('_')[1])  # Extrae comando
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=message,
                    parse_mode='HTML'
                )
                await asyncio.sleep(5)  # Check cada 5s
            except Exception as e:
                logger.warning(f"Error monitoreando progreso: {e}")
                await asyncio.sleep(5)
    
    async def _execute_short_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, script_name: str, args: list = []):
        """Ejecuta comando corto sin progreso"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text(f"🔄 Ejecutando {script_name}...")
            cmd = ["python", f"scripts/{script_name}.py"] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                try:
                    results = json.loads(stdout.decode('utf-8'))
                    report = results.get("report", stdout.decode('utf-8', errors='ignore'))
                    if isinstance(report, list):
                        for sym_report in report:
                            await update.message.reply_text(sym_report, parse_mode='HTML')
                            await asyncio.sleep(5)  # Delay entre mensajes
                    else:
                        await update.message.reply_text(report, parse_mode='HTML')
                except json.JSONDecodeError:
                    await update.message.reply_text(stdout.decode('utf-8', errors='ignore'), parse_mode='HTML')
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                await update.message.reply_text(f"❌ Error en {script_name}:\n{error_msg}", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"❌ Error ejecutando {script_name}: {str(e)}")
            logger.error(f"Error en {script_name}: {e}")
    
    # ===== HANDLERS DE COMANDOS =====
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /start - Mensaje de bienvenida """
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        welcome = """
🤖 <b>Bot Trading v10 Enterprise</b>

🔥 Sistema activo y listo para operaciones.
📊 Datos sincronizados y agentes preparados.

<b>Comandos principales:</b>
/help - Lista completa
/status - Estado del sistema
/download_data - Descargar datos históricos
/sync_symbols - Sincronizar símbolos
/train_hist - Entrenamiento histórico
        """
        await update.message.reply_text(welcome, parse_mode='HTML')
        await self._send_commands_after_delay(update, delay_seconds=3)
    
    async def _send_commands_after_delay(self, update: Update, delay_seconds: int = 3):
        """Envía comandos adicionales después de un delay"""
        try:
            await asyncio.sleep(delay_seconds)
            commands_text = """
📋 <b>Comandos rápidos disponibles:</b>

🔧 <b>Datos:</b>
/status - Estado del sistema
/download_data - Descargar datos históricos
/sync_symbols - Sincronizar símbolos

⚡ <b>Entrenamiento:</b>
/train_hist - Entrenamiento histórico

💡 <b>Ayuda:</b>
/help - Lista completa de comandos
            """
            await update.message.reply_text(commands_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error enviando comandos después de delay: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /help - Lista de comandos """
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        help_text = """
<b>🤖 COMANDOS DISPONIBLES - Modo Enterprise</b>

<b>📊 GESTIÓN DE DATOS</b>
/download_data - Descarga y alinea datos históricos (progreso en vivo)
/data_status - Estado detallado de datos y sincronización
/analyze_data - Analiza y repara problemas (duplicados, gaps)
/verify_align - Verifica y alinea temporalmente
/repair_data - Reparación completa enterprise

<b>⚡ SINCRONIZACIÓN Y EJECUCIÓN</b>
/sync_symbols - Sincroniza símbolos para ejecución paralela (progreso en vivo)
/train_hist - Entrenamiento histórico paralelo (progreso en vivo)

<b>🔧 SISTEMA Y MONITOREO</b>
/status - Estado general del sistema
/health - Salud detallada con métricas
/metrics - Métricas avanzadas de rendimiento
/positions - Posiciones abiertas (integra con Bitget API)

<b>🎮 TRADING (Futuro)</b>
/start_trading - Iniciar trading automatizado
/stop_trading - Detener trading
/emergency_stop - Parada de emergencia

💡 <b>Modo Enterprise:</b> Todos los comandos incluyen logging detallado, auditoría y métricas.
Para comandos largos: Progreso en vivo con barra actualizable.
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /status - Estado general """
        await self._execute_short_command(update, context, "data_status", [])
    
    async def download_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /download_data - Descarga histórica con progreso """
        await self._execute_long_command(update, context, "download_data", [])
    
    async def sync_symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /sync_symbols - Sincronización con progreso """
        await self._execute_long_command(update, context, "sync_symbols", [])
    
    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /train_hist - Entrenamiento histórico con progreso """
        await self._execute_long_command(update, context, "train_hist", [])
    
    async def analyze_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /analyze_data - Análisis y reparación básica """
        await self._execute_long_command(update, context, "analyze_data", ["--no-repair"])  # Solo analiza primero
    
    async def repair_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /repair_data - Reparación completa con progreso """
        await self._execute_long_command(update, context, "repair_data", [])
    
    async def verify_align_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /verify_align - Verificación y alineación con progreso """
        await self._execute_long_command(update, context, "verify_align", [])
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /health - Salud del sistema """
        await self._execute_short_command(update, context, "health_check", [])  # Asume script health_check.py
    
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /metrics - Métricas avanzadas """
        await self._execute_short_command(update, context, "metrics", [])
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /positions - Posiciones abiertas (integra Bitget) """
        await self._execute_short_command(update, context, "positions", [])  # Asume script positions.py
    
    # ===== REGISTRO DE HANDLERS =====
    
    def register_handlers(self, application):
        """Registra todos los handlers en la aplicación de Telegram"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("download_data", self.download_data_command))
        application.add_handler(CommandHandler("sync_symbols", self.sync_symbols_command))
        application.add_handler(CommandHandler("train_hist", self.train_hist_command))
        application.add_handler(CommandHandler("analyze_data", self.analyze_data_command))
        application.add_handler(CommandHandler("repair_data", self.repair_data_command))
        application.add_handler(CommandHandler("verify_align", self.verify_align_command))
        application.add_handler(CommandHandler("health", self.health_command))
        application.add_handler(CommandHandler("metrics", self.metrics_command))
        application.add_handler(CommandHandler("positions", self.positions_command))
        
        # Handler para mensajes no comandos
        from telegram.ext import MessageHandler, filters
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_command))
    
    async def echo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensajes no reconocidos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        await update.message.reply_text(
            "🤖 Comando no reconocido. Use /help para ver comandos disponibles.",
            parse_mode='HTML'
        )