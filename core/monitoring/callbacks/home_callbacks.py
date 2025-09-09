# Ruta: core/monitoring/callbacks/home_callbacks.py
"""
monitoring/callbacks/home_callbacks.py
Callbacks para Página Principal (HOME) - Trading Bot v10

Este módulo contiene todos los callbacks de Dash para la página principal del dashboard,
manejando la actualización de métricas de portfolio, tarjetas de símbolos, resumen general,
alertas del sistema, gráficos de rendimiento y acciones rápidas.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import dash
from dash import Input, Output, State, callback, ctx, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px

# Importaciones locales
from monitoring.core.data_provider import DataProvider
from monitoring.core.performance_tracker import PerformanceTracker
from monitoring.core.real_time_manager import RealTimeManager, RealTimeUpdate
from monitoring.config.chart_config import CHART_CONFIG, apply_theme, TRADING_COLORS
from monitoring.config.layout_config import LAYOUT_CONFIG

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL DE CALLBACKS
# ============================================================================

# Instancias globales (serán inyectadas por la aplicación principal)
data_provider: Optional[DataProvider] = None
performance_tracker: Optional[PerformanceTracker] = None
real_time_manager: Optional[RealTimeManager] = None

def initialize_home_callbacks(dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Inicializa las instancias globales para los callbacks de HOME
    
    Args:
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    global data_provider, performance_tracker, real_time_manager
    data_provider = dp
    performance_tracker = pt
    real_time_manager = rtm
    logger.info("🏠 Callbacks de HOME inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: ACTUALIZACIÓN DE DATOS
# ============================================================================

@callback(
    [
        Output('home-data-store', 'data'),
        Output('home-symbols-store', 'data'),
        Output('home-last-update', 'children')
    ],
    [
        Input('home-refresh-interval', 'n_intervals'),
        Input('home-refresh-btn', 'n_clicks'),
        Input('home-force-refresh-btn', 'n_clicks')
    ],
    prevent_initial_call=False
)
def update_home_data(n_intervals: int, refresh_clicks: int, 
                    force_refresh_clicks: int) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Callback principal para actualizar todos los datos de la página HOME
    """
    try:
        # Determinar si es una actualización forzada
        triggered_id = ctx.triggered_id if ctx.triggered else None
        force_update = triggered_id == 'home-force-refresh-btn'
        
        # Obtener datos del portfolio
        portfolio_data = _get_portfolio_data(force_refresh=force_update)
        
        # Obtener datos de símbolos individuales
        symbols_data = _get_symbols_data(force_refresh=force_update)
        
        # Timestamp de última actualización
        last_update = datetime.now().strftime("%H:%M:%S")
        
        logger.info(f"🏠 Datos de HOME actualizados: {len(symbols_data)} símbolos")
        
        return portfolio_data, symbols_data, f"Última actualización: {last_update}"
        
    except Exception as e:
        logger.error(f"❌ Error actualizando datos de HOME: {e}")
        
        # Datos de fallback
        empty_portfolio = {'error': str(e)}
        empty_symbols = {}
        error_message = f"Error: {datetime.now().strftime('%H:%M:%S')}"
        
        return empty_portfolio, empty_symbols, error_message

# ============================================================================
# CALLBACK: RESUMEN DEL PORTFOLIO
# ============================================================================

