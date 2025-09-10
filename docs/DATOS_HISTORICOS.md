# 📊 Sistema de Datos Históricos - Trading Bot v10

## Descripción General

El sistema de datos históricos del Trading Bot v10 asegura que siempre tengas al menos 1 año de datos históricos para todos los timeframes y símbolos configurados. El sistema verifica automáticamente la cobertura de datos al iniciar el bot y descarga datos faltantes cuando es necesario.

## 🚀 Características Principales

- **Verificación Automática**: Al iniciar el bot, verifica automáticamente la cobertura de datos
- **Descarga Inteligente**: Solo descarga los datos que faltan, no duplica información
- **Múltiples Timeframes**: Soporta descarga simultánea de varios timeframes
- **Configuración Flexible**: Configurable desde `user_settings.yaml`
- **Comandos de Telegram**: Control total desde Telegram
- **Reportes Detallados**: Análisis completo del estado de los datos

## ⚙️ Configuración

### En `user_settings.yaml`

```yaml
data_collection:
  historical:
    enabled: true                    # Habilitar descarga histórica
    years: 1                        # Años de datos históricos (1 o 5)
    timeframes: ["1m", "5m", "15m", "1h", "4h", "1d"]  # Timeframes a descargar
    align_after_download: true      # Alinear datos después de descargar
    auto_verify_coverage: true      # Verificar automáticamente al inicio
    min_coverage_days: 365         # Mínimo de días requeridos
    download_missing: true         # Descargar automáticamente datos faltantes
    verification_interval_hours: 24 # Verificar cada 24 horas
```

### Símbolos Configurados

Los símbolos se obtienen automáticamente de la sección `multi_symbol_settings`:

```yaml
multi_symbol_settings:
  symbols:
    BTCUSDT:
      enabled: true
      allocation_pct: 20.0
    ETHUSDT:
      enabled: true
      allocation_pct: 20.0
    # ... más símbolos
```

## 🎯 Uso del Sistema

### 1. Verificación Automática

El bot verifica automáticamente los datos al iniciar:

```bash
python bot.py
```

### 2. Comandos de Telegram

#### Verificar Cobertura
```
/verify_historical_data
```
Verifica si tienes suficientes datos históricos.

#### Descargar Datos Faltantes
```
/download_historical_data
```
Descarga automáticamente los datos que faltan.

#### Reporte Detallado
```
/historical_data_report
```
Genera un reporte completo del estado de los datos.

### 3. Script Standalone

#### Verificación Rápida
```bash
python scripts/data/ensure_historical_data.py --quick-check
```

#### Verificación Completa
```bash
python scripts/data/ensure_historical_data.py
```

#### Solo Reporte
```bash
python scripts/data/ensure_historical_data.py --report-only
```

#### Forzar Descarga
```bash
python scripts/data/ensure_historical_data.py --force-download
```

### 4. Pruebas

```bash
python test_historical_data.py
```

## 📊 Estados del Sistema

### ✅ `complete`
Todos los datos históricos están disponibles y completos.

### 🔄 `completed`
Se descargaron datos faltantes exitosamente.

### ⚠️ `missing_data_detected`
Se detectaron datos faltantes pero la descarga automática está deshabilitada.

### ❌ `error`
Error durante la verificación o descarga.

## 🔧 Configuración Avanzada

### Cambiar Años de Datos

Para cambiar de 1 año a 5 años de datos:

```yaml
data_collection:
  historical:
    years: 5
    min_coverage_days: 1825  # 5 años en días
```

### Deshabilitar Verificación Automática

```yaml
data_collection:
  historical:
    auto_verify_coverage: false
    download_missing: false
```

### Timeframes Personalizados

```yaml
data_collection:
  historical:
    timeframes: ["5m", "15m", "1h", "4h"]  # Solo estos timeframes
```

## 📈 Monitoreo y Logs

### Logs del Sistema

Los logs se guardan en:
- `logs/bot.log` - Logs generales del bot
- `logs/historical_data_verification.log` - Logs específicos de verificación

### Métricas de Descarga

El sistema reporta:
- Número de registros descargados
- Símbolos actualizados vs nuevos
- Tiempo de procesamiento
- Cobertura por timeframe
- Calidad de los datos

## 🚨 Solución de Problemas

### Error: "No hay datos históricos"

**Causa**: La base de datos está vacía o corrupta.

**Solución**:
1. Verificar conexión a la base de datos
2. Ejecutar `/download_historical_data` en Telegram
3. Revisar logs para errores específicos

### Error: "Cobertura insuficiente"

**Causa**: Los datos existentes no cubren el período mínimo requerido.

**Solución**:
1. Aumentar `min_coverage_days` en la configuración
2. Descargar más datos históricos
3. Verificar la calidad de los datos existentes

### Error: "Rate limit exceeded"

**Causa**: Demasiadas solicitudes a la API de Bitget.

**Solución**:
1. Esperar unos minutos y reintentar
2. Reducir el número de símbolos simultáneos
3. Ajustar los intervalos de descarga

### Error: "Credenciales no configuradas"

**Causa**: Las credenciales de Bitget no están configuradas.

**Solución**:
1. Configurar variables de entorno:
   ```bash
   export BITGET_API_KEY="tu_api_key"
   export BITGET_SECRET_KEY="tu_secret_key"
   export BITGET_PASSPHRASE="tu_passphrase"
   ```
2. O crear archivo `.env` con las credenciales

## 🔒 Seguridad

- Las credenciales se almacenan de forma segura
- Solo datos públicos se descargan sin credenciales
- Todas las operaciones se registran en logs
- Verificación de integridad de datos

## 📚 Archivos del Sistema

```
core/data/
├── historical_data_manager.py    # Gestor principal
├── collector.py                  # Descargador de datos
├── history_analyzer.py          # Analizador de cobertura
├── history_downloader.py        # Descargador especializado
└── database.py                  # Gestor de base de datos

scripts/data/
└── ensure_historical_data.py    # Script standalone

control/
├── handlers.py                  # Comandos de Telegram
└── telegram_bot.py             # Bot de Telegram

config/
└── user_settings.yaml          # Configuración principal
```

## 🎯 Próximas Mejoras

- [ ] Soporte para más exchanges
- [ ] Compresión automática de datos antiguos
- [ ] Análisis de calidad de datos más avanzado
- [ ] Descarga incremental inteligente
- [ ] Dashboard web para monitoreo
- [ ] Alertas automáticas por Telegram

## 📞 Soporte

Para problemas o preguntas:
1. Revisar los logs del sistema
2. Ejecutar `/historical_data_report` en Telegram
3. Verificar la configuración en `user_settings.yaml`
4. Consultar este documento

---

**Versión**: 1.0.0  
**Última actualización**: 2024  
**Autor**: Trading Bot v10 Enterprise
