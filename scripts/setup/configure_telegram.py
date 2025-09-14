#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/setup/configure_telegram.py
===================================
Script de Configuración de Telegram para Sistema Mejorado

Configura fácilmente las credenciales de Telegram para el sistema de entrenamiento mejorado.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def configure_telegram():
    """Configura las credenciales de Telegram"""
    print("🤖 Configuración de Telegram para Sistema Mejorado")
    print("=" * 50)
    
    # Verificar si ya existe configuración
    env_file = Path(".env")
    if env_file.exists():
        print("📄 Archivo .env encontrado. ¿Deseas actualizar la configuración? (y/n): ", end="")
        if input().lower() != 'y':
            print("❌ Configuración cancelada")
            return False
    
    # Solicitar credenciales
    print("\n📱 Ingresa las credenciales de Telegram:")
    print("(Puedes obtenerlas de @BotFather en Telegram)")
    
    bot_token = input("🔑 Bot Token: ").strip()
    if not bot_token:
        print("❌ Bot Token es requerido")
        return False
    
    chat_id = input("💬 Chat ID: ").strip()
    if not chat_id:
        print("❌ Chat ID es requerido")
        return False
    
    # Validar formato básico
    if not bot_token.count(':') == 1:
        print("⚠️  Advertencia: El Bot Token parece tener un formato incorrecto")
        print("   Debería ser algo como: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
    
    if not chat_id.lstrip('-').isdigit():
        print("⚠️  Advertencia: El Chat ID parece tener un formato incorrecto")
        print("   Debería ser un número como: -1001234567890")
    
    # Crear/actualizar archivo .env
    env_content = f"""# Bot Trading v10 Enterprise - Configuración de Telegram
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}

# Configuración adicional
TELEGRAM_RATE_LIMIT_DELAY=0.1
TELEGRAM_MAX_MESSAGE_LENGTH=4096
TELEGRAM_ENABLE_INDIVIDUAL_TRADES=true
TELEGRAM_ENABLE_CYCLE_SUMMARIES=true
TELEGRAM_ENABLE_ALERTS=true
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"\n✅ Configuración guardada en {env_file.absolute()}")
        
        # Crear archivo de ejemplo para referencia
        example_file = Path("config/telegram_example.env")
        example_file.parent.mkdir(exist_ok=True)
        
        with open(example_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"📄 Archivo de ejemplo creado en {example_file.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando configuración: {e}")
        return False

def test_telegram_connection():
    """Prueba la conexión con Telegram"""
    print("\n🧪 Probando conexión con Telegram...")
    
    try:
        from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
        
        # Cargar configuración desde .env
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ No se encontraron credenciales de Telegram en .env")
            return False
        
        # Crear configuración
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        # Crear reporter
        reporter = TelegramTradeReporter(config)
        
        # Enviar mensaje de prueba
        import asyncio
        
        async def send_test():
            return await reporter.send_performance_alert(
                "TEST",
                "🧪 Mensaje de prueba del Sistema Mejorado\n\n✅ Conexión exitosa con Telegram!",
                "INFO"
            )
        
        result = asyncio.run(send_test())
        
        if result:
            print("✅ Conexión con Telegram exitosa!")
            print("📱 Revisa tu chat de Telegram para ver el mensaje de prueba")
            return True
        else:
            print("❌ Error enviando mensaje de prueba")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        print("💡 Asegúrate de que todas las dependencias estén instaladas")
        return False
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")
        return False

def show_telegram_help():
    """Muestra ayuda para obtener credenciales de Telegram"""
    print("\n📚 Cómo obtener credenciales de Telegram:")
    print("=" * 40)
    print("1. Abre Telegram y busca @BotFather")
    print("2. Envía /newbot para crear un nuevo bot")
    print("3. Sigue las instrucciones para darle nombre a tu bot")
    print("4. Copia el Bot Token que te proporciona")
    print("5. Para obtener el Chat ID:")
    print("   - Agrega tu bot al chat/grupo")
    print("   - Envía un mensaje al bot")
    print("   - Visita: https://api.telegram.org/bot<BOT_TOKEN>/getUpdates")
    print("   - Busca 'chat':{'id': -1001234567890} en la respuesta")
    print("   - El número es tu Chat ID")

def main():
    """Función principal"""
    print("🚀 Configurador de Telegram - Bot Trading v10 Enterprise")
    print("=" * 60)
    
    while True:
        print("\n📋 Opciones disponibles:")
        print("1. Configurar credenciales de Telegram")
        print("2. Probar conexión con Telegram")
        print("3. Mostrar ayuda para obtener credenciales")
        print("4. Salir")
        
        choice = input("\n🔢 Selecciona una opción (1-4): ").strip()
        
        if choice == '1':
            if configure_telegram():
                print("\n✅ Configuración completada exitosamente!")
            else:
                print("\n❌ Error en la configuración")
        
        elif choice == '2':
            test_telegram_connection()
        
        elif choice == '3':
            show_telegram_help()
        
        elif choice == '4':
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("\n❌ Opción inválida. Por favor selecciona 1-4.")

if __name__ == "__main__":
    main()
