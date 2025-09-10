# Ruta: core/ml/enterprise/data_pipeline.py
#!/usr/bin/env python3
"""
Enterprise Data Pipeline - Sistema de Pipelines de Datos Escalables
===================================================================

Sistema enterprise-grade para procesamiento de datos de trading con:
- Pipelines escalables con Dask
- Procesamiento distribuido
- Caching inteligente (disco + Redis)
- Validación de datos
- ETL optimizado con indicadores trading (Volatility, Bollinger Bands, ATR)
- Soporte para streaming en tiempo real (Kafka)
- Auditoría detallada por símbolo

Uso:
    from core.ml.enterprise.data_pipeline import EnterpriseDataPipeline
    pipeline = EnterpriseDataPipeline(config)
    processed_data = await pipeline.process_trading_data(data_config)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
import json
import pickle
from pathlib import Path

import pandas as pd
import numpy as np
import dask
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster
from dask.diagnostics import ProgressBar
import dask.array as da
import mlflow
import mlflow.data
import redis
from kafka import KafkaConsumer, KafkaProducer
from core.data.historical_data_adapter import get_historical_data

logger = logging.getLogger(__name__)

@dataclass
class DataPipelineConfig:
    """Configuración del pipeline de datos"""
    n_workers: int = 4
    threads_per_worker: int = 2
    memory_limit: str = "2GB"
    cluster_type: str = "local"
    chunk_size: int = 10000
    npartitions: int = None
    memory_efficient: bool = True
    enable_caching: bool = True
    cache_dir: str = "cache/data_pipeline"
    cache_ttl: int = 3600
    enable_validation: bool = True
    validation_rules: Dict[str, Any] = None
    enable_etl: bool = True
    etl_steps: List[str] = None
    log_level: str = "INFO"
    log_file: str = "logs/data_pipeline.log"
    enable_streaming: bool = False
    kafka_bootstrap_servers: List[str] = ["localhost:9092"]
    kafka_topic: str = "trading_data"
    redis_url: str = "redis://localhost:6379"

class DataValidator:
    """Validador de datos enterprise"""
    def __init__(self, rules: Dict[str, Any] = None):
        self.rules = rules or {
            "positive_columns": ["open", "high", "low", "close", "volume"],
            "max_gap_minutes": 60,
            "outlier_threshold": 3.0
        }
        self.logger = logging.getLogger(__name__)

    def validate(self, data: dd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """Valida datos y retorna estado y reporte"""
        try:
            report = {}
            # Validar columnas positivas
            for col in self.rules.get("positive_columns", []):
                if col in data.columns:
                    invalid = data[data[col] <= 0][col].compute()
                    report[f"invalid_{col}"] = len(invalid)
                    data = data[data[col] > 0]

            # Validar gaps temporales
            if 'timestamp' in data.columns:
                data['timestamp'] = dd.to_datetime(data['timestamp'], unit='s')
                gaps = (data['timestamp'].diff().dt.total_seconds() / 60 > self.rules["max_gap_minutes"]).sum().compute()
                report["gaps"] = gaps

            # Validar outliers
            for col in ['close', 'volume']:
                if col in data.columns:
                    z_scores = (data[col] - data[col].mean()) / data[col].std()
                    outliers = (z_scores.abs() > self.rules["outlier_threshold"]).sum().compute()
                    report[f"outliers_{col}"] = outliers
                    data = data[z_scores.abs() <= self.rules["outlier_threshold"]]

            return True, report
        except Exception as e:
            self.logger.error(f"Error en validación: {e}")
            return False, {"error": str(e)}

class EnterpriseDataPipeline:
    """Pipeline de datos enterprise para trading"""
    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.redis_client = None
        self.kafka_producer = None
        self.kafka_consumer = None
        self._setup_logging()
        if config.enable_streaming:
            self._setup_kafka()
        if config.redis_url:
            self._setup_redis()

    def _setup_logging(self):
        """Configura logging"""
        logging.basicConfig(
            filename=self.config.log_file,
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _setup_kafka(self):
        """Configura Kafka para streaming"""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            self.kafka_consumer = KafkaConsumer(
                self.config.kafka_topic,
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='latest'
            )
            self.logger.info("Conexión a Kafka establecida")
        except Exception as e:
            self.logger.error(f"Error conectando a Kafka: {e}")
            self.kafka_producer = None
            self.kafka_consumer = None

    def _setup_redis(self):
        """Configura Redis para caching por símbolo"""
        try:
            self.redis_client = redis.Redis.from_url(self.config.redis_url)
            self.logger.info("Conexión a Redis establecida para caching")
        except Exception as e:
            self.logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None

    async def start(self):
        """Inicia el cluster Dask"""
        try:
            if self.config.cluster_type == "local":
                self.client = Client(
                    LocalCluster(
                        n_workers=self.config.n_workers,
                        threads_per_worker=self.config.threads_per_worker,
                        memory_limit=self.config.memory_limit
                    )
                )
            self.logger.info(f"Cluster Dask iniciado: {self.config.cluster_type}")
        except Exception as e:
            self.logger.error(f"Error iniciando Dask: {e}")

    async def stop(self):
        """Detiene el cluster Dask y cierra conexiones"""
        try:
            if self.client:
                self.client.close()
            if self.kafka_producer:
                self.kafka_producer.close()
            if self.kafka_consumer:
                self.kafka_consumer.close()
            if self.redis_client:
                self.redis_client.close()
            self.logger.info("Pipeline detenido")
        except Exception as e:
            self.logger.error(f"Error deteniendo pipeline: {e}")

    async def process_trading_data(
        self,
        data_config: Dict[str, Any],
        transform_config: Optional[Dict[str, Any]] = None
    ) -> dd.DataFrame:
        """Procesa datos de trading (históricos o en tiempo real)"""
        try:
            start_time = time.time()
            symbol = data_config.get('symbol', 'BTCUSDT')
            timeframe = data_config.get('timeframe', '1h')

            # Verificar cache en Redis
            if self.redis_client and self.config.enable_caching:
                cache_key = f"pipeline_{symbol}_{timeframe}"
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    self.logger.info(f"Usando datos cacheados para {symbol}_{timeframe}")
                    return dd.from_pandas(pd.read_json(cached_data), npartitions=self.config.npartitions or 1)

            # Cargar datos
            if data_config.get('type') == 'streaming':
                data = await self._process_streaming_data(data_config)
            else:
                data = await self._load_historical_data(data_config)

            # Validar datos
            if self.config.enable_validation:
                validator = DataValidator(self.config.validation_rules)
                valid, report = validator.validate(data)
                if not valid:
                    self.logger.error(f"Validación fallida: {report}")
                    return data
                self.logger.info(f"Validación completada: {report}")

            # Transformaciones
            if transform_config and self.config.enable_etl:
                data = self._apply_transformations(data, transform_config, symbol, timeframe)

            # Guardar en cache
            if self.redis_client and self.config.enable_caching:
                self.redis_client.setex(cache_key, self.config.cache_ttl, data.compute().to_json())
                self.logger.info(f"Datos cacheados para {symbol}_{timeframe}")

            # Guardar en disco
            if data_config.get('save_to_disk', True):
                output_path = Path(f"data/processed/{symbol}_{timeframe}_processed.parquet")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                data.compute().to_parquet(output_path)
                self.logger.info(f"Datos guardados en {output_path}")

            # Log en MLflow
            with mlflow.start_run():
                mlflow.log_metrics({
                    "processing_time": time.time() - start_time,
                    "records_processed": len(data),
                    "partitions": data.npartitions
                })
                mlflow.log_param("symbol", symbol)
                mlflow.log_param("timeframe", timeframe)

            return data

        except Exception as e:
            self.logger.error(f"Error procesando datos: {e}")
            return dd.from_pandas(pd.DataFrame(), npartitions=1)

    async def _load_historical_data(self, data_config: Dict[str, Any]) -> dd.DataFrame:
        """Carga datos históricos desde SQLite"""
        try:
            symbol = data_config.get('symbol', 'BTCUSDT')
            timeframe = data_config.get('timeframe', '1h')
            data = get_historical_data(symbol, timeframe)
            if data.empty:
                self.logger.warning(f"No se encontraron datos para {symbol}_{timeframe}")
                return dd.from_pandas(pd.DataFrame(), npartitions=1)
            return dd.from_pandas(data, npartitions=self.config.npartitions or 1)
        except Exception as e:
            self.logger.error(f"Error cargando datos históricos: {e}")
            return dd.from_pandas(pd.DataFrame(), npartitions=1)

    async def _process_streaming_data(self, data_config: Dict[str, Any]) -> dd.DataFrame:
        """Procesa datos en tiempo real desde Kafka"""
        try:
            if not self.kafka_consumer:
                raise ValueError("Kafka no configurado")
            
            symbol = data_config.get('symbol', 'BTCUSDT')
            timeframe = data_config.get('timeframe', '1h')
            records = []
            for message in self.kafka_consumer:
                data = message.value
                if data.get('symbol') == symbol and data.get('timeframe') == timeframe:
                    records.append(data)
                if len(records) >= self.config.chunk_size:
                    break
            
            df = pd.DataFrame(records)
            if df.empty:
                return dd.from_pandas(df, npartitions=1)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            return dd.from_pandas(df, npartitions=self.config.npartitions or 1)
        except Exception as e:
            self.logger.error(f"Error procesando streaming: {e}")
            return dd.from_pandas(pd.DataFrame(), npartitions=1)

    def _apply_transformations(self, data: dd.DataFrame, transform_config: Dict[str, Any], symbol: str, timeframe: str) -> dd.DataFrame:
        """Aplica transformaciones de feature engineering"""
        try:
            steps = transform_config.get('steps', [])
            for step in steps:
                if step['type'] == 'feature_engineering':
                    for feature in step.get('features', []):
                        if feature['type'] == 'sma':
                            data[f"sma_{feature['window']}"] = data[feature['column']].rolling(window=feature['window']).mean()
                        elif feature['type'] == 'rsi':
                            delta = data[feature['column']].diff()
                            gain = delta.where(delta > 0, 0).rolling(window=feature['window']).mean()
                            loss = -delta.where(delta < 0, 0).rolling(window=feature['window']).mean()
                            rs = gain / loss
                            data[f"rsi_{feature['window']}"] = 100 - (100 / (1 + rs))
                        elif feature['type'] == 'macd':
                            ema12 = data[feature['column']].ewm(span=12, adjust=False).mean()
                            ema26 = data[feature['column']].ewm(span=26, adjust=False).mean()
                            data['macd'] = ema12 - ema26
                            data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
                        elif feature['type'] == 'volatility':
                            returns = data[feature['column']].pct_change()
                            data[f"volatility_{feature['window']}"] = returns.rolling(window=feature['window']).std()
                        elif feature['type'] == 'bollinger':
                            sma = data[feature['column']].rolling(window=feature['window']).mean()
                            std = data[feature['column']].rolling(window=feature['window']).std()
                            data[f"bb_upper_{feature['window']}"] = sma + 2 * std
                            data[f"bb_lower_{feature['window']}"] = sma - 2 * std
                        elif feature['type'] == 'atr':
                            high_low = data['high'] - data['low']
                            high_close = (data['high'] - data['close'].shift(1)).abs()
                            low_close = (data['low'] - data['close'].shift(1)).abs()
                            tr = da.maximum(da.maximum(high_low, high_close), low_close)
                            data[f"atr_{feature['window']}"] = tr.rolling(window=feature['window']).mean()
                elif step['type'] == 'normalize':
                    if step['method'] == 'zscore':
                        for col in step['columns']:
                            data[col] = (data[col] - data[col].mean()) / data[col].std()
            self.logger.info(f"Transformaciones aplicadas para {symbol}_{timeframe}")
            return data
        except Exception as e:
            self.logger.error(f"Error aplicando transformaciones: {e}")
            return data

    async def get_data_summary(self, data: dd.DataFrame) -> Dict[str, Any]:
        """Obtiene resumen estadístico de los datos"""
        try:
            stats = data.describe().compute().to_dict()
            stats['symbol'] = data['symbol'].iloc[0].compute()
            stats['timeframe'] = data['timeframe'].iloc[0].compute()
            stats['records'] = len(data)
            return stats
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen: {e}")
            return {}

def create_data_pipeline_config(
    n_workers: int = 4,
    memory_limit: str = "2GB",
    enable_caching: bool = True,
    enable_streaming: bool = False
) -> DataPipelineConfig:
    """Crea configuración del pipeline"""
    return DataPipelineConfig(
        n_workers=n_workers,
        memory_limit=memory_limit,
        enable_caching=enable_caching,
        enable_streaming=enable_streaming
    )

async def main():
    """Ejemplo de uso"""
    config = create_data_pipeline_config(enable_streaming=True)
    pipeline = EnterpriseDataPipeline(config)
    await pipeline.start()
    try:
        data_config = {
            "type": "historical",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "save_to_disk": True
        }
        transform_config = {
            "steps": [
                {
                    "type": "feature_engineering",
                    "features": [
                        {"type": "sma", "column": "close", "window": 20},
                        {"type": "rsi", "column": "close", "window": 14},
                        {"type": "macd", "column": "close"},
                        {"type": "volatility", "column": "close", "window": 20},
                        {"type": "bollinger", "column": "close", "window": 20},
                        {"type": "atr", "column": "close", "window": 14}
                    ]
                },
                {
                    "type": "normalize",
                    "method": "zscore",
                    "columns": ["close", "volume", "sma_20", "rsi_14", "macd", "volatility_20"]
                }
            ]
        }
        processed_data = await pipeline.process_trading_data(data_config, transform_config)
        summary = await pipeline.get_data_summary(processed_data)
        print(f"Resumen de datos: {summary}")
    finally:
        await pipeline.stop()

if __name__ == "__main__":
    asyncio.run(main())