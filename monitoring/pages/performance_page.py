"""
monitoring/pages/performance_page.py
Página de Análisis de Rendimiento - Trading Bot v10

Esta página proporciona análisis avanzado de rendimiento:
- Métricas financieras detalladas (Sharpe, Sortino, Calmar, etc.)
- Análisis de drawdown y volatilidad
- Comparación con benchmarks
- Análisis de atribución de rendimiento
- Optimización de tamaño de posiciones
- Reportes de rendimiento exportables
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

class RiskAnalysisPage(BasePage):
    """
    Página de análisis integral de riesgo del Trading Bot v10
    
    Proporciona análisis avanzado de riesgo de mercado, operacional
    y de portfolio con herramientas de gestión y monitoreo.
    """
    
    def __init__(self, data_provider=None):
        """
        Inicializa la página de análisis de riesgo
        
        Args:
            data_provider: Proveedor de datos centralizado
        """
        super().__init__(data_provider=data_provider)
        
        # Configuración específica de la página Risk Analysis
        self.page_config.update({
            'title': 'Análisis de Riesgo',
            'update_interval': 30000,  # 30 segundos
            'auto_refresh': True,
            'enable_stress_testing': True,
            'enable_monte_carlo': True,
            'confidence_levels': [0.90, 0.95, 0.99],
            'default_confidence': 0.95,
            'chart_height': 450,
            'risk_alert_threshold': 0.15  # 15% para alertas
        })
        
        # Tipos de riesgo a analizar
        self.risk_categories = {
            'market': {
                'name': 'Riesgo de Mercado',
                'color': 'danger',
                'icon': 'fas fa-chart-line',
                'metrics': ['var', 'cvar', 'volatility', 'beta']
            },
            'credit': {
                'name': 'Riesgo de Crédito',
                'color': 'warning',
                'icon': 'fas fa-handshake',
                'metrics': ['counterparty_exposure', 'credit_rating']
            },
            'liquidity': {
                'name': 'Riesgo de Liquidez',
                'color': 'info',
                'icon': 'fas fa-tint',
                'metrics': ['bid_ask_spread', 'market_impact', 'trading_volume']
            },
            'operational': {
                'name': 'Riesgo Operacional',
                'color': 'secondary',
                'icon': 'fas fa-cogs',
                'metrics': ['system_uptime', 'execution_slippage', 'api_failures']
            },
            'concentration': {
                'name': 'Riesgo de Concentración',
                'color': 'primary',
                'icon': 'fas fa-bullseye',
                'metrics': ['position_concentration', 'sector_exposure', 'correlation_risk']
            }
        }
        
        # Escenarios de stress testing
        self.stress_scenarios = {
            'market_crash': {
                'name': 'Crash de Mercado',
                'description': 'Caída del 20% en todos los activos',
                'shock': -0.20,
                'duration_days': 1
            },
            'flash_crash': {
                'name': 'Flash Crash',
                'description': 'Caída súbita del 10% en 1 hora',
                'shock': -0.10,
                'duration_days': 0.04  # 1 hora
            },
            'volatility_spike': {
                'name': 'Spike de Volatilidad',
                'description': 'Aumento de volatilidad 5x',
                'shock': 0,
                'volatility_multiplier': 5
            },
            'liquidity_crisis': {
                'name': 'Crisis de Liquidez',
                'description': 'Spreads bid-ask aumentan 10x',
                'shock': 0,
                'liquidity_impact': 10
            },
            'correlation_breakdown': {
                'name': 'Breakdown de Correlaciones',
                'description': 'Correlaciones tienden a 1',
                'correlation_shock': 0.9
            },
            'black_swan': {
                'name': 'Evento Cisne Negro',
                'description': 'Evento extremo improbable',
                'shock': -0.50,
                'probability': 0.001
            }
        }
        
        # Límites de riesgo configurables
        self.risk_limits = {
            'max_portfolio_var': 0.05,  # 5% VaR máximo
            'max_position_size': 0.20,  # 20% máximo por posición
            'max_sector_exposure': 0.40,  # 40% máximo por sector
            'max_correlation': 0.80,  # 80% correlación máxima
            'max_drawdown': 0.15,  # 15% drawdown máximo
            'min_liquidity_ratio': 0.30  # 30% mínimo en activos líquidos
        }
        
        logger.info("RiskAnalysisPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de análisis de riesgo
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Análisis de Riesgo",
                    subtitle="Gestión integral de riesgo y monitoreo de exposiciones",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Panel de alertas de riesgo
                self._create_risk_alerts_section(),
                
                # Controles de configuración
                self._create_risk_controls_section(),
                
                # Dashboard de riesgo principal
                self._create_risk_dashboard_section(),
                
                # Análisis de VaR y métricas de mercado
                dbc.Row([
                    dbc.Col([
                        self._create_var_analysis_section()
                    ], width=8),
                    dbc.Col([
                        self._create_risk_limits_monitor_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Matriz de correlaciones y exposiciones
                dbc.Row([
                    dbc.Col([
                        self._create_correlation_matrix_section()
                    ], width=6),
                    dbc.Col([
                        self._create_exposure_analysis_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Stress testing y análisis de escenarios
                self._create_stress_testing_section(),
                
                # Monte Carlo y simulaciones
                self._create_monte_carlo_section(),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("risk-refresh-interval"),
                dcc.Store(id='risk-data-store'),
                dcc.Store(id='risk-config-store', data={
                    'confidence_level': self.page_config['default_confidence'],
                    'time_horizon': 1,  # días
                    'enable_alerts': True,
                    'stress_scenario': 'market_crash'
                }),
                
            ], fluid=True, className="risk-analysis-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de RiskAnalysisPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de análisis de riesgo: {e}")
            ])
    
    def _create_risk_alerts_section(self) -> dbc.Row:
        """Crea la sección de alertas de riesgo"""
        return dbc.Row([
            dbc.Col([
                html.Div(id="risk-alerts-container")
            ], width=12)
        ], className="mb-4")
    
    def _create_risk_controls_section(self) -> dbc.Row:
        """Crea la sección de controles de configuración"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Nivel de confianza
                            dbc.Col([
                                html.Label("Nivel de Confianza:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="confidence-level-selector",
                                    options=[
                                        {'label': '90%', 'value': 0.90},
                                        {'label': '95%', 'value': 0.95},
                                        {'label': '99%', 'value': 0.99}
                                    ],
                                    value=self.page_config['default_confidence'],
                                    placeholder="Nivel de confianza"
                                )
                            ], width=12, md=2),
                            
                            # Horizonte temporal
                            dbc.Col([
                                html.Label("Horizonte (días):", className="form-label mb-1"),
                                dbc.Input(
                                    id="time-horizon-input",
                                    type="number",
                                    value=1,
                                    min=1,
                                    max=30,
                                    step=1
                                )
                            ], width=12, md=2),
                            
                            # Método de cálculo
                            dbc.Col([
                                html.Label("Método VaR:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="var-method-selector",
                                    options=[
                                        {'label': 'Histórico', 'value': 'historical'},
                                        {'label': 'Paramétrico', 'value': 'parametric'},
                                        {'label': 'Monte Carlo', 'value': 'monte_carlo'}
                                    ],
                                    value='historical',
                                    placeholder="Método"
                                )
                            ], width=12, md=2),
                            
                            # Alertas activas
                            dbc.Col([
                                html.Label("Alertas:", className="form-label mb-1"),
                                dbc.Switch(
                                    id="enable-alerts-switch",
                                    label="Activar alertas automáticas",
                                    value=True
                                )
                            ], width=12, md=3),
                            
                            # Botones de acción
                            dbc.Col([
                                html.Label("Acciones:", className="form-label mb-1"),
                                dbc.ButtonGroup([
                                    dbc.Button("Recalcular", id="recalculate-risk-btn", 
                                              color="primary", size="sm"),
                                    dbc.Button("Configurar Límites", id="config-limits-btn", 
                                              color="secondary", size="sm")
                                ])
                            ], width=12, md=3)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_risk_dashboard_section(self) -> dbc.Row:
        """Crea el dashboard principal de riesgo"""
        return dbc.Row([
            dbc.Col([
                html.H5("Dashboard de Riesgo", className="section-title mb-3"),
                self.create_loading_component(
                    "risk-dashboard",
                    html.Div(id="risk-dashboard-cards"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_var_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de VaR"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Value at Risk (VaR)", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "var-analysis",
                    dcc.Graph(
                        id="var-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_risk_limits_monitor_section(self) -> dbc.Card:
        """Crea la sección de monitoreo de límites"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Monitor de Límites de Riesgo", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "risk-limits",
                    html.Div(id="risk-limits-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_correlation_matrix_section(self) -> dbc.Card:
        """Crea la sección de matriz de correlaciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Matriz de Correlaciones", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "correlation-matrix",
                    dcc.Graph(
                        id="correlation-matrix-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_exposure_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de exposiciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Exposiciones", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "exposure-analysis",
                    dcc.Graph(
                        id="exposure-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_stress_testing_section(self) -> dbc.Row:
        """Crea la sección de stress testing"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Stress Testing", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                dcc.Dropdown(
                                    id="stress-scenario-selector",
                                    options=[
                                        {'label': scenario['name'], 'value': key}
                                        for key, scenario in self.stress_scenarios.items()
                                    ],
                                    value='market_crash',
                                    placeholder="Escenario",
                                    className="stress-scenario-dropdown"
                                )
                            ], width="auto", className="ms-auto")
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                self.create_loading_component(
                                    "stress-test-results",
                                    dcc.Graph(
                                        id="stress-test-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=8),
                            dbc.Col([
                                html.Div(id="stress-test-summary")
                            ], width=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_monte_carlo_section(self) -> dbc.Row:
        """Crea la sección de simulaciones Monte Carlo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Simulación Monte Carlo", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="monte-carlo-simulations",
                                        type="number",
                                        value=10000,
                                        min=1000,
                                        max=100000,
                                        step=1000
                                    ),
                                    dbc.InputGroupText("simulaciones")
                                ], size="sm")
                            ], width="auto"),
                            dbc.Col([
                                dbc.Button("Ejecutar", id="run-monte-carlo-btn", 
                                          color="primary", size="sm")
                            ], width="auto")
                        ])
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                self.create_loading_component(
                                    "monte-carlo-results",
                                    dcc.Graph(
                                        id="monte-carlo-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=8),
                            dbc.Col([
                                html.Div(id="monte-carlo-statistics")
                            ], width=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de análisis de riesgo
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para actualizar configuración de riesgo
        @app.callback(
            Output('risk-config-store', 'data'),
            [Input('confidence-level-selector', 'value'),
             Input('time-horizon-input', 'value'),
             Input('var-method-selector', 'value'),
             Input('enable-alerts-switch', 'value'),
             Input('stress-scenario-selector', 'value')],
            [State('risk-config-store', 'data')]
        )
        def update_risk_config(confidence, horizon, method, alerts, scenario, current_config):
            """Actualiza configuración de análisis de riesgo"""
            return {
                'confidence_level': confidence or self.page_config['default_confidence'],
                'time_horizon': horizon or 1,
                'var_method': method or 'historical',
                'enable_alerts': alerts if alerts is not None else True,
                'stress_scenario': scenario or 'market_crash',
                'last_update': datetime.now().isoformat()
            }
        
        # Callback principal para cargar datos de riesgo
        @app.callback(
            Output('risk-data-store', 'data'),
            [Input('risk-config-store', 'data'),
             Input('risk-refresh-interval', 'n_intervals'),
             Input('risk-refresh-btn', 'n_clicks'),
             Input('recalculate-risk-btn', 'n_clicks')]
        )
        def update_risk_data(config, n_intervals, refresh_clicks, recalc_clicks):
            """Actualiza datos de análisis de riesgo"""
            try:
                risk_data = self._calculate_risk_metrics(config)
                correlation_data = self._calculate_correlations()
                exposure_data = self._calculate_exposures()
                
                self.update_page_stats()
                
                return {
                    'risk_metrics': risk_data,
                    'correlations': correlation_data,
                    'exposures': exposure_data,
                    'config': config,
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de riesgo: {e}")
                return {}
        
        # Callback para alertas de riesgo
        @app.callback(
            Output('risk-alerts-container', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_alerts(risk_data):
            """Actualiza alertas de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return html.Div()
                
                return self._create_risk_alerts(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear alertas de riesgo: {e}")
                return html.Div()
        
        # Callback para dashboard de riesgo
        @app.callback(
            Output('risk-dashboard-cards', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_dashboard(risk_data):
            """Actualiza dashboard principal de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return self.create_empty_state(
                        title="Calculando métricas de riesgo...",
                        message="Procesando datos para análisis de riesgo",
                        icon="fas fa-calculator"
                    )
                
                return self._create_risk_dashboard_cards(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear dashboard de riesgo: {e}")
                return self.create_error_alert("Error al calcular métricas de riesgo")
        
        # Callback para análisis de VaR
        @app.callback(
            Output('var-analysis-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_var_analysis(risk_data):
            """Actualiza análisis de VaR"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return self._create_empty_chart("Calculando VaR...")
                
                return self._create_var_analysis_chart(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de VaR: {e}")
                return self._create_empty_chart("Error en análisis de VaR")
        
        # Callback para monitor de límites
        @app.callback(
            Output('risk-limits-container', 'children'),
            [Input('risk-data-store', 'data')]
        )
        def update_risk_limits_monitor(risk_data):
            """Actualiza monitor de límites de riesgo"""
            try:
                if not risk_data or not risk_data.get('risk_metrics'):
                    return html.P("Cargando límites de riesgo...", className="text-muted")
                
                return self._create_risk_limits_monitor(risk_data['risk_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear monitor de límites: {e}")
                return self.create_error_alert("Error en monitor de límites")
        
        # Callback para matriz de correlaciones
        @app.callback(
            Output('correlation-matrix-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_correlation_matrix(risk_data):
            """Actualiza matriz de correlaciones"""
            try:
                if not risk_data or not risk_data.get('correlations'):
                    return self._create_empty_chart("Calculando correlaciones...")
                
                return self._create_correlation_heatmap(risk_data['correlations'])
                
            except Exception as e:
                logger.error(f"Error al crear matriz de correlaciones: {e}")
                return self._create_empty_chart("Error en matriz de correlaciones")
        
        # Callback para análisis de exposiciones
        @app.callback(
            Output('exposure-analysis-chart', 'figure'),
            [Input('risk-data-store', 'data')]
        )
        def update_exposure_analysis(risk_data):
            """Actualiza análisis de exposiciones"""
            try:
                if not risk_data or not risk_data.get('exposures'):
                    return self._create_empty_chart("Calculando exposiciones...")
                
                return self._create_exposure_chart(risk_data['exposures'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de exposiciones: {e}")
                return self._create_empty_chart("Error en análisis de exposiciones")
        
        # Callback para stress testing
        @app.callback(
            [Output('stress-test-chart', 'figure'),
             Output('stress-test-summary', 'children')],
            [Input('risk-data-store', 'data'),
             Input('stress-scenario-selector', 'value')]
        )
        def update_stress_testing(risk_data, scenario):
            """Actualiza análisis de stress testing"""
            try:
                if not risk_data or not scenario:
                    return (
                        self._create_empty_chart("Seleccione un escenario..."),
                        html.P("Configurando stress test...", className="text-muted")
                    )
                
                stress_results = self._run_stress_test(risk_data, scenario)
                chart = self._create_stress_test_chart(stress_results, scenario)
                summary = self._create_stress_test_summary(stress_results, scenario)
                
                return chart, summary
                
            except Exception as e:
                logger.error(f"Error en stress testing: {e}")
                return (
                    self._create_empty_chart("Error en stress test"),
                    self.create_error_alert("Error en stress testing")
                )
        
        # Callback para Monte Carlo
        @app.callback(
            [Output('monte-carlo-chart', 'figure'),
             Output('monte-carlo-statistics', 'children')],
            [Input('run-monte-carlo-btn', 'n_clicks'),
             Input('risk-data-store', 'data')],
            [State('monte-carlo-simulations', 'value')]
        )
        def update_monte_carlo(n_clicks, risk_data, num_simulations):
            """Actualiza simulación Monte Carlo"""
            try:
                if not n_clicks or not risk_data:
                    return (
                        self._create_empty_chart("Presione 'Ejecutar' para iniciar simulación"),
                        html.P("Listo para ejecutar Monte Carlo", className="text-muted")
                    )
                
                mc_results = self._run_monte_carlo_simulation(risk_data, num_simulations or 10000)
                chart = self._create_monte_carlo_chart(mc_results)
                stats = self._create_monte_carlo_statistics(mc_results)
                
                return chart, stats
                
            except Exception as e:
                logger.error(f"Error en Monte Carlo: {e}")
                return (
                    self._create_empty_chart("Error en simulación"),
                    self.create_error_alert("Error en Monte Carlo")
                )
        
        logger.info("Callbacks de RiskAnalysisPage registrados")
    
    def _calculate_risk_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas de riesgo según configuración"""
        try:
            confidence_level = config.get('confidence_level', 0.95)
            time_horizon = config.get('time_horizon', 1)
            
            # Obtener datos de portfolio si disponible
            if self.data_provider:
                symbols = self.data_provider.get_configured_symbols()
                portfolio_data = {}
                
                for symbol in symbols:
                    metrics = self.data_provider.get_symbol_metrics(symbol)
                    if metrics:
                        portfolio_data[symbol] = metrics
            else:
                # Datos simulados
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
                portfolio_data = self._generate_sample_portfolio_data(symbols)
        
        running_max = np.maximum.accumulate(cumulative_returns + 1)
        drawdowns = (running_max - (cumulative_returns + 1)) / running_max
        
        # Calcular métricas
        total_return = cumulative_returns[-1]
        annualized_return = (1 + total_return) ** (365 / days) - 1
        volatility = np.std(daily_returns) * np.sqrt(252)  # Anualizada
        max_drawdown = np.max(drawdowns)
        
        # Sharpe Ratio
        risk_free_rate = config.get('risk_free_rate', 0.02)
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
        
        # Calmar Ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # VaR y CVaR
        var_95 = np.percentile(daily_returns, 5)
        cvar_95 = np.mean(daily_returns[daily_returns <= var_95]) if np.any(daily_returns <= var_95) else 0
        
        # Métricas de trading simuladas
        total_trades = np.random.randint(50, 200)
        win_rate = np.random.uniform(55, 75)
        winning_trades = int(total_trades * win_rate / 100)
        avg_win = np.random.uniform(0.02, 0.05)  # 2-5%
        avg_loss = np.random.uniform(-0.015, -0.03)  # 1.5-3%
        profit_factor = (winning_trades * avg_win) / ((total_trades - winning_trades) * abs(avg_loss))
        expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
        
        return {
            'dates': dates.tolist(),
            'daily_returns': daily_returns.tolist(),
            'cumulative_returns': cumulative_returns.tolist(),
            'drawdowns': drawdowns.tolist(),
            'metrics': {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'var_95': var_95,
                'cvar_95': cvar_95,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades
            }
        }
    
    def _get_benchmark_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene datos del benchmark"""
        benchmark = config.get('benchmark', 'SPY')
        period = config.get('period', '3M')
        days = self.analysis_periods.get(period, {}).get('days', 90)
        
        if not days:
            days = 365
        
        # Generar retornos del benchmark
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), end=datetime.now(), freq='D')
        
        # Retornos típicos según benchmark
        if benchmark == 'SPY':
            daily_returns = np.random.normal(0.0004, 0.012, len(dates))  # S&P 500
        elif benchmark == 'BTC':
            daily_returns = np.random.normal(0.001, 0.04, len(dates))  # Bitcoin más volátil
        elif benchmark == 'RISK_FREE':
            daily_returns = np.full(len(dates), config.get('risk_free_rate', 0.02) / 365)  # Tasa libre de riesgo
        else:
            daily_returns = np.random.normal(0.0003, 0.01, len(dates))  # Benchmark genérico
        
        cumulative_returns = np.cumprod(1 + daily_returns) - 1
        
        return {
            'benchmark': benchmark,
            'dates': dates.tolist(),
            'daily_returns': daily_returns.tolist(),
            'cumulative_returns': cumulative_returns.tolist(),
            'total_return': cumulative_returns[-1],
            'annualized_return': (1 + cumulative_returns[-1]) ** (365 / days) - 1,
            'volatility': np.std(daily_returns) * np.sqrt(252)
        }
    
    def _format_portfolio_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea métricas del portfolio"""
        # Convertir métricas del performance tracker al formato esperado
        return metrics  # Ya está en el formato correcto
    
    def _format_symbol_metrics(self, metrics) -> Dict[str, Any]:
        """Formatea métricas de un símbolo específico"""
        if hasattr(metrics, '__dict__'):
            return metrics.__dict__
        return metrics
    
    def _create_key_metrics_cards(self, performance_data: Dict[str, Any]) -> dbc.Row:
        """Crea tarjetas de métricas principales"""
        if not performance_data:
            return dbc.Row([])
        
        metrics = performance_data.get('metrics', {})
        cards = []
        
        # Retorno Total
        total_return = metrics.get('total_return', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Retorno Total",
                value=f"{total_return*100:.2f}%",
                subtitle="Período completo",
                icon="fas fa-chart-line",
                color="success" if total_return > 0 else "danger"
            )
        ], width=12, md=6, lg=2))
        
        # Retorno Anualizado
        annual_return = metrics.get('annualized_return', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Retorno Anualizado",
                value=f"{annual_return*100:.2f}%",
                subtitle="Base anual",
                icon="fas fa-calendar-alt",
                color="primary"
            )
        ], width=12, md=6, lg=2))
        
        # Sharpe Ratio
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Sharpe Ratio",
                value=f"{sharpe_ratio:.2f}",
                subtitle="Riesgo ajustado",
                icon="fas fa-balance-scale",
                color="success" if sharpe_ratio > 1 else "warning"
            )
        ], width=12, md=6, lg=2))
        
        # Máximo Drawdown
        max_dd = metrics.get('max_drawdown', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Máximo Drawdown",
                value=f"{max_dd*100:.2f}%",
                subtitle="Pérdida máxima",
                icon="fas fa-arrow-down",
                color="danger" if max_dd > 0.15 else "warning"
            )
        ], width=12, md=6, lg=2))
        
        # Volatilidad
        volatility = metrics.get('volatility', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Volatilidad",
                value=f"{volatility*100:.2f}%",
                subtitle="Desviación estándar",
                icon="fas fa-wave-square",
                color="info"
            )
        ], width=12, md=6, lg=2))
        
        # Win Rate
        win_rate = metrics.get('win_rate', 0)
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Win Rate",
                value=f"{win_rate:.1f}%",
                subtitle="Tasa de éxito",
                icon="fas fa-target",
                color="success" if win_rate > 60 else "warning"
            )
        ], width=12, md=6, lg=2))
        
        return dbc.Row(cards)
    
    def _create_performance_evolution_chart(self, performance_data: Dict[str, Any], 
                                          benchmark_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de evolución del rendimiento"""
        try:
            fig = go.Figure()
            
            # Línea de rendimiento del portfolio
            dates = performance_data.get('dates', [])
            cumulative_returns = performance_data.get('cumulative_returns', [])
            
            if dates and cumulative_returns:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[r * 100 for r in cumulative_returns],
                    mode='lines',
                    name='Portfolio',
                    line=dict(color='#007bff', width=2),
                    hovertemplate='Portfolio<br>Retorno: %{y:.2f}%<br>Fecha: %{x}<extra></extra>'
                ))
            
            # Línea del benchmark si está disponible
            if benchmark_data and benchmark_data.get('dates'):
                benchmark_dates = benchmark_data.get('dates', [])
                benchmark_returns = benchmark_data.get('cumulative_returns', [])
                benchmark_name = self.benchmarks.get(benchmark_data.get('benchmark', ''), 'Benchmark')
                
                if benchmark_dates and benchmark_returns:
                    fig.add_trace(go.Scatter(
                        x=benchmark_dates,
                        y=[r * 100 for r in benchmark_returns],
                        mode='lines',
                        name=benchmark_name,
                        line=dict(color='#6c757d', width=2, dash='dash'),
                        hovertemplate=f'{benchmark_name}<br>Retorno: %{{y:.2f}}%<br>Fecha: %{{x}}<extra></extra>'
                    ))
            
            # Configuración del gráfico
            fig.update_layout(
                title="Evolución del Rendimiento Acumulado",
                xaxis_title="Fecha",
                yaxis_title="Retorno Acumulado (%)",
                height=self.page_config['chart_height'],
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            # Línea en y=0 para referencia
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            # Configurar ejes
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de evolución: {e}")
            return self._create_empty_chart("Error al generar gráfico de evolución")
    
    def _create_drawdown_chart(self, performance_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de análisis de drawdown"""
        try:
            fig = go.Figure()
            
            dates = performance_data.get('dates', [])
            drawdowns = performance_data.get('drawdowns', [])
            
            if dates and drawdowns:
                # Área de drawdown
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=[-d * 100 for d in drawdowns],  # Negativo para mostrar como pérdida
                    mode='lines',
                    name='Drawdown',
                    fill='tonexty',
                    fillcolor='rgba(255, 0, 0, 0.3)',
                    line=dict(color='red', width=2),
                    hovertemplate='Drawdown: %{y:.2f}%<br>Fecha: %{x}<extra></extra>'
                ))
            
            # Línea en y=0
            fig.add_hline(y=0, line_color="black", line_width=1)
            
            # Líneas de referencia para niveles críticos
            fig.add_hline(y=-5, line_dash="dash", line_color="orange", 
                         annotation_text="5% DD", annotation_position="right")
            fig.add_hline(y=-10, line_dash="dash", line_color="red", 
                         annotation_text="10% DD", annotation_position="right")
            
            # Configuración
            fig.update_layout(
                title="Análisis de Drawdown",
                xaxis_title="Fecha",
                yaxis_title="Drawdown (%)",
                height=self.page_config['chart_height'],
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            # Configurar ejes
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de drawdown: {e}")
            return self._create_empty_chart("Error al generar análisis de drawdown")
    
    def _create_risk_metrics_table(self, performance_data: Dict[str, Any]) -> html.Div:
        """Crea tabla de métricas de riesgo"""
        try:
            metrics = performance_data.get('metrics', {})
            
            risk_metrics = [
                {
                    'metric': 'Volatilidad Anualizada',
                    'value': f"{metrics.get('volatility', 0)*100:.2f}%",
                    'description': 'Desviación estándar de retornos'
                },
                {
                    'metric': 'Máximo Drawdown',
                    'value': f"{metrics.get('max_drawdown', 0)*100:.2f}%",
                    'description': 'Máxima pérdida desde un pico'
                },
                {
                    'metric': 'VaR 95%',
                    'value': f"{metrics.get('var_95', 0)*100:.2f}%",
                    'description': 'Pérdida máxima esperada (95% confianza)'
                },
                {
                    'metric': 'CVaR 95%',
                    'value': f"{metrics.get('cvar_95', 0)*100:.2f}%",
                    'description': 'Pérdida esperada cuando se excede VaR'
                },
                {
                    'metric': 'Sortino Ratio',
                    'value': f"{metrics.get('sortino_ratio', 0):.2f}",
                    'description': 'Retorno ajustado por riesgo negativo'
                },
                {
                    'metric': 'Calmar Ratio',
                    'value': f"{metrics.get('calmar_ratio', 0):.2f}",
                    'description': 'Retorno anualizado / Máximo Drawdown'
                }
            ]
            
            rows = []
            for metric in risk_metrics:
                rows.append(
                    html.Tr([
                        html.Td(metric['metric'], className="fw-bold"),
                        html.Td(metric['value'], className="text-end"),
                        html.Td(html.Small(metric['description'], className="text-muted"))
                    ])
                )
            
            return dbc.Table([
                html.Tbody(rows)
            ], striped=True, hover=True, responsive=True, className="mb-0")
            
        except Exception as e:
            logger.error(f"Error al crear tabla de métricas de riesgo: {e}")
            return html.P("Error al cargar métricas de riesgo", className="text-danger")
    
    def _create_trading_metrics_table(self, performance_data: Dict[str, Any]) -> html.Div:
        """Crea tabla de métricas de trading"""
        try:
            metrics = performance_data.get('metrics', {})
            
            trading_metrics = [
                {
                    'metric': 'Total de Trades',
                    'value': f"{metrics.get('total_trades', 0):,}",
                    'description': 'Número total de operaciones'
                },
                {
                    'metric': 'Win Rate',
                    'value': f"{metrics.get('win_rate', 0):.1f}%",
                    'description': 'Porcentaje de trades ganadores'
                },
                {
                    'metric': 'Ganancia Promedio',
                    'value': f"{metrics.get('avg_win', 0)*100:.2f}%",
                    'description': 'Retorno promedio de trades ganadores'
                },
                {
                    'metric': 'Pérdida Promedio',
                    'value': f"{metrics.get('avg_loss', 0)*100:.2f}%",
                    'description': 'Retorno promedio de trades perdedores'
                },
                {
                    'metric': 'Profit Factor',
                    'value': f"{metrics.get('profit_factor', 0):.2f}",
                    'description': 'Ganancias brutas / Pérdidas brutas'
                },
                {
                    'metric': 'Expectancy',
                    'value': f"{metrics.get('expectancy', 0)*100:.2f}%",
                    'description': 'Retorno esperado por trade'
                }
            ]
            
            rows = []
            for metric in trading_metrics:
                rows.append(
                    html.Tr([
                        html.Td(metric['metric'], className="fw-bold"),
                        html.Td(metric['value'], className="text-end"),
                        html.Td(html.Small(metric['description'], className="text-muted"))
                    ])
                )
            
            return dbc.Table([
                html.Tbody(rows)
            ], striped=True, hover=True, responsive=True, className="mb-0")
            
        except Exception as e:
            logger.error(f"Error al crear tabla de métricas de trading: {e}")
            return html.P("Error al cargar métricas de trading", className="text-danger")
    
    def _create_benchmark_comparison_chart(self, performance_data: Dict[str, Any], 
                                         benchmark_data: Dict[str, Any], 
                                         config: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de comparación con benchmark"""
        try:
            fig = go.Figure()
            
            # Métricas del portfolio
            portfolio_metrics = performance_data.get('metrics', {})
            portfolio_return = portfolio_metrics.get('annualized_return', 0) * 100
            portfolio_volatility = portfolio_metrics.get('volatility', 0) * 100
            portfolio_sharpe = portfolio_metrics.get('sharpe_ratio', 0)
            
            # Métricas del benchmark
            benchmark_return = benchmark_data.get('annualized_return', 0) * 100
            benchmark_volatility = benchmark_data.get('volatility', 0) * 100
            benchmark_name = self.benchmarks.get(benchmark_data.get('benchmark', ''), 'Benchmark')
            
            # Calcular Sharpe del benchmark
            risk_free_rate = config.get('risk_free_rate', 0.02) * 100
            benchmark_sharpe = (benchmark_return - risk_free_rate) / benchmark_volatility if benchmark_volatility > 0 else 0
            
            # Scatter plot de retorno vs volatilidad
            fig.add_trace(go.Scatter(
                x=[portfolio_volatility],
                y=[portfolio_return],
                mode='markers',
                name='Portfolio',
                marker=dict(size=15, color='blue'),
                text=[f'Sharpe: {portfolio_sharpe:.2f}'],
                hovertemplate='Portfolio<br>Retorno: %{y:.2f}%<br>Volatilidad: %{x:.2f}%<br>%{text}<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=[benchmark_volatility],
                y=[benchmark_return],
                mode='markers',
                name=benchmark_name,
                marker=dict(size=15, color='gray'),
                text=[f'Sharpe: {benchmark_sharpe:.2f}'],
                hovertemplate=f'{benchmark_name}<br>Retorno: %{{y:.2f}}%<br>Volatilidad: %{{x:.2f}}%<br>%{{text}}<extra></extra>'
            ))
            
            # Líneas de Sharpe ratio constante
            volatility_range = np.linspace(0, max(portfolio_volatility, benchmark_volatility) * 1.2, 100)
            for sharpe in [0.5, 1.0, 1.5, 2.0]:
                returns_line = risk_free_rate + sharpe * volatility_range
                fig.add_trace(go.Scatter(
                    x=volatility_range,
                    y=returns_line,
                    mode='lines',
                    name=f'Sharpe {sharpe}',
                    line=dict(dash='dot', color='lightgray'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            # Configuración
            fig.update_layout(
                title="Comparación Retorno vs Riesgo",
                xaxis_title="Volatilidad (%)",
                yaxis_title="Retorno Anualizado (%)",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear comparación de benchmark: {e}")
            return self._create_empty_chart("Error en comparación de benchmark")
    
    def _create_attribution_chart(self, performance_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de análisis de atribución"""
        try:
            # Simulamos análisis de atribución por componentes
            components = ['Alpha', 'Beta', 'Sector Allocation', 'Security Selection', 'Residual']
            contributions = [0.03, 0.05, 0.02, 0.04, 0.01]  # Contribuciones simuladas
            
            colors = ['green' if c > 0 else 'red' for c in contributions]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=components,
                y=[c * 100 for c in contributions],
                marker_color=colors,
                name='Contribución',
                text=[f'{c*100:+.1f}%' for c in contributions],
                textposition='outside'
            ))
            
            # Línea en y=0
            fig.add_hline(y=0, line_color="black", line_width=1)
            
            fig.update_layout(
                title="Análisis de Atribución de Rendimiento",
                xaxis_title="Componente",
                yaxis_title="Contribución (%)",
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear análisis de atribución: {e}")
            return self._create_empty_chart("Error en análisis de atribución")
    
    def _create_returns_distribution_chart(self, performance_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de distribución de retornos"""
        try:
            daily_returns = performance_data.get('daily_returns', [])
            
            if not daily_returns:
                return self._create_empty_chart("No hay datos de retornos")
            
            # Convertir a porcentajes
            returns_pct = [r * 100 for r in daily_returns]
            
            fig = go.Figure()
            
            # Histograma
            fig.add_trace(go.Histogram(
                x=returns_pct,
                nbinsx=30,
                name='Distribución',
                opacity=0.7,
                marker_color='rgba(0, 123, 255, 0.7)'
            ))
            
            # Estadísticas
            mean_return = np.mean(returns_pct)
            std_return = np.std(returns_pct)
            
            # Líneas de estadísticas
            fig.add_vline(x=mean_return, line_dash="dash", line_color="red",
                         annotation_text=f"Media: {mean_return:.2f}%")
            fig.add_vline(x=mean_return + std_return, line_dash="dot", line_color="orange",
                         annotation_text=f"+1σ: {mean_return + std_return:.2f}%")
            fig.add_vline(x=mean_return - std_return, line_dash="dot", line_color="orange",
                         annotation_text=f"-1σ: {mean_return - std_return:.2f}%")
            
            fig.update_layout(
                title="Distribución de Retornos Diarios",
                xaxis_title="Retorno Diario (%)",
                yaxis_title="Frecuencia",
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear distribución de retornos: {e}")
            return self._create_empty_chart("Error en distribución de retornos")
    
    def _create_kelly_criterion_results(self, performance_data: Dict[str, Any]) -> html.Div:
        """Crea resultados del Kelly Criterion"""
        try:
            metrics = performance_data.get('metrics', {})
            
            # Parámetros para Kelly
            win_rate = metrics.get('win_rate', 0) / 100
            avg_win = abs(metrics.get('avg_win', 0))
            avg_loss = abs(metrics.get('avg_loss', 0))
            
            if avg_loss == 0:
                kelly_f = 0
            else:
                # Kelly Criterion: f = (bp - q) / b
                # donde b = avg_win/avg_loss, p = win_rate, q = 1-p
                b = avg_win / avg_loss
                p = win_rate
                q = 1 - p
                kelly_f = (b * p - q) / b
            
            # Limitar Kelly al 25% máximo por seguridad
            kelly_percentage = max(0, min(kelly_f * 100, 25))
            
            # Tamaño recomendado (50% del Kelly)
            recommended_size = kelly_percentage * 0.5
            
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        html.H6("Kelly Óptimo", className="text-primary"),
                        html.H4(f"{kelly_percentage:.1f}%", className="mb-0"),
                        html.Small("Tamaño teórico óptimo", className="text-muted")
                    ], width=6),
                    dbc.Col([
                        html.H6("Recomendado", className="text-success"),
                        html.H4(f"{recommended_size:.1f}%", className="mb-0"),
                        html.Small("50% del Kelly (conservador)", className="text-muted")
                    ], width=6)
                ]),
                html.Hr(),
                html.Div([
                    html.P([
                        html.Strong("Interpretación: "),
                        "Kelly Criterion sugiere el tamaño óptimo de posición para maximizar el crecimiento logarítmico del capital."
                    ], className="small text-muted mb-2"),
                    html.P([
                        html.Strong("Recomendación: "),
                        f"Usar {recommended_size:.1f}% del capital por posición para balance entre crecimiento y riesgo."
                    ], className="small text-muted mb-0")
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error al calcular Kelly Criterion: {e}")
            return html.P("Error en cálculo de Kelly Criterion", className="text-danger")
    
    def _create_portfolio_optimization_results(self, performance_data: Dict[str, Any]) -> html.Div:
        """Crea resultados de optimización de portfolio"""
        try:
            # Simulamos resultados de optimización
            current_allocation = {'BTCUSDT': 40, 'ETHUSDT': 35, 'ADAUSDT': 25}
            optimal_allocation = {'BTCUSDT': 45, 'ETHUSDT': 30, 'ADAUSDT': 25}
            
            improvement_metrics = {
                'expected_return': 0.02,  # 2% mejora
                'volatility_reduction': 0.015,  # 1.5% reducción
                'sharpe_improvement': 0.3  # 0.3 puntos
            }
            
            return html.Div([
                html.H6("Asignación Actual vs Óptima", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Strong("Actual:"),
                        html.Ul([
                            html.Li(f"{symbol}: {weight}%") 
                            for symbol, weight in current_allocation.items()
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Strong("Óptima:"),
                        html.Ul([
                            html.Li(f"{symbol}: {weight}%") 
                            for symbol, weight in optimal_allocation.items()
                        ])
                    ], width=6)
                ]),
                html.Hr(),
                html.H6("Mejoras Esperadas", className="mb-2"),
                html.Div([
                    dbc.Badge(f"+{improvement_metrics['expected_return']*100:.1f}% Retorno", 
                             color="success", className="me-2"),
                    dbc.Badge(f"-{improvement_metrics['volatility_reduction']*100:.1f}% Volatilidad", 
                             color="info", className="me-2"),
                    dbc.Badge(f"+{improvement_metrics['sharpe_improvement']:.1f} Sharpe", 
                             color="primary")
                ]),
                html.Hr(),
                html.P([
                    html.Strong("Recomendación: "),
                    "Rebalancear portfolio hacia la asignación óptima para mejorar métricas de riesgo-retorno."
                ], className="small text-muted mb-0")
            ])
            
        except Exception as e:
            logger.error(f"Error en optimización de portfolio: {e}")
            return html.P("Error en optimización de portfolio", className="text-danger")
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Crea un gráfico vacío con mensaje"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig
"""
monitoring/pages/performance_page.py
Página de Análisis de Rendimiento - Trading Bot v10

Esta página proporciona análisis avanzado de rendimiento:
- Métricas financieras detalladas (Sharpe, Sortino, Calmar, etc.)
- Análisis de drawdown y volatilidad
- Comparación con benchmarks
- Análisis de atribución de rendimiento
- Optimización de tamaño de posiciones
- Reportes de rendimiento exportables
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

class PerformancePage(BasePage):
    """
    Página de análisis avanzado de rendimiento del Trading Bot v10
    
    Proporciona métricas financieras detalladas, análisis de riesgo,
    comparaciones con benchmarks y optimización de estrategias.
    """
    
    def __init__(self, data_provider=None, performance_tracker=None):
        """
        Inicializa la página de análisis de rendimiento
        
        Args:
            data_provider: Proveedor de datos centralizado
            performance_tracker: Tracker de rendimiento avanzado
        """
        super().__init__(data_provider=data_provider, performance_tracker=performance_tracker)
        
        # Configuración específica de la página Performance
        self.page_config.update({
            'title': 'Análisis de Rendimiento',
            'update_interval': 60000,  # 1 minuto
            'auto_refresh': True,
            'enable_benchmark_comparison': True,
            'enable_attribution_analysis': True,
            'enable_optimization_tools': True,
            'chart_height': 500,
            'analysis_periods': ['1M', '3M', '6M', '1Y', 'YTD', 'ALL'],
            'default_period': '3M'
        })
        
        # Métricas de rendimiento disponibles
        self.performance_metrics = {
            'basic': {
                'total_return': 'Retorno Total',
                'annualized_return': 'Retorno Anualizado',
                'volatility': 'Volatilidad',
                'max_drawdown': 'Máximo Drawdown'
            },
            'risk_adjusted': {
                'sharpe_ratio': 'Sharpe Ratio',
                'sortino_ratio': 'Sortino Ratio',
                'calmar_ratio': 'Calmar Ratio',
                'treynor_ratio': 'Treynor Ratio'
            },
            'trading': {
                'win_rate': 'Win Rate',
                'profit_factor': 'Profit Factor',
                'expectancy': 'Expectancy',
                'avg_win': 'Ganancia Promedio'
            },
            'advanced': {
                'var_95': 'VaR 95%',
                'cvar_95': 'CVaR 95%',
                'jensen_alpha': 'Jensen Alpha',
                'information_ratio': 'Information Ratio'
            }
        }
        
        # Benchmarks disponibles
        self.benchmarks = {
            'SPY': 'S&P 500',
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'PORTFOLIO_60_40': 'Portfolio 60/40',
            'RISK_FREE': 'Tasa Libre de Riesgo'
        }
        
        # Períodos de análisis
        self.analysis_periods = {
            '1M': {'days': 30, 'label': '1 Mes'},
            '3M': {'days': 90, 'label': '3 Meses'},
            '6M': {'days': 180, 'label': '6 Meses'},
            '1Y': {'days': 365, 'label': '1 Año'},
            'YTD': {'days': None, 'label': 'Año a la Fecha'},
            'ALL': {'days': None, 'label': 'Todo el Período'}
        }
        
        logger.info("PerformancePage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de rendimiento
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Análisis de Rendimiento",
                    subtitle="Métricas financieras avanzadas y análisis de performance",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Controles de análisis
                self._create_analysis_controls_section(),
                
                # Resumen de métricas principales
                self._create_key_metrics_section(),
                
                # Gráficos principales de rendimiento
                dbc.Row([
                    dbc.Col([
                        self._create_performance_evolution_section()
                    ], width=8),
                    dbc.Col([
                        self._create_drawdown_analysis_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Análisis de riesgo y métricas avanzadas
                dbc.Row([
                    dbc.Col([
                        self._create_risk_metrics_section()
                    ], width=6),
                    dbc.Col([
                        self._create_trading_metrics_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Comparación con benchmarks
                self._create_benchmark_comparison_section(),
                
                # Análisis de atribución y distribución
                dbc.Row([
                    dbc.Col([
                        self._create_attribution_analysis_section()
                    ], width=6),
                    dbc.Col([
                        self._create_returns_distribution_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Herramientas de optimización
                self._create_optimization_tools_section(),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("performance-refresh-interval"),
                dcc.Store(id='performance-data-store'),
                dcc.Store(id='performance-analysis-config', data={
                    'period': self.page_config['default_period'],
                    'symbol': 'all',
                    'benchmark': 'SPY',
                    'risk_free_rate': 0.02
                }),
                
            ], fluid=True, className="performance-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de PerformancePage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de rendimiento: {e}")
            ])
    
    def _create_analysis_controls_section(self) -> dbc.Row:
        """Crea la sección de controles de análisis"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Selector de símbolo
                            dbc.Col([
                                html.Label("Símbolo:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="performance-symbol-selector",
                                    placeholder="Todos los símbolos",
                                    className="symbol-selector"
                                )
                            ], width=12, md=3),
                            
                            # Período de análisis
                            dbc.Col([
                                html.Label("Período:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="performance-period-selector",
                                    options=[
                                        {'label': period['label'], 'value': key}
                                        for key, period in self.analysis_periods.items()
                                    ],
                                    value=self.page_config['default_period'],
                                    placeholder="Período de análisis"
                                )
                            ], width=12, md=2),
                            
                            # Benchmark de comparación
                            dbc.Col([
                                html.Label("Benchmark:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="performance-benchmark-selector",
                                    options=[
                                        {'label': name, 'value': key}
                                        for key, name in self.benchmarks.items()
                                    ],
                                    value='SPY',
                                    placeholder="Benchmark"
                                )
                            ], width=12, md=2),
                            
                            # Tasa libre de riesgo
                            dbc.Col([
                                html.Label("Tasa Libre Riesgo:", className="form-label mb-1"),
                                dbc.Input(
                                    id="risk-free-rate-input",
                                    type="number",
                                    value=2.0,
                                    step=0.1,
                                    min=0,
                                    max=10,
                                    placeholder="2.0%"
                                )
                            ], width=12, md=2),
                            
                            # Configuración avanzada
                            dbc.Col([
                                html.Label("Opciones:", className="form-label mb-1"),
                                dbc.Checklist(
                                    id="performance-advanced-options",
                                    options=[
                                        {'label': 'Ajustar por inflación', 'value': 'inflation_adjusted'},
                                        {'label': 'Incluir dividendos', 'value': 'include_dividends'}
                                    ],
                                    value=[],
                                    inline=True
                                )
                            ], width=12, md=3)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_key_metrics_section(self) -> dbc.Row:
        """Crea la sección de métricas clave"""
        return dbc.Row([
            dbc.Col([
                html.H5("Métricas Principales", className="section-title mb-3"),
                self.create_loading_component(
                    "key-metrics",
                    html.Div(id="key-metrics-cards"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_performance_evolution_section(self) -> dbc.Card:
        """Crea la sección de evolución del rendimiento"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Evolución del Rendimiento", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "performance-evolution",
                    dcc.Graph(
                        id="performance-evolution-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_drawdown_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de drawdown"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Drawdown", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "drawdown-analysis",
                    dcc.Graph(
                        id="drawdown-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_risk_metrics_section(self) -> dbc.Card:
        """Crea la sección de métricas de riesgo"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Métricas de Riesgo", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "risk-metrics",
                    html.Div(id="risk-metrics-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_trading_metrics_section(self) -> dbc.Card:
        """Crea la sección de métricas de trading"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Métricas de Trading", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "trading-metrics",
                    html.Div(id="trading-metrics-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_benchmark_comparison_section(self) -> dbc.Row:
        """Crea la sección de comparación con benchmarks"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Comparación con Benchmarks", className="mb-0")
                    ]),
                    dbc.CardBody([
                        self.create_loading_component(
                            "benchmark-comparison",
                            dcc.Graph(
                                id="benchmark-comparison-chart",
                                config=self.get_default_chart_config(),
                                style={'height': '400px'}
                            ),
                            loading_type="default"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_attribution_analysis_section(self) -> dbc.Card:
        """Crea la sección de análisis de atribución"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Análisis de Atribución", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "attribution-analysis",
                    dcc.Graph(
                        id="attribution-analysis-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_returns_distribution_section(self) -> dbc.Card:
        """Crea la sección de distribución de retornos"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Distribución de Retornos", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "returns-distribution",
                    dcc.Graph(
                        id="returns-distribution-chart",
                        config=self.get_default_chart_config(),
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_optimization_tools_section(self) -> dbc.Row:
        """Crea la sección de herramientas de optimización"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Herramientas de Optimización", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Kelly Criterion", className="mb-3"),
                                html.Div(id="kelly-criterion-results")
                            ], width=6),
                            dbc.Col([
                                html.H6("Optimización de Portfolio", className="mb-3"),
                                html.Div(id="portfolio-optimization-results")
                            ], width=6)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de rendimiento
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para inicializar selector de símbolos
        @app.callback(
            Output('performance-symbol-selector', 'options'),
            [Input('performance-refresh-interval', 'n_intervals')]
        )
        def initialize_symbol_selector(n_intervals):
            """Inicializa opciones del selector de símbolos"""
            try:
                options = [{'label': 'Todos los símbolos', 'value': 'all'}]
                
                if self.data_provider:
                    symbols = self.data_provider.get_configured_symbols()
                    options.extend([{'label': symbol, 'value': symbol} for symbol in symbols])
                else:
                    example_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
                    options.extend([{'label': symbol, 'value': symbol} for symbol in example_symbols])
                
                return options
                
            except Exception as e:
                logger.error(f"Error al inicializar selector de símbolos: {e}")
                return [{'label': 'Error al cargar símbolos', 'value': 'all'}]
        
        # Callback para actualizar configuración de análisis
        @app.callback(
            Output('performance-analysis-config', 'data'),
            [Input('performance-symbol-selector', 'value'),
             Input('performance-period-selector', 'value'),
             Input('performance-benchmark-selector', 'value'),
             Input('risk-free-rate-input', 'value'),
             Input('performance-advanced-options', 'value')],
            [State('performance-analysis-config', 'data')]
        )
        def update_analysis_config(symbol, period, benchmark, risk_free_rate, advanced_options, current_config):
            """Actualiza configuración del análisis"""
            return {
                'symbol': symbol or 'all',
                'period': period or self.page_config['default_period'],
                'benchmark': benchmark or 'SPY',
                'risk_free_rate': (risk_free_rate or 2.0) / 100,  # Convertir a decimal
                'advanced_options': advanced_options or [],
                'last_update': datetime.now().isoformat()
            }
        
        # Callback principal para cargar datos de rendimiento
        @app.callback(
            Output('performance-data-store', 'data'),
            [Input('performance-analysis-config', 'data'),
             Input('performance-refresh-interval', 'n_intervals'),
             Input('performance-refresh-btn', 'n_clicks')]
        )
        def update_performance_data(analysis_config, n_intervals, refresh_clicks):
            """Actualiza datos de rendimiento"""
            try:
                performance_data = self._get_performance_data(analysis_config)
                benchmark_data = self._get_benchmark_data(analysis_config)
                
                self.update_page_stats()
                
                return {
                    'performance': performance_data,
                    'benchmark': benchmark_data,
                    'config': analysis_config,
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de rendimiento: {e}")
                return {}
        
        # Callback para métricas principales
        @app.callback(
            Output('key-metrics-cards', 'children'),
            [Input('performance-data-store', 'data')]
        )
        def update_key_metrics(performance_data):
            """Actualiza tarjetas de métricas principales"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return self.create_empty_state(
                        title="Cargando métricas...",
                        message="Calculando métricas de rendimiento",
                        icon="fas fa-calculator"
                    )
                
                return self._create_key_metrics_cards(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear métricas principales: {e}")
                return self.create_error_alert("Error al calcular métricas")
        
        # Callback para gráfico de evolución del rendimiento
        @app.callback(
            Output('performance-evolution-chart', 'figure'),
            [Input('performance-data-store', 'data')]
        )
        def update_performance_evolution(performance_data):
            """Actualiza gráfico de evolución del rendimiento"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return self._create_empty_chart("Cargando datos de rendimiento...")
                
                return self._create_performance_evolution_chart(
                    performance_data['performance'],
                    performance_data.get('benchmark', {})
                )
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de evolución: {e}")
                return self._create_empty_chart("Error al generar gráfico")
        
        # Callback para análisis de drawdown
        @app.callback(
            Output('drawdown-analysis-chart', 'figure'),
            [Input('performance-data-store', 'data')]
        )
        def update_drawdown_analysis(performance_data):
            """Actualiza análisis de drawdown"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return self._create_empty_chart("Cargando análisis de drawdown...")
                
                return self._create_drawdown_chart(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de drawdown: {e}")
                return self._create_empty_chart("Error en análisis de drawdown")
        
        # Callback para métricas de riesgo
        @app.callback(
            Output('risk-metrics-container', 'children'),
            [Input('performance-data-store', 'data')]
        )
        def update_risk_metrics(performance_data):
            """Actualiza métricas de riesgo"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return html.P("Cargando métricas de riesgo...", className="text-muted")
                
                return self._create_risk_metrics_table(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear métricas de riesgo: {e}")
                return self.create_error_alert("Error al calcular métricas de riesgo")
        
        # Callback para métricas de trading
        @app.callback(
            Output('trading-metrics-container', 'children'),
            [Input('performance-data-store', 'data')]
        )
        def update_trading_metrics(performance_data):
            """Actualiza métricas de trading"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return html.P("Cargando métricas de trading...", className="text-muted")
                
                return self._create_trading_metrics_table(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear métricas de trading: {e}")
                return self.create_error_alert("Error al calcular métricas de trading")
        
        # Callback para comparación con benchmarks
        @app.callback(
            Output('benchmark-comparison-chart', 'figure'),
            [Input('performance-data-store', 'data')]
        )
        def update_benchmark_comparison(performance_data):
            """Actualiza comparación con benchmarks"""
            try:
                if not performance_data:
                    return self._create_empty_chart("Cargando comparación...")
                
                return self._create_benchmark_comparison_chart(
                    performance_data.get('performance', {}),
                    performance_data.get('benchmark', {}),
                    performance_data.get('config', {})
                )
                
            except Exception as e:
                logger.error(f"Error al crear comparación de benchmarks: {e}")
                return self._create_empty_chart("Error en comparación")
        
        # Callback para análisis de atribución
        @app.callback(
            Output('attribution-analysis-chart', 'figure'),
            [Input('performance-data-store', 'data')]
        )
        def update_attribution_analysis(performance_data):
            """Actualiza análisis de atribución"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return self._create_empty_chart("Cargando análisis de atribución...")
                
                return self._create_attribution_chart(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear análisis de atribución: {e}")
                return self._create_empty_chart("Error en atribución")
        
        # Callback para distribución de retornos
        @app.callback(
            Output('returns-distribution-chart', 'figure'),
            [Input('performance-data-store', 'data')]
        )
        def update_returns_distribution(performance_data):
            """Actualiza distribución de retornos"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return self._create_empty_chart("Cargando distribución...")
                
                return self._create_returns_distribution_chart(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al crear distribución de retornos: {e}")
                return self._create_empty_chart("Error en distribución")
        
        # Callback para Kelly Criterion
        @app.callback(
            Output('kelly-criterion-results', 'children'),
            [Input('performance-data-store', 'data')]
        )
        def update_kelly_criterion(performance_data):
            """Actualiza resultados del Kelly Criterion"""
            try:
                if not performance_data or not performance_data.get('performance'):
                    return html.P("Calculando Kelly Criterion...", className="text-muted")
                
                return self._create_kelly_criterion_results(performance_data['performance'])
                
            except Exception as e:
                logger.error(f"Error al calcular Kelly Criterion: {e}")
                return html.P("Error en cálculo de Kelly", className="text-danger")
        
        # Callback para optimización de portfolio
        @app.callback(
            Output('portfolio-optimization-results', 'children'),
            [Input('performance-data-store', 'data')]
        )
        def update_portfolio_optimization(performance_data):
            """Actualiza optimización de portfolio"""
            try:
                if not performance_data:
                    return html.P("Optimizando portfolio...", className="text-muted")
                
                return self._create_portfolio_optimization_results(performance_data)
                
            except Exception as e:
                logger.error(f"Error en optimización de portfolio: {e}")
                return html.P("Error en optimización", className="text-danger")
        
        # Callback para exportar reportes
        @app.callback(
            Output('performance-export-btn', 'children'),
            [Input('performance-export-btn', 'n_clicks'),
             State('performance-data-store', 'data')],
            prevent_initial_call=True
        )
        def export_performance_report(n_clicks, performance_data):
            """Exporta reporte de rendimiento"""
            if n_clicks and performance_data:
                try:
                    # Implementar exportación
                    self.log_page_action("export_performance_report", {
                        "format": "pdf",
                        "period": performance_data.get('config', {}).get('period', 'unknown')
                    })
                    return [
                        html.I(className="fas fa-check me-1"),
                        "Exportado"
                    ]
                except Exception as e:
                    logger.error(f"Error al exportar: {e}")
            
            return [
                html.I(className="fas fa-download me-1"),
                "Exportar"
            ]
        
        logger.info("Callbacks de PerformancePage registrados")
    
    def _get_performance_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene datos de rendimiento según configuración"""
        try:
            if self.performance_tracker:
                symbol = config.get('symbol', 'all')
                
                if symbol == 'all':
                    # Portfolio completo
                    metrics = self.performance_tracker.get_portfolio_summary()
                    return self._format_portfolio_metrics(metrics)
                else:
                    # Símbolo específico
                    metrics = self.performance_tracker.get_performance_metrics(symbol)
                    return self._format_symbol_metrics(metrics)
            else:
                # Generar datos de muestra
                return self._generate_sample_performance_data(config)
                
        except Exception as e:
            logger.error(f"Error al obtener datos de rendimiento: {e}")
            return {}
    
    def _generate_sample_performance_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Genera datos de rendimiento de muestra"""
        # Período de análisis
        period = config.get('period', '3M')
        days = self.analysis_periods.get(period, {}).get('days', 90)
        
        if not days:  # ALL o YTD
            days = 365
        
        # Generar serie temporal de retornos
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), end=datetime.now(), freq='D')
        
        # Retornos diarios con tendencia positiva
        daily_returns = np.random.normal(0.0008, 0.015, len(dates))  # 0.08% promedio, 1.5% volatilidad
        
        # Añadir algo de momentum y reversión a la media
        for i in range(1, len(daily_returns)):
            daily_returns[i] += 0.1 * daily_returns[i-1] + np.random.normal(0, 0.001)
        
        # Calcular retornos cumulativos
        cumulative_returns = np.cumprod(1 + daily_returns) - 1
        
        # Calcular drawdowns
        running_max = np.maximum.accumulate(cumulative_returns + 1)
        drawdowns = (running_max - (cumulative_returns + 1)) / running_max