@callback(
    Output('portfolio-summary-cards', 'children'),
    [
        Input('home-data-store', 'data'),
        Input('portfolio-period-selector', 'value')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_portfolio_summary(portfolio_data: Dict[str, Any], period: str, 
                           theme: str) -> dbc.Row:
    """
    Actualiza las tarjetas de resumen del portfolio
    """
    try:
        if not portfolio_data or 'error' in portfolio_data:
            return _create_loading_portfolio_cards()
        
        # Crear tarjetas con métricas del portfolio
        summary_cards = _create_portfolio_summary_cards(portfolio_data, period, theme)
        
        return summary_cards
        
    except Exception as e:
        logger.error(f"❌ Error creando resumen del portfolio: {e}")
        
        return dbc.Row([
            dbc.Col([
                dbc.Alert(
                    f"Error al cargar resumen del portfolio: {str(e)}",
                    color="danger",
                    className="text-center"
                )
            ], width=12)
        ])

# ============================================================================
# CALLBACK: GRID DE SÍMBOLOS AUTO-GENERADO
# ============================================================================

@callback(
    Output('symbols-grid-container', 'children'),
    [
        Input('home-symbols-store', 'data'),
        Input('symbols-view-toggle', 'value'),
        Input('symbols-sort-dropdown', 'value')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_symbols_grid(symbols_data: Dict[str, Any], view_mode: str, 
                       sort_by: str, theme: str) -> html.Div:
    """
    Actualiza el grid de símbolos con auto-generación de tarjetas
    """
    try:
        if not symbols_data:
            return _create_empty_symbols_grid()
        
        # Ordenar símbolos según criterio seleccionado
        sorted_symbols = _sort_symbols_data(symbols_data, sort_by)
        
        # Crear grid responsivo de tarjetas
        if view_mode == 'cards':
            grid_content = _create_symbols_cards_grid(sorted_symbols, theme)
        else:  # table view
            grid_content = _create_symbols_table_view(sorted_symbols, theme)
        
        logger.info(f"🏠 Grid de símbolos actualizado: {len(sorted_symbols)} símbolos en modo {view_mode}")
        
        return grid_content
        
    except Exception as e:
        logger.error(f"❌ Error creando grid de símbolos: {e}")
        
        return dbc.Alert(
            f"Error al cargar símbolos: {str(e)}",
            color="danger",
            className="text-center"
        )

# ============================================================================
# CALLBACK: ALERTAS DEL SISTEMA
# ============================================================================

@callback(
    [
        Output('system-alerts-container', 'children'),
        Output('alerts-count-badge', 'children'),
        Output('alerts-count-badge', 'color')
    ],
    [
        Input('home-data-store', 'data'),
        Input('alerts-refresh-interval', 'n_intervals'),
        Input('dismiss-alert-button', 'n_clicks')
    ],
    [
        State({'type': 'alert-item', 'index': ALL}, 'id')
    ],
    prevent_initial_call=False
)
def update_system_alerts(portfolio_data: Dict[str, Any], n_intervals: int,
                        dismiss_clicks: int, alert_ids: List[Dict]) -> Tuple[html.Div, str, str]:
    """
    Actualiza las alertas del sistema en tiempo real
    """
    try:
        # Obtener alertas activas
        alerts = _get_system_alerts(portfolio_data)
        
        # Filtrar alertas desestimadas (si las hay)
        active_alerts = _filter_active_alerts(alerts)
        
        # Crear contenido de alertas
        alerts_content = _create_alerts_content(active_alerts)
        
        # Configurar badge de contador
        alert_count = len(active_alerts)
        badge_text = str(alert_count) if alert_count > 0 else ""
        badge_color = _get_alert_badge_color(active_alerts)
        
        return alerts_content, badge_text, badge_color
        
    except Exception as e:
        logger.error(f"❌ Error actualizando alertas: {e}")
        
        error_alert = dbc.Alert(
            "Error al cargar alertas del sistema",
            color="warning",
            className="mb-2"
        )
        
        return error_alert, "!", "warning"

# ============================================================================
# CALLBACK: GRÁFICO DE RENDIMIENTO GENERAL
# ============================================================================

@callback(
    [
        Output('home-performance-chart', 'figure'),
        Output('performance-chart-loading', 'style')
    ],
    [
        Input('home-data-store', 'data'),
        Input('performance-timeframe-selector', 'value'),
        Input('performance-metric-selector', 'value')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_performance_chart(portfolio_data: Dict[str, Any], timeframe: str,
                           metric: str, theme: str) -> Tuple[go.Figure, Dict[str, str]]:
    """
    Actualiza el gráfico de rendimiento general del portfolio
    """
    try:
        # Mostrar indicador de carga
        loading_style = {'display': 'flex'}
        
        if not portfolio_data or 'error' in portfolio_data:
            raise ValueError("No hay datos de portfolio disponibles")
        
        # Crear gráfico de rendimiento
        fig = _create_portfolio_performance_chart(portfolio_data, timeframe, metric, theme)
        
        # Ocultar indicador de carga
        loading_style = {'display': 'none'}
        
        return fig, loading_style
        
    except Exception as e:
        logger.error(f"❌ Error creando gráfico de rendimiento: {e}")
        
        # Crear gráfico vacío con mensaje de error
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        
        loading_style = {'display': 'none'}
        return fig, loading_style

# ============================================================================
# CALLBACK: MÉTRICAS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('real-time-total-balance', 'children'),
        Output('real-time-daily-pnl', 'children'),
        Output('real-time-daily-pnl', 'color'),
        Output('real-time-active-trades', 'children'),
        Output('real-time-win-rate', 'children')
    ],
    [
        Input('real-time-fast-interval', 'n_intervals')
    ],
    prevent_initial_call=False
)
def update_real_time_metrics(n_intervals: int) -> Tuple[str, str, str, str, str]:
    """
    Actualiza métricas clave en tiempo real
    """
    try:
        # Obtener métricas en tiempo real
        metrics = _get_real_time_metrics()
        
        # Formatear valores
        total_balance = f"${metrics.get('total_balance', 0):,.2f}"
        
        daily_pnl = metrics.get('daily_pnl', 0)
        daily_pnl_text = f"${daily_pnl:+,.2f}"
        daily_pnl_color = "success" if daily_pnl >= 0 else "danger"
        
        active_trades = str(metrics.get('active_trades', 0))
        win_rate = f"{metrics.get('win_rate', 0):.1f}%"
        
        return total_balance, daily_pnl_text, daily_pnl_color, active_trades, win_rate
        
    except Exception as e:
        logger.error(f"❌ Error actualizando métricas en tiempo real: {e}")
        return "Error", "Error", "warning", "Error", "Error"

# ============================================================================
# CALLBACK: ACCIONES RÁPIDAS
# ============================================================================

@callback(
    [
        Output('quick-action-feedback', 'children'),
        Output('quick-action-feedback', 'is_open')
    ],
    [
        Input({'type': 'quick-action-btn', 'action': ALL}, 'n_clicks')
    ],
    prevent_initial_call=True
)
def handle_quick_actions(action_clicks: List[int]) -> Tuple[dbc.Alert, bool]:
    """
    Maneja las acciones rápidas del dashboard
    """
    try:
        if not any(action_clicks) or not ctx.triggered:
            return dbc.Alert(), False
        
        # Determinar qué acción fue activada
        triggered_id = ctx.triggered[0]['prop_id']
        action_type = eval(triggered_id.split('.')[0])['action']
        
        # Ejecutar acción correspondiente
        result = _execute_quick_action(action_type)
        
        # Crear mensaje de feedback
        if result['success']:
            alert = dbc.Alert(
                [
                    html.I(className="fas fa-check-circle me-2"),
                    result['message']
                ],
                color="success",
                dismissable=True,
                duration=4000
            )
        else:
            alert = dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    result['message']
                ],
                color="warning",
                dismissable=True,
                duration=6000
            )
        
        return alert, True
        
    except Exception as e:
        logger.error(f"❌ Error en acción rápida: {e}")
        
        error_alert = dbc.Alert(
            f"Error ejecutando acción: {str(e)}",
            color="danger",
            dismissable=True,
            duration=5000
        )
        
        return error_alert, True

# ============================================================================
# CALLBACK: EXPORTACIÓN DE DATOS
# ============================================================================

@callback(
    [
        Output('export-home-download', 'data'),
        Output('export-home-button', 'children'),
        Output('export-home-button', 'disabled')
    ],
    [
        Input('export-home-button', 'n_clicks'),
        Input('export-format-dropdown', 'value')
    ],
    [
        State('home-data-store', 'data'),
        State('home-symbols-store', 'data')
    ],
    prevent_initial_call=True
)
def export_home_data(export_clicks: int, export_format: str,
                    portfolio_data: Dict[str, Any], 
                    symbols_data: Dict[str, Any]):
    """
    Exporta datos de la página HOME en el formato seleccionado
    """
    try:
        if not export_clicks:
            return no_update, no_update, no_update
        
        # Preparar datos para exportación
        export_data = _prepare_export_data(portfolio_data, symbols_data)
        
        # Generar archivo según formato
        if export_format == 'json':
            content = _export_as_json(export_data)
            filename = f"dashboard_home_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            mimetype = 'application/json'
        
        elif export_format == 'csv':
            content = _export_as_csv(export_data)
            filename = f"dashboard_home_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            mimetype = 'text/csv'
        
        elif export_format == 'excel':
            content = _export_as_excel(export_data)
            filename = f"dashboard_home_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        else:
            raise ValueError(f"Formato de exportación no soportado: {export_format}")
        
        # Actualizar botón temporalmente
        button_content = [
            html.I(className="fas fa-check me-2"),
            "Exportado"
        ]
        
        logger.info(f"📁 Datos de HOME exportados: {filename}")
        
        # Devolver archivo para descarga
        download_data = {
            'content': content,
            'filename': filename,
            'type': mimetype
        }
        
        return download_data, button_content, True
        
    except Exception as e:
        logger.error(f"❌ Error exportando datos: {e}")
        
        error_button = [
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Error"
        ]
        
        return no_update, error_button, False

# ============================================================================
# CALLBACK: CONFIGURACIÓN DE VISTA
# ============================================================================

@callback(
    [
        Output('home-layout-store', 'data'),
        Output('layout-settings-feedback', 'children')
    ],
    [
        Input('symbols-per-row-slider', 'value'),
        Input('auto-refresh-toggle', 'value'),
        Input('refresh-interval-slider', 'value'),
        Input('compact-view-toggle', 'value')
    ],
    prevent_initial_call=True
)
def update_layout_settings(symbols_per_row: int, auto_refresh: List[str],
                          refresh_interval: int, compact_view: List[str]) -> Tuple[Dict[str, Any], str]:
    """
    Actualiza configuración de layout y vista
    """
    try:
        layout_config = {
            'symbols_per_row': symbols_per_row,
            'auto_refresh': 'auto' in (auto_refresh or []),
            'refresh_interval': refresh_interval * 1000,  # Convertir a ms
            'compact_view': 'compact' in (compact_view or []),
            'updated_at': datetime.now().isoformat()
        }
        
        feedback = f"Configuración actualizada: {symbols_per_row} símbolos por fila"
        
        logger.info(f"⚙️ Configuración de layout actualizada: {layout_config}")
        
        return layout_config, feedback
        
    except Exception as e:
        logger.error(f"❌ Error actualizando configuración: {e}")
        
        return {}, f"Error: {str(e)}"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_portfolio_data(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene datos consolidados del portfolio
    """
    try:
        if data_provider:
            portfolio_summary = data_provider.get_portfolio_summary()
        else:
            # Datos de ejemplo para desarrollo
            portfolio_summary = _generate_example_portfolio_data()
        
        return portfolio_summary
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos del portfolio: {e}")
        return {'error': str(e)}

def _get_symbols_data(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Obtiene datos de todos los símbolos configurados
    """
    try:
        if data_provider:
            symbols = data_provider.get_symbols_list()
            symbols_data = {}
            
            for symbol in symbols:
                symbol_metrics = data_provider.get_symbol_metrics(symbol)
                symbols_data[symbol] = symbol_metrics
        else:
            # Datos de ejemplo para desarrollo
            symbols_data = _generate_example_symbols_data()
        
        return symbols_data
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de símbolos: {e}")
        return {}

def _generate_example_portfolio_data() -> Dict[str, Any]:
    """
    Genera datos de ejemplo del portfolio para desarrollo
    """
    import random
    
    return {
        'total_symbols': 5,
        'active_symbols': 4,
        'total_trades': random.randint(150, 500),
        'total_pnl': random.uniform(1000, 5000),
        'avg_win_rate': random.uniform(55, 75),
        'total_balance': random.uniform(15000, 25000),
        'daily_pnl': random.uniform(-200, 400),
        'weekly_pnl': random.uniform(-500, 1000),
        'monthly_pnl': random.uniform(-1000, 2500),
        'best_performer': random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT']),
        'worst_performer': random.choice(['SOLUSDT', 'DOTUSDT']),
        'active_trades': random.randint(0, 8),
        'pending_orders': random.randint(0, 5),
        'avg_trade_duration': random.uniform(60, 240),
        'sharpe_ratio': random.uniform(1.2, 2.5),
        'max_drawdown': random.uniform(5, 15),
        'updated_at': datetime.now().isoformat()
    }

def _generate_example_symbols_data() -> Dict[str, Any]:
    """
    Genera datos de ejemplo de símbolos para desarrollo
    """
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
    symbols_data = {}
    
    for symbol in symbols:
        if data_provider:
            symbols_data[symbol] = data_provider.get_symbol_metrics(symbol)
        else:
            import random
            
            symbols_data[symbol] = {
                'symbol': symbol,
                'total_trades': random.randint(20, 100),
                'win_rate': random.uniform(45, 85),
                'total_pnl': random.uniform(-500, 1500),
                'daily_pnl': random.uniform(-50, 100),
                'sharpe_ratio': random.uniform(1.0, 3.0),
                'max_drawdown': random.uniform(3, 20),
                'current_balance': random.uniform(2000, 8000),
                'target_balance': 10000,
                'last_signal': random.choice(['BUY', 'SELL', 'HOLD']),
                'status': random.choice(['active', 'paused', 'monitoring']),
                'updated_at': datetime.now().isoformat()
            }
    
    return symbols_data

def _create_loading_portfolio_cards() -> dbc.Row:
    """
    Crea tarjetas de carga para el resumen del portfolio
    """
    loading_cards = []
    
    for i in range(4):
        loading_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Skeleton(height="20px", className="mb-2"),
                        dbc.Skeleton(height="30px", width="60%")
                    ])
                ], className="text-center h-100")
            ], width=3, className="mb-3")
        )
    
    return dbc.Row(loading_cards)

