# Directorio de Agentes - Trading Bot v10 Enterprise

Este directorio contiene todos los modelos de agentes, checkpoints y estrategias del sistema de trading.

## 📁 Estructura

```
agents/
├── models/              # Modelos por símbolo
│   ├── BTCUSDT/        # Modelo para BTCUSDT
│   ├── ETHUSDT/        # Modelo para ETHUSDT
│   └── ADAUSDT/        # Modelo para ADAUSDT
├── checkpoints/         # Checkpoints de entrenamiento
├── strategies/          # Estrategias guardadas
└── README.md           # Este archivo
```

## 🤖 Modelos de Agentes

### Estructura por Símbolo
Cada símbolo tiene su propio directorio con:
- `model_weights.json` - Pesos del modelo actual
- `progress_cycle_X.json` - Progreso en cada ciclo
- `checkpoint_cycle_X.pkl` - Checkpoint del modelo

### Ejemplo de `model_weights.json`:
```json
{
  "symbol": "BTCUSDT",
  "cycle_id": 150,
  "timestamp": "2025-09-09T16:59:00",
  "performance_weight": 0.85,
  "win_rate": 65.2,
  "sharpe_ratio": 1.8,
  "last_updated": "2025-09-09T16:59:00",
  "status": "updated"
}
```

## 📊 Checkpoints

Los checkpoints se guardan automáticamente cada X ciclos (configurable en `config.yaml`):
- `checkpoint_cycle_X.pkl` - Checkpoint del modelo
- Contiene el estado completo del agente
- Permite reanudar entrenamiento desde cualquier punto

## 🎯 Estrategias

Las estrategias se guardan en `strategies/`:
- `{symbol}_strategies.json` - Estrategias por símbolo
- Incluye métricas de rendimiento
- KPIs y estadísticas de trading

## ⚙️ Configuración

### Guardado Automático
```yaml
general:
  auto_save_cycles: 10  # Guardar cada 10 ciclos
  agents_directory: "agents"
  enable_infinite_mode: true
```

### Comandos de Telegram
- `/train_hist` - Entrenamiento histórico infinito
- `/train_live` - Entrenamiento en vivo infinito
- `/stop_train` - Detener entrenamiento de forma elegante

## 🔄 Flujo de Trabajo

1. **Entrenamiento Iniciado**: Se crean directorios por símbolo
2. **Ciclos de Entrenamiento**: Cada ciclo actualiza métricas
3. **Guardado Automático**: Cada X ciclos se guarda progreso
4. **Actualización de Modelos**: Los pesos se actualizan basados en rendimiento
5. **Parada Elegante**: `/stop_train` guarda todo y crea resumen

## 📈 Métricas Guardadas

### Por Ciclo
- Win Rate
- Sharpe Ratio
- Max Drawdown
- Total Trades
- Equity
- Estrategias utilizadas

### Por Símbolo
- Rendimiento individual
- KPIs específicos
- Historial de estrategias
- Estadísticas de penalizaciones

## 🛡️ Seguridad

- Los modelos se guardan de forma segura
- Checkpoints permiten recuperación
- Resúmenes finales para auditoría
- Logs detallados de cada operación

## 📅 Mantenimiento

### Limpieza Automática
- Los checkpoints antiguos se pueden limpiar
- Las estrategias se mantienen por historial
- Los logs se rotan automáticamente

### Respaldo
- Los modelos se respaldan en cada guardado
- Los checkpoints permiten rollback
- Los resúmenes se mantienen permanentemente

## 🚀 Uso

### Iniciar Entrenamiento
```bash
# Desde Telegram
/train_hist
/train_live

# Desde línea de comandos
python scripts/train/train_historical.py
python scripts/train/train_live.py
```

### Detener Entrenamiento
```bash
# Desde Telegram
/stop_train

# Desde código
trainer.stop_training_gracefully()
```

## 📋 Estado del Sistema

El sistema mantiene un estado consistente:
- **Modo Infinito**: Los entrenamientos continúan hasta `/stop_train`
- **Guardado Automático**: Progreso guardado cada X ciclos
- **Actualización Continua**: Modelos mejoran con cada ciclo
- **Recuperación**: Sistema puede reanudar desde cualquier checkpoint

## 🔧 Troubleshooting

### Problemas Comunes
1. **Directorio no existe**: Se crea automáticamente
2. **Permisos**: Verificar permisos de escritura
3. **Espacio**: Monitorear espacio en disco
4. **Corrupción**: Usar checkpoints para recuperación

### Logs
- `logs/train/` - Logs de entrenamiento
- `logs/bot.log` - Logs generales del sistema
- `artifacts/` - Resúmenes y artefactos

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs en `logs/train/`
2. Verificar configuración en `config.yaml`
3. Comprobar estado en Telegram con `/status`
4. Usar `/stop_train` para parada segura

---

**Nota**: Este directorio es crítico para el funcionamiento del sistema. No eliminar archivos manualmente sin respaldo.
