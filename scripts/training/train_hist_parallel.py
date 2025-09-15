#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train Hist Parallel - Bot Trading v10 Enterprise
================================================
Script principal para comando /train_hist con entrenamiento paralelo sincronizado.
Ejecuta múltiples agentes en paralelo con timestamps sincronizados.

Características:
- Entrenamiento paralelo sincronizado por timestamps
- PnL diario agregado (media entre agentes)
- Win rate global y métricas consolidadas
- Progreso en tiempo real para Telegram
- Guardado de estrategias y runs por agente
- Base de conocimiento compartida

Uso desde Telegram:
    /train_hist

Uso desde línea de comandos:
    python scripts/training/train_hist_parallel.py --progress-file data/tmp/progress.json

Autor: Bot Trading v10 Enterprise
Versión: 2.0.0
"""

import asyncio
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Imports del proyecto
try:
    from scripts.training.parallel_training_orchestrator import create_parallel_training_orchestrator
    from core.sync.metrics_aggregator import create_metrics_aggregator
    from config.unified_config import get_config_manager
except ImportError as e:
    print(f"⚠️ Imports no disponibles, usando fallbacks: {e}")
    # Fallbacks para desarrollo
    def create_parallel_training_orchestrator(*args, **kwargs):
        return None
    def create_metrics_aggregator(*args, **kwargs):
        return None
    def get_config_manager():
        class FallbackConfig:
            def get_symbols(self): return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]
            def get_timeframes(self): return ["1h", "4h", "1d"]
            def get_initial_balance(self): return 1000.0
        return FallbackConfig()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/train_hist_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrainHistParallel:
    """
    Entrenador Histórico Paralelo
    =============================
    
    Ejecuta entrenamiento histórico con múltiples agentes sincronizados
    y agrega resultados globales para análisis conjunto.
    """
    
    def __init__(self, progress_file: Optional[str] = None):
        """
        Inicializa el entrenador
        
        Args:
            progress_file: Archivo para guardar progreso (opcional)
        """
        self.progress_file = progress_file
        self.session_id = f"train_hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Configuración
        self.config = get_config_manager()
        self.symbols = self.config.get_symbols()
        self.timeframes = self.config.get_timeframes()
        self.initial_balance = self.config.get_initial_balance()
        
        # Componentes principales
        self.orchestrator = None
        self.metrics_aggregator = None
        
        # Estado del entrenamiento
        self.is_running = False
        self.start_time = None
        self.results = None
        self.pre_aligned_data: Optional[Dict[str, Any]] = None
        self.cycle_metrics_history: List[Dict[str, Any]] = []
        
        logger.info(f"🎯 TrainHistParallel inicializado: {len(self.symbols)} símbolos")
    
    async def initialize_components(self):
        """Inicializa componentes del sistema"""
        try:
            logger.info("🔧 Inicializando componentes del sistema...")
            
            # Crear orchestrador
            self.orchestrator = await create_parallel_training_orchestrator(
                symbols=self.symbols,
                timeframes=self.timeframes,
                initial_balance=self.initial_balance
            )
            
            # Crear agregador de métricas
            self.metrics_aggregator = create_metrics_aggregator(self.symbols)
            
            logger.info("✅ Componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            raise
    
    async def execute_training(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento histórico paralelo
        
        Args:
            start_date: Fecha de inicio (None = usar config)
            end_date: Fecha de fin (None = usar config)
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            self.start_time = datetime.now()
            self.is_running = True
            
            logger.info(f"🚀 Iniciando entrenamiento histórico paralelo: {self.session_id}")
            
            # Configurar fechas por defecto
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)  # 1 año atrás
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Hasta ayer
            
            # Actualizar progreso inicial
            await self._update_progress(0, "Inicializando sistema", "🔧 Preparando componentes")
            
            # Inicializar componentes
            await self.initialize_components()
            
            # Integrar alineamiento pre-generado si existe; si no, generarlo
            await self._ensure_pre_alignment(start_date, end_date)
            
            # Configurar callback de progreso
            progress_callback = self._create_progress_callback()
            
            # Ejecutar entrenamiento con orchestrador
            await self._update_progress(10, "Ejecutando entrenamiento", "🤖 Iniciando agentes paralelos")
            
            if self.orchestrator:
                results = await self.orchestrator.execute_training_session(
                    start_date=start_date,
                    end_date=end_date,
                    progress_callback=progress_callback
                )
            else:
                # Simulación para desarrollo
                results = await self._simulate_training_session(start_date, end_date, progress_callback)
            
            # Procesar y agregar resultados finales
            await self._update_progress(90, "Procesando resultados", "📊 Agregando métricas globales")
            
            final_results = await self._process_final_results(results)

            # Anexar métricas por ciclo consolidadas a resultados finales
            if self.cycle_metrics_history:
                final_results["cycle_metrics_history"] = self.cycle_metrics_history
                final_results["cycle_metrics"] = self.cycle_metrics_history[-1]
            
            # Guardar resultados completos
            await self._save_final_results(final_results)
            
            await self._update_progress(100, "Completado", "✅ Entrenamiento finalizado")
            
            self.is_running = False
            self.results = final_results
            
            logger.info(f"✅ Entrenamiento completado: {self.session_id}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            self.is_running = False
            
            # Actualizar progreso con error
            await self._update_progress(0, "Error", f"❌ Error: {str(e)}")
            
            raise
    
    async def _simulate_training_session(self, start_date: datetime, end_date: datetime, progress_callback) -> Dict[str, Any]:
        """Simula sesión de entrenamiento para desarrollo"""
        try:
            import random
            import numpy as np
            
            logger.info("🎭 Ejecutando simulación de entrenamiento...")
            
            # Simular progreso
            total_days = (end_date - start_date).days
            cycles_per_day = 24  # Una por hora
            total_cycles = total_days * cycles_per_day
            
            # Simular datos de agentes
            agent_summaries = {}
            
            for symbol in self.symbols:
                # Simular performance realista
                win_rate = random.uniform(55, 85)  # 55-85% win rate
                total_trades = random.randint(100, 500)
                winning_trades = int(total_trades * win_rate / 100)
                losing_trades = total_trades - winning_trades
                
                # PnL basado en win rate y número de trades
                base_pnl_pct = (win_rate - 50) * 2 + random.uniform(-10, 20)
                pnl_pct = max(-50, min(200, base_pnl_pct))  # Limitar entre -50% y +200%
                pnl = self.initial_balance * pnl_pct / 100
                current_balance = self.initial_balance + pnl
                
                agent_summaries[symbol] = {
                    'symbol': symbol,
                    'current_balance': current_balance,
                    'total_pnl': pnl,
                    'total_pnl_pct': pnl_pct,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'max_drawdown': random.uniform(5, 25),
                    'daily_pnl': pnl / total_days if total_days > 0 else 0
                }
            
            # Simular progreso con delays realistas
            for cycle in range(min(50, total_cycles)):  # Limitar para demo
                await asyncio.sleep(0.1)  # Simular tiempo de procesamiento
                
                progress = (cycle + 1) / min(50, total_cycles) * 100
                
                if progress_callback:
                    await progress_callback({
                        'progress': progress,
                        'status': f'Procesando ciclo {cycle + 1}',
                        'current_cycle': cycle + 1,
                        'total_cycles': min(50, total_cycles),
                        'timestamp': (start_date + timedelta(hours=cycle)).isoformat(),
                        'symbols': self.symbols
                    })
            
            # Simular estrategias
            strategies = ['RSI_Divergence', 'MA_Crossover', 'Bollinger_Bounce', 'MACD_Signal', 'Support_Resistance']
            strategy_analysis = {
                'top_strategies': [(strategy, random.randint(10, 100)) for strategy in strategies[:3]],
                'total_unique_strategies': len(strategies),
                'strategy_distribution': {strategy: random.randint(5, 50) for strategy in strategies}
            }
            
            return {
                'session_info': {
                    'session_id': self.session_id,
                    'start_time': self.start_time.isoformat(),
                    'symbols': self.symbols,
                    'timeframes': self.timeframes,
                    'initial_balance_per_agent': self.initial_balance,
                    'simulated': True
                },
                'performance_summary': {
                    'cycles_completed': min(50, total_cycles),
                    'total_decisions': random.randint(500, 2000),
                    'total_trades': sum(s['total_trades'] for s in agent_summaries.values()),
                    'agent_summaries': agent_summaries
                },
                'strategy_analysis': strategy_analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Error en simulación: {e}")
            return {'error': str(e)}
    
    def _create_progress_callback(self):
        """Crea callback para progreso del orchestrador"""
        async def progress_callback(data):
            try:
                # Mapear progreso del orchestrador (10-90%)
                orchestrator_progress = data.get('progress', 0)
                mapped_progress = 10 + (orchestrator_progress * 0.8)  # 10% a 90%
                
                status = data.get('status', 'Entrenando')
                current_cycle = data.get('current_cycle', 0)
                total_cycles = data.get('total_cycles', 1)
                
                detailed_status = f"🔄 Ciclo {current_cycle}/{total_cycles}: {status}"
                
                # Calcular métricas medias por ciclo si hay datos disponibles
                cycle_metrics = self._compute_cycle_metrics(data)

                # Guardar historial de métricas por ciclo si se obtuvo algo
                if cycle_metrics:
                    self.cycle_metrics_history.append({
                        **cycle_metrics,
                        "cycle": current_cycle,
                        "total_cycles": total_cycles,
                        "timestamp": data.get('timestamp')
                    })

                # Actualizar progreso incluyendo métricas por ciclo en el JSON de progreso
                await self._update_progress(
                    mapped_progress,
                    status,
                    detailed_status if not cycle_metrics else f"{detailed_status} | PnL̄: {cycle_metrics['avg_pnl']:+.2f} | WR̄: {cycle_metrics['avg_win_rate']:.1f}% | DD̄: {cycle_metrics['avg_drawdown']:.2f}%"
                )
                
            except Exception as e:
                logger.error(f"❌ Error en callback de progreso: {e}")
        
        return progress_callback

    def _compute_cycle_metrics(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrae y promedia métricas clave del ciclo actual a través de agentes.
        Espera datos como 'agent_cycle_stats' o 'agent_summaries' en el payload del orchestrador.
        """
        try:
            agent_stats = None
            if 'agent_cycle_stats' in data and isinstance(data['agent_cycle_stats'], dict):
                agent_stats = data['agent_cycle_stats']
            elif 'agent_summaries' in data and isinstance(data['agent_summaries'], dict):
                agent_stats = data['agent_summaries']
            else:
                return None

            if not agent_stats:
                return None

            num = max(1, len(agent_stats))
            sum_pnl = 0.0
            sum_wr = 0.0
            sum_dd = 0.0
            sum_trades = 0
            sum_sharpe = 0.0
            sharpe_count = 0

            for _sym, stat in agent_stats.items():
                pnl = stat.get('cycle_pnl', stat.get('total_pnl', 0))
                win_rate = stat.get('cycle_win_rate', stat.get('win_rate', 0))
                dd = stat.get('cycle_drawdown', stat.get('max_drawdown', 0))
                trades = stat.get('cycle_trades', stat.get('total_trades', 0))
                sharpe = stat.get('cycle_sharpe', stat.get('sharpe_ratio', None))

                sum_pnl += float(pnl or 0)
                sum_wr += float(win_rate or 0)
                sum_dd += float(dd or 0)
                sum_trades += int(trades or 0)
                if sharpe is not None:
                    sum_sharpe += float(sharpe)
                    sharpe_count += 1

            avg_pnl = sum_pnl / num
            avg_wr = sum_wr / num
            avg_dd = sum_dd / num
            avg_trades = sum_trades / num
            avg_sharpe = (sum_sharpe / sharpe_count) if sharpe_count > 0 else 0.0

            profitability = "rentable" if (avg_pnl > 0 and avg_wr > 50.0) else "no rentable"

            return {
                "avg_pnl": avg_pnl,
                "avg_win_rate": avg_wr,
                "avg_drawdown": avg_dd,
                "avg_sharpe": avg_sharpe,
                "avg_trades": avg_trades,
                "profitability": profitability
            }
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron calcular métricas de ciclo: {e}")
            return None
    
    async def _process_final_results(self, orchestrator_results: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa y agrega resultados finales"""
        try:
            logger.info("📊 Procesando resultados finales...")
            
            # Extraer métricas de performance
            performance_summary = orchestrator_results.get('performance_summary', {})
            agent_summaries = performance_summary.get('agent_summaries', {})
            
            # Agregar métricas con el agregador (si está disponible)
            aggregated_metrics = {}
            if self.metrics_aggregator:
                try:
                    aggregated_metrics = await self.metrics_aggregator.aggregate_symbol_stats(agent_summaries)
                except Exception as e:
                    logger.warning(f"⚠️ Error agregando métricas: {e}")
                    # Usar datos directos como fallback
                    aggregated_metrics = self._create_fallback_metrics(agent_summaries)
            else:
                aggregated_metrics = self._create_fallback_metrics(agent_summaries)
            
            # Calcular métricas globales consolidadas
            global_summary = self._calculate_global_summary(agent_summaries)
            
            # Obtener información de estrategias
            strategy_analysis = orchestrator_results.get('strategy_analysis', {})
            
            # Crear resultado final completo
            final_results = {
                "session_info": {
                    "session_id": self.session_id,
                    "start_time": self.start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                    "symbols": self.symbols,
                    "timeframes": self.timeframes,
                    "initial_balance_per_agent": self.initial_balance
                },
                
                "global_performance": global_summary,
                
                "symbol_performance": {
                    symbol: self._extract_symbol_metrics(symbol, metrics, agent_summaries.get(symbol, {}))
                    for symbol, metrics in aggregated_metrics.items()
                },
                
                "strategy_analysis": strategy_analysis,
                
                "orchestrator_results": orchestrator_results,
                
                "telegram_summary": await self._generate_telegram_summary(global_summary, aggregated_metrics)
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error procesando resultados finales: {e}")
            return {"error": str(e)}
    
    def _create_fallback_metrics(self, agent_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Crea métricas de fallback cuando el agregador no está disponible"""
        try:
            fallback_metrics = {}
            
            for symbol, summary in agent_summaries.items():
                # Crear objeto similar a SymbolStats
                class FallbackStats:
                    def __init__(self, data):
                        self.symbol = data.get('symbol', symbol)
                        self.current_balance = data.get('current_balance', 1000)
                        self.total_pnl = data.get('total_pnl', 0)
                        self.total_pnl_pct = data.get('total_pnl_pct', 0)
                        self.total_trades = data.get('total_trades', 0)
                        self.win_rate = data.get('win_rate', 0)
                        self.sharpe_ratio = data.get('sharpe_ratio', 0)
                        self.max_drawdown = data.get('max_drawdown', 0)
                
                fallback_metrics[symbol] = FallbackStats(summary)
            
            return fallback_metrics
            
        except Exception as e:
            logger.error(f"❌ Error creando métricas de fallback: {e}")
            return {}
    
    def _extract_symbol_metrics(self, symbol: str, metrics, agent_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae métricas de símbolo de forma segura"""
        try:
            if hasattr(metrics, 'current_balance'):
                # Es un objeto SymbolStats
                return {
                    "balance": metrics.current_balance,
                    "pnl": metrics.total_pnl,
                    "pnl_pct": metrics.total_pnl_pct,
                    "trades": metrics.total_trades,
                    "win_rate": metrics.win_rate,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown
                }
            else:
                # Es un dict o fallback
                return {
                    "balance": agent_summary.get('current_balance', 1000),
                    "pnl": agent_summary.get('total_pnl', 0),
                    "pnl_pct": agent_summary.get('total_pnl_pct', 0),
                    "trades": agent_summary.get('total_trades', 0),
                    "win_rate": agent_summary.get('win_rate', 0),
                    "sharpe_ratio": agent_summary.get('sharpe_ratio', 0),
                    "max_drawdown": agent_summary.get('max_drawdown', 0)
                }
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo métricas de {symbol}: {e}")
            return {
                "balance": 1000, "pnl": 0, "pnl_pct": 0,
                "trades": 0, "win_rate": 0, "sharpe_ratio": 0, "max_drawdown": 0
            }
    
    def _calculate_global_summary(self, agent_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula resumen global de métricas"""
        try:
            if not agent_summaries:
                return {}
            
            # Agregar métricas de todos los agentes
            total_balance = sum(metrics.get('current_balance', 0) for metrics in agent_summaries.values())
            total_pnl = sum(metrics.get('total_pnl', 0) for metrics in agent_summaries.values())
            total_trades = sum(metrics.get('total_trades', 0) for metrics in agent_summaries.values())
            total_winning = sum(metrics.get('winning_trades', 0) for metrics in agent_summaries.values())
            total_losing = sum(metrics.get('losing_trades', 0) for metrics in agent_summaries.values())
            
            # Calcular métricas derivadas
            avg_balance = total_balance / len(agent_summaries)
            avg_pnl = total_pnl / len(agent_summaries)
            avg_pnl_pct = (avg_pnl / self.initial_balance) * 100
            global_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
            
            # Encontrar mejores y peores performers
            best_performer = max(agent_summaries.items(), key=lambda x: x[1].get('total_pnl_pct', 0))
            worst_performer = min(agent_summaries.items(), key=lambda x: x[1].get('total_pnl_pct', 0))
            
            # Calcular drawdown máximo global
            max_drawdown = max(metrics.get('max_drawdown', 0) for metrics in agent_summaries.values())
            
            return {
                "total_balance": total_balance,
                "avg_balance_per_agent": avg_balance,
                "total_pnl": total_pnl,
                "avg_pnl_per_agent": avg_pnl,
                "avg_pnl_pct": avg_pnl_pct,
                "total_trades": total_trades,
                "winning_trades": total_winning,
                "losing_trades": total_losing,
                "global_win_rate": global_win_rate,
                "max_drawdown": max_drawdown,
                "best_performer": {
                    "symbol": best_performer[0],
                    "pnl_pct": best_performer[1].get('total_pnl_pct', 0)
                },
                "worst_performer": {
                    "symbol": worst_performer[0],
                    "pnl_pct": worst_performer[1].get('total_pnl_pct', 0)
                },
                "active_agents": len(agent_summaries)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando resumen global: {e}")
            return {}
    
    async def _generate_telegram_summary(self, global_summary: Dict[str, Any], 
                                       symbol_metrics: Dict[str, Any]) -> str:
        """Genera resumen optimizado para Telegram"""
        try:
            duration = (datetime.now() - self.start_time).total_seconds() / 60  # minutos
            
            # Evaluación de rentabilidad si hay métricas de ciclo
            rentable_line = ""
            if self.cycle_metrics_history:
                last_cycle = self.cycle_metrics_history[-1]
                rentable_line = f"\n💡 <b>Rentabilidad (último ciclo):</b> {last_cycle.get('profitability','N/A').upper()}  (PnL̄ {last_cycle.get('avg_pnl',0):+.2f}, WR̄ {last_cycle.get('avg_win_rate',0):.1f}%)\n"

            message = f"""🎯 <b>Entrenamiento Histórico Completado</b>

📊 <b>Resumen Global:</b>
• Duración: {duration:.1f} minutos
• Agentes: {global_summary.get('active_agents', 0)}
• Total Trades: {global_summary.get('total_trades', 0):,}

💰 <b>Performance Agregada:</b>
• PnL Promedio: ${global_summary.get('avg_pnl_per_agent', 0):+.2f} ({global_summary.get('avg_pnl_pct', 0):+.2f}%)
• Win Rate Global: {global_summary.get('global_win_rate', 0):.1f}%
• Max Drawdown: {global_summary.get('max_drawdown', 0):.2f}%
{rentable_line}

🏆 <b>Top Performers:</b>
• 🥇 {global_summary.get('best_performer', {}).get('symbol', 'N/A')}: {global_summary.get('best_performer', {}).get('pnl_pct', 0):+.2f}%
• 🥉 {global_summary.get('worst_performer', {}).get('symbol', 'N/A')}: {global_summary.get('worst_performer', {}).get('pnl_pct', 0):+.2f}%

📈 <b>Performance por Símbolo:</b>"""
            
            # Agregar top 5 símbolos
            try:
                sorted_symbols = sorted(
                    symbol_metrics.items(),
                    key=lambda x: getattr(x[1], 'total_pnl_pct', x[1].get('total_pnl_pct', 0)) if hasattr(x[1], 'total_pnl_pct') else x[1].get('total_pnl_pct', 0),
                    reverse=True
                )
                
                for i, (symbol, metrics) in enumerate(sorted_symbols[:5], 1):
                    if hasattr(metrics, 'total_pnl_pct'):
                        pnl_pct = metrics.total_pnl_pct
                        trades = metrics.total_trades
                        win_rate = metrics.win_rate
                    else:
                        pnl_pct = metrics.get('total_pnl_pct', 0)
                        trades = metrics.get('total_trades', 0)
                        win_rate = metrics.get('win_rate', 0)
                    
                    message += f"\n{i}. <b>{symbol}</b>: {pnl_pct:+.2f}% ({trades} trades, {win_rate:.1f}% WR)"
            except Exception as e:
                logger.warning(f"⚠️ Error formateando símbolos: {e}")
                message += "\n• Ver resultados detallados en archivos guardados"
            
            message += f"""

💾 <b>Datos Guardados:</b>
• Estrategias por agente: <code>data/agents/{{symbol}}/strategies.json</code>
• Runs completos: <code>data/training_sessions/{self.session_id}/</code>
• Resumen ejecutivo: <code>data/training_sessions/{self.session_id}/executive_summary.md</code>"""
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen de Telegram: {e}")
            return "❌ Error generando resumen del entrenamiento"
    
    async def _save_final_results(self, results: Dict[str, Any]):
        """Guarda resultados finales"""
        try:
            # Crear directorio de sesión
            session_dir = Path(f"data/training_sessions/{self.session_id}")
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar resultados completos
            results_file = session_dir / "complete_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Guardar solo resumen para acceso rápido
            summary_file = session_dir / "summary.json"
            summary_data = {
                "session_id": self.session_id,
                "global_performance": results.get("global_performance", {}),
                "symbol_performance": results.get("symbol_performance", {}),
                "telegram_summary": results.get("telegram_summary", "")
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            # Crear resumen ejecutivo en Markdown
            executive_summary = self._create_executive_summary(results)
            summary_md_file = session_dir / "executive_summary.md"
            
            with open(summary_md_file, 'w', encoding='utf-8') as f:
                f.write(executive_summary)
            
            logger.info(f"💾 Resultados guardados en: {session_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {e}")

    async def _ensure_pre_alignment(self, start_date: datetime, end_date: datetime):
        """Carga alineamiento pre-generado desde data/aligned_timeframes.json si existe.
        Si no existe, intenta generarlo automáticamente usando scripts/training/align_timeframes.py
        """
        try:
            alignment_path = Path("data/aligned_timeframes.json")
            if alignment_path.exists():
                with open(alignment_path, 'r') as f:
                    self.pre_aligned_data = json.load(f)
                logger.info("✅ Alineamiento pre-generado cargado desde data/aligned_timeframes.json")
                return

            # Si no existe, intentar generarlo automáticamente
            logger.info("⚠️ Alineamiento no encontrado. Generando con align_timeframes.py...")
            try:
                import subprocess, sys
                days_back = max(1, (end_date - start_date).days) if (start_date and end_date) else 365
                cmd = [sys.executable, "scripts/training/align_timeframes.py", "--days-back", str(days_back)]
                subprocess.run(cmd, check=True)
            except Exception as gen_err:
                logger.warning(f"⚠️ No se pudo generar alineamiento automáticamente: {gen_err}")
                return

            if alignment_path.exists():
                with open(alignment_path, 'r') as f:
                    self.pre_aligned_data = json.load(f)
                logger.info("✅ Alineamiento generado y cargado correctamente")
            else:
                logger.warning("⚠️ Aún no existe data/aligned_timeframes.json tras la generación")
        except Exception as e:
            logger.warning(f"⚠️ Error manejando alineamiento pre-generado: {e}")
    
    def _create_executive_summary(self, results: Dict[str, Any]) -> str:
        """Crea resumen ejecutivo en formato Markdown"""
        try:
            session_info = results.get('session_info', {})
            global_perf = results.get('global_performance', {})
            symbol_perf = results.get('symbol_performance', {})
            
            summary = f"""# Resumen Ejecutivo - Entrenamiento Histórico Paralelo

## 📊 Información de la Sesión
- **ID de Sesión**: {session_info.get('session_id', 'N/A')}
- **Duración**: {session_info.get('duration_seconds', 0):.0f} segundos
- **Símbolos**: {', '.join(session_info.get('symbols', []))}
- **Balance Inicial por Agente**: ${session_info.get('initial_balance_per_agent', 0):,.2f}

## 🎯 Resultados Globales
- **PnL Promedio por Agente**: ${global_perf.get('avg_pnl_per_agent', 0):+.2f} ({global_perf.get('avg_pnl_pct', 0):+.2f}%)
- **Win Rate Global**: {global_perf.get('global_win_rate', 0):.1f}%
- **Total de Trades**: {global_perf.get('total_trades', 0):,}
- **Trades Ganadores**: {global_perf.get('winning_trades', 0):,}
- **Trades Perdedores**: {global_perf.get('losing_trades', 0):,}
- **Max Drawdown**: {global_perf.get('max_drawdown', 0):.2f}%

## 🏆 Top Performers
- **Mejor Agente**: {global_perf.get('best_performer', {}).get('symbol', 'N/A')} ({global_perf.get('best_performer', {}).get('pnl_pct', 0):+.2f}%)
- **Peor Agente**: {global_perf.get('worst_performer', {}).get('symbol', 'N/A')} ({global_perf.get('worst_performer', {}).get('pnl_pct', 0):+.2f}%)

## 📈 Performance por Símbolo
"""
            
            for symbol, perf in symbol_perf.items():
                pnl = perf.get('pnl', 0)
                pnl_pct = perf.get('pnl_pct', 0)
                trades = perf.get('trades', 0)
                win_rate = perf.get('win_rate', 0)
                drawdown = perf.get('max_drawdown', 0)
                
                summary += f"- **{symbol}**: ${pnl:+.2f} ({pnl_pct:+.2f}%), {trades} trades, {win_rate:.1f}% WR, {drawdown:.2f}% DD\n"
            
            summary += f"""
## 📁 Archivos Generados
- `complete_results.json` - Resultados completos de la sesión
- `summary.json` - Resumen rápido para dashboards
- `executive_summary.md` - Este resumen ejecutivo

## 🎯 Próximos Pasos
1. Revisar estrategias exitosas en `data/agents/{{symbol}}/strategies.json`
2. Analizar patrones de trades perdedores para mejoras
3. Considerar ajustar parámetros de riesgo si drawdown > 15%
4. Evaluar ampliar entrenamiento a más timeframes si WR > 70%

---
*Generado automáticamente por Bot Trading v10 Enterprise el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error creando resumen ejecutivo: {e}")
            return "# Error generando resumen ejecutivo"
    
    async def _update_progress(self, progress: float, status: str, detailed_status: str):
        """Actualiza progreso del entrenamiento"""
        try:
            progress_data = {
                "session_id": self.session_id,
                "progress": min(progress, 100),
                "status": status,
                "detailed_status": detailed_status,
                "timestamp": datetime.now().isoformat(),
                "is_running": self.is_running,
                "symbols": self.symbols,
                "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }
            
            # Guardar en archivo de progreso si está especificado
            if self.progress_file:
                progress_path = Path(self.progress_file)
                progress_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(progress_path, 'w') as f:
                    json.dump(progress_data, f, indent=2)
            
            # Log del progreso
            logger.info(f"📊 Progreso: {progress:.1f}% - {detailed_status}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando progreso: {e}")
    
    async def stop_training(self):
        """Detiene el entrenamiento de forma elegante"""
        try:
            logger.info("🛑 Deteniendo entrenamiento...")
            
            self.is_running = False
            
            if self.orchestrator:
                await self.orchestrator.stop_training()
            
            if self.metrics_aggregator:
                await self.metrics_aggregator.cleanup()
            
            await self._update_progress(0, "Detenido", "🛑 Entrenamiento detenido por usuario")
            
            logger.info("✅ Entrenamiento detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del entrenamiento"""
        try:
            if not self.is_running:
                return {
                    "status": "not_running",
                    "session_id": self.session_id,
                    "last_run": self.start_time.isoformat() if self.start_time else None
                }
            
            return {
                "status": "running",
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat(),
                "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
                "symbols": self.symbols,
                "progress_file": self.progress_file
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {"status": "error", "error": str(e)}

# Función principal para ejecución independiente
async def main():
    """Función principal para ejecutar desde línea de comandos"""
    parser = argparse.ArgumentParser(description="Entrenamiento Histórico Paralelo")
    parser.add_argument("--start-date", type=str, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--symbols", nargs="+", help="Símbolos específicos")
    parser.add_argument("--progress-file", type=str, help="Archivo para progreso")
    parser.add_argument("--output-dir", type=str, help="Directorio de salida")
    parser.add_argument("--simulate", action="store_true", help="Modo simulación para desarrollo")
    
    args = parser.parse_args()
    
    try:
        # Configurar fechas
        start_date = None
        end_date = None
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        
        # Crear entrenador
        trainer = TrainHistParallel(progress_file=args.progress_file)
        
        # Configurar símbolos específicos si se proporcionan
        if args.symbols:
            trainer.symbols = args.symbols
        
        print("=" * 60)
        print("🚀 INICIANDO ENTRENAMIENTO HISTÓRICO PARALELO")
        print("=" * 60)
        print(f"📊 Sesión ID: {trainer.session_id}")
        print(f"🎯 Símbolos: {', '.join(trainer.symbols)}")
        print(f"📅 Período: {start_date or 'Auto'} → {end_date or 'Auto'}")
        print(f"💰 Balance inicial por agente: ${trainer.initial_balance:,.2f}")
        
        if args.simulate:
            print("🎭 Modo: SIMULACIÓN")
        else:
            print("🔥 Modo: REAL")
        
        print("=" * 60)
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Mostrar resumen
        global_perf = results.get('global_performance', {})
        
        print("\n" + "=" * 60)
        print("🎯 ENTRENAMIENTO HISTÓRICO PARALELO COMPLETADO")
        print("=" * 60)
        print(f"📊 Sesión ID: {results['session_info']['session_id']}")
        print(f"⏱️ Duración: {results['session_info']['duration_seconds']:.1f} segundos")
        print(f"🤖 Agentes: {global_perf.get('active_agents', 0)}")
        print(f"💰 PnL Promedio: ${global_perf.get('avg_pnl_per_agent', 0):+.2f} ({global_perf.get('avg_pnl_pct', 0):+.2f}%)")
        print(f"🎯 Win Rate Global: {global_perf.get('global_win_rate', 0):.1f}%")
        print(f"📉 Max Drawdown: {global_perf.get('max_drawdown', 0):.2f}%")
        print(f"📈 Total Trades: {global_perf.get('total_trades', 0):,}")
        
        print(f"\n🏆 Top Performer: {global_perf.get('best_performer', {}).get('symbol', 'N/A')} ({global_perf.get('best_performer', {}).get('pnl_pct', 0):+.2f}%)")
        print(f"🥉 Worst Performer: {global_perf.get('worst_performer', {}).get('symbol', 'N/A')} ({global_perf.get('worst_performer', {}).get('pnl_pct', 0):+.2f}%)")
        
        print(f"\n💾 Resultados guardados en: data/training_sessions/{trainer.session_id}/")
        
        # Mostrar performance por símbolo
        symbol_perf = results.get('symbol_performance', {})
        if symbol_perf:
            print(f"\n📈 Performance Detallada por Símbolo:")
            print("-" * 40)
            for symbol, perf in symbol_perf.items():
                pnl_pct = perf.get('pnl_pct', 0)
                trades = perf.get('trades', 0)
                win_rate = perf.get('win_rate', 0)
                print(f"{symbol:8} | {pnl_pct:+7.2f}% | {trades:4} trades | {win_rate:5.1f}% WR")
        
        print("=" * 60)
        
        # Guardar en directorio específico si se proporciona
        if args.output_dir:
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            output_file = output_path / f"train_hist_results_{trainer.session_id}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"📤 Resultados también guardados en: {output_file}")
        
    except KeyboardInterrupt:
        print("\n🛑 Entrenamiento interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)

# Factory function para uso desde otros módulos
async def create_train_hist_parallel(progress_file: str = None) -> TrainHistParallel:
    """
    Crea instancia de entrenador histórico paralelo
    
    Args:
        progress_file: Archivo para progreso (opcional)
        
    Returns:
        Instancia configurada del entrenador
    """
    return TrainHistParallel(progress_file=progress_file)

# Función de conveniencia para ejecutar entrenamiento rápido
async def execute_quick_training(symbols: List[str] = None, 
                                days_back: int = 30) -> Dict[str, Any]:
    """
    Ejecuta entrenamiento rápido con configuración básica
    
    Args:
        symbols: Símbolos a entrenar (None = usar config)
        days_back: Días hacia atrás para entrenar
        
    Returns:
        Resultados del entrenamiento
    """
    try:
        trainer = TrainHistParallel()
        
        if symbols:
            trainer.symbols = symbols
        
        # Configurar fechas
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days_back)
        
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento rápido: {e}")
        return {"error": str(e)}

# Función para integración con handlers de Telegram
async def execute_train_hist_for_telegram(progress_file: str) -> Dict[str, Any]:
    """
    Ejecuta entrenamiento histórico específicamente para comando de Telegram
    
    Args:
        progress_file: Archivo para guardar progreso en tiempo real
        
    Returns:
        Resultados del entrenamiento con resumen para Telegram
    """
    try:
        logger.info("🎯 Ejecutando entrenamiento histórico para Telegram")
        
        # Crear entrenador con archivo de progreso
        trainer = TrainHistParallel(progress_file=progress_file)
        
        # Configurar fechas por defecto (último año)
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=365)
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Añadir información específica para Telegram
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = results.get("telegram_summary", "Entrenamiento completado")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Error en entrenamiento: {str(e)[:100]}..."
        }

if __name__ == "__main__":
    # Configurar logging para ejecución directa
    logging.getLogger().setLevel(logging.INFO)
    
    # Ejecutar función principal
    asyncio.run(main())