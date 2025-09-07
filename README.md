# 🤖 Trading Bot v10

Bot de trading automatizado con IA avanzada, análisis de mercado en tiempo real y dashboard web interactivo.

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python app.py
```

## 📋 Modos de Operación

```bash
# Flujo completo (default)
python app.py --mode full

# Solo verificar datos
python app.py --mode verify

# Descargar datos históricos
python app.py --mode download

# Entrenar modelo
python app.py --mode train

# Modo paper trading
python app.py --mode paper-trading

# Solo dashboard
python app.py --mode dashboard
```

## 🌐 Dashboard

Una vez ejecutado, accede al dashboard en: **http://127.0.0.1:8050**

## 📁 Estructura del Proyecto

- `app.py` - Punto de entrada único
- `core/` - Archivos principales del bot
- `data/` - Gestión de datos y base de datos
- `models/` - Modelos de IA y entrenamiento
- `monitoring/` - Dashboard web y monitoreo
- `trading/` - Motor de trading y ejecución
- `config/` - Configuraciones del sistema

## 🔧 Configuración

Edita `config/user_settings.yaml` para personalizar el bot.

## 📊 Características

- ✅ IA avanzada con LSTM + Attention
- ✅ Dashboard web en tiempo real
- ✅ Paper trading y trading en vivo
- ✅ Análisis de performance avanzado
- ✅ Gestión de riesgo automática
- ✅ Múltiples símbolos de trading

## 🆘 Soporte

Para más información, consulta la documentación en `docs/`.