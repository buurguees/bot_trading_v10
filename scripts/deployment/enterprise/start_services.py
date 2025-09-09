# start_services.py - Script para iniciar servicios enterprise
# Ubicación: C:\TradingBot_v10\scripts\enterprise\start_services.py

import os
import sys
import logging
import subprocess
import time
from datetime import datetime, timezone
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

class ServiceManager:
    """Gestor de servicios enterprise"""
    
    def __init__(self):
        """Inicializar el gestor de servicios"""
        self.config = get_enterprise_config()
        self.infrastructure_config = self.config.get_infrastructure_config()
        
        # Configuración de Docker
        self.docker_config = self.infrastructure_config.get("docker", {})
        self.compose_file = self.docker_config.get("compose_file", "docker/docker-compose.enterprise.yml")
        
        # Estado de servicios
        self.services_status = {
            "kafka": False,
            "redis": False,
            "timescaledb": False,
            "prometheus": False,
            "grafana": False,
            "kafka_exporter": False,
            "redis_exporter": False,
            "node_exporter": False,
            "alertmanager": False
        }
        
        logger.info("ServiceManager inicializado")
    
    def start_all_services(self) -> bool:
        """Iniciar todos los servicios"""
        try:
            logger.info("=== INICIANDO SERVICIOS ENTERPRISE ===")
            
            # Verificar que Docker esté ejecutándose
            if not self._check_docker_running():
                logger.error("Docker no está ejecutándose")
                return False
            
            # Iniciar servicios con Docker Compose
            if not self._start_docker_services():
                logger.error("Error iniciando servicios Docker")
                return False
            
            # Esperar a que los servicios estén listos
            if not self._wait_for_services():
                logger.error("Timeout esperando servicios")
                return False
            
            # Verificar estado de servicios
            self._check_services_status()
            
            # Mostrar resumen
            self._show_services_summary()
            
            logger.info("=== SERVICIOS INICIADOS EXITOSAMENTE ===")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando servicios: {e}")
            return False
    
    def start_specific_services(self, services: List[str]) -> bool:
        """Iniciar servicios específicos"""
        try:
            logger.info(f"Iniciando servicios específicos: {services}")
            
            # Verificar que Docker esté ejecutándose
            if not self._check_docker_running():
                logger.error("Docker no está ejecutándose")
                return False
            
            # Iniciar servicios específicos
            for service in services:
                if not self._start_service(service):
                    logger.error(f"Error iniciando servicio {service}")
                    return False
            
            # Esperar a que los servicios estén listos
            if not self._wait_for_services():
                logger.error("Timeout esperando servicios")
                return False
            
            # Verificar estado de servicios
            self._check_services_status()
            
            logger.info("Servicios específicos iniciados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando servicios específicos: {e}")
            return False
    
    def stop_all_services(self) -> bool:
        """Detener todos los servicios"""
        try:
            logger.info("=== DETENIENDO SERVICIOS ENTERPRISE ===")
            
            # Detener servicios con Docker Compose
            cmd = [
                "docker-compose",
                "-f", self.compose_file,
                "down"
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✓ Servicios detenidos exitosamente")
                return True
            else:
                logger.error(f"Error deteniendo servicios: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error deteniendo servicios: {e}")
            return False
    
    def restart_services(self) -> bool:
        """Reiniciar todos los servicios"""
        try:
            logger.info("=== REINICIANDO SERVICIOS ENTERPRISE ===")
            
            # Detener servicios
            if not self.stop_all_services():
                logger.error("Error deteniendo servicios")
                return False
            
            # Esperar un momento
            time.sleep(5)
            
            # Iniciar servicios
            if not self.start_all_services():
                logger.error("Error iniciando servicios")
                return False
            
            logger.info("Servicios reiniciados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error reiniciando servicios: {e}")
            return False
    
    def _check_docker_running(self) -> bool:
        """Verificar que Docker esté ejecutándose"""
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _start_docker_services(self) -> bool:
        """Iniciar servicios con Docker Compose"""
        try:
            cmd = [
                "docker-compose",
                "-f", self.compose_file,
                "up", "-d"
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos
            )
            
            if result.returncode == 0:
                logger.info("✓ Servicios Docker iniciados")
                return True
            else:
                logger.error(f"Error iniciando servicios Docker: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error iniciando servicios Docker: {e}")
            return False
    
    def _start_service(self, service: str) -> bool:
        """Iniciar un servicio específico"""
        try:
            cmd = [
                "docker-compose",
                "-f", self.compose_file,
                "up", "-d", service
            ]
            
            logger.info(f"Iniciando servicio {service}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service} iniciado")
                return True
            else:
                logger.error(f"Error iniciando servicio {service}: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error iniciando servicio {service}: {e}")
            return False
    
    def _wait_for_services(self, timeout: int = 300) -> bool:
        """Esperar a que los servicios estén listos"""
        try:
            logger.info("Esperando a que los servicios estén listos...")
            
            services = [
                ("Kafka", "localhost:9092"),
                ("Redis", "localhost:6379"),
                ("TimescaleDB", "localhost:5432"),
                ("Prometheus", "localhost:9090"),
                ("Grafana", "localhost:3000")
            ]
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                all_ready = True
                
                for service_name, endpoint in services:
                    if not self._check_service_health(endpoint):
                        all_ready = False
                        break
                
                if all_ready:
                    logger.info("✓ Todos los servicios están listos")
                    return True
                
                logger.info("Esperando servicios...")
                time.sleep(10)
            
            logger.error("Timeout esperando servicios")
            return False
            
        except Exception as e:
            logger.error(f"Error esperando servicios: {e}")
            return False
    
    def _check_service_health(self, endpoint: str) -> bool:
        """Verificar salud de un servicio"""
        try:
            import socket
            
            host, port = endpoint.split(":")
            port = int(port)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False
    
    def _check_services_status(self):
        """Verificar estado de servicios"""
        try:
            logger.info("Verificando estado de servicios...")
            
            # Verificar servicios principales
            self.services_status["kafka"] = self._check_service_health("localhost:9092")
            self.services_status["redis"] = self._check_service_health("localhost:6379")
            self.services_status["timescaledb"] = self._check_service_health("localhost:5432")
            self.services_status["prometheus"] = self._check_service_health("localhost:9090")
            self.services_status["grafana"] = self._check_service_health("localhost:3000")
            
            # Verificar exporters
            self.services_status["kafka_exporter"] = self._check_service_health("localhost:9308")
            self.services_status["redis_exporter"] = self._check_service_health("localhost:9121")
            self.services_status["node_exporter"] = self._check_service_health("localhost:9100")
            self.services_status["alertmanager"] = self._check_service_health("localhost:9093")
            
        except Exception as e:
            logger.error(f"Error verificando estado de servicios: {e}")
    
    def _show_services_summary(self):
        """Mostrar resumen de servicios"""
        try:
            logger.info("=== RESUMEN DE SERVICIOS ===")
            
            # Servicios principales
            logger.info("Servicios principales:")
            for service, status in self.services_status.items():
                if service in ["kafka", "redis", "timescaledb", "prometheus", "grafana"]:
                    status_icon = "✓" if status else "✗"
                    logger.info(f"  {status_icon} {service.upper()}")
            
            # Exporters
            logger.info("Exporters:")
            for service, status in self.services_status.items():
                if service.endswith("_exporter") or service == "alertmanager":
                    status_icon = "✓" if status else "✗"
                    logger.info(f"  {status_icon} {service.upper()}")
            
            # URLs de acceso
            logger.info("URLs de acceso:")
            logger.info("  - Prometheus: http://localhost:9090")
            logger.info("  - Grafana: http://localhost:3000")
            logger.info("  - Kafka: localhost:9092")
            logger.info("  - Redis: localhost:6379")
            logger.info("  - TimescaleDB: localhost:5432")
            
        except Exception as e:
            logger.error(f"Error mostrando resumen de servicios: {e}")
    
    def get_services_status(self) -> Dict[str, bool]:
        """Obtener estado de servicios"""
        return self.services_status.copy()
    
    def get_services_info(self) -> Dict[str, Any]:
        """Obtener información de servicios"""
        try:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services_status": self.get_services_status(),
                "configuration": {
                    "compose_file": self.compose_file,
                    "kafka_config": self.config.get_kafka_config(),
                    "redis_config": self.config.get_redis_config(),
                    "timescaledb_config": self.config.get_timescaledb_config(),
                    "prometheus_config": self.config.get_prometheus_config(),
                    "grafana_config": self.config.get_grafana_config()
                }
            }
        except Exception as e:
            logger.error(f"Error obteniendo información de servicios: {e}")
            return {}

def main():
    """Función principal"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="Gestor de servicios enterprise")
        parser.add_argument("action", choices=["start", "stop", "restart", "status"], 
                          help="Acción a realizar")
        parser.add_argument("--services", nargs="+", 
                          help="Servicios específicos (solo para start)")
        
        args = parser.parse_args()
        
        manager = ServiceManager()
        
        if args.action == "start":
            if args.services:
                success = manager.start_specific_services(args.services)
            else:
                success = manager.start_all_services()
        elif args.action == "stop":
            success = manager.stop_all_services()
        elif args.action == "restart":
            success = manager.restart_services()
        elif args.action == "status":
            manager._check_services_status()
            manager._show_services_summary()
            success = True
        
        if success:
            print(f"\n✅ Acción '{args.action}' completada exitosamente")
            sys.exit(0)
        else:
            print(f"\n❌ Error en la acción '{args.action}'")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error en función principal: {e}")
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
