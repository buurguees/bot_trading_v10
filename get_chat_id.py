#!/usr/bin/env python3
"""
Obtener Chat ID de Telegram
==========================

Script para obtener automáticamente el Chat ID del usuario
que envía mensajes al bot de Telegram.

Uso:
    python get_chat_id.py

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import requests
import json
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_chat_id():
    """Obtiene el Chat ID del último mensaje enviado al bot"""
    try:
        bot_token = "8422053215:AAH5hqD8472CCQyDTHfL8Zge9VXZNEJbdd8"
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        
        logger.info("🔍 Obteniendo Chat ID...")
        logger.info("📱 Envía un mensaje a @Trading_buurguees_Bot primero")
        
        response = requests.get(url)
        data = response.json()
        
        if data['ok'] and data['result']:
            # Obtener el último mensaje
            last_message = data['result'][-1]
            chat_id = last_message['message']['chat']['id']
            username = last_message['message']['from'].get('username', 'Sin username')
            first_name = last_message['message']['from'].get('first_name', 'Sin nombre')
            
            logger.info(f"✅ Chat ID encontrado: {chat_id}")
            logger.info(f"👤 Usuario: {first_name} (@{username})")
            
            # Actualizar el archivo de configuración
            update_config_file(chat_id)
            
            return chat_id
        else:
            logger.warning("⚠️ No se encontraron mensajes")
            logger.info("📱 Envía un mensaje a @Trading_buurguees_Bot y vuelve a ejecutar este script")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo Chat ID: {e}")
        return None

def update_config_file(chat_id):
    """Actualiza el archivo de configuración con el Chat ID"""
    try:
        config_file = "notifications/telegram/config.yaml"
        
        # Leer el archivo actual
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reemplazar el placeholder
        updated_content = content.replace('<YOUR_CHAT_ID>', str(chat_id))
        
        # Escribir el archivo actualizado
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"✅ Archivo de configuración actualizado: {config_file}")
        logger.info(f"🔧 Chat ID configurado: {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Error actualizando archivo de configuración: {e}")

def main():
    """Función principal"""
    print("🤖 Bot de Trading v10 - Obtener Chat ID")
    print("=" * 50)
    print()
    print("📱 INSTRUCCIONES:")
    print("1. Abre Telegram en tu móvil")
    print("2. Busca @Trading_buurguees_Bot")
    print("3. Envía cualquier mensaje al bot (ej: /start)")
    print("4. Presiona Enter aquí para continuar...")
    print()
    
    input("Presiona Enter cuando hayas enviado el mensaje...")
    
    chat_id = get_chat_id()
    
    if chat_id:
        print()
        print("🎉 ¡Chat ID obtenido exitosamente!")
        print(f"📱 Tu Chat ID es: {chat_id}")
        print()
        print("✅ El bot ahora puede enviarte mensajes")
        print("🚀 Puedes ejecutar el bot principal con: python run_bot.py")
    else:
        print()
        print("❌ No se pudo obtener el Chat ID")
        print("📱 Asegúrate de enviar un mensaje al bot primero")

if __name__ == "__main__":
    main()
