# Ruta: core/ml/enterprise/metrics_tracker.py
# metrics_tracker.py - Tracker de métricas enterprise
# Ubicación: C:\TradingBot_v10\models\enterprise\metrics_tracker.py

"""
Tracker de métricas enterprise para PyTorch Lightning.

Características:
- Métricas de trading especializadas
- Integración con Prometheus
- Logging estructurado
- Visualización de métricas
- Exportación de datos
"""

import torch
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Importar ConfigLoader
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class TradingMetrics:
    """Clase para calcular métricas específicas de trading"""
    
    @staticmethod
    def calculate_accuracy_by_class(predictions: torch.Tensor, targets: torch.Tensor) -> Dict[str, float]:
        """Calcula accuracy por clase"""
        pred_classes = torch.argmax(predictions, dim=1)
        class_names = ['SELL', 'HOLD', 'BUY']
        accuracies = {}
        
        for class_id, class_name in enumerate(class_names):
            class_mask = targets == class_id
            if class_mask.sum() > 0:
                class_accuracy = (pred_classes[class_mask] == targets[class_mask]).float().mean()
                accuracies[f'accuracy_{class_name.lower()}'] = class_accuracy.item()
            else:
                accuracies[f'accuracy_{class_name.lower()}'] = 0.0
        
        return accuracies
    
    @staticmethod
    def calculate_class_distribution(predictions: torch.Tensor, targets: torch.Tensor) -> Dict[str, float]:
        """Calcula distribución de clases en predicciones y targets"""
        pred_classes = torch.argmax(predictions, dim=1)
        class_names = ['SELL', 'HOLD', 'BUY']
        
        # Distribución de predicciones
        pred_dist = torch.bincount(pred_classes, minlength=3).float() / len(pred_classes)
        pred_distribution = {}
        for i, class_name in enumerate(class_names):
            pred_distribution[f'pred_dist_{class_name.lower()}'] = pred_dist[i].item()
        
        # Distribución de targets
        target_dist = torch.bincount(targets, minlength=3).float() / len(targets)
        target_distribution = {}
        for i, class_name in enumerate(class_names):
            target_distribution[f'target_dist_{class_name.lower()}'] = target_dist[i].item()
        
        return {**pred_distribution, **target_distribution}
    
    @staticmethod
    def calculate_confidence_metrics(predictions: torch.Tensor) -> Dict[str, float]:
        """Calcula métricas de confianza"""
        probs = torch.softmax(predictions, dim=1)
        
        # Confianza promedio
        confidence = torch.max(probs, dim=1)[0].mean()
        
        # Entropía promedio
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1).mean()
        
        # Varianza de confianza
        confidence_var = torch.var(torch.max(probs, dim=1)[0])
        
        return {
            'average_confidence': confidence.item(),
            'average_entropy': entropy.item(),
            'confidence_variance': confidence_var.item()
        }
    
    @staticmethod
    def calculate_trading_performance(predictions: torch.Tensor, targets: torch.Tensor, 
                                    returns: Optional[torch.Tensor] = None) -> Dict[str, float]:
        """Calcula métricas de rendimiento de trading"""
        pred_classes = torch.argmax(predictions, dim=1)
        
        # Accuracy general
        accuracy = (pred_classes == targets).float().mean()
        
        # Precision, Recall, F1 por clase
        class_names = ['SELL', 'HOLD', 'BUY']
        metrics = {'overall_accuracy': accuracy.item()}
        
        for class_id, class_name in enumerate(class_names):
            # True positives, false positives, false negatives
            tp = ((pred_classes == class_id) & (targets == class_id)).sum().float()
            fp = ((pred_classes == class_id) & (targets != class_id)).sum().float()
            fn = ((pred_classes != class_id) & (targets == class_id)).sum().float()
            
            # Precision
            precision = tp / (tp + fp + 1e-8)
            metrics[f'precision_{class_name.lower()}'] = precision.item()
            
            # Recall
            recall = tp / (tp + fn + 1e-8)
            metrics[f'recall_{class_name.lower()}'] = recall.item()
            
            # F1 Score
            f1 = 2 * (precision * recall) / (precision + recall + 1e-8)
            metrics[f'f1_{class_name.lower()}'] = f1.item()
        
        # F1 macro promedio
        f1_scores = [metrics[f'f1_{name.lower()}'] for name in class_names]
        metrics['f1_macro'] = np.mean(f1_scores)
        
        # Si hay retornos, calcular métricas financieras
        if returns is not None:
            financial_metrics = TradingMetrics._calculate_financial_metrics(
                pred_classes, targets, returns
            )
            metrics.update(financial_metrics)
        
        return metrics
    
    @staticmethod
    def _calculate_financial_metrics(pred_classes: torch.Tensor, targets: torch.Tensor, 
                                   returns: torch.Tensor) -> Dict[str, float]:
        """Calcula métricas financieras"""
        # Simular trades basados en predicciones
        # 0=SELL, 1=HOLD, 2=BUY
        trade_signals = pred_classes - 1  # -1, 0, 1
        trade_returns = trade_signals.float() * returns
        
        # Métricas básicas
        total_return = trade_returns.sum().item()
        win_rate = (trade_returns > 0).float().mean().item()
        avg_win = trade_returns[trade_returns > 0].mean().item() if (trade_returns > 0).sum() > 0 else 0
        avg_loss = trade_returns[trade_returns < 0].mean().item() if (trade_returns < 0).sum() > 0 else 0
        
        # Sharpe ratio (simplificado)
        sharpe_ratio = trade_returns.mean().item() / (trade_returns.std().item() + 1e-8)
        
        # Profit factor
        gross_profit = trade_returns[trade_returns > 0].sum().item()
        gross_loss = abs(trade_returns[trade_returns < 0].sum().item())
        profit_factor = gross_profit / (gross_loss + 1e-8)
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor
        }

