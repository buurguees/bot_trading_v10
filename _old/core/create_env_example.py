#!/usr/bin/env python3
"""
Script para crear .env.example con credenciales enmascaradas
"""

env_content = """# .env.example
# Ubicación: C:\\TradingBot_v10\\.env.example
#
# IMPORTANTE: Este archivo es un template. Copia a .env y configura tus credenciales reales.
# NUNCA subas el archivo .env real a GitHub.

# =============================================================================
# CREDENCIALES BITGET API
# =============================================================================
# Obtén tus credenciales desde: https://www.bitget.com/es/user/api
# IMPORTANTE: Rota estas keys regularmente por seguridad
BITGET_API_KEY=bg_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITGET_PASSPHRASE=tu_passphrase_aqui

# Nota: Bitget normalmente no requiere passphrase para futuros,
# pero lo dejamos disponible por si acaso. Si no lo necesitas, déjalo vacío.

# =============================================================================
# CONFIGURACIÓN DE ENTORNO
# =============================================================================
# Valores: development, backtesting, paper_trading, live_trading
ENVIRONMENT=development

# Configuración de logging
LOG_LEVEL=INFO

# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (OPCIONAL)
# =============================================================================
# Por defecto usamos SQLite, pero si quieres PostgreSQL en producción:
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DATABASE=trading_bot
# POSTGRES_USER=trading_bot
# POSTGRES_PASSWORD=tu_password_aqui

# =============================================================================
# CONFIGURACIÓN DE ALERTAS (OPCIONAL - PARA FUTURO)
# =============================================================================
# Email notifications (Gmail example)
# EMAIL_SMTP_SERVER=smtp.gmail.com
# EMAIL_SMTP_PORT=587
# EMAIL_USERNAME=tu_email@gmail.com
# EMAIL_PASSWORD=tu_app_password
# EMAIL_TO=destinatario@gmail.com

# Telegram notifications
# TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
# TELEGRAM_CHAT_ID=tu_chat_id_aqui

# Discord notifications
# DISCORD_WEBHOOK_URL=tu_webhook_url_aqui

# =============================================================================
# CONFIGURACIÓN OPCIONAL DEL DASHBOARD
# =============================================================================
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8050

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =============================================================================
# Clave para encriptar datos sensibles (genera una aleatoria)
SECRET_KEY=genera_una_clave_secreta_super_segura_2025

# Límites de seguridad adicionales
MAX_API_CALLS_PER_MINUTE=50
EMERGENCY_STOP_LOSS_PCT=10.0  # Para automáticamente en 10% de pérdida total

# =============================================================================
# CONFIGURACIÓN DEL AGENTE DE IA
# =============================================================================
# Configuración del agente autónomo
AI_AGENT_ENABLED=true
AI_AGENT_MODE=autonomous
AI_AGENT_LEARNING_ENABLED=true
AI_AGENT_SELF_CORRECTION_ENABLED=true

# =============================================================================
# CONFIGURACIÓN DE TRADING
# =============================================================================
# Símbolo principal de trading
PRIMARY_SYMBOL=BTCUSDT

# Modo de trading
TRADING_MODE=paper_trading

# Configuración de riesgo
MAX_RISK_PER_TRADE=0.02
MAX_DAILY_LOSS_PCT=0.05
MAX_DRAWDOWN_PCT=0.10
MAX_LEVERAGE=3.0
"""

# Escribir el archivo
with open('.env.example', 'w', encoding='utf-8') as f:
    f.write(env_content)

print("✅ .env.example creado exitosamente con credenciales enmascaradas")
