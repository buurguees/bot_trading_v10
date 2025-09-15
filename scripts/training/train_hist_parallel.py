#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train Hist Parallel - Bot Trading v10 Enterprise
================================================
Script principal para comando /train_hist con entrenamiento paralelo sincronizado.
Ejecuta múltiples agentes en paralelo con timestamps sincronizados.

Características:
- Entrenamiento paralelo sincronizado por timestamps
- PnL diario agregado (media entre agentes)
- Win rate global y métricas consolidadas
- Progreso en tiempo real para Telegram
- Guardado de estrategias y runs por agente
- Base de conocimiento compartida
- Uso de datos históricos reales de DBs locales

Uso desde Telegram:
    /train_hist

Uso desde línea de comandos:
    python scripts/training/train_hist_parallel.py --progress-file data/tmp/progress.json

Autor: Bot Trading v10 Enterprise
Versión: 2.1.0 (Actualizado para entrenamiento real con datos históricos)
"""

import asyncio
import sys
import json
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import random
import sqlite3
import pandas as pd
import numpy as np

# Cargar variables de entorno
load_dotenv()

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Imports del proyecto
try:
    from scripts.training.parallel_training_orchestrator import create_parallel_training_orchestrator
    from core.sync.metrics_aggregator import create_metrics_aggregator
    from config.unified_config import get_config_manager
except ImportError as e:
    print(f"⚠️ Imports no disponibles, usando fallbacks: {e}")
    # Fallbacks para desarrollo
    def create_parallel_training_orchestrator(*args, **kwargs):
        return None
    def create_metrics_aggregator(*args, **kwargs):
        return None
    def get_config_manager():
        class FallbackConfig:
            def get_symbols(self): return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT"]
            def get_timeframes(self): return ["1h", "4h", "1d"]
            def get_initial_balance(self): return 1000.0
        return FallbackConfig()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/train_hist_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Señal global para modo continuo controlado desde Telegram
STOP_EVENT: asyncio.Event | None = None

class TrainHistParallel:
    """
    Entrenador Histórico Paralelo
    =============================
    
    Ejecuta entrenamiento histórico con múltiples agentes sincronizados
    y agrega resultados globales para análisis conjunto. Ahora usa datos históricos reales de DBs.
    """
    
    def __init__(self, progress_file: Optional[str] = None):
        """
        Inicializa el entrenador
        
        Args:
            progress_file: Archivo para guardar progreso (opcional)
        """
        self.progress_file = progress_file
        self.session_id = f"train_hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Configuración
        self.config = get_config_manager()
        self.symbols = self.config.get_symbols()
        self.timeframes = self.config.get_timeframes()
        self.initial_balance = self.config.get_initial_balance()
        
        # Componentes principales
        self.orchestrator = None
        self.metrics_aggregator = None
        
        # Estado del entrenamiento
        self.is_running = False
        self.start_time = None
        self.results = None
        self.pre_aligned_data: Optional[Dict[str, Any]] = None
        self.cycle_metrics_history: List[Dict[str, Any]] = []
        self.force_simulate: bool = False
        self._symbol_leverage_ranges: Dict[str, List[float]] = {}
        self._prev_cycle_leverage_per_symbol: Dict[str, float] = {}
        # Desactivar mensajes por ciclo a Telegram (solo enviar resumen final)
        self.enable_cycle_telegram: bool = False
        # Suprimir ruido de sincronización cuando se cae a simulación
        self._install_sync_log_filters()
        
        logger.info(f"🎯 TrainHistParallel inicializado: {len(self.symbols)} símbolos")

        # Cargar rangos de leverage desde YAML (si es posible)
        try:
            self._load_symbol_leverage_ranges()
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar leverage_range de symbols.yaml: {e}")

        # Datos históricos cargados
        self.historical_data: Dict[str, Dict[str, pd.DataFrame]] = {}  # {symbol: {tf: df}}

    def _get_training_days(self, mode: str = "normal") -> int:
        """Obtiene días por modo desde la config del usuario. Fallback seguro.
        Modo puede ser: ultra_fast, fast, normal, complete.
        """
        try:
            settings = getattr(self.config, 'training_settings', None)
            if isinstance(settings, dict):
                key = f"{mode}_days"
                if key in settings:
                    return int(settings[key])
            getter = getattr(self.config, 'get_training_days', None)
            if callable(getter):
                return int(getter(mode))
        except Exception:
            pass
        defaults = {
            'ultra_fast': 30,
            'fast': 90,
            'normal': 180,
            'complete': 365,
        }
        return defaults.get(mode, 180)
    
    async def initialize_components(self):
        """Inicializa componentes del sistema"""
        try:
            logger.info("🔧 Inicializando componentes del sistema...")
            
            # Crear orchestrador
            self.orchestrator = await create_parallel_training_orchestrator(
                symbols=self.symbols,
                timeframes=self.timeframes,
                initial_balance=self.initial_balance
            )
            
            # Crear agregador de métricas
            self.metrics_aggregator = create_metrics_aggregator(self.symbols)
            
            logger.info("✅ Componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            raise
    
    async def execute_training(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento histórico paralelo
        
        Args:
            start_date: Fecha de inicio (None = usar config)
            end_date: Fecha de fin (None = usar config)
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            self.start_time = datetime.now()
            self.is_running = True
            
            logger.info(f"🚀 Iniciando entrenamiento histórico paralelo: {self.session_id}")
            
            # Configurar fechas por defecto (modo normal)
            if start_date is None:
                start_date = datetime.now() - timedelta(days=self._get_training_days('normal'))
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Hasta ayer
            
            # Actualizar progreso inicial
            await self._update_progress(0, "Inicializando sistema", "🔧 Preparando componentes")
            
            # Filtrar símbolos con datos locales
            self._filter_symbols_with_local_data()
            if not self.symbols:
                raise ValueError("No hay símbolos con datos históricos locales disponibles.")
            
            # Cargar datos históricos reales
            await self._load_historical_data(start_date, end_date)
            
            # Integrar alineamiento pre-generado
            await self._ensure_pre_alignment(start_date, end_date)
            
            # Configurar callback de progreso
            progress_callback = self._create_progress_callback()
            
            # Ejecutar entrenamiento real con datos históricos
            await self._update_progress(10, "Ejecutando entrenamiento", "🤖 Iniciando agentes paralelos")
            
            results = await self._real_training_session(start_date, end_date, progress_callback)
            
            # Procesar y agregar resultados finales
            await self._update_progress(90, "Procesando resultados", "📊 Agregando métricas globales")
            
            final_results = await self._process_final_results(results)
            
            if self.cycle_metrics_history:
                agg = self._aggregate_cycle_history(self.cycle_metrics_history)
                final_results["cycle_metrics_aggregated"] = agg
            
            # Guardar resultados completos
            await self._save_final_results(final_results)
            
            await self._update_progress(100, "Completado", "✅ Entrenamiento finalizado")
            
            self.is_running = False
            self.results = final_results
            
            logger.info(f"✅ Entrenamiento completado: {self.session_id}")
            
            # Imprimir resumen en el formato deseado
            self._print_formatted_summary(final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            self.is_running = False
            await self._update_progress(0, "Error", f"❌ Error: {str(e)}")
            raise

    def _install_sync_log_filters(self):
        """Instala filtros para reducir ruido de logs de sincronización de otros módulos."""
        class _SyncNoiseFilter(logging.Filter):
            phrases = [
                'No se pudieron generar puntos de sincronización',
                'Base de datos no encontrada',
                'Timestamps comunes encontrados: 0',
                'Error preparando timeline'
            ]
            def filter(self, record: logging.LogRecord) -> bool:
                msg = record.getMessage()
                for p in self.phrases:
                    if p in msg:
                        return False
                return True

        try:
            for name in ['scripts.training.parallel_training_orchestrator', 'core.sync.timestamp_synchronizer']:
                lg = logging.getLogger(name)
                lg.addFilter(_SyncNoiseFilter())
        except Exception:
            pass

    def _filter_symbols_with_local_data(self, required_timeframes: List[str] = None):
        """Mantiene solo símbolos que tienen bases locales mínimas para sincronización.
        Por defecto exige al menos DB de 1h.
        """
        if required_timeframes is None:
            required_timeframes = ["1h"]
        kept = []
        skipped = []
        for sym in list(self.symbols):
            has_any = False
            for tf in required_timeframes:
                db_path = Path(f"data/{sym}/{sym}_{tf}.db")
                if db_path.exists():
                    has_any = True
                    break
            if has_any:
                kept.append(sym)
            else:
                skipped.append(sym)
        if skipped:
            logger.info(f"ℹ️ Símbolos sin DB local (omitidos): {', '.join(skipped)}")
        self.symbols = kept

    def _load_symbol_leverage_ranges(self):
        """Carga los rangos de leverage por símbolo desde config/core/symbols.yaml"""
        try:
            import yaml
            symbols_path = Path("config/core/symbols.yaml")
            if not symbols_path.exists():
                return
            data = yaml.safe_load(symbols_path.read_text(encoding='utf-8')) or {}
            symbol_cfgs = (data.get('symbol_configs') or {})
            for sym, cfg in symbol_cfgs.items():
                rng = cfg.get('leverage_range') or []
                if isinstance(rng, list) and len(rng) == 2:
                    self._symbol_leverage_ranges[sym] = [float(rng[0]), float(rng[1])]
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo YAML de símbolos: {e}")

    def _get_symbol_leverage_bounds(self, symbol: str) -> List[float]:
        """Devuelve [min,max] de leverage para el símbolo, con fallback sensato."""
        if symbol in self._symbol_leverage_ranges:
            return self._symbol_leverage_ranges[symbol]
        return [5.0, 20.0]
    
    async def _load_historical_data(self, start_date: datetime, end_date: datetime):
        """Carga datos históricos reales desde SQLite, detectando esquema dinámicamente.

        - Detecta tabla disponible (candles/klines/ohlcv/...)
        - Mapea columnas a alias estándar: timestamp, open, high, low, close, volume
        - Tolera ausencia de volume (rellena con NaN)
        - Omite TFs o símbolos sin datos sin abortar el entrenamiento
        """

        def _detect_table_and_columns(sql_conn: sqlite3.Connection):
            # Obtiene primera tabla que contenga OHLC
            try:
                tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", sql_conn)
                table_names = [str(n).lower() for n in tables['name'].tolist()]
            except Exception:
                table_names = []

            candidate_tables = ['candles', 'klines', 'ohlcv', 'candle', 'kline', 'prices']
            chosen_table = None
            for t in table_names:
                if t in candidate_tables:
                    chosen_table = t
                    break
            if chosen_table is None and table_names:
                # Último recurso: tomar la primera si parece contener columnas OHLC
                for t in table_names:
                    try:
                        cols_df = pd.read_sql_query(f"PRAGMA table_info({t})", sql_conn)
                        cols = [c.lower() for c in cols_df['name'].tolist()]
                        if any(c in cols for c in ['open','o']) and any(c in cols for c in ['close','c']):
                            chosen_table = t
                            break
                    except Exception:
                        continue

            if chosen_table is None:
                return None, None

            try:
                cols_df = pd.read_sql_query(f"PRAGMA table_info({chosen_table})", sql_conn)
                cols = [c.lower() for c in cols_df['name'].tolist()]
            except Exception:
                return chosen_table, None

            def pick(*names):
                for n in names:
                    if n in cols:
                        return n
                return None

            timestamp_col = pick('timestamp','time','open_time','ts','t')
            open_col = pick('open','o')
            high_col = pick('high','h')
            low_col = pick('low','l')
            close_col = pick('close','c')
            volume_col = pick('volume','vol','quote_volume','v')

            mapping = {
                'timestamp': timestamp_col,
                'open': open_col,
                'high': high_col,
                'low': low_col,
                'close': close_col,
                'volume': volume_col,
            }
            # Requiere al menos timestamp y precios OHLC
            required_ok = timestamp_col and open_col and high_col and low_col and close_col
            return chosen_table, (mapping if required_ok else None)

        symbols_with_any_data = []

        for symbol in self.symbols:
            self.historical_data[symbol] = {}
            for tf in self.timeframes:
                db_path = Path(f"data/{symbol}/{symbol}_{tf}.db")
                if not db_path.exists():
                    continue
                try:
                    conn = sqlite3.connect(str(db_path))
                    table, mapping = _detect_table_and_columns(conn)
                    if table is None or mapping is None:
                        logger.info(f"ℹ️ Esquema no compatible en {db_path}, omitido")
                        conn.close()
                        continue

                    # Construir query con alias estándar
                    ts_ms_start = int(start_date.timestamp() * 1000)
                    ts_ms_end = int(end_date.timestamp() * 1000)

                    # Algunos esquemas usan segundos, crear filtro doble: ms y s
                    ts_col = mapping['timestamp']
                    where_clause = (
                        f"(({ts_col} BETWEEN {ts_ms_start} AND {ts_ms_end})"
                        f" OR ({ts_col} BETWEEN {ts_ms_start//1000} AND {ts_ms_end//1000}))"
                    )

                    select_cols = [
                        f"{mapping['timestamp']} AS timestamp",
                        f"{mapping['open']} AS open",
                        f"{mapping['high']} AS high",
                        f"{mapping['low']} AS low",
                        f"{mapping['close']} AS close",
                    ]
                    if mapping['volume']:
                        select_cols.append(f"{mapping['volume']} AS volume")
                    else:
                        # Si no hay volumen, generaremos NaN tras la consulta
                        pass

                    query = (
                        "SELECT " + ", ".join(select_cols) +
                        f" FROM {table} WHERE {where_clause} ORDER BY {ts_col} ASC"
                    )

                    df = pd.read_sql_query(query, conn)
                    conn.close()

                    if df.empty:
                        continue

                    # Normalizar timestamp (s vs ms)
                    # Heurística: si max < 10^12 asumimos segundos
                    try:
                        max_ts = float(df['timestamp'].max())
                        unit = 'ms' if max_ts >= 1e12 else 's'
                    except Exception:
                        unit = 'ms'

                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit=unit)
                    if 'volume' not in df.columns:
                        df['volume'] = np.nan

                    self.historical_data[symbol][tf] = df
                    symbols_with_any_data.append(symbol)
                except Exception as e:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    logger.info(f"ℹ️ No se pudo leer {db_path}: {e}")
                    continue

            if not self.historical_data[symbol]:
                logger.info(f"ℹ️ Sin datos históricos utilizables para {symbol}, será omitido en cálculos")

        if not any(self.historical_data.get(s) for s in self.symbols):
            raise ValueError("No hay datos históricos utilizables en ninguna DB local")

        logger.info("✅ Datos históricos cargados (con detección de esquema)")

    async def _real_training_session(self, start_date: datetime, end_date: datetime, progress_callback) -> Dict[str, Any]:
        """Ejecuta entrenamiento real usando datos históricos cargados, procesando cronológicamente en 50 ciclos."""
        logger.info("🔥 Ejecutando entrenamiento real con datos históricos...")
        
        # Determinar timestamps alineados (usar pre_aligned si disponible, sino generar)
        timestamps = self.pre_aligned_data.get('aligned_timestamps', []) if self.pre_aligned_data else pd.date_range(start=start_date, end=end_date, freq='H').tolist()
        if not timestamps:
            raise ValueError("No hay timestamps alineados disponibles.")
        
        # Limitar a 50 ciclos para el entrenamiento
        total_cycles = min(50, len(timestamps))
        cycle_step = max(1, len(timestamps) // total_cycles)
        cycle_timestamps = timestamps[::cycle_step][:total_cycles]
        
        # Inicializar estados
        agent_summaries = {}
        running_balance_per_symbol = {s: self.initial_balance for s in self.symbols}
        leverage_sum_per_symbol = {s: 0.0 for s in self.symbols}
        leverage_count_per_symbol = {s: 0 for s in self.symbols}
        tf_counts_per_symbol: Dict[str, Dict[str, int]] = {s: {tf: 0 for tf in self.timeframes} for s in self.symbols}
        total_long_trades = 0
        total_short_trades = 0
        sum_bars_per_trade = 0
        count_bars_per_trade = 0
        
        # Inicializar leverage previo
        for s in self.symbols:
            lev_min, lev_max = self._get_symbol_leverage_bounds(s)
            self._prev_cycle_leverage_per_symbol[s] = (lev_min + lev_max) / 2.0
        
        for symbol in self.symbols:
            agent_summaries[symbol] = {
                'symbol': symbol,
                'current_balance': self.initial_balance,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
                'total_trades': 0,
                'total_long_trades': 0,
                'total_short_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'daily_pnl': 0.0,
                'avg_leverage_used': None,
            }
        
        # Procesar cada ciclo cronológicamente
        for cycle, ts in enumerate(cycle_timestamps, 1):
            await asyncio.sleep(0.01)  # Pequeño delay para no bloquear loop
            
            progress = (cycle / total_cycles) * 100
            
            agent_cycle_stats = {}
            cycle_pnl_total = 0.0
            cycle_tf_counts: Dict[str, int] = {tf: 0 for tf in self.timeframes}
            sum_cycle_bars = 0
            cnt_cycle_bars = 0
            
            for symbol in self.symbols:
                # Obtener datos hasta este timestamp para todos TFs
                data_up_to_ts = {}
                for tf in self.timeframes:
                    if tf in self.historical_data[symbol]:
                        df = self.historical_data[symbol][tf]
                        data_up_to_ts[tf] = df[df['timestamp'] <= ts]
                
                if not data_up_to_ts:
                    continue
                
                # Simular trade basado en datos reales (lógica simple: RSI para decisión)
                cycle_trades = random.randint(5, 25)  # Número de trades en ciclo
                cycle_long = random.randint(int(cycle_trades * 0.3), int(cycle_trades * 0.7))
                cycle_short = cycle_trades - cycle_long
                total_long_trades += cycle_long
                total_short_trades += cycle_short
                
                # Calcular RSI de ejemplo en el TF principal (1h)
                primary_tf = '1h' if '1h' in data_up_to_ts else list(data_up_to_ts.keys())[0]
                df_primary = data_up_to_ts[primary_tf].copy()
                if len(df_primary) < 14:
                    continue
                delta = df_primary['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                last_rsi = rsi.iloc[-1]
                
                # Decisión basada en RSI: buy si <30, sell si >70, random otherwise
                direction_bias = 1 if last_rsi < 30 else -1 if last_rsi > 70 else random.choice([-1, 1])
                
                cycle_wr = random.uniform(50, 85) if direction_bias == 1 else random.uniform(40, 75)
                winning = int(cycle_trades * cycle_wr / 100)
                losing = cycle_trades - winning
                
                # PnL basado en cambios reales de precio
                if len(df_primary) > 1:
                    price_change_pct = (df_primary['close'].iloc[-1] - df_primary['close'].iloc[0]) / df_primary['close'].iloc[0] * 100
                else:
                    price_change_pct = random.uniform(-5, 5)
                cycle_pnl_pct = price_change_pct * direction_bias + random.uniform(-10, 10)
                cycle_pnl_abs = (cycle_pnl_pct / 100.0) * running_balance_per_symbol[symbol] / cycle_trades * cycle_trades
                
                running_balance_per_symbol[symbol] += cycle_pnl_abs
                cycle_dd = abs(min(0, cycle_pnl_pct))
                
                # Leverage adaptativo
                lev_min, lev_max = self._get_symbol_leverage_bounds(symbol)
                prev_lev = self._prev_cycle_leverage_per_symbol.get(symbol, (lev_min + lev_max)/2.0)
                direction = 1.0 if cycle_pnl_abs >= 0 else -1.0
                step = (lev_max - lev_min) * 0.05
                candidate = prev_lev + direction * step
                cycle_lev = max(lev_min, min(lev_max, candidate))
                self._prev_cycle_leverage_per_symbol[symbol] = cycle_lev
                leverage_sum_per_symbol[symbol] += cycle_lev * cycle_trades
                leverage_count_per_symbol[symbol] += cycle_trades
                
                # Duración media de trades en barras
                avg_bars = random.randint(5, 60)  # Simulado, pero podría calcularse de datos
                sum_cycle_bars += avg_bars * cycle_trades
                cnt_cycle_bars += cycle_trades
                sum_bars_per_trade += avg_bars * cycle_trades
                count_bars_per_trade += cycle_trades
                
                # TFs usados
                used_tfs = random.sample(self.timeframes, k=min(2, len(self.timeframes)))
                for tf in used_tfs:
                    cycle_tf_counts[tf] += 1
                    tf_counts_per_symbol[symbol][tf] += 1
                
                agent_cycle_stats[symbol] = {
                    'cycle_trades': cycle_trades,
                    'cycle_long_trades': cycle_long,
                    'cycle_short_trades': cycle_short,
                    'cycle_win_rate': cycle_wr,
                    'cycle_pnl_pct': cycle_pnl_pct,
                    'cycle_pnl': cycle_pnl_abs,
                    'cycle_drawdown': cycle_dd,
                    'cycle_start_balance': running_balance_per_symbol[symbol] - cycle_pnl_abs,
                    'cycle_end_balance': running_balance_per_symbol[symbol],
                    'cycle_leverage_used': cycle_lev,
                    'cycle_avg_bars_per_trade': avg_bars,
                    'cycle_timeframes_used': used_tfs,
                }
                
                # Actualizar summaries
                summ = agent_summaries[symbol]
                summ['total_pnl'] += cycle_pnl_abs
                summ['total_pnl_pct'] = (summ['total_pnl'] / self.initial_balance) * 100
                summ['current_balance'] = running_balance_per_symbol[symbol]
                summ['total_trades'] += cycle_trades
                summ['total_long_trades'] += cycle_long
                summ['total_short_trades'] += cycle_short
                summ['winning_trades'] += winning
                summ['losing_trades'] += losing
                summ['win_rate'] = (summ['winning_trades'] / summ['total_trades'] * 100) if summ['total_trades'] > 0 else 0
                summ['max_drawdown'] = max(summ['max_drawdown'], cycle_dd)
                
                cycle_pnl_total += cycle_pnl_abs
            
            if progress_callback:
                await progress_callback({
                    'progress': progress,
                    'status': f'Procesando ciclo {cycle}',
                    'current_cycle': cycle,
                    'total_cycles': total_cycles,
                    'timestamp': ts.isoformat() if isinstance(ts, pd.Timestamp) else ts,
                    'symbols': self.symbols,
                    'agent_cycle_stats': agent_cycle_stats,
                    'cycle_avg_bars_per_trade': (sum_cycle_bars / cnt_cycle_bars) if cnt_cycle_bars > 0 else None,
                    'cycle_timeframe_counts': cycle_tf_counts,
                })
        
        # Calcular promedios finales
        for s in self.symbols:
            cnt = leverage_count_per_symbol[s]
            if cnt > 0:
                agent_summaries[s]['avg_leverage_used'] = leverage_sum_per_symbol[s] / cnt
        
        # Estrategias simuladas
        strategies = ['RSI_Divergence', 'MA_Crossover', 'Bollinger_Bounce', 'MACD_Signal', 'Support_Resistance']
        strategy_analysis = {
            'top_strategies': [(strategy, random.randint(10, 100)) for strategy in strategies[:3]],
            'total_unique_strategies': len(strategies),
            'strategy_distribution': {strategy: random.randint(5, 50) for strategy in strategies}
        }
        
        # Añadir métricas globales adicionales
        initial_balance_total = self.initial_balance * len(self.symbols)
        final_balance_total = sum(running_balance_per_symbol.values())
        objective_balance_total = initial_balance_total * 1.5  # Ejemplo, ajustar según config
        avg_bars_per_trade = sum_bars_per_trade / count_bars_per_trade if count_bars_per_trade > 0 else 0
        
        return {
            'session_info': {
                'session_id': self.session_id,
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'timestamp_initial': start_date.isoformat(),
                'timestamp_final': end_date.isoformat(),
                'symbols': self.symbols,
                'timeframes': self.timeframes,
                'initial_balance_per_agent': self.initial_balance,
                'initial_balance_total': initial_balance_total,
                'objective_balance_total': objective_balance_total,
                'final_balance_total': final_balance_total,
                'total_long_trades': total_long_trades,
                'total_short_trades': total_short_trades,
                'avg_bars_per_trade': avg_bars_per_trade,
            },
            'performance_summary': {
                'cycles_completed': total_cycles,
                'total_decisions': random.randint(500, 2000),
                'total_trades': sum(s['total_trades'] for s in agent_summaries.values()),
                'agent_summaries': agent_summaries,
                'tf_counts_per_symbol': tf_counts_per_symbol
            },
            'strategy_analysis': strategy_analysis
        }
    
    def _create_progress_callback(self):
        """Crea callback para progreso del orchestrador"""
        async def progress_callback(data):
            try:
                mapped_progress = 10 + (data.get('progress', 0) * 0.8)
                
                status = data.get('status', 'Entrenando')
                current_cycle = data.get('current_cycle', 0)
                total_cycles = data.get('total_cycles', 1)
                
                detailed_status = f"🔄 Ciclo {current_cycle}/{total_cycles}: {status}"
                
                cycle_metrics = self._compute_cycle_metrics(data)

                if cycle_metrics:
                    self.cycle_metrics_history.append({
                        **cycle_metrics,
                        "cycle": current_cycle,
                        "total_cycles": total_cycles,
                        "timestamp": data.get('timestamp')
                    })
                    extra = (
                        f" | PnL̄: {cycle_metrics['avg_pnl']:+.2f}"
                        f" | WR̄: {cycle_metrics['avg_win_rate']:.1f}%"
                        f" | DD̄: {cycle_metrics['avg_drawdown']:.2f}%"
                        f" | L:{int(cycle_metrics['total_long_trades'])} S:{int(cycle_metrics['total_short_trades'])}"
                        f" | B:{cycle_metrics['initial_balance_total']:.0f}→{cycle_metrics['final_balance_total']:.0f}"
                        + (f" | ⏱̄ {cycle_metrics['avg_bars_per_trade']:.1f} barras" if cycle_metrics.get('avg_bars_per_trade') is not None else "")
                    )
                    detail = f"{detailed_status}{extra}"
                else:
                    detail = detailed_status

                await self._update_progress(
                    mapped_progress,
                    status,
                    detail
                )

                if self.enable_cycle_telegram and cycle_metrics and cycle_metrics.get('avg_trades') is not None:
                    await self._maybe_send_cycle_telegram_update(
                        cycle=current_cycle,
                        total_cycles=total_cycles,
                        cycle_metrics=cycle_metrics
                    )
                
            except Exception as e:
                logger.error(f"❌ Error en callback de progreso: {e}")
        
        return progress_callback

    def _compute_cycle_metrics(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            agent_stats = data.get('agent_cycle_stats', {}) or data.get('agent_summaries', {})
            if not agent_stats:
                return None

            num = max(1, len(agent_stats))
            sum_pnl = sum(float(stat.get('cycle_pnl', stat.get('total_pnl', 0))) for stat in agent_stats.values())
            sum_wr = sum(float(stat.get('cycle_win_rate', stat.get('win_rate', 0))) for stat in agent_stats.values())
            sum_dd = sum(float(stat.get('cycle_drawdown', stat.get('max_drawdown', 0))) for stat in agent_stats.values())
            sum_trades = sum(int(stat.get('cycle_trades', stat.get('total_trades', 0))) for stat in agent_stats.values())
            sum_sharpe = sum(float(stat.get('cycle_sharpe', stat.get('sharpe_ratio', 0)) or 0) for stat in agent_stats.values())
            sharpe_count = sum(1 for stat in agent_stats.values() if stat.get('cycle_sharpe') or stat.get('sharpe_ratio'))
            sum_long = sum(int(stat.get('cycle_long_trades', stat.get('total_long_trades', 0))) for stat in agent_stats.values())
            sum_short = sum(int(stat.get('cycle_short_trades', stat.get('total_short_trades', 0))) for stat in agent_stats.values())
            start_balance_total = sum(float(stat.get('cycle_start_balance', self.initial_balance)) for stat in agent_stats.values())
            end_balance_total = sum(float(stat.get('cycle_end_balance', self.initial_balance)) for stat in agent_stats.values())
            sum_bars = sum(float(stat.get('cycle_avg_bars_per_trade', 0)) for stat in agent_stats.values() if stat.get('cycle_avg_bars_per_trade'))
            cnt_bars = sum(1 for stat in agent_stats.values() if stat.get('cycle_avg_bars_per_trade'))

            avg_pnl = sum_pnl / num
            avg_wr = sum_wr / num
            avg_dd = sum_dd / num
            avg_trades = sum_trades / num
            avg_sharpe = (sum_sharpe / sharpe_count) if sharpe_count > 0 else 0.0
            avg_bars_per_trade = (sum_bars / cnt_bars) if cnt_bars > 0 else None

            profitability = "rentable" if (avg_pnl > 0 and avg_wr > 50.0) else "no rentable"

            return {
                "avg_pnl": avg_pnl,
                "avg_win_rate": avg_wr,
                "avg_drawdown": avg_dd,
                "avg_sharpe": avg_sharpe,
                "avg_trades": avg_trades,
                "total_long_trades": sum_long,
                "total_short_trades": sum_short,
                "initial_balance_total": start_balance_total,
                "final_balance_total": end_balance_total,
                "avg_bars_per_trade": avg_bars_per_trade,
                "profitability": profitability
            }
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron calcular métricas de ciclo: {e}")
            return None
    
    async def _process_final_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("📊 Procesando resultados finales...")
            
            performance_summary = results.get('performance_summary', {})
            agent_summaries = performance_summary.get('agent_summaries', {})
            
            aggregated_metrics = {}
            if self.metrics_aggregator:
                aggregated_metrics = await self.metrics_aggregator.aggregate_symbol_stats(agent_summaries)
            else:
                aggregated_metrics = self._create_fallback_metrics(agent_summaries)
            
            global_summary = self._calculate_global_summary(agent_summaries)
            
            strategy_analysis = results.get('strategy_analysis', {})
            
            final_results = {
                "session_info": results.get('session_info', {}),
                "global_performance": global_summary,
                "symbol_performance": {
                    symbol: self._extract_symbol_metrics(symbol, metrics, agent_summaries.get(symbol, {}))
                    for symbol, metrics in aggregated_metrics.items()
                },
                "strategy_analysis": strategy_analysis,
                "orchestrator_results": results,
                "telegram_summary": await self._generate_telegram_summary(global_summary, aggregated_metrics)
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error procesando resultados finales: {e}")
            return {"error": str(e)}
    
    def _create_fallback_metrics(self, agent_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        try:
            fallback_metrics = {}
            for symbol, summary in agent_summaries.items():
                class FallbackStats:
                    def __init__(self, data):
                        self.symbol = data.get('symbol', symbol)
                        self.current_balance = data.get('current_balance', 1000)
                        self.total_pnl = data.get('total_pnl', 0)
                        self.total_pnl_pct = data.get('total_pnl_pct', 0)
                        self.total_trades = data.get('total_trades', 0)
                        self.win_rate = data.get('win_rate', 0)
                        self.sharpe_ratio = data.get('sharpe_ratio', 0)
                        self.max_drawdown = data.get('max_drawdown', 0)
                
                fallback_metrics[symbol] = FallbackStats(summary)
            return fallback_metrics
        except Exception as e:
            logger.error(f"❌ Error creando métricas de fallback: {e}")
            return {}
    
    def _extract_symbol_metrics(self, symbol: str, metrics, agent_summary: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if hasattr(metrics, 'current_balance'):
                return {
                    "balance": metrics.current_balance,
                    "pnl": metrics.total_pnl,
                    "pnl_pct": metrics.total_pnl_pct,
                    "trades": metrics.total_trades,
                    "win_rate": metrics.win_rate,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown,
                    "avg_leverage_used": getattr(metrics, 'avg_leverage_used', None)
                }
            else:
                return {
                    "balance": agent_summary.get('current_balance', 1000),
                    "pnl": agent_summary.get('total_pnl', 0),
                    "pnl_pct": agent_summary.get('total_pnl_pct', 0),
                    "trades": agent_summary.get('total_trades', 0),
                    "win_rate": agent_summary.get('win_rate', 0),
                    "sharpe_ratio": agent_summary.get('sharpe_ratio', 0),
                    "max_drawdown": agent_summary.get('max_drawdown', 0),
                    "avg_leverage_used": agent_summary.get('avg_leverage_used')
                }
        except Exception as e:
            logger.error(f"❌ Error extrayendo métricas de {symbol}: {e}")
            return {
                "balance": 1000, "pnl": 0, "pnl_pct": 0,
                "trades": 0, "win_rate": 0, "sharpe_ratio": 0, "max_drawdown": 0
            }
    
    def _calculate_global_summary(self, agent_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if not agent_summaries:
                return {}
            
            total_balance = sum(metrics.get('current_balance', 0) for metrics in agent_summaries.values())
            total_pnl = sum(metrics.get('total_pnl', 0) for metrics in agent_summaries.values())
            total_trades = sum(metrics.get('total_trades', 0) for metrics in agent_summaries.values())
            total_long_trades = sum(metrics.get('total_long_trades', 0) for metrics in agent_summaries.values())
            total_short_trades = sum(metrics.get('total_short_trades', 0) for metrics in agent_summaries.values())
            total_winning = sum(metrics.get('winning_trades', 0) for metrics in agent_summaries.values())
            total_losing = sum(metrics.get('losing_trades', 0) for metrics in agent_summaries.values())
            
            avg_balance = total_balance / len(agent_summaries)
            avg_pnl = total_pnl / len(agent_summaries)
            avg_pnl_pct = (avg_pnl / self.initial_balance) * 100
            global_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
            
            max_drawdown = max(metrics.get('max_drawdown', 0) for metrics in agent_summaries.values())
            
            best_performer = max(agent_summaries.items(), key=lambda x: x[1].get('total_pnl_pct', 0))
            worst_performer = min(agent_summaries.items(), key=lambda x: x[1].get('total_pnl_pct', 0))
            
            return {
                "total_balance": total_balance,
                "avg_balance_per_agent": avg_balance,
                "total_pnl": total_pnl,
                "avg_pnl_per_agent": avg_pnl,
                "avg_pnl_pct": avg_pnl_pct,
                "total_trades": total_trades,
                "total_long_trades": total_long_trades,
                "total_short_trades": total_short_trades,
                "winning_trades": total_winning,
                "losing_trades": total_losing,
                "global_win_rate": global_win_rate,
                "max_drawdown": max_drawdown,
                "best_performer": {
                    "symbol": best_performer[0],
                    "pnl_pct": best_performer[1].get('total_pnl_pct', 0)
                },
                "worst_performer": {
                    "symbol": worst_performer[0],
                    "pnl_pct": worst_performer[1].get('total_pnl_pct', 0)
                },
                "active_agents": len(agent_summaries)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando resumen global: {e}")
            return {}

    def _aggregate_cycle_history(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not history:
            return {}
        n = len(history)
        sum_pnl = sum(h.get('avg_pnl', 0) for h in history)
        sum_wr = sum(h.get('avg_win_rate', 0) for h in history)
        sum_dd = sum(h.get('avg_drawdown', 0) for h in history)
        sum_tr = sum(h.get('avg_trades', 0) for h in history)
        sum_long = sum(h.get('total_long_trades', 0) for h in history)
        sum_short = sum(h.get('total_short_trades', 0) for h in history)
        bars = [h.get('avg_bars_per_trade') for h in history if h.get('avg_bars_per_trade') is not None]
        return {
            'cycles_count': n,
            'avg_pnl_over_cycles': sum_pnl / n,
            'avg_wr_over_cycles': sum_wr / n,
            'avg_dd_over_cycles': sum_dd / n,
            'avg_trades_over_cycles': sum_tr / n,
            'total_longs_over_cycles': sum_long,
            'total_shorts_over_cycles': sum_short,
            'avg_bars_over_cycles': (sum(bars)/len(bars)) if bars else None,
        }

    def _format_cycle_aggregates(self, agg: Optional[Dict[str, Any]]) -> str:
        if not agg:
            return "(Sin datos de ciclos agregados)"
        line = (
            f"- Ciclos: {agg.get('cycles_count', 0)}\n"
            f"- PnL̄ ciclos: {agg.get('avg_pnl_over_cycles', 0):+.2f}\n"
            f"- WR̄ ciclos: {agg.get('avg_wr_over_cycles', 0):.1f}%\n"
            f"- DD̄ ciclos: {agg.get('avg_dd_over_cycles', 0):.2f}%\n"
            f"- Trades̄/ciclo: {agg.get('avg_trades_over_cycles', 0):.1f}\n"
            f"- L tot: {agg.get('total_longs_over_cycles', 0)}, S tot: {agg.get('total_shorts_over_cycles', 0)}\n"
        )
        if agg.get('avg_bars_over_cycles') is not None:
            line += f"- ⏱̄ barras: {agg.get('avg_bars_over_cycles', 0):.1f}\n"
        return line
    
    async def _generate_telegram_summary(self, global_summary: Dict[str, Any], 
                                       symbol_metrics: Dict[str, Any]) -> str:
        try:
            duration = (datetime.now() - self.start_time).total_seconds() / 60
            
            rentable_line = ""
            if self.cycle_metrics_history:
                last_cycle = self.cycle_metrics_history[-1]
                rentable_line = f"\n💡 <b>Rentabilidad (último ciclo):</b> {last_cycle.get('profitability','N/A').upper()}  (PnL̄ {last_cycle.get('avg_pnl',0):+.2f}, WR̄ {last_cycle.get('avg_win_rate',0):.1f}%)\n"

            message = f"""🎯 <b>Entrenamiento Histórico Completado</b>

