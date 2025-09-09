#!/usr/bin/env python3
"""
Gestor de Datos Históricos - Trading Bot v10 Enterprise
=======================================================

Maneja la descarga, auditoría y alineación de datos históricos.
Incluye funciones para detectar duplicados, gaps y reparar datos.

Características:
- Descarga automática por símbolo y timeframe
- Auditoría de duplicados y gaps
- Reparación automática de datos faltantes
- Alineación multi-timeframe
- Reportes detallados

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

logger = logging.getLogger(__name__)

@dataclass
class FileReport:
    """Reporte de un archivo de datos históricos"""
    symbol: str
    timeframe: str
    file_path: str
    min_open_time: int
    max_open_time: int
    num_rows: int
    gaps_count: int
    max_gap_size: int
    duplicates_count: int
    coverage_percentage: float
    integrity_score: float
    status: str

@dataclass
class DownloadStatus:
    """Estado de descarga en tiempo real"""
    total_symbols: int
    total_timeframes: int
    completed_tasks: int
    current_symbol: str
    current_timeframe: str
    current_action: str
    progress_percentage: float
    start_time: datetime
    elapsed_time: str
    rate_limit_ok: bool
    retries_count: int
    new_candles: int
    duplicates_removed: int
    gaps_repaired: int

class HistoryManager:
    """Gestor de datos históricos con descarga y auditoría"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el gestor de datos históricos"""
        self.config = self._load_config(config_path)
        self.exchange = None
        self.historical_root = Path(self.config.get('paths', {}).get('historical_root', 'data/historical'))
        self.download_window_years = self.config.get('download', {}).get('window', {}).get('default_years', 5)
        self.update_rate_sec = self.config.get('telegram', {}).get('update_rate_sec', 3)
        
        # Configurar directorios
        self._setup_directories()
        
        # Inicializar exchange
        self._initialize_exchange()
        
        logger.info("📊 Gestor de datos históricos inicializado")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde user_settings.yaml"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuración cargada desde {config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            return {}
    
    def _setup_directories(self):
        """Configura directorios necesarios"""
        directories = [
            self.historical_root,
            'logs',
            'reports'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _initialize_exchange(self):
        """Inicializa el exchange para descarga de datos"""
        try:
            exchange_name = self.config.get('history', {}).get('source', 'binance')
            
            if exchange_name == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': '',
                    'secret': '',
                    'sandbox': False,
                    'rateLimit': 1200,  # 1200ms entre requests
                })
            elif exchange_name == 'bitget':
                self.exchange = ccxt.bitget({
                    'apiKey': '',
                    'secret': '',
                    'sandbox': False,
                    'rateLimit': 1000,
                })
            else:
                self.exchange = ccxt.binance()  # Default
            
            logger.info(f"✅ Exchange {exchange_name} inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando exchange: {e}")
            self.exchange = ccxt.binance()
    
    def list_symbols_and_tfs(self) -> Tuple[List[str], List[str]]:
        """Obtiene símbolos y timeframes de la configuración"""
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        timeframes = self.config.get('timeframes', ['1m', '5m', '15m', '1h', '4h', '1d'])
        
        return symbols, timeframes
    
    def read_csv_or_empty(self, file_path: str) -> pd.DataFrame:
        """Lee un CSV o retorna DataFrame vacío si no existe"""
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if not df.empty:
                    # Convertir open_time a int si es necesario
                    if 'open_time' in df.columns:
                        df['open_time'] = df['open_time'].astype('int64')
                    return df
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo {file_path}: {e}")
            return pd.DataFrame()
    
    def fetch_klines(self, symbol: str, timeframe: str, since: int, until: int) -> pd.DataFrame:
        """Descarga datos de klines desde el exchange"""
        try:
            # Convertir timeframe a formato ccxt
            tf_mapping = {
                '1m': '1m', '5m': '5m', '15m': '15m',
                '1h': '1h', '4h': '4h', '1d': '1d'
            }
            tf_ccxt = tf_mapping.get(timeframe, '1h')
            
            # Descargar datos
            ohlcv = self.exchange.fetch_ohlcv(symbol, tf_ccxt, since=since, limit=1000)
            
            if not ohlcv:
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'trades', 'taker_buy_base', 'taker_buy_quote'
            ])
            
            # Agregar columnas adicionales
            df['vwap'] = (df['high'] + df['low'] + df['close']) / 3
            df['source'] = 'exchange'
            
            # Convertir tipos
            df['open_time'] = df['open_time'].astype('int64')
            df['close_time'] = df['close_time'].astype('int64')
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error descargando {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def dedupe_by_open_time(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Elimina duplicados por open_time, prefiriendo datos del exchange"""
        if df.empty:
            return df, 0
        
        original_count = len(df)
        
        # Ordenar por open_time y source (exchange primero)
        df_sorted = df.sort_values(['open_time', 'source'], ascending=[True, True])
        
        # Eliminar duplicados, manteniendo el primero (exchange)
        df_deduped = df_sorted.drop_duplicates(subset=['open_time'], keep='first')
        
        duplicates_removed = original_count - len(df_deduped)
        
        return df_deduped, duplicates_removed
    
    def detect_gaps(self, df: pd.DataFrame, timeframe: str) -> List[Tuple[int, int]]:
        """Detecta gaps en los datos por timeframe"""
        if df.empty or len(df) < 2:
            return []
        
        # Calcular intervalo en milisegundos
        tf_intervals = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        
        interval_ms = tf_intervals.get(timeframe, 60 * 60 * 1000)
        gaps = []
        
        df_sorted = df.sort_values('open_time')
        
        for i in range(len(df_sorted) - 1):
            current_time = df_sorted.iloc[i]['open_time']
            next_time = df_sorted.iloc[i + 1]['open_time']
            expected_next = current_time + interval_ms
            
            if next_time > expected_next:
                gap_start = expected_next
                gap_end = next_time - interval_ms
                gaps.append((gap_start, gap_end))
        
        return gaps
    
    def redownload_ranges(self, symbol: str, timeframe: str, gaps: List[Tuple[int, int]]) -> pd.DataFrame:
        """Re-descarga rangos específicos para llenar gaps"""
        if not gaps:
            return pd.DataFrame()
        
        all_patches = []
        
        for gap_start, gap_end in gaps:
            try:
                # Descargar con margen de ±1 intervalo
                tf_intervals = {
                    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
                    '1h': 60 * 60 * 1000, '4h': 4 * 60 * 60 * 1000, '1d': 24 * 60 * 60 * 1000
                }
                interval_ms = tf_intervals.get(timeframe, 60 * 60 * 1000)
                
                since = gap_start - interval_ms
                until = gap_end + interval_ms
                
                patch_df = self.fetch_klines(symbol, timeframe, since, until)
                if not patch_df.empty:
                    all_patches.append(patch_df)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ Error re-descargando gap {gap_start}-{gap_end}: {e}")
        
        if all_patches:
            return pd.concat(all_patches, ignore_index=True)
        return pd.DataFrame()
    
    def merge_and_sort(self, df_existing: pd.DataFrame, df_patch: pd.DataFrame) -> pd.DataFrame:
        """Combina datos existentes con parches y ordena"""
        if df_existing.empty:
            return df_patch
        if df_patch.empty:
            return df_existing
        
        # Combinar y eliminar duplicados
        combined = pd.concat([df_existing, df_patch], ignore_index=True)
        df_clean, _ = self.dedupe_by_open_time(combined)
        
        # Ordenar por open_time
        df_clean = df_clean.sort_values('open_time').reset_index(drop=True)
        
        return df_clean
    
    def validate_schema_and_ranges(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Valida el schema y rangos de los datos"""
        if df.empty:
            return {
                'valid': False,
                'errors': ['DataFrame vacío'],
                'integrity_score': 0.0
            }
        
        errors = []
        integrity_score = 100.0
        
        # Validar columnas requeridas
        required_columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Columnas faltantes: {missing_columns}")
            integrity_score -= 20.0
        
        # Validar tipos de datos
        if 'open_time' in df.columns:
            if not pd.api.types.is_integer_dtype(df['open_time']):
                errors.append("open_time debe ser entero")
                integrity_score -= 10.0
        
        # Validar OHLC
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_ohlc = (
                (df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])
            ).sum()
            
            if invalid_ohlc > 0:
                errors.append(f"{invalid_ohlc} filas con OHLC inválido")
                integrity_score -= invalid_ohlc * 0.1
        
        # Validar NaN
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            errors.append(f"{nan_count} valores NaN encontrados")
            integrity_score -= nan_count * 0.05
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'integrity_score': max(0.0, integrity_score)
        }
    
    def write_csv_atomic(self, df: pd.DataFrame, file_path: str):
        """Escribe CSV de forma atómica"""
        try:
            # Crear directorio si no existe
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Escribir a archivo temporal primero
            temp_path = f"{file_path}.tmp"
            df.to_csv(temp_path, index=False)
            
            # Mover a ubicación final (atómico)
            os.replace(temp_path, file_path)
            
            logger.info(f"✅ CSV guardado: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando CSV {file_path}: {e}")
    
    def scan_historical_files(self) -> List[Dict[str, str]]:
        """Escanea archivos históricos existentes"""
        files = []
        
        for symbol_dir in self.historical_root.iterdir():
            if symbol_dir.is_dir():
                symbol = symbol_dir.name
                for tf_file in symbol_dir.glob("*.csv"):
                    timeframe = tf_file.stem
                    files.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'file_path': str(tf_file)
                    })
        
        return files
    
    def inspect_file(self, symbol: str, timeframe: str, file_path: str) -> FileReport:
        """Inspecciona un archivo de datos históricos"""
        try:
            df = self.read_csv_or_empty(file_path)
            
            if df.empty:
                return FileReport(
                    symbol=symbol,
                    timeframe=timeframe,
                    file_path=file_path,
                    min_open_time=0,
                    max_open_time=0,
                    num_rows=0,
                    gaps_count=0,
                    max_gap_size=0,
                    duplicates_count=0,
                    coverage_percentage=0.0,
                    integrity_score=0.0,
                    status="empty"
                )
            
            # Calcular estadísticas básicas
            min_open_time = int(df['open_time'].min()) if 'open_time' in df.columns else 0
            max_open_time = int(df['open_time'].max()) if 'open_time' in df.columns else 0
            num_rows = len(df)
            
            # Detectar gaps
            gaps = self.detect_gaps(df, timeframe)
            gaps_count = len(gaps)
            max_gap_size = max([(end - start) for start, end in gaps]) if gaps else 0
            
            # Detectar duplicados
            _, duplicates_count = self.dedupe_by_open_time(df)
            
            # Calcular cobertura
            coverage_percentage = self.compute_coverage(df, timeframe)
            
            # Validar integridad
            validation = self.validate_schema_and_ranges(df, timeframe)
            integrity_score = validation['integrity_score']
            
            status = "ok" if integrity_score > 95 else "warning" if integrity_score > 80 else "error"
            
            return FileReport(
                symbol=symbol,
                timeframe=timeframe,
                file_path=file_path,
                min_open_time=min_open_time,
                max_open_time=max_open_time,
                num_rows=num_rows,
                gaps_count=gaps_count,
                max_gap_size=max_gap_size,
                duplicates_count=duplicates_count,
                coverage_percentage=coverage_percentage,
                integrity_score=integrity_score,
                status=status
            )
            
        except Exception as e:
            logger.error(f"❌ Error inspeccionando {file_path}: {e}")
            return FileReport(
                symbol=symbol,
                timeframe=timeframe,
                file_path=file_path,
                min_open_time=0,
                max_open_time=0,
                num_rows=0,
                gaps_count=0,
                max_gap_size=0,
                duplicates_count=0,
                coverage_percentage=0.0,
                integrity_score=0.0,
                status="error"
            )
    
    def compute_coverage(self, df: pd.DataFrame, timeframe: str) -> float:
        """Calcula el porcentaje de cobertura de datos"""
        if df.empty:
            return 0.0
        
        # Calcular intervalo en milisegundos
        tf_intervals = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        
        interval_ms = tf_intervals.get(timeframe, 60 * 60 * 1000)
        
        # Calcular rango esperado (últimos 5 años)
        end_time = int(time.time() * 1000)
        start_time = end_time - (self.download_window_years * 365 * 24 * 60 * 60 * 1000)
        
        expected_intervals = (end_time - start_time) // interval_ms
        actual_intervals = len(df)
        
        coverage = min(100.0, (actual_intervals / expected_intervals) * 100) if expected_intervals > 0 else 0.0
        
        return round(coverage, 1)
    
    def aggregate_reports(self, reports: List[FileReport]) -> Dict[str, Any]:
        """Agrega reportes individuales en un resumen"""
        if not reports:
            return {}
        
        summary = {
            'total_files': len(reports),
            'total_rows': sum(r.num_rows for r in reports),
            'total_gaps': sum(r.gaps_count for r in reports),
            'total_duplicates': sum(r.duplicates_count for r in reports),
            'avg_coverage': round(sum(r.coverage_percentage for r in reports) / len(reports), 1),
            'avg_integrity': round(sum(r.integrity_score for r in reports) / len(reports), 1),
            'files_by_status': {},
            'symbols': {}
        }
        
        # Agrupar por estado
        for report in reports:
            status = report.status
            if status not in summary['files_by_status']:
                summary['files_by_status'][status] = 0
            summary['files_by_status'][status] += 1
        
        # Agrupar por símbolo
        for report in reports:
            symbol = report.symbol
            if symbol not in summary['symbols']:
                summary['symbols'][symbol] = []
            summary['symbols'][symbol].append(report)
        
        return summary
    
    def write_inventory_report(self, summary: Dict[str, Any], reports: List[FileReport], output_path: str):
        """Escribe reporte de inventario"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'files': [asdict(report) for report in reports]
            }
            
            # Escribir JSON
            json_path = f"{output_path}.json"
            with open(json_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Escribir CSV
            csv_path = f"{output_path}.csv"
            df_reports = pd.DataFrame([asdict(report) for report in reports])
            df_reports.to_csv(csv_path, index=False)
            
            logger.info(f"✅ Reporte guardado: {json_path}, {csv_path}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando reporte: {e}")
    
    def render_live_download(self, status: DownloadStatus) -> str:
        """Renderiza mensaje de descarga en vivo"""
        elapsed = datetime.now() - status.start_time
        elapsed_str = str(elapsed).split('.')[0]
        
        return f"""
