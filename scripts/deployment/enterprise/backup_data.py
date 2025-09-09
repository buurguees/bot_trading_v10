# Ruta: scripts/deployment/enterprise/backup_data.py
# backup_data.py - Script de backup de datos enterprise
# Ubicación: C:\TradingBot_v10\scripts\enterprise\backup_data.py

import os
import sys
import json
import logging
import subprocess
import tarfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.config.enterprise_config import get_enterprise_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataBackupManager:
    """Gestor de backup de datos enterprise"""
    
    def __init__(self):
        """Inicializar el gestor de backup"""
        self.config = get_enterprise_config()
        self.infrastructure_config = self.config.get_infrastructure_config()
        
        # Configuración de backup
        self.storage_config = self.infrastructure_config.get("storage", {})
        self.backup_config = self.storage_config.get("backup", {})
        
        # Paths de backup
        self.backup_path = self.backup_config.get("path_template", "backups/enterprise/{date}/backup_{timestamp}.tar.gz")
        self.retention_days = self.backup_config.get("retention_days", 30)
        self.compression = self.backup_config.get("compression", True)
        
        # Directorios a respaldar
        self.backup_directories = [
            "data/realtime",
            "logs/enterprise",
            "config/enterprise",
            "security/keys",
            "models/saved_models",
            "checkpoints"
        ]
        
        # Archivos de configuración importantes
        self.important_files = [
            "config/enterprise_config.py",
            "docker/docker-compose.enterprise.yml",
            "requirements-enterprise.txt",
            "README_ENTERPRISE.md"
        ]
        
        logger.info("DataBackupManager inicializado")
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Crear backup completo"""
        try:
            logger.info("=== INICIANDO BACKUP DE DATOS ===")
            
            # Generar nombre de backup
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"
            
            # Crear directorio de backup
            backup_dir = self._create_backup_directory(backup_name)
            
            # Respaldar directorios
            self._backup_directories(backup_dir)
            
            # Respaldar archivos importantes
            self._backup_important_files(backup_dir)
            
            # Respaldar base de datos
            self._backup_database(backup_dir)
            
            # Respaldar configuración de Docker
            self._backup_docker_data(backup_dir)
            
            # Crear archivo de metadatos
            self._create_backup_metadata(backup_dir, backup_name)
            
            # Comprimir backup
            backup_file = self._compress_backup(backup_dir, backup_name)
            
            # Limpiar directorio temporal
            shutil.rmtree(backup_dir)
            
            logger.info(f"Backup creado exitosamente: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            raise
    
    def restore_backup(self, backup_file: str, target_dir: str = ".") -> bool:
        """Restaurar backup"""
        try:
            logger.info(f"=== RESTAURANDO BACKUP: {backup_file} ===")
            
            # Verificar que el archivo de backup existe
            if not Path(backup_file).exists():
                logger.error(f"Archivo de backup no encontrado: {backup_file}")
                return False
            
            # Crear directorio temporal para extracción
            temp_dir = Path("temp/backup_restore")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Extraer backup
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(temp_dir)
            
            # Restaurar archivos
            self._restore_files(temp_dir, target_dir)
            
            # Limpiar directorio temporal
            shutil.rmtree(temp_dir)
            
            logger.info("Backup restaurado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error restaurando backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Listar backups disponibles"""
        try:
            backups = []
            backup_base_dir = Path("backups/enterprise")
            
            if not backup_base_dir.exists():
                return backups
            
            # Buscar archivos de backup
            for backup_file in backup_base_dir.rglob("*.tar.gz"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Error obteniendo información de {backup_file}: {e}")
            
            # Ordenar por fecha de creación (más reciente primero)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listando backups: {e}")
            return []
    
    def cleanup_old_backups(self) -> int:
        """Limpiar backups antiguos"""
        try:
            logger.info("Limpiando backups antiguos...")
            
            backups = self.list_backups()
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0
            
            for backup in backups:
                backup_date = datetime.fromisoformat(backup["created"])
                
                if backup_date < cutoff_date:
                    try:
                        Path(backup["path"]).unlink()
                        deleted_count += 1
                        logger.info(f"Backup eliminado: {backup['filename']}")
                    except Exception as e:
                        logger.warning(f"Error eliminando backup {backup['filename']}: {e}")
            
            logger.info(f"Backups antiguos eliminados: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error limpiando backups antiguos: {e}")
            return 0
    
    def _create_backup_directory(self, backup_name: str) -> Path:
        """Crear directorio de backup"""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            backup_dir = Path(f"temp/backup_{backup_name}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Directorio de backup creado: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            logger.error(f"Error creando directorio de backup: {e}")
            raise
    
    def _backup_directories(self, backup_dir: Path):
        """Respaldar directorios"""
        try:
            logger.info("Respaldando directorios...")
            
            for directory in self.backup_directories:
                source_dir = Path(directory)
                
                if source_dir.exists():
                    dest_dir = backup_dir / directory
                    dest_dir.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copytree(source_dir, dest_dir)
                    logger.info(f"✓ Directorio respaldado: {directory}")
                else:
                    logger.warning(f"Directorio no encontrado: {directory}")
            
        except Exception as e:
            logger.error(f"Error respaldando directorios: {e}")
            raise
    
    def _backup_important_files(self, backup_dir: Path):
        """Respaldar archivos importantes"""
        try:
            logger.info("Respaldando archivos importantes...")
            
            for file_path in self.important_files:
                source_file = Path(file_path)
                
                if source_file.exists():
                    dest_file = backup_dir / file_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"✓ Archivo respaldado: {file_path}")
                else:
                    logger.warning(f"Archivo no encontrado: {file_path}")
            
        except Exception as e:
            logger.error(f"Error respaldando archivos importantes: {e}")
            raise
    
    def _backup_database(self, backup_dir: Path):
        """Respaldar base de datos"""
        try:
            logger.info("Respaldando base de datos...")
            
            # Crear directorio de base de datos
            db_dir = backup_dir / "database"
            db_dir.mkdir(exist_ok=True)
            
            # Crear dump de TimescaleDB
            dump_file = db_dir / "trading_bot_enterprise.sql"
            
            cmd = [
                "docker", "exec", "trading_bot_timescaledb",
                "pg_dump", "-U", "trading_bot", "-d", "trading_bot_enterprise"
            ]
            
            with open(dump_file, "w") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minutos
                )
            
            if result.returncode == 0:
                logger.info("✓ Base de datos respaldada")
            else:
                logger.error(f"Error respaldando base de datos: {result.stderr}")
            
        except Exception as e:
            logger.error(f"Error respaldando base de datos: {e}")
    
    def _backup_docker_data(self, backup_dir: Path):
        """Respaldar datos de Docker"""
        try:
            logger.info("Respaldando datos de Docker...")
            
            # Crear directorio de Docker
            docker_dir = backup_dir / "docker"
            docker_dir.mkdir(exist_ok=True)
            
            # Respaldar volúmenes de Docker
            volumes = [
                "trading_bot_kafka_data",
                "trading_bot_redis_data",
                "trading_bot_timescaledb_data",
                "trading_bot_prometheus_data",
                "trading_bot_grafana_data"
            ]
            
            for volume in volumes:
                try:
                    # Crear backup del volumen
                    volume_backup = docker_dir / f"{volume}.tar"
                    
                    cmd = [
                        "docker", "run", "--rm",
                        "-v", f"{volume}:/data",
                        "-v", f"{docker_dir.absolute()}:/backup",
                        "alpine:latest",
                        "tar", "cf", f"/backup/{volume}.tar", "-C", "/data", "."
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"✓ Volumen respaldado: {volume}")
                    else:
                        logger.warning(f"Error respaldando volumen {volume}: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Error respaldando volumen {volume}: {e}")
            
        except Exception as e:
            logger.error(f"Error respaldando datos de Docker: {e}")
    
    def _create_backup_metadata(self, backup_dir: Path, backup_name: str):
        """Crear metadatos del backup"""
        try:
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "directories": self.backup_directories,
                "important_files": self.important_files,
                "retention_days": self.retention_days,
                "compression": self.compression,
                "system_info": {
                    "platform": sys.platform,
                    "python_version": sys.version,
                    "working_directory": str(Path.cwd())
                }
            }
            
            metadata_file = backup_dir / "backup_metadata.json"
            
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info("✓ Metadatos del backup creados")
            
        except Exception as e:
            logger.error(f"Error creando metadatos del backup: {e}")
    
    def _compress_backup(self, backup_dir: Path, backup_name: str) -> str:
        """Comprimir backup"""
        try:
            logger.info("Comprimiendo backup...")
            
            # Crear directorio de backups si no existe
            backup_base_dir = Path("backups/enterprise")
            backup_base_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre del archivo comprimido
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_base_dir / f"{backup_name}_{timestamp}.tar.gz"
            
            # Comprimir backup
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_name)
            
            logger.info(f"✓ Backup comprimido: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Error comprimiendo backup: {e}")
            raise
    
    def _restore_files(self, temp_dir: Path, target_dir: str):
        """Restaurar archivos del backup"""
        try:
            logger.info("Restaurando archivos...")
            
            target_path = Path(target_dir)
            
            # Restaurar directorios
            for directory in self.backup_directories:
                source_dir = temp_dir / directory
                dest_dir = target_path / directory
                
                if source_dir.exists():
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    
                    shutil.copytree(source_dir, dest_dir)
                    logger.info(f"✓ Directorio restaurado: {directory}")
            
            # Restaurar archivos importantes
            for file_path in self.important_files:
                source_file = temp_dir / file_path
                dest_file = target_path / file_path
                
                if source_file.exists():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"✓ Archivo restaurado: {file_path}")
            
        except Exception as e:
            logger.error(f"Error restaurando archivos: {e}")
            raise
    
    def get_backup_info(self, backup_file: str) -> Optional[Dict[str, Any]]:
        """Obtener información de un backup"""
        try:
            if not Path(backup_file).exists():
                return None
            
            # Extraer metadatos del backup
            with tarfile.open(backup_file, "r:gz") as tar:
                try:
                    metadata_file = tar.extractfile("backup_metadata.json")
                    if metadata_file:
                        metadata = json.load(metadata_file)
                        return metadata
                except KeyError:
                    pass
            
            # Si no hay metadatos, usar información del archivo
            stat = Path(backup_file).stat()
            return {
                "filename": Path(backup_file).name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información del backup: {e}")
            return None

def main():
    """Función principal"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="Gestor de backup de datos enterprise")
        parser.add_argument("action", choices=["create", "restore", "list", "cleanup", "info"],
                          help="Acción a realizar")
        parser.add_argument("--name", help="Nombre del backup")
        parser.add_argument("--file", help="Archivo de backup para restaurar o obtener info")
        parser.add_argument("--target", default=".", help="Directorio objetivo para restaurar")
        
        args = parser.parse_args()
        
        manager = DataBackupManager()
        
        if args.action == "create":
            backup_file = manager.create_backup(args.name)
            print(f"✅ Backup creado: {backup_file}")
            
        elif args.action == "restore":
            if not args.file:
                print("❌ Error: Se requiere --file para restaurar")
                sys.exit(1)
            
            success = manager.restore_backup(args.file, args.target)
            if success:
                print("✅ Backup restaurado exitosamente")
            else:
                print("❌ Error restaurando backup")
                sys.exit(1)
                
        elif args.action == "list":
            backups = manager.list_backups()
            print(f"\n📋 Backups disponibles ({len(backups)}):")
            for backup in backups:
                print(f"  📁 {backup['filename']} ({backup['size_mb']}MB) - {backup['created']}")
                
        elif args.action == "cleanup":
            deleted = manager.cleanup_old_backups()
            print(f"✅ Backups antiguos eliminados: {deleted}")
            
        elif args.action == "info":
            if not args.file:
                print("❌ Error: Se requiere --file para obtener información")
                sys.exit(1)
            
            info = manager.get_backup_info(args.file)
            if info:
                print(f"\n📊 Información del backup:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ No se pudo obtener información del backup")
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error en función principal: {e}")
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
