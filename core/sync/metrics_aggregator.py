#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics Aggregator - Bot Trading v10 Enterprise
===============================================
Agregador de métricas globales para entrenamiento paralelo.
Calcula PnL conjunto, winrate global, Sharpe ratio y métricas estadísticas.

Características:
- PnL diario agregado (media entre todos los agentes)
- Win rate global y por símbolo
- Trades por día consolidados
- Métricas de riesgo (Sharpe, Sortino, Calmar)
- Rankings de performance
- Estadísticas de estrategias
- Reportes en tiempo real

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

@dataclass
class DailyMetrics:
    """Métricas diarias agregadas"""
    date: str
    total_pnl: float
    avg_pnl_per_agent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    best_symbol: str
    best_symbol_pnl: float
    worst_symbol: str
    worst_symbol_pnl: float
    daily_return: float
    volatility: float
    sharpe_ratio: float

@dataclass
class SymbolStats:
    """Estadísticas por símbolo"""
    symbol: str
    total_pnl: float
    total_pnl_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_pnl: float
    best_trade: float
    worst_trade: float
    max_drawdown: float
    current_balance: float
    sharpe_ratio: float
    profit_factor: float
    avg_trade_duration: float

@dataclass
class StrategyPerformance:
    """Performance de estrategias"""
    strategy_name: str
    total_uses: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_return: float
    total_pnl: float
    best_trade: float
    worst_trade: float
    symbols_used: List[str]
    avg_confidence: float
    performance_score: float