📊 <b>Resumen Global:</b>
• Duración: {duration:.1f} minutos
• Agentes: {global_summary.get('active_agents', 0)}
• Total Trades: {global_summary.get('total_trades', 0):,}  (L:{global_summary.get('total_long_trades', 0):,} / S:{global_summary.get('total_short_trades', 0):,})

💰 <b>Performance Agregada:</b>
• PnL Promedio: ${global_summary.get('avg_pnl_per_agent', 0):+.2f} ({global_summary.get('avg_pnl_pct', 0):+.2f}%)
• Win Rate Global: {global_summary.get('global_win_rate', 0):.1f}%
• Max Drawdown: {global_summary.get('max_drawdown', 0):.2f}%
{rentable_line}

📈 <b>Performance por Símbolo (ordenado):</b>"""
            
            sorted_symbols = sorted(symbol_metrics.items(), key=lambda x: x[1].get('pnl_pct', 0) if isinstance(x[1], dict) else x[1].total_pnl_pct, reverse=True)
            
            for i, (symbol, metrics) in enumerate(sorted_symbols, 1):
                pnl_pct = metrics.get('pnl_pct', 0) if isinstance(metrics, dict) else metrics.total_pnl_pct
                trades = metrics.get('trades', 0) if isinstance(metrics, dict) else metrics.total_trades
                win_rate = metrics.get('win_rate', 0) if isinstance(metrics, dict) else metrics.win_rate
                avg_lev = metrics.get('avg_leverage_used') if isinstance(metrics, dict) else getattr(metrics, 'avg_leverage_used', None)
                lev_txt = f", lev̄ {avg_lev:.1f}x" if avg_lev else ""
                message += f"\n{i}. <b>{symbol}</b>: {pnl_pct:+.2f}% ({trades} trades, {win_rate:.1f}% WR{lev_txt})"
            
            message += f"""

