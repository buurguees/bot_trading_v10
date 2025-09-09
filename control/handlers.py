#!/usr/bin/env python3
"""
Handlers para Telegram Bot - Trading Bot v10 Enterprise
======================================================

Maneja todos los comandos y mensajes del bot de Telegram.
Incluye comandos de monitoreo, control y información del sistema.

Comandos disponibles:
- /start, /help - Información y ayuda
- /status - Estado general del sistema
- /metrics - Métricas actuales
- /positions - Posiciones abiertas
- /balance - Balance actual
- /health - Salud del sistema
- /start_trading - Iniciar trading
- /stop_trading - Detener trading
- /emergency_stop - Parada de emergencia
- /settings - Configuración actual

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class Handlers:
    """Handlers para comandos de Telegram"""
    
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.alerting_system = None
        self.trading_engine = None
        self.data_provider = None
        self.controller = None  # Referencia al controlador principal
        
        # Inicializar componentes de forma lazy
        self._init_components()
    
    def _init_components(self):
        """Inicializa los componentes del sistema de forma lazy"""
        try:
            # Inicializar componentes básicos sin dependencias complejas
            self.alerting_system = None
            self.trading_engine = None
            self.data_provider = None
            
            logger.info("✅ Handlers inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
    
    def set_controller(self, controller):
        """Establece la referencia al controlador principal"""
        self.controller = controller
        logger.info("✅ Controlador establecido en Handlers")
    
    def _check_authorization(self, update: Update) -> bool:
        """Verifica si el usuario está autorizado"""
        if not self.telegram_bot.is_authorized(update.message.chat_id):
            logger.warning(f"🚫 Acceso no autorizado desde chat_id: {update.message.chat_id}")
            return False
        return True
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Mensaje de bienvenida"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        welcome_message = """
🤖 <b>Trading Bot v10 Enterprise</b>

¡Hola! Soy tu asistente de trading personal. Puedo ayudarte a monitorear y controlar tu bot de trading.

<b>📋 Comandos disponibles:</b>

<b>📊 Monitoreo:</b>
/status - Estado general del sistema
/metrics - Métricas actuales
/positions - Posiciones abiertas
/balance - Balance actual
/health - Salud del sistema

<b>🎮 Control:</b>
/train_hist - Entrenamiento histórico
/train_live - Entrenamiento en vivo
/start_trading - Iniciar trading
/stop_trading - Detener trading
/emergency_stop - Parada de emergencia

<b>⚙️ Configuración:</b>
/settings - Configuración actual
/help - Lista completa de comandos

<b>💡 Tip:</b> Usa /help para ver más detalles sobre cada comando.
        """
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
        logger.info(f"✅ Comando /start ejecutado por chat_id: {update.message.chat_id}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Lista detallada de comandos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        help_message = """
🤖 <b>TRADING BOT v10 - COMANDOS COMPLETOS</b>

<b>📊 MONITOREO Y ESTADO</b>
<code>/status</code> - Estado general del sistema
<code>/metrics</code> - Métricas detalladas en tiempo real
<code>/positions</code> - Posiciones abiertas
<code>/balance</code> - Balance detallado
<code>/health</code> - Salud del sistema
<code>/agents</code> - Estado de todos los agentes
<code>/agent_status SYMBOL</code> - Estado de agente específico

<b>🎓 ENTRENAMIENTO Y ML</b>
<code>/train_hist</code> - Entrenamiento sobre datos históricos
<code>/train_live</code> - Entrenamiento en tiempo real (paper trading)
<code>/train --symbols BTC,ETH --duration 8h</code> - Entrenar agentes
<code>/stop_training</code> - Detener entrenamiento
<code>/retrain SYMBOL</code> - Reentrenar agente específico
<code>/model_info SYMBOL</code> - Información del modelo
<code>/training_status</code> - Estado del entrenamiento

<b>💹 TRADING Y OPERACIONES</b>
<code>/trade --mode paper --symbols BTC,ETH</code> - Iniciar trading
<code>/trade --mode live --symbols SOL --leverage 20</code> - Trading live
<code>/stop_trading</code> - Detener trading
<code>/emergency_stop</code> - Parada de emergencia
<code>/close_position SYMBOL</code> - Cerrar posición específica

<b>📈 DATOS Y ANÁLISIS</b>
<code>/download_data --symbols BTC,ETH --days 30</code> - Descargar datos
<code>/analyze_data SYMBOL</code> - Analizar datos históricos
<code>/align_data --symbols BTC,ETH</code> - Alinear datos
<code>/data_status</code> - Estado de los datos
<code>/backtest SYMBOL --days 7</code> - Backtest de estrategia

