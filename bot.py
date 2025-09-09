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
import subprocess
import json

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.deployment.phase_manager import PhaseManager
from src.core.deployment.health_monitor import HealthMonitor
from src.core.config.enterprise_config import EnterpriseConfigManager
from src.scripts.trading.run_enterprise_trading import EnterpriseTradingLauncher

# Configurar logging (UTF-8 y sin emojis para compatibilidad Windows)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
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

    # ======= NUEVAS OPERACIONES PERSONALES DESDE MAIN =======
    async def download_historical(self, symbols: List[str], timeframe: str = '1m', limit: int = 1000):
        """Descarga histórico OHLCV usando ccxt y lo guarda en data/historical como CSV.
        """
        try:
            import ccxt
            Path('data/historical').mkdir(parents=True, exist_ok=True)
            exchange = ccxt.binance({'enableRateLimit': True})
            for symbol in symbols:
                market_symbol = symbol.replace('USDT', '/USDT')
                logger.info(f"Descargando {market_symbol} {timeframe} ({limit} velas)...")
                ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, limit=limit)
                out = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                with open(out, 'w', encoding='utf-8') as f:
                    f.write('timestamp,open,high,low,close,volume\n')
                    for t, o, h, l, c, v in ohlcv:
                        f.write(f"{t},{o},{h},{l},{c},{v}\n")
                logger.info(f"Guardado: {out}")
        except Exception as e:
            logger.error(f"Error descargando histórico: {e}")
            raise

    async def analyze_data(self, symbols: List[str], timeframe: str = '1m'):
        """Analiza CSVs en data/historical y genera métricas simples en reports/analysis.json."""
        try:
            import pandas as pd
            Path('reports').mkdir(exist_ok=True)
            report = {}
            for symbol in symbols:
                csv_path = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                if not csv_path.exists():
                    logger.warning(f"No existe {csv_path}, omitiendo")
                    continue
                df = pd.read_csv(csv_path)
                df['return'] = df['close'].pct_change()
                report[symbol] = {
                    'rows': int(df.shape[0]),
                    'start_ts': int(df['timestamp'].iloc[0]) if df.shape[0] else None,
                    'end_ts': int(df['timestamp'].iloc[-1]) if df.shape[0] else None,
                    'mean_return': float(df['return'].mean()) if df['return'].notna().any() else 0.0,
                    'volatility': float(df['return'].std()) if df['return'].notna().any() else 0.0,
                    'missing': int(df.isna().sum().sum())
                }
            out = Path('reports') / 'analysis.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte de análisis: {out}")
        except Exception as e:
            logger.error(f"Error analizando datos: {e}")
            raise

    async def validate_data(self, symbols: List[str], timeframe: str = '1m'):
        """Valida CSVs en data/historical (NA, orden temporal, columnas)."""
        try:
            import pandas as pd
            issues = {}
            for symbol in symbols:
                csv_path = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                sym_issues = []
                if not csv_path.exists():
                    sym_issues.append('missing_file')
                else:
                    df = pd.read_csv(csv_path)
                    expected_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
                    if set(df.columns) != expected_cols:
                        sym_issues.append('bad_columns')
                    if df.isna().any().any():
                        sym_issues.append('na_values')
                    if (df['timestamp'].diff() <= 0).any():
                        sym_issues.append('not_strictly_increasing_ts')
                if sym_issues:
                    issues[symbol] = sym_issues
            out = Path('reports') / 'validation.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(issues, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte de validación: {out}")
        except Exception as e:
            logger.error(f"Error validando datos: {e}")
            raise

    async def train_short(self, symbols: List[str]):
        """Lanza entrenamiento corto usando el script personal."""
        cmd = [sys.executable, 'scripts/root/start_6h_training_enterprise.py', '--symbols', *symbols, '--duration', '0']
        logger.info(f"Ejecutando: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        logger.info("Entrenamiento corto finalizado")

    async def train_infinite_with_dashboard(self, symbols: List[str]):
        """Bucle de entrenamiento infinito y arranque de dashboard en paralelo."""
        # Lanzar dashboard (si existe)
        dash_path = Path('src/core/monitoring/main_dashboard.py')
        dash_proc = None
        if dash_path.exists():
            dash_cmd = [sys.executable, str(dash_path)]
            logger.info(f"Iniciando dashboard: {' '.join(dash_cmd)}")
            dash_proc = await asyncio.create_subprocess_exec(*dash_cmd)

        # Bucle de entrenamiento (simulación: usa entrenamiento corto en bucle)
        try:
            while True:
                await self.train_short(symbols)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Bucle de entrenamiento cancelado")
        finally:
            if dash_proc:
                dash_proc.terminate()

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
        choices=['live', 'paper', 'emergency-stop', 'download-historical', 'analyze', 'validate', 'train-short', 'train-infinite'],
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

            if args.mode in ['live', 'paper', 'emergency-stop']:
                if args.mode != 'emergency-stop':
                    if not (5 <= args.leverage <= 30):
                        logger.error("❌ Leverage debe estar entre 5 y 30")
                        return
                await bot.run_trading(args.mode, symbols, args.leverage)

            elif args.mode == 'download-historical':
                await bot.download_historical(symbols, timeframe='1m', limit=1000)

            elif args.mode == 'analyze':
                await bot.analyze_data(symbols, timeframe='1m')

            elif args.mode == 'validate':
                await bot.validate_data(symbols, timeframe='1m')

            elif args.mode == 'train-short':
                await bot.train_short(symbols)

            elif args.mode == 'train-infinite':
                await bot.train_infinite_with_dashboard(symbols)
        
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
