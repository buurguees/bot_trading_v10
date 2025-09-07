"""
monitoring/layout_components.py
Componentes de layout para el dashboard del Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\layout_components.py

Funcionalidades:
- Define todos los layouts de las páginas
- Componentes reutilizables de UI
- Estructura visual del dashboard
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LayoutComponents:
    """Componentes de layout para el dashboard"""
    
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
    
    def create_header(self):
        """Crea el header principal del dashboard"""
        return html.Div([
            html.Div([
                # Logo y título
                html.Div([
                    html.I(className="fas fa-robot", style={'color': self.theme_colors['accent'], 'marginRight': '10px'}),
                    html.H2("Trading Bot v10", style={'margin': '0', 'color': self.theme_colors['text_primary']})
                ], style={'display': 'flex', 'alignItems': 'center'}),
                
                # Navegación
                html.Div([
                    dcc.Link([
                        html.I(className="fas fa-home", style={'marginRight': '5px'}),
                        "Home"
                    ], href="/", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-chart-line", style={'marginRight': '5px'}),
                        "Trading"
                    ], href="/trading", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-chart-bar", style={'marginRight': '5px'}),
                        "Performance"
                    ], href="/performance", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-bell", style={'marginRight': '5px'}),
                        "Alerts"
                    ], href="/alerts", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-cog", style={'marginRight': '5px'}),
                        "Settings"
                    ], href="/settings", className="nav-link"),
                    
                    dcc.Link([
                        html.I(className="fas fa-comments", style={'marginRight': '5px'}),
                        "Chat"
                    ], href="/chat", className="nav-link chat-link"),
                    
                ], className="nav-menu"),
                
                # Status indicator
                html.Div([
                    html.Div(id="status-indicator", className="status-active"),
                    html.Span("ACTIVE", id="status-text", style={'color': self.theme_colors['accent'], 'fontWeight': 'bold'})
                ], style={'display': 'flex', 'alignItems': 'center'})
                
            ], className="header-content")
        ], className="dashboard-header")
    
    def create_home_page(self):
        """Página principal del dashboard"""
        return html.Div([
            # Métricas principales
            html.Div([
                html.H3("📊 Overview", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
                
                html.Div([
                    # Balance Total
                    self.create_metric_card(
                        title="Total Balance",
                        value="$10,000.00",
                        value_id="total-balance",
                        icon="fas fa-wallet",
                        color=self.theme_colors['info']
                    ),
                    
                    # P&L Diario
                    self.create_metric_card(
                        title="Daily P&L",
                        value="+$156.30",
                        value_id="daily-pnl",
                        icon="fas fa-chart-line",
                        color=self.theme_colors['accent']
                    ),
                    
                    # Win Rate
                    self.create_metric_card(
                        title="Win Rate",
                        value="75%",
                        value_id="win-rate",
                        icon="fas fa-percentage",
                        color=self.theme_colors['warning']
                    ),
                    
                    # Posiciones Activas
                    self.create_metric_card(
                        title="Active Positions",
                        value="2",
                        value_id="active-positions",
                        icon="fas fa-coins",
                        color=self.theme_colors['info']
                    ),
                    
                    # Progreso hacia objetivo
                    self.create_metric_card(
                        title="Progress to $1M",
                        value="0.1%",
                        value_id="progress-to-target",
                        icon="fas fa-trophy",
                        color=self.theme_colors['success']
                    )
                ], className="metrics-grid"),
                
            ], style={'marginBottom': '30px'}),
            
            # Gráficos principales
            html.Div([
                # Gráfico P&L
                html.Div([
                    html.H4("📈 P&L Evolution", style={'color': self.theme_colors['text_primary']}),
                    dcc.Graph(id="pnl-chart", style={'height': '400px'})
                ], className="chart-container", style={'width': '60%', 'display': 'inline-block'}),
                
                # Distribución de trades
                html.Div([
                    html.H4("🎯 Trades Distribution", style={'color': self.theme_colors['text_primary']}),
                    dcc.Graph(id="trades-distribution-chart", style={'height': '400px'})
                ], className="chart-container", style={'width': '40%', 'display': 'inline-block'})
                
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
    
    def create_trading_page(self):
        """Página de trading en vivo"""
        return html.Div([
            html.H3("⚡ Live Trading", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
            
            # Estado del trading
            html.Div([
                self.create_metric_card(
                    title="Trading Status",
                    value="ACTIVE",
                    value_id="trading-status",
                    icon="fas fa-play",
                    color=self.theme_colors['accent']
                ),
                
                self.create_metric_card(
                    title="Model Confidence",
                    value="78%",
                    value_id="model-confidence",
                    icon="fas fa-brain",
                    color=self.theme_colors['info']
                ),
                
                self.create_metric_card(
                    title="Trades Today",
                    value="8",
                    value_id="trades-today",
                    icon="fas fa-exchange-alt",
                    color=self.theme_colors['warning']
                ),
                
                self.create_metric_card(
                    title="Last Signal",
                    value="BUY 85%",
                    value_id="last-signal",
                    icon="fas fa-signal",
                    color=self.theme_colors['accent']
                )
            ], className="metrics-grid", style={'marginBottom': '30px'}),
            
            # Tabla de señales en tiempo real
            html.Div([
                html.H4("🔮 Real-time Signals", style={'color': self.theme_colors['text_primary']}),
                html.Div(id="live-signals-table")
            ], style={'marginBottom': '30px'}),
            
            # Gráfico de precio con señales
            html.Div([
                html.H4("📊 Price Chart with Signals", style={'color': self.theme_colors['text_primary']}),
                dcc.Graph(id="price-signals-chart", style={'height': '500px'})
            ])
            
        ], className="page-content")
    
    def create_performance_page(self):
        """Página de análisis de performance"""
        return html.Div([
            html.H3("📈 Performance Analysis", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
            
            # Métricas de performance
            html.Div([
                self.create_metric_card(
                    title="Total Trades",
                    value="145",
                    value_id="total-trades",
                    icon="fas fa-hashtag",
                    color=self.theme_colors['info']
                ),
                
                self.create_metric_card(
                    title="Profit Factor",
                    value="1.34",
                    value_id="profit-factor",
                    icon="fas fa-trophy",
                    color=self.theme_colors['accent']
                ),
                
                self.create_metric_card(
                    title="Sharpe Ratio",
                    value="1.67",
                    value_id="sharpe-ratio",
                    icon="fas fa-chart-area",
                    color=self.theme_colors['warning']
                ),
                
                self.create_metric_card(
                    title="Max Drawdown",
                    value="-8.5%",
                    value_id="max-drawdown",
                    icon="fas fa-arrow-down",
                    color=self.theme_colors['danger']
                )
            ], className="metrics-grid", style={'marginBottom': '30px'}),
            
            # Gráficos de análisis
            html.Div([
                # Evolución de accuracy
                html.Div([
                    html.H4("🧠 Model Accuracy Evolution", style={'color': self.theme_colors['text_primary']}),
                    dcc.Graph(id="accuracy-evolution-chart", style={'height': '400px'})
                ], style={'width': '50%', 'display': 'inline-block', 'paddingRight': '15px'}),
                
                # Análisis de trades
                html.Div([
                    html.H4("📊 Trades Analysis", style={'color': self.theme_colors['text_primary']}),
                    dcc.Graph(id="trades-analysis-chart", style={'height': '400px'})
                ], style={'width': '50%', 'display': 'inline-block', 'paddingLeft': '15px'})
            ], style={'marginBottom': '30px'}),
            
            # Tabla de trades históricos
            html.Div([
                html.H4("📋 Trade History", style={'color': self.theme_colors['text_primary']}),
                html.Div(id="trade-history-table")
            ])
            
        ], className="page-content")
    
    def create_alerts_page(self):
        """Página de alertas y notificaciones"""
        return html.Div([
            html.H3("🚨 Alerts & Notifications", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
            
            # Estado de alertas
            html.Div([
                self.create_metric_card(
                    title="Active Alerts",
                    value="3",
                    value_id="active-alerts",
                    icon="fas fa-exclamation-triangle",
                    color=self.theme_colors['warning']
                ),
                
                self.create_metric_card(
                    title="System Health",
                    value="OK",
                    value_id="system-health",
                    icon="fas fa-heart",
                    color=self.theme_colors['accent']
                ),
                
                self.create_metric_card(
                    title="API Status",
                    value="Connected",
                    value_id="api-status",
                    icon="fas fa-wifi",
                    color=self.theme_colors['accent']
                ),
                
                self.create_metric_card(
                    title="Model Status",
                    value="Training",
                    value_id="model-status",
                    icon="fas fa-cogs",
                    color=self.theme_colors['info']
                )
            ], className="metrics-grid", style={'marginBottom': '30px'}),
            
            # Lista de alertas
            html.Div([
                html.H4("📋 Recent Alerts", style={'color': self.theme_colors['text_primary']}),
                html.Div(id="alerts-list")
            ])
            
        ], className="page-content")
    
    def create_settings_page(self):
        """Página de configuraciones"""
        return html.Div([
            html.H3("⚙️ Settings", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
            
            # Controles básicos
            html.Div([
                html.H4("🎛️ Trading Controls", style={'color': self.theme_colors['text_primary']}),
                
                html.Div([
                    html.Button("⏸️ Pause Trading", id="pause-btn", className="control-btn pause-btn"),
                    html.Button("▶️ Resume Trading", id="resume-btn", className="control-btn resume-btn"),
                    html.Button("🛑 Emergency Stop", id="emergency-btn", className="control-btn emergency-btn"),
                    html.Button("🔄 Retrain Model", id="retrain-btn", className="control-btn retrain-btn")
                ], style={'marginBottom': '20px'}),
                
                html.Div(id="control-feedback", style={'color': self.theme_colors['accent']})
            ], style={'marginBottom': '30px'}),
            
            # Configuraciones
            html.Div([
                html.H4("📊 Configuration", style={'color': self.theme_colors['text_primary']}),
                
                html.Div([
                    html.Label("Risk per Trade (%)", style={'color': self.theme_colors['text_secondary']}),
                    dcc.Slider(
                        id="risk-slider",
                        min=0.5,
                        max=5.0,
                        step=0.1,
                        value=2.0,
                        marks={i: f"{i}%" for i in [0.5, 1, 2, 3, 4, 5]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={'marginBottom': '20px'}),
                
                html.Div([
                    html.Label("Minimum Confidence (%)", style={'color': self.theme_colors['text_secondary']}),
                    dcc.Slider(
                        id="confidence-slider",
                        min=50,
                        max=95,
                        step=1,
                        value=70,
                        marks={i: f"{i}%" for i in [50, 60, 70, 80, 90]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={'marginBottom': '20px'})
            ])
            
        ], className="page-content")
    
    def create_chat_page(self):
        """Página de chat (placeholder para futuro)"""
        return html.Div([
            html.H3("💬 AI Assistant Chat", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
            
            # Mensaje de futuro desarrollo
            html.Div([
                html.Div([
                    html.I(className="fas fa-robot", style={
                        'fontSize': '64px', 
                        'color': self.theme_colors['accent'],
                        'marginBottom': '20px'
                    }),
                    html.H4("🚧 Coming Soon!", style={'color': self.theme_colors['text_primary']}),
                    html.P([
                        "The AI Assistant Chat will be available in a future update. ",
                        "This feature will allow you to:"
                    ], style={'color': self.theme_colors['text_secondary'], 'marginBottom': '20px'}),
                    
                    html.Ul([
                        html.Li("💬 Chat naturally with your trading bot"),
                        html.Li("🔍 Ask questions about performance and trades"),
                        html.Li("🐛 Get help debugging issues"),
                        html.Li("⚙️ Modify settings through conversation"),
                        html.Li("📊 Request custom analysis and reports"),
                        html.Li("🎓 Learn about trading strategies")
                    ], style={'color': self.theme_colors['text_secondary'], 'textAlign': 'left'})
                    
                ], style={
                    'textAlign': 'center',
                    'padding': '60px',
                    'backgroundColor': self.theme_colors['secondary'],
                    'borderRadius': '12px',
                    'border': f"2px dashed {self.theme_colors['accent']}"
                })
            ])
            
        ], className="page-content")
    
    def create_404_page(self):
        """Página de error 404"""
        return html.Div([
            html.Div([
                html.H1("404", style={'fontSize': '120px', 'color': self.theme_colors['danger'], 'margin': '0'}),
                html.H3("Page Not Found", style={'color': self.theme_colors['text_primary']}),
                html.P("The page you're looking for doesn't exist.", style={'color': self.theme_colors['text_secondary']}),
                dcc.Link("🏠 Go Home", href="/", className="btn btn-primary")
            ], style={'textAlign': 'center', 'padding': '100px'})
        ], className="page-content")
    
    def create_metric_card(self, title, value, value_id, icon, color):
        """Crea una tarjeta de métrica"""
        return html.Div([
            html.Div([
                html.I(className=icon, style={'fontSize': '24px', 'color': color}),
                html.Div([
                    html.H4(title, style={'margin': '0', 'color': self.theme_colors['text_secondary'], 'fontSize': '14px'}),
                    html.H2(value, id=value_id, style={'margin': '5px 0 0 0', 'color': self.theme_colors['text_primary']})
                ])
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})
        ], className="metric-card")


# Funciones de compatibilidad para el dashboard existente
def build_layout():
    """Función de compatibilidad para el dashboard existente"""
    layout_components = LayoutComponents()
    
    return html.Div([
        dcc.Location(id="url"),
        layout_components.create_header(),
        html.Div(id="page-content", children=[
            layout_components.create_home_page()
        ])
    ], className="dashboard-container")


def render_home_page():
    """Función de compatibilidad para la página home"""
    layout_components = LayoutComponents()
    return layout_components.create_home_page()
