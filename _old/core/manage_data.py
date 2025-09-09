#!/usr/bin/env python3
"""
manage_data.py - Gestor Unificado de Datos - Trading Bot v10
===========================================================

Script principal que consolida todas las funcionalidades de gestión de datos
que antes estaban dispersas en múltiples scripts.

Funcionalidades:
- Verificación de datos históricos
- Descarga de datos faltantes
- Corrección de problemas de timestamps
- Análisis de integridad de datos
- Resumen completo del estado de la base de datos

Uso:
    python manage_data.py --action verify
    python manage_data.py --action download --years 2
    python manage_data.py --action fix-timestamps
    python manage_data.py --action summary
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
import logging

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.database import db_manager
from data.collector import download_extensive_historical_data, download_missing_data
from config.config_loader import user_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataManager:
    """Gestor unificado de datos del Trading Bot v10"""
    
    def __init__(self):
        try:
            config_data = user_config.config
            self.symbols = config_data.get('bot_settings', {}).get('main_symbols', 
                                                                 ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
        except:
            self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    def verify_historical_data(self):
        """Verifica el estado de los datos históricos"""
        print("🔍 VERIFICACIÓN DE DATOS HISTÓRICOS")
        print("=" * 40)
        
        try:
            summary = db_manager.get_historical_data_summary()
            
            if 'error' in summary:
                print(f"❌ Error: {summary['error']}")
                return
            
            print(f"📊 Símbolos disponibles: {summary['total_symbols']}")
            print(f"📈 Total registros: {summary['total_records']:,}")
            print()
            
            for symbol_info in summary['symbols']:
                symbol = symbol_info['symbol']
                count = symbol_info['count']
                status = symbol_info['status']
                
                if status == 'OK':
                    start_date = symbol_info['start_date']
                    end_date = symbol_info['end_date']
                    duration = symbol_info['duration_days']
                    
                    print(f"📈 {symbol}:")
                    print(f"   📊 Registros: {count:,}")
                    print(f"   📅 Desde: {start_date}")
                    print(f"   📅 Hasta: {end_date}")
                    print(f"   ⏱️  Duración: {duration} días")
                else:
                    print(f"❌ {symbol}: {status}")
                print()
            
            print("💡 RECOMENDACIONES:")
            for rec in summary['recommendations']:
                print(f"   {rec}")
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
    
    async def download_data(self, years: int = 2, target_days: int = None):
        """Descarga datos históricos"""
        print(f"📥 DESCARGANDO DATOS HISTÓRICOS ({years} años)")
        print("=" * 45)
        
        try:
            if target_days:
                # Descargar solo datos faltantes
                print("🔍 Verificando datos faltantes...")
                results = await download_missing_data(self.symbols, target_days)
                
                print(f"📊 Símbolos verificados: {results['symbols_checked']}")
                print(f"✅ Símbolos OK: {results['symbols_ok']}")
                print(f"🔄 Símbolos actualizados: {results['symbols_updated']}")
                print(f"📈 Total descargado: {results['total_downloaded']:,} registros")
                print()
                
                for symbol, details in results['details'].items():
                    status = details['status']
                    if status == 'OK':
                        print(f"✅ {symbol}: {details['message']}")
                    elif status == 'UPDATED':
                        print(f"🔄 {symbol}: {details['downloaded']} registros descargados")
                    elif status == 'NEW':
                        print(f"🆕 {symbol}: {details['downloaded']} registros descargados")
                    else:
                        print(f"❌ {symbol}: {details.get('error', 'Error desconocido')}")
            else:
                # Descarga completa
                results = await download_extensive_historical_data(self.symbols, years)
                
                # Calcular total correctamente
                total_downloaded = 0
                for symbol_results in results.values():
                    if isinstance(symbol_results, dict):
                        for timeframe_count in symbol_results.values():
                            if isinstance(timeframe_count, int):
                                total_downloaded += timeframe_count
                    elif isinstance(symbol_results, int):
                        total_downloaded += symbol_results
                
                print(f"🎉 Descarga completada: {total_downloaded:,} registros totales")
                print()
                
                for symbol, symbol_results in results.items():
                    if isinstance(symbol_results, dict):
                        symbol_total = sum(count for count in symbol_results.values() if isinstance(count, int))
                        print(f"📈 {symbol}: {symbol_total:,} registros")
                    else:
                        print(f"📈 {symbol}: {symbol_results:,} registros")
            
        except Exception as e:
            print(f"❌ Error en descarga: {e}")
    
    def fix_timestamps(self):
        """Corrige problemas de timestamps"""
        print("🔧 CORRIGIENDO TIMESTAMPS")
        print("=" * 30)
        
        try:
            results = db_manager.fix_timestamp_issues()
            
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
                return
            
            for symbol, result in results.items():
                status = result['status']
                if status == 'OK':
                    print(f"✅ {symbol}: {result['message']}")
                elif status == 'FIXED':
                    print(f"🔧 {symbol}: {result['message']}")
                else:
                    print(f"❌ {symbol}: {result.get('error', 'Error desconocido')}")
            
        except Exception as e:
            print(f"❌ Error corrigiendo timestamps: {e}")
    
    def show_summary(self):
        """Muestra un resumen completo del estado de la base de datos"""
        print("📊 RESUMEN COMPLETO DE LA BASE DE DATOS")
        print("=" * 45)
        
        try:
            # Estadísticas generales
            stats = db_manager.get_database_stats()
            print("📈 ESTADÍSTICAS GENERALES:")
            for key, value in stats.items():
                if 'count' in key:
                    print(f"   {key}: {value:,}")
                else:
                    print(f"   {key}: {value}")
            print()
            
            # Resumen de datos históricos
            summary = db_manager.get_historical_data_summary()
            if 'error' not in summary:
                print("📅 DATOS HISTÓRICOS:")
                print(f"   Símbolos: {summary['total_symbols']}")
                print(f"   Total registros: {summary['total_records']:,}")
                
                valid_symbols = [s for s in summary['symbols'] if s['status'] == 'OK']
                if valid_symbols:
                    min_duration = min(s['duration_days'] for s in valid_symbols)
                    max_duration = max(s['duration_days'] for s in valid_symbols)
                    print(f"   Duración mínima: {min_duration} días")
                    print(f"   Duración máxima: {max_duration} días")
                print()
            
            # Verificar integridad
            print("🔍 VERIFICACIÓN DE INTEGRIDAD:")
            integrity = db_manager.verify_data_integrity()
            print(f"   Total registros: {integrity['total_records']:,}")
            print(f"   Símbolos: {len(integrity['symbols'])}")
            
            if integrity['gaps_detected']:
                print("   ⚠️ Gaps detectados en:")
                for symbol, gaps in integrity['gaps_detected'].items():
                    print(f"      {symbol}: {len(gaps)} gaps")
            else:
                print("   ✅ No se detectaron gaps significativos")
            
        except Exception as e:
            print(f"❌ Error en resumen: {e}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Gestor Unificado de Datos - Trading Bot v10')
    parser.add_argument('--action', choices=['verify', 'download', 'fix-timestamps', 'summary'], 
                       required=True, help='Acción a realizar')
    parser.add_argument('--years', type=int, default=2, help='Años de datos a descargar')
    parser.add_argument('--target-days', type=int, help='Días objetivo para verificación')
    parser.add_argument('--symbols', nargs='+', help='Símbolos específicos a procesar')
    
    args = parser.parse_args()
    
    manager = DataManager()
    
    if args.symbols:
        manager.symbols = args.symbols
    
    try:
        if args.action == 'verify':
            manager.verify_historical_data()
        elif args.action == 'download':
            asyncio.run(manager.download_data(args.years, args.target_days))
        elif args.action == 'fix-timestamps':
            manager.fix_timestamps()
        elif args.action == 'summary':
            manager.show_summary()
        
        print("\n🎉 Operación completada exitosamente")
        
    except KeyboardInterrupt:
        print("\n⏹️ Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
