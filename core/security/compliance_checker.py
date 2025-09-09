# compliance_checker.py - Verificador de compliance enterprise
# Ubicación: C:\TradingBot_v10\security\compliance_checker.py

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

from core.config.enterprise_config import get_enterprise_config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    """Estándares de compliance"""
    GDPR = "gdpr"
    MIFID2 = "mifid2"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"

class ComplianceStatus(Enum):
    """Estados de compliance"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    UNKNOWN = "unknown"

class ComplianceChecker:
    """Verificador de compliance enterprise"""
    
    def __init__(self):
        """Inicializar el verificador de compliance"""
        self.config = get_enterprise_config()
        self.security_config = self.config.get_security_config()
        self.compliance_config = self.security_config.get("compliance", {})
        
        # Configuración de compliance
        self.gdpr_config = self.compliance_config.get("gdpr", {})
        self.mifid2_config = self.compliance_config.get("mifid2", {})
        self.reporting_config = self.compliance_config.get("reporting", {})
        
        # Configuración de reportes
        self.reports_enabled = self.reporting_config.get("enabled", True)
        self.reports_frequency = self.reporting_config.get("frequency", "daily")
        self.reports_path = self.reporting_config.get("path", "reports/compliance/{date}/compliance_report_{timestamp}.json")
        
        # Checks automáticos
        self.checks_config = self.reporting_config.get("checks", [])
        
        # Métricas
        self.metrics = {
            "checks_executed_total": 0,
            "checks_passed": 0,
            "checks_failed": 0,
            "checks_warning": 0,
            "reports_generated_total": 0,
            "last_check_time": None,
            "last_report_time": None,
            "errors_total": 0
        }
        
        logger.info("ComplianceChecker inicializado")
    
    async def start(self):
        """Iniciar el verificador de compliance"""
        try:
            logger.info("Iniciando ComplianceChecker...")
            
            # Crear directorio de reportes si no existe
            if self.reports_enabled:
                self._create_reports_directory()
            
            logger.info("ComplianceChecker iniciado exitosamente")
            
        except Exception as e:
            logger.error(f"Error iniciando ComplianceChecker: {e}")
            raise
    
    async def stop(self):
        """Detener el verificador de compliance"""
        try:
            logger.info("Deteniendo ComplianceChecker...")
            logger.info("ComplianceChecker detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo ComplianceChecker: {e}")
    
    def _create_reports_directory(self):
        """Crear directorio de reportes"""
        try:
            # Crear directorio base de reportes
            reports_dir = Path("reports/compliance")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("Directorio de reportes creado")
            
        except Exception as e:
            logger.error(f"Error creando directorio de reportes: {e}")
            raise
    
    async def run_compliance_check(self, standard: ComplianceStandard) -> Dict[str, Any]:
        """Ejecutar verificación de compliance para un estándar"""
        try:
            self.metrics["checks_executed_total"] += 1
            self.metrics["last_check_time"] = datetime.now(timezone.utc)
            
            if standard == ComplianceStandard.GDPR:
                return await self._check_gdpr_compliance()
            elif standard == ComplianceStandard.MIFID2:
                return await self._check_mifid2_compliance()
            else:
                return {
                    "standard": standard.value,
                    "status": ComplianceStatus.UNKNOWN.value,
                    "message": f"Estándar {standard.value} no implementado",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error ejecutando verificación de compliance {standard.value}: {e}")
            self.metrics["errors_total"] += 1
            return {
                "standard": standard.value,
                "status": ComplianceStatus.UNKNOWN.value,
                "message": f"Error en verificación: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _check_gdpr_compliance(self) -> Dict[str, Any]:
        """Verificar compliance GDPR"""
        try:
            gdpr_enabled = self.gdpr_config.get("enabled", True)
            if not gdpr_enabled:
                return {
                    "standard": "gdpr",
                    "status": ComplianceStatus.UNKNOWN.value,
                    "message": "GDPR no está habilitado",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            issues = []
            warnings = []
            
            # Verificar retención de datos
            data_retention_days = self.gdpr_config.get("data_retention_days", 2555)
            if data_retention_days > 2555:  # 7 años
                issues.append(f"Retención de datos excede 7 años: {data_retention_days} días")
            
            # Verificar anonimización
            anonymization_enabled = self.gdpr_config.get("anonymization_enabled", True)
            if not anonymization_enabled:
                warnings.append("Anonimización de datos no está habilitada")
            
            # Verificar derecho al olvido
            right_to_be_forgotten = self.gdpr_config.get("right_to_be_forgotten", True)
            if not right_to_be_forgotten:
                warnings.append("Derecho al olvido no está implementado")
            
            # Determinar estado
            if issues:
                status = ComplianceStatus.NON_COMPLIANT
            elif warnings:
                status = ComplianceStatus.WARNING
            else:
                status = ComplianceStatus.COMPLIANT
            
            # Actualizar métricas
            if status == ComplianceStatus.COMPLIANT:
                self.metrics["checks_passed"] += 1
            elif status == ComplianceStatus.WARNING:
                self.metrics["checks_warning"] += 1
            else:
                self.metrics["checks_failed"] += 1
            
            return {
                "standard": "gdpr",
                "status": status.value,
                "issues": issues,
                "warnings": warnings,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verificando compliance GDPR: {e}")
            self.metrics["checks_failed"] += 1
            return {
                "standard": "gdpr",
                "status": ComplianceStatus.UNKNOWN.value,
                "message": f"Error en verificación GDPR: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _check_mifid2_compliance(self) -> Dict[str, Any]:
        """Verificar compliance MiFID II"""
        try:
            mifid2_enabled = self.mifid2_config.get("enabled", True)
            if not mifid2_enabled:
                return {
                    "standard": "mifid2",
                    "status": ComplianceStatus.UNKNOWN.value,
                    "message": "MiFID II no está habilitado",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            issues = []
            warnings = []
            
            # Verificar reporte de transacciones
            transaction_reporting = self.mifid2_config.get("transaction_reporting", True)
            if not transaction_reporting:
                issues.append("Reporte de transacciones no está habilitado")
            
            # Verificar reporte de mejor ejecución
            best_execution_reporting = self.mifid2_config.get("best_execution_reporting", True)
            if not best_execution_reporting:
                issues.append("Reporte de mejor ejecución no está habilitado")
            
            # Verificar reconstrucción de trades
            trade_reconstruction = self.mifid2_config.get("trade_reconstruction", True)
            if not trade_reconstruction:
                issues.append("Reconstrucción de trades no está habilitada")
            
            # Verificar retención de datos
            data_retention_years = self.mifid2_config.get("data_retention_years", 7)
            if data_retention_years < 7:
                issues.append(f"Retención de datos insuficiente: {data_retention_years} años (mínimo 7)")
            
            # Determinar estado
            if issues:
                status = ComplianceStatus.NON_COMPLIANT
            elif warnings:
                status = ComplianceStatus.WARNING
            else:
                status = ComplianceStatus.COMPLIANT
            
            # Actualizar métricas
            if status == ComplianceStatus.COMPLIANT:
                self.metrics["checks_passed"] += 1
            elif status == ComplianceStatus.WARNING:
                self.metrics["checks_warning"] += 1
            else:
                self.metrics["checks_failed"] += 1
            
            return {
                "standard": "mifid2",
                "status": status.value,
                "issues": issues,
                "warnings": warnings,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verificando compliance MiFID II: {e}")
            self.metrics["checks_failed"] += 1
            return {
                "standard": "mifid2",
                "status": ComplianceStatus.UNKNOWN.value,
                "message": f"Error en verificación MiFID II: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def run_all_compliance_checks(self) -> Dict[str, Any]:
        """Ejecutar todas las verificaciones de compliance"""
        try:
            results = {}
            
            # Verificar GDPR
            gdpr_result = await self.run_compliance_check(ComplianceStandard.GDPR)
            results["gdpr"] = gdpr_result
            
            # Verificar MiFID II
            mifid2_result = await self.run_compliance_check(ComplianceStandard.MIFID2)
            results["mifid2"] = mifid2_result
            
            # Determinar estado general
            all_statuses = [result["status"] for result in results.values()]
            
            if ComplianceStatus.NON_COMPLIANT.value in all_statuses:
                overall_status = ComplianceStatus.NON_COMPLIANT.value
            elif ComplianceStatus.WARNING.value in all_statuses:
                overall_status = ComplianceStatus.WARNING.value
            elif ComplianceStatus.UNKNOWN.value in all_statuses:
                overall_status = ComplianceStatus.UNKNOWN.value
            else:
                overall_status = ComplianceStatus.COMPLIANT.value
            
            return {
                "overall_status": overall_status,
                "checks": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando todas las verificaciones de compliance: {e}")
            return {
                "overall_status": ComplianceStatus.UNKNOWN.value,
                "message": f"Error en verificaciones: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def generate_compliance_report(self) -> Optional[str]:
        """Generar reporte de compliance"""
        try:
            if not self.reports_enabled:
                return None
            
            # Ejecutar verificaciones
            compliance_results = await self.run_all_compliance_checks()
            
            # Generar reporte
            report = {
                "report_id": f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "compliance_results": compliance_results,
                "metrics": self.get_metrics(),
                "configuration": {
                    "gdpr": self.gdpr_config,
                    "mifid2": self.mifid2_config
                }
            }
            
            # Guardar reporte
            report_path = self._get_report_path()
            report_dir = Path(report_path).parent
            report_dir.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # Actualizar métricas
            self.metrics["reports_generated_total"] += 1
            self.metrics["last_report_time"] = datetime.now(timezone.utc)
            
            logger.info(f"Reporte de compliance generado: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generando reporte de compliance: {e}")
            return None
    
    def _get_report_path(self) -> str:
        """Obtener path del reporte"""
        try:
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            
            path = self.reports_path.format(
                date=date_str,
                timestamp=timestamp_str
            )
            
            return path
            
        except Exception as e:
            logger.error(f"Error generando path del reporte: {e}")
            return f"reports/compliance/{datetime.now().strftime('%Y%m%d')}/compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    async def run_automatic_checks(self):
        """Ejecutar checks automáticos configurados"""
        try:
            for check_config in self.checks_config:
                check_name = check_config.get("name", "")
                frequency = check_config.get("frequency", "daily")
                description = check_config.get("description", "")
                
                # Verificar si es momento de ejecutar el check
                if self._should_run_check(check_name, frequency):
                    logger.info(f"Ejecutando check automático: {check_name}")
                    
                    # Ejecutar check específico
                    if check_name == "data_retention_check":
                        await self._check_data_retention()
                    elif check_name == "encryption_check":
                        await self._check_encryption()
                    elif check_name == "access_control_check":
                        await self._check_access_control()
                    elif check_name == "audit_log_check":
                        await self._check_audit_logs()
                    
                    # Actualizar timestamp del último check
                    self._update_check_timestamp(check_name)
            
        except Exception as e:
            logger.error(f"Error ejecutando checks automáticos: {e}")
    
    def _should_run_check(self, check_name: str, frequency: str) -> bool:
        """Verificar si un check debe ejecutarse"""
        try:
            # Implementar lógica de frecuencia
            # Por simplicidad, siempre ejecutar en este ejemplo
            return True
            
        except Exception as e:
            logger.error(f"Error verificando frecuencia de check {check_name}: {e}")
            return False
    
    def _update_check_timestamp(self, check_name: str):
        """Actualizar timestamp del último check"""
        try:
            # Implementar almacenamiento de timestamps
            # Por simplicidad, no hacer nada en este ejemplo
            pass
            
        except Exception as e:
            logger.error(f"Error actualizando timestamp de check {check_name}: {e}")
    
    async def _check_data_retention(self):
        """Verificar retención de datos"""
        try:
            # Implementar verificación de retención de datos
            logger.info("Verificando retención de datos...")
            
        except Exception as e:
            logger.error(f"Error verificando retención de datos: {e}")
    
    async def _check_encryption(self):
        """Verificar encriptación"""
        try:
            # Implementar verificación de encriptación
            logger.info("Verificando encriptación...")
            
        except Exception as e:
            logger.error(f"Error verificando encriptación: {e}")
    
    async def _check_access_control(self):
        """Verificar controles de acceso"""
        try:
            # Implementar verificación de controles de acceso
            logger.info("Verificando controles de acceso...")
            
        except Exception as e:
            logger.error(f"Error verificando controles de acceso: {e}")
    
    async def _check_audit_logs(self):
        """Verificar logs de auditoría"""
        try:
            # Implementar verificación de logs de auditoría
            logger.info("Verificando logs de auditoría...")
            
        except Exception as e:
            logger.error(f"Error verificando logs de auditoría: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del verificador de compliance"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del verificador de compliance"""
        return {
            "is_running": True,
            "reports_enabled": self.reports_enabled,
            "reports_frequency": self.reports_frequency,
            "reports_path": self.reports_path,
            "gdpr_enabled": self.gdpr_config.get("enabled", True),
            "mifid2_enabled": self.mifid2_config.get("enabled", True),
            "automatic_checks": len(self.checks_config),
            "metrics": self.get_metrics()
        }
    
    async def health_check(self) -> bool:
        """Verificar salud del verificador de compliance"""
        try:
            # Verificar que la configuración esté cargada
            if not self.compliance_config:
                return False
            
            # Verificar que los directorios existan
            if self.reports_enabled:
                reports_dir = Path("reports/compliance")
                if not reports_dir.exists():
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False

