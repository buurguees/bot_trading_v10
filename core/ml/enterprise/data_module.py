# Ruta: core/ml/enterprise/data_module.py
# data_module.py - PyTorch Lightning DataModule para trading
# Ubicación: C:\TradingBot_v10\models\enterprise\data_module.py

"""
DataModule de PyTorch Lightning para datos de trading.

Características:
- Carga de datos desde múltiples fuentes
- Preprocesamiento automático
- Data augmentation
- Splits de train/val/test
- Integración con TimescaleDB y Redis
"""

import torch
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import yaml

# Importar el nuevo sistema de datos
from core.data.historical_data_adapter import get_historical_data

# Importar ConfigLoader
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class TradingDataset(Dataset):
    """Dataset personalizado para datos de trading"""
    
    def __init__(
        self,
        data: pd.DataFrame,
        features: List[str],
        target_column: str = 'target',
        sequence_length: int = 60,
        prediction_horizon: int = 1
    ):
        self.data = data
        self.features = features
        self.target_column = target_column
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        
        # Preparar datos
        self.X = data[features].values.astype(np.float32)
        self.y = data[target_column].values.astype(np.int64)
        
        # Validar datos
        self._validate_data()
        
    def _validate_data(self):
        """Valida la integridad de los datos"""
        if len(self.X) < self.sequence_length + self.prediction_horizon:
            raise ValueError(f"Datos insuficientes: {len(self.X)} < {self.sequence_length + self.prediction_horizon}")
        
        if np.isnan(self.X).any():
            logger.warning("Datos con NaN encontrados, rellenando con 0")
            self.X = np.nan_to_num(self.X, nan=0.0)
        
        if np.isinf(self.X).any():
            logger.warning("Datos con infinitos encontrados, rellenando con 0")
            self.X = np.nan_to_num(self.X, nan=0.0, posinf=0.0, neginf=0.0)
    
    def __len__(self) -> int:
        return len(self.X) - self.sequence_length - self.prediction_horizon + 1
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # Obtener secuencia de features
        start_idx = idx
        end_idx = start_idx + self.sequence_length
        X_seq = self.X[start_idx:end_idx]
        
        # Obtener target (predicción futura)
        target_idx = end_idx + self.prediction_horizon - 1
        y_target = self.y[target_idx]
        
        return torch.tensor(X_seq), torch.tensor(y_target)

