# 🛠️ Scripts de Utilidad

Esta carpeta contiene scripts de utilidad para el Trading Bot v10.

## 📁 Scripts Disponibles

### 🌙 `entrenamiento_nocturno.py`
Script principal para entrenamiento nocturno del bot:
- Entrena con datos históricos (5 años → 4 → 3 → 2 → 1 año si falla)
- Continúa aprendiendo en tiempo real
- Maneja errores automáticamente
- Registra todo el proceso

**Uso:**
```bash
python scripts/entrenamiento_nocturno.py
```

### 🔍 `estado_bot_rapido.py`
Script para verificación rápida del estado del bot:
- Muestra modo de trading actual
- Estado del sistema de aprendizaje
- Configuración activa

**Uso:**
```bash
python scripts/estado_bot_rapido.py
```

### 📊 `verificar_estado_bot.py`
Script completo para verificación detallada del estado:
- Análisis completo del sistema
- Verificación de componentes
- Estado de la base de datos
- Métricas de performance

**Uso:**
```bash
python scripts/verificar_estado_bot.py
```

## 🚀 Ejecutar Scripts

Todos los scripts se ejecutan desde la raíz del proyecto:

```bash
# Desde la raíz del proyecto
python scripts/nombre_del_script.py
```
