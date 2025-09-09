"""
monitoring/config/chart_config.py
Configuración de Gráficos - Trading Bot v10

Este módulo contiene toda la configuración específica para gráficos
del dashboard: colores, estilos, layouts, indicadores técnicos, etc.
Proporciona configuraciones optimizadas para diferentes tipos de gráficos.
"""

from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN PRINCIPAL DE GRÁFICOS
# ============================================================================

# Configuración base para todos los gráficos
BASE_CHART_CONFIG = {
    'height': 600,
    'responsive': True,
    'displayModeBar': True,
    'displaylogo': False,
    'scrollZoom': True,
    'doubleClick': 'reset+autosize',
    'showTips': True,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'trading_chart',
        'height': 800,
        'width': 1200,
        'scale': 2
    },
    'modeBarButtonsToRemove': [
        'lasso2d', 'select2d', 'toggleSpikelines',
        'hoverCompareCartesian', 'hoverClosestCartesian'
    ]
}

# ============================================================================
# CONFIGURACIÓN POR TIPO DE GRÁFICO
# ============================================================================

# Configuración para gráficos de velas (Candlestick)
CANDLESTICK_CONFIG = {
    **BASE_CHART_CONFIG,
    'height': 700,
    'rangeslider_visible': False,
    'xaxis_rangeslider_visible': False,
    'hovermode': 'x unified',
    'dragmode': 'pan',
    'layout': {
        'showlegend': True,
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        },
        'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50},
        'xaxis': {
            'showgrid': True,
            'gridwidth': 1,
            'gridcolor': 'rgba(128,128,128,0.2)',
            'showspikes': True,
            'spikecolor': 'rgba(255,255,255,0.5)',
            'spikethickness': 1,
            'spikedash': 'dot',
            'type': 'date'
        },
        'yaxis': {
            'showgrid': True,
            'gridwidth': 1,
            'gridcolor': 'rgba(128,128,128,0.2)',
            'showspikes': True,
            'spikecolor': 'rgba(255,255,255,0.5)',
            'spikethickness': 1,
            'spikedash': 'dot',
            'side': 'right'
        }
    }
}

# Configuración para gráficos de líneas de rendimiento
PERFORMANCE_CHART_CONFIG = {
    **BASE_CHART_CONFIG,
    'height': 400,
    'hovermode': 'x unified',
    'layout': {
        'showlegend': True,
        'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40},
        'xaxis': {
            'showgrid': True,
            'gridcolor': 'rgba(128,128,128,0.1)'
        },
        'yaxis': {
            'showgrid': True,
            'gridcolor': 'rgba(128,128,128,0.1)',
            'zeroline': True,
            'zerolinecolor': 'rgba(128,128,128,0.5)'
        }
    }
}

# Configuración para gráficos de barras de volumen
VOLUME_CHART_CONFIG = {
    **BASE_CHART_CONFIG,
    'height': 200,
    'hovermode': 'x unified',
    'layout': {
        'showlegend': False,
        'margin': {'l': 50, 'r': 50, 't': 20, 'b': 40},
        'xaxis': {
            'showgrid': False,
            'type': 'date'
        },
        'yaxis': {
            'showgrid': True,
            'gridcolor': 'rgba(128,128,128,0.1)',
            'side': 'right'
        }
    }
}

# Configuración para heatmaps
HEATMAP_CONFIG = {
    **BASE_CHART_CONFIG,
    'height': 400,
    'hovermode': 'closest',
    'layout': {
        'showlegend': False,
        'margin': {'l': 100, 'r': 50, 't': 50, 'b': 100}
    }
}

# ============================================================================
# ESQUEMAS DE COLORES
# ============================================================================

# Colores principales del trading
TRADING_COLORS = {
    'bullish': '#00C853',      # Verde brillante para velas alcistas
    'bearish': '#FF1744',      # Rojo brillante para velas bajistas
    'neutral': '#FFC107',      # Amarillo para neutral
    'volume_up': '#4CAF50',    # Verde para volumen en alza
    'volume_down': '#F44336',  # Rojo para volumen en baja
    'background': '#121212',   # Fondo oscuro
    'surface': '#1E1E1E',      # Superficie elevada
    'primary': '#BB86FC',      # Color primario
    'secondary': '#03DAC6',    # Color secundario
    'text': '#FFFFFF',         # Texto principal
    'text_secondary': '#BBBBBB' # Texto secundario
}

