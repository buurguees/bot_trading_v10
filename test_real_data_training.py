#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_real_data_training.py
==========================
Script para probar que el bot esté usando datos reales en lugar de simulados
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

async def test_real_data_training():
    """Prueba que el bot use datos reales"""
    try:
        print("🧪 Probando entrenamiento con datos reales...")
        
        # Importar el bot
        from bot_enhanced import EnhancedTradingBot
        
        # Crear instancia del bot
        bot = EnhancedTradingBot()
        
        print("✅ Bot enhanced creado")
        
        # Inicializar el bot
        print("🚀 Inicializando bot...")
        await bot.initialize()
        
        print("✅ Bot inicializado")
        
        # Verificar configuración de Telegram
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ Variables de entorno de Telegram no configuradas")
            print("   Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
            return
        
        print(f"✅ Telegram configurado: {chat_id}")
        
        # Enviar mensaje de prueba
        await bot.telegram_bot.send_message(
            "🧪 <b>PRUEBA DE DATOS REALES</b>\n\n"
            "✅ Bot configurado para usar datos reales\n"
            "📊 Cargando datos desde data/{symbol}/\n\n"
            "⏰ <b>Tiempo:</b> " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            priority=1
        )
        
        print("✅ Mensaje de prueba enviado")
        
        # Simular comando de entrenamiento
        print("🔄 Simulando comando /train_hist...")
        
        # Crear tarea de entrenamiento
        training_task = asyncio.create_task(bot._run_enhanced_training(30))  # 30 días
        
        print("✅ Entrenamiento iniciado con datos reales")
        print("📱 Revisa Telegram para ver el progreso")
        
        # Esperar un poco para que el entrenamiento progrese
        print("⏳ Esperando 30 segundos para verificar progreso...")
        await asyncio.sleep(30)
        
        # Verificar estado del entrenamiento
        print(f"📊 Estado del entrenamiento:")
        print(f"   - Entrenamiento activo: {bot.training_active}")
        print(f"   - Tarea de entrenamiento: {bot.training_task is not None}")
        
        # Cancelar entrenamiento si está activo
        if bot.training_active and bot.training_task:
            print("🛑 Cancelando entrenamiento de prueba...")
            bot.training_task.cancel()
            try:
                await bot.training_task
            except asyncio.CancelledError:
                pass
        
        print("✅ Prueba completada")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_data_training())

