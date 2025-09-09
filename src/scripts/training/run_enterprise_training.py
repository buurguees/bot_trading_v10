# run_enterprise_training.py - Launcher principal de entrenamiento enterprise
# Ubicación: C:\TradingBot_v10\training_scripts\run_enterprise_training.py

"""
Launcher principal para ejecutar entrenamiento enterprise.

Características:
- Interfaz unificada para todos los tipos de entrenamiento
- Configuración automática del entorno
- Validación de prerrequisitos
- Monitoreo en tiempo real
- Recovery automático
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
import subprocess
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from training_scripts.enterprise.start_8h_training import EightHourTrainingManager
from training_scripts.enterprise.start_distributed_training import DistributedTrainingManager
from training_scripts.enterprise.hyperparameter_optimization import HyperparameterOptimizationManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/training/main_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseTrainingLauncher:
    """Launcher principal de entrenamiento enterprise"""
    
    def __init__(self):
        """Inicializa el launcher"""
        self.setup_directories()
        self.check_prerequisites()
        
    def setup_directories(self):
        """Crea directorios necesarios"""
        directories = [
            "logs/enterprise/training",
            "reports/training",
            "reports/hyperparameter_optimization",
            "checkpoints/hyperparameter_optimization",
            "models/trained_models/experiments",
            "data/processed"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        logger.info("Directorios de entrenamiento configurados")
    
    def check_prerequisites(self):
        """Verifica prerrequisitos del sistema"""
        logger.info("🔍 Verificando prerrequisitos...")
        
        # Verificar Python
        python_version = sys.version_info
        if python_version < (3, 8):
            raise RuntimeError(f"Python 3.8+ requerido, encontrado {python_version}")
        logger.info(f"✅ Python {python_version.major}.{python_version.minor}")
        
        # Verificar PyTorch
        try:
            import torch
            logger.info(f"✅ PyTorch {torch.__version__}")
            if torch.cuda.is_available():
                logger.info(f"✅ CUDA {torch.version.cuda} disponible")
                logger.info(f"✅ GPUs: {torch.cuda.device_count()}")
            else:
                logger.warning("⚠️ CUDA no disponible, usando CPU")
        except ImportError:
            raise RuntimeError("PyTorch no instalado")
        
        # Verificar PyTorch Lightning
        try:
            import pytorch_lightning
            logger.info(f"✅ PyTorch Lightning {pytorch_lightning.__version__}")
        except ImportError:
            raise RuntimeError("PyTorch Lightning no instalado")
        
        # Verificar MLflow
        try:
            import mlflow
            logger.info(f"✅ MLflow {mlflow.__version__}")
        except ImportError:
            logger.warning("⚠️ MLflow no instalado, experiment tracking deshabilitado")
        
        # Verificar Optuna
        try:
            import optuna
            logger.info(f"✅ Optuna {optuna.__version__}")
        except ImportError:
            logger.warning("⚠️ Optuna no instalado, hyperparameter tuning deshabilitado")
        
        # Verificar Docker (opcional)
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ Docker disponible")
            else:
                logger.warning("⚠️ Docker no disponible, servicios enterprise limitados")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("⚠️ Docker no disponible, servicios enterprise limitados")
        
        logger.info("✅ Prerrequisitos verificados")
    
    async def run_8h_training(
        self,
        symbols: Optional[List[str]] = None,
        model_architecture: str = "lstm_attention",
        enable_hyperparameter_tuning: bool = False,
        enable_data_collection: bool = True,
        duration_hours: int = 8,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ejecuta entrenamiento de 8 horas"""
        logger.info("🚀 Iniciando entrenamiento de 8 horas")
        
        manager = EightHourTrainingManager(config_path)
        
        try:
            results = await manager.start_training(
                symbols=symbols,
                model_architecture=model_architecture,
                enable_hyperparameter_tuning=enable_hyperparameter_tuning,
                enable_data_collection=enable_data_collection,
                duration_hours=duration_hours
            )
            
            logger.info("✅ Entrenamiento de 8 horas completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento de 8 horas: {e}")
            raise
    
    async def run_distributed_training(
        self,
        symbols: List[str],
        model_architecture: str = "lstm_attention",
        trainer_type: str = "ddp",
        max_epochs: int = 1000,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ejecuta entrenamiento distribuido"""
        logger.info("🚀 Iniciando entrenamiento distribuido")
        
        manager = DistributedTrainingManager(config_path)
        
        try:
            results = await manager.start_distributed_training(
                symbols=symbols,
                model_architecture=model_architecture,
                trainer_type=trainer_type,
                max_epochs=max_epochs,
                enable_data_collection=True
            )
            
            logger.info("✅ Entrenamiento distribuido completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento distribuido: {e}")
            raise
    
    async def run_hyperparameter_optimization(
        self,
        symbols: List[str],
        model_architecture: str = "lstm_attention",
        n_trials: int = 100,
        timeout: Optional[int] = None,
        n_jobs: int = 1,
        max_epochs: int = 50,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ejecuta optimización de hiperparámetros"""
        logger.info("🚀 Iniciando optimización de hiperparámetros")
        
        manager = HyperparameterOptimizationManager(config_path)
        
        try:
            results = await manager.start_optimization(
                symbols=symbols,
                model_architecture=model_architecture,
                n_trials=n_trials,
                timeout=timeout,
                n_jobs=n_jobs,
                max_epochs=max_epochs
            )
            
            logger.info("✅ Optimización de hiperparámetros completada")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en optimización de hiperparámetros: {e}")
            raise
    
    def print_usage(self):
        """Imprime información de uso"""
        print("\n" + "="*60)
        print("        TRADING BOT ENTERPRISE - ENTRENAMIENTO")
        print("="*60)
        print()
        print("📋 TIPOS DE ENTRENAMIENTO DISPONIBLES:")
        print()
        print("1. 🕐 ENTRENAMIENTO DE 8 HORAS")
        print("   python run_enterprise_training.py --mode 8h --symbols BTCUSDT ETHUSDT")
        print("   --architecture lstm_attention --hyperparameter-tuning")
        print()
        print("2. 🔄 ENTRENAMIENTO DISTRIBUIDO")
        print("   python run_enterprise_training.py --mode distributed --symbols BTCUSDT ETHUSDT")
        print("   --architecture transformer --trainer-type ddp")
        print()
        print("3. 🔧 OPTIMIZACIÓN DE HIPERPARÁMETROS")
        print("   python run_enterprise_training.py --mode hyperparameter --symbols BTCUSDT")
        print("   --architecture lstm_attention --n-trials 50")
        print()
        print("📊 ARQUITECTURAS DISPONIBLES:")
        print("   - lstm_attention (LSTM con atención)")
        print("   - transformer (Transformer puro)")
        print("   - cnn_lstm (CNN-LSTM híbrido)")
        print("   - gru_simple (GRU simple)")
        print()
        print("🔧 TIPOS DE TRAINER DISTRIBUIDO:")
        print("   - ddp (Distributed Data Parallel)")
        print("   - deepspeed (DeepSpeed)")
        print("   - multi_node (Multi-nodo)")
        print()
        print("⚙️ OPCIONES ADICIONALES:")
        print("   --config: Ruta al archivo de configuración")
        print("   --duration: Duración en horas (solo para 8h)")
        print("   --max-epochs: Número máximo de epochs")
        print("   --n-trials: Número de trials (solo para hyperparameter)")
        print("   --timeout: Tiempo límite en segundos")
        print("   --n-jobs: Número de jobs paralelos")
        print()
        print("="*60)

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Launcher principal de entrenamiento enterprise",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--mode", required=True,
                       choices=["8h", "distributed", "hyperparameter"],
                       help="Modo de entrenamiento")
    parser.add_argument("--symbols", nargs="+", required=True,
                       help="Símbolos para entrenar")
    parser.add_argument("--architecture", default="lstm_attention",
                       choices=["lstm_attention", "transformer", "cnn_lstm", "gru_simple"],
                       help="Arquitectura del modelo")
    parser.add_argument("--config", help="Ruta al archivo de configuración")
    
    # Opciones específicas para 8h training
    parser.add_argument("--duration", type=int, default=8,
                       help="Duración en horas (solo para 8h)")
    parser.add_argument("--hyperparameter-tuning", action="store_true",
                       help="Habilitar tuning de hiperparámetros (solo para 8h)")
    parser.add_argument("--no-data-collection", action="store_true",
                       help="Deshabilitar recolección de datos (solo para 8h)")
    
    # Opciones específicas para distributed training
    parser.add_argument("--trainer-type", default="ddp",
                       choices=["ddp", "deepspeed", "multi_node"],
                       help="Tipo de trainer distribuido")
    parser.add_argument("--max-epochs", type=int, default=1000,
                       help="Número máximo de epochs")
    
    # Opciones específicas para hyperparameter optimization
    parser.add_argument("--n-trials", type=int, default=100,
                       help="Número de trials (solo para hyperparameter)")
    parser.add_argument("--timeout", type=int,
                       help="Tiempo límite en segundos (solo para hyperparameter)")
    parser.add_argument("--n-jobs", type=int, default=1,
                       help="Número de jobs paralelos (solo para hyperparameter)")
    
    # Opciones de ayuda
    parser.add_argument("--help-usage", action="store_true",
                       help="Mostrar información de uso detallada")
    
    args = parser.parse_args()
    
    # Mostrar ayuda de uso si se solicita
    if args.help_usage:
        launcher = EnterpriseTrainingLauncher()
        launcher.print_usage()
        return
    
    # Crear launcher
    launcher = EnterpriseTrainingLauncher()
    
    try:
        # Ejecutar según el modo
        if args.mode == "8h":
            results = await launcher.run_8h_training(
                symbols=args.symbols,
                model_architecture=args.architecture,
                enable_hyperparameter_tuning=args.hyperparameter_tuning,
                enable_data_collection=not args.no_data_collection,
                duration_hours=args.duration,
                config_path=args.config
            )
            
        elif args.mode == "distributed":
            results = await launcher.run_distributed_training(
                symbols=args.symbols,
                model_architecture=args.architecture,
                trainer_type=args.trainer_type,
                max_epochs=args.max_epochs,
                config_path=args.config
            )
            
        elif args.mode == "hyperparameter":
            results = await launcher.run_hyperparameter_optimization(
                symbols=args.symbols,
                model_architecture=args.architecture,
                n_trials=args.n_trials,
                timeout=args.timeout,
                n_jobs=args.n_jobs,
                max_epochs=args.max_epochs,
                config_path=args.config
            )
        
        print(f"\n✅ {args.mode.upper()} completado exitosamente")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ {args.mode.upper()} interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error en {args.mode.upper()}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
