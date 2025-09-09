"""
monitoring/pages/home_page.py
Página Principal del Dashboard - Trading Bot v10

Esta es la página principal (HOME) del dashboard que muestra:
- Bloques de métricas por símbolo (auto-generados)
- Resumen general del portfolio
- Alertas y notificaciones importantes
- Accesos rápidos a otras secciones
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from monitoring.pages.base_page import BasePage

logger = logging.getLogger(__name__)

class HomePage(BasePage):
    """
    Página principal del dashboard del Trading Bot v10
    
    Muestra una vista general con métricas por símbolo, resumen del portfolio
    y accesos rápidos a funcionalidades principales.
    """
    
    def __init__(self, data_provider=None, performance_tracker=None):
        """
        Inicializa la página principal
        
        Args:
            data_provider: Proveedor de datos centralizado
            performance_tracker: Tracker de rendimiento
        """
        super().__init__(data_provider=data_provider, performance_tracker=performance_tracker)
        
        # Configuración específica de la página HOME
        self.page_config.update({
            'title': 'Dashboard Principal',
            'update_interval': 5000,  # 5 segundos
            'auto_refresh': True,
            'show_portfolio_summary': True,
            'show_quick_actions': True,
            'symbols_per_row': 3,  # Símbolos por fila en grid
            'max_symbols_display': 12  # Máximo símbolos a mostrar
        })
        
        logger.info("HomePage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página HOME
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Dashboard Principal",
                    subtitle="Vista general del Trading Bot v10",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Resumen del portfolio
                self._create_portfolio_summary_section(),
                
                # Grid de símbolos (auto-generado)
                self._create_symbols_grid_section(),
                
                # Sección de acciones rápidas y alertas
                dbc.Row([
                    dbc.Col([
                        self._create_quick_actions_section()
                    ], width=8),
                    dbc.Col([
                        self._create_alerts_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Gráfico de rendimiento general
                self._create_performance_chart_section(),
                
                # Componentes de actualización
                self.create_refresh_interval("home-refresh-interval"),
                
                # Stores para datos
                dcc.Store(id='home-data-store'),
                dcc.Store(id='home-symbols-store'),
                
            ], fluid=True, className="home-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de HomePage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página principal: {e}")
            ])
    
    def _create_portfolio_summary_section(self) -> dbc.Row:
        """Crea la sección de resumen del portfolio"""
        return dbc.Row([
            dbc.Col([
                html.H4("Resumen del Portfolio", className="section-title mb-3"),
                dbc.Row([
                    dbc.Col([
                        self.create_loading_component(
                            "portfolio-summary",
                            html.Div(id="portfolio-summary-cards"),
                            loading_type="default"
                        )
                    ], width=12)
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_symbols_grid_section(self) -> dbc.Row:
        """Crea la sección del grid de símbolos"""
        return dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("Métricas por Símbolo", className="section-title mb-3"),
                    html.P("Los bloques se generan automáticamente para cada símbolo configurado", 
                           className="text-muted mb-3"),
                ]),
                self.create_loading_component(
                    "symbols-grid",
                    html.Div(id="symbols-grid-container"),
                    loading_type="default"
                )
            ], width=12)
        ], className="mb-4")
    
    def _create_quick_actions_section(self) -> dbc.Card:
        """Crea la sección de acciones rápidas"""
        quick_actions = [
            {
                'title': 'Ver Gráficos',
                'description': 'Análisis técnico detallado',
                'icon': 'fas fa-chart-line',
                'href': '/charts',
                'color': 'primary'
            },
            {
                'title': 'Analizar Ciclos',
                'description': 'Top 20 mejores ciclos',
                'icon': 'fas fa-sync-alt',
                'href': '/cycles',
                'color': 'success'
            },
            {
                'title': 'Trading Live',
                'description': 'Monitoreo en tiempo real',
                'icon': 'fas fa-broadcast-tower',
                'href': '/live-trading',
                'color': 'warning'
            },
            {
                'title': 'Análisis de Riesgo',
                'description': 'Gestión de riesgo avanzada',
                'icon': 'fas fa-shield-alt',
                'href': '/risk-analysis',
                'color': 'danger'
            }
        ]
        
        action_buttons = []
        for action in quick_actions:
            action_buttons.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className=f"{action['icon']} fa-2x text-{action['color']} mb-2"),
                                html.H6(action['title'], className="card-title mb-1"),
                                html.P(action['description'], className="card-text text-muted small")
                            ], className="text-center")
                        ])
                    ], className="h-100 quick-action-card", href=action['href'])
                ], width=6, className="mb-3")
            )
        
        return dbc.Card([
            dbc.CardHeader([
                html.H5("Acciones Rápidas", className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row(action_buttons)
            ])
        ], className="quick-actions-section")
    
    def _create_alerts_section(self) -> dbc.Card:
        """Crea la sección de alertas y notificaciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("Alertas del Sistema", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "system-alerts",
                    html.Div(id="system-alerts-container"),
                    loading_type="default"
                )
            ])
        ], className="alerts-section")
    
    def _create_performance_chart_section(self) -> dbc.Row:
        """Crea la sección del gráfico de rendimiento general"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("Rendimiento General del Portfolio", className="mb-0")
                    ]),
                    dbc.CardBody([
                        self.create_loading_component(
                            "performance-chart",
                            dcc.Graph(
                                id="home-performance-chart",
                                config=self.get_default_chart_config(),
                                style={'height': '400px'}
                            ),
                            loading_type="default"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página HOME
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback principal para actualizar datos
        @app.callback(
            [Output('home-data-store', 'data'),
             Output('home-symbols-store', 'data')],
            [Input('home-refresh-interval', 'n_intervals'),
             Input('home-refresh-btn', 'n_clicks')]
        )
        def update_home_data(n_intervals, refresh_clicks):
            """Actualiza datos principales de la página HOME"""
            try:
                # Obtener datos del portfolio
                portfolio_data = self._get_portfolio_data()
                
                # Obtener datos de símbolos
                symbols_data = self._get_symbols_data()
                
                self.update_page_stats()
                
                return portfolio_data, symbols_data
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de HOME: {e}")
                return {}, {}
        
        # Callback para resumen del portfolio
        @app.callback(
            Output('portfolio-summary-cards', 'children'),
            [Input('home-data-store', 'data')]
        )
        def update_portfolio_summary(portfolio_data):
            """Actualiza las tarjetas de resumen del portfolio"""
            try:
                if not portfolio_data:
                    return self.create_empty_state(
                        title="Cargando datos del portfolio...",
                        message="Por favor espere mientras se cargan los datos",
                        icon="fas fa-spinner fa-spin"
                    )
                
                return self._create_portfolio_summary_cards(portfolio_data)
                
            except Exception as e:
                logger.error(f"Error al crear resumen del portfolio: {e}")
                return self.create_error_alert("Error al cargar resumen del portfolio")
        
        # Callback para grid de símbolos
        @app.callback(
            Output('symbols-grid-container', 'children'),
            [Input('home-symbols-store', 'data')]
        )
        def update_symbols_grid(symbols_data):
            """Actualiza el grid de símbolos auto-generado"""
            try:
                if not symbols_data:
                    return self.create_empty_state(
                        title="No hay símbolos configurados",
                        message="Configure símbolos en la sección de ajustes",
                        icon="fas fa-coins",
                        action_button={'text': 'Ir a Configuración', 'href': '/settings'}
                    )
                
                return self._create_symbols_grid(symbols_data)
                
            except Exception as e:
                logger.error(f"Error al crear grid de símbolos: {e}")
                return self.create_error_alert("Error al cargar métricas de símbolos")
        
        # Callback para alertas del sistema
        @app.callback(
            Output('system-alerts-container', 'children'),
            [Input('home-data-store', 'data')]
        )
        def update_system_alerts(portfolio_data):
            """Actualiza las alertas del sistema"""
            try:
                return self._create_system_alerts(portfolio_data)
                
            except Exception as e:
                logger.error(f"Error al crear alertas del sistema: {e}")
                return html.P("Error al cargar alertas", className="text-muted")
        
        # Callback para gráfico de rendimiento
        @app.callback(
            Output('home-performance-chart', 'figure'),
            [Input('home-data-store', 'data')]
        )
        def update_performance_chart(portfolio_data):
            """Actualiza el gráfico de rendimiento general"""
            try:
                return self._create_portfolio_performance_chart(portfolio_data)
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de rendimiento: {e}")
                return self._create_empty_chart("Error al cargar gráfico de rendimiento")
        
        # Callback para botón de exportar
        @app.callback(
            Output('home-export-btn', 'children'),
            [Input('home-export-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def export_home_data(n_clicks):
            """Exporta datos de la página HOME"""
            if n_clicks:
                try:
                    # Implementar exportación
                    self.log_page_action("export_data", {"format": "json"})
                    return [
                        html.I(className="fas fa-check me-1"),
                        "Exportado"
                    ]
                except Exception as e:
                    logger.error(f"Error al exportar datos: {e}")
            
            return [
                html.I(className="fas fa-download me-1"),
                "Exportar"
            ]
        
        logger.info("Callbacks de HomePage registrados")
    
    def _get_portfolio_data(self) -> Dict[str, Any]:
        """Obtiene datos consolidados del portfolio"""
        try:
            if self.performance_tracker:
                portfolio_summary = self.performance_tracker.get_portfolio_summary()
                return portfolio_summary
            else:
                # Datos simulados para desarrollo
                return {
                    'total_value': 15750.50,
                    'total_pnl': 2750.50,
                    'total_pnl_pct': 21.2,
                    'avg_sharpe_ratio': 1.85,
                    'max_drawdown': 8.5,
                    'win_rate': 68.2,
                    'total_symbols': 4,
                    'active_positions': 2,
                    'daily_pnl': 125.30,
                    'weekly_pnl': 890.75
                }
                
        except Exception as e:
            logger.error(f"Error al obtener datos del portfolio: {e}")
            return {}
    
    def _get_symbols_data(self) -> Dict[str, Any]:
        """Obtiene datos de todos los símbolos configurados"""
        try:
            if self.data_provider:
                symbols_metrics = self.data_provider.get_all_symbols_metrics()
                return {symbol: metrics.__dict__ if hasattr(metrics, '__dict__') else metrics 
                       for symbol, metrics in symbols_metrics.items()}
            else:
                # Datos simulados para desarrollo
                return {
                    'BTCUSDT': {
                        'symbol': 'BTCUSDT',
                        'win_rate': 72.5,
                        'total_runs': 25,
                        'avg_pnl': 145.30,
                        'balance_progress': 84.2,
                        'sharpe_ratio': 2.1,
                        'max_drawdown': 6.8,
                        'current_status': 'active',
                        'last_signal': 'buy',
                        'current_balance': 4250.75,
                        'target_balance': 5000.00,
                        'total_trades': 127
                    },
                    'ETHUSDT': {
                        'symbol': 'ETHUSDT',
                        'win_rate': 65.8,
                        'total_runs': 18,
                        'avg_pnl': 98.50,
                        'balance_progress': 62.4,
                        'sharpe_ratio': 1.6,
                        'max_drawdown': 12.3,
                        'current_status': 'active',
                        'last_signal': 'hold',
                        'current_balance': 3124.60,
                        'target_balance': 5000.00,
                        'total_trades': 89
                    },
                    'ADAUSDT': {
                        'symbol': 'ADAUSDT',
                        'win_rate': 58.3,
                        'total_runs': 12,
                        'avg_pnl': 45.20,
                        'balance_progress': 34.8,
                        'sharpe_ratio': 1.2,
                        'max_drawdown': 15.7,
                        'current_status': 'paused',
                        'last_signal': 'sell',
                        'current_balance': 1674.20,
                        'target_balance': 2500.00,
                        'total_trades': 56
                    }
                }
                
        except Exception as e:
            logger.error(f"Error al obtener datos de símbolos: {e}")
            return {}
    
    def _create_portfolio_summary_cards(self, portfolio_data: Dict[str, Any]) -> dbc.Row:
        """Crea las tarjetas de resumen del portfolio"""
        if not portfolio_data:
            return dbc.Row([])
        
        cards = []
        
        # Tarjeta de valor total
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Valor Total del Portfolio",
                value=portfolio_data.get('total_value', 0),
                subtitle="Balance consolidado",
                icon="fas fa-wallet",
                color="primary"
            )
        ], width=12, md=6, lg=3))
        
        # Tarjeta de PnL total
        pnl_trend = None
        if portfolio_data.get('total_pnl', 0) != 0:
            pnl_trend = portfolio_data.get('total_pnl_pct', 0)
        
        cards.append(dbc.Col([
            self.create_metric_card(
                title="PnL Total",
                value=f"${portfolio_data.get('total_pnl', 0):,.2f}",
                subtitle=f"{portfolio_data.get('total_pnl_pct', 0):.1f}%",
                icon="fas fa-chart-line",
                color="success" if portfolio_data.get('total_pnl', 0) > 0 else "danger",
                trend=pnl_trend
            )
        ], width=12, md=6, lg=3))
        
        # Tarjeta de Win Rate
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Win Rate Promedio",
                value=f"{portfolio_data.get('win_rate', 0):.1f}%",
                subtitle="Todas las operaciones",
                icon="fas fa-target",
                color="info"
            )
        ], width=12, md=6, lg=3))
        
        # Tarjeta de Sharpe Ratio
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Sharpe Ratio",
                value=f"{portfolio_data.get('avg_sharpe_ratio', 0):.2f}",
                subtitle="Rendimiento ajustado",
                icon="fas fa-chart-bar",
                color="warning"
            )
        ], width=12, md=6, lg=3))
        
        return dbc.Row(cards)
    
    def _create_symbols_grid(self, symbols_data: Dict[str, Any]) -> dbc.Row:
        """Crea el grid auto-generado de símbolos"""
        if not symbols_data:
            return dbc.Row([])
        
        symbol_cards = []
        symbols_per_row = self.page_config.get('symbols_per_row', 3)
        
        for symbol, metrics in symbols_data.items():
            # Determinar color según estado
            status = metrics.get('current_status', 'unknown')
            status_color = {
                'active': 'success',
                'paused': 'warning', 
                'error': 'danger',
                'unknown': 'secondary'
            }.get(status, 'secondary')
            
            # Crear tarjeta del símbolo
            symbol_card = dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H5(symbol, className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                dbc.Badge(
                                    status.title(),
                                    color=status_color,
                                    className="ms-auto"
                                )
                            ], width="auto", className="ms-auto")
                        ])
                    ]),
                    dbc.CardBody([
                        # Métricas principales
                        dbc.Row([
                            dbc.Col([
                                html.Small("Win Rate", className="text-muted"),
                                html.H6(f"{metrics.get('win_rate', 0):.1f}%", className="mb-2")
                            ], width=6),
                            dbc.Col([
                                html.Small("Total Runs", className="text-muted"),
                                html.H6(f"{metrics.get('total_runs', 0)}", className="mb-2")
                            ], width=6)
                        ]),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Small("PnL Promedio", className="text-muted"),
                                html.H6(f"${metrics.get('avg_pnl', 0):.2f}", className="mb-2")
                            ], width=6),
                            dbc.Col([
                                html.Small("% Objetivo", className="text-muted"),
                                html.H6(f"{metrics.get('balance_progress', 0):.1f}%", className="mb-2")
                            ], width=6)
                        ]),
                        
                        # Barra de progreso hacia objetivo
                        dbc.Progress(
                            value=metrics.get('balance_progress', 0),
                            color="success" if metrics.get('balance_progress', 0) > 70 else "primary",
                            className="mb-2",
                            style={'height': '8px'}
                        ),
                        
                        # Métricas adicionales
                        html.Div([
                            dbc.Badge(f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}", 
                                     color="outline-primary", className="me-1"),
                            dbc.Badge(f"DD: {metrics.get('max_drawdown', 0):.1f}%", 
                                     color="outline-secondary", className="me-1"),
                            dbc.Badge(f"Trades: {metrics.get('total_trades', 0)}", 
                                     color="outline-info")
                        ], className="mb-2"),
                        
                        # Última señal
                        html.Div([
                            html.Small("Última señal: ", className="text-muted"),
                            dbc.Badge(
                                metrics.get('last_signal', 'N/A').upper(),
                                color={
                                    'buy': 'success',
                                    'sell': 'danger', 
                                    'hold': 'warning'
                                }.get(metrics.get('last_signal', ''), 'secondary'),
                                className="ms-1"
                            )
                        ])
                    ]),
                    dbc.CardFooter([
                        dbc.ButtonGroup([
                            dbc.Button("Ver Gráfico", 
                                      href=f"/charts?symbol={symbol}",
                                      color="primary", 
                                      size="sm",
                                      outline=True),
                            dbc.Button("Detalles", 
                                      href=f"/performance?symbol={symbol}",
                                      color="secondary", 
                                      size="sm",
                                      outline=True)
                        ], size="sm", className="w-100")
                    ])
                ], className="symbol-card h-100")
            ], width=12, md=6, lg=12//symbols_per_row, className="mb-3")
            
            symbol_cards.append(symbol_card)
        
        return dbc.Row(symbol_cards)
    
    def _create_system_alerts(self, portfolio_data: Dict[str, Any]) -> html.Div:
        """Crea alertas del sistema basadas en datos"""
        alerts = []
        
        try:
            # Verificar estado de proveedores
            providers_status = self.validate_data_providers()
            
            if not providers_status.get('data_provider', False):
                alerts.append(
                    dbc.Alert([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "Proveedor de datos desconectado"
                    ], color="warning", className="mb-2")
                )
            
            # Alertas basadas en rendimiento
            if portfolio_data:
                max_drawdown = portfolio_data.get('max_drawdown', 0)
                if max_drawdown > 15:
                    alerts.append(
                        dbc.Alert([
                            html.I(className="fas fa-exclamation-circle me-2"),
                            f"Alto drawdown detectado: {max_drawdown:.1f}%"
                        ], color="danger", className="mb-2")
                    )
                
                win_rate = portfolio_data.get('win_rate', 0)
                if win_rate < 50:
                    alerts.append(
                        dbc.Alert([
                            html.I(className="fas fa-info-circle me-2"),
                            f"Win rate bajo: {win_rate:.1f}%"
                        ], color="info", className="mb-2")
                    )
            
            # Alertas de ejemplo adicionales
            alerts.append(
                dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    "Sistema funcionando correctamente"
                ], color="success", className="mb-2")
            )
            
            if not alerts:
                alerts.append(
                    html.P("No hay alertas activas", className="text-muted text-center py-3")
                )
            
            return html.Div(alerts)
            
        except Exception as e:
            logger.error(f"Error al crear alertas del sistema: {e}")
            return html.P("Error al cargar alertas", className="text-muted")
    
    def _create_portfolio_performance_chart(self, portfolio_data: Dict[str, Any]) -> go.Figure:
        """Crea gráfico de rendimiento del portfolio"""
        try:
            # Generar datos de ejemplo para el gráfico
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                                 end=datetime.now(), freq='D')
            
            # Simular evolución del balance
            initial_value = 10000
            returns = np.random.normal(0.005, 0.02, len(dates))  # 0.5% promedio diario
            cumulative_returns = np.cumprod(1 + returns)
            portfolio_values = initial_value * cumulative_returns
            
            fig = go.Figure()
            
            # Línea principal del portfolio
            fig.add_trace(go.Scatter(
                x=dates,
                y=portfolio_values,
                mode='lines',
                name='Valor del Portfolio',
                line=dict(color='#007bff', width=3),
                fill='tonexty',
                fillcolor='rgba(0, 123, 255, 0.1)'
            ))
            
            # Línea base
            fig.add_trace(go.Scatter(
                x=dates,
                y=[initial_value] * len(dates),
                mode='lines',
                name='Valor Inicial',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False
            ))
            
            # Configuración del gráfico
            fig.update_layout(
                title="Evolución del Portfolio (Últimos 30 días)",
                xaxis_title="Fecha",
                yaxis_title="Valor ($)",
                hovermode='x unified',
                showlegend=True,
                height=380,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            # Formateo de ejes
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de rendimiento: {e}")
            return self._create_empty_chart("Error al cargar datos del gráfico")
    
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
            height=380,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig