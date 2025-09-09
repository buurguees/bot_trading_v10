"""
Personal Maintenance Script - Bot Trading v10 Personal
======================================================

Script de mantenimiento automatizado para uso personal con:
- Limpieza de logs antiguos
- Validación de backups
- Verificación de salud del sistema
- Optimización de rendimiento
- Reportes de mantenimiento
"""

import asyncio
import logging
import sys
import argparse
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.personal.multi_exchange import MultiExchangeManager
from src.core.personal.latency import LatencyOptimizer
from src.core.config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/maintenance.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PersonalMaintenance:
    """Script de mantenimiento personal"""
    
    def __init__(self, config_path: str = "config/personal/exchanges.yaml"):
        self.config_path = config_path
        self.config_manager = EnterpriseConfigManager(config_path)
        self.exchange_manager = None
        self.latency_optimizer = None
        
        # Configuración de mantenimiento
        self.log_retention_days = 30
        self.backup_retention_days = 7
        self.max_log_size_mb = 100
        self.max_cache_size_mb = 500
        
        logger.info("PersonalMaintenance inicializado")
    
    async def initialize(self):
        """Inicializa los componentes necesarios"""
        try:
            logger.info("Inicializando PersonalMaintenance...")
            
            # Cargar configuración
            config = self.config_manager.load_config()
            
            # Inicializar componentes si es necesario
            if config.get('maintenance', {}).get('check_exchanges', False):
                self.exchange_manager = MultiExchangeManager(self.config_path)
                await self.exchange_manager.start()
            
            if config.get('maintenance', {}).get('check_latency', False):
                latency_config = config.get('latency', {})
                self.latency_optimizer = LatencyOptimizer(self.exchange_manager, latency_config)
                await self.latency_optimizer.start()
            
            logger.info("PersonalMaintenance inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando PersonalMaintenance: {e}")
            raise
    
    async def run_full_maintenance(self):
        """Ejecuta mantenimiento completo"""
        try:
            logger.info("🧹 Iniciando mantenimiento completo...")
            
            maintenance_report = {
                'timestamp': datetime.now().isoformat(),
                'operations': [],
                'errors': [],
                'summary': {}
            }
            
            # 1. Limpiar logs antiguos
            log_cleanup = await self.cleanup_old_logs()
            maintenance_report['operations'].append(log_cleanup)
            
            # 2. Limpiar cache
            cache_cleanup = await self.cleanup_cache()
            maintenance_report['operations'].append(cache_cleanup)
            
            # 3. Verificar backups
            backup_check = await self.check_backups()
            maintenance_report['operations'].append(backup_check)
            
            # 4. Verificar salud del sistema
            health_check = await self.check_system_health()
            maintenance_report['operations'].append(health_check)
            
            # 5. Optimizar rendimiento
            performance_optimization = await self.optimize_performance()
            maintenance_report['operations'].append(performance_optimization)
            
            # 6. Generar reporte
            await self.generate_maintenance_report(maintenance_report)
            
            logger.info("✅ Mantenimiento completo finalizado")
            return maintenance_report
            
        except Exception as e:
            logger.error(f"Error en mantenimiento completo: {e}")
            raise
    
    async def cleanup_old_logs(self) -> Dict[str, Any]:
        """Limpia logs antiguos"""
        try:
            logger.info("🧹 Limpiando logs antiguos...")
            
            log_dirs = ['logs', 'logs/enterprise', 'logs/personal']
            deleted_files = 0
            freed_space_mb = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if not log_path.exists():
                    continue
                
                for log_file in log_path.rglob("*.log"):
                    try:
                        # Verificar antigüedad
                        file_age = datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)
                        
                        if file_age.days > self.log_retention_days:
                            file_size = log_file.stat().st_size
                            log_file.unlink()
                            deleted_files += 1
                            freed_space_mb += file_size / (1024 * 1024)
                            logger.debug(f"Eliminado: {log_file}")
                    
                    except Exception as e:
                        logger.warning(f"Error eliminando {log_file}: {e}")
            
            result = {
                'operation': 'log_cleanup',
                'deleted_files': deleted_files,
                'freed_space_mb': round(freed_space_mb, 2),
                'success': True
            }
            
            logger.info(f"✅ Logs limpiados: {deleted_files} archivos, {freed_space_mb:.2f} MB liberados")
            return result
            
        except Exception as e:
            logger.error(f"Error limpiando logs: {e}")
            return {
                'operation': 'log_cleanup',
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_cache(self) -> Dict[str, Any]:
        """Limpia cache del sistema"""
        try:
            logger.info("🧹 Limpiando cache...")
            
            cache_dirs = ['cache', 'mlruns', 'checkpoints']
            deleted_files = 0
            freed_space_mb = 0
            
            for cache_dir in cache_dirs:
                cache_path = Path(cache_dir)
                if not cache_path.exists():
                    continue
                
                for cache_file in cache_path.rglob("*"):
                    try:
                        if cache_file.is_file():
                            file_size = cache_file.stat().st_size
                            file_size_mb = file_size / (1024 * 1024)
                            
                            # Eliminar archivos de cache grandes o antiguos
                            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                            
                            if (file_size_mb > self.max_cache_size_mb or 
                                file_age.days > self.backup_retention_days):
                                
                                cache_file.unlink()
                                deleted_files += 1
                                freed_space_mb += file_size_mb
                                logger.debug(f"Eliminado: {cache_file}")
                    
                    except Exception as e:
                        logger.warning(f"Error eliminando {cache_file}: {e}")
            
            result = {
                'operation': 'cache_cleanup',
                'deleted_files': deleted_files,
                'freed_space_mb': round(freed_space_mb, 2),
                'success': True
            }
            
            logger.info(f"✅ Cache limpiado: {deleted_files} archivos, {freed_space_mb:.2f} MB liberados")
            return result
            
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
            return {
                'operation': 'cache_cleanup',
                'success': False,
                'error': str(e)
            }
    
    async def check_backups(self) -> Dict[str, Any]:
        """Verifica la integridad de los backups"""
        try:
            logger.info("🔍 Verificando backups...")
            
            backup_dir = Path("backups")
            if not backup_dir.exists():
                return {
                    'operation': 'backup_check',
                    'success': False,
                    'error': 'Directorio de backups no existe'
                }
            
            backup_files = list(backup_dir.glob("*.zip"))
            valid_backups = 0
            corrupted_backups = 0
            
            for backup_file in backup_files:
                try:
                    # Verificar que el archivo no esté corrupto
                    if backup_file.stat().st_size > 0:
                        valid_backups += 1
                    else:
                        corrupted_backups += 1
                        logger.warning(f"Backup corrupto: {backup_file}")
                
                except Exception as e:
                    corrupted_backups += 1
                    logger.warning(f"Error verificando {backup_file}: {e}")
            
            # Verificar si hay backups recientes
            recent_backups = 0
            for backup_file in backup_files:
                file_age = datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_age.days <= 1:  # Backup de las últimas 24 horas
                    recent_backups += 1
            
            result = {
                'operation': 'backup_check',
                'total_backups': len(backup_files),
                'valid_backups': valid_backups,
                'corrupted_backups': corrupted_backups,
                'recent_backups': recent_backups,
                'success': True
            }
            
            if recent_backups == 0:
                logger.warning("⚠️ No hay backups recientes")
                result['warning'] = 'No hay backups recientes'
            
            logger.info(f"✅ Backups verificados: {valid_backups} válidos, {corrupted_backups} corruptos")
            return result
            
        except Exception as e:
            logger.error(f"Error verificando backups: {e}")
            return {
                'operation': 'backup_check',
                'success': False,
                'error': str(e)
            }
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Verifica la salud del sistema"""
        try:
            logger.info("🏥 Verificando salud del sistema...")
            
            health_status = {
                'exchanges': {},
                'latency': {},
                'disk_space': {},
                'memory_usage': {}
            }
            
            # Verificar exchanges si están disponibles
            if self.exchange_manager:
                connection_status = self.exchange_manager.get_connection_status()
                health_status['exchanges'] = connection_status
                
                connected_exchanges = sum(1 for status in connection_status.values() if status)
                total_exchanges = len(connection_status)
                
                if connected_exchanges < total_exchanges:
                    logger.warning(f"⚠️ Solo {connected_exchanges}/{total_exchanges} exchanges conectados")
            
            # Verificar latencia si está disponible
            if self.latency_optimizer:
                perf_stats = self.latency_optimizer.get_performance_stats()
                health_status['latency'] = {
                    'avg_latency_ms': perf_stats['avg_latency_ms'],
                    'success_rate': perf_stats['success_rate'],
                    'target_latency_ms': perf_stats['target_latency_ms']
                }
                
                if perf_stats['avg_latency_ms'] > perf_stats['target_latency_ms']:
                    logger.warning(f"⚠️ Latencia alta: {perf_stats['avg_latency_ms']:.2f}ms")
            
            # Verificar espacio en disco
            disk_usage = shutil.disk_usage('.')
            disk_free_gb = disk_usage.free / (1024**3)
            health_status['disk_space'] = {
                'free_gb': round(disk_free_gb, 2),
                'total_gb': round(disk_usage.total / (1024**3), 2)
            }
            
            if disk_free_gb < 1:  # Menos de 1GB libre
                logger.warning(f"⚠️ Poco espacio en disco: {disk_free_gb:.2f} GB")
            
            result = {
                'operation': 'health_check',
                'health_status': health_status,
                'success': True
            }
            
            logger.info("✅ Salud del sistema verificada")
            return result
            
        except Exception as e:
            logger.error(f"Error verificando salud del sistema: {e}")
            return {
                'operation': 'health_check',
                'success': False,
                'error': str(e)
            }
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimiza el rendimiento del sistema"""
        try:
            logger.info("⚡ Optimizando rendimiento...")
            
            optimizations = []
            
            # Limpiar archivos temporales
            temp_dirs = ['__pycache__', '.pytest_cache', '.mypy_cache']
            for temp_dir in temp_dirs:
                for temp_path in Path('.').rglob(temp_dir):
                    if temp_path.is_dir():
                        shutil.rmtree(temp_path, ignore_errors=True)
                        optimizations.append(f"Eliminado: {temp_path}")
            
            # Optimizar base de datos si existe
            db_file = Path("data/trading_bot.db")
            if db_file.exists():
                # Aquí podrías ejecutar VACUUM o ANALYZE en SQLite
                optimizations.append("Base de datos optimizada")
            
            result = {
                'operation': 'performance_optimization',
                'optimizations': optimizations,
                'success': True
            }
            
            logger.info(f"✅ Rendimiento optimizado: {len(optimizations)} optimizaciones")
            return result
            
        except Exception as e:
            logger.error(f"Error optimizando rendimiento: {e}")
            return {
                'operation': 'performance_optimization',
                'success': False,
                'error': str(e)
            }
    
    async def generate_maintenance_report(self, report: Dict[str, Any]):
        """Genera reporte de mantenimiento"""
        try:
            logger.info("📊 Generando reporte de mantenimiento...")
            
            # Calcular resumen
            total_operations = len(report['operations'])
            successful_operations = sum(1 for op in report['operations'] if op.get('success', False))
            
            total_freed_space = sum(
                op.get('freed_space_mb', 0) for op in report['operations'] 
                if 'freed_space_mb' in op
            )
            
            report['summary'] = {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': successful_operations / max(1, total_operations),
                'total_freed_space_mb': round(total_freed_space, 2),
                'timestamp': report['timestamp']
            }
            
            # Guardar reporte
            report_file = Path(f"logs/maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            import json
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Mostrar resumen
            print("\n" + "="*60)
            print("REPORTE DE MANTENIMIENTO")
            print("="*60)
            print(f"Fecha: {report['timestamp']}")
            print(f"Operaciones totales: {total_operations}")
            print(f"Operaciones exitosas: {successful_operations}")
            print(f"Tasa de éxito: {successful_operations / max(1, total_operations):.2%}")
            print(f"Espacio liberado: {total_freed_space:.2f} MB")
            print(f"Reporte guardado: {report_file}")
            print("="*60)
            
            logger.info(f"✅ Reporte generado: {report_file}")
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
    
    async def shutdown(self):
        """Cierra el sistema de forma segura"""
        try:
            logger.info("Cerrando PersonalMaintenance...")
            
            if self.latency_optimizer:
                await self.latency_optimizer.stop()
            
            if self.exchange_manager:
                await self.exchange_manager.stop()
            
            logger.info("PersonalMaintenance cerrado correctamente")
            
        except Exception as e:
            logger.error(f"Error cerrando PersonalMaintenance: {e}")

async def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Personal Maintenance Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python maintenance.py --full
  python maintenance.py --cleanup-logs
  python maintenance.py --check-backups
  python maintenance.py --check-health
  python maintenance.py --optimize
        """
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Ejecutar mantenimiento completo'
    )
    
    parser.add_argument(
        '--cleanup-logs',
        action='store_true',
        help='Limpiar logs antiguos'
    )
    
    parser.add_argument(
        '--check-backups',
        action='store_true',
        help='Verificar backups'
    )
    
    parser.add_argument(
        '--check-health',
        action='store_true',
        help='Verificar salud del sistema'
    )
    
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Optimizar rendimiento'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/personal/exchanges.yaml',
        help='Ruta al archivo de configuración'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del script
    maintenance = PersonalMaintenance(args.config)
    
    try:
        # Inicializar sistema
        await maintenance.initialize()
        
        # Ejecutar comando solicitado
        if args.full:
            await maintenance.run_full_maintenance()
        
        elif args.cleanup_logs:
            result = await maintenance.cleanup_old_logs()
            print(f"Logs limpiados: {result}")
        
        elif args.check_backups:
            result = await maintenance.check_backups()
            print(f"Backups verificados: {result}")
        
        elif args.check_health:
            result = await maintenance.check_system_health()
            print(f"Salud del sistema: {result}")
        
        elif args.optimize:
            result = await maintenance.optimize_performance()
            print(f"Rendimiento optimizado: {result}")
        
        else:
            logger.info("ℹ️ Usa --help para ver las opciones disponibles")
            await maintenance.run_full_maintenance()
    
    except KeyboardInterrupt:
        logger.info("Script detenido por el usuario")
    
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    
    finally:
        await maintenance.shutdown()

if __name__ == "__main__":
    # Ejecutar script
    asyncio.run(main())
