# Ruta: core/ml/enterprise/callbacks.py
# callbacks.py - Callbacks personalizados para PyTorch Lightning
# Ubicación: C:\TradingBot_v10\models\enterprise\callbacks.py

"""
Callbacks personalizados para PyTorch Lightning.

Características:
- Monitoreo de gradientes
- Tracking de complejidad del modelo
- Validación de calidad de datos
- Métricas de trading especializadas
- Alertas automáticas
"""

import torch
import torch.nn as nn
import pytorch_lightning as pl
from pytorch_lightning.callbacks import Callback
from pytorch_lightning.utilities.types import STEP_OUTPUT
import numpy as np
import logging
from typing import Any, Dict, Optional, List
import matplotlib.pyplot as plt
from pathlib import Path
import json

# Importar ConfigLoader
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class GradientNormCallback(Callback):
    """Callback para monitorear normas de gradientes"""
    
    def __init__(self, log_every_n_steps: int = 100):
        super().__init__()
        self.log_every_n_steps = log_every_n_steps
        self.gradient_norms = []
        
    def on_before_optimizer_step(self, trainer, pl_module, optimizer, optimizer_idx):
        """Calcula y registra normas de gradientes"""
        if trainer.global_step % self.log_every_n_steps == 0:
            total_norm = 0
            param_count = 0
            
            for name, param in pl_module.named_parameters():
                if param.grad is not None:
                    param_norm = param.grad.data.norm(2)
                    total_norm += param_norm.item() ** 2
                    param_count += 1
                    
                    # Log gradientes por capa
                    pl_module.log(f"grad_norm/{name}", param_norm.item(), on_step=True)
            
            total_norm = total_norm ** (1. / 2)
            self.gradient_norms.append(total_norm)
            
            pl_module.log("grad_norm/total", total_norm, on_step=True)
            
            # Detectar gradientes explosivos
            if total_norm > 10.0:
                logger.warning(f"Gradientes explosivos detectados: {total_norm:.4f}")
                pl_module.log("grad_norm/explosive", 1.0, on_step=True)
            else:
                pl_module.log("grad_norm/explosive", 0.0, on_step=True)
            
            # Detectar gradientes que se desvanecen
            if total_norm < 1e-6:
                logger.warning(f"Gradientes que se desvanecen detectados: {total_norm:.4f}")
                pl_module.log("grad_norm/vanishing", 1.0, on_step=True)
            else:
                pl_module.log("grad_norm/vanishing", 0.0, on_step=True)

class ModelComplexityCallback(Callback):
    """Callback para monitorear complejidad del modelo"""
    
    def __init__(self):
        super().__init__()
        self.complexity_metrics = {}
        
    def on_train_start(self, trainer, pl_module):
        """Calcula métricas de complejidad al inicio del entrenamiento"""
        self.complexity_metrics = self._calculate_complexity_metrics(pl_module)
        
        # Log métricas de complejidad
        for metric, value in self.complexity_metrics.items():
            pl_module.log(f"model_complexity/{metric}", value, on_epoch=True)
            
        logger.info(f"Métricas de complejidad del modelo: {self.complexity_metrics}")
    
    def _calculate_complexity_metrics(self, model: nn.Module) -> Dict[str, float]:
        """Calcula métricas de complejidad del modelo"""
        metrics = {}
        
        # Contar parámetros
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        metrics['total_parameters'] = total_params
        metrics['trainable_parameters'] = trainable_params
        metrics['non_trainable_parameters'] = total_params - trainable_params
        
        # Calcular tamaño del modelo en MB
        param_size = sum(p.numel() * p.element_size() for p in model.parameters())
        buffer_size = sum(b.numel() * b.element_size() for b in model.buffers())
        model_size_mb = (param_size + buffer_size) / (1024 * 1024)
        
        metrics['model_size_mb'] = model_size_mb
        
        # Calcular profundidad del modelo
        def get_model_depth(module, depth=0):
            if not list(module.children()):
                return depth
            return max(get_model_depth(child, depth + 1) for child in module.children())
        
        metrics['model_depth'] = get_model_depth(model)
        
        # Calcular número de capas
        layers = [m for m in model.modules() if len(list(m.children())) == 0 and len(list(m.parameters())) > 0]
        metrics['num_layers'] = len(layers)
        
        return metrics

