#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_enhanced_training.py
========================
Script Principal para Ejecutar el Sistema de Entrenamiento Mejorado

Punto de entrada principal para ejecutar el sistema de entrenamiento histórico
mejorado con todas las funcionalidades avanzadas.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/run_enhanced_training.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Muestra el banner del sistema"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 BOT TRADING v10 ENTERPRISE 🚀                        ║
║                    Sistema de Entrenamiento Mejorado                       ║
║                                                                              ║
║  📊 Tracking granular de trades individuales                               ║
║  📈 Análisis de portfolio con correlación entre agentes                    ║
║  📱 Reporting completo vía Telegram con formato visual                     ║
║  ⚡ Gestión de memoria optimizada para entrenamientos largos               ║
║  🔧 Recovery automático y robustez enterprise                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

async def run_quick_test():
    """Ejecuta prueba rápida del sistema"""
    print("🧪 Ejecutando prueba rápida del sistema...")
    
    try:
        from scripts.testing.test_enhanced_system import EnhancedSystemTester
        
        tester = EnhancedSystemTester()
        results = await tester.run_all_tests()
        
        if results['failed_tests'] == 0:
            print("✅ Todas las pruebas pasaron exitosamente!")
            return True
        else:
            print(f"❌ {results['failed_tests']} pruebas fallaron")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando pruebas: {e}")
        return False

async def run_enhanced_training(
    days_back: int = 365,
    cycle_size_hours: int = 24,
    max_concurrent_agents: int = 8,
    telegram_enabled: bool = True,
    bot_token: str = None,
    chat_id: str = None
):
    """Ejecuta entrenamiento mejorado completo"""
    print(f"🚀 Iniciando entrenamiento mejorado:")
    print(f"   📅 Período: {days_back} días")
    print(f"   ⏰ Ciclos: {cycle_size_hours} horas")
    print(f"   🤖 Agentes: {max_concurrent_agents}")
    print(f"   📱 Telegram: {'✅' if telegram_enabled else '❌'}")
    
    try:
        from scripts.training.integrate_enhanced_system import run_enhanced_historical_training
        
        results = await run_enhanced_historical_training(
            days_back=days_back,
            telegram_enabled=telegram_enabled,
            bot_token=bot_token,
            chat_id=chat_id
        )
        
        if 'error' in results:
            print(f"❌ Error en entrenamiento: {results['error']}")
            return False
        
        print("✅ Entrenamiento completado exitosamente!")
        print(f"📊 Resultados: {results.get('performance_summary', {})}")
        return True
        
    except Exception as e:
        print(f"❌ Error ejecutando entrenamiento: {e}")
        return False

def check_requirements():
    """Verifica que se cumplan los requisitos del sistema"""
    print("🔍 Verificando requisitos del sistema...")
    
    # Verificar Python version
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False
    
    # Verificar archivos necesarios
    required_files = [
        'core/metrics/trade_metrics.py',
        'core/sync/enhanced_metrics_aggregator.py',
        'core/telegram/trade_reporter.py',
        'core/agents/enhanced_trading_agent.py',
        'scripts/training/optimized_training_pipeline.py',
        'scripts/training/integrate_enhanced_system.py'
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Archivo requerido no encontrado: {file_path}")
            return False
    
    # Verificar directorios
    required_dirs = ['logs', 'data', 'config']
    for dir_path in required_dirs:
        Path(dir_path).mkdir(exist_ok=True)
    
    print("✅ Todos los requisitos cumplidos")
    return True

def show_help():
    """Muestra ayuda del sistema"""
    print("""
📚 AYUDA - Sistema de Entrenamiento Mejorado

🚀 COMANDOS PRINCIPALES:
  python run_enhanced_training.py --help                    # Mostrar esta ayuda
  python run_enhanced_training.py --test                   # Ejecutar pruebas
  python run_enhanced_training.py --train                  # Entrenamiento completo
  python run_enhanced_training.py --quick                  # Prueba rápida (7 días)

⚙️ OPCIONES DE ENTRENAMIENTO:
  --days N                    # Días hacia atrás (default: 365)
  --cycle-size N              # Tamaño del ciclo en horas (default: 24)
  --max-agents N              # Máximo de agentes concurrentes (default: 8)
  --no-telegram               # Deshabilitar notificaciones de Telegram
  --bot-token TOKEN           # Token del bot de Telegram
  --chat-id ID                # ID del chat de Telegram

📱 CONFIGURACIÓN DE TELEGRAM:
  python scripts/setup/configure_telegram.py               # Configurar Telegram

🧪 PRUEBAS:
  python scripts/testing/test_enhanced_system.py           # Ejecutar todas las pruebas

📊 EJEMPLOS DE USO:

  # Prueba rápida (7 días, sin Telegram)
  python run_enhanced_training.py --quick

  # Entrenamiento completo (365 días, con Telegram)
  python run_enhanced_training.py --train --days 365 --bot-token YOUR_TOKEN --chat-id YOUR_CHAT_ID

  # Entrenamiento personalizado
  python run_enhanced_training.py --train --days 180 --cycle-size 12 --max-agents 6

  # Solo ejecutar pruebas
  python run_enhanced_training.py --test
    """)

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Sistema de Entrenamiento Mejorado - Bot Trading v10 Enterprise',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Comandos principales
    parser.add_argument('--test', action='store_true', help='Ejecutar pruebas del sistema')
    parser.add_argument('--train', action='store_true', help='Ejecutar entrenamiento completo')
    parser.add_argument('--quick', action='store_true', help='Ejecutar prueba rápida (7 días)')
    parser.add_argument('--help-detailed', action='store_true', help='Mostrar ayuda detallada')
    
    # Opciones de entrenamiento
    parser.add_argument('--days', type=int, default=365, help='Días hacia atrás para entrenar')
    parser.add_argument('--cycle-size', type=int, default=24, help='Tamaño del ciclo en horas')
    parser.add_argument('--max-agents', type=int, default=8, help='Máximo de agentes concurrentes')
    parser.add_argument('--no-telegram', action='store_true', help='Deshabilitar Telegram')
    
    # Configuración de Telegram
    parser.add_argument('--bot-token', type=str, help='Token del bot de Telegram')
    parser.add_argument('--chat-id', type=str, help='ID del chat de Telegram')
    
    args = parser.parse_args()
    
    # Mostrar banner
    print_banner()
    
    # Mostrar ayuda detallada
    if args.help_detailed:
        show_help()
        return 0
    
    # Verificar requisitos
    if not check_requirements():
        print("❌ Requisitos del sistema no cumplidos")
        return 1
    
    # Ejecutar comando solicitado
    if args.test:
        print("🧪 Ejecutando pruebas del sistema...")
        success = await run_quick_test()
        return 0 if success else 1
    
    elif args.quick:
        print("⚡ Ejecutando prueba rápida...")
        success = await run_enhanced_training(
            days_back=7,
            cycle_size_hours=6,
            max_concurrent_agents=4,
            telegram_enabled=False
        )
        return 0 if success else 1
    
    elif args.train:
        print("🚀 Ejecutando entrenamiento completo...")
        success = await run_enhanced_training(
            days_back=args.days,
            cycle_size_hours=args.cycle_size,
            max_concurrent_agents=args.max_agents,
            telegram_enabled=not args.no_telegram,
            bot_token=args.bot_token,
            chat_id=args.chat_id
        )
        return 0 if success else 1
    
    else:
        print("❌ No se especificó ningún comando")
        print("💡 Usa --help para ver las opciones disponibles")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Operación interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
