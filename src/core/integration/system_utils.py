#!/usr/bin/env python3
"""
Utilidades del Sistema Integrado - Trading Bot v10 Enterprise
============================================================

Utilidades para la integración del sistema completo con Telegram y dashboard.

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import asyncio
import logging
import json
import yaml
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import shlex

logger = logging.getLogger(__name__)

class CommandParser:
    """Parser de comandos de Telegram"""
    
    @staticmethod
    def parse_train_command(args: List[str]) -> Dict[str, Any]:
        """Parsea comando de entrenamiento"""
        parsed = {
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'duration': '8h',
            'mode': 'enterprise'
        }
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('--'):
                key = arg[2:]
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    value = args[i + 1]
                    if key == 'symbols' and ',' in value:
                        parsed[key] = [s.strip().upper() for s in value.split(',')]
                    else:
                        parsed[key] = value
                    i += 2
                else:
                    parsed[key] = True
                    i += 1
            else:
                # Argumento posicional - símbolos
                if 'symbols' not in parsed:
                    parsed['symbols'] = [arg.upper()]
                else:
                    parsed['symbols'].append(arg.upper())
                i += 1
        
        return parsed
    
    @staticmethod
    def parse_trade_command(args: List[str]) -> Dict[str, Any]:
        """Parsea comando de trading"""
        parsed = {
            'mode': 'paper',
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'leverage': 10
        }
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('--'):
                key = arg[2:]
                if i + 1 < len(args) and not args[i + 1].startswith('-'):
                    value = args[i + 1]
                    if key == 'symbols' and ',' in value:
                        parsed[key] = [s.strip().upper() for s in value.split(',')]
                    elif key == 'leverage':
                        parsed[key] = int(value)
                    else:
                        parsed[key] = value
                    i += 2
                else:
                    parsed[key] = True
                    i += 1
            else:
                # Argumento posicional - símbolos
                if 'symbols' not in parsed:
                    parsed['symbols'] = [arg.upper()]
                else:
                    parsed['symbols'].append(arg.upper())
                i += 1
        
        return parsed
    
    @staticmethod
    def parse_set_command(args: List[str]) -> Dict[str, Any]:
        """Parsea comando de configuración"""
        parsed = {}
        
        if not args:
            return parsed
        
        key = args[0]
        value = args[1] if len(args) > 1 else None
        
        if key == 'mode':
            parsed['mode'] = value
        elif key == 'symbols':
            if value and ',' in value:
                parsed['symbols'] = [s.strip().upper() for s in value.split(',')]
            elif value:
                parsed['symbols'] = [value.upper()]
        
        return parsed

class ConfirmationManager:
    """Maneja confirmaciones de comandos críticos"""
    
    def __init__(self, timeout: int = 300):
        self.pending_confirmations = {}
        self.timeout = timeout
        
    async def request_confirmation(self, command: str, args: Dict[str, Any], chat_id: str) -> bool:
        """Solicita confirmación para un comando"""
        confirmation_id = f"{chat_id}_{datetime.now().timestamp()}"
        
        self.pending_confirmations[confirmation_id] = {
            'command': command,
            'args': args,
            'chat_id': chat_id,
            'timestamp': datetime.now(),
            'confirmed': False
        }
        
        # Limpiar confirmaciones expiradas
        await self._cleanup_expired_confirmations()
        
        return confirmation_id
    
    async def confirm_command(self, confirmation_id: str) -> Optional[Dict[str, Any]]:
        """Confirma un comando"""
        if confirmation_id in self.pending_confirmations:
            self.pending_confirmations[confirmation_id]['confirmed'] = True
            return self.pending_confirmations.pop(confirmation_id)
        return None
    
    async def _cleanup_expired_confirmations(self):
        """Limpia confirmaciones expiradas"""
        now = datetime.now()
        expired = []
        
        for conf_id, conf in self.pending_confirmations.items():
            if (now - conf['timestamp']).total_seconds() > self.timeout:
                expired.append(conf_id)
        
        for conf_id in expired:
            del self.pending_confirmations[conf_id]

class MetricsFormatter:
    """Formatea métricas para diferentes salidas"""
    
    @staticmethod
    def format_telegram_metrics(metrics: Dict[str, Any]) -> str:
        """Formatea métricas para Telegram"""
        try:
            # Determinar emoji de estado
            pnl = metrics.get('pnl_today', 0)
            if pnl > 0:
                pnl_emoji = "📈"
            elif pnl < 0:
                pnl_emoji = "📉"
            else:
                pnl_emoji = "➡️"
            
            # Determinar emoji de salud
            health = metrics.get('health_score', 0)
            if health >= 90:
                health_emoji = "🟢"
            elif health >= 70:
                health_emoji = "🟡"
            else:
                health_emoji = "🔴"
            
            message = f"""
