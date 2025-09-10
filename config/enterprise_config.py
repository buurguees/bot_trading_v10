#!/usr/bin/env python3
"""
Enterprise Configuration Manager
Maneja configuraciones enterprise que no están en user_settings.yaml
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EnterpriseConfigManager:
    """Gestor de configuración enterprise"""
    
    def __init__(self, config_dir: str = "config/enterprise"):
        self.config_dir = Path(config_dir)
        self._configs = {}
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Carga una configuración enterprise específica"""
        if config_name not in self._configs:
            config_path = self.config_dir / f"{config_name}.yaml"
            try:
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self._configs[config_name] = yaml.safe_load(f) or {}
                else:
                    logger.warning(f"Archivo de configuración no encontrado: {config_path}")
                    self._configs[config_name] = {}
            except Exception as e:
                logger.error(f"Error cargando configuración {config_name}: {e}")
                self._configs[config_name] = {}
        
        return self._configs[config_name]
    
    def get_value(self, config_name: str, keys: list, default: Any = None) -> Any:
        """Obtiene un valor de configuración enterprise"""
        config = self.load_config(config_name)
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current

# Instancia global
enterprise_config = EnterpriseConfigManager()

def get_enterprise_config(config_name: str = "trading") -> Dict[str, Any]:
    """Función de conveniencia para obtener configuración enterprise"""
    return enterprise_config.load_config(config_name)
