#!/usr/bin/env python3
"""
Monitor de Entrenamiento en Tiempo Real
=======================================

Script para monitorear el progreso del entrenamiento autónomo en tiempo real.
"""

import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import subprocess

def clear_screen():
    """Limpia la pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Imprime header del monitor"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "🤖 MONITOR DE ENTRENAMIENTO ENTERPRISE 🤖" + " " * 20 + "║")
    print("╚" + "═" * 78 + "╝")

def get_log_tail(n_lines=20):
    """Obtiene las últimas líneas del log"""
    log_file = "logs/autonomous_training.log"
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
        
        # GPU stats si está disponible
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                stats["gpu_memory_percent"] = gpu.memoryUtil * 100
                stats["gpu_temperature"] = gpu.temperature
            else:
                stats["gpu_memory_percent"] = 0
                stats["gpu_temperature"] = 0
        except:
            stats["gpu_memory_percent"] = 0
            stats["gpu_temperature"] = 0
        
        return stats
    except Exception as e:
        return {"error": str(e)}

def get_training_progress():
    """Obtiene progreso del entrenamiento"""
    try:
        # Buscar archivos de checkpoint
        checkpoint_dir = Path("checkpoints/autonomous")
        if checkpoint_dir.exists():
            checkpoints = list(checkpoint_dir.glob("*.ckpt"))
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=os.path.getctime)
                return {
                    "checkpoints": len(checkpoints),
                    "latest_checkpoint": latest_checkpoint.name,
                    "checkpoint_size": f"{latest_checkpoint.stat().st_size / 1024 / 1024:.1f} MB"
                }
        
        return {"checkpoints": 0, "latest_checkpoint": "N/A", "checkpoint_size": "0 MB"}
    except Exception as e:
        return {"error": str(e)}

def get_mlflow_status():
    """Verifica estado de MLflow"""
    try:
        # Verificar si MLflow está corriendo
        result = subprocess.run(
            "curl -s http://localhost:5000/api/2.0/mlflow/experiments/search",
            shell=True, capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            return {"status": "✅ MLflow activo", "url": "http://localhost:5000"}
        else:
            return {"status": "❌ MLflow inactivo", "url": "N/A"}
    except:
        return {"status": "❌ MLflow no disponible", "url": "N/A"}

def get_prometheus_status():
    """Verifica estado de Prometheus"""
    try:
        result = subprocess.run(
            "curl -s http://localhost:8000/metrics",
            shell=True, capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            metrics_count = len([line for line in result.stdout.split('\n') if line and not line.startswith('#')])
            return {"status": "✅ Prometheus activo", "metrics": metrics_count, "url": "http://localhost:8000/metrics"}
        else:
            return {"status": "❌ Prometheus inactivo", "metrics": 0, "url": "N/A"}
    except:
        return {"status": "❌ Prometheus no disponible", "metrics": 0, "url": "N/A"}

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
    
    if stats["gpu_memory_percent"] > 0:
        print(format_status_line("🎮 GPU Memoria", f"{stats['gpu_memory_percent']:.1f}%"))
        print(format_status_line("🌡️ GPU Temp", f"{stats['gpu_temperature']:.1f}°C"))

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

def print_services_status():
    """Imprime estado de servicios"""
    print("\n🔧 SERVICIOS")
    print("─" * 50)
    
    mlflow = get_mlflow_status()
    prometheus = get_prometheus_status()
    
    print(format_status_line("📊 MLflow", mlflow["status"]))
    if mlflow["url"] != "N/A":
        print(f"   URL: {mlflow['url']}")
    
    print(format_status_line("📈 Prometheus", prometheus["status"]))
    if prometheus["url"] != "N/A":
        print(f"   URL: {prometheus['url']}")
        print(f"   Métricas: {prometheus['metrics']}")

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
    print("• El monitor se actualiza cada 10 segundos")
    print("• Revisa logs/autonomous_training.log para detalles")
    print("• Métricas en tiempo real: http://localhost:8000/metrics")

def main():
    """Función principal del monitor"""
    print("🚀 Iniciando monitor de entrenamiento...")
    
    try:
        while True:
            clear_screen()
            print_header()
            
            # Obtener estadísticas
            stats = get_system_stats()
            progress = get_training_progress()
            
            # Imprimir información
            print_system_stats(stats)
            print_training_progress(progress)
            print_services_status()
            print_recent_logs()
            print_instructions()
            
            # Esperar antes de la siguiente actualización
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido. ¡Que disfrutes tu cena! 🍽️")
    except Exception as e:
        print(f"\n❌ Error en monitor: {e}")

if __name__ == "__main__":
    main()
