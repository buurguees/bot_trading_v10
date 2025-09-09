# Ruta: core/trading/enterprise/leverage_calculator.py
# leverage_calculator.py - Calculador de leverage dinámico
# Ubicación: C:\TradingBot_v10\trading\enterprise\leverage_calculator.py

"""
Calculador de leverage dinámico para trading enterprise.

Características principales:
- Leverage dinámico 5x-30x basado en confianza del modelo
- Ajuste por volatilidad del mercado
- Ajuste por correlación entre posiciones
- Ajuste por drawdown del portfolio
- Límites de seguridad por símbolo
- Integración con risk management
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LeverageStrategy(Enum):
    """Estrategias de cálculo de leverage"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DYNAMIC = "dynamic"

@dataclass
class LeverageFactors:
    """Factores que influyen en el cálculo de leverage"""
    confidence: float
    volatility: float
    correlation: float
    drawdown: float
    market_conditions: str
    symbol_risk: float
    portfolio_risk: float

@dataclass
class LeverageResult:
    """Resultado del cálculo de leverage"""
    leverage: int
    confidence: float
    factors: LeverageFactors
    reasoning: str
    risk_score: float
    timestamp: datetime

class LeverageCalculator:
    """
    Calculador de leverage dinámico para trading enterprise
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el calculador de leverage
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        
        # Configuración de leverage
        self.leverage_config = config.trading.futures.leverage
        self.risk_config = config.risk_management
        
        # Configuración de leverage por símbolo
        self.symbol_leverage_limits = {
            'BTCUSDT': 125,
            'ETHUSDT': 75,
            'ADAUSDT': 50,
            'SOLUSDT': 50,
            'DOGEUSDT': 25
        }
        
        # Historial de cálculos
        self.leverage_history: List[LeverageResult] = []
        
        # Métricas de performance
        self.total_calculations = 0
        self.avg_leverage = 0.0
        self.leverage_distribution = {}
        
        logger.info("LeverageCalculator inicializado")
    
    async def calculate_optimal_leverage(
        self,
        symbol: str,
        confidence: float,
        volatility: float,
        correlation: float = 0.0,
        drawdown: float = 0.0,
        market_conditions: str = "normal"
    ) -> LeverageResult:
        """
        Calcula el leverage óptimo para una posición
        
        Args:
            symbol: Símbolo a tradear
            confidence: Confianza del modelo ML (0-1)
            volatility: Volatilidad del símbolo (0-1)
            correlation: Correlación con otras posiciones (0-1)
            drawdown: Drawdown actual del portfolio (0-1)
            market_conditions: Condiciones del mercado
            
        Returns:
            Resultado del cálculo de leverage
        """
        try:
            self.total_calculations += 1
            
            # Crear factores de leverage
            factors = LeverageFactors(
                confidence=confidence,
                volatility=volatility,
                correlation=correlation,
                drawdown=drawdown,
                market_conditions=market_conditions,
                symbol_risk=self._calculate_symbol_risk(symbol),
                portfolio_risk=self._calculate_portfolio_risk()
            )
            
            # Calcular leverage base
            base_leverage = await self._calculate_base_leverage(factors)
            
            # Aplicar ajustes dinámicos
            adjusted_leverage = await self._apply_dynamic_adjustments(base_leverage, factors)
            
            # Aplicar límites de seguridad
            final_leverage = await self._apply_safety_limits(adjusted_leverage, symbol, factors)
            
            # Calcular score de riesgo
            risk_score = await self._calculate_risk_score(final_leverage, factors)
            
            # Generar reasoning
            reasoning = await self._generate_reasoning(final_leverage, factors)
            
            # Crear resultado
            result = LeverageResult(
                leverage=final_leverage,
                confidence=confidence,
                factors=factors,
                reasoning=reasoning,
                risk_score=risk_score,
                timestamp=datetime.now()
            )
            
            # Agregar al historial
            self.leverage_history.append(result)
            self._update_metrics(result)
            
            logger.debug(
                f"Leverage calculado para {symbol}: {final_leverage}x "
                f"(Confianza: {confidence:.2f}, Volatilidad: {volatility:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculando leverage para {symbol}: {e}")
            # Retornar leverage conservador en caso de error
            return LeverageResult(
                leverage=5,
                confidence=confidence,
                factors=factors,
                reasoning="Error en cálculo, usando leverage conservador",
                risk_score=0.8,
                timestamp=datetime.now()
            )
    
    async def _calculate_base_leverage(self, factors: LeverageFactors) -> int:
        """Calcula el leverage base según la estrategia configurada"""
        try:
            if self.leverage_config.dynamic_leverage.enabled:
                # Leverage dinámico basado en confianza
                base_leverage = self.leverage_config.dynamic_leverage.base_leverage
                
                # Ajustar por confianza
                confidence_multiplier = self._get_confidence_multiplier(factors.confidence)
                leverage = int(base_leverage * confidence_multiplier)
                
            else:
                # Leverage fijo por símbolo
                leverage = self.leverage_config.fixed_leverage.leverage_by_symbol.get(
                    factors.symbol, self.leverage_config.dynamic_leverage.base_leverage
                )
            
            return leverage
            
        except Exception as e:
            logger.error(f"Error calculando leverage base: {e}")
            return self.leverage_config.dynamic_leverage.base_leverage
    
    def _get_confidence_multiplier(self, confidence: float) -> float:
        """Obtiene el multiplicador de leverage basado en confianza"""
        try:
            multipliers = self.leverage_config.dynamic_leverage.confidence_multipliers
            
            if confidence >= 0.9:
                return multipliers.high_confidence
            elif confidence >= 0.7:
                return multipliers.medium_confidence
            elif confidence >= 0.5:
                return multipliers.low_confidence
            else:
                return multipliers.very_low_confidence
                
        except Exception as e:
            logger.error(f"Error obteniendo multiplicador de confianza: {e}")
            return 1.0
    
    async def _apply_dynamic_adjustments(
        self,
        base_leverage: int,
        factors: LeverageFactors
    ) -> int:
        """Aplica ajustes dinámicos al leverage base"""
        try:
            adjusted_leverage = base_leverage
            
            # Ajuste por volatilidad
            volatility_adjustment = self._calculate_volatility_adjustment(factors.volatility)
            adjusted_leverage = int(adjusted_leverage * volatility_adjustment)
            
            # Ajuste por correlación
            correlation_adjustment = self._calculate_correlation_adjustment(factors.correlation)
            adjusted_leverage = int(adjusted_leverage * correlation_adjustment)
            
            # Ajuste por drawdown
            drawdown_adjustment = self._calculate_drawdown_adjustment(factors.drawdown)
            adjusted_leverage = int(adjusted_leverage * drawdown_adjustment)
            
            # Ajuste por condiciones del mercado
            market_adjustment = self._calculate_market_adjustment(factors.market_conditions)
            adjusted_leverage = int(adjusted_leverage * market_adjustment)
            
            return max(1, adjusted_leverage)  # Mínimo leverage 1x
            
        except Exception as e:
            logger.error(f"Error aplicando ajustes dinámicos: {e}")
            return base_leverage
    
    def _calculate_volatility_adjustment(self, volatility: float) -> float:
        """Calcula ajuste de leverage por volatilidad"""
        try:
            # Volatilidad alta = leverage menor
            if volatility > 0.05:  # >5% volatilidad
                return 0.5  # Reducir 50%
            elif volatility > 0.03:  # >3% volatilidad
                return 0.7  # Reducir 30%
            elif volatility > 0.01:  # >1% volatilidad
                return 0.9  # Reducir 10%
            else:
                return 1.0  # Sin ajuste
                
        except Exception as e:
            logger.error(f"Error calculando ajuste de volatilidad: {e}")
            return 1.0
    
    def _calculate_correlation_adjustment(self, correlation: float) -> float:
        """Calcula ajuste de leverage por correlación"""
        try:
            # Correlación alta = leverage menor (diversificación)
            if correlation > 0.8:
                return 0.6  # Reducir 40%
            elif correlation > 0.6:
                return 0.8  # Reducir 20%
            elif correlation > 0.4:
                return 0.9  # Reducir 10%
            else:
                return 1.0  # Sin ajuste
                
        except Exception as e:
            logger.error(f"Error calculando ajuste de correlación: {e}")
            return 1.0
    
    def _calculate_drawdown_adjustment(self, drawdown: float) -> float:
        """Calcula ajuste de leverage por drawdown"""
        try:
            # Drawdown alto = leverage menor
            if drawdown > 0.15:  # >15% drawdown
                return 0.5  # Reducir 50%
            elif drawdown > 0.10:  # >10% drawdown
                return 0.7  # Reducir 30%
            elif drawdown > 0.05:  # >5% drawdown
                return 0.9  # Reducir 10%
            else:
                return 1.0  # Sin ajuste
                
        except Exception as e:
            logger.error(f"Error calculando ajuste de drawdown: {e}")
            return 1.0
    
    def _calculate_market_adjustment(self, market_conditions: str) -> float:
        """Calcula ajuste de leverage por condiciones del mercado"""
        try:
            adjustments = {
                'extreme_volatility': 0.3,  # Reducir 70%
                'high_volatility': 0.6,     # Reducir 40%
                'normal': 1.0,              # Sin ajuste
                'low_volatility': 1.2,      # Aumentar 20%
                'stable': 1.1               # Aumentar 10%
            }
            
            return adjustments.get(market_conditions, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando ajuste de mercado: {e}")
            return 1.0
    
    async def _apply_safety_limits(
        self,
        leverage: int,
        symbol: str,
        factors: LeverageFactors
    ) -> int:
        """Aplica límites de seguridad al leverage"""
        try:
            # Límite mínimo
            min_leverage = self.leverage_config.dynamic_leverage.min_leverage
            leverage = max(leverage, min_leverage)
            
            # Límite máximo
            max_leverage = self.leverage_config.dynamic_leverage.max_leverage
            leverage = min(leverage, max_leverage)
            
            # Límite por símbolo
            symbol_limit = self.symbol_leverage_limits.get(symbol, max_leverage)
            leverage = min(leverage, symbol_limit)
            
            # Límite por riesgo del símbolo
            if factors.symbol_risk > 0.8:  # Alto riesgo
                leverage = min(leverage, 10)
            elif factors.symbol_risk > 0.6:  # Riesgo medio-alto
                leverage = min(leverage, 15)
            
            # Límite por riesgo del portfolio
            if factors.portfolio_risk > 0.8:  # Alto riesgo del portfolio
                leverage = min(leverage, 8)
            elif factors.portfolio_risk > 0.6:  # Riesgo medio-alto del portfolio
                leverage = min(leverage, 12)
            
            return leverage
            
        except Exception as e:
            logger.error(f"Error aplicando límites de seguridad: {e}")
            return leverage
    
    def _calculate_symbol_risk(self, symbol: str) -> float:
        """Calcula el riesgo específico de un símbolo"""
        try:
            # Riesgo base por símbolo (simplificado)
            risk_scores = {
                'BTCUSDT': 0.3,   # Bajo riesgo
                'ETHUSDT': 0.4,   # Riesgo medio-bajo
                'ADAUSDT': 0.6,   # Riesgo medio
                'SOLUSDT': 0.7,   # Riesgo medio-alto
                'DOGEUSDT': 0.8   # Alto riesgo
            }
            
            return risk_scores.get(symbol, 0.5)  # Riesgo medio por defecto
            
        except Exception as e:
            logger.error(f"Error calculando riesgo del símbolo {symbol}: {e}")
            return 0.5
    
    def _calculate_portfolio_risk(self) -> float:
        """Calcula el riesgo actual del portfolio"""
        try:
            # En un sistema real, esto se calcularía basado en:
            # - Número de posiciones abiertas
            # - Correlación entre posiciones
            # - Concentración de capital
            # - Drawdown actual
            
            # Por ahora, retornar un valor simulado
            return 0.4  # Riesgo medio
            
        except Exception as e:
            logger.error(f"Error calculando riesgo del portfolio: {e}")
            return 0.5
    
    async def _calculate_risk_score(
        self,
        leverage: int,
        factors: LeverageFactors
    ) -> float:
        """Calcula el score de riesgo del leverage"""
        try:
            # Score base basado en leverage
            leverage_score = min(leverage / 30.0, 1.0)  # Normalizar a 0-1
            
            # Ajustar por factores de riesgo
            volatility_penalty = factors.volatility * 0.3
            correlation_penalty = factors.correlation * 0.2
            drawdown_penalty = factors.drawdown * 0.3
            symbol_penalty = factors.symbol_risk * 0.2
            
            # Calcular score final
            risk_score = leverage_score + volatility_penalty + correlation_penalty + drawdown_penalty + symbol_penalty
            
            return min(risk_score, 1.0)  # Máximo 1.0
            
        except Exception as e:
            logger.error(f"Error calculando score de riesgo: {e}")
            return 0.5
    
    async def _generate_reasoning(
        self,
        leverage: int,
        factors: LeverageFactors
    ) -> str:
        """Genera explicación del cálculo de leverage"""
        try:
            reasoning_parts = []
            
            # Confianza
            if factors.confidence >= 0.9:
                reasoning_parts.append("Alta confianza del modelo")
            elif factors.confidence >= 0.7:
                reasoning_parts.append("Confianza media del modelo")
            else:
                reasoning_parts.append("Baja confianza del modelo")
            
            # Volatilidad
            if factors.volatility > 0.05:
                reasoning_parts.append("Alta volatilidad reduce leverage")
            elif factors.volatility < 0.01:
                reasoning_parts.append("Baja volatilidad permite mayor leverage")
            
            # Correlación
            if factors.correlation > 0.8:
                reasoning_parts.append("Alta correlación reduce leverage")
            elif factors.correlation < 0.3:
                reasoning_parts.append("Baja correlación permite mayor leverage")
            
            # Drawdown
            if factors.drawdown > 0.1:
                reasoning_parts.append("Drawdown alto reduce leverage")
            elif factors.drawdown < 0.02:
                reasoning_parts.append("Drawdown bajo permite mayor leverage")
            
            # Condiciones del mercado
            if factors.market_conditions == "extreme_volatility":
                reasoning_parts.append("Condiciones extremas requieren leverage conservador")
            elif factors.market_conditions == "stable":
                reasoning_parts.append("Mercado estable permite leverage moderado")
            
            # Score de riesgo
            if factors.portfolio_risk > 0.8:
                reasoning_parts.append("Alto riesgo del portfolio limita leverage")
            
            return "; ".join(reasoning_parts) if reasoning_parts else "Leverage calculado con configuración estándar"
            
        except Exception as e:
            logger.error(f"Error generando reasoning: {e}")
            return "Error en cálculo de reasoning"
    
    def _update_metrics(self, result: LeverageResult):
        """Actualiza las métricas del calculador"""
        try:
            # Actualizar promedio
            total_leverage = sum(r.leverage for r in self.leverage_history)
            self.avg_leverage = total_leverage / len(self.leverage_history)
            
            # Actualizar distribución
            leverage_range = (result.leverage // 5) * 5  # Agrupar en rangos de 5
            self.leverage_distribution[leverage_range] = self.leverage_distribution.get(leverage_range, 0) + 1
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    def get_leverage_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del calculador de leverage"""
        try:
            if not self.leverage_history:
                return {
                    'total_calculations': 0,
                    'avg_leverage': 0.0,
                    'min_leverage': 0,
                    'max_leverage': 0,
                    'leverage_distribution': {},
                    'avg_risk_score': 0.0
                }
            
            leverages = [r.leverage for r in self.leverage_history]
            risk_scores = [r.risk_score for r in self.leverage_history]
            
            return {
                'total_calculations': len(self.leverage_history),
                'avg_leverage': np.mean(leverages),
                'min_leverage': np.min(leverages),
                'max_leverage': np.max(leverages),
                'std_leverage': np.std(leverages),
                'leverage_distribution': self.leverage_distribution,
                'avg_risk_score': np.mean(risk_scores),
                'avg_confidence': np.mean([r.confidence for r in self.leverage_history]),
                'avg_volatility': np.mean([r.factors.volatility for r in self.leverage_history])
            }
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            return {}
    
    def get_recent_leverage_history(self, limit: int = 10) -> List[LeverageResult]:
        """Obtiene el historial reciente de cálculos de leverage"""
        return self.leverage_history[-limit:] if self.leverage_history else []
    
    def export_leverage_history(self, output_file: Optional[str] = None) -> str:
        """Exporta el historial de cálculos de leverage"""
        try:
            if output_file is None:
                output_file = f"leverage_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = Path("logs/enterprise/trading/leverage") / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Preparar datos para exportación
            export_data = {
                'leverage_history': [
                    {
                        'leverage': r.leverage,
                        'confidence': r.confidence,
                        'factors': {
                            'confidence': r.factors.confidence,
                            'volatility': r.factors.volatility,
                            'correlation': r.factors.correlation,
                            'drawdown': r.factors.drawdown,
                            'market_conditions': r.factors.market_conditions,
                            'symbol_risk': r.factors.symbol_risk,
                            'portfolio_risk': r.factors.portfolio_risk
                        },
                        'reasoning': r.reasoning,
                        'risk_score': r.risk_score,
                        'timestamp': r.timestamp.isoformat()
                    }
                    for r in self.leverage_history
                ],
                'statistics': self.get_leverage_statistics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            import json
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Historial de leverage exportado: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando historial de leverage: {e}")
            return None
    
    async def reset_leverage_limits(self):
        """Resetea los límites de leverage a valores conservadores"""
        try:
            # Reducir límites máximos temporalmente
            self.leverage_config.dynamic_leverage.max_leverage = 10
            self.leverage_config.dynamic_leverage.base_leverage = 3
            
            logger.info("🛡️ Límites de leverage resetados a valores conservadores")
            
        except Exception as e:
            logger.error(f"Error reseteando límites de leverage: {e}")
    
    async def emergency_leverage_reduction(self):
        """Reduce el leverage a valores mínimos en caso de emergencia"""
        try:
            # Establecer leverage mínimo para todas las posiciones
            self.leverage_config.dynamic_leverage.max_leverage = 2
            self.leverage_config.dynamic_leverage.base_leverage = 1
            
            logger.warning("🚨 LEVERAGE REDUCIDO A MÍNIMOS - Modo de emergencia activado")
            
        except Exception as e:
            logger.error(f"Error en reducción de emergencia de leverage: {e}")
