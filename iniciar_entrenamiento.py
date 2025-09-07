#!/usr/bin/env python3
"""
🚀 Iniciar Entrenamiento Nocturno
================================

Script de inicio rápido para el entrenamiento nocturno del Trading Bot v10.

Uso: python iniciar_entrenamiento.py
"""

import os
import sys
import subprocess
from datetime import datetime

def main():
    """Función principal de inicio"""
    print("🌙 TRADING BOT v10 - INICIAR ENTRENAMIENTO NOCTURNO")
    print("=" * 60)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('scripts/entrenamiento_nocturno.py'):
        print("❌ Error: No se encuentra el script de entrenamiento nocturno")
        print("   Asegúrate de ejecutar este script desde la raíz del proyecto")
        return
    
    # Verificar que existe la configuración
    if not os.path.exists('config/entrenamiento_nocturno.yaml'):
        print("⚠️ Advertencia: No se encuentra la configuración específica")
        print("   Se usará la configuración por defecto")
    
    # Mostrar información del sistema
    print("📊 INFORMACIÓN DEL SISTEMA")
    print("-" * 30)
    print(f"   📁 Directorio: {os.getcwd()}")
    print(f"   🐍 Python: {sys.version}")
    print(f"   📦 Script: scripts/entrenamiento_nocturno.py")
    print()
    
    # Mostrar opciones
    print("🎯 OPCIONES DE ENTRENAMIENTO")
    print("-" * 30)
    print("1. 🌙 Entrenamiento completo (recomendado)")
    print("2. 📊 Solo verificar estado del bot")
    print("3. 🔧 Configurar parámetros")
    print("4. ❌ Cancelar")
    print()
    
    try:
        opcion = input("Selecciona una opción (1-4): ").strip()
        
        if opcion == "1":
            print("\n🚀 Iniciando entrenamiento completo...")
            print("   ⏳ Esto puede tomar varias horas...")
            print("   📝 Los logs se guardarán en logs/")
            print("   ⚠️ Presiona Ctrl+C para detener en cualquier momento")
            print()
            
            input("Presiona Enter para continuar...")
            
            # Ejecutar el script de entrenamiento
            subprocess.run([sys.executable, "scripts/entrenamiento_nocturno.py"])
            
        elif opcion == "2":
            print("\n🔍 Verificando estado del bot...")
            subprocess.run([sys.executable, "scripts/estado_bot_rapido.py"])
            
        elif opcion == "3":
            print("\n🔧 Configuración de parámetros")
            print("   📝 Edita el archivo: config/entrenamiento_nocturno.yaml")
            print("   📚 Lee la documentación en: docs/")
            
        elif opcion == "4":
            print("\n❌ Operación cancelada")
            
        else:
            print("\n❌ Opción inválida")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
