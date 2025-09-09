# Ruta: scripts/root/install_requirements.py
#!/usr/bin/env python3
"""
Script de Instalación Automática de Dependencias
===============================================

Este script facilita la instalación de dependencias del sistema enterprise
según el entorno y necesidades específicas.

Uso:
    python install_requirements.py --env production
    python install_requirements.py --env development
    python install_requirements.py --env minimal
    python install_requirements.py --env full

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import argparse
import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        print(f"   Comando: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ requerido. Versión actual:", f"{version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor} detectado")
    return True

def check_pip():
    """Verifica que pip esté disponible"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        print("✅ pip disponible")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip no disponible")
        return False

def install_system_dependencies():
    """Instala dependencias del sistema según el OS"""
    system = platform.system().lower()
    
    if system == "linux":
        print("🐧 Detectado Linux")
        commands = [
            "sudo apt-get update",
            "sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev",
            "sudo apt-get install -y postgresql-client libpq-dev",
            "sudo apt-get install -y redis-server"
        ]
    elif system == "darwin":
        print("🍎 Detectado macOS")
        commands = [
            "brew install openssl libffi postgresql redis",
            "brew services start postgresql",
            "brew services start redis"
        ]
    elif system == "windows":
        print("🪟 Detectado Windows")
        print("⚠️  En Windows, instalar manualmente:")
        print("   - Visual Studio Build Tools")
        print("   - PostgreSQL")
        print("   - Redis")
        return True
    else:
        print(f"⚠️  Sistema no reconocido: {system}")
        return True
    
    for command in commands:
        if not run_command(command, f"Ejecutando: {command}"):
            print(f"⚠️  Comando falló: {command}")
    
    return True

def install_python_dependencies(env_type):
    """Instala dependencias de Python según el entorno"""
    requirements_files = {
        "minimal": "requirements-minimal.txt",
        "production": "requirements-prod.txt",
        "development": "requirements-dev.txt",
        "full": "requirements.txt"
    }
    
    if env_type not in requirements_files:
        print(f"❌ Entorno no válido: {env_type}")
        return False
    
    requirements_file = requirements_files[env_type]
    
    if not Path(requirements_file).exists():
        print(f"❌ Archivo no encontrado: {requirements_file}")
        return False
    
    # Comando de instalación
    command = f"{sys.executable} -m pip install -r {requirements_file}"
    
    # Agregar constraints si existe
    if Path("constraints.txt").exists():
        command += " -c constraints.txt"
    
    # Agregar flags de optimización
    command += " --upgrade --no-cache-dir"
    
    return run_command(command, f"Instalando dependencias {env_type}")

def create_virtual_environment():
    """Crea un entorno virtual"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Entorno virtual ya existe")
        return True
    
    print("🔄 Creando entorno virtual...")
    command = f"{sys.executable} -m venv venv"
    
    if run_command(command, "Creando entorno virtual"):
        print("✅ Entorno virtual creado")
        print("💡 Para activar:")
        if platform.system().lower() == "windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        return True
    else:
        print("❌ Error creando entorno virtual")
        return False

def verify_installation():
    """Verifica que la instalación fue exitosa"""
    print("🔍 Verificando instalación...")
    
    # Verificar imports críticos
    critical_modules = [
        "numpy",
        "pandas", 
        "ccxt",
        "websockets",
        "torch"
    ]
    
    failed_modules = []
    
    for module in critical_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_modules.append(module)
    
    if failed_modules:
        print(f"❌ Módulos faltantes: {', '.join(failed_modules)}")
        return False
    else:
        print("✅ Todos los módulos críticos instalados")
        return True

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Instalador automático de dependencias del sistema enterprise",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python install_requirements.py --env production
  python install_requirements.py --env development --venv
  python install_requirements.py --env minimal --no-system
        """
    )
    
    parser.add_argument(
        "--env",
        choices=["minimal", "production", "development", "full"],
        default="full",
        help="Tipo de entorno a instalar"
    )
    
    parser.add_argument(
        "--venv",
        action="store_true",
        help="Crear entorno virtual"
    )
    
    parser.add_argument(
        "--no-system",
        action="store_true",
        help="No instalar dependencias del sistema"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verificar instalación después de instalar"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 BOT TRADING V10 ENTERPRISE - INSTALADOR")
    print("=" * 60)
    print(f"Entorno: {args.env}")
    print(f"Entorno virtual: {'Sí' if args.venv else 'No'}")
    print(f"Dependencias del sistema: {'No' if args.no_system else 'Sí'}")
    print("=" * 60)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Verificar pip
    if not check_pip():
        sys.exit(1)
    
    # Crear entorno virtual si se solicita
    if args.venv:
        if not create_virtual_environment():
            sys.exit(1)
    
    # Instalar dependencias del sistema
    if not args.no_system:
        if not install_system_dependencies():
            print("⚠️  Algunas dependencias del sistema fallaron")
    
    # Instalar dependencias de Python
    if not install_python_dependencies(args.env):
        sys.exit(1)
    
    # Verificar instalación
    if args.verify:
        if not verify_installation():
            print("⚠️  Verificación falló, pero la instalación puede estar completa")
    
    print("=" * 60)
    print("✅ INSTALACIÓN COMPLETADA")
    print("=" * 60)
    print("Próximos pasos:")
    print("1. Configurar variables de entorno (.env)")
    print("2. Configurar base de datos (TimescaleDB)")
    print("3. Configurar Redis")
    print("4. Ejecutar: python trading_scripts/run_enterprise_trading.py --mode paper")
    print("=" * 60)

if __name__ == "__main__":
    main()
