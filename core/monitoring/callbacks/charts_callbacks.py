# Ruta: core/monitoring/callbacks/charts_callbacks.py
"""
monitoring/callbacks/charts_callbacks.py
Callbacks para Página de Gráficos - Trading Bot v10

Este módulo contiene todos los callbacks de Dash para la página de gráficos,
manejando la interactividad del gráfico de velas, selectores de símbolo/período,
indicadores técnicos, tabla de ciclos y actualizaciones en tiempo real.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import dash
from dash import Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc

# Importaciones locales
from monitoring.core.data_provider import DataProvider
from monitoring.core.real_time_manager import RealTimeManager, RealTimeUpdate
from monitoring.config.chart_config import (
    CHART_CONFIG, 
    get_chart_config,
    create_candlestick_trace,
    create_volume_trace,
    apply_theme,
    get_indicator_config,
    TRADING_COLORS,
    INDICATOR_COLORS
)
from monitoring.config.layout_config import LAYOUT_CONFIG

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL DE CALLBACKS
# ============================================================================

# Instancias globales (serán inyectadas por la aplicación principal)
data_provider: Optional[DataProvider] = None
real_time_manager: Optional[RealTimeManager] = None

def initialize_callbacks(dp: DataProvider, rtm: RealTimeManager):
    """
    Inicializa las instancias globales para los callbacks
    
    Args:
        dp (DataProvider): Proveedor de datos
        rtm (RealTimeManager): Gestor de tiempo real
    """
    global data_provider, real_time_manager
    data_provider = dp
    real_time_manager = rtm
    logger.info("📊 Callbacks de gráficos inicializados")

# ============================================================================
# CALLBACK PRINCIPAL: ACTUALIZACIÓN DEL GRÁFICO
# ============================================================================

@callback(
    [
        Output('main-candlestick-chart', 'figure'),
        Output('volume-chart', 'figure'),
        Output('chart-loading-overlay', 'style'),
        Output('chart-error-alert', 'children'),
        Output('chart-error-alert', 'is_open')
    ],
    [
        Input('symbol-selector', 'value'),
        Input('period-selector', 'value'),
        Input('timeframe-selector', 'value'),
        Input('indicators-checklist', 'value'),
        Input('chart-refresh-interval', 'n_intervals'),
        Input('refresh-chart-button', 'n_clicks')
    ],
    [
        State('theme-store', 'data'),
        State('chart-settings-store', 'data')
    ],
    prevent_initial_call=False
)
def update_main_chart(symbol: str, period: str, timeframe: str, 
                     indicators: List[str], n_intervals: int, 
                     refresh_clicks: int, theme: str, 
                     chart_settings: Dict[str, Any]) -> Tuple[go.Figure, go.Figure, Dict, str, bool]:
    """
    Callback principal para actualizar el gráfico de velas y volumen
    
    Actualiza tanto el gráfico principal como el de volumen basado en:
    - Símbolo seleccionado
    - Período temporal
    - Timeframe (1m, 5m, 1h, etc.)
    - Indicadores técnicos habilitados
    - Intervalos de actualización automática
    """
    try:
        # Validar inputs
        if not symbol or not period or not timeframe:
            raise ValueError("Parámetros requeridos faltantes")
        
        # Obtener datos OHLCV
        start_date, end_date = _parse_period(period)
        df = data_provider.get_ohlcv_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            raise ValueError(f"No hay datos disponibles para {symbol}")
        
        # Crear gráfico principal de velas
        main_fig = _create_candlestick_figure(
            df, symbol, timeframe, indicators, theme, chart_settings
        )
        
        # Crear gráfico de volumen
        volume_fig = _create_volume_figure(df, symbol, theme)
        
        # Ocultar overlay de carga
        loading_style = {'display': 'none'}
        
        logger.info(f"📊 Gráfico actualizado: {symbol} - {period} - {timeframe}")
        
        return main_fig, volume_fig, loading_style, "", False
        
    except Exception as e:
        logger.error(f"❌ Error actualizando gráfico: {e}")
        
        # Crear figuras vacías en caso de error
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        
        loading_style = {'display': 'none'}
        error_message = f"Error al cargar datos para {symbol}: {str(e)}"
        
        return empty_fig, empty_fig, loading_style, error_message, True

# ============================================================================
# CALLBACK: ACTUALIZACIÓN DE OPCIONES DE SÍMBOLOS
# ============================================================================

@callback(
    [
        Output('symbol-selector', 'options'),
        Output('symbol-selector', 'value')
    ],
    [
        Input('refresh-symbols-button', 'n_clicks'),
        Input('symbols-refresh-interval', 'n_intervals')
    ],
    prevent_initial_call=False
)
def update_symbol_options(refresh_clicks: int, n_intervals: int) -> Tuple[List[Dict], str]:
    """
    Actualiza las opciones disponibles en el selector de símbolos
    """
    try:
        symbols = data_provider.get_symbols_list()
        
        options = [
            {'label': f"{symbol} - {_get_symbol_description(symbol)}", 'value': symbol}
            for symbol in symbols
        ]
        
        # Valor por defecto (primer símbolo o BTCUSDT si está disponible)
        default_value = 'BTCUSDT' if 'BTCUSDT' in symbols else symbols[0] if symbols else None
        
        logger.info(f"📋 Símbolos actualizados: {len(symbols)} disponibles")
        
        return options, default_value
        
    except Exception as e:
        logger.error(f"❌ Error actualizando símbolos: {e}")
        
        # Opciones por defecto en caso de error
        default_options = [
            {'label': 'BTCUSDT - Bitcoin', 'value': 'BTCUSDT'},
            {'label': 'ETHUSDT - Ethereum', 'value': 'ETHUSDT'},
            {'label': 'ADAUSDT - Cardano', 'value': 'ADAUSDT'}
        ]
        
        return default_options, 'BTCUSDT'

# ============================================================================
# CALLBACK: ACTUALIZACIÓN DE TABLA DE TOP CICLOS
# ============================================================================

@callback(
    [
        Output('top-cycles-table', 'data'),
        Output('top-cycles-table', 'columns'),
        Output('cycles-table-loading', 'children')
    ],
    [
        Input('symbol-selector', 'value'),
        Input('cycles-period-selector', 'value'),
        Input('cycles-refresh-interval', 'n_intervals')
    ],
    prevent_initial_call=False
)
def update_top_cycles_table(symbol: str, period: str, n_intervals: int) -> Tuple[List[Dict], List[Dict], str]:
    """
    Actualiza la tabla con el top 20 de ciclos de trading
    """
    try:
        if not symbol:
            raise ValueError("Símbolo requerido")
        
        # Obtener datos de ciclos (simulados por ahora)
        cycles_data = _get_top_cycles_data(symbol, period)
        
        # Configurar columnas de la tabla
        columns = [
            {"name": "#", "id": "rank", "type": "numeric", "format": {"specifier": "d"}},
            {"name": "Fecha Inicio", "id": "start_date", "type": "text"},
            {"name": "Fecha Fin", "id": "end_date", "type": "text"},
            {"name": "Duración", "id": "duration", "type": "text"},
            {"name": "PnL ($)", "id": "pnl", "type": "numeric", "format": {"specifier": ".2f"}},
            {"name": "PnL Diario", "id": "daily_pnl", "type": "numeric", "format": {"specifier": ".2f"}},
            {"name": "ROI (%)", "id": "roi", "type": "numeric", "format": {"specifier": ".1f"}},
            {"name": "Trades", "id": "total_trades", "type": "numeric", "format": {"specifier": "d"}},
            {"name": "Win Rate (%)", "id": "win_rate", "type": "numeric", "format": {"specifier": ".1f"}},
            {"name": "Max DD (%)", "id": "max_drawdown", "type": "numeric", "format": {"specifier": ".1f"}}
        ]
        
        # Formatear datos para la tabla
        table_data = []
        for i, cycle in enumerate(cycles_data, 1):
            table_data.append({
                "rank": i,
                "start_date": cycle['start_date'].strftime('%Y-%m-%d'),
                "end_date": cycle['end_date'].strftime('%Y-%m-%d') if cycle['end_date'] else 'Activo',
                "duration": cycle['duration_text'],
                "pnl": cycle['total_pnl'],
                "daily_pnl": cycle['daily_pnl'],
                "roi": cycle['roi_percent'],
                "total_trades": cycle['total_trades'],
                "win_rate": cycle['win_rate'],
                "max_drawdown": cycle['max_drawdown']
            })
        
        logger.info(f"📊 Tabla de ciclos actualizada: {len(table_data)} ciclos para {symbol}")
        
        return table_data, columns, ""
        
    except Exception as e:
        logger.error(f"❌ Error actualizando tabla de ciclos: {e}")
        
        return [], [], f"Error cargando ciclos: {str(e)}"

# ============================================================================
# CALLBACK: CONFIGURACIÓN DE INDICADORES TÉCNICOS
# ============================================================================

@callback(
    [
        Output('indicators-checklist', 'options'),
        Output('indicators-checklist', 'value')
    ],
    [
        Input('reset-indicators-button', 'n_clicks'),
        Input('select-all-indicators-button', 'n_clicks')
    ],
    [
        State('indicators-checklist', 'value')
    ],
    prevent_initial_call=False
)
def update_indicators_config(reset_clicks: int, select_all_clicks: int, 
                           current_values: List[str]) -> Tuple[List[Dict], List[str]]:
    """
    Maneja la configuración de indicadores técnicos
    """
    try:
        # Definir indicadores disponibles
        available_indicators = [
            {'label': 'SMA 20', 'value': 'sma_20'},
            {'label': 'SMA 50', 'value': 'sma_50'},
            {'label': 'EMA 12', 'value': 'ema_12'},
            {'label': 'EMA 26', 'value': 'ema_26'},
            {'label': 'Bollinger Bands', 'value': 'bollinger'},
            {'label': 'RSI', 'value': 'rsi'},
            {'label': 'MACD', 'value': 'macd'},
            {'label': 'Soporte/Resistencia', 'value': 'support_resistance'}
        ]
        
        # Determinar qué botón fue presionado
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        if triggered_id == 'reset-indicators-button':
            # Resetear a valores por defecto
            default_values = ['sma_20', 'sma_50', 'bollinger']
            return available_indicators, default_values
        
        elif triggered_id == 'select-all-indicators-button':
            # Seleccionar todos los indicadores
            all_values = [opt['value'] for opt in available_indicators]
            return available_indicators, all_values
        
        else:
            # Valores por defecto en carga inicial
            default_values = ['sma_20', 'sma_50', 'bollinger']
            current_values = current_values or default_values
            return available_indicators, current_values
        
    except Exception as e:
        logger.error(f"❌ Error configurando indicadores: {e}")
        
        # Fallback seguro
        default_options = [{'label': 'SMA 20', 'value': 'sma_20'}]
        return default_options, ['sma_20']

# ============================================================================
# CALLBACK: INFORMACIÓN DETALLADA AL HACER HOVER
# ============================================================================

@callback(
    Output('chart-hover-info', 'children'),
    [
        Input('main-candlestick-chart', 'hoverData'),
        Input('symbol-selector', 'value')
    ],
    prevent_initial_call=True
)
def update_hover_info(hover_data: Dict[str, Any], symbol: str) -> dbc.Card:
    """
    Muestra información detallada cuando se hace hover sobre el gráfico
    """
    try:
        if not hover_data or not symbol:
            return no_update
        
        # Extraer datos del hover
        point_data = hover_data['points'][0]
        timestamp = point_data.get('x')
        
        if not timestamp:
            return no_update
        
        # Obtener información adicional del punto
        price_info = _get_price_info_at_timestamp(symbol, timestamp)
        
        # Crear card con información
        info_card = dbc.Card([
            dbc.CardHeader([
                html.H6(f"{symbol}", className="mb-0"),
                html.Small(timestamp, className="text-muted")
            ]),
            dbc.CardBody([
                _create_price_info_content(price_info)
            ])
        ], className="chart-hover-card")
        
        return info_card
        
    except Exception as e:
        logger.error(f"❌ Error en hover info: {e}")
        return no_update

# ============================================================================
# CALLBACK: EXPORTACIÓN DE GRÁFICOS
# ============================================================================

@callback(
    Output('export-chart-download', 'data'),
    [
        Input('export-png-button', 'n_clicks'),
        Input('export-svg-button', 'n_clicks'),
        Input('export-pdf-button', 'n_clicks')
    ],
    [
        State('main-candlestick-chart', 'figure'),
        State('symbol-selector', 'value'),
        State('period-selector', 'value')
    ],
    prevent_initial_call=True
)
def export_chart(png_clicks: int, svg_clicks: int, pdf_clicks: int,
                figure: Dict[str, Any], symbol: str, period: str):
    """
    Maneja la exportación de gráficos en diferentes formatos
    """
    try:
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        if not triggered_id or not figure:
            return no_update
        
        # Determinar formato de exportación
        export_format = triggered_id.replace('export-', '').replace('-button', '')
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{period}_{timestamp}.{export_format}"
        
        logger.info(f"📁 Exportando gráfico: {filename}")
        
        # Por ahora, retornar configuración para descarga
        # En implementación completa, se generaría el archivo real
        return {
            'content': 'Chart export functionality',
            'filename': filename,
            'type': f'image/{export_format}'
        }
        
    except Exception as e:
        logger.error(f"❌ Error exportando gráfico: {e}")
        return no_update

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _parse_period(period: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Convierte string de período a fechas de inicio y fin
    
    Args:
        period (str): Período ('1d', '30d', '90d', '1y', 'all')
        
    Returns:
        Tuple[Optional[datetime], Optional[datetime]]: Fechas de inicio y fin
    """
    end_date = datetime.now()
    
    if period == 'all':
        return None, None
    elif period == '1d':
        start_date = end_date - timedelta(days=1)
    elif period == '30d':
        start_date = end_date - timedelta(days=30)
    elif period == '90d':
        start_date = end_date - timedelta(days=90)
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
    else:
        # Default a 30 días
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date

