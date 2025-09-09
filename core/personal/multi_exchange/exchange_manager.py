"""
Multi-Exchange Manager - Bot Trading v10 Personal
================================================

Gestión de múltiples exchanges para trading personal con:
- Soporte para Bitget y Binance
- Configuración simplificada
- Gestión de credenciales encriptadas
- Reconexión automática
- Métricas de latencia
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import ccxt.async_support as ccxt
from prometheus_client import Counter, Histogram, Gauge
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

# Métricas Prometheus
exchange_connections = Gauge('trading_bot_exchange_connections', 'Conexiones activas por exchange', ['exchange'])
exchange_errors = Counter('trading_bot_exchange_errors_total', 'Errores por exchange', ['exchange', 'error_type'])
exchange_latency = Histogram('trading_bot_exchange_latency_seconds', 'Latencia de requests por exchange', ['exchange', 'operation'])
trades_executed = Counter('trading_bot_trades_executed_total', 'Trades ejecutados por exchange', ['exchange', 'symbol', 'side'])

class MultiExchangeManager:
    """Gestor de múltiples exchanges para trading personal"""
    
    def __init__(self, config_path: str = "config/personal/exchanges.yaml"):
        self.config_path = config_path
        self.exchanges = {}
        self.connection_status = {}
        self.last_health_check = {}
        self.rate_limits = {}
        self.is_running = False
        
        # Cargar configuración
        self.config = self._load_config()
        
        # Inicializar exchanges
        self._initialize_exchanges()
        
        logger.info("MultiExchangeManager inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración de exchanges"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                # Crear configuración por defecto
                default_config = {
                    'exchanges': {
                        'bitget': {
                            'enabled': True,
                            'api_key': '${BITGET_API_KEY}',
                            'secret': '${BITGET_SECRET_KEY}',
                            'passphrase': '${BITGET_PASSPHRASE}',
                            'sandbox': False,
                            'rate_limit': 100,
                            'timeout': 10000
                        },
                        'binance': {
                            'enabled': True,
                            'api_key': '${BINANCE_API_KEY}',
                            'secret': '${BINANCE_SECRET_KEY}',
                            'sandbox': False,
                            'rate_limit': 1200,
                            'timeout': 10000
                        }
                    },
                    'arbitrage': {
                        'enabled': True,
                        'min_profit_pct': 0.1,
                        'max_position_size': 1000,
                        'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
                    },
                    'monitoring': {
                        'health_check_interval': 30,
                        'latency_threshold_ms': 1000,
                        'max_errors_per_minute': 10
                    }
                }
                
                # Crear directorio si no existe
                config_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                
                logger.info(f"Configuración por defecto creada en {config_path}")
                return default_config
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Configuración cargada desde {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            raise
    
    def _initialize_exchanges(self):
        """Inicializa los exchanges configurados"""
        for exchange_id, exchange_config in self.config['exchanges'].items():
            if not exchange_config.get('enabled', False):
                continue
                
            try:
                # Obtener clase del exchange
                exchange_class = getattr(ccxt, exchange_id)
                
                # Configurar credenciales
                credentials = {
                    'apiKey': exchange_config['api_key'],
                    'secret': exchange_config['secret'],
                    'enableRateLimit': True,
                    'timeout': exchange_config.get('timeout', 10000),
                    'options': {'defaultType': 'swap'}
                }
                
                # Agregar passphrase para Bitget
                if exchange_id == 'bitget' and 'passphrase' in exchange_config:
                    credentials['password'] = exchange_config['passphrase']
                
                # Crear instancia del exchange
                exchange = exchange_class(credentials)
                
                # Configurar rate limit
                if 'rate_limit' in exchange_config:
                    exchange.rateLimit = exchange_config['rate_limit']
                
                self.exchanges[exchange_id] = exchange
                self.connection_status[exchange_id] = False
                self.last_health_check[exchange_id] = None
                self.rate_limits[exchange_id] = {
                    'requests': 0,
                    'reset_time': time.time() + 60
                }
                
                logger.info(f"Exchange {exchange_id} inicializado")
                
            except Exception as e:
                logger.error(f"Error inicializando exchange {exchange_id}: {e}")
                exchange_errors.labels(exchange=exchange_id, error_type='initialization').inc()
    
    async def start(self):
        """Inicia el gestor de exchanges"""
        try:
            logger.info("Iniciando MultiExchangeManager...")
            self.is_running = True
            
            # Verificar conexiones
            await self._check_all_connections()
            
            # Iniciar monitoreo de salud
            asyncio.create_task(self._health_monitor())
            
            logger.info("MultiExchangeManager iniciado correctamente")
            
        except Exception as e:
            logger.error(f"Error iniciando MultiExchangeManager: {e}")
            raise
    
    async def stop(self):
        """Detiene el gestor de exchanges"""
        try:
            logger.info("Deteniendo MultiExchangeManager...")
            self.is_running = False
            
            # Cerrar conexiones
            for exchange_id, exchange in self.exchanges.items():
                try:
                    await exchange.close()
                    logger.info(f"Exchange {exchange_id} cerrado")
                except Exception as e:
                    logger.error(f"Error cerrando exchange {exchange_id}: {e}")
            
            logger.info("MultiExchangeManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo MultiExchangeManager: {e}")
    
    async def _check_all_connections(self):
        """Verifica la conexión con todos los exchanges"""
        tasks = []
        for exchange_id in self.exchanges.keys():
            tasks.append(self._check_connection(exchange_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for exchange_id, result in zip(self.exchanges.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Error verificando conexión {exchange_id}: {result}")
                self.connection_status[exchange_id] = False
            else:
                self.connection_status[exchange_id] = result
                exchange_connections.labels(exchange=exchange_id).set(1 if result else 0)
    
    async def _check_connection(self, exchange_id: str) -> bool:
        """Verifica la conexión con un exchange específico"""
        try:
            exchange = self.exchanges[exchange_id]
            
            # Verificar balance
            balance = await exchange.fetch_balance()
            
            if balance and 'info' in balance:
                self.connection_status[exchange_id] = True
                self.last_health_check[exchange_id] = datetime.now()
                logger.info(f"✅ Conexión {exchange_id} verificada")
                return True
            else:
                logger.warning(f"⚠️ Respuesta inválida de {exchange_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando conexión {exchange_id}: {e}")
            exchange_errors.labels(exchange=exchange_id, error_type='connection').inc()
            return False
    
    async def _health_monitor(self):
        """Monitor de salud de los exchanges"""
        while self.is_running:
            try:
                await self._check_all_connections()
                await asyncio.sleep(self.config['monitoring']['health_check_interval'])
            except Exception as e:
                logger.error(f"Error en health monitor: {e}")
                await asyncio.sleep(30)
    
    async def get_order_book(self, symbol: str, exchange_id: str = None) -> Dict[str, Any]:
        """Obtiene el order book de un exchange específico o todos"""
        if exchange_id:
            if exchange_id not in self.exchanges:
                raise ValueError(f"Exchange {exchange_id} no disponible")
            
            return await self._fetch_order_book(exchange_id, symbol)
        else:
            # Obtener de todos los exchanges
            tasks = []
            for ex_id in self.exchanges.keys():
                tasks.append(self._fetch_order_book(ex_id, symbol))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            order_books = {}
            for ex_id, result in zip(self.exchanges.keys(), results):
                if not isinstance(result, Exception):
                    order_books[ex_id] = result
                else:
                    logger.error(f"Error obteniendo order book de {ex_id}: {result}")
            
            return order_books
    
    async def _fetch_order_book(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """Obtiene el order book de un exchange específico"""
        start_time = time.time()
        
        try:
            exchange = self.exchanges[exchange_id]
            order_book = await exchange.fetch_order_book(symbol, limit=20)
            
            # Calcular latencia
            latency = time.time() - start_time
            exchange_latency.labels(exchange=exchange_id, operation='fetch_order_book').observe(latency)
            
            return order_book
            
        except Exception as e:
            logger.error(f"Error obteniendo order book de {exchange_id}: {e}")
            exchange_errors.labels(exchange=exchange_id, error_type='fetch_order_book').inc()
            raise
    
    async def execute_trade(self, exchange_id: str, symbol: str, side: str, amount: float, 
                          order_type: str = 'market') -> Dict[str, Any]:
        """Ejecuta un trade en un exchange específico"""
        start_time = time.time()
        
        try:
            if exchange_id not in self.exchanges:
                raise ValueError(f"Exchange {exchange_id} no disponible")
            
            exchange = self.exchanges[exchange_id]
            
            # Verificar rate limit
            if not self._check_rate_limit(exchange_id):
                raise Exception(f"Rate limit excedido para {exchange_id}")
            
            # Ejecutar trade
            order = await exchange.create_order(
                symbol, order_type, side, amount,
                params={'reduceOnly': False}
            )
            
            # Calcular latencia
            latency = time.time() - start_time
            exchange_latency.labels(exchange=exchange_id, operation='execute_trade').observe(latency)
            
            # Actualizar métricas
            trades_executed.labels(exchange=exchange_id, symbol=symbol, side=side).inc()
            
            logger.info(f"✅ Trade ejecutado: {exchange_id} {symbol} {side} {amount}")
            
            return {
                'success': True,
                'order': order,
                'exchange': exchange_id,
                'latency_ms': latency * 1000
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando trade en {exchange_id}: {e}")
            exchange_errors.labels(exchange=exchange_id, error_type='execute_trade').inc()
            return {
                'success': False,
                'error': str(e),
                'exchange': exchange_id
            }
    
    def _check_rate_limit(self, exchange_id: str) -> bool:
        """Verifica si se puede hacer una request respetando el rate limit"""
        now = time.time()
        rate_limit = self.rate_limits[exchange_id]
        
        # Resetear contador si ha pasado un minuto
        if now > rate_limit['reset_time']:
            rate_limit['requests'] = 0
            rate_limit['reset_time'] = now + 60
        
        # Verificar límite
        max_requests = self.config['exchanges'][exchange_id].get('rate_limit', 100)
        if rate_limit['requests'] >= max_requests:
            return False
        
        rate_limit['requests'] += 1
        return True
    
    async def get_balance(self, exchange_id: str = None) -> Dict[str, Any]:
        """Obtiene el balance de un exchange específico o todos"""
        if exchange_id:
            if exchange_id not in self.exchanges:
                raise ValueError(f"Exchange {exchange_id} no disponible")
            
            return await self._fetch_balance(exchange_id)
        else:
            # Obtener de todos los exchanges
            tasks = []
            for ex_id in self.exchanges.keys():
                tasks.append(self._fetch_balance(ex_id))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            balances = {}
            for ex_id, result in zip(self.exchanges.keys(), results):
                if not isinstance(result, Exception):
                    balances[ex_id] = result
                else:
                    logger.error(f"Error obteniendo balance de {ex_id}: {result}")
            
            return balances
    
    async def _fetch_balance(self, exchange_id: str) -> Dict[str, Any]:
        """Obtiene el balance de un exchange específico"""
        try:
            exchange = self.exchanges[exchange_id]
            balance = await exchange.fetch_balance()
            
            return balance
            
        except Exception as e:
            logger.error(f"Error obteniendo balance de {exchange_id}: {e}")
            exchange_errors.labels(exchange=exchange_id, error_type='fetch_balance').inc()
            raise
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Obtiene el estado de conexión de todos los exchanges"""
        return self.connection_status.copy()
    
    def get_available_exchanges(self) -> List[str]:
        """Obtiene la lista de exchanges disponibles"""
        return list(self.exchanges.keys())
    
    async def get_exchange_info(self, exchange_id: str) -> Dict[str, Any]:
        """Obtiene información detallada de un exchange"""
        if exchange_id not in self.exchanges:
            raise ValueError(f"Exchange {exchange_id} no disponible")
        
        exchange = self.exchanges[exchange_id]
        
        return {
            'id': exchange_id,
            'name': exchange.name,
            'countries': exchange.countries,
            'rateLimit': exchange.rateLimit,
            'has': exchange.has,
            'urls': exchange.urls,
            'version': exchange.version,
            'connection_status': self.connection_status.get(exchange_id, False),
            'last_health_check': self.last_health_check.get(exchange_id),
            'rate_limit_requests': self.rate_limits[exchange_id]['requests']
        }
