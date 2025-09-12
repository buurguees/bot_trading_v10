#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de diagnóstico para Telegram Bot
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_telegram_bot():
    """Test del bot de Telegram"""
    try:
        print("🔍 Diagnóstico del Bot de Telegram")
        print("=" * 50)
        
        # 1. Verificar variables de entorno
        print("\n1. Variables de entorno:")
        bot_token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID') or os.getenv('CHAT_ID')
        
        print(f"   BOT_TOKEN: {'✅' if bot_token else '❌'} {bot_token[:10] + '...' if bot_token else 'No encontrado'}")
        print(f"   CHAT_ID: {'✅' if chat_id else '❌'} {chat_id}")
        
        # 2. Verificar configuración unificada
        print("\n2. Configuración unificada:")
        from config.unified_config import get_config_manager
        config = get_config_manager()
        
        telegram_config = config.get_telegram_config()
        print(f"   Telegram config: {telegram_config}")
        
        # 3. Verificar control config
        print("\n3. Control config:")
        from control.config import control_config
        control_telegram = control_config.telegram
        print(f"   Control telegram: {control_telegram}")
        
        # 4. Crear bot de Telegram
        print("\n4. Crear bot de Telegram:")
        from control.telegram_bot import TelegramBot
        
        bot = TelegramBot()
        print(f"   Bot habilitado: {'✅' if bot.enabled else '❌'}")
        print(f"   Bot token: {'✅' if bot.bot_token else '❌'}")
        print(f"   Chat ID: {'✅' if bot.chat_id else '❌'}")
        
        if not bot.enabled:
            print("   ❌ Bot deshabilitado - revisar configuración")
            return False
        
        # 5. Test de envío de mensaje
        print("\n5. Test de envío de mensaje:")
        test_message = "🧪 Test de diagnóstico del bot"
        success = await bot.send_message(test_message)
        print(f"   Envío: {'✅' if success else '❌'}")
        
        # 6. Test de handlers
        print("\n6. Test de handlers:")
        from control.handlers import Handlers
        handlers = Handlers(bot)
        
        # Verificar algunos handlers importantes
        important_handlers = ['start_command', 'help_command', 'status_command', 'safe_download_command']
        for handler_name in important_handlers:
            has_handler = hasattr(handlers, handler_name)
            print(f"   {handler_name}: {'✅' if has_handler else '❌'}")
        
        print("\n✅ Diagnóstico completado")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())
