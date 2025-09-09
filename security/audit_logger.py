# audit_logger.py - Logger de auditoría enterprise
# Ubicación: C:\TradingBot_v10\security\audit_logger.py

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum

from config.enterprise_config import get_enterprise_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Tipos de eventos de auditoría"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    TRADING = "trading"
    SECURITY = "security"

class AuditSeverity(Enum):
    """Niveles de severidad de auditoría"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLogger:
    """Logger de auditoría enterprise"""
    
    def __init__(self):
        """Inicializar el logger de auditoría"""
        self.config = get_enterprise_config()
        self.security_config = self.config.get_security_config()
        self.audit_config = self.security_config.get("audit", {})
        
        # Configuración de auditoría
        self.enabled = self.audit_config.get("enabled", True)
        self.logging_config = self.audit_config.get("logging", {})
        self.events_config = self.audit_config.get("events", {})
        
        # Configuración de archivos
        self.log_path = self.logging_config.get("path", "logs/enterprise/security/audit.log")
        self.log_format = self.logging_config.get("format", "json")
        self.rotation_config = self.logging_config.get("rotation", {})
        
        # Configuración de rotación
        self.max_size_mb = self.rotation_config.get("max_size_mb", 50)
        self.max_files = self.rotation_config.get("max_files", 100)
        self.compression = self.rotation_config.get("compression", True)
        
        # Eventos a auditar
        self.audit_events = self._load_audit_events()
        
        # Configurar logger
        self._setup_logger()
        
        # Métricas
        self.metrics = {
            "events_logged_total": 0,
            "events_by_type": {},
            "events_by_severity": {},
            "events_failed": 0,
            "last_event_time": None,
            "errors_total": 0
        }
        
        logger.info("AuditLogger inicializado")
    
    def _load_audit_events(self) -> Dict[str, List[str]]:
        """Cargar eventos a auditar"""
        try:
            events = {}
            
            for event_type, event_list in self.events_config.items():
                if isinstance(event_list, list):
                    events[event_type] = event_list
                else:
                    events[event_type] = []
            
            return events
            
        except Exception as e:
            logger.error(f"Error cargando eventos de auditoría: {e}")
            return {}
    
    def _setup_logger(self):
        """Configurar logger de auditoría"""
        try:
            # Crear directorio de logs si no existe
            log_dir = Path(self.log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Configurar logger
            self.audit_logger = logging.getLogger("audit")
            self.audit_logger.setLevel(logging.INFO)
            
            # Evitar duplicación de handlers
            if not self.audit_logger.handlers:
                # Handler de archivo con rotación
                from logging.handlers import RotatingFileHandler
                
                file_handler = RotatingFileHandler(
                    self.log_path,
                    maxBytes=self.max_size_mb * 1024 * 1024,
                    backupCount=self.max_files,
                    encoding='utf-8'
                )
                
                # Formato de log
                if self.log_format == "json":
                    formatter = logging.Formatter('%(message)s')
                else:
                    formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                
                file_handler.setFormatter(formatter)
                self.audit_logger.addHandler(file_handler)
                
                # Evitar propagación al logger raíz
                self.audit_logger.propagate = False
            
            logger.info(f"Logger de auditoría configurado: {self.log_path}")
            
        except Exception as e:
            logger.error(f"Error configurando logger de auditoría: {e}")
            raise
    
    def log_event(self, 
                  event_type: AuditEventType,
                  event_name: str,
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None,
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  description: str = "",
                  metadata: Optional[Dict[str, Any]] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None):
        """Registrar evento de auditoría"""
        try:
            if not self.enabled:
                return
            
            # Verificar si el evento debe ser auditado
            if not self._should_audit_event(event_type, event_name):
                return
            
            # Crear evento de auditoría
            audit_event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type.value,
                "event_name": event_name,
                "user_id": user_id,
                "session_id": session_id,
                "severity": severity.value,
                "description": description,
                "metadata": metadata or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "source": "trading_bot_enterprise"
            }
            
            # Registrar evento
            if self.log_format == "json":
                self.audit_logger.info(json.dumps(audit_event, ensure_ascii=False))
            else:
                self.audit_logger.info(f"{event_type.value}:{event_name} - {description}")
            
            # Actualizar métricas
            self._update_metrics(event_type, severity)
            
            logger.debug(f"Evento de auditoría registrado: {event_name}")
            
        except Exception as e:
            logger.error(f"Error registrando evento de auditoría: {e}")
            self.metrics["events_failed"] += 1
            self.metrics["errors_total"] += 1
    
    def _should_audit_event(self, event_type: AuditEventType, event_name: str) -> bool:
        """Verificar si un evento debe ser auditado"""
        try:
            event_type_str = event_type.value
            if event_type_str in self.audit_events:
                return event_name in self.audit_events[event_type_str]
            return False
            
        except Exception as e:
            logger.error(f"Error verificando evento de auditoría: {e}")
            return False
    
    def _update_metrics(self, event_type: AuditEventType, severity: AuditSeverity):
        """Actualizar métricas de auditoría"""
        try:
            self.metrics["events_logged_total"] += 1
            self.metrics["last_event_time"] = datetime.now(timezone.utc)
            
            # Contar por tipo
            event_type_str = event_type.value
            if event_type_str not in self.metrics["events_by_type"]:
                self.metrics["events_by_type"][event_type_str] = 0
            self.metrics["events_by_type"][event_type_str] += 1
            
            # Contar por severidad
            severity_str = severity.value
            if severity_str not in self.metrics["events_by_severity"]:
                self.metrics["events_by_severity"][severity_str] = 0
            self.metrics["events_by_severity"][severity_str] += 1
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de auditoría: {e}")
    
    def log_authentication(self, event_name: str, user_id: str, success: bool, 
                          ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de autenticación"""
        severity = AuditSeverity.HIGH if not success else AuditSeverity.MEDIUM
        description = f"Autenticación {'exitosa' if success else 'fallida'} para usuario {user_id}"
        
        self.log_event(
            event_type=AuditEventType.AUTHENTICATION,
            event_name=event_name,
            user_id=user_id,
            severity=severity,
            description=description,
            metadata=metadata,
            ip_address=ip_address
        )
    
    def log_authorization(self, event_name: str, user_id: str, resource: str, 
                         granted: bool, ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de autorización"""
        severity = AuditSeverity.HIGH if not granted else AuditSeverity.MEDIUM
        description = f"Acceso {'otorgado' if granted else 'denegado'} a {resource} para usuario {user_id}"
        
        self.log_event(
            event_type=AuditEventType.AUTHORIZATION,
            event_name=event_name,
            user_id=user_id,
            severity=severity,
            description=description,
            metadata={**metadata or {}, "resource": resource, "granted": granted},
            ip_address=ip_address
        )
    
    def log_data_access(self, event_name: str, user_id: str, data_type: str, 
                       operation: str, ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de acceso a datos"""
        description = f"Acceso a datos {data_type} - Operación: {operation} por usuario {user_id}"
        
        self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            event_name=event_name,
            user_id=user_id,
            severity=AuditSeverity.MEDIUM,
            description=description,
            metadata={**metadata or {}, "data_type": data_type, "operation": operation},
            ip_address=ip_address
        )
    
    def log_configuration(self, event_name: str, user_id: str, config_type: str, 
                         old_value: Any, new_value: Any, ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de configuración"""
        description = f"Configuración {config_type} modificada por usuario {user_id}"
        
        self.log_event(
            event_type=AuditEventType.CONFIGURATION,
            event_name=event_name,
            user_id=user_id,
            severity=AuditSeverity.HIGH,
            description=description,
            metadata={**metadata or {}, "config_type": config_type, "old_value": str(old_value), "new_value": str(new_value)},
            ip_address=ip_address
        )
    
    def log_trading(self, event_name: str, user_id: str, symbol: str, 
                   action: str, amount: float, price: float, ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de trading"""
        description = f"Operación de trading: {action} {amount} {symbol} a {price} por usuario {user_id}"
        
        self.log_event(
            event_type=AuditEventType.TRADING,
            event_name=event_name,
            user_id=user_id,
            severity=AuditSeverity.HIGH,
            description=description,
            metadata={**metadata or {}, "symbol": symbol, "action": action, "amount": amount, "price": price},
            ip_address=ip_address
        )
    
    def log_security(self, event_name: str, user_id: Optional[str] = None, 
                    severity: AuditSeverity = AuditSeverity.HIGH, description: str = "", 
                    ip_address: Optional[str] = None, metadata: Optional[Dict] = None):
        """Registrar evento de seguridad"""
        self.log_event(
            event_type=AuditEventType.SECURITY,
            event_name=event_name,
            user_id=user_id,
            severity=severity,
            description=description,
            metadata=metadata,
            ip_address=ip_address
        )
    
    def get_audit_events(self, 
                        event_type: Optional[AuditEventType] = None,
                        user_id: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 1000) -> List[Dict[str, Any]]:
        """Obtener eventos de auditoría"""
        try:
            events = []
            
            # Leer archivo de log
            if not Path(self.log_path).exists():
                return events
            
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Procesar líneas (últimas N líneas)
            lines_to_process = lines[-limit:] if len(lines) > limit else lines
            
            for line in lines_to_process:
                try:
                    if self.log_format == "json":
                        event = json.loads(line.strip())
                    else:
                        # Parsear formato de texto
                        event = self._parse_text_log_line(line.strip())
                    
                    # Filtrar eventos
                    if self._filter_event(event, event_type, user_id, start_time, end_time):
                        events.append(event)
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error parseando línea de log: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Error obteniendo eventos de auditoría: {e}")
            return []
    
    def _parse_text_log_line(self, line: str) -> Dict[str, Any]:
        """Parsear línea de log en formato de texto"""
        try:
            # Formato: timestamp - logger - level - message
            parts = line.split(" - ", 3)
            if len(parts) >= 4:
                return {
                    "timestamp": parts[0],
                    "logger": parts[1],
                    "level": parts[2],
                    "message": parts[3]
                }
            else:
                return {"message": line}
                
        except Exception as e:
            logger.error(f"Error parseando línea de texto: {e}")
            return {"message": line}
    
    def _filter_event(self, event: Dict[str, Any], event_type: Optional[AuditEventType], 
                     user_id: Optional[str], start_time: Optional[datetime], end_time: Optional[datetime]) -> bool:
        """Filtrar evento según criterios"""
        try:
            # Filtrar por tipo de evento
            if event_type and event.get("event_type") != event_type.value:
                return False
            
            # Filtrar por usuario
            if user_id and event.get("user_id") != user_id:
                return False
            
            # Filtrar por tiempo
            if start_time or end_time:
                event_time_str = event.get("timestamp")
                if event_time_str:
                    try:
                        event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                        
                        if start_time and event_time < start_time:
                            return False
                        
                        if end_time and event_time > end_time:
                            return False
                    except ValueError:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error filtrando evento: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del logger de auditoría"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del logger de auditoría"""
        return {
            "enabled": self.enabled,
            "log_path": self.log_path,
            "log_format": self.log_format,
            "max_size_mb": self.max_size_mb,
            "max_files": self.max_files,
            "compression": self.compression,
            "audit_events": self.audit_events,
            "metrics": self.get_metrics()
        }
    
    def health_check(self) -> bool:
        """Verificar salud del logger de auditoría"""
        try:
            # Verificar que el directorio de logs existe
            log_dir = Path(self.log_path).parent
            if not log_dir.exists():
                return False
            
            # Verificar que el logger está configurado
            if not hasattr(self, 'audit_logger'):
                return False
            
            # Test de logging
            self.log_security(
                "health_check",
                description="Health check del logger de auditoría",
                severity=AuditSeverity.LOW
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear logger
def create_audit_logger() -> AuditLogger:
    """Crear instancia del logger de auditoría"""
    return AuditLogger()

if __name__ == "__main__":
    # Test del logger de auditoría
    def test_audit_logger():
        logger = AuditLogger()
        
        # Test de health check
        health = logger.health_check()
        print(f"Health check: {health}")
        
        # Test de eventos de auditoría
        logger.log_authentication("login_attempt", "user123", True, "192.168.1.100")
        logger.log_authorization("access_granted", "user123", "trading_data", True, "192.168.1.100")
        logger.log_data_access("data_read", "user123", "market_data", "read", "192.168.1.100")
        logger.log_configuration("config_change", "user123", "trading_params", "old_value", "new_value", "192.168.1.100")
        logger.log_trading("order_placed", "user123", "BTCUSDT", "buy", 0.1, 50000.0, "192.168.1.100")
        logger.log_security("security_alert", "user123", AuditSeverity.HIGH, "Intento de acceso no autorizado", "192.168.1.100")
        
        # Obtener eventos
        events = logger.get_audit_events(limit=10)
        print(f"Eventos obtenidos: {len(events)}")
        
        # Mostrar métricas
        print("\n=== MÉTRICAS DEL LOGGER DE AUDITORÍA ===")
        metrics = logger.get_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")
    
    # Ejecutar test
    test_audit_logger()
