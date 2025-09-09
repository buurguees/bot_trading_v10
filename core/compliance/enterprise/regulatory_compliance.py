#!/usr/bin/env python3
"""
Regulatory Compliance Enterprise - Cumplimiento Regulatorio
==========================================================

Este módulo implementa cumplimiento regulatorio para MiFID II, GDPR
y otras regulaciones financieras aplicables.

Características:
- Cumplimiento MiFID II
- Cumplimiento GDPR
- Reportes regulatorios automáticos
- Gestión de consentimiento
- Retención de datos
- Auditoría de cumplimiento

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from compliance.enterprise.audit_logger import AuditLogger, EventType
from config.config_loader import user_config

logger = logging.getLogger(__name__)

class RegulationType(Enum):
    """Tipos de regulaciones"""
    MIFID_II = "mifid_ii"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    BASEL_III = "basel_iii"

class ComplianceStatus(Enum):
    """Estados de cumplimiento"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    AT_RISK = "at_risk"
    UNKNOWN = "unknown"

@dataclass
class ComplianceRule:
    """Regla de cumplimiento"""
    rule_id: str
    regulation: RegulationType
    name: str
    description: str
    severity: str
    enabled: bool
    last_checked: Optional[datetime] = None
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    violations: List[Dict[str, Any]] = None

@dataclass
class ComplianceReport:
    """Reporte de cumplimiento regulatorio"""
    report_id: str
    generated_at: datetime
    regulation: RegulationType
    overall_status: ComplianceStatus
    compliance_score: float
    rules_checked: int
    rules_passed: int
    rules_failed: int
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    next_review_date: datetime

