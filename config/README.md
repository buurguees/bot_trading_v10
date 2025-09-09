# 📁 config/ - Configuración del Usuario

> **Propósito**: Configuración personalizable del usuario y variables de entorno.

## 🎯 ORGANIZACIÓN DE ARCHIVOS

```
config/
├── user_settings.yaml          # 👤 Configuración personalizable del usuario
├── .env.example                # 🔐 Variables de entorno (ejemplo)
└── README.md                   # 📄 Esta documentación
```

## 🔧 CONFIGURACIÓN DEL USUARIO

### **user_settings.yaml**
Archivo principal de configuración que permite personalizar el bot sin tocar código:

```yaml
# Configuración general del bot
bot_settings:
  name: "TradingBot_v10_Alex"
  trading_mode: "aggressive"  # conservative/moderate/aggressive/custom
  
# Gestión de capital y riesgo
capital_management:
  initial_balance: 1000.0
  max_risk_per_trade: 2.0
  max_daily_loss_pct: 5.0

# Configuración de trading
trading_settings:
  symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
  timeframes: ["1h", "4h", "1d"]
  
# Configuración del modelo IA
ai_model_settings:
  confidence:
    min_confidence_to_trade: 65.0
```

### **.env.example**
Variables de entorno para API keys y configuraciones sensibles:

```env
# API Keys (copiar a .env y configurar)
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_key_here
BITGET_PASSPHRASE=your_passphrase_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Base de datos
DATABASE_URL=sqlite:///data/trading_bot.db
```

## 🔗 CONEXIÓN CON CORE

Las configuraciones YAML de dominio (trading, riesgo, infraestructura, etc.) se encuentran en:
- `core/config/enterprise/` - Configuraciones enterprise por dominio

El sistema carga automáticamente:
1. `config/user_settings.yaml` - Configuración del usuario
2. `core/config/enterprise/*.yaml` - Configuraciones de dominio
3. Variables de entorno desde `.env`

## 🚀 USO

### **Para Usuarios**
1. Editar `config/user_settings.yaml` según tus preferencias
2. Copiar `.env.example` a `.env` y configurar API keys
3. Reiniciar el bot para aplicar cambios

### **Para Desarrolladores**
```python
from core.config.enterprise_config import EnterpriseConfigManager
from core.config.config_loader import ConfigLoader

# Cargar configuración
config_manager = EnterpriseConfigManager('config/user_settings.yaml')
user_config = config_manager.load_config()

# Acceder a valores
trading_mode = user_config.get('bot_settings.trading_mode')
initial_balance = user_config.get('capital_management.initial_balance')
```

## ⚠️ IMPORTANTE

- **NUNCA** commitees el archivo `.env` (contiene API keys)
- **SIEMPRE** usa `.env.example` como plantilla
- Los cambios en `user_settings.yaml` requieren reinicio del bot
- Las configuraciones enterprise en `core/config/enterprise/` son para desarrolladores
