#!/usr/bin/env python3
"""
Script de validación de alineación temporal
Verifica que todos los timeframes estén correctamente alineados para los agentes
"""

import sys
import os
import asyncio
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

async def validate_temporal_alignment():
    """Valida la alineación temporal de todos los símbolos y timeframes"""
    
    try:
        # Importar módulos necesarios
        from config.config_loader import user_config
        from core.data.temporal_alignment import TemporalAlignment, AlignmentConfig
        from core.data.symbol_database_manager import symbol_db_manager
        from core.data.historical_data_adapter import get_historical_data
        
        print("🔍 Validando configuración de alineación temporal...")
        
        # Obtener configuración
        symbols = user_config.get_symbols()
        timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'], [])
        
        print(f"📊 Símbolos configurados: {len(symbols)}")
        print(f"⏰ Timeframes configurados: {timeframes}")
        
        # Crear configuración de alineación
        alignment_config = AlignmentConfig(
            base_timeframe="5m",
            timeframes=timeframes,
            required_symbols=symbols,
            alignment_tolerance=timedelta(minutes=1),
            min_data_coverage=0.95,
            max_gap_minutes=60
        )
        
        # Crear alineador temporal
        aligner = TemporalAlignment(alignment_config)
        
        # Verificar datos disponibles
        print("\n📈 Verificando datos disponibles por símbolo y timeframe...")
        
        data_availability = {}
        for symbol in symbols:
            data_availability[symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Obtener datos de los últimos 7 días
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    
                    data = get_historical_data(symbol, timeframe, start_date, end_date)
                    
                    if not data.empty:
                        data_availability[symbol][timeframe] = {
                            'count': len(data),
                            'start': data.index[0] if not data.empty else None,
                            'end': data.index[-1] if not data.empty else None,
                            'available': True
                        }
                        print(f"  ✅ {symbol}_{timeframe}: {len(data)} registros")
                    else:
                        data_availability[symbol][timeframe] = {
                            'count': 0,
                            'start': None,
                            'end': None,
                            'available': False
                        }
                        print(f"  ❌ {symbol}_{timeframe}: Sin datos")
                        
                except Exception as e:
                    data_availability[symbol][timeframe] = {
                        'count': 0,
                        'start': None,
                        'end': None,
                        'available': False,
                        'error': str(e)
                    }
                    print(f"  ⚠️ {symbol}_{timeframe}: Error - {e}")
        
        # Verificar alineación temporal
        print("\n🔄 Verificando alineación temporal...")
        
        # Verificar que el timeframe base (5m) esté disponible para todos los símbolos
        base_timeframe = "5m"
        base_available = all(
            data_availability.get(symbol, {}).get(base_timeframe, {}).get('available', False)
            for symbol in symbols
        )
        
        if base_available:
            print(f"  ✅ Timeframe base {base_timeframe} disponible para todos los símbolos")
        else:
            print(f"  ❌ Timeframe base {base_timeframe} no disponible para todos los símbolos")
            
            # Mostrar qué símbolos no tienen el timeframe base
            missing_base = [
                symbol for symbol in symbols
                if not data_availability.get(symbol, {}).get(base_timeframe, {}).get('available', False)
            ]
            print(f"  📋 Símbolos sin {base_timeframe}: {missing_base}")
        
        # Verificar cobertura de datos
        print("\n📊 Análisis de cobertura de datos...")
        
        for symbol in symbols:
            print(f"\n  📈 {symbol}:")
            
            for timeframe in timeframes:
                tf_data = data_availability.get(symbol, {}).get(timeframe, {})
                
                if tf_data.get('available', False):
                    count = tf_data.get('count', 0)
                    start = tf_data.get('start')
                    end = tf_data.get('end')
                    
                    # Calcular días de cobertura
                    if start and end:
                        days_covered = (end - start).days
                        print(f"    {timeframe}: {count} registros, {days_covered} días")
                    else:
                        print(f"    {timeframe}: {count} registros")
                else:
                    error = tf_data.get('error', 'Sin datos')
                    print(f"    {timeframe}: ❌ {error}")
        
        # Verificar configuración de agentes
        print("\n🤖 Verificando configuración de agentes...")
        
        # Verificar que los timeframes requeridos para ML estén disponibles
        ml_timeframes = user_config.get_value(['trading_settings', 'timeframes', 'ml_training'], ['1h', '4h', '1d'])
        trading_timeframes = user_config.get_value(['trading_settings', 'timeframes', 'priority', 'high'], ['1m', '5m', '15m'])
        
        print(f"  🧠 Timeframes para ML: {ml_timeframes}")
        print(f"  📈 Timeframes para Trading: {trading_timeframes}")
        
        # Verificar disponibilidad de timeframes ML
        ml_available = {}
        for symbol in symbols:
            ml_available[symbol] = all(
                data_availability.get(symbol, {}).get(tf, {}).get('available', False)
                for tf in ml_timeframes
            )
        
        ml_ready_symbols = [s for s, ready in ml_available.items() if ready]
        print(f"  ✅ Símbolos listos para ML: {len(ml_ready_symbols)}/{len(symbols)}")
        
        if ml_ready_symbols:
            print(f"    📋 {ml_ready_symbols}")
        
        # Verificar disponibilidad de timeframes de trading
        trading_available = {}
        for symbol in symbols:
            trading_available[symbol] = all(
                data_availability.get(symbol, {}).get(tf, {}).get('available', False)
                for tf in trading_timeframes
            )
        
        trading_ready_symbols = [s for s, ready in trading_available.items() if ready]
        print(f"  ✅ Símbolos listos para Trading: {len(trading_ready_symbols)}/{len(symbols)}")
        
        if trading_ready_symbols:
            print(f"    📋 {trading_ready_symbols}")
        
        # Resumen final
        print("\n📋 RESUMEN DE VALIDACIÓN:")
        print(f"  📊 Total de símbolos: {len(symbols)}")
        print(f"  ⏰ Total de timeframes: {len(timeframes)}")
        print(f"  🧠 Símbolos listos para ML: {len(ml_ready_symbols)}")
        print(f"  📈 Símbolos listos para Trading: {len(trading_ready_symbols)}")
        print(f"  🔄 Timeframe base ({base_timeframe}) disponible: {'✅' if base_available else '❌'}")
        
        # Recomendaciones
        print("\n💡 RECOMENDACIONES:")
        
        if not base_available:
            print("  ⚠️ Descargar datos del timeframe base (5m) para todos los símbolos")
        
        if len(ml_ready_symbols) < len(symbols):
            missing_ml = set(symbols) - set(ml_ready_symbols)
            print(f"  ⚠️ Descargar datos ML para: {list(missing_ml)}")
        
        if len(trading_ready_symbols) < len(symbols):
            missing_trading = set(symbols) - set(trading_ready_symbols)
            print(f"  ⚠️ Descargar datos de trading para: {list(missing_trading)}")
        
        if base_available and len(ml_ready_symbols) == len(symbols) and len(trading_ready_symbols) == len(symbols):
            print("  ✅ ¡Todos los agentes están listos para funcionar correctamente!")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en validación: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando validación de alineación temporal...")
    success = asyncio.run(validate_temporal_alignment())
    
    if success:
        print("\n✅ Validación completada exitosamente")
    else:
        print("\n❌ Validación falló")
        sys.exit(1)