<b>🔧 CONFIGURACIÓN</b>
<code>/set_mode paper|live</code> - Cambiar modo
<code>/set_symbols BTC,ETH,ADA</code> - Cambiar símbolos
<code>/set_leverage SYMBOL 20</code> - Cambiar leverage
<code>/settings</code> - Ver configuración actual

<b>📊 REPORTES Y ANÁLISIS</b>
<code>/performance_report</code> - Reporte de rendimiento
<code>/agent_analysis SYMBOL</code> - Análisis detallado de agente
<code>/risk_report</code> - Reporte de riesgo
<code>/trades_history --days 7</code> - Historial de trades

<b>🛠️ MANTENIMIENTO</b>
<code>/restart_system</code> - Reiniciar sistema
<code>/clear_cache</code> - Limpiar cache
<code>/update_models</code> - Actualizar modelos
<code>/shutdown</code> - Apagar sistema

<b>💡 EJEMPLOS DE USO:</b>
• <code>/train --symbols BTCUSDT,ETHUSDT --duration 8h</code>
• <code>/download_data --symbols BTC,ETH,ADA --days 30</code>
• <code>/analyze_data BTCUSDT</code>
• <code>/agent_status BTCUSDT</code>
• <code>/performance_report</code>

<b>🔒 SEGURIDAD:</b>
• Solo tu Chat ID puede usar comandos
• Comandos críticos requieren confirmación
• Todas las acciones se registran en logs
        """
        
        await update.message.reply_text(help_message, parse_mode='HTML')
        logger.info(f"✅ Comando /help ejecutado por chat_id: {update.message.chat_id}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Estado general del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Sistema no disponible")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('status', {}, str(update.message.chat_id))
            logger.info(f"✅ Comando /status ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo estado: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /status: {e}")
    
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /metrics - Métricas detalladas"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Sistema no disponible")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('metrics', {}, str(update.message.chat_id))
            logger.info(f"✅ Comando /metrics ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo métricas: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /metrics: {e}")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /positions - Posiciones abiertas"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Sistema no disponible")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('positions', {}, str(update.message.chat_id))
            logger.info(f"✅ Comando /positions ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo posiciones: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /positions: {e}")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance - Balance detallado"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.alerting_system:
                await update.message.reply_text("❌ Sistema de monitoreo no disponible.")
                return
            
            # Obtener balance detallado
            balance_info = await self._get_balance_info()
            
            message = f"""
💰 <b>Balance Detallado</b>

💵 <b>Balance Total:</b> ${balance_info.get('total_balance', 0):,.2f}
✅ <b>Disponible:</b> ${balance_info.get('available_balance', 0):,.2f}
🔒 <b>En Uso:</b> ${balance_info.get('used_balance', 0):,.2f}
📊 <b>PnL Total:</b> ${balance_info.get('total_pnl', 0):,.2f}
📈 <b>PnL Hoy:</b> ${balance_info.get('pnl_today', 0):,.2f}
⏰ <b>Actualizado:</b> {datetime.now().strftime('%H:%M:%S')}
            """
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Comando /balance ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo balance: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /balance: {e}")
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /health - Salud del sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.alerting_system:
                await update.message.reply_text("❌ Sistema de monitoreo no disponible.")
                return
            
            # Obtener salud del sistema
            health_info = await self._get_system_health()
            
            # Determinar emoji de salud
            health_score = health_info.get('health_score', 0)
            if health_score >= 90:
                health_emoji = "🟢"
            elif health_score >= 70:
                health_emoji = "🟡"
            else:
                health_emoji = "🔴"
            
            message = f"""
❤️ <b>Salud del Sistema</b>

