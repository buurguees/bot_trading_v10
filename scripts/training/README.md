# Scripts de Entrenamiento - Trading Bot v10 Enterprise

Este directorio contiene los scripts de entrenamiento avanzado para el sistema de trading, incluyendo entrenamiento histórico y en tiempo real.

## 📁 Estructura

```
scripts/train/
├── train_hist_parallel.py  # Entrenamiento histórico paralelo (principal)
├── train_live.py          # Entrenamiento en tiempo real (paper trading)
├── state_manager.py       # Gestión de estado y sincronización
├── config.yaml           # Configuración de los scripts
└── README.md             # Este archivo
```

## 🚀 Uso Rápido

### Entrenamiento Histórico Paralelo
```bash
# Uso básico
python scripts/training/train_hist_parallel.py --progress-file data/tmp/progress.json
```

### Entrenamiento en Vivo
```bash
# Uso básico
python scripts/train/train_live.py

# Con parámetros personalizados
python scripts/train/train_live.py --cycle_minutes 60 --update_every 10

# Con configuración personalizada
python scripts/train/train_live.py --config custom_config.yaml
```

### Desde Telegram
```
/train_hist --cycle_size 500 --update_every 25
/train_live --cycle_minutes 30 --update_every 5
```

## 📊 Características

### Entrenamiento Histórico Paralelo (`train_hist_parallel.py`)
- **Sincronización multi-símbolo**: Todos los símbolos avanzan en paralelo
- **Ciclos configurables**: Tamaño de ciclo y frecuencia de actualización
- **Métricas en tiempo real**: Actualizaciones periódicas via Telegram
- **Sistema de penalizaciones**: Reset automático y penalización de estrategias
- **Persistencia de estado**: Guardado automático de progreso y artefactos

### Entrenamiento en Vivo (`train_live.py`)
- **Paper trading**: Balance ficticio con datos reales
- **Streams en tiempo real**: Conexión a WebSockets de exchanges
- **Registro de datos**: Almacenamiento automático en histórico
- **Evaluación de estrategias**: Aplicación de estrategias aprendidas
- **Métricas en vivo**: Monitoreo en tiempo real via Telegram

### Gestión de Estado (`state_manager.py`)
- **Sincronización**: Barreras para coordinación multi-símbolo
- **Persistencia**: Guardado y recuperación de sesiones
- **Penalizaciones**: Sistema de penalización y resets
- **Métricas agregadas**: Cálculo de KPIs globales

## ⚙️ Configuración

### Archivo de Configuración (`config.yaml`)

```yaml
# Configuración de entrenamiento histórico
historical:
  cycle_size_bars: 500
  update_every_bars: 25
  symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
  risk:
    initial_balance: 1000.0
    per_trade_pct: 0.5
    max_exposure_pct: 20.0

# Configuración de entrenamiento en vivo
live:
  cycle_minutes: 30
  update_every_seconds: 5
  symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
  exchanges:
    binance:
      testnet: true
      websocket_url: "wss://testnet.binance.vision/ws/"
```

### Variables de Entorno

```bash
# Token de Telegram (opcional, se puede usar encriptado)
export TELEGRAM_BOT_TOKEN="tu_token_aqui"

# Clave de encriptación (opcional)
export ENCRYPTION_KEY="tu_clave_aqui"

# Configuración de base de datos (opcional)
export DATABASE_URL="postgresql://user:pass@localhost:5432/trading"
export REDIS_URL="redis://localhost:6379"
```

## 📈 Métricas y Monitoreo

### Métricas en Tiempo Real
- **Progreso**: Porcentaje completado del ciclo
- **Equity**: Balance total y por símbolo
- **PnL**: Ganancia/pérdida del ciclo y acumulada
- **Trades**: Número total, ganadores, perdedores
- **Win Rate**: Porcentaje de trades ganadores
- **Drawdown**: Drawdown máximo y actual
- **Latencia**: Tiempo de procesamiento
- **CPU/Memoria**: Uso de recursos del sistema

