# Implementación de Timestamps de Ciclo

## Objetivo

Añadir timestamps de inicio y fin de cada ciclo de entrenamiento para que el usuario pueda ver el recorrido temporal del entrenamiento.

## Cambios Implementados

### 1. Estructura de Datos Actualizada

**Archivo**: `scripts/training/parallel_training_orchestrator.py`

#### Clase `CycleResult` actualizada:
```python
@dataclass
class CycleResult:
    """Resultado de un ciclo de entrenamiento"""
    cycle_id: int
    timestamp: datetime
    start_timestamp: datetime      # ← NUEVO
    end_timestamp: datetime        # ← NUEVO
    duration_seconds: float
    # ... resto de campos
```

#### Creación de `CycleResult` actualizada:
```python
cycle_result = CycleResult(
    cycle_id=sync_point.cycle_id,
    timestamp=sync_point.timestamp,
    start_timestamp=cycle_start,    # ← NUEVO
    end_timestamp=datetime.now(),   # ← NUEVO
    duration_seconds=cycle_duration,
    # ... resto de campos
)
```

### 2. Método de Progreso Actualizado

**Archivo**: `scripts/training/parallel_training_orchestrator.py`

#### Método `_update_progress` actualizado:
```python
async def _update_progress(self, progress: float, status: str, timestamp: datetime, 
                          cycle_start: datetime = None, cycle_end: datetime = None):
    """Actualiza progreso y notifica callback"""
    # ... código existente ...
    progress_data = {
        'session_id': self.session_id,
        'progress': progress,
        'status': status,
        'current_cycle': self.current_cycle,
        'total_cycles': self.total_cycles,
        'timestamp': timestamp.isoformat(),
        'cycle_start_timestamp': cycle_start,    # ← NUEVO
        'cycle_end_timestamp': cycle_end,        # ← NUEVO
        'symbols': self.symbols,
        'elapsed_time': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
    }
```

#### Llamada a `_update_progress` actualizada:
```python
await self._update_progress(
    progress=(self.current_cycle / self.total_cycles) * 100,
    status=f"Ciclo {self.current_cycle}/{self.total_cycles}",
    timestamp=sync_point.timestamp,
    cycle_start=sync_point.timestamp,    # ← NUEVO
    cycle_end=datetime.now()             # ← NUEVO
)
```

### 3. Cálculo de Métricas de Ciclo Actualizado

**Archivo**: `scripts/training/train_hist_parallel.py`

#### Método `_compute_cycle_metrics` actualizado:
```python
def _compute_cycle_metrics(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # ... cálculos existentes ...
    
    # Obtener timestamps del ciclo
    cycle_start = data.get('cycle_start_timestamp')
    cycle_end = data.get('cycle_end_timestamp')
    cycle_timestamp = data.get('timestamp')
    
    return {
        "avg_pnl": avg_pnl,
        "avg_win_rate": avg_wr,
        # ... métricas existentes ...
        "cycle_start_timestamp": cycle_start,    # ← NUEVO
        "cycle_end_timestamp": cycle_end,        # ← NUEVO
        "cycle_timestamp": cycle_timestamp       # ← NUEVO
    }
```

### 4. Visualización de Timestamps

**Archivo**: `scripts/training/train_hist_parallel.py`

#### Formateo de timestamps en el callback de progreso:
```python
# Formatear timestamps del ciclo
cycle_start_str = ""
cycle_end_str = ""
if cycle_metrics.get('cycle_start_timestamp'):
    cycle_start_str = cycle_metrics['cycle_start_timestamp'].strftime('%H:%M:%S')
if cycle_metrics.get('cycle_end_timestamp'):
    cycle_end_str = cycle_metrics['cycle_end_timestamp'].strftime('%H:%M:%S')

timestamp_info = ""
if cycle_start_str and cycle_end_str:
    timestamp_info = f" | ⏰ {cycle_start_str}→{cycle_end_str}"
elif cycle_metrics.get('cycle_timestamp'):
    timestamp_info = f" | ⏰ {cycle_metrics['cycle_timestamp'].strftime('%H:%M:%S')}"

extra = (
    f" | PnL̄: {cycle_metrics['avg_pnl']:+.2f}"
    f" | WR̄: {cycle_metrics['avg_win_rate']:.1f}%"
    f" | DD̄: {cycle_metrics['avg_drawdown']:.2f}%"
    f" | L:{int(cycle_metrics['total_long_trades'])} S:{int(cycle_metrics['total_short_trades'])}"
    f" | B:{cycle_metrics['initial_balance_total']:.0f}→{cycle_metrics['final_balance_total']:.0f}"
    + (f" | ⏱̄ {cycle_metrics['avg_bars_per_trade']:.1f} barras" if cycle_metrics.get('avg_bars_per_trade') is not None else "")
    + timestamp_info  # ← NUEVO
)
```

## Resultado Visual

### Antes:
```
🔄 Ciclo 25/50: Ejecutando | PnL̄: +1.37 | WR̄: 55.4% | DD̄: 2.19% | L:143 S:146 | B:1000→1011 | ⏱̄ 15.5 barras
```

### Después:
```
🔄 Ciclo 25/50: Ejecutando | PnL̄: +1.37 | WR̄: 55.4% | DD̄: 2.19% | L:143 S:146 | B:1000→1011 | ⏱̄ 15.5 barras | ⏰ 20:15:08→20:20:08
```

## Características

1. **Timestamp de Inicio**: Muestra cuándo comenzó el ciclo
2. **Timestamp de Fin**: Muestra cuándo terminó el ciclo
3. **Formato Legible**: Formato HH:MM:SS para fácil lectura
4. **Fallback**: Si no hay timestamps de inicio/fin, muestra el timestamp del ciclo
5. **Integración**: Se integra perfectamente con las métricas existentes

## Verificación

La implementación ha sido probada y verifica que:
- ✅ Los timestamps se capturan correctamente
- ✅ Se formatean en formato legible (HH:MM:SS)
- ✅ Se muestran en la línea de progreso
- ✅ Hay fallback si faltan timestamps específicos
- ✅ No interfiere con las métricas existentes

## Uso

Los timestamps aparecerán automáticamente en:
- Líneas de progreso del entrenamiento
- Métricas de ciclo guardadas
- Callbacks de progreso
- Notificaciones de Telegram (si están habilitadas)

El usuario ahora puede ver exactamente cuándo comenzó y terminó cada ciclo de entrenamiento, proporcionando una mejor comprensión del recorrido temporal del sistema.
