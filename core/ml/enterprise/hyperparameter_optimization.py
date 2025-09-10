# Ruta: core/ml/enterprise/hyperparameter_optimization.py
"""
Enterprise Hyperparameter Optimization - Sistema de Optimización Automática
=====================================================================

Sistema enterprise-grade para optimización de hiperparámetros con:
- Optimización bayesiana con Optuna (TPE, CmaEs, Random)
- Multi-objective optimization (val_loss, val_accuracy, Sharpe, drawdown)
- Ejecución asíncrona y paralela
- Integración con MLflow y Redis
- Visualización interactiva (Plotly) y estática (Matplotlib)
- Métricas trading específicas (Sortino, max drawdown)

Uso:
    from core.ml.enterprise.hyperparameter_optimization import EnterpriseHyperparameterTuner
    tuner = EnterpriseHyperparameterTuner(config)
    best_params = await tuner.optimize(training_config, data_config)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, asdict
import json
import pickle
from pathlib import Path
import yaml

import optuna
from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler
from optuna.pruners import MedianPruner, SuccessiveHalvingPruner, HyperbandPruner
from optuna.integration import PyTorchLightningPruningCallback
from optuna.visualization import plot_optimization_history, plot_param_importances
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import mlflow
import mlflow.optuna
import redis

# Importar ConfigLoader
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

@dataclass
class HyperparameterSpace:
    """Espacio de búsqueda de hiperparámetros"""
    hidden_size: Tuple[int, int] = (64, 256)  # (min, max)
    num_layers: Tuple[int, int] = (1, 5)
    dropout: Tuple[float, float] = (0.1, 0.5)
    attention_heads: Tuple[int, int] = (4, 16)
    learning_rate: Tuple[float, float] = (1e-5, 1e-2)  # log scale
    weight_decay: Tuple[float, float] = (1e-6, 1e-3)  # log scale
    batch_size: List[int] = [16, 32, 64, 128, 256]
    optimizer: List[str] = ["adam", "adamw", "sgd", "rmsprop"]
    scheduler: List[str] = ["cosine", "step", "plateau", "none"]
    warmup_epochs: Tuple[int, int] = (0, 10)
    l1_regularization: Tuple[float, float] = (0.0, 1e-4)
    l2_regularization: Tuple[float, float] = (0.0, 1e-3)
    gradient_clip_val: Tuple[float, float] = (0.1, 10.0)

@dataclass
class TuningConfig:
    """Configuración de optimización"""
    n_trials: int = 100
    timeout: int = 3600  # segundos
    sampler_type: str = "tpe"
    pruner_type: str = "median"
    study_name: str = "trading_bot_optimization"
    direction: str = "maximize"  # or minimize
    storage: str = "sqlite:///optuna_study.db"
    n_jobs: int = 4
    redis_cache: bool = False
    redis_url: str = "redis://localhost:6379"

class EnterpriseHyperparameterTuner:
    """Optimizador de hiperparámetros enterprise"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.study = None
        self.best_params = None
        self.best_value = None
        self.redis_client = None
        self._setup_optuna()
        if config.get('redis_cache', False):
            self._setup_redis()

    def _setup_optuna(self):
        """Configura Optuna con la configuración especificada"""
        study_config = self.config.get('study', {})
        study_name = study_config.get('study_name', self.config.get('study_name', 'trading_bot_optimization'))
        direction = study_config.get('direction', self.config.get('direction', 'maximize'))
        storage = study_config.get('storage', self.config.get('storage', 'sqlite:///optuna_study.db'))

        sampler_config = self.config.get('sampler', {})
        sampler_name = sampler_config.get('name', self.config.get('sampler_type', 'tpe'))
        if sampler_name.lower() == 'tpe':
            sampler = TPESampler(n_startup_trials=sampler_config.get('n_startup_trials', 10))
        elif sampler_name.lower() == 'cmaes':
            sampler = CmaEsSampler()
        elif sampler_name.lower() == 'random':
            sampler = RandomSampler()
        else:
            raise ValueError(f"Sampler no soportado: {sampler_name}")

        pruner_config = self.config.get('pruner', {})
        pruner_name = pruner_config.get('name', self.config.get('pruner_type', 'median'))
        if pruner_name.lower() == 'median':
            pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=30)
        elif pruner_name.lower() == 'hyperband':
            pruner = HyperbandPruner()
        elif pruner_name.lower() == 'successivehalving':
            pruner = SuccessiveHalvingPruner()
        else:
            raise ValueError(f"Pruner no soportado: {pruner_name}")

        self.study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=sampler,
            pruner=pruner,
            storage=storage
        )

    def _setup_redis(self):
        """Configura Redis para caching de trials"""
        try:
            self.redis_client = redis.Redis.from_url(self.config.get('redis_url', 'redis://localhost:6379'))
            logger.info("Conexión a Redis establecida para caching de trials")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None

    async def optimize(
        self,
        training_function: Callable,
        data_config: Dict[str, Any],
        hyperparameter_space: Optional[HyperparameterSpace] = None
    ) -> Dict[str, Any]:
        """Optimiza hiperparámetros de forma asíncrona"""
        try:
            def objective(trial: optuna.trial.Trial) -> float:
                params = {}
                space = hyperparameter_space or HyperparameterSpace()
                params['hidden_size'] = trial.suggest_int('hidden_size', space.hidden_size[0], space.hidden_size[1])
                params['num_layers'] = trial.suggest_int('num_layers', space.num_layers[0], space.num_layers[1])
                params['dropout'] = trial.suggest_float('dropout', space.dropout[0], space.dropout[1])
                params['attention_heads'] = trial.suggest_int('attention_heads', space.attention_heads[0], space.attention_heads[1])
                params['learning_rate'] = trial.suggest_float('learning_rate', space.learning_rate[0], space.learning_rate[1], log=True)
                params['weight_decay'] = trial.suggest_float('weight_decay', space.weight_decay[0], space.weight_decay[1], log=True)
                params['batch_size'] = trial.suggest_categorical('batch_size', space.batch_size)
                params['optimizer'] = trial.suggest_categorical('optimizer', space.optimizer)
                params['scheduler'] = trial.suggest_categorical('scheduler', space.scheduler)
                params['warmup_epochs'] = trial.suggest_int('warmup_epochs', space.warmup_epochs[0], space.warmup_epochs[1])
                params['l1_regularization'] = trial.suggest_float('l1_regularization', space.l1_regularization[0], space.l1_regularization[1])
                params['l2_regularization'] = trial.suggest_float('l2_regularization', space.l2_regularization[0], space.l2_regularization[1])
                params['gradient_clip_val'] = trial.suggest_float('gradient_clip_val', space.gradient_clip_val[0], space.gradient_clip_val[1])

                # Cache en Redis
                if self.redis_client:
                    cache_key = f"trial_{trial.number}_{json.dumps(params)}"
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        logger.info(f"Usando resultado cacheado para trial {trial.number}")
                        return float(cached_result)

                # Ejecutar entrenamiento
                loop = asyncio.get_event_loop()
                metrics = loop.run_until_complete(training_function(params, data_config))

                # Calcular métricas trading
                val_loss = metrics.get('val_loss', float('inf'))
                val_accuracy = metrics.get('val_accuracy', 0.0)
                sharpe_ratio = metrics.get('sharpe_ratio', 0.0)
                max_drawdown = metrics.get('max_drawdown', 1.0)

                # Multi-objective (ponderado)
                objective_value = 0.5 * val_accuracy - 0.3 * val_loss + 0.2 * sharpe_ratio - 0.1 * max_drawdown

                # Guardar en MLflow
                with mlflow.start_run():
                    mlflow.log_params(params)
                    mlflow.log_metrics({
                        "val_loss": val_loss,
                        "val_accuracy": val_accuracy,
                        "sharpe_ratio": sharpe_ratio,
                        "max_drawdown": max_drawdown,
                        "objective_value": objective_value
                    })

                # Cachear resultado
                if self.redis_client:
                    self.redis_client.setex(cache_key, 3600, objective_value)

                return objective_value

            # Ejecutar optimización
            n_trials = self.config.get('n_trials', 100)
            timeout = self.config.get('timeout', 3600)
            self.study.optimize(objective, n_trials=n_trials, timeout=timeout, n_jobs=self.config.get('n_jobs', 4))

            self.best_params = self.study.best_params
            self.best_value = self.study.best_value
            logger.info(f"Mejores parámetros: {self.best_params}")
            logger.info(f"Mejor score: {self.best_value:.4f}")

            return {
                "success": True,
                "best_params": self.best_params,
                "best_score": self.best_value,
                "trials": len(self.study.trials)
            }

        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return {"success": False, "error": str(e)}

    async def plot_optimization_history(self, save_path: Optional[str] = None):
        """Genera gráfico interactivo de historial de optimización"""
        try:
            fig = plot_optimization_history(self.study)
            if save_path:
                fig.write_html(save_path)
                logger.info(f"Gráfico interactivo guardado en {save_path}")
            else:
                fig.show()

            # Gráfico estático como respaldo
            plt.figure(figsize=(10, 6))
            trial_numbers = [t.number for t in self.study.trials]
            values = [t.value for t in self.study.trials]
            best_values = []
            current_best = float('-inf') if self.study.direction == optuna.study.StudyDirection.MAXIMIZE else float('inf')
            for value in values:
                if value is not None:
                    if self.study.direction == optuna.study.StudyDirection.MAXIMIZE:
                        if value > current_best:
                            current_best = value
                    else:
                        if value < current_best:
                            current_best = value
                best_values.append(current_best)
            
            plt.plot(trial_numbers, best_values, 'r-', linewidth=2, label='Best Value')
            plt.xlabel('Trial Number')
            plt.ylabel('Objective Value')
            plt.title('Optimization History')
            plt.legend()
            plt.grid(True, alpha=0.3)
            static_path = save_path.replace('.html', '.png') if save_path else 'optimization_history.png'
            plt.savefig(static_path, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Gráfico estático guardado en {static_path}")

        except Exception as e:
            logger.error(f"Error generando gráfico: {e}")

    async def plot_param_importances(self, save_path: Optional[str] = None):
        """Genera gráfico de importancia de parámetros"""
        try:
            fig = plot_param_importances(self.study)
            if save_path:
                fig.write_html(save_path)
                logger.info(f"Gráfico interactivo guardado en {save_path}")
            else:
                fig.show()

        except Exception as e:
            logger.error(f"Error generando gráfico: {e}")

    async def save_results(self, filepath: str):
        """Guarda resultados de optimización"""
        try:
            results = {
                "best_params": self.best_params,
                "best_score": self.best_value,
                "trials": [asdict(trial) for trial in self.study.trials],
                "timestamp": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Resultados guardados en {filepath}")
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

    def get_best_trial(self) -> Optional[optuna.trial.FrozenTrial]:
        """Obtiene el mejor trial"""
        return self.study.best_trial if self.study else None

def create_hyperparameter_tuner(config_path: Optional[str] = None) -> 'EnterpriseHyperparameterTuner':
    """Factory function para crear HyperparameterTuner"""
    # Configuración por defecto
    config = {
        "study_name": "trading_bot_optimization",
        "direction": "maximize",
        "storage": "sqlite:///optuna_study.db",
        "n_trials": 100,
        "timeout": 3600,
        "sampler_type": "tpe",
        "pruner_type": "median",
        "n_jobs": 4,
        "redis_cache": False,
        "redis_url": "redis://localhost:6379"
    }
    
    # Cargar configuración desde archivo si se proporciona
    if config_path:
        with open(config_path, 'r') as f:
            config.update(yaml.safe_load(f))
    else:
        # Intentar cargar desde configuración del proyecto
        try:
            config_loader = ConfigLoader("config/data_config.yaml")
            data_config = config_loader.load_config()
            
            # Usar configuración de Redis del proyecto
            if data_config.get('database', {}).get('redis', {}).get('enabled', False):
                config['redis_cache'] = True
                config['redis_url'] = data_config['database']['redis']['url']
            
            # Cargar configuración específica de hiperparámetros si existe
            try:
                hyperparam_config_loader = ConfigLoader("config/enterprise/hyperparameter_config.yaml")
                hyperparam_config = hyperparam_config_loader.load_config()
                config.update(hyperparam_config)
            except FileNotFoundError:
                logger.info("No se encontró config/enterprise/hyperparameter_config.yaml, usando configuración por defecto")
                
        except Exception as e:
            logger.warning(f"Error cargando configuración del proyecto: {e}, usando configuración por defecto")
    
    return EnterpriseHyperparameterTuner(config)

async def main():
    """Ejemplo de uso"""
    async def mock_training_function(training_config: Dict[str, Any], data_config: Dict[str, Any]) -> Dict[str, float]:
        await asyncio.sleep(1)
        val_loss = np.random.exponential(0.5) + 0.1
        train_loss = val_loss + np.random.normal(0, 0.1)
        val_accuracy = max(0, 1 - val_loss + np.random.normal(0, 0.05))
        sharpe_ratio = np.random.normal(1.0, 0.5)
        max_drawdown = np.random.uniform(0.1, 0.5)
        return {
            "val_loss": val_loss,
            "train_loss": train_loss,
            "val_accuracy": val_accuracy,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown
        }

    tuner = create_hyperparameter_tuner()
    data_config = {"n_samples": 1000, "n_features": 5}
    hyperparameter_space = HyperparameterSpace()
    results = await tuner.optimize(mock_training_function, data_config, hyperparameter_space)
    print(f"Mejores parámetros: {results['best_params']}")
    print(f"Mejor score: {results['best_score']:.4f}")
    await tuner.plot_optimization_history("optimization_history.html")
    await tuner.plot_param_importances("param_importances.html")
    await tuner.save_results("tuning_results.json")

if __name__ == "__main__":
    asyncio.run(main())