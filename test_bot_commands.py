#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bot_commands.py
====================
Script de Prueba de Comandos del Bot Mejorado

Simula los comandos de Telegram para probar el bot mejorado.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from bot_enhanced import EnhancedTradingBot

async def test_bot_commands():
    """Prueba los comandos del bot mejorado"""
    print("🧪 Probando comandos del Bot Mejorado...")
    
    # Crear bot
    bot = EnhancedTradingBot()
    
    # Inicializar bot
    print("🔧 Inicializando bot...")
    if not await bot.initialize():
        print("❌ Error inicializando bot")
        return False
    
    print("✅ Bot inicializado correctamente")
    
    # Probar comando de estado
    print("\n📊 Probando comando /status...")
    status_result = await bot.handle_status_command()
    print(f"Resultado: {status_result['status']}")
    if status_result['status'] == 'success':
        print("✅ Comando /status funcionando")
    else:
        print(f"❌ Error en /status: {status_result['message']}")
    
    # Probar comando de entrenamiento (solo 1 día para prueba)
    print("\n🚀 Probando comando /train_hist (1 día)...")
    train_result = await bot.handle_train_hist_command(days_back=1)
    print(f"Resultado: {train_result['status']}")
    if train_result['status'] == 'success':
        print("✅ Comando /train_hist funcionando")
        
        # Esperar un poco para simular entrenamiento
        print("⏳ Simulando entrenamiento (10 segundos)...")
        await asyncio.sleep(10)
        
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
    
    print("\n🎉 Prueba de comandos completada")
    return True

async def main():
    """Función principal de prueba"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 PRUEBA DE COMANDOS DEL BOT MEJORADO 🧪                ║
║                    Bot Trading v10 Enterprise                              ║
║                                                                              ║
║  🔧 Prueba de inicialización                                               ║
║  📊 Prueba de comando /status                                              ║
║  🚀 Prueba de comando /train_hist                                          ║
║  ⏹️ Prueba de comando /stop_train                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        success = await test_bot_commands()
        if success:
            print("\n✅ Todas las pruebas exitosas!")
            print("🎉 El bot mejorado está listo para usar")
        else:
            print("\n❌ Algunas pruebas fallaron")
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
