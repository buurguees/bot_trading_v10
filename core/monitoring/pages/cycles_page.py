# Ruta: core/monitoring/pages/cycles_page.py
"""
monitoring/pages/cycles_page.py
Página de Análisis de Ciclos - Trading Bot v10

Esta página proporciona un análisis detallado de los ciclos de trading:
- Tabla completa del Top 20+ ciclos con métricas avanzadas
- Análisis comparativo de rendimiento por ciclos
- Visualizaciones de distribución de métricas
- Filtros por símbolo, período y métricas
- Análisis de patrones y tendencias
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

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

class CyclesPage(BasePage):
    """
    Página de análisis detallado de ciclos del Trading Bot v10
    
    Proporciona análisis avanzados de los ciclos de trading,
    métricas comparativas y visualizaciones de rendimiento.
    """
    
    def __init__(self, data_provider=None, performance_tracker=None):
        """
        Inicializa la página de análisis de ciclos
        
        Args:
            data_provider: Proveedor de datos centralizado
            performance_tracker: Tracker de rendimiento
        """
        super().__init__(data_provider=data_provider, performance_tracker=performance_tracker)
        
        # Configuración específica de la página Cycles
        self.page_config.update({
            'title': 'Análisis de Ciclos',
            'update_interval': 30000,  # 30 segundos
            'auto_refresh': True,
            'max_cycles_display': 50,
            'default_sort_metric': 'pnl_percentage',
            'chart_height': 450,
            'enable_cycle_comparison': True,
            'show_statistical_analysis': True
        })
        
        # Métricas disponibles para análisis
        self.cycle_metrics = {
            'pnl_percentage': {
                'name': 'PnL Porcentual',
                'format': 'percentage',
                'description': 'Rendimiento porcentual del ciclo'
            },
            'pnl': {
                'name': 'PnL Absoluto',
                'format': 'currency',
                'description': 'Ganancia/pérdida en dólares'
            },
            'sharpe_ratio': {
                'name': 'Sharpe Ratio',
                'format': 'decimal',
                'description': 'Rendimiento ajustado por riesgo'
            },
            'win_rate': {
                'name': 'Win Rate',
                'format': 'percentage',
                'description': 'Porcentaje de trades ganadores'
            },
            'avg_daily_pnl': {
                'name': 'PnL Diario Promedio',
                'format': 'currency',
                'description': 'Ganancia promedio por día'
            },
            'max_drawdown': {
                'name': 'Máximo Drawdown',
                'format': 'percentage',
                'description': 'Máxima pérdida desde un pico'
            },
            'total_trades': {
                'name': 'Total de Trades',
                'format': 'number',
                'description': 'Número total de operaciones'
            },
            'duration_days': {
                'name': 'Duración (días)',
                'format': 'number',
                'description': 'Duración del ciclo en días'
            }
        }
        
        # Filtros disponibles
        self.filter_options = {
            'period': {
                'all': 'Todos los períodos',
                '1y': 'Último año',
                '6m': 'Últimos 6 meses',
                '3m': 'Últimos 3 meses',
                '1m': 'Último mes'
            },
            'status': {
                'all': 'Todos los estados',
                'completed': 'Completados',
                'active': 'Activos',
                'stopped': 'Detenidos'
            },
            'performance': {
                'all': 'Todos',
                'top_10': 'Top 10%',
                'top_25': 'Top 25%',
                'profitable': 'Solo rentables',
                'losses': 'Solo pérdidas'
            }
        }
        
        logger.info("CyclesPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de ciclos
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Análisis de Ciclos",
                    subtitle="Análisis detallado del rendimiento por ciclos de trading",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Controles y filtros
                self._create_filters_section(),
                
                # Resumen estadístico
                self._create_statistical_summary_section(),
                
                # Visualizaciones principales
                dbc.Row([
                    dbc.Col([
                        self._create_cycles_distribution_chart_section()
                    ], width=6),
                    dbc.Col([
                        self._create_performance_timeline_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Tabla detallada de ciclos
                self._create_detailed_cycles_table_section(),
                
                # Análisis comparativo
                self._create_comparative_analysis_section(),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("cycles-refresh-interval"),
                dcc.Store(id='cycles-data-store'),
                dcc.Store(id='filtered-cycles-store'),
                dcc.Store(id='cycles-filters-store', data={
                    'symbol': 'all',
                    'period': 'all',
                    'status': 'all',
                    'performance': 'all',
                    'sort_by': self.page_config['default_sort_metric']
                }),
                
            ], fluid=True, className="cycles-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de CyclesPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de ciclos: {e}")
            ])
    
    def _create_filters_section(self) -> dbc.Row:
        """Crea la sección de filtros y controles"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Filtros y Controles", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            # Filtro por símbolo
                            dbc.Col([
                                html.Label("Símbolo:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="cycles-symbol-filter",
                                    placeholder="Todos los símbolos",
                                    className="symbol-filter-dropdown"
                                )
                            ], width=12, md=2),
                            
                            # Filtro por período
                            dbc.Col([
                                html.Label("Período:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="cycles-period-filter",
                                    options=[
                                        {'label': label, 'value': value}
                                        for value, label in self.filter_options['period'].items()
                                    ],
                                    value='all',
                                    placeholder="Período"
                                )
                            ], width=12, md=2),
                            
                            # Filtro por estado
                            dbc.Col([
                                html.Label("Estado:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="cycles-status-filter",
                                    options=[
                                        {'label': label, 'value': value}
                                        for value, label in self.filter_options['status'].items()
                                    ],
                                    value='all',
                                    placeholder="Estado"
                                )
                            ], width=12, md=2),
                            
                            # Filtro por rendimiento
                            dbc.Col([
                                html.Label("Rendimiento:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="cycles-performance-filter",
                                    options=[
                                        {'label': label, 'value': value}
                                        for value, label in self.filter_options['performance'].items()
                                    ],
                                    value='all',
                                    placeholder="Rendimiento"
                                )
                            ], width=12, md=2),
                            
                            # Ordenar por
                            dbc.Col([
                                html.Label("Ordenar por:", className="form-label mb-1"),
                                dcc.Dropdown(
                                    id="cycles-sort-by",
                                    options=[
                                        {'label': metric['name'], 'value': key}
                                        for key, metric in self.cycle_metrics.items()
                                    ],
                                    value=self.page_config['default_sort_metric'],
                                    placeholder="Métrica"
                                )
                            ], width=12, md=2),
                            
                            # Botones de acción
                            dbc.Col([
                                html.Label("Acciones:", className="form-label mb-1"),
                                dbc.ButtonGroup([
                                    dbc.Button("Limpiar", id="clear-filters-btn", 
                                              color="outline-secondary", size="sm"),
                                    dbc.Button("Analizar", id="analyze-cycles-btn", 
                                              color="primary", size="sm")
                                ], className="w-100")
                            ], width=12, md=2)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_statistical_summary_section(self) -> dbc.Row:
        """Crea la sección de resumen estadístico"""
        return dbc.Row([
            dbc.Col([
                html.H5("Resumen Estadístico", className="section-title mb-3"),
                self.create_loading_component(
                    "statistical-summary",
                    html.Div(id="statistical-summary-cards"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_cycles_distribution_chart_section(self) -> dbc.Card:
        """Crea la sección del gráfico de distribución de ciclos"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Distribución de Rendimiento", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "cycles-distribution",
                    dcc.Graph(
                        id="cycles-distribution-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_performance_timeline_section(self) -> dbc.Card:
        """Crea la sección del timeline de rendimiento"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Timeline de Rendimiento", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "performance-timeline",
                    dcc.Graph(
                        id="performance-timeline-chart",
                        config=self.get_default_chart_config(),
                        style={'height': f"{self.page_config['chart_height']}px"}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_detailed_cycles_table_section(self) -> dbc.Row:
        """Crea la sección de tabla detallada de ciclos"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Tabla Detallada de Ciclos", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                html.Div(id="cycles-count-info", className="text-muted small")
                            ], width="auto", className="ms-auto")
                        ])
                    ]),
                    dbc.CardBody([
                        self.create_loading_component(
                            "detailed-cycles-table",
                            html.Div(id="detailed-cycles-table-container"),
                            loading_type="default"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_comparative_analysis_section(self) -> dbc.Row:
        """Crea la sección de análisis comparativo"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Análisis Comparativo", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                self.create_loading_component(
                                    "correlation-matrix",
                                    dcc.Graph(
                                        id="correlation-matrix-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=6),
                            dbc.Col([
                                self.create_loading_component(
                                    "performance-scatter",
                                    dcc.Graph(
                                        id="performance-scatter-chart",
                                        config=self.get_default_chart_config(),
                                        style={'height': '400px'}
                                    ),
                                    loading_type="default"
                                )
                            ], width=6)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de ciclos
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para inicializar filtros
        @app.callback(
            Output('cycles-symbol-filter', 'options'),
            [Input('cycles-refresh-interval', 'n_intervals')]
        )
        def initialize_symbol_filter(n_intervals):
            """Inicializa opciones del filtro de símbolos"""
            try:
                options = [{'label': 'Todos los símbolos', 'value': 'all'}]
                
                if self.data_provider:
                    symbols = self.data_provider.get_configured_symbols()
                    options.extend([{'label': symbol, 'value': symbol} for symbol in symbols])
                else:
                    # Símbolos de ejemplo
                    example_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
                    options.extend([{'label': symbol, 'value': symbol} for symbol in example_symbols])
                
                return options
                
            except Exception as e:
                logger.error(f"Error al inicializar filtro de símbolos: {e}")
                return [{'label': 'Error al cargar símbolos', 'value': 'all'}]
        
        # Callback para actualizar filtros
        @app.callback(
            Output('cycles-filters-store', 'data'),
            [Input('cycles-symbol-filter', 'value'),
             Input('cycles-period-filter', 'value'),
             Input('cycles-status-filter', 'value'),
             Input('cycles-performance-filter', 'value'),
             Input('cycles-sort-by', 'value'),
             Input('clear-filters-btn', 'n_clicks')],
            [State('cycles-filters-store', 'data')]
        )
        def update_filters(symbol, period, status, performance, sort_by, clear_clicks, current_filters):
            """Actualiza los filtros aplicados"""
            ctx_triggered = dash.callback_context.triggered[0]['prop_id']
            
            if 'clear-filters-btn' in ctx_triggered:
                return {
                    'symbol': 'all',
                    'period': 'all',
                    'status': 'all',
                    'performance': 'all',
                    'sort_by': self.page_config['default_sort_metric']
                }
            
            return {
                'symbol': symbol or 'all',
                'period': period or 'all',
                'status': status or 'all',
                'performance': performance or 'all',
                'sort_by': sort_by or self.page_config['default_sort_metric']
            }
        
        # Callback principal para cargar datos de ciclos
        @app.callback(
            Output('cycles-data-store', 'data'),
            [Input('cycles-refresh-interval', 'n_intervals'),
             Input('cycles-refresh-btn', 'n_clicks'),
             Input('analyze-cycles-btn', 'n_clicks')]
        )
        def update_cycles_data(n_intervals, refresh_clicks, analyze_clicks):
            """Actualiza datos de ciclos"""
            try:
                cycles_data = self._get_cycles_data()
                statistical_summary = self._calculate_statistical_summary(cycles_data)
                
                self.update_page_stats()
                
                return {
                    'cycles': cycles_data,
                    'statistical_summary': statistical_summary,
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de ciclos: {e}")
                return {}
        
        # Callback para filtrar datos
        @app.callback(
            Output('filtered-cycles-store', 'data'),
            [Input('cycles-data-store', 'data'),
             Input('cycles-filters-store', 'data')]
        )
        def filter_cycles_data(cycles_data, filters):
            """Aplica filtros a los datos de ciclos"""
            try:
                if not cycles_data or not cycles_data.get('cycles'):
                    return {}
                
                filtered_cycles = self._apply_filters(cycles_data['cycles'], filters)
                
                return {
                    'cycles': filtered_cycles,
                    'filters_applied': filters,
                    'total_count': len(cycles_data['cycles']),
                    'filtered_count': len(filtered_cycles)
                }
                
            except Exception as e:
                logger.error(f"Error al filtrar ciclos: {e}")
                return {}
        
        # Callback para resumen estadístico
        @app.callback(
            Output('statistical-summary-cards', 'children'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_statistical_summary(filtered_data):
            """Actualiza tarjetas de resumen estadístico"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self.create_empty_state(
                        title="No hay datos disponibles",
                        message="No se encontraron ciclos que coincidan con los filtros",
                        icon="fas fa-filter"
                    )
                
                return self._create_statistical_summary_cards(filtered_data['cycles'])
                
            except Exception as e:
                logger.error(f"Error al crear resumen estadístico: {e}")
                return self.create_error_alert("Error al calcular estadísticas")
        
        # Callback para gráfico de distribución
        @app.callback(
            Output('cycles-distribution-chart', 'figure'),
            [Input('filtered-cycles-store', 'data'),
             Input('cycles-sort-by', 'value')]
        )
        def update_distribution_chart(filtered_data, sort_metric):
            """Actualiza gráfico de distribución de rendimiento"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self._create_empty_chart("No hay datos para mostrar")
                
                return self._create_distribution_chart(filtered_data['cycles'], sort_metric)
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de distribución: {e}")
                return self._create_empty_chart("Error al generar gráfico")
        
        # Callback para timeline de rendimiento
        @app.callback(
            Output('performance-timeline-chart', 'figure'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_timeline_chart(filtered_data):
            """Actualiza timeline de rendimiento"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self._create_empty_chart("No hay datos para mostrar")
                
                return self._create_performance_timeline_chart(filtered_data['cycles'])
                
            except Exception as e:
                logger.error(f"Error al crear timeline: {e}")
                return self._create_empty_chart("Error al generar timeline")
        
        # Callback para tabla detallada
        @app.callback(
            Output('detailed-cycles-table-container', 'children'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_detailed_table(filtered_data):
            """Actualiza tabla detallada de ciclos"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self.create_empty_state(
                        title="No hay ciclos para mostrar",
                        message="Ajuste los filtros para ver más resultados",
                        icon="fas fa-table"
                    )
                
                return self._create_detailed_cycles_table(filtered_data['cycles'])
                
            except Exception as e:
                logger.error(f"Error al crear tabla detallada: {e}")
                return self.create_error_alert("Error al cargar tabla de ciclos")
        
        # Callback para información de conteo
        @app.callback(
            Output('cycles-count-info', 'children'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_count_info(filtered_data):
            """Actualiza información de conteo de ciclos"""
            try:
                if not filtered_data:
                    return "Cargando..."
                
                total = filtered_data.get('total_count', 0)
                filtered = filtered_data.get('filtered_count', 0)
                
                return f"Mostrando {filtered:,} de {total:,} ciclos"
                
            except Exception as e:
                logger.error(f"Error al actualizar conteo: {e}")
                return "Error en conteo"
        
        # Callback para matriz de correlación
        @app.callback(
            Output('correlation-matrix-chart', 'figure'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_correlation_matrix(filtered_data):
            """Actualiza matriz de correlación"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self._create_empty_chart("No hay datos suficientes")
                
                return self._create_correlation_matrix(filtered_data['cycles'])
                
            except Exception as e:
                logger.error(f"Error al crear matriz de correlación: {e}")
                return self._create_empty_chart("Error en correlación")
        
        # Callback para scatter plot de rendimiento
        @app.callback(
            Output('performance-scatter-chart', 'figure'),
            [Input('filtered-cycles-store', 'data')]
        )
        def update_scatter_plot(filtered_data):
            """Actualiza scatter plot de rendimiento vs riesgo"""
            try:
                if not filtered_data or not filtered_data.get('cycles'):
                    return self._create_empty_chart("No hay datos suficientes")
                
                return self._create_performance_scatter(filtered_data['cycles'])
                
            except Exception as e:
                logger.error(f"Error al crear scatter plot: {e}")
                return self._create_empty_chart("Error en scatter plot")
        
        logger.info("Callbacks de CyclesPage registrados")
    
    def _get_cycles_data(self) -> List[Dict[str, Any]]:
        """Obtiene datos de ciclos"""
        try:
            if self.data_provider:
                cycles = self.data_provider.get_top_cycles(self.page_config['max_cycles_display'])
                return [cycle.__dict__ if hasattr(cycle, '__dict__') else cycle for cycle in cycles]
            else:
                # Generar datos de muestra
                return self._generate_sample_cycles_data(self.page_config['max_cycles_display'])
                
        except Exception as e:
            logger.error(f"Error al obtener datos de ciclos: {e}")
            return []
    
    def _generate_sample_cycles_data(self, count: int) -> List[Dict[str, Any]]:
        """Genera datos de muestra para ciclos"""
        cycles = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT']
        
        for i in range(count):
            start_date = datetime.now() - timedelta(days=np.random.randint(1, 365))
            duration = np.random.randint(5, 90)
            end_date = start_date + timedelta(days=duration)
            
            # Generar métricas realistas
            pnl_pct = np.random.normal(12, 25)  # 12% promedio, 25% desviación
            start_balance = np.random.uniform(800, 1200)
            pnl = start_balance * (pnl_pct / 100)
            end_balance = start_balance + pnl
            
            # Otras métricas
            total_trades = np.random.randint(5, 60)
            win_rate = np.random.uniform(35, 85)
            sharpe_ratio = np.random.uniform(-0.5, 4.0)
            max_drawdown = np.random.uniform(1, 25)
            
            cycles.append({
                'cycle_id': f'cycle_{i+1:03d}',
                'symbol': np.random.choice(symbols),
                'start_date': start_date,
                'end_date': end_date,
                'start_balance': start_balance,
                'end_balance': end_balance,
                'pnl': pnl,
                'pnl_percentage': pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_daily_pnl': pnl / duration,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'duration_days': duration,
                'status': np.random.choice(['completed', 'active', 'stopped'], p=[0.8, 0.15, 0.05]),
                'efficiency_score': (win_rate / 100) * (1 - max_drawdown / 100) * max(sharpe_ratio, 0),
                'risk_adjusted_return': pnl_pct / max(max_drawdown, 1),
                'trades_per_day': total_trades / duration,
                'profit_factor': np.random.uniform(0.5, 3.5)
            })
        
        return cycles
    
    def _calculate_statistical_summary(self, cycles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula resumen estadístico de los ciclos"""
        if not cycles_data:
            return {}
        
        # Convertir a DataFrame para cálculos
        df = pd.DataFrame(cycles_data)
        
        summary = {}
        for metric_key, metric_info in self.cycle_metrics.items():
            if metric_key in df.columns:
                values = df[metric_key].dropna()
                if len(values) > 0:
                    summary[metric_key] = {
                        'mean': float(values.mean()),
                        'median': float(values.median()),
                        'std': float(values.std()),
                        'min': float(values.min()),
                        'max': float(values.max()),
                        'q25': float(values.quantile(0.25)),
                        'q75': float(values.quantile(0.75))
                    }
        
        return summary
    
    def _apply_filters(self, cycles_data: List[Dict[str, Any]], 
                      filters: Dict[str, str]) -> List[Dict[str, Any]]:
        """Aplica filtros a los datos de ciclos"""
        filtered_cycles = cycles_data.copy()
        
        # Filtro por símbolo
        if filters.get('symbol') and filters['symbol'] != 'all':
            filtered_cycles = [c for c in filtered_cycles if c.get('symbol') == filters['symbol']]
        
        # Filtro por período
        if filters.get('period') and filters['period'] != 'all':
            cutoff_date = self._get_period_cutoff_date(filters['period'])
            filtered_cycles = [c for c in filtered_cycles 
                             if c.get('start_date', datetime.now()) >= cutoff_date]
        
        # Filtro por estado
        if filters.get('status') and filters['status'] != 'all':
            filtered_cycles = [c for c in filtered_cycles if c.get('status') == filters['status']]
        
        # Filtro por rendimiento
        if filters.get('performance') and filters['performance'] != 'all':
            filtered_cycles = self._apply_performance_filter(filtered_cycles, filters['performance'])
        
        # Ordenar
        if filters.get('sort_by'):
            sort_key = filters['sort_by']
            reverse = True  # Por defecto descendente
            if sort_key in ['max_drawdown', 'duration_days']:
                reverse = False  # Estos mejor ascendente
            
            filtered_cycles.sort(
                key=lambda x: x.get(sort_key, 0) if x.get(sort_key) is not None else 0,
                reverse=reverse
            )
        
        return filtered_cycles
    
    def _get_period_cutoff_date(self, period: str) -> datetime:
        """Obtiene fecha de corte según el período"""
        now = datetime.now()
        
        if period == '1y':
            return now - timedelta(days=365)
        elif period == '6m':
            return now - timedelta(days=180)
        elif period == '3m':
            return now - timedelta(days=90)
        elif period == '1m':
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=365*10)  # Muy atrás para incluir todo
    
    def _apply_performance_filter(self, cycles: List[Dict[str, Any]], 
                                 performance_filter: str) -> List[Dict[str, Any]]:
        """Aplica filtro de rendimiento"""
        if performance_filter == 'profitable':
            return [c for c in cycles if c.get('pnl_percentage', 0) > 0]
        elif performance_filter == 'losses':
            return [c for c in cycles if c.get('pnl_percentage', 0) < 0]
        elif performance_filter in ['top_10', 'top_25']:
            # Ordenar por PnL porcentual y tomar top %
            sorted_cycles = sorted(cycles, key=lambda x: x.get('pnl_percentage', 0), reverse=True)
            pct = 0.1 if performance_filter == 'top_10' else 0.25
            count = max(1, int(len(sorted_cycles) * pct))
            return sorted_cycles[:count]
        
        return cycles
    
    def _create_statistical_summary_cards(self, cycles_data: List[Dict[str, Any]]) -> dbc.Row:
        """Crea tarjetas de resumen estadístico"""
        if not cycles_data:
            return dbc.Row([])
        
        df = pd.DataFrame(cycles_data)
        cards = []
        
        # Total de ciclos
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Total de Ciclos",
                value=len(df),
                subtitle="Ciclos analizados",
                icon="fas fa-sync-alt",
                color="primary"
            )
        ], width=12, md=6, lg=2))
        
        # PnL promedio
        avg_pnl = df['pnl_percentage'].mean() if 'pnl_percentage' in df else 0
        cards.append(dbc.Col([
            self.create_metric_card(
                title="PnL Promedio",
                value=f"{avg_pnl:.1f}%",
                subtitle="Rendimiento medio",
                icon="fas fa-chart-line",
                color="success" if avg_pnl > 0 else "danger"
            )
        ], width=12, md=6, lg=2))
        
        # Win Rate promedio
        avg_win_rate = df['win_rate'].mean() if 'win_rate' in df else 0
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Win Rate Promedio",
                value=f"{avg_win_rate:.1f}%",
                subtitle="Tasa de éxito",
                icon="fas fa-target",
                color="info"
            )
        ], width=12, md=6, lg=2))
        
        # Sharpe Ratio promedio
        avg_sharpe = df['sharpe_ratio'].mean() if 'sharpe_ratio' in df else 0
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Sharpe Promedio",
                value=f"{avg_sharpe:.2f}",
                subtitle="Ratio riesgo-retorno",
                icon="fas fa-balance-scale",
                color="warning"
            )
        ], width=12, md=6, lg=2))
        
        # Mejor ciclo
        if 'pnl_percentage' in df and len(df) > 0:
            best_cycle = df.loc[df['pnl_percentage'].idxmax()]
            cards.append(dbc.Col([
                self.create_metric_card(
                    title="Mejor Ciclo",
                    value=f"{best_cycle['pnl_percentage']:.1f}%",
                    subtitle=best_cycle.get('symbol', 'N/A'),
                    icon="fas fa-trophy",
                    color="success"
                )
            ], width=12, md=6, lg=2))
        
        # Ciclos rentables
        profitable_count = len(df[df['pnl_percentage'] > 0]) if 'pnl_percentage' in df else 0
        profitable_pct = (profitable_count / len(df)) * 100 if len(df) > 0 else 0
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Ciclos Rentables",
                value=f"{profitable_count}",
                subtitle=f"{profitable_pct:.1f}% del total",
                icon="fas fa-chart-pie",
                color="success"
            )
        ], width=12, md=6, lg=2))
        
        return dbc.Row(cards)
    
    def _create_distribution_chart(self, cycles_data: List[Dict[str, Any]], 
                                  metric: str) -> go.Figure:
        """Crea gráfico de distribución de métricas"""
        try:
            df = pd.DataFrame(cycles_data)
            
            if metric not in df.columns:
                return self._create_empty_chart(f"Métrica {metric} no disponible")
            
            values = df[metric].dropna()
            if len(values) == 0:
                return self._create_empty_chart("No hay datos para mostrar")
            
            # Crear histograma con curva de densidad
            fig = go.Figure()
            
            # Histograma
            fig.add_trace(go.Histogram(
                x=values,
                nbinsx=20,
                name='Distribución',
                opacity=0.7,
                marker_color='rgba(0, 123, 255, 0.7)'
            ))
            
            # Línea de media
            mean_val = values.mean()
            fig.add_vline(
                x=mean_val,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Media: {mean_val:.2f}"
            )
            
            # Línea de mediana
            median_val = values.median()
            fig.add_vline(
                x=median_val,
                line_dash="dot",
                line_color="green",
                annotation_text=f"Mediana: {median_val:.2f}"
            )
            
            # Configuración
            metric_info = self.cycle_metrics.get(metric, {})
            title = f"Distribución de {metric_info.get('name', metric)}"
            
            fig.update_layout(
                title=title,
                xaxis_title=metric_info.get('name', metric),
                yaxis_title='Frecuencia',
                height=self.page_config['chart_height'],
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de distribución: {e}")
            return self._create_empty_chart("Error al generar distribución")
    
    def _create_performance_timeline_chart(self, cycles_data: List[Dict[str, Any]]) -> go.Figure:
        """Crea timeline de rendimiento de ciclos"""
        try:
            df = pd.DataFrame(cycles_data)
            
            if df.empty or 'start_date' not in df:
                return self._create_empty_chart("No hay datos de fechas")
            
            # Ordenar por fecha de inicio
            df['start_date'] = pd.to_datetime(df['start_date'])
            df = df.sort_values('start_date')
            
            # Crear gráfico de timeline
            fig = go.Figure()
            
            # Scatter plot con colores según rendimiento
            colors = ['red' if pnl < 0 else 'green' for pnl in df['pnl_percentage']]
            
            fig.add_trace(go.Scatter(
                x=df['start_date'],
                y=df['pnl_percentage'],
                mode='markers+lines',
                marker=dict(
                    color=df['pnl_percentage'],
                    colorscale='RdYlGn',
                    size=df['duration_days'] / 2,  # Tamaño según duración
                    showscale=True,
                    colorbar=dict(title="PnL %")
                ),
                text=[f"Ciclo: {row['cycle_id']}<br>"
                      f"Símbolo: {row['symbol']}<br>"
                      f"PnL: {row['pnl_percentage']:.2f}%<br>"
                      f"Duración: {row['duration_days']}d<br>"
                      f"Win Rate: {row['win_rate']:.1f}%"
                      for _, row in df.iterrows()],
                hovertemplate='%{text}<extra></extra>',
                name='Ciclos'
            ))
            
            # Línea de tendencia
            if len(df) > 1:
                z = np.polyfit(df.index, df['pnl_percentage'], 1)
                trend_line = np.poly1d(z)
                
                fig.add_trace(go.Scatter(
                    x=df['start_date'],
                    y=trend_line(df.index),
                    mode='lines',
                    name='Tendencia',
                    line=dict(color='blue', dash='dash', width=2)
                ))
            
            # Configuración
            fig.update_layout(
                title="Timeline de Rendimiento de Ciclos",
                xaxis_title="Fecha de Inicio",
                yaxis_title="PnL Porcentual (%)",
                height=self.page_config['chart_height'],
                hovermode='closest',
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            # Línea en y=0 para referencia
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear timeline: {e}")
            return self._create_empty_chart("Error al generar timeline")
    
    def _create_detailed_cycles_table(self, cycles_data: List[Dict[str, Any]]) -> html.Div:
        """Crea tabla detallada de ciclos"""
        try:
            # Preparar datos para la tabla
            table_data = []
            for cycle in cycles_data:
                # Formatear fechas
                start_date = cycle.get('start_date')
                end_date = cycle.get('end_date')
                
                if isinstance(start_date, datetime):
                    start_str = start_date.strftime('%Y-%m-%d')
                else:
                    start_str = str(start_date)[:10] if start_date else 'N/A'
                
                if isinstance(end_date, datetime):
                    end_str = end_date.strftime('%Y-%m-%d')
                else:
                    end_str = str(end_date)[:10] if end_date else 'N/A'
                
                table_data.append({
                    'cycle_id': cycle.get('cycle_id', 'N/A'),
                    'symbol': cycle.get('symbol', 'N/A'),
                    'start_date': start_str,
                    'end_date': end_str,
                    'duration_days': f"{cycle.get('duration_days', 0)}d",
                    'pnl_percentage': f"{cycle.get('pnl_percentage', 0):.2f}%",
                    'pnl': f"${cycle.get('pnl', 0):,.2f}",
                    'start_balance': f"${cycle.get('start_balance', 0):,.2f}",
                    'end_balance': f"${cycle.get('end_balance', 0):,.2f}",
                    'total_trades': cycle.get('total_trades', 0),
                    'win_rate': f"{cycle.get('win_rate', 0):.1f}%",
                    'avg_daily_pnl': f"${cycle.get('avg_daily_pnl', 0):.2f}",
                    'sharpe_ratio': f"{cycle.get('sharpe_ratio', 0):.2f}",
                    'max_drawdown': f"{cycle.get('max_drawdown', 0):.1f}%",
                    'leverage_min': cycle.get('leverage_min', 1.0),
                    'leverage_max': cycle.get('leverage_max', 1.0),
                    'status': cycle.get('status', 'unknown').title(),
                    'efficiency_score': f"{cycle.get('efficiency_score', 0):.3f}",
                    'risk_adjusted_return': f"{cycle.get('risk_adjusted_return', 0):.2f}",
                    'trades_per_day': f"{cycle.get('trades_per_day', 0):.1f}",
                    'profit_factor': f"{cycle.get('profit_factor', 0):.2f}"
                })
            
            # Configuración de columnas
            columns = [
                {'name': 'ID Ciclo', 'id': 'cycle_id', 'type': 'text'},
                {'name': 'Símbolo', 'id': 'symbol', 'type': 'text'},
                {'name': 'Inicio', 'id': 'start_date', 'type': 'text'},
                {'name': 'Fin', 'id': 'end_date', 'type': 'text'},
                {'name': 'Duración', 'id': 'duration_days', 'type': 'text'},
                {'name': 'PnL %', 'id': 'pnl_percentage', 'type': 'numeric'},
                {'name': 'PnL $', 'id': 'pnl', 'type': 'numeric'},
                {'name': 'Balance Inicial', 'id': 'start_balance', 'type': 'numeric'},
                {'name': 'Balance Final', 'id': 'end_balance', 'type': 'numeric'},
                {'name': 'Total Trades', 'id': 'total_trades', 'type': 'numeric'},
                {'name': 'Win Rate', 'id': 'win_rate', 'type': 'numeric'},
                {'name': 'PnL Diario', 'id': 'avg_daily_pnl', 'type': 'numeric'},
                {'name': 'Sharpe', 'id': 'sharpe_ratio', 'type': 'numeric'},
                {'name': 'Max DD', 'id': 'max_drawdown', 'type': 'numeric'},
                {'name': 'Leverage Min', 'id': 'leverage_min', 'type': 'numeric', 'format': {'specifier': '.1f'}},
                {'name': 'Leverage Max', 'id': 'leverage_max', 'type': 'numeric', 'format': {'specifier': '.1f'}},
                {'name': 'Estado', 'id': 'status', 'type': 'text'},
                {'name': 'Eficiencia', 'id': 'efficiency_score', 'type': 'numeric'},
                {'name': 'Riesgo Ajustado', 'id': 'risk_adjusted_return', 'type': 'numeric'},
                {'name': 'Trades/Día', 'id': 'trades_per_day', 'type': 'numeric'},
                {'name': 'Profit Factor', 'id': 'profit_factor', 'type': 'numeric'}
            ]
            
            return self.create_data_table(
                data=table_data,
                columns=columns,
                table_id="detailed-cycles-data-table",
                page_size=20,
                sortable=True
            )
            
        except Exception as e:
            logger.error(f"Error al crear tabla detallada: {e}")
            return self.create_error_alert("Error al procesar datos de la tabla")
    
    def _create_correlation_matrix(self, cycles_data: List[Dict[str, Any]]) -> go.Figure:
        """Crea matriz de correlación entre métricas"""
        try:
            df = pd.DataFrame(cycles_data)
            
            # Seleccionar columnas numéricas relevantes
            numeric_cols = ['pnl_percentage', 'win_rate', 'sharpe_ratio', 'max_drawdown',
                           'total_trades', 'avg_daily_pnl', 'duration_days']
            
            # Filtrar columnas que existen
            available_cols = [col for col in numeric_cols if col in df.columns]
            
            if len(available_cols) < 2:
                return self._create_empty_chart("Datos insuficientes para correlación")
            
            # Calcular matriz de correlación
            corr_matrix = df[available_cols].corr()
            
            # Crear heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.round(2).values,
                texttemplate='%{text}',
                textfont={'size': 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="Matriz de Correlación entre Métricas",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear matriz de correlación: {e}")
            return self._create_empty_chart("Error en matriz de correlación")
    
    def _create_performance_scatter(self, cycles_data: List[Dict[str, Any]]) -> go.Figure:
        """Crea scatter plot de rendimiento vs riesgo"""
        try:
            df = pd.DataFrame(cycles_data)
            
            if 'pnl_percentage' not in df or 'max_drawdown' not in df:
                return self._create_empty_chart("Datos insuficientes para scatter plot")
            
            # Crear scatter plot
            fig = go.Figure()
            
            # Colorear por símbolo si está disponible
            if 'symbol' in df:
                symbols = df['symbol'].unique()
                colors = px.colors.qualitative.Set1[:len(symbols)]
                
                for i, symbol in enumerate(symbols):
                    symbol_data = df[df['symbol'] == symbol]
                    
                    fig.add_trace(go.Scatter(
                        x=symbol_data['max_drawdown'],
                        y=symbol_data['pnl_percentage'],
                        mode='markers',
                        name=symbol,
                        marker=dict(
                            color=colors[i % len(colors)],
                            size=10,
                            opacity=0.7
                        ),
                        text=[f"Ciclo: {row['cycle_id']}<br>"
                              f"Win Rate: {row['win_rate']:.1f}%<br>"
                              f"Sharpe: {row['sharpe_ratio']:.2f}"
                              for _, row in symbol_data.iterrows()],
                        hovertemplate='%{text}<br>Riesgo: %{x:.1f}%<br>Retorno: %{y:.1f}%<extra></extra>'
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=df['max_drawdown'],
                    y=df['pnl_percentage'],
                    mode='markers',
                    marker=dict(size=10, opacity=0.7),
                    name='Ciclos'
                ))
            
            # Líneas de referencia
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_vline(x=10, line_dash="dash", line_color="orange", 
                         annotation_text="10% DD")
            
            # Configuración
            fig.update_layout(
                title="Rendimiento vs Riesgo (Max Drawdown)",
                xaxis_title="Máximo Drawdown (%)",
                yaxis_title="PnL Porcentual (%)",
                height=400,
                hovermode='closest',
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear scatter plot: {e}")
            return self._create_empty_chart("Error en scatter plot")
    
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