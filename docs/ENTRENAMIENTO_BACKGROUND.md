# 🤖 Entrenamiento Background - Trading Bot v10

## Descripción

El sistema de entrenamiento background permite ejecutar el bot de trading sin la interfaz del dashboard, ideal para:

- **Servidores de producción** sin interfaz gráfica
- **Entrenamiento nocturno** automático
- **Desarrollo paralelo** mientras trabajas en el dashboard
- **Entrenamiento de larga duración** sin supervisión

## 🚀 Opciones de Entrenamiento

### 1. Desde el Menú Principal (`app.py`)

```bash
python app.py
```

**Opción 5: 🤖 Entrenamiento sin Dashboard (Background)**

- Selecciona modo de entrenamiento
- Configura duración
- Monitoreo en tiempo real
- Logs detallados

### 2. Inicio Rápido (`start_training.py`)

```bash
# Entrenamiento básico (8 horas, paper trading)
python start_training.py

# Entrenamiento personalizado
python start_training.py --mode paper_trading --duration 12h --verbose

# Entrenamiento de desarrollo
python start_training.py --mode development --duration 4h

# Aprendizaje continuo indefinido
python start_training.py --mode continuous_learning --duration indefinite
```

### 3. Entrenamiento Nocturno (`scripts/start_night_training.py`)

```bash
# Programar entrenamiento nocturno (22:00, 10 horas)
python scripts/start_night_training.py

# Entrenamiento inmediato
python scripts/start_night_training.py --immediate

# Configuración personalizada
python scripts/start_night_training.py --start-time 23:00 --duration 12h

# Ver estado del programador
python scripts/start_night_training.py --status
```

## 🎯 Modos de Entrenamiento

### 1. **Paper Trading** (Recomendado)
- Trading simulado sin riesgo real
- Datos de mercado reales
- Ideal para validar estrategias
- **Duración recomendada**: 4-12 horas

### 2. **Backtesting**
- Pruebas con datos históricos
- Validación de estrategias pasadas
- Análisis de rendimiento histórico
- **Duración recomendada**: 2-8 horas

### 3. **Development**
- Modo de desarrollo y debugging
- Logs detallados
- Pruebas de componentes
- **Duración recomendada**: 1-4 horas

### 4. **Continuous Learning**
- Aprendizaje continuo del modelo
- Entrenamiento prolongado
- Ideal para entrenamiento nocturno
- **Duración recomendada**: 8-24 horas

## ⏰ Duraciones Disponibles

| Duración | Descripción | Uso Recomendado |
|----------|-------------|-----------------|
| `1h` | 1 hora | Pruebas rápidas |
| `4h` | 4 horas | Sesiones cortas |
| `8h` | 8 horas | Entrenamiento estándar |
| `12h` | 12 horas | Entrenamiento nocturno |
| `24h` | 24 horas | Entrenamiento intensivo |
| `indefinite` | Indefinido | Aprendizaje continuo |

## 📊 Monitoreo del Entrenamiento

### Logs del Sistema

```bash
# Logs principales del bot
tail -f logs/trading_bot.log

# Logs específicos de entrenamiento
tail -f logs/agent_training.log

# Logs del entrenamiento nocturno
tail -f logs/night_training.log

# Logs del dashboard (si está activo)
tail -f logs/dashboard.log
```

### Archivos de Monitoreo

- **`logs/trading_bot.log`**: Logs generales del sistema
- **`logs/agent_training.log`**: Logs específicos del entrenamiento
- **`logs/night_training.log`**: Logs del programador nocturno
- **`data/trading_bot.db`**: Base de datos con datos y resultados
- **`models/saved_models/`**: Modelos entrenados guardados

### Comandos de Monitoreo

```bash
# Ver procesos activos
ps aux | grep python

# Ver uso de recursos
htop

# Ver logs en tiempo real
tail -f logs/agent_training.log | grep -E "(EPOCH|LOSS|ACCURACY)"

# Verificar estado de la base de datos
sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM market_data;"
```

## 🔧 Configuración Avanzada

### Variables de Entorno

```bash
# Configurar modo de trading
export TRADING_MODE=paper_trading

# Configurar duración
export TRAINING_DURATION=8h

# Modo background
export BACKGROUND_MODE=true

# Deshabilitar dashboard
export DASHBOARD_ENABLED=false
```

### Configuración de Logging

```python
# En config/logging_config.yaml
background_training:
  level: INFO
  file: logs/agent_training.log
  max_size: 100MB
  backup_count: 5
```

## 🛠️ Solución de Problemas

### Problemas Comunes

#### 1. **Error de Datos Insuficientes**
```bash
⚠️ Datos insuficientes: 500 registros
```
**Solución**: Descargar más datos históricos
```bash
python app.py
# Seleccionar opción 1: Descargar datos históricos
```

#### 2. **Error de Permisos**
```bash
❌ Permission denied: logs/agent_training.log
```
**Solución**: Verificar permisos de escritura
```bash
chmod 755 logs/
touch logs/agent_training.log
```

#### 3. **Proceso No Se Detiene**
```bash
# Encontrar proceso
ps aux | grep python

# Detener proceso específico
kill -TERM <PID>

# Forzar detención
kill -KILL <PID>
```

#### 4. **Memoria Insuficiente**
```bash
# Monitorear uso de memoria
htop
free -h

# Reducir duración del entrenamiento
python start_training.py --duration 4h
```

### Logs de Debugging

```bash
# Modo verbose para debugging
python start_training.py --verbose

# Logs detallados del sistema
export LOG_LEVEL=DEBUG
python start_training.py
```

## 📈 Optimización del Rendimiento

### Para Servidores

1. **Configurar límites de memoria**:
```bash
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

2. **Usar modo de desarrollo** para pruebas:
```bash
python start_training.py --mode development --duration 1h
```

3. **Monitorear recursos**:
```bash
# Instalar htop si no está disponible
sudo apt install htop
htop
```

### Para Entrenamiento Nocturno

1. **Configurar cron job**:
```bash
# Editar crontab
crontab -e

# Agregar entrada para 22:00 todos los días
0 22 * * * cd /path/to/bot && python scripts/start_night_training.py
```

2. **Configurar reinicio automático**:
```bash
# Script de reinicio automático
#!/bin/bash
while true; do
    python start_training.py --mode continuous_learning --duration indefinite
    sleep 300  # Esperar 5 minutos antes de reiniciar
done
```

## 🎯 Mejores Prácticas

### 1. **Entrenamiento Gradual**
- Comenzar con duraciones cortas (1-4 horas)
- Aumentar gradualmente según el rendimiento
- Monitorear logs regularmente

### 2. **Backup de Modelos**
- Los modelos se guardan automáticamente en `models/saved_models/`
- Hacer backup regular de modelos exitosos
- Documentar configuraciones que funcionan bien

### 3. **Monitoreo Continuo**
- Revisar logs al menos una vez al día
- Verificar que el entrenamiento no se detenga inesperadamente
- Monitorear uso de recursos del sistema

### 4. **Configuración de Red**
- Asegurar conexión estable a internet
- Configurar proxy si es necesario
- Verificar límites de API de exchanges

## 📞 Soporte

Si encuentras problemas:

1. **Revisar logs** para identificar errores específicos
2. **Verificar configuración** de variables de entorno
3. **Probar con modo development** para debugging
4. **Consultar documentación** de componentes específicos

---

**¡El sistema de entrenamiento background está listo para usar!** 🚀

Puedes comenzar con `python start_training.py` para un entrenamiento básico o usar el menú principal con `python app.py` para más opciones.
