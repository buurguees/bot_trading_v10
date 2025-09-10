#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handlers simplificados - Nodo de distribución entre Telegram y scripts
"""

import asyncio
import subprocess
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.config_loader import ConfigLoader

# Configurar logging
logger = logging.getLogger(__name__)

class Handlers:
    """Handlers simplificados para comandos de Telegram - Nodo de distribución"""
    
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
    
    def _check_authorization(self, update: Update) -> bool:
        """Verificar autorización del usuario"""
        # Implementar lógica de autorización si es necesario
        return True
    
    def _escape_html(self, text: str) -> str:
        """Escapar caracteres HTML"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#x27;"))
    
    async def _send_commands_after_delay(self, update, delay_seconds: int = 10):
        """Enviar listado de comandos después de un delay"""
        await asyncio.sleep(delay_seconds)
        
        commands_message = """
🤖 <b>COMANDOS DISPONIBLES</b>

<b>📊 DATOS Y ANÁLISIS</b>
<code>/download_data</code> - Descargar datos históricos
<code>/sync_symbols</code> - Sincronizar símbolos
<code>/train_hist</code> - Entrenamiento histórico
<code>/data_status</code> - Estado de los datos

<b>🤖 ENTRENAMIENTO</b>
<code>/train_hist</code> - Entrenamiento histórico paralelo
<code>/sync_symbols</code> - Sincronización de símbolos

<b>📈 TRADING</b>
<code>/start_trading</code> - Iniciar trading
<code>/stop_trading</code> - Detener trading
<code>/positions</code> - Ver posiciones
<code>/balance</code> - Ver balance

<b>🔧 SISTEMA</b>
<code>/status</code> - Estado del sistema
<code>/health</code> - Salud del sistema
<code>/help</code> - Ayuda completa
        """
        
        await update.message.reply_text(commands_message, parse_mode='HTML')
    
    # ===== COMANDOS BÁSICOS =====
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Mensaje de bienvenida"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        welcome_message = """
🤖 <b>Bot Trading v10 - ENTERPRISE</b>

✅ <b>Bot Iniciado</b>
🔄 <b>Conectando con Exchange</b>

<b>📊 Símbolos configurados:</b>
• BTCUSDT, ETHUSDT, ADAUSDT
• SOLUSDT, DOGEUSDT, XRPUSDT

<b>⏰ Timeframes:</b>
• 1m, 5m, 15m, 1h, 4h, 1d

<b>🚀 Sistema listo para operar</b>
        """
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
        
        # Enviar comandos después de 5 segundos
        asyncio.create_task(self._send_commands_after_delay(update, 5))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Lista de comandos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        await self._send_commands_after_delay(update, 0)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Estado del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Ejecutar script de estado
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/system/status.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Error obteniendo estado del sistema")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /status: {e}")
    
    # ===== COMANDOS DE DATOS =====
    
    async def download_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /download_data - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Iniciando descarga de datos...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/data/download_data.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                
                # Buscar reporte en la salida
                if "Reporte de Descarga de Datos" in output:
                    lines = output.split('\n')
                    report_start = -1
                    for i, line in enumerate(lines):
                        if "Reporte de Descarga de Datos" in line:
                            report_start = i
                            break
                    
                    if report_start >= 0:
                        report_lines = lines[report_start:]
                        report = '\n'.join(report_lines).strip()
                        await update.message.reply_text(report, parse_mode='HTML')
                    else:
                        await update.message.reply_text("✅ Descarga completada exitosamente")
                else:
                    await update.message.reply_text("✅ Descarga completada exitosamente")
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
            # Enviar comandos después de 10 segundos
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /download_data: {e}")
    
    async def sync_symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /sync_symbols - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Iniciando sincronización de símbolos...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/data/sync_symbols.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                
                # Buscar reporte en la salida
                if "Reporte de Sincronización" in output:
                    lines = output.split('\n')
                    report_start = -1
                    for i, line in enumerate(lines):
                        if "Reporte de Sincronización" in line:
                            report_start = i
                            break
                    
                    if report_start >= 0:
                        report_lines = lines[report_start:]
                        report = '\n'.join(report_lines).strip()
                        await update.message.reply_text(report, parse_mode='HTML')
                    else:
                        await update.message.reply_text("✅ Sincronización completada exitosamente")
                else:
                    await update.message.reply_text("✅ Sincronización completada exitosamente")
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
            # Enviar comandos después de 10 segundos
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /sync_symbols: {e}")
    
    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /train_hist - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Iniciando entrenamiento histórico...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/training/train_hist.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                
                # Buscar reporte en la salida
                if "Reporte de Entrenamiento" in output:
                    lines = output.split('\n')
                    report_start = -1
                    for i, line in enumerate(lines):
                        if "Reporte de Entrenamiento" in line:
                            report_start = i
                            break
                    
                    if report_start >= 0:
                        report_lines = lines[report_start:]
                        report = '\n'.join(report_lines).strip()
                        await update.message.reply_text(report, parse_mode='HTML')
                    else:
                        await update.message.reply_text("✅ Entrenamiento completado exitosamente")
                else:
                    await update.message.reply_text("✅ Entrenamiento completado exitosamente")
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
            # Enviar comandos después de 10 segundos
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /train_hist: {e}")
    
    # ===== COMANDOS DE TRADING =====
    
    async def start_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start_trading - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Iniciando trading...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/trading/start_trading.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /start_trading: {e}")
    
    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_trading - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Deteniendo trading...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/trading/stop_trading.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /stop_trading: {e}")
    
    # ===== COMANDOS DE INFORMACIÓN =====
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /positions - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Obteniendo posiciones...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/trading/positions.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /positions: {e}")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Obteniendo balance...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/trading/balance.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /balance: {e}")
    
    # ===== COMANDOS DE SISTEMA =====
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /health - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Verificando salud del sistema...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/system/health.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /health: {e}")
    
    # ===== COMANDOS DE DATOS =====
    
    async def data_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /data_status - Nodo de distribución"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔄 Obteniendo estado de datos...")
            
            # Ejecutar script
            process = await asyncio.create_subprocess_exec(
                "python", "scripts/data/data_status.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                await update.message.reply_text(output, parse_mode='HTML')
            else:
                error_text = stderr.decode('utf-8', errors='ignore')[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logger.error(f"Error en /data_status: {e}")
    
    # ===== HANDLER DE MENSAJES =====
    
    async def echo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensajes de texto que no son comandos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        await update.message.reply_text(
            "🤖 Comando no reconocido. Use /help para ver la lista de comandos disponibles."
        )
