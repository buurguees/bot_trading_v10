"""
config/settings.py
Configuración principal del sistema de trading autónomo
Ubicación: C:\TradingBot_v10\config\settings.py
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
MODELS_DIR = PROJECT_ROOT / "models" / "saved_models"
BACKUPS_DIR = PROJECT_ROOT / "backups"

# Crear directorios si no existen
for directory in [DATA_DIR, LOGS_DIR, MODELS_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Environment(Enum):
    """Entornos de ejecución del bot"""
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"

class LogLevel(Enum):
    """Niveles de logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    # SQLite para desarrollo
    sqlite_path: str = str(DATA_DIR / "trading_bot.db")
    
    # PostgreSQL para producción (futuro)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "trading_bot"
    postgres_user: str = os.getenv("POSTGRES_USER", "trading_bot")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Configuraciones generales
    connection_pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600

@dataclass
class BitgetConfig:
    """Configuración API de Bitget"""
    # Credenciales API (desde variables de entorno)
    api_key: str = os.getenv("BITGET_API_KEY", "")
    secret_key: str = os.getenv("BITGET_SECRET_KEY", "")
    passphrase: str = os.getenv("BITGET_PASSPHRASE", "")
    
    # URLs de API
    base_url: str = "https://api.bitget.com"
    websocket_url: str = "wss://ws.bitget.com/spot/v1/stream"
    
    # Configuraciones de conexión
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: int = 10
    
    # Configuraciones de trading
    default_symbol: str = "BTCUSDT"
    base_currency: str = "USDT"
    
    @property
    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas"""
        return bool(self.api_key and self.secret_key and self.passphrase)

@dataclass
class TradingConfig:
    """Configuración principal de trading"""
    # Símbolo principal
    symbol: str = "BTCUSDT"
    base_asset: str = "BTC"
    quote_asset: str = "USDT"
    
    # Capital y gestión de riesgo
    initial_balance: float = 1000.0
    max_position_size_pct: float = 0.02  # 2% del balance máximo por posición
    max_daily_loss_pct: float = 0.05     # 5% pérdida máxima diaria
    max_drawdown_pct: float = 0.15       # 15% drawdown máximo
    
    # Stop loss y take profit
    default_stop_loss_pct: float = 0.02   # 2% stop loss por defecto
    default_take_profit_pct: float = 0.04  # 4% take profit por defecto
    trailing_stop_activation: float = 0.01 # Activar trailing stop en 1% ganancia
    
    # Gestión de posiciones
    max_concurrent_positions: int = 3
    min_trade_interval_minutes: int = 5
    position_size_method: str = "kelly"  # kelly, fixed, volatility
    
    # Configuración de fees
    maker_fee: float = 0.001   # 0.1% maker fee
    taker_fee: float = 0.001   # 0.1% taker fee
    slippage_bps: int = 10     # 10 basis points de slippage estimado

@dataclass
class MLConfig:
    """Configuración del modelo de Machine Learning"""
    # Arquitectura de red
    model_type: str = "lstm_attention"
    lookback_window: int = 60           # Períodos históricos para input
    prediction_horizon: int = 1        # Períodos a predecir
    
    # Capas de la red neuronal
    lstm_units: List[int] = field(default_factory=lambda: [128, 64, 32])
    dense_units: List[int] = field(default_factory=lambda: [64, 32])
    dropout_rate: float = 0.2
    
    # Entrenamiento
    learning_rate: float = 0.001
    batch_size: int = 64
    epochs: int = 100
    early_stopping_patience: int = 10
    validation_split: float = 0.2
    
    # Reentrenamiento
    retrain_frequency: int = 100        # Cada 100 trades
    min_trades_before_retrain: int = 50
    retrain_performance_threshold: float = 0.6  # Precisión mínima para usar modelo
    
    # Features
    technical_indicators: List[str] = field(default_factory=lambda: [
        "sma_20", "sma_50", "ema_12", "ema_26",
        "rsi_14", "macd", "bollinger_upper", "bollinger_lower",
        "atr_14", "volume_sma_20", "stoch_k", "stoch_d"
    ])
    
    # Confidence threshold para trading
    min_confidence_threshold: float = 0.65
    
    @property
    def input_shape(self) -> tuple:
        """Forma del input para la red neuronal"""
        feature_count = len(self.technical_indicators) + 5  # OHLCV
        return (self.lookback_window, feature_count)

@dataclass
class MonitoringConfig:
    """Configuración de monitoreo y alertas"""
    # Dashboard web
    dashboard_enabled: bool = True
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8050
    
    # Métricas de performance
    performance_check_interval: int = 3600  # Cada hora
    health_check_interval: int = 300        # Cada 5 minutos
    
    # Alertas
    email_alerts_enabled: bool = False
    telegram_alerts_enabled: bool = False
    discord_alerts_enabled: bool = False
    
    # Thresholds para alertas
    drawdown_alert_threshold: float = 0.10   # Alerta en 10% drawdown
    loss_streak_alert: int = 5               # Alerta tras 5 pérdidas consecutivas
    api_error_alert_threshold: int = 10      # Alerta tras 10 errores de API
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_to_file: bool = True
    log_to_console: bool = True
    max_log_file_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

@dataclass
class BacktestingConfig:
    """Configuración para backtesting"""
    # Datos históricos
    start_date: str = "2022-01-01"
    end_date: str = "2024-12-31"
    timeframe: str = "1h"
    
    # Motor de backtesting
    initial_capital: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0001
    
    # Walk-forward analysis
    train_period_months: int = 6
    test_period_months: int = 1
    rebalance_frequency: str = "monthly"
    
    # Métricas a calcular
    benchmark_symbol: str = "BTCUSDT"
    risk_free_rate: float = 0.02  # 2% anual

class GlobalConfig:
    """Configuración global del sistema"""
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.database = DatabaseConfig()
        self.bitget = BitgetConfig()
        self.trading = TradingConfig()
        self.ml = MLConfig()
        self.monitoring = MonitoringConfig()
        self.backtesting = BacktestingConfig()
        
        # Ajustar configuraciones según entorno
        self._adjust_for_environment()
    
    def _adjust_for_environment(self):
        """Ajusta configuraciones según el entorno"""
        if self.environment == Environment.DEVELOPMENT:
            self.trading.initial_balance = 1000.0
            self.monitoring.log_level = LogLevel.DEBUG
            self.ml.epochs = 50  # Menos epochs en desarrollo
            
        elif self.environment == Environment.BACKTESTING:
            self.trading.initial_balance = 10000.0
            self.monitoring.log_level = LogLevel.INFO
            self.monitoring.dashboard_enabled = False
            
        elif self.environment == Environment.PAPER_TRADING:
            self.trading.initial_balance = 5000.0
            self.monitoring.log_level = LogLevel.INFO
            self.monitoring.dashboard_enabled = True
            
        elif self.environment == Environment.LIVE_TRADING:
            # Configuración más conservadora para trading real
            self.trading.max_position_size_pct = 0.01  # 1% máximo
            self.trading.max_daily_loss_pct = 0.03     # 3% pérdida máxima
            self.trading.max_drawdown_pct = 0.10       # 10% drawdown máximo
            self.monitoring.log_level = LogLevel.WARNING
            self.monitoring.dashboard_enabled = True
            # Activar todas las alertas
            self.monitoring.email_alerts_enabled = True
            self.monitoring.telegram_alerts_enabled = True
    
    def validate_config(self) -> List[str]:
        """Valida la configuración y retorna lista de errores"""
        errors = []
        
        # Validar credenciales de Bitget
        if not self.bitget.is_configured:
            errors.append("Credenciales de Bitget no configuradas")
        
        # Validar configuraciones de trading
        if self.trading.max_position_size_pct <= 0 or self.trading.max_position_size_pct > 1:
            errors.append("max_position_size_pct debe estar entre 0 y 1")
        
        if self.trading.max_daily_loss_pct <= 0 or self.trading.max_daily_loss_pct > 1:
            errors.append("max_daily_loss_pct debe estar entre 0 y 1")
        
        # Validar configuraciones de ML
        if self.ml.lookback_window < 10:
            errors.append("lookback_window debe ser al menos 10")
        
        if self.ml.min_confidence_threshold < 0.5 or self.ml.min_confidence_threshold > 1:
            errors.append("min_confidence_threshold debe estar entre 0.5 y 1")
        
        return errors
    
    def to_dict(self) -> Dict:
        """Convierte la configuración a diccionario"""
        return {
            "environment": self.environment.value,
            "database": self.database.__dict__,
            "bitget": {k: v for k, v in self.bitget.__dict__.items() if k not in ["api_key", "secret_key", "passphrase"]},
            "trading": self.trading.__dict__,
            "ml": self.ml.__dict__,
            "monitoring": self.monitoring.__dict__,
            "backtesting": self.backtesting.__dict__
        }

# Instancia global de configuración
config = GlobalConfig()

# Configurar logging básico
def setup_logging():
    """Configura el sistema de logging"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurar logging a archivo
    if config.monitoring.log_to_file:
        log_file = LOGS_DIR / f"trading_bot_{config.environment.value}.log"
        logging.basicConfig(
            level=getattr(logging, config.monitoring.log_level.value),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if config.monitoring.log_to_console else logging.NullHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, config.monitoring.log_level.value),
            format=log_format
        )

# Configurar logging al importar
setup_logging()

# Logger para este módulo
logger = logging.getLogger(__name__)
logger.info(f"Configuración inicializada para entorno: {config.environment.value}")