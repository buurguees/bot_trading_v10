#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test directo de comandos de Telegram
"""

import asyncio
import logging
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_commands():
    """Test de comandos de Telegram"""
    try:
        print("🧪 Test de Comandos de Telegram")
        print("=" * 50)
        
        # Importar módulos
        from control.telegram_bot import TelegramBot
        from control.handlers import Handlers
        
        # Crear bot
        bot = TelegramBot()
        if not bot.enabled:
            print("❌ Bot deshabilitado")
            return
        
        # Crear handlers
        handlers = Handlers(bot)
        
        # Simular Update y Context
        class MockUpdate:
            def __init__(self, command="", chat_id="937027893"):
                self.message = MockMessage(command, chat_id)
                self.effective_chat = MockChat(chat_id)
        
        class MockMessage:
            def __init__(self, text, chat_id):
                self.text = text
                self.chat_id = int(chat_id)
            
            async def reply_text(self, text, parse_mode=None):
                print(f"📱 Respuesta: {text[:100]}...")
                return True
        
        class MockChat:
            def __init__(self, chat_id):
                self.id = int(chat_id)
        
        class MockContext:
            def __init__(self):
                self.bot = bot
        
        # Test de comandos principales
        commands_to_test = [
            ("/start", "start_command"),
            ("/help", "help_command"),
            ("/status", "status_command"),
            ("/safe_download", "safe_download_command"),
            ("/metrics", "metrics_command")
        ]
        
        context = MockContext()
        
        for command, handler_name in commands_to_test:
            print(f"\n🔍 Probando {command}...")
            try:
                update = MockUpdate(command)
                handler = getattr(handlers, handler_name)
                await handler(update, context)
                print(f"   ✅ {command} ejecutado correctamente")
            except Exception as e:
                print(f"   ❌ Error en {command}: {e}")
        
        print("\n✅ Test de comandos completado")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_telegram_commands())
