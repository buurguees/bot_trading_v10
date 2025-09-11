# Ruta: control/__init__.py
"""
Control Module - Bot Trading v10 Enterprise
==========================================

Módulo de control de Telegram para el bot de trading.
Maneja todos los comandos y comunicación con el usuario.

Submódulos:
- telegram_bot: Bot principal de Telegram
- handlers: Manejo de comandos
- metrics_sender: Envío de métricas
- security_guard: Protección de comandos
"""

from .telegram_bot import TelegramBot
from .handlers import Handlers
from .metrics_sender import MetricsSender
from .security_guard import SecurityGuard as TelegramSecurity

__all__ = [
    'TelegramBot',
    'Handlers', 
    'MetricsSender',
    'TelegramSecurity'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'