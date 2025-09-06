"""
trading/bitget_client.py
Cliente de Bitget para trading y datos de mercado
Ubicación: C:\TradingBot_v10\trading\bitget_client.py

Funcionalidades:
- Conexión REST API para órdenes y datos
- WebSocket para datos en tiempo real
- Soporte para mix/futures y spot
- Sandbox/testnet para testing
- Reconexión automática
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
import websockets
import ccxt
import os

from config.config_loader import user_config

logger = logging.getLogger(__name__)

class BitgetClient:
    """Cliente de Bitget para trading y datos de mercado"""
    
    def __init__(self):
        self.config = user_config
        self.trading_config = self.config.get_value(['trading'], {})
        
        # Configuración de API
        self.api_key = os.getenv('BITGET_API_KEY')
        self.secret_key = os.getenv('BITGET_SECRET_KEY')
        self.passphrase = os.getenv('BITGET_PASSPHRASE', '')
        
        # Modo de trading
        self.trading_mode = self.trading_config.get('mode', 'paper_trading')
        self.is_futures = self.trading_config.get('futures', True)
        
        # Cliente REST
        self.rest_client = None
        self._initialize_rest_client()
        
        # WebSocket
        self.ws_connections = {}
        self.ws_callbacks = {}
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 5
        
        logger.info(f"BitgetClient inicializado - Modo: {self.trading_mode}, Futures: {self.is_futures}")
    
    def _initialize_rest_client(self):
        """Inicializa el cliente REST de Bitget"""
        try:
            if not self.api_key or not self.secret_key:
                logger.warning("Credenciales de Bitget no configuradas")
                return
            
            # Configurar sandbox según el modo
            sandbox = self.trading_mode in ['paper_trading', 'backtesting']
            
            self.rest_client = ccxt.bitget({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'password': self.passphrase,
                'sandbox': sandbox,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap' if self.is_futures else 'spot',
                }
            })
            
            logger.info(f"Cliente REST inicializado - Sandbox: {sandbox}")
            
        except Exception as e:
            logger.error(f"Error inicializando cliente REST: {e}")
            self.rest_client = None
    
    async def get_market_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """
        Obtiene datos de mercado históricos
        
        Args:
            symbol: Símbolo del activo (ej: BTCUSDT)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Número de velas a obtener
        
        Returns:
            Lista de velas OHLCV
        """
        try:
            if not self.rest_client:
                logger.error("Cliente REST no inicializado")
                return []
            
            # Obtener datos históricos
            ohlcv = self.rest_client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convertir a formato estándar
            klines = []
            for candle in ohlcv:
                klines.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            logger.info(f"Datos obtenidos: {len(klines)} velas de {symbol}")
            return klines
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio actual de un símbolo
        
        Args:
            symbol: Símbolo del activo
        
        Returns:
            Precio actual o None si hay error
        """
        try:
            if not self.rest_client:
                return None
            
            ticker = self.rest_client.fetch_ticker(symbol)
            return float(ticker['last'])
            
        except Exception as e:
            logger.error(f"Error obteniendo precio actual: {e}")
            return None
    
    async def get_balance(self) -> Dict:
        """
        Obtiene el balance de la cuenta
        
        Returns:
            Diccionario con balances por moneda
        """
        try:
            if not self.rest_client:
                return {}
            
            balance = self.rest_client.fetch_balance()
            
            # Filtrar solo balances con saldo > 0
            filtered_balance = {}
            for currency, data in balance.items():
                if isinstance(data, dict) and data.get('free', 0) > 0:
                    filtered_balance[currency] = {
                        'free': data.get('free', 0),
                        'used': data.get('used', 0),
                        'total': data.get('total', 0)
                    }
            
            return filtered_balance
            
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {}
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = 'limit',
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Crea una orden en Bitget
        
        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            amount: Cantidad
            price: Precio (para órdenes limit)
            order_type: 'limit' o 'market'
            client_order_id: ID único del cliente
        
        Returns:
            Información de la orden creada
        """
        try:
            if not self.rest_client:
                logger.error("Cliente REST no inicializado")
                return None
            
            # Preparar parámetros
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount,
            }
            
            if order_type == 'limit' and price:
                order_params['price'] = price
            
            if client_order_id:
                order_params['clientOrderId'] = client_order_id
            
            # Crear orden
            order = self.rest_client.create_order(**order_params)
            
            logger.info(f"Orden creada: {order.get('id')} - {side} {amount} {symbol}")
            return order
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"Fondos insuficientes: {e}")
            return None
        except ccxt.InvalidOrder as e:
            logger.error(f"Orden inválida: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creando orden: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancela una orden
        
        Args:
            order_id: ID de la orden
            symbol: Símbolo del activo
        
        Returns:
            True si se canceló exitosamente
        """
        try:
            if not self.rest_client:
                return False
            
            self.rest_client.cancel_order(order_id, symbol)
            logger.info(f"Orden cancelada: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """
        Obtiene el estado de una orden
        
        Args:
            order_id: ID de la orden
            symbol: Símbolo del activo
        
        Returns:
            Estado de la orden
        """
        try:
            if not self.rest_client:
                return None
            
            order = self.rest_client.fetch_order(order_id, symbol)
            return order
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de orden: {e}")
            return None
    
    async def start_websocket(
        self,
        symbol: str,
        callback: Callable,
        topics: List[str] = None
    ) -> bool:
        """
        Inicia conexión WebSocket para datos en tiempo real
        
        Args:
            symbol: Símbolo del activo
            callback: Función callback para procesar datos
            topics: Lista de topics a suscribir
        
        Returns:
            True si se inició exitosamente
        """
        try:
            if symbol in self.ws_connections:
                logger.warning(f"WebSocket ya activo para {symbol}")
                return True
            
            # Topics por defecto
            if topics is None:
                topics = ['ticker', 'kline']
            
            # URL del WebSocket
            ws_url = self._get_websocket_url()
            
            # Crear conexión
            websocket = await websockets.connect(ws_url)
            self.ws_connections[symbol] = websocket
            self.ws_callbacks[symbol] = callback
            self.reconnect_attempts[symbol] = 0
            
            # Suscribir a topics
            await self._subscribe_to_topics(symbol, topics)
            
            # Iniciar loop de escucha
            asyncio.create_task(self._websocket_listener(symbol))
            
            logger.info(f"WebSocket iniciado para {symbol} - Topics: {topics}")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando WebSocket: {e}")
            return False
    
    def _get_websocket_url(self) -> str:
        """Obtiene la URL del WebSocket según el modo"""
        if self.trading_mode in ['paper_trading', 'backtesting']:
            # Sandbox/testnet
            return "wss://ws-sandbox.bitget.com/spot/v1/stream"
        else:
            # Live
            if self.is_futures:
                return "wss://ws.bitget.com/spot/v1/stream"
            else:
                return "wss://ws.bitget.com/spot/v1/stream"
    
    async def _subscribe_to_topics(self, symbol: str, topics: List[str]):
        """Suscribe a topics específicos"""
        try:
            websocket = self.ws_connections[symbol]
            
            for topic in topics:
                if topic == 'ticker':
                    message = {
                        "op": "subscribe",
                        "args": [{"instType": "SPOT", "channel": "ticker", "instId": symbol}]
                    }
                elif topic == 'kline':
                    message = {
                        "op": "subscribe",
                        "args": [{"instType": "SPOT", "channel": "candle1m", "instId": symbol}]
                    }
                else:
                    continue
                
                await websocket.send(json.dumps(message))
                logger.info(f"Suscrito a {topic} para {symbol}")
                
        except Exception as e:
            logger.error(f"Error suscribiendo a topics: {e}")
    
    async def _websocket_listener(self, symbol: str):
        """Loop principal del WebSocket"""
        try:
            websocket = self.ws_connections[symbol]
            callback = self.ws_callbacks[symbol]
            
            while True:
                try:
                    # Recibir mensaje
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Procesar con callback
                    if callback:
                        await callback(symbol, data)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"WebSocket cerrado para {symbol}")
                    break
                except Exception as e:
                    logger.error(f"Error en WebSocket listener: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error en WebSocket listener: {e}")
        finally:
            # Limpiar conexión
            if symbol in self.ws_connections:
                del self.ws_connections[symbol]
            if symbol in self.ws_callbacks:
                del self.ws_callbacks[symbol]
            
            # Intentar reconexión
            await self._attempt_reconnection(symbol)
    
    async def _attempt_reconnection(self, symbol: str):
        """Intenta reconectar WebSocket"""
        try:
            attempts = self.reconnect_attempts.get(symbol, 0)
            
            if attempts >= self.max_reconnect_attempts:
                logger.error(f"Max intentos de reconexión alcanzados para {symbol}")
                return
            
            # Incrementar contador
            self.reconnect_attempts[symbol] = attempts + 1
            
            # Esperar antes de reconectar
            wait_time = min(2 ** attempts, 30)  # Backoff exponencial
            logger.info(f"Reconectando {symbol} en {wait_time}s (intento {attempts + 1})")
            await asyncio.sleep(wait_time)
            
            # Intentar reconectar
            callback = self.ws_callbacks.get(symbol)
            if callback:
                await self.start_websocket(symbol, callback)
            
        except Exception as e:
            logger.error(f"Error en reconexión: {e}")
    
    async def stop_websocket(self, symbol: str) -> bool:
        """
        Detiene la conexión WebSocket
        
        Args:
            symbol: Símbolo del activo
        
        Returns:
            True si se detuvo exitosamente
        """
        try:
            if symbol not in self.ws_connections:
                return True
            
            websocket = self.ws_connections[symbol]
            await websocket.close()
            
            # Limpiar
            del self.ws_connections[symbol]
            if symbol in self.ws_callbacks:
                del self.ws_callbacks[symbol]
            if symbol in self.reconnect_attempts:
                del self.reconnect_attempts[symbol]
            
            logger.info(f"WebSocket detenido para {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error deteniendo WebSocket: {e}")
            return False
    
    async def stop_all_websockets(self) -> bool:
        """Detiene todas las conexiones WebSocket"""
        try:
            symbols = list(self.ws_connections.keys())
            
            for symbol in symbols:
                await self.stop_websocket(symbol)
            
            logger.info("Todos los WebSockets detenidos")
            return True
            
        except Exception as e:
            logger.error(f"Error deteniendo WebSockets: {e}")
            return False
    
    def get_connection_status(self) -> Dict:
        """Obtiene el estado de las conexiones"""
        return {
            'rest_client': self.rest_client is not None,
            'ws_connections': list(self.ws_connections.keys()),
            'reconnect_attempts': dict(self.reconnect_attempts),
            'trading_mode': self.trading_mode,
            'is_futures': self.is_futures
        }
    
    async def health_check(self) -> Dict:
        """Verifica el estado de salud del cliente"""
        try:
            health_status = {
                'rest_api': False,
                'websocket': False,
                'credentials': bool(self.api_key and self.secret_key),
                'trading_mode': self.trading_mode
            }
            
            # Verificar REST API
            if self.rest_client:
                try:
                    # Intentar obtener ticker
                    ticker = self.rest_client.fetch_ticker('BTCUSDT')
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

# Instancia global
bitget_client = BitgetClient()
