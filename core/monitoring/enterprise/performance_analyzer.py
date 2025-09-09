# Ruta: core/monitoring/enterprise/performance_analyzer.py
# performance_analyzer.py - Analizador de rendimiento enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\performance_analyzer.py

"""
Analizador de rendimiento para el sistema de trading enterprise.

Características:
- Análisis de rendimiento en tiempo real
- Detección de cuellos de botella
- Optimización automática de recursos
- Reportes de rendimiento
- Integración con Prometheus
"""

import time
import psutil
import GPUtil
import threading
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import pandas as pd
from collections import deque, defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor
import torch

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del sistema"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    gpu_usage: Optional[float]
    gpu_memory: Optional[float]
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    process_count: int
    thread_count: int
    load_average: float

@dataclass
class BottleneckAlert:
    """Alerta de cuello de botella"""
    timestamp: datetime
    type: str  # 'cpu', 'memory', 'gpu', 'disk', 'network'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    current_value: float
    threshold: float
    recommendation: str

class PerformanceAnalyzer:
    """Analizador de rendimiento enterprise"""
    
    def __init__(
        self,
        monitoring_interval: float = 5.0,
        history_size: int = 1000,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        self.alert_thresholds = alert_thresholds or self._get_default_thresholds()
        
        # Estado del analizador
        self.is_monitoring = False
        self.monitor_thread = None
        self.metrics_history = deque(maxlen=history_size)
        self.bottleneck_alerts = deque(maxlen=100)
        
        # Configurar directorios
        self.analysis_dir = Path("monitoring/performance")
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Estadísticas de rendimiento
        self.performance_stats = {
            'total_samples': 0,
            'avg_cpu_usage': 0.0,
            'avg_memory_usage': 0.0,
            'avg_gpu_usage': 0.0,
            'peak_cpu_usage': 0.0,
            'peak_memory_usage': 0.0,
            'peak_gpu_usage': 0.0,
            'bottleneck_count': 0
        }
        
    def setup_logging(self):
        """Configura logging del analizador"""
        analyzer_logger = logging.getLogger(f"{__name__}.PerformanceAnalyzer")
        analyzer_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.analysis_dir / "performance_analyzer.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        analyzer_logger.addHandler(file_handler)
        self.analyzer_logger = analyzer_logger
    
    def _get_default_thresholds(self) -> Dict[str, float]:
        """Obtiene umbrales por defecto para alertas"""
        return {
            'cpu_usage': 80.0,  # Porcentaje
            'memory_usage': 85.0,  # Porcentaje
            'gpu_usage': 90.0,  # Porcentaje
            'gpu_memory': 90.0,  # Porcentaje
            'disk_usage': 90.0,  # Porcentaje
            'load_average': 4.0,  # Load average
            'response_time': 1.0,  # Segundos
            'error_rate': 5.0  # Porcentaje
        }
    
    def start_monitoring(self):
        """Inicia el monitoreo de rendimiento"""
        if self.is_monitoring:
            self.analyzer_logger.warning("El monitoreo ya está activo")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        self.analyzer_logger.info("🚀 Monitoreo de rendimiento iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo de rendimiento"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.analyzer_logger.info("🛑 Monitoreo de rendimiento detenido")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_monitoring:
            try:
                # Recopilar métricas
                metrics = self._collect_metrics()
                
                # Analizar cuellos de botella
                self._analyze_bottlenecks(metrics)
                
                # Actualizar estadísticas
                self._update_performance_stats(metrics)
                
                # Guardar métricas
                self.metrics_history.append(metrics)
                
                # Log métricas cada 10 muestras
                if len(self.metrics_history) % 10 == 0:
                    self._log_performance_summary()
                
            except Exception as e:
                self.analyzer_logger.error(f"Error en loop de monitoreo: {e}")
            
            time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Recopila métricas del sistema"""
        timestamp = datetime.now()
        
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # GPU usage (si está disponible)
        gpu_usage = None
        gpu_memory = None
        if torch.cuda.is_available():
            try:
                gpu_usage = torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else None
                gpu_memory = (torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()) * 100
            except Exception:
                pass
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_io_dict = {
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0,
            'read_count': disk_io.read_count if disk_io else 0,
            'write_count': disk_io.write_count if disk_io else 0
        }
        
        # Network I/O
        network_io = psutil.net_io_counters()
        network_io_dict = {
            'bytes_sent': network_io.bytes_sent if network_io else 0,
            'bytes_recv': network_io.bytes_recv if network_io else 0,
            'packets_sent': network_io.packets_sent if network_io else 0,
            'packets_recv': network_io.packets_recv if network_io else 0
        }
        
        # Process and thread count
        process_count = len(psutil.pids())
        thread_count = psutil.Process().num_threads()
        
        # Load average (solo en sistemas Unix)
        try:
            load_average = psutil.getloadavg()[0]
        except AttributeError:
            load_average = 0.0
        
        return PerformanceMetrics(
            timestamp=timestamp,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            gpu_usage=gpu_usage,
            gpu_memory=gpu_memory,
            disk_io=disk_io_dict,
            network_io=network_io_dict,
            process_count=process_count,
            thread_count=thread_count,
            load_average=load_average
        )
    
    def _analyze_bottlenecks(self, metrics: PerformanceMetrics):
        """Analiza cuellos de botella en el sistema"""
        alerts = []
        
        # CPU bottleneck
        if metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            severity = self._get_severity(metrics.cpu_usage, self.alert_thresholds['cpu_usage'])
            alerts.append(BottleneckAlert(
                timestamp=metrics.timestamp,
                type='cpu',
                severity=severity,
                message=f"Alto uso de CPU: {metrics.cpu_usage:.1f}%",
                current_value=metrics.cpu_usage,
                threshold=self.alert_thresholds['cpu_usage'],
                recommendation="Considerar optimizar algoritmos o aumentar recursos"
            ))
        
        # Memory bottleneck
        if metrics.memory_usage > self.alert_thresholds['memory_usage']:
            severity = self._get_severity(metrics.memory_usage, self.alert_thresholds['memory_usage'])
            alerts.append(BottleneckAlert(
                timestamp=metrics.timestamp,
                type='memory',
                severity=severity,
                message=f"Alto uso de memoria: {metrics.memory_usage:.1f}%",
                current_value=metrics.memory_usage,
                threshold=self.alert_thresholds['memory_usage'],
                recommendation="Considerar liberar memoria o aumentar RAM"
            ))
        
        # GPU bottleneck
        if metrics.gpu_usage and metrics.gpu_usage > self.alert_thresholds['gpu_usage']:
            severity = self._get_severity(metrics.gpu_usage, self.alert_thresholds['gpu_usage'])
            alerts.append(BottleneckAlert(
                timestamp=metrics.timestamp,
                type='gpu',
                severity=severity,
                message=f"Alto uso de GPU: {metrics.gpu_usage:.1f}%",
                current_value=metrics.gpu_usage,
                threshold=self.alert_thresholds['gpu_usage'],
                recommendation="Considerar optimizar modelos o usar múltiples GPUs"
            ))
        
        # GPU Memory bottleneck
        if metrics.gpu_memory and metrics.gpu_memory > self.alert_thresholds['gpu_memory']:
            severity = self._get_severity(metrics.gpu_memory, self.alert_thresholds['gpu_memory'])
            alerts.append(BottleneckAlert(
                timestamp=metrics.timestamp,
                type='gpu_memory',
                severity=severity,
                message=f"Alta memoria GPU: {metrics.gpu_memory:.1f}%",
                current_value=metrics.gpu_memory,
                threshold=self.alert_thresholds['gpu_memory'],
                recommendation="Considerar reducir batch size o usar gradient checkpointing"
            ))
        
        # Load average bottleneck
        if metrics.load_average > self.alert_thresholds['load_average']:
            severity = self._get_severity(metrics.load_average, self.alert_thresholds['load_average'])
            alerts.append(BottleneckAlert(
                timestamp=metrics.timestamp,
                type='load',
                severity=severity,
                message=f"Alta carga del sistema: {metrics.load_average:.2f}",
                current_value=metrics.load_average,
                threshold=self.alert_thresholds['load_average'],
                recommendation="Considerar distribuir carga o aumentar recursos"
            ))
        
        # Agregar alertas al historial
        for alert in alerts:
            self.bottleneck_alerts.append(alert)
            self._log_bottleneck_alert(alert)
    
    def _get_severity(self, current_value: float, threshold: float) -> str:
        """Determina la severidad basada en el valor actual vs umbral"""
        ratio = current_value / threshold
        
        if ratio >= 2.0:
            return 'critical'
        elif ratio >= 1.5:
            return 'high'
        elif ratio >= 1.2:
            return 'medium'
        else:
            return 'low'
    
    def _log_bottleneck_alert(self, alert: BottleneckAlert):
        """Log de alerta de cuello de botella"""
        severity_emoji = {
            'low': '🟡',
            'medium': '🟠',
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_emoji.get(alert.severity, '⚠️')
        self.analyzer_logger.warning(
            f"{emoji} {alert.type.upper()} - {alert.message} "
            f"(Umbral: {alert.threshold:.1f}, Recomendación: {alert.recommendation})"
        )
    
    def _update_performance_stats(self, metrics: PerformanceMetrics):
        """Actualiza estadísticas de rendimiento"""
        self.performance_stats['total_samples'] += 1
        
        # Actualizar promedios
        n = self.performance_stats['total_samples']
        self.performance_stats['avg_cpu_usage'] = (
            (self.performance_stats['avg_cpu_usage'] * (n - 1) + metrics.cpu_usage) / n
        )
        self.performance_stats['avg_memory_usage'] = (
            (self.performance_stats['avg_memory_usage'] * (n - 1) + metrics.memory_usage) / n
        )
        
        if metrics.gpu_usage is not None:
            self.performance_stats['avg_gpu_usage'] = (
                (self.performance_stats['avg_gpu_usage'] * (n - 1) + metrics.gpu_usage) / n
            )
        
        # Actualizar picos
        self.performance_stats['peak_cpu_usage'] = max(
            self.performance_stats['peak_cpu_usage'], metrics.cpu_usage
        )
        self.performance_stats['peak_memory_usage'] = max(
            self.performance_stats['peak_memory_usage'], metrics.memory_usage
        )
        
        if metrics.gpu_usage is not None:
            self.performance_stats['peak_gpu_usage'] = max(
                self.performance_stats['peak_gpu_usage'], metrics.gpu_usage
            )
        
        # Contar cuellos de botella
        if self.bottleneck_alerts:
            self.performance_stats['bottleneck_count'] = len(self.bottleneck_alerts)
    
    def _log_performance_summary(self):
        """Log resumen de rendimiento"""
        stats = self.performance_stats
        self.analyzer_logger.info(
            f"📊 Rendimiento - Muestras: {stats['total_samples']}, "
            f"CPU: {stats['avg_cpu_usage']:.1f}% (pico: {stats['peak_cpu_usage']:.1f}%), "
            f"Memoria: {stats['avg_memory_usage']:.1f}% (pico: {stats['peak_memory_usage']:.1f}%), "
            f"Cuellos de botella: {stats['bottleneck_count']}"
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de rendimiento"""
        return {
            'performance_stats': self.performance_stats.copy(),
            'recent_alerts': list(self.bottleneck_alerts)[-10:],  # Últimas 10 alertas
            'monitoring_active': self.is_monitoring,
            'history_size': len(self.metrics_history)
        }
    
    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """Obtiene análisis de cuellos de botella"""
        if not self.bottleneck_alerts:
            return {'message': 'No se detectaron cuellos de botella'}
        
        # Agrupar por tipo
        by_type = defaultdict(list)
        for alert in self.bottleneck_alerts:
            by_type[alert.type].append(alert)
        
        # Calcular estadísticas por tipo
        analysis = {}
        for alert_type, alerts in by_type.items():
            severities = [alert.severity for alert in alerts]
            severity_counts = {s: severities.count(s) for s in set(severities)}
            
            analysis[alert_type] = {
                'total_alerts': len(alerts),
                'severity_distribution': severity_counts,
                'most_common_severity': max(severity_counts, key=severity_counts.get),
                'latest_alert': alerts[-1].timestamp.isoformat() if alerts else None
            }
        
        return analysis
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Genera reporte completo de rendimiento"""
        try:
            # Convertir historial a DataFrame
            if not self.metrics_history:
                return {'error': 'No hay datos de rendimiento disponibles'}
            
            df = pd.DataFrame([
                {
                    'timestamp': m.timestamp,
                    'cpu_usage': m.cpu_usage,
                    'memory_usage': m.memory_usage,
                    'gpu_usage': m.gpu_usage or 0,
                    'gpu_memory': m.gpu_memory or 0,
                    'load_average': m.load_average
                }
                for m in self.metrics_history
            ])
            
            # Calcular estadísticas
            report = {
                'summary': self.performance_stats.copy(),
                'bottleneck_analysis': self.get_bottleneck_analysis(),
                'time_series_stats': {
                    'cpu_usage': {
                        'mean': df['cpu_usage'].mean(),
                        'std': df['cpu_usage'].std(),
                        'min': df['cpu_usage'].min(),
                        'max': df['cpu_usage'].max(),
                        'percentile_95': df['cpu_usage'].quantile(0.95)
                    },
                    'memory_usage': {
                        'mean': df['memory_usage'].mean(),
                        'std': df['memory_usage'].std(),
                        'min': df['memory_usage'].min(),
                        'max': df['memory_usage'].max(),
                        'percentile_95': df['memory_usage'].quantile(0.95)
                    },
                    'gpu_usage': {
                        'mean': df['gpu_usage'].mean(),
                        'std': df['gpu_usage'].std(),
                        'min': df['gpu_usage'].min(),
                        'max': df['gpu_usage'].max(),
                        'percentile_95': df['gpu_usage'].quantile(0.95)
                    }
                },
                'recommendations': self._generate_recommendations(df),
                'generated_at': datetime.now().isoformat()
            }
            
            # Guardar reporte
            report_file = self.analysis_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            self.analyzer_logger.info(f"📋 Reporte de rendimiento generado: {report_file}")
            
            return report
            
        except Exception as e:
            self.analyzer_logger.error(f"Error generando reporte de rendimiento: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        # CPU recommendations
        if df['cpu_usage'].mean() > 70:
            recommendations.append("Considerar optimizar algoritmos o aumentar recursos de CPU")
        
        if df['cpu_usage'].std() > 20:
            recommendations.append("La variabilidad de CPU es alta, considerar balancear carga")
        
        # Memory recommendations
        if df['memory_usage'].mean() > 80:
            recommendations.append("Considerar aumentar memoria RAM o optimizar uso de memoria")
        
        if df['memory_usage'].max() > 95:
            recommendations.append("Se alcanzó uso crítico de memoria, revisar memory leaks")
        
        # GPU recommendations
        if 'gpu_usage' in df.columns and df['gpu_usage'].mean() > 80:
            recommendations.append("Considerar optimizar modelos o usar múltiples GPUs")
        
        if 'gpu_memory' in df.columns and df['gpu_memory'].max() > 95:
            recommendations.append("Se alcanzó uso crítico de memoria GPU, reducir batch size")
        
        # Load average recommendations
        if df['load_average'].mean() > 2:
            recommendations.append("La carga del sistema es alta, considerar distribuir procesos")
        
        return recommendations
    
    def optimize_resources(self) -> Dict[str, Any]:
        """Sugiere optimizaciones de recursos"""
        if not self.metrics_history:
            return {'error': 'No hay datos suficientes para optimización'}
        
        # Analizar patrones de uso
        recent_metrics = list(self.metrics_history)[-100:]  # Últimas 100 muestras
        
        cpu_usage = [m.cpu_usage for m in recent_metrics]
        memory_usage = [m.memory_usage for m in recent_metrics]
        
        optimizations = []
        
        # CPU optimizations
        if np.mean(cpu_usage) > 80:
            optimizations.append({
                'resource': 'CPU',
                'current_usage': np.mean(cpu_usage),
                'recommendation': 'Aumentar cores de CPU o optimizar algoritmos',
                'priority': 'high'
            })
        
        # Memory optimizations
        if np.mean(memory_usage) > 85:
            optimizations.append({
                'resource': 'Memory',
                'current_usage': np.mean(memory_usage),
                'recommendation': 'Aumentar RAM o optimizar uso de memoria',
                'priority': 'high'
            })
        
        # GPU optimizations
        gpu_usage = [m.gpu_usage for m in recent_metrics if m.gpu_usage is not None]
        if gpu_usage and np.mean(gpu_usage) > 85:
            optimizations.append({
                'resource': 'GPU',
                'current_usage': np.mean(gpu_usage),
                'recommendation': 'Optimizar modelos o usar múltiples GPUs',
                'priority': 'medium'
            })
        
        return {
            'optimizations': optimizations,
            'analysis_period': f"{len(recent_metrics)} muestras",
            'generated_at': datetime.now().isoformat()
        }

# Funciones de utilidad
def create_performance_analyzer(
    monitoring_interval: float = 5.0,
    history_size: int = 1000,
    alert_thresholds: Optional[Dict[str, float]] = None
) -> PerformanceAnalyzer:
    """Factory function para crear PerformanceAnalyzer"""
    return PerformanceAnalyzer(
        monitoring_interval=monitoring_interval,
        history_size=history_size,
        alert_thresholds=alert_thresholds
    )

def analyze_system_performance(duration_minutes: int = 10) -> Dict[str, Any]:
    """Analiza rendimiento del sistema por un período específico"""
    analyzer = create_performance_analyzer(monitoring_interval=1.0)
    
    try:
        # Iniciar monitoreo
        analyzer.start_monitoring()
        
        # Esperar duración especificada
        time.sleep(duration_minutes * 60)
        
        # Detener monitoreo
        analyzer.stop_monitoring()
        
        # Generar reporte
        return analyzer.generate_performance_report()
        
    except Exception as e:
        logger.error(f"Error en análisis de rendimiento: {e}")
        return {'error': str(e)}
    finally:
        analyzer.stop_monitoring()
