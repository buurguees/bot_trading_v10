# Ruta: core/trading/enterprise/trading_signal.py
"""
Trading Signal Definitions
=========================

Definiciones de señales de trading para evitar importaciones circulares.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

class SignalType(Enum):
    """Tipos de señales de trading"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"

class SignalStrength(Enum):
    """Fuerza de la señal"""
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"

@dataclass
class TradingSignal:
    """
    Señal de trading generada por el sistema ML
    
    Attributes:
        symbol: Símbolo del activo
        signal_type: Tipo de señal (BUY, SELL, HOLD, CLOSE)
        strength: Fuerza de la señal
        confidence: Nivel de confianza (0.0 - 1.0)
        price: Precio objetivo
        stop_loss: Precio de stop loss
        take_profit: Precio de take profit
        leverage: Apalancamiento sugerido
        timestamp: Timestamp de la señal
        model_name: Nombre del modelo que generó la señal
        features: Características utilizadas para la predicción
        metadata: Metadatos adicionales
    """
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: Optional[int] = None
    timestamp: Optional[datetime] = None
    model_name: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validaciones post-inicialización"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        
        if self.price <= 0:
            raise ValueError("Price must be positive")
        
        if self.stop_loss is not None and self.stop_loss <= 0:
            raise ValueError("Stop loss must be positive")
        
        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("Take profit must be positive")
        
        if self.leverage is not None and not (1 <= self.leverage <= 100):
            raise ValueError("Leverage must be between 1 and 100")
    
    def is_buy_signal(self) -> bool:
        """Verifica si es una señal de compra"""
        return self.signal_type == SignalType.BUY
    
    def is_sell_signal(self) -> bool:
        """Verifica si es una señal de venta"""
        return self.signal_type == SignalType.SELL
    
    def is_hold_signal(self) -> bool:
        """Verifica si es una señal de mantener"""
        return self.signal_type == SignalType.HOLD
    
    def is_close_signal(self) -> bool:
        """Verifica si es una señal de cerrar"""
        return self.signal_type == SignalType.CLOSE
    
    def is_strong_signal(self) -> bool:
        """Verifica si es una señal fuerte"""
        return self.strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]
    
    def get_risk_reward_ratio(self) -> Optional[float]:
        """Calcula el ratio riesgo/recompensa"""
        if self.stop_loss is None or self.take_profit is None:
            return None
        
        if self.is_buy_signal():
            risk = self.price - self.stop_loss
            reward = self.take_profit - self.price
        else:  # SELL signal
            risk = self.stop_loss - self.price
            reward = self.price - self.take_profit
        
        if risk <= 0:
            return None
        
        return reward / risk
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la señal a diccionario"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'price': self.price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'leverage': self.leverage,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'model_name': self.model_name,
            'features': self.features,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Crea una señal desde un diccionario"""
        return cls(
            symbol=data['symbol'],
            signal_type=SignalType(data['signal_type']),
            strength=SignalStrength(data['strength']),
            confidence=data['confidence'],
            price=data['price'],
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit'),
            leverage=data.get('leverage'),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None,
            model_name=data.get('model_name'),
            features=data.get('features'),
            metadata=data.get('metadata')
        )
    
    def __str__(self) -> str:
        """Representación string de la señal"""
        return (f"TradingSignal({self.symbol}, {self.signal_type.value}, "
                f"{self.strength.value}, conf={self.confidence:.2f}, "
                f"price={self.price:.4f})")
    
    def __repr__(self) -> str:
        """Representación detallada de la señal"""
        return (f"TradingSignal(symbol='{self.symbol}', "
                f"signal_type={self.signal_type.value}, "
                f"strength={self.strength.value}, "
                f"confidence={self.confidence}, "
                f"price={self.price}, "
                f"stop_loss={self.stop_loss}, "
                f"take_profit={self.take_profit}, "
                f"leverage={self.leverage}, "
                f"timestamp={self.timestamp}, "
                f"model_name='{self.model_name}')")
