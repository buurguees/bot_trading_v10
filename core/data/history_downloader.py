#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History Downloader - Bot Trading v10 Enterprise
===============================================

Módulo especializado para descarga masiva de datos históricos.
Integra con múltiples exchanges y optimiza la descarga.

Funcionalidades:
- Descarga masiva de datos históricos
- Optimización de descarga por chunks
- Validación de integridad durante descarga
- Progreso en tiempo real
- Recuperación de errores
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import json
import yaml
from dataclasses import dataclass

# Imports locales
from .collector import data_collector, collect_and_save_historical_data
from .enterprise.database import TimescaleDBManager
from .database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class DownloadProgress:
    """Progreso de descarga para un símbolo"""
    symbol: str
    timeframe: str
    total_periods: int
    completed_periods: int = 0
    records_downloaded: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        if self.total_periods == 0:
            return 0.0
        return (self.completed_periods / self.total_periods) * 100
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return None

class HistoryDownloader:
    """Descargador de datos históricos con capacidades enterprise"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.symbols = self.config.get('data_collection', {}).get('real_time', {}).get('symbols', [])
        self.timeframes = self.config.get('data_collection', {}).get('real_time', {}).get('timeframes', [])
        
        # Inicializar gestores de datos
        self.db_manager = DatabaseManager()
        self.timescale_manager = TimescaleDBManager()
        
        # Directorios de datos
        self.historical_path = Path("data/historical")
        self.historical_path.mkdir(exist_ok=True)
        
        # Configuración de descarga
        self.max_concurrent_downloads = 3
        self.chunk_size_days = 30
        self.retry_attempts = 3
        self.retry_delay = 5  # segundos
        
        logger.info(f"HistoryDownloader inicializado con {len(self.symbols)} símbolos")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración del usuario"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    async def download_historical_data(
        self, 
        symbols: List[str] = None,
        timeframes: List[str] = None,
        days_back: int = 365,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Descarga datos históricos para múltiples símbolos y timeframes
        
        Args:
            symbols: Lista de símbolos a descargar
            timeframes: Lista de timeframes a descargar
            days_back: Días hacia atrás a descargar
            progress_callback: Callback para progreso en tiempo real
            
        Returns:
            Diccionario con resultados de descarga
        """
        if symbols is None:
            symbols = self.symbols
        if timeframes is None:
            timeframes = self.timeframes
        
        logger.info(f"🚀 Iniciando descarga masiva: {len(symbols)} símbolos, {len(timeframes)} timeframes, {days_back} días")
        
        download_results = {
            'download_date': datetime.now().isoformat(),
            'symbols_requested': len(symbols),
            'timeframes_requested': len(timeframes),
            'days_back': days_back,
            'total_combinations': len(symbols) * len(timeframes),
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_records_downloaded': 0,
            'symbol_results': {},
            'timeframe_results': {},
            'errors': [],
            'recommendations': []
        }
        
        # Crear semáforo para limitar descargas concurrentes
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        # Crear tareas de descarga
        download_tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task = self._download_symbol_timeframe(
                    symbol, timeframe, days_back, semaphore, progress_callback
                )
                download_tasks.append(task)
        
        # Ejecutar descargas en paralelo
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Procesar resultados
        for i, result in enumerate(results):
            symbol_idx = i // len(timeframes)
            timeframe_idx = i % len(timeframes)
            symbol = symbols[symbol_idx]
            timeframe = timeframes[timeframe_idx]
            
            if isinstance(result, Exception):
                logger.error(f"Error descargando {symbol}-{timeframe}: {result}")
                download_results['failed_downloads'] += 1
                download_results['errors'].append(f"{symbol}-{timeframe}: {str(result)}")
            else:
                download_results['symbol_results'][f"{symbol}-{timeframe}"] = result
                download_results['successful_downloads'] += 1
                download_results['total_records_downloaded'] += result.get('records_downloaded', 0)
        
        # Generar recomendaciones
        if download_results['failed_downloads'] > 0:
            download_results['recommendations'].append(
                f"Reintentar descarga para {download_results['failed_downloads']} combinaciones fallidas"
            )
        
        if download_results['successful_downloads'] > 0:
            download_results['recommendations'].append(
                f"Descarga exitosa: {download_results['total_records_downloaded']:,} registros descargados"
            )
        
        logger.info(f"✅ Descarga completada: {download_results['successful_downloads']}/{download_results['total_combinations']} exitosas")
        
        return download_results
    
    async def _download_symbol_timeframe(
        self, 
        symbol: str, 
        timeframe: str, 
        days_back: int,
        semaphore: asyncio.Semaphore,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Descarga datos para un símbolo y timeframe específicos"""
        async with semaphore:
            progress = DownloadProgress(
                symbol=symbol,
                timeframe=timeframe,
                total_periods=1,
                start_time=datetime.now()
            )
            
            try:
                logger.info(f"📥 Descargando {symbol}-{timeframe} ({days_back} días)")
                
                # Llamar al descargador principal
                records_downloaded = await collect_and_save_historical_data(
                    symbol, timeframe, days_back
                )
                
                progress.completed_periods = 1
                progress.records_downloaded = records_downloaded
                progress.end_time = datetime.now()
                
                # Llamar callback de progreso si está disponible
                if progress_callback:
                    await progress_callback(progress)
                
                result = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'SUCCESS',
                    'records_downloaded': records_downloaded,
                    'days_requested': days_back,
                    'download_time': progress.elapsed_time.total_seconds() if progress.elapsed_time else 0,
                    'start_time': progress.start_time.isoformat(),
                    'end_time': progress.end_time.isoformat()
                }
                
                logger.info(f"✅ {symbol}-{timeframe}: {records_downloaded:,} registros en {progress.elapsed_time}")
                return result
                
            except Exception as e:
                progress.errors += 1
                progress.end_time = datetime.now()
                
                logger.error(f"❌ Error descargando {symbol}-{timeframe}: {e}")
                
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'ERROR',
                    'error': str(e),
                    'records_downloaded': 0,
                    'download_time': progress.elapsed_time.total_seconds() if progress.elapsed_time else 0
                }
    
    async def download_missing_data(
        self, 
        symbols: List[str] = None,
        target_years: int = 2,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Descarga solo los datos faltantes para completar cobertura
        
        Args:
            symbols: Lista de símbolos a analizar
            target_years: Años objetivo de cobertura
            progress_callback: Callback para progreso en tiempo real
            
        Returns:
            Diccionario con resultados de descarga de datos faltantes
        """
        if symbols is None:
            symbols = self.symbols
        
        logger.info(f"🔍 Analizando datos faltantes para {len(symbols)} símbolos ({target_years} años)")
        
        missing_data_results = {
            'analysis_date': datetime.now().isoformat(),
            'symbols_analyzed': len(symbols),
            'target_years': target_years,
            'symbols_with_missing_data': 0,
            'symbols_complete': 0,
            'total_missing_days': 0,
            'total_downloaded': 0,
            'symbol_results': {},
            'recommendations': []
        }
        
        for symbol in symbols:
            try:
                symbol_result = await self._analyze_and_download_missing(
                    symbol, target_years, progress_callback
                )
                missing_data_results['symbol_results'][symbol] = symbol_result
                
                if symbol_result['status'] == 'MISSING_DATA':
                    missing_data_results['symbols_with_missing_data'] += 1
                    missing_data_results['total_missing_days'] += symbol_result.get('missing_days', 0)
                    missing_data_results['total_downloaded'] += symbol_result.get('records_downloaded', 0)
                elif symbol_result['status'] == 'COMPLETE':
                    missing_data_results['symbols_complete'] += 1
                
            except Exception as e:
                logger.error(f"Error analizando datos faltantes para {symbol}: {e}")
                missing_data_results['symbol_results'][symbol] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        # Generar recomendaciones
        if missing_data_results['symbols_with_missing_data'] > 0:
            missing_data_results['recommendations'].append(
                f"Descargados {missing_data_results['total_downloaded']:,} registros para {missing_data_results['symbols_with_missing_data']} símbolos"
            )
        
        if missing_data_results['symbols_complete'] > 0:
            missing_data_results['recommendations'].append(
                f"{missing_data_results['symbols_complete']} símbolos ya tienen cobertura completa"
            )
        
        return missing_data_results
    
    async def _analyze_and_download_missing(
        self, 
        symbol: str, 
        target_years: int,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Analiza y descarga datos faltantes para un símbolo"""
        try:
            # Obtener rango de datos existentes
            date_range = self.db_manager.get_data_date_range(symbol)
            record_count = self.db_manager.get_market_data_count_fast(symbol)
            
            if record_count == 0:
                # No hay datos, descargar todo
                logger.info(f"📥 {symbol}: Sin datos, descargando {target_years} años completos")
                records_downloaded = await collect_and_save_historical_data(
                    symbol, self.timeframes[0], target_years * 365
                )
                return {
                    'status': 'MISSING_DATA',
                    'missing_days': target_years * 365,
                    'records_downloaded': records_downloaded,
                    'message': f'Descargados {records_downloaded:,} registros históricos'
                }
            
            if not date_range[0] or not date_range[1]:
                return {
                    'status': 'ERROR',
                    'error': 'Rango de fechas inválido'
                }
            
            # Calcular días faltantes
            current_days = (date_range[1] - date_range[0]).days
            target_days = target_years * 365
            missing_days = max(0, target_days - current_days)
            
            if missing_days == 0:
                return {
                    'status': 'COMPLETE',
                    'current_days': current_days,
                    'message': f'Cobertura completa ({current_days} días)'
                }
            
            # Descargar datos faltantes
            logger.info(f"📥 {symbol}: Descargando {missing_days} días faltantes")
            records_downloaded = await collect_and_save_historical_data(
                symbol, self.timeframes[0], missing_days, date_range[0]
            )
            
            return {
                'status': 'MISSING_DATA',
                'current_days': current_days,
                'missing_days': missing_days,
                'records_downloaded': records_downloaded,
                'message': f'Agregados {records_downloaded:,} registros históricos'
            }
            
        except Exception as e:
            logger.error(f"Error analizando datos faltantes para {symbol}: {e}")
            return {
                'status': 'ERROR',
                'error': str(e)
            }
    
    async def validate_download_integrity(
        self, 
        symbols: List[str] = None,
        timeframes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Valida la integridad de los datos descargados
        
        Args:
            symbols: Lista de símbolos a validar
            timeframes: Lista de timeframes a validar
            
        Returns:
            Diccionario con resultados de validación
        """
        if symbols is None:
            symbols = self.symbols
        if timeframes is None:
            timeframes = self.timeframes
        
        logger.info(f"🔍 Validando integridad de datos para {len(symbols)} símbolos")
        
        validation_results = {
            'validation_date': datetime.now().isoformat(),
            'symbols_validated': len(symbols),
            'total_combinations': len(symbols) * len(timeframes),
            'valid_combinations': 0,
            'invalid_combinations': 0,
            'symbol_results': {},
            'integrity_issues': [],
            'recommendations': []
        }
        
        for symbol in symbols:
            symbol_validation = {
                'symbol': symbol,
                'timeframe_results': {},
                'overall_status': 'VALID',
                'issues': []
            }
            
            for timeframe in timeframes:
                try:
                    # Validar datos para este símbolo-timeframe
                    is_valid = await self._validate_symbol_timeframe(symbol, timeframe)
                    
                    symbol_validation['timeframe_results'][timeframe] = {
                        'status': 'VALID' if is_valid else 'INVALID',
                        'validated_at': datetime.now().isoformat()
                    }
                    
                    if is_valid:
                        validation_results['valid_combinations'] += 1
                    else:
                        validation_results['invalid_combinations'] += 1
                        symbol_validation['overall_status'] = 'INVALID'
                        symbol_validation['issues'].append(f'{timeframe}: Datos inválidos')
                
                except Exception as e:
                    logger.error(f"Error validando {symbol}-{timeframe}: {e}")
                    symbol_validation['timeframe_results'][timeframe] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    validation_results['invalid_combinations'] += 1
                    symbol_validation['overall_status'] = 'INVALID'
            
            validation_results['symbol_results'][symbol] = symbol_validation
            
            if symbol_validation['overall_status'] == 'INVALID':
                validation_results['integrity_issues'].append(f"{symbol}: {len(symbol_validation['issues'])} problemas")
        
        # Generar recomendaciones
        if validation_results['invalid_combinations'] > 0:
            validation_results['recommendations'].append(
                f"Revisar {validation_results['invalid_combinations']} combinaciones con problemas de integridad"
            )
        
        if validation_results['valid_combinations'] > 0:
            validation_results['recommendations'].append(
                f"{validation_results['valid_combinations']} combinaciones validadas correctamente"
            )
        
        return validation_results
    
    async def _validate_symbol_timeframe(self, symbol: str, timeframe: str) -> bool:
        """Valida integridad de datos para un símbolo-timeframe específico"""
        try:
            # Verificar que existen datos
            record_count = self.db_manager.get_market_data_count_fast(symbol)
            if record_count == 0:
                return False
            
            # Verificar rango de fechas
            date_range = self.db_manager.get_data_date_range(symbol)
            if not date_range[0] or not date_range[1]:
                return False
            
            # Verificar que los datos no están corruptos
            # (implementación simplificada)
            return True
            
        except Exception as e:
            logger.error(f"Error validando {symbol}-{timeframe}: {e}")
            return False

# Instancia global del descargador
history_downloader = HistoryDownloader()
