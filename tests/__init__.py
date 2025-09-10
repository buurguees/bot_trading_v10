# -*- coding: utf-8 -*-
"""
Tests para Bot Trading v10 Enterprise
====================================
Estructura organizada de pruebas unitarias, de integración y end-to-end
"""

__version__ = "1.0.0"
__author__ = "Bot Trading v10 Enterprise"

# Configuración de testing
import sys
import os
from pathlib import Path

# Agregar directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuración de logging para tests
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def setup_test_environment():
    """Configurar entorno de pruebas"""
    logger.info("🧪 Configurando entorno de pruebas...")
    
    # Configurar variables de entorno para testing
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'INFO'
    
    logger.info("✅ Entorno de pruebas configurado")

def cleanup_test_environment():
    """Limpiar entorno de pruebas"""
    logger.info("🧹 Limpiando entorno de pruebas...")
    
    # Limpiar variables de entorno de testing
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
    
    logger.info("✅ Entorno de pruebas limpiado")

if __name__ == "__main__":
    setup_test_environment()
