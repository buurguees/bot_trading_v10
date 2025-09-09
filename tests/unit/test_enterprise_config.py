"""
tests/test_enterprise_config.py - Enterprise Configuration Testing Suite
Suite de testing completa para el sistema de configuración enterprise
"""

import pytest
import json
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.enterprise_config import (
    SecureConfigManager,
    APICredentialsManager,
    EnterpriseConfigValidator,
    ThreadSafeConfigManager,
    ConfigurationVersionManager,
    ConfigurationAuditor,
    ValidationResult,
    TradingMode,
    Environment,
    AuditEventType,
    SecurityError,
    ConfigurationError,
    ValidationError
)

# Test data
SAMPLE_CONFIG = {
    'bot_settings': {
        'name': 'test_bot',
        'trading_mode': 'moderate',
        'features': {
            'auto_trading': True,
            'risk_management': True,
            'stop_on_drawdown': True
        }
    },
    'capital_management': {
        'initial_balance': 1000.0,
        'target_balance': 10000.0,
        'max_risk_per_trade': 2.0,
        'max_daily_loss_pct': 5.0,
        'max_weekly_loss_pct': 15.0,
        'max_drawdown_pct': 20.0,
        'daily_profit_target': 3.0,
        'take_profit_at_target': False
    },
    'trading': {
        'mode': 'paper_trading',
        'futures': False,
        'min_confidence': 0.7,
        'max_trades_per_bar': 1,
        'commission_rate': 0.001,
        'circuit_breaker_loss': 0.05,
        'initial_balance': 1000.0
    },
    'risk_management': {
        'max_risk_per_trade': 2.0,
        'max_daily_loss_pct': 5.0,
        'max_drawdown_pct': 20.0,
        'max_leverage': 2.0,
        'default_stop_loss_pct': 2.0,
        'risk_reward_ratio': 2.0
    }
}

INVALID_CONFIG = {
    'bot_settings': {
        'name': 'admin',  # Reserved word
        'trading_mode': 'invalid_mode',
        'features': {
            'auto_trading': True
            # Missing required features
        }
    },
    'capital_management': {
        'initial_balance': -1000.0,  # Negative balance
        'target_balance': 500.0,  # Less than initial
        'max_risk_per_trade': 50.0,  # Too high
        'max_daily_loss_pct': 200.0,  # Too high
        'max_weekly_loss_pct': 5.0,  # Less than daily
        'max_drawdown_pct': 10.0,  # Less than weekly
        'daily_profit_target': 500.0,  # Too high
        'take_profit_at_target': False
    }
}

class TestSecureConfigManager:
    """Test secure configuration manager"""
    
    def test_encryption_roundtrip(self):
        """Test encryption and decryption of configuration data"""
        secure_manager = SecureConfigManager()
        
        original_data = {
            'api_key': 'test_key_123',
            'secret': 'super_secret_data',
            'nested': {'password': 'nested_password'}
        }
        
        # Encrypt and decrypt
        encrypted = secure_manager.encrypt_config(original_data)
        decrypted = secure_manager.decrypt_config(encrypted)
        
        assert decrypted == original_data
        assert encrypted != original_data  # Ensure it's actually encrypted
    
    def test_secret_storage_and_retrieval(self):
        """Test secret storage and retrieval"""
        secure_manager = SecureConfigManager()
        
        secret_data = {
            'api_key': 'test_api_key',
            'secret_key': 'test_secret_key',
            'passphrase': 'test_passphrase'
        }
        
        # Store secret
        secure_manager.store_secret('test/path', secret_data)
        
        # Retrieve secret
        retrieved = secure_manager.retrieve_secret('test/path')
        
        assert retrieved == secret_data
    
    def test_secret_not_found(self):
        """Test error handling when secret not found"""
        secure_manager = SecureConfigManager()
        
        with pytest.raises(SecurityError):
            secure_manager.retrieve_secret('nonexistent/path')
    
    def test_encryption_key_management(self):
        """Test encryption key management"""
        secure_manager = SecureConfigManager()
        
        # Should have a valid encryption key
        assert secure_manager.encryption_key is not None
        assert len(secure_manager.encryption_key) > 0

