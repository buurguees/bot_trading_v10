"""
monitoring/styles/themes.py
Sistema de Temas para Dashboard - Trading Bot v10

Define los temas visuales, colores y estilos para el dashboard.
Incluye tema oscuro y claro con esquemas de colores optimizados
para trading y análisis financiero.
"""

from typing import Dict, Any

# Colores base del sistema
COLORS = {
    # Colores primarios
    'primary': '#007bff',
    'secondary': '#6c757d', 
    'success': '#28a745',
    'danger': '#dc3545',
    'warning': '#ffc107',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40',
    
    # Colores para trading
    'bull': '#00c851',      # Verde para subidas
    'bear': '#ff4444',      # Rojo para bajadas
    'neutral': '#ffc107',   # Amarillo para neutral
    
    # Colores para gráficos
    'chart_bg_dark': '#1e1e1e',
    'chart_bg_light': '#ffffff',
    'grid_dark': '#2d2d2d',
    'grid_light': '#f0f0f0',
    
    # Colores para métricas
    'profit': '#00c851',
    'loss': '#ff4444',
    'breakeven': '#ffc107',
    
    # Colores adicionales
    'purple': '#6f42c1',
    'cyan': '#17a2b8',
    'orange': '#fd7e14',
    'pink': '#e83e8c',
    'teal': '#20c997',
    'indigo': '#6610f2'
}

# Tema oscuro
DARK_THEME = {
    'name': 'dark',
    'colors': {
        # Fondo principal
        'background': '#121212',
        'surface': '#1e1e1e',
        'card': '#2d2d2d',
        'sidebar': '#1a1a1a',
        'header': '#0d1117',
        
        # Texto
        'text_primary': '#ffffff',
        'text_secondary': '#b3b3b3',
        'text_muted': '#6c757d',
        
        # Bordes
        'border': '#3d3d3d',
        'border_light': '#4d4d4d',
        
        # Estados
        'hover': '#404040',
        'active': '#505050',
        'disabled': '#2a2a2a',
        
        # Componentes específicos
        'navbar': '#0d1117',
        'dropdown': '#2d2d2d',
        'modal': '#1e1e1e',
        'tooltip': '#2d2d2d',
        
        # Trading colors
        'bull': COLORS['bull'],
        'bear': COLORS['bear'],
        'neutral': COLORS['neutral'],
        
        # Chart colors
        'chart_bg': COLORS['chart_bg_dark'],
        'grid': COLORS['grid_dark'],
        'axis': '#666666',
        
        # Status indicators
        'online': '#00c851',
        'offline': '#ff4444',
        'warning': '#ffc107',
        'info': '#17a2b8'
    },
    'styles': {
        'font_family': "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        'font_size_base': '14px',
        'font_size_sm': '12px',
        'font_size_lg': '16px',
        'line_height': '1.5',
        'border_radius': '8px',
        'border_radius_sm': '4px',
        'border_radius_lg': '12px',
        'box_shadow': '0 4px 6px rgba(0, 0, 0, 0.3)',
        'box_shadow_sm': '0 2px 4px rgba(0, 0, 0, 0.2)',
        'box_shadow_lg': '0 8px 12px rgba(0, 0, 0, 0.4)',
        'transition': 'all 0.3s ease'
    }
}

# Tema claro
LIGHT_THEME = {
    'name': 'light',
    'colors': {
        # Fondo principal
        'background': '#ffffff',
        'surface': '#f8f9fa',
        'card': '#ffffff',
        'sidebar': '#f5f5f5',
        'header': '#ffffff',
        
        # Texto
        'text_primary': '#212529',
        'text_secondary': '#495057',
        'text_muted': '#6c757d',
        
        # Bordes
        'border': '#dee2e6',
        'border_light': '#e9ecef',
        
        # Estados
        'hover': '#f8f9fa',
        'active': '#e9ecef',
        'disabled': '#f8f9fa',
        
        # Componentes específicos
        'navbar': '#ffffff',
        'dropdown': '#ffffff',
        'modal': '#ffffff',
        'tooltip': '#212529',
        
        # Trading colors
        'bull': COLORS['bull'],
        'bear': COLORS['bear'],
        'neutral': COLORS['neutral'],
        
        # Chart colors
        'chart_bg': COLORS['chart_bg_light'],
        'grid': COLORS['grid_light'],
        'axis': '#333333',
        
        # Status indicators
        'online': '#00c851',
        'offline': '#ff4444',
        'warning': '#ffc107',
        'info': '#17a2b8'
    },
    'styles': {
        'font_family': "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        'font_size_base': '14px',
        'font_size_sm': '12px',
        'font_size_lg': '16px',
        'line_height': '1.5',
        'border_radius': '8px',
        'border_radius_sm': '4px',
        'border_radius_lg': '12px',
        'box_shadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'box_shadow_sm': '0 2px 4px rgba(0, 0, 0, 0.05)',
        'box_shadow_lg': '0 8px 12px rgba(0, 0, 0, 0.15)',
        'transition': 'all 0.3s ease'
    }
}

