# Ruta: core/deployment/__init__.py
"""
Deployment Module - Bot Trading v10 Enterprise
==============================================

Gestión de despliegues enterprise con soporte para:
- Gestión de fases del sistema
- Monitoreo de salud
- Recuperación automática
- Orquestación de servicios
- Gestión de backups
"""

from .phase_manager import *
from .health_monitor import *
from .recovery_manager import *
