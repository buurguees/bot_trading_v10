# 🤖 Bot de Telegram - Trading Bot v10 Enterprise

Sistema de notificaciones y control móvil para el Trading Bot v10 Enterprise a través de Telegram.

## 📱 Características

- **Monitoreo en tiempo real** - Métricas del sistema cada 5 minutos
- **Control remoto** - Iniciar/detener trading desde tu móvil
- **Alertas automáticas** - Notificaciones de eventos importantes
- **Seguridad** - Acceso restringido por Chat ID
- **Comandos intuitivos** - Interfaz fácil de usar

## 🚀 Configuración Rápida

### 1. Obtener tu Chat ID

```bash
# Ejecutar script de configuración
python notifications/telegram/get_chat_id.py
```

Sigue las instrucciones para obtener tu Chat ID único.

### 2. Configurar el bot

Edita `notifications/telegram/config.yaml`:

```yaml
telegram:
  bot_token: "8422053215:AAH5hqD8472CCQyDTHfL8Zge9VXZNEJbdd8"  # Ya configurado
  chat_id: "TU_CHAT_ID_AQUI"  # Reemplazar con tu Chat ID
  enabled: true
  metrics_interval: 300  # 5 minutos
```

### 3. Instalar dependencias

```bash
pip install python-telegram-bot>=20.7
```

### 4. Ejecutar el bot

```bash
# Con bot de Telegram habilitado
python bot.py --mode paper --symbols BTCUSDT,ETHUSDT --telegram-enabled

# Solo bot de Telegram (para testing)
python notifications/telegram/telegram_bot.py
```

## 📋 Comandos Disponibles

### 🔍 Monitoreo
- `/start` - Mensaje de bienvenida y comandos
- `/help` - Lista detallada de comandos
- `/status` - Estado general del sistema
- `/metrics` - Métricas actuales
- `/positions` - Posiciones abiertas
- `/balance` - Balance detallado
- `/health` - Salud del sistema

### 🎮 Control
- `/start_trading` - Iniciar motor de trading
- `/stop_trading` - Detener motor de trading
- `/emergency_stop` - Parada de emergencia

### ⚙️ Configuración
- `/settings` - Ver configuración actual

## 📊 Métricas Automáticas

El bot envía métricas automáticamente cada 5 minutos:

```
📊 Métricas del Sistema
⏰ 14:30:15

💰 Balance: $10,500.00
📈 PnL Hoy: $250.00
🎯 Win Rate: 75.0%
📉 Drawdown: 2.5%
⚡ Latencia: 45.0ms
🔄 Trades: 5
📊 Posiciones: 2
🟢 Salud: 95.0%
```

## 🚨 Alertas Automáticas

### Alertas de PnL
- **Ganancia alta**: PnL > $1,000
- **Pérdida significativa**: PnL < -$1,000

### Alertas de Riesgo
- **Drawdown alto**: > 10%
- **Salud crítica**: Health Score < 70%

### Alertas de Rendimiento
- **Latencia alta**: > 100ms

## 🔒 Seguridad

### Restricción de Acceso
- Solo tu Chat ID puede usar los comandos
- Otros usuarios reciben mensaje de "Acceso no autorizado"

### Encriptación (Opcional)
```bash
# Generar clave de encriptación
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Agregar a .env
echo "ENCRYPTION_KEY=tu_clave_aqui" >> .env
```

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/notifications/test_telegram_bot.py -v

# Test específico
pytest tests/notifications/test_telegram_bot.py::TestTelegramBot::test_send_message_success -v
```

## 📁 Estructura de Archivos

```
notifications/telegram/
├── __init__.py              # Inicializador del paquete
├── telegram_bot.py          # Clase principal del bot
├── handlers.py              # Manejo de comandos
├── metrics_sender.py        # Envío de métricas
├── config.yaml              # Configuración
├── get_chat_id.py           # Script para obtener Chat ID
└── README.md                # Esta documentación
```

## 🔧 Configuración Avanzada

### Personalizar Intervalos
```yaml
telegram:
  metrics_interval: 600  # 10 minutos
  alert_thresholds:
    pnl_alert: 2000      # $2,000
    risk_alert: 15       # 15%
    latency_alert: 150   # 150ms
```

### Configurar Alertas
```yaml
security:
  alert_cooldown: 600    # 10 minutos entre alertas
  rate_limit: 30         # 30 mensajes por minuto
```

## 🐛 Solución de Problemas

### Bot no responde
1. Verifica que el bot esté habilitado en `config.yaml`
2. Confirma que tu Chat ID sea correcto
3. Revisa los logs en `logs/telegram_bot.log`

### Error de conexión
1. Verifica tu conexión a internet
2. Confirma que el token del bot sea correcto
3. Ejecuta `python notifications/telegram/get_chat_id.py`

### Comandos no funcionan
1. Asegúrate de haber enviado `/start` al bot primero
2. Verifica que tu Chat ID esté en la configuración
3. Revisa que el sistema de trading esté funcionando

## 📞 Soporte

- **Logs**: Revisa `logs/telegram_bot.log`
- **Configuración**: Verifica `notifications/telegram/config.yaml`
- **Tests**: Ejecuta `pytest tests/notifications/`

## 🔄 Actualizaciones

Para actualizar el bot de Telegram:

1. Actualiza las dependencias:
   ```bash
   pip install --upgrade python-telegram-bot
   ```

2. Reinicia el bot:
   ```bash
   python bot.py --mode paper --symbols BTCUSDT --telegram-enabled
   ```

## 📝 Notas Importantes

- **Chat ID único**: Cada usuario tiene un Chat ID único
- **Rate limits**: Telegram limita a 30 mensajes por minuto
- **Seguridad**: Nunca compartas tu Chat ID o token
- **Backup**: Mantén una copia de tu configuración

---

**¡Disfruta del control móvil de tu Trading Bot v10!** 🚀📱
