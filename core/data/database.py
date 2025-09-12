# Ruta: core/data/database.py
"""
data/database.py - VERSIÓN PROFESIONAL MEJORADA
Gestor de base de datos para el sistema de trading
Ubicación: C:\\TradingBot_v10\\data\\database.py
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import json
from pathlib import Path
import threading
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import asyncio
import aiosqlite
import gzip
import pickle
from concurrent.futures import ThreadPoolExecutor
import time
from functools import wraps

logger = logging.getLogger(__name__)

def timing_decorator(func):
    """Decorator para medir tiempo de ejecución de funciones críticas"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        if end_time - start_time > 1.0:
            logger.debug(f"{func.__name__} ejecutado en {end_time - start_time:.2f}s")
        return result
    return wrapper

@dataclass
class MarketData:
    """Estructura optimizada de datos de mercado"""
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.timestamp = self._normalize_timestamp(self.timestamp)
        self._validate_ohlcv()
    
    def _normalize_timestamp(self, ts: Union[int, float]) -> int:
        if ts > 10000000000:
            return int(ts / 1000)
        return int(ts)
    
    def _validate_ohlcv(self):
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            raise ValueError(f"Precios inválidos en {self.symbol}: OHLC debe ser > 0")
        if self.high < self.low:
            raise ValueError(f"High < Low en {self.symbol}")

