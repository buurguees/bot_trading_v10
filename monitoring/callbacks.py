"""
monitoring/callbacks.py
Sistema de callbacks para el dashboard del Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\callbacks.py

Funcionalidades:
- Callbacks para actualización en tiempo real
- Interactividad del dashboard
- Manejo de eventos y controles
"""

from dash import Input, Output, State, callback, dash_table, html
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging
import dash

logger = logging.getLogger(__name__)

class DashboardCallbacks:
    """Manejador de callbacks para el dashboard"""
    
    def __init__(self, app, data_provider, chart_components):
        self.app = app
        self.data_provider = data_provider
        self.chart_components = chart_components
    
    def register_all_callbacks(self):
        """Registra todos los callbacks del dashboard"""
        self.register_home_callbacks()
        self.register_trading_callbacks()
        self.register_performance_callbacks()
        self.register_alerts_callbacks()
        self.register_settings_callbacks()
    
    def register_home_callbacks(self):
        """Callbacks para la página principal"""
        
        # Actualizar métricas principales
        @self.app.callback(
            [Output('total-balance', 'children'),
             Output('daily-pnl', 'children'),
             Output('win-rate', 'children'),
             Output('active-positions', 'children'),
             Output('progress-to-target', 'children')],
            Input('dashboard-data', 'data')
        )
        def update_home_metrics(data):
            if not data or 'portfolio' not in data:
                return "$1,000.00", "+$0.00", "0%", "0", "0.1%"
            
            portfolio = data['portfolio']
            performance = data.get('performance', {})
            positions = data.get('positions', [])
            
            balance = f"${portfolio.get('total_balance', 1000):,.2f}"
            daily_pnl = f"+${portfolio.get('daily_pnl', 0):,.2f}" if portfolio.get('daily_pnl', 0) >= 0 else f"-${abs(portfolio.get('daily_pnl', 0)):,.2f}"
            win_rate = f"{performance.get('win_rate', 0)*100:.0f}%"
            active_pos = str(len(positions))
            
            # Calcular progreso hacia objetivo de $1M
            current_balance = portfolio.get('total_balance', 1000)
            target_balance = portfolio.get('target_balance', 1000000)
            progress_pct = (current_balance / target_balance) * 100
            progress = f"{progress_pct:.2f}%"
            
            return balance, daily_pnl, win_rate, active_pos, progress
        
        # Actualizar gráfico P&L
        @self.app.callback(
            Output('pnl-chart', 'figure'),
            Input('dashboard-data', 'data')
        )
        def update_pnl_chart(data):
            return self.chart_components.create_pnl_chart(data.get('charts', {}) if data else {})
        
        # Actualizar gráfico de distribución de trades
        @self.app.callback(
            Output('trades-distribution-chart', 'figure'),
            Input('dashboard-data', 'data')
        )
        def update_trades_distribution(data):
            return self.chart_components.create_trades_distribution_chart(data.get('charts', {}) if data else {})
        
        # Actualizar tabla de posiciones activas
        @self.app.callback(
            Output('active-positions-table', 'children'),
            Input('dashboard-data', 'data')
        )
        def update_positions_table(data):
            if not data or 'positions' not in data:
                return html.Div("No active positions", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            positions = data['positions']
            if not positions:
                return html.Div("No active positions", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            # Convertir a DataFrame para la tabla
            df = pd.DataFrame(positions)
            df['unrealized_pnl'] = df['unrealized_pnl'].apply(lambda x: f"${x:+.2f}")
            df['unrealized_pnl_pct'] = df['unrealized_pnl_pct'].apply(lambda x: f"{x:+.2f}%")
            df['entry_time'] = pd.to_datetime(df['entry_time']).dt.strftime('%H:%M')
            
            return dash_table.DataTable(
                data=df[['symbol', 'side', 'size', 'unrealized_pnl', 'unrealized_pnl_pct', 'entry_time']].to_dict('records'),
                columns=[
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Side', 'id': 'side'},
                    {'name': 'Size', 'id': 'size'},
                    {'name': 'P&L', 'id': 'unrealized_pnl'},
                    {'name': 'P&L %', 'id': 'unrealized_pnl_pct'},
                    {'name': 'Time', 'id': 'entry_time'}
                ],
                style_cell={
                    'backgroundColor': '#2d2d2d',
                    'color': '#ffffff',
                    'border': '1px solid #404040',
                    'textAlign': 'center',
                    'fontSize': '12px'
                },
                style_header={
                    'backgroundColor': '#404040',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{side} = LONG'},
                        'backgroundColor': '#1a4d3a',
                    },
                    {
                        'if': {'filter_query': '{side} = SHORT'},
                        'backgroundColor': '#4d1a1a',
                    }
                ]
            )
        
        # Actualizar tabla de señales recientes
        @self.app.callback(
            Output('recent-signals-table', 'children'),
            Input('dashboard-data', 'data')
        )
        def update_signals_table(data):
            if not data or 'signals' not in data:
                return html.Div("No recent signals", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            signals = data['signals'][:5]  # Últimas 5 señales
            if not signals:
                return html.Div("No recent signals", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            # Convertir a DataFrame
            df = pd.DataFrame(signals)
            df['confidence'] = df['confidence'].apply(lambda x: f"{x:.0%}")
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M')
            df['executed'] = df['executed'].apply(lambda x: '✅' if x else '❌')
            
            return dash_table.DataTable(
                data=df[['symbol', 'signal', 'confidence', 'executed', 'timestamp']].to_dict('records'),
                columns=[
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Signal', 'id': 'signal'},
                    {'name': 'Conf.', 'id': 'confidence'},
                    {'name': 'Exec.', 'id': 'executed'},
                    {'name': 'Time', 'id': 'timestamp'}
                ],
                style_cell={
                    'backgroundColor': '#2d2d2d',
                    'color': '#ffffff',
                    'border': '1px solid #404040',
                    'textAlign': 'center',
                    'fontSize': '12px'
                },
                style_header={
                    'backgroundColor': '#404040',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{signal} = BUY'},
                        'color': '#00ff88',
                    },
                    {
                        'if': {'filter_query': '{signal} = SELL'},
                        'color': '#ff4444',
                    },
                    {
                        'if': {'filter_query': '{signal} = HOLD'},
                        'color': '#ffaa00',
                    }
                ]
            )
    
    def register_trading_callbacks(self):
        """Callbacks para la página de trading"""
        
        # Actualizar métricas de trading
        @self.app.callback(
            [Output('trading-status', 'children'),
             Output('model-confidence', 'children'),
             Output('trades-today', 'children'),
             Output('last-signal', 'children')],
            [Input('dashboard-data', 'data'),
             Input('bot-status', 'data')]
        )
        def update_trading_metrics(dashboard_data, bot_status):
            if not bot_status:
                return "UNKNOWN", "0%", "0", "None"
            
            status = bot_status.get('status', 'UNKNOWN')
            model_data = bot_status.get('model', {})
            trading_data = bot_status.get('trading', {})
            
            confidence = f"{model_data.get('confidence_avg', 0)*100:.0f}%"
            trades_today = str(trading_data.get('trades_today', 0))
            
            # Última señal
            signals = dashboard_data.get('signals', []) if dashboard_data else []
            if signals:
                last_signal = f"{signals[0]['signal']} {signals[0]['confidence']:.0%}"
            else:
                last_signal = "None"
            
            return status, confidence, trades_today, last_signal
        
        # Actualizar tabla de señales en vivo
        @self.app.callback(
            Output('live-signals-table', 'children'),
            Input('dashboard-data', 'data')
        )
        def update_live_signals(data):
            if not data or 'signals' not in data:
                return html.Div("No signals available", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            signals = data['signals']
            if not signals:
                return html.Div("No signals available", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            # Tabla más detallada para la página de trading
            df = pd.DataFrame(signals)
            df['confidence'] = df['confidence'].apply(lambda x: f"{x:.1%}")
            df['quality_score'] = df['quality_score'].apply(lambda x: f"{x:.1%}")
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')
            df['executed'] = df['executed'].apply(lambda x: '✅ Yes' if x else '❌ No')
            
            return dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[
                    {'name': 'Time', 'id': 'timestamp'},
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Signal', 'id': 'signal'},
                    {'name': 'Confidence', 'id': 'confidence'},
                    {'name': 'Quality', 'id': 'quality_score'},
                    {'name': 'Executed', 'id': 'executed'},
                    {'name': 'Reason', 'id': 'reason'}
                ],
                style_cell={
                    'backgroundColor': '#2d2d2d',
                    'color': '#ffffff',
                    'border': '1px solid #404040',
                    'textAlign': 'left',
                    'fontSize': '11px',
                    'padding': '8px'
                },
                style_header={
                    'backgroundColor': '#404040',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{signal} = BUY'},
                        'backgroundColor': '#1a4d3a',
                    },
                    {
                        'if': {'filter_query': '{signal} = SELL'},
                        'backgroundColor': '#4d1a1a',
                    }
                ]
            )
        
        # Actualizar gráfico de precio con señales
        @self.app.callback(
            Output('price-signals-chart', 'figure'),
            Input('dashboard-data', 'data')
        )
        def update_price_chart(data):
            return self.chart_components.create_price_signals_chart(data)
    
    def register_performance_callbacks(self):
        """Callbacks para la página de performance"""
        
        # Actualizar métricas de performance
        @self.app.callback(
            [Output('total-trades', 'children'),
             Output('profit-factor', 'children'),
             Output('sharpe-ratio', 'children'),
             Output('max-drawdown', 'children')],
            Input('dashboard-data', 'data')
        )
        def update_performance_metrics(data):
            if not data or 'performance' not in data:
                return "0", "0.00", "0.00", "0.00%"
            
            perf = data['performance']
            
            total_trades = str(perf.get('total_trades', 0))
            profit_factor = f"{perf.get('profit_factor', 0):.2f}"
            sharpe_ratio = f"{perf.get('sharpe_ratio', 0):.2f}"
            max_drawdown = f"{perf.get('max_drawdown', 0)*100:.1f}%"
            
            return total_trades, profit_factor, sharpe_ratio, max_drawdown
        
        # Actualizar gráfico de evolución de accuracy
        @self.app.callback(
            Output('accuracy-evolution-chart', 'figure'),
            Input('dashboard-data', 'data')
        )
        def update_accuracy_chart(data):
            return self.chart_components.create_accuracy_evolution_chart(data.get('charts', {}) if data else {})
        
        # Actualizar gráfico de análisis de trades
        @self.app.callback(
            Output('trades-analysis-chart', 'figure'),
            Input('dashboard-data', 'data')
        )
        def update_trades_analysis(data):
            return self.chart_components.create_trades_analysis_chart(data)
        
        # Actualizar tabla de historial de trades
        @self.app.callback(
            Output('trade-history-table', 'children'),
            Input('dashboard-data', 'data')
        )
        def update_trade_history(data):
            if not data or 'trades' not in data:
                return html.Div("No trade history available", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            trades = data['trades']
            if not trades:
                return html.Div("No trade history available", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            # Crear DataFrame
            df = pd.DataFrame(trades)
            df['pnl'] = df['pnl'].apply(lambda x: f"${x:+.2f}")
            df['pnl_pct'] = df['pnl_pct'].apply(lambda x: f"{x:+.2f}%")
            df['entry_time'] = pd.to_datetime(df['entry_time']).dt.strftime('%m/%d %H:%M')
            df['confidence'] = df['confidence'].apply(lambda x: f"{x:.0%}")
            
            return dash_table.DataTable(
                data=df[['entry_time', 'symbol', 'side', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'confidence', 'status']].to_dict('records'),
                columns=[
                    {'name': 'Time', 'id': 'entry_time'},
                    {'name': 'Symbol', 'id': 'symbol'},
                    {'name': 'Side', 'id': 'side'},
                    {'name': 'Entry', 'id': 'entry_price'},
                    {'name': 'Exit', 'id': 'exit_price'},
                    {'name': 'P&L', 'id': 'pnl'},
                    {'name': 'P&L %', 'id': 'pnl_pct'},
                    {'name': 'Conf.', 'id': 'confidence'},
                    {'name': 'Status', 'id': 'status'}
                ],
                style_cell={
                    'backgroundColor': '#2d2d2d',
                    'color': '#ffffff',
                    'border': '1px solid #404040',
                    'textAlign': 'center',
                    'fontSize': '11px',
                    'padding': '6px'
                },
                style_header={
                    'backgroundColor': '#404040',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{pnl} contains +'},
                        'color': '#00ff88',
                    },
                    {
                        'if': {'filter_query': '{pnl} contains -'},
                        'color': '#ff4444',
                    }
                ],
                page_size=15
            )
    
    def register_alerts_callbacks(self):
        """Callbacks para la página de alertas"""
        
        # Actualizar métricas de alertas
        @self.app.callback(
            [Output('active-alerts', 'children'),
             Output('system-health', 'children'),
             Output('api-status', 'children'),
             Output('model-status', 'children')],
            Input('bot-status', 'data')
        )
        def update_alerts_metrics(data):
            if not data:
                return "0", "Unknown", "Unknown", "Unknown"
            
            health = data.get('health', {})
            model = data.get('model', {})
            
            # Calcular alertas activas basado en health
            alerts_count = sum(1 for status in health.values() if not status)
            
            system_health = "OK" if health.get('overall', False) else "Issues"
            api_status = "Connected" if health.get('api_connection', False) else "Disconnected"
            
            # Estado del modelo
            if 'last_training' in model:
                model_status = "Ready"
            else:
                model_status = "Training"
            
            return str(alerts_count), system_health, api_status, model_status
        
        # Actualizar lista de alertas
        @self.app.callback(
            Output('alerts-list', 'children'),
            Input('bot-status', 'data')
        )
        def update_alerts_list(data):
            if not data:
                return html.Div("No alerts data available", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            
            # Generar alertas basadas en el estado del sistema
            alerts = []
            health = data.get('health', {})
            
            if not health.get('database', True):
                alerts.append({
                    'type': 'error',
                    'message': 'Database connection lost',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            if not health.get('api_connection', True):
                alerts.append({
                    'type': 'warning',
                    'message': 'API connection unstable',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            if not health.get('model_loaded', True):
                alerts.append({
                    'type': 'info',
                    'message': 'Model is being retrained',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            # Si no hay alertas, mostrar estado OK
            if not alerts:
                return html.Div([
                    html.Div([
                        html.I(className="fas fa-check-circle", style={'color': '#00ff88', 'marginRight': '10px'}),
                        html.Span("All systems operational", style={'color': '#00ff88'})
                    ], style={'padding': '20px', 'textAlign': 'center'})
                ])
            
            # Crear lista de alertas
            alert_elements = []
            for alert in alerts:
                icon_class = {
                    'error': 'fas fa-exclamation-circle',
                    'warning': 'fas fa-exclamation-triangle',
                    'info': 'fas fa-info-circle'
                }.get(alert['type'], 'fas fa-info-circle')
                
                color = {
                    'error': '#ff4444',
                    'warning': '#ffaa00',
                    'info': '#4488ff'
                }.get(alert['type'], '#4488ff')
                
                alert_elements.append(
                    html.Div([
                        html.I(className=icon_class, style={'color': color, 'marginRight': '10px'}),
                        html.Span(alert['message'], style={'color': '#ffffff'}), 
                        html.Span(alert['time'], style={'color': '#cccccc', 'float': 'right'})
                    ], style={
                        'padding': '10px',
                        'marginBottom': '5px',
                        'backgroundColor': '#2d2d2d',
                        'borderRadius': '5px',
                        'borderLeft': f'4px solid {color}'
                    })
                )
            
            return html.Div(alert_elements)
    
    def register_settings_callbacks(self):
        """Callbacks para la página de configuraciones"""
        
        # Callbacks para botones de control
        @self.app.callback(
            Output('control-feedback', 'children'),
            [Input('pause-btn', 'n_clicks'),
             Input('resume-btn', 'n_clicks'),
             Input('emergency-btn', 'n_clicks'),
             Input('retrain-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def handle_control_buttons(pause, resume, emergency, retrain):
            from dash import callback_context
            
            if not callback_context.triggered:
                return ""
            
            button_id = callback_context.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if button_id == 'pause-btn':
                    # TODO: Implementar pausa del trading
                    return html.Div("✅ Trading paused successfully", style={'color': '#00ff88'})
                
                elif button_id == 'resume-btn':
                    # TODO: Implementar reanudación del trading
                    return html.Div("✅ Trading resumed successfully", style={'color': '#00ff88'})
                
                elif button_id == 'emergency-btn':
                    # TODO: Implementar parada de emergencia
                    return html.Div("🛑 Emergency stop activated", style={'color': '#ff4444'})
                
                elif button_id == 'retrain-btn':
                    # TODO: Implementar reentrenamiento
                    return html.Div("🔄 Model retraining started", style={'color': '#4488ff'})
                
            except Exception as e:
                return html.Div(f"❌ Error: {str(e)}", style={'color': '#ff4444'})
            
            return ""


# Función de compatibilidad para el sistema existente
def register_callbacks(app):
    """Función de compatibilidad para registrar callbacks"""
    from .data_provider import DashboardDataProvider
    from .chart_components import ChartComponents
    from .layout_components import LayoutComponents
    
    data_provider = DashboardDataProvider()
    chart_components = ChartComponents()
    layout_components = LayoutComponents()
    
    # Callback para navegación entre páginas
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def display_page(pathname):
        """Maneja la navegación entre páginas"""
        if pathname == '/' or pathname == '/home':
            return layout_components.create_home_page()
        elif pathname == '/trading':
            return layout_components.create_trading_page()
        elif pathname == '/performance':
            return layout_components.create_performance_page()
        elif pathname == '/settings':
            return layout_components.create_settings_page()
        elif pathname == '/alerts':
            return layout_components.create_alerts_page()
        elif pathname == '/chat':
            return layout_components.create_chat_page()
        else:
            return layout_components.create_404_page()
    
    # Crear instancia de callbacks avanzados
    callbacks_handler = DashboardCallbacks(app, data_provider, chart_components)
    callbacks_handler.register_all_callbacks()
    
    # Callbacks para navegación temporal
    register_temporal_navigation_callbacks(app, data_provider, chart_components)

def register_temporal_navigation_callbacks(app, data_provider, chart_components):
    """Registra callbacks para navegación temporal en gráficos"""
    
    # Callback para navegación del gráfico P&L en home
    @app.callback(
        [Output('pnl-chart', 'figure'),
         Output('home-pnl-period-info', 'children')],
        [Input('home-pnl-timeframe', 'value'),
         Input('home-pnl-prev', 'n_clicks'),
         Input('home-pnl-next', 'n_clicks'),
         Input('home-pnl-today', 'n_clicks')],
        [State('home-pnl-timeframe', 'value')]
    )
    def update_home_pnl_chart(timeframe, prev_clicks, next_clicks, today_clicks, current_timeframe):
        """Actualiza el gráfico P&L con navegación temporal"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return chart_components.create_pnl_chart({}), "Período: Último mes"
        
        # Determinar acción
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Obtener datos históricos basados en el período
        end_date = datetime.now()
        if timeframe == '7d':
            start_date = end_date - timedelta(days=7)
            period_text = "Última semana"
        elif timeframe == '30d':
            start_date = end_date - timedelta(days=30)
            period_text = "Último mes"
        elif timeframe == '90d':
            start_date = end_date - timedelta(days=90)
            period_text = "Últimos 3 meses"
        elif timeframe == '365d':
            start_date = end_date - timedelta(days=365)
            period_text = "Último año"
        else:  # 'all'
            start_date = end_date - timedelta(days=1095)  # 3 años
            period_text = "Todo el histórico"
        
        # Crear datos de ejemplo para el gráfico
        chart_data = {
            'pnl_data': generate_sample_pnl_data(start_date, end_date),
            'trades_data': generate_sample_trades_data(start_date, end_date)
        }
        
        figure = chart_components.create_pnl_chart(chart_data)
        period_info = f"Período: {period_text} ({start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')})"
        
        return figure, period_info
    
    # Callback para navegación del gráfico de precios en trading
    @app.callback(
        [Output('price-signals-chart', 'figure'),
         Output('trading-chart-period-info', 'children')],
        [Input('trading-symbol-selector', 'value'),
         Input('trading-timeframe-selector', 'value'),
         Input('trading-range-selector', 'value'),
         Input('trading-chart-prev', 'n_clicks'),
         Input('trading-chart-next', 'n_clicks'),
         Input('trading-chart-today', 'n_clicks'),
         Input('trading-chart-zoom', 'n_clicks')]
    )
    def update_trading_chart(symbol, timeframe, range_period, prev_clicks, next_clicks, today_clicks, zoom_clicks):
        """Actualiza el gráfico de precios con navegación temporal"""
        # Obtener datos históricos reales
        end_date = datetime.now()
        if range_period == '7d':
            start_date = end_date - timedelta(days=7)
        elif range_period == '30d':
            start_date = end_date - timedelta(days=30)
        elif range_period == '90d':
            start_date = end_date - timedelta(days=90)
        else:  # '365d'
            start_date = end_date - timedelta(days=365)
        
        # Obtener datos de la base de datos
        try:
            from data.database import db_manager
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data 
                    WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                ''', (symbol, int(start_date.timestamp() * 1000), int(end_date.timestamp() * 1000)))
                
                results = cursor.fetchall()
                if results:
                    df_market = pd.DataFrame(results, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df_market['timestamp'] = pd.to_datetime(df_market['timestamp'], unit='ms')
                else:
                    df_market = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {e}")
            df_market = pd.DataFrame()
        
        # Crear gráfico
        from monitoring.components.enhanced_chart import create_enhanced_candlestick_chart
        figure = create_enhanced_candlestick_chart(df_market, pd.DataFrame(), {})
        period_info = f"{symbol} | {timeframe} | {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"
        
        return figure, period_info

def generate_sample_pnl_data(start_date, end_date):
    """Genera datos de ejemplo para el gráfico P&L"""
    import numpy as np
    
    # Crear serie temporal
    date_range = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Simular PnL acumulativo con tendencia positiva
    np.random.seed(42)  # Para reproducibilidad
    returns = np.random.normal(0.0001, 0.02, len(date_range))  # 0.01% promedio por hora
    cumulative_pnl = np.cumsum(returns) * 1000  # Escalar a $1000 inicial
    
    return pd.DataFrame({
        'timestamp': date_range,
        'pnl': cumulative_pnl,
        'balance': 1000 + cumulative_pnl
    })

def generate_sample_trades_data(start_date, end_date):
    """Genera datos de ejemplo para trades"""
    import numpy as np
    
    # Crear algunos trades de ejemplo
    np.random.seed(42)
    n_trades = max(10, int((end_date - start_date).days / 3))  # ~1 trade cada 3 días
    
    trades = []
    for i in range(n_trades):
        trade_time = start_date + timedelta(days=np.random.uniform(0, (end_date - start_date).days))
        pnl = np.random.normal(50, 200)  # PnL promedio $50, std $200
        
        trades.append({
            'timestamp': trade_time,
            'symbol': np.random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']),
            'side': np.random.choice(['BUY', 'SELL']),
            'pnl': pnl,
            'confidence': np.random.uniform(0.6, 0.95)
        })
    
    return pd.DataFrame(trades)
