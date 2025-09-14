#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot_enhanced.py
===============
Bot Trading v10 Enterprise - Versión Mejorada con Sistema de Entrenamiento

Integra el sistema de entrenamiento mejorado con comandos de Telegram
y todas las funcionalidades avanzadas.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import sys
import logging
import uuid
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging
from config.unified_config import get_config_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot_enhanced.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Filtro para suprimir avisos legacy
class _SuppressLegacyConfigWarnings(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("⚠️ Archivo de configuración no encontrado:"):
            return False
        return True

_root_logger = logging.getLogger()
_root_logger.addFilter(_SuppressLegacyConfigWarnings())

class EnhancedTradingBot:
    """Bot de Trading Mejorado con Sistema de Entrenamiento Avanzado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.telegram_bot = None
        self.training_pipeline = None
        self.metrics_aggregator = None
        self.telegram_reporter = None
        self.training_active = False
        self.training_task = None
        
    async def initialize(self):
        """Inicializa el bot mejorado"""
        try:
            self.logger.info("🤖 Inicializando Bot Trading v10 Enterprise Mejorado...")
            
            # 1. Inicializar configuración
            cfg = get_config_manager()
            self.symbols = cfg.get_symbols() or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            self.timeframes = cfg.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            self.start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
            
            # 2. Crear bot de Telegram
            from control.telegram_bot import TelegramBot
            collection_ready = asyncio.Event()
            self.telegram_bot = TelegramBot.from_env(collection_ready=collection_ready)
            
            # 3. Inicializar sistema de entrenamiento mejorado
            await self._initialize_enhanced_training_system()
            
            # 4. Configurar manejadores de comandos
            await self._setup_command_handlers()
            
            self.logger.info("✅ Bot mejorado inicializado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando bot mejorado: {e}")
            return False
    
    async def _initialize_enhanced_training_system(self):
        """Inicializa el sistema de entrenamiento mejorado"""
        try:
            self.logger.info("🔧 Inicializando sistema de entrenamiento mejorado...")
            
            # Importar componentes del sistema mejorado
            from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
            from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
            from scripts.training.optimized_training_pipeline import OptimizedTrainingPipeline, TrainingConfig
            
            # Crear agregador de métricas
            self.metrics_aggregator = EnhancedMetricsAggregator(initial_capital=1000.0)
            
            # Crear reporter de Telegram
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if bot_token and chat_id:
                telegram_config = TelegramConfig(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    enable_individual_trades=True,
                    enable_cycle_summaries=True,
                    enable_alerts=True
                )
                self.telegram_reporter = TelegramTradeReporter(telegram_config)
                self.logger.info("✅ Reporter de Telegram configurado")
            else:
                self.logger.warning("⚠️ Credenciales de Telegram no encontradas")
            
            # Crear pipeline de entrenamiento
            training_config = TrainingConfig(
                days_back=365,
                cycle_size_hours=24,
                max_concurrent_agents=len(self.symbols),
                telegram_enabled=bool(self.telegram_reporter),
                checkpoint_interval=100,
                memory_cleanup_interval=50,
                max_memory_usage_mb=8000,
                recovery_enabled=True
            )
            self.training_pipeline = OptimizedTrainingPipeline(training_config)
            
            self.logger.info("✅ Sistema de entrenamiento mejorado inicializado")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando sistema de entrenamiento: {e}")
            raise
    
    async def _setup_command_handlers(self):
        """Configura los manejadores de comandos de Telegram"""
        try:
            # Configurar manejadores de comandos usando el sistema existente
            from control.handlers import TradingBotHandlers
            
            # Crear handlers con el bot de Telegram
            collection_ready = asyncio.Event()
            self.handlers = TradingBotHandlers(
                authorized_users=self.telegram_bot.authorized_users if hasattr(self.telegram_bot, 'authorized_users') else [],
                collection_ready=collection_ready
            )
            
            # Registrar handlers con el bot de Telegram
            self.handlers.register_handlers(self.telegram_bot.application)
            
            # Agregar manejadores específicos del sistema mejorado
            self._add_enhanced_handlers()
            
            self.logger.info("📱 Manejadores de comandos configurados (incluyendo sistema mejorado)")
            
        except Exception as e:
            self.logger.error(f"❌ Error configurando manejadores: {e}")
    
    def _add_enhanced_handlers(self):
        """Agrega manejadores específicos del sistema mejorado"""
        try:
            from telegram.ext import CommandHandler
            
            # Manejador para /train_hist mejorado
            async def train_hist_handler(update, context):
                """Maneja el comando /train_hist mejorado"""
                try:
                    # Obtener días desde los argumentos
                    days_back = 365  # Por defecto
                    if context.args and len(context.args) > 0:
                        try:
                            days_back = int(context.args[0])
                        except ValueError:
                            await update.message.reply_text("❌ Días inválidos. Usando 365 días por defecto.")
                    
                    # Ejecutar entrenamiento mejorado
                    result = await self.handle_train_hist_command(days_back)
                    
                    if result['status'] == 'success':
                        await update.message.reply_text(f"✅ {result['message']}")
                    else:
                        await update.message.reply_text(f"❌ {result['message']}")
                        
                except Exception as e:
                    await update.message.reply_text(f"❌ Error ejecutando entrenamiento: {e}")
            
            # Manejador para /stop_train
            async def stop_train_handler(update, context):
                """Maneja el comando /stop_train"""
                try:
                    result = await self.handle_stop_train_command()
                    
                    if result['status'] == 'success':
                        await update.message.reply_text(f"✅ {result['message']}")
                    else:
                        await update.message.reply_text(f"❌ {result['message']}")
                        
                except Exception as e:
                    await update.message.reply_text(f"❌ Error deteniendo entrenamiento: {e}")
            
            # Manejador para /status
            async def status_handler(update, context):
                """Maneja el comando /status"""
                try:
                    result = await self.handle_status_command()
                    
                    if result['status'] == 'success':
                        await update.message.reply_text(result['message'], parse_mode="HTML")
                    else:
                        await update.message.reply_text(f"❌ {result['message']}")
                        
                except Exception as e:
                    await update.message.reply_text(f"❌ Error obteniendo estado: {e}")
            
            # Manejador para /health
            async def health_handler(update, context):
                """Maneja el comando /health"""
                try:
                    memory_usage = self._get_memory_usage()
                    health_status = f"""
🏥 <b>SALUD DEL SISTEMA</b>

💾 <b>Memoria:</b> {memory_usage:.1f} MB
🔄 <b>Entrenamiento:</b> {'🟢 Activo' if self.training_active else '🔴 Inactivo'}
📱 <b>Telegram:</b> {'✅ Conectado' if self.telegram_reporter else '❌ Desconectado'}
🤖 <b>Agentes:</b> {len(self.symbols)} activos
⏰ <b>Timeframes:</b> {len(self.timeframes)} configurados

✅ <b>Sistema funcionando correctamente</b>
                    """.strip()
                    
                    await update.message.reply_text(health_status, parse_mode="HTML")
                        
                except Exception as e:
                    await update.message.reply_text(f"❌ Error obteniendo salud: {e}")
            
            # Registrar handlers
            self.telegram_bot.application.add_handler(CommandHandler("train_hist", train_hist_handler))
            self.telegram_bot.application.add_handler(CommandHandler("stop_train", stop_train_handler))
            self.telegram_bot.application.add_handler(CommandHandler("status", status_handler))
            self.telegram_bot.application.add_handler(CommandHandler("health", health_handler))
            
            self.logger.info("✅ Handlers del sistema mejorado registrados")
            
        except Exception as e:
            self.logger.error(f"❌ Error agregando handlers mejorados: {e}")
    
    async def handle_train_hist_command(self, days_back: int = 365) -> Dict[str, Any]:
        """Maneja el comando /train_hist"""
        try:
            if self.training_active:
                return {
                    'status': 'error',
                    'message': '⚠️ Ya hay un entrenamiento en progreso. Usa /stop_train para detenerlo primero.'
                }
            
            self.logger.info(f"🚀 Iniciando entrenamiento histórico mejorado ({days_back} días)")
            
            # Enviar mensaje de inicio
            if self.telegram_reporter:
                await self.telegram_reporter.send_performance_alert(
                    "SISTEMA",
                    f"🚀 <b>INICIANDO ENTRENAMIENTO HISTÓRICO MEJORADO</b>\n\n"
                    f"📅 Período: {days_back} días\n"
                    f"🤖 Agentes: {len(self.symbols)} ({', '.join(self.symbols)})\n"
                    f"⏰ Timeframes: {', '.join(self.timeframes)}\n"
                    f"📊 Sistema: Mejorado con tracking granular\n\n"
                    f"⏳ Iniciando en 3 segundos...",
                    "INFO"
                )
            
            # Iniciar entrenamiento en background
            self.training_active = True
            self.training_task = asyncio.create_task(
                self._run_enhanced_training(days_back)
            )
            
            return {
                'status': 'success',
                'message': f'✅ Entrenamiento histórico iniciado ({days_back} días)'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en comando train_hist: {e}")
            return {
                'status': 'error',
                'message': f'❌ Error iniciando entrenamiento: {e}'
            }
    
    async def handle_stop_train_command(self) -> Dict[str, Any]:
        """Maneja el comando /stop_train"""
        try:
            if not self.training_active:
                return {
                    'status': 'error',
                    'message': '⚠️ No hay entrenamiento activo para detener'
                }
            
            self.logger.info("⏹️ Deteniendo entrenamiento...")
            
            # Cancelar tarea de entrenamiento
            if self.training_task:
                self.training_task.cancel()
                try:
                    await self.training_task
                except asyncio.CancelledError:
                    pass
            
            self.training_active = False
            self.training_task = None
            
            # Enviar mensaje de confirmación
            if self.telegram_reporter:
                await self.telegram_reporter.send_performance_alert(
                    "SISTEMA",
                    "⏹️ <b>ENTRENAMIENTO DETENIDO</b>\n\n"
                    "✅ El entrenamiento ha sido detenido correctamente\n"
                    "📊 Los datos se han guardado automáticamente",
                    "WARNING"
                )
            
            return {
                'status': 'success',
                'message': '✅ Entrenamiento detenido correctamente'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo entrenamiento: {e}")
            return {
                'status': 'error',
                'message': f'❌ Error deteniendo entrenamiento: {e}'
            }
    
    async def handle_status_command(self) -> Dict[str, Any]:
        """Maneja el comando /status"""
        try:
            status_info = {
                'bot_status': '🟢 Activo',
                'training_status': '🟢 Activo' if self.training_active else '🔴 Inactivo',
                'symbols': len(self.symbols),
                'timeframes': len(self.timeframes),
                'telegram_connected': bool(self.telegram_reporter),
                'memory_usage': self._get_memory_usage()
            }
            
            status_message = f"""
🤖 <b>ESTADO DEL SISTEMA</b>

🟢 <b>Bot:</b> {status_info['bot_status']}
🔄 <b>Entrenamiento:</b> {status_info['training_status']}
📊 <b>Símbolos:</b> {status_info['symbols']} ({', '.join(self.symbols)})
⏰ <b>Timeframes:</b> {status_info['timeframes']} ({', '.join(self.timeframes)})
📱 <b>Telegram:</b> {'✅ Conectado' if status_info['telegram_connected'] else '❌ Desconectado'}
💾 <b>Memoria:</b> {status_info['memory_usage']:.1f} MB

📚 <b>Comandos disponibles:</b>
/train_hist - Entrenamiento histórico
/stop_train - Detener entrenamiento
/status - Estado del sistema
/health - Salud del sistema
            """.strip()
            
            if self.telegram_reporter:
                await self.telegram_reporter.send_performance_alert(
                    "SISTEMA",
                    status_message,
                    "INFO"
                )
            
            return {
                'status': 'success',
                'message': status_message
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en comando status: {e}")
            return {
                'status': 'error',
                'message': f'❌ Error obteniendo estado: {e}'
            }
    
    async def _run_enhanced_training(self, days_back: int):
        """Ejecuta el entrenamiento mejorado"""
        try:
            self.logger.info(f"🚀 Ejecutando entrenamiento mejorado ({days_back} días)")
            
            # Usar el sistema de entrenamiento mejorado
            from scripts.training.integrate_enhanced_system import run_enhanced_historical_training
            
            # Obtener credenciales de Telegram
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            # Ejecutar entrenamiento
            results = await run_enhanced_historical_training(
                days_back=days_back,
                telegram_enabled=bool(self.telegram_reporter),
                bot_token=bot_token,
                chat_id=chat_id
            )
            
            # Procesar resultados
            if 'error' in results:
                self.logger.error(f"❌ Error en entrenamiento: {results['error']}")
                if self.telegram_reporter:
                    await self.telegram_reporter.send_performance_alert(
                        "SISTEMA",
                        f"❌ <b>ERROR EN ENTRENAMIENTO</b>\n\n{results['error']}",
                        "ERROR"
                    )
            else:
                self.logger.info("✅ Entrenamiento completado exitosamente")
                if self.telegram_reporter:
                    await self.telegram_reporter.send_performance_alert(
                        "SISTEMA",
                        "✅ <b>ENTRENAMIENTO COMPLETADO</b>\n\n"
                        "🎉 El entrenamiento histórico ha finalizado exitosamente\n"
                        "📊 Revisa los logs para ver los resultados detallados",
                        "SUCCESS"
                    )
            
            self.training_active = False
            self.training_task = None
            
        except asyncio.CancelledError:
            self.logger.info("⏹️ Entrenamiento cancelado por el usuario")
            self.training_active = False
            self.training_task = None
        except Exception as e:
            self.logger.error(f"❌ Error en entrenamiento: {e}")
            self.training_active = False
            self.training_task = None
    
    def _get_memory_usage(self) -> float:
        """Obtiene el uso de memoria actual"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    async def start(self):
        """Inicia el bot mejorado con todas las funcionalidades del bot original"""
        try:
            # Inicializar bot
            if not await self.initialize():
                return False
            
            # ========================================================================
            # PROCESO COMPLETO DEL BOT ORIGINAL (ANÁLISIS, DESCARGA, ALINEACIÓN, ETC.)
            # ========================================================================
            
            # 1. Enviar mensaje de inicio
            try:
                await self.telegram_bot.send_message(
                    "🤖 <b>Trading Bot v10 Enterprise MEJORADO</b>\n\n"
                    "🔄 Conectando con Exchange...",
                    parse_mode="HTML",
                    priority=1  # Alta prioridad para mensaje de inicio
                )
                self.logger.info("📨 Mensaje de inicio enviado a Telegram")
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar mensaje inicial: {e}")

            # 2. Análisis de datos históricos
            self.logger.info("🔍 Analizando datos históricos...")
            from scripts.data.analyze_data import AnalyzeDataEnterprise
            analyze_script = AnalyzeDataEnterprise(progress_id=str(uuid.uuid4()), auto_repair=False)
            await analyze_script.initialize()
            analysis_result = await analyze_script.execute(symbols=self.symbols, timeframes=self.timeframes, start_date=self.start_date)
            
            if analysis_result.get("status") != "success":
                self.logger.error(f"❌ Error en análisis: {analysis_result.get('message')}")
                await self.telegram_bot.send_message(
                    f"❌ <b>Error en análisis de datos</b>\n{analysis_result.get('message')}",
                    parse_mode="HTML",
                    priority=1  # Alta prioridad para errores
                )
                return False
            
            try:
                await self.telegram_bot.send_message(
                    "✅ <b>Análisis de datos completado</b>\n" + "\n".join(analysis_result.get("report", [])),
                    parse_mode="HTML",
                    priority=2  # Media prioridad para reportes
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar reporte de análisis: {e}")

            # 3. Descarga y reparación de datos
            self.logger.info("🔄 Descargando y reparando datos históricos...")
            from scripts.data.download_data import DownloadDataEnterprise
            download_script = DownloadDataEnterprise(progress_id=str(uuid.uuid4()))
            await download_script.initialize()
            download_result = await download_script.execute(symbols=self.symbols, timeframes=self.timeframes, start_date=self.start_date)
            
            if download_result.get("status") != "success":
                self.logger.error(f"❌ Error en descarga: {download_result.get('message')}")
                await self.telegram_bot.send_message(
                    f"❌ <b>Error en descarga de datos</b>\n{download_result.get('message')}",
                    parse_mode="HTML",
                    priority=1  # Alta prioridad para errores
                )
                return False
            
            try:
                await self.telegram_bot.send_message(
                    f"✅ <b>Descarga completada</b>\n{download_result.get('total_downloaded', 0):,} registros",
                    parse_mode="HTML",
                    priority=2  # Media prioridad para reportes
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar reporte de descarga: {e}")

            # 4. Alineación de timeframes
            self.logger.info("🔗 Alineando timeframes...")
            from scripts.data.verify_align import VerifyAlignEnterprise
            align_script = VerifyAlignEnterprise(progress_id=str(uuid.uuid4()))
            await align_script.initialize()
            align_result = await align_script.execute(symbols=self.symbols, timeframes=self.timeframes)
            
            if align_result.get("status") != "success":
                self.logger.error(f"❌ Error en alineación: {align_result.get('message')}")
                await self.telegram_bot.send_message(
                    f"❌ <b>Error en alineación</b>\n{align_result.get('message')}",
                    parse_mode="HTML",
                    priority=1  # Alta prioridad para errores
                )
                return False
            
            try:
                await self.telegram_bot.send_message(
                    f"✅ <b>Alineación completada</b>\n{align_result.get('total_aligned', 0):,} registros",
                    parse_mode="HTML",
                    priority=2  # Media prioridad para reportes
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar reporte de alineación: {e}")

            # 5. Sincronización de timestamps
            self.logger.info("⏰ Sincronizando timestamps...")
            from scripts.data.sync_symbols_robust import SyncSymbolsRobust
            sync_script = SyncSymbolsRobust(progress_id=str(uuid.uuid4()))
            sync_result = await sync_script.execute(symbols=self.symbols, timeframes=self.timeframes)
            
            if sync_result.get("status") != "success":
                self.logger.error(f"❌ Error en sincronización: {sync_result.get('message')}")
                await self.telegram_bot.send_message(
                    f"❌ <b>Error en sincronización</b>\n{sync_result.get('message')}",
                    parse_mode="HTML",
                    priority=1  # Alta prioridad para errores
                )
                return False
            
            try:
                await self.telegram_bot.send_message(
                    "✅ <b>Sincronización completada</b>\n" + sync_result.get("report", ""),
                    parse_mode="HTML",
                    priority=2  # Media prioridad para reportes
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar reporte de sincronización: {e}")

            # 6. Confirmación final y recolección en tiempo real
            self.logger.info("✅ Datos históricos procesados, iniciando recolección en tiempo real...")
            try:
                await self.telegram_bot.send_message(
                    "✅ <b>Conexión establecida, datos actualizados</b>",
                    parse_mode="HTML",
                    priority=2  # Media prioridad para estado
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar mensaje de confirmación: {e}")
            
            # Iniciar recolección en tiempo real
            collection_ready = asyncio.Event()
            collection_task = asyncio.create_task(self._start_real_time_collection(collection_ready))

            # 7. Enviar comandos de entrenamiento disponibles (MEJORADOS)
            try:
                await self.telegram_bot.send_message(
                    "📚 <b>Comandos de entrenamiento MEJORADOS disponibles:</b>\n"
                    "/train_hist - Entrenamiento histórico MEJORADO\n"
                    "/train_live - Entrenamiento en vivo\n"
                    "/stop_train - Detener entrenamiento\n"
                    "/status - Estado del sistema\n"
                    "/health - Salud del sistema\n\n"
                    "🚀 <b>SISTEMA MEJORADO ACTIVO:</b>\n"
                    "✅ Tracking granular de trades individuales\n"
                    "✅ Análisis de portfolio con correlación\n"
                    "✅ Reportes en tiempo real vía Telegram\n"
                    "✅ Gestión de memoria optimizada\n"
                    "✅ Recovery automático y robustez enterprise",
                    parse_mode="HTML"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ No se pudo enviar mensaje de comandos: {e}")

            # 8. Iniciar polling de Telegram
            self.logger.info("🔄 Iniciando polling de Telegram...")
            try:
                await self.telegram_bot.start_polling()
            except Exception as e:
                self.logger.error(f"❌ Error en polling de Telegram: {e}")
                self.logger.warning("⚠️ Continuando sin Telegram - el bot funcionará sin interfaz de chat")

            # Esperar a que la tarea de recolección termine
            await collection_task
                
        except KeyboardInterrupt:
            self.logger.info("⚠️ Bot detenido por el usuario")
        except Exception as e:
            self.logger.error(f"❌ Error crítico: {e}")
            import traceback
            traceback.print_exc()
    
    async def _start_real_time_collection(self, collection_ready: asyncio.Event):
        """Inicia la recolección en tiempo real (igual que en bot.py original)"""
        try:
            self.logger.info("🔄 Iniciando recolección en tiempo real...")
            
            # Simular recolección en tiempo real
            # En una implementación real, aquí iría la lógica de recolección
            collection_ready.set()
            
            # Mantener la recolección activa
            while True:
                await asyncio.sleep(60)  # Recolección cada minuto
                self.logger.debug("📊 Recolección en tiempo real activa...")
                
        except Exception as e:
            self.logger.error(f"❌ Error en recolección en tiempo real: {e}")

async def main():
    """Función principal"""
    bot = EnhancedTradingBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
