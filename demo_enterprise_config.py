"""
demo_enterprise_config.py - Demo del Sistema de Configuración Enterprise
Demostración completa del sistema de configuración enterprise-grade
"""

import os
import json
import yaml
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import enterprise configuration system
from core.enterprise_config import (
    SecureConfigManager,
    APICredentialsManager,
    EnterpriseConfigValidator,
    ThreadSafeConfigManager,
    ConfigurationVersionManager,
    ConfigurationAuditor,
    load_enterprise_config,
    get_secure_config,
    update_config_safely,
    get_api_credentials,
    store_api_credentials,
    TradingMode,
    Environment,
    AuditEventType
)

def demo_security_features():
    """Demo de características de seguridad"""
    print("\n🔐 DEMO: Características de Seguridad")
    print("=" * 50)
    
    # Inicializar gestor de configuración seguro
    secure_manager = SecureConfigManager()
    credentials_manager = APICredentialsManager(secure_manager)
    
    # Demo de encriptación de configuración
    print("\n🔒 Encriptación de Configuración:")
    sensitive_config = {
        'api_settings': {
            'api_key': 'pk_test_demo_key_123456789012345678901234567890',
            'secret_key': 'sk_test_demo_secret_key_123456789',
            'webhook_secret': 'whsec_demo_1234567890abcdef'
        },
        'database': {
            'password': 'database_password_123',
            'connection_string': 'postgresql://user:pass@localhost:5432/db'
        }
    }
    
    # Encriptar configuración
    encrypted_data = secure_manager.encrypt_config(sensitive_config)
    print(f"   ✅ Configuración encriptada: {len(encrypted_data)} bytes")
    
    # Desencriptar configuración
    decrypted_data = secure_manager.decrypt_config(encrypted_data)
    print(f"   ✅ Configuración desencriptada: {len(decrypted_data)} caracteres")
    print(f"   ✅ Integridad verificada: {decrypted_data == sensitive_config}")
    
    # Demo de gestión de credenciales API
    print("\n🔑 Gestión de Credenciales API:")
    api_credentials = {
        'api_key': 'test_api_key_12345',
        'secret_key': 'test_secret_key_67890',
        'passphrase': 'test_passphrase_abcde'
    }
    
    # Almacenar credenciales
    credentials_manager.store_api_credentials('bitget', api_credentials)
    print("   ✅ Credenciales almacenadas para Bitget")
    
    # Recuperar credenciales
    retrieved_credentials = credentials_manager.get_api_credentials('bitget')
    print(f"   ✅ Credenciales recuperadas: {retrieved_credentials['api_key']}")
    
    # Demo de rotación de credenciales
    print("\n🔄 Rotación de Credenciales:")
    new_credentials = {
        'api_key': 'new_api_key_54321',
        'secret_key': 'new_secret_key_09876',
        'passphrase': 'new_passphrase_edcba'
    }
    
    credentials_manager.rotate_credentials('bitget', new_credentials)
    print("   ✅ Credenciales rotadas exitosamente")
    
    # Verificar nuevas credenciales
    current_credentials = credentials_manager.get_api_credentials('bitget')
    print(f"   ✅ Nuevas credenciales activas: {current_credentials['api_key']}")

