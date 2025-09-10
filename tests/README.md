# Tests - Bot Trading v10 Enterprise

## 📁 Estructura de Pruebas

```
tests/
├── __init__.py              # Configuración principal de tests
├── conftest.py              # Fixtures y configuración de pytest
├── README.md                # Este archivo
├── unit/                    # Pruebas unitarias
│   └── __init__.py
├── integration/             # Pruebas de integración
│   └── __init__.py
├── e2e/                     # Pruebas end-to-end
│   └── __init__.py
├── data/                    # Pruebas de datos
│   ├── __init__.py
│   ├── test_historical_data.py
│   └── test_symbol_database.py
├── ml/                      # Pruebas de ML
│   └── __init__.py
└── test_training.log        # Logs de pruebas
```

## 🧪 Tipos de Pruebas

### **Pruebas Unitarias (`unit/`)**
- Pruebas de funciones individuales
- Pruebas de clases aisladas
- Pruebas de métodos específicos
- **Ejemplo**: `test_calculator.py`, `test_data_validator.py`

### **Pruebas de Integración (`integration/`)**
- Pruebas de interacción entre módulos
- Pruebas de APIs y servicios
- Pruebas de flujos de datos
- **Ejemplo**: `test_database_integration.py`, `test_telegram_integration.py`

### **Pruebas End-to-End (`e2e/`)**
- Pruebas completas del flujo de la aplicación
- Pruebas de escenarios de usuario
- Pruebas de casos de uso completos
- **Ejemplo**: `test_trading_flow.py`, `test_bot_startup.py`

### **Pruebas de Datos (`data/`)**
- Pruebas de gestión de datos históricos
- Pruebas de bases de datos
- Pruebas de migración de datos
- **Ejemplo**: `test_historical_data.py`, `test_symbol_database.py`

### **Pruebas de ML (`ml/`)**
- Pruebas de modelos de machine learning
- Pruebas de entrenamiento
- Pruebas de predicciones
- **Ejemplo**: `test_model_training.py`, `test_predictions.py`

## 🚀 Ejecutar Pruebas

### **Todas las pruebas**
```bash
pytest
```

### **Por categoría**
```bash
# Pruebas unitarias
pytest tests/unit/

# Pruebas de integración
pytest tests/integration/

# Pruebas end-to-end
pytest tests/e2e/

# Pruebas de datos
pytest tests/data/

# Pruebas de ML
pytest tests/ml/
```

### **Por marcadores**
```bash
# Pruebas rápidas
pytest -m fast

# Pruebas lentas
pytest -m slow

# Pruebas de base de datos
pytest -m database

# Pruebas de API
pytest -m api
```

### **Con cobertura**
```bash
pytest --cov=core --cov=control --cov=scripts --cov-report=html
```

## 📝 Escribir Pruebas

### **Estructura básica**
```python
import pytest
from unittest.mock import Mock, patch

def test_function_name():
    """Descripción de la prueba"""
    # Arrange
    input_data = "test_data"
    expected_result = "expected_output"
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_result

@pytest.mark.unit
def test_with_marker():
    """Prueba con marcador"""
    assert True

@pytest.fixture
def sample_data():
    """Fixture de datos de prueba"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """Prueba que usa fixture"""
    assert sample_data["key"] == "value"
```

### **Marcadores disponibles**
- `@pytest.mark.unit` - Pruebas unitarias
- `@pytest.mark.integration` - Pruebas de integración
- `@pytest.mark.e2e` - Pruebas end-to-end
- `@pytest.mark.data` - Pruebas de datos
- `@pytest.mark.ml` - Pruebas de ML
- `@pytest.mark.slow` - Pruebas lentas
- `@pytest.mark.fast` - Pruebas rápidas
- `@pytest.mark.database` - Pruebas que requieren BD
- `@pytest.mark.api` - Pruebas que requieren API
- `@pytest.mark.telegram` - Pruebas de Telegram

## 🔧 Configuración

### **Variables de entorno**
- `TESTING=true` - Modo de prueba activado
- `LOG_LEVEL=WARNING` - Nivel de logging en pruebas

### **Fixtures disponibles**
- `project_root_path` - Ruta del directorio raíz
- `test_data_dir` - Directorio temporal para datos
- `mock_config` - Configuración mock
- `mock_database` - Base de datos mock
- `mock_telegram_bot` - Bot de Telegram mock
- `mock_ml_model` - Modelo de ML mock
- `sample_market_data` - Datos de mercado de muestra
- `sample_trading_signal` - Señal de trading de muestra

## 📊 Cobertura de Código

Para generar reportes de cobertura:

```bash
# Instalar pytest-cov
pip install pytest-cov

# Ejecutar con cobertura
pytest --cov=core --cov=control --cov=scripts --cov-report=html

# Ver reporte en HTML
open htmlcov/index.html
```

## 🐛 Debugging

### **Ejecutar con verbose**
```bash
pytest -v -s
```

### **Ejecutar una prueba específica**
```bash
pytest tests/data/test_historical_data.py::test_function_name
```

### **Ejecutar con pdb**
```bash
pytest --pdb
```

## 📋 Mejores Prácticas

1. **Nombres descriptivos**: `test_should_return_error_when_invalid_input()`
2. **Una aserción por prueba**: Cada prueba debe verificar una cosa
3. **Usar fixtures**: Para datos de prueba reutilizables
4. **Mockear dependencias**: Para pruebas unitarias aisladas
5. **Marcar pruebas**: Usar marcadores apropiados
6. **Documentar**: Incluir docstrings descriptivos
7. **Limpiar**: Limpiar recursos después de las pruebas

## 🔍 Ejemplos de Pruebas

Ver los archivos existentes en cada directorio para ejemplos de implementación:

- `tests/data/test_historical_data.py` - Pruebas de datos históricos
- `tests/data/test_symbol_database.py` - Pruebas de base de datos por símbolo
