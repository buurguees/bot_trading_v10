# Scripts de Entrenamiento Antiguos - Movidos a _old

Este directorio contiene todos los scripts de entrenamiento antiguos que han sido reemplazados por los nuevos scripts en `scripts/train/`.

## 📁 Estructura

```
_old/training_scripts/
├── enterprise/          # Scripts de entrenamiento enterprise
├── autonomous/          # Scripts de entrenamiento autónomo
├── legacy/             # Scripts legacy de entrenamiento
├── root/               # Scripts de root para entrenamiento
└── README.md           # Este archivo
```

## 🔄 Scripts Movidos

### Enterprise (`enterprise/`)
- `start_8h_training.py` - Script de entrenamiento de 8 horas
- `start_distributed_training.py` - Entrenamiento distribuido
- `hyperparameter_optimization.py` - Optimización de hiperparámetros
- `run_enterprise_training.py` - Ejecutor principal enterprise
- `training.yaml` - Configuración de entrenamiento enterprise
- `training_monitor.py` - Monitor de entrenamiento enterprise
- `training_engine.py` - Motor de entrenamiento enterprise
- `distributed_trainer.py` - Entrenador distribuido
- `ENTERPRISE_TRAINING_SYSTEM.md` - Documentación del sistema
- `ENTERPRISE_TRAINING_IMPLEMENTATION_SUMMARY.md` - Resumen de implementación
- `test_enterprise_training.py` - Tests unitarios

### Autonomous (`autonomous/`)
- `run_autonomous_training.py` - Ejecutor de entrenamiento autónomo
- `setup_autonomous_training.py` - Configuración de entrenamiento autónomo
- `start_autonomous_training.bat` - Script batch para Windows
- `start_autonomous_training.sh` - Script shell para Linux/Mac

### Legacy (`legacy/`)
- `run_fixed_training.py` - Entrenamiento con datos fijos
- `run_simple_training.py` - Entrenamiento simple
- `train_background.py` - Entrenamiento en background
- `start_training.py` - Script de inicio de entrenamiento
- `start_night_training.py` - Entrenamiento nocturno
- `training_data.csv` - Datos de entrenamiento
- `training_data_fixed.csv` - Datos de entrenamiento fijos

### Root (`root/`)
- `start_6h_training_enterprise.py` - Script de 6 horas enterprise
- `monitor_training.py` - Monitor de entrenamiento

## 🆕 Scripts Nuevos

Los scripts de entrenamiento han sido reemplazados por:

- `scripts/train/train_historical.py` - Entrenamiento histórico
- `scripts/train/train_live.py` - Entrenamiento en vivo
- `scripts/train/state_manager.py` - Gestión de estado
- `scripts/train/config.yaml` - Configuración unificada

## 📱 Comandos de Telegram

Los nuevos comandos disponibles son:

- `/train_hist` - Entrenamiento histórico
- `/train_live` - Entrenamiento en vivo
- `/training_status` - Estado del entrenamiento

## 🔧 Uso

Los scripts antiguos están disponibles en este directorio por si necesitas consultarlos o recuperar alguna funcionalidad específica. Sin embargo, se recomienda usar los nuevos scripts en `scripts/train/` que ofrecen:

- Mejor integración con Telegram
- Sincronización multi-símbolo
- Sistema de penalizaciones
- Métricas en tiempo real
- Configuración unificada
- Mejor documentación

## 📅 Fecha de Movimiento

Scripts movidos el: 09/09/2025

## ⚠️ Nota

Estos scripts están en `_old` y no se mantienen activamente. Para cualquier funcionalidad de entrenamiento, usar los scripts en `scripts/train/`.
