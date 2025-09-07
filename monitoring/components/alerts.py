from dash import html
import dash_bootstrap_components as dbc

from ..data_provider import DashboardDataProvider


def render_alerts():
    """Renderiza las alertas del sistema"""
    try:
        data_provider = DashboardDataProvider()
        data = data_provider.get_dashboard_data()
        
        alerts_data = data.get('alerts', [])
        
        if not alerts_data:
            return html.Div([
                dbc.Alert("✅ Sistema activo y monitorizando.", color="success", dismissable=True),
            ])
        
        alerts = []
        for alert in alerts_data[:5]:  # Mostrar solo las 5 más recientes
            color = "success" if alert.get('level') == 'info' else "warning" if alert.get('level') == 'warning' else "danger"
            alerts.append(
                dbc.Alert(
                    f"{alert.get('icon', '🔔')} {alert.get('message', '')}",
                    color=color,
                    dismissable=True,
                    style={'marginBottom': '10px'}
                )
            )
        
        return html.Div(alerts)
        
    except Exception as e:
        return html.Div([
            dbc.Alert("⚠️ Error cargando alertas del sistema.", color="warning", dismissable=True),
        ])


