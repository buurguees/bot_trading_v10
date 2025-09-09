#!/usr/bin/env python3
"""
Enterprise Monitoring System - Sistema de Monitoreo Avanzado
============================================================

Sistema enterprise-grade para monitoreo de entrenamiento con:
- Métricas en tiempo real con Prometheus
- Dashboards con Grafana
- Alertas automáticas
- Monitoreo de recursos (CPU, GPU, memoria)
- Tracking de experimentos
- Métricas de modelo (loss, accuracy, etc.)

Uso:
    from models.enterprise.monitoring_system import EnterpriseMonitoringSystem
    
    monitor = EnterpriseMonitoringSystem()
    await monitor.start_monitoring()
"""

import asyncio
import logging
import time
import psutil
import GPUtil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import json
import threading
from pathlib import Path

# Prometheus metrics
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, 
    start_http_server, CollectorRegistry, REGISTRY
)

# MLflow para experiment tracking
import mlflow
import mlflow.pytorch

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """Configuración del sistema de monitoreo"""
    # Prometheus
    prometheus_port: int = 8000
    prometheus_host: str = "0.0.0.0"
    
    # Métricas
    metrics_interval: float = 1.0  # segundos
    resource_interval: float = 5.0  # segundos
    
    # Alertas
    enable_alerts: bool = True
    alert_webhook_url: str = None
    alert_email: str = None
    
    # Límites
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_gpu_memory_percent: float = 90.0
    max_gpu_temp: float = 85.0
    
    # Logging
    log_metrics: bool = True
    log_file: str = "logs/monitoring.log"

