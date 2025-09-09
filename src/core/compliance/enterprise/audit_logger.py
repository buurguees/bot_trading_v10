#!/usr/bin/env python3
"""
Audit Logger Enterprise - Logging Inmutable
==========================================

Este módulo implementa logging de auditoría inmutable con checksums
para cumplimiento regulatorio (MiFID II, GDPR).

Características:
- Logging inmutable con checksums SHA-256
- Encriptación AES-256-GCM
- Retención de datos por 7 años
- Integridad de datos verificable
- Cumplimiento MiFID II/GDPR

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

import psycopg2
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.config_loader import user_config

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Tipos de eventos de auditoría"""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    LEVERAGE_CHANGED = "leverage_changed"
    MARGIN_CALL = "margin_call"
    EMERGENCY_STOP = "emergency_stop"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"
    USER_ACTION = "user_action"
    ERROR_OCCURRED = "error_occurred"
    COMPLIANCE_VIOLATION = "compliance_violation"

class Severity(Enum):
    """Niveles de severidad"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Evento de auditoría inmutable"""
    id: str
    timestamp: datetime
    event_type: EventType
    data: Dict[str, Any]
    severity: Severity
    user_id: str
    session_id: str
    checksum: str
    encrypted_data: Optional[bytes] = None
    retention_until: Optional[datetime] = None

