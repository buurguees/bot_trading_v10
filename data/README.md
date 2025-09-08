# Directorio de Datos - Trading Bot v10

Este directorio contiene los datos del sistema de trading. Los archivos de datos históricos no se incluyen en el repositorio para mantener el tamaño del repo bajo control.

## Estructura de Datos

```
data/
├── README.md                    # Este archivo
├── trading_bot.db              # Base de datos SQLite (NO incluida en git)
├── feature_cache/              # Cache de features procesadas (NO incluido en git)
│   ├── *.pkl                   # Archivos de cache de features
├── cycles_history.json         # Historial de ciclos (NO incluido en git)
├── synchronized_cycles.json    # Ciclos sincronizados (NO incluido en git)
└── backups/                    # Backups de la base de datos
```

## Configuración Inicial

### 1. Descargar Datos Históricos
Ejecuta el bot y selecciona la opción de descarga de datos:

```bash
python app.py
# Selecciona: 1. Descargar datos históricos
```

### 2. Alinear Datos (Recomendado)
Para entrenamiento multi-símbolo:

```bash
python app.py
# Selecciona: 4. Alinear datos históricos (Multi-símbolo)
```

### 3. Verificar Datos
```bash
python app.py
# Selecciona: 2. Verificar datos históricos
```

## Archivos Generados Automáticamente

- **`trading_bot.db`**: Base de datos SQLite con datos de mercado
- **`feature_cache/`**: Cache de features procesadas para entrenamiento
- **`cycles_history.json`**: Historial de ciclos de trading
- **`synchronized_cycles.json`**: Ciclos sincronizados entre símbolos

## Notas Importantes

- Los archivos de datos se generan automáticamente al ejecutar el bot
- Los datos históricos se descargan de Bitget API
- El cache de features acelera el entrenamiento
- Los archivos de datos NO se incluyen en el repositorio Git

## Tamaño Estimado

- **Base de datos**: ~50-100 MB (dependiendo del período)
- **Cache de features**: ~50-100 MB
- **Archivos JSON**: ~1-5 MB

## Backup y Restauración

Para hacer backup de los datos:

```bash
# Backup de la base de datos
cp data/trading_bot.db data/backups/trading_bot_backup_$(date +%Y%m%d_%H%M%S).db

# Backup de archivos de estado
cp data/*.json data/backups/
```

## Limpieza de Datos

Para limpiar datos antiguos:

```bash
# Limpiar cache de features
rm -rf data/feature_cache/*

# Limpiar logs antiguos
find logs/ -name "*.log" -mtime +30 -delete
```