from dash import Dash, Input, Output, callback
from . import data_provider as dp
from .layout_components import LayoutComponents
import logging

logger = logging.getLogger(__name__)

def register_callbacks(app: Dash) -> None:
    """Registra todos los callbacks del dashboard"""
    
    layout_components = LayoutComponents()
    
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
    
    @app.callback(
        Output("dummy-output", "children"),
        Input("url", "pathname")
    )
    def _on_route_change(_):  # noqa: ANN001
        return ""


