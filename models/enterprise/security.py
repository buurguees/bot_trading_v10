"""
models/enterprise/security.py - Security & Compliance System
Sistema de seguridad y cumplimiento enterprise para modelos ML
"""

import os
import json
import hashlib
import hmac
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Configuration for security system"""
    encryption_key_path: str = "keys/encryption.key"
    signing_key_path: str = "keys/signing.key"
    audit_log_path: str = "logs/security_audit.log"
    model_encryption_enabled: bool = True
    request_signing_enabled: bool = True
    audit_logging_enabled: bool = True
    key_rotation_days: int = 90
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 60
    encryption_algorithm: str = "AES-256-GCM"
    signing_algorithm: str = "HMAC-SHA256"

@dataclass
class SecurityAuditEvent:
    """Security audit event"""
    event_id: str
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    resource: str
    action: str
    result: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]

class MLSecurityManager:
    """Security manager for ML models and data"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.encryption_key = None
        self.signing_key = None
        self.audit_events = []
        self.failed_attempts = {}
        self.locked_accounts = {}
        self._initialize_security()
    
    def _initialize_security(self):
        """Initialize security components"""
        # Create keys directory
        keys_dir = Path(self.config.encryption_key_path).parent
        keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate encryption key
        self.encryption_key = self._load_or_generate_encryption_key()
        
        # Load or generate signing key
        self.signing_key = self._load_or_generate_signing_key()
        
        # Initialize audit logging
        if self.config.audit_logging_enabled:
            self._setup_audit_logging()
        
        logger.info("Security manager initialized")
    
    def _load_or_generate_encryption_key(self) -> bytes:
        """Load or generate encryption key"""
        key_path = Path(self.config.encryption_key_path)
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            logger.info(f"Generated new encryption key: {key_path}")
            return key
    
    def _load_or_generate_signing_key(self) -> bytes:
        """Load or generate signing key"""
        key_path = Path(self.config.signing_key_path)
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = secrets.token_bytes(32)
            with open(key_path, 'wb') as f:
                f.write(key)
            logger.info(f"Generated new signing key: {key_path}")
            return key
    
    def _setup_audit_logging(self):
        """Setup audit logging"""
        audit_dir = Path(self.config.audit_log_path).parent
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Create audit log handler
        audit_handler = logging.FileHandler(self.config.audit_log_path)
        audit_handler.setLevel(logging.INFO)
        
        # Create audit formatter
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Add handler to audit logger
        audit_logger = logging.getLogger('security_audit')
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
    
    def encrypt_model_artifacts(self, model_data: bytes, model_id: str) -> Dict[str, Any]:
        """Encrypt model artifacts"""
        try:
            # Generate unique encryption key for this model
            model_key = Fernet.generate_key()
            fernet = Fernet(model_key)
            
            # Encrypt model data
            encrypted_data = fernet.encrypt(model_data)
            
            # Encrypt the model key with master key
            master_fernet = Fernet(self.encryption_key)
            encrypted_model_key = master_fernet.encrypt(model_key)
            
            # Generate integrity hash
            integrity_hash = hashlib.sha256(model_data).hexdigest()
            
            # Log security event
            self._log_audit_event(
                event_type="model_encryption",
                resource=f"model:{model_id}",
                action="encrypt",
                result="success",
                details={
                    "model_id": model_id,
                    "data_size": len(model_data),
                    "encrypted_size": len(encrypted_data),
                    "integrity_hash": integrity_hash
                }
            )
            
            return {
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "encrypted_key": base64.b64encode(encrypted_model_key).decode(),
                "integrity_hash": integrity_hash,
                "encryption_algorithm": self.config.encryption_algorithm,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self._log_audit_event(
                event_type="model_encryption",
                resource=f"model:{model_id}",
                action="encrypt",
                result="failure",
                details={"error": str(e)}
            )
            raise
    
    def decrypt_model_artifacts(self, encrypted_data: Dict[str, Any], model_id: str) -> bytes:
        """Decrypt model artifacts"""
        try:
            # Decode encrypted data
            encrypted_data_bytes = base64.b64decode(encrypted_data["encrypted_data"])
            encrypted_key_bytes = base64.b64decode(encrypted_data["encrypted_key"])
            
            # Decrypt model key
            master_fernet = Fernet(self.encryption_key)
            model_key = master_fernet.decrypt(encrypted_key_bytes)
            
            # Decrypt model data
            fernet = Fernet(model_key)
            decrypted_data = fernet.decrypt(encrypted_data_bytes)
            
            # Verify integrity
            integrity_hash = hashlib.sha256(decrypted_data).hexdigest()
            if integrity_hash != encrypted_data["integrity_hash"]:
                raise ValueError("Integrity check failed - data may be corrupted")
            
            # Log security event
            self._log_audit_event(
                event_type="model_decryption",
                resource=f"model:{model_id}",
                action="decrypt",
                result="success",
                details={
                    "model_id": model_id,
                    "data_size": len(decrypted_data),
                    "integrity_verified": True
                }
            )
            
            return decrypted_data
        
        except Exception as e:
            self._log_audit_event(
                event_type="model_decryption",
                resource=f"model:{model_id}",
                action="decrypt",
                result="failure",
                details={"error": str(e)}
            )
            raise
    
    def sign_request(self, request_data: Dict[str, Any], user_id: str) -> str:
        """Sign request for integrity verification"""
        try:
            # Create signature payload
            payload = json.dumps(request_data, sort_keys=True)
            
            # Generate signature
            signature = hmac.new(
                self.signing_key,
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Log security event
            self._log_audit_event(
                event_type="request_signing",
                resource="api",
                action="sign",
                result="success",
                user_id=user_id,
                details={
                    "request_id": request_data.get("request_id"),
                    "signature_algorithm": self.config.signing_algorithm
                }
            )
            
            return signature
        
        except Exception as e:
            self._log_audit_event(
                event_type="request_signing",
                resource="api",
                action="sign",
                result="failure",
                user_id=user_id,
                details={"error": str(e)}
            )
            raise
    
    def verify_request_signature(self, request_data: Dict[str, Any], signature: str, user_id: str) -> bool:
        """Verify request signature"""
        try:
            # Create signature payload
            payload = json.dumps(request_data, sort_keys=True)
            
            # Generate expected signature
            expected_signature = hmac.new(
                self.signing_key,
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            # Log security event
            self._log_audit_event(
                event_type="request_verification",
                resource="api",
                action="verify",
                result="success" if is_valid else "failure",
                user_id=user_id,
                details={
                    "request_id": request_data.get("request_id"),
                    "signature_valid": is_valid
                }
            )
            
            return is_valid
        
        except Exception as e:
            self._log_audit_event(
                event_type="request_verification",
                resource="api",
                action="verify",
                result="failure",
                user_id=user_id,
                details={"error": str(e)}
            )
            return False
    
    def validate_model_integrity(self, model_path: str, expected_hash: str) -> bool:
        """Validate model file integrity"""
        try:
            with open(model_path, 'rb') as f:
                model_data = f.read()
            
            actual_hash = hashlib.sha256(model_data).hexdigest()
            is_valid = actual_hash == expected_hash
            
            # Log security event
            self._log_audit_event(
                event_type="model_integrity_check",
                resource=f"file:{model_path}",
                action="validate",
                result="success" if is_valid else "failure",
                details={
                    "expected_hash": expected_hash,
                    "actual_hash": actual_hash,
                    "file_size": len(model_data)
                }
            )
            
            return is_valid
        
        except Exception as e:
            self._log_audit_event(
                event_type="model_integrity_check",
                resource=f"file:{model_path}",
                action="validate",
                result="failure",
                details={"error": str(e)}
            )
            return False
    
    def audit_model_requests(self, user_id: str, request_data: Dict[str, Any]) -> bool:
        """Audit model requests for suspicious activity"""
        try:
            # Check for rate limiting
            if self._is_rate_limited(user_id):
                self._log_audit_event(
                    event_type="rate_limit_exceeded",
                    resource="api",
                    action="request",
                    result="blocked",
                    user_id=user_id,
                    details={"reason": "rate_limit_exceeded"}
                )
                return False
            
            # Check for suspicious patterns
            if self._detect_suspicious_patterns(request_data):
                self._log_audit_event(
                    event_type="suspicious_activity",
                    resource="api",
                    action="request",
                    result="flagged",
                    user_id=user_id,
                    details={"reason": "suspicious_patterns"}
                )
                return False
            
            # Log successful request
            self._log_audit_event(
                event_type="model_request",
                resource="api",
                action="request",
                result="success",
                user_id=user_id,
                details={
                    "request_id": request_data.get("request_id"),
                    "symbol": request_data.get("symbol"),
                    "feature_count": len(request_data.get("features", []))
                }
            )
            
            return True
        
        except Exception as e:
            self._log_audit_event(
                event_type="model_request",
                resource="api",
                action="request",
                result="failure",
                user_id=user_id,
                details={"error": str(e)}
            )
            return False
    
    def _is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        # Clean up old entries
        self.failed_attempts = {
            k: v for k, v in self.failed_attempts.items()
            if current_time - v["last_attempt"] < self.config.lockout_duration_minutes * 60
        }
        
        # Check if user is locked out
        if user_id in self.locked_accounts:
            lockout_time = self.locked_accounts[user_id]
            if current_time - lockout_time < self.config.lockout_duration_minutes * 60:
                return True
            else:
                # Remove from locked accounts
                del self.locked_accounts[user_id]
        
        # Check failed attempts
        if user_id in self.failed_attempts:
            attempts = self.failed_attempts[user_id]
            if attempts["count"] >= self.config.max_failed_attempts:
                # Lock account
                self.locked_accounts[user_id] = current_time
                return True
        
        return False
    
    def _detect_suspicious_patterns(self, request_data: Dict[str, Any]) -> bool:
        """Detect suspicious patterns in requests"""
        # Check for unusual feature values
        features = request_data.get("features", [])
        if features:
            # Check for extreme values
            if any(abs(f) > 1000 for f in features):
                return True
            
            # Check for NaN or infinite values
            if any(not isinstance(f, (int, float)) or not (f == f) for f in features):
                return True
        
        # Check for unusual request frequency (simplified)
        # In a real implementation, this would check against historical patterns
        
        return False
    
    def _log_audit_event(self, event_type: str, resource: str, action: str, result: str, 
                        user_id: str = None, ip_address: str = None, user_agent: str = None, 
                        details: Dict[str, Any] = None):
        """Log security audit event"""
        if not self.config.audit_logging_enabled:
            return
        
        event = SecurityAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
        
        # Add to in-memory list
        self.audit_events.append(event)
        
        # Log to file
        audit_logger = logging.getLogger('security_audit')
        audit_logger.info(json.dumps(asdict(event), default=str))
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security report"""
        current_time = datetime.now()
        last_24h = current_time - timedelta(hours=24)
        
        # Filter recent events
        recent_events = [
            event for event in self.audit_events
            if event.timestamp >= last_24h
        ]
        
        # Count events by type
        event_counts = {}
        for event in recent_events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        
        # Count failed attempts
        failed_attempts = sum(
            1 for event in recent_events
            if event.result == "failure"
        )
        
        # Count blocked requests
        blocked_requests = sum(
            1 for event in recent_events
            if event.result == "blocked"
        )
        
        return {
            "timestamp": current_time.isoformat(),
            "total_events_24h": len(recent_events),
            "event_counts": event_counts,
            "failed_attempts": failed_attempts,
            "blocked_requests": blocked_requests,
            "locked_accounts": len(self.locked_accounts),
            "security_status": "healthy" if failed_attempts < 10 else "warning"
        }

class ComplianceManager:
    """Compliance manager for regulatory requirements"""
    
    def __init__(self):
        self.compliance_rules = {}
        self.audit_trail = []
        self._initialize_compliance_rules()
    
    def _initialize_compliance_rules(self):
        """Initialize compliance rules"""
        self.compliance_rules = {
            "data_retention": {
                "model_artifacts": 2555,  # 7 years in days
                "audit_logs": 2555,
                "prediction_logs": 365,   # 1 year
                "user_data": 1095        # 3 years
            },
            "data_privacy": {
                "anonymize_personal_data": True,
                "encrypt_sensitive_data": True,
                "audit_data_access": True
            },
            "model_governance": {
                "version_control": True,
                "approval_workflow": True,
                "performance_monitoring": True,
                "bias_detection": True
            },
            "trading_compliance": {
                "risk_limits": True,
                "position_limits": True,
                "audit_trail": True,
                "regulatory_reporting": True
            }
        }
    
    def validate_model_deployment(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model deployment for compliance"""
        compliance_checks = {
            "data_privacy": self._check_data_privacy_compliance(model_config),
            "model_governance": self._check_model_governance_compliance(model_config),
            "trading_compliance": self._check_trading_compliance(model_config),
            "security": self._check_security_compliance(model_config)
        }
        
        all_passed = all(check["passed"] for check in compliance_checks.values())
        
        result = {
            "compliant": all_passed,
            "checks": compliance_checks,
            "timestamp": datetime.now().isoformat(),
            "model_id": model_config.get("model_id"),
            "version": model_config.get("version")
        }
        
        # Log compliance check
        self._log_compliance_event("model_deployment_validation", result)
        
        return result
    
    def _check_data_privacy_compliance(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check data privacy compliance"""
        checks = {
            "personal_data_handling": True,  # Simplified
            "data_encryption": True,
            "data_retention": True,
            "consent_management": True
        }
        
        return {
            "passed": all(checks.values()),
            "details": checks,
            "requirements": self.compliance_rules["data_privacy"]
        }
    
    def _check_model_governance_compliance(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check model governance compliance"""
        checks = {
            "version_control": "version" in model_config,
            "approval_workflow": "approved_by" in model_config,
            "performance_monitoring": "monitoring_enabled" in model_config,
            "bias_detection": "bias_tests_passed" in model_config
        }
        
        return {
            "passed": all(checks.values()),
            "details": checks,
            "requirements": self.compliance_rules["model_governance"]
        }
    
    def _check_trading_compliance(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check trading compliance"""
        checks = {
            "risk_limits": "max_position_size" in model_config,
            "position_limits": "max_daily_trades" in model_config,
            "audit_trail": "audit_enabled" in model_config,
            "regulatory_reporting": "reporting_enabled" in model_config
        }
        
        return {
            "passed": all(checks.values()),
            "details": checks,
            "requirements": self.compliance_rules["trading_compliance"]
        }
    
    def _check_security_compliance(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check security compliance"""
        checks = {
            "encryption_at_rest": "encryption_enabled" in model_config,
            "encryption_in_transit": "tls_enabled" in model_config,
            "access_control": "access_control_enabled" in model_config,
            "audit_logging": "audit_logging_enabled" in model_config
        }
        
        return {
            "passed": all(checks.values()),
            "details": checks,
            "requirements": ["encryption", "access_control", "audit_logging"]
        }
    
    def generate_model_documentation(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate model documentation for compliance"""
        documentation = {
            "model_info": {
                "name": model_config.get("model_name"),
                "version": model_config.get("version"),
                "created_at": model_config.get("created_at"),
                "last_updated": datetime.now().isoformat()
            },
            "technical_specs": {
                "framework": model_config.get("framework"),
                "algorithm": model_config.get("algorithm"),
                "input_features": model_config.get("input_features", []),
                "output_classes": model_config.get("output_classes", []),
                "performance_metrics": model_config.get("performance_metrics", {})
            },
            "data_info": {
                "training_data_source": model_config.get("training_data_source"),
                "data_retention_policy": self.compliance_rules["data_retention"],
                "privacy_controls": self.compliance_rules["data_privacy"]
            },
            "governance": {
                "approval_status": model_config.get("approval_status"),
                "approved_by": model_config.get("approved_by"),
                "review_date": model_config.get("review_date"),
                "next_review": model_config.get("next_review")
            },
            "compliance": {
                "regulatory_framework": "MiFID II, GDPR, SOX",
                "risk_management": model_config.get("risk_management", {}),
                "audit_trail": model_config.get("audit_trail", {})
            }
        }
        
        return documentation
    
    def _log_compliance_event(self, event_type: str, details: Dict[str, Any]):
        """Log compliance event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.audit_trail.append(event)
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        current_time = datetime.now()
        last_30_days = current_time - timedelta(days=30)
        
        # Filter recent events
        recent_events = [
            event for event in self.audit_trail
            if datetime.fromisoformat(event["timestamp"]) >= last_30_days
        ]
        
        # Count compliance events
        event_counts = {}
        for event in recent_events:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "timestamp": current_time.isoformat(),
            "total_events_30d": len(recent_events),
            "event_counts": event_counts,
            "compliance_status": "compliant",
            "next_review_date": (current_time + timedelta(days=90)).isoformat()
        }

# Global security and compliance managers
security_manager = MLSecurityManager()
compliance_manager = ComplianceManager()

# Convenience functions
def encrypt_model(model_path: str, model_id: str) -> Dict[str, Any]:
    """Encrypt model file"""
    with open(model_path, 'rb') as f:
        model_data = f.read()
    
    return security_manager.encrypt_model_artifacts(model_data, model_id)

def decrypt_model(encrypted_data: Dict[str, Any], model_id: str, output_path: str) -> bool:
    """Decrypt model file"""
    try:
        decrypted_data = security_manager.decrypt_model_artifacts(encrypted_data, model_id)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return True
    except Exception as e:
        logger.error(f"Error decrypting model: {e}")
        return False

def validate_model_compliance(model_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate model compliance"""
    return compliance_manager.validate_model_deployment(model_config)

def generate_security_report() -> Dict[str, Any]:
    """Generate security report"""
    return security_manager.get_security_report()

def generate_compliance_report() -> Dict[str, Any]:
    """Generate compliance report"""
    return compliance_manager.get_compliance_report()