{health_emoji} <b>Health Score:</b> {health_score:.1f}%
💻 <b>CPU:</b> {health_info.get('cpu_percent', 0):.1f}%
🧠 <b>Memoria:</b> {health_info.get('memory_percent', 0):.1f}%
⚡ <b>Latencia:</b> {health_info.get('latency', 0):.1f}ms
🌐 <b>Conexiones:</b> {health_info.get('connections', 0)}
⏰ <b>Uptime:</b> {health_info.get('uptime', 'N/A')}
            """
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Comando /health ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo salud: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /health: {e}")
    
    async def start_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start_trading - Iniciar trading"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.trading_engine:
                await update.message.reply_text("❌ Motor de trading no disponible.")
                return
            
            # Iniciar trading
            await self.trading_engine.start_trading()
            
            message = "✅ <b>Trading Iniciado</b>\n\nEl motor de trading ha sido iniciado correctamente."
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Comando /start_trading ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando trading: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /start_trading: {e}")
    
    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_trading - Detener trading"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.trading_engine:
                await update.message.reply_text("❌ Motor de trading no disponible.")
                return
            
            # Detener trading
            await self.trading_engine.stop_trading()
            
            message = "🛑 <b>Trading Detenido</b>\n\nEl motor de trading ha sido detenido correctamente."
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Comando /stop_trading ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error deteniendo trading: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /stop_trading: {e}")
    
    async def emergency_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /emergency_stop - Parada de emergencia"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.trading_engine:
                await update.message.reply_text("❌ Motor de trading no disponible.")
                return
            
            # Parada de emergencia
            await self.trading_engine.emergency_stop()
            
            message = """
🚨 <b>PARADA DE EMERGENCIA EJECUTADA</b>

✅ Todas las posiciones han sido cerradas
🛑 El trading ha sido detenido
⚠️ Revisa el estado del sistema antes de reiniciar
            """
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.warning(f"🚨 Comando /emergency_stop ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error en parada de emergencia: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /emergency_stop: {e}")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /settings - Configuración actual"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            config = self.telegram_bot.get_config()
            telegram_config = config.get('telegram', {})
            
            message = f"""
⚙️ <b>Configuración Actual</b>

🤖 <b>Bot:</b> {'✅ Habilitado' if telegram_config.get('enabled', False) else '❌ Deshabilitado'}
📱 <b>Chat ID:</b> {telegram_config.get('chat_id', 'N/A')}
⏰ <b>Intervalo Métricas:</b> {telegram_config.get('metrics_interval', 300)}s

