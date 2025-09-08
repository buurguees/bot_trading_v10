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
    
    def __init__(self, data_provider=None):
        """
        Inicializa la página de estado del modelo
        
        Args:
            data_provider: Proveedor de datos centralizado
        """
        super().__init__(data_provider=data_provider)
        
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
                'target': 0.62,
                'format': 'decimal'
            },
            'sharpe_predictions': {
                'name': 'Sharpe de Predicciones',
                'description': 'Sharpe ratio basado en predicciones',
                'target': 1.0,
                'format': 'decimal'
            }
        }
        
        # Features principales del modelo
        self.model_features = [
            'price_momentum_5m', 'price_momentum_15m', 'price_momentum_1h',
            'rsi_14', 'rsi_7', 'macd_signal', 'macd_histogram',
            'bollinger_position', 'bollinger_width', 'volume_sma_ratio',
            'volume_momentum', 'bid_ask_spread', 'order_book_imbalance',
            'volatility_5m', 'volatility_1h', 'time_of_day', 'day_of_week',
            'market_regime', 'correlation_btc', 'fear_greed_index'
        ]
        
        # Umbrales de alerta
        self.alert_thresholds = {
            'accuracy_min': 0.55,
            'drift_threshold': 0.15,
            'feature_importance_change': 0.30,
            'prediction_confidence_min': 0.60,
            'days_without_training': 7
        }
        
        logger.info("ModelStatusPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de estado del modelo
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Estado del Modelo IA",
                    subtitle="Monitoreo y control del modelo de machine learning",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Panel de estado principal
                self._create_model_status_panel(),
                
                # Controles del modelo
                self._create_model_controls_section(),
                
                # Métricas principales del modelo
                self._create_model_metrics_section(),
                
                # Análisis de rendimiento y drift
                dbc.Row([
                    dbc.Col([
                        self._create_performance_trend_section()
                    ], width=8),
                    dbc.Col([
                        self._create_drift_detection_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Feature importance y análisis
                dbc.Row([
                    dbc.Col([
                        self._create_feature_importance_section()
                    ], width=6),
                    dbc.Col([
                        self._create_prediction_analysis_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Historial de entrenamientos
                self._create_training_history_section(),
                
                # Diagnósticos técnicos
                self._create_technical_diagnostics_section(),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("model-refresh-interval"),
                dcc.Store(id='model-data-store'),
                dcc.Store(id='model-config-store', data={
                    'auto_retrain': True,
                    'retrain_threshold': 0.55,
                    'drift_sensitivity': 0.15
                }),
                
            ], fluid=True, className="model-status-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de ModelStatusPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de estado del modelo: {e}")
            ])
    
    def _create_model_status_panel(self) -> dbc.Row:
        """Crea el panel principal de estado del modelo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Estado del modelo
                            dbc.Col([
                                html.Div([
                                    html.H6("Estado del Modelo", className="mb-2"),
                                    html.Div(id="model-status-indicator"),
                                    html.Small(id="model-status-description", className="text-muted")
                                ])
                            ], width=3),
                            
                            # Versión actual
                            dbc.Col([
                                html.Div([
                                    html.H6("Versión Actual", className="mb-2"),
                                    html.H5(id="model-version", className="text-primary mb-0"),
                                    html.Small(id="model-last-update", className="text-muted")
                                ])
                            ], width=3),
                            
                            # Precisión actual
                            dbc.Col([
                                html.Div([
                                    html.H6("Precisión Actual", className="mb-2"),
                                    html.H5(id="model-accuracy", className="mb-0"),
                                    html.Small(id="model-accuracy-trend", className="text-muted")
                                ])
                            ], width=3),
                            
                            # Próximo entrenamiento
                            dbc.Col([
                                html.Div([
                                    html.H6("Próximo Entrenamiento", className="mb-2"),
                                    html.H6(id="next-training-time", className="text-info mb-0"),
                                    html.Small(id="training-trigger", className="text-muted")
                                ])
                            ], width=3)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_model_controls_section(self) -> dbc.Row:
        """Crea la sección de controles del modelo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Controles del Modelo", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            # Controles de entrenamiento
                            dbc.Col([
                                html.Label("Entrenamiento:", className="form-label mb-2"),
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-play me-1"),
                                        "Entrenar Ahora"
                                    ], id="train-now-btn", color="primary", size="sm"),
                                    dbc.Button([
                                        html.I(className="fas fa-pause me-1"),
                                        "Pausar Auto"
                                    ], id="pause-auto-train-btn", color="warning", size="sm"),
                                    dbc.Button([
                                        html.I(className="fas fa-undo me-1"),
                                        "Rollback"
                                    ], id="rollback-model-btn", color="danger", size="sm")
                                ])
                            ], width=12, md=4),
                            
                            # Configuración automática
                            dbc.Col([
                                html.Label("Auto-entrenamiento:", className="form-label mb-2"),
                                dbc.Switch(
                                    id="auto-retrain-switch",
                                    label="Activar reentrenamiento automático",
                                    value=True
                                ),
                                dbc.Input(
                                    id="retrain-threshold-input",
                                    type="number",
                                    value=55,
                                    min=40,
                                    max=80,
                                    step=5,
                                    size="sm",
                                    placeholder="Umbral de precisión (%)"
                                )
                            ], width=12, md=4),
                            
                            # Configuración de drift
                            dbc.Col([
                                html.Label("Detección de Drift:", className="form-label mb-2"),
                                dbc.Input(
                                    id="drift-sensitivity-input",
                                    type="number",
                                    value=15,
                                    min=5,
                                    max=30,
                                    step=5,
                                    size="sm",
                                    placeholder="Sensibilidad (%)"
                                ),
                                dbc.Switch(
                                    id="drift-alerts-switch",
                                    label="Alertas de drift",
                                    value=True,
                                    className="mt-2"
                                )
                            ], width=12, md=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_model_metrics_section(self) -> dbc.Row:
        """Crea la sección de métricas del modelo"""
        return dbc.Row([
            dbc.Col([
                html.H5("Métricas del Modelo", className="section-title mb-3"),
                self.create_loading_component(
                    "model-metrics",
                    html.Div(id="model-metrics-cards"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_performance_trend_section(self) -> dbc.Card:
        """Crea la sección de tendencia de rendimiento"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Tendencia de Rendimiento", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "performance-trend",
                    dcc.Graph(
                        id="performance-trend-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_drift_detection_section(self) -> dbc.Card:
        """Crea la sección de detección de drift"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Detección de Drift", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "drift-detection",
                    html.Div(id="drift-detection-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_feature_importance_section(self) -> dbc.Card:
        """Crea la sección de importancia de features"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Importancia de Features", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "feature-importance",
                    dcc.Graph(
                        id="feature-importance-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_prediction_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de predicciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Predicciones", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "prediction-analysis",
                    dcc.Graph(
                        id="prediction-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_training_history_section(self) -> dbc.Row:
        """Crea la sección de historial de entrenamientos"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Historial de Entrenamientos", className="mb-0")
                    ]),
                    dbc.CardBody([
                        self.create_loading_component(
                            "training-history",
                            html.Div(id="training-history-table"),
                            loading_type="default"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_technical_diagnostics_section(self) -> dbc.Row:
        """Crea la sección de diagnósticos técnicos"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Diagnósticos Técnicos", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div(id="model-architecture-info")
                            ], width=6),
                            dbc.Col([
                                html.Div(id="model-performance-metrics")
                            ], width=6)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de estado del modelo
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para actualizar configuración del modelo
        @app.callback(
            Output('model-config-store', 'data'),
            [Input('auto-retrain-switch', 'value'),
             Input('retrain-threshold-input', 'value'),
             Input('drift-sensitivity-input', 'value'),
             Input('drift-alerts-switch', 'value')],
            [State('model-config-store', 'data')]
        )
        def update_model_config(auto_retrain, threshold, sensitivity, drift_alerts, current_config):
            """Actualiza configuración del modelo"""
            return {
                'auto_retrain': auto_retrain if auto_retrain is not None else True,
                'retrain_threshold': (threshold or 55) / 100,  # Convertir a decimal
                'drift_sensitivity': (sensitivity or 15) / 100,
                'drift_alerts': drift_alerts if drift_alerts is not None else True,
                'last_update': datetime.now().isoformat()
            }
        
        # Callback principal para datos del modelo
        @app.callback(
            Output('model-data-store', 'data'),
            [Input('model-refresh-interval', 'n_intervals'),
             Input('model-refresh-btn', 'n_clicks'),
             Input('train-now-btn', 'n_clicks')],
            [State('model-config-store', 'data')]
        )
        def update_model_data(n_intervals, refresh_clicks, train_clicks, config):
            """Actualiza datos del modelo"""
            try:
                # Simular inicio de entrenamiento si se presionó el botón
                triggered_id = dash.callback_context.triggered[0]['prop_id']
                is_training = 'train-now-btn' in triggered_id
                
                model_data = self._get_model_status_data(config, is_training)
                
                self.update_page_stats()
                
                return model_data
                
            except Exception as e:
                logger.error(f"Error al actualizar datos del modelo: {e}")
                return {}
        
        # Callback para panel de estado principal
        @app.callback(
            [Output('model-status-indicator', 'children'),
             Output('model-status-description', 'children'),
             Output('model-version', 'children'),
             Output('model-last-update', 'children'),
             Output('model-accuracy', 'children'),
             Output('model-accuracy-trend', 'children'),
             Output('next-training-time', 'children'),
             Output('training-trigger', 'children')],
            [Input('model-data-store', 'data')]
        )
        def update_model_status_panel(model_data):
            """Actualiza panel principal de estado"""
            try:
                if not model_data:
                    return ("Cargando...",) * 8
                
                status_info = model_data.get('status', {})
                current_state = status_info.get('state', 'healthy')
                state_config = self.model_states.get(current_state, self.model_states['healthy'])
                
                # Indicador de estado
                status_indicator = dbc.Badge([
                    html.I(className=f"{state_config['icon']} me-1"),
                    state_config['label']
                ], color=state_config['color'])
                
                # Descripción del estado
                status_description = state_config['description']
                
                # Versión del modelo
                version = status_info.get('version', 'v10.0.0')
                last_update = status_info.get('last_update', datetime.now())
                if isinstance(last_update, str):
                    last_update = datetime.fromisoformat(last_update)
                last_update_text = f"Actualizado: {last_update.strftime('%d/%m/%Y %H:%M')}"
                
                # Precisión
                accuracy = status_info.get('accuracy', 0)
                accuracy_text = f"{accuracy*100:.1f}%"
                accuracy_change = status_info.get('accuracy_change', 0)
                accuracy_trend = f"{accuracy_change:+.1f}% (7d)" if accuracy_change != 0 else "Sin cambios"
                accuracy_trend_color = "text-success" if accuracy_change > 0 else "text-danger" if accuracy_change < 0 else "text-muted"
                
                # Próximo entrenamiento
                next_training = status_info.get('next_training', datetime.now() + timedelta(hours=6))
                if isinstance(next_training, str):
                    next_training = datetime.fromisoformat(next_training)
                
                time_diff = next_training - datetime.now()
                if time_diff.total_seconds() > 0:
                    if time_diff.days > 0:
                        next_training_text = f"En {time_diff.days}d {time_diff.seconds//3600}h"
                    else:
                        next_training_text = f"En {time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m"
                else:
                    next_training_text = "Pendiente"
                
                # Trigger de entrenamiento
                trigger_reason = status_info.get('training_trigger', 'Programado')
                
                return (
                    status_indicator,
                    status_description,
                    version,
                    last_update_text,
                    accuracy_text,
                    html.Span(accuracy_trend, className=accuracy_trend_color),
                    next_training_text,
                    trigger_reason
                )
                
            except Exception as e:
                logger.error(f"Error al actualizar panel de estado: {e}")
                return ("Error",) * 8
        
        # Callback para métricas del modelo
        @app.callback(
            Output('model-metrics-cards', 'children'),
            [Input('model-data-store', 'data')]
        )
        def update_model_metrics(model_data):
            """Actualiza tarjetas de métricas del modelo"""
            try:
                if not model_data or not model_data.get('metrics'):
                    return self.create_empty_state(
                        title="Cargando métricas del modelo...",
                        message="Obteniendo datos de rendimiento",
                        icon="fas fa-brain"
                    )
                
                return self._create_model_metrics_cards(model_data['metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear métricas del modelo: {e}")
                return self.create_error_alert("Error al cargar métricas")
        
        # Callback para tendencia de rendimiento
        @app.callback(
            Output('performance-trend-chart', 'figure'),
            [Input('model-data-store', 'data')]
        )
        def update_performance_trend(model_data):
            """Actualiza gráfico de tendencia de rendimiento"""
            try:
                if not model_data or not model_data.get('performance_history'):
                    return self._create_empty_chart("Cargando historial de rendimiento...")
                
                return self._create_performance_trend_chart(model_data['performance_history'])
                
            except Exception as e:
                logger.error(f"Error al crear tendencia de rendimiento: {e}")
                return self._create_empty_chart("Error en tendencia de rendimiento")
        
        # Callback para detección de drift
        @app.callback(
            Output('drift-detection-container', 'children'),
            [Input('model-data-store', 'data')]
        )
        def update_drift_detection(model_data):
            """Actualiza detección de drift"""
            try:
                if not model_data or not model_data.get('drift_analysis'):
                    return html.P("Analizando drift del modelo...", className="text-muted")
                
                return self._create_drift_detection_display(model_data['drift_analysis'])
                
            except Exception as e:
                logger.error(f"Error en detección de drift: {e}")
                return self.create_error_alert("Error en detección de drift")
        
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
                    return (
                        html.P("Cargando arquitectura...", className="text-muted"),
                        html.P("Cargando métricas...", className="text-muted")
                    )
                
                architecture_info = self._create_architecture_info(model_data.get('architecture', {}))
                performance_metrics = self._create_performance_metrics_info(model_data.get('technical_metrics', {}))
                
                return architecture_info, performance_metrics
                
            except Exception as e:
                logger.error(f"Error en diagnósticos técnicos: {e}")
                return (
                    self.create_error_alert("Error en arquitectura"),
                    self.create_error_alert("Error en métricas")
                )
        
        # Callbacks para controles del modelo
        @app.callback(
            [Output('train-now-btn', 'children'),
             Output('pause-auto-train-btn', 'children')],
            [Input('train-now-btn', 'n_clicks'),
             Input('pause-auto-train-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def handle_model_controls(train_clicks, pause_clicks):
            """Maneja controles del modelo"""
            try:
                triggered_id = dash.callback_context.triggered[0]['prop_id']
                
                if 'train-now-btn' in triggered_id:
                    self.log_page_action("manual_training_started")
                    return (
                        [html.I(className="fas fa-cog fa-spin me-1"), "Entrenando..."],
                        [html.I(className="fas fa-pause me-1"), "Pausar Auto"]
                    )
                elif 'pause-auto-train-btn' in triggered_id:
                    self.log_page_action("auto_training_paused")
                    return (
                        [html.I(className="fas fa-play me-1"), "Entrenar Ahora"],
                        [html.I(className="fas fa-play me-1"), "Reanudar Auto"]
                    )
                
                # Estado por defecto
                return (
                    [html.I(className="fas fa-play me-1"), "Entrenar Ahora"],
                    [html.I(className="fas fa-pause me-1"), "Pausar Auto"]
                )
            except Exception as e:
                logger.error(f"Error en controles del modelo: {e}")
                return (
                    [html.I(className="fas fa-play me-1"), "Entrenar Ahora"],
                    [html.I(className="fas fa-pause me-1"), "Pausar Auto"]
                )
        
        logger.info("Callbacks de ModelStatusPage registrados")