class DataQualityCallback(Callback):
    """Callback para validar calidad de datos"""
    
    def __init__(self, check_every_n_epochs: int = 10):
        super().__init__()
        self.check_every_n_epochs = check_every_n_epochs
        
    def on_validation_epoch_end(self, trainer, pl_module):
        """Valida calidad de datos cada N epochs"""
        if trainer.current_epoch % self.check_every_n_epochs == 0:
            self._check_data_quality(trainer, pl_module)
    
    def _check_data_quality(self, trainer, pl_module):
        """Verifica calidad de los datos de validación"""
        try:
            # Obtener un batch de validación
            val_dataloader = trainer.val_dataloaders[0]
            batch = next(iter(val_dataloader))
            x, y = batch
            
            # Verificar datos de entrada
            x_nan_count = torch.isnan(x).sum().item()
            x_inf_count = torch.isinf(x).sum().item()
            x_zero_count = (x == 0).sum().item()
            
            # Verificar targets
            y_nan_count = torch.isnan(y.float()).sum().item()
            y_unique = torch.unique(y).numel()
            
            # Log métricas de calidad
            pl_module.log("data_quality/x_nan_count", x_nan_count, on_epoch=True)
            pl_module.log("data_quality/x_inf_count", x_inf_count, on_epoch=True)
            pl_module.log("data_quality/x_zero_ratio", x_zero_count / x.numel(), on_epoch=True)
            pl_module.log("data_quality/y_nan_count", y_nan_count, on_epoch=True)
            pl_module.log("data_quality/y_unique_classes", y_unique, on_epoch=True)
            
            # Alertas de calidad
            if x_nan_count > 0:
                logger.warning(f"Datos con NaN encontrados: {x_nan_count}")
                pl_module.log("data_quality/nan_alert", 1.0, on_epoch=True)
            else:
                pl_module.log("data_quality/nan_alert", 0.0, on_epoch=True)
            
            if x_inf_count > 0:
                logger.warning(f"Datos con infinitos encontrados: {x_inf_count}")
                pl_module.log("data_quality/inf_alert", 1.0, on_epoch=True)
            else:
                pl_module.log("data_quality/inf_alert", 0.0, on_epoch=True)
            
            if y_unique < 2:
                logger.warning(f"Targets con menos de 2 clases: {y_unique}")
                pl_module.log("data_quality/class_imbalance_alert", 1.0, on_epoch=True)
            else:
                pl_module.log("data_quality/class_imbalance_alert", 0.0, on_epoch=True)
                
        except Exception as e:
            logger.error(f"Error verificando calidad de datos: {e}")

class TradingMetricsCallback(Callback):
    """Callback para métricas específicas de trading"""
    
    def __init__(self):
        super().__init__()
        self.predictions = []
        self.targets = []
        
    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        """Recolecta predicciones y targets para métricas de trading"""
        if outputs is not None:
            if isinstance(outputs, dict):
                preds = outputs.get('logits', outputs.get('predictions'))
                targets = batch[1] if isinstance(batch, (list, tuple)) else batch['target']
            else:
                preds = outputs
                targets = batch[1] if isinstance(batch, (list, tuple)) else batch['target']
            
            if preds is not None and targets is not None:
                self.predictions.append(preds.detach().cpu())
                self.targets.append(targets.detach().cpu())
    
    def on_validation_epoch_end(self, trainer, pl_module):
        """Calcula métricas de trading al final de la validación"""
        if not self.predictions or not self.targets:
            return
        
        try:
            # Concatenar todas las predicciones y targets
            all_preds = torch.cat(self.predictions, dim=0)
            all_targets = torch.cat(self.targets, dim=0)
            
            # Convertir predicciones a clases
            pred_classes = torch.argmax(all_preds, dim=1)
            
            # Calcular métricas de trading
            metrics = self._calculate_trading_metrics(all_preds, all_targets, pred_classes)
            
            # Log métricas
            for metric_name, value in metrics.items():
                pl_module.log(f"trading/{metric_name}", value, on_epoch=True)
            
            # Limpiar listas para el siguiente epoch
            self.predictions.clear()
            self.targets.clear()
            
        except Exception as e:
            logger.error(f"Error calculando métricas de trading: {e}")
    
    def _calculate_trading_metrics(self, preds, targets, pred_classes):
        """Calcula métricas específicas de trading"""
        metrics = {}
        
        # Accuracy por clase
        for class_id in range(3):  # 0=SELL, 1=HOLD, 2=BUY
            class_mask = targets == class_id
            if class_mask.sum() > 0:
                class_accuracy = (pred_classes[class_mask] == targets[class_mask]).float().mean()
                class_names = ['SELL', 'HOLD', 'BUY']
                metrics[f'accuracy_{class_names[class_id].lower()}'] = class_accuracy.item()
        
        # Distribución de predicciones
        pred_dist = torch.bincount(pred_classes, minlength=3).float() / len(pred_classes)
        for i, class_name in enumerate(['SELL', 'HOLD', 'BUY']):
            metrics[f'pred_distribution_{class_name.lower()}'] = pred_dist[i].item()
        
        # Distribución de targets
        target_dist = torch.bincount(targets, minlength=3).float() / len(targets)
        for i, class_name in enumerate(['SELL', 'HOLD', 'BUY']):
            metrics[f'target_distribution_{class_name.lower()}'] = target_dist[i].item()
        
        # Confianza promedio
        confidence = torch.max(torch.softmax(preds, dim=1), dim=1)[0].mean()
        metrics['average_confidence'] = confidence.item()
        
        # Entropía promedio
        probs = torch.softmax(preds, dim=1)
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1).mean()
        metrics['average_entropy'] = entropy.item()
        
        return metrics

