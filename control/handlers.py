# control/handlers.py - RECTIFICADO PARA /download_data

import asyncio
import logging
import subprocess
import json
import uuid
from pathlib import Path
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

class TradingBotHandlers:
    """Handlers de comandos para Telegram que delegan a scripts/"""
    
    def __init__(self, authorized_users: list = None, collection_ready: asyncio.Event = None):
        self.authorized_users = authorized_users or []
        self.collection_ready = collection_ready
        
        logger.info("✅ Handlers inicializados para delegación a scripts")
    
    def _check_authorization(self, update: Update) -> bool:
        """Verificar autorización del usuario"""
        if not self.authorized_users:
            return True
        user_id = update.effective_user.id
        return user_id in self.authorized_users
    
    async def _monitor_progress(self, update: Update, progress_id: str):
        """Monitorea archivo de progreso y envía actualizaciones a Telegram"""
        progress_path = Path("data/tmp") / f"{progress_id}.json"
        last_progress = -1
        try:
            while True:
                if progress_path.exists():
                    with open(progress_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    progress = data.get("progress", 0)
                    if progress != last_progress:
                        message = f"📥 Progreso: {progress}% - {data.get('current_symbol', 'N/A')} - {data.get('bar', '░░░░░░░░░░')}\nEstado: {data.get('status', 'En curso')}"
                        await update.message.reply_text(message, parse_mode='HTML')
                        last_progress = progress
                    if data.get("status") in ["completed", "error"]:
                        break
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error monitoreando progreso {progress_id}: {e}")
            await update.message.reply_text(f"❌ Error monitoreando progreso: {str(e)}", parse_mode='HTML')
    
    async def data_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra el estado de los datos almacenados"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        try:
            from core.data.database import db_manager
            from config.unified_config import get_config_manager
            
            cfg = get_config_manager()
            symbols = cfg.get_symbols()
            timeframes = cfg.get_timeframes() or ["1m", "5m", "15m", "1h", "4h"]
            
            report = "📊 <b>Estado de Datos Históricos</b>\n\n"
            total_records = 0
            
            for symbol in symbols[:5]:  # Mostrar solo los primeros 5 símbolos
                report += f"<b>🔸 {symbol}:</b>\n"
                symbol_total = 0
                
                for tf in timeframes:
                    try:
                        db_path = f"data/{symbol}/trading_bot.db"
                        if Path(db_path).exists():
                            # Contar registros
                            with db_manager._get_connection(db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT COUNT(*) FROM market_data WHERE symbol = ? AND timeframe = ?",
                                    (symbol, tf)
                                )
                                count = cursor.fetchone()[0]
                                symbol_total += count
                                
                                # Obtener rango de fechas
                                cursor.execute(
                                    "SELECT MIN(timestamp), MAX(timestamp) FROM market_data WHERE symbol = ? AND timeframe = ?",
                                    (symbol, tf)
                                )
                                min_ts, max_ts = cursor.fetchone()
                                
                                if min_ts and max_ts:
                                    min_date = datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d %H:%M')
                                    max_date = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')
                                    report += f"  • {tf}: {count:,} registros ({min_date} - {max_date})\n"
                                else:
                                    report += f"  • {tf}: 0 registros\n"
                        else:
                            report += f"  • {tf}: Sin datos\n"
                    except Exception as e:
                        report += f"  • {tf}: Error ({str(e)[:30]}...)\n"
                
                total_records += symbol_total
                report += f"  <b>Total {symbol}:</b> {symbol_total:,} registros\n\n"
            
            report += f"<b>📈 Total General:</b> {total_records:,} registros"
            
            await update.message.reply_text(report, parse_mode='HTML')
            logger.info(f"📊 Estado de datos consultado: {total_records:,} registros totales")
            
        except Exception as e:
            logger.error(f"❌ Error en data_status: {e}")
            await update.message.reply_text(f"❌ Error obteniendo estado: {str(e)}", parse_mode='HTML')

    async def download_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ejecuta /download_data y monitorea progreso"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        progress_id = str(uuid.uuid4())
        await update.message.reply_text(f"🚀 Iniciando descarga de datos históricos...\n🆔 Progreso ID: {progress_id}", parse_mode='HTML')
        logger.info(f"🚀 Ejecutando /download_data con progress_id: {progress_id}")
        
        # Ejecutar script en background con encoding UTF-8
        process = subprocess.Popen(
            ['python', 'scripts/data/download_data.py', '--progress_id', progress_id],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace'
        )
        
        # Monitorear progreso
        monitor_task = asyncio.create_task(self._monitor_progress(update, progress_id))
        
        # Esperar a que el proceso termine
        stdout, stderr = process.communicate()
        await monitor_task
        
        # Procesar resultado
        try:
            # Decodificar stdout con encoding UTF-8
            if stdout:
                stdout_utf8 = stdout.encode('utf-8', errors='replace').decode('utf-8')
                result = json.loads(stdout_utf8)
            else:
                result = {"status": "error", "message": stderr}
                
            if result.get("status") == "success":
                report = "\n\n".join(result.get("report", ["Sin reporte"]))
                message = f"✅ <b>Descarga Completada</b>\nTotal registros: {result.get('total_downloaded', 0):,}\nSesión: {result.get('session_id', 'N/A')}\n\n{report}"
            else:
                message = f"❌ <b>Error en Descarga</b>\nMensaje: {result.get('message', 'Error desconocido')}"
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ /download_data completado: {result.get('status')}")
        except Exception as e:
            logger.error(f"Error procesando resultado de /download_data: {e}")
            await update.message.reply_text(f"❌ Error procesando resultado: {str(e)}", parse_mode='HTML')
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando de inicio con wait para ready"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        
        await update.message.reply_text("🤖 <b>Bot Trading v10 Enterprise</b>\n\n🔄 Conectando con exchange mientras se descargan datos...", parse_mode='HTML')
        
        if self.collection_ready:
            await self.collection_ready.wait()
        
        commands_message = (
            "🚀 <b>Sistema Completamente Operativo</b>\n\n"
            "<b>📊 Comandos Operativos:</b>\n"
            "/download_data\n"
            "/data_status\n"
            "/analyze_data\n"
            "/verify_align\n"
            "/repair_history\n"
            "/sync_symbols\n"
            "/train_hist\n"
            "/train_live\n"
            "/status\n"
            "/health\n\n"
            "💡 Usa /help para detalles."
        )
        await update.message.reply_text(commands_message, parse_mode='HTML')
    
    async def data_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/data_status.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def analyze_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/analyze_data.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def verify_align_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/verify_align.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def repair_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/repair_history.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def sync_symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/sync_symbols.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/training/train_hist.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def train_live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/training/train_live.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/status.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.", parse_mode='HTML')
            return
        output = await self._execute_script('scripts/data/health.py')
        await update.message.reply_text(output, parse_mode='HTML')
    
    async def _execute_script(self, script_path: str) -> str:
        """Ejecuta script y captura output"""
        try:
            result = subprocess.run(['python', script_path], capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return f"Error en script: {result.stderr}"
            return result.stdout
        except subprocess.TimeoutExpired:
            return "Timeout ejecutando script"
        except Exception as e:
            return f"Error ejecutando script: {str(e)}"
    
    def register_handlers(self, application):
        """Registrar todos los handlers"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("download_data", self.download_data_command))
        application.add_handler(CommandHandler("data_status", self.data_status_command))
        application.add_handler(CommandHandler("analyze_data", self.analyze_data_command))
        application.add_handler(CommandHandler("verify_align", self.verify_align_command))
        application.add_handler(CommandHandler("repair_history", self.repair_history_command))
        application.add_handler(CommandHandler("sync_symbols", self.sync_symbols_command))
        application.add_handler(CommandHandler("train_hist", self.train_hist_command))
        application.add_handler(CommandHandler("train_live", self.train_live_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("health", self.health_command))
        
        logger.info("✅ Todos los handlers registrados para delegación")