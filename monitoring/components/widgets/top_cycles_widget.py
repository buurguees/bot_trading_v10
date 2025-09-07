"""
monitoring/components/top_cycles_widget.py
Widget para mostrar los Top 10 ciclos cronológicos
Ubicación: C:\TradingBot_v10\monitoring\components\top_cycles_widget.py

Funcionalidades:
- Widget de Top 10 ciclos con mejor PnL diario
- Métricas de progreso hacia objetivo
- Gráficos de rendimiento por ciclo
- Filtros y ordenamiento
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TopCyclesWidget:
    """Widget para mostrar los mejores ciclos cronológicos"""
    
    def __init__(self):
        self.theme_colors = {
            'primary': '#1a1a1a',
            'secondary': '#2d2d2d',
            'accent': '#00ff88',
            'danger': '#ff4444',
            'warning': '#ffaa00',
            'info': '#4488ff',
            'success': '#28a745',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc'
        }
    
    def create_top_cycles_widget(self) -> html.Div:
        """Crea el widget principal de Top 10 ciclos"""
        
        return html.Div([
            # Header del widget
            html.Div([
                html.H4("🏆 Top 10 Mejores Ciclos Sincronizados", 
                       style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                html.P("Ciclos con mejor balance final, win rate, trades y progreso hacia objetivo", 
                      style={'color': self.theme_colors['text_secondary'], 'marginBottom': '20px'})
            ]),
            
            # Controles de filtrado
            html.Div([
                html.Div([
                    html.Label("Ordenar por:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='cycles-sort-metric',
                        options=[
                            {'label': 'Balance Final', 'value': 'final_balance'},
                            {'label': 'Win Rate', 'value': 'win_rate'},
                            {'label': 'Número de Trades', 'value': 'trades_count'},
                            {'label': 'Progreso Objetivo', 'value': 'progress_to_target'},
                            {'label': 'PnL Diario', 'value': 'daily_pnl'},
                            {'label': 'Sharpe Ratio', 'value': 'sharpe_ratio'}
                        ],
                        value='final_balance',
                        style={'width': '150px', 'display': 'inline-block'}
                    )
                ], style={'margin': '5px', 'display': 'inline-block'}),
                
                html.Div([
                    html.Label("Símbolo:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='cycles-symbol-filter',
                        options=[
                            {'label': 'Todos', 'value': 'all'},
                            {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                            {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                            {'label': 'ADAUSDT', 'value': 'ADAUSDT'},
                            {'label': 'SOLUSDT', 'value': 'SOLUSDT'}
                        ],
                        value='all',
                        style={'width': '120px', 'display': 'inline-block'}
                    )
                ], style={'margin': '5px', 'display': 'inline-block'}),
                
                html.Div([
                    html.Button("🔄 Actualizar", id="refresh-cycles-btn", 
                              className="nav-btn-small", title="Actualizar datos")
                ], style={'margin': '5px', 'display': 'inline-block'})
                
            ], className="chart-controls-small", style={'marginBottom': '15px'}),
            
            # Tabla de Top 10 ciclos
            html.Div([
                    dash_table.DataTable(
                    id='top-cycles-table',
                    columns=[
                        {'name': 'Rank', 'id': 'rank', 'type': 'numeric', 'width': '60px'},
                        {'name': 'Ciclo', 'id': 'cycle_id', 'type': 'text', 'width': '120px'},
                        {'name': 'Símbolos', 'id': 'symbols', 'type': 'text', 'width': '100px'},
                        {'name': 'Fecha', 'id': 'date', 'type': 'text', 'width': '100px'},
                        {'name': 'Balance Final', 'id': 'final_balance', 'type': 'numeric', 'format': {'specifier': '$,.2f'}, 'width': '120px'},
                        {'name': 'Win Rate', 'id': 'win_rate', 'type': 'numeric', 'format': {'specifier': '.1%'}, 'width': '80px'},
                        {'name': 'Trades', 'id': 'trades', 'type': 'numeric', 'width': '70px'},
                        {'name': 'Progreso', 'id': 'progress', 'type': 'numeric', 'format': {'specifier': '.2f'}, 'width': '80px'},
                        {'name': 'PnL Diario', 'id': 'daily_pnl', 'type': 'numeric', 'format': {'specifier': '$,.2f'}, 'width': '100px'},
                        {'name': 'Sharpe', 'id': 'sharpe', 'type': 'numeric', 'format': {'specifier': '.2f'}, 'width': '70px'}
                    ],
                    data=[],
                    style_cell={
                        'backgroundColor': self.theme_colors['secondary'],
                        'color': self.theme_colors['text_primary'],
                        'fontFamily': 'Inter, sans-serif',
                        'fontSize': '12px',
                        'textAlign': 'center',
                        'padding': '8px'
                    },
                    style_header={
                        'backgroundColor': self.theme_colors['primary'],
                        'color': self.theme_colors['accent'],
                        'fontWeight': 'bold',
                        'border': f'1px solid {self.theme_colors["border_color"]}'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 0},
                            'backgroundColor': '#2d4a2d',  # Verde oscuro para #1
                            'color': '#00ff88'
                        },
                        {
                            'if': {'row_index': 1},
                            'backgroundColor': '#3d4a3d',  # Verde medio para #2
                        },
                        {
                            'if': {'row_index': 2},
                            'backgroundColor': '#4d4a4d',  # Verde claro para #3
                        },
                        {
                            'if': {'filter_query': '{daily_pnl} > 0'},
                            'color': '#00ff88'
                        },
                        {
                            'if': {'filter_query': '{daily_pnl} < 0'},
                            'color': '#ff4444'
                        }
                    ],
                    style_table={
                        'height': '400px',
                        'overflowY': 'auto',
                        'border': f'1px solid {self.theme_colors["border_color"]}',
                        'borderRadius': '8px'
                    }
                )
            ], style={'marginBottom': '20px'}),
            
            # Gráfico de rendimiento
            html.Div([
                html.H5("📈 Rendimiento de Top 5 Ciclos", 
                       style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                dcc.Graph(
                    id='cycles-performance-chart',
                    config={'displayModeBar': False},
                    style={'height': '300px'}
                )
            ]),
            
            # Estadísticas resumen
            html.Div([
                html.H5("📊 Estadísticas Generales", 
                       style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                html.Div(id='cycles-summary-stats', className="stats-grid")
            ])
            
        ], className="top-cycles-widget", style={
            'background': self.theme_colors['secondary'],
            'padding': '20px',
            'borderRadius': '8px',
            'border': f'1px solid {self.theme_colors["border_color"]}',
            'marginBottom': '20px'
        })
    
    def create_cycles_performance_chart(self, cycles_data: list) -> go.Figure:
        """Crea gráfico de rendimiento de ciclos"""
        try:
            if not cycles_data:
                return go.Figure()
            
            # Tomar top 5 ciclos
            top_5 = cycles_data[:5]
            
            fig = go.Figure()
            
            # Gráfico de barras para PnL diario
            fig.add_trace(go.Bar(
                x=[f"{cycle['symbol']}\n{cycle['date']}" for cycle in top_5],
                y=[cycle['daily_pnl'] for cycle in top_5],
                name='PnL Diario',
                marker_color=['#00ff88' if pnl > 0 else '#ff4444' for pnl in [cycle['daily_pnl'] for cycle in top_5]],
                text=[f"${pnl:,.0f}" for pnl in [cycle['daily_pnl'] for cycle in top_5]],
                textposition='auto'
            ))
            
            fig.update_layout(
                title="Top 5 Ciclos - PnL Diario",
                xaxis_title="Ciclo",
                yaxis_title="PnL Diario ($)",
                template="plotly_dark",
                height=300,
                showlegend=False,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de ciclos: {e}")
            return go.Figure()
    
    def create_cycles_summary_stats(self, stats: dict) -> html.Div:
        """Crea estadísticas resumen de ciclos"""
        try:
            if not stats:
                return html.Div("No hay datos disponibles", 
                              style={'color': self.theme_colors['text_secondary']})
            
            return html.Div([
                html.Div([
                    html.H6("Total Ciclos", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"{stats.get('total_cycles', 0)}", 
                           style={'color': self.theme_colors['accent'], 'margin': '0'})
                ], className="stat-card"),
                
                html.Div([
                    html.H6("Completados", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"{stats.get('completed_cycles', 0)}", 
                           style={'color': self.theme_colors['success'], 'margin': '0'})
                ], className="stat-card"),
                
                html.Div([
                    html.H6("Mejor PnL", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"${stats.get('best_daily_pnl', 0):,.0f}", 
                           style={'color': self.theme_colors['accent'], 'margin': '0'})
                ], className="stat-card"),
                
                html.Div([
                    html.H6("Mejor Progreso", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"{stats.get('best_progress', 0):.2f}%", 
                           style={'color': self.theme_colors['info'], 'margin': '0'})
                ], className="stat-card"),
                
                html.Div([
                    html.H6("PnL Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"${stats.get('avg_daily_pnl', 0):,.0f}", 
                           style={'color': self.theme_colors['warning'], 'margin': '0'})
                ], className="stat-card"),
                
                html.Div([
                    html.H6("Total PnL", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H4(f"${stats.get('total_pnl', 0):,.0f}", 
                           style={'color': self.theme_colors['success'], 'margin': '0'})
                ], className="stat-card")
                
            ], className="stats-grid", style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(120px, 1fr))',
                'gap': '15px',
                'marginTop': '15px'
            })
            
        except Exception as e:
            logger.error(f"Error creando estadísticas resumen: {e}")
            return html.Div("Error cargando estadísticas", 
                          style={'color': self.theme_colors['danger']})
