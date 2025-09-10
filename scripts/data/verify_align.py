#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Verificar y aplicar alineamiento temporal por símbolo/TF
Objetivo: Validar alineación; si falta o es pobre, alinear y guardar en base de datos.
"""

import sys
import logging
from typing import List, Dict, Any
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


async def _run(symbols: List[str] = None, timeframes: List[str] = None) -> int:
    try:
        from core.data.historical_data_manager import HistoricalDataManager
        from core.data.temporal_alignment import TemporalAlignment
        from core.data.database import DatabaseManager
        from core.data.historical_data_adapter import get_historical_data
        from datetime import datetime, timedelta

        manager = HistoricalDataManager()
        db = DatabaseManager()
        aligner = TemporalAlignment()

        symbols = symbols or manager.config.get('symbols', [])
        timeframes = timeframes or manager.config.get('timeframes', [])

        if not symbols or not timeframes:
            logger.error("❌ No hay símbolos/timeframes configurados")
            return 1

        logger.info(f"🔄 Verificando alineación | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)}")
        report_lines: List[str] = []
        report_lines.append(f"🔄 Verificar/Alinear | Símbolos: {len(symbols)} | TFs: {', '.join(timeframes)}")
        
        # Procesar TODOS los símbolos configurados en user_settings.yaml
        logger.info(f"📋 Símbolos configurados: {symbols}")
        logger.info(f"📋 Timeframes configurados: {timeframes}")

        # Procesar cada símbolo individualmente
        for idx, symbol in enumerate(symbols, 1):
            logger.info(f"🔄 Procesando símbolo {idx}/{len(symbols)}: {symbol}")
            report_lines.append("─" * 60)
            report_lines.append(f"🎯 Símbolo: {symbol}")
            
            try:
                # Cargar datos históricos para el símbolo
                symbol_data = {}
                years = manager.config.get('years', 1)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=years * 365)
                
                for tf in timeframes:
                    try:
                        df = get_historical_data(symbol=symbol, timeframe=tf, start_date=start_date, end_date=end_date)
                        if df is not None and not df.empty:
                            symbol_data[tf] = df
                    except Exception as e:
                        logger.error(f"❌ Error cargando {symbol} {tf}: {e}")
                
                if not symbol_data:
                    report_lines.append(f"• ❌ Sin datos para alinear")
                    continue
                
                # Verificar si ya hay datos alineados en la base de datos
                has_aligned_data = False
                try:
                    # Verificar si existe alineación para este símbolo
                    for tf in timeframes:
                        aligned_probe = db.get_aligned_data([symbol], tf, start_date, end_date)
                        if aligned_probe and symbol in aligned_probe and not aligned_probe[symbol].empty:
                            has_aligned_data = True
                            break
                except Exception:
                    has_aligned_data = False
                
                if has_aligned_data:
                    # Ya hay datos alineados, mostrar métricas
                    report_lines.append("• ✅ Datos ya alineados en base de datos")
                    
                    # Calcular métricas de los datos existentes
                    total_records = 0
                    start_dt = None
                    end_dt = None
                    
                    for tf in timeframes:
                        try:
                            aligned_probe = db.get_aligned_data([symbol], tf, start_date, end_date)
                            if aligned_probe and symbol in aligned_probe and not aligned_probe[symbol].empty:
                                df = aligned_probe[symbol]
                                total_records += len(df)
                                if start_dt is None:
                                    start_dt = df.index.min()
                                    end_dt = df.index.max()
                                else:
                                    start_dt = min(start_dt, df.index.min())
                                    end_dt = max(end_dt, df.index.max())
                        except Exception:
                            continue
                    
                    if start_dt and end_dt:
                        report_lines.append(f"• Inicio: {start_dt}")
                        report_lines.append(f"• Fin: {end_dt}")
                        report_lines.append(f"• Timeframes: {len(timeframes)}")
                        report_lines.append(f"• Registros: {total_records:,}")
                else:
                    # Necesita alineación
                    report_lines.append("• 🔄 Alineando datos...")
                    
                    # Crear timeline maestro para el timeframe más pequeño
                    base_timeframe = timeframes[0]  # Usar el primer timeframe como base
                    base_data = symbol_data.get(base_timeframe)
                    
                    if base_data is None:
                        report_lines.append(f"• ❌ Sin datos base para alinear ({base_timeframe})")
                        continue
                    
                    if not hasattr(base_data, 'empty') or base_data.empty:
                        report_lines.append(f"• ❌ Datos base vacíos para alinear ({base_timeframe})")
                        continue
                    
                    # Crear timeline maestro
                    try:
                        master_timeline = aligner.create_master_timeline(
                            timeframe=base_timeframe,
                            start_date=base_data.index.min(),
                            end_date=base_data.index.max()
                        )
                    except Exception as e:
                        logger.error(f"❌ Error creando timeline maestro: {e}")
                        report_lines.append(f"• ❌ Error creando timeline maestro: {e}")
                        continue
                    
                    # Alinear datos por timeframe
                    aligned_data = {}
                    for tf in timeframes:
                        if tf in symbol_data:
                            df_tf = symbol_data[tf]
                            if df_tf is not None and hasattr(df_tf, 'empty') and not df_tf.empty:
                                try:
                                    result = aligner.align_symbol_data(
                                        {symbol: df_tf}, 
                                        master_timeline, 
                                        tf
                                    )
                                    logger.info(f"🔍 Resultado alineación {symbol} {tf}: {type(result)} - {len(result) if result else 0} elementos")
                                    if result and symbol in result:
                                        aligned_df = result[symbol]
                                        logger.info(f"🔍 DataFrame alineado {symbol} {tf}: {aligned_df.shape} - Columnas: {list(aligned_df.columns)}")
                                        aligned_data[tf] = aligned_df
                                    else:
                                        logger.warning(f"⚠️ No se pudo alinear {symbol} {tf}: result={result}, symbol_in_result={symbol in result if result else False}")
                                except Exception as e:
                                    logger.error(f"❌ Error alineando {symbol} {tf}: {e}")
                                    continue
                    
                    # Guardar datos alineados en SQLite por timeframe
                    saved_timeframes = 0
                    total_records = 0
                    start_dt = None
                    end_dt = None
                    
                    for tf, df in aligned_data.items():
                        if df is not None and not df.empty:
                            try:
                                # Verificar que el DataFrame tiene las columnas necesarias
                                required_columns = ['open', 'high', 'low', 'close', 'volume']
                                missing_columns = [col for col in required_columns if col not in df.columns]
                                
                                if missing_columns:
                                    logger.error(f"❌ DataFrame de {symbol} {tf} le faltan columnas: {missing_columns}")
                                    report_lines.append(f"• ❌ {tf}: Faltan columnas {missing_columns}")
                                    continue
                                
                                # Guardar en SQLite usando la función del sistema
                                success = db.store_aligned_data({symbol: df}, tf, f"verify_align_{symbol}_{tf}")
                                if success:
                                    saved_timeframes += 1
                                    total_records += len(df)
                                    if start_dt is None:
                                        start_dt = df.index.min()
                                        end_dt = df.index.max()
                                    else:
                                        start_dt = min(start_dt, df.index.min())
                                        end_dt = max(end_dt, df.index.max())
                                    logger.info(f"✅ Guardado exitoso: {symbol} {tf} - {len(df)} registros")
                                else:
                                    logger.error(f"❌ Fallo guardando: {symbol} {tf}")
                                    report_lines.append(f"• ❌ {tf}: Error guardando en SQLite")
                            except Exception as e:
                                logger.error(f"❌ Error procesando {symbol} {tf}: {e}")
                                report_lines.append(f"• ❌ {tf}: Error - {e}")
                    
                    if saved_timeframes > 0:
                        report_lines.append("• ✅ Alineación completada y guardada en SQLite")
                        report_lines.append(f"• Inicio: {start_dt}")
                        report_lines.append(f"• Fin: {end_dt}")
                        report_lines.append(f"• Timeframes guardados: {saved_timeframes}/{len(timeframes)}")
                        report_lines.append(f"• Registros: {total_records:,}")
                    else:
                        report_lines.append("• ❌ Error guardando datos alineados en SQLite")
                        
            except Exception as e:
                logger.error(f"❌ Error procesando {symbol}: {e}")
                report_lines.append(f"• ❌ Error: {e}")

        report_lines.append("─" * 60)
        report_lines.append("✅ Verificación/alineación completada")
        print("\n".join(report_lines))
        return 0

    except Exception as e:
        logger.error(f"❌ Error verificando/alineando: {e}")
        return 2


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Verificar y aplicar alineamiento temporal")
    parser.add_argument('--symbols', type=str, help='Lista de símbolos separados por coma (opcional)')
    parser.add_argument('--timeframes', type=str, help='Lista de timeframes separados por coma (opcional)')
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(',')] if args.symbols else None
    timeframes = [t.strip() for t in args.timeframes.split(',')] if args.timeframes else None

    import asyncio
    return asyncio.run(_run(symbols=symbols, timeframes=timeframes))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