def _create_candlestick_figure(df: pd.DataFrame, symbol: str, timeframe: str,
                              indicators: List[str], theme: str,
                              chart_settings: Dict[str, Any]) -> go.Figure:
    """
    Crea la figura principal del gráfico de velas con indicadores
    """
    # Configuración base del gráfico
    config = get_chart_config('candlestick')
    
    # Crear subplots para el gráfico principal e indicadores
    subplot_titles = [f"{symbol} - {timeframe}"]
    rows = 1
    
    # Agregar subplots para indicadores que necesitan su propio eje
    if 'rsi' in indicators:
        subplot_titles.append("RSI")
        rows += 1
    if 'macd' in indicators:
        subplot_titles.append("MACD")
        rows += 1
    
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=subplot_titles,
        row_heights=[0.7] + [0.15] * (rows - 1) if rows > 1 else [1.0]
    )
    
    # Agregar trace principal de velas
    candlestick = create_candlestick_trace(df, name=symbol)
    fig.add_trace(candlestick, row=1, col=1)
    
    # Agregar indicadores técnicos
    _add_technical_indicators(fig, df, indicators)
    
    # Agregar señales de trading si están disponibles
    _add_trading_signals(fig, df, symbol)
    
    # Aplicar configuración y tema
    fig.update_layout(**config['layout'])
    fig = apply_theme(fig, theme)
    
    # Configuraciones específicas del chart
    fig.update_xaxes(type='date')
    fig.update_layout(
        height=config.get('height', 600),
        title=f"{symbol} - {timeframe.upper()}",
        hovermode='x unified'
    )
    
    return fig

