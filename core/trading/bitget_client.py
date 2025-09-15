# Ruta: core/trading/bitget_client.py
"""
trading/bitget_client.py
Cliente de Bitget para trading y datos de mercado enterprise

Funcionalidades:
- Conexión REST API para órdenes y datos
- WebSocket para datos en tiempo real
- Soporte completo para futures trading (one-way/hedge mode)
- Leverage dinámico y gestión de posiciones
- Sandbox/testnet para testing
- Reconexión automática con backoff exponencial
- Integración con sistema de recopilación de datos
- Redis caching para datos WebSocket
"""

import asyncio
import logging
import json
import time
import hmac
import hashlib
import base64
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import websockets
import ccxt.async_support as ccxt
import os
from urllib.parse import urlencode
import redis

from core.config.config_loader import config_loader

logger = logging.getLogger(__name__)

class BitgetClient:
    """Cliente de Bitget para trading y datos de mercado enterprise"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or config_loader.get_main_config()
        
        # Configuración de API
        self.api_key = os.getenv('BITGET_API_KEY')
        self.secret_key = os.getenv('BITGET_SECRET_KEY')
        self.passphrase = os.getenv('BITGET_PASSPHRASE', '')
        
        # Modo de trading
        self.trading_mode = self.config.get('mode', 'paper_trading')
        self.is_futures = self.config.get('futures', True)
        self.position_mode = self.config.get('position_mode', 'one-way')  # one-way or hedge
        
        # URLs de API
        self.base_url = self._get_base_url()
        self.ws_url = self._get_websocket_url()
        
        # Cliente REST asíncrono
        self.rest_client = None
        self._initialize_rest_client()
        
        # WebSocket
        self.ws_connections = {}
        self.ws_callbacks = {}
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1
        
        # Redis para caching
        self.redis_client = None
        self._setup_redis()
        
        # Métricas
        self.requests_made = 0
        self.requests_failed = 0
        self.websocket_messages = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"BitgetClient enterprise inicializado - Modo: {self.trading_mode}, Futures: {self.is_futures}, Position Mode: {self.position_mode}")
    
    def _get_base_url(self) -> str:
        """Obtiene la URL base según el modo"""
        if self.trading_mode in ['paper_trading', 'backtesting']:
            return "https://api-sandbox.bitget.com"
        else:
            return "https://api.bitget.com"
    
    def _get_websocket_url(self) -> str:
        """Obtiene la URL de WebSocket según el modo"""
        if self.trading_mode in ['paper_trading', 'backtesting']:
            return "wss://ws-sandbox.bitget.com:443/mix/v1/stream"
        else:
            return "wss://ws.bitget.com:443/mix/v1/stream"
    
    def _setup_redis(self):
        """Configura Redis para caching de datos WebSocket"""
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            logger.info("Conexión a Redis establecida para caching")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
    
    def _initialize_rest_client(self):
        """Inicializa el cliente REST de ccxt"""
        try:
            exchange_config = {
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'password': self.passphrase,
                'enableRateLimit': True,
                'asyncio_loop': asyncio.get_event_loop()
            }
            self.rest_client = ccxt.bitget(exchange_config)
            self.rest_client.load_markets()
            logger.info("Cliente REST inicializado")
        except Exception as e:
            logger.error(f"Error inicializando cliente REST: {e}")
            self.rest_client = None
    
    async def set_position_mode(self, mode: str):
        """Configura el modo de posición (one-way o hedge)"""
        try:
            if mode not in ['one-way', 'hedge']:
                raise ValueError(f"Modo inválido: {mode}")
            endpoint = '/api/mix/v1/position/setPositionMode'
            params = {'positionMode': 'hedge_mode' if mode == 'hedge' else 'one_way_mode'}
            response = await self._signed_request('POST', endpoint, params)
            self.position_mode = mode
            logger.info(f"Modo de posición configurado: {mode}")
            return response
        except Exception as e:
            logger.error(f"Error configurando modo de posición: {e}")
            return None
    
    async def _signed_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Realiza una solicitud firmada a la API"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = params or {}
            query_string = urlencode(params)
            sign_str = f"{timestamp}{method.upper()}{endpoint}{query_string}"
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'ACCESS-KEY': self.api_key,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': timestamp,
                'ACCESS-PASSPHRASE': self.passphrase,
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}{endpoint}"
            if method.upper() == 'GET':
                response = await self.rest_client.fetch(url, method=method, headers=headers, params=params)
            else:
                response = await self.rest_client.fetch(url, method=method, headers=headers, body=json.dumps(params))
            
            self.requests_made += 1
            return response
        except Exception as e:
            self.requests_failed += 1
            logger.error(f"Error en solicitud firmada: {e}")
            return {'error': str(e)}
    
    async def fetch_ticker(self, symbol: str) -> Dict:
        """Obtiene el ticker del símbolo especificado"""
        try:
            # Verificar cache en Redis
            if self.redis_client:
                cache_key = f"ticker_{symbol}"
                cached_ticker = self.redis_client.get(cache_key)
                if cached_ticker:
                    self.cache_hits += 1
                    return json.loads(cached_ticker)
            
            ticker = await self.rest_client.fetch_ticker(symbol)
            self.requests_made += 1
            
            # Guardar en cache
            if self.redis_client:
                self.redis_client.setex(cache_key, 30, json.dumps(ticker))
            
            return ticker
        except Exception as e:
            self.requests_failed += 1
            logger.error(f"Error obteniendo ticker para {symbol}: {e}")
            return {'error': str(e)}
    
    async def fetch_balance(self) -> Dict:
        """Obtiene el balance de la cuenta"""
        try:
            if self.trading_mode == 'paper_trading':
                return {'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}}
            return await self.rest_client.fetch_balance()
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {'error': str(e)}
    
    async def create_order(self, symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, params: Dict = None) -> Dict:
        """Crea una orden en Bitget"""
        try:
            params = params or {}
            if self.is_futures:
                params['marginMode'] = 'isolated'
                params['productType'] = 'umcbl'  # USDT-M Futures
            order = await self.rest_client.create_order(symbol, order_type, side, amount, price, params)
            self.requests_made += 1
            return order
        except Exception as e:
            self.requests_failed += 1
            logger.error(f"Error creando orden para {symbol}: {e}")
            return {'error': str(e)}
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Configura el apalancamiento para un símbolo"""
        try:
            endpoint = '/api/mix/v1/position/setLeverage'
            params = {
                'symbol': symbol.replace('/', ''),
                'marginMode': 'isolated',
                'leverage': str(leverage)
            }
            response = await self._signed_request('POST', endpoint, params)
            logger.info(f"Leverage configurado para {symbol}: {leverage}x")
            return response
        except Exception as e:
            logger.error(f"Error configurando leverage para {symbol}: {e}")
            return {'error': str(e)}
    
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Obtiene las posiciones abiertas"""
        try:
            endpoint = '/api/mix/v1/position/allPosition'
            params = {'productType': 'umcbl'} if not symbol else {'symbol': symbol.replace('/', ''), 'productType': 'umcbl'}
            response = await self._signed_request('GET', endpoint, params)
            self.requests_made += 1
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    async def start_websocket(self, channels: List[str], callback: Callable, symbol: Optional[str] = None):
        """Inicia una conexión WebSocket"""
        try:
            ws_key = f"{symbol or 'global'}_{','.join(channels)}"
            self.ws_connections[ws_key] = None
            self.ws_callbacks[ws_key] = callback
            self.reconnect_attempts[ws_key] = 0
            asyncio.create_task(self._websocket_listener(ws_key, channels, symbol))
            logger.info(f"WebSocket iniciado para {ws_key}")
        except Exception as e:
            logger.error(f"Error iniciando WebSocket: {e}")
    
    async def _websocket_listener(self, ws_key: str, channels: List[str], symbol: Optional[str] = None):
        """Escucha mensajes WebSocket con reconexión automática"""
        while self.reconnect_attempts[ws_key] < self.max_reconnect_attempts:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws_connections[ws_key] = websocket
                    self.reconnect_attempts[ws_key] = 0
                    
                    # Suscribirse a canales
                    subscribe_msg = {
                        'op': 'subscribe',
                        'args': [{'instType': 'umcbl', 'channel': ch, 'instId': symbol.replace('/', '') if symbol else 'default'} for ch in channels]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    async for message in websocket:
                        self.websocket_messages += 1
                        data = json.loads(message)
                        await self.ws_callbacks[ws_key](data)
                
            except Exception as e:
                self.reconnect_attempts[ws_key] += 1
                delay = self.reconnect_delay * (2 ** self.reconnect_attempts[ws_key])
                logger.warning(f"WebSocket {ws_key} desconectado. Reintentando en {delay}s... ({self.reconnect_attempts[ws_key]}/{self.max_reconnect_attempts})")
                await asyncio.sleep(delay)
        
        logger.error(f"WebSocket {ws_key} alcanzó máximo de reintentos")
        self.ws_connections.pop(ws_key, None)
    
    async def stop_all_websockets(self):
        """Para todas las conexiones WebSocket"""
        for ws_key, websocket in list(self.ws_connections.items()):
            if websocket:
                await websocket.close()
                self.ws_connections.pop(ws_key, None)
        logger.info("Todas las conexiones WebSocket cerradas")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance"""
        return {
            'requests_made': self.requests_made,
            'requests_failed': self.requests_failed,
            'websocket_messages': self.websocket_messages,
            'success_rate': (self.requests_made - self.requests_failed) / self.requests_made if self.requests_made > 0 else 0,
            'websocket_connections': len(self.ws_connections),
            'reconnect_attempts': dict(self.reconnect_attempts),
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    async def health_check(self) -> Dict:
        """Verifica el estado de salud del cliente"""
        try:
            health_status = {
                'rest_api': False,
                'websocket': False,
                'credentials': bool(self.api_key and self.secret_key),
                'trading_mode': self.trading_mode,
                'is_futures': self.is_futures,
                'position_mode': self.position_mode,
                'performance_metrics': self.get_performance_metrics()
            }
            
            # Verificar REST API
            if self.rest_client:
                try:
                    ticker = await self.rest_client.fetch_ticker('BTCUSDT')
                    health_status['rest_api'] = True
                except Exception as e:
                    logger.warning(f"REST API no disponible: {e}")
            
            # Verificar WebSocket
            if self.ws_connections:
                health_status['websocket'] = True
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {'error': str(e)}
    
    async def close(self):
        """Cierra todas las conexiones"""
        try:
            await self.stop_all_websockets()
            if self.rest_client:
                await self.rest_client.close()
            if self.redis_client:
                self.redis_client.close()
            logger.info("✅ BitgetClient cerrado correctamente")
            
        except Exception as e:
            logger.error(f"Error cerrando BitgetClient: {e}")

# Instancia global
bitget_client = BitgetClient()