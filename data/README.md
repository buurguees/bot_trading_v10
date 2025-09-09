# 📁 data/ - Almacenamiento de Datos

> **Propósito**: Almacenamiento centralizado de todos los datos del bot de trading.

## 🎯 ORGANIZACIÓN DE ARCHIVOS

```
data/
├── historical/              # 📊 Datos históricos por símbolo
│   ├── BTCUSDT_1h.csv      # Datos de Bitcoin 1 hora
│   ├── ETHUSDT_4h.csv      # Datos de Ethereum 4 horas
│   └── ...
├── models/                  # 🤖 Modelos de IA entrenados
│   ├── BTCUSDT_model.json  # Modelo para Bitcoin
│   ├── ETHUSDT_model.json  # Modelo para Ethereum
│   └── ...
├── checkpoints/             # 💾 Puntos de control del entrenamiento
│   ├── training_state.pkl  # Estado del entrenamiento
│   └── ...
├── logs/                    # 📝 Logs del sistema
│   ├── bot.log             # Log principal
│   ├── trading.log         # Log de trading
│   └── ...
├── alignments/              # 🔄 Alineaciones temporales
│   └── ...
├── trading_bot.db           # 🗄️ Base de datos SQLite
├── trading_bot.db-shm       # Archivo de memoria compartida
├── trading_bot.db-wal       # Archivo de write-ahead log
└── README.md               # 📄 Esta documentación
```

## 📊 TIPOS DE DATOS

### **historical/**
Datos históricos de precios y volúmenes por símbolo y timeframe:
- Formato: CSV con columnas estándar (timestamp, open, high, low, close, volume)
- Frecuencia: Actualización automática cada hora
- Retención: 5 años de datos históricos
- Símbolos: BTCUSDT, ETHUSDT, ADAUSDT, etc.

### **models/**
Modelos de machine learning entrenados:
- Formato: JSON con arquitectura y pesos
- Entrenamiento: Automático cada noche
- Validación: Cross-validation con datos históricos
- Versiones: Múltiples versiones con timestamps

### **checkpoints/**
Puntos de control del entrenamiento:
- Estado del entrenamiento (epoch, loss, metrics)
- Configuración de hiperparámetros
- Datos de validación
- Permite reanudar entrenamiento interrumpido

### **logs/**
Logs del sistema organizados por módulo:
- `bot.log`: Log principal del bot
- `trading.log`: Actividad de trading
- `training.log`: Proceso de entrenamiento
- `enterprise/`: Logs específicos enterprise
- Rotación: Automática cada 24 horas

### **Base de Datos**
- **trading_bot.db**: Base de datos SQLite principal
- **trading_bot.db-shm**: Memoria compartida (temporal)
- **trading_bot.db-wal**: Write-ahead log (temporal)

## 🔄 GESTIÓN DE DATOS

### **Descarga de Datos Históricos**
```bash
# Desde Telegram
/download_history --symbol BTCUSDT --timeframe 1h --days 30

# Desde script
python scripts/history/download_history.py --symbol BTCUSDT --timeframe 1h
```

### **Inspección de Datos**
```bash
# Verificar calidad de datos
python scripts/history/inspect_history.py --symbol BTCUSDT

# Reparar datos corruptos
python scripts/history/repair_history.py --symbol BTCUSDT
```

### **Limpieza de Logs**
```bash
# Limpiar logs antiguos
python scripts/maintenance/logs_cleanup.py --days 30
```

## ⚠️ IMPORTANTE

- **Backup**: Los datos críticos se respaldan automáticamente
- **Espacio**: Monitorear espacio en disco (datos históricos crecen rápido)
- **Integridad**: Verificar integridad de datos regularmente
- **Seguridad**: Los archivos de base de datos contienen información sensible

## 🔧 CONFIGURACIÓN

### **Retención de Datos**
```yaml
# En core/config/enterprise/data_collection.yaml
retention:
  historical_days: 1825  # 5 años
  logs_days: 30
  checkpoints_days: 90
```

### **Límites de Espacio**
```yaml
# En core/config/enterprise/infrastructure.yaml
storage:
  max_historical_gb: 50
  max_logs_gb: 10
  cleanup_threshold: 0.8  # 80% de uso
```
