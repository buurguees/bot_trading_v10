# distributed_trainer.py - Entrenador distribuido enterprise
# Ubicación: C:\TradingBot_v10\models\enterprise\distributed_trainer.py

"""
Entrenador distribuido enterprise para PyTorch Lightning.

Características:
- Soporte para múltiples GPUs
- Estrategias DDP y DeepSpeed
- Balanceado de carga
- Sincronización de métricas
- Recovery automático
"""

import torch
import pytorch_lightning as pl
from pytorch_lightning import Trainer
from pytorch_lightning.strategies import DDPStrategy, DeepSpeedStrategy
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import MLFlowLogger
import logging
from typing import Dict, List, Optional, Any, Union
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class DistributedTrainer:
    """Entrenador distribuido enterprise"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el entrenador distribuido
        
        Args:
            config: Configuración de entrenamiento distribuido
        """
        self.config = config
        self.strategy = None
        self.trainer = None
        
        # Configurar estrategia
        self._setup_strategy()
        
    def _setup_strategy(self):
        """Configura la estrategia de entrenamiento distribuido"""
        strategy_name = self.config.get('strategy', 'ddp')
        
        if strategy_name == 'ddp':
            self.strategy = DDPStrategy(
                find_unused_parameters=self.config.get('ddp', {}).get('find_unused_parameters', False),
                gradient_as_bucket_view=self.config.get('ddp', {}).get('gradient_as_bucket_view', True),
                static_graph=self.config.get('ddp', {}).get('static_graph', True)
            )
        elif strategy_name == 'deepspeed':
            deepspeed_config = self.config.get('deepspeed', {})
            self.strategy = DeepSpeedStrategy(
                stage=deepspeed_config.get('stage', 2),
                offload_optimizer=deepspeed_config.get('offload_optimizer', False),
                offload_parameters=deepspeed_config.get('offload_parameters', False)
            )
        else:
            logger.warning(f"Estrategia no soportada: {strategy_name}, usando DDP")
            self.strategy = DDPStrategy()
    
    def create_trainer(
        self,
        model: pl.LightningModule,
        data_module: pl.LightningDataModule,
        callbacks: Optional[List] = None,
        logger: Optional[pl.loggers.Logger] = None,
        **kwargs
    ) -> Trainer:
        """
        Crea un trainer distribuido
        
        Args:
            model: Modelo PyTorch Lightning
            data_module: DataModule
            callbacks: Lista de callbacks
            logger: Logger para experimentos
            **kwargs: Argumentos adicionales para Trainer
            
        Returns:
            Trainer configurado
        """
        # Configuración de recursos
        devices = self.config.get('resources', {}).get('devices', 'auto')
        accelerator = self.config.get('resources', {}).get('accelerator', 'auto')
        precision = self.config.get('resources', {}).get('precision', '16-mixed')
        
        # Configuración de entrenamiento
        max_epochs = kwargs.get('max_epochs', 1000)
        max_time = kwargs.get('max_time', None)
        
        # Callbacks por defecto
        if callbacks is None:
            callbacks = self._get_default_callbacks()
        
        # Logger por defecto
        if logger is None and self.config.get('mlflow', {}).get('enabled', False):
            logger = MLFlowLogger(
                experiment_name=self.config['mlflow']['experiment_name'],
                tracking_uri=self.config['mlflow']['tracking_uri']
            )
        
        # Crear trainer
        self.trainer = Trainer(
            strategy=self.strategy,
            devices=devices,
            accelerator=accelerator,
            precision=precision,
            max_epochs=max_epochs,
            max_time=max_time,
            callbacks=callbacks,
            logger=logger,
            enable_checkpointing=True,
            enable_progress_bar=True,
            enable_model_summary=True,
            log_every_n_steps=50,
            **kwargs
        )
        
        return self.trainer
    
    def _get_default_callbacks(self) -> List:
        """Obtiene callbacks por defecto"""
        callbacks = []
        
        # Model checkpoint
        if self.config.get('checkpoints', {}).get('enabled', True):
            checkpoint_config = self.config['checkpoints']
            callbacks.append(ModelCheckpoint(
                dirpath=checkpoint_config.get('paths', {}).get('base_dir', 'checkpoints'),
                filename=checkpoint_config.get('paths', {}).get('filename', '{epoch:02d}-{val_loss:.4f}'),
                monitor=checkpoint_config.get('save_frequency', {}).get('monitor', 'val_loss'),
                mode=checkpoint_config.get('save_frequency', {}).get('mode', 'min'),
                save_top_k=checkpoint_config.get('save_frequency', {}).get('save_top_k', 3),
                save_last=True
            ))
        
        # Early stopping
        if self.config.get('callbacks', {}).get('early_stopping', {}).get('enabled', True):
            early_stop_config = self.config['callbacks']['early_stopping']
            callbacks.append(EarlyStopping(
                monitor=early_stop_config.get('monitor', 'val_loss'),
                patience=early_stop_config.get('patience', 50),
                mode=early_stop_config.get('mode', 'min'),
                min_delta=early_stop_config.get('min_delta', 0.001)
            ))
        
        return callbacks
    
    def train(self, model: pl.LightningModule, data_module: pl.LightningDataModule) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento distribuido
        
        Args:
            model: Modelo a entrenar
            data_module: DataModule con datos
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            logger.info("🚀 Iniciando entrenamiento distribuido")
            
            # Crear trainer si no existe
            if self.trainer is None:
                self.create_trainer(model, data_module)
            
            # Entrenar
            self.trainer.fit(model, data_module)
            
            # Evaluar
            test_results = self.trainer.test(model, data_module)
            
            # Obtener métricas finales
            results = {
                'trainer_state': {
                    'current_epoch': self.trainer.current_epoch,
                    'global_step': self.trainer.global_step,
                    'best_model_path': self.trainer.checkpoint_callback.best_model_path if self.trainer.checkpoint_callback else None
                },
                'test_results': test_results[0] if test_results else {},
                'strategy': str(self.strategy),
                'devices': self.trainer.num_devices,
                'nodes': self.trainer.num_nodes
            }
            
            logger.info("✅ Entrenamiento distribuido completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento distribuido: {e}")
            raise
    
    def get_rank(self) -> int:
        """Obtiene el rank del proceso actual"""
        if hasattr(self.trainer, 'global_rank'):
            return self.trainer.global_rank
        return 0
    
    def get_world_size(self) -> int:
        """Obtiene el tamaño del mundo (número total de procesos)"""
        if hasattr(self.trainer, 'world_size'):
            return self.trainer.world_size
        return 1
    
    def is_main_process(self) -> bool:
        """Verifica si es el proceso principal"""
        return self.get_rank() == 0
    
    def synchronize(self):
        """Sincroniza todos los procesos"""
        if torch.distributed.is_initialized():
            torch.distributed.barrier()
    
    def cleanup(self):
        """Limpia recursos del entrenador distribuido"""
        if self.trainer:
            self.trainer.should_stop = True

