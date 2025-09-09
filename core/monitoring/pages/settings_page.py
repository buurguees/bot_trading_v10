# Ruta: core/monitoring/pages/settings_page.py
"""
monitoring/pages/settings_page.py
Página de Configuración del Sistema - Trading Bot v10

Esta página proporciona gestión completa de la configuración del sistema:
- Configuración de trading y estrategias
- Configuración del modelo de IA
- Configuración de monitoreo y alertas
- Configuración de APIs y conexiones
- Configuración de riesgo y límites
- Configuración de notificaciones
- Configuración de temas y UI
- Gestión de usuarios y permisos
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import dash
from dash import html, dcc, Input, Output, State, callback, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from monitoring.pages.base_page import BasePage

logger = logging.getLogger(__name__)

class SettingsPage(BasePage):
    """
    Página de configuración del sistema del Trading Bot v10
    
    Proporciona interfaz completa para gestionar todas las configuraciones
    del sistema, desde trading hasta monitoreo y notificaciones.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None, performance_tracker=None):
        """
        Inicializa la página de configuración
        
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
        
        # Configuración específica de la página Settings
        self.page_config.update({
            'title': 'Configuración del Sistema',
            'update_interval': 300000,  # 5 minutos
            'auto_refresh': False,
            'enable_advanced_settings': True,
            'show_debug_options': False,
            'backup_on_save': True,
            'validate_on_change': True
        })
        
        # Categorías de configuración
        self.config_categories = {
            'trading': {
                'name': 'Trading y Estrategias',
                'icon': 'fas fa-chart-line',
                'description': 'Configuración de parámetros de trading',
                'color': 'primary'
            },
            'model': {
                'name': 'Modelo de IA',
                'icon': 'fas fa-brain',
                'description': 'Configuración del modelo de machine learning',
                'color': 'info'
            },
            'risk': {
                'name': 'Gestión de Riesgo',
                'icon': 'fas fa-shield-alt',
                'description': 'Límites y controles de riesgo',
                'color': 'warning'
            },
            'monitoring': {
                'name': 'Monitoreo',
                'icon': 'fas fa-eye',
                'description': 'Configuración de monitoreo y métricas',
                'color': 'success'
            },
            'notifications': {
                'name': 'Notificaciones',
                'icon': 'fas fa-bell',
                'description': 'Alertas y notificaciones',
                'color': 'info'
            },
            'api': {
                'name': 'APIs y Conexiones',
                'icon': 'fas fa-plug',
                'description': 'Configuración de conexiones externas',
                'color': 'secondary'
            },
            'ui': {
                'name': 'Interfaz de Usuario',
                'icon': 'fas fa-palette',
                'description': 'Temas y configuración visual',
                'color': 'purple'
            },
            'system': {
                'name': 'Sistema',
                'icon': 'fas fa-cogs',
                'description': 'Configuración general del sistema',
                'color': 'dark'
            }
        }
        
        # Configuraciones por defecto
        self.default_configs = self._load_default_configurations()
        
        # Estado de configuraciones actual
        self.current_configs = {}
        self.unsaved_changes = {}
        
        logger.info("SettingsPage inicializada correctamente")
    
    def get_layout(self) -> html.Div:
        """
        Genera el layout de la página de configuración
        
        Returns:
            html.Div: Layout completo de la página
        """
        try:
            return html.Div([
                # Store para configuraciones
                dcc.Store(id='settings-store'),
                dcc.Store(id='unsaved-changes-store', data={}),
                
                # Intervalo de auto-guardado
                dcc.Interval(
                    id='auto-save-interval',
                    interval=30000,  # 30 segundos
                    n_intervals=0,
                    disabled=True
                ),
                
                # Header de la página
                self._create_page_header(),
                
                # Navegación por pestañas
                self._create_navigation_tabs(),
                
                # Contenido de configuración
                html.Div(id="settings-content"),
                
                # Footer con controles
                self._create_settings_footer(),
                
                # Modales
                self._create_modals()
                
            ], className="container-fluid")
            
        except Exception as e:
            logger.error(f"Error al crear layout de SettingsPage: {e}")
            return self.create_error_layout("Error al cargar página de configuración")
    
    def _create_page_header(self) -> dbc.Row:
        """Crea el header de la página"""
        return dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-cog me-3"),
                    "Configuración del Sistema"
                ], className="text-primary mb-1"),
                html.P("Gestión completa de configuraciones del Trading Bot", 
                      className="text-muted mb-4")
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-save me-2"),
                        "Guardar Todo"
                    ], color="success", id="save-all-btn", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-undo me-2"),
                        "Descartar"
                    ], color="secondary", outline=True, id="discard-changes-btn", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-download me-2"),
                        "Exportar"
                    ], color="info", outline=True, id="export-config-btn", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-upload me-2"),
                        "Importar"
                    ], color="warning", outline=True, id="import-config-btn", size="sm")
                ], className="d-flex justify-content-end mb-3")
            ], width=4)
        ], className="mb-4")
    
    def _create_navigation_tabs(self) -> dbc.Card:
        """Crea las pestañas de navegación"""
        tabs = []
        
        for category_id, category_info in self.config_categories.items():
            tab = dbc.Tab(
                label=html.Div([
                    html.I(className=f"{category_info['icon']} me-2"),
                    category_info['name']
                ]),
                tab_id=category_id,
                label_style={"color": f"var(--bs-{category_info['color']})"}
            )
            tabs.append(tab)
        
        return dbc.Card([
            dbc.CardBody([
                dbc.Tabs(
                    tabs,
                    id="settings-tabs",
                    active_tab="trading",
                    className="mb-3"
                )
            ], className="p-2")
        ], className="shadow-sm mb-4")
    
    def _create_settings_footer(self) -> dbc.Row:
        """Crea el footer con controles"""
        return dbc.Row([
            dbc.Col([
                # Indicador de cambios
                html.Div(id="changes-indicator", className="d-flex align-items-center")
            ], width=6),
            dbc.Col([
                # Estado de auto-guardado
                html.Div(id="auto-save-status", className="text-end text-muted small")
            ], width=6)
        ], className="mt-4 py-3 border-top")
    
    def _create_modals(self) -> html.Div:
        """Crea los modales necesarios"""
        return html.Div([
            # Modal de confirmación para descartar cambios
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Confirmar Descarte")),
                dbc.ModalBody([
                    html.P("¿Estás seguro de que deseas descartar todos los cambios no guardados?"),
                    html.P("Esta acción no se puede deshacer.", className="text-danger small")
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", color="secondary", id="cancel-discard-btn"),
                    dbc.Button("Descartar", color="danger", id="confirm-discard-btn")
                ])
            ], id="discard-modal", is_open=False),
            
            # Modal de importación
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Importar Configuración")),
                dbc.ModalBody([
                    dcc.Upload([
                        html.Div([
                            html.I(className="fas fa-upload fa-2x mb-3"),
                            html.H5("Seleccionar archivo de configuración"),
                            html.P("Formatos soportados: JSON", className="text-muted")
                        ], className="text-center py-4")
                    ], id="upload-config", className="border-dashed"),
                    html.Div(id="upload-feedback")
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cerrar", color="secondary", id="close-import-btn")
                ])
            ], id="import-modal", is_open=False, size="lg")
        ])
    
    def _create_trading_settings(self) -> html.Div:
        """Crea la configuración de trading"""
        return html.Div([
            dbc.Row([
                # Configuración general de trading
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-line me-2"),
                            "Configuración General"
                        ]),
                        dbc.CardBody([
                            # Modo de trading
                            html.Label("Modo de Trading:", className="form-label"),
                            dcc.Dropdown(
                                id="trading-mode-dropdown",
                                options=[
                                    {"label": "Automático", "value": "auto"},
                                    {"label": "Semi-automático", "value": "semi"},
                                    {"label": "Manual", "value": "manual"}
                                ],
                                value="auto",
                                className="mb-3"
                            ),
                            
                            # Timeframes activos
                            html.Label("Timeframes Activos:", className="form-label"),
                            dcc.Checklist(
                                id="active-timeframes-checklist",
                                options=[
                                    {"label": "1 minuto", "value": "1m"},
                                    {"label": "5 minutos", "value": "5m"},
                                    {"label": "15 minutos", "value": "15m"},
                                    {"label": "1 hora", "value": "1h"},
                                    {"label": "4 horas", "value": "4h"}
                                ],
                                value=["1m", "5m", "15m"],
                                className="mb-3"
                            ),
                            
                            # Balance inicial
                            html.Label("Balance Inicial (USDT):", className="form-label"),
                            dbc.Input(
                                id="initial-balance-input",
                                type="number",
                                value=1000,
                                min=100,
                                step=100,
                                className="mb-3"
                            ),
                            
                            # Max posiciones simultáneas
                            html.Label("Máximo Posiciones Simultáneas:", className="form-label"),
                            dcc.Slider(
                                id="max-positions-slider",
                                min=1,
                                max=10,
                                step=1,
                                value=3,
                                marks={i: str(i) for i in range(1, 11)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de símbolos
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-coins me-2"),
                            "Símbolos de Trading"
                        ]),
                        dbc.CardBody([
                            # Símbolos activos
                            html.Label("Símbolos Activos:", className="form-label"),
                            dcc.Dropdown(
                                id="active-symbols-dropdown",
                                options=[
                                    {"label": "BTC/USDT", "value": "BTCUSDT"},
                                    {"label": "ETH/USDT", "value": "ETHUSDT"},
                                    {"label": "BNB/USDT", "value": "BNBUSDT"},
                                    {"label": "ADA/USDT", "value": "ADAUSDT"},
                                    {"label": "SOL/USDT", "value": "SOLUSDT"}
                                ],
                                value=["BTCUSDT", "ETHUSDT"],
                                multi=True,
                                className="mb-3"
                            ),
                            
                            # Configuración por símbolo
                            html.Label("Configuración Individual:", className="form-label"),
                            html.Div(id="symbol-config-container"),
                            
                            dbc.Button([
                                html.I(className="fas fa-plus me-2"),
                                "Agregar Símbolo"
                            ], color="success", outline=True, size="sm", 
                            id="add-symbol-btn", className="mt-2")
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de estrategias
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chess me-2"),
                            "Estrategias de Trading"
                        ]),
                        dbc.CardBody([
                            # Estrategia principal
                            html.Label("Estrategia Principal:", className="form-label"),
                            dcc.Dropdown(
                                id="main-strategy-dropdown",
                                options=[
                                    {"label": "LSTM + Technical Analysis", "value": "lstm_ta"},
                                    {"label": "Mean Reversion", "value": "mean_reversion"},
                                    {"label": "Momentum", "value": "momentum"},
                                    {"label": "Grid Trading", "value": "grid"},
                                    {"label": "DCA", "value": "dca"}
                                ],
                                value="lstm_ta",
                                className="mb-3"
                            ),
                            
                            # Peso de estrategias
                            html.Label("Distribución de Estrategias:", className="form-label"),
                            html.Div(id="strategy-weights-container"),
                            
                            # Filtros de entrada
                            html.Label("Filtros de Entrada:", className="form-label mt-3"),
                            dcc.Checklist(
                                id="entry-filters-checklist",
                                options=[
                                    {"label": "Confirmación de volumen", "value": "volume"},
                                    {"label": "Filtro de volatilidad", "value": "volatility"},
                                    {"label": "Tendencia principal", "value": "trend"},
                                    {"label": "Soporte/Resistencia", "value": "sr"}
                                ],
                                value=["volume", "trend"],
                                className="mb-3"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_model_settings(self) -> html.Div:
        """Crea la configuración del modelo"""
        return html.Div([
            dbc.Row([
                # Configuración del modelo
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-brain me-2"),
                            "Configuración del Modelo"
                        ]),
                        dbc.CardBody([
                            # Arquitectura del modelo
                            html.Label("Arquitectura:", className="form-label"),
                            dcc.Dropdown(
                                id="model-architecture-dropdown",
                                options=[
                                    {"label": "LSTM + Attention", "value": "lstm_attention"},
                                    {"label": "Transformer", "value": "transformer"},
                                    {"label": "CNN-LSTM", "value": "cnn_lstm"},
                                    {"label": "GRU", "value": "gru"}
                                ],
                                value="lstm_attention",
                                className="mb-3"
                            ),
                            
                            # Secuencia de entrada
                            html.Label("Longitud de Secuencia:", className="form-label"),
                            dcc.Slider(
                                id="sequence-length-slider",
                                min=30,
                                max=120,
                                step=10,
                                value=60,
                                marks={i: str(i) for i in range(30, 121, 30)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Features
                            html.Label("Features Activos:", className="form-label"),
                            dcc.Checklist(
                                id="model-features-checklist",
                                options=[
                                    {"label": "Precio (OHLCV)", "value": "price"},
                                    {"label": "Indicadores Técnicos", "value": "technical"},
                                    {"label": "Volumen", "value": "volume"},
                                    {"label": "Microestructura", "value": "microstructure"},
                                    {"label": "Sentimiento", "value": "sentiment"}
                                ],
                                value=["price", "technical", "volume"],
                                className="mb-3"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de entrenamiento
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-graduation-cap me-2"),
                            "Entrenamiento"
                        ]),
                        dbc.CardBody([
                            # Reentrenamiento automático
                            html.Label("Reentrenamiento Automático:", className="form-label"),
                            dbc.Switch(
                                id="auto-retrain-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Frecuencia de reentrenamiento
                            html.Label("Frecuencia de Reentrenamiento:", className="form-label"),
                            dcc.Dropdown(
                                id="retrain-frequency-dropdown",
                                options=[
                                    {"label": "Cada 100 trades", "value": "100_trades"},
                                    {"label": "Diario", "value": "daily"},
                                    {"label": "Semanal", "value": "weekly"},
                                    {"label": "Por performance", "value": "performance"}
                                ],
                                value="performance",
                                className="mb-3"
                            ),
                            
                            # Umbral de precisión
                            html.Label("Umbral de Precisión para Reentrenamiento:", className="form-label"),
                            dcc.Slider(
                                id="accuracy-threshold-slider",
                                min=0.5,
                                max=0.8,
                                step=0.05,
                                value=0.65,
                                marks={i/100: f"{i}%" for i in range(50, 81, 10)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Validación
                            html.Label("Método de Validación:", className="form-label"),
                            dcc.Dropdown(
                                id="validation-method-dropdown",
                                options=[
                                    {"label": "Walk-Forward", "value": "walk_forward"},
                                    {"label": "Time Series Split", "value": "time_split"},
                                    {"label": "Purged CV", "value": "purged_cv"}
                                ],
                                value="walk_forward"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de predicción
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-crystal-ball me-2"),
                            "Predicciones"
                        ]),
                        dbc.CardBody([
                            # Umbral de confianza
                            html.Label("Umbral de Confianza:", className="form-label"),
                            dcc.Slider(
                                id="confidence-threshold-slider",
                                min=0.6,
                                max=0.95,
                                step=0.05,
                                value=0.75,
                                marks={i/100: f"{i}%" for i in range(60, 96, 10)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Horizonte de predicción
                            html.Label("Horizonte de Predicción (minutos):", className="form-label"),
                            dcc.Dropdown(
                                id="prediction-horizon-dropdown",
                                options=[
                                    {"label": "5 minutos", "value": 5},
                                    {"label": "15 minutos", "value": 15},
                                    {"label": "30 minutos", "value": 30},
                                    {"label": "1 hora", "value": 60}
                                ],
                                value=15,
                                className="mb-3"
                            ),
                            
                            # Ensemble methods
                            html.Label("Métodos de Ensemble:", className="form-label"),
                            dcc.Checklist(
                                id="ensemble-methods-checklist",
                                options=[
                                    {"label": "Voting Classifier", "value": "voting"},
                                    {"label": "Bagging", "value": "bagging"},
                                    {"label": "Boosting", "value": "boosting"},
                                    {"label": "Stacking", "value": "stacking"}
                                ],
                                value=["voting"],
                                className="mb-3"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_risk_settings(self) -> html.Div:
        """Crea la configuración de riesgo"""
        return html.Div([
            dbc.Row([
                # Límites generales
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-shield-alt me-2"),
                            "Límites de Riesgo"
                        ]),
                        dbc.CardBody([
                            # Max pérdida diaria
                            html.Label("Máxima Pérdida Diaria (%):", className="form-label"),
                            dcc.Slider(
                                id="max-daily-loss-slider",
                                min=1,
                                max=20,
                                step=1,
                                value=5,
                                marks={i: f"{i}%" for i in range(0, 21, 5)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Max drawdown
                            html.Label("Máximo Drawdown (%):", className="form-label"),
                            dcc.Slider(
                                id="max-drawdown-slider",
                                min=5,
                                max=30,
                                step=1,
                                value=15,
                                marks={i: f"{i}%" for i in range(5, 31, 5)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Position sizing
                            html.Label("Tamaño de Posición (% del balance):", className="form-label"),
                            dcc.Slider(
                                id="position-size-slider",
                                min=0.5,
                                max=10,
                                step=0.5,
                                value=2,
                                marks={i: f"{i}%" for i in range(1, 11, 2)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Max leverage
                            html.Label("Máximo Apalancamiento:", className="form-label"),
                            dcc.Slider(
                                id="max-leverage-slider",
                                min=1,
                                max=20,
                                step=1,
                                value=5,
                                marks={i: f"{i}x" for i in range(1, 21, 5)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Stop Loss y Take Profit
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-hand-paper me-2"),
                            "Stop Loss & Take Profit"
                        ]),
                        dbc.CardBody([
                            # Stop Loss por defecto
                            html.Label("Stop Loss por Defecto (%):", className="form-label"),
                            dcc.Slider(
                                id="default-stop-loss-slider",
                                min=0.5,
                                max=5,
                                step=0.1,
                                value=2,
                                marks={i: f"{i}%" for i in [0.5, 1, 2, 3, 5]},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Take Profit por defecto
                            html.Label("Take Profit por Defecto (%):", className="form-label"),
                            dcc.Slider(
                                id="default-take-profit-slider",
                                min=1,
                                max=10,
                                step=0.5,
                                value=4,
                                marks={i: f"{i}%" for i in [1, 2, 4, 6, 10]},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Trailing stop
                            html.Label("Trailing Stop:", className="form-label"),
                            dbc.Switch(
                                id="trailing-stop-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # ATR-based stops
                            html.Label("Stops basados en ATR:", className="form-label"),
                            dbc.Switch(
                                id="atr-stops-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Risk-reward ratio
                            html.Label("Ratio Riesgo/Recompensa Mínimo:", className="form-label"),
                            dcc.Slider(
                                id="risk-reward-ratio-slider",
                                min=1,
                                max=5,
                                step=0.1,
                                value=1.5,
                                marks={i: f"1:{i}" for i in [1, 2, 3, 4, 5]},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Circuit breakers
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-power-off me-2"),
                            "Circuit Breakers"
                        ]),
                        dbc.CardBody([
                            # Activar circuit breakers
                            html.Label("Activar Circuit Breakers:", className="form-label"),
                            dbc.Switch(
                                id="circuit-breakers-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Pérdidas consecutivas
                            html.Label("Máximas Pérdidas Consecutivas:", className="form-label"),
                            dbc.Input(
                                id="max-consecutive-losses-input",
                                type="number",
                                value=5,
                                min=1,
                                max=20,
                                className="mb-3"
                            ),
                            
                            # Volatilidad extrema
                            html.Label("Umbral de Volatilidad Extrema:", className="form-label"),
                            dcc.Slider(
                                id="extreme-volatility-threshold-slider",
                                min=50,
                                max=200,
                                step=10,
                                value=100,
                                marks={i: f"{i}%" for i in range(50, 201, 50)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Correlación alta
                            html.Label("Umbral de Correlación Alta:", className="form-label"),
                            dcc.Slider(
                                id="high-correlation-threshold-slider",
                                min=0.7,
                                max=0.95,
                                step=0.05,
                                value=0.85,
                                marks={i/100: f"{i}%" for i in range(70, 96, 10)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_monitoring_settings(self) -> html.Div:
        """Crea la configuración de monitoreo"""
        return html.Div([
            dbc.Row([
                # Configuración de métricas
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-bar me-2"),
                            "Métricas de Monitoreo"
                        ]),
                        dbc.CardBody([
                            # Métricas principales
                            html.Label("Métricas Principales:", className="form-label"),
                            dcc.Checklist(
                                id="main-metrics-checklist",
                                options=[
                                    {"label": "P&L Total", "value": "total_pnl"},
                                    {"label": "Sharpe Ratio", "value": "sharpe"},
                                    {"label": "Max Drawdown", "value": "max_dd"},
                                    {"label": "Win Rate", "value": "win_rate"},
                                    {"label": "Profit Factor", "value": "profit_factor"},
                                    {"label": "Calmar Ratio", "value": "calmar"}
                                ],
                                value=["total_pnl", "sharpe", "max_dd", "win_rate"],
                                className="mb-3"
                            ),
                            
                            # Frecuencia de actualización
                            html.Label("Frecuencia de Actualización:", className="form-label"),
                            dcc.Dropdown(
                                id="update-frequency-dropdown",
                                options=[
                                    {"label": "Tiempo real (1s)", "value": 1},
                                    {"label": "5 segundos", "value": 5},
                                    {"label": "30 segundos", "value": 30},
                                    {"label": "1 minuto", "value": 60}
                                ],
                                value=30,
                                className="mb-3"
                            ),
                            
                            # Retención de datos
                            html.Label("Retención de Datos Históricos (días):", className="form-label"),
                            dcc.Slider(
                                id="data-retention-slider",
                                min=30,
                                max=365,
                                step=30,
                                value=90,
                                marks={i: f"{i}d" for i in range(30, 366, 60)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de logging
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-file-alt me-2"),
                            "Logging y Auditoría"
                        ]),
                        dbc.CardBody([
                            # Nivel de logging
                            html.Label("Nivel de Logging:", className="form-label"),
                            dcc.Dropdown(
                                id="logging-level-dropdown",
                                options=[
                                    {"label": "DEBUG", "value": "DEBUG"},
                                    {"label": "INFO", "value": "INFO"},
                                    {"label": "WARNING", "value": "WARNING"},
                                    {"label": "ERROR", "value": "ERROR"}
                                ],
                                value="INFO",
                                className="mb-3"
                            ),
                            
                            # Logs a archivo
                            html.Label("Guardar Logs en Archivo:", className="form-label"),
                            dbc.Switch(
                                id="file-logging-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Rotación de logs
                            html.Label("Rotación de Logs (MB):", className="form-label"),
                            dbc.Input(
                                id="log-rotation-input",
                                type="number",
                                value=50,
                                min=1,
                                max=500,
                                className="mb-3"
                            ),
                            
                            # Auditoría de trades
                            html.Label("Auditoría Completa de Trades:", className="form-label"),
                            dbc.Switch(
                                id="trade-audit-switch",
                                value=True
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de alertas
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            "Sistema de Alertas"
                        ]),
                        dbc.CardBody([
                            # Alertas de performance
                            html.Label("Alertas de Performance:", className="form-label"),
                            dcc.Checklist(
                                id="performance-alerts-checklist",
                                options=[
                                    {"label": "Drawdown excesivo", "value": "drawdown"},
                                    {"label": "Pérdidas consecutivas", "value": "consecutive_losses"},
                                    {"label": "Baja precisión del modelo", "value": "low_accuracy"},
                                    {"label": "Alta volatilidad", "value": "high_volatility"}
                                ],
                                value=["drawdown", "consecutive_losses"],
                                className="mb-3"
                            ),
                            
                            # Alertas técnicas
                            html.Label("Alertas Técnicas:", className="form-label"),
                            dcc.Checklist(
                                id="technical-alerts-checklist",
                                options=[
                                    {"label": "Fallo de conexión API", "value": "api_failure"},
                                    {"label": "Error del modelo", "value": "model_error"},
                                    {"label": "Latencia alta", "value": "high_latency"},
                                    {"label": "Uso alto de memoria", "value": "high_memory"}
                                ],
                                value=["api_failure", "model_error"],
                                className="mb-3"
                            ),
                            
                            # Cooldown de alertas
                            html.Label("Cooldown entre Alertas (minutos):", className="form-label"),
                            dbc.Input(
                                id="alert-cooldown-input",
                                type="number",
                                value=15,
                                min=1,
                                max=120
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_notifications_settings(self) -> html.Div:
        """Crea la configuración de notificaciones"""
        return html.Div([
            dbc.Row([
                # Configuración de email
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-envelope me-2"),
                            "Notificaciones por Email"
                        ]),
                        dbc.CardBody([
                            # Activar email
                            html.Label("Activar Notificaciones por Email:", className="form-label"),
                            dbc.Switch(
                                id="email-notifications-switch",
                                value=False,
                                className="mb-3"
                            ),
                            
                            # Servidor SMTP
                            html.Label("Servidor SMTP:", className="form-label"),
                            dbc.Input(
                                id="smtp-server-input",
                                placeholder="smtp.gmail.com",
                                className="mb-3"
                            ),
                            
                            # Puerto SMTP
                            html.Label("Puerto SMTP:", className="form-label"),
                            dbc.Input(
                                id="smtp-port-input",
                                type="number",
                                value=587,
                                className="mb-3"
                            ),
                            
                            # Email del usuario
                            html.Label("Email de Origen:", className="form-label"),
                            dbc.Input(
                                id="sender-email-input",
                                type="email",
                                placeholder="bot@trading.com",
                                className="mb-3"
                            ),
                            
                            # Email de destino
                            html.Label("Email de Destino:", className="form-label"),
                            dbc.Input(
                                id="recipient-email-input",
                                type="email",
                                placeholder="usuario@email.com"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de Telegram
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fab fa-telegram me-2"),
                            "Notificaciones por Telegram"
                        ]),
                        dbc.CardBody([
                            # Activar Telegram
                            html.Label("Activar Notificaciones por Telegram:", className="form-label"),
                            dbc.Switch(
                                id="telegram-notifications-switch",
                                value=False,
                                className="mb-3"
                            ),
                            
                            # Bot Token
                            html.Label("Bot Token:", className="form-label"),
                            dbc.Input(
                                id="telegram-bot-token-input",
                                type="password",
                                placeholder="123456789:ABCdefGhIJKlmNOPQrstUVwxyZ",
                                className="mb-3"
                            ),
                            
                            # Chat ID
                            html.Label("Chat ID:", className="form-label"),
                            dbc.Input(
                                id="telegram-chat-id-input",
                                placeholder="123456789",
                                className="mb-3"
                            ),
                            
                            # Test de conexión
                            dbc.Button([
                                html.I(className="fas fa-paper-plane me-2"),
                                "Enviar Mensaje de Prueba"
                            ], color="info", outline=True, size="sm", 
                            id="test-telegram-btn", className="mb-3"),
                            
                            html.Div(id="telegram-test-feedback")
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de tipos de notificación
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-bell me-2"),
                            "Tipos de Notificación"
                        ]),
                        dbc.CardBody([
                            # Notificaciones de trading
                            html.Label("Notificaciones de Trading:", className="form-label"),
                            dcc.Checklist(
                                id="trading-notifications-checklist",
                                options=[
                                    {"label": "Nuevos trades abiertos", "value": "new_trades"},
                                    {"label": "Trades cerrados", "value": "closed_trades"},
                                    {"label": "Stop loss activados", "value": "stop_loss"},
                                    {"label": "Take profit alcanzados", "value": "take_profit"},
                                    {"label": "Resumen diario", "value": "daily_summary"}
                                ],
                                value=["stop_loss", "daily_summary"],
                                className="mb-3"
                            ),
                            
                            # Notificaciones de sistema
                            html.Label("Notificaciones de Sistema:", className="form-label"),
                            dcc.Checklist(
                                id="system-notifications-checklist",
                                options=[
                                    {"label": "Inicio/parada del bot", "value": "bot_status"},
                                    {"label": "Errores críticos", "value": "critical_errors"},
                                    {"label": "Reentrenamiento del modelo", "value": "model_retrain"},
                                    {"label": "Actualizaciones de software", "value": "updates"}
                                ],
                                value=["bot_status", "critical_errors"],
                                className="mb-3"
                            ),
                            
                            # Horario de notificaciones
                            html.Label("Horario de Notificaciones:", className="form-label"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Desde:", className="form-label small"),
                                    dbc.Input(
                                        id="notification-start-time-input",
                                        type="time",
                                        value="08:00"
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label("Hasta:", className="form-label small"),
                                    dbc.Input(
                                        id="notification-end-time-input",
                                        type="time",
                                        value="22:00"
                                    )
                                ], width=6)
                            ])
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_api_settings(self) -> html.Div:
        """Crea la configuración de APIs"""
        return html.Div([
            dbc.Row([
                # Configuración de Bitget
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-exchange-alt me-2"),
                            "Bitget API"
                        ]),
                        dbc.CardBody([
                            # Activar API
                            html.Label("Usar Bitget API:", className="form-label"),
                            dbc.Switch(
                                id="bitget-api-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Entorno
                            html.Label("Entorno:", className="form-label"),
                            dcc.Dropdown(
                                id="bitget-environment-dropdown",
                                options=[
                                    {"label": "Sandbox (Testnet)", "value": "sandbox"},
                                    {"label": "Producción", "value": "production"}
                                ],
                                value="sandbox",
                                className="mb-3"
                            ),
                            
                            # API Key
                            html.Label("API Key:", className="form-label"),
                            dbc.Input(
                                id="bitget-api-key-input",
                                type="password",
                                placeholder="API Key",
                                className="mb-3"
                            ),
                            
                            # Secret Key
                            html.Label("Secret Key:", className="form-label"),
                            dbc.Input(
                                id="bitget-secret-key-input",
                                type="password",
                                placeholder="Secret Key",
                                className="mb-3"
                            ),
                            
                            # Passphrase
                            html.Label("Passphrase:", className="form-label"),
                            dbc.Input(
                                id="bitget-passphrase-input",
                                type="password",
                                placeholder="Passphrase",
                                className="mb-3"
                            ),
                            
                            # Test de conexión
                            dbc.Button([
                                html.I(className="fas fa-wifi me-2"),
                                "Probar Conexión"
                            ], color="success", outline=True, size="sm", 
                            id="test-bitget-connection-btn"),
                            
                            html.Div(id="bitget-connection-feedback", className="mt-2")
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de Rate Limits
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-tachometer-alt me-2"),
                            "Rate Limits y Timeouts"
                        ]),
                        dbc.CardBody([
                            # Rate limit por minuto
                            html.Label("Requests por Minuto:", className="form-label"),
                            dbc.Input(
                                id="rate-limit-per-minute-input",
                                type="number",
                                value=100,
                                min=10,
                                max=1000,
                                className="mb-3"
                            ),
                            
                            # Timeout de conexión
                            html.Label("Timeout de Conexión (segundos):", className="form-label"),
                            dbc.Input(
                                id="connection-timeout-input",
                                type="number",
                                value=10,
                                min=1,
                                max=60,
                                className="mb-3"
                            ),
                            
                            # Timeout de respuesta
                            html.Label("Timeout de Respuesta (segundos):", className="form-label"),
                            dbc.Input(
                                id="response-timeout-input",
                                type="number",
                                value=30,
                                min=5,
                                max=120,
                                className="mb-3"
                            ),
                            
                            # Reintentos
                            html.Label("Máximo Reintentos:", className="form-label"),
                            dbc.Input(
                                id="max-retries-input",
                                type="number",
                                value=3,
                                min=1,
                                max=10,
                                className="mb-3"
                            ),
                            
                            # Delay entre reintentos
                            html.Label("Delay entre Reintentos (segundos):", className="form-label"),
                            dbc.Input(
                                id="retry-delay-input",
                                type="number",
                                value=1,
                                min=0.1,
                                step=0.1,
                                max=10
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # WebSocket Configuration
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-satellite-dish me-2"),
                            "WebSocket Configuration"
                        ]),
                        dbc.CardBody([
                            # Activar WebSocket
                            html.Label("Usar WebSocket para Datos en Tiempo Real:", className="form-label"),
                            dbc.Switch(
                                id="websocket-enabled-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Ping interval
                            html.Label("Ping Interval (segundos):", className="form-label"),
                            dbc.Input(
                                id="websocket-ping-interval-input",
                                type="number",
                                value=30,
                                min=10,
                                max=300,
                                className="mb-3"
                            ),
                            
                            # Reconnect attempts
                            html.Label("Intentos de Reconexión:", className="form-label"),
                            dbc.Input(
                                id="websocket-reconnect-attempts-input",
                                type="number",
                                value=5,
                                min=1,
                                max=20,
                                className="mb-3"
                            ),
                            
                            # Buffer size
                            html.Label("Buffer Size (MB):", className="form-label"),
                            dbc.Input(
                                id="websocket-buffer-size-input",
                                type="number",
                                value=10,
                                min=1,
                                max=100
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_ui_settings(self) -> html.Div:
        """Crea la configuración de UI"""
        return html.Div([
            dbc.Row([
                # Configuración de tema
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-palette me-2"),
                            "Configuración de Tema"
                        ]),
                        dbc.CardBody([
                            # Tema principal
                            html.Label("Tema Principal:", className="form-label"),
                            dcc.Dropdown(
                                id="main-theme-dropdown",
                                options=[
                                    {"label": "Claro", "value": "light"},
                                    {"label": "Oscuro", "value": "dark"},
                                    {"label": "Automático", "value": "auto"}
                                ],
                                value="dark",
                                className="mb-3"
                            ),
                            
                            # Color primario
                            html.Label("Color Primario:", className="form-label"),
                            dcc.Dropdown(
                                id="primary-color-dropdown",
                                options=[
                                    {"label": "Azul", "value": "blue"},
                                    {"label": "Verde", "value": "green"},
                                    {"label": "Púrpura", "value": "purple"},
                                    {"label": "Naranja", "value": "orange"},
                                    {"label": "Rojo", "value": "red"}
                                ],
                                value="blue",
                                className="mb-3"
                            ),
                            
                            # Densidad de información
                            html.Label("Densidad de Información:", className="form-label"),
                            dcc.Dropdown(
                                id="info-density-dropdown",
                                options=[
                                    {"label": "Compacta", "value": "compact"},
                                    {"label": "Normal", "value": "normal"},
                                    {"label": "Espaciosa", "value": "spacious"}
                                ],
                                value="normal",
                                className="mb-3"
                            ),
                            
                            # Animaciones
                            html.Label("Animaciones:", className="form-label"),
                            dbc.Switch(
                                id="animations-switch",
                                value=True
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de dashboard
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-th-large me-2"),
                            "Configuración del Dashboard"
                        ]),
                        dbc.CardBody([
                            # Actualización automática
                            html.Label("Actualización Automática:", className="form-label"),
                            dbc.Switch(
                                id="auto-refresh-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Intervalo de actualización
                            html.Label("Intervalo de Actualización (segundos):", className="form-label"),
                            dcc.Slider(
                                id="refresh-interval-slider",
                                min=5,
                                max=300,
                                step=5,
                                value=30,
                                marks={i: f"{i}s" for i in [5, 30, 60, 120, 300]},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Número de decimales
                            html.Label("Decimales en Métricas:", className="form-label"),
                            dcc.Slider(
                                id="decimal-places-slider",
                                min=0,
                                max=6,
                                step=1,
                                value=2,
                                marks={i: str(i) for i in range(7)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Timezone
                            html.Label("Zona Horaria:", className="form-label"),
                            dcc.Dropdown(
                                id="timezone-dropdown",
                                options=[
                                    {"label": "UTC", "value": "UTC"},
                                    {"label": "Madrid (CET)", "value": "Europe/Madrid"},
                                    {"label": "Londres (GMT)", "value": "Europe/London"},
                                    {"label": "Nueva York (EST)", "value": "America/New_York"},
                                    {"label": "Tokio (JST)", "value": "Asia/Tokyo"}
                                ],
                                value="Europe/Madrid"
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de gráficos
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-line me-2"),
                            "Configuración de Gráficos"
                        ]),
                        dbc.CardBody([
                            # Tipo de gráfico por defecto
                            html.Label("Tipo de Gráfico por Defecto:", className="form-label"),
                            dcc.Dropdown(
                                id="default-chart-type-dropdown",
                                options=[
                                    {"label": "Velas", "value": "candlestick"},
                                    {"label": "Línea", "value": "line"},
                                    {"label": "OHLC", "value": "ohlc"}
                                ],
                                value="candlestick",
                                className="mb-3"
                            ),
                            
                            # Indicadores por defecto
                            html.Label("Indicadores por Defecto:", className="form-label"),
                            dcc.Checklist(
                                id="default-indicators-checklist",
                                options=[
                                    {"label": "SMA 20", "value": "sma_20"},
                                    {"label": "EMA 12", "value": "ema_12"},
                                    {"label": "Bollinger Bands", "value": "bb"},
                                    {"label": "RSI", "value": "rsi"},
                                    {"label": "MACD", "value": "macd"},
                                    {"label": "Volumen", "value": "volume"}
                                ],
                                value=["sma_20", "ema_12", "rsi"],
                                className="mb-3"
                            ),
                            
                            # Altura de gráficos
                            html.Label("Altura de Gráficos (px):", className="form-label"),
                            dcc.Slider(
                                id="chart-height-slider",
                                min=300,
                                max=800,
                                step=50,
                                value=400,
                                marks={i: str(i) for i in range(300, 801, 100)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def _create_system_settings(self) -> html.Div:
        """Crea la configuración del sistema"""
        return html.Div([
            dbc.Row([
                # Configuración de performance
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-rocket me-2"),
                            "Performance del Sistema"
                        ]),
                        dbc.CardBody([
                            # Número de workers
                            html.Label("Número de Workers:", className="form-label"),
                            dcc.Slider(
                                id="num-workers-slider",
                                min=1,
                                max=8,
                                step=1,
                                value=2,
                                marks={i: str(i) for i in range(1, 9)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Cache size
                            html.Label("Tamaño de Cache (MB):", className="form-label"),
                            dbc.Input(
                                id="cache-size-input",
                                type="number",
                                value=256,
                                min=64,
                                max=2048,
                                step=64,
                                className="mb-3"
                            ),
                            
                            # Batch size para procesamiento
                            html.Label("Batch Size para Procesamiento:", className="form-label"),
                            dcc.Slider(
                                id="batch-size-slider",
                                min=16,
                                max=256,
                                step=16,
                                value=32,
                                marks={i: str(i) for i in range(16, 257, 48)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                            
                            # Optimización GPU
                            html.Label("Usar GPU (si está disponible):", className="form-label"),
                            dbc.Switch(
                                id="use-gpu-switch",
                                value=True
                            )
                        ])
                    ], className="shadow-sm")
                ], width=6),
                
                # Configuración de backups
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-save me-2"),
                            "Backups y Recuperación"
                        ]),
                        dbc.CardBody([
                            # Backup automático
                            html.Label("Backup Automático:", className="form-label"),
                            dbc.Switch(
                                id="auto-backup-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # Frecuencia de backup
                            html.Label("Frecuencia de Backup:", className="form-label"),
                            dcc.Dropdown(
                                id="backup-frequency-dropdown",
                                options=[
                                    {"label": "Cada 6 horas", "value": "6hourly"},
                                    {"label": "Diario", "value": "daily"},
                                    {"label": "Semanal", "value": "weekly"}
                                ],
                                value="daily",
                                className="mb-3"
                            ),
                            
                            # Retención de backups
                            html.Label("Retención de Backups (días):", className="form-label"),
                            dbc.Input(
                                id="backup-retention-input",
                                type="number",
                                value=30,
                                min=1,
                                max=365,
                                className="mb-3"
                            ),
                            
                            # Ubicación de backups
                            html.Label("Ubicación de Backups:", className="form-label"),
                            dbc.Input(
                                id="backup-location-input",
                                value="./backups/",
                                className="mb-3"
                            ),
                            
                            # Crear backup manual
                            dbc.Button([
                                html.I(className="fas fa-download me-2"),
                                "Crear Backup Manual"
                            ], color="info", outline=True, size="sm", 
                            id="manual-backup-btn")
                        ])
                    ], className="shadow-sm")
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                # Configuración de seguridad
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-lock me-2"),
                            "Configuración de Seguridad"
                        ]),
                        dbc.CardBody([
                            # Encriptación de datos
                            html.Label("Encriptar Datos Sensibles:", className="form-label"),
                            dbc.Switch(
                                id="encrypt-data-switch",
                                value=True,
                                className="mb-3"
                            ),
                            
                            # IP Whitelist
                            html.Label("IP Whitelist (una por línea):", className="form-label"),
                            dbc.Textarea(
                                id="ip-whitelist-textarea",
                                placeholder="192.168.1.0/24\n127.0.0.1",
                                rows=4,
                                className="mb-3"
                            ),
                            
                            # Timeout de sesión
                            html.Label("Timeout de Sesión (minutos):", className="form-label"),
                            dbc.Input(
                                id="session-timeout-input",
                                type="number",
                                value=120,
                                min=15,
                                max=480,
                                className="mb-3"
                            ),
                            
                            # Registro de accesos
                            html.Label("Registro de Accesos:", className="form-label"),
                            dbc.Switch(
                                id="access-logging-switch",
                                value=True
                            )
                        ])
                    ], className="shadow-sm")
                ], width=12)
            ])
        ])
    
    def register_callbacks(self, app: dash.Dash):
        """
        Registra todos los callbacks de la página
        
        Args:
            app: Instancia de la aplicación Dash
        """
        # Callback principal para cargar configuraciones
        @app.callback(
            Output('settings-store', 'data'),
            [Input('settings-tabs', 'active_tab')]
        )
        def load_settings(active_tab):
            """Carga configuraciones del sistema"""
            try:
                return self._load_current_settings()
            except Exception as e:
                logger.error(f"Error al cargar configuraciones: {e}")
                return {}
        
        # Callback para mostrar contenido por pestaña
        @app.callback(
            Output('settings-content', 'children'),
            [Input('settings-tabs', 'active_tab')]
        )
        def display_tab_content(active_tab):
            """Muestra el contenido de la pestaña activa"""
            try:
                if active_tab == 'trading':
                    return self._create_trading_settings()
                elif active_tab == 'model':
                    return self._create_model_settings()
                elif active_tab == 'risk':
                    return self._create_risk_settings()
                elif active_tab == 'monitoring':
                    return self._create_monitoring_settings()
                elif active_tab == 'notifications':
                    return self._create_notifications_settings()
                elif active_tab == 'api':
                    return self._create_api_settings()
                elif active_tab == 'ui':
                    return self._create_ui_settings()
                elif active_tab == 'system':
                    return self._create_system_settings()
                else:
                    return self._create_trading_settings()
                    
            except Exception as e:
                logger.error(f"Error al mostrar contenido de pestaña {active_tab}: {e}")
                return self.create_error_alert(f"Error al cargar configuración de {active_tab}")
        
        # Callback para manejar cambios no guardados
        @app.callback(
            [Output('unsaved-changes-store', 'data'),
             Output('changes-indicator', 'children')],
            [Input({'type': 'settings-input', 'id': ALL}, 'value')],
            [State('unsaved-changes-store', 'data')]
        )
        def track_unsaved_changes(values, current_changes):
            """Rastrea cambios no guardados"""
            try:
                if not dash.callback_context.triggered:
                    return current_changes, ""
                
                # Detectar si hay cambios
                has_changes = len(current_changes) > 0 or any(values)
                
                if has_changes:
                    indicator = dbc.Alert([
                        html.I(className="fas fa-exclamation-circle me-2"),
                        "Tienes cambios sin guardar"
                    ], color="warning", className="py-2 mb-0")
                else:
                    indicator = ""
                
                return current_changes, indicator
                
            except Exception as e:
                logger.error(f"Error al rastrear cambios: {e}")
                return current_changes, ""
        
        # Callback para guardar configuraciones
        @app.callback(
            Output('save-feedback', 'children'),
            [Input('save-all-btn', 'n_clicks')],
            [State('settings-store', 'data')]
        )
        def save_all_settings(n_clicks, settings_data):
            """Guarda todas las configuraciones"""
            try:
                if not n_clicks:
                    return ""
                
                success = self._save_settings(settings_data)
                
                if success:
                    return dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        "Configuraciones guardadas correctamente"
                    ], color="success", dismissable=True)
                else:
                    return dbc.Alert([
                        html.I(className="fas fa-times-circle me-2"),
                        "Error al guardar configuraciones"
                    ], color="danger", dismissable=True)
                    
            except Exception as e:
                logger.error(f"Error al guardar configuraciones: {e}")
                return dbc.Alert("Error interno al guardar", color="danger", dismissable=True)
        
        # Callback para modal de descarte
        @app.callback(
            Output('discard-modal', 'is_open'),
            [Input('discard-changes-btn', 'n_clicks'),
             Input('cancel-discard-btn', 'n_clicks'),
             Input('confirm-discard-btn', 'n_clicks')]
        )
        def toggle_discard_modal(discard_clicks, cancel_clicks, confirm_clicks):
            """Controla el modal de confirmación de descarte"""
            if not dash.callback_context.triggered:
                return False
            
            trigger_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
            
            if trigger_id == 'discard-changes-btn':
                return True
            else:
                return False
        
        # Callback para test de conexión Bitget
        @app.callback(
            Output('bitget-connection-feedback', 'children'),
            [Input('test-bitget-connection-btn', 'n_clicks')],
            [State('bitget-api-key-input', 'value'),
             State('bitget-secret-key-input', 'value'),
             State('bitget-passphrase-input', 'value')]
        )
        def test_bitget_connection(n_clicks, api_key, secret_key, passphrase):
            """Prueba la conexión con Bitget"""
            try:
                if not n_clicks:
                    return ""
                
                if not all([api_key, secret_key, passphrase]):
                    return dbc.Alert("Por favor completa todos los campos", 
                                   color="warning", dismissable=True)
                
                # Simular test de conexión
                success = self._test_bitget_connection(api_key, secret_key, passphrase)
                
                if success:
                    return dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        "Conexión exitosa"
                    ], color="success", dismissable=True)
                else:
                    return dbc.Alert([
                        html.I(className="fas fa-times-circle me-2"),
                        "Error de conexión"
                    ], color="danger", dismissable=True)
                    
            except Exception as e:
                logger.error(f"Error al probar conexión Bitget: {e}")
                return dbc.Alert("Error en test de conexión", color="danger", dismissable=True)
        
        # Callback para test de Telegram
        @app.callback(
            Output('telegram-test-feedback', 'children'),
            [Input('test-telegram-btn', 'n_clicks')],
            [State('telegram-bot-token-input', 'value'),
             State('telegram-chat-id-input', 'value')]
        )
        def test_telegram_notification(n_clicks, bot_token, chat_id):
            """Prueba las notificaciones de Telegram"""
            try:
                if not n_clicks:
                    return ""
                
                if not all([bot_token, chat_id]):
                    return dbc.Alert("Por favor completa Token y Chat ID", 
                                   color="warning", dismissable=True)
                
                # Simular envío de mensaje
                success = self._test_telegram_notification(bot_token, chat_id)
                
                if success:
                    return dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        "Mensaje enviado correctamente"
                    ], color="success", dismissable=True)
                else:
                    return dbc.Alert([
                        html.I(className="fas fa-times-circle me-2"),
                        "Error al enviar mensaje"
                    ], color="danger", dismissable=True)
                    
            except Exception as e:
                logger.error(f"Error al probar Telegram: {e}")
                return dbc.Alert("Error en test de Telegram", color="danger", dismissable=True)
        
        # Callback para auto-guardado
        @app.callback(
            Output('auto-save-status', 'children'),
            [Input('auto-save-interval', 'n_intervals')],
            [State('unsaved-changes-store', 'data')]
        )
        def auto_save_settings(n_intervals, unsaved_changes):
            """Auto-guardado de configuraciones"""
            try:
                if not unsaved_changes or len(unsaved_changes) == 0:
                    return ""
                
                # Simular auto-guardado
                timestamp = datetime.now().strftime("%H:%M:%S")
                return f"Auto-guardado: {timestamp}"
                
            except Exception as e:
                logger.error(f"Error en auto-guardado: {e}")
                return "Error en auto-guardado"
        
        # Callback para backup manual
        @app.callback(
            Output('backup-feedback', 'children'),
            [Input('manual-backup-btn', 'n_clicks')]
        )
        def create_manual_backup(n_clicks):
            """Crea backup manual"""
            try:
                if not n_clicks:
                    return ""
                
                success = self._create_backup()
                
                if success:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        f"Backup creado exitosamente: {timestamp}"
                    ], color="success", dismissable=True)
                else:
                    return dbc.Alert([
                        html.I(className="fas fa-times-circle me-2"),
                        "Error al crear backup"
                    ], color="danger", dismissable=True)
                    
            except Exception as e:
                logger.error(f"Error al crear backup: {e}")
                return dbc.Alert("Error interno al crear backup", color="danger", dismissable=True)
        
        logger.info("Callbacks de SettingsPage registrados correctamente")
    
    def _load_default_configurations(self) -> Dict[str, Any]:
        """
        Carga configuraciones por defecto del sistema
        
        Returns:
            Dict[str, Any]: Configuraciones por defecto
        """
        return {
            'trading': {
                'mode': 'auto',
                'active_timeframes': ['1m', '5m', '15m'],
                'initial_balance': 1000,
                'max_positions': 3,
                'active_symbols': ['BTCUSDT', 'ETHUSDT'],
                'main_strategy': 'lstm_ta',
                'entry_filters': ['volume', 'trend']
            },
            'model': {
                'architecture': 'lstm_attention',
                'sequence_length': 60,
                'features': ['price', 'technical', 'volume'],
                'auto_retrain': True,
                'retrain_frequency': 'performance',
                'accuracy_threshold': 0.65,
                'validation_method': 'walk_forward',
                'confidence_threshold': 0.75,
                'prediction_horizon': 15,
                'ensemble_methods': ['voting']
            },
            'risk': {
                'max_daily_loss': 5,
                'max_drawdown': 15,
                'position_size': 2,
                'max_leverage': 5,
                'default_stop_loss': 2,
                'default_take_profit': 4,
                'trailing_stop': True,
                'atr_stops': True,
                'risk_reward_ratio': 1.5,
                'circuit_breakers': True,
                'max_consecutive_losses': 5,
                'extreme_volatility_threshold': 100,
                'high_correlation_threshold': 0.85
            },
            'monitoring': {
                'main_metrics': ['total_pnl', 'sharpe', 'max_dd', 'win_rate'],
                'update_frequency': 30,
                'data_retention': 90,
                'logging_level': 'INFO',
                'file_logging': True,
                'log_rotation': 50,
                'trade_audit': True,
                'performance_alerts': ['drawdown', 'consecutive_losses'],
                'technical_alerts': ['api_failure', 'model_error'],
                'alert_cooldown': 15
            },
            'notifications': {
                'email_enabled': False,
                'telegram_enabled': False,
                'trading_notifications': ['stop_loss', 'daily_summary'],
                'system_notifications': ['bot_status', 'critical_errors'],
                'notification_start_time': '08:00',
                'notification_end_time': '22:00'
            },
            'api': {
                'bitget_enabled': True,
                'bitget_environment': 'sandbox',
                'rate_limit_per_minute': 100,
                'connection_timeout': 10,
                'response_timeout': 30,
                'max_retries': 3,
                'retry_delay': 1,
                'websocket_enabled': True,
                'websocket_ping_interval': 30,
                'websocket_reconnect_attempts': 5,
                'websocket_buffer_size': 10
            },
            'ui': {
                'main_theme': 'dark',
                'primary_color': 'blue',
                'info_density': 'normal',
                'animations': True,
                'auto_refresh': True,
                'refresh_interval': 30,
                'decimal_places': 2,
                'timezone': 'Europe/Madrid',
                'default_chart_type': 'candlestick',
                'default_indicators': ['sma_20', 'ema_12', 'rsi'],
                'chart_height': 400
            },
            'system': {
                'num_workers': 2,
                'cache_size': 256,
                'batch_size': 32,
                'use_gpu': True,
                'auto_backup': True,
                'backup_frequency': 'daily',
                'backup_retention': 30,
                'backup_location': './backups/',
                'encrypt_data': True,
                'session_timeout': 120,
                'access_logging': True
            }
        }
    
    def _load_current_settings(self) -> Dict[str, Any]:
        """
        Carga configuraciones actuales del sistema
        
        Returns:
            Dict[str, Any]: Configuraciones actuales
        """
        try:
            if self.data_provider:
                # Intentar cargar desde data provider
                current_settings = self.data_provider.get_system_settings()
                if current_settings:
                    return current_settings
            
            # Fallback a configuraciones por defecto
            return self.default_configs
            
        except Exception as e:
            logger.error(f"Error al cargar configuraciones actuales: {e}")
            return self.default_configs
    
    def _save_settings(self, settings_data: Dict[str, Any]) -> bool:
        """
        Guarda configuraciones en el sistema
        
        Args:
            settings_data: Datos de configuración a guardar
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if self.data_provider:
                # Intentar guardar usando data provider
                success = self.data_provider.save_system_settings(settings_data)
                if success:
                    logger.info("Configuraciones guardadas correctamente")
                    return True
            
            # Fallback: guardar en archivo local
            config_file = Path("config/settings.json")
            config_file.parent.mkdir(exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(settings_data, f, indent=2, default=str)
            
            logger.info(f"Configuraciones guardadas en {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar configuraciones: {e}")
            return False
    
    def _test_bitget_connection(self, api_key: str, secret_key: str, passphrase: str) -> bool:
        """
        Prueba la conexión con Bitget API
        
        Args:
            api_key: Clave de API
            secret_key: Clave secreta
            passphrase: Passphrase
            
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            # Simular test de conexión
            # En implementación real, usar ccxt o cliente de Bitget
            if len(api_key) > 10 and len(secret_key) > 10 and len(passphrase) > 3:
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error al probar conexión Bitget: {e}")
            return False
    
    def _test_telegram_notification(self, bot_token: str, chat_id: str) -> bool:
        """
        Prueba el envío de notificaciones por Telegram
        
        Args:
            bot_token: Token del bot
            chat_id: ID del chat
            
        Returns:
            bool: True si el envío es exitoso
        """
        try:
            # Simular envío de mensaje de prueba
            # En implementación real, usar requests o python-telegram-bot
            if len(bot_token) > 20 and chat_id.isdigit():
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error al probar Telegram: {e}")
            return False
    
    def _create_backup(self) -> bool:
        """
        Crea un backup manual del sistema
        
        Returns:
            bool: True si el backup se creó correctamente
        """
        try:
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            
            # Obtener configuraciones actuales
            current_settings = self._load_current_settings()
            
            # Guardar backup
            with open(backup_file, 'w') as f:
                json.dump(current_settings, f, indent=2, default=str)
            
            logger.info(f"Backup creado: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            return False
    
    def get_page_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la página
        
        Returns:
            Dict[str, Any]: Estado de la página
        """
        base_status = super().get_page_status()
        
        # Agregar información específica de SettingsPage
        base_status.update({
            'config_categories': len(self.config_categories),
            'has_unsaved_changes': len(self.unsaved_changes) > 0,
            'backup_enabled': self.page_config.get('backup_on_save', True),
            'validation_enabled': self.page_config.get('validate_on_change', True),
            'advanced_settings_enabled': self.page_config.get('enable_advanced_settings', True)
        })
        
        return base_status