def _create_volume_figure(df: pd.DataFrame, symbol: str, theme: str) -> go.Figure:
    """
    Crea la figura del gráfico de volumen
    """
    config = get_chart_config('volume')
    
    fig = go.Figure()
    
    # Agregar trace de volumen
    volume_trace = create_volume_trace(df, name="Volumen")
    fig.add_trace(volume_trace)
    
    # Aplicar configuración y tema
    fig.update_layout(**config['layout'])
    fig = apply_theme(fig, theme)
    
    fig.update_layout(
        height=config.get('height', 200),
        title=f"Volumen - {symbol}",
        showlegend=False
    )
    
    return fig

def _add_technical_indicators(fig: go.Figure, df: pd.DataFrame, indicators: List[str]):
    """
    Agrega indicadores técnicos al gráfico
    """
    for indicator in indicators:
        try:
            if indicator == 'sma_20':
                sma_20 = df['close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(
                    x=df.index, y=sma_20,
                    name='SMA 20',
                    line=dict(color=INDICATOR_COLORS['sma_20'], width=2)
                ), row=1, col=1)
            
            elif indicator == 'sma_50':
                sma_50 = df['close'].rolling(window=50).mean()
                fig.add_trace(go.Scatter(
                    x=df.index, y=sma_50,
                    name='SMA 50',
                    line=dict(color=INDICATOR_COLORS['sma_50'], width=2)
                ), row=1, col=1)
            
            elif indicator == 'ema_12':
                ema_12 = df['close'].ewm(span=12).mean()
                fig.add_trace(go.Scatter(
                    x=df.index, y=ema_12,
                    name='EMA 12',
                    line=dict(color=INDICATOR_COLORS['ema_12'], width=2)
                ), row=1, col=1)
            
            elif indicator == 'ema_26':
                ema_26 = df['close'].ewm(span=26).mean()
                fig.add_trace(go.Scatter(
                    x=df.index, y=ema_26,
                    name='EMA 26',
                    line=dict(color=INDICATOR_COLORS['ema_26'], width=2)
                ), row=1, col=1)
            
            elif indicator == 'bollinger':
                _add_bollinger_bands(fig, df)
            
            elif indicator == 'rsi':
                _add_rsi_indicator(fig, df)
            
            elif indicator == 'macd':
                _add_macd_indicator(fig, df)
            
            elif indicator == 'support_resistance':
                _add_support_resistance_levels(fig, df)
                
        except Exception as e:
            logger.error(f"❌ Error agregando indicador {indicator}: {e}")

