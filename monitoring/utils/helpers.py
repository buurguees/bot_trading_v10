"""
monitoring/utils/helpers.py
Funciones de ayuda y utilidades para el dashboard
"""

from datetime import datetime
from typing import Union, Any
import logging

logger = logging.getLogger(__name__)

def format_currency(value: Union[float, int], currency: str = "$", decimals: int = 2) -> str:
    """Formatea un valor como moneda"""
    try:
        if value is None:
            return f"{currency}0.00"
        
        if isinstance(value, (int, float)):
            return f"{currency}{value:,.{decimals}f}"
        else:
            return f"{currency}0.00"
    except Exception as e:
        logger.error(f"Error formateando moneda: {e}")
        return f"{currency}0.00"

def format_percentage(value: Union[float, int], decimals: int = 2) -> str:
    """Formatea un valor como porcentaje"""
    try:
        if value is None:
            return "0.00%"
        
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}%"
        else:
            return "0.00%"
    except Exception as e:
        logger.error(f"Error formateando porcentaje: {e}")
        return "0.00%"

def format_number(value: Union[float, int], decimals: int = 2) -> str:
    """Formatea un número con separadores de miles"""
    try:
        if value is None:
            return "0.00"
        
        if isinstance(value, (int, float)):
            return f"{value:,.{decimals}f}"
        else:
            return "0.00"
    except Exception as e:
        logger.error(f"Error formateando número: {e}")
        return "0.00"

def format_timestamp(timestamp: Union[datetime, str, int, float], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Formatea un timestamp a string legible"""
    try:
        if timestamp is None:
            return "N/A"
        
        if isinstance(timestamp, datetime):
            return timestamp.strftime(format_str)
        elif isinstance(timestamp, (int, float)):
            # Asumir que es un timestamp Unix
            if timestamp > 1e10:  # Milisegundos
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp).strftime(format_str)
        elif isinstance(timestamp, str):
            # Intentar parsear como datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime(format_str)
            except:
                return timestamp
        else:
            return str(timestamp)
    except Exception as e:
        logger.error(f"Error formateando timestamp: {e}")
        return "N/A"

def format_duration(seconds: Union[int, float]) -> str:
    """Formatea una duración en segundos a formato legible"""
    try:
        if seconds is None or seconds < 0:
            return "0s"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"
    except Exception as e:
        logger.error(f"Error formateando duración: {e}")
        return "0s"

def get_color_for_value(value: Union[float, int], positive_color: str = "#00ff88", negative_color: str = "#ff4444", neutral_color: str = "#cccccc") -> str:
    """Obtiene un color basado en el valor (positivo/negativo)"""
    try:
        if value is None:
            return neutral_color
        
        if isinstance(value, (int, float)):
            if value > 0:
                return positive_color
            elif value < 0:
                return negative_color
            else:
                return neutral_color
        else:
            return neutral_color
    except Exception as e:
        logger.error(f"Error obteniendo color: {e}")
        return neutral_color

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Trunca una cadena a una longitud máxima"""
    try:
        if not isinstance(text, str):
            text = str(text)
        
        if len(text) <= max_length:
            return text
        else:
            return text[:max_length - len(suffix)] + suffix
    except Exception as e:
        logger.error(f"Error truncando string: {e}")
        return str(text)[:max_length]

def safe_divide(numerator: Union[float, int], denominator: Union[float, int], default: Union[float, int] = 0) -> Union[float, int]:
    """División segura que evita división por cero"""
    try:
        if denominator is None or denominator == 0:
            return default
        
        if numerator is None:
            return default
        
        return numerator / denominator
    except Exception as e:
        logger.error(f"Error en división segura: {e}")
        return default
