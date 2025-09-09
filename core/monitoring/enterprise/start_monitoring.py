# Ruta: core/monitoring/enterprise/start_monitoring.py
# start_monitoring.py - Iniciador del sistema de monitoreo
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\start_monitoring.py

"""
Script principal para iniciar el sistema de monitoreo enterprise.

Características:
- Inicia todos los componentes de monitoreo
- Configuración automática
- Health checks
- Logging centralizado
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import argparse
from datetime import datetime

# Imports del sistema de monitoreo
from .training_monitor import create_training_monitor
from .performance_analyzer import create_performance_analyzer
from .alert_manager import create_alert_manager, AlertSeverity
from .metrics_collector import create_metrics_collector
from .dashboard_generator import create_dashboard_generator
from .mlflow_integration import create_mlflow_integration

class MonitoringSystem:
    """Sistema de monitoreo enterprise"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/enterprise/monitoring.yaml"
        self.config = self._load_config()
        
        # Componentes del sistema
        self.training_monitor = None
        self.performance_analyzer = None
        self.alert_manager = None
        self.metrics_collector = None
        self.dashboard_generator = None
        self.mlflow_integration = None
        
        # Estado del sistema
        self.is_running = False
        self.start_time = None
        
        # Configurar logging
        self.setup_logging()
        
        # Configurar signal handlers
        self.setup_signal_handlers()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'monitoring': {
                'enabled': True,
                'components': {
                    'training_monitor': True,
                    'performance_analyzer': True,
                    'alert_manager': True,
                    'metrics_collector': True,
                    'dashboard_generator': True,
                    'mlflow_integration': True
                }
            },
            'prometheus': {
                'port': 8000,
                'enabled': True
            },
            'grafana': {
                'url': 'http://localhost:3000',
                'api_key': None,
                'enabled': True
            },
            'mlflow': {
                'tracking_uri': 'http://localhost:5000',
                'experiment_name': 'trading_bot_experiments',
                'enabled': True
            }
        }
    
    def setup_logging(self):
        """Configura logging del sistema"""
        # Crear directorio de logs
        logs_dir = Path("logs/enterprise/monitoring")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / "monitoring_system.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def setup_signal_handlers(self):
        """Configura handlers para graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Señal {signum} recibida. Iniciando shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Inicia el sistema de monitoreo"""
        if self.is_running:
            self.logger.warning("El sistema de monitoreo ya está ejecutándose")
            return
        
        try:
            self.logger.info("🚀 Iniciando sistema de monitoreo enterprise")
            self.start_time = datetime.now()
            
            # Inicializar componentes según configuración
            await self._initialize_components()
            
            # Iniciar componentes
            await self._start_components()
            
            # Configurar como ejecutándose
            self.is_running = True
            
            self.logger.info("✅ Sistema de monitoreo iniciado exitosamente")
            
            # Mantener el sistema ejecutándose
            await self._run_forever()
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando sistema de monitoreo: {e}")
            await self.stop()
            raise
    
    async def _initialize_components(self):
        """Inicializa componentes del sistema"""
        self.logger.info("🔧 Inicializando componentes...")
        
        # Training Monitor
        if self.config.get('monitoring', {}).get('components', {}).get('training_monitor', True):
            self.training_monitor = create_training_monitor()
            self.logger.info("✅ Training Monitor inicializado")
        
        # Performance Analyzer
        if self.config.get('monitoring', {}).get('components', {}).get('performance_analyzer', True):
            self.performance_analyzer = create_performance_analyzer()
            self.logger.info("✅ Performance Analyzer inicializado")
        
        # Alert Manager
        if self.config.get('monitoring', {}).get('components', {}).get('alert_manager', True):
            self.alert_manager = create_alert_manager()
            await self.alert_manager.start()
            self.logger.info("✅ Alert Manager inicializado")
        
        # Metrics Collector
        if self.config.get('monitoring', {}).get('components', {}).get('metrics_collector', True):
            prometheus_port = self.config.get('prometheus', {}).get('port', 8000)
            self.metrics_collector = create_metrics_collector(prometheus_port=prometheus_port)
            self.logger.info("✅ Metrics Collector inicializado")
        
        # Dashboard Generator
        if self.config.get('monitoring', {}).get('components', {}).get('dashboard_generator', True):
            grafana_url = self.config.get('grafana', {}).get('url', 'http://localhost:3000')
            grafana_api_key = self.config.get('grafana', {}).get('api_key')
            self.dashboard_generator = create_dashboard_generator(grafana_url, grafana_api_key)
            self.logger.info("✅ Dashboard Generator inicializado")
        
        # MLflow Integration
        if self.config.get('monitoring', {}).get('components', {}).get('mlflow_integration', True):
            mlflow_config = self.config.get('mlflow', {})
            tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')
            experiment_name = mlflow_config.get('experiment_name', 'trading_bot_experiments')
            self.mlflow_integration = create_mlflow_integration(tracking_uri, experiment_name)
            self.logger.info("✅ MLflow Integration inicializado")
    
    async def _start_components(self):
        """Inicia componentes del sistema"""
        self.logger.info("🚀 Iniciando componentes...")
        
        # Iniciar Performance Analyzer
        if self.performance_analyzer:
            self.performance_analyzer.start_monitoring()
            self.logger.info("✅ Performance Analyzer iniciado")
        
        # Iniciar Metrics Collector
        if self.metrics_collector:
            self.metrics_collector.start_collection()
            self.logger.info("✅ Metrics Collector iniciado")
        
        # Generar dashboards
        if self.dashboard_generator:
            self.dashboard_generator.generate_all_dashboards()
            self.logger.info("✅ Dashboards generados")
    
    async def _run_forever(self):
        """Mantiene el sistema ejecutándose"""
        try:
            while self.is_running:
                # Health check de componentes
                await self._health_check()
                
                # Esperar antes del siguiente check
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            self.logger.info("Sistema de monitoreo cancelado")
        except Exception as e:
            self.logger.error(f"Error en loop principal: {e}")
    
    async def _health_check(self):
        """Realiza health check de componentes"""
        try:
            # Verificar estado de componentes
            components_status = {
                'training_monitor': self.training_monitor is not None,
                'performance_analyzer': self.performance_analyzer is not None and self.performance_analyzer.is_monitoring,
                'alert_manager': self.alert_manager is not None and self.alert_manager.is_running,
                'metrics_collector': self.metrics_collector is not None and self.metrics_collector.is_collecting,
                'dashboard_generator': self.dashboard_generator is not None,
                'mlflow_integration': self.mlflow_integration is not None
            }
            
            # Log estado de componentes
            for component, status in components_status.items():
                if not status:
                    self.logger.warning(f"⚠️ Componente {component} no está funcionando correctamente")
            
            # Enviar alerta si hay problemas
            if self.alert_manager and not all(components_status.values()):
                await self.alert_manager.create_alert(
                    title="Sistema de Monitoreo - Componente Fallido",
                    message=f"Componentes con problemas: {[k for k, v in components_status.items() if not v]}",
                    severity=AlertSeverity.WARNING,
                    source="monitoring_system"
                )
            
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
    
    async def stop(self):
        """Detiene el sistema de monitoreo"""
        if not self.is_running:
            return
        
        self.logger.info("🛑 Deteniendo sistema de monitoreo...")
        
        try:
            # Detener componentes
            if self.performance_analyzer:
                self.performance_analyzer.stop_monitoring()
                self.logger.info("✅ Performance Analyzer detenido")
            
            if self.metrics_collector:
                self.metrics_collector.stop_collection()
                self.logger.info("✅ Metrics Collector detenido")
            
            if self.alert_manager:
                await self.alert_manager.stop()
                self.logger.info("✅ Alert Manager detenido")
            
            # Configurar como detenido
            self.is_running = False
            
            # Calcular tiempo de ejecución
            if self.start_time:
                duration = datetime.now() - self.start_time
                self.logger.info(f"⏱️ Sistema ejecutado por {duration}")
            
            self.logger.info("✅ Sistema de monitoreo detenido exitosamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo sistema de monitoreo: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtiene estado del sistema"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'components': {
                'training_monitor': self.training_monitor is not None,
                'performance_analyzer': self.performance_analyzer is not None,
                'alert_manager': self.alert_manager is not None,
                'metrics_collector': self.metrics_collector is not None,
                'dashboard_generator': self.dashboard_generator is not None,
                'mlflow_integration': self.mlflow_integration is not None
            },
            'config': self.config
        }

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Sistema de Monitoreo Enterprise')
    parser.add_argument('--config', type=str, help='Ruta al archivo de configuración')
    parser.add_argument('--daemon', action='store_true', help='Ejecutar como daemon')
    
    args = parser.parse_args()
    
    # Crear sistema de monitoreo
    monitoring_system = MonitoringSystem(args.config)
    
    try:
        # Iniciar sistema
        await monitoring_system.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupción recibida. Deteniendo sistema...")
        await monitoring_system.stop()
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        await monitoring_system.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())