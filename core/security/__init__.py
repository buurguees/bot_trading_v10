# Ruta: core/security/__init__.py
# __init__.py - Módulo de seguridad enterprise
# Ubicación: C:\TradingBot_v10\security\__init__.py

"""
Módulo de seguridad enterprise para el trading bot.

Este módulo proporciona:
- Encriptación de datos sensibles
- Gestión de claves y secrets
- Auditoría de eventos
- Verificación de compliance
- Detección de anomalías
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Enterprise Team"

# Imports principales
from .encryption_manager import EncryptionManager
from .vault_manager import VaultManager
from .audit_logger import AuditLogger
from .compliance_checker import ComplianceChecker

# Exports principales
__all__ = [
    "EncryptionManager",
    "VaultManager", 
    "AuditLogger",
    "ComplianceChecker"
]
