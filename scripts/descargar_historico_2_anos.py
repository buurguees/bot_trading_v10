#!/usr/bin/env python3
"""
Script para Descargar 2 Años de Histórico - Trading Bot v10
===========================================================

Descarga datos históricos de 2 años para mejorar el entrenamiento del modelo.

Uso: python scripts/descargar_historico_2_anos.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.collector import collect_and_save_historical_data
from datetime import datetime, timedelta
import asyncio
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DescargaHistorico2Anos:
    """Descarga datos históricos de 2 años para múltiples símbolos"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        self.timeframes = ['1h', '4h', '1d']  # Múltiples timeframes
        self.days_back = 730  # 2 años
        
    async def descargar_historico_2_anos(self):
        """Descarga histórico de 2 años para todos los símbolos"""
        print("📈 DESCARGA DE HISTÓRICO 2 AÑOS - TRADING BOT v10")
        print("=" * 60)
        print(f"🎯 Objetivo: Descargar 2 años de datos ({self.days_back} días)")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"⏰ Timeframes: {', '.join(self.timeframes)}")
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_downloaded = 0
        
        for symbol in self.symbols:
            print(f"🔄 PROCESANDO {symbol}")
            print("-" * 40)
            
            symbol_total = 0
            
            for timeframe in self.timeframes:
                print(f"📊 Descargando {symbol} - {timeframe} - {self.days_back} días")
                
                try:
                    # Descargar datos
                    saved_count = await collect_and_save_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        days_back=self.days_back
                    )
                    
                    if saved_count > 0:
                        print(f"✅ {symbol} - {timeframe}: {saved_count} registros")
                        symbol_total += saved_count
                    else:
                        print(f"⚠️ {symbol} - {timeframe}: Sin nuevos datos")
                    
                    # Pausa entre descargas para evitar límites de API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error {symbol} - {timeframe}: {e}")
            
            print(f"📊 Total {symbol}: {symbol_total} registros")
            total_downloaded += symbol_total
            print()
        
        print("📊 RESUMEN FINAL")
        print("=" * 20)
        print(f"✅ Total descargado: {total_downloaded} registros")
        print(f"📈 Símbolos procesados: {len(self.symbols)}")
        print(f"⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar datos finales
        await self._verificar_datos_finales()
    
    async def _verificar_datos_finales(self):
        """Verifica el estado final de los datos"""
        print("\n🔍 VERIFICACIÓN FINAL DE DATOS")
        print("=" * 35)
        
        try:
            from data.database import db_manager
            
            for symbol in self.symbols:
                try:
                    # Obtener datos de la base de datos
                    query = f"""
                    SELECT 
                        COUNT(*) as count,
                        MIN(timestamp) as start_ts,
                        MAX(timestamp) as end_ts
                    FROM market_data 
                    WHERE symbol = '{symbol}'
                    """
                    
                    result = db_manager.execute_query(query)
                    if not result.empty:
                        row = result.iloc[0]
                        count = row['count']
                        start_date = datetime.fromtimestamp(row['start_ts']).strftime('%Y-%m-%d')
                        end_date = datetime.fromtimestamp(row['end_ts']).strftime('%Y-%m-%d')
                        
                        # Calcular duración
                        duration = (datetime.fromtimestamp(row['end_ts']) - datetime.fromtimestamp(row['start_ts'])).days
                        
                        print(f"📊 {symbol}:")
                        print(f"   📈 Registros: {count:,}")
                        print(f"   📅 Desde: {start_date}")
                        print(f"   📅 Hasta: {end_date}")
                        print(f"   ⏱️  Duración: {duration} días ({duration/365:.1f} años)")
                        print()
                    
                except Exception as e:
                    print(f"❌ Error verificando {symbol}: {e}")
        
        except Exception as e:
            print(f"❌ Error en verificación final: {e}")
    
    async def descargar_por_simbolo_individual(self, symbol):
        """Descarga datos para un símbolo específico"""
        print(f"🔄 DESCARGA INDIVIDUAL: {symbol}")
        print("-" * 40)
        
        total_downloaded = 0
        
        for timeframe in self.timeframes:
            print(f"📊 Descargando {symbol} - {timeframe} - {self.days_back} días")
            
            try:
                saved_count = await collect_and_save_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    days_back=self.days_back
                )
                
                if saved_count > 0:
                    print(f"✅ {symbol} - {timeframe}: {saved_count} registros")
                    total_downloaded += saved_count
                else:
                    print(f"⚠️ {symbol} - {timeframe}: Sin nuevos datos")
                
                # Pausa entre descargas
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error {symbol} - {timeframe}: {e}")
        
        print(f"📊 Total {symbol}: {total_downloaded} registros")
        return total_downloaded

async def main():
    """Función principal"""
    try:
        descargador = DescargaHistorico2Anos()
        
        print("Selecciona el método de descarga:")
        print("1. Descarga completa (todos los símbolos)")
        print("2. Descarga individual por símbolo")
        print("3. Solo BTCUSDT y ETHUSDT (corregir errores)")
        
        choice = input("Opción (1-3): ").strip()
        
        if choice == "1":
            await descargador.descargar_historico_2_anos()
        elif choice == "2":
            print("\nSímbolos disponibles:")
            for i, symbol in enumerate(descargador.symbols, 1):
                print(f"{i}. {symbol}")
            
            symbol_choice = input("Selecciona símbolo (1-4): ").strip()
            try:
                symbol_index = int(symbol_choice) - 1
                if 0 <= symbol_index < len(descargador.symbols):
                    symbol = descargador.symbols[symbol_index]
                    await descargador.descargar_por_simbolo_individual(symbol)
                else:
                    print("Opción inválida")
            except ValueError:
                print("Opción inválida")
        elif choice == "3":
            print("🔄 Corrigiendo BTCUSDT y ETHUSDT...")
            for symbol in ['BTCUSDT', 'ETHUSDT']:
                await descargador.descargar_por_simbolo_individual(symbol)
        else:
            print("Opción inválida, usando descarga completa...")
            await descargador.descargar_historico_2_anos()
        
        print("\n🎉 DESCARGA COMPLETADA")
        print("Ahora puedes ejecutar: python scripts/verificar_historico.py")
        
    except KeyboardInterrupt:
        print("\n⏹️ Descarga cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