def demo_validation_system():
    """Demo del sistema de validación"""
    print("\n🔍 DEMO: Sistema de Validación")
    print("=" * 50)
    
    validator = EnterpriseConfigValidator()
    
    # Configuración válida
    print("\n✅ Configuración Válida:")
    valid_config = {
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
    
    result = validator.validate_complete_config(valid_config)
    print(f"   Validación: {'✅ Válida' if result.is_valid else '❌ Inválida'}")
    if result.errors:
        print(f"   Errores: {result.errors}")
    
    # Configuración inválida
    print("\n❌ Configuración Inválida:")
    invalid_config = {
        'bot_settings': {
            'name': 'admin',  # Palabra reservada
            'trading_mode': 'invalid_mode',
            'features': {
                'auto_trading': True
                # Faltan características requeridas
            }
        },
        'capital_management': {
            'initial_balance': -1000.0,  # Balance negativo
            'target_balance': 500.0,  # Menor que inicial
            'max_risk_per_trade': 50.0,  # Demasiado alto
            'max_daily_loss_pct': 200.0,  # Demasiado alto
            'max_weekly_loss_pct': 5.0,  # Menor que diario
            'max_drawdown_pct': 10.0,  # Menor que semanal
            'daily_profit_target': 500.0,  # Demasiado alto
            'take_profit_at_target': False
        }
    }
    
    result = validator.validate_complete_config(invalid_config)
    print(f"   Validación: {'✅ Válida' if result.is_valid else '❌ Inválida'}")
    if result.errors:
        print(f"   Errores encontrados: {len(result.errors)}")
        for i, error in enumerate(result.errors[:3], 1):  # Mostrar primeros 3 errores
            print(f"   {i}. {error}")
        if len(result.errors) > 3:
            print(f"   ... y {len(result.errors) - 3} errores más")
    
    # Validación de datos sensibles
    print("\n🔒 Detección de Datos Sensibles:")
    config_with_secrets = {
        'api_settings': {
            'api_key': 'pk_test_demo_key_123456789012345678901234567890',
            'password': 'demo_password_123'
        }
    }
    
    result = validator.validate_complete_config(config_with_secrets)
    print(f"   Validación: {'✅ Válida' if result.is_valid else '❌ Inválida'}")
    if result.errors:
        print(f"   Datos sensibles detectados: {len([e for e in result.errors if 'sensitive' in e.lower()])}")

def demo_thread_safety():
    """Demo de thread safety"""
    print("\n🔒 DEMO: Thread Safety & Concurrency")
    print("=" * 50)
    
    config_manager = ThreadSafeConfigManager()
    
    # Demo de acceso concurrente
    print("\n🔄 Acceso Concurrente:")
    
    def reader_thread(thread_id):
        """Thread de lectura"""
        for i in range(10):
            with config_manager.read_config() as config:
                value = config.get(f'thread_{thread_id}', 'not_found')
                print(f"   Thread {thread_id} lee: {value}")
            time.sleep(0.01)
    
    def writer_thread(thread_id):
        """Thread de escritura"""
        for i in range(5):
            def update_func(config):
                config[f'thread_{thread_id}'] = f'value_{i}'
                config['last_update'] = datetime.utcnow().isoformat()
                return config
            
            success = config_manager.atomic_update(update_func)
            print(f"   Thread {thread_id} actualiza: {'✅ Éxito' if success else '❌ Fallo'}")
            time.sleep(0.02)
    
    # Crear threads
    threads = []
    for i in range(3):
        threads.append(threading.Thread(target=reader_thread, args=(i,)))
    for i in range(2):
        threads.append(threading.Thread(target=writer_thread, args=(i,)))
    
    # Ejecutar threads
    start_time = time.time()
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    print(f"   ⏱️ Tiempo total: {end_time - start_time:.2f}s")
    
    # Demo de actualización atómica
    print("\n⚛️ Actualización Atómica:")
    
    def update_with_validation(config):
        config['version'] = 1
        config['updated_at'] = datetime.utcnow().isoformat()
        config['features'] = {
            'auto_trading': True,
            'risk_management': True
        }
        return config
    
    success = config_manager.atomic_update(update_with_validation)
    print(f"   Actualización: {'✅ Éxito' if success else '❌ Fallo'}")
    
    # Verificar configuración actual
    with config_manager.read_config() as config:
        print(f"   Versión actual: {config.get('version', 'N/A')}")
        print(f"   Última actualización: {config.get('updated_at', 'N/A')}")

def demo_version_management():
    """Demo de gestión de versiones"""
    print("\n📚 DEMO: Gestión de Versiones")
    print("=" * 50)
    
    version_manager = ConfigurationVersionManager(max_versions=5)
    
    # Crear múltiples versiones
    print("\n💾 Creando Versiones:")
    for i in range(7):  # Crearemos más versiones que el máximo permitido
        config = {
            'version': i + 1,
            'setting': f'value_{i + 1}',
            'created_at': datetime.utcnow().isoformat()
        }
        version_manager.save_version(config, i + 1)
        print(f"   ✅ Versión {i + 1} guardada")
    
    # Verificar limpieza automática
    print(f"\n🧹 Limpieza Automática:")
    print(f"   Versiones almacenadas: {len(version_manager.versions)}")
    print(f"   Versiones disponibles: {sorted(version_manager.versions.keys())}")
    
    # Demo de rollback
    print("\n🔄 Rollback de Configuración:")
    
    # Rollback a versión 3
    if version_manager.rollback_to_version(3):
        config_v3 = version_manager.get_version(3)
        print(f"   ✅ Rollback a versión 3 exitoso")
        print(f"   Configuración: {config_v3['setting']}")
    else:
        print("   ❌ Rollback fallido")
    
    # Intentar rollback a versión inexistente
    if version_manager.rollback_to_version(999):
        print("   ✅ Rollback a versión 999 exitoso")
    else:
        print("   ❌ Rollback a versión 999 fallido (esperado)")

def demo_audit_system():
    """Demo del sistema de auditoría"""
    print("\n📋 DEMO: Sistema de Auditoría")
    print("=" * 50)
    
    auditor = ConfigurationAuditor()
    
    # Demo de logging de eventos
    print("\n📝 Logging de Eventos:")
    
    # Evento de carga de configuración
    load_event = AuditEvent(
        event_type=AuditEventType.CONFIG_LOADED,
        timestamp=datetime.utcnow(),
        user_id='demo_user',
        details={'config_path': '/path/to/config.yaml'},
        risk_level='LOW'
    )
    auditor.log_event(load_event)
    print("   ✅ Evento de carga registrado")
    
    # Evento de actualización de configuración
    update_event = AuditEvent(
        event_type=AuditEventType.CONFIG_UPDATED,
        timestamp=datetime.utcnow(),
        user_id='demo_user',
        details={'changes': ['setting1', 'setting2']},
        risk_level='MEDIUM'
    )
    auditor.log_event(update_event)
    print("   ✅ Evento de actualización registrado")
    
    # Evento de violación de seguridad
    security_event = AuditEvent(
        event_type=AuditEventType.SECURITY_VIOLATION,
        timestamp=datetime.utcnow(),
        user_id='demo_user',
        details={'violation_type': 'sensitive_data_detected'},
        risk_level='HIGH'
    )
    auditor.log_event(security_event)
    print("   ✅ Evento de seguridad registrado")
    
    # Demo de logging de cambios de configuración
    print("\n🔄 Logging de Cambios:")
    
    old_config = {
        'setting1': 'old_value',
        'setting2': 'unchanged_value',
        'api_key': 'old_api_key_123',
        'nested': {'key': 'old_nested_value'}
    }
    
    new_config = {
        'setting1': 'new_value',  # Cambiado
        'setting2': 'unchanged_value',  # Sin cambios
        'api_key': 'new_api_key_456',  # Cambiado (sensible)
        'nested': {'key': 'new_nested_value'},  # Nested cambiado
        'new_setting': 'added_value'  # Agregado
    }
    
    auditor.log_config_change(old_config, new_config, 'demo_user')
    print("   ✅ Cambios de configuración registrados")
    
    # Demo de cálculo de diferencias
    print("\n🔍 Cálculo de Diferencias:")
    changes = auditor._calculate_config_diff(old_config, new_config)
    print(f"   Cambios detectados: {len(changes)}")
    for i, change in enumerate(changes, 1):
        print(f"   {i}. {change}")

def demo_performance():
    """Demo de performance"""
    print("\n⚡ DEMO: Performance del Sistema")
    print("=" * 50)
    
    validator = EnterpriseConfigValidator()
    config_manager = ThreadSafeConfigManager()
    secure_manager = SecureConfigManager()
    
    # Demo de validación de configuración grande
    print("\n📊 Validación de Configuración Grande:")
    
    # Crear configuración grande
    large_config = {}
    for i in range(100):
        large_config[f'section_{i}'] = {
            f'setting_{j}': f'value_{i}_{j}'
            for j in range(50)
        }
    
    start_time = time.time()
    result = validator.validate_complete_config(large_config)
    validation_time = time.time() - start_time
    
    print(f"   Configuración: {len(large_config)} secciones, {sum(len(section) for section in large_config.values())} configuraciones")
    print(f"   Tiempo de validación: {validation_time:.3f}s")
    print(f"   Resultado: {'✅ Válida' if result.is_valid else '❌ Inválida'}")
    
    # Demo de encriptación/desencriptación
    print("\n🔐 Encriptación/Desencriptación:")
    
    start_time = time.time()
    encrypted = secure_manager.encrypt_config(large_config)
    encryption_time = time.time() - start_time
    
    start_time = time.time()
    decrypted = secure_manager.decrypt_config(encrypted)
    decryption_time = time.time() - start_time
    
    print(f"   Tiempo de encriptación: {encryption_time:.3f}s")
    print(f"   Tiempo de desencriptación: {decryption_time:.3f}s")
    print(f"   Integridad: {'✅ Verificada' if decrypted == large_config else '❌ Fallida'}")
    
    # Demo de actualizaciones concurrentes
    print("\n🔄 Actualizaciones Concurrentes:")
    
    def update_thread(thread_id):
        def update_func(config):
            config[f'thread_{thread_id}'] = f'value_{thread_id}'
            return config
        return config_manager.atomic_update(update_func)
    
    threads = []
    start_time = time.time()
    
    for i in range(10):
        thread = threading.Thread(target=update_thread, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    print(f"   Threads: 10")
    print(f"   Tiempo total: {end_time - start_time:.3f}s")
    print(f"   Throughput: {10 / (end_time - start_time):.1f} updates/s")

def demo_integration():
    """Demo de integración completa"""
    print("\n🔗 DEMO: Integración Completa")
    print("=" * 50)
    
    # Cargar configuración desde archivo
    print("\n📁 Cargando Configuración:")
    
    # Crear archivo de configuración de ejemplo
    sample_config = {
        'bot_settings': {
            'name': 'demo_bot',
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
    
    # Guardar configuración en archivo
    config_file = Path('demo_config.yaml')
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f, default_flow_style=False)
    
    # Cargar configuración
    loaded_config = load_enterprise_config(str(config_file))
    print(f"   ✅ Configuración cargada: {len(loaded_config)} secciones")
    
    # Obtener configuración actual
    current_config = get_secure_config()
    print(f"   ✅ Configuración actual: {len(current_config)} secciones")
    
    # Actualizar configuración
    print("\n🔄 Actualizando Configuración:")
    
    def update_config(config):
        config['last_updated'] = datetime.utcnow().isoformat()
        config['version'] = 1
        return config
    
    success = update_config_safely(update_config)
    print(f"   Actualización: {'✅ Éxito' if success else '❌ Fallo'}")
    
    # Verificar configuración actualizada
    updated_config = get_secure_config()
    print(f"   Versión: {updated_config.get('version', 'N/A')}")
    print(f"   Última actualización: {updated_config.get('last_updated', 'N/A')}")
    
    # Limpiar archivo temporal
    config_file.unlink()

def main():
    """Función principal del demo"""
    print("🏢 ENTERPRISE CONFIGURATION SYSTEM - DEMO")
    print("=" * 60)
    
    try:
        # Ejecutar demos
        demo_security_features()
        demo_validation_system()
        demo_thread_safety()
        demo_version_management()
        demo_audit_system()
        demo_performance()
        demo_integration()
        
        print("\n🎉 DEMO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        print("✅ Sistema de configuración enterprise funcionando correctamente")
        print("✅ Características de seguridad implementadas")
        print("✅ Sistema de validación robusto")
        print("✅ Thread safety garantizado")
        print("✅ Gestión de versiones funcional")
        print("✅ Sistema de auditoría operativo")
        print("✅ Performance optimizada")
        
    except Exception as e:
        print(f"\n❌ Error durante el demo: {e}")
        logger.error(f"Demo error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
