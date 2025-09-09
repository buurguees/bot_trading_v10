# Ruta: core/config/enterprise_config.py
#!/usr/bin/env python3
"""
Gestor de Configuración Enterprise
"""

import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EnterpriseConfigManager:
    """Gestor de configuración enterprise"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or 'config/user_settings.yaml'
        self.config_cache = {}
        
        # Configurar logging
        self.setup_logging()
        
        logger.info("⚙️ EnterpriseConfigManager inicializado")
    
    def setup_logging(self):
        """Configura el logging"""
        log_dir = Path("logs/enterprise/config")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        config_logger = logging.getLogger('config_manager')
        config_logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(log_dir / 'config_manager.log')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        config_logger.addHandler(file_handler)
    
    def load_config(self) -> Dict[str, Any]:
        """Carga la configuración"""
        try:
            if 'main' in self.config_cache:
                return self.config_cache['main']
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Archivo de configuración vacío")
            
            self.config_cache['main'] = config
            logger.info("✅ Configuración cargada exitosamente")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            raise
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """Obtiene un valor específico de la configuración"""
        try:
            config = self.load_config()
            keys = key_path.split('.')
            
            value = config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo valor de configuración {key_path}: {e}")
            return default
    
    def set_config_value(self, key_path: str, value: Any) -> bool:
        """Establece un valor específico en la configuración"""
        try:
            config = self.load_config()
            keys = key_path.split('.')
            
            current = config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.config_cache.clear()
            logger.info(f"✅ Valor de configuración {key_path} actualizado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error estableciendo valor de configuración {key_path}: {e}")
            return False
    
    def reload_config(self) -> Dict[str, Any]:
        """Recarga la configuración"""
        try:
            self.config_cache.clear()
            config = self.load_config()
            logger.info("🔄 Configuración recargada exitosamente")
            return config
            
        except Exception as e:
            logger.error(f"❌ Error recargando configuración: {e}")
            raise

# Instancia global
config_manager = EnterpriseConfigManager()