def _add_bollinger_bands(fig: go.Figure, df: pd.DataFrame):
    """Agrega Bandas de Bollinger al gráfico"""
    window = 20
    sma = df['close'].rolling(window=window).mean()
    std = df['close'].rolling(window=window).std()
    
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    
    # Banda superior
    fig.add_trace(go.Scatter(
        x=df.index, y=upper_band,
        name='BB Superior',
        line=dict(color=INDICATOR_COLORS['bollinger_upper'], width=1),
        fill=None
    ), row=1, col=1)
    
    # Banda media (SMA)
    fig.add_trace(go.Scatter(
        x=df.index, y=sma,
        name='BB Media',
        line=dict(color=INDICATOR_COLORS['bollinger_middle'], width=1),
        fill=None
    ), row=1, col=1)
    
    # Banda inferior con relleno
    fig.add_trace(go.Scatter(
        x=df.index, y=lower_band,
        name='BB Inferior',
        line=dict(color=INDICATOR_COLORS['bollinger_lower'], width=1),
        fill='tonexty',
        fillcolor='rgba(96, 125, 139, 0.1)'
    ), row=1, col=1)

def _add_rsi_indicator(fig: go.Figure, df: pd.DataFrame):
    """Agrega RSI al gráfico (requiere subplot separado)"""
    # Calcular RSI simplificado
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Agregar al subplot del RSI (asumiendo que existe)
    try:
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi,
            name='RSI',
            line=dict(color=INDICATOR_COLORS['rsi'], width=2)
        ), row=2, col=1)
        
        # Líneas de sobrecompra y sobreventa
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
    except Exception as e:
        logger.warning(f"No se pudo agregar RSI: {e}")

