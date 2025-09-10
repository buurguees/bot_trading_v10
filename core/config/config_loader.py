# Ruta: core/config/config_loader.py
# config_loader.py - Cargador de configuraciones enterprise
# Ubicación: core/config/config_loader.py

"""
Cargador de Configuraciones Enterprise
Integra con UnifiedConfigManager para proporcionar acceso fácil a configuraciones

Características principales:
- Acceso simplificado a configuraciones por módulo
- Cache de configuraciones frecuentemente usadas
- Validación automática de configuraciones
- Soporte para configuraciones por entorno
- Integración con sistema de logging
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

from .unified_config import unified_config

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Cargador de configuraciones enterprise"""
    
    def __init__(self):
        self.unified_config = unified_config
        self.cache = {}
        self.cache_ttl = 300  # 5 minutos
        self.last_cache_update = {}
        
        logger.info("ConfigLoader inicializado")
    
    async def initialize(self):
        """Inicializa el cargador de configuraciones"""
        try:
            await self.unified_config.initialize()
            logger.info("ConfigLoader inicializado exitosamente")
        except Exception as e:
            logger.error(f"Error inicializando ConfigLoader: {e}")
            raise
    
    def get_config(self, config_file: str, key_path: str = None, default: Any = None) -> Any:
        """Obtiene una configuración específica"""
        try:
            return self.unified_config.get_config(config_file, key_path, default)
        except Exception as e:
            logger.error(f"Error obteniendo configuración {config_file}.{key_path}: {e}")
            return default
    
    def get_module_config(self, module: str) -> Dict[str, Any]:
        """Obtiene configuraciones para un módulo específico"""
        try:
            # Verificar cache
            cache_key = f"module_{module}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Obtener configuraciones del módulo
            module_configs = self.unified_config.get_module_configs(module)
            
            # Cachear resultado
            self.cache[cache_key] = module_configs
            self.last_cache_update[cache_key] = datetime.now()
            
            return module_configs
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración del módulo {module}: {e}")
            return {}
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Obtiene configuración de trading"""
        return self.get_module_config('trading')
    
    def get_data_collection_config(self) -> Dict[str, Any]:
        """Obtiene configuración de recolección de datos"""
        return self.get_module_config('data_collection')
    
    def get_portfolio_config(self) -> Dict[str, Any]:
        """Obtiene configuración de portafolio"""
        return self.get_module_config('portfolio')
    
    def get_security_config(self) -> Dict[str, Any]:
        """Obtiene configuración de seguridad"""
        return self.get_module_config('security')
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Obtiene configuración de ML"""
        return self.get_module_config('ml')
    
    def get_infrastructure_config(self) -> Dict[str, Any]:
        """Obtiene configuración de infraestructura"""
        return self.get_module_config('infrastructure')
    
    def get_symbols(self) -> List[str]:
        """Obtiene lista de símbolos de trading"""
        try:
            trading_config = self.get_trading_config()
            symbols = trading_config.get('trading.yaml', {}).get('trading', {}).get('symbols', [])
            
            if not symbols:
                # Fallback a data_collection.yaml
                data_config = self.get_data_collection_config()
                symbols = data_config.get('data_collection.yaml', {}).get('data_collection', {}).get('symbols', [])
            
            return symbols if symbols else ['BTCUSDT', 'ETHUSDT']
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos: {e}")
            return ['BTCUSDT', 'ETHUSDT']
    
    def get_timeframes(self) -> List[str]:
        """Obtiene lista de timeframes"""
        try:
            data_config = self.get_data_collection_config()
            timeframes = data_config.get('data_collection.yaml', {}).get('data_collection', {}).get('timeframes', {})
            
            if isinstance(timeframes, dict):
                return list(timeframes.keys())
            elif isinstance(timeframes, list):
                return timeframes
            else:
                return ['1m', '5m', '15m', '1h', '4h', '1d']
                
        except Exception as e:
            logger.error(f"Error obteniendo timeframes: {e}")
            return ['1m', '5m', '15m', '1h', '4h', '1d']
    
    def get_trading_mode(self) -> str:
        """Obtiene modo de trading actual"""
        try:
            trading_config = self.get_trading_config()
            mode = trading_config.get('trading.yaml', {}).get('trading', {}).get('mode', 'paper_trading')
            return mode
        except Exception as e:
            logger.error(f"Error obteniendo modo de trading: {e}")
            return 'paper_trading'
    
    def get_exchange_config(self, exchange: str = 'bitget') -> Dict[str, Any]:
        """Obtiene configuración de exchange específico"""
        try:
            futures_config = self.get_config('futures_config.yaml')
            return futures_config.get('exchanges', {}).get(exchange, {})
        except Exception as e:
            logger.error(f"Error obteniendo configuración de exchange {exchange}: {e}")
            return {}
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Obtiene límites de riesgo"""
        try:
            risk_config = self.get_config('risk_management.yaml')
            return risk_config.get('risk_management', {}).get('exposure_limits', {})
        except Exception as e:
            logger.error(f"Error obteniendo límites de riesgo: {e}")
            return {}
    
    def get_portfolio_settings(self) -> Dict[str, Any]:
        """Obtiene configuración de portafolio"""
        try:
            portfolio_config = self.get_config('portfolio_management.yaml')
            return portfolio_config.get('portfolio_management', {})
        except Exception as e:
            logger.error(f"Error obteniendo configuración de portafolio: {e}")
            return {}
    
    def get_ml_settings(self) -> Dict[str, Any]:
        """Obtiene configuración de ML"""
        try:
            ml_config = self.get_ml_config()
            return {
                'hyperparameters': ml_config.get('hyperparameters.yaml', {}),
                'model_architectures': ml_config.get('model_architectures.yaml', {})
            }
        except Exception as e:
            logger.error(f"Error obteniendo configuración de ML: {e}")
            return {}
    
    def get_infrastructure_settings(self) -> Dict[str, Any]:
        """Obtiene configuración de infraestructura"""
        try:
            infra_config = self.get_infrastructure_config()
            return infra_config.get('infrastructure.yaml', {})
        except Exception as e:
            logger.error(f"Error obteniendo configuración de infraestructura: {e}")
            return {}
    
    def get_logs_config(self) -> Dict[str, Any]:
        """Obtiene configuración de logs"""
        return self.get_config('logs_config.yaml', 'logging', {})
    
    def get_main_config(self) -> Dict[str, Any]:
        """Obtiene configuración principal"""
        return self.get_config('main_config.yaml')
    
    def get_control_config(self) -> Dict[str, Any]:
        """Obtiene configuración de control"""
        return self.get_config('control_config.yaml')
    
    def get_data_config(self) -> Dict[str, Any]:
        """Obtiene configuración de datos"""
        return self.get_config('data_config.yaml')
    
    def get_agents_config(self) -> Dict[str, Any]:
        """Obtiene configuración de agentes"""
        return self.get_config('agents_config.yaml')
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Obtiene configuración de logging detallada"""
        return self.get_config('logging_config.yaml')
    
    def get_security_config(self) -> Dict[str, Any]:
        """Obtiene configuración de seguridad"""
        return self.get_config('security_config.yaml')
    
    def get_security_settings(self) -> Dict[str, Any]:
        """Obtiene configuración de seguridad"""
        try:
            security_config = self.get_security_config()
            return security_config.get('security.yaml', {})
        except Exception as e:
            logger.error(f"Error obteniendo configuración de seguridad: {e}")
            return {}
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Obtiene configuración de estrategia específica"""
        try:
            strategies_config = self.get_config('strategies.yaml')
            strategies = strategies_config.get('strategies', {})
            return strategies.get(strategy_name, {})
        except Exception as e:
            logger.error(f"Error obteniendo configuración de estrategia {strategy_name}: {e}")
            return {}
    
    def get_validation_status(self) -> Dict[str, Any]:
        """Obtiene estado de validación de configuraciones"""
        try:
            return self.unified_config.get_validation_status()
        except Exception as e:
            logger.error(f"Error obteniendo estado de validación: {e}")
            return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el cache es válido"""
        try:
            if cache_key not in self.cache or cache_key not in self.last_cache_update:
                return False
            
            time_diff = datetime.now() - self.last_cache_update[cache_key]
            return time_diff.total_seconds() < self.cache_ttl
            
        except Exception:
            return False
    
    def clear_cache(self):
        """Limpia el cache de configuraciones"""
        try:
            self.cache.clear()
            self.last_cache_update.clear()
            logger.info("Cache de configuraciones limpiado")
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
    
    async def reload_configs(self):
        """Recarga todas las configuraciones"""
        try:
            await self.unified_config.load_all_configs()
            await self.unified_config.validate_all_configs()
            self.clear_cache()
            logger.info("Configuraciones recargadas exitosamente")
        except Exception as e:
            logger.error(f"Error recargando configuraciones: {e}")
    
    def export_configs(self, output_dir: str = "config/exported") -> str:
        """Exporta todas las configuraciones"""
        try:
            return asyncio.run(self.unified_config.export_configs(output_dir))
        except Exception as e:
            logger.error(f"Error exportando configuraciones: {e}")
            return None

# Instancia global
config_loader = ConfigLoader()

# Función de conveniencia para compatibilidad
def get_config(config_file: str, key_path: str = None, default: Any = None) -> Any:
    """Función de conveniencia para obtener configuraciones"""
    return config_loader.get_config(config_file, key_path, default)

def get_symbols() -> List[str]:
    """Función de conveniencia para obtener símbolos"""
    return config_loader.get_symbols()

def get_timeframes() -> List[str]:
    """Función de conveniencia para obtener timeframes"""
    return config_loader.get_timeframes()

def get_trading_mode() -> str:
    """Función de conveniencia para obtener modo de trading"""
    return config_loader.get_trading_mode()
