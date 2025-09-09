#!/usr/bin/env python3
"""
Config Loader - Cargador de configuración simple
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List

class ConfigLoader:
    """Cargador de configuración simple"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        self.config_path = config_path
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde YAML"""
        if self._config is None:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
            except Exception as e:
                print(f"Error cargando configuración: {e}")
                self._config = {}
        return self._config
    
    def get_value(self, keys: List[str], default: Any = None) -> Any:
        """Obtiene un valor de la configuración usando claves anidadas"""
        config = self.load_config()
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_symbols(self) -> List[str]:
        """Obtiene la lista de símbolos configurados"""
        # Primero intentar desde data_collection.real_time.symbols
        symbols = self.get_value(['data_collection', 'real_time', 'symbols'], [])
        
        if not symbols:
            # Fallback: extraer de multi_symbol_settings.symbols
            multi_symbols = self.get_value(['multi_symbol_settings', 'symbols'], {})
            symbols = list(multi_symbols.keys())
        
        if not symbols:
            # Fallback final: símbolos por defecto
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
        
        return symbols
    
    def get_main_symbols(self) -> List[str]:
        """Obtiene los símbolos principales para trading"""
        return self.get_symbols()

# Instancia global para compatibilidad
user_config = ConfigLoader()
