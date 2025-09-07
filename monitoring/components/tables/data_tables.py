from dash import html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

from monitoring.core.data_provider import DashboardDataProvider


def render_trades_table(limit: int = 20):
    """Renderiza la tabla de trades recientes"""
    try:
        data_provider = DashboardDataProvider()
        data = data_provider.get_dashboard_data()
        
        trades_data = data.get('trades', [])
        
        if not trades_data:
            return html.Div([
                html.H5("📋 Recent Trades"),
                html.P("No hay trades recientes", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            ])
        
        # Convertir a DataFrame para dash_table
        df = pd.DataFrame(trades_data[:limit])
        
        return html.Div([
            html.H5("📋 Recent Trades"),
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df.columns],
                style_cell={
                    'backgroundColor': '#1b1e28',
                    'color': '#e6e6e6',
                    'textAlign': 'left',
                    'fontSize': '12px',
                    'fontFamily': 'Segoe UI'
                },
                style_header={
                    'backgroundColor': '#2d2d2d',
                    'color': '#00ff88',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{side} = BUY'},
                        'backgroundColor': 'rgba(0, 255, 136, 0.1)',
                    },
                    {
                        'if': {'filter_query': '{side} = SELL'},
                        'backgroundColor': 'rgba(255, 68, 68, 0.1)',
                    }
                ],
                page_size=10,
                sort_action="native",
                filter_action="native"
            )
        ])
        
    except Exception as e:
        return html.Div([
            html.H5("📋 Recent Trades"),
            html.P(f"Error cargando trades: {str(e)}", style={'color': '#ff4444', 'textAlign': 'center', 'padding': '20px'})
        ])


def render_positions_table():
    """Renderiza la tabla de posiciones activas"""
    try:
        data_provider = DashboardDataProvider()
        data = data_provider.get_dashboard_data()
        
        positions_data = data.get('positions', [])
        
        if not positions_data:
            return html.Div([
                html.H5("💼 Active Positions"),
                html.P("No hay posiciones activas", style={'color': '#cccccc', 'textAlign': 'center', 'padding': '20px'})
            ])
        
        # Convertir a DataFrame
        df = pd.DataFrame(positions_data)
        
        return html.Div([
            html.H5("💼 Active Positions"),
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df.columns],
                style_cell={
                    'backgroundColor': '#1b1e28',
                    'color': '#e6e6e6',
                    'textAlign': 'left',
                    'fontSize': '12px',
                    'fontFamily': 'Segoe UI'
                },
                style_header={
                    'backgroundColor': '#2d2d2d',
                    'color': '#00ff88',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{pnl} > 0'},
                        'backgroundColor': 'rgba(0, 255, 136, 0.1)',
                    },
                    {
                        'if': {'filter_query': '{pnl} < 0'},
                        'backgroundColor': 'rgba(255, 68, 68, 0.1)',
                    }
                ],
                page_size=10,
                sort_action="native"
            )
        ])
        
    except Exception as e:
        return html.Div([
            html.H5("💼 Active Positions"),
            html.P(f"Error cargando posiciones: {str(e)}", style={'color': '#ff4444', 'textAlign': 'center', 'padding': '20px'})
        ])


