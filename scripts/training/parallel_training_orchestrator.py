#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel Training Orchestrator - Bot Trading v10 Enterprise
==========================================================
Coordinador principal del entrenamiento paralelo sincronizado.
Orquesta múltiples agentes y agrega resultados globales.

Características:
- Coordinación de múltiples agentes en paralelo
- Sincronización temporal perfecta
- Agregación de métricas globales (PnL, Winrate, etc.)
- Gestión de estrategias compartidas
- Progreso en tiempo real para Telegram
- Guardado automático de resultados

Uso desde Telegram:
    /train_hist → ejecuta este orchestrator

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import uuid
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Imports del proyecto
try:
    from core.sync.timestamp_synchronizer import TimestampSynchronizer, SyncPoint
    from core.agents.trading_agent import TradingAgent, TradeAction, ConfidenceLevel
    from config.unified_config import get_config_manager
except ImportError as e:
    print(f"⚠️ Imports no disponibles, usando fallbacks: {e}")
    # Fallbacks para desarrollo
    class TimestampSynchronizer:
        def __init__(self, symbols, timeframes): pass
        async def build_sync_timeline(self, start, end): return []
        async def get_synchronized_data(self, timestamp, tf): return {}
        async def cleanup(self): pass
    
    class SyncPoint:
        def __init__(self, timestamp, cycle_id): 
            self.timestamp = timestamp
            self.cycle_id = cycle_id
    
    class TradeAction:
        HOLD = "HOLD"
        BUY = "BUY"
        SELL = "SELL"
    
    class ConfidenceLevel:
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
    
    class TradingAgent:
        def __init__(self, symbol, balance): 
            self.symbol = symbol
            self.is_active = True
        async def make_trading_decision(self, data, tf): return None
        async def record_trade_result(self, trade_id, price, time): pass
        def get_agent_metrics(self): return {}
        async def save_agent_state(self): pass
        async def cleanup(self): pass
    
    def get_config_manager():
        class FallbackConfig:
            def get_symbols(self): return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
            def get_timeframes(self): return ["1h", "4h", "1d"]
            def get_initial_balance(self): return 1000.0
        return FallbackConfig()

logger = logging.getLogger(__name__)

@dataclass
class GlobalMetrics:
    """Métricas globales agregadas de todos los agentes"""
    timestamp: datetime
    cycle_id: int
    
    # Métricas financieras
    total_balance: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    
    # Métricas de trading
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Métricas de riesgo
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    
    # Métricas por símbolo
    symbol_performance: Dict[str, Dict[str, float]]
    
    # Top performers
    best_symbol: str
    worst_symbol: str
    best_strategy: str
    
    # Estado del sistema
    active_agents: int
    sync_quality: float

@dataclass
class CycleResult:
    """Resultado de un ciclo de entrenamiento"""
    cycle_id: int
    timestamp: datetime
    duration_seconds: float
    
    # Decisiones tomadas
    decisions_made: int
    trades_executed: int
    
    # Resultados por agente
    agent_results: Dict[str, Dict[str, Any]]
    
    # Métricas agregadas
    global_metrics: GlobalMetrics
    
    # Estrategias utilizadas
    strategies_used: Dict[str, int]
    new_strategies_discovered: List[str]

