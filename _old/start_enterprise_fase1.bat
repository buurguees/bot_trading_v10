@echo off
REM start_enterprise_fase1.bat - Script de inicio para FASE 1 Enterprise
REM Ubicación: C:\TradingBot_v10\start_enterprise_fase1.bat

echo ========================================
echo    TRADING BOT ENTERPRISE - FASE 1
echo ========================================
echo.

REM Verificar que Python esté instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no está instalado o no está en el PATH
    pause
    exit /b 1
)

REM Verificar que Docker esté instalado
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker no está instalado o no está en el PATH
    pause
    exit /b 1
)

REM Verificar que Docker Compose esté instalado
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose no está instalado o no está en el PATH
    pause
    exit /b 1
)

echo ✓ Prerrequisitos verificados
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Instalar dependencias enterprise
echo Instalando dependencias enterprise...
pip install -r requirements-enterprise.txt

REM Ejecutar configuración de infraestructura
echo.
echo ========================================
echo    CONFIGURANDO INFRAESTRUCTURA
echo ========================================
echo.

python scripts\enterprise\setup_infrastructure.py

if %errorlevel% neq 0 (
    echo ERROR: Falló la configuración de infraestructura
    pause
    exit /b 1
)

REM Iniciar servicios
echo.
echo ========================================
echo    INICIANDO SERVICIOS
echo ========================================
echo.

python scripts\enterprise\start_services.py start

if %errorlevel% neq 0 (
    echo ERROR: Falló el inicio de servicios
    pause
    exit /b 1
)

REM Verificar salud de servicios
echo.
echo ========================================
echo    VERIFICANDO SALUD DE SERVICIOS
echo ========================================
echo.

python scripts\enterprise\health_check.py check

if %errorlevel% neq 0 (
    echo WARNING: Algunos servicios no están saludables
    echo Continuando con el inicio...
)

REM Mostrar información de acceso
echo.
echo ========================================
echo    SERVICIOS DISPONIBLES
echo ========================================
echo.
echo 🌐 Prometheus: http://localhost:9090
echo 📊 Grafana: http://localhost:3000
echo 🔄 Kafka: localhost:9092
echo 💾 Redis: localhost:6379
echo 🗄️  TimescaleDB: localhost:5432
echo.
echo ========================================
echo    FASE 1 COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo Para verificar el estado de los servicios:
echo   python scripts\enterprise\health_check.py check
echo.
echo Para detener los servicios:
echo   python scripts\enterprise\start_services.py stop
echo.
echo Para crear un backup:
echo   python scripts\enterprise\backup_data.py create
echo.

pause