def _add_macd_indicator(fig: go.Figure, df: pd.DataFrame):
    """Agrega MACD al gráfico (requiere subplot separado)"""
    # Calcular MACD
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal
    
    try:
        # Agregar línea MACD
        fig.add_trace(go.Scatter(
            x=df.index, y=macd,
            name='MACD',
            line=dict(color=INDICATOR_COLORS['macd_line'], width=2)
        ), row=3, col=1)
        
        # Agregar línea de señal
        fig.add_trace(go.Scatter(
            x=df.index, y=signal,
            name='Signal',
            line=dict(color=INDICATOR_COLORS['macd_signal'], width=2)
        ), row=3, col=1)
        
        # Agregar histograma
        fig.add_trace(go.Bar(
            x=df.index, y=histogram,
            name='Histogram',
            marker_color=INDICATOR_COLORS['macd_histogram'],
            opacity=0.7
        ), row=3, col=1)
        
    except Exception as e:
        logger.warning(f"No se pudo agregar MACD: {e}")

def _add_support_resistance_levels(fig: go.Figure, df: pd.DataFrame):
    """Agrega niveles de soporte y resistencia"""
    # Cálculo simplificado de soporte y resistencia
    high_max = df['high'].rolling(window=20).max()
    low_min = df['low'].rolling(window=20).min()
    
    # Niveles de resistencia (máximos locales)
    resistance_levels = high_max.dropna().unique()[-3:]  # Últimos 3 niveles
    
    # Niveles de soporte (mínimos locales)
    support_levels = low_min.dropna().unique()[-3:]  # Últimos 3 niveles
    
    # Agregar líneas de resistencia
    for level in resistance_levels:
        fig.add_hline(
            y=level,
            line_dash="dash",
            line_color=INDICATOR_COLORS['resistance'],
            line_width=1,
            annotation_text=f"R: {level:.2f}",
            annotation_position="right"
        )
    
    # Agregar líneas de soporte
    for level in support_levels:
        fig.add_hline(
            y=level,
            line_dash="dash",
            line_color=INDICATOR_COLORS['support'],
            line_width=1,
            annotation_text=f"S: {level:.2f}",
            annotation_position="right"
        )

def _add_trading_signals(fig: go.Figure, df: pd.DataFrame, symbol: str):
    """Agrega señales de trading al gráfico"""
    try:
        # Obtener señales de trading (simuladas por ahora)
        signals = _get_trading_signals(symbol, df.index)
        
        for signal in signals:
            if signal['type'] == 'BUY':
                fig.add_trace(go.Scatter(
                    x=[signal['timestamp']],
                    y=[signal['price']],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color=TRADING_COLORS['bullish'],
                        line=dict(color='white', width=2)
                    ),
                    name='Señal Compra',
                    showlegend=False
                ), row=1, col=1)
            
            elif signal['type'] == 'SELL':
                fig.add_trace(go.Scatter(
                    x=[signal['timestamp']],
                    y=[signal['price']],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color=TRADING_COLORS['bearish'],
                        line=dict(color='white', width=2)
                    ),
                    name='Señal Venta',
                    showlegend=False
                ), row=1, col=1)
                
    except Exception as e:
        logger.warning(f"No se pudieron agregar señales de trading: {e}")

def _get_symbol_description(symbol: str) -> str:
    """Obtiene descripción legible del símbolo"""
    descriptions = {
        'BTCUSDT': 'Bitcoin',
        'ETHUSDT': 'Ethereum',
        'ADAUSDT': 'Cardano',
        'SOLUSDT': 'Solana',
        'DOTUSDT': 'Polkadot',
        'LINKUSDT': 'Chainlink',
        'MATICUSDT': 'Polygon',
        'AVAXUSDT': 'Avalanche',
        'ATOMUSDT': 'Cosmos',
        'ALGOUSDT': 'Algorand'
    }
    return descriptions.get(symbol, symbol.replace('USDT', ''))

