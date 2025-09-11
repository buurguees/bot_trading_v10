# Ruta: core/data/historical_data_adapter.py
"""
historical_data_adapter.py - ADAPTADOR PARA DATOS HISTÓRICOS
Adaptador que integra el nuevo sistema de base de datos por símbolo con el sistema existente
Ubicación: C:\TradingBot_v10\core\data\historical_data_adapter.py

FUNCIONALIDADES:
- Migración automática de datos existentes
- Compatibilidad con el sistema actual
- Interfaz unificada para acceso a datos
- Configuración desde YAML
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import asyncio
import json

from .symbol_database_manager import (
    SymbolDatabaseManager, 
    OHLCVData, 
    symbol_db_manager,
    insert_ohlcv_data,
    get_ohlcv_data,
    get_latest_ohlcv_data
)
from .database import db_manager as legacy_db_manager
from core.config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class HistoricalDataAdapter:
    """Adaptador para datos históricos con migración automática"""
    
    def __init__(self):
        self.symbol_db = SymbolDatabaseManager()
        self.legacy_db = legacy_db_manager
        self.config = self._load_config()
        
        # Configuración de migración
        self.migration_enabled = self.config.get('migration_enabled', True)
        self.auto_migrate = self.config.get('auto_migrate', True)
        
        logger.info("HistoricalDataAdapter inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde user_settings.yaml"""
        try:
            return {
                'migration_enabled': True,
                'auto_migrate': True,
                'symbols': ConfigLoader().get_main_config().get('data_collection', {}).get('real_time', {}).get('symbols', []),
                'timeframes': ConfigLoader().get_main_config().get('data_collection', {}).get('historical', {}).get('timeframes', []),
                'years': ConfigLoader().get_main_config().get('data_collection', {}).get('historical', {}).get('years', 1),
                'min_coverage_days': ConfigLoader().get_main_config().get('data_collection', {}).get('historical', {}).get('min_coverage_days', 365)
            }
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    async def migrate_legacy_data(self) -> Dict[str, Any]:
        """Migra datos del sistema legacy al nuevo sistema por símbolo"""
        if not self.migration_enabled:
            logger.info("Migración deshabilitada")
            return {'status': 'disabled'}
        
        try:
            logger.info("🔄 Iniciando migración de datos legacy...")
            
            # Obtener símbolos y timeframes configurados
            symbols = self.config.get('symbols', [])
            timeframes = self.config.get('timeframes', ['1h', '4h', '1d'])
            
            migration_results = {
                'status': 'completed',
                'symbols_processed': 0,
                'total_records_migrated': 0,
                'errors': [],
                'details': {}
            }
            
            for symbol in symbols:
                try:
                    logger.info(f"📊 Migrando datos para {symbol}...")
                    
                    # Obtener datos del sistema legacy
                    legacy_data = self.legacy_db.get_market_data(symbol, limit=1000000)
                    
                    if legacy_data.empty:
                        logger.warning(f"No hay datos legacy para {symbol}")
                        continue
                    
                    # Agrupar por timeframe (asumiendo que todos son 1h por ahora)
                    # En una implementación real, necesitarías datos por timeframe
                    for timeframe in timeframes:
                        try:
                            # Convertir datos legacy a formato OHLCV
                            ohlcv_data = []
                            for timestamp, row in legacy_data.iterrows():
                                try:
                                    ohlcv = OHLCVData(
                                        timestamp=int(timestamp.timestamp()),
                                        open=float(row['open']),
                                        high=float(row['high']),
                                        low=float(row['low']),
                                        close=float(row['close']),
                                        volume=float(row['volume'])
                                    )
                                    ohlcv_data.append(ohlcv)
                                except Exception as e:
                                    logger.warning(f"Error procesando registro {timestamp}: {e}")
                                    continue
                            
                            # Insertar en nuevo sistema
                            if ohlcv_data:
                                inserted = self.symbol_db.insert_data(symbol, timeframe, ohlcv_data)
                                migration_results['total_records_migrated'] += inserted
                                
                                migration_results['details'][f"{symbol}_{timeframe}"] = {
                                    'records_migrated': inserted,
                                    'status': 'success'
                                }
                                
                                logger.info(f"✅ {symbol}_{timeframe}: {inserted} registros migrados")
                        
                        except Exception as e:
                            error_msg = f"Error migrando {symbol}_{timeframe}: {e}"
                            logger.error(error_msg)
                            migration_results['errors'].append(error_msg)
                    
                    migration_results['symbols_processed'] += 1
                    
                except Exception as e:
                    error_msg = f"Error procesando {symbol}: {e}"
                    logger.error(error_msg)
                    migration_results['errors'].append(error_msg)
            
            logger.info(f"✅ Migración completada: {migration_results['total_records_migrated']} registros")
            return migration_results
            
        except Exception as e:
            logger.error(f"Error en migración: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_data(
        self, 
        symbol: str, 
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Obtiene datos históricos (nuevo sistema prioritario)"""
        try:
            # Intentar obtener del nuevo sistema
            data = get_ohlcv_data(symbol, timeframe, start_date, end_date, limit)
            
            if not data.empty:
                return data
            
            # Fallback al sistema legacy si no hay datos
            logger.warning(f"No hay datos en nuevo sistema para {symbol}_{timeframe}, usando legacy")
            return self._get_legacy_data(symbol, start_date, end_date, limit)
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}_{timeframe}: {e}")
            return pd.DataFrame()
    
    def _get_legacy_data(
        self, 
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Obtiene datos del sistema legacy como fallback"""
        try:
            # Convertir fechas a timestamps si es necesario
            start_ts = int(start_date.timestamp()) if start_date else None
            end_ts = int(end_date.timestamp()) if end_date else None
            
            # Obtener datos del sistema legacy
            data = self.legacy_db.get_market_data(
                symbol, 
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                limit=limit
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos legacy para {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Obtiene los datos más recientes"""
        try:
            # Intentar nuevo sistema
            data = get_latest_ohlcv_data(symbol, timeframe, limit)
            
            if not data.empty:
                return data
            
            # Fallback al sistema legacy
            return self.legacy_db.get_latest_market_data(symbol, limit)
            
        except Exception as e:
            logger.error(f"Error obteniendo datos recientes para {symbol}_{timeframe}: {e}")
            return pd.DataFrame()
    
    def get_data_range(self, symbol: str, timeframe: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Obtiene el rango de fechas de los datos disponibles"""
        try:
            # Intentar nuevo sistema
            start_date, end_date = self.symbol_db.get_data_range(symbol, timeframe)
            
            if start_date and end_date:
                return start_date, end_date
            
            # Fallback al sistema legacy
            legacy_range = self.legacy_db.get_data_date_range(symbol)
            return legacy_range
            
        except Exception as e:
            logger.error(f"Error obteniendo rango de datos para {symbol}_{timeframe}: {e}")
            return None, None
    
    def get_record_count(self, symbol: str, timeframe: str) -> int:
        """Obtiene el número de registros disponibles"""
        try:
            # Intentar nuevo sistema
            count = self.symbol_db.get_record_count(symbol, timeframe)
            
            if count > 0:
                return count
            
            # Fallback al sistema legacy
            return self.legacy_db.get_market_data_count_fast(symbol)
            
        except Exception as e:
            logger.error(f"Error contando registros para {symbol}_{timeframe}: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas de todas las bases de datos"""
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'new_system': {},
                'legacy_system': {},
                'migration_status': 'unknown'
            }
            
            # Estadísticas del nuevo sistema
            symbols = self.symbol_db.get_all_symbols()
            for symbol in symbols:
                timeframes = self.symbol_db.get_symbol_timeframes(symbol)
                stats['new_system'][symbol] = {}
                
                for timeframe in timeframes:
                    symbol_stats = self.symbol_db.get_database_stats(symbol, timeframe)
                    stats['new_system'][symbol][timeframe] = symbol_stats
            
            # Estadísticas del sistema legacy
            try:
                legacy_stats = self.legacy_db.get_database_stats()
                stats['legacy_system'] = legacy_stats
            except Exception as e:
                stats['legacy_system'] = {'error': str(e)}
            
            # Verificar estado de migración
            if stats['new_system'] and stats['legacy_system']:
                stats['migration_status'] = 'partial'
            elif stats['new_system']:
                stats['migration_status'] = 'completed'
            elif stats['legacy_system']:
                stats['migration_status'] = 'pending'
            else:
                stats['migration_status'] = 'no_data'
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def insert_data(self, symbol: str, timeframe: str, data: List[OHLCVData]) -> int:
        """Inserta datos en el nuevo sistema"""
        try:
            return self.symbol_db.insert_data(symbol, timeframe, data)
        except Exception as e:
            logger.error(f"Error insertando datos para {symbol}_{timeframe}: {e}")
            return 0
    
    def cleanup_old_data(self, days_threshold: int = 30) -> Dict[str, int]:
        """Limpia datos antiguos de todas las bases de datos"""
        try:
            cleanup_results = {}
            symbols = self.symbol_db.get_all_symbols()
            
            for symbol in symbols:
                timeframes = self.symbol_db.get_symbol_timeframes(symbol)
                symbol_cleaned = 0
                
                for timeframe in timeframes:
                    cleaned = self.symbol_db.compress_old_data(symbol, timeframe, days_threshold)
                    symbol_cleaned += cleaned
                
                cleanup_results[symbol] = symbol_cleaned
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Error limpiando datos antiguos: {e}")
            return {}
    
    def get_coverage_analysis(self) -> Dict[str, Any]:
        """Analiza la cobertura de datos en ambos sistemas"""
        try:
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'new_system_coverage': {},
                'legacy_system_coverage': {},
                'recommendations': []
            }
            
            symbols = self.config.get('symbols', [])
            timeframes = self.config.get('timeframes', [])
            min_days = self.config.get('min_coverage_days', 365)
            
            # Analizar nuevo sistema
            for symbol in symbols:
                analysis['new_system_coverage'][symbol] = {}
                
                for timeframe in timeframes:
                    try:
                        start_date, end_date = self.get_data_range(symbol, timeframe)
                        record_count = self.get_record_count(symbol, timeframe)
                        
                        if start_date and end_date:
                            days_covered = (end_date - start_date).days
                            meets_requirement = days_covered >= min_days
                        else:
                            days_covered = 0
                            meets_requirement = False
                        
                        analysis['new_system_coverage'][symbol][timeframe] = {
                            'record_count': record_count,
                            'days_covered': days_covered,
                            'meets_requirement': meets_requirement,
                            'start_date': start_date.isoformat() if start_date else None,
                            'end_date': end_date.isoformat() if end_date else None
                        }
                        
                    except Exception as e:
                        analysis['new_system_coverage'][symbol][timeframe] = {
                            'error': str(e)
                        }
            
            # Generar recomendaciones
            total_symbols = len(symbols)
            total_timeframes = len(timeframes)
            total_combinations = total_symbols * total_timeframes
            
            complete_combinations = 0
            for symbol_data in analysis['new_system_coverage'].values():
                for timeframe_data in symbol_data.values():
                    if isinstance(timeframe_data, dict) and timeframe_data.get('meets_requirement', False):
                        complete_combinations += 1
            
            coverage_percentage = (complete_combinations / total_combinations * 100) if total_combinations > 0 else 0
            
            if coverage_percentage < 50:
                analysis['recommendations'].append("🚨 Cobertura crítica: Menos del 50% de datos disponibles")
            elif coverage_percentage < 80:
                analysis['recommendations'].append("⚠️ Cobertura insuficiente: Menos del 80% de datos disponibles")
            else:
                analysis['recommendations'].append("✅ Cobertura adecuada: Más del 80% de datos disponibles")
            
            analysis['overall_coverage_percentage'] = coverage_percentage
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando cobertura: {e}")
            return {'error': str(e)}

# Instancia global del adaptador
historical_data_adapter = HistoricalDataAdapter()

# Funciones de conveniencia para compatibilidad
def get_historical_data(
    symbol: str, 
    timeframe: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Función de conveniencia para obtener datos históricos"""
    return historical_data_adapter.get_data(symbol, timeframe, start_date, end_date, limit)

def get_latest_historical_data(symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    """Función de conveniencia para obtener datos recientes"""
    return historical_data_adapter.get_latest_data(symbol, timeframe, limit)

def get_historical_data_range(symbol: str, timeframe: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Función de conveniencia para obtener rango de datos"""
    return historical_data_adapter.get_data_range(symbol, timeframe)

def get_historical_data_count(symbol: str, timeframe: str) -> int:
    """Función de conveniencia para contar registros"""
    return historical_data_adapter.get_record_count(symbol, timeframe)
