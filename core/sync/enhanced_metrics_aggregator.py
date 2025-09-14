#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/sync/enhanced_metrics_aggregator.py
========================================
Agregador Mejorado de Métricas con Análisis de Portfolio Completo

Proporciona análisis avanzado de métricas conjuntas, correlación entre agentes,
diversificación, riesgo de portfolio y métricas operacionales detalladas.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from ..metrics.trade_metrics import DetailedTradeMetric

logger = logging.getLogger(__name__)

@dataclass
class PortfolioMetrics:
    """Métricas completas del portfolio"""
    cycle_id: int
    timestamp: datetime
    
    # Métricas financieras
    total_pnl_usdt: float
    portfolio_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    
    # Métricas de riesgo
    correlation_avg: float
    diversification_score: float
    var_95: float
    concentration_risk: float
    
    # Métricas operacionales
    total_trades: int
    avg_trade_duration: float
    best_performing_agent: str
    worst_performing_agent: str
    strategy_effectiveness: Dict[str, float]
    
    # Métricas de calidad
    avg_quality_score: float
    high_quality_trades_pct: float
    avg_confluence_score: float
    
    # Métricas de correlación detallada
    correlation_matrix: Dict[str, Dict[str, float]]
    agent_contributions: Dict[str, float]
    
    # Métricas de timing
    avg_cycle_duration: float
    trades_per_hour: float
    efficiency_score: float

