"""
monitoring/chart_components.py
ENHANCED VERSION 2.0 - Componentes de gráficos avanzados para el dashboard
Funcionalidades mejoradas:
- Visualización avanzada de runs y ciclos de trading
- Gráficos interactivos de performance temporal
- Análisis visual de patrones de trading
- Heatmaps de performance por timeframes
- Gráficos 3D de correlaciones de mercado
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class EnhancedChartComponents:
    """Componentes de gráficos avanzados para el dashboard"""
    
    def __init__(self):
        self.theme_colors = {
            'primary': '#0d1117',      # GitHub dark
            'secondary': '#161b22',    # Más oscuro
            'surface': '#21262d',      # Superficie
            'accent': '#58a6ff',       # Azul moderno
            'success': '#3fb950',      # Verde éxito
            'danger': '#f85149',       # Rojo peligro
            'warning': '#d29922',      # Amarillo advertencia
            'info': '#79c0ff',         # Info azul claro
            'text_primary': '#f0f6fc', # Texto principal
            'text_secondary': '#8b949e', # Texto secundario
            'grid': '#30363d',         # Líneas de grid
            'border': '#21262d'        # Bordes
        }
        
        # Template moderno para todos los gráficos
        self.modern_template = {
            'layout': {
                'plot_bgcolor': self.theme_colors['primary'],
                'paper_bgcolor': self.theme_colors['primary'],
                'font': {
                    'family': "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                    'color': self.theme_colors['text_primary'],
                    'size': 12
                },
                'colorway': [
                    self.theme_colors['accent'], 
                    self.theme_colors['success'], 
                    self.theme_colors['danger'],
                    self.theme_colors['warning'], 
                    self.theme_colors['info']
                ],
                'xaxis': {
                    'gridcolor': self.theme_colors['grid'],
                    'linecolor': self.theme_colors['border'],
                    'zerolinecolor': self.theme_colors['grid'],
                    'tickcolor': self.theme_colors['text_secondary']
                },
                'yaxis': {
                    'gridcolor': self.theme_colors['grid'],
                    'linecolor': self.theme_colors['border'],
                    'zerolinecolor': self.theme_colors['grid'],
                    'tickcolor': self.theme_colors['text_secondary']
                },
                'margin': {'t': 40, 'l': 60, 'r': 20, 'b': 40},
                'showlegend': True,
                'legend': {
                    'bgcolor': 'rgba(0,0,0,0)',
                    'bordercolor': self.theme_colors['border']
                }
            }
        }
    
    def create_runs_overview_chart(self, data: Dict[str, Any]) -> go.Figure:
        """
        Crea un gráfico avanzado de overview de runs/ciclos
        Muestra múltiples métricas en un solo gráfico interactivo
        """
        try:
            if not data or 'cycles' not in data:
                return self._create_empty_chart("No hay datos de runs disponibles")
            
            cycles_data = data['cycles']
            
            # Crear subplots con múltiples ejes Y
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    'P&L por Run', 'Accuracy del Modelo',
                    'Duración vs Rentabilidad', 'Distribución de Trades',
                    'Performance Timeline', 'Risk Metrics'
                ],
                specs=[
                    [{"secondary_y": True}, {"secondary_y": False}],
                    [{"secondary_y": False}, {"type": "pie"}],
                    [{"colspan": 2, "secondary_y": True}, None]
                ],
                vertical_spacing=0.08,
                horizontal_spacing=0.1
            )
            
            # 1. P&L por Run con volumen
            if 'pnl_by_run' in cycles_data:
                pnl_data = cycles_data['pnl_by_run']
                
                # Barras de P&L
                colors = [self.theme_colors['success'] if x > 0 else self.theme_colors['danger'] for x in pnl_data['values']]
                fig.add_trace(
                    go.Bar(
                        x=pnl_data['run_ids'],
                        y=pnl_data['values'],
                        name='P&L por Run',
                        marker_color=colors,
                        opacity=0.8,
                        hovertemplate='<b>Run %{x}</b><br>P&L: $%{y:.2f}<br><extra></extra>'
                    ),
                    row=1, col=1
                )
                
                # Línea de P&L acumulado
                cumulative_pnl = np.cumsum(pnl_data['values'])
                fig.add_trace(
                    go.Scatter(
                        x=pnl_data['run_ids'],
                        y=cumulative_pnl,
                        mode='lines+markers',
                        name='P&L Acumulado',
                        line=dict(color=self.theme_colors['accent'], width=3),
                        marker=dict(size=6),
                        yaxis='y2'
                    ),
                    row=1, col=1, secondary_y=True
                )
            
            # 2. Accuracy del modelo con intervalos de confianza
            if 'model_accuracy' in cycles_data:
                acc_data = cycles_data['model_accuracy']
                
                # Línea principal de accuracy
                fig.add_trace(
                    go.Scatter(
                        x=acc_data['timestamps'],
                        y=acc_data['accuracy'],
                        mode='lines+markers',
                        name='Accuracy',
                        line=dict(color=self.theme_colors['success'], width=2),
                        marker=dict(size=5),
                        fill=None
                    ),
                    row=1, col=2
                )
                
                # Banda de confianza
                if 'confidence_lower' in acc_data and 'confidence_upper' in acc_data:
                    fig.add_trace(
                        go.Scatter(
                            x=acc_data['timestamps'] + acc_data['timestamps'][::-1],
                            y=acc_data['confidence_upper'] + acc_data['confidence_lower'][::-1],
                            fill='toself',
                            fillcolor=f'rgba(63, 185, 80, 0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='Intervalo de Confianza',
                            showlegend=False
                        ),
                        row=1, col=2
                    )
            
            # 3. Scatter: Duración vs Rentabilidad
            if 'duration_vs_profit' in cycles_data:
                dvp_data = cycles_data['duration_vs_profit']
                
                # Tamaño basado en número de trades
                sizes = [max(10, min(50, x*2)) for x in dvp_data.get('num_trades', [20]*len(dvp_data['duration']))]
                
                fig.add_trace(
                    go.Scatter(
                        x=dvp_data['duration'],
                        y=dvp_data['profit'],
                        mode='markers',
                        name='Runs',
                        marker=dict(
                            size=sizes,
                            color=dvp_data['profit'],
                            colorscale='RdYlGn',
                            showscale=True,
                            colorbar=dict(title="Profit $", len=0.3, y=0.5),
                            line=dict(width=1, color=self.theme_colors['border'])
                        ),
                        hovertemplate='<b>Duración:</b> %{x:.1f}h<br><b>Profit:</b> $%{y:.2f}<br><extra></extra>'
                    ),
                    row=2, col=1
                )
            
            # 4. Pie chart de distribución de trades
            if 'trade_distribution' in cycles_data:
                dist_data = cycles_data['trade_distribution']
                
                fig.add_trace(
                    go.Pie(
                        labels=dist_data['types'],
                        values=dist_data['counts'],
                        name="Trade Types",
                        hole=.3,
                        marker_colors=[
                            self.theme_colors['success'],
                            self.theme_colors['danger'],
                            self.theme_colors['warning'],
                            self.theme_colors['info']
                        ],
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<br><extra></extra>'
                    ),
                    row=2, col=2
                )
            
            # 5. Timeline de performance (gráfico combinado)
            if 'timeline_performance' in cycles_data:
                timeline_data = cycles_data['timeline_performance']
                
                # Equity curve
                fig.add_trace(
                    go.Scatter(
                        x=timeline_data['timestamps'],
                        y=timeline_data['equity'],
                        mode='lines',
                        name='Equity Curve',
                        line=dict(color=self.theme_colors['accent'], width=2),
                        fill='tonexty',
                        fillcolor=f"rgba(88, 166, 255, 0.1)"
                    ),
                    row=3, col=1
                )
                
                # Drawdown
                fig.add_trace(
                    go.Scatter(
                        x=timeline_data['timestamps'],
                        y=timeline_data['drawdown'],
                        mode='lines',
                        name='Drawdown',
                        line=dict(color=self.theme_colors['danger'], width=1, dash='dot'),
                        yaxis='y6'
                    ),
                    row=3, col=1, secondary_y=True
                )
                
                # Marcar trades importantes
                if 'major_trades' in timeline_data:
                    major_trades = timeline_data['major_trades']
                    fig.add_trace(
                        go.Scatter(
                            x=major_trades['timestamps'],
                            y=major_trades['equity_at_trade'],
                            mode='markers',
                            name='Major Trades',
                            marker=dict(
                                symbol='diamond',
                                size=10,
                                color=self.theme_colors['warning'],
                                line=dict(width=2, color=self.theme_colors['primary'])
                            ),
                            hovertemplate='<b>Major Trade</b><br>Time: %{x}<br>Equity: $%{y:.2f}<br><extra></extra>'
                        ),
                        row=3, col=1
                    )
            
            # Actualizar layout general
            fig.update_layout(
                **self.modern_template['layout'],
                title={
                    'text': '<b>Trading Runs - Dashboard Avanzado</b>',
                    'x': 0.5,
                    'font': {'size': 18, 'color': self.theme_colors['text_primary']}
                },
                height=900,
                showlegend=True
            )
            
            # Configurar ejes específicos
            fig.update_xaxes(title_text="Run ID", row=1, col=1)
            fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
            fig.update_yaxes(title_text="P&L Acumulado ($)", secondary_y=True, row=1, col=1)
            
            fig.update_xaxes(title_text="Tiempo", row=1, col=2)
            fig.update_yaxes(title_text="Accuracy (%)", row=1, col=2)
            
            fig.update_xaxes(title_text="Duración (horas)", row=2, col=1)
            fig.update_yaxes(title_text="Profit ($)", row=2, col=1)
            
            fig.update_xaxes(title_text="Tiempo", row=3, col=1)
            fig.update_yaxes(title_text="Equity ($)", row=3, col=1)
            fig.update_yaxes(title_text="Drawdown (%)", secondary_y=True, row=3, col=1)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de runs overview: {e}")
            return self._create_empty_chart("Error al cargar datos de runs")
    
    def create_real_time_trading_chart(self, data: Dict[str, Any]) -> go.Figure:
        """
        Crea un gráfico de trading en tiempo real con múltiples indicadores
        """
        try:
            if not data or 'price_data' not in data:
                return self._create_empty_chart("No hay datos de precio en tiempo real")
            
            price_data = data['price_data']
            
            # Crear subplot con indicadores secundarios
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_width=[0.6, 0.15, 0.15, 0.1],
                subplot_titles=['Precio y Señales', 'Volumen', 'RSI', 'MACD']
            )
            
            # 1. Candlestick chart principal
            if 'ohlcv' in price_data:
                ohlcv = price_data['ohlcv']
                
                fig.add_trace(
                    go.Candlestick(
                        x=ohlcv['timestamp'],
                        open=ohlcv['open'],
                        high=ohlcv['high'],
                        low=ohlcv['low'],
                        close=ohlcv['close'],
                        name='Precio',
                        increasing_line_color=self.theme_colors['success'],
                        decreasing_line_color=self.theme_colors['danger']
                    ),
                    row=1, col=1
                )
                
                # Media móvil exponencial
                if 'ema' in price_data:
                    for period, ema_data in price_data['ema'].items():
                        fig.add_trace(
                            go.Scatter(
                                x=ohlcv['timestamp'],
                                y=ema_data,
                                mode='lines',
                                name=f'EMA {period}',
                                line=dict(width=1),
                                opacity=0.7
                            ),
                            row=1, col=1
                        )
                
                # Señales de trading
                if 'signals' in data:
                    signals = data['signals']
                    
                    # Señales de compra
                    if 'buy_signals' in signals:
                        buy_signals = signals['buy_signals']
                        fig.add_trace(
                            go.Scatter(
                                x=buy_signals['timestamp'],
                                y=buy_signals['price'],
                                mode='markers',
                                name='Buy Signal',
                                marker=dict(
                                    symbol='triangle-up',
                                    size=12,
                                    color=self.theme_colors['success'],
                                    line=dict(width=2, color=self.theme_colors['primary'])
                                ),
                                hovertemplate='<b>BUY</b><br>Time: %{x}<br>Price: $%{y:.4f}<br><extra></extra>'
                            ),
                            row=1, col=1
                        )
                    
                    # Señales de venta
                    if 'sell_signals' in signals:
                        sell_signals = signals['sell_signals']
                        fig.add_trace(
                            go.Scatter(
                                x=sell_signals['timestamp'],
                                y=sell_signals['price'],
                                mode='markers',
                                name='Sell Signal',
                                marker=dict(
                                    symbol='triangle-down',
                                    size=12,
                                    color=self.theme_colors['danger'],
                                    line=dict(width=2, color=self.theme_colors['primary'])
                                ),
                                hovertemplate='<b>SELL</b><br>Time: %{x}<br>Price: $%{y:.4f}<br><extra></extra>'
                            ),
                            row=1, col=1
                        )
            
            # 2. Volumen
            if 'volume' in price_data:
                volume_data = price_data['volume']
                colors = [self.theme_colors['success'] if c >= o else self.theme_colors['danger'] 
                         for c, o in zip(ohlcv['close'], ohlcv['open'])]
                
                fig.add_trace(
                    go.Bar(
                        x=ohlcv['timestamp'],
                        y=volume_data,
                        name='Volumen',
                        marker_color=colors,
                        opacity=0.6,
                        showlegend=False
                    ),
                    row=2, col=1
                )
            
            # 3. RSI
            if 'rsi' in price_data:
                rsi_data = price_data['rsi']
                
                fig.add_trace(
                    go.Scatter(
                        x=ohlcv['timestamp'],
                        y=rsi_data,
                        mode='lines',
                        name='RSI',
                        line=dict(color=self.theme_colors['info'], width=2),
                        showlegend=False
                    ),
                    row=3, col=1
                )
                
                # Líneas de sobrecompra/sobreventa
                fig.add_hline(y=70, line_dash="dash", line_color=self.theme_colors['danger'], 
                             opacity=0.5, row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color=self.theme_colors['success'], 
                             opacity=0.5, row=3, col=1)
            
            # 4. MACD
            if 'macd' in price_data:
                macd_data = price_data['macd']
                
                # MACD línea
                fig.add_trace(
                    go.Scatter(
                        x=ohlcv['timestamp'],
                        y=macd_data['macd'],
                        mode='lines',
                        name='MACD',
                        line=dict(color=self.theme_colors['accent'], width=2),
                        showlegend=False
                    ),
                    row=4, col=1
                )
                
                # Signal línea
                fig.add_trace(
                    go.Scatter(
                        x=ohlcv['timestamp'],
                        y=macd_data['signal'],
                        mode='lines',
                        name='Signal',
                        line=dict(color=self.theme_colors['warning'], width=1),
                        showlegend=False
                    ),
                    row=4, col=1
                )
                
                # Histograma
                colors = [self.theme_colors['success'] if x > 0 else self.theme_colors['danger'] 
                         for x in macd_data['histogram']]
                fig.add_trace(
                    go.Bar(
                        x=ohlcv['timestamp'],
                        y=macd_data['histogram'],
                        name='MACD Hist',
                        marker_color=colors,
                        opacity=0.6,
                        showlegend=False
                    ),
                    row=4, col=1
                )
            
            # Layout final
            fig.update_layout(
                **self.modern_template['layout'],
                title={
                    'text': '<b>Trading en Tiempo Real - Análisis Técnico</b>',
                    'x': 0.5,
                    'font': {'size': 18}
                },
                height=800,
                xaxis4_title="Tiempo",
                yaxis_title="Precio ($)",
                yaxis2_title="Volumen",
                yaxis3_title="RSI",
                yaxis4_title="MACD"
            )
            
            # Remover selector de rango para tiempo real
            fig.update_layout(xaxis_rangeslider_visible=False)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de trading en tiempo real: {e}")
            return self._create_empty_chart("Error al cargar datos de trading")
    
    def create_performance_heatmap(self, data: Dict[str, Any]) -> go.Figure:
        """
        Crea un heatmap de performance por horas del día y días de la semana
        """
        try:
            if not data or 'performance_matrix' not in data:
                return self._create_empty_chart("No hay datos de performance por tiempo")
            
            perf_matrix = data['performance_matrix']
            
            # Datos de ejemplo si no están disponibles
            if 'hourly_daily_pnl' not in perf_matrix:
                # Generar datos de ejemplo
                hours = list(range(24))
                days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                
                # Matriz de P&L simulada con patrones realistas
                np.random.seed(42)
                pnl_matrix = np.random.normal(0, 50, (len(days), len(hours)))
                
                # Patrones: mejor performance en horarios de mercado
                for i, day in enumerate(days):
                    if day in ['Sáb', 'Dom']:  # Fines de semana menos volátiles
                        pnl_matrix[i] *= 0.3
                    for j, hour in enumerate(hours):
                        if 9 <= hour <= 16:  # Horario de mercado
                            pnl_matrix[i][j] *= 1.5
                        elif 22 <= hour or hour <= 2:  # Mercado asiático
                            pnl_matrix[i][j] *= 1.2
            else:
                pnl_matrix = perf_matrix['hourly_daily_pnl']
                days = perf_matrix.get('days', ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'])
                hours = perf_matrix.get('hours', list(range(24)))
            
            # Crear heatmap
            fig = go.Figure(data=go.Heatmap(
                z=pnl_matrix,
                x=[f"{h:02d}:00" for h in hours],
                y=days,
                colorscale=[
                    [0, self.theme_colors['danger']],
                    [0.5, self.theme_colors['primary']],
                    [1, self.theme_colors['success']]
                ],
                colorbar=dict(
                    title="P&L ($)",
                    titleside="right",
                    tickmode="linear",
                    tick0=np.min(pnl_matrix),
                    dtick=(np.max(pnl_matrix) - np.min(pnl_matrix)) / 10
                ),
                hovertemplate='<b>%{y}</b><br>Hora: %{x}<br>P&L: $%{z:.2f}<br><extra></extra>',
                showscale=True
            ))
            
            # Añadir anotaciones para valores significativos
            for i, day in enumerate(days):
                for j, hour in enumerate(hours):
                    value = pnl_matrix[i][j]
                    if abs(value) > np.std(pnl_matrix) * 2:  # Valores significativos
                        fig.add_annotation(
                            x=j, y=i,
                            text=f"${value:.0f}",
                            showarrow=False,
                            font=dict(
                                color=self.theme_colors['text_primary'] if abs(value) > np.std(pnl_matrix) * 2.5 
                                     else self.theme_colors['text_secondary'],
                                size=10
                            )
                        )
            
            fig.update_layout(
                **self.modern_template['layout'],
                title={
                    'text': '<b>Heatmap de Performance - Horarios Óptimos</b>',
                    'x': 0.5,
                    'font': {'size': 16}
                },
                xaxis_title="Hora del Día",
                yaxis_title="Día de la Semana",
                height=400,
                margin=dict(l=80, r=100, t=60, b=80)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando heatmap de performance: {e}")
            return self._create_empty_chart("Error al cargar heatmap")
    
    def _create_empty_chart(self, message="No data available"):
        """Crea un gráfico vacío con mensaje personalizado"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"<b>{message}</b><br><br>🤖 El sistema está recopilando datos...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color=self.theme_colors['text_secondary']),
            showarrow=False,
            bgcolor=self.theme_colors['secondary'],
            bordercolor=self.theme_colors['border'],
            borderwidth=1
        )
        
        fig.update_layout(
            **self.modern_template['layout'],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=20, r=20, t=20, b=20),
            height=400
        )
        
        return fig


