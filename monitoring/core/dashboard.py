r"""
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
from monitoring.pages.home import HomePage
from monitoring.components.chart_components import ChartComponents
from monitoring.callbacks.home_callbacks import register_callbacks

logger = logging.getLogger(__name__)

class TradingDashboard:
    """Dashboard principal del Trading Bot v10"""
    
    def __init__(self, host='127.0.0.1', port=8050, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Inicializar componentes
        self.data_provider = DashboardDataProvider()
        self.home_page = HomePage()
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
            self._create_header(),
            
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
                return self.home_page.create_home_page()
            elif pathname == '/trading':
                from monitoring.pages.trading import create_trading_page
                return create_trading_page()
            elif pathname == '/performance':
                from monitoring.pages.analytics import create_analytics_page
                return create_analytics_page()
            elif pathname == '/settings':
                from monitoring.pages.settings import create_settings_page
                return create_settings_page()
            elif pathname == '/alerts':
                return self._create_alerts_page()
            elif pathname == '/chat':
                return self._create_chat_page()
            else:
                return self._create_404_page()
        
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
            logger.info(f"Iniciando dashboard en http://{self.host}:{self.port}")
            
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

    def _create_header(self):
        """Crea el header del dashboard"""
        return html.Div([
            html.Div([
                html.H1("🤖 Trading Bot v10", className="dashboard-title"),
                html.Div([
                    html.Span("📊 Dashboard", className="nav-item", id="nav-home"),
                    html.Span("💹 Trading", className="nav-item", id="nav-trading"),
                    html.Span("📈 Analytics", className="nav-item", id="nav-performance"),
                    html.Span("⚙️ Settings", className="nav-item", id="nav-settings"),
                ], className="nav-menu")
            ], className="dashboard-header")
        ], className="header-container")

    def _create_alerts_page(self):
        """Crea la página de alertas"""
        return html.Div([
            html.H2("🚨 Alertas del Sistema"),
            html.P("Página de alertas en desarrollo...")
        ], className="page-content")

    def _create_chat_page(self):
        """Crea la página de chat"""
        return html.Div([
            html.H2("💬 Chat con el Bot"),
            html.P("Página de chat en desarrollo...")
        ], className="page-content")

    def _create_404_page(self):
        """Crea la página 404"""
        return html.Div([
            html.H2("404 - Página no encontrada"),
            html.P("La página que buscas no existe."),
            html.A("Volver al inicio", href="/", className="button-primary")
        ], className="page-content")

# Instancia global del dashboard
dashboard = TradingDashboard()

def start_dashboard(host='127.0.0.1', port=8050, debug=False):
    """Función para iniciar el dashboard"""
    try:
        global dashboard
        dashboard = TradingDashboard(host=host, port=port, debug=debug)
        
        # Abrir navegador automáticamente
        import webbrowser
        import time
        
        def open_browser():
            time.sleep(2)  # Esperar a que el servidor se inicie
            webbrowser.open(f'http://{host}:{port}')
        
        # Iniciar hilo para abrir navegador
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
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