def _get_top_cycles_data(symbol: str, period: str) -> List[Dict[str, Any]]:
    """
    Obtiene datos de los mejores ciclos de trading para un símbolo
    
    Args:
        symbol (str): Símbolo a consultar
        period (str): Período de análisis
        
    Returns:
        List[Dict[str, Any]]: Lista de ciclos ordenados por rendimiento
    """
    try:
        # En implementación real, esto vendría de la base de datos
        # Por ahora, generar datos de ejemplo realistas
        import random
        from datetime import datetime, timedelta
        
        cycles = []
        base_date = datetime.now() - timedelta(days=90)
        
        # Generar 25 ciclos de ejemplo
        for i in range(25):
            start_date = base_date + timedelta(days=random.randint(0, 80))
            duration_days = random.randint(1, 15)
            end_date = start_date + timedelta(days=duration_days)
            
            # Generar métricas realistas
            total_trades = random.randint(5, 50)
            win_rate = random.uniform(45, 85)
            winning_trades = int(total_trades * win_rate / 100)
            
            # PnL basado en performance del símbolo
            base_pnl = {
                'BTCUSDT': random.uniform(50, 500),
                'ETHUSDT': random.uniform(30, 300),
                'ADAUSDT': random.uniform(10, 100),
                'SOLUSDT': random.uniform(20, 200),
                'DOTUSDT': random.uniform(15, 150)
            }.get(symbol, random.uniform(25, 250))
            
            # Ajustar PnL por duración
            total_pnl = base_pnl * (duration_days / 7) * random.uniform(0.5, 1.8)
            daily_pnl = total_pnl / max(duration_days, 1)
            
            # Calcular otras métricas
            roi_percent = random.uniform(5, 25)
            max_drawdown = random.uniform(2, 12)
            
            cycle_data = {
                'cycle_id': f"C{i+1:03d}",
                'start_date': start_date,
                'end_date': end_date if random.random() > 0.1 else None,  # 10% de ciclos activos
                'duration_days': duration_days,
                'duration_text': f"{duration_days}d" if duration_days < 7 else f"{duration_days//7}w {duration_days%7}d",
                'total_pnl': round(total_pnl, 2),
                'daily_pnl': round(daily_pnl, 2),
                'roi_percent': round(roi_percent, 1),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': round(win_rate, 1),
                'max_drawdown': round(max_drawdown, 1),
                'sharpe_ratio': round(random.uniform(1.2, 3.5), 2),
                'profit_factor': round(random.uniform(1.1, 2.8), 2)
            }
            
            cycles.append(cycle_data)
        
        # Ordenar por PnL total descendente y tomar top 20
        cycles.sort(key=lambda x: x['total_pnl'], reverse=True)
        return cycles[:20]
        
    except Exception as e:
        logger.error(f"❌ Error generando datos de ciclos: {e}")
        return []

