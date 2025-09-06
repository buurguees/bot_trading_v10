"""
🤖 TradingAgent - Agente Principal de IA para Trading

Agente autónomo, autodidacta y autocorrectivo que:
- Toma decisiones de trading de forma independiente
- Aprende continuamente de sus acciones y resultados
- Se autocorrige y adapta a condiciones cambiantes del mercado
- Integra todo el sistema ML y de trading existente

Características principales:
- Autonomía: Decisiones independientes sin intervención humana
- Autodidacta: Aprendizaje continuo de experiencias pasadas
- Autocorrección: Detección y corrección de errores automáticamente
- Adaptabilidad: Ajuste dinámico a condiciones de mercado

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Imports del sistema existente
from config.config_loader import user_config
from models.predictor import predictor
from models.trainer import trainer
from trading.execution_engine import execution_engine
from trading.risk_manager import risk_manager
from trading.order_manager import order_manager
from data.preprocessor import data_preprocessor
from data.collector import data_collector

# Imports de los nuevos módulos del agente
from .autonomous_decision_engine import AutonomousDecisionEngine
from .self_learning_system import SelfLearningSystem
from .self_correction_mechanism import SelfCorrectionMechanism

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Estados del agente"""
    INITIALIZING = "initializing"
    LEARNING = "learning"
    TRADING = "trading"
    ADAPTING = "adapting"
    CORRECTING = "correcting"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class AgentMemory:
    """Memoria del agente para almacenar experiencias"""
    trade_history: List[Dict]
    prediction_history: List[Dict]
    learning_episodes: List[Dict]
    performance_metrics: Dict
    market_regimes: List[Dict]
    correction_actions: List[Dict]
    last_update: datetime

@dataclass
class AgentDecision:
    """Decisión tomada por el agente"""
    action: str  # BUY, SELL, HOLD
    confidence: float
    reasoning: str
    expected_return: float
    risk_assessment: str
    market_context: Dict
    timestamp: datetime
    decision_id: str

