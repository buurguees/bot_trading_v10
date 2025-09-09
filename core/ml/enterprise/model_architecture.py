# model_architecture.py - Arquitecturas de modelos enterprise
# Ubicación: C:\TradingBot_v10\models\enterprise\model_architecture.py

"""
Arquitecturas de modelos enterprise para Trading Bot v10.

Características:
- LSTM con mecanismo de atención
- Transformer para series temporales
- CNN-LSTM híbrido
- GRU simple
- Modelo ensemble
- Integración con PyTorch Lightning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import pytorch_lightning as pl
from typing import Dict, List, Optional, Any, Tuple
import math
import yaml
from pathlib import Path

class MultiHeadAttention(nn.Module):
    """Mecanismo de atención multi-cabeza para series temporales"""
    
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = math.sqrt(self.d_k)
        
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size, seq_len, d_model = x.size()
        
        # Proyecciones Q, K, V
        Q = self.w_q(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        K = self.w_k(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        V = self.w_v(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        
        # Calcular atención
        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
            
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # Aplicar atención a V
        context = torch.matmul(attention_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, d_model)
        
        # Proyección final
        output = self.w_o(context)
        
        return output, attention_weights

class PositionalEncoding(nn.Module):
    """Codificación posicional para Transformer"""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)

class LSTMAttentionModel(pl.LightningModule):
    """Modelo LSTM con mecanismo de atención"""
    
    def __init__(
        self,
        input_size: int = 50,
        hidden_size: int = 256,
        num_layers: int = 3,
        dropout: float = 0.2,
        attention_heads: int = 8,
        num_classes: int = 3,
        learning_rate: float = 0.001,
        class_weights: Optional[List[float]] = None,
        label_smoothing: float = 0.1
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        
        # Capas LSTM
        self.lstm_layers = nn.ModuleList([
            nn.LSTM(
                input_size if i == 0 else hidden_size,
                hidden_size,
                num_layers=1,
                batch_first=True,
                dropout=dropout if i < num_layers - 1 else 0
            ) for i in range(num_layers)
        ])
        
        # Mecanismo de atención
        self.attention = MultiHeadAttention(
            d_model=hidden_size,
            num_heads=attention_heads,
            dropout=dropout
        )
        
        # Capas densas
        self.dense_layers = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # Capa de salida
        self.output_layer = nn.Linear(16, num_classes)
        
        # Loss function
        if class_weights is not None:
            class_weights = torch.tensor(class_weights, dtype=torch.float32)
        self.criterion = nn.CrossEntropyLoss(
            weight=class_weights,
            label_smoothing=label_smoothing
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Pasar por capas LSTM
        for lstm in self.lstm_layers:
            x, _ = lstm(x)
        
        # Aplicar atención
        attended_output, attention_weights = self.attention(x)
        
        # Global average pooling
        pooled = torch.mean(attended_output, dim=1)
        
        # Capas densas
        features = self.dense_layers(pooled)
        
        # Salida
        output = self.output_layer(features)
        
        return output, attention_weights
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits, _ = self(x)
        loss = self.criterion(logits, y)
        
        # Logging
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits, _ = self(x)
        loss = self.criterion(logits, y)
        
        # Métricas
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        # Logging
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits, _ = self(x)
        loss = self.criterion(logits, y)
        
        # Métricas
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        # Logging
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_accuracy', accuracy, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=0.01
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=self.trainer.max_epochs
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss"
            }
        }

class TransformerModel(pl.LightningModule):
    """Modelo Transformer para series temporales"""
    
    def __init__(
        self,
        input_size: int = 50,
        d_model: int = 256,
        nhead: int = 8,
        num_encoder_layers: int = 6,
        dim_feedforward: int = 1024,
        dropout: float = 0.1,
        num_classes: int = 3,
        learning_rate: float = 0.001,
        warmup_steps: int = 4000
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.d_model = d_model
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        self.warmup_steps = warmup_steps
        
        # Proyección de entrada
        self.input_projection = nn.Linear(input_size, d_model)
        
        # Codificación posicional
        self.pos_encoding = PositionalEncoding(d_model, dropout=dropout)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_encoder_layers
        )
        
        # Capa de salida
        self.output_projection = nn.Linear(d_model, num_classes)
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Proyección de entrada
        x = self.input_projection(x)
        
        # Codificación posicional
        x = self.pos_encoding(x)
        
        # Transformer encoder
        encoded = self.transformer_encoder(x)
        
        # Global average pooling
        pooled = torch.mean(encoded, dim=1)
        
        # Salida
        output = self.output_projection(pooled)
        
        return output
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_accuracy', accuracy, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=0.01
        )
        
        def lr_lambda(step):
            if step < self.warmup_steps:
                return step / self.warmup_steps
            else:
                return 0.5 * (1 + math.cos(math.pi * (step - self.warmup_steps) / 
                                          (self.trainer.max_epochs - self.warmup_steps)))
        
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "step"
            }
        }

class CNNLSTMModel(pl.LightningModule):
    """Modelo híbrido CNN-LSTM"""
    
    def __init__(
        self,
        input_size: int = 50,
        cnn_channels: List[int] = [64, 128],
        kernel_size: int = 3,
        lstm_hidden_size: int = 256,
        lstm_layers: int = 2,
        dropout: float = 0.2,
        num_classes: int = 3,
        learning_rate: float = 0.001
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        
        # Capas CNN
        cnn_layers = []
        in_channels = input_size
        
        for out_channels in cnn_channels:
            cnn_layers.extend([
                nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2),
                nn.BatchNorm1d(out_channels),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            in_channels = out_channels
        
        cnn_layers.append(nn.MaxPool1d(2))
        
        self.cnn = nn.Sequential(*cnn_layers)
        
        # Capas LSTM
        self.lstm = nn.LSTM(
            input_size=cnn_channels[-1],
            hidden_size=lstm_hidden_size,
            num_layers=lstm_layers,
            dropout=dropout,
            bidirectional=True,
            batch_first=True
        )
        
        # Capas densas
        self.dense = nn.Sequential(
            nn.Linear(lstm_hidden_size * 2, 128),  # *2 por bidirectional
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # CNN
        x = x.transpose(1, 2)  # (batch, features, seq_len)
        cnn_out = self.cnn(x)
        
        # LSTM
        cnn_out = cnn_out.transpose(1, 2)  # (batch, seq_len, features)
        lstm_out, _ = self.lstm(cnn_out)
        
        # Global average pooling
        pooled = torch.mean(lstm_out, dim=1)
        
        # Dense layers
        output = self.dense(pooled)
        
        return output
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_accuracy', accuracy, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=0.01
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=self.trainer.max_epochs
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss"
            }
        }

class GRUSimpleModel(pl.LightningModule):
    """Modelo GRU simple y eficiente"""
    
    def __init__(
        self,
        input_size: int = 50,
        hidden_size: int = 256,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_classes: int = 3,
        learning_rate: float = 0.001
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        
        # Capas GRU
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        # Capas densas
        self.dense = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # GRU
        gru_out, _ = self.gru(x)
        
        # Global average pooling
        pooled = torch.mean(gru_out, dim=1)
        
        # Dense layers
        output = self.dense(pooled)
        
        return output
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_accuracy', accuracy, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.Adam(
            self.parameters(),
            lr=self.learning_rate
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=self.trainer.max_epochs
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss"
            }
        }

class EnsembleModel(pl.LightningModule):
    """Modelo ensemble de múltiples arquitecturas"""
    
    def __init__(
        self,
        base_models: List[str],
        model_weights: List[float],
        aggregation_method: str = "weighted_average",
        num_classes: int = 3,
        learning_rate: float = 0.001
    ):
        super().__init__()
        self.save_hyperparameters()
        
        self.base_models = base_models
        self.model_weights = torch.tensor(model_weights, dtype=torch.float32)
        self.aggregation_method = aggregation_method
        self.num_classes = num_classes
        self.learning_rate = learning_rate
        
        # Crear modelos base
        self.models = nn.ModuleDict()
        for model_name in base_models:
            if model_name == "lstm_attention":
                self.models[model_name] = LSTMAttentionModel()
            elif model_name == "transformer":
                self.models[model_name] = TransformerModel()
            elif model_name == "cnn_lstm":
                self.models[model_name] = CNNLSTMModel()
            elif model_name == "gru_simple":
                self.models[model_name] = GRUSimpleModel()
        
        # Meta-learner para stacking
        if aggregation_method == "stacking":
            self.meta_learner = nn.Sequential(
                nn.Linear(len(base_models) * num_classes, 64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, num_classes)
            )
        
        # Loss function
        self.criterion = nn.CrossEntropyLoss()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Obtener predicciones de todos los modelos
        predictions = []
        for model_name, model in self.models.items():
            pred = model(x)
            predictions.append(pred)
        
        # Agregar predicciones
        if self.aggregation_method == "weighted_average":
            # Promedio ponderado
            weighted_preds = torch.stack(predictions, dim=0)
            weights = self.model_weights.view(-1, 1, 1).to(weighted_preds.device)
            ensemble_pred = torch.sum(weighted_preds * weights, dim=0)
            
        elif self.aggregation_method == "voting":
            # Votación
            pred_classes = torch.stack([torch.argmax(pred, dim=1) for pred in predictions], dim=1)
            ensemble_pred = torch.zeros_like(predictions[0])
            for i in range(self.num_classes):
                votes = (pred_classes == i).sum(dim=1).float()
                ensemble_pred[:, i] = votes / len(predictions)
                
        elif self.aggregation_method == "stacking":
            # Stacking con meta-learner
            stacked_preds = torch.cat(predictions, dim=1)
            ensemble_pred = self.meta_learner(stacked_preds)
        
        return ensemble_pred
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        preds = torch.argmax(logits, dim=1)
        accuracy = (preds == y).float().mean()
        
        self.log('test_loss', loss, on_step=False, on_epoch=True)
        self.log('test_accuracy', accuracy, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.learning_rate,
            weight_decay=0.01
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=self.trainer.max_epochs
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss"
            }
        }

def create_model(architecture: str, config: Dict[str, Any]) -> pl.LightningModule:
    """
    Factory function para crear modelos
    
    Args:
        architecture: Nombre de la arquitectura
        config: Configuración del modelo
        
    Returns:
        Modelo PyTorch Lightning
    """
    if architecture == "lstm_attention":
        return LSTMAttentionModel(**config)
    elif architecture == "transformer":
        return TransformerModel(**config)
    elif architecture == "cnn_lstm":
        return CNNLSTMModel(**config)
    elif architecture == "gru_simple":
        return GRUSimpleModel(**config)
    elif architecture == "ensemble":
        return EnsembleModel(**config)
    else:
        raise ValueError(f"Arquitectura no soportada: {architecture}")

def load_model_architecture_config() -> Dict[str, Any]:
    """Cargar configuración de arquitecturas desde YAML"""
    config_path = Path("config/enterprise/model_architectures.yaml")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")
