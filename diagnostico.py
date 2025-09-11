#!/usr/bin/env python3
"""Script de Diagnóstico Automático"""

import os
from pathlib import Path
import importlib.util


def check_structure() -> None:
    print("🔍 Verificando estructura del proyecto...")
    required_dirs = ['control', 'scripts', 'core', 'config', 'data']
    required_files = ['bot.py']

    for dir_name in required_dirs:
        print(f"✅ {dir_name}/ existe" if Path(dir_name).exists() else f"❌ {dir_name}/ falta")

    for file_name in required_files:
        print(f"✅ {file_name} existe" if Path(file_name).exists() else f"❌ {file_name} falta")


def check_imports() -> None:
    print("\n🔍 Verificando imports...")
    modules = [
        'control.telegram_bot',
        'control.handlers',
        'config.unified_config'
    ]

    for module in modules:
        try:
            spec = importlib.util.find_spec(module)
            print(f"✅ {module} disponible" if spec else f"❌ {module} no encontrado")
        except Exception as e:
            print(f"❌ {module} error: {e}")


def check_config() -> None:
    print("\n🔍 Verificando configuración (.env)...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]

    ok = True
    for var in required_vars:
        value = os.getenv(var)
        print(f"✅ {var} configurado" if value else f"❌ {var} falta")
        ok = ok and bool(value)
    if ok:
        print("✅ Variables de entorno OK")
    else:
        print("❌ Variables de entorno faltantes")


if __name__ == "__main__":
    print("🔧 DIAGNÓSTICO DEL BOT TRADING v10")
    print("=" * 50)
    check_structure()
    check_imports()
    check_config()
    print("\n✅ Diagnóstico completado")


