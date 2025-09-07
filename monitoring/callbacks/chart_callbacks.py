"""
monitoring/callbacks/chart_callbacks.py
Callbacks específicos para gráficos y visualizaciones
"""

from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def register_chart_callbacks(app, data_provider, chart_components):
    """Registra callbacks para gráficos y visualizaciones"""
    
    # Callback para navegación temporal del gráfico P&L
    @app.callback(
        [Output('pnl-chart', 'figure'), Output('home-pnl-period-info', 'children')],
        [Input('home-pnl-timeframe', 'value'), Input('home-pnl-prev', 'n_clicks'), Input('home-pnl-next', 'n_clicks'), Input('home-pnl-today', 'n_clicks')],
        [State('home-pnl-timeframe', 'value')]
    )
    def update_home_pnl_chart(timeframe, prev_clicks, next_clicks, today_clicks, current_timeframe):
        """Actualiza el gráfico P&L con navegación temporal"""
        try:
            # Generar datos de ejemplo para P&L
            end_date = datetime.now()
            
            if timeframe == '7d':
                start_date = end_date - timedelta(days=7)
            elif timeframe == '30d':
                start_date = end_date - timedelta(days=30)
            elif timeframe == '90d':
                start_date = end_date - timedelta(days=90)
            elif timeframe == '1y':
                start_date = end_date - timedelta(days=365)
            else:  # 'all'
                start_date = end_date - timedelta(days=365)
            
            # Generar datos de P&L simulados
            dates = pd.date_range(start=start_date, end=end_date, freq='H')
            pnl_data = []
            cumulative_pnl = 0
            
            for i, date in enumerate(dates):
                # Simular variación de P&L
                daily_change = (i * 0.1) + (i % 24) * 0.05 + (i % 7) * 0.2
                cumulative_pnl += daily_change
                pnl_data.append({
                    'timestamp': date,
                    'pnl': cumulative_pnl,
                    'daily_pnl': daily_change
                })
            
            df_pnl = pd.DataFrame(pnl_data)
            
            # Crear gráfico
            fig = go.Figure()
            
            # Línea de P&L acumulado
            fig.add_trace(go.Scatter(
                x=df_pnl['timestamp'],
                y=df_pnl['pnl'],
                mode='lines',
                name='P&L Acumulado',
                line=dict(color='#00ff88', width=2),
                fill='tonexty'
            ))
            
            # Línea de P&L diario
            fig.add_trace(go.Scatter(
                x=df_pnl['timestamp'],
                y=df_pnl['daily_pnl'],
                mode='lines',
                name='P&L Diario',
                line=dict(color='#4488ff', width=1),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title="Análisis de P&L Histórico",
                xaxis_title="Fecha",
                yaxis_title="P&L Acumulado ($)",
                yaxis2=dict(title="P&L Diario ($)", overlaying="y", side="right"),
                template="plotly_dark",
                height=400,
                showlegend=True,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            # Información del período
            period_info = f"Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')} | {len(df_pnl)} puntos de datos"
            
            return fig, period_info
            
        except Exception as e:
            logger.error(f"Error actualizando gráfico P&L: {e}")
            return go.Figure(), "Error cargando datos"
    
    # Callback para gráfico de precios con señales
    @app.callback(
        [Output('price-signals-chart', 'figure'), Output('trading-chart-period-info', 'children')],
        [Input('trading-symbol-selector', 'value'), Input('trading-timeframe-selector', 'value'), Input('trading-range-selector', 'value'), Input('trading-chart-prev', 'n_clicks'), Input('trading-chart-next', 'n_clicks'), Input('trading-chart-today', 'n_clicks'), Input('trading-chart-zoom', 'n_clicks')]
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
    
    # Callback para widget de ciclos
    @app.callback(
        [Output('top-cycles-table', 'data'),
         Output('cycles-performance-chart', 'figure'),
         Output('cycles-summary-stats', 'children')],
        [Input('cycles-sort-metric', 'value'),
         Input('cycles-symbol-filter', 'value'),
         Input('refresh-cycles-btn', 'n_clicks')]
    )
    def update_cycles_data(sort_metric, symbol_filter, refresh_clicks):
        """Actualiza los datos del widget de ciclos"""
        try:
            from monitoring.components.widgets.top_cycles_widget import TopCyclesWidget
            from monitoring.core.cycle_tracker import cycle_tracker
            
            cycles_widget = TopCyclesWidget()
            
            # Obtener ciclos del tracker
            cycles = cycle_tracker.get_top_cycles(limit=10, metric=sort_metric)
            
            # Filtrar por símbolo si no es 'all'
            if symbol_filter != 'all':
                cycles = [c for c in cycles if c.symbol == symbol_filter]
            
            # Convertir a datos de tabla
            table_data = []
            for i, cycle in enumerate(cycles):
                table_data.append({
                    'rank': i + 1,
                    'cycle_id': cycle.cycle_id.split('_')[-1],  # Solo la parte final del ID
                    'symbol': cycle.symbol,
                    'date': cycle.start_time.strftime('%Y-%m-%d'),
                    'daily_pnl': cycle.daily_pnl,
                    'pnl_pct': cycle.pnl_percentage,
                    'progress': cycle.progress_to_target,
                    'trades': cycle.trades_count,
                    'win_rate': cycle.win_rate,
                    'sharpe': cycle.sharpe_ratio
                })
            
            # Crear gráfico de rendimiento
            chart_figure = cycles_widget.create_cycles_performance_chart(table_data)
            
            # Obtener estadísticas resumen
            stats = cycle_tracker.get_cycle_statistics()
            summary_stats = cycles_widget.create_cycles_summary_stats(stats)
            
            return table_data, chart_figure, summary_stats
            
        except Exception as e:
            logger.error(f"Error actualizando datos de ciclos: {e}")
            return [], go.Figure(), html.Div("Error cargando datos", style={'color': 'red'})
