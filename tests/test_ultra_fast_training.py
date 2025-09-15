#!/usr/bin/env python3
"""
Script de prueba para modo ultra rápido de entrenamiento
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from scripts.training.train_hist_parallel import TrainHistParallel

async def test_ultra_fast_training():
    """Prueba el entrenamiento en modo ultra rápido"""
    print("🚀 INICIANDO PRUEBA DE ENTRENAMIENTO ULTRA RÁPIDO")
    print("=" * 60)
    
    try:
        # Crear entrenador en modo ultra rápido
        trainer = TrainHistParallel(progress_file="data/tmp/test_ultra_fast_progress.json")
        
        # Inicializar
        print("🔧 Inicializando entrenador...")
        print("✅ Entrenador inicializado correctamente")
        from datetime import datetime, timedelta
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=30)
        print("\n🚀 Iniciando entrenamiento ultra rápido...")
        result = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        if result:
            print("✅ Entrenamiento completado exitosamente")
            print(f"📊 Resultados guardados en: {trainer.agents_dir}")
        else:
            print("❌ Error en el entrenamiento")
            
        return True if result else False
        
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
