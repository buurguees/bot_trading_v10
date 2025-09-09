# Ruta: core/monitoring/config/layout_config.py
"""
monitoring/config/layout_config.py
Configuración de Layout y Diseño - Trading Bot v10

Este módulo contiene toda la configuración relacionada con el layout,
diseño responsivo, espaciado, grid system y estructura visual del dashboard.
Proporciona configuraciones consistentes para todos los componentes.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import dash_bootstrap_components as dbc

# ============================================================================
# BREAKPOINTS Y SISTEMA RESPONSIVO
# ============================================================================

# Breakpoints estándar para responsive design
BREAKPOINTS = {
    'xs': 0,      # Extra small devices (portrait phones)
    'sm': 576,    # Small devices (landscape phones)
    'md': 768,    # Medium devices (tablets)
    'lg': 992,    # Large devices (desktops)
    'xl': 1200,   # Extra large devices (large desktops)
    'xxl': 1400   # Extra extra large devices
}

# Configuración del grid system
GRID_CONFIG = {
    'columns': 12,
    'gutter_width': 24,      # Espaciado entre columnas en px
    'container_padding': 16, # Padding del contenedor
    'max_width': {
        'sm': 540,
        'md': 720,
        'lg': 960,
        'xl': 1140,
        'xxl': 1320
    }
}

# ============================================================================
# CONFIGURACIÓN DE COMPONENTES PRINCIPALES
# ============================================================================

# Configuración del Header/Navbar
HEADER_CONFIG = {
    'height': 64,
    'mobile_height': 56,
    'fixed': True,
    'z_index': 1000,
    'padding': {
        'horizontal': 24,
        'vertical': 16
    },
    'logo': {
        'width': 140,
        'height': 32,
        'mobile_width': 120,
        'mobile_height': 28
    },
    'nav_items': {
        'spacing': 32,
        'mobile_spacing': 16
    },
    'user_menu': {
        'width': 200,
        'max_height': 300
    }
}

# Configuración del Sidebar
SIDEBAR_CONFIG = {
    'width': {
        'desktop': 280,
        'tablet': 240,
        'mobile': 0  # Colapsado en móvil
    },
    'collapsed_width': 72,
    'z_index': 900,
    'transition_duration': '0.3s',
    'background': 'var(--bs-dark)',
    'border_radius': 0,
    'padding': {
        'top': 24,
        'horizontal': 16,
        'bottom': 24
    },
    'nav_items': {
        'height': 48,
        'spacing': 4,
        'icon_size': 20,
        'text_size': 14,
        'border_radius': 8
    },
    'sections': {
        'spacing': 32,
        'title_size': 12,
        'title_weight': 600
    }
}

# Configuración del contenido principal
MAIN_CONTENT_CONFIG = {
    'margin_left': {
        'desktop': 280,  # Ancho del sidebar
        'tablet': 240,
        'mobile': 0
    },
    'margin_top': 64,    # Altura del header
    'padding': {
        'desktop': 32,
        'tablet': 24,
        'mobile': 16
    },
    'max_width': None,   # Sin límite de ancho
    'min_height': 'calc(100vh - 64px)'
}

# Configuración del Footer
FOOTER_CONFIG = {
    'height': 48,
    'margin_left': {
        'desktop': 280,
        'tablet': 240,
        'mobile': 0
    },
    'padding': {
        'horizontal': 32,
        'vertical': 12
    },
    'background': 'var(--bs-light)',
    'border_top': '1px solid var(--bs-border-color)',
    'text_size': 12,
    'text_color': 'var(--bs-secondary)'
}

# ============================================================================
# CONFIGURACIÓN DE TARJETAS Y COMPONENTES
# ============================================================================

# Configuración base para tarjetas
CARD_CONFIG = {
    'border_radius': 12,
    'box_shadow': '0 2px 8px rgba(0,0,0,0.1)',
    'hover_shadow': '0 4px 16px rgba(0,0,0,0.15)',
    'transition': 'all 0.3s ease',
    'padding': {
        'small': 16,
        'medium': 24,
        'large': 32
    },
    'margin_bottom': 24,
    'border': '1px solid var(--bs-border-color)',
    'background': 'var(--bs-body-bg)'
}

# Configuración específica para tarjetas de métricas
METRIC_CARD_CONFIG = {
    **CARD_CONFIG,
    'min_height': 160,
    'title': {
        'size': 14,
        'weight': 600,
        'color': 'var(--bs-secondary)',
        'margin_bottom': 12
    },
    'value': {
        'size': 28,
        'weight': 700,
        'margin_bottom': 8
    },
    'change': {
        'size': 14,
        'weight': 500
    },
    'icon': {
        'size': 24,
        'position': 'top-right',
        'opacity': 0.7
    },
    'chart': {
        'height': 60,
        'margin_top': 16
    }
}

# Configuración para tarjetas de símbolo
SYMBOL_CARD_CONFIG = {
    **CARD_CONFIG,
    'min_height': 200,
    'header': {
        'height': 48,
        'padding': 16,
        'border_bottom': '1px solid var(--bs-border-color)'
    },
    'body': {
        'padding': 16
    },
    'metrics_grid': {
        'columns': 2,
        'gap': 12
    },
    'status_indicator': {
        'size': 8,
        'positions': ['active', 'warning', 'error']
    }
}

# ============================================================================
# CONFIGURACIÓN DE ESPACIADO Y TIPOGRAFÍA
# ============================================================================

# Sistema de espaciado consistente
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 16,
    'lg': 24,
    'xl': 32,
    'xxl': 48,
    'xxxl': 64
}

# Configuración tipográfica
TYPOGRAPHY = {
    'font_family': {
        'primary': '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'monospace': '"JetBrains Mono", "Fira Code", Consolas, monospace'
    },
    'font_sizes': {
        'xs': 10,
        'sm': 12,
        'base': 14,
        'lg': 16,
        'xl': 18,
        'xxl': 20,
        'xxxl': 24,
        'display_sm': 28,
        'display_md': 32,
        'display_lg': 40,
        'display_xl': 48
    },
    'font_weights': {
        'light': 300,
        'normal': 400,
        'medium': 500,
        'semibold': 600,
        'bold': 700,
        'extrabold': 800
    },
    'line_heights': {
        'tight': 1.2,
        'normal': 1.5,
        'relaxed': 1.7
    }
}

# ============================================================================
# CONFIGURACIÓN DE COLORES Y TEMAS
# ============================================================================

# Paleta de colores base
COLOR_PALETTE = {
    'primary': {
        50: '#f0f9ff',
        100: '#e0f2fe',
        200: '#bae6fd',
        300: '#7dd3fc',
        400: '#38bdf8',
        500: '#0ea5e9',  # Principal
        600: '#0284c7',
        700: '#0369a1',
        800: '#075985',
        900: '#0c4a6e'
    },
    'success': {
        50: '#f0fdf4',
        100: '#dcfce7',
        200: '#bbf7d0',
        300: '#86efac',
        400: '#4ade80',
        500: '#22c55e',  # Principal
        600: '#16a34a',
        700: '#15803d',
        800: '#166534',
        900: '#14532d'
    },
    'danger': {
        50: '#fef2f2',
        100: '#fee2e2',
        200: '#fecaca',
        300: '#fca5a5',
        400: '#f87171',
        500: '#ef4444',  # Principal
        600: '#dc2626',
        700: '#b91c1c',
        800: '#991b1b',
        900: '#7f1d1d'
    },
    'warning': {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b',  # Principal
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f'
    },
    'neutral': {
        50: '#fafafa',
        100: '#f5f5f5',
        200: '#e5e5e5',
        300: '#d4d4d4',
        400: '#a3a3a3',
        500: '#737373',
        600: '#525252',
        700: '#404040',
        800: '#262626',
        900: '#171717'
    }
}

# Configuración específica de tema oscuro
DARK_THEME_CONFIG = {
    'background': {
        'primary': '#0a0a0a',
        'secondary': '#151515',
        'tertiary': '#1f1f1f',
        'elevated': '#262626'
    },
    'text': {
        'primary': '#ffffff',
        'secondary': '#a3a3a3',
        'tertiary': '#737373',
        'disabled': '#525252'
    },
    'border': {
        'primary': '#404040',
        'secondary': '#262626',
        'tertiary': '#171717'
    },
    'accent': {
        'primary': '#0ea5e9',
        'success': '#22c55e',
        'danger': '#ef4444',
        'warning': '#f59e0b'
    }
}

# Configuración específica de tema claro
LIGHT_THEME_CONFIG = {
    'background': {
        'primary': '#ffffff',
        'secondary': '#fafafa',
        'tertiary': '#f5f5f5',
        'elevated': '#ffffff'
    },
    'text': {
        'primary': '#171717',
        'secondary': '#525252',
        'tertiary': '#737373',
        'disabled': '#a3a3a3'
    },
    'border': {
        'primary': '#e5e5e5',
        'secondary': '#d4d4d4',
        'tertiary': '#a3a3a3'
    },
    'accent': {
        'primary': '#0ea5e9',
        'success': '#22c55e',
        'danger': '#ef4444',
        'warning': '#f59e0b'
    }
}

# ============================================================================
# CONFIGURACIÓN DE ANIMACIONES Y TRANSICIONES
# ============================================================================

ANIMATION_CONFIG = {
    'duration': {
        'fast': '0.15s',
        'normal': '0.3s',
        'slow': '0.5s'
    },
    'easing': {
        'ease_in': 'cubic-bezier(0.4, 0, 1, 1)',
        'ease_out': 'cubic-bezier(0, 0, 0.2, 1)',
        'ease_in_out': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'bounce': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
    },
    'effects': {
        'fade_in': 'fadeIn 0.3s ease-out',
        'slide_up': 'slideUp 0.3s ease-out',
        'scale_in': 'scaleIn 0.2s ease-out',
        'hover_lift': 'transform: translateY(-2px)',
        'hover_scale': 'transform: scale(1.02)'
    }
}

# ============================================================================
# CONFIGURACIÓN DE COMPONENTES ESPECÍFICOS
# ============================================================================

# Configuración de botones
BUTTON_CONFIG = {
    'height': {
        'small': 32,
        'medium': 40,
        'large': 48
    },
    'padding': {
        'small': '6px 12px',
        'medium': '10px 16px',
        'large': '14px 20px'
    },
    'border_radius': 8,
    'font_weight': 500,
    'transition': 'all 0.2s ease',
    'hover_transform': 'translateY(-1px)',
    'active_transform': 'translateY(0)'
}

# Configuración de inputs y formularios
INPUT_CONFIG = {
    'height': 40,
    'padding': '10px 12px',
    'border_radius': 6,
    'border_width': 1,
    'font_size': 14,
    'transition': 'all 0.2s ease',
    'focus': {
        'border_color': 'var(--bs-primary)',
        'box_shadow': '0 0 0 3px rgba(14, 165, 233, 0.1)',
        'outline': 'none'
    }
}

# Configuración de tablas
TABLE_CONFIG = {
    'header': {
        'height': 48,
        'background': 'var(--bs-light)',
        'font_weight': 600,
        'font_size': 12,
        'text_transform': 'uppercase',
        'letter_spacing': '0.5px',
        'border_bottom': '2px solid var(--bs-primary)'
    },
    'row': {
        'height': 52,
        'padding': '12px 16px',
        'border_bottom': '1px solid var(--bs-border-color)',
        'hover_background': 'var(--bs-light)'
    },
    'cell': {
        'padding': '12px 16px',
        'font_size': 14,
        'vertical_align': 'middle'
    },
    'pagination': {
        'height': 48,
        'padding': '12px 16px',
        'border_top': '1px solid var(--bs-border-color)'
    }
}

# Configuración de modales
MODAL_CONFIG = {
    'overlay': {
        'background': 'rgba(0, 0, 0, 0.5)',
        'backdrop_filter': 'blur(4px)',
        'z_index': 1050
    },
    'container': {
        'max_width': {
            'small': 400,
            'medium': 600,
            'large': 800,
            'extra_large': 1000
        },
        'border_radius': 12,
        'box_shadow': '0 20px 40px rgba(0, 0, 0, 0.15)',
        'animation': 'modal-appear 0.3s ease-out'
    },
    'header': {
        'padding': '20px 24px 16px',
        'border_bottom': '1px solid var(--bs-border-color)'
    },
    'body': {
        'padding': '20px 24px'
    },
    'footer': {
        'padding': '16px 24px 20px',
        'border_top': '1px solid var(--bs-border-color)',
        'gap': 12
    }
}

# ============================================================================
# CONFIGURACIÓN DE DASHBOARD ESPECÍFICA
# ============================================================================

# Layout específico para página HOME
HOME_PAGE_LAYOUT = {
    'header': {
        'margin_bottom': 32,
        'title_size': 32,
        'subtitle_size': 16
    },
    'summary_cards': {
        'columns': {
            'desktop': 4,
            'tablet': 2,
            'mobile': 1
        },
        'gap': 24,
        'margin_bottom': 32
    },
    'symbol_cards': {
        'columns': {
            'desktop': 3,
            'tablet': 2,
            'mobile': 1
        },
        'gap': 24,
        'auto_fit': True,
        'min_card_width': 300
    }
}

# Layout específico para página CHARTS
CHARTS_PAGE_LAYOUT = {
    'controls': {
        'height': 60,
        'padding': '12px 0',
        'margin_bottom': 24,
        'gap': 16
    },
    'main_chart': {
        'height': 600,
        'margin_bottom': 24
    },
    'secondary_charts': {
        'height': 200,
        'columns': 2,
        'gap': 24
    },
    'sidebar': {
        'width': 300,
        'padding': 24
    }
}

# Layout específico para página CYCLES
CYCLES_PAGE_LAYOUT = {
    'filters': {
        'height': 80,
        'padding': '16px 0',
        'margin_bottom': 24
    },
    'table': {
        'min_height': 400,
        'max_height': 800
    },
    'pagination': {
        'margin_top': 24
    }
}

# ============================================================================
# UTILIDADES Y FUNCIONES HELPER
# ============================================================================

@dataclass
class LayoutBreakpoint:
    """Clase para manejar breakpoints de manera tipo-segura"""
    xs: Any = None
    sm: Any = None
    md: Any = None
    lg: Any = None
    xl: Any = None
    xxl: Any = None

def get_responsive_value(breakpoint_values: Union[Dict, LayoutBreakpoint], 
                        current_breakpoint: str = 'lg') -> Any:
    """
    Obtiene un valor responsivo basado en el breakpoint actual
    
    Args:
        breakpoint_values: Valores por breakpoint
        current_breakpoint: Breakpoint actual
        
    Returns:
        Any: Valor para el breakpoint actual
    """
    if isinstance(breakpoint_values, dict):
        # Buscar el valor más apropiado
        breakpoint_order = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs']
        current_index = breakpoint_order.index(current_breakpoint)
        
        for bp in breakpoint_order[current_index:]:
            if bp in breakpoint_values and breakpoint_values[bp] is not None:
                return breakpoint_values[bp]
        
        # Si no encuentra, buscar hacia arriba
        for bp in breakpoint_order[:current_index]:
            if bp in breakpoint_values and breakpoint_values[bp] is not None:
                return breakpoint_values[bp]
    
    return breakpoint_values

def create_responsive_columns(columns: Union[int, Dict[str, int]]) -> Dict[str, int]:
    """
    Crea configuración de columnas responsivas
    
    Args:
        columns: Número de columnas o dict con breakpoints
        
    Returns:
        Dict[str, int]: Configuración responsiva
    """
    if isinstance(columns, int):
        return {
            'xs': 1,
            'sm': min(2, columns),
            'md': min(3, columns),
            'lg': columns,
            'xl': columns,
            'xxl': columns
        }
    return columns

def get_bootstrap_col_class(columns: Union[int, Dict[str, int]]) -> str:
    """
    Genera clases de Bootstrap para columnas responsivas
    
    Args:
        columns: Configuración de columnas
        
    Returns:
        str: Clases CSS de Bootstrap
    """
    if isinstance(columns, int):
        return f"col-lg-{12 // columns}"
    
    classes = []
    for bp, cols in columns.items():
        if cols and cols > 0:
            col_width = 12 // cols
            if bp == 'xs':
                classes.append(f"col-{col_width}")
            else:
                classes.append(f"col-{bp}-{col_width}")
    
    return " ".join(classes)

def apply_spacing(element_type: str, size: str = 'md') -> Dict[str, str]:
    """
    Aplica espaciado consistente a un elemento
    
    Args:
        element_type: Tipo de elemento ('card', 'section', etc.)
        size: Tamaño del espaciado
        
    Returns:
        Dict[str, str]: Estilos CSS
    """
    spacing_value = SPACING.get(size, SPACING['md'])
    
    spacing_configs = {
        'card': {
            'margin-bottom': f'{spacing_value}px',
            'padding': f'{spacing_value}px'
        },
        'section': {
            'margin-bottom': f'{spacing_value * 2}px'
        },
        'item': {
            'margin-bottom': f'{spacing_value // 2}px'
        }
    }
    
    return spacing_configs.get(element_type, {})

def generate_css_variables(theme: str = 'dark') -> str:
    """
    Genera variables CSS para el tema especificado
    
    Args:
        theme: Tema a aplicar ('dark' o 'light')
        
    Returns:
        str: Variables CSS
    """
    theme_config = DARK_THEME_CONFIG if theme == 'dark' else LIGHT_THEME_CONFIG
    
    css_vars = [":root {"]
    
    for category, values in theme_config.items():
        for key, value in values.items():
            var_name = f"--{category}-{key}".replace('_', '-')
            css_vars.append(f"  {var_name}: {value};")
    
    # Agregar espaciado
    for size, value in SPACING.items():
        css_vars.append(f"  --spacing-{size}: {value}px;")
    
    # Agregar tipografía
    for category, values in TYPOGRAPHY.items():
        if isinstance(values, dict):
            for key, value in values.items():
                var_name = f"--{category}-{key}".replace('_', '-')
                if category == 'font_sizes':
                    css_vars.append(f"  {var_name}: {value}px;")
                else:
                    css_vars.append(f"  {var_name}: {value};")
    
    css_vars.append("}")
    
    return "\n".join(css_vars)

# ============================================================================
# CONFIGURACIÓN FINAL EXPORTADA
# ============================================================================

LAYOUT_CONFIG = {
    'breakpoints': BREAKPOINTS,
    'grid': GRID_CONFIG,
    'header': HEADER_CONFIG,
    'sidebar': SIDEBAR_CONFIG,
    'main_content': MAIN_CONTENT_CONFIG,
    'footer': FOOTER_CONFIG,
    'cards': {
        'base': CARD_CONFIG,
        'metric': METRIC_CARD_CONFIG,
        'symbol': SYMBOL_CARD_CONFIG
    },
    'spacing': SPACING,
    'typography': TYPOGRAPHY,
    'colors': COLOR_PALETTE,
    'themes': {
        'dark': DARK_THEME_CONFIG,
        'light': LIGHT_THEME_CONFIG
    },
    'animations': ANIMATION_CONFIG,
    'components': {
        'button': BUTTON_CONFIG,
        'input': INPUT_CONFIG,
        'table': TABLE_CONFIG,
        'modal': MODAL_CONFIG
    },
    'pages': {
        'home': HOME_PAGE_LAYOUT,
        'charts': CHARTS_PAGE_LAYOUT,
        'cycles': CYCLES_PAGE_LAYOUT
    }
}

# Funciones de utilidad exportadas
__all__ = [
    'LAYOUT_CONFIG',
    'BREAKPOINTS',
    'SPACING',
    'TYPOGRAPHY',
    'COLOR_PALETTE',
    'get_responsive_value',
    'create_responsive_columns',
    'get_bootstrap_col_class',
    'apply_spacing',
    'generate_css_variables'
]