class ParallelTrainingOrchestrator:
    """
    Orchestrador de Entrenamiento Paralelo
    =====================================
    
    Coordina el entrenamiento sincronizado de múltiples agentes,
    agrega resultados globales y gestiona el progreso del sistema.
    """
    
    def __init__(self, symbols: List[str], timeframes: List[str], 
                 initial_balance: float = 1000.0):
        """
        Inicializa el orchestrador
        
        Args:
            symbols: Lista de símbolos a entrenar
            timeframes: Lista de timeframes
            initial_balance: Balance inicial por agente
        """
        self.symbols = symbols
        self.timeframes = timeframes
        self.initial_balance = initial_balance
        
        # Identificación de sesión
        self.session_id = f"parallel_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Componentes principales
        self.synchronizer = TimestampSynchronizer(symbols, timeframes)
        self.agents = {}
        self.executor = ThreadPoolExecutor(max_workers=len(symbols))
        
        # Estado del entrenamiento
        self.is_running = False
        self.current_cycle = 0
        self.total_cycles = 0
        self.start_time = None
        self.cycle_results = []
        self.global_strategy_library = {}
        
        # Configuración
        self.config = get_config_manager()
        self.progress_callback = None
        self.save_interval = 50  # Guardar cada 50 ciclos
        
        # Métricas agregadas
        self.cumulative_metrics = None
        
        # Directorios de salida
        self.output_dir = Path("data/training_sessions") / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎯 ParallelTrainingOrchestrator inicializado para {len(symbols)} símbolos")
    
    async def initialize_agents(self):
        """Inicializa agentes de trading para cada símbolo"""
        try:
            logger.info("🤖 Inicializando agentes de trading...")
            
            for symbol in self.symbols:
                agent = TradingAgent(symbol, self.initial_balance)
                self.agents[symbol] = agent
                
                logger.info(f"✅ Agente {symbol} inicializado")
            
            logger.info(f"✅ {len(self.agents)} agentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agentes: {e}")
            raise
    
    async def prepare_training_timeline(self, start_date: datetime, end_date: datetime):
        """Prepara el timeline de entrenamiento sincronizado"""
        try:
            logger.info("📅 Preparando timeline de entrenamiento...")
            
            # Construir puntos de sincronización
            sync_points = await self.synchronizer.build_sync_timeline(start_date, end_date)
            
            if not sync_points:
                raise ValueError("No se pudieron generar puntos de sincronización")
            
            self.total_cycles = len(sync_points)
            
            logger.info(f"✅ Timeline preparado: {self.total_cycles} ciclos de entrenamiento")
            
            return sync_points
            
        except Exception as e:
            logger.error(f"❌ Error preparando timeline: {e}")
            raise
    
    async def execute_training_session(self, start_date: datetime, end_date: datetime, 
                                     progress_callback=None) -> Dict[str, Any]:
        """
        Ejecuta sesión completa de entrenamiento paralelo
        
        Args:
            start_date: Fecha de inicio del entrenamiento
            end_date: Fecha de fin del entrenamiento
            progress_callback: Función callback para progreso
            
        Returns:
            Diccionario con resultados de la sesión
        """
        try:
            self.start_time = datetime.now()
            self.progress_callback = progress_callback
            self.is_running = True
            
            logger.info(f"🚀 Iniciando sesión de entrenamiento paralelo: {self.session_id}")
            
            # 1. Inicializar agentes
            await self.initialize_agents()
            
            # 2. Preparar timeline
            sync_points = await self.prepare_training_timeline(start_date, end_date)
            
            # 3. Ejecutar entrenamiento por ciclos
            await self._execute_training_cycles(sync_points)
            
            # 4. Generar resultados finales
            final_results = await self._generate_final_results()
            
            # 5. Guardar sesión completa
            await self._save_training_session(final_results)
            
            self.is_running = False
            
            logger.info(f"✅ Sesión de entrenamiento completada: {self.session_id}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error en sesión de entrenamiento: {e}")
            self.is_running = False
            raise
    
    async def _execute_training_cycles(self, sync_points: List[SyncPoint]):
        """Ejecuta todos los ciclos de entrenamiento"""
        try:
            logger.info(f"🔄 Ejecutando {len(sync_points)} ciclos de entrenamiento...")
            
            for i, sync_point in enumerate(sync_points):
                self.current_cycle = i + 1
                
                # Actualizar progreso
                await self._update_progress(
                    progress=(self.current_cycle / self.total_cycles) * 100,
                    status=f"Ciclo {self.current_cycle}/{self.total_cycles}",
                    timestamp=sync_point.timestamp
                )
                
                # Ejecutar ciclo individual
                cycle_result = await self._execute_single_cycle(sync_point)
                
                # Guardar resultado del ciclo
                self.cycle_results.append(cycle_result)
                
                # Guardar progreso periódicamente
                if self.current_cycle % self.save_interval == 0:
                    await self._save_intermediate_results()
                
                # Pequeña pausa para evitar sobrecarga
                await asyncio.sleep(0.1)
            
            logger.info("✅ Todos los ciclos de entrenamiento completados")
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclos de entrenamiento: {e}")
            raise
    
    async def _execute_single_cycle(self, sync_point: SyncPoint) -> CycleResult:
        """Ejecuta un ciclo individual de entrenamiento"""
        try:
            cycle_start = datetime.now()
            
            # Obtener datos sincronizados para todos los símbolos
            synchronized_data = await self.synchronizer.get_synchronized_data(
                sync_point.timestamp, "1h"
            )
            
            # Ejecutar análisis paralelo de todos los agentes
            agent_tasks = []
            for symbol, agent in self.agents.items():
                if symbol in synchronized_data and not synchronized_data[symbol].empty:
                    task = self._execute_agent_cycle(agent, synchronized_data[symbol], sync_point)
                    agent_tasks.append(task)
            
            # Esperar a que todos los agentes completen su análisis
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Procesar resultados de agentes
            valid_results = {}
            decisions_made = 0
            trades_executed = 0
            strategies_used = {}
            
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Error en agente {list(self.agents.keys())[i]}: {result}")
                    continue
                
                symbol = result['symbol']
                valid_results[symbol] = result
                
                if result.get('decision'):
                    decisions_made += 1
                    strategy = result['decision']['strategy_used']
                    strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
                
                if result.get('trade_executed'):
                    trades_executed += 1
            
            # Calcular métricas globales del ciclo
            global_metrics = await self._calculate_global_metrics(sync_point.timestamp, sync_point.cycle_id)
            
            # Crear resultado del ciclo
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            
            cycle_result = CycleResult(
                cycle_id=sync_point.cycle_id,
                timestamp=sync_point.timestamp,
                duration_seconds=cycle_duration,
                decisions_made=decisions_made,
                trades_executed=trades_executed,
                agent_results=valid_results,
                global_metrics=global_metrics,
                strategies_used=strategies_used,
                new_strategies_discovered=[]  # TODO: Implementar detección de nuevas estrategias
            )
            
            return cycle_result
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo individual: {e}")
            raise
    
    async def _execute_agent_cycle(self, agent: TradingAgent, market_data: pd.DataFrame, 
                                 sync_point: SyncPoint) -> Dict[str, Any]:
        """Ejecuta un ciclo para un agente específico"""
        try:
            # Análisis de mercado
            decision = await agent.make_trading_decision(market_data, "1h")
            
            # Simular ejecución de trade (en entrenamiento)
            trade_executed = False
            pnl = 0.0
            
            if decision and decision.action != TradeAction.HOLD:
                # Simular resultado del trade basado en datos futuros
                pnl = await self._simulate_trade_outcome(decision, market_data)
                trade_executed = True
                
                # Registrar resultado en el agente
                exit_time = sync_point.timestamp + timedelta(hours=1)  # Simplificado
                exit_price = decision.price + (pnl / decision.quantity)
                await agent.record_trade_result(str(uuid.uuid4()), exit_price, exit_time)
            
            # Obtener métricas del agente
            agent_metrics = agent.get_agent_metrics()
            
            return {
                'symbol': agent.symbol,
                'timestamp': sync_point.timestamp,
                'decision': asdict(decision) if decision else None,
                'trade_executed': trade_executed,
                'pnl': pnl,
                'agent_metrics': agent_metrics,
                'analysis_duration': 0.1  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando ciclo para agente {agent.symbol}: {e}")
            return {
                'symbol': agent.symbol,
                'error': str(e),
                'agent_metrics': {}
            }
    
    async def _simulate_trade_outcome(self, decision, market_data: pd.DataFrame) -> float:
        """Simula el resultado de un trade basado en datos históricos"""
        try:
            # Simplificación: usar datos futuros para simular resultado
            current_price = decision.price
            
            # Simular movimiento basado en volatilidad histórica
            volatility = market_data['close'].pct_change().std()
            
            # Generar resultado aleatorio pero basado en la decisión
            confluence_score = decision.features_analyzed.get('confluence_score', 0)
            
            # Probabilidad de éxito basada en confluence
            success_prob = 0.5 + (confluence_score * 0.3)
            
            # Simular resultado
            if np.random.random() < success_prob:
                # Trade exitoso
                return_pct = np.random.normal(0.02, volatility)  # 2% promedio con volatilidad
            else:
                # Trade fallido
                return_pct = np.random.normal(-0.015, volatility)  # -1.5% promedio
            
            pnl = current_price * decision.quantity * return_pct
            
            return pnl
            
        except Exception as e:
            logger.error(f"❌ Error simulando resultado de trade: {e}")
            return 0.0
    
    async def _calculate_global_metrics(self, timestamp: datetime, cycle_id: int) -> GlobalMetrics:
        """Calcula métricas globales agregadas"""
        try:
            # Agregar métricas de todos los agentes
            total_balance = 0.0
            total_pnl = 0.0
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            daily_pnl = 0.0
            max_drawdown = 0.0
            current_drawdown = 0.0
            
            symbol_performance = {}
            active_agents = 0
            
            for symbol, agent in self.agents.items():
                if agent.is_active:
                    active_agents += 1
                    metrics = agent.get_agent_metrics()
                    
                    total_balance += metrics.get('current_balance', 0)
                    total_pnl += metrics.get('total_pnl', 0)
                    total_trades += metrics.get('total_trades', 0)
                    winning_trades += metrics.get('winning_trades', 0)
                    losing_trades += metrics.get('losing_trades', 0)
                    daily_pnl += metrics.get('daily_pnl', 0)
                    max_drawdown = max(max_drawdown, metrics.get('max_drawdown', 0))
                    current_drawdown += metrics.get('current_drawdown', 0)
                    
                    # Performance por símbolo
                    symbol_performance[symbol] = {
                        'balance': metrics.get('current_balance', 0),
                        'pnl_pct': metrics.get('total_pnl_pct', 0),
                        'win_rate': metrics.get('win_rate', 0),
                        'trades': metrics.get('total_trades', 0)
                    }
            
            # Calcular métricas derivadas
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_pnl_pct = (total_pnl / (len(self.agents) * self.initial_balance)) * 100
            current_drawdown = current_drawdown / len(self.agents) if len(self.agents) > 0 else 0
            
            # Encontrar mejores y peores performers
            best_symbol = max(symbol_performance.keys(), 
                            key=lambda s: symbol_performance[s]['pnl_pct']) if symbol_performance else ""
            worst_symbol = min(symbol_performance.keys(), 
                             key=lambda s: symbol_performance[s]['pnl_pct']) if symbol_performance else ""
            
            # Calcular Sharpe ratio simplificado
            if len(self.cycle_results) > 10:
                returns = [r.global_metrics.daily_pnl for r in self.cycle_results[-10:]]
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
            
            return GlobalMetrics(
                timestamp=timestamp,
                cycle_id=cycle_id,
                total_balance=total_balance,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                daily_pnl=daily_pnl,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                sharpe_ratio=sharpe_ratio,
                symbol_performance=symbol_performance,
                best_symbol=best_symbol,
                worst_symbol=worst_symbol,
                best_strategy="",  # TODO: Implementar tracking de mejores estrategias
                active_agents=active_agents,
                sync_quality=1.0  # TODO: Calcular calidad de sincronización real
            )
            
        except Exception as e:
            logger.error(f"❌ Error calculando métricas globales: {e}")
            return GlobalMetrics(
                timestamp=timestamp,
                cycle_id=cycle_id,
                total_balance=0,
                total_pnl=0,
                total_pnl_pct=0,
                daily_pnl=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                max_drawdown=0,
                current_drawdown=0,
                sharpe_ratio=0,
                symbol_performance={},
                best_symbol="",
                worst_symbol="",
                best_strategy="",
                active_agents=0,
                sync_quality=0
            )
    
    async def _update_progress(self, progress: float, status: str, timestamp: datetime):
        """Actualiza progreso y notifica callback"""
        try:
            if self.progress_callback:
                progress_data = {
                    'session_id': self.session_id,
                    'progress': progress,
                    'status': status,
                    'current_cycle': self.current_cycle,
                    'total_cycles': self.total_cycles,
                    'timestamp': timestamp.isoformat(),
                    'symbols': self.symbols,
                    'elapsed_time': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
                }
                
                await self.progress_callback(progress_data)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando progreso: {e}")
    
    async def _save_intermediate_results(self):
        """Guarda resultados intermedios"""
        try:
            # Guardar resultados de ciclos
            cycles_file = self.output_dir / f"cycles_{self.current_cycle}.json"
            cycles_data = {
                'session_id': self.session_id,
                'cycles_completed': self.current_cycle,
                'total_cycles': self.total_cycles,
                'last_save': datetime.now().isoformat(),
                'cycle_results': [asdict(result) for result in self.cycle_results[-self.save_interval:]]
            }
            
            with open(cycles_file, 'w') as f:
                json.dump(cycles_data, f, indent=2, default=str)
            
            # Guardar estado de agentes
            for symbol, agent in self.agents.items():
                await agent.save_agent_state()
            
            logger.info(f"💾 Resultados intermedios guardados en ciclo {self.current_cycle}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados intermedios: {e}")
    
    async def _generate_final_results(self) -> Dict[str, Any]:
        """Genera resultados finales de la sesión"""
        try:
            session_duration = (datetime.now() - self.start_time).total_seconds()
            
            # Métricas finales globales
            final_metrics = None
            if self.cycle_results:
                final_metrics = self.cycle_results[-1].global_metrics
            
            # Estadísticas de la sesión
            total_decisions = sum(r.decisions_made for r in self.cycle_results)
            total_trades = sum(r.trades_executed for r in self.cycle_results)
            
            # Performance por agente
            agent_summaries = {}
            for symbol, agent in self.agents.items():
                agent_summaries[symbol] = agent.get_agent_metrics()
            
            # Top estrategias utilizadas
            all_strategies = {}
            for result in self.cycle_results:
                for strategy, count in result.strategies_used.items():
                    all_strategies[strategy] = all_strategies.get(strategy, 0) + count
            
            top_strategies = sorted(all_strategies.items(), key=lambda x: x[1], reverse=True)[:10]
            
            final_results = {
                'session_info': {
                    'session_id': self.session_id,
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration_seconds': session_duration,
                    'symbols': self.symbols,
                    'timeframes': self.timeframes,
                    'initial_balance_per_agent': self.initial_balance
                },
                'performance_summary': {
                    'cycles_completed': len(self.cycle_results),
                    'total_decisions': total_decisions,
                    'total_trades': total_trades,
                    'final_metrics': asdict(final_metrics) if final_metrics else {},
                    'agent_summaries': agent_summaries
                },
                'strategy_analysis': {
                    'top_strategies': top_strategies,
                    'total_unique_strategies': len(all_strategies),
                    'strategy_distribution': all_strategies
                },
                'cycle_summaries': [
                    {
                        'cycle_id': r.cycle_id,
                        'timestamp': r.timestamp.isoformat(),
                        'decisions': r.decisions_made,
                        'trades': r.trades_executed,
                        'global_pnl': r.global_metrics.total_pnl,
                        'win_rate': r.global_metrics.win_rate
                    }
                    for r in self.cycle_results
                ]
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error generando resultados finales: {e}")
            return {}
    
    async def _save_training_session(self, final_results: Dict[str, Any]):
        """Guarda la sesión completa de entrenamiento"""
        try:
            # Guardar resultados finales
            results_file = self.output_dir / "final_results.json"
            with open(results_file, 'w') as f:
                json.dump(final_results, f, indent=2, default=str)
            
            # Guardar todos los ciclos
            all_cycles_file = self.output_dir / "all_cycles.json"
            all_cycles_data = {
                'session_id': self.session_id,
                'total_cycles': len(self.cycle_results),
                'cycles': [asdict(result) for result in self.cycle_results]
            }
            
            with open(all_cycles_file, 'w') as f:
                json.dump(all_cycles_data, f, indent=2, default=str)
            
            # Guardar estados finales de agentes
            for symbol, agent in self.agents.items():
                await agent.save_agent_state()
            
            # Crear resumen ejecutivo
            executive_summary = self._create_executive_summary(final_results)
            summary_file = self.output_dir / "executive_summary.md"
            
            with open(summary_file, 'w') as f:
                f.write(executive_summary)
            
            logger.info(f"💾 Sesión completa guardada en: {self.output_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando sesión de entrenamiento: {e}")
    
    def _create_executive_summary(self, results: Dict[str, Any]) -> str:
        """Crea resumen ejecutivo en formato Markdown"""
        try:
            session_info = results.get('session_info', {})
            performance = results.get('performance_summary', {})
            final_metrics = performance.get('final_metrics', {})
            
            summary = f"""# Resumen Ejecutivo - Entrenamiento Paralelo

## 📊 Información de la Sesión
- **ID de Sesión**: {session_info.get('session_id', 'N/A')}
- **Duración**: {session_info.get('duration_seconds', 0):.0f} segundos
- **Símbolos**: {', '.join(session_info.get('symbols', []))}
- **Ciclos Completados**: {performance.get('cycles_completed', 0)}

## 🎯 Resultados Principales
- **Balance Total Final**: ${final_metrics.get('total_balance', 0):,.2f}
- **PnL Total**: ${final_metrics.get('total_pnl', 0):,.2f} ({final_metrics.get('total_pnl_pct', 0):.2f}%)
- **Win Rate Global**: {final_metrics.get('win_rate', 0):.1f}%
- **Total de Trades**: {final_metrics.get('total_trades', 0)}
- **Sharpe Ratio**: {final_metrics.get('sharpe_ratio', 0):.2f}
- **Max Drawdown**: {final_metrics.get('max_drawdown', 0):.2f}%

## 🏆 Top Performers
- **Mejor Símbolo**: {final_metrics.get('best_symbol', 'N/A')}
- **Peor Símbolo**: {final_metrics.get('worst_symbol', 'N/A')}

## 📈 Performance por Símbolo
"""
            
            agent_summaries = performance.get('agent_summaries', {})
            for symbol, metrics in agent_summaries.items():
                pnl_pct = metrics.get('total_pnl_pct', 0)
                win_rate = metrics.get('win_rate', 0)
                trades = metrics.get('total_trades', 0)
                
                summary += f"- **{symbol}**: {pnl_pct:+.2f}% PnL, {win_rate:.1f}% WR, {trades} trades\n"
            
            summary += f"""
## 🎯 Archivos Generados
- `final_results.json` - Resultados completos
- `all_cycles.json` - Detalle de todos los ciclos
- `executive_summary.md` - Este resumen
- `data/agents/{{symbol}}/` - Estados de agentes individuales

---
*Generado automáticamente por Bot Trading v10 Enterprise*
"""
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error creando resumen ejecutivo: {e}")
            return "# Error generando resumen ejecutivo"
    
    def get_progress_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del progreso"""
        try:
            if not self.is_running:
                return {'status': 'not_running', 'progress': 0}
            
            progress = (self.current_cycle / self.total_cycles * 100) if self.total_cycles > 0 else 0
            
            return {
                'status': 'running',
                'session_id': self.session_id,
                'progress': progress,
                'current_cycle': self.current_cycle,
                'total_cycles': self.total_cycles,
                'symbols': self.symbols,
                'active_agents': len([a for a in self.agents.values() if a.is_active]),
                'elapsed_time': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de progreso: {e}")
            return {'status': 'error', 'progress': 0}
    
    async def stop_training(self):
        """Detiene el entrenamiento de forma elegante"""
        logger.info("🛑 Deteniendo entrenamiento paralelo...")
        try:
            self.is_running = False
            # Guardar resultados intermedios
            await self._save_intermediate_results()
            # Limpiar agentes
            for agent in self.agents.values():
                try:
                    await agent.cleanup()
                except Exception:
                    pass
            # Limpiar synchronizer
            try:
                await self.synchronizer.cleanup()
            except Exception:
                pass
            logger.info("✅ Entrenamiento paralelo detenido")
            return True
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento: {e}")
            return False

# Factory function para uso desde otros módulos
async def create_parallel_training_orchestrator(symbols: List[str], timeframes: List[str], 
                                               initial_balance: float = 1000.0) -> 'ParallelTrainingOrchestrator':
    """
    Crea instancia del orchestrador de entrenamiento paralelo
    
    Args:
        symbols: Lista de símbolos a entrenar
        timeframes: Lista de timeframes
        initial_balance: Balance inicial por agente
        
    Returns:
        Instancia configurada del orchestrador
    """
    return ParallelTrainingOrchestrator(symbols, timeframes, initial_balance)