class MetricsAggregator:
    """
    Agregador de Métricas Globales
    ==============================
    
    Consolida y agrega métricas de múltiples agentes de trading
    para proporcionar una vista global del performance del sistema.
    """
    
    def __init__(self, symbols: List[str]):
        """
        Inicializa el agregador de métricas
        
        Args:
            symbols: Lista de símbolos a agregar
        """
        self.symbols = symbols
        self.daily_metrics = []
        self.symbol_stats = {}
        self.strategy_performance = {}
        self.global_metrics_cache = {}
        
        # Configuración
        self.risk_free_rate = 0.02  # 2% anual
        self.trading_days_per_year = 365
        
        # Historial para cálculos estadísticos
        self.daily_returns = []
        self.rolling_window = 30  # días
        
        # Base de datos para persistencia
        self.db_path = Path("data/global_metrics.db")
        self._initialize_database()
        
        logger.info(f"📊 MetricsAggregator inicializado para {len(symbols)} símbolos")
    
    def _initialize_database(self):
        """Inicializa base de datos para métricas"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Tabla de métricas diarias
                conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    date TEXT PRIMARY KEY,
                    total_pnl REAL,
                    avg_pnl_per_agent REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    best_symbol TEXT,
                    best_symbol_pnl REAL,
                    worst_symbol TEXT,
                    worst_symbol_pnl REAL,
                    daily_return REAL,
                    volatility REAL,
                    sharpe_ratio REAL,
                    created_at TEXT
                )
                """)
                
                # Tabla de estadísticas por símbolo
                conn.execute("""
                CREATE TABLE IF NOT EXISTS symbol_stats (
                    symbol TEXT,
                    date TEXT,
                    pnl REAL,
                    pnl_pct REAL,
                    trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    balance REAL,
                    drawdown REAL,
                    created_at TEXT,
                    PRIMARY KEY (symbol, date)
                )
                """)
                
                # Tabla de performance de estrategias
                conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    strategy_name TEXT,
                    date TEXT,
                    uses INTEGER,
                    successes INTEGER,
                    failures INTEGER,
                    success_rate REAL,
                    avg_return REAL,
                    total_pnl REAL,
                    performance_score REAL,
                    created_at TEXT,
                    PRIMARY KEY (strategy_name, date)
                )
                """)
                
            logger.info("✅ Base de datos de métricas inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
    
    async def aggregate_daily_metrics(self, agent_metrics: Dict[str, Dict[str, Any]], 
                                    date: datetime) -> DailyMetrics:
        """
        Agrega métricas diarias de todos los agentes
        
        Args:
            agent_metrics: Métricas por agente {symbol: metrics}
            date: Fecha de las métricas
            
        Returns:
            Métricas diarias agregadas
        """
        try:
            date_str = date.strftime("%Y-%m-%d")
            
            # Agregar PnL y trades
            total_pnl = sum(metrics.get('daily_pnl', 0) for metrics in agent_metrics.values())
            avg_pnl_per_agent = total_pnl / len(agent_metrics) if agent_metrics else 0
            
            total_trades = sum(metrics.get('total_trades', 0) for metrics in agent_metrics.values())
            winning_trades = sum(metrics.get('winning_trades', 0) for metrics in agent_metrics.values())
            losing_trades = sum(metrics.get('losing_trades', 0) for metrics in agent_metrics.values())
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Encontrar mejores y peores performers
            symbol_pnls = {symbol: metrics.get('daily_pnl', 0) 
                          for symbol, metrics in agent_metrics.items()}
            
            best_symbol = max(symbol_pnls.keys(), key=lambda s: symbol_pnls[s]) if symbol_pnls else ""
            worst_symbol = min(symbol_pnls.keys(), key=lambda s: symbol_pnls[s]) if symbol_pnls else ""
            
            best_symbol_pnl = symbol_pnls.get(best_symbol, 0)
            worst_symbol_pnl = symbol_pnls.get(worst_symbol, 0)
            
            # Calcular return diario y volatilidad
            total_balance = sum(metrics.get('current_balance', 1000) for metrics in agent_metrics.values())
            daily_return = (total_pnl / total_balance) * 100 if total_balance > 0 else 0
            
            # Agregar a historial para volatilidad
            self.daily_returns.append(daily_return)
            if len(self.daily_returns) > self.rolling_window:
                self.daily_returns.pop(0)
            
            volatility = np.std(self.daily_returns) if len(self.daily_returns) > 1 else 0
            
            # Calcular Sharpe ratio
            if volatility > 0 and len(self.daily_returns) > 1:
                excess_returns = np.array(self.daily_returns) - (self.risk_free_rate / self.trading_days_per_year)
                sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(self.trading_days_per_year)
            else:
                sharpe_ratio = 0
            
            # Crear métricas diarias
            daily_metrics = DailyMetrics(
                date=date_str,
                total_pnl=total_pnl,
                avg_pnl_per_agent=avg_pnl_per_agent,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                best_symbol=best_symbol,
                best_symbol_pnl=best_symbol_pnl,
                worst_symbol=worst_symbol,
                worst_symbol_pnl=worst_symbol_pnl,
                daily_return=daily_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio
            )
            
            # Guardar en historial
            self.daily_metrics.append(daily_metrics)
            
            # Persistir en base de datos
            await self._save_daily_metrics(daily_metrics)
            
            logger.info(f"📊 Métricas diarias agregadas para {date_str}: PnL={total_pnl:+.2f}, WR={win_rate:.1f}%")
            
            return daily_metrics
            
        except Exception as e:
            logger.error(f"❌ Error agregando métricas diarias: {e}")
            return DailyMetrics(
                date=date.strftime("%Y-%m-%d"),
                total_pnl=0, avg_pnl_per_agent=0, total_trades=0,
                winning_trades=0, losing_trades=0, win_rate=0,
                best_symbol="", best_symbol_pnl=0,
                worst_symbol="", worst_symbol_pnl=0,
                daily_return=0, volatility=0, sharpe_ratio=0
            )
    
    async def aggregate_symbol_stats(self, agent_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, SymbolStats]:
        """
        Agrega estadísticas por símbolo
        
        Args:
            agent_metrics: Métricas por agente
            
        Returns:
            Estadísticas agregadas por símbolo
        """
        try:
            symbol_stats = {}
            
            for symbol, metrics in agent_metrics.items():
                # Calcular estadísticas del símbolo
                total_pnl = metrics.get('total_pnl', 0)
                total_pnl_pct = metrics.get('total_pnl_pct', 0)
                total_trades = metrics.get('total_trades', 0)
                winning_trades = metrics.get('winning_trades', 0)
                losing_trades = metrics.get('losing_trades', 0)
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
                
                # Calcular profit factor (ganancia bruta / pérdida bruta)
                profit_factor = await self._calculate_profit_factor(symbol)
                
                # Calcular Sharpe ratio del símbolo
                symbol_sharpe = await self._calculate_symbol_sharpe(symbol)
                
                # Obtener mejores y peores trades
                best_trade, worst_trade = await self._get_best_worst_trades(symbol)
                
                # Duración promedio de trades
                avg_trade_duration = await self._calculate_avg_trade_duration(symbol)
                
                stats = SymbolStats(
                    symbol=symbol,
                    total_pnl=total_pnl,
                    total_pnl_pct=total_pnl_pct,
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    win_rate=win_rate,
                    avg_trade_pnl=avg_trade_pnl,
                    best_trade=best_trade,
                    worst_trade=worst_trade,
                    max_drawdown=metrics.get('max_drawdown', 0),
                    current_balance=metrics.get('current_balance', 0),
                    sharpe_ratio=symbol_sharpe,
                    profit_factor=profit_factor,
                    avg_trade_duration=avg_trade_duration
                )
                
                symbol_stats[symbol] = stats
                
            self.symbol_stats = symbol_stats
            
            logger.info(f"📈 Estadísticas agregadas para {len(symbol_stats)} símbolos")
            
            return symbol_stats
            
        except Exception as e:
            logger.error(f"❌ Error agregando estadísticas por símbolo: {e}")
            return {}
    
    async def aggregate_strategy_performance(self, strategy_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, StrategyPerformance]:
        """
        Agrega performance de estrategias
        
        Args:
            strategy_data: Datos de estrategias por símbolo
            
        Returns:
            Performance agregada por estrategia
        """
        try:
            strategy_stats = defaultdict(lambda: {
                'uses': 0, 'successes': 0, 'failures': 0,
                'returns': [], 'confidences': [], 'symbols': set(),
                'pnl': 0, 'best_trade': 0, 'worst_trade': 0
            })
            
            # Agregar datos de todas las estrategias
            for symbol, strategies in strategy_data.items():
                for strategy_info in strategies:
                    strategy_name = strategy_info.get('name', 'Unknown')
                    success = strategy_info.get('success', False)
                    pnl = strategy_info.get('pnl', 0)
                    confidence = strategy_info.get('confidence', 0)
                    
                    stats = strategy_stats[strategy_name]
                    stats['uses'] += 1
                    stats['symbols'].add(symbol)
                    stats['pnl'] += pnl
                    stats['confidences'].append(confidence)
                    stats['returns'].append(pnl)
                    
                    if success:
                        stats['successes'] += 1
                    else:
                        stats['failures'] += 1
                    
                    # Actualizar mejores/peores trades
                    if pnl > stats['best_trade']:
                        stats['best_trade'] = pnl
                    if pnl < stats['worst_trade']:
                        stats['worst_trade'] = pnl
            
            # Convertir a objetos StrategyPerformance
            strategy_performance = {}
            
            for strategy_name, stats in strategy_stats.items():
                success_rate = (stats['successes'] / stats['uses'] * 100) if stats['uses'] > 0 else 0
                avg_return = statistics.mean(stats['returns']) if stats['returns'] else 0
                avg_confidence = statistics.mean(stats['confidences']) if stats['confidences'] else 0
                
                # Calcular performance score
                performance_score = self._calculate_strategy_score(
                    success_rate, avg_return, stats['uses'], avg_confidence
                )
                
                performance = StrategyPerformance(
                    strategy_name=strategy_name,
                    total_uses=stats['uses'],
                    success_count=stats['successes'],
                    failure_count=stats['failures'],
                    success_rate=success_rate,
                    avg_return=avg_return,
                    total_pnl=stats['pnl'],
                    best_trade=stats['best_trade'],
                    worst_trade=stats['worst_trade'],
                    symbols_used=list(stats['symbols']),
                    avg_confidence=avg_confidence,
                    performance_score=performance_score
                )
                
                strategy_performance[strategy_name] = performance
            
            self.strategy_performance = strategy_performance
            
            logger.info(f"🎯 Performance agregada para {len(strategy_performance)} estrategias")
            
            return strategy_performance
            
        except Exception as e:
            logger.error(f"❌ Error agregando performance de estrategias: {e}")
            return {}
    
    def _calculate_strategy_score(self, success_rate: float, avg_return: float, 
                                total_uses: int, avg_confidence: float) -> float:
        """Calcula score de performance de estrategia"""
        try:
            # Normalizar componentes
            success_component = success_rate / 100  # 0-1
            return_component = max(0, avg_return) / 10  # Normalizar retornos
            usage_component = min(total_uses / 100, 1)  # Más uso = mejor
            confidence_component = avg_confidence / 100  # 0-1
            
            # Pesos
            score = (success_component * 0.4 + 
                    return_component * 0.3 + 
                    usage_component * 0.2 + 
                    confidence_component * 0.1)
            
            return min(score, 1.0)  # Limitar a 1.0
            
        except Exception as e:
            logger.error(f"❌ Error calculando score de estrategia: {e}")
            return 0.0
    
    async def _calculate_profit_factor(self, symbol: str) -> float:
        """Calcula profit factor para un símbolo"""
        try:
            # Simplificado: asumir que tenemos acceso a trades individuales
            # En implementación real, leer de base de datos de trades
            gross_profit = 1000  # Placeholder
            gross_loss = 500     # Placeholder
            
            return gross_profit / gross_loss if gross_loss > 0 else 0
            
        except Exception as e:
            logger.error(f"❌ Error calculando profit factor para {symbol}: {e}")
            return 0.0
    
    async def _calculate_symbol_sharpe(self, symbol: str) -> float:
        """Calcula Sharpe ratio para un símbolo específico"""
        try:
            # Simplificado: usar datos globales
            # En implementación real, calcular específico por símbolo
            return self.daily_metrics[-1].sharpe_ratio if self.daily_metrics else 0
            
        except Exception as e:
            logger.error(f"❌ Error calculando Sharpe para {symbol}: {e}")
            return 0.0
    
    async def _get_best_worst_trades(self, symbol: str) -> Tuple[float, float]:
        """Obtiene mejores y peores trades de un símbolo"""
        try:
            # Placeholder: en implementación real leer de base de datos
            return 50.0, -25.0  # best_trade, worst_trade
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo trades de {symbol}: {e}")
            return 0.0, 0.0
    
    async def _calculate_avg_trade_duration(self, symbol: str) -> float:
        """Calcula duración promedio de trades"""
        try:
            # Placeholder: en implementación real calcular desde base de datos
            return 4.5  # horas promedio
            
        except Exception as e:
            logger.error(f"❌ Error calculando duración promedio para {symbol}: {e}")
            return 0.0
    
    async def _save_daily_metrics(self, metrics: DailyMetrics):
        """Guarda métricas diarias en base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO daily_metrics VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """, (
                    metrics.date, metrics.total_pnl, metrics.avg_pnl_per_agent,
                    metrics.total_trades, metrics.winning_trades, metrics.losing_trades,
                    metrics.win_rate, metrics.best_symbol, metrics.best_symbol_pnl,
                    metrics.worst_symbol, metrics.worst_symbol_pnl, metrics.daily_return,
                    metrics.volatility, metrics.sharpe_ratio, datetime.now().isoformat()
                ))
                
        except Exception as e:
            logger.error(f"❌ Error guardando métricas diarias: {e}")
    
    def get_global_summary(self) -> Dict[str, Any]:
        """Obtiene resumen global de métricas"""
        try:
            if not self.daily_metrics:
                return {"status": "no_data"}
            
            latest_metrics = self.daily_metrics[-1]
            
            # Calcular métricas acumuladas
            total_days = len(self.daily_metrics)
            cumulative_pnl = sum(m.total_pnl for m in self.daily_metrics)
            avg_daily_return = statistics.mean([m.daily_return for m in self.daily_metrics])
            
            # Win rate promedio
            total_trades_all = sum(m.total_trades for m in self.daily_metrics)
            total_wins_all = sum(m.winning_trades for m in self.daily_metrics)
            overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0
            
            # Mejor y peor día
            best_day = max(self.daily_metrics, key=lambda m: m.total_pnl)
            worst_day = min(self.daily_metrics, key=lambda m: m.total_pnl)
            
            # Ranking de símbolos
            symbol_ranking = sorted(
                self.symbol_stats.items(),
                key=lambda x: x[1].total_pnl_pct,
                reverse=True
            )
            
            # Top estrategias
            top_strategies = sorted(
                self.strategy_performance.items(),
                key=lambda x: x[1].performance_score,
                reverse=True
            )[:5]
            
            return {
                "summary": {
                    "total_days": total_days,
                    "cumulative_pnl": cumulative_pnl,
                    "avg_daily_return": avg_daily_return,
                    "overall_win_rate": overall_win_rate,
                    "current_sharpe": latest_metrics.sharpe_ratio,
                    "total_trades": total_trades_all
                },
                "latest_day": asdict(latest_metrics),
                "extremes": {
                    "best_day": {
                        "date": best_day.date,
                        "pnl": best_day.total_pnl,
                        "return": best_day.daily_return
                    },
                    "worst_day": {
                        "date": worst_day.date,
                        "pnl": worst_day.total_pnl,
                        "return": worst_day.daily_return
                    }
                },
                "symbol_ranking": [
                    {
                        "symbol": symbol,
                        "pnl_pct": stats.total_pnl_pct,
                        "win_rate": stats.win_rate,
                        "trades": stats.total_trades
                    }
                    for symbol, stats in symbol_ranking[:10]
                ],
                "top_strategies": [
                    {
                        "name": name,
                        "performance_score": perf.performance_score,
                        "success_rate": perf.success_rate,
                        "uses": perf.total_uses
                    }
                    for name, perf in top_strategies
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen global: {e}")
            return {"status": "error"}
    
    async def generate_report(self, output_file: str = None) -> str:
        """Genera reporte detallado de métricas"""
        try:
            summary = self.get_global_summary()
            
            if summary.get("status") == "no_data":
                return "No hay datos disponibles para generar reporte"
            
            # Generar reporte en formato Markdown
            report = f"""# Reporte de Métricas Globales - Trading Bot v10

