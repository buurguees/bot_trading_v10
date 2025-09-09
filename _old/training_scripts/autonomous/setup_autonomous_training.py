#!/usr/bin/env python3
"""
Setup para Entrenamiento Autónomo
=================================

Script para configurar y verificar el entorno antes del entrenamiento autónomo.
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

def run_command(command, description):
    """Ejecuta comando y maneja errores"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Verifica versión de Python"""
    print("🐍 Verificando versión de Python...")
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    return True

def install_dependencies():
    """Instala dependencias necesarias"""
    print("📦 Instalando dependencias...")
    
    # Dependencias base
    base_deps = [
        "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
        "pytorch-lightning",
        "optuna",
        "dask[complete]",
        "prometheus-client",
        "mlflow",
        "cryptography",
        "pandas",
        "numpy",
        "scikit-learn",
        "plotly",
        "psutil",
        "GPUtil"
    ]
    
    for dep in base_deps:
        if not run_command(f"pip install {dep}", f"Instalando {dep.split()[0]}"):
            return False
    
    return True

def create_directories():
    """Crea directorios necesarios"""
    print("📁 Creando directorios...")
    
    directories = [
        "logs",
        "checkpoints",
        "cache",
        "data",
        "secrets",
        "mlruns",
        "models/enterprise"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directorio creado: {directory}")
    
    return True

def create_sample_data():
    """Crea datos de muestra para entrenamiento"""
    print("📊 Creando datos de muestra...")
    
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Generar datos de trading sintéticos
        n_samples = 10000
        start_date = datetime.now() - timedelta(days=365)
        dates = [start_date + timedelta(hours=i) for i in range(n_samples)]
        
        data = {
            'timestamp': dates,
            'open': np.random.randn(n_samples) * 100 + 50000,
            'high': np.random.randn(n_samples) * 100 + 50000,
            'low': np.random.randn(n_samples) * 100 + 50000,
            'close': np.random.randn(n_samples) * 100 + 50000,
            'volume': np.random.randint(1000, 10000, n_samples)
        }
        
        df = pd.DataFrame(data)
        df.to_csv('data/sample_trading_data.csv', index=False)
        print("✅ Datos de muestra creados: data/sample_trading_data.csv")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando datos de muestra: {e}")
        return False

def test_imports():
    """Prueba imports de módulos enterprise"""
    print("🧪 Probando imports de módulos enterprise...")
    
    try:
        # Test imports básicos
        import torch
        import pandas as pd
        import numpy as np
        print("✅ Imports básicos OK")
        
        # Test imports enterprise (si existen)
        try:
            sys.path.append('.')
            from models.enterprise.training_engine import EnterpriseTrainingEngine
            print("✅ Training Engine OK")
        except ImportError:
            print("⚠️ Training Engine no disponible (se creará durante el entrenamiento)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        return False

def create_config_files():
    """Crea archivos de configuración"""
    print("⚙️ Creando archivos de configuración...")
    
    # Configuración de logging
    log_config = """
[loggers]
keys=root,training,monitoring

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_training]
level=INFO
handlers=fileHandler
qualname=training
propagate=0

[logger_monitoring]
level=INFO
handlers=fileHandler
qualname=monitoring
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=simpleFormatter
args=('logs/autonomous_training.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
"""
    
    with open('logging.conf', 'w') as f:
        f.write(log_config)
    
    print("✅ Archivo de configuración de logging creado")
    
    # Configuración de Prometheus
    prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-bot-training'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5s
    metrics_path: /metrics
"""
    
    with open('prometheus.yml', 'w') as f:
        f.write(prometheus_config)
    
    print("✅ Configuración de Prometheus creada")
    
    return True

def main():
    """Función principal de setup"""
    print("🚀 Configurando entorno para entrenamiento autónomo...")
    print("=" * 60)
    
    steps = [
        ("Verificar Python", check_python_version),
        ("Crear directorios", create_directories),
        ("Instalar dependencias", install_dependencies),
        ("Crear datos de muestra", create_sample_data),
        ("Probar imports", test_imports),
        ("Crear configuraciones", create_config_files)
    ]
    
    success = True
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ Falló: {step_name}")
            success = False
        else:
            print(f"✅ Completado: {step_name}")
    
    print("\n" + "=" * 60)
    
    if success:
        print("🎉 ¡Setup completado exitosamente!")
        print("\n📋 Próximos pasos:")
        print("1. Ejecutar: python run_autonomous_training.py")
        print("2. Monitorear logs: tail -f logs/autonomous_training.log")
        print("3. Ver métricas: http://localhost:8000/metrics")
        print("4. ¡Disfrutar tu cena! 🍽️")
    else:
        print("❌ Setup falló. Revisa los errores arriba.")
        return False
    
    return True

if __name__ == "__main__":
    main()
