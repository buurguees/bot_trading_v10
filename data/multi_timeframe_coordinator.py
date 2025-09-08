"""
data/multi_timeframe_coordinator.py - Coordinador Multi-Timeframe
Sistema para mantener coherencia entre todos los timeframes y coordinar operaciones
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path

from .temporal_alignment import TemporalAlignment, AlignmentConfig, AlignmentResult
from .hybrid_storage import HybridStorageManager, StorageConfig

logger = logging.getLogger(__name__)

class TimeframePriority(Enum):
    """Prioridades de timeframes para procesamiento"""
    CRITICAL = 1  # 5m, 15m - Datos críticos para trading
    HIGH = 2      # 1h - Datos importantes para análisis
    MEDIUM = 3    # 4h - Datos de tendencia
    LOW = 4       # 1d - Datos de largo plazo

@dataclass
class TimeframeConfig:
    """Configuración específica por timeframe"""
    name: str
    minutes: int
    priority: TimeframePriority
    chunk_days: int  # Días por chunk para descarga
    cache_hours: int  # Horas de cache
    validation_tolerance: float  # Tolerancia para validación
    aggregation_source: Optional[str] = None  # Timeframe fuente para agregación

@dataclass
class CoordinationResult:
    """Resultado de coordinación multi-timeframe"""
    success: bool
    processed_timeframes: List[str]
    alignment_results: Dict[str, AlignmentResult]
    coherence_scores: Dict[str, float]
    processing_time: float
    errors: List[str]
    metadata: Dict[str, Any]

class MultiTimeframeCoordinator:
    """Coordinador para mantener coherencia entre todos los timeframes"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configurar timeframes
        self.timeframe_configs = self._create_timeframe_configs()
        self.timeframes = list(self.timeframe_configs.keys())
        self.base_timeframe = '5m'
        
        # Configurar reglas de agregación
        self.aggregation_rules = {
            '15m': {'from': '5m', 'periods': 3, 'method': 'ohlc'},
            '1h': {'from': '15m', 'periods': 4, 'method': 'ohlc'},
            '4h': {'from': '1h', 'periods': 4, 'method': 'ohlc'},
            '1d': {'from': '4h', 'periods': 6, 'method': 'ohlc'}
        }
        
        # Inicializar componentes
        self.alignment_system = TemporalAlignment()
        self.storage_manager = HybridStorageManager()
        
        # Lock para operaciones concurrentes
        self._lock = threading.RLock()
        
        # Configurar procesamiento paralelo
        self.max_workers = self.config.get('max_workers', 4)
        
        self.logger.info(f"MultiTimeframeCoordinator initialized with {len(self.timeframes)} timeframes")
    
    def _create_timeframe_configs(self) -> Dict[str, TimeframeConfig]:
        """Crea configuraciones específicas para cada timeframe"""
        return {
            '5m': TimeframeConfig(
                name='5m', minutes=5, priority=TimeframePriority.CRITICAL,
                chunk_days=2, cache_hours=2, validation_tolerance=0.001
            ),
            '15m': TimeframeConfig(
                name='15m', minutes=15, priority=TimeframePriority.CRITICAL,
                chunk_days=7, cache_hours=6, validation_tolerance=0.002,
                aggregation_source='5m'
            ),
            '1h': TimeframeConfig(
                name='1h', minutes=60, priority=TimeframePriority.HIGH,
                chunk_days=30, cache_hours=12, validation_tolerance=0.005,
                aggregation_source='15m'
            ),
            '4h': TimeframeConfig(
                name='4h', minutes=240, priority=TimeframePriority.MEDIUM,
                chunk_days=60, cache_hours=24, validation_tolerance=0.01,
                aggregation_source='1h'
            ),
            '1d': TimeframeConfig(
                name='1d', minutes=1440, priority=TimeframePriority.LOW,
                chunk_days=180, cache_hours=72, validation_tolerance=0.02,
                aggregation_source='4h'
            )
        }
    
    async def process_all_timeframes_coordinated(
        self, 
        symbols: List[str], 
        days_back: int = 365,
        use_aggregation: bool = True
    ) -> CoordinationResult:
        """
        Procesa todos los timeframes de forma coordinada
        
        Args:
            symbols: Lista de símbolos a procesar
            days_back: Días hacia atrás para procesar
            use_aggregation: Si usar agregación automática
        
        Returns:
            CoordinationResult: Resultado de la coordinación
        """
        start_time = datetime.now()
        session_id = f"coord_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            self.logger.info(f"Starting coordinated processing for {symbols} ({days_back} days)")
            
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Procesar timeframes en orden de prioridad
            processed_timeframes = []
            alignment_results = {}
            errors = []
            
            # Primero procesar timeframes base (5m)
            base_tf = self.base_timeframe
            if base_tf in self.timeframes:
                try:
                    result = await self._process_single_timeframe(
                        symbols, base_tf, start_date, end_date, session_id
                    )
                    alignment_results[base_tf] = result
                    processed_timeframes.append(base_tf)
                except Exception as e:
                    error_msg = f"Error processing {base_tf}: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Luego procesar timeframes agregados si está habilitado
            if use_aggregation and base_tf in alignment_results:
                for tf in self.timeframes:
                    if tf == base_tf:
                        continue
                    
                    if self.timeframe_configs[tf].aggregation_source:
                        try:
                            result = await self._process_aggregated_timeframe(
                                tf, alignment_results, session_id
                            )
                            alignment_results[tf] = result
                            processed_timeframes.append(tf)
                        except Exception as e:
                            error_msg = f"Error processing aggregated {tf}: {e}"
                            self.logger.error(error_msg)
                            errors.append(error_msg)
            
            # Calcular coherencia entre timeframes
            coherence_scores = self._calculate_timeframe_coherence(alignment_results)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = CoordinationResult(
                success=len(errors) == 0,
                processed_timeframes=processed_timeframes,
                alignment_results=alignment_results,
                coherence_scores=coherence_scores,
                processing_time=processing_time,
                errors=errors,
                metadata={
                    'symbols': symbols,
                    'days_back': days_back,
                    'session_id': session_id,
                    'use_aggregation': use_aggregation
                }
            )
            
            self.logger.info(f"Coordinated processing completed in {processing_time:.2f}s. "
                           f"Processed: {processed_timeframes}, Errors: {len(errors)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in coordinated processing: {e}")
            return CoordinationResult(
                success=False,
                processed_timeframes=[],
                alignment_results={},
                coherence_scores={},
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
                metadata={'error': str(e)}
            )
    
    async def _process_single_timeframe(
        self, 
        symbols: List[str], 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime,
        session_id: str
    ) -> AlignmentResult:
        """Procesa un timeframe individual"""
        try:
            self.logger.info(f"Processing timeframe {timeframe} for {symbols}")
            
            # Cargar datos existentes del storage
            existing_data = self.storage_manager.load_aligned_data(
                symbols, timeframe, start_date, end_date
            )
            
            # Si no hay datos suficientes, simular descarga (en implementación real, descargar de API)
            if not existing_data or all(df.empty for df in existing_data.values()):
                self.logger.warning(f"No existing data for {timeframe}, simulating download")
                existing_data = self._simulate_data_download(symbols, timeframe, start_date, end_date)
            
            # Alinear datos
            alignment_result = self.alignment_system.process_multi_symbol_alignment(
                {timeframe: existing_data}, start_date, end_date
            )
            
            # Almacenar datos alineados
            if alignment_result.success and alignment_result.aligned_data:
                tf_data = alignment_result.aligned_data.get(timeframe, {})
                if tf_data:
                    self.storage_manager.store_aligned_data(
                        tf_data, timeframe, session_id, 
                        metadata={'source': 'coordinated_processing'}
                    )
            
            return alignment_result
            
        except Exception as e:
            self.logger.error(f"Error processing {timeframe}: {e}")
            raise
    
    async def _process_aggregated_timeframe(
        self, 
        target_tf: str, 
        alignment_results: Dict[str, AlignmentResult],
        session_id: str
    ) -> AlignmentResult:
        """Procesa un timeframe agregado desde un timeframe base"""
        try:
            config = self.timeframe_configs[target_tf]
            source_tf = config.aggregation_source
            
            if source_tf not in alignment_results:
                raise ValueError(f"Source timeframe {source_tf} not available for aggregation")
            
            source_result = alignment_results[source_tf]
            if not source_result.success:
                raise ValueError(f"Source timeframe {source_tf} processing failed")
            
            self.logger.info(f"Aggregating {source_tf} to {target_tf}")
            
            # Obtener datos fuente
            source_data = source_result.aligned_data.get(source_tf, {})
            if not source_data:
                raise ValueError(f"No source data available for {source_tf}")
            
            # Agregar datos
            aggregated_data = {}
            for symbol, df in source_data.items():
                if df.empty:
                    continue
                
                aggregated_df = self.alignment_system.aggregate_to_higher_timeframe(df, target_tf)
                aggregated_data[symbol] = aggregated_df
            
            # Validar agregación
            validation = self._validate_aggregation_quality(source_data, aggregated_data, target_tf)
            
            # Crear resultado de alineación
            alignment_result = AlignmentResult(
                success=True,
                aligned_data={target_tf: aggregated_data},
                master_timeline=aggregated_data[list(aggregated_data.keys())[0]].index if aggregated_data else pd.DatetimeIndex([]),
                alignment_quality=validation['quality_score'],
                coherence_scores={f"{source_tf}_to_{target_tf}": validation['coherence_score']},
                gaps_detected={},
                session_id=session_id,
                processing_time=0.0,
                metadata={
                    'source_timeframe': source_tf,
                    'aggregation_method': 'ohlc',
                    'validation': validation
                }
            )
            
            # Almacenar datos agregados
            self.storage_manager.store_aligned_data(
                aggregated_data, target_tf, session_id,
                metadata={'source': 'aggregation', 'source_tf': source_tf}
            )
            
            return alignment_result
            
        except Exception as e:
            self.logger.error(f"Error aggregating to {target_tf}: {e}")
            raise
    
    def validate_timeframe_coherence(
        self, 
        all_timeframe_data: Dict[str, Dict[str, pd.DataFrame]]
    ) -> Dict[str, Any]:
        """
        Valida coherencia entre diferentes timeframes
        
        Args:
            all_timeframe_data: Datos organizados por timeframe y símbolo
        
        Returns:
            Dict[str, Any]: Resultados de validación de coherencia
        """
        try:
            self.logger.info("Validating timeframe coherence")
            
            coherence_results = {
                'overall_coherence': 0.0,
                'timeframe_pairs': {},
                'symbol_coherence': {},
                'issues': []
            }
            
            # Validar pares de timeframes relacionados
            for target_tf, config in self.timeframe_configs.items():
                if not config.aggregation_source:
                    continue
                
                source_tf = config.aggregation_source
                
                if source_tf not in all_timeframe_data or target_tf not in all_timeframe_data:
                    continue
                
                source_data = all_timeframe_data[source_tf]
                target_data = all_timeframe_data[target_tf]
                
                # Validar coherencia para cada símbolo
                symbol_coherences = []
                for symbol in source_data.keys():
                    if symbol not in target_data:
                        continue
                    
                    coherence = self._validate_symbol_coherence(
                        source_data[symbol], target_data[symbol], source_tf, target_tf
                    )
                    symbol_coherences.append(coherence)
                
                if symbol_coherences:
                    pair_coherence = np.mean(symbol_coherences)
                    coherence_results['timeframe_pairs'][f"{source_tf}_to_{target_tf}"] = pair_coherence
                    
                    if pair_coherence < config.validation_tolerance:
                        issue = f"Low coherence between {source_tf} and {target_tf}: {pair_coherence:.4f}"
                        coherence_results['issues'].append(issue)
            
            # Calcular coherencia general
            if coherence_results['timeframe_pairs']:
                coherence_results['overall_coherence'] = np.mean(list(coherence_results['timeframe_pairs'].values()))
            
            self.logger.info(f"Coherence validation completed. Overall: {coherence_results['overall_coherence']:.4f}")
            return coherence_results
            
        except Exception as e:
            self.logger.error(f"Error validating timeframe coherence: {e}")
            return {'overall_coherence': 0.0, 'timeframe_pairs': {}, 'symbol_coherence': {}, 'issues': [str(e)]}
    
    def auto_aggregate_timeframes(
        self, 
        base_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Agrega automáticamente timeframes desde datos base
        
        Args:
            base_data: Datos del timeframe base
        
        Returns:
            Dict[str, Dict[str, pd.DataFrame]]: Datos agregados por timeframe
        """
        try:
            self.logger.info(f"Auto-aggregating timeframes from base data")
            
            aggregated_data = {}
            current_data = base_data.copy()
            
            # Agregar en orden de dependencia
            for target_tf in ['15m', '1h', '4h', '1d']:
                if target_tf not in self.timeframe_configs:
                    continue
                
                config = self.timeframe_configs[target_tf]
                if not config.aggregation_source:
                    continue
                
                self.logger.info(f"Aggregating to {target_tf}")
                
                tf_data = {}
                for symbol, df in current_data.items():
                    if df.empty:
                        continue
                    
                    aggregated_df = self.alignment_system.aggregate_to_higher_timeframe(df, target_tf)
                    tf_data[symbol] = aggregated_df
                
                aggregated_data[target_tf] = tf_data
                
                # Para la siguiente iteración, usar datos agregados si están disponibles
                if target_tf in ['15m', '1h']:  # Solo para timeframes intermedios
                    current_data = tf_data
            
            self.logger.info(f"Auto-aggregation completed for {len(aggregated_data)} timeframes")
            return aggregated_data
            
        except Exception as e:
            self.logger.error(f"Error in auto-aggregation: {e}")
            return {}
    
    def _simulate_data_download(
        self, 
        symbols: List[str], 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Simula descarga de datos (para testing)"""
        try:
            # Crear timeline para el timeframe
            minutes = self.timeframe_configs[timeframe].minutes
            timeline = pd.date_range(start=start_date, end=end_date, freq=f'{minutes}min')
            
            simulated_data = {}
            for symbol in symbols:
                # Generar datos simulados con OHLCV
                np.random.seed(hash(symbol) % 2**32)  # Seed consistente por símbolo
                
                n_periods = len(timeline)
                base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.0
                
                # Generar precios con tendencia y volatilidad
                returns = np.random.normal(0, 0.02, n_periods)  # 2% volatilidad diaria
                prices = base_price * np.exp(np.cumsum(returns))
                
                # Crear OHLCV
                data = []
                for i, (timestamp, price) in enumerate(zip(timeline, prices)):
                    volatility = 0.01 * (1 + np.random.random())
                    
                    open_price = price * (1 + np.random.normal(0, volatility/2))
                    close_price = price * (1 + np.random.normal(0, volatility/2))
                    high_price = max(open_price, close_price) * (1 + np.random.random() * volatility)
                    low_price = min(open_price, close_price) * (1 - np.random.random() * volatility)
                    volume = np.random.exponential(1000) * (1 + np.random.random())
                    
                    data.append({
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                simulated_data[symbol] = df
            
            self.logger.info(f"Simulated data for {len(symbols)} symbols, {timeframe}, {len(timeline)} periods")
            return simulated_data
            
        except Exception as e:
            self.logger.error(f"Error simulating data download: {e}")
            return {}
    
    def _validate_aggregation_quality(
        self, 
        source_data: Dict[str, pd.DataFrame], 
        aggregated_data: Dict[str, pd.DataFrame], 
        target_tf: str
    ) -> Dict[str, float]:
        """Valida la calidad de la agregación"""
        try:
            quality_scores = []
            
            for symbol in source_data.keys():
                if symbol not in aggregated_data:
                    continue
                
                source_df = source_data[symbol]
                agg_df = aggregated_data[symbol]
                
                if source_df.empty or agg_df.empty:
                    continue
                
                # Validar que no hay pérdida de datos críticos
                source_span = (source_df.index[-1] - source_df.index[0]).total_seconds()
                agg_span = (agg_df.index[-1] - agg_df.index[0]).total_seconds()
                span_ratio = agg_span / source_span if source_span > 0 else 0
                
                # Validar consistencia de precios
                price_consistency = self._check_price_consistency(source_df, agg_df)
                
                # Calcular score de calidad
                quality = (span_ratio * 0.3 + price_consistency * 0.7)
                quality_scores.append(quality)
            
            return {
                'quality_score': np.mean(quality_scores) if quality_scores else 0.0,
                'coherence_score': np.mean(quality_scores) if quality_scores else 0.0,
                'samples': len(quality_scores)
            }
            
        except Exception as e:
            self.logger.error(f"Error validating aggregation quality: {e}")
            return {'quality_score': 0.0, 'coherence_score': 0.0, 'samples': 0}
    
    def _validate_symbol_coherence(
        self, 
        source_df: pd.DataFrame, 
        target_df: pd.DataFrame, 
        source_tf: str, 
        target_tf: str
    ) -> float:
        """Valida coherencia entre datos de un símbolo en dos timeframes"""
        try:
            if source_df.empty or target_df.empty:
                return 0.0
            
            # Encontrar períodos superpuestos
            common_start = max(source_df.index[0], target_df.index[0])
            common_end = min(source_df.index[-1], target_df.index[-1])
            
            if common_start >= common_end:
                return 0.0
            
            # Filtrar datos comunes
            source_common = source_df[(source_df.index >= common_start) & (source_df.index <= common_end)]
            target_common = target_df[(target_df.index >= common_start) & (target_df.index <= common_end)]
            
            if source_common.empty or target_common.empty:
                return 0.0
            
            # Calcular coherencia de precios (simplificado)
            source_prices = source_common['close'].values
            target_prices = target_common['close'].values
            
            # Interpolar para comparar
            if len(source_prices) != len(target_prices):
                min_len = min(len(source_prices), len(target_prices))
                source_prices = source_prices[:min_len]
                target_prices = target_prices[:min_len]
            
            if len(source_prices) == 0:
                return 0.0
            
            # Calcular correlación
            correlation = np.corrcoef(source_prices, target_prices)[0, 1]
            return float(correlation) if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error validating symbol coherence: {e}")
            return 0.0
    
    def _check_price_consistency(self, source_df: pd.DataFrame, agg_df: pd.DataFrame) -> float:
        """Verifica consistencia de precios entre datos fuente y agregados"""
        try:
            if source_df.empty or agg_df.empty:
                return 0.0
            
            # Verificar que los precios agregados son consistentes con los fuente
            # (simplificado - en implementación real sería más complejo)
            source_avg = source_df['close'].mean()
            agg_avg = agg_df['close'].mean()
            
            if source_avg == 0:
                return 0.0
            
            consistency = 1.0 - abs(source_avg - agg_avg) / source_avg
            return max(0.0, min(1.0, consistency))
            
        except Exception as e:
            self.logger.error(f"Error checking price consistency: {e}")
            return 0.0
    
    def _calculate_timeframe_coherence(self, alignment_results: Dict[str, AlignmentResult]) -> Dict[str, float]:
        """Calcula coherencia entre timeframes basada en resultados de alineación"""
        try:
            coherence_scores = {}
            
            for tf, result in alignment_results.items():
                if result.success and result.coherence_scores:
                    coherence_scores[tf] = np.mean(list(result.coherence_scores.values()))
                else:
                    coherence_scores[tf] = 0.0
            
            return coherence_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating timeframe coherence: {e}")
            return {}

# Funciones de conveniencia
def create_coordinator(config: Optional[Dict[str, Any]] = None) -> MultiTimeframeCoordinator:
    """Crea un coordinador multi-timeframe"""
    return MultiTimeframeCoordinator(config)

async def quick_coordinate_processing(
    symbols: List[str], 
    days_back: int = 365
) -> CoordinationResult:
    """Función de conveniencia para procesamiento coordinado rápido"""
    coordinator = MultiTimeframeCoordinator()
    return await coordinator.process_all_timeframes_coordinated(symbols, days_back)
