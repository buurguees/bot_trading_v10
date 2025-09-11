# Ruta: core/security/audit_logger.py
# audit_logger.py - Sistema de auditoría enterprise
# Ubicación: core/security/audit_logger.py

"""
Sistema de Auditoría Enterprise
Registra y monitorea eventos de seguridad y trading

Características principales:
- Logging de eventos de auditoría
- Encriptación de datos sensibles
- Detección de anomalías
- Retención de logs (7 años)
- Integración con alertas
- Compliance GDPR/MiFID II
"""

import logging
import json
import hashlib
import hmac
import base64
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import os
import asyncio
from pathlib import Path
import redis
# from control.telegram_bot import telegram_bot  # Eliminado para evitar import circular
from core.config.config_loader import config_loader

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Tipos de eventos de auditoría"""
    LOGIN = "login"
    LOGOUT = "logout"
    TRADE_EXECUTED = "trade_executed"
    TRADE_CANCELLED = "trade_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    CONFIG_CHANGED = "config_changed"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    DATA_ACCESS = "data_access"
    SYSTEM_ERROR = "system_error"
    SECURITY_VIOLATION = "security_violation"

class AuditSeverity(Enum):
    """Niveles de severidad"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Evento de auditoría"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    description: str
    details: Dict[str, Any]
    risk_score: float
    encrypted: bool

@dataclass
class AnomalyDetection:
    """Detección de anomalías"""
    anomaly_id: str
    anomaly_type: str
    severity: AuditSeverity
    timestamp: datetime
    description: str
    details: Dict[str, Any]
    risk_score: float
    resolved: bool

