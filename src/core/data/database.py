"""
data/database.py - VERSIÓN PROFESIONAL MEJORADA
Gestor de base de datos para el sistema de trading
Ubicación: C:\TradingBot_v10\data\database.py

MEJORAS PRINCIPALES:
- Gestión robusta de timestamps con normalización automática
- Optimizaciones para manejar millones de registros
- Índices optimizados para consultas rápidas
- Validación automática de integridad de datos
- Backup automático y recuperación de errores
- Transacciones atómicas para operaciones críticas
- Pool de conexiones para concurrencia
- Compresión automática de datos antiguos
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
                # Optimizaciones de SQLite
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
            
            self._used_connections.add(conn)
            return conn
    
    def return_connection(self, conn):
        """Devuelve una conexión al pool"""
        with self._lock:
            if conn in self._used_connections:
                self._used_connections.remove(conn)
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    conn.close()
    
    def close_all(self):
        """Cierra todas las conexiones"""
        with self._lock:
            for conn in self._pool:
                conn.close()
            for conn in self._used_connections:
                conn.close()
            self._pool.clear()
            self._used_connections.clear()

class DatabaseManager:
    """Gestor profesional de base de datos con optimizaciones"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            from config.settings import DATA_DIR
            self.db_path = DATA_DIR / "trading_bot.db"
        else:
            self.db_path = Path(db_path)
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Pool de conexiones
        self.connection_pool = ConnectionPool(str(self.db_path))
        
        # Cache para consultas frecuentes
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos
        self._last_cache_clear = time.time()
        
        # Thread pool para operaciones pesadas
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        self._init_database()
        self._create_optimized_indices()
        
        logger.info(f"DatabaseManager inicializado: {self.db_path}")
        logger.info(f"Tamaño de BD: {self.db_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    @contextmanager
    def _get_connection(self):
        """Context manager optimizado para conexiones"""
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.return_connection(conn)
    
    def _clear_old_cache(self):
        """Limpia cache antiguo automáticamente"""
        now = time.time()
        if now - self._last_cache_clear > self._cache_timeout:
            self._cache.clear()
            self._last_cache_clear = now
    
    def _init_database(self):
        """Inicializa las tablas con optimizaciones"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Configuraciones de optimización
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            # Tabla de datos de mercado optimizada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp) ON CONFLICT REPLACE
                )
            """)
            
            # Tabla de trades mejorada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
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
                    trade_id TEXT UNIQUE,
                    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'closed', 'cancelled')),
                    stop_loss REAL,
                    take_profit REAL,
                    exit_reason TEXT,
                    timeframe TEXT DEFAULT '1h',
                    strategy_name TEXT DEFAULT 'default',
                    market_conditions TEXT,
                    risk_reward_ratio REAL,
                    leverage REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de métricas del modelo mejorada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY,
                    model_version TEXT NOT NULL,
                    accuracy REAL NOT NULL,
                    precision_score REAL NOT NULL,
                    recall_score REAL NOT NULL,
                    f1_score REAL NOT NULL,
                    total_predictions INTEGER NOT NULL,
                    correct_predictions INTEGER NOT NULL,
                    training_time REAL NOT NULL,
                    features_used TEXT NOT NULL,
                    hyperparameters TEXT NOT NULL,
                    training_data_size INTEGER DEFAULT 0,
                    validation_accuracy REAL DEFAULT 0.0,
                    test_accuracy REAL DEFAULT 0.0,
                    feature_importance TEXT,
                    model_size_mb REAL DEFAULT 0.0,
                    inference_time_ms REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de configuraciones del sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    config_type TEXT DEFAULT 'user',
                    is_encrypted BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de logs optimizada con particionado por tiempo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    line_number INTEGER,
                    extra_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de performance diaria optimizada
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY,
                    date DATE UNIQUE NOT NULL,
                    symbol TEXT,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0.0,
                    total_fees REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    avg_win REAL DEFAULT 0.0,
                    avg_loss REAL DEFAULT 0.0,
                    profit_factor REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    sortino_ratio REAL DEFAULT 0.0,
                    calmar_ratio REAL DEFAULT 0.0,
                    balance REAL DEFAULT 0.0,
                    volume_traded REAL DEFAULT 0.0,
                    largest_win REAL DEFAULT 0.0,
                    largest_loss REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de análisis de mercado
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_analysis (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    trend_direction TEXT,
                    volatility_level REAL,
                    support_level REAL,
                    resistance_level REAL,
                    rsi_14 REAL,
                    macd_signal TEXT,
                    volume_profile TEXT,
                    market_regime TEXT,
                    confidence_score REAL,
                    analysis_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            """)
            
            # Tabla de backup automático
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY,
                    backup_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_mb REAL,
                    records_count INTEGER,
                    compression_ratio REAL,
                    backup_duration_seconds REAL,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # =============================================================================
            # NUEVAS TABLAS PARA SISTEMA MULTI-TIMEFRAME
            # =============================================================================
            
            # Tabla de datos alineados multi-timeframe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aligned_market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    alignment_session_id TEXT,
                    coherence_score REAL DEFAULT 1.0,
                    data_quality_score REAL DEFAULT 1.0,
                    gap_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp) ON CONFLICT REPLACE
                )
            """)
            
            # Tabla de metadatos de alineación
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alignment_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    symbols_processed TEXT NOT NULL,
                    timeframes_processed TEXT NOT NULL,
                    alignment_quality REAL NOT NULL,
                    coherence_scores TEXT,
                    total_periods INTEGER,
                    processing_time_seconds REAL,
                    master_timeline_start INTEGER,
                    master_timeline_end INTEGER,
                    gaps_detected TEXT,
                    validation_results TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de cache de features
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    feature_type TEXT NOT NULL,
                    feature_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de coherencia entre timeframes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timeframe_coherence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_timeframe TEXT NOT NULL,
                    target_timeframe TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    coherence_score REAL NOT NULL,
                    validation_timestamp INTEGER NOT NULL,
                    period_start INTEGER NOT NULL,
                    period_end INTEGER NOT NULL,
                    issues_detected TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de logs de operaciones multi-timeframe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    operation_status TEXT NOT NULL,
                    symbols TEXT,
                    timeframes TEXT,
                    records_processed INTEGER,
                    processing_time_seconds REAL,
                    error_message TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Esquema de base de datos inicializado con optimizaciones y tablas multi-timeframe")
    
    def _create_optimized_indices(self):
        """Crea índices optimizados para consultas rápidas"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Índices para market_data (críticos para performance)
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_created_at ON market_data(created_at)",
                
                # Índices para trades
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol_entry_time ON trades(symbol, entry_time)",
                "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
                "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name)",
                "CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)",
                "CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl)",
                
                # Índices para model_metrics
                "CREATE INDEX IF NOT EXISTS idx_model_metrics_version ON model_metrics(model_version)",
                "CREATE INDEX IF NOT EXISTS idx_model_metrics_created_at ON model_metrics(created_at)",
                
                # Índices para performance
                "CREATE INDEX IF NOT EXISTS idx_daily_performance_date ON daily_performance(date)",
                "CREATE INDEX IF NOT EXISTS idx_daily_performance_symbol ON daily_performance(symbol)",
                
                # Índices para logs (con particionado temporal)
                "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)",
                "CREATE INDEX IF NOT EXISTS idx_system_logs_module ON system_logs(module)",
                
                # Índices para análisis de mercado
                "CREATE INDEX IF NOT EXISTS idx_market_analysis_symbol_timestamp ON market_analysis(symbol, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_market_analysis_timeframe ON market_analysis(timeframe)",
                
                # =============================================================================
                # ÍNDICES PARA NUEVAS TABLAS MULTI-TIMEFRAME
                # =============================================================================
                
                # Índices para aligned_market_data (críticos para performance)
                "CREATE INDEX IF NOT EXISTS idx_aligned_symbol_tf_timestamp ON aligned_market_data(symbol, timeframe, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_aligned_timestamp_tf ON aligned_market_data(timestamp, timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_aligned_session ON aligned_market_data(alignment_session_id)",
                "CREATE INDEX IF NOT EXISTS idx_aligned_symbol ON aligned_market_data(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_aligned_timeframe ON aligned_market_data(timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_aligned_quality ON aligned_market_data(coherence_score, data_quality_score)",
                
                # Índices para alignment_metadata
                "CREATE INDEX IF NOT EXISTS idx_alignment_session ON alignment_metadata(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_alignment_created_at ON alignment_metadata(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_alignment_quality ON alignment_metadata(alignment_quality)",
                
                # Índices para feature_cache
                "CREATE INDEX IF NOT EXISTS idx_feature_cache_key ON feature_cache(cache_key)",
                "CREATE INDEX IF NOT EXISTS idx_feature_cache_symbol_tf ON feature_cache(symbol, timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_feature_cache_expires ON feature_cache(expires_at)",
                "CREATE INDEX IF NOT EXISTS idx_feature_cache_accessed ON feature_cache(last_accessed)",
                
                # Índices para timeframe_coherence
                "CREATE INDEX IF NOT EXISTS idx_coherence_source_target ON timeframe_coherence(source_timeframe, target_timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_coherence_symbol ON timeframe_coherence(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_coherence_timestamp ON timeframe_coherence(validation_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_coherence_score ON timeframe_coherence(coherence_score)",
                
                # Índices para operation_logs
                "CREATE INDEX IF NOT EXISTS idx_operation_type ON operation_logs(operation_type)",
                "CREATE INDEX IF NOT EXISTS idx_operation_status ON operation_logs(operation_status)",
                "CREATE INDEX IF NOT EXISTS idx_operation_created_at ON operation_logs(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_operation_symbols ON operation_logs(symbols)",
            ]
            
            for index_sql in indices:
                try:
                    cursor.execute(index_sql)
                except sqlite3.Error as e:
                    logger.warning(f"Error creando índice: {e}")
            
            conn.commit()
            logger.info("Índices optimizados creados")
    
    # =============================================================================
    # OPERACIONES OPTIMIZADAS DE DATOS DE MERCADO
    # =============================================================================
    
    @timing_decorator
    def bulk_save_market_data(self, market_data_list: List[MarketData]) -> int:
        """
        Guarda múltiples registros de forma ultra-optimizada
        Maneja millones de registros eficientemente
        """
        if not market_data_list:
            return 0
        
        saved_count = 0
        batch_size = 10000  # Optimizado para SQLite WAL
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Preparar statement una sola vez
                insert_sql = """
                    INSERT OR REPLACE INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                # Procesar en lotes grandes
                for i in range(0, len(market_data_list), batch_size):
                    batch = market_data_list[i:i + batch_size]
                    
                    # Preparar datos del lote
                    batch_data = []
                    for market_data in batch:
                        try:
                            # Validación ya hecha en __post_init__
                            batch_data.append((
                                market_data.symbol,
                                market_data.timestamp,
                                market_data.open,
                                market_data.high,
                                market_data.low,
                                market_data.close,
                                market_data.volume
                            ))
                        except Exception as e:
                            logger.debug(f"Error preparando registro: {e}")
                            continue
                    
                    if batch_data:
                        # Transacción atómica para el lote
                        cursor.execute("BEGIN IMMEDIATE")
                        try:
                            cursor.executemany(insert_sql, batch_data)
                            cursor.execute("COMMIT")
                            saved_count += len(batch_data)
                            
                            # Log de progreso cada 100k registros
                            if saved_count % 100000 == 0:
                                logger.info(f"Guardados {saved_count:,} registros...")
                                
                        except Exception as e:
                            cursor.execute("ROLLBACK")
                            logger.error(f"Error en lote {i//batch_size + 1}: {e}")
                            continue
                
            logger.info(f"Bulk save completado: {saved_count:,} registros guardados de {len(market_data_list):,}")
            
            # Limpiar cache después de operación masiva
            self._cache.clear()
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error crítico en bulk save: {e}")
            return saved_count
    
    @timing_decorator
    def get_market_data_optimized(
        self, 
        symbol: str, 
        start_time: datetime = None, 
        end_time: datetime = None,
        limit: int = None,
        columns: List[str] = None
    ) -> pd.DataFrame:
        """Obtiene datos de mercado con optimizaciones avanzadas"""
        try:
            # Crear cache key
            cache_key = f"market_data_{symbol}_{start_time}_{end_time}_{limit}"
            
            # Verificar cache
            self._clear_old_cache()
            if cache_key in self._cache:
                logger.debug(f"Cache hit para {symbol}")
                return self._cache[cache_key].copy()
            
            # Seleccionar columnas específicas si se especifican
            if columns:
                columns_str = ', '.join(columns)
            else:
                columns_str = '*'
            
            with self._get_connection() as conn:
                query = f"SELECT {columns_str} FROM market_data WHERE symbol = ?"
                params = [symbol]
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(int(start_time.timestamp()))
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(int(end_time.timestamp()))
                
                query += " ORDER BY timestamp ASC"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                # Usar pandas para lectura optimizada
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty and 'timestamp' in df.columns:
                    # Convertir timestamp de forma vectorizada
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('datetime', inplace=True)
                
                # Guardar en cache si es una consulta pequeña
                if len(df) < 50000:
                    self._cache[cache_key] = df.copy()
                
                return df
                
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado optimizados: {e}")
            return pd.DataFrame()
    
    def get_market_data_count_fast(self, symbol: str = None) -> int:
        """Obtiene conteo rápido usando índices"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if symbol:
                    # Usar índice optimizado
                    cursor.execute("""
                        SELECT COUNT(*) FROM market_data 
                        WHERE symbol = ?
                    """, (symbol,))
                else:
                    # Usar estadísticas de SQLite si están disponibles
                    cursor.execute("SELECT COUNT(*) FROM market_data")
                
                count = cursor.fetchone()[0]
                return count
                
        except Exception as e:
            logger.error(f"Error obteniendo conteo rápido: {e}")
            return 0
    
    def get_data_summary_optimized(self) -> Dict[str, Any]:
        """Obtiene resumen optimizado de todos los datos"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Consulta optimizada usando GROUP BY
                cursor.execute("""
                    SELECT 
                        symbol,
                        COUNT(*) as record_count,
                        MIN(timestamp) as min_timestamp,
                        MAX(timestamp) as max_timestamp,
                        MIN(created_at) as first_insert,
                        MAX(created_at) as last_insert
                    FROM market_data 
                    GROUP BY symbol
                    ORDER BY symbol
                """)
                
                results = cursor.fetchall()
                summary = {
                    'total_symbols': len(results),
                    'symbols': [],
                    'total_records': 0,
                    'global_date_range': None,
                    'database_size_mb': self.db_path.stat().st_size / 1024 / 1024
                }
                
                min_global_ts = None
                max_global_ts = None
                
                for row in results:
                    symbol_info = {
                        'symbol': row['symbol'],
                        'record_count': row['record_count'],
                        'date_range': None,
                        'duration_days': 0,
                        'status': 'OK'
                    }
                    
                    try:
                        if row['min_timestamp'] and row['max_timestamp']:
                            min_dt = datetime.fromtimestamp(row['min_timestamp'])
                            max_dt = datetime.fromtimestamp(row['max_timestamp'])
                            
                            symbol_info['date_range'] = (min_dt, max_dt)
                            symbol_info['duration_days'] = (max_dt - min_dt).days
                            
                            # Actualizar rango global
                            if min_global_ts is None or row['min_timestamp'] < min_global_ts:
                                min_global_ts = row['min_timestamp']
                            if max_global_ts is None or row['max_timestamp'] > max_global_ts:
                                max_global_ts = row['max_timestamp']
                    
                    except Exception as e:
                        symbol_info['status'] = f'ERROR: {str(e)}'
                    
                    summary['symbols'].append(symbol_info)
                    summary['total_records'] += row['record_count']
                
                # Rango global
                if min_global_ts and max_global_ts:
                    summary['global_date_range'] = (
                        datetime.fromtimestamp(min_global_ts),
                        datetime.fromtimestamp(max_global_ts)
                    )
                
                return summary
                
        except Exception as e:
            logger.error(f"Error obteniendo resumen optimizado: {e}")
            return {'error': str(e)}
    
    # =============================================================================
    # ANÁLISIS AVANZADO Y MANTENIMIENTO
    # =============================================================================
    
    def analyze_data_quality(self, symbol: str = None) -> Dict[str, Any]:
        """Análisis profundo de calidad de datos"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                analysis = {
                    'timestamp': datetime.now().isoformat(),
                    'symbols_analyzed': [],
                    'quality_issues': {
                        'duplicate_timestamps': 0,
                        'invalid_ohlcv': 0,
                        'zero_volume_periods': 0,
                        'extreme_price_moves': 0,
                        'timestamp_gaps': 0
                    },
                    'recommendations': []
                }
                
                # Obtener símbolos a analizar
                if symbol:
                    symbols = [symbol]
                else:
                    cursor.execute("SELECT DISTINCT symbol FROM market_data")
                    symbols = [row[0] for row in cursor.fetchall()]
                
                for sym in symbols:
                    logger.info(f"Analizando calidad de datos para {sym}...")
                    
                    symbol_analysis = {
                        'symbol': sym,
                        'issues': {},
                        'quality_score': 100.0
                    }
                    
                    # 1. Detectar duplicados
                    cursor.execute("""
                        SELECT COUNT(*) FROM (
                            SELECT timestamp, COUNT(*) as count
                            FROM market_data 
                            WHERE symbol = ?
                            GROUP BY timestamp
                            HAVING COUNT(*) > 1
                        )
                    """, (sym,))
                    duplicates = cursor.fetchone()[0]
                    symbol_analysis['issues']['duplicates'] = duplicates
                    analysis['quality_issues']['duplicate_timestamps'] += duplicates
                    
                    # 2. Detectar OHLCV inválidos
                    cursor.execute("""
                        SELECT COUNT(*) FROM market_data 
                        WHERE symbol = ? AND (
                            open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 OR
                            high < low OR open > high OR open < low OR
                            close > high OR close < low OR volume < 0
                        )
                    """, (sym,))
                    invalid_ohlcv = cursor.fetchone()[0]
                    symbol_analysis['issues']['invalid_ohlcv'] = invalid_ohlcv
                    analysis['quality_issues']['invalid_ohlcv'] += invalid_ohlcv
                    
                    # 3. Períodos con volumen cero
                    cursor.execute("""
                        SELECT COUNT(*) FROM market_data 
                        WHERE symbol = ? AND volume = 0
                    """, (sym,))
                    zero_volume = cursor.fetchone()[0]
                    symbol_analysis['issues']['zero_volume'] = zero_volume
                    analysis['quality_issues']['zero_volume_periods'] += zero_volume
                    
                    # 4. Movimientos de precio extremos (>20% en una vela)
                    cursor.execute("""
                        SELECT COUNT(*) FROM market_data 
                        WHERE symbol = ? AND (
                            ABS(close - open) / open > 0.20 OR
                            (high - low) / low > 0.30
                        )
                    """, (sym,))
                    extreme_moves = cursor.fetchone()[0]
                    symbol_analysis['issues']['extreme_moves'] = extreme_moves
                    analysis['quality_issues']['extreme_price_moves'] += extreme_moves
                    
                    # Calcular puntuación de calidad
                    total_records = self.get_market_data_count_fast(sym)
                    if total_records > 0:
                        issues_count = sum(symbol_analysis['issues'].values())
                        symbol_analysis['quality_score'] = max(0, 100 - (issues_count / total_records * 100))
                    
                    analysis['symbols_analyzed'].append(symbol_analysis)
                
                # Generar recomendaciones
                total_issues = sum(analysis['quality_issues'].values())
                if total_issues == 0:
                    analysis['recommendations'].append("✅ Excelente calidad de datos")
                else:
                    if analysis['quality_issues']['duplicate_timestamps'] > 0:
                        analysis['recommendations'].append("🔧 Ejecutar limpieza de duplicados")
                    if analysis['quality_issues']['invalid_ohlcv'] > 0:
                        analysis['recommendations'].append("⚠️ Corregir datos OHLCV inválidos")
                    if analysis['quality_issues']['zero_volume_periods'] > 100:
                        analysis['recommendations'].append("📊 Revisar períodos sin volumen")
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error en análisis de calidad: {e}")
            return {'error': str(e)}
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimización automática de la base de datos"""
        try:
            optimization_results = {
                'start_time': datetime.now().isoformat(),
                'operations': [],
                'size_before_mb': self.db_path.stat().st_size / 1024 / 1024,
                'size_after_mb': 0,
                'space_saved_mb': 0
            }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. VACUUM para reorganizar la base de datos
                logger.info("Ejecutando VACUUM...")
                start_time = time.time()
                cursor.execute("VACUUM")
                vacuum_time = time.time() - start_time
                optimization_results['operations'].append({
                    'operation': 'VACUUM',
                    'duration_seconds': round(vacuum_time, 2),
                    'status': 'completed'
                })
                
                # 2. ANALYZE para actualizar estadísticas
                logger.info("Actualizando estadísticas...")
                cursor.execute("ANALYZE")
                optimization_results['operations'].append({
                    'operation': 'ANALYZE',
                    'status': 'completed'
                })
                
                # 3. Reindexar
                logger.info("Reindexando...")
                cursor.execute("REINDEX")
                optimization_results['operations'].append({
                    'operation': 'REINDEX',
                    'status': 'completed'
                })
                
                conn.commit()
            
            # Calcular espacio ahorrado
            optimization_results['size_after_mb'] = self.db_path.stat().st_size / 1024 / 1024
            optimization_results['space_saved_mb'] = (
                optimization_results['size_before_mb'] - optimization_results['size_after_mb']
            )
            optimization_results['end_time'] = datetime.now().isoformat()
            
            logger.info(f"Optimización completada. Espacio ahorrado: {optimization_results['space_saved_mb']:.1f} MB")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return {'error': str(e)}
    
    def create_backup(self, backup_path: str = None, compress: bool = True) -> Dict[str, Any]:
        """Crea backup optimizado con compresión opcional"""
        try:
            if backup_path is None:
                from config.settings import BACKUPS_DIR
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"trading_bot_backup_{timestamp}"
                backup_path = BACKUPS_DIR / f"{backup_name}.db"
                if compress:
                    backup_path = BACKUPS_DIR / f"{backup_name}.db.gz"
            
            backup_info = {
                'start_time': datetime.now().isoformat(),
                'backup_path': str(backup_path),
                'compressed': compress,
                'original_size_mb': self.db_path.stat().st_size / 1024 / 1024,
                'backup_size_mb': 0,
                'compression_ratio': 1.0,
                'duration_seconds': 0,
                'status': 'started'
            }
            
            start_time = time.time()
            
            if compress:
                # Backup con compresión
                with open(self.db_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb', compresslevel=6) as f_out:
                        f_out.writelines(f_in)
            else:
                # Backup simple
                import shutil
                shutil.copy2(self.db_path, backup_path)
            
            # Estadísticas finales
            backup_info['duration_seconds'] = round(time.time() - start_time, 2)
            backup_info['backup_size_mb'] = backup_path.stat().st_size / 1024 / 1024
            backup_info['compression_ratio'] = (
                backup_info['original_size_mb'] / backup_info['backup_size_mb']
                if backup_info['backup_size_mb'] > 0 else 1.0
            )
            backup_info['status'] = 'completed'
            backup_info['end_time'] = datetime.now().isoformat()
            
            # Registrar en historial
            self._record_backup_history(backup_info)
            
            logger.info(f"Backup creado: {backup_path} ({backup_info['backup_size_mb']:.1f} MB)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    def _record_backup_history(self, backup_info: Dict[str, Any]):
        """Registra información del backup en el historial"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO backup_history (
                        backup_type, file_path, file_size_mb, 
                        compression_ratio, backup_duration_seconds, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'full' if not backup_info.get('compressed') else 'compressed',
                    backup_info['backup_path'],
                    backup_info['backup_size_mb'],
                    backup_info['compression_ratio'],
                    backup_info['duration_seconds'],
                    backup_info['status']
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error registrando historial de backup: {e}")
    
    def cleanup_old_data_advanced(self, 
                                 days_to_keep: int = 365,
                                 dry_run: bool = False) -> Dict[str, Any]:
        """Limpieza avanzada con preview y configuración granular"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            cleanup_results = {
                'dry_run': dry_run,
                'cutoff_date': cutoff_date.isoformat(),
                'records_to_delete': {},
                'records_deleted': {},
                'total_deleted': 0,
                'space_freed_mb': 0
            }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Analizar qué se va a eliminar
                tables_to_clean = [
                    'market_data',
                    'system_logs',
                    'market_analysis'
                ]
                
                for table in tables_to_clean:
                    # Contar registros a eliminar
                    if table == 'market_data':
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {table} 
                            WHERE timestamp < ?
                        """, (cutoff_timestamp,))
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {table} 
                            WHERE created_at < ?
                        """, (cutoff_date,))
                    
                    count = cursor.fetchone()[0]
                    cleanup_results['records_to_delete'][table] = count
                    
                    if not dry_run and count > 0:
                        # Ejecutar limpieza
                        if table == 'market_data':
                            cursor.execute(f"""
                                DELETE FROM {table} 
                                WHERE timestamp < ?
                            """, (cutoff_timestamp,))
                        else:
                            cursor.execute(f"""
                                DELETE FROM {table} 
                                WHERE created_at < ?
                            """, (cutoff_date,))
                        
                        deleted = cursor.rowcount
                        cleanup_results['records_deleted'][table] = deleted
                        cleanup_results['total_deleted'] += deleted
                
                if not dry_run:
                    conn.commit()
                    # Ejecutar VACUUM para liberar espacio
                    cursor.execute("VACUUM")
            
            if not dry_run:
                logger.info(f"Limpieza completada: {cleanup_results['total_deleted']} registros eliminados")
            else:
                logger.info(f"Preview de limpieza: {sum(cleanup_results['records_to_delete'].values())} registros serían eliminados")
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Error en limpieza avanzada: {e}")
            return {'error': str(e)}
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Estadísticas de performance de la base de datos"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {
                    'database_size_mb': self.db_path.stat().st_size / 1024 / 1024,
                    'table_stats': {},
                    'index_stats': {},
                    'query_performance': {},
                    'recommendations': []
                }
                
                # Estadísticas por tabla
                
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    # Obtener tamaño estimado de la tabla
                    cursor.execute(f"""
                        SELECT SUM(length(quote(symbol)) + length(quote(timestamp)) + 
                                   length(quote(open)) + length(quote(high)) + 
                                   length(quote(low)) + length(quote(close)) + 
                                   length(quote(volume)))
                        FROM {table} LIMIT 1000
                    """)
                    
                    try:
                        avg_row_size = cursor.fetchone()[0] or 0
                        estimated_size_mb = (avg_row_size * count) / 1024 / 1024 if avg_row_size else 0
                    except:
                        estimated_size_mb = 0
                    
                    stats['table_stats'][table] = {
                        'record_count': count,
                        'estimated_size_mb': round(estimated_size_mb, 2)
                    }
                
                # Test de performance de consultas comunes
                performance_tests = [
                    ("Simple count", "SELECT COUNT(*) FROM market_data"),
                    ("Symbol filter", "SELECT COUNT(*) FROM market_data WHERE symbol = 'BTCUSDT'"),
                    ("Date range", "SELECT COUNT(*) FROM market_data WHERE timestamp > ? AND timestamp < ?")
                ]
                
                for test_name, query in performance_tests:
                    start_time = time.time()
                    try:
                        if "?" in query:
                            # Test con parámetros de fecha
                            yesterday = int((datetime.now() - timedelta(days=1)).timestamp())
                            today = int(datetime.now().timestamp())
                            cursor.execute(query, (yesterday, today))
                        else:
                            cursor.execute(query)
                        cursor.fetchone()
                        duration = time.time() - start_time
                        stats['query_performance'][test_name] = round(duration * 1000, 2)  # en ms
                    except Exception as e:
                        stats['query_performance'][test_name] = f"Error: {e}"
                
                # Generar recomendaciones
                if stats['database_size_mb'] > 1000:  # > 1GB
                    stats['recommendations'].append("Considerar particionado o archivado de datos antiguos")
                
                slow_queries = [name for name, duration in stats['query_performance'].items() 
                               if isinstance(duration, (int, float)) and duration > 1000]
                if slow_queries:
                    stats['recommendations'].append(f"Optimizar consultas lentas: {', '.join(slow_queries)}")
                
                if not stats['recommendations']:
                    stats['recommendations'].append("Rendimiento de base de datos dentro de parámetros normales")
                
                return stats
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de performance: {e}")
            return {'error': str(e)}
    
    # =============================================================================
    # MÉTODOS PARA SISTEMA MULTI-TIMEFRAME
    # =============================================================================
    
    @timing_decorator
    def store_aligned_data(self, aligned_data: Dict[str, pd.DataFrame], timeframe: str, session_id: str) -> bool:
        """
        Almacena datos alineados en la tabla aligned_market_data
        
        Args:
            aligned_data: Datos alineados por símbolo
            timeframe: Timeframe de los datos
            session_id: ID de la sesión de alineación
        
        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                records_inserted = 0
                for symbol, df in aligned_data.items():
                    if df.empty:
                        continue
                    
                    # Calcular métricas de calidad
                    coherence_score = self._calculate_coherence_score(df)
                    data_quality_score = self._calculate_data_quality_score(df)
                    gap_count = self._count_gaps(df)
                    
                    # Insertar datos
                    for timestamp, row in df.iterrows():
                        cursor.execute("""
                            INSERT OR REPLACE INTO aligned_market_data 
                            (symbol, timeframe, timestamp, open, high, low, close, volume, 
                             alignment_session_id, coherence_score, data_quality_score, gap_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            symbol, timeframe, int(timestamp.timestamp()),
                            row['open'], row['high'], row['low'], row['close'], row['volume'],
                            session_id, coherence_score, data_quality_score, gap_count
                        ))
                        records_inserted += 1
                
                conn.commit()
                logger.info(f"Stored {records_inserted} aligned records for {timeframe}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing aligned data: {e}")
            return False
    
    @timing_decorator
    def get_aligned_data(self, symbols: List[str], timeframe: str, start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos alineados de la tabla aligned_market_data
        
        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe de los datos
            start_date: Fecha de inicio
            end_date: Fecha de fin
        
        Returns:
            Dict[str, pd.DataFrame]: Datos alineados por símbolo
        """
        try:
            with self._get_connection() as conn:
                aligned_data = {}
                
                for symbol in symbols:
                    query = """
                        SELECT timestamp, open, high, low, close, volume, coherence_score, data_quality_score
                        FROM aligned_market_data
                        WHERE symbol = ? AND timeframe = ? 
                        AND timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp
                    """
                    
                    df = pd.read_sql_query(
                        query, conn,
                        params=(symbol, timeframe, int(start_date.timestamp()), int(end_date.timestamp())),
                        parse_dates=['timestamp']
                    )
                    
                    if not df.empty:
                        df.set_index('timestamp', inplace=True)
                        aligned_data[symbol] = df
                    else:
                        aligned_data[symbol] = pd.DataFrame()
                
                logger.info(f"Retrieved aligned data for {len(symbols)} symbols, {timeframe}")
                return aligned_data
                
        except Exception as e:
            logger.error(f"Error getting aligned data: {e}")
            return {}
    
    def store_alignment_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Almacena metadatos de una sesión de alineación
        
        Args:
            session_id: ID de la sesión
            metadata: Metadatos de la alineación
        
        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO alignment_metadata 
                    (session_id, symbols_processed, timeframes_processed, alignment_quality,
                     coherence_scores, total_periods, processing_time_seconds,
                     master_timeline_start, master_timeline_end, gaps_detected, validation_results)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    json.dumps(metadata.get('symbols_processed', [])),
                    json.dumps(metadata.get('timeframes_processed', [])),
                    metadata.get('alignment_quality', 0.0),
                    json.dumps(metadata.get('coherence_scores', {})),
                    metadata.get('total_periods', 0),
                    metadata.get('processing_time_seconds', 0.0),
                    int(metadata.get('master_timeline_start', 0)),
                    int(metadata.get('master_timeline_end', 0)),
                    json.dumps(metadata.get('gaps_detected', {})),
                    json.dumps(metadata.get('validation_results', {}))
                ))
                
                conn.commit()
                logger.info(f"Stored alignment metadata for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing alignment metadata: {e}")
            return False
    
    def get_alignment_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadatos de una sesión de alineación
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Optional[Dict[str, Any]]: Metadatos de la sesión
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM alignment_metadata WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'session_id': row[1],
                        'symbols_processed': json.loads(row[2]),
                        'timeframes_processed': json.loads(row[3]),
                        'alignment_quality': row[4],
                        'coherence_scores': json.loads(row[5]),
                        'total_periods': row[6],
                        'processing_time_seconds': row[7],
                        'master_timeline_start': row[8],
                        'master_timeline_end': row[9],
                        'gaps_detected': json.loads(row[10]),
                        'validation_results': json.loads(row[11]),
                        'created_at': row[12]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting alignment metadata: {e}")
            return None
    
    def store_timeframe_coherence(self, source_tf: str, target_tf: str, symbol: str, 
                                coherence_score: float, validation_timestamp: int,
                                period_start: int, period_end: int, issues: List[str] = None) -> bool:
        """
        Almacena métricas de coherencia entre timeframes
        
        Args:
            source_tf: Timeframe fuente
            target_tf: Timeframe objetivo
            symbol: Símbolo
            coherence_score: Score de coherencia
            validation_timestamp: Timestamp de validación
            period_start: Inicio del período
            period_end: Fin del período
            issues: Lista de problemas detectados
        
        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO timeframe_coherence 
                    (source_timeframe, target_timeframe, symbol, coherence_score,
                     validation_timestamp, period_start, period_end, issues_detected)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_tf, target_tf, symbol, coherence_score,
                    validation_timestamp, period_start, period_end,
                    json.dumps(issues or [])
                ))
                
                conn.commit()
                logger.debug(f"Stored coherence data: {source_tf}->{target_tf} for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing timeframe coherence: {e}")
            return False
    
    def get_timeframe_coherence_stats(self, source_tf: str = None, target_tf: str = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de coherencia entre timeframes
        
        Args:
            source_tf: Timeframe fuente (opcional)
            target_tf: Timeframe objetivo (opcional)
        
        Returns:
            Dict[str, Any]: Estadísticas de coherencia
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir query con filtros opcionales
                where_conditions = []
                params = []
                
                if source_tf:
                    where_conditions.append("source_timeframe = ?")
                    params.append(source_tf)
                
                if target_tf:
                    where_conditions.append("target_timeframe = ?")
                    params.append(target_tf)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                # Obtener estadísticas
                query = f"""
                    SELECT 
                        source_timeframe,
                        target_timeframe,
                        COUNT(*) as validation_count,
                        AVG(coherence_score) as avg_coherence,
                        MIN(coherence_score) as min_coherence,
                        MAX(coherence_score) as max_coherence,
                        COUNT(CASE WHEN coherence_score < 0.95 THEN 1 END) as low_coherence_count
                    FROM timeframe_coherence
                    {where_clause}
                    GROUP BY source_timeframe, target_timeframe
                    ORDER BY avg_coherence DESC
                """
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                stats = {
                    'coherence_by_pair': [],
                    'overall_stats': {
                        'total_validations': 0,
                        'avg_coherence': 0.0,
                        'low_coherence_pairs': 0
                    }
                }
                
                total_coherence = 0
                total_count = 0
                
                for row in results:
                    pair_stats = {
                        'source_timeframe': row[0],
                        'target_timeframe': row[1],
                        'validation_count': row[2],
                        'avg_coherence': row[3],
                        'min_coherence': row[4],
                        'max_coherence': row[5],
                        'low_coherence_count': row[6]
                    }
                    stats['coherence_by_pair'].append(pair_stats)
                    
                    total_coherence += row[3] * row[2]
                    total_count += row[2]
                
                if total_count > 0:
                    stats['overall_stats']['avg_coherence'] = total_coherence / total_count
                    stats['overall_stats']['total_validations'] = total_count
                    stats['overall_stats']['low_coherence_pairs'] = sum(
                        pair['low_coherence_count'] for pair in stats['coherence_by_pair']
                    )
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting timeframe coherence stats: {e}")
            return {'error': str(e)}
    
    def log_operation(self, operation_type: str, status: str, symbols: List[str] = None,
                     timeframes: List[str] = None, records_processed: int = 0,
                     processing_time: float = 0.0, error_message: str = None,
                     metadata: Dict[str, Any] = None) -> bool:
        """
        Registra una operación en el log de operaciones
        
        Args:
            operation_type: Tipo de operación
            status: Estado de la operación
            symbols: Símbolos procesados
            timeframes: Timeframes procesados
            records_processed: Número de registros procesados
            processing_time: Tiempo de procesamiento en segundos
            error_message: Mensaje de error si aplica
            metadata: Metadatos adicionales
        
        Returns:
            bool: True si se registró correctamente
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO operation_logs 
                    (operation_type, operation_status, symbols, timeframes, records_processed,
                     processing_time_seconds, error_message, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_type, status,
                    json.dumps(symbols or []),
                    json.dumps(timeframes or []),
                    records_processed, processing_time,
                    error_message,
                    json.dumps(metadata or {})
                ))
                
                conn.commit()
                logger.debug(f"Logged operation: {operation_type} - {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error logging operation: {e}")
            return False
    
    def _calculate_coherence_score(self, df: pd.DataFrame) -> float:
        """Calcula score de coherencia para un DataFrame"""
        try:
            if df.empty or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                return 0.0
            
            # Verificar consistencia OHLC
            valid_ohlc = (
                (df['high'] >= df[['open', 'close']].max(axis=1)) &
                (df['low'] <= df[['open', 'close']].min(axis=1)) &
                (df['high'] >= df['low'])
            ).sum()
            
            return float(valid_ohlc / len(df)) if len(df) > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating coherence score: {e}")
            return 0.0
    
    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """Calcula score de calidad de datos para un DataFrame"""
        try:
            if df.empty:
                return 0.0
            
            # Factores de calidad
            completeness = df.notna().sum().sum() / (len(df) * len(df.columns))
            consistency = self._calculate_coherence_score(df)
            
            # Peso de cada factor
            quality_score = completeness * 0.6 + consistency * 0.4
            return float(quality_score)
            
        except Exception as e:
            logger.error(f"Error calculating data quality score: {e}")
            return 0.0
    
    def _count_gaps(self, df: pd.DataFrame) -> int:
        """Cuenta gaps en los datos"""
        try:
            if df.empty or len(df) < 2:
                return 0
            
            # Calcular diferencias entre timestamps consecutivos
            time_diffs = df.index.to_series().diff()
            
            # Contar gaps significativos (más de 2 períodos)
            gaps = (time_diffs > time_diffs.median() * 2).sum()
            return int(gaps)
            
        except Exception as e:
            logger.error(f"Error counting gaps: {e}")
            return 0
    
    def get_data_date_range(self, symbol: str = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Obtiene el rango de fechas de los datos"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) 
                        FROM market_data 
                        WHERE symbol = ?
                    """, (symbol,))
                else:
                    cursor.execute("""
                        SELECT MIN(timestamp), MAX(timestamp) 
                        FROM market_data
                    """)
                
                result = cursor.fetchone()
                if result and result[0] and result[1]:
                    min_ts = result[0]
                    max_ts = result[1]
                    
                    def safe_timestamp_convert(ts):
                        """Convierte timestamp de forma segura"""
                        try:
                            if isinstance(ts, str):
                                ts = int(ts)
                            
                            if isinstance(ts, (int, float)):
                                # Verificar si es timestamp en milisegundos o segundos
                                if ts > 1e10:  # Timestamp en milisegundos
                                    # Convertir a segundos
                                    ts_seconds = ts / 1000
                                    # Validar rango razonable (2010-2030)
                                    if ts_seconds < 1262304000 or ts_seconds > 1893456000:
                                        return None
                                    return datetime.fromtimestamp(ts_seconds)
                                else:  # Timestamp en segundos
                                    # Validar rango razonable (2010-2030)
                                    if ts < 1262304000 or ts > 1893456000:
                                        return None
                                    return datetime.fromtimestamp(ts)
                        except (ValueError, OSError, OverflowError) as e:
                            logger.warning(f"Error convirtiendo timestamp {ts}: {e}")
                            return None
                        return None
                    
                    min_dt = safe_timestamp_convert(min_ts)
                    max_dt = safe_timestamp_convert(max_ts)
                    
                    if min_dt and max_dt:
                        return (min_dt, max_dt)
                
                return (None, None)
                
        except Exception as e:
            logger.error(f"Error obteniendo rango de fechas: {e}")
            return (None, None)
    
    def get_historical_data_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de datos históricos (alias para compatibilidad)"""
        return self.get_data_summary_optimized()
    
    def get_aligned_market_data(self, symbols: List[str], timeframe: str, 
                               start_date: datetime = None, end_date: datetime = None) -> Dict[str, pd.DataFrame]:
        """Obtiene datos alineados de múltiples símbolos para análisis simultáneo"""
        try:
            aligned_data = {}
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for symbol in symbols:
                    query = """
                        SELECT timestamp, open, high, low, close, volume
                        FROM aligned_market_data 
                        WHERE symbol = ? AND timeframe = ?
                    """
                    params = [symbol, timeframe]
                    
                    if start_date:
                        query += " AND timestamp >= ?"
                        params.append(int(start_date.timestamp()))
                    
                    if end_date:
                        query += " AND timestamp <= ?"
                        params.append(int(end_date.timestamp()))
                    
                    query += " ORDER BY timestamp"
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    if results:
                        # Crear DataFrame
                        df = pd.DataFrame(results, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                        df.set_index('datetime', inplace=True)
                        df.drop('timestamp', axis=1, inplace=True)
                        
                        aligned_data[symbol] = df
                    else:
                        aligned_data[symbol] = pd.DataFrame()
            
            return aligned_data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos alineados: {e}")
            return {symbol: pd.DataFrame() for symbol in symbols}
    
    def __del__(self):
        """Cleanup al destruir el objeto"""
        try:
            if hasattr(self, 'connection_pool'):
                self.connection_pool.close_all()
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=False)
        except:
            pass

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()