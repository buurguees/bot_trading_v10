#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/training/train_hist_enhanced.py
======================================
Script Principal de Entrenamiento Histórico Mejorado

Integra todos los componentes mejorados:
- DetailedTradeMetric para tracking granular
- EnhancedMetricsAggregator para análisis de portfolio
- TelegramTradeReporter para reporting completo
- OptimizedTrainingPipeline para gestión de memoria
- EnhancedTradingAgent para tracking detallado

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agents.enhanced_trading_agent import EnhancedTradingAgent
from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
from scripts.training.optimized_training_pipeline import OptimizedTrainingPipeline, TrainingConfig
from config.unified_config import get_config_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/train_hist_enhanced.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnhancedTrainingOrchestrator:
    """
    Orquestador Mejorado de Entrenamiento Histórico
    ===============================================
    
    Integra todos los componentes mejorados para proporcionar:
    - Entrenamiento paralelo sincronizado
    - Tracking granular de cada trade
    - Reporting completo vía Telegram
    - Análisis de portfolio avanzado
    - Gestión de memoria optimizada
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Inicializa el orquestador mejorado
        
        Args:
            config: Configuración del entrenamiento
        """
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Componentes principales
        self.config_manager = get_config_manager()
        self.pipeline = OptimizedTrainingPipeline(self.config)
        self.metrics_aggregator = EnhancedMetricsAggregator()
        self.telegram_reporter = None
        
        # Estado del entrenamiento
        self.session_id = f"enhanced_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.is_running = False
        self.start_time = None
        
        # Estadísticas
        self.total_cycles = 0
        self.completed_cycles = 0
        self.total_trades = 0
        self.total_pnl = 0.0
        
        self.logger.info(f"✅ EnhancedTrainingOrchestrator inicializado: {self.session_id}")
    
    async def initialize(self) -> bool:
        """Inicializa todos los componentes"""
        try:
            # Inicializar pipeline
            if not await self.pipeline.initialize():
                self.logger.error("❌ Error inicializando pipeline")
                return False
            
            # Inicializar Telegram si está habilitado
            if self.config.telegram_enabled:
                await self._initialize_telegram()
            
            # Crear agentes mejorados
            await self._create_enhanced_agents()
            
            self.logger.info("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando orquestador: {e}")
            return False
    
    async def _initialize_telegram(self):
        """Inicializa el reporter de Telegram"""
        try:
            # TODO: Cargar configuración real de Telegram desde config
            telegram_config = TelegramConfig(
                bot_token="YOUR_BOT_TOKEN",  # Debería venir de config
                chat_id="YOUR_CHAT_ID",     # Debería venir de config
                enable_individual_trades=True,
                enable_cycle_summaries=True,
                enable_alerts=True
            )
            
            self.telegram_reporter = TelegramTradeReporter(telegram_config)
            self.logger.info("✅ Telegram reporter inicializado")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando Telegram: {e}")
            self.telegram_reporter = None
    
    async def _create_enhanced_agents(self):
        """Crea agentes mejorados para cada símbolo"""
        try:
            symbols = self.config_manager.get_symbols()
            
            for symbol in symbols:
                agent = EnhancedTradingAgent(symbol, initial_balance=1000.0)
                self.pipeline.active_agents[symbol] = agent
                self.logger.info(f"🤖 Agente mejorado {symbol} creado")
            
            self.logger.info(f"✅ {len(symbols)} agentes mejorados creados")
            
        except Exception as e:
            self.logger.error(f"❌ Error creando agentes mejorados: {e}")
            raise
    
    async def execute_enhanced_training(self) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento mejorado completo
        
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            if not self.is_running:
                await self.start_training()
            
            self.logger.info(f"🚀 Iniciando entrenamiento mejorado: {self.config.days_back} días")
            
            # Ejecutar pipeline optimizado
            results = await self.pipeline.execute_multi_day_training()
            
            # Procesar resultados finales
            final_report = await self._process_final_results(results)
            
            # Enviar resumen final a Telegram
            if self.telegram_reporter:
                await self._send_final_summary(final_report)
            
            self.logger.info("✅ Entrenamiento mejorado completado")
            return final_report
            
        except Exception as e:
            self.logger.error(f"❌ Error en entrenamiento mejorado: {e}")
            await self._handle_training_error(e)
            return {'error': str(e)}
    
    async def start_training(self):
        """Inicia el entrenamiento"""
        self.is_running = True
        self.start_time = datetime.now()
        
        # Enviar notificación de inicio
        if self.telegram_reporter:
            await self.telegram_reporter.send_performance_alert(
                "TRAINING_START",
                f"🚀 Entrenamiento mejorado iniciado\n📊 Período: {self.config.days_back} días\n🤖 Agentes: {len(self.pipeline.active_agents)}",
                "INFO"
            )
    
    async def stop_training(self):
        """Detiene el entrenamiento de forma elegante"""
        try:
            self.is_running = False
            
            # Enviar notificación de parada
            if self.telegram_reporter:
                duration = datetime.now() - self.start_time if self.start_time else timedelta(0)
                await self.telegram_reporter.send_performance_alert(
                    "TRAINING_STOP",
                    f"⏹️ Entrenamiento detenido\n⏱️ Duración: {duration}\n📊 Ciclos completados: {self.completed_cycles}",
                    "INFO"
                )
            
            self.logger.info("✅ Entrenamiento detenido de forma elegante")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo entrenamiento: {e}")
    
    async def _process_final_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa resultados finales del entrenamiento"""
        try:
            # Calcular estadísticas finales
            total_cycles = results.get('total_cycles', 0)
            total_trades = results.get('total_trades', 0)
            total_pnl = results.get('total_pnl_usdt', 0.0)
            
            # Obtener métricas de agentes
            agent_summaries = {}
            for symbol, agent in self.pipeline.active_agents.items():
                if hasattr(agent, 'get_agent_summary'):
                    agent_summaries[symbol] = agent.get_agent_summary()
            
            # Crear reporte final
            final_report = {
                'session_id': self.session_id,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat(),
                'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
                'config': {
                    'days_back': self.config.days_back,
                    'cycle_size_hours': self.config.cycle_size_hours,
                    'max_concurrent_agents': self.config.max_concurrent_agents
                },
                'results': results,
                'agent_summaries': agent_summaries,
                'performance_summary': {
                    'total_cycles': total_cycles,
                    'total_trades': total_trades,
                    'total_pnl_usdt': total_pnl,
                    'avg_pnl_per_cycle': total_pnl / total_cycles if total_cycles > 0 else 0,
                    'avg_trades_per_cycle': total_trades / total_cycles if total_cycles > 0 else 0
                }
            }
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando resultados finales: {e}")
            return {'error': str(e)}
    
    async def _send_final_summary(self, final_report: Dict[str, Any]):
        """Envía resumen final a Telegram"""
        try:
            if not self.telegram_reporter:
                return
            
            performance = final_report.get('performance_summary', {})
            duration_hours = final_report.get('duration_hours', 0)
            
            message = f"""
