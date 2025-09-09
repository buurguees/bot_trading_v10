#!/usr/bin/env python3
"""
Gestor de Recuperación Enterprise - Sistema de Backup y Restauración
====================================================================

Este módulo automatiza la recuperación del sistema desde backups,
asegurando cumplimiento con retención de 7 años y recuperación rápida.

Características:
- Restauración automática desde backups
- Validación de integridad de datos
- Cumplimiento de retención (7 años)
- Recuperación granular (datos, modelos, configuraciones)
- Verificación de consistencia
- Logging detallado de operaciones

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import shutil
import json
import hashlib
import boto3
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import yaml
import zipfile
import tarfile

logger = logging.getLogger(__name__)

class RecoveryStatus(Enum):
    """Estados de recuperación"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"

@dataclass
class BackupInfo:
    """Información de un backup"""
    backup_id: str
    timestamp: datetime
    size_bytes: int
    type: str  # 'full', 'incremental', 'differential'
    components: List[str]  # ['data', 'models', 'configs', 'logs']
    checksum: str
    status: str
    retention_until: datetime

@dataclass
class RecoveryOperation:
    """Operación de recuperación"""
    operation_id: str
    backup_id: str
    target_components: List[str]
    status: RecoveryStatus
    start_time: datetime
    end_time: Optional[datetime]
    error_message: Optional[str]
    restored_files: List[str]
    validation_results: Dict[str, bool]

