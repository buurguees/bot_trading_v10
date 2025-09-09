# Ruta: core/data/__init__.py
"""
Data Module - Bot Trading v10 Enterprise
========================================

Gestión de datos enterprise con soporte para:
- Recolección de datos en tiempo real
- Preprocesamiento y validación
- Almacenamiento en TimescaleDB
- Cache inteligente con Redis
- Agregación de timeframes
"""

from .enterprise import *
from .database import *
from .preprocessor import *
