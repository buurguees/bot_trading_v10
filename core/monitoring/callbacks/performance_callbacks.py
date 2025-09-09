# Ruta: core/monitoring/callbacks/performance_callbacks.py
"""
monitoring/callbacks/performance_callbacks.py
Callbacks para Página de Análisis de Rendimiento - Trading Bot v10

Este módulo contiene todos los callbacks de Dash para la página de análisis de rendimiento,
manejando métricas avanzadas, gráficos de equity, análisis de drawdown, distribución de 
retornos, comparaciones de rendimiento y reportes de performance detallados.
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
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
import yfinance as yf  # Para benchmarks

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

def initialize_performance_callbacks(dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Inicializa las instancias globales para los callbacks de performance
    
    Args:
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    global data_provider, performance_tracker, real_time_manager
    data_provider = dp
    performance_tracker = pt
    real_time_manager = rtm
    logger.info("📊 Callbacks de Performance inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: ACTUALIZACIÓN DE DATOS DE PERFORMANCE
# ============================================================================

@callback(
    [
        Output('performance-data-store', 'data'),
        Output('performance-symbols-store', 'data'),
        Output('benchmark-data-store', 'data'),
        Output('performance-last-update', 'children')
    ],
    [
        Input('performance-refresh-interval', 'n_intervals'),
        Input('performance-refresh-btn', 'n_clicks'),
        Input('performance-period-selector', 'value'),
        Input('performance-symbol-filter', 'value')
    ],
    [
        State('benchmark-selector', 'value')
    ],
    prevent_initial_call=False
)
def update_performance_data(n_intervals: int, refresh_clicks: int, period: str,
                          symbol_filter: str, benchmark: str) -> Tuple:
    """
    Callback principal para actualizar todos los datos de performance
    """
    try:
        # Obtener datos de rendimiento general
        performance_data = _get_performance_data(period, symbol_filter)
        
        # Obtener métricas por símbolo
        symbols_data = _get_symbols_performance_data(period, symbol_filter)
        
        # Obtener datos de benchmark para comparación
        benchmark_data = _get_benchmark_data(benchmark, period)
        
        # Timestamp de última actualización
        last_update = datetime.now().strftime("%H:%M:%S")
        
        logger.info(f"📊 Datos de performance actualizados: {period} - {symbol_filter}")
        
        return performance_data, symbols_data, benchmark_data, f"Actualizado: {last_update}"
        
    except Exception as e:
        logger.error(f"❌ Error actualizando datos de performance: {e}")
        
        # Datos de fallback
        empty_data = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        error_message = f"Error: {datetime.now().strftime('%H:%M:%S')}"
        
        return empty_data, empty_data, empty_data, error_message

# ============================================================================
# CALLBACK: MÉTRICAS PRINCIPALES DE PERFORMANCE
# ============================================================================

@callback(
    [
        Output('performance-metrics-cards', 'children'),
        Output('performance-summary-table', 'children')
    ],
    [
        Input('performance-data-store', 'data'),
        Input('metrics-comparison-toggle', 'value')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_performance_metrics(performance_data: Dict[str, Any], 
                             comparison_mode: List[str], theme: str) -> Tuple:
    """
    Actualiza las métricas principales de rendimiento
    """
    try:
        if not performance_data or 'error' in performance_data:
            loading_cards = _create_loading_metrics_cards()
            loading_table = html.P("Cargando métricas...", className="text-muted")
            return loading_cards, loading_table
        
        # Crear tarjetas de métricas principales
        metrics_cards = _create_performance_metrics_cards(performance_data, theme)
        
        # Crear tabla de resumen de métricas
        show_comparison = 'comparison' in (comparison_mode or [])
        summary_table = _create_performance_summary_table(performance_data, show_comparison)
        
        return metrics_cards, summary_table
        
    except Exception as e:
        logger.error(f"❌ Error creando métricas de performance: {e}")
        
        error_cards = dbc.Alert(f"Error: {str(e)}", color="danger")
        error_table = dbc.Alert("Error cargando tabla", color="warning")
        
        return error_cards, error_table

# ============================================================================
# CALLBACK: GRÁFICO DE EQUITY CURVE
# ============================================================================

@callback(
    [
        Output('equity-curve-chart', 'figure'),
        Output('equity-chart-loading', 'style')
    ],
    [
        Input('performance-data-store', 'data'),
        Input('benchmark-data-store', 'data'),
        Input('equity-chart-options', 'value'),
        Input('equity-timeframe-selector', 'value')
    ],
    [
        State('theme-store', 'data')
    ],
    prevent_initial_call=False
)
def update_equity_curve(performance_data: Dict[str, Any], benchmark_data: Dict[str, Any],
                       chart_options: List[str], timeframe: str, theme: str) -> Tuple:
    """
    Actualiza el gráfico de curva de equity
    """
    try:
        # Mostrar loading
        loading_style = {'display': 'flex'}
        
        if not performance_data or 'error' in performance_data:
            raise ValueError("No hay datos de performance disponibles")
        
        # Crear gráfico de equity curve
        fig = _create_equity_curve_chart(performance_data, benchmark_data, 
                                       chart_options, timeframe, theme)
        
        # Ocultar loading
        loading_style = {'display': 'none'}
        
        return fig, loading_style
        
    except Exception as e:
        logger.error(f"❌ Error creando equity curve: {e}")
        
        # Gráfico vacío con error
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
# FUNCIONES AUXILIARES PARA CREAR COMPONENTES
# ============================================================================

def _create_loading_metrics_cards() -> dbc.Row:
    """
    Crea tarjetas de carga para métricas
    """
    loading_cards = []
    
    for i in range(6):
        loading_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Skeleton(height="20px", className="mb-2"),
                        dbc.Skeleton(height="30px", width="70%")
                    ])
                ], className="text-center h-100")
            ], width=2, className="mb-3")
        )
    
    return dbc.Row(loading_cards)

def _create_performance_metrics_cards(performance_data: Dict[str, Any], theme: str) -> dbc.Row:
    """
    Crea tarjetas de métricas principales de performance
    """
    metrics = performance_data.get('metrics', {})
    
    cards_data = [
        {
            'title': 'Retorno Total',
            'value': f"{metrics.get('total_return', 0):+.2f}%",
            'icon': 'fas fa-chart-line',
            'color': 'success' if metrics.get('total_return', 0) >= 0 else 'danger',
            'subtitle': f"Anualizado: {metrics.get('annualized_return', 0):+.2f}%"
        },
        {
            'title': 'Ratio de Sharpe',
            'value': f"{metrics.get('sharpe_ratio', 0):.2f}",
            'icon': 'fas fa-balance-scale',
            'color': 'info',
            'subtitle': f"Sortino: {metrics.get('sortino_ratio', 0):.2f}"
        },
        {
            'title': 'Volatilidad',
            'value': f"{metrics.get('volatility', 0):.2f}%",
            'icon': 'fas fa-wave-square',
            'color': 'warning',
            'subtitle': "Anualizada"
        },
        {
            'title': 'Max Drawdown',
            'value': f"{metrics.get('max_drawdown', 0):.2f}%",
            'icon': 'fas fa-arrow-down',
            'color': 'danger',
            'subtitle': f"Calmar: {metrics.get('calmar_ratio', 0):.2f}"
        },
        {
            'title': 'Win Rate',
            'value': f"{metrics.get('win_rate', 0):.1f}%",
            'icon': 'fas fa-target',
            'color': 'primary',
            'subtitle': f"Profit Factor: {metrics.get('profit_factor', 0):.2f}"
        },
        {
            'title': 'VaR (95%)',
            'value': f"{metrics.get('var_95', 0):.2f}%",
            'icon': 'fas fa-exclamation-triangle',
            'color': 'secondary',
            'subtitle': f"ES: {metrics.get('es_95', 0):.2f}%"
        }
    ]
    
    card_components = []
    
    for card in cards_data:
        card_components.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6(card['title'], className="card-subtitle mb-1 text-muted"),
                                html.H4(card['value'], className=f"card-title mb-0 text-{card['color']}"),
                                html.Small(card['subtitle'], className="text-muted")
                            ], width=9),
                            dbc.Col([
                                html.I(className=f"{card['icon']} fa-lg text-{card['color']} opacity-75")
                            ], width=3, className="text-end")
                        ])
                    ])
                ], className="h-100")
            ], width=2, className="mb-3")
        )
    
    return dbc.Row(card_components)

def _create_performance_summary_table(performance_data: Dict[str, Any], 
                                    show_comparison: bool) -> dbc.Table:
    """
    Crea tabla de resumen de métricas de performance
    """
    metrics = performance_data.get('metrics', {})
    
    # Datos básicos de la tabla
    table_data = [
        ['Retorno Total (%)', f"{metrics.get('total_return', 0):+.2f}"],
        ['Retorno Anualizado (%)', f"{metrics.get('annualized_return', 0):+.2f}"],
        ['Volatilidad Anualizada (%)', f"{metrics.get('volatility', 0):.2f}"],
        ['Ratio de Sharpe', f"{metrics.get('sharpe_ratio', 0):.2f}"],
        ['Ratio de Sortino', f"{metrics.get('sortino_ratio', 0):.2f}"],
        ['Máximo Drawdown (%)', f"{metrics.get('max_drawdown', 0):.2f}"],
        ['Ratio de Calmar', f"{metrics.get('calmar_ratio', 0):.2f}"],
        ['Win Rate (%)', f"{metrics.get('win_rate', 0):.1f}"],
        ['Profit Factor', f"{metrics.get('profit_factor', 0):.2f}"],
        ['VaR 95% (%)', f"{metrics.get('var_95', 0):.2f}"],
        ['Expected Shortfall 95% (%)', f"{metrics.get('es_95', 0):.2f}"],
        ['Skewness', f"{metrics.get('skewness', 0):.3f}"],
        ['Kurtosis', f"{metrics.get('kurtosis', 0):.3f}"]
    ]
    
    # Si se solicita comparación, agregar columna de benchmark
    if show_comparison:
        headers = ['Métrica', 'Valor', 'Benchmark', 'Diferencia']
        # En implementación real, agregar datos de benchmark
        for row in table_data:
            row.extend(['N/A', 'N/A'])
    else:
        headers = ['Métrica', 'Valor']
    
    df = pd.DataFrame(table_data, columns=headers)
    
    return dbc.Table.from_dataframe(
        df,
        striped=True,
        hover=True,
        responsive=True,
        className="performance-metrics-table"
    )

def _create_equity_curve_chart(performance_data: Dict[str, Any], 
                             benchmark_data: Dict[str, Any],
                             chart_options: List[str], timeframe: str, 
                             theme: str) -> go.Figure:
    """
    Crea el gráfico de curva de equity
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=['Equity Curve', 'Drawdown', 'Daily Returns'],
        row_heights=[0.6, 0.2, 0.2]
    )
    
    dates = pd.to_datetime(performance_data.get('dates', []))
    equity_curve = performance_data.get('equity_curve', [])
    drawdown = performance_data.get('drawdown', [])
    daily_returns = performance_data.get('daily_returns', [])
    
    # Equity curve principal
    fig.add_trace(go.Scatter(
        x=dates,
        y=equity_curve,
        mode='lines',
        name='Portfolio',
        line=dict(color=TRADING_COLORS['primary'], width=2),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Fecha: %{x}<br>' +
                     'Valor: $%{y:,.2f}<br>' +
                     '<extra></extra>'
    ), row=1, col=1)
    
    # Benchmark si está disponible
    if benchmark_data and 'cumulative_returns' in benchmark_data:
        benchmark_curve = np.array(benchmark_data['cumulative_returns']) / 100 + 1
        benchmark_curve *= performance_data.get('initial_balance', 10000)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark_curve,
            mode='lines',
            name=f"Benchmark ({benchmark_data.get('benchmark', 'N/A')})",
            line=dict(color=TRADING_COLORS['secondary'], width=2, dash='dash'),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Fecha: %{x}<br>' +
                         'Valor: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        ), row=1, col=1)
    
    # Drawdown
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdown,
        mode='lines',
        name='Drawdown',
        line=dict(color=TRADING_COLORS['bearish'], width=1),
        fill='tonexty',
        fillcolor='rgba(255, 23, 68, 0.1)',
        hovertemplate='<b>Drawdown</b><br>' +
                     'Fecha: %{x}<br>' +
                     'Drawdown: %{y:.2f}%<br>' +
                     '<extra></extra>',
        showlegend=False
    ), row=2, col=1)
    
    # Daily returns si está en opciones
    if 'daily_returns' in (chart_options or []):
        colors = ['green' if r >= 0 else 'red' for r in daily_returns]
        fig.add_trace(go.Bar(
            x=dates,
            y=np.array(daily_returns) * 100,
            name='Daily Returns',
            marker=dict(color=colors),
            opacity=0.7,
            hovertemplate='<b>Retorno Diario</b><br>' +
                         'Fecha: %{x}<br>' +
                         'Retorno: %{y:.2f}%<br>' +
                         '<extra></extra>',
            showlegend=False
        ), row=3, col=1)
    
    # Configurar layout
    fig.update_layout(
        title="Análisis de Performance - Equity Curve",
        height=600,
        hovermode='x unified'
    )
    
    # Configurar ejes
    fig.update_xaxes(title_text="Fecha", row=3, col=1)
    fig.update_yaxes(title_text="Valor ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.update_yaxes(title_text="Retorno (%)", row=3, col=1)
    
    return apply_theme(fig, theme)

# ============================================================================
# FUNCIONES AUXILIARES PARA DATOS
# ============================================================================

def _get_performance_data(period: str, symbol_filter: str) -> Dict[str, Any]:
    """
    Obtiene datos de rendimiento general
    """
    try:
        if performance_tracker:
            # Implementación real usando performance_tracker
            pass
        
        # Datos de ejemplo para desarrollo
        return _generate_example_performance_data(period, symbol_filter)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de performance: {e}")
        return {'error': str(e)}

def _generate_example_performance_data(period: str, symbol_filter: str) -> Dict[str, Any]:
    """
    Genera datos de ejemplo de performance
    """
    import random
    
    # Determinar número de días según período
    period_days = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        'YTD': (datetime.now() - datetime(datetime.now().year, 1, 1)).days,
        'ALL': 730  # 2 años
    }.get(period, 90)
    
    # Generar serie temporal de retornos
    np.random.seed(42)  # Para consistencia
    daily_returns = np.random.normal(0.0008, 0.02, period_days)  # 0.08% diario, 2% volatilidad
    
    # Calcular equity curve
    initial_balance = 10000
    equity_curve = initial_balance * np.cumprod(1 + daily_returns)
    
    # Calcular drawdown
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max * 100
    
    # Fechas
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    dates = pd.date_range(start=start_date, end=end_date, periods=period_days)
    
    # Calcular métricas
    total_return = (equity_curve[-1] - initial_balance) / initial_balance * 100
    annualized_return = ((equity_curve[-1] / initial_balance) ** (365 / period_days) - 1) * 100
    volatility = np.std(daily_returns) * np.sqrt(252) * 100
    sharpe_ratio = (np.mean(daily_returns) * 252) / (np.std(daily_returns) * np.sqrt(252))
    sortino_ratio = _calculate_sortino_ratio(daily_returns)
    max_drawdown = np.min(drawdown)
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # VaR y Expected Shortfall
    var_95 = np.percentile(daily_returns, 5) * 100
    var_99 = np.percentile(daily_returns, 1) * 100
    es_95 = np.mean(daily_returns[daily_returns <= np.percentile(daily_returns, 5)]) * 100
    
    return {
        'dates': dates.tolist(),
        'equity_curve': equity_curve.tolist(),
        'daily_returns': daily_returns.tolist(),
        'cumulative_returns': ((equity_curve / initial_balance - 1) * 100).tolist(),
        'drawdown': drawdown.tolist(),
        'metrics': {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'var_95': var_95,
            'var_99': var_99,
            'es_95': es_95,
            'skewness': stats.skew(daily_returns),
            'kurtosis': stats.kurtosis(daily_returns),
            'win_rate': len(daily_returns[daily_returns > 0]) / len(daily_returns) * 100,
            'avg_win': np.mean(daily_returns[daily_returns > 0]) * 100,
            'avg_loss': np.mean(daily_returns[daily_returns < 0]) * 100,
            'profit_factor': abs(np.sum(daily_returns[daily_returns > 0]) / np.sum(daily_returns[daily_returns < 0])),
            'recovery_factor': total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        },
        'period': period,
        'period_days': period_days,
        'initial_balance': initial_balance,
        'final_balance': equity_curve[-1],
        'symbol_filter': symbol_filter,
        'timestamp': datetime.now().isoformat()
    }

