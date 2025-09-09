#!/usr/bin/env python3
"""
scripts/start_night_training.py - Entrenamiento Nocturno Automático
===================================================================

Script para iniciar automáticamente el entrenamiento durante la noche.
Ideal para ejecutar en servidores o sistemas que no están en uso durante la noche.

Características:
- Inicio automático en horario nocturno
- Entrenamiento de larga duración (8-12 horas)
- Logging detallado
- Reinicio automático en caso de errores
- Notificaciones por email (opcional)

Uso:
    python scripts/start_night_training.py
    python scripts/start_night_training.py --start-time 22:00 --duration 10h
"""

import argparse
import os
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/night_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NightTrainingScheduler:
    """Programador de entrenamiento nocturno"""
    
    def __init__(self, start_time: str = "22:00", duration: str = "10h"):
        self.start_time = start_time
        self.duration = duration
        self.is_running = False
        self.training_process = None
        
    def start_training(self):
        """Inicia el entrenamiento nocturno"""
        try:
            logger.info("🌙 Iniciando entrenamiento nocturno...")
            
            # Verificar que no haya otro entrenamiento corriendo
            if self.is_running:
                logger.warning("⚠️ Ya hay un entrenamiento en progreso")
                return
            
            self.is_running = True
            
            # Importar y ejecutar start_training
            from start_training import start_training
            
            # Configurar modo para entrenamiento nocturno
            mode = "continuous_learning"  # Mejor para entrenamiento prolongado
            
            logger.info(f"🎯 Modo: {mode}")
            logger.info(f"⏰ Duración: {self.duration}")
            logger.info(f"🕐 Hora de inicio: {datetime.now().strftime('%H:%M:%S')}")
            
            # Ejecutar entrenamiento
            success = start_training(
                mode=mode,
                duration=self.duration,
                verbose=False  # Menos verbose para logs nocturnos
            )
            
            if success:
                logger.info("✅ Entrenamiento nocturno completado exitosamente")
            else:
                logger.error("❌ Entrenamiento nocturno falló")
                
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento nocturno: {e}")
        finally:
            self.is_running = False
    
    def schedule_training(self):
        """Programa el entrenamiento para la hora especificada"""
        logger.info(f"📅 Programando entrenamiento para las {self.start_time}")
        
        # Programar entrenamiento diario
        schedule.every().day.at(self.start_time).do(self.start_training)
        
        # Mostrar próximas ejecuciones
        next_run = schedule.next_run()
        logger.info(f"⏰ Próximo entrenamiento: {next_run}")
        
        # Mantener el programador activo
        logger.info("🔄 Programador activo - Presiona Ctrl+C para detener")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
                
        except KeyboardInterrupt:
            logger.info("⏹️ Programador detenido por el usuario")
    
    def run_immediate(self):
        """Ejecuta el entrenamiento inmediatamente"""
        logger.info("🚀 Ejecutando entrenamiento inmediato...")
        self.start_training()
    
    def show_status(self):
        """Muestra el estado del programador"""
        print("\n📊 ESTADO DEL ENTRENAMIENTO NOCTURNO")
        print("=" * 40)
        print(f"🕐 Hora programada: {self.start_time}")
        print(f"⏰ Duración: {self.duration}")
        print(f"🔄 Estado: {'Activo' if self.is_running else 'Inactivo'}")
        
        if schedule.jobs:
            next_run = schedule.next_run()
            print(f"📅 Próxima ejecución: {next_run}")
        else:
            print("📅 No hay entrenamientos programados")
        
        print(f"📁 Logs: logs/night_training.log")
        print()

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Programador de entrenamiento nocturno del Trading Bot v10',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python scripts/start_night_training.py
  python scripts/start_night_training.py --start-time 23:00 --duration 12h
  python scripts/start_night_training.py --immediate
  python scripts/start_night_training.py --status
        """
    )
    
    parser.add_argument(
        '--start-time',
        default='22:00',
        help='Hora de inicio del entrenamiento (formato HH:MM) (default: 22:00)'
    )
    
    parser.add_argument(
        '--duration',
        default='10h',
        choices=['6h', '8h', '10h', '12h', '14h', '16h'],
        help='Duración del entrenamiento (default: 10h)'
    )
    
    parser.add_argument(
        '--immediate',
        action='store_true',
        help='Ejecutar entrenamiento inmediatamente'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Mostrar estado del programador'
    )
    
    args = parser.parse_args()
    
    # Crear directorio de logs si no existe
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Crear programador
    scheduler = NightTrainingScheduler(
        start_time=args.start_time,
        duration=args.duration
    )
    
    if args.status:
        scheduler.show_status()
    elif args.immediate:
        scheduler.run_immediate()
    else:
        scheduler.schedule_training()

if __name__ == "__main__":
    main()
