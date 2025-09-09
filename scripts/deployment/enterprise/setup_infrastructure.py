# setup_infrastructure.py - Script de configuración de infraestructura enterprise
# Ubicación: C:\TradingBot_v10\scripts\enterprise\setup_infrastructure.py

import os
import sys
import json
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

class InfrastructureSetup:
    """Configurador de infraestructura enterprise"""
    
    def __init__(self):
        """Inicializar el configurador"""
        self.config = get_enterprise_config()
        self.infrastructure_config = self.config.get_infrastructure_config()
        
        # Configuración de Docker
        self.docker_config = self.infrastructure_config.get("docker", {})
        self.compose_file = self.docker_config.get("compose_file", "docker/docker-compose.enterprise.yml")
        
        # Configuración de servicios
        self.kafka_config = self.config.get_kafka_config()
        self.redis_config = self.config.get_redis_config()
        self.timescaledb_config = self.config.get_timescaledb_config()
        self.prometheus_config = self.config.get_prometheus_config()
        self.grafana_config = self.config.get_grafana_config()
        
        # Estado del setup
        self.setup_status = {
            "docker_installed": False,
            "docker_compose_installed": False,
            "services_started": False,
            "health_checks_passed": False,
            "setup_completed": False
        }
        
        logger.info("InfrastructureSetup inicializado")
    
    def check_prerequisites(self) -> bool:
        """Verificar prerrequisitos del sistema"""
        try:
            logger.info("Verificando prerrequisitos...")
            
            # Verificar Docker
            if self._check_docker():
                self.setup_status["docker_installed"] = True
                logger.info("✓ Docker está instalado")
            else:
                logger.error("✗ Docker no está instalado")
                return False
            
            # Verificar Docker Compose
            if self._check_docker_compose():
                self.setup_status["docker_compose_installed"] = True
                logger.info("✓ Docker Compose está instalado")
            else:
                logger.error("✗ Docker Compose no está instalado")
                return False
            
            # Verificar archivos de configuración
            if self._check_config_files():
                logger.info("✓ Archivos de configuración encontrados")
            else:
                logger.error("✗ Archivos de configuración faltantes")
                return False
            
            # Verificar puertos disponibles
            if self._check_ports():
                logger.info("✓ Puertos disponibles")
            else:
                logger.error("✗ Puertos no disponibles")
                return False
            
            logger.info("Todos los prerrequisitos verificados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error verificando prerrequisitos: {e}")
            return False
    
    def _check_docker(self) -> bool:
        """Verificar si Docker está instalado"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_docker_compose(self) -> bool:
        """Verificar si Docker Compose está instalado"""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_config_files(self) -> bool:
        """Verificar archivos de configuración"""
        try:
            required_files = [
                self.compose_file,
                "config/enterprise/infrastructure.yaml",
                "config/enterprise/data_collection.yaml",
                "config/enterprise/security.yaml",
                "config/enterprise/monitoring.yaml",
                "monitoring/prometheus/prometheus.yml",
                "monitoring/prometheus/rules/trading_bot_rules.yml"
            ]
            
            for file_path in required_files:
                if not Path(file_path).exists():
                    logger.error(f"Archivo faltante: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando archivos de configuración: {e}")
            return False
    
    def _check_ports(self) -> bool:
        """Verificar puertos disponibles"""
        try:
            required_ports = [
                9092,  # Kafka
                6379,  # Redis
                5432,  # TimescaleDB
                9090,  # Prometheus
                3000,  # Grafana
                8000,  # Trading Bot
                8001,  # Data Collection
                8002,  # ML Training
                8003   # Trading Engine
            ]
            
            import socket
            
            for port in required_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    logger.warning(f"Puerto {port} ya está en uso")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando puertos: {e}")
            return False
    
    def create_directories(self):
        """Crear directorios necesarios"""
        try:
            logger.info("Creando directorios...")
            
            directories = [
                "data/realtime/raw_ticks",
                "data/realtime/processed_data",
                "data/realtime/daily_backups",
                "data/realtime/metadata",
                "logs/enterprise/infrastructure",
                "logs/enterprise/data_collection",
                "logs/enterprise/security",
                "logs/enterprise/monitoring",
                "backups/enterprise",
                "temp/enterprise",
                "security/keys",
                "security/vault",
                "reports/compliance"
            ]
            
            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.info(f"✓ Directorio creado: {directory}")
            
            logger.info("Todos los directorios creados exitosamente")
            
        except Exception as e:
            logger.error(f"Error creando directorios: {e}")
            raise
    
    def setup_environment(self):
        """Configurar variables de entorno"""
        try:
            logger.info("Configurando variables de entorno...")
            
            # Crear archivo .env
            env_content = f"""# Trading Bot Enterprise Environment Variables
# Generated on {datetime.now().isoformat()}

# TimescaleDB
TIMESCALEDB_PASSWORD=trading_bot_password

# Grafana
GRAFANA_PASSWORD=admin123

# Redis
REDIS_PASSWORD=

# Kafka
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
KAFKA_BROKER_ID=1

