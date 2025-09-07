"""
monitoring/callbacks/home_callbacks.py
Callbacks específicos para la página principal
"""

from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def register_home_callbacks(app, data_provider, chart_components):
    """Registra callbacks para la página principal"""
    
    # Callback para métricas principales
    @app.callback(
        [Output('total-balance', 'children'),
         Output('daily-pnl', 'children'),
         Output('progress-to-target', 'children'),
         Output('trades-today', 'children')],
        [Input('dashboard-data', 'data')]
    )
    def update_home_metrics(data):
        """Actualiza las métricas principales de la página home"""
        try:
            if not data:
                return "$0.00", "$0.00", "0.00%", "0"
            
            portfolio = data.get('portfolio', {})
            
            total_balance = f"${portfolio.get('total_balance', 0):,.2f}"
            daily_pnl = f"${portfolio.get('daily_pnl', 0):,.2f}"
            progress = f"{portfolio.get('progress_to_target', 0):.2f}%"
            trades = str(portfolio.get('trades_count', 0))
            
            return total_balance, daily_pnl, progress, trades
            
        except Exception as e:
            logger.error(f"Error actualizando métricas home: {e}")
            return "$0.00", "$0.00", "0.00%", "0"
    
    # Callback para gráfico P&L con navegación
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
        """Actualiza el gráfico P&L de la página home"""
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
            logger.error(f"Error actualizando gráfico P&L home: {e}")
            return go.Figure(), "Error cargando datos"
    
    # Callback para distribución de trades
    @app.callback(
        Output('trades-distribution-chart', 'figure'),
        [Input('dashboard-data', 'data')]
    )
    def update_trades_distribution(data):
        """Actualiza el gráfico de distribución de trades"""
        try:
            if not data:
                return go.Figure()
            
            # Generar datos de ejemplo para distribución de trades
            trades_data = {
                'Símbolo': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'],
                'Trades': [45, 32, 28, 15],
                'PnL': [1250, 890, 650, 320]
            }
            
            df_trades = pd.DataFrame(trades_data)
            
            fig = go.Figure()
            
            # Gráfico de barras para número de trades
            fig.add_trace(go.Bar(
                x=df_trades['Símbolo'],
                y=df_trades['Trades'],
                name='Número de Trades',
                marker_color='#00ff88',
                yaxis='y'
            ))
            
            # Gráfico de líneas para P&L
            fig.add_trace(go.Scatter(
                x=df_trades['Símbolo'],
                y=df_trades['PnL'],
                mode='lines+markers',
                name='P&L ($)',
                line=dict(color='#4488ff', width=3),
                marker=dict(size=8),
                yaxis='y2'
            ))
            
            fig.update_layout(
                title="Distribución de Trades por Símbolo",
                xaxis_title="Símbolo",
                yaxis_title="Número de Trades",
                yaxis2=dict(title="P&L ($)", overlaying="y", side="right"),
                template="plotly_dark",
                height=400,
                showlegend=True,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error actualizando distribución de trades: {e}")
            return go.Figure()
    
    # Callback para posiciones activas
    @app.callback(
        Output('active-positions-table', 'children'),
        [Input('dashboard-data', 'data')]
    )
    def update_active_positions(data):
        """Actualiza la tabla de posiciones activas"""
        try:
            if not data:
                return html.Div("No hay posiciones activas", style={'color': '#cccccc'})
            
            # Generar datos de ejemplo para posiciones activas
            positions_data = [
                {'Símbolo': 'BTCUSDT', 'Tipo': 'LONG', 'Cantidad': '0.05', 'Precio': '$110,250', 'PnL': '+$125.50'},
                {'Símbolo': 'ETHUSDT', 'Tipo': 'SHORT', 'Cantidad': '0.8', 'Precio': '$3,450', 'PnL': '-$45.20'},
                {'Símbolo': 'ADAUSDT', 'Tipo': 'LONG', 'Cantidad': '500', 'Precio': '$0.52', 'PnL': '+$12.80'}
            ]
            
            if not positions_data:
                return html.Div("No hay posiciones activas", style={'color': '#cccccc'})
            
            return html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Símbolo", style={'color': '#00ff88'}),
                        html.Th("Tipo", style={'color': '#00ff88'}),
                        html.Th("Cantidad", style={'color': '#00ff88'}),
                        html.Th("Precio", style={'color': '#00ff88'}),
                        html.Th("PnL", style={'color': '#00ff88'})
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(pos['Símbolo']),
                        html.Td(pos['Tipo'], style={'color': '#00ff88' if pos['Tipo'] == 'LONG' else '#ff4444'}),
                        html.Td(pos['Cantidad']),
                        html.Td(pos['Precio']),
                        html.Td(pos['PnL'], style={'color': '#00ff88' if '+' in pos['PnL'] else '#ff4444'})
                    ]) for pos in positions_data
                ])
            ], style={'width': '100%', 'color': '#ffffff'})
            
        except Exception as e:
            logger.error(f"Error actualizando posiciones activas: {e}")
            return html.Div("Error cargando posiciones", style={'color': '#ff4444'})
    
    # Callback para señales recientes
    @app.callback(
        Output('recent-signals-table', 'children'),
        [Input('dashboard-data', 'data')]
    )
    def update_recent_signals(data):
        """Actualiza la tabla de señales recientes"""
        try:
            if not data:
                return html.Div("No hay señales recientes", style={'color': '#cccccc'})
            
            # Generar datos de ejemplo para señales recientes
            signals_data = [
                {'Símbolo': 'BTCUSDT', 'Señal': 'BUY', 'Confianza': '85%', 'Precio': '$110,250', 'Tiempo': '2 min'},
                {'Símbolo': 'ETHUSDT', 'Señal': 'SELL', 'Confianza': '78%', 'Precio': '$3,450', 'Tiempo': '5 min'},
                {'Símbolo': 'ADAUSDT', 'Señal': 'BUY', 'Confianza': '92%', 'Precio': '$0.52', 'Tiempo': '8 min'}
            ]
            
            if not signals_data:
                return html.Div("No hay señales recientes", style={'color': '#cccccc'})
            
            return html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Símbolo", style={'color': '#00ff88'}),
                        html.Th("Señal", style={'color': '#00ff88'}),
                        html.Th("Confianza", style={'color': '#00ff88'}),
                        html.Th("Precio", style={'color': '#00ff88'}),
                        html.Th("Tiempo", style={'color': '#00ff88'})
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(signal['Símbolo']),
                        html.Td(signal['Señal'], style={'color': '#00ff88' if signal['Señal'] == 'BUY' else '#ff4444'}),
                        html.Td(signal['Confianza']),
                        html.Td(signal['Precio']),
                        html.Td(signal['Tiempo'])
                    ]) for signal in signals_data
                ])
            ], style={'width': '100%', 'color': '#ffffff'})
            
        except Exception as e:
            logger.error(f"Error actualizando señales recientes: {e}")
            return html.Div("Error cargando señales", style={'color': '#ff4444'})
    
    # Callback para overview de ciclos
    @app.callback(
        Output('cycles-overview-widget-container', 'children'),
        [Input('dashboard-data', 'data')]
    )
    def load_cycles_overview_widget(data):
        """Carga el widget de overview de ciclos"""
        try:
            from monitoring.components.widgets.cycles_overview import CyclesOverviewWidget
            return CyclesOverviewWidget().create_cycles_overview_widget()
        except Exception as e:
            logger.error(f"Error cargando widget de overview de ciclos: {e}")
            return html.Div("Error cargando overview de ciclos", 
                          style={'color': 'red', 'textAlign': 'center'})
    
    # Callback para métricas del overview de ciclos
    @app.callback(
        [Output('avg-final-balance', 'children'),
         Output('avg-daily-pnl', 'children'),
         Output('avg-progress-target', 'children'),
         Output('avg-win-rate', 'children'),
         Output('avg-sharpe-ratio', 'children'),
         Output('total-completed-cycles', 'children')],
        [Input('dashboard-data', 'data')]
    )
    def update_cycles_overview_metrics(data):
        """Actualiza las métricas del overview de ciclos sincronizados"""
        try:
            if not data or 'cycles' not in data:
                return "$0.00", "$0.00", "0.00%", "0.00%", "0.00", "0"
            
            cycles_data = data['cycles'].get('top_cycles', [])
            
            # Calcular promedios de ciclos sincronizados
            if not cycles_data:
                return "$0.00", "$0.00", "0.00%", "0.00%", "0.00", "0"
            
            # Filtrar solo ciclos completados
            completed_cycles = [c for c in cycles_data if c.get('status') == 'completed']
            
            if not completed_cycles:
                return "$0.00", "$0.00", "0.00%", "0.00%", "0.00", "0"
            
            # Calcular promedios
            avg_final_balance = np.mean([c.get('final_balance', 0) for c in completed_cycles])
            avg_daily_pnl = np.mean([c.get('daily_pnl', 0) for c in completed_cycles])
            avg_progress_target = np.mean([c.get('progress_to_target', 0) for c in completed_cycles])
            avg_win_rate = np.mean([c.get('win_rate', 0) for c in completed_cycles])
            avg_sharpe_ratio = np.mean([c.get('sharpe_ratio', 0) for c in completed_cycles])
            total_cycles = len(completed_cycles)
            
            # Formatear valores
            avg_final_balance_str = f"${avg_final_balance:,.2f}"
            avg_daily_pnl_str = f"${avg_daily_pnl:,.2f}"
            avg_progress_target_str = f"{avg_progress_target:.2f}%"
            avg_win_rate_str = f"{avg_win_rate:.1f}%"
            avg_sharpe_ratio_str = f"{avg_sharpe_ratio:.2f}"
            total_cycles_str = str(total_cycles)
            
            return avg_final_balance_str, avg_daily_pnl_str, avg_progress_target_str, avg_win_rate_str, avg_sharpe_ratio_str, total_cycles_str
            
        except Exception as e:
            logger.error(f"Error actualizando métricas del overview: {e}")
            return "$0.00", "$0.00", "0.00%", "0.00%", "0.00", "0"
    
    # Callback para gráficos del overview de ciclos
    @app.callback(
        [Output('pnl-evolution-chart', 'figure'),
         Output('performance-distribution-chart', 'figure')],
        [Input('dashboard-data', 'data')]
    )
    def update_cycles_overview_charts(data):
        """Actualiza los gráficos del overview de ciclos"""
        try:
            if not data or 'cycles' not in data:
                return go.Figure(), go.Figure()
            
            cycles_data = data['cycles'].get('top_cycles', [])
            
            from monitoring.components.widgets.cycles_overview import CyclesOverviewWidget
            overview_widget = CyclesOverviewWidget()
            
            # Crear gráficos
            pnl_evolution_fig = overview_widget.create_pnl_evolution_chart(cycles_data)
            distribution_fig = overview_widget.create_performance_distribution_chart(cycles_data)
            
            return pnl_evolution_fig, distribution_fig
            
        except Exception as e:
            logger.error(f"Error actualizando gráficos del overview: {e}")
            return go.Figure(), go.Figure()
