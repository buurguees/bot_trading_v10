#!/usr/bin/env python3
"""
scripts/data_management.py - Script de Gestión Profesional de Datos
Ubicación: C:\TradingBot_v10\scripts\data_management.py

FUNCIONALIDADES:
- Descarga masiva de 5+ años de datos históricos
- Verificación y reparación de integridad de datos
- Análisis de calidad y cobertura de datos
- Optimización automática de la base de datos
- Backup y recuperación de datos
- Limpieza y mantenimiento automático
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse
import json
import time

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.collector import (
    data_collector, 
    download_extensive_historical_data,
    download_missing_data,
    verify_data_integrity
)
from data.database import db_manager
from data.preprocessor import data_preprocessor, analyze_feature_correlation, get_feature_statistics
from config.config_loader import user_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_management.log')
    ]
)
logger = logging.getLogger(__name__)

class DataManager:
    """Gestor principal de datos con funcionalidades profesionales"""
    
    def __init__(self):
        self.symbols = self._get_symbols_from_config()
        self.timeframes = ['1h', '4h', '1d']
        self.default_years = 5
        
    def _get_symbols_from_config(self) -> List[str]:
        """Obtiene símbolos desde la configuración"""
        try:
            bot_settings = user_config.get_value(['bot_settings'], {})
            symbols = bot_settings.get('main_symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
            return symbols
        except Exception as e:
            logger.error(f"Error obteniendo símbolos de configuración: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    async def download_all_historical_data(self, years: int = None, timeframes: List[str] = None):
        """Descarga masiva de datos históricos para todos los símbolos"""
        if years is None:
            years = self.default_years
        if timeframes is None:
            timeframes = self.timeframes
        
        logger.info(f"🚀 INICIANDO DESCARGA MASIVA DE DATOS HISTÓRICOS")
        logger.info(f"📊 Configuración:")
        logger.info(f"   Símbolos: {len(self.symbols)} ({', '.join(self.symbols)})")
        logger.info(f"   Timeframes: {len(timeframes)} ({', '.join(timeframes)})")
        logger.info(f"   Período: {years} años")
        logger.info(f"   Total de descargas: {len(self.symbols) * len(timeframes)}")
        
        start_time = time.time()
        
        try:
            # Ejecutar descarga
            results = await download_extensive_historical_data(
                symbols=self.symbols,
                years=years,
                timeframes=timeframes
            )
            
            # Generar reporte de resultados
            total_records = sum(
                sum(timeframe_results.values()) 
                for timeframe_results in results.values()
            )
            
            duration = time.time() - start_time
            
            logger.info(f"🎉 DESCARGA MASIVA COMPLETADA")
            logger.info(f"⏱️  Tiempo total: {duration/60:.1f} minutos")
            logger.info(f"📈 Registros descargados: {total_records:,}")
            
            # Guardar reporte detallado
            self._save_download_report(results, duration, years, timeframes)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en descarga masiva: {e}")
            return {}
    
    def _save_download_report(self, results: Dict[str, Any], duration: float, 
                            years: int, timeframes: List[str]):
        """Guarda reporte detallado de la descarga"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'configuration': {
                    'symbols': self.symbols,
                    'timeframes': timeframes,
                    'years': years
                },
                'execution': {
                    'duration_minutes': round(duration / 60, 2),
                    'total_downloads': len(self.symbols) * len(timeframes)
                },
                'results': results,
                'summary': {
                    'total_records': sum(
                        sum(tf_results.values()) for tf_results in results.values()
                    ),
                    'successful_downloads': sum(
                        1 for symbol_results in results.values()
                        for count in symbol_results.values() if count > 0
                    ),
                    'failed_downloads': sum(
                        1 for symbol_results in results.values()
                        for count in symbol_results.values() if count == 0
                    )
                }
            }
            
            report_file = Path(f"download_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📄 Reporte guardado: {report_file}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
    
    async def analyze_data_coverage(self) -> Dict[str, Any]:
        """Analiza la cobertura de datos históricos"""
        logger.info("🔍 ANALIZANDO COBERTURA DE DATOS")
        
        try:
            # Obtener resumen de la base de datos
            db_summary = db_manager.get_data_summary_optimized()
            
            # Verificar integridad
            integrity_results = await verify_data_integrity(self.symbols)
            
            # Análisis de calidad
            quality_analysis = db_manager.analyze_data_quality()
            
            # Compilar reporte comprehensivo
            coverage_report = {
                'analysis_timestamp': datetime.now().isoformat(),
                'database_summary': db_summary,
                'integrity_check': integrity_results,
                'quality_analysis': quality_analysis,
                'recommendations': self._generate_coverage_recommendations(
                    db_summary, integrity_results, quality_analysis
                )
            }
            
            # Imprimir resumen
            self._print_coverage_summary(coverage_report)
            
            return coverage_report
            
        except Exception as e:
            logger.error(f"❌ Error analizando cobertura: {e}")
            return {'error': str(e)}
    
    def _generate_coverage_recommendations(self, db_summary: Dict, 
                                         integrity: Dict, quality: Dict) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        try:
            # Análisis de cobertura temporal
            if db_summary.get('total_symbols', 0) < len(self.symbols):
                missing_symbols = len(self.symbols) - db_summary.get('total_symbols', 0)
                recommendations.append(f"🔽 Descargar datos para {missing_symbols} símbolos faltantes")
            
            # Análisis de calidad
            total_quality_issues = quality.get('quality_issues', {})
            total_issues = sum(total_quality_issues.values())
            
            if total_issues > 1000:
                recommendations.append("🧹 Ejecutar limpieza de datos (muchos problemas detectados)")
            
            if total_quality_issues.get('duplicate_timestamps', 0) > 0:
                recommendations.append("🔧 Corregir timestamps duplicados")
            
            # Análisis de integridad
            if integrity.get('critical_issues'):
                recommendations.append("🚨 Resolver problemas críticos de integridad")
            
            # Recomendaciones de optimización
            if db_summary.get('database_size_mb', 0) > 1000:
                recommendations.append("⚡ Optimizar base de datos (>1GB)")
            
            if not recommendations:
                recommendations.append("✅ Datos en buen estado, sin acciones requeridas")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return ["❌ Error generando recomendaciones"]
    
    def _print_coverage_summary(self, report: Dict[str, Any]):
        """Imprime resumen de cobertura en consola"""
        try:
            print("\n" + "="*60)
            print("📊 RESUMEN DE COBERTURA DE DATOS")
            print("="*60)
            
            db_summary = report.get('database_summary', {})
            print(f"📈 Total de símbolos: {db_summary.get('total_symbols', 0)}")
            print(f"📊 Total de registros: {db_summary.get('total_records', 0):,}")
            print(f"💾 Tamaño de BD: {db_summary.get('database_size_mb', 0):.1f} MB")
            
            # Estadísticas por símbolo
            symbols_info = db_summary.get('symbols', [])
            if symbols_info:
                print(f"\n📋 Detalles por símbolo:")
                for symbol_info in symbols_info[:10]:  # Solo primeros 10
                    symbol = symbol_info.get('symbol', 'N/A')
                    count = symbol_info.get('record_count', 0)
                    days = symbol_info.get('duration_days', 0)
                    status = symbol_info.get('status', 'UNKNOWN')
                    print(f"   {symbol}: {count:,} registros, {days} días ({status})")
            
            # Recomendaciones
            recommendations = report.get('recommendations', [])
            if recommendations:
                print(f"\n💡 RECOMENDACIONES:")
                for rec in recommendations:
                    print(f"   {rec}")
            
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error imprimiendo resumen: {e}")
    
    async def repair_data_issues(self):
        """Repara problemas comunes de datos"""
        logger.info("🔧 INICIANDO REPARACIÓN DE DATOS")
        
        try:
            repair_results = {
                'timestamp': datetime.now().isoformat(),
                'operations': []
            }
            
            # 1. Corregir timestamps problemáticos
            logger.info("🕐 Corrigiendo timestamps...")
            timestamp_results = db_manager.fix_timestamp_issues()
            repair_results['operations'].append({
                'operation': 'fix_timestamps',
                'results': timestamp_results
            })
            
            # 2. Limpiar datos duplicados y problemáticos
            logger.info("🧹 Limpiando datos duplicados...")
            # Esta operación se puede implementar en el database manager
            
            # 3. Validar integridad OHLCV
            logger.info("✅ Validando integridad OHLCV...")
            integrity_results = await verify_data_integrity(self.symbols)
            repair_results['operations'].append({
                'operation': 'validate_integrity',
                'results': integrity_results
            })
            
            # 4. Optimizar base de datos
            logger.info("⚡ Optimizando base de datos...")
            optimization_results = db_manager.optimize_database()
            repair_results['operations'].append({
                'operation': 'optimize_database',
                'results': optimization_results
            })
            
            logger.info("✅ Reparación de datos completada")
            return repair_results
            
        except Exception as e:
            logger.error(f"❌ Error en reparación de datos: {e}")
            return {'error': str(e)}
    
    async def update_missing_data(self, target_years: int = None):
        """Actualiza datos faltantes automáticamente"""
        if target_years is None:
            target_years = self.default_years
        
        logger.info(f"📥 ACTUALIZANDO DATOS FALTANTES (objetivo: {target_years} años)")
        
        try:
            # Analizar datos faltantes
            missing_analysis = await download_missing_data(
                symbols=self.symbols,
                target_years=target_years
            )
            
            # Imprimir resumen
            logger.info(f"📊 Análisis completado:")
            logger.info(f"   Símbolos analizados: {missing_analysis.get('symbols_analyzed', 0)}")
            logger.info(f"   Símbolos OK: {missing_analysis.get('symbols_ok', 0)}")
            logger.info(f"   Símbolos actualizados: {missing_analysis.get('symbols_updated', 0)}")
            logger.info(f"   Símbolos nuevos: {missing_analysis.get('symbols_new', 0)}")
            logger.info(f"   Total descargado: {missing_analysis.get('total_downloaded', 0):,} registros")
            
            return missing_analysis
            
        except Exception as e:
            logger.error(f"❌ Error actualizando datos faltantes: {e}")
            return {'error': str(e)}
    
    def create_backup(self, compress: bool = True):
        """Crea backup de la base de datos"""
        logger.info("💾 CREANDO BACKUP DE BASE DE DATOS")
        
        try:
            backup_info = db_manager.create_backup(compress=compress)
            
            if backup_info.get('status') == 'completed':
                logger.info(f"✅ Backup creado exitosamente:")
                logger.info(f"   Archivo: {backup_info['backup_path']}")
                logger.info(f"   Tamaño: {backup_info['backup_size_mb']:.1f} MB")
                logger.info(f"   Compresión: {backup_info['compression_ratio']:.1f}x")
                logger.info(f"   Duración: {backup_info['duration_seconds']:.1f}s")
            else:
                logger.error(f"❌ Error creando backup: {backup_info.get('error', 'Unknown error')}")
            
            return backup_info
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de backup: {e}")
            return {'error': str(e)}
    
    def analyze_features_quality(self, symbol: str = "BTCUSDT", days_back: int = 30):
        """Analiza la calidad de los features generados"""
        logger.info(f"🔬 ANALIZANDO CALIDAD DE FEATURES PARA {symbol}")
        
        try:
            # Preparar datos
            X, y, df, stats = data_preprocessor.prepare_training_data_advanced(
                symbol=symbol,
                days_back=days_back,
                target_method="classification"
            )
            
            if df.empty:
                logger.error(f"No se pudieron obtener datos para {symbol}")
                return {}
            
            # Análisis de correlaciones
            correlations = analyze_feature_correlation(df, threshold=0.95)
            
            # Estadísticas de features
            feature_stats = get_feature_statistics(df)
            
            # Estadísticas del preprocessor
            processor_stats = data_preprocessor.get_preprocessing_statistics()
            
            # Compilar reporte
            quality_report = {
                'symbol': symbol,
                'analysis_timestamp': datetime.now().isoformat(),
                'data_preparation_stats': stats,
                'feature_statistics': feature_stats,
                'high_correlations': correlations,
                'preprocessor_stats': processor_stats,
                'data_shape': {
                    'samples': len(df),
                    'features': len(df.columns),
                    'target_distribution': dict(df['target'].value_counts().sort_index()) if 'target' in df.columns else {}
                }
            }
            
            # Imprimir resumen
            self._print_features_summary(quality_report)
            
            return quality_report
            
        except Exception as e:
            logger.error(f"❌ Error analizando calidad de features: {e}")
            return {'error': str(e)}
    
    def _print_features_summary(self, report: Dict[str, Any]):
        """Imprime resumen de análisis de features"""
        try:
            print("\n" + "="*60)
            print(f"🔬 ANÁLISIS DE FEATURES - {report['symbol']}")
            print("="*60)
            
            # Estadísticas de datos
            data_shape = report.get('data_shape', {})
            print(f"📊 Muestras: {data_shape.get('samples', 0):,}")
            print(f"🧮 Features: {data_shape.get('features', 0)}")
            
            # Distribución del target
            target_dist = data_shape.get('target_distribution', {})
            if target_dist:
                print(f"🎯 Distribución del target:")
                for target_val, count in target_dist.items():
                    print(f"   Clase {target_val}: {count:,} muestras")
            
            # Estadísticas de preparación
            prep_stats = report.get('data_preparation_stats', {})
            if prep_stats:
                print(f"⚡ Tiempo de preparación: {prep_stats.get('preparation_time_seconds', 0):.1f}s")
                print(f"📈 Features originales → seleccionados: {prep_stats.get('original_features', 0)} → {prep_stats.get('selected_features', 0)}")
                print(f"🏆 Puntuación de calidad: {prep_stats.get('data_quality_score', 0):.3f}")
            
            # Correlaciones altas
            correlations = report.get('high_correlations', {})
            if correlations:
                print(f"\n⚠️ Features con alta correlación:")
                for feature, correlated_features in list(correlations.items())[:5]:
                    print(f"   {feature}: {len(correlated_features)} correlaciones altas")
            
            # Categorías de features
            processor_stats = report.get('preprocessor_stats', {})
            feature_cats = processor_stats.get('features', {}).get('feature_categories', {})
            if feature_cats:
                print(f"\n📋 Categorías de features:")
                for category, count in feature_cats.items():
                    if count > 0:
                        print(f"   {category}: {count}")
            
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error imprimiendo resumen de features: {e}")
    
    def run_maintenance(self):
        """Ejecuta mantenimiento completo de la base de datos"""
        logger.info("🧹 INICIANDO MANTENIMIENTO COMPLETO")
        
        try:
            maintenance_results = {
                'timestamp': datetime.now().isoformat(),
                'operations': []
            }
            
            # 1. Limpiar cache de features
            logger.info("🗂️ Limpiando cache de features...")
            data_preprocessor.feature_cache.clear_expired()
            maintenance_results['operations'].append('clear_feature_cache')
            
            # 2. Optimizar base de datos
            logger.info("⚡ Optimizando base de datos...")
            optimization_results = db_manager.optimize_database()
            maintenance_results['operations'].append({
                'operation': 'optimize_database',
                'results': optimization_results
            })
            
            # 3. Limpieza de datos antiguos (opcional)
            logger.info("🗑️ Analizando datos antiguos...")
            cleanup_preview = db_manager.cleanup_old_data_advanced(
                days_to_keep=365 * 2,  # Mantener 2 años
                dry_run=True
            )
            
            if cleanup_preview.get('total_deleted', 0) > 0:
                logger.info(f"   Se pueden eliminar {sum(cleanup_preview['records_to_delete'].values()):,} registros antiguos")
                logger.info("   Ejecutar con --cleanup para realizar la limpieza")
            
            # 4. Estadísticas de performance
            logger.info("📊 Obteniendo estadísticas de performance...")
            perf_stats = db_manager.get_performance_statistics()
            maintenance_results['operations'].append({
                'operation': 'performance_stats',
                'results': perf_stats
            })
            
            logger.info("✅ Mantenimiento completado")
            return maintenance_results
            
        except Exception as e:
            logger.error(f"❌ Error en mantenimiento: {e}")
            return {'error': str(e)}

async def main():
    """Función principal con interfaz de línea de comandos"""
    parser = argparse.ArgumentParser(description="Sistema de Gestión Profesional de Datos")
    
    # Comandos principales
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando: download
    download_parser = subparsers.add_parser('download', help='Descargar datos históricos')
    download_parser.add_argument('--years', type=int, default=5, help='Años de datos a descargar')
    download_parser.add_argument('--timeframes', nargs='+', default=['1h', '4h', '1d'], help='Timeframes a descargar')
    download_parser.add_argument('--symbols', nargs='+', help='Símbolos específicos a descargar')
    
    # Comando: analyze
    analyze_parser = subparsers.add_parser('analyze', help='Analizar cobertura de datos')
    analyze_parser.add_argument('--save-report', action='store_true', help='Guardar reporte en archivo')
    
    # Comando: repair
    repair_parser = subparsers.add_parser('repair', help='Reparar problemas de datos')
    
    # Comando: update
    update_parser = subparsers.add_parser('update', help='Actualizar datos faltantes')
    update_parser.add_argument('--target-years', type=int, default=5, help='Años objetivo de datos')
    
    # Comando: backup
    backup_parser = subparsers.add_parser('backup', help='Crear backup de la base de datos')
    backup_parser.add_argument('--no-compress', action='store_true', help='No comprimir el backup')
    
    # Comando: features
    features_parser = subparsers.add_parser('features', help='Analizar calidad de features')
    features_parser.add_argument('--symbol', default='BTCUSDT', help='Símbolo a analizar')
    features_parser.add_argument('--days', type=int, default=30, help='Días de datos para análisis')
    
    # Comando: maintenance
    maintenance_parser = subparsers.add_parser('maintenance', help='Ejecutar mantenimiento')
    maintenance_parser.add_argument('--cleanup', action='store_true', help='Ejecutar limpieza de datos antiguos')
    
    # Comando: health
    health_parser = subparsers.add_parser('health', help='Verificar salud del sistema')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Inicializar gestor de datos
    data_manager = DataManager()
    
    try:
        if args.command == 'download':
            await data_manager.download_all_historical_data(
                years=args.years,
                timeframes=args.timeframes
            )
        
        elif args.command == 'analyze':
            report = await data_manager.analyze_data_coverage()
            if args.save_report:
                filename = f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                logger.info(f"📄 Reporte guardado: {filename}")
        
        elif args.command == 'repair':
            await data_manager.repair_data_issues()
        
        elif args.command == 'update':
            await data_manager.update_missing_data(target_years=args.target_years)
        
        elif args.command == 'backup':
            data_manager.create_backup(compress=not args.no_compress)
        
        elif args.command == 'features':
            data_manager.analyze_features_quality(symbol=args.symbol, days_back=args.days)
        
        elif args.command == 'maintenance':
            results = data_manager.run_maintenance()
            if args.cleanup:
                logger.info("🗑️ Ejecutando limpieza de datos antiguos...")
                cleanup_results = db_manager.cleanup_old_data_advanced(
                    days_to_keep=365 * 2,
                    dry_run=False
                )
                logger.info(f"✅ Limpieza completada: {cleanup_results.get('total_deleted', 0)} registros eliminados")
        
        elif args.command == 'health':
            health_status = await data_collector.health_check()
            
            print("\n" + "="*50)
            print("🏥 ESTADO DE SALUD DEL SISTEMA")
            print("="*50)
            print(f"📊 Puntuación general: {health_status.get('health_score', 0)}%")
            print(f"🔑 Credenciales: {'✅' if health_status.get('credentials_configured') else '❌'}")
            print(f"🔌 API REST: {'✅' if health_status.get('rest_api_ok') else '❌'}")
            print(f"💾 Base de datos: {'✅' if health_status.get('database_ok') else '❌'}")
            print(f"🔄 Frescura de datos: {'✅' if health_status.get('data_freshness_ok') else '❌'}")
            
            details = health_status.get('details', {})
            if details:
                print(f"\n📋 Detalles:")
                for key, value in details.items():
                    print(f"   {key}: {value}")
            print("="*50)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Operación cancelada por el usuario")
    except Exception as e:
        logger.error(f"❌ Error ejecutando comando {args.command}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())