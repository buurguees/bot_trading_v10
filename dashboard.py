#!/usr/bin/env python3
"""
Dashboard Independiente del Trading Bot v10
===========================================

Dashboard web completamente independiente para monitorear el bot de trading.
No depende de módulos complejos del sistema.

Uso:
    python dashboard.py
    python dashboard.py --port 8050 --debug
"""

import sys
import os
import logging
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DASHBOARD - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dashboard.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

try:
    import dash
    from dash import html, dcc, Input, Output, State, callback
    import dash_bootstrap_components as dbc
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Error: Faltan dependencias para el dashboard: {e}")
    print("Instala con: pip install dash dash-bootstrap-components plotly pandas")
    sys.exit(1)

class IndependentDashboard:
    """Dashboard independiente del Trading Bot v10"""
    
    def __init__(self):
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            suppress_callback_exceptions=True
        )
        self.setup_layout()
        self.setup_callbacks()
        logger.info("Dashboard independiente inicializado")
    
    def setup_layout(self):
        """Configura el layout del dashboard"""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🤖 Trading Bot v10 - Dashboard", className="text-center mb-4"),
                    html.P("Monitoreo en tiempo real del sistema de trading", className="text-center text-muted")
                ])
            ]),
            
            # Métricas principales
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Símbolos Activos", className="card-title"),
                            html.H2(id="active-symbols", className="text-primary")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Modelos Entrenados", className="card-title"),
                            html.H2(id="trained-models", className="text-success")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Datos Históricos", className="card-title"),
                            html.H2(id="historical-data", className="text-info")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Estado del Sistema", className="card-title"),
                            html.H2(id="system-status", className="text-warning")
                        ])
                    ])
                ], width=3)
            ], className="mb-4"),
            
            # Gráficos
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Rendimiento de Modelos"),
                        dbc.CardBody([
                            dcc.Graph(id="model-performance-chart")
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Datos Históricos por Símbolo"),
                        dbc.CardBody([
                            dcc.Graph(id="historical-data-chart")
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            # Tabla de símbolos
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Estado de Símbolos"),
                        dbc.CardBody([
                            html.Div(id="symbols-table")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            # Controles
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Controles del Sistema"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button("Actualizar Datos", id="refresh-btn", color="primary", className="me-2"),
                                    dbc.Button("Entrenar Modelos", id="train-btn", color="success", className="me-2"),
                                    dbc.Button("Descargar Histórico", id="download-btn", color="info")
                                ])
                            ]),
                            html.Hr(),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Símbolos:"),
                                    dcc.Dropdown(
                                        id="symbols-dropdown",
                                        options=[
                                            {"label": "BTCUSDT", "value": "BTCUSDT"},
                                            {"label": "ETHUSDT", "value": "ETHUSDT"},
                                            {"label": "ADAUSDT", "value": "ADAUSDT"},
                                            {"label": "SOLUSDT", "value": "SOLUSDT"},
                                            {"label": "DOGEUSDT", "value": "DOGEUSDT"},
                                            {"label": "AVAXUSDT", "value": "AVAXUSDT"},
                                            {"label": "TONUSDT", "value": "TONUSDT"},
                                            {"label": "BNBUSDT", "value": "BNBUSDT"},
                                            {"label": "XRPUSDT", "value": "XRPUSDT"},
                                            {"label": "LINKUSDT", "value": "LINKUSDT"}
                                        ],
                                        value=["BTCUSDT", "ETHUSDT"],
                                        multi=True
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label("Acción:"),
                                    dcc.Dropdown(
                                        id="action-dropdown",
                                        options=[
                                            {"label": "Analizar", "value": "analyze"},
                                            {"label": "Validar", "value": "validate"},
                                            {"label": "Entrenar", "value": "train"}
                                        ],
                                        value="analyze"
                                    )
                                ], width=6)
                            ])
                        ])
                    ])
                ], width=12)
            ]),
            
            # Intervalo de actualización
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # 30 segundos
                n_intervals=0
            ),
            
            # Stores para datos
            dcc.Store(id='dashboard-data-store')
            
        ], fluid=True)
    
    def setup_callbacks(self):
        """Configura los callbacks del dashboard"""
        
        @self.app.callback(
            [Output('active-symbols', 'children'),
             Output('trained-models', 'children'),
             Output('historical-data', 'children'),
             Output('system-status', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_metrics(n):
            """Actualiza las métricas principales"""
            try:
                # Contar símbolos activos (configurados)
                symbols = self.get_configured_symbols()
                active_symbols = len(symbols)
                
                # Contar modelos entrenados
                models_dir = Path("models")
                trained_models = len(list(models_dir.glob("*_model.json"))) if models_dir.exists() else 0
                
                # Contar archivos de datos históricos
                historical_dir = Path("data/historical")
                historical_files = len(list(historical_dir.glob("*.csv"))) if historical_dir.exists() else 0
                
                # Estado del sistema
                system_status = "OK" if trained_models > 0 else "Sin Modelos"
                
                return active_symbols, trained_models, historical_files, system_status
                
            except Exception as e:
                logger.error(f"Error actualizando métricas: {e}")
                return "Error", "Error", "Error", "Error"
        
        @self.app.callback(
            Output('model-performance-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_model_performance_chart(n):
            """Actualiza el gráfico de rendimiento de modelos"""
            try:
                models_data = self.get_models_data()
                
                if not models_data:
                    return go.Figure().add_annotation(
                        text="No hay datos de modelos disponibles",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                symbols = list(models_data.keys())
                accuracies = [models_data[symbol].get('test_accuracy', 0) for symbol in symbols]
                
                fig = go.Figure(data=[
                    go.Bar(x=symbols, y=accuracies, name='Accuracy')
                ])
                
                fig.update_layout(
                    title="Rendimiento de Modelos por Símbolo",
                    xaxis_title="Símbolo",
                    yaxis_title="Accuracy",
                    yaxis=dict(range=[0, 1])
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error actualizando gráfico de modelos: {e}")
                return go.Figure()
        
        @self.app.callback(
            Output('historical-data-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_historical_data_chart(n):
            """Actualiza el gráfico de datos históricos"""
            try:
                historical_data = self.get_historical_data_summary()
                
                if not historical_data:
                    return go.Figure().add_annotation(
                        text="No hay datos históricos disponibles",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                symbols = list(historical_data.keys())
                data_points = [historical_data[symbol].get('rows', 0) for symbol in symbols]
                
                fig = go.Figure(data=[
                    go.Bar(x=symbols, y=data_points, name='Puntos de Datos')
                ])
                
                fig.update_layout(
                    title="Datos Históricos por Símbolo",
                    xaxis_title="Símbolo",
                    yaxis_title="Número de Puntos de Datos"
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error actualizando gráfico histórico: {e}")
                return go.Figure()
        
        @self.app.callback(
            Output('symbols-table', 'children'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_symbols_table(n):
            """Actualiza la tabla de símbolos"""
            try:
                symbols_data = self.get_symbols_status()
                
                if not symbols_data:
                    return html.P("No hay datos de símbolos disponibles")
                
                table_rows = []
                for symbol, data in symbols_data.items():
                    status_color = "success" if data.get('has_model', False) else "warning"
                    table_rows.append(
                        dbc.Row([
                            dbc.Col(symbol, width=2),
                            dbc.Col(
                                dbc.Badge("Modelo", color=status_color) if data.get('has_model', False) else "Sin Modelo",
                                width=2
                            ),
                            dbc.Col(f"{data.get('data_points', 0)} puntos", width=2),
                            dbc.Col(f"Accuracy: {data.get('accuracy', 0):.3f}", width=3),
                            dbc.Col(data.get('last_update', 'N/A'), width=3)
                        ], className="mb-2")
                    )
                
                return table_rows
                
            except Exception as e:
                logger.error(f"Error actualizando tabla de símbolos: {e}")
                return html.P(f"Error: {e}")
    
    def get_configured_symbols(self) -> List[str]:
        """Obtiene los símbolos configurados"""
        # Símbolos por defecto del sistema
        return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT', 
                'AVAXUSDT', 'TONUSDT', 'BNBUSDT', 'XRPUSDT', 'LINKUSDT']
    
    def get_models_data(self) -> Dict[str, Any]:
        """Obtiene datos de los modelos entrenados"""
        models_data = {}
        models_dir = Path("models")
        
        if models_dir.exists():
            for model_file in models_dir.glob("*_model.json"):
                try:
                    with open(model_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        symbol = data.get('symbol', model_file.stem.replace('_model', ''))
                        models_data[symbol] = data.get('model', {})
                except Exception as e:
                    logger.error(f"Error leyendo modelo {model_file}: {e}")
        
        return models_data
    
    def get_historical_data_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de datos históricos"""
        historical_data = {}
        historical_dir = Path("data/historical")
        
        if historical_dir.exists():
            for csv_file in historical_dir.glob("*.csv"):
                try:
                    symbol = csv_file.stem.split('_')[0]
                    df = pd.read_csv(csv_file)
                    historical_data[symbol] = {
                        'rows': len(df),
                        'last_update': datetime.fromtimestamp(csv_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    }
                except Exception as e:
                    logger.error(f"Error leyendo datos históricos {csv_file}: {e}")
        
        return historical_data
    
    def get_symbols_status(self) -> Dict[str, Any]:
        """Obtiene el estado de todos los símbolos"""
        symbols_status = {}
        symbols = self.get_configured_symbols()
        
        for symbol in symbols:
            # Verificar si tiene modelo
            model_file = Path(f"models/{symbol}_model.json")
            has_model = model_file.exists()
            
            # Verificar datos históricos
            historical_file = Path(f"data/historical/{symbol}_1m.csv")
            data_points = 0
            if historical_file.exists():
                try:
                    df = pd.read_csv(historical_file)
                    data_points = len(df)
                except:
                    pass
            
            # Obtener accuracy del modelo
            accuracy = 0
            if has_model:
                try:
                    with open(model_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        accuracy = data.get('model', {}).get('test_results', {}).get('test_accuracy', 0)
                except:
                    pass
            
            symbols_status[symbol] = {
                'has_model': has_model,
                'data_points': data_points,
                'accuracy': accuracy,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
        
        return symbols_status
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """Ejecuta el dashboard"""
        try:
            logger.info(f"Iniciando dashboard en http://{host}:{port}")
            self.app.run_server(host=host, port=port, debug=debug)
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
            raise

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Dashboard Independiente del Trading Bot v10")
    parser.add_argument('--host', default='127.0.0.1', help='Host del servidor')
    parser.add_argument('--port', type=int, default=8050, help='Puerto del servidor')
    parser.add_argument('--debug', action='store_true', help='Modo debug')
    
    args = parser.parse_args()
    
    # Crear directorio de logs
    Path("logs").mkdir(exist_ok=True)
    
    # Crear y ejecutar dashboard
    dashboard = IndependentDashboard()
    dashboard.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
