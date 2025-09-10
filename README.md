# 🤖 Bot Trading v10 Enterprise

Sistema de trading automatizado con inteligencia artificial y gestión de agentes por símbolo.

## 📁 Estructura del Proyecto

```
bot_trading_v10/
├── 📁 config/                    # Configuraciones del sistema
│   ├── user_settings.yaml       # Configuración principal del usuario
│   ├── control_config.yaml      # Configuración de control
│   ├── logging_config.yaml      # Configuración de logging
│   ├── main_config.yaml         # Configuración principal
│   ├── agents_config.yaml       # Configuración de agentes
│   ├── logs_config.yaml         # Configuración de logs
│   ├── data_config.yaml         # Configuración de datos
│   ├── monitoring_config.yaml   # Configuración de monitoreo
│   ├── security_config.yaml     # Configuración de seguridad
│   ├── unified_config.py        # Gestor de configuración unificado
│   ├── config_loader.py         # Cargador de configuración
│   ├── .env                     # Variables de entorno
│   └── 📁 enterprise/           # Configuraciones enterprise
│       └── *.yaml               # Configuraciones específicas
│
├── 📁 core/                     # Módulos principales del sistema
│   ├── 📁 data/                 # Gestión de datos históricos
│   │   ├── collector.py         # Recolector de datos
│   │   ├── database.py          # Gestión de base de datos
│   │   ├── historical_data_manager.py
│   │   ├── history_analyzer.py  # Análisis de datos históricos
│   │   ├── history_downloader.py
│   │   └── symbol_database_manager.py
│   │
│   ├── 📁 ml/                   # Machine Learning
│   │   ├── enterprise/          # Módulos ML enterprise
│   │   └── __init__.py
│   │
│   ├── 📁 monitoring/           # Monitoreo de datos
│   │   ├── enterprise/          # Módulos de monitoreo enterprise
│   │   └── __init__.py
│   │
│   ├── 📁 logs/                 # Gestión de logs
│   │   └── (archivos de logs)
│   │
│   ├── 📁 security/             # Seguridad y auditoría
│   │   ├── audit_logger.py      # Logger de auditoría
│   │   ├── compliance_checker.py
│   │   └── __init__.py
│   │
│   ├── 📁 trading/              # Motores de trading
│   │   ├── enterprise/          # Módulos de trading enterprise
│   │   └── __init__.py
│   │
│   ├── 📁 compliance/           # Cumplimiento normativo
│   │   ├── enterprise/          # Módulos de cumplimiento enterprise
│   │   └── __init__.py
│   │
│   ├── 📁 deployment/           # Despliegue y recuperación
│   │   └── __init__.py
│   │
│   └── 📁 integration/          # Utilidades del sistema
│       └── __init__.py
│
├── 📁 scripts/                  # Scripts de ejecución
│   ├── 📁 training/             # Scripts de entrenamiento
│   │   └── train_historical.py
│   └── 📁 data/                 # Scripts de datos
│       └── ensure_historical_data.py
│
├── 📁 control/                  # Control del bot
│   ├── handlers.py              # Handlers de Telegram
│   ├── telegram_bot.py          # Bot de Telegram
│   ├── metrics_sender.py        # Envío de métricas
│   └── security_guard.py        # Guardia de seguridad
│
├── 📁 agents/                   # Agentes por símbolo
│   ├── 📁 BTCUSDT/             # Agente BTCUSDT
│   │   ├── model.pkl           # Modelo ML
│   │   ├── strategies.json     # Estrategias
│   │   ├── state.json          # Estado del agente
│   │   └── 📁 logs/            # Logs del agente
│   │
│   ├── 📁 ETHUSDT/             # Agente ETHUSDT
│   ├── 📁 ADAUSDT/             # Agente ADAUSDT
│   ├── 📁 SOLUSDT/             # Agente SOLUSDT
│   └── 📁 DOGEUSDT/            # Agente DOGEUSDT
│
├── 📁 data/                     # Almacenamiento de datos
│   ├── trading_bot.db          # Base de datos SQLite
│   └── 📁 historical/          # Datos históricos por símbolo
│
├── 📁 docs/                     # Documentación
│   └── *.md                    # Archivos de documentación
│
├── 📁 _old/                     # Archivos obsoletos
│   └── (archivos movidos)
│
├── 📁 venv/                     # Entorno virtual Python
│
├── bot.py                       # Punto de entrada principal
├── requirements.txt             # Dependencias Python
└── README.md                    # Este archivo
```

