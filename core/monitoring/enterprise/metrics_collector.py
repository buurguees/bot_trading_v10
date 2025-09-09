# metrics_collector.py - Colector de métricas enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\metrics_collector.py

"""
Colector de métricas enterprise para Prometheus.

Características:
- Recolección de métricas personalizadas
- Exportación a Prometheus
- Métricas de trading, ML y sistema
- Agregación y procesamiento
- Integración con MLflow
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import asyncio
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    start_http_server, CollectorRegistry, generate_latest
)
import torch
import psutil
import GPUtil

logger = logging.getLogger(__name__)

@dataclass
class MetricValue:
    """Valor de métrica con metadatos"""
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metric_type: str  # 'counter', 'gauge', 'histogram', 'summary'

class MetricsCollector:
    """Colector de métricas enterprise"""
    
    def __init__(
        self,
        prometheus_port: int = 8000,
        collection_interval: float = 5.0,
        history_size: int = 10000
    ):
        self.prometheus_port = prometheus_port
        self.collection_interval = collection_interval
        self.history_size = history_size
        
        # Estado del colector
        self.is_collecting = False
        self.collection_thread = None
        self.metrics_history = deque(maxlen=history_size)
        
        # Configurar directorios
        self.metrics_dir = Path("monitoring/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Inicializar métricas de Prometheus
        self.setup_prometheus_metrics()
        
        # Iniciar servidor Prometheus
        self.start_prometheus_server()
        
    def setup_logging(self):
        """Configura logging del colector"""
        collector_logger = logging.getLogger(f"{__name__}.MetricsCollector")
        collector_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.metrics_dir / "metrics_collector.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        collector_logger.addHandler(file_handler)
        self.collector_logger = collector_logger
    
    def setup_prometheus_metrics(self):
        """Configura métricas de Prometheus"""
        self.registry = CollectorRegistry()
        
        # Métricas de trading
        self.trading_metrics = self._create_trading_metrics()
        
        # Métricas de ML
        self.ml_metrics = self._create_ml_metrics()
        
        # Métricas de sistema
        self.system_metrics = self._create_system_metrics()
        
        # Métricas de data collection
        self.data_collection_metrics = self._create_data_collection_metrics()
        
        # Métricas de performance
        self.performance_metrics = self._create_performance_metrics()
        
        # Registrar todas las métricas
        self._register_all_metrics()
    
    def _create_trading_metrics(self) -> Dict[str, Any]:
        """Crea métricas de trading"""
        return {
            'trades_executed_total': Counter(
                'trading_trades_executed_total',
                'Total de trades ejecutados',
                ['symbol', 'side', 'status', 'strategy'],
                registry=self.registry
            ),
            'trades_pnl_total': Counter(
                'trading_trades_pnl_total',
                'PnL total de trades',
                ['symbol', 'side'],
                registry=self.registry
            ),
            'account_balance_usd': Gauge(
                'trading_account_balance_usd',
                'Balance de cuenta en USD',
                ['account_type'],
                registry=self.registry
            ),
            'open_positions_count': Gauge(
                'trading_open_positions_count',
                'Número de posiciones abiertas',
                ['symbol', 'side'],
                registry=self.registry
            ),
            'trade_amount_usd': Histogram(
                'trading_trade_amount_usd',
                'Cantidad de trade en USD',
                ['symbol', 'side'],
                buckets=[10, 50, 100, 500, 1000, 5000, 10000],
                registry=self.registry
            ),
            'order_execution_time_seconds': Histogram(
                'trading_order_execution_time_seconds',
                'Tiempo de ejecución de órdenes',
                ['symbol', 'order_type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                registry=self.registry
            ),
            'trading_errors_total': Counter(
                'trading_errors_total',
                'Total de errores de trading',
                ['error_type', 'symbol'],
                registry=self.registry
            )
        }
    
    def _create_ml_metrics(self) -> Dict[str, Any]:
        """Crea métricas de ML"""
        return {
            'training_epochs_total': Counter(
                'ml_training_epochs_total',
                'Total de epochs de entrenamiento',
                ['model_name', 'symbol'],
                registry=self.registry
            ),
            'training_loss': Gauge(
                'ml_training_loss',
                'Loss de entrenamiento actual',
                ['model_name', 'symbol', 'phase'],
                registry=self.registry
            ),
            'training_accuracy': Gauge(
                'ml_training_accuracy',
                'Accuracy de entrenamiento actual',
                ['model_name', 'symbol', 'phase'],
                registry=self.registry
            ),
            'model_inference_time_seconds': Histogram(
                'ml_model_inference_time_seconds',
                'Tiempo de inferencia del modelo',
                ['model_name', 'symbol'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
                registry=self.registry
            ),
            'model_predictions_total': Counter(
                'ml_model_predictions_total',
                'Total de predicciones del modelo',
                ['model_name', 'symbol', 'prediction_type'],
                registry=self.registry
            ),
            'model_confidence': Gauge(
                'ml_model_confidence',
                'Confianza del modelo',
                ['model_name', 'symbol'],
                registry=self.registry
            ),
            'hyperparameter_tuning_trials_total': Counter(
                'ml_hyperparameter_tuning_trials_total',
                'Total de trials de hyperparameter tuning',
                ['model_name', 'status'],
                registry=self.registry
            ),
            'model_training_duration_seconds': Histogram(
                'ml_model_training_duration_seconds',
                'Duración de entrenamiento de modelos',
                ['model_name', 'symbol'],
                buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
                registry=self.registry
            )
        }
    
    def _create_system_metrics(self) -> Dict[str, Any]:
        """Crea métricas de sistema"""
        return {
            'cpu_usage_percent': Gauge(
                'system_cpu_usage_percent',
                'Uso de CPU en porcentaje',
                ['core'],
                registry=self.registry
            ),
            'memory_usage_bytes': Gauge(
                'system_memory_usage_bytes',
                'Uso de memoria en bytes',
                ['type'],
                registry=self.registry
            ),
            'disk_usage_bytes': Gauge(
                'system_disk_usage_bytes',
                'Uso de disco en bytes',
                ['mount_point', 'type'],
                registry=self.registry
            ),
            'network_io_bytes_total': Counter(
                'system_network_io_bytes_total',
                'Total de bytes de red',
                ['direction', 'interface'],
                registry=self.registry
            ),
            'process_count': Gauge(
                'system_process_count',
                'Número de procesos',
                registry=self.registry
            ),
            'thread_count': Gauge(
                'system_thread_count',
                'Número de hilos',
                registry=self.registry
            ),
            'load_average': Gauge(
                'system_load_average',
                'Load average del sistema',
                ['period'],
                registry=self.registry
            )
        }
    
    def _create_data_collection_metrics(self) -> Dict[str, Any]:
        """Crea métricas de data collection"""
        return {
            'ticks_received_total': Counter(
                'data_collection_ticks_received_total',
                'Total de ticks recibidos',
                ['symbol', 'source'],
                registry=self.registry
            ),
            'ticks_processed_total': Counter(
                'data_collection_ticks_processed_total',
                'Total de ticks procesados',
                ['symbol', 'status'],
                registry=self.registry
            ),
            'ticks_dropped_total': Counter(
                'data_collection_ticks_dropped_total',
                'Total de ticks descartados',
                ['symbol', 'reason'],
                registry=self.registry
            ),
            'processing_latency_seconds': Histogram(
                'data_collection_processing_latency_seconds',
                'Latencia de procesamiento de ticks',
                ['symbol', 'operation'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                registry=self.registry
            ),
            'websocket_connections_active': Gauge(
                'data_collection_websocket_connections_active',
                'Conexiones WebSocket activas',
                ['exchange', 'symbol'],
                registry=self.registry
            ),
            'kafka_messages_sent_total': Counter(
                'data_collection_kafka_messages_sent_total',
                'Total de mensajes enviados a Kafka',
                ['topic', 'status'],
                registry=self.registry
            ),
            'redis_operations_total': Counter(
                'data_collection_redis_operations_total',
                'Total de operaciones Redis',
                ['operation_type', 'status'],
                registry=self.registry
            ),
            'timescaledb_inserts_total': Counter(
                'data_collection_timescaledb_inserts_total',
                'Total de inserts a TimescaleDB',
                ['table', 'status'],
                registry=self.registry
            )
        }
    
    def _create_performance_metrics(self) -> Dict[str, Any]:
        """Crea métricas de performance"""
        return {
            'response_time_seconds': Histogram(
                'performance_response_time_seconds',
                'Tiempo de respuesta de operaciones',
                ['operation', 'status'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                registry=self.registry
            ),
            'throughput_ops_per_second': Gauge(
                'performance_throughput_ops_per_second',
                'Throughput de operaciones por segundo',
                ['operation'],
                registry=self.registry
            ),
            'error_rate_percent': Gauge(
                'performance_error_rate_percent',
                'Tasa de errores en porcentaje',
                ['operation'],
                registry=self.registry
            ),
            'queue_size': Gauge(
                'performance_queue_size',
                'Tamaño de colas',
                ['queue_name'],
                registry=self.registry
            ),
            'cache_hit_rate_percent': Gauge(
                'performance_cache_hit_rate_percent',
                'Tasa de aciertos de cache',
                ['cache_name'],
                registry=self.registry
            ),
            'gpu_memory_usage_bytes': Gauge(
                'performance_gpu_memory_usage_bytes',
                'Uso de memoria GPU',
                ['gpu_id'],
                registry=self.registry
            ),
            'gpu_utilization_percent': Gauge(
                'performance_gpu_utilization_percent',
                'Utilización de GPU',
                ['gpu_id'],
                registry=self.registry
            )
        }
    
    def _register_all_metrics(self):
        """Registra todas las métricas en el registry"""
        all_metrics = [
            self.trading_metrics,
            self.ml_metrics,
            self.system_metrics,
            self.data_collection_metrics,
            self.performance_metrics
        ]
        
        for metric_group in all_metrics:
            for metric_name, metric_obj in metric_group.items():
                self.registry.register(metric_obj)
    
    def start_prometheus_server(self):
        """Inicia servidor Prometheus"""
        try:
            start_http_server(self.prometheus_port, registry=self.registry)
            self.collector_logger.info(f"📊 Servidor Prometheus iniciado en puerto {self.prometheus_port}")
        except Exception as e:
            self.collector_logger.error(f"Error iniciando servidor Prometheus: {e}")
    
    def start_collection(self):
        """Inicia recolección de métricas"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self.collection_thread.start()
        
        self.collector_logger.info("🚀 Recolección de métricas iniciada")
    
    def stop_collection(self):
        """Detiene recolección de métricas"""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        self.collector_logger.info("🛑 Recolección de métricas detenida")
    
    def _collection_loop(self):
        """Loop principal de recolección"""
        while self.is_collecting:
            try:
                # Recolectar métricas del sistema
                self._collect_system_metrics()
                
                # Recolectar métricas de GPU
                self._collect_gpu_metrics()
                
                # Recolectar métricas de trading (si están disponibles)
                self._collect_trading_metrics()
                
                # Recolectar métricas de ML (si están disponibles)
                self._collect_ml_metrics()
                
                # Recolectar métricas de data collection (si están disponibles)
                self._collect_data_collection_metrics()
                
            except Exception as e:
                self.collector_logger.error(f"Error en recolección de métricas: {e}")
            
            time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self):
        """Recolecta métricas del sistema"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            for i, cpu in enumerate(cpu_percent):
                self.system_metrics['cpu_usage_percent'].labels(core=f'cpu{i}').set(cpu)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_metrics['memory_usage_bytes'].labels(type='virtual').set(memory.used)
            self.system_metrics['memory_usage_bytes'].labels(type='available').set(memory.available)
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            self.system_metrics['disk_usage_bytes'].labels(mount_point='/', type='used').set(disk_usage.used)
            self.system_metrics['disk_usage_bytes'].labels(mount_point='/', type='free').set(disk_usage.free)
            
            # Network I/O
            network_io = psutil.net_io_counters()
            if network_io:
                self.system_metrics['network_io_bytes_total'].labels(
                    direction='sent', interface='total'
                )._value._value = network_io.bytes_sent
                self.system_metrics['network_io_bytes_total'].labels(
                    direction='received', interface='total'
                )._value._value = network_io.bytes_recv
            
            # Process and thread count
            self.system_metrics['process_count'].set(len(psutil.pids()))
            self.system_metrics['thread_count'].set(psutil.Process().num_threads())
            
            # Load average
            try:
                load_avg = psutil.getloadavg()
                for i, load in enumerate(load_avg):
                    period = ['1m', '5m', '15m'][i]
                    self.system_metrics['load_average'].labels(period=period).set(load)
            except AttributeError:
                pass  # No disponible en Windows
            
        except Exception as e:
            self.collector_logger.error(f"Error recolectando métricas del sistema: {e}")
    
    def _collect_gpu_metrics(self):
        """Recolecta métricas de GPU"""
        try:
            if not torch.cuda.is_available():
                return
            
            # GPU memory usage
            for i in range(torch.cuda.device_count()):
                gpu_memory = torch.cuda.memory_allocated(i)
                self.performance_metrics['gpu_memory_usage_bytes'].labels(gpu_id=i).set(gpu_memory)
                
                # GPU utilization (si está disponible)
                if hasattr(torch.cuda, 'utilization'):
                    gpu_util = torch.cuda.utilization(i)
                    self.performance_metrics['gpu_utilization_percent'].labels(gpu_id=i).set(gpu_util)
            
        except Exception as e:
            self.collector_logger.error(f"Error recolectando métricas de GPU: {e}")
    
    def _collect_trading_metrics(self):
        """Recolecta métricas de trading"""
        # Esta función se implementaría con la integración del sistema de trading
        # Por ahora, solo se mantiene como placeholder
        pass
    
    def _collect_ml_metrics(self):
        """Recolecta métricas de ML"""
        # Esta función se implementaría con la integración del sistema de ML
        # Por ahora, solo se mantiene como placeholder
        pass
    
    def _collect_data_collection_metrics(self):
        """Recolecta métricas de data collection"""
        # Esta función se implementaría con la integración del sistema de data collection
        # Por ahora, solo se mantiene como placeholder
        pass
    
    def record_trade(
        self,
        symbol: str,
        side: str,
        amount_usd: float,
        execution_time: float,
        status: str = "success",
        strategy: str = "default"
    ):
        """Registra un trade"""
        self.trading_metrics['trades_executed_total'].labels(
            symbol=symbol, side=side, status=status, strategy=strategy
        ).inc()
        
        self.trading_metrics['trade_amount_usd'].labels(
            symbol=symbol, side=side
        ).observe(amount_usd)
        
        self.trading_metrics['order_execution_time_seconds'].labels(
            symbol=symbol, order_type=side
        ).observe(execution_time)
    
    def record_ml_training(
        self,
        model_name: str,
        symbol: str,
        epoch: int,
        loss: float,
        accuracy: float,
        phase: str = "train"
    ):
        """Registra métricas de entrenamiento ML"""
        self.ml_metrics['training_epochs_total'].labels(
            model_name=model_name, symbol=symbol
        ).inc()
        
        self.ml_metrics['training_loss'].labels(
            model_name=model_name, symbol=symbol, phase=phase
        ).set(loss)
        
        self.ml_metrics['training_accuracy'].labels(
            model_name=model_name, symbol=symbol, phase=phase
        ).set(accuracy)
    
    def record_data_collection(
        self,
        symbol: str,
        source: str,
        operation: str,
        latency: float,
        status: str = "success"
    ):
        """Registra métricas de data collection"""
        self.data_collection_metrics['ticks_received_total'].labels(
            symbol=symbol, source=source
        ).inc()
        
        self.data_collection_metrics['ticks_processed_total'].labels(
            symbol=symbol, status=status
        ).inc()
        
        self.data_collection_metrics['processing_latency_seconds'].labels(
            symbol=symbol, operation=operation
        ).observe(latency)
    
    def record_performance(
        self,
        operation: str,
        response_time: float,
        status: str = "success"
    ):
        """Registra métricas de performance"""
        self.performance_metrics['response_time_seconds'].labels(
            operation=operation, status=status
        ).observe(response_time)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        return {
            'prometheus_port': self.prometheus_port,
            'is_collecting': self.is_collecting,
            'history_size': len(self.metrics_history),
            'metrics_groups': {
                'trading': len(self.trading_metrics),
                'ml': len(self.ml_metrics),
                'system': len(self.system_metrics),
                'data_collection': len(self.data_collection_metrics),
                'performance': len(self.performance_metrics)
            }
        }
    
    def export_metrics(self) -> str:
        """Exporta métricas en formato Prometheus"""
        return generate_latest(self.registry)
    
    def save_metrics_snapshot(self, filename: Optional[str] = None):
        """Guarda snapshot de métricas"""
        if filename is None:
            filename = f"metrics_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        snapshot_file = self.metrics_dir / filename
        
        try:
            with open(snapshot_file, 'w') as f:
                f.write(self.export_metrics())
            
            self.collector_logger.info(f"📊 Snapshot de métricas guardado: {snapshot_file}")
            
        except Exception as e:
            self.collector_logger.error(f"Error guardando snapshot de métricas: {e}")

# Funciones de utilidad
def create_metrics_collector(
    prometheus_port: int = 8000,
    collection_interval: float = 5.0,
    history_size: int = 10000
) -> MetricsCollector:
    """Factory function para crear MetricsCollector"""
    return MetricsCollector(
        prometheus_port=prometheus_port,
        collection_interval=collection_interval,
        history_size=history_size
    )

def start_metrics_collection(
    prometheus_port: int = 8000,
    collection_interval: float = 5.0
) -> MetricsCollector:
    """Inicia recolección de métricas"""
    collector = create_metrics_collector(
        prometheus_port=prometheus_port,
        collection_interval=collection_interval
    )
    
    collector.start_collection()
    return collector