class LearningRateSchedulerCallback(Callback):
    """Callback personalizado para scheduling de learning rate"""
    
    def __init__(self, monitor: str = "val_loss", mode: str = "min", factor: float = 0.5, patience: int = 10):
        super().__init__()
        self.monitor = monitor
        self.mode = mode
        self.factor = factor
        self.patience = patience
        self.wait = 0
        self.best = float('inf') if mode == 'min' else float('-inf')
        
    def on_validation_epoch_end(self, trainer, pl_module):
        """Ajusta learning rate basado en métricas de validación"""
        current = trainer.callback_metrics.get(self.monitor)
        if current is None:
            return
        
        if self.mode == 'min':
            is_better = current < self.best
        else:
            is_better = current > self.best
        
        if is_better:
            self.best = current
            self.wait = 0
        else:
            self.wait += 1
            
        if self.wait >= self.patience:
            # Reducir learning rate
            for optimizer in trainer.optimizers:
                for param_group in optimizer.param_groups:
                    old_lr = param_group['lr']
                    new_lr = old_lr * self.factor
                    param_group['lr'] = new_lr
                    
                    pl_module.log("learning_rate", new_lr, on_epoch=True)
                    logger.info(f"Learning rate reducido: {old_lr:.6f} -> {new_lr:.6f}")
            
            self.wait = 0

class ModelCheckpointCallback(Callback):
    """Callback personalizado para guardar checkpoints con métricas adicionales"""
    
    def __init__(self, save_dir: str = "checkpoints", save_top_k: int = 3):
        super().__init__()
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.save_top_k = save_top_k
        self.checkpoints = []
        
    def on_validation_epoch_end(self, trainer, pl_module):
        """Guarda checkpoint con métricas adicionales"""
        try:
            # Obtener métricas actuales
            metrics = trainer.callback_metrics
            
            # Crear información del checkpoint
            checkpoint_info = {
                'epoch': trainer.current_epoch,
                'global_step': trainer.global_step,
                'val_loss': metrics.get('val_loss', float('inf')),
                'val_accuracy': metrics.get('val_accuracy', 0.0),
                'timestamp': trainer.logger.experiment.start_time if hasattr(trainer.logger, 'experiment') else None
            }
            
            # Guardar checkpoint
            checkpoint_path = self.save_dir / f"checkpoint_epoch_{trainer.current_epoch:03d}.pth"
            torch.save({
                'model_state_dict': pl_module.state_dict(),
                'optimizer_state_dict': trainer.optimizers[0].state_dict(),
                'epoch': trainer.current_epoch,
                'metrics': checkpoint_info
            }, checkpoint_path)
            
            # Mantener solo los mejores checkpoints
            self.checkpoints.append((checkpoint_path, checkpoint_info['val_loss']))
            self.checkpoints.sort(key=lambda x: x[1])
            
            if len(self.checkpoints) > self.save_top_k:
                # Eliminar el peor checkpoint
                worst_checkpoint = self.checkpoints.pop()
                worst_checkpoint[0].unlink()
            
            logger.info(f"Checkpoint guardado: {checkpoint_path}")
            
        except Exception as e:
            logger.error(f"Error guardando checkpoint: {e}")

class EnterpriseCallbacks:
    """Clase de conveniencia para crear todos los callbacks enterprise"""
    
    @staticmethod
    def get_all_callbacks(config: Dict[str, Any]) -> List[Callback]:
        """Obtiene todos los callbacks enterprise configurados"""
        callbacks = []
        
        # Callbacks básicos
        callbacks.append(GradientNormCallback(
            log_every_n_steps=config.get('gradient_norm', {}).get('log_every_n_steps', 100)
        ))
        
        callbacks.append(ModelComplexityCallback())
        
        callbacks.append(DataQualityCallback(
            check_every_n_epochs=config.get('data_quality', {}).get('check_every_n_epochs', 10)
        ))
        
        callbacks.append(TradingMetricsCallback())
        
        # Learning rate scheduler personalizado
        if config.get('lr_scheduler', {}).get('enabled', True):
            callbacks.append(LearningRateSchedulerCallback(
                monitor=config.get('lr_scheduler', {}).get('monitor', 'val_loss'),
                mode=config.get('lr_scheduler', {}).get('mode', 'min'),
                factor=config.get('lr_scheduler', {}).get('factor', 0.5),
                patience=config.get('lr_scheduler', {}).get('patience', 10)
            ))
        
        # Checkpoint personalizado
        if config.get('checkpoint', {}).get('enabled', True):
            callbacks.append(ModelCheckpointCallback(
                save_dir=config.get('checkpoint', {}).get('save_dir', 'checkpoints'),
                save_top_k=config.get('checkpoint', {}).get('save_top_k', 3)
            ))
        
        return callbacks
