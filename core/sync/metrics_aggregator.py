# Ruta: core/sync/metrics_aggregator.py
"""
Agregador de Métricas Enterprise - Sistema de Trading
Agrega y analiza métricas de ejecución paralela
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
import json
from collections import defaultdict, Counter
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class DailyMetrics:
    """Métricas diarias agregadas"""
    date: str
    total_cycles: int
    successful_cycles: int
    total_pnl: float
    total_trades: int
    win_rate: float
    avg_pnl_per_cycle: float
    best_strategy: str
    worst_strategy: str
    best_symbol: str
    worst_symbol: str
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float

@dataclass
class StrategyPerformance:
    """Rendimiento de estrategia"""
    strategy_name: str
    total_pnl: float
    total_trades: int
    win_rate: float
    avg_pnl_per_trade: float
    max_win: float
    max_loss: float
    profit_factor: float
    sharpe_ratio: float
    usage_count: int
    success_rate: float

@dataclass
class SymbolPerformance:
    """Rendimiento por símbolo"""
    symbol: str
    total_pnl: float
    total_trades: int
    win_rate: float
    avg_pnl_per_trade: float
    best_timeframe: str
    worst_timeframe: str
    volatility: float
    success_rate: float

class MetricsAggregator:
    """Agregador enterprise de métricas de trading"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.metrics_cache = {}
        self.performance_history = []
        
    async def aggregate_cycle_metrics(self, cycle_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Agrega métricas de ciclos de ejecución
        
        Args:
            cycle_results: Lista de resultados de ciclos
            
        Returns:
            Dict con métricas agregadas
        """
        try:
            logger.info(f"📊 Agregando métricas de {len(cycle_results)} ciclos")
            
            if not cycle_results:
                return self._empty_metrics()
            
            # Convertir a DataFrame para análisis
            df = pd.DataFrame(cycle_results)
            
            # Métricas básicas
            basic_metrics = self._calculate_basic_metrics(df)
            
            # Métricas por estrategia
            strategy_metrics = self._calculate_strategy_metrics(df)
            
            # Métricas por símbolo
            symbol_metrics = self._calculate_symbol_metrics(df)
            
            # Métricas por timeframe
            timeframe_metrics = self._calculate_timeframe_metrics(df)
            
            # Métricas de riesgo
            risk_metrics = self._calculate_risk_metrics(df)
            
            # Rankings y recomendaciones
            rankings = self._generate_rankings(strategy_metrics, symbol_metrics)
            recommendations = self._generate_recommendations(basic_metrics, strategy_metrics, risk_metrics)
            
            aggregated_metrics = {
                'timestamp': datetime.now().isoformat(),
                'basic_metrics': basic_metrics,
                'strategy_metrics': strategy_metrics,
                'symbol_metrics': symbol_metrics,
                'timeframe_metrics': timeframe_metrics,
                'risk_metrics': risk_metrics,
                'rankings': rankings,
                'recommendations': recommendations,
                'summary': self._generate_summary(basic_metrics, strategy_metrics, symbol_metrics)
            }
            
            # Guardar en cache
            self.metrics_cache[datetime.now().strftime('%Y%m%d')] = aggregated_metrics
            
            logger.info(f"✅ Métricas agregadas exitosamente")
            return aggregated_metrics
            
        except Exception as e:
            logger.error(f"❌ Error agregando métricas: {e}")
            return self._empty_metrics()
    
    def _calculate_basic_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula métricas básicas"""
        try:
            successful_df = df[df['status'] == 'success']
            
            if successful_df.empty:
                return {
                    'total_cycles': len(df),
                    'successful_cycles': 0,
                    'success_rate': 0,
                    'total_pnl': 0,
                    'total_trades': 0,
                    'win_rate': 0,
                    'avg_pnl_per_cycle': 0,
                    'avg_execution_time': 0
                }
            
            total_cycles = len(df)
            successful_cycles = len(successful_df)
            success_rate = (successful_cycles / total_cycles * 100) if total_cycles > 0 else 0
            
            total_pnl = successful_df['pnl'].sum()
            total_trades = successful_df['trades_count'].sum()
            
            # Win rate basado en ciclos con PnL positivo
            winning_cycles = len(successful_df[successful_df['pnl'] > 0])
            win_rate = (winning_cycles / successful_cycles * 100) if successful_cycles > 0 else 0
            
            avg_pnl_per_cycle = total_pnl / successful_cycles if successful_cycles > 0 else 0
            avg_execution_time = successful_df['execution_time'].mean()
            
            return {
                'total_cycles': total_cycles,
                'successful_cycles': successful_cycles,
                'success_rate': success_rate,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_pnl_per_cycle': avg_pnl_per_cycle,
                'avg_execution_time': avg_execution_time
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas básicas: {e}")
            return {}
    
    def _calculate_strategy_metrics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calcula métricas por estrategia"""
        try:
            successful_df = df[df['status'] == 'success']
            
            if successful_df.empty:
                return []
            
            strategy_metrics = []
            
            for strategy in successful_df['strategy_used'].unique():
                strategy_df = successful_df[successful_df['strategy_used'] == strategy]
                
                total_pnl = strategy_df['pnl'].sum()
                total_trades = strategy_df['trades_count'].sum()
                win_rate = (len(strategy_df[strategy_df['pnl'] > 0]) / len(strategy_df) * 100) if len(strategy_df) > 0 else 0
                avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
                
                max_win = strategy_df['pnl'].max()
                max_loss = strategy_df['pnl'].min()
                
                # Profit factor
                wins = strategy_df[strategy_df['pnl'] > 0]['pnl'].sum()
                losses = abs(strategy_df[strategy_df['pnl'] < 0]['pnl'].sum())
                profit_factor = wins / losses if losses > 0 else float('inf') if wins > 0 else 0
                
                # Sharpe ratio (simplificado)
                returns = strategy_df['pnl'].values
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
                
                strategy_metrics.append({
                    'strategy_name': strategy,
                    'total_pnl': total_pnl,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'avg_pnl_per_trade': avg_pnl_per_trade,
                    'max_win': max_win,
                    'max_loss': max_loss,
                    'profit_factor': profit_factor,
                    'sharpe_ratio': sharpe_ratio,
                    'usage_count': len(strategy_df),
                    'success_rate': 100  # Todos los registros son exitosos
                })
            
            return sorted(strategy_metrics, key=lambda x: x['total_pnl'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculando métricas de estrategia: {e}")
            return []
    
    def _calculate_symbol_metrics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calcula métricas por símbolo"""
        try:
            successful_df = df[df['status'] == 'success']
            
            if successful_df.empty:
                return []
            
            symbol_metrics = []
            
            for symbol in successful_df['symbol'].unique():
                symbol_df = successful_df[successful_df['symbol'] == symbol]
                
                total_pnl = symbol_df['pnl'].sum()
                total_trades = symbol_df['trades_count'].sum()
                win_rate = (len(symbol_df[symbol_df['pnl'] > 0]) / len(symbol_df) * 100) if len(symbol_df) > 0 else 0
                avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
                
                # Mejor y peor timeframe
                timeframe_pnl = symbol_df.groupby('timeframe')['pnl'].sum()
                best_timeframe = timeframe_pnl.idxmax() if not timeframe_pnl.empty else 'N/A'
                worst_timeframe = timeframe_pnl.idxmin() if not timeframe_pnl.empty else 'N/A'
                
                # Volatilidad (desviación estándar de PnL)
                volatility = symbol_df['pnl'].std()
                
                symbol_metrics.append({
                    'symbol': symbol,
                    'total_pnl': total_pnl,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'avg_pnl_per_trade': avg_pnl_per_trade,
                    'best_timeframe': best_timeframe,
                    'worst_timeframe': worst_timeframe,
                    'volatility': volatility,
                    'success_rate': 100
                })
            
            return sorted(symbol_metrics, key=lambda x: x['total_pnl'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculando métricas de símbolo: {e}")
            return []
    
    def _calculate_timeframe_metrics(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calcula métricas por timeframe"""
        try:
            successful_df = df[df['status'] == 'success']
            
            if successful_df.empty:
                return []
            
            timeframe_metrics = []
            
            for timeframe in successful_df['timeframe'].unique():
                timeframe_df = successful_df[successful_df['timeframe'] == timeframe]
                
                total_pnl = timeframe_df['pnl'].sum()
                total_trades = timeframe_df['trades_count'].sum()
                win_rate = (len(timeframe_df[timeframe_df['pnl'] > 0]) / len(timeframe_df) * 100) if len(timeframe_df) > 0 else 0
                avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
                
                timeframe_metrics.append({
                    'timeframe': timeframe,
                    'total_pnl': total_pnl,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'avg_pnl_per_trade': avg_pnl_per_trade,
                    'usage_count': len(timeframe_df)
                })
            
            return sorted(timeframe_metrics, key=lambda x: x['total_pnl'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculando métricas de timeframe: {e}")
            return []
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula métricas de riesgo"""
        try:
            successful_df = df[df['status'] == 'success']
            
            if successful_df.empty:
                return {
                    'volatility': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'var_95': 0,
                    'cvar_95': 0
                }
            
            returns = successful_df['pnl'].values
            
            # Volatilidad
            volatility = np.std(returns)
            
            # Sharpe ratio
            mean_return = np.mean(returns)
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = np.min(drawdowns)
            
            # Value at Risk (95%)
            var_95 = np.percentile(returns, 5)
            
            # Conditional Value at Risk (95%)
            cvar_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else 0
            
            return {
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'var_95': var_95,
                'cvar_95': cvar_95
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
            return {}
    
    def _generate_rankings(self, strategy_metrics: List[Dict], symbol_metrics: List[Dict]) -> Dict[str, Any]:
        """Genera rankings de estrategias y símbolos"""
        try:
            # Ranking de estrategias
            strategy_rankings = {
                'by_pnl': sorted(strategy_metrics, key=lambda x: x['total_pnl'], reverse=True)[:5],
                'by_win_rate': sorted(strategy_metrics, key=lambda x: x['win_rate'], reverse=True)[:5],
                'by_profit_factor': sorted(strategy_metrics, key=lambda x: x['profit_factor'], reverse=True)[:5]
            }
            
            # Ranking de símbolos
            symbol_rankings = {
                'by_pnl': sorted(symbol_metrics, key=lambda x: x['total_pnl'], reverse=True)[:5],
                'by_win_rate': sorted(symbol_metrics, key=lambda x: x['win_rate'], reverse=True)[:5],
                'by_volatility': sorted(symbol_metrics, key=lambda x: x['volatility'], reverse=True)[:5]
            }
            
            return {
                'strategies': strategy_rankings,
                'symbols': symbol_rankings
            }
            
        except Exception as e:
            logger.error(f"Error generando rankings: {e}")
            return {'strategies': {}, 'symbols': {}}
    
    def _generate_recommendations(self, basic_metrics: Dict, strategy_metrics: List[Dict], 
                                risk_metrics: Dict) -> List[str]:
        """Genera recomendaciones basadas en métricas"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en éxito
            if basic_metrics.get('success_rate', 0) < 80:
                recommendations.append("🔧 Revisar configuración de agentes - tasa de éxito baja")
            
            # Recomendaciones basadas en PnL
            if basic_metrics.get('total_pnl', 0) < 0:
                recommendations.append("⚠️ Revisar estrategias - PnL total negativo")
            
            # Recomendaciones basadas en win rate
            if basic_metrics.get('win_rate', 0) < 50:
                recommendations.append("📊 Mejorar estrategias - win rate bajo")
            
            # Recomendaciones basadas en riesgo
            if risk_metrics.get('max_drawdown', 0) < -1000:
                recommendations.append("🛡️ Implementar gestión de riesgo más estricta")
            
            if risk_metrics.get('sharpe_ratio', 0) < 1.0:
                recommendations.append("📈 Mejorar ratio riesgo-recompensa")
            
            # Recomendaciones basadas en estrategias
            if strategy_metrics:
                best_strategy = max(strategy_metrics, key=lambda x: x['total_pnl'])
                worst_strategy = min(strategy_metrics, key=lambda x: x['total_pnl'])
                
                if best_strategy['total_pnl'] > 0:
                    recommendations.append(f"✅ Continuar usando estrategia {best_strategy['strategy_name']}")
                
                if worst_strategy['total_pnl'] < 0:
                    recommendations.append(f"❌ Revisar o desactivar estrategia {worst_strategy['strategy_name']}")
            
            if not recommendations:
                recommendations.append("✅ Rendimiento óptimo - mantener configuración actual")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return ["❌ Error generando recomendaciones"]
    
    def _generate_summary(self, basic_metrics: Dict, strategy_metrics: List[Dict], 
                         symbol_metrics: List[Dict]) -> Dict[str, Any]:
        """Genera resumen ejecutivo"""
        try:
            total_pnl = basic_metrics.get('total_pnl', 0)
            total_trades = basic_metrics.get('total_trades', 0)
            win_rate = basic_metrics.get('win_rate', 0)
            
            # Mejor estrategia
            best_strategy = max(strategy_metrics, key=lambda x: x['total_pnl']) if strategy_metrics else None
            
            # Mejor símbolo
            best_symbol = max(symbol_metrics, key=lambda x: x['total_pnl']) if symbol_metrics else None
            
            return {
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'best_strategy': best_strategy['strategy_name'] if best_strategy else 'N/A',
                'best_symbol': best_symbol['symbol'] if best_symbol else 'N/A',
                'performance_grade': self._calculate_performance_grade(total_pnl, win_rate),
                'key_insights': self._generate_key_insights(basic_metrics, strategy_metrics, symbol_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return {}
    
    def _calculate_performance_grade(self, total_pnl: float, win_rate: float) -> str:
        """Calcula calificación de rendimiento"""
        try:
            if total_pnl > 1000 and win_rate > 70:
                return 'A+'
            elif total_pnl > 500 and win_rate > 60:
                return 'A'
            elif total_pnl > 0 and win_rate > 50:
                return 'B'
            elif total_pnl > -500 and win_rate > 40:
                return 'C'
            else:
                return 'D'
        except:
            return 'F'
    
    def _generate_key_insights(self, basic_metrics: Dict, strategy_metrics: List[Dict], 
                             symbol_metrics: List[Dict]) -> List[str]:
        """Genera insights clave"""
        try:
            insights = []
            
            total_pnl = basic_metrics.get('total_pnl', 0)
            win_rate = basic_metrics.get('win_rate', 0)
            
            if total_pnl > 0:
                insights.append(f"💰 PnL positivo: ${total_pnl:.2f}")
            
            if win_rate > 60:
                insights.append(f"🎯 Win rate excelente: {win_rate:.1f}%")
            
            if strategy_metrics:
                best_strategy = max(strategy_metrics, key=lambda x: x['total_pnl'])
                insights.append(f"🏆 Mejor estrategia: {best_strategy['strategy_name']} (${best_strategy['total_pnl']:.2f})")
            
            if symbol_metrics:
                best_symbol = max(symbol_metrics, key=lambda x: x['total_pnl'])
                insights.append(f"📈 Mejor símbolo: {best_symbol['symbol']} (${best_symbol['total_pnl']:.2f})")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generando insights: {e}")
            return []
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Retorna métricas vacías"""
        return {
            'timestamp': datetime.now().isoformat(),
            'basic_metrics': {},
            'strategy_metrics': [],
            'symbol_metrics': [],
            'timeframe_metrics': [],
            'risk_metrics': {},
            'rankings': {'strategies': {}, 'symbols': {}},
            'recommendations': ['❌ No hay datos para analizar'],
            'summary': {}
        }
    
    async def calculate_daily_metrics(self, date: str) -> Optional[DailyMetrics]:
        """Calcula métricas diarias para una fecha específica"""
        try:
            # Implementar cálculo de métricas diarias
            # Esto sería usado para análisis histórico
            pass
        except Exception as e:
            logger.error(f"Error calculando métricas diarias: {e}")
            return None
    
    async def track_strategy_performance(self, strategy_name: str, pnl: float, trades_count: int):
        """Rastrea rendimiento de estrategia específica"""
        try:
            # Implementar tracking de estrategia
            pass
        except Exception as e:
            logger.error(f"Error trackeando estrategia: {e}")
    
    async def update_rankings(self) -> Dict[str, Any]:
        """Actualiza rankings de estrategias y símbolos"""
        try:
            # Implementar actualización de rankings
            pass
        except Exception as e:
            logger.error(f"Error actualizando rankings: {e}")
            return {}
