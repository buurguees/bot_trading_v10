# Ruta: core/ml/enterprise/security_system.py
#!/usr/bin/env python3
"""
Enterprise Security System - Sistema de Seguridad y Compliance
==============================================================

Sistema enterprise-grade para seguridad y compliance con:
- Encriptación de datos sensibles
- Auditoría completa de operaciones
- Cumplimiento de regulaciones (GDPR, MiFID II, etc.)
- Gestión de secretos y API keys
- Logging de seguridad
- Detección de anomalías

Uso:
    from models.enterprise.security_system import EnterpriseSecuritySystem
    
    security = EnterpriseSecuritySystem()
    await security.encrypt_sensitive_data(data)
"""

import asyncio
import logging
import hashlib
import hmac
import secrets
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import os
import sys

# Criptografía
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Configuración del sistema de seguridad"""
    # Encriptación
    encryption_algorithm: str = "AES-256-GCM"
    key_derivation_algorithm: str = "PBKDF2"
    key_length: int = 32
    salt_length: int = 16
    iterations: int = 100000
    
    # Auditoría
    enable_audit_logging: bool = True
    audit_log_file: str = "logs/security_audit.log"
    audit_retention_days: int = 365
    
    # Compliance
    enable_gdpr_compliance: bool = True
    enable_mifid_compliance: bool = True
    data_retention_days: int = 2555  # 7 años para MiFID II
    
    # Detección de anomalías
    enable_anomaly_detection: bool = True
    anomaly_threshold: float = 0.8
    max_failed_attempts: int = 5
    
    # Gestión de secretos
    secrets_manager_type: str = "file"  # file, aws_secrets, azure_keyvault
    secrets_file: str = "secrets/encrypted_secrets.json"
    
    # Logging de seguridad
    security_log_file: str = "logs/security.log"
    log_level: str = "INFO"

class DataEncryption:
    """Sistema de encriptación de datos"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._master_key = None
        self._fernet = None
    
    def _generate_master_key(self, password: str = None) -> bytes:
        """Genera clave maestra"""
        if password is None:
            password = os.environ.get("TRADING_BOT_MASTER_PASSWORD", "default_password")
        
        # Generar salt
        salt = os.urandom(self.config.salt_length)
        
        # Derivar clave
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.config.key_length,
            salt=salt,
            iterations=self.config.iterations
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_fernet(self) -> Fernet:
        """Obtiene instancia de Fernet"""
        if self._fernet is None:
            if self._master_key is None:
                self._master_key = self._generate_master_key()
            self._fernet = Fernet(self._master_key)
        
        return self._fernet
    
    def encrypt_data(self, data: Any) -> str:
        """Encripta datos"""
        try:
            # Serializar datos
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data).encode()
            else:
                serialized_data = pickle.dumps(data)
            
            # Encriptar
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(serialized_data)
            
            # Codificar en base64
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Error encriptando datos: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """Desencripta datos"""
        try:
            # Decodificar base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            
            # Desencriptar
            fernet = self._get_fernet()
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            # Deserializar
            try:
                return json.loads(decrypted_data.decode())
            except json.JSONDecodeError:
                return pickle.loads(decrypted_data)
                
        except Exception as e:
            self.logger.error(f"Error desencriptando datos: {e}")
            raise
    
    def encrypt_file(self, file_path: str, output_path: str = None) -> str:
        """Encripta archivo"""
        if output_path is None:
            output_path = f"{file_path}.encrypted"
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = self._get_fernet().encrypt(data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        self.logger.info(f"Archivo encriptado: {file_path} -> {output_path}")
        return output_path
    
    def decrypt_file(self, encrypted_file_path: str, output_path: str = None) -> str:
        """Desencripta archivo"""
        if output_path is None:
            output_path = encrypted_file_path.replace('.encrypted', '')
        
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self._get_fernet().decrypt(encrypted_data)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        self.logger.info(f"Archivo desencriptado: {encrypted_file_path} -> {output_path}")
        return output_path

class AuditLogger:
    """Sistema de auditoría"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setup_audit_logging()
    
    def _setup_audit_logging(self):
        """Configura logging de auditoría"""
        if self.config.enable_audit_logging:
            # Crear directorio de logs
            log_dir = Path(self.config.audit_log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Configurar handler de auditoría
            audit_handler = logging.FileHandler(self.config.audit_log_file)
            audit_handler.setLevel(logging.INFO)
            
            # Formato de auditoría
            audit_format = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            audit_handler.setFormatter(audit_format)
            
            # Agregar handler
            self.logger.addHandler(audit_handler)
    
    def log_operation(
        self,
        operation: str,
        user_id: str = None,
        resource: str = None,
        details: Dict[str, Any] = None,
        success: bool = True
    ):
        """Registra operación en auditoría"""
        if not self.config.enable_audit_logging:
            return
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "user_id": user_id or "system",
            "resource": resource,
            "success": success,
            "details": details or {}
        }
        
        # Log nivel INFO para auditoría
        self.logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    def log_data_access(
        self,
        data_type: str,
        data_id: str,
        user_id: str = None,
        access_type: str = "read",
        success: bool = True
    ):
        """Registra acceso a datos"""
        self.log_operation(
            operation=f"data_{access_type}",
            user_id=user_id,
            resource=f"{data_type}:{data_id}",
            details={
                "data_type": data_type,
                "data_id": data_id,
                "access_type": access_type
            },
            success=success
        )
    
    def log_model_training(
        self,
        model_id: str,
        user_id: str = None,
        training_config: Dict[str, Any] = None,
        success: bool = True
    ):
        """Registra entrenamiento de modelo"""
        self.log_operation(
            operation="model_training",
            user_id=user_id,
            resource=f"model:{model_id}",
            details={
                "model_id": model_id,
                "training_config": training_config or {}
            },
            success=success
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        details: Dict[str, Any] = None
    ):
        """Registra evento de seguridad"""
        self.log_operation(
            operation="security_event",
            resource=event_type,
            details={
                "event_type": event_type,
                "severity": severity,
                "details": details or {}
            },
            success=False  # Eventos de seguridad son generalmente negativos
        )

class ComplianceManager:
    """Gestor de compliance"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger(config)
    
    def check_gdpr_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica cumplimiento GDPR"""
        if not self.config.enable_gdpr_compliance:
            return {"compliant": True, "issues": []}
        
        issues = []
        
        # Verificar datos personales
        personal_data_fields = ["email", "phone", "name", "address", "ssn", "passport"]
        for field in personal_data_fields:
            if field in data:
                issues.append(f"Campo personal detectado: {field}")
        
        # Verificar consentimiento
        if "consent" not in data:
            issues.append("Falta consentimiento explícito")
        
        # Verificar propósito específico
        if "purpose" not in data:
            issues.append("Falta especificación del propósito")
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "regulation": "GDPR"
        }
    
    def check_mifid_compliance(self, trading_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica cumplimiento MiFID II"""
        if not self.config.enable_mifid_compliance:
            return {"compliant": True, "issues": []}
        
        issues = []
        
        # Verificar campos requeridos para trading
        required_fields = ["timestamp", "symbol", "price", "quantity", "side"]
        for field in required_fields:
            if field not in trading_data:
                issues.append(f"Campo requerido faltante: {field}")
        
        # Verificar timestamp válido
        if "timestamp" in trading_data:
            try:
                datetime.fromisoformat(trading_data["timestamp"])
            except ValueError:
                issues.append("Timestamp inválido")
        
        # Verificar precios positivos
        if "price" in trading_data:
            try:
                price = float(trading_data["price"])
                if price <= 0:
                    issues.append("Precio debe ser positivo")
            except (ValueError, TypeError):
                issues.append("Precio inválido")
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "regulation": "MiFID II"
        }
    
    def check_data_retention(self, data_timestamp: str) -> bool:
        """Verifica si los datos están dentro del período de retención"""
        try:
            data_date = datetime.fromisoformat(data_timestamp)
            retention_limit = datetime.now() - timedelta(days=self.config.data_retention_days)
            return data_date >= retention_limit
        except ValueError:
            return False
    
    def anonymize_personal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonimiza datos personales"""
        anonymized_data = data.copy()
        
        # Campos a anonimizar
        personal_fields = ["email", "phone", "name", "address", "ssn", "passport"]
        
        for field in personal_fields:
            if field in anonymized_data:
                # Hash del valor original
                hashed_value = hashlib.sha256(str(anonymized_data[field]).encode()).hexdigest()[:8]
                anonymized_data[field] = f"ANONYMIZED_{hashed_value}"
        
        return anonymized_data

class SecretsManager:
    """Gestor de secretos"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.encryption = DataEncryption(config)
        self._secrets_cache = {}
    
    def store_secret(self, key: str, value: str, description: str = None):
        """Almacena secreto encriptado"""
        try:
            # Cargar secretos existentes
            secrets_data = self._load_secrets()
            
            # Agregar nuevo secreto
            secrets_data[key] = {
                "value": self.encryption.encrypt_data(value),
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Guardar secretos
            self._save_secrets(secrets_data)
            
            self.logger.info(f"Secreto almacenado: {key}")
            
        except Exception as e:
            self.logger.error(f"Error almacenando secreto {key}: {e}")
            raise
    
    def get_secret(self, key: str) -> str:
        """Obtiene secreto desencriptado"""
        try:
            # Verificar cache
            if key in self._secrets_cache:
                return self._secrets_cache[key]
            
            # Cargar secretos
            secrets_data = self._load_secrets()
            
            if key not in secrets_data:
                raise KeyError(f"Secreto no encontrado: {key}")
            
            # Desencriptar valor
            encrypted_value = secrets_data[key]["value"]
            decrypted_value = self.encryption.decrypt_data(encrypted_value)
            
            # Cachear
            self._secrets_cache[key] = decrypted_value
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(f"Error obteniendo secreto {key}: {e}")
            raise
    
    def list_secrets(self) -> List[str]:
        """Lista todas las claves de secretos"""
        try:
            secrets_data = self._load_secrets()
            return list(secrets_data.keys())
        except Exception as e:
            self.logger.error(f"Error listando secretos: {e}")
            return []
    
    def delete_secret(self, key: str):
        """Elimina secreto"""
        try:
            secrets_data = self._load_secrets()
            
            if key in secrets_data:
                del secrets_data[key]
                self._save_secrets(secrets_data)
                
                # Remover del cache
                if key in self._secrets_cache:
                    del self._secrets_cache[key]
                
                self.logger.info(f"Secreto eliminado: {key}")
            else:
                raise KeyError(f"Secreto no encontrado: {key}")
                
        except Exception as e:
            self.logger.error(f"Error eliminando secreto {key}: {e}")
            raise
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Carga secretos desde archivo"""
        secrets_file = Path(self.config.secrets_file)
        
        if not secrets_file.exists():
            return {}
        
        try:
            with open(secrets_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando secretos: {e}")
            return {}
    
    def _save_secrets(self, secrets_data: Dict[str, Any]):
        """Guarda secretos en archivo"""
        secrets_file = Path(self.config.secrets_file)
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(secrets_file, 'w') as f:
                json.dump(secrets_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando secretos: {e}")
            raise

class AnomalyDetector:
    """Detector de anomalías de seguridad"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.audit_logger = AuditLogger(config)
        self._failed_attempts = {}
        self._suspicious_activities = []
    
    def detect_anomaly(
        self,
        operation: str,
        user_id: str = None,
        resource: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Detecta anomalías en operaciones"""
        if not self.config.enable_anomaly_detection:
            return False
        
        is_anomaly = False
        anomaly_reasons = []
        
        # Detectar intentos fallidos repetidos
        if user_id:
            if user_id not in self._failed_attempts:
                self._failed_attempts[user_id] = 0
            
            if operation.endswith("_failed"):
                self._failed_attempts[user_id] += 1
                
                if self._failed_attempts[user_id] >= self.config.max_failed_attempts:
                    is_anomaly = True
                    anomaly_reasons.append("Múltiples intentos fallidos")
            else:
                # Resetear contador en operación exitosa
                self._failed_attempts[user_id] = 0
        
        # Detectar operaciones en horarios inusuales
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            is_anomaly = True
            anomaly_reasons.append("Operación en horario inusual")
        
        # Detectar acceso a recursos sensibles
        sensitive_resources = ["model", "training_data", "secrets", "config"]
        if resource and any(sensitive in resource.lower() for sensitive in sensitive_resources):
            is_anomaly = True
            anomaly_reasons.append("Acceso a recurso sensible")
        
        # Detectar patrones de acceso anómalos
        if metadata and "frequency" in metadata:
            if metadata["frequency"] > 100:  # Más de 100 operaciones por minuto
                is_anomaly = True
                anomaly_reasons.append("Frecuencia de acceso anómala")
        
        # Registrar anomalía si se detecta
        if is_anomaly:
            self._log_anomaly(operation, user_id, resource, anomaly_reasons)
        
        return is_anomaly
    
    def _log_anomaly(
        self,
        operation: str,
        user_id: str,
        resource: str,
        reasons: List[str]
    ):
        """Registra anomalía detectada"""
        anomaly_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "resource": resource,
            "reasons": reasons,
            "severity": "high" if len(reasons) > 1 else "medium"
        }
        
        self._suspicious_activities.append(anomaly_entry)
        
        # Log de seguridad
        self.audit_logger.log_security_event(
            event_type="anomaly_detected",
            severity=anomaly_entry["severity"],
            details=anomaly_entry
        )
        
        self.logger.warning(f"ANOMALÍA DETECTADA: {json.dumps(anomaly_entry)}")
    
    def get_anomaly_report(self) -> Dict[str, Any]:
        """Obtiene reporte de anomalías"""
        return {
            "total_anomalies": len(self._suspicious_activities),
            "failed_attempts": dict(self._failed_attempts),
            "recent_anomalies": self._suspicious_activities[-10:],  # Últimas 10
            "timestamp": datetime.now().isoformat()
        }

class EnterpriseSecuritySystem:
    """Sistema de seguridad enterprise"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.logger = logging.getLogger(__name__)
        
        # Configurar logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.security_log_file),
                logging.StreamHandler()
            ]
        )
        
        # Componentes
        self.encryption = DataEncryption(self.config)
        self.audit_logger = AuditLogger(self.config)
        self.compliance = ComplianceManager(self.config)
        self.secrets_manager = SecretsManager(self.config)
        self.anomaly_detector = AnomalyDetector(self.config)
    
    async def encrypt_sensitive_data(self, data: Any) -> str:
        """Encripta datos sensibles"""
        try:
            encrypted_data = self.encryption.encrypt_data(data)
            
            # Log de auditoría
            self.audit_logger.log_operation(
                operation="data_encryption",
                resource="sensitive_data",
                details={"data_type": type(data).__name__},
                success=True
            )
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Error encriptando datos sensibles: {e}")
            raise
    
    async def decrypt_sensitive_data(self, encrypted_data: str) -> Any:
        """Desencripta datos sensibles"""
        try:
            decrypted_data = self.encryption.decrypt_data(encrypted_data)
            
            # Log de auditoría
            self.audit_logger.log_operation(
                operation="data_decryption",
                resource="sensitive_data",
                details={"data_type": type(decrypted_data).__name__},
                success=True
            )
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"Error desencriptando datos sensibles: {e}")
            raise
    
    async def check_compliance(self, data: Dict[str, Any], data_type: str = "general") -> Dict[str, Any]:
        """Verifica cumplimiento de regulaciones"""
        compliance_results = {}
        
        # GDPR compliance
        gdpr_result = self.compliance.check_gdpr_compliance(data)
        compliance_results["gdpr"] = gdpr_result
        
        # MiFID II compliance (para datos de trading)
        if data_type == "trading":
            mifid_result = self.compliance.check_mifid_compliance(data)
            compliance_results["mifid_ii"] = mifid_result
        
        # Log de auditoría
        self.audit_logger.log_operation(
            operation="compliance_check",
            resource=data_type,
            details=compliance_results,
            success=all(result["compliant"] for result in compliance_results.values())
        )
        
        return compliance_results
    
    async def store_api_key(self, key_name: str, api_key: str, description: str = None):
        """Almacena API key de forma segura"""
        try:
            self.secrets_manager.store_secret(
                key=f"api_key_{key_name}",
                value=api_key,
                description=description
            )
            
            # Log de auditoría
            self.audit_logger.log_operation(
                operation="api_key_stored",
                resource=key_name,
                details={"key_name": key_name},
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Error almacenando API key {key_name}: {e}")
            raise
    
    async def get_api_key(self, key_name: str) -> str:
        """Obtiene API key de forma segura"""
        try:
            api_key = self.secrets_manager.get_secret(f"api_key_{key_name}")
            
            # Log de auditoría
            self.audit_logger.log_data_access(
                data_type="api_key",
                data_id=key_name,
                access_type="read",
                success=True
            )
            
            return api_key
            
        except Exception as e:
            self.logger.error(f"Error obteniendo API key {key_name}: {e}")
            raise
    
    async def monitor_operation(
        self,
        operation: str,
        user_id: str = None,
        resource: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Monitorea operación para anomalías"""
        try:
            # Detectar anomalías
            is_anomaly = self.anomaly_detector.detect_anomaly(
                operation=operation,
                user_id=user_id,
                resource=resource,
                metadata=metadata
            )
            
            # Log de auditoría
            self.audit_logger.log_operation(
                operation=operation,
                user_id=user_id,
                resource=resource,
                details=metadata,
                success=not is_anomaly
            )
            
            return not is_anomaly
            
        except Exception as e:
            self.logger.error(f"Error monitoreando operación {operation}: {e}")
            return False
    
    async def get_security_report(self) -> Dict[str, Any]:
        """Obtiene reporte de seguridad"""
        try:
            anomaly_report = self.anomaly_detector.get_anomaly_report()
            
            # Estadísticas de secretos
            secrets_list = self.secrets_manager.list_secrets()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "anomaly_report": anomaly_report,
                "secrets_count": len(secrets_list),
                "compliance_enabled": {
                    "gdpr": self.config.enable_gdpr_compliance,
                    "mifid": self.config.enable_mifid_compliance
                },
                "encryption_enabled": True,
                "audit_logging_enabled": self.config.enable_audit_logging
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generando reporte de seguridad: {e}")
            return {}

# Funciones de utilidad
def create_security_config(
    enable_gdpr: bool = True,
    enable_mifid: bool = True,
    enable_anomaly_detection: bool = True
) -> SecurityConfig:
    """Crea configuración de seguridad"""
    return SecurityConfig(
        enable_gdpr_compliance=enable_gdpr,
        enable_mifid_compliance=enable_mifid,
        enable_anomaly_detection=enable_anomaly_detection
    )

# Ejemplo de uso
async def main():
    """Ejemplo de uso del sistema de seguridad"""
    
    # Crear configuración
    config = create_security_config()
    
    # Crear sistema de seguridad
    security = EnterpriseSecuritySystem(config)
    
    # Encriptar datos sensibles
    sensitive_data = {
        "user_id": "user123",
        "api_key": "sk_live_123456789",
        "trading_data": {
            "symbol": "BTCUSDT",
            "price": 50000,
            "quantity": 0.1
        }
    }
    
    encrypted_data = await security.encrypt_sensitive_data(sensitive_data)
    print(f"Datos encriptados: {encrypted_data[:50]}...")
    
    # Verificar compliance
    compliance_result = await security.check_compliance(sensitive_data, "trading")
    print(f"Compliance: {compliance_result}")
    
    # Almacenar API key
    await security.store_api_key("binance", "sk_live_123456789", "Binance API Key")
    
    # Monitorear operación
    is_safe = await security.monitor_operation(
        operation="model_training",
        user_id="user123",
        resource="model:lstm_attention",
        metadata={"frequency": 5}
    )
    print(f"Operación segura: {is_safe}")
    
    # Obtener reporte de seguridad
    report = await security.get_security_report()
    print(f"Reporte de seguridad: {report}")

if __name__ == "__main__":
    asyncio.run(main())
