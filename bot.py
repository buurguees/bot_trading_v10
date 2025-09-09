#!/usr/bin/env python3
"""
Bot Trading v10 Enterprise - Ejecutor Principal
===============================================

Sistema de trading enterprise con arquitectura modular y escalable.

Características:
- Trading de futuros con leverage dinámico (5x-30x)
- Machine Learning con LSTM + Attention
- Monitoreo en tiempo real con Prometheus/Grafana
- Cumplimiento regulatorio (MiFID II, GDPR)
- Recuperación automática y gestión de backups
- Arquitectura asíncrona y escalable

Uso:
    python bot.py --mode live --symbols BTCUSDT,ETHUSDT --leverage 10
    python bot.py --mode paper --symbols BTCUSDT,ETHUSDT --leverage 5
    python bot.py --mode emergency-stop

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.deployment.phase_manager import PhaseManager
from src.core.deployment.health_monitor import HealthMonitor
from src.core.config.enterprise_config import EnterpriseConfigManager
from src.scripts.trading.run_enterprise_trading import EnterpriseTradingLauncher

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BotTradingEnterprise:
    """Bot Trading v10 Enterprise - Clase principal"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        self.config_path = config_path
        self.config_manager = EnterpriseConfigManager(config_path)
        self.phase_manager = None
        self.health_monitor = None
        self.trading_launcher = None
        
        # Crear directorio de logs
        Path("logs").mkdir(exist_ok=True)
        
        logger.info("🤖 Bot Trading v10 Enterprise inicializado")
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("🚀 Inicializando sistema enterprise...")
            
            # Cargar configuración
            config = self.config_manager.load_config()
            logger.info("✅ Configuración cargada")
            
            # Inicializar gestor de fases
            self.phase_manager = PhaseManager(config)
            logger.info("✅ Gestor de fases inicializado")
            
            # Inicializar monitor de salud
            self.health_monitor = HealthMonitor(config)
            logger.info("✅ Monitor de salud inicializado")
            
            # Inicializar launcher de trading
            self.trading_launcher = EnterpriseTradingLauncher(config)
            logger.info("✅ Launcher de trading inicializado")
            
            logger.info("🎉 Sistema enterprise inicializado completamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema: {e}")
            raise
    
    async def run_trading(self, mode: str, symbols: List[str], leverage: int = 10):
        """Ejecuta el trading en el modo especificado"""
        try:
            logger.info(f"💰 Iniciando trading en modo {mode}")
            logger.info(f"📊 Símbolos: {', '.join(symbols)}")
            logger.info(f"⚡ Leverage: {leverage}x")
            
            # Validar modo
            if mode not in ['live', 'paper', 'emergency-stop']:
                raise ValueError(f"Modo inválido: {mode}")
            
            # Ejecutar trading
            if mode == 'emergency-stop':
                await self.trading_launcher.emergency_stop()
            else:
                await self.trading_launcher.start_trading(
                    mode=mode,
                    symbols=symbols,
                    leverage=leverage
                )
            
            logger.info(f"✅ Trading en modo {mode} completado")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trading: {e}")
            raise
    
    async def run_system_health_check(self):
        """Ejecuta verificación de salud del sistema"""
        try:
            logger.info("🏥 Verificando salud del sistema...")
            
            health_status = await self.health_monitor.get_system_health()
            
            logger.info(f"📊 Estado general: {health_status.overall_status.value}")
            logger.info(f"📈 Score de salud: {health_status.overall_score:.1f}/100")
            logger.info(f"⚠️ Problemas críticos: {health_status.critical_issues}")
            logger.info(f"⚠️ Advertencias: {health_status.warning_issues}")
            
            # Mostrar métricas detalladas
            for metric in health_status.metrics:
                logger.info(f"📊 {metric.description}: {metric.value:.2f} {metric.unit} ({metric.status.value})")
            
            # Mostrar estado de servicios
            for service, status in health_status.services_status.items():
                status_icon = "✅" if status else "❌"
                logger.info(f"{status_icon} {service}: {'UP' if status else 'DOWN'}")
            
            # Mostrar recomendaciones
            if health_status.recommendations:
                logger.info("💡 Recomendaciones:")
                for rec in health_status.recommendations:
                    logger.info(f"   • {rec}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"❌ Error verificando salud del sistema: {e}")
            raise
    
    async def run_phase_management(self, phases: List[str] = None):
        """Ejecuta gestión de fases del sistema"""
        try:
            logger.info("🔄 Ejecutando gestión de fases...")
            
            if phases is None:
                phases = ['infrastructure', 'training', 'trading', 'monitoring']
            
            result = await self.phase_manager.execute_all_phases(
                mode='production',
                phases=phases
            )
            
            if result['overall_success']:
                logger.info("✅ Todas las fases completadas exitosamente")
            else:
                logger.warning(f"⚠️ {result['phases_failed']} fases fallaron")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando gestión de fases: {e}")
            raise
    
    async def shutdown(self):
        """Cierra el sistema de forma segura"""
        try:
            logger.info("🛑 Cerrando sistema enterprise...")
            
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
            
            if self.phase_manager:
                await self.phase_manager.cancel_execution()
            
            logger.info("✅ Sistema enterprise cerrado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando sistema: {e}")

async def main():
    """Función principal del bot"""
    parser = argparse.ArgumentParser(
        description="Bot Trading v10 Enterprise",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python bot.py --mode live --symbols BTCUSDT,ETHUSDT --leverage 10
  python bot.py --mode paper --symbols BTCUSDT,ETHUSDT,ADAUSDT --leverage 5
  python bot.py --mode emergency-stop
  python bot.py --health-check
  python bot.py --phases infrastructure,training
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['live', 'paper', 'emergency-stop'],
        help='Modo de operación del bot'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Símbolos a tradear (separados por comas)'
    )
    
    parser.add_argument(
        '--leverage',
        type=int,
        default=10,
        help='Leverage a utilizar (5-30)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='src/core/config/user_settings.yaml',
        help='Ruta al archivo de configuración'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Ejecutar verificación de salud del sistema'
    )
    
    parser.add_argument(
        '--phases',
        type=str,
        help='Fases a ejecutar (separadas por comas)'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del bot
    bot = BotTradingEnterprise(args.config)
    
    try:
        # Inicializar sistema
        await bot.initialize()
        
        # Ejecutar comando solicitado
        if args.health_check:
            await bot.run_system_health_check()
        
        elif args.phases:
            phases = [p.strip() for p in args.phases.split(',')]
            await bot.run_phase_management(phases)
        
        elif args.mode:
            if not args.symbols:
                logger.error("❌ Se requiere especificar símbolos con --symbols")
                return
            
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
            
            # Validar leverage
            if not (5 <= args.leverage <= 30):
                logger.error("❌ Leverage debe estar entre 5 y 30")
                return
            
            await bot.run_trading(args.mode, symbols, args.leverage)
        
        else:
            logger.info("ℹ️ Usa --help para ver las opciones disponibles")
            await bot.run_system_health_check()
    
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupción del usuario")
    
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Ejecutar bot
    asyncio.run(main())
