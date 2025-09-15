#!/usr/bin/env python3
"""
Script de prueba para modo ultra rápido de entrenamiento
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scripts.training.train_historical import TrainHistoricalEnterprise

async def test_ultra_fast_training():
    """Prueba el entrenamiento en modo ultra rápido"""
    print("🚀 INICIANDO PRUEBA DE ENTRENAMIENTO ULTRA RÁPIDO")
    print("=" * 60)
    
    try:
        # Crear entrenador en modo ultra rápido
        trainer = TrainHistoricalEnterprise(
            progress_id="test_ultra_fast",
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
        print(f"🤖 Símbolos: {len(trainer.symbols)}")
        print(f"⏰ Timeframes: {len(trainer.timeframes)}")
        
        # Ejecutar entrenamiento
        print("\n🚀 Iniciando entrenamiento ultra rápido...")
        result = await trainer.execute()
        
        if result:
            print("✅ Entrenamiento completado exitosamente")
            print(f"📊 Resultados guardados en: {trainer.agents_dir}")
        else:
            print("❌ Error en el entrenamiento")
            
        return result
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        return False

if __name__ == "__main__":
    print("🎯 MODO ULTRA RÁPIDO - 30 DÍAS DE DATOS")
    print("⏱️ Tiempo estimado: 15-30 minutos")
    print("=" * 60)
    
    result = asyncio.run(test_ultra_fast_training())
    
    if result:
        print("\n🎉 ¡PRUEBA EXITOSA!")
        print("✅ El modo ultra rápido funciona correctamente")
    else:
        print("\n💥 PRUEBA FALLIDA")
        print("❌ Revisar logs para más detalles")
