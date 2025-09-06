"""
setup.py
Script de instalación y configuración del Trading Bot v10
Ubicación: C:\TradingBot_v10\setup.py

Uso:
    python setup.py install    # Instalación completa
    python setup.py develop    # Instalación en modo desarrollo
    python setup.py test       # Ejecutar tests
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TradingBotSetup:
    """Configurador del Trading Bot v10"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.python_exe = self.venv_path / "Scripts" / "python.exe"
        self.pip_exe = self.venv_path / "Scripts" / "pip.exe"
        
    def check_python_version(self):
        """Verifica la versión de Python"""
        logger.info("🐍 Verificando versión de Python...")
        
        if sys.version_info < (3, 8):
            logger.error("❌ Python 3.8+ requerido. Versión actual: {}.{}.{}".format(
                sys.version_info.major, sys.version_info.minor, sys.version_info.micro
            ))
            return False
        
        logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} OK")
        return True
    
    def create_virtual_environment(self):
        """Crea el entorno virtual"""
        logger.info("📦 Configurando entorno virtual...")
        
        if self.venv_path.exists():
            logger.info("⚠️ Entorno virtual ya existe, eliminando...")
            shutil.rmtree(self.venv_path)
        
        try:
            subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            logger.info("✅ Entorno virtual creado")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error creando entorno virtual: {e}")
            return False
    
    def upgrade_pip(self):
        """Actualiza pip en el entorno virtual"""
        logger.info("🔄 Actualizando pip...")
        
        try:
            subprocess.run([
                str(self.python_exe), "-m", "pip", "install", "--upgrade", "pip"
            ], check=True)
            logger.info("✅ Pip actualizado")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error actualizando pip: {e}")
            return False
    
    def install_dependencies(self):
        """Instala las dependencias del proyecto"""
        logger.info("📚 Instalando dependencias...")
        
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            logger.error("❌ Archivo requirements.txt no encontrado")
            return False
        
        try:
            # Instalar dependencias básicas primero
            basic_deps = [
                "wheel", "setuptools", "pip-tools"
            ]
            
            for dep in basic_deps:
                logger.info(f"📦 Instalando {dep}...")
                subprocess.run([
                    str(self.pip_exe), "install", dep
                ], check=True)
            
            # Instalar dependencias principales
            logger.info("📦 Instalando dependencias principales...")
            subprocess.run([
                str(self.pip_exe), "install", "-r", str(requirements_file)
            ], check=True)
            
            logger.info("✅ Dependencias instaladas")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error instalando dependencias: {e}")
            return False
    
    def create_directory_structure(self):
        """Crea la estructura de directorios necesaria"""
        logger.info("📁 Creando estructura de directorios...")
        
        directories = [
            "config",
            "data/raw",
            "data/processed", 
            "data/historical",
            "models/saved_models",
            "trading",
            "monitoring",
            "backtesting",
            "strategies",
            "utils",
            "tests",
            "logs",
            "backups",
            "docs"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 {directory}")
        
        logger.info("✅ Estructura de directorios creada")
        return True
    
    def create_init_files(self):
        """Crea archivos __init__.py necesarios"""
        logger.info("📄 Creando archivos __init__.py...")
        
        init_dirs = [
            "config",
            "data", 
            "models",
            "trading",
            "monitoring",
            "backtesting",
            "strategies",
            "utils",
            "tests"
        ]
        
        for directory in init_dirs:
            init_file = self.project_root / directory / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""{}"""\n'.format(directory.title() + " module"))
                logger.info(f"📄 {directory}/__init__.py")
        
        logger.info("✅ Archivos __init__.py creados")
        return True
    
    def setup_environment_file(self):
        """Configura el archivo .env"""
        logger.info("🔧 Configurando archivo .env...")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_file.exists():
            if env_example.exists():
                shutil.copy2(env_example, env_file)
                logger.info("✅ Archivo .env creado desde .env.example")
            else:
                # Crear .env básico
                env_content = """# Trading Bot v10 - Environment Variables

# BITGET API CREDENTIALS
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_key_here
BITGET_PASSPHRASE=your_passphrase_here

# ENVIRONMENT
ENVIRONMENT=development
LOG_LEVEL=INFO

# DASHBOARD
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8050
"""
                env_file.write_text(env_content)
                logger.info("✅ Archivo .env básico creado")
        else:
            logger.info("ℹ️ Archivo .env ya existe")
        
        logger.warning("⚠️ IMPORTANTE: Configura tus credenciales de Bitget en .env")
        return True
    
    def test_installation(self):
        """Prueba la instalación"""
        logger.info("🧪 Probando instalación...")
        
        test_script = """
import sys
import os
sys.path.append('{}')

try:
    # Test imports básicos
    import pandas as pd
    import numpy as np
    import tensorflow as tf
    import ccxt
    import sqlalchemy
    
    print("✅ Imports básicos OK")
    
    # Test GPU (si disponible)
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"✅ GPU detectada: {{gpus[0].name}}")
    else:
        print("ℹ️ GPU no disponible (usando CPU)")
    
    # Test configuración
    from config.settings import config
    print("✅ Configuración cargada")
    
    # Test base de datos
    from data.database import db_manager
    stats = db_manager.get_database_stats()
    print("✅ Base de datos OK")
    
    print("\\n🎉 ¡Instalación exitosa!")
    
