# Ruta: core/data/enterprise/database.py
# database.py - Gestor de base de datos TimescaleDB
# Ubicación: C:\TradingBot_v10\data\enterprise\database.py

"""
Gestor de base de datos TimescaleDB para almacenamiento histórico.

Características principales:
- Almacenamiento en TimescaleDB con hypertables
- Consultas optimizadas para datos de series temporales
- Compresión automática de datos antiguos
- Índices optimizados para trading
- Conexión asíncrona con pool de conexiones
- Backup y recuperación automática
"""

import asyncio
import logging
import psycopg2
import psycopg2.extras
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from contextlib import asynccontextmanager
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TimescaleDBManager:
    """
    Gestor de base de datos TimescaleDB para datos de trading
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el gestor de base de datos
        
        Args:
            config: Configuración de la base de datos
        """
        self.config = config or self._default_config()
        self.connection_pool = None
        self.is_connected = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Métricas
        self.queries_executed = 0
        self.queries_failed = 0
        self.data_inserted = 0
        
        logger.info("TimescaleDBManager inicializado")
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'trading_data',
            'user': 'postgres',
            'password': 'password',
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'compression': {
                'enabled': True,
                'chunk_time_interval': '7 days',
                'compression_segmentby': 'symbol'
            },
            'retention': {
                'enabled': True,
                'data_retention_period': '1 year'
            }
        }
    
    async def initialize(self):
        """Inicializa la conexión y crea tablas"""
        try:
            # Crear pool de conexiones
            await self._create_connection_pool()
            
            # Crear tablas
            await self._create_tables()
            
            # Configurar compresión
            await self._setup_compression()
            
            # Configurar retención
            await self._setup_retention()
            
            self.is_connected = True
            logger.info("✅ TimescaleDB inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando TimescaleDB: {e}")
            raise
    
    async def _create_connection_pool(self):
        """Crea pool de conexiones"""
        try:
            # En un sistema real, usaríamos asyncpg para conexiones asíncronas
            # Por ahora, usamos psycopg2 con ThreadPoolExecutor
            self.connection_pool = {
                'host': self.config['host'],
                'port': self.config['port'],
                'database': self.config['database'],
                'user': self.config['user'],
                'password': self.config['password']
            }
            
            # Verificar conexión
            await self._test_connection()
            
        except Exception as e:
            logger.error(f"Error creando pool de conexiones: {e}")
            raise
    
    async def _test_connection(self):
        """Prueba la conexión a la base de datos"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._execute_query,
                "SELECT 1"
            )
            logger.info("✅ Conexión a TimescaleDB verificada")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a TimescaleDB: {e}")
            raise
    
    def _execute_query(self, query: str, params: Optional[Tuple] = None, fetch: bool = False) -> Optional[List[Dict]]:
        """Ejecuta una consulta SQL"""
        try:
            with psycopg2.connect(**self.connection_pool) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    
                    if fetch:
                        result = cur.fetchall()
                        return [dict(row) for row in result]
                    else:
                        conn.commit()
                        return None
                        
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            self.queries_failed += 1
            raise
        finally:
            self.queries_executed += 1
    
    async def _create_tables(self):
        """Crea las tablas necesarias"""
        try:
            # Tabla de ticks
            create_ticks_table = """
            CREATE TABLE IF NOT EXISTS market_ticks (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                open DECIMAL(20,8) NOT NULL,
                high DECIMAL(20,8) NOT NULL,
                low DECIMAL(20,8) NOT NULL,
                close DECIMAL(20,8) NOT NULL,
                volume DECIMAL(20,8) NOT NULL,
                source VARCHAR(50) DEFAULT 'bitget_websocket',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            
            # Tabla de velas
            create_candles_table = """
            CREATE TABLE IF NOT EXISTS market_candles (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                open DECIMAL(20,8) NOT NULL,
                high DECIMAL(20,8) NOT NULL,
                low DECIMAL(20,8) NOT NULL,
                close DECIMAL(20,8) NOT NULL,
                volume DECIMAL(20,8) NOT NULL,
                indicators JSONB,
                source VARCHAR(50) DEFAULT 'bitget_websocket',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            
            # Tabla de order book
            create_orderbook_table = """
            CREATE TABLE IF NOT EXISTS market_orderbook (
                time TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                bids JSONB NOT NULL,
                asks JSONB NOT NULL,
                source VARCHAR(50) DEFAULT 'bitget_websocket',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            
            # Ejecutar creación de tablas
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._execute_query, create_ticks_table)
            await loop.run_in_executor(self.executor, self._execute_query, create_candles_table)
            await loop.run_in_executor(self.executor, self._execute_query, create_orderbook_table)
            
            # Crear hypertables
            await self._create_hypertables()
            
            # Crear índices
            await self._create_indexes()
            
            logger.info("✅ Tablas creadas correctamente")
            
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            raise
    
    async def _create_hypertables(self):
        """Crea hypertables de TimescaleDB"""
        try:
            # Hypertable para ticks
            create_ticks_hypertable = """
            SELECT create_hypertable('market_ticks', 'time', 
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE
            );
            """
            
            # Hypertable para velas
            create_candles_hypertable = """
            SELECT create_hypertable('market_candles', 'time',
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE
            );
            """
            
            # Hypertable para order book
            create_orderbook_hypertable = """
            SELECT create_hypertable('market_orderbook', 'time',
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE
            );
            """
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._execute_query, create_ticks_hypertable)
            await loop.run_in_executor(self.executor, self._execute_query, create_candles_hypertable)
            await loop.run_in_executor(self.executor, self._execute_query, create_orderbook_hypertable)
            
            logger.info("✅ Hypertables creadas correctamente")
            
        except Exception as e:
            logger.error(f"Error creando hypertables: {e}")
            raise
    
    async def _create_indexes(self):
        """Crea índices optimizados"""
        try:
            indexes = [
                # Índices para ticks
                "CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON market_ticks (symbol, time DESC);",
                "CREATE INDEX IF NOT EXISTS idx_ticks_time ON market_ticks (time DESC);",
                
                # Índices para velas
                "CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON market_candles (symbol, time DESC);",
                "CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval ON market_candles (symbol, interval, time DESC);",
                "CREATE INDEX IF NOT EXISTS idx_candles_time ON market_candles (time DESC);",
                
                # Índices para order book
                "CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_time ON market_orderbook (symbol, time DESC);",
                "CREATE INDEX IF NOT EXISTS idx_orderbook_time ON market_orderbook (time DESC);",
                
                # Índices para consultas de trading
                "CREATE INDEX IF NOT EXISTS idx_candles_symbol_close ON market_candles (symbol, close, time DESC);",
                "CREATE INDEX IF NOT EXISTS idx_candles_symbol_volume ON market_candles (symbol, volume, time DESC);"
            ]
            
            loop = asyncio.get_event_loop()
            for index_query in indexes:
                await loop.run_in_executor(self.executor, self._execute_query, index_query)
            
            logger.info("✅ Índices creados correctamente")
            
        except Exception as e:
            logger.error(f"Error creando índices: {e}")
            raise
    
    async def _setup_compression(self):
        """Configura compresión de datos"""
        try:
            if not self.config['compression']['enabled']:
                return
            
            compression_config = self.config['compression']
            
            # Configurar compresión para ticks
            compression_ticks = f"""
            ALTER TABLE market_ticks SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = '{compression_config['compression_segmentby']}',
                timescaledb.compress_orderby = 'time DESC'
            );
            """
            
            # Configurar compresión para velas
            compression_candles = f"""
            ALTER TABLE market_candles SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = '{compression_config['compression_segmentby']}',
                timescaledb.compress_orderby = 'time DESC'
            );
            """
            
            # Agregar políticas de compresión
            add_compression_policy_ticks = f"""
            SELECT add_compression_policy('market_ticks', INTERVAL '{compression_config['chunk_time_interval']}');
            """
            
            add_compression_policy_candles = f"""
            SELECT add_compression_policy('market_candles', INTERVAL '{compression_config['chunk_time_interval']}');
            """
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._execute_query, compression_ticks)
            await loop.run_in_executor(self.executor, self._execute_query, compression_candles)
            await loop.run_in_executor(self.executor, self._execute_query, add_compression_policy_ticks)
            await loop.run_in_executor(self.executor, self._execute_query, add_compression_policy_candles)
            
            logger.info("✅ Compresión configurada correctamente")
            
        except Exception as e:
            logger.error(f"Error configurando compresión: {e}")
            raise
    
    async def _setup_retention(self):
        """Configura retención de datos"""
        try:
            if not self.config['retention']['enabled']:
                return
            
            retention_period = self.config['retention']['data_retention_period']
            
            # Política de retención para ticks
            retention_ticks = f"""
            SELECT add_retention_policy('market_ticks', INTERVAL '{retention_period}');
            """
            
            # Política de retención para velas
            retention_candles = f"""
            SELECT add_retention_policy('market_candles', INTERVAL '{retention_period}');
            """
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._execute_query, retention_ticks)
            await loop.run_in_executor(self.executor, self._execute_query, retention_candles)
            
            logger.info("✅ Retención configurada correctamente")
            
        except Exception as e:
            logger.error(f"Error configurando retención: {e}")
            raise
    
    async def insert_ticks(self, ticks: List[Dict[str, Any]]):
        """Inserta ticks en la base de datos"""
        try:
            if not ticks:
                return
            
            query = """
            INSERT INTO market_ticks (time, symbol, open, high, low, close, volume, source)
            VALUES %s
            ON CONFLICT DO NOTHING
            """
            
            values = [
                (
                    tick['timestamp'],
                    tick['symbol'],
                    tick['open'],
                    tick['high'],
                    tick['low'],
                    tick['close'],
                    tick['volume'],
                    tick.get('source', 'bitget_websocket')
                )
                for tick in ticks
            ]
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._execute_batch_insert,
                query,
                values
            )
            
            self.data_inserted += len(ticks)
            
        except Exception as e:
            logger.error(f"Error insertando ticks: {e}")
            raise
    
    async def insert_candles(self, candles: List[Dict[str, Any]]):
        """Inserta velas en la base de datos"""
        try:
            if not candles:
                return
            
            query = """
            INSERT INTO market_candles (time, symbol, interval, open, high, low, close, volume, indicators, source)
            VALUES %s
            ON CONFLICT DO NOTHING
            """
            
            values = [
                (
                    candle['timestamp'],
                    candle['symbol'],
                    candle.get('interval', '1m'),
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume'],
                    json.dumps(candle.get('indicators', {})),
                    candle.get('source', 'bitget_websocket')
                )
                for candle in candles
            ]
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._execute_batch_insert,
                query,
                values
            )
            
            self.data_inserted += len(candles)
            
        except Exception as e:
            logger.error(f"Error insertando velas: {e}")
            raise
    
    def _execute_batch_insert(self, query: str, values: List[Tuple]):
        """Ejecuta inserción por lotes"""
        try:
            with psycopg2.connect(**self.connection_pool) as conn:
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        query,
                        values,
                        template=None,
                        page_size=1000
                    )
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error en inserción por lotes: {e}")
            raise
    
    async def get_latest_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtiene los datos más recientes para un símbolo"""
        try:
            query = """
            SELECT time, open, high, low, close, volume, indicators
            FROM market_candles
            WHERE symbol = %s
            ORDER BY time DESC
            LIMIT %s
            """
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                query,
                (symbol, limit),
                True
            )
            
            if not result:
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(result)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time').sort_index()
            
            # Procesar indicadores JSON
            if 'indicators' in df.columns:
                df['indicators'] = df['indicators'].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = '1m'
    ) -> Optional[pd.DataFrame]:
        """Obtiene datos históricos para un símbolo"""
        try:
            query = """
            SELECT time, open, high, low, close, volume, indicators
            FROM market_candles
            WHERE symbol = %s
            AND interval = %s
            AND time >= %s
            AND time <= %s
            ORDER BY time ASC
            """
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                query,
                (symbol, interval, start_date, end_date),
                True
            )
            
            if not result:
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(result)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time')
            
            # Procesar indicadores JSON
            if 'indicators' in df.columns:
                df['indicators'] = df['indicators'].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos para {symbol}: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """Obtiene lista de símbolos disponibles"""
        try:
            query = """
            SELECT DISTINCT symbol
            FROM market_candles
            ORDER BY symbol
            """
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                query,
                None,
                True
            )
            
            return [row['symbol'] for row in result] if result else []
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos: {e}")
            return []
    
    async def get_data_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de datos almacenados"""
        try:
            query = """
            SELECT 
                symbol,
                COUNT(*) as candle_count,
                MIN(time) as first_candle,
                MAX(time) as last_candle,
                AVG(volume) as avg_volume,
                AVG(close) as avg_price
            FROM market_candles
            GROUP BY symbol
            ORDER BY symbol
            """
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                query,
                None,
                True
            )
            
            return {
                'symbols': result if result else [],
                'total_symbols': len(result) if result else 0,
                'queries_executed': self.queries_executed,
                'queries_failed': self.queries_failed,
                'data_inserted': self.data_inserted
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Verifica la salud de la base de datos"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._execute_query,
                "SELECT 1"
            )
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False
    
    async def close(self):
        """Cierra conexiones"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            
            self.is_connected = False
            logger.info("✅ TimescaleDB cerrado correctamente")
            
        except Exception as e:
            logger.error(f"Error cerrando TimescaleDB: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance"""
        return {
            'queries_executed': self.queries_executed,
            'queries_failed': self.queries_failed,
            'data_inserted': self.data_inserted,
            'is_connected': self.is_connected,
            'success_rate': (self.queries_executed - self.queries_failed) / self.queries_executed if self.queries_executed > 0 else 0
        }
