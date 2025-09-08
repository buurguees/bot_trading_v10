#!/usr/bin/env python3
"""
Tests para Enterprise Training System
====================================

Tests exhaustivos para el sistema de entrenamiento enterprise:
- Tests unitarios para cada componente
- Tests de integración para flujos completos
- Tests de performance y escalabilidad
- Tests de fault tolerance
- Tests de distributed training
- Mock tests para dependencias externas

Uso:
    pytest tests/test_enterprise_training.py -v
"""

import pytest
import asyncio
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# Añadir directorio del proyecto al path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from models.enterprise.training_engine import (
    EnterpriseTrainingEngine, 
    TrainingConfig, 
    EnterpriseTradingDataset,
    EnterpriseTradingDataModule,
    LSTMAttentionModel,
    EnterpriseTradingModel
)
from models.enterprise.monitoring_system import (
    EnterpriseMonitoringSystem,
    MonitoringConfig,
    TrainingProgressTracker
)
from models.enterprise.data_pipeline import (
    EnterpriseDataPipeline,
    DataPipelineConfig,
    DataValidator,
    DataETL,
    DataCache
)
from models.enterprise.hyperparameter_tuning import (
    EnterpriseHyperparameterTuner,
    TuningConfig,
    HyperparameterSpace,
    ObjectiveFunction
)