class TestAPICredentialsManager:
    """Test API credentials management"""
    
    def test_store_and_retrieve_credentials(self):
        """Test storing and retrieving API credentials"""
        secure_manager = SecureConfigManager()
        credentials_manager = APICredentialsManager(secure_manager)
        
        credentials = {
            'api_key': 'test_api_key',
            'secret_key': 'test_secret_key',
            'passphrase': 'test_passphrase'
        }
        
        # Store credentials
        credentials_manager.store_api_credentials('test_exchange', credentials)
        
        # Retrieve credentials
        retrieved = credentials_manager.get_api_credentials('test_exchange')
        
        assert retrieved['api_key'] == credentials['api_key']
        assert retrieved['secret_key'] == credentials['secret_key']
        assert retrieved['passphrase'] == credentials['passphrase']
    
    def test_credentials_validation(self):
        """Test credentials validation"""
        secure_manager = SecureConfigManager()
        credentials_manager = APICredentialsManager(secure_manager)
        
        # Test missing required fields
        incomplete_credentials = {
            'api_key': 'test_key',
            'secret_key': 'test_secret'
            # Missing passphrase
        }
        
        with pytest.raises(ValidationError):
            credentials_manager.store_api_credentials('test_exchange', incomplete_credentials)
    
    def test_credentials_rotation(self):
        """Test API credential rotation"""
        secure_manager = SecureConfigManager()
        credentials_manager = APICredentialsManager(secure_manager)
        
        # Store initial credentials
        initial_creds = {
            'api_key': 'initial_key',
            'secret_key': 'initial_secret',
            'passphrase': 'initial_passphrase'
        }
        credentials_manager.store_api_credentials('test_exchange', initial_creds)
        
        # Rotate credentials
        new_creds = {
            'api_key': 'new_key',
            'secret_key': 'new_secret',
            'passphrase': 'new_passphrase'
        }
        credentials_manager.rotate_credentials('test_exchange', new_creds)
        
        # Verify new credentials are active
        current_creds = credentials_manager.get_api_credentials('test_exchange')
        assert current_creds['api_key'] == new_creds['api_key']

class TestEnterpriseConfigValidator:
    """Test enterprise configuration validator"""
    
    def test_valid_configuration(self):
        """Test validation with valid configuration"""
        validator = EnterpriseConfigValidator()
        result = validator.validate_complete_config(SAMPLE_CONFIG)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.validated_config is not None
    
    def test_invalid_configuration(self):
        """Test validation with invalid configuration"""
        validator = EnterpriseConfigValidator()
        result = validator.validate_complete_config(INVALID_CONFIG)
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_cross_field_validation(self):
        """Test cross-field validation"""
        validator = EnterpriseConfigValidator()
        
        # Test conservative mode validation
        conservative_config = SAMPLE_CONFIG.copy()
        conservative_config['bot_settings']['trading_mode'] = 'conservative'
        conservative_config['risk_management']['max_risk_per_trade'] = 5.0  # Too high for conservative
        
        result = validator.validate_complete_config(conservative_config)
        assert not result.is_valid
        assert any('conservative mode requires' in error.lower() for error in result.errors)
    
    def test_environment_validation(self):
        """Test environment-specific validation"""
        validator = EnterpriseConfigValidator()
        
        # Test live trading validation
        live_config = SAMPLE_CONFIG.copy()
        live_config['trading']['mode'] = 'live_trading'
        live_config['bot_settings']['features']['risk_management'] = False  # Should fail for live trading
        
        result = validator.validate_complete_config(live_config)
        assert not result.is_valid
        assert any('live trading requires risk_management' in error.lower() for error in result.errors)
    
    def test_security_validation(self):
        """Test security validation"""
        validator = EnterpriseConfigValidator()
        
        # Test sensitive data detection
        config_with_secrets = {
            'api_settings': {
                'api_key': 'pk_test_demo_key_123456789012345678901234567890',
                'password': 'demo_password_123'
            }
        }
        
        result = validator.validate_complete_config(config_with_secrets)
        assert not result.is_valid
        assert any('sensitive data' in error.lower() for error in result.errors)
    
    def test_business_logic_validation(self):
        """Test business logic validation"""
        validator = EnterpriseConfigValidator()
        
        # Test symbol allocation validation
        config_with_allocation = SAMPLE_CONFIG.copy()
        config_with_allocation['multi_symbol_settings'] = {
            'enabled': True,
            'symbols': {
                'BTCUSDT': {'enabled': True, 'allocation_pct': 60.0},
                'ETHUSDT': {'enabled': True, 'allocation_pct': 30.0}
                # Total: 90%, should fail
            }
        }
        
        result = validator.validate_complete_config(config_with_allocation)
        assert not result.is_valid
        assert any('must sum to 100%' in error for error in result.errors)

