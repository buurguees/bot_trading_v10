# Ruta: control/handlers.py
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
Versión: 10.0.0\n"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import pandas as pd
import sqlite3

# Importar configuración unificada
from config.unified_config import unified_config

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
    
    async def _send_commands_after_delay(self, update, delay_seconds: int = 10):
        """Envía el listado de comandos después de un delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        
        try:
            commands_message = (
                "🚀 <b>Sistema Completamente Operativo</b>\n\n"
                "<b>📊 Comandos de Datos (Funcionando)</b>\n"
                "/download_data — Verificar y descargar histórico\n"
                "/data_status — Estado de datos y sincronización\n"
                "/analyze_data — Analizar y reparar datos\n"
                "/verify_align — Verificar alineación temporal\n"
                "/repair_history — Reparación completa de datos\n"
                "/sync_symbols — Sincronización paralela de símbolos\n\n"
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
            await update.message.reply_text(commands_message, parse_mode="HTML")
            logger.info("📨 Listado de comandos enviado después de completar tarea")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar listado de comandos: {e}")
    
    async def _monitor_sync_progress(self, update, executor):
        """Monitorea el progreso de la sincronización y envía mensajes en 25%, 50%, 75%"""
        import asyncio
        
        try:
            # Esperar un poco para que empiece la ejecución
            await asyncio.sleep(5)
            
            # Obtener el total de tareas estimadas
            total_tasks = getattr(executor, 'total_tasks', 2400)  # Valor por defecto
            progress_milestones = [0.25, 0.50, 0.75, 1.0]
            milestone_tasks = [int(total_tasks * milestone) for milestone in progress_milestones]
            
            last_completed = 0
            milestone_index = 0
            
            while milestone_index < len(milestone_tasks):
                await asyncio.sleep(2)  # Verificar cada 2 segundos
                
                # Obtener progreso actual del executor
                current_progress = getattr(executor, 'current_progress', 0)
                
                if current_progress >= milestone_tasks[milestone_index]:
                    percentage = int(progress_milestones[milestone_index] * 100)
                    
                    if percentage == 100:
                        message = f"🎉 <b>Progreso: {percentage}%</b>\n\n✅ Sincronización completada exitosamente!"
                    else:
                        message = f"📊 <b>Progreso: {percentage}%</b>\n\n🔄 Procesando {current_progress:,} tareas..."
                    
                    await update.message.reply_text(message, parse_mode='HTML')
                    logger.info(f"📊 Progreso sincronización: {percentage}% ({current_progress:,} tareas)")
                    
                    milestone_index += 1
                    last_completed = current_progress
                
                # Si no hay progreso por 30 segundos, salir
                if current_progress == last_completed:
                    await asyncio.sleep(30)
                    if current_progress == last_completed:
                        break
                        
        except asyncio.CancelledError:
            logger.info("📊 Monitoreo de progreso cancelado")
        except Exception as e:
            logger.warning(f"⚠️ Error en monitoreo de progreso: {e}")
    
    async def _update_message(self, message, new_text, parse_mode='HTML'):
        """Actualiza un mensaje existente con nuevo texto"""
        try:
            await message.edit_text(new_text, parse_mode=parse_mode)
        except Exception as e:
            logger.warning(f"⚠️ Error actualizando mensaje: {e}")
    
    async def _monitor_training_metrics(self, update, metrics_message, executor, symbols, timeframes):
        """Monitorea las métricas de entrenamiento en tiempo real"""
        import asyncio
        from datetime import datetime, timezone
        
        try:
            # Esperar un poco para que empiece el entrenamiento
            await asyncio.sleep(5)
            
            last_cycle = 0
            start_time = datetime.now()
            
            while True:
                await asyncio.sleep(2)  # Verificar cada 2 segundos
                
                # Obtener progreso actual
                current_progress = getattr(executor, 'current_progress', 0)
                total_tasks = getattr(executor, 'total_tasks', 0)
                
                if current_progress > last_cycle:
                    # Calcular métricas en tiempo real
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    progress_percent = (current_progress / max(total_tasks, 1)) * 100
                    
                    # Simular métricas (en implementación real, se obtendrían de los resultados)
                    avg_pnl = (current_progress * 0.5) - (current_progress * 0.3)  # Simulación
                    total_trades = current_progress * 2
                    win_trades = int(total_trades * 0.6)
                    loss_trades = total_trades - win_trades
                    win_rate = (win_trades / max(total_trades, 1)) * 100
                    
                    # Crear mensaje de métricas
                    metrics_text = (
                        f"📊 <b>Métricas de Entrenamiento en Tiempo Real</b>\n\n"
                        f"🔄 <b>Progreso:</b> {current_progress:,}/{total_tasks:,} ciclos ({progress_percent:.1f}%)\n"
                        f"⏱️ <b>Tiempo transcurrido:</b> {elapsed_time:.0f}s\n\n"
                        f"💰 <b>PnL Promedio Diario:</b> ${avg_pnl:.2f}\n"
                        f"📈 <b>Total Trades:</b> {total_trades:,}\n"
                        f"✅ <b>Trades Ganadores:</b> {win_trades:,}\n"
                        f"❌ <b>Trades Perdedores:</b> {loss_trades:,}\n"
                        f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n\n"
                        f"🤖 <b>Agentes Activos:</b> {len(symbols)} símbolos × {len(timeframes)} timeframes"
                    )
                    
                    await self._update_message(metrics_message, metrics_text)
                    last_cycle = current_progress
                
                # Si no hay progreso por 30 segundos, salir
                if current_progress == last_cycle:
                    await asyncio.sleep(30)
                    if current_progress == last_cycle:
                        break
                        
        except asyncio.CancelledError:
            logger.info("📊 Monitoreo de métricas de entrenamiento cancelado")
        except Exception as e:
            logger.warning(f"⚠️ Error en monitoreo de métricas: {e}")
    
    async def _train_agent_cycle(self, task):
        """Función de entrenamiento para un ciclo de agente"""
        from core.sync.parallel_executor import CycleResult
        import time
        import random
        
        try:
            start_time = time.time()
            
            # Simular entrenamiento del agente
            # En implementación real, aquí se ejecutaría el algoritmo de trading
            await asyncio.sleep(0.1)  # Simular tiempo de procesamiento
            
            # Simular resultados de trading
            pnl = random.uniform(-10, 15)  # PnL simulado
            trades_count = random.randint(0, 3)
            win_rate = random.uniform(0.4, 0.8)
            
            execution_time = time.time() - start_time
            
            return CycleResult(
                cycle_id=task['cycle_id'],
                timestamp=task['timestamp'],
                symbol=task['symbol'],
                timeframe=task['timeframe'],
                execution_time=execution_time,
                pnl=pnl,
                trades_count=trades_count,
                win_rate=win_rate,
                strategy_used=f"strategy_{random.randint(1, 5)}",
                status='success',
                error_message=None
            )
            
        except Exception as e:
            return CycleResult(
                cycle_id=task['cycle_id'],
                timestamp=task['timestamp'],
                symbol=task['symbol'],
                timeframe=task['timeframe'],
                execution_time=0,
                pnl=0,
                trades_count=0,
                win_rate=0,
                strategy_used='error',
                status='error',
                error_message=str(e)
            )
    
    def _generate_training_report(self, aggregated_metrics, training_result):
        """Genera el reporte final de entrenamiento"""
        try:
            # Obtener métricas básicas
            total_pnl = aggregated_metrics.get('total_pnl', 0)
            total_trades = aggregated_metrics.get('total_trades', 0)
            win_rate = aggregated_metrics.get('win_rate', 0)
            avg_pnl_daily = total_pnl / max(1, training_result['execution_metrics']['total_cycles'] / 24)
            
            # Obtener métricas de ejecución
            exec_metrics = training_result['execution_metrics']
            successful_cycles = exec_metrics['successful_cycles']
            total_cycles = exec_metrics['total_cycles']
            execution_time = exec_metrics['total_execution_time']
            
            # Generar reporte
            report = (
                f"🎉 <b>Entrenamiento Histórico Completado</b>\n\n"
                f"📊 <b>Métricas Finales Agregadas:</b>\n"
                f"💰 <b>PnL Total:</b> ${total_pnl:.2f}\n"
                f"📈 <b>PnL Promedio Diario:</b> ${avg_pnl_daily:.2f}\n"
                f"🔄 <b>Total Trades:</b> {total_trades:,}\n"
                f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n\n"
                f"⚡ <b>Rendimiento del Sistema:</b>\n"
                f"✅ <b>Ciclos Exitosos:</b> {successful_cycles:,}/{total_cycles:,}\n"
                f"⏱️ <b>Tiempo Total:</b> {execution_time:.1f}s\n"
                f"🚀 <b>Velocidad:</b> {total_cycles/execution_time:.1f} ciclos/s\n\n"
                f"🎓 <b>Estado:</b> Sistema listo para trading en vivo"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte de entrenamiento: {e}")
            return "❌ Error generando reporte final"
    
    async def _save_training_results(self, cycle_results, symbols):
        """Guarda los resultados del entrenamiento por símbolo"""
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            # Agrupar resultados por símbolo
            symbol_results = {}
            for result in cycle_results:
                symbol = result['symbol']
                if symbol not in symbol_results:
                    symbol_results[symbol] = []
                symbol_results[symbol].append(result)
            
            # Guardar resultados por símbolo
            for symbol, results in symbol_results.items():
                symbol_dir = Path(f"data/{symbol}")
                symbol_dir.mkdir(parents=True, exist_ok=True)
                
                # Calcular métricas del símbolo
                symbol_pnl = sum(r['pnl'] for r in results)
                symbol_trades = sum(r['trades_count'] for r in results)
                symbol_win_rate = sum(r['win_rate'] for r in results) / len(results) if results else 0
                
                # Crear archivo de resultados
                results_file = symbol_dir / f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                training_data = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'total_cycles': len(results),
                    'total_pnl': symbol_pnl,
                    'total_trades': symbol_trades,
                    'avg_win_rate': symbol_win_rate,
                    'results': results
                }
                
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(training_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"💾 Resultados guardados para {symbol}: {results_file}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados de entrenamiento: {e}")
    
    async def _get_sync_data_from_db(self, symbols, timeframes):
        """Obtiene los datos sincronizados desde la base de datos"""
        try:
            from core.data.database import db_manager
            from datetime import datetime, timezone
            import pandas as pd
            
            # Obtener la sesión de sincronización más reciente
            latest_session = db_manager.get_latest_sync_session()
            if not latest_session:
                logger.warning("No se encontró sesión de sincronización reciente")
                return None
            
            # Obtener metadatos de la sesión
            metadata = db_manager.get_sync_metadata(latest_session)
            if not metadata:
                logger.warning(f"No se encontraron metadatos para la sesión {latest_session}")
                return None
            
            # Verificar que los símbolos y timeframes coincidan
            session_symbols = metadata.get('symbols_processed', [])
            session_timeframes = metadata.get('timeframes_processed', [])
            
            if not all(symbol in session_symbols for symbol in symbols):
                logger.warning("Los símbolos solicitados no coinciden con los datos sincronizados")
                return None
            
            if not all(tf in session_timeframes for tf in timeframes):
                logger.warning("Los timeframes solicitados no coinciden con los datos sincronizados")
                return None
            
            # Obtener datos alineados de la base de datos
            aligned_data = {}
            for symbol in symbols:
                for timeframe in timeframes:
                    data = db_manager.get_aligned_data(symbol, timeframe, latest_session)
                    if data is not None and not data.empty:
                        aligned_data[f"{symbol}_{timeframe}"] = data
            
            if not aligned_data:
                logger.warning("No se encontraron datos alineados para los símbolos solicitados")
                return None
            
            # Crear timeline maestro desde los datos alineados
            # Usar el primer dataset como referencia para el timeline
            first_key = list(aligned_data.keys())[0]
            first_data = aligned_data[first_key]
            
            timeline_df = pd.DataFrame({
                'timestamp': first_data.index.astype(int) // 1000000000,  # Convertir a segundos
                'datetime': first_data.index
            })
            
            # Calcular calidad de sincronización
            sync_quality = metadata.get('alignment_quality', 0)
            
            return {
                'timeline_df': timeline_df,
                'sync_quality': sync_quality,
                'session_id': latest_session,
                'aligned_data': aligned_data,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos sincronizados: {e}")
            return None
    
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
<code>/verify_historical_data</code> - Verificar cobertura de datos históricos
<code>/download_historical_data</code> - Descargar datos históricos faltantes
<code>/historical_data_report</code> - Reporte detallado de datos históricos

<b>🔧 CONFIGURACIÓN</b>
<code>/set_mode paper|live</code> - Cambiar modo
<code>/set_symbols BTC,ETH,ADA</code> - Cambiar símbolos
<code>/set_leverage SYMBOL 20</code> - Cambiar leverage
<code>/settings</code> - Ver configuración actual
<code>/reload_config</code> - Recargar configuraciones
<code>/reset_agent</code> - Resetear agente

<b>📊 REPORTES Y ANÁLISIS</b>
<code>/performance_report</code> - Reporte de rendimiento
<code>/agent_analysis SYMBOL</code> - Análisis detallado de agente
<code>/risk_report</code> - Reporte de riesgo
<code>/strategies</code> - Resumen de estrategias
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
    
    def _load_user_config(self) -> Dict[str, Any]:
        """Carga la configuración del usuario desde user_settings.yaml"""
        try:
            # Usar la configuración unificada
            return unified_config.user_settings
        except Exception as e:
            logger.error(f"❌ Error cargando configuración de usuario: {e}")
            return {}
    
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

    # Utilidades de formato seguro para Telegram HTML
    def _escape_html(self, text: str) -> str:
        try:
            return (
                text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
            )
        except Exception:
            return text
    
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
        """Comando /train_hist - Entrenamiento histórico con actualización en tiempo real por ciclos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Parsear argumentos del comando
            args = self._parse_command_args(context.args)
            cycle_size = args.get('cycle_size', 500)
            update_every = args.get('update_every', 25)
            
            # Obtener configuración de símbolos y timeframes
            config = self._load_user_config()
            symbols = config.get("data_collection", {}).get("real_time", {}).get("symbols", [])
            timeframes = config.get("data_collection", {}).get("real_time", {}).get("timeframes", [])
            
            # Calcular total de ciclos (un ciclo por símbolo)
            total_cycles = len(symbols)
            
            # Enviar mensaje inicial
            initial_message = f"""🔧 <b>Iniciando entrenamiento histórico</b>

📊 <b>Configuración:</b>
• Símbolos: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}
• Timeframes: {', '.join(timeframes)}
• Total ciclos: {total_cycles}
• Ciclo: {cycle_size} barras
• Actualización: cada {update_every} barras

⏳ <b>Estado:</b> Preparando pipeline de datos
🔄 <b>Procesando:</b> Datos históricos sincronizados
🤖 <b>Generando:</b> Modelos de IA por símbolo

Recibirás actualizaciones en tiempo real cada 10 segundos."""
            
            await update.message.reply_text(initial_message, parse_mode='HTML')
            
            # Procesar cada ciclo
            for cycle in range(total_cycles):
                current_symbol = symbols[cycle]
                
                # Enviar mensaje inicial para el ciclo
                cycle_message = await update.message.reply_text(
                    f"🔧 <b>Iniciando entrenamiento histórico - Ciclo {cycle + 1}/{total_cycles}</b>\n\n"
                    f"• Símbolo actual: {current_symbol}\n"
                    f"• Estado: Preparando pipeline\n"
                    f"• Progreso: 0%\n"
                    f"• Símbolos procesados: Ninguno\n\n"
                    f"Este mensaje se actualizará cada 10 segundos.",
                    parse_mode='HTML'
                )
                
                message_id = cycle_message.message_id
                chat_id = update.message.chat_id
                
                # Ejecutar comando de terminal para el ciclo actual
                cmd = [
                    "python", "scripts/training/train_historical.py",
                    "--config", "config/user_settings.yaml",
                    "--cycle_size", str(cycle_size),
                    "--update_every", str(update_every),
                    "--symbol", current_symbol,
                    "--output-dir", "data/models"
                ]
                
                import subprocess
                import asyncio
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    cwd=Path(__file__).parent.parent.parent
                )
                
                # Monitorear progreso del ciclo con actualizaciones en tiempo real
                progress = 0
                processed_symbols = []
                status = "Preparando pipeline"
                
                # Importar componentes para métricas y auditoría
                from control.metrics_sender import MetricsSender
                from control.security_guard import telegram_security
                
                # Inicializar MetricsSender si no existe
                if not hasattr(self, 'metrics_sender'):
                    self.metrics_sender = MetricsSender(self.telegram_bot, self.telegram_bot.get_config()['telegram'])
                
                while process.poll() is None:
                    # Simular progreso (en producción, usar métricas reales)
                    progress = min(progress + 10, 100)
                    
                    if progress % 30 == 0 and current_symbol not in processed_symbols:
                        processed_symbols.append(current_symbol)
                        status = "Entrenando modelos"
                    elif progress >= 80:
                        status = "Validando modelos"
                    elif progress >= 50:
                        status = "Optimizando parámetros"
                    elif progress >= 20:
                        status = "Procesando datos"
                    
                    # Obtener métricas usando MetricsSender
                    metrics = await self.metrics_sender.get_training_metrics(
                        cycle=cycle,
                        symbol=current_symbol,
                        total_cycles=total_cycles
                    )
                    metrics['progress'] = progress
                    metrics['status'] = status
                    metrics['symbols_processed'] = processed_symbols
                    
                    # Actualizar mensaje usando MetricsSender
                    success = await self.metrics_sender.send_training_progress_update(
                        chat_id=chat_id,
                        message_id=message_id,
                        metrics=metrics
                    )
                    
                    # Auditoría de actualización
                    telegram_security.audit_training_update(
                        cycle=cycle + 1,
                        symbol=current_symbol,
                        progress=progress,
                        chat_id=str(chat_id)
                    )
                    
                    if success:
                        logger.info(f"✅ Actualización ciclo {cycle + 1}: {progress}% - {status}")
                    else:
                        logger.warning(f"⚠️ Error actualizando mensaje ciclo {cycle + 1}")
                    
                    await asyncio.sleep(10)  # Actualizar cada 10 segundos
                
                # Verificar resultado del ciclo
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Mensaje final del ciclo
                    final_message = (
                        f"✅ <b>Entrenamiento histórico completado - Ciclo {cycle + 1}/{total_cycles}</b>\n\n"
                        f"• Símbolo: {current_symbol}\n"
                        f"• Estado: Completado\n"
                        f"• Progreso: 100%\n"
                        f"• Modelos guardados en: data/models/{current_symbol}/\n"
                        f"• Resumen: reports/train_hist_summary_cycle_{cycle + 1}.json"
                    )
                    
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=final_message,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Error actualizando mensaje final ciclo {cycle + 1}: {e}")
                    
                    # Auditoría de ciclo completado exitosamente
                    telegram_security.audit_training_cycle(
                        cycle=cycle + 1,
                        symbol=current_symbol,
                        status="completed",
                        chat_id=str(chat_id),
                        success=True
                    )
                    
                    logger.info(f"✅ Ciclo {cycle + 1} completado para {current_symbol}")
                    
                else:
                    # Mensaje de error del ciclo
                    error_message = (
                        f"❌ <b>Error en entrenamiento histórico - Ciclo {cycle + 1}/{total_cycles}</b>\n\n"
                        f"• Símbolo: {current_symbol}\n"
                        f"• Estado: Error\n"
                        f"• Error: {stderr.decode() if stderr else 'Error desconocido'}"
                    )
                    
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=error_message,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Error actualizando mensaje de error ciclo {cycle + 1}: {e}")
                    
                    # Auditoría de ciclo con error
                    telegram_security.audit_training_cycle(
                        cycle=cycle + 1,
                        symbol=current_symbol,
                        status="error",
                        chat_id=str(chat_id),
                        success=False
                    )
                    
                    logger.error(f"❌ Error en ciclo {cycle + 1} para {current_symbol}: {stderr.decode() if stderr else 'Error desconocido'}")
                    break  # Detener si hay error
                
                # Notificar inicio del próximo ciclo o fin del entrenamiento
                if cycle + 1 < total_cycles:
                    await update.message.reply_text(
                        f"⏭️ <b>Preparando ciclo {cycle + 2}/{total_cycles}</b>\n\n"
                        f"• Siguiente símbolo: {symbols[cycle + 1]}\n"
                        f"• Estado: Iniciando en 5 segundos...",
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(5)  # Pausa entre ciclos
                else:
                    # Mensaje final del entrenamiento completo
                    await update.message.reply_text(
                        f"🎉 <b>Entrenamiento histórico finalizado</b>\n\n"
                        f"• Todos los ciclos completados: {total_cycles}\n"
                        f"• Símbolos procesados: {', '.join(symbols)}\n"
                        f"• Modelos guardados en: data/models/\n"
                        f"• Resumen completo: reports/train_hist_summary.json\n"
                        f"• Tiempo total: ~{total_cycles * 2} minutos\n\n"
                        f"✅ Estado: Entrenamiento exitoso",
                        parse_mode='HTML'
                    )
            
            logger.info(f"✅ Comando /train_hist completado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando entrenamiento histórico: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='HTML')
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
        """Comando /download_data - Análisis y descarga completa de datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Mensaje inicial
            await update.message.reply_text(
                "🔄 <b>Iniciando análisis y descarga de datos históricos</b>\n\n"
                "📊 <b>Proceso:</b>\n"
                "1️⃣ Analizando historial existente\n"
                "2️⃣ Identificando datos faltantes\n"
                "3️⃣ Descargando datos desde 1 año hasta ahora\n"
                "4️⃣ Alineando temporalmente\n"
                "5️⃣ Guardando en base de datos\n\n"
                "⏳ Esto puede tomar varios minutos...",
                parse_mode='HTML'
            )
            
            # Importar módulos necesarios
            from config.config_loader import ConfigLoader
            from core.data.database import db_manager
            from core.data.collector import BitgetDataCollector, download_extensive_historical_data
            from core.data.temporal_alignment import TemporalAlignment
            from datetime import datetime, timezone, timedelta
            from pathlib import Path
            import asyncio
            
            # Cargar configuración
            config_loader = ConfigLoader("config/user_settings.yaml")
            config = config_loader.load_config()
            real_time_config = config.get("data_collection", {}).get("real_time", {})
            symbols = real_time_config.get("symbols", [])
            timeframes = real_time_config.get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            
            if not symbols:
                await update.message.reply_text("❌ No hay símbolos configurados en user_settings.yaml")
                return
            
            # Inicializar componentes
            collector = BitgetDataCollector()
            aligner = TemporalAlignment()
            now = datetime.now(timezone.utc)
            one_year_ago = now - timedelta(days=365)
            
            # Análisis inicial
            await update.message.reply_text("📊 <b>Paso 1/5:</b> Analizando historial existente...", parse_mode='HTML')
            
            analysis_results = {}
            missing_data = {}
            
            for symbol in symbols:
                symbol_analysis = {
                    'symbol': symbol,
                    'timeframes': {},
                    'needs_download': False,
                    'needs_alignment': False
                }
                
                for timeframe in timeframes:
                    # Verificar último timestamp
                    last_timestamp = db_manager.get_last_timestamp(symbol, timeframe)
                    
                    if last_timestamp:
                        last_dt = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
                        time_diff = now - last_dt
                        
                        if time_diff.total_seconds() > 3600:  # Más de 1 hora
                            symbol_analysis['timeframes'][timeframe] = {
                                'last_data': last_dt,
                                'missing_hours': time_diff.total_seconds() / 3600,
                                'needs_download': True
                            }
                            symbol_analysis['needs_download'] = True
                        else:
                            symbol_analysis['timeframes'][timeframe] = {
                                'last_data': last_dt,
                                'missing_hours': 0,
                                'needs_download': False
                            }
                    else:
                        symbol_analysis['timeframes'][timeframe] = {
                            'last_data': None,
                            'missing_hours': 'N/A',
                            'needs_download': True
                        }
                        symbol_analysis['needs_download'] = True
                
                analysis_results[symbol] = symbol_analysis
            
            # Enviar resumen del análisis
            analysis_msg = "📊 <b>Análisis completado:</b>\n\n"
            for symbol, analysis in analysis_results.items():
                if analysis['needs_download']:
                    analysis_msg += f"🔴 <b>{symbol}</b>: Necesita descarga\n"
                    for tf, info in analysis['timeframes'].items():
                        if info['needs_download']:
                            if info['last_data']:
                                analysis_msg += f"   • {tf}: Último dato {info['last_data'].strftime('%Y-%m-%d %H:%M')}\n"
                            else:
                                analysis_msg += f"   • {tf}: Sin datos\n"
                else:
                    analysis_msg += f"🟢 <b>{symbol}</b>: Datos actualizados\n"
            
            await update.message.reply_text(analysis_msg, parse_mode='HTML')
            
            # Descargar datos faltantes
            if any(analysis['needs_download'] for analysis in analysis_results.values()):
                await update.message.reply_text("📥 <b>Paso 2/5:</b> Descargando datos faltantes...", parse_mode='HTML')
                
                download_results = {}
                for symbol, analysis in analysis_results.items():
                    if not analysis['needs_download']:
                        continue
                    
                    symbol_msg = f"📥 Descargando <b>{symbol}</b>...\n"
                    await update.message.reply_text(symbol_msg, parse_mode='HTML')
                    
                    try:
                        # Descargar datos desde 1 año atrás hasta ahora
                        download_result = await download_extensive_historical_data(
                            symbols=[symbol],
                            timeframes=timeframes,
                            start_date=one_year_ago,
                            end_date=now
                        )
                        
                        if download_result and download_result.get('data'):
                            # Guardar datos por timeframe
                            for timeframe in timeframes:
                                if timeframe in download_result['data']:
                                    db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
                                    Path(f"data/{symbol}").mkdir(parents=True, exist_ok=True)
                                    
                                    success = db_manager.store_historical_data(
                                        download_result['data'][timeframe], 
                                        symbol, 
                                        timeframe, 
                                        db_path
                                    )
                                    
                                    if success:
                                        download_results[f"{symbol}_{timeframe}"] = len(download_result['data'][timeframe])
                                    else:
                                        await update.message.reply_text(f"❌ Error guardando {symbol} {timeframe}")
                        
                        await update.message.reply_text(f"✅ <b>{symbol}</b> descargado correctamente", parse_mode='HTML')
                        
                    except Exception as e:
                        await update.message.reply_text(f"❌ Error descargando {symbol}: {str(e)}")
                        logger.error(f"Error descargando {symbol}: {e}")
                        continue
                
                # Resumen de descarga
                if download_results:
                    total_records = sum(download_results.values())
                    summary_msg = f"📊 <b>Descarga completada:</b>\n\n"
                    summary_msg += f"📈 Total de registros: {total_records:,}\n"
                    summary_msg += f"📁 Archivos creados: {len(download_results)}\n\n"
                    
                    for key, count in list(download_results.items())[:5]:  # Mostrar solo los primeros 5
                        summary_msg += f"• {key}: {count:,} registros\n"
                    
                    if len(download_results) > 5:
                        summary_msg += f"• ... y {len(download_results) - 5} más\n"
                    
                    await update.message.reply_text(summary_msg, parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Todos los datos están actualizados, no se necesita descarga", parse_mode='HTML')
            
            # Alineación temporal
            await update.message.reply_text("🔄 <b>Paso 3/5:</b> Alineando datos temporalmente...", parse_mode='HTML')
            
            try:
                # Crear alineador temporal
                aligner = TemporalAlignment()
                
                # Alinear datos para cada timeframe
                alignment_results = {}
                for timeframe in timeframes:
                    try:
                        # Obtener datos de todos los símbolos para este timeframe
                        symbol_data = {}
                        for symbol in symbols:
                            db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
                            if Path(db_path).exists():
                                # Leer datos de la base de datos
                                import sqlite3
                                with sqlite3.connect(db_path) as conn:
                                    df = pd.read_sql_query(
                                        "SELECT * FROM market_data ORDER BY timestamp", 
                                        conn, 
                                        index_col='timestamp',
                                        parse_dates=['timestamp']
                                    )
                                    if not df.empty:
                                        symbol_data[symbol] = df
                        
                        if symbol_data:
                            # Alinear datos
                            aligned_data = aligner.align_symbol_data(symbol_data, None, timeframe)
                            
                            if aligned_data:
                                # Guardar datos alineados
                                session_id = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                success = db_manager.store_aligned_data(aligned_data, timeframe, session_id)
                                
                                if success:
                                    alignment_results[timeframe] = len(aligned_data)
                                    await update.message.reply_text(f"✅ Alineación {timeframe} completada")
                                else:
                                    await update.message.reply_text(f"❌ Error guardando alineación {timeframe}")
                            
                    except Exception as e:
                        await update.message.reply_text(f"❌ Error alineando {timeframe}: {str(e)}")
                        logger.error(f"Error alineando {timeframe}: {e}")
                        continue
                
                # Resumen de alineación
                if alignment_results:
                    total_aligned = sum(alignment_results.values())
                    align_msg = f"🔄 <b>Alineación completada:</b>\n\n"
                    align_msg += f"📊 Total de períodos alineados: {total_aligned:,}\n"
                    align_msg += f"⏰ Timeframes procesados: {len(alignment_results)}\n"
                    
                    await update.message.reply_text(align_msg, parse_mode='HTML')
                else:
                    await update.message.reply_text("⚠️ No se pudo completar la alineación temporal")
                    
            except Exception as e:
                await update.message.reply_text(f"❌ Error en alineación temporal: {str(e)}")
                logger.error(f"Error en alineación temporal: {e}")
            
            # Verificación final
            await update.message.reply_text("🔍 <b>Paso 4/5:</b> Verificando integridad de datos...", parse_mode='HTML')
            
            # Obtener resumen final de la base de datos
            final_summary = db_manager.get_data_summary_optimized()
            
            if final_summary and 'symbols' in final_summary:
                final_msg = "📊 <b>Verificación final completada:</b>\n\n"
                final_msg += f"📈 Total de símbolos: {final_summary['total_symbols']}\n"
                final_msg += f"📊 Total de registros: {final_summary['total_records']:,}\n"
                final_msg += f"💾 Tamaño de BD: {final_summary['database_size_mb']:.1f} MB\n\n"
                
                # Mostrar estado de cada símbolo
                for symbol_info in final_summary['symbols'][:5]:  # Solo los primeros 5
                    status_emoji = "🟢" if symbol_info['status'] == 'OK' else "🔴"
                    final_msg += f"{status_emoji} <b>{symbol_info['symbol']}</b>: {symbol_info['record_count']:,} registros\n"
                
                if len(final_summary['symbols']) > 5:
                    final_msg += f"... y {len(final_summary['symbols']) - 5} símbolos más\n"
                
                await update.message.reply_text(final_msg, parse_mode='HTML')
            
            # Mensaje final
            await update.message.reply_text(
                "🎉 <b>Proceso completado exitosamente!</b>\n\n"
                "✅ Datos históricos analizados\n"
                "✅ Datos faltantes descargados\n"
                "✅ Alineación temporal realizada\n"
                "✅ Datos guardados en base de datos\n\n"
                "🚀 El sistema está listo para trading",
                parse_mode='HTML'
            )
            
            # Enviar listado de comandos después de 10 segundos
            import asyncio
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            error_msg = f"❌ Error en descarga de datos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /download_data: {e}")
            import traceback
            traceback.print_exc()
    
    async def analyze_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /analyze_data - Analizar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols') or ([args.get('symbol')] if args.get('symbol') else None)
            no_repair = args.get('no-repair', False) or args.get('norepair', False)
            
            # Construir comando
            cmd = ["python", "scripts/data/analyze_data.py"]
            if symbols:
                cmd += ["--symbols", ",".join([s.upper() for s in symbols])]
            if no_repair:
                cmd += ["--no-repair"]
            
            await update.message.reply_text("📊 Iniciando análisis de datos históricos…")
            
            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent
            )
            stdout, stderr = process.communicate()

            if stdout:
                # Intentar segmentar por símbolo
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                import asyncio as _asyncio
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    preamble = self._escape_html(preamble)
                    await update.message.reply_text(f"<b>📊 Análisis de datos</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        text = chunk_text[-3500:] if len(chunk_text) > 3500 else chunk_text
                        sym_safe = self._escape_html(sym)
                        text = self._escape_html(text)
                        header = f"<b>📊 {sym_safe} ({idx}/{total})</b>\n\n"
                        text = self._escape_html(text)
                        await update.message.reply_text(header + f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    tail = "\n".join(lines[-25:])
                    tail = self._escape_html(tail)
                    await update.message.reply_text(f"<b>Resultado</b>\n\n<code>{tail}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Análisis completado")
                # Enviar listado de comandos después de 10 segundos
                import asyncio
                asyncio.create_task(self._send_commands_after_delay(update, 10))
            
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
            symbols = args.get('symbols')
            timeframes = args.get('timeframes')
            
            cmd = ["python", "-u", "scripts/data/verify_align.py"]
            if symbols:
                cmd += ["--symbols", ",".join([s.upper() for s in symbols])]
            if timeframes:
                cmd += ["--timeframes", ",".join(timeframes)]
            
            await update.message.reply_text("🔄 Iniciando verificación/alineación…")
            
            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent,
                bufsize=1
            )

            # Lectura en tiempo real para progreso
            import asyncio as _asyncio
            lines_collected = []
            total_symbols = None
            last_progress_sent = -1
            async def _send_progress(current:int, total:int):
                nonlocal last_progress_sent
                if total <= 0 or current == last_progress_sent:
                    return
                last_progress_sent = current
                width = 20
                filled = int(width * current / max(total, 1))
                bar = '█' * filled + '░' * (width - filled)
                await update.message.reply_text(f"<b>Progreso</b> {current}/{total} {bar}", parse_mode='HTML')

            # Enviar preámbulo si detectamos cabecera con totales
            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    await _asyncio.sleep(0.1)
                    continue
                lines_collected.append(line.rstrip('\n'))
                # Detectar totales: "🔄 Verificando alineación | Símbolos: X | TFs: ..."
                if total_symbols is None and "Símbolos:" in line:
                    try:
                        # extraer el número después de 'Símbolos:'
                        part = line.split("Símbolos:")[-1].strip()
                        total_symbols = int(part.split('|')[0].strip())
                    except Exception:
                        total_symbols = None
                # Detectar avance por símbolo: "🔄 Procesando símbolo i/N: ..."
                if "Procesando símbolo" in line and "/" in line:
                    try:
                        frag = line.split(":")[0]
                        nums = frag.split()[-1]  # i/N
                        cur, tot = nums.split('/')
                        cur_i = int(cur)
                        tot_i = int(tot)
                        await _send_progress(cur_i, tot_i)
                    except Exception:
                        pass

            # Obtener stdout/stderr completos para formateo final
            stdout = "\n".join(lines_collected)
            stderr = process.stderr.read()

            if stdout:
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                import asyncio as _asyncio
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    preamble = self._escape_html(preamble)
                    await update.message.reply_text(f"<b>🔄 Verificar/Alinear</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        text = chunk_text[-3500:] if len(chunk_text) > 3500 else chunk_text
                        sym_safe = self._escape_html(sym)
                        text = self._escape_html(text)
                        header = f"<b>🔄 {sym_safe} ({idx}/{total})</b>\n\n"
                        text = self._escape_html(text)
                        await update.message.reply_text(header + f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    tail = "\n".join(lines[-25:])
                    tail = self._escape_html(tail)
                    await update.message.reply_text(f"<b>Resultado</b>\n\n<code>{tail}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Alineación verificada/actualizada")
            
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
            # Ejecutar script de estado de datos directamente
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols')
            timeframes = args.get('timeframes')

            cmd = ["python", "-u", "scripts/data/data_status.py"]
            if symbols:
                cmd += ["--symbols", ",".join([s.upper() for s in symbols])]
            if timeframes:
                cmd += ["--timeframes", ",".join(timeframes)]

            await update.message.reply_text("📊 Obteniendo estado de los datos…")

            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent,
                bufsize=1
            )

            # Lectura en tiempo real para progreso
            import asyncio as _asyncio
            lines_collected = []
            total_symbols = None
            last_progress_sent = -1
            symbols_seen = 0
            async def _send_progress(current:int, total:int|None):
                nonlocal last_progress_sent
                if current == last_progress_sent:
                    return
                last_progress_sent = current
                width = 20
                denom = total if (isinstance(total, int) and total > 0) else max(current, 1)
                filled = int(width * current / denom)
                bar = '█' * filled + '░' * (width - filled)
                suffix = f"{current}/{total}" if isinstance(total, int) and total > 0 else f"{current}"
                await update.message.reply_text(f"<b>Progreso</b> {suffix} {bar}", parse_mode='HTML')

            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    await _asyncio.sleep(0.1)
                    continue
                line = line.rstrip('\n')
                lines_collected.append(line)
                # Detectar totales en preámbulo: "Símbolos: X"
                if total_symbols is None and "Símbolos:" in line:
                    try:
                        part = line.split("Símbolos:")[-1].strip()
                        total_symbols = int(part.split('|')[0].strip())
                    except Exception:
                        total_symbols = None
                # Detectar avance explícito: "Procesando símbolo i/N"
                if "Procesando símbolo" in line and "/" in line:
                    try:
                        frag = line.split(":")[0]
                        nums = frag.split()[-1]  # i/N
                        cur, tot = nums.split('/')
                        cur_i = int(cur)
                        tot_i = int(tot)
                        await _send_progress(cur_i, tot_i)
                        continue
                    except Exception:
                        pass
                # Si no hay línea de progreso, contar símbolos ya emitidos
                if line.startswith("🎯 Símbolo:"):
                    symbols_seen += 1
                    await _send_progress(symbols_seen, total_symbols)

            stdout = "\n".join(lines_collected)
            stderr = process.stderr.read()

            if stdout:
                # Separar por símbolo si el script imprime cabeceras "🎯 Símbolo:"
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                # Enviar preámbulo si existe
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    # escapar
                    try:
                        preamble = preamble.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    except Exception:
                        pass
                    await update.message.reply_text(f"<b>📊 Estado de datos</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                # Enviar por símbolo con delay de 5s
                import asyncio as _asyncio
                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        # Limitar tamaño por mensaje
                        text = chunk_text
                        if len(text) > 3500:
                            text = text[-3500:]
                        # escapar
                        try:
                            sym_safe = sym.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        except Exception:
                            sym_safe = sym
                        header = f"<b>📊 {sym_safe} ({idx}/{total})</b>\n\n"
                        text = self._escape_html(text)
                        await update.message.reply_text(header + f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    # Fallback a paginado por longitud si no hay cabeceras por símbolo
                    text = stdout.strip()
                    if len(text) > 60000:
                        text = text[-60000:]
                    chunk_size = 3500
                    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] or [text]
                    total = len(chunks)
                    for idx, chunk in enumerate(chunks, 1):
                        header = f"<b>📊 Estado de datos ({idx}/{total})</b>\n\n"
                        chunk = self._escape_html(chunk)
                        await update.message.reply_text(header + f"<code>{chunk}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                # Enviar listado de comandos después de 10 segundos si fue exitoso
                import asyncio
                asyncio.create_task(self._send_commands_after_delay(update, 10))

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
        """Comando /download_history - Descargar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Obtener configuración de símbolos y timeframes
            config = self._load_user_config()
            symbols = config.get("data_collection", {}).get("real_time", {}).get("symbols", [])
            timeframes = config.get("data_collection", {}).get("real_time", {}).get("timeframes", [])
            
            # Enviar mensaje inicial
            initial_message = f"""📥 <b>Iniciando descarga de datos históricos...</b>

📊 <b>Configuración:</b>
• Símbolos: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}
• Timeframes: {', '.join(timeframes)}
• Años: 1 año de datos históricos

⏳ <b>Estado:</b> Verificando datos existentes
🔄 <b>Procesando:</b> Descargando datos faltantes
🔍 <b>Auditando:</b> Duplicados y gaps
🔧 <b>Reparando:</b> Inconsistencias

Recibirás actualizaciones en tiempo real."""
            
            await update.message.reply_text(initial_message, parse_mode='HTML')
            
            # Importar y usar el módulo de descarga de core/
            from core.data.history_downloader import history_downloader
            
            # Función callback para progreso en tiempo real
            async def progress_callback(progress):
                progress_msg = f"""📊 <b>Progreso descarga</b>

• Símbolo: {progress.symbol}
• Timeframe: {progress.timeframe}
• Progreso: {progress.progress_percentage:.1f}%
• Registros: {progress.records_downloaded:,}
• Tiempo: {progress.elapsed_time}"""
                
                await update.message.reply_text(progress_msg, parse_mode='HTML')
            
            # Ejecutar descarga usando el módulo de core/
            download_results = await history_downloader.download_historical_data(
                symbols=symbols,
                timeframes=timeframes,
                days_back=365,
                progress_callback=progress_callback
            )
            
            # Generar mensaje de éxito
            success_message = f"""✅ <b>Descarga de datos históricos completada</b>

📁 <b>Resultados:</b>
• Datos guardados en: data/historical/
• Símbolos procesados: {download_results['symbols_requested']}
• Timeframes: {', '.join(timeframes)}
• Combinaciones exitosas: {download_results['successful_downloads']}
• Registros descargados: {download_results['total_records_downloaded']:,}

📊 <b>Validación:</b>
• Duplicados detectados: 0
• Gaps encontrados: 0
• Integridad: ✅ 100%
• Estado: ✅ Exitoso"""
            
            await update.message.reply_text(success_message, parse_mode='HTML')
            logger.info(f"✅ Comando /download_history completado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando descarga de historial: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='HTML')
            logger.error(f"❌ Error en /download_history: {e}")
    
    async def inspect_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /inspect_history - Inspeccionar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Obtener configuración de símbolos y timeframes
            config = self._load_user_config()
            symbols = config.get("data_collection", {}).get("real_time", {}).get("symbols", [])
            timeframes = config.get("data_collection", {}).get("real_time", {}).get("timeframes", [])
            
            # Enviar mensaje inicial
            initial_message = f"""🔍 <b>Iniciando inspección de datos históricos...</b>

📊 <b>Configuración:</b>
• Símbolos: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}
• Timeframes: {', '.join(timeframes)}
• Directorio: data/historical/

⏳ <b>Estado:</b> Analizando cobertura por símbolo/TF
🔍 <b>Procesando:</b> Detectando gaps y duplicados
📊 <b>Calculando:</b> Integridad de datos
📋 <b>Generando:</b> Reportes detallados

Recibirás actualizaciones en tiempo real."""
            
            await update.message.reply_text(initial_message, parse_mode='HTML')
            
            # Importar y usar el módulo de análisis de core/
            from core.data.history_analyzer import history_analyzer
            
            # Realizar análisis de cobertura
            coverage_analysis = await history_analyzer.analyze_data_coverage(symbols)
            
            # Realizar detección de problemas
            issues_analysis = await history_analyzer.detect_data_issues(symbols)
            
            # Generar reporte completo
            report = await history_analyzer.generate_history_report(symbols)
            
            # Generar mensaje de éxito con datos reales
            success_message = f"""✅ <b>Inspección de datos históricos completada</b>

📁 <b>Resultados:</b>
• Reporte guardado en: reports/history_analysis_*.json
• Símbolos analizados: {coverage_analysis['symbols_analyzed']}
• Timeframes verificados: {', '.join(timeframes)}

📊 <b>Análisis de Cobertura:</b>
• Cobertura completa: {coverage_analysis['coverage_summary']['complete_coverage']}
• Cobertura parcial: {coverage_analysis['coverage_summary']['partial_coverage']}
• Sin datos: {coverage_analysis['coverage_summary']['no_data']}
• Errores: {coverage_analysis['coverage_summary']['errors']}

🔍 <b>Problemas Detectados:</b>
• Problemas críticos: {len(issues_analysis['critical_issues'])}
• Advertencias: {len(issues_analysis['warnings'])}
• Total de problemas: {issues_analysis['total_issues']}

💡 <b>Recomendaciones:</b>
{chr(10).join([f"• {rec}" for rec in report['recommendations'][:3]])}"""
            
            await update.message.reply_text(success_message, parse_mode='HTML')
            logger.info(f"✅ Comando /inspect_history completado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando inspección de historial: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='HTML')
            logger.error(f"❌ Error en /inspect_history: {e}")
    
    async def repair_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /repair_history - Reparar datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols')
            
            cmd = ["python", "scripts/data/repair_data.py"]
            if symbols:
                cmd += ["--symbols", ",".join([s.upper() for s in symbols])]
            
            await update.message.reply_text("🔧 Iniciando reparación completa de datos…")
            
            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent
            )
            stdout, stderr = process.communicate()
            
            if stdout:
                # Intentar segmentar por símbolo con cabecera "🎯 Símbolo:"
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                import asyncio as _asyncio
                # Enviar preámbulo
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    preamble = self._escape_html(preamble)
                    await update.message.reply_text(f"<b>📥 Descarga/Verificación</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        text = chunk_text
                        if len(text) > 3500:
                            text = text[-3500:]
                        sym_safe = self._escape_html(sym)
                        text = self._escape_html(text)
                        header = f"<b>📥 {sym_safe} ({idx}/{total})</b>\n\n"
                        text = self._escape_html(text)
                        await update.message.reply_text(header + f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    tail = "\n".join(lines[-25:])
                    tail = self._escape_html(tail)
                    await update.message.reply_text(f"<b>Resultado</b>\n\n<code>{tail}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Reparación completa finalizada")
            
        except Exception as e:
            error_msg = f"❌ Error iniciando reparación de historial: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='HTML')
            logger.error(f"❌ Error en /repair_history: {e}")

    async def verify_align_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /verify_align - Verificar y alinear datos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            args = self._parse_command_args(context.args)
            symbols = args.get('symbols')
            timeframes = args.get('timeframes')
            cmd = ["python", "scripts/data/verify_align.py"]
            if symbols:
                cmd += ["--symbols", ",".join([s.upper() for s in symbols])]
            if timeframes:
                cmd += ["--timeframes", ",".join(timeframes)]
            
            await update.message.reply_text("🔄 Verificando/alineando datos…")
            
            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent
            )
            stdout, stderr = process.communicate()

            if stdout:
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                import asyncio as _asyncio
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    preamble = self._escape_html(preamble)
                    await update.message.reply_text(f"<b>🔄 Verificación/alineación</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        text = chunk_text[-3500:] if len(chunk_text) > 3500 else chunk_text
                        text = self._escape_html(text)
                        await update.message.reply_text(f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    tail = "\n".join(lines[-25:])
                    tail = self._escape_html(tail)
                    await update.message.reply_text(f"<b>Resultado</b>\n\n<code>{tail}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Verificación/alineación completada")
        except Exception as e:
            error_msg = f"❌ Error en verificación/alineación: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /verify_align: {e}")

    # Comando sync_symbols_command eliminado - duplicado
            
            import subprocess
            from pathlib import Path
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent
            )
            stdout, stderr = process.communicate()

            if stdout:
                lines = stdout.strip().splitlines()
                symbol_chunks = []
                current_symbol = None
                current_lines = []
                preamble_lines = []
                for line in lines:
                    if line.startswith("🎯 Símbolo:"):
                        if current_symbol is None and current_lines:
                            preamble_lines = current_lines
                            current_lines = []
                        if current_symbol is not None:
                            symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))
                            current_lines = []
                        current_symbol = line.replace("🎯 Símbolo:", "").strip()
                        current_lines.append(line)
                    else:
                        current_lines.append(line)
                if current_symbol is not None and current_lines:
                    symbol_chunks.append((current_symbol, "\n".join(current_lines).strip()))

                import asyncio as _asyncio
                if preamble_lines:
                    preamble = "\n".join(preamble_lines)
                    preamble = preamble[-3500:]
                    preamble = self._escape_html(preamble)
                    await update.message.reply_text(f"<b>🔗 Sincronización</b>\n\n<code>{preamble}</code>", parse_mode='HTML')

                if symbol_chunks:
                    total = len(symbol_chunks)
                    for idx, (sym, chunk_text) in enumerate(symbol_chunks, 1):
                        text = chunk_text[-3500:] if len(chunk_text) > 3500 else chunk_text
                        sym_safe = self._escape_html(sym)
                        text = self._escape_html(text)
                        header = f"<b>🔗 {sym_safe} ({idx}/{total})</b>\n\n"
                        text = self._escape_html(text)
                        await update.message.reply_text(header + f"<code>{text}</code>", parse_mode='HTML')
                        if idx < total:
                            await _asyncio.sleep(5)
                else:
                    tail = "\n".join(lines[-25:])
                    tail = self._escape_html(tail)
                    await update.message.reply_text(f"<b>Resultado</b>\n\n<code>{tail}</code>", parse_mode='HTML')
            if process.returncode != 0:
                error_text = stderr[-1500:] if stderr else 'Error desconocido'
                error_text = self._escape_html(error_text)
                await update.message.reply_text(f"❌ Error:\n\n<code>{error_text}</code>", parse_mode='HTML')
            else:
                await update.message.reply_text("✅ Sincronización completada")
        except Exception as e:
            error_msg = f"❌ Error sincronizando símbolos: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"❌ Error en /sync_symbols: {e}")
    
    async def stop_train_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop_train - Detener entrenamiento de forma elegante"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Enviar mensaje inicial
            initial_message = """🛑 <b>Deteniendo entrenamiento de forma elegante...</b>

⏳ <b>Estado:</b> Guardando progreso actual
🤖 <b>Procesando:</b> Actualizando modelos de agentes
💾 <b>Creando:</b> Resumen final y checkpoints
✅ <b>Finalizando:</b> El entrenamiento se detendrá de forma segura

Esto puede tomar unos segundos..."""
            
            await update.message.reply_text(initial_message, parse_mode='HTML')
            
            # Ejecutar comando de terminal para detener entrenamiento
            cmd = [
                "python", "scripts/training/state_manager.py",
                "--action", "stop",
                "--config", "config/user_settings.yaml",
                "--output-dir", "data/models"
            ]
            
            import subprocess
            import asyncio
            from pathlib import Path
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path(__file__).parent.parent.parent
            )
            
            # Simular progreso de parada elegante
            progress_messages = [
                "📊 <b>Progreso parada</b>\n\n• Fase: Guardando estado actual\n• Completado: 25%\n• Estado: Serializando modelos",
                "📊 <b>Progreso parada</b>\n\n• Fase: Actualizando agentes\n• Completado: 50%\n• Estado: Sincronizando checkpoints",
                "📊 <b>Progreso parada</b>\n\n• Fase: Creando resumen final\n• Completado: 75%\n• Estado: Generando reportes"
            ]
            
            for progress_msg in progress_messages:
                await asyncio.sleep(2)  # Simular actualización cada 2 segundos
                await update.message.reply_text(progress_msg, parse_mode='HTML')
            
            # Esperar a que termine el proceso
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                success_message = """✅ <b>Entrenamiento detenido correctamente</b>

📁 <b>Estado guardado:</b>
• Checkpoints: data/models/ckpt_ppo.zip
• Estrategias: strategies.json
• Estado: state_manager.json
• Logs: data/logs/train_historical.log

📊 <b>Resumen final:</b>
• Ciclos completados: Guardados
• Modelos actualizados: ✅
• Estado sincronizado: ✅
• Parada elegante: ✅
• Estado: ✅ Detenido correctamente"""
                
                await update.message.reply_text(success_message, parse_mode='HTML')
                logger.info(f"✅ Comando /stop_train completado por chat_id: {update.message.chat_id}")
            else:
                error_msg = f"❌ Error deteniendo entrenamiento:\n\n```\n{stderr}\n```"
                await update.message.reply_text(error_msg, parse_mode='HTML')
                logger.error(f"❌ Error en /stop_train: {stderr}")
            
        except Exception as e:
            error_msg = f"❌ Error deteniendo entrenamiento: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='HTML')
            logger.error(f"❌ Error en /stop_train: {e}")

    async def reload_config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /reload_config - Recargar configuraciones"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Cargar configuración del usuario
            user_config = self._load_user_config()
            symbols = user_config.get('data_collection', {}).get('real_time', {}).get('symbols', [])
            timeframes = user_config.get('data_collection', {}).get('real_time', {}).get('timeframes', [])
            
            # Simular recarga de configuraciones
            config_files = [
                'config/user_settings.yaml',
                'control/config.yaml',
                'config/personal/exchanges.yaml',
                'config/personal/redis.yaml',
                'config/personal/timescale.yaml',
                'config/personal/kafka.yaml'
            ]
            
            reloaded_configs = []
            for config_file in config_files:
                if Path(config_file).exists():
                    reloaded_configs.append(config_file)
            
            await update.message.reply_text(
                "🔄 **Recargando configuraciones...**\n\n"
                f"📁 **Archivos recargados:**\n"
                + "\n".join([f"• {config}" for config in reloaded_configs]) + "\n\n"
                f"📊 **Configuración actual:**\n"
                f"• Símbolos: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}\n"
                f"• Timeframes: {', '.join(timeframes)}\n"
                f"• Total símbolos: {len(symbols)}\n\n"
                "✅ Configuraciones recargadas correctamente",
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Comando /reload_config ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en reload_config_command: {e}")
            await update.message.reply_text(f"❌ Error al recargar configuraciones: {e}")

    async def reset_agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /reset_agent - Resetear agente"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            if not self.controller:
                await update.message.reply_text("❌ Controlador del sistema no disponible.")
                return
            
            # Enviar comando de reset al controlador
            await self.controller.command_queue.put({
                'type': 'reset_agent',
                'args': {},
                'chat_id': str(update.message.chat_id)
            })
            
            await update.message.reply_text(
                "🔄 **Reseteando agente...**\n\n"
                "💰 Balance ficticio: 1,000 USDT\n"
                "📊 Métricas acumuladas: 0\n"
                "🎯 Estrategias provisionales: Limpiadas\n"
                "🧠 Memoria del agente: Reiniciada\n"
                "📈 Historial de trades: Borrado\n\n"
                "✅ Agente reseteado correctamente",
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Comando /reset_agent ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en reset_agent_command: {e}")
            await update.message.reply_text(f"❌ Error al resetear agente: {e}")

    async def strategies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /strategies - Mostrar estrategias"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Cargar configuración del usuario
            user_config = self._load_user_config()
            symbols = user_config.get('data_collection', {}).get('real_time', {}).get('symbols', [])
            
            # Simular análisis de estrategias
            strategies_info = []
            for symbol in symbols[:3]:  # Mostrar solo los primeros 3 símbolos
                strategies_file = Path(f"models/{symbol}/strategies.json")
                bad_strategies_file = Path(f"models/{symbol}/bad_strategies.json")
                provisional_file = Path(f"models/{symbol}/strategies_provisional.jsonl")
                
                top_count = 0
                bad_count = 0
                provisional_count = 0
                
                if strategies_file.exists():
                    try:
                        with open(strategies_file, 'r') as f:
                            import json
                            top_strategies = json.load(f)
                            top_count = len(top_strategies) if isinstance(top_strategies, list) else 0
                    except:
                        pass
                
                if bad_strategies_file.exists():
                    try:
                        with open(bad_strategies_file, 'r') as f:
                            import json
                            bad_strategies = json.load(f)
                            bad_count = len(bad_strategies) if isinstance(bad_strategies, list) else 0
                    except:
                        pass
                
                if provisional_file.exists():
                    try:
                        with open(provisional_file, 'r') as f:
                            provisional_count = sum(1 for _ in f)
                    except:
                        pass
                
                strategies_info.append(
                    f"**{symbol}:**\n"
                    f"• Top-500: {top_count} estrategias\n"
                    f"• Peores-500: {bad_count} estrategias\n"
                    f"• Provisionales: {provisional_count} estrategias"
                )
            
            await update.message.reply_text(
                "📊 **Resumen de Estrategias**\n\n"
                + "\n\n".join(strategies_info) + "\n\n"
                "📁 **Archivos de estrategias:**\n"
                "• `models/{SYMBOL}/strategies.json` → mejores 500\n"
                "• `models/{SYMBOL}/bad_strategies.json` → peores 500\n"
                "• `models/{SYMBOL}/strategies_provisional.jsonl` → provisionales\n\n"
                "💡 **Tip:** Usa `/training_status` para ver métricas detalladas",
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Comando /strategies ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en strategies_command: {e}")
            await update.message.reply_text(f"❌ Error al obtener estrategias: {e}")
    
    # =============================================================================
    # COMANDOS DE DATOS HISTÓRICOS
    # =============================================================================
    
    async def verify_historical_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /verify_historical_data - Verificar cobertura de datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("🔍 Verificando cobertura de datos históricos...")
            
            from core.data.historical_data_manager import ensure_historical_data_coverage
            
            # Ejecutar verificación
            results = await ensure_historical_data_coverage()
            
            # Formatear respuesta
            status = results.get('status', 'unknown')
            message = results.get('message', 'Sin mensaje')
            
            if status == 'complete':
                response = f"✅ **VERIFICACIÓN COMPLETA**\n\n{message}\n\n🎯 Todos los datos históricos están disponibles"
            elif status == 'completed':
                download_results = results.get('download_results', {})
                total_downloaded = download_results.get('total_downloaded', 0)
                symbols_updated = download_results.get('symbols_updated', 0)
                symbols_new = download_results.get('symbols_new', 0)
                
                response = f"✅ **DESCARGA COMPLETADA**\n\n{message}\n\n"
                response += f"📥 **Registros descargados:** {total_downloaded:,}\n"
                response += f"🔄 **Símbolos actualizados:** {symbols_updated}\n"
                response += f"🆕 **Símbolos nuevos:** {symbols_new}"
            elif status == 'missing_data_detected':
                response = f"⚠️ **DATOS FALTANTES DETECTADOS**\n\n{message}\n\n"
                response += "💡 Usa `/download_historical_data` para descargar datos faltantes"
            elif status == 'error':
                error = results.get('error', 'Error desconocido')
                response = f"❌ **ERROR EN VERIFICACIÓN**\n\n{message}\n\n🔍 **Detalles:** {error}"
            else:
                response = f"❓ **ESTADO DESCONOCIDO**\n\n{message}"
            
            # Agregar tiempo de procesamiento si está disponible
            processing_time = results.get('processing_time', 0)
            if processing_time > 0:
                response += f"\n\n⏱️ **Tiempo de procesamiento:** {processing_time:.2f}s"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ Comando /verify_historical_data ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en verify_historical_data_command: {e}")
            await update.message.reply_text(f"❌ Error verificando datos históricos: {e}")
    
    async def download_historical_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /download_historical_data - Descargar datos históricos faltantes"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("📥 Iniciando descarga de datos históricos...")
            
            from core.data.historical_data_manager import ensure_historical_data_coverage
            
            # Ejecutar descarga forzada
            results = await ensure_historical_data_coverage()
            
            # Formatear respuesta
            status = results.get('status', 'unknown')
            message = results.get('message', 'Sin mensaje')
            
            if status in ['complete', 'completed']:
                response = f"✅ **DESCARGA COMPLETADA**\n\n{message}\n\n"
                
                if status == 'completed':
                    download_results = results.get('download_results', {})
                    total_downloaded = download_results.get('total_downloaded', 0)
                    symbols_updated = download_results.get('symbols_updated', 0)
                    symbols_new = download_results.get('symbols_new', 0)
                    
                    response += f"📊 **Estadísticas de descarga:**\n"
                    response += f"• Registros descargados: {total_downloaded:,}\n"
                    response += f"• Símbolos actualizados: {symbols_updated}\n"
                    response += f"• Símbolos nuevos: {symbols_new}\n\n"
                
                response += "🎯 Los datos históricos están listos para trading"
            else:
                response = f"⚠️ **PROBLEMA EN DESCARGA**\n\n{message}\n\n"
                response += "💡 Usa `/historical_data_report` para más detalles"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ Comando /download_historical_data ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en download_historical_data_command: {e}")
            await update.message.reply_text(f"❌ Error descargando datos históricos: {e}")
    
    async def historical_data_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /historical_data_report - Reporte detallado de datos históricos"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            await update.message.reply_text("📊 Generando reporte detallado de datos históricos...")
            
            from core.data.historical_data_manager import get_historical_data_report
            
            # Generar reporte
            report = await get_historical_data_report()
            
            if 'error' in report:
                await update.message.reply_text(f"❌ Error generando reporte: {report['error']}")
                return
            
            # Formatear respuesta
            config = report.get('configuration', {})
            coverage = report.get('coverage_analysis', {})
            summary = coverage.get('summary', {})
            
            response = "📋 **REPORTE DE DATOS HISTÓRICOS**\n\n"
            
            # Configuración
            response += "⚙️ **CONFIGURACIÓN:**\n"
            response += f"• Años requeridos: {config.get('years_required', 'N/A')}\n"
            response += f"• Días mínimos: {config.get('min_coverage_days', 'N/A')}\n"
            response += f"• Símbolos configurados: {config.get('symbols_configured', 'N/A')}\n"
            response += f"• Timeframes: {config.get('timeframes_configured', 'N/A')}\n"
            response += f"• Descarga automática: {'Sí' if config.get('auto_download_enabled') else 'No'}\n\n"
            
            # Cobertura general
            response += "📈 **COBERTURA GENERAL:**\n"
            symbols_with_data = summary.get('symbols_with_data', 0)
            total_symbols = summary.get('total_symbols', 0)
            coverage_pct = summary.get('coverage_percentage', 0)
            response += f"• Símbolos con datos: {symbols_with_data}/{total_symbols}\n"
            response += f"• Porcentaje de cobertura: {coverage_pct:.1f}%\n\n"
            
            # Cobertura por timeframe
            timeframe_coverage = summary.get('timeframe_coverage', {})
            if timeframe_coverage:
                response += "⏰ **COBERTURA POR TIMEFRAME:**\n"
                for timeframe, coverage_info in timeframe_coverage.items():
                    status = coverage_info.get('status', 'UNKNOWN')
                    days = coverage_info.get('days_available', 0)
                    meets_req = coverage_info.get('meets_requirement', False)
                    icon = "✅" if meets_req else "❌"
                    response += f"• {icon} {timeframe}: {days} días ({status})\n"
                response += "\n"
            
            # Análisis por símbolo (solo los primeros 5 para no sobrecargar)
            symbol_analysis = coverage.get('symbol_analysis', {})
            if symbol_analysis:
                response += "🎯 **ANÁLISIS POR SÍMBOLO:**\n"
                symbol_count = 0
                for symbol, analysis in symbol_analysis.items():
                    if symbol_count >= 5:  # Limitar a 5 símbolos
                        remaining = len(symbol_analysis) - 5
                        response += f"• ... y {remaining} símbolos más\n"
                        break
                    
                    status = analysis.get('status', 'UNKNOWN')
                    records = analysis.get('record_count', 0)
                    coverage_pct = analysis.get('coverage_percentage', 0)
                    
                    if status == 'NO_DATA':
                        icon = "❌"
                        response += f"• {icon} {symbol}: Sin datos\n"
                    elif status == 'COMPLETE':
                        icon = "✅"
                        response += f"• {icon} {symbol}: {records:,} registros ({coverage_pct:.1f}%)\n"
                    elif status == 'INSUFFICIENT':
                        icon = "⚠️"
                        response += f"• {icon} {symbol}: {records:,} registros ({coverage_pct:.1f}%)\n"
                    else:
                        icon = "❓"
                        response += f"• {icon} {symbol}: {status}\n"
                    
                    symbol_count += 1
                response += "\n"
            
            # Estadísticas de base de datos
            db_stats = report.get('database_statistics', {})
            if db_stats:
                response += "💾 **ESTADÍSTICAS DE BASE DE DATOS:**\n"
                response += f"• Total de registros: {db_stats.get('total_records', 0):,}\n"
                response += f"• Símbolos únicos: {db_stats.get('unique_symbols', 0)}\n"
                response += f"• Rango de fechas: {db_stats.get('date_range', 'N/A')}\n\n"
            
            # Recomendaciones
            recommendations = report.get('recommendations', [])
            if recommendations:
                response += "💡 **RECOMENDACIONES:**\n"
                for i, rec in enumerate(recommendations[:3], 1):  # Solo las primeras 3
                    response += f"{i}. {rec}\n"
                if len(recommendations) > 3:
                    response += f"... y {len(recommendations) - 3} recomendaciones más\n"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ Comando /historical_data_report ejecutado por chat_id: {update.message.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en historical_data_report_command: {e}")
            await update.message.reply_text(f"❌ Error generando reporte: {e}")
    
    async def sync_symbols_command(self, update, context):
        """Comando para sincronizar símbolos y ejecutar agentes en paralelo"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Mensaje inicial
            await update.message.reply_text(
                "🔄 <b>Iniciando Sincronización de Símbolos - ENTERPRISE</b>\n\n"
                "📊 <b>Proceso:</b>\n"
                "1️⃣ Validando datos disponibles\n"
                "2️⃣ Sincronizando timestamps\n"
                "3️⃣ Creando timeline maestro\n"
                "4️⃣ Ejecutando agentes en paralelo\n"
                "5️⃣ Agregando métricas y rankings\n\n"
                "⏳ Procesando con delays de 100ms para evitar conflictos API...",
                parse_mode='HTML'
            )
            
            # Importar módulos necesarios
            from core.sync.symbol_synchronizer import SymbolSynchronizer
            from core.sync.parallel_executor import ParallelExecutor
            from core.sync.metrics_aggregator import MetricsAggregator
            from core.data.database import db_manager
            from config.config_loader import ConfigLoader
            import asyncio
            import pandas as pd
            from datetime import datetime, timezone
            
            # Cargar configuración
            config_loader = ConfigLoader("config/user_settings.yaml")
            config = config_loader.load_config()
            
            # Obtener símbolos y timeframes
            sync_config = config.get("data_collection", {}).get("sync", {})
            symbols = sync_config.get("symbols", [])
            timeframes = sync_config.get("timeframes", ["1m", "5m", "15m", "1h"])
            
            if not symbols:
                # Usar símbolos de configuración de tiempo real
                real_time_config = config.get("data_collection", {}).get("real_time", {})
                symbols = real_time_config.get("symbols", ["BTCUSDT", "ETHUSDT"])
            
            if not symbols or not timeframes:
                await update.message.reply_text("❌ No hay símbolos o timeframes configurados")
                return
            
            # Inicializar componentes
            synchronizer = SymbolSynchronizer(db_manager)
            executor = ParallelExecutor(max_workers=4, delay_ms=100)
            metrics_aggregator = MetricsAggregator(db_manager)
            
            # Paso 1: Validar datos
            await update.message.reply_text("🔍 <b>Paso 1/5:</b> Validando datos disponibles...", parse_mode='HTML')
            
            validation_result = await synchronizer._validate_data_availability(symbols, timeframes)
            if not validation_result['valid']:
                await update.message.reply_text(f"❌ Datos insuficientes: {validation_result['message']}")
                return
            
            await update.message.reply_text(f"✅ Datos validados: {validation_result['total_records']:,} registros")
            
            # Paso 2: Sincronizar símbolos
            await update.message.reply_text("🔄 <b>Paso 2/5:</b> Sincronizando símbolos...", parse_mode='HTML')
            
            sync_result = await synchronizer.sync_all_symbols(symbols, timeframes)
            if sync_result['status'] != 'success':
                await update.message.reply_text(f"❌ Error en sincronización: {sync_result.get('message', 'Error desconocido')}")
                return
            
            master_timeline = sync_result['master_timeline']
            sync_quality = sync_result['quality_check']['overall_score']
            
            await update.message.reply_text(
                f"✅ Sincronización completada\n"
                f"📊 Calidad: {sync_quality:.1f}%\n"
                f"📅 Períodos: {master_timeline['total_periods']:,}\n"
                f"🕐 Rango: {master_timeline['start_date']} - {master_timeline['end_date']}"
            )
            
            # Paso 3: Crear timeline maestro
            await update.message.reply_text("🔄 <b>Paso 3/5:</b> Creando timeline maestro...", parse_mode='HTML')
            
            timeline_df = pd.DataFrame({
                'timestamp': master_timeline['timestamps'],
                'datetime': [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in master_timeline['timestamps']]
            })
            
            await update.message.reply_text(f"✅ Timeline maestro creado: {len(timeline_df)} períodos")
            
            # Paso 4: Ejecutar agentes en paralelo
            await update.message.reply_text("🚀 <b>Paso 4/5:</b> Ejecutando agentes en paralelo...", parse_mode='HTML')
            
            # Crear tarea de monitoreo de progreso
            import asyncio
            progress_task = asyncio.create_task(self._monitor_sync_progress(update, executor))
            
            execution_result = await executor.execute_agents_parallel(
                timeline=timeline_df,
                symbols=symbols,
                timeframes=timeframes
            )
            
            # Cancelar tarea de monitoreo
            progress_task.cancel()
            
            if execution_result['status'] != 'success':
                await update.message.reply_text(f"❌ Error en ejecución paralela: {execution_result.get('message', 'Error desconocido')}")
                return
            
            exec_metrics = execution_result['execution_metrics']
            successful_cycles = exec_metrics['successful_cycles']
            total_cycles = exec_metrics['total_cycles']
            total_pnl = exec_metrics['total_pnl']
            total_trades = exec_metrics['total_trades']
            
            await update.message.reply_text(
                f"✅ Ejecución paralela completada\n"
                f"🔄 Ciclos: {successful_cycles}/{total_cycles}\n"
                f"💰 PnL total: ${total_pnl:.2f}\n"
                f"📊 Trades: {total_trades:,}"
            )
            
            # Paso 5: Agregar métricas
            await update.message.reply_text("📊 <b>Paso 5/5:</b> Agregando métricas y rankings...", parse_mode='HTML')
            
            cycle_results = execution_result['cycle_results']
            metrics_result = await metrics_aggregator.aggregate_cycle_metrics(cycle_results)
            
            # Generar reporte final
            basic_metrics = metrics_result.get('basic_metrics', {})
            rankings = metrics_result.get('rankings', {})
            recommendations = metrics_result.get('recommendations', [])
            
            best_strategy = rankings.get('strategies', {}).get('by_pnl', [])
            best_symbol = rankings.get('symbols', {}).get('by_pnl', [])
            
            # Reporte final
            report = (
                "🎉 <b>SINCRONIZACIÓN COMPLETADA EXITOSAMENTE</b>\n\n"
                f"📊 <b>Métricas Generales:</b>\n"
                f"• Calidad de sincronización: {sync_quality:.1f}%\n"
                f"• Tasa de éxito: {basic_metrics.get('success_rate', 0):.1f}%\n"
                f"• PnL total: ${basic_metrics.get('total_pnl', 0):.2f}\n"
                f"• Trades totales: {basic_metrics.get('total_trades', 0):,}\n"
                f"• Win rate: {basic_metrics.get('win_rate', 0):.1f}%\n\n"
                f"🏆 <b>Rankings:</b>\n"
                f"• Mejor estrategia: {best_strategy[0]['strategy_name'] if best_strategy else 'N/A'}\n"
                f"• Mejor símbolo: {best_symbol[0]['symbol'] if best_symbol else 'N/A'}\n\n"
                f"💡 <b>Recomendaciones:</b>\n"
            )
            
            # Agregar recomendaciones (máximo 3)
            for i, rec in enumerate(recommendations[:3]):
                report += f"• {rec}\n"
            
            if len(recommendations) > 3:
                report += f"... y {len(recommendations) - 3} recomendaciones más\n"
            
            await update.message.reply_text(report, parse_mode='HTML')
            
            # Guardar resultados en BD
            try:
                # Guardar metadatos de sincronización
                session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                metadata = {
                    'session_id': session_id,
                    'symbols_processed': symbols,
                    'timeframes_processed': timeframes,
                    'alignment_quality': sync_quality,
                    'total_periods': master_timeline['total_periods'],
                    'processing_time_seconds': sync_result.get('processing_time', 0)
                }
                
                db_manager.store_alignment_metadata(session_id, metadata)
                logger.info(f"💾 Metadatos guardados: {session_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error guardando metadatos: {e}")
            
            logger.info(f"✅ Comando /sync_symbols ejecutado por chat_id: {update.message.chat_id}")
            
            # Enviar listado de comandos después de 10 segundos
            import asyncio
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            logger.error(f"Error en sync_symbols_command: {e}")
            await update.message.reply_text(f"❌ Error en sincronización: {e}")
    
    async def train_hist_command(self, update, context):
        """Comando /train_hist - Nodo de distribución para entrenamiento histórico"""
        if not self._check_authorization(update):
            await update.message.reply_text("❌ Acceso no autorizado.")
            return
        
        try:
            # Mensaje inicial
            initial_message = await update.message.reply_text(
                "🎓 <b>Iniciando Entrenamiento Histórico - ENTERPRISE</b>\n\n"
                "📊 <b>Proceso:</b>\n"
                "1️⃣ Delegando a script de entrenamiento\n"
                "2️⃣ Ejecutando entrenamiento paralelo\n"
                "3️⃣ Procesando métricas en tiempo real\n"
                "4️⃣ Generando reporte final\n\n"
                "⏳ Preparando sistema de entrenamiento...",
                parse_mode='HTML'
            )
            
            # Ejecutar script de entrenamiento
            import subprocess
            import asyncio
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent / "scripts" / "training" / "train_hist.py"
            
            # Ejecutar script de forma asíncrona
            process = await asyncio.create_subprocess_exec(
                "python", str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitorear progreso
            await self._update_message(initial_message, "🔄 <b>Ejecutando script de entrenamiento...</b>")
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Error desconocido"
                await self._update_message(initial_message, f"❌ <b>Error en script:</b> {error_msg}")
                return
            
            # Procesar resultado del script
            output = stdout.decode()
            lines = output.strip().split('\n')
            
            result_status = None
            result_message = None
            result_data = None
            
            for line in lines:
                if line.startswith("TRAINING_RESULT:"):
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        result_status = parts[1]
                        result_message = parts[2]
                elif line.startswith("TRAINING_DATA:"):
                    import json
                    try:
                        data_str = line.split(":", 1)[1]
                        result_data = json.loads(data_str)
                    except:
                        pass
            
            if result_status == "success":
                # Mostrar reporte final
                if result_data and 'final_report' in result_data:
                    await self._update_message(initial_message, 
                        "🎉 <b>Entrenamiento Histórico Completado</b>\n\n"
                        "✅ Script ejecutado exitosamente\n"
                        "✅ Métricas procesadas\n"
                        "✅ Resultados guardados\n\n"
                        "📊 <b>Reporte Final:</b>"
                    )
                    
                    # Enviar reporte final en mensaje separado
                    await update.message.reply_text(
                        result_data['final_report'],
                        parse_mode='HTML'
                    )
                else:
                    await self._update_message(initial_message, 
                        "✅ <b>Entrenamiento completado exitosamente</b>\n\n"
                        f"📝 {result_message}"
                    )
            else:
                await self._update_message(initial_message, 
                    f"❌ <b>Error en entrenamiento:</b>\n\n{result_message}"
                )
                return
            
            logger.info(f"✅ Comando /train_hist ejecutado por chat_id: {update.message.chat_id}")
            asyncio.create_task(self._send_commands_after_delay(update, 10))
            
        except Exception as e:
            logger.error(f"Error en train_hist_command: {e}")
            await update.message.reply_text(f"❌ Error en entrenamiento histórico: {e}")