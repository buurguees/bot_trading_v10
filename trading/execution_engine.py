"""
trading/execution_engine.py
Motor de ejecución de señales de trading
Ubicación: C:\\TradingBot_v10\\trading\\execution_engine.py

Funcionalidades:
- Enrutamiento de señales de trading
- Control de duplicados y circuit breakers
- Integración con risk_manager y order_manager
- Validación de señales antes de ejecución
"""

import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict

from config.config_loader import user_config
from .risk_manager import risk_manager, RiskDecision
from .order_manager import order_manager, TradeRecord

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Motor de ejecución de señales de trading"""
    
    def __init__(self):
        self.config = user_config
        self.trading_config = self.config.get_value(['trading'], {})
        
        # Configuración de ejecución
        self.min_confidence = self.trading_config.get('min_confidence', 0.6)  # 60% mínimo
        self.max_trades_per_bar = self.trading_config.get('max_trades_per_bar', 1)
        self.circuit_breaker_loss = self.trading_config.get('circuit_breaker_loss', 0.05)  # 5%
        
        # Control de duplicados
        self.last_signals = {}  # {symbol: (signal, timestamp)}
        self.trades_per_bar = defaultdict(int)  # {symbol: count}
        self.current_bar = None
        
        # Circuit breakers
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"ExecutionEngine inicializado - Confianza mínima: {self.min_confidence}")
    
    async def route_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        current_price: float,
        atr: float,
        balance: float,
        bar_timestamp: datetime
    ) -> Optional[TradeRecord]:
        """
        Enruta una señal de trading para ejecución
        
        Args:
            symbol: Símbolo del activo
            signal: Señal (BUY, SELL, HOLD)
            confidence: Confianza de la señal (0-1)
            current_price: Precio actual
            atr: Average True Range
            balance: Balance disponible
            bar_timestamp: Timestamp de la barra actual
        
        Returns:
            TradeRecord si la señal se ejecutó
        """
        try:
            # Verificar circuit breakers
            if not await self._check_circuit_breakers(balance):
                logger.warning("Circuit breaker activado, señal rechazada")
                return None
            
            # Verificar duplicados
            if not self._check_duplicate_signal(symbol, signal, bar_timestamp):
                logger.warning(f"Señal duplicada rechazada: {symbol} {signal}")
                return None
            
            # Validar señal
            if not risk_manager.validate_signal(signal, confidence):
                logger.warning(f"Señal inválida: {signal} (confianza: {confidence:.2%})")
                return None
            
            # Verificar confianza mínima
            if confidence < self.min_confidence:
                logger.warning(f"Confianza insuficiente: {confidence:.2%} < {self.min_confidence:.2%}")
                return None
            
            # Calcular decisión de riesgo
            risk_decision = risk_manager.calculate_position_size(
                current_price=current_price,
                atr=atr,
                balance=balance,
                stop_loss_pct=0.02,  # 2% por defecto
                confidence=confidence
            )
            
            # Verificar que la decisión es válida
            if risk_decision.size_qty <= 0:
                logger.warning("Decisión de riesgo inválida, señal rechazada")
                return None
            
            # Ejecutar orden
            trade_record = await order_manager.execute_order(
                symbol=symbol,
                signal=signal,
                risk_decision=risk_decision,
                current_price=current_price,
                confidence=confidence
            )
            
            if trade_record:
                # Actualizar controles
                self.last_signals[symbol] = (signal, bar_timestamp)
                self.trades_per_bar[symbol] += 1
                self.current_bar = bar_timestamp
                
                logger.info(f"Señal ejecutada: {symbol} {signal} - Trade ID: {trade_record.trade_id}")
                return trade_record
            else:
                logger.error(f"Error ejecutando señal: {symbol} {signal}")
                return None
                
        except Exception as e:
            logger.error(f"Error en route_signal: {e}")
            return None
    
    def _check_duplicate_signal(
        self,
        symbol: str,
        signal: str,
        bar_timestamp: datetime
    ) -> bool:
        """Verifica si la señal es duplicada"""
        try:
            # Verificar si es la misma barra
            if self.current_bar and bar_timestamp == self.current_bar:
                # Verificar límite de trades por barra
                if self.trades_per_bar[symbol] >= self.max_trades_per_bar:
                    return False
                
                # Verificar si es la misma señal
                if symbol in self.last_signals:
                    last_signal, last_timestamp = self.last_signals[symbol]
                    if last_signal == signal and last_timestamp == bar_timestamp:
                        return False
            
            # Resetear contador si es nueva barra
            if not self.current_bar or bar_timestamp != self.current_bar:
                self.trades_per_bar.clear()
                self.current_bar = bar_timestamp
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando duplicados: {e}")
            return False
    
    async def _check_circuit_breakers(self, balance: float) -> bool:
        """Verifica circuit breakers"""
        try:
            # Resetear pérdidas diarias si es nuevo día
            today = datetime.now().date()
            if today != self.last_reset_date:
                self.daily_loss = 0.0
                self.last_reset_date = today
            
            # Verificar pérdida diaria máxima
            max_daily_loss = balance * self.circuit_breaker_loss
            if self.daily_loss >= max_daily_loss:
                logger.warning(f"Circuit breaker activado por pérdida diaria: {self.daily_loss:.2f} >= {max_daily_loss:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando circuit breakers: {e}")
            return False
    
    async def update_daily_loss(self, pnl: float):
        """Actualiza la pérdida diaria para circuit breakers"""
        if pnl < 0:
            self.daily_loss += abs(pnl)
            logger.info(f"Pérdida diaria actualizada: {self.daily_loss:.2f}")
    
    async def check_open_trades(self, current_price: float) -> List[TradeRecord]:
        """Verifica trades abiertos para SL/TP"""
        try:
            closed_trades = await order_manager.check_stop_loss_take_profit(current_price)
            
            # Actualizar pérdida diaria
            for trade in closed_trades:
                if trade.pnl < 0:
                    await self.update_daily_loss(trade.pnl)
            
            return closed_trades
            
        except Exception as e:
            logger.error(f"Error verificando trades abiertos: {e}")
            return []
    
    def get_execution_summary(self) -> Dict:
        """Obtiene un resumen del estado de ejecución"""
        return {
            'min_confidence': self.min_confidence,
            'max_trades_per_bar': self.max_trades_per_bar,
            'circuit_breaker_loss': self.circuit_breaker_loss,
            'daily_loss': self.daily_loss,
            'open_trades': len(order_manager.get_open_trades()),
            'current_balance': order_manager.get_balance()
        }
    
    def reset_daily_counters(self):
        """Resetea contadores diarios"""
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        self.trades_per_bar.clear()
        logger.info("Contadores diarios reseteados")

# Instancia global
execution_engine = ExecutionEngine()