class MetricsTracker:
    """Tracker principal de métricas enterprise"""
    
    def __init__(self, save_dir: str = "metrics"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # Almacenamiento de métricas
        self.metrics_history = []
        self.current_epoch_metrics = {}
        
        # Configuración de logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def log_epoch_metrics(self, epoch: int, metrics: Dict[str, float], phase: str = "train"):
        """Registra métricas de un epoch"""
        epoch_data = {
            'epoch': epoch,
            'phase': phase,
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
        
        self.metrics_history.append(epoch_data)
        self.current_epoch_metrics = epoch_data
        
        # Log a archivo
        self._log_to_file(epoch_data)
        
    def log_batch_metrics(self, batch_idx: int, metrics: Dict[str, float], phase: str = "train"):
        """Registra métricas de un batch"""
        batch_data = {
            'batch_idx': batch_idx,
            'phase': phase,
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
        
        # Log a archivo
        self._log_to_file(batch_data)
        
    def calculate_trading_metrics(self, predictions: torch.Tensor, targets: torch.Tensor, 
                                returns: Optional[torch.Tensor] = None) -> Dict[str, float]:
        """Calcula métricas de trading completas"""
        metrics = {}
        
        # Métricas básicas
        metrics.update(TradingMetrics.calculate_accuracy_by_class(predictions, targets))
        metrics.update(TradingMetrics.calculate_class_distribution(predictions, targets))
        metrics.update(TradingMetrics.calculate_confidence_metrics(predictions))
        metrics.update(TradingMetrics.calculate_trading_performance(predictions, targets, returns))
        
        return metrics
    
    def _log_to_file(self, data: Dict[str, Any]):
        """Log métricas a archivo JSON"""
        try:
            log_file = self.save_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Error escribiendo métricas a archivo: {e}")
    
    def get_metrics_summary(self, last_n_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        if not self.metrics_history:
            return {}
        
        # Filtrar por epochs si se especifica
        if last_n_epochs:
            recent_metrics = self.metrics_history[-last_n_epochs:]
        else:
            recent_metrics = self.metrics_history
        
        # Convertir a DataFrame para análisis
        df = pd.DataFrame(recent_metrics)
        
        summary = {
            'total_epochs': len(df),
            'latest_epoch': df['epoch'].max() if 'epoch' in df.columns else 0,
            'metrics_count': len(df)
        }
        
        # Calcular estadísticas para métricas numéricas
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col not in ['epoch', 'batch_idx']:
                summary[f'{col}_mean'] = df[col].mean()
                summary[f'{col}_std'] = df[col].std()
                summary[f'{col}_min'] = df[col].min()
                summary[f'{col}_max'] = df[col].max()
        
        return summary
    
    def plot_metrics(self, metrics: List[str], save_path: Optional[str] = None, 
                    phase: str = "train") -> None:
        """Genera gráficos de métricas"""
        if not self.metrics_history:
            self.logger.warning("No hay métricas para graficar")
            return
        
        # Filtrar por fase
        df = pd.DataFrame(self.metrics_history)
        if 'phase' in df.columns:
            df = df[df['phase'] == phase]
        
        if df.empty:
            self.logger.warning(f"No hay métricas para la fase {phase}")
            return
        
        # Crear subplots
        n_metrics = len(metrics)
        n_cols = min(3, n_metrics)
        n_rows = (n_metrics + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        if n_metrics == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for i, metric in enumerate(metrics):
            if metric not in df.columns:
                self.logger.warning(f"Métrica {metric} no encontrada")
                continue
            
            row = i // n_cols
            col = i % n_cols
            
            if n_rows == 1:
                ax = axes[col]
            else:
                ax = axes[row, col]
            
            # Plotear métrica
            if 'epoch' in df.columns:
                ax.plot(df['epoch'], df[metric], label=metric)
                ax.set_xlabel('Epoch')
            else:
                ax.plot(df[metric], label=metric)
                ax.set_xlabel('Batch')
            
            ax.set_ylabel(metric)
            ax.set_title(f'{metric} - {phase}')
            ax.grid(True, alpha=0.3)
            ax.legend()
        
        # Ocultar subplots vacíos
        for i in range(n_metrics, n_rows * n_cols):
            row = i // n_cols
            col = i % n_cols
            if n_rows == 1:
                axes[col].set_visible(False)
            else:
                axes[row, col].set_visible(False)
        
        plt.tight_layout()
        
        # Guardar o mostrar
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Gráfico guardado en {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_confusion_matrix(self, predictions: torch.Tensor, targets: torch.Tensor, 
                            save_path: Optional[str] = None) -> None:
        """Genera matriz de confusión"""
        from sklearn.metrics import confusion_matrix
        import seaborn as sns
        
        pred_classes = torch.argmax(predictions, dim=1)
        cm = confusion_matrix(targets.cpu().numpy(), pred_classes.cpu().numpy())
        
        class_names = ['SELL', 'HOLD', 'BUY']
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=class_names, yticklabels=class_names)
        plt.title('Matriz de Confusión')
        plt.xlabel('Predicción')
        plt.ylabel('Target Real')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Matriz de confusión guardada en {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def export_metrics(self, filepath: str, format: str = "csv") -> None:
        """Exporta métricas a archivo"""
        if not self.metrics_history:
            self.logger.warning("No hay métricas para exportar")
            return
        
        df = pd.DataFrame(self.metrics_history)
        
        if format.lower() == "csv":
            df.to_csv(filepath, index=False)
        elif format.lower() == "json":
            df.to_json(filepath, orient='records', indent=2)
        elif format.lower() == "excel":
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Formato no soportado: {format}")
        
        self.logger.info(f"Métricas exportadas a {filepath}")
    
    def clear_history(self):
        """Limpia el historial de métricas"""
        self.metrics_history.clear()
        self.current_epoch_metrics = {}
        self.logger.info("Historial de métricas limpiado")
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas más recientes"""
        return self.current_epoch_metrics.copy() if self.current_epoch_metrics else {}
    
    def get_metrics_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Obtiene métricas filtradas por fase"""
        return [m for m in self.metrics_history if m.get('phase') == phase]
    
    def get_metric_trend(self, metric_name: str, phase: str = "train") -> List[float]:
        """Obtiene tendencia de una métrica específica"""
        phase_metrics = self.get_metrics_by_phase(phase)
        return [m.get(metric_name, 0) for m in phase_metrics if metric_name in m]

# Funciones de utilidad
def create_metrics_tracker(save_dir: str = "metrics") -> MetricsTracker:
    """Factory function para crear MetricsTracker"""
    return MetricsTracker(save_dir)

def calculate_model_performance(predictions: torch.Tensor, targets: torch.Tensor, 
                              returns: Optional[torch.Tensor] = None) -> Dict[str, float]:
    """Función de conveniencia para calcular rendimiento del modelo"""
    tracker = MetricsTracker()
    return tracker.calculate_trading_metrics(predictions, targets, returns)
