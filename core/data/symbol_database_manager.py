# Ruta: core/data/symbol_database_manager.py
"""
symbol_database_manager.py - GESTOR DE BASE DE DATOS POR SÍMBOLO
Gestor optimizado para almacenar datos históricos por símbolo y timeframe
Ubicación: C:\TradingBot_v10\core\data\symbol_database_manager.py

CARACTERÍSTICAS PRINCIPALES:
- Una base de datos SQLite por símbolo y timeframe
- Estructura: data/historical/{symbol}/{symbol}_{timeframe}.db
- Índices optimizados para consultas rápidas
- Compresión automática de datos antiguos
- Validación de integridad de datos OHLCV
- Soporte para múltiples timeframes simultáneos
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import logging
from pathlib import Path
import threading
from contextlib import contextmanager
import time
import json
import gzip
import pickle
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class OHLCVData:
    """Estructura de datos OHLCV optimizada"""
    timestamp: int  # Unix timestamp en segundos
    open: float
    high: float
    low: float
    close: float
    volume: float
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Validar datos
        self._validate_data()
    
    def _validate_data(self):
        """Valida la integridad de los datos OHLCV"""
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            raise ValueError("Precios deben ser positivos")
        
        if self.high < self.low:
            raise ValueError("High debe ser >= Low")
        
        if not (self.low <= self.open <= self.high):
            raise ValueError("Open debe estar entre Low y High")
        
        if not (self.low <= self.close <= self.high):
            raise ValueError("Close debe estar entre Low y High")
        
        if self.volume < 0:
            raise ValueError("Volumen debe ser no negativo")

class SymbolDatabaseManager:
    """Gestor de base de datos por símbolo y timeframe"""
    
    def __init__(self, base_path: str = "data/historical"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Cache de conexiones
        self._connections: Dict[str, sqlite3.Connection] = {}
        self._connection_lock = threading.RLock()
        
        # Configuración de compresión
        self.compression_days = 30  # Comprimir datos más antiguos
        self.max_records_per_file = 1000000  # 1M registros por archivo
        
        logger.info(f"SymbolDatabaseManager inicializado en {self.base_path}")
    
    def _get_db_path(self, symbol: str, timeframe: str) -> Path:
        """Obtiene la ruta de la base de datos para un símbolo y timeframe"""
        symbol_dir = self.base_path / symbol
        symbol_dir.mkdir(exist_ok=True)
        return symbol_dir / f"{symbol}_{timeframe}.db"
    
    def _get_connection(self, symbol: str, timeframe: str) -> sqlite3.Connection:
        """Obtiene una conexión a la base de datos del símbolo/timeframe"""
        db_path = self._get_db_path(symbol, timeframe)
        db_key = f"{symbol}_{timeframe}"
        
        with self._connection_lock:
            if db_key not in self._connections:
                conn = sqlite3.connect(
                    str(db_path),
                    check_same_thread=False,
                    timeout=30.0
                )
                
                # Configurar la conexión para optimización
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                
                # Crear tabla si no existe
                self._create_table(conn)
                
                self._connections[db_key] = conn
                logger.debug(f"Conexión creada para {db_key}")
            
            return self._connections[db_key]
    
    def _create_table(self, conn: sqlite3.Connection):
        """Crea la tabla optimizada para datos OHLCV"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp) ON CONFLICT REPLACE
            )
        """)
        
        # Crear índices optimizados
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON ohlcv_data(timestamp)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp_desc 
            ON ohlcv_data(timestamp DESC)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON ohlcv_data(created_at)
        """)
        
        conn.commit()
    
    def insert_data(self, symbol: str, timeframe: str, data: List[OHLCVData]) -> int:
        """Inserta datos OHLCV en la base de datos"""
        if not data:
            return 0
        
        try:
            conn = self._get_connection(symbol, timeframe)
            
            # Preparar datos para inserción
            records = []
            for ohlcv in data:
                records.append((
                    ohlcv.timestamp,
                    ohlcv.open,
                    ohlcv.high,
                    ohlcv.low,
                    ohlcv.close,
                    ohlcv.volume,
                    ohlcv.created_at
                ))
            
            # Insertar en lotes para mejor rendimiento
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO ohlcv_data 
                (timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            
            conn.commit()
            inserted_count = cursor.rowcount
            
            logger.debug(f"Insertados {inserted_count} registros para {symbol}_{timeframe}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error insertando datos para {symbol}_{timeframe}: {e}")
            raise
    
    def get_data(
        self, 
        symbol: str, 
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Obtiene datos OHLCV de la base de datos"""
        try:
            conn = self._get_connection(symbol, timeframe)
            
            # Construir consulta SQL
            query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv_data"
            conditions = []
            params = []
            
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(int(start_date.timestamp()))
            
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(int(end_date.timestamp()))
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp ASC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Ejecutar consulta
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return df
            
            # Convertir timestamp a datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}_{timeframe}: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Obtiene los datos más recientes"""
        try:
            conn = self._get_connection(symbol, timeframe)
            
            query = """
                SELECT timestamp, open, high, low, close, volume 
                FROM ohlcv_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            
            df = pd.read_sql_query(query, conn, params=[limit])
            
            if df.empty:
                return df
            
            # Convertir timestamp y ordenar
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos recientes para {symbol}_{timeframe}: {e}")
            return pd.DataFrame()
    
    def get_data_range(self, symbol: str, timeframe: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Obtiene el rango de fechas de los datos disponibles"""
        try:
            conn = self._get_connection(symbol, timeframe)
            
            # Obtener fecha más antigua
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(timestamp) FROM ohlcv_data")
            min_timestamp = cursor.fetchone()[0]
            
            # Obtener fecha más reciente
            cursor.execute("SELECT MAX(timestamp) FROM ohlcv_data")
            max_timestamp = cursor.fetchone()[0]
            
            if min_timestamp is None or max_timestamp is None:
                return None, None
            
            return (
                datetime.fromtimestamp(min_timestamp),
                datetime.fromtimestamp(max_timestamp)
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo rango de datos para {symbol}_{timeframe}: {e}")
            return None, None
    
    def get_record_count(self, symbol: str, timeframe: str) -> int:
        """Obtiene el número de registros en la base de datos"""
        try:
            conn = self._get_connection(symbol, timeframe)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ohlcv_data")
            return cursor.fetchone()[0]
            
        except Exception as e:
            logger.error(f"Error contando registros para {symbol}_{timeframe}: {e}")
            return 0
    
    def get_database_stats(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Obtiene estadísticas de la base de datos"""
        try:
            conn = self._get_connection(symbol, timeframe)
            cursor = conn.cursor()
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM ohlcv_data")
            record_count = cursor.fetchone()[0]
            
            # Obtener rango de fechas
            start_date, end_date = self.get_data_range(symbol, timeframe)
            
            # Obtener tamaño del archivo
            db_path = self._get_db_path(symbol, timeframe)
            file_size = db_path.stat().st_size if db_path.exists() else 0
            
            # Obtener estadísticas de la tabla
            cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='ohlcv_data'")
            table_info = cursor.fetchone()
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'record_count': record_count,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'file_size_mb': round(file_size / 1024 / 1024, 2),
                'days_covered': (end_date - start_date).days if start_date and end_date else 0,
                'table_exists': table_info is not None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas para {symbol}_{timeframe}: {e}")
            return {'error': str(e)}
    
    def compress_old_data(self, symbol: str, timeframe: str, days_threshold: int = 30) -> int:
        """Comprime datos antiguos para ahorrar espacio"""
        try:
            conn = self._get_connection(symbol, timeframe)
            cursor = conn.cursor()
            
            # Calcular timestamp de corte
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            # Obtener datos antiguos
            cursor.execute("""
                SELECT * FROM ohlcv_data 
                WHERE timestamp < ? 
                ORDER BY timestamp
            """, [cutoff_timestamp])
            
            old_data = cursor.fetchall()
            
            if not old_data:
                return 0
            
            # Comprimir datos
            compressed_data = gzip.compress(pickle.dumps(old_data))
            
            # Guardar datos comprimidos
            compressed_path = self._get_db_path(symbol, timeframe).with_suffix('.compressed')
            with open(compressed_path, 'wb') as f:
                f.write(compressed_data)
            
            # Eliminar datos antiguos de la tabla principal
            cursor.execute("DELETE FROM ohlcv_data WHERE timestamp < ?", [cutoff_timestamp])
            conn.commit()
            
            compressed_count = len(old_data)
            logger.info(f"Comprimidos {compressed_count} registros antiguos para {symbol}_{timeframe}")
            
            return compressed_count
            
        except Exception as e:
            logger.error(f"Error comprimiendo datos para {symbol}_{timeframe}: {e}")
            return 0
    
    def get_all_symbols(self) -> List[str]:
        """Obtiene lista de todos los símbolos con datos"""
        try:
            symbols = set()
            for symbol_dir in self.base_path.iterdir():
                if symbol_dir.is_dir():
                    symbols.add(symbol_dir.name)
            return sorted(list(symbols))
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos: {e}")
            return []
    
    def get_symbol_timeframes(self, symbol: str) -> List[str]:
        """Obtiene lista de timeframes disponibles para un símbolo"""
        try:
            symbol_dir = self.base_path / symbol
            if not symbol_dir.exists():
                return []
            
            timeframes = []
            for db_file in symbol_dir.glob(f"{symbol}_*.db"):
                timeframe = db_file.stem.replace(f"{symbol}_", "")
                timeframes.append(timeframe)
            
            return sorted(timeframes)
            
        except Exception as e:
            logger.error(f"Error obteniendo timeframes para {symbol}: {e}")
            return []
    
    def cleanup_empty_databases(self) -> int:
        """Elimina bases de datos vacías"""
        try:
            cleaned_count = 0
            
            for symbol_dir in self.base_path.iterdir():
                if not symbol_dir.is_dir():
                    continue
                
                for db_file in symbol_dir.glob("*.db"):
                    try:
                        conn = sqlite3.connect(str(db_file))
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM ohlcv_data")
                        count = cursor.fetchone()[0]
                        conn.close()
                        
                        if count == 0:
                            db_file.unlink()
                            cleaned_count += 1
                            logger.info(f"Eliminada base de datos vacía: {db_file}")
                    
                    except Exception as e:
                        logger.warning(f"Error verificando {db_file}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error limpiando bases de datos vacías: {e}")
            return 0
    
    def close_all_connections(self):
        """Cierra todas las conexiones de base de datos"""
        with self._connection_lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error cerrando conexión: {e}")
            self._connections.clear()
    
    def __del__(self):
        """Destructor - cierra conexiones"""
        self.close_all_connections()

# Instancia global del gestor
symbol_db_manager = SymbolDatabaseManager()

# Funciones de conveniencia
def insert_ohlcv_data(symbol: str, timeframe: str, data: List[OHLCVData]) -> int:
    """Función de conveniencia para insertar datos OHLCV"""
    return symbol_db_manager.insert_data(symbol, timeframe, data)

def get_ohlcv_data(
    symbol: str, 
    timeframe: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Función de conveniencia para obtener datos OHLCV"""
    return symbol_db_manager.get_data(symbol, timeframe, start_date, end_date, limit)

def get_latest_ohlcv_data(symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    """Función de conveniencia para obtener datos recientes"""
    return symbol_db_manager.get_latest_data(symbol, timeframe, limit)
