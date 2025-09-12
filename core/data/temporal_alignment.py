# Ruta: core/data/temporal_alignment.py
"""
data/temporal_alignment.py - Sistema de Alineación Temporal para Trading Multi-Símbolo
Sistema robusto para garantizar timestamps idénticos entre todos los símbolos y timeframes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from .symbol_database_manager import symbol_db_manager
from .historical_data_adapter import get_historical_data

logger = logging.getLogger(__name__)

class TimeframeType(Enum):
    """Tipos de timeframes soportados"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"

@dataclass
class AlignmentConfig:
    """Configuración para alineación temporal"""
    base_timeframe: str = "5m"
    timeframes: List[str] = None
    required_symbols: List[str] = None
    alignment_tolerance: timedelta = None
    min_data_coverage: float = 0.95
    max_gap_minutes: int = 60
    
    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        if self.required_symbols is None:
            # Usar configuración centralizada
            from config.unified_config import get_config_manager
            config_manager = get_config_manager()
            self.required_symbols = config_manager.get_symbols() or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
        if self.alignment_tolerance is None:
            self.alignment_tolerance = timedelta(minutes=1)

@dataclass
class AlignmentResult:
    """Resultado de una operación de alineación"""
    success: bool
    aligned_data: Dict[str, pd.DataFrame]
    master_timeline: pd.DatetimeIndex
    alignment_quality: float
    coherence_scores: Dict[str, float]
    gaps_detected: Dict[str, List[Tuple[datetime, datetime]]]
    session_id: str
    processing_time: float
    metadata: Dict[str, Any]

