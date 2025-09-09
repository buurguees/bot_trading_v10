#!/usr/bin/env python3
"""
Script Principal de Monitoreo Enterprise - Fase 3C
=================================================

Este script lanza el sistema completo de monitoreo enterprise incluyendo:
- Monitoreo de trading en tiempo real
- Monitoreo de riesgo
- Monitoreo de performance
- Seguimiento de PnL
- Cumplimiento regulatorio
- Dashboards de Grafana

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from monitoring.enterprise.trading_monitor import TradingMonitor
from monitoring.enterprise.risk_monitor import RiskMonitor
from monitoring.enterprise.performance_monitor import PerformanceMonitor
from monitoring.enterprise.pnl_tracker import PnLTracker
from compliance.enterprise.audit_logger import AuditLogger
from compliance.enterprise.trade_reporting import TradeReporting
from compliance.enterprise.risk_reporting import RiskReporting
from compliance.enterprise.regulatory_compliance import RegulatoryCompliance
from config.config_loader import user_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/monitoring/enterprise_monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnterpriseMonitoringSystem:
    """Sistema principal de monitoreo enterprise"""
    
    def __init__(self):
        self.is_running = False
        self.components = {}
        self.tasks = []
        
        # Configuración
        self.config = user_config.get_value(['monitoring_enterprise'], {})
        
        logger.info("🏢 Enterprise Monitoring System inicializado")
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("🔧 Inicializando componentes enterprise...")
            
            # Inicializar componentes de monitoreo
            self.components['trading_monitor'] = TradingMonitor()
            self.components['risk_monitor'] = RiskMonitor()
            self.components['performance_monitor'] = PerformanceMonitor()
            self.components['pnl_tracker'] = PnLTracker()
            
            # Inicializar componentes de compliance
            self.components['audit_logger'] = AuditLogger()
            self.components['trade_reporting'] = TradeReporting()
            self.components['risk_reporting'] = RiskReporting()
            self.components['regulatory_compliance'] = RegulatoryCompliance()
            
            # Inicializar cada componente
            for name, component in self.components.items():
                if hasattr(component, 'initialize'):
                    await component.initialize()
                    logger.info(f"✅ {name} inicializado")
            
            logger.info("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    async def start_monitoring(self):
        """Inicia el monitoreo de todos los componentes"""
        try:
            logger.info("🚀 Iniciando monitoreo enterprise...")
            
            self.is_running = True
            
            # Crear tareas para cada componente
            if 'trading_monitor' in self.components:
                task = asyncio.create_task(
                    self.components['trading_monitor'].start_monitoring()
                )
                self.tasks.append(task)
            
            if 'risk_monitor' in self.components:
                task = asyncio.create_task(
                    self.components['risk_monitor'].start_monitoring()
                )
                self.tasks.append(task)
            
            if 'performance_monitor' in self.components:
                task = asyncio.create_task(
                    self.components['performance_monitor'].start_monitoring()
                )
                self.tasks.append(task)
            
            if 'pnl_tracker' in self.components:
                task = asyncio.create_task(
                    self.components['pnl_tracker'].start_tracking()
                )
                self.tasks.append(task)
            
            # Esperar a que todas las tareas terminen
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
        finally:
            self.is_running = False
    
    async def stop_monitoring(self):
        """Detiene el monitoreo de todos los componentes"""
        try:
            logger.info("⏹️ Deteniendo monitoreo enterprise...")
            
            self.is_running = False
            
            # Detener cada componente
            for name, component in self.components.items():
                if hasattr(component, 'stop_monitoring'):
                    await component.stop_monitoring()
                elif hasattr(component, 'stop_tracking'):
                    await component.stop_tracking()
                elif hasattr(component, 'close'):
                    await component.close()
                logger.info(f"✅ {name} detenido")
            
            # Cancelar todas las tareas
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            logger.info("✅ Monitoreo enterprise detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo monitoreo: {e}")
    
    async def generate_reports(self):
        """Genera reportes de compliance y riesgo"""
        try:
            logger.info("📊 Generando reportes enterprise...")
            
            # Generar reporte de cumplimiento
            if 'regulatory_compliance' in self.components:
                compliance_report = await self.components['regulatory_compliance'].check_compliance()
                logger.info(f"✅ Reporte de cumplimiento generado: {compliance_report.report_id}")
            
            # Generar reporte de riesgo
            if 'risk_reporting' in self.components:
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                risk_report = await self.components['risk_reporting'].generate_risk_report(
                    start_date, end_date
                )
                logger.info(f"✅ Reporte de riesgo generado: {risk_report.report_id}")
            
            # Generar reporte de trades
            if 'trade_reporting' in self.components:
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                trade_report = await self.components['trade_reporting'].generate_trade_report(
                    start_date, end_date
                )
                logger.info(f"✅ Reporte de trades generado: {trade_report}")
            
        except Exception as e:
            logger.error(f"❌ Error generando reportes: {e}")
    
    def get_status(self):
        """Obtiene el estado del sistema"""
        try:
            status = {
                'is_running': self.is_running,
                'components': {},
                'uptime': datetime.now().isoformat() if self.is_running else None
            }
            
            for name, component in self.components.items():
                if hasattr(component, 'get_current_metrics'):
                    status['components'][name] = 'monitoring'
                elif hasattr(component, 'get_current_summary'):
                    status['components'][name] = 'tracking'
                else:
                    status['components'][name] = 'ready'
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {'error': str(e)}

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Sistema de Monitoreo Enterprise - Fase 3C",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run_enterprise_monitoring.py --mode monitoring
  python run_enterprise_monitoring.py --mode reports
  python run_enterprise_monitoring.py --mode status
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['monitoring', 'reports', 'status'],
        default='monitoring',
        help='Modo de operación'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=0,
        help='Duración en minutos (0 = indefinido)'
    )
    
    args = parser.parse_args()
    
    # Crear sistema de monitoreo
    monitoring_system = EnterpriseMonitoringSystem()
    
    # Configurar manejador de señales para shutdown graceful
    def signal_handler(signum, frame):
        logger.info(f"🛑 Señal {signum} recibida, iniciando shutdown...")
        asyncio.create_task(monitoring_system.stop_monitoring())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.mode == 'monitoring':
            # Inicializar sistema
            if not await monitoring_system.initialize():
                logger.error("❌ Error inicializando sistema")
                return 1
            
            # Iniciar monitoreo
            if args.duration > 0:
                logger.info(f"⏰ Monitoreo por {args.duration} minutos")
                await asyncio.wait_for(
                    monitoring_system.start_monitoring(),
                    timeout=args.duration * 60
                )
            else:
                logger.info("♾️ Monitoreo continuo iniciado")
                await monitoring_system.start_monitoring()
        
        elif args.mode == 'reports':
            # Inicializar sistema
            if not await monitoring_system.initialize():
                logger.error("❌ Error inicializando sistema")
                return 1
            
            # Generar reportes
            await monitoring_system.generate_reports()
        
        elif args.mode == 'status':
            # Mostrar estado
            status = monitoring_system.get_status()
            print("📊 Estado del Sistema Enterprise:")
            print(f"  Ejecutándose: {status.get('is_running', False)}")
            print(f"  Componentes: {status.get('components', {})}")
            print(f"  Uptime: {status.get('uptime', 'N/A')}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupción del usuario")
        return 0
    except Exception as e:
        logger.error(f"❌ Error en sistema principal: {e}")
        return 1
    finally:
        # Limpiar recursos
        await monitoring_system.stop_monitoring()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
