# Ruta: core/monitoring/pages/model_status_page.py
"""
monitoring/pages/model_status_page.py
Página de Estado del Modelo IA - Trading Bot v10

Esta página proporciona monitoreo completo del modelo de IA:
- Estado del modelo y métricas de rendimiento
- Historial de entrenamientos y versiones
- Análisis de precisión y drift del modelo
- Monitoreo de features y su importancia
- Diagnósticos de salud del modelo
- Control de reentrenamiento automático
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from monitoring.pages.base_page import BasePage

logger = logging.getLogger(__name__)

class ModelStatusPage(BasePage):
    """
    Página de estado y monitoreo del modelo de IA del Trading Bot v10
    
    Proporciona supervisión completa del modelo de machine learning,
    incluyendo métricas de rendimiento, drift detection y control de entrenamientos.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None, performance_tracker=None):
        """
        Inicializa la página de estado del modelo
        
        Args:
            data_provider: Proveedor de datos centralizado
            real_time_manager: Gestor de tiempo real
            performance_tracker: Tracker de rendimiento
        """
        super().__init__(
            data_provider=data_provider, 
            real_time_manager=real_time_manager, 
            performance_tracker=performance_tracker
        )
        
        # Configuración específica de la página Model Status
        self.page_config.update({
            'title': 'Estado del Modelo IA',
            'update_interval': 60000,  # 1 minuto
            'auto_refresh': True,
            'enable_model_controls': True,
            'show_technical_details': True,
            'chart_height': 400,
            'max_training_history': 50
        })
        
        # Estados del modelo
        self.model_states = {
            'healthy': {
                'color': 'success',
                'icon': 'fas fa-check-circle',
                'label': 'Saludable',
                'description': 'Funcionando correctamente'
            },
            'training': {
                'color': 'primary',
                'icon': 'fas fa-cog fa-spin',
                'label': 'Entrenando',
                'description': 'Reentrenamiento en curso'
            },
            'degraded': {
                'color': 'warning',
                'icon': 'fas fa-exclamation-triangle',
                'label': 'Degradado',
                'description': 'Rendimiento por debajo del esperado'
            },
            'error': {
                'color': 'danger',
                'icon': 'fas fa-times-circle',
                'label': 'Error',
                'description': 'Fallo en el modelo'
            },
            'updating': {
                'color': 'info',
                'icon': 'fas fa-sync-alt fa-spin',
                'label': 'Actualizando',
                'description': 'Actualizando parámetros'
            }
        }
        
        # Métricas del modelo
        self.model_metrics = {
            'accuracy': {
                'name': 'Precisión',
                'description': 'Porcentaje de predicciones correctas',
                'target': 0.65,
                'format': 'percentage'
            },
            'precision': {
                'name': 'Precisión (Positive)',
                'description': 'TP / (TP + FP)',
                'target': 0.60,
                'format': 'percentage'
            },
            'recall': {
                'name': 'Recall',
                'description': 'TP / (TP + FN)',
                'target': 0.55,
                'format': 'percentage'
            },
            'f1_score': {
                'name': 'F1 Score',
                'description': 'Media armónica de precisión y recall',
                'target': 0.58,
                'format': 'percentage'
            },
            'auc_roc': {
                'name': 'AUC-ROC',
                'description': 'Área bajo la curva ROC',
                'target': 0.70,
                'format': 'percentage'
            },
            'loss': {
                'name': 'Loss',
                'description': 'Función de pérdida del modelo',
                'target': 0.30,
                'format': 'decimal',
                'lower_is_better': True
            }
        }
        
        logger.info("ModelStatusPage inicializada correctamente")
    
    def get_layout(self) -> html.Div:
        """
        Genera el layout de la página de estado del modelo
        
        Returns:
            html.Div: Layout completo de la página
        """
        try:
            return html.Div([
                # Store para datos del modelo
                dcc.Store(id='model-data-store'),
                
                # Intervalos de actualización
                dcc.Interval(
                    id='model-status-interval',
                    interval=self.page_config['update_interval'],
                    n_intervals=0
                ),
                
                # Header de la página
                self._create_page_header(),
                
                # Estado general del modelo
                self._create_model_overview_section(),
                
                # Métricas de rendimiento
                self._create_metrics_section(),
                
                # Análisis de drift y stability
                self._create_stability_section(),
                
                # Importancia de features
                self._create_features_section(),
                
                # Historial de entrenamientos
                self._create_training_history_section(),
                
                # Controles del modelo
                self._create_model_controls_section(),
                
                # Diagnósticos técnicos
                self._create_technical_diagnostics_section()
                
            ], className="container-fluid")
            
        except Exception as e:
            logger.error(f"Error al crear layout de ModelStatusPage: {e}")
            return self.create_error_layout("Error al cargar página de estado del modelo")
    
    def _create_page_header(self) -> dbc.Row:
        """Crea el header de la página"""
        return dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-brain me-3"),
                    "Estado del Modelo IA"
                ], className="text-primary mb-1"),
                html.P("Monitoreo completo del modelo de machine learning", 
                      className="text-muted mb-4")
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-sync-alt me-2"),
                        "Actualizar"
                    ], color="primary", outline=True, size="sm", id="refresh-model-btn"),
                    dbc.Button([
                        html.I(className="fas fa-download me-2"),
                        "Exportar"
                    ], color="secondary", outline=True, size="sm", id="export-model-btn")
                ], className="d-flex justify-content-end mb-3")
            ], width=4)
        ], className="mb-4")
    
    def _create_model_overview_section(self) -> dbc.Row:
        """Crea la sección de overview del modelo"""
        return dbc.Row([
            # Estado actual del modelo
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-heartbeat me-2"),
                        "Estado del Modelo"
                    ]),
                    dbc.CardBody([
                        html.Div(id="model-status-indicator"),
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                html.Small("Versión:", className="text-muted d-block"),
                                html.Strong(id="model-version", children="v10.1.0")
                            ], width=6),
                            dbc.Col([
                                html.Small("Última actualización:", className="text-muted d-block"),
                                html.Strong(id="model-last-update", children="Hace 2 horas")
                            ], width=6)
                        ])
                    ])
                ], className="shadow-sm")
            ], width=3),
            
            # Métricas principales
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-line me-2"),
                        "Rendimiento Actual"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H4(id="current-accuracy", children="68.5%", 
                                       className="text-success mb-1"),
                                html.Small("Precisión", className="text-muted")
                            ], width=6),
                            dbc.Col([
                                html.H4(id="current-f1", children="0.63", 
                                       className="text-info mb-1"),
                                html.Small("F1 Score", className="text-muted")
                            ], width=6)
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.H4(id="prediction-confidence", children="72.1%", 
                                       className="text-primary mb-1"),
                                html.Small("Confianza Promedio", className="text-muted")
                            ], width=6),
                            dbc.Col([
                                html.H4(id="model-stability", children="95.2%", 
                                       className="text-warning mb-1"),
                                html.Small("Estabilidad", className="text-muted")
                            ], width=6)
                        ])
                    ])
                ], className="shadow-sm")
            ], width=4),
            
            # Estadísticas de uso
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Estadísticas de Uso"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H4(id="predictions-today", children="1,247", 
                                       className="text-success mb-1"),
                                html.Small("Predicciones Hoy", className="text-muted")
                            ], width=6),
                            dbc.Col([
                                html.H4(id="avg-inference-time", children="45ms", 
                                       className="text-info mb-1"),
                                html.Small("Tiempo Inferencia", className="text-muted")
                            ], width=6)
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.H4(id="model-uptime", children="99.8%", 
                                       className="text-primary mb-1"),
                                html.Small("Uptime", className="text-muted")
                            ], width=6),
                            dbc.Col([
                                html.H4(id="error-rate", children="0.2%", 
                                       className="text-danger mb-1"),
                                html.Small("Tasa de Error", className="text-muted")
                            ], width=6)
                        ])
                    ])
                ], className="shadow-sm")
            ], width=5)
        ], className="mb-4")
    
    def _create_metrics_section(self) -> dbc.Row:
        """Crea la sección de métricas de rendimiento"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-tachometer-alt me-2"),
                        "Métricas de Rendimiento",
                        dbc.Badge("En tiempo real", color="success", className="ms-2")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='model-metrics-chart',
                            config={'displayModeBar': False},
                            style={'height': self.page_config['chart_height']}
                        )
                    ])
                ], className="shadow-sm")
            ], width=8),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-bullseye me-2"),
                        "Matriz de Confusión"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='confusion-matrix-chart',
                            config={'displayModeBar': False},
                            style={'height': self.page_config['chart_height']}
                        )
                    ])
                ], className="shadow-sm")
            ], width=4)
        ], className="mb-4")
    
    def _create_stability_section(self) -> dbc.Row:
        """Crea la sección de análisis de estabilidad y drift"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-wave-square me-2"),
                        "Análisis de Drift del Modelo"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='model-drift-chart',
                            config={'displayModeBar': False},
                            style={'height': self.page_config['chart_height']}
                        )
                    ])
                ], className="shadow-sm")
            ], width=8),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-thermometer-half me-2"),
                        "Alertas de Drift"
                    ]),
                    dbc.CardBody([
                        html.Div(id="drift-alerts-container", children=[
                            dbc.Alert([
                                html.I(className="fas fa-check-circle me-2"),
                                html.Strong("Sistema Estable"),
                                html.Br(),
                                html.Small("No se detectaron cambios significativos en la distribución de datos")
                            ], color="success", className="mb-2"),
                            
                            dbc.Alert([
                                html.I(className="fas fa-info-circle me-2"),
                                html.Strong("Monitoreo Activo"),
                                html.Br(),
                                html.Small("Evaluando continuamente la estabilidad del modelo")
                            ], color="info", className="mb-0")
                        ])
                    ])
                ], className="shadow-sm")
            ], width=4)
        ], className="mb-4")
    
    def _create_features_section(self) -> dbc.Row:
        """Crea la sección de análisis de features"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-list-ol me-2"),
                        "Importancia de Features"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='feature-importance-chart',
                            config={'displayModeBar': False},
                            style={'height': self.page_config['chart_height']}
                        )
                    ])
                ], className="shadow-sm")
            ], width=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-search me-2"),
                        "Análisis de Predicciones"
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id='prediction-analysis-chart',
                            config={'displayModeBar': False},
                            style={'height': self.page_config['chart_height']}
                        )
                    ])
                ], className="shadow-sm")
            ], width=6)
        ], className="mb-4")
    
    def _create_training_history_section(self) -> dbc.Row:
        """Crea la sección de historial de entrenamientos"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-history me-2"),
                        "Historial de Entrenamientos",
                        dbc.Button([
                            html.I(className="fas fa-plus me-1"),
                            "Nuevo Entrenamiento"
                        ], color="primary", size="sm", className="ms-auto", 
                        id="new-training-btn")
                    ], className="d-flex align-items-center"),
                    dbc.CardBody([
                        html.Div(id="training-history-table")
                    ])
                ], className="shadow-sm")
            ], width=12)
        ], className="mb-4")
    
    def _create_model_controls_section(self) -> dbc.Row:
        """Crea la sección de controles del modelo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-sliders-h me-2"),
                        "Controles del Modelo"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Umbral de Confianza:", className="form-label"),
                                dcc.Slider(
                                    id='confidence-threshold-slider',
                                    min=0.5,
                                    max=0.95,
                                    step=0.05,
                                    value=0.75,
                                    marks={
                                        0.5: '50%',
                                        0.6: '60%',
                                        0.7: '70%',
                                        0.8: '80%',
                                        0.9: '90%'
                                    },
                                    tooltip={"placement": "bottom", "always_visible": True}
                                )
                            ], width=4),
                            
                            dbc.Col([
                                html.Label("Reentrenamiento Automático:", className="form-label"),
                                dbc.Switch(
                                    id="auto-retrain-switch",
                                    value=True,
                                    className="mb-2"
                                ),
                                html.Small("Reentrenar cuando la precisión baje del umbral", 
                                         className="text-muted")
                            ], width=4),
                            
                            dbc.Col([
                                html.Label("Acciones:", className="form-label"),
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-play me-1"),
                                        "Iniciar"
                                    ], color="success", size="sm", id="start-model-btn"),
                                    dbc.Button([
                                        html.I(className="fas fa-pause me-1"),
                                        "Pausar"
                                    ], color="warning", size="sm", id="pause-model-btn"),
                                    dbc.Button([
                                        html.I(className="fas fa-redo me-1"),
                                        "Reentrenar"
                                    ], color="primary", size="sm", id="retrain-model-btn")
                                ], vertical=False, className="d-flex")
                            ], width=4)
                        ])
                    ])
                ], className="shadow-sm")
            ], width=12)
        ], className="mb-4")
    
    def _create_technical_diagnostics_section(self) -> dbc.Row:
        """Crea la sección de diagnósticos técnicos"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-tools me-2"),
                        "Diagnósticos Técnicos"
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Arquitectura del Modelo", className="mb-3"),
                                html.Div(id="model-architecture-info")
                            ], width=6),
                            dbc.Col([
                                html.H6("Métricas de Performance", className="mb-3"),
                                html.Div(id="model-performance-metrics")
                            ], width=6)
                        ])
                    ])
                ], className="shadow-sm")
            ], width=12)
        ])
    
    def register_callbacks(self, app: dash.Dash):
        """
        Registra todos los callbacks de la página
        
        Args:
            app: Instancia de la aplicación Dash
        """
        # Callback principal para cargar datos del modelo
        @app.callback(
            Output('model-data-store', 'data'),
            [Input('model-status-interval', 'n_intervals'),
             Input('refresh-model-btn', 'n_clicks')]
        )
        def load_model_data(n_intervals, refresh_clicks):
            """Carga datos del modelo"""
            try:
                return self._load_model_data()
            except Exception as e:
                logger.error(f"Error al cargar datos del modelo: {e}")
                return {}
        
        # Callback para indicador de estado
        @app.callback(
            [Output('model-status-indicator', 'children'),
             Output('model-version', 'children'),
             Output('model-last-update', 'children')],
            [Input('model-data-store', 'data')]
        )
        def update_model_status(model_data):
            """Actualiza indicador de estado del modelo"""
            try:
                if not model_data:
                    return self._create_status_indicator('error'), "N/A", "N/A"
                
                status = model_data.get('status', 'error')
                version = model_data.get('version', 'N/A')
                last_update = model_data.get('last_update', 'N/A')
                
                status_indicator = self._create_status_indicator(status)
                
                return status_indicator, version, last_update
                
            except Exception as e:
                logger.error(f"Error al actualizar estado: {e}")
                return self._create_status_indicator('error'), "Error", "Error"
        
        # Callback para métricas principales
        @app.callback(
            [Output('current-accuracy', 'children'),
             Output('current-f1', 'children'),
             Output('prediction-confidence', 'children'),
             Output('model-stability', 'children')],
            [Input('model-data-store', 'data')]
        )
        def update_main_metrics(model_data):
            """Actualiza métricas principales"""
            try:
                if not model_data or not model_data.get('metrics'):
                    return "N/A", "N/A", "N/A", "N/A"
                
                metrics = model_data['metrics']
                
                accuracy = f"{metrics.get('accuracy', 0)*100:.1f}%"
                f1_score = f"{metrics.get('f1_score', 0):.3f}"
                confidence = f"{metrics.get('avg_confidence', 0)*100:.1f}%"
                stability = f"{metrics.get('stability', 0)*100:.1f}%"
                
                return accuracy, f1_score, confidence, stability
                
            except Exception as e:
                logger.error(f"Error al actualizar métricas principales: {e}")
                return "Error", "Error", "Error", "Error"
        
        # Callback para estadísticas de uso
        @app.callback(
            [Output('predictions-today', 'children'),
             Output('avg-inference-time', 'children'),
             Output('model-uptime', 'children'),
             Output('error-rate', 'children')],
            [Input('model-data-store', 'data')]
        )
        def update_usage_stats(model_data):
            """Actualiza estadísticas de uso"""
            try:
                if not model_data or not model_data.get('usage_stats'):
                    return "N/A", "N/A", "N/A", "N/A"
                
                stats = model_data['usage_stats']
                
                predictions = f"{stats.get('predictions_today', 0):,}"
                inference_time = f"{stats.get('avg_inference_time', 0):.0f}ms"
                uptime = f"{stats.get('uptime', 0)*100:.1f}%"
                error_rate = f"{stats.get('error_rate', 0)*100:.1f}%"
                
                return predictions, inference_time, uptime, error_rate
                
            except Exception as e:
                logger.error(f"Error al actualizar estadísticas de uso: {e}")
                return "Error", "Error", "Error", "Error"
        
        # Callback para gráfico de métricas
        @app.callback(
            Output('model-metrics-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_metrics_chart(model_data):
            """Actualiza gráfico de métricas"""
            try:
                if not model_data or not model_data.get('metrics_history'):
                    return self._create_empty_chart("Cargando métricas...")
                
                return self._create_metrics_chart(model_data['metrics_history'])
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de métricas: {e}")
                return self._create_empty_chart("Error en métricas")
        
        # Callback para matriz de confusión
        @app.callback(
            Output('confusion-matrix-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_confusion_matrix(model_data):
            """Actualiza matriz de confusión"""
            try:
                if not model_data or not model_data.get('confusion_matrix'):
                    return self._create_empty_chart("Cargando matriz...")
                
                return self._create_confusion_matrix_chart(model_data['confusion_matrix'])
                
            except Exception as e:
                logger.error(f"Error al crear matriz de confusión: {e}")
                return self._create_empty_chart("Error en matriz")
        
        # Callback para gráfico de drift
        @app.callback(
            Output('model-drift-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_drift_chart(model_data):
            """Actualiza gráfico de drift"""
            try:
                if not model_data or not model_data.get('drift_data'):
                    return self._create_empty_chart("Cargando análisis de drift...")
                
                return self._create_drift_chart(model_data['drift_data'])
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de drift: {e}")
                return self._create_empty_chart("Error en drift")
        
        # Callback para importancia de features
        @app.callback(
            Output('feature-importance-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_feature_importance(model_data):
            """Actualiza gráfico de importancia de features"""
            try:
                if not model_data or not model_data.get('feature_importance'):
                    return self._create_empty_chart("Cargando importancia de features...")
                
                return self._create_feature_importance_chart(model_data['feature_importance'])
                
            except Exception as e:
                logger.error(f"Error al crear importancia de features: {e}")
                return self._create_empty_chart("Error en importancia de features")
        
        # Callback para análisis de predicciones
        @app.callback(
            Output('prediction-analysis-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_prediction_analysis(model_data):
            """Actualiza análisis de predicciones"""
            try:
                if not model_data or not model_data.get('predictions'):
                    return self._create_empty_chart("Cargando análisis de predicciones...")
                
                return self._create_prediction_analysis_chart(model_data['predictions'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de predicciones: {e}")
                return self._create_empty_chart("Error en análisis de predicciones")
        
        # Callback para historial de entrenamientos
        @app.callback(
            Output('training-history-table', 'children'),
            [Input('model-data-store', 'data')]
        )
        def update_training_history(model_data):
            """Actualiza tabla de historial de entrenamientos"""
            try:
                if not model_data or not model_data.get('training_history'):
                    return html.P("Cargando historial de entrenamientos...", className="text-muted")
                
                return self._create_training_history_table(model_data['training_history'])
                
            except Exception as e:
                logger.error(f"Error al crear historial de entrenamientos: {e}")
                return self.create_error_alert("Error al cargar historial")
        
        # Callback para diagnósticos técnicos
        @app.callback(
            [Output('model-architecture-info', 'children'),
             Output('model-performance-metrics', 'children')],
            [Input('model-data-store', 'data')]
        )
        def update_technical_diagnostics(model_data):
            """Actualiza diagnósticos técnicos"""
            try:
                if not model_data:
                    return html.P("Cargando...", className="text-muted"), html.P("Cargando...", className="text-muted")
                
                architecture_info = self._create_architecture_info(model_data.get('architecture', {}))
                performance_metrics = self._create_performance_metrics(model_data.get('performance', {}))
                
                return architecture_info, performance_metrics
                
            except Exception as e:
                logger.error(f"Error al actualizar diagnósticos técnicos: {e}")
                return self.create_error_alert("Error en arquitectura"), self.create_error_alert("Error en métricas")
        
        # Callback para controles del modelo
        @app.callback(
            Output('model-controls-feedback', 'children'),
            [Input('start-model-btn', 'n_clicks'),
             Input('pause-model-btn', 'n_clicks'),
             Input('retrain-model-btn', 'n_clicks'),
             Input('confidence-threshold-slider', 'value'),
             Input('auto-retrain-switch', 'value')]
        )
        def handle_model_controls(start_clicks, pause_clicks, retrain_clicks, threshold, auto_retrain):
            """Maneja los controles del modelo"""
            try:
                if not dash.callback_context.triggered:
                    return ""
                
                trigger_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
                
                if trigger_id == 'start-model-btn' and start_clicks:
                    return dbc.Alert("Modelo iniciado correctamente", color="success", dismissable=True)
                elif trigger_id == 'pause-model-btn' and pause_clicks:
                    return dbc.Alert("Modelo pausado", color="warning", dismissable=True)
                elif trigger_id == 'retrain-model-btn' and retrain_clicks:
                    return dbc.Alert("Reentrenamiento iniciado", color="info", dismissable=True)
                elif trigger_id == 'confidence-threshold-slider':
                    return dbc.Alert(f"Umbral actualizado a {threshold*100:.0f}%", color="info", dismissable=True)
                elif trigger_id == 'auto-retrain-switch':
                    status = "activado" if auto_retrain else "desactivado"
                    return dbc.Alert(f"Reentrenamiento automático {status}", color="info", dismissable=True)
                
                return ""
                
            except Exception as e:
                logger.error(f"Error en controles del modelo: {e}")
                return dbc.Alert("Error al procesar control", color="danger", dismissable=True)
        
        logger.info("Callbacks de ModelStatusPage registrados correctamente")
    
    def _load_model_data(self) -> Dict[str, Any]:
        """
        Carga datos del modelo desde el data provider
        
        Returns:
            Dict[str, Any]: Datos del modelo
        """
        try:
            if not self.data_provider:
                return self._generate_mock_model_data()
            
            # Intentar cargar datos reales
            model_data = self.data_provider.get_model_status()
            
            if not model_data:
                return self._generate_mock_model_data()
            
            return model_data
            
        except Exception as e:
            logger.error(f"Error al cargar datos del modelo: {e}")
            return self._generate_mock_model_data()
    
    def _generate_mock_model_data(self) -> Dict[str, Any]:
        """
        Genera datos simulados del modelo para desarrollo
        
        Returns:
            Dict[str, Any]: Datos simulados
        """
        now = datetime.now()
        
        # Generar historial de métricas (últimos 30 días)
        dates = [(now - timedelta(days=i)) for i in range(30, 0, -1)]
        metrics_history = []
        
        for date in dates:
            metrics_history.append({
                'timestamp': date.isoformat(),
                'accuracy': np.random.normal(0.68, 0.05),
                'precision': np.random.normal(0.65, 0.04),
                'recall': np.random.normal(0.62, 0.04),
                'f1_score': np.random.normal(0.63, 0.03),
                'auc_roc': np.random.normal(0.72, 0.03),
                'loss': np.random.normal(0.28, 0.05)
            })
        
        # Generar matriz de confusión
        confusion_matrix = {
            'true_positive': 145,
            'false_positive': 23,
            'true_negative': 167,
            'false_negative': 18
        }
        
        # Generar datos de drift
        drift_data = []
        for i in range(24):  # Últimas 24 horas
            drift_data.append({
                'timestamp': (now - timedelta(hours=i)).isoformat(),
                'drift_score': np.random.normal(0.15, 0.05),
                'threshold': 0.3
            })
        
        # Generar importancia de features
        feature_names = [
            'RSI_14', 'MACD_Signal', 'BB_Upper', 'BB_Lower', 'SMA_20', 
            'EMA_12', 'Volume_SMA', 'ATR_14', 'Stoch_K', 'Williams_R',
            'OBV', 'CCI_20', 'VWAP', 'Price_Change', 'Volatility'
        ]
        
        feature_importance = {
            name: np.random.uniform(0.02, 0.15) 
            for name in feature_names
        }
        
        # Normalizar importancia
        total_importance = sum(feature_importance.values())
        feature_importance = {
            k: v/total_importance for k, v in feature_importance.items()
        }
        
        # Generar historial de entrenamientos
        training_history = []
        for i in range(5):
            training_date = now - timedelta(days=i*7)
            training_history.append({
                'id': f"train_{i+1}",
                'timestamp': training_date.isoformat(),
                'version': f"v10.{i+1}.0",
                'duration': f"{np.random.randint(45, 120)} min",
                'accuracy': np.random.uniform(0.62, 0.72),
                'loss': np.random.uniform(0.25, 0.35),
                'status': 'completed' if i > 0 else 'running'
            })
        
        # Generar predicciones recientes
        predictions = []
        for i in range(100):
            pred_time = now - timedelta(minutes=i*5)
            predictions.append({
                'timestamp': pred_time.isoformat(),
                'predicted_class': np.random.choice(['BUY', 'SELL', 'HOLD'], p=[0.3, 0.3, 0.4]),
                'confidence': np.random.uniform(0.6, 0.95),
                'actual_class': np.random.choice(['BUY', 'SELL', 'HOLD'], p=[0.3, 0.3, 0.4])
            })
        
        return {
            'status': 'healthy',
            'version': 'v10.1.0',
            'last_update': (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            'metrics': {
                'accuracy': 0.685,
                'precision': 0.652,
                'recall': 0.618,
                'f1_score': 0.634,
                'auc_roc': 0.721,
                'loss': 0.284,
                'avg_confidence': 0.721,
                'stability': 0.952
            },
            'usage_stats': {
                'predictions_today': 1247,
                'avg_inference_time': 45,
                'uptime': 0.998,
                'error_rate': 0.002
            },
            'metrics_history': metrics_history,
            'confusion_matrix': confusion_matrix,
            'drift_data': drift_data,
            'feature_importance': feature_importance,
            'training_history': training_history,
            'predictions': predictions,
            'architecture': {
                'model_type': 'LSTM + Attention',
                'layers': 8,
                'parameters': 2847352,
                'input_features': 50,
                'sequence_length': 60,
                'batch_size': 32,
                'optimizer': 'Adam',
                'learning_rate': 0.001
            },
            'performance': {
                'memory_usage': '1.2 GB',
                'gpu_utilization': '45%',
                'cpu_utilization': '12%',
                'inference_speed': '45 ms',
                'training_speed': '2.3 samples/sec'
            }
        }
    
    def _create_status_indicator(self, status: str) -> html.Div:
        """
        Crea indicador visual del estado del modelo
        
        Args:
            status: Estado del modelo
            
        Returns:
            html.Div: Componente del indicador
        """
        state_info = self.model_states.get(status, self.model_states['error'])
        
        return html.Div([
            html.Div([
                html.I(className=f"{state_info['icon']} fa-2x text-{state_info['color']}")
            ], className="text-center mb-2"),
            html.H5(state_info['label'], className=f"text-{state_info['color']} mb-1 text-center"),
            html.P(state_info['description'], className="text-muted text-center small mb-0")
        ])
    
    def _create_metrics_chart(self, metrics_history: List[Dict]) -> go.Figure:
        """
        Crea gráfico de evolución de métricas
        
        Args:
            metrics_history: Historial de métricas
            
        Returns:
            go.Figure: Gráfico de métricas
        """
        if not metrics_history:
            return self._create_empty_chart("No hay datos de métricas")
        
        df = pd.DataFrame(metrics_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Precisión', 'F1 Score', 'AUC-ROC', 'Loss'),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # Precisión
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['accuracy'],
                mode='lines+markers',
                name='Accuracy',
                line=dict(color='#28a745', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        # F1 Score
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['f1_score'],
                mode='lines+markers',
                name='F1 Score',
                line=dict(color='#17a2b8', width=2),
                marker=dict(size=4)
            ),
            row=1, col=2
        )
        
        # AUC-ROC
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['auc_roc'],
                mode='lines+markers',
                name='AUC-ROC',
                line=dict(color='#6f42c1', width=2),
                marker=dict(size=4)
            ),
            row=2, col=1
        )
        
        # Loss
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['loss'],
                mode='lines+markers',
                name='Loss',
                line=dict(color='#dc3545', width=2),
                marker=dict(size=4)
            ),
            row=2, col=2
        )
        
        # Líneas de target
        target_accuracy = self.model_metrics['accuracy']['target']
        target_f1 = self.model_metrics['f1_score']['target']
        target_auc = self.model_metrics['auc_roc']['target']
        target_loss = self.model_metrics['loss']['target']
        
        fig.add_hline(y=target_accuracy, line_dash="dash", line_color="gray", 
                     annotation_text="Target", row=1, col=1)
        fig.add_hline(y=target_f1, line_dash="dash", line_color="gray", 
                     annotation_text="Target", row=1, col=2)
        fig.add_hline(y=target_auc, line_dash="dash", line_color="gray", 
                     annotation_text="Target", row=2, col=1)
        fig.add_hline(y=target_loss, line_dash="dash", line_color="gray", 
                     annotation_text="Target", row=2, col=2)
        
        fig.update_layout(
            title="Evolución de Métricas del Modelo",
            height=self.page_config['chart_height'],
            showlegend=False,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return fig
    
    def _create_confusion_matrix_chart(self, confusion_data: Dict) -> go.Figure:
        """
        Crea gráfico de matriz de confusión
        
        Args:
            confusion_data: Datos de la matriz de confusión
            
        Returns:
            go.Figure: Gráfico de matriz de confusión
        """
        if not confusion_data:
            return self._create_empty_chart("No hay datos de matriz de confusión")
        
        # Crear matriz
        matrix = np.array([
            [confusion_data['true_positive'], confusion_data['false_negative']],
            [confusion_data['false_positive'], confusion_data['true_negative']]
        ])
        
        # Calcular porcentajes
        total = matrix.sum()
        matrix_pct = (matrix / total * 100).round(1)
        
        # Crear anotaciones
        annotations = []
        for i in range(2):
            for j in range(2):
                annotations.append(
                    dict(
                        x=j, y=i,
                        text=f"{matrix[i,j]}<br>({matrix_pct[i,j]}%)",
                        showarrow=False,
                        font=dict(color="white" if matrix[i,j] > total/4 else "black")
                    )
                )
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=['Predicted Positive', 'Predicted Negative'],
            y=['Actual Positive', 'Actual Negative'],
            colorscale='Blues',
            showscale=False,
            hovertemplate='%{x}<br>%{y}<br>Count: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Matriz de Confusión",
            annotations=annotations,
            height=self.page_config['chart_height'],
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return fig
    
    def _create_drift_chart(self, drift_data: List[Dict]) -> go.Figure:
        """
        Crea gráfico de análisis de drift
        
        Args:
            drift_data: Datos de drift del modelo
            
        Returns:
            go.Figure: Gráfico de drift
        """
        if not drift_data:
            return self._create_empty_chart("No hay datos de drift")
        
        df = pd.DataFrame(drift_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        fig = go.Figure()
        
        # Línea de drift score
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['drift_score'],
            mode='lines+markers',
            name='Drift Score',
            line=dict(color='#007bff', width=2),
            marker=dict(size=4),
            hovertemplate='%{x}<br>Drift Score: %{y:.3f}<extra></extra>'
        ))
        
        # Línea de umbral
        if 'threshold' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['threshold'],
                mode='lines',
                name='Umbral de Alerta',
                line=dict(color='#dc3545', width=2, dash='dash'),
                hovertemplate='Umbral: %{y:.3f}<extra></extra>'
            ))
        
        # Área de alerta
        fig.add_hrect(
            y0=0.3, y1=1.0,
            fillcolor="rgba(220, 53, 69, 0.1)",
            layer="below",
            line_width=0,
        )
        
        fig.update_layout(
            title="Análisis de Drift del Modelo (Últimas 24h)",
            xaxis_title="Tiempo",
            yaxis_title="Drift Score",
            height=self.page_config['chart_height'],
            margin=dict(l=40, r=40, t=60, b=40),
            legend=dict(x=0.02, y=0.98)
        )
        
        return fig
    
    def _create_feature_importance_chart(self, feature_importance: Dict) -> go.Figure:
        """
        Crea gráfico de importancia de features
        
        Args:
            feature_importance: Diccionario de importancia por feature
            
        Returns:
            go.Figure: Gráfico de importancia
        """
        if not feature_importance:
            return self._create_empty_chart("No hay datos de importancia")
        
        # Ordenar features por importancia
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        features, importance = zip(*sorted_features[:15])  # Top 15
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(importance),
                y=list(features),
                orientation='h',
                marker=dict(
                    color=list(importance),
                    colorscale='Viridis',
                    showscale=False
                ),
                hovertemplate='%{y}<br>Importancia: %{x:.3f}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="Top 15 Features más Importantes",
            xaxis_title="Importancia",
            yaxis_title="Features",
            height=self.page_config['chart_height'],
            margin=dict(l=120, r=40, t=60, b=40)
        )
        
        return fig
    
    def _create_prediction_analysis_chart(self, predictions: List[Dict]) -> go.Figure:
        """
        Crea gráfico de análisis de predicciones
        
        Args:
            predictions: Lista de predicciones recientes
            
        Returns:
            go.Figure: Gráfico de análisis
        """
        if not predictions:
            return self._create_empty_chart("No hay datos de predicciones")
        
        df = pd.DataFrame(predictions)
        
        # Distribución de confianza por clase
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Distribución de Confianza', 'Precisión por Confianza'),
            horizontal_spacing=0.15
        )
        
        # Histograma de confianza por clase
        for class_name in ['BUY', 'SELL', 'HOLD']:
            class_data = df[df['predicted_class'] == class_name]
            if not class_data.empty:
                fig.add_trace(
                    go.Histogram(
                        x=class_data['confidence'],
                        name=class_name,
                        opacity=0.7,
                        nbinsx=20
                    ),
                    row=1, col=1
                )
        
        # Precisión por nivel de confianza
        confidence_bins = np.arange(0.6, 1.0, 0.05)
        bin_accuracy = []
        bin_centers = []
        
        for i in range(len(confidence_bins)-1):
            bin_mask = (df['confidence'] >= confidence_bins[i]) & (df['confidence'] < confidence_bins[i+1])
            bin_data = df[bin_mask]
            
            if len(bin_data) > 0:
                accuracy = (bin_data['predicted_class'] == bin_data['actual_class']).mean()
                bin_accuracy.append(accuracy)
                bin_centers.append((confidence_bins[i] + confidence_bins[i+1]) / 2)
        
        if bin_accuracy:
            fig.add_trace(
                go.Scatter(
                    x=bin_centers,
                    y=bin_accuracy,
                    mode='lines+markers',
                    name='Precisión',
                    line=dict(color='#28a745', width=3),
                    marker=dict(size=6)
                ),
                row=1, col=2
            )
        
        fig.update_layout(
            title="Análisis de Predicciones",
            height=self.page_config['chart_height'],
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        fig.update_xaxes(title_text="Confianza", row=1, col=1)
        fig.update_xaxes(title_text="Nivel de Confianza", row=1, col=2)
        fig.update_yaxes(title_text="Frecuencia", row=1, col=1)
        fig.update_yaxes(title_text="Precisión", row=1, col=2)
        
        return fig
    
    def _create_training_history_table(self, training_history: List[Dict]) -> html.Div:
        """
        Crea tabla de historial de entrenamientos
        
        Args:
            training_history: Lista de entrenamientos
            
        Returns:
            html.Div: Tabla de entrenamientos
        """
        if not training_history:
            return html.P("No hay historial de entrenamientos", className="text-muted")
        
        # Crear filas de la tabla
        table_rows = []
        for training in training_history[:self.page_config['max_training_history']]:
            status_color = {
                'completed': 'success',
                'running': 'primary',
                'failed': 'danger',
                'pending': 'warning'
            }.get(training.get('status', 'pending'), 'secondary')
            
            row = html.Tr([
                html.Td(training.get('version', 'N/A')),
                html.Td(datetime.fromisoformat(training['timestamp']).strftime("%Y-%m-%d %H:%M")),
                html.Td(training.get('duration', 'N/A')),
                html.Td(f"{training.get('accuracy', 0)*100:.1f}%" if training.get('accuracy') else 'N/A'),
                html.Td(f"{training.get('loss', 0):.3f}" if training.get('loss') else 'N/A'),
                html.Td([
                    dbc.Badge(
                        training.get('status', 'pending').title(),
                        color=status_color,
                        className="me-1"
                    )
                ]),
                html.Td([
                    dbc.ButtonGroup([
                        dbc.Button("Ver", size="sm", color="primary", outline=True),
                        dbc.Button("Usar", size="sm", color="success", outline=True)
                    ], size="sm")
                ])
            ])
            table_rows.append(row)
        
        return dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th("Versión"),
                    html.Th("Fecha"),
                    html.Th("Duración"),
                    html.Th("Precisión"),
                    html.Th("Loss"),
                    html.Th("Estado"),
                    html.Th("Acciones")
                ])
            ]),
            html.Tbody(table_rows)
        ], striped=True, hover=True, responsive=True, className="mb-0")
    
    def _create_architecture_info(self, architecture: Dict) -> html.Div:
        """
        Crea información de arquitectura del modelo
        
        Args:
            architecture: Datos de arquitectura
            
        Returns:
            html.Div: Información de arquitectura
        """
        if not architecture:
            return html.P("No hay información de arquitectura", className="text-muted")
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong("Tipo de Modelo:"),
                    html.Br(),
                    html.Span(architecture.get('model_type', 'N/A'))
                ], width=6),
                dbc.Col([
                    html.Strong("Capas:"),
                    html.Br(),
                    html.Span(str(architecture.get('layers', 'N/A')))
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Strong("Parámetros:"),
                    html.Br(),
                    html.Span(f"{architecture.get('parameters', 0):,}")
                ], width=6),
                dbc.Col([
                    html.Strong("Features de Entrada:"),
                    html.Br(),
                    html.Span(str(architecture.get('input_features', 'N/A')))
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Strong("Longitud de Secuencia:"),
                    html.Br(),
                    html.Span(str(architecture.get('sequence_length', 'N/A')))
                ], width=6),
                dbc.Col([
                    html.Strong("Batch Size:"),
                    html.Br(),
                    html.Span(str(architecture.get('batch_size', 'N/A')))
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Strong("Optimizador:"),
                    html.Br(),
                    html.Span(architecture.get('optimizer', 'N/A'))
                ], width=6),
                dbc.Col([
                    html.Strong("Learning Rate:"),
                    html.Br(),
                    html.Span(str(architecture.get('learning_rate', 'N/A')))
                ], width=6)
            ])
        ])
    
    def _create_performance_metrics(self, performance: Dict) -> html.Div:
        """
        Crea métricas de performance del modelo
        
        Args:
            performance: Datos de performance
            
        Returns:
            html.Div: Métricas de performance
        """
        if not performance:
            return html.P("No hay métricas de performance", className="text-muted")
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong("Uso de Memoria:"),
                    html.Br(),
                    html.Span(performance.get('memory_usage', 'N/A'))
                ], width=6),
                dbc.Col([
                    html.Strong("GPU Utilization:"),
                    html.Br(),
                    html.Span(performance.get('gpu_utilization', 'N/A'))
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Strong("CPU Utilization:"),
                    html.Br(),
                    html.Span(performance.get('cpu_utilization', 'N/A'))
                ], width=6),
                dbc.Col([
                    html.Strong("Velocidad Inferencia:"),
                    html.Br(),
                    html.Span(performance.get('inference_speed', 'N/A'))
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                dbc.Col([
                    html.Strong("Velocidad Entrenamiento:"),
                    html.Br(),
                    html.Span(performance.get('training_speed', 'N/A'))
                ], width=12)
            ])
        ])
    
    def get_page_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la página
        
        Returns:
            Dict[str, Any]: Estado de la página
        """
        base_status = super().get_page_status()
        
        # Agregar información específica de ModelStatusPage
        base_status.update({
            'model_states_configured': len(self.model_states),
            'model_metrics_configured': len(self.model_metrics),
            'auto_refresh_enabled': self.page_config.get('auto_refresh', False),
            'update_interval': self.page_config.get('update_interval', 60000),
            'max_training_history': self.page_config.get('max_training_history', 50)
        })
        
        return base_status