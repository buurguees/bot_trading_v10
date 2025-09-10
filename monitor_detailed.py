#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor Detallado de Entrenamiento
=================================
Monitorea el progreso detallado del entrenamiento con métricas por ciclo
"""

import time
import os
import json
from pathlib import Path
from datetime import datetime

def monitor_detailed_progress():
    """Monitorear progreso detallado del entrenamiento"""
    log_file = "train_6h_all_symbols.log"
    
    if not os.path.exists(log_file):
        print("❌ Archivo de log no encontrado")
        return
    
    print("🔍 Monitoreando entrenamiento detallado de 6 horas...")
    print("=" * 60)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Buscar información de progreso
        current_symbol = None
        current_cycle = 0
        total_cycles = 120
        symbols_completed = 0
        current_equity = 0
        current_pnl = 0
        current_win_rate = 0
        
        # Buscar líneas relevantes
        for line in lines:
            if "ENTRENANDO" in line and "Iniciando entrenamiento para" in line:
                current_symbol = line.split("para ")[1].split("...")[0]
            elif "Ciclo" in line and "Equity:" in line:
                # Extraer información del ciclo
                parts = line.split(" - ")
                for part in parts:
                    if "Ciclo" in part:
                        cycle_info = part.split("Ciclo ")[1].split("/")[0]
                        current_cycle = int(cycle_info)
                    elif "Equity:" in part:
                        equity_info = part.split("Equity: ")[1].split(" USDT")[0]
                        current_equity = float(equity_info)
                    elif "PnL:" in part:
                        pnl_info = part.split("PnL: ")[1].split("%")[0]
                        current_pnl = float(pnl_info)
                    elif "WR:" in part:
                        wr_info = part.split("WR: ")[1].split("%")[0]
                        current_win_rate = float(wr_info)
            elif "entrenado exitosamente" in line:
                symbols_completed += 1
        
        # Mostrar estado actual
        if current_symbol:
            progress = (current_cycle / total_cycles) * 100
            print(f"📊 Símbolo actual: {current_symbol}")
            print(f"🔄 Ciclo: {current_cycle}/{total_cycles} ({progress:.1f}%)")
            print(f"💰 Equity: {current_equity:.0f} USDT")
            print(f"📈 PnL: {current_pnl:.2f}%")
            print(f"🎯 Win Rate: {current_win_rate:.1f}%")
        else:
            print("⏳ Esperando inicio del entrenamiento...")
        
        print(f"\n📈 Progreso general:")
        print(f"  • Símbolos completados: {symbols_completed}")
        print(f"  • Símbolo actual: {current_symbol or 'N/A'}")
        
        # Verificar archivos generados
        models_dir = Path("data/models")
        if models_dir.exists():
            symbol_dirs = [d for d in models_dir.iterdir() if d.is_dir()]
            print(f"  • Directorios de símbolos: {len(symbol_dirs)}")
            
            for symbol_dir in symbol_dirs:
                symbol_name = symbol_dir.name
                files = list(symbol_dir.glob("*.json")) + list(symbol_dir.glob("*.jsonl"))
                print(f"    - {symbol_name}: {len(files)} archivos")
        
        # Verificar reportes
        reports_dir = Path("reports")
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.json"))
            print(f"  • Archivos de reporte: {len(report_files)}")
        
        # Mostrar últimas líneas del log
        print(f"\n📊 Últimas líneas del log:")
        print("-" * 60)
        for line in lines[-10:]:
            print(line.strip())
        
    except Exception as e:
        print(f"❌ Error monitoreando: {e}")

if __name__ == "__main__":
    monitor_detailed_progress()
