#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_validation_tests.py
========================
Script de Ejecución de Pruebas de Validación

Permite ejecutar diferentes tipos de pruebas de validación del sistema mejorado:
- Prueba rápida (5 minutos)
- Prueba extrema (2 horas)
- Prueba personalizada

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
        logging.FileHandler('logs/run_validation_tests.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Muestra el banner del sistema de pruebas"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 SISTEMA DE PRUEBAS DE VALIDACIÓN 🧪                  ║
║                    Bot Trading v10 Enterprise                              ║
║                                                                              ║
║  ⚡ Prueba Rápida: 5 minutos, validación básica                           ║
║  🔥 Prueba Extrema: 2 horas, validación completa                          ║
║  🎯 Prueba Personalizada: configuración específica                        ║
║                                                                              ║
║  📊 Valida: Trades, Telegram, Timeframes, Features, Estrategias           ║
║  🎯 Objetivos: Win Rate, Calidad, Robustez, Performance                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

async def run_quick_test():
    """Ejecuta prueba rápida de validación"""
    print("⚡ Ejecutando prueba rápida de validación...")
    
    try:
        from scripts.testing.quick_validation_test import QuickValidationTester
        
        tester = QuickValidationTester()
        results = await tester.run_quick_validation()
        
        if 'error' in results:
            print(f"❌ Error en prueba rápida: {results['error']}")
            return False
        
        # Mostrar resumen
        summary = results.get('validation_summary', {})
        success_rate = summary.get('success_rate', 0)
        
        print(f"\n📊 RESUMEN DE PRUEBA RÁPIDA:")
        print(f"✅ Validaciones exitosas: {summary.get('passed', 0)}/{summary.get('total', 0)}")
        print(f"🎯 Tasa de éxito: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            print("🎉 ¡PRUEBA RÁPIDA EXITOSA!")
            return True
        else:
            print("⚠️ Prueba rápida completada con advertencias")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando prueba rápida: {e}")
        return False

async def run_extreme_test():
    """Ejecuta prueba extrema de estrés"""
    print("🔥 Ejecutando prueba extrema de estrés...")
    print("⚠️ ADVERTENCIA: Esta prueba puede tardar 2 horas")
    
    confirm = input("¿Continuar con la prueba extrema? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Prueba extrema cancelada")
        return False
    
    try:
        from scripts.testing.extreme_stress_test import ExtremeStressTester
        
        tester = ExtremeStressTester()
        results = await tester.run_extreme_test()
        
        if 'error' in results:
            print(f"❌ Error en prueba extrema: {results['error']}")
            return False
        
        # Mostrar resumen
        summary = results.get('test_summary', {})
        success_rate = summary.get('success_rate', 0)
        
        print(f"\n📊 RESUMEN DE PRUEBA EXTREMA:")
        print(f"⏱️ Duración: {summary.get('duration_hours', 0):.2f} horas")
        print(f"🔄 Ciclos completados: {summary.get('cycles_completed', 0)}")
        print(f"📊 Trades generados: {summary.get('total_trades', 0)}")
        print(f"📱 Mensajes Telegram: {summary.get('total_telegram_messages', 0)}")
        print(f"🎯 Objetivos cumplidos: {summary.get('objectives_passed', 0)}/{summary.get('objectives_total', 0)}")
        print(f"✅ Tasa de éxito: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            print("🎉 ¡PRUEBA EXTREMA EXITOSA!")
            return True
        else:
            print("⚠️ Prueba extrema completada con advertencias")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando prueba extrema: {e}")
        return False

async def run_custom_test(cycles: int, duration_hours: float, symbols: list):
    """Ejecuta prueba personalizada"""
    print(f"🎯 Ejecutando prueba personalizada...")
    print(f"   🔄 Ciclos: {cycles}")
    print(f"   ⏱️ Duración: {duration_hours} horas")
    print(f"   🤖 Símbolos: {symbols}")
    
    try:
        from scripts.testing.extreme_stress_test import ExtremeStressTester
        
        # Crear tester personalizado
        tester = ExtremeStressTester()
        tester.cycles_to_test = cycles
        tester.test_duration_hours = duration_hours
        tester.symbols = symbols
        
        results = await tester.run_extreme_test()
        
        if 'error' in results:
            print(f"❌ Error en prueba personalizada: {results['error']}")
            return False
        
        # Mostrar resumen
        summary = results.get('test_summary', {})
        success_rate = summary.get('success_rate', 0)
        
        print(f"\n📊 RESUMEN DE PRUEBA PERSONALIZADA:")
        print(f"⏱️ Duración: {summary.get('duration_hours', 0):.2f} horas")
        print(f"🔄 Ciclos completados: {summary.get('cycles_completed', 0)}")
        print(f"📊 Trades generados: {summary.get('total_trades', 0)}")
        print(f"🎯 Objetivos cumplidos: {summary.get('objectives_passed', 0)}/{summary.get('objectives_total', 0)}")
        print(f"✅ Tasa de éxito: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            print("🎉 ¡PRUEBA PERSONALIZADA EXITOSA!")
            return True
        else:
            print("⚠️ Prueba personalizada completada con advertencias")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando prueba personalizada: {e}")
        return False

def show_help():
    """Muestra ayuda del sistema de pruebas"""
    print("""
📚 AYUDA - Sistema de Pruebas de Validación

🧪 TIPOS DE PRUEBAS:

1. PRUEBA RÁPIDA (--quick):
   - Duración: ~5 minutos
   - Ciclos: 5
   - Símbolos: 2 (BTCUSDT, ETHUSDT)
   - Valida: Aspectos básicos del sistema
   - Uso: python run_validation_tests.py --quick

2. PRUEBA EXTREMA (--extreme):
   - Duración: 2 horas
   - Ciclos: 24 (12 por hora)
   - Símbolos: 4 (BTCUSDT, ETHUSDT, ADAUSDT, SOLUSDT)
   - Valida: Robustez completa del sistema
   - Uso: python run_validation_tests.py --extreme

3. PRUEBA PERSONALIZADA (--custom):
   - Duración: Personalizable
   - Ciclos: Personalizable
   - Símbolos: Personalizable
   - Valida: Configuración específica
   - Uso: python run_validation_tests.py --custom --cycles 10 --duration 1.0 --symbols BTCUSDT ETHUSDT

🎯 ASPECTOS VALIDADOS:

✅ Trades Individuales:
   - Generación de trades en 1m y 5m
   - Análisis técnico con todos los timeframes
   - Uso de features e indicadores
   - Calidad de trades y scoring

✅ Mensajes de Telegram:
   - Trades individuales reportados
   - Resúmenes de ciclo
   - Formato visual con emojis
   - Rate limiting y robustez

✅ Estrategias:
   - Registro de mejores estrategias
   - Registro de peores estrategias
   - Performance por estrategia
   - Análisis de efectividad

✅ Objetivos:
   - Win rate mínimo
   - Calidad de trades
   - Uso de memoria
   - Tiempo de procesamiento
   - Robustez del sistema

✅ Robustez:
   - Funcionamiento continuo
   - Gestión de memoria
   - Recovery ante fallos
   - Performance estable

📊 MÉTRICAS DE ÉXITO:

- Prueba Rápida: 80% de validaciones exitosas
- Prueba Extrema: 80% de objetivos cumplidos
- Prueba Personalizada: 80% de objetivos cumplidos

🔧 COMANDOS ÚTILES:

# Prueba rápida
python run_validation_tests.py --quick

# Prueba extrema
python run_validation_tests.py --extreme

# Prueba personalizada
python run_validation_tests.py --custom --cycles 20 --duration 2.0 --symbols BTCUSDT ETHUSDT ADAUSDT

# Ayuda
python run_validation_tests.py --help

💡 RECOMENDACIONES:

1. Ejecutar prueba rápida primero para validar configuración
2. Ejecutar prueba extrema para validar robustez completa
3. Usar prueba personalizada para casos específicos
4. Revisar logs en logs/ para debugging
5. Configurar Telegram antes de pruebas con notificaciones
    """)

async def main():
    """Función principal del sistema de pruebas"""
    parser = argparse.ArgumentParser(
        description='Sistema de Pruebas de Validación - Bot Trading v10 Enterprise',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Comandos principales
    parser.add_argument('--quick', action='store_true', help='Ejecutar prueba rápida (5 minutos)')
    parser.add_argument('--extreme', action='store_true', help='Ejecutar prueba extrema (2 horas)')
    parser.add_argument('--custom', action='store_true', help='Ejecutar prueba personalizada')
    parser.add_argument('--help-detailed', action='store_true', help='Mostrar ayuda detallada')
    
    # Opciones para prueba personalizada
    parser.add_argument('--cycles', type=int, default=10, help='Número de ciclos para prueba personalizada')
    parser.add_argument('--duration', type=float, default=1.0, help='Duración en horas para prueba personalizada')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'], help='Símbolos para prueba personalizada')
    
    args = parser.parse_args()
    
    # Mostrar banner
    print_banner()
    
    # Mostrar ayuda detallada
    if args.help_detailed:
        show_help()
        return 0
    
    # Verificar que se especifique un tipo de prueba
    if not any([args.quick, args.extreme, args.custom]):
        print("❌ No se especificó ningún tipo de prueba")
        print("💡 Usa --help para ver las opciones disponibles")
        return 1
    
    # Ejecutar prueba seleccionada
    if args.quick:
        success = await run_quick_test()
        return 0 if success else 1
    
    elif args.extreme:
        success = await run_extreme_test()
        return 0 if success else 1
    
    elif args.custom:
        success = await run_custom_test(args.cycles, args.duration, args.symbols)
        return 0 if success else 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Pruebas interrumpidas por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
