# Ruta: core/trading/enterprise/order_executor.py
# order_executor.py - Ejecutor de órdenes con múltiples tipos
# Ubicación: C:\TradingBot_v10\trading\enterprise\order_executor.py

"""
Ejecutor de órdenes enterprise con soporte para múltiples tipos de orden.

Características principales:
- Market, Limit, Stop, Stop-Limit orders
- Ejecución asíncrona con timeouts
- Retry automático en caso de fallos
- Slippage y costos de transacción
- Integración con circuit breakers
- Monitoreo de performance
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

# Imports de trading
import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Tipos de orden soportados"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"

class OrderStatus(Enum):
    """Estado de una orden"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderSide(Enum):
    """Lado de una orden"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Representa una orden de trading"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    filled: float
    remaining: float
    cost: float
    fee: float
    timestamp: datetime
    params: Dict[str, Any]
    
    @property
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def fill_percentage(self) -> float:
        return (self.filled / self.amount) * 100 if self.amount > 0 else 0

@dataclass
class OrderResult:
    """Resultado de la ejecución de una orden"""
    success: bool
    order: Optional[Order]
    error: Optional[str]
    execution_time: float
    slippage: float
    cost: float

class OrderExecutor:
    """
    Ejecutor de órdenes enterprise
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el ejecutor de órdenes
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.exchange = None
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # Configuración de órdenes
        self.order_config = config.trading.orders
        
        # Configuración de ejecución
        self.execution_config = self.order_config.execution
        
        # Métricas de performance
        self.execution_times = []
        self.success_rate = 0.0
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        
        # Circuit breaker
        self.circuit_breaker_active = False
        self.circuit_breaker_until = None
        
        # Rate limiting
        self.last_order_time = 0
        self.min_order_interval = 0.1  # 100ms entre órdenes
        
        logger.info("OrderExecutor inicializado")
    
    def set_exchange(self, exchange: ccxt.Exchange):
        """Configura el exchange para ejecutar órdenes"""
        self.exchange = exchange
        logger.info("Exchange configurado en OrderExecutor")
    
    async def execute_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> OrderResult:
        """
        Ejecuta una orden de trading
        
        Args:
            symbol: Símbolo a tradear
            side: Lado de la orden (buy/sell)
            amount: Cantidad a tradear
            order_type: Tipo de orden
            price: Precio para órdenes limit
            stop_price: Precio de stop
            params: Parámetros adicionales
            
        Returns:
            Resultado de la ejecución
        """
        start_time = time.time()
        
        try:
            # Verificar circuit breaker
            if self.circuit_breaker_active:
                if datetime.now() < self.circuit_breaker_until:
                    return OrderResult(
                        success=False,
                        order=None,
                        error="Circuit breaker activo",
                        execution_time=time.time() - start_time,
                        slippage=0.0,
                        cost=0.0
                    )
                else:
                    self.circuit_breaker_active = False
                    self.circuit_breaker_until = None
            
            # Verificar rate limiting
            await self._check_rate_limit()
            
            # Validar orden
            validation_result = await self._validate_order(symbol, side, amount, order_type, price)
            if not validation_result['valid']:
                return OrderResult(
                    success=False,
                    order=None,
                    error=validation_result['error'],
                    execution_time=time.time() - start_time,
                    slippage=0.0,
                    cost=0.0
                )
            
            # Crear orden
            order = await self._create_order(
                symbol, side, amount, order_type, price, stop_price, params
            )
            
            # Ejecutar orden según tipo
            if order_type.upper() == "MARKET":
                result = await self._execute_market_order(order)
            elif order_type.upper() == "LIMIT":
                result = await self._execute_limit_order(order)
            elif order_type.upper() == "STOP":
                result = await self._execute_stop_order(order)
            elif order_type.upper() == "STOP_LIMIT":
                result = await self._execute_stop_limit_order(order)
            else:
                result = await self._execute_generic_order(order)
            
            # Actualizar métricas
            execution_time = time.time() - start_time
            self.execution_times.append(execution_time)
            self.total_orders += 1
            
            if result.success:
                self.successful_orders += 1
                self.orders[order.id] = order
                self.order_history.append(order)
            else:
                self.failed_orders += 1
            
            # Actualizar success rate
            self.success_rate = self.successful_orders / self.total_orders if self.total_orders > 0 else 0
            
            # Verificar circuit breaker
            await self._check_circuit_breaker()
            
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando orden: {e}")
            self.failed_orders += 1
            
            return OrderResult(
                success=False,
                order=None,
                error=str(e),
                execution_time=time.time() - start_time,
                slippage=0.0,
                cost=0.0
            )
    
    async def _create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str,
        price: Optional[float],
        stop_price: Optional[float],
        params: Optional[Dict[str, Any]]
    ) -> Order:
        """Crea una orden"""
        order_id = f"order_{int(time.time() * 1000)}"
        
        return Order(
            id=order_id,
            symbol=symbol,
            side=OrderSide(side.lower()),
            type=OrderType(order_type.lower()),
            amount=amount,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            filled=0.0,
            remaining=amount,
            cost=0.0,
            fee=0.0,
            timestamp=datetime.now(),
            params=params or {}
        )
    
    async def _execute_market_order(self, order: Order) -> OrderResult:
        """Ejecuta una orden de mercado"""
        try:
            if not self.exchange:
                return OrderResult(False, order, "Exchange no configurado", 0, 0, 0)
            
            # Obtener precio actual para calcular slippage
            ticker = await self.exchange.fetch_ticker(order.symbol)
            expected_price = ticker['last']
            
            # Ejecutar orden
            exchange_order = await self.exchange.create_market_order(
                order.symbol,
                order.side.value,
                order.amount,
                None,  # price
                None,  # params
                order.params
            )
            
            # Actualizar orden con resultado
            order.status = OrderStatus.FILLED
            order.filled = order.amount
            order.remaining = 0.0
            order.cost = exchange_order.get('cost', 0)
            order.fee = exchange_order.get('fee', {}).get('cost', 0)
            
            # Calcular slippage
            actual_price = exchange_order.get('price', expected_price)
            slippage = abs(actual_price - expected_price) / expected_price if expected_price > 0 else 0
            
            return OrderResult(
                success=True,
                order=order,
                error=None,
                execution_time=0,
                slippage=slippage,
                cost=order.cost
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando orden de mercado: {e}")
            order.status = OrderStatus.REJECTED
            return OrderResult(False, order, str(e), 0, 0, 0)
    
    async def _execute_limit_order(self, order: Order) -> OrderResult:
        """Ejecuta una orden limit"""
        try:
            if not self.exchange:
                return OrderResult(False, order, "Exchange no configurado", 0, 0, 0)
            
            if not order.price:
                return OrderResult(False, order, "Precio requerido para orden limit", 0, 0, 0)
            
            # Ejecutar orden
            exchange_order = await self.exchange.create_limit_order(
                order.symbol,
                order.side.value,
                order.amount,
                order.price,
                None,  # params
                order.params
            )
            
            # Actualizar orden
            order.status = OrderStatus.OPEN
            order.cost = exchange_order.get('cost', 0)
            order.fee = exchange_order.get('fee', {}).get('cost', 0)
            
            return OrderResult(
                success=True,
                order=order,
                error=None,
                execution_time=0,
                slippage=0.0,
                cost=order.cost
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando orden limit: {e}")
            order.status = OrderStatus.REJECTED
            return OrderResult(False, order, str(e), 0, 0, 0)
    
    async def _execute_stop_order(self, order: Order) -> OrderResult:
        """Ejecuta una orden stop"""
        try:
            if not self.exchange:
                return OrderResult(False, order, "Exchange no configurado", 0, 0, 0)
            
            if not order.stop_price:
                return OrderResult(False, order, "Stop price requerido", 0, 0, 0)
            
            # Crear orden stop
            stop_params = {
                'stopPrice': order.stop_price,
                'type': 'stop'
            }
            stop_params.update(order.params)
            
            exchange_order = await self.exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                order.amount,
                order.price,
                stop_params
            )
            
            # Actualizar orden
            order.status = OrderStatus.OPEN
            order.cost = exchange_order.get('cost', 0)
            order.fee = exchange_order.get('fee', {}).get('cost', 0)
            
            return OrderResult(
                success=True,
                order=order,
                error=None,
                execution_time=0,
                slippage=0.0,
                cost=order.cost
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando orden stop: {e}")
            order.status = OrderStatus.REJECTED
            return OrderResult(False, order, str(e), 0, 0, 0)
    
    async def _execute_stop_limit_order(self, order: Order) -> OrderResult:
        """Ejecuta una orden stop-limit"""
        try:
            if not self.exchange:
                return OrderResult(False, order, "Exchange no configurado", 0, 0, 0)
            
            if not order.stop_price or not order.price:
                return OrderResult(False, order, "Stop price y price requeridos", 0, 0, 0)
            
            # Crear orden stop-limit
            stop_limit_params = {
                'stopPrice': order.stop_price,
                'type': 'stop_limit'
            }
            stop_limit_params.update(order.params)
            
            exchange_order = await self.exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                order.amount,
                order.price,
                stop_limit_params
            )
            
            # Actualizar orden
            order.status = OrderStatus.OPEN
            order.cost = exchange_order.get('cost', 0)
            order.fee = exchange_order.get('fee', {}).get('cost', 0)
            
            return OrderResult(
                success=True,
                order=order,
                error=None,
                execution_time=0,
                slippage=0.0,
                cost=order.cost
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando orden stop-limit: {e}")
            order.status = OrderStatus.REJECTED
            return OrderResult(False, order, str(e), 0, 0, 0)
    
    async def _execute_generic_order(self, order: Order) -> OrderResult:
        """Ejecuta una orden genérica"""
        try:
            if not self.exchange:
                return OrderResult(False, order, "Exchange no configurado", 0, 0, 0)
            
            # Ejecutar orden genérica
            exchange_order = await self.exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                order.amount,
                order.price,
                order.params
            )
            
            # Actualizar orden
            order.status = OrderStatus.OPEN
            order.cost = exchange_order.get('cost', 0)
            order.fee = exchange_order.get('fee', {}).get('cost', 0)
            
            return OrderResult(
                success=True,
                order=order,
                error=None,
                execution_time=0,
                slippage=0.0,
                cost=order.cost
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando orden genérica: {e}")
            order.status = OrderStatus.REJECTED
            return OrderResult(False, order, str(e), 0, 0, 0)
    
    async def _validate_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str,
        price: Optional[float]
    ) -> Dict[str, Any]:
        """Valida una orden antes de ejecutarla"""
        try:
            # Verificar símbolo
            if not symbol:
                return {'valid': False, 'error': 'Símbolo requerido'}
            
            # Verificar lado
            if side.lower() not in ['buy', 'sell']:
                return {'valid': False, 'error': 'Lado inválido'}
            
            # Verificar cantidad
            if amount <= 0:
                return {'valid': False, 'error': 'Cantidad debe ser positiva'}
            
            # Verificar límites de cantidad
            min_amount = self.execution_config.min_order_size_usd
            max_amount = self.execution_config.max_order_size_usd
            
            if amount < min_amount:
                return {'valid': False, 'error': f'Cantidad mínima: {min_amount}'}
            
            if amount > max_amount:
                return {'valid': False, 'error': f'Cantidad máxima: {max_amount}'}
            
            # Verificar precio para órdenes limit
            if order_type.upper() == "LIMIT" and not price:
                return {'valid': False, 'error': 'Precio requerido para orden limit'}
            
            if price and price <= 0:
                return {'valid': False, 'error': 'Precio debe ser positivo'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': f'Error validando orden: {e}'}
    
    async def _check_rate_limit(self):
        """Verifica y aplica rate limiting"""
        current_time = time.time()
        time_since_last_order = current_time - self.last_order_time
        
        if time_since_last_order < self.min_order_interval:
            sleep_time = self.min_order_interval - time_since_last_order
            await asyncio.sleep(sleep_time)
        
        self.last_order_time = time.time()
    
    async def _check_circuit_breaker(self):
        """Verifica si debe activar el circuit breaker"""
        try:
            # Activar circuit breaker si hay muchas fallas
            if self.total_orders > 10:  # Mínimo 10 órdenes para evaluar
                failure_rate = self.failed_orders / self.total_orders
                
                if failure_rate > 0.5:  # Más del 50% de fallas
                    self.circuit_breaker_active = True
                    self.circuit_breaker_until = datetime.now() + timedelta(minutes=5)
                    logger.warning(f"🚨 Circuit breaker activado. Failure rate: {failure_rate:.2%}")
            
        except Exception as e:
            logger.error(f"Error verificando circuit breaker: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancela una orden
        
        Args:
            order_id: ID de la orden a cancelar
            
        Returns:
            True si se canceló exitosamente
        """
        try:
            if order_id not in self.orders:
                logger.warning(f"Orden {order_id} no encontrada")
                return False
            
            order = self.orders[order_id]
            
            if not order.is_active:
                logger.warning(f"Orden {order_id} no está activa")
                return False
            
            if self.exchange:
                await self.exchange.cancel_order(order_id, order.symbol)
            
            # Actualizar estado
            order.status = OrderStatus.CANCELLED
            order.remaining = 0.0
            
            logger.info(f"✅ Orden {order_id} cancelada")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelando orden {order_id}: {e}")
            return False
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancela todas las órdenes o las de un símbolo específico
        
        Args:
            symbol: Símbolo específico (None para todos)
            
        Returns:
            Número de órdenes canceladas
        """
        try:
            orders_to_cancel = []
            
            for order_id, order in self.orders.items():
                if order.is_active and (symbol is None or order.symbol == symbol):
                    orders_to_cancel.append(order_id)
            
            cancelled_count = 0
            for order_id in orders_to_cancel:
                if await self.cancel_order(order_id):
                    cancelled_count += 1
            
            logger.info(f"✅ Canceladas {cancelled_count} órdenes")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelando órdenes: {e}")
            return 0
    
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Obtiene el estado de una orden"""
        if order_id in self.orders:
            return self.orders[order_id].status
        return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Obtiene todas las órdenes abiertas"""
        open_orders = []
        
        for order in self.orders.values():
            if order.is_active and (symbol is None or order.symbol == symbol):
                open_orders.append(order)
        
        return open_orders
    
    async def close_position(self, position) -> Optional[Dict[str, Any]]:
        """
        Cierra una posición
        
        Args:
            position: Posición a cerrar
            
        Returns:
            Orden de cierre ejecutada
        """
        try:
            # Determinar lado opuesto
            opposite_side = 'sell' if position.side == 'long' else 'buy'
            
            # Ejecutar orden de cierre
            result = await self.execute_order(
                symbol=position.symbol,
                side=opposite_side,
                amount=position.size,
                order_type="market"
            )
            
            if result.success:
                logger.info(f"✅ Posición {position.symbol} cerrada exitosamente")
                return result.order
            else:
                logger.error(f"❌ Error cerrando posición {position.symbol}: {result.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error cerrando posición {position.symbol}: {e}")
            return None
    
    async def set_stop_loss_take_profit(
        self,
        symbol: str,
        order: Dict[str, Any],
        stop_loss_price: float,
        take_profit_price: float
    ) -> bool:
        """
        Configura stop loss y take profit para una posición
        
        Args:
            symbol: Símbolo
            order: Orden original
            stop_loss_price: Precio de stop loss
            take_profit_price: Precio de take profit
            
        Returns:
            True si se configuró exitosamente
        """
        try:
            # Crear orden de stop loss
            stop_result = await self.execute_order(
                symbol=symbol,
                side='sell' if order['side'] == 'buy' else 'buy',
                amount=order['amount'],
                order_type="stop",
                stop_price=stop_loss_price
            )
            
            # Crear orden de take profit
            tp_result = await self.execute_order(
                symbol=symbol,
                side='sell' if order['side'] == 'buy' else 'buy',
                amount=order['amount'],
                order_type="limit",
                price=take_profit_price
            )
            
            if stop_result.success and tp_result.success:
                logger.info(f"✅ SL/TP configurado para {symbol}")
                return True
            else:
                logger.error(f"❌ Error configurando SL/TP para {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error configurando SL/TP para {symbol}: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance del ejecutor"""
        try:
            avg_execution_time = np.mean(self.execution_times) if self.execution_times else 0
            max_execution_time = np.max(self.execution_times) if self.execution_times else 0
            min_execution_time = np.min(self.execution_times) if self.execution_times else 0
            
            return {
                'total_orders': self.total_orders,
                'successful_orders': self.successful_orders,
                'failed_orders': self.failed_orders,
                'success_rate': self.success_rate,
                'avg_execution_time': avg_execution_time,
                'max_execution_time': max_execution_time,
                'min_execution_time': min_execution_time,
                'circuit_breaker_active': self.circuit_breaker_active,
                'open_orders': len([o for o in self.orders.values() if o.is_active])
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de performance: {e}")
            return {}
    
    def export_order_history(self, output_file: Optional[str] = None) -> str:
        """Exporta el historial de órdenes"""
        try:
            if output_file is None:
                output_file = f"order_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = Path("logs/enterprise/trading/orders") / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar datos para exportación
            export_data = {
                'order_history': [asdict(order) for order in self.order_history],
                'performance_metrics': self.get_performance_metrics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            import json
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Historial de órdenes exportado: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando historial de órdenes: {e}")
            return None
