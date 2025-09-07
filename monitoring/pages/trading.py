"""
monitoring/pages/trading.py
Página de trading en vivo
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TradingPage:
    """Página de trading en vivo"""
    
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
            'text_secondary': '#cccccc',
            'border_color': '#444444'
        }
    
    def create_trading_page(self):
        """Crea la página de trading en vivo"""
        return html.Div([
            # Controles de trading
            html.Div([
                html.H3("🎯 Trading en Vivo", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
                
                # Controles de símbolo y período
                html.Div([
                    html.Div([
                        html.Label("Símbolo:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                        dcc.Dropdown(
                            id='trading-symbol-selector',
                            options=[
                                {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                                {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                                {'label': 'ADAUSDT', 'value': 'ADAUSDT'},
                                {'label': 'SOLUSDT', 'value': 'SOLUSDT'}
                            ],
                            value='BTCUSDT',
                            style={'width': '120px', 'display': 'inline-block'}
                        )
                    ], style={'margin': '5px', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label("Período:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                        dcc.Dropdown(
                            id='trading-timeframe-selector',
                            options=[
                                {'label': '1H', 'value': '1h'},
                                {'label': '4H', 'value': '4h'},
                                {'label': '1D', 'value': '1d'},
                                {'label': '1W', 'value': '1w'}
                            ],
                            value='1h',
                            style={'width': '100px', 'display': 'inline-block'}
                        )
                    ], style={'margin': '5px', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label("Rango:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                        dcc.Dropdown(
                            id='trading-range-selector',
                            options=[
                                {'label': '24H', 'value': '24h'},
                                {'label': '7D', 'value': '7d'},
                                {'label': '30D', 'value': '30d'},
                                {'label': '90D', 'value': '90d'}
                            ],
                            value='24h',
                            style={'width': '100px', 'display': 'inline-block'}
                        )
                    ], style={'margin': '5px', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Button("◀", id="trading-chart-prev", className="nav-btn-small", title="Período anterior"),
                        html.Button("▶", id="trading-chart-next", className="nav-btn-small", title="Período siguiente"),
                        html.Button("🏠", id="trading-chart-today", className="nav-btn-small", title="Ir a hoy"),
                        html.Button("📊", id="trading-chart-zoom", className="nav-btn-small", title="Zoom automático")
                    ], style={'margin': '5px', 'display': 'inline-block'})
                    
                ], className="chart-controls-small", style={'marginBottom': '20px'}),
                
                # Gráfico de precios con señales
                dcc.Graph(id="price-signals-chart", style={'height': '500px'}),
                html.Div(id="trading-chart-period-info", className="period-info-small", style={'marginTop': '10px'})
                
            ], style={'marginBottom': '30px'}),
            
            # Métricas de trading
            html.Div([
                # Métricas de rendimiento
                html.Div([
                    html.H4("📊 Métricas de Trading", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                    html.Div([
                        html.Div([
                            html.H5("Win Rate", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="win-rate", style={'color': self.theme_colors['success'], 'margin': '0'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Profit Factor", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="profit-factor", style={'color': self.theme_colors['accent'], 'margin': '0'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Max Drawdown", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="max-drawdown", style={'color': self.theme_colors['danger'], 'margin': '0'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Sharpe Ratio", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="sharpe-ratio", style={'color': self.theme_colors['info'], 'margin': '0'})
                        ], className="metric-card-small")
                    ], className="metrics-grid-small")
                ], style={'width': '50%', 'display': 'inline-block', 'paddingRight': '15px'}),
                
                # Estado del modelo
                html.Div([
                    html.H4("🤖 Estado del Modelo", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                    html.Div([
                        html.Div([
                            html.H5("Confianza Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="avg-confidence", style={'color': self.theme_colors['accent'], 'margin': '0'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Precisión", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="model-accuracy", style={'color': self.theme_colors['success'], 'margin': '0'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Última Actualización", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="last-update", style={'color': self.theme_colors['info'], 'margin': '0', 'fontSize': '14px'})
                        ], className="metric-card-small"),
                        
                        html.Div([
                            html.H5("Estado", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                            html.H3(id="model-status", style={'color': self.theme_colors['success'], 'margin': '0'})
                        ], className="metric-card-small")
                    ], className="metrics-grid-small")
                ], style={'width': '50%', 'display': 'inline-block', 'paddingLeft': '15px'})
            ], style={'marginBottom': '30px'}),
            
            # Historial de trades recientes
            html.Div([
                html.H4("📋 Historial de Trades Recientes", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                html.Div(id="recent-trades-table")
            ])
            
        ], className="page-content")

# Función de conveniencia para compatibilidad
def create_trading_page():
    """Función de conveniencia para crear la página de trading"""
    trading_page = TradingPage()
    return trading_page.create_trading_page()