# Colores para indicadores técnicos
INDICATOR_COLORS = {
    'sma_20': '#FF9800',       # Naranja
    'sma_50': '#2196F3',       # Azul
    'sma_200': '#9C27B0',      # Púrpura
    'ema_12': '#E91E63',       # Rosa
    'ema_26': '#3F51B5',       # Índigo
    'bollinger_upper': '#607D8B',  # Azul grisáceo
    'bollinger_middle': '#795548', # Marrón
    'bollinger_lower': '#607D8B',  # Azul grisáceo
    'rsi': '#FF5722',          # Rojo naranja
    'macd_line': '#00BCD4',    # Cian
    'macd_signal': '#FF9800',  # Naranja
    'macd_histogram': '#4CAF50', # Verde
    'support': '#4CAF50',      # Verde para soporte
    'resistance': '#F44336',   # Rojo para resistencia
    'trend_up': '#00C853',     # Verde brillante
    'trend_down': '#FF1744'    # Rojo brillante
}

# Paleta de colores extendida para múltiples series
EXTENDED_COLOR_PALETTE = [
    '#BB86FC', '#03DAC6', '#CF6679', '#018786',
    '#FF0266', '#FFA726', '#66BB6A', '#42A5F5',
    '#AB47BC', '#26C6DA', '#78909C', '#8D6E63',
    '#FFD54F', '#FF8A65', '#A1C181', '#7986CB'
]

# ============================================================================
# CONFIGURACIÓN DE INDICADORES TÉCNICOS
# ============================================================================

TECHNICAL_INDICATORS_CONFIG = {
    'sma': {
        'periods': [20, 50, 200],
        'colors': ['#FF9800', '#2196F3', '#9C27B0'],
        'line_width': 2,
        'enabled_by_default': [20, 50]
    },
    'ema': {
        'periods': [12, 26, 50],
        'colors': ['#E91E63', '#3F51B5', '#673AB7'],
        'line_width': 2,
        'enabled_by_default': [12, 26]
    },
    'bollinger_bands': {
        'period': 20,
        'std_dev': 2,
        'colors': {
            'upper': '#607D8B',
            'middle': '#795548',
            'lower': '#607D8B',
            'fill': 'rgba(96, 125, 139, 0.1)'
        },
        'line_width': 1,
        'fill_area': True
    },
    'rsi': {
        'period': 14,
        'color': '#FF5722',
        'line_width': 2,
        'overbought_level': 70,
        'oversold_level': 30,
        'level_colors': {
            'overbought': '#F44336',
            'oversold': '#4CAF50',
            'neutral': '#FFC107'
        }
    },
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'colors': {
            'macd': '#00BCD4',
            'signal': '#FF9800',
            'histogram': '#4CAF50'
        },
        'line_width': 2
    },
    'support_resistance': {
        'color_support': '#4CAF50',
        'color_resistance': '#F44336',
        'line_width': 2,
        'line_dash': 'dash',
        'opacity': 0.7
    }
}

# ============================================================================
# CONFIGURACIÓN DE SEÑALES DE TRADING
# ============================================================================

TRADING_SIGNALS_CONFIG = {
    'buy_signal': {
        'color': '#00C853',
        'symbol': 'triangle-up',
        'size': 15,
        'line_color': '#FFFFFF',
        'line_width': 2
    },
    'sell_signal': {
        'color': '#FF1744',
        'symbol': 'triangle-down',
        'size': 15,
        'line_color': '#FFFFFF',
        'line_width': 2
    },
    'hold_signal': {
        'color': '#FFC107',
        'symbol': 'circle',
        'size': 10,
        'line_color': '#FFFFFF',
        'line_width': 1
    },
    'entry_point': {
        'color': '#00E676',
        'symbol': 'diamond',
        'size': 12,
        'line_color': '#FFFFFF',
        'line_width': 2
    },
    'exit_point': {
        'color': '#FF6D00',
        'symbol': 'diamond',
        'size': 12,
        'line_color': '#FFFFFF',
        'line_width': 2
    }
}

# ============================================================================
# CONFIGURACIÓN DE ANOTACIONES
# ============================================================================

ANNOTATIONS_CONFIG = {
    'default': {
        'arrowcolor': '#FFFFFF',
        'arrowwidth': 2,
        'arrowhead': 2,
        'bgcolor': 'rgba(0,0,0,0.8)',
        'bordercolor': '#FFFFFF',
        'borderwidth': 1,
        'font': {
            'color': '#FFFFFF',
            'size': 12
        }
    },
    'profit': {
        'arrowcolor': '#00C853',
        'bgcolor': 'rgba(0, 200, 83, 0.1)',
        'bordercolor': '#00C853',
        'font': {'color': '#00C853'}
    },
    'loss': {
        'arrowcolor': '#FF1744',
        'bgcolor': 'rgba(255, 23, 68, 0.1)',
        'bordercolor': '#FF1744',
        'font': {'color': '#FF1744'}
    },
    'warning': {
        'arrowcolor': '#FFC107',
        'bgcolor': 'rgba(255, 193, 7, 0.1)',
        'bordercolor': '#FFC107',
        'font': {'color': '#FFC107'}
    }
}

