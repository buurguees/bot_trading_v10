from dash import html
import dash_bootstrap_components as dbc


def render_alerts():
    return html.Div([
        dbc.Alert("Sistema activo y monitorizando.", color="success", dismissable=True),
    ])


