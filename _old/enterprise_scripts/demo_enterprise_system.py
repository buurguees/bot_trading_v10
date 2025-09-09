"""
demo_enterprise_system.py - Demo del Sistema Enterprise ML
Demostración completa del sistema de modelos ML enterprise-grade
"""

import asyncio
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import enterprise system
from models.enterprise import (
    initialize_enterprise_system,
    get_system_status,
    health_check,
    run_enterprise_tests,
    get_security_report,
    get_compliance_report,
    get_performance_metrics,
    thread_safe_manager,
    data_sanitizer,
    circuit_breaker,
    metrics_collector,
    tracing,
    business_metrics,
    security_manager,
    compliance_manager
)

async def demo_thread_safety():
    """Demo de thread safety"""
    print("\n🔒 DEMO: Thread Safety & Concurrency")
    print("=" * 50)
    
    # Simular múltiples requests concurrentes
    async def make_prediction(symbol, features):
        try:
            # Simular validación de datos
            sanitized_features = data_sanitizer.sanitize_features(features)
            
            # Simular predicción con thread safety
            with thread_safe_manager.get_read_lock():
                # Simular predicción
                prediction = np.random.choice(['buy', 'sell', 'hold'])
                confidence = np.random.uniform(0.6, 0.95)
                
                # Registrar métricas
                metrics_collector.record_prediction(
                    symbol=symbol,
                    prediction=prediction,
                    confidence=confidence,
                    latency_ms=np.random.uniform(10, 50)
                )
                
                return {
                    "symbol": symbol,
                    "prediction": prediction,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error in prediction for {symbol}: {e}")
            return None
    
    # Crear múltiples requests concurrentes
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    tasks = []
    
    for i in range(20):  # 20 requests concurrentes
        symbol = symbols[i % len(symbols)]
        features = np.random.random(50).tolist()
        task = make_prediction(symbol, features)
        tasks.append(task)
    
    # Ejecutar concurrentemente
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # Analizar resultados
    successful = sum(1 for r in results if isinstance(r, dict) and r is not None)
    failed = len(results) - successful
    
    print(f"✅ Requests procesados: {len(results)}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    print(f"⏱️ Tiempo total: {end_time - start_time:.2f}s")
    print(f"🚀 Throughput: {len(results) / (end_time - start_time):.2f} req/s")

def demo_validation_system():
    """Demo del sistema de validación"""
    print("\n🔍 DEMO: Input Validation & Data Sanitization")
    print("=" * 50)
    
    # Casos de prueba
    test_cases = [
        {
            "name": "Request válido",
            "data": {
                "symbol": "BTCUSDT",
                "features": np.random.random(50).tolist(),
                "request_id": "test_001",
                "model_version": "v1.0.0"
            }
        },
        {
            "name": "Request con símbolo inválido",
            "data": {
                "symbol": "INVALID_SYMBOL",
                "features": np.random.random(50).tolist(),
                "request_id": "test_002",
                "model_version": "v1.0.0"
            }
        },
        {
            "name": "Request con features inválidas",
            "data": {
                "symbol": "BTCUSDT",
                "features": [float('inf'), float('nan'), 'invalid'],
                "request_id": "test_003",
                "model_version": "v1.0.0"
            }
        },
        {
            "name": "Request con features insuficientes",
            "data": {
                "symbol": "BTCUSDT",
                "features": [1, 2, 3],  # Solo 3 features
                "request_id": "test_004",
                "model_version": "v1.0.0"
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n📋 Caso: {case['name']}")
        
        # Validar request
        from models.enterprise.validation_system import validate_prediction_request
        validated_request, validation_result = validate_prediction_request(case['data'])
        
        print(f"   Validación: {'✅ Válido' if validation_result.is_valid else '❌ Inválido'}")
        if not validation_result.is_valid:
            print(f"   Errores: {validation_result.errors}")
        
        # Sanitizar features
        if validation_result.is_valid:
            sanitized_features = data_sanitizer.sanitize_features(validated_request.features)
            print(f"   Features sanitizadas: {len(sanitized_features)}")

def demo_circuit_breakers():
    """Demo de circuit breakers"""
    print("\n⚡ DEMO: Circuit Breakers & Fault Tolerance")
    print("=" * 50)
    
    # Simular diferentes escenarios
    scenarios = [
        {"name": "Operación exitosa", "success": True, "latency": 0.1},
        {"name": "Operación lenta", "success": True, "latency": 2.0},
        {"name": "Operación fallida", "success": False, "latency": 0.05},
        {"name": "Operación exitosa", "success": True, "latency": 0.2},
        {"name": "Operación fallida", "success": False, "latency": 0.03},
        {"name": "Operación fallida", "success": False, "latency": 0.02},
        {"name": "Operación fallida", "success": False, "latency": 0.01},
        {"name": "Operación fallida", "success": False, "latency": 0.01},
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\n🔄 Escenario {i+1}: {scenario['name']}")
        
        # Simular operación
        start_time = time.time()
        time.sleep(scenario['latency'])
        end_time = time.time()
        
        # Registrar en circuit breaker
        success = circuit_breaker.record_success() if scenario['success'] else circuit_breaker.record_failure()
        
        print(f"   Resultado: {'✅ Éxito' if scenario['success'] else '❌ Fallo'}")
        print(f"   Latencia: {(end_time - start_time) * 1000:.1f}ms")
        print(f"   Circuit Breaker: {circuit_breaker.get_state()}")
        print(f"   Success Rate: {circuit_breaker.get_success_rate():.2%}")
        
        # Verificar si el circuit breaker está abierto
        if circuit_breaker.is_open():
            print("   🚨 CIRCUIT BREAKER ABIERTO - Operaciones bloqueadas")
            break

def demo_observability():
    """Demo del sistema de observabilidad"""
    print("\n📊 DEMO: Observability & Monitoring")
    print("=" * 50)
    
    # Simular métricas de trading
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    for symbol in symbols:
        # Simular predicciones
        for _ in range(10):
            prediction = np.random.choice(['buy', 'sell', 'hold'])
            confidence = np.random.uniform(0.6, 0.95)
            latency = np.random.uniform(10, 100)
            
            # Registrar métricas
            metrics_collector.record_prediction(
                symbol=symbol,
                prediction=prediction,
                confidence=confidence,
                latency_ms=latency
            )
            
            # Registrar métricas de negocio
            if prediction == 'buy':
                business_metrics.record_trade_signal(
                    symbol=symbol,
                    signal_type='buy',
                    confidence=confidence,
                    market_conditions={'volatility': np.random.uniform(0.1, 0.5)}
                )
    
    # Mostrar métricas
    print("\n📈 Métricas de Performance:")
    metrics = metrics_collector.get_metrics_summary()
    print(f"   Total predicciones: {metrics['total_predictions']}")
    print(f"   Latencia promedio: {metrics['avg_latency_ms']:.1f}ms")
    print(f"   Throughput: {metrics['throughput_per_second']:.1f} req/s")
    
    print("\n💰 Métricas de Negocio:")
    business_metrics_data = business_metrics.get_metrics_summary()
    print(f"   Señales de trading: {business_metrics_data['total_signals']}")
    print(f"   Señales BUY: {business_metrics_data['buy_signals']}")
    print(f"   Señales SELL: {business_metrics_data['sell_signals']}")
    
    # Simular tracing
    print("\n🔍 Distributed Tracing:")
    with tracing.start_span("trading_cycle") as span:
        span.set_attribute("symbols", symbols)
        span.set_attribute("cycle_id", "demo_001")
        
        with tracing.start_span("data_collection") as data_span:
            data_span.set_attribute("data_source", "exchange_api")
            time.sleep(0.1)  # Simular recolección de datos
        
        with tracing.start_span("model_prediction") as model_span:
            model_span.set_attribute("model_version", "v1.0.0")
            time.sleep(0.2)  # Simular predicción
        
        with tracing.start_span("risk_assessment") as risk_span:
            risk_span.set_attribute("risk_level", "medium")
            time.sleep(0.05)  # Simular evaluación de riesgo

def demo_security():
    """Demo del sistema de seguridad"""
    print("\n🔐 DEMO: Security & Compliance")
    print("=" * 50)
    
    # Simular encriptación de modelo
    print("\n🔒 Encriptación de Modelo:")
    model_data = b"Mock model data for encryption demo"
    model_id = "demo_model_v1.0.0"
    
    try:
        encrypted_data = security_manager.encrypt_model_artifacts(model_data, model_id)
        print(f"   ✅ Modelo encriptado: {len(encrypted_data['encrypted_data'])} bytes")
        print(f"   🔑 Hash de integridad: {encrypted_data['integrity_hash'][:16]}...")
        
        # Desencriptar
        decrypted_data = security_manager.decrypt_model_artifacts(encrypted_data, model_id)
        print(f"   ✅ Modelo desencriptado: {len(decrypted_data)} bytes")
        print(f"   ✅ Integridad verificada: {decrypted_data == model_data}")
        
    except Exception as e:
        print(f"   ❌ Error en encriptación: {e}")
    
    # Simular validación de compliance
    print("\n📋 Validación de Compliance:")
    model_config = {
        "model_id": "demo_model_v1.0.0",
        "version": "1.0.0",
        "model_name": "TradingModel",
        "framework": "tensorflow",
        "algorithm": "LSTM",
        "input_features": 50,
        "output_classes": 3,
        "performance_metrics": {"accuracy": 0.85, "precision": 0.82},
        "training_data_source": "exchange_api",
        "approval_status": "approved",
        "approved_by": "compliance_team",
        "encryption_enabled": True,
        "audit_logging_enabled": True,
        "max_position_size": 1000,
        "max_daily_trades": 50
    }
    
    compliance_result = compliance_manager.validate_model_deployment(model_config)
    print(f"   Compliance: {'✅ Cumple' if compliance_result['compliant'] else '❌ No cumple'}")
    
    for check_name, check_result in compliance_result['checks'].items():
        status = "✅" if check_result['passed'] else "❌"
        print(f"   {check_name}: {status}")

def demo_testing():
    """Demo del sistema de testing"""
    print("\n🧪 DEMO: Enterprise Testing Framework")
    print("=" * 50)
    
    # Ejecutar tests enterprise
    print("Ejecutando tests enterprise...")
    test_results = run_enterprise_tests()
    
    print(f"\n📊 Resultados de Tests:")
    print(f"   Total tests: {test_results['summary']['total_tests']}")
    print(f"   Tests pasados: {test_results['summary']['total_passed']}")
    print(f"   Tasa de éxito: {test_results['summary']['success_rate']:.2%}")
    
    print(f"\n📋 Tests por Categoría:")
    for category, results in test_results.items():
        if category != 'summary':
            print(f"   {category}: {results.get('passed', 0)}/{results.get('total', 0)}")

def demo_deployment():
    """Demo del sistema de deployment"""
    print("\n🚀 DEMO: Production Deployment")
    print("=" * 50)
    
    # Simular configuración de deployment
    from models.enterprise.deployment import ModelServingConfig, DeploymentConfig
    
    deployment_config = DeploymentConfig(
        environment="demo",
        namespace="trading-bot-demo",
        replicas=2,
        cpu_limit="500m",
        memory_limit="1Gi"
    )
    
    model_config = ModelServingConfig(
        model_name="trading_model",
        model_version="v1.0.0",
        model_path="/models/trading_model_v1.0.0",
        serving_framework="tensorflow-serving",
        batch_size=16,
        max_concurrent_requests=50
    )
    
    print(f"📦 Configuración de Deployment:")
    print(f"   Entorno: {deployment_config.environment}")
    print(f"   Namespace: {deployment_config.namespace}")
    print(f"   Réplicas: {deployment_config.replicas}")
    print(f"   CPU Limit: {deployment_config.cpu_limit}")
    print(f"   Memory Limit: {deployment_config.memory_limit}")
    
    print(f"\n🤖 Configuración de Modelo:")
    print(f"   Nombre: {model_config.model_name}")
    print(f"   Versión: {model_config.model_version}")
    print(f"   Framework: {model_config.serving_framework}")
    print(f"   Batch Size: {model_config.batch_size}")
    print(f"   Max Concurrent: {model_config.max_concurrent_requests}")

async def main():
    """Función principal del demo"""
    print("🏢 ENTERPRISE ML MODELS SYSTEM - DEMO")
    print("=" * 60)
    
    # Inicializar sistema
    print("\n🚀 Inicializando sistema enterprise...")
    success = initialize_enterprise_system()
    if not success:
        print("❌ Error inicializando sistema")
        return
    
    print("✅ Sistema inicializado correctamente")
    
    # Verificar estado del sistema
    print("\n📊 Estado del Sistema:")
    status = get_system_status()
    print(f"   Versión: {status['version']}")
    print(f"   Componentes: {len(status['components'])}")
    
    # Health check
    health = health_check()
    print(f"   Estado: {health['status']}")
    print(f"   Health Score: {health['health_score']:.2%}")
    
    # Ejecutar demos
    await demo_thread_safety()
    demo_validation_system()
    demo_circuit_breakers()
    demo_observability()
    demo_security()
    demo_testing()
    demo_deployment()
    
    # Reportes finales
    print("\n📋 REPORTES FINALES")
    print("=" * 50)
    
    print("\n🔐 Reporte de Seguridad:")
    security_report = get_security_report()
    print(f"   Eventos 24h: {security_report['total_events_24h']}")
    print(f"   Intentos fallidos: {security_report['failed_attempts']}")
    print(f"   Requests bloqueados: {security_report['blocked_requests']}")
    print(f"   Estado: {security_report['security_status']}")
    
    print("\n📋 Reporte de Compliance:")
    compliance_report = get_compliance_report()
    print(f"   Eventos 30d: {compliance_report['total_events_30d']}")
    print(f"   Estado: {compliance_report['compliance_status']}")
    print(f"   Próxima revisión: {compliance_report['next_review_date']}")
    
    print("\n📊 Métricas de Performance:")
    performance_metrics = get_performance_metrics()
    print(f"   Total predicciones: {performance_metrics['total_predictions']}")
    print(f"   Latencia promedio: {performance_metrics['avg_latency_ms']:.1f}ms")
    print(f"   Throughput: {performance_metrics['throughput_per_second']:.1f} req/s")
    
    print("\n🎉 DEMO COMPLETADO EXITOSAMENTE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
