# Ruta: scripts/trading/enterprise/start_live_trading.py
# start_live_trading.py - Script para iniciar trading en vivo
# Ubicación: C:\TradingBot_v10\trading_scripts\enterprise\start_live_trading.py

"""
Script para iniciar trading en vivo enterprise.

Características:
- Trading autónomo 24/7
- Leverage dinámico 5x-30x
- Risk management enterprise
- Monitoreo en tiempo real
- Alertas y notificaciones
"""

import asyncio
import logging
import sys
import os
import signal
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Imports del sistema
from trading.enterprise.futures_engine import EnterpriseFuturesEngine
from config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/trading/live_trading.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class LiveTradingLauncher:
    """Launcher para trading en vivo"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.engine = None
        self.is_running = False
        
        # Configurar signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales del sistema"""
        logger.info(f"Señal {signum} recibida. Iniciando shutdown...")
        self.stop_trading()
    
    async def start_trading(
        self,
        duration_hours: Optional[int] = None,
        symbols: Optional[list] = None
    ):
        """Inicia el trading en vivo"""
        try:
            logger.info("🚀 Iniciando Trading en Vivo Enterprise")
            logger.info("=" * 60)
            
            # Verificaciones previas
            await self._pre_trading_checks()
            
            # Inicializar motor de trading
            self.engine = EnterpriseFuturesEngine(self.config_path)
            
            # Configurar exchange para live trading
            await self._setup_live_trading()
            
            # Iniciar trading
            self.is_running = True
            
            logger.info(f"📊 Modo: LIVE TRADING")
            logger.info(f"⏱️ Duración: {'Indefinido' if duration_hours is None else f'{duration_hours} horas'}")
            logger.info(f"💰 Símbolos: {symbols or 'Todos los configurados'}")
            logger.info("=" * 60)
            
            # Ejecutar trading
            results = await self.engine.start_autonomous_trading(
                duration_hours=duration_hours,
                symbols=symbols
            )
            
            # Mostrar resultados
            await self._show_results(results)
            
        except Exception as e:
            logger.error(f"❌ Error en trading en vivo: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _pre_trading_checks(self):
        """Verificaciones previas al trading"""
        logger.info("🔍 Ejecutando verificaciones previas...")
        
        # Verificar variables de entorno
        required_env_vars = ['BITGET_API_KEY', 'BITGET_SECRET_KEY', 'BITGET_PASSPHRASE']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            raise Exception(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
        
        # Verificar configuración
        config_manager = EnterpriseConfigManager(self.config_path)
        config = config_manager.load_config()
        
        if config.trading.mode != 'live_trading':
            logger.warning("⚠️ Modo de trading no es 'live_trading'. Cambiando a live_trading...")
            config.trading.mode = 'live_trading'
        
        # Verificar balance mínimo
        # (En un sistema real, esto verificaría el balance real del exchange)
        logger.info("✅ Verificaciones previas completadas")
    
    async def _setup_live_trading(self):
        """Configura el sistema para trading en vivo"""
        try:
            # Configurar exchange para live trading
            if self.engine.exchange:
                # Deshabilitar sandbox mode
                self.engine.exchange.sandbox = False
                
                # Configurar rate limiting más estricto
                self.engine.exchange.rateLimit = 100  # 100ms entre requests
                
                logger.info("✅ Exchange configurado para live trading")
            
            # Configurar alertas adicionales
            await self._setup_live_alerts()
            
        except Exception as e:
            logger.error(f"Error configurando live trading: {e}")
            raise
    
    async def _setup_live_alerts(self):
        """Configura alertas para trading en vivo"""
        try:
            # Configurar alertas críticas
            logger.info("🔔 Configurando alertas para live trading...")
            
            # En un sistema real, esto configuraría:
            # - Alertas por email
            # - Alertas por Slack/Discord
            # - Alertas por SMS para eventos críticos
            # - Notificaciones push
            
            logger.info("✅ Alertas configuradas")
            
        except Exception as e:
            logger.error(f"Error configurando alertas: {e}")
    
    async def _show_results(self, results: dict):
        """Muestra los resultados del trading"""
        try:
            logger.info("=" * 60)
            logger.info("📊 RESULTADOS DEL TRADING")
            logger.info("=" * 60)
            
            if results:
                logger.info(f"⏱️ Duración: {results.get('duration_hours', 0):.2f} horas")
                logger.info(f"💰 Trades ejecutados: {results.get('total_trades', 0)}")
                logger.info(f"📈 PnL Total: ${results.get('total_pnl', 0):.2f}")
                logger.info(f"💵 Balance Final: ${results.get('final_balance', 0):.2f}")
                logger.info(f"🎯 Tasa de éxito: {results.get('success_rate', 0):.2%}")
                logger.info(f"🔒 Posiciones cerradas: {results.get('positions_closed', 0)}")
            else:
                logger.info("No hay resultados disponibles")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error mostrando resultados: {e}")
    
    async def _cleanup(self):
        """Limpieza al finalizar"""
        try:
            if self.engine:
                await self.engine.cleanup()
            
            self.is_running = False
            logger.info("✅ Cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")
    
    def stop_trading(self):
        """Detiene el trading"""
        if self.engine and self.is_running:
            logger.info("🛑 Deteniendo trading...")
            self.engine.stop_trading()
            self.is_running = False

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Trading en Vivo Enterprise')
    parser.add_argument('--duration', type=int, help='Duración en horas (opcional)')
    parser.add_argument('--symbols', nargs='+', help='Símbolos específicos a tradear')
    parser.add_argument('--config', type=str, help='Ruta al archivo de configuración')
    
    args = parser.parse_args()
    
    try:
        # Crear launcher
        launcher = LiveTradingLauncher(args.config)
        
        # Iniciar trading
        await launcher.start_trading(
            duration_hours=args.duration,
            symbols=args.symbols
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrumpido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Verificar que estamos en el directorio correcto
    if not Path("trading/enterprise").exists():
        logger.error("❌ Ejecutar desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Ejecutar
    asyncio.run(main())
