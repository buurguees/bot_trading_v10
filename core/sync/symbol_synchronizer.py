# Ruta: core/sync/symbol_synchronizer.py
"""
Sistema de Sincronización de Símbolos - ENTERPRISE
Sincroniza timestamps de todos los símbolos para ejecución paralela
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import asyncio
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

@dataclass
class SyncMetrics:
    """Métricas de sincronización enterprise"""
    total_symbols: int
    total_timeframes: int
    sync_quality_score: float
    timeline_coverage: float
    gaps_detected: int
    alignment_errors: int
    processing_time: float
    memory_usage_mb: float
    timestamp_precision: float

@dataclass
class MasterTimeline:
    """Timeline maestro unificado"""
    timestamps: List[int]
    symbols: List[str]
    timeframes: List[str]
    start_date: datetime
    end_date: datetime
    total_periods: int
    sync_quality: float
    created_at: datetime

class SymbolSynchronizer:
    """Sincronizador enterprise de símbolos con métricas avanzadas"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.sync_cache = {}
        self.performance_metrics = {}
        self.max_workers = 4  # Límite de concurrencia
        
    async def sync_all_symbols(self, symbols: List[str], timeframes: List[str]) -> Dict[str, Any]:
        """
        Sincroniza todos los símbolos con métricas enterprise
        
        Args:
            symbols: Lista de símbolos a sincronizar
            timeframes: Lista de timeframes a procesar
            
        Returns:
            Dict con resultados de sincronización
        """
        start_time = time.time()
        logger.info(f"🔄 Iniciando sincronización enterprise de {len(symbols)} símbolos")
        
        try:
            # 1. Validar datos disponibles
            validation_result = await self._validate_data_availability(symbols, timeframes)
            if not validation_result['valid']:
                return {
                    'status': 'error',
                    'message': f"Datos insuficientes: {validation_result['message']}",
                    'metrics': None
                }
            
            # 2. Crear timeline maestro
            master_timeline = await self._create_master_timeline(symbols, timeframes)
            if not master_timeline:
                return {
                    'status': 'error',
                    'message': "No se pudo crear timeline maestro",
                    'metrics': None
                }
            
            # 3. Sincronizar datos por símbolo
            sync_results = await self._sync_symbol_data_parallel(symbols, timeframes, master_timeline)
            
            # 4. Calcular métricas enterprise
            metrics = await self._calculate_enterprise_metrics(sync_results, master_timeline)
            
            # 5. Validar calidad de sincronización
            quality_check = await self._validate_sync_quality(sync_results, master_timeline)
            
            processing_time = time.time() - start_time
            
            result = {
                'status': 'success',
                'master_timeline': asdict(master_timeline),
                'sync_results': sync_results,
                'metrics': asdict(metrics),
                'quality_check': quality_check,
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Sincronización completada en {processing_time:.2f}s")
            logger.info(f"📊 Calidad de sincronización: {quality_check['overall_score']:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'metrics': None
            }
    
    async def _validate_data_availability(self, symbols: List[str], timeframes: List[str]) -> Dict[str, Any]:
        """Valida disponibilidad de datos para sincronización"""
        try:
            if not self.db_manager:
                return {'valid': False, 'message': 'Database manager no disponible'}
            
            missing_data = []
            total_records = 0
            
            for symbol in symbols:
                for timeframe in timeframes:
                    # Verificar datos en BD principal
                    count = self.db_manager.get_market_data_count_fast(symbol)
                    if count == 0:
                        missing_data.append(f"{symbol}_{timeframe}")
                    else:
                        total_records += count
            
            if missing_data:
                return {
                    'valid': False,
                    'message': f"Datos faltantes para: {', '.join(missing_data[:5])}...",
                    'missing_count': len(missing_data)
                }
            
            return {
                'valid': True,
                'total_records': total_records,
                'symbols_checked': len(symbols),
                'timeframes_checked': len(timeframes)
            }
            
        except Exception as e:
            logger.error(f"Error validando disponibilidad: {e}")
            return {'valid': False, 'message': str(e)}
    
    async def _create_master_timeline(self, symbols: List[str], timeframes: List[str]) -> Optional[MasterTimeline]:
        """Crea timeline maestro unificado"""
        try:
            logger.info("🔄 Creando timeline maestro...")
            
            # Obtener rango de fechas de todos los símbolos
            all_timestamps = set()
            
            for symbol in symbols:
                for timeframe in timeframes:
                    # Obtener datos del símbolo
                    data = self.db_manager.get_market_data_optimized(symbol)
                    if not data.empty and 'timestamp' in data.columns:
                        timestamps = data['timestamp'].tolist()
                        all_timestamps.update(timestamps)
            
            if not all_timestamps:
                logger.warning("⚠️ No se encontraron timestamps para crear timeline")
                return None
            
            # Crear timeline ordenado
            sorted_timestamps = sorted(list(all_timestamps))
            
            # Calcular rango de fechas
            start_ts = min(sorted_timestamps)
            end_ts = max(sorted_timestamps)
            
            start_date = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc)
            
            # Calcular calidad de sincronización
            sync_quality = self._calculate_timeline_quality(sorted_timestamps, symbols, timeframes)
            
            master_timeline = MasterTimeline(
                timestamps=sorted_timestamps,
                symbols=symbols,
                timeframes=timeframes,
                start_date=start_date,
                end_date=end_date,
                total_periods=len(sorted_timestamps),
                sync_quality=sync_quality,
                created_at=datetime.now()
            )
            
            logger.info(f"✅ Timeline maestro creado: {len(sorted_timestamps)} períodos")
            logger.info(f"📅 Rango: {start_date} - {end_date}")
            
            return master_timeline
            
        except Exception as e:
            logger.error(f"Error creando timeline maestro: {e}")
            return None
    
    def _calculate_timeline_quality(self, timestamps: List[int], symbols: List[str], timeframes: List[str]) -> float:
        """Calcula calidad del timeline maestro"""
        try:
            if len(timestamps) < 2:
                return 0.0
            
            # Calcular intervalos entre timestamps
            intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            
            # Calcular consistencia de intervalos
            if intervals:
                mean_interval = np.mean(intervals)
                std_interval = np.std(intervals)
                consistency = 1.0 - (std_interval / mean_interval) if mean_interval > 0 else 0.0
            else:
                consistency = 0.0
            
            # Factor de cobertura (símbolos * timeframes)
            coverage_factor = min(1.0, (len(symbols) * len(timeframes)) / 20.0)
            
            # Calidad general
            quality = (consistency * 0.7 + coverage_factor * 0.3) * 100
            
            return min(100.0, max(0.0, quality))
            
        except Exception as e:
            logger.error(f"Error calculando calidad del timeline: {e}")
            return 0.0
    
    async def _sync_symbol_data_parallel(self, symbols: List[str], timeframes: List[str], 
                                       master_timeline: MasterTimeline) -> Dict[str, Any]:
        """Sincroniza datos de símbolos en paralelo"""
        try:
            logger.info(f"🔄 Sincronizando {len(symbols)} símbolos en paralelo...")
            
            sync_results = {}
            
            # Usar ThreadPoolExecutor para paralelización controlada
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Crear tareas para cada símbolo
                future_to_symbol = {}
                
                for symbol in symbols:
                    future = executor.submit(
                        self._sync_single_symbol,
                        symbol, timeframes, master_timeline
                    )
                    future_to_symbol[future] = symbol
                
                # Procesar resultados con delay de 100ms entre operaciones
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                        sync_results[symbol] = result
                        logger.debug(f"✅ Sincronizado {symbol}: {result['status']}")
                        
                        # Delay de 100ms para evitar conflictos con API
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"❌ Error sincronizando {symbol}: {e}")
                        sync_results[symbol] = {
                            'status': 'error',
                            'message': str(e),
                            'data': None
                        }
            
            successful_syncs = sum(1 for r in sync_results.values() if r['status'] == 'success')
            logger.info(f"✅ Sincronización completada: {successful_syncs}/{len(symbols)} símbolos")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Error en sincronización paralela: {e}")
            return {}
    
    def _sync_single_symbol(self, symbol: str, timeframes: List[str], 
                          master_timeline: MasterTimeline) -> Dict[str, Any]:
        """Sincroniza un solo símbolo"""
        try:
            symbol_data = {}
            
            for timeframe in timeframes:
                # Obtener datos del símbolo
                data = self.db_manager.get_market_data_optimized(symbol)
                
                if data.empty:
                    symbol_data[timeframe] = {
                        'status': 'no_data',
                        'records': 0,
                        'aligned_records': 0
                    }
                    continue
                
                # Alinear con timeline maestro
                aligned_data = self._align_with_master_timeline(data, master_timeline, timeframe)
                
                symbol_data[timeframe] = {
                    'status': 'success',
                    'records': len(data),
                    'aligned_records': len(aligned_data),
                    'alignment_quality': self._calculate_alignment_quality(data, aligned_data),
                    'data': aligned_data
                }
            
            return {
                'status': 'success',
                'symbol': symbol,
                'timeframes': symbol_data,
                'total_records': sum(tf['records'] for tf in symbol_data.values()),
                'total_aligned': sum(tf['aligned_records'] for tf in symbol_data.values())
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'symbol': symbol,
                'message': str(e),
                'timeframes': {}
            }
    
    def _align_with_master_timeline(self, data: pd.DataFrame, master_timeline: MasterTimeline, 
                                  timeframe: str) -> pd.DataFrame:
        """Alinea datos de un símbolo con el timeline maestro"""
        try:
            if data.empty:
                return pd.DataFrame()
            
            # Convertir timestamps a enteros si es necesario
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp']).astype('int64') // 10**6
            
            # Filtrar datos que coincidan con timeline maestro
            master_timestamps = set(master_timeline.timestamps)
            aligned_data = data[data['timestamp'].isin(master_timestamps)].copy()
            
            # Ordenar por timestamp
            aligned_data = aligned_data.sort_values('timestamp').reset_index(drop=True)
            
            return aligned_data
            
        except Exception as e:
            logger.error(f"Error alineando datos: {e}")
            return pd.DataFrame()
    
    def _calculate_alignment_quality(self, original_data: pd.DataFrame, aligned_data: pd.DataFrame) -> float:
        """Calcula calidad de alineación"""
        try:
            if original_data.empty:
                return 0.0
            
            alignment_ratio = len(aligned_data) / len(original_data)
            return min(100.0, alignment_ratio * 100)
            
        except Exception as e:
            logger.error(f"Error calculando calidad de alineación: {e}")
            return 0.0
    
    async def _calculate_enterprise_metrics(self, sync_results: Dict[str, Any], 
                                          master_timeline: MasterTimeline) -> SyncMetrics:
        """Calcula métricas enterprise de sincronización"""
        try:
            total_symbols = len(sync_results)
            total_timeframes = len(master_timeline.timeframes)
            
            # Calcular métricas de calidad
            successful_syncs = sum(1 for r in sync_results.values() if r['status'] == 'success')
            sync_quality_score = (successful_syncs / total_symbols * 100) if total_symbols > 0 else 0
            
            # Calcular cobertura del timeline
            total_records = sum(r.get('total_records', 0) for r in sync_results.values())
            total_aligned = sum(r.get('total_aligned', 0) for r in sync_results.values())
            timeline_coverage = (total_aligned / total_records * 100) if total_records > 0 else 0
            
            # Detectar gaps
            gaps_detected = self._detect_timeline_gaps(master_timeline)
            
            # Calcular errores de alineación
            alignment_errors = sum(
                sum(1 for tf in r.get('timeframes', {}).values() 
                    if tf.get('alignment_quality', 0) < 80)
                for r in sync_results.values()
            )
            
            # Métricas de rendimiento
            processing_time = time.time() - getattr(self, '_start_time', time.time())
            memory_usage = self._estimate_memory_usage(sync_results)
            
            # Precisión de timestamps
            timestamp_precision = self._calculate_timestamp_precision(master_timeline)
            
            return SyncMetrics(
                total_symbols=total_symbols,
                total_timeframes=total_timeframes,
                sync_quality_score=sync_quality_score,
                timeline_coverage=timeline_coverage,
                gaps_detected=gaps_detected,
                alignment_errors=alignment_errors,
                processing_time=processing_time,
                memory_usage_mb=memory_usage,
                timestamp_precision=timestamp_precision
            )
            
        except Exception as e:
            logger.error(f"Error calculando métricas enterprise: {e}")
            return SyncMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def _detect_timeline_gaps(self, master_timeline: MasterTimeline) -> int:
        """Detecta gaps en el timeline maestro"""
        try:
            if len(master_timeline.timestamps) < 2:
                return 0
            
            gaps = 0
            for i in range(len(master_timeline.timestamps) - 1):
                interval = master_timeline.timestamps[i+1] - master_timeline.timestamps[i]
                # Considerar gap si el intervalo es más del doble del promedio
                avg_interval = (master_timeline.timestamps[-1] - master_timeline.timestamps[0]) / len(master_timeline.timestamps)
                if interval > avg_interval * 2:
                    gaps += 1
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error detectando gaps: {e}")
            return 0
    
    def _estimate_memory_usage(self, sync_results: Dict[str, Any]) -> float:
        """Estima uso de memoria en MB"""
        try:
            total_records = sum(r.get('total_aligned', 0) for r in sync_results.values())
            # Estimación: ~100 bytes por registro
            memory_bytes = total_records * 100
            return memory_bytes / (1024 * 1024)  # Convertir a MB
            
        except Exception as e:
            logger.error(f"Error estimando memoria: {e}")
            return 0.0
    
    def _calculate_timestamp_precision(self, master_timeline: MasterTimeline) -> float:
        """Calcula precisión de timestamps"""
        try:
            if len(master_timeline.timestamps) < 2:
                return 0.0
            
            # Calcular consistencia de intervalos
            intervals = [master_timeline.timestamps[i+1] - master_timeline.timestamps[i] 
                        for i in range(len(master_timeline.timestamps)-1)]
            
            if intervals:
                mean_interval = np.mean(intervals)
                std_interval = np.std(intervals)
                precision = 1.0 - (std_interval / mean_interval) if mean_interval > 0 else 0.0
                return min(100.0, max(0.0, precision * 100))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculando precisión de timestamps: {e}")
            return 0.0
    
    async def _validate_sync_quality(self, sync_results: Dict[str, Any], 
                                   master_timeline: MasterTimeline) -> Dict[str, Any]:
        """Valida calidad general de la sincronización"""
        try:
            # Calcular score general
            successful_syncs = sum(1 for r in sync_results.values() if r['status'] == 'success')
            total_symbols = len(sync_results)
            
            # Calcular calidad promedio de alineación
            alignment_qualities = []
            for result in sync_results.values():
                if result['status'] == 'success':
                    for tf_data in result.get('timeframes', {}).values():
                        if 'alignment_quality' in tf_data:
                            alignment_qualities.append(tf_data['alignment_quality'])
            
            avg_alignment_quality = np.mean(alignment_qualities) if alignment_qualities else 0
            
            # Score general
            overall_score = (successful_syncs / total_symbols * 0.6 + avg_alignment_quality * 0.4) if total_symbols > 0 else 0
            
            # Recomendaciones
            recommendations = []
            if overall_score < 80:
                recommendations.append("🔧 Considerar reparar datos antes de sincronizar")
            if master_timeline.sync_quality < 90:
                recommendations.append("📊 Timeline maestro necesita optimización")
            if len(alignment_qualities) > 0 and np.mean(alignment_qualities) < 85:
                recommendations.append("⚡ Revisar alineación de datos por timeframe")
            
            if not recommendations:
                recommendations.append("✅ Sincronización de alta calidad")
            
            return {
                'overall_score': overall_score,
                'success_rate': successful_syncs / total_symbols * 100 if total_symbols > 0 else 0,
                'avg_alignment_quality': avg_alignment_quality,
                'timeline_quality': master_timeline.sync_quality,
                'recommendations': recommendations,
                'status': 'excellent' if overall_score >= 90 else 'good' if overall_score >= 80 else 'needs_improvement'
            }
            
        except Exception as e:
            logger.error(f"Error validando calidad de sincronización: {e}")
            return {
                'overall_score': 0,
                'success_rate': 0,
                'avg_alignment_quality': 0,
                'timeline_quality': 0,
                'recommendations': ["❌ Error en validación de calidad"],
                'status': 'error'
            }
