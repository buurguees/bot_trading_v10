"""
monitoring/callbacks/cycles_callbacks.py
Callbacks para Página de Ciclos - Trading Bot v10

Este módulo contiene todos los callbacks de Dash para la página de análisis de ciclos,
manejando la tabla interactiva, filtros, ordenamiento, detalles de ciclos específicos,
métricas comparativas y análisis de rendimiento por ciclos.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import dash
from dash import Input, Output, State, callback, ctx, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Importaciones locales
from monitoring.core.data_provider import DataProvider
from monitoring.core.performance_tracker import PerformanceTracker, PerformanceMetrics
from monitoring.core.real_time_manager import RealTimeManager
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

def initialize_cycles_callbacks(dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Inicializa las instancias globales para los callbacks de ciclos
    
    Args:
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    global data_provider, performance_tracker, real_time_manager
    data_provider = dp
    performance_tracker = pt
    real_time_manager = rtm
    logger.info("🔄 Callbacks de ciclos inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: TABLA DE CICLOS
# ============================================================================

@callback(
    [
        Output('cycles-main-table', 'data'),
        Output('cycles-main-table', 'columns'),
        Output('cycles-table-loading', 'style'),
        Output('cycles-stats-summary', 'children'),
        Output('cycles-error-alert', 'children'),
        Output('cycles-error-alert', 'is_open')
    ],
    [
        Input('cycles-symbol-filter', 'value'),
        Input('cycles-period-filter', 'value'),
        Input('cycles-status-filter', 'value'),
        Input('cycles-sort-dropdown', 'value'),
        Input('cycles-refresh-interval', 'n_intervals'),
        Input('refresh-cycles-button', 'n_clicks'),
        Input('cycles-page-size-dropdown', 'value')
    ],
    [
        State('theme-store', 'data'),
        State('cycles-filters-store', 'data')
    ],
    prevent_initial_call=False
)
def update_cycles_table(symbol_filter: str, period_filter: str, status_filter: str,
                       sort_by: str, n_intervals: int, refresh_clicks: int,
                       page_size: int, theme: str, filters_state: Dict[str, Any]) -> Tuple:
    """
    Callback principal para actualizar la tabla de ciclos con filtros y ordenamiento
    """
    try:
        # Mostrar indicador de carga
        loading_style = {'display': 'flex'}
        
        # Obtener datos de ciclos
        cycles_data = _get_cycles_data(
            symbol_filter=symbol_filter,
            period_filter=period_filter,
            status_filter=status_filter,
            sort_by=sort_by,
            limit=page_size or 20
        )
        
        if not cycles_data:
            raise ValueError("No hay ciclos disponibles para los filtros seleccionados")
        
        # Configurar columnas de la tabla
        columns = _get_cycles_table_columns()
        
        # Formatear datos para la tabla
        table_data = _format_cycles_for_table(cycles_data)
        
        # Generar resumen estadístico
        stats_summary = _create_cycles_stats_summary(cycles_data)
        
        # Ocultar indicador de carga
        loading_style = {'display': 'none'}
        
        logger.info(f"🔄 Tabla de ciclos actualizada: {len(table_data)} ciclos mostrados")
        
        return table_data, columns, loading_style, stats_summary, "", False
        
    except Exception as e:
        logger.error(f"❌ Error actualizando tabla de ciclos: {e}")
        
        # Estado de error
        empty_columns = [{"name": "Error", "id": "error"}]
        empty_data = [{"error": f"Error: {str(e)}"}]
        loading_style = {'display': 'none'}
        error_message = f"Error al cargar ciclos: {str(e)}"
        
        return empty_data, empty_columns, loading_style, html.Div(), error_message, True

# ============================================================================
# CALLBACK: DETALLES DE CICLO ESPECÍFICO
# ============================================================================

@callback(
    [
        Output('cycle-details-modal', 'is_open'),
        Output('cycle-details-content', 'children')
    ],
    [
        Input('cycles-main-table', 'active_cell'),
        Input('close-cycle-details-button', 'n_clicks')
    ],
    [
        State('cycles-main-table', 'data'),
        State('cycle-details-modal', 'is_open'),
        State('theme-store', 'data')
    ],
    prevent_initial_call=True
)
def show_cycle_details(active_cell: Dict[str, Any], close_clicks: int,
                      table_data: List[Dict], is_open: bool, theme: str) -> Tuple[bool, html.Div]:
    """
    Muestra detalles completos de un ciclo específico en modal
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        if triggered_id == 'close-cycle-details-button':
            return False, html.Div()
        
        if not active_cell or not table_data:
            return no_update, no_update
        
        # Obtener datos del ciclo seleccionado
        row_index = active_cell.get('row', 0)
        if row_index >= len(table_data):
            return no_update, no_update
        
        cycle_data = table_data[row_index]
        cycle_id = cycle_data.get('cycle_id')
        
        if not cycle_id:
            return no_update, no_update
        
        # Obtener detalles completos del ciclo
        detailed_cycle = _get_detailed_cycle_info(cycle_id)
        
        # Crear contenido del modal
        modal_content = _create_cycle_details_content(detailed_cycle, theme)
        
        logger.info(f"📋 Mostrando detalles del ciclo: {cycle_id}")
        
        return True, modal_content
        
    except Exception as e:
        logger.error(f"❌ Error mostrando detalles del ciclo: {e}")
        
        error_content = dbc.Alert(
            f"Error cargando detalles del ciclo: {str(e)}",
            color="danger"
        )
        
        return True, error_content