# === FUNCIONES DE COMPATIBILIDAD ===
# Mantener funciones existentes para retrocompatibilidad

def create_pnl_chart(data):
    """Función de compatibilidad para P&L chart"""
    chart_components = EnhancedChartComponents()
    return chart_components.create_runs_overview_chart(data)

def create_trades_distribution_chart(data):
    """Función de compatibilidad para distribución de trades"""
    chart_components = EnhancedChartComponents()
    if not data or 'trades' not in data:
        return chart_components._create_empty_chart("No trade data available")
    
    trades_data = data['trades']
    
    # Crear gráfico de dona simple
    fig = go.Figure(data=[go.Pie(
        labels=['Winning Trades', 'Losing Trades', 'Breakeven'],
        values=[
            trades_data.get('winning_trades', 0),
            trades_data.get('losing_trades', 0),
            trades_data.get('breakeven_trades', 0)
        ],
        hole=.3,
        marker_colors=[
            chart_components.theme_colors['success'],
            chart_components.theme_colors['danger'],
            chart_components.theme_colors['warning']
        ]
    )])
    
    fig.update_layout(
        **chart_components.modern_template['layout'],
        title="Trade Distribution",
        height=400
    )
    
    return fig

def create_accuracy_evolution_chart(data):
    """Función de compatibilidad para evolución de accuracy"""
    chart_components = EnhancedChartComponents()
    return chart_components.create_runs_overview_chart(data)

