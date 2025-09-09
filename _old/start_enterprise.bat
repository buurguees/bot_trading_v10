@echo off
echo.
echo ========================================
echo   TRADING BOT v10 - ENTERPRISE EDITION
echo ========================================
echo.
echo Iniciando sistema enterprise...
echo.

REM Crear directorios necesarios
if not exist "logs" mkdir logs
if not exist "checkpoints\enterprise" mkdir checkpoints\enterprise

REM Iniciar aplicación enterprise
python app_enterprise_simple.py

pause
