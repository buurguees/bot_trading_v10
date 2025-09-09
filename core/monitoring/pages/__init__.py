"""
monitoring/pages/__init__.py
Páginas del Dashboard - Trading Bot v10

Este módulo contiene todas las páginas del dashboard web del sistema de monitoreo.
Cada página es una clase independiente que maneja su propio layout, callbacks
y funcionalidades específicas.

Páginas disponibles:
- HomePage: Dashboard principal con métricas por símbolo
- ChartsPage: Gráficos interactivos e históricos
- CyclesPage: Análisis detallado de ciclos de trading
- LiveTradingPage: Monitoreo de trading en tiempo real
- PerformancePage: Análisis avanzado de rendimiento
- RiskAnalysisPage: Gestión y análisis de riesgo
- ModelStatusPage: Estado del modelo de IA
- SettingsPage: Configuración del sistema
"""

__version__ = "10.0.0"
__description__ = "Páginas del Dashboard de Monitoreo"

# Importaciones de todas las páginas
from monitoring.pages.home_page import HomePage
from monitoring.pages.charts_page import ChartsPage
from monitoring.pages.cycles_page import CyclesPage
from monitoring.pages.live_trading_page import LiveTradingPage
from monitoring.pages.performance_page import PerformancePage
from monitoring.pages.risk_analysis_page import RiskAnalysisPage
from monitoring.pages.model_status_page import ModelStatusPage
from monitoring.pages.settings_page import SettingsPage

# Clase base para todas las páginas
from monitoring.pages.base_page import BasePage

import logging
from typing import Dict, List, Any, Type, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Registro de todas las páginas disponibles
AVAILABLE_PAGES = {
    'home': {
        'class': HomePage,
        'title': 'Dashboard Principal',
        'description': 'Vista general con métricas por símbolo',
        'icon': 'fas fa-home',
        'url': '/',
        'order': 1,
        'category': 'principal'
    },
    'charts': {
        'class': ChartsPage,
        'title': 'Gráficos',
        'description': 'Gráficos interactivos e históricos',
        'icon': 'fas fa-chart-line',
        'url': '/charts',
        'order': 2,
        'category': 'análisis'
    },
    'cycles': {
        'class': CyclesPage,
        'title': 'Ciclos',
        'description': 'Análisis de ciclos de trading',
        'icon': 'fas fa-sync-alt',
        'url': '/cycles',
        'order': 3,
        'category': 'análisis'
    },
    'live_trading': {
        'class': LiveTradingPage,
        'title': 'Trading Live',
        'description': 'Monitoreo en tiempo real',
        'icon': 'fas fa-broadcast-tower',
        'url': '/live-trading',
        'order': 4,
        'category': 'trading'
    },
    'performance': {
        'class': PerformancePage,
        'title': 'Rendimiento',
        'description': 'Análisis de performance avanzado',
        'icon': 'fas fa-chart-bar',
        'url': '/performance',
        'order': 5,
        'category': 'análisis'
    },
    'risk_analysis': {
        'class': RiskAnalysisPage,
        'title': 'Análisis de Riesgo',
        'description': 'Gestión y análisis de riesgo',
        'icon': 'fas fa-shield-alt',
        'url': '/risk-analysis',
        'order': 6,
        'category': 'riesgo'
    },
    'model_status': {
        'class': ModelStatusPage,
        'title': 'Estado del Modelo',
        'description': 'Estado y rendimiento del modelo IA',
        'icon': 'fas fa-brain',
        'url': '/model-status',
        'order': 7,
        'category': 'sistema'
    },
    'settings': {
        'class': SettingsPage,
        'title': 'Configuración',
        'description': 'Configuración del sistema',
        'icon': 'fas fa-cog',
        'url': '/settings',
        'order': 8,
        'category': 'sistema'
    }
}