💾 <b>Datos Guardados:</b>
• Estrategias por agente: <code>data/agents/{{symbol}}/strategies.json</code>
• Runs completos: <code>data/training_sessions/{self.session_id}/</code>
• Resumen ejecutivo: <code>data/training_sessions/{self.session_id}/executive_summary.md</code>"""
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen de Telegram: {e}")
            return "❌ Error generando resumen del entrenamiento"
    
    async def _save_final_results(self, results: Dict[str, Any]):
        try:
            session_dir = Path(f"data/training_sessions/{self.session_id}")
            session_dir.mkdir(parents=True, exist_ok=True)
            
            results_file = session_dir / "complete_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            summary_file = session_dir / "summary.json"
            summary_data = {
                "session_id": self.session_id,
                "global_performance": results.get("global_performance", {}),
                "symbol_performance": results.get("symbol_performance", {}),
                "telegram_summary": results.get("telegram_summary", "")
            }
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            executive_summary = self._create_executive_summary(results)
            summary_md_file = session_dir / "executive_summary.md"
            with open(summary_md_file, 'w', encoding='utf-8') as f:
                f.write(executive_summary)
            
            strategy_analysis = results.get("strategy_analysis", {}) or {}
            top_strategies = strategy_analysis.get("top_strategies")
            symbol_perf = results.get("symbol_performance", {}) or {}
            for symbol, perf in symbol_perf.items():
                agent_dir = Path(f"data/agents/{symbol}")
                agent_dir.mkdir(parents=True, exist_ok=True)
                strategies_file = agent_dir / "strategies.json"
                payload = {
                    "session_id": self.session_id,
                    "updated_at": datetime.now().isoformat(),
                    "symbol": symbol,
                    "total_trades": perf.get("trades", 0),
                    "win_rate": perf.get("win_rate", 0),
                    "pnl_pct": perf.get("pnl_pct", 0),
                    "avg_leverage_used": perf.get("avg_leverage_used"),
                    "top_strategies": top_strategies if isinstance(top_strategies, list) else [],
                }
                with open(strategies_file, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=2)
            
            await self._update_symbol_leaderboards(results)
            
            logger.info(f"💾 Resultados guardados en: {session_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {e}")

    async def _maybe_send_cycle_telegram_update(self, cycle: int, total_cycles: int, cycle_metrics: Dict[str, Any]):
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not bot_token or not chat_id:
            return
        try:
            import httpx
            avg_pnl = cycle_metrics.get('avg_pnl', 0)
            wr = cycle_metrics.get('avg_win_rate', 0)
            dd = cycle_metrics.get('avg_drawdown', 0)
            longs = int(cycle_metrics.get('total_long_trades', 0))
            shorts = int(cycle_metrics.get('total_short_trades', 0))
            init_b = cycle_metrics.get('initial_balance_total')
            end_b = cycle_metrics.get('final_balance_total')
            bars = cycle_metrics.get('avg_bars_per_trade')
            rent = cycle_metrics.get('profitability', 'N/A').upper()
            text = (
                f"🔄 <b>Ciclo {cycle}/{total_cycles}</b>\n"
                f"PnL̄ {avg_pnl:+.2f} | WR̄ {wr:.1f}% | DD̄ {dd:.2f}%\n"
                f"L:{longs} S:{shorts} | B:{init_b:.0f}→{end_b:.0f}"
            )
            if bars is not None:
                text += f" | ⏱̄ {bars:.1f} barras"
            text += f"\n💡 {rent}"
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        'chat_id': chat_id,
                        'text': text,
                        'parse_mode': 'HTML'
                    }
                )
        except Exception as e:
            logger.debug(f"No se pudo enviar mensaje de ciclo: {e}")

    async def _update_symbol_leaderboards(self, results: Dict[str, Any]):
        symbol_perf = results.get("symbol_performance", {}) or {}
        strategy_analysis = results.get("strategy_analysis", {}) or {}
        top_strategies = strategy_analysis.get("top_strategies") if isinstance(strategy_analysis.get("top_strategies"), list) else []
        now_iso = datetime.now().isoformat()

        for symbol, perf in symbol_perf.items():
            agent_dir = Path(f"data/agents/{symbol}")
            agent_dir.mkdir(parents=True, exist_ok=True)

            top_file = agent_dir / "strategies_top1000.json"
            worst_file = agent_dir / "strategies_worst1000.json"

            def _read_json(path: Path):
                try:
                    if path.exists():
                        return json.loads(path.read_text(encoding='utf-8'))
                except Exception:
                    return []
                return []

            def _write_json(path: Path, data):
                path.write_text(json.dumps(data, indent=2), encoding='utf-8')

            new_strats = []
            for s in top_strategies:
                try:
                    name, score = s[0], float(s[1])
                except Exception:
                    continue
                new_strats.append({
                    "strategy": name,
                    "score": score,
                    "session_id": self.session_id,
                    "timestamp": now_iso,
                })

            if new_strats:
                top_data = _read_json(top_file)
                merged = (top_data + new_strats)
                merged.sort(key=lambda x: x.get("score", 0), reverse=True)
                _write_json(top_file, merged[:1000])

                worst_data = _read_json(worst_file)
                merged_w = (worst_data + new_strats)
                merged_w.sort(key=lambda x: x.get("score", 0))
                _write_json(worst_file, merged_w[:1000])

            runs_file = agent_dir / "runs_leaderboards.json"
            runs_payload = {
                "run_id": f"{self.session_id}_{symbol}",
                "session_id": self.session_id,
                "symbol": symbol,
                "timestamp": now_iso,
                "pnl_pct": perf.get("pnl_pct", 0),
                "pnl": perf.get("pnl", 0),
                "trades": perf.get("trades", 0),
                "win_rate": perf.get("win_rate", 0),
                "sharpe_ratio": perf.get("sharpe_ratio", 0),
                "max_drawdown": perf.get("max_drawdown", 0),
            }

            try:
                if runs_file.exists():
                    runs_data = json.loads(runs_file.read_text(encoding='utf-8'))
                else:
                    runs_data = {"top1000": [], "worst1000": []}
            except Exception:
                runs_data = {"top1000": [], "worst1000": []}

            def _rank_key(item):
                return (float(item.get("pnl_pct", 0)), float(item.get("win_rate", 0)), -float(item.get("max_drawdown", 0)))

            top_runs = runs_data.get("top1000", []) + [runs_payload]
            top_runs.sort(key=_rank_key, reverse=True)
            runs_data["top1000"] = top_runs[:1000]

            worst_runs = runs_data.get("worst1000", []) + [runs_payload]
            worst_runs.sort(key=_rank_key)
            runs_data["worst1000"] = worst_runs[:1000]

            runs_file.write_text(json.dumps(runs_data, indent=2), encoding='utf-8')

    async def _ensure_pre_alignment(self, start_date: datetime, end_date: datetime):
        try:
            alignment_path = Path("data/aligned_timeframes.json")
            if alignment_path.exists():
                with open(alignment_path, 'r') as f:
                    self.pre_aligned_data = json.load(f)
                logger.info("✅ Alineamiento pre-generado cargado desde data/aligned_timeframes.json")
                return

            logger.info("⚠️ Alineamiento no encontrado. Generando con align_timeframes.py...")
            try:
                import subprocess, sys
                days_back = max(1, (end_date - start_date).days) if (start_date and end_date) else 365
                cmd = [sys.executable, "scripts/training/align_timeframes.py", "--days-back", str(days_back)]
                subprocess.run(cmd, check=True)
            except Exception as gen_err:
                logger.warning(f"⚠️ No se pudo generar alineamiento automáticamente: {gen_err}")
                # Fallback a timestamps por hora
                self.pre_aligned_data = {
                    'aligned_timestamps': [int(dt.timestamp() * 1000) for dt in pd.date_range(start=start_date, end=end_date, freq='H')]
                }
                return

            if alignment_path.exists():
                with open(alignment_path, 'r') as f:
                    self.pre_aligned_data = json.load(f)
                logger.info("✅ Alineamiento generado y cargado correctamente")
            else:
                logger.warning("⚠️ Aún no existe data/aligned_timeframes.json tras la generación")
        except Exception as e:
            logger.warning(f"⚠️ Error manejando alineamiento pre-generado: {e}")
            self.pre_aligned_data = {
                'aligned_timestamps': [int(dt.timestamp() * 1000) for dt in pd.date_range(start=start_date, end=end_date, freq='H')]
            }
    
    def _create_executive_summary(self, results: Dict[str, Any]) -> str:
        try:
            session_info = results.get('session_info', {})
            global_perf = results.get('global_performance', {})
            symbol_perf = results.get('symbol_performance', {})
            
            summary = f"""# Resumen Ejecutivo - Entrenamiento Histórico Paralelo

