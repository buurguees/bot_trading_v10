"""
monitoring/config/dashboard_config.py
Configuración del Dashboard - Trading Bot v10

Contiene todas las configuraciones específicas del dashboard,
incluyendo intervalos de actualización, layout, colores,
y configuraciones por defecto.
"""

from typing import Dict, List, Any
from datetime import timedelta
import os
from pathlib import Path
from copy import deepcopy

# Configuración principal del dashboard
# Aplicar overrides desde variables de entorno (cuando existan)
def _apply_env_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    new_cfg = deepcopy(cfg)
    host = os.getenv('DASHBOARD_HOST')
    port = os.getenv('DASHBOARD_PORT')
    debug = os.getenv('DASHBOARD_DEBUG')
    upd = os.getenv('DASHBOARD_UPDATE_INTERVAL')
    if host:
        new_cfg['default_host'] = host
    if port and port.isdigit():
        new_cfg['default_port'] = int(port)
    if debug is not None:
        new_cfg['debug_mode'] = debug.lower() in ('1', 'true', 'yes', 'on')
    if upd and upd.isdigit():
        new_cfg['update_interval'] = max(100, int(upd))
    return new_cfg

DASHBOARD_CONFIG = _apply_env_overrides({
    # Configuración del servidor
    'default_host': '127.0.0.1',
    'default_port': 8050,
    'auto_open_browser': True,
    'debug_mode': False,
    
    # Tema por defecto
    'default_theme': 'dark',
    
    # Intervalos de actualización (en milisegundos)
    'update_interval': 5000,          # 5 segundos - actualización general
    'fast_update_interval': 1000,     # 1 segundo - datos críticos
    'slow_update_interval': 30000,    # 30 segundos - métricas pesadas
    'real_time_interval': 500,        # 500ms - datos en tiempo real
    
    # Configuración de caché
    'cache_timeout': 300,             # 5 minutos
    'enable_cache': True,
    'max_cache_size': 100,            # MB
    
    # Configuración de datos
    'default_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
    'default_timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
    'default_lookback_days': 30,
    'max_data_points': 1000,
    
    # Configuración de gráficos
    'chart_height': 400,
    'chart_margin': {'t': 40, 'b': 40, 'l': 60, 'r': 60},
    'show_rangeslider': False,
    'show_legend': True,
    'responsive': True,
    
    # Configuración de tablas
    'table_page_size': 20,
    'table_height': 400,
    'enable_sorting': True,
    'enable_filtering': True,
    
    # Configuración de alertas
    'enable_notifications': True,
    'notification_timeout': 5000,     # 5 segundos
    'max_notifications': 5,
    
    # Configuración de métricas
    'currency_format': 'USD',
    'decimal_places': 2,
    'percentage_decimal_places': 2,
    'large_number_format': 'K',       # K, M, B
    
    # Configuración de rendimiento
    'enable_lazy_loading': True,
    'batch_size': 50,
    'max_concurrent_requests': 10,
    
    # Configuración de logs
    'log_level': 'INFO',
    'log_to_console': True,
    'log_to_file': True,
    'max_log_files': 10,
    
    # Configuración de seguridad
    'enable_cors': True,
    'allowed_origins': ['http://localhost:8050', 'http://127.0.0.1:8050'],
    'csrf_protection': False,         # Deshabilitado para desarrollo
    
    # Configuración experimental
    'enable_experimental_features': False,
    'enable_beta_components': False
})

