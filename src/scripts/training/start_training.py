#!/usr/bin/env python3
"""
start_training.py - Inicio Rápido de Entrenamiento Background
============================================================

Script para iniciar rápidamente el entrenamiento del bot sin dashboard.
Útil para ejecutar el bot en servidores o cuando no necesitas la interfaz gráfica.

Uso:
    python start_training.py
    python start_training.py --mode paper_trading --duration 8h
    python start_training.py --help

Modos disponibles:
    - paper_trading: Trading simulado (recomendado)
    - backtesting: Pruebas con datos históricos
    - development: Modo desarrollo y debugging
    - continuous_learning: Aprendizaje continuo

Duración:
    - 1h, 4h, 8h, 12h, 24h, indefinite
"""

import argparse
import os
import sys
import subprocess
import time
import signal
from datetime import datetime
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def signal_handler(signum, frame):
    """Maneja señales para cierre limpio"""
    print(f"\n⏹️ Recibida señal {signum}. Deteniendo entrenamiento...")
    sys.exit(0)

def validate_mode(mode: str) -> bool:
    """Valida que el modo sea válido"""
    valid_modes = ['paper_trading', 'backtesting', 'development', 'continuous_learning']
    return mode in valid_modes

def validate_duration(duration: str) -> bool:
    """Valida que la duración sea válida"""
    valid_durations = ['1h', '4h', '8h', '12h', '24h', 'indefinite']
    return duration in valid_durations

def start_training(mode: str = 'paper_trading', duration: str = '8h', verbose: bool = False):
    """Inicia el entrenamiento en background"""
    
    print("🤖 INICIO RÁPIDO DE ENTRENAMIENTO BACKGROUND")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Modo: {mode}")
    print(f"⏰ Duración: {duration}")
    print(f"📁 Directorio: {project_root}")
    print("=" * 50)
    print()
    
    # Validar parámetros
    if not validate_mode(mode):
        print(f"❌ Modo inválido: {mode}")
        print(f"Modos válidos: paper_trading, backtesting, development, continuous_learning")
        return False
    
    if not validate_duration(duration):
        print(f"❌ Duración inválida: {duration}")
        print(f"Duración válidas: 1h, 4h, 8h, 12h, 24h, indefinite")
        return False
    
    # Verificar prerequisitos
    print("🔍 Verificando prerequisitos...")
    
    # Verificar archivos críticos
    critical_files = [
        'core/main_background.py',
        'data/database.py',
        'models/adaptive_trainer.py'
    ]
    
    for file_path in critical_files:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"❌ Archivo crítico no encontrado: {file_path}")
            return False
        else:
            print(f"✅ {file_path}")
    
    # Verificar base de datos
    try:
        from data.database import db_manager
        stats = db_manager.get_database_stats()
        total_records = stats.get('total_records', 0)
        
        if total_records < 1000:
            print(f"⚠️ Datos insuficientes: {total_records:,} registros")
            print("💡 Considera descargar más datos históricos primero")
        else:
            print(f"✅ Datos suficientes: {total_records:,} registros")
            
    except Exception as e:
        print(f"⚠️ No se pudo verificar la base de datos: {e}")
    
    print()
    
    # Configurar variables de entorno
    env = os.environ.copy()
    env['TRADING_MODE'] = mode
    env['TRAINING_DURATION'] = duration
    env['BACKGROUND_MODE'] = 'true'
    env['DASHBOARD_ENABLED'] = 'false'
    env['PYTHONPATH'] = str(project_root)
    
    # Comando para ejecutar - usar main_background.py para evitar imports del dashboard
    cmd = [
        sys.executable, 
        'core/main_background.py', 
        '--mode', mode, 
        '--background', 
        '--no-dashboard'
    ]
    
    if verbose:
        cmd.append('--verbose')
    
    print(f"🚀 Ejecutando comando:")
    print(f"   {' '.join(cmd)}")
    print()
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Cambiar al directorio del proyecto
        os.chdir(project_root)
        
        # Ejecutar el proceso
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print("📊 Entrenamiento iniciado exitosamente")
        print("💡 Presiona Ctrl+C para detener")
        print()
        
        # Monitorear output
        start_time = time.time()
        line_count = 0
        
        for line in iter(process.stdout.readline, ''):
            if line:
                line_count += 1
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                if verbose or line_count % 10 == 0:  # Mostrar cada 10 líneas o si es verbose
                    print(f"[{timestamp}] {line.strip()}")
                
                # Mostrar progreso cada 5 minutos
                if int(time.time() - start_time) % 300 == 0:
                    elapsed = int(time.time() - start_time) // 60
                    print(f"⏰ Entrenamiento activo por {elapsed} minutos...")
        
        # Esperar a que termine el proceso
        return_code = process.wait()
        
        if return_code == 0:
            print("✅ Entrenamiento completado exitosamente")
        else:
            print(f"❌ Entrenamiento terminó con código: {return_code}")
            
        return return_code == 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo entrenamiento...")
        if 'process' in locals():
            process.terminate()
            process.wait()
        print("🔄 Entrenamiento detenido")
        return True
        
    except Exception as e:
        print(f"❌ Error durante el entrenamiento: {e}")
        return False

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Inicio rápido de entrenamiento background del Trading Bot v10',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python start_training.py
  python start_training.py --mode paper_trading --duration 8h
  python start_training.py --mode backtesting --duration 24h --verbose
  python start_training.py --mode continuous_learning --duration indefinite
        """
    )
    
    parser.add_argument(
        '--mode', 
        default='paper_trading',
        choices=['paper_trading', 'backtesting', 'development', 'continuous_learning'],
        help='Modo de entrenamiento (default: paper_trading)'
    )
    
    parser.add_argument(
        '--duration',
        default='8h',
        choices=['1h', '4h', '8h', '12h', '24h', 'indefinite'],
        help='Duración del entrenamiento (default: 8h)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar output detallado'
    )
    
    args = parser.parse_args()
    
    # Iniciar entrenamiento
    success = start_training(
        mode=args.mode,
        duration=args.duration,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
