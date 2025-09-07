"""
trading/__init__.py
Módulo de Trading para el Trading Bot v10
Ubicación: C:\\TradingBot_v10\\trading\\__init__.py

Este módulo contiene toda la lógica de trading incluyendo:
- Motor principal de ejecución (executor.py)
- Gestión de riesgo (risk_manager.py)
- Gestión de órdenes (order_manager.py)
- Cliente de exchange (bitget_client.py)
- Engine de ejecución (execution_engine.py)
"""

from .executor import (
    TradingExecutor,
    trading_executor,
    execute_trading_cycle,
    start_trading,
    stop_trading,
    health_check,
    dry_run_cycle,
    get_performance_summary
)

from .risk_manager import (
    RiskManager,
    risk_manager
)

from .order_manager import (
    OrderManager,
    order_manager,
    TradeRecord
)

from .bitget_client import (
    BitgetClient,
    bitget_client
)

from .execution_engine import (
    ExecutionEngine,
    execution_engine
)

from .position_manager import (
    Position,
    PositionManager,
    position_manager
)

from .signal_processor import (
    SignalQuality,
    SignalProcessor,
    signal_processor
)

from .portfolio_optimizer import (
    PortfolioState,
    AllocationTarget,
    PortfolioOptimizer,
    portfolio_optimizer
)

__version__ = "1.0.0"
__author__ = "Trading Bot v10"

__all__ = [
    # Motor principal
    'TradingExecutor',
    'trading_executor',
    'execute_trading_cycle',
    'start_trading',
    'stop_trading',
    'health_check',
    'dry_run_cycle',
    'get_performance_summary',
    
    # Gestión de riesgo
    'RiskManager',
    'risk_manager',
    
    # Gestión de órdenes
    'OrderManager',
    'order_manager',
    'TradeRecord',
    
    # Cliente de exchange
    'BitgetClient',
    'bitget_client',
    
    # Engine de ejecución
    'ExecutionEngine',
    'execution_engine',
    
    # Gestión de posiciones
    'Position',
    'PositionManager',
    'position_manager',
    
    # Procesador de señales
    'SignalQuality',
    'SignalProcessor',
    'signal_processor',
    
    # Optimizador de portfolio
    'PortfolioState',
    'AllocationTarget',
    'PortfolioOptimizer',
    'portfolio_optimizer'
]