## 📊 Resumen Ejecutivo
- **Total de días**: {summary['summary']['total_days']}
- **PnL acumulado**: ${summary['summary']['cumulative_pnl']:,.2f}
- **Retorno diario promedio**: {summary['summary']['avg_daily_return']:.2f}%
- **Win rate general**: {summary['summary']['overall_win_rate']:.1f}%
- **Sharpe ratio actual**: {summary['summary']['current_sharpe']:.2f}
- **Total de trades**: {summary['summary']['total_trades']:,}

## 📈 Último Día de Trading
- **Fecha**: {summary['latest_day']['date']}
- **PnL total**: ${summary['latest_day']['total_pnl']:+.2f}
- **PnL promedio por agente**: ${summary['latest_day']['avg_pnl_per_agent']:+.2f}
- **Trades ejecutados**: {summary['latest_day']['total_trades']}
- **Win rate**: {summary['latest_day']['win_rate']:.1f}%
- **Mejor símbolo**: {summary['latest_day']['best_symbol']} (${summary['latest_day']['best_symbol_pnl']:+.2f})
- **Peor símbolo**: {summary['latest_day']['worst_symbol']} (${summary['latest_day']['worst_symbol_pnl']:+.2f})

## 🏆 Ranking de Símbolos
"""
            
            for i, symbol_data in enumerate(summary['symbol_ranking'], 1):
                report += f"{i}. **{symbol_data['symbol']}**: {symbol_data['pnl_pct']:+.2f}% PnL, {symbol_data['win_rate']:.1f}% WR, {symbol_data['trades']} trades\n"
            
            report += f"""
