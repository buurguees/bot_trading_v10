# 📦 Dependencias del Sistema Enterprise

## 📋 Archivos de Dependencias

Este proyecto incluye múltiples archivos de dependencias para diferentes casos de uso:

### 🎯 **requirements.txt** - Dependencias Completas
- **Propósito**: Instalación completa del sistema enterprise
- **Incluye**: ML, trading, monitoreo, dashboards, testing
- **Uso**: `pip install -r requirements.txt`

### 🚀 **requirements-prod.txt** - Dependencias de Producción
- **Propósito**: Versiones optimizadas para producción
- **Incluye**: Solo dependencias necesarias para producción
- **Uso**: `pip install -r requirements-prod.txt`

### 🛠️ **requirements-dev.txt** - Dependencias de Desarrollo
- **Propósito**: Herramientas de desarrollo y testing
- **Incluye**: Linting, testing, debugging, documentación
- **Uso**: `pip install -r requirements-dev.txt`

### ⚡ **requirements-minimal.txt** - Dependencias Mínimas
- **Propósito**: Solo dependencias esenciales
- **Incluye**: Core, trading básico, configuración
- **Uso**: `pip install -r requirements-minimal.txt`

### 🔒 **constraints.txt** - Constraints de Versiones
- **Propósito**: Versiones específicas para compatibilidad
- **Uso**: `pip install -r requirements.txt -c constraints.txt`

## 🚀 Instalación Rápida

### **Desarrollo Completo**
```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# O con constraints de seguridad
pip install -r requirements.txt -c constraints.txt
```

### **Producción**
```bash
# Instalar solo dependencias de producción
pip install -r requirements-prod.txt -c constraints.txt
```

### **Desarrollo**
```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

### **Mínimo**
```bash
# Instalar solo dependencias esenciales
pip install -r requirements-minimal.txt
```

## 📊 Categorías de Dependencias

### 🤖 **Machine Learning**
- `torch` - PyTorch para deep learning
- `pytorch-lightning` - Framework de entrenamiento
- `mlflow` - Experiment tracking
- `optuna` - Hyperparameter optimization
- `scikit-learn` - Machine learning clásico

### 💹 **Trading & Exchange**
- `ccxt` - APIs de exchanges
- `websockets` - Conexiones en tiempo real
- `aiohttp` - HTTP asíncrono
- `TA-Lib` - Indicadores técnicos

### 🗄️ **Database & Storage**
- `psycopg2-binary` - PostgreSQL
- `asyncpg` - PostgreSQL asíncrono
- `redis` - Caching
- `pyarrow` - Parquet files

### 📊 **Monitoring & Metrics**
- `prometheus-client` - Métricas
- `structlog` - Logging estructurado
- `sentry-sdk` - Error tracking

### 🌐 **Web & Dashboards**
- `fastapi` - API REST
- `dash` - Dashboards web
- `plotly` - Visualizaciones

### 🔧 **Development Tools**
- `pytest` - Testing
- `black` - Code formatting
- `mypy` - Type checking
- `jupyter` - Notebooks

## ⚠️ Consideraciones Importantes

### **Versiones de Python**
- **Mínimo**: Python 3.9
- **Recomendado**: Python 3.10 o 3.11
- **Máximo**: Python 3.11 (3.12 no soportado aún)

### **Dependencias Opcionales**
Algunas dependencias son opcionales y se pueden instalar según necesidad:

```bash
# Para AWS
pip install boto3 botocore

# Para Azure
pip install azure-cli

# Para Kubernetes
pip install kubernetes

# Para Elasticsearch
pip install elasticsearch

# Para InfluxDB
pip install influxdb-client
```

### **Dependencias de Sistema**
Algunas dependencias requieren librerías del sistema:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential libssl-dev libffi-dev

# CentOS/RHEL
sudo yum install gcc openssl-devel libffi-devel

# macOS
brew install openssl libffi
```

## 🔍 Troubleshooting

### **Error de Compilación**
Si hay errores de compilación, instalar dependencias del sistema:

```bash
# Instalar dependencias de compilación
sudo apt-get install build-essential python3-dev

# Reinstalar con cache limpio
pip install --no-cache-dir -r requirements.txt
```

### **Conflictos de Versiones**
Si hay conflictos de versiones:

```bash
# Usar constraints
pip install -r requirements.txt -c constraints.txt

# O crear entorno virtual limpio
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### **Dependencias Opcionales**
Si alguna dependencia opcional falla:

```bash
# Instalar sin dependencias opcionales
pip install -r requirements.txt --no-deps
pip install numpy pandas scikit-learn torch ccxt websockets
```

## 📈 Optimización de Instalación

### **Instalación Paralela**
```bash
# Instalar en paralelo (más rápido)
pip install -r requirements.txt --parallel
```

### **Cache de Pip**
```bash
# Usar cache local
pip install -r requirements.txt --cache-dir ~/.pip/cache
```

### **Instalación Offline**
```bash
# Descargar paquetes
pip download -r requirements.txt -d packages/

# Instalar desde archivos locales
pip install --no-index --find-links packages/ -r requirements.txt
```

## 🎯 Recomendaciones por Entorno

### **Desarrollo Local**
```bash
pip install -r requirements-dev.txt
```

### **Testing CI/CD**
```bash
pip install -r requirements.txt
pip install pytest-cov pytest-html
```

### **Producción Docker**
```bash
pip install -r requirements-prod.txt -c constraints.txt
```

### **Desarrollo Mínimo**
```bash
pip install -r requirements-minimal.txt
```

---

**Nota**: Siempre usar entornos virtuales para evitar conflictos de dependencias.
