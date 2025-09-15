#!/usr/bin/env python3
"""
Script de prueba para entrenamiento incremental
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scripts.training.train_historical import TrainHistoricalEnterprise

async def test_incremental_training():
    """Prueba el entrenamiento incremental"""
    print("🔄 INICIANDO PRUEBA DE ENTRENAMIENTO INCREMENTAL")
    print("=" * 60)
    
    try:
        # Crear entrenador en modo ultra rápido con entrenamiento incremental
        trainer = TrainHistoricalEnterprise(
            progress_id="test_incremental",
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
        print(f"💾 Límite de memoria: {trainer.training_config.get('max_memory_mb', 2048)} MB")
        print(f"🤖 Símbolos: {len(trainer.symbols)}")
        print(f"⏰ Timeframes: {len(trainer.timeframes)}")
        
        # Ejecutar entrenamiento
        print("\n🚀 Iniciando entrenamiento incremental...")
        result = await trainer.execute()
        
        if result.get("status") == "success":
            print("✅ Entrenamiento incremental completado exitosamente")
            print(f"📊 Chunks procesados: {result.get('chunks_processed', 0)}")
            print(f"📈 Métricas conjuntas: {result.get('joint_metrics', {})}")
            print(f"📊 Resultados guardados en: {trainer.agents_dir}")
        else:
            print("❌ Error en el entrenamiento")
            print(f"💥 Mensaje: {result.get('message', 'Error desconocido')}")
            
        return result.get("status") == "success"
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        return False

if __name__ == "__main__":
    print("🎯 ENTRENAMIENTO INCREMENTAL - 30 DÍAS EN CHUNKS DE 7 DÍAS")
    print("⏱️ Tiempo estimado: 10-20 minutos")
    print("💾 Consumo de memoria: <2GB")
    print("=" * 60)
    
    result = asyncio.run(test_incremental_training())
    
    if result:
        print("\n🎉 ¡PRUEBA EXITOSA!")
        print("✅ El entrenamiento incremental funciona correctamente")
        print("💾 Memoria optimizada - procesamiento por chunks")
    else:
        print("\n💥 PRUEBA FALLIDA")
        print("❌ Revisar logs para más detalles")
