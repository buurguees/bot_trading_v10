"""
Backup Validator Script - Bot Trading v10 Personal
==================================================

Script para validación de backups con:
- Verificación de integridad
- Validación de contenido
- Restauración de prueba
- Reportes de validación
- Limpieza de backups antiguos
"""

import asyncio
import logging
import sys
import argparse
import zipfile
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup_validator.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BackupValidator:
    """Validador de backups personal"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configuración de validación
        self.retention_days = 7
        self.max_backup_size_mb = 1000
        self.required_files = [
            'config/',
            'src/',
            'requirements.txt',
            'README.md'
        ]
        
        logger.info("BackupValidator inicializado")
    
    async def validate_all_backups(self) -> Dict[str, Any]:
        """Valida todos los backups disponibles"""
        try:
            logger.info("🔍 Validando todos los backups...")
            
            backup_files = list(self.backup_dir.glob("*.zip"))
            validation_results = {
                'timestamp': datetime.now().isoformat(),
                'total_backups': len(backup_files),
                'valid_backups': 0,
                'invalid_backups': 0,
                'backups': []
            }
            
            for backup_file in backup_files:
                try:
                    result = await self.validate_single_backup(backup_file)
                    validation_results['backups'].append(result)
                    
                    if result['valid']:
                        validation_results['valid_backups'] += 1
                    else:
                        validation_results['invalid_backups'] += 1
                
                except Exception as e:
                    logger.error(f"Error validando {backup_file}: {e}")
                    validation_results['backups'].append({
                        'file': str(backup_file),
                        'valid': False,
                        'error': str(e)
                    })
                    validation_results['invalid_backups'] += 1
            
            # Generar reporte
            await self.generate_validation_report(validation_results)
            
            logger.info(f"✅ Validación completada: {validation_results['valid_backups']} válidos, {validation_results['invalid_backups']} inválidos")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validando backups: {e}")
            raise
    
    async def validate_single_backup(self, backup_file: Path) -> Dict[str, Any]:
        """Valida un backup específico"""
        try:
            logger.info(f"Validando backup: {backup_file.name}")
            
            result = {
                'file': str(backup_file),
                'valid': False,
                'size_mb': 0,
                'created': None,
                'checksum': None,
                'files_count': 0,
                'missing_files': [],
                'errors': []
            }
            
            # Verificar que el archivo existe y no está corrupto
            if not backup_file.exists():
                result['errors'].append("Archivo no existe")
                return result
            
            # Obtener información del archivo
            file_stats = backup_file.stat()
            result['size_mb'] = round(file_stats.st_size / (1024 * 1024), 2)
            result['created'] = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            
            # Verificar tamaño máximo
            if result['size_mb'] > self.max_backup_size_mb:
                result['errors'].append(f"Archivo muy grande: {result['size_mb']} MB")
            
            # Verificar que es un ZIP válido
            try:
                with zipfile.ZipFile(backup_file, 'r') as zip_file:
                    # Verificar integridad del ZIP
                    bad_file = zip_file.testzip()
                    if bad_file:
                        result['errors'].append(f"Archivo ZIP corrupto: {bad_file}")
                        return result
                    
                    # Contar archivos
                    file_list = zip_file.namelist()
                    result['files_count'] = len(file_list)
                    
                    # Verificar archivos requeridos
                    for required_file in self.required_files:
                        if not any(required_file in file for file in file_list):
                            result['missing_files'].append(required_file)
                    
                    # Calcular checksum simple
                    result['checksum'] = hash(str(sorted(file_list)))
                    
            except zipfile.BadZipFile:
                result['errors'].append("No es un archivo ZIP válido")
                return result
            
            # Determinar si es válido
            result['valid'] = (
                len(result['errors']) == 0 and 
                len(result['missing_files']) == 0 and
                result['files_count'] > 0
            )
            
            if result['valid']:
                logger.info(f"✅ {backup_file.name}: Válido ({result['files_count']} archivos, {result['size_mb']} MB)")
            else:
                logger.warning(f"⚠️ {backup_file.name}: Inválido - {result['errors'] + result['missing_files']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validando {backup_file}: {e}")
            return {
                'file': str(backup_file),
                'valid': False,
                'error': str(e)
            }
    
    async def test_restore(self, backup_file: Path, test_dir: str = "test_restore") -> Dict[str, Any]:
        """Prueba la restauración de un backup"""
        try:
            logger.info(f"🧪 Probando restauración: {backup_file.name}")
            
            test_path = Path(test_dir)
            test_path.mkdir(exist_ok=True)
            
            result = {
                'backup_file': str(backup_file),
                'test_dir': str(test_path),
                'success': False,
                'restored_files': 0,
                'errors': []
            }
            
            try:
                with zipfile.ZipFile(backup_file, 'r') as zip_file:
                    # Extraer archivos
                    zip_file.extractall(test_path)
                    
                    # Contar archivos restaurados
                    restored_files = list(test_path.rglob("*"))
                    result['restored_files'] = len([f for f in restored_files if f.is_file()])
                    
                    # Verificar estructura básica
                    required_dirs = ['config', 'src']
                    for req_dir in required_dirs:
                        if not (test_path / req_dir).exists():
                            result['errors'].append(f"Directorio requerido no encontrado: {req_dir}")
                    
                    result['success'] = len(result['errors']) == 0
                    
                    if result['success']:
                        logger.info(f"✅ Restauración exitosa: {result['restored_files']} archivos")
                    else:
                        logger.warning(f"⚠️ Restauración con errores: {result['errors']}")
                
            except Exception as e:
                result['errors'].append(f"Error extrayendo backup: {e}")
                logger.error(f"Error extrayendo {backup_file}: {e}")
            
            finally:
                # Limpiar directorio de prueba
                if test_path.exists():
                    shutil.rmtree(test_path, ignore_errors=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error probando restauración: {e}")
            return {
                'backup_file': str(backup_file),
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_old_backups(self) -> Dict[str, Any]:
        """Limpia backups antiguos"""
        try:
            logger.info("🧹 Limpiando backups antiguos...")
            
            backup_files = list(self.backup_dir.glob("*.zip"))
            deleted_files = 0
            freed_space_mb = 0
            
            for backup_file in backup_files:
                try:
                    file_age = datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_age.days > self.retention_days:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        deleted_files += 1
                        freed_space_mb += file_size / (1024 * 1024)
                        logger.info(f"Eliminado backup antiguo: {backup_file.name}")
                
                except Exception as e:
                    logger.warning(f"Error eliminando {backup_file}: {e}")
            
            result = {
                'deleted_files': deleted_files,
                'freed_space_mb': round(freed_space_mb, 2),
                'success': True
            }
            
            logger.info(f"✅ Backups limpiados: {deleted_files} archivos, {freed_space_mb:.2f} MB liberados")
            return result
            
        except Exception as e:
            logger.error(f"Error limpiando backups: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_backup(self, backup_name: str = None) -> Dict[str, Any]:
        """Crea un nuevo backup"""
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            backup_file = self.backup_dir / backup_name
            logger.info(f"📦 Creando backup: {backup_file.name}")
            
            # Archivos y directorios a incluir
            include_paths = [
                'src/',
                'config/',
                'requirements.txt',
                'README.md',
                'bot.py',
                'app_personal_complete.py'
            ]
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for include_path in include_paths:
                    path = Path(include_path)
                    if path.exists():
                        if path.is_file():
                            zip_file.write(path, path.name)
                        else:
                            for file_path in path.rglob("*"):
                                if file_path.is_file():
                                    arcname = file_path.relative_to(Path('.'))
                                    zip_file.write(file_path, arcname)
            
            # Verificar el backup creado
            validation_result = await self.validate_single_backup(backup_file)
            
            result = {
                'backup_file': str(backup_file),
                'size_mb': validation_result['size_mb'],
                'files_count': validation_result['files_count'],
                'valid': validation_result['valid'],
                'success': validation_result['valid']
            }
            
            if result['success']:
                logger.info(f"✅ Backup creado exitosamente: {backup_file.name}")
            else:
                logger.error(f"❌ Error creando backup: {validation_result.get('errors', [])}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_validation_report(self, validation_results: Dict[str, Any]):
        """Genera reporte de validación"""
        try:
            logger.info("📊 Generando reporte de validación...")
            
            # Calcular estadísticas
            total_backups = validation_results['total_backups']
            valid_backups = validation_results['valid_backups']
            invalid_backups = validation_results['invalid_backups']
            
            success_rate = valid_backups / max(1, total_backups)
            
            # Mostrar resumen
            print("\n" + "="*60)
            print("REPORTE DE VALIDACIÓN DE BACKUPS")
            print("="*60)
            print(f"Fecha: {validation_results['timestamp']}")
            print(f"Total de backups: {total_backups}")
            print(f"Backups válidos: {valid_backups}")
            print(f"Backups inválidos: {invalid_backups}")
            print(f"Tasa de éxito: {success_rate:.2%}")
            print()
            
            # Mostrar detalles de cada backup
            for backup in validation_results['backups']:
                status = "✅" if backup['valid'] else "❌"
                print(f"{status} {Path(backup['file']).name}")
                print(f"   Tamaño: {backup.get('size_mb', 0):.2f} MB")
                print(f"   Archivos: {backup.get('files_count', 0)}")
                print(f"   Creado: {backup.get('created', 'N/A')}")
                
                if backup.get('errors'):
                    print(f"   Errores: {', '.join(backup['errors'])}")
                
                if backup.get('missing_files'):
                    print(f"   Archivos faltantes: {', '.join(backup['missing_files'])}")
                
                print()
            
            # Guardar reporte
            report_file = Path(f"logs/backup_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_file, 'w') as f:
                json.dump(validation_results, f, indent=2, default=str)
            
            print(f"Reporte guardado: {report_file}")
            print("="*60)
            
            logger.info(f"✅ Reporte generado: {report_file}")
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")

async def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Backup Validator Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python backup_validator.py --validate-all
  python backup_validator.py --validate-file backup_20250101.zip
  python backup_validator.py --test-restore backup_20250101.zip
  python backup_validator.py --cleanup-old
  python backup_validator.py --create-backup
        """
    )
    
    parser.add_argument(
        '--validate-all',
        action='store_true',
        help='Validar todos los backups'
    )
    
    parser.add_argument(
        '--validate-file',
        type=str,
        help='Validar un backup específico'
    )
    
    parser.add_argument(
        '--test-restore',
        type=str,
        help='Probar restauración de un backup'
    )
    
    parser.add_argument(
        '--cleanup-old',
        action='store_true',
        help='Limpiar backups antiguos'
    )
    
    parser.add_argument(
        '--create-backup',
        action='store_true',
        help='Crear nuevo backup'
    )
    
    parser.add_argument(
        '--backup-dir',
        type=str,
        default='backups',
        help='Directorio de backups'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del validador
    validator = BackupValidator(args.backup_dir)
    
    try:
        # Ejecutar comando solicitado
        if args.validate_all:
            await validator.validate_all_backups()
        
        elif args.validate_file:
            backup_file = Path(args.backup_file)
            result = await validator.validate_single_backup(backup_file)
            print(f"Resultado de validación: {result}")
        
        elif args.test_restore:
            backup_file = Path(args.test_restore)
            result = await validator.test_restore(backup_file)
            print(f"Resultado de restauración: {result}")
        
        elif args.cleanup_old:
            result = await validator.cleanup_old_backups()
            print(f"Limpieza completada: {result}")
        
        elif args.create_backup:
            result = await validator.create_backup()
            print(f"Backup creado: {result}")
        
        else:
            logger.info("ℹ️ Usa --help para ver las opciones disponibles")
            await validator.validate_all_backups()
    
    except KeyboardInterrupt:
        logger.info("Script detenido por el usuario")
    
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ejecutar script
    asyncio.run(main())
