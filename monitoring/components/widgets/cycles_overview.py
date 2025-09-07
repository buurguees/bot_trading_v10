"""
monitoring/components/widgets/cycles_overview.py
Widget de overview con métricas promedio de ciclos del agente
"""

from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CyclesOverviewWidget:
    """Widget de overview con métricas promedio de ciclos"""
    
    def __init__(self):
        self.theme_colors = {
            'primary': '#1a1a1a',
            'secondary': '#2d2d2d',
            'accent': '#00ff88',
            'danger': '#ff4444',
            'warning': '#ffaa00',
            'info': '#4488ff',
            'success': '#28a745',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'border_color': '#444444'
        }
    
    def create_cycles_overview_widget(self) -> html.Div:
        """Crea el widget de overview de ciclos"""
        
        return html.Div([
            # Header del overview
            html.Div([
                html.H3("📊 Overview de Ciclos del Agente", 
                       style={'color': self.theme_colors['text_primary'], 'marginBottom': '10px'}),
                html.P("Métricas promedio de rendimiento histórico", 
                      style={'color': self.theme_colors['text_secondary'], 'marginBottom': '20px'})
            ]),
            
            # Métricas principales del overview
            html.Div([
                # Balance promedio final
                html.Div([
                    html.Div([
                        html.I(className="fas fa-wallet", style={'fontSize': '24px', 'color': self.theme_colors['accent']}),
                        html.Div([
                            html.H4("Balance Promedio Final", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="avg-final-balance", style={'color': self.theme_colors['accent'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card"),
                
                # PnL diario promedio
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-line", style={'fontSize': '24px', 'color': self.theme_colors['success']}),
                        html.Div([
                            html.H4("PnL Diario Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="avg-daily-pnl", style={'color': self.theme_colors['success'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card"),
                
                # Progreso promedio hacia objetivo
                html.Div([
                    html.Div([
                        html.I(className="fas fa-target", style={'fontSize': '24px', 'color': self.theme_colors['info']}),
                        html.Div([
                            html.H4("Progreso Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="avg-progress-target", style={'color': self.theme_colors['info'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card"),
                
                # Win rate promedio
                html.Div([
                    html.Div([
                        html.I(className="fas fa-trophy", style={'fontSize': '24px', 'color': self.theme_colors['warning']}),
                        html.Div([
                            html.H4("Win Rate Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="avg-win-rate", style={'color': self.theme_colors['warning'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card"),
                
                # Sharpe ratio promedio
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-area", style={'fontSize': '24px', 'color': self.theme_colors['success']}),
                        html.Div([
                            html.H4("Sharpe Ratio Promedio", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="avg-sharpe-ratio", style={'color': self.theme_colors['success'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card"),
                
                # Total de ciclos completados
                html.Div([
                    html.Div([
                        html.I(className="fas fa-sync-alt", style={'fontSize': '24px', 'color': self.theme_colors['info']}),
                        html.Div([
                            html.H4("Ciclos Completados", style={'color': self.theme_colors['text_secondary'], 'margin': '0', 'fontSize': '14px'}),
                            html.H2(id="total-completed-cycles", style={'color': self.theme_colors['info'], 'margin': '0', 'fontSize': '28px'})
                        ], style={'marginLeft': '15px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], className="overview-metric-card")
                
            ], className="overview-metrics-grid", style={'marginBottom': '30px'}),
            
            # Gráficos de evolución
            html.Div([
                # Gráfico de evolución PnL total
                html.Div([
                    html.H4("📈 Evolución PnL Total", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                    dcc.Graph(
                        id='pnl-evolution-chart',
                        config={'displayModeBar': False},
                        style={'height': '400px'}
                    )
                ], style={'width': '70%', 'display': 'inline-block', 'paddingRight': '15px'}),
                
                # Gráfico circular de distribución
                html.Div([
                    html.H4("🎯 Distribución de Rendimiento", style={'color': self.theme_colors['text_primary'], 'marginBottom': '15px'}),
                    dcc.Graph(
                        id='performance-distribution-chart',
                        config={'displayModeBar': False},
                        style={'height': '400px'}
                    )
                ], style={'width': '30%', 'display': 'inline-block', 'paddingLeft': '15px'})
            ])
            
        ], className="cycles-overview-widget", style={
            'background': self.theme_colors['secondary'],
            'padding': '25px',
            'borderRadius': '12px',
            'border': f'1px solid {self.theme_colors["border_color"]}',
            'marginBottom': '25px'
        })
    
    def create_pnl_evolution_chart(self, cycles_data: list) -> go.Figure:
        """Crea gráfico de evolución PnL total desde inicio hasta final"""
        try:
            if not cycles_data:
                return go.Figure()
            
            # Ordenar ciclos por fecha de inicio
            sorted_cycles = sorted(cycles_data, key=lambda x: x.get('start_time', ''))
            
            # Crear datos de evolución acumulativa
            evolution_data = []
            cumulative_pnl = 0
            cumulative_balance = 1000.0  # Balance inicial
            
            for i, cycle in enumerate(sorted_cycles):
                start_time = datetime.fromisoformat(cycle.get('start_time', datetime.now().isoformat()))
                daily_pnl = cycle.get('daily_pnl', 0)
                total_pnl = cycle.get('total_pnl', 0)
                
                # Simular evolución diaria del ciclo
                cycle_days = 7  # Duración promedio del ciclo
                for day in range(cycle_days):
                    current_time = start_time + timedelta(days=day)
                    daily_change = daily_pnl / cycle_days
                    cumulative_pnl += daily_change
                    cumulative_balance += daily_change
                    
                    evolution_data.append({
                        'timestamp': current_time,
                        'cumulative_pnl': cumulative_pnl,
                        'cumulative_balance': cumulative_balance,
                        'daily_pnl': daily_change,
                        'cycle_id': cycle.get('cycle_id', f'cycle_{i+1}'),
                        'symbol': cycle.get('symbol', 'BTCUSDT')
                    })
            
            df_evolution = pd.DataFrame(evolution_data)
            
            # Crear gráfico
            fig = go.Figure()
            
            # Línea de PnL acumulativo
            fig.add_trace(go.Scatter(
                x=df_evolution['timestamp'],
                y=df_evolution['cumulative_pnl'],
                mode='lines',
                name='PnL Acumulativo',
                line=dict(color='#00ff88', width=3),
                fill='tonexty',
                fillcolor='rgba(0, 255, 136, 0.1)'
            ))
            
            # Línea de balance acumulativo
            fig.add_trace(go.Scatter(
                x=df_evolution['timestamp'],
                y=df_evolution['cumulative_balance'],
                mode='lines',
                name='Balance Total',
                line=dict(color='#4488ff', width=2),
                yaxis='y2'
            ))
            
            # Marcadores para ciclos completados
            cycle_completions = df_evolution.groupby('cycle_id').tail(1)
            fig.add_trace(go.Scatter(
                x=cycle_completions['timestamp'],
                y=cycle_completions['cumulative_pnl'],
                mode='markers',
                name='Fin de Ciclo',
                marker=dict(
                    symbol='circle',
                    size=8,
                    color='#ffaa00',
                    line=dict(width=2, color='#ffffff')
                )
            ))
            
            fig.update_layout(
                title="Evolución PnL Total - Desde Inicio hasta Final",
                xaxis_title="Tiempo",
                yaxis_title="PnL Acumulativo ($)",
                yaxis2=dict(title="Balance Total ($)", overlaying="y", side="right"),
                template="plotly_dark",
                height=400,
                showlegend=True,
                margin=dict(l=40, r=40, t=40, b=40),
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de evolución PnL: {e}")
            return go.Figure()
    
    def create_performance_distribution_chart(self, cycles_data: list) -> go.Figure:
        """Crea gráfico circular de distribución de rendimiento"""
        try:
            if not cycles_data:
                return go.Figure()
            
            # Categorizar ciclos por rendimiento
            excellent_cycles = [c for c in cycles_data if c.get('pnl_percentage', 0) > 10]
            good_cycles = [c for c in cycles_data if 5 <= c.get('pnl_percentage', 0) <= 10]
            average_cycles = [c for c in cycles_data if 0 <= c.get('pnl_percentage', 0) < 5]
            poor_cycles = [c for c in cycles_data if c.get('pnl_percentage', 0) < 0]
            
            # Datos para el gráfico circular
            labels = ['Excelente (>10%)', 'Bueno (5-10%)', 'Promedio (0-5%)', 'Pobre (<0%)']
            values = [len(excellent_cycles), len(good_cycles), len(average_cycles), len(poor_cycles)]
            colors = ['#00ff88', '#4488ff', '#ffaa00', '#ff4444']
            
            # Crear gráfico circular
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
                textinfo='label+percent+value',
                textfont=dict(size=12, color='#ffffff'),
                hovertemplate='<b>%{label}</b><br>Ciclos: %{value}<br>Porcentaje: %{percent}<extra></extra>'
            )])
            
            # Agregar texto central
            total_cycles = sum(values)
            fig.add_annotation(
                text=f"<b>Total<br>{total_cycles}<br>Ciclos</b>",
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False,
                font_color='#ffffff'
            )
            
            fig.update_layout(
                title="Distribución de Rendimiento por Ciclos",
                template="plotly_dark",
                height=400,
                showlegend=True,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.01
                )
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creando gráfico de distribución: {e}")
            return go.Figure()
    
    def calculate_cycles_averages(self, cycles_data: list) -> dict:
        """Calcula las medias de los ciclos"""
        try:
            if not cycles_data:
                return {
                    'avg_final_balance': 0.0,
                    'avg_daily_pnl': 0.0,
                    'avg_progress_target': 0.0,
                    'avg_win_rate': 0.0,
                    'avg_sharpe_ratio': 0.0,
                    'total_completed_cycles': 0
                }
            
            # Filtrar solo ciclos completados
            completed_cycles = [c for c in cycles_data if c.get('status') == 'completed']
            
            if not completed_cycles:
                return {
                    'avg_final_balance': 0.0,
                    'avg_daily_pnl': 0.0,
                    'avg_progress_target': 0.0,
                    'avg_win_rate': 0.0,
                    'avg_sharpe_ratio': 0.0,
                    'total_completed_cycles': 0
                }
            
            # Calcular promedios
            avg_final_balance = np.mean([c.get('final_balance', 0) for c in completed_cycles])
            avg_daily_pnl = np.mean([c.get('daily_pnl', 0) for c in completed_cycles])
            avg_progress_target = np.mean([c.get('progress_to_target', 0) for c in completed_cycles])
            avg_win_rate = np.mean([c.get('win_rate', 0) for c in completed_cycles])
            avg_sharpe_ratio = np.mean([c.get('sharpe_ratio', 0) for c in completed_cycles])
            
            return {
                'avg_final_balance': avg_final_balance,
                'avg_daily_pnl': avg_daily_pnl,
                'avg_progress_target': avg_progress_target,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe_ratio,
                'total_completed_cycles': len(completed_cycles)
            }
            
        except Exception as e:
            logger.error(f"Error calculando promedios de ciclos: {e}")
            return {
                'avg_final_balance': 0.0,
                'avg_daily_pnl': 0.0,
                'avg_progress_target': 0.0,
                'avg_win_rate': 0.0,
                'avg_sharpe_ratio': 0.0,
                'total_completed_cycles': 0
            }
