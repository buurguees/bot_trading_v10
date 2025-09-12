#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Trading v10 Enterprise - Punto de Entrada Principal
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging
import logging
from core.config.unified_config import unified_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# ============================================================================
# FUNCIONES DE DESCARGA SEGURA/DIAGNÓSTICO
# ============================================================================
async def fill_missing_data_to_now_debug():
    """Versión de diagnóstico que saltea descarga automática"""
    logger.info("🔧 Modo diagnóstico: descarga automática desactivada")
    logger.info("Usa /safe_download para descarga segura manual")
    return

async def fill_missing_data_to_now_safe():
    """Versión segura con manejo de errores y límites"""
    try:
        logger.info("🔄 Iniciando descarga segura de datos faltantes...")
        from core.data.collector import BitgetDataCollector
        from datetime import datetime, timedelta, timezone
        collector = BitgetDataCollector()
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        # Símbolos/timeframes reducidos para evitar 429
        from config.unified_config import get_config_manager
        cfg = get_config_manager()
        symbols = (cfg.get_symbols() or ['BTCUSDT'])[:2]
        timeframes = ['1h', '4h']
        class P:
            downloaded_periods = 0
            total_records = 0
            errors = 0
        for sym in symbols:
            for tf in timeframes:
                try:
                    df = await collector.fetch_historical_data_chunk(sym, tf, start_time, end_time, P())
                    if df is not None and not df.empty:
                        from core.data.collector import data_collector
                        saved = await data_collector.save_historical_data(df)
                        logger.info(f"✅ {sym}-{tf}: {saved} registros guardados")
                    await asyncio.sleep(1.0)
                except Exception as e:
                    logger.warning(f"⚠️ Error en descarga segura {sym}-{tf}: {e}")
        logger.info("✅ Descarga segura completada")
    except Exception as e:
        logger.error(f"❌ Error en descarga segura: {e}")
        await fill_missing_data_to_now_debug()

async def fill_missing_data_to_now():
    """Descarga datos faltantes desde el último timestamp hasta ahora."""
    try:
        from config.unified_config import get_config_manager
        from core.data.database import db_manager
        from core.data.collector import BitgetDataCollector, download_extensive_historical_data
        from datetime import datetime, timezone, timedelta
        from core.utils.timestamp_utils import TimestampManager as TS
        import pandas as pd
        
        logger.info("🔄 Descargando datos faltantes hasta ahora...")
        
        # Configuración unificada v2
        cfg = get_config_manager()
        symbols = cfg.get_symbols()
        timeframes = cfg.get_timeframes() or ["1m"]

        if not symbols:
            logger.warning("⚠️ No hay símbolos configurados para descarga.")
            return

        collector = BitgetDataCollector()
        now = datetime.now(timezone.utc)
        
        # Mapa de duración de vela en segundos para filtrar ventanas muy pequeñas
        tf_seconds = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '2h': 7200, '4h': 14400, '6h': 21600,
            '8h': 28800, '12h': 43200, '1d': 86400
        }

        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    # Obtener último timestamp de la base de datos
                    last_timestamp = db_manager.get_last_timestamp(symbol, timeframe)
                    
                    if last_timestamp:
                        # Calcular tiempo faltante
                        # Asegurar conversión segura a UTC y evitar since >= until
                        last_dt = datetime.fromtimestamp(int(last_timestamp), tz=timezone.utc)
                        if last_dt >= now:
                            last_dt = now - timedelta(minutes=5)
                        time_diff = now - last_dt
                        
                        # Ventana mínima: al menos 2 velas del timeframe y <= 1 día
                        min_window = tf_seconds.get(timeframe, 300) * 2
                        if min_window < time_diff.total_seconds() < 86400:
                            logger.info(f"📥 Descargando datos faltantes para {symbol} ({timeframe}) desde {last_dt}")
                            
                            # Descargar datos faltantes
                            # Usar rango con normalización a ms dentro del collector
                            missing_data = await download_extensive_historical_data(
                                symbols=[symbol],
                                timeframes=[timeframe],
                                start_date=last_dt,
                                end_date=now
                            )
                            
                            if missing_data and missing_data.get('data') is not None:
                                # Extraer DataFrame del diccionario anidado
                                symbol_data = missing_data['data'].get(symbol, {})
                                timeframe_data = symbol_data.get(timeframe, pd.DataFrame())
                                
                                if not timeframe_data.empty:
                                    # Guardar datos faltantes
                                    # Path configurable desde config
                                    data_dir = cfg.get('data_sources.storage_dir', 'data')
                                    db_path = f"{data_dir}/{symbol}/{symbol}_{timeframe}.db"
                                    from pathlib import Path
                                    Path(f"{data_dir}/{symbol}").mkdir(parents=True, exist_ok=True)
                                    
                                    success = db_manager.store_historical_data(
                                        timeframe_data, 
                                        symbol, 
                                        timeframe, 
                                        db_path
                                    )
                                else:
                                    success = False
                                
                                if success:
                                    logger.info(f"✅ Datos faltantes guardados para {symbol} ({timeframe})")
                                else:
                                    logger.warning(f"⚠️ Error guardando datos faltantes para {symbol} ({timeframe})")
                            else:
                                logger.warning(f"⚠️ No se obtuvieron datos faltantes para {symbol} ({timeframe})")
                        elif time_diff.total_seconds() <= 300:
                            logger.debug(f"✅ {symbol} ({timeframe}) ya está actualizado (última actualización: {time_diff})")
                        else:
                            logger.warning(f"⚠️ {symbol} ({timeframe}) tiene más de 1 día de datos faltantes, saltando descarga automática")
                    else:
                        logger.info(f"📥 No hay datos previos para {symbol} ({timeframe}), se descargarán en la verificación histórica")
                        
                except Exception as e:
                    logger.error(f"❌ Error descargando datos faltantes para {symbol} ({timeframe}): {e}")
                    continue
        
        logger.info("✅ Descarga de datos faltantes completada")
        
    except Exception as e:
        logger.error(f"❌ Error en descarga de datos faltantes: {e}")
        raise