class TradingDataModule(pl.LightningDataModule):
    """DataModule de PyTorch Lightning para datos de trading"""
    
    def __init__(
        self,
        symbol: str,
        config: Dict[str, Any],
        data_source: str = "timescaledb",  # timescaledb, redis, csv
        data_path: Optional[str] = None
    ):
        super().__init__()
        self.symbol = symbol
        self.config = config
        self.data_source = data_source
        self.data_path = data_path
        
        # Configuración de datos
        self.sequence_length = config.get('lookback_periods', 60)
        self.prediction_horizon = config.get('prediction_horizon', 1)
        self.batch_size = config.get('batch_size', 64)
        self.num_workers = config.get('num_workers', 8)
        self.pin_memory = config.get('pin_memory', True)
        
        # Splits de datos
        self.train_split = config.get('train_split', 0.7)
        self.val_split = config.get('val_split', 0.2)
        self.test_split = config.get('test_split', 0.1)
        
        # Features
        self.features = self._get_features()
        self.target_column = 'target'
        
        # Datasets
        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None
        
    def _get_features(self) -> List[str]:
        """Obtiene la lista de features a usar"""
        # Features por defecto
        default_features = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_10', 'sma_20', 'ema_12', 'ema_26',
            'rsi_14', 'macd', 'bollinger_upper', 'bollinger_lower'
        ]
        
        # Obtener features de configuración si están disponibles
        if 'features' in self.config:
            features_config = self.config['features']
            all_features = []
            
            # Features técnicos
            if 'technical' in features_config:
                tech_features = features_config['technical']
                if 'price_features' in tech_features:
                    all_features.extend(tech_features['price_features'])
                if 'volume_features' in tech_features:
                    all_features.extend(tech_features['volume_features'])
                if 'momentum_features' in tech_features:
                    all_features.extend(tech_features['momentum_features'])
            
            # Features de precio
            if 'price_features' in features_config:
                all_features.extend(features_config['price_features'])
            
            # Features de mercado
            if 'market_features' in features_config:
                all_features.extend(features_config['market_features'])
            
            return all_features if all_features else default_features
        
        return default_features
    
    def prepare_data(self):
        """Prepara los datos (se ejecuta una sola vez)"""
        logger.info(f"Preparando datos para {self.symbol}")
        
        # Cargar datos
        data = self._load_data()
        
        # Preprocesar datos
        data = self._preprocess_data(data)
        
        # Crear target
        data = self._create_target(data)
        
        # Guardar datos procesados
        self._save_processed_data(data)
        
        logger.info(f"Datos preparados: {len(data)} registros, {len(self.features)} features")
    
    def _load_data(self) -> pd.DataFrame:
        """Carga datos desde la fuente especificada"""
        try:
            # Usar el nuevo sistema de bases de datos SQLite
            if self.data_source == "csv" and self.data_path:
                # Migrar de CSV a SQLite si es necesario
                logger.info(f"Migrando datos CSV a SQLite para {self.symbol}")
                return self._migrate_csv_to_sqlite()
            elif self.data_source == "timescaledb":
                return self._load_from_timescaledb()
            elif self.data_source == "redis":
                return self._load_from_redis()
            else:
                # Usar el nuevo sistema de datos históricos
                return self._load_from_historical_db()
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
            return self._generate_synthetic_data()
    
    def _load_from_historical_db(self) -> pd.DataFrame:
        """Carga datos desde el nuevo sistema de bases de datos históricos"""
        try:
            # Obtener datos de los últimos 30 días para entrenamiento
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Leer timeframes desde configuración
            config_loader = ConfigLoader("config/data_config.yaml")
            data_config = config_loader.load_config()
            timeframes = data_config.get('historical_data', {}).get('timeframes', ['1h', '4h', '1d'])
            
            for timeframe in timeframes:
                try:
                    data = get_historical_data(
                        symbol=self.symbol,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if not data.empty and len(data) > 100:  # Mínimo 100 registros
                        logger.info(f"Cargados {len(data)} registros de {self.symbol}_{timeframe}")
                        return data
                        
                except Exception as e:
                    logger.warning(f"Error cargando {self.symbol}_{timeframe}: {e}")
                    continue
            
            # Si no se encontraron datos, generar sintéticos
            logger.warning(f"No se encontraron datos históricos para {self.symbol}")
            return self._generate_synthetic_data()
            
        except Exception as e:
            logger.error(f"Error cargando datos históricos: {e}")
            return self._generate_synthetic_data()
    
    def _migrate_csv_to_sqlite(self) -> pd.DataFrame:
        """Migra datos CSV a SQLite y los carga"""
        try:
            # Cargar datos CSV
            csv_data = pd.read_csv(self.data_path)
            
            # Convertir a OHLCVData
            from core.data.symbol_database_manager import OHLCVData
            from core.data.symbol_database_manager import symbol_db_manager
            
            ohlcv_data = []
            for _, row in csv_data.iterrows():
                try:
                    # Convertir timestamp
                    timestamp = row['timestamp']
                    if isinstance(timestamp, str):
                        timestamp = int(pd.to_datetime(timestamp).timestamp())
                    elif isinstance(timestamp, pd.Timestamp):
                        timestamp = int(timestamp.timestamp())
                    
                    ohlcv = OHLCVData(
                        timestamp=int(timestamp),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    ohlcv_data.append(ohlcv)
                except Exception as e:
                    logger.warning(f"Error procesando fila: {e}")
                    continue
            
            # Insertar en SQLite
            if ohlcv_data:
                # Determinar timeframe del nombre del archivo
                timeframe = '1h'  # Default
                if '_1m' in self.data_path:
                    timeframe = '1m'
                elif '_5m' in self.data_path:
                    timeframe = '5m'
                elif '_15m' in self.data_path:
                    timeframe = '15m'
                elif '_4h' in self.data_path:
                    timeframe = '4h'
                elif '_1d' in self.data_path:
                    timeframe = '1d'
                
                symbol_db_manager.insert_data(self.symbol, timeframe, ohlcv_data)
                logger.info(f"Migrados {len(ohlcv_data)} registros a SQLite")
            
            return csv_data
            
        except Exception as e:
            logger.error(f"Error migrando CSV: {e}")
            return pd.DataFrame()
    
    def _load_from_timescaledb(self) -> pd.DataFrame:
        """Carga datos desde TimescaleDB"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Configuración de conexión
            conn_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'trading_bot_enterprise',
                'user': 'trading_bot',
                'password': 'trading_bot_password'
            }
            
            with psycopg2.connect(**conn_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                    SELECT time, symbol, price, volume, bid, ask,
                           sma_10, sma_20, ema_12, ema_26, rsi_14, macd,
                           bollinger_upper, bollinger_lower
                    FROM market_ticks 
                    WHERE symbol = %s 
                    ORDER BY time DESC 
                    LIMIT 10000
                    """
                    cur.execute(query, (self.symbol,))
                    rows = cur.fetchall()
                    
                    if not rows:
                        logger.warning(f"No se encontraron datos para {self.symbol} en TimescaleDB")
                        return self._generate_synthetic_data()
                    
                    return pd.DataFrame(rows)
                    
        except Exception as e:
            logger.error(f"Error cargando datos desde TimescaleDB: {e}")
            return self._generate_synthetic_data()
    
    def _load_from_redis(self) -> pd.DataFrame:
        """Carga datos desde Redis"""
        try:
            import redis
            import json
            
            r = redis.Redis(host='localhost', port=6379, db=0)
            
            # Obtener datos del símbolo
            key_pattern = f"market_data:{self.symbol}:*"
            keys = r.keys(key_pattern)
            
            if not keys:
                logger.warning(f"No se encontraron datos para {self.symbol} en Redis")
                return self._generate_synthetic_data()
            
            data = []
            for key in keys[:1000]:  # Limitar a 1000 registros
                value = r.get(key)
                if value:
                    data.append(json.loads(value))
            
            if not data:
                return self._generate_synthetic_data()
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error cargando datos desde Redis: {e}")
            return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self) -> pd.DataFrame:
        """Genera datos sintéticos para testing"""
        logger.info(f"Generando datos sintéticos para {self.symbol}")
        
        np.random.seed(42)
        n_samples = 5000
        
        # Generar datos de precio
        base_price = 100.0
        returns = np.random.normal(0, 0.02, n_samples)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Generar OHLCV
        data = {
            'time': pd.date_range('2023-01-01', periods=n_samples, freq='1H'),
            'symbol': [self.symbol] * n_samples,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'volume': np.random.exponential(1000, n_samples),
        }
        
        # Generar features técnicos
        df = pd.DataFrame(data)
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['macd'] = df['ema_12'] - df['ema_26']
        df['bollinger_upper'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
        df['bollinger_lower'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
        
        # Rellenar NaN
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocesa los datos"""
        # Eliminar columnas no necesarias
        columns_to_keep = ['time'] + self.features
        available_columns = [col for col in columns_to_keep if col in data.columns]
        data = data[available_columns]
        
        # Ordenar por tiempo
        if 'time' in data.columns:
            data = data.sort_values('time').reset_index(drop=True)
        
        # Normalizar features numéricas
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col != 'time':
                data[col] = (data[col] - data[col].mean()) / data[col].std()
        
        # Rellenar valores faltantes
        data = data.fillna(method='bfill').fillna(method='ffill')
        
        return data
    
    def _create_target(self, data: pd.DataFrame) -> pd.DataFrame:
        """Crea la variable target para clasificación"""
        if 'close' not in data.columns:
            # Usar la primera columna numérica como precio
            price_col = data.select_dtypes(include=[np.number]).columns[0]
        else:
            price_col = 'close'
        
        # Calcular retornos futuros
        future_returns = data[price_col].shift(-self.prediction_horizon) / data[price_col] - 1
        
        # Crear target categórico: 0=SELL, 1=HOLD, 2=BUY
        data['target'] = 1  # HOLD por defecto
        data.loc[future_returns > 0.01, 'target'] = 2  # BUY si retorno > 1%
        data.loc[future_returns < -0.01, 'target'] = 0  # SELL si retorno < -1%
        
        return data
    
    def _save_processed_data(self, data: pd.DataFrame):
        """Guarda datos procesados"""
        processed_dir = Path("data/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar como parquet para mejor rendimiento
        filename = f"{self.symbol}_processed.parquet"
        filepath = processed_dir / filename
        data.to_parquet(filepath, index=False)
        
        logger.info(f"Datos procesados guardados en {filepath}")
    
    def setup(self, stage: Optional[str] = None):
        """Configura los datasets para cada etapa"""
        if stage == "fit" or stage is None:
            # Cargar datos procesados
            processed_file = Path(f"data/processed/{self.symbol}_processed.parquet")
            if processed_file.exists():
                data = pd.read_parquet(processed_file)
            else:
                # Preparar datos si no existen
                self.prepare_data()
                data = pd.read_parquet(processed_file)
            
            # Dividir datos
            train_size = int(len(data) * self.train_split)
            val_size = int(len(data) * self.val_split)
            
            train_data = data[:train_size]
            val_data = data[train_size:train_size + val_size]
            
            # Crear datasets
            self.train_dataset = TradingDataset(
                train_data, self.features, self.target_column,
                self.sequence_length, self.prediction_horizon
            )
            
            self.val_dataset = TradingDataset(
                val_data, self.features, self.target_column,
                self.sequence_length, self.prediction_horizon
            )
        
        if stage == "test" or stage is None:
            # Cargar datos procesados
            processed_file = Path(f"data/processed/{self.symbol}_processed.parquet")
            if processed_file.exists():
                data = pd.read_parquet(processed_file)
            else:
                self.prepare_data()
                data = pd.read_parquet(processed_file)
            
            # Usar últimos datos para test
            test_size = int(len(data) * self.test_split)
            test_data = data[-test_size:]
            
            self.test_dataset = TradingDataset(
                test_data, self.features, self.target_column,
                self.sequence_length, self.prediction_horizon
            )
    
    def train_dataloader(self) -> DataLoader:
        """DataLoader para entrenamiento"""
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=True if self.num_workers > 0 else False
        )
    
    def val_dataloader(self) -> DataLoader:
        """DataLoader para validación"""
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=True if self.num_workers > 0 else False
        )
    
    def test_dataloader(self) -> DataLoader:
        """DataLoader para testing"""
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            persistent_workers=True if self.num_workers > 0 else False
        )
