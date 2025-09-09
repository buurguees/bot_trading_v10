#!/usr/bin/env python3
"""
train_background.py - Entrenamiento Background Simple
====================================================

Script simplificado para ejecutar entrenamiento sin dashboard.
Solo entrenamiento, registro de datos y actualización de modelos.

Uso:
    python train_background.py
    python train_background.py --mode continuous_learning --hours 8
    python train_background.py --help
"""

import argparse
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Importar la clase de background
from core.main_background import TradingBotBackground

def setup_logging():
    """Configura el sistema de logging"""
    # Crear directorio de logs si no existe
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "background_training.log"),
            logging.StreamHandler()
        ]
    )

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Trading Bot v10 - Entrenamiento Background Simple',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python train_background.py
  python train_background.py --mode continuous_learning --hours 8
  python train_background.py --mode paper_trading --hours 24
  python train_background.py --mode development --hours 1
        """
    )
    
    parser.add_argument(
        '--mode', 
        default='paper_trading',
        choices=['paper_trading', 'backtesting', 'development', 'continuous_learning'],
        help='Modo de entrenamiento (default: paper_trading)'
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        help='Duración en horas (opcional, si no se especifica es indefinido)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar output detallado'
    )
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging()
    
    # Mostrar información de inicio
    print("🤖 TRADING BOT V10 - ENTRENAMIENTO BACKGROUND")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Modo: {args.mode}")
    print(f"⏰ Duración: {args.hours} horas" if args.hours else "Indefinido")
    print(f"📁 Directorio: {project_root}")
    print("🖥️ Dashboard: Deshabilitado")
    print("=" * 50)
    print()
    
    # Crear instancia del bot
    bot = TradingBotBackground(mode=args.mode, duration_hours=args.hours)
    
    try:
        # Ejecutar el flujo de background
        success = asyncio.run(bot.ejecutar_flujo_background())
        
        if success:
            print("\n✅ Entrenamiento completado exitosamente")
            return 0
        else:
            print("\n❌ Entrenamiento terminó con errores")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Entrenamiento detenido por el usuario")
        bot.detener_entrenamiento()
        return 0
        
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logging.error(f"Error crítico: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
