# 📁 Estructura del Proyecto Bot Trading v10

## 🏗️ Organización Principal

```
bot_trading_v10/
├── 📱 app.py                          # Aplicación principal (menú interactivo)
├── 📋 README.md                       # Documentación principal
├── 📦 requirements*.txt               # Dependencias del proyecto
├── ⚙️ pytest.ini                     # Configuración de testing
├── 📊 prometheus.yml                  # Configuración de monitoreo
├── 🔧 logging.conf                    # Configuración de logs
└── 📁 bot_status.log                  # Log de estado del bot
```

## 📂 Directorios Principales

### 🤖 `agents/` - Agentes de IA
- `trading_agent.py` - Agente principal de trading
- `autonomous_decision_engine.py` - Motor de decisiones autónomas
- `self_learning_system.py` - Sistema de autoaprendizaje
- `self_correction_mechanism.py` - Mecanismo de autocorrección

### 🧠 `core/` - Lógica Central
- `main.py` - Orquestador principal
- `config_manager.py` - Gestor de configuración
- `enterprise_config.py` - Configuración enterprise
- `error_handler.py` - Manejo de errores
- `health_checker.py` - Verificación de salud del sistema
- `integrate_multi_timeframe.py` - Integración multi-timeframe

### 📊 `data/` - Gestión de Datos
- `collector.py` - Recolector de datos
- `database.py` - Base de datos
- `preprocessor.py` - Preprocesamiento
- `hybrid_storage.py` - Almacenamiento híbrido
- `intelligent_cache.py` - Cache inteligente
- `multi_timeframe_coordinator.py` - Coordinador multi-timeframe

### 🎯 `models/` - Modelos de IA
- `neural_network.py` - Red neuronal
- `prediction_engine.py` - Motor de predicciones
- `trainer.py` - Entrenador
- `adaptive_trainer.py` - Entrenador adaptativo
- `enterprise/` - Sistema enterprise de ML

### 📈 `trading/` - Motor de Trading
- `executor.py` - Ejecutor de órdenes
- `risk_manager.py` - Gestor de riesgo
- `portfolio_manager.py` - Gestor de portafolio
- `strategy_manager.py` - Gestor de estrategias

### 📊 `monitoring/` - Dashboard y Monitoreo
- `main_dashboard.py` - Dashboard principal
- `pages/` - Páginas del dashboard
- `components/` - Componentes UI
- `callbacks/` - Callbacks de Dash

### 📁 `enterprise_scripts/` - Scripts Enterprise
- `app_enterprise_complete.py` - Aplicación enterprise completa
- `app_enterprise.py` - Aplicación enterprise base
- `app_enterprise_methods.py` - Métodos enterprise
- `demo_enterprise_config.py` - Demo de configuración
- `demo_enterprise_system.py` - Demo del sistema

### 🚀 `training_scripts/` - Scripts de Entrenamiento
- `run_autonomous_training.py` - Entrenamiento autónomo
- `run_fixed_training.py` - Entrenamiento corregido
- `run_simple_training.py` - Entrenamiento simple
- `setup_autonomous_training.py` - Setup de entrenamiento
- `start_autonomous_training.bat/.sh` - Scripts de inicio
- `train_background.py` - Entrenamiento en background
- `start_training.py` - Inicio de entrenamiento

### 📊 `monitoring_scripts/` - Scripts de Monitoreo
- `monitor_training.py` - Monitor de entrenamiento
- `monitor_simple_training.py` - Monitor simple
- `quick_monitor.py` - Monitor rápido

### 📚 `docs/` - Documentación
- `README.md` - Documentación principal
- `ENTERPRISE_*.md` - Guías enterprise
- `COMO_*.md` - Guías de uso
- `ESTADO_*.md` - Estados del sistema

### 📋 `summary_docs/` - Resúmenes
- `ENTERPRISE_SYSTEM_SUMMARY.md` - Resumen del sistema enterprise
- `ENTERPRISE_APP_IMPLEMENTATION_SUMMARY.md` - Resumen de la app
- `ENTERPRISE_TRAINING_IMPLEMENTATION_SUMMARY.md` - Resumen de entrenamiento
- `ENTRENAMIENTO_AUTONOMO_COMPLETADO.md` - Resumen de entrenamiento autónomo

### 🧪 `tests/` - Testing
- `test_*.py` - Tests unitarios e integración
- `test_enterprise_*.py` - Tests enterprise

### ⚙️ `config/` - Configuración
- `user_settings.yaml` - Configuración del usuario
- `ai_agent_config.yaml` - Configuración del agente IA
- `core_config.yaml` - Configuración central

### 📦 `backups/` - Respaldos
- Archivos ZIP de versiones anteriores

### 🔐 `keys/` y `secrets/` - Claves y Secretos
- Archivos de configuración sensibles

## 🚀 Uso Rápido

### Entrenamiento de 1 Hora
```bash
# Opción 1: Usar app.py (recomendado)
python app.py
# Seleccionar opción 4: "Empezar entrenamiento + dashboard"

# Opción 2: Entrenamiento autónomo
cd training_scripts
python run_fixed_training.py

# Opción 3: Entrenamiento enterprise
python run_autonomous_training.py
```

### Monitoreo
```bash
# Dashboard web
python monitoring/main_dashboard.py

# Monitor rápido
python monitoring_scripts/quick_monitor.py
```

### Aplicación Enterprise
```bash
# App enterprise completa
python enterprise_scripts/app_enterprise_complete.py

# Con argumentos CLI
python enterprise_scripts/app_enterprise_complete.py --mode train --duration 3600
```

## 📊 Características Principales

- ✅ **Sistema Modular**: Separación clara de responsabilidades
- ✅ **Enterprise Ready**: Scripts y configuraciones de nivel empresarial
- ✅ **Monitoreo Avanzado**: Dashboard web y scripts de monitoreo
- ✅ **Entrenamiento Autónomo**: Scripts para entrenamiento sin supervisión
- ✅ **Testing Completo**: Suite de tests unitarios e integración
- ✅ **Documentación Extensa**: Guías y resúmenes detallados
- ✅ **Configuración Flexible**: Múltiples archivos de configuración
- ✅ **Logging Estructurado**: Sistema de logs avanzado

## 🔧 Mantenimiento

- **Logs**: Revisar `logs/` para debugging
- **Checkpoints**: Modelos guardados en `checkpoints/` y `models/saved_models/`
- **Configuración**: Modificar archivos en `config/`
- **Tests**: Ejecutar `pytest` para validar el sistema
- **Monitoreo**: Usar scripts en `monitoring_scripts/`

---
*Estructura organizada para máxima eficiencia y mantenibilidad* 🚀