async def start_real_time_collection():
    """Inicia la recolección de datos en tiempo real para todos los símbolos."""
    try:
        # Cargar configuración unificada v2
        from config.unified_config import get_config_manager
        from core.data.database import db_manager
        cfg = get_config_manager()
        symbols = cfg.get_symbols()
        timeframes = cfg.get_timeframes() or ["1m"]
        rt_enabled = cfg.get("data_sources.real_time.enabled", True)
        data_types = cfg.get("data_sources.real_time.data_types", ["kline"]) or ["kline"]

        if not symbols or not rt_enabled:
            logger.warning("⚠️ Recolección en tiempo real deshabilitada o sin símbolos configurados.")
            return

        # Inicializar el recolector
        from core.data.collector import BitgetDataCollector
        collector = BitgetDataCollector()
        
        # Usar el nuevo método de recolección
        await collector.start_real_time_collection(
            symbols=symbols,
            timeframes=timeframes,
            data_types=data_types,
            interval_seconds=60
        )

    except Exception as e:
        logger.error(f"❌ Error en la recolección en tiempo real: {e}")
        raise

async def main():
    """Función principal del Trading Bot v10 Enterprise"""
    logger.info("🚀 Bot Trading v10 Enterprise iniciado")
    
    try:
        # 1. Verificar y asegurar datos históricos
        logger.info("📊 Verificando cobertura de datos históricos...")
        from core.data.historical_data_manager import ensure_historical_data_coverage
        
        data_verification = await ensure_historical_data_coverage()
        
        if data_verification.get('status') == 'error':
            logger.error("❌ Error crítico en verificación de datos históricos")
            logger.error(f"Detalles: {data_verification.get('message', 'Error desconocido')}")
            return
        
        elif data_verification.get('status') in ['complete', 'completed']:
            logger.info("✅ Datos históricos verificados correctamente")
            if data_verification.get('status') == 'completed':
                download_results = data_verification.get('download_results', {})
                total_downloaded = download_results.get('total_downloaded', 0)
                logger.info(f"📥 Descargados {total_downloaded:,} registros históricos")
        else:
            logger.warning("⚠️ Problemas detectados en cobertura de datos históricos")
            logger.warning(f"Estado: {data_verification.get('status')}")
        
        # 2. Importar y inicializar Telegram Bot
        logger.info("🤖 Inicializando bot de Telegram...")
        from control.telegram_bot import TelegramBot
        
        logger.info("✅ Módulos importados correctamente")
        
        # Crear bot de Telegram con configuración real
        try:
            telegram_bot = TelegramBot.from_env()
            logger.info("✅ Bot de Telegram creado")
        except Exception as e:
            logger.error(f"❌ Error creando bot de Telegram: {e}")
            return
        
        # Enviar mensaje de inicio
        try:
            startup_message = (
                "🤖 <b>Trading Bot v10 Enterprise</b>\n\n"
                "✅ <b>Bot Iniciado</b>\n"
                "🔄 Conectando con Exchange..."
            )
            await telegram_bot.send_message(startup_message, parse_mode="HTML")
            logger.info("📨 Mensaje de inicio enviado a Telegram")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")
        
        # 3. Llenar datos faltantes hasta ahora (MODO SEGURO)
        logger.info("🔄 Llenando datos faltantes hasta ahora (modo seguro)...")
        try:
            await fill_missing_data_to_now_safe()
        except Exception as e:
            logger.error(f"❌ Error en descarga segura, activando modo diagnóstico: {e}")
            await fill_missing_data_to_now_debug()
        
        # 4. Iniciar recolección en tiempo real en una tarea separada
        logger.info("🔄 Iniciando recolección de datos en tiempo real...")
        collection_task = asyncio.create_task(start_real_time_collection())
        
        # 5. Enviar mensaje de comandos después de que todo esté listo
        try:
            await asyncio.sleep(2)  # Esperar un poco para que la recolección se inicie
            commands_message = (
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
            await telegram_bot.send_message(commands_message, parse_mode="HTML")
            logger.info("📨 Mensaje de comandos enviado a Telegram")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo enviar mensaje de comandos: {e}")
        
        # 6. Iniciar polling de Telegram
        logger.info("🔄 Iniciando polling de Telegram...")
        await telegram_bot.start_polling()
        
        # Esperar a que la tarea de recolección termine (no debería terminar)
        await collection_task
        
    except KeyboardInterrupt:
        logger.info("⚠️ Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())