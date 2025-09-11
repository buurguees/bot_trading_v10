# 📁 config/ - Sistema de Configuración Unificado (v2)

> **Propósito**: Proveer una arquitectura modular, sin duplicaciones y con fuente única de verdad para símbolos, timeframes y objetivos del sistema.

## 🎯 Nueva Organización

```
config/
├── core/                      # Configuraciones centrales (fuente única)
│   ├── symbols.yaml           # ÚNICA fuente de símbolos y timeframes
│   ├── training_objectives.yaml  # Objetivos de entrenamiento/negocio
│   ├── rewards.yaml           # Recompensas y penalizaciones
│   └── data_sources.yaml      # Fuentes de datos y parámetros de colección
│
├── environments/              # Configs por entorno
│   ├── development.yaml
│   ├── production.yaml
│   └── testing.yaml
│
├── features/                  # Configs por funcionalidad
│   ├── ml.yaml
│   ├── monitoring.yaml
│   ├── risk_management.yaml
│   └── telegram.yaml
│
├── user_settings.yaml         # Overrides del usuario (referencias a grupos)
└── README.md
```

## 🔧 Puntos Clave
- **Fuente única de símbolos/timeframes**: `core/symbols.yaml`.
- **Objetivos unificados**: `core/training_objectives.yaml` (ROI, winrate, drawdown, etc.).
- **Jerarquía de resolución**: `environments` > `user_settings` > `features` > `core`.
- **Referencias**: soporta `${training_objectives.financial_targets.balance.initial}`.
- **Variables de entorno**: se cargan desde `config/.env` o `.env` si existen (opcional).

## ✍️ user_settings.yaml (overrides por referencias)
```yaml
bot_settings:
  name: "TradingBot_v10_Alex"

# Referencias a grupos definidos en core/symbols.yaml
active_symbol_groups: ["primary"]
active_timeframes: ["real_time", "analysis"]

# Ejemplo de override directo
capital_management:
  initial_balance: 1000.0
  max_risk_per_trade: 2.0
  max_daily_loss_pct: 5.0
```

## 🧠 Unified Config Manager v2
- Archivo: `config/unified_config.py`
- Clase principal: `UnifiedConfigManager`

### Acceso básico
```python
from config.unified_config import UnifiedConfigManager

config = UnifiedConfigManager(environment="development")

symbols = config.get_symbols()                 # desde core/symbols.yaml
timeframes = config.get_timeframes()           # desde core/symbols.yaml
objectives = config.get_training_objectives()  # desde core/training_objectives.yaml
initial_balance = config.get_initial_balance() # con fallbacks inteligentes
telegram = config.get_telegram_config()        # features + variables de entorno
```

### Validación y estado
```python
validation = config.validate_trading_config()
status = config.get_config_status()
```

## 🚀 Flujo recomendado
1) Define símbolos/timeframes en `core/symbols.yaml`.
2) Usa `user_settings.yaml` para indicar grupos activos (`active_symbol_groups`, `active_timeframes`).
3) Ajusta objetivos en `core/training_objectives.yaml`.
4) Habilita funcionalidades en `features/*.yaml` (ML, monitoreo, Telegram, riesgo).
5) Selecciona entorno con `UnifiedConfigManager(environment=...)`.

## ⚠️ Importante
- No dupliques símbolos/timeframes fuera de `core/symbols.yaml`.
- No commitees `config/.env` si contiene secretos.
- Cambios en `user_settings.yaml` pueden requerir reiniciar el bot.