# Configuración específica por página
PAGE_CONFIG = {
    'home': {
        'refresh_interval': 5000,
        'show_overview_cards': True,
        'cards_per_row': 3,
        'show_recent_trades': True,
        'max_recent_trades': 10,
        'show_performance_chart': True,
        'chart_timeframe': '1h'
    },
    
    'charts': {
        'refresh_interval': 2000,
        'default_timeframe': '15m',
        'default_symbol': 'BTCUSDT',
        'show_indicators': True,
        'available_indicators': [
            'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26',
            'RSI', 'MACD', 'Bollinger_Bands', 'Volume'
        ],
        'max_indicators': 5,
        'show_volume': True,
        'candlestick_colors': {
            'increasing': '#00c851',
            'decreasing': '#ff4444'
        }
    },
    
    'cycles': {
        'refresh_interval': 10000,
        'default_lookback_days': 90,
        'show_active_cycles': True,
        'show_completed_cycles': True,
        'max_cycles_displayed': 50,
        'cycle_metrics': [
            'duration', 'total_return', 'win_rate', 
            'sharpe_ratio', 'max_drawdown'
        ]
    },
    
    'live_trading': {
        'refresh_interval': 1000,
        'show_order_book': True,
        'show_recent_trades': True,
        'max_recent_trades': 20,
        'show_open_positions': True,
        'show_pnl_chart': True,
        'enable_trading_controls': False,  # Seguridad: deshabilitado por defecto
        'position_size_limits': {
            'min_size': 0.001,
            'max_size': 1.0
        }
    },
    
    'performance': {
        'refresh_interval': 15000,
        'default_period': '30d',
        'available_periods': ['1d', '7d', '30d', '90d', '1y', 'all'],
        'show_drawdown_chart': True,
        'show_returns_distribution': True,
        'show_monthly_returns': True,
        'performance_metrics': [
            'total_return', 'annualized_return', 'volatility',
            'sharpe_ratio', 'sortino_ratio', 'max_drawdown',
            'win_rate', 'profit_factor', 'calmar_ratio'
        ]
    },
    
    'risk_analysis': {
        'refresh_interval': 30000,
        'show_var_analysis': True,
        'show_correlation_matrix': True,
        'show_stress_tests': True,
        'confidence_levels': [0.95, 0.99],
        'monte_carlo_simulations': 1000,
        'stress_scenarios': [
            'market_crash', 'volatility_spike', 'liquidity_crisis'
        ]
    },
    
    'model_status': {
        'refresh_interval': 10000,
        'show_model_metrics': True,
        'show_prediction_accuracy': True,
        'show_feature_importance': True,
        'show_training_history': True,
        'metrics_history_days': 30
    },
    
    'settings': {
        'show_system_info': True,
        'show_api_status': True,
        'show_logs': True,
        'max_log_entries': 100,
        'editable_settings': [
            'symbols', 'timeframes', 'risk_limits',
            'notification_settings', 'theme_preferences'
        ]
    }
}

# Configuración de métricas y KPIs
METRICS_CONFIG = {
    'financial_metrics': {
        'total_return': {
            'name': 'Retorno Total',
            'format': 'currency',
            'color_by_value': True,
            'precision': 2
        },
        'total_return_percentage': {
            'name': 'Retorno %',
            'format': 'percentage',
            'color_by_value': True,
            'precision': 2
        },
        'win_rate': {
            'name': 'Tasa de Éxito',
            'format': 'percentage',
            'color_by_value': True,
            'precision': 1,
            'thresholds': {'good': 60, 'warning': 50}
        },
        'sharpe_ratio': {
            'name': 'Ratio Sharpe',
            'format': 'decimal',
            'color_by_value': True,
            'precision': 2,
            'thresholds': {'good': 1.5, 'warning': 1.0}
        },
        'max_drawdown': {
            'name': 'Drawdown Máx.',
            'format': 'percentage',
            'color_by_value': True,
            'precision': 2,
            'invert_colors': True,  # Menor es mejor
            'thresholds': {'good': 5, 'warning': 15}
        },
        'profit_factor': {
            'name': 'Factor Profit',
            'format': 'decimal',
            'color_by_value': True,
            'precision': 2,
            'thresholds': {'good': 1.5, 'warning': 1.2}
        }
    },
    
    'trading_metrics': {
        'total_trades': {
            'name': 'Total Trades',
            'format': 'integer',
            'color_by_value': False
        },
        'winning_trades': {
            'name': 'Trades Ganadores',
            'format': 'integer',
            'color_by_value': False
        },
        'avg_trade_duration': {
            'name': 'Duración Promedio',
            'format': 'duration',
            'color_by_value': False
        },
        'largest_win': {
            'name': 'Mayor Ganancia',
            'format': 'currency',
            'color_by_value': False
        },
        'largest_loss': {
            'name': 'Mayor Pérdida',
            'format': 'currency',
            'color_by_value': False
        }
    },
    
    'risk_metrics': {
        'var_95': {
            'name': 'VaR 95%',
            'format': 'currency',
            'color_by_value': True,
            'precision': 2,
            'invert_colors': True
        },
        'portfolio_correlation': {
            'name': 'Correlación',
            'format': 'percentage',
            'color_by_value': True,
            'precision': 1
        },
        'leverage': {
            'name': 'Apalancamiento',
            'format': 'decimal',
            'color_by_value': True,
            'precision': 2,
            'thresholds': {'warning': 2.0, 'danger': 5.0}
        }
    }
}

