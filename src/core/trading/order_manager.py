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
import ccxt
import os

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
        
        # Cliente Bitget para modo live
        self.bitget_client = None
        self._initialize_bitget_client()
        
        logger.info(f"OrderManager inicializado - Modo: {self.trading_mode}, Balance inicial: {self.paper_balance}")
    
    def _initialize_bitget_client(self):
        """Inicializa el cliente de Bitget para trading live"""
        try:
            if self.trading_mode == 'live_trading':
                # Obtener credenciales del .env
                api_key = os.getenv('BITGET_API_KEY')
                secret_key = os.getenv('BITGET_SECRET_KEY')
                passphrase = os.getenv('BITGET_PASSPHRASE', '')
                
                if not api_key or not secret_key:
                    logger.error("Credenciales de Bitget no configuradas para modo live")
                    return
                
                # Crear cliente Bitget
                self.bitget_client = ccxt.bitget({
                    'apiKey': api_key,
                    'secret': secret_key,
                    'password': passphrase,
                    'sandbox': False,  # True para testnet
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'swap',  # Para futuros
                    }
                })
                
                logger.info("Cliente Bitget inicializado para trading live")
            else:
                logger.info("Modo paper trading - Cliente Bitget no inicializado")
                
        except Exception as e:
            logger.error(f"Error inicializando cliente Bitget: {e}")
            self.bitget_client = None
    
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
            if not self.bitget_client:
                logger.error("Cliente Bitget no inicializado")
                return False
            
            # Preparar parámetros de la orden
            symbol = trade_record.symbol
            side = 'buy' if trade_record.side == 'BUY' else 'sell'
            amount = trade_record.size_qty
            price = trade_record.entry_price
            
            # Generar clientOrderId único para idempotencia
            client_order_id = f"bot_{trade_record.trade_id}"
            
            # Crear orden en Bitget
            order_params = {
                'symbol': symbol,
                'type': 'limit',  # Orden limitada
                'side': side,
                'amount': amount,
                'price': price,
                'clientOrderId': client_order_id,
                'timeInForce': 'GTC',  # Good Till Cancelled
            }
            
            # Ejecutar orden
            logger.info(f"Enviando orden a Bitget: {order_params}")
            order = self.bitget_client.create_order(**order_params)
            
            if order and order.get('id'):
                # Orden creada exitosamente
                trade_record.status = "FILLED"
                trade_record.trade_id = order['id']  # Usar ID real de Bitget
                
                # Calcular comisiones reales
                trade_value = trade_record.size_qty * trade_record.entry_price
                commission = trade_value * self.commission_rate
                trade_record.fees = commission
                
                logger.info(f"Orden live ejecutada: {order['id']} - {side} {amount} {symbol} @ {price}")
                return True
            else:
                logger.error(f"Error creando orden en Bitget: {order}")
                return False
                
        except ccxt.InsufficientFunds as e:
            logger.error(f"Fondos insuficientes para la orden: {e}")
            return False
        except ccxt.InvalidOrder as e:
            logger.error(f"Orden inválida: {e}")
            return False
        except ccxt.NetworkError as e:
            logger.error(f"Error de red con Bitget: {e}")
            return False
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
            # Crear query SQL para insertar trade
            query = """
            INSERT INTO trades (
                trade_id, symbol, side, size_qty, entry_price, exit_price,
                stop_loss, take_profit, leverage, pnl, pnl_pct, fees,
                entry_time, exit_time, exit_reason, status, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                trade_record.trade_id,
                trade_record.symbol,
                trade_record.side,
                trade_record.size_qty,
                trade_record.entry_price,
                trade_record.exit_price,
                trade_record.stop_loss,
                trade_record.take_profit,
                trade_record.leverage,
                trade_record.pnl,
                trade_record.pnl_pct,
                trade_record.fees,
                trade_record.entry_time,
                trade_record.exit_time,
                trade_record.exit_reason,
                trade_record.status,
                trade_record.confidence
            )
            
            # Ejecutar query
            await db_manager.execute_query(query, values)
            logger.info(f"Trade guardado en BD: {trade_record.trade_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando trade en BD: {e}")
            return False
    
    async def _update_trade_in_db(self, trade_record: TradeRecord) -> bool:
        """Actualiza un trade en la base de datos"""
        try:
            # Crear query SQL para actualizar trade
            query = """
            UPDATE trades SET
                exit_price = ?, exit_time = ?, exit_reason = ?, status = ?,
                pnl = ?, pnl_pct = ?, fees = ?
            WHERE trade_id = ?
            """
            
            values = (
                trade_record.exit_price,
                trade_record.exit_time,
                trade_record.exit_reason,
                trade_record.status,
                trade_record.pnl,
                trade_record.pnl_pct,
                trade_record.fees,
                trade_record.trade_id
            )
            
            # Ejecutar query
            await db_manager.execute_query(query, values)
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
        if self.trading_mode == 'paper_trading':
            return self.current_balance
        else:
            # En modo live, obtener balance real de Bitget
            return self._get_live_balance()
    
    def _get_live_balance(self) -> float:
        """Obtiene el balance real de Bitget"""
        try:
            if not self.bitget_client:
                return self.current_balance
            
            # Obtener balance de USDT
            balance = self.bitget_client.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0.0)
            
            # Actualizar balance local
            self.current_balance = usdt_balance
            
            return usdt_balance
            
        except Exception as e:
            logger.error(f"Error obteniendo balance live: {e}")
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
    
    async def get_last_trade_result(self) -> Optional[Dict]:
        """Obtiene el resultado del último trade cerrado"""
        try:
            # Query para obtener el último trade cerrado
            query = """
            SELECT * FROM trades 
            WHERE status = 'CLOSED' 
            ORDER BY exit_time DESC 
            LIMIT 1
            """
            
            result = await db_manager.fetch_one(query)
            if result:
                return {
                    'trade_id': result[0],
                    'symbol': result[1],
                    'side': result[2],
                    'pnl': result[9],
                    'pnl_pct': result[10],
                    'fees': result[11],
                    'exit_reason': result[14],
                    'duration_hours': (result[13] - result[12]).total_seconds() / 3600 if result[13] and result[12] else 0
                }
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo último trade: {e}")
            return None

# Instancia global
order_manager = OrderManager()
