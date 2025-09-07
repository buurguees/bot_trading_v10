#!/usr/bin/env python3
"""
📊 Descarga Simple de Datos - Trading Bot v10
=============================================

Script simple para descargar datos históricos y probar el sistema.

Uso: python scripts/descargar_datos_simple.py
"""

import asyncio
import logging
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback
import json

# Añadir el directorio del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Imports del bot
from config.config_loader import user_config
from data.collector import data_collector
from data.database import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/descarga_simple_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DescargaSimple:
    """Sistema simple de descarga de datos"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.timeframes = ['1h', '4h', '1d']
        self.days = 30  # Empezar con 30 días
        
        logger.info("Sistema de descarga simple inicializado")
    
    async def ejecutar_descarga(self):
        """Ejecuta la descarga de datos"""
        print("TRADING BOT v10 - DESCARGA SIMPLE")
        print("=" * 50)
        print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Símbolos: {', '.join(self.symbols)}")
        print(f"Timeframes: {', '.join(self.timeframes)}")
        print(f"Días: {self.days}")
        print()
        
        try:
            # 1. Verificar conectividad
            await self._verificar_conectividad()
            
            # 2. Descargar datos
            await self._descargar_datos()
            
            # 3. Verificar datos descargados
            await self._verificar_datos()
            
            print("\n[OK] Descarga completada exitosamente")
            
        except Exception as e:
            logger.error(f"Error en descarga: {e}")
            logger.error(traceback.format_exc())
            print(f"\n[ERROR] Error en descarga: {e}")
    
    async def _verificar_conectividad(self):
        """Verifica conectividad con APIs"""
        print("VERIFICANDO CONECTIVIDAD")
        print("-" * 30)
        
        try:
            # Verificar collector
            collector_health = await data_collector.health_check()
            if collector_health.get('rest_api_ok'):
                print("   [OK] API REST funcionando")
            else:
                print("   [ERROR] API REST no disponible")
                raise Exception("API REST no disponible")
            
            # Verificar base de datos
            db_stats = db_manager.get_database_stats()
            print(f"   [OK] Base de datos: {db_stats.get('file_size_mb', 0):.2f} MB")
            
            print("   [OK] Conectividad verificada")
            print()
            
        except Exception as e:
            logger.error(f"Error verificando conectividad: {e}")
            raise
    
    async def _descargar_datos(self):
        """Descarga datos históricos"""
        print("DESCARGANDO DATOS HISTORICOS")
        print("-" * 35)
        
        try:
            total_downloaded = 0
            
            for symbol in self.symbols:
                print(f"Descargando {symbol}...")
                
                for timeframe in self.timeframes:
                    try:
                        print(f"   {timeframe}...", end=" ")
                        
                        # Descargar datos
                        df = await data_collector.fetch_historical_data(
                            symbol, timeframe, self.days
                        )
                        
                        if not df.empty:
                            # Guardar en base de datos
                            saved_count = await self._save_historical_data(df, symbol, timeframe)
                            total_downloaded += saved_count
                            print(f"[OK] {saved_count:,} registros")
                        else:
                            print("[ERROR] Sin datos")
                            
                    except Exception as e:
                        print(f"[ERROR] {e}")
                        continue
                
                print(f"   {symbol} completado")
                print()
            
            print(f"TOTAL DESCARGADO: {total_downloaded:,} registros")
            print()
            
            if total_downloaded < 100:
                raise Exception(f"Datos insuficientes: solo {total_downloaded} registros")
            
        except Exception as e:
            logger.error(f"Error descargando datos históricos: {e}")
            raise
    
    async def _save_historical_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                return 0
            
            # Importar MarketData
            from data.database import MarketData
            
            # Convertir DataFrame a MarketData objects
            market_data_list = []
            for timestamp, row in df.iterrows():
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=int(timestamp.timestamp()),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume'])
                )
                market_data_list.append(market_data)
            
            # Insertar en base de datos usando bulk insert
            try:
                saved_count = db_manager.insert_market_data_bulk(market_data_list)
                return saved_count
            except Exception as e:
                logger.error(f"Error en bulk insert, intentando uno por uno: {e}")
                # Fallback: insertar uno por uno
                saved_count = 0
                for data in market_data_list:
                    try:
                        success = db_manager.insert_market_data(data)
                        if success:
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"Error insertando dato: {e}")
                        continue
                return saved_count
            
        except Exception as e:
            logger.error(f"Error guardando datos históricos: {e}")
            return 0
    
    async def _verificar_datos(self):
        """Verifica los datos descargados"""
        print("VERIFICANDO DATOS DESCARGADOS")
        print("-" * 35)
        
        try:
            for symbol in self.symbols:
                print(f"Verificando {symbol}...")
                
                # Obtener datos de la base de datos
                data = db_manager.get_market_data(
                    symbol=symbol,
                    limit=10
                )
                
                if not data.empty:
                    print(f"   Total: {len(data)} registros disponibles")
                    print(f"   Rango: {data.index.min()} - {data.index.max()}")
                else:
                    print(f"   Sin datos")
                
                print()
            
            # Estadísticas generales
            db_stats = db_manager.get_database_stats()
            print(f"Total registros en BD: {db_stats.get('total_records', 0):,}")
            print(f"Tamaño BD: {db_stats.get('file_size_mb', 0):.2f} MB")
            print()
            
        except Exception as e:
            logger.error(f"Error verificando datos: {e}")
            raise

async def main():
    """Función principal"""
    descarga = DescargaSimple()
    await descarga.ejecutar_descarga()

if __name__ == "__main__":
    print("TRADING BOT v10 - DESCARGA SIMPLE")
    print("=" * 50)
    print("Este script descargará datos históricos de 30 días")
    print("para probar el sistema antes de descargar 5 años.")
    print()
    
    input("Presiona Enter para continuar...")
    
    asyncio.run(main())