class TemporalAlignment:
    """Sistema de alineación temporal para trading multi-símbolo"""
    
    def __init__(self, config: Optional[AlignmentConfig] = None):
        self.config = config or AlignmentConfig()
        self.logger = logging.getLogger(__name__)
        
        # Mapeo de timeframes a minutos
        self.timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        # Reglas de agregación
        self.aggregation_rules = {
            '5m': {'from': '1m', 'periods': 5},
            '15m': {'from': '5m', 'periods': 3},
            '1h': {'from': '15m', 'periods': 4},
            '4h': {'from': '1h', 'periods': 4},
            '1d': {'from': '4h', 'periods': 6}
        }
        
        self.logger.info(f"TemporalAlignment initialized with {len(self.config.timeframes)} timeframes")
    
    def create_master_timeline(
        self, 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime,
        exclude_weekends: bool = True
    ) -> pd.DatetimeIndex:
        """
        Crea una línea de tiempo maestra para un timeframe específico
        
        Args:
            timeframe: Timeframe objetivo ('5m', '15m', '1h', '4h', '1d')
            start_date: Fecha de inicio
            end_date: Fecha de fin
            exclude_weekends: Si excluir fines de semana (solo para timeframes >= 1d)
        
        Returns:
            pd.DatetimeIndex: Línea de tiempo maestra
        """
        try:
            minutes = self.timeframe_minutes[timeframe]
            
            # Crear rango de fechas
            if timeframe in ['1d'] and exclude_weekends:
                # Para timeframes diarios, excluir fines de semana
                date_range = pd.bdate_range(start=start_date, end=end_date, freq=f'{minutes}min')
            else:
                # Para timeframes menores, incluir todos los días
                date_range = pd.date_range(start=start_date, end=end_date, freq=f'{minutes}min')
            
            # Filtrar horarios de trading (24/7 para crypto)
            # Mantener todos los horarios para criptomonedas
            
            self.logger.info(f"Created master timeline for {timeframe}: {len(date_range)} periods")
            return date_range
            
        except Exception as e:
            self.logger.error(f"Error creating master timeline: {e}")
            raise
    
    def align_symbol_data(
        self, 
        symbol_data: Dict[str, pd.DataFrame],
        master_timeline: pd.DatetimeIndex,
        timeframe: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Alinea datos de múltiples símbolos a una línea de tiempo maestra
        
        Args:
            symbol_data: Diccionario con datos de cada símbolo
            master_timeline: Línea de tiempo maestra
            timeframe: Timeframe de los datos
        
        Returns:
            Dict[str, pd.DataFrame]: Datos alineados por símbolo
        """
        try:
            aligned_data = {}
            
            for symbol, df in symbol_data.items():
                if df.empty:
                    self.logger.warning(f"No data for symbol {symbol}")
                    continue
                
                # Asegurar que timestamp sea el índice
                if 'timestamp' in df.columns:
                    df = df.set_index('timestamp')
                
                # Convertir índice a datetime si es necesario
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, unit='s')
                
                # Reindexar a la línea de tiempo maestra
                df_aligned = df.reindex(master_timeline, method='ffill')
                
                # Eliminar filas con valores NaN (especialmente al principio)
                df_aligned = df_aligned.dropna()
                
                # Validar que tenemos datos suficientes
                data_coverage = df_aligned.notna().sum().sum() / (len(df_aligned) * len(df_aligned.columns))
                if data_coverage < self.config.min_data_coverage:
                    self.logger.warning(f"Low data coverage for {symbol}: {data_coverage:.2%}")
                
                # Detectar gaps significativos
                gaps = self._detect_gaps(df_aligned, timeframe)
                if gaps:
                    self.logger.warning(f"Gaps detected in {symbol}: {len(gaps)} gaps")
                
                aligned_data[symbol] = df_aligned
                self.logger.debug(f"Aligned {symbol}: {len(df_aligned)} periods")
            
            return aligned_data
            
        except Exception as e:
            self.logger.error(f"Error aligning symbol data: {e}")
            raise
    
    def validate_alignment(
        self, 
        aligned_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Valida la calidad de la alineación temporal
        
        Args:
            aligned_data: Datos alineados por símbolo
        
        Returns:
            Dict[str, Any]: Resultados de validación
        """
        try:
            validation_results = {
                'overall_quality': 0.0,
                'symbol_quality': {},
                'timeline_consistency': True,
                'gaps_summary': {},
                'coverage_stats': {},
                'issues': []
            }
            
            if not aligned_data:
                validation_results['issues'].append("No aligned data provided")
                return validation_results
            
            # Obtener timeline de referencia
            reference_timeline = None
            for symbol, df in aligned_data.items():
                if reference_timeline is None:
                    reference_timeline = df.index
                else:
                    # Verificar consistencia de timeline
                    if not df.index.equals(reference_timeline):
                        validation_results['timeline_consistency'] = False
                        validation_results['issues'].append(f"Timeline mismatch in {symbol}")
            
            # Calcular calidad por símbolo
            total_quality = 0
            for symbol, df in aligned_data.items():
                symbol_quality = self._calculate_symbol_quality(df)
                validation_results['symbol_quality'][symbol] = symbol_quality
                total_quality += symbol_quality
                
                # Detectar gaps
                gaps = self._detect_gaps(df, 'unknown')
                validation_results['gaps_summary'][symbol] = len(gaps)
                
                # Estadísticas de cobertura
                coverage = df.notna().sum() / len(df)
                validation_results['coverage_stats'][symbol] = {
                    'coverage': float(coverage),
                    'total_periods': len(df),
                    'valid_periods': int(df.notna().sum())
                }
            
            # Calcular calidad general
            validation_results['overall_quality'] = total_quality / len(aligned_data)
            
            self.logger.info(f"Alignment validation completed. Overall quality: {validation_results['overall_quality']:.3f}")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating alignment: {e}")
            raise
    
    def aggregate_to_higher_timeframe(
        self, 
        base_data: pd.DataFrame, 
        target_tf: str
    ) -> pd.DataFrame:
        """
        Agrega datos de un timeframe base a un timeframe superior
        
        Args:
            base_data: Datos del timeframe base
            target_tf: Timeframe objetivo
        
        Returns:
            pd.DataFrame: Datos agregados
        """
        try:
            if target_tf not in self.aggregation_rules:
                raise ValueError(f"Unsupported target timeframe: {target_tf}")
            
            rule = self.aggregation_rules[target_tf]
            periods = rule['periods']
            
            # Agregar datos OHLCV
            agg_data = base_data.resample(f'{self.timeframe_minutes[target_tf]}min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Validar agregación
            self._validate_aggregation(base_data, agg_data, target_tf)
            
            self.logger.info(f"Aggregated data to {target_tf}: {len(agg_data)} periods")
            return agg_data
            
        except Exception as e:
            self.logger.error(f"Error aggregating to {target_tf}: {e}")
            raise
    
    def process_multi_symbol_alignment(
        self,
        raw_data: Dict[str, Dict[str, pd.DataFrame]],
        start_date: datetime,
        end_date: datetime
    ) -> AlignmentResult:
        """
        Procesa alineación completa para múltiples símbolos y timeframes
        
        Args:
            raw_data: Datos brutos organizados por timeframe y símbolo
            start_date: Fecha de inicio
            end_date: Fecha de fin
        
        Returns:
            AlignmentResult: Resultado completo de la alineación
        """
        start_time = datetime.now()
        session_id = self._generate_session_id()
        
        try:
            self.logger.info(f"Starting multi-symbol alignment session {session_id}")
            
            # Procesar cada timeframe
            aligned_results = {}
            master_timelines = {}
            
            for timeframe in self.config.timeframes:
                self.logger.info(f"Processing timeframe {timeframe}")
                
                # Crear timeline maestra para este timeframe
                master_timeline = self.create_master_timeline(timeframe, start_date, end_date)
                master_timelines[timeframe] = master_timeline
                
                # Alinear datos de símbolos
                symbol_data = raw_data.get(timeframe, {})
                aligned_data = self.align_symbol_data(symbol_data, master_timeline, timeframe)
                
                # Validar alineación
                validation = self.validate_alignment(aligned_data)
                
                aligned_results[timeframe] = {
                    'data': aligned_data,
                    'validation': validation,
                    'master_timeline': master_timeline
                }
            
            # Calcular métricas de coherencia entre timeframes
            coherence_scores = self._calculate_timeframe_coherence(aligned_results)
            
            # Calcular calidad general
            overall_quality = np.mean([
                result['validation']['overall_quality'] 
                for result in aligned_results.values()
            ])
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = AlignmentResult(
                success=True,
                aligned_data=aligned_results,
                master_timeline=master_timelines[self.config.base_timeframe],
                alignment_quality=overall_quality,
                coherence_scores=coherence_scores,
                gaps_detected={},  # TODO: Implementar detección de gaps
                session_id=session_id,
                processing_time=processing_time,
                metadata={
                    'timeframes_processed': self.config.timeframes,
                    'symbols_processed': self.config.required_symbols,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            )
            
            self.logger.info(f"Multi-symbol alignment completed in {processing_time:.2f}s. Quality: {overall_quality:.3f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in multi-symbol alignment: {e}")
            return AlignmentResult(
                success=False,
                aligned_data={},
                master_timeline=pd.DatetimeIndex([]),
                alignment_quality=0.0,
                coherence_scores={},
                gaps_detected={},
                session_id=session_id,
                processing_time=(datetime.now() - start_time).total_seconds(),
                metadata={'error': str(e)}
            )
    
    def _detect_gaps(self, df: pd.DataFrame, timeframe: str) -> List[Tuple[datetime, datetime]]:
        """Detecta gaps significativos en los datos"""
        gaps = []
        
        if df.empty:
            return gaps
        
        # Calcular diferencias entre timestamps consecutivos
        time_diffs = df.index.to_series().diff()
        
        # Definir gap máximo permitido por timeframe
        max_gap = timedelta(minutes=self.timeframe_minutes.get(timeframe, 60) * 2)
        
        # Encontrar gaps
        gap_mask = time_diffs > max_gap
        gap_starts = df.index[gap_mask]
        gap_ends = df.index[gap_mask.shift(-1).fillna(False)]
        
        for start, end in zip(gap_starts, gap_ends):
            gaps.append((start, end))
        
        return gaps
    
    def _calculate_symbol_quality(self, df: pd.DataFrame) -> float:
        """Calcula la calidad de datos de un símbolo"""
        if df.empty:
            return 0.0
        
        # Factores de calidad
        coverage = df.notna().sum() / len(df)
        completeness = df.isna().sum().sum() == 0
        consistency = self._check_ohlc_consistency(df)
        
        # Peso de cada factor
        quality = (
            coverage * 0.4 +
            (1.0 if completeness else 0.0) * 0.3 +
            consistency * 0.3
        )
        
        return float(quality)
    
    def _check_ohlc_consistency(self, df: pd.DataFrame) -> float:
        """Verifica consistencia de datos OHLC"""
        if df.empty or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            return 0.0
        
        # Verificar que high >= max(open, close) y low <= min(open, close)
        valid_ohlc = (
            (df['high'] >= df[['open', 'close']].max(axis=1)) &
            (df['low'] <= df[['open', 'close']].min(axis=1)) &
            (df['high'] >= df['low'])
        ).sum()
        
        return float(valid_ohlc / len(df)) if len(df) > 0 else 0.0
    
    def _validate_aggregation(self, base_data: pd.DataFrame, agg_data: pd.DataFrame, target_tf: str):
        """Valida que la agregación sea correcta"""
        # Verificar que no hay pérdida de datos críticos
        if len(agg_data) == 0:
            raise ValueError(f"Aggregation resulted in empty data for {target_tf}")
        
        # Verificar consistencia de precios
        if not all(agg_data['high'] >= agg_data[['open', 'close']].max(axis=1)):
            raise ValueError(f"Invalid OHLC data after aggregation to {target_tf}")
    
    def _calculate_timeframe_coherence(self, aligned_results: Dict[str, Any]) -> Dict[str, float]:
        """Calcula coherencia entre diferentes timeframes"""
        coherence_scores = {}
        
        # Comparar timeframes relacionados (ej: 5m vs 15m agregado)
        for tf, result in aligned_results.items():
            if tf in self.aggregation_rules:
                base_tf = self.aggregation_rules[tf]['from']
                if base_tf in aligned_results:
                    # TODO: Implementar comparación de coherencia
                    coherence_scores[f"{base_tf}_to_{tf}"] = 1.0
        
        return coherence_scores
    
    def _generate_session_id(self) -> str:
        """Genera un ID único para la sesión de alineación"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"align_{timestamp}_{random_part}"

# Funciones de conveniencia
def create_alignment_config(
    timeframes: List[str] = None,
    symbols: List[str] = None,
    base_timeframe: str = "5m"
) -> AlignmentConfig:
    """Crea configuración de alineación con valores por defecto"""
    return AlignmentConfig(
        timeframes=timeframes or ['5m', '15m', '1h', '4h', '1d'],
        required_symbols=symbols or (get_config_manager().get_symbols() if 'get_config_manager' in globals() else ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']),
        base_timeframe=base_timeframe
    )

def quick_align_data(
    symbol_data: Dict[str, pd.DataFrame],
    timeframe: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, pd.DataFrame]:
    """Función de conveniencia para alineación rápida"""
    aligner = TemporalAlignment()
    master_timeline = aligner.create_master_timeline(timeframe, start_date, end_date)
    return aligner.align_symbol_data(symbol_data, master_timeline, timeframe)
