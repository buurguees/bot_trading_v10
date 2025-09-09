# Ruta: core/monitoring/core/dashboard_app.py
"""
monitoring/core/dashboard_app.py
Aplicación Principal del Dashboard - Trading Bot v10

Esta clase maneja la aplicación principal de Dash, el routing de páginas,
la configuración de temas y la integración de todos los componentes
del sistema de monitoreo.
"""

import logging
import webbrowser
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Importaciones de páginas
from monitoring.pages.home_page import HomePage
from monitoring.pages.charts_page import ChartsPage
from monitoring.pages.cycles_page import CyclesPage
from monitoring.pages.live_trading_page import LiveTradingPage
from monitoring.pages.performance_page import PerformancePage
from monitoring.pages.risk_analysis_page import RiskAnalysisPage
from monitoring.pages.model_status_page import ModelStatusPage
from monitoring.pages.settings_page import SettingsPage

# Importaciones de estilos y configuración
from monitoring.styles.themes import get_theme, AVAILABLE_THEMES
from monitoring.config.dashboard_config import DASHBOARD_CONFIG

logger = logging.getLogger(__name__)

class DashboardApp:
    """
    Aplicación principal del dashboard del Trading Bot v10
    
    Gestiona la aplicación Dash, el routing, temas, y la integración
    de todos los componentes del sistema de monitoreo.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None, performance_tracker=None, **kwargs):
        """
        Inicializa la aplicación del dashboard
        
        Args:
            data_provider: Proveedor de datos centralizado
            real_time_manager: Gestor de datos en tiempo real
            performance_tracker: Tracker de rendimiento
            **kwargs: Argumentos adicionales para Dash
        """
        self.data_provider = data_provider
        self.real_time_manager = real_time_manager
        self.performance_tracker = performance_tracker
        
        # Configuración de la aplicación Dash
        external_stylesheets = [
            dbc.themes.BOOTSTRAP,
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap'
        ]
        
        # Crear aplicación Dash
        self.app = Dash(
            __name__,
            external_stylesheets=external_stylesheets,
            suppress_callback_exceptions=True,
            update_title=None,
            **kwargs
        )
        
        # Configurar título y metadatos
        self.app.title = "Trading Bot v10 - Dashboard"
        self.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="description" content="Dashboard del Trading Bot v10 - Monitoreo en tiempo real">
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
        
        # Inicializar páginas
        self._initialize_pages()
        
        # Configurar layout y callbacks
        self._setup_layout()
        self._register_callbacks()
        
        # Estado de la aplicación
        self.current_theme = DASHBOARD_CONFIG.get('default_theme', 'dark')
        self.is_running = False
        
        logger.info("DashboardApp inicializada correctamente")
    
    def _initialize_pages(self):
        """Inicializa todas las páginas del dashboard"""
        try:
            self.pages = {
                'home': HomePage(self.data_provider, self.performance_tracker),
                'charts': ChartsPage(self.data_provider),
                'cycles': CyclesPage(self.data_provider, self.performance_tracker),
                'live_trading': LiveTradingPage(self.data_provider, self.real_time_manager),
                'performance': PerformancePage(self.data_provider, self.performance_tracker),
                'risk_analysis': RiskAnalysisPage(self.data_provider),
                'model_status': ModelStatusPage(self.data_provider),
                'settings': SettingsPage()
            }
            logger.info("Páginas del dashboard inicializadas")
            
        except Exception as e:
            logger.error(f"Error al inicializar páginas: {e}")
            # Crear páginas básicas como fallback
            self.pages = {
                'home': HomePage(),
                'charts': ChartsPage(),
                'cycles': CyclesPage()
            }
    
    def _setup_layout(self):
        """Configura el layout principal de la aplicación"""
        
        # Header con navegación
        header = self._create_header()
        
        # Sidebar con navegación
        sidebar = self._create_sidebar()
        
        # Contenido principal
        main_content = html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content', className='page-content')
        ], className='main-content')
        
        # Layout principal
        self.app.layout = dbc.Container([
            # Stores para datos globales
            dcc.Store(id='global-data-store'),
            dcc.Store(id='theme-store', data=self.current_theme),
            dcc.Store(id='user-preferences-store'),
            
            # Intervalos para actualizaciones
            dcc.Interval(
                id='global-update-interval',
                interval=DASHBOARD_CONFIG.get('update_interval', 5000),
                n_intervals=0
            ),
            dcc.Interval(
                id='fast-update-interval', 
                interval=1000,  # 1 segundo para datos críticos
                n_intervals=0
            ),
            
            # Layout principal
            html.Div([
                header,
                html.Div([
                    sidebar,
                    main_content
                ], className='dashboard-body')
            ], className='dashboard-container', id='dashboard-container')
            
        ], fluid=True, className='dashboard-wrapper')
    
    def _create_header(self):
        """Crea el header con navegación principal"""
        return dbc.Navbar([
            dbc.Container([
                # Logo y título
                dbc.NavbarBrand([
                    html.I(className="fas fa-robot me-2"),
                    "Trading Bot v10"
                ], className="navbar-brand"),
                
                # Controles del header
                dbc.Nav([
                    # Selector de tema
                    dbc.NavItem([
                        dbc.Button([
                            html.I(className="fas fa-moon", id="theme-icon")
                        ], id="theme-toggle", color="link", className="nav-button")
                    ]),
                    
                    # Estado de conexión
                    dbc.NavItem([
                        dbc.Badge([
                            html.I(className="fas fa-circle me-1"),
                            html.Span("Conectado", id="connection-status")
                        ], id="connection-badge", color="success", className="me-2")
                    ]),
                    
                    # Última actualización
                    dbc.NavItem([
                        html.Small(id="last-update", className="text-muted")
                    ])
                    
                ], navbar=True, className="ms-auto")
                
            ], fluid=True)
        ], color="primary", dark=True, className="dashboard-header")
    
    def _create_sidebar(self):
        """Crea el sidebar con navegación de páginas"""
        nav_items = [
            {
                'id': 'home',
                'label': 'Dashboard',
                'icon': 'fas fa-home',
                'href': '/'
            },
            {
                'id': 'charts', 
                'label': 'Gráficos',
                'icon': 'fas fa-chart-line',
                'href': '/charts'
            },
            {
                'id': 'cycles',
                'label': 'Ciclos',
                'icon': 'fas fa-sync-alt',
                'href': '/cycles'
            },
            {
                'id': 'live_trading',
                'label': 'Trading Live',
                'icon': 'fas fa-broadcast-tower',
                'href': '/live-trading'
            },
            {
                'id': 'performance',
                'label': 'Rendimiento', 
                'icon': 'fas fa-chart-bar',
                'href': '/performance'
            },
            {
                'id': 'risk_analysis',
                'label': 'Análisis Riesgo',
                'icon': 'fas fa-shield-alt',
                'href': '/risk-analysis'
            },
            {
                'id': 'model_status',
                'label': 'Estado Modelo',
                'icon': 'fas fa-brain',
                'href': '/model-status'
            },
            {
                'id': 'settings',
                'label': 'Configuración',
                'icon': 'fas fa-cog',
                'href': '/settings'
            }
        ]
        
        nav_links = []
        for item in nav_items:
            nav_links.append(
                dbc.NavLink([
                    html.I(className=f"{item['icon']} me-2"),
                    item['label']
                ], href=item['href'], id=f"nav-{item['id']}", className="nav-link")
            )
        
        return html.Div([
            html.Div([
                html.H6("Navegación", className="sidebar-title"),
                dbc.Nav(nav_links, vertical=True, pills=True)
            ], className="sidebar-content")
        ], className="sidebar")
    
    def _register_callbacks(self):
        """Registra todos los callbacks de la aplicación"""
        
        # Callback principal de routing
        @self.app.callback(
            Output('page-content', 'children'),
            [Input('url', 'pathname')]
        )
        def display_page(pathname):
            """Enruta a la página correspondiente según la URL"""
            try:
                if pathname == '/' or pathname == '/home':
                    return self.pages['home'].get_layout()
                elif pathname == '/charts':
                    return self.pages['charts'].get_layout()
                elif pathname == '/cycles':
                    return self.pages['cycles'].get_layout()
                elif pathname == '/live-trading':
                    return self.pages['live_trading'].get_layout()
                elif pathname == '/performance':
                    return self.pages['performance'].get_layout()
                elif pathname == '/risk-analysis':
                    return self.pages['risk_analysis'].get_layout()
                elif pathname == '/model-status':
                    return self.pages['model_status'].get_layout()
                elif pathname == '/settings':
                    return self.pages['settings'].get_layout()
                else:
                    # Página 404
                    return self._create_404_page()
                    
            except Exception as e:
                logger.error(f"Error al mostrar página {pathname}: {e}")
                return self._create_error_page(str(e))
        
        # Callback para toggle de tema
        @self.app.callback(
            [Output('theme-store', 'data'),
             Output('theme-icon', 'className'),
             Output('dashboard-container', 'className')],
            [Input('theme-toggle', 'n_clicks')],
            [State('theme-store', 'data')]
        )
        def toggle_theme(n_clicks, current_theme):
            """Alterna entre tema claro y oscuro"""
            if n_clicks:
                new_theme = 'light' if current_theme == 'dark' else 'dark'
                icon_class = "fas fa-sun" if new_theme == 'dark' else "fas fa-moon"
                container_class = f"dashboard-container theme-{new_theme}"
                return new_theme, icon_class, container_class
            
            icon_class = "fas fa-moon" if current_theme == 'dark' else "fas fa-sun"
            container_class = f"dashboard-container theme-{current_theme}"
            return current_theme, icon_class, container_class
        
        # Callback para estado de conexión
        @self.app.callback(
            [Output('connection-badge', 'color'),
             Output('connection-badge', 'children'),
             Output('last-update', 'children')],
            [Input('global-update-interval', 'n_intervals')]
        )
        def update_connection_status(n_intervals):
            """Actualiza el estado de conexión y última actualización"""
            try:
                # Verificar estado de conexiones
                is_connected = True
                if self.data_provider:
                    is_connected = self.data_provider.is_connected()
                
                if is_connected:
                    badge_color = "success"
                    badge_content = [
                        html.I(className="fas fa-circle me-1"),
                        "Conectado"
                    ]
                else:
                    badge_color = "danger"
                    badge_content = [
                        html.I(className="fas fa-exclamation-circle me-1"),
                        "Desconectado"
                    ]
                
                # Última actualización
                last_update = f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"
                
                return badge_color, badge_content, last_update
                
            except Exception as e:
                logger.error(f"Error al actualizar estado de conexión: {e}")
                return "warning", [html.I(className="fas fa-exclamation-triangle me-1"), "Error"], "Error de conexión"
        
        # Registrar callbacks de páginas individuales
        self._register_page_callbacks()
        
        logger.info("Callbacks del dashboard registrados")
    
    def _register_page_callbacks(self):
        """Registra callbacks específicos de cada página"""
        try:
            for page_name, page_instance in self.pages.items():
                if hasattr(page_instance, 'register_callbacks'):
                    page_instance.register_callbacks(self.app)
                    logger.debug(f"Callbacks registrados para página: {page_name}")
        except Exception as e:
            logger.error(f"Error al registrar callbacks de páginas: {e}")
    
    def _create_404_page(self):
        """Crea una página 404 personalizada"""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle fa-5x mb-4 text-warning"),
                        html.H1("404 - Página no encontrada", className="mb-3"),
                        html.P("La página que buscas no existe.", className="mb-4"),
                        dbc.Button("Volver al Dashboard", href="/", color="primary")
                    ], className="text-center py-5")
                ], width=12)
            ])
        ], className="py-5")
    
    def _create_error_page(self, error_message):
        """Crea una página de error personalizada"""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-bug fa-5x mb-4 text-danger"),
                        html.H1("Error del Sistema", className="mb-3"),
                        html.P(f"Ha ocurrido un error: {error_message}", className="mb-4"),
                        dbc.Button("Recargar Página", id="reload-button", color="primary", className="me-2"),
                        dbc.Button("Volver al Dashboard", href="/", color="secondary")
                    ], className="text-center py-5")
                ], width=12)
            ])
        ], className="py-5")
    
    def run_server(self, host='127.0.0.1', port=8050, debug=False, **kwargs):
        """
        Inicia el servidor del dashboard
        
        Args:
            host (str): Host del servidor
            port (int): Puerto del servidor
            debug (bool): Modo debug
            **kwargs: Argumentos adicionales para el servidor
        """
        try:
            self.is_running = True
            
            # Configurar logging según modo debug
            if debug:
                logging.getLogger('werkzeug').setLevel(logging.INFO)
            else:
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
            
            logger.info(f"Iniciando dashboard en http://{host}:{port}")
            
            # Abrir navegador automáticamente si no está en modo debug
            if not debug and DASHBOARD_CONFIG.get('auto_open_browser', True):
                def open_browser():
                    time.sleep(1.5)  # Esperar a que el servidor esté listo
                    webbrowser.open(f'http://{host}:{port}')
                
                threading.Thread(target=open_browser, daemon=True).start()
            
            # Iniciar servidor
            self.app.run_server(
                host=host,
                port=port,
                debug=debug,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Error al iniciar servidor: {e}")
            raise
        finally:
            self.is_running = False
    
    def stop_server(self):
        """Detiene el servidor del dashboard"""
        # Nota: Dash no tiene un método directo para parar el servidor
        # Esto se manejará a nivel del proceso principal
        self.is_running = False
        logger.info("Solicitud de parada del servidor enviada")
    
    def get_app(self):
        """Retorna la instancia de la aplicación Dash"""
        return self.app
    
    def get_status(self):
        """Obtiene el estado actual de la aplicación"""
        return {
            'is_running': self.is_running,
            'current_theme': self.current_theme,
            'pages_loaded': len(self.pages),
            'data_provider_connected': self.data_provider.is_connected() if self.data_provider else False,
            'real_time_active': self.real_time_manager.is_running() if self.real_time_manager else False
        }