# Temas disponibles
AVAILABLE_THEMES = {
    'dark': DARK_THEME,
    'light': LIGHT_THEME
}

# CSS personalizado para cada tema
THEME_CSS = {
    'dark': """
        .dashboard-container.theme-dark {
            background-color: #121212;
            color: #ffffff;
        }
        
        .dashboard-container.theme-dark .card {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            color: #ffffff;
        }
        
        .dashboard-container.theme-dark .sidebar {
            background-color: #1a1a1a;
            border-right: 1px solid #3d3d3d;
        }
        
        .dashboard-container.theme-dark .nav-link {
            color: #b3b3b3;
        }
        
        .dashboard-container.theme-dark .nav-link:hover {
            background-color: #404040;
            color: #ffffff;
        }
        
        .dashboard-container.theme-dark .nav-link.active {
            background-color: #007bff;
            color: #ffffff;
        }
        
        .dashboard-container.theme-dark .metric-card {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            border: 1px solid #4d4d4d;
        }
        
        .dashboard-container.theme-dark .table {
            color: #ffffff;
            background-color: #2d2d2d;
        }
        
        .dashboard-container.theme-dark .table th {
            border-color: #3d3d3d;
            background-color: #1e1e1e;
        }
        
        .dashboard-container.theme-dark .table td {
            border-color: #3d3d3d;
        }
    """,
    
    'light': """
        .dashboard-container.theme-light {
            background-color: #ffffff;
            color: #212529;
        }
        
        .dashboard-container.theme-light .card {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            color: #212529;
        }
        
        .dashboard-container.theme-light .sidebar {
            background-color: #f5f5f5;
            border-right: 1px solid #dee2e6;
        }
        
        .dashboard-container.theme-light .nav-link {
            color: #495057;
        }
        
        .dashboard-container.theme-light .nav-link:hover {
            background-color: #f8f9fa;
            color: #212529;
        }
        
        .dashboard-container.theme-light .nav-link.active {
            background-color: #007bff;
            color: #ffffff;
        }
        
        .dashboard-container.theme-light .metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border: 1px solid #dee2e6;
        }
        
        .dashboard-container.theme-light .table {
            color: #212529;
            background-color: #ffffff;
        }
        
        .dashboard-container.theme-light .table th {
            border-color: #dee2e6;
            background-color: #f8f9fa;
        }
        
        .dashboard-container.theme-light .table td {
            border-color: #dee2e6;
        }
    """
}

# Configuración de gráficos por tema
CHART_THEMES = {
    'dark': {
        'template': 'plotly_dark',
        'paper_bgcolor': DARK_THEME['colors']['background'],
        'plot_bgcolor': DARK_THEME['colors']['chart_bg'],
        'font_color': DARK_THEME['colors']['text_primary'],
        'grid_color': DARK_THEME['colors']['grid'],
        'axis_color': DARK_THEME['colors']['axis']
    },
    'light': {
        'template': 'plotly_white',
        'paper_bgcolor': LIGHT_THEME['colors']['background'],
        'plot_bgcolor': LIGHT_THEME['colors']['chart_bg'],
        'font_color': LIGHT_THEME['colors']['text_primary'],
        'grid_color': LIGHT_THEME['colors']['grid'],
        'axis_color': LIGHT_THEME['colors']['axis']
    }
}

def get_theme(theme_name: str = 'dark') -> Dict[str, Any]:
    """
    Obtiene la configuración completa de un tema
    
    Args:
        theme_name (str): Nombre del tema ('dark' o 'light')
        
    Returns:
        Dict[str, Any]: Configuración completa del tema
    """
    if theme_name not in AVAILABLE_THEMES:
        theme_name = 'dark'  # Fallback al tema oscuro
    
    return AVAILABLE_THEMES[theme_name]

def get_theme_colors(theme_name: str = 'dark') -> Dict[str, str]:
    """
    Obtiene solo los colores de un tema
    
    Args:
        theme_name (str): Nombre del tema
        
    Returns:
        Dict[str, str]: Diccionario de colores del tema
    """
    theme = get_theme(theme_name)
    return theme['colors']

