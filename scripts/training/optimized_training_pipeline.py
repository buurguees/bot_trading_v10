#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/training/optimized_training_pipeline.py
===============================================
Pipeline Optimizado para Entrenamiento Robusto de Días

Sistema de entrenamiento paralelo optimizado con gestión de memoria,
checkpointing automático, recovery de errores y reporting completo.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import gc
import logging
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import pickle
import pandas as pd
import numpy as np

# Imports del proyecto
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.metrics.trade_metrics import DetailedTradeMetric
from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator, PortfolioMetrics
from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
from core.agents.trading_agent import TradingAgent
from core.data.database import DatabaseManager
from config.unified_config import get_config_manager

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuración del pipeline de entrenamiento"""
    days_back: int = 365
    cycle_size_hours: int = 24
    max_concurrent_agents: int = 8
    checkpoint_interval: int = 100  # Checkpoint cada N ciclos
    memory_cleanup_interval: int = 50  # Cleanup cada N ciclos
    max_memory_usage_mb: int = 8000  # Límite de memoria
    telegram_enabled: bool = True
    recovery_enabled: bool = True

@dataclass
class CycleData:
    """Datos de un ciclo de entrenamiento"""
    cycle_id: int
    start_time: datetime
    end_time: datetime
    sync_point: datetime
    market_data: Dict[str, Dict[str, Any]]
    agent_results: Dict[str, List[DetailedTradeMetric]]
    portfolio_metrics: Optional[PortfolioMetrics] = None
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0

@dataclass
class TrainingSession:
    """Sesión de entrenamiento completa"""
    session_id: str
    start_time: datetime
    config: TrainingConfig
    total_cycles: int
    completed_cycles: int
    total_trades: int
    total_pnl: float
    best_cycle: Optional[int] = None
    worst_cycle: Optional[int] = None
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0

class OptimizedTrainingPipeline:
    """Pipeline optimizado para entrenamientos largos con gestión de memoria"""
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Inicializa el pipeline de entrenamiento
        
        Args:
            config: Configuración del pipeline
        """
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Componentes principales
        self.config_manager = get_config_manager()
        self.db_manager = DatabaseManager()
        self.metrics_aggregator = EnhancedMetricsAggregator()
        self.telegram_reporter = None
        
        # Estado del entrenamiento
        self.session: Optional[TrainingSession] = None
        self.active_agents: Dict[str, TradingAgent] = {}
        self.cycle_data_cache: Dict[int, CycleData] = {}
        
        # Control de concurrencia
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_agents)
        self.memory_monitor = MemoryMonitor(self.config.max_memory_usage_mb)
        
        # Directorios de trabajo
        self.output_dir = Path("data/training_sessions")
        self.checkpoint_dir = self.output_dir / "checkpoints"
        self.logs_dir = Path("logs")
        
        # Crear directorios
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"✅ OptimizedTrainingPipeline inicializado con {self.config.max_concurrent_agents} agentes concurrentes")
    
    async def initialize(self) -> bool:
        """Inicializa el pipeline y todos sus componentes"""
        try:
            # Inicializar configuración
            self.symbols = self.config_manager.get_symbols()
            self.timeframes = self.config_manager.get_timeframes()
            
            # Inicializar agentes
            await self._initialize_agents()
            
            # Inicializar Telegram si está habilitado
            if self.config.telegram_enabled:
                await self._initialize_telegram()
            
            # Crear sesión de entrenamiento
            self.session = TrainingSession(
                session_id=f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                start_time=datetime.now(),
                config=self.config,
                total_cycles=0,
                completed_cycles=0,
                total_trades=0,
                total_pnl=0.0
            )
            
            self.logger.info(f"✅ Pipeline inicializado: {len(self.symbols)} símbolos, {len(self.timeframes)} timeframes")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando pipeline: {e}")
            return False
    
    async def execute_multi_day_training(self) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento multi-día optimizado
        
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            if not self.session:
                raise RuntimeError("Pipeline no inicializado. Llama a initialize() primero.")
            
            self.logger.info(f"🚀 Iniciando entrenamiento multi-día: {self.config.days_back} días")
            
            # 1. Crear timeline maestro optimizado
            master_timeline = await self._create_optimized_master_timeline()
            
            # 2. Dividir en ciclos inteligentes
            training_cycles = self._create_intelligent_cycles(master_timeline)
            self.session.total_cycles = len(training_cycles)
            
            # 3. Pre-cargar datos en memoria (batch loading)
            await self._preload_market_data(training_cycles)
            
            # 4. Ejecutar ciclos con gestión de memoria
            cycle_results = []
            for cycle_id, cycle_data in enumerate(training_cycles):
                
                # Verificar memoria antes del ciclo
                if not await self._check_memory_usage():
                    await self._force_memory_cleanup()
                
                # Ejecutar ciclo con límite de concurrencia
                cycle_result = await self._execute_synchronized_cycle(cycle_id, cycle_data)
                
                if cycle_result:
                    cycle_results.append(cycle_result)
                    
                    # Procesar resultados inmediatamente
                    await self._process_cycle_results(cycle_result)
                    
                    # Enviar updates a Telegram
                    if self.telegram_reporter:
                        await self._send_telegram_updates(cycle_result)
                    
                    # Checkpoint si es necesario
                    if cycle_id % self.config.checkpoint_interval == 0:
                        await self._create_checkpoint(cycle_id, cycle_results)
                    
                    # Cleanup de memoria si es necesario
                    if cycle_id % self.config.memory_cleanup_interval == 0:
                        await self._cleanup_cycle_data(cycle_id)
                
                # Actualizar progreso
                self.session.completed_cycles = cycle_id + 1
                progress_pct = (self.session.completed_cycles / self.session.total_cycles) * 100
                
                if cycle_id % 10 == 0:  # Log cada 10 ciclos
                    self.logger.info(f"📊 Progreso: {cycle_id + 1}/{self.session.total_cycles} ({progress_pct:.1f}%)")
            
            # 5. Generar reporte final
            final_report = await self._generate_final_report(cycle_results)
            
            # 6. Guardar resultados
            await self._save_training_results(final_report)
            
            self.logger.info(f"✅ Entrenamiento completado: {self.session.completed_cycles} ciclos, {self.session.total_trades} trades")
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"❌ Error en entrenamiento multi-día: {e}")
            await self._handle_training_error(e)
            return {'error': str(e), 'completed_cycles': self.session.completed_cycles if self.session else 0}
    
    async def _initialize_agents(self):
        """Inicializa agentes de trading para cada símbolo"""
        try:
            for symbol in self.symbols:
                agent = TradingAgent(symbol, initial_balance=1000.0)
                self.active_agents[symbol] = agent
                self.logger.info(f"🤖 Agente {symbol} inicializado")
            
            self.logger.info(f"✅ {len(self.active_agents)} agentes inicializados")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando agentes: {e}")
            raise
    
    async def _initialize_telegram(self):
        """Inicializa el reporter de Telegram"""
        try:
            # TODO: Cargar configuración real de Telegram
            telegram_config = TelegramConfig(
                bot_token="YOUR_BOT_TOKEN",
                chat_id="YOUR_CHAT_ID",
                enable_individual_trades=True,
                enable_cycle_summaries=True,
                enable_alerts=True
            )
            
            self.telegram_reporter = TelegramTradeReporter(telegram_config)
            self.logger.info("✅ Telegram reporter inicializado")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando Telegram: {e}")
            self.telegram_reporter = None
    
    async def _create_optimized_master_timeline(self) -> List[datetime]:
        """Crea timeline maestro optimizado para el período de entrenamiento"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config.days_back)
            
            # Crear timeline con resolución de 1 hora para optimizar memoria
            timeline = []
            current_time = start_date
            
            while current_time <= end_date:
                timeline.append(current_time)
                current_time += timedelta(hours=1)
            
            self.logger.info(f"✅ Timeline maestro creado: {len(timeline)} puntos desde {start_date} hasta {end_date}")
            return timeline
            
        except Exception as e:
            self.logger.error(f"❌ Error creando timeline maestro: {e}")
            raise
    
    def _create_intelligent_cycles(self, master_timeline: List[datetime]) -> List[Dict[str, Any]]:
        """Crea ciclos inteligentes basados en el timeline maestro"""
        try:
            cycles = []
            cycle_size_hours = self.config.cycle_size_hours
            
            for i in range(0, len(master_timeline), cycle_size_hours):
                cycle_start = master_timeline[i]
                cycle_end = master_timeline[min(i + cycle_size_hours - 1, len(master_timeline) - 1)]
                
                cycle_data = {
                    'cycle_id': len(cycles),
                    'start_time': cycle_start,
                    'end_time': cycle_end,
                    'sync_point': cycle_start,  # Punto de sincronización
                    'duration_hours': cycle_size_hours
                }
                
                cycles.append(cycle_data)
            
            self.logger.info(f"✅ {len(cycles)} ciclos inteligentes creados")
            return cycles
            
        except Exception as e:
            self.logger.error(f"❌ Error creando ciclos inteligentes: {e}")
            raise
    
    async def _preload_market_data(self, training_cycles: List[Dict[str, Any]]):
        """Pre-carga datos de mercado en memoria de forma optimizada"""
        try:
            self.logger.info("📊 Pre-cargando datos de mercado...")
            
            # Cargar datos en batches para optimizar memoria
            batch_size = 10  # Ciclos por batch
            
            for i in range(0, len(training_cycles), batch_size):
                batch_cycles = training_cycles[i:i + batch_size]
                
                for cycle_data in batch_cycles:
                    # Cargar datos para este ciclo
                    market_data = await self._load_cycle_market_data(cycle_data)
                    cycle_data['market_data'] = market_data
                
                # Pequeño delay para no sobrecargar la base de datos
                await asyncio.sleep(0.1)
            
            self.logger.info("✅ Datos de mercado pre-cargados")
            
        except Exception as e:
            self.logger.error(f"❌ Error pre-cargando datos: {e}")
            raise
    
    async def _load_cycle_market_data(self, cycle_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Carga datos de mercado para un ciclo específico"""
        try:
            market_data = {}
            
            for symbol in self.symbols:
                symbol_data = {}
                
                for timeframe in self.timeframes:
                    # Cargar datos desde la base de datos
                    data = self.db_manager.get_historical_data(
                        symbol, 
                        timeframe, 
                        cycle_data['start_time'], 
                        cycle_data['end_time']
                    )
                    symbol_data[timeframe] = data
                
                market_data[symbol] = symbol_data
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando datos del ciclo: {e}")
            return {}
    
    async def _execute_synchronized_cycle(self, cycle_id: int, cycle_data: Dict[str, Any]) -> Optional[CycleData]:
        """Ejecuta un ciclo sincronizado con límite de concurrencia"""
        try:
            start_time = time.time()
            
            # Verificar memoria antes del ciclo
            memory_usage = self.memory_monitor.get_memory_usage()
            
            # Ejecutar con semáforo para controlar concurrencia
            async with self.semaphore:
                # Crear tareas paralelas por agente
                agent_tasks = []
                for symbol, agent in self.active_agents.items():
                    task = asyncio.create_task(
                        self._execute_agent_cycle(agent, cycle_data, symbol)
                    )
                    agent_tasks.append((symbol, task))
                
                # Esperar a que todos los agentes completen
                agent_results = {}
                for symbol, task in agent_tasks:
                    try:
                        result = await task
                        agent_results[symbol] = result
                    except Exception as e:
                        self.logger.error(f"❌ Agente {symbol} falló en ciclo {cycle_id}: {e}")
                        agent_results[symbol] = []
                
                # Calcular métricas agregadas
                portfolio_metrics = await self.metrics_aggregator.calculate_portfolio_metrics(
                    agent_results, 
                    cycle_id
                )
                
                # Crear objeto CycleData
                cycle_result = CycleData(
                    cycle_id=cycle_id,
                    start_time=cycle_data['start_time'],
                    end_time=cycle_data['end_time'],
                    sync_point=cycle_data['sync_point'],
                    market_data=cycle_data.get('market_data', {}),
                    agent_results=agent_results,
                    portfolio_metrics=portfolio_metrics,
                    processing_time=time.time() - start_time,
                    memory_usage_mb=memory_usage
                )
                
                # Guardar en cache
                self.cycle_data_cache[cycle_id] = cycle_result
                
                return cycle_result
                
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando ciclo {cycle_id}: {e}")
            return None
    
    async def _execute_agent_cycle(self, agent: TradingAgent, cycle_data: Dict[str, Any], symbol: str) -> List[DetailedTradeMetric]:
        """Ejecuta un ciclo para un agente específico"""
        try:
            trades = []
            
            # Obtener datos del agente
            agent_data = cycle_data.get('market_data', {}).get(symbol, {})
            
            if not agent_data:
                return trades
            
            # Simular trading para cada timeframe
            for timeframe, data in agent_data.items():
                if not data:
                    continue
                
                # Convertir datos a DataFrame
                df = self._data_to_dataframe(data)
                
                if df.empty:
                    continue
                
                # Simular trades para este timeframe
                timeframe_trades = await self._simulate_agent_trading(
                    agent, df, timeframe, cycle_data['sync_point']
                )
                
                trades.extend(timeframe_trades)
            
            return trades
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando ciclo del agente {symbol}: {e}")
            return []
    
    async def _simulate_agent_trading(
        self, 
        agent: TradingAgent, 
        df: 'pd.DataFrame', 
        timeframe: str, 
        sync_point: datetime
    ) -> List[DetailedTradeMetric]:
        """Simula trading para un agente en un timeframe específico"""
        try:
            trades = []
            
            # Lógica de simulación simplificada
            # En un sistema real, esto sería más complejo
            
            for i in range(1, len(df)):
                current_row = df.iloc[i]
                previous_row = df.iloc[i-1]
                
                # Lógica de trading simple (ejemplo)
                if current_row['close'] > previous_row['close'] * 1.01:  # Subida > 1%
                    # Crear trade LONG
                    trade_data = {
                        'action': 'LONG',
                        'entry_price': current_row['close'],
                        'exit_price': current_row['close'] * 1.02,  # +2% target
                        'quantity': 0.1,
                        'leverage': 1.0,
                        'entry_time': sync_point + timedelta(hours=i),
                        'exit_time': sync_point + timedelta(hours=i+1),
                        'duration_candles': 1,
                        'balance_before': 1000.0,
                        'follow_plan': True,
                        'exit_reason': 'TAKE_PROFIT',
                        'slippage': 0.0,
                        'commission': 0.0,
                        'timeframe': timeframe
                    }
                    
                    technical_analysis = {
                        'confidence_level': 'MEDIUM',
                        'strategy_name': 'trend_following',
                        'confluence_score': 0.7,
                        'risk_reward_ratio': 2.0,
                        'indicators': {'rsi': 65.0, 'macd': 0.1},
                        'support_resistance': {'support': current_row['low'], 'resistance': current_row['high']},
                        'trend_strength': 0.6,
                        'momentum_score': 0.7
                    }
                    
                    market_context = {
                        'market_regime': 'TRENDING_UP',
                        'volatility_level': 0.02,
                        'volume_confirmation': True,
                        'market_session': 'EUROPEAN',
                        'news_impact': None
                    }
                    
                    # Crear métrica detallada
                    trade_metric = DetailedTradeMetric.create_from_trade_data(
                        trade_data, agent.symbol, 0, technical_analysis, market_context
                    )
                    
                    trades.append(trade_metric)
            
            return trades
            
        except Exception as e:
            self.logger.error(f"❌ Error simulando trading: {e}")
            return []
    
    def _data_to_dataframe(self, data: List[Dict]) -> 'pd.DataFrame':
        """Convierte datos de lista a DataFrame"""
        try:
            import pandas as pd
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp').sort_index()
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error convirtiendo datos a DataFrame: {e}")
            return pd.DataFrame()
    
    async def _process_cycle_results(self, cycle_result: CycleData):
        """Procesa resultados de un ciclo"""
        try:
            # Actualizar estadísticas de la sesión
            if self.session:
                self.session.total_trades += sum(len(trades) for trades in cycle_result.agent_results.values())
                
                if cycle_result.portfolio_metrics:
                    self.session.total_pnl += cycle_result.portfolio_metrics.total_pnl_usdt
                    
                    # Actualizar drawdown
                    if cycle_result.portfolio_metrics.total_pnl_usdt < 0:
                        self.session.current_drawdown += abs(cycle_result.portfolio_metrics.total_pnl_usdt)
                        self.session.max_drawdown = max(self.session.max_drawdown, self.session.current_drawdown)
                    else:
                        self.session.current_drawdown = 0.0
                    
                    # Actualizar mejor/peor ciclo
                    if not self.session.best_cycle or cycle_result.portfolio_metrics.total_pnl_usdt > 0:
                        self.session.best_cycle = cycle_result.cycle_id
                    
                    if not self.session.worst_cycle or cycle_result.portfolio_metrics.total_pnl_usdt < 0:
                        self.session.worst_cycle = cycle_result.cycle_id
            
            self.logger.info(f"✅ Ciclo {cycle_result.cycle_id} procesado: {cycle_result.portfolio_metrics.total_pnl_usdt:+.2f} USDT")
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando resultados del ciclo: {e}")
    
    async def _send_telegram_updates(self, cycle_result: CycleData):
        """Envía updates a Telegram"""
        try:
            if not self.telegram_reporter:
                return
            
            # Enviar trades individuales
            for symbol, trades in cycle_result.agent_results.items():
                for trade in trades:
                    await self.telegram_reporter.send_individual_trade_alert(trade)
            
            # Enviar resumen del ciclo
            if cycle_result.portfolio_metrics:
                agent_summaries = self.metrics_aggregator.get_agent_summary(cycle_result.agent_results)
                await self.telegram_reporter.send_cycle_summary(
                    cycle_result.portfolio_metrics, 
                    agent_summaries
                )
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando updates a Telegram: {e}")
    
    async def _check_memory_usage(self) -> bool:
        """Verifica si el uso de memoria está dentro de límites"""
        try:
            memory_usage = self.memory_monitor.get_memory_usage()
            return memory_usage < self.config.max_memory_usage_mb
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando memoria: {e}")
            return True  # Continuar si hay error
    
    async def _force_memory_cleanup(self):
        """Fuerza limpieza de memoria"""
        try:
            self.logger.info("🧹 Forzando limpieza de memoria...")
            
            # Limpiar cache de ciclos antiguos
            if len(self.cycle_data_cache) > 50:
                # Mantener solo los últimos 50 ciclos
                old_cycles = sorted(self.cycle_data_cache.keys())[:-50]
                for cycle_id in old_cycles:
                    del self.cycle_data_cache[cycle_id]
            
            # Forzar garbage collection
            gc.collect()
            
            # Limpiar memoria de agentes
            for agent in self.active_agents.values():
                if hasattr(agent, 'cleanup_memory'):
                    agent.cleanup_memory()
            
            self.logger.info("✅ Limpieza de memoria completada")
            
        except Exception as e:
            self.logger.error(f"❌ Error en limpieza de memoria: {e}")
    
    async def _cleanup_cycle_data(self, cycle_id: int):
        """Limpia datos de un ciclo específico"""
        try:
            if cycle_id in self.cycle_data_cache:
                # Limpiar datos pesados del ciclo
                cycle_data = self.cycle_data_cache[cycle_id]
                cycle_data.market_data = {}  # Limpiar datos de mercado
                
            # Forzar garbage collection
            gc.collect()
            
        except Exception as e:
            self.logger.error(f"❌ Error limpiando datos del ciclo {cycle_id}: {e}")
    
    async def _create_checkpoint(self, cycle_id: int, cycle_results: List[CycleData]):
        """Crea checkpoint del entrenamiento"""
        try:
            checkpoint_data = {
                'session': self.session,
                'cycle_id': cycle_id,
                'cycle_results': cycle_results,
                'agent_states': {symbol: agent.get_state() for symbol, agent in self.active_agents.items()},
                'timestamp': datetime.now().isoformat()
            }
            
            checkpoint_file = self.checkpoint_dir / f"checkpoint_cycle_{cycle_id:04d}.pkl"
            
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            self.logger.info(f"✅ Checkpoint creado: {checkpoint_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Error creando checkpoint: {e}")
    
    async def _generate_final_report(self, cycle_results: List[CycleData]) -> Dict[str, Any]:
        """Genera reporte final del entrenamiento"""
        try:
            if not cycle_results:
                return {'error': 'No hay resultados para reportar'}
            
            # Calcular métricas finales
            total_cycles = len(cycle_results)
            total_trades = sum(len(trades) for result in cycle_results for trades in result.agent_results.values())
            total_pnl = sum(result.portfolio_metrics.total_pnl_usdt for result in cycle_results if result.portfolio_metrics)
            
            # Mejor y peor ciclo
            best_cycle = max(cycle_results, key=lambda x: x.portfolio_metrics.total_pnl_usdt if x.portfolio_metrics else 0)
            worst_cycle = min(cycle_results, key=lambda x: x.portfolio_metrics.total_pnl_usdt if x.portfolio_metrics else 0)
            
            # Métricas por agente
            agent_performance = {}
            for symbol in self.symbols:
                agent_trades = []
                for result in cycle_results:
                    agent_trades.extend(result.agent_results.get(symbol, []))
                
                if agent_trades:
                    agent_pnl = sum(trade.pnl_usdt for trade in agent_trades)
                    agent_trades_count = len(agent_trades)
                    agent_win_rate = sum(1 for trade in agent_trades if trade.was_successful) / agent_trades_count * 100
                    
                    agent_performance[symbol] = {
                        'total_pnl': agent_pnl,
                        'total_trades': agent_trades_count,
                        'win_rate': agent_win_rate,
                        'avg_quality': sum(trade.get_quality_score() for trade in agent_trades) / agent_trades_count
                    }
            
            report = {
                'session_id': self.session.session_id,
                'start_time': self.session.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_cycles': total_cycles,
                'total_trades': total_trades,
                'total_pnl_usdt': total_pnl,
                'best_cycle': {
                    'cycle_id': best_cycle.cycle_id,
                    'pnl': best_cycle.portfolio_metrics.total_pnl_usdt if best_cycle.portfolio_metrics else 0
                },
                'worst_cycle': {
                    'cycle_id': worst_cycle.cycle_id,
                    'pnl': worst_cycle.portfolio_metrics.total_pnl_usdt if worst_cycle.portfolio_metrics else 0
                },
                'agent_performance': agent_performance,
                'config': {
                    'days_back': self.config.days_back,
                    'cycle_size_hours': self.config.cycle_size_hours,
                    'max_concurrent_agents': self.config.max_concurrent_agents
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte final: {e}")
            return {'error': str(e)}
    
    async def _save_training_results(self, final_report: Dict[str, Any]):
        """Guarda resultados del entrenamiento"""
        try:
            # Guardar reporte final
            report_file = self.output_dir / f"{self.session.session_id}_final_report.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False, default=str)
            
            # Guardar métricas del agregador
            metrics_file = self.output_dir / f"{self.session.session_id}_metrics.json"
            self.metrics_aggregator.save_metrics_to_file(str(metrics_file))
            
            self.logger.info(f"✅ Resultados guardados: {report_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando resultados: {e}")
    
    async def _handle_training_error(self, error: Exception):
        """Maneja errores durante el entrenamiento"""
        try:
            self.logger.error(f"❌ Error crítico en entrenamiento: {error}")
            
            # Crear checkpoint de emergencia
            if self.session:
                await self._create_checkpoint(
                    self.session.completed_cycles, 
                    list(self.cycle_data_cache.values())
                )
            
            # Enviar alerta a Telegram si está disponible
            if self.telegram_reporter:
                await self.telegram_reporter.send_performance_alert(
                    "ERROR", 
                    f"Error crítico en entrenamiento: {str(error)}", 
                    "CRITICAL"
                )
            
        except Exception as e:
            self.logger.error(f"❌ Error manejando error de entrenamiento: {e}")

class MemoryMonitor:
    """Monitor de memoria para el pipeline"""
    
    def __init__(self, max_memory_mb: int):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
    
    def get_memory_usage(self) -> float:
        """Obtiene uso actual de memoria en MB"""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convertir a MB
        except Exception:
            return 0.0
    
    def is_memory_usage_high(self) -> bool:
        """Verifica si el uso de memoria es alto"""
        return self.get_memory_usage() > self.max_memory_mb * 0.8  # 80% del límite
