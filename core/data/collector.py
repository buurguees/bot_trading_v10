# Ruta: core/data/collector.py
"""
data/collector.py - VERSIÓN PROFESIONAL MEJORADA
Recolector de datos de mercado desde Bitget API
Ubicación: C:\\TradingBot_v10\\data\\collector.py

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
from dataclasses import dataclass, asdict
import numpy as np
from pathlib import Path
import threading
from itertools import chain

from .database import db_manager, MarketData

# Lazy import para evitar posibles circulares
def _get_cfg():
    from config.unified_config import get_config_manager
    return get_config_manager()

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
                    logger.warning(f"Precio inválido {field} en {symbol}: {data[field]}")
                    return False
            
            # Validar relación High >= Low
            if data['high'] < data['low']:
                logger.warning(f"High < Low en {symbol}: {data['high']} < {data['low']}")
                return False
            
            # Validar Open y Close en rango
            if not (data['low'] <= data['open'] <= data['high']):
                logger.warning(f"Open fuera de rango en {symbol}")
                return False
            
            if not (data['low'] <= data['close'] <= data['high']):
                logger.warning(f"Close fuera de rango en {symbol}")
                return False
            
            # Validar volumen
            if data['volume'] < 0:
                logger.warning(f"Volumen negativo en {symbol}: {data['volume']}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validando OHLCV para {symbol}: {e}")
            return False
    
    @staticmethod
    def clean_ohlcv_data(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Limpia y repara datos OHLCV inválidos"""
        original_len = len(data)
        if original_len == 0:
            return data
        
        # Eliminar duplicados
        data = data.drop_duplicates(subset=['timestamp'])
        
        # Ordenar por timestamp
        data = data.sort_values('timestamp')
        
        # Validar y reparar OHLC
        mask = (data['high'] < data['low'])
        data.loc[mask, ['high', 'low']] = data.loc[mask, ['low', 'high']].values
        
        # Asegurar open/close en rango
        data['open'] = data['open'].clip(lower=data['low'], upper=data['high'])
        data['close'] = data['close'].clip(lower=data['low'], upper=data['high'])
        
        # Volumen no negativo
        data['volume'] = data['volume'].clip(lower=0)
        
        # Rellenar NaNs con forward fill
        data = data.ffill()
        
        cleaned_len = len(data)
        if cleaned_len < original_len:
            logger.info(f"Limpiados {original_len - cleaned_len} registros inválidos para {symbol}")
        
        return data

