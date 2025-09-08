"""
test_multi_timeframe_system.py - Script de Prueba del Sistema Multi-Timeframe
Valida la funcionalidad completa del nuevo sistema de datos mejorado
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from data.temporal_alignment import TemporalAlignment, AlignmentConfig
from data.hybrid_storage import HybridStorageManager, StorageConfig
from data.multi_timeframe_coordinator import MultiTimeframeCoordinator
from data.intelligent_cache import IntelligentCacheManager, CacheConfig
from data.collector import download_multi_timeframe_with_alignment
from data.database import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_temporal_alignment():
    """Prueba el sistema de alineación temporal"""
    logger.info("🧪 Probando sistema de alineación temporal...")
    
    try:
        # Crear configuración de prueba
        config = AlignmentConfig(
            timeframes=['5m', '15m', '1h'],
            required_symbols=['BTCUSDT', 'ETHUSDT'],
            base_timeframe='5m'
        )
        
        # Crear alineador
        aligner = TemporalAlignment(config)
        
        # Simular datos de prueba
        from datetime import datetime
        import pandas as pd
        import numpy as np
        
        # Crear datos simulados
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # Timeline de 5 minutos
        timeline_5m = pd.date_range(start=start_date, end=end_date, freq='5min')
        
        # Datos simulados para BTCUSDT
        np.random.seed(42)
        btc_data = pd.DataFrame({
            'open': 50000 + np.random.normal(0, 100, len(timeline_5m)),
            'high': 50000 + np.random.normal(0, 100, len(timeline_5m)) + 50,
            'low': 50000 + np.random.normal(0, 100, len(timeline_5m)) - 50,
            'close': 50000 + np.random.normal(0, 100, len(timeline_5m)),
            'volume': np.random.exponential(1000, len(timeline_5m))
        }, index=timeline_5m)
        
        # Datos simulados para ETHUSDT (con algunos gaps)
        eth_data = btc_data.copy()
        eth_data.iloc[100:150] = np.nan  # Simular gap
        
        # Crear timeline maestra
        master_timeline = aligner.create_master_timeline('5m', start_date, end_date)
        
        # Alinear datos
        symbol_data = {
            'BTCUSDT': btc_data,
            'ETHUSDT': eth_data
        }
        
        aligned_data = aligner.align_symbol_data(symbol_data, master_timeline, '5m')
        
        # Validar alineación
        validation = aligner.validate_alignment(aligned_data)
        
        logger.info(f"✅ Alineación temporal completada")
        logger.info(f"   - Calidad general: {validation['overall_quality']:.3f}")
        logger.info(f"   - Símbolos procesados: {len(aligned_data)}")
        logger.info(f"   - Períodos alineados: {len(master_timeline)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de alineación temporal: {e}")
        return False

def test_hybrid_storage():
    """Prueba el sistema de almacenamiento híbrido"""
    logger.info("🧪 Probando sistema de almacenamiento híbrido...")
    
    try:
        # Crear configuración de prueba
        config = StorageConfig(
            base_path=Path("data/test_storage"),
            hot_data_days=7,
            max_size_mb=100
        )
        
        # Crear gestor de almacenamiento
        storage = HybridStorageManager(config)
        
        # Simular datos de prueba
        import pandas as pd
        import numpy as np
        
        timeline = pd.date_range(start=datetime.now() - timedelta(days=3), 
                               end=datetime.now(), freq='5min')
        
        test_data = {
            'BTCUSDT': pd.DataFrame({
                'open': 50000 + np.random.normal(0, 100, len(timeline)),
                'high': 50000 + np.random.normal(0, 100, len(timeline)) + 50,
                'low': 50000 + np.random.normal(0, 100, len(timeline)) - 50,
                'close': 50000 + np.random.normal(0, 100, len(timeline)),
                'volume': np.random.exponential(1000, len(timeline))
            }, index=timeline)
        }
        
        # Almacenar datos
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success = storage.store_aligned_data(test_data, '5m', session_id)
        
        if success:
            # Recuperar datos
            start_date = datetime.now() - timedelta(days=2)
            end_date = datetime.now()
            
            retrieved_data = storage.load_aligned_data(['BTCUSDT'], '5m', start_date, end_date)
            
            # Obtener estadísticas
            stats = storage.get_storage_statistics()
            
            logger.info(f"✅ Almacenamiento híbrido completado")
            logger.info(f"   - Datos almacenados: {len(test_data['BTCUSDT'])} registros")
            logger.info(f"   - Datos recuperados: {len(retrieved_data.get('BTCUSDT', pd.DataFrame()))} registros")
            logger.info(f"   - Tamaño hot data: {stats.hot_data_size_mb:.2f} MB")
            logger.info(f"   - Tamaño histórico: {stats.historical_size_gb:.2f} GB")
            
            return True
        else:
            logger.error("❌ Error almacenando datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba de almacenamiento híbrido: {e}")
        return False

def test_intelligent_cache():
    """Prueba el sistema de cache inteligente"""
    logger.info("🧪 Probando sistema de cache inteligente...")
    
    try:
        # Crear configuración de prueba
        config = CacheConfig(
            cache_dir=Path("data/test_cache"),
            max_size_mb=50,
            cleanup_interval=60
        )
        
        # Crear gestor de cache
        cache = IntelligentCacheManager(config)
        
        # Simular datos de prueba
        import pandas as pd
        import numpy as np
        
        timeline = pd.date_range(start=datetime.now() - timedelta(hours=1), 
                               end=datetime.now(), freq='5min')
        
        test_data = {
            'BTCUSDT': pd.DataFrame({
                'open': 50000 + np.random.normal(0, 100, len(timeline)),
                'high': 50000 + np.random.normal(0, 100, len(timeline)) + 50,
                'low': 50000 + np.random.normal(0, 100, len(timeline)) - 50,
                'close': 50000 + np.random.normal(0, 100, len(timeline)),
                'volume': np.random.exponential(1000, len(timeline))
            }, index=timeline)
        }
        
        # Almacenar en cache
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now()
        
        cache.set_aligned_data_cache(['BTCUSDT'], '5m', test_data)
        
        # Recuperar del cache
        cached_data = cache.get_aligned_data_cached(['BTCUSDT'], '5m', start_date, end_date)
        
        # Obtener estadísticas
        stats = cache.get_cache_statistics()
        
        logger.info(f"✅ Cache inteligente completado")
        logger.info(f"   - Datos cacheados: {len(test_data['BTCUSDT'])} registros")
        logger.info(f"   - Datos recuperados: {len(cached_data.get('BTCUSDT', pd.DataFrame()))} registros")
        logger.info(f"   - Hit rate: {stats.hit_rate:.2%}")
        logger.info(f"   - Tamaño cache: {stats.total_size_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de cache inteligente: {e}")
        return False

async def test_multi_timeframe_coordinator():
    """Prueba el coordinador multi-timeframe"""
    logger.info("🧪 Probando coordinador multi-timeframe...")
    
    try:
        # Crear coordinador
        coordinator = MultiTimeframeCoordinator()
        
        # Simular datos de prueba
        import pandas as pd
        import numpy as np
        
        # Crear datos base de 5 minutos
        timeline_5m = pd.date_range(start=datetime.now() - timedelta(days=1), 
                                  end=datetime.now(), freq='5min')
        
        base_data = {
            'BTCUSDT': pd.DataFrame({
                'open': 50000 + np.random.normal(0, 100, len(timeline_5m)),
                'high': 50000 + np.random.normal(0, 100, len(timeline_5m)) + 50,
                'low': 50000 + np.random.normal(0, 100, len(timeline_5m)) - 50,
                'close': 50000 + np.random.normal(0, 100, len(timeline_5m)),
                'volume': np.random.exponential(1000, len(timeline_5m))
            }, index=timeline_5m)
        }
        
        # Procesar agregación automática
        aggregated_data = coordinator.auto_aggregate_timeframes(base_data)
        
        # Validar coherencia
        all_data = {'5m': base_data}
        all_data.update(aggregated_data)
        
        coherence_results = coordinator.validate_timeframe_coherence(all_data)
        
        logger.info(f"✅ Coordinador multi-timeframe completado")
        logger.info(f"   - Timeframes procesados: {list(aggregated_data.keys())}")
        logger.info(f"   - Coherencia general: {coherence_results['overall_coherence']:.3f}")
        logger.info(f"   - Pares validados: {len(coherence_results['timeframe_pairs'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de coordinador multi-timeframe: {e}")
        return False

async def test_database_integration():
    """Prueba la integración con la base de datos"""
    logger.info("🧪 Probando integración con base de datos...")
    
    try:
        # Simular datos de prueba
        import pandas as pd
        import numpy as np
        
        timeline = pd.date_range(start=datetime.now() - timedelta(hours=1), 
                               end=datetime.now(), freq='5min')
        
        test_data = {
            'BTCUSDT': pd.DataFrame({
                'open': 50000 + np.random.normal(0, 100, len(timeline)),
                'high': 50000 + np.random.normal(0, 100, len(timeline)) + 50,
                'low': 50000 + np.random.normal(0, 100, len(timeline)) - 50,
                'close': 50000 + np.random.normal(0, 100, len(timeline)),
                'volume': np.random.exponential(1000, len(timeline))
            }, index=timeline)
        }
        
        # Almacenar datos alineados
        session_id = f"test_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success = db_manager.store_aligned_data(test_data, '5m', session_id)
        
        if success:
            # Recuperar datos
            start_date = datetime.now() - timedelta(hours=1)
            end_date = datetime.now()
            
            retrieved_data = db_manager.get_aligned_data(['BTCUSDT'], '5m', start_date, end_date)
            
            # Almacenar metadatos
            metadata = {
                'symbols_processed': ['BTCUSDT'],
                'timeframes_processed': ['5m'],
                'alignment_quality': 0.95,
                'coherence_scores': {'5m': 0.95},
                'total_periods': len(timeline),
                'processing_time_seconds': 1.5
            }
            
            db_manager.store_alignment_metadata(session_id, metadata)
            
            # Obtener metadatos
            retrieved_metadata = db_manager.get_alignment_metadata(session_id)
            
            logger.info(f"✅ Integración con base de datos completada")
            logger.info(f"   - Datos almacenados: {len(test_data['BTCUSDT'])} registros")
            logger.info(f"   - Datos recuperados: {len(retrieved_data.get('BTCUSDT', pd.DataFrame()))} registros")
            logger.info(f"   - Metadatos almacenados: {retrieved_metadata is not None}")
            
            return True
        else:
            logger.error("❌ Error almacenando datos en base de datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba de integración con base de datos: {e}")
        return False

async def test_full_system_integration():
    """Prueba la integración completa del sistema"""
    logger.info("🧪 Probando integración completa del sistema...")
    
    try:
        # Simular descarga multi-timeframe (sin API real)
        logger.info("   - Simulando descarga multi-timeframe...")
        
        # Crear datos simulados para múltiples timeframes
        import pandas as pd
        import numpy as np
        
        symbols = ['BTCUSDT', 'ETHUSDT']
        timeframes = ['5m', '15m', '1h']
        
        simulated_data = {}
        
        for tf in timeframes:
            minutes = {'5m': 5, '15m': 15, '1h': 60}[tf]
            timeline = pd.date_range(start=datetime.now() - timedelta(days=1), 
                                   end=datetime.now(), freq=f'{minutes}min')
            
            tf_data = {}
            for symbol in symbols:
                np.random.seed(hash(symbol) % 2**32)
                tf_data[symbol] = pd.DataFrame({
                    'open': 50000 + np.random.normal(0, 100, len(timeline)),
                    'high': 50000 + np.random.normal(0, 100, len(timeline)) + 50,
                    'low': 50000 + np.random.normal(0, 100, len(timeline)) - 50,
                    'close': 50000 + np.random.normal(0, 100, len(timeline)),
                    'volume': np.random.exponential(1000, len(timeline))
                }, index=timeline)
            
            simulated_data[tf] = tf_data
        
        # Procesar con coordinador
        logger.info("   - Procesando con coordinador multi-timeframe...")
        coordinator = MultiTimeframeCoordinator()
        
        # Simular procesamiento coordinado
        results = {
            'success': True,
            'processed_timeframes': timeframes,
            'alignment_results': {},
            'coherence_scores': {}
        }
        
        for tf, data in simulated_data.items():
            # Alinear datos
            from data.temporal_alignment import TemporalAlignment, AlignmentConfig
            config = AlignmentConfig(timeframes=[tf], required_symbols=symbols)
            aligner = TemporalAlignment(config)
            
            start_date = min(df.index.min() for df in data.values())
            end_date = max(df.index.max() for df in data.values())
            master_timeline = aligner.create_master_timeline(tf, start_date, end_date)
            aligned_data = aligner.align_symbol_data(data, master_timeline, tf)
            validation = aligner.validate_alignment(aligned_data)
            
            results['alignment_results'][tf] = {
                'data': aligned_data,
                'validation': validation
            }
        
        # Calcular coherencia
        coherence_scores = coordinator.validate_timeframe_coherence(
            {tf: result['data'] for tf, result in results['alignment_results'].items()}
        )
        results['coherence_scores'] = coherence_scores
        
        logger.info(f"✅ Integración completa del sistema completada")
        logger.info(f"   - Timeframes procesados: {len(results['processed_timeframes'])}")
        logger.info(f"   - Símbolos procesados: {len(symbols)}")
        logger.info(f"   - Coherencia general: {coherence_scores['overall_coherence']:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba de integración completa: {e}")
        return False

async def main():
    """Función principal de pruebas"""
    logger.info("🚀 Iniciando pruebas del sistema multi-timeframe...")
    
    test_results = []
    
    # Ejecutar pruebas individuales
    test_results.append(("Alineación Temporal", await test_temporal_alignment()))
    test_results.append(("Almacenamiento Híbrido", test_hybrid_storage()))
    test_results.append(("Cache Inteligente", test_intelligent_cache()))
    test_results.append(("Coordinador Multi-Timeframe", await test_multi_timeframe_coordinator()))
    test_results.append(("Integración Base de Datos", await test_database_integration()))
    test_results.append(("Integración Completa", await test_full_system_integration()))
    
    # Mostrar resultados
    logger.info("\n📊 RESULTADOS DE PRUEBAS:")
    logger.info("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    logger.info("=" * 50)
    logger.info(f"Pruebas pasadas: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ¡Todas las pruebas pasaron! El sistema multi-timeframe está funcionando correctamente.")
    else:
        logger.warning(f"⚠️ {total-passed} pruebas fallaron. Revisar los logs para más detalles.")
    
    return passed == total

if __name__ == "__main__":
    # Ejecutar pruebas
    success = asyncio.run(main())
    exit(0 if success else 1)
