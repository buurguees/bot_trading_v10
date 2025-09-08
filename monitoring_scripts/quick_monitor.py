#!/usr/bin/env python3
"""
Monitor Rápido de Entrenamiento
===============================

Script para monitorear rápidamente el progreso del entrenamiento.
"""

import time
import os
from datetime import datetime
from pathlib import Path

def check_training_status():
    """Verifica el estado del entrenamiento"""
    print("🤖 ESTADO DEL ENTRENAMIENTO AUTÓNOMO")
    print("=" * 50)
    
    # Verificar logs
    log_files = [
        "logs/simple_training.log",
        "logs/fixed_training.log"
    ]
    
    active_log = None
    for log_file in log_files:
        if Path(log_file).exists():
            stat = Path(log_file).stat()
            if stat.st_size > 0:
                active_log = log_file
                break
    
    if active_log:
        print(f"📁 Log activo: {active_log}")
        
        # Mostrar últimas líneas
        try:
            with open(active_log, 'r') as f:
                lines = f.readlines()
                print(f"\n📝 Últimas 10 líneas:")
                print("-" * 30)
                for line in lines[-10:]:
                    print(line.strip())
        except Exception as e:
            print(f"❌ Error leyendo log: {e}")
    else:
        print("❌ No se encontraron logs activos")
    
    # Verificar checkpoints
    checkpoint_dir = Path("checkpoints")
    if checkpoint_dir.exists():
        checkpoints = list(checkpoint_dir.glob("*.pkl"))
        print(f"\n📁 Checkpoints: {len(checkpoints)} archivos")
        for checkpoint in checkpoints:
            size_kb = checkpoint.stat().st_size / 1024
            print(f"   • {checkpoint.name} ({size_kb:.1f} KB)")
    
    # Verificar datos
    data_dir = Path("data")
    if data_dir.exists():
        data_files = list(data_dir.glob("*.csv"))
        print(f"\n📊 Archivos de datos: {len(data_files)}")
        for file in data_files:
            size_kb = file.stat().st_size / 1024
            print(f"   • {file.name} ({size_kb:.1f} KB)")
    
    # Verificar sistema
    try:
        import psutil
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        print(f"\n💻 Sistema: CPU {cpu:.1f}%, Memoria {memory:.1f}%")
    except:
        print("\n💻 Sistema: No disponible")

def main():
    """Función principal"""
    print("🚀 Monitor Rápido de Entrenamiento")
    print("Presiona Ctrl+C para salir")
    print()
    
    try:
        while True:
            check_training_status()
            print("\n" + "=" * 50)
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Actualizando en 10 segundos...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido. ¡Que disfrutes tu cena! 🍽️")

if __name__ == "__main__":
    main()