🎯 **ENTRENAMIENTO COMPLETADO** 🎯

📊 **RESUMEN FINAL:**
• **Duración:** {duration_hours:.1f} horas
• **Ciclos:** {performance.get('total_cycles', 0)}
• **Trades:** {performance.get('total_trades', 0)}
• **PnL Total:** {performance.get('total_pnl_usdt', 0):+.2f} USDT
• **PnL/Ciclo:** {performance.get('avg_pnl_per_cycle', 0):+.2f} USDT
• **Trades/Ciclo:** {performance.get('avg_trades_per_cycle', 0):.1f}

🤖 **PERFORMANCE POR AGENTE:**
            """.strip()
            
            # Agregar resumen por agente
            agent_summaries = final_report.get('agent_summaries', {})
            for symbol, summary in agent_summaries.items():
                if isinstance(summary, dict) and 'error' not in summary:
                    message += f"""
**{symbol}:**
├ PnL: {summary.get('total_pnl', 0):+.2f} USDT
├ Trades: {summary.get('total_trades', 0)}
├ Win Rate: {summary.get('win_rate', 0):.1f}%
└ DD: {summary.get('max_drawdown', 0):.1f}%
                    """.strip()
            
            await self.telegram_reporter.send_performance_alert(
                "TRAINING_COMPLETE",
                message,
                "INFO"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando resumen final: {e}")
    
    async def _handle_training_error(self, error: Exception):
        """Maneja errores durante el entrenamiento"""
        try:
            self.logger.error(f"❌ Error crítico en entrenamiento: {error}")
            
            # Enviar alerta a Telegram
            if self.telegram_reporter:
                await self.telegram_reporter.send_performance_alert(
                    "TRAINING_ERROR",
                    f"❌ Error crítico en entrenamiento:\n{str(error)}",
                    "CRITICAL"
                )
            
        except Exception as e:
            self.logger.error(f"❌ Error manejando error de entrenamiento: {e}")
    
    def get_training_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del entrenamiento"""
        try:
            return {
                'session_id': self.session_id,
                'is_running': self.is_running,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'completed_cycles': self.completed_cycles,
                'total_cycles': self.total_cycles,
                'total_trades': self.total_trades,
                'total_pnl': self.total_pnl,
                'agents_count': len(self.pipeline.active_agents),
                'telegram_enabled': self.telegram_reporter is not None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estado: {e}")
            return {'error': str(e)}

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Entrenamiento Histórico Mejorado')
    parser.add_argument('--days', type=int, default=365, help='Días hacia atrás para entrenar')
    parser.add_argument('--cycle-size', type=int, default=24, help='Tamaño del ciclo en horas')
    parser.add_argument('--max-agents', type=int, default=8, help='Máximo de agentes concurrentes')
    parser.add_argument('--telegram', action='store_true', help='Habilitar notificaciones de Telegram')
    parser.add_argument('--checkpoint-interval', type=int, default=100, help='Intervalo de checkpoint')
    
    args = parser.parse_args()
    
    # Crear configuración
    config = TrainingConfig(
        days_back=args.days,
        cycle_size_hours=args.cycle_size,
        max_concurrent_agents=args.max_agents,
        telegram_enabled=args.telegram,
        checkpoint_interval=args.checkpoint_interval
    )
    
    # Crear orquestador
    orchestrator = EnhancedTrainingOrchestrator(config)
    
    try:
        # Inicializar
        if not await orchestrator.initialize():
            logger.error("❌ Error inicializando orquestador")
            return 1
        
        # Ejecutar entrenamiento
        results = await orchestrator.execute_enhanced_training()
        
        if 'error' in results:
            logger.error(f"❌ Error en entrenamiento: {results['error']}")
            return 1
        
        logger.info("✅ Entrenamiento completado exitosamente")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️ Entrenamiento interrumpido por usuario")
        await orchestrator.stop_training()
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
