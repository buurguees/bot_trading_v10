# Ruta: core/monitoring/pages/base_page.py
"""
monitoring/pages/base_page.py
Clase Base para Páginas del Dashboard - Trading Bot v10

Esta clase abstracta define la interfaz común y funcionalidades base
para todas las páginas del sistema de monitoreo. Proporciona estructura,
utilidades comunes y patrones consistentes.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json

import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class BasePage(ABC):
    """
    Clase base abstracta para todas las páginas del dashboard
    
    Define la interfaz común y proporciona funcionalidades base
    que todas las páginas deben implementar o pueden usar.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None, performance_tracker=None):
        """
        Inicializa la página base
        
        Args:
            data_provider: Proveedor de datos centralizado
            real_time_manager: Gestor de datos en tiempo real
            performance_tracker: Tracker de rendimiento
        """
        self.data_provider = data_provider
        self.real_time_manager = real_time_manager
        self.performance_tracker = performance_tracker
        
        # Configuración de la página
        self.page_config = self._get_page_config()
        
        # Estado de la página
        self._initialized = False
        self._last_update = None
        self._update_count = 0
        
        # Cache de componentes
        self._component_cache = {}
        
        # Callbacks registrados
        self._registered_callbacks = []
        
        logger.debug(f"Página base inicializada: {self.__class__.__name__}")
    
    @abstractmethod
    def get_layout(self) -> Any:
        """
        Obtiene el layout principal de la página
        
        Returns:
            Any: Layout de Dash para la página
        """
        pass
    
    def _get_page_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración base de la página
        Puede ser sobrescrita por páginas específicas
        
        Returns:
            Dict[str, Any]: Configuración de la página
        """
        return {
            'title': self.__class__.__name__,
            'update_interval': 5000,  # 5 segundos
            'auto_refresh': True,
            'show_last_update': True,
            'enable_export': False,
            'theme_compatible': True,
            'loading_timeout': 10000,  # 10 segundos
            'error_retry_attempts': 3
        }
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra callbacks específicos de la página
        Puede ser sobrescrita por páginas que necesiten callbacks
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        # Implementación por defecto - no hay callbacks
        logger.debug(f"No hay callbacks para registrar en {self.__class__.__name__}")
    
    def create_page_header(self, title: str, subtitle: Optional[str] = None, 
                          show_refresh: bool = True, show_export: bool = False) -> dbc.Row:
        """
        Crea un header estándar para la página
        
        Args:
            title (str): Título principal
            subtitle (str, optional): Subtítulo descriptivo
            show_refresh (bool): Mostrar botón de refresh
            show_export (bool): Mostrar botón de exportar
            
        Returns:
            dbc.Row: Header de la página
        """
        header_content = [
            dbc.Col([
                html.H2(title, className="page-title mb-1"),
                html.P(subtitle, className="page-subtitle text-muted mb-0") if subtitle else None
            ], width="auto"),
            
            dbc.Col([
                dbc.ButtonGroup([
                    # Botón de refresh
                    dbc.Button([
                        html.I(className="fas fa-sync-alt me-1"),
                        "Actualizar"
                    ], 
                    id=f"{self._get_page_id()}-refresh-btn",
                    color="outline-primary", 
                    size="sm",
                    className="me-2") if show_refresh else None,
                    
                    # Botón de exportar
                    dbc.Button([
                        html.I(className="fas fa-download me-1"),
                        "Exportar"
                    ], 
                    id=f"{self._get_page_id()}-export-btn",
                    color="outline-secondary", 
                    size="sm") if show_export else None,
                    
                ], className="ms-auto")
            ], width="auto", className="d-flex align-items-center")
        ]
        
        # Filtrar elementos None
        header_content = [item for item in header_content if item is not None]
        
        return dbc.Row(header_content, className="page-header mb-4 align-items-center")
    
    def create_loading_component(self, component_id: str, children: Any, 
                               loading_type: str = "default") -> dcc.Loading:
        """
        Crea un componente de loading estándar
        
        Args:
            component_id (str): ID del componente
            children (Any): Contenido a mostrar
            loading_type (str): Tipo de loading
            
        Returns:
            dcc.Loading: Componente de loading
        """
        return dcc.Loading(
            id=f"{component_id}-loading",
            type=loading_type,
            children=children,
            color="#007bff",
            className="loading-component"
        )
    
    def create_error_alert(self, message: str, error_id: Optional[str] = None) -> dbc.Alert:
        """
        Crea una alerta de error estándar
        
        Args:
            message (str): Mensaje de error
            error_id (str, optional): ID del alert
            
        Returns:
            dbc.Alert: Alerta de error
        """
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            html.Strong("Error: "),
            message
        ], 
        color="danger", 
        id=error_id or f"{self._get_page_id()}-error-alert",
        is_open=True,
        dismissable=True,
        className="error-alert")
    
    def create_info_alert(self, message: str, alert_type: str = "info") -> dbc.Alert:
        """
        Crea una alerta informativa
        
        Args:
            message (str): Mensaje informativo
            alert_type (str): Tipo de alerta (info, success, warning)
            
        Returns:
            dbc.Alert: Alerta informativa
        """
        icons = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle'
        }
        
        return dbc.Alert([
            html.I(className=f"{icons.get(alert_type, 'fas fa-info-circle')} me-2"),
            message
        ], color=alert_type, className="info-alert")
    
    def create_metric_card(self, title: str, value: Any, subtitle: Optional[str] = None,
                          icon: Optional[str] = None, color: str = "primary",
                          trend: Optional[float] = None) -> dbc.Card:
        """
        Crea una tarjeta de métrica estándar
        
        Args:
            title (str): Título de la métrica
            value (Any): Valor principal
            subtitle (str, optional): Subtítulo o descripción
            icon (str, optional): Clase de icono FontAwesome
            color (str): Color del tema
            trend (float, optional): Tendencia (+/- para mostrar flecha)
            
        Returns:
            dbc.Card: Tarjeta de métrica
        """
        # Formatear valor
        formatted_value = self._format_metric_value(value)
        
        # Crear contenido del icono
        icon_content = None
        if icon:
            icon_content = html.Div([
                html.I(className=f"{icon} fa-2x")
            ], className=f"metric-icon text-{color}")
        
        # Crear indicador de tendencia
        trend_content = None
        if trend is not None:
            trend_icon = "fas fa-arrow-up" if trend > 0 else "fas fa-arrow-down"
            trend_color = "success" if trend > 0 else "danger"
            trend_content = html.Span([
                html.I(className=f"{trend_icon} me-1"),
                f"{abs(trend):.1f}%"
            ], className=f"text-{trend_color} small")
        
        card_body = dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6(title, className="metric-title text-muted mb-1"),
                    html.H3(formatted_value, className="metric-value mb-0"),
                    html.Div([
                        subtitle if subtitle else "",
                        trend_content
                    ], className="metric-subtitle d-flex justify-content-between align-items-center")
                ], width=8 if icon_content else 12),
                
                dbc.Col([
                    icon_content
                ], width=4, className="text-end") if icon_content else None
            ], className="align-items-center")
        ])
        
        return dbc.Card(card_body, className="metric-card h-100")
    
    def create_empty_state(self, title: str = "No hay datos disponibles",
                          message: str = "No se encontraron datos para mostrar",
                          icon: str = "fas fa-chart-line",
                          action_button: Optional[Dict[str, str]] = None) -> html.Div:
        """
        Crea un estado vacío estándar
        
        Args:
            title (str): Título del estado vacío
            message (str): Mensaje descriptivo
            icon (str): Icono a mostrar
            action_button (dict, optional): Botón de acción {'text': str, 'href': str}
            
        Returns:
            html.Div: Estado vacío
        """
        content = [
            html.I(className=f"{icon} fa-4x text-muted mb-3"),
            html.H4(title, className="text-muted mb-2"),
            html.P(message, className="text-muted mb-3")
        ]
        
        if action_button:
            content.append(
                dbc.Button(
                    action_button['text'],
                    href=action_button.get('href', '#'),
                    color="primary",
                    outline=True
                )
            )
        
        return html.Div(
            content,
            className="empty-state text-center py-5"
        )
    
    def create_data_table(self, data: List[Dict], columns: List[Dict],
                         table_id: Optional[str] = None, 
                         page_size: int = 10,
                         sortable: bool = True) -> html.Div:
        """
        Crea una tabla de datos estándar
        
        Args:
            data (List[Dict]): Datos de la tabla
            columns (List[Dict]): Configuración de columnas
            table_id (str, optional): ID de la tabla
            page_size (int): Tamaño de página
            sortable (bool): Permitir ordenamiento
            
        Returns:
            html.Div: Tabla de datos
        """
        try:
            from dash import dash_table
            
            return dash_table.DataTable(
                id=table_id or f"{self._get_page_id()}-data-table",
                data=data,
                columns=columns,
                page_size=page_size,
                sort_action='native' if sortable else 'none',
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'fontFamily': 'Inter, sans-serif'
                },
                style_header={
                    'backgroundColor': 'var(--bs-gray-100)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'var(--bs-gray-50)'
                    }
                ],
                className="data-table"
            )
            
        except ImportError:
            # Fallback si dash_table no está disponible
            return html.Div([
                html.P("Tabla de datos no disponible - dash_table no instalado"),
                html.Pre(json.dumps(data[:5], indent=2, default=str))
            ])
    
    def _format_metric_value(self, value: Any) -> str:
        """
        Formatea valores de métricas para mostrar
        
        Args:
            value (Any): Valor a formatear
            
        Returns:
            str: Valor formateado
        """
        if value is None:
            return "N/A"
        
        if isinstance(value, (int, float)):
            if abs(value) >= 1_000_000:
                return f"{value/1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                return f"{value/1_000:.1f}K"
            elif isinstance(value, float):
                return f"{value:.2f}"
            else:
                return f"{value:,}"
        
        return str(value)
    
    def _get_page_id(self) -> str:
        """
        Obtiene el ID único de la página
        
        Returns:
            str: ID de la página
        """
        return self.__class__.__name__.lower().replace('page', '')
    
    def get_page_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre la página
        
        Returns:
            Dict[str, Any]: Información de la página
        """
        return {
            'class_name': self.__class__.__name__,
            'page_id': self._get_page_id(),
            'initialized': self._initialized,
            'last_update': self._last_update,
            'update_count': self._update_count,
            'config': self.page_config,
            'has_data_provider': self.data_provider is not None,
            'has_real_time_manager': self.real_time_manager is not None,
            'has_performance_tracker': self.performance_tracker is not None,
            'registered_callbacks': len(self._registered_callbacks)
        }
    
    def update_page_stats(self):
        """Actualiza estadísticas de la página"""
        self._update_count += 1
        self._last_update = datetime.now()
    
    def validate_data_providers(self) -> Dict[str, bool]:
        """
        Valida que los proveedores de datos estén disponibles
        
        Returns:
            Dict[str, bool]: Estado de cada proveedor
        """
        return {
            'data_provider': (
                self.data_provider is not None and 
                self.data_provider.is_connected()
            ),
            'real_time_manager': (
                self.real_time_manager is not None and 
                self.real_time_manager.is_running()
            ),
            'performance_tracker': (
                self.performance_tracker is not None and 
                self.performance_tracker.is_active()
            )
        }
    
    def create_status_indicator(self, status: bool, 
                              true_text: str = "Conectado",
                              false_text: str = "Desconectado") -> dbc.Badge:
        """
        Crea un indicador de estado
        
        Args:
            status (bool): Estado a mostrar
            true_text (str): Texto para estado verdadero
            false_text (str): Texto para estado falso
            
        Returns:
            dbc.Badge: Indicador de estado
        """
        return dbc.Badge([
            html.I(className=f"fas fa-circle me-1"),
            true_text if status else false_text
        ], 
        color="success" if status else "danger",
        className="status-indicator")
    
    def create_time_selector(self, selector_id: str, 
                           default_value: str = "24h") -> dbc.ButtonGroup:
        """
        Crea un selector de tiempo estándar
        
        Args:
            selector_id (str): ID del selector
            default_value (str): Valor por defecto
            
        Returns:
            dbc.ButtonGroup: Selector de tiempo
        """
        time_options = [
            {'label': '1H', 'value': '1h'},
            {'label': '24H', 'value': '24h'},
            {'label': '7D', 'value': '7d'},
            {'label': '30D', 'value': '30d'},
            {'label': '90D', 'value': '90d'},
            {'label': 'Todo', 'value': 'all'}
        ]
        
        buttons = []
        for option in time_options:
            buttons.append(
                dbc.Button(
                    option['label'],
                    id=f"{selector_id}-{option['value']}",
                    color="primary" if option['value'] == default_value else "outline-primary",
                    size="sm",
                    value=option['value']
                )
            )
        
        return dbc.ButtonGroup(buttons, id=selector_id, className="time-selector")
    
    def create_symbol_selector(self, selector_id: str) -> dcc.Dropdown:
        """
        Crea un selector de símbolos
        
        Args:
            selector_id (str): ID del selector
            
        Returns:
            dcc.Dropdown: Selector de símbolos
        """
        options = []
        
        if self.data_provider:
            try:
                symbols = self.data_provider.get_configured_symbols()
                options = [{'label': symbol, 'value': symbol} for symbol in symbols]
            except Exception as e:
                logger.error(f"Error al obtener símbolos: {e}")
                options = [{'label': 'Error al cargar símbolos', 'value': None}]
        else:
            options = [
                {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                {'label': 'ADAUSDT', 'value': 'ADAUSDT'}
            ]
        
        return dcc.Dropdown(
            id=selector_id,
            options=options,
            value=options[0]['value'] if options else None,
            placeholder="Seleccionar símbolo",
            className="symbol-selector"
        )
    
    def log_page_action(self, action: str, details: Optional[Dict[str, Any]] = None):
        """
        Registra acciones de la página para auditoría
        
        Args:
            action (str): Acción realizada
            details (Dict[str, Any], optional): Detalles adicionales
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'page': self.__class__.__name__,
            'action': action,
            'details': details or {}
        }
        
        logger.info(f"Página {self.__class__.__name__}: {action}", extra=log_entry)
    
    def get_default_chart_config(self) -> Dict[str, Any]:
        """
        Obtiene configuración por defecto para gráficos Plotly
        
        Returns:
            Dict[str, Any]: Configuración de gráficos
        """
        return {
            'displayModeBar': True,
            'modeBarButtonsToRemove': [
                'pan2d', 'lasso2d', 'select2d', 'autoScale2d'
            ],
            'displaylogo': False,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'{self._get_page_id()}_chart',
                'height': 500,
                'width': 700,
                'scale': 1
            }
        }
    
    def create_refresh_interval(self, interval_id: Optional[str] = None) -> dcc.Interval:
        """
        Crea un componente de intervalo para auto-refresh
        
        Args:
            interval_id (str, optional): ID del componente
            
        Returns:
            dcc.Interval: Componente de intervalo
        """
        return dcc.Interval(
            id=interval_id or f"{self._get_page_id()}-refresh-interval",
            interval=self.page_config.get('update_interval', 5000),
            n_intervals=0,
            disabled=not self.page_config.get('auto_refresh', True)
        )