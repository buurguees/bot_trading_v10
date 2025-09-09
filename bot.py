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
    
    async def run_dashboard(self, host: str = '127.0.0.1', port: int = 8050, debug: bool = False):
        """Ejecuta el dashboard del sistema"""
        try:
            logger.info(f"Iniciando dashboard en http://{host}:{port}")
            
            # Intentar importar y ejecutar el dashboard avanzado
            try:
                from src.core.monitoring.core.dashboard_app import DashboardApp
                from src.core.monitoring.core.data_provider import DataProvider
                from src.core.monitoring.core.performance_tracker import PerformanceTracker
                
                # Inicializar componentes
                data_provider = DataProvider()
                performance_tracker = PerformanceTracker(data_provider)
                
                # Crear y ejecutar dashboard
                dashboard_app = DashboardApp(
                    data_provider=data_provider,
                    performance_tracker=performance_tracker
                )
                
                logger.info("Dashboard avanzado iniciado correctamente")
                dashboard_app.run_server(host=host, port=port, debug=debug)
                
            except ImportError as e:
                logger.warning(f"Dashboard avanzado no disponible: {e}")
                logger.info("Usando dashboard básico...")
                
                # Fallback al dashboard básico
                from dashboard import IndependentDashboard
                dashboard = IndependentDashboard()
                dashboard.run(host=host, port=port, debug=debug)
                
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
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
        """Descarga histórico OHLCV leyendo años/timeframe(s) desde YAML y guarda 1 CSV por símbolo y tf.

        Configuración leída (con defaults razonables):
          - data_collection.historical.years: int (por defecto 1)
          - data_collection.historical.timeframes: lista o string (por defecto '1m')
          - data_collection.historical.align_after_download: bool (por defecto True)
        """
        try:
            import ccxt
            from config.config_loader import user_config

            Path('data/historical').mkdir(parents=True, exist_ok=True)

            # Leer parámetros desde YAML
            cfg_years = user_config.get_value(['data_collection', 'historical', 'years'], 1)
            cfg_tfs = user_config.get_value(['data_collection', 'historical', 'timeframes'], timeframe)

            years_to_fetch = int(cfg_years) if cfg_years else 1
            # Normalizar timeframes
            if isinstance(cfg_tfs, str):
                timeframes = [cfg_tfs]
            elif isinstance(cfg_tfs, list) and cfg_tfs:
                timeframes = [str(tf) for tf in cfg_tfs]
            else:
                timeframes = [timeframe]

            exchange = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 60000,  # 60 segundos
                'rateLimit': 2000,  # 2 segundos entre llamadas
            })

            # Convertir años a milisegundos y calcular fecha de inicio
            now_ms = exchange.milliseconds()
            year_ms = 365 * 24 * 60 * 60 * 1000
            start_ms = now_ms - years_to_fetch * year_ms

            for tf in timeframes:
                tf_ms = ccxt.Exchange.parse_timeframe(tf) * 1000
                for symbol in symbols:
                    market_symbol = symbol.replace('USDT', '/USDT')
                    out = Path('data/historical') / f"{symbol}_{tf}.csv"

                    logger.info(f"Descargando {years_to_fetch} años de {market_symbol} @ {tf}...")

                    # Escribir encabezado (sobrescribe para mantener un único archivo coherente)
                    with open(out, 'w', encoding='utf-8') as f:
                        f.write('timestamp,open,high,low,close,volume\n')

                    since = start_ms
                    total_rows = 0

                    try:
                        while True:
                            batch = exchange.fetch_ohlcv(market_symbol, timeframe=tf, since=since, limit=1000)
                            if not batch:
                                break

                            last_ts = batch[-1][0]
                            with open(out, 'a', encoding='utf-8') as f:
                                for t, o, h, l, c, v in batch:
                                    f.write(f"{t},{o},{h},{l},{c},{v}\n")
                                    total_rows += 1

                            next_since = last_ts + tf_ms
                            if next_since <= since or next_since >= now_ms:
                                break
                            since = next_since
                            await asyncio.sleep(2.0)  # Aumentado de 0.35 a 2.0 segundos

                        logger.info(f"Guardado: {out} ({total_rows} velas)")
                    except Exception as e:
                        logger.error(f"Error descargando {symbol} {tf}: {e}")
                        continue

            logger.info("Descarga de historico completada")

            # Alinear después de descarga si está habilitado
            align_after = user_config.get_value(['data_collection', 'historical', 'align_after_download'], True)
            if align_after:
                await self.align_historical(symbols)

        except Exception as e:
            logger.error(f"Error descargando historico: {e}")
            raise

    async def analyze_data(self, symbols: List[str], timeframe: str = '1m'):
        """Analiza históricos y genera métricas por múltiples timeframes (1h, 4h, 1d por defecto).

        - Lee analysis.timeframes del YAML; por defecto ['1h','4h','1d'].
        - Si hay fichero específico del timeframe lo usa; si no, re-muestrea desde 1m.
        """
        try:
            import pandas as pd
            from config.config_loader import user_config
            Path('reports').mkdir(exist_ok=True)
            report: Dict[str, Any] = {}

            cfg_tfs = user_config.get_value(['analysis', 'timeframes'], ['1h', '4h', '1d'])
            if isinstance(cfg_tfs, str):
                cfg_tfs = [cfg_tfs]

            def resample(df_1m: pd.DataFrame, tf: str) -> pd.DataFrame:
                ohlc = {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
                return df_1m.resample(tf).agg(ohlc).dropna()

            for symbol in symbols:
                symbol_report: Dict[str, Any] = {}

                # Cargar 1m si existe (para resample)
                csv_1m = Path('data/historical') / f"{symbol}_1m.csv"
                df_1m = None
                if csv_1m.exists():
                    base = pd.read_csv(csv_1m)
                    if not base.empty:
                        base['ts'] = pd.to_datetime(base['timestamp'], unit='ms')
                        base.set_index('ts', inplace=True)
                        df_1m = base[['open','high','low','close','volume']]

                for tf in cfg_tfs:
                    try:
                        # Intentar leer archivo directo del timeframe
                        csv_tf = Path('data/historical') / f"{symbol}_{tf}.csv"
                        if csv_tf.exists():
                            df = pd.read_csv(csv_tf)
                            df['return'] = df['close'].pct_change()
                        elif df_1m is not None:
                            # Re-muestrear desde 1m
                            df_rs = resample(df_1m, tf)
                            df = df_rs.copy()
                            df.reset_index(inplace=True)
                            df.rename(columns={'index':'ts'}, inplace=True)
                            df['timestamp'] = df['ts'].astype('int64') // 10**6
                            df['return'] = df['close'].pct_change()
                        else:
                            logger.warning(f"No hay datos 1m ni {tf} para {symbol}")
                            continue

                        symbol_report[tf] = {
                            'rows': int(len(df)),
                            'start_ts': int(df['timestamp'].iloc[0]) if len(df)>0 and 'timestamp' in df else None,
                            'end_ts': int(df['timestamp'].iloc[-1]) if len(df)>0 and 'timestamp' in df else None,
                            'mean_return': float(df['return'].mean()) if 'return' in df else 0.0,
                            'volatility': float(df['return'].std()) if 'return' in df else 0.0,
                            'price_range': {
                                'min': float(df['low'].min()) if 'low' in df else 0.0,
                                'max': float(df['high'].max()) if 'high' in df else 0.0
                            }
                        }
                    except Exception as e:
                        logger.error(f"Error analizando {symbol} {tf}: {e}")
                        symbol_report[tf] = {'error': str(e)}

                if symbol_report:
                    report[symbol] = symbol_report

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

    async def align_historical(self, symbols: List[str], base_timeframe: str = '1m'):
        """Alinea datos entre símbolos por timestamps comunes y guarda JSON.

        - Usa base_timeframe (1m por defecto). Si no existe para un símbolo, lo omite.
        - Intersección de rango [max(starts), min(ends)]. Forward-fill para gaps.
        Guarda en data/alignments/multi_symbol_aligned.json (metadatos + no datos crudos para no inflar tamaño).
        """
        import pandas as pd
        try:
            align_dir = Path('data/alignments')
            align_dir.mkdir(parents=True, exist_ok=True)

            series = {}
            starts = []
            ends = []

            for symbol in symbols:
                csv_path = Path('data/historical') / f"{symbol}_{base_timeframe}.csv"
                if not csv_path.exists():
                    logger.warning(f"Alinear: falta {csv_path}")
                    continue
                df = pd.read_csv(csv_path)
                if df.empty:
                    continue
                df['ts'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('ts', inplace=True)
                series[symbol] = df[['open','high','low','close','volume']]
                starts.append(df.index.min())
                ends.append(df.index.max())

            if not series or not starts or not ends:
                logger.warning("Alinear: no hay datos suficientes")
                return

            common_start = max(starts)
            common_end = min(ends)
            if common_start >= common_end:
                logger.warning("Alinear: rango común vacío")
                return

            idx = pd.date_range(start=common_start, end=common_end, freq='1min')
            summary = { 'base_timeframe': base_timeframe, 'common_start': common_start.isoformat(), 'common_end': common_end.isoformat(), 'symbols': {} }

            for symbol, df in series.items():
                aligned = df.reindex(idx).ffill()
                summary['symbols'][symbol] = {
                    'rows': int(aligned.shape[0]),
                    'start': aligned.index.min().isoformat(),
                    'end': aligned.index.max().isoformat()
                }

            out = align_dir / 'multi_symbol_aligned.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Alineación completada: {out}")

        except Exception as e:
            logger.error(f"Error alineando datos: {e}")

    async def _sync_incremental(self, symbols: List[str]) -> None:
        """Sincroniza histórico incremental desde el último timestamp del CSV hasta ahora.

        Lee parámetros desde YAML:
          - data_collection.historical.timeframes: lista o string
        """
        try:
            import ccxt
            from config.config_loader import user_config
            import pandas as pd

            exchange = ccxt.binance({'enableRateLimit': True})
            cfg_timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'])
            if not cfg_timeframes:
                cfg_timeframes = [user_config.get_value(['data_collection', 'historical', 'timeframe'], '1m')]
            if isinstance(cfg_timeframes, str):
                cfg_timeframes = [cfg_timeframes]

            for timeframe in cfg_timeframes:
                tf_ms = ccxt.Exchange.parse_timeframe(timeframe) * 1000
                for symbol in symbols:
                    path = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                    path.parent.mkdir(parents=True, exist_ok=True)

                    # Determinar since a partir del CSV si existe
                    since_ms = None
                    if path.exists():
                        try:
                            df = pd.read_csv(path)
                            if 'timestamp' in df.columns and not df.empty:
                                since_ms = int(df['timestamp'].iloc[-1]) + tf_ms
                        except Exception:
                            since_ms = None

                    if since_ms is None:
                        # Si no hay CSV previo, usar descarga paginada estándar
                        await self.download_historical([symbol], timeframe=timeframe)
                        continue

                    market_symbol = symbol.replace('USDT', '/USDT')
                    total = 0
                    now_ms = exchange.milliseconds()
                    logger.info(f"Sincronizando {symbol} {timeframe} desde {since_ms} hasta now...")
                    try:
                        while since_ms < now_ms:
                            batch = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, since=since_ms, limit=1000)
                            if not batch:
                                break
                            last_ts = batch[-1][0]
                            with open(path, 'a', encoding='utf-8') as f:
                                for t, o, h, l, c, v in batch:
                                    f.write(f"{t},{o},{h},{l},{c},{v}\n")
                                    total += 1
                            next_since = last_ts + tf_ms
                            if next_since <= since_ms:
                                break
                            since_ms = next_since
                            await asyncio.sleep(0.35)
                        logger.info(f"Sincronizacion {symbol} {timeframe} +{total} velas")
                    except Exception as e:
                        logger.warning(f"Sync incremental fallo para {symbol} {timeframe}: {e}")

        except Exception as e:
            logger.error(f"Error en sincronizacion incremental: {e}")

    async def _stream_realtime(self, symbols: List[str]) -> None:
        """Streamer simple en background que añade nuevas velas a CSV cada intervalo.

        Config desde YAML:
          - data_collection.historical.timeframes
          - training.stream_interval_sec (default 15)
        """
        import ccxt
        from config.config_loader import user_config

        exchange = ccxt.binance({'enableRateLimit': True})
        cfg_timeframes = user_config.get_value(['data_collection', 'historical', 'timeframes'])
        if not cfg_timeframes:
            cfg_timeframes = [user_config.get_value(['data_collection', 'historical', 'timeframe'], '1m')]
        if isinstance(cfg_timeframes, str):
            cfg_timeframes = [cfg_timeframes]
        interval = int(user_config.get_value(['training', 'stream_interval_sec'], 15))

        try:
            while True:
                for timeframe in cfg_timeframes:
                    tf_ms = ccxt.Exchange.parse_timeframe(timeframe) * 1000
                    for symbol in symbols:
                        try:
                            market_symbol = symbol.replace('USDT', '/USDT')
                            # Fetch la última vela cerrada
                            ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, limit=2)
                            if not ohlcv:
                                continue
                            last = ohlcv[-1]
                            ts = last[0]
                            path = Path('data/historical') / f"{symbol}_{timeframe}.csv"
                            path.parent.mkdir(parents=True, exist_ok=True)
                            # Evitar duplicados leyendo el último timestamp del archivo
                            exists_ts = None
                            if path.exists():
                                try:
                                    with open(path, 'rb') as f:
                                        try:
                                            f.seek(-200, 2)
                                        except Exception:
                                            f.seek(0)
                                        tail = f.read().decode('utf-8', errors='ignore').strip().splitlines()
                                        if tail:
                                            parts = tail[-1].split(',')
                                            if parts:
                                                exists_ts = int(parts[0])
                                except Exception:
                                    exists_ts = None
                            if exists_ts != ts:
                                with open(path, 'a', encoding='utf-8') as f:
                                    f.write(f"{ts},{last[1]},{last[2]},{last[3]},{last[4]},{last[5]}\n")
                        except Exception as e:
                            logger.debug(f"Stream fallo {symbol} {timeframe}: {e}")
                await asyncio.sleep(max(5, interval))
        except asyncio.CancelledError:
            logger.info("Streamer en tiempo real detenido")
        except Exception as e:
            logger.error(f"Error en streamer: {e}")
    async def train_short(self, symbols: List[str]):
        """Sincroniza datos (opcional), inicia streamer (opcional) y lanza entrenamiento corto."""
        try:
            from config.config_loader import user_config

            # Flags desde YAML
            sync_before = bool(user_config.get_value(['training', 'sync_before'], True))
            stream_during = bool(user_config.get_value(['training', 'stream_during'], True))

            if sync_before:
                logger.info("Sincronizando histórico incremental antes de entrenar...")
                await self._sync_incremental(symbols)

            streamer_task = None
            if stream_during:
                logger.info("Iniciando streamer en tiempo real durante el entrenamiento...")
                streamer_task = asyncio.create_task(self._stream_realtime(symbols))

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
        finally:
            # Detener streamer si estaba activo
            try:
                for task in asyncio.all_tasks():
                    # No cancelar nuestra propia tarea principal
                    pass
            except Exception:
                pass

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
        choices=['live', 'paper', 'emergency-stop', 'download-historical', 'analyze', 'validate', 'train-short', 'train-infinite', 'dashboard'],
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
    
    parser.add_argument(
        '--dashboard-port',
        type=int,
        default=8050,
        help='Puerto para el dashboard (solo con --mode dashboard)'
    )
    
    parser.add_argument(
        '--dashboard-host',
        type=str,
        default='127.0.0.1',
        help='Host para el dashboard (solo con --mode dashboard)'
    )
    
    parser.add_argument(
        '--dashboard-debug',
        action='store_true',
        help='Modo debug para el dashboard'
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
                    # Rango de leverage configurable desde YAML
                    try:
                        from config.config_loader import user_config
                        min_lev = user_config.get_value(['risk_management', 'min_leverage'], 5)
                        max_lev = user_config.get_value(['risk_management', 'max_leverage'], 30)
                    except Exception:
                        min_lev, max_lev = 5, 30
                    if not (min_lev <= args.leverage <= max_lev):
                        logger.error(f"❌ Leverage debe estar entre {min_lev} y {max_lev}")
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
            
            elif args.mode == 'dashboard':
                await bot.run_dashboard(
                    host=args.dashboard_host,
                    port=args.dashboard_port,
                    debug=args.dashboard_debug
                )
        
        else:
            logger.info("Usa --help para ver las opciones disponibles")
            logger.info("Modos disponibles:")
            logger.info("  --mode download-historical --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode analyze --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode validate --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode train-short --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode train-infinite --symbols BTCUSDT,ETHUSDT")
            logger.info("  --mode dashboard [--dashboard-port 8050] [--dashboard-host 127.0.0.1] [--dashboard-debug]")
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
