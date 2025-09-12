#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de envío de mensaje directo a Telegram
"""

import asyncio
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

async def test_send_message():
    """Test de envío de mensaje"""
    try:
        from telegram import Bot
        
        bot_token = os.getenv('BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ Faltan credenciales de Telegram")
            return
        
        bot = Bot(token=bot_token)
        
        # Enviar mensaje de prueba
        message = """
🧪 <b>Test de Conectividad</b>

✅ Bot funcionando correctamente
📱 Comandos disponibles
🔧 Sistema operativo

Envía /start para comenzar
        """
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        
        print("✅ Mensaje de prueba enviado correctamente")
        
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")

if __name__ == "__main__":
    asyncio.run(test_send_message())
