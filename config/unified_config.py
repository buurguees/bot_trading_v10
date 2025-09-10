#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración Unificada del Bot Trading v10 Enterprise
=====================================================
Centraliza toda la configuración del sistema desde archivos YAML
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

class UnifiedConfig:
    """Gestor de configuración unificado"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config_cache = {}
        self._env_loaded = False
        
        # Cargar variables de entorno
        self._load_environment()
        
        # Cargar configuraciones
        self._load_all_configs()
    
    def _load_environment(self):
        """Cargar variables de entorno desde .env"""
        if not self._env_loaded:
            env_file = self.config_dir / ".env"
            if env_file.exists():
                load_dotenv(env_file)
            self._env_loaded = True
    
    def _load_all_configs(self):
        """Cargar todas las configuraciones del sistema"""
        # Configuración principal del usuario
        self.user_settings = self._load_yaml("user_settings.yaml")
        
        # Configuraciones enterprise
        self.enterprise_configs = {}
        enterprise_dir = Path("config/enterprise")
        if enterprise_dir.exists():
            for yaml_file in enterprise_dir.glob("*.yaml"):
                config_name = yaml_file.stem
                self.enterprise_configs[config_name] = self._load_yaml(str(yaml_file))
        
        # Configuración de control
        self.control_config = self._load_yaml("control_config.yaml")
        
        # Configuración de logging
        self.logging_config = self._load_yaml("logging_config.yaml")
        
        # Configuración de agentes
        self.agents_config = self._load_yaml("agents_config.yaml")
        
        # Configuración de logs
        self.logs_config = self._load_yaml("logs_config.yaml")
        
        # Configuración de datos
        self.data_config = self._load_yaml("data_config.yaml")
        
        # Configuración de monitoreo
        self.monitoring_config = self._load_yaml("monitoring_config.yaml")
        
        # Configuración de seguridad
        self.security_config = self._load_yaml("security_config.yaml")
    
    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """Cargar archivo YAML con cache.
        Acepta rutas relativas a config/ o rutas absolutas/ya prefijadas.
        """
        p = Path(file_path)
        # Si ya es absoluta o ya está prefijada con config_dir, usar tal cual
        if p.is_absolute() or str(p).startswith(str(self.config_dir)):
            full_path = p
        else:
            full_path = self.config_dir / p
        
        if str(full_path) in self._config_cache:
            return self._config_cache[str(full_path)]
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                self._config_cache[str(full_path)] = config
                return config
        except FileNotFoundError:
            print(f"⚠️ Archivo de configuración no encontrado: {full_path}")
            return {}
        except Exception as e:
            print(f"❌ Error cargando configuración {full_path}: {e}")
            return {}
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Obtener valor usando notación de puntos (ej: 'trading.symbols')"""
        # Buscar en user_settings primero
        value = self._get_nested_value(self.user_settings, key_path)
        if value is not None:
            return value
        
        # Buscar en configuraciones enterprise
        for config_name, config in self.enterprise_configs.items():
            value = self._get_nested_value(config, key_path)
            if value is not None:
                return value
        
        # Buscar en control config
        value = self._get_nested_value(self.control_config, key_path)
        if value is not None:
            return value
        
        return default
    
    def _get_nested_value(self, config: Dict[str, Any], key_path: str) -> Any:
        """Obtener valor anidado usando notación de puntos"""
        keys = key_path.split('.')
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def get_symbols(self) -> List[str]:
        """Obtener símbolos configurados"""
        # Buscar en múltiples ubicaciones
        symbols = self.get('data_collection.real_time.symbols', [])
        
        if not symbols:
            symbols = self.get('multi_symbol_settings.symbols', {})
            if isinstance(symbols, dict):
                symbols = list(symbols.keys())
        
        if not symbols:
            symbols = self.get('trading_settings.symbols', [])
        
        if not symbols:
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
        
        return symbols
    
    def get_timeframes(self) -> List[str]:
        """Obtener timeframes configurados"""
        timeframes = self.get('data_collection.real_time.timeframes', [])
        
        if not timeframes:
            timeframes = self.get('data_collection.historical.timeframes', [])
        
        if not timeframes:
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        return timeframes
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Obtener configuración de Telegram"""
        return {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'enabled': self.get('monitoring.alerts.telegram.enabled', False),
            'update_interval': self.get('monitoring.alerts.telegram.training_update_interval', 60)
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtener configuración de base de datos"""
        return {
            'url': os.getenv('DATABASE_URL', 'sqlite:///data/trading_bot.db'),
            'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
            'timescaledb_url': os.getenv('TIMESCALEDB_URL'),
            'storage_format': self.get('data_collection.historical.storage_format', 'sqlite'),
            'database_per_symbol': self.get('data_collection.historical.database_per_symbol', True)
        }
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Obtener configuración de trading"""
        return {
            'mode': self.get('trading.mode', 'paper_trading'),
            'symbols': self.get_symbols(),
            'timeframes': self.get_timeframes(),
            'min_confidence': self.get('trading.min_confidence', 0.7),
            'max_risk_per_trade': self.get('risk_management.max_risk_per_trade', 0.01),
            'max_leverage': self.get('risk_management.max_leverage', 20.0),
            'futures_enabled': self.get('trading.futures', True)
        }
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Obtener configuración de ML"""
        return {
            'min_confidence': self.get('ai_model_settings.confidence.min_confidence_to_trade', 75.0),
            'model_type': self.get('trading_enterprise.strategies.ml_strategy.model_type', 'lstm_attention'),
            'retraining_frequency': self.get('ai_model_settings.retraining.frequency', 'adaptive'),
            'feature_importance': self.get('ai_model_settings.feature_importance', {})
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Obtener configuración de monitoreo"""
        return {
            'dashboard_enabled': self.get('monitoring.dashboard.enabled', True),
            'dashboard_port': self.get('monitoring.dashboard.port', 8050),
            'prometheus_enabled': self.get('monitoring_enterprise.prometheus.enabled', True),
            'prometheus_port': self.get('monitoring_enterprise.prometheus.port', 8003),
            'telegram_alerts': self.get_telegram_config()
        }
    
    def reload_config(self):
        """Recargar todas las configuraciones"""
        self._config_cache.clear()
        self._load_all_configs()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obtener toda la configuración como diccionario"""
        return {
            'user_settings': self.user_settings,
            'enterprise_configs': self.enterprise_configs,
            'control_config': self.control_config,
            'logging_config': self.logging_config
        }

# Instancia global
unified_config = UnifiedConfig()

# Funciones de conveniencia
def get_config(key_path: str, default: Any = None) -> Any:
    """Obtener valor de configuración"""
    return unified_config.get(key_path, default)

def get_symbols() -> List[str]:
    """Obtener símbolos configurados"""
    return unified_config.get_symbols()

def get_timeframes() -> List[str]:
    """Obtener timeframes configurados"""
    return unified_config.get_timeframes()

def get_telegram_config() -> Dict[str, Any]:
    """Obtener configuración de Telegram"""
    return unified_config.get_telegram_config()

def get_database_config() -> Dict[str, Any]:
    """Obtener configuración de base de datos"""
    return unified_config.get_database_config()

def get_trading_config() -> Dict[str, Any]:
    """Obtener configuración de trading"""
    return unified_config.get_trading_config()

def get_ml_config() -> Dict[str, Any]:
    """Obtener configuración de ML"""
    return unified_config.get_ml_config()

def get_monitoring_config() -> Dict[str, Any]:
    """Obtener configuración de monitoreo"""
    return unified_config.get_monitoring_config()