class EnhancedMetricsAggregator:
    """Agregador mejorado de métricas con análisis de portfolio completo"""
    
    def __init__(self, initial_capital: float = 1000.0):
        """
        Inicializa el agregador de métricas
        
        Args:
            initial_capital: Capital inicial del portfolio
        """
        self.initial_capital = initial_capital
        self.logger = logging.getLogger(__name__)
        
        # Historial de métricas para análisis temporal
        self.metrics_history: List[PortfolioMetrics] = []
        
        # Cache para cálculos costosos
        self._correlation_cache: Dict[str, float] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update = datetime.min
        
        self.logger.info(f"✅ EnhancedMetricsAggregator inicializado con capital inicial: ${initial_capital:,.2f}")
    
    async def calculate_portfolio_metrics(
        self, 
        agent_results: Dict[str, List[DetailedTradeMetric]], 
        current_cycle: int
    ) -> PortfolioMetrics:
        """
        Calcula métricas del portfolio completo
        
        Args:
            agent_results: Resultados de trades por agente
            current_cycle: ID del ciclo actual
            
        Returns:
            PortfolioMetrics: Métricas completas del portfolio
        """
        try:
            start_time = datetime.now()
            
            # 1. Extraer todos los trades del ciclo
            all_trades = []
            for symbol, trades in agent_results.items():
                all_trades.extend(trades)
            
            if not all_trades:
                return self._create_empty_metrics(current_cycle)
            
            # 2. Calcular métricas financieras globales
            financial_metrics = await self._calculate_financial_metrics(all_trades)
            
            # 3. Análisis de correlación entre agentes
            correlation_metrics = await self._calculate_correlation_metrics(agent_results)
            
            # 4. Diversification score
            diversification = await self._calculate_diversification_score(agent_results)
            
            # 5. Portfolio Sharpe ratio
            portfolio_sharpe = await self._calculate_portfolio_sharpe(all_trades)
            
            # 6. Drawdown conjunto
            portfolio_drawdown = await self._calculate_portfolio_drawdown(all_trades)
            
            # 7. Métricas operacionales
            operational_metrics = await self._calculate_operational_metrics(agent_results)
            
            # 8. Métricas de calidad
            quality_metrics = await self._calculate_quality_metrics(all_trades)
            
            # 9. Métricas de timing
            timing_metrics = await self._calculate_timing_metrics(all_trades, current_cycle)
            
            # 10. Crear objeto de métricas completo
            portfolio_metrics = PortfolioMetrics(
                cycle_id=current_cycle,
                timestamp=datetime.now(),
                
                # Financieras
                total_pnl_usdt=financial_metrics['total_pnl_usdt'],
                portfolio_return_pct=financial_metrics['portfolio_return_pct'],
                sharpe_ratio=portfolio_sharpe,
                max_drawdown_pct=portfolio_drawdown,
                win_rate=financial_metrics['win_rate'],
                
                # Riesgo
                correlation_avg=correlation_metrics['correlation_avg'],
                diversification_score=diversification,
                var_95=correlation_metrics['var_95'],
                concentration_risk=correlation_metrics['concentration_risk'],
                
                # Operacionales
                total_trades=operational_metrics['total_trades'],
                avg_trade_duration=operational_metrics['avg_trade_duration'],
                best_performing_agent=operational_metrics['best_performing_agent'],
                worst_performing_agent=operational_metrics['worst_performing_agent'],
                strategy_effectiveness=operational_metrics['strategy_effectiveness'],
                
                # Calidad
                avg_quality_score=quality_metrics['avg_quality_score'],
                high_quality_trades_pct=quality_metrics['high_quality_trades_pct'],
                avg_confluence_score=quality_metrics['avg_confluence_score'],
                
                # Correlación detallada
                correlation_matrix=correlation_metrics['correlation_matrix'],
                agent_contributions=correlation_metrics['agent_contributions'],
                
                # Timing
                avg_cycle_duration=timing_metrics['avg_cycle_duration'],
                trades_per_hour=timing_metrics['trades_per_hour'],
                efficiency_score=timing_metrics['efficiency_score']
            )
            
            # Guardar en historial
            self.metrics_history.append(portfolio_metrics)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Métricas de portfolio calculadas en {processing_time:.2f}s para ciclo {current_cycle}")
            
            return portfolio_metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de portfolio: {e}")
            return self._create_empty_metrics(current_cycle)
    
    async def _calculate_financial_metrics(self, all_trades: List[DetailedTradeMetric]) -> Dict[str, Any]:
        """Calcula métricas financieras globales"""
        try:
            if not all_trades:
                return {
                    'total_pnl_usdt': 0.0,
                    'portfolio_return_pct': 0.0,
                    'win_rate': 0.0
                }
            
            # PnL total
            total_pnl = sum(trade.pnl_usdt for trade in all_trades)
            portfolio_return_pct = (total_pnl / self.initial_capital) * 100
            
            # Win rate
            successful_trades = sum(1 for trade in all_trades if trade.was_successful)
            win_rate = successful_trades / len(all_trades) if all_trades else 0.0
            
            return {
                'total_pnl_usdt': total_pnl,
                'portfolio_return_pct': portfolio_return_pct,
                'win_rate': win_rate
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas financieras: {e}")
            return {'total_pnl_usdt': 0.0, 'portfolio_return_pct': 0.0, 'win_rate': 0.0}
    
    async def _calculate_correlation_metrics(self, agent_results: Dict[str, List[DetailedTradeMetric]]) -> Dict[str, Any]:
        """Calcula métricas de correlación entre agentes"""
        try:
            if len(agent_results) < 2:
                return {
                    'correlation_avg': 0.0,
                    'var_95': 0.0,
                    'concentration_risk': 0.0,
                    'correlation_matrix': {},
                    'agent_contributions': {}
                }
            
            # Crear DataFrame de PnL por agente
            agent_pnl_data = {}
            for symbol, trades in agent_results.items():
                if trades:
                    # Agrupar por timestamp para calcular PnL por período
                    pnl_by_time = {}
                    for trade in trades:
                        time_key = trade.timestamp.replace(second=0, microsecond=0)
                        if time_key not in pnl_by_time:
                            pnl_by_time[time_key] = 0.0
                        pnl_by_time[time_key] += trade.pnl_usdt
                    
                    agent_pnl_data[symbol] = pnl_by_time
            
            # Crear DataFrame de correlación
            if agent_pnl_data:
                df = pd.DataFrame(agent_pnl_data).fillna(0.0)
                correlation_matrix = df.corr().to_dict()
                
                # Calcular correlación promedio (excluyendo diagonal)
                correlations = []
                for i, symbol1 in enumerate(df.columns):
                    for j, symbol2 in enumerate(df.columns):
                        if i != j:
                            correlations.append(correlation_matrix[symbol1][symbol2])
                
                correlation_avg = np.mean(correlations) if correlations else 0.0
                
                # Calcular VaR 95%
                portfolio_returns = df.sum(axis=1)
                var_95 = np.percentile(portfolio_returns, 5) if len(portfolio_returns) > 0 else 0.0
                
                # Calcular concentración de riesgo
                agent_contributions = {}
                total_pnl = df.sum().sum()
                for symbol in df.columns:
                    agent_pnl = df[symbol].sum()
                    agent_contributions[symbol] = (agent_pnl / total_pnl) * 100 if total_pnl != 0 else 0.0
                
                # Concentración = suma de cuadrados de contribuciones
                concentration_risk = sum(contrib**2 for contrib in agent_contributions.values()) / 100
                
                return {
                    'correlation_avg': correlation_avg,
                    'var_95': abs(var_95),
                    'concentration_risk': concentration_risk,
                    'correlation_matrix': correlation_matrix,
                    'agent_contributions': agent_contributions
                }
            
            return {
                'correlation_avg': 0.0,
                'var_95': 0.0,
                'concentration_risk': 0.0,
                'correlation_matrix': {},
                'agent_contributions': {}
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de correlación: {e}")
            return {
                'correlation_avg': 0.0,
                'var_95': 0.0,
                'concentration_risk': 0.0,
                'correlation_matrix': {},
                'agent_contributions': {}
            }
    
    async def _calculate_diversification_score(self, agent_results: Dict[str, List[DetailedTradeMetric]]) -> float:
        """Calcula score de diversificación del portfolio"""
        try:
            if len(agent_results) < 2:
                return 0.0
            
            # Calcular PnL por agente
            agent_pnl = {}
            for symbol, trades in agent_results.items():
                agent_pnl[symbol] = sum(trade.pnl_usdt for trade in trades)
            
            # Calcular índice de Herfindahl (inverso = diversificación)
            total_pnl = sum(agent_pnl.values())
            if total_pnl == 0:
                return 0.0
            
            # Proporciones de PnL
            proportions = [pnl / total_pnl for pnl in agent_pnl.values()]
            
            # Índice de Herfindahl
            herfindahl = sum(p**2 for p in proportions)
            
            # Diversificación = 1 - Herfindahl (normalizado)
            diversification = 1 - herfindahl
            
            return min(1.0, max(0.0, diversification))
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando diversificación: {e}")
            return 0.0
    
    async def _calculate_portfolio_sharpe(self, all_trades: List[DetailedTradeMetric]) -> float:
        """Calcula Sharpe ratio del portfolio"""
        try:
            if len(all_trades) < 2:
                return 0.0
            
            # Obtener returns por trade
            returns = [trade.pnl_percentage / 100 for trade in all_trades]
            
            if len(returns) < 2:
                return 0.0
            
            # Calcular Sharpe ratio
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            # Asumir risk-free rate de 0% para simplificar
            sharpe_ratio = mean_return / std_return
            
            return sharpe_ratio
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando Sharpe ratio: {e}")
            return 0.0
    
    async def _calculate_portfolio_drawdown(self, all_trades: List[DetailedTradeMetric]) -> float:
        """Calcula drawdown máximo del portfolio"""
        try:
            if not all_trades:
                return 0.0
            
            # Ordenar trades por timestamp
            sorted_trades = sorted(all_trades, key=lambda x: x.timestamp)
            
            # Calcular balance acumulado
            balance = self.initial_capital
            peak_balance = balance
            max_drawdown = 0.0
            
            for trade in sorted_trades:
                balance += trade.pnl_usdt
                
                if balance > peak_balance:
                    peak_balance = balance
                
                drawdown = (peak_balance - balance) / peak_balance * 100
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando drawdown: {e}")
            return 0.0
    
    async def _calculate_operational_metrics(self, agent_results: Dict[str, List[DetailedTradeMetric]]) -> Dict[str, Any]:
        """Calcula métricas operacionales"""
        try:
            all_trades = []
            for trades in agent_results.values():
                all_trades.extend(trades)
            
            if not all_trades:
                return {
                    'total_trades': 0,
                    'avg_trade_duration': 0.0,
                    'best_performing_agent': 'N/A',
                    'worst_performing_agent': 'N/A',
                    'strategy_effectiveness': {}
                }
            
            # Total trades
            total_trades = len(all_trades)
            
            # Duración promedio
            avg_duration = np.mean([trade.duration_hours for trade in all_trades])
            
            # Mejor y peor agente por PnL
            agent_pnl = {}
            for symbol, trades in agent_results.items():
                agent_pnl[symbol] = sum(trade.pnl_usdt for trade in trades)
            
            best_agent = max(agent_pnl.items(), key=lambda x: x[1])[0] if agent_pnl else 'N/A'
            worst_agent = min(agent_pnl.items(), key=lambda x: x[1])[0] if agent_pnl else 'N/A'
            
            # Efectividad de estrategias
            strategy_pnl = {}
            for trade in all_trades:
                strategy = trade.strategy_name
                if strategy not in strategy_pnl:
                    strategy_pnl[strategy] = []
                strategy_pnl[strategy].append(trade.pnl_usdt)
            
            strategy_effectiveness = {}
            for strategy, pnls in strategy_pnl.items():
                if pnls:
                    strategy_effectiveness[strategy] = {
                        'avg_pnl': np.mean(pnls),
                        'win_rate': sum(1 for pnl in pnls if pnl > 0) / len(pnls),
                        'total_trades': len(pnls)
                    }
            
            return {
                'total_trades': total_trades,
                'avg_trade_duration': avg_duration,
                'best_performing_agent': best_agent,
                'worst_performing_agent': worst_agent,
                'strategy_effectiveness': strategy_effectiveness
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas operacionales: {e}")
            return {
                'total_trades': 0,
                'avg_trade_duration': 0.0,
                'best_performing_agent': 'N/A',
                'worst_performing_agent': 'N/A',
                'strategy_effectiveness': {}
            }
    
    async def _calculate_quality_metrics(self, all_trades: List[DetailedTradeMetric]) -> Dict[str, Any]:
        """Calcula métricas de calidad de trades"""
        try:
            if not all_trades:
                return {
                    'avg_quality_score': 0.0,
                    'high_quality_trades_pct': 0.0,
                    'avg_confluence_score': 0.0
                }
            
            # Calcular quality scores
            quality_scores = [trade.get_quality_score() for trade in all_trades]
            avg_quality_score = np.mean(quality_scores)
            
            # Porcentaje de trades de alta calidad
            high_quality_trades = sum(1 for trade in all_trades if trade.is_high_quality_trade())
            high_quality_pct = (high_quality_trades / len(all_trades)) * 100
            
            # Score de confluence promedio
            confluence_scores = [trade.confluence_score for trade in all_trades]
            avg_confluence = np.mean(confluence_scores)
            
            return {
                'avg_quality_score': avg_quality_score,
                'high_quality_trades_pct': high_quality_pct,
                'avg_confluence_score': avg_confluence
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de calidad: {e}")
            return {
                'avg_quality_score': 0.0,
                'high_quality_trades_pct': 0.0,
                'avg_confluence_score': 0.0
            }
    
    async def _calculate_timing_metrics(self, all_trades: List[DetailedTradeMetric], cycle_id: int) -> Dict[str, Any]:
        """Calcula métricas de timing y eficiencia"""
        try:
            if not all_trades:
                return {
                    'avg_cycle_duration': 0.0,
                    'trades_per_hour': 0.0,
                    'efficiency_score': 0.0
                }
            
            # Duración promedio de trades
            avg_trade_duration = np.mean([trade.duration_hours for trade in all_trades])
            
            # Trades por hora (asumiendo ciclo de 1 hora)
            trades_per_hour = len(all_trades)  # Para simplificar, asumimos ciclo de 1h
            
            # Score de eficiencia basado en duración vs PnL
            if all_trades:
                total_pnl = sum(trade.pnl_usdt for trade in all_trades)
                total_duration = sum(trade.duration_hours for trade in all_trades)
                
                if total_duration > 0:
                    efficiency_score = (total_pnl / total_duration) * 100  # PnL por hora
                else:
                    efficiency_score = 0.0
            else:
                efficiency_score = 0.0
            
            return {
                'avg_cycle_duration': avg_trade_duration,
                'trades_per_hour': trades_per_hour,
                'efficiency_score': efficiency_score
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de timing: {e}")
            return {
                'avg_cycle_duration': 0.0,
                'trades_per_hour': 0.0,
                'efficiency_score': 0.0
            }
    
    def _create_empty_metrics(self, cycle_id: int) -> PortfolioMetrics:
        """Crea métricas vacías para ciclos sin trades"""
        return PortfolioMetrics(
            cycle_id=cycle_id,
            timestamp=datetime.now(),
            total_pnl_usdt=0.0,
            portfolio_return_pct=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            correlation_avg=0.0,
            diversification_score=0.0,
            var_95=0.0,
            concentration_risk=0.0,
            total_trades=0,
            avg_trade_duration=0.0,
            best_performing_agent='N/A',
            worst_performing_agent='N/A',
            strategy_effectiveness={},
            avg_quality_score=0.0,
            high_quality_trades_pct=0.0,
            avg_confluence_score=0.0,
            correlation_matrix={},
            agent_contributions={},
            avg_cycle_duration=0.0,
            trades_per_hour=0.0,
            efficiency_score=0.0
        )
    
    def get_agent_summary(self, agent_results: Dict[str, List[DetailedTradeMetric]]) -> Dict[str, Dict[str, Any]]:
        """Obtiene resumen por agente"""
        summaries = {}
        
        for symbol, trades in agent_results.items():
            if not trades:
                summaries[symbol] = {
                    'pnl': 0.0,
                    'pnl_pct': 0.0,
                    'trades': 0,
                    'win_rate': 0.0,
                    'drawdown': 0.0,
                    'avg_quality': 0.0
                }
                continue
            
            # Calcular métricas del agente
            total_pnl = sum(trade.pnl_usdt for trade in trades)
            pnl_pct = (total_pnl / self.initial_capital) * 100
            total_trades = len(trades)
            win_rate = sum(1 for trade in trades if trade.was_successful) / total_trades * 100
            
            # Drawdown del agente
            balance = self.initial_capital
            peak_balance = balance
            max_drawdown = 0.0
            
            for trade in sorted(trades, key=lambda x: x.timestamp):
                balance += trade.pnl_usdt
                if balance > peak_balance:
                    peak_balance = balance
                drawdown = (peak_balance - balance) / peak_balance * 100
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calidad promedio
            avg_quality = np.mean([trade.get_quality_score() for trade in trades])
            
            summaries[symbol] = {
                'pnl': total_pnl,
                'pnl_pct': pnl_pct,
                'trades': total_trades,
                'win_rate': win_rate,
                'drawdown': max_drawdown,
                'avg_quality': avg_quality
            }
        
        return summaries
    
    def get_historical_performance(self, days_back: int = 30) -> Dict[str, Any]:
        """Obtiene performance histórica del portfolio"""
        try:
            if not self.metrics_history:
                return {'error': 'No hay datos históricos disponibles'}
            
            # Filtrar últimos N días
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_date]
            
            if not recent_metrics:
                return {'error': f'No hay datos para los últimos {days_back} días'}
            
            # Calcular métricas históricas
            total_pnl = sum(m.total_pnl_usdt for m in recent_metrics)
            avg_return = np.mean([m.portfolio_return_pct for m in recent_metrics])
            avg_sharpe = np.mean([m.sharpe_ratio for m in recent_metrics])
            max_dd = max([m.max_drawdown_pct for m in recent_metrics])
            avg_win_rate = np.mean([m.win_rate for m in recent_metrics])
            
            return {
                'period_days': days_back,
                'cycles_analyzed': len(recent_metrics),
                'total_pnl_usdt': total_pnl,
                'avg_return_pct': avg_return,
                'avg_sharpe_ratio': avg_sharpe,
                'max_drawdown_pct': max_dd,
                'avg_win_rate': avg_win_rate,
                'best_cycle': max(recent_metrics, key=lambda x: x.total_pnl_usdt).cycle_id,
                'worst_cycle': min(recent_metrics, key=lambda x: x.total_pnl_usdt).cycle_id
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando performance histórica: {e}")
            return {'error': str(e)}
    
    def save_metrics_to_file(self, filepath: str) -> bool:
        """Guarda métricas en archivo JSON"""
        try:
            data = {
                'initial_capital': self.initial_capital,
                'metrics_history': [
                    {
                        'cycle_id': m.cycle_id,
                        'timestamp': m.timestamp.isoformat(),
                        'total_pnl_usdt': m.total_pnl_usdt,
                        'portfolio_return_pct': m.portfolio_return_pct,
                        'sharpe_ratio': m.sharpe_ratio,
                        'max_drawdown_pct': m.max_drawdown_pct,
                        'win_rate': m.win_rate,
                        'correlation_avg': m.correlation_avg,
                        'diversification_score': m.diversification_score,
                        'total_trades': m.total_trades,
                        'avg_quality_score': m.avg_quality_score
                    }
                    for m in self.metrics_history
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Métricas guardadas en {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando métricas: {e}")
            return False
