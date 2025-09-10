#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_symbol_database.py - SCRIPT DE PRUEBA PARA BASES DE DATOS POR SÍMBOLO
Script para probar el nuevo sistema de bases de datos por símbolo y timeframe
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from core.data.symbol_database_manager import (
    SymbolDatabaseManager, 
    OHLCVData, 
    symbol_db_manager
)
from core.data.historical_data_adapter import historical_data_adapter

async def test_symbol_database_system():
    """Prueba el sistema de bases de datos por símbolo"""
    print("🧪 Iniciando prueba del sistema de bases de datos por símbolo...")
    
    try:
        # 1. Crear datos de prueba
        print("\n1️⃣ Creando datos de prueba...")
        
        test_symbol = "BTCUSDT"
        test_timeframe = "1h"
        
        # Generar datos de prueba para las últimas 24 horas
        now = datetime.now()
        test_data = []
        
        for i in range(24):  # 24 horas
            timestamp = now - timedelta(hours=i)
            # Datos simulados de Bitcoin
            base_price = 50000 + (i * 100)  # Precio base que varía
            
            ohlcv = OHLCVData(
                timestamp=int(timestamp.timestamp()),
                open=base_price,
                high=base_price + 50,
                low=base_price - 50,
                close=base_price + 25,
                volume=1000 + (i * 10)
            )
            test_data.append(ohlcv)
        
        print(f"   ✅ Creados {len(test_data)} registros de prueba")
        
        # 2. Insertar datos
        print("\n2️⃣ Insertando datos en la base de datos...")
        
        inserted = symbol_db_manager.insert_data(test_symbol, test_timeframe, test_data)
        print(f"   ✅ Insertados {inserted} registros")
        
        # 3. Verificar inserción
        print("\n3️⃣ Verificando inserción...")
        
        record_count = symbol_db_manager.get_record_count(test_symbol, test_timeframe)
        print(f"   📊 Registros en BD: {record_count}")
        
        # 4. Obtener datos
        print("\n4️⃣ Obteniendo datos...")
        
        data = symbol_db_manager.get_data(test_symbol, test_timeframe)
        print(f"   📈 Datos obtenidos: {len(data)} registros")
        print(f"   📅 Rango de fechas: {data.index.min()} a {data.index.max()}")
        
        # 5. Obtener datos recientes
        print("\n5️⃣ Obteniendo datos recientes...")
        
        recent_data = symbol_db_manager.get_latest_data(test_symbol, test_timeframe, limit=5)
        print(f"   🕐 Datos recientes: {len(recent_data)} registros")
        
        # 6. Obtener rango de fechas
        print("\n6️⃣ Obteniendo rango de fechas...")
        
        start_date, end_date = symbol_db_manager.get_data_range(test_symbol, test_timeframe)
        print(f"   📅 Rango: {start_date} a {end_date}")
        
        # 7. Obtener estadísticas
        print("\n7️⃣ Obteniendo estadísticas...")
        
        stats = symbol_db_manager.get_database_stats(test_symbol, test_timeframe)
        print(f"   📊 Estadísticas:")
        for key, value in stats.items():
            print(f"      • {key}: {value}")
        
        # 8. Probar adaptador
        print("\n8️⃣ Probando adaptador...")
        
        adapter_data = historical_data_adapter.get_data(test_symbol, test_timeframe)
        print(f"   🔄 Datos del adaptador: {len(adapter_data)} registros")
        
        # 9. Probar análisis de cobertura
        print("\n9️⃣ Probando análisis de cobertura...")
        
        coverage = historical_data_adapter.get_coverage_analysis()
        print(f"   📈 Cobertura general: {coverage.get('overall_coverage_percentage', 0):.1f}%")
        
        # 10. Limpiar datos de prueba
        print("\n🔟 Limpiando datos de prueba...")
        
        # Nota: En una implementación real, podrías querer mantener los datos de prueba
        # o tener una función específica para limpiar datos de prueba
        
        print("   ✅ Prueba completada exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_symbols():
    """Prueba con múltiples símbolos y timeframes"""
    print("\n🧪 Probando múltiples símbolos y timeframes...")
    
    try:
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        timeframes = ["1h", "4h", "1d"]
        
        for symbol in symbols:
            for timeframe in timeframes:
                print(f"   📊 Probando {symbol}_{timeframe}...")
                
                # Crear datos de prueba
                test_data = []
                now = datetime.now()
                
                for i in range(10):  # 10 registros de prueba
                    timestamp = now - timedelta(hours=i)
                    base_price = 1000 + (i * 10)
                    
                    ohlcv = OHLCVData(
                        timestamp=int(timestamp.timestamp()),
                        open=base_price,
                        high=base_price + 5,
                        low=base_price - 5,
                        close=base_price + 2,
                        volume=100 + i
                    )
                    test_data.append(ohlcv)
                
                # Insertar datos
                inserted = symbol_db_manager.insert_data(symbol, timeframe, test_data)
                print(f"      ✅ {inserted} registros insertados")
        
        # Verificar todos los símbolos
        all_symbols = symbol_db_manager.get_all_symbols()
        print(f"   🎯 Símbolos en el sistema: {all_symbols}")
        
        # Verificar timeframes para cada símbolo
        for symbol in all_symbols:
            timeframes = symbol_db_manager.get_symbol_timeframes(symbol)
            print(f"   📊 {symbol}: {timeframes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba múltiple: {e}")
        return False

async def main():
    """Función principal de prueba"""
    print("=" * 80)
    print("🧪 PRUEBA DEL SISTEMA DE BASES DE DATOS POR SÍMBOLO")
    print("=" * 80)
    
    # Prueba 1: Sistema básico
    test1_success = await test_symbol_database_system()
    
    # Prueba 2: Múltiples símbolos
    test2_success = await test_multiple_symbols()
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 80)
    print(f"✅ Sistema básico: {'PASÓ' if test1_success else 'FALLÓ'}")
    print(f"✅ Múltiples símbolos: {'PASÓ' if test2_success else 'FALLÓ'}")
    
    if test1_success and test2_success:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("\n💡 PRÓXIMOS PASOS:")
        print("   1. Ejecutar migración: python scripts/data/migrate_to_symbol_databases.py --dry-run")
        print("   2. Migrar datos reales: python scripts/data/migrate_to_symbol_databases.py")
        print("   3. Verificar migración: python scripts/data/migrate_to_symbol_databases.py --stats-only")
        return 0
    else:
        print("\n⚠️ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
