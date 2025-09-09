# Ruta: core/data/enterprise/__init__.py
# __init__.py - Módulo de recopilación de datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\__init__.py

"""
Módulo de recopilación de datos enterprise para el sistema de trading.

Componentes principales:
- EnterpriseDataCollector: Recopilación de datos en tiempo real
- DataPreprocessor: Preprocesamiento de datos en streaming
- TimescaleDB integration: Almacenamiento histórico
- Kafka streaming: Procesamiento distribuido
"""

from .stream_collector import EnterpriseDataCollector
from .preprocessor import DataPreprocessor
from .database import TimescaleDBManager

__all__ = [
    'EnterpriseDataCollector',
    'DataPreprocessor', 
    'TimescaleDBManager'
]

# Versión del módulo
__version__ = "1.0.0"

# Información del módulo
__author__ = "Trading Bot Enterprise Team"
__description__ = "Sistema de recopilación de datos enterprise en tiempo real"