# Configuración de alertas y notificaciones
ALERTS_CONFIG = {
    'enable_alerts': True,
    'alert_types': {
        'performance': {
            'enabled': True,
            'thresholds': {
                'daily_loss_limit': -5.0,  # -5%
                'drawdown_limit': -15.0,   # -15%
                'profit_target': 10.0      # +10%
            }
        },
        'system': {
            'enabled': True,
            'monitor': [
                'connection_lost', 'api_error', 'model_error',
                'high_latency', 'memory_usage'
            ]
        },
        'trading': {
            'enabled': True,
            'monitor': [
                'position_opened', 'position_closed', 'stop_loss_hit',
                'take_profit_hit', 'unusual_volume'
            ]
        }
    },
    'notification_channels': {
        'dashboard': True,
        'email': False,      # Requiere configuración SMTP
        'webhook': False,    # Requiere URL de webhook
        'desktop': True      # Notificaciones del sistema
    }
}

# Configuración de exportación y reportes
EXPORT_CONFIG = {
    'enable_export': True,
    'formats': ['json', 'csv', 'excel', 'pdf'],
    'default_format': 'json',
    'include_charts': True,
    'max_export_records': 10000,
    'export_path': 'exports/',
    'auto_cleanup_days': 30
}

# Configuración de layout responsivo
LAYOUT_CONFIG = {
    'breakpoints': {
        'xs': 576,
        'sm': 768,
        'md': 992,
        'lg': 1200,
        'xl': 1400
    },
    'grid_columns': 12,
    'sidebar_width': {
        'desktop': 250,
        'tablet': 200,
        'mobile': 0  # Colapsado en móvil
    },
    'header_height': 60,
    'footer_height': 40,
    'content_padding': 20
}

# Configuración de componentes específicos
COMPONENT_CONFIG = {
    'cards': {
        'animation_duration': 300,
        'hover_elevation': 8,
        'border_radius': 12,
        'padding': 24
    },
    'charts': {
        'animation_duration': 750,
        'transition_duration': 500,
        'hover_mode': 'x unified',
        'dragmode': 'pan'
    },
    'tables': {
        'row_height': 40,
        'header_height': 45,
        'stripe_rows': True,
        'hover_rows': True,
        'pagination': True
    },
    'buttons': {
        'animation_duration': 200,
        'border_radius': 6,
        'padding': '8px 16px'
    }
}

# Configuración de desarrollo y debugging
DEV_CONFIG = {
    'enable_dev_tools': False,
    'show_component_ids': False,
    'log_callback_timing': False,
    'enable_hot_reload': False,
    'mock_data': False,
    'debug_mode': False
}

