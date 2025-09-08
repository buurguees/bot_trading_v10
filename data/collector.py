"""
data/collector.py - VERSIÓN PROFESIONAL MEJORADA
Recolector de datos de mercado desde Bitget API
Ubicación: C:\TradingBot_v10\data\collector.py

MEJORAS PRINCIPALES:
- Gestión robusta de timestamps (milisegundos/segundos)
- Descarga eficiente de 5+ años de datos históricos
- Rate limiting inteligente y backoff exponencial
- Validación y limpieza automática de datos
- Recuperación de errores y reintentos
- Progress tracking detallado
- Soporte para múltiples timeframes simultáneos
"""

import asyncio
import websockets
import json
import hmac
import hashlib
import base64
import time
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable, Any, Union
import logging
import pandas as pd
import ccxt
import aiohttp
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import numpy as np
from pathlib import Path
import threading
from itertools import chain

from .database import db_manager, MarketData
from config.config_loader import user_config

logger = logging.getLogger(__name__)

@dataclass
class BitgetCredentials:
    """Credenciales de Bitget API con validación"""
    api_key: str
    secret_key: str
    passphrase: str
    
    @property
    def is_valid(self) -> bool:
        return bool(self.api_key and self.secret_key and self.passphrase)
    
    @property
    def is_sandbox(self) -> bool:
        """Detecta si son credenciales de sandbox"""
        return 'sandbox' in self.api_key.lower() or 'test' in self.api_key.lower()

@dataclass
class DownloadProgress:
    """Tracker de progreso de descarga"""
    symbol: str
    total_periods: int = 0
    downloaded_periods: int = 0
    total_records: int = 0
    start_time: datetime = None
    errors: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    @property
    def progress_pct(self) -> float:
        return (self.downloaded_periods / self.total_periods * 100) if self.total_periods > 0 else 0
    
    @property
    def elapsed_time(self) -> timedelta:
        return datetime.now() - self.start_time
    
    @property
    def estimated_remaining(self) -> timedelta:
        if self.downloaded_periods == 0:
            return timedelta(seconds=0)
        time_per_period = self.elapsed_time / self.downloaded_periods
        remaining_periods = self.total_periods - self.downloaded_periods
        return time_per_period * remaining_periods

class TimeframeManager:
    """Gestor de timeframes con conversiones precisas"""
    
    TIMEFRAME_MINUTES = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '2h': 120,
        '4h': 240,
        '6h': 360,
        '8h': 480,
        '12h': 720,
        '1d': 1440,
        '3d': 4320,
        '1w': 10080,
        '1M': 43200  # Aproximado
    }
    
    @classmethod
    def to_minutes(cls, timeframe: str) -> int:
        """Convierte timeframe a minutos"""
        return cls.TIMEFRAME_MINUTES.get(timeframe, 60)
    
    @classmethod
    def to_timedelta(cls, timeframe: str) -> timedelta:
        """Convierte timeframe a timedelta"""
        return timedelta(minutes=cls.to_minutes(timeframe))
    
    @classmethod
    def calculate_periods_needed(cls, timeframe: str, days: int) -> int:
        """Calcula períodos necesarios para N días"""
        minutes_per_day = 1440
        minutes_per_period = cls.to_minutes(timeframe)
        return int((days * minutes_per_day) / minutes_per_period)
    
    @classmethod
    def is_valid_timeframe(cls, timeframe: str) -> bool:
        """Valida si el timeframe es soportado"""
        return timeframe in cls.TIMEFRAME_MINUTES

class TimestampManager:
    """Gestor de timestamps con normalización automática"""
    
    @staticmethod
    def normalize_timestamp(timestamp: Union[int, float, str, datetime]) -> int:
        """Normaliza timestamp a segundos Unix"""
        try:
            if isinstance(timestamp, datetime):
                return int(timestamp.timestamp())
            elif isinstance(timestamp, str):
                dt = pd.to_datetime(timestamp)
                return int(dt.timestamp())
            elif isinstance(timestamp, (int, float)):
                # Detectar si está en milisegundos
                if timestamp > 10000000000:  # Timestamp en ms
                    return int(timestamp / 1000)
                else:  # Timestamp en segundos
                    return int(timestamp)
            else:
                raise ValueError(f"Tipo de timestamp no soportado: {type(timestamp)}")
        except Exception as e:
            logger.error(f"Error normalizando timestamp {timestamp}: {e}")
            return int(time.time())
    
    @staticmethod
    def validate_timestamp_range(timestamp: int, 
                                min_year: int = 2010, 
                                max_year: int = None) -> bool:
        """Valida que el timestamp esté en un rango razonable"""
        if max_year is None:
            max_year = datetime.now().year + 1
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return min_year <= dt.year <= max_year
        except (ValueError, OSError):
            return False
    
    @staticmethod
    def to_datetime(timestamp: int) -> datetime:
        """Convierte timestamp normalizado a datetime"""
        try:
            return datetime.fromtimestamp(timestamp)
        except (ValueError, OSError) as e:
            logger.error(f"Error convirtiendo timestamp {timestamp}: {e}")
            return datetime.now()

