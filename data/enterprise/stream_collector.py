# stream_collector.py - Recopilador de datos en tiempo real enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\stream_collector.py

"""
Recopilador de datos en tiempo real para trading enterprise.

Características principales:
- Streaming WebSocket de Bitget para 10 símbolos
- Procesamiento en tiempo real con Kafka
- Almacenamiento histórico en TimescaleDB
- Validación y limpieza de datos
- Métricas de Prometheus
- Reconexión automática con backoff exponencial
"""

import asyncio
import logging
import json
import time
import websockets
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor
import ssl

# Kafka y base de datos
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import execute_values

# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Reconexión automática
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Imports del proyecto
from data.enterprise.database import TimescaleDBManager
from data.enterprise.preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)

@dataclass
class MarketTick:
    """Tick de mercado individual"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str = "bitget_websocket"

@dataclass
class OrderBookSnapshot:
    """Snapshot del order book"""
    symbol: str
    timestamp: datetime
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    source: str = "bitget_websocket"

class EnterpriseDataCollector:
    """
    Recopilador de datos en tiempo real enterprise
    """
    
    def __init__(self, symbols: List[str], config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el recopilador de datos
        
        Args:
            symbols: Lista de símbolos a recopilar
            config: Configuración del sistema
        """
        self.symbols = symbols
        self.config = config or self._default_config()
        
        # Estado del sistema
        self.is_running = False
        self.websocket = None
        self.connection_retries = 0
        self.max_retries = 10
        
        # Componentes del sistema
        self.kafka_producer = None
        self.timescaledb = TimescaleDBManager(self.config.get('database', {}))
        self.preprocessor = DataPreprocessor(self.config.get('preprocessing', {}))
        
        # Threading y control
        self.collection_thread = None
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Cache de datos
        self.tick_cache: Dict[str, List[MarketTick]] = {symbol: [] for symbol in symbols}
        self.candle_cache: Dict[str, pd.DataFrame] = {symbol: pd.DataFrame() for symbol in symbols}
        
        # Métricas de Prometheus
        self.setup_prometheus_metrics()
        
        # Configurar Kafka
        self.setup_kafka()
        
        logger.info(f"EnterpriseDataCollector inicializado para {len(symbols)} símbolos")
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'websocket': {
                'url': 'wss://ws.bitgetapi.com/v2/ws/public',
                'ping_interval': 30,
                'ping_timeout': 10,
                'max_size': 2**20,  # 1MB
                'compression': None
            },
            'kafka': {
                'bootstrap_servers': ['localhost:9092'],
                'topic_ticks': 'market_ticks',
                'topic_candles': 'market_candles',
                'topic_orderbook': 'market_orderbook',
                'batch_size': 1000,
                'linger_ms': 1000
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'trading_data',
                'user': 'postgres',
                'password': 'password'
            },
            'preprocessing': {
                'candle_interval': '1m',
                'indicators': ['rsi', 'macd', 'bollinger', 'atr', 'vwap'],
                'cache_size': 10000
            },
            'monitoring': {
                'prometheus_port': 8004,
                'health_check_interval': 30
            }
        }
    
    def setup_prometheus_metrics(self):
        """Configura métricas de Prometheus"""
        # Métricas de recopilación
        self.ticks_collected = Counter(
            'ticks_collected_total',
            'Total de ticks recopilados',
            ['symbol', 'source']
        )
        
        self.candles_processed = Counter(
            'candles_processed_total',
            'Total de velas procesadas',
            ['symbol', 'interval']
        )
        
        self.websocket_errors = Counter(
            'websocket_errors_total',
            'Total de errores de WebSocket',
            ['error_type']
        )
        
        self.data_latency = Histogram(
            'data_latency_seconds',
            'Latencia de datos desde el exchange',
            ['symbol'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        
        self.cache_size = Gauge(
            'data_cache_size',
            'Tamaño del cache de datos',
            ['symbol', 'type']
        )
        
        self.connection_status = Gauge(
            'websocket_connection_status',
            'Estado de conexión WebSocket',
            ['status']
        )
        
        # Iniciar servidor Prometheus
        port = self.config['monitoring']['prometheus_port']
        start_http_server(port)
        logger.info(f"Prometheus metrics server iniciado en puerto {port}")
    
    def setup_kafka(self):
        """Configura Kafka producer"""
        try:
            kafka_config = self.config['kafka']
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=kafka_config['bootstrap_servers'],
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                batch_size=kafka_config['batch_size'],
                linger_ms=kafka_config['linger_ms'],
                compression_type='gzip',
                retries=3,
                retry_backoff_ms=1000
            )
            logger.info("✅ Kafka producer configurado")
        except Exception as e:
            logger.error(f"❌ Error configurando Kafka: {e}")
            raise
    
    async def start_collection(self):
        """Inicia la recopilación de datos"""
        try:
            logger.info("🚀 Iniciando recopilación de datos enterprise")
            
            # Inicializar base de datos
            await self.timescaledb.initialize()
            
            # Iniciar hilos de procesamiento
            self.processing_thread = threading.Thread(
                target=self._processing_worker,
                daemon=True
            )
            self.processing_thread.start()
            
            # Iniciar recopilación WebSocket
            self.is_running = True
            await self._websocket_collection_loop()
            
        except Exception as e:
            logger.error(f"❌ Error iniciando recopilación: {e}")
            raise
        finally:
            await self.stop_collection()
    
    async def stop_collection(self):
        """Detiene la recopilación de datos"""
        logger.info("🛑 Deteniendo recopilación de datos...")
        
        self.is_running = False
        self.stop_event.set()
        
        # Cerrar WebSocket
        if self.websocket:
            await self.websocket.close()
        
        # Cerrar Kafka producer
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
        
        # Cerrar base de datos
        await self.timescaledb.close()
        
        logger.info("✅ Recopilación de datos detenida")
    
    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((websockets.exceptions.ConnectionClosed, ConnectionError))
    )
    async def _websocket_collection_loop(self):
        """Loop principal de recopilación WebSocket"""
        try:
            # Configurar SSL
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Conectar a WebSocket
            websocket_config = self.config['websocket']
            self.websocket = await websockets.connect(
                websocket_config['url'],
                ssl=ssl_context,
                ping_interval=websocket_config['ping_interval'],
                ping_timeout=websocket_config['ping_timeout'],
                max_size=websocket_config['max_size'],
                compression=websocket_config['compression']
            )
            
            # Suscribirse a canales
            await self._subscribe_to_channels()
            
            # Actualizar estado de conexión
            self.connection_status.labels(status='connected').set(1)
            self.connection_retries = 0
            
            logger.info("✅ Conectado a WebSocket de Bitget")
            
            # Loop de recopilación
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                try:
                    await self._process_websocket_message(message)
                except Exception as e:
                    logger.error(f"Error procesando mensaje WebSocket: {e}")
                    self.websocket_errors.labels(error_type='message_processing').inc()
            
        except Exception as e:
            logger.error(f"Error en WebSocket: {e}")
            self.websocket_errors.labels(error_type='connection').inc()
            self.connection_status.labels(status='disconnected').set(1)
            raise
        finally:
            if self.websocket:
                await self.websocket.close()
    
    async def _subscribe_to_channels(self):
        """Suscribe a canales de datos"""
        try:
            # Suscribirse a klines (velas) para todos los símbolos
            kline_subscription = {
                'op': 'subscribe',
                'args': [
                    {
                        'instType': 'sp',  # Spot
                        'channel': 'kline.1m',
                        'instId': symbol
                    }
                    for symbol in self.symbols
                ]
            }
            
            await self.websocket.send(json.dumps(kline_subscription))
            logger.info(f"✅ Suscrito a klines para {len(self.symbols)} símbolos")
            
            # Suscribirse a order book para símbolos principales
            main_symbols = self.symbols[:5]  # Primeros 5 símbolos
            orderbook_subscription = {
                'op': 'subscribe',
                'args': [
                    {
                        'instType': 'sp',
                        'channel': 'books',
                        'instId': symbol
                    }
                    for symbol in main_symbols
                ]
            }
            
            await self.websocket.send(json.dumps(orderbook_subscription))
            logger.info(f"✅ Suscrito a order book para {len(main_symbols)} símbolos")
            
        except Exception as e:
            logger.error(f"Error suscribiéndose a canales: {e}")
            raise
    
    async def _process_websocket_message(self, message: str):
        """Procesa mensaje del WebSocket"""
        try:
            data = json.loads(message)
            
            # Verificar tipo de mensaje
            if 'data' in data:
                channel = data.get('arg', {}).get('channel', '')
                symbol = data.get('arg', {}).get('instId', '')
                
                if 'kline' in channel:
                    await self._process_kline_data(data, symbol)
                elif 'books' in channel:
                    await self._process_orderbook_data(data, symbol)
                else:
                    logger.debug(f"Canal no reconocido: {channel}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
            self.websocket_errors.labels(error_type='json_decode').inc()
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            self.websocket_errors.labels(error_type='processing').inc()
    
    async def _process_kline_data(self, data: Dict[str, Any], symbol: str):
        """Procesa datos de velas"""
        try:
            kline_data = data['data'][0]  # Primer elemento del array
            
            # Crear tick de mercado
            tick = MarketTick(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(kline_data['ts']) / 1000),
                open=float(kline_data['open']),
                high=float(kline_data['high']),
                low=float(kline_data['low']),
                close=float(kline_data['close']),
                volume=float(kline_data['vol']),
                source='bitget_websocket'
            )
            
            # Validar datos
            if self._validate_tick(tick):
                # Agregar al cache
                self.tick_cache[symbol].append(tick)
                
                # Limitar tamaño del cache
                if len(self.tick_cache[symbol]) > 1000:
                    self.tick_cache[symbol] = self.tick_cache[symbol][-500:]
                
                # Enviar a Kafka
                await self._send_to_kafka('ticks', asdict(tick))
                
                # Actualizar métricas
                self.ticks_collected.labels(symbol=symbol, source='bitget').inc()
                self.cache_size.labels(symbol=symbol, type='ticks').set(len(self.tick_cache[symbol]))
                
                # Calcular latencia
                latency = (datetime.now() - tick.timestamp).total_seconds()
                self.data_latency.labels(symbol=symbol).observe(latency)
            
        except Exception as e:
            logger.error(f"Error procesando kline para {symbol}: {e}")
            self.websocket_errors.labels(error_type='kline_processing').inc()
    
    async def _process_orderbook_data(self, data: Dict[str, Any], symbol: str):
        """Procesa datos del order book"""
        try:
            orderbook_data = data['data'][0]
            
            # Crear snapshot del order book
            snapshot = OrderBookSnapshot(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(orderbook_data['ts']) / 1000),
                bids=[[float(bid[0]), float(bid[1])] for bid in orderbook_data['bids'][:10]],
                asks=[[float(ask[0]), float(ask[1])] for ask in orderbook_data['asks'][:10]],
                source='bitget_websocket'
            )
            
            # Enviar a Kafka
            await self._send_to_kafka('orderbook', asdict(snapshot))
            
        except Exception as e:
            logger.error(f"Error procesando order book para {symbol}: {e}")
            self.websocket_errors.labels(error_type='orderbook_processing').inc()
    
    def _validate_tick(self, tick: MarketTick) -> bool:
        """Valida un tick de mercado"""
        try:
            # Verificar precios positivos
            if any(price <= 0 for price in [tick.open, tick.high, tick.low, tick.close]):
                return False
            
            # Verificar que high >= low
            if tick.high < tick.low:
                return False
            
            # Verificar que high >= open, close y low <= open, close
            if tick.high < max(tick.open, tick.close) or tick.low > min(tick.open, tick.close):
                return False
            
            # Verificar volumen no negativo
            if tick.volume < 0:
                return False
            
            # Verificar timestamp reciente (no más de 1 hora atrás)
            if (datetime.now() - tick.timestamp).total_seconds() > 3600:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando tick: {e}")
            return False
    
    async def _send_to_kafka(self, data_type: str, data: Dict[str, Any]):
        """Envía datos a Kafka"""
        try:
            topic = f"market_{data_type}"
            self.kafka_producer.send(topic, data)
            
        except KafkaError as e:
            logger.error(f"Error enviando a Kafka: {e}")
            self.websocket_errors.labels(error_type='kafka_send').inc()
    
    def _processing_worker(self):
        """Worker para procesamiento de datos en background"""
        try:
            while not self.stop_event.is_set():
                # Procesar cache de ticks
                for symbol in self.symbols:
                    if len(self.tick_cache[symbol]) >= 60:  # 60 ticks = 1 minuto
                        self._process_candles(symbol)
                
                # Esperar antes del siguiente ciclo
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error en processing worker: {e}")
    
    def _process_candles(self, symbol: str):
        """Procesa ticks en velas"""
        try:
            ticks = self.tick_cache[symbol]
            if len(ticks) < 2:
                return
            
            # Convertir a DataFrame
            df = pd.DataFrame([asdict(tick) for tick in ticks])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Agrupar por minuto
            candles = df.resample('1T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(candles) > 0:
                # Calcular indicadores técnicos
                processed_candles = self.preprocessor.process_candles(candles, symbol)
                
                # Enviar a Kafka
                for timestamp, candle in processed_candles.iterrows():
                    candle_data = {
                        'symbol': symbol,
                        'timestamp': timestamp.isoformat(),
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close']),
                        'volume': float(candle['volume']),
                        'indicators': candle.get('indicators', {}).to_dict() if 'indicators' in candle else {}
                    }
                    
                    # Enviar a Kafka de forma síncrona
                    try:
                        self.kafka_producer.send('market_candles', candle_data)
                    except Exception as e:
                        logger.error(f"Error enviando vela a Kafka: {e}")
                
                # Actualizar métricas
                self.candles_processed.labels(symbol=symbol, interval='1m').inc(len(candles))
                
                # Limpiar cache procesado
                self.tick_cache[symbol] = []
                
        except Exception as e:
            logger.error(f"Error procesando velas para {symbol}: {e}")
    
    async def get_latest_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtiene los datos más recientes para un símbolo"""
        try:
            # Obtener de la base de datos
            data = await self.timescaledb.get_latest_data(symbol, limit)
            return data
            
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
            data = await self.timescaledb.get_historical_data(
                symbol, start_date, end_date, interval
            )
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos para {symbol}: {e}")
            return None
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la recopilación"""
        try:
            return {
                'is_running': self.is_running,
                'symbols_count': len(self.symbols),
                'cache_sizes': {
                    symbol: len(ticks) 
                    for symbol, ticks in self.tick_cache.items()
                },
                'connection_retries': self.connection_retries,
                'kafka_connected': self.kafka_producer is not None,
                'database_connected': self.timescaledb.is_connected()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica la salud del sistema"""
        try:
            status = {
                'healthy': True,
                'components': {}
            }
            
            # Verificar WebSocket
            status['components']['websocket'] = {
                'connected': self.websocket is not None and not self.websocket.closed,
                'retries': self.connection_retries
            }
            
            # Verificar Kafka
            status['components']['kafka'] = {
                'connected': self.kafka_producer is not None
            }
            
            # Verificar base de datos
            status['components']['database'] = {
                'connected': await self.timescaledb.health_check()
            }
            
            # Verificar cache
            status['components']['cache'] = {
                'total_ticks': sum(len(ticks) for ticks in self.tick_cache.values()),
                'symbols_with_data': len([s for s, ticks in self.tick_cache.items() if len(ticks) > 0])
            }
            
            # Determinar salud general
            status['healthy'] = all(
                comp.get('connected', False) 
                for comp in status['components'].values() 
                if 'connected' in comp
            )
            
            return status
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {'healthy': False, 'error': str(e)}