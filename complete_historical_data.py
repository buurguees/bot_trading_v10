#!/usr/bin/env python3
"""
Script para completar datos históricos faltantes
Se enfoca en los símbolos que solo tienen ~90 días en lugar del año completo
"""

import asyncio
import sys
import os
import ccxt
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
import time

# Agregar el directorio raíz al path
sys.path.append('.')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HistoricalDataCompleter:
    """Completador de datos históricos faltantes"""
    
    def __init__(self):
        self.exchanges = {}
        self.base_path = Path("data/historical")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._setup_exchanges()
    
    def _setup_exchanges(self):
        """Configurar exchanges para obtener más datos"""
        try:
            # Binance (mejor para datos históricos largos)
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 50,
                'options': {
                    'defaultType': 'future',
                }
            })
            
            # Bybit (alternativa confiable)
            self.exchanges['bybit'] = ccxt.bybit({
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 50,
            })
            
            logger.info("✅ Exchanges configurados: Binance, Bybit")
            
        except Exception as e:
            logger.error(f"❌ Error configurando exchanges: {e}")
            self.exchanges = {}
    
    def _get_exchange_symbol(self, symbol: str, exchange_name: str) -> str:
        """Convierte símbolo al formato específico del exchange"""
        symbol = symbol.upper().strip()
        
        if exchange_name == 'binance':
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                return f"{base}/USDT"
            return symbol
        elif exchange_name == 'bybit':
            return symbol
        else:
            return symbol
    
    def get_existing_data_range(self, symbol, timeframe):
        """Obtiene el rango de datos existentes en la base de datos"""
        try:
            db_path = self.base_path / symbol / f"{symbol}_{timeframe}.db"
            if not db_path.exists():
                return None, None
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM ohlcv_data')
            min_ts, max_ts = cursor.fetchone()
            
            conn.close()
            
            if min_ts and max_ts:
                return datetime.fromtimestamp(min_ts), datetime.fromtimestamp(max_ts)
            return None, None
            
        except Exception as e:
            logger.error(f"Error obteniendo rango de datos para {symbol}_{timeframe}: {e}")
            return None, None
    
    async def download_missing_data(self, symbol, timeframe, start_date, end_date, exchange_name, exchange):
        """Descargar datos faltantes desde un exchange específico"""
        try:
            ccxt_symbol = self._get_exchange_symbol(symbol, exchange_name)
            
            logger.info(f"📥 Descargando desde {exchange_name}: {symbol} {timeframe} desde {start_date.strftime('%Y-%m-%d')}")
            
            since = int(start_date.timestamp() * 1000)
            until = int(end_date.timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            # Descargar en chunks más pequeños para mayor estabilidad
            chunk_size = 500
            max_retries = 5
            
            while current_since < until:
                retries = 0
                success = False
                
                while retries < max_retries and not success:
                    try:
                        # Usar run_in_executor para evitar bloqueos
                        ohlcv = await asyncio.get_event_loop().run_in_executor(
                            None,
                            exchange.fetch_ohlcv,
                            ccxt_symbol,
                            timeframe,
                            current_since,
                            chunk_size
                        )
                        
                        if not ohlcv:
                            break
                        
                        # Filtrar datos dentro del rango
                        filtered_data = [
                            candle for candle in ohlcv 
                            if since <= candle[0] <= until
                        ]
                        
                        if filtered_data:
                            all_data.extend(filtered_data)
                            current_since = filtered_data[-1][0] + 1
                        else:
                            current_since += chunk_size * self._get_timeframe_ms(timeframe)
                        
                        success = True
                        
                    except ccxt.RateLimitExceeded:
                        retries += 1
                        wait_time = min(2 ** retries, 30)
                        logger.warning(f"Rate limit en {exchange_name}, esperando {wait_time}s")
                        await asyncio.sleep(wait_time)
                        
                    except Exception as e:
                        logger.warning(f"Error en {exchange_name}: {e}")
                        retries += 1
                        await asyncio.sleep(2)
                
                if not success:
                    logger.error(f"Falló descarga desde {exchange_name} después de {max_retries} intentos")
                    break
                
                # Pausa entre requests
                await asyncio.sleep(0.2)
            
            if all_data:
                # Convertir a DataFrame
                df = pd.DataFrame(
                    all_data, 
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                df['symbol'] = symbol
                df['exchange'] = exchange_name
                
                logger.info(f"✅ {exchange_name}: {len(df)} registros para {symbol} {timeframe}")
                return df
            else:
                logger.warning(f"Sin datos de {exchange_name} para {symbol} {timeframe}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error descargando desde {exchange_name}: {e}")
            return pd.DataFrame()
    
    def _get_timeframe_ms(self, timeframe):
        """Convierte timeframe a milisegundos"""
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        return timeframe_minutes.get(timeframe, 60) * 60 * 1000
    
    def save_ohlcv_data(self, df, symbol, timeframe):
        """Guardar datos OHLCV en la base de datos del símbolo"""
        try:
            if df.empty:
                logger.warning(f"DataFrame vacío para {symbol} {timeframe}")
                return 0
            
            db_path = self.base_path / symbol / f"{symbol}_{timeframe}.db"
            if not db_path.exists():
                logger.error(f"Base de datos no existe: {db_path}")
                return 0
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Asegurar que la columna exchange existe
            try:
                cursor.execute('ALTER TABLE ohlcv_data ADD COLUMN exchange TEXT DEFAULT "unknown"')
            except sqlite3.OperationalError:
                pass  # La columna ya existe
            
            data_to_insert = []
            for timestamp, row in df.iterrows():
                data_to_insert.append((
                    int(timestamp.timestamp()),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    row.get('exchange', 'unknown')
                ))
            
            cursor.executemany('''
                INSERT OR REPLACE INTO ohlcv_data 
                (timestamp, open, high, low, close, volume, exchange)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data_to_insert)
            
            rows_inserted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"💾 Guardados {rows_inserted} registros para {symbol}_{timeframe}")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos para {symbol}_{timeframe}: {e}")
            return 0
    
    async def complete_historical_data(self, symbol, timeframe, target_days=365):
        """Completar datos históricos para un símbolo y timeframe específico"""
        try:
            if not self.exchanges:
                logger.error("No hay exchanges configurados")
                return False
            
            # Obtener rango de datos existentes
            min_date, max_date = self.get_existing_data_range(symbol, timeframe)
            
            if not min_date or not max_date:
                logger.warning(f"No hay datos existentes para {symbol}_{timeframe}")
                return False
            
            # Calcular fechas objetivo
            end_date = datetime.now()
            start_date = end_date - timedelta(days=target_days)
            
            logger.info(f"📊 {symbol}_{timeframe}:")
            logger.info(f"   Datos existentes: {min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')}")
            logger.info(f"   Objetivo: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            
            # Determinar qué datos faltan
            missing_data = []
            
            # Datos antes del rango existente
            if min_date > start_date:
                missing_data.append((start_date, min_date))
                logger.info(f"   📥 Faltan datos desde {start_date.strftime('%Y-%m-%d')} hasta {min_date.strftime('%Y-%m-%d')}")
            
            # Datos después del rango existente
            if max_date < end_date:
                missing_data.append((max_date, end_date))
                logger.info(f"   📥 Faltan datos desde {max_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")
            
            if not missing_data:
                logger.info(f"   ✅ {symbol}_{timeframe} ya tiene datos completos")
                return True
            
            # Descargar datos faltantes
            total_saved = 0
            for start, end in missing_data:
                logger.info(f"   🔄 Descargando datos de {start.strftime('%Y-%m-%d')} a {end.strftime('%Y-%m-%d')}")
                
                for exchange_name, exchange in self.exchanges.items():
                    try:
                        df = await self.download_missing_data(symbol, timeframe, start, end, exchange_name, exchange)
                        
                        if not df.empty:
                            saved = self.save_ohlcv_data(df, symbol, timeframe)
                            total_saved += saved
                            break  # Usar solo el primer exchange exitoso
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error con {exchange_name}: {e}")
                        continue
            
            logger.info(f"   ✅ {symbol}_{timeframe}: {total_saved} registros adicionales guardados")
            return total_saved > 0
            
        except Exception as e:
            logger.error(f"❌ Error completando datos para {symbol}_{timeframe}: {e}")
            return False

async def main():
    """Función principal"""
    try:
        logger.info("🚀 Iniciando completado de datos históricos...")
        
        # Leer configuración
        from config.config_loader import user_config
        
        symbols = user_config.get_symbols()
        timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'], ['1h', '4h', '1d'])
        years = user_config.get_value(['data_collection', 'historical', 'years'], 1)
        
        # Convertir años a días
        target_days = int(years * 365.25)
        
        logger.info(f"📊 Configuración:")
        logger.info(f"   Símbolos: {len(symbols)} ({', '.join(symbols)})")
        logger.info(f"   Timeframes: {len(timeframes)} ({', '.join(timeframes)})")
        logger.info(f"   Días objetivo: {target_days}")
        
        # Crear completador
        completer = HistoricalDataCompleter()
        
        total_completed = 0
        
        # Completar datos para cada símbolo y timeframe
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    logger.info(f"\n📈 Completando {symbol} - {timeframe}")
                    
                    success = await completer.complete_historical_data(symbol, timeframe, target_days)
                    if success:
                        total_completed += 1
                    
                    # Pausa entre descargas
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando {symbol} {timeframe}: {e}")
                    continue
        
        logger.info(f"\n✅ Completado de datos históricos finalizado!")
        logger.info(f"📊 Símbolos/timeframes completados: {total_completed}")
        
    except Exception as e:
        logger.error(f"❌ Error durante el completado: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
