#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Reparación completa de datos históricos
Objetivo: Corregir duplicados, gaps, descargas faltantes, re-alinear y guardar alineados.
"""

import sys
import logging
from typing import List
import argparse
from pathlib import Path

# Asegurar importaciones desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Configurar codificación UTF-8 para Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def _run(symbols: List[str] = None) -> int:
    try:
        from core.data.historical_data_manager import HistoricalDataManager, ensure_historical_data_coverage
        from core.data.history_analyzer import HistoryAnalyzer
        from core.data.collector import validate_and_align_downloaded_data
        from core.data.historical_data_adapter import get_historical_data
        from core.data.database import DatabaseManager

        manager = HistoricalDataManager()
        analyzer = HistoryAnalyzer()
        db = DatabaseManager()

        symbols = symbols or manager.config.get('symbols', [])
        timeframes = manager.config.get('timeframes', [])
        if not symbols or not timeframes:
            logger.error("❌ No hay símbolos/timeframes configurados")
            return 1

        logger.info(f"🔧 Reparación completa | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)}")
        report_lines = []
        report_lines.append(f"🔧 Reparación completa | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)}")

        # 1) Reparación de calidad básica (duplicados/gaps)
        repair = await analyzer.repair_data_issues(symbols=symbols, repair_duplicates=True, fill_gaps=True)
        report_lines.append(
            f"🧹 Limpieza: exito={repair.get('successful_repairs', 0)} | "
            f"fallos={repair.get('failed_repairs', 0)} | total={repair.get('total_repairs', 0)}"
        )

        # 2) Verificar cobertura y descargar faltantes según config
        cov = await ensure_historical_data_coverage()
        logger.info(f"📥 Cobertura: {cov.get('status', 'unknown')} - {cov.get('message', '')}")
        report_lines.append(f"📥 Cobertura: {cov.get('status', 'unknown')} - {cov.get('message', '')}")

        # 3) Re-alinear todo y guardar
        raw_data = {}
        for tf in timeframes:
            tf_data = {}
            for sym in symbols:
                try:
                    df = get_historical_data(symbol=sym, timeframe=tf, years=manager.config.get('years'))
                    tf_data[sym] = df if df is not None else None
                    if tf == timeframes[0]:
                        report_lines.append("─" * 60)
                        report_lines.append(f"🎯 Símbolo: {sym}")
                except Exception as e:
                    logger.error(f"❌ Error cargando {sym} {tf}: {e}")
                    tf_data[sym] = None
            raw_data[tf] = tf_data

        aligned = await validate_and_align_downloaded_data(raw_data)

        saved = 0
        for tf, sym_map in aligned.items():
            cleaned = {s: df for s, df in sym_map.items() if df is not None and hasattr(df, 'empty') and not df.empty}
            if not cleaned:
                continue
            ok = db.store_aligned_data(cleaned, tf, session_id=f"repair_full_{tf}")
            if ok:
                saved += 1
                report_lines.append(f"• {tf}: Alineación guardada")
            else:
                report_lines.append(f"• {tf}: Error guardando alineación")

        logger.info(f"✅ Reparación completa finalizada | TFs guardados: {saved}/{len(timeframes)}")
        report_lines.append(f"✅ Finalizado | TFs guardados: {saved}/{len(timeframes)}")
        print("\n".join(report_lines))
        return 0

    except Exception as e:
        logger.error(f"❌ Error en reparación completa: {e}")
        return 2


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Reparación completa de datos históricos")
    parser.add_argument('--symbols', type=str, help='Lista de símbolos separados por coma (opcional)')
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(',')] if args.symbols else None
    import asyncio
    return asyncio.run(_run(symbols=symbols))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


