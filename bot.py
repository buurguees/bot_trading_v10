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
from config.unified_config import get_config_manager

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
    """Versión segura con manejo de errores y límites - solo descarga datos faltantes"""
    try:
        logger.info("🔄 Iniciando descarga segura de datos faltantes...")
        from core.data.collector import BitgetDataCollector
        from core.data.database import db_manager
        from datetime import datetime, timedelta, timezone
        import asyncio
        
        collector = BitgetDataCollector()
        
        # Cargar configuración completa
        from config.unified_config import get_config_manager
        cfg = get_config_manager()
        symbols = cfg.get_symbols() or ['BTCUSDT']  # Ya usa UnifiedConfigManager
        timeframes = cfg.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
        
        logger.info(f"📊 Procesando {len(symbols)} símbolos: {symbols}")
        logger.info(f"📊 Procesando {len(timeframes)} timeframes: {timeframes}")
        
        total_records = 0
        errors = 0
        
        for sym in symbols:
            for tf in timeframes:
                try:
                    # Verificar último timestamp en la base de datos
                    db_path = f"data/{sym}/trading_bot.db"
                    last_timestamp = db_manager.get_last_timestamp(sym, tf, db_path)
                    
                    if last_timestamp:
                        # Convertir a datetime UTC
                        last_dt = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
                        now = datetime.now(timezone.utc)
                        
                        # Solo descargar si han pasado más de 2 minutos desde el último dato
                        time_diff = now - last_dt
                        if time_diff.total_seconds() < 120:  # 2 minutos
                            logger.info(f"✅ {sym}-{tf}: Datos recientes (último: {last_dt.strftime('%H:%M:%S')}), saltando descarga")
                            continue
                        
                        # Descargar desde el último timestamp + 1 minuto
                        start_time = last_dt + timedelta(minutes=1)
                        end_time = now
                        logger.info(f"📥 {sym}-{tf}: Descargando desde {start_time.strftime('%H:%M:%S')} hasta {end_time.strftime('%H:%M:%S')}")
                    else:
                        # No hay datos, descargar últimos 5 minutos
                        end_time = datetime.now(timezone.utc)
                        start_time = end_time - timedelta(minutes=5)
                        logger.info(f"📥 {sym}-{tf}: Sin datos previos, descargando últimos 5 minutos")
                    
                    class P:
                        def __init__(self):
                            self.downloaded_periods = 0
                            self.total_records = 0
                            self.errors = 0
                    
                    df = collector.fetch_historical_data_chunk(sym, tf, start_time, end_time, P())
                    if df is not None and not df.empty:
                        # Guardar en base de datos
                        saved = db_manager.store_historical_data(df, sym, tf, db_path)
                        if saved:
                            logger.info(f"✅ {sym}-{tf}: {len(df)} registros guardados")
                            total_records += len(df)
                        else:
                            logger.warning(f"⚠️ Error guardando {sym}-{tf}")
                            errors += 1
                    else:
                        logger.info(f"ℹ️ {sym}-{tf}: No hay datos nuevos para descargar")
                    
                    await asyncio.sleep(0.5)  # Pausa más corta
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error en descarga segura {sym}-{tf}: {e}")
                    errors += 1
        
        logger.info(f"✅ Descarga segura completada: {total_records} registros, {errors} errores")
        
    except Exception as e:
        logger.error(f"❌ Error en descarga segura: {e}")
        await fill_missing_data_to_now_debug()
    finally:
        # Cerrar sesión aiohttp
        if 'collector' in locals() and collector:
            await collector.close()

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
                            
                            if missing_data and missing_data.get('data'):
                                # Guardar datos descargados
                                saved = await db_manager.store_aligned_data(missing_data['data'], timeframe, "fill_missing")
                                if saved:
                                    logger.info(f"✅ {symbol}-{timeframe}: Guardados {len(missing_data['data'])} registros faltantes")
                                else:
                                    logger.warning(f"⚠️ Error guardando datos faltantes para {symbol}-{timeframe}")
                    else:
                        logger.warning(f"⚠️ No hay datos previos para {symbol} ({timeframe}), considera descarga completa")
                except Exception as e:
                    logger.error(f"❌ Error descargando datos faltantes para {symbol} ({timeframe}): {e}")
        logger.info("✅ Descarga de datos faltantes completada")
    except Exception as e:
        logger.error(f"❌ Error general en descarga de datos faltantes: {e}")
        raise

async def start_real_time_collection(collection_ready: asyncio.Event):
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
        
        # Usar WebSocket para recolección en tiempo real (más eficiente)
        try:
            await collector.start_websocket_collection(
                symbols=symbols,
                timeframes=timeframes,
                collection_ready=collection_ready
            )
        except Exception as e:
            logger.warning(f"⚠️ WebSocket falló, usando polling: {e}")
            # Fallback a polling si WebSocket falla
            await collector.start_real_time_collection(
                symbols=symbols,
                timeframes=timeframes,
                data_types=data_types,
                interval_seconds=60,
                collection_ready=collection_ready
            )

        # Signal listo después de inicio
        collection_ready.set()
        
        # Mantener la recolección activa indefinidamente
        try:
            while True:
                await asyncio.sleep(60)  # Verificar cada minuto
        except asyncio.CancelledError:
            logger.info("🔄 Recolección en tiempo real cancelada")
        finally:
            # Cerrar sesión aiohttp al finalizar
            if 'collector' in locals() and collector:
                await collector.close()
                logger.info("✅ Collector cerrado correctamente")
                
    except Exception as e:
        logger.error(f"❌ Error en la recolección en tiempo real: {e}")
        # Cerrar collector en caso de error
        if 'collector' in locals() and collector:
            await collector.close()
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
        
        # Crear event para collector listo
        collection_ready = asyncio.Event()
        
        # Crear bot de Telegram con event
        try:
            telegram_bot = TelegramBot.from_env(collection_ready=collection_ready)
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
        collection_task = asyncio.create_task(start_real_time_collection(collection_ready))
        
        # 5. Iniciar polling de Telegram (handlers esperará event internamente)
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