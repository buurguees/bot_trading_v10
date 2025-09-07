"""
Mejoras del Dashboard - Gráfico Histórico Navegable y Análisis Mejorado
=======================================================================
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from data.database import db_manager
except ImportError:
    db_manager = None

# Componente mejorado para el gráfico histórico
def create_enhanced_chart_component():
    """Crea componente de gráfico mejorado con navegación completa"""
    
    return html.Div([
        # Controles de navegación temporal
        html.Div([
            html.H3("Análisis Histórico Completo", className="chart-title"),
            
            # Selector de rango temporal
            html.Div([
                html.Label("Período:"),
                dcc.Dropdown(
                    id='timeframe-selector',
                    options=[
                        {'label': 'Última semana', 'value': '7d'},
                        {'label': 'Último mes', 'value': '30d'},
                        {'label': 'Últimos 3 meses', 'value': '90d'},
                        {'label': 'Último año', 'value': '365d'},
                        {'label': 'Todo el histórico', 'value': 'all'},
                        {'label': 'Rango personalizado', 'value': 'custom'}
                    ],
                    value='30d',
                    className="timeframe-dropdown"
                )
            ], className="control-group"),
            
            # Selector de fechas personalizado
            html.Div([
                html.Label("Rango personalizado:"),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    start_date=datetime.now() - timedelta(days=30),
                    end_date=datetime.now(),
                    display_format='YYYY-MM-DD',
                    style={'display': 'none'}
                )
            ], id='custom-date-container'),
            
            # Selector de símbolo
            html.Div([
                html.Label("Símbolo:"),
                dcc.Dropdown(
                    id='symbol-selector',
                    options=[
                        {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                        {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                        {'label': 'ADAUSDT', 'value': 'ADAUSDT'},
                        {'label': 'SOLUSDT', 'value': 'SOLUSDT'}
                    ],
                    value='ADAUSDT',
                    className="symbol-dropdown"
                )
            ], className="control-group"),
            
            # Configuración de visualización
            html.Div([
                html.Label("Mostrar:"),
                dcc.Checklist(
                    id='chart-options',
                    options=[
                        {'label': 'Señales de compra/venta', 'value': 'signals'},
                        {'label': 'Líneas de soporte/resistencia', 'value': 'support_resistance'},
                        {'label': 'Indicadores técnicos', 'value': 'indicators'},
                        {'label': 'Volumen', 'value': 'volume'},
                        {'label': 'Análisis de rendimiento', 'value': 'performance'}
                    ],
                    value=['signals', 'volume'],
                    className="chart-options"
                )
            ], className="control-group")
        ], className="chart-controls"),
        
        # Gráfico principal
        dcc.Graph(
            id='enhanced-price-chart',
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath'],
                'scrollZoom': True
            },
            style={'height': '600px'}
        ),
        
        # Panel de estadísticas del período seleccionado
        html.Div([
            html.H4("Estadísticas del Período"),
            html.Div(id='period-stats', className="stats-grid")
        ], className="period-statistics"),
        
        # Análisis de rendimiento detallado
        html.Div([
            html.H4("Análisis de Rendimiento"),
            html.Div([
                # Métricas por categorías
                html.Div(id='performance-metrics', className="metrics-container"),
                
                # Gráfico de distribución de retornos
                dcc.Graph(id='returns-distribution', style={'height': '300px'}),
                
                # Gráfico de drawdown
                dcc.Graph(id='drawdown-chart', style={'height': '300px'})
            ], className="performance-analysis")
        ], className="analysis-section")
        
    ], className="enhanced-chart-container")

# Callbacks para funcionalidad interactiva
@callback(
    Output('custom-date-container', 'style'),
    Input('timeframe-selector', 'value')
)
def toggle_custom_date_picker(timeframe):
    """Muestra/oculta selector de fechas personalizado"""
    if timeframe == 'custom':
        return {'display': 'block'}
    return {'display': 'none'}

@callback(
    [Output('enhanced-price-chart', 'figure'),
     Output('period-stats', 'children'),
     Output('performance-metrics', 'children'),
     Output('returns-distribution', 'figure'),
     Output('drawdown-chart', 'figure')],
    [Input('timeframe-selector', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('symbol-selector', 'value'),
     Input('chart-options', 'value')]
)
def update_enhanced_chart(timeframe, start_date, end_date, symbol, chart_options):
    """Actualiza el gráfico con todas las funcionalidades mejoradas"""
    
    # Determinar rango de fechas
    if timeframe == 'custom':
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    elif timeframe == 'all':
        start_dt = None
        end_dt = None
    else:
        days = int(timeframe.replace('d', ''))
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
    
    # Obtener datos históricos
    df_market = get_historical_market_data(symbol, start_dt, end_dt)
    df_trades = get_historical_trades_data(symbol, start_dt, end_dt)
    
    # Crear gráfico principal
    fig = create_enhanced_candlestick_chart(df_market, df_trades, chart_options)
    
    # Calcular estadísticas del período
    period_stats = calculate_period_statistics(df_market, df_trades)
    
    # Generar métricas de rendimiento
    performance_metrics = generate_performance_metrics(df_trades)
    
    # Crear gráfico de distribución de retornos
    returns_fig = create_returns_distribution_chart(df_trades)
    
    # Crear gráfico de drawdown
    drawdown_fig = create_drawdown_chart(df_trades)
    
    return fig, period_stats, performance_metrics, returns_fig, drawdown_fig

def get_historical_market_data(symbol, start_date=None, end_date=None):
    """Obtiene datos históricos de mercado de la base de datos"""
    try:
        if not db_manager:
            return create_sample_market_data(symbol, start_date, end_date)
        
        # Query a la base de datos
        query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM market_data 
        WHERE symbol = '{symbol}'
        """
        
        if start_date:
            query += f" AND timestamp >= {int(start_date.timestamp())}"
        if end_date:
            query += f" AND timestamp <= {int(end_date.timestamp())}"
            
        query += " ORDER BY timestamp ASC"
        
        df = db_manager.execute_query(query)
        
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('datetime', inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error obteniendo datos históricos: {e}")
        return create_sample_market_data(symbol, start_date, end_date)

def get_historical_trades_data(symbol, start_date=None, end_date=None):
    """Obtiene datos históricos de trades"""
    try:
        if not db_manager:
            return create_sample_trades_data(symbol, start_date, end_date)
        
        query = f"""
        SELECT trade_id, symbol, side, entry_price, exit_price, 
               entry_time, exit_time, pnl, confidence
        FROM trades 
        WHERE symbol = '{symbol}'
        """
        
        if start_date:
            query += f" AND entry_time >= '{start_date.isoformat()}'"
        if end_date:
            query += f" AND entry_time <= '{end_date.isoformat()}'"
            
        query += " ORDER BY entry_time ASC"
        
        return db_manager.execute_query(query)
        
    except Exception as e:
        print(f"Error obteniendo datos de trades: {e}")
        return create_sample_trades_data(symbol, start_date, end_date)

def create_enhanced_candlestick_chart(df_market, df_trades, options):
    """Crea gráfico de candlesticks mejorado con todas las opciones"""
    
    fig = go.Figure()
    
    if df_market.empty:
        fig.add_annotation(
            text="No hay datos disponibles para el período seleccionado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Candlesticks principales
    fig.add_trace(go.Candlestick(
        x=df_market.index,
        open=df_market['open'],
        high=df_market['high'],
        low=df_market['low'],
        close=df_market['close'],
        name="Precio",
        increasing_line_color='#00ff88',
        decreasing_line_color='#ff4444'
    ))
    
    # Añadir señales de trading si están habilitadas
    if 'signals' in options and not df_trades.empty:
        # Señales de compra
        buy_signals = df_trades[df_trades['side'] == 'BUY']
        if not buy_signals.empty:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(buy_signals['entry_time']),
                y=buy_signals['entry_price'],
                mode='markers',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color='#00ff88',
                    line=dict(width=2, color='white')
                ),
                name='Compra',
                hovertemplate='<b>COMPRA</b><br>Precio: $%{y:,.2f}<br>Fecha: %{x}<extra></extra>'
            ))
        
        # Señales de venta
        sell_signals = df_trades[df_trades['side'] == 'SELL']
        if not sell_signals.empty:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(sell_signals['entry_time']),
                y=sell_signals['entry_price'],
                mode='markers',
                marker=dict(
                    symbol='triangle-down',
                    size=12,
                    color='#ff4444',
                    line=dict(width=2, color='white')
                ),
                name='Venta',
                hovertemplate='<b>VENTA</b><br>Precio: $%{y:,.2f}<br>Fecha: %{x}<extra></extra>'
            ))
    
    # Añadir volumen si está habilitado
    if 'volume' in options:
        fig.add_trace(go.Bar(
            x=df_market.index,
            y=df_market['volume'],
            name='Volumen',
            yaxis='y2',
            opacity=0.3,
            marker_color='#888888'
        ))
        
        # Configurar eje Y secundario para volumen
        fig.update_layout(
            yaxis2=dict(
                title='Volumen',
                overlaying='y',
                side='right',
                range=[0, df_market['volume'].max() * 4]
            )
        )
    
    # Añadir indicadores técnicos si están habilitados
    if 'indicators' in options:
        # Calcular medias móviles
        df_market['MA20'] = df_market['close'].rolling(window=20).mean()
        df_market['MA50'] = df_market['close'].rolling(window=50).mean()
        
        fig.add_trace(go.Scatter(
            x=df_market.index,
            y=df_market['MA20'],
            mode='lines',
            name='MA20',
            line=dict(color='orange', width=1)
        ))
        
        fig.add_trace(go.Scatter(
            x=df_market.index,
            y=df_market['MA50'],
            mode='lines',
            name='MA50',
            line=dict(color='purple', width=1)
        ))
    
    # Configuración del layout
    fig.update_layout(
        title=f"Análisis Histórico Completo - {symbol}",
        xaxis_title="Fecha",
        yaxis_title="Precio (USDT)",
        template="plotly_dark",
        height=600,
        showlegend=True,
        xaxis=dict(
            rangeslider=dict(visible=False),
            type='date',
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=7, label="7D", step="day", stepmode="backward"),
                    dict(count=30, label="30D", step="day", stepmode="backward"),
                    dict(count=90, label="3M", step="day", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
    )
    
    return fig

def calculate_period_statistics(df_market, df_trades):
    """Calcula estadísticas del período seleccionado"""
    
    if df_market.empty:
        return html.Div("No hay datos disponibles")
    
    # Estadísticas de precio
    price_change = df_market['close'].iloc[-1] - df_market['close'].iloc[0]
    price_change_pct = (price_change / df_market['close'].iloc[0]) * 100
    
    # Estadísticas de trading
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['pnl'] > 0]) if not df_trades.empty else 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Volatilidad
    returns = df_market['close'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(24*365) * 100  # Anualizada para crypto
    
    return html.Div([
        html.Div([
            html.H5("Precio"),
            html.P(f"Cambio: {price_change:+.2f} USDT ({price_change_pct:+.1f}%)")
        ], className="stat-card"),
        
        html.Div([
            html.H5("Trading"),
            html.P(f"Trades: {total_trades}"),
            html.P(f"Win Rate: {win_rate:.1f}%")
        ], className="stat-card"),
        
        html.Div([
            html.H5("Volatilidad"),
            html.P(f"{volatility:.1f}% anual")
        ], className="stat-card")
    ], className="stats-grid")

def generate_performance_metrics(df_trades):
    """Genera métricas de rendimiento"""
    if df_trades.empty:
        return html.Div("No hay datos de trades")
    
    total_pnl = df_trades['pnl'].sum()
    avg_pnl = df_trades['pnl'].mean()
    max_win = df_trades['pnl'].max()
    max_loss = df_trades['pnl'].min()
    
    return html.Div([
        html.Div([
            html.H5("P&L Total"),
            html.P(f"${total_pnl:+.2f}")
        ], className="metric-card"),
        
        html.Div([
            html.H5("P&L Promedio"),
            html.P(f"${avg_pnl:+.2f}")
        ], className="metric-card"),
        
        html.Div([
            html.H5("Mejor Trade"),
            html.P(f"${max_win:+.2f}")
        ], className="metric-card"),
        
        html.Div([
            html.H5("Peor Trade"),
            html.P(f"${max_loss:+.2f}")
        ], className="metric-card")
    ], className="metrics-grid")

def create_returns_distribution_chart(df_trades):
    """Crea gráfico de distribución de retornos"""
    fig = go.Figure()
    
    if df_trades.empty:
        fig.add_annotation(text="No hay datos de trades", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Histograma de P&L
    fig.add_trace(go.Histogram(
        x=df_trades['pnl'],
        nbinsx=20,
        name='Distribución P&L',
        marker_color='#00ff88',
        opacity=0.7
    ))
    
    fig.update_layout(
        title="Distribución de Retornos",
        xaxis_title="P&L ($)",
        yaxis_title="Frecuencia",
        template="plotly_dark"
    )
    
    return fig

def create_drawdown_chart(df_trades):
    """Crea gráfico de drawdown"""
    fig = go.Figure()
    
    if df_trades.empty:
        fig.add_annotation(text="No hay datos de trades", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Calcular drawdown acumulado
    cumulative_pnl = df_trades['pnl'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max
    
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df_trades['entry_time']),
        y=drawdown,
        mode='lines',
        name='Drawdown',
        line=dict(color='#ff4444', width=2),
        fill='tonexty'
    ))
    
    fig.update_layout(
        title="Drawdown",
        xaxis_title="Fecha",
        yaxis_title="Drawdown ($)",
        template="plotly_dark"
    )
    
    return fig

# Funciones helper para datos de muestra
def create_sample_market_data(symbol, start_date=None, end_date=None):
    """Crea datos de mercado de muestra"""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now()
    
    dates = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    # Simular datos de precio con tendencia
    base_price = 45000 if symbol == 'BTCUSDT' else 2500
    prices = []
    current_price = base_price
    
    for _ in dates:
        change = np.random.normal(0, 100)
        current_price += change
        prices.append(current_price)
    
    market_data = pd.DataFrame({
        'open': prices,
        'high': [p + np.random.uniform(0, 200) for p in prices],
        'low': [p - np.random.uniform(0, 200) for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000, 5000, len(dates))
    }, index=dates)
    
    return market_data

def create_sample_trades_data(symbol, start_date=None, end_date=None):
    """Crea datos de trades de muestra"""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now()
    
    np.random.seed(42)
    n_trades = 38  # Basado en el dashboard actual
    
    trades = []
    for i in range(n_trades):
        entry_time = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days))
        exit_time = entry_time + timedelta(hours=np.random.randint(1, 48))
        
        # Simular trades con win rate 0% (problema actual)
        pnl = np.random.normal(-50, 20)  # Trades perdedores
        
        trades.append({
            'trade_id': f'trade_{i+1}',
            'symbol': symbol,
            'side': np.random.choice(['BUY', 'SELL']),
            'entry_price': 45000 + np.random.normal(0, 1000),
            'exit_price': 45000 + np.random.normal(0, 1000),
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': pnl,
            'confidence': np.random.uniform(0.6, 0.8)
        })
    
    return pd.DataFrame(trades)
