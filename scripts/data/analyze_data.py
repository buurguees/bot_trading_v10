#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Analizar y reparar problemas de datos históricos
Objetivo: Detectar gaps, duplicados y valores inválidos. Reparación básica opcional.
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


async def _run(symbols: List[str] = None, auto_repair: bool = True) -> int:
    try:
        from core.data.history_analyzer import HistoryAnalyzer

        analyzer = HistoryAnalyzer()

        if symbols is None or len(symbols) == 0:
            symbols = analyzer.symbols

        logger.info(f"📊 Analizando datos históricos | Símbolos: {len(symbols)}")

        issues = await analyzer.detect_data_issues(symbols)
        total = issues.get('total_issues', 0) if isinstance(issues, dict) else None
        
        # Build report
        report_lines = []
        report_lines.append(f"📊 Análisis de datos | Símbolos: {len(symbols)}")
        report_lines.append(f"🔍 Problemas detectados totales: {total if total is not None else 'N/A'}")
        
        # Detalles por símbolo
        for sym in symbols:
            report_lines.append("─" * 60)
            report_lines.append(f"🎯 Símbolo: {sym}")
            
            # Obtener detalles específicos del símbolo
            try:
                symbol_issues = issues.get('symbols', {}).get(sym, {}) if isinstance(issues, dict) else {}
                gaps = symbol_issues.get('gaps', 0)
                duplicates = symbol_issues.get('duplicates', 0)
                invalid_ohlcv = symbol_issues.get('invalid_ohlcv', 0)
                
                if gaps > 0 or duplicates > 0 or invalid_ohlcv > 0:
                    report_lines.append(f"• Gaps detectados: {gaps}")
                    report_lines.append(f"• Duplicados: {duplicates}")
                    report_lines.append(f"• Valores inválidos: {invalid_ohlcv}")
                else:
                    report_lines.append("• ✅ Sin problemas detectados")
                    
            except Exception as e:
                report_lines.append(f"• ❌ Error analizando: {e}")

        # Mensaje de reparación separado
        if auto_repair:
            logger.info("🔧 Iniciando reparación básica (duplicados + gaps)")
            repair = await analyzer.repair_data_issues(symbols=symbols, repair_duplicates=True, fill_gaps=True)
            
            # Separar el mensaje de reparación
            report_lines.append("─" * 60)
            report_lines.append("🔧 RESULTADO DE REPARACIÓN")
            report_lines.append(
                f"✅ Reparación: exito={repair.get('successful_repairs', 0)} | "
                f"fallos={repair.get('failed_repairs', 0)} | total={repair.get('total_repairs', 0)}"
            )

        report_lines.append("─" * 60)
        report_lines.append("✅ Análisis completado")
        print("\n".join(report_lines))
        return 0

    except Exception as e:
        logger.error(f"❌ Error analizando datos: {e}")
        return 2


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Analizar y reparar datos históricos")
    parser.add_argument('--symbols', type=str, help='Lista de símbolos separados por coma (opcional)')
    parser.add_argument('--no-repair', action='store_true', help='Solo analizar, no reparar')
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(',')] if args.symbols else None
    auto_repair = not args.no_repair
    import asyncio
    return asyncio.run(_run(symbols=symbols, auto_repair=auto_repair))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


