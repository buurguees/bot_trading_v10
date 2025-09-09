# 🤖 COMANDOS DE TELEGRAM COMPLETOS - TRADING BOT v10

## 📋 **RESUMEN DE COMANDOS DISPONIBLES**

El bot de Telegram ahora incluye **40+ comandos** para controlar completamente el sistema de trading desde tu móvil.

---

## 📊 **MONITOREO Y ESTADO**

### **Comandos Básicos**
- `/status` - Estado general del sistema
- `/metrics` - Métricas detalladas en tiempo real
- `/positions` - Posiciones abiertas
- `/balance` - Balance detallado
- `/health` - Salud del sistema

### **Comandos de Agentes**
- `/agents` - Estado de todos los agentes
- `/agent_status SYMBOL` - Estado de agente específico
  - Ejemplo: `/agent_status BTCUSDT`

---

## 🎓 **ENTRENAMIENTO Y MACHINE LEARNING**

### **Comandos de Entrenamiento**
- `/train --symbols BTC,ETH --duration 8h` - Entrenar agentes
- `/stop_training` - Detener entrenamiento
- `/retrain SYMBOL --duration 4h` - Reentrenar agente específico
- `/training_status` - Estado del entrenamiento

### **Comandos de Modelos**
- `/model_info SYMBOL` - Información del modelo
  - Ejemplo: `/model_info BTCUSDT`

---

## 💹 **TRADING Y OPERACIONES**

### **Comandos de Trading**
- `/trade --mode paper --symbols BTC,ETH` - Iniciar trading en modo paper
- `/trade --mode live --symbols SOL --leverage 20` - Trading live con leverage
- `/stop_trading` - Detener trading
- `/emergency_stop` - Parada de emergencia (cierra todas las posiciones)

### **Comandos de Posiciones**
- `/close_position SYMBOL` - Cerrar posición específica
  - Ejemplo: `/close_position BTCUSDT`

---

## 📈 **DATOS Y ANÁLISIS**

### **Comandos de Datos**
- `/download_data --symbols BTC,ETH --days 30` - Descargar datos históricos
- `/analyze_data SYMBOL` - Analizar datos históricos
- `/align_data --symbols BTC,ETH` - Alinear datos entre símbolos
- `/data_status` - Estado de los datos

### **Comandos de Testing**
- `/backtest SYMBOL --days 7` - Backtest de estrategia
  - Ejemplo: `/backtest BTCUSDT --days 7`

---

## 🔧 **CONFIGURACIÓN**

### **Comandos de Configuración**
- `/set_mode paper|live` - Cambiar modo de trading
- `/set_symbols BTC,ETH,ADA` - Cambiar símbolos de trading
- `/set_leverage SYMBOL 20` - Cambiar leverage de símbolo
- `/settings` - Ver configuración actual

---

## 📊 **REPORTES Y ANÁLISIS**

### **Comandos de Reportes**
- `/performance_report` - Reporte de rendimiento completo
- `/agent_analysis SYMBOL` - Análisis detallado de agente
- `/risk_report` - Reporte de riesgo
- `/trades_history --days 7` - Historial de trades

---

## 🛠️ **MANTENIMIENTO**

### **Comandos de Sistema**
- `/restart_system` - Reiniciar sistema completo
- `/clear_cache` - Limpiar cache del sistema
- `/update_models` - Actualizar modelos
- `/shutdown` - Apagar sistema

---

## 💡 **EJEMPLOS DE USO PRÁCTICOS**

### **Flujo de Trabajo Completo**

#### **1. Configuración Inicial**
```
/set_mode paper
/set_symbols BTCUSDT,ETHUSDT,ADAUSDT
/set_leverage BTCUSDT 10
/set_leverage ETHUSDT 15
```

#### **2. Descarga y Análisis de Datos**
```
/download_data --symbols BTCUSDT,ETHUSDT --days 30
/analyze_data BTCUSDT
/align_data --symbols BTCUSDT,ETHUSDT
/data_status
```

#### **3. Entrenamiento de Agentes**
```
/train --symbols BTCUSDT,ETHUSDT --duration 8h
/training_status
/agents
/agent_status BTCUSDT
```

