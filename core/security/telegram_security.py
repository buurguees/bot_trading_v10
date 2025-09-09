# Ruta: core/security/telegram_security.py
#!/usr/bin/env python3
"""
Seguridad de Telegram - Trading Bot v10 Enterprise
=================================================

Sistema de seguridad avanzado para el bot de Telegram.
Incluye encriptación, validación de comandos y auditoría.

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import logging
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import os

logger = logging.getLogger(__name__)

class TelegramSecurity:
    """Sistema de seguridad para Telegram"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or os.getenv('ENCRYPTION_KEY')
        self.fernet = None
        self.allowed_commands = {
            'start', 'help', 'status', 'metrics', 'positions', 'balance', 'health',
            'train', 'stop_training', 'trade', 'stop_trading', 'set_mode', 
            'set_symbols', 'shutdown', 'start_trading', 'stop_trading', 
            'emergency_stop', 'settings'
        }
        self.critical_commands = {
            'trade', 'shutdown', 'emergency_stop', 'start_trading'
        }
        self.rate_limits = {}
        self.audit_log = []
        
        # Inicializar encriptación
        self._init_encryption()
        
        logger.info("🔒 Sistema de seguridad de Telegram inicializado")
    
    def _init_encryption(self):
        """Inicializa el sistema de encriptación"""
        try:
            if self.encryption_key:
                # Generar clave desde password
                password = self.encryption_key.encode()
                salt = b'trading_bot_v10_salt'  # Salt fijo para consistencia
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                self.fernet = Fernet(key)
                logger.info("✅ Encriptación inicializada")
            else:
                logger.warning("⚠️ ENCRYPTION_KEY no encontrada, usando encriptación básica")
        except Exception as e:
            logger.error(f"❌ Error inicializando encriptación: {e}")
    
    def encrypt_token(self, token: str) -> str:
        """Encripta el token del bot"""
        try:
            if self.fernet:
                encrypted = self.fernet.encrypt(token.encode())
                return encrypted.decode()
            else:
                # Encriptación básica si no hay Fernet
                return base64.b64encode(token.encode()).decode()
        except Exception as e:
            logger.error(f"❌ Error encriptando token: {e}")
            return token
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Desencripta el token del bot"""
        try:
            if self.fernet:
                decrypted = self.fernet.decrypt(encrypted_token.encode())
                return decrypted.decode()
            else:
                # Desencriptación básica
                return base64.b64decode(encrypted_token.encode()).decode()
        except Exception as e:
            logger.error(f"❌ Error desencriptando token: {e}")
            return encrypted_token
    
    def validate_chat_id(self, chat_id: str, allowed_chat_id: str) -> bool:
        """Valida que el chat_id esté autorizado"""
        try:
            # Comparación segura de strings
            return hmac.compare_digest(str(chat_id), str(allowed_chat_id))
        except Exception as e:
            logger.error(f"❌ Error validando chat_id: {e}")
            return False
    
    def validate_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Valida un comando de Telegram"""
        try:
            validation_result = {
                'valid': True,
                'command': command,
                'args': args,
                'errors': [],
                'warnings': []
            }
            
            # Verificar si el comando está permitido
            if command not in self.allowed_commands:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Comando '{command}' no permitido")
                return validation_result
            
            # Validar argumentos específicos por comando
            if command == 'train':
                validation_result.update(self._validate_train_args(args))
            elif command == 'trade':
                validation_result.update(self._validate_trade_args(args))
            elif command == 'set_mode':
                validation_result.update(self._validate_set_mode_args(args))
            elif command == 'set_symbols':
                validation_result.update(self._validate_set_symbols_args(args))
            
            # Verificar rate limiting
            if not self._check_rate_limit(command):
                validation_result['warnings'].append("Rate limit excedido")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error validando comando: {e}")
            return {
                'valid': False,
                'command': command,
                'args': args,
                'errors': [f"Error de validación: {str(e)}"],
                'warnings': []
            }
    
    def _validate_train_args(self, args: List[str]) -> Dict[str, Any]:
        """Valida argumentos del comando train"""
        result = {'errors': [], 'warnings': []}
        
        # Buscar símbolos
        symbols = []
        duration = '8h'
        
        for i, arg in enumerate(args):
            if arg.startswith('--symbols') and i + 1 < len(args):
                symbols = [s.strip().upper() for s in args[i + 1].split(',')]
            elif arg.startswith('--duration') and i + 1 < len(args):
                duration = args[i + 1]
            elif not arg.startswith('--'):
                symbols.append(arg.upper())
        
        # Validar símbolos
        if not symbols:
            symbols = ['BTCUSDT', 'ETHUSDT']
        
        valid_symbols = {'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOGEUSDT', 'LINKUSDT', 'TONUSDT', 'XRPUSDT'}
        invalid_symbols = [s for s in symbols if s not in valid_symbols]
        
        if invalid_symbols:
            result['errors'].append(f"Símbolos inválidos: {', '.join(invalid_symbols)}")
        
        # Validar duración
        if not self._validate_duration(duration):
            result['errors'].append(f"Duración inválida: {duration}")
        
        return result
    
    def _validate_trade_args(self, args: List[str]) -> Dict[str, Any]:
        """Valida argumentos del comando trade"""
        result = {'errors': [], 'warnings': []}
        
        mode = 'paper'
        symbols = []
        leverage = 10
        
        for i, arg in enumerate(args):
            if arg.startswith('--mode') and i + 1 < len(args):
                mode = args[i + 1].lower()
            elif arg.startswith('--symbols') and i + 1 < len(args):
                symbols = [s.strip().upper() for s in args[i + 1].split(',')]
            elif arg.startswith('--leverage') and i + 1 < len(args):
                try:
                    leverage = int(args[i + 1])
                except ValueError:
                    result['errors'].append(f"Leverage inválido: {args[i + 1]}")
            elif not arg.startswith('--'):
                symbols.append(arg.upper())
        
        # Validar modo
        if mode not in ['paper', 'live']:
            result['errors'].append(f"Modo inválido: {mode}")
        
        # Validar leverage
        if not (1 <= leverage <= 30):
            result['errors'].append(f"Leverage debe estar entre 1 y 30: {leverage}")
        
        # Validar símbolos
        if not symbols:
            symbols = ['BTCUSDT', 'ETHUSDT']
        
        valid_symbols = {'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOGEUSDT', 'LINKUSDT', 'TONUSDT', 'XRPUSDT'}
        invalid_symbols = [s for s in symbols if s not in valid_symbols]
        
        if invalid_symbols:
            result['errors'].append(f"Símbolos inválidos: {', '.join(invalid_symbols)}")
        
        return result
    
    def _validate_set_mode_args(self, args: List[str]) -> Dict[str, Any]:
        """Valida argumentos del comando set_mode"""
        result = {'errors': [], 'warnings': []}
        
        if not args:
            result['errors'].append("Modo no especificado")
        else:
            mode = args[0].lower()
            if mode not in ['paper', 'live']:
                result['errors'].append(f"Modo inválido: {mode}")
        
        return result
    
    def _validate_set_symbols_args(self, args: List[str]) -> Dict[str, Any]:
        """Valida argumentos del comando set_symbols"""
        result = {'errors': [], 'warnings': []}
        
        if not args:
            result['errors'].append("Símbolos no especificados")
        else:
            symbols = [s.strip().upper() for s in args[0].split(',')]
            valid_symbols = {'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOGEUSDT', 'LINKUSDT', 'TONUSDT', 'XRPUSDT'}
            invalid_symbols = [s for s in symbols if s not in valid_symbols]
            
            if invalid_symbols:
                result['errors'].append(f"Símbolos inválidos: {', '.join(invalid_symbols)}")
        
        return result
    
    def _validate_duration(self, duration: str) -> bool:
        """Valida formato de duración"""
        try:
            if duration.endswith('h'):
                hours = int(duration[:-1])
                return 1 <= hours <= 24
            elif duration.endswith('m'):
                minutes = int(duration[:-1])
                return 1 <= minutes <= 1440
            else:
                return False
        except ValueError:
            return False
    
    def _check_rate_limit(self, command: str, chat_id: str = "default") -> bool:
        """Verifica rate limiting"""
        try:
            now = time.time()
            key = f"{chat_id}_{command}"
            
            if key not in self.rate_limits:
                self.rate_limits[key] = []
            
            # Limpiar timestamps antiguos (más de 1 minuto)
            self.rate_limits[key] = [t for t in self.rate_limits[key] if now - t < 60]
            
            # Verificar límite (máximo 10 comandos por minuto por chat)
            if len(self.rate_limits[key]) >= 10:
                return False
            
            # Agregar timestamp actual
            self.rate_limits[key].append(now)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verificando rate limit: {e}")
            return True  # Permitir en caso de error
    
    def is_critical_command(self, command: str) -> bool:
        """Verifica si un comando es crítico"""
        return command in self.critical_commands
    
    def requires_confirmation(self, command: str) -> bool:
        """Verifica si un comando requiere confirmación"""
        return command in self.critical_commands
    
    def log_command(self, command: str, args: List[str], chat_id: str, success: bool = True):
        """Registra un comando en el log de auditoría"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'command': command,
                'args': args,
                'chat_id': chat_id,
                'success': success,
                'ip': 'telegram'  # Los comandos vienen de Telegram
            }
            
            self.audit_log.append(log_entry)
            
            # Mantener solo los últimos 1000 registros
            if len(self.audit_log) > 1000:
                self.audit_log = self.audit_log[-1000:]
            
            logger.info(f"🔍 Comando auditado: {command} | Chat: {chat_id} | Success: {success}")
            
        except Exception as e:
            logger.error(f"❌ Error registrando comando: {e}")
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene el log de auditoría"""
        return self.audit_log[-limit:]
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Genera un reporte de seguridad"""
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            
            # Filtrar comandos de las últimas 24 horas
            recent_commands = [
                cmd for cmd in self.audit_log
                if datetime.fromisoformat(cmd['timestamp']) > last_24h
            ]
            
            # Estadísticas
            total_commands = len(recent_commands)
            successful_commands = len([cmd for cmd in recent_commands if cmd['success']])
            failed_commands = total_commands - successful_commands
            
            # Comandos más usados
            command_counts = {}
            for cmd in recent_commands:
                command_counts[cmd['command']] = command_counts.get(cmd['command'], 0) + 1
            
            most_used = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'period': '24 horas',
                'total_commands': total_commands,
                'successful_commands': successful_commands,
                'failed_commands': failed_commands,
                'success_rate': (successful_commands / total_commands * 100) if total_commands > 0 else 0,
                'most_used_commands': most_used,
                'rate_limits_active': len(self.rate_limits),
                'encryption_enabled': self.fernet is not None,
                'generated_at': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte de seguridad: {e}")
            return {}
    
    def cleanup_old_data(self):
        """Limpia datos antiguos"""
        try:
            # Limpiar rate limits antiguos
            now = time.time()
            for key in list(self.rate_limits.keys()):
                self.rate_limits[key] = [t for t in self.rate_limits[key] if now - t < 3600]  # 1 hora
                if not self.rate_limits[key]:
                    del self.rate_limits[key]
            
            # Limpiar audit log antiguo (más de 7 días)
            week_ago = datetime.now() - timedelta(days=7)
            self.audit_log = [
                cmd for cmd in self.audit_log
                if datetime.fromisoformat(cmd['timestamp']) > week_ago
            ]
            
            logger.info("🧹 Datos antiguos limpiados")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando datos antiguos: {e}")

# Instancia global
telegram_security = TelegramSecurity()
