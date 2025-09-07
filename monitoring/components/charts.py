from dash import html
from .. import data_provider as dp
from ..chart_components import price_line_chart, volume_bar_chart


def render_price_section(symbol: str = "ETHUSDT"):
    df = dp.get_market_data(symbol=symbol, limit=200)
    return html.Div([
        price_line_chart(df, y="close", title=f"Precio {symbol}"),
        volume_bar_chart(df, y="volume", title=f"Volumen {symbol}"),
    ])


