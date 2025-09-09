# Ruta: core/monitoring/pages/live_trading_page.py
"""
monitoring/pages/live_trading_page.py
Página de Trading en Tiempo Real - Trading Bot v10

Esta página proporciona monitoreo en tiempo real de:
- Operaciones activas en curso
- Precios en tiempo real con WebSocket
- Señales del modelo IA en vivo
- Órdenes pendientes y ejecutadas
- Feed de actividad en tiempo real
- Métricas de rendimiento instantáneas
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from monitoring.pages.base_page import BasePage

logger = logging.getLogger(__name__)

class LiveTradingPage(BasePage):
    """
    Página de trading en tiempo real del Trading Bot v10
    
    Monitorea operaciones activas, precios en vivo, señales del modelo
    y proporciona control en tiempo real del sistema de trading.
    """
    
    def __init__(self, data_provider=None, real_time_manager=None):
        """
        Inicializa la página de trading en tiempo real
        
        Args:
            data_provider: Proveedor de datos centralizado
            real_time_manager: Gestor de datos en tiempo real
        """
        super().__init__(data_provider=data_provider, real_time_manager=real_time_manager)
        
        # Configuración específica de la página Live Trading
        self.page_config.update({
            'title': 'Trading en Tiempo Real',
            'update_interval': 1000,  # 1 segundo para datos críticos
            'price_update_interval': 500,  # 0.5 segundos para precios
            'auto_refresh': True,
            'max_live_trades': 50,
            'max_activity_feed': 100,
            'enable_live_controls': True,
            'show_advanced_metrics': True,
            'alert_on_signals': True
        })
        
        # Estados de trading
        self.trading_states = {
            'active': {'color': 'success', 'icon': 'fas fa-play-circle', 'label': 'Activo'},
            'paused': {'color': 'warning', 'icon': 'fas fa-pause-circle', 'label': 'Pausado'},
            'stopped': {'color': 'danger', 'icon': 'fas fa-stop-circle', 'label': 'Detenido'},
            'error': {'color': 'danger', 'icon': 'fas fa-exclamation-triangle', 'label': 'Error'}
        }
        
        # Tipos de señales
        self.signal_types = {
            'buy': {'color': 'success', 'icon': 'fas fa-arrow-up', 'label': 'Compra'},
            'sell': {'color': 'danger', 'icon': 'fas fa-arrow-down', 'label': 'Venta'},
            'hold': {'color': 'warning', 'icon': 'fas fa-hand-paper', 'label': 'Mantener'}
        }
        
        # Tipos de órdenes
        self.order_types = {
            'market': {'label': 'Mercado', 'color': 'primary'},
            'limit': {'label': 'Límite', 'color': 'info'},
            'stop_loss': {'label': 'Stop Loss', 'color': 'danger'},
            'take_profit': {'label': 'Take Profit', 'color': 'success'}
        }
        
        logger.info("LiveTradingPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de trading en tiempo real
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Trading en Tiempo Real",
                    subtitle="Monitoreo y control de operaciones en vivo",
                    show_refresh=True,
                    show_export=False
                ),
                
                # Panel de control principal
                self._create_main_control_panel(),
                
                # Precios en tiempo real
                self._create_real_time_prices_section(),
                
                # Sección principal con 3 columnas
                dbc.Row([
                    # Columna izquierda: Operaciones activas
                    dbc.Col([
                        self._create_active_trades_section()
                    ], width=4),
                    
                    # Columna central: Gráfico de precios en vivo
                    dbc.Col([
                        self._create_live_chart_section()
                    ], width=5),
                    
                    # Columna derecha: Feed de actividad
                    dbc.Col([
                        self._create_activity_feed_section()
                    ], width=3)
                ], className="mb-4"),
                
                # Sección inferior: Órdenes y señales
                dbc.Row([
                    dbc.Col([
                        self._create_orders_section()
                    ], width=6),
                    dbc.Col([
                        self._create_signals_section()
                    ], width=6)
                ], className="mb-4"),
                
                # Métricas de rendimiento en tiempo real
                self._create_live_metrics_section(),
                
                # Componentes de actualización y stores
                dcc.Interval(
                    id='live-fast-update',
                    interval=self.page_config['price_update_interval'],
                    n_intervals=0
                ),
                dcc.Interval(
                    id='live-slow-update',
                    interval=self.page_config['update_interval'],
                    n_intervals=0
                ),
                dcc.Store(id='live-prices-store'),
                dcc.Store(id='live-trades-store'),
                dcc.Store(id='live-signals-store'),
                dcc.Store(id='live-orders-store'),
                dcc.Store(id='live-activity-store'),
                
            ], fluid=True, className="live-trading-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de LiveTradingPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de trading en vivo: {e}")
            ])
    
    def _create_main_control_panel(self) -> dbc.Row:
        """Crea el panel de control principal"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Estado general del sistema
                            dbc.Col([
                                html.Div([
                                    html.H6("Estado del Sistema", className="mb-2"),
                                    html.Div(id="system-status-indicator"),
                                ])
                            ], width=3),
                            
                            # Balance en tiempo real
                            dbc.Col([
                                html.Div([
                                    html.H6("Balance Total", className="mb-2"),
                                    html.H4(id="live-total-balance", className="text-primary mb-0"),
                                    html.Small(id="live-balance-change", className="text-muted")
                                ])
                            ], width=3),
                            
                            # PnL del día
                            dbc.Col([
                                html.Div([
                                    html.H6("PnL Hoy", className="mb-2"),
                                    html.H4(id="live-daily-pnl", className="mb-0"),
                                    html.Small(id="live-daily-pnl-pct", className="text-muted")
                                ])
                            ], width=3),
                            
                            # Controles del bot
                            dbc.Col([
                                html.Div([
                                    html.H6("Control del Bot", className="mb-2"),
                                    dbc.ButtonGroup([
                                        dbc.Button([
                                            html.I(className="fas fa-play me-1"),
                                            "Iniciar"
                                        ], id="start-bot-btn", color="success", size="sm"),
                                        dbc.Button([
                                            html.I(className="fas fa-pause me-1"),
                                            "Pausar"
                                        ], id="pause-bot-btn", color="warning", size="sm"),
                                        dbc.Button([
                                            html.I(className="fas fa-stop me-1"),
                                            "Detener"
                                        ], id="stop-bot-btn", color="danger", size="sm")
                                    ], size="sm")
                                ])
                            ], width=3)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_real_time_prices_section(self) -> dbc.Row:
        """Crea la sección de precios en tiempo real"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Precios en Tiempo Real", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="real-time-prices-grid", className="prices-grid")
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_active_trades_section(self) -> dbc.Card:
        """Crea la sección de operaciones activas"""
        return dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6("Operaciones Activas", className="mb-0")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Badge("0", id="active-trades-count", color="primary")
                    ], width="auto", className="ms-auto")
                ])
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "active-trades",
                    html.Div(id="active-trades-container"),
                    loading_type="default"
                )
            ]),
            dbc.CardFooter([
                dbc.Button("Ver Todas", href="/performance", color="outline-primary", size="sm")
            ])
        ])
    
    def _create_live_chart_section(self) -> dbc.Card:
        """Crea la sección del gráfico en tiempo real"""
        return dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6("Gráfico en Vivo", className="mb-0")
                    ], width="auto"),
                    dbc.Col([
                        dcc.Dropdown(
                            id="live-chart-symbol",
                            placeholder="Símbolo",
                            className="symbol-dropdown-sm"
                        )
                    ], width="auto", className="ms-auto")
                ])
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "live-chart",
                    dcc.Graph(
                        id="live-price-chart",
                        config={
                            **self.get_default_chart_config(),
                            'displayModeBar': False
                        },
                        style={'height': '400px'}
                    ),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_activity_feed_section(self) -> dbc.Card:
        """Crea la sección del feed de actividad"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Feed de Actividad", className="mb-0")
            ]),
            dbc.CardBody([
                html.Div(
                    id="activity-feed-container",
                    style={'height': '400px', 'overflow-y': 'auto'},
                    className="activity-feed"
                )
            ]),
            dbc.CardFooter([
                dbc.Button("Limpiar", id="clear-activity-btn", color="outline-secondary", size="sm")
            ])
        ])
    
    def _create_orders_section(self) -> dbc.Card:
        """Crea la sección de órdenes"""
        return dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6("Órdenes Pendientes", className="mb-0")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Badge("0", id="pending-orders-count", color="warning")
                    ], width="auto", className="ms-auto")
                ])
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "orders-table",
                    html.Div(id="orders-table-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_signals_section(self) -> dbc.Card:
        """Crea la sección de señales del modelo"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Señales del Modelo IA", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "signals-feed",
                    html.Div(id="signals-feed-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_live_metrics_section(self) -> dbc.Row:
        """Crea la sección de métricas en tiempo real"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Métricas en Tiempo Real", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="live-metrics-cards")
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de trading en tiempo real
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para inicializar selector de símbolo
        @app.callback(
            Output('live-chart-symbol', 'options'),
            [Input('live-slow-update', 'n_intervals')]
        )
        def initialize_symbol_selector(n_intervals):
            """Inicializa opciones del selector de símbolo"""
            try:
                if self.data_provider:
                    symbols = self.data_provider.get_configured_symbols()
                    options = [{'label': symbol, 'value': symbol} for symbol in symbols]
                    return options
                else:
                    return [
                        {'label': 'BTCUSDT', 'value': 'BTCUSDT'},
                        {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                        {'label': 'ADAUSDT', 'value': 'ADAUSDT'}
                    ]
            except Exception as e:
                logger.error(f"Error al inicializar selector: {e}")
                return []
        
        # Callback para precios en tiempo real (actualización rápida)
        @app.callback(
            Output('live-prices-store', 'data'),
            [Input('live-fast-update', 'n_intervals')]
        )
        def update_live_prices(n_intervals):
            """Actualiza precios en tiempo real"""
            try:
                if self.real_time_manager:
                    prices = self.real_time_manager.get_current_prices()
                    return self._format_live_prices(prices)
                else:
                    return self._generate_sample_live_prices()
                    
            except Exception as e:
                logger.error(f"Error al actualizar precios: {e}")
                return {}
        
        # Callback para datos de trading (actualización lenta)
        @app.callback(
            [Output('live-trades-store', 'data'),
             Output('live-signals-store', 'data'),
             Output('live-orders-store', 'data'),
             Output('live-activity-store', 'data')],
            [Input('live-slow-update', 'n_intervals')]
        )
        def update_live_trading_data(n_intervals):
            """Actualiza datos de trading"""
            try:
                # Obtener trades activos
                active_trades = self._get_active_trades()
                
                # Obtener señales recientes
                recent_signals = self._get_recent_signals()
                
                # Obtener órdenes pendientes
                pending_orders = self._get_pending_orders()
                
                # Obtener actividad reciente
                recent_activity = self._get_recent_activity()
                
                self.update_page_stats()
                
                return active_trades, recent_signals, pending_orders, recent_activity
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de trading: {e}")
                return {}, {}, {}, {}
        
        # Callback para panel de control principal
        @app.callback(
            [Output('system-status-indicator', 'children'),
             Output('live-total-balance', 'children'),
             Output('live-balance-change', 'children'),
             Output('live-daily-pnl', 'children'),
             Output('live-daily-pnl-pct', 'children')],
            [Input('live-slow-update', 'n_intervals')]
        )
        def update_main_control_panel(n_intervals):
            """Actualiza panel de control principal"""
            try:
                # Estado del sistema
                system_status = self._get_system_status()
                status_config = self.trading_states.get(system_status['status'], self.trading_states['error'])
                
                status_indicator = dbc.Badge([
                    html.I(className=f"{status_config['icon']} me-1"),
                    status_config['label']
                ], color=status_config['color'])
                
                # Balance total
                balance_data = self._get_balance_data()
                total_balance = f"${balance_data['total']:,.2f}"
                balance_change = f"{balance_data['change_24h']:+.2f}% (24h)"
                
                # PnL diario
                daily_pnl = balance_data['daily_pnl']
                daily_pnl_text = f"${daily_pnl:+,.2f}"
                daily_pnl_pct = f"{(daily_pnl/balance_data['total'])*100:+.2f}%"
                
                # Colores según signo
                daily_pnl_color = "text-success" if daily_pnl >= 0 else "text-danger"
                
                return (
                    status_indicator,
                    total_balance,
                    balance_change,
                    html.Span(daily_pnl_text, className=daily_pnl_color),
                    html.Span(daily_pnl_pct, className=daily_pnl_color)
                )
                
            except Exception as e:
                logger.error(f"Error al actualizar panel de control: {e}")
                return "Error", "$0.00", "N/A", "$0.00", "0.00%"
        
        # Callback para precios en tiempo real
        @app.callback(
            Output('real-time-prices-grid', 'children'),
            [Input('live-prices-store', 'data')]
        )
        def update_real_time_prices(prices_data):
            """Actualiza grid de precios en tiempo real"""
            try:
                if not prices_data:
                    return html.P("Conectando a feeds de precios...", className="text-muted text-center py-3")
                
                return self._create_prices_grid(prices_data)
                
            except Exception as e:
                logger.error(f"Error al actualizar precios: {e}")
                return html.P("Error al cargar precios", className="text-danger text-center")
        
        # Callback para operaciones activas
        @app.callback(
            [Output('active-trades-container', 'children'),
             Output('active-trades-count', 'children')],
            [Input('live-trades-store', 'data')]
        )
        def update_active_trades(trades_data):
            """Actualiza lista de operaciones activas"""
            try:
                if not trades_data or not trades_data.get('trades'):
                    return (
                        html.P("No hay operaciones activas", className="text-muted text-center py-3"),
                        "0"
                    )
                
                trades_list = self._create_active_trades_list(trades_data['trades'])
                count = len(trades_data['trades'])
                
                return trades_list, str(count)
                
            except Exception as e:
                logger.error(f"Error al actualizar trades activos: {e}")
                return html.P("Error al cargar trades", className="text-danger"), "0"
        
        # Callback para gráfico en vivo
        @app.callback(
            Output('live-price-chart', 'figure'),
            [Input('live-prices-store', 'data'),
             Input('live-chart-symbol', 'value')]
        )
        def update_live_chart(prices_data, selected_symbol):
            """Actualiza gráfico de precios en vivo"""
            try:
                if not selected_symbol:
                    # Auto-seleccionar primer símbolo disponible
                    if prices_data:
                        selected_symbol = list(prices_data.keys())[0]
                    else:
                        selected_symbol = 'BTCUSDT'
                
                return self._create_live_price_chart(prices_data, selected_symbol)
                
            except Exception as e:
                logger.error(f"Error al actualizar gráfico en vivo: {e}")
                return self._create_empty_live_chart("Error al cargar gráfico")
        
        # Callback para feed de actividad
        @app.callback(
            Output('activity-feed-container', 'children'),
            [Input('live-activity-store', 'data'),
             Input('clear-activity-btn', 'n_clicks')]
        )
        def update_activity_feed(activity_data, clear_clicks):
            """Actualiza feed de actividad"""
            try:
                # Si se presionó limpiar, retornar vacío
                if clear_clicks and ctx.triggered[0]['prop_id'] == 'clear-activity-btn.n_clicks':
                    return html.P("Feed limpiado", className="text-muted text-center py-3")
                
                if not activity_data or not activity_data.get('activities'):
                    return html.P("No hay actividad reciente", className="text-muted text-center py-3")
                
                return self._create_activity_feed_list(activity_data['activities'])
                
            except Exception as e:
                logger.error(f"Error al actualizar feed de actividad: {e}")
                return html.P("Error al cargar actividad", className="text-danger")
        
        # Callback para órdenes pendientes
        @app.callback(
            [Output('orders-table-container', 'children'),
             Output('pending-orders-count', 'children')],
            [Input('live-orders-store', 'data')]
        )
        def update_orders_table(orders_data):
            """Actualiza tabla de órdenes pendientes"""
            try:
                if not orders_data or not orders_data.get('orders'):
                    return (
                        html.P("No hay órdenes pendientes", className="text-muted text-center py-3"),
                        "0"
                    )
                
                orders_table = self._create_orders_table(orders_data['orders'])
                count = len(orders_data['orders'])
                
                return orders_table, str(count)
                
            except Exception as e:
                logger.error(f"Error al actualizar órdenes: {e}")
                return html.P("Error al cargar órdenes", className="text-danger"), "0"
        
        # Callback para señales del modelo
        @app.callback(
            Output('signals-feed-container', 'children'),
            [Input('live-signals-store', 'data')]
        )
        def update_signals_feed(signals_data):
            """Actualiza feed de señales del modelo"""
            try:
                if not signals_data or not signals_data.get('signals'):
                    return html.P("No hay señales recientes", className="text-muted text-center py-3")
                
                return self._create_signals_feed_list(signals_data['signals'])
                
            except Exception as e:
                logger.error(f"Error al actualizar señales: {e}")
                return html.P("Error al cargar señales", className="text-danger")
        
        # Callback para métricas en tiempo real
        @app.callback(
            Output('live-metrics-cards', 'children'),
            [Input('live-slow-update', 'n_intervals')]
        )
        def update_live_metrics(n_intervals):
            """Actualiza métricas en tiempo real"""
            try:
                metrics = self._get_live_metrics()
                return self._create_live_metrics_cards(metrics)
                
            except Exception as e:
                logger.error(f"Error al actualizar métricas en vivo: {e}")
                return html.P("Error al cargar métricas", className="text-danger")
        
        # Callbacks para controles del bot
        @app.callback(
            [Output('start-bot-btn', 'disabled'),
             Output('pause-bot-btn', 'disabled'),
             Output('stop-bot-btn', 'disabled')],
            [Input('start-bot-btn', 'n_clicks'),
             Input('pause-bot-btn', 'n_clicks'),
             Input('stop-bot-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def handle_bot_controls(start_clicks, pause_clicks, stop_clicks):
            """Maneja controles del bot"""
            try:
                triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
                
                if triggered_id == 'start-bot-btn':
                    self.log_page_action("start_bot_requested")
                    # Aquí iría la lógica para iniciar el bot
                elif triggered_id == 'pause-bot-btn':
                    self.log_page_action("pause_bot_requested")
                    # Aquí iría la lógica para pausar el bot
                elif triggered_id == 'stop-bot-btn':
                    self.log_page_action("stop_bot_requested")
                    # Aquí iría la lógica para detener el bot
                
                # Por ahora, retornar estado actual
                return False, False, False
                
            except Exception as e:
                logger.error(f"Error en controles del bot: {e}")
                return False, False, False
        
        logger.info("Callbacks de LiveTradingPage registrados")
    
    def _format_live_prices(self, prices_dict: Dict) -> Dict[str, Any]:
        """Formatea precios en tiempo real"""
        formatted_prices = {}
        
        for symbol, price_data in prices_dict.items():
            formatted_prices[symbol] = {
                'price': price_data.price,
                'change_24h': price_data.change_24h_percentage,
                'volume_24h': price_data.volume_24h,
                'bid': price_data.bid,
                'ask': price_data.ask,
                'spread': price_data.spread,
                'timestamp': price_data.timestamp.isoformat()
            }
        
        return formatted_prices
    
    def _generate_sample_live_prices(self) -> Dict[str, Any]:
        """Genera precios de muestra para desarrollo"""
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
        base_prices = {'BTCUSDT': 50000, 'ETHUSDT': 3000, 'ADAUSDT': 1.5, 'BNBUSDT': 300}
        
        prices = {}
        for symbol in symbols:
            base_price = base_prices.get(symbol, 1000)
            # Añadir movimiento aleatorio pequeño
            current_price = base_price * (1 + np.random.normal(0, 0.001))
            
            prices[symbol] = {
                'price': round(current_price, 2),
                'change_24h': round(np.random.normal(0, 3), 2),
                'volume_24h': round(np.random.uniform(1000000, 10000000), 0),
                'bid': round(current_price * 0.9995, 2),
                'ask': round(current_price * 1.0005, 2),
                'spread': round(current_price * 0.001, 4),
                'timestamp': datetime.now().isoformat()
            }
        
        return prices
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Obtiene estado del sistema"""
        try:
            # Verificar estado de proveedores
            providers_status = self.validate_data_providers()
            
            if providers_status.get('data_provider') and providers_status.get('real_time_manager'):
                status = 'active'
            elif providers_status.get('data_provider'):
                status = 'paused'
            else:
                status = 'error'
            
            return {
                'status': status,
                'uptime': '2h 15m',
                'last_signal': datetime.now() - timedelta(minutes=3),
                'providers': providers_status
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estado del sistema: {e}")
            return {'status': 'error'}
    
    def _get_balance_data(self) -> Dict[str, float]:
        """Obtiene datos de balance"""
        return {
            'total': np.random.uniform(8000, 12000),
            'change_24h': np.random.normal(2, 5),
            'daily_pnl': np.random.normal(50, 200),
            'available': np.random.uniform(7000, 11000),
            'in_orders': np.random.uniform(500, 1500)
        }
    
    def _get_active_trades(self) -> Dict[str, Any]:
        """Obtiene trades activos"""
        try:
            if self.data_provider:
                trades = self.data_provider.get_recent_trades(None, 10)
                active_trades = [t for t in trades if t.status == 'open']
                return {'trades': [t.__dict__ if hasattr(t, '__dict__') else t for t in active_trades]}
            else:
                # Generar trades de muestra
                return self._generate_sample_active_trades()
                
        except Exception as e:
            logger.error(f"Error al obtener trades activos: {e}")
            return {'trades': []}
    
    def _generate_sample_active_trades(self) -> Dict[str, Any]:
        """Genera trades activos de muestra"""
        trades = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for i in range(np.random.randint(1, 4)):
            symbol = np.random.choice(symbols)
            side = np.random.choice(['buy', 'sell'])
            entry_time = datetime.now() - timedelta(minutes=np.random.randint(5, 120))
            entry_price = np.random.uniform(40000, 60000) if 'BTC' in symbol else np.random.uniform(2000, 4000)
            quantity = np.random.uniform(0.001, 0.1)
            
            # Calcular PnL no realizado
            current_price = entry_price * (1 + np.random.normal(0, 0.02))
            if side == 'buy':
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity
            
            trades.append({
                'trade_id': f'live_trade_{i+1}',
                'symbol': symbol,
                'side': side,
                'entry_time': entry_time,
                'entry_price': entry_price,
                'current_price': current_price,
                'quantity': quantity,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': (unrealized_pnl / (entry_price * quantity)) * 100,
                'duration_minutes': (datetime.now() - entry_time).total_seconds() / 60,
                'stop_loss': entry_price * (0.98 if side == 'buy' else 1.02),
                'take_profit': entry_price * (1.05 if side == 'buy' else 0.95),
                'status': 'open'
            })
        
        return {'trades': trades}
    
    def _get_recent_signals(self) -> Dict[str, Any]:
        """Obtiene señales recientes del modelo"""
        signals = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for i in range(np.random.randint(3, 8)):
            signal_time = datetime.now() - timedelta(minutes=np.random.randint(1, 30))
            signal_type = np.random.choice(['buy', 'sell', 'hold'], p=[0.3, 0.3, 0.4])
            
            signals.append({
                'signal_id': f'signal_{i+1}',
                'symbol': np.random.choice(symbols),
                'signal_type': signal_type,
                'confidence': np.random.uniform(0.6, 0.95),
                'price': np.random.uniform(45000, 55000),
                'timestamp': signal_time,
                'model_version': '10.2.1',
                'features_used': ['rsi', 'macd', 'bollinger', 'volume'],
                'executed': np.random.choice([True, False], p=[0.7, 0.3])
            })
        
        # Ordenar por timestamp descendente
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        return {'signals': signals}
    
    def _get_pending_orders(self) -> Dict[str, Any]:
        """Obtiene órdenes pendientes"""
        orders = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for i in range(np.random.randint(2, 6)):
            order_time = datetime.now() - timedelta(minutes=np.random.randint(1, 60))
            order_type = np.random.choice(['limit', 'stop_loss', 'take_profit'])
            
            orders.append({
                'order_id': f'order_{i+1}',
                'symbol': np.random.choice(symbols),
                'side': np.random.choice(['buy', 'sell']),
                'type': order_type,
                'quantity': np.random.uniform(0.001, 0.1),
                'price': np.random.uniform(45000, 55000),
                'filled_quantity': 0,
                'remaining_quantity': np.random.uniform(0.001, 0.1),
                'status': 'pending',
                'created_time': order_time,
                'expires_time': order_time + timedelta(hours=24)
            })
        
        return {'orders': orders}
    
    def _get_recent_activity(self) -> Dict[str, Any]:
        """Obtiene actividad reciente"""
        activities = []
        activity_types = [
            'trade_opened', 'trade_closed', 'signal_generated', 'order_placed',
            'order_filled', 'order_cancelled', 'model_updated', 'balance_updated'
        ]
        
        for i in range(np.random.randint(10, 20)):
            activity_time = datetime.now() - timedelta(minutes=np.random.randint(1, 120))
            activity_type = np.random.choice(activity_types)
            
            activities.append({
                'id': f'activity_{i+1}',
                'type': activity_type,
                'message': self._generate_activity_message(activity_type),
                'timestamp': activity_time,
                'symbol': np.random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT', None]),
                'severity': np.random.choice(['info', 'success', 'warning', 'error'], p=[0.5, 0.3, 0.15, 0.05])
            })
        
        # Ordenar por timestamp descendente
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return {'activities': activities[:self.page_config['max_activity_feed']]}
    
    def _generate_activity_message(self, activity_type: str) -> str:
        """Genera mensaje de actividad"""
        messages = {
            'trade_opened': 'Nueva operación abierta',
            'trade_closed': 'Operación cerrada con ganancia',
            'signal_generated': 'Nueva señal de compra generada',
            'order_placed': 'Orden límite colocada',
            'order_filled': 'Orden ejecutada exitosamente',
            'order_cancelled': 'Orden cancelada por timeout',
            'model_updated': 'Modelo IA actualizado',
            'balance_updated': 'Balance sincronizado con exchange'
        }
        return messages.get(activity_type, 'Actividad del sistema')
    
    def _get_live_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas en tiempo real"""
        return {
            'active_positions': np.random.randint(1, 5),
            'open_orders': np.random.randint(2, 8),
            'signals_today': np.random.randint(15, 45),
            'trades_today': np.random.randint(5, 20),
            'win_rate_today': np.random.uniform(50, 85),
            'avg_trade_duration': np.random.uniform(15, 180),  # minutos
            'model_accuracy': np.random.uniform(65, 85),
            'api_latency': np.random.uniform(50, 200),  # ms
            'uptime_hours': np.random.uniform(2, 24),
            'last_error': datetime.now() - timedelta(hours=np.random.randint(1, 12))
        }
    
    def _create_prices_grid(self, prices_data: Dict[str, Any]) -> html.Div:
        """Crea grid de precios en tiempo real"""
        price_cards = []
        
        for symbol, data in prices_data.items():
            change_color = "text-success" if data['change_24h'] >= 0 else "text-danger"
            change_icon = "fas fa-arrow-up" if data['change_24h'] >= 0 else "fas fa-arrow-down"
            
            price_card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H6(symbol, className="mb-1"),
                            html.H5(f"${data['price']:,.2f}", className="mb-1"),
                            html.Div([
                                html.I(className=f"{change_icon} me-1"),
                                html.Span(f"{data['change_24h']:+.2f}%")
                            ], className=f"{change_color} small"),
                            html.Div([
                                html.Small(f"Vol: {self._format_metric_value(data['volume_24h'])}", 
                                          className="text-muted")
                            ])
                        ])
                    ])
                ], className="price-card h-100")
            ], width=6, md=4, lg=3, className="mb-2")
            
            price_cards.append(price_card)
        
        return dbc.Row(price_cards)
    
    def _create_active_trades_list(self, trades: List[Dict[str, Any]]) -> html.Div:
        """Crea lista de trades activos"""
        if not trades:
            return html.P("No hay operaciones activas", className="text-muted text-center py-3")
        
        trade_items = []
        
        for trade in trades[:self.page_config['max_live_trades']]:
            pnl_color = "text-success" if trade.get('unrealized_pnl', 0) >= 0 else "text-danger"
            side_color = "text-success" if trade['side'] == 'buy' else "text-danger"
            side_icon = "fas fa-arrow-up" if trade['side'] == 'buy' else "fas fa-arrow-down"
            
            duration = int(trade.get('duration_minutes', 0))
            duration_text = f"{duration}m" if duration < 60 else f"{duration//60}h {duration%60}m"
            
            trade_item = dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Strong(trade['symbol']),
                            html.Span([
                                html.I(className=f"{side_icon} ms-2 me-1"),
                                trade['side'].upper()
                            ], className=f"{side_color} small")
                        ])
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.Strong(f"${trade.get('unrealized_pnl', 0):+,.2f}", className=pnl_color),
                            html.Br(),
                            html.Small(f"{trade.get('unrealized_pnl_pct', 0):+.2f}%", className=pnl_color)
                        ])
                    ], width=6, className="text-end")
                ]),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([
                        html.Small([
                            f"Entrada: ${trade['entry_price']:,.2f}",
                            html.Br(),
                            f"Actual: ${trade.get('current_price', 0):,.2f}"
                        ], className="text-muted")
                    ], width=6),
                    dbc.Col([
                        html.Small([
                            f"Cantidad: {trade['quantity']:.4f}",
                            html.Br(),
                            f"Duración: {duration_text}"
                        ], className="text-muted")
                    ], width=6)
                ])
            ])
            
            trade_items.append(trade_item)
        
        return dbc.ListGroup(trade_items)
    
    def _create_live_price_chart(self, prices_data: Dict[str, Any], symbol: str) -> go.Figure:
        """Crea gráfico de precio en tiempo real"""
        try:
            # Generar datos de precio histórico reciente para el símbolo
            timestamps = pd.date_range(
                start=datetime.now() - timedelta(minutes=60),
                end=datetime.now(),
                freq='1min'
            )
            
            # Precio base del símbolo
            if symbol in prices_data:
                current_price = prices_data[symbol]['price']
            else:
                current_price = 50000 if 'BTC' in symbol else 3000
            
            # Generar serie de precios realista
            prices = []
            base_price = current_price * 0.999  # Empezar ligeramente más bajo
            
            for i, timestamp in enumerate(timestamps):
                # Movimiento aleatorio pequeño
                change = np.random.normal(0, current_price * 0.0002)
                base_price += change
                prices.append(base_price)
            
            # Asegurar que el último precio sea el actual
            prices[-1] = current_price
            
            fig = go.Figure()
            
            # Línea de precio
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=prices,
                mode='lines',
                name=symbol,
                line=dict(color='#007bff', width=2),
                hovertemplate=f'{symbol}<br>Precio: $%{{y:,.2f}}<br>Tiempo: %{{x}}<extra></extra>'
            ))
            
            # Precio actual como punto destacado
            fig.add_trace(go.Scatter(
                x=[timestamps[-1]],
                y=[current_price],
                mode='markers',
                name='Precio Actual',
                marker=dict(color='red', size=8),
                showlegend=False
            ))
            
            # Configuración del gráfico
            fig.update_layout(
                title=f'{symbol} - Precio en Tiempo Real',
                xaxis_title='Tiempo',
                yaxis_title='Precio ($)',
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
                hovermode='x unified'
            )
            
            # Configurar ejes
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickformat='%H:%M'
            )
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickformat='$,.2f'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico en vivo: {e}")
            return self._create_empty_live_chart("Error al generar gráfico en vivo")
    
    def _create_activity_feed_list(self, activities: List[Dict[str, Any]]) -> html.Div:
        """Crea lista del feed de actividad"""
        if not activities:
            return html.P("No hay actividad reciente", className="text-muted text-center py-3")
        
        activity_items = []
        
        for activity in activities:
            # Iconos y colores según tipo de actividad
            activity_icons = {
                'trade_opened': 'fas fa-play-circle',
                'trade_closed': 'fas fa-check-circle',
                'signal_generated': 'fas fa-lightbulb',
                'order_placed': 'fas fa-plus-circle',
                'order_filled': 'fas fa-check',
                'order_cancelled': 'fas fa-times-circle',
                'model_updated': 'fas fa-brain',
                'balance_updated': 'fas fa-sync-alt'
            }
            
            severity_colors = {
                'info': 'text-info',
                'success': 'text-success',
                'warning': 'text-warning',
                'error': 'text-danger'
            }
            
            icon = activity_icons.get(activity['type'], 'fas fa-info-circle')
            color = severity_colors.get(activity['severity'], 'text-info')
            
            # Formatear tiempo relativo
            time_diff = datetime.now() - activity['timestamp']
            if time_diff.total_seconds() < 60:
                time_text = "Hace unos segundos"
            elif time_diff.total_seconds() < 3600:
                time_text = f"Hace {int(time_diff.total_seconds() / 60)} min"
            else:
                time_text = f"Hace {int(time_diff.total_seconds() / 3600)} h"
            
            activity_item = html.Div([
                html.Div([
                    html.I(className=f"{icon} me-2 {color}"),
                    html.Span(activity['message'], className="activity-message"),
                    html.Br(),
                    html.Small([
                        activity.get('symbol', ''),
                        " • " if activity.get('symbol') else "",
                        time_text
                    ], className="text-muted")
                ], className="activity-item py-2 px-2 mb-1 rounded")
            ])
            
            activity_items.append(activity_item)
        
        return html.Div(activity_items)
    
    def _create_orders_table(self, orders: List[Dict[str, Any]]) -> html.Div:
        """Crea tabla de órdenes pendientes"""
        if not orders:
            return html.P("No hay órdenes pendientes", className="text-muted text-center py-3")
        
        # Preparar datos para tabla
        table_data = []
        for order in orders:
            table_data.append({
                'symbol': order['symbol'],
                'side': order['side'].upper(),
                'type': order['type'].replace('_', ' ').title(),
                'quantity': f"{order['quantity']:.4f}",
                'price': f"${order['price']:,.2f}",
                'status': order['status'].title(),
                'created': order['created_time'].strftime('%H:%M:%S')
            })
        
        # Configuración de columnas
        columns = [
            {'name': 'Símbolo', 'id': 'symbol'},
            {'name': 'Lado', 'id': 'side'},
            {'name': 'Tipo', 'id': 'type'},
            {'name': 'Cantidad', 'id': 'quantity'},
            {'name': 'Precio', 'id': 'price'},
            {'name': 'Estado', 'id': 'status'},
            {'name': 'Creada', 'id': 'created'}
        ]
        
        return self.create_data_table(
            data=table_data,
            columns=columns,
            table_id="live-orders-table",
            page_size=10,
            sortable=False
        )
    
    def _create_signals_feed_list(self, signals: List[Dict[str, Any]]) -> html.Div:
        """Crea lista de señales del modelo"""
        if not signals:
            return html.P("No hay señales recientes", className="text-muted text-center py-3")
        
        signal_items = []
        
        for signal in signals[:10]:  # Mostrar últimas 10 señales
            signal_config = self.signal_types.get(signal['signal_type'], self.signal_types['hold'])
            
            # Formatear tiempo
            time_diff = datetime.now() - signal['timestamp']
            if time_diff.total_seconds() < 60:
                time_text = "Ahora"
            elif time_diff.total_seconds() < 3600:
                time_text = f"{int(time_diff.total_seconds() / 60)}m"
            else:
                time_text = f"{int(time_diff.total_seconds() / 3600)}h"
            
            # Badge de ejecución
            executed_badge = dbc.Badge(
                "Ejecutada" if signal.get('executed') else "Pendiente",
                color="success" if signal.get('executed') else "warning",
                className="ms-2"
            )
            
            signal_item = dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className=f"{signal_config['icon']} me-2 text-{signal_config['color']}"),
                            html.Strong(f"{signal['symbol']} - {signal_config['label'].upper()}"),
                            executed_badge
                        ])
                    ], width=12)
                ]),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([
                        html.Small([
                            f"Precio: ${signal['price']:,.2f}",
                            html.Br(),
                            f"Confianza: {signal['confidence']*100:.1f}%"
                        ], className="text-muted")
                    ], width=6),
                    dbc.Col([
                        html.Small([
                            f"Tiempo: {time_text}",
                            html.Br(),
                            f"Modelo: v{signal['model_version']}"
                        ], className="text-muted")
                    ], width=6)
                ])
            ])
            
            signal_items.append(signal_item)
        
        return dbc.ListGroup(signal_items)
    
    def _create_live_metrics_cards(self, metrics: Dict[str, Any]) -> dbc.Row:
        """Crea tarjetas de métricas en tiempo real"""
        cards = []
        
        # Posiciones activas
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Posiciones Activas",
                value=metrics['active_positions'],
                subtitle="Operaciones abiertas",
                icon="fas fa-chart-line",
                color="primary"
            )
        ], width=12, md=6, lg=2))
        
        # Órdenes abiertas
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Órdenes Pendientes",
                value=metrics['open_orders'],
                subtitle="En el libro de órdenes",
                icon="fas fa-list-ul",
                color="warning"
            )
        ], width=12, md=6, lg=2))
        
        # Señales hoy
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Señales Hoy",
                value=metrics['signals_today'],
                subtitle="Generadas por IA",
                icon="fas fa-lightbulb",
                color="info"
            )
        ], width=12, md=6, lg=2))
        
        # Trades hoy
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Trades Hoy",
                value=metrics['trades_today'],
                subtitle="Operaciones ejecutadas",
                icon="fas fa-exchange-alt",
                color="success"
            )
        ], width=12, md=6, lg=2))
        
        # Win rate hoy
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Win Rate Hoy",
                value=f"{metrics['win_rate_today']:.1f}%",
                subtitle="Tasa de éxito",
                icon="fas fa-target",
                color="success" if metrics['win_rate_today'] > 60 else "warning"
            )
        ], width=12, md=6, lg=2))
        
        # Latencia API
        cards.append(dbc.Col([
            self.create_metric_card(
                title="Latencia API",
                value=f"{metrics['api_latency']:.0f}ms",
                subtitle="Tiempo de respuesta",
                icon="fas fa-stopwatch",
                color="success" if metrics['api_latency'] < 100 else "warning"
            )
        ], width=12, md=6, lg=2))
        
        return dbc.Row(cards)
    
    def _create_empty_live_chart(self, message: str) -> go.Figure:
        """Crea gráfico vacío para modo live"""
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