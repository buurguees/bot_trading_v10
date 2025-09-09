# training_monitor.py - Monitor de entrenamiento enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\training_monitor.py

"""
Monitor de entrenamiento enterprise para PyTorch Lightning.

Características:
- Monitoreo en tiempo real de métricas
- Alertas automáticas
- Visualización de progreso
- Integración con Prometheus
- Logging estructurado
"""

import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import Callback
from pytorch_lightning.utilities.types import STEP_OUTPUT
import logging
import time
import psutil
import GPUtil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

logger = logging.getLogger(__name__)

class TrainingMonitor(Callback):
    """Monitor de entrenamiento enterprise"""
    
    def __init__(
        self,
        log_every_n_steps: int = 100,
        log_every_n_epochs: int = 1,
        save_plots: bool = True,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        super().__init__()
        self.log_every_n_steps = log_every_n_steps
        self.log_every_n_epochs = log_every_n_epochs
        self.save_plots = save_plots
        
        # Configurar umbrales de alerta
        self.alert_thresholds = alert_thresholds or {
            'loss_spike': 2.0,  # Factor de aumento de loss
            'gradient_norm': 10.0,  # Norma de gradientes
            'memory_usage': 0.9,  # Uso de memoria
            'gpu_memory': 0.9,  # Uso de GPU
            'learning_rate': 1e-6  # Learning rate mínimo
        }
        
        # Estado del monitor
        self.metrics_history = []
        self.start_time = None
        self.current_epoch = 0
        self.current_step = 0
        
        # Configurar directorios
        self.monitor_dir = Path("monitoring/training")
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configura logging del monitor"""
        monitor_logger = logging.getLogger(f"{__name__}.TrainingMonitor")
        monitor_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.monitor_dir / "training_monitor.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        monitor_logger.addHandler(file_handler)
        self.monitor_logger = monitor_logger
    
    def on_train_start(self, trainer, pl_module):
        """Inicializa el monitor al inicio del entrenamiento"""
        self.start_time = time.time()
        self.monitor_logger.info("🚀 Monitor de entrenamiento iniciado")
        
        # Log información del sistema
        self._log_system_info()
        
    def on_train_epoch_start(self, trainer, pl_module):
        """Inicializa métricas al inicio de cada epoch"""
        self.current_epoch = trainer.current_epoch
        self.monitor_logger.info(f"📊 Iniciando epoch {self.current_epoch}")
        
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        """Monitorea cada batch de entrenamiento"""
        self.current_step = trainer.global_step
        
        if self.current_step % self.log_every_n_steps == 0:
            self._monitor_batch(trainer, pl_module, outputs, batch)
    
    def on_validation_epoch_end(self, trainer, pl_module):
        """Monitorea al final de cada epoch de validación"""
        if self.current_epoch % self.log_every_n_epochs == 0:
            self._monitor_epoch(trainer, pl_module)
    
    def on_train_end(self, trainer, pl_module):
        """Finaliza el monitor al terminar el entrenamiento"""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        self.monitor_logger.info(f"✅ Entrenamiento completado en {total_time:.2f} segundos")
        
        # Generar reporte final
        self._generate_final_report(trainer, pl_module)
    
    def _monitor_batch(self, trainer, pl_module, outputs, batch):
        """Monitorea un batch específico"""
        try:
            # Obtener métricas del batch
            batch_metrics = self._extract_batch_metrics(trainer, pl_module, outputs)
            
            # Monitorear sistema
            system_metrics = self._get_system_metrics()
            
            # Combinar métricas
            all_metrics = {**batch_metrics, **system_metrics}
            
            # Verificar alertas
            self._check_alerts(all_metrics)
            
            # Log métricas
            self._log_metrics(all_metrics, "batch")
            
            # Guardar en historial
            self.metrics_history.append({
                'timestamp': datetime.now().isoformat(),
                'epoch': self.current_epoch,
                'step': self.current_step,
                'type': 'batch',
                **all_metrics
            })
            
        except Exception as e:
            self.monitor_logger.error(f"Error monitoreando batch: {e}")
    
    def _monitor_epoch(self, trainer, pl_module):
        """Monitorea un epoch completo"""
        try:
            # Obtener métricas del epoch
            epoch_metrics = self._extract_epoch_metrics(trainer, pl_module)
            
            # Monitorear sistema
            system_metrics = self._get_system_metrics()
            
            # Combinar métricas
            all_metrics = {**epoch_metrics, **system_metrics}
            
            # Verificar alertas
            self._check_alerts(all_metrics)
            
            # Log métricas
            self._log_metrics(all_metrics, "epoch")
            
            # Guardar en historial
            self.metrics_history.append({
                'timestamp': datetime.now().isoformat(),
                'epoch': self.current_epoch,
                'step': self.current_step,
                'type': 'epoch',
                **all_metrics
            })
            
            # Generar plots si está habilitado
            if self.save_plots and self.current_epoch % 10 == 0:
                self._generate_plots()
                
        except Exception as e:
            self.monitor_logger.error(f"Error monitoreando epoch: {e}")
    
    def _extract_batch_metrics(self, trainer, pl_module, outputs) -> Dict[str, float]:
        """Extrae métricas de un batch"""
        metrics = {}
        
        try:
            # Obtener loss del batch
            if hasattr(pl_module, 'training_step'):
                if isinstance(outputs, dict):
                    metrics['batch_loss'] = outputs.get('loss', 0.0)
                else:
                    metrics['batch_loss'] = float(outputs) if outputs is not None else 0.0
            
            # Obtener learning rate
            if hasattr(trainer, 'optimizers') and trainer.optimizers:
                optimizer = trainer.optimizers[0]
                if hasattr(optimizer, 'param_groups'):
                    lr = optimizer.param_groups[0].get('lr', 0.0)
                    metrics['learning_rate'] = lr
            
            # Obtener gradientes
            if hasattr(pl_module, 'parameters'):
                total_norm = 0
                param_count = 0
                for param in pl_module.parameters():
                    if param.grad is not None:
                        param_norm = param.grad.data.norm(2)
                        total_norm += param_norm.item() ** 2
                        param_count += 1
                
                if param_count > 0:
                    total_norm = total_norm ** (1. / 2)
                    metrics['gradient_norm'] = total_norm
            
        except Exception as e:
            self.monitor_logger.warning(f"Error extrayendo métricas de batch: {e}")
        
        return metrics
    
    def _extract_epoch_metrics(self, trainer, pl_module) -> Dict[str, float]:
        """Extrae métricas de un epoch"""
        metrics = {}
        
        try:
            # Obtener métricas de callback_metrics
            callback_metrics = trainer.callback_metrics
            
            for key, value in callback_metrics.items():
                if isinstance(value, torch.Tensor):
                    metrics[key] = value.item()
                else:
                    metrics[key] = float(value)
            
            # Calcular tiempo del epoch
            if hasattr(trainer, 'train_dataloader'):
                dataloader = trainer.train_dataloader
                if hasattr(dataloader, '__len__'):
                    batch_size = dataloader.batch_size if hasattr(dataloader, 'batch_size') else 1
                    total_batches = len(dataloader)
                    metrics['batches_per_epoch'] = total_batches
                    metrics['samples_per_epoch'] = total_batches * batch_size
            
        except Exception as e:
            self.monitor_logger.warning(f"Error extrayendo métricas de epoch: {e}")
        
        return metrics
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Obtiene métricas del sistema"""
        metrics = {}
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage_percent'] = cpu_percent
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics['memory_usage_percent'] = memory.percent
            metrics['memory_usage_gb'] = memory.used / (1024**3)
            metrics['memory_available_gb'] = memory.available / (1024**3)
            
            # GPU usage
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated() / (1024**3)
                gpu_memory_max = torch.cuda.max_memory_allocated() / (1024**3)
                gpu_utilization = torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else 0
                
                metrics['gpu_memory_usage_gb'] = gpu_memory
                metrics['gpu_memory_max_gb'] = gpu_memory_max
                metrics['gpu_utilization_percent'] = gpu_utilization
                
                # Reset max memory
                torch.cuda.reset_peak_memory_stats()
            
        except Exception as e:
            self.monitor_logger.warning(f"Error obteniendo métricas del sistema: {e}")
        
        return metrics
    
    def _check_alerts(self, metrics: Dict[str, float]):
        """Verifica alertas basadas en métricas"""
        alerts = []
        
        # Alert de spike de loss
        if 'batch_loss' in metrics and 'train_loss' in metrics:
            loss_ratio = metrics['batch_loss'] / max(metrics['train_loss'], 1e-8)
            if loss_ratio > self.alert_thresholds['loss_spike']:
                alerts.append(f"Loss spike detectado: {loss_ratio:.2f}x")
        
        # Alert de gradientes
        if 'gradient_norm' in metrics:
            if metrics['gradient_norm'] > self.alert_thresholds['gradient_norm']:
                alerts.append(f"Gradientes explosivos: {metrics['gradient_norm']:.2f}")
        
        # Alert de memoria
        if 'memory_usage_percent' in metrics:
            if metrics['memory_usage_percent'] > self.alert_thresholds['memory_usage'] * 100:
                alerts.append(f"Alto uso de memoria: {metrics['memory_usage_percent']:.1f}%")
        
        # Alert de GPU
        if 'gpu_memory_usage_gb' in metrics and 'gpu_memory_max_gb' in metrics:
            gpu_usage = metrics['gpu_memory_usage_gb'] / max(metrics['gpu_memory_max_gb'], 1e-8)
            if gpu_usage > self.alert_thresholds['gpu_memory']:
                alerts.append(f"Alto uso de GPU: {gpu_usage:.1%}")
        
        # Alert de learning rate
        if 'learning_rate' in metrics:
            if metrics['learning_rate'] < self.alert_thresholds['learning_rate']:
                alerts.append(f"Learning rate muy bajo: {metrics['learning_rate']:.2e}")
        
        # Log alertas
        for alert in alerts:
            self.monitor_logger.warning(f"⚠️ {alert}")
    
    def _log_metrics(self, metrics: Dict[str, float], metric_type: str):
        """Log métricas"""
        metric_str = ", ".join([f"{k}: {v:.4f}" for k, v in metrics.items()])
        self.monitor_logger.info(f"📊 {metric_type.upper()} - {metric_str}")
    
    def _log_system_info(self):
        """Log información del sistema"""
        info = {
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'pytorch_version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'cuda_version': torch.version.cuda if torch.cuda.is_available() else None,
            'gpu_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3)
        }
        
        info_str = ", ".join([f"{k}: {v}" for k, v in info.items()])
        self.monitor_logger.info(f"🖥️ Sistema - {info_str}")
    
    def _generate_plots(self):
        """Genera gráficos de métricas"""
        try:
            if not self.metrics_history:
                return
            
            # Crear DataFrame
            import pandas as pd
            df = pd.DataFrame(self.metrics_history)
            
            # Filtrar métricas numéricas
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            plot_columns = [col for col in numeric_columns if col not in ['epoch', 'step']]
            
            if not plot_columns:
                return
            
            # Crear subplots
            n_plots = min(len(plot_columns), 6)  # Máximo 6 gráficos
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            axes = axes.flatten()
            
            for i, col in enumerate(plot_columns[:n_plots]):
                ax = axes[i]
                
                # Plotear métricas por epoch
                epoch_data = df[df['type'] == 'epoch']
                if not epoch_data.empty and col in epoch_data.columns:
                    ax.plot(epoch_data['epoch'], epoch_data[col], 'b-', label=col)
                    ax.set_xlabel('Epoch')
                    ax.set_ylabel(col)
                    ax.set_title(f'{col} vs Epoch')
                    ax.grid(True, alpha=0.3)
                    ax.legend()
            
            # Ocultar subplots vacíos
            for i in range(n_plots, len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            # Guardar plot
            plot_file = self.monitor_dir / f"training_metrics_epoch_{self.current_epoch}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.monitor_logger.info(f"📈 Gráfico guardado: {plot_file}")
            
        except Exception as e:
            self.monitor_logger.error(f"Error generando gráficos: {e}")
    
    def _generate_final_report(self, trainer, pl_module):
        """Genera reporte final del entrenamiento"""
        try:
            # Calcular estadísticas finales
            total_time = time.time() - self.start_time if self.start_time else 0
            
            # Obtener métricas finales
            final_metrics = trainer.callback_metrics
            
            # Crear reporte
            report = {
                'training_summary': {
                    'total_time_seconds': total_time,
                    'total_epochs': self.current_epoch,
                    'total_steps': self.current_step,
                    'final_metrics': {k: float(v) if isinstance(v, torch.Tensor) else v 
                                    for k, v in final_metrics.items()}
                },
                'system_info': {
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    'pytorch_version': torch.__version__,
                    'cuda_available': torch.cuda.is_available(),
                    'gpu_count': torch.cuda.device_count() if torch.cuda.is_available() else 0
                },
                'metrics_history': self.metrics_history[-100:]  # Últimos 100 registros
            }
            
            # Guardar reporte
            report_file = self.monitor_dir / f"training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.monitor_logger.info(f"📋 Reporte final guardado: {report_file}")
            
        except Exception as e:
            self.monitor_logger.error(f"Error generando reporte final: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        if not self.metrics_history:
            return {}
        
        # Convertir a DataFrame para análisis
        import pandas as pd
        df = pd.DataFrame(self.metrics_history)
        
        # Calcular estadísticas
        summary = {
            'total_epochs': self.current_epoch,
            'total_steps': self.current_step,
            'total_time_seconds': time.time() - self.start_time if self.start_time else 0,
            'metrics_count': len(self.metrics_history)
        }
        
        # Estadísticas por tipo de métrica
        for metric_type in ['batch', 'epoch']:
            type_data = df[df['type'] == metric_type]
            if not type_data.empty:
                summary[f'{metric_type}_metrics'] = len(type_data)
        
        return summary

# Funciones de utilidad
def create_training_monitor(
    log_every_n_steps: int = 100,
    log_every_n_epochs: int = 1,
    save_plots: bool = True,
    alert_thresholds: Optional[Dict[str, float]] = None
) -> TrainingMonitor:
    """Factory function para crear TrainingMonitor"""
    return TrainingMonitor(
        log_every_n_steps=log_every_n_steps,
        log_every_n_epochs=log_every_n_epochs,
        save_plots=save_plots,
        alert_thresholds=alert_thresholds
    )
