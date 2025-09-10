#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Entrenamiento
========================
Monitorea el progreso del entrenamiento de 6 horas
"""

import time
import os
from pathlib import Path
from datetime import datetime

def monitor_training_progress():
    """Monitorear progreso del entrenamiento"""
    log_file = "train_6h_all_symbols.log"
    
    if not os.path.exists(log_file):
        print("❌ Archivo de log no encontrado")
        return
    
    print("🔍 Monitoreando entrenamiento de 6 horas...")
    print("=" * 50)
    
    # Leer las últimas líneas del log
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Mostrar últimas 20 líneas
        print("📊 Últimas líneas del log:")
        print("-" * 50)
        for line in lines[-20:]:
            print(line.strip())
            
        # Buscar información de progreso
        symbols_trained = 0
        current_symbol = None
        
        for line in lines:
            if "ENTRENANDO" in line and "Iniciando entrenamiento para" in line:
                current_symbol = line.split("para ")[1].split("...")[0]
            elif "entrenado exitosamente" in line:
                symbols_trained += 1
        
        print("\n📈 Progreso actual:")
        print(f"  • Símbolos completados: {symbols_trained}")
        if current_symbol:
            print(f"  • Símbolo actual: {current_symbol}")
        
        # Verificar si hay archivos de resultados
        results_files = list(Path(".").glob("training_6h_results_*.json"))
        if results_files:
            print(f"  • Archivos de resultados: {len(results_files)}")
        
        # Verificar modelos generados
        models_dir = Path("data/models")
        if models_dir.exists():
            model_files = list(models_dir.glob("*.pkl"))
            print(f"  • Modelos generados: {len(model_files)}")
        
    except Exception as e:
        print(f"❌ Error monitoreando: {e}")

if __name__ == "__main__":
    monitor_training_progress()
