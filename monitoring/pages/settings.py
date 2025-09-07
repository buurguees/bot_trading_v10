"""
monitoring/pages/settings.py
Página de configuración del sistema
"""

from dash import html, dcc, dash_table
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SettingsPage:
    """Página de configuración del sistema"""
    
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
    
    def create_settings_page(self):
        """Crea la página de configuración"""
        return html.Div([
            # Configuración del bot
            html.Div([
                html.H3("⚙️ Configuración del Bot", style={'color': self.theme_colors['text_primary'], 'marginBottom': '20px'}),
                
                # Configuración de trading
                html.Div([
                    html.H4("📈 Configuración de Trading", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                    
                    html.Div([
                        html.Div([
                            html.Label("Balance Inicial:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="initial-balance",
                                type="number",
                                value=1000,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'}),
                        
                        html.Div([
                            html.Label("Objetivo:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="target-balance",
                                type="number",
                                value=1000000,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'}),
                        
                        html.Div([
                            html.Label("Riesgo por Trade (%):", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="risk-per-trade",
                                type="number",
                                value=1.0,
                                step=0.1,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'})
                    ], style={'marginBottom': '20px'}),
                    
                    html.Div([
                        html.Div([
                            html.Label("Confianza Mínima:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="min-confidence",
                                type="number",
                                value=0.75,
                                step=0.05,
                                min=0.1,
                                max=1.0,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'}),
                        
                        html.Div([
                            html.Label("Stop Loss (%):", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="stop-loss",
                                type="number",
                                value=1.0,
                                step=0.1,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'}),
                        
                        html.Div([
                            html.Label("Risk/Reward Ratio:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                            dcc.Input(
                                id="risk-reward-ratio",
                                type="number",
                                value=3.0,
                                step=0.1,
                                style={'width': '150px', 'display': 'inline-block'}
                            )
                        ], style={'margin': '10px', 'display': 'inline-block'})
                    ], style={'marginBottom': '20px'})
                ], style={'marginBottom': '30px'})
            ]),
            
            # Configuración de datos
            html.Div([
                html.H4("📊 Configuración de Datos", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                
                html.Div([
                    html.Div([
                        html.Label("Símbolos a Monitorear:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                        dcc.Dropdown(
                            id="symbols-selector",
                            options=[
                                {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                                {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                                {'label': 'ADAUSDT', 'value': 'ADAUSDT'},
                                {'label': 'SOLUSDT', 'value': 'SOLUSDT'}
                            ],
                            value=['BTCUSDT', 'ETHUSDT'],
                            multi=True,
                            style={'width': '300px', 'display': 'inline-block'}
                        )
                    ], style={'margin': '10px', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label("Período de Datos:", style={'color': self.theme_colors['text_secondary'], 'marginRight': '10px'}),
                        dcc.Dropdown(
                            id="data-period",
                            options=[
                                {'label': '1 año', 'value': '1y'},
                                {'label': '2 años', 'value': '2y'},
                                {'label': '3 años', 'value': '3y'},
                                {'label': '5 años', 'value': '5y'}
                            ],
                            value='3y',
                            style={'width': '150px', 'display': 'inline-block'}
                        )
                    ], style={'margin': '10px', 'display': 'inline-block'})
                ], style={'marginBottom': '20px'})
            ], style={'marginBottom': '30px'}),
            
            # Botones de acción
            html.Div([
                html.Button("💾 Guardar Configuración", id="save-settings-btn", className="action-btn"),
                html.Button("🔄 Restaurar Valores", id="reset-settings-btn", className="action-btn"),
                html.Button("📥 Exportar Config", id="export-config-btn", className="action-btn"),
                html.Button("📤 Importar Config", id="import-config-btn", className="action-btn")
            ], style={'textAlign': 'center', 'marginTop': '30px'}),
            
            # Estado del sistema
            html.Div([
                html.H4("🔧 Estado del Sistema", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                html.Div(id="system-status-table")
            ], style={'marginTop': '30px'})
            
        ], className="page-content")

# Función de conveniencia para compatibilidad
def create_settings_page():
    """Función de conveniencia para crear la página de settings"""
    settings_page = SettingsPage()
    return settings_page.create_settings_page()
