"""
Core Module - Bot Trading v10 Enterprise
=======================================

Módulo principal de infraestructura del bot de trading.
Contiene todos los motores y sistemas de trabajo.

Submódulos:
- config: Gestión de configuración
- trading: Motores de trading
- ml: Sistemas de machine learning
- data: Gestión de datos
- monitoring: Sistemas de monitoreo
- security: Seguridad y auditoría
- compliance: Cumplimiento normativo
- deployment: Despliegue y recuperación
- integration: Utilidades del sistema
"""

from .config import *
from .trading import *
from .ml import *
from .data import *
from .monitoring import *
from .security import *
from .compliance import *
from .deployment import *
from .integration import *

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
