#!/usr/bin/env python3
"""Fachada de configuración para el módulo control"""

from typing import Dict, Any
from config.unified_config import get_config_manager


class ControlConfig:
    """Configuración centralizada del módulo control"""

    def __init__(self):
        self._manager = get_config_manager()

    @property
    def telegram(self) -> Dict[str, Any]:
        return self._manager.get_telegram_config() or {}

    @property
    def security(self) -> Dict[str, Any]:
        return self._manager.get('security', {}) or {}

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._manager.get('monitoring.metrics', {}) or {}


# Singleton
control_config = ControlConfig()


