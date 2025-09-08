"""
monitoring/__init__.py
Sistema de Monitoreo para Trading Bot v10

Este módulo proporciona un sistema completo de monitoreo y dashboard
para el bot de trading autónomo.

Características principales:
- Dashboard web interactivo con Dash
- Métricas en tiempo real por símbolo
- Gráficos de velas interactivos
- Análisis de ciclos y rendimiento
- Monitoreo de trading en vivo
- Gestión de riesgo visual
"""

__version__ = "10.0.0"
__author__ = "Trading Bot v10 Team"
__description__ = "Sistema de Monitoreo Avanzado para Trading Bot"

# Importaciones principales del módulo
from monitoring.core.dashboard_app import DashboardApp
from monitoring.core.data_provider import DataProvider
from monitoring.core.real_time_manager import RealTimeManager
from monitoring.core.performance_tracker import PerformanceTracker

# Importaciones de páginas principales
from monitoring.pages.home_page import HomePage
from monitoring.pages.charts_page import ChartsPage
from monitoring.pages.cycles_page import CyclesPage

# Funciones de conveniencia para iniciar el dashboard
def start_dashboard(host='127.0.0.1', port=8050, debug=False, **kwargs):
    """
    Inicia el dashboard principal del sistema de monitoreo
    
    Args:
        host (str): Dirección IP del servidor (default: 127.0.0.1)
        port (int): Puerto del servidor (default: 8050)
        debug (bool): Modo debug de Dash (default: False)
        **kwargs: Argumentos adicionales para la aplicación Dash
    
    Returns:
        DashboardApp: Instancia de la aplicación del dashboard
    """
    app = DashboardApp(**kwargs)
    app.run_server(host=host, port=port, debug=debug)
    return app

def get_data_provider():
    """
    Obtiene una instancia del proveedor de datos centralizado
    
    Returns:
        DataProvider: Instancia del proveedor de datos
    """
    return DataProvider()

def get_performance_tracker():
    """
    Obtiene una instancia del tracker de rendimiento
    
    Returns:
        PerformanceTracker: Instancia del tracker de rendimiento
    """
    return PerformanceTracker()

# Configuración de logging para el módulo
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Crear handler si no existe
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.info(f"Módulo de monitoreo v{__version__} inicializado")

# Exportar elementos principales
__all__ = [
    'DashboardApp',
    'DataProvider', 
    'RealTimeManager',
    'PerformanceTracker',
    'HomePage',
    'ChartsPage',
    'CyclesPage',
    'start_dashboard',
    'get_data_provider',
    'get_performance_tracker',
    '__version__',
    '__author__',
    '__description__'
]

# Verificar dependencias críticas al importar
try:
    import dash
    import plotly
    import pandas as pd
    import numpy as np
    logger.info("Dependencias críticas verificadas correctamente")
except ImportError as e:
    logger.error(f"Error al importar dependencias críticas: {e}")
    logger.error("Instale las dependencias con: pip install dash plotly pandas numpy")
    raise

# Configuración global del módulo
MONITORING_CONFIG = {
    'default_host': '127.0.0.1',
    'default_port': 8050,
    'update_interval': 5000,  # 5 segundos
    'max_data_points': 10000,
    'cache_timeout': 300,  # 5 minutos
    'theme': 'dark',
    'responsive': True
}

def get_config():
    """Obtiene la configuración global del módulo de monitoreo"""
    return MONITORING_CONFIG.copy()

def update_config(**kwargs):
    """Actualiza la configuración global del módulo"""
    MONITORING_CONFIG.update(kwargs)
    logger.info(f"Configuración actualizada: {kwargs}")