# ============================================================================
# CALLBACK: GRÁFICO DE RENDIMIENTO DE CICLOS
# ============================================================================

@callback(
    [
        Output('cycles-performance-chart', 'figure'),
        Output('cycles-chart-loading', 'style')
    ],
    [
        Input('cycles-symbol-filter', 'value'),
        Input('cycles-chart-metric-selector', 'value'),
        Input('cycles-chart-timeframe-selector', 'value'),
        Input('cycles-performance-refresh', 'n_intervals')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_cycles_performance_chart(symbol_filter: str, metric: str, timeframe: str,
                                  n_intervals: int, theme: str) -> Tuple[go.Figure, Dict[str, str]]:
    """
    Actualiza el gráfico de rendimiento comparativo de ciclos
    """
    try:
        # Mostrar indicador de carga
        loading_style = {'display': 'flex'}
        
        # Obtener datos para el gráfico
        cycles_data = _get_cycles_data(
            symbol_filter=symbol_filter,
            period_filter='all',
            limit=50  # Top 50 ciclos para el gráfico
        )
        
        if not cycles_data:
            raise ValueError("No hay datos suficientes para el gráfico")
        
        # Crear gráfico basado en la métrica seleccionada
        fig = _create_cycles_performance_figure(cycles_data, metric, timeframe, theme)
        
        # Ocultar indicador de carga
        loading_style = {'display': 'none'}
        
        logger.info(f"📊 Gráfico de ciclos actualizado: {metric} - {timeframe}")
        
        return fig, loading_style
        
    except Exception as e:
        logger.error(f"❌ Error actualizando gráfico de ciclos: {e}")
        
        # Crear figura vacía en caso de error
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
# CALLBACK: ANÁLISIS COMPARATIVO
# ============================================================================

@callback(
    [
        Output('cycles-comparison-content', 'children'),
        Output('cycles-comparison-loading', 'style')
    ],
    [
        Input('compare-cycles-button', 'n_clicks'),
        Input('cycles-comparison-selector', 'value')
    ],
    [
        State('cycles-main-table', 'selected_rows'),
        State('cycles-main-table', 'data'),
        State('theme-store', 'data')
    ],
    prevent_initial_call=True
)
def update_cycles_comparison(compare_clicks: int, comparison_metric: str,
                           selected_rows: List[int], table_data: List[Dict],
                           theme: str) -> Tuple[html.Div, Dict[str, str]]:
    """
    Crea análisis comparativo entre ciclos seleccionados
    """
    try:
        if not compare_clicks or not selected_rows or not table_data:
            return html.Div("Selecciona al menos 2 ciclos para comparar"), {'display': 'none'}
        
        if len(selected_rows) < 2:
            return dbc.Alert(
                "Selecciona al menos 2 ciclos para comparar",
                color="warning"
            ), {'display': 'none'}
        
        # Mostrar indicador de carga
        loading_style = {'display': 'flex'}
        
        # Obtener datos de los ciclos seleccionados
        selected_cycles = [table_data[i] for i in selected_rows]
        cycle_ids = [cycle['cycle_id'] for cycle in selected_cycles]
        
        # Obtener datos detallados para comparación
        detailed_cycles = [_get_detailed_cycle_info(cycle_id) for cycle_id in cycle_ids]
        
        # Crear contenido de comparación
        comparison_content = _create_cycles_comparison_content(
            detailed_cycles, comparison_metric, theme
        )
        
        # Ocultar indicador de carga
        loading_style = {'display': 'none'}
        
        logger.info(f"📊 Comparación de ciclos creada: {len(selected_cycles)} ciclos")
        
        return comparison_content, loading_style
        
    except Exception as e:
        logger.error(f"❌ Error en comparación de ciclos: {e}")
        
        error_content = dbc.Alert(
            f"Error en comparación: {str(e)}",
            color="danger"
        )
        
        return error_content, {'display': 'none'}

# ============================================================================
# CALLBACK: FILTROS DINÁMICOS
# ============================================================================

@callback(
    [
        Output('cycles-symbol-filter', 'options'),
        Output('cycles-symbol-filter', 'value'),
        Output('cycles-filters-stats', 'children')
    ],
    [
        Input('refresh-filters-button', 'n_clicks'),
        Input('reset-filters-button', 'n_clicks'),
        Input('cycles-filters-refresh-interval', 'n_intervals')
    ],
    [
        State('cycles-symbol-filter', 'value'),
        State('cycles-period-filter', 'value'),
        State('cycles-status-filter', 'value')
    ],
    prevent_initial_call=False
)
def update_cycles_filters(refresh_clicks: int, reset_clicks: int, n_intervals: int,
                         current_symbol: str, current_period: str, 
                         current_status: str) -> Tuple[List[Dict], str, html.Div]:
    """
    Actualiza las opciones de filtros dinámicamente
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        # Obtener símbolos disponibles
        symbols = data_provider.get_symbols_list() if data_provider else []
        
        symbol_options = [{'label': 'Todos los símbolos', 'value': 'all'}]
        symbol_options.extend([
            {'label': f"{symbol} - {_get_symbol_description(symbol)}", 'value': symbol}
            for symbol in symbols
        ])
        
        # Determinar valor del símbolo
        if triggered_id == 'reset-filters-button':
            symbol_value = 'all'
        else:
            symbol_value = current_symbol or 'all'
        
        # Crear estadísticas de filtros
        filter_stats = _create_filter_stats(symbols)
        
        logger.info(f"🔧 Filtros de ciclos actualizados: {len(symbols)} símbolos disponibles")
        
        return symbol_options, symbol_value, filter_stats
        
    except Exception as e:
        logger.error(f"❌ Error actualizando filtros: {e}")
        
        # Opciones por defecto
        default_options = [{'label': 'Error cargando símbolos', 'value': 'all'}]
        return default_options, 'all', html.Div()

# ============================================================================
# CALLBACK: EXPORTACIÓN DE DATOS
# ============================================================================

@callback(
    Output('export-cycles-download', 'data'),
    [
        Input('export-cycles-csv-button', 'n_clicks'),
        Input('export-cycles-excel-button', 'n_clicks'),
        Input('export-cycles-json-button', 'n_clicks')
    ],
    [
        State('cycles-main-table', 'data'),
        State('cycles-symbol-filter', 'value'),
        State('cycles-period-filter', 'value')
    ],
    prevent_initial_call=True
)
def export_cycles_data(csv_clicks: int, excel_clicks: int, json_clicks: int,
                      table_data: List[Dict], symbol_filter: str, 
                      period_filter: str):
    """
    Exporta datos de ciclos en diferentes formatos
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        if not triggered_id or not table_data:
            return no_update
        
        # Determinar formato de exportación
        if 'csv' in triggered_id:
            export_format = 'csv'
        elif 'excel' in triggered_id:
            export_format = 'xlsx'
        elif 'json' in triggered_id:
            export_format = 'json'
        else:
            return no_update
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol_part = symbol_filter if symbol_filter != 'all' else 'todos'
        filename = f"ciclos_{symbol_part}_{period_filter}_{timestamp}.{export_format}"
        
        # Preparar datos para exportación
        df = pd.DataFrame(table_data)
        
        if export_format == 'csv':
            content = df.to_csv(index=False)
            mime_type = 'text/csv'
        elif export_format == 'xlsx':
            # Para Excel, usar BytesIO (simplificado para este ejemplo)
            content = df.to_csv(index=False)  # Simplificado
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif export_format == 'json':
            content = df.to_json(orient='records', indent=2)
            mime_type = 'application/json'
        
        logger.info(f"📁 Exportando ciclos: {filename}")
        
        return {
            'content': content,
            'filename': filename,
            'type': mime_type
        }
        
    except Exception as e:
        logger.error(f"❌ Error exportando ciclos: {e}")
        return no_update

# ============================================================================
# CALLBACK: ESTADÍSTICAS EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('cycles-real-time-stats', 'children'),
        Output('active-cycles-count', 'children'),
        Output('total-cycles-pnl', 'children'),
        Output('avg-cycle-duration', 'children')
    ],
    [
        Input('cycles-real-time-interval', 'n_intervals'),
        Input('cycles-symbol-filter', 'value')
    ],
    prevent_initial_call=False
)
def update_real_time_cycles_stats(n_intervals: int, symbol_filter: str) -> Tuple:
    """
    Actualiza estadísticas en tiempo real de los ciclos
    """
    try:
        # Obtener estadísticas actuales
        stats = _get_real_time_cycles_stats(symbol_filter)
        
        # Formatear estadísticas para mostrar
        real_time_content = _create_real_time_stats_content(stats)
        
        # Métricas individuales
        active_count = f"{stats.get('active_cycles', 0)}"
        total_pnl = f"${stats.get('total_pnl', 0):,.2f}"
        avg_duration = f"{stats.get('avg_duration_days', 0):.1f}d"
        
        return real_time_content, active_count, total_pnl, avg_duration
        
    except Exception as e:
        logger.error(f"❌ Error actualizando estadísticas en tiempo real: {e}")
        
        error_content = dbc.Alert("Error cargando estadísticas", color="warning", className="mb-0")
        return error_content, "N/A", "N/A", "N/A"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _get_cycles_data(symbol_filter: str = 'all', period_filter: str = 'all',
                    status_filter: str = 'all', sort_by: str = 'pnl_desc',
                    limit: int = 20) -> List[Dict[str, Any]]:
    """
    Obtiene datos de ciclos con filtros aplicados
    """
    try:
        # En implementación real, esto consultaría la base de datos
        # Por ahora, generar datos de ejemplo realistas
        cycles = _generate_example_cycles(limit * 2)  # Generar más para filtrar
        
        # Aplicar filtros
        if symbol_filter and symbol_filter != 'all':
            cycles = [c for c in cycles if c['symbol'] == symbol_filter]
        
        if status_filter and status_filter != 'all':
            cycles = [c for c in cycles if c['status'] == status_filter]
        
        # Aplicar filtro de período
        if period_filter != 'all':
            cutoff_date = _get_period_cutoff_date(period_filter)
            cycles = [c for c in cycles if c['start_date'] >= cutoff_date]
        
        # Aplicar ordenamiento
        cycles = _sort_cycles(cycles, sort_by)
        
        # Limitar resultados
        return cycles[:limit]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de ciclos: {e}")
        return []

