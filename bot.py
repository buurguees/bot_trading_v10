#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Trading v10 Enterprise - Punto de Entrada Principal
Automates data management (analysis, download/repair, alignment, synchronization) at startup.
Sends Telegram messages for progress and exposes only training commands.
"""

import asyncio
import sys
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

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
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Filtro para suprimir avisos legacy de archivos de configuración faltantes
class _SuppressLegacyConfigWarnings(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("⚠️ Archivo de configuración no encontrado:"):
            return False
        return True

# Aplicar filtro al root logger
_root_logger = logging.getLogger()
_root_logger.addFilter(_SuppressLegacyConfigWarnings())

# ============================================================================
# CONFIGURACIÓN WINDOWS - Solución para Error [Errno 22] Invalid argument
# ============================================================================
import os as _os
import sys as _sys
if _sys.platform == "win32":
    _os.environ['PYTHONIOENCODING'] = 'utf-8'
    _os.environ['TZ'] = 'UTC'
    try:
        import codecs as _codecs
        _sys.stdout = _codecs.getwriter('utf-8')(_sys.stdout.buffer, 'strict')
        _sys.stderr = _codecs.getwriter('utf-8')(_sys.stderr.buffer, 'strict')
    except Exception:
        pass

async def start_real_time_collection(collection_ready: asyncio.Event):
    """Inicia recolección de datos en tiempo real"""
    try:
        from core.data.collector import BitgetDataCollector
        collector = BitgetDataCollector()
        cfg = get_config_manager()
        symbols = cfg.get_symbols()
        timeframes = cfg.get_timeframes()
        await collector.start_real_time_collection(symbols, timeframes)
        collection_ready.set()
    except Exception as e:
        logger.error(f"❌ Error en recolección en tiempo real: {e}")
        collection_ready.set()  # Asegurar que el event se establece incluso en error

async def main():
    """Punto de entrada principal"""
    try:
        logger.info("🤖 Iniciando Bot Trading v10 Enterprise...")

        # 1. Inicializar configuración
        cfg = get_config_manager()
        symbols = cfg.get_symbols() or ['BTCUSDT']
        timeframes = cfg.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
        start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)

        # 2. Crear bot de Telegram
        from control.telegram_bot import TelegramBot
        collection_ready = asyncio.Event()
        telegram_bot = TelegramBot.from_env(collection_ready=collection_ready)
        try:
            await telegram_bot.send_message(
                "🤖 <b>Trading Bot v10 Enterprise</b>\n\n"
                "🔄 Conectando con Exchange...",
                parse_mode="HTML"
            )
            logger.info("📨 Mensaje de inicio enviado a Telegram")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar mensaje inicial: {e}")
            # Continuar sin el mensaje

        # 3. Análisis de datos históricos
        logger.info("🔍 Analizando datos históricos...")
        from scripts.data.analyze_data import AnalyzeDataEnterprise
        analyze_script = AnalyzeDataEnterprise(progress_id=str(uuid.uuid4()), auto_repair=False)
        await analyze_script.initialize()
        analysis_result = await analyze_script.execute(symbols=symbols, timeframes=timeframes, start_date=start_date)
        if analysis_result.get("status") != "success":
            logger.error(f"❌ Error en análisis: {analysis_result.get('message')}")
            await telegram_bot.send_message(
                f"❌ <b>Error en análisis de datos</b>\n{analysis_result.get('message')}",
                parse_mode="HTML"
            )
            return
        try:
            await telegram_bot.send_message(
                "✅ <b>Análisis de datos completado</b>\n" + "\n".join(analysis_result.get("report", [])),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar reporte de análisis: {e}")

        # 4. Descarga y reparación de datos
        logger.info("🔄 Descargando y reparando datos históricos...")
        from scripts.data.download_data import DownloadDataEnterprise
        download_script = DownloadDataEnterprise(progress_id=str(uuid.uuid4()))
        await download_script.initialize()
        download_result = await download_script.execute(symbols=symbols, timeframes=timeframes, start_date=start_date)
        if download_result.get("status") != "success":
            logger.error(f"❌ Error en descarga: {download_result.get('message')}")
            await telegram_bot.send_message(
                f"❌ <b>Error en descarga de datos</b>\n{download_result.get('message')}",
                parse_mode="HTML"
            )
            return
        try:
            await telegram_bot.send_message(
                f"✅ <b>Descarga completada</b>\n{download_result.get('total_downloaded', 0):,} registros",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar reporte de descarga: {e}")

        # 5. Alineación de timeframes
        logger.info("🔗 Alineando timeframes...")
        from scripts.data.verify_align import VerifyAlignEnterprise
        align_script = VerifyAlignEnterprise(progress_id=str(uuid.uuid4()))
        await align_script.initialize()
        align_result = await align_script.execute(symbols=symbols, timeframes=timeframes)
        if align_result.get("status") != "success":
            logger.error(f"❌ Error en alineación: {align_result.get('message')}")
            await telegram_bot.send_message(
                f"❌ <b>Error en alineación</b>\n{align_result.get('message')}",
                parse_mode="HTML"
            )
            return
        try:
            await telegram_bot.send_message(
                f"✅ <b>Alineación completada</b>\n{align_result.get('total_aligned', 0):,} registros",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar reporte de alineación: {e}")

        # 6. Sincronización de timestamps
        logger.info("⏰ Sincronizando timestamps...")
        from scripts.data.sync_symbols import SyncSymbolsEnterprise
        sync_script = SyncSymbolsEnterprise(progress_id=str(uuid.uuid4()))
        sync_result = await sync_script.execute(symbols=symbols, timeframes=timeframes)
        if sync_result.get("status") != "success":
            logger.error(f"❌ Error en sincronización: {sync_result.get('message')}")
            await telegram_bot.send_message(
                f"❌ <b>Error en sincronización</b>\n{sync_result.get('message')}",
                parse_mode="HTML"
            )
            return
        try:
            await telegram_bot.send_message(
                "✅ <b>Sincronización completada</b>\n" + sync_result.get("report", ""),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar reporte de sincronización: {e}")

        # 7. Confirmación final y recolección en tiempo real
        logger.info("✅ Datos históricos procesados, iniciando recolección en tiempo real...")
        try:
            await telegram_bot.send_message(
                "✅ <b>Conexión establecida, datos actualizados</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar mensaje de confirmación: {e}")
        collection_task = asyncio.create_task(start_real_time_collection(collection_ready))

        # 8. Enviar comandos de entrenamiento disponibles
        try:
            await telegram_bot.send_message(
                "📚 <b>Comandos de entrenamiento disponibles:</b>\n"
                "/train_hist - Entrenamiento histórico\n"
                "/train_live - Entrenamiento en vivo\n"
                "/stop_train - Detener entrenamiento\n"
                "/status - Estado del sistema\n"
                "/health - Salud del sistema",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar mensaje de comandos: {e}")

        # 9. Iniciar polling de Telegram
        logger.info("🔄 Iniciando polling de Telegram...")
        try:
            await telegram_bot.start_polling()
        except Exception as e:
            logger.error(f"❌ Error en polling de Telegram: {e}")
            logger.warning("⚠️ Continuando sin Telegram - el bot funcionará sin interfaz de chat")
            # Continuar sin Telegram si hay problemas de conexión

        # Esperar a que la tarea de recolección termine
        await collection_task

    except KeyboardInterrupt:
        logger.info("⚠️ Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())