# ============================================================================
# CONFIGURACIÓN DE TEMAS
# ============================================================================

# Tema oscuro (por defecto)
DARK_THEME = {
    'layout': {
        'paper_bgcolor': '#121212',
        'plot_bgcolor': '#1E1E1E',
        'font': {
            'color': '#FFFFFF',
            'family': 'Roboto, sans-serif'
        },
        'colorway': EXTENDED_COLOR_PALETTE
    },
    'annotations': {
        'font': {'color': '#FFFFFF'},
        'arrowcolor': '#FFFFFF'
    }
}

# Tema claro
LIGHT_THEME = {
    'layout': {
        'paper_bgcolor': '#FFFFFF',
        'plot_bgcolor': '#FAFAFA',
        'font': {
            'color': '#333333',
            'family': 'Roboto, sans-serif'
        },
        'colorway': [
            '#1976D2', '#388E3C', '#F57C00', '#7B1FA2',
            '#C2185B', '#00796B', '#5D4037', '#455A64'
        ]
    },
    'annotations': {
        'font': {'color': '#333333'},
        'arrowcolor': '#333333'
    }
}

# ============================================================================
# CONFIGURACIÓN DE PERÍODOS TEMPORALES
# ============================================================================

TIME_PERIODS_CONFIG = {
    '1m': {
        'label': '1 Minuto',
        'max_candles': 500,
        'update_interval': 1000,  # 1 segundo
        'ideal_for': ['scalping', 'entries']
    },
    '5m': {
        'label': '5 Minutos',
        'max_candles': 1000,
        'update_interval': 5000,  # 5 segundos
        'ideal_for': ['day_trading', 'short_term']
    },
    '15m': {
        'label': '15 Minutos',
        'max_candles': 2000,
        'update_interval': 15000,  # 15 segundos
        'ideal_for': ['swing_trading', 'intraday']
    },
    '1h': {
        'label': '1 Hora',
        'max_candles': 5000,
        'update_interval': 60000,  # 1 minuto
        'ideal_for': ['trend_analysis', 'position_trading']
    },
    '4h': {
        'label': '4 Horas',
        'max_candles': 10000,
        'update_interval': 240000,  # 4 minutos
        'ideal_for': ['swing_trading', 'weekly_analysis']
    },
    '1d': {
        'label': '1 Día',
        'max_candles': 20000,
        'update_interval': 900000,  # 15 minutos
        'ideal_for': ['long_term', 'monthly_analysis']
    }
}

# ============================================================================
# UTILIDADES DE CONFIGURACIÓN
# ============================================================================

def get_chart_config(chart_type: str) -> Dict[str, Any]:
    """
    Obtiene la configuración para un tipo específico de gráfico
    
    Args:
        chart_type (str): Tipo de gráfico ('candlestick', 'performance', etc.)
        
    Returns:
        Dict[str, Any]: Configuración del gráfico
    """
    configs = {
        'candlestick': CANDLESTICK_CONFIG,
        'performance': PERFORMANCE_CHART_CONFIG,
        'volume': VOLUME_CHART_CONFIG,
        'heatmap': HEATMAP_CONFIG
    }
    
    return configs.get(chart_type, BASE_CHART_CONFIG)

def get_indicator_config(indicator: str) -> Dict[str, Any]:
    """
    Obtiene la configuración para un indicador técnico específico
    
    Args:
        indicator (str): Nombre del indicador
        
    Returns:
        Dict[str, Any]: Configuración del indicador
    """
    return TECHNICAL_INDICATORS_CONFIG.get(indicator, {})

def get_color_scheme(scheme: str = 'trading') -> Dict[str, str]:
    """
    Obtiene un esquema de colores específico
    
    Args:
        scheme (str): Nombre del esquema ('trading', 'indicators', etc.)
        
    Returns:
        Dict[str, str]: Esquema de colores
    """
    schemes = {
        'trading': TRADING_COLORS,
        'indicators': INDICATOR_COLORS
    }
    
    return schemes.get(scheme, TRADING_COLORS)

