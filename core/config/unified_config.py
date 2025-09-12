# Ruta: core/config/unified_config.py
# unified_config.py - Gestión centralizada de configuraciones enterprise
# Ubicación: core/config/unified_config.py

"""
Sistema de Configuración Unificado Enterprise
Gestiona todas las configuraciones .yaml del proyecto de forma centralizada

Características principales:
- Carga centralizada de todos los .yaml
- Validación de configuraciones
- Cache de configuraciones
- Hot-reload de configuraciones
- Validación de dependencias entre configuraciones
- Logging de cambios de configuración
"""

import os
import yaml
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
from dataclasses import dataclass, asdict
import redis
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@dataclass
class ConfigValidationResult:
    """Resultado de validación de configuración"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    config_hash: str
    last_modified: datetime

@dataclass
class ConfigDependency:
    """Dependencia entre configuraciones"""
    source_config: str
    target_config: str
    required_keys: List[str]
    validation_rule: str

class ConfigFileHandler(FileSystemEventHandler):
    """Manejador de cambios en archivos de configuración"""
    
    def __init__(self, unified_config):
        self.unified_config = unified_config
        self.last_modified = {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            # Verificar si realmente cambió el archivo
            current_time = datetime.now()
            if file_path in self.last_modified:
                time_diff = current_time - self.last_modified[file_path]
                if time_diff.total_seconds() < 1:  # Evitar múltiples eventos
                    return
            
            self.last_modified[file_path] = current_time
            logger.info(f"Archivo de configuración modificado: {file_path}")
            
            # Recargar configuración en background
            asyncio.create_task(self.unified_config.reload_config(file_path))

class UnifiedConfigManager:
    """Gestor centralizado de configuraciones enterprise"""
    
    def __init__(self, config_dir: str = "config/enterprise"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.config_hashes = {}
        self.validation_results = {}
        self.dependencies = []
        self.redis_client = None
        self.observer = None
        self.file_handler = None
        self.hot_reload_enabled = True
        
        # Configuraciones por módulo
        self.module_configs = {
            'data_collection': ['data_collection.yaml', 'infrastructure.yaml'],
            'trading': ['trading.yaml', 'futures_config.yaml', 'strategies.yaml'],
            'portfolio': ['portfolio_management.yaml', 'risk_management.yaml'],
            'security': ['security.yaml'],
            'ml': ['hyperparameters.yaml', 'model_architectures.yaml'],
            'infrastructure': ['infrastructure.yaml']
        }
        
        # Dependencias entre configuraciones
        self._setup_dependencies()
        
        logger.info("UnifiedConfigManager inicializado")
    
    def _setup_dependencies(self):
        """Configura dependencias entre archivos de configuración"""
        self.dependencies = [
            ConfigDependency(
                source_config="trading.yaml",
                target_config="futures_config.yaml",
                required_keys=["exchanges.bitget"],
                validation_rule="exchange_config_validation"
            ),
            ConfigDependency(
                source_config="data_collection.yaml",
                target_config="infrastructure.yaml",
                required_keys=["kafka", "redis"],
                validation_rule="infrastructure_validation"
            ),
            ConfigDependency(
                source_config="portfolio_management.yaml",
                target_config="risk_management.yaml",
                required_keys=["max_concentration_per_asset"],
                validation_rule="risk_portfolio_validation"
            ),
            ConfigDependency(
                source_config="strategies.yaml",
                target_config="hyperparameters.yaml",
                required_keys=["ml_strategy"],
                validation_rule="strategy_ml_validation"
            )
        ]
    
    async def initialize(self):
        """Inicializa el gestor de configuraciones"""
        try:
            # Configurar Redis para cache
            await self._setup_redis()
            
            # Cargar todas las configuraciones
            await self.load_all_configs()
            
            # Validar configuraciones
            await self.validate_all_configs()
            
            # Configurar hot-reload si está habilitado
            if self.hot_reload_enabled:
                await self._setup_hot_reload()
            
            logger.info("UnifiedConfigManager inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando UnifiedConfigManager: {e}")
            raise
    
    async def _setup_redis(self):
        """Configura Redis para cache de configuraciones"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Conexión a Redis establecida para configuraciones")
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}")
            self.redis_client = None
    
    async def load_all_configs(self):
        """Carga todas las configuraciones .yaml"""
        try:
            # Configuraciones enterprise
            enterprise_config_files = [
                'data_collection.yaml',
                'trading.yaml',
                'portfolio_management.yaml',
                'futures_config.yaml',
                'security.yaml',
                'hyperparameters.yaml',
                'strategies.yaml',
                'infrastructure.yaml',
                'model_architectures.yaml',
                'risk_management.yaml'
            ]
            
            # Configuraciones principales
            main_config_files = [
                'logs_config.yaml',
                'main_config.yaml',
                'control_config.yaml',
                'data_config.yaml',
                'agents_config.yaml',
                'logging_config.yaml',
                'security_config.yaml'
            ]
            
            config_files = enterprise_config_files + main_config_files
            
            for config_file in config_files:
                await self.load_config(config_file)

            # Cargar nuevas rutas unificadas
            self._load_directory_configs(Path("config/core"), prefix="core/")
            self._load_directory_configs(Path("config/environments"), prefix="environments/")
            self._load_directory_configs(Path("config/features"), prefix="features/")
            
            logger.info(f"Cargadas {len(self.configs)} configuraciones")
            
        except Exception as e:
            logger.error(f"Error cargando configuraciones: {e}")
            raise

    def _load_directory_configs(self, directory: Path, prefix: str = "") -> None:
        """Carga todos los YAML de un directorio y los registra con un alias prefijado"""
        try:
            if not directory.exists():
                return
            for file in directory.glob("*.yml"):
                with open(file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                self.configs[f"{prefix}{file.name}"] = data
            for file in directory.glob("*.yaml"):
                with open(file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                self.configs[f"{prefix}{file.name}"] = data
        except Exception as e:
            logger.warning(f"No se pudieron cargar configuraciones desde {directory}: {e}")

    def ensure_loaded(self) -> None:
        """Carga sincrónicamente configuraciones básicas si aún no han sido cargadas.
        Útil como fallback cuando no se ha inicializado el gestor de forma asíncrona.
        """
        try:
            if self.configs:
                return
            # Cargar las mismas listas que en load_all_configs(), de forma síncrona
            enterprise_config_files = [
                'data_collection.yaml',
                'trading.yaml',
                'portfolio_management.yaml',
                'futures_config.yaml',
                'security.yaml',
                'hyperparameters.yaml',
                'strategies.yaml',
                'infrastructure.yaml',
                'model_architectures.yaml',
                'risk_management.yaml'
            ]
            main_config_files = [
                'logs_config.yaml',
                'main_config.yaml',
                'control_config.yaml',
                'data_config.yaml',
                'agents_config.yaml',
                'logging_config.yaml',
                'security_config.yaml'
            ]
            for config_file in enterprise_config_files + main_config_files:
                # Resolver ruta
                if config_file in ['logs_config.yaml', 'main_config.yaml', 'control_config.yaml',
                                   'data_config.yaml', 'agents_config.yaml', 'logging_config.yaml',
                                   'security_config.yaml']:
                    config_path = Path("config") / config_file
                else:
                    config_path = self.config_dir / config_file
                if not config_path.exists():
                    continue
                with open(config_path, 'r', encoding='utf-8') as f:
                    try:
                        config_data = yaml.safe_load(f)
                    except Exception:
                        config_data = {}
                self.configs[config_file] = config_data or {}

            # Cargar nuevas rutas unificadas
            self._load_directory_configs(Path("config/core"), prefix="core/")
            self._load_directory_configs(Path("config/environments"), prefix="environments/")
            self._load_directory_configs(Path("config/features"), prefix="features/")
        except Exception as e:
            logger.warning(f"ensure_loaded() falló: {e}")
    
    async def load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga una configuración específica"""
        try:
            # Determinar directorio según el tipo de configuración
            if config_file in ['logs_config.yaml', 'main_config.yaml', 'control_config.yaml', 
                             'data_config.yaml', 'agents_config.yaml', 'logging_config.yaml', 
                             'security_config.yaml']:
                config_path = Path("config") / config_file
            else:
                config_path = self.config_dir / config_file
            
            if not config_path.exists():
                logger.warning(f"Archivo de configuración no encontrado: {config_path}")
                return {}
            
            # Verificar cache de Redis
            cache_key = f"config:{config_file}"
            if self.redis_client:
                try:
                    cached_config = self.redis_client.get(cache_key)
                    if cached_config:
                        config_data = json.loads(cached_config)
                        logger.info(f"Configuración {config_file} cargada desde cache")
                        self.configs[config_file] = config_data
                        return config_data
                except Exception as e:
                    logger.warning(f"Error leyendo cache para {config_file}: {e}")
            
            # Cargar desde archivo
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Calcular hash para validación
            config_str = json.dumps(config_data, sort_keys=True)
            config_hash = hashlib.md5(config_str.encode()).hexdigest()
            self.config_hashes[config_file] = config_hash
            
            # Guardar en cache
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, 3600, json.dumps(config_data))
                except Exception as e:
                    logger.warning(f"Error guardando en cache {config_file}: {e}")
            
            self.configs[config_file] = config_data
            logger.info(f"Configuración {config_file} cargada exitosamente")
            
            return config_data
            
        except Exception as e:
            logger.error(f"Error cargando configuración {config_file}: {e}")
            return {}
    
    async def reload_config(self, file_path: str):
        """Recarga una configuración específica"""
        try:
            config_file = os.path.basename(file_path)
            if config_file in self.configs:
                logger.info(f"Recargando configuración: {config_file}")
                await self.load_config(config_file)
                await self.validate_config(config_file)
                
                # Notificar a módulos que usan esta configuración
                await self._notify_config_change(config_file)
                
        except Exception as e:
            logger.error(f"Error recargando configuración {file_path}: {e}")
    
    async def validate_all_configs(self):
        """Valida todas las configuraciones"""
        try:
            for config_file in self.configs.keys():
                await self.validate_config(config_file)
            
            # Validar dependencias
            await self._validate_dependencies()
            
            logger.info("Validación de configuraciones completada")
            
        except Exception as e:
            logger.error(f"Error validando configuraciones: {e}")
            raise
    
    async def validate_config(self, config_file: str) -> ConfigValidationResult:
        """Valida una configuración específica"""
        try:
            config_data = self.configs.get(config_file, {})
            errors = []
            warnings = []
            
            # Validaciones específicas por archivo
            if config_file == 'trading.yaml':
                errors.extend(self._validate_trading_config(config_data))
            elif config_file == 'futures_config.yaml':
                errors.extend(self._validate_futures_config(config_data))
            elif config_file == 'data_collection.yaml':
                errors.extend(self._validate_data_collection_config(config_data))
            elif config_file == 'portfolio_management.yaml':
                errors.extend(self._validate_portfolio_config(config_data))
            elif config_file == 'risk_management.yaml':
                errors.extend(self._validate_risk_config(config_data))
            elif config_file == 'security.yaml':
                errors.extend(self._validate_security_config(config_data))
            elif config_file == 'infrastructure.yaml':
                errors.extend(self._validate_infrastructure_config(config_data))
            
            # Validación general
            errors.extend(self._validate_general_config(config_data))
            
            result = ConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                config_hash=self.config_hashes.get(config_file, ''),
                last_modified=datetime.now()
            )
            
            self.validation_results[config_file] = result
            
            if errors:
                logger.error(f"Errores en {config_file}: {errors}")
            if warnings:
                logger.warning(f"Advertencias en {config_file}: {warnings}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validando configuración {config_file}: {e}")
            return ConfigValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                config_hash='',
                last_modified=datetime.now()
            )
    
    def _validate_trading_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de trading"""
        errors = []
        
        if 'trading' not in config:
            errors.append("Sección 'trading' no encontrada")
            return errors
        
        trading = config['trading']
        
        # Validar modo de trading
        if 'mode' not in trading:
            errors.append("'trading.mode' es requerido")
        elif trading['mode'] not in ['paper_trading', 'live_trading']:
            errors.append("'trading.mode' debe ser 'paper_trading' o 'live_trading'")
        
        # Validar símbolos
        if 'symbols' not in trading:
            errors.append("'trading.symbols' es requerido")
        elif not isinstance(trading['symbols'], list) or len(trading['symbols']) == 0:
            errors.append("'trading.symbols' debe ser una lista no vacía")
        
        # Validar configuraciones de entorno
        if 'environment_configs' not in trading:
            errors.append("'trading.environment_configs' es requerido")
        
        return errors
    
    def _validate_futures_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de futuros"""
        errors = []
        
        if 'exchanges' not in config:
            errors.append("Sección 'exchanges' no encontrada")
            return errors
        
        if 'bitget' not in config['exchanges']:
            errors.append("Configuración de Bitget no encontrada")
            return errors
        
        bitget = config['exchanges']['bitget']
        
        # Validar endpoints
        if 'endpoints' not in bitget:
            errors.append("'exchanges.bitget.endpoints' es requerido")
        else:
            endpoints = bitget['endpoints']
            required_endpoints = ['rest_base', 'websocket_base', 'futures_path']
            for endpoint in required_endpoints:
                if endpoint not in endpoints:
                    errors.append(f"'{endpoint}' es requerido en endpoints")
        
        # Validar límites
        if 'limits' not in bitget:
            errors.append("'exchanges.bitget.limits' es requerido")
        
        return errors
    
    def _validate_data_collection_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de recolección de datos"""
        errors = []
        
        if 'data_collection' not in config:
            errors.append("Sección 'data_collection' no encontrada")
            return errors
        
        data_collection = config['data_collection']
        
        # Validar símbolos
        if 'symbols' not in data_collection:
            errors.append("'data_collection.symbols' es requerido")
        elif not isinstance(data_collection['symbols'], list):
            errors.append("'data_collection.symbols' debe ser una lista")
        
        # Validar timeframes
        if 'timeframes' not in data_collection:
            errors.append("'data_collection.timeframes' es requerido")
        
        return errors
    
    def _validate_portfolio_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de portafolio"""
        errors = []
        
        if 'portfolio_management' not in config:
            errors.append("Sección 'portfolio_management' no encontrada")
            return errors
        
        portfolio = config['portfolio_management']
        
        # Validar asignación de capital
        if 'capital_allocation' not in portfolio:
            errors.append("'portfolio_management.capital_allocation' es requerido")
        elif 'method' not in portfolio['capital_allocation']:
            errors.append("'capital_allocation.method' es requerido")
        
        # Validar diversificación
        if 'diversification' not in portfolio:
            errors.append("'portfolio_management.diversification' es requerido")
        
        return errors
    
    def _validate_risk_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de riesgo"""
        errors = []
        
        if 'risk_management' not in config:
            errors.append("Sección 'risk_management' no encontrada")
            return errors
        
        risk = config['risk_management']
        
        # Validar límites de posición
        if 'position_sizing' not in risk:
            errors.append("'risk_management.position_sizing' es requerido")
        
        # Validar límites de exposición
        if 'exposure_limits' not in risk:
            errors.append("'risk_management.exposure_limits' es requerido")
        
        return errors
    
    def _validate_security_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de seguridad"""
        errors = []
        
        if 'security' not in config:
            errors.append("Sección 'security' no encontrada")
            return errors
        
        security = config['security']
        
        # Validar encriptación
        if 'encryption' not in security:
            errors.append("'security.encryption' es requerido")
        
        # Validar auditoría
        if 'audit' not in security:
            errors.append("'security.audit' es requerido")
        
        return errors
    
    def _validate_infrastructure_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de infraestructura"""
        errors = []
        
        if 'infrastructure' not in config:
            errors.append("Sección 'infrastructure' no encontrada")
            return errors
        
        infrastructure = config['infrastructure']
        
        # Validar Kafka
        if 'kafka' not in infrastructure:
            errors.append("'infrastructure.kafka' es requerido")
        
        # Validar Redis
        if 'redis' not in infrastructure:
            errors.append("'infrastructure.redis' es requerido")
        
        return errors
    
    def _validate_general_config(self, config: Dict[str, Any]) -> List[str]:
        """Validaciones generales para cualquier configuración"""
        errors = []
        
        # Verificar que no esté vacío
        if not config:
            errors.append("Configuración vacía")
        
        # Verificar estructura básica
        if not isinstance(config, dict):
            errors.append("Configuración debe ser un diccionario")
        
        return errors
    
    async def _validate_dependencies(self):
        """Valida dependencias entre configuraciones"""
        try:
            for dependency in self.dependencies:
                source_config = self.configs.get(dependency.source_config, {})
                target_config = self.configs.get(dependency.target_config, {})
                
                if not source_config or not target_config:
                    logger.warning(f"Dependencia no validada: {dependency.source_config} -> {dependency.target_config}")
                    continue
                
                # Validar que las claves requeridas existan
                for key in dependency.required_keys:
                    if not self._key_exists(source_config, key):
                        logger.warning(f"Clave requerida '{key}' no encontrada en {dependency.source_config}")
                
        except Exception as e:
            logger.error(f"Error validando dependencias: {e}")
    
    def _key_exists(self, config: Dict[str, Any], key_path: str) -> bool:
        """Verifica si una clave existe en la configuración"""
        try:
            keys = key_path.split('.')
            current = config
            
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    return False
                current = current[key]
            
            return True
        except Exception:
            return False
    
    async def _setup_hot_reload(self):
        """Configura hot-reload de configuraciones"""
        try:
            self.file_handler = ConfigFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(self.file_handler, str(self.config_dir), recursive=False)
            self.observer.start()
            
            logger.info("Hot-reload de configuraciones habilitado")
            
        except Exception as e:
            logger.error(f"Error configurando hot-reload: {e}")
    
    async def _notify_config_change(self, config_file: str):
        """Notifica cambios de configuración a módulos relevantes"""
        try:
            # En un sistema real, esto notificaría a los módulos que usan esta configuración
            logger.info(f"Configuración {config_file} cambiada, notificando módulos")
            
            # Aquí se implementaría la notificación a módulos específicos
            # Por ejemplo, usando eventos asyncio o un sistema de pub/sub
            
        except Exception as e:
            logger.error(f"Error notificando cambio de configuración: {e}")
    
    def get_config(self, config_file: str, key_path: str = None, default: Any = None) -> Any:
        """Obtiene una configuración específica"""
        try:
            config_data = self.configs.get(config_file, {})
            
            if key_path is None:
                return config_data
            
            # Navegar por la ruta de claves
            keys = key_path.split('.')
            current = config_data
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            
            return current
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración {config_file}.{key_path}: {e}")
            return default
    
    def get_module_configs(self, module: str) -> Dict[str, Any]:
        """Obtiene configuraciones para un módulo específico"""
        try:
            module_configs = {}
            config_files = self.module_configs.get(module, [])
            
            for config_file in config_files:
                if config_file in self.configs:
                    module_configs[config_file] = self.configs[config_file]
            
            return module_configs
            
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones para módulo {module}: {e}")
            return {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """Obtiene un valor usando ruta de claves (notación de puntos) buscando en todas las configuraciones cargadas.
        Devuelve el primer resultado encontrado.
        """
        try:
            # Búsqueda directa por archivo si la ruta parece incluir nombre de archivo (e.g., data_config.yaml.data_collection)
            if ":" in key_path or key_path.endswith(".yaml"):
                # Notación no soportada explícitamente; devolver default para evitar errores
                return default
            
            keys = key_path.split(".") if key_path else []
            if not keys:
                return default
            
            # Intentar coincidencias conocidas por archivo para acelerar
            preferred_files = []
            if keys[0] in {"data_collection", "historical_data", "database", "alignment", "real_time_data"}:
                preferred_files.append("data_config.yaml")
            if keys[0] in {"trading", "portfolio_management", "risk_management", "security", "infrastructure"}:
                # Buscar primero en enterprise
                preferred_files.extend([
                    "trading.yaml",
                    "portfolio_management.yaml",
                    "risk_management.yaml",
                    "security.yaml",
                    "infrastructure.yaml",
                ])
            
            # Lista de archivos a revisar: preferidos primero, luego el resto
            files_to_search = []
            files_to_search.extend([f for f in preferred_files if f in self.configs])
            files_to_search.extend([f for f in self.configs.keys() if f not in files_to_search])
            
            for config_file in files_to_search:
                config_data = self.configs.get(config_file, {})
                value = self._get_nested_value(config_data, keys)
                if value is not None:
                    return value
            
            return default
        except Exception as e:
            logger.error(f"Error en get('{key_path}'): {e}")
            return default

    def _get_nested_value(self, config: Dict[str, Any], keys: List[str]) -> Any:
        """Obtiene valor anidado dado un diccionario y lista de claves."""
        try:
            current: Any = config
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except Exception:
            return None
    
    def get_validation_status(self) -> Dict[str, Any]:
        """Obtiene el estado de validación de todas las configuraciones"""
        try:
            status = {
                'total_configs': len(self.configs),
                'valid_configs': 0,
                'invalid_configs': 0,
                'validation_results': {}
            }
            
            for config_file, result in self.validation_results.items():
                if result.is_valid:
                    status['valid_configs'] += 1
                else:
                    status['invalid_configs'] += 1
                
                status['validation_results'][config_file] = {
                    'is_valid': result.is_valid,
                    'error_count': len(result.errors),
                    'warning_count': len(result.warnings),
                    'last_modified': result.last_modified.isoformat()
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de validación: {e}")
            return {}
    
    async def export_configs(self, output_dir: str = "config/exported") -> str:
        """Exporta todas las configuraciones a un directorio"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for config_file, config_data in self.configs.items():
                # Exportar como JSON
                json_file = output_path / f"{config_file.replace('.yaml', '')}_{timestamp}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False, default=str)
                
                # Exportar como YAML
                yaml_file = output_path / f"{config_file.replace('.yaml', '')}_{timestamp}.yaml"
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # Exportar estado de validación
            validation_file = output_path / f"validation_status_{timestamp}.json"
            with open(validation_file, 'w', encoding='utf-8') as f:
                json.dump(self.get_validation_status(), f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Configuraciones exportadas a: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando configuraciones: {e}")
            return None
    
    async def cleanup(self):
        """Limpia recursos del gestor de configuraciones"""
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("UnifiedConfigManager limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando UnifiedConfigManager: {e}")

# Instancia global
unified_config = UnifiedConfigManager()