class EnterpriseMonitoringSystem:
    """Sistema de monitoreo enterprise para entrenamiento"""
    
    def __init__(self, config: MonitoringConfig = None):
        self.config = config or MonitoringConfig()
        self.logger = logging.getLogger(__name__)
        
        # Estado del monitoreo
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Métricas Prometheus
        self._setup_prometheus_metrics()
        
        # Callbacks de alertas
        self.alert_callbacks: List[Callable] = []
        
        # Estado de recursos
        self.resource_state = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "gpu_memory_percent": 0.0,
            "gpu_temperature": 0.0,
            "disk_usage_percent": 0.0
        }
        
        # Historial de métricas
        self.metrics_history = {
            "timestamps": [],
            "cpu_percent": [],
            "memory_percent": [],
            "gpu_memory_percent": [],
            "gpu_temperature": []
        }
    
    def _setup_prometheus_metrics(self):
        """Configura métricas de Prometheus"""
        # Métricas de sistema
        self.cpu_usage = Gauge('system_cpu_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('system_memory_percent', 'Memory usage percentage')
        self.disk_usage = Gauge('system_disk_percent', 'Disk usage percentage')
        
        # Métricas de GPU
        self.gpu_memory_usage = Gauge('gpu_memory_percent', 'GPU memory usage percentage')
        self.gpu_temperature = Gauge('gpu_temperature_celsius', 'GPU temperature in Celsius')
        self.gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization percentage')
        
        # Métricas de entrenamiento
        self.training_epoch = Gauge('training_epoch', 'Current training epoch')
        self.training_loss = Gauge('training_loss', 'Current training loss')
        self.validation_loss = Gauge('validation_loss', 'Current validation loss')
        self.learning_rate = Gauge('learning_rate', 'Current learning rate')
        
        # Métricas de datos
        self.data_loaded_samples = Counter('data_loaded_samples_total', 'Total samples loaded')
        self.data_processed_batches = Counter('data_processed_batches_total', 'Total batches processed')
        
        # Métricas de tiempo
        self.training_duration = Histogram('training_duration_seconds', 'Training duration')
        self.epoch_duration = Histogram('epoch_duration_seconds', 'Epoch duration')
        self.batch_duration = Histogram('batch_duration_seconds', 'Batch processing duration')
        
        # Métricas de errores
        self.training_errors = Counter('training_errors_total', 'Total training errors')
        self.validation_errors = Counter('validation_errors_total', 'Total validation errors')
        
        # Métricas de checkpoints
        self.checkpoints_saved = Counter('checkpoints_saved_total', 'Total checkpoints saved')
        self.model_size_mb = Gauge('model_size_mb', 'Model size in MB')
    
    async def start_monitoring(self):
        """Inicia el sistema de monitoreo"""
        try:
            self.logger.info("Iniciando sistema de monitoreo enterprise")
            
            # Iniciar servidor Prometheus
            start_http_server(
                self.config.prometheus_port, 
                addr=self.config.prometheus_host
            )
            
            self.logger.info(f"Servidor Prometheus iniciado en {self.config.prometheus_host}:{self.config.prometheus_port}")
            
            # Iniciar monitoreo de recursos
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            self.logger.info("Sistema de monitoreo iniciado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error iniciando monitoreo: {e}")
            raise
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_monitoring:
            try:
                # Actualizar métricas de recursos
                self._update_resource_metrics()
                
                # Verificar alertas
                self._check_alerts()
                
                # Log métricas si está habilitado
                if self.config.log_metrics:
                    self._log_metrics()
                
                time.sleep(self.config.resource_interval)
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(1)
    
    def _update_resource_metrics(self):
        """Actualiza métricas de recursos del sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_percent)
            self.resource_state["cpu_percent"] = cpu_percent
            
            # Memoria
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_usage.set(memory_percent)
            self.resource_state["memory_percent"] = memory_percent
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_usage.set(disk_percent)
            self.resource_state["disk_usage_percent"] = disk_percent
            
            # GPU
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]  # Primera GPU
                    gpu_memory_percent = gpu.memoryUtil * 100
                    gpu_temperature = gpu.temperature
                    gpu_utilization = gpu.load * 100
                    
                    self.gpu_memory_usage.set(gpu_memory_percent)
                    self.gpu_temperature.set(gpu_temperature)
                    self.gpu_utilization.set(gpu_utilization)
                    
                    self.resource_state["gpu_memory_percent"] = gpu_memory_percent
                    self.resource_state["gpu_temperature"] = gpu_temperature
                else:
                    self.resource_state["gpu_memory_percent"] = 0.0
                    self.resource_state["gpu_temperature"] = 0.0
            except Exception as e:
                self.logger.debug(f"No se pudo obtener métricas de GPU: {e}")
                self.resource_state["gpu_memory_percent"] = 0.0
                self.resource_state["gpu_temperature"] = 0.0
            
            # Actualizar historial
            self._update_metrics_history()
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas de recursos: {e}")
    
    def _update_metrics_history(self):
        """Actualiza historial de métricas"""
        timestamp = time.time()
        
        self.metrics_history["timestamps"].append(timestamp)
        self.metrics_history["cpu_percent"].append(self.resource_state["cpu_percent"])
        self.metrics_history["memory_percent"].append(self.resource_state["memory_percent"])
        self.metrics_history["gpu_memory_percent"].append(self.resource_state["gpu_memory_percent"])
        self.metrics_history["gpu_temperature"].append(self.resource_state["gpu_temperature"])
        
        # Mantener solo los últimos 1000 puntos
        max_points = 1000
        for key in self.metrics_history:
            if len(self.metrics_history[key]) > max_points:
                self.metrics_history[key] = self.metrics_history[key][-max_points:]
    
    def _check_alerts(self):
        """Verifica condiciones de alerta"""
        if not self.config.enable_alerts:
            return
        
        alerts = []
        
        # CPU alto
        if self.resource_state["cpu_percent"] > self.config.max_cpu_percent:
            alerts.append(f"CPU usage high: {self.resource_state['cpu_percent']:.1f}%")
        
        # Memoria alta
        if self.resource_state["memory_percent"] > self.config.max_memory_percent:
            alerts.append(f"Memory usage high: {self.resource_state['memory_percent']:.1f}%")
        
        # GPU memoria alta
        if self.resource_state["gpu_memory_percent"] > self.config.max_gpu_memory_percent:
            alerts.append(f"GPU memory usage high: {self.resource_state['gpu_memory_percent']:.1f}%")
        
        # GPU temperatura alta
        if self.resource_state["gpu_temperature"] > self.config.max_gpu_temp:
            alerts.append(f"GPU temperature high: {self.resource_state['gpu_temperature']:.1f}°C")
        
        # Enviar alertas
        for alert in alerts:
            self._send_alert(alert)
    
    def _send_alert(self, message: str):
        """Envía alerta"""
        self.logger.warning(f"ALERT: {message}")
        
        # Ejecutar callbacks de alerta
        for callback in self.alert_callbacks:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Error en callback de alerta: {e}")
    
    def _log_metrics(self):
        """Log métricas actuales"""
        if self.config.log_file:
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a') as f:
                f.write(f"{datetime.now().isoformat()},"
                       f"cpu={self.resource_state['cpu_percent']:.1f},"
                       f"memory={self.resource_state['memory_percent']:.1f},"
                       f"gpu_memory={self.resource_state['gpu_memory_percent']:.1f},"
                       f"gpu_temp={self.resource_state['gpu_temperature']:.1f}\n")
    
    def add_alert_callback(self, callback: Callable[[str], None]):
        """Agrega callback de alerta"""
        self.alert_callbacks.append(callback)
    
    def update_training_metrics(
        self, 
        epoch: int = None,
        train_loss: float = None,
        val_loss: float = None,
        learning_rate: float = None
    ):
        """Actualiza métricas de entrenamiento"""
        if epoch is not None:
            self.training_epoch.set(epoch)
        
        if train_loss is not None:
            self.training_loss.set(train_loss)
        
        if val_loss is not None:
            self.validation_loss.set(val_loss)
        
        if learning_rate is not None:
            self.learning_rate.set(learning_rate)
    
    def log_data_loaded(self, samples: int):
        """Log samples de datos cargados"""
        self.data_loaded_samples.inc(samples)
    
    def log_batch_processed(self, duration: float = None):
        """Log batch procesado"""
        self.data_processed_batches.inc()
        
        if duration is not None:
            self.batch_duration.observe(duration)
    
    def log_epoch_completed(self, duration: float):
        """Log epoch completado"""
        self.epoch_duration.observe(duration)
    
    def log_training_error(self, error_type: str = "general"):
        """Log error de entrenamiento"""
        self.training_errors.labels(error_type=error_type).inc()
    
    def log_validation_error(self, error_type: str = "general"):
        """Log error de validación"""
        self.validation_errors.labels(error_type=error_type).inc()
    
    def log_checkpoint_saved(self, model_size_mb: float = None):
        """Log checkpoint guardado"""
        self.checkpoints_saved.inc()
        
        if model_size_mb is not None:
            self.model_size_mb.set(model_size_mb)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        return {
            "resource_state": self.resource_state.copy(),
            "metrics_history_length": len(self.metrics_history["timestamps"]),
            "is_monitoring": self.is_monitoring,
            "prometheus_url": f"http://{self.config.prometheus_host}:{self.config.prometheus_port}"
        }
    
    def get_metrics_history(self, last_n: int = 100) -> Dict[str, List]:
        """Obtiene historial de métricas"""
        result = {}
        for key, values in self.metrics_history.items():
            result[key] = values[-last_n:] if len(values) > last_n else values
        return result
    
    async def stop_monitoring(self):
        """Detiene el sistema de monitoreo"""
        self.logger.info("Deteniendo sistema de monitoreo")
        self.is_monitoring = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("Sistema de monitoreo detenido")

class TrainingProgressTracker:
    """Tracker de progreso de entrenamiento"""
    
    def __init__(self, monitoring_system: EnterpriseMonitoringSystem):
        self.monitoring = monitoring_system
        self.logger = logging.getLogger(__name__)
        
        # Estado del entrenamiento
        self.current_epoch = 0
        self.total_epochs = 0
        self.start_time = None
        self.epoch_start_time = None
        
        # Métricas acumuladas
        self.epoch_losses = []
        self.epoch_val_losses = []
        self.epoch_durations = []
    
    def start_training(self, total_epochs: int):
        """Inicia tracking de entrenamiento"""
        self.total_epochs = total_epochs
        self.start_time = time.time()
        self.current_epoch = 0
        
        self.logger.info(f"Iniciando tracking de entrenamiento: {total_epochs} epochs")
    
    def start_epoch(self, epoch: int):
        """Inicia tracking de epoch"""
        self.current_epoch = epoch
        self.epoch_start_time = time.time()
        
        self.monitoring.update_training_metrics(epoch=epoch)
        
        self.logger.info(f"Iniciando epoch {epoch}/{self.total_epochs}")
    
    def update_epoch_loss(self, loss: float, is_validation: bool = False):
        """Actualiza loss del epoch"""
        if is_validation:
            self.epoch_val_losses.append(loss)
            self.monitoring.update_training_metrics(val_loss=loss)
        else:
            self.epoch_losses.append(loss)
            self.monitoring.update_training_metrics(train_loss=loss)
    
    def end_epoch(self):
        """Finaliza tracking de epoch"""
        if self.epoch_start_time:
            duration = time.time() - self.epoch_start_time
            self.epoch_durations.append(duration)
            
            self.monitoring.log_epoch_completed(duration)
            
            self.logger.info(f"Epoch {self.current_epoch} completado en {duration:.2f}s")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del progreso"""
        if not self.start_time:
            return {}
        
        total_time = time.time() - self.start_time
        progress_percent = (self.current_epoch / self.total_epochs) * 100 if self.total_epochs > 0 else 0
        
        avg_epoch_duration = np.mean(self.epoch_durations) if self.epoch_durations else 0
        estimated_remaining = avg_epoch_duration * (self.total_epochs - self.current_epoch)
        
        return {
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "progress_percent": progress_percent,
            "total_time": total_time,
            "avg_epoch_duration": avg_epoch_duration,
            "estimated_remaining": estimated_remaining,
            "avg_train_loss": np.mean(self.epoch_losses[-10:]) if self.epoch_losses else 0,
            "avg_val_loss": np.mean(self.epoch_val_losses[-10:]) if self.epoch_val_losses else 0
        }

# Funciones de utilidad
def create_monitoring_config(
    prometheus_port: int = 8000,
    enable_alerts: bool = True,
    max_cpu_percent: float = 80.0,
    max_memory_percent: float = 85.0
) -> MonitoringConfig:
    """Crea configuración de monitoreo"""
    return MonitoringConfig(
        prometheus_port=prometheus_port,
        enable_alerts=enable_alerts,
        max_cpu_percent=max_cpu_percent,
        max_memory_percent=max_memory_percent
    )

async def setup_grafana_dashboard(monitoring_config: MonitoringConfig):
    """Configura dashboard de Grafana"""
    # Esta función configuraría automáticamente Grafana
    # Por ahora, solo log la configuración
    logger.info("Configurando dashboard de Grafana...")
    logger.info(f"Prometheus URL: http://{monitoring_config.prometheus_host}:{monitoring_config.prometheus_port}")
    logger.info("Dashboard de Grafana disponible en: http://localhost:3000")

# Ejemplo de uso
async def main():
    """Ejemplo de uso del sistema de monitoreo"""
    
    # Crear configuración
    config = create_monitoring_config()
    
    # Crear sistema de monitoreo
    monitor = EnterpriseMonitoringSystem(config)
    
    # Agregar callback de alerta
    def alert_callback(message: str):
        print(f"ALERTA: {message}")
    
    monitor.add_alert_callback(alert_callback)
    
    # Iniciar monitoreo
    await monitor.start_monitoring()
    
    # Crear tracker de progreso
    tracker = TrainingProgressTracker(monitor)
    
    # Simular entrenamiento
    tracker.start_training(10)
    
    for epoch in range(10):
        tracker.start_epoch(epoch)
        
        # Simular loss
        train_loss = 1.0 - (epoch * 0.1)
        val_loss = 1.1 - (epoch * 0.09)
        
        tracker.update_epoch_loss(train_loss)
        tracker.update_epoch_loss(val_loss, is_validation=True)
        
        # Simular duración de epoch
        await asyncio.sleep(1)
        
        tracker.end_epoch()
        
        # Mostrar progreso
        summary = tracker.get_progress_summary()
        print(f"Progreso: {summary['progress_percent']:.1f}% - Loss: {summary['avg_train_loss']:.3f}")
    
    # Obtener métricas finales
    metrics = monitor.get_metrics_summary()
    print(f"Métricas finales: {metrics}")
    
    # Detener monitoreo
    await monitor.stop_monitoring()

if __name__ == "__main__":
    import numpy as np
    asyncio.run(main())
