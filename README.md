# 🤖 Bot Trading v10 Enterprise

Sistema de trading enterprise con arquitectura modular, escalable y robusta para trading de criptomonedas con machine learning.

## 🚀 **Características Principales**

### **Trading Avanzado**
- **Futures Trading** con leverage dinámico (5x-30x)
- **10 Símbolos** soportados (BTCUSDT, ETHUSDT, ADAUSDT, SOLUSDT, DOGEUSDT, AVAXUSDT, TONUSDT, BNBUSDT, XRPUSDT, LINKUSDT)
- **Estrategias ML** con LSTM + Attention
- **Gestión de Riesgo** avanzada con stop-loss dinámico
- **Ejecución de Órdenes** de alta velocidad (<100ms)

### **Machine Learning**
- **Modelos LSTM + Attention** para predicción de precios
- **Entrenamiento Distribuido** con PyTorch Lightning
- **Optimización de Hiperparámetros** con Optuna
- **Tracking de Experimentos** con MLflow
- **Inferencia Optimizada** con torch.jit

### **Monitoreo y Observabilidad**
- **Métricas en Tiempo Real** con Prometheus
- **Dashboards** interactivos con Grafana
- **Alertas Automáticas** basadas en umbrales
- **Health Checks** del sistema
- **Logging Estructurado** con diferentes niveles

### **Cumplimiento Regulatorio**
- **MiFID II** compliance integrado
- **GDPR** compliance con retención de 7 años
- **Audit Logging** inmutable con checksums
- **Reportes Regulatorios** automáticos
- **Encriptación** de datos sensibles

### **Infraestructura Enterprise**
- **Arquitectura Asíncrona** con asyncio
- **Escalabilidad Horizontal** con Kubernetes
- **Recuperación Automática** desde backups
- **Gestión de Configuración** centralizada
- **Tests Exhaustivos** (unit, integration, e2e, performance)

## 📁 **Estructura del Proyecto**

```
bot_trading_v10/
├── 🤖 bot.py                          # Ejecutor principal
├── 📋 requirements.txt                 # Dependencias
├── 📖 README.md                        # Documentación
├── 🔧 .env.example                     # Variables de entorno
├── 📁 src/                            # Código fuente
│   ├── 📁 core/                       # Módulos principales
│   │   ├── 📁 trading/                # Motor de trading
│   │   ├── 📁 data/                   # Gestión de datos
│   │   ├── 📁 ml/                     # Machine Learning
│   │   ├── 📁 monitoring/             # Monitoreo
│   │   ├── 📁 compliance/             # Cumplimiento
│   │   ├── 📁 config/                 # Configuración
│   │   └── 📁 deployment/             # Despliegues
│   └── 📁 scripts/                    # Scripts de ejecución
│       ├── 📁 trading/                # Scripts de trading
│       ├── 📁 deployment/             # Scripts de despliegue
│       ├── 📁 maintenance/            # Scripts de mantenimiento
│       └── 📁 training/               # Scripts de entrenamiento
├── 📁 infrastructure/                 # Infraestructura
│   ├── 📁 docker/                     # Contenedores Docker
│   ├── 📁 kubernetes/                 # Manifiestos K8s
│   └── 📁 monitoring/                 # Configuración de monitoreo
├── 📁 tests/                          # Tests
│   ├── 📁 unit/                       # Tests unitarios
│   ├── 📁 integration/                # Tests de integración
│   ├── 📁 e2e/                        # Tests end-to-end
│   └── 📁 performance/                # Tests de rendimiento
├── 📁 docs/                           # Documentación
├── 📁 logs/                           # Logs del sistema
├── 📁 data/                           # Datos (TimescaleDB)
├── 📁 models/                         # Modelos ML
├── 📁 checkpoints/                    # Checkpoints de entrenamiento
└── 📁 _old/                          # Archivos obsoletos
```

## 🚀 **Inicio Rápido**

### **1. Instalación**

```bash
# Clonar repositorio
git clone https://github.com/buurguees/bot_trading_v10.git
cd bot_trading_v10

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### **2. Configuración**

```bash
# Configurar credenciales de Bitget
export BITGET_API_KEY="tu_api_key"
export BITGET_SECRET_KEY="tu_secret_key"
export BITGET_PASSPHRASE="tu_passphrase"