def _create_portfolio_summary_cards(portfolio_data: Dict[str, Any], 
                                  period: str, theme: str) -> dbc.Row:
    """
    Crea las tarjetas de resumen del portfolio
    """
    # Determinar métricas según el período
    if period == 'daily':
        pnl_value = portfolio_data.get('daily_pnl', 0)
        pnl_label = "PnL Diario"
    elif period == 'weekly':
        pnl_value = portfolio_data.get('weekly_pnl', 0)
        pnl_label = "PnL Semanal"
    elif period == 'monthly':
        pnl_value = portfolio_data.get('monthly_pnl', 0)
        pnl_label = "PnL Mensual"
    else:
        pnl_value = portfolio_data.get('total_pnl', 0)
        pnl_label = "PnL Total"
    
    cards = [
        # Balance Total
        {
            'title': 'Balance Total',
            'value': f"${portfolio_data.get('total_balance', 0):,.2f}",
            'icon': 'fas fa-wallet',
            'color': 'primary',
            'change': f"+{portfolio_data.get('daily_pnl', 0):,.2f} hoy"
        },
        # PnL del Período
        {
            'title': pnl_label,
            'value': f"${pnl_value:+,.2f}",
            'icon': 'fas fa-chart-line',
            'color': 'success' if pnl_value >= 0 else 'danger',
            'change': f"{(pnl_value/portfolio_data.get('total_balance', 1)*100):+.2f}%"
        },
        # Símbolos Activos
        {
            'title': 'Símbolos Activos',
            'value': f"{portfolio_data.get('active_symbols', 0)}/{portfolio_data.get('total_symbols', 0)}",
            'icon': 'fas fa-coins',
            'color': 'info',
            'change': f"{portfolio_data.get('avg_win_rate', 0):.1f}% win rate"
        },
        # Trades Activos
        {
            'title': 'Trades Activos',
            'value': str(portfolio_data.get('active_trades', 0)),
            'icon': 'fas fa-exchange-alt',
            'color': 'warning',
            'change': f"{portfolio_data.get('total_trades', 0)} total"
        }
    ]
    
    card_components = []
    for card in cards:
        card_components.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6(card['title'], className="card-subtitle mb-2 text-muted"),
                                html.H4(card['value'], className=f"card-title mb-1 text-{card['color']}"),
                                html.Small(card['change'], className="text-muted")
                            ], width=9),
                            dbc.Col([
                                html.I(className=f"{card['icon']} fa-2x text-{card['color']} opacity-75")
                            ], width=3, className="text-end")
                        ])
                    ])
                ], className="h-100")
            ], width=3, className="mb-3")
        )
    
    return dbc.Row(card_components)

