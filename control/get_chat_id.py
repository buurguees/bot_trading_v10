# Ruta: control/get_chat_id.py
#!/usr/bin/env python3
"""
Script para obtener Chat ID de Telegram
=======================================

Este script te ayuda a obtener tu Chat ID para configurar el bot de Telegram.
Sigue las instrucciones para obtener tu Chat ID único.

Uso:
    python notifications/telegram/get_chat_id.py

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import requests
import json
import time
from datetime import datetime

# Token del bot (ya configurado)
BOT_TOKEN = "8422053215:AAH5hqD8472CCQyDTHfL8Zge9VXZNEJbdd8"

def get_chat_id():
    """Obtiene el Chat ID del usuario"""
    print("🤖 Obteniendo Chat ID para Trading Bot v10")
    print("=" * 50)
    print()
    print("📱 INSTRUCCIONES:")
    print("1. Abre Telegram en tu móvil o computadora")
    print("2. Busca el bot: @Trading_buurguees_Bot")
    print("3. Inicia una conversación enviando: /start")
    print("4. Espera unos segundos y presiona Enter aquí...")
    print()
    
    input("Presiona Enter después de enviar /start al bot...")
    
    print("\n🔍 Buscando tu Chat ID...")
    
    # URL de la API de Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    try:
        # Hacer petición a la API
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('ok'):
            print("❌ Error en la respuesta de la API")
            print(f"Descripción: {data.get('description', 'Desconocido')}")
            return None
        
        updates = data.get('result', [])
        
        if not updates:
            print("❌ No se encontraron mensajes recientes")
            print("Asegúrate de haber enviado /start al bot primero")
            return None
        
        # Buscar el Chat ID más reciente
        latest_update = updates[-1]
        message = latest_update.get('message', {})
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        
        if not chat_id:
            print("❌ No se pudo extraer el Chat ID del mensaje")
            return None
        
        # Información del usuario
        user = message.get('from', {})
        first_name = user.get('first_name', 'Usuario')
        last_name = user.get('last_name', '')
        username = user.get('username', 'Sin username')
        
        print("✅ ¡Chat ID encontrado!")
        print()
        print("📋 INFORMACIÓN:")
        print(f"• Nombre: {first_name} {last_name}".strip())
        print(f"• Username: @{username}" if username != 'Sin username' else "• Username: No disponible")
        print(f"• Chat ID: {chat_id}")
        print()
        print("🔧 CONFIGURACIÓN:")
        print("Ahora puedes actualizar tu archivo de configuración:")
        print(f"notifications/telegram/config.yaml")
        print()
        print("Reemplaza esta línea:")
        print('  chat_id: "<YOUR_CHAT_ID>"')
        print("Con:")
        print(f'  chat_id: "{chat_id}"')
        print()
        print("✅ ¡Configuración completada!")
        
        return chat_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        print("Verifica tu conexión a internet")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error decodificando respuesta: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def test_bot_connection():
    """Prueba la conexión con el bot"""
    print("🧪 Probando conexión con el bot...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result', {})
            print("✅ Conexión exitosa!")
            print(f"• Bot: {bot_info.get('first_name', 'N/A')}")
            print(f"• Username: @{bot_info.get('username', 'N/A')}")
            print(f"• ID: {bot_info.get('id', 'N/A')}")
            return True
        else:
            print("❌ Error en la respuesta del bot")
            return False
            
    except Exception as e:
        print(f"❌ Error conectando con el bot: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Trading Bot v10 - Configuración de Telegram")
    print("=" * 50)
    print()
    
    # Probar conexión primero
    if not test_bot_connection():
        print("\n❌ No se pudo conectar con el bot")
        print("Verifica que el token sea correcto")
        return
    
    print()
    
    # Obtener Chat ID
    chat_id = get_chat_id()
    
    if chat_id:
        print("\n🎉 ¡Configuración completada exitosamente!")
        print("Ahora puedes usar el bot de Telegram con tu Trading Bot v10")
    else:
        print("\n❌ No se pudo obtener el Chat ID")
        print("Intenta nuevamente siguiendo las instrucciones")

if __name__ == "__main__":
    main()
