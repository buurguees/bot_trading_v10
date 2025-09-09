# Ruta: core/compliance/audit_config.py
# audit_config.py - Configuración de auditoría enterprise
# Ubicación: C:\TradingBot_v10\compliance\audit_config.py

"""
Configuración de auditoría enterprise para el sistema de trading.

Características:
- Configuración de reglas de auditoría
- Gestión de eventos de auditoría
- Integración con sistemas de compliance
- Reportes automáticos
"""

import logging
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class AuditEvent:
    """Evento de auditoría"""
    id: str
    timestamp: datetime
    event_type: str
    description: str
    user_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    severity: str
    status: str

@dataclass
class AuditRule:
    """Regla de auditoría"""
    id: str
    name: str
    description: str
    event_types: List[str]
    enabled: bool
    conditions: Dict[str, Any]
    actions: List[str]
    severity: str

class AuditConfig:
    """Configuración de auditoría enterprise"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "compliance/audit_config.yaml"
        self.config = self._load_config()
        
        # Estado del sistema
        self.audit_events = []
        self.audit_rules = {}
        
        # Configurar directorios
        self.audit_dir = Path("compliance/audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Cargar reglas de auditoría
        self._load_audit_rules()
    
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
            'audit': {
                'enabled': True,
                'retention_days': 2555
            }
        }
    
    def setup_logging(self):
        """Configura logging del sistema de auditoría"""
        audit_logger = logging.getLogger(f"{__name__}.AuditConfig")
        audit_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.audit_dir / "audit_config.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        audit_logger.addHandler(file_handler)
        self.audit_logger = audit_logger
    
    def _load_audit_rules(self):
        """Carga reglas de auditoría"""
        try:
            rules_config = self.config.get('compliance', {}).get('rules', [])
            
            for rule_config in rules_config:
                rule = AuditRule(
                    id=rule_config['id'],
                    name=rule_config['name'],
                    description=rule_config['description'],
                    event_types=[rule_config.get('event_type', 'trading')],
                    enabled=rule_config['enabled'],
                    conditions={'condition': rule_config['condition']},
                    actions=[rule_config['action']],
                    severity=rule_config['severity']
                )
                
                self.audit_rules[rule.id] = rule
            
            self.audit_logger.info(f"Cargadas {len(self.audit_rules)} reglas de auditoría")
            
        except Exception as e:
            self.audit_logger.error(f"Error cargando reglas de auditoría: {e}")
    
    def log_audit_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """Registra un evento de auditoría"""
        try:
            event_id = f"audit_{int(datetime.now().timestamp())}"
            
            event = AuditEvent(
                id=event_id,
                timestamp=datetime.now(),
                event_type=event_type,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                details=details or {},
                severity=severity,
                status="logged"
            )
            
            self.audit_events.append(event)
            
            # Log del evento
            self.audit_logger.info(f"Evento de auditoría registrado: {event_type} - {description}")
            
            return event_id
            
        except Exception as e:
            self.audit_logger.error(f"Error registrando evento de auditoría: {e}")
            return None
    
    def get_audit_events(
        self,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Obtiene eventos de auditoría"""
        try:
            events = self.audit_events.copy()
            
            # Filtrar por tipo de evento
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Filtrar por fecha
            if start_date:
                events = [e for e in events if e.timestamp >= start_date]
            
            if end_date:
                events = [e for e in events if e.timestamp <= end_date]
            
            # Ordenar por timestamp (más recientes primero)
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limitar resultados
            return events[:limit]
            
        except Exception as e:
            self.audit_logger.error(f"Error obteniendo eventos de auditoría: {e}")
            return []
    
    def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Genera reporte de auditoría"""
        try:
            # Obtener eventos del período
            events = self.get_audit_events(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            # Calcular estadísticas
            total_events = len(events)
            events_by_type = {}
            events_by_severity = {}
            
            for event in events:
                # Por tipo
                event_type = event.event_type
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                
                # Por severidad
                severity = event.severity
                events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
            
            # Crear reporte
            report = {
                'report_id': f"audit_report_{int(datetime.now().timestamp())}",
                'generated_at': datetime.now().isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_events': total_events,
                'events_by_type': events_by_type,
                'events_by_severity': events_by_severity,
                'summary': {
                    'most_common_event_type': max(events_by_type, key=events_by_type.get) if events_by_type else None,
                    'most_common_severity': max(events_by_severity, key=events_by_severity.get) if events_by_severity else None,
                    'critical_events': events_by_severity.get('critical', 0),
                    'warning_events': events_by_severity.get('warning', 0)
                }
            }
            
            # Log del reporte
            self.audit_logger.info(f"Reporte de auditoría generado: {report['report_id']}")
            
            return report
            
        except Exception as e:
            self.audit_logger.error(f"Error generando reporte de auditoría: {e}")
            return {}
    
    def export_audit_data(self, output_file: Optional[str] = None) -> str:
        """Exporta datos de auditoría"""
        try:
            if output_file is None:
                output_file = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.audit_dir / output_file
            
            # Preparar datos para exportación
            export_data = {
                'audit_events': [asdict(event) for event in self.audit_events],
                'audit_rules': [asdict(rule) for rule in self.audit_rules.values()],
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            import json
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.audit_logger.info(f"Datos de auditoría exportados: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            self.audit_logger.error(f"Error exportando datos de auditoría: {e}")
            return None

# Funciones de utilidad
def create_audit_config(config_path: Optional[str] = None) -> AuditConfig:
    """Factory function para crear AuditConfig"""
    return AuditConfig(config_path)

def log_trading_event(
    event_type: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    audit_system: Optional[AuditConfig] = None
) -> str:
    """Registra un evento de trading"""
    if audit_system is None:
        audit_system = create_audit_config()
    
    return audit_system.log_audit_event(
        event_type=event_type,
        description=description,
        details=details,
        severity="info"
    )
