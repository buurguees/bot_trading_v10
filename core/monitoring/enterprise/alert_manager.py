# Ruta: core/monitoring/enterprise/alert_manager.py
# alert_manager.py - Gestor de alertas enterprise
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\alert_manager.py

"""
Gestor de alertas enterprise para el sistema de trading.

Características:
- Gestión centralizada de alertas
- Múltiples canales de notificación
- Escalamiento automático
- Supresión de alertas duplicadas
- Integración con Prometheus AlertManager
"""

import asyncio
import logging
import smtplib
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests
from collections import defaultdict, deque
import threading
import yaml

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Severidad de alertas"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Estado de alertas"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

@dataclass
class Alert:
    """Estructura de alerta"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    escalation_level: int = 0
    suppression_key: Optional[str] = None

@dataclass
class NotificationChannel:
    """Canal de notificación"""
    name: str
    type: str  # 'email', 'slack', 'discord', 'webhook'
    enabled: bool
    config: Dict[str, Any]
    escalation_delay_minutes: int = 0
    max_retries: int = 3

class AlertManager:
    """Gestor de alertas enterprise"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/enterprise/monitoring.yaml"
        self.config = self._load_config()
        
        # Estado del gestor
        self.active_alerts = {}
        self.alert_history = deque(maxlen=10000)
        self.suppression_rules = {}
        self.escalation_rules = {}
        
        # Canales de notificación
        self.notification_channels = {}
        self._setup_notification_channels()
        
        # Configurar directorios
        self.alerts_dir = Path("monitoring/alerts")
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Threading para procesamiento asíncrono
        self.alert_queue = asyncio.Queue()
        self.processing_task = None
        self.is_running = False
        
        # Estadísticas
        self.stats = {
            'total_alerts': 0,
            'active_alerts': 0,
            'resolved_alerts': 0,
            'suppressed_alerts': 0,
            'notifications_sent': 0,
            'notification_failures': 0
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'alerting': {
                'enabled': True,
                'suppression_window_minutes': 5,
                'escalation_enabled': True,
                'max_escalation_levels': 3,
                'channels': {
                    'email': {
                        'enabled': False,
                        'smtp_server': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'username': '',
                        'password': '',
                        'from_email': 'trading-bot@company.com',
                        'to_emails': ['admin@company.com']
                    },
                    'slack': {
                        'enabled': False,
                        'webhook_url': '',
                        'channel': '#trading-bot-alerts'
                    },
                    'discord': {
                        'enabled': False,
                        'webhook_url': '',
                        'username': 'TradingBot-Alerts'
                    }
                }
            }
        }
    
    def setup_logging(self):
        """Configura logging del gestor de alertas"""
        alert_logger = logging.getLogger(f"{__name__}.AlertManager")
        alert_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.alerts_dir / "alert_manager.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        alert_logger.addHandler(file_handler)
        self.alert_logger = alert_logger
    
    def _setup_notification_channels(self):
        """Configura canales de notificación"""
        channels_config = self.config.get('alerting', {}).get('channels', {})
        
        # Email channel
        if channels_config.get('email', {}).get('enabled', False):
            email_config = channels_config['email']
            self.notification_channels['email'] = NotificationChannel(
                name='email',
                type='email',
                enabled=True,
                config=email_config,
                escalation_delay_minutes=5
            )
        
        # Slack channel
        if channels_config.get('slack', {}).get('enabled', False):
            slack_config = channels_config['slack']
            self.notification_channels['slack'] = NotificationChannel(
                name='slack',
                type='slack',
                enabled=True,
                config=slack_config,
                escalation_delay_minutes=2
            )
        
        # Discord channel
        if channels_config.get('discord', {}).get('enabled', False):
            discord_config = channels_config['discord']
            self.notification_channels['discord'] = NotificationChannel(
                name='discord',
                type='discord',
                enabled=True,
                config=discord_config,
                escalation_delay_minutes=2
            )
    
    async def start(self):
        """Inicia el gestor de alertas"""
        if self.is_running:
            return
        
        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_alerts())
        
        self.alert_logger.info("🚨 Gestor de alertas iniciado")
    
    async def stop(self):
        """Detiene el gestor de alertas"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        self.alert_logger.info("🛑 Gestor de alertas detenido")
    
    async def _process_alerts(self):
        """Procesa alertas de la cola"""
        while self.is_running:
            try:
                # Procesar alerta de la cola
                alert = await asyncio.wait_for(
                    self.alert_queue.get(), timeout=1.0
                )
                
                await self._handle_alert(alert)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.alert_logger.error(f"Error procesando alerta: {e}")
    
    async def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        suppression_key: Optional[str] = None
    ) -> str:
        """Crea una nueva alerta"""
        alert_id = f"{source}_{int(time.time())}_{hash(title) % 10000}"
        
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata,
            suppression_key=suppression_key
        )
        
        # Verificar supresión
        if self._should_suppress_alert(alert):
            self.stats['suppressed_alerts'] += 1
            self.alert_logger.info(f"🚫 Alerta suprimida: {alert.title}")
            return alert_id
        
        # Agregar a la cola de procesamiento
        await self.alert_queue.put(alert)
        
        return alert_id
    
    def _should_suppress_alert(self, alert: Alert) -> bool:
        """Verifica si una alerta debe ser suprimida"""
        if not alert.suppression_key:
            return False
        
        # Verificar reglas de supresión
        suppression_window = self.config.get('alerting', {}).get('suppression_window_minutes', 5)
        cutoff_time = datetime.now() - timedelta(minutes=suppression_window)
        
        # Buscar alertas similares recientes
        for historical_alert in reversed(self.alert_history):
            if (historical_alert.suppression_key == alert.suppression_key and
                historical_alert.timestamp > cutoff_time):
                return True
        
        return False
    
    async def _handle_alert(self, alert: Alert):
        """Maneja una alerta individual"""
        try:
            # Agregar a alertas activas
            self.active_alerts[alert.id] = alert
            
            # Agregar al historial
            self.alert_history.append(alert)
            
            # Actualizar estadísticas
            self.stats['total_alerts'] += 1
            self.stats['active_alerts'] = len(self.active_alerts)
            
            # Log de la alerta
            severity_emoji = {
                AlertSeverity.INFO: 'ℹ️',
                AlertSeverity.WARNING: '⚠️',
                AlertSeverity.ERROR: '❌',
                AlertSeverity.CRITICAL: '🚨'
            }
            
            emoji = severity_emoji.get(alert.severity, '⚠️')
            self.alert_logger.warning(
                f"{emoji} {alert.severity.value.upper()} - {alert.title}: {alert.message}"
            )
            
            # Enviar notificaciones
            await self._send_notifications(alert)
            
            # Configurar escalamiento si está habilitado
            if self.config.get('alerting', {}).get('escalation_enabled', True):
                await self._schedule_escalation(alert)
            
            # Guardar alerta
            await self._save_alert(alert)
            
        except Exception as e:
            self.alert_logger.error(f"Error manejando alerta {alert.id}: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """Envía notificaciones para una alerta"""
        for channel_name, channel in self.notification_channels.items():
            if not channel.enabled:
                continue
            
            try:
                await self._send_notification(alert, channel)
                self.stats['notifications_sent'] += 1
                
            except Exception as e:
                self.stats['notification_failures'] += 1
                self.alert_logger.error(f"Error enviando notificación por {channel_name}: {e}")
    
    async def _send_notification(self, alert: Alert, channel: NotificationChannel):
        """Envía notificación por un canal específico"""
        if channel.type == 'email':
            await self._send_email_notification(alert, channel)
        elif channel.type == 'slack':
            await self._send_slack_notification(alert, channel)
        elif channel.type == 'discord':
            await self._send_discord_notification(alert, channel)
    
    async def _send_email_notification(self, alert: Alert, channel: NotificationChannel):
        """Envía notificación por email"""
        config = channel.config
        
        # Crear mensaje
        subject = f"[{alert.severity.value.upper()}] {alert.title}"
        body = f"""
        Alerta del Trading Bot
        
        Título: {alert.title}
        Mensaje: {alert.message}
        Severidad: {alert.severity.value.upper()}
        Fuente: {alert.source}
        Timestamp: {alert.timestamp.isoformat()}
        
        ID de Alerta: {alert.id}
        """
        
        # Enviar email
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['username'], config['password'])
            
            for to_email in config['to_emails']:
                message = f"Subject: {subject}\n\n{body}"
                server.sendmail(config['from_email'], to_email, message)
    
    async def _send_slack_notification(self, alert: Alert, channel: NotificationChannel):
        """Envía notificación a Slack"""
        config = channel.config
        
        # Crear payload
        severity_colors = {
            AlertSeverity.INFO: '#36a64f',
            AlertSeverity.WARNING: '#ff9500',
            AlertSeverity.ERROR: '#ff0000',
            AlertSeverity.CRITICAL: '#8b0000'
        }
        
        payload = {
            'channel': config['channel'],
            'username': 'TradingBot-Alerts',
            'attachments': [{
                'color': severity_colors.get(alert.severity, '#ff9500'),
                'title': alert.title,
                'text': alert.message,
                'fields': [
                    {'title': 'Severidad', 'value': alert.severity.value.upper(), 'short': True},
                    {'title': 'Fuente', 'value': alert.source, 'short': True},
                    {'title': 'Timestamp', 'value': alert.timestamp.isoformat(), 'short': False},
                    {'title': 'ID', 'value': alert.id, 'short': True}
                ],
                'footer': 'Trading Bot Enterprise',
                'ts': int(alert.timestamp.timestamp())
            }]
        }
        
        # Enviar a Slack
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
    
    async def _send_discord_notification(self, alert: Alert, channel: NotificationChannel):
        """Envía notificación a Discord"""
        config = channel.config
        
        # Crear embed
        severity_colors = {
            AlertSeverity.INFO: 0x36a64f,
            AlertSeverity.WARNING: 0xff9500,
            AlertSeverity.ERROR: 0xff0000,
            AlertSeverity.CRITICAL: 0x8b0000
        }
        
        embed = {
            'title': alert.title,
            'description': alert.message,
            'color': severity_colors.get(alert.severity, 0xff9500),
            'fields': [
                {'name': 'Severidad', 'value': alert.severity.value.upper(), 'inline': True},
                {'name': 'Fuente', 'value': alert.source, 'inline': True},
                {'name': 'Timestamp', 'value': alert.timestamp.isoformat(), 'inline': False},
                {'name': 'ID', 'value': alert.id, 'inline': True}
            ],
            'footer': {'text': 'Trading Bot Enterprise'},
            'timestamp': alert.timestamp.isoformat()
        }
        
        payload = {
            'username': config.get('username', 'TradingBot-Alerts'),
            'embeds': [embed]
        }
        
        # Enviar a Discord
        response = requests.post(config['webhook_url'], json=payload)
        response.raise_for_status()
    
    async def _schedule_escalation(self, alert: Alert):
        """Programa escalamiento de alerta"""
        if alert.escalation_level >= self.config.get('alerting', {}).get('max_escalation_levels', 3):
            return
        
        # Calcular delay de escalamiento
        escalation_delay = 5 * (2 ** alert.escalation_level)  # 5, 10, 20 minutos
        
        # Programar escalamiento
        asyncio.create_task(self._escalate_alert(alert, escalation_delay))
    
    async def _escalate_alert(self, alert: Alert, delay_seconds: int):
        """Escalama una alerta después del delay"""
        await asyncio.sleep(delay_seconds)
        
        # Verificar si la alerta sigue activa
        if alert.id not in self.active_alerts:
            return
        
        # Incrementar nivel de escalamiento
        alert.escalation_level += 1
        
        # Crear alerta de escalamiento
        escalation_alert = Alert(
            id=f"{alert.id}_escalation_{alert.escalation_level}",
            title=f"[ESCALADO] {alert.title}",
            message=f"Alerta escalada al nivel {alert.escalation_level}: {alert.message}",
            severity=alert.severity,
            source=alert.source,
            timestamp=datetime.now(),
            metadata=alert.metadata,
            suppression_key=alert.suppression_key
        )
        
        # Procesar escalamiento
        await self._handle_alert(escalation_alert)
    
    async def _save_alert(self, alert: Alert):
        """Guarda alerta en archivo"""
        try:
            alert_file = self.alerts_dir / f"alert_{alert.id}.json"
            with open(alert_file, 'w') as f:
                json.dump(asdict(alert), f, indent=2, default=str)
        except Exception as e:
            self.alert_logger.error(f"Error guardando alerta {alert.id}: {e}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Reconoce una alerta"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        self.alert_logger.info(f"✅ Alerta reconocida: {alert.title} por {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resuelve una alerta"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        # Remover de alertas activas
        del self.active_alerts[alert_id]
        
        # Actualizar estadísticas
        self.stats['resolved_alerts'] += 1
        self.stats['active_alerts'] = len(self.active_alerts)
        
        self.alert_logger.info(f"✅ Alerta resuelta: {alert.title}")
        return True
    
    def get_active_alerts(self) -> List[Alert]:
        """Obtiene alertas activas"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Obtiene historial de alertas"""
        return list(self.alert_history)[-limit:]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de alertas"""
        return {
            'stats': self.stats.copy(),
            'active_alerts_count': len(self.active_alerts),
            'notification_channels': len(self.notification_channels),
            'is_running': self.is_running
        }
    
    def get_alerts_by_severity(self) -> Dict[str, int]:
        """Obtiene conteo de alertas por severidad"""
        severity_counts = defaultdict(int)
        
        for alert in self.active_alerts.values():
            severity_counts[alert.severity.value] += 1
        
        return dict(severity_counts)

# Funciones de utilidad
def create_alert_manager(config_path: Optional[str] = None) -> AlertManager:
    """Factory function para crear AlertManager"""
    return AlertManager(config_path)

async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity,
    source: str,
    alert_manager: Optional[AlertManager] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Envía una alerta usando el gestor de alertas"""
    if alert_manager is None:
        alert_manager = create_alert_manager()
        await alert_manager.start()
    
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=severity,
        source=source,
        metadata=metadata
    )

# Decorador para alertas automáticas
def alert_on_exception(severity: AlertSeverity = AlertSeverity.ERROR, source: str = "system"):
    """Decorador para enviar alertas automáticamente en excepciones"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Enviar alerta
                await send_alert(
                    title=f"Excepción en {func.__name__}",
                    message=str(e),
                    severity=severity,
                    source=source,
                    metadata={'function': func.__name__, 'args': str(args), 'kwargs': str(kwargs)}
                )
                raise
        return wrapper
    return decorator