def _get_trading_signals(symbol: str, timestamps: pd.DatetimeIndex) -> List[Dict[str, Any]]:
    """
    Obtiene señales de trading para mostrar en el gráfico
    
    Args:
        symbol (str): Símbolo
        timestamps (pd.DatetimeIndex): Índice de fechas del DataFrame
        
    Returns:
        List[Dict[str, Any]]: Lista de señales de trading
    """
    try:
        import random
        
        signals = []
        
        # Generar algunas señales aleatorias para demostración
        num_signals = min(10, len(timestamps) // 20)  # Máximo 10 señales, 1 cada 20 períodos
        
        if num_signals > 0:
            signal_indices = random.sample(range(len(timestamps)), num_signals)
            
            for idx in signal_indices:
                timestamp = timestamps[idx]
                signal_type = random.choice(['BUY', 'SELL', 'HOLD'])
                
                # Simular precio en ese momento (sería obtenido de los datos reales)
                base_price = {
                    'BTCUSDT': 45000,
                    'ETHUSDT': 3000,
                    'ADAUSDT': 0.5,
                    'SOLUSDT': 100,
                    'DOTUSDT': 20
                }.get(symbol, 1000)
                
                price = base_price * random.uniform(0.95, 1.05)
                
                signal = {
                    'timestamp': timestamp,
                    'type': signal_type,
                    'price': price,
                    'confidence': random.uniform(0.6, 0.95),
                    'reason': random.choice(['breakout', 'oversold', 'trend_reversal', 'volume_spike'])
                }
                
                signals.append(signal)
        
        return signals
        
    except Exception as e:
        logger.error(f"❌ Error generando señales de trading: {e}")
        return []

def _get_price_info_at_timestamp(symbol: str, timestamp: str) -> Dict[str, Any]:
    """
    Obtiene información detallada de precio en un timestamp específico
    
    Args:
        symbol (str): Símbolo
        timestamp (str): Timestamp en formato string
        
    Returns:
        Dict[str, Any]: Información de precio
    """
    try:
        # En implementación real, esto consultaría la base de datos
        # Por ahora, generar información de ejemplo
        import random
        
        base_price = {
            'BTCUSDT': 45000,
            'ETHUSDT': 3000,
            'ADAUSDT': 0.5,
            'SOLUSDT': 100,
            'DOTUSDT': 20
        }.get(symbol, 1000)
        
        current_price = base_price * random.uniform(0.98, 1.02)
        
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'price': round(current_price, 4),
            'volume': random.randint(100000, 1000000),
            'change_24h': random.uniform(-5, 5),
            'change_percent': random.uniform(-3, 3),
            'high_24h': round(current_price * random.uniform(1.01, 1.05), 4),
            'low_24h': round(current_price * random.uniform(0.95, 0.99), 4),
            'market_cap': random.randint(1000000000, 100000000000),
            'last_signal': random.choice(['BUY', 'SELL', 'HOLD']),
            'signal_confidence': random.uniform(0.6, 0.95)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo info de precio: {e}")
        return {}

def _create_price_info_content(price_info: Dict[str, Any]) -> html.Div:
    """
    Crea el contenido HTML para la información de precio en hover
    
    Args:
        price_info (Dict[str, Any]): Información de precio
        
    Returns:
        html.Div: Contenido HTML formateado
    """
    if not price_info:
        return html.Div("No hay información disponible")
    
    change_color = "success" if price_info.get('change_percent', 0) >= 0 else "danger"
    change_icon = "↗" if price_info.get('change_percent', 0) >= 0 else "↘"
    
    return html.Div([
        # Precio actual
        dbc.Row([
            dbc.Col([
                html.Strong("Precio:", className="text-muted"),
                html.Span(f" ${price_info.get('price', 0):,.4f}", className="ms-2")
            ])
        ], className="mb-2"),
        
        # Cambio 24h
        dbc.Row([
            dbc.Col([
                html.Strong("Cambio 24h:", className="text-muted"),
                html.Span([
                    change_icon,
                    f" {price_info.get('change_percent', 0):+.2f}%"
                ], className=f"ms-2 text-{change_color}")
            ])
        ], className="mb-2"),
        
        # Rango 24h
        dbc.Row([
            dbc.Col([
                html.Strong("Rango 24h:", className="text-muted"),
                html.Div([
                    html.Small(f"Min: ${price_info.get('low_24h', 0):,.4f}", className="text-muted"),
                    html.Br(),
                    html.Small(f"Max: ${price_info.get('high_24h', 0):,.4f}", className="text-muted")
                ], className="ms-2")
            ])
        ], className="mb-2"),
        
        # Volumen
        dbc.Row([
            dbc.Col([
                html.Strong("Volumen:", className="text-muted"),
                html.Span(f" {price_info.get('volume', 0):,.0f}", className="ms-2")
            ])
        ], className="mb-2"),
        
        # Última señal
        dbc.Row([
            dbc.Col([
                html.Strong("Última señal:", className="text-muted"),
                dbc.Badge(
                    price_info.get('last_signal', 'N/A'),
                    color="success" if price_info.get('last_signal') == 'BUY' else 
                          "danger" if price_info.get('last_signal') == 'SELL' else "warning",
                    className="ms-2"
                )
            ])
        ])
    ])

# ============================================================================
# CALLBACK: ACTUALIZACIÓN EN TIEMPO REAL
# ============================================================================

@callback(
    [
        Output('real-time-price-badge', 'children'),
        Output('real-time-change-badge', 'children'),
        Output('real-time-change-badge', 'color'),
        Output('last-update-time', 'children')
    ],
    [
        Input('real-time-interval', 'n_intervals'),
        Input('symbol-selector', 'value')
    ],
    prevent_initial_call=False
)
def update_real_time_info(n_intervals: int, symbol: str) -> Tuple[str, str, str, str]:
    """
    Actualiza información en tiempo real en la interfaz
    """
    try:
        if not symbol:
            return "N/A", "N/A", "secondary", "No disponible"
        
        # Obtener último precio del real time manager
        if real_time_manager:
            latest_price = real_time_manager.get_latest_price(symbol)
        else:
            latest_price = None
        
        if latest_price:
            # Usar datos reales del real time manager
            price_text = f"${latest_price:,.4f}"
            
            # Simular cambio (en implementación real vendría del real time manager)
            import random
            change_percent = random.uniform(-2, 2)
            
        else:
            # Datos simulados para desarrollo
            import random
            base_price = {
                'BTCUSDT': 45000,
                'ETHUSDT': 3000,
                'ADAUSDT': 0.5,
                'SOLUSDT': 100,
                'DOTUSDT': 20
            }.get(symbol, 1000)
            
            current_price = base_price * random.uniform(0.995, 1.005)
            price_text = f"${current_price:,.4f}"
            change_percent = random.uniform(-1, 1)
        
        # Formatear cambio
        change_text = f"{change_percent:+.2f}%"
        change_color = "success" if change_percent >= 0 else "danger"
        
        # Timestamp de última actualización
        last_update = datetime.now().strftime("%H:%M:%S")
        
        return price_text, change_text, change_color, f"Actualizado: {last_update}"
        
    except Exception as e:
        logger.error(f"❌ Error en actualización tiempo real: {e}")
        return "Error", "N/A", "secondary", "Error"

# ============================================================================
# CALLBACK: CONFIGURACIÓN DINÁMICA DE GRÁFICOS
# ============================================================================

@callback(
    [
        Output('chart-settings-store', 'data')
    ],
    [
        Input('chart-theme-selector', 'value'),
        Input('chart-height-slider', 'value'),
        Input('show-volume-toggle', 'value'),
        Input('show-grid-toggle', 'value'),
        Input('animation-toggle', 'value')
    ],
    prevent_initial_call=False
)
def update_chart_settings(theme: str, height: int, show_volume: List[str],
                         show_grid: List[str], animations: List[str]) -> Dict[str, Any]:
    """
    Actualiza configuración dinámica de gráficos
    """
    try:
        settings = {
            'theme': theme or 'dark',
            'height': height or 600,
            'show_volume': 'volume' in (show_volume or []),
            'show_grid': 'grid' in (show_grid or []),
            'animations_enabled': 'animations' in (animations or []),
            'updated_at': datetime.now().isoformat()
        }
        
        logger.info(f"⚙️ Configuración de gráficos actualizada: {settings}")
        
        return settings
        
    except Exception as e:
        logger.error(f"❌ Error actualizando configuración: {e}")
        
        # Configuración por defecto segura
        return {
            'theme': 'dark',
            'height': 600,
            'show_volume': True,
            'show_grid': True,
            'animations_enabled': True,
            'updated_at': datetime.now().isoformat()
        }

# ============================================================================
# CALLBACK: MANEJO DE ERRORES Y ESTADOS DE CARGA
# ============================================================================

@callback(
    [
        Output('chart-loading-overlay', 'style'),
        Output('chart-error-boundary', 'children')
    ],
    [
        Input('symbol-selector', 'value'),
        Input('period-selector', 'value'),
        Input('timeframe-selector', 'value')
    ],
    [
        State('chart-loading-overlay', 'style')
    ],
    prevent_initial_call=True
)
def manage_loading_states(symbol: str, period: str, timeframe: str,
                         current_style: Dict[str, str]) -> Tuple[Dict[str, str], html.Div]:
    """
    Maneja estados de carga y errores en la interfaz
    """
    try:
        # Mostrar indicador de carga cuando cambian los parámetros
        if symbol and period and timeframe:
            loading_style = {'display': 'flex'}
            error_content = html.Div()  # Sin errores
        else:
            loading_style = {'display': 'none'}
            error_content = dbc.Alert(
                "Por favor selecciona símbolo, período y timeframe válidos",
                color="warning",
                dismissable=True
            )
        
        return loading_style, error_content
        
    except Exception as e:
        logger.error(f"❌ Error manejando estados de carga: {e}")
        
        return {'display': 'none'}, dbc.Alert(
            f"Error interno: {str(e)}",
            color="danger",
            dismissable=True
        )

# ============================================================================
# FUNCIONES DE UTILIDAD PARA CALLBACKS
# ============================================================================

def register_all_charts_callbacks(app, dp: DataProvider, rtm: RealTimeManager):
    """
    Registra todos los callbacks de gráficos en la aplicación Dash
    
    Args:
        app: Aplicación Dash
        dp (DataProvider): Proveedor de datos
        rtm (RealTimeManager): Gestor de tiempo real
    """
    # Inicializar instancias globales
    initialize_callbacks(dp, rtm)
    
    # Los callbacks ya están registrados usando el decorador @callback
    # Esta función se puede usar para configuración adicional si es necesaria
    
    logger.info("📊 Todos los callbacks de gráficos registrados correctamente")

def get_callback_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas de los callbacks para debugging
    
    Returns:
        Dict[str, Any]: Estadísticas de callbacks
    """
    return {
        'data_provider_connected': data_provider is not None,
        'real_time_manager_connected': real_time_manager is not None,
        'callbacks_registered': True,
        'last_check': datetime.now().isoformat()
    }

# ============================================================================
# CONFIGURACIÓN DE LOGGING ESPECÍFICA
# ============================================================================

# Configurar logging específico para callbacks de gráficos
logging.getLogger(__name__).setLevel(logging.INFO)

logger.info("📊 Módulo de callbacks de gráficos cargado correctamente")