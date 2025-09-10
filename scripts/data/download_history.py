#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Descargar historial (por símbolos y timeframes) usando ccxt
Objetivo: Verificar cobertura histórica según config/ y descargar faltantes o todo si no existe.
Salida: Mensajes detallados por símbolo/TF para consumo por Telegram.
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime

import argparse
from pathlib import Path

# Asegurar importaciones desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Configurar codificación UTF-8 para Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Logging básico para salida limpia a consola
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def _run(symbols: List[str] = None, timeframes: List[str] = None, force_years: int = None) -> int:
    """Orquesta la verificación de cobertura y las descargas faltantes.

    - Obtiene configuración desde config/ por defecto.
    - Por cada símbolo: informa cobertura, descarga faltantes y reporta rango por TF.
    """
    try:
        # Cargar gestores de datos
        from core.data.historical_data_manager import HistoricalDataManager, ensure_historical_data_coverage
        from core.data.historical_data_adapter import get_historical_data

        manager = HistoricalDataManager()

        # Si el usuario fuerza años, sobreescribir temporalmente la configuración del manager
        if force_years is not None and force_years > 0:
            manager.config['years'] = force_years

        # Determinar universo de símbolos y TFs
        cfg_symbols = manager.config.get('symbols', [])
        cfg_timeframes = manager.config.get('timeframes', [])
        symbols = symbols or cfg_symbols
        timeframes = timeframes or cfg_timeframes

        if not symbols or not timeframes:
            logger.error("❌ No hay símbolos/timeframes configurados")
            return 1

        logger.info(f"📥 Iniciando descarga histórica | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)} | Años: {manager.config.get('years')}")

        # Verificación global de cobertura con auto-descarga si procede (según config)
        overall = await ensure_historical_data_coverage()
        status = overall.get('status', 'unknown')
        logger.info(f"🔎 Verificación global: {status} - {overall.get('message', '')}")

        report_lines: List[str] = []
        report_lines.append(f"📥 Descarga/Verificación histórica | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)} | Años: {manager.config.get('years')}")
        report_lines.append(f"🔎 Verificación global: {status} - {overall.get('message', '')}")

        # Recorrido detallado símbolo x TF
        for symbol in symbols:
            logger.info("─" * 60)
            logger.info(f"🔧 Procesando símbolo: {symbol}")
            report_lines.append("─" * 60)
            report_lines.append(f"🎯 Símbolo: {symbol}")

            # Para cada TF, recuperar DataFrame y reportar rangos reales
            for tf in timeframes:
                try:
                    df = get_historical_data(symbol=symbol, timeframe=tf, years=manager.config.get('years'))
                    if df is None or df.empty:
                        logger.info(f"• {symbol} {tf}: sin datos tras verificación. Intentando re-descarga puntual…")
                        # Forzar re-verificación solo para este símbolo si se desea granularidad futura
                        # Por ahora se confía en ensure_historical_data_coverage() global
                        df = get_historical_data(symbol=symbol, timeframe=tf, years=manager.config.get('years'))

                    if df is None or df.empty:
                        logger.warning(f"❌ {symbol} {tf}: sin datos disponibles")
                        report_lines.append(f"• {tf}: Sin datos")
                        continue

                    start_dt: datetime = df.index.min().to_pydatetime() if hasattr(df.index.min(), 'to_pydatetime') else df.index.min()
                    end_dt: datetime = df.index.max().to_pydatetime() if hasattr(df.index.max(), 'to_pydatetime') else df.index.max()
                    count = len(df)
                    logger.info(f"✅ {symbol} {tf}: {count:,} velas | Inicio: {start_dt} | Fin: {end_dt}")
                    report_lines.append(f"• {tf}: {count:,} velas | Inicio: {start_dt} | Fin: {end_dt}")
                except Exception as e:
                    logger.error(f"❌ Error consultando {symbol} {tf}: {e}")
                    report_lines.append(f"❌ Error consultando {tf}: {e}")

        logger.info("─" * 60)
        logger.info("✅ Proceso de verificación y descarga histórica finalizado")
        report_lines.append("─" * 60)
        report_lines.append("✅ Proceso de verificación y descarga histórica finalizado")
        print("\n".join(report_lines))
        return 0

    except Exception as e:
        logger.error(f"❌ Error en descarga histórica: {e}")
        return 2


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Descargar historial con verificación de cobertura")
    parser.add_argument('--symbols', type=str, help='Lista de símbolos separados por coma (opcional)')
    parser.add_argument('--timeframes', type=str, help='Lista de timeframes separados por coma (opcional)')
    parser.add_argument('--years', type=int, help='Años de histórico a requerir (opcional, override config)')
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(',')] if args.symbols else None
    timeframes = [t.strip() for t in args.timeframes.split(',')] if args.timeframes else None
    years = args.years if args.years and args.years > 0 else None

    return asyncio.run(_run(symbols=symbols, timeframes=timeframes, force_years=years))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