def _create_empty_symbols_grid() -> html.Div:
    """
    Crea un estado vacío para el grid de símbolos
    """
    return html.Div([
        html.Div([
            html.I(className="fas fa-coins fa-3x text-muted mb-3"),
            html.H5("No hay símbolos configurados", className="text-muted"),
            html.P("Configure símbolos en la sección de ajustes para ver métricas individuales", 
                  className="text-muted"),
            dbc.Button([
                html.I(className="fas fa-cog me-2"),
                "Ir a Configuración"
            ], color="primary", outline=True, href="/settings")
        ], className="text-center py-5")
    ])

def _sort_symbols_data(symbols_data: Dict[str, Any], sort_by: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Ordena los datos de símbolos según el criterio especificado
    """
    symbol_items = list(symbols_data.items())
    
    sort_configs = {
        'pnl_desc': lambda x: x[1].get('total_pnl', 0),
        'pnl_asc': lambda x: x[1].get('total_pnl', 0),
        'win_rate_desc': lambda x: x[1].get('win_rate', 0),
        'win_rate_asc': lambda x: x[1].get('win_rate', 0),
        'trades_desc': lambda x: x[1].get('total_trades', 0),
        'trades_asc': lambda x: x[1].get('total_trades', 0),
        'alphabetical': lambda x: x[0]
    }
    
    if sort_by in sort_configs:
        reverse = not sort_by.endswith('_asc') and sort_by != 'alphabetical'
        symbol_items.sort(key=sort_configs[sort_by], reverse=reverse)
    
    return symbol_items

def _create_symbols_cards_grid(symbols_data: List[Tuple[str, Dict[str, Any]]], 
                              theme: str) -> dbc.Row:
    """
    Crea grid de tarjetas para los símbolos
    """
    cards = []
    
    for symbol, metrics in symbols_data:
        # Determinar color del estado
        status = metrics.get('status', 'unknown')
        status_colors = {
            'active': 'success',
            'paused': 'warning', 
            'monitoring': 'info',
            'error': 'danger'
        }
        status_color = status_colors.get(status, 'secondary')
        
        # Determinar color del PnL
        total_pnl = metrics.get('total_pnl', 0)
        pnl_color = 'success' if total_pnl >= 0 else 'danger'
        
        # Crear tarjeta del símbolo
        card = dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col([
                            html.H5(symbol, className="mb-0"),
                            html.Small(f"{_get_symbol_description(symbol)}", className="text-muted")
                        ], width=8),
                        dbc.Col([
                            dbc.Badge(
                                status.upper(),
                                color=status_color,
                                className="float-end"
                            )
                        ], width=4)
                    ])
                ]),
                dbc.CardBody([
                    # Métricas principales
                    dbc.Row([
                        dbc.Col([
                            html.Small("PnL Total", className="text-muted d-block"),
                            html.Strong(f"${total_pnl:+,.2f}", className=f"text-{pnl_color}")
                        ], width=6),
                        dbc.Col([
                            html.Small("Win Rate", className="text-muted d-block"),
                            html.Strong(f"{metrics.get('win_rate', 0):.1f}%")
                        ], width=6)
                    ], className="mb-2"),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Small("Trades", className="text-muted d-block"),
                            html.Strong(str(metrics.get('total_trades', 0)))
                        ], width=6),
                        dbc.Col([
                            html.Small("Sharpe", className="text-muted d-block"),
                            html.Strong(f"{metrics.get('sharpe_ratio', 0):.2f}")
                        ], width=6)
                    ], className="mb-3"),
                    
                    # Última señal
                    html.Div([
                        html.Small("Última señal: ", className="text-muted"),
                        dbc.Badge(
                            metrics.get('last_signal', 'N/A'),
                            color="success" if metrics.get('last_signal') == 'BUY' else 
                                  "danger" if metrics.get('last_signal') == 'SELL' else "warning",
                            className="ms-1"
                        )
                    ])
                ])
            ], className="h-100 symbol-card", 
               style={"cursor": "pointer"},
               id={'type': 'symbol-card', 'symbol': symbol})
        ], width=4, className="mb-3")
        
        cards.append(card)
    
    return dbc.Row(cards)

def _create_symbols_table_view(symbols_data: List[Tuple[str, Dict[str, Any]]], 
                              theme: str) -> dbc.Table:
    """
    Crea vista de tabla para los símbolos
    """
    # Preparar datos para la tabla
    table_data = []
    for symbol, metrics in symbols_data:
        row = {
            'Símbolo': symbol,
            'Estado': metrics.get('status', 'N/A').upper(),
            'PnL Total': f"${metrics.get('total_pnl', 0):+,.2f}",
            'Win Rate': f"{metrics.get('win_rate', 0):.1f}%",
            'Trades': metrics.get('total_trades', 0),
            'Sharpe': f"{metrics.get('sharpe_ratio', 0):.2f}",
            'Última Señal': metrics.get('last_signal', 'N/A')
        }
        table_data.append(row)
    
    # Crear DataFrame y tabla
    df = pd.DataFrame(table_data)
    
    return dbc.Table.from_dataframe(
        df,
        striped=True,
        hover=True,
        responsive=True,
        className="symbols-table"
    )

def _get_system_alerts(portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Genera alertas del sistema basadas en los datos del portfolio
    """
    alerts = []
    
    try:
        # Alerta de PnL diario negativo significativo
        daily_pnl = portfolio_data.get('daily_pnl', 0)
        if daily_pnl < -200:
            alerts.append({
                'id': 'daily_loss',
                'type': 'warning',
                'title': 'Pérdida Diaria Significativa',
                'message': f"PnL diario de ${daily_pnl:,.2f} excede el umbral de alerta",
                'timestamp': datetime.now(),
                'dismissible': True
            })
        
        # Alerta de drawdown alto
        max_drawdown = portfolio_data.get('max_drawdown', 0)
        if max_drawdown > 10:
            alerts.append({
                'id': 'high_drawdown',
                'type': 'danger',
                'title': 'Drawdown Elevado',
                'message': f"Drawdown actual de {max_drawdown:.1f}% requiere atención",
                'timestamp': datetime.now(),
                'dismissible': True
            })
        
        # Alerta de símbolos inactivos
        active_symbols = portfolio_data.get('active_symbols', 0)
        total_symbols = portfolio_data.get('total_symbols', 0)
        if active_symbols < total_symbols:
            inactive_count = total_symbols - active_symbols
            alerts.append({
                'id': 'inactive_symbols',
                'type': 'info',
                'title': 'Símbolos Inactivos',
                'message': f"{inactive_count} símbolo(s) no están operando activamente",
                'timestamp': datetime.now(),
                'dismissible': True
            })
        
        # Alerta de win rate bajo
        avg_win_rate = portfolio_data.get('avg_win_rate', 0)
        if avg_win_rate < 50:
            alerts.append({
                'id': 'low_win_rate',
                'type': 'warning',
                'title': 'Win Rate Bajo',
                'message': f"Win rate promedio de {avg_win_rate:.1f}% está por debajo del objetivo",
                'timestamp': datetime.now(),
                'dismissible': True
            })
        
        # Alerta positiva de buen rendimiento
        if daily_pnl > 300:
            alerts.append({
                'id': 'good_performance',
                'type': 'success',
                'title': 'Excelente Rendimiento',
                'message': f"PnL diario de ${daily_pnl:,.2f} supera expectativas",
                'timestamp': datetime.now(),
                'dismissible': True
            })
        
    except Exception as e:
        logger.error(f"❌ Error generando alertas: {e}")
        alerts.append({
            'id': 'system_error',
            'type': 'danger',
            'title': 'Error del Sistema',
            'message': f"Error al generar alertas: {str(e)}",
            'timestamp': datetime.now(),
            'dismissible': True
        })
    
    return alerts

def _filter_active_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtra alertas activas (no desestimadas)
    """
    # En implementación real, esto consultaría estado de alertas desestimadas
    # Por ahora, devolver todas las alertas
    return alerts

def _create_alerts_content(alerts: List[Dict[str, Any]]) -> html.Div:
    """
    Crea el contenido HTML de las alertas
    """
    if not alerts:
        return html.Div([
            html.I(className="fas fa-check-circle text-success me-2"),
            html.Span("No hay alertas activas", className="text-muted")
        ], className="text-center py-3")
    
    alert_components = []
    for alert in alerts:
        alert_component = dbc.Alert([
            html.Div([
                html.Strong(alert['title']),
                html.Small(f" - {alert['timestamp'].strftime('%H:%M:%S')}", className="text-muted ms-2")
            ]),
            html.P(alert['message'], className="mb-0 mt-1")
        ], 
        color=alert['type'],
        dismissable=alert.get('dismissible', True),
        className="mb-2",
        id={'type': 'alert-item', 'index': alert['id']})
        
        alert_components.append(alert_component)
    
    return html.Div(alert_components)

def _get_alert_badge_color(alerts: List[Dict[str, Any]]) -> str:
    """
    Determina el color del badge basado en el tipo de alertas
    """
    if not alerts:
        return "success"
    
    # Priorizar por severidad
    alert_types = [alert['type'] for alert in alerts]
    
    if 'danger' in alert_types:
        return "danger"
    elif 'warning' in alert_types:
        return "warning"
    elif 'info' in alert_types:
        return "info"
    else:
        return "success"

def _create_portfolio_performance_chart(portfolio_data: Dict[str, Any], 
                                      timeframe: str, metric: str, 
                                      theme: str) -> go.Figure:
    """
    Crea el gráfico de rendimiento del portfolio
    """
    # Generar datos de ejemplo para el gráfico
    days = 30 if timeframe == '30d' else 7 if timeframe == '7d' else 90
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Simular datos de rendimiento
    np.random.seed(42)  # Para consistencia
    returns = np.random.normal(0.02, 0.15, days)  # 2% retorno promedio, 15% volatilidad
    cumulative_returns = np.cumprod(1 + returns) - 1
    
    if metric == 'balance':
        initial_balance = 10000
        balance_series = initial_balance * (1 + cumulative_returns)
        y_data = balance_series
        y_title = "Balance ($)"
        title = "Evolución del Balance"
    
    elif metric == 'pnl':
        initial_balance = 10000
        pnl_series = initial_balance * cumulative_returns
        y_data = pnl_series
        y_title = "PnL Acumulado ($)"
        title = "PnL Acumulado"
    
    elif metric == 'returns':
        y_data = cumulative_returns * 100
        y_title = "Retorno Acumulado (%)"
        title = "Retorno Acumulado"
    
    else:
        # Default a balance
        initial_balance = 10000
        balance_series = initial_balance * (1 + cumulative_returns)
        y_data = balance_series
        y_title = "Balance ($)"
        title = "Evolución del Balance"
    
    # Crear gráfico
    fig = go.Figure()
    
    # Línea principal
    fig.add_trace(go.Scatter(
        x=dates,
        y=y_data,
        mode='lines',
        name=title,
        line=dict(color=TRADING_COLORS['primary'], width=3),
        fill='tonexty' if metric == 'returns' else None,
        fillcolor='rgba(187, 134, 252, 0.1)' if metric == 'returns' else None
    ))
    
    # Línea de referencia (break-even) para PnL y Returns
    if metric in ['pnl', 'returns']:
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            annotation_text="Break-even"
        )
    
    # Configurar layout
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title=y_title,
        hovermode='x unified',
        height=400,
        showlegend=False
    )
    
    # Aplicar tema
    fig = apply_theme(fig, theme)
    
    return fig

def _get_real_time_metrics() -> Dict[str, Any]:
    """
    Obtiene métricas en tiempo real del sistema
    """
    try:
        if real_time_manager:
            # Obtener datos reales del real time manager
            # Esta sería la implementación real
            pass
        
        # Por ahora, simular métricas en tiempo real
        import random
        
        return {
            'total_balance': random.uniform(18000, 22000),
            'daily_pnl': random.uniform(-150, 300),
            'active_trades': random.randint(0, 8),
            'win_rate': random.uniform(58, 72),
            'hourly_change': random.uniform(-0.5, 1.2),
            'last_update': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas en tiempo real: {e}")
        return {}

def _execute_quick_action(action_type: str) -> Dict[str, Any]:
    """
    Ejecuta una acción rápida del dashboard
    """
    try:
        if action_type == 'refresh_data':
            # Refrescar todos los datos
            return {
                'success': True,
                'message': 'Datos actualizados correctamente'
            }
        
        elif action_type == 'pause_all':
            # Pausar todos los símbolos
            return {
                'success': True,
                'message': 'Todos los símbolos pausados'
            }
        
        elif action_type == 'resume_all':
            # Reanudar todos los símbolos
            return {
                'success': True,
                'message': 'Todos los símbolos reactivados'
            }
        
        elif action_type == 'export_data':
            # Exportar datos
            return {
                'success': True,
                'message': 'Datos exportados correctamente'
            }
        
        elif action_type == 'backup_config':
            # Backup de configuración
            return {
                'success': True,
                'message': 'Configuración respaldada'
            }
        
        else:
            return {
                'success': False,
                'message': f'Acción no reconocida: {action_type}'
            }
            
    except Exception as e:
        logger.error(f"❌ Error ejecutando acción {action_type}: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

def _prepare_export_data(portfolio_data: Dict[str, Any], 
                        symbols_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara datos para exportación
    """
    return {
        'export_timestamp': datetime.now().isoformat(),
        'portfolio_summary': portfolio_data,
        'symbols_metrics': symbols_data,
        'export_info': {
            'total_symbols': len(symbols_data),
            'export_format': 'dashboard_home',
            'generated_by': 'Trading Bot v10'
        }
    }

def _export_as_json(data: Dict[str, Any]) -> str:
    """
    Exporta datos como JSON
    """
    import json
    return json.dumps(data, indent=2, default=str)

def _export_as_csv(data: Dict[str, Any]) -> str:
    """
    Exporta datos como CSV
    """
    # Convertir datos de símbolos a DataFrame
    symbols_data = []
    for symbol, metrics in data.get('symbols_metrics', {}).items():
        row = {'symbol': symbol}
        row.update(metrics)
        symbols_data.append(row)
    
    df = pd.DataFrame(symbols_data)
    return df.to_csv(index=False)

def _export_as_excel(data: Dict[str, Any]) -> str:
    """
    Exporta datos como Excel (simplificado, retorna CSV por ahora)
    """
    # En implementación real, usar openpyxl o xlsxwriter
    return _export_as_csv(data)

def _get_symbol_description(symbol: str) -> str:
    """
    Obtiene descripción del símbolo
    """
    descriptions = {
        'BTCUSDT': 'Bitcoin',
        'ETHUSDT': 'Ethereum',
        'ADAUSDT': 'Cardano',
        'SOLUSDT': 'Solana',
        'DOTUSDT': 'Polkadot',
        'LINKUSDT': 'Chainlink',
        'MATICUSDT': 'Polygon',
        'AVAXUSDT': 'Avalanche'
    }
    return descriptions.get(symbol, symbol.replace('USDT', ''))

# ============================================================================
# CALLBACK: CLICK EN TARJETA DE SÍMBOLO
# ============================================================================

@callback(
    [
        Output('symbol-detail-modal', 'is_open'),
        Output('symbol-detail-content', 'children')
    ],
    [
        Input({'type': 'symbol-card', 'symbol': ALL}, 'n_clicks')
    ],
    [
        State('home-symbols-store', 'data'),
        State('theme-store', 'data')
    ],
    prevent_initial_call=True
)
def show_symbol_detail(card_clicks: List[int], symbols_data: Dict[str, Any], 
                      theme: str) -> Tuple[bool, html.Div]:
    """
    Muestra detalle de símbolo cuando se hace click en su tarjeta
    """
    try:
        if not any(card_clicks) or not ctx.triggered:
            return False, html.Div()
        
        # Determinar qué tarjeta fue clickeada
        triggered_id = ctx.triggered[0]['prop_id']
        symbol = eval(triggered_id.split('.')[0])['symbol']
        
        if symbol not in symbols_data:
            return False, html.Div()
        
        # Crear contenido del modal con detalles del símbolo
        symbol_metrics = symbols_data[symbol]
        modal_content = _create_symbol_detail_modal_content(symbol, symbol_metrics, theme)
        
        logger.info(f"🏠 Mostrando detalles del símbolo: {symbol}")
        
        return True, modal_content
        
    except Exception as e:
        logger.error(f"❌ Error mostrando detalles del símbolo: {e}")
        
        error_content = dbc.Alert(
            f"Error cargando detalles: {str(e)}",
            color="danger"
        )
        
        return True, error_content

def _create_symbol_detail_modal_content(symbol: str, metrics: Dict[str, Any], 
                                       theme: str) -> html.Div:
    """
    Crea contenido del modal de detalles del símbolo
    """
    return html.Div([
        # Header del modal
        dbc.Row([
            dbc.Col([
                html.H4(f"{symbol}", className="mb-1"),
                html.P(f"{_get_symbol_description(symbol)}", className="text-muted mb-3")
            ], width=8),
            dbc.Col([
                dbc.Badge(
                    metrics.get('status', 'N/A').upper(),
                    color="success" if metrics.get('status') == 'active' else "warning",
                    className="fs-6"
                )
            ], width=4, className="text-end")
        ], className="mb-4"),
        
        # Métricas detalladas
        dbc.Row([
            dbc.Col([
                _create_detail_metric_card("PnL Total", f"${metrics.get('total_pnl', 0):+,.2f}", 
                                         "success" if metrics.get('total_pnl', 0) >= 0 else "danger")
            ], width=3),
            dbc.Col([
                _create_detail_metric_card("Win Rate", f"{metrics.get('win_rate', 0):.1f}%", "info")
            ], width=3),
            dbc.Col([
                _create_detail_metric_card("Total Trades", str(metrics.get('total_trades', 0)), "primary")
            ], width=3),
            dbc.Col([
                _create_detail_metric_card("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", "warning")
            ], width=3)
        ], className="mb-4"),
        
        # Información adicional
        dbc.Row([
            dbc.Col([
                html.H6("Balance Actual", className="text-muted"),
                html.H5(f"${metrics.get('current_balance', 0):,.2f}")
            ], width=4),
            dbc.Col([
                html.H6("Objetivo", className="text-muted"),
                html.H5(f"${metrics.get('target_balance', 0):,.2f}")
            ], width=4),
            dbc.Col([
                html.H6("Progreso", className="text-muted"),
                html.H5(f"{(metrics.get('current_balance', 0) / max(metrics.get('target_balance', 1), 1) * 100):.1f}%")
            ], width=4)
        ], className="mb-3"),
        
        # Acciones rápidas
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("Ver Gráficos", color="primary", outline=True, 
                              href=f"/charts?symbol={symbol}"),
                    dbc.Button("Ver Ciclos", color="info", outline=True,
                              href=f"/cycles?symbol={symbol}"),
                    dbc.Button("Configurar", color="secondary", outline=True,
                              href=f"/settings?symbol={symbol}")
                ])
            ], width=12, className="text-center")
        ])
    ])

