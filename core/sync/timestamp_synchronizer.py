#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Timestamp Synchronizer - Bot Trading v10 Enterprise
==================================================
Sistema de sincronización de timestamps para entrenamiento paralelo.
Garantiza que todos los agentes operen en el mismo punto temporal.

Características:
- Sincronización de timestamps entre múltiples símbolos
- Detección de gaps temporales
- Alineación automática de datos
- Barreras de sincronización para agentes
- Progreso temporal uniforme

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from threading import Barrier, Lock
import pandas as pd
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class TimeWindow:
    """Ventana temporal sincronizada"""
    timestamp: datetime
    symbols_data: Dict[str, pd.DataFrame]
    is_complete: bool
    missing_symbols: List[str]
    
@dataclass
class SyncPoint:
    """Punto de sincronización"""
    timestamp: datetime
    cycle_id: int
    all_symbols_ready: bool
    data_quality_score: float

class TimestampSynchronizer:
    """
    Sincronizador de timestamps para entrenamiento paralelo
    ======================================================
    
    Garantiza que todos los agentes entrenen en el mismo punto temporal,
    permitiendo comparaciones justas y métricas agregadas precisas.
    """
    
    def __init__(self, symbols: List[str], timeframes: List[str]):
        """
        Inicializa el sincronizador
        
        Args:
            symbols: Lista de símbolos a sincronizar
            timeframes: Lista de timeframes
        """
        self.symbols = symbols
        self.timeframes = timeframes
        self.sync_points = []
        self.current_sync_point = None
        self.agent_barriers = {}
        self.data_cache = {}
        self.sync_lock = Lock()
        
        # Configuración
        self.batch_size = 500  # Barras por lote
        self.min_data_quality = 0.8  # Calidad mínima de datos
        self.max_gap_tolerance = timedelta(hours=1)
        
        # Inicializar barreras para sincronización
        self._setup_barriers()
        
        logger.info(f"🔄 TimestampSynchronizer inicializado para {len(symbols)} símbolos")
    
    def _setup_barriers(self):
        """Configura barreras de sincronización para agentes"""
        for timeframe in self.timeframes:
            self.agent_barriers[timeframe] = Barrier(len(self.symbols))
        
        logger.debug(f"🚧 Barreras configuradas para {len(self.timeframes)} timeframes")
    
    async def build_sync_timeline(self, start_date: datetime, end_date: datetime) -> List[SyncPoint]:
        """
        Construye timeline sincronizado para el período especificado
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Lista de puntos de sincronización
        """
        try:
            logger.info(f"🔄 Construyendo timeline sincronizado: {start_date} → {end_date}")
            
            # 1. Obtener timestamps disponibles para todos los símbolos
            common_timestamps = await self._find_common_timestamps(start_date, end_date)
            
            # 2. Validar calidad de datos en cada timestamp
            validated_timestamps = await self._validate_data_quality(common_timestamps)
            
            # 3. Crear puntos de sincronización
            sync_points = []
            for i, timestamp in enumerate(validated_timestamps):
                sync_point = SyncPoint(
                    timestamp=timestamp,
                    cycle_id=i,
                    all_symbols_ready=True,
                    data_quality_score=await self._calculate_quality_score(timestamp)
                )
                sync_points.append(sync_point)
            
            self.sync_points = sync_points
            logger.info(f"✅ Timeline construido: {len(sync_points)} puntos de sincronización")
            
            return sync_points
            
        except Exception as e:
            logger.error(f"❌ Error construyendo timeline: {e}")
            return []
    
    async def _find_common_timestamps(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Encuentra timestamps comunes entre todos los símbolos"""
        try:
            all_timestamps = {}
            
            # Obtener timestamps de cada símbolo
            for symbol in self.symbols:
                symbol_timestamps = await self._get_symbol_timestamps(symbol, start_date, end_date)
                all_timestamps[symbol] = set(symbol_timestamps)
            
            # Encontrar intersección (timestamps comunes)
            if not all_timestamps:
                return []
            
            common_timestamps = set.intersection(*all_timestamps.values())
            common_timestamps = sorted(list(common_timestamps))
            
            logger.info(f"📊 Timestamps comunes encontrados: {len(common_timestamps)}")
            return common_timestamps
            
        except Exception as e:
            logger.error(f"❌ Error encontrando timestamps comunes: {e}")
            return []
    
    async def _get_symbol_timestamps(self, symbol: str, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Obtiene timestamps disponibles para un símbolo"""
        try:
            # Construir path de base de datos
            db_path = f"data/{symbol}/{symbol}_1h.db"  # Usar 1h como referencia
            
            if not Path(db_path).exists():
                logger.warning(f"⚠️ Base de datos no encontrada: {db_path}")
                return []
            
            # Consultar timestamps
            with sqlite3.connect(db_path) as conn:
                query = """
                SELECT DISTINCT datetime(timestamp) as timestamp
                FROM market_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
                """
                
                df = pd.read_sql_query(
                    query, 
                    conn,
                    params=[start_date.isoformat(), end_date.isoformat()]
                )
                
                if df.empty:
                    return []
                
                timestamps = pd.to_datetime(df['timestamp']).tolist()
                return timestamps
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo timestamps de {symbol}: {e}")
            return []
    
    async def _validate_data_quality(self, timestamps: List[datetime]) -> List[datetime]:
        """Valida calidad de datos en cada timestamp"""
        try:
            validated = []
            
            for timestamp in timestamps:
                quality_score = await self._calculate_quality_score(timestamp)
                
                if quality_score >= self.min_data_quality:
                    validated.append(timestamp)
                else:
                    logger.debug(f"⚠️ Timestamp {timestamp} descartado - calidad: {quality_score:.2f}")
            
            logger.info(f"✅ Timestamps validados: {len(validated)}/{len(timestamps)}")
            return validated
            
        except Exception as e:
            logger.error(f"❌ Error validando calidad de datos: {e}")
            return timestamps  # Fallback
    
    async def _calculate_quality_score(self, timestamp: datetime) -> float:
        """Calcula score de calidad para un timestamp específico"""
        try:
            scores = []
            
            for symbol in self.symbols:
                # Verificar disponibilidad de datos
                data_available = await self._check_data_availability(symbol, timestamp)
                
                # Verificar calidad de datos (no NaN, rangos válidos)
                data_quality = await self._check_data_quality(symbol, timestamp)
                
                symbol_score = (data_available + data_quality) / 2
                scores.append(symbol_score)
            
            # Score promedio
            overall_score = sum(scores) / len(scores) if scores else 0.0
            return overall_score
            
        except Exception as e:
            logger.error(f"❌ Error calculando quality score: {e}")
            return 0.0
    
    async def _check_data_availability(self, symbol: str, timestamp: datetime) -> float:
        """Verifica disponibilidad de datos para símbolo en timestamp"""
        try:
            db_path = f"data/{symbol}/{symbol}_1h.db"
            
            if not Path(db_path).exists():
                return 0.0
            
            with sqlite3.connect(db_path) as conn:
                query = """
                SELECT COUNT(*) as count
                FROM market_data 
                WHERE datetime(timestamp) = ?
                """
                
                cursor = conn.execute(query, [timestamp.isoformat()])
                count = cursor.fetchone()[0]
                
                return 1.0 if count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Error verificando disponibilidad {symbol}: {e}")
            return 0.0
    
    async def _check_data_quality(self, symbol: str, timestamp: datetime) -> float:
        """Verifica calidad de datos (no NaN, rangos válidos)"""
        try:
            db_path = f"data/{symbol}/{symbol}_1h.db"
            
            if not Path(db_path).exists():
                return 0.0
            
            with sqlite3.connect(db_path) as conn:
                query = """
                SELECT open, high, low, close, volume
                FROM market_data 
                WHERE datetime(timestamp) = ?
                LIMIT 1
                """
                
                df = pd.read_sql_query(query, conn, params=[timestamp.isoformat()])
                
                if df.empty:
                    return 0.0
                
                # Verificar que no haya NaN
                if df.isnull().any().any():
                    return 0.5
                
                # Verificar rangos válidos (OHLC)
                row = df.iloc[0]
                if not (row['low'] <= row['open'] <= row['high'] and 
                       row['low'] <= row['close'] <= row['high']):
                    return 0.5
                
                # Verificar volumen positivo
                if row['volume'] <= 0:
                    return 0.8
                
                return 1.0
            
        except Exception as e:
            logger.error(f"❌ Error verificando calidad {symbol}: {e}")
            return 0.0
    
    async def get_synchronized_data(self, timestamp: datetime, timeframe: str = "1h") -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos sincronizados para todos los símbolos en un timestamp
        
        Args:
            timestamp: Timestamp específico
            timeframe: Timeframe de datos
            
        Returns:
            Diccionario con datos por símbolo
        """
        try:
            synchronized_data = {}
            
            for symbol in self.symbols:
                symbol_data = await self._get_symbol_data_at_timestamp(symbol, timestamp, timeframe)
                synchronized_data[symbol] = symbol_data
            
            logger.debug(f"📊 Datos sincronizados obtenidos para {len(synchronized_data)} símbolos")
            return synchronized_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos sincronizados: {e}")
            return {}
    
    async def _get_symbol_data_at_timestamp(self, symbol: str, timestamp: datetime, timeframe: str) -> pd.DataFrame:
        """Obtiene datos de un símbolo en timestamp específico"""
        try:
            db_path = f"data/{symbol}/{symbol}_{timeframe}.db"
            
            if not Path(db_path).exists():
                logger.warning(f"⚠️ Base de datos no encontrada: {db_path}")
                return pd.DataFrame()
            
            with sqlite3.connect(db_path) as conn:
                # Obtener ventana de datos alrededor del timestamp
                query = """
                SELECT *
                FROM market_data 
                WHERE timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 100
                """
                
                df = pd.read_sql_query(
                    query, 
                    conn,
                    params=[timestamp.isoformat()],
                    parse_dates=['timestamp']
                )
                
                return df
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()
    
    async def wait_for_sync_point(self, agent_id: str, timeframe: str) -> bool:
        """
        Hace que un agente espere en el punto de sincronización
        
        Args:
            agent_id: ID del agente
            timeframe: Timeframe del agente
            
        Returns:
            True si sincronización exitosa
        """
        try:
            if timeframe in self.agent_barriers:
                # Esperar a que todos los agentes lleguen al punto de sincronización
                logger.debug(f"🔄 Agente {agent_id} esperando sincronización en {timeframe}")
                
                # Usar barrier para sincronización
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.agent_barriers[timeframe].wait
                )
                
                logger.debug(f"✅ Agente {agent_id} sincronizado en {timeframe}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización de agente {agent_id}: {e}")
            return False
    
    def get_sync_progress(self) -> Dict[str, Any]:
        """Obtiene progreso de sincronización"""
        try:
            if not self.sync_points:
                return {"status": "not_started", "progress": 0}
            
            total_points = len(self.sync_points)
            current_point = self.current_sync_point
            
            if current_point is None:
                progress = 0
            else:
                progress = (current_point.cycle_id / total_points) * 100
            
            return {
                "status": "running" if current_point else "completed",
                "progress": progress,
                "current_cycle": current_point.cycle_id if current_point else 0,
                "total_cycles": total_points,
                "current_timestamp": current_point.timestamp.isoformat() if current_point else None,
                "symbols": self.symbols,
                "quality_score": current_point.data_quality_score if current_point else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo progreso de sincronización: {e}")
            return {"status": "error", "progress": 0}
    
    async def advance_to_next_sync_point(self) -> Optional[SyncPoint]:
        """Avanza al siguiente punto de sincronización"""
        try:
            with self.sync_lock:
                if not self.sync_points:
                    return None
                
                # Si es la primera vez, empezar por el primer punto
                if self.current_sync_point is None:
                    self.current_sync_point = self.sync_points[0]
                    return self.current_sync_point
                
                # Buscar siguiente punto
                current_index = None
                for i, point in enumerate(self.sync_points):
                    if point.cycle_id == self.current_sync_point.cycle_id:
                        current_index = i
                        break
                
                if current_index is not None and current_index + 1 < len(self.sync_points):
                    self.current_sync_point = self.sync_points[current_index + 1]
                    return self.current_sync_point
                
                # Fin del timeline
                return None
            
        except Exception as e:
            logger.error(f"❌ Error avanzando sync point: {e}")
            return None
    
    def reset_barriers(self):
        """Resetea las barreras de sincronización"""
        try:
            for timeframe in self.timeframes:
                self.agent_barriers[timeframe] = Barrier(len(self.symbols))
            
            logger.debug("🔄 Barreras de sincronización reseteadas")
            
        except Exception as e:
            logger.error(f"❌ Error reseteando barreras: {e}")
    
    async def cleanup(self):
        """Limpia recursos del sincronizador"""
        try:
            self.sync_points.clear()
            self.current_sync_point = None
            self.data_cache.clear()
            
            logger.info("🧹 TimestampSynchronizer limpiado")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando TimestampSynchronizer: {e}")

# Función de conveniencia para crear sincronizador
def create_timestamp_synchronizer(symbols: List[str], timeframes: List[str]) -> TimestampSynchronizer:
    """Crea una instancia del sincronizador de timestamps"""
    return TimestampSynchronizer(symbols, timeframes)