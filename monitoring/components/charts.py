from dash import html, dcc
from .. import data_provider as dp
from ..chart_components import ChartComponents


def render_price_section(symbol: str = "ETHUSDT"):
    """Renderiza la sección de gráficos de precio"""
    chart_components = ChartComponents()
    
    # Obtener datos del proveedor
    data = dp.get_dashboard_data()
    
    return html.Div([
        # Gráfico P&L
        dcc.Graph(
            id="pnl-chart",
            figure=chart_components.create_pnl_chart(data),
            style={'height': '400px'}
        ),
        
        # Gráfico de distribución de trades
        dcc.Graph(
            id="trades-distribution-chart", 
            figure=chart_components.create_trades_distribution_chart(data),
            style={'height': '400px'}
        ),
        
        # Gráfico de precio con señales
        dcc.Graph(
            id="price-signals-chart",
            figure=chart_components.create_price_signals_chart(data),
            style={'height': '500px'}
        ),
        
        # Gráfico de evolución de accuracy
        dcc.Graph(
            id="accuracy-evolution-chart",
            figure=chart_components.create_accuracy_evolution_chart(data),
            style={'height': '400px'}
        ),
        
        # Gráfico de análisis de trades
        dcc.Graph(
            id="trades-analysis-chart",
            figure=chart_components.create_trades_analysis_chart(data),
            style={'height': '400px'}
        )
    ])


