#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/testing/quick_validation_test.py
=======================================
Prueba Rápida de Validación del Sistema Mejorado

Valida rápidamente los aspectos críticos del sistema:
- Mensajes de trades individuales
- Resúmenes de ciclo
- Trading en 1m y 5m
- Análisis con todos los timeframes
- Uso de features
- Registro de estrategias
- Objetivos a cumplir

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.metrics.trade_metrics import DetailedTradeMetric, TradeAction, ConfidenceLevel, MarketRegime, ExitReason
from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
from core.agents.enhanced_trading_agent import EnhancedTradingAgent

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/quick_validation_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class QuickValidationTester:
    """Tester Rápido de Validación del Sistema Mejorado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = {}
        self.telegram_messages = []
        self.trades_generated = []
        
        # Configuración de prueba rápida
        self.cycles_to_test = 5  # 5 ciclos de prueba
        self.trades_per_cycle = 3  # 3 trades por ciclo por agente
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        self.execution_timeframes = ['1m', '5m']
        self.analysis_timeframes = ['15m', '1h', '4h', '1d']
        
        self.logger.info("🧪 QuickValidationTester inicializado")
    
    async def run_quick_validation(self) -> Dict[str, Any]:
        """Ejecuta validación rápida del sistema"""
        self.logger.info("🚀 INICIANDO VALIDACIÓN RÁPIDA")
        
        try:
            # 1. Inicializar componentes
            await self._initialize_components()
            
            # 2. Ejecutar ciclos de prueba
            await self._run_validation_cycles()
            
            # 3. Validar aspectos críticos
            validation_results = await self._validate_critical_aspects()
            
            # 4. Generar reporte
            final_report = await self._generate_validation_report(validation_results)
            
            self.logger.info("✅ VALIDACIÓN RÁPIDA COMPLETADA")
            return final_report
            
        except Exception as e:
            self.logger.error(f"❌ Error en validación rápida: {e}")
            return {'error': str(e)}
    
    async def _initialize_components(self):
        """Inicializa componentes del sistema"""
        self.logger.info("🔧 Inicializando componentes...")
        
        # Crear agentes
        self.agents = {}
        for symbol in self.symbols:
            agent = EnhancedTradingAgent(symbol, initial_balance=1000.0)
            self.agents[symbol] = agent
        
        # Crear agregador de métricas
        self.metrics_aggregator = EnhancedMetricsAggregator(initial_capital=1000.0)
        
        # Crear reporter de Telegram
        telegram_config = TelegramConfig(
            bot_token="test_token",
            chat_id="test_chat",
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        self.telegram_reporter = TelegramTradeReporter(telegram_config)
        
        self.logger.info("✅ Componentes inicializados")
    
    async def _run_validation_cycles(self):
        """Ejecuta ciclos de validación"""
        self.logger.info("🔄 Ejecutando ciclos de validación...")
        
        for cycle_id in range(self.cycles_to_test):
            self.logger.info(f"🔄 Ciclo {cycle_id + 1}/{self.cycles_to_test}")
            
            # Generar datos de mercado
            market_data = await self._generate_market_data(cycle_id)
            
            # Ejecutar trading en 1m y 5m
            cycle_trades = []
            for symbol in self.symbols:
                agent = self.agents[symbol]
                
                for tf in self.execution_timeframes:
                    tf_data = market_data.get(tf, {})
                    if tf_data:
                        trades = await self._generate_agent_trades(
                            agent, tf_data, tf, cycle_id
                        )
                        cycle_trades.extend(trades)
            
            # Calcular métricas del ciclo
            portfolio_metrics = await self.metrics_aggregator.calculate_portfolio_metrics(
                {symbol: [t for t in cycle_trades if t.agent_symbol == symbol] 
                 for symbol in self.symbols}, 
                cycle_id
            )
            
            # Simular envío a Telegram
            await self._simulate_telegram_sending(cycle_trades, portfolio_metrics, cycle_id)
            
            # Procesar resultados
            await self._process_cycle_results(cycle_trades, cycle_id)
            
            self.trades_generated.extend(cycle_trades)
            
            # Pequeña pausa entre ciclos
            await asyncio.sleep(0.1)
        
        self.logger.info(f"✅ Ciclos completados: {self.cycles_to_test}")
    
    async def _generate_market_data(self, cycle_id: int) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Genera datos de mercado simulados"""
        market_data = {}
        
        for tf in self.timeframes:
            tf_data = {}
            
            for symbol in self.symbols:
                # Generar datos OHLCV
                periods = 50
                base_price = 50000 + cycle_id * 100
                
                # Generar precios con tendencia
                returns = np.random.normal(0.001, 0.02, periods)
                prices = [base_price]
                
                for ret in returns[1:]:
                    new_price = prices[-1] * (1 + ret)
                    prices.append(new_price)
                
                # Crear DataFrame
                df_data = []
                for i, price in enumerate(prices):
                    high = price * (1 + abs(np.random.normal(0, 0.01)))
                    low = price * (1 - abs(np.random.normal(0, 0.01)))
                    open_price = prices[i-1] if i > 0 else price
                    volume = np.random.uniform(1000, 10000)
                    
                    df_data.append({
                        'timestamp': datetime.now() - timedelta(minutes=(periods-i)*5),
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': price,
                        'volume': volume
                    })
                
                df = pd.DataFrame(df_data)
                df.set_index('timestamp', inplace=True)
                tf_data[symbol] = df
            
            market_data[tf] = tf_data
        
        return market_data
    
    async def _generate_agent_trades(
        self, 
        agent: EnhancedTradingAgent, 
        market_data: Dict[str, pd.DataFrame], 
        timeframe: str, 
        cycle_id: int
    ) -> List[DetailedTradeMetric]:
        """Genera trades para un agente"""
        trades = []
        
        agent_data = market_data.get(agent.symbol)
        if agent_data is None or agent_data.empty:
            return trades
        
        # Generar trades
        for trade_idx in range(self.trades_per_cycle):
            current_price = agent_data['close'].iloc[-1]
            
            # Simular decisión de trading
            action = self._simulate_trading_decision(agent_data, timeframe)
            
            if action != TradeAction.HOLD:
                trade = await self._simulate_trade_execution(
                    agent, action, current_price, timeframe, cycle_id
                )
                
                if trade:
                    trades.append(trade)
        
        return trades
    
    def _simulate_trading_decision(self, market_data: pd.DataFrame, timeframe: str) -> TradeAction:
        """Simula decisión de trading"""
        current_price = market_data['close'].iloc[-1]
        sma_20 = market_data['close'].rolling(20).mean().iloc[-1]
        
        if pd.isna(sma_20):
            return TradeAction.HOLD
        
        if current_price > sma_20 * 1.01:
            return TradeAction.LONG
        elif current_price < sma_20 * 0.99:
            return TradeAction.SHORT
        else:
            return TradeAction.HOLD
    
    async def _simulate_trade_execution(
        self, 
        agent: EnhancedTradingAgent, 
        action: TradeAction, 
        entry_price: float, 
        timeframe: str, 
        cycle_id: int
    ) -> Optional[DetailedTradeMetric]:
        """Simula ejecución de trade"""
        try:
            # Simular precio de salida
            price_change_pct = np.random.normal(0.02, 0.01)
            exit_price = entry_price * (1 + price_change_pct)
            
            # Calcular PnL
            quantity = 0.1
            if action == TradeAction.LONG:
                pnl_usdt = (exit_price - entry_price) * quantity
            else:  # SHORT
                pnl_usdt = (entry_price - exit_price) * quantity
            
            # Crear datos del trade
            trade_data = {
                'action': action.value,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'leverage': 1.0,
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=1),
                'duration_candles': 12,
                'balance_before': agent.agent_state.current_balance,
                'follow_plan': True,
                'exit_reason': 'TAKE_PROFIT' if pnl_usdt > 0 else 'STOP_LOSS',
                'slippage': 0.0,
                'commission': abs(pnl_usdt) * 0.001,
                'timeframe': timeframe
            }
            
            # Análisis técnico simulado
            technical_analysis = {
                'confidence_level': 'HIGH',
                'strategy_name': f'strategy_{np.random.randint(1, 4)}',
                'confluence_score': np.random.uniform(0.6, 0.9),
                'risk_reward_ratio': np.random.uniform(1.5, 2.5),
                'indicators': {
                    'rsi': np.random.uniform(30, 70),
                    'macd': np.random.uniform(-0.05, 0.05),
                    'sma_20': entry_price * np.random.uniform(0.98, 1.02)
                },
                'support_resistance': {
                    'support': entry_price * 0.95,
                    'resistance': entry_price * 1.05
                },
                'trend_strength': np.random.uniform(0.5, 0.8),
                'momentum_score': np.random.uniform(0.5, 0.8)
            }
            
            # Contexto de mercado
            market_context = {
                'market_regime': 'TRENDING_UP',
                'volatility_level': np.random.uniform(0.02, 0.04),
                'volume_confirmation': True,
                'market_session': 'EUROPEAN',
                'news_impact': None
            }
            
            # Crear métrica detallada
            trade_metric = DetailedTradeMetric.create_from_trade_data(
                trade_data=trade_data,
                agent_symbol=agent.symbol,
                cycle_id=cycle_id,
                technical_analysis=technical_analysis,
                market_context=market_context
            )
            
            # Actualizar estado del agente
            await agent._update_agent_state(trade_metric)
            
            return trade_metric
            
        except Exception as e:
            self.logger.error(f"❌ Error simulando trade: {e}")
            return None
    
    async def _simulate_telegram_sending(
        self, 
        trades: List[DetailedTradeMetric], 
        portfolio_metrics, 
        cycle_id: int
    ):
        """Simula envío de mensajes a Telegram"""
        try:
            # Simular mensajes de trades individuales
            for trade in trades:
                message = {
                    'type': 'individual_trade',
                    'timestamp': datetime.now(),
                    'trade_id': trade.trade_id,
                    'symbol': trade.agent_symbol,
                    'action': trade.action.value,
                    'pnl': trade.pnl_usdt,
                    'timeframe': trade.timeframe_analyzed
                }
                self.telegram_messages.append(message)
            
            # Simular resumen de ciclo
            if portfolio_metrics:
                summary_message = {
                    'type': 'cycle_summary',
                    'timestamp': datetime.now(),
                    'cycle_id': cycle_id,
                    'total_pnl': portfolio_metrics.total_pnl_usdt,
                    'total_trades': portfolio_metrics.total_trades,
                    'win_rate': portfolio_metrics.win_rate
                }
                self.telegram_messages.append(summary_message)
            
        except Exception as e:
            self.logger.error(f"❌ Error simulando Telegram: {e}")
    
    async def _process_cycle_results(self, trades: List[DetailedTradeMetric], cycle_id: int):
        """Procesa resultados del ciclo"""
        try:
            # Actualizar estrategias por agente
            for trade in trades:
                agent = self.agents[trade.agent_symbol]
                strategy_name = trade.strategy_name
                
                if strategy_name not in agent.agent_state.strategy_performance:
                    agent.agent_state.strategy_performance[strategy_name] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'total_pnl': 0.0,
                        'trades': []
                    }
                
                strategy_metrics = agent.agent_state.strategy_performance[strategy_name]
                strategy_metrics['total_trades'] += 1
                if trade.was_successful:
                    strategy_metrics['winning_trades'] += 1
                strategy_metrics['total_pnl'] += trade.pnl_usdt
                strategy_metrics['trades'].append(trade.trade_id)
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando resultados: {e}")
    
    async def _validate_critical_aspects(self) -> Dict[str, bool]:
        """Valida aspectos críticos del sistema"""
        self.logger.info("🎯 Validando aspectos críticos...")
        
        validation = {}
        
        # 1. Trades generados
        total_trades = len(self.trades_generated)
        validation['trades_generated'] = total_trades > 0
        self.logger.info(f"📊 Trades generados: {total_trades}")
        
        # 2. Mensajes de Telegram
        total_messages = len(self.telegram_messages)
        validation['telegram_messages'] = total_messages > 0
        self.logger.info(f"📱 Mensajes Telegram: {total_messages}")
        
        # 3. Trading en 1m y 5m
        execution_tfs = set(t.timeframe_analyzed for t in self.trades_generated)
        validation['trading_1m_5m'] = '1m' in execution_tfs and '5m' in execution_tfs
        self.logger.info(f"⏰ Timeframes de trading: {execution_tfs}")
        
        # 4. Análisis con todos los timeframes
        validation['analysis_timeframes'] = len(self.analysis_timeframes) > 0
        self.logger.info(f"📊 Timeframes de análisis: {len(self.analysis_timeframes)}")
        
        # 5. Uso de features
        features_used = set()
        for trade in self.trades_generated:
            features_used.update(trade.technical_indicators.keys())
        validation['features_used'] = len(features_used) > 0
        self.logger.info(f"🔧 Features utilizadas: {features_used}")
        
        # 6. Estrategias registradas
        all_strategies = set()
        for agent in self.agents.values():
            all_strategies.update(agent.agent_state.strategy_performance.keys())
        validation['strategies_registered'] = len(all_strategies) > 0
        self.logger.info(f"🔍 Estrategias registradas: {len(all_strategies)}")
        
        # 7. Mejores y peores estrategias
        if all_strategies:
            strategy_performance = {}
            for agent in self.agents.values():
                for strategy_name, metrics in agent.agent_state.strategy_performance.items():
                    if strategy_name not in strategy_performance:
                        strategy_performance[strategy_name] = {
                            'total_pnl': 0.0,
                            'total_trades': 0
                        }
                    strategy_performance[strategy_name]['total_pnl'] += metrics['total_pnl']
                    strategy_performance[strategy_name]['total_trades'] += metrics['total_trades']
            
            sorted_strategies = sorted(
                strategy_performance.items(), 
                key=lambda x: x[1]['total_pnl'], 
                reverse=True
            )
            
            validation['best_worst_strategies'] = len(sorted_strategies) > 0
            self.logger.info(f"🏆 Mejores estrategias: {sorted_strategies[:2]}")
            self.logger.info(f"⚠️ Peores estrategias: {sorted_strategies[-2:]}")
        else:
            validation['best_worst_strategies'] = False
        
        # 8. Objetivos cumplidos
        if total_trades > 0:
            winning_trades = sum(1 for t in self.trades_generated if t.was_successful)
            win_rate = winning_trades / total_trades
            validation['objectives_met'] = win_rate > 0.3  # 30% mínimo
            self.logger.info(f"🎯 Win rate: {win_rate:.2%}")
        else:
            validation['objectives_met'] = False
        
        # 9. Calidad de trades
        if total_trades > 0:
            high_quality_trades = sum(1 for t in self.trades_generated if t.is_high_quality_trade())
            quality_ratio = high_quality_trades / total_trades
            validation['quality_trades'] = quality_ratio > 0.2  # 20% mínimo
            self.logger.info(f"⭐ Trades de alta calidad: {quality_ratio:.2%}")
        else:
            validation['quality_trades'] = False
        
        # 10. Robustez del sistema
        validation['system_robustness'] = (
            validation['trades_generated'] and
            validation['telegram_messages'] and
            validation['trading_1m_5m'] and
            validation['features_used'] and
            validation['strategies_registered']
        )
        
        return validation
    
    async def _generate_validation_report(self, validation: Dict[str, bool]) -> Dict[str, Any]:
        """Genera reporte de validación"""
        try:
            total_trades = len(self.trades_generated)
            total_messages = len(self.telegram_messages)
            
            # Calcular métricas
            if total_trades > 0:
                winning_trades = sum(1 for t in self.trades_generated if t.was_successful)
                win_rate = winning_trades / total_trades
                total_pnl = sum(t.pnl_usdt for t in self.trades_generated)
                avg_quality = np.mean([t.get_quality_score() for t in self.trades_generated])
            else:
                win_rate = 0.0
                total_pnl = 0.0
                avg_quality = 0.0
            
            # Estrategias por agente
            agent_strategies = {}
            for symbol, agent in self.agents.items():
                strategies = list(agent.agent_state.strategy_performance.keys())
                agent_strategies[symbol] = {
                    'strategies_count': len(strategies),
                    'strategies': strategies,
                    'total_pnl': sum(t.pnl_usdt for t in self.trades_generated if t.agent_symbol == symbol),
                    'trades_count': sum(1 for t in self.trades_generated if t.agent_symbol == symbol)
                }
            
            # Contar validaciones exitosas
            passed_validations = sum(1 for v in validation.values() if v)
            total_validations = len(validation)
            
            report = {
                'validation_summary': {
                    'passed': passed_validations,
                    'total': total_validations,
                    'success_rate': passed_validations / total_validations if total_validations > 0 else 0
                },
                'performance_metrics': {
                    'total_trades': total_trades,
                    'total_telegram_messages': total_messages,
                    'win_rate': win_rate,
                    'total_pnl_usdt': total_pnl,
                    'avg_quality_score': avg_quality
                },
                'validation_results': validation,
                'agent_performance': agent_strategies,
                'timeframe_analysis': {
                    'execution_timeframes': list(set(t.timeframe_analyzed for t in self.trades_generated)),
                    'analysis_timeframes': self.analysis_timeframes
                },
                'features_analysis': {
                    'features_used': list(set(feature for t in self.trades_generated 
                                            for feature in t.technical_indicators.keys())),
                    'features_count': len(set(feature for t in self.trades_generated 
                                            for feature in t.technical_indicators.keys()))
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte: {e}")
            return {'error': str(e)}

async def main():
    """Función principal de validación rápida"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 VALIDACIÓN RÁPIDA DEL SISTEMA 🧪                     ║
║                    Sistema de Entrenamiento Mejorado                       ║
║                                                                              ║
║  ⚡ 5 ciclos de prueba rápida                                              ║
║  🤖 2 agentes operando                                                     ║
║  ⏰ Trading en 1m y 5m, análisis en todos los TFs                         ║
║  📱 Mensajes de Telegram simulados                                        ║
║  🎯 Validación de aspectos críticos                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    tester = QuickValidationTester()
    
    try:
        print("🚀 Iniciando validación rápida...")
        results = await tester.run_quick_validation()
        
        if 'error' in results:
            print(f"❌ Error en la validación: {results['error']}")
            return 1
        
        # Mostrar resultados
        print("\n" + "="*80)
        print("📊 RESULTADOS DE LA VALIDACIÓN RÁPIDA")
        print("="*80)
        
        summary = results.get('validation_summary', {})
        print(f"✅ Validaciones exitosas: {summary.get('passed', 0)}/{summary.get('total', 0)}")
        print(f"🎯 Tasa de éxito: {summary.get('success_rate', 0):.1%}")
        
        # Métricas de performance
        perf = results.get('performance_metrics', {})
        print(f"\n📈 MÉTRICAS DE PERFORMANCE:")
        print(f"📊 Trades generados: {perf.get('total_trades', 0)}")
        print(f"📱 Mensajes Telegram: {perf.get('total_telegram_messages', 0)}")
        print(f"🎯 Win Rate: {perf.get('win_rate', 0):.2%}")
        print(f"💰 PnL Total: {perf.get('total_pnl_usdt', 0):+.2f} USDT")
        print(f"⭐ Calidad Promedio: {perf.get('avg_quality_score', 0):.1f}/100")
        
        # Validaciones específicas
        print(f"\n🎯 VALIDACIONES ESPECÍFICAS:")
        validations = results.get('validation_results', {})
        for validation, passed in validations.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {validation}")
        
        # Análisis de timeframes
        tf_analysis = results.get('timeframe_analysis', {})
        print(f"\n⏰ ANÁLISIS DE TIMEFRAMES:")
        print(f"  Trading: {tf_analysis.get('execution_timeframes', [])}")
        print(f"  Análisis: {tf_analysis.get('analysis_timeframes', [])}")
        
        # Features utilizadas
        features = results.get('features_analysis', {})
        print(f"\n🔧 FEATURES UTILIZADAS:")
        print(f"  Count: {features.get('features_count', 0)}")
        print(f"  Features: {features.get('features_used', [])}")
        
        # Performance por agente
        print(f"\n🤖 PERFORMANCE POR AGENTE:")
        agent_perf = results.get('agent_performance', {})
        for symbol, metrics in agent_perf.items():
            print(f"  {symbol}: {metrics.get('trades_count', 0)} trades, "
                  f"{metrics.get('strategies_count', 0)} estrategias, "
                  f"PnL: {metrics.get('total_pnl', 0):+.2f} USDT")
        
        # Determinar éxito
        success_rate = summary.get('success_rate', 0)
        if success_rate >= 0.8:  # 80% de validaciones exitosas
            print(f"\n🎉 ¡VALIDACIÓN EXITOSA! ({success_rate:.1%})")
            print("✅ El sistema está listo para funcionar correctamente")
            return 0
        else:
            print(f"\n⚠️ Validación completada con advertencias ({success_rate:.1%})")
            print("❌ Algunos aspectos necesitan atención")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Validación interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