class DataValidator:
    """Validador de datos de mercado"""
    
    @staticmethod
    def validate_ohlcv_data(data: Dict[str, float], symbol: str) -> bool:
        """Valida datos OHLCV básicos"""
        try:
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            
            # Verificar que todos los campos están presentes
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.warning(f"Campo faltante {field} en {symbol}")
                    return False
            
            # Validar que los precios son positivos
            for field in ['open', 'high', 'low', 'close']:
                if data[field] <= 0:
                    logger.warning(f"Precio inválido {field}={data[field]} en {symbol}")
                    return False
            
            # Validar relación High >= Low
            if data['high'] < data['low']:
                logger.warning(f"High < Low en {symbol}: {data['high']} < {data['low']}")
                return False
            
            # Validar que Open y Close están dentro del rango High-Low
            if not (data['low'] <= data['open'] <= data['high']):
                logger.warning(f"Open fuera de rango en {symbol}")
                return False
            
            if not (data['low'] <= data['close'] <= data['high']):
                logger.warning(f"Close fuera de rango en {symbol}")
                return False
            
            # Validar volumen no negativo
            if data['volume'] < 0:
                logger.warning(f"Volumen negativo en {symbol}: {data['volume']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando datos OHLCV: {e}")
            return False
    
    @staticmethod
    def detect_and_fix_gaps(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Detecta y corrige gaps en los datos"""
        try:
            if df.empty:
                return df
            
            # Calcular frecuencia esperada
            freq_minutes = TimeframeManager.to_minutes(timeframe)
            expected_freq = f"{freq_minutes}T"
            
            # Crear índice completo
            full_index = pd.date_range(
                start=df.index.min(),
                end=df.index.max(),
                freq=expected_freq
            )
            
            # Reindexar con forward fill para gaps pequeños
            df_filled = df.reindex(full_index)
            
            # Solo llenar gaps pequeños (menos de 5 períodos)
            df_filled = df_filled.ffill(limit=5)
            
            gaps_filled = df_filled.isna().sum().sum()
            if gaps_filled > 0:
                logger.info(f"Gaps detectados y parcialmente llenados: {gaps_filled}")
            
            # Remover filas que no se pudieron llenar
            df_filled = df_filled.dropna()
            
            return df_filled
            
        except Exception as e:
            logger.error(f"Error corrigiendo gaps: {e}")
            return df

class BitgetDataCollector:
    """Recolector de datos profesional de Bitget"""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.exchange = None
        self.websocket = None
        self.running = False
        self.tick_callbacks = []
        self.kline_callbacks = []
        self.rate_limiter = asyncio.Semaphore(10)  # Max 10 requests concurrentes
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms entre requests
        self._setup_exchange()
        
        # Configuración de descarga extensiva
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        self.chunk_size = 1000
        self.concurrent_downloads = 3
        
        logger.info("BitgetDataCollector inicializado con configuración robusta")
    
    def _load_credentials(self) -> BitgetCredentials:
        """Carga credenciales con validación"""
        credentials = BitgetCredentials(
            api_key=os.getenv("BITGET_API_KEY", ""),
            secret_key=os.getenv("BITGET_SECRET_KEY", ""),
            passphrase=os.getenv("BITGET_PASSPHRASE", "")
        )
        
        if credentials.is_valid:
            logger.info(f"Credenciales cargadas - Tipo: {'Sandbox' if credentials.is_sandbox else 'Producción'}")
        else:
            logger.warning("Credenciales no configuradas - Solo datos públicos disponibles")
        
        return credentials
    
    def _setup_exchange(self):
        """Configura el exchange CCXT con configuración optimizada"""
        try:
            config = {
                'enableRateLimit': True,
                'timeout': 30000,
                'rateLimit': 100,  # ms between requests
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                },
                'headers': {
                    'User-Agent': 'TradingBot_v10/1.0'
                }
            }
            
            if self.credentials.is_valid:
                config.update({
                    'apiKey': self.credentials.api_key,
                    'secret': self.credentials.secret_key,
                    'password': self.credentials.passphrase,
                })
            
            # Usar sandbox si las credenciales son de sandbox
            if self.credentials.is_sandbox:
                config['sandbox'] = True
            
            self.exchange = ccxt.bitget(config)
            
            # Test de conectividad
            asyncio.create_task(self._test_connectivity())
            
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            self.exchange = None
    
    async def _test_connectivity(self):
        """Test de conectividad básico"""
        try:
            if self.exchange:
                markets = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.load_markets
                )
                logger.info(f"Conectividad OK - {len(markets)} mercados disponibles")
        except Exception as e:
            logger.warning(f"Test de conectividad falló: {e}")
    
    async def _rate_limited_request(self, request_func, *args, **kwargs):
        """Ejecuta request con rate limiting"""
        async with self.rate_limiter:
            # Respetar intervalo mínimo entre requests
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            
            self.last_request_time = time.time()
            
            # Crear una función wrapper para manejar los parámetros correctamente
            def wrapper():
                return request_func(*args, **kwargs)
            
            return await asyncio.get_event_loop().run_in_executor(
                None, wrapper
            )
    
    async def _exponential_backoff_retry(self, request_func, *args, max_retries=5, **kwargs):
        """Retry con backoff exponencial"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self._rate_limited_request(request_func, *args, **kwargs)
                
            except ccxt.RateLimitExceeded as e:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"Rate limit alcanzado, esperando {delay}s (intento {attempt + 1})")
                await asyncio.sleep(delay)
                last_exception = e
                
            except ccxt.NetworkError as e:
                delay = min(self.base_delay * (2 ** attempt), 10.0)
                logger.warning(f"Error de red, reintentando en {delay}s (intento {attempt + 1})")
                await asyncio.sleep(delay)
                last_exception = e
                
            except ccxt.ExchangeError as e:
                if "Invalid symbol" in str(e):
                    logger.error(f"Símbolo inválido: {e}")
                    raise
                delay = min(self.base_delay * (2 ** attempt), 5.0)
                logger.warning(f"Error de exchange, reintentando en {delay}s: {e}")
                await asyncio.sleep(delay)
                last_exception = e
                
            except Exception as e:
                logger.error(f"Error no recuperable: {e}")
                raise
        
        # Si llegamos aquí, se agotaron los reintentos
        logger.error(f"Máximo de reintentos alcanzado: {last_exception}")
        raise last_exception
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normaliza el símbolo para Bitget"""
        symbol = symbol.upper().strip()
        
        # Convertir diferentes formatos a formato estándar
        if '/' in symbol:
            symbol = symbol.replace('/', '')
        
        # Asegurar que termine en USDT para futuros
        if not symbol.endswith('USDT') and not symbol.endswith('USD'):
            if symbol.endswith('BTC') or symbol.endswith('ETH'):
                symbol = symbol  # Mantener como está
            else:
                symbol = symbol + 'USDT'
        
        return symbol
    
    def _symbol_to_ccxt_format(self, symbol: str) -> str:
        """Convierte símbolo a formato CCXT"""
        normalized = self._normalize_symbol(symbol)
        
        # Para futuros USDT
        if normalized.endswith('USDT'):
            base = normalized[:-4]
            return f"{base}/USDT:USDT"
        elif normalized.endswith('USD'):
            base = normalized[:-3]
            return f"{base}/USD:USD"
        
        return normalized
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check completo del sistema"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'credentials_configured': self.credentials.is_valid,
            'exchange_configured': self.exchange is not None,
            'rest_api_ok': False,
            'websocket_ok': False,
            'data_freshness_ok': False,
            'database_ok': False,
            'details': {}
        }
        
        try:
            # Test REST API
            if self.exchange:
                try:
                    ticker = await self._rate_limited_request(
                        self.exchange.fetch_ticker, 'BTC/USDT:USDT'
                    )
                    health['rest_api_ok'] = True
                    health['details']['last_price_btc'] = ticker.get('last', 0)
                except Exception as e:
                    health['details']['rest_api_error'] = str(e)
            
            # Test WebSocket
            health['websocket_ok'] = (self.websocket is not None and 
                                    not getattr(self.websocket, 'closed', True))
            
            # Test base de datos
            try:
                stats = db_manager.get_database_stats()
                health['database_ok'] = True
                health['details']['database_records'] = stats.get('total_records', 0)
            except Exception as e:
                health['details']['database_error'] = str(e)
            
            # Test frescura de datos
            try:
                latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
                if not latest_data.empty:
                    last_update = latest_data.index[-1]
                    if hasattr(last_update, 'tz_localize'):
                        last_update = (last_update.tz_localize(None) 
                                     if last_update.tz is None 
                                     else last_update.tz_convert(None))
                    hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                    health['data_freshness_ok'] = hours_since_update < 2
                    health['details']['hours_since_last_update'] = round(hours_since_update, 2)
            except Exception as e:
                health['details']['freshness_error'] = str(e)
            
            # Score general de salud
            health_score = sum([
                health['credentials_configured'],
                health['exchange_configured'],
                health['rest_api_ok'],
                health['database_ok']
            ]) / 4 * 100
            
            health['health_score'] = round(health_score, 1)
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            health['details']['general_error'] = str(e)
        
        return health
    
    async def fetch_historical_data_chunk(
        self, 
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        progress: DownloadProgress
    ) -> pd.DataFrame:
        """Descarga un chunk de datos históricos"""
        try:
            ccxt_symbol = self._symbol_to_ccxt_format(symbol)
            original_symbol = self._normalize_symbol(symbol)
            
            since = int(start_date.timestamp() * 1000)
            until = int(end_date.timestamp() * 1000)
            
            logger.debug(f"Descargando chunk: {symbol} {timeframe} "
                        f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            
            # Usar fetch_ohlcv con parámetros optimizados
            ohlcv = await self._exponential_backoff_retry(
                self.exchange.fetch_ohlcv,
                ccxt_symbol,
                timeframe,
                since,
                self.chunk_size,
                params={'until': until}
            )
            
            if not ohlcv:
                logger.warning(f"Sin datos para chunk {start_date} - {end_date}")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Normalizar timestamps
            df['timestamp'] = df['timestamp'].apply(TimestampManager.normalize_timestamp)
            df['datetime'] = df['timestamp'].apply(TimestampManager.to_datetime)
            df.set_index('datetime', inplace=True)
            df['symbol'] = original_symbol
            
            # Validar datos
            valid_rows = []
            for idx, row in df.iterrows():
                data_dict = {
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                }
                if DataValidator.validate_ohlcv_data(data_dict, symbol):
                    valid_rows.append(idx)
            
            df = df.loc[valid_rows]
            
            # Filtrar por rango de fechas
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Actualizar progreso
            progress.downloaded_periods += 1
            progress.total_records += len(df)
            
            logger.debug(f"Chunk completado: {len(df)} registros válidos")
            return df
            
        except Exception as e:
            progress.errors += 1
            logger.error(f"Error en chunk {start_date}-{end_date}: {e}")
            return pd.DataFrame()
    
    async def fetch_historical_data_extended(
        self,
        symbol: str,
        timeframe: str = "1h",
        years: int = 5,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Descarga datos históricos extensos (5+ años) de forma eficiente"""
        try:
            if not TimeframeManager.is_valid_timeframe(timeframe):
                raise ValueError(f"Timeframe no válido: {timeframe}")
            
            if end_date is None:
                end_date = datetime.now()
            
            start_date = end_date - timedelta(days=years * 365)
            
            logger.info(f"🚀 Descarga extensa: {symbol} - {timeframe} - {years} años")
            logger.info(f"📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            
            # Calcular chunks optimizados basados en timeframe
            chunk_days = self._calculate_optimal_chunk_size(timeframe)
            
            # Crear lista de chunks
            chunks = []
            current_start = start_date
            
            while current_start < end_date:
                chunk_end = min(current_start + timedelta(days=chunk_days), end_date)
                chunks.append((current_start, chunk_end))
                current_start = chunk_end
            
            # Inicializar progreso
            progress = DownloadProgress(
                symbol=symbol,
                total_periods=len(chunks),
                downloaded_periods=0,
                total_records=0
            )
            
            logger.info(f"📦 Descarga dividida en {len(chunks)} chunks de ~{chunk_days} días")
            
            # Descargar chunks de forma concurrente (limitada)
            all_dataframes = []
            semaphore = asyncio.Semaphore(self.concurrent_downloads)
            
            async def download_chunk_with_semaphore(chunk_info):
                async with semaphore:
                    start, end = chunk_info
                    return await self.fetch_historical_data_chunk(
                        symbol, timeframe, start, end, progress
                    )
            
            # Ejecutar descargas
            tasks = [download_chunk_with_semaphore(chunk) for chunk in chunks]
            
            # Procesar resultados con progress tracking
            for i, task in enumerate(asyncio.as_completed(tasks)):
                try:
                    df_chunk = await task
                    if not df_chunk.empty:
                        all_dataframes.append(df_chunk)
                    
                    # Log de progreso cada 10 chunks
                    if (progress.downloaded_periods % 10 == 0) or (progress.downloaded_periods == progress.total_periods):
                        self._log_progress(progress)
                        
                except Exception as e:
                    logger.error(f"Error en chunk {i}: {e}")
            
            # Combinar todos los DataFrames
            if not all_dataframes:
                logger.error(f"❌ No se obtuvieron datos para {symbol}")
                return pd.DataFrame()
            
            logger.info(f"🔄 Combinando {len(all_dataframes)} chunks...")
            combined_df = pd.concat(all_dataframes, ignore_index=False)
            
            # Eliminar duplicados y ordenar
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            combined_df = combined_df.sort_index()
            
            # Detectar y corregir gaps
            combined_df = DataValidator.detect_and_fix_gaps(combined_df, timeframe)
            
            # Estadísticas finales
            total_days = (combined_df.index.max() - combined_df.index.min()).days
            expected_records = TimeframeManager.calculate_periods_needed(timeframe, total_days)
            coverage = (len(combined_df) / expected_records * 100) if expected_records > 0 else 0
            
            logger.info(f"✅ Descarga completada: {symbol}")
            logger.info(f"📊 Estadísticas:")
            logger.info(f"   - Registros: {len(combined_df):,}")
            logger.info(f"   - Período: {total_days} días")
            logger.info(f"   - Cobertura: {coverage:.1f}%")
            logger.info(f"   - Errores: {progress.errors}")
            logger.info(f"   - Tiempo total: {progress.elapsed_time}")
            
            return combined_df
            
        except Exception as e:
            logger.error(f"❌ Error en descarga extensa para {symbol}: {e}")
            return pd.DataFrame()
    
    def _calculate_optimal_chunk_size(self, timeframe: str) -> int:
        """Calcula el tamaño óptimo de chunk basado en timeframe"""
        # Chunks más pequeños para timeframes menores
        if timeframe in ['1m', '5m']:
            return 7  # 1 semana
        elif timeframe in ['15m', '30m']:
            return 14  # 2 semanas
        elif timeframe in ['1h', '2h']:
            return 30  # 1 mes
        elif timeframe in ['4h', '6h']:
            return 60  # 2 meses
        else:  # 12h, 1d, etc.
            return 90  # 3 meses
    
    def _log_progress(self, progress: DownloadProgress):
        """Log detallado de progreso"""
        logger.info(f"📈 Progreso {progress.symbol}: "
                   f"{progress.downloaded_periods}/{progress.total_periods} chunks "
                   f"({progress.progress_pct:.1f}%) - "
                   f"{progress.total_records:,} registros - "
                   f"ETA: {progress.estimated_remaining}")
    
    async def save_historical_data(self, df: pd.DataFrame) -> int:
        """Guarda datos históricos con optimizaciones"""
        try:
            if df.empty:
                logger.warning("DataFrame vacío, no hay nada que guardar")
                return 0
            
            logger.info(f"💾 Guardando {len(df)} registros en base de datos...")
            
            # Convertir a objetos MarketData en lotes
            batch_size = 5000
            total_saved = 0
            
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i:i + batch_size]
                market_data_list = []
                
                for timestamp, row in batch_df.iterrows():
                    try:
                        market_data = MarketData(
                            symbol=row['symbol'],
                            timestamp=int(row['timestamp']),
                            open=float(row['open']),
                            high=float(row['high']),
                            low=float(row['low']),
                            close=float(row['close']),
                            volume=float(row['volume'])
                        )
                        market_data_list.append(market_data)
                    except Exception as e:
                        logger.debug(f"Error procesando fila {timestamp}: {e}")
                        continue
                
                # Guardar lote
                if market_data_list:
                    saved = db_manager.bulk_save_market_data(market_data_list)
                    total_saved += saved
                    
                    if i % (batch_size * 10) == 0:  # Log cada 50k registros
                        logger.info(f"   Guardados {total_saved:,} de {len(df):,} registros...")
            
            logger.info(f"✅ Guardado completado: {total_saved:,} registros")
            return total_saved
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos históricos: {e}")
            return 0
    
    # Resto de métodos mantenidos con mejoras menores
    def add_tick_callback(self, callback: Callable):
        """Añade callback para datos de tick"""
        self.tick_callbacks.append(callback)
    
    def add_kline_callback(self, callback: Callable):
        """Añade callback para datos de kline"""
        self.kline_callbacks.append(callback)
    
    async def start_websocket_stream(self):
        """Inicia el stream de WebSocket con reconexión automática"""
        try:
            if not self.credentials.is_valid:
                logger.warning("Sin credenciales para WebSocket, solo datos históricos disponibles")
                return
            
            self.running = True
            max_reconnects = 10
            reconnect_delay = 5
            
            for attempt in range(max_reconnects):
                try:
                    logger.info(f"🔄 Iniciando stream WebSocket (intento {attempt + 1})...")
                    
                    ws_url = "wss://ws.bitget.com/spot/v1/stream"
                    
                    async with websockets.connect(
                        ws_url,
                        ping_interval=30,
                        ping_timeout=10,
                        close_timeout=10
                    ) as websocket:
                        self.websocket = websocket
                        
                        # Suscribirse a múltiples símbolos
                        symbols = self._get_symbols_from_config()
                        for symbol in symbols:
                            subscribe_msg = {
                                "op": "subscribe",
                                "args": [{
                                    "channel": "ticker",
                                    "instId": symbol
                                }]
                            }
                            await websocket.send(json.dumps(subscribe_msg))
                        
                        logger.info(f"✅ WebSocket conectado - {len(symbols)} símbolos suscritos")
                        
                        while self.running:
                            try:
                                message = await asyncio.wait_for(
                                    websocket.recv(), 
                                    timeout=60
                                )
                                data = json.loads(message)
                                
                                if 'data' in data:
                                    await self._handle_websocket_message(data['data'])
                                    
                            except asyncio.TimeoutError:
                                # Ping para mantener conexión
                                await websocket.ping()
                                continue
                                
                            except websockets.exceptions.ConnectionClosed:
                                logger.warning("WebSocket desconectado")
                                break
                                
                        break  # Salir del loop de reconexión si se detiene normalmente
                        
                except Exception as e:
                    logger.error(f"Error en WebSocket (intento {attempt + 1}): {e}")
                    if attempt < max_reconnects - 1:
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, 60)  # Backoff exponencial
                    else:
                        logger.error("Máximo de intentos de reconexión alcanzado")
                        
        except Exception as e:
            logger.error(f"Error crítico en WebSocket: {e}")
    
    def _get_symbols_from_config(self) -> List[str]:
        """Obtiene símbolos desde la configuración del usuario"""
        try:
            bot_settings = user_config.get_value(['bot_settings'], {})
            symbols = bot_settings.get('main_symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
            return [self._normalize_symbol(symbol) for symbol in symbols]
        except Exception as e:
            logger.error(f"Error obteniendo símbolos de configuración: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    async def _handle_websocket_message(self, data):
        """Maneja mensajes del WebSocket con callbacks"""
        try:
            for callback in self.tick_callbacks:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error en tick callback: {e}")
            
            for callback in self.kline_callbacks:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error en kline callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    def stop_websocket_stream(self):
        """Detiene el stream de WebSocket"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia global del recolector
data_collector = BitgetDataCollector()

async def collect_and_save_historical_data(
    symbol: str, 
    timeframe: str = "1h", 
    days_back: int = 30,
    end_date: datetime = None
) -> int:
    """
    Función helper para recolectar y guardar datos históricos
    
    Args:
        symbol: Símbolo del activo (ej: BTCUSDT)
        timeframe: Marco temporal (1h, 4h, 1d)
        days_back: Días hacia atrás
        end_date: Fecha final (default: ahora)
    
    Returns:
        Número de registros guardados
    """
    try:
        logger.info(f"🚀 Iniciando recolección: {symbol} - {timeframe} - {days_back} días")
        
        # Para períodos extensos (>1 año), usar método extendido
        if days_back > 365:
            years = days_back / 365.25
            df = await data_collector.fetch_historical_data_extended(
                symbol, timeframe, years, end_date
            )
        else:
            # Para períodos menores, usar método chunk simple
            if end_date is None:
                end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            progress = DownloadProgress(symbol=symbol, total_periods=1)
            df = await data_collector.fetch_historical_data_chunk(
                symbol, timeframe, start_date, end_date, progress
            )
        
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

async def download_extensive_historical_data(
    symbols: List[str] = None, 
    years: int = 5, 
    timeframes: List[str] = None
) -> Dict[str, Dict[str, int]]:
    """
    Descarga datos históricos extensos para múltiples símbolos y timeframes
    
    Args:
        symbols: Lista de símbolos a descargar
        years: Años de datos históricos
        timeframes: Lista de timeframes
    
    Returns:
        Diccionario anidado con resultados por símbolo y timeframe
    """
    try:
        if symbols is None:
            symbols = data_collector._get_symbols_from_config()
        
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']
        
        logger.info(f"🚀 Descarga masiva iniciada:")
        logger.info(f"   Símbolos: {len(symbols)} ({', '.join(symbols)})")
        logger.info(f"   Timeframes: {len(timeframes)} ({', '.join(timeframes)})")
        logger.info(f"   Período: {years} años")
        
        results = {}
        total_downloads = len(symbols) * len(timeframes)
        completed_downloads = 0
        
        for symbol in symbols:
            results[symbol] = {}
            
            for timeframe in timeframes:
                logger.info(f"📊 Procesando {symbol} - {timeframe} ({completed_downloads + 1}/{total_downloads})")
                
                try:
                    # Convertir años a días
                    days_back = int(years * 365.25)
                    
                    downloaded = await collect_and_save_historical_data(
                        symbol, timeframe, days_back
                    )
                    
                    results[symbol][timeframe] = downloaded
                    completed_downloads += 1
                    
                    # Progreso general
                    progress_pct = (completed_downloads / total_downloads) * 100
                    logger.info(f"🎯 Progreso general: {progress_pct:.1f}% ({completed_downloads}/{total_downloads})")
                    
                    # Pausa entre descargas para evitar sobrecarga
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error descargando {symbol} {timeframe}: {e}")
                    results[symbol][timeframe] = 0
                    completed_downloads += 1
        
        # Resumen final
        total_records = 0
        for symbol_results in results.values():
            for timeframe_count in symbol_results.values():
                if isinstance(timeframe_count, int):
                    total_records += timeframe_count
                else:
                    logger.warning(f"Valor inesperado en resultados: {timeframe_count}")
        
        logger.info(f"🎉 Descarga masiva completada:")
        logger.info(f"   Total de registros: {total_records:,}")
        logger.info(f"   Descargas exitosas: {completed_downloads}/{total_downloads}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga masiva: {e}")
        return {}

async def download_missing_data(
    symbols: List[str] = None, 
    target_years: int = 5,
    timeframes: List[str] = None
) -> Dict[str, Any]:
    """
    Analiza y descarga solo los datos faltantes
    
    Args:
        symbols: Lista de símbolos a verificar
        target_years: Años objetivo de datos históricos
        timeframes: Lista de timeframes a verificar
    
    Returns:
        Diccionario con análisis y resultados de descarga
    """
    try:
        if symbols is None:
            symbols = data_collector._get_symbols_from_config()
        
        if timeframes is None:
            timeframes = ['1h']  # Solo 1h para análisis inicial
        
        results = {
            'analysis_date': datetime.now().isoformat(),
            'target_years': target_years,
            'symbols_analyzed': len(symbols),
            'symbols_ok': 0,
            'symbols_updated': 0,
            'symbols_new': 0,
            'total_downloaded': 0,
            'details': {}
        }
        
        for symbol in symbols:
            logger.info(f"🔍 Analizando {symbol}...")
            
            try:
                # Verificar datos existentes
                date_range = db_manager.get_data_date_range(symbol)
                
                if date_range[0] is None or date_range[1] is None:
                    # No hay datos, descargar completo
                    logger.info(f"📥 {symbol}: Sin datos históricos, descargando completo...")
                    
                    days_back = int(target_years * 365.25)
                    downloaded = await collect_and_save_historical_data(
                        symbol, timeframes[0], days_back
                    )
                    
                    results['symbols_new'] += 1
                    results['total_downloaded'] += downloaded
                    results['details'][symbol] = {
                        'status': 'NEW',
                        'downloaded': downloaded,
                        'message': f'Descargados {downloaded:,} registros desde cero'
                    }
                    
                else:
                    # Verificar cobertura
                    current_days = (date_range[1] - date_range[0]).days
                    target_days = target_years * 365
                    
                    if current_days >= target_days:
                        results['symbols_ok'] += 1
                        results['details'][symbol] = {
                            'status': 'OK',
                            'current_days': current_days,
                            'message': f'Cobertura completa ({current_days} días)'
                        }
                    else:
                        # Descargar datos faltantes
                        missing_days = target_days - current_days
                        oldest_date = date_range[0] - timedelta(days=missing_days)
                        
                        logger.info(f"📈 {symbol}: Descargando {missing_days} días faltantes...")
                        
                        downloaded = await collect_and_save_historical_data(
                            symbol, timeframes[0], missing_days, date_range[0]
                        )
                        
                        results['symbols_updated'] += 1
                        results['total_downloaded'] += downloaded
                        results['details'][symbol] = {
                            'status': 'UPDATED',
                            'current_days': current_days,
                            'missing_days': missing_days,
                            'downloaded': downloaded,
                            'message': f'Agregados {downloaded:,} registros históricos'
                        }
                
            except Exception as e:
                logger.error(f"❌ Error analizando {symbol}: {e}")
                results['details'][symbol] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de datos faltantes: {e}")
        return {'error': str(e)}

async def verify_data_integrity(symbols: List[str] = None) -> Dict[str, Any]:
    """
    Verifica la integridad completa de los datos históricos
    
    Args:
        symbols: Lista de símbolos a verificar
    
    Returns:
        Diccionario con análisis de integridad detallado
    """
    try:
        if symbols is None:
            symbols = data_collector._get_symbols_from_config()
        
        verification_results = {
            'verification_date': datetime.now().isoformat(),
            'symbols_analyzed': len(symbols),
            'database_stats': db_manager.get_database_stats(),
            'symbol_analysis': {},
            'recommendations': [],
            'critical_issues': [],
            'warnings': []
        }
        
        for symbol in symbols:
            logger.info(f"🔍 Verificando integridad de {symbol}...")
            
            try:
                symbol_analysis = {
                    'symbol': symbol,
                    'record_count': db_manager.get_market_data_count_fast(symbol),
                    'date_range': db_manager.get_data_date_range(symbol),
                    'data_quality_issues': [],
                    'gaps_detected': 0,
                    'duplicates_detected': 0,
                    'invalid_records': 0,
                    'status': 'OK'
                }
                
                if symbol_analysis['record_count'] == 0:
                    symbol_analysis['status'] = 'NO_DATA'
                    verification_results['critical_issues'].append(
                        f"{symbol}: No hay datos históricos"
                    )
                    
                elif symbol_analysis['date_range'][0] is None:
                    symbol_analysis['status'] = 'CORRUPTED'
                    verification_results['critical_issues'].append(
                        f"{symbol}: Datos corruptos o timestamps inválidos"
                    )
                    
                else:
                    # Análisis detallado de calidad
                    date_start, date_end = symbol_analysis['date_range']
                    duration_days = (date_end - date_start).days
                    
                    # Verificar cobertura temporal
                    if duration_days < 365:
                        symbol_analysis['status'] = 'INSUFFICIENT'
                        verification_results['warnings'].append(
                            f"{symbol}: Cobertura insuficiente ({duration_days} días)"
                        )
                    
                    # Verificar densidad de datos (para 1h debería ser ~8760 registros/año)
                    expected_records_per_year = 8760  # 365 * 24
                    expected_total = int((duration_days / 365) * expected_records_per_year)
                    actual_records = symbol_analysis['record_count']
                    coverage_pct = (actual_records / expected_total * 100) if expected_total > 0 else 0
                    
                    symbol_analysis['coverage_percentage'] = round(coverage_pct, 1)
                    
                    if coverage_pct < 80:
                        verification_results['warnings'].append(
                            f"{symbol}: Baja cobertura de datos ({coverage_pct:.1f}%)"
                        )
                
                verification_results['symbol_analysis'][symbol] = symbol_analysis
                
            except Exception as e:
                logger.error(f"Error verificando {symbol}: {e}")
                verification_results['symbol_analysis'][symbol] = {
                    'symbol': symbol,
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        # Generar recomendaciones
        if verification_results['critical_issues']:
            verification_results['recommendations'].append(
                "🚨 Resolver problemas críticos antes de iniciar trading"
            )
        
        if verification_results['warnings']:
            verification_results['recommendations'].append(
                "⚠️ Considerar descargar más datos históricos para mejor precisión"
            )
        
        symbols_ok = sum(1 for analysis in verification_results['symbol_analysis'].values() 
                        if analysis.get('status') == 'OK')
        
        if symbols_ok >= len(symbols) * 0.8:
            verification_results['recommendations'].append(
                "✅ Calidad de datos suficiente para iniciar entrenamiento del modelo"
            )
        
        return verification_results
        
    except Exception as e:
        logger.error(f"❌ Error en verificación de integridad: {e}")
        return {'error': str(e)}