# Trading Bot
TRADING_BOT_ENVIRONMENT=development
TRADING_BOT_LOG_LEVEL=INFO
"""
            
            with open(".env", "w") as f:
                f.write(env_content)
            
            logger.info("✓ Archivo .env creado")
            
        except Exception as e:
            logger.error(f"Error configurando variables de entorno: {e}")
            raise
    
    def start_services(self) -> bool:
        """Iniciar servicios Docker"""
        try:
            logger.info("Iniciando servicios Docker...")
            
            # Comando Docker Compose
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
                self.setup_status["services_started"] = True
                logger.info("✓ Servicios Docker iniciados exitosamente")
                return True
            else:
                logger.error(f"Error iniciando servicios: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error iniciando servicios: {e}")
            return False
    
    def wait_for_services(self, timeout: int = 300):
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
    
    def run_health_checks(self) -> bool:
        """Ejecutar verificaciones de salud"""
        try:
            logger.info("Ejecutando verificaciones de salud...")
            
            health_checks = [
                ("Kafka", "localhost:9092"),
                ("Redis", "localhost:6379"),
                ("TimescaleDB", "localhost:5432"),
                ("Prometheus", "localhost:9090"),
                ("Grafana", "localhost:3000")
            ]
            
            all_healthy = True
            
            for service_name, endpoint in health_checks:
                if self._check_service_health(endpoint):
                    logger.info(f"✓ {service_name} está saludable")
                else:
                    logger.error(f"✗ {service_name} no está saludable")
                    all_healthy = False
            
            if all_healthy:
                self.setup_status["health_checks_passed"] = True
                logger.info("✓ Todas las verificaciones de salud pasaron")
            else:
                logger.error("✗ Algunas verificaciones de salud fallaron")
            
            return all_healthy
            
        except Exception as e:
            logger.error(f"Error ejecutando verificaciones de salud: {e}")
            return False
    
    def create_kafka_topics(self):
        """Crear topics de Kafka"""
        try:
            logger.info("Creando topics de Kafka...")
            
            topics = [
                "market_ticks",
                "processed_data",
                "alerts",
                "dead_letter_queue"
            ]
            
            for topic in topics:
                cmd = [
                    "docker", "exec", "trading_bot_kafka",
                    "kafka-topics", "--create",
                    "--topic", topic,
                    "--bootstrap-server", "localhost:9092",
                    "--partitions", "10",
                    "--replication-factor", "1"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ Topic creado: {topic}")
                else:
                    logger.warning(f"Topic {topic} ya existe o error: {result.stderr}")
            
            logger.info("Topics de Kafka configurados")
            
        except Exception as e:
            logger.error(f"Error creando topics de Kafka: {e}")
    
    def setup_database(self):
        """Configurar base de datos"""
        try:
            logger.info("Configurando base de datos...")
            
            # Esperar a que TimescaleDB esté listo
            logger.info("Esperando a que TimescaleDB esté listo...")
            time.sleep(30)
            
            # Verificar conexión
            if self._check_service_health("localhost:5432"):
                logger.info("✓ TimescaleDB está listo")
            else:
                logger.error("✗ TimescaleDB no está listo")
                return False
            
            logger.info("Base de datos configurada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error configurando base de datos: {e}")
            return False
    
    def generate_setup_report(self) -> str:
        """Generar reporte de configuración"""
        try:
            report = {
                "setup_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": self.setup_status,
                "configuration": {
                    "kafka": self.kafka_config,
                    "redis": self.redis_config,
                    "timescaledb": self.timescaledb_config,
                    "prometheus": self.prometheus_config,
                    "grafana": self.grafana_config
                },
                "services": {
                    "kafka": "localhost:9092",
                    "redis": "localhost:6379",
                    "timescaledb": "localhost:5432",
                    "prometheus": "localhost:9090",
                    "grafana": "localhost:3000"
                }
            }
            
            # Guardar reporte
            report_path = f"reports/setup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de configuración generado: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generando reporte de configuración: {e}")
            return ""
    
    def run_complete_setup(self) -> bool:
        """Ejecutar configuración completa"""
        try:
            logger.info("=== INICIANDO CONFIGURACIÓN DE INFRAESTRUCTURA ENTERPRISE ===")
            
            # 1. Verificar prerrequisitos
            if not self.check_prerequisites():
                logger.error("Prerrequisitos no cumplidos")
                return False
            
            # 2. Crear directorios
            self.create_directories()
            
            # 3. Configurar variables de entorno
            self.setup_environment()
            
            # 4. Iniciar servicios
            if not self.start_services():
                logger.error("Error iniciando servicios")
                return False
            
            # 5. Esperar servicios
            if not self.wait_for_services():
                logger.error("Timeout esperando servicios")
                return False
            
            # 6. Verificaciones de salud
            if not self.run_health_checks():
                logger.error("Verificaciones de salud fallaron")
                return False
            
            # 7. Crear topics de Kafka
            self.create_kafka_topics()
            
            # 8. Configurar base de datos
            if not self.setup_database():
                logger.error("Error configurando base de datos")
                return False
            
            # 9. Generar reporte
            report_path = self.generate_setup_report()
            
            # 10. Marcar como completado
            self.setup_status["setup_completed"] = True
            
            logger.info("=== CONFIGURACIÓN COMPLETADA EXITOSAMENTE ===")
            logger.info(f"Reporte generado: {report_path}")
            logger.info("Servicios disponibles:")
            logger.info("  - Kafka: http://localhost:9092")
            logger.info("  - Redis: localhost:6379")
            logger.info("  - TimescaleDB: localhost:5432")
            logger.info("  - Prometheus: http://localhost:9090")
            logger.info("  - Grafana: http://localhost:3000")
            
            return True
            
        except Exception as e:
            logger.error(f"Error en configuración completa: {e}")
            return False

def main():
    """Función principal"""
    try:
        setup = InfrastructureSetup()
        success = setup.run_complete_setup()
        
        if success:
            print("\n✅ Configuración de infraestructura completada exitosamente")
            sys.exit(0)
        else:
            print("\n❌ Error en la configuración de infraestructura")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error en función principal: {e}")
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