class BitgetDataCollector:
    """Recolector profesional de datos de Bitget API"""
    
    BASE_URL = "https://api.bitget.com"
    WS_URL = "wss://ws.bitget.com/v2/ws/public/spot"
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 2
    RATE_LIMIT = 10  # Requests por segundo
    CHUNK_SIZE = 1000  # Velas por request histórico
    
    def __init__(self, credentials: Optional[BitgetCredentials] = None):
        self.credentials = credentials or self._load_credentials()
        self.session = aiohttp.ClientSession()
        self.exchange = ccxt.bitget({
            'apiKey': self.credentials.api_key,
            'secret': self.credentials.secret_key,
            'password': self.credentials.passphrase,
            'options': {'defaultType': 'spot'}
        })
        self.rate_limiter = asyncio.Semaphore(self.RATE_LIMIT)
    
    async def close(self):
        """Cierra la sesión aiohttp"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
    
    def _load_credentials(self) -> BitgetCredentials:
        """Carga credenciales desde env"""
        api_key = os.getenv('BITGET_API_KEY')
        secret_key = os.getenv('BITGET_SECRET_KEY')
        passphrase = os.getenv('BITGET_PASSPHRASE')
        
        if not all([api_key, secret_key, passphrase]):
            raise ValueError("Credenciales de Bitget no configuradas en .env")
        
        return BitgetCredentials(api_key, secret_key, passphrase)
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Request con rate limiting y reintentos"""
        async with self.rate_limiter:
            for attempt in range(self.MAX_RETRIES):
                try:
                    async with getattr(self.session, method.lower())(f"{self.BASE_URL}{endpoint}", params=params) as response:
                        if response.status == 429:
                            await asyncio.sleep(self.BACKOFF_FACTOR ** attempt)
                            continue
                        response.raise_for_status()
                        return await response.json()
                except Exception as e:
                    if attempt == self.MAX_RETRIES - 1:
                        raise
                    await asyncio.sleep(self.BACKOFF_FACTOR ** attempt)
    
    def fetch_historical_data_chunk(self, symbol: str, timeframe: str, start: datetime, end: datetime, progress: DownloadProgress) -> Optional[pd.DataFrame]:
        """Fetch chunk histórico con validación"""
        try:
            since = int(start.timestamp() * 1000)
            until = int(end.timestamp() * 1000)
            
            # Ajustar límite según timeframe
            limit = min(self.CHUNK_SIZE, 1000 if timeframe in ['1m', '5m'] else 500)
            
            # ccxt.fetch_ohlcv no es asíncrono
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            
            if not ohlcv or len(ohlcv) == 0:
                logger.debug(f"⚠️ Sin datos para {symbol} {timeframe} en {start.date()}")
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # La API de Bitget ya devuelve datos en el rango correcto, no necesitamos filtrar
            
            # Validar y limpiar
            df = DataValidator.clean_ohlcv_data(df, symbol)
            
            progress.downloaded_periods += 1
            progress.total_records += len(df)
            
            return df
        except Exception as e:
            progress.errors += 1
            logger.error(f"Error fetching chunk {symbol} {timeframe}: {e}")
            return None
    
    async def download_historical_data(self, symbol: str, timeframe: str, days_back: int = None, start: datetime = None, end: datetime = None) -> Dict[str, Any]:
        """Wrapper para descargar datos históricos, soporta rangos específicos"""
        try:
            if days_back is None and (start is None or end is None):
                return {"success": False, "error": "Debe especificar days_back o start/end"}
            
            if start is None:
                start = datetime.now(timezone.utc) - timedelta(days=days_back or 365)
            if end is None:
                end = datetime.now(timezone.utc)
            
            # Verificar datos existentes solo para gaps, no para completitud
            db_path = f"data/{symbol}/trading_bot.db"
            if Path(db_path).exists():
                analysis = db_manager.analyze_historical_data(symbol, timeframe, db_path)
                # Solo saltar si hay datos suficientes Y no hay gaps
                records_per_day = 24 if timeframe == "1h" else 6 if timeframe == "4h" else 1440 if timeframe == "1m" else 288 if timeframe == "5m" else 96 if timeframe == "15m" else 1
                current_days = analysis["total_records"] / records_per_day
                expected_days = days_back or 365
                
                if current_days >= expected_days * 0.8 and not analysis.get("gaps"):
                    logger.info(f"✅ {symbol} {timeframe}: Datos suficientes ({current_days:.1f} días), {analysis['total_records']} registros")
                    return {"success": True, "data": pd.DataFrame(), "records": analysis["total_records"], "errors": []}
                else:
                    logger.info(f"📥 {symbol} {timeframe}: Solo {current_days:.1f} días, necesarios {expected_days} días")
            
            # Descargar datos
            result = await self.download_extensive_historical_data([symbol], [timeframe], start, end)
            if result["success"] and symbol in result["data"] and timeframe in result["data"][symbol]:
                data_df = result["data"][symbol][timeframe]
                logger.info(f"✅ Descargados {len(data_df)} registros para {symbol} {timeframe}")
                return {
                    "success": True,
                    "data": data_df,
                    "records": len(data_df),
                    "errors": result["errors"]
                }
            else:
                error_msg = f"No se obtuvieron datos para {symbol} {timeframe}"
                if result["errors"]:
                    error_msg += f": {', '.join(result['errors'])}"
                logger.warning(f"⚠️ {error_msg}")
                return {"success": False, "data": pd.DataFrame(), "records": 0, "errors": [error_msg]}
        except Exception as e:
            logger.error(f"❌ Error en download_historical_data {symbol} {timeframe}: {e}")
            return {"success": False, "data": pd.DataFrame(), "records": 0, "errors": [str(e)]}
    
    async def download_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        days_back: int = None, 
        start: datetime = None, 
        end: datetime = None
    ) -> Dict[str, Any]:
        """
        Descarga datos históricos para un símbolo y timeframe específicos
        
        Args:
            symbol: Símbolo a descargar
            timeframe: Timeframe (1m, 5m, 1h, etc.)
            days_back: Días hacia atrás desde ahora
            start: Fecha de inicio específica
            end: Fecha de fin específica
            
        Returns:
            Dict con success, data, records, errors
        """
        try:
            logger.info(f"📥 Descargando datos históricos: {symbol} {timeframe}")
            
            # Calcular fechas si no se proporcionan
            if start is None and end is None:
                if days_back:
                    end = datetime.now(timezone.utc)
                    start = end - timedelta(days=days_back)
                else:
                    end = datetime.now(timezone.utc)
                    start = end - timedelta(days=365)  # Default 1 año
            
            # Verificar si ya existen datos para evitar descargas redundantes
            from .database import db_manager
            last_timestamp = db_manager.get_last_timestamp(symbol, timeframe)
            
            if last_timestamp:
                last_dt = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
                if last_dt >= start:
                    logger.info(f"✅ {symbol} {timeframe} ya tiene datos desde {last_dt}")
                    # Solo descargar datos faltantes
                    start = last_dt + timedelta(minutes=1)
                    if start >= end:
                        return {
                            "success": True,
                            "data": pd.DataFrame(),
                            "records": 0,
                            "errors": []
                        }
            
            # Usar download_extensive_historical_data como base
            result = await self.download_extensive_historical_data(
                symbols=[symbol],
                timeframes=[timeframe],
                start_date=start,
                end_date=end
            )
            
            if result.get('success') and result.get('data'):
                symbol_data = result['data'].get(symbol, {})
                timeframe_data = symbol_data.get(timeframe, pd.DataFrame())
                
                if not timeframe_data.empty:
                    # Validar datos
                    timeframe_data = DataValidator.clean_ohlcv_data(timeframe_data, symbol)
                    
                    return {
                        "success": True,
                        "data": timeframe_data,
                        "records": len(timeframe_data),
                        "errors": []
                    }
                else:
                    return {
                        "success": False,
                        "data": pd.DataFrame(),
                        "records": 0,
                        "errors": ["No se obtuvieron datos"]
                    }
            else:
                return {
                    "success": False,
                    "data": pd.DataFrame(),
                    "records": 0,
                    "errors": result.get('errors', ['Error en descarga'])
                }
                
        except Exception as e:
            logger.error(f"❌ Error descargando {symbol} {timeframe}: {e}")
            return {
                "success": False,
                "data": pd.DataFrame(),
                "records": 0,
                "errors": [str(e)]
            }

    async def download_extensive_historical_data(
        self,
        symbols: List[str],
        timeframes: List[str],
        start_date: datetime,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Descarga extensa histórica multi-symbol/timeframe"""
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        results = {'success': True, 'data': {}, 'errors': []}
        
        # Procesar cada símbolo y timeframe secuencialmente para evitar problemas de concurrencia
        all_data = {}
        
        for symbol in symbols:
            results['data'][symbol] = {}
            for timeframe in timeframes:
                try:
                    logger.info(f"📥 Descargando {symbol} {timeframe}")
                    progress = DownloadProgress(symbol)
                    
                    # Descargar datos en chunks (ajustar tamaño según timeframe)
                    chunk_days = 7 if timeframe in ['1m', '5m'] else 30 if timeframe in ['15m', '1h'] else 90
                    chunk_start = start_date
                    symbol_timeframe_data = []
                    
                    while chunk_start < end_date:
                        chunk_end = min(chunk_start + timedelta(days=chunk_days), end_date)
                        df_chunk = self.fetch_historical_data_chunk(symbol, timeframe, chunk_start, chunk_end, progress)
                        
                        if df_chunk is not None and not df_chunk.empty:
                            symbol_timeframe_data.append(df_chunk)
                            logger.debug(f"📊 {symbol} {timeframe}: Chunk {chunk_start.date()} → {chunk_end.date()}: {len(df_chunk)} registros")
                        
                        chunk_start = chunk_end
                    
                    # Concatenar todos los chunks para este símbolo/timeframe
                    if symbol_timeframe_data:
                        df_combined = pd.concat(symbol_timeframe_data, ignore_index=True)
                        df_combined = df_combined.drop_duplicates().sort_values('timestamp')
                        
                        if symbol not in all_data:
                            all_data[symbol] = {}
                        all_data[symbol][timeframe] = df_combined
                        logger.info(f"✅ {symbol} {timeframe}: {len(df_combined)} registros")
                    else:
                        logger.warning(f"⚠️ No se obtuvieron datos para {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando {symbol} {timeframe}: {e}")
                    results['errors'].append(f"{symbol} {timeframe}: {str(e)}")
        
        # Asignar datos finales a results
        for symbol in symbols:
            for timeframe in timeframes:
                if symbol in all_data and timeframe in all_data[symbol]:
                    df = all_data[symbol][timeframe]
                    df = DataValidator.clean_ohlcv_data(df, symbol)
                    results['data'][symbol][timeframe] = df
                else:
                    results['data'][symbol][timeframe] = pd.DataFrame()
        
        results['success'] = len(results['errors']) == 0
        return results

    async def start_real_time_collection(
        self,
        symbols: List[str],
        timeframes: List[str],
        data_types: List[str] = None,
        interval_seconds: int = 60,
        collection_ready: asyncio.Event = None
    ):
        """Recolección RT con websockets mejorada"""
        if data_types is None:
            data_types = ["kline"]
            
        logger.info(f"🚀 Iniciando recolección en tiempo real para {len(symbols)} símbolos")
        
        try:
            # Usar polling en lugar de websockets para mayor estabilidad
            while True:
                try:
                    # Recolectar datos para cada símbolo y timeframe
                    for symbol in symbols:
                        for timeframe in timeframes:
                            try:
                                # Obtener datos más recientes
                                end_time = datetime.now(timezone.utc)
                                start_time = end_time - timedelta(minutes=5)  # Últimos 5 minutos
                                
                                # Descargar datos recientes
                                result = await self.download_historical_data(
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    start=start_time,
                                    end=end_time
                                )
                                
                                if result.get("success") and not result.get("data").empty:
                                    # Almacenar datos en tiempo real
                                    db_path = f"data/{symbol}/trading_bot.db"
                                    success = db_manager.store_historical_data(
                                        data_to_store=result["data"],
                                        symbol=symbol,
                                        timeframe=timeframe,
                                        db_path=db_path
                                    )
                                    
                                    if success:
                                        logger.debug(f"✅ Datos RT almacenados: {symbol} {timeframe} - {len(result['data'])} registros")
                                    else:
                                        logger.warning(f"⚠️ Error almacenando datos RT: {symbol} {timeframe}")
                                
                            except Exception as e:
                                logger.error(f"❌ Error recolectando {symbol} {timeframe}: {e}")
                                continue
                    
                    # Señalar que la recolección está lista
                    if collection_ready and not collection_ready.is_set():
                        collection_ready.set()
                        logger.info("✅ Recolección en tiempo real iniciada correctamente")
                    
                    # Esperar antes de la siguiente recolección
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"❌ Error en ciclo de recolección RT: {e}")
                    await asyncio.sleep(30)  # Esperar 30 segundos antes de reintentar
                    
        except Exception as e:
            logger.error(f"❌ Error fatal en recolección RT: {e}")
            if collection_ready:
                collection_ready.set()  # Señalar que terminó (con error)

    async def start_websocket_collection(
        self,
        symbols: List[str],
        timeframes: List[str],
        collection_ready: asyncio.Event = None
    ):
        """Recolección RT usando WebSockets de Bitget"""
        import websockets
        import json
        
        logger.info(f"🌐 Iniciando recolección WebSocket para {len(symbols)} símbolos")
        
        try:
            # URL de WebSocket de Bitget
            ws_url = "wss://ws.bitget.com/spot/v1/stream"
            
            async with websockets.connect(ws_url) as ws:
                # Suscribir a klines para cada símbolo y timeframe
                for symbol in symbols:
                    for timeframe in timeframes:
                        subscribe_msg = {
                            "op": "subscribe",
                            "args": [{
                                "channel": "candle1m" if timeframe == "1m" else f"candle{timeframe}",
                                "instId": symbol
                            }]
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        logger.debug(f"📡 Suscrito a {symbol} {timeframe}")
                
                # Señalar que está listo
                if collection_ready:
                    collection_ready.set()
                    logger.info("✅ WebSocket conectado y suscrito correctamente")
                
                # Procesar mensajes
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        if data.get("arg", {}).get("channel", "").startswith("candle"):
                            # Procesar datos de kline
                            kline_data = data.get("data", [])
                            for kline in kline_data:
                                await self._process_websocket_kline(kline, data["arg"]["instId"], data["arg"]["channel"])
                                
                    except Exception as e:
                        logger.error(f"❌ Error procesando mensaje WebSocket: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Error en WebSocket collection: {e}")
            if collection_ready:
                collection_ready.set()

    async def _process_websocket_kline(self, kline_data: dict, symbol: str, channel: str):
        """Procesa datos de kline del WebSocket"""
        try:
            # Extraer timeframe del channel
            timeframe = channel.replace("candle", "")
            if timeframe == "1m":
                timeframe = "1m"
            elif timeframe == "5m":
                timeframe = "5m"
            elif timeframe == "15m":
                timeframe = "15m"
            elif timeframe == "1h":
                timeframe = "1h"
            elif timeframe == "4h":
                timeframe = "4h"
            else:
                timeframe = "1m"  # Default
            
            # Convertir datos de kline a formato estándar
            timestamp = int(kline_data[0]) / 1000  # Convertir de ms a segundos
            open_price = float(kline_data[1])
            high_price = float(kline_data[2])
            low_price = float(kline_data[3])
            close_price = float(kline_data[4])
            volume = float(kline_data[5])
            
            # Crear DataFrame con el dato
            df = pd.DataFrame([{
                'timestamp': pd.to_datetime(timestamp, unit='s'),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            }])
            
            # Almacenar en base de datos
            db_path = f"data/{symbol}/trading_bot.db"
            success = db_manager.store_historical_data(
                data_to_store=df,
                symbol=symbol,
                timeframe=timeframe,
                db_path=db_path
            )
            
            if success:
                logger.debug(f"📊 Kline WebSocket almacenado: {symbol} {timeframe} - {close_price}")
            else:
                logger.warning(f"⚠️ Error almacenando kline WebSocket: {symbol} {timeframe}")
                
        except Exception as e:
            logger.error(f"❌ Error procesando kline WebSocket: {e}")

    def _get_auth_message(self):
        """Genera mensaje de auth para WS"""
        timestamp = str(int(time.time() * 1000))
        sign = hmac.new(self.credentials.secret_key.encode(), timestamp.encode(), hashlib.sha256).hexdigest()
        return json.dumps({
            "op": "login",
            "args": [self.credentials.api_key, self.credentials.passphrase, timestamp, sign]
        })

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
        collector = BitgetDataCollector()
        download_results = await collector.download_extensive_historical_data(
            symbols, timeframes, datetime.now(timezone.utc) - timedelta(days=days_back)
        )
        
        if not download_results['success']:
            return download_results
        
        # Si se solicita agregación, procesar timeframes agregados
        if use_aggregation and '5m' in timeframes:
            logger.info("🔄 Procesando agregación automática de timeframes")
            
            from .multi_timeframe_coordinator import MultiTimeframeCoordinator
            coordinator = MultiTimeframeCoordinator()
            
            # Obtener datos base (5m)
            base_data = download_results['data'].get('5m', {})
            
            if base_data:
                # Agregar timeframes automáticamente
                aggregated_data = coordinator.auto_aggregate_timeframes(base_data)
                
                # Agregar datos agregados a los resultados
                for tf, data in aggregated_data.items():
                    if tf not in download_results['data']:
                        download_results['data'][tf] = data
                        timeframes.append(tf)
        
        # Almacenar datos en base de datos
        logger.info("💾 Almacenando datos alineados en base de datos")
        
        for symbol in symbols:
            for timeframe in timeframes:
                if symbol in download_results['data'] and timeframe in download_results['data'][symbol]:
                    db_path = f"data/{symbol}/trading_bot.db"
                    session_id = f"multi_tf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    success = db_manager.store_historical_data(
                        download_results['data'][symbol][timeframe], symbol, timeframe, db_path
                    )
                    if success:
                        logger.info(f"✅ Datos {symbol} {timeframe} almacenados correctamente")
                    else:
                        logger.warning(f"⚠️ Error almacenando datos {symbol} {timeframe}")
        
        # Registrar operación
        db_manager.log_download_session(
            session_id=session_id,
            symbols=symbols,
            timeframes=timeframes,
            results=download_results
        )
        
        logger.info(f"✅ Descarga multi-timeframe completada: {sum(len(d) for s in download_results['data'].values() for d in s.values())} registros")
        return download_results
        
    except Exception as e:
        logger.error(f"❌ Error en descarga multi-timeframe: {e}")
        
        # Registrar error
        db_manager.log_download_session(
            session_id=f"multi_tf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbols=symbols,
            timeframes=timeframes,
            results={"success": False, "errors": [str(e)]}
        )
        
        return {
            'success': False,
            'error': str(e),
            'data': {},
            'errors': [str(e)]
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
            from core.config.unified_config import unified_config
            from core.config.config_loader import user_config as _user_config
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
            # Usar configuración centralizada
            from config.unified_config import get_config_manager
            config_manager = get_config_manager()
            symbols = symbols or config_manager.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or ['1h']

    return await download_multi_timeframe_with_alignment(symbols, timeframes, days_back)

# Alias para compatibilidad con bot.py
DataCollector = BitgetDataCollector