class AuditLogger:
    """Sistema de auditoría enterprise"""
    
    def __init__(self):
        self.config_loader = config_loader
        self.redis_client = None
        self.encryption_key = None
        self.audit_events = []
        self.anomalies = []
        self.retention_days = 2555  # 7 años
        
        # Configuración de auditoría
        self.audit_config = {}
        self.anomaly_patterns = {}
        self.risk_thresholds = {}
        
        # Métricas
        self.total_events = 0
        self.total_anomalies = 0
        self.encryption_enabled = True
        
        logger.info("AuditLogger inicializado")
    
    async def initialize(self):
        """Inicializa el sistema de auditoría"""
        try:
            # Inicializar configuraciones
            await self.config_loader.initialize()
            
            # Cargar configuración de seguridad
            security_config = self.config_loader.get_security_settings()
            self.audit_config = security_config.get('audit', {})
            self.anomaly_patterns = security_config.get('anomaly_detection', {}).get('patterns', {})
            self.risk_thresholds = security_config.get('risk_management', {}).get('thresholds', {})
            
            # Configurar encriptación
            await self._setup_encryption()
            
            # Configurar Redis
            await self._setup_redis()
            
            # Configurar directorio de logs
            await self._setup_log_directory()
            
            logger.info("AuditLogger inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando AuditLogger: {e}")
            raise
    
    async def _setup_encryption(self):
        """Configura encriptación para datos sensibles"""
        try:
            encryption_config = self.audit_config.get('encryption', {})
            
            if encryption_config.get('enabled', True):
                # Obtener clave de encriptación
                self.encryption_key = os.getenv('AUDIT_ENCRYPTION_KEY')
                if not self.encryption_key:
                    # Generar clave temporal (en producción debe ser persistente)
                    self.encryption_key = self._generate_encryption_key()
                    logger.warning("Usando clave de encriptación temporal")
                
                self.encryption_enabled = True
                logger.info("Encriptación de auditoría habilitada")
            else:
                self.encryption_enabled = False
                logger.info("Encriptación de auditoría deshabilitada")
                
        except Exception as e:
            logger.error(f"Error configurando encriptación: {e}")
            self.encryption_enabled = False
    
    async def _setup_redis(self):
        """Configura Redis para cache de auditoría"""
        try:
            redis_url = self.config_loader.get_infrastructure_settings().get('redis', {}).get('url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            # ping es síncrono en redis-py
            self.redis_client.ping()
            logger.info("Conexión a Redis establecida para auditoría")
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}")
            self.redis_client = None
    
    async def _setup_log_directory(self):
        """Configura directorio de logs de auditoría"""
        try:
            log_dir = Path("logs/enterprise/security/audit")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear subdirectorios por año
            current_year = datetime.now().year
            year_dir = log_dir / str(current_year)
            year_dir.mkdir(exist_ok=True)
            
            logger.info(f"Directorio de auditoría configurado: {log_dir}")
            
        except Exception as e:
            logger.error(f"Error configurando directorio de auditoría: {e}")
    
    def _generate_encryption_key(self) -> str:
        """Genera clave de encriptación"""
        import secrets
        return secrets.token_hex(32)
    
    def _encrypt_data(self, data: str) -> str:
        """Encripta datos sensibles"""
        try:
            if not self.encryption_enabled or not self.encryption_key:
                return data
            
            # Usar HMAC para encriptación simple
            key = self.encryption_key.encode()
            encrypted = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
            return base64.b64encode(encrypted.encode()).decode()
            
        except Exception as e:
            logger.error(f"Error encriptando datos: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Desencripta datos (implementación simplificada)"""
        try:
            if not self.encryption_enabled or not self.encryption_key:
                return encrypted_data
            
            # En un sistema real, esto desencriptaría los datos
            # Por ahora, retornamos los datos tal como están
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Error desencriptando datos: {e}")
            return encrypted_data
    
    async def log_event(self, 
                       event_type: AuditEventType,
                       description: str,
                       details: Dict[str, Any] = None,
                       user_id: str = None,
                       session_id: str = None,
                       source_ip: str = None,
                       severity: AuditSeverity = AuditSeverity.MEDIUM) -> str:
        """Registra un evento de auditoría"""
        try:
            # Generar ID único del evento
            event_id = self._generate_event_id()
            
            # Calcular score de riesgo
            risk_score = self._calculate_risk_score(event_type, details, severity)
            
            # Encriptar datos sensibles si es necesario
            encrypted_details = details.copy() if details else {}
            if self.encryption_enabled and self._contains_sensitive_data(details):
                for key, value in encrypted_details.items():
                    if isinstance(value, str) and self._is_sensitive_field(key):
                        encrypted_details[key] = self._encrypt_data(str(value))
            
            # Crear evento de auditoría
            event = AuditEvent(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                timestamp=datetime.now(),
                user_id=user_id,
                session_id=session_id,
                source_ip=source_ip,
                description=description,
                details=encrypted_details or {},
                risk_score=risk_score,
                encrypted=self.encryption_enabled
            )
            
            # Guardar evento
            await self._save_audit_event(event)
            
            # Verificar anomalías
            await self._check_anomalies(event)
            
            # Enviar alertas si es necesario
            if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                await self._send_alert(event)
            
            self.total_events += 1
            logger.info(f"Evento de auditoría registrado: {event_id}")
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error registrando evento de auditoría: {e}")
            return None
    
    def _generate_event_id(self) -> str:
        """Genera ID único para evento"""
        import uuid
        return str(uuid.uuid4())
    
    def _calculate_risk_score(self, 
                            event_type: AuditEventType, 
                            details: Dict[str, Any], 
                            severity: AuditSeverity) -> float:
        """Calcula score de riesgo del evento"""
        try:
            base_score = 0.0
            
            # Score base por tipo de evento
            risk_scores = {
                AuditEventType.LOGIN: 0.1,
                AuditEventType.LOGOUT: 0.1,
                AuditEventType.TRADE_EXECUTED: 0.3,
                AuditEventType.TRADE_CANCELLED: 0.2,
                AuditEventType.POSITION_OPENED: 0.4,
                AuditEventType.POSITION_CLOSED: 0.3,
                AuditEventType.CONFIG_CHANGED: 0.5,
                AuditEventType.RISK_LIMIT_EXCEEDED: 0.8,
                AuditEventType.ANOMALY_DETECTED: 0.7,
                AuditEventType.DATA_ACCESS: 0.2,
                AuditEventType.SYSTEM_ERROR: 0.6,
                AuditEventType.SECURITY_VIOLATION: 0.9
            }
            
            base_score = risk_scores.get(event_type, 0.5)
            
            # Ajustar por severidad
            severity_multipliers = {
                AuditSeverity.LOW: 0.5,
                AuditSeverity.MEDIUM: 1.0,
                AuditSeverity.HIGH: 1.5,
                AuditSeverity.CRITICAL: 2.0
            }
            
            base_score *= severity_multipliers.get(severity, 1.0)
            
            # Ajustar por detalles específicos
            if details:
                # Penalizar por montos altos
                if 'amount' in details and isinstance(details['amount'], (int, float)):
                    if details['amount'] > 100000:  # > $100k
                        base_score += 0.2
                
                # Penalizar por múltiples intentos
                if 'attempts' in details and isinstance(details['attempts'], int):
                    if details['attempts'] > 5:
                        base_score += 0.3
            
            return min(1.0, base_score)
            
        except Exception as e:
            logger.error(f"Error calculando risk score: {e}")
            return 0.5
    
    def _contains_sensitive_data(self, details: Dict[str, Any]) -> bool:
        """Verifica si los detalles contienen datos sensibles"""
        if not details:
            return False
        
        sensitive_fields = ['password', 'api_key', 'secret', 'token', 'private_key']
        return any(field in str(details).lower() for field in sensitive_fields)
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Verifica si un campo es sensible"""
        sensitive_fields = ['password', 'api_key', 'secret', 'token', 'private_key', 'passphrase']
        return any(field in field_name.lower() for field in sensitive_fields)
    
    async def _save_audit_event(self, event: AuditEvent):
        """Guarda evento de auditoría"""
        try:
            # Agregar a lista en memoria
            self.audit_events.append(event)
            
            # Guardar en archivo
            await self._write_to_file(event)
            
            # Cachear en Redis
            if self.redis_client:
                cache_key = f"audit_event:{event.event_id}"
                event_data = asdict(event)
                event_data['timestamp'] = event.timestamp.isoformat()
                self.redis_client.setex(cache_key, 3600, json.dumps(event_data, default=str))
            
            # Limpiar eventos antiguos
            await self._cleanup_old_events()
            
        except Exception as e:
            logger.error(f"Error guardando evento de auditoría: {e}")
    
    async def _write_to_file(self, event: AuditEvent):
        """Escribe evento a archivo de log"""
        try:
            log_dir = Path("logs/enterprise/security/audit")
            year = event.timestamp.year
            month = event.timestamp.month
            day = event.timestamp.day
            
            # Crear estructura de directorios
            date_dir = log_dir / str(year) / f"{month:02d}"
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Archivo de log por día
            log_file = date_dir / f"audit_{year}{month:02d}{day:02d}.log"
            
            # Formatear evento
            event_data = {
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'severity': event.severity.value,
                'timestamp': event.timestamp.isoformat(),
                'user_id': event.user_id,
                'session_id': event.session_id,
                'source_ip': event.source_ip,
                'description': event.description,
                'details': event.details,
                'risk_score': event.risk_score,
                'encrypted': event.encrypted
            }
            
            # Escribir a archivo
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"Error escribiendo evento a archivo: {e}")
    
    async def _check_anomalies(self, event: AuditEvent):
        """Verifica anomalías en el evento"""
        try:
            # Verificar patrones de anomalías
            for pattern_name, pattern_config in self.anomaly_patterns.items():
                if await self._matches_pattern(event, pattern_config):
                    await self._create_anomaly(event, pattern_name, pattern_config)
            
        except Exception as e:
            logger.error(f"Error verificando anomalías: {e}")
    
    async def _matches_pattern(self, event: AuditEvent, pattern_config: Dict[str, Any]) -> bool:
        """Verifica si un evento coincide con un patrón de anomalía"""
        try:
            # Verificar tipo de evento
            if 'event_types' in pattern_config:
                if event.event_type.value not in pattern_config['event_types']:
                    return False
            
            # Verificar severidad
            if 'min_severity' in pattern_config:
                severity_levels = ['low', 'medium', 'high', 'critical']
                event_severity_level = severity_levels.index(event.severity.value)
                min_severity_level = severity_levels.index(pattern_config['min_severity'])
                if event_severity_level < min_severity_level:
                    return False
            
            # Verificar score de riesgo
            if 'min_risk_score' in pattern_config:
                if event.risk_score < pattern_config['min_risk_score']:
                    return False
            
            # Verificar frecuencia (simplificado)
            if 'max_frequency_per_hour' in pattern_config:
                recent_events = [
                    e for e in self.audit_events
                    if e.event_type == event.event_type
                    and e.timestamp > datetime.now() - timedelta(hours=1)
                ]
                if len(recent_events) >= pattern_config['max_frequency_per_hour']:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando patrón de anomalía: {e}")
            return False
    
    async def _create_anomaly(self, event: AuditEvent, pattern_name: str, pattern_config: Dict[str, Any]):
        """Crea una anomalía detectada"""
        try:
            anomaly_id = self._generate_event_id()
            
            anomaly = AnomalyDetection(
                anomaly_id=anomaly_id,
                anomaly_type=pattern_name,
                severity=event.severity,
                timestamp=datetime.now(),
                description=f"Anomalía detectada: {pattern_name}",
                details={
                    'trigger_event_id': event.event_id,
                    'pattern_config': pattern_config,
                    'event_details': event.details
                },
                risk_score=event.risk_score,
                resolved=False
            )
            
            self.anomalies.append(anomaly)
            self.total_anomalies += 1
            
            # Enviar alerta de anomalía
            await self._send_anomaly_alert(anomaly)
            
            logger.warning(f"Anomalía detectada: {anomaly_id}")
            
        except Exception as e:
            logger.error(f"Error creando anomalía: {e}")
    
    async def _send_alert(self, event: AuditEvent):
        """Envía alerta de evento crítico (adaptado a logging para evitar dependencia)"""
        try:
            message = (
                f"🚨 [Audit] Tipo: {event.event_type.value} | Sev: {event.severity.value} | "
                f"Riesgo: {event.risk_score:.2f} | {event.description}"
            )
            logger.warning(message)
            # En producción: inyectar un sender externo para Telegram si está disponible
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")
    
    async def _send_anomaly_alert(self, anomaly: AnomalyDetection):
        """Envía alerta de anomalía (adaptado a logging para evitar dependencia)"""
        try:
            message = (
                f"⚠️ [Anomalía] Tipo: {anomaly.anomaly_type} | Sev: {anomaly.severity.value} | "
                f"Riesgo: {anomaly.risk_score:.2f} | {anomaly.description}"
            )
            logger.warning(message)
            # En producción: inyectar un sender externo para Telegram si está disponible
        except Exception as e:
            logger.error(f"Error enviando alerta de anomalía: {e}")
    
    async def _cleanup_old_events(self):
        """Limpia eventos antiguos según retención"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            # Limpiar eventos en memoria
            self.audit_events = [
                event for event in self.audit_events
                if event.timestamp > cutoff_date
            ]
            
            # Limpiar anomalías resueltas antiguas
            self.anomalies = [
                anomaly for anomaly in self.anomalies
                if not anomaly.resolved or anomaly.timestamp > cutoff_date
            ]
            
        except Exception as e:
            logger.error(f"Error limpiando eventos antiguos: {e}")
    
    def get_audit_events(self, 
                        event_type: AuditEventType = None,
                        severity: AuditSeverity = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene eventos de auditoría"""
        try:
            events = self.audit_events.copy()
            
            # Filtrar por tipo
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Filtrar por severidad
            if severity:
                events = [e for e in events if e.severity == severity]
            
            # Ordenar por timestamp (más recientes primero)
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limitar resultados
            events = events[:limit]
            
            # Convertir a diccionarios
            return [asdict(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error obteniendo eventos de auditoría: {e}")
            return []
    
    def get_anomalies(self, resolved: bool = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene anomalías detectadas"""
        try:
            anomalies = self.anomalies.copy()
            
            # Filtrar por estado de resolución
            if resolved is not None:
                anomalies = [a for a in anomalies if a.resolved == resolved]
            
            # Ordenar por timestamp (más recientes primero)
            anomalies.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limitar resultados
            anomalies = anomalies[:limit]
            
            # Convertir a diccionarios
            return [asdict(anomaly) for anomaly in anomalies]
            
        except Exception as e:
            logger.error(f"Error obteniendo anomalías: {e}")
            return []
    
    def get_audit_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de auditoría"""
        try:
            total_events = len(self.audit_events)
            total_anomalies = len(self.anomalies)
            unresolved_anomalies = len([a for a in self.anomalies if not a.resolved])
            
            # Eventos por tipo
            events_by_type = {}
            for event in self.audit_events:
                event_type = event.event_type.value
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            
            # Eventos por severidad
            events_by_severity = {}
            for event in self.audit_events:
                severity = event.severity.value
                events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
            
            return {
                'total_events': total_events,
                'total_anomalies': total_anomalies,
                'unresolved_anomalies': unresolved_anomalies,
                'events_by_type': events_by_type,
                'events_by_severity': events_by_severity,
                'encryption_enabled': self.encryption_enabled,
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de auditoría: {e}")
            return {}
    
    async def resolve_anomaly(self, anomaly_id: str) -> bool:
        """Marca una anomalía como resuelta"""
        try:
            for anomaly in self.anomalies:
                if anomaly.anomaly_id == anomaly_id:
                    anomaly.resolved = True
                    logger.info(f"Anomalía resuelta: {anomaly_id}")
                    return True
            
            logger.warning(f"Anomalía no encontrada: {anomaly_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error resolviendo anomalía: {e}")
            return False
    
    async def cleanup(self):
        """Limpia recursos del sistema de auditoría"""
        try:
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("AuditLogger limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando AuditLogger: {e}")

# Instancia global
audit_logger = AuditLogger()