#!/usr/bin/env python3
"""
Configuración de Logging para Trading Bot v10
============================================

Configuración de logging que maneja correctamente los emojis y caracteres Unicode
en Windows.

Uso:
    from logging_config import setup_logging
    setup_logging()

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import logging
import sys
from pathlib import Path

def setup_logging(level=logging.INFO, log_file='logs/bot.log'):
    """
    Configura el sistema de logging para manejar emojis correctamente
    
    Args:
        level: Nivel de logging (default: INFO)
        log_file: Archivo de log (default: logs/bot.log)
    """
    try:
        # Crear directorio de logs
        Path('logs').mkdir(exist_ok=True)
        
        # Configurar el handler para consola con encoding UTF-8
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Configurar el handler para archivo con encoding UTF-8
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        
        # Formato de logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Configurar el logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Limpiar handlers existentes
        root_logger.handlers.clear()
        
        # Agregar handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # Configurar logging para librerías específicas
        logging.getLogger('telegram').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        
        return root_logger
        
    except Exception as e:
        print(f"Error configurando logging: {e}")
        return None

def get_logger(name):
    """
    Obtiene un logger configurado
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)

# Configuración por defecto
if __name__ == "__main__":
    setup_logging()
    logger = get_logger(__name__)
    logger.info("✅ Sistema de logging configurado correctamente")
    logger.info("🤖 Bot de Trading v10 - Logging Enterprise")
    logger.warning("⚠️ Este es un mensaje de prueba")
    logger.error("❌ Este es un mensaje de error de prueba")
