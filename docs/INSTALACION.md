# 🚀 Guía de Instalación - Bot Trading v10 Enterprise

## 📋 **REQUISITOS PREVIOS**

### **Sistema Operativo**
- **Windows 10/11** (recomendado)
- **Linux Ubuntu 20.04+** (compatible)
- **macOS 10.15+** (compatible)

### **Software Requerido**
- **Python 3.8+** ([Descargar](https://python.org))
- **Git** ([Descargar](https://git-scm.com))
- **8GB RAM mínimo** (16GB recomendado)
- **50GB espacio en disco** libre

---

## 🔧 **INSTALACIÓN AUTOMÁTICA**

### **Windows**
```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd bot_trading_v10

# 2. Ejecutar script de configuración
setup_environment.bat
```

### **Linux/macOS**
```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd bot_trading_v10

# 2. Dar permisos de ejecución
chmod +x setup_environment.sh

# 3. Ejecutar script de configuración
./setup_environment.sh
```

---

## 🔧 **INSTALACIÓN MANUAL**

### **1. Crear Entorno Virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### **2. Instalar Dependencias**
```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

### **3. Configurar Variables de Entorno**
```bash
# Copiar archivo de ejemplo
copy env.example .env  # Windows
cp env.example .env    # Linux/macOS

# Editar .env con tus credenciales
notepad .env           # Windows
nano .env              # Linux/macOS
```

---

## ⚙️ **CONFIGURACIÓN INICIAL**

### **1. Configurar API Keys de Bitget**
1. Ve a [Bitget API](https://www.bitget.com/account/api)
2. Crea una nueva API key
3. Copia los valores a tu archivo `.env`:
```env
BITGET_API_KEY=tu_api_key_aqui
BITGET_SECRET_KEY=tu_secret_key_aqui
BITGET_PASSPHRASE=tu_passphrase_aqui
```

### **2. Configurar Bot de Telegram**
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Crea un nuevo bot con `/newbot`
3. Copia el token a tu archivo `.env`:
```env
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

### **3. Configurar Chat ID**
```bash
# Ejecutar script para obtener tu Chat ID
python control/get_chat_id.py
```

### **4. Configurar Usuario**
Editar `config/user_settings.yaml`:
```yaml
bot_settings:
  name: "TradingBot_v10_TuNombre"
  trading_mode: "aggressive"  # conservative/moderate/aggressive

capital_management:
  initial_balance: 1000.0
  max_risk_per_trade: 2.0
```

---

## 🧪 **VERIFICACIÓN DE INSTALACIÓN**

### **1. Probar Imports**
```bash
# Probar control
python -c "from control.telegram_bot import TelegramBot; print('✅ Control OK')"

# Probar core
python -c "from core.config.enterprise_config import EnterpriseConfigManager; print('✅ Core OK')"

# Probar scripts
python -c "from scripts.training.train_hist_parallel import TrainHistParallel; print('✅ Scripts OK')"
```

### **2. Probar Configuración**
```bash
# Verificar configuración
python -c "from core.config.enterprise_config import EnterpriseConfigManager; c = EnterpriseConfigManager(); print('Config OK:', c.load_config() is not None)"
```

### **3. Probar Bot**
```bash
# Iniciar en modo paper trading
python bot.py --mode paper --telegram-enabled
```

---

## 🎮 **PRIMER USO**

### **1. Iniciar el Bot**
```bash
# Modo Paper Trading (recomendado para empezar)
python bot.py --mode paper --telegram-enabled

# Modo Live Trading (solo cuando estés listo)
python bot.py --mode live --symbols BTCUSDT,ETHUSDT --telegram-enabled
```

### **2. Comandos de Telegram**
- `/start` - Iniciar bot
- `/help` - Lista de comandos
- `/status` - Estado del sistema
- `/download_history` - Descargar datos
- `/train_hist` - Entrenamiento histórico

### **3. Monitoreo**
- **Dashboard Web**: http://localhost:8050
- **Métricas Prometheus**: http://localhost:9090
- **Logs**: `data/logs/bot.log`

---

## 🚨 **SOLUCIÓN DE PROBLEMAS**

### **Error: "ModuleNotFoundError"**
```bash
# Verificar que el entorno virtual está activo
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

### **Error: "No module named 'telegram'"**
```bash
# Instalar dependencias de Telegram
pip install python-telegram-bot==20.7
```

### **Error: "No module named 'ccxt'"**
```bash
# Instalar dependencias de trading
pip install ccxt==4.1.77
```

### **Error de Configuración**
```bash
# Verificar archivos de configuración
python -c "import yaml; yaml.safe_load(open('config/user_settings.yaml'))"
```

### **Error de Base de Datos**
```bash
# El bot creará automáticamente la base de datos
# Si hay problemas, eliminar y recrear:
rm data/trading_bot.db*
python bot.py --mode paper
```

---

## 📚 **CONFIGURACIÓN AVANZADA**

### **1. Configuración de Trading**
Editar `config/user_settings.yaml`:
```yaml
trading_settings:
  symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
  timeframes: ["1h", "4h", "1d"]
  max_positions: 5
  min_confidence: 70.0
```

### **2. Configuración de IA**
```yaml
ai_model_settings:
  confidence:
    min_confidence_to_trade: 70.0
  training:
    auto_retrain: true
    retrain_interval_hours: 12
```

### **3. Configuración de Monitoreo**
```yaml
monitoring:
  prometheus_port: 9090
  dashboard_port: 8050
  metrics_interval: 300
```

---

## 🔄 **ACTUALIZACIONES**

### **Actualizar Código**
```bash
# Hacer backup de configuración
copy config\user_settings.yaml config\user_settings.yaml.backup

# Actualizar código
git pull origin main

# Restaurar configuración
copy config\user_settings.yaml.backup config\user_settings.yaml

# Actualizar dependencias
pip install -r requirements.txt --upgrade
```

### **Actualizar Dependencias**
```bash
# Actualizar todas las dependencias
pip install -r requirements.txt --upgrade

# Actualizar dependencias específicas
pip install python-telegram-bot --upgrade
pip install ccxt --upgrade
```

---

## 📞 **SOPORTE**

### **Problemas Comunes**
1. **Verificar Python 3.8+**
2. **Verificar entorno virtual activo**
3. **Verificar archivos de configuración**
4. **Verificar credenciales API**

### **Logs de Diagnóstico**
```bash
# Ver logs en tiempo real
tail -f data/logs/bot.log

# Ver logs de errores
grep "ERROR" data/logs/*.log
```

### **Comandos de Diagnóstico**
```bash
# Estado del sistema
python -c "from core.monitoring.health_checks import HealthChecker; h = HealthChecker(); print(h.check_all())"

# Verificar configuración
python -c "from core.config.enterprise_config import EnterpriseConfigManager; c = EnterpriseConfigManager(); print('Config OK')"
```

---

## 🎯 **PRÓXIMOS PASOS**

1. **Configurar credenciales** en `.env`
2. **Probar comandos básicos** de Telegram
3. **Descargar datos históricos** con `/download_history`
4. **Entrenar modelo** con `/train_hist` (paralelo)
5. **Iniciar trading** con `/start_trading`

---

**¡El bot está listo para usar!** 🚀

*Para más información, consulta el README.md principal*
