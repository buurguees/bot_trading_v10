@echo off
REM Script de inicio para entrenamiento autónomo en Windows
REM =====================================================

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                🤖 ENTRENAMIENTO AUTÓNOMO ENTERPRISE 🤖        ║
echo ║                                                              ║
echo ║  Configurando y ejecutando entrenamiento enterprise          ║
echo ║  completamente automatizado mientras cenas 🍽️                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no encontrado. Instala Python 3.8+ primero.
    pause
    exit /b 1
)

echo ✅ Python detectado

REM Configurar entorno
echo.
echo 🔧 Configurando entorno...
python setup_autonomous_training.py
if errorlevel 1 (
    echo ❌ Error en configuración. Revisa los errores arriba.
    pause
    exit /b 1
)

echo.
echo 🚀 Iniciando entrenamiento autónomo...
echo.
echo 📋 Información importante:
echo    • El entrenamiento correrá en background
echo    • Logs: logs/autonomous_training.log
echo    • Métricas: http://localhost:8000/metrics
echo    • Tiempo estimado: 2-4 horas
echo    • ¡Disfruta tu cena! 🍽️
echo.

REM Iniciar entrenamiento
python run_autonomous_training.py

echo.
echo 🏁 Entrenamiento finalizado
echo 📊 Revisa los logs para ver los resultados
pause
