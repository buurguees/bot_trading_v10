"""
core/config_manager.py - Gestor de Configuración Centralizada
Sistema robusto de configuración para el trading bot
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CoreConfig:
    """Configuración central del sistema"""
    
    # Entorno
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Base de datos
    database_path: str = "data/trading_bot.db"
    database_backup_path: str = "data/backups"
    max_connections: int = 10
    
    # Modelos
    model_path: str = "models/saved_models"
    model_backup_path: str = "models/backups"
    default_model: str = "best_lstm_attention"
    
    # Trading
    symbols: List[str] = field(default_factory=lambda: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
    timeframes: List[str] = field(default_factory=lambda: ['1h', '4h', '1d'])
    paper_trading: bool = True
    
    # Dashboard
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8050
    dashboard_debug: bool = False
    
    # Entrenamiento
    training_epochs: int = 50
    training_batch_size: int = 32
    training_validation_split: float = 0.2
    training_patience: int = 10
    training_min_delta: float = 0.001
    
    # Recursos
    max_memory_gb: float = 8.0
    max_cpu_percent: float = 80.0
    max_disk_gb: float = 10.0
    
    # APIs
    bitget_api_key: Optional[str] = None
    bitget_secret_key: Optional[str] = None
    bitget_passphrase: Optional[str] = None
    bitget_sandbox: bool = True
    
    # Logging
    log_file: str = "logs/trading_bot.log"
    log_max_size_mb: int = 100
    log_backup_count: int = 5
    
    # Health Checks
    health_check_interval: int = 300  # segundos
    health_check_timeout: int = 30
    
    # Alineación de datos
    alignment_enabled: bool = True
    alignment_symbols: List[str] = field(default_factory=lambda: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
    alignment_timeframes: List[str] = field(default_factory=lambda: ['1h', '4h', '1d'])
    
    @classmethod
    def from_env(cls) -> 'CoreConfig':
        """Crea configuración desde variables de entorno"""
        return cls(
            environment=os.getenv('ENVIRONMENT', 'development'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            database_path=os.getenv('DATABASE_PATH', 'data/trading_bot.db'),
            dashboard_host=os.getenv('DASHBOARD_HOST', '127.0.0.1'),
            dashboard_port=int(os.getenv('DASHBOARD_PORT', '8050')),
            paper_trading=os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            bitget_api_key=os.getenv('BITGET_API_KEY'),
            bitget_secret_key=os.getenv('BITGET_SECRET_KEY'),
            bitget_passphrase=os.getenv('BITGET_PASSPHRASE'),
            bitget_sandbox=os.getenv('BITGET_SANDBOX', 'true').lower() == 'true',
            training_epochs=int(os.getenv('TRAINING_EPOCHS', '50')),
            training_batch_size=int(os.getenv('TRAINING_BATCH_SIZE', '32'))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario"""
        return {
            field.name: getattr(self, field.name) 
            for field in self.__dataclass_fields__.values()
        }
    
    def validate(self) -> List[str]:
        """Valida la configuración y devuelve errores"""
        errors = []
        
        # Validar entornos
        if self.environment not in ['development', 'testing', 'production']:
            errors.append(f"Invalid environment: {self.environment}")
        
        # Validar puerto del dashboard
        if not (1024 <= self.dashboard_port <= 65535):
            errors.append(f"Invalid dashboard port: {self.dashboard_port}")
        
        # Validar símbolos
        if not self.symbols or len(self.symbols) == 0:
            errors.append("No trading symbols configured")
        
        # Validar timeframes
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        for tf in self.timeframes:
            if tf not in valid_timeframes:
                errors.append(f"Invalid timeframe: {tf}")
        
        # Validar recursos
        if self.max_memory_gb < 1:
            errors.append(f"Insufficient max memory: {self.max_memory_gb}GB")
        
        if self.max_disk_gb < 1:
            errors.append(f"Insufficient max disk space: {self.max_disk_gb}GB")
        
        # Validar configuración de trading
        if not self.paper_trading and not all([
            self.bitget_api_key,
            self.bitget_secret_key,
            self.bitget_passphrase
        ]):
            errors.append("Live trading requires API credentials")
        
        return errors

