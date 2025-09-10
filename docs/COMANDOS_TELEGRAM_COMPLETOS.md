# 📲 Comandos de Telegram Completos - Bot Trading v10 Enterprise

## ✅ Comandos Implementados

### 🎓 **Entrenamiento**
- **`/train_hist`** - Entrenamiento cronológico sobre histórico
- **`/train_live`** - Entrenamiento en vivo (paper trading)
- **`/training_status`** - Estado del entrenamiento
- **`/stop_train`** - Detener entrenamiento de forma elegante

### 📥 **Gestión de Datos Históricos**
- **`/download_history`** - Descargar datos históricos
- **`/inspect_history`** - Inspeccionar datos históricos
- **`/repair_history`** - Reparar datos históricos

### 💹 **Trading en Vivo**
- **`/start_trading`** - Iniciar sesión de trading en vivo
- **`/stop_trading`** - Detener trading en vivo
- **`/emergency_stop`** - Parada de emergencia

### 🛠️ **Control del Sistema**
- **`/reload_config`** - Recargar configuraciones
- **`/reset_agent`** - Resetear agente
- **`/restart_system`** - Reiniciar sistema

### 📊 **Monitoreo y Métricas**
- **`/status`** - Estado general del sistema
- **`/metrics`** - Métricas detalladas en tiempo real
- **`/positions`** - Posiciones abiertas
- **`/balance`** - Balance detallado
- **`/health`** - Salud del sistema
- **`/strategies`** - Resumen de estrategias

### 🔧 **Configuración**
- **`/set_mode`** - Cambiar modo (paper/live)
- **`/set_symbols`** - Cambiar símbolos
- **`/set_leverage`** - Cambiar leverage
- **`/settings`** - Ver configuración actual

### 📈 **Análisis y Reportes**
- **`/performance_report`** - Reporte de rendimiento
- **`/agent_analysis`** - Análisis detallado de agente
- **`/risk_report`** - Reporte de riesgo
- **`/trades_history`** - Historial de trades

### 🛠️ **Mantenimiento**
- **`/clear_cache`** - Limpiar cache
- **`/update_models`** - Actualizar modelos
- **`/shutdown`** - Apagar sistema

## 🚀 **Características Implementadas**

### ✅ **Seguridad Robusta**
- Validación de Chat ID autorizado
- Rate limiting (30 requests/min)
- Logging detallado de todas las acciones
- Manejo de errores enterprise

### ✅ **Integración con Scripts de Terminal**
- Mapeo directo a scripts de Python
- Ejecución en background
- Feedback en tiempo real
- Manejo de errores y timeouts

### ✅ **Configuración Dinámica**
- Lectura automática de `user_settings.yaml`
- Símbolos y timeframes configurables
- Recarga de configuraciones en caliente
- Validación de parámetros

### ✅ **Feedback en Tiempo Real**
- Mensajes de progreso con emojis
- Actualizaciones de estado
- Reportes detallados
- Logs persistentes

## 📁 **Archivos Clave**

- **`control/handlers.py`** - Implementación de todos los comandos
- **`control/telegram_bot.py`** - Bot principal y registro de comandos
- **`control/config.yaml`** - Configuración de seguridad y logging
- **`config/user_settings.yaml`** - Configuración de usuario
- **`logging_config.py`** - Configuración de logging UTF-8

## 🎯 **Flujo de Comandos**

```
Telegram → control/ → scripts/ → core/ → scripts/ → control/ → Telegram
```

1. **Usuario envía comando** en Telegram
2. **Handlers valida** autorización y parámetros
3. **Ejecuta script** de terminal correspondiente
4. **Procesa en core/** módulos del sistema
5. **Envía feedback** en tiempo real a Telegram
6. **Registra logs** para auditoría

## 🔧 **Configuración Requerida**

### Variables de Entorno
```bash
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=937027893
```

### Archivos de Configuración
- `config/user_settings.yaml` - Símbolos y timeframes
- `control/config.yaml` - Seguridad y logging
- `config/personal/exchanges.yaml` - Configuración de exchanges

## 📊 **Ejemplos de Uso**

### Entrenamiento Histórico
```
/train_hist --cycle_size 500 --update_every 25
```

### Descarga de Datos
```
/download_history
```

### Monitoreo del Sistema
```
/status
/metrics
/strategies
```

### Control del Sistema
```
/reload_config
/reset_agent
```

## ✅ **Estado de Implementación**

- **Total comandos implementados:** 25+
- **Categorías cubiertas:** 7
- **Seguridad:** ✅ Implementada
- **Logging:** ✅ Implementado
- **Manejo de errores:** ✅ Implementado
- **Integración con scripts:** ✅ Implementada
- **Feedback en tiempo real:** ✅ Implementado

---

**Última actualización:** Septiembre 2025  
**Versión:** 10.1.0  
**Autor:** Bot Trading v10 Enterprise Team
