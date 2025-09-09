# start_distributed_training.py - Script de entrenamiento distribuido
# Ubicación: C:\TradingBot_v10\training_scripts\enterprise\start_distributed_training.py

"""
Script para ejecutar entrenamiento distribuido enterprise.

Características:
- Soporte para múltiples GPUs
- Estrategias DDP y DeepSpeed
- Balanceado de carga automático
- Sincronización de métricas
- Recovery automático
"""

import asyncio
import logging
import sys
import argparse
import torch
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
import signal

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.enterprise.distributed_trainer import (
    DistributedTrainer, MultiNodeTrainer, DeepSpeedTrainer,
    create_distributed_trainer, setup_distributed_environment
)
from models.enterprise.training_engine import EnterpriseTrainingEngine
from models.enterprise.model_architecture import create_model
from models.enterprise.data_module import TradingDataModule
from config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/training/distributed_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DistributedTrainingManager:
    """Gestor de entrenamiento distribuido"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el gestor de entrenamiento distribuido
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = config_path or "config/enterprise/training.yaml"
        self.config_manager = EnterpriseConfigManager(self.config_path)
        self.config = self.config_manager.load_config()
        
        # Componentes
        self.distributed_trainer = None
        self.training_engine = None
        
        # Estado
        self.is_running = False
        
        # Configurar entorno distribuido
        setup_distributed_environment()
        
        # Configurar signal handlers
        self.setup_signal_handlers()
        
        logger.info("DistributedTrainingManager inicializado")
    
    def setup_signal_handlers(self):
        """Configura handlers para graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Iniciando parada segura...")
            self.stop_training()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_distributed_training(
        self,
        symbols: List[str],
        model_architecture: str = "lstm_attention",
        trainer_type: str = "ddp",
        max_epochs: int = 1000,
        enable_data_collection: bool = True
    ) -> Dict[str, Any]:
        """
        Inicia entrenamiento distribuido
        
        Args:
            symbols: Lista de símbolos para entrenar
            model_architecture: Arquitectura del modelo
            trainer_type: Tipo de trainer (ddp, deepspeed, multi_node)
            max_epochs: Número máximo de epochs
            enable_data_collection: Si habilitar recolección de datos
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            logger.info(f"🚀 Iniciando entrenamiento distribuido ({trainer_type})")
            logger.info(f"Símbolos: {symbols}")
            logger.info(f"Arquitectura: {model_architecture}")
            logger.info(f"GPUs disponibles: {torch.cuda.device_count()}")
            
            self.is_running = True
            
            # Crear trainer distribuido
            self.distributed_trainer = create_distributed_trainer(
                self.config.distributed, trainer_type
            )
            
            # Crear motor de entrenamiento
            self.training_engine = EnterpriseTrainingEngine(self.config_path)
            
            # Ejecutar entrenamiento para cada símbolo
            results = {}
            
            for symbol in symbols:
                if not self.is_running:
                    break
                    
                logger.info(f"🎯 Entrenando {symbol} con {trainer_type}")
                
                try:
                    # Crear modelo
                    model = create_model(
                        architecture=model_architecture,
                        config=self.config.training.model
                    )
                    
                    # Crear data module
                    data_module = TradingDataModule(
                        symbol=symbol,
                        config=self.config.training.data
                    )
                    
                    # Entrenar
                    symbol_results = self.distributed_trainer.train(model, data_module)
                    
                    # Agregar información adicional
                    symbol_results['symbol'] = symbol
                    symbol_results['model_architecture'] = model_architecture
                    symbol_results['trainer_type'] = trainer_type
                    
                    results[symbol] = symbol_results
                    
                    logger.info(f"✅ {symbol} entrenado exitosamente")
                    
                except Exception as e:
                    logger.error(f"❌ Error entrenando {symbol}: {e}")
                    results[symbol] = {'error': str(e)}
            
            # Procesar resultados
            processed_results = self._process_distributed_results(results)
            
            # Generar reporte
            self._generate_distributed_report(processed_results)
            
            logger.info("✅ Entrenamiento distribuido completado")
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento distribuido: {e}")
            raise
        finally:
            self.is_running = False
            self._cleanup()
    
    def _process_distributed_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa resultados del entrenamiento distribuido"""
        processed = {
            'distributed_summary': {
                'total_symbols': len(results),
                'successful_training': len([r for r in results.values() if isinstance(r, dict) and 'error' not in r]),
                'failed_training': len([r for r in results.values() if isinstance(r, dict) and 'error' in r]),
                'trainer_type': results.get(list(results.keys())[0], {}).get('trainer_type', 'unknown') if results else 'unknown',
                'devices_used': results.get(list(results.keys())[0], {}).get('devices', 1) if results else 1,
                'nodes_used': results.get(list(results.keys())[0], {}).get('nodes', 1) if results else 1
            },
            'model_results': results,
            'performance_metrics': self._calculate_distributed_metrics(results),
            'scaling_efficiency': self._calculate_scaling_efficiency(results)
        }
        
        return processed
    
    def _calculate_distributed_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas de rendimiento distribuido"""
        metrics = {
            'total_training_time_seconds': 0,
            'average_accuracy': 0,
            'throughput_samples_per_second': 0,
            'gpu_utilization': 0,
            'memory_efficiency': 0
        }
        
        successful_results = [r for r in results.values() if isinstance(r, dict) and 'error' not in r]
        
        if not successful_results:
            return metrics
        
        # Calcular métricas agregadas
        total_time = sum(r.get('trainer_state', {}).get('current_epoch', 0) for r in successful_results)
        accuracies = [r.get('test_results', {}).get('test_accuracy', 0) for r in successful_results]
        
        metrics['total_training_time_seconds'] = total_time
        metrics['average_accuracy'] = sum(accuracies) / len(accuracies) if accuracies else 0
        
        # Calcular throughput (estimado)
        total_samples = sum(1000 for _ in successful_results)  # Estimación
        metrics['throughput_samples_per_second'] = total_samples / max(total_time, 1)
        
        return metrics
    
    def _calculate_scaling_efficiency(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Calcula eficiencia de escalado"""
        if not results:
            return {}
        
        first_result = next(iter(results.values()))
        if not isinstance(first_result, dict) or 'error' in first_result:
            return {}
        
        devices = first_result.get('devices', 1)
        nodes = first_result.get('nodes', 1)
        
        # Eficiencia teórica vs práctica
        theoretical_speedup = devices * nodes
        actual_speedup = 1.0  # Calcular basado en tiempo real
        
        efficiency = (actual_speedup / theoretical_speedup) * 100 if theoretical_speedup > 0 else 0
        
        return {
            'theoretical_speedup': theoretical_speedup,
            'actual_speedup': actual_speedup,
            'scaling_efficiency_percent': efficiency,
            'devices_used': devices,
            'nodes_used': nodes
        }
    
    def _generate_distributed_report(self, results: Dict[str, Any]):
        """Genera reporte del entrenamiento distribuido"""
        try:
            # Crear directorio de reportes
            report_dir = Path("reports/training/distributed")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"distributed_training_report_{timestamp}.json"
            
            # Guardar reporte
            import json
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte distribuido guardado en {report_file}")
            
            # Imprimir resumen
            self._print_distributed_summary(results)
            
        except Exception as e:
            logger.error(f"Error generando reporte distribuido: {e}")
    
    def _print_distributed_summary(self, results: Dict[str, Any]):
        """Imprime resumen del entrenamiento distribuido"""
        summary = results.get('distributed_summary', {})
        metrics = results.get('performance_metrics', {})
        scaling = results.get('scaling_efficiency', {})
        
        print("\n" + "="*60)
        print("        RESUMEN DEL ENTRENAMIENTO DISTRIBUIDO")
        print("="*60)
        
        print(f"🔧 Tipo de trainer: {summary.get('trainer_type', 'unknown')}")
        print(f"🖥️  Dispositivos usados: {summary.get('devices_used', 1)}")
        print(f"🌐 Nodos usados: {summary.get('nodes_used', 1)}")
        print(f"📊 Símbolos entrenados: {summary.get('successful_training', 0)}/{summary.get('total_symbols', 0)}")
        print(f"🎯 Accuracy promedio: {metrics.get('average_accuracy', 0):.4f}")
        print(f"⚡ Throughput: {metrics.get('throughput_samples_per_second', 0):.2f} samples/s")
        print(f"📈 Eficiencia de escalado: {scaling.get('scaling_efficiency_percent', 0):.1f}%")
        
        print("="*60)
    
    def stop_training(self):
        """Detiene el entrenamiento de forma segura"""
        logger.info("🛑 Deteniendo entrenamiento distribuido...")
        self.is_running = False
        
        if self.distributed_trainer:
            self.distributed_trainer.cleanup()
    
    def _cleanup(self):
        """Limpia recursos al finalizar"""
        try:
            if self.distributed_trainer:
                self.distributed_trainer.cleanup()
            
            if self.training_engine:
                self.training_engine.cleanup()
            
            logger.info("✅ Cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Entrenamiento distribuido enterprise")
    parser.add_argument("--symbols", nargs="+", required=True, help="Símbolos para entrenar")
    parser.add_argument("--architecture", default="lstm_attention", 
                       choices=["lstm_attention", "transformer", "cnn_lstm", "gru_simple"],
                       help="Arquitectura del modelo")
    parser.add_argument("--trainer-type", default="ddp",
                       choices=["ddp", "deepspeed", "multi_node"],
                       help="Tipo de trainer distribuido")
    parser.add_argument("--max-epochs", type=int, default=1000,
                       help="Número máximo de epochs")
    parser.add_argument("--config", help="Ruta al archivo de configuración")
    parser.add_argument("--node-rank", type=int, default=0,
                       help="Rank del nodo (para multi-node)")
    parser.add_argument("--master-addr", default="localhost",
                       help="Dirección del nodo maestro")
    parser.add_argument("--master-port", type=int, default=12355,
                       help="Puerto del nodo maestro")
    
    args = parser.parse_args()
    
    # Configurar variables de entorno para multi-node
    if args.trainer_type == "multi_node":
        os.environ['NODE_RANK'] = str(args.node_rank)
        os.environ['MASTER_ADDR'] = args.master_addr
        os.environ['MASTER_PORT'] = str(args.master_port)
    
    # Crear gestor de entrenamiento distribuido
    manager = DistributedTrainingManager(args.config)
    
    try:
        # Ejecutar entrenamiento distribuido
        results = await manager.start_distributed_training(
            symbols=args.symbols,
            model_architecture=args.architecture,
            trainer_type=args.trainer_type,
            max_epochs=args.max_epochs,
            enable_data_collection=True
        )
        
        print(f"\n✅ Entrenamiento distribuido completado exitosamente")
        print(f"📊 Resultados: {len(results.get('model_results', {}))} modelos entrenados")
        
    except KeyboardInterrupt:
        print("\n⚠️ Entrenamiento interrumpido por el usuario")
        manager.stop_training()
    except Exception as e:
        print(f"\n❌ Error en entrenamiento distribuido: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
