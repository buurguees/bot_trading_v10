"""
🧪 test_ai_agent.py - Tests para el Agente de IA

Script de prueba para validar el funcionamiento del TradingAgent
autónomo, autodidacta y autocorrectivo.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del proyecto
from config.config_loader import user_config
from agents.trading_agent import TradingAgent
from agents.autonomous_decision_engine import AutonomousDecisionEngine
from agents.self_learning_system import SelfLearningSystem
from agents.self_correction_mechanism import SelfCorrectionMechanism

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIAgentTester:
    """Tester para el Agente de IA"""
    
    def __init__(self):
        self.agent = None
        self.test_results = {}
    
    async def run_all_tests(self) -> Dict:
        """Ejecuta todos los tests del agente"""
        logger.info("🧪 Iniciando tests del Agente de IA...")
        
        try:
            # Test 1: Inicialización del agente
            await self.test_agent_initialization()
            
            # Test 2: Motor de decisiones
            await self.test_decision_engine()
            
            # Test 3: Sistema de aprendizaje
            await self.test_learning_system()
            
            # Test 4: Mecanismo de autocorrección
            await self.test_self_correction()
            
            # Test 5: Integración completa
            await self.test_full_integration()
            
            # Mostrar resultados
            self.print_test_results()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Error en tests: {e}")
            return {'error': str(e)}
    
    async def test_agent_initialization(self) -> bool:
        """Test de inicialización del agente"""
        logger.info("🔧 Test 1: Inicialización del agente...")
        
        try:
            # Crear agente
            self.agent = TradingAgent()
            
            # Verificar componentes
            assert self.agent.decision_engine is not None, "Decision engine no inicializado"
            assert self.agent.learning_system is not None, "Learning system no inicializado"
            assert self.agent.correction_mechanism is not None, "Correction mechanism no inicializado"
            
            # Inicializar agente
            initialized = await self.agent.initialize()
            assert initialized, "Agente no se inicializó correctamente"
            
            # Verificar estado
            status = self.agent.get_agent_status()
            assert status['state'] in ['learning', 'trading'], f"Estado inválido: {status['state']}"
            
            self.test_results['initialization'] = True
            logger.info("✅ Test de inicialización: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de inicialización: FAILED - {e}")
            self.test_results['initialization'] = False
            return False
    
    async def test_decision_engine(self) -> bool:
        """Test del motor de decisiones"""
        logger.info("🧠 Test 2: Motor de decisiones...")
        
        try:
            decision_engine = self.agent.decision_engine
            
            # Crear datos de mercado simulados
            market_data = {
                'klines': [
                    {
                        'open': 45000.0,
                        'high': 45500.0,
                        'low': 44800.0,
                        'close': 45200.0,
                        'volume': 1000000.0,
                        'timestamp': datetime.now()
                    }
                ],
                'features': None,
                'prediction': {'confidence': 0.8, 'signal': 'BUY'},
                'balance': 10000.0,
                'current_position': None
            }
            
            # Test análisis de mercado
            analysis = await decision_engine.analyze_market_state(market_data)
            assert analysis is not None, "Análisis de mercado falló"
            assert hasattr(analysis, 'trend_direction'), "Análisis incompleto"
            
            # Test toma de decisión
            decision = await decision_engine.make_decision(analysis)
            if decision:  # Puede ser None si no cumple criterios
                assert 'action' in decision, "Decisión sin acción"
                assert 'confidence' in decision, "Decisión sin confianza"
                assert 'reasoning' in decision, "Decisión sin reasoning"
            
            # Test estadísticas
            stats = decision_engine.get_decision_statistics()
            assert isinstance(stats, dict), "Estadísticas inválidas"
            
            self.test_results['decision_engine'] = True
            logger.info("✅ Test de motor de decisiones: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de motor de decisiones: FAILED - {e}")
            self.test_results['decision_engine'] = False
            return False
    
    async def test_learning_system(self) -> bool:
        """Test del sistema de aprendizaje"""
        logger.info("🎓 Test 3: Sistema de aprendizaje...")
        
        try:
            learning_system = self.agent.learning_system
            
            # Crear episodio de aprendizaje simulado
            episode = {
                'decision': {
                    'action': 'BUY',
                    'confidence': 0.8,
                    'reasoning': 'Test decision'
                },
                'result': {
                    'pnl': 150.0,
                    'duration_hours': 2.5,
                    'success': True
                },
                'timestamp': datetime.now()
            }
            
            # Test aprendizaje de episodio
            await learning_system.learn_from_episode(episode)
            
            # Test adaptación a condiciones
            recent_performance = {
                'win_rate': 0.7,
                'avg_pnl': 100.0,
                'trade_count': 10
            }
            
            market_changes = {
                'volatility_change': 1.2,
                'volume_change': 1.1,
                'trend_change': 0.05
            }
            
            adaptations = await learning_system.adapt_to_conditions(
                recent_performance, market_changes
            )
            assert isinstance(adaptations, list), "Adaptaciones inválidas"
            
            # Test estadísticas
            stats = learning_system.get_learning_statistics()
            assert isinstance(stats, dict), "Estadísticas de aprendizaje inválidas"
            
            # Test insights
            insights = learning_system.get_learning_insights()
            assert isinstance(insights, dict), "Insights de aprendizaje inválidos"
            
            self.test_results['learning_system'] = True
            logger.info("✅ Test de sistema de aprendizaje: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de sistema de aprendizaje: FAILED - {e}")
            self.test_results['learning_system'] = False
            return False
    
    async def test_self_correction(self) -> bool:
        """Test del mecanismo de autocorrección"""
        logger.info("🔧 Test 4: Mecanismo de autocorrección...")
        
        try:
            correction_mechanism = self.agent.correction_mechanism
            
            # Test validación de decisión
            decision = {
                'action': 'BUY',
                'confidence': 0.6,
                'reasoning': 'Test decision'
            }
            
            analysis = {
                'market_regime': 'bull',
                'trend_direction': 'bullish',
                'volatility_level': 'medium',
                'risk_level': 'low'
            }
            
            validated_decision = await correction_mechanism.validate_decision(decision, analysis)
            assert validated_decision is not None, "Validación de decisión falló"
            
            # Test detección de errores
            context = {
                'performance': {
                    'accuracy': 0.5,
                    'total_pnl': -500.0,
                    'max_drawdown': 0.15
                },
                'predictions': [
                    {'correct': True, 'confidence': 0.8},
                    {'correct': False, 'confidence': 0.6}
                ],
                'decisions': [
                    {'action': 'BUY', 'confidence': 0.7},
                    {'action': 'SELL', 'confidence': 0.8}
                ],
                'system_health': {
                    'memory_usage': 0.7,
                    'cpu_usage': 0.6
                }
            }
            
            errors = await correction_mechanism.detect_errors(context)
            assert isinstance(errors, list), "Detección de errores falló"
            
            # Test aplicación de correcciones
            if errors:
                corrections = await correction_mechanism.apply_corrections(errors)
                assert isinstance(corrections, list), "Aplicación de correcciones falló"
            
            # Test estadísticas
            stats = correction_mechanism.get_correction_statistics()
            assert isinstance(stats, dict), "Estadísticas de corrección inválidas"
            
            self.test_results['self_correction'] = True
            logger.info("✅ Test de mecanismo de autocorrección: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de mecanismo de autocorrección: FAILED - {e}")
            self.test_results['self_correction'] = False
            return False
    
    async def test_full_integration(self) -> bool:
        """Test de integración completa"""
        logger.info("🔗 Test 5: Integración completa...")
        
        try:
            # Test estado del agente
            status = self.agent.get_agent_status()
            assert 'state' in status, "Estado del agente inválido"
            assert 'is_active' in status, "Estado activo inválido"
            assert 'performance' in status, "Métricas de performance inválidas"
            
            # Test insights del agente
            insights = self.agent.get_agent_insights()
            assert isinstance(insights, dict), "Insights del agente inválidos"
            
            # Test memoria del agente
            memory = self.agent.memory
            assert hasattr(memory, 'trade_history'), "Memoria de trades inválida"
            assert hasattr(memory, 'learning_episodes'), "Memoria de aprendizaje inválida"
            
            # Test configuración del agente
            config = self.agent.agent_config
            assert isinstance(config, dict), "Configuración del agente inválida"
            
            self.test_results['full_integration'] = True
            logger.info("✅ Test de integración completa: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de integración completa: FAILED - {e}")
            self.test_results['full_integration'] = False
            return False
    
    def print_test_results(self) -> None:
        """Imprime los resultados de los tests"""
        logger.info("\n" + "="*60)
        logger.info("🧪 RESULTADOS DE TESTS DEL AGENTE DE IA")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name.upper()}: {status}")
        
        logger.info("-"*60)
        logger.info(f"TOTAL: {passed_tests}/{total_tests} tests pasaron")
        
        if passed_tests == total_tests:
            logger.info("🎉 ¡TODOS LOS TESTS PASARON! El agente está listo.")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests fallaron. Revisar implementación.")
        
        logger.info("="*60)

async def main():
    """Función principal de testing"""
    logger.info("🚀 Iniciando tests del Agente de IA...")
    
    # Crear tester
    tester = AIAgentTester()
    
    # Ejecutar tests
    results = await tester.run_all_tests()
    
    # Verificar si todos los tests pasaron
    all_passed = all(result for result in results.values() if isinstance(result, bool))
    
    if all_passed:
        logger.info("🎉 ¡Todos los tests del Agente de IA pasaron exitosamente!")
        return 0
    else:
        logger.error("❌ Algunos tests del Agente de IA fallaron.")
        return 1

if __name__ == "__main__":
    # Ejecutar tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