def _generate_example_cycles(count: int) -> List[Dict[str, Any]]:
    """
    Genera datos de ejemplo de ciclos para desarrollo
    """
    import random
    from datetime import datetime, timedelta
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
    statuses = ['completed', 'active', 'paused']
    
    cycles = []
    base_date = datetime.now() - timedelta(days=180)
    
    for i in range(count):
        symbol = random.choice(symbols)
        status = random.choice(statuses)
        
        start_date = base_date + timedelta(days=random.randint(0, 150))
        duration_days = random.randint(1, 30)
        end_date = start_date + timedelta(days=duration_days) if status == 'completed' else None
        
        # Métricas basadas en el símbolo
        base_multiplier = {
            'BTCUSDT': 5.0,
            'ETHUSDT': 3.0,
            'ADAUSDT': 1.0,
            'SOLUSDT': 2.0,
            'DOTUSDT': 1.5
        }.get(symbol, 2.0)
        
        total_trades = random.randint(10, 100)
        win_rate = random.uniform(45, 85)
        total_pnl = random.uniform(-200, 1000) * base_multiplier
        
        # Generar leverage min/max realista
        leverage_min = round(random.uniform(1.0, 3.0), 1)
        leverage_max = round(random.uniform(leverage_min, 10.0), 1)
        
        cycle = {
            'cycle_id': f"CY{i+1:04d}",
            'symbol': symbol,
            'status': status,
            'start_date': start_date,
            'end_date': end_date,
            'duration_days': duration_days if status == 'completed' else (datetime.now() - start_date).days,
            'total_trades': total_trades,
            'winning_trades': int(total_trades * win_rate / 100),
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'daily_pnl': round(total_pnl / max(duration_days, 1), 2),
            'roi_percent': round(random.uniform(-15, 45), 1),
            'max_drawdown': round(random.uniform(2, 20), 1),
            'sharpe_ratio': round(random.uniform(0.5, 3.5), 2),
            'profit_factor': round(random.uniform(0.8, 2.8), 2),
            'avg_trade_duration': round(random.uniform(30, 240), 1),
            'largest_win': round(total_pnl * random.uniform(0.1, 0.3), 2),
            'largest_loss': round(total_pnl * random.uniform(-0.15, -0.05), 2),
            'initial_balance': round(random.uniform(5000, 20000), 2),
            'current_balance': round(random.uniform(5000, 25000), 2),
            'leverage_min': leverage_min,
            'leverage_max': leverage_max
        }
        
        cycles.append(cycle)
    
    return cycles

