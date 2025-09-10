#!/usr/bin/env python3
"""
Script para descarga extensa de datos históricos usando CCXT
Maneja las limitaciones de Bitget y descarga datos más antiguos
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

class ExtensiveHistoricalDownloader:
    """Descargador extenso de datos históricos usando CCXT"""
    
    def __init__(self):
        self.exchanges = {}
        self.base_path = Path("data/historical")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._setup_exchanges()
    
    def _setup_exchanges(self):
        """Configurar múltiples exchanges para obtener más datos"""
        try:
            # Bitget (principal)
            self.exchanges['bitget'] = ccxt.bitget({
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 100,
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                }
            })
            
            # Binance (para datos más antiguos)
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 50,
                'options': {
                    'defaultType': 'future',
                }
            })
            
            # Bybit (alternativa)
            self.exchanges['bybit'] = ccxt.bybit({
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 50,
            })
            
            logger.info("✅ Exchanges configurados: Bitget, Binance, Bybit")
            
        except Exception as e:
            logger.error(f"❌ Error configurando exchanges: {e}")
            self.exchanges = {}
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normaliza el símbolo para diferentes exchanges"""
        symbol = symbol.upper().strip()
        
        if not symbol.endswith('USDT') and not symbol.endswith('USD'):
            if symbol.endswith('BTC') or symbol.endswith('ETH'):
                symbol = symbol
            else:
                symbol = symbol + 'USDT'
        
        return symbol
    
    def _get_exchange_symbol(self, symbol: str, exchange_name: str) -> str:
        """Convierte símbolo al formato específico del exchange"""
        normalized = self._normalize_symbol(symbol)
        
        if exchange_name == 'bitget':
            if normalized.endswith('USDT'):
                base = normalized[:-4]
                return f"{base}/USDT:USDT"
            return normalized
        elif exchange_name == 'binance':
            if normalized.endswith('USDT'):
                base = normalized[:-4]
                return f"{base}/USDT"
            return normalized
        elif exchange_name == 'bybit':
            return normalized
        else:
            return normalized
    
    def create_symbol_database(self, symbol, timeframe):
        """Crear base de datos para un símbolo y timeframe específico"""
        try:
            symbol_dir = self.base_path / symbol
            symbol_dir.mkdir(exist_ok=True)
            
            db_path = symbol_dir / f"{symbol}_{timeframe}.db"
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ohlcv_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    exchange TEXT DEFAULT 'unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp)
                )
            ''')
            
            # Agregar columna exchange si no existe
            try:
                cursor.execute('ALTER TABLE ohlcv_data ADD COLUMN exchange TEXT DEFAULT "unknown"')
            except sqlite3.OperationalError:
                pass  # La columna ya existe
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON ohlcv_data(timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            return str(db_path)
            
        except Exception as e:
            logger.error(f"❌ Error creando base de datos para {symbol}_{timeframe}: {e}")
            return None
    
    async def download_from_exchange(self, exchange_name, symbol, timeframe, start_date, end_date, exchange):
        """Descargar datos desde un exchange específico"""
        try:
            ccxt_symbol = self._get_exchange_symbol(symbol, exchange_name)
            
            logger.info(f"📥 Descargando desde {exchange_name}: {symbol} {timeframe}")
            
            since = int(start_date.timestamp() * 1000)
            until = int(end_date.timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            # Descargar en chunks para evitar límites
            chunk_size = 1000
            max_retries = 3
            
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
                        wait_time = min(2 ** retries, 60)
                        logger.warning(f"Rate limit en {exchange_name}, esperando {wait_time}s")
                        await asyncio.sleep(wait_time)
                        
                    except Exception as e:
                        logger.warning(f"Error en {exchange_name}: {e}")
                        retries += 1
                        await asyncio.sleep(1)
                
                if not success:
                    logger.error(f"Falló descarga desde {exchange_name} después de {max_retries} intentos")
                    break
                
                # Pausa entre requests
                await asyncio.sleep(0.1)
            
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
    
    async def download_historical_data_extensive(self, symbol, timeframe, days_back=365):
        """Descarga datos históricos extensos desde múltiples exchanges"""
        try:
            if not self.exchanges:
                logger.error("No hay exchanges configurados")
                return pd.DataFrame()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"🚀 Descarga extensa: {symbol} {timeframe} desde {start_date.strftime('%Y-%m-%d')}")
            
            all_dataframes = []
            
            # Intentar descargar desde cada exchange
            for exchange_name, exchange in self.exchanges.items():
                try:
                    df = await self.download_from_exchange(
                        exchange_name, symbol, timeframe, start_date, end_date, exchange
                    )
                    
                    if not df.empty:
                        all_dataframes.append(df)
                        logger.info(f"📊 {exchange_name}: {len(df)} registros")
                    
                    # Pausa entre exchanges
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error con {exchange_name}: {e}")
                    continue
            
            if not all_dataframes:
                logger.warning(f"No se obtuvieron datos para {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Combinar datos de todos los exchanges
            logger.info(f"🔄 Combinando datos de {len(all_dataframes)} exchanges...")
            combined_df = pd.concat(all_dataframes, ignore_index=False)
            
            # Eliminar duplicados (mantener el más reciente)
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            combined_df = combined_df.sort_index()
            
            # Llenar gaps pequeños
            combined_df = combined_df.resample(timeframe).ffill().dropna()
            
            logger.info(f"✅ Datos combinados: {len(combined_df)} registros únicos")
            return combined_df
            
        except Exception as e:
            logger.error(f"❌ Error en descarga extensa: {e}")
            return pd.DataFrame()
    
    def save_ohlcv_data(self, df, symbol, timeframe):
        """Guardar datos OHLCV en la base de datos del símbolo"""
        try:
            if df.empty:
                logger.warning(f"DataFrame vacío para {symbol} {timeframe}")
                return 0
            
            db_path = self.create_symbol_database(symbol, timeframe)
            if not db_path:
                return 0
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
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

async def main():
    """Función principal"""
    try:
        logger.info("🚀 Iniciando descarga extensa de datos históricos...")
        
        # Leer configuración
        from config.config_loader import user_config
        
        symbols = user_config.get_symbols()
        timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'], ['1h', '4h', '1d'])
        years = user_config.get_value(['data_collection', 'historical', 'years'], 1)
        
        # Convertir años a días
        days_back = int(years * 365.25)
        
        logger.info(f"📊 Configuración:")
        logger.info(f"   Símbolos: {len(symbols)} ({', '.join(symbols)})")
        logger.info(f"   Timeframes: {len(timeframes)} ({', '.join(timeframes)})")
        logger.info(f"   Días hacia atrás: {days_back}")
        
        # Crear descargador
        downloader = ExtensiveHistoricalDownloader()
        
        total_records = 0
        
        # Descargar para cada símbolo y timeframe
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    logger.info(f"\n📈 Procesando {symbol} - {timeframe}")
                    
                    # Descargar datos extensos
                    df = await downloader.download_historical_data_extensive(symbol, timeframe, days_back)
                    
                    if not df.empty:
                        # Guardar en SQLite
                        saved = downloader.save_ohlcv_data(df, symbol, timeframe)
                        total_records += saved
                    else:
                        logger.warning(f"⚠️ No se obtuvieron datos para {symbol} {timeframe}")
                    
                    # Pausa entre descargas
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando {symbol} {timeframe}: {e}")
                    continue
        
        logger.info(f"\n✅ Descarga extensa completada!")
        logger.info(f"📊 Total de registros descargados: {total_records:,}")
        
    except Exception as e:
        logger.error(f"❌ Error durante la descarga: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
