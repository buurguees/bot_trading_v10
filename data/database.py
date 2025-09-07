"""
data/database.py
Gestor de base de datos para el sistema de trading
Ubicación: C:\\TradingBot_v10\\data\\database.py

Maneja todas las operaciones de base de datos incluyendo:
- Datos de mercado históricos y en tiempo real
- Trades ejecutados y su performance
- Métricas del modelo de ML
- Configuraciones y logs del sistema
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
from pathlib import Path
import threading
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import asyncio
import aiosqlite

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Estructura de datos de mercado"""
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

@dataclass
class TradeRecord:
    """Estructura de registro de trade"""
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
    
    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ModelMetrics:
    """Métricas del modelo de ML"""
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
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class DatabaseManager:
    """Gestor principal de base de datos"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            from config.settings import DATA_DIR
            self.db_path = DATA_DIR / "trading_bot.db"
        else:
            self.db_path = Path(db_path)
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
        
        logger.info(f"Base de datos inicializada: {self.db_path}")
    
    def _init_database(self):
        """Inicializa las tablas de la base de datos"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de datos de mercado
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp)
                )
            """)
            
            # Índices para optimizar consultas
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp 
                ON market_data(symbol, timestamp)
            """)
            
            # Tabla de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_entry_time 
                ON trades(symbol, entry_time)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_status 
                ON trades(status)
            """)
            
            # Tabla de métricas del modelo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    accuracy REAL NOT NULL,
                    precision_score REAL NOT NULL,
                    recall_score REAL NOT NULL,
                    f1_score REAL NOT NULL,
                    total_predictions INTEGER NOT NULL,
                    correct_predictions INTEGER NOT NULL,
                    training_time REAL NOT NULL,
                    features_used TEXT NOT NULL,  -- JSON string
                    hyperparameters TEXT NOT NULL,  -- JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de configuraciones del sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,  -- JSON string
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de logs de sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    line_number INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de performance diaria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
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
                    balance REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Esquema de base de datos inicializado exitosamente")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones de base de datos thread-safe"""
        with self._lock:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
            try:
                yield conn
            finally:
                conn.close()
    
    # =============================================================================
    # OPERACIONES DE DATOS DE MERCADO
    # =============================================================================
    
    def insert_market_data(self, data: MarketData) -> bool:
        """Inserta datos de mercado"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.symbol, data.timestamp, data.open, data.high,
                    data.low, data.close, data.volume, data.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error insertando datos de mercado: {e}")
            return False
    
    def insert_market_data_bulk(self, data_list: List[MarketData]) -> int:
        """Inserta múltiples datos de mercado de forma eficiente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data_tuples = [
                    (d.symbol, d.timestamp, d.open, d.high, d.low, d.close, d.volume, d.created_at)
                    for d in data_list
                ]
                cursor.executemany("""
                    INSERT OR REPLACE INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, data_tuples)
                conn.commit()
                return len(data_list)
        except Exception as e:
            logger.error(f"Error insertando datos de mercado en bulk: {e}")
            return 0
    
    def save_market_data(self, market_data: MarketData) -> bool:
        """
        Guarda un registro de datos de mercado en la base de datos
        
        Args:
            market_data: Objeto MarketData a guardar
            
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si ya existe el registro (evitar duplicados)
                cursor.execute("""
                    SELECT id FROM market_data 
                    WHERE symbol = ? AND timestamp = ?
                """, (market_data.symbol, market_data.timestamp))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Actualizar registro existente
                    cursor.execute("""
                        UPDATE market_data 
                        SET open = ?, high = ?, low = ?, close = ?, volume = ?
                        WHERE symbol = ? AND timestamp = ?
                    """, (market_data.open, market_data.high, market_data.low, 
                          market_data.close, market_data.volume, 
                          market_data.symbol, market_data.timestamp))
                    logger.debug(f"Actualizado registro existente: {market_data.symbol} - {market_data.timestamp}")
                else:
                    # Insertar nuevo registro
                    cursor.execute("""
                        INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (market_data.symbol, market_data.timestamp, market_data.open,
                          market_data.high, market_data.low, market_data.close, market_data.volume))
                    logger.debug(f"Insertado nuevo registro: {market_data.symbol} - {market_data.timestamp}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error guardando datos de mercado: {e}")
            return False

    def bulk_save_market_data(self, market_data_list: List[MarketData]) -> int:
        """
        Guarda múltiples registros de datos de mercado de forma eficiente
        
        Args:
            market_data_list: Lista de objetos MarketData
            
        Returns:
            Número de registros guardados exitosamente
        """
        if not market_data_list:
            return 0
        
        saved_count = 0
        batch_size = 1000  # Procesar en lotes para evitar memory issues
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for i in range(0, len(market_data_list), batch_size):
                    batch = market_data_list[i:i + batch_size]
                    
                    for market_data in batch:
                        try:
                            # Verificar duplicados
                            cursor.execute("""
                                SELECT id FROM market_data 
                                WHERE symbol = ? AND timestamp = ?
                            """, (market_data.symbol, market_data.timestamp))
                            
                            existing = cursor.fetchone()
                            
                            if not existing:
                                cursor.execute("""
                                    INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (market_data.symbol, market_data.timestamp, market_data.open,
                                      market_data.high, market_data.low, market_data.close, market_data.volume))
                                saved_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error en registro individual: {e}")
                            continue
                    
                    # Commit del lote
                    conn.commit()
                    logger.debug(f"Lote {i//batch_size + 1} procesado: {len(batch)} registros")
                
            logger.info(f"Bulk save completado: {saved_count} registros guardados de {len(market_data_list)} totales")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error en bulk save: {e}")
            return saved_count

    def get_market_data_count(self, symbol: str = None) -> int:
        """
        Obtiene el conteo de registros de datos de mercado
        
        Args:
            symbol: Símbolo específico (opcional)
            
        Returns:
            Número de registros
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol = ?", (symbol,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM market_data")
                
                count = cursor.fetchone()[0]
                return count
                
        except Exception as e:
            logger.error(f"Error obteniendo conteo de datos: {e}")
            return 0

    def get_symbols_list(self) -> List[str]:
        """
        Obtiene lista de símbolos únicos en la base de datos
        
        Returns:
            Lista de símbolos únicos
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT symbol FROM market_data ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]
                return symbols
                
        except Exception as e:
            logger.error(f"Error obteniendo lista de símbolos: {e}")
            return []

    def get_data_date_range(self, symbol: str) -> tuple:
        """
        Obtiene el rango de fechas disponible para un símbolo
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            Tupla (fecha_inicio, fecha_fin) o (None, None) si no hay datos
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) 
                    FROM market_data 
                    WHERE symbol = ?
                """, (symbol,))
                
                result = cursor.fetchone()
                
                if result and result[0] is not None and result[1] is not None:
                    try:
                        start_date = datetime.fromtimestamp(result[0])
                        end_date = datetime.fromtimestamp(result[1])
                        return (start_date, end_date)
                    except (ValueError, OSError) as e:
                        logger.error(f"Error convirtiendo timestamp: {e}")
                        return (None, None)
                else:
                    return (None, None)
                    
        except Exception as e:
            logger.error(f"Error obteniendo rango de fechas: {e}")
            return (None, None)

    def clean_old_data(self, days_to_keep: int = 365) -> int:
        """
        Limpia datos antiguos para mantener la base de datos optimizada
        
        Args:
            days_to_keep: Días de datos a mantener
            
        Returns:
            Número de registros eliminados
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM market_data 
                    WHERE timestamp < ?
                """, (cutoff_timestamp,))
                
                deleted = cursor.rowcount
                conn.commit()
                
            logger.info(f"Limpieza completada: {deleted} registros antiguos eliminados")
            return deleted
            
        except Exception as e:
            logger.error(f"Error limpiando datos antiguos: {e}")
            return 0

    def verify_data_integrity(self, symbol: str = None) -> Dict[str, Any]:
        """
        Verifica la integridad de los datos en la base de datos
        
        Args:
            symbol: Símbolo específico a verificar (opcional)
            
        Returns:
            Diccionario con estadísticas de integridad
        """
        try:
            stats = {
                'total_records': 0,
                'symbols': [],
                'date_ranges': {},
                'gaps_detected': {},
                'duplicate_timestamps': {},
                'invalid_data': 0
            }
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Estadísticas generales
                if symbol:
                    cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol = ?", (symbol,))
                    stats['total_records'] = cursor.fetchone()[0]
                    symbols_to_check = [symbol]
                else:
                    cursor.execute("SELECT COUNT(*) FROM market_data")
                    stats['total_records'] = cursor.fetchone()[0]
                    cursor.execute("SELECT DISTINCT symbol FROM market_data")
                    symbols_to_check = [row[0] for row in cursor.fetchall()]
                stats['symbols'] = symbols_to_check
                
                # Verificar cada símbolo
                for sym in symbols_to_check:
                    # Rango de fechas
                    date_range = self.get_data_date_range(sym)
                    stats['date_ranges'][sym] = date_range
                    
                    # Detectar duplicados
                    cursor.execute("""
                        SELECT timestamp, COUNT(*) as count
                        FROM market_data 
                        WHERE symbol = ?
                        GROUP BY timestamp
                        HAVING COUNT(*) > 1
                    """, (sym,))
                    
                    duplicates = cursor.fetchall()
                    stats['duplicate_timestamps'][sym] = len(duplicates)
                    
                    # Detectar datos inválidos (precios <= 0)
                    cursor.execute("""
                        SELECT COUNT(*) FROM market_data 
                        WHERE symbol = ? AND (
                            open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 OR volume < 0
                        )
                    """, (sym,))
                    
                    invalid = cursor.fetchone()[0]
                    stats['invalid_data'] += invalid
            
            return stats
            
        except Exception as e:
            logger.error(f"Error verificando integridad de datos: {e}")
            return {'error': str(e)}
    
    def get_market_data(
        self, 
        symbol: str, 
        start_time: datetime = None, 
        end_time: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:
        """Obtiene datos de mercado históricos"""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM market_data WHERE symbol = ?"
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
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('datetime', inplace=True)
                
                return df
                
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {e}")
            return pd.DataFrame()
    
    def get_latest_market_data(self, symbol: str, count: int = 1) -> pd.DataFrame:
        """Obtiene los últimos N registros de datos de mercado"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT * FROM market_data 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                df = pd.read_sql_query(query, conn, params=[symbol, count])
                
                if not df.empty:
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('datetime', inplace=True)
                    df = df.sort_index()  # Ordenar por fecha ascendente
                
                return df
                
        except Exception as e:
            logger.error(f"Error obteniendo últimos datos de mercado: {e}")
            return pd.DataFrame()
    
    # =============================================================================
    # OPERACIONES DE TRADES
    # =============================================================================
    
    def insert_trade(self, trade: TradeRecord) -> Optional[int]:
        """Inserta un nuevo trade"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (
                        symbol, side, entry_price, exit_price, quantity,
                        entry_time, exit_time, pnl, pnl_pct, confidence,
                        model_prediction, actual_result, fees, trade_id,
                        status, stop_loss, take_profit, exit_reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.symbol, trade.side, trade.entry_price, trade.exit_price,
                    trade.quantity, trade.entry_time, trade.exit_time, trade.pnl,
                    trade.pnl_pct, trade.confidence, trade.model_prediction,
                    trade.actual_result, trade.fees, trade.trade_id, trade.status,
                    trade.stop_loss, trade.take_profit, trade.exit_reason, trade.created_at
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error insertando trade: {e}")
            return None
    
    def update_trade(self, trade_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza un trade existente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir query dinámicamente
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                query = f"UPDATE trades SET {set_clause} WHERE id = ?"
                
                params = list(updates.values()) + [trade_id]
                cursor.execute(query, params)
                conn.commit()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error actualizando trade {trade_id}: {e}")
            return False
    
    def close_trade(
        self, 
        trade_id: int, 
        exit_price: float, 
        exit_time: datetime = None,
        exit_reason: str = "manual"
    ) -> bool:
        """Cierra un trade"""
        if exit_time is None:
            exit_time = datetime.now()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener información del trade
                cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
                trade_row = cursor.fetchone()
                
                if not trade_row:
                    logger.warning(f"Trade {trade_id} no encontrado")
                    return False
                
                # Calcular PnL
                entry_price = trade_row['entry_price']
                quantity = trade_row['quantity']
                side = trade_row['side']
                
                if side == 'buy':
                    pnl = (exit_price - entry_price) * quantity
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:  # sell
                    pnl = (entry_price - exit_price) * quantity
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                
                # Actualizar trade
                updates = {
                    'exit_price': exit_price,
                    'exit_time': exit_time,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'status': 'closed',
                    'exit_reason': exit_reason
                }
                
                return self.update_trade(trade_id, updates)
                
        except Exception as e:
            logger.error(f"Error cerrando trade {trade_id}: {e}")
            return False
    
    def get_trades(
        self,
        symbol: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:
        """Obtiene trades con filtros opcionales"""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                if start_date:
                    query += " AND entry_time >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND entry_time <= ?"
                    params.append(end_date)
                
                query += " ORDER BY entry_time DESC"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                return pd.read_sql_query(query, conn, params=params)
                
        except Exception as e:
            logger.error(f"Error obteniendo trades: {e}")
            return pd.DataFrame()
    
    def get_open_trades(self, symbol: str = None) -> pd.DataFrame:
        """Obtiene trades abiertos"""
        return self.get_trades(symbol=symbol, status='open')
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, float]:
        """Calcula estadísticas de performance"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            trades_df = self.get_trades(
                status='closed',
                start_date=start_date
            )
            
            if trades_df.empty:
                return {}
            
            # Calcular métricas básicas
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            losing_trades = len(trades_df[trades_df['pnl'] < 0])
            
            total_pnl = trades_df['pnl'].sum()
            total_fees = trades_df['fees'].sum()
            net_pnl = total_pnl - total_fees
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
            
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 else float('inf')
            
            # Calcular drawdown
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            trades_df['running_max'] = trades_df['cumulative_pnl'].expanding().max()
            trades_df['drawdown'] = trades_df['cumulative_pnl'] - trades_df['running_max']
            max_drawdown = trades_df['drawdown'].min()
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'net_pnl': net_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'avg_trade_duration_hours': (
                    pd.to_datetime(trades_df['exit_time']) - pd.to_datetime(trades_df['entry_time'])
                ).dt.total_seconds().mean() / 3600 if total_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de performance: {e}")
            return {}
    
    # =============================================================================
    # OPERACIONES DE MÉTRICAS DEL MODELO
    # =============================================================================
    
    def save_model_metrics(self, metrics: ModelMetrics) -> bool:
        """Guarda métricas del modelo de ML"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO model_metrics (
                        model_version, accuracy, precision_score, recall_score,
                        f1_score, total_predictions, correct_predictions,
                        training_time, features_used, hyperparameters, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.model_version, metrics.accuracy, metrics.precision,
                    metrics.recall, metrics.f1_score, metrics.total_predictions,
                    metrics.correct_predictions, metrics.training_time,
                    json.dumps(metrics.features_used),
                    json.dumps(metrics.hyperparameters),
                    metrics.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando métricas del modelo: {e}")
            return False
    
    def get_latest_model_metrics(self) -> Optional[ModelMetrics]:
        """Obtiene las últimas métricas del modelo"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM model_metrics 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                row = cursor.fetchone()
                
                if row:
                    return ModelMetrics(
                        model_version=row['model_version'],
                        accuracy=row['accuracy'],
                        precision=row['precision_score'],
                        recall=row['recall_score'],
                        f1_score=row['f1_score'],
                        total_predictions=row['total_predictions'],
                        correct_predictions=row['correct_predictions'],
                        training_time=row['training_time'],
                        features_used=json.loads(row['features_used']),
                        hyperparameters=json.loads(row['hyperparameters']),
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error obteniendo métricas del modelo: {e}")
            return None
    
    # =============================================================================
    # OPERACIONES DE CONFIGURACIÓN DEL SISTEMA
    # =============================================================================
    
    def save_system_config(self, key: str, value: Any, description: str = None) -> bool:
        """Guarda configuración del sistema"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO system_config 
                    (config_key, config_value, description, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (key, json.dumps(value), description, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando configuración del sistema: {e}")
            return False
    
    def get_system_config(self, key: str) -> Any:
        """Obtiene configuración del sistema"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT config_value FROM system_config WHERE config_key = ?", 
                    (key,)
                )
                row = cursor.fetchone()
                return json.loads(row['config_value']) if row else None
        except Exception as e:
            logger.error(f"Error obteniendo configuración del sistema: {e}")
            return None
    
    # =============================================================================
    # OPERACIONES DE MANTENIMIENTO
    # =============================================================================
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Limpia datos antiguos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Limpiar datos de mercado antiguos
                cursor.execute(
                    "DELETE FROM market_data WHERE created_at < ?",
                    (cutoff_date,)
                )
                deleted_count += cursor.rowcount
                
                # Limpiar logs antiguos
                cursor.execute(
                    "DELETE FROM system_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                deleted_count += cursor.rowcount
                
                conn.commit()
                
            logger.info(f"Datos antiguos limpiados: {deleted_count} registros eliminados")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error limpiando datos antiguos: {e}")
            return 0
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Crea backup de la base de datos"""
        try:
            if backup_path is None:
                from config.settings import BACKUPS_DIR
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = BACKUPS_DIR / f"trading_bot_backup_{timestamp}.db"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup creado: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de la base de datos"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Contar registros en cada tabla
                tables = ['market_data', 'trades', 'model_metrics', 'system_config', 'system_logs']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Tamaño de archivo
                stats['file_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de BD: {e}")
            return {}

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()