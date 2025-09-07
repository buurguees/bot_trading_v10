"""
monitoring/dashboard_reorganized.py
Dashboard principal reorganizado con nueva estructura
"""

from dash import Dash, html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
from datetime import datetime
import logging
import webbrowser
import threading
import time

# Importar módulos reorganizados
from monitoring.core.dashboard import start_dashboard as core_start_dashboard
from monitoring.core.data_provider import DataProvider
from monitoring.core.cycle_tracker import cycle_tracker

# Importar páginas
from monitoring.pages.home import HomePage
from monitoring.pages.trading import TradingPage
from monitoring.pages.analytics import AnalyticsPage
from monitoring.pages.settings import SettingsPage

# Importar callbacks
from monitoring.callbacks.home_callbacks import register_home_callbacks
from monitoring.callbacks.trading_callbacks import register_trading_callbacks
from monitoring.callbacks.chart_callbacks import register_chart_callbacks

logger = logging.getLogger(__name__)

class ReorganizedDashboard:
    """Dashboard principal reorganizado"""
    
    def __init__(self):
        self.app = Dash(__name__, 
                       external_stylesheets=[
                           'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
                           'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
                       ])
        
        self.data_provider = DataProvider()
        self.home_page = HomePage()
        self.trading_page = TradingPage()
        self.analytics_page = AnalyticsPage()
        self.settings_page = SettingsPage()
        
        self.setup_layout()
        self.register_callbacks()
        
        logger.info("Dashboard reorganizado inicializado")
    
    def setup_layout(self):
        """Configura el layout principal del dashboard"""
        
        # Tema de colores
        theme_colors = {
            'primary': '#1a1a1a',
            'secondary': '#2d2d2d',
            'accent': '#00ff88',
            'danger': '#ff4444',
            'warning': '#ffaa00',
            'info': '#4488ff',
            'success': '#28a745',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'border_color': '#444444'
        }
        
        # Header
        header = html.Div([
            html.Div([
                # Logo y título
                html.Div([
                    html.I(className="fas fa-robot", style={'color': theme_colors['accent'], 'marginRight': '10px'}),
                    html.H2("Trading Bot v10", style={'margin': '0', 'color': theme_colors['text_primary']})
                ], style={'display': 'flex', 'alignItems': 'center'}),
                
                # Navegación
                html.Div([
                    dcc.Link([
                        html.I(className="fas fa-home", style={'marginRight': '5px'}),
                        "Home"
                    ], href="/", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-chart-line", style={'marginRight': '5px'}),
                        "Trading"
                    ], href="/trading", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-analytics", style={'marginRight': '5px'}),
                        "Analytics"
                    ], href="/analytics", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-cog", style={'marginRight': '5px'}),
                        "Settings"
                    ], href="/settings", className="nav-link")
                ], className="nav-links")
                
            ], className="header-content")
        ], className="header")
        
        # Contenido principal
        content = html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ], className="main-content")
        
        # Layout principal
        self.app.layout = html.Div([
            header,
            content,
            # Store para datos del dashboard
            dcc.Store(id='dashboard-data'),
            # Interval para actualización automática
            dcc.Interval(
                id='dashboard-interval',
                interval=5000,  # 5 segundos
                n_intervals=0
            )
        ], className="dashboard-container")
    
    def register_callbacks(self):
        """Registra todos los callbacks del dashboard"""
        
        # Callback para navegación de páginas
        @self.app.callback(
            Output('page-content', 'children'),
            [Input('url', 'pathname')]
        )
        def display_page(pathname):
            """Muestra la página correspondiente según la URL"""
            if pathname == '/':
                return self.home_page.create_home_page()
            elif pathname == '/trading':
                return self.trading_page.create_trading_page()
            elif pathname == '/analytics':
                return self.analytics_page.create_analytics_page()
            elif pathname == '/settings':
                return self.settings_page.create_settings_page()
            else:
                return self.home_page.create_home_page()
        
        # Callback para datos del dashboard
        @self.app.callback(
            Output('dashboard-data', 'data'),
            [Input('dashboard-interval', 'n_intervals')]
        )
        def update_dashboard_data(n_intervals):
            """Actualiza los datos del dashboard"""
            try:
                return self.data_provider.get_dashboard_data()
            except Exception as e:
                logger.error(f"Error actualizando datos del dashboard: {e}")
                return {}
        
        # Registrar callbacks específicos
        register_home_callbacks(self.app, self.data_provider, None)
        register_trading_callbacks(self.app, self.data_provider, None)
        register_chart_callbacks(self.app, self.data_provider, None)
        
        logger.info("Callbacks registrados exitosamente")
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """Ejecuta el dashboard"""
        try:
            logger.info(f"Iniciando dashboard reorganizado en http://{host}:{port}")
            
            # Función para abrir navegador
            def open_browser():
                time.sleep(2)
                webbrowser.open(f'http://{host}:{port}')
            
            # Abrir navegador en hilo separado
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Ejecutar dashboard
            self.app.run_server(host=host, port=port, debug=debug)
            
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
            raise

def start_dashboard_reorganized(host='127.0.0.1', port=8050, debug=False):
    """Función principal para iniciar el dashboard reorganizado"""
    try:
        dashboard = ReorganizedDashboard()
        dashboard.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Error iniciando dashboard reorganizado: {e}")
        raise

if __name__ == "__main__":
    start_dashboard_reorganized()
