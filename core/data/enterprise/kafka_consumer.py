# kafka_consumer.py - Consumidor Kafka para datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\kafka_consumer.py

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from config.enterprise_config import get_enterprise_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConsumerMessage:
    """Estructura de mensaje del consumidor"""
    topic: str
    partition: int
    offset: int
    key: str
    value: Dict[str, Any]
    timestamp: datetime
    headers: Optional[Dict] = None

class KafkaDataConsumer:
    """Consumidor Kafka para datos enterprise"""
    
    def __init__(self, group_id: Optional[str] = None):
        """Inicializar el consumidor Kafka"""
        self.config = get_enterprise_config()
        self.kafka_config = self.config.get_kafka_config()
        
        # Configuración del consumidor
        self.bootstrap_servers = self.kafka_config.get("bootstrap_servers", "localhost:9092")
        self.consumer_config = self.kafka_config.get("consumer", {})
        self.group_id = group_id or self.consumer_config.get("group_id", "trading_bot_consumer")
        
        # Configuración de topics
        self.topics = self.kafka_config.get("topics", {})
        self.market_ticks_topic = self.topics.get("market_ticks", {}).get("name", "market_ticks")
        self.processed_data_topic = self.topics.get("processed_data", {}).get("name", "processed_data")
        self.alerts_topic = self.topics.get("alerts", {}).get("name", "alerts")
        
        # Consumidor Kafka
        self.consumer: Optional[KafkaConsumer] = None
        self.is_running = False
        
        # Callbacks para procesamiento de mensajes
        self.message_handlers: Dict[str, Callable] = {}
        
        # Métricas
        self.metrics = {
            "messages_consumed_total": 0,
            "messages_processed_total": 0,
            "messages_failed_total": 0,
            "bytes_consumed_total": 0,
            "last_consume_time": None,
            "errors_total": 0,
            "processing_latency_seconds": []
        }
        
        logger.info(f"KafkaDataConsumer inicializado - Group ID: {self.group_id}")
    
    async def start(self):
        """Iniciar el consumidor Kafka"""
        try:
            logger.info("Iniciando KafkaDataConsumer...")
            
            # Configuración del consumidor
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.group_id,
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'key_deserializer': lambda m: m.decode('utf-8') if m else None,
                'auto_offset_reset': self.consumer_config.get("auto_offset_reset", "latest"),
                'enable_auto_commit': self.consumer_config.get("enable_auto_commit", True),
                'auto_commit_interval_ms': self.consumer_config.get("auto_commit_interval_ms", 5000),
                'session_timeout_ms': 30000,
                'heartbeat_interval_ms': 10000,
                'max_poll_records': 500,
                'fetch_min_bytes': 1,
                'fetch_max_wait_ms': 500,
                'request_timeout_ms': 30000,
                'retry_backoff_ms': 100,
                'reconnect_backoff_ms': 50,
                'reconnect_backoff_max_ms': 1000
            }
            
            # Crear consumidor
            self.consumer = KafkaConsumer(**consumer_config)
            self.is_running = True
            
            logger.info(f"KafkaDataConsumer iniciado - Servers: {self.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Error iniciando KafkaDataConsumer: {e}")
            raise
    
    async def stop(self):
        """Detener el consumidor Kafka"""
        try:
            logger.info("Deteniendo KafkaDataConsumer...")
            self.is_running = False
            
            if self.consumer:
                self.consumer.close()
                self.consumer = None
            
            logger.info("KafkaDataConsumer detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo KafkaDataConsumer: {e}")
    
    def register_handler(self, topic: str, handler: Callable[[ConsumerMessage], None]):
        """Registrar handler para un topic específico"""
        self.message_handlers[topic] = handler
        logger.info(f"Handler registrado para topic: {topic}")
    
    async def subscribe(self, topics: List[str]):
        """Suscribirse a topics específicos"""
        try:
            if not self.consumer or not self.is_running:
                logger.warning("Consumidor Kafka no está disponible")
                return
            
            self.consumer.subscribe(topics)
            logger.info(f"Suscrito a topics: {topics}")
            
        except Exception as e:
            logger.error(f"Error suscribiéndose a topics {topics}: {e}")
            raise
    
    async def consume_loop(self):
        """Loop principal de consumo de mensajes"""
        try:
            if not self.consumer or not self.is_running:
                logger.warning("Consumidor Kafka no está disponible")
                return
            
            logger.info("Iniciando loop de consumo...")
            
            while self.is_running:
                try:
                    # Poll mensajes
                    message_batch = self.consumer.poll(timeout_ms=1000)
                    
                    if message_batch:
                        await self._process_message_batch(message_batch)
                    
                except Exception as e:
                    logger.error(f"Error en loop de consumo: {e}")
                    self.metrics["errors_total"] += 1
                    await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en loop de consumo: {e}")
            raise
    
    async def _process_message_batch(self, message_batch: Dict):
        """Procesar lote de mensajes"""
        try:
            for topic_partition, messages in message_batch.items():
                topic = topic_partition.topic
                
                for message in messages:
                    await self._process_message(message, topic)
                    
        except Exception as e:
            logger.error(f"Error procesando lote de mensajes: {e}")
            self.metrics["errors_total"] += 1
    
    async def _process_message(self, message, topic: str):
        """Procesar mensaje individual"""
        try:
            start_time = time.time()
            
            # Crear objeto ConsumerMessage
            consumer_message = ConsumerMessage(
                topic=topic,
                partition=message.partition,
                offset=message.offset,
                key=message.key,
                value=message.value,
                timestamp=datetime.fromtimestamp(message.timestamp / 1000, tz=timezone.utc),
                headers=message.headers
            )
            
            # Actualizar métricas
            self.metrics["messages_consumed_total"] += 1
            self.metrics["bytes_consumed_total"] += len(str(message.value))
            self.metrics["last_consume_time"] = datetime.now(timezone.utc)
            
            # Procesar mensaje
            await self._handle_message(consumer_message)
            
            # Calcular latencia de procesamiento
            processing_time = time.time() - start_time
            self.metrics["processing_latency_seconds"].append(processing_time)
            self.metrics["messages_processed_total"] += 1
            
            # Mantener solo los últimos 1000 tiempos de procesamiento
            if len(self.metrics["processing_latency_seconds"]) > 1000:
                self.metrics["processing_latency_seconds"] = self.metrics["processing_latency_seconds"][-1000:]
            
            logger.debug(f"Mensaje procesado: {topic} - Offset: {message.offset}")
            
        except Exception as e:
            logger.error(f"Error procesando mensaje {topic}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
    
    async def _handle_message(self, message: ConsumerMessage):
        """Manejar mensaje usando el handler registrado"""
        try:
            # Obtener handler para el topic
            handler = self.message_handlers.get(message.topic)
            
            if handler:
                # Ejecutar handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            else:
                # Handler por defecto
                await self._default_handler(message)
                
        except Exception as e:
            logger.error(f"Error en handler para {message.topic}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
    
    async def _default_handler(self, message: ConsumerMessage):
        """Handler por defecto para mensajes"""
        logger.info(f"Mensaje recibido en {message.topic}: {message.value}")
    
    async def consume_market_ticks(self, handler: Callable[[ConsumerMessage], None]):
        """Consumir ticks de mercado"""
        self.register_handler(self.market_ticks_topic, handler)
        await self.subscribe([self.market_ticks_topic])
        logger.info(f"Consumiendo ticks de mercado desde {self.market_ticks_topic}")
    
    async def consume_processed_data(self, handler: Callable[[ConsumerMessage], None]):
        """Consumir datos procesados"""
        self.register_handler(self.processed_data_topic, handler)
        await self.subscribe([self.processed_data_topic])
        logger.info(f"Consumiendo datos procesados desde {self.processed_data_topic}")
    
    async def consume_alerts(self, handler: Callable[[ConsumerMessage], None]):
        """Consumir alertas"""
        self.register_handler(self.alerts_topic, handler)
        await self.subscribe([self.alerts_topic])
        logger.info(f"Consumiendo alertas desde {self.alerts_topic}")
    
    async def consume_all_topics(self, handlers: Dict[str, Callable[[ConsumerMessage], None]]):
        """Consumir todos los topics con handlers específicos"""
        topics = []
        
        for topic, handler in handlers.items():
            self.register_handler(topic, handler)
            topics.append(topic)
        
        await self.subscribe(topics)
        logger.info(f"Consumiendo todos los topics: {topics}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del consumidor"""
        metrics = self.metrics.copy()
        
        # Calcular métricas adicionales
        if metrics["processing_latency_seconds"]:
            import numpy as np
            metrics["avg_processing_latency"] = np.mean(metrics["processing_latency_seconds"])
            metrics["p95_processing_latency"] = np.percentile(metrics["processing_latency_seconds"], 95)
            metrics["p99_processing_latency"] = np.percentile(metrics["processing_latency_seconds"], 99)
        
        return metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del consumidor"""
        return {
            "is_running": self.is_running,
            "group_id": self.group_id,
            "bootstrap_servers": self.bootstrap_servers,
            "topics": {
                "market_ticks": self.market_ticks_topic,
                "processed_data": self.processed_data_topic,
                "alerts": self.alerts_topic
            },
            "registered_handlers": list(self.message_handlers.keys()),
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del consumidor"""
        try:
            if not self.consumer or not self.is_running:
                return False
            
            # Verificar que el consumidor esté suscrito a topics
            subscription = self.consumer.subscription()
            return len(subscription) > 0
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear consumidor
def create_kafka_consumer(group_id: Optional[str] = None) -> KafkaDataConsumer:
    """Crear instancia del consumidor Kafka"""
    return KafkaDataConsumer(group_id)

if __name__ == "__main__":
    # Test del consumidor
    async def test_consumer():
        consumer = KafkaDataConsumer("test_group")
        
        # Handler para ticks de mercado
        async def market_tick_handler(message: ConsumerMessage):
            print(f"Tick recibido: {message.value}")
        
        # Handler para alertas
        async def alert_handler(message: ConsumerMessage):
            print(f"Alerta recibida: {message.value}")
        
        try:
            await consumer.start()
            
            # Registrar handlers
            consumer.register_handler(consumer.market_ticks_topic, market_tick_handler)
            consumer.register_handler(consumer.alerts_topic, alert_handler)
            
            # Suscribirse a topics
            await consumer.subscribe([consumer.market_ticks_topic, consumer.alerts_topic])
            
            # Iniciar consumo
            await consumer.consume_loop()
            
        finally:
            await consumer.stop()
    
    # Ejecutar test
    asyncio.run(test_consumer())
