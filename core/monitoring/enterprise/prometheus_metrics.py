# Ruta: core/monitoring/enterprise/prometheus_metrics.py
# prometheus_metrics.py - Métricas de Prometheus enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\prometheus_metrics.py

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    start_http_server, generate_latest, REGISTRY
)

from core.config.unified_config import unified_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricConfig:
    """Configuración de métrica"""
    name: str
    description: str
    metric_type: str
    labels: List[str] = None
    buckets: List[float] = None

class PrometheusMetrics:
    """Gestor de métricas de Prometheus enterprise"""
    
    def __init__(self, port: int = 8000):
        """Inicializar el gestor de métricas"""
        self.config = get_enterprise_config()
        self.monitoring_config = self.config.get_monitoring_config()
        self.metrics_config = self.monitoring_config.get("metrics", {})
        
        # Puerto del servidor de métricas
        self.port = port
        self.server_started = False
        
        # Configuración de métricas
        self.data_collection_metrics = self.metrics_config.get("data_collection", [])
        self.ml_training_metrics = self.metrics_config.get("ml_training", [])
        self.trading_metrics = self.metrics_config.get("trading", [])
        self.system_metrics = self.metrics_config.get("system", [])
        
        # Métricas de Prometheus
        self._create_metrics()
        
        # Métricas internas
        self.internal_metrics = {
            "metrics_created_total": 0,
            "metrics_updated_total": 0,
            "server_started": False,
            "last_update_time": None
        }
        
        logger.info("PrometheusMetrics inicializado")
    
    def _create_metrics(self):
        """Crear métricas de Prometheus"""
        try:
            # Métricas de data collection
            self.ticks_received_total = Counter(
                'ticks_received_total',
                'Total de ticks recibidos',
                ['symbol', 'source']
            )
            
            self.ticks_processed_total = Counter(
                'ticks_processed_total',
                'Total de ticks procesados',
                ['symbol', 'status']
            )
            
            self.ticks_dropped_total = Counter(
                'ticks_dropped_total',
                'Total de ticks descartados',
                ['symbol', 'reason']
            )
            
            self.processing_latency_seconds = Histogram(
                'processing_latency_seconds',
                'Latencia de procesamiento de ticks',
                ['symbol', 'operation'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
            )
            
            self.websocket_connections_active = Gauge(
                'websocket_connections_active',
                'Conexiones WebSocket activas',
                ['exchange', 'symbol']
            )
            
            self.kafka_messages_sent_total = Counter(
                'kafka_messages_sent_total',
                'Total de mensajes enviados a Kafka',
                ['topic', 'status']
            )
            
            self.redis_operations_total = Counter(
                'redis_operations_total',
                'Total de operaciones en Redis',
                ['operation', 'status']
            )
            
            self.timescaledb_inserts_total = Counter(
                'timescaledb_inserts_total',
                'Total de inserciones en TimescaleDB',
                ['table', 'status']
            )
            
            # Métricas de ML training
            self.training_epoch_duration_seconds = Histogram(
                'training_epoch_duration_seconds',
                'Duración de epochs de entrenamiento',
                ['model_name', 'symbol'],
                buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
            )
            
            self.training_loss = Gauge(
                'training_loss',
                'Loss de entrenamiento actual',
                ['model_name', 'symbol', 'phase']
            )
            
            self.training_accuracy = Gauge(
                'training_accuracy',
                'Accuracy de entrenamiento actual',
                ['model_name', 'symbol', 'phase']
            )
            
            self.model_inference_time_seconds = Histogram(
                'model_inference_time_seconds',
                'Tiempo de inferencia del modelo',
                ['model_name', 'symbol'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
            )
            
            self.training_epochs_completed_total = Counter(
                'training_epochs_completed_total',
                'Total de epochs de entrenamiento completados',
                ['model_name', 'symbol']
            )
            
            # Métricas de trading
            self.trades_executed_total = Counter(
                'trades_executed_total',
                'Total de trades ejecutados',
                ['symbol', 'side', 'status']
            )
            
            self.account_balance_usd = Gauge(
                'account_balance_usd',
                'Balance de cuenta en USD',
                ['account_type']
            )
            
            self.open_positions_count = Gauge(
                'open_positions_count',
                'Número de posiciones abiertas',
                ['symbol', 'side']
            )
            
            self.trade_pnl_usd = Histogram(
                'trade_pnl_usd',
                'PnL de trades en USD',
                ['symbol', 'side'],
                buckets=[-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000]
            )
            
            self.order_execution_time_seconds = Histogram(
                'order_execution_time_seconds',
                'Tiempo de ejecución de órdenes',
                ['symbol', 'order_type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            )
            
            self.trade_amount_usd = Gauge(
                'trade_amount_usd',
                'Cantidad de trade en USD',
                ['symbol', 'side']
            )
            
            # Métricas de sistema
            self.cpu_usage_percent = Gauge(
                'cpu_usage_percent',
                'Uso de CPU en porcentaje',
                ['core']
            )
            
            self.memory_usage_bytes = Gauge(
                'memory_usage_bytes',
                'Uso de memoria en bytes',
                ['type']
            )
            
            self.disk_usage_bytes = Gauge(
                'disk_usage_bytes',
                'Uso de disco en bytes',
                ['mount_point', 'type']
            )
            
            self.network_io_bytes_total = Counter(
                'network_io_bytes_total',
                'Total de bytes de red',
                ['direction', 'interface']
            )
            
            # Métricas de errores
            self.errors_total = Counter(
                'errors_total',
                'Total de errores',
                ['service', 'error_type']
            )
            
            self.kafka_producer_errors_total = Counter(
                'kafka_producer_errors_total',
                'Total de errores del producer de Kafka',
                ['topic', 'error_type']
            )
            
            self.redis_operations_failed_total = Counter(
                'redis_operations_failed_total',
                'Total de operaciones fallidas en Redis',
                ['operation', 'error_type']
            )
            
            # Métricas de información del sistema
            self.system_info = Info(
                'system_info',
                'Información del sistema'
            )
            
            self.model_info = Info(
                'model_info',
                'Información del modelo'
            )
            
            # Actualizar métricas internas
            self.internal_metrics["metrics_created_total"] = len([m for m in dir(self) if not m.startswith('_')])
            
            logger.info(f"{self.internal_metrics['metrics_created_total']} métricas de Prometheus creadas")
            
        except Exception as e:
            logger.error(f"Error creando métricas de Prometheus: {e}")
            raise
    
    def start_server(self):
        """Iniciar servidor de métricas"""
        try:
            if not self.server_started:
                start_http_server(self.port)
                self.server_started = True
                self.internal_metrics["server_started"] = True
                
                logger.info(f"Servidor de métricas iniciado en puerto {self.port}")
            
        except Exception as e:
            logger.error(f"Error iniciando servidor de métricas: {e}")
            raise
    
    def stop_server(self):
        """Detener servidor de métricas"""
        try:
            # Nota: prometheus_client no proporciona una forma directa de detener el servidor
            # En un entorno de producción, se usaría un servidor web más robusto
            self.server_started = False
            self.internal_metrics["server_started"] = False
            
            logger.info("Servidor de métricas detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo servidor de métricas: {e}")
    
    def record_tick_received(self, symbol: str, source: str = "bitget"):
        """Registrar tick recibido"""
        try:
            self.ticks_received_total.labels(symbol=symbol, source=source).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando tick recibido: {e}")
    
    def record_tick_processed(self, symbol: str, status: str = "success"):
        """Registrar tick procesado"""
        try:
            self.ticks_processed_total.labels(symbol=symbol, status=status).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando tick procesado: {e}")
    
    def record_tick_dropped(self, symbol: str, reason: str = "validation_failed"):
        """Registrar tick descartado"""
        try:
            self.ticks_dropped_total.labels(symbol=symbol, reason=reason).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando tick descartado: {e}")
    
    def record_processing_latency(self, symbol: str, operation: str, latency: float):
        """Registrar latencia de procesamiento"""
        try:
            self.processing_latency_seconds.labels(symbol=symbol, operation=operation).observe(latency)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando latencia de procesamiento: {e}")
    
    def set_websocket_connections(self, exchange: str, symbol: str, count: int):
        """Establecer número de conexiones WebSocket"""
        try:
            self.websocket_connections_active.labels(exchange=exchange, symbol=symbol).set(count)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo conexiones WebSocket: {e}")
    
    def record_kafka_message_sent(self, topic: str, status: str = "success"):
        """Registrar mensaje enviado a Kafka"""
        try:
            self.kafka_messages_sent_total.labels(topic=topic, status=status).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando mensaje de Kafka: {e}")
    
    def record_redis_operation(self, operation: str, status: str = "success"):
        """Registrar operación de Redis"""
        try:
            self.redis_operations_total.labels(operation=operation, status=status).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando operación de Redis: {e}")
    
    def record_timescaledb_insert(self, table: str, status: str = "success"):
        """Registrar inserción en TimescaleDB"""
        try:
            self.timescaledb_inserts_total.labels(table=table, status=status).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando inserción en TimescaleDB: {e}")
    
    def record_training_epoch_duration(self, model_name: str, symbol: str, duration: float):
        """Registrar duración de epoch de entrenamiento"""
        try:
            self.training_epoch_duration_seconds.labels(model_name=model_name, symbol=symbol).observe(duration)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando duración de epoch: {e}")
    
    def set_training_loss(self, model_name: str, symbol: str, phase: str, loss: float):
        """Establecer loss de entrenamiento"""
        try:
            self.training_loss.labels(model_name=model_name, symbol=symbol, phase=phase).set(loss)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo loss de entrenamiento: {e}")
    
    def set_training_accuracy(self, model_name: str, symbol: str, phase: str, accuracy: float):
        """Establecer accuracy de entrenamiento"""
        try:
            self.training_accuracy.labels(model_name=model_name, symbol=symbol, phase=phase).set(accuracy)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo accuracy de entrenamiento: {e}")
    
    def record_model_inference_time(self, model_name: str, symbol: str, inference_time: float):
        """Registrar tiempo de inferencia del modelo"""
        try:
            self.model_inference_time_seconds.labels(model_name=model_name, symbol=symbol).observe(inference_time)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando tiempo de inferencia: {e}")
    
    def record_training_epoch_completed(self, model_name: str, symbol: str):
        """Registrar epoch de entrenamiento completado"""
        try:
            self.training_epochs_completed_total.labels(model_name=model_name, symbol=symbol).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando epoch completado: {e}")
    
    def record_trade_executed(self, symbol: str, side: str, status: str = "filled"):
        """Registrar trade ejecutado"""
        try:
            self.trades_executed_total.labels(symbol=symbol, side=side, status=status).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando trade ejecutado: {e}")
    
    def set_account_balance(self, account_type: str, balance: float):
        """Establecer balance de cuenta"""
        try:
            self.account_balance_usd.labels(account_type=account_type).set(balance)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo balance de cuenta: {e}")
    
    def set_open_positions_count(self, symbol: str, side: str, count: int):
        """Establecer número de posiciones abiertas"""
        try:
            self.open_positions_count.labels(symbol=symbol, side=side).set(count)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo posiciones abiertas: {e}")
    
    def record_trade_pnl(self, symbol: str, side: str, pnl: float):
        """Registrar PnL de trade"""
        try:
            self.trade_pnl_usd.labels(symbol=symbol, side=side).observe(pnl)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando PnL de trade: {e}")
    
    def record_order_execution_time(self, symbol: str, order_type: str, execution_time: float):
        """Registrar tiempo de ejecución de orden"""
        try:
            self.order_execution_time_seconds.labels(symbol=symbol, order_type=order_type).observe(execution_time)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando tiempo de ejecución: {e}")
    
    def set_trade_amount(self, symbol: str, side: str, amount: float):
        """Establecer cantidad de trade"""
        try:
            self.trade_amount_usd.labels(symbol=symbol, side=side).set(amount)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo cantidad de trade: {e}")
    
    def set_cpu_usage(self, core: str, usage_percent: float):
        """Establecer uso de CPU"""
        try:
            self.cpu_usage_percent.labels(core=core).set(usage_percent)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo uso de CPU: {e}")
    
    def set_memory_usage(self, memory_type: str, usage_bytes: int):
        """Establecer uso de memoria"""
        try:
            self.memory_usage_bytes.labels(type=memory_type).set(usage_bytes)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo uso de memoria: {e}")
    
    def set_disk_usage(self, mount_point: str, disk_type: str, usage_bytes: int):
        """Establecer uso de disco"""
        try:
            self.disk_usage_bytes.labels(mount_point=mount_point, type=disk_type).set(usage_bytes)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo uso de disco: {e}")
    
    def record_network_io(self, direction: str, interface: str, bytes_count: int):
        """Registrar I/O de red"""
        try:
            self.network_io_bytes_total.labels(direction=direction, interface=interface).inc(bytes_count)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando I/O de red: {e}")
    
    def record_error(self, service: str, error_type: str):
        """Registrar error"""
        try:
            self.errors_total.labels(service=service, error_type=error_type).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando error: {e}")
    
    def record_kafka_producer_error(self, topic: str, error_type: str):
        """Registrar error del producer de Kafka"""
        try:
            self.kafka_producer_errors_total.labels(topic=topic, error_type=error_type).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando error de Kafka producer: {e}")
    
    def record_redis_operation_failed(self, operation: str, error_type: str):
        """Registrar operación fallida de Redis"""
        try:
            self.redis_operations_failed_total.labels(operation=operation, error_type=error_type).inc()
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error registrando operación fallida de Redis: {e}")
    
    def set_system_info(self, info: Dict[str, str]):
        """Establecer información del sistema"""
        try:
            self.system_info.info(info)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo información del sistema: {e}")
    
    def set_model_info(self, info: Dict[str, str]):
        """Establecer información del modelo"""
        try:
            self.model_info.info(info)
            self._update_internal_metrics()
            
        except Exception as e:
            logger.error(f"Error estableciendo información del modelo: {e}")
    
    def _update_internal_metrics(self):
        """Actualizar métricas internas"""
        try:
            self.internal_metrics["metrics_updated_total"] += 1
            self.internal_metrics["last_update_time"] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas internas: {e}")
    
    def get_metrics(self) -> str:
        """Obtener métricas en formato Prometheus"""
        try:
            return generate_latest(REGISTRY).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return ""
    
    def get_internal_metrics(self) -> Dict[str, Any]:
        """Obtener métricas internas"""
        return self.internal_metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del gestor de métricas"""
        return {
            "server_started": self.server_started,
            "port": self.port,
            "metrics_created": self.internal_metrics["metrics_created_total"],
            "metrics_updated": self.internal_metrics["metrics_updated_total"],
            "last_update": self.internal_metrics["last_update_time"],
            "internal_metrics": self.get_internal_metrics()
        }
    
    def health_check(self) -> bool:
        """Verificar salud del gestor de métricas"""
        try:
            # Verificar que el servidor esté iniciado
            if not self.server_started:
                return False
            
            # Verificar que las métricas estén funcionando
            metrics = self.get_metrics()
            if not metrics:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear gestor
def create_prometheus_metrics(port: int = 8000) -> PrometheusMetrics:
    """Crear instancia del gestor de métricas de Prometheus"""
    return PrometheusMetrics(port)

if __name__ == "__main__":
    # Test del gestor de métricas
    def test_prometheus_metrics():
        metrics = PrometheusMetrics(8000)
        
        # Iniciar servidor
        metrics.start_server()
        
        # Test de métricas
        metrics.record_tick_received("BTCUSDT", "bitget")
        metrics.record_tick_processed("BTCUSDT", "success")
        metrics.record_processing_latency("BTCUSDT", "validation", 0.001)
        metrics.set_websocket_connections("bitget", "BTCUSDT", 1)
        
        # Test de métricas de trading
        metrics.record_trade_executed("BTCUSDT", "buy", "filled")
        metrics.set_account_balance("spot", 10000.0)
        metrics.set_open_positions_count("BTCUSDT", "long", 1)
        
        # Test de métricas de sistema
        metrics.set_cpu_usage("cpu0", 45.5)
        metrics.set_memory_usage("used", 8589934592)  # 8GB
        
        # Mostrar métricas
        print("=== MÉTRICAS DE PROMETHEUS ===")
        print(metrics.get_metrics())
        
        # Mostrar estado
        print("\n=== ESTADO DEL GESTOR ===")
        status = metrics.get_status()
        for key, value in status.items():
            print(f"{key}: {value}")
        
        # Test de health check
        health = metrics.health_check()
        print(f"\nHealth check: {health}")
    
    # Ejecutar test
    test_prometheus_metrics()
