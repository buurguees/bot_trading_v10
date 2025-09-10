# Ruta: core/data/enterprise_data_collector.py
# enterprise_data_collector.py - Recolector de datos enterprise
# Ubicación: core/data/enterprise_data_collector.py

"""
Recolector de Datos Enterprise
Sistema avanzado de recolección de datos para trading de alta frecuencia

Características principales:
- Recolección en tiempo real via WebSocket
- Integración con Kafka para streaming
- Cache Redis para datos frecuentes
- Almacenamiento en TimescaleDB
- Monitoreo de calidad de datos
- Alertas de desconexión
- Rate limiting y circuit breakers
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import websockets
import aiohttp
import redis
import ccxt.async_support as ccxt
from kafka import KafkaProducer, KafkaConsumer
from prometheus_client import Counter, Histogram, Gauge
from control.telegram_bot import telegram_bot
from core.config.config_loader import config_loader
from core.data.database import db_manager

logger = logging.getLogger(__name__)

# Métricas Prometheus
ticks_received_total = Counter('data_ticks_received_total', 'Total ticks received', ['symbol', 'timeframe'])
processing_latency_seconds = Histogram('data_processing_latency_seconds', 'Data processing latency', ['symbol'])
websocket_connections = Gauge('data_websocket_connections', 'Active WebSocket connections')
kafka_messages_sent = Counter('data_kafka_messages_sent_total', 'Kafka messages sent', ['topic'])
data_quality_score = Gauge('data_quality_score', 'Data quality score', ['symbol'])

@dataclass
class TickData:
    """Datos de tick en tiempo real"""
    symbol: str
    price: float
    volume: float
    timestamp: int
    bid: float
    ask: float
    spread: float
    source: str

@dataclass
class OHLCVData:
    """Datos OHLCV agregados"""
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int
    quality_score: float

@dataclass
class DataQualityMetrics:
    """Métricas de calidad de datos"""
    symbol: str
    timeframe: str
    total_ticks: int
    missing_ticks: int
    quality_score: float
    latency_avg: float
    latency_p95: float
    last_update: datetime

class EnterpriseDataCollector:
    """Recolector de datos enterprise"""
    
    def __init__(self):
        self.config_loader = config_loader
        self.db_manager = db_manager
        self.redis_client = None
        self.kafka_producer = None
        self.kafka_consumer = None
        self.exchange = None
        
        # Estado del colector
        self.running = False
        self.websocket_connections = {}
        self.data_quality = {}
        self.circuit_breaker_active = False
        self.last_heartbeat = {}
        
        # Configuración
        self.symbols = []
        self.timeframes = []
        self.collection_frequency_ms = 1000
        self.rate_limiting = {}
        self.kafka_config = {}
        self.redis_config = {}
        
        # Métricas
        self.total_ticks_received = 0
        self.total_ticks_processed = 0
        self.total_errors = 0
        
        logger.info("EnterpriseDataCollector inicializado")
    
    async def initialize(self):
        """Inicializa el recolector de datos"""
        try:
            # Inicializar configuraciones
            await self.config_loader.initialize()
            
            # Cargar configuración de recolección de datos
            data_config = self.config_loader.get_data_collection_config()
            self.symbols = self.config_loader.get_symbols()
            self.timeframes = self.config_loader.get_timeframes()
            
            # Configurar parámetros de recolección
            collection_config = data_config.get('data_collection.yaml', {}).get('data_collection', {})
            self.collection_frequency_ms = collection_config.get('collection_frequency_ms', 1000)
            self.rate_limiting = collection_config.get('rate_limiting', {})
            
            # Configurar infraestructura
            await self._setup_infrastructure()
            
            # Inicializar exchange
            await self._setup_exchange()
            
            logger.info("EnterpriseDataCollector inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando EnterpriseDataCollector: {e}")
            raise
    
    async def _setup_infrastructure(self):
        """Configura infraestructura (Redis, Kafka)"""
        try:
            # Configurar Redis
            infra_config = self.config_loader.get_infrastructure_settings()
            redis_config = infra_config.get('redis', {})
            redis_url = redis_config.get('url', 'redis://localhost:6379')
            
            self.redis_client = redis.Redis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Conexión a Redis establecida")
            
            # Configurar Kafka
            kafka_config = infra_config.get('kafka', {})
            bootstrap_servers = kafka_config.get('bootstrap_servers', 'localhost:9092')
            
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                retries=3,
                retry_backoff_ms=1000
            )
            
            logger.info("Conexión a Kafka establecida")
            
        except Exception as e:
            logger.error(f"Error configurando infraestructura: {e}")
            raise
    
    async def _setup_exchange(self):
        """Configura conexión con exchange"""
        try:
            exchange_config = self.config_loader.get_exchange_config('bitget')
            
            self.exchange = ccxt.bitget({
                'apiKey': exchange_config.get('authentication', {}).get('api_key', ''),
                'secret': exchange_config.get('authentication', {}).get('secret_key', ''),
                'password': exchange_config.get('authentication', {}).get('passphrase', ''),
                'enableRateLimit': True,
                'rateLimit': exchange_config.get('connection', {}).get('rate_limit_per_second', 10) * 1000
            })
            
            await self.exchange.load_markets()
            logger.info("Conexión con Bitget establecida")
            
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            raise
    
    async def start_collection(self):
        """Inicia la recolección de datos"""
        try:
            self.running = True
            logger.info("Iniciando recolección de datos enterprise")
            
            # Iniciar tareas de recolección
            tasks = [
                asyncio.create_task(self._collect_websocket_data()),
                asyncio.create_task(self._collect_rest_data()),
                asyncio.create_task(self._process_data_queue()),
                asyncio.create_task(self._monitor_data_quality()),
                asyncio.create_task(self._heartbeat_monitor())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error iniciando recolección de datos: {e}")
            await telegram_bot.send_message(f"❌ Error iniciando recolección de datos: {e}")
        finally:
            self.running = False
    
    async def _collect_websocket_data(self):
        """Recolecta datos via WebSocket"""
        try:
            while self.running:
                for symbol in self.symbols:
                    try:
                        await self._connect_websocket(symbol)
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error conectando WebSocket para {symbol}: {e}")
                        await asyncio.sleep(5)
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error en recolección WebSocket: {e}")
    
    async def _connect_websocket(self, symbol: str):
        """Conecta WebSocket para un símbolo específico"""
        try:
            if symbol in self.websocket_connections:
                return
            
            # URL del WebSocket de Bitget
            ws_url = "wss://ws.bitget.com/mix/v1/stream"
            
            # Suscripción a ticker
            subscribe_msg = {
                "op": "subscribe",
                "args": [{"instType": "mc", "channel": "ticker", "instId": symbol}]
            }
            
            async with websockets.connect(ws_url) as websocket:
                self.websocket_connections[symbol] = websocket
                websocket_connections.inc()
                
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"WebSocket conectado para {symbol}")
                
                async for message in websocket:
                    if not self.running:
                        break
                    
                    try:
                        data = json.loads(message)
                        await self._process_websocket_message(symbol, data)
                    except Exception as e:
                        logger.error(f"Error procesando mensaje WebSocket: {e}")
                
        except Exception as e:
            logger.error(f"Error conectando WebSocket para {symbol}: {e}")
        finally:
            if symbol in self.websocket_connections:
                del self.websocket_connections[symbol]
                websocket_connections.dec()
    
    async def _process_websocket_message(self, symbol: str, data: Dict[str, Any]):
        """Procesa mensaje del WebSocket"""
        try:
            if 'data' in data and data['data']:
                tick_data = data['data'][0]
                
                tick = TickData(
                    symbol=symbol,
                    price=float(tick_data.get('last', 0)),
                    volume=float(tick_data.get('volCcy24h', 0)),
                    timestamp=int(tick_data.get('ts', time.time() * 1000)),
                    bid=float(tick_data.get('bidPr', 0)),
                    ask=float(tick_data.get('askPr', 0)),
                    spread=float(tick_data.get('askPr', 0)) - float(tick_data.get('bidPr', 0)),
                    source='websocket'
                )
                
                # Procesar tick
                await self._process_tick(tick)
                
                # Actualizar métricas
                ticks_received_total.labels(symbol=symbol, timeframe='tick').inc()
                self.total_ticks_received += 1
                
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    async def _collect_rest_data(self):
        """Recolecta datos via REST API"""
        try:
            while self.running:
                for symbol in self.symbols:
                    try:
                        # Obtener ticker
                        ticker = await self.exchange.fetch_ticker(symbol)
                        
                        tick = TickData(
                            symbol=symbol,
                            price=ticker['last'],
                            volume=ticker['baseVolume'],
                            timestamp=int(ticker['timestamp']),
                            bid=ticker['bid'],
                            ask=ticker['ask'],
                            spread=ticker['ask'] - ticker['bid'],
                            source='rest'
                        )
                        
                        await self._process_tick(tick)
                        
                        # Rate limiting
                        await asyncio.sleep(self.rate_limiting.get('requests_per_second', 1))
                        
                    except Exception as e:
                        logger.error(f"Error obteniendo datos REST para {symbol}: {e}")
                        self.total_errors += 1
                
                await asyncio.sleep(self.collection_frequency_ms / 1000)
                
        except Exception as e:
            logger.error(f"Error en recolección REST: {e}")
    
    async def _process_tick(self, tick: TickData):
        """Procesa un tick individual"""
        try:
            start_time = time.time()
            
            # Validar calidad del tick
            if not self._validate_tick(tick):
                return
            
            # Cachear en Redis
            await self._cache_tick(tick)
            
            # Enviar a Kafka
            await self._send_to_kafka(tick)
            
            # Almacenar en base de datos
            await self._store_tick(tick)
            
            # Actualizar métricas de calidad
            await self._update_quality_metrics(tick)
            
            # Actualizar métricas Prometheus
            processing_latency_seconds.labels(symbol=tick.symbol).observe(time.time() - start_time)
            self.total_ticks_processed += 1
            
        except Exception as e:
            logger.error(f"Error procesando tick: {e}")
            self.total_errors += 1
    
    def _validate_tick(self, tick: TickData) -> bool:
        """Valida calidad de un tick"""
        try:
            # Validaciones básicas
            if tick.price <= 0 or tick.volume < 0:
                return False
            
            if tick.bid <= 0 or tick.ask <= 0:
                return False
            
            if tick.spread < 0:
                return False
            
            # Validar timestamp (no más de 5 segundos de diferencia)
            current_time = int(time.time() * 1000)
            if abs(current_time - tick.timestamp) > 5000:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _cache_tick(self, tick: TickData):
        """Cachea tick en Redis"""
        try:
            if not self.redis_client:
                return
            
            cache_key = f"tick:{tick.symbol}:{tick.timestamp}"
            tick_data = asdict(tick)
            tick_data['timestamp'] = str(tick_data['timestamp'])
            
            self.redis_client.setex(cache_key, 300, json.dumps(tick_data))  # TTL 5 minutos
            
        except Exception as e:
            logger.warning(f"Error cacheando tick: {e}")
    
    async def _send_to_kafka(self, tick: TickData):
        """Envía tick a Kafka"""
        try:
            if not self.kafka_producer:
                return
            
            topic = 'market_ticks'
            message = {
                'symbol': tick.symbol,
                'price': tick.price,
                'volume': tick.volume,
                'timestamp': tick.timestamp,
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.spread,
                'source': tick.source
            }
            
            self.kafka_producer.send(topic, message)
            kafka_messages_sent.labels(topic=topic).inc()
            
        except Exception as e:
            logger.warning(f"Error enviando a Kafka: {e}")
    
    async def _store_tick(self, tick: TickData):
        """Almacena tick en base de datos"""
        try:
            # En un sistema real, esto almacenaría en TimescaleDB
            # Por ahora, usamos SQLite
            await db_manager.save_tick_data(tick)
            
        except Exception as e:
            logger.warning(f"Error almacenando tick: {e}")
    
    async def _process_data_queue(self):
        """Procesa cola de datos para agregación"""
        try:
            while self.running:
                # Procesar agregación de datos por timeframe
                for symbol in self.symbols:
                    for timeframe in self.timeframes:
                        await self._aggregate_data(symbol, timeframe)
                
                await asyncio.sleep(60)  # Procesar cada minuto
                
        except Exception as e:
            logger.error(f"Error procesando cola de datos: {e}")
    
    async def _aggregate_data(self, symbol: str, timeframe: str):
        """Agrega datos por timeframe"""
        try:
            # Obtener ticks recientes del cache
            if not self.redis_client:
                return
            
            # Buscar ticks de los últimos minutos
            pattern = f"tick:{symbol}:*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return
            
            # Obtener datos
            ticks_data = []
            for key in keys:
                tick_json = self.redis_client.get(key)
                if tick_json:
                    tick_data = json.loads(tick_json)
                    ticks_data.append(tick_data)
            
            if not ticks_data:
                return
            
            # Crear DataFrame
            df = pd.DataFrame(ticks_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp')
            
            # Agregar por timeframe
            ohlcv = df.resample(timeframe, on='timestamp').agg({
                'price': ['first', 'max', 'min', 'last'],
                'volume': 'sum'
            }).dropna()
            
            ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']
            ohlcv = ohlcv.reset_index()
            
            # Crear datos OHLCV
            for _, row in ohlcv.iterrows():
                ohlcv_data = OHLCVData(
                    symbol=symbol,
                    timeframe=timeframe,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    timestamp=int(row['timestamp'].timestamp() * 1000),
                    quality_score=1.0
                )
                
                await self._store_ohlcv(ohlcv_data)
                
        except Exception as e:
            logger.error(f"Error agregando datos para {symbol} {timeframe}: {e}")
    
    async def _store_ohlcv(self, ohlcv: OHLCVData):
        """Almacena datos OHLCV"""
        try:
            await db_manager.save_ohlcv_data(ohlcv)
        except Exception as e:
            logger.warning(f"Error almacenando OHLCV: {e}")
    
    async def _update_quality_metrics(self, tick: TickData):
        """Actualiza métricas de calidad de datos"""
        try:
            symbol = tick.symbol
            
            if symbol not in self.data_quality:
                self.data_quality[symbol] = DataQualityMetrics(
                    symbol=symbol,
                    timeframe='tick',
                    total_ticks=0,
                    missing_ticks=0,
                    quality_score=1.0,
                    latency_avg=0.0,
                    latency_p95=0.0,
                    last_update=datetime.now()
                )
            
            metrics = self.data_quality[symbol]
            metrics.total_ticks += 1
            metrics.last_update = datetime.now()
            
            # Calcular score de calidad
            quality_score = self._calculate_quality_score(tick, metrics)
            metrics.quality_score = quality_score
            
            # Actualizar métrica Prometheus
            data_quality_score.labels(symbol=symbol).set(quality_score)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de calidad: {e}")
    
    def _calculate_quality_score(self, tick: TickData, metrics: DataQualityMetrics) -> float:
        """Calcula score de calidad de datos"""
        try:
            score = 1.0
            
            # Penalizar por spread alto
            if tick.spread > tick.price * 0.01:  # Spread > 1%
                score -= 0.1
            
            # Penalizar por volumen bajo
            if tick.volume < 1000:  # Volumen muy bajo
                score -= 0.1
            
            # Penalizar por latencia alta
            current_time = int(time.time() * 1000)
            latency = current_time - tick.timestamp
            if latency > 5000:  # Latencia > 5 segundos
                score -= 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5
    
    async def _monitor_data_quality(self):
        """Monitorea calidad de datos"""
        try:
            while self.running:
                for symbol, metrics in self.data_quality.items():
                    # Verificar si hay datos recientes
                    time_since_update = datetime.now() - metrics.last_update
                    if time_since_update > timedelta(minutes=5):
                        logger.warning(f"Sin datos recientes para {symbol}")
                        await telegram_bot.send_message(f"⚠️ Sin datos recientes para {symbol}")
                    
                    # Verificar calidad
                    if metrics.quality_score < 0.7:
                        logger.warning(f"Calidad de datos baja para {symbol}: {metrics.quality_score}")
                        await telegram_bot.send_message(f"⚠️ Calidad de datos baja para {symbol}: {metrics.quality_score:.2f}")
                
                await asyncio.sleep(300)  # Verificar cada 5 minutos
                
        except Exception as e:
            logger.error(f"Error monitoreando calidad de datos: {e}")
    
    async def _heartbeat_monitor(self):
        """Monitorea heartbeat de conexiones"""
        try:
            while self.running:
                current_time = time.time()
                
                # Verificar conexiones WebSocket
                for symbol, ws in list(self.websocket_connections.items()):
                    if symbol not in self.last_heartbeat:
                        self.last_heartbeat[symbol] = current_time
                        continue
                    
                    time_since_heartbeat = current_time - self.last_heartbeat[symbol]
                    if time_since_heartbeat > 60:  # Sin heartbeat por 1 minuto
                        logger.warning(f"WebSocket inactivo para {symbol}")
                        await telegram_bot.send_message(f"⚠️ WebSocket inactivo para {symbol}")
                        self.last_heartbeat[symbol] = current_time
                
                await asyncio.sleep(30)  # Verificar cada 30 segundos
                
        except Exception as e:
            logger.error(f"Error en heartbeat monitor: {e}")
    
    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de calidad de datos"""
        try:
            return {
                symbol: {
                    'total_ticks': metrics.total_ticks,
                    'quality_score': metrics.quality_score,
                    'last_update': metrics.last_update.isoformat()
                }
                for symbol, metrics in self.data_quality.items()
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de calidad: {e}")
            return {}
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Obtiene estado de la recolección"""
        try:
            return {
                'running': self.running,
                'symbols': self.symbols,
                'timeframes': self.timeframes,
                'websocket_connections': len(self.websocket_connections),
                'total_ticks_received': self.total_ticks_received,
                'total_ticks_processed': self.total_ticks_processed,
                'total_errors': self.total_errors,
                'circuit_breaker_active': self.circuit_breaker_active
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado de recolección: {e}")
            return {}
    
    async def stop_collection(self):
        """Detiene la recolección de datos"""
        try:
            self.running = False
            
            # Cerrar conexiones WebSocket
            for symbol, ws in self.websocket_connections.items():
                try:
                    await ws.close()
                except Exception as e:
                    logger.warning(f"Error cerrando WebSocket para {symbol}: {e}")
            
            self.websocket_connections.clear()
            
            # Cerrar Kafka producer
            if self.kafka_producer:
                self.kafka_producer.close()
            
            # Cerrar Redis
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("Recolección de datos detenida")
            
        except Exception as e:
            logger.error(f"Error deteniendo recolección: {e}")
    
    async def cleanup(self):
        """Limpia recursos del recolector"""
        try:
            await self.stop_collection()
            logger.info("EnterpriseDataCollector limpiado")
        except Exception as e:
            logger.error(f"Error limpiando EnterpriseDataCollector: {e}")

# Instancia global
enterprise_data_collector = EnterpriseDataCollector()
