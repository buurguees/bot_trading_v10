"""
core/health_checker.py - Sistema de Health Checks Robusto
Sistema de monitoreo y validación del estado del trading bot
"""

import os
import psutil
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import aiohttp
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Resultado de un health check individual"""
    name: str
    status: bool
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: float

class BaseHealthCheck:
    """Clase base para health checks"""
    
    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
        self.logger = logging.getLogger(f"health.{name}")
    
    async def run(self) -> HealthCheckResult:
        """Ejecuta el health check"""
        start_time = datetime.now()
        
        try:
            status, message, details = await self._check()
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details,
                timestamp=start_time,
                duration_ms=duration
            )
            
            if status:
                self.logger.debug(f"Health check {self.name} passed")
            else:
                level = self.logger.critical if self.critical else self.logger.warning
                level(f"Health check {self.name} failed: {message}")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Health check {self.name} error: {e}")
            
            return HealthCheckResult(
                name=self.name,
                status=False,
                message=f"Check failed with exception: {str(e)}",
                details={"error": str(e), "type": type(e).__name__},
                timestamp=start_time,
                duration_ms=duration
            )
    
    async def _check(self) -> tuple[bool, str, Dict[str, Any]]:
        """Implementar en subclases"""
        raise NotImplementedError

class DatabaseHealthCheck(BaseHealthCheck):
    """Health check para la base de datos"""
    
    def __init__(self):
        super().__init__("database", critical=True)
    
    async def _check(self) -> tuple[bool, str, Dict[str, Any]]:
        try:
            from data.database import db_manager
            
            # Verificar conexión
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if not result:
                    return False, "Database query failed", {}
            
            # Verificar tamaño de la base de datos
            db_path = Path("data/trading_bot.db")
            if not db_path.exists():
                return False, "Database file not found", {}
            
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            
            # Verificar tablas críticas
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('market_data', 'aligned_market_data')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                if 'market_data' not in tables:
                    return False, "Critical table 'market_data' missing", {}
                
                # Contar registros
                cursor.execute("SELECT COUNT(*) FROM market_data")
                record_count = cursor.fetchone()[0]
            
            details = {
                "db_size_mb": round(db_size_mb, 2),
                "tables": tables,
                "record_count": record_count,
                "has_aligned_data": 'aligned_market_data' in tables
            }
            
            if db_size_mb < 1:
                return False, f"Database too small: {db_size_mb:.2f}MB", details
            
            if record_count < 1000:
                return False, f"Insufficient data: {record_count} records", details
            
            return True, f"Database healthy: {record_count:,} records, {db_size_mb:.2f}MB", details
            
        except Exception as e:
            return False, f"Database check failed: {str(e)}", {"error": str(e)}

class ModelHealthCheck(BaseHealthCheck):
    """Health check para modelos de ML"""
    
    def __init__(self):
        super().__init__("models", critical=True)
    
    async def _check(self) -> tuple[bool, str, Dict[str, Any]]:
        try:
            models_dir = Path("models/saved_models")
            if not models_dir.exists():
                return False, "Models directory not found", {}
            
            # Buscar archivos de modelo
            model_files = list(models_dir.glob("*.h5"))
            if not model_files:
                return False, "No model files found", {}
            
            # Verificar el modelo más reciente
            latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
            model_size_mb = latest_model.stat().st_size / (1024 * 1024)
            
            # Verificar que el modelo se puede cargar
            try:
                import tensorflow as tf
                model = tf.keras.models.load_model(str(latest_model), compile=False)
                model_loaded = True
                model_layers = len(model.layers)
            except Exception as e:
                model_loaded = False
                model_layers = 0
            
            details = {
                "model_files": len(model_files),
                "latest_model": latest_model.name,
                "model_size_mb": round(model_size_mb, 2),
                "model_loaded": model_loaded,
                "model_layers": model_layers
            }
            
            if not model_loaded:
                return False, f"Latest model cannot be loaded: {latest_model.name}", details
            
            if model_size_mb < 1:
                return False, f"Model file too small: {model_size_mb:.2f}MB", details
            
            return True, f"Models healthy: {len(model_files)} files, latest: {latest_model.name}", details
            
        except Exception as e:
            return False, f"Model check failed: {str(e)}", {"error": str(e)}

class ResourceHealthCheck(BaseHealthCheck):
    """Health check para recursos del sistema"""
    
    def __init__(self):
        super().__init__("resources", critical=True)
    
    async def _check(self) -> tuple[bool, str, Dict[str, Any]]:
        try:
            # Memoria disponible
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            # Espacio en disco
            disk = psutil.disk_usage('.')
            free_gb = disk.free / (1024**3)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Procesos del bot
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'bot_trading' in cmdline or 'main_background' in cmdline:
                            bot_processes.append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            details = {
                "memory_available_gb": round(available_gb, 2),
                "disk_free_gb": round(free_gb, 2),
                "cpu_percent": round(cpu_percent, 1),
                "bot_processes": len(bot_processes),
                "processes": bot_processes
            }
            
            # Verificaciones críticas
            if available_gb < 1:
                return False, f"Insufficient memory: {available_gb:.2f}GB available", details
            
            if free_gb < 2:
                return False, f"Insufficient disk space: {free_gb:.2f}GB free", details
            
            if cpu_percent > 95:
                return False, f"High CPU usage: {cpu_percent:.1f}%", details
            
            return True, f"Resources healthy: {available_gb:.2f}GB RAM, {free_gb:.2f}GB disk", details
            
        except Exception as e:
            return False, f"Resource check failed: {str(e)}", {"error": str(e)}

class APIHealthCheck(BaseHealthCheck):
    """Health check para APIs externas"""
    
    def __init__(self):
        super().__init__("api", critical=False)
    
    async def _check(self) -> tuple[bool, str, Dict[str, Any]]:
        try:
            # Verificar conectividad a Bitget API
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get('https://api.bitget.com/api/spot/v1/public/time', timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            api_working = True
                            api_response = data
                        else:
                            api_working = False
                            api_response = {"status": response.status}
                except Exception as e:
                    api_working = False
                    api_response = {"error": str(e)}
            
            details = {
                "bitget_api": api_working,
                "response": api_response
            }
            
            if not api_working:
                return False, "Bitget API not accessible", details
            
            return True, "APIs healthy", details
            
        except Exception as e:
            return False, f"API check failed: {str(e)}", {"error": str(e)}

class SystemHealthChecker:
    """Coordinador principal de health checks"""
    
    def __init__(self):
        self.checks = [
            DatabaseHealthCheck(),
            ModelHealthCheck(),
            ResourceHealthCheck(),
            APIHealthCheck()
        ]
        self.logger = logging.getLogger("health_checker")
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Ejecuta todos los health checks"""
        self.logger.info("Running system health checks...")
        
        results = {}
        for check in self.checks:
            try:
                result = await check.run()
                results[check.name] = result
            except Exception as e:
                self.logger.error(f"Health check {check.name} crashed: {e}")
                results[check.name] = HealthCheckResult(
                    name=check.name,
                    status=False,
                    message=f"Check crashed: {str(e)}",
                    details={"error": str(e)},
                    timestamp=datetime.now(),
                    duration_ms=0
                )
        
        # Análisis de resultados
        critical_failures = [
            name for name, result in results.items() 
            if not result.status and self._get_check(name).critical
        ]
        
        if critical_failures:
            self.logger.critical(f"Critical health check failures: {critical_failures}")
        else:
            self.logger.info("All health checks completed")
        
        return results
    
    def _get_check(self, name: str) -> Optional[BaseHealthCheck]:
        """Obtiene un health check por nombre"""
        for check in self.checks:
            if check.name == name:
                return check
        return None
    
    def get_system_status(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Analiza los resultados y devuelve el estado del sistema"""
        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r.status)
        critical_failures = [
            name for name, result in results.items() 
            if not result.status and self._get_check(name).critical
        ]
        
        overall_status = len(critical_failures) == 0
        
        return {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "critical_failures": critical_failures,
            "system_ready": overall_status,
            "timestamp": datetime.now().isoformat()
        }

# Instancia global
health_checker = SystemHealthChecker()

# Funciones de conveniencia
async def check_system_health() -> Dict[str, Any]:
    """Función de conveniencia para verificar la salud del sistema"""
    results = await health_checker.run_all_checks()
    return health_checker.get_system_status(results)

async def validate_system_state() -> bool:
    """Valida que el sistema esté listo para operar"""
    results = await health_checker.run_all_checks()
    status = health_checker.get_system_status(results)
    return status["system_ready"]