class ConfigManager:
    """Gestor principal de configuración"""
    
    def __init__(self, config_file: str = "config/core_config.yaml"):
        self.config_file = Path(config_file)
        self.config: Optional[CoreConfig] = None
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> CoreConfig:
        """Carga la configuración desde archivo o crea una nueva"""
        try:
            if self.config_file.exists():
                self.logger.info(f"Loading configuration from {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix == '.yaml' or self.config_file.suffix == '.yml':
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                # Crear configuración desde datos cargados
                self.config = CoreConfig(**config_data)
            else:
                self.logger.info("Configuration file not found, creating default configuration")
                self.config = CoreConfig.from_env()
                self.save_config()
            
            # Validar configuración
            errors = self.config.validate()
            if errors:
                self.logger.error(f"Configuration validation errors: {errors}")
                raise ValueError(f"Invalid configuration: {', '.join(errors)}")
            
            self.logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            # Fallback a configuración por defecto
            self.config = CoreConfig.from_env()
            return self.config
    
    def save_config(self) -> bool:
        """Guarda la configuración actual"""
        try:
            if not self.config:
                self.logger.error("No configuration to save")
                return False
            
            # Crear directorio si no existe
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar en formato YAML
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config.to_dict(), f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_config(self) -> CoreConfig:
        """Obtiene la configuración actual"""
        if not self.config:
            self.config = self.load_config()
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Actualiza la configuración con nuevos valores"""
        try:
            if not self.config:
                self.config = self.load_config()
            
            # Aplicar actualizaciones
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.logger.warning(f"Unknown configuration key: {key}")
            
            # Validar configuración actualizada
            errors = self.config.validate()
            if errors:
                self.logger.error(f"Configuration validation errors after update: {errors}")
                return False
            
            # Guardar configuración actualizada
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de trading"""
        config = self.get_config()
        return {
            'symbols': config.symbols,
            'timeframes': config.timeframes,
            'paper_trading': config.paper_trading,
            'api_credentials': {
                'api_key': config.bitget_api_key,
                'secret_key': config.bitget_secret_key,
                'passphrase': config.bitget_passphrase,
                'sandbox': config.bitget_sandbox
            }
        }
    
    def get_training_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de entrenamiento"""
        config = self.get_config()
        return {
            'epochs': config.training_epochs,
            'batch_size': config.training_batch_size,
            'validation_split': config.training_validation_split,
            'patience': config.training_patience,
            'min_delta': config.training_min_delta,
            'symbols': config.symbols
        }
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica del dashboard"""
        config = self.get_config()
        return {
            'host': config.dashboard_host,
            'port': config.dashboard_port,
            'debug': config.dashboard_debug
        }
    
    def get_resource_limits(self) -> Dict[str, float]:
        """Obtiene límites de recursos"""
        config = self.get_config()
        return {
            'max_memory_gb': config.max_memory_gb,
            'max_cpu_percent': config.max_cpu_percent,
            'max_disk_gb': config.max_disk_gb
        }
    
    def is_production(self) -> bool:
        """Verifica si está en modo producción"""
        return self.get_config().environment == 'production'
    
    def is_development(self) -> bool:
        """Verifica si está en modo desarrollo"""
        return self.get_config().environment == 'development'
    
    def is_testing(self) -> bool:
        """Verifica si está en modo testing"""
        return self.get_config().environment == 'testing'

# Instancia global
config_manager = ConfigManager()

# Funciones de conveniencia
def get_config() -> CoreConfig:
    """Obtiene la configuración actual"""
    return config_manager.get_config()

def get_trading_config() -> Dict[str, Any]:
    """Obtiene configuración de trading"""
    return config_manager.get_trading_config()

def get_training_config() -> Dict[str, Any]:
    """Obtiene configuración de entrenamiento"""
    return config_manager.get_training_config()

def get_dashboard_config() -> Dict[str, Any]:
    """Obtiene configuración del dashboard"""
    return config_manager.get_dashboard_config()

def is_production() -> bool:
    """Verifica si está en modo producción"""
    return config_manager.is_production()

def is_development() -> bool:
    """Verifica si está en modo desarrollo"""
    return config_manager.is_development()
