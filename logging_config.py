#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración de logging para Bot Trading v10 Enterprise
Maneja correctamente la codificación UTF-8 en Windows
"""

import logging
import sys
import yaml
from pathlib import Path
from config.unified_config import unified_config

def setup_logging():
    """Configura el sistema de logging con codificación UTF-8"""
    
    # Crear directorio de logs si no existe
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configurar formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para archivo (UTF-8)
    file_handler = logging.FileHandler(
        'logs/bot.log', 
        encoding='utf-8',
        mode='a'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Handler para consola (sin emojis para evitar errores de codificación)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configurar logging raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre especificado"""
    return logging.getLogger(name)
