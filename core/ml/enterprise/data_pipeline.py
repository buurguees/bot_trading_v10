# Ruta: core/ml/enterprise/data_pipeline.py
#!/usr/bin/env python3
"""
Enterprise Data Pipeline - Sistema de Pipelines de Datos Escalables
===================================================================

Sistema enterprise-grade para procesamiento de datos de trading con:
- Pipelines escalables con Dask
- Procesamiento distribuido
- Caching inteligente
- Validación de datos
- ETL optimizado
- Soporte para big data

Uso:
    from models.enterprise.data_pipeline import EnterpriseDataPipeline
    
    pipeline = EnterpriseDataPipeline()
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

# MLflow para versionado de datos
import mlflow
import mlflow.data

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class DataPipelineConfig:
    """Configuración del pipeline de datos"""
    # Dask
    n_workers: int = 4
    threads_per_worker: int = 2
    memory_limit: str = "2GB"
    cluster_type: str = "local"  # local, distributed
    
    # Procesamiento
    chunk_size: int = 10000
    npartitions: int = None  # Auto si es None
    memory_efficient: bool = True
    
    # Caching
    enable_caching: bool = True
    cache_dir: str = "cache/data_pipeline"
    cache_ttl: int = 3600  # segundos
    
    # Validación
    enable_validation: bool = True
    validation_rules: Dict[str, Any] = None
    
    # ETL
    enable_etl: bool = True
    etl_steps: List[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/data_pipeline.log"

class DataValidator:
    """Validador de datos enterprise"""
    
    def __init__(self, rules: Dict[str, Any] = None):
        self.rules = rules or self._get_default_rules()
        self.logger = logging.getLogger(__name__)
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Reglas de validación por defecto"""
        return {
            "required_columns": ["open", "high", "low", "close", "volume"],
            "numeric_columns": ["open", "high", "low", "close", "volume"],
            "positive_columns": ["open", "high", "low", "close", "volume"],
            "ohlc_consistency": True,
            "volume_positive": True,
            "no_duplicates": True,
            "time_series_order": True
        }
    
    def validate_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Valida un DataFrame de trading"""
        results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }
        
        try:
            # Verificar columnas requeridas
            missing_cols = set(self.rules["required_columns"]) - set(df.columns)
            if missing_cols:
                results["errors"].append(f"Columnas faltantes: {missing_cols}")
                results["is_valid"] = False
            
            # Verificar tipos numéricos
            for col in self.rules["numeric_columns"]:
                if col in df.columns:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        results["errors"].append(f"Columna {col} no es numérica")
                        results["is_valid"] = False
            
            # Verificar valores positivos
            for col in self.rules["positive_columns"]:
                if col in df.columns:
                    negative_count = (df[col] <= 0).sum()
                    if negative_count > 0:
                        results["warnings"].append(f"Columna {col} tiene {negative_count} valores no positivos")
            
            # Verificar consistencia OHLC
            if self.rules["ohlc_consistency"]:
                ohlc_cols = ["open", "high", "low", "close"]
                if all(col in df.columns for col in ohlc_cols):
                    invalid_ohlc = (
                        (df["high"] < df["low"]) |
                        (df["high"] < df["open"]) |
                        (df["high"] < df["close"]) |
                        (df["low"] > df["open"]) |
                        (df["low"] > df["close"])
                    ).sum()
                    
                    if invalid_ohlc > 0:
                        results["errors"].append(f"Consistencia OHLC: {invalid_ohlc} filas inválidas")
                        results["is_valid"] = False
            
            # Verificar duplicados
            if self.rules["no_duplicates"]:
                duplicates = df.duplicated().sum()
                if duplicates > 0:
                    results["warnings"].append(f"Duplicados encontrados: {duplicates}")
            
            # Estadísticas
            results["stats"] = {
                "rows": len(df),
                "columns": len(df.columns),
                "memory_usage": df.memory_usage(deep=True).sum(),
                "null_values": df.isnull().sum().to_dict()
            }
            
        except Exception as e:
            results["errors"].append(f"Error en validación: {str(e)}")
            results["is_valid"] = False
        
        return results

class DataETL:
    """Sistema ETL para datos de trading"""
    
    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def extract(self, source_config: Dict[str, Any]) -> dd.DataFrame:
        """Extrae datos de fuentes"""
        self.logger.info("Iniciando extracción de datos")
        
        source_type = source_config.get("type", "csv")
        
        if source_type == "csv":
            return await self._extract_csv(source_config)
        elif source_type == "database":
            return await self._extract_database(source_config)
        elif source_type == "api":
            return await self._extract_api(source_config)
        else:
            raise ValueError(f"Tipo de fuente no soportado: {source_type}")
    
    async def _extract_csv(self, config: Dict[str, Any]) -> dd.DataFrame:
        """Extrae datos de archivos CSV"""
        file_path = config["file_path"]
        
        # Leer con Dask
        df = dd.read_csv(
            file_path,
            parse_dates=config.get("parse_dates", []),
            dtype=config.get("dtype", {}),
            npartitions=self.config.npartitions
        )
        
        self.logger.info(f"Datos CSV cargados: {len(df)} filas")
        return df
    
    async def _extract_database(self, config: Dict[str, Any]) -> dd.DataFrame:
        """Extrae datos de base de datos"""
        # Implementar extracción de BD con Dask
        # Por ahora, simular
        self.logger.info("Extrayendo datos de base de datos...")
        
        # Simular datos
        n_rows = config.get("n_rows", 10000)
        data = {
            "timestamp": pd.date_range("2020-01-01", periods=n_rows, freq="1H"),
            "open": np.random.randn(n_rows) * 100 + 50000,
            "high": np.random.randn(n_rows) * 100 + 50000,
            "low": np.random.randn(n_rows) * 100 + 50000,
            "close": np.random.randn(n_rows) * 100 + 50000,
            "volume": np.random.randint(1000, 10000, n_rows)
        }
        
        df = pd.DataFrame(data)
        return dd.from_pandas(df, npartitions=self.config.npartitions)
    
    async def _extract_api(self, config: Dict[str, Any]) -> dd.DataFrame:
        """Extrae datos de API"""
        # Implementar extracción de API
        self.logger.info("Extrayendo datos de API...")
        
        # Simular datos de API
        n_rows = config.get("n_rows", 10000)
        data = {
            "timestamp": pd.date_range("2020-01-01", periods=n_rows, freq="1H"),
            "open": np.random.randn(n_rows) * 100 + 50000,
            "high": np.random.randn(n_rows) * 100 + 50000,
            "low": np.random.randn(n_rows) * 100 + 50000,
            "close": np.random.randn(n_rows) * 100 + 50000,
            "volume": np.random.randint(1000, 10000, n_rows)
        }
        
        df = pd.DataFrame(data)
        return dd.from_pandas(df, npartitions=self.config.npartitions)
    
    async def transform(self, df: dd.DataFrame, transform_config: Dict[str, Any]) -> dd.DataFrame:
        """Transforma los datos"""
        self.logger.info("Iniciando transformación de datos")
        
        # Aplicar transformaciones
        for step in transform_config.get("steps", []):
            df = await self._apply_transform_step(df, step)
        
        return df
    
    async def _apply_transform_step(self, df: dd.DataFrame, step: Dict[str, Any]) -> dd.DataFrame:
        """Aplica un paso de transformación"""
        step_type = step["type"]
        
        if step_type == "filter":
            return await self._filter_data(df, step)
        elif step_type == "aggregate":
            return await self._aggregate_data(df, step)
        elif step_type == "feature_engineering":
            return await self._engineer_features(df, step)
        elif step_type == "normalize":
            return await self._normalize_data(df, step)
        else:
            raise ValueError(f"Tipo de transformación no soportado: {step_type}")
    
    async def _filter_data(self, df: dd.DataFrame, step: Dict[str, Any]) -> dd.DataFrame:
        """Filtra datos"""
        conditions = step.get("conditions", {})
        
        for column, condition in conditions.items():
            if column in df.columns:
                if condition["operator"] == ">":
                    df = df[df[column] > condition["value"]]
                elif condition["operator"] == "<":
                    df = df[df[column] < condition["value"]]
                elif condition["operator"] == "==":
                    df = df[df[column] == condition["value"]]
        
        return df
    
    async def _aggregate_data(self, df: dd.DataFrame, step: Dict[str, Any]) -> dd.DataFrame:
        """Agrega datos"""
        groupby = step.get("groupby", [])
        agg_functions = step.get("agg_functions", {})
        freq = step.get("freq", "1H")
        
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
            df = df.resample(freq).agg(agg_functions)
            df = df.reset_index()
        
        return df
    
    async def _engineer_features(self, df: dd.DataFrame, step: Dict[str, Any]) -> dd.DataFrame:
        """Ingeniería de características"""
        features = step.get("features", [])
        
        for feature in features:
            if feature["type"] == "sma":
                df = self._add_sma(df, feature)
            elif feature["type"] == "rsi":
                df = self._add_rsi(df, feature)
            elif feature["type"] == "macd":
                df = self._add_macd(df, feature)
        
        return df
    
    def _add_sma(self, df: dd.DataFrame, feature: Dict[str, Any]) -> dd.DataFrame:
        """Agrega media móvil simple"""
        column = feature["column"]
        window = feature["window"]
        new_column = feature.get("new_column", f"{column}_sma_{window}")
        
        df[new_column] = df[column].rolling(window=window).mean()
        return df
    
    def _add_rsi(self, df: dd.DataFrame, feature: Dict[str, Any]) -> dd.DataFrame:
        """Agrega RSI"""
        column = feature["column"]
        window = feature["window"]
        new_column = feature.get("new_column", f"{column}_rsi_{window}")
        
        # Calcular RSI
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df[new_column] = 100 - (100 / (1 + rs))
        
        return df
    
    def _add_macd(self, df: dd.DataFrame, feature: Dict[str, Any]) -> dd.DataFrame:
        """Agrega MACD"""
        column = feature["column"]
        fast = feature.get("fast", 12)
        slow = feature.get("slow", 26)
        signal = feature.get("signal", 9)
        
        ema_fast = df[column].ewm(span=fast).mean()
        ema_slow = df[column].ewm(span=slow).mean()
        
        df[f"{column}_macd"] = ema_fast - ema_slow
        df[f"{column}_macd_signal"] = df[f"{column}_macd"].ewm(span=signal).mean()
        df[f"{column}_macd_histogram"] = df[f"{column}_macd"] - df[f"{column}_macd_signal"]
        
        return df
    
    async def _normalize_data(self, df: dd.DataFrame, step: Dict[str, Any]) -> dd.DataFrame:
        """Normaliza datos"""
        method = step.get("method", "zscore")
        columns = step.get("columns", [])
        
        for column in columns:
            if column in df.columns:
                if method == "zscore":
                    mean = df[column].mean()
                    std = df[column].std()
                    df[column] = (df[column] - mean) / std
                elif method == "minmax":
                    min_val = df[column].min()
                    max_val = df[column].max()
                    df[column] = (df[column] - min_val) / (max_val - min_val)
        
        return df
    
    async def load(self, df: dd.DataFrame, load_config: Dict[str, Any]) -> str:
        """Carga datos procesados"""
        self.logger.info("Cargando datos procesados")
        
        output_path = load_config.get("output_path", "processed_data.parquet")
        
        # Guardar como Parquet (formato eficiente)
        df.to_parquet(output_path, engine="pyarrow")
        
        self.logger.info(f"Datos guardados en: {output_path}")
        return output_path

class DataCache:
    """Sistema de cache para datos"""
    
    def __init__(self, cache_dir: str, ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.logger = logging.getLogger(__name__)
    
    def _get_cache_key(self, data_config: Dict[str, Any]) -> str:
        """Genera clave de cache"""
        config_str = json.dumps(data_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def get(self, data_config: Dict[str, Any]) -> Optional[dd.DataFrame]:
        """Obtiene datos del cache"""
        cache_key = self._get_cache_key(data_config)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        metadata_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists() or not metadata_file.exists():
            return None
        
        # Verificar TTL
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            cache_time = datetime.fromisoformat(metadata["timestamp"])
            if (datetime.now() - cache_time).seconds > self.ttl:
                self.logger.info("Cache expirado")
                return None
            
            # Cargar datos
            df = dd.read_parquet(cache_file)
            self.logger.info(f"Datos cargados desde cache: {cache_key}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error cargando cache: {e}")
            return None
    
    def set(self, data_config: Dict[str, Any], df: dd.DataFrame):
        """Guarda datos en cache"""
        cache_key = self._get_cache_key(data_config)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        metadata_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            # Guardar datos
            df.to_parquet(cache_file, engine="pyarrow")
            
            # Guardar metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "config": data_config,
                "rows": len(df),
                "columns": list(df.columns)
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            self.logger.info(f"Datos guardados en cache: {cache_key}")
            
        except Exception as e:
            self.logger.error(f"Error guardando cache: {e}")

class EnterpriseDataPipeline:
    """Pipeline de datos enterprise"""
    
    def __init__(self, config: DataPipelineConfig = None):
        self.config = config or DataPipelineConfig()
        self.logger = logging.getLogger(__name__)
        
        # Componentes
        self.validator = DataValidator(self.config.validation_rules)
        self.etl = DataETL(self.config)
        self.cache = DataCache(self.config.cache_dir, self.config.cache_ttl) if self.config.enable_caching else None
        
        # Cliente Dask
        self.client = None
        
        # Configurar logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.log_file),
                logging.StreamHandler()
            ]
        )
    
    async def start(self):
        """Inicia el pipeline"""
        self.logger.info("Iniciando pipeline de datos enterprise")
        
        # Configurar Dask
        if self.config.cluster_type == "local":
            cluster = LocalCluster(
                n_workers=self.config.n_workers,
                threads_per_worker=self.config.threads_per_worker,
                memory_limit=self.config.memory_limit
            )
            self.client = Client(cluster)
        else:
            self.client = Client()
        
        self.logger.info(f"Dask configurado: {self.client}")
    
    async def stop(self):
        """Detiene el pipeline"""
        if self.client:
            self.client.close()
        
        self.logger.info("Pipeline de datos detenido")
    
    async def process_trading_data(
        self, 
        data_config: Dict[str, Any],
        transform_config: Dict[str, Any] = None,
        load_config: Dict[str, Any] = None
    ) -> dd.DataFrame:
        """Procesa datos de trading"""
        
        try:
            # Verificar cache
            if self.cache:
                cached_data = self.cache.get(data_config)
                if cached_data is not None:
                    self.logger.info("Usando datos del cache")
                    return cached_data
            
            # ETL Pipeline
            with ProgressBar():
                # Extract
                df = await self.etl.extract(data_config)
                
                # Transform
                if transform_config:
                    df = await self.etl.transform(df, transform_config)
                
                # Validate
                if self.config.enable_validation:
                    validation_result = self.validator.validate_dataframe(df.compute())
                    if not validation_result["is_valid"]:
                        self.logger.error(f"Datos inválidos: {validation_result['errors']}")
                        raise ValueError("Datos no pasaron validación")
                    
                    self.logger.info(f"Validación exitosa: {validation_result['stats']}")
                
                # Load
                if load_config:
                    output_path = await self.etl.load(df, load_config)
                    self.logger.info(f"Datos guardados en: {output_path}")
            
            # Guardar en cache
            if self.cache:
                self.cache.set(data_config, df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error procesando datos: {e}")
            raise
    
    async def get_data_summary(self, df: dd.DataFrame) -> Dict[str, Any]:
        """Obtiene resumen de datos"""
        try:
            # Computar estadísticas básicas
            stats = {
                "rows": len(df),
                "columns": list(df.columns),
                "memory_usage": df.memory_usage(deep=True).sum().compute(),
                "dtypes": df.dtypes.to_dict(),
                "null_counts": df.isnull().sum().compute().to_dict()
            }
            
            # Estadísticas numéricas
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stats["numeric_stats"] = df[numeric_cols].describe().compute().to_dict()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen: {e}")
            return {}

# Funciones de utilidad
def create_data_pipeline_config(
    n_workers: int = 4,
    memory_limit: str = "2GB",
    enable_caching: bool = True
) -> DataPipelineConfig:
    """Crea configuración del pipeline"""
    return DataPipelineConfig(
        n_workers=n_workers,
        memory_limit=memory_limit,
        enable_caching=enable_caching
    )

# Ejemplo de uso
async def main():
    """Ejemplo de uso del pipeline de datos"""
    
    # Crear configuración
    config = create_data_pipeline_config()
    
    # Crear pipeline
    pipeline = EnterpriseDataPipeline(config)
    
    try:
        # Iniciar pipeline
        await pipeline.start()
        
        # Configurar datos
        data_config = {
            "type": "csv",
            "file_path": "data/sample_trading_data.csv",
            "parse_dates": ["timestamp"]
        }
        
        transform_config = {
            "steps": [
                {
                    "type": "feature_engineering",
                    "features": [
                        {"type": "sma", "column": "close", "window": 20},
                        {"type": "rsi", "column": "close", "window": 14},
                        {"type": "macd", "column": "close"}
                    ]
                },
                {
                    "type": "normalize",
                    "method": "zscore",
                    "columns": ["close", "volume"]
                }
            ]
        }
        
        # Procesar datos
        processed_data = await pipeline.process_trading_data(
            data_config=data_config,
            transform_config=transform_config
        )
        
        # Obtener resumen
        summary = await pipeline.get_data_summary(processed_data)
        print(f"Resumen de datos: {summary}")
        
    finally:
        # Detener pipeline
        await pipeline.stop()

if __name__ == "__main__":
    import hashlib
    asyncio.run(main())