### Artefactos Generados
- **Estrategias**: `strategies_cycle_X.json`
- **KPIs**: `cycle_X.json`
- **Trades**: `{symbol}_trades.jsonl`
- **Estado**: `live_status.json`
- **Penalizaciones**: `{symbol}_penalties.jsonl`

## 🔧 Parámetros de Línea de Comandos

### Entrenamiento Histórico
```bash
python scripts/training/train_hist_parallel.py [opciones]
```

### Entrenamiento en Vivo
```bash
python train_live.py [opciones]

Opciones:
  --cycle_minutes N        Duración del ciclo en minutos (default: 30)
  --update_every N         Actualizar cada N segundos (default: 5)
  --config FILE            Archivo de configuración (default: config.yaml)
  --symbols SYMBOLS        Símbolos a procesar (default: del config)
  --max_cycles N           Máximo número de ciclos (default: 1000)
  --output_dir DIR         Directorio de salida (default: artifacts/)
  --log_level LEVEL        Nivel de logging (default: INFO)
```

## 📱 Integración con Telegram

### Comandos Disponibles
- `/train_hist` - Iniciar entrenamiento histórico
- `/train_live` - Iniciar entrenamiento en vivo
- `/training_status` - Estado del entrenamiento
- `/stop_training` - Detener entrenamiento

### Ejemplos de Uso
```
# Entrenamiento histórico básico
/train_hist

# Entrenamiento histórico con parámetros
/train_hist --cycle_size 1000 --update_every 50

# Entrenamiento en vivo básico
/train_live

# Entrenamiento en vivo con parámetros
/train_live --cycle_minutes 60 --update_every 10

# Ver estado del entrenamiento
/training_status
```

## 🛠️ Desarrollo y Personalización

### Agregar Nuevas Estrategias
1. Modificar `state_manager.py` para incluir la nueva estrategia
2. Actualizar la configuración en `config.yaml`
3. Implementar la lógica de trading en los scripts

### Personalizar Métricas
1. Modificar `_calculate_kpis()` en `state_manager.py`
2. Actualizar `_render_live_status()` en los scripts
3. Agregar nuevas métricas a la configuración

### Integrar Nuevos Exchanges
1. Agregar configuración en `config.yaml`
2. Implementar conexión WebSocket en `train_live.py`
3. Actualizar el mapeo de datos de mercado

## 🐛 Solución de Problemas

### Errores Comunes

#### "No se pudieron cargar datos históricos"
- Verificar que existan archivos CSV en `data/historical/`
- Comprobar formato de los archivos (OHLCV)
- Revisar permisos de lectura

#### "Error conectando WebSocket"
- Verificar conectividad a internet
- Comprobar URLs de WebSocket en configuración
- Revisar credenciales de API (si es necesario)

#### "Error de sincronización"
- Verificar que todos los símbolos tengan datos
- Comprobar alineación de timestamps
- Revisar configuración de barreras

#### "Error de memoria"
- Reducir `cycle_size` o `update_every`
- Aumentar memoria disponible
- Procesar menos símbolos simultáneamente

### Logs y Debugging
```bash
# Ver logs en tiempo real del histórico paralelo
tail -f data/logs/train_hist_parallel.log
tail -f logs/train_live.log

# Ver logs con filtro
grep "ERROR" logs/train_*.log
grep "WARNING" logs/train_*.log
```

## 📚 Referencias

- [Documentación de Trading Bot v10](../README.md)
- [Configuración de Telegram](../notifications/telegram/README.md)
- [API de Exchanges](../src/core/data/README.md)
- [Sistema de ML](../src/core/ml/README.md)

## 🤝 Contribución

Para contribuir a los scripts de entrenamiento:

1. Fork del repositorio
2. Crear rama para la feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit de cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](../LICENSE) para más detalles.
