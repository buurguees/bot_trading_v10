# Ruta: control/security_guard.py
# security_guard.py - Guardián de seguridad para comandos
# Ubicación: control/security_guard.py

"""
Guardián de Seguridad para Comandos
Valida y audita comandos de Telegram y sistema

Características principales:
- Validación de autorización
- Rate limiting
- Auditoría de comandos
- Detección de anomalías
- Bloqueo de accesos no autorizados
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
from core.config.config_loader import config_loader
from core.security.audit_logger import audit_logger, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)

class AccessLevel(Enum):
    """Nivel de acceso"""
    READONLY = "readonly"
    TRADING = "trading"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class CommandStatus(Enum):
    """Estado del comando"""
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    SUSPICIOUS = "suspicious"

@dataclass
class SecurityEvent:
    """Evento de seguridad"""
    event_id: str
    event_type: str
    user_id: str
    chat_id: str
    command: str
    status: CommandStatus
    timestamp: datetime
    details: Dict[str, Any]
    risk_score: float

@dataclass
class RateLimitInfo:
    """Información de rate limiting"""
    user_id: str
    requests_count: int
    window_start: datetime
    blocked_until: Optional[datetime] = None

class SecurityGuard:
    """Guardián de seguridad para comandos"""
    
    def __init__(self):
        self.config_loader = config_loader
        self.audit_logger = audit_logger
        self.control_config = {}
        self.security_config = {}
        
        # Configuración de seguridad
        self.authorized_chat_ids: Set[str] = set()
        self.rate_limits: Dict[str, RateLimitInfo] = {}
        self.blocked_users: Set[str] = set()
        self.suspicious_activities: List[SecurityEvent] = []
        
        # Configuración de rate limiting
        self.max_requests_per_minute = 20
        self.max_requests_per_hour = 100
        self.block_duration = 300  # seconds
        
        # Configuración de comandos
        self.require_confirmation = True
        self.confirmation_timeout = 30
        self.max_concurrent_commands = 3
        
        logger.info("SecurityGuard inicializado")
    
    async def initialize(self):
        """Inicializa el guardián de seguridad"""
        try:
            # Inicializar configuraciones
            await self.config_loader.initialize()
            
            # Cargar configuración de control
            self.control_config = self.config_loader.get_control_config()
            
            # Cargar configuración de seguridad
            self.security_config = self.config_loader.get_security_config()
            
            # Configurar autorización
            self.authorized_chat_ids = set(
                self.control_config.get('security', {}).get('authorized_chat_ids', [])
            )
            
            # Configurar rate limiting
            rate_limiting = self.control_config.get('security', {}).get('rate_limiting', {})
            self.max_requests_per_minute = rate_limiting.get('max_requests_per_minute', 20)
            self.max_requests_per_hour = rate_limiting.get('max_requests_per_hour', 100)
            self.block_duration = rate_limiting.get('block_duration', 300)
            
            # Configurar comandos
            commands_config = self.control_config.get('commands', {})
            self.require_confirmation = commands_config.get('require_confirmation', True)
            self.confirmation_timeout = commands_config.get('confirmation_timeout', 30)
            self.max_concurrent_commands = commands_config.get('max_concurrent_commands', 3)
            
            logger.info("SecurityGuard inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando SecurityGuard: {e}")
            raise
    
    async def validate_command(self, 
                             user_id: str, 
                             chat_id: str, 
                             command: str, 
                             args: List[str] = None) -> Dict[str, Any]:
        """Valida un comando de seguridad"""
        try:
            # Verificar si el usuario está bloqueado
            if user_id in self.blocked_users:
                await self._log_security_event(
                    user_id, chat_id, command, CommandStatus.BLOCKED,
                    "Usuario bloqueado", {"args": args}
                )
                return {
                    'status': CommandStatus.BLOCKED.value,
                    'message': 'Usuario bloqueado por seguridad',
                    'blocked_until': None
                }
            
            # Verificar autorización
            if not await self._check_authorization(chat_id):
                await self._log_security_event(
                    user_id, chat_id, command, CommandStatus.UNAUTHORIZED,
                    "Acceso no autorizado", {"args": args}
                )
                return {
                    'status': CommandStatus.UNAUTHORIZED.value,
                    'message': 'Acceso no autorizado'
                }
            
            # Verificar rate limiting
            rate_limit_result = await self._check_rate_limit(user_id)
            if rate_limit_result['blocked']:
                await self._log_security_event(
                    user_id, chat_id, command, CommandStatus.RATE_LIMITED,
                    "Rate limit excedido", {"args": args, "blocked_until": rate_limit_result['blocked_until']}
                )
                return {
                    'status': CommandStatus.RATE_LIMITED.value,
                    'message': 'Rate limit excedido',
                    'blocked_until': rate_limit_result['blocked_until']
                }
            
            # Verificar comando sospechoso
            if await self._is_suspicious_command(command, args):
                await self._log_security_event(
                    user_id, chat_id, command, CommandStatus.SUSPICIOUS,
                    "Comando sospechoso detectado", {"args": args}
                )
                return {
                    'status': CommandStatus.SUSPICIOUS.value,
                    'message': 'Comando sospechoso detectado'
                }
            
            # Comando permitido
            await self._log_security_event(
                user_id, chat_id, command, CommandStatus.ALLOWED,
                "Comando permitido", {"args": args}
            )
            
            return {
                'status': CommandStatus.ALLOWED.value,
                'message': 'Comando permitido',
                'requires_confirmation': self._requires_confirmation(command)
            }
            
        except Exception as e:
            logger.error(f"Error validando comando: {e}")
            await self._log_security_event(
                user_id, chat_id, command, CommandStatus.BLOCKED,
                "Error en validación", {"args": args, "error": str(e)}
            )
            return {
                'status': CommandStatus.BLOCKED.value,
                'message': 'Error en validación de seguridad'
            }
    
    async def _check_authorization(self, chat_id: str) -> bool:
        """Verifica autorización del chat"""
        try:
            # Si no hay chat IDs autorizados, permitir todos
            if not self.authorized_chat_ids:
                return True
            
            # Verificar si el chat está autorizado
            return chat_id in self.authorized_chat_ids
            
        except Exception as e:
            logger.error(f"Error verificando autorización: {e}")
            return False
    
    async def _check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """Verifica rate limiting del usuario"""
        try:
            current_time = datetime.now()
            
            # Obtener información de rate limit del usuario
            if user_id not in self.rate_limits:
                self.rate_limits[user_id] = RateLimitInfo(
                    user_id=user_id,
                    requests_count=0,
                    window_start=current_time
                )
            
            rate_limit_info = self.rate_limits[user_id]
            
            # Verificar si el usuario está bloqueado
            if rate_limit_info.blocked_until and current_time < rate_limit_info.blocked_until:
                return {
                    'blocked': True,
                    'blocked_until': rate_limit_info.blocked_until.isoformat()
                }
            
            # Resetear contador si la ventana ha expirado
            if current_time - rate_limit_info.window_start > timedelta(minutes=1):
                rate_limit_info.requests_count = 0
                rate_limit_info.window_start = current_time
                rate_limit_info.blocked_until = None
            
            # Incrementar contador de requests
            rate_limit_info.requests_count += 1
            
            # Verificar límites
            if rate_limit_info.requests_count > self.max_requests_per_minute:
                # Bloquear usuario
                rate_limit_info.blocked_until = current_time + timedelta(seconds=self.block_duration)
                self.blocked_users.add(user_id)
                
                return {
                    'blocked': True,
                    'blocked_until': rate_limit_info.blocked_until.isoformat()
                }
            
            return {'blocked': False}
            
        except Exception as e:
            logger.error(f"Error verificando rate limit: {e}")
            return {'blocked': True, 'blocked_until': None}
    
    async def _is_suspicious_command(self, command: str, args: List[str] = None) -> bool:
        """Verifica si un comando es sospechoso"""
        try:
            # Comandos sospechosos conocidos
            suspicious_patterns = [
                'rm -rf',
                'sudo',
                'chmod 777',
                'passwd',
                'su -',
                'wget',
                'curl',
                'nc -l',
                'python -c',
                'eval',
                'exec'
            ]
            
            # Verificar comando
            if any(pattern in command.lower() for pattern in suspicious_patterns):
                return True
            
            # Verificar argumentos
            if args:
                for arg in args:
                    if any(pattern in arg.lower() for pattern in suspicious_patterns):
                        return True
            
            # Verificar patrones de inyección
            injection_patterns = [';', '|', '&', '`', '$', '$(', '${']
            full_command = f"{command} {' '.join(args or [])}"
            
            if any(pattern in full_command for pattern in injection_patterns):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando comando sospechoso: {e}")
            return True  # En caso de error, considerar sospechoso
    
    def _requires_confirmation(self, command: str) -> bool:
        """Verifica si un comando requiere confirmación"""
        try:
            if not self.require_confirmation:
                return False
            
            # Comandos críticos que requieren confirmación
            critical_commands = self.control_config.get('commands', {}).get('critical_commands', [])
            return command in critical_commands
            
        except Exception as e:
            logger.error(f"Error verificando confirmación requerida: {e}")
            return True  # En caso de error, requerir confirmación
    
    async def _log_security_event(self, 
                                user_id: str, 
                                chat_id: str, 
                                command: str, 
                                status: CommandStatus,
                                description: str, 
                                details: Dict[str, Any]):
        """Registra evento de seguridad"""
        try:
            event_id = f"security_event_{int(time.time())}"
            
            # Calcular score de riesgo
            risk_score = self._calculate_risk_score(status, command, details)
            
            # Crear evento de seguridad
            security_event = SecurityEvent(
                event_id=event_id,
                event_type="command_validation",
                user_id=user_id,
                chat_id=chat_id,
                command=command,
                status=status,
                timestamp=datetime.now(),
                details=details,
                risk_score=risk_score
            )
            
            # Agregar a historial
            self.suspicious_activities.append(security_event)
            
            # Registrar en auditoría
            audit_event_type = AuditEventType.SECURITY_VIOLATION if status != CommandStatus.ALLOWED else AuditEventType.DATA_ACCESS
            audit_severity = AuditSeverity.HIGH if status != CommandStatus.ALLOWED else AuditSeverity.LOW
            
            await self.audit_logger.log_event(
                audit_event_type,
                f"Evento de seguridad: {description}",
                {
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'command': command,
                    'status': status.value,
                    'risk_score': risk_score,
                    'details': details
                },
                user_id=user_id,
                severity=audit_severity
            )
            
            # Si es un evento de alta severidad, bloquear usuario temporalmente
            if risk_score > 0.8:
                await self._block_user_temporarily(user_id, 3600)  # 1 hora
            
        except Exception as e:
            logger.error(f"Error registrando evento de seguridad: {e}")
    
    def _calculate_risk_score(self, status: CommandStatus, command: str, details: Dict[str, Any]) -> float:
        """Calcula score de riesgo del evento"""
        try:
            base_score = 0.0
            
            # Score base por estado
            status_scores = {
                CommandStatus.ALLOWED: 0.0,
                CommandStatus.RATE_LIMITED: 0.3,
                CommandStatus.UNAUTHORIZED: 0.6,
                CommandStatus.SUSPICIOUS: 0.8,
                CommandStatus.BLOCKED: 1.0
            }
            
            base_score = status_scores.get(status, 0.5)
            
            # Ajustar por comando
            if command in ['/stop', '/restart', '/config']:
                base_score += 0.2
            
            # Ajustar por argumentos sospechosos
            if details.get('args'):
                for arg in details['args']:
                    if any(pattern in arg.lower() for pattern in ['rm', 'sudo', 'chmod', 'passwd']):
                        base_score += 0.3
            
            return min(1.0, base_score)
            
        except Exception as e:
            logger.error(f"Error calculando risk score: {e}")
            return 0.5
    
    async def _block_user_temporarily(self, user_id: str, duration_seconds: int):
        """Bloquea usuario temporalmente"""
        try:
            self.blocked_users.add(user_id)
            
            # Programar desbloqueo
            asyncio.create_task(self._unblock_user_after_delay(user_id, duration_seconds))
            
            logger.warning(f"Usuario {user_id} bloqueado temporalmente por {duration_seconds} segundos")
            
        except Exception as e:
            logger.error(f"Error bloqueando usuario temporalmente: {e}")
    
    async def _unblock_user_after_delay(self, user_id: str, delay_seconds: int):
        """Desbloquea usuario después de un delay"""
        try:
            await asyncio.sleep(delay_seconds)
            self.blocked_users.discard(user_id)
            logger.info(f"Usuario {user_id} desbloqueado")
            
        except Exception as e:
            logger.error(f"Error desbloqueando usuario: {e}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Obtiene estado de seguridad"""
        try:
            return {
                'authorized_chat_ids': list(self.authorized_chat_ids),
                'blocked_users': list(self.blocked_users),
                'rate_limits': {
                    user_id: {
                        'requests_count': info.requests_count,
                        'window_start': info.window_start.isoformat(),
                        'blocked_until': info.blocked_until.isoformat() if info.blocked_until else None
                    }
                    for user_id, info in self.rate_limits.items()
                },
                'suspicious_activities_count': len(self.suspicious_activities),
                'max_requests_per_minute': self.max_requests_per_minute,
                'max_requests_per_hour': self.max_requests_per_hour,
                'block_duration': self.block_duration
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de seguridad: {e}")
            return {'error': str(e)}
    
    def get_suspicious_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene actividades sospechosas"""
        try:
            recent_activities = self.suspicious_activities[-limit:]
            return [asdict(activity) for activity in recent_activities]
            
        except Exception as e:
            logger.error(f"Error obteniendo actividades sospechosas: {e}")
            return []
    
    async def unblock_user(self, user_id: str) -> bool:
        """Desbloquea un usuario"""
        try:
            self.blocked_users.discard(user_id)
            
            # Limpiar rate limit
            if user_id in self.rate_limits:
                self.rate_limits[user_id].blocked_until = None
                self.rate_limits[user_id].requests_count = 0
            
            logger.info(f"Usuario {user_id} desbloqueado manualmente")
            return True
            
        except Exception as e:
            logger.error(f"Error desbloqueando usuario: {e}")
            return False
    
    async def add_authorized_chat(self, chat_id: str) -> bool:
        """Añade chat autorizado"""
        try:
            self.authorized_chat_ids.add(chat_id)
            logger.info(f"Chat {chat_id} añadido a lista autorizada")
            return True
            
        except Exception as e:
            logger.error(f"Error añadiendo chat autorizado: {e}")
            return False
    
    async def remove_authorized_chat(self, chat_id: str) -> bool:
        """Remueve chat autorizado"""
        try:
            self.authorized_chat_ids.discard(chat_id)
            logger.info(f"Chat {chat_id} removido de lista autorizada")
            return True
            
        except Exception as e:
            logger.error(f"Error removiendo chat autorizado: {e}")
            return False
    
    async def cleanup(self):
        """Limpia recursos del guardián de seguridad"""
        try:
            # Limpiar rate limits antiguos
            current_time = datetime.now()
            self.rate_limits = {
                user_id: info for user_id, info in self.rate_limits.items()
                if not info.blocked_until or current_time < info.blocked_until
            }
            
            # Limpiar actividades sospechosas antiguas
            cutoff_time = current_time - timedelta(days=7)
            self.suspicious_activities = [
                activity for activity in self.suspicious_activities
                if activity.timestamp > cutoff_time
            ]
            
            logger.info("SecurityGuard limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando SecurityGuard: {e}")

# Instancia global
security_guard = SecurityGuard()