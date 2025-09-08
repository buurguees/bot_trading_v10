"""
models/enterprise/__init__.py - Enterprise ML Models System
Sistema de modelos ML enterprise-grade para trading bot
"""

from .thread_safe_manager import ThreadSafeModelManager, ReadWriteLock
from .validation_system import PredictionRequest, DataSanitizer, ValidationResult
from .circuit_breakers import MLCircuitBreaker, GracefulDegradationHandler
from .observability import MLMetricsCollector, DistributedTracing, BusinessMetricsTracker
from .testing_framework import ModelTestSuite, BacktestValidation, PerformanceTestSuite, EnterpriseTestRunner
from .deployment import ModelServingInfrastructure, BlueGreenDeployment, KubernetesDeployment, DockerManager
from .security import MLSecurityManager, ComplianceManager, SecurityConfig

__version__ = "1.0.0"
__author__ = "Trading Bot Enterprise Team"

# Export main classes
__all__ = [
    # Thread Safety
    "ThreadSafeModelManager",
    "ReadWriteLock",
    
    # Validation
    "PredictionRequest",
    "DataSanitizer", 
    "ValidationResult",
    
    # Circuit Breakers
    "MLCircuitBreaker",
    "GracefulDegradationHandler",
    
    # Observability
    "MLMetricsCollector",
    "DistributedTracing",
    "BusinessMetricsTracker",
    
    # Testing
    "ModelTestSuite",
    "BacktestValidation",
    "PerformanceTestSuite",
    "EnterpriseTestRunner",
    
    # Deployment
    "ModelServingInfrastructure",
    "BlueGreenDeployment",
    "KubernetesDeployment",
    "DockerManager",
    
    # Security
    "MLSecurityManager",
    "ComplianceManager",
    "SecurityConfig"
]

# Global instances
thread_safe_manager = ThreadSafeModelManager()
data_sanitizer = DataSanitizer()
circuit_breaker = MLCircuitBreaker()
metrics_collector = MLMetricsCollector()
tracing = DistributedTracing()
business_metrics = BusinessMetricsTracker()
security_manager = MLSecurityManager()
compliance_manager = ComplianceManager()

# Convenience functions
def initialize_enterprise_system(config: dict = None):
    """Initialize the complete enterprise ML system"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Initializing Enterprise ML System")
    
    try:
        # Initialize all components
        components = {
            "thread_safe_manager": thread_safe_manager,
            "data_sanitizer": data_sanitizer,
            "circuit_breaker": circuit_breaker,
            "metrics_collector": metrics_collector,
            "tracing": tracing,
            "business_metrics": business_metrics,
            "security_manager": security_manager,
            "compliance_manager": compliance_manager
        }
        
        # Initialize each component
        for name, component in components.items():
            if hasattr(component, 'initialize'):
                component.initialize()
            logger.info(f"Initialized {name}")
        
        logger.info("Enterprise ML System initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Enterprise ML System: {e}")
        return False

def get_system_status() -> dict:
    """Get overall system status"""
    status = {
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "version": __version__,
        "components": {}
    }
    
    # Check each component
    components = {
        "thread_safe_manager": thread_safe_manager,
        "data_sanitizer": data_sanitizer,
        "circuit_breaker": circuit_breaker,
        "metrics_collector": metrics_collector,
        "tracing": tracing,
        "business_metrics": business_metrics,
        "security_manager": security_manager,
        "compliance_manager": compliance_manager
    }
    
    for name, component in components.items():
        try:
            if hasattr(component, 'get_status'):
                status["components"][name] = component.get_status()
            else:
                status["components"][name] = {"status": "unknown"}
        except Exception as e:
            status["components"][name] = {"status": "error", "error": str(e)}
    
    return status

def run_enterprise_tests() -> dict:
    """Run all enterprise tests"""
    from .testing_framework import run_enterprise_tests
    return run_enterprise_tests()

def get_security_report() -> dict:
    """Get security report"""
    return security_manager.get_security_report()

def get_compliance_report() -> dict:
    """Get compliance report"""
    return compliance_manager.get_compliance_report()

def get_performance_metrics() -> dict:
    """Get performance metrics"""
    return metrics_collector.get_metrics_summary()

# System health check
def health_check() -> dict:
    """Perform system health check"""
    try:
        status = get_system_status()
        
        # Check if all components are healthy
        healthy_components = sum(
            1 for comp in status["components"].values()
            if comp.get("status") == "healthy"
        )
        
        total_components = len(status["components"])
        health_score = healthy_components / total_components if total_components > 0 else 0
        
        return {
            "status": "healthy" if health_score > 0.8 else "degraded",
            "health_score": health_score,
            "healthy_components": healthy_components,
            "total_components": total_components,
            "timestamp": status["timestamp"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