def _get_cycles_table_columns() -> List[Dict[str, Any]]:
    """
    Define las columnas de la tabla de ciclos
    """
    return [
        {
            "name": "Ciclo ID",
            "id": "cycle_id",
            "type": "text",
            "presentation": "markdown"
        },
        {
            "name": "Símbolo",
            "id": "symbol", 
            "type": "text"
        },
        {
            "name": "Estado",
            "id": "status",
            "type": "text",
            "presentation": "markdown"
        },
        {
            "name": "Inicio",
            "id": "start_date",
            "type": "text"
        },
        {
            "name": "Duración",
            "id": "duration_text",
            "type": "text"
        },
        {
            "name": "Trades",
            "id": "total_trades",
            "type": "numeric",
            "format": {"specifier": "d"}
        },
        {
            "name": "Win Rate (%)",
            "id": "win_rate",
            "type": "numeric",
            "format": {"specifier": ".1f"}
        },
        {
            "name": "PnL Total ($)",
            "id": "total_pnl",
            "type": "numeric",
            "format": {"specifier": ".2f"}
        },
        {
            "name": "PnL Diario ($)",
            "id": "daily_pnl", 
            "type": "numeric",
            "format": {"specifier": ".2f"}
        },
        {
            "name": "ROI (%)",
            "id": "roi_percent",
            "type": "numeric",
            "format": {"specifier": ".1f"}
        },
        {
            "name": "Max DD (%)",
            "id": "max_drawdown",
            "type": "numeric",
            "format": {"specifier": ".1f"}
        },
        {
            "name": "Sharpe",
            "id": "sharpe_ratio",
            "type": "numeric", 
            "format": {"specifier": ".2f"}
        }
    ]

