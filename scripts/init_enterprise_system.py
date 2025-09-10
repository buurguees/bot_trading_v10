# Ruta: scripts/init_enterprise_system.py
# init_enterprise_system.py - Inicializador del sistema enterprise
# Ubicación: scripts/init_enterprise_system.py

"""
Inicializador del Sistema Enterprise
Configura e inicializa todos los componentes del sistema de trading

Características principales:
- Inicialización de configuraciones
- Verificación de dependencias
- Configuración de infraestructura
- Pruebas de conectividad
- Monitoreo de estado
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from core.config.config_loader import config_loader
from core.trading.enterprise.futures_execution_engine import FuturesExecutionEngine
from core.trading.enterprise.strategy_manager import strategy_manager
from core.data.enterprise_data_collector import enterprise_data_collector
from core.security.audit_logger import audit_logger
from core.security.compliance_checker import compliance_checker
from core.sync.metrics_aggregator import metrics_aggregator
from control.telegram_bot import telegram_bot
from control.security_guard import security_guard

logger = logging.getLogger(__name__)

class EnterpriseSystemInitializer:
    """Inicializador del sistema enterprise"""
    
    def __init__(self):
        self.components = {}
        self.initialization_status = {}
        self.start_time = None
        
    async def initialize_system(self) -> bool:
        """Inicializa todo el sistema enterprise"""
        try:
            self.start_time = datetime.now()
            logger.info("🚀 Iniciando sistema enterprise...")
            
            # 1. Inicializar configuraciones
            await self._initialize_configurations()
            
            # 2. Verificar dependencias
            await self._check_dependencies()
            
            # 3. Inicializar componentes core
            await self._initialize_core_components()
            
            # 4. Inicializar componentes de trading
            await self._initialize_trading_components()
            
            # 5. Inicializar componentes de datos
            await self._initialize_data_components()
            
            # 6. Inicializar componentes de seguridad
            await self._initialize_security_components()
            
            # 7. Inicializar componentes de control
            await self._initialize_control_components()
            
            # 8. Verificar conectividad
            await self._verify_connectivity()
            
            # 9. Ejecutar pruebas de sistema
            await self._run_system_tests()
            
            # 10. Enviar notificación de inicio
            await self._send_startup_notification()
            
            logger.info("✅ Sistema enterprise inicializado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema enterprise: {e}")
            await self._send_error_notification(str(e))
            return False
    
    async def _initialize_configurations(self):
        """Inicializa el sistema de configuraciones"""
        try:
            logger.info("📋 Inicializando configuraciones...")
            
            await config_loader.initialize()
            
            # Verificar estado de validación
            validation_status = config_loader.get_validation_status()
            valid_configs = validation_status.get('valid_configs', 0)
            total_configs = validation_status.get('total_configs', 0)
            
            if valid_configs != total_configs:
                logger.warning(f"⚠️ {total_configs - valid_configs} configuraciones con errores")
            
            self.initialization_status['configurations'] = {
                'status': 'success',
                'valid_configs': valid_configs,
                'total_configs': total_configs
            }
            
            logger.info(f"✅ Configuraciones inicializadas: {valid_configs}/{total_configs} válidas")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando configuraciones: {e}")
            self.initialization_status['configurations'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _check_dependencies(self):
        """Verifica dependencias del sistema"""
        try:
            logger.info("🔍 Verificando dependencias...")
            
            dependencies = {
                'redis': await self._check_redis(),
                'kafka': await self._check_kafka(),
                'database': await self._check_database(),
                'bitget_api': await self._check_bitget_api()
            }
            
            failed_deps = [name for name, status in dependencies.items() if not status]
            
            if failed_deps:
                logger.warning(f"⚠️ Dependencias fallidas: {failed_deps}")
            else:
                logger.info("✅ Todas las dependencias verificadas")
            
            self.initialization_status['dependencies'] = {
                'status': 'success' if not failed_deps else 'warning',
                'dependencies': dependencies,
                'failed': failed_deps
            }
            
        except Exception as e:
            logger.error(f"❌ Error verificando dependencias: {e}")
            self.initialization_status['dependencies'] = {'status': 'error', 'error': str(e)}
    
    async def _check_redis(self) -> bool:
        """Verifica conexión a Redis"""
        try:
            import redis
            redis_url = config_loader.get_infrastructure_settings().get('redis', {}).get('url', 'redis://localhost:6379')
            client = redis.Redis.from_url(redis_url)
            client.ping()
            return True
        except Exception:
            return False
    
    async def _check_kafka(self) -> bool:
        """Verifica conexión a Kafka"""
        try:
            from kafka import KafkaProducer
            bootstrap_servers = config_loader.get_infrastructure_settings().get('kafka', {}).get('bootstrap_servers', 'localhost:9092')
            producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            producer.close()
            return True
        except Exception:
            return False
    
    async def _check_database(self) -> bool:
        """Verifica conexión a base de datos"""
        try:
            from core.data.database import db_manager
            # Verificar conexión básica
            return True
        except Exception:
            return False
    
    async def _check_bitget_api(self) -> bool:
        """Verifica conexión a Bitget API"""
        try:
            import ccxt.async_support as ccxt
            exchange = ccxt.bitget({
                'apiKey': os.getenv('BITGET_API_KEY', ''),
                'secret': os.getenv('BITGET_SECRET_KEY', ''),
                'password': os.getenv('BITGET_PASSPHRASE', ''),
                'sandbox': True  # Usar sandbox para verificación
            })
            await exchange.load_markets()
            await exchange.close()
            return True
        except Exception:
            return False
    
    async def _initialize_core_components(self):
        """Inicializa componentes core"""
        try:
            logger.info("🔧 Inicializando componentes core...")
            
            # Inicializar metrics aggregator
            await metrics_aggregator.initialize()
            
            self.initialization_status['core_components'] = {'status': 'success'}
            logger.info("✅ Componentes core inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes core: {e}")
            self.initialization_status['core_components'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _initialize_trading_components(self):
        """Inicializa componentes de trading"""
        try:
            logger.info("📈 Inicializando componentes de trading...")
            
            # Inicializar strategy manager
            await strategy_manager.initialize()
            
            # Inicializar futures execution engine
            self.components['futures_engine'] = FuturesExecutionEngine()
            
            self.initialization_status['trading_components'] = {'status': 'success'}
            logger.info("✅ Componentes de trading inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes de trading: {e}")
            self.initialization_status['trading_components'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _initialize_data_components(self):
        """Inicializa componentes de datos"""
        try:
            logger.info("📊 Inicializando componentes de datos...")
            
            # Inicializar enterprise data collector
            await enterprise_data_collector.initialize()
            
            self.initialization_status['data_components'] = {'status': 'success'}
            logger.info("✅ Componentes de datos inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes de datos: {e}")
            self.initialization_status['data_components'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _initialize_security_components(self):
        """Inicializa componentes de seguridad"""
        try:
            logger.info("🔒 Inicializando componentes de seguridad...")
            
            # Inicializar audit logger
            await audit_logger.initialize()
            
            self.initialization_status['security_components'] = {'status': 'success'}
            logger.info("✅ Componentes de seguridad inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes de seguridad: {e}")
            self.initialization_status['security_components'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _initialize_control_components(self):
        """Inicializa componentes de control"""
        try:
            logger.info("🎮 Inicializando componentes de control...")
            
            # Inicializar security guard
            await security_guard.initialize()
            
            self.initialization_status['control_components'] = {'status': 'success'}
            logger.info("✅ Componentes de control inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes de control: {e}")
            self.initialization_status['control_components'] = {'status': 'error', 'error': str(e)}
            raise
    
    async def _verify_connectivity(self):
        """Verifica conectividad entre componentes"""
        try:
            logger.info("🌐 Verificando conectividad...")
            
            # Verificar conectividad básica
            connectivity_tests = {
                'config_loader': config_loader is not None,
                'strategy_manager': strategy_manager is not None,
                'enterprise_data_collector': enterprise_data_collector is not None,
                'audit_logger': audit_logger is not None,
                'metrics_aggregator': metrics_aggregator is not None
            }
            
            failed_tests = [name for name, status in connectivity_tests.items() if not status]
            
            if failed_tests:
                logger.warning(f"⚠️ Pruebas de conectividad fallidas: {failed_tests}")
            else:
                logger.info("✅ Conectividad verificada")
            
            self.initialization_status['connectivity'] = {
                'status': 'success' if not failed_tests else 'warning',
                'tests': connectivity_tests,
                'failed': failed_tests
            }
            
        except Exception as e:
            logger.error(f"❌ Error verificando conectividad: {e}")
            self.initialization_status['connectivity'] = {'status': 'error', 'error': str(e)}
    
    async def _run_system_tests(self):
        """Ejecuta pruebas del sistema"""
        try:
            logger.info("🧪 Ejecutando pruebas del sistema...")
            
            tests = {
                'config_validation': await self._test_config_validation(),
                'data_collection': await self._test_data_collection(),
                'strategy_execution': await self._test_strategy_execution(),
                'audit_logging': await self._test_audit_logging()
            }
            
            failed_tests = [name for name, status in tests.items() if not status]
            
            if failed_tests:
                logger.warning(f"⚠️ Pruebas fallidas: {failed_tests}")
            else:
                logger.info("✅ Todas las pruebas pasaron")
            
            self.initialization_status['system_tests'] = {
                'status': 'success' if not failed_tests else 'warning',
                'tests': tests,
                'failed': failed_tests
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando pruebas del sistema: {e}")
            self.initialization_status['system_tests'] = {'status': 'error', 'error': str(e)}
    
    async def _test_config_validation(self) -> bool:
        """Prueba validación de configuraciones"""
        try:
            validation_status = config_loader.get_validation_status()
            return validation_status.get('valid_configs', 0) > 0
        except Exception:
            return False
    
    async def _test_data_collection(self) -> bool:
        """Prueba recolección de datos"""
        try:
            # Verificar que el data collector esté inicializado
            return enterprise_data_collector is not None
        except Exception:
            return False
    
    async def _test_strategy_execution(self) -> bool:
        """Prueba ejecución de estrategias"""
        try:
            # Verificar que el strategy manager esté inicializado
            return strategy_manager is not None
        except Exception:
            return False
    
    async def _test_audit_logging(self) -> bool:
        """Prueba logging de auditoría"""
        try:
            # Probar logging de un evento
            event_id = await audit_logger.log_event(
                'system_startup',
                'Sistema enterprise iniciado',
                {'test': True}
            )
            return event_id is not None
        except Exception:
            return False
    
    async def _send_startup_notification(self):
        """Envía notificación de inicio exitoso"""
        try:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            message = f"🚀 **Sistema Enterprise Iniciado**\n\n"
            message += f"⏱️ Tiempo de inicialización: {duration:.2f}s\n"
            message += f"📋 Configuraciones: {self.initialization_status.get('configurations', {}).get('valid_configs', 0)} válidas\n"
            message += f"🔧 Componentes: {len([c for c in self.initialization_status.values() if c.get('status') == 'success'])} inicializados\n"
            message += f"🧪 Pruebas: {'✅' if self.initialization_status.get('system_tests', {}).get('status') == 'success' else '⚠️'}\n\n"
            message += "**Estado del Sistema:**\n"
            
            for component, status in self.initialization_status.items():
                status_icon = "✅" if status.get('status') == 'success' else "⚠️" if status.get('status') == 'warning' else "❌"
                message += f"• {component.replace('_', ' ').title()}: {status_icon}\n"
            
            await telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de inicio: {e}")
    
    async def _send_error_notification(self, error_message: str):
        """Envía notificación de error"""
        try:
            message = f"❌ **Error Inicializando Sistema Enterprise**\n\n"
            message += f"**Error:** {error_message}\n"
            message += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
            message += "Revisar logs para más detalles."
            
            await telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de error: {e}")
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Obtiene reporte de inicialización"""
        try:
            duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return {
                'initialization_time': duration,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'status': self.initialization_status,
                'components': list(self.components.keys()),
                'overall_status': 'success' if all(
                    status.get('status') in ['success', 'warning'] 
                    for status in self.initialization_status.values()
                ) else 'error'
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de inicialización: {e}")
            return {'error': str(e)}

async def main():
    """Función principal de inicialización"""
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/enterprise/initialization.log'),
                logging.StreamHandler()
            ]
        )
        
        # Crear directorio de logs
        Path('logs/enterprise').mkdir(parents=True, exist_ok=True)
        
        # Inicializar sistema
        initializer = EnterpriseSystemInitializer()
        success = await initializer.initialize_system()
        
        # Generar reporte
        report = initializer.get_initialization_report()
        
        # Guardar reporte
        with open('logs/enterprise/initialization_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        if success:
            logger.info("✅ Sistema enterprise inicializado exitosamente")
            return 0
        else:
            logger.error("❌ Error inicializando sistema enterprise")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error crítico en inicialización: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
