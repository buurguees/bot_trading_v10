#!/usr/bin/env python3
"""
Script de prueba para análisis pre-guardado
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scripts.training.train_historical import TrainHistoricalEnterprise

async def test_cached_analysis():
    """Prueba el análisis pre-guardado"""
    print("🔍 INICIANDO PRUEBA DE ANÁLISIS PRE-GUARDADO")
    print("=" * 60)
    
    try:
        # Crear entrenador en modo ultra rápido
        trainer = TrainHistoricalEnterprise(
            progress_id="test_cached",
            training_mode="ultra_fast"
        )
        
        # Inicializar
        print("🔧 Inicializando entrenador...")
        success = await trainer.initialize()
        
        if not success:
            print("❌ Error en inicialización")
            return False
        
        print("✅ Entrenador inicializado correctamente")
        print(f"📅 Período de datos: {trainer.training_config.get('data_period_days', 30)} días")
        print(f"🔄 Entrenamiento incremental: {trainer.training_config.get('incremental_training', False)}")
        print(f"📦 Tamaño de chunk: {trainer.training_config.get('chunk_size_days', 7)} días")
        
        # Ejecutar entrenamiento (usará cache si existe)
        print("\n🚀 Iniciando entrenamiento (usará cache si existe)...")
        result = await trainer.execute()
        
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
            
        return result.get("status") == "success"
        
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