def get_config(section: str = None) -> Dict[str, Any]:
    """
    Obtiene la configuración completa o de una sección específica
    
    Args:
        section (str, optional): Sección específica a obtener
        
    Returns:
        Dict[str, Any]: Configuración solicitada
    """
    configs = {
        'dashboard': DASHBOARD_CONFIG,
        'pages': PAGE_CONFIG,
        'metrics': METRICS_CONFIG,
        'alerts': ALERTS_CONFIG,
        'export': EXPORT_CONFIG,
        'layout': LAYOUT_CONFIG,
        'components': COMPONENT_CONFIG,
        'dev': DEV_CONFIG
    }
    
    if section:
        return configs.get(section, {})
    
    return {
        'dashboard': DASHBOARD_CONFIG,
        'pages': PAGE_CONFIG,
        'metrics': METRICS_CONFIG,
        'alerts': ALERTS_CONFIG,
        'export': EXPORT_CONFIG,
        'layout': LAYOUT_CONFIG,
        'components': COMPONENT_CONFIG
    }

def update_config(section: str, updates: Dict[str, Any]) -> bool:
    """
    Actualiza la configuración de una sección específica
    
    Args:
        section (str): Sección a actualizar
        updates (Dict[str, Any]): Nuevos valores
        
    Returns:
        bool: True si se actualizó correctamente
    """
    def _validate(section_name: str, values: Dict[str, Any]) -> Dict[str, Any]:
        # Validación básica por tipo y límites razonables
        validators: Dict[str, Dict[str, Any]] = {
            'dashboard': {
                'default_host': str,
                'default_port': int,
                'auto_open_browser': bool,
                'debug_mode': bool,
                'update_interval': int,
                'fast_update_interval': int,
                'slow_update_interval': int,
                'real_time_interval': int,
            },
            'export': {
                'enable_export': bool,
                'formats': list,
                'default_format': str,
                'export_path': str,
                'max_export_records': int,
            },
        }
        allowed = validators.get(section_name, None)
        if not allowed:
            return values
        filtered: Dict[str, Any] = {}
        for k, v in values.items():
            expected = allowed.get(k)
            if expected and isinstance(v, expected):
                filtered[k] = v
        # límites
        if section_name == 'dashboard':
            for key in ['update_interval', 'fast_update_interval', 'slow_update_interval', 'real_time_interval']:
                if key in filtered and filtered[key] < 100:
                    filtered[key] = 100
            if 'default_port' in filtered and not (1 <= filtered['default_port'] <= 65535):
                filtered.pop('default_port')
        if section_name == 'export' and 'export_path' in filtered:
            try:
                Path(filtered['export_path']).mkdir(parents=True, exist_ok=True)
            except Exception:
                filtered.pop('export_path')
        return filtered

    try:
        if section == 'dashboard':
            DASHBOARD_CONFIG.update(_validate('dashboard', updates))
        elif section == 'pages':
            PAGE_CONFIG.update(updates)
        elif section == 'metrics':
            METRICS_CONFIG.update(updates)
        elif section == 'alerts':
            ALERTS_CONFIG.update(updates)
        elif section == 'export':
            EXPORT_CONFIG.update(_validate('export', updates))
        elif section == 'layout':
            LAYOUT_CONFIG.update(updates)
        elif section == 'components':
            COMPONENT_CONFIG.update(updates)
        elif section == 'dev':
            DEV_CONFIG.update(updates)
        else:
            return False
        return True
    except Exception:
        return False

def get_page_config(page_name: str) -> Dict[str, Any]:
    """
    Obtiene la configuración específica de una página
    
    Args:
        page_name (str): Nombre de la página
        
    Returns:
        Dict[str, Any]: Configuración de la página
    """
    return PAGE_CONFIG.get(page_name, {})

def get_metric_config(metric_name: str, category: str = 'financial_metrics') -> Dict[str, Any]:
    """
    Obtiene la configuración de una métrica específica
    
    Args:
        metric_name (str): Nombre de la métrica
        category (str): Categoría de la métrica
        
    Returns:
        Dict[str, Any]: Configuración de la métrica
    """
    return METRICS_CONFIG.get(category, {}).get(metric_name, {})

def is_dev_mode() -> bool:
    """
    Verifica si el dashboard está en modo desarrollo
    
    Returns:
        bool: True si está en modo desarrollo
    """
    return DEV_CONFIG.get('debug_mode', False) or DASHBOARD_CONFIG.get('debug_mode', False)