# Configurar base de datos
export DATABASE_URL="postgresql://user:password@localhost:5432/trading_bot"
export REDIS_URL="redis://localhost:6379"
```

### **3. Ejecución**

```bash
# Trading en vivo
python bot.py --mode live --symbols BTCUSDT,ETHUSDT --leverage 10

# Trading simulado (paper trading)
python bot.py --mode paper --symbols BTCUSDT,ETHUSDT,ADAUSDT --leverage 5

# Parada de emergencia
python bot.py --mode emergency-stop

# Verificación de salud del sistema
python bot.py --health-check

# Gestión de fases
python bot.py --phases infrastructure,training,trading
```

## ⚙️ **Configuración Avanzada**

### **Archivo de Configuración Principal**
```yaml
# src/core/config/user_settings.yaml
bot_settings:
  main_symbols:
    - BTCUSDT
    - ETHUSDT
    - ADAUSDT
    - SOLUSDT
    - DOGEUSDT
    - AVAXUSDT
    - TONUSDT
    - BNBUSDT
    - XRPUSDT
    - LINKUSDT
  
  enterprise_features:
    real_time_data_collection: true
    futures_trading: true
    compliance_monitoring: true

trading_enterprise:
  futures_trading:
    leverage:
      min_leverage: 5
      max_leverage: 30
      confidence_based: true
    margin_mode: isolated
  
  strategies:
    ml_strategy:
      confidence_threshold: 65.0
      model_type: lstm_attention

monitoring:
  prometheus:
    enabled: true
    port: 8001
  
  grafana:
    enabled: true
    port: 3000

compliance:
  mifid2_enabled: true
  gdpr_enabled: true
  data_retention_years: 7
```

## 🧪 **Testing**

```bash
# Tests unitarios
pytest tests/unit/ -v

# Tests de integración
pytest tests/integration/ -v

# Tests end-to-end
pytest tests/e2e/ -v

# Tests de rendimiento
pytest tests/performance/ -v --benchmark-only

# Cobertura de tests
pytest --cov=src --cov-report=html
```

## 📊 **Monitoreo**

### **Prometheus Metrics**
- `trading_bot_health_score`: Score de salud del sistema (0-100)
- `trading_bot_cpu_percent`: Uso de CPU
- `trading_bot_memory_percent`: Uso de memoria
- `trading_bot_trades_total`: Total de trades ejecutados
- `trading_bot_pnl_total`: PnL total

### **Grafana Dashboards**
- **Trading Dashboard**: Métricas de trading en tiempo real
- **Risk Dashboard**: Monitoreo de riesgo y exposición
- **System Health**: Salud del sistema y recursos
- **Performance**: Métricas de rendimiento

## 🔒 **Seguridad**

- **Encriptación AES-256-GCM** para datos sensibles
- **AWS Secrets Manager** para gestión de secretos
- **Audit Logging** inmutable con checksums SHA-256
- **Cumplimiento MiFID II** y GDPR
- **Validación de configuraciones** con JSON Schema

## 🚀 **Despliegue**

### **Docker**
```bash
# Construir imagen
docker build -t bot-trading-v10 .

# Ejecutar contenedor
docker run -d --name bot-trading \
  -e BITGET_API_KEY=tu_key \
  -e BITGET_SECRET_KEY=tu_secret \
  -e BITGET_PASSPHRASE=tu_passphrase \
  bot-trading-v10
```

### **Kubernetes**
```bash
# Aplicar manifiestos
kubectl apply -f infrastructure/kubernetes/

# Verificar despliegue
kubectl get pods -n trading-bot
```

## 📈 **Rendimiento**

- **Latencia de ejecución**: <100ms
- **Throughput**: 1000+ trades/segundo
- **Disponibilidad**: 99.9%
- **Recuperación**: <30 segundos
- **Escalabilidad**: Horizontal con Kubernetes

## 🤝 **Contribución**

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📄 **Licencia**

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 **Soporte**

- **Documentación**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/buurguees/bot_trading_v10/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/buurguees/bot_trading_v10/discussions)

## 🎯 **Roadmap**

- [ ] **Fase 4**: Dashboards de Grafana avanzados
- [ ] **Fase 5**: Integración con más exchanges
- [ ] **Fase 6**: Estrategias de arbitraje
- [ ] **Fase 7**: Trading de opciones
- [ ] **Fase 8**: IA generativa para estrategias

---

**Bot Trading v10 Enterprise** - *Trading inteligente para el futuro* 🚀