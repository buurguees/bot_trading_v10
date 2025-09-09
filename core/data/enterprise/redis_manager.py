# Ruta: core/data/enterprise/redis_manager.py
# redis_manager.py - Gestor Redis para datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\redis_manager.py

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict

import redis.asyncio as redis
from redis.asyncio import Redis

from config.enterprise_config import get_enterprise_config
from .stream_collector import MarketTick

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisDataManager:
    """Gestor Redis para datos enterprise"""
    
    def __init__(self):
        """Inicializar el gestor Redis"""
        self.config = get_enterprise_config()
        self.redis_config = self.config.get_redis_config()
        
        # Configuración de conexión
        self.host = self.redis_config.get("host", "localhost")
        self.port = self.redis_config.get("port", 6379)
        self.password = self.redis_config.get("password", "")
        self.db = self.redis_config.get("db", 0)
        self.max_connections = self.redis_config.get("max_connections", 20)
        self.socket_timeout = self.redis_config.get("socket_timeout", 30)
        self.socket_connect_timeout = self.redis_config.get("socket_connect_timeout", 30)
        self.health_check_interval = self.redis_config.get("health_check_interval", 30)
        self.decode_responses = self.redis_config.get("decode_responses", True)
        
        # Configuración de TTL
        self.ttl_config = self.redis_config.get("ttl_config", {})
        
        # Cliente Redis
        self.redis_client: Optional[Redis] = None
        self.is_running = False
        
        # Métricas
        self.metrics = {
            "operations_total": 0,
            "operations_successful": 0,
            "operations_failed": 0,
            "bytes_stored_total": 0,
            "keys_created_total": 0,
            "keys_expired_total": 0,
            "last_operation_time": None,
            "errors_total": 0
        }
        
        logger.info("RedisDataManager inicializado")
    
    async def start(self):
        """Iniciar el gestor Redis"""
        try:
            logger.info("Iniciando RedisDataManager...")
            
            # Configuración de conexión
            connection_config = {
                'host': self.host,
                'port': self.port,
                'db': self.db,
                'password': self.password if self.password else None,
                'max_connections': self.max_connections,
                'socket_timeout': self.socket_timeout,
                'socket_connect_timeout': self.socket_connect_timeout,
                'decode_responses': self.decode_responses,
                'retry_on_timeout': True,
                'retry_on_error': [redis.ConnectionError, redis.TimeoutError]
            }
            
            # Crear cliente Redis
            self.redis_client = redis.Redis(**connection_config)
            self.is_running = True
            
            # Verificar conexión
            await self.redis_client.ping()
            
            logger.info(f"RedisDataManager iniciado - Host: {self.host}:{self.port}, DB: {self.db}")
            
        except Exception as e:
            logger.error(f"Error iniciando RedisDataManager: {e}")
            raise
    
    async def stop(self):
        """Detener el gestor Redis"""
        try:
            logger.info("Deteniendo RedisDataManager...")
            self.is_running = False
            
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
            
            logger.info("RedisDataManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo RedisDataManager: {e}")
    
    def _get_key(self, key_type: str, symbol: str, additional: str = "") -> str:
        """Generar clave Redis"""
        timestamp = datetime.now().strftime("%Y%m%d%H")
        if additional:
            return f"trading_bot:{key_type}:{symbol}:{additional}:{timestamp}"
        return f"trading_bot:{key_type}:{symbol}:{timestamp}"
    
    def _get_ttl(self, key_type: str) -> int:
        """Obtener TTL para un tipo de clave"""
        return self.ttl_config.get(key_type, 3600)  # 1 hora por defecto
    
    async def store_tick(self, tick: MarketTick):
        """Almacenar tick de mercado en Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return
            
            # Generar clave
            key = self._get_key("market_ticks", tick.symbol)
            
            # Convertir tick a diccionario
            tick_data = asdict(tick)
            tick_data["timestamp"] = tick.timestamp.isoformat()
            
            # Almacenar en Redis
            await self.redis_client.lpush(key, json.dumps(tick_data, default=str))
            
            # Establecer TTL
            ttl = self._get_ttl("market_ticks")
            await self.redis_client.expire(key, ttl)
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["bytes_stored_total"] += len(json.dumps(tick_data, default=str))
            self.metrics["keys_created_total"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Tick almacenado en Redis: {tick.symbol}")
            
        except Exception as e:
            logger.error(f"Error almacenando tick {tick.symbol}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def get_latest_ticks(self, symbol: str, count: int = 100) -> List[Dict[str, Any]]:
        """Obtener los últimos ticks de un símbolo"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return []
            
            # Generar clave
            key = self._get_key("market_ticks", symbol)
            
            # Obtener ticks
            ticks_data = await self.redis_client.lrange(key, 0, count - 1)
            
            # Deserializar
            ticks = []
            for tick_data in ticks_data:
                try:
                    tick = json.loads(tick_data)
                    ticks.append(tick)
                except json.JSONDecodeError:
                    continue
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            return ticks
            
        except Exception as e:
            logger.error(f"Error obteniendo ticks {symbol}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
            return []
    
    async def store_processed_features(self, symbol: str, timeframe: str, features: Dict[str, Any]):
        """Almacenar features procesados en Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return
            
            # Generar clave
            key = self._get_key("processed_features", symbol, timeframe)
            
            # Agregar timestamp
            features_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "features": features
            }
            
            # Almacenar en Redis
            await self.redis_client.set(key, json.dumps(features_data, default=str))
            
            # Establecer TTL
            ttl = self._get_ttl("processed_features")
            await self.redis_client.expire(key, ttl)
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["bytes_stored_total"] += len(json.dumps(features_data, default=str))
            self.metrics["keys_created_total"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Features procesados almacenados: {symbol}_{timeframe}")
            
        except Exception as e:
            logger.error(f"Error almacenando features {symbol}_{timeframe}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def get_processed_features(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Obtener features procesados de Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return None
            
            # Generar clave
            key = self._get_key("processed_features", symbol, timeframe)
            
            # Obtener datos
            features_data = await self.redis_client.get(key)
            
            if features_data:
                features = json.loads(features_data)
                
                # Actualizar métricas
                self.metrics["operations_total"] += 1
                self.metrics["operations_successful"] += 1
                self.metrics["last_operation_time"] = datetime.now(timezone.utc)
                
                return features
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo features {symbol}_{timeframe}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
            return None
    
    async def store_model_prediction(self, symbol: str, model_name: str, prediction: Dict[str, Any]):
        """Almacenar predicción del modelo en Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return
            
            # Generar clave
            key = self._get_key("model_predictions", symbol, model_name)
            
            # Agregar timestamp
            prediction_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "model_name": model_name,
                "prediction": prediction
            }
            
            # Almacenar en Redis
            await self.redis_client.set(key, json.dumps(prediction_data, default=str))
            
            # Establecer TTL
            ttl = self._get_ttl("model_predictions")
            await self.redis_client.expire(key, ttl)
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["bytes_stored_total"] += len(json.dumps(prediction_data, default=str))
            self.metrics["keys_created_total"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Predicción almacenada: {symbol}_{model_name}")
            
        except Exception as e:
            logger.error(f"Error almacenando predicción {symbol}_{model_name}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def get_model_prediction(self, symbol: str, model_name: str) -> Optional[Dict[str, Any]]:
        """Obtener predicción del modelo de Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return None
            
            # Generar clave
            key = self._get_key("model_predictions", symbol, model_name)
            
            # Obtener datos
            prediction_data = await self.redis_client.get(key)
            
            if prediction_data:
                prediction = json.loads(prediction_data)
                
                # Actualizar métricas
                self.metrics["operations_total"] += 1
                self.metrics["operations_successful"] += 1
                self.metrics["last_operation_time"] = datetime.now(timezone.utc)
                
                return prediction
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo predicción {symbol}_{model_name}: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
            return None
    
    async def store_account_balance(self, balance: Dict[str, Any]):
        """Almacenar balance de cuenta en Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return
            
            # Generar clave
            key = "trading_bot:account_balance:current"
            
            # Agregar timestamp
            balance_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "balance": balance
            }
            
            # Almacenar en Redis
            await self.redis_client.set(key, json.dumps(balance_data, default=str))
            
            # Establecer TTL
            ttl = self._get_ttl("account_balance")
            await self.redis_client.expire(key, ttl)
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["bytes_stored_total"] += len(json.dumps(balance_data, default=str))
            self.metrics["keys_created_total"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            logger.debug("Balance de cuenta almacenado")
            
        except Exception as e:
            logger.error(f"Error almacenando balance de cuenta: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Obtener balance de cuenta de Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return None
            
            # Generar clave
            key = "trading_bot:account_balance:current"
            
            # Obtener datos
            balance_data = await self.redis_client.get(key)
            
            if balance_data:
                balance = json.loads(balance_data)
                
                # Actualizar métricas
                self.metrics["operations_total"] += 1
                self.metrics["operations_successful"] += 1
                self.metrics["last_operation_time"] = datetime.now(timezone.utc)
                
                return balance
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo balance de cuenta: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
            return None
    
    async def store_open_positions(self, positions: List[Dict[str, Any]]):
        """Almacenar posiciones abiertas en Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return
            
            # Generar clave
            key = "trading_bot:open_positions:current"
            
            # Agregar timestamp
            positions_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "positions": positions
            }
            
            # Almacenar en Redis
            await self.redis_client.set(key, json.dumps(positions_data, default=str))
            
            # Establecer TTL
            ttl = self._get_ttl("open_positions")
            await self.redis_client.expire(key, ttl)
            
            # Actualizar métricas
            self.metrics["operations_total"] += 1
            self.metrics["operations_successful"] += 1
            self.metrics["bytes_stored_total"] += len(json.dumps(positions_data, default=str))
            self.metrics["keys_created_total"] += 1
            self.metrics["last_operation_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Posiciones abiertas almacenadas: {len(positions)}")
            
        except Exception as e:
            logger.error(f"Error almacenando posiciones abiertas: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
    
    async def get_open_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Obtener posiciones abiertas de Redis"""
        try:
            if not self.redis_client or not self.is_running:
                logger.warning("Cliente Redis no está disponible")
                return None
            
            # Generar clave
            key = "trading_bot:open_positions:current"
            
            # Obtener datos
            positions_data = await self.redis_client.get(key)
            
            if positions_data:
                positions = json.loads(positions_data)
                
                # Actualizar métricas
                self.metrics["operations_total"] += 1
                self.metrics["operations_successful"] += 1
                self.metrics["last_operation_time"] = datetime.now(timezone.utc)
                
                return positions.get("positions", [])
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones abiertas: {e}")
            self.metrics["operations_failed"] += 1
            self.metrics["errors_total"] += 1
            return None
    
    async def cleanup_expired_keys(self):
        """Limpiar claves expiradas"""
        try:
            if not self.redis_client or not self.is_running:
                return
            
            # Obtener todas las claves del patrón
            pattern = "trading_bot:*"
            keys = await self.redis_client.keys(pattern)
            
            expired_count = 0
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # Clave sin TTL
                    await self.redis_client.expire(key, 3600)  # Establecer TTL de 1 hora
                elif ttl == -2:  # Clave expirada
                    await self.redis_client.delete(key)
                    expired_count += 1
            
            self.metrics["keys_expired_total"] += expired_count
            logger.info(f"Limpieza completada: {expired_count} claves expiradas eliminadas")
            
        except Exception as e:
            logger.error(f"Error en limpieza de claves: {e}")
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del gestor Redis"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del gestor Redis"""
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "max_connections": self.max_connections,
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del gestor Redis"""
        try:
            if not self.redis_client or not self.is_running:
                return False
            
            # Verificar conexión
            await self.redis_client.ping()
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear gestor
def create_redis_manager() -> RedisDataManager:
    """Crear instancia del gestor Redis"""
    return RedisDataManager()

if __name__ == "__main__":
    # Test del gestor Redis
    async def test_redis_manager():
        manager = RedisDataManager()
        try:
            await manager.start()
            
            # Test de health check
            health = await manager.health_check()
            print(f"Health check: {health}")
            
            # Test de almacenamiento de tick
            from .stream_collector import MarketTick
            tick = MarketTick(
                timestamp=datetime.now(timezone.utc),
                symbol="BTCUSDT",
                price=50000.0,
                volume=1.5
            )
            
            await manager.store_tick(tick)
            
            # Test de obtención de ticks
            ticks = await manager.get_latest_ticks("BTCUSDT", 10)
            print(f"Ticks obtenidos: {len(ticks)}")
            
            # Mostrar métricas
            print("=== MÉTRICAS DEL GESTOR REDIS ===")
            metrics = manager.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await manager.stop()
    
    # Ejecutar test
    asyncio.run(test_redis_manager())
