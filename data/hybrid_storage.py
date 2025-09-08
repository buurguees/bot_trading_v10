"""
data/hybrid_storage.py - Sistema Híbrido de Almacenamiento SQLite + Parquet
Sistema optimizado para datos calientes (SQLite) y datos históricos (Parquet)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import sqlite3
import logging
import pyarrow as pa
import pyarrow.parquet as pq
import gzip
import json
from dataclasses import dataclass
import shutil
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Configuración del sistema de almacenamiento híbrido"""
    base_path: Path = Path("data")
    hot_data_days: int = 30  # Días de datos calientes en SQLite
    compression_level: int = 6  # Nivel de compresión para Parquet
    chunk_size: int = 10000  # Tamaño de chunk para procesamiento
    max_workers: int = 4  # Workers para procesamiento paralelo
    backup_enabled: bool = True
    backup_retention_days: int = 7

@dataclass
class StorageStats:
    """Estadísticas del sistema de almacenamiento"""
    hot_data_size_mb: float
    historical_size_gb: float
    compression_ratio: float
    total_symbols: int
    timeframes_available: List[str]
    oldest_data: datetime
    newest_data: datetime
    last_updated: datetime

class HybridStorageManager:
    """Sistema híbrido: SQLite + Parquet para optimización"""
    
    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        self.logger = logging.getLogger(__name__)
        
        # Configurar directorios
        self.base_path = self.config.base_path
        self.hot_data_db = self.base_path / "trading_bot.db"
        self.historical_path = self.base_path / "historical"
        self.aligned_path = self.historical_path / "aligned"
        self.compressed_path = self.historical_path / "compressed"
        self.metadata_path = self.historical_path / "metadata"
        self.backup_path = self.base_path / "backups"
        
        # Crear directorios si no existen
        self._create_directories()
        
        # Configurar timeframes
        self.timeframes = ['5m', '15m', '1h', '4h', '1d']
        self.timeframe_minutes = {
            '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440
        }
        
        # Lock para operaciones concurrentes
        self._lock = threading.RLock()
        
        self.logger.info(f"HybridStorageManager initialized at {self.base_path}")
    
    def _create_directories(self):
        """Crea la estructura de directorios necesaria"""
        directories = [
            self.historical_path,
            self.aligned_path,
            self.compressed_path,
            self.metadata_path,
            self.backup_path
        ]
        
        # Crear directorios para cada timeframe
        for tf in self.timeframes:
            directories.extend([
                self.aligned_path / tf,
                self.compressed_path / tf
            ])
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def store_aligned_data(
        self, 
        aligned_data: Dict[str, pd.DataFrame], 
        timeframe: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Almacena datos alineados en el sistema híbrido
        
        Args:
            aligned_data: Datos alineados por símbolo
            timeframe: Timeframe de los datos
            session_id: ID de la sesión de alineación
            metadata: Metadatos adicionales
        
        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            with self._lock:
                self.logger.info(f"Storing aligned data for {timeframe} (session: {session_id})")
                
                # Determinar si los datos van a hot storage o historical
                cutoff_date = datetime.now() - timedelta(days=self.config.hot_data_days)
                
                hot_data = {}
                historical_data = {}
                
                for symbol, df in aligned_data.items():
                    if df.empty:
                        continue
                    
                    # Separar datos calientes de históricos
                    hot_mask = df.index >= cutoff_date
                    hot_df = df[hot_mask].copy()
                    hist_df = df[~hot_mask].copy()
                    
                    if not hot_df.empty:
                        hot_data[symbol] = hot_df
                    
                    if not hist_df.empty:
                        historical_data[symbol] = hist_df
                
                # Almacenar datos calientes en SQLite
                if hot_data:
                    self._store_hot_data(hot_data, timeframe, session_id)
                
                # Almacenar datos históricos en Parquet
                if historical_data:
                    self._store_historical_data(historical_data, timeframe, session_id)
                
                # Guardar metadatos
                self._store_metadata(timeframe, session_id, metadata or {})
                
                self.logger.info(f"Successfully stored {len(aligned_data)} symbols for {timeframe}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing aligned data: {e}")
            return False
    
    def load_aligned_data(
        self, 
        symbols: List[str], 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """
        Carga datos alineados del sistema híbrido
        
        Args:
            symbols: Lista de símbolos a cargar
            timeframe: Timeframe de los datos
            start_date: Fecha de inicio
            end_date: Fecha de fin
        
        Returns:
            Dict[str, pd.DataFrame]: Datos cargados por símbolo
        """
        try:
            with self._lock:
                self.logger.info(f"Loading aligned data for {symbols} ({timeframe}) from {start_date} to {end_date}")
                
                loaded_data = {}
                cutoff_date = datetime.now() - timedelta(days=self.config.hot_data_days)
                
                for symbol in symbols:
                    symbol_data = []
                    
                    # Cargar datos históricos si es necesario
                    if start_date < cutoff_date:
                        hist_data = self._load_historical_data(symbol, timeframe, start_date, min(end_date, cutoff_date))
                        if hist_data is not None and not hist_data.empty:
                            symbol_data.append(hist_data)
                    
                    # Cargar datos calientes si es necesario
                    if end_date >= cutoff_date:
                        hot_data = self._load_hot_data(symbol, timeframe, max(start_date, cutoff_date), end_date)
                        if hot_data is not None and not hot_data.empty:
                            symbol_data.append(hot_data)
                    
                    # Combinar datos si hay múltiples fuentes
                    if symbol_data:
                        combined_data = pd.concat(symbol_data, axis=0)
                        combined_data = combined_data.sort_index()
                        combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                        loaded_data[symbol] = combined_data
                    else:
                        loaded_data[symbol] = pd.DataFrame()
                
                self.logger.info(f"Loaded data for {len(loaded_data)} symbols")
                return loaded_data
                
        except Exception as e:
            self.logger.error(f"Error loading aligned data: {e}")
            return {}
    
    def _store_hot_data(self, hot_data: Dict[str, pd.DataFrame], timeframe: str, session_id: str):
        """Almacena datos calientes en SQLite"""
        try:
            with sqlite3.connect(self.hot_data_db) as conn:
                # Crear tabla si no existe
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS aligned_market_data (
                        id INTEGER PRIMARY KEY,
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timeframe, timestamp) ON CONFLICT REPLACE
                    )
                """)
                
                # Insertar datos
                for symbol, df in hot_data.items():
                    for timestamp, row in df.iterrows():
                        conn.execute("""
                            INSERT OR REPLACE INTO aligned_market_data 
                            (symbol, timeframe, timestamp, open, high, low, close, volume, alignment_session_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            symbol, timeframe, int(timestamp.timestamp()),
                            row['open'], row['high'], row['low'], row['close'], row['volume'],
                            session_id
                        ))
                
                conn.commit()
                self.logger.debug(f"Stored {sum(len(df) for df in hot_data.values())} hot records for {timeframe}")
                
        except Exception as e:
            self.logger.error(f"Error storing hot data: {e}")
            raise
    
    def _store_historical_data(self, historical_data: Dict[str, pd.DataFrame], timeframe: str, session_id: str):
        """Almacena datos históricos en Parquet"""
        try:
            tf_path = self.aligned_path / timeframe
            tf_path.mkdir(exist_ok=True)
            
            # Almacenar cada símbolo por separado
            for symbol, df in historical_data.items():
                if df.empty:
                    continue
                
                # Crear archivo Parquet
                filename = f"{symbol}_{timeframe}_{df.index[0].strftime('%Y%m%d')}.parquet"
                filepath = tf_path / filename
                
                # Convertir a Arrow Table y guardar
                table = pa.Table.from_pandas(df.reset_index())
                pq.write_table(table, filepath, compression='snappy')
                
                # Comprimir archivo antiguo si existe
                self._compress_old_file(filepath)
            
            # Crear archivo multi-símbolo si hay múltiples símbolos
            if len(historical_data) > 1:
                self._create_multi_symbol_file(historical_data, timeframe, session_id)
            
            self.logger.debug(f"Stored historical data for {len(historical_data)} symbols in {timeframe}")
            
        except Exception as e:
            self.logger.error(f"Error storing historical data: {e}")
            raise
    
    def _load_hot_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Carga datos calientes de SQLite"""
        try:
            with sqlite3.connect(self.hot_data_db) as conn:
                query = """
                    SELECT timestamp, open, high, low, close, volume
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
                    return df
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading hot data for {symbol}: {e}")
            return None
    
    def _load_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Carga datos históricos de Parquet"""
        try:
            tf_path = self.aligned_path / timeframe
            if not tf_path.exists():
                return None
            
            # Buscar archivos relevantes
            pattern = f"{symbol}_{timeframe}_*.parquet"
            files = list(tf_path.glob(pattern))
            
            if not files:
                return None
            
            # Cargar y combinar archivos
            dataframes = []
            for file_path in files:
                try:
                    table = pq.read_table(file_path)
                    df = table.to_pandas()
                    df.set_index('timestamp', inplace=True)
                    
                    # Filtrar por rango de fechas
                    mask = (df.index >= start_date) & (df.index <= end_date)
                    if mask.any():
                        dataframes.append(df[mask])
                        
                except Exception as e:
                    self.logger.warning(f"Error reading {file_path}: {e}")
                    continue
            
            if dataframes:
                combined_df = pd.concat(dataframes, axis=0)
                combined_df = combined_df.sort_index()
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                return combined_df
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading historical data for {symbol}: {e}")
            return None
    
    def _create_multi_symbol_file(self, data: Dict[str, pd.DataFrame], timeframe: str, session_id: str):
        """Crea archivo Parquet multi-símbolo"""
        try:
            # Combinar todos los símbolos en un DataFrame
            combined_data = []
            for symbol, df in data.items():
                df_copy = df.copy()
                df_copy['symbol'] = symbol
                df_copy['timeframe'] = timeframe
                combined_data.append(df_copy.reset_index())
            
            if combined_data:
                combined_df = pd.concat(combined_data, axis=0)
                combined_df = combined_df.sort_values(['timestamp', 'symbol'])
                
                # Guardar archivo multi-símbolo
                filename = f"multi_symbol_{timeframe}_{combined_df['timestamp'].min().strftime('%Y%m%d')}.parquet"
                filepath = self.aligned_path / timeframe / filename
                
                table = pa.Table.from_pandas(combined_df)
                pq.write_table(table, filepath, compression='snappy')
                
                self.logger.debug(f"Created multi-symbol file: {filename}")
                
        except Exception as e:
            self.logger.error(f"Error creating multi-symbol file: {e}")
    
    def _store_metadata(self, timeframe: str, session_id: str, metadata: Dict[str, Any]):
        """Almacena metadatos de la sesión"""
        try:
            metadata_file = self.metadata_path / f"alignment_{timeframe}_{session_id}.json"
            
            metadata_data = {
                'timeframe': timeframe,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error storing metadata: {e}")
    
    def compress_old_data(self, days_threshold: int = 90):
        """Comprime datos antiguos para ahorrar espacio"""
        try:
            self.logger.info(f"Starting compression of data older than {days_threshold} days")
            
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            compressed_count = 0
            
            for tf in self.timeframes:
                tf_path = self.aligned_path / tf
                if not tf_path.exists():
                    continue
                
                for file_path in tf_path.glob("*.parquet"):
                    # Verificar si el archivo es lo suficientemente antiguo
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_date < cutoff_date:
                        # Comprimir archivo
                        compressed_path = self.compressed_path / tf / f"{file_path.stem}.parquet.gz"
                        compressed_path.parent.mkdir(exist_ok=True)
                        
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb', compresslevel=self.config.compression_level) as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Eliminar archivo original
                        file_path.unlink()
                        compressed_count += 1
            
            self.logger.info(f"Compressed {compressed_count} files")
            
        except Exception as e:
            self.logger.error(f"Error compressing old data: {e}")
    
    def get_storage_statistics(self) -> StorageStats:
        """Obtiene estadísticas del sistema de almacenamiento"""
        try:
            # Calcular tamaño de datos calientes
            hot_size = 0
            if self.hot_data_db.exists():
                hot_size = self.hot_data_db.stat().st_size / (1024 * 1024)  # MB
            
            # Calcular tamaño de datos históricos
            historical_size = 0
            total_symbols = set()
            timeframes_available = []
            oldest_data = None
            newest_data = None
            
            for tf in self.timeframes:
                tf_path = self.aligned_path / tf
                if tf_path.exists():
                    timeframes_available.append(tf)
                    
                    for file_path in tf_path.glob("*.parquet"):
                        file_size = file_path.stat().st_size
                        historical_size += file_size
                        
                        # Extraer símbolo del nombre del archivo
                        symbol = file_path.stem.split('_')[0]
                        total_symbols.add(symbol)
                        
                        # Actualizar fechas
                        file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if oldest_data is None or file_date < oldest_data:
                            oldest_data = file_date
                        if newest_data is None or file_date > newest_data:
                            newest_data = file_date
            
            historical_size_gb = historical_size / (1024 * 1024 * 1024)
            
            # Calcular ratio de compresión (estimado)
            compression_ratio = 0.15  # Estimación basada en Parquet + Snappy
            
            return StorageStats(
                hot_data_size_mb=hot_size,
                historical_size_gb=historical_size_gb,
                compression_ratio=compression_ratio,
                total_symbols=len(total_symbols),
                timeframes_available=timeframes_available,
                oldest_data=oldest_data or datetime.now(),
                newest_data=newest_data or datetime.now(),
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting storage statistics: {e}")
            return StorageStats(
                hot_data_size_mb=0, historical_size_gb=0, compression_ratio=0,
                total_symbols=0, timeframes_available=[], 
                oldest_data=datetime.now(), newest_data=datetime.now(),
                last_updated=datetime.now()
            )
    
    def cleanup_expired_data(self, retention_days: int = 365):
        """Limpia datos expirados según la política de retención"""
        try:
            self.logger.info(f"Cleaning up data older than {retention_days} days")
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0
            
            # Limpiar datos históricos
            for tf in self.timeframes:
                tf_path = self.aligned_path / tf
                if tf_path.exists():
                    for file_path in tf_path.glob("*.parquet"):
                        file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_date < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
            
            # Limpiar metadatos antiguos
            if self.metadata_path.exists():
                for file_path in self.metadata_path.glob("*.json"):
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_date < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} files")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
    
    def backup_data(self, backup_name: Optional[str] = None) -> bool:
        """Crea backup de los datos"""
        try:
            if not self.config.backup_enabled:
                return False
            
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_dir = self.backup_path / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup de base de datos caliente
            if self.hot_data_db.exists():
                shutil.copy2(self.hot_data_db, backup_dir / "trading_bot.db")
            
            # Backup de datos históricos
            if self.historical_path.exists():
                shutil.copytree(self.historical_path, backup_dir / "historical")
            
            self.logger.info(f"Backup created: {backup_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return False

# Funciones de conveniencia
def create_storage_manager(config: Optional[StorageConfig] = None) -> HybridStorageManager:
    """Crea un gestor de almacenamiento híbrido"""
    return HybridStorageManager(config)

def quick_store_data(
    data: Dict[str, pd.DataFrame], 
    timeframe: str, 
    session_id: str
) -> bool:
    """Función de conveniencia para almacenar datos rápidamente"""
    manager = HybridStorageManager()
    return manager.store_aligned_data(data, timeframe, session_id)

def quick_load_data(
    symbols: List[str], 
    timeframe: str, 
    start_date: datetime, 
    end_date: datetime
) -> Dict[str, pd.DataFrame]:
    """Función de conveniencia para cargar datos rápidamente"""
    manager = HybridStorageManager()
    return manager.load_aligned_data(symbols, timeframe, start_date, end_date)
