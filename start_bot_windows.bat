@echo off
REM start_bot_windows.bat - Script de inicio optimizado para Windows

echo 🚀 Iniciando Trading Bot v10 Enterprise para Windows...

REM Configurar variables de entorno para Windows
set PYTHONIOENCODING=utf-8
set TZ=UTC
set LC_ALL=en_US.UTF-8
set LANG=en_US.UTF-8

REM Verificar Python
python --version
if %errorlevel% neq 0 (
    echo ❌ Python no encontrado. Instala Python 3.13+ && pause && exit /b 1
)

REM Verificar dependencias
echo 🔍 Verificando dependencias...
python -c "import numpy, pandas" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Instalando dependencias faltantes...
    pip install -r requirements.txt
)

REM Verificar archivo .env
if not exist .env (
    echo ⚠️ Archivo .env no encontrado. Copiando desde .env.example...
    copy config\env.example .env
    echo ❗ IMPORTANTE: Edita .env con tus credenciales antes de continuar
    pause
)

REM Ejecutar diagnóstico primero
echo 🔍 Ejecutando diagnóstico del sistema...
python diagnostic_data.py

echo.
echo ✅ Diagnóstico completado. Presiona cualquier tecla para iniciar el bot...
pause >nul

REM Iniciar el bot
echo 🚀 Iniciando el bot...
python bot.py --mode paper

pause