## 🎯 Top Estrategias
"""
            
            for i, strategy_data in enumerate(summary['top_strategies'], 1):
                report += f"{i}. **{strategy_data['name']}**: Score {strategy_data['performance_score']:.3f}, {strategy_data['success_rate']:.1f}% éxito, {strategy_data['uses']} usos\n"
            
            report += f"""
## 📊 Extremos
- **Mejor día**: {summary['extremes']['best_day']['date']} (${summary['extremes']['best_day']['pnl']:+.2f}, {summary['extremes']['best_day']['return']:+.2f}%)
- **Peor día**: {summary['extremes']['worst_day']['date']} (${summary['extremes']['worst_day']['pnl']:+.2f}, {summary['extremes']['worst_day']['return']:+.2f}%)

---
*Reporte generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # Guardar archivo si se especifica
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                logger.info(f"📄 Reporte guardado en: {output_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "Error generando reporte de métricas"
    
    async def get_telegram_summary(self) -> str:
        """Genera resumen optimizado para Telegram"""
        try:
            if not self.daily_metrics:
                return "📊 <b>Métricas Globales</b>\n\n⚠️ No hay datos disponibles"
            
            latest = self.daily_metrics[-1]
            summary = self.get_global_summary()
            
            # Formatear mensaje para Telegram
            message = f"""📊 <b>Métricas Globales - {latest.date}</b>

💰 <b>Performance Diario:</b>
• PnL Total: ${latest.total_pnl:+.2f}
• PnL Promedio/Agente: ${latest.avg_pnl_per_agent:+.2f}
• Retorno Diario: {latest.daily_return:+.2f}%

🎯 <b>Trading:</b>
• Trades: {latest.total_trades} (✅{latest.winning_trades} ❌{latest.losing_trades})
• Win Rate: {latest.win_rate:.1f}%
• Sharpe Ratio: {latest.sharpe_ratio:.2f}

🏆 <b>Performers:</b>
• 🥇 Mejor: {latest.best_symbol} ({latest.best_symbol_pnl:+.2f})
• 🥉 Peor: {latest.worst_symbol} ({latest.worst_symbol_pnl:+.2f})

📈 <b>Acumulado ({summary['summary']['total_days']} días):</b>
• PnL Total: ${summary['summary']['cumulative_pnl']:+.2f}
• Win Rate: {summary['summary']['overall_win_rate']:.1f}%
• Total Trades: {summary['summary']['total_trades']:,}"""
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen para Telegram: {e}")
            return "❌ Error obteniendo métricas globales"
    
    async def export_data(self, format: str = "json", output_dir: str = "data/exports") -> str:
        """
        Exporta datos de métricas en formato especificado
        
        Args:
            format: Formato de exportación (json, csv, excel)
            output_dir: Directorio de salida
            
        Returns:
            Path del archivo exportado
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == "json":
                # Exportar como JSON
                export_file = output_path / f"metrics_export_{timestamp}.json"
                
                export_data = {
                    "export_info": {
                        "timestamp": datetime.now().isoformat(),
                        "format": "json",
                        "symbols": self.symbols
                    },
                    "daily_metrics": [asdict(m) for m in self.daily_metrics],
                    "symbol_stats": {k: asdict(v) for k, v in self.symbol_stats.items()},
                    "strategy_performance": {k: asdict(v) for k, v in self.strategy_performance.items()},
                    "global_summary": self.get_global_summary()
                }
                
                with open(export_file, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
            elif format.lower() == "csv":
                # Exportar métricas diarias como CSV
                export_file = output_path / f"daily_metrics_{timestamp}.csv"
                
                df = pd.DataFrame([asdict(m) for m in self.daily_metrics])
                df.to_csv(export_file, index=False)
                
            else:
                raise ValueError(f"Formato no soportado: {format}")
            
            logger.info(f"📤 Datos exportados a: {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.error(f"❌ Error exportando datos: {e}")
            return ""
    
    async def cleanup(self):
        """Limpia recursos del agregador"""
        try:
            # Guardar datos finales
            if self.daily_metrics:
                await self._save_daily_metrics(self.daily_metrics[-1])
            
            # Limpiar cache
            self.global_metrics_cache.clear()
            
            logger.info("🧹 MetricsAggregator limpiado")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando MetricsAggregator: {e}")

# Factory function
def create_metrics_aggregator(symbols: List[str]) -> MetricsAggregator:
    """Crea una instancia del agregador de métricas"""
    return MetricsAggregator(symbols)

# Utilidades para análisis
def calculate_performance_metrics(returns: List[float], risk_free_rate: float = 0.02) -> Dict[str, float]:
    """
    Calcula métricas de performance estándar
    
    Args:
        returns: Lista de retornos
        risk_free_rate: Tasa libre de riesgo
        
    Returns:
        Diccionario con métricas calculadas
    """
    try:
        if not returns or len(returns) < 2:
            return {}
        
        returns_array = np.array(returns)
        
        # Métricas básicas
        total_return = np.sum(returns_array)
        avg_return = np.mean(returns_array)
        volatility = np.std(returns_array)
        
        # Sharpe Ratio
        excess_returns = returns_array - (risk_free_rate / 365)
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(365) if np.std(excess_returns) > 0 else 0
        
        # Sortino Ratio (solo downside deviation)
        downside_returns = returns_array[returns_array < 0]
        downside_deviation = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino_ratio = avg_return / downside_deviation if downside_deviation > 0 else 0
        
        # Maximum Drawdown
        cumulative_returns = np.cumprod(1 + returns_array / 100)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown) * 100
        
        # Calmar Ratio
        calmar_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0
        
        return {
            "total_return": total_return,
            "avg_return": avg_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
            "win_rate": len([r for r in returns if r > 0]) / len(returns) * 100
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculando métricas de performance: {e}")
        return {}

# Función para análisis de correlación entre símbolos
def analyze_symbol_correlation(symbol_returns: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """
    Analiza correlación entre retornos de símbolos
    
    Args:
        symbol_returns: Retornos por símbolo
        
    Returns:
        Matriz de correlación
    """
    try:
        if len(symbol_returns) < 2:
            return {}
        
        # Crear DataFrame
        df = pd.DataFrame(symbol_returns)
        
        # Calcular matriz de correlación
        correlation_matrix = df.corr()
        
        # Convertir a diccionario
        correlation_dict = {}
        for symbol1 in correlation_matrix.index:
            correlation_dict[symbol1] = {}
            for symbol2 in correlation_matrix.columns:
                correlation_dict[symbol1][symbol2] = correlation_matrix.loc[symbol1, symbol2]
        
        return correlation_dict
        
    except Exception as e:
        logger.error(f"❌ Error analizando correlación: {e}")
        return {}