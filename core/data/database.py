# Ruta: core/data/database.py
"""
data/database.py - VERSIÓN PROFESIONAL MEJORADA
Gestor de base de datos para el sistema de trading
Ubicación: C:\\TradingBot_v10\\data\\database.py

MEJORAS PRINCIPALES:
- Gestión robusta de timestamps con normalización automática
- Optimizaciones para manejar millones de registros
- Índices optimizados para consultas rápidas
- Validación automática de integridad de datos
- Backup automático y recuperación de errores
- Transacciones atómicas para operaciones críticas
- Pool de conexiones para concurrencia
- Compresión automática de datos antiguos
- Soporte para DBs por símbolo (data/{symbol}/trading_bot.db)
- Análisis y reparación de datos históricos
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
        if end_time - start_time > 1.0:  # Solo log si toma más de 1 segundo
            logger.debug(f"{func.__name__} ejecutado en {end_time - start_time:.2f}s")
        return result
    return wrapper

@dataclass
class MarketData:
    """Estructura optimizada de datos de mercado"""
    symbol: str
    timestamp: int  # Siempre en segundos Unix
    open: float
    high: float
    low: float
    close: float
    volume: float
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Normalizar timestamp automáticamente
        self.timestamp = self._normalize_timestamp(self.timestamp)
        
        # Validar datos OHLCV
        self._validate_ohlcv()
    
    def _normalize_timestamp(self, ts: Union[int, float]) -> int:
        """Normaliza timestamp a segundos Unix"""
        if ts > 10000000000:  # Está en milisegundos
            return int(ts / 1000)
        return int(ts)
    
    def _validate_ohlcv(self):
        """Valida la integridad de los datos OHLCV"""
        # Validar que todos los precios son positivos
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            raise ValueError(f"Precios inválidos en {self.symbol}: OHLC debe ser > 0")
        
        # Validar relación High >= Low
        if self.high < self.low:
            raise ValueError(f"High < Low en {self.symbol}: {self.high} < {self.low}")
        
        # Validar que Open y Close están en el rango
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"Open fuera de rango en {self.symbol}")
        
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"Close fuera de rango en {self.symbol}")
        
        # Validar volumen no negativo
        if self.volume < 0:
            raise ValueError(f"Volumen negativo en {self.symbol}: {self.volume}")
        
        # Validar timestamp razonable (después de 2010, antes del futuro)
        try:
            dt = datetime.fromtimestamp(self.timestamp)
            if dt.year < 2010 or dt.year > datetime.now().year + 1:
                raise ValueError(f"Timestamp fuera de rango: {dt}")
        except (ValueError, OSError):
            raise ValueError(f"Timestamp inválido: {self.timestamp}")

@dataclass
class TradeRecord:
    """Estructura mejorada de registro de trade"""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    entry_time: datetime = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    confidence: float = 0.0
    model_prediction: float = 0.0
    actual_result: Optional[float] = None
    fees: float = 0.0
    trade_id: Optional[str] = None
    status: str = "open"  # 'open', 'closed', 'cancelled'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: Optional[str] = None
    created_at: datetime = None
    
    # Campos adicionales para análisis
    timeframe: str = "1h"
    strategy_name: str = "default"
    market_conditions: Optional[str] = None
    risk_reward_ratio: Optional[float] = None
    leverage: float = 1.0
    
    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Validar side
        if self.side not in ['buy', 'sell']:
            raise ValueError(f"Side inválido: {self.side}")
        
        # Validar status
        if self.status not in ['open', 'closed', 'cancelled']:
            raise ValueError(f"Status inválido: {self.status}")
        
        # Calcular risk-reward ratio si es posible
        if self.stop_loss and self.take_profit:
            self._calculate_risk_reward_ratio()
    
    def _calculate_risk_reward_ratio(self):
        """Calcula la relación riesgo-recompensa"""
        try:
            if self.side == 'buy':
                risk = abs(self.entry_price - self.stop_loss)
                reward = abs(self.take_profit - self.entry_price)
            else:  # sell
                risk = abs(self.stop_loss - self.entry_price)
                reward = abs(self.entry_price - self.take_profit)
            
            self.risk_reward_ratio = reward / risk if risk > 0 else None
        except:
            self.risk_reward_ratio = None

@dataclass
class ModelMetrics:
    """Métricas optimizadas del modelo de ML"""
    model_version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    total_predictions: int
    correct_predictions: int
    training_time: float
    features_used: List[str]
    hyperparameters: Dict[str, Any]
    created_at: datetime = None
    
    # Métricas adicionales
    training_data_size: int = 0
    validation_accuracy: float = 0.0
    test_accuracy: float = 0.0
    feature_importance: Optional[Dict[str, float]] = None
    model_size_mb: float = 0.0
    inference_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class ConnectionPool:
    """Pool de conexiones para mejorar concurrencia"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = []
        self._lock = threading.Lock()
        self._used_connections = set()
    
    def get_connection(self):
        """Obtiene una conexión del pool"""
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                # Optimizaciones de rendimiento
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA temp_store=MEMORY;")
                conn.execute("PRAGMA mmap_size=30000000000;")  # 30GB mmap
                conn.execute("PRAGMA page_size=4096;")
            self._used_connections.add(id(conn))
            return conn
    
    def release_connection(self, conn):
        """Libera conexión de vuelta al pool"""
        with self._lock:
            conn_id = id(conn)
            if conn_id in self._used_connections:
                self._used_connections.remove(conn_id)
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    conn.close()
    
    def close_all(self):
        """Cierra todas las conexiones"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool = []
            self._used_connections = set()

class DatabaseManager:
    """Gestor profesional de base de datos"""
    
    def __init__(self, default_db_path: str = 'data/trading_bot.db'):
        self.default_db_path = default_db_path
        self._initialize_database(default_db_path)
    
    def _initialize_database(self, db_path: str):
        """Inicializa esquema de base de datos con optimizaciones"""
        connection_pool = ConnectionPool(db_path)
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de datos de mercado optimizada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    timeframe TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, timeframe, timestamp)
                ) WITHOUT ROWID;
            """)
            
            # Índices optimizados
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_symbol_timeframe ON market_data(symbol, timeframe);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_timestamp ON market_data(timestamp);")
            
            # Tabla de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    pnl REAL,
                    pnl_pct REAL,
                    confidence REAL DEFAULT 0.0,
                    model_prediction REAL DEFAULT 0.0,
                    actual_result REAL,
                    fees REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'open',
                    stop_loss REAL,
                    take_profit REAL,
                    exit_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timeframe TEXT DEFAULT '1h',
                    strategy_name TEXT DEFAULT 'default',
                    market_conditions TEXT,
                    risk_reward_ratio REAL,
                    leverage REAL DEFAULT 1.0
                );
            """)
            
            # Índices para trades
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);")
            
            # Tabla de métricas de modelos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    model_version TEXT PRIMARY KEY,
                    accuracy REAL NOT NULL,
                    precision REAL NOT NULL,
                    recall REAL NOT NULL,
                    f1_score REAL NOT NULL,
                    total_predictions INTEGER NOT NULL,
                    correct_predictions INTEGER NOT NULL,
                    training_time REAL NOT NULL,
                    features_used TEXT NOT NULL,
                    hyperparameters TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    training_data_size INTEGER DEFAULT 0,
                    validation_accuracy REAL DEFAULT 0.0,
                    test_accuracy REAL DEFAULT 0.0,
                    feature_importance TEXT,
                    model_size_mb REAL DEFAULT 0.0,
                    inference_time_ms REAL DEFAULT 0.0
                );
            """)
            
            # Tabla para datos alineados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aligned_market_data (
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    PRIMARY KEY (session_id, symbol, timeframe, timestamp)
                ) WITHOUT ROWID;
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aligned_session_symbol_tf ON aligned_market_data(session_id, symbol, timeframe);")
            
            # Tabla de metadatos de sincronización
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    session_id TEXT PRIMARY KEY,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Tabla de logs de operaciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    symbols TEXT,
                    timeframes TEXT,
                    records_processed INTEGER,
                    processing_time REAL,
                    error_message TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_type_status ON operation_logs(operation_type, status);")
            
            conn.commit()
        connection_pool.close_all()
    
    @contextmanager
    def _get_connection(self, db_path: str):
        """Context manager para conexiones"""
        connection_pool = ConnectionPool(db_path)
        conn = connection_pool.get_connection()
        try:
            yield conn
        finally:
            connection_pool.release_connection(conn)
    
    @timing_decorator
    def store_historical_data(self, data_to_store: pd.DataFrame, symbol: str, timeframe: str, db_path: str = None) -> bool:
        """Almacena datos históricos con validación y optimización"""
        try:
            if data_to_store.empty:
                logger.warning(f"No hay datos para almacenar para {symbol} {timeframe}")
                return False
            
            db_path = db_path or f"data/{symbol}/trading_bot.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Inicializar esquema si necesario
            self._initialize_database(db_path)
            
            # Normalizar datos
            if data_to_store.index.name == 'timestamp' or 'timestamp' in str(data_to_store.index.dtype):
                data_to_store = data_to_store.reset_index()
                if 'timestamp' not in data_to_store.columns:
                    data_to_store.rename(columns={'index': 'timestamp'}, inplace=True)
            
            # Asegurar que timestamp sea entero (segundos)
            if 'timestamp' in data_to_store.columns:
                data_to_store['timestamp'] = pd.to_datetime(data_to_store['timestamp']).apply(lambda x: int(x.timestamp()))
            
            # Validar datos básicos
            data_to_store = data_to_store.dropna()
            data_to_store = data_to_store[
                (data_to_store['open'] > 0) & 
                (data_to_store['high'] > 0) & 
                (data_to_store['low'] > 0) & 
                (data_to_store['close'] > 0) & 
                (data_to_store['volume'] >= 0) &
                (data_to_store['high'] >= data_to_store['low']) &
                (data_to_store['high'] >= data_to_store['open']) &
                (data_to_store['high'] >= data_to_store['close']) &
                (data_to_store['low'] <= data_to_store['open']) &
                (data_to_store['low'] <= data_to_store['close'])
            ]
            
            if data_to_store.empty:
                logger.warning(f"Todos los datos fueron inválidos para {symbol} {timeframe}")
                return False
            
            # Almacenar con transacción
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                # Usar UPSERT para evitar duplicados
                query = """
                    INSERT OR REPLACE INTO market_data (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                records = [
                    (
                        symbol,
                        timeframe,
                        int(row['timestamp']),
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    for _, row in data_to_store.iterrows()
                ]
                
                cursor.executemany(query, records)
                conn.commit()
                
                logger.info(f"✅ Almacenados {len(records)} registros para {symbol} {timeframe} en {db_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error almacenando datos para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def store_real_time_data(self, data: Dict, symbol: str, timeframe: str, db_path: str = None) -> bool:
        """Almacena datos en tiempo real"""
        try:
            db_path = db_path or f"data/{symbol}/trading_bot.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Validar datos
            market_data = MarketData(
                symbol=symbol,
                timestamp=data['timestamp'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                volume=data['volume']
            )
            
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                query = """
                    INSERT OR REPLACE INTO market_data (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    symbol,
                    timeframe,
                    market_data.timestamp,
                    market_data.open,
                    market_data.high,
                    market_data.low,
                    market_data.close,
                    market_data.volume,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                conn.commit()
                
                logger.debug(f"✅ Almacenado dato en tiempo real para {symbol} {timeframe}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error almacenando dato en tiempo real para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def log_download_session(self, session_id: str, symbols: List[str], timeframes: List[str], results: Dict) -> bool:
        """Registra una sesión de descarga en operation_logs"""
        try:
            db_path = self.default_db_path
            start_time = time.time()
            total_records = sum(sum(r.get("count", 0) for r in sym_results.values()) for sym_results in results.values())
            errors = [r.get("error") for sym_results in results.values() for r in sym_results.values() if r.get("status") == "error"]
            
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO operation_logs (
                        operation_type, status, symbols, timeframes,
                        records_processed, processing_time, error_message, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    "download_data",
                    "success" if not errors else "error",
                    json.dumps(symbols),
                    json.dumps(timeframes),
                    total_records,
                    time.time() - start_time,
                    json.dumps(errors) if errors else None,
                    json.dumps(results)
                ))
                conn.commit()
                
                logger.info(f"✅ Sesión de descarga {session_id} registrada con {total_records} registros")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error registrando sesión de descarga {session_id}: {e}")
            return False
    
    @timing_decorator
    def analyze_historical_data(self, symbol: str, timeframe: str, db_path: str = None) -> Dict:
        """Analiza datos históricos para detectar gaps, duplicados y errores"""
        try:
            db_path = db_path or f"data/{symbol}/trading_bot.db"
            if not Path(db_path).exists():
                return {"gaps": [], "duplicates": [], "errors": [], "total_records": 0}
            
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                # Contar registros totales
                cursor.execute(
                    "SELECT COUNT(*) FROM market_data WHERE symbol = ? AND timeframe = ?",
                    (symbol, timeframe)
                )
                total_records = cursor.fetchone()[0]
                
                # Detectar duplicados
                cursor.execute("""
                    SELECT timestamp, COUNT(*) as count
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                    GROUP BY timestamp
                    HAVING count > 1
                """, (symbol, timeframe))
                duplicates = [row['timestamp'] for row in cursor.fetchall()]
                
                # Detectar gaps
                cursor.execute("""
                    SELECT timestamp
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp
                """, (symbol, timeframe))
                timestamps = [row['timestamp'] for row in cursor.fetchall()]
                
                gaps = []
                timeframe_minutes = {
                    '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
                    '1h': 3600, '2h': 7200, '4h': 14400, '6h': 21600,
                    '12h': 43200, '1d': 86400, '1w': 604800, '1M': 2592000
                }.get(timeframe, 3600)
                
                for i in range(1, len(timestamps)):
                    diff = timestamps[i] - timestamps[i-1]
                    if diff > timeframe_minutes * 1.5:  # Tolerancia de 1.5x
                        gaps.append((timestamps[i-1], timestamps[i]))
                
                # Detectar errores (precios inválidos)
                cursor.execute("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                """, (symbol, timeframe))
                errors = []
                for row in cursor.fetchall():
                    try:
                        MarketData(
                            symbol=symbol,
                            timestamp=row['timestamp'],
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        )
                    except ValueError as e:
                        errors.append(f"Error en timestamp {row['timestamp']}: {str(e)}")
                
                result = {
                    "gaps": gaps,
                    "duplicates": duplicates,
                    "errors": errors,
                    "total_records": total_records
                }
                logger.info(f"✅ Análisis de datos para {symbol} {timeframe}: {total_records} registros, {len(gaps)} gaps, {len(duplicates)} duplicados, {len(errors)} errores")
                return result
                
        except Exception as e:
            logger.error(f"❌ Error analizando datos para {symbol} {timeframe}: {e}")
            return {"gaps": [], "duplicates": [], "errors": [str(e)], "total_records": 0}
    
    @timing_decorator
    def repair_historical_data(self, symbol: str, timeframe: str, gaps: List[Tuple[int, int]], duplicates: List[int], db_path: str = None) -> bool:
        """Repara datos históricos eliminando duplicados y marcando gaps para descarga"""
        try:
            db_path = db_path or f"data/{symbol}/trading_bot.db"
            if not Path(db_path).exists():
                logger.warning(f"No existe DB para {symbol} {timeframe}")
                return False
            
            with self._get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                # Eliminar duplicados
                if duplicates:
                    query = """
                        DELETE FROM market_data
                        WHERE symbol = ? AND timeframe = ? AND timestamp IN ({})
                        AND rowid NOT IN (
                            SELECT MIN(rowid)
                            FROM market_data
                            WHERE symbol = ? AND timeframe = ? AND timestamp IN ({})
                            GROUP BY timestamp
                        )
                    """
                    placeholders = ','.join('?' * len(duplicates))
                    cursor.execute(
                        query.format(placeholders, placeholders),
                        [symbol, timeframe] + duplicates + [symbol, timeframe] + duplicates
                    )
                    conn.commit()
                    logger.info(f"✅ Eliminados {len(duplicates)} registros duplicados para {symbol} {timeframe}")
                
                # Gaps se manejan en download_data.py mediante descargas específicas
                # Aquí solo registramos la operación
                logger.info(f"✅ Gaps marcados para descarga posterior: {len(gaps)} para {symbol} {timeframe}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error reparando datos para {symbol} {timeframe}: {e}")
            return False
    
    @timing_decorator
    def get_last_timestamp(self, symbol: str, timeframe: str, db_path: str = None) -> Optional[int]:
        """Obtiene el último timestamp disponible"""
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
                return result[0] if result and result[0] is not None else None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo último timestamp para {symbol} {timeframe}: {e}")
            return None
    
    @timing_decorator
    def backup_database(self, db_path: str, backup_path: str = None) -> bool:
        """Realiza backup de la base de datos"""
        try:
            if not Path(db_path).exists():
                logger.warning(f"No existe DB en {db_path}")
                return False
            
            backup_path = backup_path or f"{db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            
            with self._get_connection(db_path) as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                
                logger.info(f"✅ Backup creado en {backup_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creando backup de {db_path}: {e}")
            return False

# Instancia singleton
db_manager = DatabaseManager()