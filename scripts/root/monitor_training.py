#!/usr/bin/env python3
"""
Monitor de Entrenamiento Enterprise - Bot Trading v10
====================================================

Script para monitorear el progreso del entrenamiento enterprise en tiempo real.
"""

import time
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

def monitor_training():
    """Monitorea el progreso del entrenamiento"""
    log_file = Path("logs/enterprise/training/6h_training.log")
    
    print("🔍 Monitoreando entrenamiento enterprise...")
    print("=" * 60)
    
    if not log_file.exists():
        print("❌ Archivo de log no encontrado. Verificando si el entrenamiento está ejecutándose...")
        
        # Verificar procesos de Python
        import subprocess
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                  capture_output=True, text=True)
            if 'python.exe' in result.stdout:
                print("✅ Procesos de Python encontrados ejecutándose")
            else:
                print("❌ No se encontraron procesos de Python ejecutándose")
        except Exception as e:
            print(f"⚠️ Error verificando procesos: {e}")
        
        return
    
    print(f"📊 Monitoreando: {log_file}")
    print("Presiona Ctrl+C para salir del monitoreo")
    print("=" * 60)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Ir al final del archivo
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    # Mostrar línea con timestamp
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] {line.strip()}")
                else:
                    time.sleep(1)  # Esperar 1 segundo antes de leer más
                    
    except KeyboardInterrupt:
        print("\n⏹️ Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en monitoreo: {e}")

def check_training_status():
    """Verifica el estado actual del entrenamiento"""
    print("🔍 Verificando estado del entrenamiento...")
    print("=" * 60)
    
    # Verificar archivos de log
    log_file = Path("logs/enterprise/training/6h_training.log")
    if log_file.exists():
        print(f"✅ Log encontrado: {log_file}")
        
        # Leer últimas líneas
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📊 Total de líneas en log: {len(lines)}")
                
                if lines:
                    print("\n📋 Últimas 10 líneas:")
                    for line in lines[-10:]:
                        print(f"  {line.strip()}")
                else:
                    print("⚠️ Log vacío")
        except Exception as e:
            print(f"❌ Error leyendo log: {e}")
    else:
        print("❌ Log no encontrado")
    
    # Verificar directorios de resultados
    result_dirs = [
        "models/enterprise/6h_training",
        "checkpoints/enterprise/6h_training",
        "reports/training/6h_training"
    ]
    
    print(f"\n📁 Directorios de resultados:")
    for dir_path in result_dirs:
        path = Path(dir_path)
        if path.exists():
            files = list(path.glob("*"))
            print(f"  ✅ {dir_path}: {len(files)} archivos")
        else:
            print(f"  ❌ {dir_path}: No existe")
    
    # Verificar procesos
    print(f"\n🔄 Procesos de Python:")
    try:
        import subprocess
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        if 'python.exe' in result.stdout:
            lines = [line for line in result.stdout.split('\n') if 'python.exe' in line]
            print(f"  ✅ {len(lines)} procesos de Python ejecutándose")
            for line in lines:
                if line.strip():
                    print(f"    {line.strip()}")
        else:
            print("  ❌ No se encontraron procesos de Python")
    except Exception as e:
        print(f"  ⚠️ Error verificando procesos: {e}")

def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        check_training_status()
    else:
        monitor_training()

if __name__ == "__main__":
    main()
