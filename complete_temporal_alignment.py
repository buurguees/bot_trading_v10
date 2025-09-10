#!/usr/bin/env python3
"""
Script para completar la alineación temporal
Descarga los datos faltantes para que todos los agentes trabajen correctamente
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append('.')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def complete_temporal_alignment():
    """Completa la alineación temporal descargando datos faltantes"""
    
    try:
        # Importar módulos necesarios
        from config.config_loader import user_config
        from core.data.collector import data_collector
        
        print("🚀 Completando alineación temporal...")
        
        # Obtener configuración
        symbols = user_config.get_symbols()
        timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'], [])
        
        print(f"📊 Símbolos: {len(symbols)}")
        print(f"⏰ Timeframes: {timeframes}")
        
        # Identificar datos faltantes
        missing_data = {
            'BTCUSDT': timeframes,  # Todos los timeframes faltan
            'ETHUSDT': timeframes,  # Todos los timeframes faltan
            'ADAUSDT': timeframes,  # Todos los timeframes faltan
            'SOLUSDT': ['1m'],      # Solo falta 1m
            'DOGEUSDT': ['1m'],     # Solo falta 1m
            'AVAXUSDT': ['1m'],     # Solo falta 1m
            'TONUSDT': ['1m'],      # Solo falta 1m
            'XRPUSDT': ['1m'],      # Solo falta 1m
            'LINKUSDT': ['1m']      # Solo falta 1m
        }
        
        print("\n📋 Datos faltantes identificados:")
        for symbol, missing_tfs in missing_data.items():
            if missing_tfs:
                print(f"  {symbol}: {missing_tfs}")
        
        # Descargar datos faltantes
        print("\n⬇️ Iniciando descarga de datos faltantes...")
        
        total_downloads = 0
        successful_downloads = 0
        
        for symbol in symbols:
            missing_tfs = missing_data.get(symbol, [])
            
            if not missing_tfs:
                print(f"  ✅ {symbol}: Todos los datos disponibles")
                continue
            
            print(f"\n📈 Descargando datos para {symbol}...")
            
            for timeframe in missing_tfs:
                try:
                    print(f"  ⏰ Descargando {symbol}_{timeframe}...")
                    
                    # Configurar período de descarga
                    if timeframe == '1m':
                        # Para 1m, descargar solo 7 días (más reciente)
                        days_back = 7
                    else:
                        # Para otros timeframes, descargar 30 días
                        days_back = 30
                    
                    # Calcular fechas
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days_back)
                    
                    print(f"    📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
                    
                    # Descargar datos usando el collector
                    success = await data_collector.download_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if success:
                        print(f"    ✅ {symbol}_{timeframe}: Descarga exitosa")
                        successful_downloads += 1
                    else:
                        print(f"    ❌ {symbol}_{timeframe}: Error en descarga")
                    
                    total_downloads += 1
                    
                    # Pausa entre descargas para evitar rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"    ❌ {symbol}_{timeframe}: Error - {e}")
                    total_downloads += 1
        
        # Resumen de descarga
        print(f"\n📊 RESUMEN DE DESCARGA:")
        print(f"  📥 Total de descargas intentadas: {total_downloads}")
        print(f"  ✅ Descargas exitosas: {successful_downloads}")
        print(f"  ❌ Descargas fallidas: {total_downloads - successful_downloads}")
        
        if successful_downloads > 0:
            print(f"\n🔄 Ejecutando validación post-descarga...")
            
            # Ejecutar validación nuevamente
            from validate_temporal_alignment import validate_temporal_alignment
            await validate_temporal_alignment()
        
        return True
        
    except Exception as e:
        logger.error(f"Error completando alineación temporal: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando completado de alineación temporal...")
    success = asyncio.run(complete_temporal_alignment())
    
    if success:
        print("\n✅ Completado de alineación temporal exitoso")
    else:
        print("\n❌ Error en completado de alineación temporal")
        sys.exit(1)