📊 <b>Métricas del Sistema</b>
⏰ {datetime.now().strftime('%H:%M:%S')}

💰 <b>Balance:</b> ${metrics.get('balance', 0):,.2f}
{pnl_emoji} <b>PnL Hoy:</b> ${pnl:,.2f}
🎯 <b>Win Rate:</b> {metrics.get('win_rate', 0):.1f}%
📉 <b>Drawdown:</b> {metrics.get('drawdown', 0):.1f}%
⚡ <b>Latencia:</b> {metrics.get('latency', 0):.1f}ms
🔄 <b>Trades:</b> {metrics.get('trades_today', 0)}
📊 <b>Posiciones:</b> {metrics.get('positions', 0)}
{health_emoji} <b>Salud:</b> {health:.1f}%
            """
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"❌ Error formateando métricas: {e}")
            return "❌ Error obteniendo métricas del sistema"
    
    @staticmethod
    def format_dashboard_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea métricas para el dashboard"""
        try:
            return {
                'balance': metrics.get('balance', 0),
                'pnl_today': metrics.get('pnl_today', 0),
                'win_rate': metrics.get('win_rate', 0),
                'drawdown': metrics.get('drawdown', 0),
                'latency': metrics.get('latency', 0),
                'trades_today': metrics.get('trades_today', 0),
                'positions': metrics.get('positions', 0),
                'health_score': metrics.get('health_score', 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error formateando métricas para dashboard: {e}")
            return {}

class SystemStatus:
    """Maneja el estado del sistema"""
    
    def __init__(self):
        self.is_running = False
        self.is_training = False
        self.is_trading = False
        self.current_mode = "paper"
        self.current_symbols = ["BTCUSDT", "ETHUSDT"]
        self.last_update = datetime.now()
        
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del sistema"""
        return {
            'is_running': self.is_running,
            'is_training': self.is_training,
            'is_trading': self.is_trading,
            'current_mode': self.current_mode,
            'current_symbols': self.current_symbols,
            'last_update': self.last_update.isoformat()
        }
    
    def update_status(self, **kwargs):
        """Actualiza el estado del sistema"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_update = datetime.now()

class ConfigManager:
    """Maneja la configuración del sistema integrado"""
    
    def __init__(self, config_path: str = "notifications/telegram/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            return {}
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Obtiene configuración de Telegram"""
        return self.config.get('telegram', {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """Obtiene configuración del sistema"""
        return self.config.get('system', {})
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Obtiene configuración del dashboard"""
        return self.config.get('system', {}).get('dashboard', {})
    
    def is_telegram_enabled(self) -> bool:
        """Verifica si Telegram está habilitado"""
        return self.get_telegram_config().get('enabled', False)
    
    def is_dashboard_enabled(self) -> bool:
        """Verifica si el dashboard está habilitado"""
        return self.get_dashboard_config().get('enabled', True)

class LogManager:
    """Maneja logs del sistema integrado"""
    
    def __init__(self, log_file: str = "logs/integrated_system.log"):
        self.log_file = log_file
        self._setup_logging()
    
    def _setup_logging(self):
        """Configura el logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def log_command(self, command: str, args: Dict[str, Any], chat_id: str):
        """Registra un comando ejecutado"""
        logger.info(f"🎮 Comando ejecutado: {command} | Args: {args} | Chat: {chat_id}")
    
    def log_error(self, error: str, context: str = ""):
        """Registra un error"""
        logger.error(f"❌ Error en {context}: {error}")
    
    def log_system_event(self, event: str, details: Dict[str, Any] = None):
        """Registra un evento del sistema"""
        details_str = f" | Detalles: {details}" if details else ""
        logger.info(f"🔄 Evento del sistema: {event}{details_str}")

# Instancias globales
command_parser = CommandParser()
confirmation_manager = ConfirmationManager()
metrics_formatter = MetricsFormatter()
system_status = SystemStatus()
config_manager = ConfigManager()
log_manager = LogManager()
