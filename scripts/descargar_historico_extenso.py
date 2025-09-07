#!/usr/bin/env python3
"""
Script para Descargar Histórico Extenso - Trading Bot v10
========================================================

Descarga datos históricos de múltiples años para mejorar el entrenamiento del modelo.

Uso: python scripts/descargar_historico_extenso.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.collector import BitgetDataCollector
from data.database import db_manager
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DescargaHistoricoExtenso:
    """Descarga datos históricos extensos para múltiples años"""
    
    def __init__(self):
        self.collector = BitgetDataCollector()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        self.years_to_download = 3  # Descargar 3 años de datos
        
    async def descargar_historico_completo(self):
        """Descarga histórico completo para todos los símbolos"""
        print("📈 DESCARGA DE HISTÓRICO EXTENSO - TRADING BOT v10")
        print("=" * 60)
        print(f"🎯 Objetivo: Descargar {self.years_to_download} años de datos")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_downloaded = 0
        
        for symbol in self.symbols:
            print(f"🔄 PROCESANDO {symbol}")
            print("-" * 40)
            
            try:
                # Calcular fechas para 3 años hacia atrás
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365 * self.years_to_download)
                
                print(f"📅 Período: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
                print(f"⏱️  Duración: {self.years_to_download} años")
                
                # Verificar datos existentes
                existing_data = self._verificar_datos_existentes(symbol)
                if existing_data:
                    print(f"📊 Datos existentes: {existing_data['count']} registros")
                    print(f"📅 Desde: {existing_data['start']}")
                    print(f"📅 Hasta: {existing_data['end']}")
                
                # Descargar datos
                print("🚀 Iniciando descarga...")
                downloaded = await self._descargar_datos_simbolo(symbol, start_date, end_date)
                
                if downloaded > 0:
                    print(f"✅ Descargados: {downloaded} registros")
                    total_downloaded += downloaded
                else:
                    print("⚠️ No se descargaron nuevos datos")
                
                print()
                
            except Exception as e:
                print(f"❌ Error procesando {symbol}: {e}")
                print()
        
        print("📊 RESUMEN FINAL")
        print("=" * 20)
        print(f"✅ Total descargado: {total_downloaded} registros")
        print(f"📈 Símbolos procesados: {len(self.symbols)}")
        print(f"⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar datos finales
        self._verificar_datos_finales()
    
    def _verificar_datos_existentes(self, symbol):
        """Verifica datos existentes para un símbolo"""
        try:
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
                return {
                    'count': row['count'],
                    'start': datetime.fromtimestamp(row['start_ts']).strftime('%Y-%m-%d %H:%M'),
                    'end': datetime.fromtimestamp(row['end_ts']).strftime('%Y-%m-%d %H:%M')
                }
        except Exception as e:
            logger.debug(f"Error verificando datos existentes para {symbol}: {e}")
        
        return None
    
    async def _descargar_datos_simbolo(self, symbol, start_date, end_date):
        """Descarga datos para un símbolo específico"""
        try:
            # Usar el collector existente
            downloaded = await self.collector.fetch_historical_data(
                symbol=symbol,
                timeframe='1h',
                start_time=start_date,
                end_time=end_date
            )
            
            return downloaded if downloaded else 0
            
        except Exception as e:
            logger.error(f"Error descargando datos para {symbol}: {e}")
            return 0
    
    def _verificar_datos_finales(self):
        """Verifica el estado final de los datos"""
        print("\n🔍 VERIFICACIÓN FINAL DE DATOS")
        print("=" * 35)
        
        for symbol in self.symbols:
            try:
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
    
    async def descargar_por_periodos(self):
        """Descarga datos por períodos para evitar límites de API"""
        print("📈 DESCARGA POR PERÍODOS - TRADING BOT v10")
        print("=" * 50)
        
        for symbol in self.symbols:
            print(f"\n🔄 PROCESANDO {symbol} POR PERÍODOS")
            print("-" * 40)
            
            # Dividir en períodos de 1 año
            current_date = datetime.now()
            total_downloaded = 0
            
            for year in range(self.years_to_download):
                year_start = current_date - timedelta(days=365 * (year + 1))
                year_end = current_date - timedelta(days=365 * year)
                
                print(f"📅 Año {year + 1}: {year_start.strftime('%Y-%m-%d')} → {year_end.strftime('%Y-%m-%d')}")
                
                try:
                    downloaded = await self._descargar_datos_simbolo(symbol, year_start, year_end)
                    total_downloaded += downloaded
                    print(f"✅ Descargados: {downloaded} registros")
                    
                    # Pausa entre descargas para evitar límites de API
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Error en año {year + 1}: {e}")
            
            print(f"📊 Total {symbol}: {total_downloaded} registros")

async def main():
    """Función principal"""
    try:
        descargador = DescargaHistoricoExtenso()
        
        print("Selecciona el método de descarga:")
        print("1. Descarga completa (recomendado)")
        print("2. Descarga por períodos (para APIs con límites)")
        
        choice = input("Opción (1-2): ").strip()
        
        if choice == "1":
            await descargador.descargar_historico_completo()
        elif choice == "2":
            await descargador.descargar_por_periodos()
        else:
            print("Opción inválida, usando descarga completa...")
            await descargador.descargar_historico_completo()
        
        print("\n🎉 DESCARGA COMPLETADA")
        print("Ahora puedes ejecutar: python scripts/verificar_historico.py")
        
    except KeyboardInterrupt:
        print("\n⏹️ Descarga cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
