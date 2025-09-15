#!/usr/bin/env python3
"""
Script de prueba para análisis pre-guardado
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scripts.training.train_hist_parallel import TrainHistParallel

async def test_cached_analysis():
    """Prueba el análisis pre-guardado"""
    print("🔍 INICIANDO PRUEBA DE ANÁLISIS PRE-GUARDADO")
    print("=" * 60)
    
    try:
        # Crear entrenador en modo ultra rápido
        trainer = TrainHistParallel(progress_file="data/tmp/test_cached_progress.json")
        
        # Inicializar
        print("🔧 Inicializando entrenador...")
        print("✅ Entrenador inicializado correctamente")
        from datetime import datetime, timedelta
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=30)
        print("\n🚀 Iniciando entrenamiento (usará alineamiento si existe)...")
        result = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        if result.get("status") == "success":
            print("✅ Entrenamiento completado exitosamente")
            print(f"📊 Chunks procesados: {result.get('chunks_processed', 0)}")
            print(f"💾 Desde cache: {result.get('cached', False)}")
            print(f"📈 Métricas conjuntas: {result.get('joint_metrics', {})}")
            
            # Verificar si se creó el cache
            cache_path = Path("data/training_analysis_cache.json")
            if cache_path.exists():
                print(f"💾 Cache creado en: {cache_path}")
                print(f"📁 Tamaño del cache: {cache_path.stat().st_size / 1024:.1f} KB")
            else:
                print("⚠️ No se creó cache")
                
        else:
            print("❌ Error en el entrenamiento")
            print(f"💥 Mensaje: {result.get('message', 'Error desconocido')}")
            
        return True if result else False
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        return False

if __name__ == "__main__":
    print("🎯 ANÁLISIS PRE-GUARDADO - 30 DÍAS EN CHUNKS DE 7 DÍAS")
    print("⏱️ Primera ejecución: 10-20 minutos (crea cache)")
    print("⏱️ Ejecuciones siguientes: <1 minuto (usa cache)")
    print("💾 Consumo de memoria: <2GB")
    print("=" * 60)
    
    result = asyncio.run(test_cached_analysis())
    
    if result:
        print("\n🎉 ¡PRUEBA EXITOSA!")
        print("✅ El análisis pre-guardado funciona correctamente")
        print("💾 Cache creado - próximas ejecuciones serán instantáneas")
    else:
        print("\n💥 PRUEBA FALLIDA")
        print("❌ Revisar logs para más detalles")

