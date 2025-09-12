# Ruta: core/data/collector.py
"""
data/collector.py - VERSIÓN PROFESIONAL MEJORADA
Recolector de datos de mercado desde Bitget API
Ubicación: C:\\TradingBot_v10\\data\\collector.py
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
    """Gestor de timeframes"""
    def __init__(self):
        self.timeframes = _get_cfg().get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']

    def to_milliseconds(self, timeframe: str) -> int:
        tf_map = {'1m': 60_000, '5m': 300_000, '15m': 900_000, '1h': 3_600_000, '4h': 14_400_000, '1d': 86_400_000}
        return tf_map.get(timeframe, 60_000)

class BitgetDataCollector:
    """Recolector de datos desde Bitget API"""

    def __init__(self):
        cfg = _get_cfg()
        self.credentials = BitgetCredentials(
            api_key=os.getenv('BITGET_API_KEY', ''),
            secret_key=os.getenv('BITGET_SECRET_KEY', ''),
            passphrase=os.getenv('BITGET_PASSPHRASE', '')
        )
        self.exchange = ccxt.bitget({
            'apiKey': self.credentials.api_key,
            'secret': self.credentials.secret_key,
            'password': self.credentials.passphrase,
            'enableRateLimit': True
        })
        self.timeframe_mgr = TimeframeManager()
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def close(self):
        if self.session:
            await self.session.close()

    async def download_historical_data(self, symbol: str, timeframe: str, start_ts: int, end_ts: int) -> Dict:
        """Descarga datos históricos"""
        try:
            data = []
            current_ts = start_ts
            while current_ts < end_ts:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=current_ts, limit=1000)
                if not ohlcv:
                    break
                data.extend(ohlcv)
                current_ts = ohlcv[-1][0] + self.timeframe_mgr.to_milliseconds(timeframe)
            # Asegurar que los timestamps estén en milisegundos
            processed_data = []
            for d in data:
                timestamp = d[0]
                if timestamp < 10000000000:  # Si está en segundos, convertir a milisegundos
                    timestamp = timestamp * 1000
                processed_data.append({
                    "timestamp": timestamp,
                    "open": d[1],
                    "high": d[2],
                    "low": d[3],
                    "close": d[4],
                    "volume": d[5]
                })
            return {"success": True, "data": processed_data}
        except Exception as e:
            logger.error(f"❌ Error descargando {symbol} {timeframe}: {e}")
            return {"success": False, "error": str(e), "data": []}

    async def start_real_time_collection(self, symbols: List[str], timeframes: List[str]):
        """Inicia recolección en tiempo real"""
        try:
            self.session = aiohttp.ClientSession()
            for symbol in symbols:
                for tf in timeframes:
                    asyncio.create_task(self._collect_real_time(symbol, tf))
        except Exception as e:
            logger.error(f"❌ Error iniciando recolección en tiempo real: {e}")

    async def _collect_real_time(self, symbol: str, timeframe: str):
        """Recolecta datos en tiempo real para un símbolo y timeframe"""
        while True:
            try:
                data = self.exchange.fetch_ohlcv(symbol, timeframe, limit=1)
                if data:
                    # Asegurar que el timestamp esté en milisegundos
                    timestamp = data[0][0]
                    if timestamp < 10000000000:  # Si está en segundos, convertir a milisegundos
                        timestamp = timestamp * 1000
                    
                    market_data = MarketData(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=data[0][1],
                        high=data[0][2],
                        low=data[0][3],
                        close=data[0][4],
                        volume=data[0][5]
                    )
                    db_manager.store_historical_data(symbol, timeframe, [asdict(market_data)])
                await asyncio.sleep(_get_cfg().get('data_collection', {}).get('update_frequency', 5))
            except Exception as e:
                logger.error(f"❌ Error recolectando {symbol} {timeframe}: {e}")
                await asyncio.sleep(5)

async def quick_download_multi_timeframe(
    symbols: List[str] = None,
    timeframes: List[str] = None,
    days_back: int = 365
) -> Dict[str, Any]:
    """Función de conveniencia para descarga multi-timeframe rápida"""
    cfg = _get_cfg()
    symbols = symbols or cfg.get_symbols() or ['BTCUSDT']
    timeframes = timeframes or cfg.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
    collector = BitgetDataCollector()
    try:
        start_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp() * 1000)
        end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        results = {}
        for symbol in symbols:
            symbol_results = {}
            for tf in timeframes:
                result = await collector.download_historical_data(symbol, tf, start_ts, end_ts)
                symbol_results[tf] = result
                if result.get("success"):
                    db_manager.store_historical_data(symbol, tf, result["data"])
            results[symbol] = symbol_results
        return {"success": True, "data": results}
    finally:
        await collector.close()

DataCollector = BitgetDataCollector