class DatabaseManager:
    """Gestor de base de datos"""

    def __init__(self):
        self._connection_pools = {}
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Inicializa las bases de datos por símbolo"""
        from config.unified_config import get_config_manager
        cfg = get_config_manager()
        symbols = cfg.get_symbols() or ['BTCUSDT']
        for symbol in symbols:
            db_path = f"data/{symbol}/trading_bot.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        symbol TEXT,
                        timeframe TEXT,
                        timestamp INTEGER,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        created_at TEXT,
                        PRIMARY KEY (symbol, timeframe, timestamp)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS aligned_market_data (
                        symbol TEXT,
                        timeframe TEXT,
                        timestamp INTEGER,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        created_at TEXT,
                        PRIMARY KEY (symbol, timeframe, timestamp)
                    )
                """)
                # Agregar columnas que faltan si no existen
                columns_to_add = [
                    ("created_at", "TEXT"),
                    ("session_id", "TEXT")
                ]
                
                for column_name, column_type in columns_to_add:
                    try:
                        cursor.execute(f"ALTER TABLE aligned_market_data ADD COLUMN {column_name} {column_type}")
                    except sqlite3.OperationalError:
                        # La columna ya existe, no hacer nada
                        pass
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operation_logs (
                        session_id TEXT,
                        operation TEXT,
                        symbol TEXT,
                        timeframe TEXT,
                        status TEXT,
                        details TEXT,
                        created_at TEXT
                    )
                """)
                # Agregar columnas que faltan si no existen
                columns_to_add = [
                    ("session_id", "TEXT"),
                    ("operation", "TEXT"),
                    ("symbol", "TEXT"),
                    ("timeframe", "TEXT"),
                    ("status", "TEXT"),
                    ("details", "TEXT"),
                    ("created_at", "TEXT")
                ]
                
                for column_name, column_type in columns_to_add:
                    try:
                        cursor.execute(f"ALTER TABLE operation_logs ADD COLUMN {column_name} {column_type}")
                    except sqlite3.OperationalError:
                        # La columna ya existe, no hacer nada
                        pass
                conn.commit()
    
    @contextmanager
    def _get_connection(self, db_path: str):
        with self._lock:
            if db_path not in self._connection_pools:
                self._connection_pools[db_path] = sqlite3.connect(db_path, check_same_thread=False)
        conn = self._connection_pools[db_path]
        try:
            yield conn
        finally:
            pass
    
    @timing_decorator
    def store_historical_data(self, symbol: str, timeframe: str, data: List[Dict]) -> bool:
        """Almacena datos históricos"""
        try:
            db_path = f"data/{symbol}/trading_bot.db"
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                for item in data:
                    # Asegurar que el timestamp esté en milisegundos
                    timestamp = item['timestamp']
                    if timestamp < 10000000000:  # Si está en segundos, convertir a milisegundos
                        timestamp = timestamp * 1000
                    
                    market_data = MarketData(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=item['open'],
                        high=item['high'],
                        low=item['low'],
                        close=item['close'],
                        volume=item['volume']
                    )
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_data
                        (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, timeframe, market_data.timestamp, market_data.open,
                        market_data.high, market_data.low, market_data.close,
                        market_data.volume, market_data.created_at.isoformat()
                    ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error almacenando datos para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def store_aligned_data(self, symbol: str, timeframe: str, data: List[Dict], session_id: str = None) -> bool:
        """Almacena datos alineados"""
        try:
            db_path = f"data/{symbol}/trading_bot.db"
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                for item in data:
                    # Asegurar que el timestamp esté en milisegundos
                    timestamp = item['timestamp']
                    if timestamp < 10000000000:  # Si está en segundos, convertir a milisegundos
                        timestamp = timestamp * 1000
                    
                cursor.execute("""
                        INSERT OR REPLACE INTO aligned_market_data
                        (symbol, timeframe, timestamp, open, high, low, close, volume, created_at, session_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                        symbol, timeframe, timestamp, item['open'],
                        item['high'], item['low'], item['close'],
                        item['volume'], datetime.now().isoformat(), session_id or 'unknown'
                    ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error almacenando datos alineados para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def get_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Obtiene datos históricos"""
        try:
            db_path = f"data/{symbol}/trading_bot.db"
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp
                """, (symbol, timeframe, int(start_date.timestamp()), int(end_date.timestamp())))
                return [
                    {"timestamp": row[0], "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5]}
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos para {symbol} {timeframe}: {e}")
            return []
    
    @timing_decorator
    def repair_data(self, symbol: str, timeframe: str) -> bool:
        """Repara duplicados y registra gaps"""
        try:
            db_path = f"data/{symbol}/trading_bot.db"
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, COUNT(*) as count
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                    GROUP BY timestamp
                    HAVING count > 1
                """, (symbol, timeframe))
                duplicates = [row[0] for row in cursor.fetchall()]
                if duplicates:
                    placeholders = ','.join('?' * len(duplicates))
                    cursor.execute(
                        f"""
                        DELETE FROM market_data
                        WHERE symbol = ? AND timeframe = ? AND timestamp IN ({placeholders})
                        AND rowid NOT IN (
                            SELECT MIN(rowid)
                            FROM market_data
                            WHERE symbol = ? AND timeframe = ? AND timestamp IN ({placeholders})
                        )
                        """,
                        [symbol, timeframe] + duplicates + [symbol, timeframe] + duplicates
                    )
                conn.commit()
                logger.info(f"✅ Eliminados {len(duplicates)} registros duplicados para {symbol} {timeframe}")
                return True
        except Exception as e:
            logger.error(f"❌ Error reparando datos para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def get_last_timestamp(self, symbol: str, timeframe: str, db_path: str = None) -> Optional[int]:
        """Obtiene el último timestamp disponible en milisegundos"""
        try:
            db_path = db_path or f"data/{symbol}/trading_bot.db"
            if not Path(db_path).exists():
                return None
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(timestamp)
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                """, (symbol, timeframe))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    # Convertir a milisegundos si es necesario
                    ts = result[0]
                    if ts < 10000000000:  # Si está en segundos, convertir a milisegundos
                        return ts * 1000
                    return ts
                return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo último timestamp para {symbol} {timeframe}: {e}")
            return None
    
    @timing_decorator
    def log_download_session(self, session_id: str, symbols: List[str], timeframes: List[str], results: Dict):
        """Registra sesión de descarga"""
        try:
            # Simplificar logging para evitar problemas de estructura de tabla
            logger.info(f"📥 Sesión de descarga {session_id}: {len(symbols)} símbolos, {len(timeframes)} timeframes")
        except Exception as e:
            logger.error(f"❌ Error registrando sesión de descarga: {e}")

    @timing_decorator
    def log_alignment_session(self, session_id: str, symbols: List[str], timeframes: List[str], results: Dict):
        """Registra sesión de alineación"""
        try:
            # Simplificar logging para evitar problemas de estructura de tabla
            logger.info(f"🔗 Sesión de alineación {session_id}: {len(symbols)} símbolos, {len(timeframes)} timeframes")
        except Exception as e:
            logger.error(f"❌ Error registrando sesión de alineación: {e}")

db_manager = DatabaseManager()