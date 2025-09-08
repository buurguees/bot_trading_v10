#!/usr/bin/env python3
"""
Monitor Simple de Entrenamiento
===============================

Script para monitorear el progreso del entrenamiento simple en tiempo real.
"""

import time
import os
import sys
from datetime import datetime
from pathlib import Path
import json

def clear_screen():
    """Limpia la pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Imprime header del monitor"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "🤖 MONITOR DE ENTRENAMIENTO SIMPLE 🤖" + " " * 20 + "║")
    print("╚" + "═" * 78 + "╝")

def get_log_tail(n_lines=15):
    """Obtiene las últimas líneas del log"""
    log_file = "logs/simple_training.log"
    if not Path(log_file).exists():
        return ["❌ Archivo de log no encontrado"]
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return lines[-n_lines:]
    except Exception as e:
        return [f"❌ Error leyendo log: {e}"]

def get_system_stats():
    """Obtiene estadísticas del sistema"""
    try:
        import psutil
        
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        
        return stats
    except Exception as e:
        return {"error": str(e)}

def get_training_progress():
    """Obtiene progreso del entrenamiento"""
    try:
        # Buscar archivos de checkpoint
        checkpoint_dir = Path("checkpoints")
        if checkpoint_dir.exists():
            checkpoints = list(checkpoint_dir.glob("*.pkl"))
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=os.path.getctime)
                return {
                    "checkpoints": len(checkpoints),
                    "latest_checkpoint": latest_checkpoint.name,
                    "checkpoint_size": f"{latest_checkpoint.stat().st_size / 1024:.1f} KB"
                }
        
        return {"checkpoints": 0, "latest_checkpoint": "N/A", "checkpoint_size": "0 KB"}
    except Exception as e:
        return {"error": str(e)}

def get_data_files():
    """Verifica archivos de datos"""
    try:
        data_dir = Path("data")
        if data_dir.exists():
            files = list(data_dir.glob("*.csv"))
            return {
                "data_files": len(files),
                "files": [f.name for f in files]
            }
        return {"data_files": 0, "files": []}
    except Exception as e:
        return {"error": str(e)}

def format_status_line(label, value, width=20):
    """Formatea línea de estado"""
    return f"{label:<{width}}: {value}"

def print_system_stats(stats):
    """Imprime estadísticas del sistema"""
    print("\n📊 ESTADÍSTICAS DEL SISTEMA")
    print("─" * 50)
    
    if "error" in stats:
        print(f"❌ Error: {stats['error']}")
        return
    
    print(format_status_line("⏰ Tiempo", stats["timestamp"]))
    print(format_status_line("🖥️ CPU", f"{stats['cpu_percent']:.1f}%"))
    print(format_status_line("💾 Memoria", f"{stats['memory_percent']:.1f}%"))
    print(format_status_line("💿 Disco", f"{stats['disk_percent']:.1f}%"))

def print_training_progress(progress):
    """Imprime progreso del entrenamiento"""
    print("\n🤖 PROGRESO DEL ENTRENAMIENTO")
    print("─" * 50)
    
    if "error" in progress:
        print(f"❌ Error: {progress['error']}")
        return
    
    print(format_status_line("📁 Checkpoints", str(progress["checkpoints"])))
    print(format_status_line("📄 Último", progress["latest_checkpoint"]))
    print(format_status_line("💾 Tamaño", progress["checkpoint_size"]))

def print_data_files(data_info):
    """Imprime información de archivos de datos"""
    print("\n📊 ARCHIVOS DE DATOS")
    print("─" * 50)
    
    if "error" in data_info:
        print(f"❌ Error: {data_info['error']}")
        return
    
    print(format_status_line("📁 Archivos", str(data_info["data_files"])))
    for file in data_info["files"]:
        print(f"   • {file}")

def print_recent_logs():
    """Imprime logs recientes"""
    print("\n📝 LOGS RECIENTES")
    print("─" * 50)
    
    logs = get_log_tail(10)
    for log in logs:
        # Colorear logs según nivel
        log_str = log.strip()
        if "ERROR" in log_str:
            print(f"❌ {log_str}")
        elif "WARNING" in log_str:
            print(f"⚠️ {log_str}")
        elif "INFO" in log_str:
            print(f"ℹ️ {log_str}")
        else:
            print(f"   {log_str}")

def print_instructions():
    """Imprime instrucciones"""
    print("\n🎮 CONTROLES")
    print("─" * 50)
    print("• Ctrl+C: Salir del monitor")
    print("• El monitor se actualiza cada 5 segundos")
    print("• Revisa logs/simple_training.log para detalles")
    print("• El entrenamiento corre en background")

def main():
    """Función principal del monitor"""
    print("🚀 Iniciando monitor de entrenamiento simple...")
    
    try:
        while True:
            clear_screen()
            print_header()
            
            # Obtener estadísticas
            stats = get_system_stats()
            progress = get_training_progress()
            data_info = get_data_files()
            
            # Imprimir información
            print_system_stats(stats)
            print_training_progress(progress)
            print_data_files(data_info)
            print_recent_logs()
            print_instructions()
            
            # Esperar antes de la siguiente actualización
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido. ¡Que disfrutes tu cena! 🍽️")
    except Exception as e:
        print(f"\n❌ Error en monitor: {e}")

if __name__ == "__main__":
    main()
