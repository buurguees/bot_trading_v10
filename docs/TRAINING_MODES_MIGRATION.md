# Migración de Configuración de Modos de Entrenamiento

## Objetivo

Migrar la configuración de modos de entrenamiento desde `user_settings.yaml` a `training_objectives.yaml` para centralizar toda la configuración de entrenamiento en un solo archivo.

## Cambios Implementados

### 1. Nueva Configuración en `training_objectives.yaml`

**Sección añadida al inicio del archivo:**

```yaml
# ⚙️ CONFIGURACIÓN DE MODOS DE ENTRENAMIENTO HISTÓRICO
historical_training_modes:
  ultra_fast:
    name: "Ultra Rápido"
    description: "Entrenamiento rápido para pruebas y desarrollo"
    days: 30
    cycles: 50
    chunk_size_days: 7
    chunk_overlap_days: 1
    max_memory_mb: 2048
    progress_report_interval: 10
    use_case: "Desarrollo, pruebas rápidas, validación de estrategias"
    
  fast:
    name: "Rápido"
    description: "Entrenamiento acelerado con datos recientes"
    days: 90
    cycles: 100
    chunk_size_days: 14
    chunk_overlap_days: 2
    max_memory_mb: 4096
    progress_report_interval: 5
    use_case: "Análisis de tendencias recientes, optimización rápida"
    
  normal:
    name: "Normal"
    description: "Entrenamiento estándar con datos históricos completos"
    days: 180
    cycles: 200
    chunk_size_days: 30
    chunk_overlap_days: 3
    max_memory_mb: 8192
    progress_report_interval: 2
    use_case: "Entrenamiento estándar, análisis de mercado completo"
    
  complete:
    name: "Completo"
    description: "Entrenamiento exhaustivo con máximo de datos históricos"
    days: 365
    cycles: 500
    chunk_size_days: 60
    chunk_overlap_days: 5
    max_memory_mb: 16384
    progress_report_interval: 1
    use_case: "Análisis exhaustivo, entrenamiento de producción"

# 🔧 CONFIGURACIÓN POR DEFECTO DE ENTRENAMIENTO
default_training_config:
  mode: "ultra_fast"
  incremental_training: true
  enable_cycle_telegram: true
  enable_cycle_metrics: true
  save_strategies: true
  save_session_data: true
```

### 2. Actualización de `user_settings.yaml`

**Antes:**
```yaml
training_settings:
  mode: "ultra_fast"  # ultra_fast, fast, normal, complete
  ultra_fast_days: 30
  fast_days: 90
  normal_days: 180
  complete_days: 365
  # Configuración de entrenamiento incremental
  incremental_training: true
  chunk_size_days: 7  # Procesar 7 días por chunk
  chunk_overlap_days: 1  # 1 día de solapamiento
  max_memory_mb: 2048  # Límite de memoria en MB
  progress_report_interval: 10  # Reportar cada 10%
```

**Después:**
```yaml
training_settings:
  mode: "ultra_fast"  # ultra_fast, fast, normal, complete (configurado en training_objectives.yaml)
  # Las configuraciones específicas de cada modo se leen desde training_objectives.yaml
  # Solo se mantiene aquí la selección del modo activo
```

### 3. Nuevas Funciones en `train_hist_parallel.py`

#### `_load_training_mode_config(mode: str)`
```python
def _load_training_mode_config(mode: str = "ultra_fast"):
    """Carga configuración específica del modo de entrenamiento desde training_objectives.yaml"""
    try:
        objectives = _load_training_objectives()
        if objectives and 'historical_training_modes' in objectives:
            training_modes = objectives['historical_training_modes']
            if mode in training_modes:
                return training_modes[mode]
            else:
                logger.warning(f"Modo '{mode}' no encontrado, usando 'ultra_fast'")
                return training_modes.get('ultra_fast', {})
        else:
            logger.warning("No se encontraron modos de entrenamiento histórico, usando configuración por defecto")
            return {}
    except Exception as e:
        logger.warning(f"Error cargando configuración del modo de entrenamiento: {e}")
        return {}
```

#### `_get_training_cycles(mode: str)`
```python
def _get_training_cycles(self, mode: str = "ultra_fast") -> int:
    """Obtiene número de ciclos por modo desde training_objectives.yaml"""
    try:
        mode_config = _load_training_mode_config(mode)
        if 'cycles' in mode_config:
            return int(mode_config['cycles'])
    except Exception as e:
        logger.warning(f"Error obteniendo ciclos de entrenamiento para modo '{mode}': {e}")
    
    # Fallback por defecto
    defaults = {
        'ultra_fast': 50,
        'fast': 100,
        'normal': 200,
        'complete': 500,
    }
    return defaults.get(mode, 50)
```

