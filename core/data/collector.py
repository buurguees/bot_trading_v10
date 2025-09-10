# Ruta: core/data/collector.py
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
        
        # Configuración de tiempo real
        self.real_time_tasks = {}
        self.stop_collection = False
        self.websocket_connections = {}
        
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
            
            # Usar fetch_ohlcv con parámetros optimizados para Bitget
            ohlcv = await self._exponential_backoff_retry(
                self.exchange.fetch_ohlcv,
                ccxt_symbol,
                timeframe,
                since,
                self.chunk_size
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
            
            # Filtrar por rango de fechas (convertir ambos a datetime64[ns] para comparación)
            start_date_tz = pd.to_datetime(start_date).tz_localize('UTC') if start_date.tzinfo is None else pd.to_datetime(start_date)
            end_date_tz = pd.to_datetime(end_date).tz_localize('UTC') if end_date.tzinfo is None else pd.to_datetime(end_date)
            
            # Convertir a Timestamp para comparación compatible
            start_date_ts = pd.Timestamp(start_date_tz)
            end_date_ts = pd.Timestamp(end_date_tz)
            
            # Asegurar que el índice del DataFrame tenga la misma zona horaria
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            elif start_date_ts.tz is not None:
                df.index = df.index.tz_convert('UTC')
            
            df = df[(df.index >= start_date_ts) & (df.index <= end_date_ts)]
            
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
            symbols = user_config.get_symbols()
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
    
    # ===== MÉTODOS DE TIEMPO REAL =====
    
    async def fetch_real_time_data(self, symbol: str, timeframe: str, data_type: str = "kline") -> Optional[Dict]:
        """Recolecta datos en tiempo real desde Bitget (WebSocket o REST)."""
        try:
            if not self.exchange:
                logger.error("❌ Exchange no inicializado")
                return None
            
            if data_type == "kline":
                # Usar WebSocket para klines en tiempo real
                uri = "wss://ws.bitget.com/spot/v1/stream"
                async with websockets.connect(uri) as websocket:
                    # Suscribirse al canal
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [f"market.{symbol.lower()}.kline.{timeframe}"]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.debug(f"📡 Suscrito a {symbol} {timeframe} kline")
                    
                    # Escuchar un mensaje (para tiempo real, en producción sería un loop continuo)
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    if data.get("event") == "subscribe":
                        logger.debug("Suscripción confirmada")
                        return self._parse_kline_data(data)
                    
                    return self._parse_kline_data(data)
            
            elif data_type == "ticker":
                # Usar REST API para ticker
                ticker = await self._rate_limited_request(
                    self.exchange.fetch_ticker, 
                    self._symbol_to_ccxt_format(symbol)
                )
                return {
                    "timestamp": ticker["timestamp"] / 1000,
                    "last": ticker["last"],
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_type": data_type
                }
            
            elif data_type == "orderbook":
                # Usar REST API para orderbook
                orderbook = await self._rate_limited_request(
                    self.exchange.fetch_order_book, 
                    self._symbol_to_ccxt_format(symbol)
                )
                return {
                    "timestamp": orderbook["timestamp"] / 1000,
                    "bids": orderbook["bids"],
                    "asks": orderbook["asks"],
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_type": data_type
                }
            
            else:
                logger.warning(f"⚠️ Tipo de dato no soportado: {data_type}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout en recolección de {symbol} ({timeframe})")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching real-time data for {symbol} ({timeframe}): {e}")
            return None
    
    def _parse_kline_data(self, data: Dict) -> Dict:
        """Parsea datos de kline de WebSocket."""
        try:
            kline_data = data.get("data", [{}])[0]
            return {
                "timestamp": TimestampManager.normalize_timestamp(kline_data.get("t")),
                "open": float(kline_data.get("o", 0)),
                "high": float(kline_data.get("h", 0)),
                "low": float(kline_data.get("l", 0)),
                "close": float(kline_data.get("c", 0)),
                "volume": float(kline_data.get("v", 0)),
                "symbol": kline_data.get("s", ""),
                "timeframe": kline_data.get("k", ""),
                "data_type": "kline"
            }
        except Exception as e:
            logger.error(f"❌ Error parsing kline data: {e}")
            return {}
    
    async def start_real_time_collection(self, symbols: List[str], timeframes: List[str], 
                                       data_types: List[str] = ["kline"], 
                                       interval_seconds: int = 60) -> None:
        """Inicia la recolección en tiempo real para múltiples símbolos."""
        try:
            logger.info(f"🚀 Iniciando recolección en tiempo real para símbolos: {symbols}")
            self.stop_collection = False
            
            while not self.stop_collection:
                tasks = []
                for symbol in symbols:
                    for timeframe in timeframes:
                        for data_type in data_types:
                            task = asyncio.create_task(
                                self._collect_single_real_time(symbol, timeframe, data_type)
                            )
                            tasks.append(task)
                
                # Ejecutar todas las tareas en paralelo
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Esperar antes de la siguiente iteración
                await asyncio.sleep(interval_seconds)
                
        except Exception as e:
            logger.error(f"❌ Error en recolección en tiempo real: {e}")
            raise
    
    async def _collect_single_real_time(self, symbol: str, timeframe: str, data_type: str) -> None:
        """Recolecta datos para un símbolo/timeframe específico."""
        try:
            logger.debug(f"📥 Recolectando {data_type} para {symbol} ({timeframe})...")
            
            # Obtener datos en tiempo real
            data = await self.fetch_real_time_data(symbol, timeframe, data_type)
            if data:
                # Crear directorio si no existe
                from pathlib import Path
                Path(f"data/{symbol}").mkdir(parents=True, exist_ok=True)
                
                # Guardar en la base de datos por símbolo
                db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
                success = db_manager.store_real_time_data(data, symbol, timeframe, db_path)
                if success:
                    logger.debug(f"✅ Datos guardados para {symbol} ({timeframe}) en {db_path}")
                else:
                    logger.warning(f"⚠️ Error al guardar datos para {symbol} ({timeframe})")
            else:
                logger.warning(f"⚠️ No se recibieron datos para {symbol} ({timeframe})")
                
        except Exception as e:
            logger.error(f"❌ Error recolectando datos para {symbol} ({timeframe}): {e}")
            await asyncio.sleep(5)  # Espera breve antes de reintentar
    
    def stop_real_time_collection(self) -> None:
        """Detiene la recolección en tiempo real."""
        self.stop_collection = True
        logger.info("🛑 Deteniendo recolección en tiempo real...")

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
    timeframes: List[str] = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict[str, Any]:
    """
    Descarga datos históricos extensos para múltiples símbolos y timeframes
    
    Args:
        symbols: Lista de símbolos a descargar
        years: Años de datos históricos
        timeframes: Lista de timeframes
        start_date: Fecha de inicio específica (opcional)
        end_date: Fecha de fin específica (opcional)
    
    Returns:
        Diccionario con datos descargados y metadatos
    """
    try:
        if symbols is None:
            symbols = data_collector._get_symbols_from_config()
        
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']
        
        # Si se proporcionan fechas específicas, usar descarga por rango
        if start_date and end_date:
            logger.info(f"🚀 Descarga por rango de fechas:")
            logger.info(f"   Símbolos: {len(symbols)} ({', '.join(symbols)})")
            logger.info(f"   Timeframes: {len(timeframes)} ({', '.join(timeframes)})")
            logger.info(f"   Período: {start_date} a {end_date}")
            
            all_data = {}
            for symbol in symbols:
                all_data[symbol] = {}
                for timeframe in timeframes:
                    try:
                        logger.info(f"📊 Descargando {symbol} - {timeframe} desde {start_date} a {end_date}")
                        
                        # Calcular días hacia atrás
                        days_back = (end_date - start_date).days
                        
                        # Descargar datos para el rango específico
                        df = await data_collector.fetch_historical_data_chunk(
                            symbol, timeframe, start_date, end_date, 
                            DownloadProgress(symbol=symbol, total_periods=1)
                        )
                        
                        if not df.empty:
                            all_data[symbol][timeframe] = df
                            logger.info(f"✅ {symbol} {timeframe}: {len(df)} registros")
                        else:
                            logger.warning(f"⚠️ No se obtuvieron datos para {symbol} {timeframe}")
                            all_data[symbol][timeframe] = pd.DataFrame()
                        
                        await asyncio.sleep(1)  # Pausa entre descargas
                        
                    except Exception as e:
                        logger.error(f"❌ Error descargando {symbol} {timeframe}: {e}")
                        all_data[symbol][timeframe] = pd.DataFrame()
            
            return {
                'status': 'success',
                'data': all_data,
                'total_records': sum(len(df) for symbol_data in all_data.values() 
                                   for df in symbol_data.values() if isinstance(df, pd.DataFrame))
            }
        
        # Lógica original para descarga masiva por años
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
        
        # Resumen final para descarga masiva
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
        
        return {
            'status': 'success',
            'results': results,
            'total_records': total_records
        }
        
    except Exception as e:
        logger.error(f"❌ Error en descarga masiva: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'data': None
        }

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

# =============================================================================
# FUNCIONALIDADES MULTI-TIMEFRAME
# =============================================================================

async def download_coordinated_multi_timeframe(
    symbols: List[str], 
    timeframes: List[str] = ['5m', '15m', '1h', '4h', '1d'],
    days_back: int = 365
) -> Dict[str, Any]:
    """
    Descarga coordinada de múltiples timeframes con alineación automática
    
    Args:
        symbols: Lista de símbolos a descargar
        timeframes: Lista de timeframes a procesar
        days_back: Días hacia atrás para descargar
    
    Returns:
        Dict[str, Any]: Resultados de la descarga coordinada
    """
    try:
        logger.info(f"🚀 Iniciando descarga coordinada multi-timeframe para {symbols}")
        start_time = datetime.now()
        
        # Configurar timeframes con prioridades
        timeframe_priority = {
            '5m': 1,   # Crítico - base para agregación
            '15m': 2,  # Crítico - confirmación
            '1h': 3,   # Alto - tendencia
            '4h': 4,   # Medio - régimen
            '1d': 5    # Bajo - contexto
        }
        
        # Ordenar timeframes por prioridad
        sorted_timeframes = sorted(timeframes, key=lambda x: timeframe_priority.get(x, 99))
        
        results = {
            'success': True,
            'timeframes_processed': [],
            'symbols_processed': symbols,
            'total_records': 0,
            'processing_time': 0.0,
            'errors': [],
            'alignment_results': {},
            'coherence_scores': {}
        }
        
        # Procesar cada timeframe
        for timeframe in sorted_timeframes:
            try:
                logger.info(f"📊 Procesando timeframe {timeframe}")
                
                # Calcular chunk size óptimo para este timeframe
                chunk_days = calculate_optimal_chunk_size_by_timeframe(timeframe)
                
                # Descargar datos para este timeframe
                tf_results = await download_extensive_historical_data(
                    symbols=symbols,
                    timeframes=[timeframe],
                    years=days_back/365.25
                )
                
                if tf_results['success']:
                    results['timeframes_processed'].append(timeframe)
                    results['total_records'] += tf_results.get('total_records', 0)
                    results['alignment_results'][timeframe] = tf_results
                else:
                    results['errors'].append(f"Error en {timeframe}: {tf_results.get('error', 'Unknown')}")
                
            except Exception as e:
                error_msg = f"Error procesando {timeframe}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        # Validar y alinear datos descargados
        if results['timeframes_processed']:
            logger.info("🔄 Validando y alineando datos descargados")
            alignment_results = await validate_and_align_downloaded_data(results['alignment_results'])
            results['alignment_results'] = alignment_results
        
        # Calcular coherencia entre timeframes
        if len(results['timeframes_processed']) > 1:
            logger.info("📈 Calculando coherencia entre timeframes")
            coherence_scores = calculate_timeframe_coherence(results['alignment_results'])
            results['coherence_scores'] = coherence_scores
        
        results['processing_time'] = (datetime.now() - start_time).total_seconds()
        results['success'] = len(results['errors']) == 0
        
        logger.info(f"✅ Descarga coordinada completada en {results['processing_time']:.2f}s")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga coordinada multi-timeframe: {e}")
        return {
            'success': False,
            'error': str(e),
            'timeframes_processed': [],
            'symbols_processed': symbols,
            'total_records': 0,
            'processing_time': 0.0,
            'errors': [str(e)],
            'alignment_results': {},
            'coherence_scores': {}
        }

async def validate_and_align_downloaded_data(
    raw_data: Dict[str, Dict[str, pd.DataFrame]]
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Valida y alinea datos descargados antes de almacenar
    
    Args:
        raw_data: Datos brutos organizados por timeframe y símbolo
    
    Returns:
        Dict[str, Dict[str, pd.DataFrame]]: Datos validados y alineados
    """
    try:
        logger.info("🔍 Validando y alineando datos descargados")
        
        from .temporal_alignment import TemporalAlignment, AlignmentConfig
        
        # Configurar sistema de alineación
        config = AlignmentConfig(
            timeframes=list(raw_data.keys()),
            required_symbols=list(next(iter(raw_data.values())).keys()) if raw_data else []
        )
        aligner = TemporalAlignment(config)
        
        aligned_data = {}
        
        for timeframe, symbol_data in raw_data.items():
            try:
                logger.info(f"🔄 Alineando datos para {timeframe}")
                
                # Obtener rango de fechas común
                all_timestamps = []
                for df in symbol_data.values():
                    if not df.empty:
                        all_timestamps.extend(df.index.tolist())
                
                if not all_timestamps:
                    continue
                
                start_date = min(all_timestamps)
                end_date = max(all_timestamps)
                
                # Crear timeline maestra
                master_timeline = aligner.create_master_timeline(timeframe, start_date, end_date)
                
                # Alinear datos
                aligned_symbol_data = aligner.align_symbol_data(symbol_data, master_timeline, timeframe)
                
                # Validar alineación
                validation = aligner.validate_alignment(aligned_symbol_data)
                
                if validation['overall_quality'] > 0.8:
                    aligned_data[timeframe] = aligned_symbol_data
                    logger.info(f"✅ {timeframe} alineado con calidad {validation['overall_quality']:.3f}")
                else:
                    logger.warning(f"⚠️ Calidad baja en {timeframe}: {validation['overall_quality']:.3f}")
                    aligned_data[timeframe] = aligned_symbol_data  # Usar de todos modos
                
            except Exception as e:
                logger.error(f"❌ Error alineando {timeframe}: {e}")
                aligned_data[timeframe] = symbol_data  # Usar datos originales
        
        return aligned_data
        
    except Exception as e:
        logger.error(f"❌ Error en validación y alineación: {e}")
        return raw_data

def calculate_optimal_chunk_size_by_timeframe(timeframe: str) -> int:
    """
    Calcula tamaño óptimo de chunk específico por timeframe
    
    Args:
        timeframe: Timeframe objetivo
    
    Returns:
        int: Días por chunk
    """
    chunk_sizes = {
        '5m': 2,    # 2 días (576 registros) - Datos de alta frecuencia
        '15m': 7,   # 7 días (672 registros) - Balance frecuencia/memoria
        '1h': 30,   # 30 días (720 registros) - Datos horarios
        '4h': 60,   # 60 días (360 registros) - Datos de 4 horas
        '1d': 180   # 180 días (180 registros) - Datos diarios
    }
    
    return chunk_sizes.get(timeframe, 30)

def calculate_timeframe_coherence(
    alignment_results: Dict[str, Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calcula coherencia entre diferentes timeframes
    
    Args:
        alignment_results: Resultados de alineación por timeframe
    
    Returns:
        Dict[str, float]: Scores de coherencia entre pares de timeframes
    """
    try:
        coherence_scores = {}
        
        # Definir relaciones de agregación
        aggregation_relations = {
            '15m': '5m',
            '1h': '15m',
            '4h': '1h',
            '1d': '4h'
        }
        
        for target_tf, source_tf in aggregation_relations.items():
            if target_tf in alignment_results and source_tf in alignment_results:
                try:
                    # Calcular coherencia simplificada
                    target_quality = alignment_results[target_tf].get('validation', {}).get('overall_quality', 0)
                    source_quality = alignment_results[source_tf].get('validation', {}).get('overall_quality', 0)
                    
                    # Coherencia basada en calidad promedio
                    coherence = (target_quality + source_quality) / 2
                    coherence_scores[f"{source_tf}_to_{target_tf}"] = coherence
                    
                except Exception as e:
                    logger.warning(f"Error calculando coherencia {source_tf}->{target_tf}: {e}")
                    coherence_scores[f"{source_tf}_to_{target_tf}"] = 0.0
        
        return coherence_scores
        
    except Exception as e:
        logger.error(f"Error calculando coherencia entre timeframes: {e}")
        return {}

async def download_multi_timeframe_with_alignment(
    symbols: List[str],
    timeframes: List[str] = ['5m', '15m', '1h', '4h', '1d'],
    days_back: int = 365,
    use_aggregation: bool = True
) -> Dict[str, Any]:
    """
    Función principal para descarga multi-timeframe con alineación automática
    
    Args:
        symbols: Lista de símbolos
        timeframes: Lista de timeframes
        days_back: Días hacia atrás
        use_aggregation: Si usar agregación automática
    
    Returns:
        Dict[str, Any]: Resultados completos de la descarga
    """
    try:
        logger.info(f"🚀 Iniciando descarga multi-timeframe con alineación")
        
        # Descargar datos coordinados
        download_results = await download_coordinated_multi_timeframe(
            symbols, timeframes, days_back
        )
        
        if not download_results['success']:
            return download_results
        
        # Si se solicita agregación, procesar timeframes agregados
        if use_aggregation and '5m' in download_results['timeframes_processed']:
            logger.info("🔄 Procesando agregación automática de timeframes")
            
            from .multi_timeframe_coordinator import MultiTimeframeCoordinator
            coordinator = MultiTimeframeCoordinator()
            
            # Obtener datos base (5m)
            base_data = download_results['alignment_results'].get('5m', {})
            
            if base_data:
                # Agregar timeframes automáticamente
                aggregated_data = coordinator.auto_aggregate_timeframes(base_data)
                
                # Agregar datos agregados a los resultados
                for tf, data in aggregated_data.items():
                    if tf not in download_results['alignment_results']:
                        download_results['alignment_results'][tf] = data
                        download_results['timeframes_processed'].append(tf)
        
        # Almacenar datos en base de datos
        logger.info("💾 Almacenando datos alineados en base de datos")
        
        from .database import db_manager
        
        for timeframe, symbol_data in download_results['alignment_results'].items():
            if symbol_data:
                session_id = f"multi_tf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                success = db_manager.store_aligned_data(symbol_data, timeframe, session_id)
                
                if success:
                    logger.info(f"✅ Datos {timeframe} almacenados correctamente")
                else:
                    logger.warning(f"⚠️ Error almacenando datos {timeframe}")
        
        # Registrar operación
        db_manager.log_operation(
            operation_type="multi_timeframe_download",
            status="completed" if download_results['success'] else "failed",
            symbols=symbols,
            timeframes=download_results['timeframes_processed'],
            records_processed=download_results['total_records'],
            processing_time=download_results['processing_time'],
            metadata={
                'days_back': days_back,
                'use_aggregation': use_aggregation,
                'coherence_scores': download_results['coherence_scores']
            }
        )
        
        logger.info(f"✅ Descarga multi-timeframe completada: {download_results['total_records']} registros")
        return download_results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga multi-timeframe: {e}")
        
        # Registrar error
        from .database import db_manager
        db_manager.log_operation(
            operation_type="multi_timeframe_download",
            status="failed",
            symbols=symbols,
            timeframes=timeframes,
            error_message=str(e)
        )
        
        return {
            'success': False,
            'error': str(e),
            'timeframes_processed': [],
            'symbols_processed': symbols,
            'total_records': 0,
            'processing_time': 0.0,
            'errors': [str(e)],
            'alignment_results': {},
            'coherence_scores': {}
        }

# Funciones de conveniencia
async def quick_download_multi_timeframe(
    symbols: List[str] = None,
    timeframes: List[str] = None,
    days_back: int = 365
) -> Dict[str, Any]:
    """Función de conveniencia para descarga multi-timeframe rápida"""
    # Cargar desde user_settings.yaml si no se pasan parámetros
    if symbols is None or timeframes is None:
        try:
            from config.unified_config import unified_config
            from config.config_loader import user_config as _user_config
            # Símbolos habilitados
            if symbols is None:
                symbols_cfg = _user_config.get_value(['multi_symbol_settings', 'symbols'], {})
                symbols = [sym for sym, cfg in symbols_cfg.items() if cfg.get('enabled', True)] or []
            # Timeframes históricos
            if timeframes is None:
                hist_cfg = unified_config.get('data_collection', {}).get('historical', {})
                timeframes = hist_cfg.get('timeframes', ['1m', '5m', '15m', '1h', '4h', '1d'])
        except Exception:
            # Fallback seguro
            symbols = symbols or ['BTCUSDT']
            timeframes = timeframes or ['1h']

    return await download_multi_timeframe_with_alignment(symbols, timeframes, days_back)

# Alias para compatibilidad con bot.py
DataCollector = BitgetDataCollector