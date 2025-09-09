# Ruta: scripts/deployment/enterprise/health_check.py
# health_check.py - Script de verificación de salud enterprise
# Ubicación: C:\TradingBot_v10\scripts\enterprise\health_check.py

import os
import sys
import json
import logging
import subprocess
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.config.enterprise_config import get_enterprise_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """Verificador de salud enterprise"""
    
    def __init__(self):
        """Inicializar el verificador de salud"""
        self.config = get_enterprise_config()
        self.infrastructure_config = self.config.get_infrastructure_config()
        self.health_checks_config = self.infrastructure_config.get("health_checks", {})
        
        # Configuración de health checks
        self.interval_seconds = self.health_checks_config.get("interval_seconds", 30)
        self.timeout_seconds = self.health_checks_config.get("timeout_seconds", 10)
        self.max_failures = self.health_checks_config.get("max_failures", 3)
        
        # Estado de health checks
        self.health_status = {
            "kafka": {"status": "unknown", "last_check": None, "failures": 0},
            "redis": {"status": "unknown", "last_check": None, "failures": 0},
            "timescaledb": {"status": "unknown", "last_check": None, "failures": 0},
            "prometheus": {"status": "unknown", "last_check": None, "failures": 0},
            "grafana": {"status": "unknown", "last_check": None, "failures": 0},
            "trading_bot": {"status": "unknown", "last_check": None, "failures": 0}
        }
        
        logger.info("HealthChecker inicializado")
    
    def check_all_services(self) -> Dict[str, Any]:
        """Verificar salud de todos los servicios"""
        try:
            logger.info("=== VERIFICANDO SALUD DE SERVICIOS ===")
            
            results = {}
            
            # Verificar servicios de infraestructura
            results["kafka"] = self._check_kafka()
            results["redis"] = self._check_redis()
            results["timescaledb"] = self._check_timescaledb()
            results["prometheus"] = self._check_prometheus()
            results["grafana"] = self._check_grafana()
            
            # Verificar servicios de aplicación
            results["trading_bot"] = self._check_trading_bot()
            
            # Calcular estado general
            overall_status = self._calculate_overall_status(results)
            
            # Generar reporte
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": overall_status,
                "services": results,
                "summary": self._generate_summary(results)
            }
            
            logger.info(f"Verificación de salud completada - Estado general: {overall_status}")
            return report
            
        except Exception as e:
            logger.error(f"Error verificando salud de servicios: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": "error",
                "error": str(e),
                "services": {}
            }
    
    def _check_kafka(self) -> Dict[str, Any]:
        """Verificar salud de Kafka"""
        try:
            start_time = time.time()
            
            # Verificar conexión TCP
            if not self._check_tcp_connection("localhost", 9092):
                return self._create_health_result("unhealthy", "No se puede conectar a Kafka", start_time)
            
            # Verificar API de Kafka
            try:
                cmd = [
                    "docker", "exec", "trading_bot_kafka",
                    "kafka-broker-api-versions",
                    "--bootstrap-server=localhost:9092"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                
                if result.returncode == 0:
                    return self._create_health_result("healthy", "Kafka está funcionando correctamente", start_time)
                else:
                    return self._create_health_result("unhealthy", f"Error en API de Kafka: {result.stderr}", start_time)
                    
            except subprocess.TimeoutExpired:
                return self._create_health_result("unhealthy", "Timeout verificando API de Kafka", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando API de Kafka: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando Kafka: {e}", time.time())
    
    def _check_redis(self) -> Dict[str, Any]:
        """Verificar salud de Redis"""
        try:
            start_time = time.time()
            
            # Verificar conexión TCP
            if not self._check_tcp_connection("localhost", 6379):
                return self._create_health_result("unhealthy", "No se puede conectar a Redis", start_time)
            
            # Verificar comando PING
            try:
                cmd = [
                    "docker", "exec", "trading_bot_redis",
                    "redis-cli", "ping"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                
                if result.returncode == 0 and "PONG" in result.stdout:
                    return self._create_health_result("healthy", "Redis está funcionando correctamente", start_time)
                else:
                    return self._create_health_result("unhealthy", f"Error en comando PING de Redis: {result.stderr}", start_time)
                    
            except subprocess.TimeoutExpired:
                return self._create_health_result("unhealthy", "Timeout verificando Redis", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando Redis: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando Redis: {e}", time.time())
    
    def _check_timescaledb(self) -> Dict[str, Any]:
        """Verificar salud de TimescaleDB"""
        try:
            start_time = time.time()
            
            # Verificar conexión TCP
            if not self._check_tcp_connection("localhost", 5432):
                return self._create_health_result("unhealthy", "No se puede conectar a TimescaleDB", start_time)
            
            # Verificar comando pg_isready
            try:
                cmd = [
                    "docker", "exec", "trading_bot_timescaledb",
                    "pg_isready", "-U", "trading_bot", "-d", "trading_bot_enterprise"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                
                if result.returncode == 0:
                    return self._create_health_result("healthy", "TimescaleDB está funcionando correctamente", start_time)
                else:
                    return self._create_health_result("unhealthy", f"Error en pg_isready: {result.stderr}", start_time)
                    
            except subprocess.TimeoutExpired:
                return self._create_health_result("unhealthy", "Timeout verificando TimescaleDB", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando TimescaleDB: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando TimescaleDB: {e}", time.time())
    
    def _check_prometheus(self) -> Dict[str, Any]:
        """Verificar salud de Prometheus"""
        try:
            start_time = time.time()
            
            # Verificar conexión HTTP
            try:
                response = requests.get(
                    "http://localhost:9090/-/healthy",
                    timeout=self.timeout_seconds
                )
                
                if response.status_code == 200:
                    return self._create_health_result("healthy", "Prometheus está funcionando correctamente", start_time)
                else:
                    return self._create_health_result("unhealthy", f"Prometheus respondió con código {response.status_code}", start_time)
                    
            except requests.exceptions.Timeout:
                return self._create_health_result("unhealthy", "Timeout verificando Prometheus", start_time)
            except requests.exceptions.ConnectionError:
                return self._create_health_result("unhealthy", "No se puede conectar a Prometheus", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando Prometheus: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando Prometheus: {e}", time.time())
    
    def _check_grafana(self) -> Dict[str, Any]:
        """Verificar salud de Grafana"""
        try:
            start_time = time.time()
            
            # Verificar conexión HTTP
            try:
                response = requests.get(
                    "http://localhost:3000/api/health",
                    timeout=self.timeout_seconds
                )
                
                if response.status_code == 200:
                    return self._create_health_result("healthy", "Grafana está funcionando correctamente", start_time)
                else:
                    return self._create_health_result("unhealthy", f"Grafana respondió con código {response.status_code}", start_time)
                    
            except requests.exceptions.Timeout:
                return self._create_health_result("unhealthy", "Timeout verificando Grafana", start_time)
            except requests.exceptions.ConnectionError:
                return self._create_health_result("unhealthy", "No se puede conectar a Grafana", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando Grafana: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando Grafana: {e}", time.time())
    
    def _check_trading_bot(self) -> Dict[str, Any]:
        """Verificar salud del Trading Bot"""
        try:
            start_time = time.time()
            
            # Verificar si el proceso está ejecutándose
            try:
                cmd = ["docker", "ps", "--filter", "name=trading_bot", "--format", "{{.Status}}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and "Up" in result.stdout:
                    return self._create_health_result("healthy", "Trading Bot está ejecutándose", start_time)
                else:
                    return self._create_health_result("unhealthy", "Trading Bot no está ejecutándose", start_time)
                    
            except subprocess.TimeoutExpired:
                return self._create_health_result("unhealthy", "Timeout verificando Trading Bot", start_time)
            except Exception as e:
                return self._create_health_result("unhealthy", f"Error verificando Trading Bot: {e}", start_time)
                
        except Exception as e:
            return self._create_health_result("error", f"Error verificando Trading Bot: {e}", time.time())
    
    def _check_tcp_connection(self, host: str, port: int) -> bool:
        """Verificar conexión TCP"""
        try:
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False
    
    def _create_health_result(self, status: str, message: str, start_time: float) -> Dict[str, Any]:
        """Crear resultado de health check"""
        return {
            "status": status,
            "message": message,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_overall_status(self, results: Dict[str, Any]) -> str:
        """Calcular estado general"""
        try:
            statuses = [result["status"] for result in results.values()]
            
            if "error" in statuses:
                return "error"
            elif "unhealthy" in statuses:
                return "unhealthy"
            elif all(status == "healthy" for status in statuses):
                return "healthy"
            else:
                return "unknown"
                
        except Exception:
            return "unknown"
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generar resumen de health checks"""
        try:
            total_services = len(results)
            healthy_services = sum(1 for result in results.values() if result["status"] == "healthy")
            unhealthy_services = sum(1 for result in results.values() if result["status"] == "unhealthy")
            error_services = sum(1 for result in results.values() if result["status"] == "error")
            
            avg_response_time = sum(result["response_time_ms"] for result in results.values()) / total_services
            
            return {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": unhealthy_services,
                "error_services": error_services,
                "avg_response_time_ms": round(avg_response_time, 2),
                "health_percentage": round((healthy_services / total_services) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return {}
    
    def run_continuous_health_check(self, duration_minutes: int = 60):
        """Ejecutar health checks continuos"""
        try:
            logger.info(f"Iniciando health checks continuos por {duration_minutes} minutos...")
            
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)
            
            while time.time() < end_time:
                # Ejecutar health check
                report = self.check_all_services()
                
                # Mostrar resumen
                self._display_health_summary(report)
                
                # Esperar antes del siguiente check
                time.sleep(self.interval_seconds)
            
            logger.info("Health checks continuos completados")
            
        except KeyboardInterrupt:
            logger.info("Health checks continuos interrumpidos por el usuario")
        except Exception as e:
            logger.error(f"Error en health checks continuos: {e}")
    
    def _display_health_summary(self, report: Dict[str, Any]):
        """Mostrar resumen de salud"""
        try:
            print(f"\n=== HEALTH CHECK - {report['timestamp']} ===")
            print(f"Estado general: {report['overall_status'].upper()}")
            
            if 'summary' in report:
                summary = report['summary']
                print(f"Servicios saludables: {summary['healthy_services']}/{summary['total_services']}")
                print(f"Porcentaje de salud: {summary['health_percentage']}%")
                print(f"Tiempo promedio de respuesta: {summary['avg_response_time_ms']}ms")
            
            print("\nEstado de servicios:")
            for service, result in report['services'].items():
                status_icon = "✓" if result['status'] == 'healthy' else "✗" if result['status'] == 'unhealthy' else "?"
                print(f"  {status_icon} {service.upper()}: {result['message']} ({result['response_time_ms']}ms)")
            
        except Exception as e:
            logger.error(f"Error mostrando resumen de salud: {e}")
    
    def save_health_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Guardar reporte de salud"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"health_report_{timestamp}.json"
            
            # Crear directorio de reportes si no existe
            reports_dir = Path("reports/health")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar reporte
            report_path = reports_dir / filename
            
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de salud guardado: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error guardando reporte de salud: {e}")
            return ""

def main():
    """Función principal"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="Verificador de salud enterprise")
        parser.add_argument("action", choices=["check", "continuous"], 
                          help="Acción a realizar")
        parser.add_argument("--duration", type=int, default=60,
                          help="Duración en minutos para health checks continuos")
        parser.add_argument("--save", action="store_true",
                          help="Guardar reporte de salud")
        
        args = parser.parse_args()
        
        checker = HealthChecker()
        
        if args.action == "check":
            report = checker.check_all_services()
            checker._display_health_summary(report)
            
            if args.save:
                checker.save_health_report(report)
            
            # Determinar código de salida
            if report["overall_status"] == "healthy":
                sys.exit(0)
            else:
                sys.exit(1)
                
        elif args.action == "continuous":
            checker.run_continuous_health_check(args.duration)
            
    except Exception as e:
        logger.error(f"Error en función principal: {e}")
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
