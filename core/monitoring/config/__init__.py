# Ruta: core/monitoring/config/__init__.py
"""
monitoring/config/__init__.py
Configuración del Sistema de Monitoreo - Trading Bot v10

Este módulo contiene todas las configuraciones relacionadas con el
sistema de monitoreo, dashboard y componentes visuales.
"""

from monitoring.config.dashboard_config import (
    DASHBOARD_CONFIG,
    PAGE_CONFIG,
    METRICS_CONFIG,
    ALERTS_CONFIG,
    EXPORT_CONFIG,
    LAYOUT_CONFIG,
    COMPONENT_CONFIG,
    get_config,
    update_config,
    get_page_config,
    get_metric_config,
    is_dev_mode
)

__version__ = "10.0.0"
__description__ = "Configuración del Sistema de Monitoreo"

__all__ = [
    'DASHBOARD_CONFIG',
    'PAGE_CONFIG', 
    'METRICS_CONFIG',
    'ALERTS_CONFIG',
    'EXPORT_CONFIG',
    'LAYOUT_CONFIG',
    'COMPONENT_CONFIG',
    'get_config',
    'update_config',
    'get_page_config',
    'get_metric_config',
    'is_dev_mode'
]