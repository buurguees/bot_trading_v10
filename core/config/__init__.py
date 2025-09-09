# Ruta: core/config/__init__.py
"""
Config Module - Bot Trading v10 Enterprise
==========================================

Gestión de configuración enterprise con soporte para:
- Carga y validación de configuraciones YAML
- Gestión de secretos con AWS Secrets Manager
- Configuración por entornos
- Hot-reload de configuraciones
- Validación de esquemas
"""

from .enterprise_config import *