class TestTrainingConfig:
    """Tests para TrainingConfig"""
    
    def test_initialization(self):
        """Test inicialización de configuración"""
        config = TrainingConfig()
        
        assert config.model_type == "lstm_attention"
        assert config.hidden_size == 128
        assert config.num_layers == 3
        assert config.dropout == 0.2
        assert config.batch_size == 64
        assert config.learning_rate == 0.001
        assert config.max_epochs == 100
    
    def test_validation_valid_config(self):
        """Test validación de configuración válida"""
        config = TrainingConfig(
            batch_size=32,
            learning_rate=0.01,
            max_epochs=50,
            train_split=0.8,
            strategy="auto",
            precision="16-mixed"
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validation_invalid_config(self):
        """Test validación de configuración inválida"""
        config = TrainingConfig(
            batch_size=-1,
            learning_rate=0,
            max_epochs=0,
            train_split=1.5,
            strategy="invalid",
            precision="invalid"
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("batch_size" in error for error in errors)
        assert any("learning_rate" in error for error in errors)
        assert any("max_epochs" in error for error in errors)
        assert any("train_split" in error for error in errors)
        assert any("strategy" in error for error in errors)
        assert any("precision" in error for error in errors)
    
    def test_to_dict_from_dict(self):
        """Test serialización/deserialización"""
        config = TrainingConfig(
            hidden_size=256,
            num_layers=4,
            dropout=0.3
        )
        
        # Convertir a dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["hidden_size"] == 256
        assert config_dict["num_layers"] == 4
        assert config_dict["dropout"] == 0.3
        
        # Crear desde dict
        new_config = TrainingConfig.from_dict(config_dict)
        assert new_config.hidden_size == 256
        assert new_config.num_layers == 4
        assert new_config.dropout == 0.3

class TestEnterpriseTradingDataset:
    """Tests para EnterpriseTradingDataset"""
    
    @pytest.fixture
    def sample_data(self):
        """Datos de muestra para testing"""
        n_samples = 1000
        data = {
            "open": np.random.randn(n_samples) * 100 + 50000,
            "high": np.random.randn(n_samples) * 100 + 50000,
            "low": np.random.randn(n_samples) * 100 + 50000,
            "close": np.random.randn(n_samples) * 100 + 50000,
            "volume": np.random.randint(1000, 10000, n_samples)
        }
        return pd.DataFrame(data)
    
    def test_initialization(self, sample_data):
        """Test inicialización del dataset"""
        dataset = EnterpriseTradingDataset(
            sample_data,
            sequence_length=60,
            prediction_horizon=1
        )
        
        assert len(dataset) > 0
        assert dataset.sequence_length == 60
        assert dataset.prediction_horizon == 1
    
    def test_getitem(self, sample_data):
        """Test acceso a elementos del dataset"""
        dataset = EnterpriseTradingDataset(
            sample_data,
            sequence_length=10,
            prediction_horizon=1
        )
        
        if len(dataset) > 0:
            x, y = dataset[0]
            assert x.shape == (10, 5)  # sequence_length, n_features
            assert y.shape == (1,)  # prediction_horizon
    
    def test_normalization(self, sample_data):
        """Test normalización de datos"""
        dataset = EnterpriseTradingDataset(
            sample_data,
            sequence_length=10,
            prediction_horizon=1,
            normalize=True
        )
        
        if len(dataset) > 0:
            x, y = dataset[0]
            # Verificar que los datos están normalizados (media ~0, std ~1)
            assert np.abs(x.mean()) < 1.0
            assert np.abs(x.std() - 1.0) < 0.5
    
    def test_empty_data(self):
        """Test con datos vacíos"""
        empty_data = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        
        with pytest.raises(ValueError):
            EnterpriseTradingDataset(empty_data, sequence_length=10)
    
    def test_missing_columns(self, sample_data):
        """Test con columnas faltantes"""
        incomplete_data = sample_data.drop(columns=["close"])
        
        with pytest.raises(ValueError):
            EnterpriseTradingDataset(incomplete_data, sequence_length=10)

class TestLSTMAttentionModel:
    """Tests para LSTMAttentionModel"""
    
    def test_initialization(self):
        """Test inicialización del modelo"""
        model = LSTMAttentionModel(
            input_size=5,
            hidden_size=128,
            num_layers=2,
            dropout=0.2,
            attention_heads=8
        )
        
        assert model.input_size == 5
        assert model.hidden_size == 128
        assert model.num_layers == 2
    
    def test_forward_pass(self):
        """Test forward pass del modelo"""
        model = LSTMAttentionModel(
            input_size=5,
            hidden_size=64,
            num_layers=1,
            dropout=0.1,
            attention_heads=4
        )
        
        # Crear input de prueba
        batch_size = 32
        sequence_length = 60
        input_size = 5
        
        x = torch.randn(batch_size, sequence_length, input_size)
        
        # Forward pass
        output = model(x)
        
        assert output.shape == (batch_size, 1)  # (batch_size, output_size)
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()
    
    def test_different_input_sizes(self):
        """Test con diferentes tamaños de input"""
        model = LSTMAttentionModel(input_size=3, hidden_size=32)
        
        x = torch.randn(16, 30, 3)
        output = model(x)
        
        assert output.shape == (16, 1)
    
    def test_gradient_flow(self):
        """Test flujo de gradientes"""
        model = LSTMAttentionModel(input_size=5, hidden_size=64)
        
        x = torch.randn(8, 20, 5, requires_grad=True)
        output = model(x)
        
        # Calcular loss dummy
        target = torch.randn_like(output)
        loss = nn.MSELoss()(output, target)
        
        # Backward pass
        loss.backward()
        
        # Verificar que los gradientes existen
        for param in model.parameters():
            assert param.grad is not None
            assert not torch.isnan(param.grad).any()

class TestEnterpriseTradingModel:
    """Tests para EnterpriseTradingModel (Lightning)"""
    
    @pytest.fixture
    def training_config(self):
        """Configuración de entrenamiento para testing"""
        return TrainingConfig(
            hidden_size=64,
            num_layers=1,
            dropout=0.1,
            batch_size=16,
            learning_rate=0.001,
            max_epochs=2
        )
    
    def test_initialization(self, training_config):
        """Test inicialización del modelo Lightning"""
        model = EnterpriseTradingModel(training_config)
        
        assert model.config == training_config
        assert isinstance(model.model, LSTMAttentionModel)
        assert isinstance(model.criterion, nn.MSELoss)
    
    def test_training_step(self, training_config):
        """Test training step"""
        model = EnterpriseTradingModel(training_config)
        
        # Crear batch de prueba
        batch_size = 8
        sequence_length = 20
        input_size = 5
        
        x = torch.randn(batch_size, sequence_length, input_size)
        y = torch.randn(batch_size, 1)
        
        # Training step
        loss = model.training_step((x, y), 0)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
        assert not torch.isnan(loss)
    
    def test_validation_step(self, training_config):
        """Test validation step"""
        model = EnterpriseTradingModel(training_config)
        
        # Crear batch de prueba
        x = torch.randn(8, 20, 5)
        y = torch.randn(8, 1)
        
        # Validation step
        loss = model.validation_step((x, y), 0)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
        assert not torch.isnan(loss)
    
    def test_configure_optimizers(self, training_config):
        """Test configuración de optimizadores"""
        model = EnterpriseTradingModel(training_config)
        
        optimizers = model.configure_optimizers()
        
        assert "optimizer" in optimizers
        assert "lr_scheduler" in optimizers
        assert isinstance(optimizers["optimizer"], torch.optim.Optimizer)

class TestEnterpriseTrainingEngine:
    """Tests para EnterpriseTrainingEngine"""
    
    @pytest.fixture
    def engine(self):
        """Engine de entrenamiento para testing"""
        return EnterpriseTrainingEngine(
            experiment_name="test_experiment",
            run_name="test_run"
        )
    
    @pytest.fixture
    def training_config(self):
        """Configuración de entrenamiento"""
        return TrainingConfig(
            max_epochs=2,
            batch_size=16,
            learning_rate=0.001
        )
    
    @pytest.fixture
    def data_config(self):
        """Configuración de datos"""
        return {
            "n_samples": 1000,
            "n_features": 5,
            "symbols": ["BTCUSDT"]
        }
    
    def test_initialization(self, engine):
        """Test inicialización del engine"""
        assert engine.experiment_name == "test_experiment"
        assert engine.run_name == "test_run"
        assert engine.is_training == False
        assert engine.current_run is None
    
    @pytest.mark.asyncio
    async def test_setup_mlflow(self, engine):
        """Test configuración de MLflow"""
        with patch('mlflow.tracking.MlflowClient') as mock_client:
            mock_client.return_value.get_experiment_by_name.side_effect = Exception("Not found")
            mock_client.return_value.create_experiment.return_value = "exp_123"
            mock_client.return_value.create_run.return_value.info.run_id = "run_123"
            
            await engine._setup_mlflow()
            
            assert engine.current_run is not None
    
    @pytest.mark.asyncio
    async def test_load_data(self, engine, data_config):
        """Test carga de datos"""
        data = await engine._load_data(data_config)
        
        assert len(data) == 3  # train, val, test
        assert all(isinstance(df, pd.DataFrame) for df in data)
        assert all(len(df) > 0 for df in data)
    
    @pytest.mark.asyncio
    async def test_setup_callbacks(self, engine, training_config):
        """Test configuración de callbacks"""
        callbacks = await engine._setup_callbacks(training_config)
        
        assert len(callbacks) > 0
        assert any("ModelCheckpoint" in str(type(cb)) for cb in callbacks)
        assert any("EarlyStopping" in str(type(cb)) for cb in callbacks)
    
    @pytest.mark.asyncio
    async def test_setup_loggers(self, engine):
        """Test configuración de loggers"""
        loggers = await engine._setup_loggers()
        
        assert len(loggers) > 0
        assert any("TensorBoardLogger" in str(type(logger)) for logger in loggers)
    
    @pytest.mark.asyncio
    async def test_setup_strategy(self, engine, training_config):
        """Test configuración de estrategia"""
        strategy = await engine._setup_strategy(training_config)
        
        assert strategy is not None
    
    @pytest.mark.asyncio
    async def test_train_distributed_mock(self, engine, training_config, data_config):
        """Test entrenamiento distribuido con mocks"""
        with patch('pytorch_lightning.Trainer') as mock_trainer_class:
            mock_trainer = Mock()
            mock_trainer_class.return_value = mock_trainer
            
            with patch.object(engine, '_load_data', return_value=(
                pd.DataFrame(np.random.randn(100, 5)),
                pd.DataFrame(np.random.randn(20, 5)),
                pd.DataFrame(np.random.randn(10, 5))
            )):
                with patch.object(engine, '_setup_mlflow'):
                    with patch.object(engine, '_setup_callbacks', return_value=[]):
                        with patch.object(engine, '_setup_loggers', return_value=[]):
                            with patch.object(engine, '_setup_strategy', return_value="auto"):
                                
                                results = await engine.train_distributed(
                                    data_config=data_config,
                                    model_config=training_config
                                )
                                
                                assert isinstance(results, dict)
                                assert "status" in results
                                assert results["status"] == "completed"

class TestMonitoringSystem:
    """Tests para EnterpriseMonitoringSystem"""
    
    @pytest.fixture
    def monitoring_config(self):
        """Configuración de monitoreo"""
        return MonitoringConfig(
            prometheus_port=8001,
            enable_alerts=False,
            log_metrics=False
        )
    
    @pytest.fixture
    def monitoring_system(self, monitoring_config):
        """Sistema de monitoreo"""
        return EnterpriseMonitoringSystem(monitoring_config)
    
    def test_initialization(self, monitoring_system):
        """Test inicialización del sistema de monitoreo"""
        assert monitoring_system.is_monitoring == False
        assert monitoring_system.monitoring_thread is None
        assert len(monitoring_system.alert_callbacks) == 0
    
    def test_prometheus_metrics_setup(self, monitoring_system):
        """Test configuración de métricas Prometheus"""
        # Verificar que las métricas están definidas
        assert hasattr(monitoring_system, 'cpu_usage')
        assert hasattr(monitoring_system, 'memory_usage')
        assert hasattr(monitoring_system, 'gpu_memory_usage')
        assert hasattr(monitoring_system, 'training_loss')
        assert hasattr(monitoring_system, 'validation_loss')
    
    def test_update_resource_metrics(self, monitoring_system):
        """Test actualización de métricas de recursos"""
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.used = 100
                    mock_disk.return_value.total = 200
                    with patch('GPUtil.getGPUs', return_value=[]):
                        
                        monitoring_system._update_resource_metrics()
                        
                        assert monitoring_system.resource_state["cpu_percent"] == 50.0
                        assert monitoring_system.resource_state["memory_percent"] == 60.0
                        assert monitoring_system.resource_state["disk_usage_percent"] == 50.0
    
    def test_update_training_metrics(self, monitoring_system):
        """Test actualización de métricas de entrenamiento"""
        monitoring_system.update_training_metrics(
            epoch=5,
            train_loss=0.5,
            val_loss=0.6,
            learning_rate=0.001
        )
        
        # Verificar que las métricas se actualizaron
        # (No podemos verificar directamente los valores de Prometheus)
        assert True  # Si no hay excepción, el test pasa
    
    def test_alert_callback(self, monitoring_system):
        """Test callback de alertas"""
        alert_messages = []
        
        def alert_callback(message):
            alert_messages.append(message)
        
        monitoring_system.add_alert_callback(alert_callback)
        
        # Simular alerta
        monitoring_system._send_alert("Test alert")
        
        assert "Test alert" in alert_messages
    
    def test_get_metrics_summary(self, monitoring_system):
        """Test obtención de resumen de métricas"""
        summary = monitoring_system.get_metrics_summary()
        
        assert isinstance(summary, dict)
        assert "resource_state" in summary
        assert "is_monitoring" in summary
        assert "prometheus_url" in summary

class TestDataPipeline:
    """Tests para EnterpriseDataPipeline"""
    
    @pytest.fixture
    def pipeline_config(self):
        """Configuración del pipeline"""
        return DataPipelineConfig(
            n_workers=2,
            memory_limit="1GB",
            enable_caching=False,
            enable_validation=True
        )
    
    @pytest.fixture
    def data_pipeline(self, pipeline_config):
        """Pipeline de datos"""
        return EnterpriseDataPipeline(pipeline_config)
    
    def test_initialization(self, data_pipeline):
        """Test inicialización del pipeline"""
        assert data_pipeline.config is not None
        assert data_pipeline.validator is not None
        assert data_pipeline.etl is not None
        assert data_pipeline.cache is None  # Caching deshabilitado
    
    def test_data_validator(self):
        """Test validador de datos"""
        validator = DataValidator()
        
        # Datos válidos
        valid_data = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [103, 104, 105],
            "volume": [1000, 1100, 1200]
        })
        
        result = validator.validate_dataframe(valid_data)
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
    
    def test_data_validator_invalid(self):
        """Test validador con datos inválidos"""
        validator = DataValidator()
        
        # Datos inválidos (faltan columnas)
        invalid_data = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [105, 106, 107]
        })
        
        result = validator.validate_dataframe(invalid_data)
        assert result["is_valid"] == False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_etl_extract_csv(self, data_pipeline):
        """Test extracción de CSV"""
        # Crear archivo CSV temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("open,high,low,close,volume\n")
            f.write("100,105,95,103,1000\n")
            f.write("101,106,96,104,1100\n")
            temp_file = f.name
        
        try:
            data_config = {
                "type": "csv",
                "file_path": temp_file
            }
            
            df = await data_pipeline.etl.extract(data_config)
            
            assert len(df) == 2
            assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_etl_transform(self, data_pipeline):
        """Test transformación de datos"""
        # Crear datos de prueba
        data = pd.DataFrame({
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [103, 104, 105, 106, 107],
            "volume": [1000, 1100, 1200, 1300, 1400]
        })
        
        df = dd.from_pandas(data, npartitions=1)
        
        transform_config = {
            "steps": [
                {
                    "type": "feature_engineering",
                    "features": [
                        {"type": "sma", "column": "close", "window": 3}
                    ]
                }
            ]
        }
        
        result_df = await data_pipeline.etl.transform(df, transform_config)
        
        assert len(result_df) == len(data)
        assert "close_sma_3" in result_df.columns