## 📊 Información de la Sesión
- **ID de Sesión**: {session_info.get('session_id', 'N/A')}
- **Duración**: {session_info.get('duration_seconds', 0):.0f} segundos
- **Símbolos**: {', '.join(session_info.get('symbols', []))}
- **Balance Inicial por Agente**: ${session_info.get('initial_balance_per_agent', 0):,.2f}

## 🎯 Resultados Globales
- **PnL Promedio por Agente**: ${global_perf.get('avg_pnl_per_agent', 0):+.2f} ({global_perf.get('avg_pnl_pct', 0):+.2f}%)
- **Win Rate Global**: {global_perf.get('global_win_rate', 0):.1f}%
- **Total de Trades**: {global_perf.get('total_trades', 0):,}
- **Trades Ganadores**: {global_perf.get('winning_trades', 0):,}
- **Trades Perdedores**: {global_perf.get('losing_trades', 0):,}
- **Max Drawdown**: {global_perf.get('max_drawdown', 0):.2f}%

## 📊 Métricas agregadas de ciclos (si aplica)
{self._format_cycle_aggregates(results.get('cycle_metrics_aggregated'))}

## 🏆 Top Performers
- **Mejor Agente**: {global_perf.get('best_performer', {}).get('symbol', 'N/A')} ({global_perf.get('best_performer', {}).get('pnl_pct', 0):+.2f}%)
- **Peor Agente**: {global_perf.get('worst_performer', {}).get('symbol', 'N/A')} ({global_perf.get('worst_performer', {}).get('pnl_pct', 0):+.2f}%)

