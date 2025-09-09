"""
monitoring/core/real_time_manager.py
Gestor de Datos en Tiempo Real - Trading Bot v10

Esta clase maneja la obtención, procesamiento y distribución de datos
en tiempo real para el sistema de monitoreo. Gestiona WebSockets,
streams de datos y actualizaciones en vivo del dashboard.
"""

import logging
import asyncio
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import websocket
import numpy as np

# Importaciones del proyecto
try:
    from core.trading.exchange_connector import ExchangeConnector
    from core.data.stream_processor import StreamProcessor
    from core.config.user_config import UserConfig
except ImportError as e:
    logging.warning(f"Algunas importaciones del proyecto no están disponibles: {e}")
    ExchangeConnector = None
    StreamProcessor = None
    UserConfig = None

logger = logging.getLogger(__name__)

@dataclass
class RealTimePrice:
    """Precio en tiempo real"""
    symbol: str
    price: float
    change_24h: float
    change_24h_percentage: float
    volume_24h: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None

@dataclass
class RealTimeTrade:
    """Trade en tiempo real"""
    symbol: str
    side: str
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool

@dataclass
class RealTimeSignal:
    """Señal de trading en tiempo real"""
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float
    price: float
    timestamp: datetime
    model_version: str
    features_used: List[str]

@dataclass
class RealTimeMetrics:
    """Métricas en tiempo real"""
    symbol: str
    current_pnl: float
    unrealized_pnl: float
    position_size: float
    open_orders: int
    last_update: datetime