def create_price_signals_chart(data):
    """Función de compatibilidad para precio con señales"""
    chart_components = EnhancedChartComponents()
    return chart_components.create_real_time_trading_chart(data)

def create_trades_analysis_chart(data):
    """Función de compatibilidad para análisis de trades"""
    chart_components = EnhancedChartComponents()
    return chart_components.create_performance_heatmap(data)

# Compatibilidad con funciones básicas
def price_line_chart(df, y="close", title="Precio"):
    """Función de compatibilidad para gráfico de línea de precio"""
    chart_components = EnhancedChartComponents()
    if df is None or df.empty:
        return chart_components._create_empty_chart("No price data available")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[y],
        mode='lines',
        name=y,
        line=dict(color=chart_components.theme_colors['accent'], width=2)
    ))
    
    fig.update_layout(
        **chart_components.modern_template['layout'],
        title=title,
        showlegend=False,
        height=400
    )
    
    return fig

def volume_bar_chart(df, y="volume", title="Volumen"):
    """Función de compatibilidad para gráfico de volumen"""
    chart_components = EnhancedChartComponents()
    if df is None or df.empty:
        return chart_components._create_empty_chart("No volume data available")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index,
        y=df[y],
        name=y,
        marker_color=chart_components.theme_colors['info']
    ))
    
    fig.update_layout(
        **chart_components.modern_template['layout'],
        title=title,
        showlegend=False,
        height=400
    )
    
    return fig
