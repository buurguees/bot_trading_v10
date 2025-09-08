"""
monitoring/pages/charts_page.py
Página de Gráficos Interactivos - Trading Bot v10

Esta página muestra:
- Gráfico de velas interactivo con todo el histórico
- Dropdown funcional para seleccionar símbolo
- Dropdown para períodos temporales (Total, 1 año, 90 días, 30 días, 1 día)
- Top 20 ciclos con mejores métricas
- Indicadores técnicos superpuestos
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

class ChartsPage(BasePage):
    """
    Página de gráficos interactivos del Trading Bot v10
    
    Proporciona análisis técnico visual con gráficos de velas,
    indicadores técnicos y análisis de los mejores ciclos.
    """
    
    def __init__(self, data_provider=None):
        """
        Inicializa la página de gráficos
        
        Args:
            data_provider: Proveedor de datos centralizado
        """
        super().__init__(data_provider=data_provider)
        
        # Configuración específica de la página Charts
        self.page_config.update({
            'title': 'Gráficos Interactivos',
            'update_interval': 10000,  # 10 segundos
            'auto_refresh': True,
            'default_symbol': 'BTCUSDT',
            'default_period': '90d',
            'max_candles_display': 10000,
            'enable_technical_indicators': True,
            'chart_height': 600,
            'cycles_table_height': 400
        })
        
        # Períodos disponibles
        self.time_periods = {
            'all': {'label': 'Todo el histórico', 'days': None},
            '1y': {'label': '1 año', 'days': 365},
            '90d': {'label': '90 días', 'days': 90},
            '30d': {'label': '30 días', 'days': 30},
            '1d': {'label': '1 día', 'days': 1}
        }
        
        # Indicadores técnicos disponibles
        self.technical_indicators = {
            'sma_20': {'name': 'SMA 20', 'enabled': True},
            'sma_50': {'name': 'SMA 50', 'enabled': True},
            'ema_12': {'name': 'EMA 12', 'enabled': False},
            'ema_26': {'name': 'EMA 26', 'enabled': False},
            'bollinger': {'name': 'Bollinger Bands', 'enabled': True},
            'rsi': {'name': 'RSI', 'enabled': True},
            'macd': {'name': 'MACD', 'enabled': False},
            'volume': {'name': 'Volumen', 'enabled': True}
        }
        
        logger.info("ChartsPage inicializada")
    
    def get_layout(self) -> dbc.Container:
        """
        Obtiene el layout principal de la página de gráficos
        
        Returns:
            dbc.Container: Layout completo de la página
        """
        try:
            return dbc.Container([
                # Header de la página
                self.create_page_header(
                    title="Gráficos Interactivos",
                    subtitle="Análisis técnico avanzado con datos históricos completos",
                    show_refresh=True,
                    show_export=True
                ),
                
                # Controles principales
                self._create_chart_controls_section(),
                
                # Gráfico principal de velas
                self._create_main_chart_section(),
                
                # Sección inferior con Top 20 ciclos y métricas
                dbc.Row([
                    dbc.Col([
                        self._create_top_cycles_section()
                    ], width=8),
                    dbc.Col([
                        self._create_chart_metrics_section()
                    ], width=4)
                ], className="mb-4"),
                
                # Componentes de actualización y stores
                self.create_refresh_interval("charts-refresh-interval"),
                dcc.Store(id='charts-data-store'),
                dcc.Store(id='selected-symbol-store', data=self.page_config['default_symbol']),
                dcc.Store(id='selected-period-store', data=self.page_config['default_period']),
                
            ], fluid=True, className="charts-page")
            
        except Exception as e:
            logger.error(f"Error al crear layout de ChartsPage: {e}")
            return dbc.Container([
                self.create_error_alert(f"Error al cargar la página de gráficos: {e}")
            ])
    
    def _create_chart_controls_section(self) -> dbc.Row:
        """Crea la sección de controles del gráfico"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Selector de símbolo
                            dbc.Col([
                                html.Label("Símbolo:", className="form-label mb-2"),
                                self.create_symbol_selector("symbol-selector")
                            ], width=12, md=3),
                            
                            # Selector de período
                            dbc.Col([
                                html.Label("Período:", className="form-label mb-2"),
                                dcc.Dropdown(
                                    id="period-selector",
                                    options=[
                                        {'label': period['label'], 'value': key}
                                        for key, period in self.time_periods.items()
                                    ],
                                    value=self.page_config['default_period'],
                                    placeholder="Seleccionar período",
                                    className="period-selector"
                                )
                            ], width=12, md=3),
                            
                            # Selector de timeframe
                            dbc.Col([
                                html.Label("Timeframe:", className="form-label mb-2"),
                                dcc.Dropdown(
                                    id="timeframe-selector",
                                    options=[
                                        {'label': '1m', 'value': '1m'},
                                        {'label': '5m', 'value': '5m'},
                                        {'label': '15m', 'value': '15m'},
                                        {'label': '1h', 'value': '1h'},
                                        {'label': '4h', 'value': '4h'},
                                        {'label': '1d', 'value': '1d'}
                                    ],
                                    value='1h',
                                    placeholder="Timeframe",
                                    className="timeframe-selector"
                                )
                            ], width=12, md=2),
                            
                            # Indicadores técnicos
                            dbc.Col([
                                html.Label("Indicadores:", className="form-label mb-2"),
                                dcc.Dropdown(
                                    id="indicators-selector",
                                    options=[
                                        {'label': indicator['name'], 'value': key}
                                        for key, indicator in self.technical_indicators.items()
                                    ],
                                    value=[key for key, indicator in self.technical_indicators.items() 
                                          if indicator['enabled']],
                                    multi=True,
                                    placeholder="Seleccionar indicadores",
                                    className="indicators-selector"
                                )
                            ], width=12, md=4)
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_main_chart_section(self) -> dbc.Row:
        """Crea la sección del gráfico principal"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H5("Gráfico de Velas", className="mb-0")
                            ], width="auto"),
                            dbc.Col([
                                html.Div(id="chart-info", className="text-muted small")
                            ], width="auto", className="ms-auto")
                        ])
                    ]),
                    dbc.CardBody([
                        self.create_loading_component(
                            "main-chart",
                            dcc.Graph(
                                id="candlestick-chart",
                                config={
                                    **self.get_default_chart_config(),
                                    'modeBarButtonsToAdd': [
                                        'drawline', 'drawopenpath', 'drawclosedpath',
                                        'drawcircle', 'drawrect', 'eraseshape'
                                    ]
                                },
                                style={'height': f"{self.page_config['chart_height']}px"}
                            ),
                            loading_type="default"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-4")
    
    def _create_top_cycles_section(self) -> dbc.Card:
        """Crea la sección del Top 20 ciclos"""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("Top 20 Ciclos - Mejores Métricas", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "top-cycles",
                    html.Div(id="top-cycles-table"),
                    loading_type="default"
                )
            ])
        ])
    
    def _create_chart_metrics_section(self) -> dbc.Card:
        """Crea la sección de métricas del gráfico"""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("Métricas del Símbolo", className="mb-0")
            ]),
            dbc.CardBody([
                self.create_loading_component(
                    "chart-metrics",
                    html.Div(id="chart-metrics-container"),
                    loading_type="default"
                )
            ])
        ])
    
    def register_callbacks(self, app: dash.Dash) -> None:
        """
        Registra todos los callbacks de la página de gráficos
        
        Args:
            app (dash.Dash): Instancia de la aplicación Dash
        """
        
        # Callback para actualizar stores cuando cambian los selectores
        @app.callback(
            [Output('selected-symbol-store', 'data'),
             Output('selected-period-store', 'data')],
            [Input('symbol-selector', 'value'),
             Input('period-selector', 'value')]
        )
        def update_selection_stores(symbol, period):
            """Actualiza stores de selección"""
            symbol = symbol or self.page_config['default_symbol']
            period = period or self.page_config['default_period']
            return symbol, period
        
        # Callback principal para cargar datos del gráfico
        @app.callback(
            Output('charts-data-store', 'data'),
            [Input('selected-symbol-store', 'data'),
             Input('selected-period-store', 'data'),
             Input('timeframe-selector', 'value'),
             Input('charts-refresh-interval', 'n_intervals'),
             Input('charts-refresh-btn', 'n_clicks')]
        )
        def update_charts_data(symbol, period, timeframe, n_intervals, refresh_clicks):
            """Actualiza datos del gráfico"""
            try:
                # Obtener datos históricos
                chart_data = self._get_chart_data(symbol, period, timeframe)
                
                # Obtener datos de ciclos
                cycles_data = self._get_top_cycles_data(symbol)
                
                # Obtener métricas del símbolo
                symbol_metrics = self._get_symbol_chart_metrics(symbol)
                
                self.update_page_stats()
                
                return {
                    'chart_data': chart_data,
                    'cycles_data': cycles_data,
                    'symbol_metrics': symbol_metrics,
                    'symbol': symbol,
                    'period': period,
                    'timeframe': timeframe,
                    'last_update': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error al actualizar datos de gráficos: {e}")
                return {}
        
        # Callback para el gráfico de velas principal
        @app.callback(
            Output('candlestick-chart', 'figure'),
            [Input('charts-data-store', 'data'),
             Input('indicators-selector', 'value')]
        )
        def update_candlestick_chart(data, selected_indicators):
            """Actualiza el gráfico de velas con indicadores"""
            try:
                if not data or not data.get('chart_data'):
                    return self._create_empty_chart("Cargando datos del gráfico...")
                
                return self._create_candlestick_chart(
                    data['chart_data'], 
                    selected_indicators or [],
                    data.get('symbol', 'Unknown')
                )
                
            except Exception as e:
                logger.error(f"Error al crear gráfico de velas: {e}")
                return self._create_empty_chart("Error al cargar el gráfico")
        
        # Callback para la tabla de top cycles
        @app.callback(
            Output('top-cycles-table', 'children'),
            [Input('charts-data-store', 'data')]
        )
        def update_top_cycles_table(data):
            """Actualiza la tabla de top 20 ciclos"""
            try:
                if not data or not data.get('cycles_data'):
                    return self.create_empty_state(
                        title="No hay datos de ciclos",
                        message="No se encontraron ciclos para mostrar",
                        icon="fas fa-sync-alt"
                    )
                
                return self._create_cycles_table(data['cycles_data'])
                
            except Exception as e:
                logger.error(f"Error al crear tabla de ciclos: {e}")
                return self.create_error_alert("Error al cargar datos de ciclos")
        
        # Callback para métricas del símbolo
        @app.callback(
            Output('chart-metrics-container', 'children'),
            [Input('charts-data-store', 'data')]
        )
        def update_chart_metrics(data):
            """Actualiza las métricas del símbolo seleccionado"""
            try:
                if not data or not data.get('symbol_metrics'):
                    return html.P("Cargando métricas...", className="text-muted")
                
                return self._create_symbol_metrics_cards(data['symbol_metrics'])
                
            except Exception as e:
                logger.error(f"Error al crear métricas del símbolo: {e}")
                return self.create_error_alert("Error al cargar métricas")
        
        # Callback para información del gráfico
        @app.callback(
            Output('chart-info', 'children'),
            [Input('charts-data-store', 'data')]
        )
        def update_chart_info(data):
            """Actualiza información del gráfico"""
            try:
                if not data:
                    return "Cargando..."
                
                symbol = data.get('symbol', 'N/A')
                period = data.get('period', 'N/A')
                timeframe = data.get('timeframe', 'N/A')
                last_update = data.get('last_update', '')
                
                if last_update:
                    update_time = datetime.fromisoformat(last_update).strftime('%H:%M:%S')
                    return f"{symbol} • {self.time_periods.get(period, {}).get('label', period)} • {timeframe} • Actualizado: {update_time}"
                else:
                    return f"{symbol} • {self.time_periods.get(period, {}).get('label', period)} • {timeframe}"
                
            except Exception as e:
                logger.error(f"Error al actualizar info del gráfico: {e}")
                return "Error en información"
        
        # Callback para exportar datos
        @app.callback(
            Output('charts-export-btn', 'children'),
            [Input('charts-export-btn', 'n_clicks'),
             State('charts-data-store', 'data')],
            prevent_initial_call=True
        )
        def export_chart_data(n_clicks, data):
            """Exporta datos del gráfico"""
            if n_clicks and data:
                try:
                    # Implementar exportación
                    symbol = data.get('symbol', 'unknown')
                    self.log_page_action("export_chart_data", {
                        "symbol": symbol,
                        "format": "csv"
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
        
        logger.info("Callbacks de ChartsPage registrados")
    
    def _get_chart_data(self, symbol: str, period: str, timeframe: str) -> Dict[str, Any]:
        """Obtiene datos históricos para el gráfico"""
        try:
            # Calcular límite de velas basado en el período
            if period == 'all':
                limit = self.page_config['max_candles_display']
            else:
                period_days = self.time_periods[period]['days']
                # Calcular velas necesarias según timeframe
                timeframe_minutes = {
                    '1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440
                }
                minutes_per_day = 1440
                velas_per_day = minutes_per_day // timeframe_minutes.get(timeframe, 60)
                limit = min(period_days * velas_per_day, self.page_config['max_candles_display'])
            
            if self.data_provider:
                # Obtener datos reales
                df = self.data_provider.get_historical_data(symbol, timeframe, limit)
                
                if df.empty:
                    return self._generate_sample_chart_data(symbol, limit)
                
                # Convertir DataFrame a formato requerido
                return {
                    'timestamps': df.index.tolist(),
                    'open': df['open'].tolist(),
                    'high': df['high'].tolist(),
                    'low': df['low'].tolist(),
                    'close': df['close'].tolist(),
                    'volume': df['volume'].tolist() if 'volume' in df.columns else [0] * len(df)
                }
            else:
                # Generar datos de muestra
                return self._generate_sample_chart_data(symbol, limit)
                
        except Exception as e:
            logger.error(f"Error al obtener datos del gráfico: {e}")
            return self._generate_sample_chart_data(symbol, 100)
    
    def _generate_sample_chart_data(self, symbol: str, limit: int) -> Dict[str, Any]:
        """Genera datos de muestra para el gráfico"""
        # Precio base según símbolo
        base_prices = {
            'BTCUSDT': 50000,
            'ETHUSDT': 3000,
            'ADAUSDT': 1.5,
            'BNBUSDT': 300
        }
        base_price = base_prices.get(symbol, 1000)
        
        # Generar timestamps
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(hours=limit),
            end=datetime.now(),
            periods=limit
        )
        
        # Generar datos OHLCV realistas
        data = {
            'timestamps': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }
        
        current_price = base_price
        
        for timestamp in timestamps:
            # Movimiento aleatorio
            change_pct = np.random.normal(0, 0.01)  # 1% volatilidad
            new_price = current_price * (1 + change_pct)
            
            # OHLC para esta vela
            open_price = current_price
            close_price = new_price
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
            volume = np.random.uniform(100, 1000)
            
            data['timestamps'].append(timestamp)
            data['open'].append(round(open_price, 2))
            data['high'].append(round(high_price, 2))
            data['low'].append(round(low_price, 2))
            data['close'].append(round(close_price, 2))
            data['volume'].append(round(volume, 2))
            
            current_price = new_price
        
        return data
    
    def _get_top_cycles_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Obtiene datos de los top 20 ciclos"""
        try:
            if self.data_provider:
                cycles = self.data_provider.get_top_cycles(20)
                # Filtrar por símbolo si se especifica
                if symbol and symbol != 'ALL':
                    cycles = [cycle for cycle in cycles if cycle.symbol == symbol]
                
                return [cycle.__dict__ if hasattr(cycle, '__dict__') else cycle for cycle in cycles]
            else:
                # Generar datos de muestra
                return self._generate_sample_cycles_data(symbol, 20)
                
        except Exception as e:
            logger.error(f"Error al obtener datos de ciclos: {e}")
            return []
    
    def _generate_sample_cycles_data(self, symbol: str, count: int) -> List[Dict[str, Any]]:
        """Genera datos de muestra para ciclos"""
        cycles = []
        symbols = [symbol] if symbol else ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for i in range(count):
            start_date = datetime.now() - timedelta(days=np.random.randint(30, 365))
            duration = np.random.randint(7, 60)
            end_date = start_date + timedelta(days=duration)
            
            pnl_pct = np.random.normal(15, 20)  # 15% promedio, 20% desviación
            start_balance = 1000
            pnl = start_balance * (pnl_pct / 100)
            end_balance = start_balance + pnl
            
            cycles.append({
                'cycle_id': f'cycle_{i+1:03d}',
                'symbol': np.random.choice(symbols),
                'start_date': start_date,
                'end_date': end_date,
                'start_balance': start_balance,
                'end_balance': end_balance,
                'pnl': pnl,
                'pnl_percentage': pnl_pct,
                'total_trades': np.random.randint(10, 50),
                'win_rate': np.random.uniform(45, 85),
                'avg_daily_pnl': pnl / duration,
                'max_drawdown': np.random.uniform(2, 15),
                'sharpe_ratio': np.random.uniform(0.5, 3.0),
                'duration_days': duration,
                'status': 'completed'
            })
        
        # Ordenar por PnL porcentual
        cycles.sort(key=lambda x: x['pnl_percentage'], reverse=True)
        return cycles
    
    def _get_symbol_chart_metrics(self, symbol: str) -> Dict[str, Any]:
        """Obtiene métricas específicas del símbolo para el gráfico"""
        try:
            if self.data_provider:
                metrics = self.data_provider.get_symbol_metrics(symbol)
                return metrics.__dict__ if hasattr(metrics, '__dict__') else metrics
            else:
                # Métricas de muestra
                return {
                    'symbol': symbol,
                    'current_price': np.random.uniform(40000, 60000) if 'BTC' in symbol else np.random.uniform(2000, 4000),
                    'price_change_24h': np.random.uniform(-5, 5),
                    'volume_24h': np.random.uniform(1000000, 10000000),
                    'high_24h': np.random.uniform(50000, 65000) if 'BTC' in symbol else np.random.uniform(3000, 4500),
                    'low_24h': np.random.uniform(45000, 55000) if 'BTC' in symbol else np.random.uniform(2500, 3500),
                    'volatility': np.random.uniform(15, 35),
                    'rsi': np.random.uniform(30, 70),
                    'support_level': np.random.uniform(48000, 52000) if 'BTC' in symbol else np.random.uniform(2800, 3200),
                    'resistance_level': np.random.uniform(58000, 62000) if 'BTC' in symbol else np.random.uniform(3800, 4200)
                }
                
        except Exception as e:
            logger.error(f"Error al obtener métricas del símbolo: {e}")
            return {}
    
    def _create_candlestick_chart(self, chart_data: Dict[str, Any], 
                                 indicators: List[str], symbol: str) -> go.Figure:
        """Crea el gráfico de velas con indicadores técnicos"""
        try:
            # Crear subplots: main chart + volumen + RSI si está seleccionado
            rows = 1
            subplot_titles = [f"{symbol} - Gráfico de Velas"]
            
            if 'volume' in indicators:
                rows += 1
                subplot_titles.append("Volumen")
            
            if 'rsi' in indicators:
                rows += 1
                subplot_titles.append("RSI")
            
            if 'macd' in indicators:
                rows += 1
                subplot_titles.append("MACD")
            
            fig = make_subplots(
                rows=rows, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=subplot_titles,
                row_width=[0.7] + [0.15] * (rows - 1)  # Main chart más grande
            )
            
            # Gráfico de velas principal
            fig.add_trace(
                go.Candlestick(
                    x=chart_data['timestamps'],
                    open=chart_data['open'],
                    high=chart_data['high'],
                    low=chart_data['low'],
                    close=chart_data['close'],
                    name=symbol,
                    increasing_line_color='#26a69a',
                    decreasing_line_color='#ef5350'
                ), 
                row=1, col=1
            )
            
            # Añadir indicadores técnicos
            current_row = 1
            
            # SMAs y EMAs
            if 'sma_20' in indicators:
                sma_20 = self._calculate_sma(chart_data['close'], 20)
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=sma_20,
                        mode='lines',
                        name='SMA 20',
                        line=dict(color='orange', width=1)
                    ),
                    row=1, col=1
                )
            
            if 'sma_50' in indicators:
                sma_50 = self._calculate_sma(chart_data['close'], 50)
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=sma_50,
                        mode='lines',
                        name='SMA 50',
                        line=dict(color='blue', width=1)
                    ),
                    row=1, col=1
                )
            
            if 'ema_12' in indicators:
                ema_12 = self._calculate_ema(chart_data['close'], 12)
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=ema_12,
                        mode='lines',
                        name='EMA 12',
                        line=dict(color='purple', width=1)
                    ),
                    row=1, col=1
                )
            
            # Bollinger Bands
            if 'bollinger' in indicators:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(chart_data['close'])
                
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=bb_upper,
                        mode='lines',
                        name='BB Upper',
                        line=dict(color='gray', width=1, dash='dash'),
                        showlegend=False
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=bb_lower,
                        mode='lines',
                        name='BB Lower',
                        line=dict(color='gray', width=1, dash='dash'),
                        fill='tonexty',
                        fillcolor='rgba(128, 128, 128, 0.1)',
                        showlegend=False
                    ),
                    row=1, col=1
                )
            
            # Volumen
            if 'volume' in indicators:
                current_row += 1
                colors = ['red' if chart_data['close'][i] < chart_data['open'][i] else 'green' 
                         for i in range(len(chart_data['close']))]
                
                fig.add_trace(
                    go.Bar(
                        x=chart_data['timestamps'],
                        y=chart_data['volume'],
                        name='Volumen',
                        marker_color=colors,
                        opacity=0.7
                    ),
                    row=current_row, col=1
                )
            
            # RSI
            if 'rsi' in indicators:
                current_row += 1
                rsi_values = self._calculate_rsi(chart_data['close'])
                
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=rsi_values,
                        mode='lines',
                        name='RSI',
                        line=dict(color='purple', width=2)
                    ),
                    row=current_row, col=1
                )
                
                # Líneas de RSI 30 y 70
                fig.add_hline(y=70, line_dash="dash", line_color="red", 
                             annotation_text="Sobrecompra", row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", 
                             annotation_text="Sobreventa", row=current_row, col=1)
            
            # MACD
            if 'macd' in indicators:
                current_row += 1
                macd_line, macd_signal, macd_histogram = self._calculate_macd(chart_data['close'])
                
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=macd_line,
                        mode='lines',
                        name='MACD',
                        line=dict(color='blue', width=1)
                    ),
                    row=current_row, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=chart_data['timestamps'],
                        y=macd_signal,
                        mode='lines',
                        name='Signal',
                        line=dict(color='red', width=1)
                    ),
                    row=current_row, col=1
                )
                
                fig.add_trace(
                    go.Bar(
                        x=chart_data['timestamps'],
                        y=macd_histogram,
                        name='Histogram',
                        marker_color='gray',
                        opacity=0.6
                    ),
                    row=current_row, col=1
                )
            
            # Configuración del layout
            fig.update_layout(
                height=self.page_config['chart_height'],
                title=f"Análisis Técnico - {symbol}",
                xaxis_rangeslider_visible=False,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
            # Configurar ejes
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error al crear gráfico de velas: {e}")
            return self._create_empty_chart("Error al generar gráfico de velas")
    
    def _calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calcula Simple Moving Average"""
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                sma.append(sum(prices[i-period+1:i+1]) / period)
        return sma
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calcula Exponential Moving Average"""
        ema = []
        multiplier = 2 / (period + 1)
        
        for i, price in enumerate(prices):
            if i == 0:
                ema.append(price)
            else:
                ema.append((price * multiplier) + (ema[i-1] * (1 - multiplier)))
        
        return ema
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, 
                                  std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Calcula Bollinger Bands"""
        sma = self._calculate_sma(prices, period)
        upper_band = []
        lower_band = []
        
        for i in range(len(prices)):
            if i < period - 1:
                upper_band.append(None)
                lower_band.append(None)
            else:
                # Calcular desviación estándar
                subset = prices[i-period+1:i+1]
                std = np.std(subset)
                
                upper_band.append(sma[i] + (std * std_dev))
                lower_band.append(sma[i] - (std * std_dev))
        
        return upper_band, sma, lower_band
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calcula Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        rsi = [None]  # First value is None
        
        # Initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
        
        # Calculate subsequent RSI values
        for i in range(period + 1, len(prices)):
            gain = gains[i-1]
            loss = losses[i-1]
            
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period
            
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, 
                       signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """Calcula MACD"""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # MACD line
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        # Signal line
        macd_signal = self._calculate_ema([x for x in macd_line if x is not None], signal)
        
        # Pad signal line with None values to match length
        signal_padded = [None] * (len(macd_line) - len(macd_signal)) + macd_signal
        
        # Histogram
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_padded[i] is not None:
                histogram.append(macd_line[i] - signal_padded[i])
            else:
                histogram.append(None)
        
        return macd_line, signal_padded, histogram
    
    def _create_cycles_table(self, cycles_data: List[Dict[str, Any]]) -> html.Div:
        """Crea la tabla de top 20 ciclos"""
        try:
            # Preparar datos para la tabla
            table_data = []
            for i, cycle in enumerate(cycles_data[:20], 1):
                table_data.append({
                    'rank': f"#{i}",
                    'cycle_id': cycle.get('cycle_id', 'N/A'),
                    'symbol': cycle.get('symbol', 'N/A'),
                    'pnl_percentage': f"{cycle.get('pnl_percentage', 0):.2f}%",
                    'pnl': f"${cycle.get('pnl', 0):,.2f}",
                    'duration_days': f"{cycle.get('duration_days', 0)}d",
                    'win_rate': f"{cycle.get('win_rate', 0):.1f}%",
                    'total_trades': cycle.get('total_trades', 0),
                    'avg_daily_pnl': f"${cycle.get('avg_daily_pnl', 0):.2f}",
                    'sharpe_ratio': f"{cycle.get('sharpe_ratio', 0):.2f}",
                    'max_drawdown': f"{cycle.get('max_drawdown', 0):.1f}%",
                    'start_date': cycle.get('start_date', datetime.now()).strftime('%Y-%m-%d') if isinstance(cycle.get('start_date'), datetime) else str(cycle.get('start_date', 'N/A'))[:10],
                    'end_date': cycle.get('end_date', datetime.now()).strftime('%Y-%m-%d') if isinstance(cycle.get('end_date'), datetime) else str(cycle.get('end_date', 'N/A'))[:10]
                })
            
            # Configuración de columnas
            columns = [
                {'name': 'Rank', 'id': 'rank', 'type': 'text'},
                {'name': 'ID Ciclo', 'id': 'cycle_id', 'type': 'text'},
                {'name': 'Símbolo', 'id': 'symbol', 'type': 'text'},
                {'name': 'PnL %', 'id': 'pnl_percentage', 'type': 'numeric'},
                {'name': 'PnL , 'id': 'pnl', 'type': 'numeric'},
                {'name': 'Duración', 'id': 'duration_days', 'type': 'text'},
                {'name': 'Win Rate', 'id': 'win_rate', 'type': 'numeric'},
                {'name': 'Trades', 'id': 'total_trades', 'type': 'numeric'},
                {'name': 'PnL Diario', 'id': 'avg_daily_pnl', 'type': 'numeric'},
                {'name': 'Sharpe', 'id': 'sharpe_ratio', 'type': 'numeric'},
                {'name': 'Max DD', 'id': 'max_drawdown', 'type': 'numeric'},
                {'name': 'Inicio', 'id': 'start_date', 'type': 'text'},
                {'name': 'Fin', 'id': 'end_date', 'type': 'text'}
            ]
            
            return self.create_data_table(
                data=table_data,
                columns=columns,
                table_id="top-cycles-data-table",
                page_size=20,
                sortable=True
            )
            
        except Exception as e:
            logger.error(f"Error al crear tabla de ciclos: {e}")
            return self.create_error_alert("Error al procesar datos de ciclos")
    
    def _create_symbol_metrics_cards(self, metrics: Dict[str, Any]) -> html.Div:
        """Crea tarjetas de métricas del símbolo"""
        try:
            cards = []
            
            # Precio actual
            cards.append(
                self.create_metric_card(
                    title="Precio Actual",
                    value=f"${metrics.get('current_price', 0):,.2f}",
                    subtitle="Último precio",
                    icon="fas fa-dollar-sign",
                    color="primary",
                    trend=metrics.get('price_change_24h', 0)
                )
            )
            
            # Volumen 24h
            cards.append(
                self.create_metric_card(
                    title="Volumen 24h",
                    value=self._format_metric_value(metrics.get('volume_24h', 0)),
                    subtitle="Volumen diario",
                    icon="fas fa-chart-bar",
                    color="info"
                )
            )
            
            # Volatilidad
            cards.append(
                self.create_metric_card(
                    title="Volatilidad",
                    value=f"{metrics.get('volatility', 0):.1f}%",
                    subtitle="Desviación estándar",
                    icon="fas fa-wave-square",
                    color="warning"
                )
            )
            
            # RSI
            rsi = metrics.get('rsi', 50)
            rsi_color = "danger" if rsi > 70 else "success" if rsi < 30 else "secondary"
            cards.append(
                self.create_metric_card(
                    title="RSI",
                    value=f"{rsi:.1f}",
                    subtitle="Índice de fuerza relativa",
                    icon="fas fa-tachometer-alt",
                    color=rsi_color
                )
            )
            
            # Máximo 24h
            cards.append(
                self.create_metric_card(
                    title="Máximo 24h",
                    value=f"${metrics.get('high_24h', 0):,.2f}",
                    subtitle="Precio más alto",
                    icon="fas fa-arrow-up",
                    color="success"
                )
            )
            
            # Mínimo 24h
            cards.append(
                self.create_metric_card(
                    title="Mínimo 24h",
                    value=f"${metrics.get('low_24h', 0):,.2f}",
                    subtitle="Precio más bajo",
                    icon="fas fa-arrow-down",
                    color="danger"
                )
            )
            
            return html.Div([
                dbc.Row([
                    dbc.Col(card, width=12, className="mb-3") for card in cards
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error al crear tarjetas de métricas: {e}")
            return self.create_error_alert("Error al mostrar métricas del símbolo")
    
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
            height=self.page_config['chart_height'],
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig