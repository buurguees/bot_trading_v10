#!/usr/bin/env python3
"""
diagnostic_data.py - Script de diagnóstico para problemas de datos históricos
Soluciona y diagnostica el error [Errno 22] Invalid argument en Windows
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import logging
from dotenv import load_dotenv

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar encoding para Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suprimir avisos legacy de config raíz; la configuración real está en config/core, features, environments
class _SuppressLegacyConfigWarnings(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("⚠️ Archivo de configuración no encontrado:"):
            return False
        return True

logging.getLogger().addFilter(_SuppressLegacyConfigWarnings())

# Cargar .env (para que las variables se reflejen en el test de CONFIG)
try:
    load_dotenv()
except Exception:
    pass


async def test_basic_connection():
    """Probar conexión básica con Bitget"""
    try:
        logger.info("🔍 Probando conexión básica con Bitget...")
        from core.data.collector import BitgetDataCollector
        collector = BitgetDataCollector()

        # Probar obtener hora del servidor
        server_time = await collector.get_server_time()
        logger.info(f"✅ Conexión exitosa. Hora del servidor: {server_time}")
        return True

    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False


async def test_simple_data_fetch():
    """Probar descarga simple de datos"""
    try:
        logger.info("🔍 Probando descarga simple de datos (BTCUSDT, 1h, 24h)...")
        from core.data.collector import BitgetDataCollector
        collector = BitgetDataCollector()

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)

        # Progreso dummy
        class P:
            downloaded_periods = 0
            total_records = 0
            errors = 0

        df = await collector.fetch_historical_data_chunk(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date=start_time,
            end_date=end_time,
            progress=P(),
        )

        if df is not None and not df.empty:
            logger.info(f"✅ Descarga exitosa: {len(df)} registros")
            logger.info(f"📊 Rango de fechas: {df.index.min()} - {df.index.max()}")
            return True
        else:
            logger.warning("⚠️ Descarga sin datos")
            return False

    except Exception as e:
        logger.error(f"❌ Error en descarga simple: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        return False


async def check_database_status():
    """Verificar estado de la base de datos"""
    try:
        logger.info("🔍 Verificando estado de la base de datos...")
        from core.data.database import db_manager

        total_records = db_manager.get_market_data_count_fast()
        logger.info(f"📊 Total de registros en BD: {total_records:,}")

        summary = db_manager.get_data_summary_optimized()
        symbols = [s['symbol'] for s in summary.get('symbols', [])]
        logger.info(f"💰 Símbolos disponibles: {symbols}")

        return True

    except Exception as e:
        logger.error(f"❌ Error de base de datos: {e}")
        return False


async def check_configuration():
    """Verificar configuración del sistema"""
    try:
        logger.info("🔍 Verificando configuración...")

        required_vars = ['BITGET_API_KEY', 'BITGET_SECRET_KEY', 'BITGET_PASSPHRASE']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.warning(f"⚠️ Variables faltantes: {missing_vars}")
        else:
            logger.info("✅ Variables de entorno configuradas")

        # Verificar archivo .env
        for file_path in ['.env']:
            if Path(file_path).exists():
                logger.info(f"✅ Encontrado: {file_path}")
            else:
                logger.warning(f"⚠️ Faltante: {file_path}")

        return len(missing_vars) == 0

    except Exception as e:
        logger.error(f"❌ Error verificando configuración: {e}")
        return False


async def main():
    """Función principal de diagnóstico"""
    logger.info("🚀 Iniciando diagnóstico del sistema...")

    results = {}

    logger.info("\n" + "="*50)
    logger.info("TEST 1: CONFIGURACIÓN")
    logger.info("="*50)
    results['config'] = await check_configuration()

    logger.info("\n" + "="*50)
    logger.info("TEST 2: BASE DE DATOS")
    logger.info("="*50)
    results['database'] = await check_database_status()

    logger.info("\n" + "="*50)
    logger.info("TEST 3: CONEXIÓN")
    logger.info("="*50)
    results['connection'] = await test_basic_connection()

    if results['connection']:
        logger.info("\n" + "="*50)
        logger.info("TEST 4: DESCARGA SIMPLE")
        logger.info("="*50)
        results['download'] = await test_simple_data_fetch()
    else:
        results['download'] = False

    logger.info("\n" + "="*50)
    logger.info("RESUMEN DE DIAGNÓSTICO")
    logger.info("="*50)
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test.upper()}: {status}")

    if all(results.values()):
        logger.info("\n🎉 Todos los tests pasaron. El sistema debería funcionar correctamente.")
    else:
        logger.info("\n⚠️ Se detectaron problemas. Revisa los errores anteriores.")


if __name__ == "__main__":
    asyncio.run(main())