def _format_cycles_for_table(cycles_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formatea los datos de ciclos para mostrar en la tabla
    """
    formatted_data = []
    
    for cycle in cycles_data:
        # Formatear fechas
        start_date_str = cycle['start_date'].strftime('%Y-%m-%d') if cycle['start_date'] else 'N/A'
        
        # Formatear duración
        duration_days = cycle.get('duration_days', 0)
        if duration_days >= 7:
            weeks = duration_days // 7
            days = duration_days % 7
            duration_text = f"{weeks}w {days}d" if days > 0 else f"{weeks}w"
        else:
            duration_text = f"{duration_days}d"
        
        # Formatear estado con color
        status = cycle.get('status', 'unknown')
        status_colors = {
            'completed': '🟢 Completado',
            'active': '🔵 Activo', 
            'paused': '🟡 Pausado',
            'error': '🔴 Error'
        }
        status_formatted = status_colors.get(status, f"❓ {status}")
        
        formatted_cycle = {
            'cycle_id': f"**{cycle['cycle_id']}**",
            'symbol': cycle['symbol'],
            'status': status_formatted,
            'start_date': start_date_str,
            'duration_text': duration_text,
            'total_trades': cycle['total_trades'],
            'win_rate': cycle['win_rate'],
            'total_pnl': cycle['total_pnl'],
            'daily_pnl': cycle['daily_pnl'],
            'roi_percent': cycle['roi_percent'],
            'max_drawdown': cycle['max_drawdown'],
            'sharpe_ratio': cycle['sharpe_ratio']
        }
        
        formatted_data.append(formatted_cycle)
    
    return formatted_data

def _create_cycles_stats_summary(cycles_data: List[Dict[str, Any]]) -> html.Div:
    """
    Crea resumen estadístico de los ciclos
    """
    if not cycles_data:
        return html.Div("No hay datos para mostrar estadísticas")
    
    # Calcular estadísticas
    total_cycles = len(cycles_data)
    active_cycles = len([c for c in cycles_data if c['status'] == 'active'])
    completed_cycles = len([c for c in cycles_data if c['status'] == 'completed'])
    
    total_pnl = sum(c['total_pnl'] for c in cycles_data)
    avg_win_rate = np.mean([c['win_rate'] for c in cycles_data])
    avg_roi = np.mean([c['roi_percent'] for c in cycles_data])
    
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Ciclos", className="card-subtitle mb-2 text-muted"),
                    html.H4(f"{total_cycles}", className="card-title mb-0")
                ])
            ], className="text-center")
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Activos", className="card-subtitle mb-2 text-muted"),
                    html.H4(f"{active_cycles}", className="card-title mb-0 text-primary")
                ])
            ], className="text-center")
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Completados", className="card-subtitle mb-2 text-muted"),
                    html.H4(f"{completed_cycles}", className="card-title mb-0 text-success")
                ])
            ], className="text-center")
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("PnL Total", className="card-subtitle mb-2 text-muted"),
                    html.H4(f"${total_pnl:,.2f}", className=f"card-title mb-0 {'text-success' if total_pnl >= 0 else 'text-danger'}")
                ])
            ], className="text-center")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Win Rate Promedio", className="card-subtitle mb-2 text-muted"),
                    html.H4(f"{avg_win_rate:.1f}%", className="card-title mb-0")
                ])
            ], className="text-center")
        ], width=3)
    ], className="mb-4")

def _sort_cycles(cycles: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    """
    Ordena los ciclos según el criterio especificado
    """
    sort_configs = {
        'pnl_desc': ('total_pnl', True),
        'pnl_asc': ('total_pnl', False),
        'roi_desc': ('roi_percent', True),
        'roi_asc': ('roi_percent', False),
        'win_rate_desc': ('win_rate', True),
        'win_rate_asc': ('win_rate', False),
        'duration_desc': ('duration_days', True),
        'duration_asc': ('duration_days', False),
        'date_desc': ('start_date', True),
        'date_asc': ('start_date', False),
        'sharpe_desc': ('sharpe_ratio', True),
        'sharpe_asc': ('sharpe_ratio', False)
    }
    
    if sort_by in sort_configs:
        key, reverse = sort_configs[sort_by]
        return sorted(cycles, key=lambda x: x.get(key, 0), reverse=reverse)
    
    return cycles

def _get_period_cutoff_date(period: str) -> datetime:
    """
    Obtiene fecha de corte para filtro de período
    """
    now = datetime.now()
    
    period_map = {
        '1d': now - timedelta(days=1),
        '7d': now - timedelta(days=7),
        '30d': now - timedelta(days=30),
        '90d': now - timedelta(days=90),
        '1y': now - timedelta(days=365)
    }
    
    return period_map.get(period, now - timedelta(days=30))

def _get_detailed_cycle_info(cycle_id: str) -> Dict[str, Any]:
    """
    Obtiene información detallada de un ciclo específico
    """
    try:
        # En implementación real, esto consultaría la base de datos
        # Por ahora, generar datos detallados de ejemplo
        import random
        from datetime import datetime, timedelta
        
        # Datos base del ciclo
        base_cycle = {
            'cycle_id': cycle_id,
            'symbol': random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT']),
            'status': random.choice(['completed', 'active', 'paused']),
            'start_date': datetime.now() - timedelta(days=random.randint(1, 90)),
            'end_date': datetime.now() - timedelta(days=random.randint(0, 30)),
            'total_trades': random.randint(20, 150),
            'total_pnl': random.uniform(-500, 2000)
        }
        
        # Generar datos de trades individuales
        trades = []
        for i in range(base_cycle['total_trades']):
            trade_date = base_cycle['start_date'] + timedelta(
                hours=random.randint(0, int((base_cycle['end_date'] - base_cycle['start_date']).total_seconds() / 3600))
            )
            
            trade = {
                'trade_id': f"T{i+1:04d}",
                'timestamp': trade_date,
                'side': random.choice(['BUY', 'SELL']),
                'price': random.uniform(100, 50000),
                'quantity': random.uniform(0.01, 10),
                'pnl': random.uniform(-50, 100),
                'commission': random.uniform(0.1, 5),
                'duration_minutes': random.randint(5, 480)
            }
            trades.append(trade)
        
        # Calcular métricas avanzadas
        pnl_series = [t['pnl'] for t in trades]
        cumulative_pnl = np.cumsum(pnl_series)
        
        # Drawdown calculation
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = abs(np.min(drawdown))
        
        detailed_info = {
            **base_cycle,
            'trades': trades,
            'daily_performance': _generate_daily_performance(base_cycle['start_date'], base_cycle['end_date']),
            'metrics': {
                'win_rate': len([t for t in trades if t['pnl'] > 0]) / len(trades) * 100,
                'profit_factor': sum([t['pnl'] for t in trades if t['pnl'] > 0]) / abs(sum([t['pnl'] for t in trades if t['pnl'] < 0])),
                'max_drawdown': max_drawdown,
                'sharpe_ratio': np.mean(pnl_series) / np.std(pnl_series) if np.std(pnl_series) > 0 else 0,
                'sortino_ratio': random.uniform(1.0, 3.0),
                'calmar_ratio': random.uniform(0.5, 2.0),
                'largest_win': max(pnl_series),
                'largest_loss': min(pnl_series),
                'avg_win': np.mean([p for p in pnl_series if p > 0]),
                'avg_loss': np.mean([p for p in pnl_series if p < 0]),
                'consecutive_wins': random.randint(1, 10),
                'consecutive_losses': random.randint(1, 5),
                'total_commission': sum([t['commission'] for t in trades])
            },
            'risk_metrics': {
                'var_95': np.percentile(pnl_series, 5),
                'var_99': np.percentile(pnl_series, 1),
                'expected_shortfall': np.mean([p for p in pnl_series if p <= np.percentile(pnl_series, 5)]),
                'volatility': np.std(pnl_series),
                'skewness': random.uniform(-1, 1),
                'kurtosis': random.uniform(1, 5)
            }
        }
        
        return detailed_info
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo detalles del ciclo {cycle_id}: {e}")
        return {}

def _generate_daily_performance(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Genera datos de rendimiento diario para un ciclo
    """
    daily_data = []
    current_date = start_date
    cumulative_pnl = 0
    
    while current_date <= end_date:
        daily_pnl = np.random.normal(5, 15)  # Media 5, desviación 15
        cumulative_pnl += daily_pnl
        
        daily_data.append({
            'date': current_date,
            'daily_pnl': round(daily_pnl, 2),
            'cumulative_pnl': round(cumulative_pnl, 2),
            'trades_count': np.random.poisson(3),  # Promedio 3 trades por día
            'win_rate': np.random.uniform(0.4, 0.8)
        })
        
        current_date += timedelta(days=1)
    
    return daily_data

def _create_cycle_details_content(cycle_data: Dict[str, Any], theme: str) -> html.Div:
    """
    Crea el contenido detallado del modal de ciclo
    """
    if not cycle_data:
        return dbc.Alert("No se pudieron cargar los detalles del ciclo", color="warning")
    
    return html.Div([
        # Header del modal con información básica
        dbc.Row([
            dbc.Col([
                html.H4(f"Ciclo {cycle_data['cycle_id']}", className="mb-1"),
                html.P(f"{cycle_data['symbol']} - {cycle_data['status']}", className="text-muted mb-3")
            ], width=8),
            dbc.Col([
                dbc.Badge(
                    cycle_data['status'].upper(),
                    color="success" if cycle_data['status'] == 'completed' else 
                          "primary" if cycle_data['status'] == 'active' else "warning",
                    className="fs-6"
                )
            ], width=4, className="text-end")
        ], className="mb-4"),
        
        # Métricas principales
        dbc.Row([
            dbc.Col([
                _create_metric_card("PnL Total", f"${cycle_data.get('total_pnl', 0):,.2f}", 
                                   "success" if cycle_data.get('total_pnl', 0) >= 0 else "danger")
            ], width=3),
            dbc.Col([
                _create_metric_card("Win Rate", f"{cycle_data.get('metrics', {}).get('win_rate', 0):.1f}%", "info")
            ], width=3),
            dbc.Col([
                _create_metric_card("Sharpe Ratio", f"{cycle_data.get('metrics', {}).get('sharpe_ratio', 0):.2f}", "primary")
            ], width=3),
            dbc.Col([
                _create_metric_card("Max Drawdown", f"{cycle_data.get('metrics', {}).get('max_drawdown', 0):.2f}%", "warning")
            ], width=3)
        ], className="mb-4"),
        
        # Tabs con información detallada
        dbc.Tabs([
            dbc.Tab(label="📊 Performance", tab_id="performance-tab"),
            dbc.Tab(label="📈 Gráficos", tab_id="charts-tab"),
            dbc.Tab(label="💼 Trades", tab_id="trades-tab"),
            dbc.Tab(label="⚠️ Riesgo", tab_id="risk-tab")
        ], id="cycle-details-tabs", active_tab="performance-tab"),
        
        html.Div(id="cycle-details-tab-content", className="mt-3")
    ])

def _create_metric_card(title: str, value: str, color: str = "primary") -> dbc.Card:
    """
    Crea una tarjeta de métrica individual
    """
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="card-subtitle mb-2 text-muted"),
            html.H4(value, className=f"card-title mb-0 text-{color}")
        ])
    ], className="text-center h-100")