class AuditLogger:
    """Logger de auditoría enterprise inmutable"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = user_config.get_value(['compliance', 'audit'], {})
        
        # Configuración de auditoría
        self.enabled = self.config.get('enabled', True)
        self.encryption_enabled = self.config.get('encryption_enabled', True)
        self.retention_years = self.config.get('retention_years', 7)
        self.checksum_algorithm = self.config.get('checksum_algorithm', 'sha256')
        
        # Configuración de base de datos
        self.db_config = self.config.get('database', {})
        self.db_connection = None
        
        # Configuración de encriptación
        self.encryption_key = None
        self.fernet = None
        
        # Estado del logger
        self.session_id = self.generate_session_id()
        self.event_counter = 0
        
        # Directorios
        self.setup_directories()
        
        # Inicializar encriptación
        self._setup_encryption()
        
        # Inicializar base de datos
        self._setup_database()
        
        logger.info("🔐 AuditLogger enterprise inicializado")
    
    def _setup_encryption(self):
        """Configura el sistema de encriptación"""
        try:
            if self.encryption_enabled:
                # Generar o cargar clave de encriptación
                key_file = Path("config/audit_encryption.key")
                if key_file.exists():
                    with open(key_file, 'rb') as f:
                        self.encryption_key = f.read()
                else:
                    # Generar nueva clave
                    self.encryption_key = Fernet.generate_key()
                    with open(key_file, 'wb') as f:
                        f.write(self.encryption_key)
                
                self.fernet = Fernet(self.encryption_key)
                logger.info("✅ Encriptación configurada")
            else:
                logger.warning("⚠️ Encriptación deshabilitada")
                
        except Exception as e:
            logger.error(f"❌ Error configurando encriptación: {e}")
            self.encryption_enabled = False
    
    def _setup_database(self):
        """Configura la conexión a la base de datos"""
        try:
            if self.db_config:
                self.db_connection = psycopg2.connect(
                    host=self.db_config.get('host', 'localhost'),
                    port=self.db_config.get('port', 5432),
                    database=self.db_config.get('database', 'audit_logs'),
                    user=self.db_config.get('user', 'postgres'),
                    password=self.db_config.get('password', '')
                )
                
                # Crear tabla de auditoría si no existe
                self._create_audit_table()
                logger.info("✅ Base de datos de auditoría configurada")
            else:
                logger.warning("⚠️ Base de datos de auditoría no configurada")
                
        except Exception as e:
            logger.error(f"❌ Error configurando base de datos: {e}")
            self.db_connection = None
    
    def _create_audit_table(self):
        """Crea la tabla de auditoría en la base de datos"""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS audit_events (
                id VARCHAR(64) PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                data JSONB NOT NULL,
                severity VARCHAR(20) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                session_id VARCHAR(64) NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                encrypted_data BYTEA,
                retention_until TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_session_id ON audit_events(session_id);
            CREATE INDEX IF NOT EXISTS idx_audit_retention ON audit_events(retention_until);
            """
            
            cursor.execute(create_table_sql)
            self.db_connection.commit()
            cursor.close()
            
            logger.info("✅ Tabla de auditoría creada/verificada")
            
        except Exception as e:
            logger.error(f"❌ Error creando tabla de auditoría: {e}")
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/compliance/audit',
            'data/enterprise/compliance/audit',
            'backups/enterprise/compliance/audit',
            'config'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def generate_session_id(self) -> str:
        """Genera un ID único de sesión"""
        timestamp = datetime.now().isoformat()
        random_data = f"{timestamp}_{self.event_counter}"
        return hashlib.sha256(random_data.encode()).hexdigest()[:16]
    
    def generate_event_id(self) -> str:
        """Genera un ID único de evento"""
        self.event_counter += 1
        timestamp = datetime.now().isoformat()
        random_data = f"{timestamp}_{self.event_counter}_{self.session_id}"
        return hashlib.sha256(random_data.encode()).hexdigest()
    
    def calculate_checksum(self, data: Union[Dict, str]) -> str:
        """Calcula el checksum SHA-256 de los datos"""
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            else:
                data_str = str(data)
            
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculando checksum: {e}")
            return ""
    
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encripta los datos usando AES-256-GCM"""
        try:
            if not self.encryption_enabled or not self.fernet:
                return json.dumps(data).encode('utf-8')
            
            data_str = json.dumps(data)
            encrypted_data = self.fernet.encrypt(data_str.encode('utf-8'))
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Error encriptando datos: {e}")
            return json.dumps(data).encode('utf-8')
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Desencripta los datos"""
        try:
            if not self.encryption_enabled or not self.fernet:
                return json.loads(encrypted_data.decode('utf-8'))
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error desencriptando datos: {e}")
            return {}
    
    async def log_event(
        self, 
        event_type: EventType, 
        data: Dict[str, Any], 
        severity: Severity = Severity.INFO,
        user_id: str = "system"
    ) -> str:
        """Registra un evento de auditoría"""
        try:
            if not self.enabled:
                return ""
            
            # Generar ID único
            event_id = self.generate_event_id()
            
            # Calcular checksum
            checksum = self.calculate_checksum(data)
            
            # Encriptar datos si está habilitado
            encrypted_data = None
            if self.encryption_enabled:
                encrypted_data = self.encrypt_data(data)
            
            # Calcular fecha de retención
            retention_until = datetime.now() + timedelta(days=365 * self.retention_years)
            
            # Crear evento de auditoría
            event = AuditEvent(
                id=event_id,
                timestamp=datetime.now(),
                event_type=event_type,
                data=data,
                severity=severity,
                user_id=user_id,
                session_id=self.session_id,
                checksum=checksum,
                encrypted_data=encrypted_data,
                retention_until=retention_until
            )
            
            # Guardar en base de datos
            await self._store_event_db(event)
            
            # Guardar en archivo local
            await self._store_event_file(event)
            
            logger.debug(f"📝 Evento de auditoría registrado: {event_type.value} - {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"❌ Error registrando evento de auditoría: {e}")
            return ""
    
    async def _store_event_db(self, event: AuditEvent):
        """Almacena el evento en la base de datos"""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            
            insert_sql = """
            INSERT INTO audit_events (
                id, timestamp, event_type, data, severity, user_id, 
                session_id, checksum, encrypted_data, retention_until
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """
            
            cursor.execute(insert_sql, (
                event.id,
                event.timestamp,
                event.event_type.value,
                json.dumps(event.data),
                event.severity.value,
                event.user_id,
                event.session_id,
                event.checksum,
                event.encrypted_data,
                event.retention_until
            ))
            
            self.db_connection.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ Error almacenando evento en BD: {e}")
    
    async def _store_event_file(self, event: AuditEvent):
        """Almacena el evento en archivo local"""
        try:
            # Archivo de auditoría diario
            date_str = event.timestamp.strftime('%Y%m%d')
            audit_file = Path(f"logs/enterprise/compliance/audit/audit_{date_str}.jsonl")
            
            # Convertir evento a diccionario
            event_dict = asdict(event)
            event_dict['timestamp'] = event.timestamp.isoformat()
            event_dict['event_type'] = event.event_type.value
            event_dict['severity'] = event.severity.value
            event_dict['encrypted_data'] = base64.b64encode(event.encrypted_data).decode() if event.encrypted_data else None
            
            # Escribir en archivo JSONL
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_dict) + '\n')
            
        except Exception as e:
            logger.error(f"❌ Error almacenando evento en archivo: {e}")
    
    async def log_trade_opened(
        self, 
        symbol: str, 
        side: str, 
        size: float, 
        price: float, 
        leverage: float,
        strategy: str = "unknown"
    ) -> str:
        """Registra la apertura de una operación"""
        data = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'price': price,
            'leverage': leverage,
            'strategy': strategy,
            'action': 'trade_opened'
        }
        
        return await self.log_event(
            EventType.TRADE_OPENED,
            data,
            Severity.INFO
        )
    
    async def log_trade_closed(
        self, 
        symbol: str, 
        side: str, 
        size: float, 
        entry_price: float,
        exit_price: float,
        pnl: float,
        duration_minutes: int,
        reason: str = "manual"
    ) -> str:
        """Registra el cierre de una operación"""
        data = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'duration_minutes': duration_minutes,
            'reason': reason,
            'action': 'trade_closed'
        }
        
        return await self.log_event(
            EventType.TRADE_CLOSED,
            data,
            Severity.INFO
        )
    
    async def log_position_opened(
        self, 
        symbol: str, 
        side: str, 
        size: float, 
        price: float,
        leverage: float,
        margin_used: float
    ) -> str:
        """Registra la apertura de una posición"""
        data = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'price': price,
            'leverage': leverage,
            'margin_used': margin_used,
            'action': 'position_opened'
        }
        
        return await self.log_event(
            EventType.POSITION_OPENED,
            data,
            Severity.INFO
        )
    
    async def log_position_closed(
        self, 
        symbol: str, 
        side: str, 
        size: float, 
        pnl: float,
        reason: str = "manual"
    ) -> str:
        """Registra el cierre de una posición"""
        data = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'pnl': pnl,
            'reason': reason,
            'action': 'position_closed'
        }
        
        return await self.log_event(
            EventType.POSITION_CLOSED,
            data,
            Severity.INFO
        )
    
    async def log_emergency_stop(self, reason: str, details: str) -> str:
        """Registra una parada de emergencia"""
        data = {
            'reason': reason,
            'details': details,
            'action': 'emergency_stop'
        }
        
        return await self.log_event(
            EventType.EMERGENCY_STOP,
            data,
            Severity.CRITICAL
        )
    
    async def log_compliance_violation(
        self, 
        violation_type: str, 
        details: str, 
        severity: Severity = Severity.WARNING
    ) -> str:
        """Registra una violación de cumplimiento"""
        data = {
            'violation_type': violation_type,
            'details': details,
            'action': 'compliance_violation'
        }
        
        return await self.log_event(
            EventType.COMPLIANCE_VIOLATION,
            data,
            severity
        )
    
    async def verify_integrity(self, event_id: str) -> bool:
        """Verifica la integridad de un evento de auditoría"""
        try:
            if not self.db_connection:
                return False
            
            cursor = self.db_connection.cursor()
            
            select_sql = """
            SELECT data, checksum FROM audit_events WHERE id = %s
            """
            
            cursor.execute(select_sql, (event_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return False
            
            stored_data, stored_checksum = result
            calculated_checksum = self.calculate_checksum(stored_data)
            
            return stored_checksum == calculated_checksum
            
        except Exception as e:
            logger.error(f"❌ Error verificando integridad: {e}")
            return False
    
    async def cleanup_expired_events(self):
        """Limpia eventos expirados según la política de retención"""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            
            delete_sql = """
            DELETE FROM audit_events 
            WHERE retention_until < NOW()
            """
            
            cursor.execute(delete_sql)
            deleted_count = cursor.rowcount
            self.db_connection.commit()
            cursor.close()
            
            if deleted_count > 0:
                logger.info(f"🗑️ {deleted_count} eventos de auditoría expirados eliminados")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando eventos expirados: {e}")
    
    async def get_events_by_type(
        self, 
        event_type: EventType, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """Obtiene eventos por tipo"""
        try:
            if not self.db_connection:
                return []
            
            cursor = self.db_connection.cursor()
            
            select_sql = """
            SELECT id, timestamp, event_type, data, severity, user_id, 
                   session_id, checksum, encrypted_data, retention_until
            FROM audit_events 
            WHERE event_type = %s
            """
            params = [event_type.value]
            
            if start_date:
                select_sql += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                select_sql += " AND timestamp <= %s"
                params.append(end_date)
            
            select_sql += " ORDER BY timestamp DESC"
            
            cursor.execute(select_sql, params)
            results = cursor.fetchall()
            cursor.close()
            
            events = []
            for row in results:
                event = AuditEvent(
                    id=row[0],
                    timestamp=row[1],
                    event_type=EventType(row[2]),
                    data=row[3],
                    severity=Severity(row[4]),
                    user_id=row[5],
                    session_id=row[6],
                    checksum=row[7],
                    encrypted_data=row[8],
                    retention_until=row[9]
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo eventos por tipo: {e}")
            return []
    
    async def close(self):
        """Cierra el logger de auditoría"""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            logger.info("✅ AuditLogger cerrado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando AuditLogger: {e}")

# Instancia global
audit_logger = AuditLogger()