class MultiNodeTrainer(DistributedTrainer):
    """Entrenador para múltiples nodos"""
    
    def __init__(self, config: Dict[str, Any], node_rank: int = 0, master_addr: str = "localhost", master_port: int = 12355):
        """
        Inicializa entrenador multi-nodo
        
        Args:
            config: Configuración de entrenamiento
            node_rank: Rank del nodo actual
            master_addr: Dirección del nodo maestro
            master_port: Puerto del nodo maestro
        """
        super().__init__(config)
        
        self.node_rank = node_rank
        self.master_addr = master_addr
        self.master_port = master_port
        
        # Configurar variables de entorno para multi-nodo
        os.environ['MASTER_ADDR'] = master_addr
        os.environ['MASTER_PORT'] = str(master_port)
        os.environ['NODE_RANK'] = str(node_rank)
    
    def create_trainer(self, model: pl.LightningModule, data_module: pl.LightningDataModule, 
                      callbacks: Optional[List] = None, logger: Optional[pl.loggers.Logger] = None, **kwargs) -> Trainer:
        """Crea trainer para multi-nodo"""
        # Configuración específica para multi-nodo
        kwargs.update({
            'num_nodes': self.config.get('resources', {}).get('num_nodes', 1),
            'strategy': self.strategy
        })
        
        return super().create_trainer(model, data_module, callbacks, logger, **kwargs)