def _create_cycles_performance_figure(cycles_data: List[Dict[str, Any]], 
                                    metric: str, timeframe: str, theme: str) -> go.Figure:
    """
    Crea gráfico de rendimiento de ciclos
    """
    if not cycles_data:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos disponibles", x=0.5, y=0.5, xref="paper", yref="paper")
        return fig
    
    # Preparar datos según la métrica seleccionada
    if metric == 'pnl_timeline':
        return _create_pnl_timeline_chart(cycles_data, theme)
    elif metric == 'win_rate_distribution':
        return _create_win_rate_distribution_chart(cycles_data, theme)
    elif metric == 'roi_comparison':
        return _create_roi_comparison_chart(cycles_data, theme)
    elif metric == 'duration_analysis':
        return _create_duration_analysis_chart(cycles_data, theme)
    else:
        return _create_pnl_timeline_chart(cycles_data, theme)

def _create_pnl_timeline_chart(cycles_data: List[Dict[str, Any]], theme: str) -> go.Figure:
    """
    Crea gráfico de línea temporal de PnL
    """
    fig = go.Figure()
    
    # Agrupar por símbolo
    symbols = list(set([c['symbol'] for c in cycles_data]))
    colors = px.colors.qualitative.Set1
    
    for i, symbol in enumerate(symbols):
        symbol_cycles = [c for c in cycles_data if c['symbol'] == symbol]
        symbol_cycles.sort(key=lambda x: x['start_date'])
        
        x_dates = [c['start_date'] for c in symbol_cycles]
        y_pnl = [c['total_pnl'] for c in symbol_cycles]
        
        fig.add_trace(go.Scatter(
            x=x_dates,
            y=y_pnl,
            mode='lines+markers',
            name=symbol,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title="Evolución de PnL por Símbolo",
        xaxis_title="Fecha de Inicio",
        yaxis_title="PnL ($)",
        hovermode='x unified',
        height=400
    )
    
    return apply_theme(fig, theme)

def _create_win_rate_distribution_chart(cycles_data: List[Dict[str, Any]], theme: str) -> go.Figure:
    """
    Crea histograma de distribución de win rate
    """
    fig = go.Figure()
    
    win_rates = [c['win_rate'] for c in cycles_data]
    
    fig.add_trace(go.Histogram(
        x=win_rates,
        nbinsx=20,
        name="Win Rate Distribution",
        marker=dict(color=TRADING_COLORS['primary'], opacity=0.7)
    ))
    
    # Línea de promedio
    avg_win_rate = np.mean(win_rates)
    fig.add_vline(
        x=avg_win_rate,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Promedio: {avg_win_rate:.1f}%"
    )
    
    fig.update_layout(
        title="Distribución de Win Rate",
        xaxis_title="Win Rate (%)",
        yaxis_title="Número de Ciclos",
        height=400
    )
    
    return apply_theme(fig, theme)

def _create_roi_comparison_chart(cycles_data: List[Dict[str, Any]], theme: str) -> go.Figure:
    """
    Crea gráfico de comparación de ROI
    """
    fig = go.Figure()
    
    # Ordenar por ROI descendente
    sorted_cycles = sorted(cycles_data, key=lambda x: x['roi_percent'], reverse=True)[:15]
    
    cycle_ids = [c['cycle_id'] for c in sorted_cycles]
    roi_values = [c['roi_percent'] for c in sorted_cycles]
    colors = ['green' if roi >= 0 else 'red' for roi in roi_values]
    
    fig.add_trace(go.Bar(
        x=cycle_ids,
        y=roi_values,
        name="ROI",
        marker=dict(color=colors)
    ))
    
    fig.update_layout(
        title="Top 15 Ciclos por ROI",
        xaxis_title="Ciclo ID",
        yaxis_title="ROI (%)",
        height=400
    )
    
    return apply_theme(fig, theme)

def _create_duration_analysis_chart(cycles_data: List[Dict[str, Any]], theme: str) -> go.Figure:
    """
    Crea análisis de duración vs rendimiento
    """
    fig = go.Figure()
    
    durations = [c['duration_days'] for c in cycles_data]
    pnl_values = [c['total_pnl'] for c in cycles_data]
    symbols = [c['symbol'] for c in cycles_data]
    
    # Scatter plot con colores por símbolo
    unique_symbols = list(set(symbols))
    colors = px.colors.qualitative.Set1
    
    for i, symbol in enumerate(unique_symbols):
        symbol_mask = [s == symbol for s in symbols]
        symbol_durations = [d for d, m in zip(durations, symbol_mask) if m]
        symbol_pnl = [p for p, m in zip(pnl_values, symbol_mask) if m]
        
        fig.add_trace(go.Scatter(
            x=symbol_durations,
            y=symbol_pnl,
            mode='markers',
            name=symbol,
            marker=dict(
                color=colors[i % len(colors)],
                size=10,
                opacity=0.7
            )
        ))
    
    fig.update_layout(
        title="Duración vs PnL por Símbolo",
        xaxis_title="Duración (días)",
        yaxis_title="PnL ($)",
        height=400
    )
    
    return apply_theme(fig, theme)

def _create_cycles_comparison_content(cycles: List[Dict[str, Any]], 
                                    metric: str, theme: str) -> html.Div:
    """
    Crea contenido de comparación entre ciclos
    """
    if len(cycles) < 2:
        return dbc.Alert("Se necesitan al menos 2 ciclos para comparar", color="warning")
    
    return html.Div([
        html.H5(f"Comparación de {len(cycles)} Ciclos", className="mb-3"),
        
        # Tabla comparativa
        _create_comparison_table(cycles),
        
        html.Hr(),
        
        # Gráfico comparativo
        dcc.Graph(
            figure=_create_comparison_chart(cycles, metric, theme),
            config={'displayModeBar': False}
        )
    ])

def _create_comparison_table(cycles: List[Dict[str, Any]]) -> dbc.Table:
    """
    Crea tabla comparativa de ciclos
    """
    headers = ["Métrica"] + [c['cycle_id'] for c in cycles]
    
    metrics_to_compare = [
        ("Símbolo", "symbol"),
        ("PnL Total", "total_pnl"),
        ("Win Rate (%)", "win_rate"),
        ("ROI (%)", "roi_percent"),
        ("Sharpe Ratio", "sharpe_ratio"),
        ("Max Drawdown (%)", "max_drawdown"),
        ("Duración (días)", "duration_days")
    ]
    
    rows = []
    for metric_name, metric_key in metrics_to_compare:
        row = [metric_name]
        for cycle in cycles:
            value = cycle.get(metric_key, "N/A")
            if isinstance(value, (int, float)) and metric_key != "symbol":
                if metric_key in ["total_pnl", "daily_pnl"]:
                    formatted_value = f"${value:,.2f}"
                elif metric_key in ["win_rate", "roi_percent", "max_drawdown"]:
                    formatted_value = f"{value:.1f}%"
                elif metric_key in ["sharpe_ratio"]:
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
            else:
                formatted_value = str(value)
            row.append(formatted_value)
        rows.append(row)
    
    return dbc.Table.from_dataframe(
        pd.DataFrame(rows, columns=headers),
        striped=True,
        hover=True,
        responsive=True,
        className="mt-3"
    )

def _create_comparison_chart(cycles: List[Dict[str, Any]], metric: str, theme: str) -> go.Figure:
    """
    Crea gráfico de comparación entre ciclos
    """
    fig = go.Figure()
    
    cycle_ids = [c['cycle_id'] for c in cycles]
    
    if metric == 'pnl':
        values = [c['total_pnl'] for c in cycles]
        title = "Comparación de PnL Total"
        y_label = "PnL ($)"
    elif metric == 'win_rate':
        values = [c['win_rate'] for c in cycles]
        title = "Comparación de Win Rate"
        y_label = "Win Rate (%)"
    elif metric == 'roi':
        values = [c['roi_percent'] for c in cycles]
        title = "Comparación de ROI"
        y_label = "ROI (%)"
    else:
        values = [c['total_pnl'] for c in cycles]
        title = "Comparación de PnL Total"
        y_label = "PnL ($)"
    
    colors = ['green' if v >= 0 else 'red' for v in values]
    
    fig.add_trace(go.Bar(
        x=cycle_ids,
        y=values,
        marker=dict(color=colors),
        name=title
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Ciclo ID",
        yaxis_title=y_label,
        height=400
    )
    
    return apply_theme(fig, theme)

def _get_symbol_description(symbol: str) -> str:
    """
    Obtiene descripción del símbolo
    """
    descriptions = {
        'BTCUSDT': 'Bitcoin',
        'ETHUSDT': 'Ethereum', 
        'ADAUSDT': 'Cardano',
        'SOLUSDT': 'Solana',
        'DOTUSDT': 'Polkadot'
    }
    return descriptions.get(symbol, symbol.replace('USDT', ''))

def _create_filter_stats(symbols: List[str]) -> html.Div:
    """
    Crea estadísticas de filtros disponibles
    """
    return dbc.Row([
        dbc.Col([
            html.Small(f"Símbolos disponibles: {len(symbols)}", className="text-muted")
        ], width=6),
        dbc.Col([
            html.Small(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}", className="text-muted")
        ], width=6)
    ])

def _get_real_time_cycles_stats(symbol_filter: str) -> Dict[str, Any]:
    """
    Obtiene estadísticas en tiempo real de ciclos
    """
    try:
        # En implementación real, esto consultaría la base de datos
        import random
        
        base_stats = {
            'active_cycles': random.randint(3, 15),
            'completed_cycles': random.randint(50, 200),
            'total_pnl': random.uniform(1000, 10000),
            'avg_duration_days': random.uniform(5, 25),
            'best_cycle_pnl': random.uniform(500, 2000),
            'worst_cycle_pnl': random.uniform(-300, 0),
            'avg_win_rate': random.uniform(55, 75)
        }
        
        return base_stats
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas en tiempo real: {e}")
        return {}

def _create_real_time_stats_content(stats: Dict[str, Any]) -> html.Div:
    """
    Crea contenido de estadísticas en tiempo real
    """
    if not stats:
        return dbc.Alert("No hay estadísticas disponibles", color="warning", className="mb-0")
    
    return dbc.Row([
        dbc.Col([
            html.Small("Mejor Ciclo", className="text-muted d-block"),
            html.Strong(f"${stats.get('best_cycle_pnl', 0):,.2f}", className="text-success")
        ], width=6),
        dbc.Col([
            html.Small("Win Rate Promedio", className="text-muted d-block"),
            html.Strong(f"{stats.get('avg_win_rate', 0):.1f}%", className="text-info")
        ], width=6)
    ])

# ============================================================================
# FUNCIONES DE UTILIDAD PARA REGISTRAR CALLBACKS
# ============================================================================

def register_all_cycles_callbacks(app, dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Registra todos los callbacks de ciclos en la aplicación Dash
    
    Args:
        app: Aplicación Dash
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    # Inicializar instancias globales
    initialize_cycles_callbacks(dp, pt, rtm)
    
    # Los callbacks ya están registrados usando el decorador @callback
    logger.info("🔄 Todos los callbacks de ciclos registrados correctamente")

def get_cycles_callback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas de los callbacks de ciclos para debugging
    
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

# Configurar logging específico para callbacks de ciclos
logging.getLogger(__name__).setLevel(logging.INFO)

logger.info("🔄 Módulo de callbacks de ciclos cargado correctamente")