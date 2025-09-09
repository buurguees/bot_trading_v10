# hyperparameter_optimization.py - Script de optimización de hiperparámetros
# Ubicación: C:\TradingBot_v10\training_scripts\enterprise\hyperparameter_optimization.py

"""
Script para optimización de hiperparámetros enterprise.

Características:
- Optimización bayesiana con Optuna
- Multi-objective optimization
- Parallel execution
- MLflow integration
- Custom metrics para trading
- Visualización de resultados
"""

import asyncio
import logging
import sys
import argparse
import torch
import pytorch_lightning as pl
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
import json
import signal
import optuna
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.enterprise.hyperparameter_tuner import HyperparameterTuner
from models.enterprise.model_architecture import create_model
from models.enterprise.data_module import TradingDataModule
from models.enterprise.distributed_trainer import create_distributed_trainer
from config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/training/hyperparameter_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HyperparameterOptimizationManager:
    """Gestor de optimización de hiperparámetros"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el gestor de optimización
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = config_path or "config/enterprise/hyperparameters.yaml"
        self.config_manager = EnterpriseConfigManager(self.config_path)
        self.config = self.config_manager.load_config()
        
        # Componentes
        self.hyperparameter_tuner = None
        self.distributed_trainer = None
        
        # Estado
        self.is_running = False
        self.optimization_results = None
        
        # Configurar signal handlers
        self.setup_signal_handlers()
        
        logger.info("HyperparameterOptimizationManager inicializado")
    
    def setup_signal_handlers(self):
        """Configura handlers para graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Iniciando parada segura...")
            self.stop_optimization()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_optimization(
        self,
        symbols: List[str],
        model_architecture: str = "lstm_attention",
        n_trials: int = 100,
        timeout: Optional[int] = None,
        n_jobs: int = 1,
        max_epochs: int = 50
    ) -> Dict[str, Any]:
        """
        Inicia optimización de hiperparámetros
        
        Args:
            symbols: Lista de símbolos para optimizar
            model_architecture: Arquitectura del modelo
            n_trials: Número de trials a ejecutar
            timeout: Tiempo límite en segundos
            n_jobs: Número de jobs paralelos
            max_epochs: Número máximo de epochs por trial
            
        Returns:
            Resultados de la optimización
        """
        try:
            logger.info(f"🔧 Iniciando optimización de hiperparámetros")
            logger.info(f"Símbolos: {symbols}")
            logger.info(f"Arquitectura: {model_architecture}")
            logger.info(f"Trials: {n_trials}, Jobs: {n_jobs}")
            
            self.is_running = True
            
            # Crear hyperparameter tuner
            self.hyperparameter_tuner = HyperparameterTuner(self.config)
            
            # Crear distributed trainer
            self.distributed_trainer = create_distributed_trainer(
                self.config.distributed, "ddp"
            )
            
            # Crear función objetivo
            objective_func = self._create_objective_function(
                symbols, model_architecture, max_epochs
            )
            
            # Ejecutar optimización
            self.optimization_results = self.hyperparameter_tuner.optimize(
                objective_func=objective_func,
                n_trials=n_trials,
                timeout=timeout,
                n_jobs=n_jobs
            )
            
            # Procesar resultados
            processed_results = self._process_optimization_results()
            
            # Generar reporte
            self._generate_optimization_report(processed_results)
            
            # Generar visualizaciones
            self._generate_optimization_plots()
            
            logger.info("✅ Optimización de hiperparámetros completada")
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Error en optimización de hiperparámetros: {e}")
            raise
        finally:
            self.is_running = False
            self._cleanup()
    
    def _create_objective_function(
        self,
        symbols: List[str],
        model_architecture: str,
        max_epochs: int
    ):
        """Crea función objetivo para optimización"""
        def objective(trial: optuna.Trial) -> float:
            try:
                # Sugerir hiperparámetros
                hyperparams = self.hyperparameter_tuner.suggest_hyperparameters(
                    trial, model_architecture
                )
                
                # Crear modelo con hiperparámetros
                model_config = self.config.training.model.copy()
                model_config.update(hyperparams)
                
                model = create_model(
                    architecture=model_architecture,
                    config=model_config
                )
                
                # Crear data module para el primer símbolo
                data_module = TradingDataModule(
                    symbol=symbols[0],
                    config=self.config.training.data
                )
                
                # Configurar trainer con pruning callback
                callbacks = [
                    optuna.integration.PyTorchLightningPruningCallback(trial, monitor="val_accuracy")
                ]
                
                trainer = pl.Trainer(
                    max_epochs=max_epochs,
                    callbacks=callbacks,
                    enable_checkpointing=False,
                    enable_progress_bar=False,
                    enable_model_summary=False,
                    logger=False,
                    devices=1,  # Usar 1 GPU para optimización
                    accelerator="auto"
                )
                
                # Entrenar
                trainer.fit(model, data_module)
                
                # Evaluar
                val_results = trainer.validate(model, data_module)
                val_accuracy = val_results[0].get('val_accuracy', 0) if val_results else 0
                
                # Reportar resultado
                trial.report(val_accuracy, step=trainer.current_epoch)
                
                # Verificar si debe ser pruned
                if trainer.should_stop:
                    raise optuna.TrialPruned()
                
                return val_accuracy
                
            except optuna.TrialPruned:
                raise
            except Exception as e:
                logger.error(f"Error en trial {trial.number}: {e}")
                return 0.0
        
        return objective
    
    def _process_optimization_results(self) -> Dict[str, Any]:
        """Procesa resultados de la optimización"""
        if not self.optimization_results:
            return {}
        
        # Obtener mejores parámetros
        best_params = self.hyperparameter_tuner.best_params
        best_value = self.hyperparameter_tuner.best_value
        
        # Obtener estadísticas del estudio
        study = self.hyperparameter_tuner.study
        n_trials = len(study.trials)
        completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
        pruned_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])
        
        # Calcular importancia de parámetros
        try:
            importance = optuna.importance.get_param_importances(study)
        except Exception:
            importance = {}
        
        # Obtener mejores trials
        best_trials = sorted(
            [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE],
            key=lambda x: x.value,
            reverse=study.direction == optuna.study.StudyDirection.MAXIMIZE
        )[:10]
        
        processed = {
            'optimization_summary': {
                'best_value': best_value,
                'best_params': best_params,
                'total_trials': n_trials,
                'completed_trials': completed_trials,
                'pruned_trials': pruned_trials,
                'success_rate': completed_trials / n_trials if n_trials > 0 else 0
            },
            'parameter_importance': importance,
            'best_trials': [
                {
                    'trial_number': t.number,
                    'value': t.value,
                    'params': t.params,
                    'datetime_start': t.datetime_start.isoformat() if t.datetime_start else None,
                    'datetime_complete': t.datetime_complete.isoformat() if t.datetime_complete else None
                }
                for t in best_trials
            ],
            'optimization_history': [
                {
                    'trial': t.number,
                    'value': t.value,
                    'state': t.state.name,
                    'datetime': t.datetime_start.isoformat() if t.datetime_start else None
                }
                for t in study.trials
            ]
        }
        
        return processed
    
    def _generate_optimization_report(self, results: Dict[str, Any]):
        """Genera reporte de optimización"""
        try:
            # Crear directorio de reportes
            report_dir = Path("reports/hyperparameter_optimization")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"hyperparameter_optimization_report_{timestamp}.json"
            
            # Guardar reporte
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte de optimización guardado en {report_file}")
            
            # Imprimir resumen
            self._print_optimization_summary(results)
            
        except Exception as e:
            logger.error(f"Error generando reporte de optimización: {e}")
    
    def _print_optimization_summary(self, results: Dict[str, Any]):
        """Imprime resumen de la optimización"""
        summary = results.get('optimization_summary', {})
        importance = results.get('parameter_importance', {})
        best_trials = results.get('best_trials', [])
        
        print("\n" + "="*60)
        print("      RESUMEN DE OPTIMIZACIÓN DE HIPERPARÁMETROS")
        print("="*60)
        
        print(f"🎯 Mejor valor: {summary.get('best_value', 0):.4f}")
        print(f"📊 Trials totales: {summary.get('total_trials', 0)}")
        print(f"✅ Trials completados: {summary.get('completed_trials', 0)}")
        print(f"✂️  Trials pruned: {summary.get('pruned_trials', 0)}")
        print(f"📈 Tasa de éxito: {summary.get('success_rate', 0)*100:.1f}%")
        
        print(f"\n🏆 MEJORES PARÁMETROS:")
        best_params = summary.get('best_params', {})
        for param, value in best_params.items():
            print(f"  {param}: {value}")
        
        print(f"\n📊 IMPORTANCIA DE PARÁMETROS:")
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        for param, importance_val in sorted_importance[:5]:
            print(f"  {param}: {importance_val:.4f}")
        
        print(f"\n🥇 TOP 5 TRIALS:")
        for i, trial in enumerate(best_trials[:5]):
            print(f"  {i+1}. Trial {trial['trial_number']}: {trial['value']:.4f}")
        
        print("="*60)
    
    def _generate_optimization_plots(self):
        """Genera gráficos de optimización"""
        try:
            if not self.hyperparameter_tuner:
                return
            
            # Crear directorio de plots
            plots_dir = Path("reports/hyperparameter_optimization/plots")
            plots_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar gráfico de historial
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_plot = plots_dir / f"optimization_history_{timestamp}.png"
            self.hyperparameter_tuner.plot_optimization_history(str(history_plot))
            
            logger.info(f"Gráficos de optimización guardados en {plots_dir}")
            
        except Exception as e:
            logger.error(f"Error generando gráficos de optimización: {e}")
    
    def stop_optimization(self):
        """Detiene la optimización de forma segura"""
        logger.info("🛑 Deteniendo optimización...")
        self.is_running = False
        
        if self.hyperparameter_tuner and self.hyperparameter_tuner.study:
            # Guardar estudio actual
            study_file = f"checkpoints/hyperparameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.hyperparameter_tuner.save_study(study_file)
    
    def _cleanup(self):
        """Limpia recursos al finalizar"""
        try:
            if self.hyperparameter_tuner:
                # Guardar estudio
                study_file = f"checkpoints/hyperparameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                self.hyperparameter_tuner.save_study(study_file)
            
            logger.info("✅ Cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Optimización de hiperparámetros enterprise")
    parser.add_argument("--symbols", nargs="+", required=True, help="Símbolos para optimizar")
    parser.add_argument("--architecture", default="lstm_attention", 
                       choices=["lstm_attention", "transformer", "cnn_lstm", "gru_simple"],
                       help="Arquitectura del modelo")
    parser.add_argument("--n-trials", type=int, default=100,
                       help="Número de trials a ejecutar")
    parser.add_argument("--timeout", type=int, help="Tiempo límite en segundos")
    parser.add_argument("--n-jobs", type=int, default=1,
                       help="Número de jobs paralelos")
    parser.add_argument("--max-epochs", type=int, default=50,
                       help="Número máximo de epochs por trial")
    parser.add_argument("--config", help="Ruta al archivo de configuración")
    
    args = parser.parse_args()
    
    # Crear gestor de optimización
    manager = HyperparameterOptimizationManager(args.config)
    
    try:
        # Ejecutar optimización
        results = await manager.start_optimization(
            symbols=args.symbols,
            model_architecture=args.architecture,
            n_trials=args.n_trials,
            timeout=args.timeout,
            n_jobs=args.n_jobs,
            max_epochs=args.max_epochs
        )
        
        print(f"\n✅ Optimización de hiperparámetros completada exitosamente")
        print(f"🎯 Mejor valor: {results.get('optimization_summary', {}).get('best_value', 0):.4f}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Optimización interrumpida por el usuario")
        manager.stop_optimization()
    except Exception as e:
        print(f"\n❌ Error en optimización de hiperparámetros: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
