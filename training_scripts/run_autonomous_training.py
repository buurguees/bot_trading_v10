#!/usr/bin/env python3
"""
Entrenamiento Autónomo Enterprise
================================

Script para ejecutar entrenamiento enterprise completo de forma autónoma.
Incluye monitoreo, logging, y notificaciones automáticas.

Uso:
    python run_autonomous_training.py
"""

import asyncio
import logging
import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import signal
import subprocess
import threading

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutonomousTrainingManager:
    """Gestor de entrenamiento autónomo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.start_time = None
        self.training_process = None
        
        # Configurar directorios
        self.setup_directories()
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_directories(self):
        """Configura directorios necesarios"""
        directories = [
            'logs',
            'checkpoints',
            'cache',
            'data',
            'secrets',
            'mlruns'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Directorios configurados correctamente")
    
    def signal_handler(self, signum, frame):
        """Maneja señales para shutdown graceful"""
        self.logger.info(f"Recibida señal {signum}, iniciando shutdown graceful...")
        self.stop_training()
        sys.exit(0)
    
    async def start_training(self):
        """Inicia el entrenamiento autónomo"""
        try:
            self.logger.info("🚀 Iniciando entrenamiento autónomo enterprise...")
            self.is_running = True
            self.start_time = datetime.now()
            
            # Crear configuración de entrenamiento
            training_config = self.create_training_config()
            
            # Crear configuración de datos
            data_config = self.create_data_config()
            
            # Iniciar monitoreo en background
            monitoring_thread = threading.Thread(target=self.start_monitoring)
            monitoring_thread.daemon = True
            monitoring_thread.start()
            
            # Ejecutar entrenamiento
            await self.run_enterprise_training(training_config, data_config)
            
        except Exception as e:
            self.logger.error(f"Error en entrenamiento autónomo: {e}")
            raise
        finally:
            self.is_running = False
            self.logger.info("🏁 Entrenamiento autónomo finalizado")
    
    def create_training_config(self):
        """Crea configuración de entrenamiento optimizada"""
        return {
            "model": {
                "type": "lstm_attention",
                "hidden_size": 128,
                "num_layers": 3,
                "dropout": 0.2,
                "attention_heads": 8
            },
            "training": {
                "max_epochs": 50,
                "batch_size": 64,
                "learning_rate": 0.001,
                "weight_decay": 1e-5,
                "patience": 10,
                "gradient_clip_val": 1.0
            },
            "distributed": {
                "devices": 1,
                "strategy": "auto",
                "precision": "16-mixed"
            },
            "checkpoints": {
                "every_n_epochs": 5,
                "save_top_k": 3,
                "monitor": "val_loss"
            },
            "logging": {
                "log_every_n_steps": 50,
                "val_check_interval": 1.0
            }
        }
    
    def create_data_config(self):
        """Crea configuración de datos"""
        return {
            "n_samples": 10000,
            "n_features": 5,
            "sequence_length": 60,
            "prediction_horizon": 1,
            "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            "timeframe": "1h",
            "years": 2
        }
    
    async def run_enterprise_training(self, training_config, data_config):
        """Ejecuta el entrenamiento enterprise"""
        try:
            # Importar módulos enterprise
            sys.path.append('.')
            from models.enterprise.training_engine import EnterpriseTrainingEngine, TrainingConfig
            from models.enterprise.monitoring_system import EnterpriseMonitoringSystem, MonitoringConfig
            from models.enterprise.data_pipeline import EnterpriseDataPipeline, DataPipelineConfig
            from models.enterprise.hyperparameter_tuning import EnterpriseHyperparameterTuner, TuningConfig
            
            self.logger.info("📊 Iniciando sistema de monitoreo...")
            
            # Configurar monitoreo
            monitoring_config = MonitoringConfig(
                prometheus_port=8000,
                enable_alerts=False,  # Deshabilitado para evitar spam
                log_metrics=True,
                log_file="logs/training_metrics.log"
            )
            
            monitor = EnterpriseMonitoringSystem(monitoring_config)
            await monitor.start_monitoring()
            
            self.logger.info("🔄 Iniciando data pipeline...")
            
            # Configurar data pipeline
            pipeline_config = DataPipelineConfig(
                n_workers=2,
                memory_limit="2GB",
                enable_caching=True,
                cache_dir="cache/training_data"
            )
            
            pipeline = EnterpriseDataPipeline(pipeline_config)
            await pipeline.start()
            
            # Generar datos de entrenamiento
            self.logger.info("📈 Generando datos de entrenamiento...")
            processed_data = await pipeline.process_trading_data(data_config)
            
            self.logger.info("🤖 Iniciando entrenamiento del modelo...")
            
            # Configurar entrenamiento
            config = TrainingConfig(
                model_type=training_config["model"]["type"],
                hidden_size=training_config["model"]["hidden_size"],
                num_layers=training_config["model"]["num_layers"],
                dropout=training_config["model"]["dropout"],
                attention_heads=training_config["model"]["attention_heads"],
                max_epochs=training_config["training"]["max_epochs"],
                batch_size=training_config["training"]["batch_size"],
                learning_rate=training_config["training"]["learning_rate"],
                weight_decay=training_config["training"]["weight_decay"],
                patience=training_config["training"]["patience"],
                gradient_clip_val=training_config["training"]["gradient_clip_val"],
                devices=training_config["distributed"]["devices"],
                strategy=training_config["distributed"]["strategy"],
                precision=training_config["distributed"]["precision"],
                checkpoint_every_n_epochs=training_config["checkpoints"]["every_n_epochs"],
                save_top_k=training_config["checkpoints"]["save_top_k"],
                monitor=training_config["checkpoints"]["monitor"],
                log_every_n_steps=training_config["logging"]["log_every_n_steps"],
                val_check_interval=training_config["logging"]["val_check_interval"]
            )
            
            # Crear engine de entrenamiento
            engine = EnterpriseTrainingEngine(
                experiment_name="autonomous_training",
                run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                checkpoint_dir="checkpoints/autonomous",
                log_dir="logs/training"
            )
            
            # Ejecutar entrenamiento
            self.logger.info("🚀 Iniciando entrenamiento distribuido...")
            results = await engine.train_distributed(data_config, config)
            
            self.logger.info(f"✅ Entrenamiento completado exitosamente!")
            self.logger.info(f"📊 Resultados: {results}")
            
            # Guardar resultados
            self.save_training_results(results)
            
            # Detener servicios
            await monitor.stop_monitoring()
            await pipeline.stop()
            
            self.logger.info("🎉 Entrenamiento autónomo completado exitosamente!")
            
        except Exception as e:
            self.logger.error(f"❌ Error durante el entrenamiento: {e}")
            raise
    
    def start_monitoring(self):
        """Inicia monitoreo en background"""
        while self.is_running:
            try:
                # Verificar estado del sistema
                self.check_system_health()
                
                # Log de progreso
                if self.start_time:
                    elapsed = datetime.now() - self.start_time
                    self.logger.info(f"⏱️ Tiempo transcurrido: {elapsed}")
                
                time.sleep(60)  # Check cada minuto
                
            except Exception as e:
                self.logger.error(f"Error en monitoreo: {e}")
                time.sleep(30)
    
    def check_system_health(self):
        """Verifica salud del sistema"""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 90:
                self.logger.warning(f"⚠️ CPU alto: {cpu_percent}%")
            
            # Memoria
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.logger.warning(f"⚠️ Memoria alta: {memory.percent}%")
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                self.logger.warning(f"⚠️ Disco lleno: {disk_percent}%")
            
        except Exception as e:
            self.logger.error(f"Error verificando salud del sistema: {e}")
    
    def save_training_results(self, results):
        """Guarda resultados del entrenamiento"""
        try:
            results_file = f"logs/training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.logger.info(f"📁 Resultados guardados en: {results_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")
    
    def stop_training(self):
        """Detiene el entrenamiento"""
        self.logger.info("🛑 Deteniendo entrenamiento...")
        self.is_running = False
        
        if self.training_process:
            self.training_process.terminate()
            self.training_process.wait()

def print_banner():
    """Imprime banner de inicio"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                🤖 ENTRENAMIENTO AUTÓNOMO ENTERPRISE 🤖        ║
    ║                                                              ║
    ║  🚀 Sistema de entrenamiento enterprise completamente        ║
    ║     automatizado con monitoreo y logging avanzado           ║
    ║                                                              ║
    ║  📊 Características:                                        ║
    ║     • Distributed Training con PyTorch Lightning            ║
    ║     • Monitoreo en tiempo real con Prometheus               ║
    ║     • Data Pipeline escalable con Dask                      ║
    ║     • Hyperparameter Tuning automatizado                    ║
    ║     • Seguridad y compliance enterprise                     ║
    ║     • Logging completo y notificaciones                     ║
    ║                                                              ║
    ║  ⏰ Tiempo estimado: 2-4 horas                              ║
    ║  📁 Logs: logs/autonomous_training.log                      ║
    ║  📊 Métricas: http://localhost:8000/metrics                 ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main():
    """Función principal"""
    print_banner()
    
    # Crear gestor de entrenamiento
    manager = AutonomousTrainingManager()
    
    try:
        # Iniciar entrenamiento
        await manager.start_training()
        
    except KeyboardInterrupt:
        logger.info("🛑 Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        logger.info("👋 ¡Hasta luego! El entrenamiento ha finalizado.")

if __name__ == "__main__":
    # Verificar Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        sys.exit(1)
    
    # Ejecutar entrenamiento
    asyncio.run(main())