# Función de conveniencia para crear verificador
def create_compliance_checker() -> ComplianceChecker:
    """Crear instancia del verificador de compliance"""
    return ComplianceChecker()

if __name__ == "__main__":
    # Test del verificador de compliance
    async def test_compliance_checker():
        checker = ComplianceChecker()
        try:
            await checker.start()
            
            # Test de health check
            health = await checker.health_check()
            print(f"Health check: {health}")
            
            # Test de verificación GDPR
            gdpr_result = await checker.run_compliance_check(ComplianceStandard.GDPR)
            print(f"GDPR compliance: {gdpr_result}")
            
            # Test de verificación MiFID II
            mifid2_result = await checker.run_compliance_check(ComplianceStandard.MIFID2)
            print(f"MiFID II compliance: {mifid2_result}")
            
            # Test de todas las verificaciones
            all_results = await checker.run_all_compliance_checks()
            print(f"Todas las verificaciones: {all_results}")
            
            # Test de generación de reporte
            report_path = await checker.generate_compliance_report()
            print(f"Reporte generado: {report_path}")
            
            # Mostrar métricas
            print("\n=== MÉTRICAS DEL VERIFICADOR DE COMPLIANCE ===")
            metrics = checker.get_metrics()
            for key, value in metrics.items():
                print(f"{key}: {value}")
            
        finally:
            await checker.stop()
    
    # Ejecutar test
    import asyncio
    asyncio.run(test_compliance_checker())
