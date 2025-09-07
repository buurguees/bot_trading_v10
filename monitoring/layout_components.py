"""
monitoring/layout_components.py
ENHANCED VERSION 2.0 - Componentes de layout mejorados para el dashboard
Funcionalidades nuevas:
- Diseño moderno con mejores métricas visuales
- Navegación mejorada con iconos
- Cards interactivas con animaciones
- Layout responsivo optimizado
- Integración con gráficos avanzados
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EnhancedLayoutComponents:
    """Componentes de layout mejorados para el dashboard"""
    
    def __init__(self):
        self.theme_colors = {
            'primary': '#0d1117',      # GitHub dark
            'secondary': '#161b22',    # Más oscuro
            'surface': '#21262d',      # Superficie
            'accent': '#58a6ff',       # Azul moderno
            'success': '#3fb950',      # Verde éxito
            'danger': '#f85149',       # Rojo peligro
            'warning': '#d29922',      # Amarillo advertencia
            'info': '#79c0ff',         # Info azul claro
            'text_primary': '#f0f6fc', # Texto principal
            'text_secondary': '#8b949e', # Texto secundario
            'grid': '#30363d',         # Líneas de grid
            'border': '#21262d'        # Bordes
        }
    
    def create_enhanced_header(self):
        """Crea un header moderno con navegación mejorada"""
        return html.Div([
            # Header container
            html.Div([
                # Logo section
                html.Div([
                    html.Div([
                        html.I(className="fas fa-robot", 
                              style={
                                  'fontSize': '28px',
                                  'color': self.theme_colors['accent'],
                                  'marginRight': '12px',
                                  'animation': 'pulse 2s infinite'
                              }),
                        html.H2("Trading Bot v10", 
                               style={
                                   'margin': '0',
                                   'color': self.theme_colors['text_primary'],
                                   'fontWeight': '700',
                                   'fontSize': '24px',
                                   'fontFamily': 'Inter, sans-serif'
                               })
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                    
                    # Status indicator
                    html.Div([
                        html.Div(id='bot-status-indicator', 
                                className='status-indicator-running',
                                children=[
                                    html.I(className="fas fa-circle", 
                                          style={'fontSize': '8px', 'marginRight': '6px'}),
                                    "RUNNING"
                                ])
                    ], style={'marginTop': '4px'})
                ], style={'flex': '1'}),
                
                # Navigation menu
                html.Div([
                    self._create_nav_item("fas fa-home", "Overview", "/", "home"),
                    self._create_nav_item("fas fa-chart-line", "Trading", "/trading", "trading"),
                    self._create_nav_item("fas fa-brain", "AI Insights", "/ai-insights", "ai"),
                    self._create_nav_item("fas fa-shield-alt", "Risk", "/risk", "risk"),
                    self._create_nav_item("fas fa-chart-pie", "Portfolio", "/portfolio", "portfolio"),
                    self._create_nav_item("fas fa-cog", "Settings", "/settings", "settings")
                ], className='nav-menu', style={
                    'display': 'flex',
                    'gap': '8px',
                    'alignItems': 'center'
                }),
                
                # Real-time metrics (top right)
                html.Div([
                    self._create_header_metric("P&L", "$0.00", "fas fa-dollar-sign", "pnl"),
                    self._create_header_metric("24h", "0.00%", "fas fa-percentage", "daily-change"),
                    self._create_header_metric("Pos", "0", "fas fa-layer-group", "positions")
                ], style={
                    'display': 'flex',
                    'gap': '16px',
                    'alignItems': 'center'
                })
                
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'padding': '16px 24px',
                'backgroundColor': self.theme_colors['primary'],
                'borderBottom': f'1px solid {self.theme_colors["border"]}',
                'boxShadow': '0 2px 8px rgba(0,0,0,0.3)'
            })
        ], style={'position': 'sticky', 'top': '0', 'zIndex': '1000'})
    
    def _create_nav_item(self, icon, label, href, nav_id):
        """Crea un elemento de navegación"""
        return dcc.Link([
            html.Div([
                html.I(className=icon, style={'marginRight': '8px', 'fontSize': '14px'}),
                html.Span(label, style={'fontSize': '14px', 'fontWeight': '500'})
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'padding': '8px 16px',
                'borderRadius': '8px',
                'transition': 'all 0.2s ease',
                'color': self.theme_colors['text_secondary']
            })
        ], 
        href=href, 
        id=f'nav-{nav_id}',
        className='nav-link-enhanced',
        style={'textDecoration': 'none'})
    
    def _create_header_metric(self, label, value, icon, metric_id):
        """Crea una métrica en el header"""
        return html.Div([
            html.I(className=icon, style={
                'fontSize': '12px',
                'color': self.theme_colors['text_secondary'],
                'marginBottom': '2px'
            }),
            html.Div(label, style={
                'fontSize': '10px',
                'color': self.theme_colors['text_secondary'],
                'fontWeight': '500',
                'lineHeight': '1'
            }),
            html.Div(value, id=f'header-{metric_id}', style={
                'fontSize': '14px',
                'color': self.theme_colors['text_primary'],
                'fontWeight': '600',
                'lineHeight': '1'
            })
        ], style={
            'textAlign': 'center',
            'minWidth': '60px'
        })
    
    def create_enhanced_home_page(self):
        """Crea la página principal mejorada"""
        return html.Div([
            # Top metrics grid
            html.Div([
                self._create_metric_card_large("Portfolio Value", "$50,000", "+2.5%", "fas fa-wallet", "success"),
                self._create_metric_card_large("Total P&L", "+$1,250", "+2.5%", "fas fa-chart-line", "success"),
                self._create_metric_card_large("Win Rate", "68.5%", "+1.2%", "fas fa-bullseye", "success"),
                self._create_metric_card_large("Active Positions", "3", "BTC, ETH, ADA", "fas fa-layer-group", "info")
            ], className='metrics-grid-large', style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))',
                'gap': '20px',
                'marginBottom': '24px'
            }),
            
            # Main charts section
            html.Div([
                # Left column - Main chart
                html.Div([
                    self._create_chart_container(
                        "Trading Runs Overview",
                        "runs-overview-chart",
                        height="500px",
                        tools=["fullscreen", "export", "refresh"]
                    )
                ], style={'flex': '2', 'marginRight': '20px'}),
                
                # Right column - Side charts
                html.Div([
                    self._create_chart_container(
                        "Real-time Performance",
                        "realtime-performance-chart",
                        height="240px",
                        compact=True
                    ),
                    self._create_chart_container(
                        "Risk Metrics",
                        "risk-summary-chart",
                        height="240px",
                        compact=True,
                        style={'marginTop': '20px'}
                    )
                ], style={'flex': '1'})
            ], style={
                'display': 'flex',
                'marginBottom': '24px'
            }),
            
            # Bottom section - Tables and additional metrics
            html.Div([
                # Recent trades table
                html.Div([
                    self._create_data_table_container(
                        "Recent Trades",
                        "recent-trades-table",
                        tools=["export", "filter"]
                    )
                ], style={'flex': '1', 'marginRight': '20px'}),
                
                # Active positions
                html.Div([
                    self._create_data_table_container(
                        "Active Positions",
                        "active-positions-table",
                        tools=["refresh"]
                    )
                ], style={'flex': '1'})
            ], style={
                'display': 'flex',
                'gap': '20px'
            })
            
        ], style={'padding': '24px'})
    
    def create_enhanced_trading_page(self):
        """Crea la página de trading mejorada"""
        return html.Div([
            # Trading controls header
            html.Div([
                html.Div([
                    html.H3("Live Trading Dashboard", style={
                        'margin': '0',
                        'color': self.theme_colors['text_primary'],
                        'fontSize': '20px',
                        'fontWeight': '600'
                    }),
                    html.P("Real-time market analysis and trade execution", style={
                        'margin': '4px 0 0 0',
                        'color': self.theme_colors['text_secondary'],
                        'fontSize': '14px'
                    })
                ], style={'flex': '1'}),
                
                # Trading controls
                html.Div([
                    self._create_control_button("Start Trading", "play", "success", "start-trading-btn"),
                    self._create_control_button("Pause", "pause", "warning", "pause-trading-btn"),
                    self._create_control_button("Emergency Stop", "stop", "danger", "stop-trading-btn")
                ], style={'display': 'flex', 'gap': '12px'})
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'marginBottom': '24px',
                'padding': '20px',
                'backgroundColor': self.theme_colors['secondary'],
                'borderRadius': '12px',
                'border': f'1px solid {self.theme_colors["border"]}'
            }),
            
            # Main trading chart
            html.Div([
                self._create_chart_container(
                    "Live Price Action & Signals",
                    "live-trading-chart",
                    height="600px",
                    tools=["fullscreen", "drawing", "indicators", "timeframe"]
                )
            ], style={'marginBottom': '24px'}),
            
            # Trading metrics grid
            html.Div([
                self._create_metric_card("Current Symbol", "BTCUSDT", "fas fa-coins", "info"),
                self._create_metric_card("Entry Price", "$43,250", "fas fa-sign-in-alt", "info"),
                self._create_metric_card("Current Price", "$43,450", "fas fa-dollar-sign", "success"),
                self._create_metric_card("Unrealized P&L", "+$200", "fas fa-chart-line", "success"),
                self._create_metric_card("Position Size", "0.1 BTC", "fas fa-weight", "info"),
                self._create_metric_card("Leverage", "3x", "fas fa-balance-scale", "warning")
            ], style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))',
                'gap': '16px',
                'marginBottom': '24px'
            }),
            
            # Order book and trade history
            html.Div([
                html.Div([
                    self._create_data_table_container(
                        "Order Book",
                        "order-book-table",
                        tools=["refresh"],
                        realtime=True
                    )
                ], style={'flex': '1', 'marginRight': '20px'}),
                
                html.Div([
                    self._create_data_table_container(
                        "Trade History",
                        "trade-history-table",
                        tools=["export", "filter"]
                    )
                ], style={'flex': '1'})
            ], style={'display': 'flex'})
            
        ], style={'padding': '24px'})
    
    def _create_metric_card(self, title, value, icon, color_type="info"):
        """Crea una tarjeta de métrica estándar"""
        colors = {
            'success': self.theme_colors['success'],
            'danger': self.theme_colors['danger'],
            'warning': self.theme_colors['warning'],
            'info': self.theme_colors['info'],
            'secondary': self.theme_colors['text_secondary']
        }
        
        return html.Div([
            html.Div([
                html.I(className=icon, style={
                    'fontSize': '18px',
                    'color': colors.get(color_type, self.theme_colors['info']),
                    'marginBottom': '8px'
                }),
                html.Div(title, style={
                    'fontSize': '12px',
                    'color': self.theme_colors['text_secondary'],
                    'fontWeight': '500',
                    'marginBottom': '4px'
                }),
                html.Div(value, style={
                    'fontSize': '18px',
                    'color': self.theme_colors['text_primary'],
                    'fontWeight': '600'
                })
            ])
        ], className='metric-card', style={
            'padding': '16px',
            'backgroundColor': self.theme_colors['secondary'],
            'borderRadius': '12px',
            'border': f'1px solid {self.theme_colors["border"]}',
            'transition': 'all 0.2s ease',
            'cursor': 'pointer'
        })
    
    def _create_metric_card_large(self, title, value, subtitle, icon, color_type="info"):
        """Crea una tarjeta de métrica grande"""
        colors = {
            'success': self.theme_colors['success'],
            'danger': self.theme_colors['danger'],
            'warning': self.theme_colors['warning'],
            'info': self.theme_colors['info']
        }
        
        return html.Div([
            html.Div([
                html.Div([
                    html.I(className=icon, style={
                        'fontSize': '24px',
                        'color': colors.get(color_type, self.theme_colors['info'])
                    }),
                    html.Div([
                        html.Div(title, style={
                            'fontSize': '14px',
                            'color': self.theme_colors['text_secondary'],
                            'fontWeight': '500',
                            'marginBottom': '4px'
                        }),
                        html.Div(value, style={
                            'fontSize': '24px',
                            'color': self.theme_colors['text_primary'],
                            'fontWeight': '700',
                            'lineHeight': '1'
                        }),
                        html.Div(subtitle, style={
                            'fontSize': '12px',
                            'color': colors.get(color_type, self.theme_colors['info']),
                            'fontWeight': '500',
                            'marginTop': '4px'
                        })
                    ], style={'flex': '1'})
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'gap': '16px'
                })
            ])
        ], className='metric-card-large', style={
            'padding': '24px',
            'backgroundColor': self.theme_colors['secondary'],
            'borderRadius': '16px',
            'border': f'1px solid {self.theme_colors["border"]}',
            'transition': 'all 0.2s ease',
            'cursor': 'pointer'
        })
    
    def _create_chart_container(self, title, chart_id, height="400px", tools=None, compact=False, **kwargs):
        """Crea un contenedor para gráficos"""
        tools = tools or []
        
        return html.Div([
            # Chart header
            html.Div([
                html.H4(title, style={
                    'margin': '0',
                    'fontSize': '16px' if compact else '18px',
                    'fontWeight': '600',
                    'color': self.theme_colors['text_primary']
                }),
                
                # Chart tools
                html.Div([
                    self._create_chart_tool(tool) for tool in tools
                ], style={'display': 'flex', 'gap': '8px'}) if tools else None
                
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'marginBottom': '16px' if not compact else '12px'
            }),
            
            # Chart area
            dcc.Graph(
                id=chart_id,
                style={'height': height},
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                }
            )
        ], style={
            'padding': '20px' if not compact else '16px',
            'backgroundColor': self.theme_colors['secondary'],
            'borderRadius': '16px',
            'border': f'1px solid {self.theme_colors["border"]}',
            **kwargs.get('style', {})
        })
    
    def _create_chart_tool(self, tool_type):
        """Crea herramientas para gráficos"""
        icons = {
            'fullscreen': 'fas fa-expand',
            'export': 'fas fa-download',
            'refresh': 'fas fa-sync-alt',
            'drawing': 'fas fa-pencil-alt',
            'indicators': 'fas fa-chart-bar',
            'timeframe': 'fas fa-clock',
            'scenarios': 'fas fa-flask',
            'rebalance': 'fas fa-balance-scale',
            'filter': 'fas fa-filter',
            'sort': 'fas fa-sort'
        }
        
        return html.Button([
            html.I(className=icons.get(tool_type, 'fas fa-cog'))
        ], className=f'chart-tool-btn chart-tool-{tool_type}', style={
            'padding': '6px 8px',
            'backgroundColor': 'transparent',
            'border': f'1px solid {self.theme_colors["border"]}',
            'borderRadius': '6px',
            'color': self.theme_colors['text_secondary'],
            'cursor': 'pointer',
            'fontSize': '12px',
            'transition': 'all 0.2s ease'
        })
    
    def _create_data_table_container(self, title, table_id, tools=None, realtime=False):
        """Crea un contenedor para tablas de datos"""
        tools = tools or []
        
        return html.Div([
            # Table header
            html.Div([
                html.Div([
                    html.H4(title, style={
                        'margin': '0',
                        'fontSize': '16px',
                        'fontWeight': '600',
                        'color': self.theme_colors['text_primary']
                    }),
                    html.Span("● LIVE" if realtime else "", style={
                        'fontSize': '10px',
                        'color': self.theme_colors['success'],
                        'fontWeight': '600',
                        'marginLeft': '8px',
                        'animation': 'pulse 2s infinite' if realtime else 'none'
                    })
                ], style={'display': 'flex', 'alignItems': 'center'}),
                
                html.Div([
                    self._create_chart_tool(tool) for tool in tools
                ], style={'display': 'flex', 'gap': '8px'}) if tools else None
                
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'marginBottom': '16px'
            }),
            
            # Table area
            html.Div(id=table_id, style={
                'maxHeight': '300px',
                'overflowY': 'auto'
            })
            
        ], style={
            'padding': '20px',
            'backgroundColor': self.theme_colors['secondary'],
            'borderRadius': '16px',
            'border': f'1px solid {self.theme_colors["border"]}'
        })
    
    def _create_control_button(self, label, icon, color_type, button_id):
        """Crea botones de control"""
        colors = {
            'success': {'bg': self.theme_colors['success'], 'text': self.theme_colors['primary']},
            'danger': {'bg': self.theme_colors['danger'], 'text': 'white'},
            'warning': {'bg': self.theme_colors['warning'], 'text': self.theme_colors['primary']},
            'info': {'bg': self.theme_colors['info'], 'text': self.theme_colors['primary']},
            'secondary': {'bg': self.theme_colors['border'], 'text': self.theme_colors['text_primary']}
        }
        
        color_config = colors.get(color_type, colors['secondary'])
        
        return html.Button([
            html.I(className=f"fas fa-{icon}", style={'marginRight': '8px'}),
            label
        ], id=button_id, style={
            'padding': '10px 20px',
            'backgroundColor': color_config['bg'],
            'color': color_config['text'],
            'border': 'none',
            'borderRadius': '8px',
            'fontWeight': '600',
            'fontSize': '14px',
            'cursor': 'pointer',
            'transition': 'all 0.2s ease',
            'display': 'flex',
            'alignItems': 'center'
        })


# === FUNCIONES DE COMPATIBILIDAD ===
# Mantener la funcionalidad existente

class LayoutComponents(EnhancedLayoutComponents):
    """Clase de compatibilidad para mantener la funcionalidad existente"""
    
    def create_header(self):
        """Mantiene compatibilidad con header anterior"""
        return self.create_enhanced_header()
    
    def create_home_page(self):
        """Mantiene compatibilidad con página home anterior"""
        return self.create_enhanced_home_page()
    
    def create_trading_page(self):
        """Crea página de trading (compatibilidad)"""
        return self.create_enhanced_trading_page()
    
    def create_performance_page(self):
        """Crea página de performance (nueva)"""
        return html.Div([
            html.H2("Performance Analysis", style={
                'color': self.theme_colors['text_primary'],
                'marginBottom': '20px'
            }),
            
            # Performance metrics
            html.Div([
                self._create_metric_card("Total Return", "12.5%", "fas fa-chart-line", "success"),
                self._create_metric_card("Sharpe Ratio", "1.85", "fas fa-star", "success"),
                self._create_metric_card("Max Drawdown", "5.2%", "fas fa-arrow-down", "warning"),
                self._create_metric_card("Win Rate", "68.5%", "fas fa-bullseye", "success")
            ], style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))',
                'gap': '16px',
                'marginBottom': '24px'
            }),
            
            # Performance charts
            html.Div([
                self._create_chart_container(
                    "Equity Curve & Drawdown",
                    "equity-curve-chart",
                    height="500px"
                )
            ], style={'marginBottom': '24px'}),
            
            html.Div([
                html.Div([
                    self._create_chart_container(
                        "Monthly Returns",
                        "monthly-returns-chart",
                        height="350px"
                    )
                ], style={'flex': '1', 'marginRight': '20px'}),
                
                html.Div([
                    self._create_chart_container(
                        "Return Distribution",
                        "return-distribution-chart",
                        height="350px"
                    )
                ], style={'flex': '1'})
            ], style={'display': 'flex'})
            
        ], style={'padding': '24px'})
    
    def create_alerts_page(self):
        """Crea página de alertas"""
        return html.Div([
            html.H2("System Alerts", style={
                'color': self.theme_colors['text_primary'],
                'marginBottom': '20px'
            }),
            
            # Alert filters
            html.Div([
                html.Div([
                    html.Label("Filter by Type:", style={
                        'color': self.theme_colors['text_secondary'],
                        'marginBottom': '8px',
                        'display': 'block'
                    }),
                    dcc.Dropdown(
                        id='alert-type-filter',
                        options=[
                            {'label': 'All Alerts', 'value': 'all'},
                            {'label': 'Trading', 'value': 'trading'},
                            {'label': 'Risk', 'value': 'risk'},
                            {'label': 'System', 'value': 'system'},
                            {'label': 'Model', 'value': 'model'}
                        ],
                        value='all',
                        style={'backgroundColor': self.theme_colors['secondary']}
                    )
                ], style={'width': '200px', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Severity:", style={
                        'color': self.theme_colors['text_secondary'],
                        'marginBottom': '8px',
                        'display': 'block'
                    }),
                    dcc.Dropdown(
                        id='alert-severity-filter',
                        options=[
                            {'label': 'All', 'value': 'all'},
                            {'label': 'Critical', 'value': 'critical'},
                            {'label': 'Warning', 'value': 'warning'},
                            {'label': 'Info', 'value': 'info'}
                        ],
                        value='all',
                        style={'backgroundColor': self.theme_colors['secondary']}
                    )
                ], style={'width': '200px'})
            ], style={
                'display': 'flex',
                'marginBottom': '24px',
                'padding': '20px',
                'backgroundColor': self.theme_colors['secondary'],
                'borderRadius': '12px'
            }),
            
            # Alerts list
            html.Div(id='alerts-container', children=[
                self._create_alert_item(
                    "Trading Alert",
                    "Position closed: BTCUSDT +$125.50",
                    "2 minutes ago",
                    "success"
                ),
                self._create_alert_item(
                    "Risk Warning",
                    "Portfolio correlation increased to 0.85",
                    "15 minutes ago",
                    "warning"
                ),
                self._create_alert_item(
                    "Model Update",
                    "AI model retrained with new data",
                    "1 hour ago",
                    "info"
                ),
                self._create_alert_item(
                    "System Info",
                    "Daily backup completed successfully",
                    "2 hours ago",
                    "info"
                )
            ])
            
        ], style={'padding': '24px'})
    
    def create_settings_page(self):
        """Crea página de configuración"""
        return html.Div([
            html.H2("Settings & Configuration", style={
                'color': self.theme_colors['text_primary'],
                'marginBottom': '20px'
            }),
            
            # Settings sections
            html.Div([
                # Trading settings
                html.Div([
                    html.H4("Trading Parameters", style={
                        'color': self.theme_colors['text_primary'],
                        'marginBottom': '16px'
                    }),
                    
                    self._create_setting_item("Max Position Size", "input", "2.0", "%"),
                    self._create_setting_item("Stop Loss", "input", "2.5", "%"),
                    self._create_setting_item("Take Profit", "input", "5.0", "%"),
                    self._create_setting_item("Max Daily Loss", "input", "5.0", "%"),
                    
                ], style={
                    'flex': '1',
                    'padding': '20px',
                    'backgroundColor': self.theme_colors['secondary'],
                    'borderRadius': '12px',
                    'marginRight': '20px'
                }),
                
                # AI settings
                html.Div([
                    html.H4("AI Model Settings", style={
                        'color': self.theme_colors['text_primary'],
                        'marginBottom': '16px'
                    }),
                    
                    self._create_setting_item("Confidence Threshold", "input", "0.75", ""),
                    self._create_setting_item("Retrain Frequency", "select", "Daily", ""),
                    self._create_setting_item("Feature Selection", "select", "Auto", ""),
                    self._create_setting_item("Prediction Horizon", "input", "24", "hours"),
                    
                ], style={
                    'flex': '1',
                    'padding': '20px',
                    'backgroundColor': self.theme_colors['secondary'],
                    'borderRadius': '12px'
                })
            ], style={'display': 'flex', 'marginBottom': '24px'}),
            
            # Risk settings
            html.Div([
                html.H4("Risk Management", style={
                    'color': self.theme_colors['text_primary'],
                    'marginBottom': '16px'
                }),
                
                html.Div([
                    self._create_setting_item("Portfolio VaR Limit", "input", "1000", "$"),
                    self._create_setting_item("Max Correlation", "input", "0.8", ""),
                    self._create_setting_item("Leverage Limit", "input", "3", "x"),
                    self._create_setting_item("Emergency Stop", "toggle", "Enabled", ""),
                ], style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(2, 1fr)',
                    'gap': '16px'
                })
                
            ], style={
                'padding': '20px',
                'backgroundColor': self.theme_colors['secondary'],
                'borderRadius': '12px',
                'marginBottom': '24px'
            }),
            
            # Save button
            html.Div([
                html.Button([
                    html.I(className="fas fa-save", style={'marginRight': '8px'}),
                    "Save Settings"
                ], style={
                    'padding': '12px 24px',
                    'backgroundColor': self.theme_colors['success'],
                    'color': self.theme_colors['primary'],
                    'border': 'none',
                    'borderRadius': '8px',
                    'fontWeight': '600',
                    'fontSize': '14px',
                    'cursor': 'pointer'
                }),
                
                html.Button([
                    html.I(className="fas fa-undo", style={'marginRight': '8px'}),
                    "Reset to Defaults"
                ], style={
                    'padding': '12px 24px',
                    'backgroundColor': 'transparent',
                    'color': self.theme_colors['text_secondary'],
                    'border': f'1px solid {self.theme_colors["border"]}',
                    'borderRadius': '8px',
                    'fontWeight': '600',
                    'fontSize': '14px',
                    'cursor': 'pointer',
                    'marginLeft': '12px'
                })
            ], style={'textAlign': 'right'})
            
        ], style={'padding': '24px'})
    
    def _create_alert_item(self, title, message, time, severity):
        """Crea un elemento de alerta"""
        severity_colors = {
            'success': self.theme_colors['success'],
            'warning': self.theme_colors['warning'],
            'danger': self.theme_colors['danger'],
            'info': self.theme_colors['info']
        }
        
        severity_icons = {
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'danger': 'fas fa-times-circle',
            'info': 'fas fa-info-circle'
        }
        
        return html.Div([
            html.Div([
                html.I(className=severity_icons.get(severity, 'fas fa-info-circle'), style={
                    'fontSize': '18px',
                    'color': severity_colors.get(severity, self.theme_colors['info']),
                    'marginRight': '12px'
                }),
                html.Div([
                    html.Div(title, style={
                        'fontWeight': '600',
                        'color': self.theme_colors['text_primary'],
                        'marginBottom': '4px'
                    }),
                    html.Div(message, style={
                        'color': self.theme_colors['text_secondary'],
                        'fontSize': '14px'
                    })
                ], style={'flex': '1'}),
                html.Div(time, style={
                    'fontSize': '12px',
                    'color': self.theme_colors['text_secondary']
                })
            ], style={
                'display': 'flex',
                'alignItems': 'center'
            })
        ], style={
            'padding': '16px',
            'backgroundColor': self.theme_colors['secondary'],
            'borderRadius': '8px',
            'border': f'1px solid {self.theme_colors["border"]}',
            'marginBottom': '12px',
            'transition': 'all 0.2s ease',
            'cursor': 'pointer'
        })
    
    def _create_setting_item(self, label, input_type, value, unit=""):
        """Crea un elemento de configuración"""
        input_element = None
        
        if input_type == "input":
            input_element = dcc.Input(
                value=value,
                type="number" if unit in ["%", "$", "x", "hours"] else "text",
                style={
                    'width': '100%',
                    'padding': '8px 12px',
                    'backgroundColor': self.theme_colors['primary'],
                    'border': f'1px solid {self.theme_colors["border"]}',
                    'borderRadius': '6px',
                    'color': self.theme_colors['text_primary']
                }
            )
        elif input_type == "select":
            input_element = dcc.Dropdown(
                value=value,
                options=[{'label': value, 'value': value}],  # Simplificado
                style={'backgroundColor': self.theme_colors['primary']}
            )
        elif input_type == "toggle":
            input_element = html.Div([
                html.Span("Enabled", style={
                    'color': self.theme_colors['success'],
                    'fontWeight': '600'
                })
            ])
        
        return html.Div([
            html.Label(label, style={
                'color': self.theme_colors['text_secondary'],
                'fontSize': '14px',
                'fontWeight': '500',
                'marginBottom': '8px',
                'display': 'block'
            }),
            html.Div([
                input_element,
                html.Span(unit, style={
                    'color': self.theme_colors['text_secondary'],
                    'marginLeft': '8px',
                    'fontSize': '14px'
                }) if unit else None
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style={'marginBottom': '16px'})
    
    def create_metric_card(self, title, value, icon, color_type="info"):
        """Función de compatibilidad para crear tarjetas de métricas"""
        return self._create_metric_card(title, value, icon, color_type)


# === FUNCIONES AUXILIARES ===

def create_page_layout(page_content):
    """Crea el layout base de una página"""
    layout_components = EnhancedLayoutComponents()
    
    return html.Div([
        layout_components.create_enhanced_header(),
        html.Div([
            page_content
        ], id='page-content')
    ])

def get_theme_colors():
    """Retorna los colores del tema"""
    return {
        'primary': '#0d1117',
        'secondary': '#161b22',
        'surface': '#21262d',
        'accent': '#58a6ff',
        'success': '#3fb950',
        'danger': '#f85149',
        'warning': '#d29922',
        'info': '#79c0ff',
        'text_primary': '#f0f6fc',
        'text_secondary': '#8b949e',
        'grid': '#30363d',
        'border': '#21262d'
    }
