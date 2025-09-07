from typing import List

import plotly.express as px
from dash import dcc
import pandas as pd


def price_line_chart(df: pd.DataFrame, y: str = "close", title: str = "Precio"):
    if df is None or df.empty:
        return dcc.Graph(figure=px.line(title=title))
    fig = px.line(df.reset_index(), x="timestamp", y=y, title=title)
    return dcc.Graph(figure=fig)


def volume_bar_chart(df: pd.DataFrame, y: str = "volume", title: str = "Volumen"):
    if df is None or df.empty:
        return dcc.Graph(figure=px.bar(title=title))
    fig = px.bar(df.reset_index(), x="timestamp", y=y, title=title)
    return dcc.Graph(figure=fig)


