# Ruta: core/data/enterprise/kafka_producer.py
# kafka_producer.py - Productor Kafka para datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\kafka_producer.py

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from kafka import KafkaProducer
from kafka.errors import KafkaError

from core.config.unified_config import unified_config
from .stream_collector import MarketTick

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaDataProducer:
    """Productor Kafka para datos enterprise"""
    
    def __init__(self):
        """Inicializar el productor Kafka"""
        self.config = get_enterprise_config()
        self.kafka_config = self.config.get_kafka_config()
        
        # Configuración del productor
        self.bootstrap_servers = self.kafka_config.get("bootstrap_servers", "localhost:9092")
        self.producer_config = self.kafka_config.get("producer", {})
        
        # Configuración de topics
        self.topics = self.kafka_config.get("topics", {})
        self.market_ticks_topic = self.topics.get("market_ticks", {}).get("name", "market_ticks")
        self.processed_data_topic = self.topics.get("processed_data", {}).get("name", "processed_data")
        self.alerts_topic = self.topics.get("alerts", {}).get("name", "alerts")
        
        # Productor Kafka
        self.producer: Optional[KafkaProducer] = None
        self.is_running = False
        
        # Métricas
        self.metrics = {
            "messages_sent_total": 0,
            "messages_failed_total": 0,
            "bytes_sent_total": 0,
            "last_send_time": None,
            "errors_total": 0
        }
        
        logger.info("KafkaDataProducer inicializado")
    
    async def start(self):
        """Iniciar el productor Kafka"""
        try:
            logger.info("Iniciando KafkaDataProducer...")
            
            # Configuración del productor
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v, default=self._json_serializer).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None,
                'batch_size': self.producer_config.get("batch_size", 16384),
                'linger_ms': self.producer_config.get("linger_ms", 10),
                'compression_type': self.producer_config.get("compression_type", "gzip"),
                'max_request_size': self.producer_config.get("max_request_size", 1048576),
                'retries': 3,
                'retry_backoff_ms': 100,
                'request_timeout_ms': 30000,
                'metadata_max_age_ms': 300000,
                'connections_max_idle_ms': 540000,
                'reconnect_backoff_ms': 50,
                'reconnect_backoff_max_ms': 1000
            }
            
            # Crear productor
            self.producer = KafkaProducer(**producer_config)
            self.is_running = True
            
            logger.info(f"KafkaDataProducer iniciado - Servers: {self.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Error iniciando KafkaDataProducer: {e}")
            raise
    
    async def stop(self):
        """Detener el productor Kafka"""
        try:
            logger.info("Deteniendo KafkaDataProducer...")
            self.is_running = False
            
            if self.producer:
                # Flush mensajes pendientes
                self.producer.flush(timeout=10)
                
                # Cerrar productor
                self.producer.close(timeout=10)
                self.producer = None
            
            logger.info("KafkaDataProducer detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo KafkaDataProducer: {e}")
    
    def _json_serializer(self, obj):
        """Serializador JSON personalizado para datetime"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def send_tick(self, tick: MarketTick):
        """Enviar tick de mercado a Kafka"""
        try:
            if not self.producer or not self.is_running:
                logger.warning("Productor Kafka no está disponible")
                return
            
            # Convertir tick a diccionario
            tick_data = asdict(tick)
            
            # Crear clave para particionado
            key = f"{tick.symbol}_{tick.timestamp.strftime('%Y%m%d%H')}"
            
            # Enviar mensaje
            future = self.producer.send(
                self.market_ticks_topic,
                key=key,
                value=tick_data
            )
            
            # Esperar confirmación
            record_metadata = future.get(timeout=10)
            
            # Actualizar métricas
            self.metrics["messages_sent_total"] += 1
            self.metrics["bytes_sent_total"] += len(json.dumps(tick_data, default=self._json_serializer))
            self.metrics["last_send_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Tick enviado: {tick.symbol} - Partición: {record_metadata.partition}, Offset: {record_metadata.offset}")
            
        except KafkaError as e:
            logger.error(f"Error Kafka enviando tick {tick.symbol}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
            
        except Exception as e:
            logger.error(f"Error enviando tick {tick.symbol}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
    
    async def send_processed_data(self, data: Dict[str, Any], symbol: str, timeframe: str):
        """Enviar datos procesados a Kafka"""
        try:
            if not self.producer or not self.is_running:
                logger.warning("Productor Kafka no está disponible")
                return
            
            # Agregar metadatos
            processed_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "data": data
            }
            
            # Crear clave para particionado
            key = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d%H')}"
            
            # Enviar mensaje
            future = self.producer.send(
                self.processed_data_topic,
                key=key,
                value=processed_data
            )
            
            # Esperar confirmación
            record_metadata = future.get(timeout=10)
            
            # Actualizar métricas
            self.metrics["messages_sent_total"] += 1
            self.metrics["bytes_sent_total"] += len(json.dumps(processed_data, default=self._json_serializer))
            self.metrics["last_send_time"] = datetime.now(timezone.utc)
            
            logger.debug(f"Datos procesados enviados: {symbol}_{timeframe} - Partición: {record_metadata.partition}")
            
        except KafkaError as e:
            logger.error(f"Error Kafka enviando datos procesados {symbol}_{timeframe}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
            
        except Exception as e:
            logger.error(f"Error enviando datos procesados {symbol}_{timeframe}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
    
    async def send_alert(self, alert_type: str, message: str, severity: str = "info", metadata: Optional[Dict] = None):
        """Enviar alerta a Kafka"""
        try:
            if not self.producer or not self.is_running:
                logger.warning("Productor Kafka no está disponible")
                return
            
            # Crear alerta
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "metadata": metadata or {}
            }
            
            # Crear clave para particionado
            key = f"{alert_type}_{datetime.now().strftime('%Y%m%d%H')}"
            
            # Enviar mensaje
            future = self.producer.send(
                self.alerts_topic,
                key=key,
                value=alert
            )
            
            # Esperar confirmación
            record_metadata = future.get(timeout=10)
            
            # Actualizar métricas
            self.metrics["messages_sent_total"] += 1
            self.metrics["bytes_sent_total"] += len(json.dumps(alert, default=self._json_serializer))
            self.metrics["last_send_time"] = datetime.now(timezone.utc)
            
            logger.info(f"Alerta enviada: {alert_type} - {message}")
            
        except KafkaError as e:
            logger.error(f"Error Kafka enviando alerta {alert_type}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
            
        except Exception as e:
            logger.error(f"Error enviando alerta {alert_type}: {e}")
            self.metrics["messages_failed_total"] += 1
            self.metrics["errors_total"] += 1
    
    async def send_batch(self, messages: List[Dict[str, Any]], topic: str):
        """Enviar lote de mensajes a Kafka"""
        try:
            if not self.producer or not self.is_running:
                logger.warning("Productor Kafka no está disponible")
                return
            
            if not messages:
                return
            
            # Enviar mensajes en lote
            futures = []
            for message in messages:
                key = message.get("key", f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}")
                future = self.producer.send(topic, key=key, value=message)
                futures.append(future)
            
            # Esperar confirmaciones
            for future in futures:
                try:
                    record_metadata = future.get(timeout=10)
                    self.metrics["messages_sent_total"] += 1
                except Exception as e:
                    logger.error(f"Error en mensaje del lote: {e}")
                    self.metrics["messages_failed_total"] += 1
            
            # Actualizar métricas
            self.metrics["last_send_time"] = datetime.now(timezone.utc)
            
            logger.info(f"Lote de {len(messages)} mensajes enviado a {topic}")
            
        except Exception as e:
            logger.error(f"Error enviando lote a {topic}: {e}")
            self.metrics["messages_failed_total"] += len(messages)
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del productor"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del productor"""
        return {
            "is_running": self.is_running,
            "bootstrap_servers": self.bootstrap_servers,
            "topics": {
                "market_ticks": self.market_ticks_topic,
                "processed_data": self.processed_data_topic,
                "alerts": self.alerts_topic
            },
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del productor"""
        try:
            if not self.producer or not self.is_running:
                return False
            
            # Verificar conexión enviando un mensaje de prueba
            test_message = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "health_check",
                "message": "Kafka producer health check"
            }
            
            future = self.producer.send(
                self.alerts_topic,
                key="health_check",
                value=test_message
            )
            
            # Esperar confirmación con timeout corto
            record_metadata = future.get(timeout=5)
            
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear productor
def create_kafka_producer() -> KafkaDataProducer:
    """Crear instancia del productor Kafka"""
    return KafkaDataProducer()

if __name__ == "__main__":
    # Test del productor
    async def test_producer():
        producer = KafkaDataProducer()
        try:
            await producer.start()
            
            # Test de health check
            health = await producer.health_check()
            print(f"Health check: {health}")
            
            # Test de envío de alerta
            await producer.send_alert(
                "test",
                "Mensaje de prueba del productor Kafka",
                "info",
                {"test": True}
            )
            
            # Mostrar métricas
            print("=== MÉTRICAS DEL PRODUCTOR ===")
            metrics = producer.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await producer.stop()
    
    # Ejecutar test
    asyncio.run(test_producer())