## 🚀 Inicio Rápido

### 1. Instalación
```bash
# Clonar el repositorio
git clone <repository-url>
cd bot_trading_v10

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración
```bash
# Copiar archivo de variables de entorno
copy .env.example .env

# Editar configuración
notepad config/user_settings.yaml
notepad .env
```

### 3. Ejecución
```bash
# Iniciar el bot
python bot.py
```

## ⚙️ Configuración

### Archivos de Configuración Principales

- **`config/user_settings.yaml`** - Configuración principal del usuario
- **`config/agents_config.yaml`** - Configuración de agentes por símbolo
- **`config/data_config.yaml`** - Configuración de datos y base de datos
- **`config/monitoring_config.yaml`** - Configuración de monitoreo
- **`config/security_config.yaml`** - Configuración de seguridad
- **`config/logs_config.yaml`** - Configuración de logging

### Variables de Entorno (.env)

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# API Keys
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_key_here
BITGET_PASSPHRASE=your_passphrase_here

# Base de datos
DATABASE_URL=sqlite:///data/trading_bot.db
REDIS_URL=redis://localhost:6379

# Seguridad
ENCRYPTION_KEY=your_encryption_key_here
```

## 🤖 Comandos de Telegram

### Comandos Básicos
- `/start` - Iniciar el bot
- `/help` - Lista de comandos
- `/status` - Estado del sistema
- `/metrics` - Métricas actuales
- `/health` - Salud del sistema

### Comandos de Trading
- `/start_trading` - Iniciar trading
- `/stop_trading` - Detener trading
- `/emergency_stop` - Parada de emergencia
- `/positions` - Posiciones abiertas
- `/balance` - Balance actual

### Comandos de Datos
- `/verify_historical_data` - Verificar datos históricos
- `/download_historical_data` - Descargar datos históricos
- `/historical_data_report` - Reporte de datos históricos

### Comandos de Entrenamiento
- `/train_hist` - Entrenamiento histórico
- `/train_live` - Entrenamiento en vivo
- `/stop_train` - Detener entrenamiento

## 📊 Monitoreo

### Métricas Disponibles
- Rendimiento de agentes
- Métricas de trading
- Salud del sistema
- Uso de recursos
- Logs de auditoría

### Alertas
- Telegram
- Consola
- Archivos de log
- Webhooks (opcional)

## 🔒 Seguridad

### Características de Seguridad
- Encriptación de datos sensibles
- Auditoría completa de acciones
- Rate limiting
- Validación de comandos
- Cumplimiento normativo (MiFID II, GDPR)

### Configuración de Seguridad
- Chat IDs autorizados
- Timeouts de comandos
- Límites de tasa
- Logs de auditoría
- Alertas de seguridad

## 📈 Agentes

### Estructura de Agentes
Cada agente se almacena en `agents/{SYMBOL}/` con:
- `model.pkl` - Modelo ML entrenado
- `strategies.json` - Estrategias de trading
- `state.json` - Estado actual del agente
- `logs/` - Logs específicos del agente

### Símbolos Soportados
- BTCUSDT
- ETHUSDT
- ADAUSDT
- SOLUSDT
- DOGEUSDT

## 🛠️ Desarrollo

### Estructura de Módulos
- **`core/`** - Módulos principales del sistema
- **`scripts/`** - Scripts de ejecución
- **`control/`** - Control del bot
- **`config/`** - Configuraciones

### Configuración de Desarrollo
```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar tests
python -m pytest tests/

# Linting
flake8 .
black .
```

## 📝 Logs

### Ubicación de Logs
- **`core/logs/`** - Logs del sistema
- **`agents/{SYMBOL}/logs/`** - Logs por agente
- **`core/logs/security.log`** - Logs de seguridad
- **`core/logs/audit.log`** - Logs de auditoría

### Niveles de Log
- **INFO** - Información general
- **DEBUG** - Información detallada
- **WARNING** - Advertencias
- **ERROR** - Errores
- **CRITICAL** - Errores críticos

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

Para soporte, contacta:
- Email: support@tradingbot.com
- Telegram: @TradingBotSupport
- Issues: [GitHub Issues](https://github.com/username/bot-trading-v10/issues)

---

**Bot Trading v10 Enterprise** - Sistema de trading automatizado con IA