def get_chart_theme(theme_name: str = 'dark') -> Dict[str, Any]:
    """
    Obtiene la configuración de gráficos para un tema
    
    Args:
        theme_name (str): Nombre del tema
        
    Returns:
        Dict[str, Any]: Configuración de gráficos del tema
    """
    if theme_name not in CHART_THEMES:
        theme_name = 'dark'
    
    return CHART_THEMES[theme_name]

def get_theme_css(theme_name: str = 'dark') -> str:
    """
    Obtiene el CSS personalizado para un tema
    
    Args:
        theme_name (str): Nombre del tema
        
    Returns:
        str: CSS personalizado del tema
    """
    if theme_name not in THEME_CSS:
        theme_name = 'dark'
    
    return THEME_CSS[theme_name]

def format_currency(value: float, currency: str = 'USD') -> str:
    """
    Formatea un valor como moneda
    
    Args:
        value (float): Valor a formatear
        currency (str): Tipo de moneda
        
    Returns:
        str: Valor formateado como moneda
    """
    if currency == 'USD':
        return f"${value:,.2f}"
    elif currency == 'BTC':
        return f"₿{value:.8f}"
    elif currency == 'ETH':
        return f"Ξ{value:.6f}"
    else:
        return f"{value:,.2f} {currency}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Formatea un valor como porcentaje
    
    Args:
        value (float): Valor a formatear (0.1 = 10%)
        decimals (int): Número de decimales
        
    Returns:
        str: Valor formateado como porcentaje
    """
    return f"{value:.{decimals}f}%"

def get_profit_color(value: float, theme_name: str = 'dark') -> str:
    """
    Obtiene el color apropiado para mostrar ganancias/pérdidas
    
    Args:
        value (float): Valor (positivo = ganancia, negativo = pérdida)
        theme_name (str): Nombre del tema
        
    Returns:
        str: Color hexadecimal apropiado
    """
    colors = get_theme_colors(theme_name)
    
    if value > 0:
        return colors['bull']
    elif value < 0:
        return colors['bear']
    else:
        return colors['neutral']

def get_risk_color(risk_level: str, theme_name: str = 'dark') -> str:
    """
    Obtiene el color apropiado para el nivel de riesgo
    
    Args:
        risk_level (str): Nivel de riesgo ('low', 'medium', 'high')
        theme_name (str): Nombre del tema
        
    Returns:
        str: Color hexadecimal apropiado
    """
    colors = get_theme_colors(theme_name)
    
    risk_colors = {
        'low': colors['online'],
        'medium': colors['warning'], 
        'high': colors['offline']
    }
    
    return risk_colors.get(risk_level.lower(), colors['neutral'])

# Configuración de componentes específicos
COMPONENT_STYLES = {
    'metric_card': {
        'dark': {
            'backgroundColor': '#2d2d2d',
            'border': '1px solid #3d3d3d',
            'borderRadius': '12px',
            'padding': '1.5rem',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.3)',
            'transition': 'all 0.3s ease',
            'color': '#ffffff'
        },
        'light': {
            'backgroundColor': '#ffffff',
            'border': '1px solid #dee2e6',
            'borderRadius': '12px',
            'padding': '1.5rem',
            'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
            'transition': 'all 0.3s ease',
            'color': '#212529'
        }
    },
    
    'sidebar': {
        'dark': {
            'backgroundColor': '#1a1a1a',
            'borderRight': '1px solid #3d3d3d',
            'width': '250px',
            'height': '100vh',
            'position': 'fixed',
            'left': '0',
            'top': '0',
            'paddingTop': '80px',
            'color': '#ffffff'
        },
        'light': {
            'backgroundColor': '#f5f5f5',
            'borderRight': '1px solid #dee2e6',
            'width': '250px',
            'height': '100vh',
            'position': 'fixed',
            'left': '0',
            'top': '0',
            'paddingTop': '80px',
            'color': '#212529'
        }
    }
}

def get_component_style(component: str, theme_name: str = 'dark') -> Dict[str, Any]:
    """
    Obtiene los estilos para un componente específico
    
    Args:
        component (str): Nombre del componente
        theme_name (str): Nombre del tema
        
    Returns:
        Dict[str, Any]: Estilos del componente
    """
    if component not in COMPONENT_STYLES:
        return {}
    
    if theme_name not in COMPONENT_STYLES[component]:
        theme_name = 'dark'
    
    return COMPONENT_STYLES[component][theme_name]