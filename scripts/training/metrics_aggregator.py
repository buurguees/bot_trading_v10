#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics Aggregator - Bot Trading v10 Enterprise
===============================================
Agregador de métricas para entrenamiento paralelo.
Consolida métricas de múltiples agentes y genera estadísticas globales.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SymbolStats:
    """Estadísticas de un símbolo específico"""
    symbol: str
    current_balance: float
    total_pnl: float
    total_pnl_pct: float
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float

class MetricsAggregator:
    """
    Agregador de Métricas
    =====================
    
    Consolida métricas de múltiples agentes y genera estadísticas globales.
    """
    
    def __init__(self, symbols: List[str]):
        """
        Inicializa el agregador
        
        Args:
            symbols: Lista de símbolos a agregar
        """
        self.symbols = symbols
        self.symbol_stats = {}
        self.global_metrics = {}
        
        logger.info(f"📊 MetricsAggregator inicializado para {len(symbols)} símbolos")
    
    async def aggregate_symbol_stats(self, agent_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, SymbolStats]:
        """
        Agrega estadísticas por símbolo
        
        Args:
            agent_summaries: Diccionario con métricas de cada agente
            
        Returns:
            Diccionario con estadísticas agregadas por símbolo
        """
        try:
            aggregated_stats = {}
            
            for symbol, summary in agent_summaries.items():
                if symbol not in self.symbols:
                    continue
                
                # Extraer métricas del resumen
                current_balance = summary.get('current_balance', 1000.0)
                total_pnl = summary.get('total_pnl', 0.0)
                total_pnl_pct = summary.get('total_pnl_pct', 0.0)
                total_trades = summary.get('total_trades', 0)
                win_rate = summary.get('win_rate', 0.0)
                max_drawdown = summary.get('max_drawdown', 0.0)
                
                # Calcular Sharpe ratio simplificado
                sharpe_ratio = self._calculate_sharpe_ratio(summary)
                
                # Crear estadísticas del símbolo
                stats = SymbolStats(
                    symbol=symbol,
                    current_balance=current_balance,
                    total_pnl=total_pnl,
                    total_pnl_pct=total_pnl_pct,
                    total_trades=total_trades,
                    win_rate=win_rate,
                    sharpe_ratio=sharpe_ratio,
                    max_drawdown=max_drawdown
                )
                
                aggregated_stats[symbol] = stats
                self.symbol_stats[symbol] = stats
            
            logger.info(f"✅ Estadísticas agregadas para {len(aggregated_stats)} símbolos")
            return aggregated_stats
            
        except Exception as e:
            logger.error(f"❌ Error agregando estadísticas: {e}")
            return {}
    
    def _calculate_sharpe_ratio(self, summary: Dict[str, Any]) -> float:
        """Calcula Sharpe ratio simplificado"""
        try:
            # Usar métricas disponibles para calcular Sharpe
            win_rate = summary.get('win_rate', 50.0) / 100.0
            max_drawdown = summary.get('max_drawdown', 10.0) / 100.0
            
            # Sharpe ratio simplificado basado en win rate y drawdown
            if max_drawdown > 0:
                sharpe = (win_rate - 0.5) / max_drawdown
            else:
                sharpe = (win_rate - 0.5) * 2
            
            return max(0, min(3, sharpe))  # Limitar entre 0 y 3
            
        except Exception:
            return 0.0
    
    async def calculate_global_metrics(self) -> Dict[str, Any]:
        """
        Calcula métricas globales del sistema
        
        Returns:
            Diccionario con métricas globales
        """
        try:
            if not self.symbol_stats:
                return {}
            
            # Agregar métricas de todos los símbolos
            total_balance = sum(stats.current_balance for stats in self.symbol_stats.values())
            total_pnl = sum(stats.total_pnl for stats in self.symbol_stats.values())
            total_trades = sum(stats.total_trades for stats in self.symbol_stats.values())
            total_win_rate = np.mean([stats.win_rate for stats in self.symbol_stats.values()])
            avg_sharpe = np.mean([stats.sharpe_ratio for stats in self.symbol_stats.values()])
            max_drawdown = max(stats.max_drawdown for stats in self.symbol_stats.values())
            
            # Calcular métricas derivadas
            avg_balance = total_balance / len(self.symbol_stats)
            avg_pnl = total_pnl / len(self.symbol_stats)
            avg_pnl_pct = (avg_pnl / 1000.0) * 100  # Asumiendo balance inicial de 1000
            
            # Encontrar mejores y peores performers
            best_symbol = max(self.symbol_stats.items(), key=lambda x: x[1].total_pnl_pct)
            worst_symbol = min(self.symbol_stats.items(), key=lambda x: x[1].total_pnl_pct)
            
            global_metrics = {
                'total_balance': total_balance,
                'avg_balance_per_symbol': avg_balance,
                'total_pnl': total_pnl,
                'avg_pnl_per_symbol': avg_pnl,
                'avg_pnl_pct': avg_pnl_pct,
                'total_trades': total_trades,
                'avg_win_rate': total_win_rate,
                'avg_sharpe_ratio': avg_sharpe,
                'max_drawdown': max_drawdown,
                'best_symbol': best_symbol[0],
                'best_pnl_pct': best_symbol[1].total_pnl_pct,
                'worst_symbol': worst_symbol[0],
                'worst_pnl_pct': worst_symbol[1].total_pnl_pct,
                'active_symbols': len(self.symbol_stats)
            }
            
            self.global_metrics = global_metrics
            logger.info("✅ Métricas globales calculadas")
            
            return global_metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculando métricas globales: {e}")
            return {}
    
    async def generate_performance_report(self) -> str:
        """
        Genera reporte de performance en formato texto
        
        Returns:
            Reporte formateado
        """
        try:
            if not self.global_metrics:
                await self.calculate_global_metrics()
            
            report = f"""
📊 <b>Reporte de Performance Global</b>

💰 <b>Métricas Financieras:</b>
• Balance Total: ${self.global_metrics.get('total_balance', 0):,.2f}
• PnL Total: ${self.global_metrics.get('total_pnl', 0):+,.2f} ({self.global_metrics.get('avg_pnl_pct', 0):+.2f}%)
• Balance Promedio por Símbolo: ${self.global_metrics.get('avg_balance_per_symbol', 0):,.2f}

📈 <b>Métricas de Trading:</b>
• Total de Trades: {self.global_metrics.get('total_trades', 0):,}
• Win Rate Promedio: {self.global_metrics.get('avg_win_rate', 0):.1f}%
• Sharpe Ratio Promedio: {self.global_metrics.get('avg_sharpe_ratio', 0):.2f}
• Max Drawdown: {self.global_metrics.get('max_drawdown', 0):.2f}%

🏆 <b>Top Performers:</b>
• Mejor: {self.global_metrics.get('best_symbol', 'N/A')} ({self.global_metrics.get('best_pnl_pct', 0):+.2f}%)
• Peor: {self.global_metrics.get('worst_symbol', 'N/A')} ({self.global_metrics.get('worst_pnl_pct', 0):+.2f}%)

📊 <b>Performance por Símbolo:</b>
"""
            
            # Agregar detalles por símbolo
            for symbol, stats in self.symbol_stats.items():
                report += f"• {symbol}: ${stats.current_balance:,.2f} ({stats.total_pnl_pct:+.2f}%), {stats.total_trades} trades, {stats.win_rate:.1f}% WR\n"
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "❌ Error generando reporte de performance"
    
    async def cleanup(self):
        """Limpia recursos del agregador"""
        try:
            self.symbol_stats.clear()
            self.global_metrics.clear()
            logger.info("✅ MetricsAggregator limpiado")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando agregador: {e}")

# Factory function para uso desde otros módulos
def create_metrics_aggregator(symbols: List[str]) -> MetricsAggregator:
    """
    Crea instancia del agregador de métricas
    
    Args:
        symbols: Lista de símbolos a agregar
        
    Returns:
        Instancia configurada del agregador
    """
    return MetricsAggregator(symbols)
