#!/usr/bin/env python3
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
        print("\n⏹️ Bot detenido por el usuario")
        return 0
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