#### **4. Testing y Validación**
```
/backtest BTCUSDT --days 7
/backtest ETHUSDT --days 7
/performance_report
```

#### **5. Trading en Vivo**
```
/trade --mode paper --symbols BTCUSDT,ETHUSDT
/status
/metrics
/positions
```

#### **6. Monitoreo Continuo**
```
/health
/risk_report
/trades_history --days 1
/agent_analysis BTCUSDT
```

#### **7. Gestión de Posiciones**
```
/close_position BTCUSDT
/positions
/balance
```

#### **8. Mantenimiento**
```
/clear_cache
/update_models
/restart_system
```

---

## 🔒 **SEGURIDAD Y AUTORIZACIÓN**

### **Características de Seguridad**
- ✅ **Restricción por Chat ID** - Solo tu Chat ID puede usar comandos
- ✅ **Encriptación** - Token y datos sensibles encriptados
- ✅ **Validación de argumentos** - Todos los comandos validan parámetros
- ✅ **Rate limiting** - Protección contra spam
- ✅ **Auditoría completa** - Todos los comandos se registran en logs

### **Comandos Críticos con Confirmación**
- `/trade --mode live` - Requiere confirmación para trading real
- `/emergency_stop` - Requiere confirmación para parada de emergencia
- `/restart_system` - Requiere confirmación para reinicio
- `/shutdown` - Requiere confirmación para apagado

---

## 📱 **USO DESDE MÓVIL**

### **Ventajas del Control Móvil**
- 🚀 **Acceso 24/7** - Control desde cualquier lugar
- 📊 **Métricas en tiempo real** - Información actualizada constantemente
- ⚡ **Respuesta rápida** - Comandos ejecutados instantáneamente
- 🔔 **Alertas automáticas** - Notificaciones de eventos importantes
- 📈 **Dashboard integrado** - Gráficos y métricas en el navegador

### **Flujo de Trabajo Móvil**
1. **Iniciar sistema**: `python run_bot.py`
2. **Dashboard automático**: Se abre en `http://localhost:8050`
3. **Bot de Telegram**: Listo para comandos
4. **Control completo**: Todos los comandos disponibles desde móvil

---

## 🎯 **COMANDOS MÁS UTILIZADOS**

### **Para Uso Diario**
- `/status` - Estado general
- `/metrics` - Métricas actuales
- `/positions` - Posiciones abiertas
- `/health` - Salud del sistema

### **Para Entrenamiento**
- `/train --symbols BTC,ETH --duration 8h`
- `/training_status`
- `/agents`
- `/model_info BTCUSDT`

### **Para Trading**
- `/trade --mode paper --symbols BTC,ETH`
- `/stop_trading`
- `/close_position BTCUSDT`
- `/set_leverage BTCUSDT 20`

### **Para Análisis**
- `/performance_report`
- `/risk_report`
- `/agent_analysis BTCUSDT`
- `/backtest BTCUSDT --days 7`

---

## 🚀 **INICIO RÁPIDO**

### **1. Configuración Inicial**
```bash
# Obtener Chat ID
python notifications/telegram/get_chat_id.py

# Editar config.yaml con tu Chat ID
# Reemplazar <YOUR_CHAT_ID> con tu ID real
```

### **2. Instalar Dependencias**
```bash
pip install python-telegram-bot>=20.7
pip install dash>=2.14.0
pip install plotly>=5.17.0
```

### **3. Ejecutar Sistema**
```bash
python run_bot.py
```

### **4. Usar Comandos**
- El sistema se inicia automáticamente
- Dashboard se abre en el navegador
- Bot de Telegram queda listo
- Usa `/help` para ver todos los comandos

---

## 📞 **SOPORTE**

### **Comandos de Ayuda**
- `/help` - Lista completa de comandos
- `/start` - Mensaje de bienvenida
- `/settings` - Configuración actual

### **Solución de Problemas**
- Verificar Chat ID en `config.yaml`
- Comprobar conexión a internet
- Revisar logs del sistema
- Usar `/health` para diagnóstico

---

**¡El sistema está completamente operativo y listo para usar desde tu móvil!** 🚀📱💹