class RecoveryManager:
    """Gestor de recuperación del sistema enterprise"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Configuración de backup y recuperación
        self.backup_config = self.config.get('backup_recovery', {})
        self.backup_paths = self.backup_config.get('backup_paths', {})
        self.retention_days = self.backup_config.get('retention_days', 2555)  # 7 años
        
        # Configuración de AWS S3
        self.s3_config = self.backup_config.get('s3', {})
        self.bucket_name = self.s3_config.get('bucket_name', 'trading-bot-backups')
        self.region = self.s3_config.get('region', 'us-east-1')
        
        # Configuración de base de datos
        self.db_config = self.config.get('database', {})
        
        # Directorios de trabajo
        self.backup_dir = Path(self.backup_paths.get('data', 'backups/data'))
        self.temp_dir = Path(self.backup_paths.get('temp', 'backups/temp'))
        self.logs_dir = Path('logs/enterprise/recovery')
        
        # Crear directorios necesarios
        self._create_directories()
        
        # Cliente S3
        self.s3_client = None
        self._init_s3_client()
        
        # Configurar logging
        self.setup_logging()
        
        # Estado de operaciones
        self.active_operations: Dict[str, RecoveryOperation] = {}
        
        logger.info("🔄 RecoveryManager enterprise inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración del sistema"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            return {}
    
    def _create_directories(self):
        """Crea los directorios necesarios"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"❌ Error creando directorios: {e}")
    
    def _init_s3_client(self):
        """Inicializa el cliente de S3"""
        try:
            if self.s3_config.get('enabled', False):
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=self.s3_config.get('access_key'),
                    aws_secret_access_key=self.s3_config.get('secret_key')
                )
                logger.info("✅ Cliente S3 inicializado")
            else:
                logger.info("ℹ️ S3 deshabilitado - usando almacenamiento local")
        except Exception as e:
            logger.error(f"❌ Error inicializando S3: {e}")
            self.s3_client = None
    
    def setup_logging(self):
        """Configura el logging para recuperación"""
        log_file = self.logs_dir / 'recovery_manager.log'
        
        # Configurar logger específico para recuperación
        recovery_logger = logging.getLogger('recovery_manager')
        recovery_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        recovery_logger.addHandler(file_handler)
    
    async def list_available_backups(self) -> Dict[str, Any]:
        """Lista todos los backups disponibles"""
        try:
            logger.info("📋 Listando backups disponibles...")
            
            backups = []
            
            # Listar backups locales
            local_backups = await self._list_local_backups()
            backups.extend(local_backups)
            
            # Listar backups de S3
            if self.s3_client:
                s3_backups = await self._list_s3_backups()
                backups.extend(s3_backups)
            
            # Ordenar por timestamp
            backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Filtrar por retención
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            valid_backups = [b for b in backups if b['timestamp'] >= cutoff_date]
            
            logger.info(f"✅ Encontrados {len(valid_backups)} backups válidos")
            
            return {
                'success': True,
                'backups': valid_backups,
                'total_count': len(valid_backups),
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"❌ Error listando backups: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _list_local_backups(self) -> List[Dict[str, Any]]:
        """Lista backups locales"""
        backups = []
        
        try:
            for backup_path in self.backup_dir.iterdir():
                if backup_path.is_dir() and backup_path.name.startswith('backup_'):
                    backup_info = await self._get_backup_info(backup_path)
                    if backup_info:
                        backups.append(backup_info)
        except Exception as e:
            logger.error(f"❌ Error listando backups locales: {e}")
        
        return backups
    
    async def _list_s3_backups(self) -> List[Dict[str, Any]]:
        """Lista backups de S3"""
        backups = []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            backup_ids = set()
            for obj in response.get('Contents', []):
                key_parts = obj['Key'].split('/')
                if len(key_parts) >= 2:
                    backup_id = key_parts[1]
                    if backup_id not in backup_ids:
                        backup_ids.add(backup_id)
                        
                        # Obtener metadatos del backup
                        try:
                            metadata_response = self.s3_client.head_object(
                                Bucket=self.bucket_name,
                                Key=f"backups/{backup_id}/metadata.json"
                            )
                            
                            backup_info = {
                                'backup_id': backup_id,
                                'timestamp': obj['LastModified'],
                                'size_bytes': obj['Size'],
                                'type': 's3',
                                'components': ['data', 'models', 'configs'],
                                'checksum': metadata_response.get('Metadata', {}).get('checksum', ''),
                                'status': 'available',
                                'retention_until': obj['LastModified'] + timedelta(days=self.retention_days)
                            }
                            backups.append(backup_info)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error obteniendo metadatos para backup {backup_id}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error listando backups de S3: {e}")
        
        return backups
    
    async def _get_backup_info(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """Obtiene información de un backup local"""
        try:
            metadata_file = backup_path / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                return {
                    'backup_id': backup_path.name,
                    'timestamp': datetime.fromisoformat(metadata.get('timestamp', '')),
                    'size_bytes': sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()),
                    'type': metadata.get('type', 'full'),
                    'components': metadata.get('components', []),
                    'checksum': metadata.get('checksum', ''),
                    'status': 'available',
                    'retention_until': datetime.fromisoformat(metadata.get('timestamp', '')) + timedelta(days=self.retention_days)
                }
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo info de backup {backup_path}: {e}")
        
        return None
    
    async def restore_from_backup(self, backup_id: str, components: Optional[List[str]] = None) -> Dict[str, Any]:
        """Restaura el sistema desde un backup específico"""
        try:
            logger.info(f"🔄 Iniciando restauración desde backup: {backup_id}")
            
            # Crear operación de recuperación
            operation_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            operation = RecoveryOperation(
                operation_id=operation_id,
                backup_id=backup_id,
                target_components=components or ['data', 'models', 'configs'],
                status=RecoveryStatus.PENDING,
                start_time=datetime.now(),
                end_time=None,
                error_message=None,
                restored_files=[],
                validation_results={}
            )
            
            self.active_operations[operation_id] = operation
            
            try:
                # Actualizar estado
                operation.status = RecoveryStatus.IN_PROGRESS
                
                # Verificar que el backup existe
                backup_info = await self._find_backup(backup_id)
                if not backup_info:
                    raise Exception(f"Backup {backup_id} no encontrado")
                
                # Crear directorio temporal para restauración
                temp_restore_dir = self.temp_dir / f"restore_{operation_id}"
                temp_restore_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Descargar backup
                    await self._download_backup(backup_id, temp_restore_dir)
                    
                    # Validar integridad
                    validation_result = await self._validate_backup_integrity(temp_restore_dir, backup_info)
                    if not validation_result['valid']:
                        raise Exception(f"Backup corrupto: {validation_result['error']}")
                    
                    # Restaurar componentes
                    restored_files = []
                    for component in operation.target_components:
                        if component in backup_info['components']:
                            component_files = await self._restore_component(
                                component, temp_restore_dir, operation_id
                            )
                            restored_files.extend(component_files)
                            operation.validation_results[component] = True
                        else:
                            logger.warning(f"⚠️ Componente {component} no disponible en backup")
                            operation.validation_results[component] = False
                    
                    operation.restored_files = restored_files
                    operation.status = RecoveryStatus.COMPLETED
                    operation.end_time = datetime.now()
                    
                    logger.info(f"✅ Restauración completada: {len(restored_files)} archivos restaurados")
                    
                    return {
                        'success': True,
                        'operation_id': operation_id,
                        'backup_id': backup_id,
                        'restored_files': len(restored_files),
                        'components': operation.target_components,
                        'duration_seconds': (operation.end_time - operation.start_time).total_seconds()
                    }
                
                finally:
                    # Limpiar directorio temporal
                    shutil.rmtree(temp_restore_dir, ignore_errors=True)
            
            except Exception as e:
                operation.status = RecoveryStatus.FAILED
                operation.end_time = datetime.now()
                operation.error_message = str(e)
                logger.error(f"❌ Error en restauración: {e}")
                
                return {
                    'success': False,
                    'operation_id': operation_id,
                    'error': str(e)
                }
            
        except Exception as e:
            logger.error(f"❌ Error iniciando restauración: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _find_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Busca un backup específico"""
        try:
            # Buscar localmente
            local_backup = self.backup_dir / f"backup_{backup_id}"
            if local_backup.exists():
                return await self._get_backup_info(local_backup)
            
            # Buscar en S3
            if self.s3_client:
                try:
                    response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=f"backups/{backup_id}/metadata.json"
                    )
                    
                    return {
                        'backup_id': backup_id,
                        'timestamp': response['LastModified'],
                        'type': 's3',
                        'components': ['data', 'models', 'configs'],
                        'checksum': response.get('Metadata', {}).get('checksum', ''),
                        'status': 'available'
                    }
                except Exception:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error buscando backup {backup_id}: {e}")
            return None
    
    async def _download_backup(self, backup_id: str, target_dir: Path):
        """Descarga un backup desde S3 o copia localmente"""
        try:
            # Intentar descargar desde S3 primero
            if self.s3_client:
                try:
                    await self._download_from_s3(backup_id, target_dir)
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Error descargando desde S3: {e}")
            
            # Fallback a backup local
            local_backup = self.backup_dir / f"backup_{backup_id}"
            if local_backup.exists():
                shutil.copytree(local_backup, target_dir / backup_id)
            else:
                raise Exception(f"Backup {backup_id} no encontrado localmente ni en S3")
                
        except Exception as e:
            logger.error(f"❌ Error descargando backup: {e}")
            raise
    
    async def _download_from_s3(self, backup_id: str, target_dir: Path):
        """Descarga un backup desde S3"""
        try:
            # Listar objetos del backup
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"backups/{backup_id}/"
            )
            
            for obj in response.get('Contents', []):
                key = obj['Key']
                relative_path = key.replace(f"backups/{backup_id}/", "")
                
                if relative_path:  # Ignorar el directorio raíz
                    file_path = target_dir / relative_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    self.s3_client.download_file(
                        self.bucket_name,
                        key,
                        str(file_path)
                    )
            
        except Exception as e:
            logger.error(f"❌ Error descargando desde S3: {e}")
            raise
    
    async def _validate_backup_integrity(self, backup_dir: Path, backup_info: Dict[str, Any]) -> Dict[str, Any]:
        """Valida la integridad de un backup"""
        try:
            # Verificar archivos esenciales
            essential_files = ['metadata.json']
            for file_name in essential_files:
                if not (backup_dir / file_name).exists():
                    return {'valid': False, 'error': f'Archivo esencial faltante: {file_name}'}
            
            # Verificar checksum si está disponible
            if backup_info.get('checksum'):
                calculated_checksum = await self._calculate_backup_checksum(backup_dir)
                if calculated_checksum != backup_info['checksum']:
                    return {'valid': False, 'error': 'Checksum no coincide'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            logger.error(f"❌ Error validando integridad: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def _calculate_backup_checksum(self, backup_dir: Path) -> str:
        """Calcula el checksum de un backup"""
        try:
            hasher = hashlib.sha256()
            
            for file_path in sorted(backup_dir.rglob('*')):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"❌ Error calculando checksum: {e}")
            return ""
    
    async def _restore_component(self, component: str, backup_dir: Path, operation_id: str) -> List[str]:
        """Restaura un componente específico"""
        try:
            restored_files = []
            
            if component == 'data':
                # Restaurar datos de TimescaleDB
                restored_files.extend(await self._restore_database_data(backup_dir))
            
            elif component == 'models':
                # Restaurar modelos ML
                restored_files.extend(await self._restore_models(backup_dir))
            
            elif component == 'configs':
                # Restaurar configuraciones
                restored_files.extend(await self._restore_configs(backup_dir))
            
            elif component == 'logs':
                # Restaurar logs
                restored_files.extend(await self._restore_logs(backup_dir))
            
            return restored_files
            
        except Exception as e:
            logger.error(f"❌ Error restaurando componente {component}: {e}")
            return []
    
    async def _restore_database_data(self, backup_dir: Path) -> List[str]:
        """Restaura datos de la base de datos"""
        try:
            restored_files = []
            
            # Buscar archivos de dump de la base de datos
            db_dump_files = list(backup_dir.glob('**/database_*.sql'))
            
            for dump_file in db_dump_files:
                try:
                    # Restaurar desde dump
                    await self._restore_database_dump(dump_file)
                    restored_files.append(str(dump_file))
                    logger.info(f"✅ Datos de BD restaurados desde: {dump_file.name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error restaurando dump {dump_file}: {e}")
            
            return restored_files
            
        except Exception as e:
            logger.error(f"❌ Error restaurando datos de BD: {e}")
            return []
    
    async def _restore_database_dump(self, dump_file: Path):
        """Restaura un dump de base de datos"""
        try:
            # Conectar a la base de datos
            conn = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database', 'trading_bot'),
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password', '')
            )
            
            try:
                with conn.cursor() as cur:
                    # Ejecutar dump
                    with open(dump_file, 'r') as f:
                        cur.execute(f.read())
                    conn.commit()
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"❌ Error restaurando dump de BD: {e}")
            raise
    
    async def _restore_models(self, backup_dir: Path) -> List[str]:
        """Restaura modelos ML"""
        try:
            restored_files = []
            
            # Buscar directorio de modelos
            models_dir = backup_dir / 'models'
            if models_dir.exists():
                target_models_dir = Path('models')
                target_models_dir.mkdir(parents=True, exist_ok=True)
                
                # Copiar modelos
                for model_file in models_dir.rglob('*'):
                    if model_file.is_file():
                        relative_path = model_file.relative_to(models_dir)
                        target_path = target_models_dir / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(model_file, target_path)
                        restored_files.append(str(target_path))
                
                logger.info(f"✅ {len(restored_files)} modelos restaurados")
            
            return restored_files
            
        except Exception as e:
            logger.error(f"❌ Error restaurando modelos: {e}")
            return []
    
    async def _restore_configs(self, backup_dir: Path) -> List[str]:
        """Restaura configuraciones"""
        try:
            restored_files = []
            
            # Buscar directorio de configuraciones
            configs_dir = backup_dir / 'configs'
            if configs_dir.exists():
                target_configs_dir = Path('config')
                target_configs_dir.mkdir(parents=True, exist_ok=True)
                
                # Copiar configuraciones
                for config_file in configs_dir.rglob('*'):
                    if config_file.is_file():
                        relative_path = config_file.relative_to(configs_dir)
                        target_path = target_configs_dir / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(config_file, target_path)
                        restored_files.append(str(target_path))
                
                logger.info(f"✅ {len(restored_files)} configuraciones restauradas")
            
            return restored_files
            
        except Exception as e:
            logger.error(f"❌ Error restaurando configuraciones: {e}")
            return []
    
    async def _restore_logs(self, backup_dir: Path) -> List[str]:
        """Restaura logs"""
        try:
            restored_files = []
            
            # Buscar directorio de logs
            logs_dir = backup_dir / 'logs'
            if logs_dir.exists():
                target_logs_dir = Path('logs')
                target_logs_dir.mkdir(parents=True, exist_ok=True)
                
                # Copiar logs
                for log_file in logs_dir.rglob('*'):
                    if log_file.is_file():
                        relative_path = log_file.relative_to(logs_dir)
                        target_path = target_logs_dir / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(log_file, target_path)
                        restored_files.append(str(target_path))
                
                logger.info(f"✅ {len(restored_files)} logs restaurados")
            
            return restored_files
            
        except Exception as e:
            logger.error(f"❌ Error restaurando logs: {e}")
            return []
    
    async def get_recovery_status(self, operation_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una operación de recuperación"""
        try:
            if operation_id not in self.active_operations:
                return {'success': False, 'error': 'Operación no encontrada'}
            
            operation = self.active_operations[operation_id]
            
            return {
                'success': True,
                'operation_id': operation_id,
                'backup_id': operation.backup_id,
                'status': operation.status.value,
                'start_time': operation.start_time.isoformat(),
                'end_time': operation.end_time.isoformat() if operation.end_time else None,
                'duration_seconds': (operation.end_time - operation.start_time).total_seconds() if operation.end_time else None,
                'target_components': operation.target_components,
                'restored_files_count': len(operation.restored_files),
                'validation_results': operation.validation_results,
                'error_message': operation.error_message
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de recuperación: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cleanup_old_backups(self) -> Dict[str, Any]:
        """Limpia backups antiguos según la política de retención"""
        try:
            logger.info("🧹 Limpiando backups antiguos...")
            
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cleaned_count = 0
            
            # Limpiar backups locales
            for backup_path in self.backup_dir.iterdir():
                if backup_path.is_dir() and backup_path.name.startswith('backup_'):
                    backup_info = await self._get_backup_info(backup_path)
                    if backup_info and backup_info['timestamp'] < cutoff_date:
                        shutil.rmtree(backup_path, ignore_errors=True)
                        cleaned_count += 1
                        logger.info(f"🗑️ Backup local eliminado: {backup_path.name}")
            
            # Limpiar backups de S3
            if self.s3_client:
                s3_cleaned = await self._cleanup_s3_backups(cutoff_date)
                cleaned_count += s3_cleaned
            
            logger.info(f"✅ {cleaned_count} backups antiguos eliminados")
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'retention_days': self.retention_days
            }
            
        except Exception as e:
            logger.error(f"❌ Error limpiando backups: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _cleanup_s3_backups(self, cutoff_date: datetime) -> int:
        """Limpia backups antiguos de S3"""
        try:
            cleaned_count = 0
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            backup_ids = set()
            for obj in response.get('Contents', []):
                key_parts = obj['Key'].split('/')
                if len(key_parts) >= 2:
                    backup_id = key_parts[1]
                    if backup_id not in backup_ids and obj['LastModified'] < cutoff_date:
                        backup_ids.add(backup_id)
                        
                        # Eliminar todos los objetos del backup
                        objects_to_delete = []
                        for obj2 in response.get('Contents', []):
                            if obj2['Key'].startswith(f"backups/{backup_id}/"):
                                objects_to_delete.append({'Key': obj2['Key']})
                        
                        if objects_to_delete:
                            self.s3_client.delete_objects(
                                Bucket=self.bucket_name,
                                Delete={'Objects': objects_to_delete}
                            )
                            cleaned_count += 1
                            logger.info(f"🗑️ Backup S3 eliminado: {backup_id}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Error limpiando backups de S3: {e}")
            return 0

# Instancia global
recovery_manager = RecoveryManager('config/user_settings.yaml')
