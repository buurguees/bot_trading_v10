# Ruta: core/ml/enterprise/hyperparameter_tuning.py
#!/usr/bin/env python3
"""
Enterprise Hyperparameter Tuning - Sistema de Optimización Automática
=====================================================================

Sistema enterprise-grade para hyperparameter tuning con:
- Optimización bayesiana con Optuna
- Multi-objective optimization
- Early stopping inteligente
- Parallel execution
- MLflow integration
- Advanced pruning strategies

Uso:
    from models.enterprise.hyperparameter_tuning import EnterpriseHyperparameterTuner
    
    tuner = EnterpriseHyperparameterTuner()
    best_params = await tuner.optimize(training_config, data_config)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, asdict
import json
import pickle
from pathlib import Path

import optuna
from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler
from optuna.pruners import MedianPruner, SuccessiveHalvingPruner, HyperbandPruner
from optuna.visualization import plot_optimization_history, plot_param_importances
import plotly.graph_objects as go

import mlflow
import mlflow.optuna

import numpy as np
import pandas as pd

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class HyperparameterSpace:
    """Espacio de búsqueda de hyperparámetros"""
    # Modelo
    hidden_size: Tuple[int, int] = (64, 256)  # (min, max)
    num_layers: Tuple[int, int] = (1, 5)
    dropout: Tuple[float, float] = (0.1, 0.5)
    attention_heads: Tuple[int, int] = (4, 16)
    
    # Entrenamiento
    learning_rate: Tuple[float, float] = (1e-5, 1e-2)  # log scale
    weight_decay: Tuple[float, float] = (1e-6, 1e-3)  # log scale
    batch_size: List[int] = [16, 32, 64, 128, 256]
    
    # Optimización
    optimizer: List[str] = ["adam", "adamw", "sgd", "rmsprop"]
    scheduler: List[str] = ["cosine", "step", "plateau", "none"]
    warmup_epochs: Tuple[int, int] = (0, 10)
    
    # Regularización
    l1_regularization: Tuple[float, float] = (0.0, 1e-4)
    l2_regularization: Tuple[float, float] = (0.0, 1e-3)
    gradient_clip_val: Tuple[float, float] = (0.1, 10.0)
    
    # Arquitectura
    activation: List[str] = ["relu", "gelu", "swish", "leaky_relu"]
    normalization: List[str] = ["batch", "layer", "instance", "none"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return asdict(self)

@dataclass
class TuningConfig:
    """Configuración del tuning de hyperparámetros"""
    # Optimización
    n_trials: int = 100
    timeout: int = 3600  # segundos
    n_jobs: int = 1
    
    # Sampler
    sampler_type: str = "tpe"  # tpe, cmaes, random
    sampler_kwargs: Dict[str, Any] = None
    
    # Pruner
    pruner_type: str = "median"  # median, halving, hyperband
    pruner_kwargs: Dict[str, Any] = None
    
    # Early stopping
    early_stopping_patience: int = 10
    min_trials: int = 20
    
    # Objetivos
    primary_metric: str = "val_loss"
    secondary_metrics: List[str] = None
    direction: str = "minimize"  # minimize, maximize
    
    # MLflow
    experiment_name: str = "hyperparameter_tuning"
    tracking_uri: str = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/hyperparameter_tuning.log"
    
    def __post_init__(self):
        if self.sampler_kwargs is None:
            self.sampler_kwargs = {}
        if self.pruner_kwargs is None:
            self.pruner_kwargs = {}
        if self.secondary_metrics is None:
            self.secondary_metrics = ["train_loss", "val_accuracy"]

class ObjectiveFunction:
    """Función objetivo para optimización"""
    
    def __init__(
        self,
        training_function: Callable,
        data_config: Dict[str, Any],
        tuning_config: TuningConfig,
        hyperparameter_space: HyperparameterSpace
    ):
        self.training_function = training_function
        self.data_config = data_config
        self.tuning_config = tuning_config
        self.hyperparameter_space = hyperparameter_space
        self.logger = logging.getLogger(__name__)
        
        # Historial de trials
        self.trial_history = []
        self.best_score = float('inf') if tuning_config.direction == "minimize" else float('-inf')
        self.best_params = None
    
    def __call__(self, trial: optuna.Trial) -> float:
        """Ejecuta un trial de optimización"""
        try:
            # Sugerir hyperparámetros
            params = self._suggest_parameters(trial)
            
            # Crear configuración de entrenamiento
            training_config = self._create_training_config(params)
            
            # Ejecutar entrenamiento
            start_time = time.time()
            results = asyncio.run(self.training_function(training_config, self.data_config))
            training_time = time.time() - start_time
            
            # Extraer métrica principal
            primary_score = results.get(self.tuning_config.primary_metric, float('inf'))
            
            # Verificar si es el mejor resultado
            is_best = self._is_best_score(primary_score)
            if is_best:
                self.best_score = primary_score
                self.best_params = params.copy()
            
            # Registrar trial
            trial_info = {
                "trial_number": trial.number,
                "params": params,
                "primary_score": primary_score,
                "training_time": training_time,
                "is_best": is_best,
                "timestamp": datetime.now().isoformat()
            }
            
            # Agregar métricas secundarias
            for metric in self.tuning_config.secondary_metrics:
                trial_info[metric] = results.get(metric, None)
            
            self.trial_history.append(trial_info)
            
            # Logging
            self.logger.info(
                f"Trial {trial.number}: {self.tuning_config.primary_metric}={primary_score:.4f}, "
                f"time={training_time:.2f}s, best={is_best}"
            )
            
            return primary_score
            
        except Exception as e:
            self.logger.error(f"Error en trial {trial.number}: {e}")
            return float('inf') if self.tuning_config.direction == "minimize" else float('-inf')
    
    def _suggest_parameters(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Sugiere parámetros para el trial"""
        params = {}
        
        # Parámetros del modelo
        params["hidden_size"] = trial.suggest_int(
            "hidden_size", 
            self.hyperparameter_space.hidden_size[0],
            self.hyperparameter_space.hidden_size[1]
        )
        
        params["num_layers"] = trial.suggest_int(
            "num_layers",
            self.hyperparameter_space.num_layers[0],
            self.hyperparameter_space.num_layers[1]
        )
        
        params["dropout"] = trial.suggest_float(
            "dropout",
            self.hyperparameter_space.dropout[0],
            self.hyperparameter_space.dropout[1]
        )
        
        params["attention_heads"] = trial.suggest_int(
            "attention_heads",
            self.hyperparameter_space.attention_heads[0],
            self.hyperparameter_space.attention_heads[1]
        )
        
        # Parámetros de entrenamiento
        params["learning_rate"] = trial.suggest_float(
            "learning_rate",
            self.hyperparameter_space.learning_rate[0],
            self.hyperparameter_space.learning_rate[1],
            log=True
        )
        
        params["weight_decay"] = trial.suggest_float(
            "weight_decay",
            self.hyperparameter_space.weight_decay[0],
            self.hyperparameter_space.weight_decay[1],
            log=True
        )
        
        params["batch_size"] = trial.suggest_categorical(
            "batch_size",
            self.hyperparameter_space.batch_size
        )
        
        # Optimizador
        params["optimizer"] = trial.suggest_categorical(
            "optimizer",
            self.hyperparameter_space.optimizer
        )
        
        params["scheduler"] = trial.suggest_categorical(
            "scheduler",
            self.hyperparameter_space.scheduler
        )
        
        params["warmup_epochs"] = trial.suggest_int(
            "warmup_epochs",
            self.hyperparameter_space.warmup_epochs[0],
            self.hyperparameter_space.warmup_epochs[1]
        )
        
        # Regularización
        params["l1_regularization"] = trial.suggest_float(
            "l1_regularization",
            self.hyperparameter_space.l1_regularization[0],
            self.hyperparameter_space.l1_regularization[1]
        )
        
        params["l2_regularization"] = trial.suggest_float(
            "l2_regularization",
            self.hyperparameter_space.l2_regularization[0],
            self.hyperparameter_space.l2_regularization[1]
        )
        
        params["gradient_clip_val"] = trial.suggest_float(
            "gradient_clip_val",
            self.hyperparameter_space.gradient_clip_val[0],
            self.hyperparameter_space.gradient_clip_val[1]
        )
        
        # Arquitectura
        params["activation"] = trial.suggest_categorical(
            "activation",
            self.hyperparameter_space.activation
        )
        
        params["normalization"] = trial.suggest_categorical(
            "normalization",
            self.hyperparameter_space.normalization
        )
        
        return params
    
    def _create_training_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crea configuración de entrenamiento desde parámetros"""
        # Convertir parámetros a configuración de entrenamiento
        # Esto dependería de la implementación específica del modelo
        config = {
            "model": {
                "hidden_size": params["hidden_size"],
                "num_layers": params["num_layers"],
                "dropout": params["dropout"],
                "attention_heads": params["attention_heads"],
                "activation": params["activation"],
                "normalization": params["normalization"]
            },
            "training": {
                "learning_rate": params["learning_rate"],
                "weight_decay": params["weight_decay"],
                "batch_size": params["batch_size"],
                "optimizer": params["optimizer"],
                "scheduler": params["scheduler"],
                "warmup_epochs": params["warmup_epochs"],
                "gradient_clip_val": params["gradient_clip_val"]
            },
            "regularization": {
                "l1_regularization": params["l1_regularization"],
                "l2_regularization": params["l2_regularization"]
            }
        }
        
        return config
    
    def _is_best_score(self, score: float) -> bool:
        """Verifica si el score es el mejor hasta ahora"""
        if self.tuning_config.direction == "minimize":
            return score < self.best_score
        else:
            return score > self.best_score

class EnterpriseHyperparameterTuner:
    """Sistema de tuning de hyperparámetros enterprise"""
    
    def __init__(self, config: TuningConfig = None):
        self.config = config or TuningConfig()
        self.logger = logging.getLogger(__name__)
        
        # Configurar logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.log_file),
                logging.StreamHandler()
            ]
        )
        
        # Configurar MLflow
        if self.config.tracking_uri:
            mlflow.set_tracking_uri(self.config.tracking_uri)
        
        # Estado
        self.study = None
        self.objective_function = None
        self.tuning_results = None
    
    def _create_sampler(self) -> optuna.samplers.BaseSampler:
        """Crea sampler para optimización"""
        if self.config.sampler_type == "tpe":
            return TPESampler(**self.config.sampler_kwargs)
        elif self.config.sampler_type == "cmaes":
            return CmaEsSampler(**self.config.sampler_kwargs)
        elif self.config.sampler_type == "random":
            return RandomSampler(**self.config.sampler_kwargs)
        else:
            raise ValueError(f"Tipo de sampler no soportado: {self.config.sampler_type}")
    
    def _create_pruner(self) -> optuna.pruners.BasePruner:
        """Crea pruner para optimización"""
        if self.config.pruner_type == "median":
            return MedianPruner(**self.config.pruner_kwargs)
        elif self.config.pruner_type == "halving":
            return SuccessiveHalvingPruner(**self.config.pruner_kwargs)
        elif self.config.pruner_type == "hyperband":
            return HyperbandPruner(**self.config.pruner_kwargs)
        else:
            raise ValueError(f"Tipo de pruner no soportado: {self.config.pruner_type}")
    
    async def optimize(
        self,
        training_function: Callable,
        data_config: Dict[str, Any],
        hyperparameter_space: HyperparameterSpace = None
    ) -> Dict[str, Any]:
        """
        Optimiza hyperparámetros
        
        Args:
            training_function: Función de entrenamiento
            data_config: Configuración de datos
            hyperparameter_space: Espacio de búsqueda de parámetros
        
        Returns:
            Mejores parámetros encontrados
        """
        try:
            self.logger.info("Iniciando optimización de hyperparámetros")
            
            # Usar espacio por defecto si no se proporciona
            if hyperparameter_space is None:
                hyperparameter_space = HyperparameterSpace()
            
            # Crear función objetivo
            self.objective_function = ObjectiveFunction(
                training_function=training_function,
                data_config=data_config,
                tuning_config=self.config,
                hyperparameter_space=hyperparameter_space
            )
            
            # Crear estudio
            self.study = optuna.create_study(
                direction=self.config.direction,
                sampler=self._create_sampler(),
                pruner=self._create_pruner(),
                study_name=f"{self.config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Configurar MLflow
            with mlflow.start_run(run_name=f"hyperparameter_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log configuración
                mlflow.log_params({
                    "n_trials": self.config.n_trials,
                    "timeout": self.config.timeout,
                    "sampler_type": self.config.sampler_type,
                    "pruner_type": self.config.pruner_type,
                    "primary_metric": self.config.primary_metric
                })
                
                # Ejecutar optimización
                self.study.optimize(
                    self.objective_function,
                    n_trials=self.config.n_trials,
                    timeout=self.config.timeout,
                    n_jobs=self.config.n_jobs
                )
            
            # Obtener resultados
            self.tuning_results = await self._get_tuning_results()
            
            self.logger.info(f"Optimización completada. Mejor score: {self.tuning_results['best_score']:.4f}")
            
            return self.tuning_results
            
        except Exception as e:
            self.logger.error(f"Error en optimización: {e}")
            raise
    
    async def _get_tuning_results(self) -> Dict[str, Any]:
        """Obtiene resultados del tuning"""
        if not self.study:
            return {}
        
        # Mejores parámetros
        best_params = self.study.best_params
        best_score = self.study.best_value
        
        # Estadísticas del estudio
        n_trials = len(self.study.trials)
        completed_trials = len([t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE])
        pruned_trials = len([t for t in self.study.trials if t.state == optuna.trial.TrialState.PRUNED])
        failed_trials = len([t for t in self.study.trials if t.state == optuna.trial.TrialState.FAIL])
        
        # Historial de trials
        trial_history = self.objective_function.trial_history if self.objective_function else []
        
        # Importancia de parámetros
        try:
            param_importances = optuna.importance.get_param_importances(self.study)
        except Exception as e:
            self.logger.warning(f"No se pudo calcular importancia de parámetros: {e}")
            param_importances = {}
        
        results = {
            "best_params": best_params,
            "best_score": best_score,
            "n_trials": n_trials,
            "completed_trials": completed_trials,
            "pruned_trials": pruned_trials,
            "failed_trials": failed_trials,
            "param_importances": param_importances,
            "trial_history": trial_history,
            "study_name": self.study.study_name,
            "timestamp": datetime.now().isoformat()
        }
        
        return results
    
    async def get_optimization_history(self) -> pd.DataFrame:
        """Obtiene historial de optimización como DataFrame"""
        if not self.study:
            return pd.DataFrame()
        
        data = []
        for trial in self.study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                row = {
                    "trial_number": trial.number,
                    "value": trial.value,
                    "state": trial.state.name,
                    "datetime_start": trial.datetime_start,
                    "datetime_complete": trial.datetime_complete
                }
                
                # Agregar parámetros
                for param_name, param_value in trial.params.items():
                    row[f"param_{param_name}"] = param_value
                
                data.append(row)
        
        return pd.DataFrame(data)
    
    async def plot_optimization_history(self, save_path: str = None) -> go.Figure:
        """Crea gráfico del historial de optimización"""
        if not self.study:
            return None
        
        fig = plot_optimization_history(self.study)
        
        if save_path:
            fig.write_html(save_path)
            self.logger.info(f"Gráfico guardado en: {save_path}")
        
        return fig
    
    async def plot_param_importances(self, save_path: str = None) -> go.Figure:
        """Crea gráfico de importancia de parámetros"""
        if not self.study:
            return None
        
        try:
            fig = plot_param_importances(self.study)
            
            if save_path:
                fig.write_html(save_path)
                self.logger.info(f"Gráfico de importancia guardado en: {save_path}")
            
            return fig
        except Exception as e:
            self.logger.error(f"Error creando gráfico de importancia: {e}")
            return None
    
    async def save_results(self, file_path: str):
        """Guarda resultados del tuning"""
        if not self.tuning_results:
            self.logger.warning("No hay resultados para guardar")
            return
        
        results_data = {
            "config": asdict(self.config),
            "results": self.tuning_results,
            "study_name": self.study.study_name if self.study else None
        }
        
        with open(file_path, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        self.logger.info(f"Resultados guardados en: {file_path}")
    
    async def load_results(self, file_path: str) -> Dict[str, Any]:
        """Carga resultados del tuning"""
        with open(file_path, 'r') as f:
            results_data = json.load(f)
        
        self.tuning_results = results_data["results"]
        self.logger.info(f"Resultados cargados desde: {file_path}")
        
        return self.tuning_results

# Funciones de utilidad
def create_hyperparameter_space(
    hidden_size_range: Tuple[int, int] = (64, 256),
    learning_rate_range: Tuple[float, float] = (1e-5, 1e-2),
    batch_sizes: List[int] = [16, 32, 64, 128]
) -> HyperparameterSpace:
    """Crea espacio de búsqueda de hyperparámetros"""
    return HyperparameterSpace(
        hidden_size=hidden_size_range,
        learning_rate=learning_rate_range,
        batch_size=batch_sizes
    )

def create_tuning_config(
    n_trials: int = 100,
    timeout: int = 3600,
    sampler_type: str = "tpe",
    pruner_type: str = "median"
) -> TuningConfig:
    """Crea configuración de tuning"""
    return TuningConfig(
        n_trials=n_trials,
        timeout=timeout,
        sampler_type=sampler_type,
        pruner_type=pruner_type
    )

# Ejemplo de uso
async def main():
    """Ejemplo de uso del sistema de tuning"""
    
    # Función de entrenamiento simulada
    async def mock_training_function(training_config: Dict[str, Any], data_config: Dict[str, Any]) -> Dict[str, float]:
        """Función de entrenamiento simulada"""
        # Simular entrenamiento
        await asyncio.sleep(1)
        
        # Simular métricas
        val_loss = np.random.exponential(0.5) + 0.1
        train_loss = val_loss + np.random.normal(0, 0.1)
        val_accuracy = max(0, 1 - val_loss + np.random.normal(0, 0.05))
        
        return {
            "val_loss": val_loss,
            "train_loss": train_loss,
            "val_accuracy": val_accuracy
        }
    
    # Crear configuración
    tuning_config = create_tuning_config(n_trials=20, timeout=300)
    hyperparameter_space = create_hyperparameter_space()
    
    # Crear tuner
    tuner = EnterpriseHyperparameterTuner(tuning_config)
    
    # Configurar datos
    data_config = {"n_samples": 1000, "n_features": 5}
    
    # Optimizar
    results = await tuner.optimize(
        training_function=mock_training_function,
        data_config=data_config,
        hyperparameter_space=hyperparameter_space
    )
    
    print(f"Mejores parámetros: {results['best_params']}")
    print(f"Mejor score: {results['best_score']:.4f}")
    
    # Crear gráficos
    await tuner.plot_optimization_history("optimization_history.html")
    await tuner.plot_param_importances("param_importances.html")
    
    # Guardar resultados
    await tuner.save_results("tuning_results.json")

if __name__ == "__main__":
    asyncio.run(main())
