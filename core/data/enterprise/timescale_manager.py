# Ruta: core/data/enterprise/timescale_manager.py
# timescale_manager.py - Gestor TimescaleDB para datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\timescale_manager.py

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

import asyncpg
from asyncpg import Pool, Connection

from core.config.unified_config import unified_config
from .stream_collector import MarketTick

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimescaleDataManager:
    """Gestor TimescaleDB para datos enterprise"""
    
    def __init__(self):
        """Inicializar el gestor TimescaleDB"""
        self.config = get_enterprise_config()
        self.timescaledb_config = self.config.get_timescaledb_config()
        
        # Configuración de conexión
        self.host = self.timescaledb_config.get("host", "localhost")
        self.port = self.timescaledb_config.get("port", 5432)
        self.database = self.timescaledb_config.get("database", "trading_bot_enterprise")
        self.username = self.timescaledb_config.get("username", "trading_bot")
        self.password = self.timescaledb_config.get("password", "")
        self.pool_size = self.timescaledb_config.get("pool_size", 10)
        self.max_overflow = self.timescaledb_config.get("max_overflow", 20)
        self.pool_timeout = self.timescaledb_config.get("pool_timeout", 30)
        self.pool_recycle = self.timescaledb_config.get("pool_recycle", 3600)
        
        # Pool de conexiones
        self.pool: Optional[Pool] = None
        self.is_running = False
        
        # Métricas
        self.metrics = {
            "connections_active": 0,
            "connections_total": 0,
            "queries_executed_total": 0,
            "queries_successful": 0,
            "queries_failed": 0,
            "inserts_total": 0,
            "selects_total": 0,
            "updates_total": 0,
            "deletes_total": 0,
            "bytes_processed_total": 0,
            "last_query_time": None,
            "errors_total": 0
        }
        
        logger.info("TimescaleDataManager inicializado")
    
    async def start(self):
        """Iniciar el gestor TimescaleDB"""
        try:
            logger.info("Iniciando TimescaleDataManager...")
            
            # Configuración de conexión
            connection_config = {
                'host': self.host,
                'port': self.port,
                'database': self.database,
                'user': self.username,
                'password': self.password,
                'min_size': 1,
                'max_size': self.pool_size,
                'command_timeout': self.pool_timeout,
                'server_settings': {
                    'application_name': 'trading_bot_enterprise',
                    'timezone': 'UTC'
                }
            }
            
            # Crear pool de conexiones
            self.pool = await asyncpg.create_pool(**connection_config)
            self.is_running = True
            
            # Verificar conexión
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info(f"TimescaleDataManager iniciado - Host: {self.host}:{self.port}, DB: {self.database}")
            
        except Exception as e:
            logger.error(f"Error iniciando TimescaleDataManager: {e}")
            raise
    
    async def stop(self):
        """Detener el gestor TimescaleDB"""
        try:
            logger.info("Deteniendo TimescaleDataManager...")
            self.is_running = False
            
            if self.pool:
                await self.pool.close()
                self.pool = None
            
            logger.info("TimescaleDataManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo TimescaleDataManager: {e}")
    
    async def _execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Ejecutar consulta SQL"""
        try:
            if not self.pool or not self.is_running:
                logger.warning("Pool de conexiones no está disponible")
                return []
            
            start_time = time.time()
            
            async with self.pool.acquire() as conn:
                result = await conn.fetch(query, *args)
                
                # Convertir resultado a lista de diccionarios
                rows = [dict(row) for row in result]
                
                # Actualizar métricas
                execution_time = time.time() - start_time
                self.metrics["queries_executed_total"] += 1
                self.metrics["queries_successful"] += 1
                self.metrics["last_query_time"] = datetime.now(timezone.utc)
                
                # Determinar tipo de consulta
                query_type = query.strip().upper().split()[0]
                if query_type == "INSERT":
                    self.metrics["inserts_total"] += 1
                elif query_type == "SELECT":
                    self.metrics["selects_total"] += 1
                elif query_type == "UPDATE":
                    self.metrics["updates_total"] += 1
                elif query_type == "DELETE":
                    self.metrics["deletes_total"] += 1
                
                logger.debug(f"Consulta ejecutada: {query_type} - {execution_time:.3f}s")
                
                return rows
                
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            self.metrics["queries_failed"] += 1
            self.metrics["errors_total"] += 1
            return []
    
    async def insert_market_tick(self, tick: MarketTick):
        """Insertar tick de mercado en TimescaleDB"""
        try:
            query = """
                INSERT INTO market_ticks (
                    time, symbol, price, volume, bid, ask, bid_size, ask_size, 
                    exchange, raw_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (time, symbol) DO UPDATE SET
                    price = EXCLUDED.price,
                    volume = EXCLUDED.volume,
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    bid_size = EXCLUDED.bid_size,
                    ask_size = EXCLUDED.ask_size,
                    raw_data = EXCLUDED.raw_data
            """
            
            await self._execute_query(
                query,
                tick.timestamp,
                tick.symbol,
                tick.price,
                tick.volume,
                tick.bid,
                tick.ask,
                tick.bid_size,
                tick.ask_size,
                tick.exchange,
                json.dumps(tick.raw_data) if tick.raw_data else None,
                datetime.now(timezone.utc)
            )
            
            logger.debug(f"Tick insertado: {tick.symbol} - {tick.timestamp}")
            
        except Exception as e:
            logger.error(f"Error insertando tick {tick.symbol}: {e}")
            self.metrics["errors_total"] += 1
    
    async def insert_market_ticks_batch(self, ticks: List[MarketTick]):
        """Insertar lote de ticks de mercado"""
        try:
            if not ticks:
                return
            
            query = """
                INSERT INTO market_ticks (
                    time, symbol, price, volume, bid, ask, bid_size, ask_size, 
                    exchange, raw_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (time, symbol) DO UPDATE SET
                    price = EXCLUDED.price,
                    volume = EXCLUDED.volume,
                    bid = EXCLUDED.bid,
                    ask = EXCLUDED.ask,
                    bid_size = EXCLUDED.bid_size,
                    ask_size = EXCLUDED.ask_size,
                    raw_data = EXCLUDED.raw_data
            """
            
            # Preparar datos para inserción en lote
            data = []
            for tick in ticks:
                data.append((
                    tick.timestamp,
                    tick.symbol,
                    tick.price,
                    tick.volume,
                    tick.bid,
                    tick.ask,
                    tick.bid_size,
                    tick.ask_size,
                    tick.exchange,
                    json.dumps(tick.raw_data) if tick.raw_data else None,
                    datetime.now(timezone.utc)
                ))
            
            # Ejecutar inserción en lote
            if self.pool and self.is_running:
                async with self.pool.acquire() as conn:
                    await conn.executemany(query, data)
                
                self.metrics["inserts_total"] += 1
                self.metrics["queries_executed_total"] += 1
                self.metrics["queries_successful"] += 1
                self.metrics["last_query_time"] = datetime.now(timezone.utc)
                
                logger.info(f"Lote de {len(ticks)} ticks insertado")
            
        except Exception as e:
            logger.error(f"Error insertando lote de ticks: {e}")
            self.metrics["queries_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def insert_ohlcv_data(self, symbol: str, timeframe: str, ohlcv_data: Dict[str, Any]):
        """Insertar datos OHLCV en TimescaleDB"""
        try:
            query = """
                INSERT INTO ohlcv_data (
                    time, symbol, timeframe, open, high, low, close, volume,
                    trades_count, vwap, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    trades_count = EXCLUDED.trades_count,
                    vwap = EXCLUDED.vwap
            """
            
            await self._execute_query(
                query,
                ohlcv_data["timestamp"],
                symbol,
                timeframe,
                ohlcv_data["open"],
                ohlcv_data["high"],
                ohlcv_data["low"],
                ohlcv_data["close"],
                ohlcv_data["volume"],
                ohlcv_data.get("trades_count"),
                ohlcv_data.get("vwap"),
                datetime.now(timezone.utc)
            )
            
            logger.debug(f"Datos OHLCV insertados: {symbol}_{timeframe}")
            
        except Exception as e:
            logger.error(f"Error insertando datos OHLCV {symbol}_{timeframe}: {e}")
            self.metrics["errors_total"] += 1
    
    async def insert_technical_features(self, symbol: str, timeframe: str, features: Dict[str, Any]):
        """Insertar features técnicos en TimescaleDB"""
        try:
            query = """
                INSERT INTO technical_features (
                    time, symbol, timeframe, sma_10, sma_20, ema_12, ema_26,
                    rsi_14, macd, macd_signal, macd_histogram, bollinger_upper,
                    bollinger_lower, bollinger_middle, atr_14, volume_sma_10,
                    vwap, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
                    sma_10 = EXCLUDED.sma_10,
                    sma_20 = EXCLUDED.sma_20,
                    ema_12 = EXCLUDED.ema_12,
                    ema_26 = EXCLUDED.ema_26,
                    rsi_14 = EXCLUDED.rsi_14,
                    macd = EXCLUDED.macd,
                    macd_signal = EXCLUDED.macd_signal,
                    macd_histogram = EXCLUDED.macd_histogram,
                    bollinger_upper = EXCLUDED.bollinger_upper,
                    bollinger_lower = EXCLUDED.bollinger_lower,
                    bollinger_middle = EXCLUDED.bollinger_middle,
                    atr_14 = EXCLUDED.atr_14,
                    volume_sma_10 = EXCLUDED.volume_sma_10,
                    vwap = EXCLUDED.vwap
            """
            
            await self._execute_query(
                query,
                features["timestamp"],
                symbol,
                timeframe,
                features.get("sma_10"),
                features.get("sma_20"),
                features.get("ema_12"),
                features.get("ema_26"),
                features.get("rsi_14"),
                features.get("macd"),
                features.get("macd_signal"),
                features.get("macd_histogram"),
                features.get("bollinger_upper"),
                features.get("bollinger_lower"),
                features.get("bollinger_middle"),
                features.get("atr_14"),
                features.get("volume_sma_10"),
                features.get("vwap"),
                datetime.now(timezone.utc)
            )
            
            logger.debug(f"Features técnicos insertados: {symbol}_{timeframe}")
            
        except Exception as e:
            logger.error(f"Error insertando features técnicos {symbol}_{timeframe}: {e}")
            self.metrics["errors_total"] += 1
    
    async def insert_model_prediction(self, symbol: str, model_name: str, prediction: Dict[str, Any]):
        """Insertar predicción del modelo en TimescaleDB"""
        try:
            query = """
                INSERT INTO model_predictions (
                    time, symbol, model_name, prediction_type, prediction_value,
                    confidence, probabilities, features_used, model_version, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (time, symbol, model_name) DO UPDATE SET
                    prediction_type = EXCLUDED.prediction_type,
                    prediction_value = EXCLUDED.prediction_value,
                    confidence = EXCLUDED.confidence,
                    probabilities = EXCLUDED.probabilities,
                    features_used = EXCLUDED.features_used,
                    model_version = EXCLUDED.model_version
            """
            
            await self._execute_query(
                query,
                prediction["timestamp"],
                symbol,
                model_name,
                prediction.get("prediction_type"),
                prediction.get("prediction_value"),
                prediction.get("confidence"),
                json.dumps(prediction.get("probabilities")) if prediction.get("probabilities") else None,
                json.dumps(prediction.get("features_used")) if prediction.get("features_used") else None,
                prediction.get("model_version"),
                datetime.now(timezone.utc)
            )
            
            logger.debug(f"Predicción insertada: {symbol}_{model_name}")
            
        except Exception as e:
            logger.error(f"Error insertando predicción {symbol}_{model_name}: {e}")
            self.metrics["errors_total"] += 1
    
    async def insert_executed_trade(self, trade: Dict[str, Any]):
        """Insertar trade ejecutado en TimescaleDB"""
        try:
            query = """
                INSERT INTO executed_trades (
                    time, symbol, side, order_type, amount, price, filled_amount,
                    filled_price, commission, commission_asset, order_id, trade_id,
                    status, leverage, position_side, pnl, pnl_pct, prediction_id,
                    strategy_name, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """
            
            await self._execute_query(
                query,
                trade["timestamp"],
                trade["symbol"],
                trade["side"],
                trade["order_type"],
                trade["amount"],
                trade["price"],
                trade.get("filled_amount"),
                trade.get("filled_price"),
                trade.get("commission"),
                trade.get("commission_asset"),
                trade.get("order_id"),
                trade.get("trade_id"),
                trade.get("status"),
                trade.get("leverage", 1),
                trade.get("position_side"),
                trade.get("pnl"),
                trade.get("pnl_pct"),
                trade.get("prediction_id"),
                trade.get("strategy_name"),
                datetime.now(timezone.utc)
            )
            
            logger.debug(f"Trade ejecutado insertado: {trade['symbol']}")
            
        except Exception as e:
            logger.error(f"Error insertando trade ejecutado: {e}")
            self.metrics["errors_total"] += 1
    
    async def get_latest_market_data(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener los últimos datos de mercado"""
        try:
            query = """
                SELECT time, symbol, price, volume, bid, ask, bid_size, ask_size, exchange
                FROM market_ticks
                WHERE symbol = $1
                ORDER BY time DESC
                LIMIT $2
            """
            
            result = await self._execute_query(query, symbol, limit)
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado {symbol}: {e}")
            return []
    
    async def get_ohlcv_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Obtener datos OHLCV para un rango de tiempo"""
        try:
            query = """
                SELECT time, symbol, timeframe, open, high, low, close, volume, trades_count, vwap
                FROM ohlcv_data
                WHERE symbol = $1 AND timeframe = $2 AND time BETWEEN $3 AND $4
                ORDER BY time ASC
            """
            
            result = await self._execute_query(query, symbol, timeframe, start_time, end_time)
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo datos OHLCV {symbol}_{timeframe}: {e}")
            return []
    
    async def get_technical_features(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Obtener features técnicos para un rango de tiempo"""
        try:
            query = """
                SELECT time, symbol, timeframe, sma_10, sma_20, ema_12, ema_26,
                       rsi_14, macd, macd_signal, macd_histogram, bollinger_upper,
                       bollinger_lower, bollinger_middle, atr_14, volume_sma_10, vwap
                FROM technical_features
                WHERE symbol = $1 AND timeframe = $2 AND time BETWEEN $3 AND $4
                ORDER BY time ASC
            """
            
            result = await self._execute_query(query, symbol, timeframe, start_time, end_time)
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo features técnicos {symbol}_{timeframe}: {e}")
            return []
    
    async def get_daily_trading_summary(self, days: int = 30) -> List[Dict[str, Any]]:
        """Obtener resumen diario de trading"""
        try:
            query = """
                SELECT 
                    DATE(time) as date,
                    symbol,
                    COUNT(*) as trades_count,
                    SUM(amount) as total_volume,
                    AVG(price) as avg_price,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl
                FROM executed_trades
                WHERE time >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(time), symbol
                ORDER BY date DESC, symbol
            """ % days
            
            result = await self._execute_query(query)
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen diario de trading: {e}")
            return []
    
    async def cleanup_old_data(self, days: int = 30):
        """Limpiar datos antiguos"""
        try:
            # Limpiar market_ticks
            query1 = "DELETE FROM market_ticks WHERE time < NOW() - INTERVAL '%s days'" % days
            await self._execute_query(query1)
            
            # Limpiar technical_features
            query2 = "DELETE FROM technical_features WHERE time < NOW() - INTERVAL '%s days'" % days
            await self._execute_query(query2)
            
            # Limpiar model_predictions
            query3 = "DELETE FROM model_predictions WHERE time < NOW() - INTERVAL '%s days'" % days
            await self._execute_query(query3)
            
            logger.info(f"Limpieza de datos antiguos completada: {days} días")
            
        except Exception as e:
            logger.error(f"Error en limpieza de datos antiguos: {e}")
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del gestor TimescaleDB"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del gestor TimescaleDB"""
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "pool_size": self.pool_size,
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del gestor TimescaleDB"""
        try:
            if not self.pool or not self.is_running:
                return False
            
            # Verificar conexión
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear gestor
def create_timescale_manager() -> TimescaleDataManager:
    """Crear instancia del gestor TimescaleDB"""
    return TimescaleDataManager()

if __name__ == "__main__":
    # Test del gestor TimescaleDB
    async def test_timescale_manager():
        manager = TimescaleDataManager()
        try:
            await manager.start()
            
            # Test de health check
            health = await manager.health_check()
            print(f"Health check: {health}")
            
            # Test de inserción de tick
            from .stream_collector import MarketTick
            tick = MarketTick(
                timestamp=datetime.now(timezone.utc),
                symbol="BTCUSDT",
                price=50000.0,
                volume=1.5
            )
            
            await manager.insert_market_tick(tick)
            
            # Test de obtención de datos
            data = await manager.get_latest_market_data("BTCUSDT", 10)
            print(f"Datos obtenidos: {len(data)}")
            
            # Mostrar métricas
            print("=== MÉTRICAS DEL GESTOR TIMESCALEDB ===")
            metrics = manager.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await manager.stop()
    
    # Ejecutar test
    asyncio.run(test_timescale_manager())