def create_candlestick_trace(df, name: str = "Price", **kwargs) -> go.Candlestick:
    """
    Crea un trace de velas japonesas con configuración optimizada
    
    Args:
        df: DataFrame con datos OHLCV
        name (str): Nombre del trace
        **kwargs: Argumentos adicionales
        
    Returns:
        go.Candlestick: Trace configurado
    """
    return go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=name,
        increasing=dict(line=dict(color=TRADING_COLORS['bullish'])),
        decreasing=dict(line=dict(color=TRADING_COLORS['bearish'])),
        **kwargs
    )

def create_volume_trace(df, name: str = "Volume", **kwargs) -> go.Bar:
    """
    Crea un trace de volumen con colores condicionales
    
    Args:
        df: DataFrame con datos OHLCV
        name (str): Nombre del trace
        **kwargs: Argumentos adicionales
        
    Returns:
        go.Bar: Trace de volumen configurado
    """
    colors = [
        TRADING_COLORS['volume_up'] if close >= open 
        else TRADING_COLORS['volume_down']
        for close, open in zip(df['close'], df['open'])
    ]
    
    return go.Bar(
        x=df.index,
        y=df['volume'],
        name=name,
        marker=dict(color=colors),
        opacity=0.7,
        **kwargs
    )

def apply_theme(fig: go.Figure, theme: str = 'dark') -> go.Figure:
    """
    Aplica un tema específico a un gráfico
    
    Args:
        fig (go.Figure): Figura de Plotly
        theme (str): Tema a aplicar ('dark', 'light')
        
    Returns:
        go.Figure: Figura con tema aplicado
    """
    theme_config = DARK_THEME if theme == 'dark' else LIGHT_THEME
    
    fig.update_layout(**theme_config['layout'])
    
    return fig

def get_signal_marker_config(signal_type: str) -> Dict[str, Any]:
    """
    Obtiene configuración de marcadores para señales de trading
    
    Args:
        signal_type (str): Tipo de señal ('buy', 'sell', 'hold', etc.)
        
    Returns:
        Dict[str, Any]: Configuración del marcador
    """
    signal_map = {
        'buy': 'buy_signal',
        'sell': 'sell_signal',
        'hold': 'hold_signal',
        'entry': 'entry_point',
        'exit': 'exit_point'
    }
    
    signal_key = signal_map.get(signal_type, 'hold_signal')
    return TRADING_SIGNALS_CONFIG[signal_key]

# ============================================================================
# CONFIGURACIÓN DE EXPORTACIÓN
# ============================================================================

EXPORT_CONFIG = {
    'formats': {
        'png': {
            'width': 1200,
            'height': 800,
            'scale': 2
        },
        'jpg': {
            'width': 1200,
            'height': 800,
            'scale': 2
        },
        'svg': {
            'width': 1200,
            'height': 800
        },
        'pdf': {
            'width': 1200,
            'height': 800,
            'scale': 1
        }
    },
    'default_filename': 'trading_chart_{timestamp}',
    'include_timestamp': True
}

# ============================================================================
# VALIDACIÓN Y CONFIGURACIÓN DINÁMICA
# ============================================================================

def validate_chart_config(config: Dict[str, Any]) -> bool:
    """
    Valida una configuración de gráfico
    
    Args:
        config (Dict[str, Any]): Configuración a validar
        
    Returns:
        bool: True si es válida, False en caso contrario
    """
    required_keys = ['height', 'responsive']
    return all(key in config for key in required_keys)

def merge_chart_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combina múltiples configuraciones de gráfico
    
    Args:
        *configs: Configuraciones a combinar
        
    Returns:
        Dict[str, Any]: Configuración combinada
    """
    result = {}
    for config in configs:
        result.update(config)
    return result

# Configuración final exportada
CHART_CONFIG = {
    'base': BASE_CHART_CONFIG,
    'candlestick': CANDLESTICK_CONFIG,
    'performance': PERFORMANCE_CHART_CONFIG,
    'volume': VOLUME_CHART_CONFIG,
    'heatmap': HEATMAP_CONFIG,
    'colors': {
        'trading': TRADING_COLORS,
        'indicators': INDICATOR_COLORS,
        'palette': EXTENDED_COLOR_PALETTE
    },
    'indicators': TECHNICAL_INDICATORS_CONFIG,
    'signals': TRADING_SIGNALS_CONFIG,
    'themes': {
        'dark': DARK_THEME,
        'light': LIGHT_THEME
    },
    'timeframes': TIME_PERIODS_CONFIG,
    'export': EXPORT_CONFIG
}