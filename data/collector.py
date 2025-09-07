"""
data/collector.py - VERSIÓN CORREGIDA
Recolector de datos de mercado desde Bitget API
Ubicación: C:\TradingBot_v10\data\collector.py

CAMBIOS PRINCIPALES:
- Manejo correcto de símbolos sin credenciales de API
- Método save_historical_data implementado correctamente
- Mejor manejo de errores y logging
- Soporte para modo sin credenciales (usando datos públicos)
"""

import asyncio
import websockets
import json
import hmac
import hashlib
import base64
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
import pandas as pd
import ccxt
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
import aiohttp
import ssl

from .database import db_manager, MarketData
from config.config_loader import user_config

logger = logging.getLogger(__name__)

@dataclass
class BitgetCredentials:
    """Credenciales de Bitget API"""
    api_key: str
    secret_key: str
    passphrase: str
    
    @property
    def is_valid(self) -> bool:
        return bool(self.api_key and self.secret_key)

class BitgetDataCollector:
    """Recolector de datos de Bitget"""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.exchange = None
        self.websocket = None
        self.running = False
        self.tick_callbacks = []
        self.kline_callbacks = []
        self._setup_exchange()
    
    def _load_credentials(self) -> BitgetCredentials:
        """Carga credenciales desde variables de entorno"""
        return BitgetCredentials(
            api_key=os.getenv("BITGET_API_KEY", ""),
            secret_key=os.getenv("BITGET_SECRET_KEY", ""),
            passphrase=os.getenv("BITGET_PASSPHRASE", "")
        )
    
    def _setup_exchange(self):
        """Configura el exchange CCXT"""
        try:
            # Configurar exchange sin credenciales para datos públicos
            config = {
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'swap',  # Usar futuros por defecto
                }
            }
            
            # Añadir credenciales solo si están disponibles
            if self.credentials.is_valid:
                config.update({
                    'apiKey': self.credentials.api_key,
                    'secret': self.credentials.secret_key,
                    'password': self.credentials.passphrase,
                })
                logger.info("Exchange configurado con credenciales")
            else:
                logger.info("Exchange configurado sin credenciales (solo datos públicos)")
            
            self.exchange = ccxt.bitget(config)
            
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            self.exchange = None
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normaliza el símbolo para Bitget"""
        # Convertir BTCUSDT a BTCUSDT para futuros
        if '/' not in symbol and symbol.endswith('USDT'):
            return symbol  # Ya está en formato correcto para futuros
        elif '/' in symbol:
            return symbol.replace('/', '')  # BTC/USDT -> BTCUSDT
        return symbol
    
    def _symbol_to_ccxt_format(self, symbol: str) -> str:
        """Convierte símbolo a formato CCXT"""
        normalized = self._normalize_symbol(symbol)
        if normalized.endswith('USDT'):
            base = normalized[:-4]  # Quitar USDT
            return f"{base}/USDT"
        return normalized
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica el estado del recolector"""
        health = {
            'credentials_configured': self.credentials.is_valid,
            'exchange_configured': self.exchange is not None,
            'rest_api_ok': False,
            'websocket_ok': False,
            'data_freshness_ok': False
        }
        
        try:
            # Verificar API REST
            if self.exchange:
                try:
                    # Probar con un símbolo conocido
                    ticker = await asyncio.get_event_loop().run_in_executor(
                        None, self.exchange.fetch_ticker, 'BTC/USDT'
                    )
                    health['rest_api_ok'] = True
                    logger.debug("API REST funcionando correctamente")
                except Exception as e:
                    logger.warning(f"API REST limitada: {e}")
                    # Intentar sin credenciales
                    try:
                        exchange_public = ccxt.bitget({'enableRateLimit': True})
                        ticker = await asyncio.get_event_loop().run_in_executor(
                            None, exchange_public.fetch_ticker, 'BTC/USDT'
                        )
                        health['rest_api_ok'] = True
                        logger.debug("API REST pública funcionando")
                    except Exception as e2:
                        logger.error(f"API REST no disponible: {e2}")
            
            # Verificar WebSocket
            health['websocket_ok'] = self.websocket is not None and not self.websocket.closed
            
            # Verificar frescura de datos
            latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
            if not latest_data.empty:
                last_update = latest_data.index[-1]
                if hasattr(last_update, 'tz_localize'):
                    last_update = last_update.tz_localize(None) if last_update.tz is None else last_update.tz_convert(None)
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                health['data_freshness_ok'] = hours_since_update < 2  # Datos de menos de 2 horas
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
        
        return health
    
    async def fetch_historical_data(self, symbol: str, timeframe: str = "1h", 
                                  days_back: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos con manejo robusto de errores"""
        try:
            if not self.exchange:
                logger.error("Exchange no configurado")
                return pd.DataFrame()
            
            # Normalizar símbolo
            ccxt_symbol = self._symbol_to_ccxt_format(symbol)
            original_symbol = self._normalize_symbol(symbol)
            
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"📥 Descargando {symbol} ({ccxt_symbol}) - {timeframe} - {days_back} días")
            
            all_data = []
            current_start = start_date
            limit = 1000  # Límite más alto para descargas extensas
            max_attempts = 50  # Más intentos para cubrir 3 años
            attempts = 0
            
            while current_start < end_date and attempts < max_attempts:
                try:
                    attempts += 1
                    
                    # Obtener datos usando CCXT
                    since = int(current_start.timestamp() * 1000)
                    
                    logger.debug(f"Intento {attempts}: descargando desde {current_start}")
                    
                    ohlcv = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.exchange.fetch_ohlcv(
                            ccxt_symbol,
                            timeframe,
                            since,
                            limit
                        )
                    )
                    
                    if not ohlcv:
                        logger.warning(f"Sin datos en intento {attempts}")
                        break
                    
                    logger.debug(f"Obtenidos {len(ohlcv)} registros")
                    all_data.extend(ohlcv)
                    
                    # Log de progreso cada 10 intentos
                    if attempts % 10 == 0:
                        total_records = len(all_data)
                        progress_days = (current_start - start_date).days
                        total_days = (end_date - start_date).days
                        progress_pct = (progress_days / total_days) * 100 if total_days > 0 else 0
                        logger.info(f"📊 Progreso {symbol}: {total_records:,} registros, {progress_days}/{total_days} días ({progress_pct:.1f}%)")
                    
                    # Actualizar fecha de inicio para la siguiente iteración
                    if len(ohlcv) > 0:
                        last_timestamp = ohlcv[-1][0]
                        # Calcular el siguiente período basado en el timeframe
                        if timeframe == '1h':
                            time_delta = timedelta(hours=1)
                        elif timeframe == '4h':
                            time_delta = timedelta(hours=4)
                        elif timeframe == '1d':
                            time_delta = timedelta(days=1)
                        else:
                            time_delta = timedelta(hours=1)  # Default a 1h
                        
                        current_start = datetime.fromtimestamp(last_timestamp / 1000) + time_delta
                        
                        # Verificar si hemos alcanzado la fecha final
                        if current_start >= end_date:
                            break
                    else:
                        # Si no hay más datos, avanzar un período
                        if timeframe == '1h':
                            current_start += timedelta(hours=limit)
                        elif timeframe == '4h':
                            current_start += timedelta(hours=limit * 4)
                        elif timeframe == '1d':
                            current_start += timedelta(days=limit)
                        else:
                            current_start += timedelta(hours=limit)
                        
                        # Si hemos pasado la fecha final, terminar
                        if current_start >= end_date:
                            break
                    
                    # Pausa para evitar rate limiting
                    await asyncio.sleep(0.2)
                    
                except ccxt.RateLimitExceeded:
                    logger.warning("Rate limit alcanzado, esperando...")
                    await asyncio.sleep(2)
                    continue
                    
                except ccxt.NetworkError as e:
                    logger.warning(f"Error de red en intento {attempts}: {e}")
                    await asyncio.sleep(1)
                    continue
                    
                except Exception as e:
                    logger.error(f"Error en paginación intento {attempts}: {e}")
                    break
            
            if not all_data:
                logger.error(f"❌ No se obtuvieron datos para {symbol}")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['symbol'] = original_symbol
            
            # Eliminar duplicados y ordenar
            df = df[~df.index.duplicated(keep='first')]
            df = df.sort_index()
            
            # Filtrar por rango de fechas solicitado
            df = df[df.index >= start_date]
            df = df[df.index <= end_date]
            
            logger.info(f"✅ Descargados {len(df)} registros para {symbol} ({df.index.min()} a {df.index.max()})")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos históricos para {symbol}: {e}")
            return pd.DataFrame()
    
    async def save_historical_data(self, df: pd.DataFrame) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                logger.warning("DataFrame vacío, no hay nada que guardar")
                return 0
            
            # DEBUG: Información del DataFrame
            logger.info(f"🔍 DEBUG: DataFrame creado con {len(df)} filas")
            logger.info(f"🔍 DEBUG: Columnas: {df.columns.tolist()}")
            logger.info(f"🔍 DEBUG: Primeras 3 filas:")
            logger.info(f"{df.head(3)}")
            
            saved_count = 0
            errors = 0
            
            logger.info(f"💾 Guardando {len(df)} registros en base de datos...")
            
            # Convertir DataFrame a lista de objetos MarketData para bulk save
            market_data_list = []
            
            for timestamp, row in df.iterrows():
                try:
                    # Crear objeto MarketData
                    market_data = MarketData(
                        symbol=row['symbol'],
                        timestamp=int(timestamp.timestamp()),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    market_data_list.append(market_data)
                        
                except Exception as e:
                    logger.error(f"Error creando objeto MarketData para {timestamp}: {e}")
                    errors += 1
                    continue
            
            # Usar bulk save para mejor rendimiento
            if market_data_list:
                saved_count = db_manager.bulk_save_market_data(market_data_list)
                logger.info(f"✅ Bulk save completado: {saved_count} registros guardados")
            else:
                logger.warning("No se crearon objetos MarketData válidos")
            
            if errors > 0:
                logger.warning(f"⚠️ {errors} errores al procesar datos")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos históricos: {e}")
            return 0
    
    def add_tick_callback(self, callback: Callable):
        """Añade callback para datos de tick"""
        self.tick_callbacks.append(callback)
    
    def add_kline_callback(self, callback: Callable):
        """Añade callback para datos de kline"""
        self.kline_callbacks.append(callback)
    
    async def start_websocket_stream(self):
        """Inicia el stream de WebSocket"""
        try:
            if not self.credentials.is_valid:
                logger.warning("Sin credenciales para WebSocket, solo datos históricos disponibles")
                return
            
            self.running = True
            logger.info("🔄 Iniciando stream de WebSocket...")
            
            # URL del WebSocket de Bitget
            ws_url = "wss://ws.bitget.com/spot/v1/stream"
            
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                
                # Suscribirse a datos
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [
                        {
                            "channel": "ticker",
                            "instId": "BTCUSDT"
                        }
                    ]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        if 'data' in data:
                            await self._handle_websocket_message(data['data'])
                            
                    except asyncio.TimeoutError:
                        # Ping para mantener conexión
                        await websocket.ping()
                        continue
                        
                    except Exception as e:
                        logger.error(f"Error en WebSocket: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error iniciando WebSocket: {e}")
    
    async def _handle_websocket_message(self, data):
        """Maneja mensajes del WebSocket"""
        try:
            # Procesar datos de tick o kline según el tipo
            pass  # Implementar según necesidades específicas
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    def stop_websocket_stream(self):
        """Detiene el stream de WebSocket"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia global del recolector
data_collector = BitgetDataCollector()

async def collect_and_save_historical_data(symbol: str, timeframe: str = "1h", 
                                         days_back: int = 30) -> int:
    """
    Función helper para recolectar y guardar datos históricos
    
    Args:
        symbol: Símbolo del activo (ej: BTCUSDT)
        timeframe: Marco temporal (1h, 4h, 1d)
        days_back: Días hacia atrás
    
    Returns:
        Número de registros guardados
    """
    try:
        logger.info(f"🚀 Iniciando recolección: {symbol} - {timeframe} - {days_back} días")
        
        # Obtener datos históricos
        df = await data_collector.fetch_historical_data(symbol, timeframe, days_back)
        
        if df.empty:
            logger.error(f"❌ No se obtuvieron datos para {symbol}")
            return 0
        
        # Guardar en base de datos
        saved_count = await data_collector.save_historical_data(df)
        
        logger.info(f"✅ Proceso completado: {saved_count} registros guardados para {symbol}")
        return saved_count
        
    except Exception as e:
        logger.error(f"❌ Error en recolección completa para {symbol}: {e}")
        return 0

async def download_extensive_historical_data_chunked(symbols: List[str] = None, 
                                                   years: int = 2, 
                                                   timeframe: str = "1h") -> Dict[str, int]:
    """
    Descarga datos históricos en chunks para evitar límites de API
    """
    try:
        if symbols is None:
            try:
                config_data = user_config.config
                symbols = config_data.get('bot_settings', {}).get('main_symbols', 
                                                                 ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
            except:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        logger.info(f"🚀 Iniciando descarga extensa por chunks: {len(symbols)} símbolos, {years} años")
        
        results = {}
        total_downloaded = 0
        
        for symbol in symbols:
            logger.info(f"📥 Procesando {symbol} en chunks...")
            
            try:
                # Descargar en chunks de 6 meses para evitar límites
                chunk_months = 6
                total_chunks = (years * 12) // chunk_months
                if (years * 12) % chunk_months > 0:
                    total_chunks += 1
                
                symbol_total = 0
                
                for chunk in range(total_chunks):
                    chunk_start_months = chunk * chunk_months
                    chunk_end_months = min((chunk + 1) * chunk_months, years * 12)
                    
                    # Calcular días para este chunk
                    chunk_days = (chunk_end_months - chunk_start_months) * 30
                    
                    logger.info(f"📦 Chunk {chunk + 1}/{total_chunks}: {chunk_days} días")
                    
                    downloaded = await collect_and_save_historical_data(symbol, timeframe, chunk_days)
                    symbol_total += downloaded
                    
                    logger.info(f"✅ Chunk {chunk + 1}: {downloaded:,} registros")
                    
                    # Pausa entre chunks
                    await asyncio.sleep(2)
                
                results[symbol] = symbol_total
                total_downloaded += symbol_total
                
                # Calcular cobertura
                expected_records = years * 365 * 24 if timeframe == '1h' else years * 365 * 6 if timeframe == '4h' else years * 365
                coverage_pct = (symbol_total / expected_records) * 100 if expected_records > 0 else 0
                
                logger.info(f"✅ {symbol}: {symbol_total:,} registros totales ({coverage_pct:.1f}% cobertura)")
                
                # Pausa entre símbolos
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error descargando {symbol}: {e}")
                results[symbol] = 0
        
        logger.info(f"🎉 Descarga por chunks completada: {total_downloaded} registros totales")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga por chunks: {e}")
        return {}

async def download_extensive_historical_data(symbols: List[str] = None, 
                                           years: int = 2, 
                                           timeframe: str = "1h") -> Dict[str, int]:
    """
    Descarga datos históricos extensos para múltiples símbolos
    Reemplaza la funcionalidad de scripts/descargar_historico_*.py
    
    Args:
        symbols: Lista de símbolos a descargar (default: símbolos principales)
        years: Años de datos históricos a descargar
        timeframe: Marco temporal (1h, 4h, 1d)
    
    Returns:
        Diccionario con resultados por símbolo
    """
    try:
        if symbols is None:
            # Usar símbolos principales de la configuración
            try:
                config_data = user_config.config
                symbols = config_data.get('bot_settings', {}).get('main_symbols', 
                                                                 ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
            except:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # Para 3+ años, usar descarga por chunks para evitar límites de API
        if years >= 3:
            logger.info(f"🔄 Usando descarga por chunks para {years} años")
            return await download_extensive_historical_data_chunked(symbols, years, timeframe)
        
        logger.info(f"🚀 Iniciando descarga extensa: {len(symbols)} símbolos, {years} años")
        
        results = {}
        total_downloaded = 0
        
        for symbol in symbols:
            logger.info(f"📥 Procesando {symbol}...")
            
            try:
                # Descargar datos por períodos para evitar límites de API
                days_back = years * 365
                logger.info(f"🎯 Objetivo: {days_back} días de datos históricos para {symbol}")
                
                downloaded = await collect_and_save_historical_data(symbol, timeframe, days_back)
                
                results[symbol] = downloaded
                total_downloaded += downloaded
                
                # Calcular días reales descargados
                expected_records = days_back * 24 if timeframe == '1h' else days_back * 6 if timeframe == '4h' else days_back
                coverage_pct = (downloaded / expected_records) * 100 if expected_records > 0 else 0
                
                logger.info(f"✅ {symbol}: {downloaded:,} registros descargados ({coverage_pct:.1f}% cobertura)")
                
                # Pausa entre descargas para respetar límites de API
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error descargando {symbol}: {e}")
                results[symbol] = 0
        
        logger.info(f"🎉 Descarga completada: {total_downloaded} registros totales")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga extensa: {e}")
        return {}

async def download_missing_data(symbols: List[str] = None, 
                              target_days: int = 365) -> Dict[str, Any]:
    """
    Descarga solo los datos faltantes para completar el histórico
    Reemplaza funcionalidad de scripts de verificación y descarga
    
    Args:
        symbols: Lista de símbolos a verificar
        target_days: Días objetivo de datos históricos
    
    Returns:
        Diccionario con resultados de verificación y descarga
    """
    try:
        if symbols is None:
            try:
                config_data = user_config.config
                symbols = config_data.get('bot_settings', {}).get('main_symbols', 
                                                                 ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
            except:
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        results = {
            'symbols_checked': len(symbols),
            'symbols_ok': 0,
            'symbols_updated': 0,
            'total_downloaded': 0,
            'details': {}
        }
        
        for symbol in symbols:
            logger.info(f"🔍 Verificando {symbol}...")
            
            try:
                # Verificar datos existentes
                from .database import db_manager
                summary = db_manager.get_historical_data_summary()
                
                symbol_info = next((s for s in summary['symbols'] if s['symbol'] == symbol), None)
                
                if symbol_info and symbol_info['status'] == 'OK':
                    current_days = symbol_info['duration_days']
                    
                    if current_days >= target_days:
                        results['symbols_ok'] += 1
                        results['details'][symbol] = {
                            'status': 'OK',
                            'current_days': current_days,
                            'message': f'Ya tiene {current_days} días de datos'
                        }
                    else:
                        # Descargar datos faltantes
                        missing_days = target_days - current_days
                        downloaded = await collect_and_save_historical_data(symbol, "1h", missing_days)
                        
                        results['symbols_updated'] += 1
                        results['total_downloaded'] += downloaded
                        results['details'][symbol] = {
                            'status': 'UPDATED',
                            'current_days': current_days,
                            'missing_days': missing_days,
                            'downloaded': downloaded
                        }
                else:
                    # No hay datos, descargar completo
                    downloaded = await collect_and_save_historical_data(symbol, "1h", target_days)
                    
                    results['symbols_updated'] += 1
                    results['total_downloaded'] += downloaded
                    results['details'][symbol] = {
                        'status': 'NEW',
                        'downloaded': downloaded,
                        'message': 'Datos descargados desde cero'
                    }
                
            except Exception as e:
                logger.error(f"❌ Error verificando {symbol}: {e}")
                results['details'][symbol] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en verificación de datos faltantes: {e}")
        return {'error': str(e)}