"""
monitoring/chart_components.py
Componentes de gráficos para el dashboard del Trading Bot v10
Ubicación: C:\TradingBot_v10\monitoring\chart_components.py

Funcionalidades:
- Genera todos los gráficos del dashboard
- Gráficos interactivos con Plotly
- Estilos consistentes y modernos
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ChartComponents:
    """Componentes de gráficos para el dashboard"""
    
    def __init__(self):
        self.theme_colors = {
            'primary': '#1a1a1a',
            'secondary': '#2d2d2d',
            'accent': '#00ff88',
            'danger': '#ff4444',
            'warning': '#ffaa00',
            'info': '#4488ff',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'grid': '#404040'
        }
        
        self.chart_template = {
            'layout': {
                'plot_bgcolor': self.theme_colors['primary'],
                'paper_bgcolor': self.theme_colors['primary'],
                'font': {'color': self.theme_colors['text_primary']},
                'xaxis': {
                    'gridcolor': self.theme_colors['grid'],
                    'linecolor': self.theme_colors['grid']
                },
                'yaxis': {
                    'gridcolor': self.theme_colors['grid'],
                    'linecolor': self.theme_colors['grid']
                }
            }
        }
    
    def create_pnl_chart(self, data):
        """Crea gráfico de P&L acumulado"""
        try:
            if not data or 'pnl_history' not in data:
                return self._create_empty_chart("P&L data not available")
            
            pnl_data = data['pnl_history']
            
            fig = go.Figure()
            
            # Línea de P&L acumulado
            fig.add_trace(go.Scatter(
                x=pnl_data['dates'],
                y=pnl_data['cumulative_pnl'],
                mode='lines',
                name='Cumulative P&L',
                line=dict(color=self.theme_colors['accent'], width=3),
                fill='tonexty',
                fillcolor=f"rgba(0, 255, 136, 0.1)"
            ))
            
            # Línea base en 0
            fig.add_hline(
                y=0, 
                line_dash="dash", 
                line_color=self.theme_colors['text_secondary'],
                opacity=0.5
            )
            
            fig.update_layout(
                **self.chart_template['layout'],
                title="Cumulative P&L Evolution",
                xaxis_title="Date",
                yaxis_title="P&L ($)",
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico P&L: {e}")
            return self._create_empty_chart("Error loading P&L chart")
    
    def create_trades_distribution_chart(self, data):
        """Crea gráfico de distribución de trades"""
        try:
            if not data or 'trades_distribution' not in data:
                # Datos de demo
                distribution_data = {'wins': 23, 'losses': 12, 'breakeven': 3}
            else:
                distribution_data = data['trades_distribution']
            
            labels = ['Wins', 'Losses', 'Breakeven']
            values = [distribution_data['wins'], distribution_data['losses'], distribution_data['breakeven']]
            colors = [self.theme_colors['accent'], self.theme_colors['danger'], self.theme_colors['warning']]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker_colors=colors,
                textinfo='label+percent+value',
                textfont=dict(size=12, color=self.theme_colors['text_primary'])
            )])
            
            fig.update_layout(
                **self.chart_template['layout'],
                title="Trades Distribution",
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                annotations=[dict(text=f"Total<br>{sum(values)}", x=0.5, y=0.5, font_size=16, showarrow=False)]
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de distribución: {e}")
            return self._create_empty_chart("Error loading distribution chart")
    
    def create_accuracy_evolution_chart(self, data):
        """Crea gráfico de evolución de accuracy"""
        try:
            if not data or 'accuracy_evolution' not in data:
                return self._create_empty_chart("Accuracy data not available")
            
            accuracy_data = data['accuracy_evolution']
            
            fig = go.Figure()
            
            # Línea de accuracy
            fig.add_trace(go.Scatter(
                x=accuracy_data['dates'],
                y=accuracy_data['accuracy'],
                mode='lines+markers',
                name='Model Accuracy',
                line=dict(color=self.theme_colors['info'], width=3),
                marker=dict(size=6, color=self.theme_colors['info'])
            ))
            
            # Líneas de referencia
            fig.add_hline(
                y=0.7, 
                line_dash="dash", 
                line_color=self.theme_colors['accent'],
                annotation_text="Target (70%)",
                annotation_position="bottom right"
            )
            
            fig.add_hline(
                y=0.6, 
                line_dash="dash", 
                line_color=self.theme_colors['warning'],
                annotation_text="Retrain Threshold (60%)",
                annotation_position="bottom right"
            )
            
            fig.update_layout(
                **self.chart_template['layout'],
                title="Model Accuracy Evolution",
                xaxis_title="Date",
                yaxis_title="Accuracy",
                yaxis=dict(tickformat='.0%', range=[0.4, 1.0]),
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de accuracy: {e}")
            return self._create_empty_chart("Error loading accuracy chart")
    
    def create_price_signals_chart(self, data):
        """Crea gráfico de precio con señales"""
        try:
            # Generar datos de demo para el gráfico de precio
            dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
            
            # Simular datos de precio
            np.random.seed(42)
            price_base = 45000
            returns = np.random.normal(0, 0.01, len(dates))
            prices = [price_base]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Crear datos OHLCV
            df = pd.DataFrame({
                'datetime': dates,
                'close': prices
            })
            
            # Calcular OHLCV
            df['high'] = df['close'] * (1 + np.random.uniform(0, 0.02, len(df)))
            df['low'] = df['close'] * (1 - np.random.uniform(0, 0.02, len(df)))
            df['open'] = df['close'].shift(1).fillna(df['close'][0])
            df['volume'] = np.random.uniform(1000, 5000, len(df))
            
            fig = go.Figure()
            
            # Candlestick chart
            fig.add_trace(go.Candlestick(
                x=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='BTCUSDT',
                increasing_line_color=self.theme_colors['accent'],
                decreasing_line_color=self.theme_colors['danger']
            ))
            
            # Añadir señales de ejemplo
            buy_signals_x = [dates[20], dates[80], dates[120]]
            buy_signals_y = [df.iloc[20]['low'], df.iloc[80]['low'], df.iloc[120]['low']]
            
            sell_signals_x = [dates[50], dates[100]]
            sell_signals_y = [df.iloc[50]['high'], df.iloc[100]['high']]
            
            # Markers de BUY
            fig.add_trace(go.Scatter(
                x=buy_signals_x,
                y=buy_signals_y,
                mode='markers',
                name='BUY Signals',
                marker=dict(
                    symbol='triangle-up',
                    size=15,
                    color=self.theme_colors['accent'],
                    line=dict(width=2, color=self.theme_colors['primary'])
                )
            ))
            
            # Markers de SELL
            fig.add_trace(go.Scatter(
                x=sell_signals_x,
                y=sell_signals_y,
                mode='markers',
                name='SELL Signals',
                marker=dict(
                    symbol='triangle-down',
                    size=15,
                    color=self.theme_colors['danger'],
                    line=dict(width=2, color=self.theme_colors['primary'])
                )
            ))
            
            fig.update_layout(
                **self.chart_template['layout'],
                title="BTCUSDT Price with Trading Signals",
                xaxis_title="Time",
                yaxis_title="Price ($)",
                xaxis_rangeslider_visible=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de precio: {e}")
            return self._create_empty_chart("Error loading price chart")
    
    def create_trades_analysis_chart(self, data):
        """Crea gráfico de análisis de trades"""
        try:
            # Datos de demo para análisis de trades
            hours = list(range(24))
            trades_per_hour = np.random.poisson(2, 24)
            win_rates = np.random.uniform(0.5, 0.9, 24)
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Trades per Hour', 'Win Rate by Hour'),
                vertical_spacing=0.15
            )
            
            # Gráfico de barras para trades por hora
            fig.add_trace(
                go.Bar(
                    x=hours,
                    y=trades_per_hour,
                    name='Trades',
                    marker_color=self.theme_colors['info']
                ),
                row=1, col=1
            )
            
            # Línea para win rate por hora
            fig.add_trace(
                go.Scatter(
                    x=hours,
                    y=win_rates,
                    mode='lines+markers',
                    name='Win Rate',
                    line=dict(color=self.theme_colors['accent'], width=3),
                    marker=dict(size=6)
                ),
                row=2, col=1
            )
            
            fig.update_xaxes(title_text="Hour of Day", row=2, col=1)
            fig.update_yaxes(title_text="Number of Trades", row=1, col=1)
            fig.update_yaxes(title_text="Win Rate", tickformat='.0%', row=2, col=1)
            
            fig.update_layout(
                **self.chart_template['layout'],
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de análisis: {e}")
            return self._create_empty_chart("Error loading analysis chart")
    
    def _create_empty_chart(self, message="No data available"):
        """Crea un gráfico vacío con mensaje"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color=self.theme_colors['text_secondary']),
            showarrow=False
        )
        
        fig.update_layout(
            **self.chart_template['layout'],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        return fig


# Funciones de compatibilidad para el dashboard existente
def price_line_chart(df: pd.DataFrame, y: str = "close", title: str = "Precio"):
    """Función de compatibilidad para gráfico de precio"""
    chart_components = ChartComponents()
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
        **chart_components.chart_template['layout'],
        title=title,
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return fig


def volume_bar_chart(df: pd.DataFrame, y: str = "volume", title: str = "Volumen"):
    """Función de compatibilidad para gráfico de volumen"""
    chart_components = ChartComponents()
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
        **chart_components.chart_template['layout'],
        title=title,
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return fig
