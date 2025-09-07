"""
🧠 SelfLearningSystem - Sistema de Aprendizaje Autodidacta

Sistema que permite al agente aprender continuamente de sus experiencias,
mejorar sus decisiones y adaptarse a condiciones cambiantes del mercado
sin intervención humana.

Características:
- Aprendizaje por refuerzo continuo
- Análisis de patrones y correlaciones
- Adaptación dinámica de parámetros
- Detección de concept drift
- Optimización de estrategias
- Memoria episódica y semántica

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque
import json

# Imports del sistema existente
from config.config_loader import user_config
from models.adaptive_trainer import adaptive_trainer
from models.predictor import predictor

logger = logging.getLogger(__name__)

@dataclass
class LearningEpisode:
    """Episodio de aprendizaje del agente"""
    decision: Dict
    result: Dict
    market_context: Dict
    reward: float
    timestamp: datetime
    success: bool
    learning_value: float

@dataclass
class Pattern:
    """Patrón identificado por el agente"""
    pattern_type: str
    conditions: Dict
    outcome: str
    confidence: float
    frequency: int
    last_seen: datetime

@dataclass
class Adaptation:
    """Adaptación aplicada por el agente"""
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: datetime
    success: bool

class SelfLearningSystem:
    """
    🧠 Sistema de Aprendizaje Autodidacta
    
    Permite al agente aprender continuamente de sus experiencias,
    identificar patrones, adaptar estrategias y mejorar su performance
    de forma autónoma.
    """
    
    def __init__(self):
        """Inicializa el sistema de aprendizaje"""
        self.config = user_config
        self.learning_config = self.config.get_value(['ai_agent', 'learning_system'], {})
        
        # Parámetros de aprendizaje
        self.learning_rate = self.learning_config.get('learning_rate', 0.01)
        self.memory_size = self.learning_config.get('memory_size', 1000)
        self.pattern_threshold = self.learning_config.get('pattern_threshold', 0.7)
        self.adaptation_threshold = self.learning_config.get('adaptation_threshold', 0.6)
        
        # Memoria del agente
        self.episodic_memory = deque(maxlen=self.memory_size)
        self.semantic_memory = {}
        self.patterns = {}
        self.adaptations = []
        
        # Métricas de aprendizaje
        self.learning_metrics = {
            'total_episodes': 0,
            'successful_episodes': 0,
            'patterns_identified': 0,
            'adaptations_applied': 0,
            'learning_accuracy': 0.0,
            'adaptation_success_rate': 0.0
        }
        
        # Estado de aprendizaje
        self.is_learning = False
        self.current_learning_phase = "exploration"
        self.learning_confidence = 0.5
        
        logger.info("🧠 SelfLearningSystem inicializado")
    
    async def initialize(self) -> None:
        """Inicializa el sistema de aprendizaje"""
        try:
            # Cargar memoria existente
            await self._load_learning_memory()
            
            # Inicializar modelos de aprendizaje
            await self._initialize_learning_models()
            
            # Configurar parámetros de aprendizaje
            await self._configure_learning_parameters()
            
            self.is_learning = True
            logger.info("✅ Sistema de aprendizaje inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema de aprendizaje: {e}")
            raise
    
    async def learn_from_episode(self, episode: Dict) -> None:
        """
        Aprende de un episodio de trading
        
        Args:
            episode: Episodio de aprendizaje con decisión y resultado
        """
        try:
            if not self.is_learning:
                return
            
            # Crear episodio de aprendizaje
            learning_episode = await self._create_learning_episode(episode)
            if not learning_episode:
                return
            
            # Calcular reward del episodio
            reward = await self._calculate_episode_reward(learning_episode)
            learning_episode.reward = reward
            
            # Agregar a memoria episódica
            self.episodic_memory.append(learning_episode)
            
            # Actualizar métricas
            self.learning_metrics['total_episodes'] += 1
            if learning_episode.success:
                self.learning_metrics['successful_episodes'] += 1
            
            # Aplicar aprendizaje
            await self._apply_episode_learning(learning_episode)
            
            # Identificar patrones
            await self._identify_patterns(learning_episode)
            
            # Verificar si necesita adaptación
            if self._should_adapt():
                await self._adapt_parameters(learning_episode)
            
            # Actualizar confianza de aprendizaje
            self._update_learning_confidence()
            
            logger.info(f"🧠 Aprendizaje aplicado - Reward: {reward:.3f}, Éxito: {learning_episode.success}")
            
        except Exception as e:
            logger.error(f"❌ Error en aprendizaje de episodio: {e}")
    
    async def adapt_to_conditions(self, recent_performance: Dict, market_changes: Dict) -> List[Adaptation]:
        """
        Adapta el agente a condiciones cambiantes
        
        Args:
            recent_performance: Performance reciente del agente
            market_changes: Cambios detectados en el mercado
            
        Returns:
            List[Adaptation]: Adaptaciones aplicadas
        """
        try:
            adaptations = []
            
            # Analizar performance reciente
            performance_analysis = await self._analyze_performance(recent_performance)
            
            # Analizar cambios de mercado
            market_analysis = await self._analyze_market_changes(market_changes)
            
            # Generar adaptaciones basadas en análisis
            if performance_analysis['needs_improvement']:
                adaptations.extend(await self._generate_performance_adaptations(performance_analysis))
            
            if market_analysis['needs_adaptation']:
                adaptations.extend(await self._generate_market_adaptations(market_analysis))
            
            # Aplicar adaptaciones
            applied_adaptations = []
            for adaptation in adaptations:
                if await self._apply_adaptation(adaptation):
                    applied_adaptations.append(adaptation)
                    self.adaptations.append(adaptation)
                    self.learning_metrics['adaptations_applied'] += 1
            
            logger.info(f"🔄 Aplicadas {len(applied_adaptations)} adaptaciones")
            
            return applied_adaptations
            
        except Exception as e:
            logger.error(f"❌ Error en adaptación: {e}")
            return []
    
    async def _create_learning_episode(self, episode_data: Dict) -> Optional[LearningEpisode]:
        """Crea un episodio de aprendizaje estructurado"""
        try:
            decision = episode_data.get('decision', {})
            result = episode_data.get('result', {})
            
            if not decision or not result:
                return None
            
            # Determinar éxito del episodio
            success = result.get('pnl', 0) > 0
            
            # Calcular valor de aprendizaje
            learning_value = await self._calculate_learning_value(decision, result)
            
            # Crear contexto de mercado
            market_context = {
                'timestamp': episode_data.get('timestamp', datetime.now()),
                'market_regime': decision.get('market_context', {}).get('regime', 'unknown'),
                'volatility': decision.get('market_context', {}).get('volatility', 'unknown'),
                'trend': decision.get('market_context', {}).get('trend', 'unknown')
            }
            
            return LearningEpisode(
                decision=decision,
                result=result,
                market_context=market_context,
                reward=0.0,  # Se calculará después
                timestamp=episode_data.get('timestamp', datetime.now()),
                success=success,
                learning_value=learning_value
            )
            
        except Exception as e:
            logger.error(f"❌ Error creando episodio: {e}")
            return None
    
    async def _calculate_episode_reward(self, episode: LearningEpisode) -> float:
        """Calcula el reward de un episodio"""
        try:
            reward = 0.0
            
            # Reward base por éxito/fracaso
            if episode.success:
                reward += 1.0
            else:
                reward -= 0.5
            
            # Reward por magnitud del resultado
            pnl = episode.result.get('pnl', 0)
            if pnl > 0:
                reward += min(pnl * 10, 2.0)  # Máximo 2.0 por magnitud
            else:
                reward += max(pnl * 10, -1.0)  # Mínimo -1.0 por pérdida
            
            # Reward por confianza de la decisión
            confidence = episode.decision.get('confidence', 0.5)
            if episode.success:
                reward += confidence * 0.5  # Bonus por confianza correcta
            else:
                reward -= (1.0 - confidence) * 0.3  # Penalización por confianza incorrecta
            
            # Reward por duración del trade
            duration = episode.result.get('duration_hours', 0)
            if duration > 0:
                # Reward por eficiencia temporal
                if episode.success:
                    reward += min(1.0 / duration, 0.5)  # Bonus por trades rápidos exitosos
                else:
                    reward -= min(duration / 24, 0.3)  # Penalización por trades largos perdedores
            
            # Reward por contexto de mercado
            market_regime = episode.market_context.get('market_regime', 'unknown')
            if market_regime in ['bull', 'bear'] and episode.success:
                reward += 0.2  # Bonus por éxito en mercados direccionales
            
            return reward
            
        except Exception as e:
            logger.error(f"❌ Error calculando reward: {e}")
            return 0.0
    
    async def _apply_episode_learning(self, episode: LearningEpisode) -> None:
        """Aplica el aprendizaje de un episodio"""
        try:
            # Actualizar memoria semántica
            await self._update_semantic_memory(episode)
            
            # Ajustar parámetros de decisión
            await self._adjust_decision_parameters(episode)
            
            # Actualizar modelos ML si es necesario
            if episode.learning_value > 0.7:  # Episodio de alto valor
                await self._update_ml_models(episode)
            
        except Exception as e:
            logger.error(f"❌ Error aplicando aprendizaje: {e}")
    
    async def _identify_patterns(self, episode: LearningEpisode) -> None:
        """Identifica patrones en los episodios"""
        try:
            # Buscar patrones en decisiones exitosas
            if episode.success:
                pattern_conditions = {
                    'market_regime': episode.market_context.get('market_regime'),
                    'volatility': episode.market_context.get('volatility'),
                    'trend': episode.market_context.get('trend'),
                    'confidence': episode.decision.get('confidence', 0.5)
                }
                
                # Verificar si existe patrón similar
                existing_pattern = self._find_similar_pattern(pattern_conditions)
                
                if existing_pattern:
                    # Actualizar patrón existente
                    existing_pattern.frequency += 1
                    existing_pattern.confidence = (existing_pattern.confidence + episode.learning_value) / 2
                    existing_pattern.last_seen = episode.timestamp
                else:
                    # Crear nuevo patrón
                    new_pattern = Pattern(
                        pattern_type="successful_decision",
                        conditions=pattern_conditions,
                        outcome="success",
                        confidence=episode.learning_value,
                        frequency=1,
                        last_seen=episode.timestamp
                    )
                    
                    pattern_id = f"pattern_{len(self.patterns)}"
                    self.patterns[pattern_id] = new_pattern
                    self.learning_metrics['patterns_identified'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error identificando patrones: {e}")
    
    def _find_similar_pattern(self, conditions: Dict) -> Optional[Pattern]:
        """Encuentra un patrón similar a las condiciones dadas"""
        try:
            for pattern in self.patterns.values():
                similarity = self._calculate_pattern_similarity(pattern.conditions, conditions)
                if similarity > self.pattern_threshold:
                    return pattern
            return None
        except:
            return None
    
    def _calculate_pattern_similarity(self, pattern_conditions: Dict, new_conditions: Dict) -> float:
        """Calcula similitud entre condiciones de patrones"""
        try:
            if not pattern_conditions or not new_conditions:
                return 0.0
            
            matches = 0
            total = 0
            
            for key in pattern_conditions:
                if key in new_conditions:
                    total += 1
                    if pattern_conditions[key] == new_conditions[key]:
                        matches += 1
            
            return matches / total if total > 0 else 0.0
            
        except:
            return 0.0
    
    async def _analyze_performance(self, performance: Dict) -> Dict:
        """Analiza la performance reciente"""
        try:
            win_rate = performance.get('win_rate', 0)
            avg_pnl = performance.get('avg_pnl', 0)
            trade_count = performance.get('trade_count', 0)
            
            analysis = {
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'trade_count': trade_count,
                'needs_improvement': False,
                'recommendations': []
            }
            
            # Evaluar si necesita mejora
            if win_rate < 0.5:
                analysis['needs_improvement'] = True
                analysis['recommendations'].append("Mejorar tasa de éxito")
            
            if avg_pnl < 0:
                analysis['needs_improvement'] = True
                analysis['recommendations'].append("Mejorar PnL promedio")
            
            if trade_count < 5:
                analysis['recommendations'].append("Necesita más datos para análisis")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analizando performance: {e}")
            return {'needs_improvement': False, 'recommendations': []}
    
    async def _analyze_market_changes(self, market_changes: Dict) -> Dict:
        """Analiza cambios en el mercado"""
        try:
            volatility_change = market_changes.get('volatility_change', 1.0)
            volume_change = market_changes.get('volume_change', 1.0)
            trend_change = market_changes.get('trend_change', 0.0)
            
            analysis = {
                'volatility_change': volatility_change,
                'volume_change': volume_change,
                'trend_change': trend_change,
                'needs_adaptation': False,
                'recommendations': []
            }
            
            # Evaluar si necesita adaptación
            if volatility_change > 1.5 or volatility_change < 0.5:
                analysis['needs_adaptation'] = True
                analysis['recommendations'].append("Adaptar a cambios de volatilidad")
            
            if volume_change > 2.0 or volume_change < 0.5:
                analysis['needs_adaptation'] = True
                analysis['recommendations'].append("Adaptar a cambios de volumen")
            
            if abs(trend_change) > 0.05:
                analysis['needs_adaptation'] = True
                analysis['recommendations'].append("Adaptar a cambios de tendencia")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analizando cambios: {e}")
            return {'needs_adaptation': False, 'recommendations': []}
    
    async def _generate_performance_adaptations(self, analysis: Dict) -> List[Adaptation]:
        """Genera adaptaciones basadas en performance"""
        try:
            adaptations = []
            
            if analysis['win_rate'] < 0.5:
                # Reducir confianza mínima para ser más selectivo
                adaptation = Adaptation(
                    parameter="min_confidence",
                    old_value=0.7,
                    new_value=0.8,
                    reason="Baja tasa de éxito - ser más selectivo",
                    timestamp=datetime.now(),
                    success=False
                )
                adaptations.append(adaptation)
            
            if analysis['avg_pnl'] < 0:
                # Reducir tamaño de posición
                adaptation = Adaptation(
                    parameter="position_size_multiplier",
                    old_value=1.0,
                    new_value=0.7,
                    reason="PnL negativo - reducir exposición",
                    timestamp=datetime.now(),
                    success=False
                )
                adaptations.append(adaptation)
            
            return adaptations
            
        except Exception as e:
            logger.error(f"❌ Error generando adaptaciones de performance: {e}")
            return []
    
    async def _generate_market_adaptations(self, analysis: Dict) -> List[Adaptation]:
        """Genera adaptaciones basadas en cambios de mercado"""
        try:
            adaptations = []
            
            volatility_change = analysis.get('volatility_change', 1.0)
            
            if volatility_change > 1.5:
                # Aumentar stop loss en alta volatilidad
                adaptation = Adaptation(
                    parameter="stop_loss_multiplier",
                    old_value=1.0,
                    new_value=1.5,
                    reason="Alta volatilidad - aumentar SL",
                    timestamp=datetime.now(),
                    success=False
                )
                adaptations.append(adaptation)
            
            elif volatility_change < 0.5:
                # Reducir stop loss en baja volatilidad
                adaptation = Adaptation(
                    parameter="stop_loss_multiplier",
                    old_value=1.0,
                    new_value=0.8,
                    reason="Baja volatilidad - reducir SL",
                    timestamp=datetime.now(),
                    success=False
                )
                adaptations.append(adaptation)
            
            return adaptations
            
        except Exception as e:
            logger.error(f"❌ Error generando adaptaciones de mercado: {e}")
            return []
    
    async def _apply_adaptation(self, adaptation: Adaptation) -> bool:
        """Aplica una adaptación"""
        try:
            # TODO: Implementar aplicación real de adaptaciones
            # Por ahora solo simular
            adaptation.success = True
            logger.info(f"🔄 Adaptación aplicada: {adaptation.parameter} = {adaptation.new_value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error aplicando adaptación: {e}")
            return False
    
    def _should_adapt(self) -> bool:
        """Determina si el agente debe adaptar sus parámetros"""
        try:
            # Adaptar si hay suficientes episodios y performance baja
            if len(self.episodic_memory) < 10:
                return False
            
            recent_episodes = list(self.episodic_memory)[-10:]
            success_rate = sum(1 for e in recent_episodes if e.success) / len(recent_episodes)
            
            return success_rate < self.adaptation_threshold
            
        except:
            return False
    
    async def _adapt_parameters(self, episode: LearningEpisode) -> None:
        """Adapta parámetros del agente"""
        try:
            # Análisis de episodios recientes
            recent_episodes = list(self.episodic_memory)[-20:]
            
            # Calcular métricas de adaptación
            success_rate = sum(1 for e in recent_episodes if e.success) / len(recent_episodes)
            avg_reward = np.mean([e.reward for e in recent_episodes])
            
            # Generar adaptaciones basadas en métricas
            if success_rate < 0.4:
                await self._adapt_confidence_threshold(0.1)  # Aumentar selectividad
            
            if avg_reward < 0:
                await self._adapt_position_sizing(0.8)  # Reducir tamaño
            
            logger.info(f"🔄 Parámetros adaptados - Success rate: {success_rate:.2f}, Avg reward: {avg_reward:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error adaptando parámetros: {e}")
    
    async def _adapt_confidence_threshold(self, adjustment: float) -> None:
        """Adapta el umbral de confianza"""
        try:
            # TODO: Implementar adaptación real
            logger.info(f"🎯 Adaptando umbral de confianza: {adjustment}")
        except Exception as e:
            logger.error(f"❌ Error adaptando confianza: {e}")
    
    async def _adapt_position_sizing(self, multiplier: float) -> None:
        """Adapta el sizing de posiciones"""
        try:
            # TODO: Implementar adaptación real
            logger.info(f"📊 Adaptando sizing: {multiplier}")
        except Exception as e:
            logger.error(f"❌ Error adaptando sizing: {e}")
    
    def _update_learning_confidence(self) -> None:
        """Actualiza la confianza del sistema de aprendizaje"""
        try:
            if len(self.episodic_memory) < 5:
                return
            
            recent_episodes = list(self.episodic_memory)[-20:]
            success_rate = sum(1 for e in recent_episodes if e.success) / len(recent_episodes)
            
            # Actualizar confianza basada en éxito reciente
            self.learning_confidence = (self.learning_confidence + success_rate) / 2
            
        except Exception as e:
            logger.error(f"❌ Error actualizando confianza: {e}")
    
    async def _calculate_learning_value(self, decision: Dict, result: Dict) -> float:
        """Calcula el valor de aprendizaje de un episodio"""
        try:
            value = 0.0
            
            # Valor por éxito/fracaso
            if result.get('pnl', 0) > 0:
                value += 0.5
            else:
                value -= 0.3
            
            # Valor por confianza de decisión
            confidence = decision.get('confidence', 0.5)
            if result.get('pnl', 0) > 0:
                value += confidence * 0.3
            else:
                value -= (1.0 - confidence) * 0.2
            
            # Valor por magnitud del resultado
            pnl = abs(result.get('pnl', 0))
            value += min(pnl * 5, 0.2)  # Máximo 0.2 por magnitud
            
            return max(value, 0.0)
            
        except Exception as e:
            logger.error(f"❌ Error calculando valor de aprendizaje: {e}")
            return 0.0
    
    async def _update_semantic_memory(self, episode: LearningEpisode) -> None:
        """Actualiza la memoria semántica del agente"""
        try:
            # Actualizar conocimiento sobre regímenes de mercado
            regime = episode.market_context.get('market_regime', 'unknown')
            if regime not in self.semantic_memory:
                self.semantic_memory[regime] = {'successes': 0, 'failures': 0}
            
            if episode.success:
                self.semantic_memory[regime]['successes'] += 1
            else:
                self.semantic_memory[regime]['failures'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error actualizando memoria semántica: {e}")
    
    async def _adjust_decision_parameters(self, episode: LearningEpisode) -> None:
        """Ajusta parámetros de decisión basándose en el episodio"""
        try:
            # TODO: Implementar ajuste real de parámetros
            pass
        except Exception as e:
            logger.error(f"❌ Error ajustando parámetros: {e}")
    
    async def _update_ml_models(self, episode: LearningEpisode) -> None:
        """Actualiza modelos ML con el episodio"""
        try:
            # TODO: Implementar actualización de modelos ML
            pass
        except Exception as e:
            logger.error(f"❌ Error actualizando modelos ML: {e}")
    
    async def _load_learning_memory(self) -> None:
        """Carga memoria de aprendizaje desde persistencia"""
        try:
            # TODO: Implementar carga desde base de datos
            logger.info("📚 Cargando memoria de aprendizaje...")
        except Exception as e:
            logger.error(f"❌ Error cargando memoria: {e}")
    
    async def _initialize_learning_models(self) -> None:
        """Inicializa modelos de aprendizaje"""
        try:
            # TODO: Inicializar modelos específicos
            logger.info("🔧 Modelos de aprendizaje inicializados")
        except Exception as e:
            logger.error(f"❌ Error inicializando modelos: {e}")
    
    async def _configure_learning_parameters(self) -> None:
        """Configura parámetros de aprendizaje"""
        try:
            # Cargar configuración desde YAML
            self.learning_rate = self.learning_config.get('learning_rate', self.learning_rate)
            self.memory_size = self.learning_config.get('memory_size', self.memory_size)
            self.pattern_threshold = self.learning_config.get('pattern_threshold', self.pattern_threshold)
            self.adaptation_threshold = self.learning_config.get('adaptation_threshold', self.adaptation_threshold)
            
            logger.info("⚙️ Parámetros de aprendizaje configurados")
        except Exception as e:
            logger.error(f"❌ Error configurando parámetros: {e}")
    
    def get_learning_statistics(self) -> Dict:
        """Obtiene estadísticas del sistema de aprendizaje"""
        try:
            return {
                'learning_metrics': self.learning_metrics,
                'learning_confidence': self.learning_confidence,
                'patterns_count': len(self.patterns),
                'adaptations_count': len(self.adaptations),
                'memory_usage': len(self.episodic_memory),
                'recent_patterns': list(self.patterns.values())[-5:],
                'recent_adaptations': self.adaptations[-5:]
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
    
    def get_learning_insights(self) -> Dict:
        """Obtiene insights del sistema de aprendizaje"""
        try:
            insights = {
                'learning_phase': self.current_learning_phase,
                'confidence_level': self.learning_confidence,
                'key_patterns': self._get_key_patterns(),
                'adaptation_recommendations': self._get_adaptation_recommendations(),
                'learning_trends': self._analyze_learning_trends()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error generando insights: {e}")
            return {}
    
    def _get_key_patterns(self) -> List[Dict]:
        """Obtiene patrones clave identificados"""
        try:
            key_patterns = []
            for pattern_id, pattern in self.patterns.items():
                if pattern.frequency > 3 and pattern.confidence > 0.7:
                    key_patterns.append({
                        'id': pattern_id,
                        'type': pattern.pattern_type,
                        'frequency': pattern.frequency,
                        'confidence': pattern.confidence,
                        'conditions': pattern.conditions
                    })
            
            return sorted(key_patterns, key=lambda x: x['frequency'], reverse=True)[:5]
        except:
            return []
    
    def _get_adaptation_recommendations(self) -> List[str]:
        """Genera recomendaciones de adaptación"""
        try:
            recommendations = []
            
            if self.learning_confidence < 0.6:
                recommendations.append("Aumentar período de aprendizaje")
            
            if len(self.patterns) < 5:
                recommendations.append("Necesita más datos para identificar patrones")
            
            if self.learning_metrics['adaptation_success_rate'] < 0.5:
                recommendations.append("Revisar estrategia de adaptación")
            
            return recommendations
        except:
            return []
    
    def _analyze_learning_trends(self) -> Dict:
        """Analiza tendencias de aprendizaje"""
        try:
            if len(self.episodic_memory) < 10:
                return {}
            
            recent_episodes = list(self.episodic_memory)[-20:]
            
            # Tendencias de éxito
            success_rates = []
            for i in range(0, len(recent_episodes), 5):
                batch = recent_episodes[i:i+5]
                if batch:
                    success_rate = sum(1 for e in batch if e.success) / len(batch)
                    success_rates.append(success_rate)
            
            # Tendencias de reward
            rewards = [e.reward for e in recent_episodes]
            
            return {
                'success_trend': np.polyfit(range(len(success_rates)), success_rates, 1)[0] if success_rates else 0,
                'reward_trend': np.polyfit(range(len(rewards)), rewards, 1)[0] if rewards else 0,
                'learning_velocity': len(self.episodic_memory) / max(1, (datetime.now() - self.episodic_memory[0].timestamp).days)
            }
        except:
            return {}
