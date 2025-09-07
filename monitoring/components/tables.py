from dash import html
import dash_bootstrap_components as dbc

from .. import data_provider as dp


def render_trades_table(limit: int = 20):
    df = dp.get_recent_trades(limit=limit)
    if df is None or df.empty:
        return html.Div("Sin trades recientes")
    header = [html.Th(col) for col in df.columns]
    rows = [html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))]
    return dbc.Table([html.Thead(html.Tr(header)), html.Tbody(rows)], striped=True, bordered=True, hover=True)


