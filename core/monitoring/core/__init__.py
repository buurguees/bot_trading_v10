# Ruta: core/monitoring/core/__init__.py
"""
monitoring/core/__init__.py
Núcleo del Sistema de Monitoreo - Trading Bot v10

Este módulo contiene las funcionalidades centrales del sistema de monitoreo,
incluyendo la aplicación principal, proveedores de datos, gestión en tiempo real
y tracking de rendimiento.

Componentes principales:
- DashboardApp: Aplicación principal del dashboard
- DataProvider: Proveedor centralizado de datos
- RealTimeManager: Gestión de datos en tiempo real
- PerformanceTracker: Seguimiento de métricas de rendimiento
"""

__version__ = "10.0.0"
__description__ = "Núcleo del Sistema de Monitoreo"

# Importaciones de componentes core
from monitoring.core.dashboard_app import DashboardApp
from monitoring.core.data_provider import DataProvider
from monitoring.core.real_time_manager import RealTimeManager
from monitoring.core.performance_tracker import PerformanceTracker

# Configuración de logging para el core
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuración específica del core
CORE_CONFIG = {
    'data_refresh_interval': 5000,  # 5 segundos
    'performance_calculation_interval': 30000,  # 30 segundos
    'real_time_buffer_size': 1000,
    'max_concurrent_updates': 10,
    'cache_expiry_seconds': 300,  # 5 minutos
    'error_retry_attempts': 3,
    'connection_timeout': 10  # segundos
}

class CoreManager:
    """
    Gestor centralizado de todos los componentes core del sistema de monitoreo
    """
    
    def __init__(self):
        self.dashboard_app = None
        self.data_provider = None
        self.real_time_manager = None
        self.performance_tracker = None
        self._initialized = False
        
        logger.info("CoreManager inicializado")
    
    def initialize(self, config=None):
        """
        Inicializa todos los componentes core del sistema
        
        Args:
            config (dict, optional): Configuración personalizada
        """
        if self._initialized:
            logger.warning("CoreManager ya está inicializado")
            return
        
        try:
            # Aplicar configuración personalizada si se proporciona
            if config:
                CORE_CONFIG.update(config)
            
            # Inicializar componentes en orden de dependencias
            self.data_provider = DataProvider()
            self.real_time_manager = RealTimeManager(self.data_provider)
            self.performance_tracker = PerformanceTracker(self.data_provider)
            self.dashboard_app = DashboardApp(
                data_provider=self.data_provider,
                real_time_manager=self.real_time_manager,
                performance_tracker=self.performance_tracker
            )
            
            self._initialized = True
            logger.info("Todos los componentes core inicializados correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar componentes core: {e}")
            raise
    
    def start_dashboard(self, host='127.0.0.1', port=8050, debug=False):
        """
        Inicia el dashboard con todos los componentes core
        
        Args:
            host (str): Host del servidor
            port (int): Puerto del servidor
            debug (bool): Modo debug
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"Iniciando dashboard en http://{host}:{port}")
        self.dashboard_app.run(host=host, port=port, debug=debug)
    
    def stop_all(self):
        """Detiene todos los componentes y limpia recursos"""
        try:
            if self.real_time_manager:
                self.real_time_manager.stop()
            
            if self.performance_tracker:
                self.performance_tracker.stop()
            
            logger.info("Todos los componentes core detenidos")
            
        except Exception as e:
            logger.error(f"Error al detener componentes: {e}")
    
    def get_status(self):
        """
        Obtiene el estado de todos los componentes core
        
        Returns:
            dict: Estado de cada componente
        """
        return {
            'initialized': self._initialized,
            'dashboard_app': self.dashboard_app is not None,
            'data_provider': self.data_provider is not None and self.data_provider.is_connected(),
            'real_time_manager': self.real_time_manager is not None and self.real_time_manager.is_running(),
            'performance_tracker': self.performance_tracker is not None and self.performance_tracker.is_active()
        }

# Instancia global del gestor core (singleton pattern)
_core_manager = None

def get_core_manager():
    """
    Obtiene la instancia global del CoreManager (singleton)
    
    Returns:
        CoreManager: Instancia global del gestor core
    """
    global _core_manager
    if _core_manager is None:
        _core_manager = CoreManager()
    return _core_manager

def initialize_core(config=None):
    """
    Inicializa el sistema core completo
    
    Args:
        config (dict, optional): Configuración personalizada
    """
    core_manager = get_core_manager()
    core_manager.initialize(config)
    return core_manager

def start_monitoring_system(host='127.0.0.1', port=8050, debug=False, config=None):
    """
    Función de conveniencia para iniciar todo el sistema de monitoreo
    
    Args:
        host (str): Host del servidor
        port (int): Puerto del servidor  
        debug (bool): Modo debug
        config (dict, optional): Configuración personalizada
    """
    core_manager = initialize_core(config)
    core_manager.start_dashboard(host, port, debug)

def get_config():
    """Obtiene la configuración actual del core"""
    return CORE_CONFIG.copy()

def update_config(**kwargs):
    """Actualiza la configuración del core"""
    CORE_CONFIG.update(kwargs)
    logger.info(f"Configuración core actualizada: {kwargs}")

# Verificar dependencias críticas
def check_dependencies():
    """Verifica que todas las dependencias críticas estén disponibles"""
    missing_deps = []
    
    try:
        import dash
    except ImportError:
        missing_deps.append('dash')
    
    try:
        import plotly
    except ImportError:
        missing_deps.append('plotly')
    
    try:
        import pandas
    except ImportError:
        missing_deps.append('pandas')
    
    try:
        import numpy
    except ImportError:
        missing_deps.append('numpy')
    
    if missing_deps:
        error_msg = f"Dependencias faltantes: {', '.join(missing_deps)}"
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    logger.info("Todas las dependencias core verificadas")
    return True

# Verificar dependencias al importar el módulo
check_dependencies()

# Exportar elementos principales
__all__ = [
    'DashboardApp',
    'DataProvider',
    'RealTimeManager', 
    'PerformanceTracker',
    'CoreManager',
    'get_core_manager',
    'initialize_core',
    'start_monitoring_system',
    'get_config',
    'update_config',
    'check_dependencies',
    'CORE_CONFIG'
]

logger.info(f"Módulo core v{__version__} cargado correctamente")