def _get_symbols_performance_data(period: str, symbol_filter: str) -> Dict[str, Any]:
    """
    Obtiene datos de performance por símbolo
    """
    try:
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        if symbol_filter and symbol_filter != 'all':
            symbols = [symbol_filter]
        
        symbols_data = {}
        
        for symbol in symbols:
            if performance_tracker:
                metrics = performance_tracker.calculate_symbol_metrics(symbol)
            else:
                metrics = _generate_example_symbol_performance(symbol, period)
            
            symbols_data[symbol] = metrics
        
        return symbols_data
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de símbolos: {e}")
        return {'error': str(e)}

def _generate_example_symbol_performance(symbol: str, period: str) -> Dict[str, Any]:
    """
    Genera performance de ejemplo para un símbolo
    """
    import random
    
    # Multiplicadores base por símbolo
    multipliers = {
        'BTCUSDT': 1.2,
        'ETHUSDT': 1.0,
        'ADAUSDT': 0.6,
        'SOLUSDT': 0.8,
        'DOTUSDT': 0.7
    }
    
    mult = multipliers.get(symbol, 1.0)
    
    return {
        'symbol': symbol,
        'total_return': random.uniform(-20, 40) * mult,
        'annualized_return': random.uniform(-15, 30) * mult,
        'volatility': random.uniform(15, 35),
        'sharpe_ratio': random.uniform(0.5, 2.5),
        'max_drawdown': random.uniform(-20, -5),
        'win_rate': random.uniform(45, 75),
        'total_trades': random.randint(20, 100),
        'profit_factor': random.uniform(1.0, 2.5),
        'calmar_ratio': random.uniform(0.5, 2.0),
        'sortino_ratio': random.uniform(0.8, 3.0)
    }

