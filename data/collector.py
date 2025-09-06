"""
data/collector.py
Recolector de datos de mercado desde Bitget API
Ubicación: C:\TradingBot_v10\data\collector.py

Funcionalidades:
- Recolección de datos históricos de OHLCV
- Stream en tiempo real via WebSocket
- Manejo robusto de errores y reconexiones
- Almacenamiento eficiente en base de datos
"""

import asyncio
import websockets
import json
import hmac
import hashlib
import base64
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
import pandas as pd
import ccxt
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
import aiohttp
import ssl

from .database import db_manager, MarketData
from config.config_loader import user_config

logger = logging.getLogger(__name__)

@dataclass
class BitgetCredentials:
    """Credenciales de Bitget API"""
    api_key: str
    secret_key: str
    passphrase: str
    
    @property
    def is_valid(self) -> bool:
        return bool(self.api_key and self.secret_key)

class BitgetDataCollector:
    """Recolector de datos de Bitget"""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.exchange = None
        self.websocket = None
        self.running = False
        self.tick_callbacks = []
        self.kline_callbacks = []
        self._setup_exchange()
    
    def _load_credentials(self) -> BitgetCredentials:
        """Carga credenciales desde variables de entorno"""
        return BitgetCredentials(
            api_key=os.getenv("BITGET_API_KEY", ""),
            secret_key=os.getenv("BITGET_SECRET_KEY", ""),
            passphrase=os.getenv("BITGET_PASSPHRASE", "")
        )
    
    def _setup_exchange(self):
        """Configura el exchange CCXT"""
        try:
            self.exchange = ccxt.bitget({
                'apiKey': self.credentials.api_key,
                'secret': self.credentials.secret_key,
                'password': self.credentials.passphrase,
                'sandbox': False,  # Cambiar a True para testing
                'enableRateLimit': True,
                'timeout': 30000,
            })
            logger.info("Exchange Bitget configurado exitosamente")
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            self.exchange = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica el estado del recolector"""
        health = {
            'credentials_configured': self.credentials.is_valid,
            'exchange_configured': self.exchange is not None,
            'rest_api_ok': False,
            'websocket_ok': False,
            'data_freshness_ok': False
        }
        
        try:
            # Verificar API REST
            if self.exchange:
                ticker = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.fetch_ticker, 'BTC/USDT'
                )
                health['rest_api_ok'] = True
                logger.debug("API REST funcionando correctamente")
            
            # Verificar WebSocket
            health['websocket_ok'] = self.websocket is not None and not self.websocket.closed
            
            # Verificar frescura de datos
            latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
            if not latest_data.empty:
                last_update = latest_data.index[-1]
                hours_since_update = (datetime.now() - last_update.tz_localize(None)).total_seconds() / 3600
                health['data_freshness_ok'] = hours_since_update < 2  # Datos de menos de 2 horas
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
        
        return health
    
    async def fetch_historical_data(self, symbol: str, timeframe: str = "1h", 
                                  days_back: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos"""
        try:
            if not self.exchange:
                raise Exception("Exchange no configurado")
            
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"Descargando datos históricos para {symbol} desde {start_date} hasta {end_date}")
            
            # Obtener datos usando CCXT
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_ohlcv,
                symbol.replace('USDT', '/USDT'),
                timeframe,
                int(start_date.timestamp() * 1000),
                None,
                {'limit': 1000}
            )
            
            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['symbol'] = symbol
            
            logger.info(f"Descargados {len(df)} registros históricos")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return pd.DataFrame()
    
    async def save_historical_data(self, df: pd.DataFrame) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                return 0
            
            saved_count = 0
            for timestamp, row in df.iterrows():
                market_data = MarketData(
                    symbol=row['symbol'],
                    timestamp=int(timestamp.timestamp()),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume'])
                )
                
                if db_manager.save_market_data(market_data):
                    saved_count += 1
            
            logger.info(f"Guardados {saved_count} registros en base de datos")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error guardando datos históricos: {e}")
            return 0
    
    def add_tick_callback(self, callback: Callable):
        """Añade callback para datos de tick"""
        self.tick_callbacks.append(callback)
    
    def add_kline_callback(self, callback: Callable):
        """Añade callback para datos de kline"""
        self.kline_callbacks.append(callback)
    
    async def start_websocket_stream(self):
        """Inicia el stream de WebSocket"""
        try:
            if not self.credentials.is_valid:
                logger.error("Credenciales no configuradas para WebSocket")
                return
            
            self.running = True
            logger.info("Iniciando stream de WebSocket...")
            
            # URL del WebSocket de Bitget
            ws_url = "wss://ws.bitget.com/spot/v1/stream"
            
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                
                # Suscribirse a datos de tick y kline
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [
                        {"instType": "SPOT", "channel": "ticker", "instId": "BTCUSDT"},
                        {"instType": "SPOT", "channel": "candle1h", "instId": "BTCUSDT"}
                    ]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                logger.info("Suscrito a datos en tiempo real")
                
                # Escuchar mensajes
                async for message in websocket:
                    if not self.running:
                        break
                    
                    try:
                        data = json.loads(message)
                        await self._handle_websocket_message(data)
                    except json.JSONDecodeError:
                        logger.warning("Mensaje WebSocket inválido recibido")
                    except Exception as e:
                        logger.error(f"Error procesando mensaje WebSocket: {e}")
        
        except Exception as e:
            logger.error(f"Error en WebSocket stream: {e}")
        finally:
            self.running = False
            self.websocket = None
    
    async def _handle_websocket_message(self, data: Dict):
        """Maneja mensajes del WebSocket"""
        try:
            if 'data' in data:
                for item in data['data']:
                    if item.get('channel') == 'ticker':
                        await self._handle_tick_data(item)
                    elif item.get('channel') == 'candle1h':
                        await self._handle_kline_data(item)
        
        except Exception as e:
            logger.error(f"Error manejando mensaje WebSocket: {e}")
    
    async def _handle_tick_data(self, data: Dict):
        """Maneja datos de tick"""
        try:
            tick_data = {
                'symbol': data.get('instId', ''),
                'price': float(data.get('last', 0)),
                'volume': float(data.get('vol24h', 0)),
                'timestamp': datetime.now()
            }
            
            # Ejecutar callbacks
            for callback in self.tick_callbacks:
                try:
                    callback(tick_data)
                except Exception as e:
                    logger.error(f"Error en callback de tick: {e}")
        
        except Exception as e:
            logger.error(f"Error procesando tick data: {e}")
    
    async def _handle_kline_data(self, data: Dict):
        """Maneja datos de kline"""
        try:
            kline_data = {
                'symbol': data.get('instId', ''),
                'open': float(data.get('open', 0)),
                'high': float(data.get('high', 0)),
                'low': float(data.get('low', 0)),
                'close': float(data.get('close', 0)),
                'volume': float(data.get('vol', 0)),
                'timestamp': datetime.now()
            }
            
            # Ejecutar callbacks
            for callback in self.kline_callbacks:
                try:
                    callback(kline_data)
                except Exception as e:
                    logger.error(f"Error en callback de kline: {e}")
        
        except Exception as e:
            logger.error(f"Error procesando kline data: {e}")
    
    def stop_websocket_stream(self):
        """Detiene el stream de WebSocket"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia global del recolector
data_collector = BitgetDataCollector()

async def collect_and_save_historical_data(symbol: str, timeframe: str = "1h", 
                                         days_back: int = 30) -> int:
    """Función helper para recolectar y guardar datos históricos"""
    try:
        # Obtener datos históricos
        df = await data_collector.fetch_historical_data(symbol, timeframe, days_back)
        
        if df.empty:
            logger.warning("No se obtuvieron datos históricos")
            return 0
        
        # Guardar en base de datos
        saved_count = await data_collector.save_historical_data(df)
        
        return saved_count
        
    except Exception as e:
        logger.error(f"Error en recolección de datos históricos: {e}")
        return 0