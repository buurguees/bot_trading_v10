"""
monitoring/dashboard.py
Dashboard web interactivo para el Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\dashboard.py

Funcionalidades:
- Dashboard web con múltiples páginas
- Visualización en tiempo real de métricas
- Gráficos interactivos con Plotly
- Updates automáticos cada 5 segundos
- Interfaz responsive y moderna
"""

import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import threading
import time
import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from config.config_loader import user_config
from .data_provider import DashboardDataProvider
from .layout_components import LayoutComponents
from .chart_components import ChartComponents
from .callbacks import register_callbacks

logger = logging.getLogger(__name__)

class TradingDashboard:
    """Dashboard principal del Trading Bot v10"""
    
    def __init__(self, host='127.0.0.1', port=8050, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Inicializar componentes
        self.data_provider = DashboardDataProvider()
        self.layout_components = LayoutComponents()
        self.chart_components = ChartComponents()
        
        # Configurar Dash app
        self.app = dash.Dash(
            __name__,
            suppress_callback_exceptions=True,
            external_stylesheets=[
                'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
            ],
            meta_tags=[
                {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
            ]
        )
        
        # Configurar layout principal
        self.setup_layout()
        
        # Registrar callbacks
        self.setup_callbacks()
        
        logger.info(f"Dashboard inicializado en {host}:{port}")
    
    def setup_layout(self):
        """Configura el layout principal del dashboard"""
        
        self.app.layout = html.Div([
            # URL Location Component
            dcc.Location(id='url', refresh=False),
            
            # Header fijo
            self.layout_components.create_header(),
            
            # Container principal
            html.Div(
                id='page-content',
                className='dashboard-content',
                style={'margin-top': '70px', 'padding': '20px'}
            ),
            
            # Interval para updates automáticos
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # 5 segundos
                n_intervals=0
            ),
            
            # Store para datos compartidos
            dcc.Store(id='dashboard-data'),
            dcc.Store(id='bot-status'),
            
        ], className='dashboard-container')
    
    def setup_callbacks(self):
        """Registra todos los callbacks del dashboard"""
        
        # Callback para navegación entre páginas
        @self.app.callback(
            Output('page-content', 'children'),
            Input('url', 'pathname')
        )
        def display_page(pathname):
            if pathname == '/' or pathname == '/home':
                return self.layout_components.create_home_page()
            elif pathname == '/trading':
                return self.layout_components.create_trading_page()
            elif pathname == '/performance':
                return self.layout_components.create_performance_page()
            elif pathname == '/settings':
                return self.layout_components.create_settings_page()
            elif pathname == '/alerts':
                return self.layout_components.create_alerts_page()
            elif pathname == '/chat':
                return self.layout_components.create_chat_page()
            else:
                return self.layout_components.create_404_page()
        
        # Callback para actualización de datos
        @self.app.callback(
            [Output('dashboard-data', 'data'),
             Output('bot-status', 'data')],
            Input('interval-component', 'n_intervals')
        )
        def update_dashboard_data(n):
            """Actualiza datos del dashboard cada 30 segundos"""
            try:
                # Obtener datos del bot
                dashboard_data = self.data_provider.get_dashboard_data()
                bot_status = self.data_provider.get_bot_status()
                
                logger.debug(f"Dashboard data updated - interval {n}")
                return dashboard_data, bot_status
                
            except Exception as e:
                logger.error(f"Error actualizando datos del dashboard: {e}")
                return {}, {}
        
        # Registrar callbacks específicos de cada página
        from .callbacks import DashboardCallbacks
        callbacks_handler = DashboardCallbacks(self.app, self.data_provider, self.chart_components)
        callbacks_handler.register_all_callbacks()
    
    def run(self):
        """Ejecuta el servidor del dashboard"""
        try:
            logger.info(f"🚀 Iniciando dashboard en http://{self.host}:{self.port}")
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                dev_tools_hot_reload=False,
                threaded=True
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
            raise
    
    def stop(self):
        """Detiene el servidor del dashboard"""
        logger.info("Dashboard detenido")

# Instancia global del dashboard
dashboard = TradingDashboard()

def start_dashboard(host='127.0.0.1', port=8050, debug=False):
    """Función para iniciar el dashboard"""
    try:
        global dashboard
        dashboard = TradingDashboard(host=host, port=port, debug=debug)
        dashboard.run()
        
    except KeyboardInterrupt:
        logger.info("Dashboard interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error crítico en dashboard: {e}")
        raise

def start_dashboard_thread(host='127.0.0.1', port=8050, debug=False):
    """Inicia el dashboard en un hilo separado"""
    dashboard_thread = threading.Thread(
        target=start_dashboard,
        args=(host, port, debug),
        daemon=True
    )
    dashboard_thread.start()
    logger.info(f"Dashboard thread iniciado en {host}:{port}")
    return dashboard_thread

if __name__ == '__main__':
    # Ejecutar dashboard standalone
    start_dashboard(debug=True)