class TestThreadSafeConfigManager:
    """Test thread-safe configuration manager"""
    
    def test_read_write_access(self):
        """Test read and write access to configuration"""
        config_manager = ThreadSafeConfigManager()
        
        # Test write access
        with config_manager.write_config() as config:
            config['test_key'] = 'test_value'
            config['nested'] = {'key': 'value'}
        
        # Test read access
        with config_manager.read_config() as config:
            assert config['test_key'] == 'test_value'
            assert config['nested']['key'] == 'value'
    
    def test_atomic_update(self):
        """Test atomic configuration updates"""
        config_manager = ThreadSafeConfigManager()
        
        def update_func(config):
            config['version'] = 1
            config['updated_at'] = datetime.utcnow().isoformat()
            return config
        
        # Test successful update
        result = config_manager.atomic_update(update_func)
        assert result
        
        # Verify update
        with config_manager.read_config() as config:
            assert 'version' in config
            assert 'updated_at' in config
    
    def test_atomic_update_validation_failure(self):
        """Test atomic update with validation failure"""
        config_manager = ThreadSafeConfigManager()
        
        def invalid_update_func(config):
            config['bot_settings'] = {'name': 'admin'}  # Invalid name
            return config
        
        # Test failed update
        result = config_manager.atomic_update(invalid_update_func)
        assert not result
    
    def test_concurrent_access(self):
        """Test concurrent access to configuration"""
        config_manager = ThreadSafeConfigManager()
        errors = []
        
        def reader_thread():
            try:
                for _ in range(100):
                    with config_manager.read_config() as config:
                        _ = config.get('test_key', 'default')
                        time.sleep(0.001)
            except Exception as e:
                errors.append(f"Reader error: {e}")
        
        def writer_thread():
            try:
                for i in range(50):
                    def update_func(config):
                        config[f'thread_{i}'] = f'value_{i}'
                        return config
                    
                    config_manager.atomic_update(update_func)
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"Writer error: {e}")
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=reader_thread))
        for _ in range(2):
            threads.append(threading.Thread(target=writer_thread))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"
    
    def test_observer_notifications(self):
        """Test observer notifications for configuration changes"""
        config_manager = ThreadSafeConfigManager()
        notifications = []
        
        def observer_callback(config, version):
            notifications.append((version, config.get('test_key')))
        
        # Register observer
        config_manager.register_observer(observer_callback)
        
        # Make configuration change
        def update_func(config):
            config['test_key'] = 'test_value'
            return config
        
        config_manager.atomic_update(update_func)
        
        # Verify notification
        assert len(notifications) == 1
        assert notifications[0][1] == 'test_value'

