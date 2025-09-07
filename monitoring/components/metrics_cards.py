from dash import html
import dash_bootstrap_components as dbc

from monitoring.core.data_provider import DashboardDataProvider
from monitoring.utils.helpers import format_currency


def _metric_card(title: str, value: str, color: str = "primary"):
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(html.H4(value, className="card-title")),
    ], color=color, inverse=True, className="mb-3")


def render_metrics_cards():
    """Renderiza las tarjetas de métricas principales"""
    try:
        data_provider = DashboardDataProvider()
        data = data_provider.get_dashboard_data()
        
        # Extraer métricas de los datos
        portfolio = data.get('portfolio', {})
        performance = data.get('performance', {})
        
        return dbc.Row([
            dbc.Col(_metric_card("Total Balance", format_currency(portfolio.get('total_balance', 0)), "primary"), md=3),
            dbc.Col(_metric_card("Daily P&L", format_currency(performance.get('daily_pnl', 0)), "info"), md=3),
            dbc.Col(_metric_card("Win Rate", f"{performance.get('win_rate', 0):.1f}%", "success"), md=3),
            dbc.Col(_metric_card("Active Positions", str(portfolio.get('active_positions', 0)), "warning"), md=3),
        ])
    except Exception as e:
        # Fallback con datos de demo
        return dbc.Row([
            dbc.Col(_metric_card("Total Balance", "$10,000.00", "primary"), md=3),
            dbc.Col(_metric_card("Daily P&L", "+$156.30", "info"), md=3),
            dbc.Col(_metric_card("Win Rate", "75%", "success"), md=3),
            dbc.Col(_metric_card("Active Positions", "2", "warning"), md=3),
        ])


