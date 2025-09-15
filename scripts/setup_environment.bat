@echo off
REM Bot Trading v10 Enterprise - Script de Configuración
REM ====================================================

echo.
echo 🤖 Bot Trading v10 Enterprise - Configuración del Entorno
echo ========================================================
echo.

REM Verificar Python
echo 📋 Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Instala Python 3.8+ desde https://python.org
    pause
    exit /b 1
)

REM Crear entorno virtual
echo.
echo 🔧 Creando entorno virtual...
if exist venv (
    echo ⚠️  El entorno virtual ya existe. Eliminando...
    rmdir /s /q venv
)

python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Error creando entorno virtual
    pause
    exit /b 1
)

REM Activar entorno virtual
echo.
echo 🚀 Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip
echo.
echo 📦 Actualizando pip...
python -m pip install --upgrade pip

REM Instalar dependencias
echo.
echo 📥 Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)

REM Crear archivo .env si no existe
echo.
echo 🔐 Configurando variables de entorno...
if not exist .env (
    copy env.example .env
    echo ✅ Archivo .env creado desde env.example
    echo ⚠️  IMPORTANTE: Edita .env con tus credenciales antes de usar el bot
) else (
    echo ✅ Archivo .env ya existe
)

REM Crear directorios necesarios
echo.
echo 📁 Creando directorios necesarios...
if not exist data mkdir data
if not exist data\logs mkdir data\logs
if not exist data\models mkdir data\models
if not exist data\historical mkdir data\historical
if not exist data\checkpoints mkdir data\checkpoints
if not exist data\alignments mkdir data\alignments

REM Crear archivos .gitkeep
echo. > data\logs\.gitkeep
echo. > data\models\.gitkeep
echo. > data\historical\.gitkeep
echo. > data\checkpoints\.gitkeep
echo. > data\alignments\.gitkeep

echo.
echo ✅ Configuración completada exitosamente!
echo.
echo 📋 Próximos pasos:
echo    1. Edita .env con tus credenciales
echo    2. Configura config/user_settings.yaml
echo    3. Configura control/config.yaml
echo    4. Ejecuta: python bot.py --mode paper --telegram-enabled
echo.
echo 🎯 Para activar el entorno virtual en el futuro:
echo    venv\Scripts\activate.bat
echo.
pause