#### `_get_training_chunk_config(mode: str)`
```python
def _get_training_chunk_config(self, mode: str = "ultra_fast") -> Dict[str, int]:
    """Obtiene configuración de chunks por modo desde training_objectives.yaml"""
    try:
        mode_config = _load_training_mode_config(mode)
        return {
            'chunk_size_days': int(mode_config.get('chunk_size_days', 7)),
            'chunk_overlap_days': int(mode_config.get('chunk_overlap_days', 1)),
            'max_memory_mb': int(mode_config.get('max_memory_mb', 2048)),
            'progress_report_interval': int(mode_config.get('progress_report_interval', 10))
        }
    except Exception as e:
        logger.warning(f"Error obteniendo configuración de chunks para modo '{mode}': {e}")
        return {
            'chunk_size_days': 7,
            'chunk_overlap_days': 1,
            'max_memory_mb': 2048,
            'progress_report_interval': 10
        }
```

#### `get_current_training_config()`
```python
def get_current_training_config(self) -> Dict[str, Any]:
    """Obtiene la configuración actual del entrenamiento"""
    try:
        training_mode = getattr(self.config, 'training_settings', {}).get('mode', 'ultra_fast')
        mode_config = _load_training_mode_config(training_mode)
        
        return {
            'mode': training_mode,
            'name': mode_config.get('name', training_mode.title()),
            'description': mode_config.get('description', ''),
            'days': mode_config.get('days', 30),
            'cycles': mode_config.get('cycles', 50),
            'chunk_size_days': mode_config.get('chunk_size_days', 7),
            'chunk_overlap_days': mode_config.get('chunk_overlap_days', 1),
            'max_memory_mb': mode_config.get('max_memory_mb', 2048),
            'progress_report_interval': mode_config.get('progress_report_interval', 10),
            'use_case': mode_config.get('use_case', '')
        }
    except Exception as e:
        logger.warning(f"Error obteniendo configuración actual del entrenamiento: {e}")
        return {
            'mode': 'ultra_fast',
            'name': 'Ultra Rápido',
            'description': 'Configuración por defecto',
            'days': 30,
            'cycles': 50,
            'chunk_size_days': 7,
            'chunk_overlap_days': 1,
            'max_memory_mb': 2048,
            'progress_report_interval': 10,
            'use_case': 'Configuración por defecto'
        }
```

### 4. Actualización del Entrenamiento Dinámico

**En `_real_training_session`:**
```python
# Obtener configuración del modo de entrenamiento
training_mode = getattr(self.config, 'training_settings', {}).get('mode', 'ultra_fast')
max_cycles = self._get_training_cycles(training_mode)

# Limitar ciclos según el modo de entrenamiento configurado
total_cycles = min(max_cycles, len(timestamps))
cycle_step = max(1, len(timestamps) // total_cycles)
cycle_timestamps = timestamps[::cycle_step][:total_cycles]

logger.info(f"🎯 Modo de entrenamiento: {training_mode} - {total_cycles} ciclos de {len(timestamps)} timestamps disponibles")
```

### 5. Resumen Mejorado

**El resumen ahora muestra el modo de entrenamiento:**
```python
# Obtener información del modo de entrenamiento
training_mode = getattr(self.config, 'training_settings', {}).get('mode', 'ultra_fast')
mode_config = _load_training_mode_config(training_mode)
mode_name = mode_config.get('name', training_mode.title())

message = f"""🎯 <b>Entrenamiento Histórico Completado</b>

📊 <b>Resumen Global ({total_cycles} ciclos - Modo: {mode_name}):</b>
```

## Beneficios

1. **Centralización**: Toda la configuración de entrenamiento en un solo archivo
2. **Flexibilidad**: Fácil modificación de parámetros sin tocar código
3. **Escalabilidad**: Fácil añadir nuevos modos de entrenamiento
4. **Mantenibilidad**: Configuración clara y documentada
5. **Consistencia**: Misma fuente de verdad para todos los componentes

## Modos Disponibles

| Modo | Días | Ciclos | Chunk Size | Memoria | Uso |
|------|------|--------|------------|---------|-----|
| **ultra_fast** | 30 | 50 | 7 días | 2GB | Desarrollo, pruebas rápidas |
| **fast** | 90 | 100 | 14 días | 4GB | Análisis de tendencias recientes |
| **normal** | 180 | 200 | 30 días | 8GB | Entrenamiento estándar |
| **complete** | 365 | 500 | 60 días | 16GB | Análisis exhaustivo |

## Verificación

La migración ha sido probada y verifica que:
- ✅ Los modos se cargan correctamente desde `training_objectives.yaml`
- ✅ Los parámetros se aplican dinámicamente al entrenamiento
- ✅ Hay fallbacks seguros si falla la carga
- ✅ El resumen muestra el modo activo
- ✅ No hay conflictos con configuraciones existentes

La configuración de entrenamiento ahora está completamente centralizada y es fácilmente configurable desde `training_objectives.yaml`.
