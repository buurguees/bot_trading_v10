"""
monitoring/pages/__init__.py
Páginas del dashboard organizadas por funcionalidad
"""

from .home import create_home_page
from .trading import create_trading_page
from .analytics import create_analytics_page
from .settings import create_settings_page

__all__ = ['create_home_page', 'create_trading_page', 'create_analytics_page', 'create_settings_page']
