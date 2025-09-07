"""
monitoring/__init__.py
Módulo de monitoreo y dashboard para el Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\__init__.py

Este módulo contiene el dashboard web completo incluyendo:
- Dashboard web interactivo con Plotly Dash
- Monitoreo en tiempo real de métricas
- Visualización de trades y performance
- Control básico del bot
- Sistema de alertas y notificaciones
"""

from .dashboard import TradingDashboard, start_dashboard, start_dashboard_thread
from .data_provider import DashboardDataProvider
from .layout_components import LayoutComponents
from .chart_components import ChartComponents
from .callbacks import DashboardCallbacks

__version__ = "1.0.0"
__author__ = "Trading Bot v10"

__all__ = [
    # Dashboard principal
    'TradingDashboard',
    'start_dashboard',
    'start_dashboard_thread',
    
    # Componentes
    'DashboardDataProvider',
    'LayoutComponents', 
    'ChartComponents',
    'DashboardCallbacks'
]

# Función de conveniencia para inicio rápido
def quick_start(host='127.0.0.1', port=8050, debug=False):
    """
    Inicia el dashboard de forma rápida
    
    Args:
        host: Host del servidor (default: 127.0.0.1)
        port: Puerto del servidor (default: 8050)
        debug: Modo debug (default: False)
    """
    return start_dashboard(host=host, port=port, debug=debug)