class RegulatoryCompliance:
    """Sistema de cumplimiento regulatorio enterprise"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = user_config.get_value(['compliance', 'regulatory'], {})
        self.audit_logger = AuditLogger()
        
        # Configuración de cumplimiento
        self.enabled = self.config.get('enabled', True)
        self.retention_years = self.config.get('retention_years', 7)
        self.auto_reports = self.config.get('auto_reports', True)
        
        # Regulaciones habilitadas
        self.enabled_regulations = self.config.get('enabled_regulations', [
            RegulationType.MIFID_II.value,
            RegulationType.GDPR.value
        ])
        
        # Reglas de cumplimiento
        self.compliance_rules = self._load_compliance_rules()
        
        # Directorios
        self.setup_directories()
        
        logger.info("⚖️ RegulatoryCompliance enterprise inicializado")
    
    def _load_compliance_rules(self) -> List[ComplianceRule]:
        """Carga las reglas de cumplimiento"""
        try:
            rules = []
            
            # Reglas MiFID II
            if RegulationType.MIFID_II.value in self.enabled_regulations:
                rules.extend(self._get_mifid_ii_rules())
            
            # Reglas GDPR
            if RegulationType.GDPR.value in self.enabled_regulations:
                rules.extend(self._get_gdpr_rules())
            
            return rules
            
        except Exception as e:
            logger.error(f"❌ Error cargando reglas de cumplimiento: {e}")
            return []
    
    def _get_mifid_ii_rules(self) -> List[ComplianceRule]:
        """Obtiene reglas de cumplimiento MiFID II"""
        return [
            ComplianceRule(
                rule_id="MIFID_001",
                regulation=RegulationType.MIFID_II,
                name="Trade Reporting",
                description="All trades must be reported to competent authorities",
                severity="CRITICAL",
                enabled=True
            ),
            ComplianceRule(
                rule_id="MIFID_002",
                regulation=RegulationType.MIFID_II,
                name="Best Execution",
                description="Orders must be executed at best available price",
                severity="HIGH",
                enabled=True
            ),
            ComplianceRule(
                rule_id="MIFID_003",
                regulation=RegulationType.MIFID_II,
                name="Client Categorization",
                description="Clients must be properly categorized",
                severity="HIGH",
                enabled=True
            ),
            ComplianceRule(
                rule_id="MIFID_004",
                regulation=RegulationType.MIFID_II,
                name="Record Keeping",
                description="All communications and transactions must be recorded",
                severity="CRITICAL",
                enabled=True
            ),
            ComplianceRule(
                rule_id="MIFID_005",
                regulation=RegulationType.MIFID_II,
                name="Conflicts of Interest",
                description="Conflicts of interest must be managed and disclosed",
                severity="HIGH",
                enabled=True
            )
        ]
    
    def _get_gdpr_rules(self) -> List[ComplianceRule]:
        """Obtiene reglas de cumplimiento GDPR"""
        return [
            ComplianceRule(
                rule_id="GDPR_001",
                regulation=RegulationType.GDPR,
                name="Data Minimization",
                description="Only necessary personal data should be collected",
                severity="HIGH",
                enabled=True
            ),
            ComplianceRule(
                rule_id="GDPR_002",
                regulation=RegulationType.GDPR,
                name="Consent Management",
                description="Valid consent must be obtained for data processing",
                severity="CRITICAL",
                enabled=True
            ),
            ComplianceRule(
                rule_id="GDPR_003",
                regulation=RegulationType.GDPR,
                name="Data Retention",
                description="Personal data must not be kept longer than necessary",
                severity="HIGH",
                enabled=True
            ),
            ComplianceRule(
                rule_id="GDPR_004",
                regulation=RegulationType.GDPR,
                name="Right to Erasure",
                description="Data subjects have right to request data deletion",
                severity="HIGH",
                enabled=True
            ),
            ComplianceRule(
                rule_id="GDPR_005",
                regulation=RegulationType.GDPR,
                name="Data Security",
                description="Personal data must be adequately protected",
                severity="CRITICAL",
                enabled=True
            )
        ]
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/compliance/regulatory',
            'data/enterprise/compliance/regulatory',
            'backups/enterprise/compliance/regulatory',
            'exports/enterprise/compliance/regulatory'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def check_compliance(self, regulation: Optional[RegulationType] = None) -> ComplianceReport:
        """Verifica el cumplimiento regulatorio"""
        try:
            logger.info(f"⚖️ Verificando cumplimiento regulatorio: {regulation or 'TODAS'}")
            
            # Filtrar reglas por regulación si se especifica
            rules_to_check = self.compliance_rules
            if regulation:
                rules_to_check = [r for r in self.compliance_rules if r.regulation == regulation]
            
            # Verificar cada regla
            rules_passed = 0
            rules_failed = 0
            violations = []
            
            for rule in rules_to_check:
                if not rule.enabled:
                    continue
                
                rule_status, rule_violations = await self._check_rule(rule)
                rule.status = rule_status
                rule.last_checked = datetime.now()
                
                if rule_status == ComplianceStatus.COMPLIANT:
                    rules_passed += 1
                else:
                    rules_failed += 1
                    violations.extend(rule_violations)
            
            # Calcular score de cumplimiento
            total_rules = rules_passed + rules_failed
            compliance_score = (rules_passed / total_rules * 100) if total_rules > 0 else 0
            
            # Determinar estado general
            if compliance_score >= 95:
                overall_status = ComplianceStatus.COMPLIANT
            elif compliance_score >= 80:
                overall_status = ComplianceStatus.AT_RISK
            else:
                overall_status = ComplianceStatus.NON_COMPLIANT
            
            # Generar recomendaciones
            recommendations = await self._generate_compliance_recommendations(violations)
            
            # Crear reporte
            report = ComplianceReport(
                report_id=f"COMP_{regulation.value if regulation else 'ALL'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                generated_at=datetime.now(),
                regulation=regulation or RegulationType.MIFID_II,  # Default
                overall_status=overall_status,
                compliance_score=compliance_score,
                rules_checked=total_rules,
                rules_passed=rules_passed,
                rules_failed=rules_failed,
                violations=violations,
                recommendations=recommendations,
                next_review_date=datetime.now() + timedelta(days=30)
            )
            
            # Guardar reporte
            await self._save_compliance_report(report)
            
            # Registrar verificación de cumplimiento
            await self.audit_logger.log_event(
                EventType.USER_ACTION,
                {
                    'action': 'compliance_check',
                    'regulation': regulation.value if regulation else 'ALL',
                    'overall_status': overall_status.value,
                    'compliance_score': compliance_score,
                    'rules_checked': total_rules,
                    'rules_passed': rules_passed,
                    'rules_failed': rules_failed
                }
            )
            
            logger.info(f"✅ Verificación de cumplimiento completada: {overall_status.value}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error verificando cumplimiento: {e}")
            raise
    
    async def _check_rule(self, rule: ComplianceRule) -> Tuple[ComplianceStatus, List[Dict[str, Any]]]:
        """Verifica una regla específica de cumplimiento"""
        try:
            violations = []
            
            if rule.regulation == RegulationType.MIFID_II:
                return await self._check_mifid_ii_rule(rule)
            elif rule.regulation == RegulationType.GDPR:
                return await self._check_gdpr_rule(rule)
            else:
                return ComplianceStatus.UNKNOWN, []
                
        except Exception as e:
            logger.error(f"❌ Error verificando regla {rule.rule_id}: {e}")
            return ComplianceStatus.UNKNOWN, []
    
    async def _check_mifid_ii_rule(self, rule: ComplianceRule) -> Tuple[ComplianceStatus, List[Dict[str, Any]]]:
        """Verifica reglas específicas de MiFID II"""
        try:
            violations = []
            
            if rule.rule_id == "MIFID_001":  # Trade Reporting
                # Verificar que todos los trades estén reportados
                # En una implementación real, esto verificaría la base de datos
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Trade reporting verification not implemented',
                    'severity': 'WARNING'
                })
            
            elif rule.rule_id == "MIFID_002":  # Best Execution
                # Verificar que las órdenes se ejecuten al mejor precio
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Best execution verification not implemented',
                    'severity': 'WARNING'
                })
            
            elif rule.rule_id == "MIFID_003":  # Client Categorization
                # Verificar categorización de clientes
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Client categorization verification not implemented',
                    'severity': 'WARNING'
                })
            
            elif rule.rule_id == "MIFID_004":  # Record Keeping
                # Verificar que todos los registros estén guardados
                # Verificar que el audit logger esté funcionando
                if not self.audit_logger.enabled:
                    violations.append({
                        'rule_id': rule.rule_id,
                        'description': 'Audit logging is disabled',
                        'severity': 'CRITICAL'
                    })
                else:
                    # Verificar que se estén generando logs
                    recent_events = await self.audit_logger.get_events_by_type(
                        EventType.TRADE_OPENED,
                        datetime.now() - timedelta(hours=24)
                    )
                    if not recent_events:
                        violations.append({
                            'rule_id': rule.rule_id,
                            'description': 'No recent trade events logged',
                            'severity': 'WARNING'
                        })
            
            elif rule.rule_id == "MIFID_005":  # Conflicts of Interest
                # Verificar gestión de conflictos de interés
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Conflicts of interest management not implemented',
                    'severity': 'WARNING'
                })
            
            # Determinar estado
            if any(v['severity'] == 'CRITICAL' for v in violations):
                return ComplianceStatus.NON_COMPLIANT, violations
            elif violations:
                return ComplianceStatus.AT_RISK, violations
            else:
                return ComplianceStatus.COMPLIANT, []
                
        except Exception as e:
            logger.error(f"❌ Error verificando regla MiFID II {rule.rule_id}: {e}")
            return ComplianceStatus.UNKNOWN, []
    
    async def _check_gdpr_rule(self, rule: ComplianceRule) -> Tuple[ComplianceStatus, List[Dict[str, Any]]]:
        """Verifica reglas específicas de GDPR"""
        try:
            violations = []
            
            if rule.rule_id == "GDPR_001":  # Data Minimization
                # Verificar que solo se recopile datos necesarios
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Data minimization verification not implemented',
                    'severity': 'WARNING'
                })
            
            elif rule.rule_id == "GDPR_002":  # Consent Management
                # Verificar gestión de consentimiento
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Consent management system not implemented',
                    'severity': 'CRITICAL'
                })
            
            elif rule.rule_id == "GDPR_003":  # Data Retention
                # Verificar política de retención de datos
                if self.retention_years > 7:
                    violations.append({
                        'rule_id': rule.rule_id,
                        'description': f'Data retention period too long: {self.retention_years} years',
                        'severity': 'WARNING'
                    })
            
            elif rule.rule_id == "GDPR_004":  # Right to Erasure
                # Verificar implementación del derecho al olvido
                violations.append({
                    'rule_id': rule.rule_id,
                    'description': 'Right to erasure implementation not verified',
                    'severity': 'WARNING'
                })
            
            elif rule.rule_id == "GDPR_005":  # Data Security
                # Verificar seguridad de datos
                if not self.audit_logger.encryption_enabled:
                    violations.append({
                        'rule_id': rule.rule_id,
                        'description': 'Data encryption is disabled',
                        'severity': 'CRITICAL'
                    })
            
            # Determinar estado
            if any(v['severity'] == 'CRITICAL' for v in violations):
                return ComplianceStatus.NON_COMPLIANT, violations
            elif violations:
                return ComplianceStatus.AT_RISK, violations
            else:
                return ComplianceStatus.COMPLIANT, []
                
        except Exception as e:
            logger.error(f"❌ Error verificando regla GDPR {rule.rule_id}: {e}")
            return ComplianceStatus.UNKNOWN, []
    
    async def _generate_compliance_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Genera recomendaciones de cumplimiento"""
        try:
            recommendations = []
            
            # Agrupar violaciones por severidad
            critical_violations = [v for v in violations if v['severity'] == 'CRITICAL']
            warning_violations = [v for v in violations if v['severity'] == 'WARNING']
            
            if critical_violations:
                recommendations.append("URGENTE: Resolver violaciones críticas inmediatamente")
                recommendations.append("Implementar controles de cumplimiento faltantes")
            
            if warning_violations:
                recommendations.append("Revisar y corregir violaciones de advertencia")
                recommendations.append("Mejorar procesos de cumplimiento existentes")
            
            # Recomendaciones específicas por tipo de violación
            violation_types = set(v['rule_id'] for v in violations)
            
            if "MIFID_001" in violation_types:
                recommendations.append("Implementar sistema de reporte de trades automático")
            
            if "MIFID_004" in violation_types:
                recommendations.append("Asegurar que el audit logging esté habilitado y funcionando")
            
            if "GDPR_002" in violation_types:
                recommendations.append("Implementar sistema de gestión de consentimiento")
            
            if "GDPR_005" in violation_types:
                recommendations.append("Habilitar encriptación de datos personales")
            
            # Recomendaciones generales
            recommendations.append("Establecer programa de cumplimiento continuo")
            recommendations.append("Realizar auditorías de cumplimiento regulares")
            recommendations.append("Capacitar al personal en regulaciones aplicables")
            recommendations.append("Mantener documentación de cumplimiento actualizada")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones de cumplimiento: {e}")
            return []
    
    async def _save_compliance_report(self, report: ComplianceReport):
        """Guarda el reporte de cumplimiento"""
        try:
            report_file = Path(f"data/enterprise/compliance/regulatory/compliance_{report.report_id}.json")
            
            report_data = {
                'report_id': report.report_id,
                'generated_at': report.generated_at.isoformat(),
                'regulation': report.regulation.value,
                'overall_status': report.overall_status.value,
                'compliance_score': report.compliance_score,
                'rules_checked': report.rules_checked,
                'rules_passed': report.rules_passed,
                'rules_failed': report.rules_failed,
                'violations': report.violations,
                'recommendations': report.recommendations,
                'next_review_date': report.next_review_date.isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Error guardando reporte de cumplimiento: {e}")
    
    async def get_compliance_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de cumplimiento"""
        try:
            status = {
                'overall_status': 'UNKNOWN',
                'regulations': {},
                'last_check': None,
                'next_check': None
            }
            
            for regulation in self.enabled_regulations:
                reg_type = RegulationType(regulation)
                rules = [r for r in self.compliance_rules if r.regulation == reg_type]
                
                if rules:
                    passed = len([r for r in rules if r.status == ComplianceStatus.COMPLIANT])
                    total = len([r for r in rules if r.enabled])
                    score = (passed / total * 100) if total > 0 else 0
                    
                    status['regulations'][regulation] = {
                        'score': score,
                        'rules_passed': passed,
                        'rules_total': total,
                        'status': 'COMPLIANT' if score >= 95 else 'AT_RISK' if score >= 80 else 'NON_COMPLIANT'
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de cumplimiento: {e}")
            return {'error': str(e)}
    
    async def generate_regulatory_report(
        self, 
        regulation: RegulationType,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Genera reporte regulatorio para una regulación específica"""
        try:
            logger.info(f"📋 Generando reporte regulatorio: {regulation.value}")
            
            # Verificar cumplimiento
            compliance_report = await self.check_compliance(regulation)
            
            # Generar reporte específico según la regulación
            if regulation == RegulationType.MIFID_II:
                report_path = await self._generate_mifid_ii_report(compliance_report, start_date, end_date)
            elif regulation == RegulationType.GDPR:
                report_path = await self._generate_gdpr_report(compliance_report, start_date, end_date)
            else:
                report_path = await self._generate_generic_report(compliance_report, start_date, end_date)
            
            # Registrar generación de reporte
            await self.audit_logger.log_event(
                EventType.USER_ACTION,
                {
                    'action': 'regulatory_report_generated',
                    'regulation': regulation.value,
                    'report_path': str(report_path),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat()
                }
            )
            
            logger.info(f"✅ Reporte regulatorio generado: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte regulatorio: {e}")
            return ""
    
    async def _generate_mifid_ii_report(
        self, 
        compliance_report: ComplianceReport, 
        start_date: datetime, 
        end_date: datetime
    ) -> Path:
        """Genera reporte específico de MiFID II"""
        try:
            report_file = Path(f"exports/enterprise/compliance/regulatory/mifid_ii_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            report_data = {
                'report_type': 'MiFID II Compliance Report',
                'generated_at': compliance_report.generated_at.isoformat(),
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'compliance_summary': {
                    'overall_status': compliance_report.overall_status.value,
                    'compliance_score': compliance_report.compliance_score,
                    'rules_checked': compliance_report.rules_checked,
                    'rules_passed': compliance_report.rules_passed,
                    'rules_failed': compliance_report.rules_failed
                },
                'violations': compliance_report.violations,
                'recommendations': compliance_report.recommendations,
                'next_review_date': compliance_report.next_review_date.isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return report_file
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte MiFID II: {e}")
            raise
    
    async def _generate_gdpr_report(
        self, 
        compliance_report: ComplianceReport, 
        start_date: datetime, 
        end_date: datetime
    ) -> Path:
        """Genera reporte específico de GDPR"""
        try:
            report_file = Path(f"exports/enterprise/compliance/regulatory/gdpr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            report_data = {
                'report_type': 'GDPR Compliance Report',
                'generated_at': compliance_report.generated_at.isoformat(),
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'compliance_summary': {
                    'overall_status': compliance_report.overall_status.value,
                    'compliance_score': compliance_report.compliance_score,
                    'rules_checked': compliance_report.rules_checked,
                    'rules_passed': compliance_report.rules_passed,
                    'rules_failed': compliance_report.rules_failed
                },
                'data_protection_measures': {
                    'encryption_enabled': self.audit_logger.encryption_enabled,
                    'retention_years': self.retention_years,
                    'audit_logging_enabled': self.audit_logger.enabled
                },
                'violations': compliance_report.violations,
                'recommendations': compliance_report.recommendations,
                'next_review_date': compliance_report.next_review_date.isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return report_file
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte GDPR: {e}")
            raise
    
    async def _generate_generic_report(
        self, 
        compliance_report: ComplianceReport, 
        start_date: datetime, 
        end_date: datetime
    ) -> Path:
        """Genera reporte genérico de cumplimiento"""
        try:
            report_file = Path(f"exports/enterprise/compliance/regulatory/generic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            report_data = {
                'report_type': 'Generic Compliance Report',
                'generated_at': compliance_report.generated_at.isoformat(),
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'compliance_summary': {
                    'overall_status': compliance_report.overall_status.value,
                    'compliance_score': compliance_report.compliance_score,
                    'rules_checked': compliance_report.rules_checked,
                    'rules_passed': compliance_report.rules_passed,
                    'rules_failed': compliance_report.rules_failed
                },
                'violations': compliance_report.violations,
                'recommendations': compliance_report.recommendations,
                'next_review_date': compliance_report.next_review_date.isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return report_file
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte genérico: {e}")
            raise
    
    async def close(self):
        """Cierra el sistema de cumplimiento regulatorio"""
        try:
            await self.audit_logger.close()
            logger.info("✅ RegulatoryCompliance cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando RegulatoryCompliance: {e}")

# Instancia global
regulatory_compliance = RegulatoryCompliance()
