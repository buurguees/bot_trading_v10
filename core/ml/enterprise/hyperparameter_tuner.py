# hyperparameter_tuner.py - Optimizador de hiperparámetros enterprise
# Ubicación: C:\TradingBot_v10\models\enterprise\hyperparameter_tuner.py

"""
Optimizador de hiperparámetros enterprise usando Optuna.

Características:
- Optimización bayesiana con TPE
- Pruning automático de trials
- Multi-objective optimization
- Parallel execution
- MLflow integration
- Custom metrics para trading
"""

import optuna
from optuna.integration import PyTorchLightningPruningCallback
from optuna.pruners import MedianPruner, SuccessiveHalvingPruner
from optuna.samplers import TPESampler, RandomSampler, CmaEsSampler
import torch
import pytorch_lightning as pl
import logging
import yaml
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import json
import numpy as np
from datetime import datetime
import mlflow
import mlflow.optuna

logger = logging.getLogger(__name__)

class HyperparameterTuner:
    """Optimizador de hiperparámetros enterprise"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el optimizador de hiperparámetros
        
        Args:
            config: Configuración de optimización
        """
        self.config = config
        self.study = None
        self.best_params = None
        self.best_value = None
        
        # Configurar Optuna
        self._setup_optuna()
        
    def _setup_optuna(self):
        """Configura Optuna con la configuración especificada"""
        # Configuración del estudio
        study_config = self.config.get('study', {})
        study_name = study_config.get('study_name', 'trading_bot_optimization')
        direction = study_config.get('direction', 'maximize')
        storage = study_config.get('storage', 'sqlite:///optuna_study.db')
        
        # Configurar sampler
        sampler_config = self.config.get('sampler', {})
        sampler_name = sampler_config.get('name', 'TPESampler')
        
        if sampler_name == 'TPESampler':
            sampler = TPESampler(
                n_startup_trials=sampler_config.get('n_startup_trials', 10),
                n_ei_candidates=sampler_config.get('n_ei_candidates', 24)
            )
        elif sampler_name == 'RandomSampler':
            sampler = RandomSampler()
        elif sampler_name == 'CmaEsSampler':
            sampler = CmaEsSampler()
        else:
            sampler = TPESampler()
        
        # Configurar pruner
        pruner_config = self.config.get('pruner', {})
        pruner_name = pruner_config.get('name', 'MedianPruner')
        
        if pruner_name == 'MedianPruner':
            pruner = MedianPruner(
                n_startup_trials=pruner_config.get('n_startup_trials', 5),
                n_warmup_steps=pruner_config.get('n_warmup_steps', 30),
                interval_steps=pruner_config.get('interval_steps', 10)
            )
        elif pruner_name == 'SuccessiveHalvingPruner':
            pruner = SuccessiveHalvingPruner()
        else:
            pruner = MedianPruner()
        
        # Crear o cargar estudio
        try:
            self.study = optuna.create_study(
                study_name=study_name,
                direction=direction,
                storage=storage,
                sampler=sampler,
                pruner=pruner,
                load_if_exists=True
            )
        except Exception as e:
            logger.error(f"Error creando estudio Optuna: {e}")
            # Crear estudio sin storage
            self.study = optuna.create_study(
                study_name=study_name,
                direction=direction,
                sampler=sampler,
                pruner=pruner
            )
    
    def optimize(
        self,
        objective_func: Callable,
        n_trials: Optional[int] = None,
        timeout: Optional[int] = None,
        n_jobs: int = 1
    ) -> Dict[str, Any]:
        """
        Ejecuta optimización de hiperparámetros
        
        Args:
            objective_func: Función objetivo a optimizar
            n_trials: Número de trials a ejecutar
            timeout: Tiempo límite en segundos
            n_jobs: Número de jobs paralelos
            
        Returns:
            Resultados de la optimización
        """
        try:
            logger.info("🔧 Iniciando optimización de hiperparámetros")
            
            # Configurar límites
            limits = self.config.get('limits', {})
            n_trials = n_trials or limits.get('n_trials', 100)
            timeout = timeout or limits.get('timeout', 3600)
            n_jobs = min(n_jobs, limits.get('max_concurrent_trials', 4))
            
            # Ejecutar optimización
            self.study.optimize(
                objective_func,
                n_trials=n_trials,
                timeout=timeout,
                n_jobs=n_jobs
            )
            
            # Obtener mejores resultados
            self.best_params = self.study.best_params
            self.best_value = self.study.best_value
            
            # Log resultados
            logger.info(f"✅ Optimización completada")
            logger.info(f"Mejor valor: {self.best_value:.4f}")
            logger.info(f"Mejores parámetros: {self.best_params}")
            
            # Generar reporte
            report = self._generate_report()
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error en optimización: {e}")
            raise
    
    def _generate_report(self) -> Dict[str, Any]:
        """Genera reporte de optimización"""
        if not self.study:
            return {}
        
        # Estadísticas básicas
        n_trials = len(self.study.trials)
        completed_trials = len([t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE])
        pruned_trials = len([t for t in self.study.trials if t.state == optuna.trial.TrialState.PRUNED])
        
        # Mejores trials
        best_trials = sorted(
            [t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE],
            key=lambda x: x.value,
            reverse=self.study.direction == optuna.study.StudyDirection.MAXIMIZE
        )[:5]
        
        # Importancia de parámetros
        try:
            importance = optuna.importance.get_param_importances(self.study)
        except Exception:
            importance = {}
        
        report = {
            'optimization_summary': {
                'total_trials': n_trials,
                'completed_trials': completed_trials,
                'pruned_trials': pruned_trials,
                'best_value': self.best_value,
                'best_params': self.best_params,
                'study_name': self.study.study_name
            },
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
            'parameter_importance': importance,
            'optimization_history': [
                {
                    'trial': t.number,
                    'value': t.value,
                    'state': t.state.name,
                    'datetime': t.datetime_start.isoformat() if t.datetime_start else None
                }
                for t in self.study.trials
            ]
        }
        
        return report
    
    def suggest_hyperparameters(self, trial: optuna.Trial, model_architecture: str) -> Dict[str, Any]:
        """
        Sugiere hiperparámetros para un trial
        
        Args:
            trial: Trial de Optuna
            model_architecture: Arquitectura del modelo
            
        Returns:
            Diccionario con hiperparámetros sugeridos
        """
        search_spaces = self.config.get('search_spaces', {})
        
        if model_architecture not in search_spaces:
            logger.warning(f"Espacio de búsqueda no encontrado para {model_architecture}")
            return {}
        
        space_config = search_spaces[model_architecture]
        suggested_params = {}
        
        # Sugerir parámetros de arquitectura
        if 'architecture' in space_config:
            arch_config = space_config['architecture']
            for param_name, param_config in arch_config.items():
                suggested_params[param_name] = self._suggest_parameter(trial, param_name, param_config)
        
        # Sugerir parámetros de optimización
        if 'optimization' in space_config:
            opt_config = space_config['optimization']
            for param_name, param_config in opt_config.items():
                suggested_params[param_name] = self._suggest_parameter(trial, param_name, param_config)
        
        # Sugerir parámetros de regularización
        if 'regularization' in space_config:
            reg_config = space_config['regularization']
            for param_name, param_config in reg_config.items():
                suggested_params[param_name] = self._suggest_parameter(trial, param_name, param_config)
        
        return suggested_params
    
    def _suggest_parameter(self, trial: optuna.Trial, param_name: str, param_config: Dict[str, Any]) -> Any:
        """Sugiere un parámetro específico"""
        param_type = param_config.get('type', 'float')
        
        if param_type == 'categorical':
            return trial.suggest_categorical(param_name, param_config['choices'])
        elif param_type == 'int':
            return trial.suggest_int(
                param_name,
                param_config['low'],
                param_config['high'],
                step=param_config.get('step', 1)
            )
        elif param_type == 'float':
            return trial.suggest_float(
                param_name,
                param_config['low'],
                param_config['high'],
                step=param_config.get('step', None)
            )
        elif param_type == 'loguniform':
            return trial.suggest_loguniform(
                param_name,
                param_config['low'],
                param_config['high']
            )
        elif param_type == 'uniform':
            return trial.suggest_uniform(
                param_name,
                param_config['low'],
                param_config['high']
            )
        else:
            logger.warning(f"Tipo de parámetro no soportado: {param_type}")
            return param_config.get('default', 0)
    
    def create_objective_function(
        self,
        model_class,
        data_module_class,
        config: Dict[str, Any],
        model_architecture: str,
        symbols: List[str],
        max_epochs: int = 50
    ) -> Callable:
        """
        Crea función objetivo para optimización
        
        Args:
            model_class: Clase del modelo
            data_module_class: Clase del data module
            config: Configuración base
            model_architecture: Arquitectura del modelo
            symbols: Lista de símbolos
            max_epochs: Número máximo de epochs
            
        Returns:
            Función objetivo
        """
        def objective(trial: optuna.Trial) -> float:
            try:
                # Sugerir hiperparámetros
                hyperparams = self.suggest_hyperparameters(trial, model_architecture)
                
                # Crear modelo con hiperparámetros
                model_config = config.get('model', {}).copy()
                model_config.update(hyperparams)
                
                model = model_class(**model_config)
                
                # Crear data module
                data_config = config.get('data', {})
                data_module = data_module_class(symbols[0], data_config)
                
                # Configurar trainer con pruning callback
                callbacks = [
                    PyTorchLightningPruningCallback(trial, monitor="val_accuracy")
                ]
                
                trainer = pl.Trainer(
                    max_epochs=max_epochs,
                    callbacks=callbacks,
                    enable_checkpointing=False,
                    enable_progress_bar=False,
                    enable_model_summary=False,
                    logger=False
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
    
    def save_study(self, filepath: str):
        """Guarda el estudio en un archivo"""
        if not self.study:
            logger.warning("No hay estudio para guardar")
            return
        
        try:
            # Guardar configuración del estudio
            study_data = {
                'study_name': self.study.study_name,
                'direction': self.study.direction.name,
                'best_value': self.best_value,
                'best_params': self.best_params,
                'n_trials': len(self.study.trials),
                'trials': [
                    {
                        'number': t.number,
                        'value': t.value,
                        'params': t.params,
                        'state': t.state.name,
                        'datetime_start': t.datetime_start.isoformat() if t.datetime_start else None,
                        'datetime_complete': t.datetime_complete.isoformat() if t.datetime_complete else None
                    }
                    for t in self.study.trials
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(study_data, f, indent=2)
            
            logger.info(f"Estudio guardado en {filepath}")
            
        except Exception as e:
            logger.error(f"Error guardando estudio: {e}")
    
    def load_study(self, filepath: str):
        """Carga un estudio desde un archivo"""
        try:
            with open(filepath, 'r') as f:
                study_data = json.load(f)
            
            logger.info(f"Estudio cargado desde {filepath}")
            logger.info(f"Estudio: {study_data['study_name']}, Trials: {study_data['n_trials']}")
            
        except Exception as e:
            logger.error(f"Error cargando estudio: {e}")
    
    def plot_optimization_history(self, save_path: Optional[str] = None):
        """Genera gráfico del historial de optimización"""
        if not self.study:
            logger.warning("No hay estudio para graficar")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # Obtener datos de trials
            trials = [t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            if not trials:
                logger.warning("No hay trials completados para graficar")
                return
            
            # Preparar datos
            trial_numbers = [t.number for t in trials]
            values = [t.value for t in trials]
            
            # Crear gráfico
            plt.figure(figsize=(10, 6))
            plt.plot(trial_numbers, values, 'b-', alpha=0.7, label='Trial Values')
            
            # Línea de mejor valor
            best_values = []
            current_best = float('-inf') if self.study.direction == optuna.study.StudyDirection.MAXIMIZE else float('inf')
            
            for i, value in enumerate(values):
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
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Gráfico guardado en {save_path}")
            else:
                plt.show()
            
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generando gráfico: {e}")
    
    def get_best_trial(self) -> Optional[optuna.trial.FrozenTrial]:
        """Obtiene el mejor trial"""
        if not self.study:
            return None
        return self.study.best_trial
    
    def get_trial(self, trial_number: int) -> Optional[optuna.trial.FrozenTrial]:
        """Obtiene un trial específico"""
        if not self.study:
            return None
        return self.study.trials[trial_number] if trial_number < len(self.study.trials) else None

# Funciones de utilidad
def create_hyperparameter_tuner(config_path: str) -> HyperparameterTuner:
    """Factory function para crear HyperparameterTuner"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return HyperparameterTuner(config)

def load_hyperparameter_config(config_path: str) -> Dict[str, Any]:
    """Carga configuración de hiperparámetros"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_mlflow_optuna_callback(experiment_name: str) -> Callable:
    """Crea callback para integración con MLflow"""
    def callback(study: optuna.Study, trial: optuna.trial.FrozenTrial):
        with mlflow.start_run(experiment_id=mlflow.get_experiment_by_name(experiment_name).experiment_id):
            mlflow.log_params(trial.params)
            mlflow.log_metric("objective_value", trial.value)
            mlflow.log_metric("trial_number", trial.number)
    
    return callback
