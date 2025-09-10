# Ruta: core/trading/enterprise/position_manager.py
# position_manager.py - Gestor de posiciones avanzado
# Ubicación: C:\TradingBot_v10\core\trading\enterprise\position_manager.py

"""
Gestor de posiciones avanzado para trading enterprise.

Características principales:
- Gestión automática de posiciones long/short
- Stop loss y take profit dinámicos
- Trailing stops inteligentes
- Risk management por posición
- Monitoreo en tiempo real
- Integración con circuit breakers
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from enum import Enum

# Imports del proyecto
from .position import Position

logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """Estado de una posición"""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"

class ExitReason(Enum):
    """Razón de salida de una posición"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_LIMIT = "time_limit"
    MANUAL = "manual"
    EMERGENCY = "emergency"
    SIGNAL_CHANGE = "signal_change"
    MARGIN_RISK = "margin_risk"

@dataclass
class PositionMetrics:
    """Métricas de una posición"""
    symbol: str
    side: str
    entry_time: datetime
    duration_hours: float
    max_profit: float
    max_loss: float
    current_pnl: float
    current_pnl_pct: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    win_probability: float

@dataclass
class RiskLimits:
    """Límites de riesgo para una posición"""
    max_loss_usd: float
    max_loss_pct: float
    max_duration_hours: float
    max_drawdown_pct: float
    min_profit_target: float
    trailing_stop_trigger: float
    trailing_stop_distance: float

