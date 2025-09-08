"""
core/error_handler.py - Sistema Robusto de Manejo de Errores
Sistema centralizado para manejo, logging y recuperación de errores
"""

import logging
import traceback
import asyncio
from typing import Dict, Any, Optional, Callable, Type, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import functools
import sys

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Niveles de severidad de errores"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categorías de errores"""
    DATABASE = "database"
    MODEL = "model"
    API = "api"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TRADING = "trading"
    VALIDATION = "validation"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Contexto de un error"""
    timestamp: datetime
    function_name: str
    module_name: str
    line_number: int
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}

class SystemError(Exception):
    """Error base del sistema"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}

class DatabaseError(SystemError):
    """Error de base de datos"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.DATABASE, severity, context)

class ModelError(SystemError):
    """Error de modelo de ML"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.MODEL, severity, context)

class APIError(SystemError):
    """Error de API externa"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.API, severity, context)

class ConfigurationError(SystemError):
    """Error de configuración"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.CRITICAL, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.CONFIGURATION, severity, context)

class ResourceError(SystemError):
    """Error de recursos del sistema"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.RESOURCE, severity, context)

class TradingError(SystemError):
    """Error de trading"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.CRITICAL, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.TRADING, severity, context)

class ValidationError(SystemError):
    """Error de validación"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.VALIDATION, severity, context)

class ErrorHandler:
    """Manejador principal de errores"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history: list[ErrorContext] = []
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self.max_history_size = 1000
        
        # Configurar estrategias de recuperación por defecto
        self._setup_default_recovery_strategies()
    
    def _setup_default_recovery_strategies(self):
        """Configura estrategias de recuperación por defecto"""
        self.recovery_strategies = {
            ErrorCategory.DATABASE: self._recover_database_error,
            ErrorCategory.MODEL: self._recover_model_error,
            ErrorCategory.API: self._recover_api_error,
            ErrorCategory.CONFIGURATION: self._recover_configuration_error,
            ErrorCategory.RESOURCE: self._recover_resource_error,
            ErrorCategory.TRADING: self._recover_trading_error,
            ErrorCategory.VALIDATION: self._recover_validation_error,
            ErrorCategory.SYSTEM: self._recover_system_error
        }
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """Maneja un error y registra el contexto"""
        # Crear contexto del error
        error_context = self._create_error_context(error, context)
        
        # Agregar a historial
        self._add_to_history(error_context)
        
        # Log del error
        self._log_error(error_context)
        
        # Intentar recuperación si es posible
        if isinstance(error, SystemError):
            self._attempt_recovery(error_context)
        
        return error_context
    
    def _create_error_context(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """Crea el contexto de un error"""
        # Obtener información del traceback
        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            frame = tb[-1]
            function_name = frame.name
            module_name = frame.filename.split('/')[-1] if '/' in frame.filename else frame.filename
            line_number = frame.lineno
        else:
            function_name = "unknown"
            module_name = "unknown"
            line_number = 0
        
        # Determinar severidad y categoría
        if isinstance(error, SystemError):
            severity = error.severity
            category = error.category
        else:
            severity = self._determine_severity(error)
            category = self._determine_category(error)
        
        return ErrorContext(
            timestamp=datetime.now(),
            function_name=function_name,
            module_name=module_name,
            line_number=line_number,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            category=category,
            additional_data=context or {}
        )
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determina la severidad de un error basado en su tipo"""
        error_type = type(error).__name__.lower()
        
        if any(keyword in error_type for keyword in ['critical', 'fatal', 'panic']):
            return ErrorSeverity.CRITICAL
        elif any(keyword in error_type for keyword in ['error', 'exception', 'failed']):
            return ErrorSeverity.HIGH
        elif any(keyword in error_type for keyword in ['warning', 'caution']):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _determine_category(self, error: Exception) -> ErrorCategory:
        """Determina la categoría de un error basado en su tipo"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        if any(keyword in error_type or keyword in error_message for keyword in ['database', 'sql', 'connection']):
            return ErrorCategory.DATABASE
        elif any(keyword in error_type or keyword in error_message for keyword in ['model', 'tensor', 'keras', 'tensorflow']):
            return ErrorCategory.MODEL
        elif any(keyword in error_type or keyword in error_message for keyword in ['api', 'http', 'request', 'network']):
            return ErrorCategory.API
        elif any(keyword in error_type or keyword in error_message for keyword in ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        elif any(keyword in error_type or keyword in error_message for keyword in ['memory', 'disk', 'resource', 'cpu']):
            return ErrorCategory.RESOURCE
        elif any(keyword in error_type or keyword in error_message for keyword in ['trade', 'order', 'position']):
            return ErrorCategory.TRADING
        elif any(keyword in error_type or keyword in error_message for keyword in ['validation', 'validate', 'invalid']):
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    def _add_to_history(self, error_context: ErrorContext):
        """Agrega un error al historial"""
        self.error_history.append(error_context)
        
        # Mantener el historial dentro del límite
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _log_error(self, error_context: ErrorContext):
        """Registra un error en el log"""
        log_message = (
            f"Error in {error_context.module_name}.{error_context.function_name}:{error_context.line_number} - "
            f"{error_context.error_type}: {error_context.error_message}"
        )
        
        # Log con nivel apropiado
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra=error_context.additional_data)
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra=error_context.additional_data)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra=error_context.additional_data)
        else:
            self.logger.info(log_message, extra=error_context.additional_data)
    
    def _attempt_recovery(self, error_context: ErrorContext):
        """Intenta recuperar de un error"""
        try:
            recovery_func = self.recovery_strategies.get(error_context.category)
            if recovery_func:
                recovery_func(error_context)
        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
    
    # Estrategias de recuperación
    def _recover_database_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de base de datos"""
        self.logger.info("Attempting database recovery...")
        # Implementar lógica de recuperación de BD
        pass
    
    def _recover_model_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de modelo"""
        self.logger.info("Attempting model recovery...")
        # Implementar lógica de recuperación de modelo
        pass
    
    def _recover_api_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de API"""
        self.logger.info("Attempting API recovery...")
        # Implementar lógica de recuperación de API
        pass
    
    def _recover_configuration_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de configuración"""
        self.logger.info("Attempting configuration recovery...")
        # Implementar lógica de recuperación de configuración
        pass
    
    def _recover_resource_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de recursos"""
        self.logger.info("Attempting resource recovery...")
        # Implementar lógica de recuperación de recursos
        pass
    
    def _recover_trading_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de trading"""
        self.logger.info("Attempting trading recovery...")
        # Implementar lógica de recuperación de trading
        pass
    
    def _recover_validation_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores de validación"""
        self.logger.info("Attempting validation recovery...")
        # Implementar lógica de recuperación de validación
        pass
    
    def _recover_system_error(self, error_context: ErrorContext):
        """Estrategia de recuperación para errores del sistema"""
        self.logger.info("Attempting system recovery...")
        # Implementar lógica de recuperación del sistema
        pass
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de errores"""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Contar por severidad
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Contar por categoría
        category_counts = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Errores recientes (últimas 24 horas)
        recent_errors = [
            error for error in self.error_history
            if (datetime.now() - error.timestamp).total_seconds() < 86400
        ]
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "last_error": self.error_history[-1].timestamp.isoformat() if self.error_history else None
        }

# Instancia global
error_handler = ErrorHandler()

# Decoradores para manejo automático de errores
def handle_errors(category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 reraise: bool = True):
    """Decorador para manejo automático de errores"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:100],  # Limitar tamaño
                    "kwargs": str(kwargs)[:100]
                }
                error_handler.handle_error(e, context)
                if reraise:
                    raise
                return None
        return wrapper
    return decorator

def handle_async_errors(category: ErrorCategory = ErrorCategory.SYSTEM,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       reraise: bool = True):
    """Decorador para manejo automático de errores en funciones async"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100]
                }
                error_handler.handle_error(e, context)
                if reraise:
                    raise
                return None
        return wrapper
    return decorator

# Funciones de conveniencia
def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorContext:
    """Registra un error y devuelve su contexto"""
    return error_handler.handle_error(error, context)

def get_error_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de errores"""
    return error_handler.get_error_stats()

def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """Ejecuta una función de forma segura con manejo de errores"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(e)
        return None

async def safe_execute_async(func: Callable, *args, **kwargs) -> Any:
    """Ejecuta una función async de forma segura con manejo de errores"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(e)
        return None
