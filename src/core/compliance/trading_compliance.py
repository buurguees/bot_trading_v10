# trading_compliance.py - Compliance de trading enterprise
# Ubicación: C:\TradingBot_v10\compliance\trading_compliance.py

"""
Sistema de compliance para trading enterprise.

Características:
- Verificación de cumplimiento de regulaciones
- Auditoría de transacciones
- Reportes de compliance
- Integración con sistemas de monitoreo
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import hashlib
import hmac
from enum import Enum

logger = logging.getLogger(__name__)

class ComplianceLevel(Enum):
    """Niveles de compliance"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(Enum):
    """Estado de compliance"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class ComplianceRule:
    """Regla de compliance"""
    id: str
    name: str
    description: str
    level: ComplianceLevel
    enabled: bool
    condition: str
    action: str
    severity: str
    created_at: datetime
    updated_at: datetime

@dataclass
class ComplianceViolation:
    """Violación de compliance"""
    id: str
    rule_id: str
    timestamp: datetime
    severity: str
    description: str
    details: Dict[str, Any]
    status: str
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

@dataclass
class ComplianceReport:
    """Reporte de compliance"""
    id: str
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    total_violations: int
    violations_by_level: Dict[str, int]
    compliance_score: float
    recommendations: List[str]
    status: ComplianceStatus

class TradingCompliance:
    """Sistema de compliance de trading enterprise"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "compliance/audit_config.yaml"
        self.config = self._load_config()
        
        # Estado del sistema
        self.rules = {}
        self.violations = []
        self.reports = []
        
        # Configurar directorios
        self.compliance_dir = Path("compliance")
        self.compliance_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Cargar reglas de compliance
        self._load_compliance_rules()
        
        # Configurar auditoría
        self.audit_config = self._setup_audit_config()
    
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
            'compliance': {
                'enabled': True,
                'rules': [],
                'audit': {
                    'enabled': True,
                    'retention_days': 2555  # 7 años
                }
            }
        }
    
    def setup_logging(self):
        """Configura logging del sistema de compliance"""
        compliance_logger = logging.getLogger(f"{__name__}.TradingCompliance")
        compliance_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.compliance_dir / "trading_compliance.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        compliance_logger.addHandler(file_handler)
        self.compliance_logger = compliance_logger
    
    def _load_compliance_rules(self):
        """Carga reglas de compliance"""
        try:
            rules_config = self.config.get('compliance', {}).get('rules', [])
            
            for rule_config in rules_config:
                rule = ComplianceRule(
                    id=rule_config['id'],
                    name=rule_config['name'],
                    description=rule_config['description'],
                    level=ComplianceLevel(rule_config['level']),
                    enabled=rule_config['enabled'],
                    condition=rule_config['condition'],
                    action=rule_config['action'],
                    severity=rule_config['severity'],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.rules[rule.id] = rule
            
            self.compliance_logger.info(f"Cargadas {len(self.rules)} reglas de compliance")
            
        except Exception as e:
            self.compliance_logger.error(f"Error cargando reglas de compliance: {e}")
    
    def _setup_audit_config(self) -> Dict[str, Any]:
        """Configura auditoría"""
        return self.config.get('compliance', {}).get('audit', {})
    
    def add_compliance_rule(self, rule: ComplianceRule) -> bool:
        """Agrega una nueva regla de compliance"""
        try:
            self.rules[rule.id] = rule
            self.compliance_logger.info(f"Regla de compliance agregada: {rule.name}")
            return True
            
        except Exception as e:
            self.compliance_logger.error(f"Error agregando regla de compliance: {e}")
            return False
    
    def remove_compliance_rule(self, rule_id: str) -> bool:
        """Remueve una regla de compliance"""
        try:
            if rule_id in self.rules:
                del self.rules[rule_id]
                self.compliance_logger.info(f"Regla de compliance removida: {rule_id}")
                return True
            return False
            
        except Exception as e:
            self.compliance_logger.error(f"Error removiendo regla de compliance: {e}")
            return False
    
    def check_compliance(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        """Verifica compliance de datos"""
        violations = []
        
        try:
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                # Evaluar condición de la regla
                if self._evaluate_condition(rule.condition, data):
                    violation = ComplianceViolation(
                        id=f"{rule_id}_{int(time.time())}",
                        rule_id=rule_id,
                        timestamp=datetime.now(),
                        severity=rule.severity,
                        description=rule.description,
                        details=data,
                        status="open"
                    )
                    
                    violations.append(violation)
                    self.violations.append(violation)
                    
                    # Log de la violación
                    self.compliance_logger.warning(
                        f"Violación de compliance detectada: {rule.name} - {rule.description}"
                    )
            
            return violations
            
        except Exception as e:
            self.compliance_logger.error(f"Error verificando compliance: {e}")
            return []
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evalúa una condición de compliance"""
        try:
            # Reemplazar variables en la condición
            for key, value in data.items():
                condition = condition.replace(f"{{{key}}}", str(value))
            
            # Evaluar condición (simplificada)
            # En un sistema real, se usaría un motor de reglas más sofisticado
            if ">" in condition:
                parts = condition.split(">")
                if len(parts) == 2:
                    left = float(parts[0].strip())
                    right = float(parts[1].strip())
                    return left > right
            
            elif "<" in condition:
                parts = condition.split("<")
                if len(parts) == 2:
                    left = float(parts[0].strip())
                    right = float(parts[1].strip())
                    return left < right
            
            elif "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    return left == right
            
            elif "!=" in condition:
                parts = condition.split("!=")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    return left != right
            
            return False
            
        except Exception as e:
            self.compliance_logger.error(f"Error evaluando condición: {e}")
            return False
    
    def resolve_violation(self, violation_id: str, resolved_by: str) -> bool:
        """Resuelve una violación de compliance"""
        try:
            for violation in self.violations:
                if violation.id == violation_id:
                    violation.status = "resolved"
                    violation.resolved_at = datetime.now()
                    violation.resolved_by = resolved_by
                    
                    self.compliance_logger.info(
                        f"Violación resuelta: {violation_id} por {resolved_by}"
                    )
                    return True
            
            return False
            
        except Exception as e:
            self.compliance_logger.error(f"Error resolviendo violación: {e}")
            return False
    
    def generate_compliance_report(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> ComplianceReport:
        """Genera reporte de compliance"""
        try:
            # Filtrar violaciones por período
            period_violations = [
                v for v in self.violations
                if period_start <= v.timestamp <= period_end
            ]
            
            # Calcular estadísticas
            total_violations = len(period_violations)
            violations_by_level = {}
            
            for violation in period_violations:
                level = violation.severity
                violations_by_level[level] = violations_by_level.get(level, 0) + 1
            
            # Calcular score de compliance
            total_rules = len(self.rules)
            if total_rules > 0:
                compliance_score = max(0, 1 - (total_violations / total_rules))
            else:
                compliance_score = 1.0
            
            # Determinar status
            if compliance_score >= 0.95:
                status = ComplianceStatus.COMPLIANT
            elif compliance_score >= 0.8:
                status = ComplianceStatus.WARNING
            elif compliance_score >= 0.6:
                status = ComplianceStatus.NON_COMPLIANT
            else:
                status = ComplianceStatus.CRITICAL
            
            # Generar recomendaciones
            recommendations = self._generate_recommendations(period_violations)
            
            # Crear reporte
            report = ComplianceReport(
                id=f"compliance_report_{int(time.time())}",
                timestamp=datetime.now(),
                period_start=period_start,
                period_end=period_end,
                total_violations=total_violations,
                violations_by_level=violations_by_level,
                compliance_score=compliance_score,
                recommendations=recommendations,
                status=status
            )
            
            self.reports.append(report)
            
            # Log del reporte
            self.compliance_logger.info(
                f"Reporte de compliance generado: {report.id} - Score: {compliance_score:.2f}"
            )
            
            return report
            
        except Exception as e:
            self.compliance_logger.error(f"Error generando reporte de compliance: {e}")
            return None
    
    def _generate_recommendations(self, violations: List[ComplianceViolation]) -> List[str]:
        """Genera recomendaciones basadas en violaciones"""
        recommendations = []
        
        # Agrupar violaciones por tipo
        violation_types = {}
        for violation in violations:
            rule_id = violation.rule_id
            if rule_id not in violation_types:
                violation_types[rule_id] = 0
            violation_types[rule_id] += 1
        
        # Generar recomendaciones específicas
        for rule_id, count in violation_types.items():
            if count > 5:
                recommendations.append(f"Revisar regla {rule_id}: {count} violaciones detectadas")
        
        # Recomendaciones generales
        if len(violations) > 10:
            recommendations.append("Implementar controles adicionales de compliance")
        
        if any(v.severity == "critical" for v in violations):
            recommendations.append("Revisar urgentemente violaciones críticas")
        
        return recommendations
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Obtiene estado actual de compliance"""
        try:
            # Calcular estadísticas
            total_rules = len(self.rules)
            active_rules = len([r for r in self.rules.values() if r.enabled])
            total_violations = len(self.violations)
            open_violations = len([v for v in self.violations if v.status == "open"])
            
            # Calcular score de compliance
            if total_rules > 0:
                compliance_score = max(0, 1 - (open_violations / total_rules))
            else:
                compliance_score = 1.0
            
            return {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'total_violations': total_violations,
                'open_violations': open_violations,
                'compliance_score': compliance_score,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.compliance_logger.error(f"Error obteniendo estado de compliance: {e}")
            return {}
    
    def export_compliance_data(self, output_file: Optional[str] = None) -> str:
        """Exporta datos de compliance"""
        try:
            if output_file is None:
                output_file = f"compliance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.compliance_dir / output_file
            
            # Preparar datos para exportación
            export_data = {
                'rules': [asdict(rule) for rule in self.rules.values()],
                'violations': [asdict(violation) for violation in self.violations],
                'reports': [asdict(report) for report in self.reports],
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.compliance_logger.info(f"Datos de compliance exportados: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            self.compliance_logger.error(f"Error exportando datos de compliance: {e}")
            return None
    
    def audit_trading_activity(self, trading_data: Dict[str, Any]) -> bool:
        """Audita actividad de trading"""
        try:
            # Verificar compliance
            violations = self.check_compliance(trading_data)
            
            # Log de auditoría
            if violations:
                self.compliance_logger.warning(
                    f"Auditoría detectó {len(violations)} violaciones de compliance"
                )
            else:
                self.compliance_logger.info("Auditoría: actividad de trading compliant")
            
            # Guardar datos de auditoría
            self._save_audit_data(trading_data, violations)
            
            return len(violations) == 0
            
        except Exception as e:
            self.compliance_logger.error(f"Error auditando actividad de trading: {e}")
            return False
    
    def _save_audit_data(self, trading_data: Dict[str, Any], violations: List[ComplianceViolation]):
        """Guarda datos de auditoría"""
        try:
            audit_data = {
                'timestamp': datetime.now().isoformat(),
                'trading_data': trading_data,
                'violations': [asdict(v) for v in violations],
                'compliance_status': len(violations) == 0
            }
            
            # Crear directorio de auditoría
            audit_dir = self.compliance_dir / "audit"
            audit_dir.mkdir(exist_ok=True)
            
            # Guardar archivo de auditoría
            audit_file = audit_dir / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(audit_file, 'w') as f:
                json.dump(audit_data, f, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            self.compliance_logger.error(f"Error guardando datos de auditoría: {e}")

# Funciones de utilidad
def create_trading_compliance(config_path: Optional[str] = None) -> TradingCompliance:
    """Factory function para crear TradingCompliance"""
    return TradingCompliance(config_path)

def check_trading_compliance(
    trading_data: Dict[str, Any],
    compliance_system: Optional[TradingCompliance] = None
) -> List[ComplianceViolation]:
    """Verifica compliance de datos de trading"""
    if compliance_system is None:
        compliance_system = create_trading_compliance()
    
    return compliance_system.check_compliance(trading_data)