class PositionManager:
    """
    Gestor de posiciones avanzado para trading enterprise
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el gestor de posiciones
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.position_metrics: Dict[str, PositionMetrics] = {}
        self.risk_limits: Dict[str, RiskLimits] = {}
        
        # Configuración de risk management
        self.risk_config = config.risk_management
        
        # Configuración de stop loss y take profit
        self.sl_tp_config = self.risk_config.stop_loss_take_profit
        
        # Historial de posiciones
        self.position_history: List[Dict[str, Any]] = []
        
        # Monitoreo en tiempo real
        self.monitoring_active = False
        self.monitoring_task = None
        
        # Métricas de performance
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        logger.info("PositionManager inicializado")
    
    async def start_monitoring(self):
        """Inicia el monitoreo en tiempo real de posiciones"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("✅ Monitoreo de posiciones iniciado")
    
    async def stop_monitoring(self):
        """Detiene el monitoreo de posiciones"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Monitoreo de posiciones detenido")
    
    async def _monitoring_loop(self):
        """Loop principal de monitoreo de posiciones"""
        while self.monitoring_active:
            try:
                # Monitorear cada posición
                for symbol, position in list(self.positions.items()):
                    await self._monitor_position(position)
                
                # Actualizar métricas globales
                await self._update_global_metrics()
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(5)  # Monitorear cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error en monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_position(self, position: Position):
        """
        Monitorea una posición individual
        
        Args:
            position: Posición a monitorear
        """
        try:
            symbol = position.symbol
            
            # Actualizar precio actual (simulado)
            # En un sistema real, esto vendría del exchange
            price_change = np.random.normal(0, 0.001)  # 0.1% cambio promedio
            position.current_price *= (1 + price_change)
            
            # Actualizar PnL
            await self._update_position_pnl(position)
            
            # Verificar condiciones de salida
            should_exit, reason = await self._check_exit_conditions(position)
            
            if should_exit:
                await self._exit_position(position, reason)
                return
            
            # Actualizar trailing stop
            await self._update_trailing_stop(position)
            
            # Actualizar métricas de la posición
            await self._update_position_metrics(position)
            
        except Exception as e:
            logger.error(f"Error monitoreando posición {position.symbol}: {e}")
    
    async def _update_position_pnl(self, position: Position):
        """Actualiza el PnL de una posición"""
        try:
            if position.side == 'long':
                pnl = (position.current_price - position.entry_price) * position.size
            else:  # short
                pnl = (position.entry_price - position.current_price) * position.size
            
            # Aplicar leverage
            position.unrealized_pnl = pnl * position.leverage
            position.unrealized_pnl_pct = (position.unrealized_pnl / (position.entry_price * position.size)) * 100
            
        except Exception as e:
            logger.error(f"Error actualizando PnL para {position.symbol}: {e}")
    
    async def _check_exit_conditions(self, position: Position) -> Tuple[bool, ExitReason]:
        """
        Verifica condiciones de salida para una posición
        
        Args:
            position: Posición a verificar
            
        Returns:
            Tupla (debe_salir, razón)
        """
        try:
            symbol = position.symbol
            
            # 1. Verificar stop loss
            if position.stop_loss:
                if position.side == 'long' and position.current_price <= position.stop_loss:
                    return True, ExitReason.STOP_LOSS
                elif position.side == 'short' and position.current_price >= position.stop_loss:
                    return True, ExitReason.STOP_LOSS
            
            # 2. Verificar take profit
            if position.take_profit:
                if position.side == 'long' and position.current_price >= position.take_profit:
                    return True, ExitReason.TAKE_PROFIT
                elif position.side == 'short' and position.current_price <= position.take_profit:
                    return True, ExitReason.TAKE_PROFIT
            
            # 3. Verificar límites de riesgo
            risk_limits = self.risk_limits.get(symbol)
            if risk_limits:
                # Pérdida máxima en USD
                if position.unrealized_pnl < -risk_limits.max_loss_usd:
                    return True, ExitReason.MARGIN_RISK
                
                # Pérdida máxima en porcentaje
                if position.unrealized_pnl_pct < -risk_limits.max_loss_pct:
                    return True, ExitReason.MARGIN_RISK
                
                # Duración máxima
                if position.duration_hours > risk_limits.max_drawdown_pct:
                    return True, ExitReason.TIME_LIMIT
            
            # 4. Verificar drawdown máximo
            if position.unrealized_pnl_pct < -self.risk_config.capital_management.max_drawdown_pct * 100:
                return True, ExitReason.MARGIN_RISK
            
            # 5. Verificar volatilidad extrema
            if await self._check_extreme_volatility(position):
                return True, ExitReason.EMERGENCY
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error verificando condiciones de salida para {position.symbol}: {e}")
            return False, None
    
    async def _check_extreme_volatility(self, position: Position) -> bool:
        """Verifica si hay volatilidad extrema que requiera salida"""
        try:
            # Calcular volatilidad reciente (simulada)
            # En un sistema real, esto se calcularía con datos históricos
            volatility = abs(np.random.normal(0, 0.02))  # 2% volatilidad promedio
            
            # Si la volatilidad es > 5%, considerar salida
            return volatility > 0.05
            
        except Exception as e:
            logger.error(f"Error verificando volatilidad para {position.symbol}: {e}")
            return False
    
    async def _update_trailing_stop(self, position: Position):
        """Actualiza el trailing stop de una posición"""
        try:
            if not self.sl_tp_config.stop_loss.trailing_stop.enabled:
                return
            
            symbol = position.symbol
            trailing_config = self.sl_tp_config.stop_loss.trailing_stop
            
            # Verificar si debe activar trailing stop
            profit_pct = position.unrealized_pnl_pct / 100
            if profit_pct < trailing_config.trigger_pct:
                return  # No hay suficiente ganancia para activar trailing
            
            # Calcular nuevo stop loss
            if position.side == 'long':
                new_stop_loss = position.current_price * (1 - trailing_config.trail_distance_pct)
                if not position.stop_loss or new_stop_loss > position.stop_loss:
                    position.stop_loss = new_stop_loss
            else:  # short
                new_stop_loss = position.current_price * (1 + trailing_config.trail_distance_pct)
                if not position.stop_loss or new_stop_loss < position.stop_loss:
                    position.stop_loss = new_stop_loss
            
            logger.debug(f"Trailing stop actualizado para {symbol}: {position.stop_loss:.4f}")
            
        except Exception as e:
            logger.error(f"Error actualizando trailing stop para {position.symbol}: {e}")
    
    async def _update_position_metrics(self, position: Position):
        """Actualiza las métricas de una posición"""
        try:
            symbol = position.symbol
            
            if symbol not in self.position_metrics:
                self.position_metrics[symbol] = PositionMetrics(
                    symbol=symbol,
                    side=position.side,
                    entry_time=position.entry_time,
                    duration_hours=position.duration_hours,
                    max_profit=0.0,
                    max_loss=0.0,
                    current_pnl=position.unrealized_pnl,
                    current_pnl_pct=position.unrealized_pnl_pct,
                    max_drawdown=0.0,
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    win_probability=0.5
                )
            
            metrics = self.position_metrics[symbol]
            
            # Actualizar métricas
            metrics.duration_hours = position.duration_hours
            metrics.current_pnl = position.unrealized_pnl
            metrics.current_pnl_pct = position.unrealized_pnl_pct
            
            # Actualizar máximo beneficio
            if position.unrealized_pnl > metrics.max_profit:
                metrics.max_profit = position.unrealized_pnl
            
            # Actualizar máxima pérdida
            if position.unrealized_pnl < metrics.max_loss:
                metrics.max_loss = position.unrealized_pnl
            
            # Calcular drawdown actual
            if metrics.max_profit > 0:
                current_drawdown = (metrics.max_profit - position.unrealized_pnl) / metrics.max_profit
                if current_drawdown > metrics.max_drawdown:
                    metrics.max_drawdown = current_drawdown
            
            # Calcular volatilidad (simulada)
            metrics.volatility = abs(np.random.normal(0, 0.02))
            
            # Calcular Sharpe ratio (simplificado)
            if metrics.volatility > 0:
                metrics.sharpe_ratio = (position.unrealized_pnl / 100) / metrics.volatility
            else:
                metrics.sharpe_ratio = 0.0
            
            # Calcular probabilidad de ganancia (simplificada)
            if position.unrealized_pnl > 0:
                metrics.win_probability = min(0.9, 0.5 + (position.unrealized_pnl_pct / 100) * 2)
            else:
                metrics.win_probability = max(0.1, 0.5 + (position.unrealized_pnl_pct / 100) * 2)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas para {position.symbol}: {e}")
    
    async def _update_global_metrics(self):
        """Actualiza las métricas globales del portfolio"""
        try:
            # Calcular PnL total
            total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            # Actualizar drawdown
            if total_pnl > self.total_pnl:
                self.total_pnl = total_pnl
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = self.total_pnl - total_pnl
                if self.current_drawdown > self.max_drawdown:
                    self.max_drawdown = self.current_drawdown
            
        except Exception as e:
            logger.error(f"Error actualizando métricas globales: {e}")
    
    async def add_position(self, position: Position) -> bool:
        """
        Agrega una nueva posición al gestor
        
        Args:
            position: Posición a agregar
            
        Returns:
            True si se agregó exitosamente
        """
        try:
            symbol = position.symbol
            
            # Verificar si ya existe una posición para este símbolo
            if symbol in self.positions:
                logger.warning(f"Ya existe una posición para {symbol}. Cerrando posición anterior.")
                await self._exit_position(self.positions[symbol], ExitReason.SIGNAL_CHANGE)
            
            # Configurar límites de riesgo
            await self._setup_risk_limits(position)
            
            # Configurar stop loss y take profit
            await self._setup_stop_loss_take_profit(position)
            
            # Agregar posición
            self.positions[symbol] = position
            
            # Inicializar métricas
            await self._update_position_metrics(position)
            
            # Iniciar monitoreo si no está activo
            if not self.monitoring_active:
                await self.start_monitoring()
            
            logger.info(f"✅ Posición agregada: {symbol} {position.side} @ {position.entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando posición {position.symbol}: {e}")
            return False
    
    async def _setup_risk_limits(self, position: Position):
        """Configura límites de riesgo para una posición"""
        try:
            symbol = position.symbol
            
            # Obtener configuración de riesgo
            max_risk_per_trade = self.risk_config.capital_management.max_risk_per_trade_pct
            max_risk_per_symbol = self.risk_config.capital_management.max_risk_per_symbol_pct
            
            # Calcular límites basados en el tamaño de la posición
            position_value = position.entry_price * position.size
            max_loss_usd = position_value * max_risk_per_trade
            max_loss_pct = max_risk_per_trade * 100
            
            # Duración máxima
            max_duration = self.config.trading.futures.positions.max_position_duration_hours
            
            # Configurar trailing stop
            trailing_config = self.sl_tp_config.stop_loss.trailing_stop
            
            self.risk_limits[symbol] = RiskLimits(
                max_loss_usd=max_loss_usd,
                max_loss_pct=max_loss_pct,
                max_duration_hours=max_duration,
                max_drawdown_pct=self.risk_config.capital_management.max_drawdown_pct * 100,
                min_profit_target=0.02,  # 2% ganancia mínima
                trailing_stop_trigger=trailing_config.trigger_pct,
                trailing_stop_distance=trailing_config.trail_distance_pct
            )
            
        except Exception as e:
            logger.error(f"Error configurando límites de riesgo para {position.symbol}: {e}")
    
    async def _setup_stop_loss_take_profit(self, position: Position):
        """Configura stop loss y take profit para una posición"""
        try:
            symbol = position.symbol
            entry_price = position.entry_price
            side = position.side
            
            # Configuración de stop loss
            sl_config = self.sl_tp_config.stop_loss
            
            if sl_config.method == "atr_based":
                # Calcular ATR (simulado)
                atr = entry_price * 0.02  # 2% del precio como ATR
                stop_distance = atr * sl_config.atr_based.atr_multiplier
            elif sl_config.method == "fixed_percentage":
                stop_distance = entry_price * sl_config.fixed_percentage.percentage
            else:
                stop_distance = entry_price * 0.02  # 2% por defecto
            
            # Aplicar límites
            min_stop = entry_price * sl_config.atr_based.min_stop_loss_pct
            max_stop = entry_price * sl_config.atr_based.max_stop_loss_pct
            stop_distance = max(min(stop_distance, max_stop), min_stop)
            
            # Configurar stop loss
            if side == 'long':
                position.stop_loss = entry_price - stop_distance
            else:
                position.stop_loss = entry_price + stop_distance
            
            # Configuración de take profit
            tp_config = self.sl_tp_config.take_profit
            
            if tp_config.scaling.enabled:
                # Usar el primer nivel de take profit
                first_level = tp_config.scaling.levels[0]
                take_distance = entry_price * first_level.target_pct
                
                if side == 'long':
                    position.take_profit = entry_price + take_distance
                else:
                    position.take_profit = entry_price - take_distance
            else:
                # Take profit fijo
                take_distance = entry_price * tp_config.fixed.target_pct
                
                if side == 'long':
                    position.take_profit = entry_price + take_distance
                else:
                    position.take_profit = entry_price - take_distance
            
            logger.info(
                f"🛡️ SL/TP configurado para {symbol}: "
                f"SL: {position.stop_loss:.4f} TP: {position.take_profit:.4f}"
            )
            
        except Exception as e:
            logger.error(f"Error configurando SL/TP para {position.symbol}: {e}")
    
    async def _exit_position(self, position: Position, reason: ExitReason):
        """
        Cierra una posición
        
        Args:
            position: Posición a cerrar
            reason: Razón de la salida
        """
        try:
            symbol = position.symbol
            
            # Marcar posición como cerrando
            position.status = PositionStatus.CLOSING
            
            # Calcular PnL final
            final_pnl = position.unrealized_pnl
            
            # Actualizar estadísticas
            self.total_trades += 1
            if final_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            self.total_pnl += final_pnl
            
            # Agregar al historial
            self.position_history.append({
                'symbol': symbol,
                'side': position.side,
                'entry_price': position.entry_price,
                'exit_price': position.current_price,
                'size': position.size,
                'leverage': position.leverage,
                'pnl': final_pnl,
                'pnl_pct': position.unrealized_pnl_pct,
                'duration_hours': position.duration_hours,
                'exit_reason': reason.value,
                'exit_time': datetime.now().isoformat()
            })
            
            # Remover de posiciones activas
            if symbol in self.positions:
                del self.positions[symbol]
            
            # Remover métricas
            if symbol in self.position_metrics:
                del self.position_metrics[symbol]
            
            # Remover límites de riesgo
            if symbol in self.risk_limits:
                del self.risk_limits[symbol]
            
            logger.info(
                f"🔒 Posición cerrada: {symbol} {position.side} "
                f"PnL: ${final_pnl:.2f} ({position.unrealized_pnl_pct:.2f}%) "
                f"Razón: {reason.value}"
            )
            
        except Exception as e:
            logger.error(f"Error cerrando posición {position.symbol}: {e}")
    
    async def close_position(self, symbol: str, reason: ExitReason = ExitReason.MANUAL) -> bool:
        """
        Cierra una posición específica
        
        Args:
            symbol: Símbolo de la posición a cerrar
            reason: Razón de la salida
            
        Returns:
            True si se cerró exitosamente
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"No hay posición abierta para {symbol}")
                return False
            
            position = self.positions[symbol]
            await self._exit_position(position, reason)
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición {symbol}: {e}")
            return False
    
    async def close_all_positions(self, reason: ExitReason = ExitReason.EMERGENCY) -> int:
        """
        Cierra todas las posiciones abiertas
        
        Args:
            reason: Razón de la salida
            
        Returns:
            Número de posiciones cerradas
        """
        try:
            positions_to_close = list(self.positions.keys())
            closed_count = 0
            
            for symbol in positions_to_close:
                if await self.close_position(symbol, reason):
                    closed_count += 1
            
            logger.info(f"🔒 Cerradas {closed_count} posiciones. Razón: {reason.value}")
            return closed_count
            
        except Exception as e:
            logger.error(f"Error cerrando todas las posiciones: {e}")
            return 0
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Obtiene una posición específica"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Obtiene todas las posiciones activas"""
        return self.positions.copy()
    
    def get_position_metrics(self, symbol: str) -> Optional[PositionMetrics]:
        """Obtiene las métricas de una posición"""
        return self.position_metrics.get(symbol)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del portfolio"""
        try:
            total_positions = len(self.positions)
            total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            total_pnl_pct = (total_pnl / sum(pos.entry_price * pos.size for pos in self.positions.values())) * 100 if self.positions else 0
            
            return {
                'total_positions': total_positions,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
                'total_trades': self.total_trades,
                'max_drawdown': self.max_drawdown,
                'current_drawdown': self.current_drawdown,
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'side': pos.side,
                        'size': pos.size,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price,
                        'pnl': pos.unrealized_pnl,
                        'pnl_pct': pos.unrealized_pnl_pct,
                        'duration_hours': pos.duration_hours
                    }
                    for pos in self.positions.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen del portfolio: {e}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance del gestor"""
        try:
            if self.total_trades == 0:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'avg_pnl': 0.0,
                    'total_pnl': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0
                }
            
            # Calcular métricas
            win_rate = self.winning_trades / self.total_trades
            avg_pnl = self.total_pnl / self.total_trades
            
            # Calcular Sharpe ratio (simplificado)
            if len(self.position_history) > 1:
                pnl_series = [pos['pnl'] for pos in self.position_history]
                sharpe_ratio = np.mean(pnl_series) / (np.std(pnl_series) + 1e-10)
            else:
                sharpe_ratio = 0.0
            
            return {
                'total_trades': self.total_trades,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': self.total_pnl,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de performance: {e}")
            return {}
    
    async def emergency_stop(self):
        """Parada de emergencia - cierra todas las posiciones"""
        logger.warning("🚨 PARADA DE EMERGENCIA - Cerrando todas las posiciones")
        await self.close_all_positions(ExitReason.EMERGENCY)
    
    def export_position_history(self, output_file: Optional[str] = None) -> str:
        """Exporta el historial de posiciones"""
        try:
            if output_file is None:
                output_file = f"position_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = Path("logs/enterprise/trading/positions") / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar datos para exportación
            export_data = {
                'position_history': self.position_history,
                'performance_metrics': self.get_performance_metrics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            import json
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Historial de posiciones exportado: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando historial de posiciones: {e}")
            return None