class TestConfigurationVersionManager:
    """Test configuration version manager"""
    
    def test_version_save_and_retrieve(self):
        """Test saving and retrieving configuration versions"""
        version_manager = ConfigurationVersionManager()
        
        # Save initial version
        initial_config = {'version': 1, 'setting': 'value1'}
        version_manager.save_version(initial_config, 1)
        
        # Retrieve version
        retrieved = version_manager.get_version(1)
        assert retrieved == initial_config
    
    def test_version_rollback(self):
        """Test configuration rollback"""
        version_manager = ConfigurationVersionManager()
        
        # Save multiple versions
        version_manager.save_version({'version': 1, 'setting': 'value1'}, 1)
        version_manager.save_version({'version': 2, 'setting': 'value2'}, 2)
        version_manager.save_version({'version': 3, 'setting': 'value3'}, 3)
        
        # Test rollback to version 1
        assert version_manager.rollback_to_version(1)
        
        # Test rollback to non-existent version
        assert not version_manager.rollback_to_version(999)
    
    def test_version_cleanup(self):
        """Test automatic cleanup of old versions"""
        version_manager = ConfigurationVersionManager(max_versions=3)
        
        # Save more versions than max allowed
        for i in range(5):
            version_manager.save_version({'version': i, 'setting': f'value{i}'}, i)
        
        # Should only keep the last 3 versions
        assert len(version_manager.versions) == 3
        assert 0 not in version_manager.versions  # Oldest should be removed
        assert 4 in version_manager.versions  # Newest should be kept
    
    def test_checksum_validation(self):
        """Test checksum validation for integrity"""
        version_manager = ConfigurationVersionManager()
        
        # Save version
        config = {'version': 1, 'setting': 'value1'}
        version_manager.save_version(config, 1)
        
        # Tamper with stored config
        version_manager.versions[1]['config']['setting'] = 'tampered'
        
        # Rollback should fail due to checksum mismatch
        assert not version_manager.rollback_to_version(1)

