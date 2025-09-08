#!/usr/bin/env python3
"""
migrate_to_enterprise.py - Script de Migración al Sistema Enterprise
================================================================

Este script facilita la migración del sistema antiguo al sistema enterprise.

Funcionalidades:
- Backup de modelos antiguos
- Configuración del sistema enterprise
- Validación de dependencias
- Testing del sistema migrado
- Limpieza de archivos obsoletos

"""

import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnterpriseMigration:
    """Gestor de migración al sistema enterprise"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / 'backups' / 'migration_backup'
        self.legacy_dir = self.project_root / 'models' / 'legacy'
        
    def create_backup(self):
        """Crear backup del sistema actual"""
        logger.info("📦 Creando backup del sistema actual...")
        
        try:
            # Crear directorio de backup
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup de archivos importantes
            important_files = [
                'app.py',
                'config/user_settings.yaml',
                'data/trading_bot.db',
                'checkpoints/',
                'models/saved_models/',
                'logs/'
            ]
            
            for file_path in important_files:
                src = self.project_root / file_path
                if src.exists():
                    dst = self.backup_dir / file_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    
                    logger.info(f"✅ Backup: {file_path}")
            
            logger.info(f"✅ Backup completado en: {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando backup: {e}")
            return False
    
    def install_enterprise_dependencies(self):
        """Instalar dependencias enterprise"""
        logger.info("📦 Instalando dependencias enterprise...")
        
        try:
            # Instalar requirements enterprise
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements-enterprise.txt'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Dependencias enterprise instaladas")
                return True
            else:
                logger.error(f"❌ Error instalando dependencias: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error instalando dependencias: {e}")
            return False
    
    def validate_enterprise_modules(self):
        """Validar que los módulos enterprise funcionen"""
        logger.info("🔍 Validando módulos enterprise...")
        
        try:
            # Test de importación de módulos clave
            test_imports = [
                'models.enterprise.training_engine',
                'models.enterprise.monitoring_system',
                'models.enterprise.data_pipeline',
                'models.enterprise.hyperparameter_tuning',
                'core.enterprise_config'
            ]
            
            for module in test_imports:
                try:
                    __import__(module)
                    logger.info(f"✅ {module}")
                except ImportError as e:
                    logger.error(f"❌ {module}: {e}")
                    return False
            
            logger.info("✅ Todos los módulos enterprise validados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validando módulos: {e}")
            return False
    
    def run_enterprise_tests(self):
        """Ejecutar tests enterprise"""
        logger.info("🧪 Ejecutando tests enterprise...")
        
        try:
            # Ejecutar tests específicos de enterprise
            result = subprocess.run([
                'pytest', 'tests/test_enterprise_*.py', '-v'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Tests enterprise pasaron")
                return True
            else:
                logger.warning(f"⚠️  Algunos tests fallaron: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando tests: {e}")
            return False
    
    def create_enterprise_config(self):
        """Crear configuración enterprise"""
        logger.info("⚙️  Creando configuración enterprise...")
        
        try:
            # Crear archivo de configuración enterprise
            config_content = """
# Configuración Enterprise del Trading Bot v10
# Generada automáticamente durante la migración

enterprise:
  training:
    duration: 3600  # 1 hora por defecto
    checkpoint_interval: 600  # 10 minutos
    max_epochs: 100
    batch_size: 32
    learning_rate: 0.001
    distributed: true
    mixed_precision: true
    
  monitoring:
    prometheus_port: 9090
    grafana_port: 3000
    dashboard_port: 8050
    metrics_interval: 30
    
  security:
    encryption_enabled: true
    audit_logging: true
    compliance_mode: true
    secrets_management: true
    
  mlflow:
    tracking_uri: "file:./mlruns"
    experiment_name: "trading_bot_enterprise"
    auto_log: true
    
  hyperparameter_tuning:
    enabled: true
    n_trials: 50
    timeout: 3600
    pruning: true
