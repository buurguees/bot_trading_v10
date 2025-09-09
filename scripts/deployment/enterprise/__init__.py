# Ruta: scripts/deployment/enterprise/__init__.py
# __init__.py - Módulo de scripts enterprise
# Ubicación: C:\TradingBot_v10\scripts\enterprise\__init__.py

"""
Módulo de scripts enterprise para el trading bot.

Este módulo proporciona:
- Configuración de infraestructura
- Gestión de servicios
- Verificación de salud
- Backup y restauración de datos
- Monitoreo y alertas
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Enterprise Team"

# Imports principales
from .setup_infrastructure import InfrastructureSetup
from .start_services import ServiceManager
from .health_check import HealthChecker
from .backup_data import DataBackupManager

# Exports principales
__all__ = [
    "InfrastructureSetup",
    "ServiceManager",
    "HealthChecker",
    "DataBackupManager"
]