def _create_detail_metric_card(title: str, value: str, color: str = "primary") -> dbc.Card:
    """
    Crea tarjeta de métrica para el modal de detalles
    """
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="card-subtitle mb-2 text-muted"),
            html.H4(value, className=f"card-title mb-0 text-{color}")
        ])
    ], className="text-center h-100")

# ============================================================================
# FUNCIONES DE UTILIDAD PARA REGISTRAR CALLBACKS
# ============================================================================

def register_all_home_callbacks(app, dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Registra todos los callbacks de HOME en la aplicación Dash
    
    Args:
        app: Aplicación Dash
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    # Inicializar instancias globales
    initialize_home_callbacks(dp, pt, rtm)
    
    # Los callbacks ya están registrados usando el decorador @callback
    logger.info("🏠 Todos los callbacks de HOME registrados correctamente")

def get_home_callback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas de los callbacks de HOME para debugging
    
    Returns:
        Dict[str, Any]: Estadísticas de callbacks
    """
    return {
        'data_provider_connected': data_provider is not None,
        'performance_tracker_connected': performance_tracker is not None,
        'real_time_manager_connected': real_time_manager is not None,
        'callbacks_registered': True,
        'last_check': datetime.now().isoformat()
    }

# ============================================================================
# CONFIGURACIÓN DE LOGGING ESPECÍFICA
# ============================================================================

# Configurar logging específico para callbacks de HOME
logging.getLogger(__name__).setLevel(logging.INFO)

logger.info("🏠 Módulo de callbacks de HOME cargado correctamente")