⬇️ <b>Descarga/Auditoría Histórico</b>
Símbolos: {', '.join(self.config.get('symbols', []))}
Progreso: {status.progress_percentage:.0f}%  |  Tareas: {status.completed_tasks}/{status.total_symbols * status.total_timeframes}
Último: {status.current_symbol} {status.current_timeframe} → +{status.new_candles}k velas, {status.duplicates_removed} duplicados, {status.gaps_repaired} gaps reparados
Tiempo: {elapsed_str}  |  Rate-limit: {'OK' if status.rate_limit_ok else 'WAIT'}  |  Retries: {status.retries_count}
Carpeta: {self.historical_root}
        """.strip()
    
    def render_final_download(self, results: Dict[str, Any]) -> str:
        """Renderiza mensaje final de descarga"""
        return f"""
✅ <b>Completado /download_history</b>
{self._format_symbol_results(results)}
Duración total: {results.get('total_duration', '00:00:00')}
Artefactos: CSV por TF en {self.historical_root}/&lt;SYMBOL&gt;/
        """.strip()
    
    def render_live_inspect(self, summary: Dict[str, Any], current_file: str = "") -> str:
        """Renderiza mensaje de inspección en vivo"""
        return f"""
🔍 <b>Inspección Histórico</b>
Progreso: {summary.get('progress_percentage', 0):.0f}%  |  Archivos: {summary.get('files_processed', 0)}/{summary.get('total_files', 0)}
Último: {current_file}
        """.strip()
    
    def render_final_inspect(self, summary: Dict[str, Any], report_path: str) -> str:
        """Renderiza mensaje final de inspección"""
        return f"""
