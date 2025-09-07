"""
data/collector.py - VERSIÓN CORREGIDA
Recolector de datos de mercado desde Bitget API
Ubicación: C:\TradingBot_v10\data\collector.py

CAMBIOS PRINCIPALES:
- Manejo correcto de símbolos sin credenciales de API
- Método save_historical_data implementado correctamente
- Mejor manejo de errores y logging
- Soporte para modo sin credenciales (usando datos públicos)
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
            # Configurar exchange sin credenciales para datos públicos
            config = {
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'swap',  # Usar futuros por defecto
                }
            }
            
            # Añadir credenciales solo si están disponibles
            if self.credentials.is_valid:
                config.update({
                    'apiKey': self.credentials.api_key,
                    'secret': self.credentials.secret_key,
                    'password': self.credentials.passphrase,
                })
                logger.info("Exchange configurado con credenciales")
            else:
                logger.info("Exchange configurado sin credenciales (solo datos públicos)")
            
            self.exchange = ccxt.bitget(config)
            
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            self.exchange = None
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normaliza el símbolo para Bitget"""
        # Convertir BTCUSDT a BTCUSDT para futuros
        if '/' not in symbol and symbol.endswith('USDT'):
            return symbol  # Ya está en formato correcto para futuros
        elif '/' in symbol:
            return symbol.replace('/', '')  # BTC/USDT -> BTCUSDT
        return symbol
    
    def _symbol_to_ccxt_format(self, symbol: str) -> str:
        """Convierte símbolo a formato CCXT"""
        normalized = self._normalize_symbol(symbol)
        if normalized.endswith('USDT'):
            base = normalized[:-4]  # Quitar USDT
            return f"{base}/USDT"
        return normalized
    
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
                try:
                    # Probar con un símbolo conocido
                    ticker = await asyncio.get_event_loop().run_in_executor(
                        None, self.exchange.fetch_ticker, 'BTC/USDT'
                    )
                    health['rest_api_ok'] = True
                    logger.debug("API REST funcionando correctamente")
                except Exception as e:
                    logger.warning(f"API REST limitada: {e}")
                    # Intentar sin credenciales
                    try:
                        exchange_public = ccxt.bitget({'enableRateLimit': True})
                        ticker = await asyncio.get_event_loop().run_in_executor(
                            None, exchange_public.fetch_ticker, 'BTC/USDT'
                        )
                        health['rest_api_ok'] = True
                        logger.debug("API REST pública funcionando")
                    except Exception as e2:
                        logger.error(f"API REST no disponible: {e2}")
            
            # Verificar WebSocket
            health['websocket_ok'] = self.websocket is not None and not self.websocket.closed
            
            # Verificar frescura de datos
            latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
            if not latest_data.empty:
                last_update = latest_data.index[-1]
                if hasattr(last_update, 'tz_localize'):
                    last_update = last_update.tz_localize(None) if last_update.tz is None else last_update.tz_convert(None)
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                health['data_freshness_ok'] = hours_since_update < 2  # Datos de menos de 2 horas
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
        
        return health
    
    async def fetch_historical_data(self, symbol: str, timeframe: str = "1h", 
                                  days_back: int = 30) -> pd.DataFrame:
        """Obtiene datos históricos con manejo robusto de errores"""
        try:
            if not self.exchange:
                logger.error("Exchange no configurado")
                return pd.DataFrame()
            
            # Normalizar símbolo
            ccxt_symbol = self._symbol_to_ccxt_format(symbol)
            original_symbol = self._normalize_symbol(symbol)
            
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"📥 Descargando {symbol} ({ccxt_symbol}) - {timeframe} - {days_back} días")
            
            all_data = []
            current_start = start_date
            limit = 200  # Límite conservador
            max_attempts = 10  # Máximo intentos de paginación
            attempts = 0
            
            while current_start < end_date and attempts < max_attempts:
                try:
                    attempts += 1
                    
                    # Obtener datos usando CCXT
                    since = int(current_start.timestamp() * 1000)
                    
                    logger.debug(f"Intento {attempts}: descargando desde {current_start}")
                    
                    ohlcv = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.exchange.fetch_ohlcv(
                            ccxt_symbol,
                            timeframe,
                            since,
                            limit
                        )
                    )
                    
                    if not ohlcv:
                        logger.warning(f"Sin datos en intento {attempts}")
                        break
                    
                    logger.debug(f"Obtenidos {len(ohlcv)} registros")
                    all_data.extend(ohlcv)
                    
                    # Actualizar fecha de inicio para la siguiente iteración
                    if len(ohlcv) > 0:
                        last_timestamp = ohlcv[-1][0]
                        current_start = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(
                            hours=1 if timeframe == '1h' else 
                            (4 if timeframe == '4h' else 24)
                        )
                    else:
                        break
                    
                    # Pausa para evitar rate limiting
                    await asyncio.sleep(0.2)
                    
                except ccxt.RateLimitExceeded:
                    logger.warning("Rate limit alcanzado, esperando...")
                    await asyncio.sleep(2)
                    continue
                    
                except ccxt.NetworkError as e:
                    logger.warning(f"Error de red en intento {attempts}: {e}")
                    await asyncio.sleep(1)
                    continue
                    
                except Exception as e:
                    logger.error(f"Error en paginación intento {attempts}: {e}")
                    break
            
            if not all_data:
                logger.error(f"❌ No se obtuvieron datos para {symbol}")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['symbol'] = original_symbol
            
            # Eliminar duplicados y ordenar
            df = df[~df.index.duplicated(keep='first')]
            df = df.sort_index()
            
            # Filtrar por rango de fechas solicitado
            df = df[df.index >= start_date]
            df = df[df.index <= end_date]
            
            logger.info(f"✅ Descargados {len(df)} registros para {symbol} ({df.index.min()} a {df.index.max()})")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos históricos para {symbol}: {e}")
            return pd.DataFrame()
    
    async def save_historical_data(self, df: pd.DataFrame) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                logger.warning("DataFrame vacío, no hay nada que guardar")
                return 0
            
            # DEBUG: Información del DataFrame
            logger.info(f"🔍 DEBUG: DataFrame creado con {len(df)} filas")
            logger.info(f"🔍 DEBUG: Columnas: {df.columns.tolist()}")
            logger.info(f"🔍 DEBUG: Primeras 3 filas:")
            logger.info(f"{df.head(3)}")
            
            saved_count = 0
            errors = 0
            
            logger.info(f"💾 Guardando {len(df)} registros en base de datos...")
            
            # Convertir DataFrame a lista de objetos MarketData para bulk save
            market_data_list = []
            
            for timestamp, row in df.iterrows():
                try:
                    # Crear objeto MarketData
                    market_data = MarketData(
                        symbol=row['symbol'],
                        timestamp=int(timestamp.timestamp()),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    market_data_list.append(market_data)
                        
                except Exception as e:
                    logger.error(f"Error creando objeto MarketData para {timestamp}: {e}")
                    errors += 1
                    continue
            
            # Usar bulk save para mejor rendimiento
            if market_data_list:
                saved_count = db_manager.bulk_save_market_data(market_data_list)
                logger.info(f"✅ Bulk save completado: {saved_count} registros guardados")
            else:
                logger.warning("No se crearon objetos MarketData válidos")
            
            if errors > 0:
                logger.warning(f"⚠️ {errors} errores al procesar datos")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos históricos: {e}")
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
                logger.warning("Sin credenciales para WebSocket, solo datos históricos disponibles")
                return
            
            self.running = True
            logger.info("🔄 Iniciando stream de WebSocket...")
            
            # URL del WebSocket de Bitget
            ws_url = "wss://ws.bitget.com/spot/v1/stream"
            
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                
                # Suscribirse a datos
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [
                        {
                            "channel": "ticker",
                            "instId": "BTCUSDT"
                        }
                    ]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        if 'data' in data:
                            await self._handle_websocket_message(data['data'])
                            
                    except asyncio.TimeoutError:
                        # Ping para mantener conexión
                        await websocket.ping()
                        continue
                        
                    except Exception as e:
                        logger.error(f"Error en WebSocket: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error iniciando WebSocket: {e}")
    
    async def _handle_websocket_message(self, data):
        """Maneja mensajes del WebSocket"""
        try:
            # Procesar datos de tick o kline según el tipo
            pass  # Implementar según necesidades específicas
        except Exception as e:
            logger.error(f"Error procesando mensaje WebSocket: {e}")
    
    def stop_websocket_stream(self):
        """Detiene el stream de WebSocket"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Instancia global del recolector
data_collector = BitgetDataCollector()

async def collect_and_save_historical_data(symbol: str, timeframe: str = "1h", 
                                         days_back: int = 30) -> int:
    """
    Función helper para recolectar y guardar datos históricos
    
    Args:
        symbol: Símbolo del activo (ej: BTCUSDT)
        timeframe: Marco temporal (1h, 4h, 1d)
        days_back: Días hacia atrás
    
    Returns:
        Número de registros guardados
    """
    try:
        logger.info(f"🚀 Iniciando recolección: {symbol} - {timeframe} - {days_back} días")
        
        # Obtener datos históricos
        df = await data_collector.fetch_historical_data(symbol, timeframe, days_back)
        
        if df.empty:
            logger.error(f"❌ No se obtuvieron datos para {symbol}")
            return 0
        
        # Guardar en base de datos
        saved_count = await data_collector.save_historical_data(df)
        
        logger.info(f"✅ Proceso completado: {saved_count} registros guardados para {symbol}")
        return saved_count
        
    except Exception as e:
        logger.error(f"❌ Error en recolección completa para {symbol}: {e}")
        return 0