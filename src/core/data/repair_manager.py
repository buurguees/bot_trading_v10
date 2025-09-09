#!/usr/bin/env python3
"""
Gestor de Reparación de Datos Históricos - Trading Bot v10 Enterprise
====================================================================

Maneja la reparación y depuración de datos históricos existentes.
Incluye eliminación de duplicados, corrección de orden, relleno de gaps,
validación de integridad y alineación multi-timeframe.

Características:
- Pipeline completo de limpieza por archivo
- Detección y reparación de gaps precisos
- Alineación temporal perfecta por símbolo
- Reportes detallados de alineación
- Resiliencia con backoff exponencial
- Telemetría completa

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import yaml
import json
import time
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import ccxt
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.data.history_manager import HistoryManager

logger = logging.getLogger(__name__)

@dataclass
class RepairStats:
    """Estadísticas de reparación por archivo"""
    symbol: str
    timeframe: str
    file_path: str
    rows_before: int
    rows_after: int
    new_rows: int
    dup_removed: int
    gaps_fixed: int
    retries: int
    rate_limit_hits: int
    api_errors: int
    files_written: int
    status: str
    errors: List[str]

@dataclass
class AlignmentReport:
    """Reporte de alineación por símbolo"""
    symbol: str
    timestamp: str
    timeframes: Dict[str, Dict[str, Any]]
    total_expected_bars: int
    total_actual_bars: int
    total_gaps_fixed: int
    total_residual_gaps: int
    alignment_score: float
    status: str

@dataclass
class RepairStatus:
    """Estado de reparación en tiempo real"""
    total_symbols: int
    total_timeframes: int
    completed_tasks: int
    current_symbol: str
    current_timeframe: str
    current_action: str
    progress_percentage: float
    start_time: datetime
    elapsed_time: str
    current_stats: RepairStats
    alignment_status: str

class RepairManager:
    """Gestor de reparación de datos históricos"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el gestor de reparación"""
        self.history_manager = HistoryManager(config_path)
        self.config = self.history_manager.config
        self.historical_root = self.history_manager.historical_root
        self.update_rate_sec = self.history_manager.update_rate_sec
        
        # Configurar directorios
        self._setup_directories()
        
        # Inicializar exchange
        self.exchange = self.history_manager.exchange
        
        # Telemetría
        self.telemetry = {
            'started_at': None,
            'ended_at': None,
            'duration_sec': 0,
            'symbols': {}
        }
        
        logger.info("🔧 Gestor de reparación de datos históricos inicializado")
    
    def _setup_directories(self):
        """Configura directorios necesarios"""
        directories = [
            'logs',
            'reports',
            'reports/alignment'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def list_symbols_and_tfs(self) -> Tuple[List[str], List[str]]:
        """Obtiene símbolos y timeframes de la configuración"""
        return self.history_manager.list_symbols_and_tfs()
    
    def repair_all_historical_data(self) -> Dict[str, Any]:
        """Repara todos los datos históricos"""
        try:
            self.telemetry['started_at'] = datetime.now().isoformat()
            start_time = datetime.now()
            
            # Obtener símbolos y timeframes
            symbols, timeframes = self.list_symbols_and_tfs()
            
            # Inicializar telemetría
            for symbol in symbols:
                self.telemetry['symbols'][symbol] = {
                    'timeframes': {},
                    'total_rows_before': 0,
                    'total_rows_after': 0,
                    'total_duplicates_removed': 0,
                    'total_gaps_fixed': 0,
                    'total_retries': 0,
                    'total_rate_limit_hits': 0,
                    'total_api_errors': 0,
                    'total_files_written': 0
                }
            
            # Procesar cada símbolo
            all_repair_stats = []
            alignment_reports = []
            
            for symbol in symbols:
                logger.info(f"🔧 Procesando símbolo: {symbol}")
                
                # Reparar timeframes del símbolo
                symbol_stats = self._repair_symbol_timeframes(symbol, timeframes)
                all_repair_stats.extend(symbol_stats)
                
                # Generar reporte de alineación
                alignment_report = self._align_symbol_timeframes(symbol, timeframes)
                if alignment_report:
                    alignment_reports.append(alignment_report)
                    self._write_alignment_report(alignment_report)
            
            # Calcular duración total
            end_time = datetime.now()
            duration = end_time - start_time
            self.telemetry['ended_at'] = end_time.isoformat()
            self.telemetry['duration_sec'] = duration.total_seconds()
            
            # Generar resumen final
            summary = self._generate_repair_summary(all_repair_stats, alignment_reports)
            
            # Guardar telemetría
            self._save_telemetry()
            
            logger.info("✅ Reparación de datos históricos completada")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error en reparación de datos históricos: {e}")
            raise
    
    def _repair_symbol_timeframes(self, symbol: str, timeframes: List[str]) -> List[RepairStats]:
        """Repara timeframes de un símbolo específico"""
        repair_stats = []
        
        for timeframe in timeframes:
            try:
                logger.info(f"🔧 Reparando {symbol} {timeframe}")
                
                # Construir ruta del archivo
                file_path = self.historical_root / symbol / f"{timeframe}.csv"
                
                # Inicializar estadísticas
                stats = RepairStats(
                    symbol=symbol,
                    timeframe=timeframe,
                    file_path=str(file_path),
                    rows_before=0,
                    rows_after=0,
                    new_rows=0,
                    dup_removed=0,
                    gaps_fixed=0,
                    retries=0,
                    rate_limit_hits=0,
                    api_errors=0,
                    files_written=0,
                    status="processing",
                    errors=[]
                )
                
                # Pipeline de reparación
                df_repaired = self._repair_single_file(symbol, timeframe, str(file_path), stats)
                
                # Actualizar estadísticas finales
                stats.rows_after = len(df_repaired)
                stats.new_rows = stats.rows_after - stats.rows_before
                stats.files_written = 1 if stats.rows_after > 0 else 0
                stats.status = "completed" if stats.errors == [] else "warning"
                
                repair_stats.append(stats)
                
                # Actualizar telemetría
                self._update_telemetry(symbol, timeframe, stats)
                
            except Exception as e:
                logger.error(f"❌ Error reparando {symbol} {timeframe}: {e}")
                stats.status = "error"
                stats.errors.append(str(e))
                repair_stats.append(stats)
        
        return repair_stats
    
    def _repair_single_file(self, symbol: str, timeframe: str, file_path: str, stats: RepairStats) -> pd.DataFrame:
        """Repara un archivo individual siguiendo el pipeline completo"""
        try:
            # 1. Cargar CSV y normalizar schema
            df = self._load_and_normalize_csv(file_path, stats)
            stats.rows_before = len(df)
            
            if df.empty:
                logger.warning(f"⚠️ Archivo vacío: {file_path}")
                return df
            
            # 2. Eliminar duplicados por open_time
            df_clean, duplicates_removed = self.history_manager.dedupe_by_open_time(df)
            stats.dup_removed = duplicates_removed
            
            # 3. Ordenar por open_time ascendente
            df_sorted = df_clean.sort_values('open_time').reset_index(drop=True)
            
            # 4. Detectar gaps
            gaps = self.history_manager.detect_gaps(df_sorted, timeframe)
            stats.gaps_fixed = len(gaps)
            
            # 5. Re-descargar rangos faltantes
            if gaps:
                logger.info(f"🔧 Reparando {len(gaps)} gaps en {symbol} {timeframe}")
                gap_data = self._redownload_gaps_with_retry(symbol, timeframe, gaps, stats)
                if not gap_data.empty:
                    df_sorted = self.history_manager.merge_and_sort(df_sorted, gap_data)
            
            # 6. Validación final
            validation = self.history_manager.validate_schema_and_ranges(df_sorted, timeframe)
            if not validation['valid']:
                stats.errors.extend(validation['errors'])
                logger.warning(f"⚠️ Datos inválidos en {symbol} {timeframe}: {validation['errors']}")
            
            # 7. Escritura atómica
            if not df_sorted.empty:
                self.history_manager.write_csv_atomic(df_sorted, file_path)
                logger.info(f"✅ Archivo reparado: {file_path}")
            
            return df_sorted
            
        except Exception as e:
            logger.error(f"❌ Error reparando archivo {file_path}: {e}")
            stats.errors.append(str(e))
            return pd.DataFrame()
    
    def _load_and_normalize_csv(self, file_path: str, stats: RepairStats) -> pd.DataFrame:
        """Carga y normaliza un CSV"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"⚠️ Archivo no existe: {file_path}")
                return pd.DataFrame()
            
            # Cargar CSV
            df = pd.read_csv(file_path)
            
            if df.empty:
                return df
            
            # Normalizar tipos de datos
            if 'open_time' in df.columns:
                df['open_time'] = df['open_time'].astype('int64')
            if 'close_time' in df.columns:
                df['close_time'] = df['close_time'].astype('int64')
            
            # Eliminar filas con NaN críticos
            critical_columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']
            df_clean = df.dropna(subset=critical_columns)
            
            if len(df_clean) < len(df):
                removed_rows = len(df) - len(df_clean)
                logger.warning(f"⚠️ Eliminadas {removed_rows} filas con NaN críticos")
                stats.errors.append(f"Eliminadas {removed_rows} filas con NaN críticos")
            
            return df_clean
            
        except Exception as e:
            logger.error(f"❌ Error cargando CSV {file_path}: {e}")
            stats.errors.append(f"Error cargando CSV: {str(e)}")
            return pd.DataFrame()
    
    def _redownload_gaps_with_retry(self, symbol: str, timeframe: str, gaps: List[Tuple[int, int]], stats: RepairStats) -> pd.DataFrame:
        """Re-descarga gaps con reintentos y backoff"""
        all_patches = []
        
        for gap_start, gap_end in gaps:
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    # Calcular margen ±1 intervalo
                    tf_intervals = {
                        '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
                        '1h': 60 * 60 * 1000, '4h': 4 * 60 * 60 * 1000, '1d': 24 * 60 * 60 * 1000
                    }
                    interval_ms = tf_intervals.get(timeframe, 60 * 60 * 1000)
                    
                    since = gap_start - interval_ms
                    until = gap_end + interval_ms
                    
                    # Descargar datos
                    patch_df = self.history_manager.fetch_klines(symbol, timeframe, since, until)
                    
                    if not patch_df.empty:
                        all_patches.append(patch_df)
                        break
                    else:
                        retry_count += 1
                        stats.retries += 1
                        
                        if retry_count < max_retries:
                            backoff_time = min(2 ** retry_count, 64)  # Máximo 64 segundos
                            logger.warning(f"⚠️ Reintentando gap {gap_start}-{gap_end} en {backoff_time}s")
                            time.sleep(backoff_time)
                        else:
                            logger.error(f"❌ Falló descarga de gap {gap_start}-{gap_end} después de {max_retries} intentos")
                            stats.errors.append(f"Gap no reparado: {gap_start}-{gap_end}")
                
                except Exception as e:
                    retry_count += 1
                    stats.retries += 1
                    stats.api_errors += 1
                    
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        stats.rate_limit_hits += 1
                        backoff_time = min(2 ** retry_count, 64)
                        logger.warning(f"⚠️ Rate limit en {symbol} {timeframe}, esperando {backoff_time}s")
                        time.sleep(backoff_time)
                    elif "5" in str(e)[:3]:  # Error 5xx
                        backoff_time = min(2 ** retry_count, 64)
                        logger.warning(f"⚠️ Error 5xx en {symbol} {timeframe}, esperando {backoff_time}s")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"❌ Error descargando gap {gap_start}-{gap_end}: {e}")
                        stats.errors.append(f"Error descargando gap: {str(e)}")
                        break
        
        if all_patches:
            return pd.concat(all_patches, ignore_index=True)
        return pd.DataFrame()
    
    def _align_symbol_timeframes(self, symbol: str, timeframes: List[str]) -> Optional[AlignmentReport]:
        """Alinea timeframes de un símbolo y genera reporte"""
        try:
            alignment_data = {}
            total_expected_bars = 0
            total_actual_bars = 0
            total_gaps_fixed = 0
            total_residual_gaps = 0
            
            for timeframe in timeframes:
                file_path = self.historical_root / symbol / f"{timeframe}.csv"
                
                if not file_path.exists():
                    alignment_data[timeframe] = {
                        'expected_bars': 0,
                        'actual_bars': 0,
                        'gaps_fixed': 0,
                        'residual_gaps': 0,
                        'status': 'missing'
                    }
                    continue
                
                # Cargar datos
                df = pd.read_csv(file_path)
                if df.empty:
                    alignment_data[timeframe] = {
                        'expected_bars': 0,
                        'actual_bars': 0,
                        'gaps_fixed': 0,
                        'residual_gaps': 0,
                        'status': 'empty'
                    }
                    continue
                
                # Calcular barras esperadas (últimos 5 años)
                tf_intervals = {
                    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
                    '1h': 60 * 60 * 1000, '4h': 4 * 60 * 60 * 1000, '1d': 24 * 60 * 60 * 1000
                }
                interval_ms = tf_intervals.get(timeframe, 60 * 60 * 1000)
                
                end_time = int(time.time() * 1000)
                start_time = end_time - (5 * 365 * 24 * 60 * 60 * 1000)  # 5 años
                expected_bars = (end_time - start_time) // interval_ms
                
                # Calcular barras actuales
                actual_bars = len(df)
                
                # Detectar gaps residuales
                gaps = self.history_manager.detect_gaps(df, timeframe)
                residual_gaps = len(gaps)
                
                # Calcular gaps reparados (estimación)
                gaps_fixed = max(0, expected_bars - actual_bars - residual_gars)
                
                alignment_data[timeframe] = {
                    'expected_bars': expected_bars,
                    'actual_bars': actual_bars,
                    'gaps_fixed': gaps_fixed,
                    'residual_gaps': residual_gaps,
                    'status': 'ok' if residual_gaps == 0 else 'warning'
                }
                
                total_expected_bars += expected_bars
                total_actual_bars += actual_bars
                total_gaps_fixed += gaps_fixed
                total_residual_gaps += residual_gaps
            
            # Calcular score de alineación
            alignment_score = (total_actual_bars / total_expected_bars * 100) if total_expected_bars > 0 else 0
            
            return AlignmentReport(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                timeframes=alignment_data,
                total_expected_bars=total_expected_bars,
                total_actual_bars=total_actual_bars,
                total_gaps_fixed=total_gaps_fixed,
                total_residual_gaps=total_residual_gaps,
                alignment_score=round(alignment_score, 2),
                status='ok' if total_residual_gaps == 0 else 'warning'
            )
            
        except Exception as e:
            logger.error(f"❌ Error alineando {symbol}: {e}")
            return None
    
    def _write_alignment_report(self, report: AlignmentReport):
        """Escribe reporte de alineación"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"reports/alignment/{report.symbol}_alignment_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            
            logger.info(f"✅ Reporte de alineación guardado: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando reporte de alineación: {e}")
    
    def _update_telemetry(self, symbol: str, timeframe: str, stats: RepairStats):
        """Actualiza telemetría"""
        try:
            if symbol in self.telemetry['symbols']:
                symbol_data = self.telemetry['symbols'][symbol]
                symbol_data['timeframes'][timeframe] = asdict(stats)
                symbol_data['total_rows_before'] += stats.rows_before
                symbol_data['total_rows_after'] += stats.rows_after
                symbol_data['total_duplicates_removed'] += stats.dup_removed
                symbol_data['total_gaps_fixed'] += stats.gaps_fixed
                symbol_data['total_retries'] += stats.retries
                symbol_data['total_rate_limit_hits'] += stats.rate_limit_hits
                symbol_data['total_api_errors'] += stats.api_errors
                symbol_data['total_files_written'] += stats.files_written
        except Exception as e:
            logger.error(f"❌ Error actualizando telemetría: {e}")
    
    def _save_telemetry(self):
        """Guarda telemetría completa"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            telemetry_path = f"reports/repair_telemetry_{timestamp}.json"
            
            with open(telemetry_path, 'w') as f:
                json.dump(self.telemetry, f, indent=2, default=str)
            
            logger.info(f"✅ Telemetría guardada: {telemetry_path}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando telemetría: {e}")
    
    def _generate_repair_summary(self, repair_stats: List[RepairStats], alignment_reports: List[AlignmentReport]) -> Dict[str, Any]:
        """Genera resumen de reparación"""
        try:
            summary = {
                'total_files_processed': len(repair_stats),
                'total_symbols': len(set(stat.symbol for stat in repair_stats)),
                'total_rows_before': sum(stat.rows_before for stat in repair_stats),
                'total_rows_after': sum(stat.rows_after for stat in repair_stats),
                'total_duplicates_removed': sum(stat.dup_removed for stat in repair_stats),
                'total_gaps_fixed': sum(stat.gaps_fixed for stat in repair_stats),
                'total_retries': sum(stat.retries for stat in repair_stats),
                'total_rate_limit_hits': sum(stat.rate_limit_hits for stat in repair_stats),
                'total_api_errors': sum(stat.api_errors for stat in repair_stats),
                'files_by_status': {},
                'symbols': {},
                'alignment_reports': len(alignment_reports)
            }
            
            # Agrupar por estado
            for stat in repair_stats:
                status = stat.status
                if status not in summary['files_by_status']:
                    summary['files_by_status'][status] = 0
                summary['files_by_status'][status] += 1
            
            # Agrupar por símbolo
            for stat in repair_stats:
                symbol = stat.symbol
                if symbol not in summary['symbols']:
                    summary['symbols'][symbol] = []
                summary['symbols'][symbol].append(stat)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen: {e}")
            return {}
    
    def render_live_repair(self, status: RepairStatus) -> str:
        """Renderiza mensaje de reparación en vivo"""
        elapsed = datetime.now() - status.start_time
        elapsed_str = str(elapsed).split('.')[0]
        
        return f"""
🧹 <b>Reparación Histórico</b>
Progreso: {status.progress_percentage:.0f}%  |  Archivos: {status.completed_tasks}/{status.total_symbols * status.total_timeframes}
Último: {status.current_symbol} {status.current_timeframe} → dupes: {status.current_stats.dup_removed}→0 | gaps reparados: {status.current_stats.gaps_fixed} | filas:+{status.current_stats.new_rows:,}
Alineación: {status.alignment_status}
Tiempo: {elapsed_str}
        """.strip()
    
    def render_final_repair(self, summary: Dict[str, Any]) -> str:
        """Renderiza mensaje final de reparación"""
        return f"""
✅ <b>/repair_history completado</b>
{self._format_repair_summary(summary)}
Reports: reports/alignment/
        """.strip()
    
    def _format_repair_summary(self, summary: Dict[str, Any]) -> str:
        """Formatea resumen de reparación"""
        formatted = []
        for symbol, stats_list in summary.get('symbols', {}).items():
            symbol_lines = [f"{symbol}:"]
            for stat in stats_list:
                symbol_lines.append(f" - {stat.timeframe}: dupes:{stat.dup_removed} | gaps:{stat.gaps_fixed} | filas: {stat.rows_after:,}")
            formatted.append(" ".join(symbol_lines))
        return "\n".join(formatted)
