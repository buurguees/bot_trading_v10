"""
config/config_loader.py
Cargador de configuración YAML para el usuario
Ubicación: C:\TradingBot_v10\config\config_loader.py

Este módulo carga y valida la configuración del usuario desde archivos YAML,
permitiendo personalización sin tocar el código.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass, field
from .settings import config as base_config

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Cargador de configuración desde archivos YAML"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_dir = Path(__file__).parent
        self.user_config_path = config_path or (self.config_dir / "user_settings.yaml")
        self.user_config = {}
        self.load_user_config()
    
    def load_user_config(self):
        """Carga la configuración del usuario desde YAML"""
        try:
            if self.user_config_path.exists():
                with open(self.user_config_path, 'r', encoding='utf-8') as file:
                    self.user_config = yaml.safe_load(file) or {}
                logger.info(f"Configuración de usuario cargada desde {self.user_config_path}")
            else:
                logger.warning(f"Archivo de configuración no encontrado: {self.user_config_path}")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error cargando configuración de usuario: {e}")
            self.user_config = {}
    
    def _create_default_config(self):
        """Crea un archivo de configuración por defecto si no existe"""
        default_config = {
            'bot_settings': {
                'name': 'TradingBot_v10',
                'trading_mode': 'moderate',
                'features': {
                    'auto_trading': True,
                    'auto_retraining': True,
                    'risk_management': True,
                    'stop_on_drawdown': True,
                    'adaptive_sizing': True
                }
            },
            'capital_management': {
                'initial_balance': 1000.0,
                'max_risk_per_trade': 2.0,
                'max_daily_loss_pct': 5.0,
                'max_weekly_loss_pct': 15.0,
                'max_drawdown_pct': 20.0
            }
        }
        
        try:
            with open(self.user_config_path, 'w', encoding='utf-8') as file:
                yaml.dump(default_config, file, default_flow_style=False, allow_unicode=True)
            logger.info(f"Archivo de configuración por defecto creado: {self.user_config_path}")
        except Exception as e:
            logger.error(f"Error creando archivo de configuración por defecto: {e}")
    
    def get_trading_mode_settings(self) -> Dict[str, Any]:
        """Obtiene configuraciones basadas en el modo de trading seleccionado"""
        mode = self.get_value(['bot_settings', 'trading_mode'], 'moderate')
        
        mode_settings = {
            'conservative': {
                'max_risk_per_trade': 1.0,
                'min_confidence_to_trade': 75.0,
                'stop_loss_pct': 1.5,
                'take_profit_pct': 3.0,
                'max_daily_trades': 3
            },
            'moderate': {
                'max_risk_per_trade': 2.0,
                'min_confidence_to_trade': 65.0,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 4.0,
                'max_daily_trades': 5
            },
            'aggressive': {
                'max_risk_per_trade': 3.0,
                'min_confidence_to_trade': 55.0,
                'stop_loss_pct': 2.5,
                'take_profit_pct': 5.0,
                'max_daily_trades': 10
            },
            'custom': {}  # Usar valores exactos del YAML
        }
        
        return mode_settings.get(mode, mode_settings['moderate'])
    
    def get_value(self, keys: List[str], default: Any = None) -> Any:
        """Obtiene un valor de la configuración usando una lista de claves anidadas"""
        current = self.user_config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def get_bot_name(self) -> str:
        """Obtiene el nombre del bot"""
        return self.get_value(['bot_settings', 'name'], 'TradingBot_v10')
    
    def get_trading_mode(self) -> str:
        """Obtiene el modo de trading"""
        return self.get_value(['bot_settings', 'trading_mode'], 'moderate')
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Verifica si una característica está habilitada"""
        return self.get_value(['bot_settings', 'features', feature], True)
    
    def get_capital_settings(self) -> Dict[str, float]:
        """Obtiene configuraciones de capital y riesgo"""
        capital_config = self.get_value(['capital_management'], {})
        
        # Aplicar configuraciones del modo de trading si no están en custom
        mode_settings = self.get_trading_mode_settings()
        trading_mode = self.get_trading_mode()
        
        if trading_mode != 'custom':
            # Sobrescribir con configuraciones del modo
            for key, value in mode_settings.items():
                if key in capital_config:
                    continue  # Mantener valor del usuario si existe
                capital_config[key] = value
        
        return {
            'initial_balance': capital_config.get('initial_balance', 1000.0),
            'max_risk_per_trade': capital_config.get('max_risk_per_trade', 2.0),
            'max_daily_loss_pct': capital_config.get('max_daily_loss_pct', 5.0),
            'max_weekly_loss_pct': capital_config.get('max_weekly_loss_pct', 15.0),
            'max_drawdown_pct': capital_config.get('max_drawdown_pct', 20.0),
            'daily_profit_target': capital_config.get('daily_profit_target', 3.0),
            'take_profit_at_target': capital_config.get('take_profit_at_target', False)
        }
    
    def get_trading_settings(self) -> Dict[str, Any]:
        """Obtiene configuraciones de trading"""
        trading_config = self.get_value(['trading_settings'], {})
        mode_settings = self.get_trading_mode_settings()
        
        return {
            'primary_symbol': trading_config.get('primary_symbol', 'BTCUSDT'),
            'timeframes': trading_config.get('timeframes', {
                'primary': '1h',
                'secondary': '4h',
                'entry': '15m'
            }),
            'order_settings': trading_config.get('order_settings', {
                'preferred_order_type': 'limit',
                'limit_order_timeout': 5,
                'use_trailing_stops': True,
                'trailing_stop_distance': 1.5
            }),
            'stop_loss': {
                'method': trading_config.get('stop_loss', {}).get('method', 'adaptive'),
                'default_pct': mode_settings.get('stop_loss_pct', 
                    trading_config.get('stop_loss', {}).get('default_pct', 2.0)),
                'min_pct': trading_config.get('stop_loss', {}).get('min_pct', 0.5),
                'max_pct': trading_config.get('stop_loss', {}).get('max_pct', 5.0)
            },
            'take_profit': {
                'method': trading_config.get('take_profit', {}).get('method', 'scaled'),
                'default_pct': mode_settings.get('take_profit_pct', 
                    trading_config.get('take_profit', {}).get('default_pct', 4.0)),
                'levels': trading_config.get('take_profit', {}).get('levels', [
                    {'target': 2.0, 'close_pct': 33},
                    {'target': 4.0, 'close_pct': 50},
                    {'target': 8.0, 'close_pct': 100}
                ])
            }
        }
    
    def get_ai_model_settings(self) -> Dict[str, Any]:
        """Obtiene configuraciones del modelo de IA"""
        ai_config = self.get_value(['ai_model_settings'], {})
        mode_settings = self.get_trading_mode_settings()
        
        return {
            'confidence': {
                'min_confidence_to_trade': mode_settings.get('min_confidence_to_trade',
                    ai_config.get('confidence', {}).get('min_confidence_to_trade', 65.0)),
                'high_confidence_threshold': ai_config.get('confidence', {}).get('high_confidence_threshold', 80.0),
                'confidence_adjustments': ai_config.get('confidence', {}).get('confidence_adjustments', {
                    'low_confidence': 0.5,
                    'high_confidence': 1.5
                })
            },
            'retraining': ai_config.get('retraining', {
                'frequency': 'adaptive',
                'min_trades_before_retrain': 50,
                'retrain_on_poor_performance': True,
                'performance_threshold': 60.0
            }),
            'feature_importance': ai_config.get('feature_importance', {
                'price_action': 0.3,
                'technical_indicators': 0.4,
                'volume_analysis': 0.2,
                'market_sentiment': 0.1
            })
        }
    
    def get_reward_system_settings(self) -> Dict[str, Any]:
        """Obtiene configuraciones del sistema de recompensas"""
        return self.get_value(['reward_system'], {
            'rewards': {
                'profitable_trade': 1.0,
                'high_profit_bonus': 2.0,
                'quick_profit_bonus': 0.5,
                'low_risk_bonus': 0.3
            },
            'penalties': {
                'losing_trade': -0.5,
                'big_loss_penalty': -2.0,
                'missed_opportunity': -0.1,
                'early_stop_penalty': -0.2
            },
            'learning_factors': {
                'market_condition_bonus': 0.2,
                'consistency_bonus': 0.5,
                'volatility_adaptation': 0.3
            }
        })
    
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """Obtiene configuraciones de monitoreo"""
        return self.get_value(['monitoring'], {
            'dashboard': {
                'enabled': True,
                'auto_refresh_seconds': 30,
                'show_detailed_metrics': True,
                'show_model_predictions': True
            },
            'alerts': {
                'email_alerts': {
                    'enabled': False,
                    'events': ['large_loss', 'daily_limit_reached', 'system_error', 'high_profit']
                },
                'console_alerts': {
                    'enabled': True,
                    'events': ['trade_executed', 'model_retrained', 'risk_limit_hit', 'api_error']
                }
            },
            'reporting': {
                'daily_summary': True,
                'weekly_analysis': True,
                'model_performance_report': True
            }
        })
    
    def apply_to_base_config(self):
        """Aplica la configuración del usuario a la configuración base"""
        try:
            # Aplicar configuraciones de capital
            capital_settings = self.get_capital_settings()
            base_config.trading.initial_balance = capital_settings['initial_balance']
            base_config.trading.max_position_size_pct = capital_settings['max_risk_per_trade'] / 100.0
            base_config.trading.max_daily_loss_pct = capital_settings['max_daily_loss_pct'] / 100.0
            base_config.trading.max_drawdown_pct = capital_settings['max_drawdown_pct'] / 100.0
            
            # Aplicar configuraciones de trading
            trading_settings = self.get_trading_settings()
            base_config.trading.symbol = trading_settings['primary_symbol']
            base_config.trading.default_stop_loss_pct = trading_settings['stop_loss']['default_pct'] / 100.0
            base_config.trading.default_take_profit_pct = trading_settings['take_profit']['default_pct'] / 100.0
            
            # Aplicar configuraciones de IA
            ai_settings = self.get_ai_model_settings()
            base_config.ml.min_confidence_threshold = ai_settings['confidence']['min_confidence_to_trade'] / 100.0
            
            # Aplicar configuraciones de monitoreo
            monitoring_settings = self.get_monitoring_settings()
            base_config.monitoring.dashboard_enabled = monitoring_settings['dashboard']['enabled']
            
            logger.info("Configuración del usuario aplicada exitosamente")
            
        except Exception as e:
            logger.error(f"Error aplicando configuración del usuario: {e}")
    
    def validate_config(self) -> List[str]:
        """Valida la configuración del usuario"""
        errors = []
        
        # Validar configuraciones de capital
        capital_settings = self.get_capital_settings()
        if capital_settings['max_risk_per_trade'] <= 0 or capital_settings['max_risk_per_trade'] > 10:
            errors.append("max_risk_per_trade debe estar entre 0.1 y 10%")
        
        if capital_settings['max_daily_loss_pct'] <= 0 or capital_settings['max_daily_loss_pct'] > 50:
            errors.append("max_daily_loss_pct debe estar entre 0.1 y 50%")
        
        # Validar configuraciones de IA
        ai_settings = self.get_ai_model_settings()
        min_confidence = ai_settings['confidence']['min_confidence_to_trade']
        if min_confidence < 50 or min_confidence > 95:
            errors.append("min_confidence_to_trade debe estar entre 50 y 95%")
        
        # Validar símbolo
        trading_settings = self.get_trading_settings()
        if not trading_settings['primary_symbol'].endswith('USDT'):
            errors.append("primary_symbol debe terminar en USDT")
        
        return errors
    
    def save_config(self, new_config: Dict[str, Any]):
        """Guarda una nueva configuración al archivo YAML"""
        try:
            with open(self.user_config_path, 'w', encoding='utf-8') as file:
                yaml.dump(new_config, file, default_flow_style=False, allow_unicode=True)
            self.user_config = new_config
            logger.info("Configuración guardada exitosamente")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            raise
    
    def get_full_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa cargada"""
        return {
            'bot_settings': self.get_value(['bot_settings'], {}),
            'capital_management': self.get_capital_settings(),
            'trading_settings': self.get_trading_settings(),
            'ai_model_settings': self.get_ai_model_settings(),
            'reward_system': self.get_reward_system_settings(),
            'monitoring': self.get_monitoring_settings(),
            'trading_mode': self.get_trading_mode(),
            'mode_settings': self.get_trading_mode_settings()
        }

# Instancia global del cargador de configuración
user_config = ConfigLoader()

# Aplicar configuración del usuario al sistema
user_config.apply_to_base_config()

# Validar configuración
config_errors = user_config.validate_config()
if config_errors:
    logger.warning(f"Errores en configuración del usuario: {config_errors}")
else:
    logger.info("Configuración del usuario validada exitosamente")