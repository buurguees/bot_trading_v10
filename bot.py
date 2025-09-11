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

async def fill_missing_data_to_now():
    """Descarga datos faltantes desde el último timestamp hasta ahora."""
    try:
        from core.config.config_loader import ConfigLoader
        from core.data.database import db_manager
        from core.data.collector import BitgetDataCollector, download_extensive_historical_data
        from datetime import datetime, timezone
        import pandas as pd
        
        logger.info("🔄 Descargando datos faltantes hasta ahora...")
        
        # Cargar configuración unificada (fallback: main.data.real_time -> main.data_collection.real_time -> data.data_collection.real_time)
        config_loader = ConfigLoader()
        cfg_main = config_loader.get_main_config()
        cfg_data = config_loader.get_data_config()
        real_time_config = (
            cfg_main.get("data", {}).get("real_time")
            or cfg_main.get("data_collection", {}).get("real_time")
            or cfg_data.get("data_collection", {}).get("real_time", {})
        ) or {}
        symbols = real_time_config.get("symbols", [])
        timeframes = real_time_config.get("timeframes", ["1m"])

        if not symbols:
            logger.warning("⚠️ No hay símbolos configurados para descarga.")
            return

        collector = BitgetDataCollector()
        now = datetime.now(timezone.utc)
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    # Obtener último timestamp de la base de datos
                    last_timestamp = db_manager.get_last_timestamp(symbol, timeframe)
                    
                    if last_timestamp:
                        # Calcular tiempo faltante
                        last_dt = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
                        time_diff = now - last_dt
                        
                        # Solo descargar si faltan más de 5 minutos Y menos de 1 día (evitar descargas masivas)
                        if 300 < time_diff.total_seconds() < 86400:  # Entre 5 minutos y 1 día
                            logger.info(f"📥 Descargando datos faltantes para {symbol} ({timeframe}) desde {last_dt}")
                            
                            # Descargar datos faltantes
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
                                    db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
                                    from pathlib import Path
                                    Path(f"data/{symbol}").mkdir(parents=True, exist_ok=True)
                                    
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
        # Cargar configuración unificada (fallback: main.data.real_time -> main.data_collection.real_time -> data.data_collection.real_time)
        from core.config.config_loader import ConfigLoader
        from core.data.database import db_manager
        
        config_loader = ConfigLoader()
        cfg_main = config_loader.get_main_config()
        cfg_data = config_loader.get_data_config()
        real_time_config = (
            cfg_main.get("data", {}).get("real_time")
            or cfg_main.get("data_collection", {}).get("real_time")
            or cfg_data.get("data_collection", {}).get("real_time", {})
        ) or {}
        symbols = real_time_config.get("symbols", [])
        timeframes = real_time_config.get("timeframes", ["1m"])
        data_types = real_time_config.get("data_types", ["kline"])

        if not symbols or not real_time_config.get("enabled", False):
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
        
        # Crear bot de Telegram
        telegram_bot = TelegramBot()
        logger.info("✅ Bot de Telegram creado")
        
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
        
        # 3. Llenar datos faltantes hasta ahora
        logger.info("🔄 Llenando datos faltantes hasta ahora...")
        await fill_missing_data_to_now()
        
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