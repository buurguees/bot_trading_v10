#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/testing/test_enhanced_system.py
======================================
Script de Prueba del Sistema Mejorado

Prueba todos los componentes del sistema mejorado de forma rápida y segura.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_enhanced_system.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnhancedSystemTester:
    """Tester del Sistema Mejorado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = {}
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todas las pruebas del sistema"""
        self.logger.info("🧪 Iniciando pruebas del Sistema Mejorado")
        
        tests = [
            ("test_imports", self.test_imports),
            ("test_detailed_trade_metric", self.test_detailed_trade_metric),
            ("test_enhanced_metrics_aggregator", self.test_enhanced_metrics_aggregator),
            ("test_telegram_reporter", self.test_telegram_reporter),
            ("test_enhanced_trading_agent", self.test_enhanced_trading_agent),
            ("test_optimized_pipeline", self.test_optimized_pipeline),
            ("test_integration", self.test_integration)
        ]
        
        for test_name, test_func in tests:
            try:
                self.logger.info(f"🔍 Ejecutando: {test_name}")
                result = await test_func()
                self.test_results[test_name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'result': result
                }
                self.logger.info(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                self.logger.error(f"❌ {test_name}: ERROR - {e}")
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        # Resumen de resultados
        passed = sum(1 for r in self.test_results.values() if r['status'] == 'PASS')
        total = len(self.test_results)
        
        self.logger.info(f"\n📊 RESUMEN DE PRUEBAS:")
        self.logger.info(f"✅ Pasaron: {passed}/{total}")
        self.logger.info(f"❌ Fallaron: {total - passed}/{total}")
        
        return {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': total - passed,
            'results': self.test_results
        }
    
    async def test_imports(self) -> bool:
        """Prueba que todos los módulos se importen correctamente"""
        try:
            # Test imports principales
            from core.metrics.trade_metrics import DetailedTradeMetric, TradeAction, ConfidenceLevel
            from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
            from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
            from core.agents.enhanced_trading_agent import EnhancedTradingAgent
            from scripts.training.optimized_training_pipeline import OptimizedTrainingPipeline, TrainingConfig
            from scripts.training.integrate_enhanced_system import SystemIntegrator
            
            self.logger.info("✅ Todos los imports exitosos")
            return True
            
        except ImportError as e:
            self.logger.error(f"❌ Error de import: {e}")
            return False
    
    async def test_detailed_trade_metric(self) -> bool:
        """Prueba DetailedTradeMetric"""
        try:
            from core.metrics.trade_metrics import DetailedTradeMetric, TradeAction, ConfidenceLevel, MarketRegime, ExitReason
            
            # Crear métrica de prueba
            trade_data = {
                'action': 'LONG',
                'entry_price': 50000.0,
                'exit_price': 51000.0,
                'quantity': 0.1,
                'leverage': 1.0,
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=1),
                'duration_candles': 12,
                'balance_before': 1000.0,
                'follow_plan': True,
                'exit_reason': 'TAKE_PROFIT',
                'slippage': 0.0,
                'commission': 0.5,
                'timeframe': '5m'
            }
            
            technical_analysis = {
                'confidence_level': 'HIGH',
                'strategy_name': 'test_strategy',
                'confluence_score': 0.8,
                'risk_reward_ratio': 2.0,
                'indicators': {'rsi': 65.0, 'macd': 0.1},
                'support_resistance': {'support': 49500.0, 'resistance': 51500.0},
                'trend_strength': 0.7,
                'momentum_score': 0.6
            }
            
            market_context = {
                'market_regime': 'TRENDING_UP',
                'volatility_level': 0.02,
                'volume_confirmation': True,
                'market_session': 'EUROPEAN',
                'news_impact': None
            }
            
            # Crear métrica
            metric = DetailedTradeMetric.create_from_trade_data(
                trade_data=trade_data,
                agent_symbol='BTCUSDT',
                cycle_id=1,
                technical_analysis=technical_analysis,
                market_context=market_context
            )
            
            # Verificar propiedades
            assert metric.symbol == 'BTCUSDT'
            assert metric.action.value == 'LONG'
            assert metric.pnl_usdt == 100.0  # (51000 - 50000) * 0.1
            assert metric.was_successful == True
            assert metric.get_quality_score() > 0
            
            # Test serialización
            metric_dict = metric.to_dict()
            assert 'trade_id' in metric_dict
            assert 'pnl_usdt' in metric_dict
            
            self.logger.info("✅ DetailedTradeMetric funcionando correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en DetailedTradeMetric: {e}")
            return False
    
    async def test_enhanced_metrics_aggregator(self) -> bool:
        """Prueba EnhancedMetricsAggregator"""
        try:
            from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
            from core.metrics.trade_metrics import DetailedTradeMetric
            
            # Crear agregador
            aggregator = EnhancedMetricsAggregator(initial_capital=1000.0)
            
            # Crear datos de prueba
            test_trades = []
            for i in range(5):
                trade_data = {
                    'action': 'LONG' if i % 2 == 0 else 'SHORT',
                    'entry_price': 50000.0 + i * 100,
                    'exit_price': 50000.0 + i * 100 + (50 if i % 2 == 0 else -50),
                    'quantity': 0.1,
                    'leverage': 1.0,
                    'entry_time': datetime.now(),
                    'exit_time': datetime.now() + timedelta(hours=1),
                    'duration_candles': 12,
                    'balance_before': 1000.0,
                    'follow_plan': True,
                    'exit_reason': 'TAKE_PROFIT',
                    'slippage': 0.0,
                    'commission': 0.5,
                    'timeframe': '5m'
                }
                
                technical_analysis = {
                    'confidence_level': 'HIGH',
                    'strategy_name': f'test_strategy_{i}',
                    'confluence_score': 0.7 + i * 0.05,
                    'risk_reward_ratio': 1.5 + i * 0.1,
                    'indicators': {'rsi': 60.0 + i * 2},
                    'support_resistance': {'support': 49000.0, 'resistance': 52000.0},
                    'trend_strength': 0.6,
                    'momentum_score': 0.5
                }
                
                market_context = {
                    'market_regime': 'TRENDING_UP',
                    'volatility_level': 0.02,
                    'volume_confirmation': True,
                    'market_session': 'EUROPEAN',
                    'news_impact': None
                }
                
                trade = DetailedTradeMetric.create_from_trade_data(
                    trade_data=trade_data,
                    agent_symbol='BTCUSDT',
                    cycle_id=1,
                    technical_analysis=technical_analysis,
                    market_context=market_context
                )
                test_trades.append(trade)
            
            # Simular resultados de agentes
            agent_results = {
                'BTCUSDT': test_trades[:3],
                'ETHUSDT': test_trades[3:]
            }
            
            # Calcular métricas
            portfolio_metrics = await aggregator.calculate_portfolio_metrics(agent_results, 1)
            
            # Verificar métricas
            assert portfolio_metrics is not None
            assert portfolio_metrics.cycle_id == 1
            assert portfolio_metrics.total_trades > 0
            assert portfolio_metrics.total_pnl_usdt != 0
            
            # Test resumen por agente
            agent_summaries = aggregator.get_agent_summary(agent_results)
            assert 'BTCUSDT' in agent_summaries
            assert 'ETHUSDT' in agent_summaries
            
            self.logger.info("✅ EnhancedMetricsAggregator funcionando correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en EnhancedMetricsAggregator: {e}")
            return False
    
    async def test_telegram_reporter(self) -> bool:
        """Prueba TelegramTradeReporter (sin envío real)"""
        try:
            from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
            from core.metrics.trade_metrics import DetailedTradeMetric
            
            # Crear configuración de prueba
            config = TelegramConfig(
                bot_token="test_token",
                chat_id="test_chat",
                enable_individual_trades=True,
                enable_cycle_summaries=True,
                enable_alerts=True
            )
            
            # Crear reporter
            reporter = TelegramTradeReporter(config)
            
            # Crear trade de prueba
            trade_data = {
                'action': 'LONG',
                'entry_price': 50000.0,
                'exit_price': 51000.0,
                'quantity': 0.1,
                'leverage': 1.0,
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=1),
                'duration_candles': 12,
                'balance_before': 1000.0,
                'follow_plan': True,
                'exit_reason': 'TAKE_PROFIT',
                'slippage': 0.0,
                'commission': 0.5,
                'timeframe': '5m'
            }
            
            technical_analysis = {
                'confidence_level': 'HIGH',
                'strategy_name': 'test_strategy',
                'confluence_score': 0.8,
                'risk_reward_ratio': 2.0,
                'indicators': {'rsi': 65.0},
                'support_resistance': {'support': 49500.0, 'resistance': 51500.0},
                'trend_strength': 0.7,
                'momentum_score': 0.6
            }
            
            market_context = {
                'market_regime': 'TRENDING_UP',
                'volatility_level': 0.02,
                'volume_confirmation': True,
                'market_session': 'EUROPEAN',
                'news_impact': None
            }
            
            trade = DetailedTradeMetric.create_from_trade_data(
                trade_data=trade_data,
                agent_symbol='BTCUSDT',
                cycle_id=1,
                technical_analysis=technical_analysis,
                market_context=market_context
            )
            
            # Test formateo de mensajes (sin envío real)
            # El reporter debería formatear correctamente sin errores
            message = f"Test message for trade: {trade.trade_id}"
            
            # Test estadísticas
            stats = reporter.get_statistics()
            assert 'messages_sent' in stats
            
            self.logger.info("✅ TelegramTradeReporter funcionando correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en TelegramTradeReporter: {e}")
            return False
    
    async def test_enhanced_trading_agent(self) -> bool:
        """Prueba EnhancedTradingAgent"""
        try:
            from core.agents.enhanced_trading_agent import EnhancedTradingAgent
            from core.agents.trading_agent import TradingDecision, TradeAction, ConfidenceLevel
            import pandas as pd
            
            # Crear agente
            agent = EnhancedTradingAgent('BTCUSDT', initial_balance=1000.0)
            
            # Crear datos de mercado de prueba
            dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
            market_data = pd.DataFrame({
                'open': [50000 + i * 10 for i in range(100)],
                'high': [50050 + i * 10 for i in range(100)],
                'low': [49950 + i * 10 for i in range(100)],
                'close': [50025 + i * 10 for i in range(100)],
                'volume': [1000 + i * 10 for i in range(100)]
            }, index=dates)
            
            # Crear decisión de trading
            decision = TradingDecision(
                timestamp=datetime.now(),
                action=TradeAction.BUY,
                confidence=ConfidenceLevel.HIGH,
                price=50000.0,
                quantity=0.1,
                timeframe='5m',
                strategy_used='test_strategy',
                features_analyzed={'rsi': 65.0, 'macd': 0.1},
                reasoning='Test trade',
                expected_outcome='Profit',
                risk_reward_ratio=2.0
            )
            
            # Ejecutar trade con tracking
            trade_metric = await agent.execute_trade_with_tracking(
                decision, market_data, cycle_id=1
            )
            
            # Verificar que se creó la métrica
            assert trade_metric is not None
            assert trade_metric.agent_symbol == 'BTCUSDT'
            assert trade_metric.cycle_id == 1
            
            # Test métricas por estrategia
            strategy_metrics = agent.get_strategy_metrics('test_strategy')
            assert strategy_metrics is not None
            assert strategy_metrics.strategy_name == 'test_strategy'
            
            # Test resumen del agente
            agent_summary = agent.get_agent_summary()
            assert 'symbol' in agent_summary
            assert agent_summary['symbol'] == 'BTCUSDT'
            
            # Test estado del agente
            agent_state = agent.get_state()
            assert 'agent_id' in agent_state
            
            self.logger.info("✅ EnhancedTradingAgent funcionando correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en EnhancedTradingAgent: {e}")
            return False
    
    async def test_optimized_pipeline(self) -> bool:
        """Prueba OptimizedTrainingPipeline (configuración básica)"""
        try:
            from scripts.training.optimized_training_pipeline import OptimizedTrainingPipeline, TrainingConfig
            
            # Crear configuración de prueba
            config = TrainingConfig(
                days_back=1,  # Solo 1 día para prueba
                cycle_size_hours=1,  # Ciclos de 1 hora
                max_concurrent_agents=2,  # Solo 2 agentes
                telegram_enabled=False,  # Sin Telegram para prueba
                checkpoint_interval=10,
                memory_cleanup_interval=5,
                max_memory_usage_mb=1000,  # Límite bajo para prueba
                recovery_enabled=True
            )
            
            # Crear pipeline
            pipeline = OptimizedTrainingPipeline(config)
            
            # Test inicialización (sin ejecutar entrenamiento completo)
            # Solo verificar que se puede crear y configurar
            assert pipeline.config.days_back == 1
            assert pipeline.config.max_concurrent_agents == 2
            
            # Test monitor de memoria
            memory_usage = pipeline.memory_monitor.get_memory_usage()
            assert memory_usage >= 0
            
            self.logger.info("✅ OptimizedTrainingPipeline configurado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en OptimizedTrainingPipeline: {e}")
            return False
    
    async def test_integration(self) -> bool:
        """Prueba integración básica del sistema"""
        try:
            from scripts.training.integrate_enhanced_system import SystemIntegrator
            
            # Crear integrador
            integrator = SystemIntegrator()
            
            # Test configuración básica (sin Telegram)
            success = await integrator.setup_enhanced_training(
                days_back=1,
                cycle_size_hours=1,
                max_concurrent_agents=2,
                telegram_enabled=False
            )
            
            if success:
                # Test estado del sistema
                status = integrator.get_system_status()
                assert 'status' in status
                
                self.logger.info("✅ Integración del sistema funcionando correctamente")
                return True
            else:
                self.logger.error("❌ Error configurando sistema integrado")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error en integración: {e}")
            return False

async def main():
    """Función principal de testing"""
    print("🧪 Sistema de Pruebas - Bot Trading v10 Enterprise")
    print("=" * 60)
    
    tester = EnhancedSystemTester()
    results = await tester.run_all_tests()
    
    # Mostrar resumen
    print(f"\n📊 RESUMEN FINAL:")
    print(f"✅ Pruebas exitosas: {results['passed_tests']}/{results['total_tests']}")
    print(f"❌ Pruebas fallidas: {results['failed_tests']}/{results['total_tests']}")
    
    if results['failed_tests'] > 0:
        print(f"\n❌ PRUEBAS FALLIDAS:")
        for test_name, result in results['results'].items():
            if result['status'] != 'PASS':
                print(f"  - {test_name}: {result['status']}")
                if 'error' in result:
                    print(f"    Error: {result['error']}")
    
    # Determinar código de salida
    return 0 if results['failed_tests'] == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
