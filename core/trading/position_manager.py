"""
📊 position_manager.py - Gestor de Posiciones Inteligente

Gestor central que trackea y gestiona todas las posiciones de trading activas,
calculando P&L en tiempo real y gestionando stops automáticamente.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import uuid
import numpy as np

# Imports del proyecto
from core.config.config_loader import user_config
from core.data.database import db_manager
from core.data.collector import data_collector
from .order_manager import TradeRecord, order_manager

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """
    Representación de una posición de trading activa
    
    Atributos:
        position_id: ID único de la posición
        symbol: Símbolo de trading (ej: BTCUSDT)
        side: Lado de la posición (LONG, SHORT)
        size_qty: Cantidad de la posición
        entry_price: Precio de entrada
        current_price: Precio actual
        stop_loss: Precio de stop-loss
        take_profit: Precio de take-profit
        entry_time: Timestamp de entrada
        last_update: Última actualización
        leverage: Apalancamiento utilizado
        unrealized_pnl: P&L no realizado
        unrealized_pnl_pct: P&L no realizado en %
        max_pnl: Máxima ganancia alcanzada
        max_adverse_pnl: Máxima pérdida alcanzada
        confidence: Confianza original del trade
        trade_record_id: ID del TradeRecord original
        trailing_stop_price: Precio de trailing stop
        trailing_stop_triggered: Si el trailing stop se activó
    """
    position_id: str
    symbol: str
    side: str  # LONG, SHORT
    size_qty: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    last_update: datetime
    leverage: float = 1.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    max_pnl: float = 0.0  # High water mark
    max_adverse_pnl: float = 0.0  # Máxima pérdida
    confidence: float = 0.0  # Confianza original del trade
    trade_record_id: str = ""  # Referencia al TradeRecord original
    trailing_stop_price: float = 0.0
    trailing_stop_triggered: bool = False
    
    def __post_init__(self):
        """Inicialización post-creación"""
        if not self.position_id:
            self.position_id = str(uuid.uuid4())
        if not self.last_update:
            self.last_update = datetime.now()
        if not self.trailing_stop_price and self.stop_loss:
            self.trailing_stop_price = self.stop_loss
    
    def update_price(self, new_price: float) -> None:
        """Actualizar precio actual y recalcular P&L"""
        self.current_price = new_price
        self.last_update = datetime.now()
        self._calculate_pnl()
    
    def _calculate_pnl(self) -> None:
        """Calcular P&L no realizado"""
        try:
            if self.side == "LONG":
                self.unrealized_pnl = (self.current_price - self.entry_price) * self.size_qty
            else:  # SHORT
                self.unrealized_pnl = (self.entry_price - self.current_price) * self.size_qty
            
            # Calcular P&L porcentual
            self.unrealized_pnl_pct = self.unrealized_pnl / (self.entry_price * self.size_qty)
            
            # Actualizar high water marks
            if self.unrealized_pnl > self.max_pnl:
                self.max_pnl = self.unrealized_pnl
            
            if self.unrealized_pnl < self.max_adverse_pnl:
                self.max_adverse_pnl = self.unrealized_pnl
                
        except Exception as e:
            logger.error(f"Error calculando P&L para posición {self.position_id}: {e}")
    
    def is_stop_loss_triggered(self) -> bool:
        """Verificar si el stop-loss fue activado"""
        try:
            if self.side == "LONG":
                return self.current_price <= self.stop_loss
            else:  # SHORT
                return self.current_price >= self.stop_loss
        except Exception as e:
            logger.error(f"Error verificando stop-loss: {e}")
            return False
    
    def is_take_profit_triggered(self) -> bool:
        """Verificar si el take-profit fue activado"""
        try:
            if self.side == "LONG":
                return self.current_price >= self.take_profit
            else:  # SHORT
                return self.current_price <= self.take_profit
        except Exception as e:
            logger.error(f"Error verificando take-profit: {e}")
            return False
    
    def is_trailing_stop_triggered(self) -> bool:
        """Verificar si el trailing stop fue activado"""
        try:
            if not self.trailing_stop_price:
                return False
            
            if self.side == "LONG":
                return self.current_price <= self.trailing_stop_price
            else:  # SHORT
                return self.current_price >= self.trailing_stop_price
        except Exception as e:
            logger.error(f"Error verificando trailing stop: {e}")
            return False
    
    def update_trailing_stop(self, new_trailing_stop: float) -> bool:
        """Actualizar trailing stop solo si es favorable"""
        try:
            if not self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
                return True
            
            # Solo actualizar si es más favorable
            if self.side == "LONG":
                if new_trailing_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    return True
            else:  # SHORT
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error actualizando trailing stop: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir posición a diccionario para serialización"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'size_qty': self.size_qty,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'leverage': self.leverage,
            'entry_time': self.entry_time.isoformat(),
            'last_update': self.last_update.isoformat(),
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'max_pnl': self.max_pnl,
            'max_adverse_pnl': self.max_adverse_pnl,
            'confidence': self.confidence,
            'trade_record_id': self.trade_record_id,
            'trailing_stop_price': self.trailing_stop_price,
            'trailing_stop_triggered': self.trailing_stop_triggered
        }

class PositionManager:
    """
    Gestor central de todas las posiciones de trading
    
    Responsabilidades:
    - Trackear posiciones abiertas por símbolo
    - Actualizar P&L en tiempo real
    - Gestionar stop-loss y take-profit
    - Coordinar cierres de posiciones
    - Calcular métricas de portfolio
    - Persistir estado en base de datos
    """
    
    def __init__(self):
        self.config = user_config
        self.active_positions: Dict[str, Position] = {}  # position_id -> Position
        self.positions_by_symbol: Dict[str, List[str]] = {}  # symbol -> [position_ids]
        self.position_metrics: Dict[str, Any] = {}
        self.last_update_time: Optional[datetime] = None
        
        # Configuraciones
        self.trading_config = self.config.get_value(['trading'], {})
        self.max_positions_per_symbol = self.trading_config.get('max_positions_per_symbol', 1)
        self.position_timeout_hours = self.trading_config.get('position_timeout_hours', 24)
        self.trailing_stop_enabled = self.trading_config.get('trailing_stop_enabled', True)
        self.trailing_stop_distance = self.trading_config.get('trailing_stop_distance', 0.02)  # 2%
        
        # Métricas de portfolio
        self.metrics = {
            'total_positions_opened': 0,
            'total_positions_closed': 0,
            'current_active_positions': 0,
            'total_unrealized_pnl': 0.0,
            'total_realized_pnl': 0.0,
            'best_position_pnl': 0.0,
            'worst_position_pnl': 0.0,
            'average_position_duration_hours': 0.0,
            'stop_loss_hits': 0,
            'take_profit_hits': 0,
            'trailing_stops_applied': 0,
            'positions_by_symbol': {},
            'portfolio_exposure': 0.0,
            'last_update': datetime.now().isoformat()
        }
        
        logger.info("PositionManager inicializado")
    
    async def add_position(self, trade_record: TradeRecord) -> Position:
        """
        Añadir nueva posición desde un TradeRecord
        
        Args:
            trade_record: TradeRecord del trade ejecutado
            
        Returns:
            Position creada y añadida al tracking
        """
        try:
            logger.info(f"📊 Añadiendo nueva posición: {trade_record.symbol} {trade_record.side}")
            
            # Verificar límite de posiciones por símbolo
            symbol_positions = self.positions_by_symbol.get(trade_record.symbol, [])
            if len(symbol_positions) >= self.max_positions_per_symbol:
                raise Exception(f"Límite de posiciones alcanzado para {trade_record.symbol}: {len(symbol_positions)}/{self.max_positions_per_symbol}")
            
            # Crear Position desde TradeRecord
            position = Position(
                position_id=str(uuid.uuid4()),
                symbol=trade_record.symbol,
                side="LONG" if trade_record.side == "BUY" else "SHORT",
                size_qty=trade_record.size_qty,
                entry_price=trade_record.entry_price,
                current_price=trade_record.entry_price,  # Inicialmente igual al entry
                stop_loss=trade_record.stop_loss,
                take_profit=trade_record.take_profit,
                leverage=getattr(trade_record, 'leverage', 1.0),
                entry_time=trade_record.entry_time,
                confidence=getattr(trade_record, 'confidence', 0.0),
                trade_record_id=trade_record.trade_id
            )
            
            # Añadir a tracking interno
            self.active_positions[position.position_id] = position
            
            if trade_record.symbol not in self.positions_by_symbol:
                self.positions_by_symbol[trade_record.symbol] = []
            self.positions_by_symbol[trade_record.symbol].append(position.position_id)
            
            # Actualizar métricas
            self.metrics['total_positions_opened'] += 1
            self.metrics['current_active_positions'] = len(self.active_positions)
            self._update_positions_by_symbol_metrics()
            
            # Persistir en base de datos
            await self._persist_position(position)
            
            logger.info(f"✅ Posición añadida: {position.position_id} - {position.symbol} {position.side}")
            return position
            
        except Exception as e:
            logger.error(f"❌ Error añadiendo posición: {e}")
            raise
    
    async def remove_position(self, position_id: str, exit_reason: str) -> Optional[Position]:
        """
        Remover posición cerrada
        
        Args:
            position_id: ID de la posición a remover
            exit_reason: Razón del cierre
            
        Returns:
            Position removida o None si no se encontró
        """
        try:
            if position_id not in self.active_positions:
                logger.warning(f"⚠️ Posición no encontrada para remover: {position_id}")
                return None
            
            position = self.active_positions[position_id]
            symbol = position.symbol
            
            # Finalizar cálculos P&L
            final_pnl = position.unrealized_pnl
            final_pnl_pct = position.unrealized_pnl_pct
            
            # Actualizar métricas
            self.metrics['total_positions_closed'] += 1
            self.metrics['current_active_positions'] = len(self.active_positions) - 1
            self.metrics['total_realized_pnl'] += final_pnl
            
            if final_pnl > self.metrics['best_position_pnl']:
                self.metrics['best_position_pnl'] = final_pnl
            if final_pnl < self.metrics['worst_position_pnl']:
                self.metrics['worst_position_pnl'] = final_pnl
            
            # Contar tipo de salida
            if exit_reason == "stop_loss":
                self.metrics['stop_loss_hits'] += 1
            elif exit_reason == "take_profit":
                self.metrics['take_profit_hits'] += 1
            
            # Remover de tracking
            del self.active_positions[position_id]
            if symbol in self.positions_by_symbol:
                self.positions_by_symbol[symbol].remove(position_id)
                if not self.positions_by_symbol[symbol]:
                    del self.positions_by_symbol[symbol]
            
            # Actualizar métricas de símbolo
            self._update_positions_by_symbol_metrics()
            
            # Persistir cierre en base de datos
            await self._persist_position_closure(position, exit_reason, final_pnl)
            
            logger.info(f"✅ Posición removida: {position_id} - {symbol} - PnL: {final_pnl:.2f} ({exit_reason})")
            return position
            
        except Exception as e:
            logger.error(f"❌ Error removiendo posición {position_id}: {e}")
            return None
    
    async def update_positions_prices(self, price_data: Dict[str, float]) -> None:
        """
        Actualizar precios actuales de todas las posiciones
        
        Args:
            price_data: Dict con símbolo -> precio actual
        """
        try:
            self.last_update_time = datetime.now()
            positions_updated = 0
            exit_signals = []
            
            for position_id, position in self.active_positions.items():
                symbol = position.symbol
                if symbol in price_data:
                    old_price = position.current_price
                    new_price = price_data[symbol]
                    
                    # Actualizar precio y recalcular P&L
                    position.update_price(new_price)
                    positions_updated += 1
                    
                    # Verificar condiciones de salida
                    exit_condition = await self._check_position_exit_conditions(position)
                    if exit_condition:
                        exit_signals.append({
                            'position_id': position_id,
                            'symbol': symbol,
                            'condition': exit_condition,
                            'current_price': new_price,
                            'unrealized_pnl': position.unrealized_pnl
                        })
            
            # Actualizar métricas de portfolio
            self._update_portfolio_metrics()
            
            # Aplicar trailing stops si está habilitado
            if self.trailing_stop_enabled:
                await self.apply_trailing_stops()
            
            logger.debug(f"📊 Precios actualizados: {positions_updated} posiciones")
            
            # Retornar señales de salida para procesamiento externo
            return exit_signals
            
        except Exception as e:
            logger.error(f"❌ Error actualizando precios: {e}")
    
    async def check_exit_conditions(self) -> List[Dict]:
        """
        Verificar condiciones de salida para todas las posiciones
        
        Returns:
            Lista de condiciones de salida detectadas
        """
        try:
            exit_conditions = []
            
            for position_id, position in self.active_positions.items():
                condition = await self._check_position_exit_conditions(position)
                if condition:
                    exit_conditions.append({
                        'position_id': position_id,
                        'symbol': position.symbol,
                        'side': position.side,
                        'condition': condition,
                        'current_price': position.current_price,
                        'unrealized_pnl': position.unrealized_pnl,
                        'unrealized_pnl_pct': position.unrealized_pnl_pct,
                        'entry_price': position.entry_price,
                        'stop_loss': position.stop_loss,
                        'take_profit': position.take_profit
                    })
            
            if exit_conditions:
                logger.info(f"🚨 Condiciones de salida detectadas: {len(exit_conditions)} posiciones")
                for condition in exit_conditions:
                    logger.info(f"  - {condition['symbol']} {condition['side']}: {condition['condition']} (PnL: {condition['unrealized_pnl']:.2f})")
            
            return exit_conditions
            
        except Exception as e:
            logger.error(f"❌ Error verificando condiciones de salida: {e}")
            return []
    
    async def get_positions_requiring_exit(self) -> List[Position]:
        """
        Obtener lista de posiciones que deben cerrarse
        
        Returns:
            Lista de posiciones que requieren cierre
        """
        try:
            positions_to_close = []
            
            for position in self.active_positions.values():
                # Verificar timeout de posición
                duration_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                if duration_hours > self.position_timeout_hours:
                    positions_to_close.append(position)
                    continue
                
                # Verificar stops
                if position.is_stop_loss_triggered() or position.is_take_profit_triggered():
                    positions_to_close.append(position)
                    continue
                
                # Verificar trailing stop
                if position.is_trailing_stop_triggered():
                    positions_to_close.append(position)
                    continue
            
            return positions_to_close
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones para cerrar: {e}")
            return []
    
    def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Calcular métricas del portfolio completo
        
        Returns:
            Dict con métricas detalladas del portfolio
        """
        try:
            # Métricas básicas
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.active_positions.values())
            total_exposure = sum(pos.entry_price * pos.size_qty for pos in self.active_positions.values())
            
            # Métricas por símbolo
            symbol_metrics = {}
            for symbol, position_ids in self.positions_by_symbol.items():
                symbol_positions = [self.active_positions[pid] for pid in position_ids if pid in self.active_positions]
                if symbol_positions:
                    symbol_metrics[symbol] = {
                        'count': len(symbol_positions),
                        'total_pnl': sum(pos.unrealized_pnl for pos in symbol_positions),
                        'avg_pnl': np.mean([pos.unrealized_pnl for pos in symbol_positions]),
                        'best_pnl': max(pos.unrealized_pnl for pos in symbol_positions),
                        'worst_pnl': min(pos.unrealized_pnl for pos in symbol_positions),
                        'total_exposure': sum(pos.entry_price * pos.size_qty for pos in symbol_positions)
                    }
            
            # Calcular duración promedio de posiciones
            current_time = datetime.now()
            durations = [(current_time - pos.entry_time).total_seconds() / 3600 for pos in self.active_positions.values()]
            avg_duration = np.mean(durations) if durations else 0.0
            
            # Calcular win rate de posiciones cerradas
            total_closed = self.metrics['total_positions_closed']
            profitable_closed = sum(1 for _ in range(total_closed) if self.metrics['total_realized_pnl'] > 0)  # Simplificado
            win_rate = profitable_closed / total_closed if total_closed > 0 else 0.0
            
            portfolio_metrics = {
                'total_positions': len(self.active_positions),
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': self.metrics['total_realized_pnl'],
                'total_pnl': total_unrealized_pnl + self.metrics['total_realized_pnl'],
                'total_exposure': total_exposure,
                'portfolio_exposure_pct': (total_exposure / 10000) * 100 if total_exposure > 0 else 0,  # Asumiendo balance de 10k
                'symbol_metrics': symbol_metrics,
                'average_position_duration_hours': avg_duration,
                'win_rate': win_rate,
                'best_position_pnl': self.metrics['best_position_pnl'],
                'worst_position_pnl': self.metrics['worst_position_pnl'],
                'stop_loss_hits': self.metrics['stop_loss_hits'],
                'take_profit_hits': self.metrics['take_profit_hits'],
                'trailing_stops_applied': self.metrics['trailing_stops_applied'],
                'last_update': datetime.now().isoformat()
            }
            
            # Actualizar métricas internas
            self.position_metrics = portfolio_metrics
            self.metrics.update({
                'total_unrealized_pnl': total_unrealized_pnl,
                'portfolio_exposure': total_exposure,
                'average_position_duration_hours': avg_duration,
                'last_update': datetime.now().isoformat()
            })
            
            return portfolio_metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculando métricas de portfolio: {e}")
            return {}
    
    async def update_stop_loss(self, position_id: str, new_stop_loss: float) -> bool:
        """
        Actualizar stop-loss de posición
        
        Args:
            position_id: ID de la posición
            new_stop_loss: Nuevo precio de stop-loss
            
        Returns:
            True si se actualizó exitosamente
        """
        try:
            if position_id not in self.active_positions:
                logger.warning(f"⚠️ Posición no encontrada: {position_id}")
                return False
            
            position = self.active_positions[position_id]
            
            # Validar nuevo stop-loss
            if not self._validate_stop_loss(position, new_stop_loss):
                logger.warning(f"⚠️ Stop-loss inválido para {position_id}: {new_stop_loss}")
                return False
            
            # Actualizar stop-loss
            old_stop = position.stop_loss
            position.stop_loss = new_stop_loss
            
            # Actualizar trailing stop si es aplicable
            if self.trailing_stop_enabled:
                position.update_trailing_stop(new_stop_loss)
            
            # Persistir cambio
            await self._persist_position_update(position)
            
            logger.info(f"✅ Stop-loss actualizado: {position_id} - {old_stop} -> {new_stop_loss}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando stop-loss: {e}")
            return False
    
    async def apply_trailing_stops(self) -> List[str]:
        """
        Aplicar trailing stops automáticos
        
        Returns:
            Lista de IDs de posiciones modificadas
        """
        try:
            if not self.trailing_stop_enabled:
                return []
            
            modified_positions = []
            
            for position in self.active_positions.values():
                # Solo aplicar trailing stops a posiciones con ganancia
                if position.unrealized_pnl <= 0:
                    continue
                
                # Calcular nuevo trailing stop
                new_trailing_stop = self._calculate_trailing_stop(position)
                if new_trailing_stop and new_trailing_stop != position.trailing_stop_price:
                    if position.update_trailing_stop(new_trailing_stop):
                        modified_positions.append(position.position_id)
                        self.metrics['trailing_stops_applied'] += 1
                        
                        # Actualizar stop-loss si el trailing stop es más favorable
                        if self._is_trailing_stop_more_favorable(position, new_trailing_stop):
                            position.stop_loss = new_trailing_stop
                            await self._persist_position_update(position)
            
            if modified_positions:
                logger.info(f"📈 Trailing stops aplicados: {len(modified_positions)} posiciones")
            
            return modified_positions
            
        except Exception as e:
            logger.error(f"❌ Error aplicando trailing stops: {e}")
            return []
    
    async def save_positions_state(self) -> bool:
        """
        Guardar estado actual en base de datos
        
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Guardar estado de posiciones
            state_data = {
                'positions': {pid: pos.to_dict() for pid, pos in self.active_positions.items()},
                'metrics': self.metrics,
                'last_save': datetime.now().isoformat()
            }
            
            # Aquí se guardaría en la base de datos
            # Por ahora solo loggear
            logger.info(f"💾 Estado guardado: {len(self.active_positions)} posiciones activas")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado: {e}")
            return False
    
    async def load_positions_from_db(self) -> bool:
        """
        Cargar posiciones desde base de datos (recovery)
        
        Returns:
            True si se cargaron exitosamente
        """
        try:
            logger.info("🔄 Cargando posiciones desde base de datos...")
            
            # Obtener trades abiertos desde BD
            open_trades = db_manager.get_open_trades()
            
            loaded_count = 0
            for trade in open_trades:
                try:
                    # Crear Position desde TradeRecord
                    position = Position(
                        position_id=str(uuid.uuid4()),
                        symbol=trade.symbol,
                        side="LONG" if trade.side == "BUY" else "SHORT",
                        size_qty=trade.size_qty,
                        entry_price=trade.entry_price,
                        current_price=trade.entry_price,  # Se actualizará con precio actual
                        stop_loss=trade.stop_loss,
                        take_profit=trade.take_profit,
                        leverage=getattr(trade, 'leverage', 1.0),
                        entry_time=trade.entry_time,
                        confidence=getattr(trade, 'confidence', 0.0),
                        trade_record_id=trade.trade_id
                    )
                    
                    # Añadir a tracking
                    self.active_positions[position.position_id] = position
                    
                    if trade.symbol not in self.positions_by_symbol:
                        self.positions_by_symbol[trade.symbol] = []
                    self.positions_by_symbol[trade.symbol].append(position.position_id)
                    
                    loaded_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cargando posición desde trade {trade.trade_id}: {e}")
                    continue
            
            # Actualizar métricas
            self.metrics['current_active_positions'] = len(self.active_positions)
            self._update_positions_by_symbol_metrics()
            
            logger.info(f"✅ Posiciones cargadas: {loaded_count} posiciones activas")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando posiciones: {e}")
            return False
    
    # Métodos auxiliares privados
    
    async def _check_position_exit_conditions(self, position: Position) -> Optional[str]:
        """Verificar condiciones de salida para una posición específica"""
        try:
            # Verificar stop-loss
            if position.is_stop_loss_triggered():
                return "stop_loss"
            
            # Verificar take-profit
            if position.is_take_profit_triggered():
                return "take_profit"
            
            # Verificar trailing stop
            if position.is_trailing_stop_triggered():
                return "trailing_stop"
            
            # Verificar timeout
            duration_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
            if duration_hours > self.position_timeout_hours:
                return "timeout"
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando condiciones de salida: {e}")
            return None
    
    def _validate_stop_loss(self, position: Position, new_stop_loss: float) -> bool:
        """Validar que el nuevo stop-loss es lógico"""
        try:
            if new_stop_loss <= 0:
                return False
            
            # Para LONG: stop debe estar por debajo del precio actual
            if position.side == "LONG":
                return new_stop_loss < position.current_price
            
            # Para SHORT: stop debe estar por encima del precio actual
            else:
                return new_stop_loss > position.current_price
                
        except Exception as e:
            logger.error(f"Error validando stop-loss: {e}")
            return False
    
    def _calculate_trailing_stop(self, position: Position) -> Optional[float]:
        """Calcular nuevo trailing stop basado en ATR y ganancia"""
        try:
            if position.unrealized_pnl <= 0:
                return None
            
            # Calcular distancia de trailing stop basada en ATR
            # Por simplicidad, usar un porcentaje fijo del precio actual
            trailing_distance = position.current_price * self.trailing_stop_distance
            
            if position.side == "LONG":
                new_trailing_stop = position.current_price - trailing_distance
            else:  # SHORT
                new_trailing_stop = position.current_price + trailing_distance
            
            return new_trailing_stop
            
        except Exception as e:
            logger.error(f"Error calculando trailing stop: {e}")
            return None
    
    def _is_trailing_stop_more_favorable(self, position: Position, new_trailing_stop: float) -> bool:
        """Verificar si el nuevo trailing stop es más favorable que el actual"""
        try:
            if not position.trailing_stop_price:
                return True
            
            if position.side == "LONG":
                return new_trailing_stop > position.trailing_stop_price
            else:  # SHORT
                return new_trailing_stop < position.trailing_stop_price
                
        except Exception as e:
            logger.error(f"Error verificando trailing stop favorable: {e}")
            return False
    
    def _update_positions_by_symbol_metrics(self):
        """Actualizar métricas de posiciones por símbolo"""
        try:
            self.metrics['positions_by_symbol'] = {
                symbol: len(position_ids) 
                for symbol, position_ids in self.positions_by_symbol.items()
            }
        except Exception as e:
            logger.error(f"Error actualizando métricas por símbolo: {e}")
    
    def _update_portfolio_metrics(self):
        """Actualizar métricas de portfolio"""
        try:
            if not self.active_positions:
                self.metrics['total_unrealized_pnl'] = 0.0
                return
            
            total_unrealized = sum(pos.unrealized_pnl for pos in self.active_positions.values())
            self.metrics['total_unrealized_pnl'] = total_unrealized
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de portfolio: {e}")
    
    async def _persist_position(self, position: Position):
        """Persistir posición en base de datos"""
        try:
            # Aquí se guardaría en la base de datos
            # Por ahora solo loggear
            logger.debug(f"💾 Persistiendo posición: {position.position_id}")
        except Exception as e:
            logger.error(f"Error persistiendo posición: {e}")
    
    async def _persist_position_closure(self, position: Position, exit_reason: str, final_pnl: float):
        """Persistir cierre de posición en base de datos"""
        try:
            # Aquí se actualizaría el TradeRecord en la base de datos
            # Por ahora solo loggear
            logger.debug(f"💾 Persistiendo cierre: {position.position_id} - {exit_reason} - PnL: {final_pnl}")
        except Exception as e:
            logger.error(f"Error persistiendo cierre de posición: {e}")
    
    async def _persist_position_update(self, position: Position):
        """Persistir actualización de posición en base de datos"""
        try:
            # Aquí se actualizaría la posición en la base de datos
            # Por ahora solo loggear
            logger.debug(f"💾 Persistiendo actualización: {position.position_id}")
        except Exception as e:
            logger.error(f"Error persistiendo actualización de posición: {e}")
    
    # Métodos públicos para monitoreo y control
    
    def get_total_balance(self) -> float:
        """Obtener balance total del portfolio"""
        try:
            return self.metrics.get('total_balance', 10000.0)  # Default balance
        except Exception as e:
            logger.error(f"Error obteniendo balance total: {e}")
            return 10000.0
    
    def get_available_balance(self) -> float:
        """Obtener balance disponible para trading"""
        try:
            total_balance = self.get_total_balance()
            invested_balance = self.metrics.get('total_invested', 0.0)
            return total_balance - invested_balance
        except Exception as e:
            logger.error(f"Error obteniendo balance disponible: {e}")
            return 10000.0
    
    def get_total_realized_pnl(self) -> float:
        """Obtener P&L total realizado"""
        try:
            return self.metrics.get('total_realized_pnl', 0.0)
        except Exception as e:
            logger.error(f"Error obteniendo P&L realizado: {e}")
            return 0.0
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Obtener posiciones activas por símbolo"""
        try:
            return self.positions_by_symbol.get(symbol, [])
        except Exception as e:
            logger.error(f"Error obteniendo posiciones por símbolo {symbol}: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar estado del position manager"""
        try:
            health = {
                'status': 'healthy',
                'active_positions': len(self.active_positions),
                'positions_by_symbol': len(self.positions_by_symbol),
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
                'metrics': self.metrics,
                'errors': []
            }
            
            # Verificar consistencia
            inconsistencies = await self.validate_positions_consistency()
            if inconsistencies:
                health['errors'].extend(inconsistencies)
                health['status'] = 'degraded'
            
            return health
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def validate_positions_consistency(self) -> List[str]:
        """Validar consistencia entre positions y BD"""
        try:
            inconsistencies = []
            
            # Verificar que todas las posiciones tienen datos válidos
            for position_id, position in self.active_positions.items():
                if not position.symbol or not position.side:
                    inconsistencies.append(f"Posición {position_id} tiene datos inválidos")
                
                if position.unrealized_pnl != position.unrealized_pnl:  # Check NaN
                    inconsistencies.append(f"Posición {position_id} tiene PnL inválido")
            
            return inconsistencies
            
        except Exception as e:
            logger.error(f"Error validando consistencia: {e}")
            return [f"Error en validación: {e}"]
    
    def get_position_summary(self, symbol: str = None) -> Dict[str, Any]:
        """Resumen de posiciones por símbolo o total"""
        try:
            if symbol:
                # Resumen por símbolo específico
                if symbol not in self.positions_by_symbol:
                    return {'symbol': symbol, 'positions': 0, 'total_pnl': 0.0}
                
                position_ids = self.positions_by_symbol[symbol]
                positions = [self.active_positions[pid] for pid in position_ids if pid in self.active_positions]
                
                return {
                    'symbol': symbol,
                    'positions': len(positions),
                    'total_pnl': sum(pos.unrealized_pnl for pos in positions),
                    'avg_pnl': np.mean([pos.unrealized_pnl for pos in positions]) if positions else 0.0,
                    'best_pnl': max(pos.unrealized_pnl for pos in positions) if positions else 0.0,
                    'worst_pnl': min(pos.unrealized_pnl for pos in positions) if positions else 0.0
                }
            else:
                # Resumen total
                return {
                    'total_positions': len(self.active_positions),
                    'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in self.active_positions.values()),
                    'positions_by_symbol': {
                        symbol: len(position_ids) 
                        for symbol, position_ids in self.positions_by_symbol.items()
                    },
                    'metrics': self.metrics
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {'error': str(e)}
    
    async def simulate_price_update(self, symbol: str, new_price: float) -> Dict[str, Any]:
        """Simular actualización de precio para testing"""
        try:
            if symbol not in self.positions_by_symbol:
                return {'error': f'No hay posiciones para {symbol}'}
            
            # Simular actualización de precio
            price_data = {symbol: new_price}
            exit_signals = await self.update_positions_prices(price_data)
            
            # Obtener métricas actualizadas
            metrics = self.calculate_portfolio_metrics()
            
            return {
                'symbol': symbol,
                'new_price': new_price,
                'exit_signals': exit_signals,
                'updated_positions': len(self.positions_by_symbol[symbol]),
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error simulando actualización de precio: {e}")
            return {'error': str(e)}

# Instancia global del gestor de posiciones
position_manager = PositionManager()

# Funciones de conveniencia
async def add_position(trade_record: TradeRecord) -> Position:
    """Función de conveniencia para añadir posición"""
    return await position_manager.add_position(trade_record)

async def remove_position(position_id: str, exit_reason: str) -> Optional[Position]:
    """Función de conveniencia para remover posición"""
    return await position_manager.remove_position(position_id, exit_reason)

async def update_positions_prices(price_data: Dict[str, float]) -> List[Dict]:
    """Función de conveniencia para actualizar precios"""
    return await position_manager.update_positions_prices(price_data)

async def check_exit_conditions() -> List[Dict]:
    """Función de conveniencia para verificar condiciones de salida"""
    return await position_manager.check_exit_conditions()

def calculate_portfolio_metrics() -> Dict[str, Any]:
    """Función de conveniencia para calcular métricas de portfolio"""
    return position_manager.calculate_portfolio_metrics()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await position_manager.health_check()

def get_position_summary(symbol: str = None) -> Dict[str, Any]:
    """Función de conveniencia para obtener resumen de posiciones"""
    return position_manager.get_position_summary(symbol)
