#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_enhanced_system.py
========================
Script de Instalación del Sistema Mejorado

Configura automáticamente el sistema de entrenamiento mejorado con todas las
dependencias y configuraciones necesarias.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import List, Tuple

def print_banner():
    """Muestra el banner de instalación"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 BOT TRADING v10 ENTERPRISE 🚀                        ║
║                    Instalador del Sistema Mejorado                         ║
║                                                                              ║
║  📦 Instalación automática de dependencias                                 ║
║  🔧 Configuración del entorno                                               ║
║  📁 Creación de directorios necesarios                                     ║
║  🧪 Verificación del sistema                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

def check_python_version() -> bool:
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - Compatible")
    return True

def check_pip() -> bool:
    """Verifica que pip esté disponible"""
    print("📦 Verificando pip...")
    
    try:
        import pip
        print("✅ pip disponible")
        return True
    except ImportError:
        print("❌ pip no está disponible")
        print("💡 Instala pip: https://pip.pypa.io/en/stable/installation/")
        return False

def install_requirements() -> bool:
    """Instala las dependencias del sistema"""
    print("📦 Instalando dependencias...")
    
    requirements_file = Path("requirements-enhanced.txt")
    if not requirements_file.exists():
        print("❌ Archivo requirements-enhanced.txt no encontrado")
        return False
    
    try:
        # Actualizar pip primero
        print("   🔄 Actualizando pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Instalar dependencias
        print("   📥 Instalando dependencias del sistema mejorado...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        
        print("✅ Dependencias instaladas correctamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        print(f"   Error: {e.stderr}")
        return False

def create_directories() -> bool:
    """Crea los directorios necesarios"""
    print("📁 Creando directorios necesarios...")
    
    directories = [
        "logs",
        "data",
        "data/agents",
        "data/training_sessions",
        "data/training_sessions/checkpoints",
        "data/tmp",
        "config",
        "scripts/setup",
        "scripts/testing",
        "core/metrics",
        "core/telegram",
        "core/sync",
        "core/agents"
    ]
    
    try:
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory}")
        
        print("✅ Directorios creados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando directorios: {e}")
        return False

def create_config_files() -> bool:
    """Crea archivos de configuración básicos"""
    print("⚙️ Creando archivos de configuración...")
    
    try:
        # Crear .env.example
        env_example = """# Bot Trading v10 Enterprise - Configuración de Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Configuración adicional
TELEGRAM_RATE_LIMIT_DELAY=0.1
TELEGRAM_MAX_MESSAGE_LENGTH=4096
TELEGRAM_ENABLE_INDIVIDUAL_TRADES=true
TELEGRAM_ENABLE_CYCLE_SUMMARIES=true
TELEGRAM_ENABLE_ALERTS=true

# Configuración de memoria
MAX_MEMORY_USAGE_MB=8000
MEMORY_CLEANUP_INTERVAL=50

# Configuración de entrenamiento
DEFAULT_DAYS_BACK=365
DEFAULT_CYCLE_SIZE_HOURS=24
MAX_CONCURRENT_AGENTS=8
"""
        
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write(env_example)
        print("   ✅ .env.example")
        
        # Crear config/enhanced_training.yaml
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        enhanced_config = """# Bot Trading v10 Enterprise - Configuración del Sistema Mejorado
training:
  default_days_back: 365
  default_cycle_size_hours: 24
  max_concurrent_agents: 8
  checkpoint_interval: 100
  memory_cleanup_interval: 50
  max_memory_usage_mb: 8000

telegram:
  enabled: true
  rate_limit_delay: 0.1
  max_message_length: 4096
  enable_individual_trades: true
  enable_cycle_summaries: true
  enable_alerts: true

metrics:
  quality_threshold: 70.0
  confluence_threshold: 0.6
  risk_reward_minimum: 1.5

logging:
  level: INFO
  file_enabled: true
  console_enabled: true
  max_file_size_mb: 100
"""
        
        with open("config/enhanced_training.yaml", "w", encoding="utf-8") as f:
            f.write(enhanced_config)
        print("   ✅ config/enhanced_training.yaml")
        
        print("✅ Archivos de configuración creados")
        return True
        
    except Exception as e:
        print(f"❌ Error creando archivos de configuración: {e}")
        return False

def run_system_tests() -> bool:
    """Ejecuta pruebas básicas del sistema"""
    print("🧪 Ejecutando pruebas del sistema...")
    
    try:
        # Ejecutar script de pruebas
        result = subprocess.run([
            sys.executable, "scripts/testing/test_enhanced_system.py"
        ], capture_output=True, text=True, timeout=300)  # 5 minutos timeout
        
        if result.returncode == 0:
            print("✅ Pruebas del sistema pasaron correctamente")
            return True
        else:
            print("⚠️ Algunas pruebas fallaron, pero el sistema está instalado")
            print(f"   Error: {result.stderr}")
            return True  # No es crítico para la instalación
            
    except subprocess.TimeoutExpired:
        print("⚠️ Pruebas tardaron demasiado, pero el sistema está instalado")
        return True
    except Exception as e:
        print(f"⚠️ Error ejecutando pruebas: {e}")
        print("   El sistema está instalado, pero las pruebas fallaron")
        return True  # No es crítico

def show_next_steps():
    """Muestra los próximos pasos"""
    print("""
🎉 ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!

📋 PRÓXIMOS PASOS:

1. 🔧 CONFIGURAR TELEGRAM (Opcional):
   python scripts/setup/configure_telegram.py

2. 🧪 EJECUTAR PRUEBAS:
   python run_enhanced_training.py --test

3. ⚡ PRUEBA RÁPIDA (7 días):
   python run_enhanced_training.py --quick

4. 🚀 ENTRENAMIENTO COMPLETO:
   python run_enhanced_training.py --train --days 365

📚 DOCUMENTACIÓN:
   - docs/ENHANCED_TRAINING_SYSTEM.md
   - README.md

🔧 CONFIGURACIÓN:
   - .env.example (copiar a .env y configurar)
   - config/enhanced_training.yaml

💡 COMANDOS ÚTILES:
   python run_enhanced_training.py --help-detailed
   python scripts/setup/configure_telegram.py
   python scripts/testing/test_enhanced_system.py

¡El sistema está listo para usar! 🚀
    """)

def main():
    """Función principal de instalación"""
    print_banner()
    
    # Verificar requisitos
    if not check_python_version():
        return 1
    
    if not check_pip():
        return 1
    
    # Crear directorios
    if not create_directories():
        return 1
    
    # Instalar dependencias
    if not install_requirements():
        return 1
    
    # Crear archivos de configuración
    if not create_config_files():
        return 1
    
    # Ejecutar pruebas (opcional)
    run_system_tests()
    
    # Mostrar próximos pasos
    show_next_steps()
    
    print("✅ Instalación completada exitosamente!")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Instalación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado durante la instalación: {e}")
        sys.exit(1)