class PageManager:
    """
    Gestor centralizado de páginas del dashboard
    
    Maneja la creación, inicialización y gestión de todas las páginas
    del sistema de monitoreo.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None, performance_tracker=None):
        """
        Inicializa el gestor de páginas
        
        Args:
            data_provider: Proveedor de datos centralizado
            real_time_manager: Gestor de datos en tiempo real
            performance_tracker: Tracker de rendimiento
        """
        self.data_provider = data_provider
        self.real_time_manager = real_time_manager
        self.performance_tracker = performance_tracker
        
        # Instancias de páginas inicializadas
        self.pages = {}
        
        # Estado del gestor
        self._initialized = False
        
        logger.info("PageManager inicializado")
    
    def initialize_all_pages(self) -> Dict[str, Any]:
        """
        Inicializa todas las páginas disponibles
        
        Returns:
            Dict[str, Any]: Diccionario con instancias de páginas
        """
        try:
            for page_id, page_config in AVAILABLE_PAGES.items():
                page_class = page_config['class']
                
                # Inicializar página con los proveedores apropiados
                if page_id in ['home', 'cycles', 'performance']:
                    # Páginas que necesitan data_provider y performance_tracker
                    page_instance = page_class(
                        data_provider=self.data_provider,
                        performance_tracker=self.performance_tracker
                    )
                elif page_id in ['live_trading']:
                    # Páginas que necesitan real_time_manager
                    page_instance = page_class(
                        data_provider=self.data_provider,
                        real_time_manager=self.real_time_manager
                    )
                elif page_id in ['charts', 'risk_analysis', 'model_status']:
                    # Páginas que solo necesitan data_provider
                    page_instance = page_class(
                        data_provider=self.data_provider
                    )
                else:
                    # Páginas independientes (settings)
                    page_instance = page_class()
                
                self.pages[page_id] = page_instance
                logger.debug(f"Página {page_id} inicializada correctamente")
            
            self._initialized = True
            logger.info(f"Todas las páginas inicializadas: {list(self.pages.keys())}")
            
            return self.pages
            
        except Exception as e:
            logger.error(f"Error al inicializar páginas: {e}")
            raise
    
    def get_page(self, page_id: str) -> Optional[Any]:
        """
        Obtiene una instancia de página específica
        
        Args:
            page_id (str): ID de la página
            
        Returns:
            Optional[Any]: Instancia de la página o None si no existe
        """
        if not self._initialized:
            self.initialize_all_pages()
        
        return self.pages.get(page_id)
    
    def get_all_pages(self) -> Dict[str, Any]:
        """
        Obtiene todas las instancias de páginas
        
        Returns:
            Dict[str, Any]: Diccionario con todas las páginas
        """
        if not self._initialized:
            self.initialize_all_pages()
        
        return self.pages.copy()
    
    def get_page_config(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración de una página
        
        Args:
            page_id (str): ID de la página
            
        Returns:
            Optional[Dict[str, Any]]: Configuración de la página
        """
        return AVAILABLE_PAGES.get(page_id)
    
    def get_navigation_menu(self) -> List[Dict[str, Any]]:
        """
        Genera el menú de navegación organizado por categorías
        
        Returns:
            List[Dict[str, Any]]: Lista de elementos del menú
        """
        menu_items = []
        categories = {}
        
        # Agrupar por categorías
        for page_id, config in AVAILABLE_PAGES.items():
            category = config['category']
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                'id': page_id,
                'title': config['title'],
                'icon': config['icon'],
                'url': config['url'],
                'order': config['order'],
                'description': config['description']
            })
        
        # Ordenar elementos dentro de cada categoría
        for category, items in categories.items():
            items.sort(key=lambda x: x['order'])
            
            menu_items.append({
                'category': category.title(),
                'items': items
            })
        
        return menu_items
    
    def register_page_callbacks(self, app) -> None:
        """
        Registra callbacks de todas las páginas en la aplicación Dash
        
        Args:
            app: Instancia de la aplicación Dash
        """
        try:
            if not self._initialized:
                self.initialize_all_pages()
            
            for page_id, page_instance in self.pages.items():
                if hasattr(page_instance, 'register_callbacks'):
                    try:
                        page_instance.register_callbacks(app)
                        logger.debug(f"Callbacks registrados para página: {page_id}")
                    except Exception as e:
                        logger.error(f"Error al registrar callbacks para {page_id}: {e}")
                else:
                    logger.debug(f"Página {page_id} no tiene callbacks para registrar")
            
            logger.info("Callbacks de todas las páginas registrados")
            
        except Exception as e:
            logger.error(f"Error al registrar callbacks de páginas: {e}")
            raise
    
    def get_page_layout(self, page_id: str) -> Any:
        """
        Obtiene el layout de una página específica
        
        Args:
            page_id (str): ID de la página
            
        Returns:
            Any: Layout de la página o None si no existe
        """
        page_instance = self.get_page(page_id)
        
        if page_instance and hasattr(page_instance, 'get_layout'):
            try:
                return page_instance.get_layout()
            except Exception as e:
                logger.error(f"Error al obtener layout de {page_id}: {e}")
                return self._create_error_layout(f"Error al cargar página {page_id}")
        
        return self._create_404_layout(page_id)
    
    def _create_error_layout(self, error_message: str) -> Any:
        """Crea un layout de error"""
        try:
            import dash_bootstrap_components as dbc
            from dash import html
            
            return dbc.Container([
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    html.Strong("Error: "),
                    error_message
                ], color="danger", className="mt-4"),
                
                dbc.Button(
                    "Volver al Dashboard",
                    href="/",
                    color="primary",
                    className="mt-3"
                )
            ])
            
        except ImportError:
            # Fallback si dash_bootstrap_components no está disponible
            from dash import html
            return html.Div([
                html.H3("Error"),
                html.P(error_message),
                html.A("Volver al Dashboard", href="/")
            ])
    
    def _create_404_layout(self, page_id: str) -> Any:
        """Crea un layout 404"""
        try:
            import dash_bootstrap_components as dbc
            from dash import html
            
            return dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-search fa-5x mb-4 text-muted"),
                            html.H1("404 - Página no encontrada", className="mb-3"),
                            html.P(f"La página '{page_id}' no existe o no está disponible.", 
                                  className="mb-4 text-muted"),
                            dbc.Button("Volver al Dashboard", href="/", color="primary")
                        ], className="text-center py-5")
                    ], width=12)
                ])
            ], className="py-5")
            
        except ImportError:
            from dash import html
            return html.Div([
                html.H3("404 - Página no encontrada"),
                html.P(f"La página '{page_id}' no existe."),
                html.A("Volver al Dashboard", href="/")
            ])
    
    def get_page_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de todas las páginas
        
        Returns:
            Dict[str, Any]: Estado de las páginas
        """
        status = {
            'initialized': self._initialized,
            'total_pages': len(AVAILABLE_PAGES),
            'loaded_pages': len(self.pages),
            'pages_status': {}
        }
        
        for page_id, page_config in AVAILABLE_PAGES.items():
            page_instance = self.pages.get(page_id)
            
            status['pages_status'][page_id] = {
                'loaded': page_instance is not None,
                'title': page_config['title'],
                'category': page_config['category'],
                'has_callbacks': (
                    hasattr(page_instance, 'register_callbacks') 
                    if page_instance else False
                ),
                'has_layout': (
                    hasattr(page_instance, 'get_layout') 
                    if page_instance else False
                )
            }
        
        return status

# Funciones de conveniencia
def create_page_manager(data_provider=None, real_time_manager=None, performance_tracker=None) -> PageManager:
    """
    Crea una instancia del gestor de páginas
    
    Args:
        data_provider: Proveedor de datos
        real_time_manager: Gestor de tiempo real
        performance_tracker: Tracker de rendimiento
        
    Returns:
        PageManager: Instancia del gestor de páginas
    """
    return PageManager(data_provider, real_time_manager, performance_tracker)

def get_available_pages() -> Dict[str, Dict[str, Any]]:
    """
    Obtiene la configuración de todas las páginas disponibles
    
    Returns:
        Dict[str, Dict[str, Any]]: Configuración de páginas
    """
    return AVAILABLE_PAGES.copy()

def get_page_categories() -> List[str]:
    """
    Obtiene todas las categorías de páginas disponibles
    
    Returns:
        List[str]: Lista de categorías
    """
    categories = set()
    for config in AVAILABLE_PAGES.values():
        categories.add(config['category'])
    
    return sorted(list(categories))

def validate_page_implementations():
    """
    Valida que todas las páginas registradas tengan las implementaciones necesarias
    
    Raises:
        ImportError: Si alguna página no puede ser importada
        AttributeError: Si alguna página no tiene los métodos requeridos
    """
    errors = []
    
    for page_id, config in AVAILABLE_PAGES.items():
        try:
            page_class = config['class']
            
            # Verificar que la clase existe
            if not page_class:
                errors.append(f"Página {page_id}: Clase no definida")
                continue
            
            # Verificar herencia de BasePage (si está implementada)
            try:
                if not issubclass(page_class, BasePage):
                    logger.warning(f"Página {page_id}: No hereda de BasePage")
            except (NameError, TypeError):
                # BasePage podría no estar implementada aún
                pass
            
            # Verificar métodos esenciales
            required_methods = ['get_layout']
            for method in required_methods:
                if not hasattr(page_class, method):
                    errors.append(f"Página {page_id}: Método {method} no implementado")
                    
        except Exception as e:
            errors.append(f"Página {page_id}: Error al validar - {e}")
    
    if errors:
        error_msg = "Errores en implementaciones de páginas:\n" + "\n".join(errors)
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    logger.info("Todas las páginas validadas correctamente")

# Exportar elementos principales
__all__ = [
    'HomePage',
    'ChartsPage', 
    'CyclesPage',
    'LiveTradingPage',
    'PerformancePage',
    'RiskAnalysisPage',
    'ModelStatusPage',
    'SettingsPage',
    'BasePage',
    'PageManager',
    'AVAILABLE_PAGES',
    'create_page_manager',
    'get_available_pages',
    'get_page_categories',
    'validate_page_implementations',
    '__version__',
    '__description__'
]

# Verificar implementaciones al importar (solo en desarrollo)
try:
    validate_page_implementations()
except Exception as e:
    logger.warning(f"Validación de páginas falló: {e}")

logger.info(f"Módulo de páginas v{__version__} cargado con {len(AVAILABLE_PAGES)} páginas disponibles")