def _get_benchmark_data(benchmark: str, period: str) -> Dict[str, Any]:
    """
    Obtiene datos del benchmark para comparación
    """
    try:
        # Mapeo de benchmarks
        benchmark_map = {
            'btc': '^GSPC',  # S&P 500 como proxy
            'spy': '^GSPC',  # S&P 500
            'qqq': '^IXIC',  # NASDAQ
            'none': None
        }
        
        if not benchmark or benchmark == 'none':
            return {'benchmark': 'none'}
        
        # En implementación real, usar yfinance o API
        # Por ahora, generar datos de ejemplo
        return _generate_example_benchmark_data(benchmark, period)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo benchmark: {e}")
        return {'error': str(e)}

def _generate_example_benchmark_data(benchmark: str, period: str) -> Dict[str, Any]:
    """
    Genera datos de ejemplo para benchmark
    """
    import random
    
    # Generar retornos más conservadores para benchmark
    period_days = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365}.get(period, 90)
    
    np.random.seed(123)  # Seed diferente para benchmark
    daily_returns = np.random.normal(0.0005, 0.01, period_days)  # Más conservador
    
    cumulative_returns = np.cumprod(1 + daily_returns) - 1
    
    return {
        'benchmark': benchmark,
        'daily_returns': daily_returns.tolist(),
        'cumulative_returns': (cumulative_returns * 100).tolist(),
        'total_return': cumulative_returns[-1] * 100,
        'volatility': np.std(daily_returns) * np.sqrt(252) * 100,
        'sharpe_ratio': np.mean(daily_returns) * 252 / (np.std(daily_returns) * np.sqrt(252))
    }

