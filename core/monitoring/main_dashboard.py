# Ruta: core/monitoring/main_dashboard.py
#!/usr/bin/env python3
"""
Dashboard Principal del Trading Bot v10
=======================================

Script principal para iniciar el dashboard web del sistema de trading.
Incluye todas las funcionalidades de monitoreo, análisis y control.

Uso:
    python src/core/monitoring/main_dashboard.py
    python src/core/monitoring/main_dashboard.py --port 8050 --debug
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.monitoring.core import start_monitoring_system

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DASHBOARD - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dashboard.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Función principal del dashboard"""
    parser = argparse.ArgumentParser(
        description="Dashboard Principal del Trading Bot v10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python src/core/monitoring/main_dashboard.py
  python src/core/monitoring/main_dashboard.py --port 8050 --debug
  python src/core/monitoring/main_dashboard.py --host 0.0.0.0 --port 3000
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host del servidor (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8050,
        help='Puerto del servidor (default: 8050)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Modo debug'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='No abrir navegador automáticamente'
    )
    
    args = parser.parse_args()
    
    try:
        # Crear directorio de logs si no existe
        Path("logs").mkdir(exist_ok=True)
        
        logger.info("Iniciando Dashboard Principal del Trading Bot v10")
        logger.info(f"Host: {args.host}")
        logger.info(f"Puerto: {args.port}")
        logger.info(f"Debug: {args.debug}")
        
        # Configuración personalizada
        config = {
            'auto_open_browser': not args.no_browser,
            'debug_mode': args.debug
        }
        
        # Iniciar sistema de monitoreo
        start_monitoring_system(
            host=args.host,
            port=args.port,
            debug=args.debug,
            config=config
        )
        
    except KeyboardInterrupt:
        logger.info("Dashboard interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal en dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()