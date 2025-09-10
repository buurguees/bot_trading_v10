# Ruta: core/data/historical_data_manager.py
"""
historical_data_manager.py - GESTOR PRINCIPAL DE DATOS HISTÓRICOS
Gestor centralizado para verificación y descarga de datos históricos
Ubicación: C:\TradingBot_v10\core\data\historical_data_manager.py

FUNCIONALIDADES PRINCIPALES:
- Verificación automática de cobertura de datos históricos
- Descarga inteligente de datos faltantes por timeframe
- Integración con configuración de user_settings.yaml
- Reportes detallados de estado de datos
- Gestión de múltiples timeframes simultáneamente
- Validación de integridad de datos descargados
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from pathlib import Path

from .collector import (
    data_collector, 
    download_missing_data, 
    verify_data_integrity,
    download_multi_timeframe_with_alignment
)
from .history_analyzer import HistoryAnalyzer
from .history_downloader import HistoryDownloader
from config.config_loader import user_config
from .database import db_manager
from .symbol_database_manager import symbol_db_manager
from .historical_data_adapter import get_historical_data
from config.unified_config import unified_config

logger = logging.getLogger(__name__)

class HistoricalDataManager:
    """Gestor principal de datos históricos con capacidades enterprise"""
    
    def __init__(self):
        self.analyzer = HistoryAnalyzer()
        self.downloader = HistoryDownloader()
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde user_settings.yaml"""
        try:
            data_config = unified_config.get('data_collection', {})
            historical_config = data_config.get('historical', {})
            
            # Configuración por defecto si no está definida
            default_config = {
                'enabled': True,
                'years': 1,
                'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
                'align_after_download': True,
                'auto_verify_coverage': True,
                'min_coverage_days': 365,
                'download_missing': True,
                'verification_interval_hours': 24
            }
            
            # Combinar configuración con defaults
            config = {**default_config, **historical_config}
            
            # Obtener símbolos desde configuración
            symbols_config = user_config.get_value(['multi_symbol_settings', 'symbols'], {})
            config['symbols'] = [symbol for symbol, settings in symbols_config.items() 
                               if settings.get('enabled', True)]
            
            logger.info(f"Configuración cargada: {config['years']} años, {len(config['symbols'])} símbolos, {len(config['timeframes'])} timeframes")
            return config
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            # Configuración de emergencia
            return {
                'enabled': True,
                'years': 1,
                'timeframes': ['1h', '4h', '1d'],
                'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'],
                'min_coverage_days': 365,
                'download_missing': True
            }
    
    async def ensure_data_coverage(self) -> Dict[str, Any]:
        """
        Función principal: Asegura que existe al menos 1 año de datos para todos los timeframes
        
        Returns:
            Dict con resultados de verificación y descarga
        """
        try:
            logger.info("🚀 Iniciando verificación de cobertura de datos históricos")
            start_time = datetime.now()
            
            if not self.config['enabled']:
                logger.warning("Descarga de datos históricos deshabilitada en configuración")
                return {'status': 'disabled', 'message': 'Descarga deshabilitada'}
            
            # Verificar cobertura actual
            coverage_analysis = await self._analyze_current_coverage()
            
            # Determinar qué datos faltan
            missing_data = self._identify_missing_data(coverage_analysis)
            
            if not missing_data['needs_download']:
                logger.info("✅ Todos los datos históricos están completos")
                return {
                    'status': 'complete',
                    'coverage_analysis': coverage_analysis,
                    'message': 'Cobertura completa de datos históricos'
                }
            
            # Descargar datos faltantes
            if self.config['download_missing']:
                download_results = await self._download_missing_data(missing_data)
                
                # Verificar nuevamente después de la descarga
                final_verification = await self._analyze_current_coverage()
                
                return {
                    'status': 'completed',
                    'initial_coverage': coverage_analysis,
                    'missing_data': missing_data,
                    'download_results': download_results,
                    'final_coverage': final_verification,
                    'processing_time': (datetime.now() - start_time).total_seconds(),
                    'message': f'Descarga completada: {download_results.get("total_downloaded", 0)} registros'
                }
            else:
                return {
                    'status': 'missing_data_detected',
                    'coverage_analysis': coverage_analysis,
                    'missing_data': missing_data,
                    'message': 'Datos faltantes detectados pero descarga automática deshabilitada'
                }
                
        except Exception as e:
            logger.error(f"❌ Error en verificación de cobertura: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Error durante verificación de datos históricos'
            }
    
    async def _analyze_current_coverage(self) -> Dict[str, Any]:
        """Analiza la cobertura actual de datos históricos usando SQLite"""
        try:
            logger.info("🔍 Analizando cobertura actual de datos (SQLite)...")
            
            # Obtener todos los símbolos disponibles en SQLite
            available_symbols = symbol_db_manager.get_all_symbols()
            
            # Análisis por símbolo
            symbol_analysis = {}
            total_records = 0
            
            for symbol in self.config['symbols']:
                symbol_data = {
                    'record_count': 0,
                    'timeframes_available': [],
                    'coverage_percentage': 0.0,
                    'status': 'NO_DATA'
                }
                
                if symbol in available_symbols:
                    # Obtener timeframes disponibles para este símbolo
                    timeframes = symbol_db_manager.get_symbol_timeframes(symbol)
                    symbol_data['timeframes_available'] = timeframes
                    
                    # Calcular registros totales
                    for timeframe in timeframes:
                        count = symbol_db_manager.get_record_count(symbol, timeframe)
                        symbol_data['record_count'] += count
                        total_records += count
                    
                    # Calcular cobertura
                    expected_days = self.config['min_coverage_days']
                    records_per_day = self._get_records_per_day_for_timeframe('1h')  # Usar 1h como referencia
                    expected_records = expected_days * records_per_day
                    
                    if symbol_data['record_count'] > 0:
                        symbol_data['coverage_percentage'] = min(100.0, (symbol_data['record_count'] / expected_records) * 100)
                        symbol_data['status'] = 'COMPLETE' if symbol_data['coverage_percentage'] >= 90 else 'INSUFFICIENT'
                
                symbol_analysis[symbol] = symbol_data
            
            # Verificar cobertura por timeframe
            timeframe_coverage = {}
            for timeframe in self.config['timeframes']:
                timeframe_coverage[timeframe] = await self._check_timeframe_coverage_sqlite(timeframe)
            
            # Calcular estadísticas generales
            total_symbols = len(self.config['symbols'])
            symbols_with_data = sum(1 for symbol_data in symbol_analysis.values() 
                                  if symbol_data.get('record_count', 0) > 0)
            
            analysis = {
                'symbol_analysis': symbol_analysis,
                'summary': {
                    'total_symbols': total_symbols,
                    'symbols_with_data': symbols_with_data,
                    'coverage_percentage': (symbols_with_data / total_symbols * 100) if total_symbols > 0 else 0,
                    'timeframe_coverage': timeframe_coverage,
                    'total_records': total_records,
                    'analysis_date': datetime.now().isoformat()
                },
                'database_statistics': {
                    'total_records': total_records,
                    'unique_symbols': len(available_symbols),
                    'available_symbols': available_symbols
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando cobertura SQLite: {e}")
            return {'error': str(e)}
    
    async def _check_timeframe_coverage_sqlite(self, timeframe: str) -> Dict[str, Any]:
        """Verifica cobertura específica para un timeframe usando SQLite"""
        try:
            # Contar símbolos con datos para este timeframe
            symbols_with_data = 0
            total_records = 0
            
            for symbol in self.config['symbols']:
                if symbol in symbol_db_manager.get_all_symbols():
                    timeframes = symbol_db_manager.get_symbol_timeframes(symbol)
                    if timeframe in timeframes:
                        count = symbol_db_manager.get_record_count(symbol, timeframe)
                        if count > 0:
                            symbols_with_data += 1
                            total_records += count
            
            # Calcular días disponibles
            records_per_day = self._get_records_per_day_for_timeframe(timeframe)
            days_available = total_records / records_per_day if records_per_day > 0 else 0
            
            return {
                'timeframe': timeframe,
                'symbols_with_data': symbols_with_data,
                'total_symbols': len(self.config['symbols']),
                'total_records': total_records,
                'days_available': days_available,
                'meets_requirement': days_available >= self.config['min_coverage_days'],
                'status': 'COMPLETE' if days_available >= self.config['min_coverage_days'] else 'INSUFFICIENT'
            }
            
        except Exception as e:
            logger.error(f"Error verificando cobertura timeframe {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def _get_records_per_day_for_timeframe(self, timeframe: str) -> int:
        """Calcula registros por día para un timeframe"""
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
        minutes = timeframe_minutes.get(timeframe, 60)
        return 1440 // minutes  # 1440 minutos en un día
    
    async def _check_timeframe_coverage(self, timeframe: str) -> Dict[str, Any]:
        """Verifica cobertura específica para un timeframe (método legacy)"""
        try:
            # Para simplificar, verificamos solo el primer símbolo como representativo
            # En una implementación completa, verificaríamos todos los símbolos
            test_symbol = self.config['symbols'][0] if self.config['symbols'] else 'BTCUSDT'
            
            # Obtener datos del timeframe específico
            # Nota: Esto requeriría modificar la base de datos para almacenar timeframe
            # Por ahora, asumimos que todos los datos son del timeframe principal
            
            # Verificar rango de fechas
            date_range = db_manager.get_data_date_range(test_symbol)
            
            if not date_range[0] or not date_range[1]:
                return {
                    'timeframe': timeframe,
                    'status': 'NO_DATA',
                    'days_available': 0,
                    'meets_requirement': False
                }
            
            days_available = (date_range[1] - date_range[0]).days
            meets_requirement = days_available >= self.config['min_coverage_days']
            
            return {
                'timeframe': timeframe,
                'status': 'COMPLETE' if meets_requirement else 'INSUFFICIENT',
                'days_available': days_available,
                'meets_requirement': meets_requirement,
                'required_days': self.config['min_coverage_days']
            }
            
        except Exception as e:
            logger.error(f"Error verificando cobertura de {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'status': 'ERROR',
                'error': str(e),
                'meets_requirement': False
            }
    
    def _identify_missing_data(self, coverage_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Identifica qué datos faltan basado en el análisis de cobertura"""
        try:
            missing_data = {
                'needs_download': False,
                'symbols_to_download': [],
                'timeframes_to_download': [],
                'total_missing_days': 0,
                'details': {}
            }
            
            # Verificar símbolos sin datos
            for symbol, analysis in coverage_analysis.get('symbol_analysis', {}).items():
                if analysis.get('status') == 'NO_DATA':
                    missing_data['symbols_to_download'].append(symbol)
                    missing_data['needs_download'] = True
                    missing_data['details'][symbol] = {
                        'status': 'NO_DATA',
                        'missing_days': self.config['min_coverage_days'],
                        'timeframes_needed': self.config['timeframes']
                    }
                elif analysis.get('status') == 'INSUFFICIENT':
                    current_days = analysis.get('date_range', [None, None])
                    if current_days[0] and current_days[1]:
                        missing_days = self.config['min_coverage_days'] - (current_days[1] - current_days[0]).days
                        if missing_days > 0:
                            missing_data['symbols_to_download'].append(symbol)
                            missing_data['needs_download'] = True
                            missing_data['total_missing_days'] += missing_days
                            missing_data['details'][symbol] = {
                                'status': 'INSUFFICIENT',
                                'current_days': (current_days[1] - current_days[0]).days,
                                'missing_days': missing_days,
                                'timeframes_needed': self.config['timeframes']
                            }
            
            # Verificar timeframes faltantes
            timeframe_coverage = coverage_analysis.get('summary', {}).get('timeframe_coverage', {})
            for timeframe, coverage in timeframe_coverage.items():
                if not coverage.get('meets_requirement', False):
                    missing_data['timeframes_to_download'].append(timeframe)
                    missing_data['needs_download'] = True
            
            return missing_data
            
        except Exception as e:
            logger.error(f"Error identificando datos faltantes: {e}")
            return {'needs_download': True, 'error': str(e)}
    
    async def _download_missing_data(self, missing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Descarga los datos faltantes identificados usando SQLite"""
        try:
            logger.info("📥 Iniciando descarga de datos faltantes (SQLite)...")
            
            if not missing_data['symbols_to_download']:
                logger.info("No hay símbolos que requieran descarga")
                return {'status': 'no_download_needed', 'total_downloaded': 0}
            
            # Usar la función existente de download_missing_data
            download_results = await download_missing_data(
                symbols=missing_data['symbols_to_download'],
                target_years=self.config['years'],
                timeframes=self.config['timeframes']
            )
            
            # Verificar que los datos se guardaron correctamente en SQLite
            total_downloaded = 0
            symbols_updated = 0
            symbols_new = 0
            
            for symbol in missing_data['symbols_to_download']:
                if symbol in symbol_db_manager.get_all_symbols():
                    if symbol in missing_data.get('existing_symbols', []):
                        symbols_updated += 1
                    else:
                        symbols_new += 1
                    
                    # Contar registros descargados
                    for timeframe in self.config['timeframes']:
                        if timeframe in symbol_db_manager.get_symbol_timeframes(symbol):
                            count = symbol_db_manager.get_record_count(symbol, timeframe)
                            total_downloaded += count
            
            # Si hay timeframes específicos faltantes, descargar también
            if missing_data.get('timeframes_to_download'):
                logger.info(f"Descargando timeframes faltantes: {missing_data['timeframes_to_download']}")
                
                # Usar descarga multi-timeframe para timeframes específicos
                multi_tf_results = await download_multi_timeframe_with_alignment(
                    symbols=missing_data['symbols_to_download'],
                    timeframes=missing_data['timeframes_to_download'],
                    days_back=self.config['min_coverage_days']
                )
                
                # Combinar resultados
                if multi_tf_results.get('success'):
                    download_results['multi_timeframe_results'] = multi_tf_results
                    download_results['total_downloaded'] += multi_tf_results.get('total_records', 0)
            
            return download_results
            
        except Exception as e:
            logger.error(f"Error descargando datos faltantes: {e}")
            return {'status': 'error', 'error': str(e), 'total_downloaded': 0}
    
    async def get_data_status_report(self) -> Dict[str, Any]:
        """Genera un reporte completo del estado de los datos históricos"""
        try:
            logger.info("📊 Generando reporte de estado de datos históricos...")
            
            # Análisis de cobertura
            coverage_analysis = await self._analyze_current_coverage()
            
            # Verificación de integridad
            integrity_results = await verify_data_integrity(self.config['symbols'])
            
            # Estadísticas de base de datos
            db_stats = db_manager.get_database_stats()
            
            # Crear reporte consolidado
            report = {
                'report_date': datetime.now().isoformat(),
                'configuration': {
                    'years_required': self.config['years'],
                    'min_coverage_days': self.config['min_coverage_days'],
                    'symbols_configured': len(self.config['symbols']),
                    'timeframes_configured': len(self.config['timeframes']),
                    'auto_download_enabled': self.config['download_missing']
                },
                'coverage_analysis': coverage_analysis,
                'integrity_verification': integrity_results,
                'database_statistics': db_stats,
                'recommendations': self._generate_recommendations(coverage_analysis, integrity_results)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return {'error': str(e), 'report_date': datetime.now().isoformat()}
    
    def _generate_recommendations(self, coverage_analysis: Dict[str, Any], 
                                integrity_results: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        try:
            # Verificar cobertura general
            summary = coverage_analysis.get('summary', {})
            coverage_pct = summary.get('coverage_percentage', 0)
            
            if coverage_pct < 100:
                recommendations.append(f"⚠️ Cobertura incompleta: {coverage_pct:.1f}% de símbolos tienen datos")
            
            # Verificar problemas de integridad
            critical_issues = integrity_results.get('critical_issues', [])
            if critical_issues:
                recommendations.append(f"🚨 {len(critical_issues)} problemas críticos detectados")
            
            warnings = integrity_results.get('warnings', [])
            if warnings:
                recommendations.append(f"⚠️ {len(warnings)} advertencias de calidad de datos")
            
            # Verificar timeframes
            timeframe_coverage = summary.get('timeframe_coverage', {})
            incomplete_timeframes = [tf for tf, coverage in timeframe_coverage.items() 
                                   if not coverage.get('meets_requirement', False)]
            
            if incomplete_timeframes:
                recommendations.append(f"📊 Timeframes incompletos: {', '.join(incomplete_timeframes)}")
            
            # Recomendación general
            if coverage_pct >= 90 and not critical_issues and not incomplete_timeframes:
                recommendations.append("✅ Calidad de datos excelente - Listo para trading")
            elif coverage_pct >= 70:
                recommendations.append("⚠️ Calidad de datos aceptable - Considerar descargar más datos")
            else:
                recommendations.append("🚨 Calidad de datos insuficiente - Descargar datos históricos requerido")
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            recommendations.append(f"Error generando recomendaciones: {e}")
        
        return recommendations

# Instancia global del gestor
historical_data_manager = HistoricalDataManager()

# Funciones de conveniencia
async def ensure_historical_data_coverage() -> Dict[str, Any]:
    """
    Función principal de conveniencia para asegurar cobertura de datos históricos
    
    Returns:
        Dict con resultados de verificación y descarga
    """
    return await historical_data_manager.ensure_data_coverage()

async def get_historical_data_report() -> Dict[str, Any]:
    """
    Función de conveniencia para obtener reporte de datos históricos
    
    Returns:
        Dict con reporte completo de estado de datos
    """
    return await historical_data_manager.get_data_status_report()

# Función para verificación rápida
async def quick_data_check() -> bool:
    """
    Verificación rápida de cobertura de datos
    
    Returns:
        bool: True si la cobertura es suficiente, False en caso contrario
    """
    try:
        coverage_analysis = await historical_data_manager._analyze_current_coverage()
        summary = coverage_analysis.get('summary', {})
        coverage_pct = summary.get('coverage_percentage', 0)
        
        return coverage_pct >= 90  # 90% de cobertura mínima
        
    except Exception as e:
        logger.error(f"Error en verificación rápida: {e}")
        return False