class DeepSpeedTrainer(DistributedTrainer):
    """Entrenador especializado para DeepSpeed"""
    
    def __init__(self, config: Dict[str, Any], deepspeed_config_path: Optional[str] = None):
        """
        Inicializa entrenador DeepSpeed
        
        Args:
            config: Configuración de entrenamiento
            deepspeed_config_path: Ruta al archivo de configuración DeepSpeed
        """
        super().__init__(config)
        
        self.deepspeed_config_path = deepspeed_config_path
        self._setup_deepspeed_config()
    
    def _setup_deepspeed_config(self):
        """Configura DeepSpeed"""
        if self.deepspeed_config_path and Path(self.deepspeed_config_path).exists():
            # Usar configuración externa
            self.strategy = DeepSpeedStrategy(config=self.deepspeed_config_path)
        else:
            # Usar configuración por defecto
            deepspeed_config = self.config.get('deepspeed', {})
            self.strategy = DeepSpeedStrategy(
                stage=deepspeed_config.get('stage', 2),
                offload_optimizer=deepspeed_config.get('offload_optimizer', False),
                offload_parameters=deepspeed_config.get('offload_parameters', False)
            )
    
    def create_trainer(self, model: pl.LightningModule, data_module: pl.LightningDataModule, 
                      callbacks: Optional[List] = None, logger: Optional[pl.loggers.Logger] = None, **kwargs) -> Trainer:
        """Crea trainer DeepSpeed"""
        # Configuración específica para DeepSpeed
        kwargs.update({
            'strategy': self.strategy,
            'precision': '16-mixed',  # DeepSpeed funciona mejor con mixed precision
        })
        
        return super().create_trainer(model, data_module, callbacks, logger, **kwargs)

# Funciones de utilidad
def create_distributed_trainer(config: Dict[str, Any], trainer_type: str = "ddp") -> DistributedTrainer:
    """
    Factory function para crear entrenadores distribuidos
    
    Args:
        config: Configuración de entrenamiento
        trainer_type: Tipo de trainer (ddp, deepspeed, multi_node)
        
    Returns:
        Entrenador distribuido
    """
    if trainer_type == "ddp":
        return DistributedTrainer(config)
    elif trainer_type == "deepspeed":
        return DeepSpeedTrainer(config)
    elif trainer_type == "multi_node":
        return MultiNodeTrainer(config)
    else:
        raise ValueError(f"Tipo de trainer no soportado: {trainer_type}")

def setup_distributed_environment():
    """Configura el entorno distribuido"""
    # Verificar si CUDA está disponible
    if not torch.cuda.is_available():
        logger.warning("CUDA no disponible, usando CPU")
        return
    
    # Configurar variables de entorno por defecto
    if 'MASTER_ADDR' not in os.environ:
        os.environ['MASTER_ADDR'] = 'localhost'
    if 'MASTER_PORT' not in os.environ:
        os.environ['MASTER_PORT'] = '12355'
    
    logger.info(f"Entorno distribuido configurado: {os.environ.get('MASTER_ADDR')}:{os.environ.get('MASTER_PORT')}")

def get_optimal_batch_size(model: pl.LightningModule, data_module: pl.LightningDataModule, 
                          max_batch_size: int = 1024) -> int:
    """
    Encuentra el tamaño de batch óptimo para el modelo
    
    Args:
        model: Modelo a probar
        data_module: DataModule con datos
        max_batch_size: Tamaño máximo de batch a probar
        
    Returns:
        Tamaño de batch óptimo
    """
    device = next(model.parameters()).device
    
    # Probar diferentes tamaños de batch
    batch_sizes = [16, 32, 64, 128, 256, 512, 1024]
    batch_sizes = [bs for bs in batch_sizes if bs <= max_batch_size]
    
    optimal_batch_size = 16
    
    for batch_size in batch_sizes:
        try:
            # Crear batch de prueba
            sample_batch = next(iter(data_module.train_dataloader()))
            x, y = sample_batch
            
            # Expandir batch si es necesario
            if x.size(0) < batch_size:
                repeat_factor = (batch_size // x.size(0)) + 1
                x = x.repeat(repeat_factor, 1, 1)[:batch_size]
                y = y.repeat(repeat_factor)[:batch_size]
            
            # Probar forward pass
            with torch.no_grad():
                _ = model(x.to(device))
            
            optimal_batch_size = batch_size
            logger.info(f"Batch size {batch_size} funciona correctamente")
            
        except RuntimeError as e:
            if "out of memory" in str(e):
                logger.info(f"Batch size {batch_size} excede la memoria disponible")
                break
            else:
                raise e
    
    logger.info(f"Tamaño de batch óptimo: {optimal_batch_size}")
    return optimal_batch_size
