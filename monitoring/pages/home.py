"""
monitoring/pages/home.py
Página principal del dashboard
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HomePage:
    """Página principal del dashboard"""
    
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
    
    def create_home_page(self):
        """Crea la página principal del dashboard"""
        return html.Div([
            # Métricas principales
            html.Div([
                # Balance total
                html.Div([
                    html.H4("💰 Balance Total", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H2(id="total-balance", style={'color': self.theme_colors['accent'], 'margin': '0'})
                ], className="metric-card"),
                
                # P&L del día
                html.Div([
                    html.H4("📈 P&L del Día", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H2(id="daily-pnl", style={'color': self.theme_colors['success'], 'margin': '0'})
                ], className="metric-card"),
                
                # Progreso hacia objetivo
                html.Div([
                    html.H4("🎯 Progreso Objetivo", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H2(id="progress-to-target", style={'color': self.theme_colors['info'], 'margin': '0'})
                ], className="metric-card"),
                
                # Trades del día
                html.Div([
                    html.H4("📊 Trades Hoy", style={'color': self.theme_colors['text_secondary'], 'margin': '0'}),
                    html.H2(id="trades-today", style={'color': self.theme_colors['warning'], 'margin': '0'})
                ], className="metric-card")
            ], className="metrics-grid", style={'marginBottom': '30px'}),
            
            # Gráficos principales
            html.Div([
                # Gráfico P&L con navegación
                html.Div([
                    html.Div([
                        html.H4("📈 Análisis de P&L Histórico", style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                        html.Div([
                            html.Label("Período de análisis:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Dropdown(
                                id='home-pnl-timeframe',
                                options=[
                                    {'label': '7 días', 'value': '7d'},
                                    {'label': '30 días', 'value': '30d'},
                                    {'label': '90 días', 'value': '90d'},
                                    {'label': '1 año', 'value': '1y'},
                                    {'label': 'Todo', 'value': 'all'}
                                ],
                                value='30d',
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'}),
                        html.Div([
                            html.Button("◀", id="home-pnl-prev", className="nav-btn-small", title="Período anterior"),
                            html.Button("▶", id="home-pnl-next", className="nav-btn-small", title="Período siguiente"),
                            html.Button("🏠", id="home-pnl-today", className="nav-btn-small", title="Ir a hoy")
                        ], style={'margin': '10px', 'display': 'inline-block'})
                    ], className="chart-controls-small"),
                    dcc.Graph(id="pnl-chart", config={'displayModeBar': False}),
                    html.Div(id="home-pnl-period-info", className="period-info-small")
                ], className="chart-container", style={'width': '60%', 'display': 'inline-block', 'paddingRight': '15px'}),
                
                # Distribución de trades
                html.Div([
                    html.H4("📊 Distribución de Trades", style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                    dcc.Graph(id="trades-distribution-chart", style={'height': '400px'})
                ], className="chart-container", style={'width': '40%', 'display': 'inline-block'})
                
            ], style={'marginBottom': '30px'}),
            
            # Overview de Ciclos del Agente
            html.Div([
                html.Div(id="cycles-overview-widget-container")
            ], style={'marginBottom': '30px'}),
            
            # Top 10 Ciclos Cronológicos
            html.Div([
                html.Div(id="top-cycles-widget-container")
            ], style={'marginBottom': '30px'}),
            
            # Posiciones activas y señales recientes
            html.Div([
                # Posiciones activas
                html.Div([
                    html.H4("💼 Active Positions", style={'color': self.theme_colors['text_primary']}),
                    html.Div(id="active-positions-table")
                ], style={'width': '50%', 'display': 'inline-block', 'paddingRight': '15px'}),
                
                # Señales recientes
                html.Div([
                    html.H4("🎯 Recent Signals", style={'color': self.theme_colors['text_primary']}),
                    html.Div(id="recent-signals-table")
                ], style={'width': '50%', 'display': 'inline-block', 'paddingLeft': '15px'})
            ])
            
        ], className="page-content")

# Función de conveniencia para compatibilidad
def create_home_page():
    """Función de conveniencia para crear la página principal"""
    home_page = HomePage()
    return home_page.create_home_page()