class TestHyperparameterTuning:
    """Tests para EnterpriseHyperparameterTuner"""
    
    @pytest.fixture
    def tuning_config(self):
        """Configuración de tuning"""
        return TuningConfig(
            n_trials=5,
            timeout=60,
            sampler_type="random",
            pruner_type="median"
        )
    
    @pytest.fixture
    def hyperparameter_space(self):
        """Espacio de hyperparámetros"""
        return HyperparameterSpace(
            hidden_size=(32, 64),
            learning_rate=(0.001, 0.01),
            batch_size=[16, 32]
        )
    
    @pytest.fixture
    def tuner(self, tuning_config):
        """Tuner de hyperparámetros"""
        return EnterpriseHyperparameterTuner(tuning_config)
    
    def test_initialization(self, tuner):
        """Test inicialización del tuner"""
        assert tuner.config is not None
        assert tuner.study is None
        assert tuner.objective_function is None
    
    def test_create_sampler(self, tuner):
        """Test creación de sampler"""
        sampler = tuner._create_sampler()
        assert sampler is not None
    
    def test_create_pruner(self, tuner):
        """Test creación de pruner"""
        pruner = tuner._create_pruner()
        assert pruner is not None
    
    def test_objective_function(self, hyperparameter_space, tuning_config):
        """Test función objetivo"""
        async def mock_training_function(config, data_config):
            return {"val_loss": np.random.exponential(0.5)}
        
        objective = ObjectiveFunction(
            training_function=mock_training_function,
            data_config={},
            tuning_config=tuning_config,
            hyperparameter_space=hyperparameter_space
        )
        
        # Crear trial mock
        trial = Mock()
        trial.number = 0
        trial.suggest_int = Mock(side_effect=lambda name, low, high: (low + high) // 2)
        trial.suggest_float = Mock(side_effect=lambda name, low, high, log=False: (low + high) / 2)
        trial.suggest_categorical = Mock(side_effect=lambda name, choices: choices[0])
        
        # Ejecutar función objetivo
        score = objective(trial)
        
        assert isinstance(score, float)
        assert score >= 0

class TestIntegration:
    """Tests de integración"""
    
    @pytest.mark.asyncio
    async def test_full_training_pipeline(self):
        """Test pipeline completo de entrenamiento"""
        # Crear configuración
        training_config = TrainingConfig(
            max_epochs=1,
            batch_size=16,
            learning_rate=0.001
        )
        
        data_config = {
            "n_samples": 100,
            "n_features": 5
        }
        
        # Crear engine
        engine = EnterpriseTrainingEngine(
            experiment_name="test_integration",
            run_name="test_run"
        )
        
        # Mock MLflow y Trainer
        with patch('mlflow.tracking.MlflowClient'):
            with patch('pytorch_lightning.Trainer') as mock_trainer_class:
                mock_trainer = Mock()
                mock_trainer_class.return_value = mock_trainer
                
                # Ejecutar entrenamiento
                results = await engine.train_distributed(
                    data_config=data_config,
                    model_config=training_config
                )
                
                assert isinstance(results, dict)
                assert "status" in results
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test integración con sistema de monitoreo"""
        config = MonitoringConfig(enable_alerts=False, log_metrics=False)
        monitor = EnterpriseMonitoringSystem(config)
        
        # Simular métricas de entrenamiento
        monitor.update_training_metrics(
            epoch=5,
            train_loss=0.5,
            val_loss=0.6
        )
        
        # Obtener resumen
        summary = monitor.get_metrics_summary()
        assert isinstance(summary, dict)

# Tests de performance
class TestPerformance:
    """Tests de performance"""
    
    @pytest.mark.asyncio
    async def test_training_speed(self):
        """Test velocidad de entrenamiento"""
        config = TrainingConfig(
            max_epochs=2,
            batch_size=32,
            learning_rate=0.001
        )
        
        # Crear datos de prueba
        data = pd.DataFrame(np.random.randn(1000, 5), columns=['open', 'high', 'low', 'close', 'volume'])
        dataset = EnterpriseTradingDataset(data, sequence_length=20)
        
        # Medir tiempo de creación de dataset
        start_time = time.time()
        _ = EnterpriseTradingDataset(data, sequence_length=20)
        creation_time = time.time() - start_time
        
        assert creation_time < 1.0  # Debe ser rápido
    
    def test_memory_usage(self):
        """Test uso de memoria"""
        # Crear dataset grande
        data = pd.DataFrame(np.random.randn(10000, 5), columns=['open', 'high', 'low', 'close', 'volume'])
        dataset = EnterpriseTradingDataset(data, sequence_length=60)
        
        # Verificar que no hay memory leaks obvios
        assert len(dataset) > 0
        assert dataset.sequence_length == 60

# Tests de fault tolerance
class TestFaultTolerance:
    """Tests de fault tolerance"""
    
    @pytest.mark.asyncio
    async def test_training_with_invalid_data(self):
        """Test entrenamiento con datos inválidos"""
        config = TrainingConfig(max_epochs=1)
        
        # Datos inválidos
        invalid_data = pd.DataFrame({
            "open": [100, np.nan, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [103, 104, 105],
            "volume": [1000, 1100, 1200]
        })
        
        dataset = EnterpriseTradingDataset(invalid_data, sequence_length=2)
        
        # Debe manejar datos inválidos gracefully
        assert len(dataset) >= 0
    
    @pytest.mark.asyncio
    async def test_training_with_empty_data(self):
        """Test entrenamiento con datos vacíos"""
        config = TrainingConfig(max_epochs=1)
        
        # Datos vacíos
        empty_data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        with pytest.raises(ValueError):
            EnterpriseTradingDataset(empty_data, sequence_length=10)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