📄 <b>Estado Histórico (resumen)</b>
{self._format_inspect_summary(summary)}
Reporte: {report_path}
        """.strip()
    
    def _format_symbol_results(self, results: Dict[str, Any]) -> str:
        """Formatea resultados por símbolo"""
        formatted = []
        for symbol, data in results.get('symbols', {}).items():
            symbol_lines = [f"{symbol}:"]
            for tf, stats in data.items():
                symbol_lines.append(f" - {tf}: {stats}")
            formatted.append(" ".join(symbol_lines))
        return "\n".join(formatted)
    
    def _format_inspect_summary(self, summary: Dict[str, Any]) -> str:
        """Formatea resumen de inspección"""
        formatted = []
        for symbol, reports in summary.get('symbols', {}).items():
            symbol_lines = [f"{symbol}:"]
            for report in reports:
                min_date = datetime.fromtimestamp(report.min_open_time / 1000).strftime('%Y-%m-%d') if report.min_open_time > 0 else 'N/A'
                max_date = datetime.fromtimestamp(report.max_open_time / 1000).strftime('%Y-%m-%d') if report.max_open_time > 0 else 'N/A'
                symbol_lines.append(f" - {report.timeframe}: {min_date} → {max_date} | filas: {report.num_rows:,} | gaps: {report.gaps_count} | dupes: {report.duplicates_count} | cobertura: {report.coverage_percentage}%")
            formatted.append(" ".join(symbol_lines))
        return "\n".join(formatted)