class TestConfigurationAuditor:
    """Test configuration auditor"""
    
    def test_audit_event_logging(self):
        """Test audit event logging"""
        auditor = ConfigurationAuditor()
        
        # Create test audit event
        event = AuditEvent(
            event_type=AuditEventType.CONFIG_UPDATED,
            timestamp=datetime.utcnow(),
            user_id='test_user',
            details={'change': 'test_change'},
            risk_level='HIGH'
        )
        
        # Should not raise exception
        auditor.log_event(event)
    
    def test_config_change_logging(self):
        """Test configuration change logging"""
        auditor = ConfigurationAuditor()
        
        old_config = {'setting': 'old_value'}
        new_config = {'setting': 'new_value', 'new_setting': 'added'}
        
        auditor.log_config_change(old_config, new_config, 'test_user')
    
    def test_config_diff_calculation(self):
        """Test configuration diff calculation"""
        auditor = ConfigurationAuditor()
        
        old_config = {
            'setting1': 'value1',
            'setting2': 'value2',
            'nested': {'key': 'value'}
        }
        new_config = {
            'setting1': 'new_value1',  # Changed
            'setting2': 'value2',      # Unchanged
            'nested': {'key': 'new_value'},  # Nested changed
            'new_setting': 'added'     # Added
        }
        
        changes = auditor._calculate_config_diff(old_config, new_config)
        
        assert len(changes) == 3  # 3 changes
        assert any('Changed: setting1' in change for change in changes)
        assert any('Changed: nested.key' in change for change in changes)
        assert any('Added: new_setting' in change for change in changes)
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data in diffs"""
        auditor = ConfigurationAuditor()
        
        old_config = {'api_key': 'old_key_123'}
        new_config = {'api_key': 'new_key_456'}
        
        changes = auditor._calculate_config_diff(old_config, new_config)
        
        # Sensitive data should be masked
        assert any('***' in change for change in changes)
        assert not any('old_key_123' in change for change in changes)
        assert not any('new_key_456' in change for change in changes)

class TestIntegration:
    """Integration tests for the complete system"""
    
    def test_complete_workflow(self):
        """Test complete configuration workflow"""
        # Initialize components
        secure_manager = SecureConfigManager()
        credentials_manager = APICredentialsManager(secure_manager)
        config_manager = ThreadSafeConfigManager()
        validator = EnterpriseConfigValidator()
        auditor = ConfigurationAuditor()
        
        # Store API credentials
        credentials = {
            'api_key': 'test_api_key',
            'secret_key': 'test_secret_key',
            'passphrase': 'test_passphrase'
        }
        credentials_manager.store_api_credentials('bitget', credentials)
        
        # Load and validate configuration
        result = validator.validate_complete_config(SAMPLE_CONFIG)
        assert result.is_valid
        
        # Update configuration atomically
        def update_func(config):
            config['updated_at'] = datetime.utcnow().isoformat()
            return config
        
        success = config_manager.atomic_update(update_func)
        assert success
        
        # Verify configuration
        with config_manager.read_config() as config:
            assert 'updated_at' in config
    
    def test_error_handling(self):
        """Test error handling across components"""
        secure_manager = SecureConfigManager()
        credentials_manager = APICredentialsManager(secure_manager)
        
        # Test invalid credentials
        with pytest.raises(ValidationError):
            credentials_manager.store_api_credentials('test', {'invalid': 'data'})
        
        # Test secret not found
        with pytest.raises(SecurityError):
            secure_manager.retrieve_secret('nonexistent')
    
    def test_performance_under_load(self):
        """Test performance under load"""
        config_manager = ThreadSafeConfigManager()
        validator = EnterpriseConfigValidator()
        
        # Create large configuration
        large_config = {}
        for i in range(100):
            large_config[f'section_{i}'] = {
                f'setting_{j}': f'value_{i}_{j}'
                for j in range(50)
            }
        
        # Test validation performance
        start_time = time.time()
        result = validator.validate_complete_config(large_config)
        validation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert validation_time < 5.0
        assert result.is_valid
    
    def test_concurrent_updates(self):
        """Test concurrent configuration updates"""
        config_manager = ThreadSafeConfigManager()
        update_count = 0
        
        def update_thread(thread_id):
            nonlocal update_count
            
            def update_func(config):
                config[f'thread_{thread_id}'] = f'value_{thread_id}'
                return config
            
            if config_manager.atomic_update(update_func):
                update_count += 1
        
        # Start multiple update threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_thread, args=(i,))
            threads.append(thread)
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # All updates should succeed
        assert update_count == 10
        # Should complete within reasonable time
        assert total_time < 10.0

# Performance benchmarks
class TestPerformance:
    """Performance tests for configuration system"""
    
    def test_configuration_load_performance(self):
        """Test configuration loading performance"""
        validator = EnterpriseConfigValidator()
        
        # Create large configuration
        large_config = {}
        for i in range(1000):
            large_config[f'section_{i}'] = {
                f'setting_{j}': f'value_{i}_{j}'
                for j in range(100)
            }
        
        start_time = time.time()
        result = validator.validate_complete_config(large_config)
        end_time = time.time()
        
        validation_time = end_time - start_time
        assert validation_time < 5.0  # Should complete within 5 seconds
        assert result.is_valid
    
    def test_encryption_performance(self):
        """Test encryption/decryption performance"""
        secure_manager = SecureConfigManager()
        
        # Create large configuration
        large_config = {}
        for i in range(100):
            large_config[f'section_{i}'] = {
                f'setting_{j}': f'value_{i}_{j}'
                for j in range(100)
            }
        
        # Test encryption performance
        start_time = time.time()
        encrypted = secure_manager.encrypt_config(large_config)
        encryption_time = time.time() - start_time
        
        # Test decryption performance
        start_time = time.time()
        decrypted = secure_manager.decrypt_config(encrypted)
        decryption_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert encryption_time < 2.0
        assert decryption_time < 2.0
        assert decrypted == large_config

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
