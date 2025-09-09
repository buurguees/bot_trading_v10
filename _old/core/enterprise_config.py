"""
core/enterprise_config.py - Enterprise-Grade Configuration System
Sistema de configuración enterprise con seguridad, validación y cumplimiento
"""

import os
import json
import yaml
import hashlib
import hmac
import base64
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
from contextlib import contextmanager
import copy
import re
import secrets

# Security and encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Vault integration
try:
    import hvac
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False

# Keyring for secure key storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Pydantic for validation
try:
    from pydantic import BaseModel, validator, ValidationError, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

# Structured logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

logger = logging.getLogger(__name__)

# Custom Exceptions
class SecurityError(Exception):
    """Security-related configuration error"""
    pass

class ConfigurationError(Exception):
    """Configuration management error"""
    pass

class ValidationError(Exception):
    """Configuration validation error"""
    pass

# Enums
class TradingMode(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"

class Environment(str, Enum):
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"

class AuditEventType(Enum):
    CONFIG_LOADED = "config_loaded"
    CONFIG_UPDATED = "config_updated"
    CONFIG_VALIDATION_FAILED = "config_validation_failed"
    CONFIG_ROLLBACK = "config_rollback"
    SECRET_ACCESSED = "secret_accessed"
    SECRET_ROTATED = "secret_rotated"
    SECURITY_VIOLATION = "security_violation"

@dataclass
class AuditEvent:
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    details: Dict[str, Any] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_config: Optional[Dict[str, Any]] = None

class SecureConfigManager:
    """Enterprise-grade secure configuration management"""
    
    def __init__(self):
        self.vault_client = None
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key) if CRYPTO_AVAILABLE else None
        self._initialize_vault()
        
    def _initialize_vault(self):
        """Initialize HashiCorp Vault connection"""
        if not VAULT_AVAILABLE:
            logger.warning("Vault client not available. Install hvac package.")
            return
            
        vault_url = os.getenv('VAULT_URL', 'https://vault.company.com:8200')
        vault_token = os.getenv('VAULT_TOKEN')
        
        if vault_token:
            try:
                self.vault_client = hvac.Client(url=vault_url, token=vault_token)
                # Test connection
                if self.vault_client.is_authenticated():
                    logger.info("Vault connection established")
                else:
                    logger.warning("Vault authentication failed")
                    self.vault_client = None
            except Exception as e:
                logger.error(f"Vault connection failed: {e}")
                self.vault_client = None
                
    def _get_or_create_encryption_key(self) -> bytes:
        """Get encryption key from secure keyring or create new one"""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available. Using fallback encryption.")
            return b'fallback_key_32_bytes_long_for_testing'
            
        try:
            if KEYRING_AVAILABLE:
                # Try to get existing key from OS keyring
                key_str = keyring.get_password("trading_bot", "config_encryption_key")
                if key_str:
                    return key_str.encode()
                
                # Create new key and store securely
                new_key = Fernet.generate_key()
                keyring.set_password("trading_bot", "config_encryption_key", new_key.decode())
                return new_key
            else:
                # Fallback to environment variable (less secure)
                env_key = os.getenv('TRADING_BOT_ENCRYPTION_KEY')
                if env_key:
                    return env_key.encode()
                raise SecurityError("No encryption key available")
                
        except Exception as e:
            logger.error(f"Error managing encryption key: {e}")
            # Fallback to environment variable (less secure)
            env_key = os.getenv('TRADING_BOT_ENCRYPTION_KEY')
            if env_key:
                return env_key.encode()
            raise SecurityError("No encryption key available")
    
    def encrypt_config(self, config_data: Dict[str, Any]) -> bytes:
        """Encrypt configuration data"""
        if not self.cipher_suite:
            # Fallback to base64 encoding (not secure, for testing only)
            serialized = json.dumps(config_data).encode()
            return base64.b64encode(serialized)
            
        serialized = json.dumps(config_data).encode()
        return self.cipher_suite.encrypt(serialized)
    
    def decrypt_config(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt configuration data"""
        if not self.cipher_suite:
            # Fallback to base64 decoding
            decrypted = base64.b64decode(encrypted_data)
            return json.loads(decrypted.decode())
            
        decrypted = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def store_secret(self, path: str, secret_data: Dict[str, Any]):
        """Store secret in Vault or encrypted local storage"""
        if self.vault_client:
            try:
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=secret_data
                )
                logger.info(f"Secret stored in Vault: {path}")
            except Exception as e:
                logger.error(f"Failed to store secret in Vault: {e}")
                # Fallback to local storage
                self._store_secret_locally(path, secret_data)
        else:
            # Fallback to encrypted local storage
            self._store_secret_locally(path, secret_data)
    
    def retrieve_secret(self, path: str) -> Dict[str, Any]:
        """Retrieve secret from Vault or encrypted local storage"""
        if self.vault_client:
            try:
                response = self.vault_client.secrets.kv.v2.read_secret_version(path=path)
                return response['data']['data']
            except Exception as e:
                logger.error(f"Failed to retrieve secret from Vault: {e}")
                # Fallback to local storage
                return self._retrieve_secret_locally(path)
        else:
            # Fallback to encrypted local storage
            return self._retrieve_secret_locally(path)
    
    def _store_secret_locally(self, path: str, secret_data: Dict[str, Any]):
        """Store secret in encrypted local file"""
        encrypted = self.encrypt_config(secret_data)
        secret_file = Path(f"secrets/{path}.enc")
        secret_file.parent.mkdir(exist_ok=True)
        secret_file.write_bytes(encrypted)
        logger.info(f"Secret stored locally: {secret_file}")
    
    def _retrieve_secret_locally(self, path: str) -> Dict[str, Any]:
        """Retrieve secret from encrypted local file"""
        secret_file = Path(f"secrets/{path}.enc")
        if secret_file.exists():
            encrypted = secret_file.read_bytes()
            return self.decrypt_config(encrypted)
        raise SecurityError(f"Secret not found: {path}")

class APICredentialsManager:
    """Secure API credentials management"""
    
    def __init__(self, secure_manager: SecureConfigManager):
        self.secure_manager = secure_manager
        
    def store_api_credentials(self, exchange: str, credentials: Dict[str, str]):
        """Store API credentials securely"""
        # Validate credentials format
        required_fields = ['api_key', 'secret_key', 'passphrase']
        for field in required_fields:
            if field not in credentials:
                raise ValidationError(f"Missing required field: {field}")
        
        # Store in Vault with rotation metadata
        secret_path = f"trading_bot/api_credentials/{exchange}"
        secret_data = {
            **credentials,
            'created_at': datetime.utcnow().isoformat(),
            'rotation_due': (datetime.utcnow() + timedelta(days=90)).isoformat(),
            'version': 1
        }
        
        self.secure_manager.store_secret(secret_path, secret_data)
        logger.info(f"API credentials stored for {exchange}")
        
    def get_api_credentials(self, exchange: str) -> Dict[str, str]:
        """Retrieve API credentials securely"""
        secret_path = f"trading_bot/api_credentials/{exchange}"
        credentials = self.secure_manager.retrieve_secret(secret_path)
        
        # Check if credentials need rotation
        rotation_due = datetime.fromisoformat(credentials['rotation_due'])
        if datetime.utcnow() > rotation_due:
            logger.warning(f"API credentials for {exchange} are due for rotation")
            
        return {
            'api_key': credentials['api_key'],
            'secret_key': credentials['secret_key'],
            'passphrase': credentials['passphrase']
        }
    
    def rotate_credentials(self, exchange: str, new_credentials: Dict[str, str]):
        """Rotate API credentials with zero downtime"""
        # Store new credentials with incremented version
        secret_path = f"trading_bot/api_credentials/{exchange}"
        old_credentials = self.secure_manager.retrieve_secret(secret_path)
        
        new_secret_data = {
            **new_credentials,
            'created_at': datetime.utcnow().isoformat(),
            'rotation_due': (datetime.utcnow() + timedelta(days=90)).isoformat(),
            'version': old_credentials.get('version', 0) + 1,
            'previous_version': old_credentials
        }
        
        self.secure_manager.store_secret(secret_path, new_secret_data)
        logger.info(f"API credentials rotated for {exchange} to version {new_secret_data['version']}")

# Pydantic Models for Validation
if PYDANTIC_AVAILABLE:
    class BotSettings(BaseModel):
        """Validated bot settings configuration"""
        name: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_\-]+$')
        trading_mode: TradingMode
        features: Dict[str, bool]
        
        @validator('name')
        def validate_name(cls, v):
            if v.lower() in ['admin', 'root', 'system']:
                raise ValueError('Bot name cannot be reserved word')
            return v
        
        @validator('features')
        def validate_features(cls, v):
            required_features = ['auto_trading', 'risk_management']
            for feature in required_features:
                if feature not in v:
                    raise ValueError(f'Required feature missing: {feature}')
            return v

    class CapitalManagement(BaseModel):
        """Validated capital management configuration"""
        initial_balance: float = Field(..., gt=0, le=1_000_000_000)
        target_balance: float = Field(..., gt=0)
        max_risk_per_trade: float = Field(..., gt=0, le=10.0)
        max_daily_loss_pct: float = Field(..., gt=0, le=50.0)
        max_weekly_loss_pct: float = Field(..., gt=0, le=75.0)
        max_drawdown_pct: float = Field(..., gt=0, le=90.0)
        daily_profit_target: float = Field(..., gt=0, le=100.0)
        take_profit_at_target: bool
        
        @validator('target_balance')
        def validate_target_balance(cls, v, values):
            if 'initial_balance' in values and v <= values['initial_balance']:
                raise ValueError('Target balance must be greater than initial balance')
            return v
        
        @validator('max_weekly_loss_pct')
        def validate_weekly_loss(cls, v, values):
            if 'max_daily_loss_pct' in values and v <= values['max_daily_loss_pct']:
                raise ValueError('Weekly loss limit must be greater than daily loss limit')
            return v
        
        @validator('max_drawdown_pct')
        def validate_drawdown(cls, v, values):
            if 'max_weekly_loss_pct' in values and v <= values['max_weekly_loss_pct']:
                raise ValueError('Drawdown limit must be greater than weekly loss limit')
            return v

    class TradingSettings(BaseModel):
        """Validated trading configuration"""
        mode: Environment
        futures: bool
        min_confidence: float = Field(..., ge=0.5, le=0.95)
        max_trades_per_bar: int = Field(..., ge=1, le=10)
        commission_rate: float = Field(..., ge=0.0, le=0.01)
        circuit_breaker_loss: float = Field(..., gt=0, le=0.2)
        initial_balance: float = Field(..., gt=0)
        
        @validator('min_confidence')
        def validate_confidence_range(cls, v):
            if v < 0.5:
                raise ValueError('Minimum confidence cannot be less than 50%')
            if v > 0.95:
                raise ValueError('Minimum confidence cannot be greater than 95%')
            return v

    class RiskManagement(BaseModel):
        """Validated risk management configuration"""
        max_risk_per_trade: float = Field(..., gt=0, le=0.1)
        max_daily_loss_pct: float = Field(..., gt=0, le=0.5)
        max_drawdown_pct: float = Field(..., gt=0, le=0.9)
        max_leverage: float = Field(..., ge=1.0, le=10.0)
        default_stop_loss_pct: float = Field(..., gt=0, le=0.1)
        risk_reward_ratio: float = Field(..., ge=1.0, le=10.0)
        
        @validator('max_leverage')
        def validate_leverage(cls, v, values):
            # Higher leverage requires stricter risk limits
            if v > 5.0:
                max_risk = values.get('max_risk_per_trade', 0)
                if max_risk > 0.02:  # 2%
                    raise ValueError('High leverage requires max_risk_per_trade <= 2%')
            return v

class EnterpriseConfigValidator:
    """Enterprise-grade configuration validator"""
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        
    def validate_complete_config(self, config_dict: Dict[str, Any]) -> ValidationResult:
        """Validate entire configuration with cross-field validation"""
        errors = []
        warnings = []
        
        try:
            if PYDANTIC_AVAILABLE:
                # Validate individual sections
                bot_settings = BotSettings(**config_dict.get('bot_settings', {}))
                capital_mgmt = CapitalManagement(**config_dict.get('capital_management', {}))
                trading_settings = TradingSettings(**config_dict.get('trading', {}))
                risk_mgmt = RiskManagement(**config_dict.get('risk_management', {}))
                
                # Cross-field validation
                cross_validation_errors = self._cross_validate_config(
                    bot_settings, capital_mgmt, trading_settings, risk_mgmt
                )
                errors.extend(cross_validation_errors)
            else:
                # Fallback validation without Pydantic
                errors.extend(self._basic_validation(config_dict))
            
            # Business logic validation
            business_errors = self._validate_business_logic(config_dict)
            errors.extend(business_errors)
            
            # Environment-specific validation
            env_errors = self._validate_environment_constraints(config_dict)
            errors.extend(env_errors)
            
            # Security validation
            security_errors = self._validate_security_constraints(config_dict)
            errors.extend(security_errors)
            
        except ValidationError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_config=config_dict if len(errors) == 0 else None
        )
    
    def _basic_validation(self, config: Dict[str, Any]) -> List[str]:
        """Basic validation without Pydantic"""
        errors = []
        
        # Check required sections
        required_sections = ['bot_settings', 'capital_management', 'trading', 'risk_management']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Check bot settings
        if 'bot_settings' in config:
            bot_settings = config['bot_settings']
            if 'name' not in bot_settings:
                errors.append("Bot name is required")
            elif len(bot_settings['name']) < 3:
                errors.append("Bot name must be at least 3 characters")
        
        # Check capital management
        if 'capital_management' in config:
            cap_mgmt = config['capital_management']
            if 'initial_balance' in cap_mgmt and cap_mgmt['initial_balance'] <= 0:
                errors.append("Initial balance must be positive")
            if 'target_balance' in cap_mgmt and 'initial_balance' in cap_mgmt:
                if cap_mgmt['target_balance'] <= cap_mgmt['initial_balance']:
                    errors.append("Target balance must be greater than initial balance")
        
        return errors
    
    def _cross_validate_config(self, bot_settings, capital_mgmt, trading_settings, risk_mgmt) -> List[str]:
        """Cross-field validation between configuration sections"""
        errors = []
        
        # Risk consistency checks
        if capital_mgmt.max_risk_per_trade != risk_mgmt.max_risk_per_trade:
            errors.append("Risk per trade settings inconsistent between sections")
        
        # Trading mode consistency
        if bot_settings.trading_mode == TradingMode.CONSERVATIVE:
            if risk_mgmt.max_risk_per_trade > 0.02:
                errors.append("Conservative mode requires max_risk_per_trade <= 2%")
            if trading_settings.min_confidence < 0.75:
                errors.append("Conservative mode requires min_confidence >= 75%")
                
        elif bot_settings.trading_mode == TradingMode.AGGRESSIVE:
            if risk_mgmt.max_leverage < 2.0 and trading_settings.futures:
                errors.append("Aggressive mode with futures should use leverage >= 2x")
        
        # Environment consistency
        if trading_settings.mode == Environment.LIVE_TRADING:
            if not all([
                capital_mgmt.max_risk_per_trade <= 0.02,
                capital_mgmt.max_daily_loss_pct <= 0.05,
                trading_settings.min_confidence >= 0.7
            ]):
                errors.append("Live trading requires conservative risk settings")
        
        return errors
    
    def _validate_business_logic(self, config: Dict[str, Any]) -> List[str]:
        """Validate business logic constraints"""
        errors = []
        
        # Capital allocation must sum to 100%
        multi_symbol = config.get('multi_symbol_settings', {})
        if multi_symbol.get('enabled', False):
            symbols = multi_symbol.get('symbols', {})
            total_allocation = sum(
                symbol_config.get('allocation_pct', 0) 
                for symbol_config in symbols.values()
                if symbol_config.get('enabled', False)
            )
            if abs(total_allocation - 100.0) > 0.01:
                errors.append(f"Symbol allocations must sum to 100%, got {total_allocation}%")
        
        # Take profit levels must be ascending
        trading_settings = config.get('trading_settings', {})
        take_profit = trading_settings.get('take_profit', {})
        if take_profit.get('method') == 'scaled':
            levels = take_profit.get('levels', [])
            for i in range(1, len(levels)):
                if levels[i]['target'] <= levels[i-1]['target']:
                    errors.append("Take profit levels must be in ascending order")
        
        return errors
    
    def _validate_environment_constraints(self, config: Dict[str, Any]) -> List[str]:
        """Validate environment-specific constraints"""
        errors = []
        
        trading_mode = config.get('trading', {}).get('mode')
        
        if trading_mode == Environment.LIVE_TRADING:
            # Live trading requires additional validations
            required_features = ['risk_management', 'stop_on_drawdown']
            features = config.get('bot_settings', {}).get('features', {})
            
            for feature in required_features:
                if not features.get(feature, False):
                    errors.append(f"Live trading requires {feature} to be enabled")
        
        return errors
    
    def _validate_security_constraints(self, config: Dict[str, Any]) -> List[str]:
        """Validate security-related constraints"""
        errors = []
        
        # Check for sensitive data in plain text
        sensitive_patterns = [
            r'[A-Za-z0-9]{20,}',  # Potential API keys
            r'sk_[a-zA-Z0-9]{32,}',  # Secret key patterns
            r'password.*[A-Za-z0-9]+'  # Password fields
        ]
        
        def check_for_sensitive_data(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, str):
                        for pattern in sensitive_patterns:
                            if re.search(pattern, value):
                                errors.append(f"Potential sensitive data in plain text: {current_path}")
                    else:
                        check_for_sensitive_data(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_for_sensitive_data(item, f"{path}[{i}]")
        
        check_for_sensitive_data(config)
        
        return errors

class ThreadSafeConfigManager:
    """Thread-safe configuration manager with atomic updates"""
    
    def __init__(self):
        self._config = {}
        self._config_lock = threading.RLock()
        self._observers = []
        self._version = 0
        self._update_in_progress = False
        
    @contextmanager
    def read_config(self):
        """Context manager for read-only access to configuration"""
        with self._config_lock:
            # Return a deep copy to prevent external modifications
            yield copy.deepcopy(self._config)
    
    @contextmanager
    def write_config(self):
        """Context manager for write access to configuration"""
        with self._config_lock:
            if self._update_in_progress:
                raise ConfigurationError("Configuration update already in progress")
            
            self._update_in_progress = True
            try:
                # Provide reference to current config for modification
                yield self._config
                self._version += 1
                self._notify_observers()
            finally:
                self._update_in_progress = False
    
    def atomic_update(self, update_func: Callable[[Dict], Dict]) -> bool:
        """Atomically update configuration"""
        with self._config_lock:
            try:
                # Create a copy for the update function
                config_copy = copy.deepcopy(self._config)
                new_config = update_func(config_copy)
                
                # Validate new configuration
                validator = EnterpriseConfigValidator()
                validation_result = validator.validate_complete_config(new_config)
                
                if not validation_result.is_valid:
                    logger.error(f"Configuration validation failed: {validation_result.errors}")
                    return False
                
                # Apply the new configuration atomically
                self._config = new_config
                self._version += 1
                self._notify_observers()
                
                logger.info(f"Configuration updated successfully to version {self._version}")
                return True
                
            except Exception as e:
                logger.error(f"Atomic configuration update failed: {e}")
                return False
    
    def get_config_version(self) -> int:
        """Get current configuration version"""
        with self._config_lock:
            return self._version
    
    def register_observer(self, callback: Callable[[Dict, int], None]):
        """Register observer for configuration changes"""
        with self._config_lock:
            self._observers.append(callback)
    
    def _notify_observers(self):
        """Notify all observers of configuration changes"""
        config_copy = copy.deepcopy(self._config)
        for observer in self._observers:
            try:
                observer(config_copy, self._version)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

class ConfigurationVersionManager:
    """Manages configuration versions with rollback capability"""
    
    def __init__(self, max_versions: int = 10):
        self.max_versions = max_versions
        self.versions = {}
        self.current_version = 0
        
    def save_version(self, config: Dict[str, Any], version: int):
        """Save a configuration version"""
        self.versions[version] = {
            'config': copy.deepcopy(config),
            'timestamp': datetime.utcnow(),
            'checksum': self._calculate_checksum(config)
        }
        
        # Clean up old versions
        if len(self.versions) > self.max_versions:
            oldest_version = min(self.versions.keys())
            del self.versions[oldest_version]
    
    def get_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific configuration version"""
        if version in self.versions:
            return copy.deepcopy(self.versions[version]['config'])
        return None
    
    def rollback_to_version(self, version: int) -> bool:
        """Rollback to a previous configuration version"""
        if version not in self.versions:
            logger.error(f"Version {version} not found for rollback")
            return False
        
        # Verify integrity
        stored_config = self.versions[version]['config']
        stored_checksum = self.versions[version]['checksum']
        current_checksum = self._calculate_checksum(stored_config)
        
        if stored_checksum != current_checksum:
            logger.error(f"Integrity check failed for version {version}")
            return False
        
        return True
    
    def _calculate_checksum(self, config: Dict[str, Any]) -> str:
        """Calculate configuration checksum for integrity verification"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

class ConfigurationAuditor:
    """Enterprise audit system for configuration changes"""
    
    def __init__(self):
        if STRUCTLOG_AVAILABLE:
            # Configure structured logging
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            self.logger = structlog.get_logger("config_audit")
        else:
            # Fallback to standard logging
            self.logger = logging.getLogger("config_audit")
        
    def log_event(self, event: AuditEvent):
        """Log audit event with structured data"""
        log_data = {
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "risk_level": event.risk_level,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "source_ip": event.source_ip,
            "details": event.details or {}
        }
        
        if event.risk_level in ["HIGH", "CRITICAL"]:
            self.logger.error("High-risk configuration event", **log_data)
        elif event.risk_level == "MEDIUM":
            self.logger.warning("Medium-risk configuration event", **log_data)
        else:
            self.logger.info("Configuration event", **log_data)
    
    def log_config_change(self, old_config: Dict, new_config: Dict, user_id: str = None):
        """Log configuration changes with diff"""
        changes = self._calculate_config_diff(old_config, new_config)
        
        risk_level = "LOW"
        if any("api_" in change.lower() or "secret" in change.lower() for change in changes):
            risk_level = "HIGH"
        elif any("risk" in change.lower() or "loss" in change.lower() for change in changes):
            risk_level = "MEDIUM"
        
        event = AuditEvent(
            event_type=AuditEventType.CONFIG_UPDATED,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            details={
                "changes": changes,
                "change_count": len(changes)
            },
            risk_level=risk_level
        )
        
        self.log_event(event)
    
    def _calculate_config_diff(self, old_config: Dict, new_config: Dict) -> List[str]:
        """Calculate differences between configurations"""
        changes = []
        
        def compare_recursive(old, new, path=""):
            if isinstance(old, dict) and isinstance(new, dict):
                for key in set(old.keys()) | set(new.keys()):
                    current_path = f"{path}.{key}" if path else key
                    
                    if key not in old:
                        changes.append(f"Added: {current_path} = {new[key]}")
                    elif key not in new:
                        changes.append(f"Removed: {current_path}")
                    elif old[key] != new[key]:
                        if isinstance(old[key], (dict, list)):
                            compare_recursive(old[key], new[key], current_path)
                        else:
                            # Mask sensitive values
                            old_val = "***" if "secret" in key.lower() or "key" in key.lower() else old[key]
                            new_val = "***" if "secret" in key.lower() or "key" in key.lower() else new[key]
                            changes.append(f"Changed: {current_path} from {old_val} to {new_val}")
            
            elif isinstance(old, list) and isinstance(new, list):
                if old != new:
                    changes.append(f"List changed: {path}")
        
        compare_recursive(old_config, new_config)
        return changes

# Global instances
secure_config_manager = SecureConfigManager()
api_credentials_manager = APICredentialsManager(secure_config_manager)
thread_safe_config_manager = ThreadSafeConfigManager()
config_validator = EnterpriseConfigValidator()
config_auditor = ConfigurationAuditor()
version_manager = ConfigurationVersionManager()

# Convenience functions
def load_enterprise_config(config_path: str) -> Dict[str, Any]:
    """Load and validate enterprise configuration"""
    try:
        with open(config_path, 'r') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        
        # Validate configuration
        result = config_validator.validate_complete_config(config)
        
        if result.is_valid:
            # Store in thread-safe manager
            with thread_safe_config_manager.write_config() as cfg:
                cfg.update(config)
            
            # Log successful load
            event = AuditEvent(
                event_type=AuditEventType.CONFIG_LOADED,
                timestamp=datetime.utcnow(),
                details={"config_path": config_path}
            )
            config_auditor.log_event(event)
            
            return config
        else:
            logger.error(f"Configuration validation failed: {result.errors}")
            return {}
            
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def get_secure_config() -> Dict[str, Any]:
    """Get current configuration thread-safely"""
    with thread_safe_config_manager.read_config() as config:
        return config

def update_config_safely(update_func: Callable[[Dict], Dict]) -> bool:
    """Update configuration safely with validation"""
    return thread_safe_config_manager.atomic_update(update_func)

def get_api_credentials(exchange: str) -> Dict[str, str]:
    """Get API credentials securely"""
    return api_credentials_manager.get_api_credentials(exchange)

def store_api_credentials(exchange: str, credentials: Dict[str, str]):
    """Store API credentials securely"""
    api_credentials_manager.store_api_credentials(exchange, credentials)