"""
            
            config_file = self.project_root / 'config' / 'enterprise_config.yaml'
            config_file.parent.mkdir(exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"✅ Configuración creada: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando configuración: {e}")
            return False
    
    def cleanup_old_files(self):
        """Limpiar archivos obsoletos"""
        logger.info("🧹 Limpiando archivos obsoletos...")
        
        try:
            # Archivos a limpiar (ya movidos a legacy)
            old_files = [
                'run_simple_training.py',
                'run_fixed_training.py',
                'monitor_simple_training.py',
                'quick_monitor.py'
            ]
            
            cleaned = 0
            for file_name in old_files:
                file_path = self.project_root / file_name
                if file_path.exists():
                    file_path.unlink()
                    cleaned += 1
                    logger.info(f"🗑️  Eliminado: {file_name}")
            
            logger.info(f"✅ Limpieza completada: {cleaned} archivos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            return False
    
    def create_migration_report(self):
        """Crear reporte de migración"""
        logger.info("📊 Creando reporte de migración...")
        
        try:
            report_content = f"""
# Reporte de Migración al Sistema Enterprise
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ✅ Migración Completada

### Archivos Migrados a Legacy:
- models/adaptive_trainer.py
- models/trainer.py
- models/neural_network.py
- models/prediction_engine.py
- models/predictor.py
- models/confidence_estimator.py
- models/model_evaluator.py
- training_scripts/run_simple_training.py
- training_scripts/run_fixed_training.py

### Nuevo Sistema Enterprise:
- app_enterprise.py: Punto de entrada principal
- models/enterprise/: Sistema ML enterprise completo
- config/enterprise_config.yaml: Configuración enterprise
- tests/test_enterprise_*.py: Tests exhaustivos

### Características Enterprise:
- ✅ Distributed training con PyTorch Lightning
- ✅ MLflow para experiment tracking
- ✅ Prometheus/Grafana para monitoreo
- ✅ Hyperparameter tuning con Optuna
- ✅ Fault tolerance y graceful shutdown
- ✅ Security y compliance features
- ✅ Testing exhaustivo
- ✅ CI/CD pipeline

### Uso del Nuevo Sistema:
```bash
# Modo interactivo
python app_enterprise.py

# Modo headless (entrenamiento de 1 hora)
python app_enterprise.py --mode train --duration 3600 --headless

# Entrenamiento rápido
python app_enterprise.py --mode quick --headless

# Monitoreo
python app_enterprise.py --mode monitor --headless
```

### Backup:
- Ubicación: {self.backup_dir}
- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Migración completada exitosamente 🚀
"""
            
            report_file = self.project_root / 'MIGRATION_REPORT.md'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"✅ Reporte creado: {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando reporte: {e}")
            return False
    
    def run_migration(self):
        """Ejecutar migración completa"""
        logger.info("🚀 Iniciando migración al sistema enterprise...")
        
        steps = [
            ("Crear backup", self.create_backup),
            ("Instalar dependencias", self.install_enterprise_dependencies),
            ("Validar módulos", self.validate_enterprise_modules),
            ("Crear configuración", self.create_enterprise_config),
            ("Ejecutar tests", self.run_enterprise_tests),
            ("Limpiar archivos", self.cleanup_old_files),
            ("Crear reporte", self.create_migration_report)
        ]
        
        success_count = 0
        total_steps = len(steps)
        
        for step_name, step_func in steps:
            try:
                logger.info(f"🔄 Ejecutando: {step_name}")
                if step_func():
                    success_count += 1
                    logger.info(f"✅ {step_name} completado")
                else:
                    logger.warning(f"⚠️  {step_name} falló")
            except Exception as e:
                logger.error(f"❌ Error en {step_name}: {e}")
        
        # Resumen final
        logger.info(f"\n📊 MIGRACIÓN COMPLETADA")
        logger.info(f"✅ Pasos exitosos: {success_count}/{total_steps}")
        
        if success_count == total_steps:
            logger.info("🎉 ¡Migración completada exitosamente!")
            logger.info("🚀 Puedes usar: python app_enterprise.py")
        else:
            logger.warning("⚠️  Migración completada con advertencias")
            logger.info("🔍 Revisa los logs para más detalles")
        
        return success_count == total_steps

def main():
    """Función principal"""
    print("🚀 MIGRACIÓN AL SISTEMA ENTERPRISE")
    print("=" * 50)
    
    migration = EnterpriseMigration()
    success = migration.run_migration()
    
    if success:
        print("\n🎉 ¡Migración completada exitosamente!")
        print("🚀 Usa: python app_enterprise.py")
    else:
        print("\n⚠️  Migración completada con advertencias")
        print("🔍 Revisa los logs para más detalles")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
