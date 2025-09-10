# Ruta: core/trading/portfolio_optimizer.py
"""
🧠 portfolio_optimizer.py - Optimizador Inteligente de Portfolio

Gestor inteligente de portfolio multi-símbolo que optimiza asignación de capital,
gestiona correlaciones, ejecuta rebalances automáticos y maximiza diversificación.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy import linalg
import json

# Imports del proyecto
from config.config_loader import ConfigLoader
from core.data.database import db_manager
from .position_manager import position_manager
from .signal_processor import signal_processor
# from .executor import trading_executor  # Circular import - se importa dinámicamente
from .risk_manager import risk_manager

logger = logging.getLogger(__name__)

@dataclass
class PortfolioState:
    """
    Representa el estado actual del portfolio multi-símbolo
    """
    total_balance: float
    available_balance: float
    invested_balance: float
    
    # Exposición por símbolo
    symbol_allocations: Dict[str, float]  # Porcentaje actual por símbolo
    symbol_pnl: Dict[str, float]  # P&L por símbolo
    symbol_exposure: Dict[str, float]  # Exposición en USD por símbolo
    
    # Posiciones activas
    active_positions: Dict[str, int]  # Número de posiciones por símbolo
    position_details: Dict[str, List[Dict]]  # Detalles de posiciones por símbolo
    
    # Métricas de portfolio
    total_unrealized_pnl: float
    total_realized_pnl: float
    portfolio_return: float
    portfolio_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Correlaciones
    correlation_matrix: Dict[str, Dict[str, float]]
    correlation_risk_score: float
    
    # Diversificación
    diversification_ratio: float
    concentration_risk: float
    
    # Metadata
    last_rebalance: datetime
    rebalance_needed: bool
    update_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AllocationTarget:
    """
    Objetivo de asignación para un símbolo específico
    """
    symbol: str
    target_allocation_pct: float  # Objetivo de asignación %
    current_allocation_pct: float  # Asignación actual %
    max_allocation_pct: float  # Máximo permitido %
    min_allocation_pct: float  # Mínimo permitido %
    
    # Factores de optimización
    expected_return: float
    volatility: float
    correlation_penalty: float
    momentum_score: float
    ml_confidence_avg: float
    
    # Acciones requeridas
    action_required: str  # INCREASE, DECREASE, HOLD
    target_change_pct: float  # Cambio necesario en %
    priority_score: float  # Prioridad de rebalance

class PortfolioOptimizer:
    """
    Optimizador inteligente de portfolio multi-símbolo
    
    Responsabilidades:
    - Gestionar múltiples símbolos simultáneamente
    - Optimizar asignación de capital dinámicamente
    - Calcular correlaciones y gestionar riesgo de concentración
    - Rebalancear portfolio automáticamente
    - Adaptar estrategia según condiciones de mercado
    - Maximizar diversificación y ratio riesgo/retorno
    """
    
    def __init__(self):
        self.symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
        self.portfolio_state = None
        self.optimization_metrics = {
            'optimization_runs': 0,
            'optimization_latency_ms': 0.0,
            'allocation_changes': [],
            'constraint_violations': 0,
            'ml_signal_accuracy': {},
            'correlation_predictions': {},
            'rebalance_effectiveness': []
        }
        
        # Configuración de portfolio
        self.portfolio_config = user_config.get_value(['portfolio_optimization'], {})
        self.max_symbols = self.portfolio_config.get('max_symbols', 4)
        self.rebalance_threshold = self.portfolio_config.get('rebalance_threshold_pct', 5.0)
        self.max_correlation = self.portfolio_config.get('max_correlation_allowed', 0.7)
        self.min_allocation = self.portfolio_config.get('min_allocation_pct', 5.0)
        self.max_allocation = self.portfolio_config.get('max_allocation_pct', 40.0)
        
        # Límites de portfolio
        self.PORTFOLIO_LIMITS = {
            'max_symbols': 5,
            'max_allocation_single': 0.5,  # 50% máximo en un símbolo
            'max_correlation_exposure': 0.8,  # 80% máximo en símbolos correlacionados
            'min_diversification_ratio': 0.6,  # Mínima diversificación
            'max_portfolio_volatility': 0.25,  # 25% volatilidad máxima anualizada
            'emergency_cash_reserve': 0.05  # 5% en cash para emergencias
        }
        
        # Circuit breakers
        self.CIRCUIT_BREAKERS = {
            'daily_portfolio_loss': 0.05,  # 5% pérdida diaria → stop trading
            'correlation_spike': 0.9,  # Correlación > 90% → reduce exposición
            'volatility_spike': 3.0,  # 3x volatilidad normal → defensive mode
            'ml_confidence_drop': 0.4,  # Confianza < 40% → reduce allocations
        }
        
        logger.info(f"[PortfolioOptimizer] Inicializado | Símbolos: {len(self.symbols)} | Threshold: {self.rebalance_threshold}%")
    
    async def get_portfolio_state(self) -> PortfolioState:
        """
        Obtener estado completo actual del portfolio
        """
        try:
            start_time = datetime.now()
            
            # Obtener balance total
            total_balance = position_manager.get_total_balance()
            available_balance = position_manager.get_available_balance()
            invested_balance = total_balance - available_balance
            
            # Obtener posiciones por símbolo
            symbol_allocations = {}
            symbol_pnl = {}
            symbol_exposure = {}
            active_positions = {}
            position_details = {}
            
            for symbol in self.symbols:
                positions = position_manager.get_positions_by_symbol(symbol)
                active_positions[symbol] = len(positions)
                position_details[symbol] = [pos.to_dict() for pos in positions]
                
                # Calcular exposición y P&L por símbolo
                symbol_exposure[symbol] = sum(pos.size_qty * pos.current_price for pos in positions)
                symbol_pnl[symbol] = sum(pos.unrealized_pnl for pos in positions)
                
                # Calcular asignación porcentual
                if total_balance > 0:
                    symbol_allocations[symbol] = symbol_exposure[symbol] / total_balance
                else:
                    symbol_allocations[symbol] = 0.0
            
            # Calcular correlaciones
            correlation_matrix = await self.calculate_symbol_correlations()
            correlation_risk_score = self._calculate_correlation_risk(correlation_matrix)
            
            # Calcular métricas de diversificación
            diversification_metrics = self.calculate_diversification_metrics(symbol_allocations)
            
            # Calcular métricas de portfolio
            total_unrealized_pnl = sum(symbol_pnl.values())
            total_realized_pnl = position_manager.get_total_realized_pnl()
            portfolio_return = self._calculate_portfolio_return(symbol_allocations, symbol_pnl)
            portfolio_volatility = await self._calculate_portfolio_volatility(symbol_allocations)
            sharpe_ratio = self._calculate_sharpe_ratio(portfolio_return, portfolio_volatility)
            max_drawdown = await self._calculate_max_drawdown()
            
            # Verificar si se necesita rebalance
            rebalance_needed, _ = await self.should_rebalance()
            
            self.portfolio_state = PortfolioState(
                total_balance=total_balance,
                available_balance=available_balance,
                invested_balance=invested_balance,
                symbol_allocations=symbol_allocations,
                symbol_pnl=symbol_pnl,
                symbol_exposure=symbol_exposure,
                active_positions=active_positions,
                position_details=position_details,
                total_unrealized_pnl=total_unrealized_pnl,
                total_realized_pnl=total_realized_pnl,
                portfolio_return=portfolio_return,
                portfolio_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                correlation_matrix=correlation_matrix,
                correlation_risk_score=correlation_risk_score,
                diversification_ratio=diversification_metrics.get('diversification_ratio', 0.0),
                concentration_risk=diversification_metrics.get('concentration_index', 0.0),
                last_rebalance=datetime.now() - timedelta(days=1),  # Placeholder
                rebalance_needed=rebalance_needed
            )
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self.optimization_metrics['optimization_latency_ms'] = latency
            
            logger.debug(f"[PortfolioOptimizer] Estado actualizado | Balance: ${total_balance:,.2f} | P&L: ${total_unrealized_pnl:,.2f}")
            return self.portfolio_state
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error obteniendo estado del portfolio: {e}")
            return None
    
    async def calculate_symbol_correlations(self, days_back: int = 30) -> Dict[str, Dict[str, float]]:
        """
        Calcula matriz de correlaciones entre símbolos
        """
        try:
            correlation_matrix = {}
            
            for symbol1 in self.symbols:
                correlation_matrix[symbol1] = {}
                
                for symbol2 in self.symbols:
                    if symbol1 == symbol2:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        # Obtener datos de precios para ambos símbolos
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=days_back)
                        
                        data1 = db_manager.get_market_data(symbol1, start_time, end_time, limit=days_back*24)
                        data2 = db_manager.get_market_data(symbol2, start_time, end_time, limit=days_back*24)
                        
                        if data1.empty or data2.empty:
                            correlation_matrix[symbol1][symbol2] = 0.0
                            continue
                        
                        # Calcular retornos
                        returns1 = data1['close'].pct_change().dropna()
                        returns2 = data2['close'].pct_change().dropna()
                        
                        # Alinear series temporales
                        common_index = returns1.index.intersection(returns2.index)
                        if len(common_index) < 10:  # Mínimo de datos
                            correlation_matrix[symbol1][symbol2] = 0.0
                            continue
                        
                        aligned_returns1 = returns1.loc[common_index]
                        aligned_returns2 = returns2.loc[common_index]
                        
                        # Calcular correlación
                        correlation = aligned_returns1.corr(aligned_returns2)
                        correlation_matrix[symbol1][symbol2] = float(correlation) if not np.isnan(correlation) else 0.0
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando correlaciones: {e}")
            return {symbol: {s: 0.0 for s in self.symbols} for symbol in self.symbols}
    
    def _calculate_correlation_risk(self, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """
        Calcula score de riesgo por correlación
        """
        try:
            max_correlation = 0.0
            high_correlation_pairs = 0
            
            for symbol1 in self.symbols:
                for symbol2 in self.symbols:
                    if symbol1 != symbol2:
                        corr = abs(correlation_matrix.get(symbol1, {}).get(symbol2, 0.0))
                        max_correlation = max(max_correlation, corr)
                        if corr > self.max_correlation:
                            high_correlation_pairs += 1
            
            # Score de 0-1, donde 1 es máximo riesgo
            correlation_risk = min(max_correlation, 1.0)
            if high_correlation_pairs > 0:
                correlation_risk += 0.2 * min(high_correlation_pairs / len(self.symbols), 1.0)
            
            return min(correlation_risk, 1.0)
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando riesgo de correlación: {e}")
            return 0.5
    
    def calculate_diversification_metrics(self, allocations: Dict[str, float]) -> Dict[str, float]:
        """
        Calcula métricas de diversificación del portfolio
        """
        try:
            if not allocations or sum(allocations.values()) == 0:
                return {
                    'diversification_ratio': 0.0,
                    'concentration_index': 1.0,
                    'effective_positions': 0.0,
                    'correlation_adjusted_concentration': 1.0
                }
            
            # Normalizar asignaciones
            total_allocation = sum(allocations.values())
            normalized_allocations = {k: v/total_allocation for k, v in allocations.items()}
            
            # Diversification ratio (1 / HHI)
            hhi = sum(w**2 for w in normalized_allocations.values())
            diversification_ratio = 1.0 / hhi if hhi > 0 else 0.0
            
            # Concentration index (HHI)
            concentration_index = hhi
            
            # Effective number of positions
            effective_positions = 1.0 / hhi if hhi > 0 else 0.0
            
            # Correlation-adjusted concentration (simplified)
            correlation_adjusted_concentration = concentration_index  # Placeholder
            
            return {
                'diversification_ratio': diversification_ratio,
                'concentration_index': concentration_index,
                'effective_positions': effective_positions,
                'correlation_adjusted_concentration': correlation_adjusted_concentration
            }
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando métricas de diversificación: {e}")
            return {
                'diversification_ratio': 0.0,
                'concentration_index': 1.0,
                'effective_positions': 0.0,
                'correlation_adjusted_concentration': 1.0
            }
    
    def _calculate_portfolio_return(self, allocations: Dict[str, float], symbol_pnl: Dict[str, float]) -> float:
        """
        Calcula retorno del portfolio
        """
        try:
            if not allocations or sum(allocations.values()) == 0:
                return 0.0
            
            total_allocation = sum(allocations.values())
            if total_allocation == 0:
                return 0.0
            
            # Calcular retorno ponderado
            weighted_return = 0.0
            for symbol in self.symbols:
                if symbol in allocations and symbol in symbol_pnl:
                    weight = allocations[symbol] / total_allocation
                    # P&L como porcentaje del balance total
                    symbol_return = symbol_pnl[symbol] / (total_allocation * 100) if total_allocation > 0 else 0.0
                    weighted_return += weight * symbol_return
            
            return weighted_return
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando retorno del portfolio: {e}")
            return 0.0
    
    async def _calculate_portfolio_volatility(self, allocations: Dict[str, float]) -> float:
        """
        Calcula volatilidad del portfolio
        """
        try:
            if not allocations or sum(allocations.values()) == 0:
                return 0.0
            
            # Obtener datos históricos para calcular volatilidad
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            
            symbol_volatilities = {}
            for symbol in self.symbols:
                if symbol in allocations and allocations[symbol] > 0:
                    data = db_manager.get_market_data(symbol, start_time, end_time, limit=720)
                    if not data.empty:
                        returns = data['close'].pct_change().dropna()
                        volatility = returns.std() * np.sqrt(24)  # Anualizada
                        symbol_volatilities[symbol] = volatility
                    else:
                        symbol_volatilities[symbol] = 0.0
            
            # Calcular volatilidad del portfolio (simplificada)
            total_allocation = sum(allocations.values())
            if total_allocation == 0:
                return 0.0
            
            portfolio_volatility = 0.0
            for symbol in self.symbols:
                if symbol in allocations and symbol in symbol_volatilities:
                    weight = allocations[symbol] / total_allocation
                    portfolio_volatility += (weight * symbol_volatilities[symbol]) ** 2
            
            return np.sqrt(portfolio_volatility)
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando volatilidad del portfolio: {e}")
            return 0.0
    
    def _calculate_sharpe_ratio(self, portfolio_return: float, portfolio_volatility: float) -> float:
        """
        Calcula ratio de Sharpe del portfolio
        """
        try:
            if portfolio_volatility == 0:
                return 0.0
            
            # Asumir tasa libre de riesgo del 2% anual
            risk_free_rate = 0.02
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
            return sharpe_ratio
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando ratio de Sharpe: {e}")
            return 0.0
    
    async def _calculate_max_drawdown(self) -> float:
        """
        Calcula máximo drawdown del portfolio
        """
        try:
            # Obtener historial de balance
            # Placeholder - implementar con datos históricos reales
            return 0.0
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando máximo drawdown: {e}")
            return 0.0

    async def optimize_portfolio(self) -> Dict[str, AllocationTarget]:
        """
        Optimiza asignación completa del portfolio
        """
        try:
            start_time = datetime.now()
            self.optimization_metrics['optimization_runs'] += 1
            
            # Obtener estado actual
            portfolio_state = await self.get_portfolio_state()
            if not portfolio_state:
                return {}
            
            # Calcular asignaciones óptimas
            optimal_allocations = await self.calculate_optimal_allocations(self.symbols)
            
            # Aplicar restricciones de riesgo
            constrained_allocations = await self.apply_risk_constraints(optimal_allocations)
            
            # Incorporar señales ML
            ml_adjusted_allocations = await self.incorporate_ml_signals(self.symbols)
            
            # Combinar asignaciones
            final_allocations = self._combine_allocation_factors(
                constrained_allocations, 
                ml_adjusted_allocations
            )
            
            # Crear targets de asignación
            targets = {}
            for symbol in self.symbols:
                current_pct = portfolio_state.symbol_allocations.get(symbol, 0.0)
                target_pct = final_allocations.get(symbol, 0.0)
                
                # Obtener configuración del símbolo
                symbol_config = user_config.get_value(['symbols', symbol], {})
                max_pct = symbol_config.get('max_allocation_pct', self.max_allocation) / 100.0
                min_pct = symbol_config.get('min_allocation_pct', self.min_allocation) / 100.0
                
                # Calcular cambio necesario
                change_pct = target_pct - current_pct
                action = "HOLD"
                if abs(change_pct) > self.rebalance_threshold / 100.0:
                    action = "INCREASE" if change_pct > 0 else "DECREASE"
                
                # Evaluar atractivo del símbolo
                attractiveness = await self.evaluate_symbol_attractiveness(symbol)
                
                targets[symbol] = AllocationTarget(
                    symbol=symbol,
                    target_allocation_pct=target_pct,
                    current_allocation_pct=current_pct,
                    max_allocation_pct=max_pct,
                    min_allocation_pct=min_pct,
                    expected_return=attractiveness.get('expected_return', 0.0),
                    volatility=attractiveness.get('volatility', 0.0),
                    correlation_penalty=attractiveness.get('correlation_penalty', 0.0),
                    momentum_score=attractiveness.get('momentum_score', 0.0),
                    ml_confidence_avg=attractiveness.get('ml_confidence_avg', 0.0),
                    action_required=action,
                    target_change_pct=change_pct,
                    priority_score=abs(change_pct) * attractiveness.get('expected_return', 0.0)
                )
            
            # Actualizar métricas
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self.optimization_metrics['optimization_latency_ms'] = latency
            
            logger.info(f"[PortfolioOptimizer] Optimización completada | Latencia: {latency:.1f}ms")
            return targets
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error optimizando portfolio: {e}")
            return {}
    
    async def calculate_optimal_allocations(self, symbols: List[str]) -> Dict[str, float]:
        """
        Calcula asignaciones óptimas usando teoría moderna de portfolio
        """
        try:
            # Obtener retornos esperados y volatilidades
            expected_returns = {}
            volatilities = {}
            
            for symbol in symbols:
                attractiveness = await self.evaluate_symbol_attractiveness(symbol)
                expected_returns[symbol] = attractiveness.get('expected_return', 0.0)
                volatilities[symbol] = attractiveness.get('volatility', 0.0)
            
            # Obtener matriz de correlaciones
            correlation_matrix = await self.calculate_symbol_correlations()
            
            # Construir matriz de covarianza
            cov_matrix = self._build_covariance_matrix(symbols, volatilities, correlation_matrix)
            
            # Optimización de Markowitz
            optimal_weights = self._markowitz_optimization(
                list(expected_returns.values()),
                cov_matrix,
                risk_aversion=1.0
            )
            
            # Convertir a diccionario
            allocations = {}
            for i, symbol in enumerate(symbols):
                allocations[symbol] = max(0.0, optimal_weights[i])
            
            # Normalizar para que sumen 1
            total_weight = sum(allocations.values())
            if total_weight > 0:
                allocations = {k: v/total_weight for k, v in allocations.items()}
            
            return allocations
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando asignaciones óptimas: {e}")
            return {symbol: 1.0/len(symbols) for symbol in symbols}
    
    def _build_covariance_matrix(self, symbols: List[str], volatilities: Dict[str, float], 
                                correlation_matrix: Dict[str, Dict[str, float]]) -> np.ndarray:
        """
        Construye matriz de covarianza a partir de volatilidades y correlaciones
        """
        try:
            n = len(symbols)
            cov_matrix = np.zeros((n, n))
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    vol1 = volatilities.get(symbol1, 0.0)
                    vol2 = volatilities.get(symbol2, 0.0)
                    corr = correlation_matrix.get(symbol1, {}).get(symbol2, 0.0)
                    
                    cov_matrix[i, j] = vol1 * vol2 * corr
            
            return cov_matrix
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error construyendo matriz de covarianza: {e}")
            return np.eye(len(symbols))
    
    def _markowitz_optimization(self, expected_returns: List[float], cov_matrix: np.ndarray, 
                               risk_aversion: float = 1.0) -> np.ndarray:
        """
        Optimización de Markowitz con restricciones
        """
        try:
            n = len(expected_returns)
            
            # Función objetivo: minimizar w' * Σ * w - λ * μ' * w
            def objective(weights):
                portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
                portfolio_return = np.dot(weights, expected_returns)
                return portfolio_variance - risk_aversion * portfolio_return
            
            # Restricciones
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Suma de pesos = 1
            ]
            
            # Límites de pesos
            bounds = [(0.0, 1.0) for _ in range(n)]
            
            # Punto inicial (igual peso)
            x0 = np.ones(n) / n
            
            # Optimización
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
            
            if result.success:
                return result.x
            else:
                # Fallback: igual peso
                return np.ones(n) / n
                
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error en optimización de Markowitz: {e}")
            return np.ones(len(expected_returns)) / len(expected_returns)
    
    async def evaluate_symbol_attractiveness(self, symbol: str) -> Dict[str, float]:
        """
        Evalúa atractivo de inversión en un símbolo
        """
        try:
            # Obtener datos históricos
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            data = db_manager.get_market_data(symbol, start_time, end_time, limit=720)
            
            if data.empty:
                return {
                    'expected_return': 0.0,
                    'volatility': 0.0,
                    'sharpe_ratio': 0.0,
                    'momentum_score': 0.0,
                    'ml_confidence_avg': 0.0,
                    'correlation_penalty': 0.0
                }
            
            # Calcular retornos
            returns = data['close'].pct_change().dropna()
            
            # Expected return (media de retornos)
            expected_return = returns.mean() * 24 * 365  # Anualizado
            
            # Volatilidad
            volatility = returns.std() * np.sqrt(24 * 365)  # Anualizada
            
            # Sharpe ratio
            risk_free_rate = 0.02
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0.0
            
            # Momentum score (retorno de los últimos 7 días)
            recent_returns = returns.tail(168)  # 7 días * 24 horas
            momentum_score = recent_returns.mean() * 24 * 365 if len(recent_returns) > 0 else 0.0
            
            # ML confidence promedio (simulado)
            ml_confidence_avg = 0.7  # Placeholder - integrar con signal_processor
            
            # Correlation penalty (simulado)
            correlation_penalty = 0.0  # Placeholder
            
            return {
                'expected_return': expected_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'momentum_score': momentum_score,
                'ml_confidence_avg': ml_confidence_avg,
                'correlation_penalty': correlation_penalty
            }
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error evaluando atractivo de {symbol}: {e}")
            return {
                'expected_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'momentum_score': 0.0,
                'ml_confidence_avg': 0.0,
                'correlation_penalty': 0.0
            }
    
    async def apply_risk_constraints(self, allocations: Dict[str, float]) -> Dict[str, float]:
        """
        Aplica restricciones de riesgo a asignaciones propuestas
        """
        try:
            constrained_allocations = allocations.copy()
            
            # Aplicar límites por símbolo
            for symbol in self.symbols:
                if symbol in constrained_allocations:
                    symbol_config = user_config.get_value(['symbols', symbol], {})
                    max_pct = symbol_config.get('max_allocation_pct', self.max_allocation) / 100.0
                    min_pct = symbol_config.get('min_allocation_pct', self.min_allocation) / 100.0
                    
                    constrained_allocations[symbol] = np.clip(
                        constrained_allocations[symbol], 
                        min_pct, 
                        max_pct
                    )
            
            # Normalizar para que sumen 1
            total_allocation = sum(constrained_allocations.values())
            if total_allocation > 0:
                constrained_allocations = {k: v/total_allocation for k, v in constrained_allocations.items()}
            
            # Aplicar límite de volatilidad del portfolio
            portfolio_vol = await self._calculate_portfolio_volatility(constrained_allocations)
            if portfolio_vol > self.PORTFOLIO_LIMITS['max_portfolio_volatility']:
                # Reducir asignaciones proporcionalmente
                reduction_factor = self.PORTFOLIO_LIMITS['max_portfolio_volatility'] / portfolio_vol
                constrained_allocations = {k: v * reduction_factor for k, v in constrained_allocations.items()}
            
            return constrained_allocations
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error aplicando restricciones de riesgo: {e}")
            return allocations
    
    async def incorporate_ml_signals(self, symbols: List[str]) -> Dict[str, float]:
        """
        Incorpora señales ML en optimización de portfolio
        """
        try:
            ml_adjusted_allocations = {}
            
            for symbol in symbols:
                # Obtener señal ML del signal_processor
                try:
                    signal_quality = await signal_processor.process_signal(symbol, timeframe="1h")
                    ml_confidence = signal_quality.confidence
                    ml_quality_score = signal_quality.quality_score
                except Exception:
                    ml_confidence = 0.5
                    ml_quality_score = 0.5
                
                # Convertir confianza ML en factor de asignación
                # Mayor confianza = mayor asignación
                ml_factor = (ml_confidence + ml_quality_score) / 2.0
                ml_adjusted_allocations[symbol] = ml_factor
            
            # Normalizar factores ML
            total_ml_factor = sum(ml_adjusted_allocations.values())
            if total_ml_factor > 0:
                ml_adjusted_allocations = {k: v/total_ml_factor for k, v in ml_adjusted_allocations.items()}
            
            return ml_adjusted_allocations
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error incorporando señales ML: {e}")
            return {symbol: 1.0/len(symbols) for symbol in symbols}
    
    def _combine_allocation_factors(self, base_allocations: Dict[str, float], 
                                   ml_allocations: Dict[str, float]) -> Dict[str, float]:
        """
        Combina asignaciones base con factores ML
        """
        try:
            # Peso para cada factor
            base_weight = 0.6  # 60% asignación base
            ml_weight = 0.4    # 40% señales ML
            
            combined_allocations = {}
            for symbol in self.symbols:
                base_alloc = base_allocations.get(symbol, 0.0)
                ml_alloc = ml_allocations.get(symbol, 0.0)
                
                combined_allocations[symbol] = base_weight * base_alloc + ml_weight * ml_alloc
            
            # Normalizar
            total_allocation = sum(combined_allocations.values())
            if total_allocation > 0:
                combined_allocations = {k: v/total_allocation for k, v in combined_allocations.items()}
            
            return combined_allocations
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error combinando factores de asignación: {e}")
            return base_allocations

    async def should_rebalance(self) -> Tuple[bool, List[str]]:
        """
        Determina si se necesita rebalance
        """
        try:
            reasons = []
            
            # Obtener estado actual
            portfolio_state = await self.get_portfolio_state()
            if not portfolio_state:
                return False, ["No se pudo obtener estado del portfolio"]
            
            # Verificar desviaciones de asignación
            for symbol in self.symbols:
                current_pct = portfolio_state.symbol_allocations.get(symbol, 0.0)
                symbol_config = user_config.get_value(['symbols', symbol], {})
                target_pct = symbol_config.get('allocation_pct', 25.0) / 100.0  # Default 25%
                
                deviation = abs(current_pct - target_pct)
                if deviation > self.rebalance_threshold / 100.0:
                    reasons.append(f"{symbol}: desviación {deviation:.1%} > {self.rebalance_threshold/100:.1%}")
            
            # Verificar correlaciones altas
            if portfolio_state.correlation_risk_score > self.max_correlation:
                reasons.append(f"Correlación alta: {portfolio_state.correlation_risk_score:.1%}")
            
            # Verificar diversificación
            if portfolio_state.diversification_ratio < self.PORTFOLIO_LIMITS['min_diversification_ratio']:
                reasons.append(f"Diversificación baja: {portfolio_state.diversification_ratio:.1%}")
            
            # Verificar volatilidad del portfolio
            if portfolio_state.portfolio_volatility > self.PORTFOLIO_LIMITS['max_portfolio_volatility']:
                reasons.append(f"Volatilidad alta: {portfolio_state.portfolio_volatility:.1%}")
            
            rebalance_needed = len(reasons) > 0
            return rebalance_needed, reasons
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error verificando necesidad de rebalance: {e}")
            return False, [f"Error: {e}"]
    
    async def execute_rebalance(self, targets: Dict[str, AllocationTarget]) -> Dict[str, Any]:
        """
        Ejecuta rebalance del portfolio
        """
        try:
            start_time = datetime.now()
            rebalance_results = {
                'success': True,
                'orders_created': 0,
                'orders_failed': 0,
                'total_cost': 0.0,
                'execution_time_ms': 0.0,
                'errors': []
            }
            
            # Priorizar símbolos por urgencia de rebalance
            sorted_targets = sorted(
                targets.items(), 
                key=lambda x: x[1].priority_score, 
                reverse=True
            )
            
            # Ejecutar rebalance gradual
            await self.gradual_rebalance(dict(sorted_targets), steps=3)
            
            # Calcular métricas de ejecución
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            rebalance_results['execution_time_ms'] = execution_time
            
            logger.info(f"[PortfolioOptimizer] Rebalance ejecutado | Tiempo: {execution_time:.1f}ms")
            return rebalance_results
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error ejecutando rebalance: {e}")
            return {
                'success': False,
                'orders_created': 0,
                'orders_failed': 0,
                'total_cost': 0.0,
                'execution_time_ms': 0.0,
                'errors': [str(e)]
            }
    
    async def calculate_rebalance_orders(self, targets: Dict[str, AllocationTarget]) -> List[Dict]:
        """
        Calcula órdenes específicas para rebalance
        """
        try:
            orders = []
            portfolio_state = await self.get_portfolio_state()
            
            if not portfolio_state:
                return orders
            
            for symbol, target in targets.items():
                if target.action_required == "HOLD":
                    continue
                
                current_exposure = portfolio_state.symbol_exposure.get(symbol, 0.0)
                target_exposure = target.target_allocation_pct * portfolio_state.total_balance
                exposure_change = target_exposure - current_exposure
                
                if abs(exposure_change) < 10.0:  # Mínimo $10
                    continue
                
                # Determinar dirección de la orden
                side = "BUY" if exposure_change > 0 else "SELL"
                quantity_usd = abs(exposure_change)
                
                # Obtener precio actual (simulado)
                current_price = 50000.0  # Placeholder - obtener precio real
                quantity_qty = quantity_usd / current_price
                
                order = {
                    'symbol': symbol,
                    'side': side,
                    'quantity_usd': quantity_usd,
                    'quantity_qty': quantity_qty,
                    'price': current_price,
                    'priority': target.priority_score,
                    'reason': f"Rebalance: {target.action_required}",
                    'target_allocation_pct': target.target_allocation_pct,
                    'current_allocation_pct': target.current_allocation_pct
                }
                
                orders.append(order)
            
            # Ordenar por prioridad
            orders.sort(key=lambda x: x['priority'], reverse=True)
            return orders
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error calculando órdenes de rebalance: {e}")
            return []
    
    async def gradual_rebalance(self, targets: Dict[str, AllocationTarget], steps: int = 3) -> None:
        """
        Ejecuta rebalance gradual para minimizar impacto
        """
        try:
            logger.info(f"[PortfolioOptimizer] Iniciando rebalance gradual en {steps} pasos")
            
            for step in range(steps):
                logger.info(f"[PortfolioOptimizer] Paso {step + 1}/{steps}")
                
                # Calcular órdenes para este paso
                step_orders = await self.calculate_rebalance_orders(targets)
                
                # Ejecutar órdenes (simulado)
                for order in step_orders:
                    logger.info(f"[PortfolioOptimizer] Orden: {order['side']} {order['quantity_usd']:.2f} USD de {order['symbol']}")
                    # Aquí se ejecutarían las órdenes reales
                
                # Esperar entre pasos
                if step < steps - 1:
                    await asyncio.sleep(5)  # 5 segundos entre pasos
            
            logger.info(f"[PortfolioOptimizer] Rebalance gradual completado")
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error en rebalance gradual: {e}")
    
    async def detect_concentration_risk(self) -> Dict[str, Any]:
        """
        Detecta riesgos de concentración
        """
        try:
            portfolio_state = await self.get_portfolio_state()
            if not portfolio_state:
                return {'risk_detected': False, 'risks': []}
            
            risks = []
            
            # Verificar concentración en un símbolo
            max_allocation = max(portfolio_state.symbol_allocations.values()) if portfolio_state.symbol_allocations else 0.0
            if max_allocation > self.PORTFOLIO_LIMITS['max_allocation_single']:
                risks.append({
                    'type': 'single_symbol_concentration',
                    'severity': 'high' if max_allocation > 0.6 else 'medium',
                    'description': f"Concentración en un símbolo: {max_allocation:.1%}",
                    'recommendation': "Reducir exposición al símbolo más concentrado"
                })
            
            # Verificar concentración en símbolos correlacionados
            high_correlation_pairs = []
            for symbol1 in self.symbols:
                for symbol2 in self.symbols:
                    if symbol1 != symbol2:
                        corr = abs(portfolio_state.correlation_matrix.get(symbol1, {}).get(symbol2, 0.0))
                        if corr > self.max_correlation:
                            high_correlation_pairs.append((symbol1, symbol2, corr))
            
            if len(high_correlation_pairs) > 0:
                risks.append({
                    'type': 'correlation_concentration',
                    'severity': 'high' if len(high_correlation_pairs) > 2 else 'medium',
                    'description': f"Concentración en símbolos correlacionados: {len(high_correlation_pairs)} pares",
                    'recommendation': "Diversificar hacia símbolos menos correlacionados"
                })
            
            # Verificar diversificación insuficiente
            if portfolio_state.diversification_ratio < self.PORTFOLIO_LIMITS['min_diversification_ratio']:
                risks.append({
                    'type': 'insufficient_diversification',
                    'severity': 'medium',
                    'description': f"Diversificación insuficiente: {portfolio_state.diversification_ratio:.1%}",
                    'recommendation': "Aumentar número de posiciones o reducir concentración"
                })
            
            return {
                'risk_detected': len(risks) > 0,
                'risks': risks,
                'diversification_ratio': portfolio_state.diversification_ratio,
                'max_allocation': max_allocation,
                'correlation_risk_score': portfolio_state.correlation_risk_score
            }
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error detectando riesgos de concentración: {e}")
            return {'risk_detected': False, 'risks': []}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verificar estado del portfolio optimizer
        """
        try:
            health_status = {
                'status': 'healthy',
                'components': {},
                'metrics': {},
                'warnings': [],
                'errors': []
            }
            
            # Verificar componentes básicos
            try:
                portfolio_state = await self.get_portfolio_state()
                health_status['components']['portfolio_state'] = 'ok' if portfolio_state else 'error'
            except Exception as e:
                health_status['components']['portfolio_state'] = 'error'
                health_status['errors'].append(f"Portfolio state: {e}")
            
            try:
                correlations = await self.calculate_symbol_correlations()
                health_status['components']['correlations'] = 'ok' if correlations else 'error'
            except Exception as e:
                health_status['components']['correlations'] = 'error'
                health_status['errors'].append(f"Correlations: {e}")
            
            # Verificar métricas
            health_status['metrics'] = {
                'optimization_runs': self.optimization_metrics['optimization_runs'],
                'avg_latency_ms': self.optimization_metrics['optimization_latency_ms'],
                'constraint_violations': self.optimization_metrics['constraint_violations']
            }
            
            # Determinar estado general
            if health_status['errors']:
                health_status['status'] = 'error'
            elif health_status['warnings']:
                health_status['status'] = 'warning'
            
            return health_status
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error en health check: {e}")
            return {
                'status': 'error',
                'components': {},
                'metrics': {},
                'warnings': [],
                'errors': [str(e)]
            }
    
    async def test_portfolio_optimization(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Test completo de optimización
        """
        try:
            test_results = {
                'success': True,
                'test_duration_ms': 0.0,
                'optimization_results': {},
                'correlation_analysis': {},
                'diversification_metrics': {},
                'errors': []
            }
            
            start_time = datetime.now()
            
            # Test de optimización
            try:
                targets = await self.optimize_portfolio()
                test_results['optimization_results'] = {
                    'targets_generated': len(targets),
                    'targets': {k: {
                        'target_pct': v.target_allocation_pct,
                        'current_pct': v.current_allocation_pct,
                        'action': v.action_required,
                        'priority': v.priority_score
                    } for k, v in targets.items()}
                }
            except Exception as e:
                test_results['errors'].append(f"Optimization test failed: {e}")
                test_results['success'] = False
            
            # Test de correlaciones
            try:
                correlations = await self.calculate_symbol_correlations()
                test_results['correlation_analysis'] = {
                    'matrix_generated': len(correlations) > 0,
                    'max_correlation': max(
                        max(abs(corr) for corr in row.values() if corr != 1.0)
                        for row in correlations.values()
                    ) if correlations else 0.0
                }
            except Exception as e:
                test_results['errors'].append(f"Correlation test failed: {e}")
                test_results['success'] = False
            
            # Test de diversificación
            try:
                test_allocations = {symbol: 0.25 for symbol in symbols}  # Equal weight
                diversification = self.calculate_diversification_metrics(test_allocations)
                test_results['diversification_metrics'] = diversification
            except Exception as e:
                test_results['errors'].append(f"Diversification test failed: {e}")
                test_results['success'] = False
            
            # Calcular duración del test
            test_duration = (datetime.now() - start_time).total_seconds() * 1000
            test_results['test_duration_ms'] = test_duration
            
            return test_results
            
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error en test de optimización: {e}")
            return {
                'success': False,
                'test_duration_ms': 0.0,
                'optimization_results': {},
                'correlation_analysis': {},
                'diversification_metrics': {},
                'errors': [str(e)]
            }
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Resumen de optimización y performance
        """
        try:
            return {
                'optimization_metrics': self.optimization_metrics,
                'portfolio_limits': self.PORTFOLIO_LIMITS,
                'circuit_breakers': self.CIRCUIT_BREAKERS,
                'symbols_tracked': self.symbols,
                'rebalance_threshold': self.rebalance_threshold,
                'max_correlation': self.max_correlation,
                'last_optimization': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[PortfolioOptimizer] Error obteniendo resumen: {e}")
            return {}

# Instancia global del optimizador
portfolio_optimizer = PortfolioOptimizer()