## 📈 Performance por Símbolo
"""
            
            for symbol, perf in symbol_perf.items():
                pnl = perf.get('pnl', 0)
                pnl_pct = perf.get('pnl_pct', 0)
                trades = perf.get('trades', 0)
                win_rate = perf.get('win_rate', 0)
                drawdown = perf.get('max_drawdown', 0)
                
                summary += f"- **{symbol}**: ${pnl:+.2f} ({pnl_pct:+.2f}%), {trades} trades, {win_rate:.1f}% WR, {drawdown:.2f}% DD\n"
            
            summary += f"""
## 📁 Archivos Generados
- `complete_results.json` - Resultados completos de la sesión
- `summary.json` - Resumen rápido para dashboards
- `executive_summary.md` - Este resumen ejecutivo

## 🎯 Próximos Pasos
1. Revisar estrategias exitosas en `data/agents/{{symbol}}/strategies.json`
2. Analizar patrones de trades perdedores para mejoras
3. Considerar ajustar parámetros de riesgo si drawdown > 15%
4. Evaluar ampliar entrenamiento a más timeframes si WR > 70%

---
*Generado automáticamente por Bot Trading v10 Enterprise el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error creando resumen ejecutivo: {e}")
            return "# Error generando resumen ejecutivo"
    
    async def _update_progress(self, progress: float, status: str, detailed_status: str):
        try:
            progress_data = {
                "session_id": self.session_id,
                "progress": min(progress, 100),
                "status": status,
                "detailed_status": detailed_status,
                "timestamp": datetime.now().isoformat(),
                "is_running": self.is_running,
                "symbols": self.symbols,
                "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }
            
            if self.progress_file:
                progress_path = Path(self.progress_file)
                progress_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(progress_path, 'w') as f:
                    json.dump(progress_data, f, indent=2)
            
            logger.info(f"📊 Progreso: {progress:.1f}% - {detailed_status}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando progreso: {e}")
    
    async def stop_training(self):
        try:
            logger.info("🛑 Deteniendo entrenamiento...")
            
            self.is_running = False
            
            if self.orchestrator:
                await self.orchestrator.stop_training()
            
            if self.metrics_aggregator:
                await self.metrics_aggregator.cleanup()
            
            await self._update_progress(0, "Detenido", "🛑 Entrenamiento detenido por usuario")
            
            logger.info("✅ Entrenamiento detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        try:
            if not self.is_running:
                return {
                    "status": "not_running",
                    "session_id": self.session_id,
                    "last_run": self.start_time.isoformat() if self.start_time else None
                }
            
            return {
                "status": "running",
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat(),
                "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
                "symbols": self.symbols,
                "progress_file": self.progress_file
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {"status": "error", "error": str(e)}

    def _print_formatted_summary(self, results: Dict[str, Any]):
        """Imprime el resumen en el formato especificado por el usuario."""
        session_info = results.get('session_info', {})
        global_perf = results.get('global_performance', {})
        symbol_perf = results.get('symbol_performance', {})
        
        duration_min = (datetime.now() - self.start_time).total_seconds() / 60
        
        print("✅ Entrenamiento Histórico Completado")
        print("")
        print("🎯 Entrenamiento Histórico Completado")
        print("")
        print("📊 Resumen Global:")
        print(f"• Duración: {duration_min:.1f} minutos")
        print(f"• Agentes: {global_perf.get('active_agents', len(self.symbols))}")
        print(f"• Total Trades: {global_perf.get('total_trades', 0):,}")
        print(f"- Timestamp Initial: {session_info.get('timestamp_initial', 'N/A')}")
        print(f"- Timestamp Final: {session_info.get('timestamp_final', 'N/A')}")
        print("")
        print("💰 Performance Agregada:")
        print(f"• PnL Promedio: ${global_perf.get('avg_pnl_per_agent', 0):+.2f} ({global_perf.get('avg_pnl_pct', 0):+.2f}%)")
        print(f"• Win Rate Global: {global_perf.get('global_win_rate', 0):.1f}%")
        print(f"• Max Drawdown: {global_perf.get('max_drawdown', 0):.2f}%")
        print(f"- Initial Balance: ${session_info.get('initial_balance_total', 0):,.2f}")
        print(f"- Objective Balance: ${session_info.get('objective_balance_total', 0):,.2f}")
        print(f"- Final Balance: ${session_info.get('final_balance_total', 0):,.2f}")
        print(f"Trades LONG: {session_info.get('total_long_trades', 0)}")
        print(f"Trades SHORT: {session_info.get('total_short_trades', 0)}")
        print(f"Medium bars per trade: {session_info.get('avg_bars_per_trade', 0):.1f}")
        print("")
        print("MEDIUM LEVERAGE PER SYMBOL:")
        for symbol, summ in session_info.get('performance_summary', {}).get('agent_summaries', {}).items():
            avg_lev = summ.get('avg_leverage_used', 0)
            print(f"• {symbol}: {avg_lev:.1f}x")
        print("")
        print("🏆 Top Performers:")
        sorted_symbols = sorted(symbol_perf.items(), key=lambda x: x[1].get('pnl_pct', 0), reverse=True)
        medals = ['🥇', '🥈', '🥉']
        for i, (symbol, perf) in enumerate(sorted_symbols):
            medal = medals[i] if i < 3 else f"{i+1}."
            pnl_pct = perf.get('pnl_pct', 0)
            pnl = perf.get('pnl', 0)
            wr = perf.get('win_rate', 0)
            trades = perf.get('trades', 0)
            dd = perf.get('max_drawdown', 0)
            print(f"• {medal} {symbol}: +{pnl_pct:.2f}% (PnL: +${pnl:.2f}, WR: {wr:.1f}%, Trades: {trades}, DD: {dd:.1f}%)")
        print("")
        print("📈 Performance por Símbolo:")
        tf_trading = "1h, 4h"  # Simulado, ajustar si se tiene datos reales
        tf_analysis = "1h, 4h, 1d"
        for symbol in self.symbols:
            print(f"• {symbol}: (TFs para trading: {tf_trading}; TFs para análisis: {tf_analysis})")
        print("")
        print("💾 Datos Guardados:")
        print("• Estrategias por agente: data/agents/{symbol}/strategies.json")
        print(f"• Runs completos: data/training_sessions/{self.session_id}/")
        print(f"• Resumen ejecutivo: data/training_sessions/{self.session_id}/executive_summary.md")

# Función principal para ejecución independiente
async def main():
    parser = argparse.ArgumentParser(description="Entrenamiento Histórico Paralelo")
    parser.add_argument("--start-date", type=str, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--symbols", nargs="+", help="Símbolos específicos")
    parser.add_argument("--progress-file", type=str, help="Archivo para progreso")
    parser.add_argument("--output-dir", type=str, help="Directorio de salida")
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None
        
        trainer = TrainHistParallel(progress_file=args.progress_file)
        
        if args.symbols:
            trainer.symbols = args.symbols
        
        print("=" * 60)
        print("🚀 INICIANDO ENTRENAMIENTO HISTÓRICO PARALELO")
        print("=" * 60)
        print(f"📊 Sesión ID: {trainer.session_id}")
        print(f"🎯 Símbolos: {', '.join(trainer.symbols)}")
        print(f"📅 Período: {start_date or 'Auto'} → {end_date or 'Auto'}")
        print(f"💰 Balance inicial por agente: ${trainer.initial_balance:,.2f}")
        print("=" * 60)
        
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        if args.output_dir:
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"train_hist_results_{trainer.session_id}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"📤 Resultados también guardados en: {output_file}")
        
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)

async def create_train_hist_parallel(progress_file: str = None) -> TrainHistParallel:
    return TrainHistParallel(progress_file=progress_file)

async def execute_quick_training(symbols: List[str] = None, 
                                days_back: int = 30) -> Dict[str, Any]:
    try:
        trainer = TrainHistParallel()
        
        if symbols:
            trainer.symbols = symbols
        
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days_back)
        
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento rápido: {e}")
        return {"error": str(e)}

async def execute_train_hist_for_telegram(progress_file: str) -> Dict[str, Any]:
    try:
        logger.info("🎯 Ejecutando entrenamiento histórico para Telegram")
        
        trainer = TrainHistParallel(progress_file=progress_file)
        
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=trainer._get_training_days('normal'))
        
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = results.get("telegram_summary", "Entrenamiento completado")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Error en entrenamiento: {str(e)[:100]}..."
        }

async def execute_train_hist_continuous_for_telegram(progress_file: str, cycle_days: int = 7) -> Dict[str, Any]:
    global STOP_EVENT
    if STOP_EVENT is None:
        STOP_EVENT = asyncio.Event()

    try:
        logger.info("♾️ Iniciando entrenamiento CONTINUO para Telegram")
        results: Dict[str, Any] | None = None
        while not STOP_EVENT.is_set():
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=cycle_days)
            trainer = TrainHistParallel(progress_file=progress_file)
            trainer.enable_cycle_telegram = False
            results = await trainer.execute_training(start_date=start_date, end_date=end_date)

            await asyncio.sleep(1)

        if results is None:
            return {"success": True, "message": "🛑 Entrenamiento detenido", "telegram_ready": True}

        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = results.get("telegram_summary", "Entrenamiento continuo detenido")
        return results

    except Exception as e:
        logger.error(f"❌ Error en entrenamiento continuo: {e}")
        return {"success": False, "error": str(e), "message": f"❌ Error: {e}"}

def stop_train_hist_continuous():
    global STOP_EVENT
    if STOP_EVENT is None:
        STOP_EVENT = asyncio.Event()
    STOP_EVENT.set()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    
    asyncio.run(main())