class TradingAgent:
    """
    🤖 Agente Principal de IA para Trading
    
    Agente autónomo que integra todo el sistema de ML y trading,
    capaz de tomar decisiones independientes, aprender continuamente
    y autocorregirse.
    """
    
    def __init__(self):
        """Inicializa el agente de trading"""
        self.config = user_config
        self.state = AgentState.INITIALIZING
        
        # Componentes principales
        self.decision_engine = AutonomousDecisionEngine()
        self.learning_system = SelfLearningSystem()
        self.correction_mechanism = SelfCorrectionMechanism()
        
        # Memoria del agente
        self.memory = AgentMemory(
            trade_history=[],
            prediction_history=[],
            learning_episodes=[],
            performance_metrics={},
            market_regimes=[],
            correction_actions=[],
            last_update=datetime.now()
        )
        
        # Configuración del agente
        self.agent_config = self.config.get_value(['ai_agent'], {})
        self.learning_rate = self.agent_config.get('learning_rate', 0.01)
        self.confidence_threshold = self.agent_config.get('confidence_threshold', 0.7)
        self.adaptation_frequency = self.agent_config.get('adaptation_frequency', 100)  # cada N trades
        self.correction_threshold = self.agent_config.get('correction_threshold', 0.6)  # umbral para autocorrección
        
        # Métricas de performance
        self.performance_tracker = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_pnl': 0.0,
            'accuracy': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'learning_episodes': 0,
            'corrections_applied': 0
        }
        
        # Estado de trading
        self.is_active = False
        self.current_position = None
        self.last_decision = None
        self.decision_counter = 0
        
        logger.info("🤖 TradingAgent inicializado - Listo para operar de forma autónoma")
    
    async def initialize(self) -> bool:
        """
        Inicializa el agente y todos sus componentes
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            logger.info("🚀 Inicializando TradingAgent...")
            
            # Inicializar componentes
            await self.decision_engine.initialize()
            await self.learning_system.initialize()
            await self.correction_mechanism.initialize()
            
            # Cargar memoria existente
            await self._load_agent_memory()
            
            # Verificar estado del sistema
            system_status = await self._check_system_status()
            if not system_status:
                logger.error("❌ Sistema no está listo para trading")
                return False
            
            self.state = AgentState.LEARNING
            logger.info("✅ TradingAgent inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando TradingAgent: {e}")
            self.state = AgentState.ERROR
            return False
    
    async def start_autonomous_trading(self) -> None:
        """
        Inicia el trading autónomo del agente
        
        El agente comenzará a:
        - Analizar datos de mercado en tiempo real
        - Tomar decisiones de trading independientes
        - Aprender de cada decisión y resultado
        - Autocorregirse cuando sea necesario
        """
        if self.state != AgentState.LEARNING:
            logger.error("❌ Agente no está en estado de aprendizaje")
            return
        
        logger.info("🎯 Iniciando trading autónomo...")
        self.is_active = True
        self.state = AgentState.TRADING
        
        try:
            # Loop principal del agente
            while self.is_active:
                await self._autonomous_trading_cycle()
                await asyncio.sleep(1)  # Pausa de 1 segundo entre ciclos
                
        except Exception as e:
            logger.error(f"❌ Error en trading autónomo: {e}")
            self.state = AgentState.ERROR
            await self._handle_error(e)
    
    async def _autonomous_trading_cycle(self) -> None:
        """
        Ciclo principal de trading autónomo
        
        Este método se ejecuta continuamente y:
        1. Analiza el estado actual del mercado
        2. Toma una decisión de trading
        3. Ejecuta la decisión si es apropiada
        4. Aprende del resultado
        5. Se autocorrige si es necesario
        """
        try:
            # 1. Obtener datos de mercado actuales
            market_data = await self._get_current_market_state()
            if not market_data:
                return
            
            # 2. Analizar situación con el motor de decisiones
            analysis = await self.decision_engine.analyze_market_state(market_data)
            
            # 3. Tomar decisión autónoma
            decision = await self.decision_engine.make_decision(analysis)
            if not decision:
                return
            
            # 4. Validar decisión con sistema de autocorrección
            corrected_decision = await self.correction_mechanism.validate_decision(decision, analysis)
            
            # 5. Ejecutar decisión si es válida
            if corrected_decision and corrected_decision.confidence >= self.confidence_threshold:
                await self._execute_decision(corrected_decision)
            
            # 6. Aprender del resultado (si hay trade)
            if self.current_position:
                await self._learn_from_trade_result()
            
            # 7. Verificar si necesita adaptación
            if self.decision_counter % self.adaptation_frequency == 0:
                await self._adapt_to_market_conditions()
            
            self.decision_counter += 1
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de trading: {e}")
            await self._handle_error(e)
    
    async def _get_current_market_state(self) -> Optional[Dict]:
        """
        Obtiene el estado actual del mercado
        
        Returns:
            Dict: Estado actual del mercado con todos los datos necesarios
        """
        try:
            # Obtener datos de klines
            klines = await data_collector.get_latest_klines("BTCUSDT", limit=100)
            if not klines:
                return None
            
            # Procesar datos para features
            features = data_preprocessor.prepare_prediction_data(klines)
            if features is None:
                return None
            
            # Obtener predicción del modelo
            prediction = predictor.predict(features)
            
            # Obtener balance actual
            balance = await order_manager.get_balance()
            
            # Obtener posición actual
            current_position = await order_manager.get_current_position("BTCUSDT")
            
            return {
                'klines': klines,
                'features': features,
                'prediction': prediction,
                'balance': balance,
                'current_position': current_position,
                'timestamp': datetime.now(),
                'market_regime': self._detect_market_regime(klines)
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del mercado: {e}")
            return None
    
    async def _execute_decision(self, decision: AgentDecision) -> None:
        """
        Ejecuta una decisión de trading
        
        Args:
            decision: Decisión a ejecutar
        """
        try:
            logger.info(f"🎯 Ejecutando decisión: {decision.action} (confianza: {decision.confidence:.2f})")
            
            # Preparar señal de trading
            signal = {
                'action': decision.action,
                'confidence': decision.confidence,
                'expected_return': decision.expected_return,
                'reasoning': decision.reasoning,
                'timestamp': decision.timestamp
            }
            
            # Ejecutar a través del execution engine
            result = await execution_engine.route_signal(signal)
            
            if result['success']:
                logger.info(f"✅ Decisión ejecutada: {decision.action}")
                self.last_decision = decision
                
                # Guardar en memoria
                self.memory.trade_history.append({
                    'decision': decision,
                    'result': result,
                    'timestamp': datetime.now()
                })
                
                # Actualizar métricas
                self.performance_tracker['total_trades'] += 1
                
            else:
                logger.warning(f"⚠️ Decisión no ejecutada: {result.get('reason', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando decisión: {e}")
    
    async def _learn_from_trade_result(self) -> None:
        """
        Aprende del resultado del último trade
        
        El agente analiza el resultado y actualiza su conocimiento
        """
        try:
            if not self.last_decision:
                return
            
            # Obtener resultado del trade
            trade_result = await order_manager.get_last_trade_result()
            if not trade_result:
                return
            
            # Crear episodio de aprendizaje
            learning_episode = {
                'decision': self.last_decision,
                'result': trade_result,
                'timestamp': datetime.now(),
                'success': trade_result.get('pnl', 0) > 0
            }
            
            # Aplicar aprendizaje
            await self.learning_system.learn_from_episode(learning_episode)
            
            # Actualizar memoria
            self.memory.learning_episodes.append(learning_episode)
            self.performance_tracker['learning_episodes'] += 1
            
            # Actualizar métricas de performance
            self._update_performance_metrics(trade_result)
            
            logger.info(f"🧠 Agente aprendió del trade: {'✅' if learning_episode['success'] else '❌'}")
            
        except Exception as e:
            logger.error(f"❌ Error en aprendizaje: {e}")
    
    async def _adapt_to_market_conditions(self) -> None:
        """
        Adapta el agente a las condiciones actuales del mercado
        
        El agente ajusta sus parámetros y estrategias basándose en:
        - Performance reciente
        - Cambios en el mercado
        - Patrones detectados
        """
        try:
            logger.info("🔄 Adaptando agente a condiciones del mercado...")
            
            # Analizar performance reciente
            recent_performance = self._analyze_recent_performance()
            
            # Detectar cambios en el mercado
            market_changes = await self._detect_market_changes()
            
            # Aplicar adaptaciones
            adaptations = await self.learning_system.adapt_to_conditions(
                recent_performance, market_changes
            )
            
            if adaptations:
                logger.info(f"🎯 Aplicadas {len(adaptations)} adaptaciones")
                self.memory.correction_actions.extend(adaptations)
                self.performance_tracker['corrections_applied'] += len(adaptations)
            
            self.state = AgentState.ADAPTING
            await asyncio.sleep(2)  # Pausa para adaptación
            self.state = AgentState.TRADING
            
        except Exception as e:
            logger.error(f"❌ Error en adaptación: {e}")
    
    def _detect_market_regime(self, klines: List[Dict]) -> str:
        """
        Detecta el régimen actual del mercado
        
        Args:
            klines: Datos de klines
            
        Returns:
            str: Régimen detectado (bull, bear, sideways, volatile)
        """
        try:
            if len(klines) < 20:
                return "unknown"
            
            # Calcular métricas básicas
            closes = [float(k['close']) for k in klines[-20:]]
            returns = np.diff(closes) / closes[:-1]
            
            # Volatilidad
            volatility = np.std(returns)
            
            # Tendencia
            trend = (closes[-1] - closes[0]) / closes[0]
            
            # Clasificar régimen
            if volatility > 0.05:  # 5% volatilidad
                return "volatile"
            elif trend > 0.02:  # 2% tendencia alcista
                return "bull"
            elif trend < -0.02:  # 2% tendencia bajista
                return "bear"
            else:
                return "sideways"
                
        except Exception as e:
            logger.error(f"❌ Error detectando régimen: {e}")
            return "unknown"
    
    def _analyze_recent_performance(self) -> Dict:
        """
        Analiza la performance reciente del agente
        
        Returns:
            Dict: Métricas de performance reciente
        """
        try:
            recent_trades = self.memory.trade_history[-20:]  # Últimos 20 trades
            
            if not recent_trades:
                return {}
            
            profitable = sum(1 for t in recent_trades if t.get('result', {}).get('pnl', 0) > 0)
            total_pnl = sum(t.get('result', {}).get('pnl', 0) for t in recent_trades)
            
            return {
                'win_rate': profitable / len(recent_trades),
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(recent_trades),
                'trade_count': len(recent_trades)
            }
            
        except Exception as e:
            logger.error(f"❌ Error analizando performance: {e}")
            return {}
    
    async def _detect_market_changes(self) -> Dict:
        """
        Detecta cambios significativos en el mercado
        
        Returns:
            Dict: Cambios detectados
        """
        try:
            # Obtener datos recientes
            recent_klines = await data_collector.get_latest_klines("BTCUSDT", limit=50)
            if not recent_klines:
                return {}
            
            # Comparar con datos históricos
            historical_klines = await data_collector.get_latest_klines("BTCUSDT", limit=200)
            if not historical_klines:
                return {}
            
            # Detectar cambios en volatilidad, volumen, etc.
            recent_vol = np.std([float(k['close']) for k in recent_klines[-10:]])
            historical_vol = np.std([float(k['close']) for k in historical_klines[-50:])
            
            return {
                'volatility_change': recent_vol / historical_vol if historical_vol > 0 else 1.0,
                'volume_change': self._calculate_volume_change(recent_klines, historical_klines),
                'trend_change': self._calculate_trend_change(recent_klines, historical_klines)
            }
            
        except Exception as e:
            logger.error(f"❌ Error detectando cambios: {e}")
            return {}
    
    def _calculate_volume_change(self, recent: List, historical: List) -> float:
        """Calcula cambio en volumen"""
        try:
            recent_vol = np.mean([float(k['volume']) for k in recent[-10:]])
            historical_vol = np.mean([float(k['volume']) for k in historical[-50:]])
            return recent_vol / historical_vol if historical_vol > 0 else 1.0
        except:
            return 1.0
    
    def _calculate_trend_change(self, recent: List, historical: List) -> float:
        """Calcula cambio en tendencia"""
        try:
            recent_trend = (float(recent[-1]['close']) - float(recent[0]['close'])) / float(recent[0]['close'])
            historical_trend = (float(historical[-1]['close']) - float(historical[0]['close'])) / float(historical[0]['close'])
            return recent_trend - historical_trend
        except:
            return 0.0
    
    def _update_performance_metrics(self, trade_result: Dict) -> None:
        """
        Actualiza las métricas de performance del agente
        
        Args:
            trade_result: Resultado del trade
        """
        try:
            pnl = trade_result.get('pnl', 0)
            
            if pnl > 0:
                self.performance_tracker['profitable_trades'] += 1
            
            self.performance_tracker['total_pnl'] += pnl
            
            # Calcular accuracy
            total_trades = self.performance_tracker['total_trades']
            if total_trades > 0:
                self.performance_tracker['accuracy'] = (
                    self.performance_tracker['profitable_trades'] / total_trades
                )
            
            # Actualizar drawdown
            if pnl < 0:
                current_dd = abs(pnl)
                if current_dd > self.performance_tracker['max_drawdown']:
                    self.performance_tracker['max_drawdown'] = current_dd
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas: {e}")
    
    async def _load_agent_memory(self) -> None:
        """Carga la memoria persistente del agente"""
        try:
            # TODO: Implementar carga desde base de datos
            logger.info("📚 Cargando memoria del agente...")
            pass
        except Exception as e:
            logger.error(f"❌ Error cargando memoria: {e}")
    
    async def _check_system_status(self) -> bool:
        """
        Verifica que todos los componentes del sistema estén listos
        
        Returns:
            bool: True si el sistema está listo
        """
        try:
            # Verificar componentes principales
            components = [
                ('predictor', predictor),
                ('execution_engine', execution_engine),
                ('risk_manager', risk_manager),
                ('order_manager', order_manager)
            ]
            
            for name, component in components:
                if not component:
                    logger.error(f"❌ Componente {name} no disponible")
                    return False
            
            logger.info("✅ Todos los componentes del sistema están listos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verificando sistema: {e}")
            return False
    
    async def _handle_error(self, error: Exception) -> None:
        """
        Maneja errores del agente
        
        Args:
            error: Error ocurrido
        """
        logger.error(f"🚨 Error crítico en agente: {error}")
        self.state = AgentState.ERROR
        
        # Intentar recuperación automática
        try:
            await self.correction_mechanism.handle_critical_error(error)
            self.state = AgentState.LEARNING
        except Exception as recovery_error:
            logger.error(f"❌ Error en recuperación: {recovery_error}")
            self.is_active = False
    
    async def stop_trading(self) -> None:
        """Detiene el trading del agente"""
        logger.info("🛑 Deteniendo trading del agente...")
        self.is_active = False
        self.state = AgentState.PAUSED
        
        # Guardar estado actual
        await self._save_agent_state()
    
    async def _save_agent_state(self) -> None:
        """Guarda el estado actual del agente"""
        try:
            # TODO: Implementar guardado en base de datos
            logger.info("💾 Guardando estado del agente...")
            pass
        except Exception as e:
            logger.error(f"❌ Error guardando estado: {e}")
    
    def get_agent_status(self) -> Dict:
        """
        Obtiene el estado actual del agente
        
        Returns:
            Dict: Estado completo del agente
        """
        return {
            'state': self.state.value,
            'is_active': self.is_active,
            'performance': self.performance_tracker,
            'memory_size': {
                'trades': len(self.memory.trade_history),
                'predictions': len(self.memory.prediction_history),
                'episodes': len(self.memory.learning_episodes)
            },
            'last_decision': self.last_decision,
            'current_position': self.current_position
        }
    
    def get_agent_insights(self) -> Dict:
        """
        Obtiene insights del agente sobre su comportamiento
        
        Returns:
            Dict: Insights y análisis del agente
        """
        try:
            recent_performance = self._analyze_recent_performance()
            
            return {
                'performance_analysis': recent_performance,
                'learning_progress': {
                    'episodes_learned': self.performance_tracker['learning_episodes'],
                    'corrections_applied': self.performance_tracker['corrections_applied']
                },
                'market_adaptation': {
                    'regimes_detected': len(self.memory.market_regimes),
                    'adaptations_made': len(self.memory.correction_actions)
                },
                'confidence_levels': self._analyze_confidence_patterns(),
                'recommendations': self._generate_recommendations()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando insights: {e}")
            return {}
    
    def _analyze_confidence_patterns(self) -> Dict:
        """Analiza patrones de confianza del agente"""
        try:
            recent_decisions = [t['decision'] for t in self.memory.trade_history[-20:]]
            if not recent_decisions:
                return {}
            
            confidences = [d.confidence for d in recent_decisions]
            
            return {
                'avg_confidence': np.mean(confidences),
                'min_confidence': np.min(confidences),
                'max_confidence': np.max(confidences),
                'confidence_trend': np.polyfit(range(len(confidences)), confidences, 1)[0]
            }
        except:
            return {}
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en el análisis del agente"""
        recommendations = []
        
        try:
            performance = self._analyze_recent_performance()
            
            if performance.get('win_rate', 0) < 0.5:
                recommendations.append("Considerar reducir la frecuencia de trading")
            
            if performance.get('avg_pnl', 0) < 0:
                recommendations.append("Revisar estrategia de entrada y salida")
            
            if self.performance_tracker['max_drawdown'] > 0.1:
                recommendations.append("Implementar stop-loss más estricto")
            
            if len(self.memory.correction_actions) > 10:
                recommendations.append("El agente está aprendiendo activamente - continuar monitoreo")
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones: {e}")
        
        return recommendations