def _calculate_sortino_ratio(returns: np.ndarray) -> float:
    """
    Calcula el ratio de Sortino
    """
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0:
        return float('inf') if np.mean(returns) > 0 else 0.0
    
    downside_deviation = np.std(downside_returns)
    if downside_deviation == 0:
        return 0.0
    
    return (np.mean(returns) * 252) / (downside_deviation * np.sqrt(252))

# ============================================================================
# FUNCIONES DE UTILIDAD PARA REGISTRAR CALLBACKS
# ============================================================================

def register_all_performance_callbacks(app, dp: DataProvider, pt: PerformanceTracker, rtm: RealTimeManager):
    """
    Registra todos los callbacks de performance en la aplicación Dash
    
    Args:
        app: Aplicación Dash
        dp (DataProvider): Proveedor de datos
        pt (PerformanceTracker): Tracker de rendimiento
        rtm (RealTimeManager): Gestor de tiempo real
    """
    # Inicializar instancias globales
    initialize_performance_callbacks(dp, pt, rtm)
    
    # Los callbacks ya están registrados usando el decorador @callback
    logger.info("📊 Todos los callbacks de Performance registrados correctamente")

def get_performance_callback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas de los callbacks de performance para debugging
    
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

# Configurar logging específico para callbacks de performance
logging.getLogger(__name__).setLevel(logging.INFO)

logger.info("📊 Módulo de callbacks de Performance cargado correctamente")
