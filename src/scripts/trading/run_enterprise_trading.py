#!/usr/bin/env python3
"""
Script Principal para Ejecutar Trading Enterprise
================================================

Este script permite ejecutar el sistema de trading enterprise en diferentes modos:
- live: Trading en vivo con dinero real
- paper: Trading simulado para pruebas
- emergency: Parada de emergencia del sistema

Uso:
    python run_enterprise_trading.py --mode live
    python run_enterprise_trading.py --mode paper
    python run_enterprise_trading.py --mode emergency

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from trading_scripts.enterprise import start_live_trading, start_paper_trading, emergency_stop
from config.config_loader import user_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/enterprise/trading/enterprise_trading.log')
    ]
)

logger = logging.getLogger(__name__)

def parse_arguments():
    """Parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Ejecutar sistema de trading enterprise',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run_enterprise_trading.py --mode live
  python run_enterprise_trading.py --mode paper --symbols BTCUSDT,ETHUSDT
  python run_enterprise_trading.py --mode emergency
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['live', 'paper', 'emergency'],
        required=True,
        help='Modo de ejecución del sistema'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        default='BTCUSDT,ETHUSDT,ADAUSDT,SOLUSDT,DOGEUSDT,AVAXUSDT,TONUSDT,BNBUSDT,XRPUSDT,LINKUSDT',
        help='Símbolos a tradear (separados por comas)'
    )
    
    parser.add_argument(
        '--leverage',
        type=int,
        default=10,
        help='Leverage inicial (1-30)'
    )
    
    parser.add_argument(
        '--risk-percent',
        type=float,
        default=2.0,
        help='Porcentaje de riesgo por operación (0.1-10.0)'
    )
    
    parser.add_argument(
        '--max-positions',
        type=int,
        default=5,
        help='Máximo número de posiciones simultáneas'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Ejecutar en modo dry-run (sin órdenes reales)'
    )
    
    parser.add_argument(
        '--config-file',
        type=str,
        help='Archivo de configuración personalizado'
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Valida los argumentos proporcionados"""
    errors = []
    
    # Validar leverage
    if not 1 <= args.leverage <= 30:
        errors.append("Leverage debe estar entre 1 y 30")
    
    # Validar risk-percent
    if not 0.1 <= args.risk_percent <= 10.0:
        errors.append("Risk-percent debe estar entre 0.1 y 10.0")
    
    # Validar max-positions
    if not 1 <= args.max_positions <= 20:
        errors.append("Max-positions debe estar entre 1 y 20")
    
    # Validar símbolos
    symbols = args.symbols.split(',')
    if len(symbols) > 20:
        errors.append("Máximo 20 símbolos permitidos")
    
    if errors:
        for error in errors:
            logger.error(f"❌ Error de validación: {error}")
        return False
    
    return True

def load_configuration(args):
    """Carga la configuración del sistema"""
    try:
        # Cargar configuración base
        config = user_config.get_value(['trading'], {})
        
        # Aplicar argumentos de línea de comandos
        config.update({
            'mode': args.mode,
            'symbols': args.symbols.split(','),
            'leverage': args.leverage,
            'risk_percent': args.risk_percent,
            'max_positions': args.max_positions,
            'dry_run': args.dry_run
        })
        
        # Cargar configuración personalizada si se proporciona
        if args.config_file and os.path.exists(args.config_file):
            logger.info(f"📁 Cargando configuración personalizada: {args.config_file}")
            # Aquí se cargaría la configuración personalizada
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Error cargando configuración: {e}")
        return None

async def run_trading_system(mode: str, config: dict):
    """Ejecuta el sistema de trading según el modo especificado"""
    try:
        if mode == 'live':
            logger.info("🚀 Iniciando trading en vivo...")
            await start_live_trading(config)
            
        elif mode == 'paper':
            logger.info("📊 Iniciando paper trading...")
            await start_paper_trading(config)
            
        elif mode == 'emergency':
            logger.info("🛑 Ejecutando parada de emergencia...")
            await emergency_stop()
            
        else:
            logger.error(f"❌ Modo no válido: {mode}")
            return False
        
        return True
        
    except KeyboardInterrupt:
        logger.info("⏹️ Sistema detenido por el usuario")
        return True
    except Exception as e:
        logger.error(f"❌ Error ejecutando sistema de trading: {e}")
        return False

def main():
    """Función principal"""
    try:
        # Parsear argumentos
        args = parse_arguments()
        
        # Validar argumentos
        if not validate_arguments(args):
            sys.exit(1)
        
        # Cargar configuración
        config = load_configuration(args)
        if not config:
            sys.exit(1)
        
        # Mostrar información del sistema
        logger.info("=" * 60)
        logger.info("🤖 BOT TRADING V10 ENTERPRISE")
        logger.info("=" * 60)
        logger.info(f"Modo: {args.mode.upper()}")
        logger.info(f"Símbolos: {', '.join(config['symbols'])}")
        logger.info(f"Leverage: {config['leverage']}x")
        logger.info(f"Riesgo por operación: {config['risk_percent']}%")
        logger.info(f"Máximo posiciones: {config['max_positions']}")
        logger.info(f"Dry run: {config['dry_run']}")
        logger.info("=" * 60)
        
        # Ejecutar sistema
        success = asyncio.run(run_trading_system(args.mode, config))
        
        if success:
            logger.info("✅ Sistema ejecutado exitosamente")
            sys.exit(0)
        else:
            logger.error("❌ Error ejecutando sistema")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()