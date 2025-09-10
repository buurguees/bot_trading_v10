#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /download_data
Descarga datos históricos, los alinea y los guarda
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data.collector import BitgetDataCollector
from core.data.database import db_manager
from core.data.temporal_alignment import TemporalAlignment
from config.config_loader import ConfigLoader
import pandas as pd

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloadDataScript:
    """Script para descarga y alineación de datos"""
    
    def __init__(self):
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.collector = None
        self.aligner = None
        
    async def initialize(self):
        """Inicializar componentes"""
        try:
            # Inicializar collector
            self.collector = BitgetDataCollector()
            await asyncio.sleep(2)  # Esperar inicialización
            
            # Inicializar alineador temporal
            self.aligner = TemporalAlignment()
            
            logger.info("✅ Componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    async def execute(self, args=None):
        """Ejecutar descarga de datos"""
        try:
            logger.info("🚀 Iniciando descarga de datos...")
            
            # Inicializar componentes
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando componentes"}
            
            # Obtener configuración
            symbols = self.config.get("trading_settings", {}).get("timeframes", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", {}).get("timeframes", [])
            
            if not symbols or not timeframes:
                logger.error("❌ Configuración de símbolos o timeframes no encontrada")
                return {"status": "error", "message": "Configuración no encontrada"}
            
            logger.info(f"📊 Símbolos: {symbols}")
            logger.info(f"📊 Timeframes: {timeframes}")
            
            # Procesar cada símbolo
            results = {}
            for symbol in symbols:
                logger.info(f"🔄 Procesando {symbol}...")
                
                symbol_results = {}
                for timeframe in timeframes:
                    try:
                        logger.info(f"  📈 Descargando {symbol} - {timeframe}")
                        
                        # Verificar si ya existen datos
                        existing_count = db_manager.get_market_data_count_fast(symbol)
                        if existing_count > 0:
                            logger.info(f"  ✅ {symbol} ya tiene {existing_count} registros")
                            symbol_results[timeframe] = {"status": "exists", "count": existing_count}
                            continue
                        
                        # Descargar datos históricos
                        data = await self.collector.fetch_historical_data_extended(
                            symbol=symbol,
                            timeframe=timeframe,
                            years=1
                        )
                        
                        if not data.empty:
                            # Guardar datos
                            saved_count = await self.collector.save_historical_data(data)
                            symbol_results[timeframe] = {"status": "downloaded", "count": saved_count}
                            logger.info(f"  ✅ {symbol} - {timeframe}: {saved_count} registros descargados")
                        else:
                            symbol_results[timeframe] = {"status": "no_data", "count": 0}
                            logger.warning(f"  ⚠️ {symbol} - {timeframe}: Sin datos disponibles")
                            
                    except Exception as e:
                        logger.error(f"  ❌ Error procesando {symbol} - {timeframe}: {e}")
                        symbol_results[timeframe] = {"status": "error", "count": 0, "error": str(e)}
                        continue
                
                results[symbol] = symbol_results
            
            # Realizar alineación temporal
            logger.info("🔄 Iniciando alineación temporal...")
            alignment_results = await self._perform_temporal_alignment(symbols, timeframes)
            
            # Generar reporte final
            report = self._generate_report(results, alignment_results)
            
            return {
                "status": "success",
                "message": "Descarga completada",
                "results": results,
                "alignment": alignment_results,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"❌ Error en descarga de datos: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _perform_temporal_alignment(self, symbols, timeframes):
        """Realizar alineación temporal de los datos"""
        try:
            alignment_results = {}
            
            for timeframe in timeframes:
                logger.info(f"🔄 Alineando {timeframe}...")
                
                try:
                    # Obtener datos de todos los símbolos para este timeframe
                    symbol_data = {}
                    for symbol in symbols:
                        db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
                        if Path(db_path).exists():
                            import sqlite3
                            with sqlite3.connect(db_path) as conn:
                                df = pd.read_sql_query(
                                    "SELECT * FROM market_data ORDER BY timestamp", 
                                    conn, 
                                    index_col='timestamp',
                                    parse_dates=['timestamp']
                                )
                                if not df.empty:
                                    symbol_data[symbol] = df
                    
                    if symbol_data:
                        # Alinear datos
                        aligned_data = self.aligner.align_symbol_data(symbol_data, None, timeframe)
                        
                        if aligned_data:
                            # Guardar datos alineados
                            session_id = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            success = db_manager.store_aligned_data(aligned_data, timeframe, session_id)
                            
                            if success:
                                alignment_results[timeframe] = len(aligned_data)
                                logger.info(f"✅ Alineación {timeframe} completada: {len(aligned_data)} períodos")
                            else:
                                logger.error(f"❌ Error guardando alineación {timeframe}")
                        else:
                            logger.warning(f"⚠️ No se pudo alinear {timeframe}")
                    else:
                        logger.warning(f"⚠️ No hay datos para alinear {timeframe}")
                        
                except Exception as e:
                    logger.error(f"❌ Error alineando {timeframe}: {e}")
                    continue
            
            return alignment_results
            
        except Exception as e:
            logger.error(f"❌ Error en alineación temporal: {e}")
            return {}
    
    def _generate_report(self, results, alignment_results):
        """Generar reporte final"""
        try:
            total_downloaded = 0
            total_existing = 0
            total_errors = 0
            
            for symbol, symbol_results in results.items():
                for timeframe, result in symbol_results.items():
                    if result["status"] == "downloaded":
                        total_downloaded += result["count"]
                    elif result["status"] == "exists":
                        total_existing += result["count"]
                    elif result["status"] == "error":
                        total_errors += 1
            
            total_aligned = sum(alignment_results.values()) if alignment_results else 0
            
            report = f"""
📊 <b>Reporte de Descarga de Datos</b>

📈 <b>Estadísticas Generales:</b>
• Registros descargados: {total_downloaded:,}
• Registros existentes: {total_existing:,}
• Errores encontrados: {total_errors}
• Períodos alineados: {total_aligned:,}

🔄 <b>Alineación Temporal:</b>
• Timeframes procesados: {len(alignment_results)}
• Alineación exitosa: {len([k for k, v in alignment_results.items() if v > 0])}

✅ <b>Estado:</b> Proceso completado
            """
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "❌ Error generando reporte"

async def main():
    """Función principal"""
    script = DownloadDataScript()
    result = await script.execute()
    
    if result["status"] == "success":
        print("✅ Descarga completada exitosamente")
        print(result["report"])
    else:
        print(f"❌ Error: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
