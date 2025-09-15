#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_telegram_polling.py
=======================
Script de Corrección de Errores de Telegram Polling

Corrige los errores de timeout y manejo de sesiones en el bot de Telegram.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import os
import sys
from pathlib import Path

def fix_telegram_polling():
    """Corrige el método de polling de Telegram"""
    print("🔧 Corrigiendo método de polling de Telegram...")
    
    telegram_bot_file = Path("control/telegram_bot.py")
    if not telegram_bot_file.exists():
        print("❌ Archivo control/telegram_bot.py no encontrado")
        return False
    
    try:
        content = telegram_bot_file.read_text(encoding='utf-8')
        
        # Reemplazar el método start_polling problemático
        old_method = """    async def start_polling(self):
        \"\"\"Iniciar polling del bot con manejo robusto de errores\"\"\"
        try:
            logger.info("🔄 Iniciando polling de Telegram...")
            
            # ENVIAR MENSAJE DE INICIO (conectando)
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\\n\\n"
                    "✅ Sistema iniciado\\n"
                    "🔄 Conectando con exchange mientras se descargan datos..."
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")
            
            # INICIAR POLLING CON MANEJO DE TIMEOUT
            await self.application.initialize()
            await self.application.start()
            
            # Configurar polling con timeout más largo y manejo de errores
            await self.application.updater.start_polling(
                timeout=60,  # 60 segundos de timeout
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                pool_timeout=60,
                drop_pending_updates=True  # Ignorar actualizaciones pendientes
            )
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            raise"""
        
        new_method = """    async def start_polling(self):
        \"\"\"Iniciar polling del bot con manejo robusto de errores\"\"\"
        try:
            logger.info("🔄 Iniciando polling de Telegram...")
            
            # ENVIAR MENSAJE DE INICIO (conectando)
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\\n\\n"
                    "✅ Sistema iniciado\\n"
                    "🔄 Conectando con exchange mientras se descargan datos..."
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")
            
            # INICIAR POLLING CON MANEJO DE TIMEOUT
            await self.application.initialize()
            await self.application.start()
            
            # Configurar polling con timeout más corto y reintentos
            try:
                await self.application.updater.start_polling(
                    timeout=30,  # 30 segundos de timeout
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                    pool_timeout=30,
                    drop_pending_updates=True,  # Ignorar actualizaciones pendientes
                    allowed_updates=["message", "callback_query"]  # Solo mensajes y callbacks
                )
                
                logger.info("✅ Bot de Telegram funcionando correctamente")
                
                # Mantener el bot activo
                while True:
                    await asyncio.sleep(1)
                    
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout en polling de Telegram, reintentando...")
                await asyncio.sleep(5)
                await self.start_polling()  # Reintentar
                
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            # No hacer raise para evitar que el bot se detenga
            logger.warning("⚠️ Continuando sin Telegram - el bot funcionará sin interfaz de chat")"""
        
        if old_method in content:
            content = content.replace(old_method, new_method)
            telegram_bot_file.write_text(content, encoding='utf-8')
            print("✅ Método start_polling corregido")
        else:
            print("⚠️ Método start_polling no encontrado, creando versión mejorada...")
            
            # Agregar método mejorado al final de la clase
            if "class TelegramBot:" in content:
                # Encontrar el final de la clase
                lines = content.split('\n')
                class_end = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('def ') and i > 0:
                        class_end = i
                        break
                
                if class_end > 0:
                    # Insertar método mejorado
                    improved_method = '''
    async def start_polling_improved(self):
        """Versión mejorada del polling con manejo de errores"""
        try:
            logger.info("🔄 Iniciando polling de Telegram (versión mejorada)...")
            
            # ENVIAR MENSAJE DE INICIO
            try:
                await self.send_message(
                    "🚀 <b>Bot Trading v10 Enterprise</b>\\n\\n"
                    "✅ Sistema iniciado\\n"
                    "🔄 Conectando con exchange..."
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")
            
            # INICIAR POLLING CON MANEJO DE TIMEOUT
            await self.application.initialize()
            await self.application.start()
            
            # Configurar polling con timeout más corto
            await self.application.updater.start_polling(
                timeout=30,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info("✅ Bot de Telegram funcionando correctamente")
            
            # Mantener el bot activo
            while True:
                await asyncio.sleep(1)
                
        except asyncio.TimeoutError:
            logger.warning("⚠️ Timeout en polling, reintentando...")
            await asyncio.sleep(5)
            await self.start_polling_improved()
            
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
            logger.warning("⚠️ Continuando sin Telegram")
'''
                    
                    lines.insert(class_end, improved_method)
                    content = '\n'.join(lines)
                    telegram_bot_file.write_text(content, encoding='utf-8')
                    print("✅ Método start_polling_improved agregado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo polling: {e}")
        return False

def create_bot_launcher():
    """Crea un script de lanzamiento del bot mejorado"""
    print("🔧 Creando script de lanzamiento del bot mejorado...")
    
    launcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
launch_bot.py
=============
Script de Lanzamiento del Bot Mejorado

Lanza el bot con el sistema de entrenamiento mejorado integrado.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    """Función principal de lanzamiento"""
    print("🚀 Lanzando Bot Trading v10 Enterprise Mejorado...")
    
    try:
        from bot_enhanced import EnhancedTradingBot
        
        # Crear bot mejorado
        bot = EnhancedTradingBot()
        
        # Inicializar y ejecutar
        if await bot.initialize():
            await bot.start()
        else:
            print("❌ Error inicializando bot mejorado")
            return 1
            
    except KeyboardInterrupt:
        print("\\n⏹️ Bot detenido por el usuario")
        return 0
    except Exception as e:
        print(f"\\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''
    
    try:
        with open("launch_bot.py", "w", encoding="utf-8") as f:
            f.write(launcher_content)
        print("✅ launch_bot.py creado")
        return True
    except Exception as e:
        print(f"❌ Error creando launcher: {e}")
        return False

def main():
    """Función principal de corrección"""
    print("🔧 Iniciando corrección de errores de Telegram...")
    
    # Corregir polling
    if fix_telegram_polling():
        print("✅ Polling de Telegram corregido")
    else:
        print("❌ Error corrigiendo polling")
    
    # Crear launcher
    if create_bot_launcher():
        print("✅ Script de lanzamiento creado")
    else:
        print("❌ Error creando launcher")
    
    print("\\n💡 Próximos pasos:")
    print("1. Usar el bot mejorado: python launch_bot.py")
    print("2. O usar directamente: python bot_enhanced.py")
    print("3. El bot mejorado tiene el sistema de entrenamiento integrado")
    print("4. Comandos disponibles: /train_hist, /status, /stop_train")

if __name__ == "__main__":
    main()
