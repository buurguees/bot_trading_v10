"""
monitoring/callbacks/trading_callbacks.py
Callbacks específicos para la página de trading
"""

from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def register_trading_callbacks(app, data_provider, chart_components):
    """Registra callbacks para la página de trading"""
    
    # Callback para gráfico de precios con señales
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
        """Actualiza el gráfico de precios con señales de trading"""
        try:
            # Calcular fechas basadas en el rango
            end_date = datetime.now()
            
            if range_period == '24h':
                start_date = end_date - timedelta(hours=24)
            elif range_period == '7d':
                start_date = end_date - timedelta(days=7)
            elif range_period == '30d':
                start_date = end_date - timedelta(days=30)
            elif range_period == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(hours=24)
            
            # Generar datos de precios simulados
            if timeframe == '1h':
                freq = 'H'
            elif timeframe == '4h':
                freq = '4H'
            elif timeframe == '1d':
                freq = 'D'
            elif timeframe == '1w':
                freq = 'W'
            else:
                freq = 'H'
            
            dates = pd.date_range(start=start_date, end=end_date, freq=freq)
            
            # Generar datos OHLCV simulados
            price_data = []
            base_price = 110000 if symbol == 'BTCUSDT' else 3400 if symbol == 'ETHUSDT' else 0.52 if symbol == 'ADAUSDT' else 200
            
            for i, date in enumerate(dates):
                # Simular variación de precios
                price_change = (i * 0.001) + (i % 24) * 0.0005
                current_price = base_price * (1 + price_change)
                
                # Generar OHLCV
                high = current_price * (1 + abs(price_change) * 0.5)
                low = current_price * (1 - abs(price_change) * 0.3)
                open_price = current_price * (1 + price_change * 0.1)
                close_price = current_price
                volume = 1000 + (i % 100) * 10
                
                price_data.append({
                    'timestamp': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volume
                })
            
            df_prices = pd.DataFrame(price_data)
            
            # Crear gráfico de candlesticks
            fig = go.Figure()
            
            # Candlesticks
            fig.add_trace(go.Candlestick(
                x=df_prices['timestamp'],
                open=df_prices['open'],
                high=df_prices['high'],
                low=df_prices['low'],
                close=df_prices['close'],
                name=symbol,
                increasing_line_color='#00ff88',
                decreasing_line_color='#ff4444'
            ))
            
            # Señales de trading simuladas
            buy_signals = df_prices[df_prices.index % 10 == 0].copy()
            sell_signals = df_prices[df_prices.index % 15 == 5].copy()
            
            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals['timestamp'],
                    y=buy_signals['low'] * 0.995,
                    mode='markers',
                    name='Señales BUY',
                    marker=dict(
                        symbol='triangle-up',
                        size=12,
                        color='#00ff88',
                        line=dict(width=2, color='#ffffff')
                    )
                ))
            
            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals['timestamp'],
                    y=sell_signals['high'] * 1.005,
                    mode='markers',
                    name='Señales SELL',
                    marker=dict(
                        symbol='triangle-down',
                        size=12,
                        color='#ff4444',
                        line=dict(width=2, color='#ffffff')
                    )
                ))
            
            fig.update_layout(
                title=f"Análisis de Trading - {symbol}",
                xaxis_title="Tiempo",
                yaxis_title="Precio ($)",
                template="plotly_dark",
                height=500,
                showlegend=True,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            # Información del período
            period_info = f"Período: {start_date.strftime('%Y-%m-%d %H:%M')} a {end_date.strftime('%Y-%m-%d %H:%M')} | {len(df_prices)} velas"
            
            return fig, period_info
            
        except Exception as e:
            logger.error(f"Error actualizando gráfico de trading: {e}")
            return go.Figure(), "Error cargando datos"
    
    # Callback para métricas de trading
    @app.callback(
        [Output('win-rate', 'children'),
         Output('profit-factor', 'children'),
         Output('max-drawdown', 'children'),
         Output('sharpe-ratio', 'children')],
        [Input('dashboard-data', 'data')]
    )
    def update_trading_metrics(data):
        """Actualiza las métricas de trading"""
        try:
            if not data:
                return "0%", "0.00", "0%", "0.00"
            
            # Generar métricas simuladas
            win_rate = "68.5%"
            profit_factor = "1.85"
            max_drawdown = "12.3%"
            sharpe_ratio = "1.42"
            
            return win_rate, profit_factor, max_drawdown, sharpe_ratio
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de trading: {e}")
            return "0%", "0.00", "0%", "0.00"
    
    # Callback para estado del modelo
    @app.callback(
        [Output('avg-confidence', 'children'),
         Output('model-accuracy', 'children'),
         Output('last-update', 'children'),
         Output('model-status', 'children')],
        [Input('dashboard-data', 'data')]
    )
    def update_model_status(data):
        """Actualiza el estado del modelo"""
        try:
            if not data:
                return "0%", "0%", "N/A", "Inactivo"
            
            # Generar datos de estado del modelo
            avg_confidence = "78.5%"
            model_accuracy = "72.3%"
            last_update = datetime.now().strftime("%H:%M:%S")
            model_status = "Activo"
            
            return avg_confidence, model_accuracy, last_update, model_status
            
        except Exception as e:
            logger.error(f"Error actualizando estado del modelo: {e}")
            return "0%", "0%", "N/A", "Error"
    
    # Callback para historial de trades recientes
    @app.callback(
        Output('recent-trades-table', 'children'),
        [Input('dashboard-data', 'data')]
    )
    def update_recent_trades(data):
        """Actualiza la tabla de trades recientes"""
        try:
            if not data:
                return html.Div("No hay trades recientes", style={'color': '#cccccc'})
            
            # Generar datos de ejemplo para trades recientes
            trades_data = [
                {'Tiempo': '14:32', 'Símbolo': 'BTCUSDT', 'Tipo': 'BUY', 'Cantidad': '0.05', 'Precio': '$110,250', 'PnL': '+$125.50', 'Estado': 'Completado'},
                {'Tiempo': '14:28', 'Símbolo': 'ETHUSDT', 'Tipo': 'SELL', 'Cantidad': '0.8', 'Precio': '$3,450', 'PnL': '-$45.20', 'Estado': 'Completado'},
                {'Tiempo': '14:25', 'Símbolo': 'ADAUSDT', 'Tipo': 'BUY', 'Cantidad': '500', 'Precio': '$0.52', 'PnL': '+$12.80', 'Estado': 'Completado'},
                {'Tiempo': '14:20', 'Símbolo': 'SOLUSDT', 'Tipo': 'SELL', 'Cantidad': '10', 'Precio': '$200', 'PnL': '+$25.30', 'Estado': 'Completado'}
            ]
            
            if not trades_data:
                return html.Div("No hay trades recientes", style={'color': '#cccccc'})
            
            return html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Tiempo", style={'color': '#00ff88'}),
                        html.Th("Símbolo", style={'color': '#00ff88'}),
                        html.Th("Tipo", style={'color': '#00ff88'}),
                        html.Th("Cantidad", style={'color': '#00ff88'}),
                        html.Th("Precio", style={'color': '#00ff88'}),
                        html.Th("PnL", style={'color': '#00ff88'}),
                        html.Th("Estado", style={'color': '#00ff88'})
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(trade['Tiempo']),
                        html.Td(trade['Símbolo']),
                        html.Td(trade['Tipo'], style={'color': '#00ff88' if trade['Tipo'] == 'BUY' else '#ff4444'}),
                        html.Td(trade['Cantidad']),
                        html.Td(trade['Precio']),
                        html.Td(trade['PnL'], style={'color': '#00ff88' if '+' in trade['PnL'] else '#ff4444'}),
                        html.Td(trade['Estado'], style={'color': '#00ff88' if trade['Estado'] == 'Completado' else '#ffaa00'})
                    ]) for trade in trades_data
                ])
            ], style={'width': '100%', 'color': '#ffffff'})
            
        except Exception as e:
            logger.error(f"Error actualizando trades recientes: {e}")
            return html.Div("Error cargando trades", style={'color': '#ff4444'})
