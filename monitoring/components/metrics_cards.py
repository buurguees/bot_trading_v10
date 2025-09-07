from dash import html
import dash_bootstrap_components as dbc

from ..data_provider import get_overview_metrics
from ..utils import format_currency


def _metric_card(title: str, value: str, color: str = "primary"):
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(html.H4(value, className="card-title")),
    ], color=color, inverse=True, className="mb-3")


def render_metrics_cards():
    metrics = get_overview_metrics()
    return dbc.Row([
        dbc.Col(_metric_card("Symbols", str(metrics["symbols_count"]), "primary"), md=3),
        dbc.Col(_metric_card("Open Positions", str(metrics["open_positions"]), "info"), md=3),
        dbc.Col(_metric_card("Balance", format_currency(metrics["balance_total"]), "success"), md=3),
        dbc.Col(_metric_card("PnL (Day)", format_currency(metrics["pnl_day"]), "warning"), md=3),
    ])


