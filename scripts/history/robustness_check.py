#!/usr/bin/env python3
"""
Verificación de Robustez del Sistema
====================================

Script para verificar la robustez, rendimiento y ausencia de fugas de memoria
del sistema de trading bot.

Uso:
    python scripts/root/robustness_check.py
"""

import sys
import os
import time
import psutil
import gc
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Agregar src y config al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "config"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ROBUSTNESS - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/robustness_check.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RobustnessChecker:
    """Verificador de robustez del sistema"""
    
    def __init__(self):
        self.start_time = time.time()
        self.initial_memory = psutil.virtual_memory().used
        self.process = psutil.Process()
        self.results = {}
        
        logger.info("Iniciando verificación de robustez del sistema")
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Verifica el uso de memoria"""
        try:
            memory_info = psutil.virtual_memory()
            process_memory = self.process.memory_info()
            
            result = {
                'total_memory_gb': memory_info.total / 1024**3,
                'available_memory_gb': memory_info.available / 1024**3,
                'used_memory_gb': memory_info.used / 1024**3,
                'memory_percent': memory_info.percent,
                'process_memory_mb': process_memory.rss / 1024**2,
                'process_memory_percent': (process_memory.rss / memory_info.total) * 100
            }
            
            logger.info(f"Memoria total: {result['total_memory_gb']:.1f} GB")
            logger.info(f"Memoria disponible: {result['available_memory_gb']:.1f} GB")
            logger.info(f"Memoria del proceso: {result['process_memory_mb']:.1f} MB")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando memoria: {e}")
            return {}
    
    def check_cpu_usage(self) -> Dict[str, Any]:
        """Verifica el uso de CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            result = {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else 0,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            
            logger.info(f"CPU: {cpu_percent}% ({cpu_count} cores)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando CPU: {e}")
            return {}
    
    def check_disk_usage(self) -> Dict[str, Any]:
        """Verifica el uso de disco"""
        try:
            disk_usage = psutil.disk_usage('.')
            
            result = {
                'total_disk_gb': disk_usage.total / 1024**3,
                'used_disk_gb': disk_usage.used / 1024**3,
                'free_disk_gb': disk_usage.free / 1024**3,
                'disk_percent': (disk_usage.used / disk_usage.total) * 100
            }
            
            logger.info(f"Disco: {result['used_disk_gb']:.1f} GB usados de {result['total_disk_gb']:.1f} GB")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando disco: {e}")
            return {}
    
    def check_file_system(self) -> Dict[str, Any]:
        """Verifica el sistema de archivos"""
        try:
            result = {
                'models_count': 0,
                'historical_data_count': 0,
                'logs_count': 0,
                'reports_count': 0,
                'total_size_mb': 0
            }
            
            # Verificar directorios clave
            dirs_to_check = {
                'models': 'models',
                'historical_data': 'data/historical',
                'logs': 'logs',
                'reports': 'reports'
            }
            
            for key, dir_path in dirs_to_check.items():
                path = Path(dir_path)
                if path.exists():
                    files = list(path.glob('*'))
                    result[f'{key}_count'] = len(files)
                    
                    # Calcular tamaño total
                    total_size = sum(f.stat().st_size for f in files if f.is_file())
                    result['total_size_mb'] += total_size / 1024**2
                    
                    logger.info(f"{key}: {len(files)} archivos")
            
            result['total_size_mb'] = round(result['total_size_mb'], 2)
            logger.info(f"Tamaño total de archivos: {result['total_size_mb']} MB")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando sistema de archivos: {e}")
            return {}
    
    def check_imports(self) -> Dict[str, Any]:
        """Verifica que las importaciones funcionen correctamente"""
        try:
            result = {
                'config_loader': False,
                'bot_main': False,
                'dashboard': False,
                'training_script': False
            }
            
            # Verificar config_loader
            try:
                from core.config.config_loader import ConfigLoader
                config_loader = ConfigLoader()
                symbols = config_loader.get_symbols()
                result['config_loader'] = len(symbols) > 0
                logger.info(f"Config loader: OK ({len(symbols)} símbolos)")
            except Exception as e:
                logger.error(f"Config loader: ERROR - {e}")
            
            # Verificar bot principal
            try:
                import bot
                result['bot_main'] = True
                logger.info("Bot principal: OK")
            except Exception as e:
                logger.error(f"Bot principal: ERROR - {e}")
            
            # Verificar dashboard
            try:
                import src.core.monitoring.simple_dashboard
                result['dashboard'] = True
                logger.info("Dashboard: OK")
            except Exception as e:
                logger.error(f"Dashboard: ERROR - {e}")
            
            # Verificar script de entrenamiento
            try:
                training_script = Path("scripts/root/start_6h_training_enterprise.py")
                result['training_script'] = training_script.exists()
                logger.info(f"Script de entrenamiento: {'OK' if result['training_script'] else 'MISSING'}")
            except Exception as e:
                logger.error(f"Script de entrenamiento: ERROR - {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando importaciones: {e}")
            return {}
    
    def check_memory_leaks(self) -> Dict[str, Any]:
        """Verifica posibles fugas de memoria"""
        try:
            # Forzar garbage collection
            gc.collect()
            
            # Medir memoria antes y después de operaciones
            memory_before = self.process.memory_info().rss
            
            # Simular operaciones del bot
            for i in range(10):
                # Simular carga de configuración
                from core.config.config_loader import ConfigLoader
                config_loader = ConfigLoader()
                symbols = config_loader.get_symbols()
                
                # Simular procesamiento de datos
                data = [f"test_data_{i}_{j}" for j in range(1000)]
                del data
            
            # Forzar garbage collection
            gc.collect()
            
            memory_after = self.process.memory_info().rss
            memory_diff = memory_after - memory_before
            
            result = {
                'memory_before_mb': memory_before / 1024**2,
                'memory_after_mb': memory_after / 1024**2,
                'memory_diff_mb': memory_diff / 1024**2,
                'potential_leak': memory_diff > 10 * 1024**2  # Más de 10MB de diferencia
            }
            
            logger.info(f"Memoria antes: {result['memory_before_mb']:.1f} MB")
            logger.info(f"Memoria después: {result['memory_after_mb']:.1f} MB")
            logger.info(f"Diferencia: {result['memory_diff_mb']:.1f} MB")
            
            if result['potential_leak']:
                logger.warning("Posible fuga de memoria detectada")
            else:
                logger.info("No se detectaron fugas de memoria")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando fugas de memoria: {e}")
            return {}
    
    def check_performance(self) -> Dict[str, Any]:
        """Verifica el rendimiento del sistema"""
        try:
            result = {}
            
            # Medir tiempo de importación
            start_time = time.time()
            from core.config.config_loader import ConfigLoader
            config_loader = ConfigLoader()
            symbols = config_loader.get_symbols()
            import_time = time.time() - start_time
            
            result['import_time_seconds'] = round(import_time, 4)
            logger.info(f"Tiempo de importación: {import_time:.4f} segundos")
            
            # Medir tiempo de operaciones del bot
            start_time = time.time()
            import bot
            bot_time = time.time() - start_time
            
            result['bot_import_time_seconds'] = round(bot_time, 4)
            logger.info(f"Tiempo de importación del bot: {bot_time:.4f} segundos")
            
            # Verificar que el bot se puede inicializar
            start_time = time.time()
            bot_instance = bot.BotTradingEnterprise()
            init_time = time.time() - start_time
            
            result['bot_init_time_seconds'] = round(init_time, 4)
            logger.info(f"Tiempo de inicialización del bot: {init_time:.4f} segundos")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verificando rendimiento: {e}")
            return {}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Ejecuta todas las verificaciones"""
        logger.info("Ejecutando todas las verificaciones de robustez...")
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'memory': self.check_memory_usage(),
            'cpu': self.check_cpu_usage(),
            'disk': self.check_disk_usage(),
            'file_system': self.check_file_system(),
            'imports': self.check_imports(),
            'memory_leaks': self.check_memory_leaks(),
            'performance': self.check_performance()
        }
        
        # Calcular puntuación general
        self.results['overall_score'] = self.calculate_overall_score()
        
        # Generar reporte
        self.generate_report()
        
        return self.results
    
    def calculate_overall_score(self) -> int:
        """Calcula una puntuación general de robustez (0-100)"""
        score = 100
        
        # Penalizar por uso alto de memoria
        memory_percent = self.results.get('memory', {}).get('memory_percent', 0)
        if memory_percent > 90:
            score -= 20
        elif memory_percent > 80:
            score -= 10
        
        # Penalizar por uso alto de CPU
        cpu_percent = self.results.get('cpu', {}).get('cpu_percent', 0)
        if cpu_percent > 90:
            score -= 15
        elif cpu_percent > 70:
            score -= 5
        
        # Penalizar por problemas de importación
        imports = self.results.get('imports', {})
        failed_imports = sum(1 for v in imports.values() if not v)
        score -= failed_imports * 15
        
        # Penalizar por fugas de memoria
        if self.results.get('memory_leaks', {}).get('potential_leak', False):
            score -= 25
        
        # Penalizar por rendimiento lento
        import_time = self.results.get('performance', {}).get('import_time_seconds', 0)
        if import_time > 5:
            score -= 10
        elif import_time > 2:
            score -= 5
        
        return max(0, score)
    
    def generate_report(self):
        """Genera un reporte de robustez"""
        try:
            report_path = Path("reports/robustness_report.json")
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de robustez guardado: {report_path}")
            
            # Mostrar resumen
            score = self.results.get('overall_score', 0)
            logger.info(f"Puntuación general de robustez: {score}/100")
            
            if score >= 90:
                logger.info("Sistema muy robusto")
            elif score >= 70:
                logger.info("Sistema robusto")
            elif score >= 50:
                logger.warning("Sistema con problemas menores")
            else:
                logger.error("Sistema con problemas serios")
                
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")

def main():
    """Función principal"""
    try:
        # Crear directorio de logs
        Path("logs").mkdir(exist_ok=True)
        
        # Ejecutar verificaciones
        checker = RobustnessChecker()
        results = checker.run_all_checks()
        
        logger.info("Verificación de robustez completada")
        
    except Exception as e:
        logger.error(f"Error en verificación de robustez: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
