from dash import Dash, Input, Output, callback, dcc
from .data_provider import DashboardDataProvider
from .layout_components import LayoutComponents
from .chart_components import ChartComponents
import logging

logger = logging.getLogger(__name__)

def register_callbacks(app: Dash) -> None:
    """Registra todos los callbacks del dashboard"""
    
    layout_components = LayoutComponents()
    chart_components = ChartComponents()
    data_provider = DashboardDataProvider()
    
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def display_page(pathname):
        """Maneja la navegación entre páginas"""
        if pathname == '/' or pathname == '/home':
            return layout_components.create_home_page()
        elif pathname == '/trading':
            return layout_components.create_trading_page()
        elif pathname == '/performance':
            return layout_components.create_performance_page()
        elif pathname == '/settings':
            return layout_components.create_settings_page()
        elif pathname == '/alerts':
            return layout_components.create_alerts_page()
        elif pathname == '/chat':
            return layout_components.create_chat_page()
        else:
            return layout_components.create_404_page()
    
    # Callbacks para actualizar gráficos
    @app.callback(
        Output("pnl-chart", "figure"),
        Input("url", "pathname")
    )
    def update_pnl_chart(pathname):
        """Actualiza el gráfico de P&L"""
        try:
            data = data_provider.get_dashboard_data()
            return chart_components.create_pnl_chart(data)
        except Exception as e:
            logger.error(f"Error actualizando gráfico P&L: {e}")
            return chart_components._create_empty_chart("Error loading P&L chart")
    
    @app.callback(
        Output("trades-distribution-chart", "figure"),
        Input("url", "pathname")
    )
    def update_trades_distribution_chart(pathname):
        """Actualiza el gráfico de distribución de trades"""
        try:
            data = data_provider.get_dashboard_data()
            return chart_components.create_trades_distribution_chart(data)
        except Exception as e:
            logger.error(f"Error actualizando gráfico de distribución: {e}")
            return chart_components._create_empty_chart("Error loading distribution chart")
    
    @app.callback(
        Output("price-signals-chart", "figure"),
        Input("url", "pathname")
    )
    def update_price_signals_chart(pathname):
        """Actualiza el gráfico de precio con señales"""
        try:
            data = data_provider.get_dashboard_data()
            return chart_components.create_price_signals_chart(data)
        except Exception as e:
            logger.error(f"Error actualizando gráfico de precio: {e}")
            return chart_components._create_empty_chart("Error loading price chart")
    
    @app.callback(
        Output("accuracy-evolution-chart", "figure"),
        Input("url", "pathname")
    )
    def update_accuracy_evolution_chart(pathname):
        """Actualiza el gráfico de evolución de accuracy"""
        try:
            data = data_provider.get_dashboard_data()
            return chart_components.create_accuracy_evolution_chart(data)
        except Exception as e:
            logger.error(f"Error actualizando gráfico de accuracy: {e}")
            return chart_components._create_empty_chart("Error loading accuracy chart")
    
    @app.callback(
        Output("trades-analysis-chart", "figure"),
        Input("url", "pathname")
    )
    def update_trades_analysis_chart(pathname):
        """Actualiza el gráfico de análisis de trades"""
        try:
            data = data_provider.get_dashboard_data()
            return chart_components.create_trades_analysis_chart(data)
        except Exception as e:
            logger.error(f"Error actualizando gráfico de análisis: {e}")
            return chart_components._create_empty_chart("Error loading analysis chart")
    
    @app.callback(
        Output("dummy-output", "children"),
        Input("url", "pathname")
    )
    def _on_route_change(_):  # noqa: ANN001
        return ""


