"""
Position Definitions
===================

Definiciones de posiciones de trading para evitar importaciones circulares.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Position:
    """Representa una posición abierta"""
    symbol: str
    side: str  # 'long', 'short'
    size: float
    entry_price: float
    current_price: float
    leverage: int
    margin_used: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @property
    def market_value(self) -> float:
        """Valor de mercado de la posición"""
        return self.size * self.current_price
    
    @property
    def duration_hours(self) -> float:
        """Duración de la posición en horas"""
        return (datetime.now() - self.entry_time).total_seconds() / 3600
    
    def update_price(self, new_price: float) -> None:
        """Actualiza el precio actual y recalcula PnL"""
        self.current_price = new_price
        self._calculate_pnl()
    
    def _calculate_pnl(self) -> None:
        """Calcula el PnL no realizado"""
        if self.side == 'long':
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.size
        else:  # short
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.size
        
        self.unrealized_pnl_pct = (self.unrealized_pnl / (self.entry_price * self.size)) * 100
    
    def is_profitable(self) -> bool:
        """Verifica si la posición es rentable"""
        return self.unrealized_pnl > 0
    
    def is_stop_loss_hit(self) -> bool:
        """Verifica si se alcanzó el stop loss"""
        if self.stop_loss is None:
            return False
        
        if self.side == 'long':
            return self.current_price <= self.stop_loss
        else:  # short
            return self.current_price >= self.stop_loss
    
    def is_take_profit_hit(self) -> bool:
        """Verifica si se alcanzó el take profit"""
        if self.take_profit is None:
            return False
        
        if self.side == 'long':
            return self.current_price >= self.take_profit
        else:  # short
            return self.current_price <= self.take_profit
    
    def should_close(self) -> bool:
        """Verifica si la posición debe cerrarse"""
        return self.is_stop_loss_hit() or self.is_take_profit_hit()
    
    def get_risk_amount(self) -> float:
        """Calcula la cantidad de riesgo"""
        if self.stop_loss is None:
            return 0.0
        
        if self.side == 'long':
            return (self.entry_price - self.stop_loss) * self.size
        else:  # short
            return (self.stop_loss - self.entry_price) * self.size
    
    def get_reward_amount(self) -> float:
        """Calcula la cantidad de recompensa"""
        if self.take_profit is None:
            return 0.0
        
        if self.side == 'long':
            return (self.take_profit - self.entry_price) * self.size
        else:  # short
            return (self.entry_price - self.take_profit) * self.size
    
    def get_risk_reward_ratio(self) -> Optional[float]:
        """Calcula el ratio riesgo/recompensa"""
        risk = self.get_risk_amount()
        reward = self.get_reward_amount()
        
        if risk <= 0:
            return None
        
        return reward / risk
    
    def to_dict(self) -> dict:
        """Convierte la posición a diccionario"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'leverage': self.leverage,
            'margin_used': self.margin_used,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'entry_time': self.entry_time.isoformat(),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'duration_hours': self.duration_hours,
            'market_value': self.market_value,
            'is_profitable': self.is_profitable(),
            'should_close': self.should_close()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Crea una posición desde un diccionario"""
        return cls(
            symbol=data['symbol'],
            side=data['side'],
            size=data['size'],
            entry_price=data['entry_price'],
            current_price=data['current_price'],
            leverage=data['leverage'],
            margin_used=data['margin_used'],
            unrealized_pnl=data['unrealized_pnl'],
            unrealized_pnl_pct=data['unrealized_pnl_pct'],
            entry_time=datetime.fromisoformat(data['entry_time']),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit')
        )
    
    def __str__(self) -> str:
        """Representación string de la posición"""
        return (f"Position({self.symbol}, {self.side}, "
                f"size={self.size:.4f}, entry={self.entry_price:.4f}, "
                f"current={self.current_price:.4f}, pnl={self.unrealized_pnl:.2f})")
    
    def __repr__(self) -> str:
        """Representación detallada de la posición"""
        return (f"Position(symbol='{self.symbol}', side='{self.side}', "
                f"size={self.size}, entry_price={self.entry_price}, "
                f"current_price={self.current_price}, leverage={self.leverage}, "
                f"margin_used={self.margin_used}, unrealized_pnl={self.unrealized_pnl}, "
                f"unrealized_pnl_pct={self.unrealized_pnl_pct}, "
                f"entry_time={self.entry_time}, stop_loss={self.stop_loss}, "
                f"take_profit={self.take_profit})")
