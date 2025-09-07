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
    risk_manager,
    calculate_position_size,
    check_risk_limits,
    get_risk_metrics
)

from .order_manager import (
    OrderManager,
    order_manager,
    TradeRecord,
    execute_order,
    close_trade,
    get_balance,
    get_trade_history
)

from .bitget_client import (
    BitgetClient,
    bitget_client,
    fetch_ohlcv,
    fetch_balance,
    health_check as bitget_health_check
)

from .execution_engine import (
    ExecutionEngine,
    execution_engine,
    route_signal,
    check_open_trades,
    get_execution_summary
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
    'calculate_position_size',
    'check_risk_limits',
    'get_risk_metrics',
    
    # Gestión de órdenes
    'OrderManager',
    'order_manager',
    'TradeRecord',
    'execute_order',
    'close_trade',
    'get_balance',
    'get_trade_history',
    
    # Cliente de exchange
    'BitgetClient',
    'bitget_client',
    'fetch_ohlcv',
    'fetch_balance',
    'bitget_health_check',
    
    # Engine de ejecución
    'ExecutionEngine',
    'execution_engine',
    'route_signal',
    'check_open_trades',
    'get_execution_summary'
]
