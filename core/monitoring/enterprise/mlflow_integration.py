# Ruta: core/monitoring/enterprise/mlflow_integration.py
# mlflow_integration.py - Integración con MLflow
# Ubicación: C:\TradingBot_v10\monitoring\enterprise\mlflow_integration.py

"""
Integración con MLflow para experiment tracking.

Características:
- Tracking automático de experimentos
- Logging de métricas y parámetros
- Gestión de modelos
- Comparación de experimentos
- Integración con Prometheus
"""

import mlflow
import mlflow.pytorch
import mlflow.sklearn
import mlflow.xgboost
from mlflow.tracking import MlflowClient
from mlflow.entities import RunStatus
import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import torch
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
import yaml

logger = logging.getLogger(__name__)

@dataclass
class ExperimentConfig:
    """Configuración de experimento"""
    name: str
    description: str
    tags: Dict[str, str]
    artifact_location: Optional[str] = None

@dataclass
class RunInfo:
    """Información de run de MLflow"""
    run_id: str
    experiment_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None

class MLflowIntegration:
    """Integración con MLflow para experiment tracking"""
    
    def __init__(
        self,
        tracking_uri: str = "http://localhost:5000",
        experiment_name: str = "trading_bot_experiments",
        artifact_location: Optional[str] = None
    ):
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.artifact_location = artifact_location
        
        # Configurar MLflow
        self.setup_mlflow()
        
        # Configurar directorios
        self.mlflow_dir = Path("monitoring/mlflow")
        self.mlflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        self.setup_logging()
        
        # Estado del cliente
        self.client = None
        self.current_run = None
        self.experiment_id = None
        
        # Inicializar cliente
        self._initialize_client()
    
    def setup_mlflow(self):
        """Configura MLflow"""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            self.mlflow_logger.info(f"MLflow tracking URI configurado: {self.tracking_uri}")
        except Exception as e:
            self.mlflow_logger.error(f"Error configurando MLflow: {e}")
    
    def setup_logging(self):
        """Configura logging del integrador"""
        mlflow_logger = logging.getLogger(f"{__name__}.MLflowIntegration")
        mlflow_logger.setLevel(logging.INFO)
        
        # Handler para archivo
        file_handler = logging.FileHandler(
            self.mlflow_dir / "mlflow_integration.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        mlflow_logger.addHandler(file_handler)
        self.mlflow_logger = mlflow_logger
    
    def _initialize_client(self):
        """Inicializa cliente de MLflow"""
        try:
            self.client = MlflowClient()
            
            # Crear o obtener experimento
            self.experiment_id = self._get_or_create_experiment()
            
            self.mlflow_logger.info(f"Cliente MLflow inicializado. Experiment ID: {self.experiment_id}")
            
        except Exception as e:
            self.mlflow_logger.error(f"Error inicializando cliente MLflow: {e}")
    
    def _get_or_create_experiment(self) -> str:
        """Obtiene o crea experimento"""
        try:
            # Buscar experimento existente
            experiment = self.client.get_experiment_by_name(self.experiment_name)
            
            if experiment is None:
                # Crear nuevo experimento
                experiment_id = self.client.create_experiment(
                    name=self.experiment_name,
                    artifact_location=self.artifact_location
                )
                self.mlflow_logger.info(f"Experimento creado: {self.experiment_name} (ID: {experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                self.mlflow_logger.info(f"Usando experimento existente: {self.experiment_name} (ID: {experiment_id})")
            
            return experiment_id
            
        except Exception as e:
            self.mlflow_logger.error(f"Error obteniendo/creando experimento: {e}")
            return None
    
    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ) -> str:
        """Inicia un nuevo run"""
        try:
            # Configurar tags por defecto
            default_tags = {
                "trading_bot": "true",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
            
            if tags:
                default_tags.update(tags)
            
            # Iniciar run
            run = mlflow.start_run(
                experiment_id=self.experiment_id,
                run_name=run_name,
                description=description
            )
            
            # Log tags
            for key, value in default_tags.items():
                mlflow.set_tag(key, value)
            
            self.current_run = run
            run_id = run.info.run_id
            
            self.mlflow_logger.info(f"Run iniciado: {run_id}")
            
            return run_id
            
        except Exception as e:
            self.mlflow_logger.error(f"Error iniciando run: {e}")
            return None
    
    def end_run(self, status: str = "FINISHED"):
        """Termina el run actual"""
        try:
            if self.current_run is None:
                self.mlflow_logger.warning("No hay run activo para terminar")
                return
            
            # Terminar run
            mlflow.end_run(status=status)
            
            run_id = self.current_run.info.run_id
            self.mlflow_logger.info(f"Run terminado: {run_id} (Status: {status})")
            
            self.current_run = None
            
        except Exception as e:
            self.mlflow_logger.error(f"Error terminando run: {e}")
    
    def log_parameters(self, params: Dict[str, Any]):
        """Log parámetros del experimento"""
        try:
            if self.current_run is None:
                self.mlflow_logger.warning("No hay run activo para loggear parámetros")
                return
            
            # Log parámetros
            for key, value in params.items():
                mlflow.log_param(key, value)
            
            self.mlflow_logger.info(f"Parámetros loggeados: {len(params)} parámetros")
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando parámetros: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log métricas del experimento"""
        try:
            if self.current_run is None:
                self.mlflow_logger.warning("No hay run activo para loggear métricas")
                return
            
            # Log métricas
            for key, value in metrics.items():
                if step is not None:
                    mlflow.log_metric(key, value, step=step)
                else:
                    mlflow.log_metric(key, value)
            
            self.mlflow_logger.info(f"Métricas loggeadas: {len(metrics)} métricas")
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando métricas: {e}")
    
    def log_artifacts(self, artifacts_path: str, artifact_path: Optional[str] = None):
        """Log artefactos del experimento"""
        try:
            if self.current_run is None:
                self.mlflow_logger.warning("No hay run activo para loggear artefactos")
                return
            
            # Log artefactos
            mlflow.log_artifacts(artifacts_path, artifact_path)
            
            self.mlflow_logger.info(f"Artefactos loggeados: {artifacts_path}")
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando artefactos: {e}")
    
    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: Optional[str] = None,
        model_type: str = "pytorch"
    ):
        """Log modelo del experimento"""
        try:
            if self.current_run is None:
                self.mlflow_logger.warning("No hay run activo para loggear modelo")
                return
            
            # Log modelo según tipo
            if model_type == "pytorch":
                mlflow.pytorch.log_model(model, artifact_path, registered_model_name)
            elif model_type == "sklearn":
                mlflow.sklearn.log_model(model, artifact_path, registered_model_name)
            elif model_type == "xgboost":
                mlflow.xgboost.log_model(model, artifact_path, registered_model_name)
            else:
                mlflow.log_model(model, artifact_path, registered_model_name)
            
            self.mlflow_logger.info(f"Modelo loggeado: {artifact_path} (Tipo: {model_type})")
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando modelo: {e}")
    
    def log_training_metrics(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        train_accuracy: float,
        val_accuracy: float,
        learning_rate: float,
        additional_metrics: Optional[Dict[str, float]] = None
    ):
        """Log métricas de entrenamiento"""
        try:
            metrics = {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "train_accuracy": train_accuracy,
                "val_accuracy": val_accuracy,
                "learning_rate": learning_rate
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            self.log_metrics(metrics, step=epoch)
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando métricas de entrenamiento: {e}")
    
    def log_trading_metrics(
        self,
        symbol: str,
        pnl: float,
        trades_count: int,
        win_rate: float,
        sharpe_ratio: float,
        max_drawdown: float,
        additional_metrics: Optional[Dict[str, float]] = None
    ):
        """Log métricas de trading"""
        try:
            metrics = {
                f"trading_{symbol}_pnl": pnl,
                f"trading_{symbol}_trades_count": trades_count,
                f"trading_{symbol}_win_rate": win_rate,
                f"trading_{symbol}_sharpe_ratio": sharpe_ratio,
                f"trading_{symbol}_max_drawdown": max_drawdown
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            self.log_metrics(metrics)
            
        except Exception as e:
            self.mlflow_logger.error(f"Error loggeando métricas de trading: {e}")
    
    def get_experiment_runs(
        self,
        experiment_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtiene runs del experimento"""
        try:
            exp_id = experiment_id or self.experiment_id
            
            if exp_id is None:
                self.mlflow_logger.warning("No hay experimento configurado")
                return []
            
            # Obtener runs
            runs = self.client.search_runs(
                experiment_ids=[exp_id],
                filter_string=f"status = '{status}'" if status else None,
                max_results=limit
            )
            
            # Convertir a diccionarios
            runs_data = []
            for run in runs:
                run_data = {
                    'run_id': run.info.run_id,
                    'experiment_id': run.info.experiment_id,
                    'status': run.info.status,
                    'start_time': datetime.fromtimestamp(run.info.start_time / 1000),
                    'end_time': datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None,
                    'duration_seconds': (run.info.end_time - run.info.start_time) / 1000 if run.info.end_time else None,
                    'params': run.data.params,
                    'metrics': run.data.metrics,
                    'tags': run.data.tags
                }
                runs_data.append(run_data)
            
            self.mlflow_logger.info(f"Runs obtenidos: {len(runs_data)}")
            
            return runs_data
            
        except Exception as e:
            self.mlflow_logger.error(f"Error obteniendo runs: {e}")
            return []
    
    def compare_runs(
        self,
        run_ids: List[str],
        metrics: List[str],
        params: List[str] = None
    ) -> pd.DataFrame:
        """Compara runs del experimento"""
        try:
            # Obtener datos de runs
            runs_data = []
            for run_id in run_ids:
                run = self.client.get_run(run_id)
                
                run_data = {
                    'run_id': run_id,
                    'experiment_id': run.info.experiment_id,
                    'status': run.info.status,
                    'start_time': datetime.fromtimestamp(run.info.start_time / 1000),
                    'end_time': datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None
                }
                
                # Agregar métricas
                for metric in metrics:
                    if metric in run.data.metrics:
                        run_data[f'metric_{metric}'] = run.data.metrics[metric]
                    else:
                        run_data[f'metric_{metric}'] = None
                
                # Agregar parámetros
                if params:
                    for param in params:
                        if param in run.data.params:
                            run_data[f'param_{param}'] = run.data.params[param]
                        else:
                            run_data[f'param_{param}'] = None
                
                runs_data.append(run_data)
            
            # Crear DataFrame
            df = pd.DataFrame(runs_data)
            
            self.mlflow_logger.info(f"Comparación de runs completada: {len(runs_data)} runs")
            
            return df
            
        except Exception as e:
            self.mlflow_logger.error(f"Error comparando runs: {e}")
            return pd.DataFrame()
    
    def get_best_run(
        self,
        metric_name: str,
        experiment_id: Optional[str] = None,
        ascending: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el mejor run basado en una métrica"""
        try:
            exp_id = experiment_id or self.experiment_id
            
            if exp_id is None:
                self.mlflow_logger.warning("No hay experimento configurado")
                return None
            
            # Obtener runs
            runs = self.client.search_runs(
                experiment_ids=[exp_id],
                max_results=1000
            )
            
            if not runs:
                self.mlflow_logger.warning("No hay runs disponibles")
                return None
            
            # Encontrar mejor run
            best_run = None
            best_value = None
            
            for run in runs:
                if metric_name in run.data.metrics:
                    value = run.data.metrics[metric_name]
                    
                    if best_value is None:
                        best_value = value
                        best_run = run
                    elif (ascending and value < best_value) or (not ascending and value > best_value):
                        best_value = value
                        best_run = run
            
            if best_run is None:
                self.mlflow_logger.warning(f"No se encontró run con métrica {metric_name}")
                return None
            
            # Convertir a diccionario
            best_run_data = {
                'run_id': best_run.info.run_id,
                'experiment_id': best_run.info.experiment_id,
                'status': best_run.info.status,
                'start_time': datetime.fromtimestamp(best_run.info.start_time / 1000),
                'end_time': datetime.fromtimestamp(best_run.info.end_time / 1000) if best_run.info.end_time else None,
                'duration_seconds': (best_run.info.end_time - best_run.info.start_time) / 1000 if best_run.info.end_time else None,
                'params': best_run.data.params,
                'metrics': best_run.data.metrics,
                'tags': best_run.data.tags,
                'best_metric_name': metric_name,
                'best_metric_value': best_value
            }
            
            self.mlflow_logger.info(f"Mejor run encontrado: {best_run.info.run_id} ({metric_name}: {best_value})")
            
            return best_run_data
            
        except Exception as e:
            self.mlflow_logger.error(f"Error obteniendo mejor run: {e}")
            return None
    
    def export_experiment_data(
        self,
        experiment_id: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> str:
        """Exporta datos del experimento"""
        try:
            exp_id = experiment_id or self.experiment_id
            
            if exp_id is None:
                self.mlflow_logger.warning("No hay experimento configurado")
                return None
            
            # Obtener runs
            runs = self.get_experiment_runs(exp_id, limit=1000)
            
            # Crear archivo de salida
            if output_file is None:
                output_file = f"experiment_{exp_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = self.mlflow_dir / output_file
            
            # Guardar datos
            with open(output_path, 'w') as f:
                json.dump(runs, f, indent=2, ensure_ascii=False, default=str)
            
            self.mlflow_logger.info(f"Datos del experimento exportados: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            self.mlflow_logger.error(f"Error exportando datos del experimento: {e}")
            return None
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del experimento"""
        try:
            if self.experiment_id is None:
                return {'error': 'No hay experimento configurado'}
            
            # Obtener información del experimento
            experiment = self.client.get_experiment(self.experiment_id)
            
            # Obtener runs
            runs = self.get_experiment_runs(limit=1000)
            
            # Calcular estadísticas
            total_runs = len(runs)
            completed_runs = len([r for r in runs if r['status'] == 'FINISHED'])
            failed_runs = len([r for r in runs if r['status'] == 'FAILED'])
            
            # Calcular duración promedio
            durations = [r['duration_seconds'] for r in runs if r['duration_seconds'] is not None]
            avg_duration = np.mean(durations) if durations else 0
            
            summary = {
                'experiment_id': self.experiment_id,
                'experiment_name': experiment.name,
                'total_runs': total_runs,
                'completed_runs': completed_runs,
                'failed_runs': failed_runs,
                'success_rate': completed_runs / total_runs if total_runs > 0 else 0,
                'avg_duration_seconds': avg_duration,
                'experiment_created': datetime.fromtimestamp(experiment.creation_time / 1000).isoformat(),
                'last_run': max([r['start_time'] for r in runs]) if runs else None
            }
            
            return summary
            
        except Exception as e:
            self.mlflow_logger.error(f"Error obteniendo resumen del experimento: {e}")
            return {'error': str(e)}

# Funciones de utilidad
def create_mlflow_integration(
    tracking_uri: str = "http://localhost:5000",
    experiment_name: str = "trading_bot_experiments",
    artifact_location: Optional[str] = None
) -> MLflowIntegration:
    """Factory function para crear MLflowIntegration"""
    return MLflowIntegration(tracking_uri, experiment_name, artifact_location)

def start_mlflow_tracking(
    run_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    description: Optional[str] = None
) -> MLflowIntegration:
    """Inicia tracking con MLflow"""
    integration = create_mlflow_integration()
    integration.start_run(run_name, tags, description)
    return integration
