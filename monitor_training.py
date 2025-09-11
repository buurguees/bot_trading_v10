#!/usr/bin/env python3
"""
Script para monitorear el entrenamiento en tiempo real
"""

import json
import time
from pathlib import Path
from datetime import datetime

def monitor_training():
    """Monitorea el progreso del entrenamiento"""
    progress_file = Path("data/tmp/simple_train_progress.json")
    
    print("🔍 Monitoreando entrenamiento de 6 horas...")
    print("=" * 60)
    
    while True:
        try:
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                
                print(f"\n📊 Estado del Entrenamiento - {datetime.now().strftime('%H:%M:%S')}")
                print(f"🔄 Ciclo: {progress['cycle']}/{progress['total_cycles']}")
                print(f"📈 Progreso: {progress['progress_percent']:.2f}%")
                print(f"⏱️ Tiempo transcurrido: {progress['elapsed_time']}")
                print(f"⏳ Tiempo restante: {progress['remaining_time']}")
                print(f"📋 Estado: {progress['status']}")
                
                if progress['status'] == 'completed':
                    print("\n🎉 ¡Entrenamiento completado!")
                    break
                    
            else:
                print("⏳ Esperando inicio del entrenamiento...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(30)  # Verificar cada 30 segundos

if __name__ == "__main__":
    monitor_training()