except ImportError as e:
    print(f"❌ Error de import: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {{e}}")
    sys.exit(1)
""".format(str(self.project_root))
        
        try:
            result = subprocess.run([
                str(self.python_exe), "-c", test_script
            ], capture_output=True, text=True, cwd=str(self.project_root))
            
            if result.returncode == 0:
                logger.info("✅ Test de instalación exitoso")
                print(result.stdout)
                return True
            else:
                logger.error("❌ Test de instalación falló")
                print(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando test: {e}")
            return False
    
    def create_startup_scripts(self):
        """Crea scripts de inicio"""
        logger.info("🚀 Creando scripts de inicio...")
        
        # Script para Windows
        bat_content = f"""@echo off
echo 🤖 Iniciando Trading Bot v10...
cd /d "{self.project_root}"
"{self.python_exe}" main.py %*
pause
"""
        
        bat_file = self.project_root / "start_bot.bat"
        bat_file.write_text(bat_content)
        logger.info("📄 start_bot.bat creado")
        
        # Script para activar entorno
        activate_content = f"""@echo off
echo 🔧 Activando entorno virtual...
cd /d "{self.project_root}"
call "{self.venv_path}/Scripts/activate.bat"
echo ✅ Entorno activado. Usa 'python main.py' para iniciar el bot.
cmd /k
"""
        
        activate_file = self.project_root / "activate_env.bat"
        activate_file.write_text(activate_content)
        logger.info("📄 activate_env.bat creado")
        
        logger.info("✅ Scripts de inicio creados")
        return True
    
    def print_final_instructions(self):
        """Imprime instrucciones finales"""
        instructions = f"""
🎉 ¡INSTALACIÓN COMPLETADA!

📋 PRÓXIMOS PASOS:

1. 🔐 CONFIGURAR CREDENCIALES:
   - Edita el archivo .env
   - Añade tus credenciales de Bitget API
   
2. 🧪 PROBAR EL BOT:
   - Ejecuta: start_bot.bat
   - O: activate_env.bat y luego 'python main.py'
   
3. 📊 PRIMERAS PRUEBAS:
   - python main.py --collect-data     (recolectar datos)
   - python main.py --health-check     (verificar sistema)
   - python main.py --mode development (modo desarrollo)

📁 ARCHIVOS IMPORTANTES:
   - .env                    → Credenciales (NO subir a Git)
   - config/user_settings.yaml → Configuración del bot
   - start_bot.bat          → Inicio rápido
   - activate_env.bat       → Activar entorno

⚠️ IMPORTANTE:
   - NUNCA subir .env a Git
   - Empezar en modo 'development' o 'paper-trading'
   - Leer config/user_settings.yaml para personalizar

📚 DOCUMENTACIÓN:
   - README.md              → Documentación completa
   - docs/                  → Documentación adicional

🆘 SOPORTE:
   - Verificar logs/ si hay errores
   - Usar --verbose para debug detallado
   - Revisar config/user_settings.yaml

¡Feliz trading! 🚀
"""
        print(instructions)
    
    def full_install(self):
        """Instalación completa"""
        logger.info("🚀 Iniciando instalación completa del Trading Bot v10...")
        
        steps = [
            ("Verificar Python", self.check_python_version),
            ("Crear entorno virtual", self.create_virtual_environment),
            ("Actualizar pip", self.upgrade_pip),
            ("Instalar dependencias", self.install_dependencies),
            ("Crear directorios", self.create_directory_structure),
            ("Crear archivos __init__", self.create_init_files),
            ("Configurar .env", self.setup_environment_file),
            ("Crear scripts", self.create_startup_scripts),
            ("Probar instalación", self.test_installation)
        ]
        
        for step_name, step_function in steps:
            logger.info(f"📋 {step_name}...")
            if not step_function():
                logger.error(f"❌ Falló: {step_name}")
                return False
        
        self.print_final_instructions()
        return True
    
    def develop_install(self):
        """Instalación en modo desarrollo"""
        logger.info("🔧 Instalación en modo desarrollo...")
        
        # Solo instalar dependencias esenciales
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", "."
            ], check=True)
            logger.info("✅ Instalación en modo desarrollo completada")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error en instalación desarrollo: {e}")
            return False
    
    def run_tests(self):
        """Ejecuta los tests"""
        logger.info("🧪 Ejecutando tests...")
        
        try:
            subprocess.run([
                str(self.python_exe), "-m", "pytest", "tests/", "-v"
            ], check=True)
            logger.info("✅ Tests completados")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Tests fallaron: {e}")
            return False

def main():
    """Función principal del script de setup"""
    setup = TradingBotSetup()
    
    if len(sys.argv) < 2:
        print("Uso: python setup.py [install|develop|test]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "install":
        success = setup.full_install()
    elif command == "develop":
        success = setup.develop_install()
    elif command == "test":
        success = setup.run_tests()
    else:
        print(f"Comando desconocido: {command}")
        print("Comandos disponibles: install, develop, test")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()