class RealTimeManager:
    """
    Gestor de datos en tiempo real para el sistema de monitoreo
    
    Maneja conexiones WebSocket, streams de datos y distribución
    en tiempo real de información crítica del trading bot.
    """
    
    def __init__(self, data_provider=None):
        """
        Inicializa el gestor de tiempo real
        
        Args:
            data_provider: Proveedor de datos para integración
        """
        self.data_provider = data_provider
        self.exchange_connector = None
        self.stream_processor = None
        
        # Estado del gestor
        self._running = False
        self._connected = False
        self._last_error = None
        
        # Configuración
        self.config = self._load_config()
        
        # Buffers de datos en tiempo real
        self.price_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.trade_buffer = defaultdict(lambda: deque(maxlen=500))
        self.signal_buffer = defaultdict(lambda: deque(maxlen=100))
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=200))
        
        # Subscriptores para eventos en tiempo real
        self.price_subscribers = []
        self.trade_subscribers = []
        self.signal_subscribers = []
        self.metrics_subscribers = []
        
        # Threads y conexiones
        self.ws_thread = None
        self.processing_thread = None
        self.ws_connections = {}
        
        # Lock para thread safety
        self._lock = threading.RLock()
        
        # Estadísticas
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'uptime_start': None,
            'last_message_time': None
        }
        
        self._initialize_connections()
        
        logger.info("RealTimeManager inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración del gestor de tiempo real"""
        return {
            'websocket_timeout': 30,
            'reconnect_interval': 5,
            'max_reconnect_attempts': 10,
            'buffer_size': 1000,
            'processing_interval': 0.1,  # 100ms
            'heartbeat_interval': 30,
            'price_update_threshold': 0.001,  # 0.1% cambio mínimo
            'enable_trade_stream': True,
            'enable_signal_stream': True,
            'enable_metrics_stream': True
        }
    
    def _initialize_connections(self):
        """Inicializa conexiones con fuentes de datos en tiempo real"""
        try:
            if ExchangeConnector:
                self.exchange_connector = ExchangeConnector()
            
            if StreamProcessor:
                self.stream_processor = StreamProcessor()
            
            logger.info("Conexiones de tiempo real inicializadas")
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error al inicializar conexiones de tiempo real: {e}")
    
    def start(self):
        """Inicia el gestor de tiempo real"""
        if self._running:
            logger.warning("RealTimeManager ya está ejecutándose")
            return
        
        try:
            self._running = True
            self.stats['uptime_start'] = datetime.now()
            
            # Iniciar thread de WebSocket
            self.ws_thread = threading.Thread(target=self._websocket_worker, daemon=True)
            self.ws_thread.start()
            
            # Iniciar thread de procesamiento
            self.processing_thread = threading.Thread(target=self._processing_worker, daemon=True)
            self.processing_thread.start()
            
            logger.info("RealTimeManager iniciado correctamente")
            
        except Exception as e:
            self._running = False
            self._last_error = str(e)
            logger.error(f"Error al iniciar RealTimeManager: {e}")
            raise
    
    def stop(self):
        """Detiene el gestor de tiempo real"""
        if not self._running:
            return
        
        logger.info("Deteniendo RealTimeManager...")
        
        self._running = False
        self._connected = False
        
        # Cerrar conexiones WebSocket
        for ws in self.ws_connections.values():
            try:
                ws.close()
            except:
                pass
        
        # Esperar que los threads terminen
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
        
        logger.info("RealTimeManager detenido")
    
    def is_running(self) -> bool:
        """Verifica si el gestor está ejecutándose"""
        return self._running
    
    def is_connected(self) -> bool:
        """Verifica si está conectado a las fuentes de datos"""
        return self._connected
    
    def get_last_error(self) -> Optional[str]:
        """Obtiene el último error ocurrido"""
        return self._last_error
    
    def _websocket_worker(self):
        """Worker principal para conexiones WebSocket"""
        reconnect_attempts = 0
        max_attempts = self.config['max_reconnect_attempts']
        
        while self._running:
            try:
                if not self._connected and reconnect_attempts < max_attempts:
                    self._connect_websockets()
                    if self._connected:
                        reconnect_attempts = 0
                    else:
                        reconnect_attempts += 1
                        time.sleep(self.config['reconnect_interval'])
                
                # Mantener conexiones vivas
                if self._connected:
                    self._send_heartbeats()
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error en websocket worker: {e}")
                self._connected = False
                reconnect_attempts += 1
                time.sleep(self.config['reconnect_interval'])
        
        logger.info("WebSocket worker detenido")
    
    def _processing_worker(self):
        """Worker para procesar datos en tiempo real"""
        while self._running:
            try:
                # Procesar datos acumulados
                self._process_pending_data()
                
                # Notificar a subscriptores
                self._notify_subscribers()
                
                # Limpiar buffers antiguos
                self._cleanup_old_data()
                
                time.sleep(self.config['processing_interval'])
                
            except Exception as e:
                logger.error(f"Error en processing worker: {e}")
                self.stats['errors'] += 1
                time.sleep(1)
        
        logger.info("Processing worker detenido")
    
    def _connect_websockets(self):
        """Conecta a todos los WebSockets necesarios"""
        try:
            if self.exchange_connector:
                symbols = self._get_symbols_to_monitor()
                
                # Conectar stream de precios
                if symbols:
                    price_ws = self._create_price_websocket(symbols)
                    if price_ws:
                        self.ws_connections['prices'] = price_ws
                
                # Conectar stream de trades
                if self.config['enable_trade_stream']:
                    trade_ws = self._create_trade_websocket(symbols)
                    if trade_ws:
                        self.ws_connections['trades'] = trade_ws
                
                self._connected = True
                logger.info("Conexiones WebSocket establecidas")
            else:
                # Simular conexión para desarrollo
                self._connected = True
                self._start_simulation_mode()
                
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.error(f"Error al conectar WebSockets: {e}")
    
    def _create_price_websocket(self, symbols: List[str]):
        """Crea WebSocket para stream de precios"""
        try:
            def on_price_message(ws, message):
                self._handle_price_message(message)
            
            def on_error(ws, error):
                logger.error(f"Error en price WebSocket: {error}")
                self._connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("Price WebSocket cerrado")
                self._connected = False
            
            # Aquí iría la URL real del exchange
            ws_url = self._build_price_stream_url(symbols)
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_price_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Iniciar en thread separado
            threading.Thread(target=ws.run_forever, daemon=True).start()
            
            return ws
            
        except Exception as e:
            logger.error(f"Error al crear price WebSocket: {e}")
            return None
    
    def _create_trade_websocket(self, symbols: List[str]):
        """Crea WebSocket para stream de trades"""
        try:
            def on_trade_message(ws, message):
                self._handle_trade_message(message)
            
            def on_error(ws, error):
                logger.error(f"Error en trade WebSocket: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning("Trade WebSocket cerrado")
            
            ws_url = self._build_trade_stream_url(symbols)
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_trade_message,
                on_error=on_error,
                on_close=on_close
            )
            
            threading.Thread(target=ws.run_forever, daemon=True).start()
            
            return ws
            
        except Exception as e:
            logger.error(f"Error al crear trade WebSocket: {e}")
            return None
    
    def _handle_price_message(self, message: str):
        """Procesa mensajes de precios en tiempo real"""
        try:
            data = json.loads(message)
            
            # Adaptar según formato del exchange
            price_data = RealTimePrice(
                symbol=data.get('symbol', ''),
                price=float(data.get('price', 0)),
                change_24h=float(data.get('change', 0)),
                change_24h_percentage=float(data.get('changePercent', 0)),
                volume_24h=float(data.get('volume', 0)),
                timestamp=datetime.now(),
                bid=float(data.get('bid', 0)) if data.get('bid') else None,
                ask=float(data.get('ask', 0)) if data.get('ask') else None
            )
            
            if price_data.bid and price_data.ask:
                price_data.spread = price_data.ask - price_data.bid
            
            # Agregar a buffer
            with self._lock:
                self.price_buffer[price_data.symbol].append(price_data)
            
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje de precio: {e}")
            self.stats['errors'] += 1
    
    def _handle_trade_message(self, message: str):
        """Procesa mensajes de trades en tiempo real"""
        try:
            data = json.loads(message)
            
            trade_data = RealTimeTrade(
                symbol=data.get('symbol', ''),
                side=data.get('side', ''),
                price=float(data.get('price', 0)),
                quantity=float(data.get('quantity', 0)),
                timestamp=datetime.now(),
                is_buyer_maker=data.get('isBuyerMaker', False)
            )
            
            with self._lock:
                self.trade_buffer[trade_data.symbol].append(trade_data)
            
            self.stats['messages_received'] += 1
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje de trade: {e}")
            self.stats['errors'] += 1
    
    def _start_simulation_mode(self):
        """Inicia modo de simulación para desarrollo"""
        def simulation_worker():
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
            base_prices = {'BTCUSDT': 50000, 'ETHUSDT': 3000, 'ADAUSDT': 1.5}
            
            while self._running:
                try:
                    for symbol in symbols:
                        # Simular precio
                        base_price = base_prices[symbol]
                        price_change = np.random.normal(0, base_price * 0.001)
                        new_price = base_price + price_change
                        base_prices[symbol] = new_price
                        
                        # Crear datos simulados
                        price_data = RealTimePrice(
                            symbol=symbol,
                            price=new_price,
                            change_24h=np.random.normal(0, base_price * 0.02),
                            change_24h_percentage=np.random.normal(0, 2),
                            volume_24h=np.random.uniform(1000000, 10000000),
                            timestamp=datetime.now(),
                            bid=new_price * 0.9995,
                            ask=new_price * 1.0005
                        )
                        price_data.spread = price_data.ask - price_data.bid
                        
                        with self._lock:
                            self.price_buffer[symbol].append(price_data)
                        
                        # Simular trades ocasionales
                        if np.random.random() < 0.3:  # 30% probabilidad
                            trade_data = RealTimeTrade(
                                symbol=symbol,
                                side=np.random.choice(['buy', 'sell']),
                                price=new_price,
                                quantity=np.random.uniform(0.01, 1.0),
                                timestamp=datetime.now(),
                                is_buyer_maker=np.random.choice([True, False])
                            )
                            
                            with self._lock:
                                self.trade_buffer[symbol].append(trade_data)
                    
                    self.stats['messages_received'] += len(symbols)
                    self.stats['last_message_time'] = datetime.now()
                    
                    time.sleep(1)  # Actualizar cada segundo
                    
                except Exception as e:
                    logger.error(f"Error en modo simulación: {e}")
                    time.sleep(5)
        
        threading.Thread(target=simulation_worker, daemon=True).start()
        logger.info("Modo simulación iniciado")
    
    def _get_symbols_to_monitor(self) -> List[str]:
        """Obtiene la lista de símbolos a monitorear"""
        if self.data_provider:
            return self.data_provider.get_configured_symbols()
        else:
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    def _build_price_stream_url(self, symbols: List[str]) -> str:
        """Construye URL para stream de precios"""
        # Ejemplo para Binance
        symbols_str = '/'.join([s.lower() + '@ticker' for s in symbols])
        return f"wss://stream.binance.com:9443/stream?streams={symbols_str}"
    
    def _build_trade_stream_url(self, symbols: List[str]) -> str:
        """Construye URL para stream de trades"""
        symbols_str = '/'.join([s.lower() + '@trade' for s in symbols])
        return f"wss://stream.binance.com:9443/stream?streams={symbols_str}"
    
    def _process_pending_data(self):
        """Procesa datos pendientes en los buffers"""
        # Procesar señales si están disponibles
        if self.stream_processor and self.config['enable_signal_stream']:
            self._process_signals()
        
        # Procesar métricas si están disponibles
        if self.config['enable_metrics_stream']:
            self._process_metrics()
        
        self.stats['messages_processed'] += 1
    
    def _process_signals(self):
        """Procesa señales de trading generadas por el modelo"""
        try:
            # Aquí se integraría con el sistema de señales del bot
            # Por ahora generamos señales de ejemplo
            symbols = self._get_symbols_to_monitor()
            
            for symbol in symbols:
                if np.random.random() < 0.1:  # 10% probabilidad de nueva señal
                    signal = RealTimeSignal(
                        symbol=symbol,
                        signal_type=np.random.choice(['buy', 'sell', 'hold'], p=[0.3, 0.3, 0.4]),
                        confidence=np.random.uniform(0.6, 0.95),
                        price=self._get_latest_price(symbol),
                        timestamp=datetime.now(),
                        model_version='10.2.1',
                        features_used=['rsi', 'macd', 'bollinger', 'volume']
                    )
                    
                    with self._lock:
                        self.signal_buffer[symbol].append(signal)
                        
        except Exception as e:
            logger.error(f"Error al procesar señales: {e}")
    
    def _process_metrics(self):
        """Procesa métricas en tiempo real"""
        try:
            symbols = self._get_symbols_to_monitor()
            
            for symbol in symbols:
                metrics = RealTimeMetrics(
                    symbol=symbol,
                    current_pnl=np.random.normal(50, 100),
                    unrealized_pnl=np.random.normal(0, 20),
                    position_size=np.random.uniform(0, 1),
                    open_orders=np.random.randint(0, 5),
                    last_update=datetime.now()
                )
                
                with self._lock:
                    self.metrics_buffer[symbol].append(metrics)
                    
        except Exception as e:
            logger.error(f"Error al procesar métricas: {e}")
    
    def _notify_subscribers(self):
        """Notifica a todos los subscriptores de nuevos datos"""
        try:
            # Notificar subscriptores de precios
            for callback in self.price_subscribers:
                try:
                    latest_prices = self._get_latest_prices()
                    if latest_prices:
                        callback(latest_prices)
                except Exception as e:
                    logger.error(f"Error al notificar subscriptor de precios: {e}")
            
            # Notificar subscriptores de trades
            for callback in self.trade_subscribers:
                try:
                    latest_trades = self._get_latest_trades()
                    if latest_trades:
                        callback(latest_trades)
                except Exception as e:
                    logger.error(f"Error al notificar subscriptor de trades: {e}")
            
            # Notificar subscriptores de señales
            for callback in self.signal_subscribers:
                try:
                    latest_signals = self._get_latest_signals()
                    if latest_signals:
                        callback(latest_signals)
                except Exception as e:
                    logger.error(f"Error al notificar subscriptor de señales: {e}")
                    
        except Exception as e:
            logger.error(f"Error general al notificar subscriptores: {e}")
    
    def _cleanup_old_data(self):
        """Limpia datos antiguos de los buffers"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        with self._lock:
            for symbol in list(self.price_buffer.keys()):
                buffer = self.price_buffer[symbol]
                # Mantener solo datos de la última hora
                while buffer and buffer[0].timestamp < cutoff_time:
                    buffer.popleft()
            
            for symbol in list(self.trade_buffer.keys()):
                buffer = self.trade_buffer[symbol]
                while buffer and buffer[0].timestamp < cutoff_time:
                    buffer.popleft()
    
    def _send_heartbeats(self):
        """Envía heartbeats para mantener conexiones vivas"""
        for ws_name, ws in self.ws_connections.items():
            try:
                if ws:
                    # Enviar ping según protocolo del exchange
                    ws.ping()
            except Exception as e:
                logger.error(f"Error al enviar heartbeat a {ws_name}: {e}")
    
    def _get_latest_price(self, symbol: str) -> float:
        """Obtiene el último precio para un símbolo"""
        with self._lock:
            buffer = self.price_buffer.get(symbol)
            if buffer:
                return buffer[-1].price
            return 0.0
    
    def _get_latest_prices(self) -> Dict[str, RealTimePrice]:
        """Obtiene los últimos precios para todos los símbolos"""
        latest_prices = {}
        with self._lock:
            for symbol, buffer in self.price_buffer.items():
                if buffer:
                    latest_prices[symbol] = buffer[-1]
        return latest_prices
    
    def _get_latest_trades(self) -> Dict[str, List[RealTimeTrade]]:
        """Obtiene los últimos trades por símbolo"""
        latest_trades = {}
        with self._lock:
            for symbol, buffer in self.trade_buffer.items():
                if buffer:
                    latest_trades[symbol] = list(buffer)[-10:]  # Últimos 10 trades
        return latest_trades
    
    def _get_latest_signals(self) -> Dict[str, RealTimeSignal]:
        """Obtiene las últimas señales por símbolo"""
        latest_signals = {}
        with self._lock:
            for symbol, buffer in self.signal_buffer.items():
                if buffer:
                    latest_signals[symbol] = buffer[-1]
        return latest_signals
    
    # API pública para subscripciones
    def subscribe_to_prices(self, callback: Callable[[Dict[str, RealTimePrice]], None]):
        """Suscribe a actualizaciones de precios"""
        self.price_subscribers.append(callback)
        logger.info("Nuevo subscriptor de precios agregado")
    
    def subscribe_to_trades(self, callback: Callable[[Dict[str, List[RealTimeTrade]]], None]):
        """Suscribe a actualizaciones de trades"""
        self.trade_subscribers.append(callback)
        logger.info("Nuevo subscriptor de trades agregado")
    
    def subscribe_to_signals(self, callback: Callable[[Dict[str, RealTimeSignal]], None]):
        """Suscribe a señales de trading"""
        self.signal_subscribers.append(callback)
        logger.info("Nuevo subscriptor de señales agregado")
    
    def get_current_prices(self) -> Dict[str, RealTimePrice]:
        """Obtiene precios actuales de todos los símbolos"""
        return self._get_latest_prices()
    
    def get_price_history(self, symbol: str, minutes: int = 60) -> List[RealTimePrice]:
        """Obtiene historial de precios para un símbolo"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            buffer = self.price_buffer.get(symbol, deque())
            return [price for price in buffer if price.timestamp >= cutoff_time]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de tiempo real"""
        uptime = None
        if self.stats['uptime_start']:
            uptime = (datetime.now() - self.stats['uptime_start']).total_seconds()
        
        return {
            'is_running': self._running,
            'is_connected': self._connected,
            'messages_received': self.stats['messages_received'],
            'messages_processed': self.stats['messages_processed'],
            'errors': self.stats['errors'],
            'uptime_seconds': uptime,
            'last_message_time': self.stats['last_message_time'],
            'active_connections': len(self.ws_connections),
            'monitored_symbols': len(self.price_buffer),
            'buffer_sizes': {
                'prices': sum(len(buffer) for buffer in self.price_buffer.values()),
                'trades': sum(len(buffer) for buffer in self.trade_buffer.values()),
                'signals': sum(len(buffer) for buffer in self.signal_buffer.values())
            }
        }

    def get_connection_status(self) -> Dict[str, Any]:
        """Devuelve estado resumido de conexiones y colas"""
        try:
            with self._lock:
                return {
                    'running': self._running,
                    'connected': self._connected,
                    'last_error': self._last_error,
                    'last_message_time': self.stats.get('last_message_time'),
                    'messages_received': self.stats.get('messages_received', 0),
                    'messages_processed': self.stats.get('messages_processed', 0),
                    'errors': self.stats.get('errors', 0),
                    'queue_sizes': {
                        'prices': {s: len(b) for s, b in self.price_buffer.items()},
                        'trades': {s: len(b) for s, b in self.trade_buffer.items()},
                        'signals': {s: len(b) for s, b in self.signal_buffer.items()},
                        'metrics': {s: len(b) for s, b in self.metrics_buffer.items()},
                    },
                    'subscribers': {
                        'prices': len(self.price_subscribers),
                        'trades': len(self.trade_subscribers),
                        'signals': len(self.signal_subscribers),
                        'metrics': len(self.metrics_subscribers),
                    },
                }
        except Exception as e:
            logger.error(f"Error obteniendo estado de conexión: {e}")
            return {'running': self._running, 'connected': self._connected, 'error': str(e)}

    def get_performance_stats(self) -> Dict[str, Any]:
        """Devuelve estadísticas de rendimiento y uptime"""
        try:
            with self._lock:
                uptime_seconds = 0.0
                if self.stats.get('uptime_start'):
                    uptime_seconds = (datetime.now() - self.stats['uptime_start']).total_seconds()
                return {
                    'uptime_seconds': uptime_seconds,
                    'messages': {
                        'received': self.stats.get('messages_received', 0),
                        'processed': self.stats.get('messages_processed', 0),
                        'errors': self.stats.get('errors', 0),
                    },
                    'buffers': {
                        'symbols_tracked': list({*self.price_buffer.keys(), *self.trade_buffer.keys()}),
                        'price_buffer_sizes': {s: len(b) for s, b in self.price_buffer.items()},
                        'trade_buffer_sizes': {s: len(b) for s, b in self.trade_buffer.items()},
                    },
                }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de rendimiento: {e}")
            return {'error': str(e)}