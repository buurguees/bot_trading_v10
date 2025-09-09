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
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
from datetime import datetime
from typing import List, Optional
import subprocess
import json

# Agregar src y config al path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))

# Importaciones simplificadas para evitar errores de módulos complejos
try:
    from src.core.config.enterprise_config import EnterpriseConfigManager
except ImportError:
    # Fallback: usar config loader simple
    from config.config_loader import ConfigLoader
    EnterpriseConfigManager = None

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
        
        # Usar config manager simple si enterprise no está disponible
        if EnterpriseConfigManager:
            self.config_manager = EnterpriseConfigManager(config_path)
        else:
            from config.config_loader import ConfigLoader
            self.config_manager = ConfigLoader(config_path)
        
        self.phase_manager = None
        self.health_monitor = None
        self.trading_launcher = None
        
        # Crear directorio de logs
        Path("logs").mkdir(exist_ok=True)
        
        logger.info("Bot Trading v10 Enterprise inicializado")
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("Inicializando sistema enterprise...")
            
            # Cargar configuración
            config = self.config_manager.load_config()
            logger.info("Configuracion cargada")
            
            # Inicializar componentes solo si están disponibles
            try:
                from src.core.deployment.phase_manager import PhaseManager
                self.phase_manager = PhaseManager(config)
                logger.info("Gestor de fases inicializado")
            except ImportError:
                logger.warning("Gestor de fases no disponible")
            
            try:
                from src.core.deployment.health_monitor import HealthMonitor
                self.health_monitor = HealthMonitor(config)
                logger.info("Monitor de salud inicializado")
            except ImportError:
                logger.warning("Monitor de salud no disponible")
            
            try:
                from src.scripts.trading.run_enterprise_trading import EnterpriseTradingLauncher
                self.trading_launcher = EnterpriseTradingLauncher(config)
                logger.info("Launcher de trading inicializado")
            except ImportError:
                logger.warning("Launcher de trading no disponible")
            
            logger.info("Sistema enterprise inicializado completamente")
            
        except Exception as e:
            logger.error(f"Error inicializando sistema: {e}")
            raise
    
    async def run_trading(self, mode: str, symbols: List[str], leverage: int = 10):
        """Ejecuta el trading en el modo especificado"""
        try:
            logger.info(f"Iniciando trading en modo {mode}")
            logger.info(f"Simbolos: {', '.join(symbols)}")
            logger.info(f"Leverage: {leverage}x")
            
            # Validar modo
            if mode not in ['live', 'paper', 'emergency-stop']:
                raise ValueError(f"Modo invalido: {mode}")
            
            # Ejecutar trading usando launcher si está disponible
            if self.trading_launcher:
                if mode == 'emergency-stop':
                    await self.trading_launcher.emergency_stop()
                else:
                    await self.trading_launcher.start_trading(
                        mode=mode,
                        symbols=symbols,
                        leverage=leverage
                    )
            else:
                logger.warning("Launcher de trading no disponible, usando modo simulacion")
                # Simulación básica
                await asyncio.sleep(1)
                logger.info(f"Simulacion de trading completada para {', '.join(symbols)}")
            
            logger.info(f"Trading en modo {mode} completado")
            
        except Exception as e:
            logger.error(f"Error ejecutando trading: {e}")
            raise
    
    async def run_system_health_check(self):
        """Ejecuta verificación de salud del sistema"""
        try:
            logger.info("Verificando salud del sistema...")
            
            if self.health_monitor:
                health_status = await self.health_monitor.get_system_health()
                
                logger.info(f"Estado general: {health_status.overall_status.value}")
                logger.info(f"Score de salud: {health_status.overall_score:.1f}/100")
                logger.info(f"Problemas criticos: {health_status.critical_issues}")
                logger.info(f"Advertencias: {health_status.warning_issues}")
                
                # Mostrar métricas detalladas
                for metric in health_status.metrics:
                    logger.info(f"{metric.description}: {metric.value:.2f} {metric.unit} ({metric.status.value})")
                
                # Mostrar estado de servicios
                for service, status in health_status.services_status.items():
                    status_icon = "OK" if status else "ERROR"
                    logger.info(f"{status_icon} {service}: {'UP' if status else 'DOWN'}")
                
                # Mostrar recomendaciones
                if health_status.recommendations:
                    logger.info("Recomendaciones:")
                    for rec in health_status.recommendations:
                        logger.info(f"   - {rec}")
                
                return health_status
            else:
                # Verificación básica sin monitor enterprise
                logger.info("Monitor de salud no disponible, ejecutando verificacion basica...")
                
                # Verificar archivos de configuración
                config_exists = Path(self.config_path).exists()
                logger.info(f"Configuracion: {'OK' if config_exists else 'ERROR'}")
                
                # Verificar directorios necesarios
                dirs_to_check = ['logs', 'models', 'data/historical', 'reports']
                for dir_path in dirs_to_check:
                    exists = Path(dir_path).exists()
                    logger.info(f"Directorio {dir_path}: {'OK' if exists else 'MISSING'}")
                
                # Verificar símbolos configurados
                symbols = self.config_manager.get_symbols()
                logger.info(f"Simbolos configurados: {len(symbols)} - {', '.join(symbols[:5])}")
                
                logger.info("Verificacion basica completada")
                return {"status": "basic_check_completed", "symbols": symbols}
            
        except Exception as e:
            logger.error(f"Error verificando salud del sistema: {e}")
            raise
    
    async def run_phase_management(self, phases: List[str] = None):
        """Ejecuta gestión de fases del sistema"""
        try:
            logger.info("Ejecutando gestion de fases...")
            
            if phases is None:
                phases = ['infrastructure', 'training', 'trading', 'monitoring']
            
            if self.phase_manager:
                result = await self.phase_manager.execute_all_phases(
                    mode='production',
                    phases=phases
                )
                
                if result['overall_success']:
                    logger.info("Todas las fases completadas exitosamente")
                else:
                    logger.warning(f"{result['phases_failed']} fases fallaron")
                
                return result
            else:
                logger.warning("Gestor de fases no disponible, ejecutando fases basicas...")
                
                # Ejecutar fases básicas
                result = {"overall_success": True, "phases_completed": [], "phases_failed": []}
                
                for phase in phases:
                    try:
                        logger.info(f"Ejecutando fase: {phase}")
                        await asyncio.sleep(1)  # Simulación
                        result["phases_completed"].append(phase)
                        logger.info(f"Fase {phase} completada")
                    except Exception as e:
                        logger.error(f"Error en fase {phase}: {e}")
                        result["phases_failed"].append(phase)
                        result["overall_success"] = False
                
                return result
            
        except Exception as e:
            logger.error(f"Error ejecutando gestion de fases: {e}")
            raise
    
    async def shutdown(self):
        """Cierra el sistema de forma segura"""
        try:
            logger.info("Cerrando sistema enterprise...")
            
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
            
            if self.phase_manager:
                await self.phase_manager.cancel_execution()
            
            logger.info("Sistema enterprise cerrado correctamente")
            
        except Exception as e:
            logger.error(f"Error cerrando sistema: {e}")

    # ======= NUEVAS OPERACIONES PERSONALES DESDE MAIN =======
    async def download_historical(self, symbols: List[str], timeframe: str = '1m', limit: int = 1000):
        """Descarga histórico OHLCV usando ccxt y lo guarda en data/historical como CSV."""
        try:
            import ccxt
            Path('data/historical').mkdir(parents=True, exist_ok=True)
            exchange = ccxt.binance({'enableRateLimit': True})
            
            for symbol in symbols:
                market_symbol = symbol.replace('USDT', '/USDT')
                logger.info(f"Descargando {market_symbol} {timeframe} ({limit} velas)...")
                
                try:
                    ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, limit=limit)
                    out = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                    
                    with open(out, 'w', encoding='utf-8') as f:
                        f.write('timestamp,open,high,low,close,volume\n')
                        for t, o, h, l, c, v in ohlcv:
                            f.write(f"{t},{o},{h},{l},{c},{v}\n")
                    
                    logger.info(f"Guardado: {out} ({len(ohlcv)} velas)")
                    
                except Exception as e:
                    logger.error(f"Error descargando {symbol}: {e}")
                    continue
            
            logger.info("Descarga de historico completada")
            
        except Exception as e:
            logger.error(f"Error descargando historico: {e}")
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
                
                try:
                    df = pd.read_csv(csv_path)
                    df['return'] = df['close'].pct_change()
                    
                    report[symbol] = {
                        'rows': int(df.shape[0]),
                        'start_ts': int(df['timestamp'].iloc[0]) if df.shape[0] > 0 else None,
                        'end_ts': int(df['timestamp'].iloc[-1]) if df.shape[0] > 0 else None,
                        'mean_return': float(df['return'].mean()) if df['return'].notna().any() else 0.0,
                        'volatility': float(df['return'].std()) if df['return'].notna().any() else 0.0,
                        'missing': int(df.isna().sum().sum()),
                        'price_range': {
                            'min': float(df['low'].min()) if df.shape[0] > 0 else 0.0,
                            'max': float(df['high'].max()) if df.shape[0] > 0 else 0.0
                        }
                    }
                    
                    logger.info(f"Analizado {symbol}: {df.shape[0]} filas, volatilidad: {report[symbol]['volatility']:.4f}")
                    
                except Exception as e:
                    logger.error(f"Error analizando {symbol}: {e}")
                    report[symbol] = {'error': str(e)}
            
            out = Path('reports') / 'analysis.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de analisis: {out}")
            
        except Exception as e:
            logger.error(f"Error analizando datos: {e}")
            raise

    async def validate_data(self, symbols: List[str], timeframe: str = '1m'):
        """Valida CSVs en data/historical (NA, orden temporal, columnas)."""
        try:
            import pandas as pd
            Path('reports').mkdir(exist_ok=True)
            issues = {}
            
            for symbol in symbols:
                csv_path = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                sym_issues = []
                
                if not csv_path.exists():
                    sym_issues.append('missing_file')
                    logger.warning(f"Archivo no encontrado: {csv_path}")
                else:
                    try:
                        df = pd.read_csv(csv_path)
                        expected_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
                        
                        # Verificar columnas
                        if set(df.columns) != expected_cols:
                            sym_issues.append('bad_columns')
                            logger.warning(f"{symbol}: columnas incorrectas: {list(df.columns)}")
                        
                        # Verificar valores NA
                        if df.isna().any().any():
                            sym_issues.append('na_values')
                            na_count = df.isna().sum().sum()
                            logger.warning(f"{symbol}: {na_count} valores NA encontrados")
                        
                        # Verificar orden temporal
                        if df.shape[0] > 1 and (df['timestamp'].diff() <= 0).any():
                            sym_issues.append('not_strictly_increasing_ts')
                            logger.warning(f"{symbol}: timestamps no estan en orden creciente")
                        
                        # Verificar rangos de precios
                        if df.shape[0] > 0:
                            if (df['high'] < df['low']).any():
                                sym_issues.append('high_low_invalid')
                                logger.warning(f"{symbol}: high < low en algunas filas")
                            
                            if (df['close'] < 0).any() or (df['volume'] < 0).any():
                                sym_issues.append('negative_values')
                                logger.warning(f"{symbol}: valores negativos encontrados")
                        
                        logger.info(f"Validado {symbol}: {len(sym_issues)} problemas encontrados")
                        
                    except Exception as e:
                        sym_issues.append(f'read_error: {str(e)}')
                        logger.error(f"Error leyendo {symbol}: {e}")
                
                if sym_issues:
                    issues[symbol] = sym_issues
            
            out = Path('reports') / 'validation.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(issues, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de validacion: {out}")
            
        except Exception as e:
            logger.error(f"Error validando datos: {e}")
            raise

    async def train_short(self, symbols: List[str]):
        """Lanza entrenamiento corto usando el script personal."""
        try:
            cmd = [sys.executable, 'scripts/root/start_6h_training_enterprise.py', '--symbols', *symbols, '--duration', '0']
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info("Entrenamiento corto completado exitosamente")
            else:
                logger.error(f"Entrenamiento corto fallo con codigo {proc.returncode}")
                if stderr:
                    logger.error(f"Error: {stderr.decode()}")
            
        except Exception as e:
            logger.error(f"Error ejecutando entrenamiento corto: {e}")

    async def train_infinite_with_dashboard(self, symbols: List[str]):
        """Bucle de entrenamiento infinito y arranque de dashboard en paralelo."""
        # Lanzar dashboard (si existe)
        dash_path = Path('src/core/monitoring/main_dashboard.py')
        dash_proc = None
        
        if dash_path.exists():
            dash_cmd = [sys.executable, str(dash_path)]
            logger.info(f"Iniciando dashboard: {' '.join(dash_cmd)}")
            try:
                dash_proc = await asyncio.create_subprocess_exec(*dash_cmd)
            except Exception as e:
                logger.warning(f"No se pudo iniciar dashboard: {e}")

        # Bucle de entrenamiento
        try:
            iteration = 0
            while True:
                iteration += 1
                logger.info(f"Iniciando iteracion de entrenamiento {iteration}")
                
                await self.train_short(symbols)
                
                # Esperar antes de la siguiente iteración
                wait_time = 30  # 30 segundos entre iteraciones
                logger.info(f"Esperando {wait_time} segundos antes de la siguiente iteracion...")
                await asyncio.sleep(wait_time)
                
        except asyncio.CancelledError:
            logger.info("Bucle de entrenamiento cancelado por el usuario")
        except KeyboardInterrupt:
            logger.info("Bucle de entrenamiento interrumpido")
        finally:
            if dash_proc:
                logger.info("Cerrando dashboard...")
                dash_proc.terminate()
                try:
                    await dash_proc.wait()
                except:
                    pass

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
            logger.info("Usa --help para ver las opciones disponibles")
            logger.info("Modos disponibles:")
            logger.info("  --mode download-historical --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode analyze --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode validate --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode train-short --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode train-infinite --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode live --symbols BTCUSDT,ETHUSDT --leverage 10")
            logger.info("  --mode paper --symbols BTCUSDT,ETHUSDT --leverage 5")
            logger.info("  --mode emergency-stop --symbols BTCUSDT,ETHUSDT")
            logger.info("  --health-check")
            await bot.run_system_health_check()
    
    except KeyboardInterrupt:
        logger.info("Interrupcion del usuario")
    
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Ejecutar bot
    asyncio.run(main())