<b>🚨 Alertas:</b>
• PnL: ${telegram_config.get('alert_thresholds', {}).get('pnl_alert', 1000):,.0f}
• Drawdown: {telegram_config.get('alert_thresholds', {}).get('risk_alert', 10):.0f}%
• Latencia: {telegram_config.get('alert_thresholds', {}).get('latency_alert', 100):.0f}ms
            """
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Comando /settings ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo configuración: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /settings: {e}")
    
    async def echo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensajes de texto que no son comandos"""
        if not self._check_authorization(update):
            return
        
        await update.message.reply_text(
            "🤖 No entiendo ese mensaje. Usa /help para ver los comandos disponibles.",
            parse_mode='HTML'
        )
    
    # Métodos auxiliares para obtener datos del sistema
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Obtiene el estado general del sistema"""
        try:
            if hasattr(self.alerting_system, 'get_system_status'):
                return await self.alerting_system.get_system_status()
            else:
                # Fallback con datos simulados
                return {
                    'balance': 10000.0,
                    'positions': 0,
                    'trades_today': 0,
                    'win_rate': 0.0,
                    'health_score': 95.0,
                    'last_update': datetime.now().strftime('%H:%M:%S')
                }
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del sistema: {e}")
            return {}
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas del sistema"""
        try:
            if hasattr(self.alerting_system, 'get_system_metrics'):
                return await self.alerting_system.get_system_metrics()
            else:
                # Fallback con datos simulados
                return {
                    'balance': 10000.0,
                    'pnl_today': 0.0,
                    'win_rate': 0.0,
                    'drawdown': 0.0,
                    'latency': 50.0,
                    'trades_today': 0
                }
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas del sistema: {e}")
            return {}
    
    async def _get_open_positions(self) -> List[Dict[str, Any]]:
        """Obtiene las posiciones abiertas"""
        try:
            if hasattr(self.trading_engine, 'get_open_positions'):
                return await self.trading_engine.get_open_positions()
            else:
                # Fallback con datos simulados
                return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones: {e}")
            return []
    
    async def _get_balance_info(self) -> Dict[str, Any]:
        """Obtiene información detallada del balance"""
        try:
            if hasattr(self.alerting_system, 'get_balance_info'):
                return await self.alerting_system.get_balance_info()
            else:
                # Fallback con datos simulados
                return {
                    'total_balance': 10000.0,
                    'available_balance': 10000.0,
                    'used_balance': 0.0,
                    'total_pnl': 0.0,
                    'pnl_today': 0.0
                }
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance: {e}")
            return {}
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """Obtiene la salud del sistema"""
        try:
            if hasattr(self.alerting_system, 'get_system_health'):
                return await self.alerting_system.get_system_health()
            else:
                # Fallback con datos simulados
                return {
                    'health_score': 95.0,
                    'cpu_percent': 25.0,
                    'memory_percent': 45.0,
                    'latency': 50.0,
                    'connections': 5,
                    'uptime': '2h 30m'
                }
        except Exception as e:
            logger.error(f"❌ Error obteniendo salud del sistema: {e}")
            return {}
    
    # Nuevos comandos de control avanzado
    
    async def train_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /train - Iniciar entrenamiento"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            duration = args.get('duration', '8h')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'train',
                'args': {'symbols': symbols, 'duration': duration},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                f"🎓 Comando de entrenamiento enviado:\nSímbolos: {', '.join(symbols)}\nDuración: {duration}",
                parse_mode='HTML'
            )
            
        except Exception as e:
            error_msg = f"❌ Error en comando train: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /train: {e}")
    
    async def stop_training_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_training - Detener entrenamiento"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'stop_training',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🛑 Comando de detener entrenamiento enviado.")
            
        except Exception as e:
            error_msg = f"❌ Error en comando stop_training: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /stop_training: {e}")
    
    async def trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /trade - Iniciar trading"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            mode = args.get('mode', 'paper')
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'trade',
                'args': {'mode': mode, 'symbols': symbols},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                f"💹 Comando de trading enviado:\nModo: {mode.upper()}\nSímbolos: {', '.join(symbols)}",
                parse_mode='HTML'
            )
            
        except Exception as e:
            error_msg = f"❌ Error en comando trade: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /trade: {e}")
    
    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_trading - Detener trading"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'stop_trading',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🛑 Comando de detener trading enviado.")
            
        except Exception as e:
            error_msg = f"❌ Error en comando stop_trading: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /stop_trading: {e}")
    
    async def set_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /set_mode - Cambiar modo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            mode = args.get('mode', 'paper')
            
            if mode not in ['paper', 'live']:
                await update.message.reply_text("❌ Modo inválido. Usa 'paper' o 'live'.")
                return
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'set_mode',
                'args': {'mode': mode},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"⚙️ Comando de cambiar modo enviado: {mode.upper()}")
            
        except Exception as e:
            error_msg = f"❌ Error en comando set_mode: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /set_mode: {e}")
    
    async def set_symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /set_symbols - Cambiar símbolos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols', [])
            
            if not symbols:
                await update.message.reply_text("❌ No se proporcionaron símbolos.")
                return
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'set_symbols',
                'args': {'symbols': symbols},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"📈 Comando de cambiar símbolos enviado: {', '.join(symbols)}")
            
        except Exception as e:
            error_msg = f"❌ Error en comando set_symbols: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /set_symbols: {e}")
    
    async def shutdown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /shutdown - Apagar sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'shutdown',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🛑 Comando de apagado enviado.")
            
        except Exception as e:
            error_msg = f"❌ Error en comando shutdown: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /shutdown: {e}")
    
    def _parse_command_args(self, args: list) -> Dict[str, Any]:
        """Parsea argumentos de comando estilo argparse"""
        parsed_args = {}
        
        if not args:
            return parsed_args
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('--'):
                # Argumento con valor
                key = arg[2:]  # Remover --
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    value = args[i + 1]
                    # Convertir a lista si contiene comas
                    if ',' in value:
                        parsed_args[key] = [s.strip() for s in value.split(',')]
                    else:
                        parsed_args[key] = value
                    i += 2
                else:
                    # Argumento booleano
                    parsed_args[key] = True
                    i += 1
            else:
                # Argumento posicional
                if 'symbols' not in parsed_args:
                    parsed_args['symbols'] = [arg]
                else:
                    parsed_args['symbols'].append(arg)
                i += 1
        
        return parsed_args
    
    # ===== NUEVOS COMANDOS EXPANDIDOS =====
    
    # Comandos de Agentes y ML
    async def agents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /agents - Estado de todos los agentes"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'agents_status',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🤖 Obteniendo estado de todos los agentes...")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo agentes: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /agents: {e}")
    
    async def agent_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /agent_status - Estado de agente específico"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'agent_status',
                'args': {'symbol': symbol.upper()},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🤖 Analizando agente para {symbol.upper()}...")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo estado del agente: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /agent_status: {e}")
    
    async def retrain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /retrain - Reentrenar agente específico"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            duration = args.get('duration', '4h')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'retrain',
                'args': {'symbol': symbol.upper(), 'duration': duration},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🎓 Iniciando reentrenamiento de {symbol.upper()} por {duration}...")
            
        except Exception as e:
            error_msg = f"❌ Error en reentrenamiento: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /retrain: {e}")
    
    async def model_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /model_info - Información del modelo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'model_info',
                'args': {'symbol': symbol.upper()},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"📊 Obteniendo información del modelo para {symbol.upper()}...")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo información del modelo: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /model_info: {e}")
    
    async def training_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /training_status - Estado del entrenamiento"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('training_status', {}, str(update.message.chat_id))
            logger.info(f"✅ Comando /training_status ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo estado de entrenamiento: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /training_status: {e}")
    
    async def train_hist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /train_hist - Entrenamiento histórico"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            cycle_size = args.get('cycle_size', 500)
            update_every = args.get('update_every', 25)
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('train_hist', {
                'cycle_size': cycle_size,
                'update_every': update_every
            }, str(update.message.chat_id))
            
            logger.info(f"✅ Comando /train_hist ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando entrenamiento histórico: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /train_hist: {e}")
    
    async def train_live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /train_live - Entrenamiento en vivo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            cycle_minutes = args.get('cycle_minutes', 30)
            update_every = args.get('update_every', 5)
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Llamar directamente al controlador
            await self.controller.handle_command('train_live', {
                'cycle_minutes': cycle_minutes,
                'update_every': update_every
            }, str(update.message.chat_id))
            
            logger.info(f"✅ Comando /train_live ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando entrenamiento en vivo: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /train_live: {e}")
    
    # Comandos de Datos y Análisis
    async def download_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /download_data - Descargar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            days = args.get('days', 30)
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'download_data',
                'args': {'symbols': symbols, 'days': days},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"📥 Descargando datos para {', '.join(symbols)} ({days} días)...")
            
        except Exception as e:
            error_msg = f"❌ Error descargando datos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /download_data: {e}")
    
    async def analyze_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /analyze_data - Analizar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'analyze_data',
                'args': {'symbol': symbol.upper()},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"📊 Analizando datos históricos de {symbol.upper()}...")
            
        except Exception as e:
            error_msg = f"❌ Error analizando datos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /analyze_data: {e}")
    
    async def align_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /align_data - Alinear datos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'align_data',
                'args': {'symbols': symbols},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🔄 Alineando datos para {', '.join(symbols)}...")
            
        except Exception as e:
            error_msg = f"❌ Error alineando datos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /align_data: {e}")
    
    async def data_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /data_status - Estado de los datos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'data_status',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("📊 Obteniendo estado de los datos...")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo estado de datos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /data_status: {e}")
    
    async def backtest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /backtest - Backtest de estrategia"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            days = args.get('days', 7)
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'backtest',
                'args': {'symbol': symbol.upper(), 'days': days},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🧪 Ejecutando backtest de {symbol.upper()} ({days} días)...")
            
        except Exception as e:
            error_msg = f"❌ Error ejecutando backtest: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /backtest: {e}")
    
    # Comandos de Trading Avanzado
    async def close_position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /close_position - Cerrar posición específica"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'close_position',
                'args': {'symbol': symbol.upper()},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🔄 Cerrando posición de {symbol.upper()}...")
            
        except Exception as e:
            error_msg = f"❌ Error cerrando posición: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /close_position: {e}")
    
    # Comandos de Reportes
    async def performance_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /performance_report - Reporte de rendimiento"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'performance_report',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("📊 Generando reporte de rendimiento...")
            
        except Exception as e:
            error_msg = f"❌ Error generando reporte: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /performance_report: {e}")
    
    async def agent_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /agent_analysis - Análisis detallado de agente"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'agent_analysis',
                'args': {'symbol': symbol.upper()},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"🔍 Analizando agente de {symbol.upper()}...")
            
        except Exception as e:
            error_msg = f"❌ Error analizando agente: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /agent_analysis: {e}")
    
    async def risk_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /risk_report - Reporte de riesgo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'risk_report',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("⚠️ Generando reporte de riesgo...")
            
        except Exception as e:
            error_msg = f"❌ Error generando reporte de riesgo: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /risk_report: {e}")
    
    async def trades_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /trades_history - Historial de trades"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            days = args.get('days', 7)
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'trades_history',
                'args': {'days': days},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"📈 Obteniendo historial de trades ({days} días)...")
            
        except Exception as e:
            error_msg = f"❌ Error obteniendo historial: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /trades_history: {e}")
    
    # Comandos de Mantenimiento
    async def restart_system_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /restart_system - Reiniciar sistema"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Confirmar reinicio
            confirmation_msg = """
🔄 <b>CONFIRMAR REINICIO DEL SISTEMA</b>

⚠️ <b>ADVERTENCIA:</b> Esto reiniciará todo el sistema.

¿Continuar? Responde <b>YES</b> para confirmar.
            """
            
            await update.message.reply_text(confirmation_msg, parse_mode='HTML')
            
            # Enviar comando de confirmación a la cola
            await self.controller.command_queue.put({
                'type': 'confirm_restart',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
        except Exception as e:
            error_msg = f"❌ Error en reinicio: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /restart_system: {e}")
    
    async def clear_cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /clear_cache - Limpiar cache"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'clear_cache',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🧹 Limpiando cache del sistema...")
            
        except Exception as e:
            error_msg = f"❌ Error limpiando cache: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /clear_cache: {e}")
    
    async def update_models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /update_models - Actualizar modelos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'update_models',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text("🔄 Actualizando modelos...")
            
        except Exception as e:
            error_msg = f"❌ Error actualizando modelos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /update_models: {e}")
    
    # Comando de configuración adicional
    async def set_leverage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /set_leverage - Cambiar leverage"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbol = args.get('symbol', 'BTCUSDT')
            leverage = args.get('leverage', 10)
            
            if not (1 <= leverage <= 30):
                await update.message.reply_text("❌ Leverage debe estar entre 1 y 30.")
                return
            
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando al controlador
            await self.controller.command_queue.put({
                'type': 'set_leverage',
                'args': {'symbol': symbol.upper(), 'leverage': leverage},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(f"⚙️ Cambiando leverage de {symbol.upper()} a {leverage}x...")
            
        except Exception as e:
            error_msg = f"❌ Error cambiando leverage: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /set_leverage: {e}")
    
    async def download_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /download_history - Descargar y auditar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando de descarga de historial al controlador
            await self.controller.command_queue.put({
                'type': 'download_history',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                "📥 **Iniciando descarga de datos históricos...**\n\n"
                "• Verificando datos existentes\n"
                "• Descargando datos faltantes\n"
                "• Auditando duplicados y gaps\n"
                "• Reparando inconsistencias\n\n"
                "Los mensajes se actualizarán en tiempo real."
            )
            
        except Exception as e:
            error_msg = f"❌ Error iniciando descarga de historial: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /download_history: {e}")
    
    async def inspect_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /inspect_history - Inspeccionar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando de inspección de historial al controlador
            await self.controller.command_queue.put({
                'type': 'inspect_history',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                "🔍 **Iniciando inspección de datos históricos...**\n\n"
                "• Analizando cobertura por símbolo/TF\n"
                "• Detectando gaps y duplicados\n"
                "• Calculando integridad de datos\n"
                "• Generando reportes detallados\n\n"
                "Los mensajes se actualizarán en tiempo real."
            )
            
        except Exception as e:
            error_msg = f"❌ Error iniciando inspección de historial: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /inspect_history: {e}")
    
    async def repair_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /repair_history - Reparar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando de reparación de historial al controlador
            await self.controller.command_queue.put({
                'type': 'repair_history',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                "🔧 **Iniciando reparación de datos históricos...**\n\n"
                "• Pipeline completo de limpieza\n"
                "• Eliminación de duplicados\n"
                "• Corrección de orden temporal\n"
                "• Detección y relleno de gaps\n"
                "• Alineación multi-timeframe\n"
                "• Validación de integridad\n\n"
                "Los mensajes se actualizarán en tiempo real."
            )
            
        except Exception as e:
            error_msg = f"❌ Error iniciando reparación de historial: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /repair_history: {e}")
    
    async def stop_train_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_train - Detener entrenamiento de forma elegante"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando de parada elegante al controlador
            await self.controller.command_queue.put({
                'type': 'stop_train',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                "🛑 **Deteniendo entrenamiento de forma elegante...**\n\n"
                "⏳ Guardando progreso actual...\n"
                "🤖 Actualizando modelos de agentes...\n"
                "💾 Creando resumen final...\n\n"
                "✅ El entrenamiento se detendrá de forma segura."
            )
            
        except Exception as e:
            error_msg = f"❌ Error deteniendo entrenamiento: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /stop_train: {e}")
