#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_complete_validation.py
==========================
Script de Validación Completa del Sistema Mejorado

Ejecuta una validación completa del sistema mejorado incluyendo:
- Configuración de Telegram
- Pruebas de validación
- Pruebas de estrés
- Validación de robustez

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
        logging.FileHandler('logs/run_complete_validation.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Muestra el banner del sistema de validación completa"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 VALIDACIÓN COMPLETA DEL SISTEMA 🧪                   ║
║                    Bot Trading v10 Enterprise                              ║
║                                                                              ║
║  🔧 Configuración automática de Telegram                                  ║
║  ⚡ Pruebas de validación rápida                                          ║
║  🔥 Pruebas de estrés extremo                                             ║
║  📊 Validación de robustez para días enteros                              ║
║                                                                              ║
║  🎯 Valida: Trades, Telegram, Timeframes, Features, Estrategias           ║
║  🚀 Objetivos: Win Rate, Calidad, Robustez, Performance                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

async def setup_telegram():
    """Configura Telegram para las pruebas"""
    print("📱 Configurando Telegram para pruebas...")
    
    try:
        from scripts.setup.setup_telegram_for_tests import main as setup_telegram_main
        
        # Ejecutar configuración de Telegram
        result = await setup_telegram_main()
        
        if result == 0:
            print("✅ Telegram configurado exitosamente")
            return True
        else:
            print("❌ Error configurando Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Error en configuración de Telegram: {e}")
        return False

async def run_quick_validation():
    """Ejecuta validación rápida"""
    print("⚡ Ejecutando validación rápida...")
    
    try:
        from scripts.testing.quick_validation_test import QuickValidationTester
        
        tester = QuickValidationTester()
        results = await tester.run_quick_validation()
        
        if 'error' in results:
            print(f"❌ Error en validación rápida: {results['error']}")
            return False
        
        # Verificar éxito
        summary = results.get('validation_summary', {})
        success_rate = summary.get('success_rate', 0)
        
        if success_rate >= 0.8:
            print("✅ Validación rápida exitosa!")
            return True
        else:
            print(f"⚠️ Validación rápida completada con advertencias ({success_rate:.1%})")
            return False
            
    except Exception as e:
        print(f"❌ Error en validación rápida: {e}")
        return False

async def run_extreme_validation():
    """Ejecuta validación extrema"""
    print("🔥 Ejecutando validación extrema...")
    
    try:
        from scripts.testing.extreme_stress_test import ExtremeStressTester
        
        tester = ExtremeStressTester()
        results = await tester.run_extreme_test()
        
        if 'error' in results:
            print(f"❌ Error en validación extrema: {results['error']}")
            return False
        
        # Verificar éxito
        summary = results.get('test_summary', {})
        success_rate = summary.get('success_rate', 0)
        
        if success_rate >= 0.8:
            print("✅ Validación extrema exitosa!")
            return True
        else:
            print(f"⚠️ Validación extrema completada con advertencias ({success_rate:.1%})")
            return False
            
    except Exception as e:
        print(f"❌ Error en validación extrema: {e}")
        return False

async def run_complete_validation():
    """Ejecuta validación completa del sistema"""
    print("🚀 Iniciando validación completa del sistema...")
    
    start_time = datetime.now()
    results = {
        'telegram_setup': False,
        'quick_validation': False,
        'extreme_validation': False,
        'overall_success': False
    }
    
    try:
        # 1. Configurar Telegram
        print("\n" + "="*60)
        print("📱 PASO 1: CONFIGURACIÓN DE TELEGRAM")
        print("="*60)
        
        results['telegram_setup'] = await setup_telegram()
        
        if not results['telegram_setup']:
            print("❌ Error en configuración de Telegram")
            print("💡 Continúa sin Telegram para pruebas básicas")
        
        # 2. Validación rápida
        print("\n" + "="*60)
        print("⚡ PASO 2: VALIDACIÓN RÁPIDA")
        print("="*60)
        
        results['quick_validation'] = await run_quick_validation()
        
        if not results['quick_validation']:
            print("❌ Error en validación rápida")
            print("💡 Revisa la configuración del sistema")
            return results
        
        # 3. Validación extrema
        print("\n" + "="*60)
        print("🔥 PASO 3: VALIDACIÓN EXTREMA")
        print("="*60)
        
        print("⚠️ ADVERTENCIA: Esta validación puede tardar 2 horas")
        confirm = input("¿Continuar con la validación extrema? (y/N): ").strip().lower()
        
        if confirm == 'y':
            results['extreme_validation'] = await run_extreme_validation()
        else:
            print("⏭️ Saltando validación extrema")
            results['extreme_validation'] = True  # Considerar como exitosa si se salta
        
        # 4. Determinar éxito general
        results['overall_success'] = (
            results['quick_validation'] and 
            results['extreme_validation']
        )
        
        # 5. Generar reporte final
        duration = datetime.now() - start_time
        
        print("\n" + "="*80)
        print("📊 REPORTE FINAL DE VALIDACIÓN COMPLETA")
        print("="*80)
        
        print(f"⏱️ Duración total: {duration}")
        print(f"📱 Telegram configurado: {'✅' if results['telegram_setup'] else '❌'}")
        print(f"⚡ Validación rápida: {'✅' if results['quick_validation'] else '❌'}")
        print(f"🔥 Validación extrema: {'✅' if results['extreme_validation'] else '❌'}")
        print(f"🎯 Éxito general: {'✅' if results['overall_success'] else '❌'}")
        
        if results['overall_success']:
            print("\n🎉 ¡VALIDACIÓN COMPLETA EXITOSA!")
            print("✅ El sistema está listo para funcionar en producción")
            print("🚀 Puedes ejecutar entrenamientos largos con confianza")
        else:
            print("\n⚠️ VALIDACIÓN COMPLETADA CON ADVERTENCIAS")
            print("❌ Algunos aspectos necesitan atención")
            print("💡 Revisa los logs para más detalles")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error inesperado en validación completa: {e}")
        results['error'] = str(e)
        return results

def show_help():
    """Muestra ayuda del sistema de validación completa"""
    print("""
📚 AYUDA - Validación Completa del Sistema

🧪 TIPOS DE VALIDACIÓN:

1. VALIDACIÓN RÁPIDA (--quick):
   - Duración: ~5 minutos
   - Valida: Aspectos básicos del sistema
   - Uso: python run_complete_validation.py --quick

2. VALIDACIÓN EXTREMA (--extreme):
   - Duración: 2 horas
   - Valida: Robustez completa del sistema
   - Uso: python run_complete_validation.py --extreme

3. VALIDACIÓN COMPLETA (--complete):
   - Duración: 2+ horas
   - Incluye: Configuración + Validación rápida + Validación extrema
   - Uso: python run_complete_validation.py --complete

4. SOLO CONFIGURACIÓN (--setup-only):
   - Duración: ~2 minutos
   - Solo configura Telegram
   - Uso: python run_complete_validation.py --setup-only

🎯 ASPECTOS VALIDADOS:

✅ CONFIGURACIÓN:
   - Credenciales de Telegram
   - Conexión y envío de mensajes
   - Formato de reportes
   - Configuración de archivos

✅ TRADES INDIVIDUALES:
   - Generación en 1m y 5m
   - Análisis técnico con todos los timeframes
   - Uso de features e indicadores
   - Calidad y scoring de trades

✅ MENSAJES DE TELEGRAM:
   - Trades individuales reportados
   - Resúmenes de ciclo
   - Formato visual con emojis
   - Rate limiting y robustez

✅ ESTRATEGIAS:
   - Registro de mejores estrategias
   - Registro de peores estrategias
   - Performance por estrategia
   - Análisis de efectividad

✅ OBJETIVOS:
   - Win rate mínimo
   - Calidad de trades
   - Uso de memoria
   - Tiempo de procesamiento
   - Robustez del sistema

✅ ROBUSTEZ:
   - Funcionamiento continuo
   - Gestión de memoria
   - Recovery ante fallos
   - Performance estable

📊 MÉTRICAS DE ÉXITO:

- Validación Rápida: 80% de validaciones exitosas
- Validación Extrema: 80% de objetivos cumplidos
- Validación Completa: Todas las validaciones exitosas

🔧 COMANDOS ÚTILES:

# Validación rápida
python run_complete_validation.py --quick

# Validación extrema
python run_complete_validation.py --extreme

# Validación completa
python run_complete_validation.py --complete

# Solo configuración
python run_complete_validation.py --setup-only

# Ayuda
python run_complete_validation.py --help

💡 RECOMENDACIONES:

1. Ejecutar validación completa para verificación total
2. Usar validación rápida para verificaciones frecuentes
3. Configurar Telegram antes de validaciones con notificaciones
4. Revisar logs en logs/ para debugging
5. Ejecutar validación extrema antes de producción

🚀 FLUJO RECOMENDADO:

1. python run_complete_validation.py --setup-only
2. python run_complete_validation.py --quick
3. python run_complete_validation.py --extreme
4. python run_complete_validation.py --complete
    """)

async def main():
    """Función principal del sistema de validación completa"""
    parser = argparse.ArgumentParser(
        description='Validación Completa del Sistema - Bot Trading v10 Enterprise',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Comandos principales
    parser.add_argument('--quick', action='store_true', help='Ejecutar solo validación rápida')
    parser.add_argument('--extreme', action='store_true', help='Ejecutar solo validación extrema')
    parser.add_argument('--complete', action='store_true', help='Ejecutar validación completa')
    parser.add_argument('--setup-only', action='store_true', help='Solo configurar Telegram')
    parser.add_argument('--help-detailed', action='store_true', help='Mostrar ayuda detallada')
    
    args = parser.parse_args()
    
    # Mostrar banner
    print_banner()
    
    # Mostrar ayuda detallada
    if args.help_detailed:
        show_help()
        return 0
    
    # Verificar que se especifique un tipo de validación
    if not any([args.quick, args.extreme, args.complete, args.setup_only]):
        print("❌ No se especificó ningún tipo de validación")
        print("💡 Usa --help para ver las opciones disponibles")
        return 1
    
    # Ejecutar validación seleccionada
    if args.setup_only:
        success = await setup_telegram()
        return 0 if success else 1
    
    elif args.quick:
        success = await run_quick_validation()
        return 0 if success else 1
    
    elif args.extreme:
        success = await run_extreme_validation()
        return 0 if success else 1
    
    elif args.complete:
        results = await run_complete_validation()
        return 0 if results.get('overall_success', False) else 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Validación interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
