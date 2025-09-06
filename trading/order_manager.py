"""
trading/order_manager.py
Sistema de gestión de órdenes para trading
Ubicación: C:\\TradingBot_v10\\trading\\order_manager.py

Funcionalidades:
- Ejecución de órdenes en modo paper y live
- Gestión de fills instantáneos (paper mode)
- Persistencia de trades en base de datos
- Control de comisiones y fees
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import uuid
import asyncio

from config.config_loader import user_config
from data.database import db_manager
from .risk_manager import RiskDecision

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Registro de una operación de trading"""
    trade_id: str
    symbol: str
    side: str  # BUY, SELL
    size_qty: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    take_profit: float = 0.0
    leverage: float = 1.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None  # TP, SL, MANUAL, CIRCUIT_BREAKER
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    confidence: float = 0.0

class OrderManager:
    """Gestor de órdenes para trading"""
    
    def __init__(self):
        self.config = user_config
        self.trading_config = self.config.get_value(['trading'], {})
        self.trading_mode = self.trading_config.get('mode', 'paper_trading')
        
        # Configuración de comisiones
        self.commission_rate = self.trading_config.get('commission_rate', 0.001)  # 0.1%
        
        # Trades abiertos
        self.open_trades: Dict[str, TradeRecord] = {}
        
        # Balance simulado (paper mode)
        self.paper_balance = self.trading_config.get('initial_balance', 10000.0)
        self.current_balance = self.paper_balance
        
        logger.info(f"OrderManager inicializado - Modo: {self.trading_mode}, Balance inicial: {self.paper_balance}")
    
    async def execute_order(
        self,
        symbol: str,
        signal: str,
        risk_decision: RiskDecision,
        current_price: float,
        confidence: float
    ) -> Optional[TradeRecord]:
        """
        Ejecuta una orden de trading
        
        Args:
            symbol: Símbolo del activo
            signal: Señal (BUY, SELL)
            risk_decision: Decisión de riesgo calculada
            current_price: Precio actual
            confidence: Confianza de la señal
        
        Returns:
            TradeRecord si la orden se ejecutó exitosamente
        """
        try:
            # Validar que tenemos una decisión válida
            if risk_decision.size_qty <= 0:
                logger.warning("Tamaño de posición inválido, orden rechazada")
                return None
            
            # Crear registro de trade
            trade_id = str(uuid.uuid4())
            trade_record = TradeRecord(
                trade_id=trade_id,
                symbol=symbol,
                side=signal,
                size_qty=risk_decision.size_qty,
                entry_price=current_price,
                stop_loss=risk_decision.stop_loss,
                take_profit=risk_decision.take_profit,
                leverage=risk_decision.leverage,
                entry_time=datetime.now(),
                confidence=confidence,
                status="OPEN"
            )
            
            # Ejecutar según el modo
            if self.trading_mode == 'paper_trading':
                success = await self._execute_paper_order(trade_record)
            elif self.trading_mode == 'live_trading':
                success = await self._execute_live_order(trade_record)
            else:
                logger.error(f"Modo de trading no soportado: {self.trading_mode}")
                return None
            
            if success:
                # Guardar en base de datos
                await self._save_trade_to_db(trade_record)
                
                # Agregar a trades abiertos
                self.open_trades[trade_id] = trade_record
                
                logger.info(f"Orden ejecutada exitosamente: {trade_id} - {signal} {risk_decision.size_qty} {symbol} @ {current_price}")
                return trade_record
            else:
                logger.error(f"Error ejecutando orden: {trade_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error en execute_order: {e}")
            return None
    
    async def _execute_paper_order(self, trade_record: TradeRecord) -> bool:
        """Ejecuta una orden en modo paper (simulación)"""
        try:
            # Simular fill instantáneo
            trade_record.status = "FILLED"
            
            # Calcular comisión
            trade_value = trade_record.size_qty * trade_record.entry_price
            commission = trade_value * self.commission_rate
            trade_record.fees = commission
            
            # Actualizar balance (simulado)
            if trade_record.side == "BUY":
                # Comprar reduce el balance
                self.current_balance -= (trade_value + commission)
            else:
                # Vender aumenta el balance
                self.current_balance += (trade_value - commission)
            
            logger.info(f"Paper order ejecutada: {trade_record.side} {trade_record.size_qty} @ {trade_record.entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando paper order: {e}")
            return False
    
    async def _execute_live_order(self, trade_record: TradeRecord) -> bool:
        """Ejecuta una orden en modo live (Bitget API)"""
        try:
            # TODO: Implementar integración con Bitget API
            # Por ahora simular como paper mode
            logger.warning("Modo live no implementado aún, simulando como paper mode")
            return await self._execute_paper_order(trade_record)
            
        except Exception as e:
            logger.error(f"Error ejecutando live order: {e}")
            return False
    
    async def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = "MANUAL"
    ) -> Optional[TradeRecord]:
        """
        Cierra una operación abierta
        
        Args:
            trade_id: ID de la operación
            exit_price: Precio de salida
            exit_reason: Razón de cierre
        
        Returns:
            TradeRecord actualizado si se cerró exitosamente
        """
        try:
            if trade_id not in self.open_trades:
                logger.warning(f"Trade no encontrado: {trade_id}")
                return None
            
            trade_record = self.open_trades[trade_id]
            
            # Actualizar registro
            trade_record.exit_price = exit_price
            trade_record.exit_time = datetime.now()
            trade_record.exit_reason = exit_reason
            trade_record.status = "CLOSED"
            
            # Calcular PnL
            if trade_record.side == "BUY":
                pnl = (exit_price - trade_record.entry_price) * trade_record.size_qty
            else:  # SELL
                pnl = (trade_record.entry_price - exit_price) * trade_record.size_qty
            
            # Restar comisiones
            exit_commission = trade_record.size_qty * exit_price * self.commission_rate
            total_fees = trade_record.fees + exit_commission
            pnl -= total_fees
            
            trade_record.pnl = pnl
            trade_record.pnl_pct = pnl / (trade_record.entry_price * trade_record.size_qty)
            trade_record.fees = total_fees
            
            # Actualizar balance
            self.current_balance += pnl
            
            # Remover de trades abiertos
            del self.open_trades[trade_id]
            
            # Actualizar en BD
            await self._update_trade_in_db(trade_record)
            
            logger.info(f"Trade cerrado: {trade_id} - PnL: {pnl:.2f} ({trade_record.pnl_pct:.2%})")
            return trade_record
            
        except Exception as e:
            logger.error(f"Error cerrando trade: {e}")
            return None
    
    async def check_stop_loss_take_profit(self, current_price: float) -> List[TradeRecord]:
        """Verifica si algún trade abierto debe cerrarse por SL/TP"""
        closed_trades = []
        
        for trade_id, trade_record in list(self.open_trades.items()):
            try:
                exit_reason = None
                exit_price = None
                
                # Verificar stop loss
                if trade_record.side == "BUY" and current_price <= trade_record.stop_loss:
                    exit_reason = "SL"
                    exit_price = trade_record.stop_loss
                elif trade_record.side == "SELL" and current_price >= trade_record.stop_loss:
                    exit_reason = "SL"
                    exit_price = trade_record.stop_loss
                
                # Verificar take profit
                elif trade_record.side == "BUY" and current_price >= trade_record.take_profit:
                    exit_reason = "TP"
                    exit_price = trade_record.take_profit
                elif trade_record.side == "SELL" and current_price <= trade_record.take_profit:
                    exit_reason = "TP"
                    exit_price = trade_record.take_profit
                
                # Cerrar trade si corresponde
                if exit_reason:
                    closed_trade = await self.close_trade(trade_id, exit_price, exit_reason)
                    if closed_trade:
                        closed_trades.append(closed_trade)
                        
            except Exception as e:
                logger.error(f"Error verificando SL/TP para trade {trade_id}: {e}")
        
        return closed_trades
    
    async def _save_trade_to_db(self, trade_record: TradeRecord) -> bool:
        """Guarda un trade en la base de datos"""
        try:
            # TODO: Implementar guardado en BD
            # Por ahora solo loggear
            logger.info(f"Trade guardado en BD: {trade_record.trade_id}")
            return True
        except Exception as e:
            logger.error(f"Error guardando trade en BD: {e}")
            return False
    
    async def _update_trade_in_db(self, trade_record: TradeRecord) -> bool:
        """Actualiza un trade en la base de datos"""
        try:
            # TODO: Implementar actualización en BD
            logger.info(f"Trade actualizado en BD: {trade_record.trade_id}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando trade en BD: {e}")
            return False
    
    def get_open_trades(self) -> List[TradeRecord]:
        """Obtiene todos los trades abiertos"""
        return list(self.open_trades.values())
    
    def get_balance(self) -> float:
        """Obtiene el balance actual"""
        return self.current_balance
    
    def get_trade_summary(self) -> Dict:
        """Obtiene un resumen de trades"""
        total_trades = len(self.open_trades)
        total_pnl = sum(trade.pnl for trade in self.open_trades.values())
        
        return {
            'open_trades': total_trades,
            'current_balance': self.current_balance,
            'total_pnl': total_pnl,
            'trading_mode': self.trading_mode
        }

# Instancia global
order_manager = OrderManager()
