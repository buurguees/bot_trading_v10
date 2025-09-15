#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Configuración Unificado v2 - Bot Trading v10 Enterprise
================================================================
Sistema de configuración centralizado con nueva arquitectura modular
que elimina duplicaciones y proporciona fuente única de verdad.

Arquitectura:
    config/
    ├── core/                    # Configuraciones centrales
    │   ├── symbols.yaml         # ÚNICA fuente de símbolos/timeframes
    │   ├── training_objectives.yaml  # Objetivos de entrenamiento
    │   ├── rewards.yaml         # Sistema de recompensas
    │   └── data_sources.yaml    # Fuentes de datos
    ├── environments/            # Por entorno
    │   ├── development.yaml
    │   ├── production.yaml
    │   └── testing.yaml
    ├── features/               # Por funcionalidad
    │   ├── ml.yaml
    │   ├── monitoring.yaml
    │   ├── risk_management.yaml
    │   └── telegram.yaml
    └── user_settings.yaml      # Settings del usuario

Autor: Bot Trading v10 Enterprise
Versión: 2.0.0
"""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class ConfigValidationResult:
    """Resultado de validación de configuración"""
    file_path: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    last_modified: datetime
    checksum: str

class UnifiedConfigManager:
    """
    Gestor de Configuración Unificado v2
    ===================================
    
    Gestiona todas las configuraciones del sistema con nueva arquitectura:
    - Eliminación de duplicaciones
    - Fuente única de verdad para símbolos/timeframes
    - Configuración jerárquica por dominios
    - Validación automática
    - Cache inteligente
    - Referencias entre archivos
    """
    
    def __init__(self, config_dir: str = "config", environment: str = "development"):
        """
        Inicializa el gestor de configuración
        
        Args:
            config_dir: Directorio base de configuraciones
            environment: Entorno activo (development/production/testing)
        """
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.configs = {}
        self.validation_results = {}
        self._cache = {}
        self._env_loaded = False
        
        # Estructuras de configuración
        self.core_configs = {}
        self.environment_configs = {}
        self.feature_configs = {}
        self.user_settings = {}
        
        # Metadatos
        self.last_reload = None
        self.config_hierarchy = []
        
        logger.info(f"🔧 Inicializando UnifiedConfigManager v2 - Entorno: {environment}")
        
        # Inicializar sistema
        self._initialize()
    
    def _initialize(self):
        """Inicializa el sistema de configuración"""
        try:
            # 1. Cargar variables de entorno
            self._load_environment()
            
            # 2. Cargar configuraciones core (fuente única de verdad)
            self._load_core_configs()
            
            # 3. Cargar configuraciones por entorno
            self._load_environment_configs()
            
            # 4. Cargar configuraciones por funcionalidad
            self._load_feature_configs()
            
            # 5. Cargar configuración del usuario
            self._load_user_settings()
            
            # 6. Validar configuraciones
            self._validate_all_configs()
            
            # 7. Construir jerarquía de configuración
            self._build_config_hierarchy()
            
            self.last_reload = datetime.now()
            logger.info("✅ UnifiedConfigManager v2 inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando UnifiedConfigManager: {e}")
            raise
    
    def _load_environment(self):
        """Carga variables de entorno desde .env"""
        if not self._env_loaded:
            env_files = [
                self.config_dir / ".env",
                Path(".env"),
                self.config_dir / f".env.{self.environment}"
            ]
            
            for env_file in env_files:
                if env_file.exists():
                    load_dotenv(env_file)
                    logger.debug(f"📁 Variables de entorno cargadas desde: {env_file}")
            
            self._env_loaded = True
    
    def _load_core_configs(self):
        """Carga configuraciones core (fuente única de verdad)"""
        core_dir = self.config_dir / "core"
        
        core_files = {
            "symbols": "symbols.yaml",
            "training_objectives": "training_objectives.yaml", 
            "rewards": "rewards.yaml",
            "data_sources": "data_sources.yaml",
            "trading": "trading.yaml"
        }
        
        for config_name, filename in core_files.items():
            file_path = core_dir / filename
            config_data = self._load_yaml_file(file_path)
            
            if config_data:
                self.core_configs[config_name] = config_data
                logger.debug(f"📊 Core config cargado: {config_name}")
            else:
                logger.warning(f"⚠️ Core config no encontrado: {filename}")
    
    def _load_environment_configs(self):
        """Carga configuraciones específicas del entorno"""
        env_dir = self.config_dir / "environments"
        env_file = env_dir / f"{self.environment}.yaml"
        
        if env_file.exists():
            self.environment_configs = self._load_yaml_file(env_file)
            logger.debug(f"🌍 Environment config cargado: {self.environment}")
        else:
            logger.warning(f"⚠️ Environment config no encontrado: {env_file}")
            self.environment_configs = {}
    
    def _load_feature_configs(self):
        """Carga configuraciones por funcionalidad"""
        features_dir = self.config_dir / "features"
        
        if not features_dir.exists():
            logger.warning(f"⚠️ Directorio features no encontrado: {features_dir}")
            return
        
        for yaml_file in features_dir.glob("*.yaml"):
            feature_name = yaml_file.stem
            config_data = self._load_yaml_file(yaml_file)
            
            if config_data:
                self.feature_configs[feature_name] = config_data
                logger.debug(f"🔧 Feature config cargado: {feature_name}")
    
    def _load_user_settings(self):
        """Carga configuración del usuario"""
        user_file = self.config_dir / "user_settings.yaml"
        
        if user_file.exists():
            self.user_settings = self._load_yaml_file(user_file)
            logger.debug("👤 User settings cargado")
        else:
            logger.warning(f"⚠️ User settings no encontrado: {user_file}")
            self.user_settings = {}
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Carga un archivo YAML con manejo de errores"""
        try:
            if not file_path.exists():
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
                
            # Procesar referencias entre archivos (${config.key.path})
            content = self._resolve_references(content)
            
            return content
            
        except yaml.YAMLError as e:
            logger.error(f"❌ Error YAML en {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error cargando {file_path}: {e}")
            return {}
    
    def _resolve_references(self, config: Any) -> Any:
        """Resuelve referencias entre archivos de configuración"""
        if isinstance(config, dict):
            return {k: self._resolve_references(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_references(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # Resolver referencia ${config.key.path}
            ref_path = config[2:-1]  # Remover ${ y }
            return self._get_reference_value(ref_path)
        else:
            return config
    
    def _get_reference_value(self, ref_path: str) -> Any:
        """Obtiene valor de referencia desde otra configuración"""
        try:
            # Ejemplo: training_objectives.financial_targets.balance.initial
            parts = ref_path.split('.')
            
            if len(parts) < 2:
                return None
            
            config_name = parts[0]
            key_path = '.'.join(parts[1:])
            
            # Buscar en configuraciones core
            if config_name in self.core_configs:
                return self._get_nested_value(self.core_configs[config_name], key_path)
            
            # Buscar en configuraciones de features
            if config_name in self.feature_configs:
                return self._get_nested_value(self.feature_configs[config_name], key_path)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Error resolviendo referencia {ref_path}: {e}")
            return None
    
    def _validate_all_configs(self):
        """Valida todas las configuraciones cargadas"""
        try:
            # Validar configuraciones core
            for config_name, config_data in self.core_configs.items():
                result = self._validate_config(f"core/{config_name}.yaml", config_data)
                self.validation_results[f"core_{config_name}"] = result
            
            # Validar configuraciones de features
            for feature_name, config_data in self.feature_configs.items():
                result = self._validate_config(f"features/{feature_name}.yaml", config_data)
                self.validation_results[f"feature_{feature_name}"] = result
            
            # Validar user settings
            if self.user_settings:
                result = self._validate_config("user_settings.yaml", self.user_settings)
                self.validation_results["user_settings"] = result
            
            # Resumen de validación
            valid_count = sum(1 for r in self.validation_results.values() if r.is_valid)
            total_count = len(self.validation_results)
            
            logger.info(f"🔍 Validación completada: {valid_count}/{total_count} configuraciones válidas")
            
        except Exception as e:
            logger.error(f"❌ Error en validación de configuraciones: {e}")
    
    def _validate_config(self, file_name: str, config_data: Dict[str, Any]) -> ConfigValidationResult:
        """Valida una configuración específica"""
        errors = []
        warnings = []
        
        try:
            # Validaciones básicas
            if not isinstance(config_data, dict):
                errors.append("Configuración debe ser un diccionario")
            
            if not config_data:
                warnings.append("Configuración está vacía")
            
            # Validaciones específicas por tipo
            if "symbols" in file_name:
                errors.extend(self._validate_symbols_config(config_data))
            elif "training_objectives" in file_name:
                errors.extend(self._validate_training_objectives_config(config_data))
            elif "rewards" in file_name:
                errors.extend(self._validate_rewards_config(config_data))
            
            # Crear resultado
            is_valid = len(errors) == 0
            
            return ConfigValidationResult(
                file_path=file_name,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                last_modified=datetime.now(),
                checksum=str(hash(str(config_data)))
            )
            
        except Exception as e:
            return ConfigValidationResult(
                file_path=file_name,
                is_valid=False,
                errors=[f"Error de validación: {e}"],
                warnings=[],
                last_modified=datetime.now(),
                checksum=""
            )
    
    def _validate_symbols_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de símbolos"""
        errors = []
        
        # Verificar estructura requerida
        required_sections = ["active_symbols", "timeframes"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Sección requerida faltante: {section}")
        
        # Validar símbolos activos
        if "active_symbols" in config:
            symbols = config["active_symbols"]
            if not isinstance(symbols, dict):
                errors.append("active_symbols debe ser un diccionario")
            else:
                for group_name, symbol_list in symbols.items():
                    if not isinstance(symbol_list, list):
                        errors.append(f"Grupo de símbolos {group_name} debe ser una lista")
                    elif not symbol_list:
                        errors.append(f"Grupo de símbolos {group_name} está vacío")
        
        # Validar timeframes
        if "timeframes" in config:
            timeframes = config["timeframes"]
            if not isinstance(timeframes, dict):
                errors.append("timeframes debe ser un diccionario")
            else:
                for tf_group, tf_list in timeframes.items():
                    if not isinstance(tf_list, list):
                        errors.append(f"Grupo de timeframes {tf_group} debe ser una lista")
        
        return errors
    
    def _validate_training_objectives_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de objetivos de entrenamiento"""
        errors = []
        
        # Verificar secciones requeridas
        required_sections = ["financial_targets", "performance_targets"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Sección requerida faltante: {section}")
        
        # Validar targets financieros
        if "financial_targets" in config:
            financial = config["financial_targets"]
            if "balance" in financial:
                balance = financial["balance"]
                if "initial" not in balance or "target" not in balance:
                    errors.append("balance debe tener 'initial' y 'target'")
        
        return errors
    
    def _validate_rewards_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración de recompensas"""
        errors = []
        
        # Verificar estructura básica
        if not any(key in config for key in ["profit_rewards", "risk_penalties", "ml_rewards"]):
            errors.append("Debe contener al menos una sección de rewards")
        
        return errors
    
    def _build_config_hierarchy(self):
        """Construye la jerarquía de configuración para resolución de valores"""
        self.config_hierarchy = [
            ("environment", self.environment_configs),
            ("user", self.user_settings),
            ("features", self.feature_configs),
            ("core", self.core_configs)
        ]
    
    # ==========================================
    # API PÚBLICA - MÉTODOS DE ACCESO
    # ==========================================
    
    def get_symbols(self) -> List[str]:
        """
        Obtiene lista de símbolos activos
        
        Returns:
            Lista de símbolos desde fuente única de verdad
        """
        try:
            # 1. Verificar override en user_settings
            user_symbols = self._get_nested_value(self.user_settings, "data_settings.symbols")
            if user_symbols and isinstance(user_symbols, list):
                return user_symbols
            
            # 2. Usar referencias de grupos en user_settings
            symbol_groups = self._get_nested_value(self.user_settings, "active_symbol_groups")
            if symbol_groups and isinstance(symbol_groups, list):
                symbols = []
                symbols_config = self.core_configs.get("symbols", {})
                active_symbols = symbols_config.get("active_symbols", {})
                
                for group in symbol_groups:
                    if group in active_symbols:
                        symbols.extend(active_symbols[group])
                
                if symbols:
                    return symbols
            
            # 3. Fallback: usar TODOS los símbolos (primary + secondary + experimental)
            symbols_config = self.core_configs.get("symbols", {})
            active_symbols = symbols_config.get("active_symbols", {})
            
            # Combinar todos los grupos de símbolos
            all_symbols = []
            for group in ["primary", "secondary", "experimental"]:
                if group in active_symbols:
                    all_symbols.extend(active_symbols[group])
            
            if all_symbols:
                return all_symbols
            
            # 4. Fallback final
            return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo símbolos: {e}")
            return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
    
    def get_timeframes(self) -> List[str]:
        """
        Obtiene lista de timeframes activos
        
        Returns:
            Lista de timeframes desde fuente única de verdad
        """
        try:
            # 1. Verificar override en user_settings
            user_timeframes = self._get_nested_value(self.user_settings, "trading_settings.timeframes")
            if user_timeframes and isinstance(user_timeframes, list):
                return user_timeframes
            
            # 2. Usar referencias de grupos en user_settings
            tf_groups = self._get_nested_value(self.user_settings, "active_timeframes")
            if tf_groups and isinstance(tf_groups, list):
                timeframes = []
                tf_config = self.core_configs.get("symbols", {})
                tf_groups_config = tf_config.get("timeframes", {})
                
                for group in tf_groups:
                    if group in tf_groups_config:
                        timeframes.extend(tf_groups_config[group])
                
                if timeframes:
                    return timeframes
            
            # 3. Fallback: usar TODOS los timeframes (real_time + analysis + strategic)
            tf_config = self.core_configs.get("symbols", {})
            timeframes_config = tf_config.get("timeframes", {})
            
            # Combinar todos los grupos de timeframes
            all_timeframes = []
            for group in ["real_time", "analysis", "strategic"]:
                if group in timeframes_config:
                    all_timeframes.extend(timeframes_config[group])
            
            if all_timeframes:
                return all_timeframes
            
            # 4. Fallback final
            return ["1m", "5m", "15m", "1h", "4h", "1d"]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo timeframes: {e}")
            return ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    def get_training_objectives(self) -> Dict[str, Any]:
        """
        Obtiene objetivos de entrenamiento
        
        Returns:
            Diccionario con todos los objetivos de entrenamiento
        """
        return self.core_configs.get("training_objectives", {})
    
    def get_financial_targets(self) -> Dict[str, Any]:
        """
        Obtiene targets financieros específicos
        
        Returns:
            Diccionario con targets financieros
        """
        objectives = self.get_training_objectives()
        return objectives.get("financial_targets", {})
    
    def get_performance_targets(self) -> Dict[str, Any]:
        """
        Obtiene targets de performance
        
        Returns:
            Diccionario con targets de performance
        """
        objectives = self.get_training_objectives()
        return objectives.get("performance_targets", {})
    
    def get_rewards_config(self) -> Dict[str, Any]:
        """
        Obtiene configuración de recompensas
        
        Returns:
            Diccionario con configuración de rewards/penalties
        """
        return self.core_configs.get("rewards", {})
    
    def get_initial_balance(self) -> float:
        """
        Obtiene balance inicial para entrenamiento
        
        Returns:
            Balance inicial desde training_objectives
        """
        try:
            # 1. Verificar override en user_settings
            user_balance = self._get_nested_value(self.user_settings, "capital_management.initial_balance")
            if user_balance is not None:
                return float(user_balance)
            
            # 2. Usar training_objectives
            financial = self.get_financial_targets()
            initial_balance = financial.get("balance", {}).get("initial", 1000.0)
            return float(initial_balance)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance inicial: {e}")
            return 1000.0
    
    def get_target_balance(self) -> float:
        """
        Obtiene balance objetivo para entrenamiento
        
        Returns:
            Balance objetivo desde training_objectives
        """
        try:
            financial = self.get_financial_targets()
            target_balance = financial.get("balance", {}).get("target", 100000.0)
            return float(target_balance)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance objetivo: {e}")
            return 100000.0
    
    def get_target_roi(self) -> float:
        """
        Obtiene ROI objetivo
        
        Returns:
            ROI objetivo en porcentaje
        """
        try:
            financial = self.get_financial_targets()
            target_roi = financial.get("roi", {}).get("target_pct", 9900.0)
            return float(target_roi)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo ROI objetivo: {e}")
            return 9900.0
    
    def get_target_winrate(self) -> float:
        """
        Obtiene win rate objetivo
        
        Returns:
            Win rate objetivo en porcentaje
        """
        try:
            performance = self.get_performance_targets()
            target_winrate = performance.get("win_rate", {}).get("target_pct", 75.0)
            return float(target_winrate)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo win rate objetivo: {e}")
            return 75.0
    
    def get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene configuración específica de un símbolo
        
        Args:
            symbol: Símbolo a consultar (ej: BTCUSDT)
            
        Returns:
            Configuración específica del símbolo
        """
        try:
            symbols_config = self.core_configs.get("symbols", {})
            symbol_configs = symbols_config.get("symbol_configs", {})
            return symbol_configs.get(symbol, {})
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo config de símbolo {symbol}: {e}")
            return {}
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """
        Obtiene configuración de Telegram
        
        Returns:
            Configuración de Telegram con tokens y chat_id
        """
        try:
            # Combinar configuración de features y variables de entorno
            telegram_feature = self.feature_configs.get("telegram", {})
            
            return {
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
                "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
                "enabled": telegram_feature.get("enabled", True),
                "update_interval": telegram_feature.get("update_interval", 60),
                "max_message_length": telegram_feature.get("max_message_length", 4096),
                "retry_attempts": telegram_feature.get("retry_attempts", 3)
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo config de Telegram: {e}")
            return {}
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """
        Obtiene límites de riesgo
        
        Returns:
            Diccionario con límites de riesgo y circuit breakers
        """
        try:
            # Combinar de training_objectives y user_settings
            objectives = self.get_training_objectives()
            safety_limits = objectives.get("safety_limits", {})
            
            user_capital = self._get_nested_value(self.user_settings, "capital_management")
            
            return {
                "max_daily_loss_pct": user_capital.get("max_daily_loss_pct") if user_capital else safety_limits.get("emergency_stop", {}).get("max_daily_loss_pct", 10.0),
                "max_drawdown_pct": safety_limits.get("emergency_stop", {}).get("max_drawdown_pct", 25.0),
                "max_risk_per_trade": user_capital.get("max_risk_per_trade") if user_capital else 2.0,
                "consecutive_losses_limit": safety_limits.get("emergency_stop", {}).get("consecutive_losses", 8)
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo límites de riesgo: {e}")
            return {}
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene valor usando notación de puntos con jerarquía de configuración
        
        Args:
            key_path: Ruta del valor (ej: 'financial_targets.balance.initial')
            default: Valor por defecto si no se encuentra
            
        Returns:
            Valor encontrado o default
        """
        try:
            # Buscar en jerarquía de configuración (environment > user > features > core)
            for config_type, config_data in self.config_hierarchy:
                if isinstance(config_data, dict):
                    value = self._get_nested_value(config_data, key_path)
                    if value is not None:
                        return value
                elif isinstance(config_data, dict):
                    # Para features que es un dict de configs
                    for feature_config in config_data.values():
                        value = self._get_nested_value(feature_config, key_path)
                        if value is not None:
                            return value
            
            return default
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo valor para {key_path}: {e}")
            return default
    
    def _get_nested_value(self, config: Dict[str, Any], key_path: str) -> Any:
        """
        Obtiene valor anidado usando notación de puntos
        
        Args:
            config: Diccionario de configuración
            key_path: Ruta del valor (ej: 'section.subsection.key')
            
        Returns:
            Valor encontrado o None
        """
        try:
            if not isinstance(config, dict):
                return None
            
            keys = key_path.split('.')
            current = config
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current
            
        except Exception:
            return None
    
    # ==========================================
    # UTILIDADES Y MANTENIMIENTO
    # ==========================================
    
    def reload_configs(self):
        """Recarga todas las configuraciones"""
        try:
            logger.info("🔄 Recargando todas las configuraciones...")
            
            # Limpiar cache
            self._cache.clear()
            self.configs.clear()
            self.validation_results.clear()
            
            # Reinicializar
            self._initialize()
            
            logger.info("✅ Configuraciones recargadas exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error recargando configuraciones: {e}")
            raise
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen de validación de configuraciones
        
        Returns:
            Resumen del estado de validación
        """
        try:
            total_configs = len(self.validation_results)
            valid_configs = sum(1 for r in self.validation_results.values() if r.is_valid)
            invalid_configs = total_configs - valid_configs
            
            errors = []
            warnings = []
            
            for result in self.validation_results.values():
                errors.extend(result.errors)
                warnings.extend(result.warnings)
            
            return {
                "total_configs": total_configs,
                "valid_configs": valid_configs,
                "invalid_configs": invalid_configs,
                "total_errors": len(errors),
                "total_warnings": len(warnings),
                "last_validation": self.last_reload.isoformat() if self.last_reload else None,
                "environment": self.environment,
                "errors": errors[:5],  # Solo primeros 5 errores
                "warnings": warnings[:5]  # Solo primeros 5 warnings
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen de validación: {e}")
            return {}
    
    def export_config(self, output_dir: str = "config/exported") -> str:
        """
        Exporta configuración completa consolidada
        
        Args:
            output_dir: Directorio de salida
            
        Returns:
            Path del archivo exportado
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Consolidar toda la configuración
            consolidated_config = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "environment": self.environment,
                    "version": "2.0.0"
                },
                "core": self.core_configs,
                "environment": self.environment_configs,
                "features": self.feature_configs,
                "user_settings": self.user_settings,
                "validation_summary": self.get_validation_summary()
            }
            
            # Exportar como JSON
            json_file = output_path / f"unified_config_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated_config, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📤 Configuración exportada: {json_file}")
            return str(json_file)
            
        except Exception as e:
            logger.error(f"❌ Error exportando configuración: {e}")
            return ""
    
    def get_config_status(self) -> Dict[str, Any]:
        """
        Obtiene estado completo del sistema de configuración
        
        Returns:
            Estado detallado del sistema
        """
        try:
            return {
                "system_info": {
                    "version": "2.0.0",
                    "environment": self.environment,
                    "config_dir": str(self.config_dir),
                    "last_reload": self.last_reload.isoformat() if self.last_reload else None
                },
                "loaded_configs": {
                    "core_configs": list(self.core_configs.keys()),
                    "feature_configs": list(self.feature_configs.keys()),
                    "has_environment_config": bool(self.environment_configs),
                    "has_user_settings": bool(self.user_settings)
                },
                "active_settings": {
                    "symbols": self.get_symbols(),
                    "timeframes": self.get_timeframes(),
                    "initial_balance": self.get_initial_balance(),
                    "target_balance": self.get_target_balance(),
                    "target_roi_pct": self.get_target_roi(),
                    "target_winrate_pct": self.get_target_winrate()
                },
                "validation": self.get_validation_summary()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de configuración: {e}")
            return {}
    
    def validate_trading_config(self) -> Dict[str, Any]:
        """
        Valida configuración específica para trading
        
        Returns:
            Resultado de validación para trading
        """
        try:
            errors = []
            warnings = []
            
            # Validar símbolos
            symbols = self.get_symbols()
            if not symbols:
                errors.append("No hay símbolos configurados")
            elif len(symbols) > 20:
                warnings.append(f"Muchos símbolos configurados ({len(symbols)}), puede afectar rendimiento")
            
            # Validar timeframes
            timeframes = self.get_timeframes()
            if not timeframes:
                errors.append("No hay timeframes configurados")
            
            # Validar balance
            initial_balance = self.get_initial_balance()
            if initial_balance <= 0:
                errors.append("Balance inicial debe ser mayor a 0")
            
            target_balance = self.get_target_balance()
            if target_balance <= initial_balance:
                warnings.append("Balance objetivo debería ser mayor al inicial")
            
            # Validar objetivos
            target_roi = self.get_target_roi()
            if target_roi <= 0:
                warnings.append("ROI objetivo debería ser positivo")
            
            target_winrate = self.get_target_winrate()
            if target_winrate <= 50 or target_winrate >= 100:
                warnings.append("Win rate objetivo debería estar entre 50% y 100%")
            
            # Validar configuración de Telegram
            telegram_config = self.get_telegram_config()
            if not telegram_config.get("bot_token"):
                warnings.append("Token de Telegram no configurado")
            if not telegram_config.get("chat_id"):
                warnings.append("Chat ID de Telegram no configurado")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "symbols_count": len(symbols),
                "timeframes_count": len(timeframes),
                "trading_ready": len(errors) == 0 and len(symbols) > 0 and len(timeframes) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error validando configuración de trading: {e}")
            return {
                "is_valid": False,
                "errors": [f"Error de validación: {e}"],
                "warnings": [],
                "trading_ready": False
            }
    
    def get_ml_config(self) -> Dict[str, Any]:
        """
        Obtiene configuración específica para Machine Learning
        
        Returns:
            Configuración consolidada para ML
        """
        try:
            ml_feature_config = self.feature_configs.get("ml", {})
            objectives = self.get_training_objectives()
            ml_objectives = objectives.get("ml_targets", {})
            
            return {
                "model_config": ml_feature_config.get("model", {}),
                "training_config": ml_feature_config.get("training", {}),
                "targets": {
                    "model_accuracy_target": ml_objectives.get("model_accuracy", {}).get("target_pct", 85.0),
                    "prediction_confidence_target": ml_objectives.get("prediction_confidence", {}).get("target_pct", 80.0),
                    "minimum_trading_confidence": ml_objectives.get("prediction_confidence", {}).get("minimum_trading_pct", 65.0)
                },
                "hyperparameters": ml_feature_config.get("hyperparameters", {}),
                "validation": ml_feature_config.get("validation", {})
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración ML: {e}")
            return {}
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Obtiene configuración de monitoreo
        
        Returns:
            Configuración de monitoreo y alertas
        """
        try:
            monitoring_config = self.feature_configs.get("monitoring", {})
            
            return {
                "dashboard": monitoring_config.get("dashboard", {}),
                "alerts": monitoring_config.get("alerts", {}),
                "metrics": monitoring_config.get("metrics", {}),
                "logging": monitoring_config.get("logging", {}),
                "telegram": self.get_telegram_config()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo configuración de monitoreo: {e}")
            return {}
    
    def update_user_setting(self, key_path: str, value: Any) -> bool:
        """
        Actualiza un setting del usuario y guarda el archivo
        
        Args:
            key_path: Ruta del setting (ej: 'trading_settings.symbols')
            value: Nuevo valor
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            # Actualizar en memoria
            keys = key_path.split('.')
            current = self.user_settings
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            
            # Guardar archivo
            user_file = self.config_dir / "user_settings.yaml"
            with open(user_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.user_settings, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"✅ User setting actualizado: {key_path} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando user setting {key_path}: {e}")
            return False
    
    def create_config_backup(self) -> str:
        """
        Crea backup de todas las configuraciones
        
        Returns:
            Path del archivo de backup
        """
        try:
            backup_dir = Path("config/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"config_backup_{timestamp}.json"
            
            backup_data = {
                "backup_info": {
                    "timestamp": datetime.now().isoformat(),
                    "environment": self.environment,
                    "version": "2.0.0"
                },
                "user_settings": self.user_settings,
                "environment_config": self.environment_configs,
                "validation_summary": self.get_validation_summary()
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"💾 Backup creado: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"❌ Error creando backup: {e}")
            return ""
    
    def __repr__(self) -> str:
        """Representación string del manager"""
        return f"UnifiedConfigManager(environment={self.environment}, configs={len(self.core_configs + self.feature_configs)})"


# ==========================================
# SINGLETON PARA USO GLOBAL
# ==========================================

# Instancia global del manager
_config_manager_instance = None

def get_config_manager(environment: str = "development") -> UnifiedConfigManager:
    """
    Obtiene instancia singleton del config manager
    
    Args:
        environment: Entorno de configuración
        
    Returns:
        Instancia del UnifiedConfigManager
    """
    global _config_manager_instance
    
    if _config_manager_instance is None:
        _config_manager_instance = UnifiedConfigManager(environment=environment)
    
    return _config_manager_instance

def reload_config_manager():
    """Fuerza recarga del config manager"""
    global _config_manager_instance
    
    if _config_manager_instance:
        _config_manager_instance.reload_configs()
    else:
        _config_manager_instance = UnifiedConfigManager()

# ==========================================
# FUNCIONES DE CONVENIENCIA
# ==========================================

def get_symbols() -> List[str]:
    """Función de conveniencia para obtener símbolos"""
    return get_config_manager().get_symbols()

def get_timeframes() -> List[str]:
    """Función de conveniencia para obtener timeframes"""
    return get_config_manager().get_timeframes()

def get_initial_balance() -> float:
    """Función de conveniencia para obtener balance inicial"""
    return get_config_manager().get_initial_balance()

def get_target_balance() -> float:
    """Función de conveniencia para obtener balance objetivo"""
    return get_config_manager().get_target_balance()

def get_training_objectives() -> Dict[str, Any]:
    """Función de conveniencia para obtener objetivos de entrenamiento"""
    return get_config_manager().get_training_objectives()

def get_telegram_config() -> Dict[str, Any]:
    """Función de conveniencia para obtener config de Telegram"""
    return get_config_manager().get_telegram_config()


# ==========================================
# EJEMPLO DE USO
# ==========================================

if __name__ == "__main__":
    # Ejemplo de uso del nuevo sistema de configuración
    
    # Crear manager
    config = UnifiedConfigManager(environment="development")
    
    # Obtener configuraciones
    print("🎯 Símbolos activos:", config.get_symbols())
    print("⏱️ Timeframes:", config.get_timeframes())
    print("💰 Balance inicial:", config.get_initial_balance())
    print("🎯 Balance objetivo:", config.get_target_balance())
    print("📈 ROI objetivo:", config.get_target_roi(), "%")
    print("🏆 Win rate objetivo:", config.get_target_winrate(), "%")
    
    # Validar configuración
    validation = config.validate_trading_config()
    print("✅ Trading config válida:", validation["is_valid"])
    
    if validation["errors"]:
        print("❌ Errores:", validation["errors"])
    
    if validation["warnings"]:
        print("⚠️ Advertencias:", validation["warnings"])
    
    # Status del sistema
    status = config.get_config_status()
    print("📊 Status del sistema:", json.dumps(status, indent=2, default=str))
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
            # Silenciar warnings de archivos legacy no encontrados
            pass
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
