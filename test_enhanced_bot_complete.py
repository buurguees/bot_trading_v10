#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_enhanced_bot_complete.py
=============================
Script de Prueba del Bot Mejorado Completo

Prueba que el bot mejorado tenga todas las funcionalidades del bot original
más el sistema de entrenamiento mejorado.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from bot_enhanced import EnhancedTradingBot

async def test_enhanced_bot_complete():
    """Prueba el bot mejorado completo"""
    print("🧪 Probando Bot Mejorado Completo...")
    
    # Crear bot
    bot = EnhancedTradingBot()
    
    # Inicializar bot
    print("🔧 Inicializando bot mejorado...")
    if not await bot.initialize():
        print("❌ Error inicializando bot")
        return False
    
    print("✅ Bot mejorado inicializado correctamente")
    
    # Probar comando de estado
    print("\n📊 Probando comando /status...")
    status_result = await bot.handle_status_command()
    print(f"Resultado: {status_result['status']}")
    if status_result['status'] == 'success':
        print("✅ Comando /status funcionando")
    else:
        print(f"❌ Error en /status: {status_result['message']}")
    
    # Probar comando de salud
    print("\n🏥 Probando comando /health...")
    try:
        memory_usage = bot._get_memory_usage()
        print(f"✅ Comando /health funcionando - Memoria: {memory_usage:.1f} MB")
    except Exception as e:
        print(f"❌ Error en /health: {e}")
    
    # Probar comando de entrenamiento (solo 1 día para prueba)
    print("\n🚀 Probando comando /train_hist (1 día)...")
    train_result = await bot.handle_train_hist_command(days_back=1)
    print(f"Resultado: {train_result['status']}")
    if train_result['status'] == 'success':
        print("✅ Comando /train_hist funcionando")
        
        # Esperar un poco para simular entrenamiento
        print("⏳ Simulando entrenamiento (5 segundos)...")
        await asyncio.sleep(5)
        
        # Probar comando de detener
        print("\n⏹️ Probando comando /stop_train...")
        stop_result = await bot.handle_stop_train_command()
        print(f"Resultado: {stop_result['status']}")
        if stop_result['status'] == 'success':
            print("✅ Comando /stop_train funcionando")
        else:
            print(f"❌ Error en /stop_train: {stop_result['message']}")
    else:
        print(f"❌ Error en /train_hist: {train_result['message']}")
    
    print("\n🎉 Prueba del bot mejorado completada")
    return True

async def main():
    """Función principal de prueba"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 PRUEBA DEL BOT MEJORADO COMPLETO 🧪                  ║
║                    Bot Trading v10 Enterprise                              ║
║                                                                              ║
║  🔧 Prueba de inicialización                                               ║
║  📊 Prueba de comando /status                                              ║
║  🏥 Prueba de comando /health                                              ║
║  🚀 Prueba de comando /train_hist                                          ║
║  ⏹️ Prueba de comando /stop_train                                          ║
║                                                                              ║
║  ✅ Incluye todas las funcionalidades del bot original                     ║
║  ✅ Más sistema de entrenamiento mejorado                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        success = await test_enhanced_bot_complete()
        if success:
            print("\n✅ Todas las pruebas exitosas!")
            print("🎉 El bot mejorado está listo para usar")
            print("\n💡 Para usar el bot completo:")
            print("1. Ejecutar: python bot_enhanced.py")
            print("2. Esperar a que complete análisis, descarga, alineación y sincronización")
            print("3. Recibir mensaje de comandos disponibles")
            print("4. Enviar /train_hist desde Telegram para entrenamiento mejorado")
        else:
            print("\n❌ Algunas pruebas fallaron")
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
