"""
trading/risk_manager.py
Sistema de gestión de riesgo para trading
Ubicación: C:\\TradingBot_v10\\trading\\risk_manager.py

Funcionalidades:
- Cálculo de tamaño de posición basado en riesgo
- Gestión de stop loss y take profit
- Control de leverage y exposición máxima
- Validación de límites de riesgo diarios
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from decimal import Decimal, ROUND_DOWN

from config.config_loader import user_config
from data.database import db_manager

logger = logging.getLogger(__name__)

@dataclass
class RiskDecision:
    """Decisión de riesgo calculada para una operación"""
    size_qty: float
    stop_loss: float
    take_profit: float
    leverage: float
    max_position_value: float
    risk_amount: float
    risk_percentage: float
    trailing_config: Optional[Dict] = None

class RiskManager:
    """Gestor de riesgo para operaciones de trading"""
    
    def __init__(self):
        self.config = user_config
        self.risk_config = self.config.get_value(['risk_management'], {})
        self.trading_config = self.config.get_value(['trading'], {})
        
        # Límites de riesgo
        self.max_risk_per_trade = self.risk_config.get('max_risk_per_trade', 0.02)  # 2%
        self.max_daily_loss_pct = self.risk_config.get('max_daily_loss_pct', 0.05)  # 5%
        self.max_drawdown_pct = self.risk_config.get('max_drawdown_pct', 0.10)  # 10%
        self.max_leverage = self.risk_config.get('max_leverage', 3.0)  # 3x máximo
        
        # Configuración de trading
        self.trading_mode = self.trading_config.get('mode', 'paper_trading')
        self.is_futures = self.trading_config.get('futures', False)
        
        logger.info(f"RiskManager inicializado - Modo: {self.trading_mode}, Futuros: {self.is_futures}")
    
    def calculate_position_size(
        self,
        current_price: float,
        atr: float,
        balance: float,
        stop_loss_pct: float = 0.02,
        confidence: float = 1.0
    ) -> RiskDecision:
        """
        Calcula el tamaño de posición basado en el riesgo
        
        Args:
            current_price: Precio actual del activo
            atr: Average True Range para volatilidad
            balance: Balance disponible
            stop_loss_pct: Porcentaje de stop loss (default 2%)
            confidence: Confianza de la señal (0-1)
        
        Returns:
            RiskDecision con todos los parámetros calculados
        """
        try:
            # Validar inputs
            if current_price <= 0 or atr <= 0 or balance <= 0:
                logger.warning("Inputs inválidos para cálculo de posición")
                return self._create_reject_decision("Inputs inválidos")
            
            # Verificar límites diarios
            if not self._check_daily_limits(balance):
                return self._create_reject_decision("Límites diarios excedidos")
            
            # Calcular riesgo base
            base_risk_amount = balance * self.max_risk_per_trade
            
            # Ajustar por confianza
            adjusted_risk_amount = base_risk_amount * confidence
            
            # Calcular tamaño de posición
            risk_per_share = current_price * stop_loss_pct
            if risk_per_share <= 0:
                return self._create_reject_decision("Stop loss inválido")
            
            # Tamaño base
            base_size = adjusted_risk_amount / risk_per_share
            
            # Ajustar por volatilidad (ATR)
            volatility_factor = min(1.0, 0.5 / (atr / current_price))  # Reducir si muy volátil
            adjusted_size = base_size * volatility_factor
            
            # Aplicar límites de exposición
            max_position_value = balance * 0.5  # Máximo 50% del balance
            max_size_by_value = max_position_value / current_price
            final_size = min(adjusted_size, max_size_by_value)
            
            # Redondear hacia abajo
            final_size = float(Decimal(str(final_size)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN))
            
            if final_size <= 0:
                return self._create_reject_decision("Tamaño de posición muy pequeño")
            
            # Calcular stop loss y take profit
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + stop_loss_pct * 2)  # Risk:Reward 1:2
            
            # Calcular leverage
            leverage = min(self.max_leverage, 1.0)  # Paper mode: leverage 1x por defecto
            if self.is_futures and self.trading_mode == 'live_trading':
                leverage = min(self.max_leverage, 3.0)
            
            # Configuración de trailing stop
            trailing_config = {
                'enabled': True,
                'activation_pct': 0.01,  # 1% de ganancia para activar
                'trail_pct': 0.005,     # 0.5% de trailing
                'min_trail_pct': 0.01   # Mínimo 1% de trailing
            }
            
            # Calcular métricas finales
            position_value = final_size * current_price
            actual_risk_amount = final_size * (current_price - stop_loss)
            actual_risk_pct = actual_risk_amount / balance
            
            decision = RiskDecision(
                size_qty=final_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=leverage,
                max_position_value=max_position_value,
                risk_amount=actual_risk_amount,
                risk_percentage=actual_risk_pct,
                trailing_config=trailing_config
            )
            
            logger.info(f"Decisión de riesgo calculada: {final_size:.4f} unidades, "
                       f"SL: {stop_loss:.2f}, TP: {take_profit:.2f}, "
                       f"Riesgo: {actual_risk_pct:.2%}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return self._create_reject_decision(f"Error en cálculo: {e}")
    
    def _check_daily_limits(self, balance: float) -> bool:
        """Verifica si se han excedido los límites diarios"""
        try:
            # Obtener pérdidas del día
            today = datetime.now().date()
            daily_pnl = self._get_daily_pnl(today)
            
            # Verificar pérdida diaria máxima
            max_daily_loss = balance * self.max_daily_loss_pct
            if daily_pnl < -max_daily_loss:
                logger.warning(f"Límite de pérdida diaria excedido: {daily_pnl:.2f} < -{max_daily_loss:.2f}")
                return False
            
            # Verificar drawdown máximo
            max_drawdown = balance * self.max_drawdown_pct
            if daily_pnl < -max_drawdown:
                logger.warning(f"Drawdown máximo excedido: {daily_pnl:.2f} < -{max_drawdown:.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando límites diarios: {e}")
            return False
    
    def _get_daily_pnl(self, date) -> float:
        """Obtiene el PnL del día desde la base de datos"""
        try:
            # Implementar consulta a BD para obtener PnL del día
            # Por ahora retornar 0 (no hay trades aún)
            return 0.0
        except Exception as e:
            logger.error(f"Error obteniendo PnL diario: {e}")
            return 0.0
    
    def _create_reject_decision(self, reason: str) -> RiskDecision:
        """Crea una decisión de rechazo"""
        logger.warning(f"Operación rechazada: {reason}")
        return RiskDecision(
            size_qty=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            leverage=1.0,
            max_position_value=0.0,
            risk_amount=0.0,
            risk_percentage=0.0,
            trailing_config=None
        )
    
    def validate_signal(self, signal: str, confidence: float) -> bool:
        """Valida si una señal puede ser ejecutada"""
        if confidence < 0.5:  # Mínimo 50% de confianza
            logger.warning(f"Confianza insuficiente: {confidence:.2%}")
            return False
        
        if signal not in ['BUY', 'SELL', 'HOLD']:
            logger.warning(f"Señal inválida: {signal}")
            return False
        
        return True
    
    def get_risk_summary(self) -> Dict:
        """Obtiene un resumen del estado de riesgo actual"""
        return {
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_daily_loss_pct': self.max_daily_loss_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_leverage': self.max_leverage,
            'trading_mode': self.trading_mode,
            'is_futures': self.is_futures
        }

# Instancia global
risk_manager = RiskManager()
