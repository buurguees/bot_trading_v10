# 🔧 Diagnóstico y Solución de Problemas - Bot Trading v10

## 🚨 Problemas comunes

### 1) Imports y dependencias
```
ModuleNotFoundError: No module named 'control'
ModuleNotFoundError: No module named 'core'
ImportError: cannot import name 'X' from 'Y'
```

### 2) Configuración
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/user_settings.yaml'
KeyError: 'TELEGRAM_BOT_TOKEN'
AttributeError: 'NoneType' object has no attribute 'X'
```

### 3) Telegram
```
telegram.error.NetworkError: HTTPSConnectionPool
telegram.error.Unauthorized: 401 Unauthorized
AttributeError: 'Handlers' object has no attribute 'X_command'
```

## 🛠️ Soluciones paso a paso

### PASO 1: Verificar estructura del proyecto
```
cd bot_trading_v10
ls -la
```
Debe existir: `bot.py`, `control/`, `scripts/`, `core/`, `config/`, `data/`.

### PASO 2: Variables de entorno
```
copy config\.env.example .env
notepad .env
```
Contenido mínimo:
```
TELEGRAM_BOT_TOKEN=xxxx
TELEGRAM_CHAT_ID=xxxx
BITGET_API_KEY=xxxx
BITGET_SECRET_KEY=xxxx
BITGET_PASSPHRASE=xxxx
DATABASE_URL=sqlite:///data/trading_bot.db
REDIS_URL=redis://localhost:6379
```

### PASO 3: Configuración de Telegram (opcional)
Archivo sugerido `control/config.yaml`:
```
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
  enabled: true

security:
  authorized_chat_ids:
    - 937027893
  rate_limit:
    max_requests: 30
    time_window: 60

logging:
  level: "INFO"
  file: "data/logs/telegram_bot.log"
```

### PASO 4: Configuración de usuario
```
notepad config\user_settings.yaml
```
Ejemplo:
```
bot_settings:
  name: "TradingBot_v10_Alex"

active_symbol_groups: ["primary"]
active_timeframes: ["real_time", "analysis"]

capital_management:
  initial_balance: 1000.0
  max_risk_per_trade: 2.0
  max_daily_loss_pct: 5.0
```

### PASO 5: Instalar dependencias
```
pip install python-telegram-bot>=20.7 ccxt>=4.0.0 pandas>=2.0.0 numpy>=1.24.0 pyyaml>=6.0 python-dotenv>=1.0.0
```

### PASO 6: Crear directorios/archivos
```
mkdir data\logs data\historical data\models data\checkpoints 2> NUL
if not exist control\__init__.py echo. > control\__init__.py
if not exist scripts\__init__.py echo. > scripts\__init__.py
if not exist core\__init__.py echo. > core\__init__.py
if not exist config\__init__.py echo. > config\__init__.py
```

## 🧪 Tests de verificación

### Test 1: Imports
```
python - << "PY"
try:
    from control.telegram_bot import TelegramBot
    print('✅ Control OK')
except Exception as e:
    print(f'❌ Control Error: {e}')

try:
    from config.unified_config import UnifiedConfigManager
    print('✅ Config Manager OK')
except Exception as e:
    print(f'❌ Config Manager Error: {e}')
PY
```

### Test 2: Configuración
```
python - << "PY"
import os
from dotenv import load_dotenv
load_dotenv()

ok = True
for var in ['TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID']:
    v = os.getenv(var)
    print(f"{var}: {'OK' if v else 'FALTA'}")
    ok = ok and bool(v)
print('✅ Variables de entorno OK' if ok else '❌ Variables de entorno faltantes')
PY
```

### Test 3: Telegram
```
python - << "PY"
import asyncio
try:
    from control.telegram_bot import TelegramBot
except Exception as e:
    print(f'❌ Import TelegramBot: {e}')
    raise SystemExit(1)

async def test():
    try:
        bot = TelegramBot()
        success = await bot.send_message('🧪 Test de conexión')
        print('✅ Telegram OK' if success else '❌ Telegram Error al enviar')
    except Exception as e:
        print(f'❌ Telegram Error: {e}')

asyncio.run(test())
PY
```

## 🚀 Comandos de inicio
```
python bot.py --mode paper --telegram-enabled --symbols BTCUSDT,ETHUSDT
python bot.py --mode paper --telegram-enabled --verbose --log-level DEBUG
```

Solo Telegram:
```
python control\telegram_bot.py
```

## 📱 Comandos de Telegram
- /start, /help, /status, /health
- /download_history, /inspect_history, /repair_history
- /start_trading, /stop_trading, /emergency_stop
- /train_hist, /train_live, /training_status

## 📄 Script de diagnóstico
Archivo `diagnostico.py` en la raíz del proyecto (ver repo).

## 🆘 Soporte adicional
```
python bot.py --mode paper --telegram-enabled --log-level DEBUG 2>&1 | tee debug.log
```
Permisos (Windows):
```
icacls control\* /grant %USERNAME%:F
```
Reinstalar dependencias puntuales:
```
pip uninstall -y python-telegram-bot && pip install python-telegram-bot>=20.7
```
