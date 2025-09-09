"""
monitoring/styles/__init__.py
Sistema de Estilos y Temas - Trading Bot v10

Este módulo contiene todas las definiciones de estilos, temas
y formateo visual para el dashboard de monitoreo.
"""

from monitoring.styles.themes import (
    COLORS,
    DARK_THEME,
    LIGHT_THEME,
    AVAILABLE_THEMES,
    THEME_CSS,
    CHART_THEMES,
    COMPONENT_STYLES,
    get_theme,
    get_theme_colors,
    get_chart_theme,
    get_theme_css,
    get_component_style,
    format_currency,
    format_percentage,
    get_profit_color,
    get_risk_color
)

__version__ = "10.0.0"
__description__ = "Sistema de Estilos y Temas"

__all__ = [
    'COLORS',
    'DARK_THEME',
    'LIGHT_THEME', 
    'AVAILABLE_THEMES',
    'THEME_CSS',
    'CHART_THEMES',
    'COMPONENT_STYLES',
    'get_theme',
    'get_theme_colors',
    'get_chart_theme',
    'get_theme_css',
    'get_component_style',
    'format_currency',
    'format_percentage',
    'get_profit_color',
    'get_risk_color'
]