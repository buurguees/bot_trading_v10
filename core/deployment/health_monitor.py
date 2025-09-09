#!/usr/bin/env python3
"""
Monitor de Salud Enterprise - Monitoreo del Sistema
==================================================

Este módulo monitorea la salud del sistema enterprise (CPU, memoria, disco, servicios)
y expone métricas a Prometheus para alertas y dashboards.

Características:
- Monitoreo de recursos del sistema
- Verificación de servicios críticos
- Métricas de Prometheus
- Alertas automáticas
- Health checks para Kubernetes

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from prometheus_client import Gauge, Counter, Histogram, start_http_server
from prometheus_client.core import CollectorRegistry

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Estados de salud del sistema"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthMetric:
    """Métrica de salud individual"""
    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    status: HealthStatus
    description: str

@dataclass
class SystemHealth:
    """Estado general de salud del sistema"""
    timestamp: datetime
    overall_status: HealthStatus
    overall_score: float
    critical_issues: int
    warning_issues: int
    metrics: List[HealthMetric]
    services_status: Dict[str, bool]
    uptime_seconds: float
    recommendations: List[str]

class HealthMonitor:
    """Monitor de salud del sistema enterprise"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Configuración de umbrales
        self.thresholds = self.config.get('health_thresholds', {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0,
            'load_warning': 2.0,
            'load_critical': 5.0
        })
        
        # Configuración de servicios a monitorear
        self.services = self.config.get('monitored_services', [
            'trading_bot',
            'prometheus',
            'grafana',
            'redis',
            'postgresql',
            'kafka'
        ])
        
        # Estado del monitor
        self.is_monitoring = False
        self.start_time = datetime.now()
        self.health_history = []
        self.max_history = 1000
        
        # Métricas de Prometheus
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Configurar logging
        self.setup_logging()
        
        logger.info("🏥 HealthMonitor enterprise inicializado")
    
    def setup_logging(self):
        """Configura el logging para el monitor de salud"""
        log_dir = Path("logs/enterprise/health_monitoring")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logger específico para salud
        health_logger = logging.getLogger('health_monitor')
        health_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_dir / 'health_monitor.log')
        file_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        health_logger.addHandler(file_handler)
    
    def _setup_prometheus_metrics(self):
        """Configura las métricas de Prometheus"""
        # Métricas de salud general
        self.health_score_gauge = Gauge(
            'trading_bot_health_score',
            'Puntuación general de salud del sistema (0-100)',
            registry=self.registry
        )
        
        self.health_status_gauge = Gauge(
            'trading_bot_health_status',
            'Estado de salud del sistema (0=healthy, 1=warning, 2=critical)',
            registry=self.registry
        )
        
        # Métricas de recursos del sistema
        self.cpu_usage_gauge = Gauge(
            'trading_bot_cpu_percent',
            'Uso de CPU en porcentaje',
            registry=self.registry
        )
        
        self.memory_usage_gauge = Gauge(
            'trading_bot_memory_percent',
            'Uso de memoria en porcentaje',
            registry=self.registry
        )
        
        self.disk_usage_gauge = Gauge(
            'trading_bot_disk_percent',
            'Uso de disco en porcentaje',
            registry=self.registry
        )
        
        self.load_average_gauge = Gauge(
            'trading_bot_load_average',
            'Carga promedio del sistema',
            registry=self.registry
        )
        
        # Métricas de servicios
        self.service_status_gauge = Gauge(
            'trading_bot_service_status',
            'Estado de servicios (1=up, 0=down)',
            ['service_name'],
            registry=self.registry
        )
        
        # Contadores de problemas
        self.critical_issues_counter = Counter(
            'trading_bot_critical_issues_total',
            'Número total de problemas críticos detectados',
            registry=self.registry
        )
        
        self.warning_issues_counter = Counter(
            'trading_bot_warning_issues_total',
            'Número total de advertencias detectadas',
            registry=self.registry
        )
        
        # Histogramas
        self.response_time_histogram = Histogram(
            'trading_bot_health_check_duration_seconds',
            'Tiempo de respuesta de health checks',
            ['check_type'],
            registry=self.registry
        )
    
    async def start_monitoring(self, port: int = 8001):
        """Inicia el monitoreo continuo de salud"""
        try:
            logger.info("🚀 Iniciando monitoreo de salud del sistema...")
            
            # Iniciar servidor Prometheus
            start_http_server(port, registry=self.registry)
            logger.info(f"📊 Servidor Prometheus iniciado en puerto {port}")
            
            self.is_monitoring = True
            self.start_time = datetime.now()
            
            # Loop principal de monitoreo
            while self.is_monitoring:
                try:
                    # Realizar health check
                    health_status = await self.get_system_health()
                    
                    # Actualizar métricas de Prometheus
                    self.update_prometheus_metrics(health_status)
                    
                    # Guardar en historial
                    self.health_history.append(health_status)
                    if len(self.health_history) > self.max_history:
                        self.health_history.pop(0)
                    
                    # Verificar alertas
                    await self.check_health_alerts(health_status)
                    
                    # Log estado si hay problemas
                    if health_status.overall_status != HealthStatus.HEALTHY:
                        logger.warning(f"⚠️ Estado de salud: {health_status.overall_status.value} (Score: {health_status.overall_score:.1f})")
                    
                    # Esperar antes del siguiente check
                    await asyncio.sleep(30)  # Check cada 30 segundos
                    
                except Exception as e:
                    logger.error(f"❌ Error en loop de monitoreo: {e}")
                    await asyncio.sleep(60)  # Esperar más tiempo en caso de error
            
        except Exception as e:
            logger.error(f"❌ Error iniciando monitoreo: {e}")
        finally:
            self.is_monitoring = False
    
    async def get_system_health(self) -> SystemHealth:
        """Obtiene el estado actual de salud del sistema"""
        try:
            start_time = time.time()
            
            # Obtener métricas del sistema
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            
            # Calcular uptime
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Crear métricas individuales
            metrics = [
                HealthMetric(
                    name="cpu_usage",
                    value=cpu_percent,
                    threshold_warning=self.thresholds['cpu_warning'],
                    threshold_critical=self.thresholds['cpu_critical'],
                    unit="percent",
                    status=self._get_metric_status(cpu_percent, self.thresholds['cpu_warning'], self.thresholds['cpu_critical']),
                    description="Uso de CPU"
                ),
                HealthMetric(
                    name="memory_usage",
                    value=memory.percent,
                    threshold_warning=self.thresholds['memory_warning'],
                    threshold_critical=self.thresholds['memory_critical'],
                    unit="percent",
                    status=self._get_metric_status(memory.percent, self.thresholds['memory_warning'], self.thresholds['memory_critical']),
                    description="Uso de memoria"
                ),
                HealthMetric(
                    name="disk_usage",
                    value=disk.percent,
                    threshold_warning=self.thresholds['disk_warning'],
                    threshold_critical=self.thresholds['disk_critical'],
                    unit="percent",
                    status=self._get_metric_status(disk.percent, self.thresholds['disk_warning'], self.thresholds['disk_critical']),
                    description="Uso de disco"
                ),
                HealthMetric(
                    name="load_average",
                    value=load_avg,
                    threshold_warning=self.thresholds['load_warning'],
                    threshold_critical=self.thresholds['load_critical'],
                    unit="load",
                    status=self._get_metric_status(load_avg, self.thresholds['load_warning'], self.thresholds['load_critical']),
                    description="Carga promedio del sistema"
                )
            ]
            
            # Verificar estado de servicios
            services_status = await self.check_services_status()
            
            # Calcular estado general
            critical_issues = len([m for m in metrics if m.status == HealthStatus.CRITICAL])
            warning_issues = len([m for m in metrics if m.status == HealthStatus.WARNING])
            
            # Calcular score de salud (0-100)
            overall_score = self._calculate_health_score(metrics, services_status)
            
            # Determinar estado general
            if critical_issues > 0:
                overall_status = HealthStatus.CRITICAL
            elif warning_issues > 0:
                overall_status = HealthStatus.WARNING
            else:
                overall_status = HealthStatus.HEALTHY
            
            # Generar recomendaciones
            recommendations = self._generate_recommendations(metrics, services_status)
            
            # Crear objeto de salud del sistema
            health_status = SystemHealth(
                timestamp=datetime.now(),
                overall_status=overall_status,
                overall_score=overall_score,
                critical_issues=critical_issues,
                warning_issues=warning_issues,
                metrics=metrics,
                services_status=services_status,
                uptime_seconds=uptime_seconds,
                recommendations=recommendations
            )
            
            # Registrar tiempo de respuesta
            response_time = time.time() - start_time
            self.response_time_histogram.labels(check_type='full').observe(response_time)
            
            return health_status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo salud del sistema: {e}")
            return SystemHealth(
                timestamp=datetime.now(),
                overall_status=HealthStatus.UNKNOWN,
                overall_score=0.0,
                critical_issues=1,
                warning_issues=0,
                metrics=[],
                services_status={},
                uptime_seconds=0.0,
                recommendations=[f"Error en health check: {str(e)}"]
            )
    
    def _get_metric_status(self, value: float, warning_threshold: float, critical_threshold: float) -> HealthStatus:
        """Determina el estado de una métrica basado en sus umbrales"""
        if value >= critical_threshold:
            return HealthStatus.CRITICAL
        elif value >= warning_threshold:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    async def check_services_status(self) -> Dict[str, bool]:
        """Verifica el estado de los servicios críticos"""
        services_status = {}
        
        for service in self.services:
            try:
                # Verificar si el servicio está ejecutándose
                # En implementación real, aquí se verificarían puertos, procesos, etc.
                is_running = await self._check_service_running(service)
                services_status[service] = is_running
                
            except Exception as e:
                logger.warning(f"⚠️ Error verificando servicio {service}: {e}")
                services_status[service] = False
        
        return services_status
    
    async def _check_service_running(self, service: str) -> bool:
        """Verifica si un servicio específico está ejecutándose"""
        try:
            # Simular verificación de servicios
            # En implementación real, aquí se verificarían:
            # - Procesos en ejecución
            # - Puertos abiertos
            # - Respuestas HTTP
            # - Conexiones a bases de datos
            
            if service == 'trading_bot':
                # Verificar que el proceso principal esté ejecutándose
                return True
            elif service == 'redis':
                # Verificar conexión a Redis
                return True
            elif service == 'postgresql':
                # Verificar conexión a PostgreSQL
                return True
            elif service == 'prometheus':
                # Verificar que Prometheus esté respondiendo
                return True
            elif service == 'grafana':
                # Verificar que Grafana esté respondiendo
                return True
            elif service == 'kafka':
                # Verificar que Kafka esté ejecutándose
                return True
            else:
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Error verificando servicio {service}: {e}")
            return False
    
    def _calculate_health_score(self, metrics: List[HealthMetric], services_status: Dict[str, bool]) -> float:
        """Calcula el score de salud general (0-100)"""
        try:
            if not metrics:
                return 0.0
            
            # Score basado en métricas del sistema (70% del peso)
            system_score = 100.0
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    system_score -= 30
                elif metric.status == HealthStatus.WARNING:
                    system_score -= 15
            
            # Score basado en servicios (30% del peso)
            if services_status:
                services_up = sum(1 for status in services_status.values() if status)
                services_score = (services_up / len(services_status)) * 100
            else:
                services_score = 100.0
            
            # Combinar scores
            overall_score = (system_score * 0.7) + (services_score * 0.3)
            
            return max(0.0, min(100.0, overall_score))
            
        except Exception as e:
            logger.error(f"❌ Error calculando health score: {e}")
            return 0.0
    
    def _generate_recommendations(self, metrics: List[HealthMetric], services_status: Dict[str, bool]) -> List[str]:
        """Genera recomendaciones basadas en el estado del sistema"""
        recommendations = []
        
        try:
            # Recomendaciones basadas en métricas
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    if metric.name == "cpu_usage":
                        recommendations.append("CPU crítico: Considerar escalar horizontalmente o optimizar código")
                    elif metric.name == "memory_usage":
                        recommendations.append("Memoria crítica: Aumentar RAM o optimizar uso de memoria")
                    elif metric.name == "disk_usage":
                        recommendations.append("Disco crítico: Limpiar archivos temporales o aumentar almacenamiento")
                    elif metric.name == "load_average":
                        recommendations.append("Carga crítica: Reducir carga de trabajo o escalar recursos")
                
                elif metric.status == HealthStatus.WARNING:
                    if metric.name == "cpu_usage":
                        recommendations.append("CPU alto: Monitorear de cerca y considerar optimizaciones")
                    elif metric.name == "memory_usage":
                        recommendations.append("Memoria alta: Revisar uso de memoria y considerar optimizaciones")
                    elif metric.name == "disk_usage":
                        recommendations.append("Disco alto: Planificar limpieza o expansión de almacenamiento")
                    elif metric.name == "load_average":
                        recommendations.append("Carga alta: Monitorear tendencias y considerar escalado")
            
            # Recomendaciones basadas en servicios
            services_down = [name for name, status in services_status.items() if not status]
            if services_down:
                recommendations.append(f"Servicios caídos: {', '.join(services_down)} - Verificar logs y reiniciar si es necesario")
            
            # Recomendaciones generales
            if not recommendations:
                recommendations.append("Sistema funcionando correctamente - Continuar monitoreo")
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones: {e}")
            recommendations.append(f"Error generando recomendaciones: {str(e)}")
        
        return recommendations
    
    def update_prometheus_metrics(self, health_status: SystemHealth):
        """Actualiza las métricas de Prometheus"""
        try:
            # Métricas generales
            self.health_score_gauge.set(health_status.overall_score)
            
            status_value = {
                HealthStatus.HEALTHY: 0,
                HealthStatus.WARNING: 1,
                HealthStatus.CRITICAL: 2,
                HealthStatus.UNKNOWN: 3
            }.get(health_status.overall_status, 3)
            self.health_status_gauge.set(status_value)
            
            # Métricas de recursos
            for metric in health_status.metrics:
                if metric.name == "cpu_usage":
                    self.cpu_usage_gauge.set(metric.value)
                elif metric.name == "memory_usage":
                    self.memory_usage_gauge.set(metric.value)
                elif metric.name == "disk_usage":
                    self.disk_usage_gauge.set(metric.value)
                elif metric.name == "load_average":
                    self.load_average_gauge.set(metric.value)
            
            # Métricas de servicios
            for service_name, status in health_status.services_status.items():
                self.service_status_gauge.labels(service_name=service_name).set(1 if status else 0)
            
            # Contadores de problemas
            if health_status.critical_issues > 0:
                self.critical_issues_counter.inc(health_status.critical_issues)
            if health_status.warning_issues > 0:
                self.warning_issues_counter.inc(health_status.warning_issues)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas de Prometheus: {e}")
    
    async def check_health_alerts(self, health_status: SystemHealth):
        """Verifica y envía alertas de salud"""
        try:
            # Alertas críticas
            if health_status.overall_status == HealthStatus.CRITICAL:
                logger.critical(f"🚨 ALERTA CRÍTICA: Sistema en estado crítico (Score: {health_status.overall_score:.1f})")
                await self._send_alert("CRITICAL", f"Sistema en estado crítico - Score: {health_status.overall_score:.1f}")
            
            # Alertas de advertencia
            elif health_status.overall_status == HealthStatus.WARNING:
                logger.warning(f"⚠️ ADVERTENCIA: Sistema en estado de advertencia (Score: {health_status.overall_score:.1f})")
                await self._send_alert("WARNING", f"Sistema en estado de advertencia - Score: {health_status.overall_score:.1f}")
            
            # Alertas de servicios caídos
            services_down = [name for name, status in health_status.services_status.items() if not status]
            if services_down:
                logger.warning(f"⚠️ SERVICIOS CAÍDOS: {', '.join(services_down)}")
                await self._send_alert("SERVICE_DOWN", f"Servicios caídos: {', '.join(services_down)}")
            
        except Exception as e:
            logger.error(f"❌ Error verificando alertas: {e}")
    
    async def _send_alert(self, alert_type: str, message: str):
        """Envía una alerta (implementación placeholder)"""
        try:
            # En implementación real, aquí se enviarían alertas por:
            # - Email
            # - Slack
            # - Webhook
            # - SMS
            # - PagerDuty
            
            logger.info(f"📢 ALERTA {alert_type}: {message}")
            
            # Guardar alerta en archivo
            alert_file = Path("logs/enterprise/health_monitoring/alerts.log")
            with open(alert_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {alert_type} - {message}\n")
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta: {e}")
    
    async def get_current_health(self) -> SystemHealth:
        """Obtiene el estado de salud actual"""
        return await self.get_system_health()
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """Obtiene el historial de salud de las últimas N horas"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [h for h in self.health_history if h.timestamp >= cutoff_time]
        except Exception as e:
            logger.error(f"❌ Error obteniendo historial de salud: {e}")
            return []
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen del estado de salud"""
        try:
            if not self.health_history:
                return {"error": "No hay datos de salud disponibles"}
            
            recent_health = self.health_history[-1] if self.health_history else None
            if not recent_health:
                return {"error": "No hay datos de salud recientes"}
            
            # Calcular estadísticas de las últimas 24 horas
            last_24h = self.get_health_history(24)
            
            avg_score = sum(h.overall_score for h in last_24h) / len(last_24h) if last_24h else 0
            min_score = min(h.overall_score for h in last_24h) if last_24h else 0
            max_score = max(h.overall_score for h in last_24h) if last_24h else 0
            
            # Contar problemas
            critical_count = sum(1 for h in last_24h if h.overall_status == HealthStatus.CRITICAL)
            warning_count = sum(1 for h in last_24h if h.overall_status == HealthStatus.WARNING)
            
            return {
                "current_status": recent_health.overall_status.value,
                "current_score": recent_health.overall_score,
                "uptime_hours": recent_health.uptime_seconds / 3600,
                "last_24h_stats": {
                    "avg_score": avg_score,
                    "min_score": min_score,
                    "max_score": max_score,
                    "critical_incidents": critical_count,
                    "warning_incidents": warning_count
                },
                "current_issues": {
                    "critical": recent_health.critical_issues,
                    "warning": recent_health.warning_issues
                },
                "services_status": recent_health.services_status,
                "recommendations": recent_health.recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de salud: {e}")
            return {"error": str(e)}
    
    async def stop_monitoring(self):
        """Detiene el monitoreo de salud"""
        try:
            logger.info("⏹️ Deteniendo monitoreo de salud...")
            self.is_monitoring = False
            logger.info("✅ Monitoreo de salud detenido")
        except Exception as e:
            logger.error(f"❌ Error deteniendo monitoreo: {e}")

# Instancia global
health_monitor = HealthMonitor()
