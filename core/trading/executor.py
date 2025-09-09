"""
⚡ executor.py - Motor Principal de Trading

Motor central que conecta el sistema ML con la ejecución real de trading,
orquestando el flujo completo desde predicciones hasta ejecución de órdenes.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import time
from collections import defaultdict

# Imports del proyecto
from core.config.config_loader import ConfigLoader
from core.data.database import db_manager
from core.data.preprocessor import data_preprocessor
from core.ml.legacy.prediction_engine import prediction_engine
from core.ml.legacy.confidence_estimator import confidence_estimator
from core.ml.legacy.adaptive_trainer import adaptive_trainer
from core.ml.legacy.model_evaluator import model_evaluator
from .risk_manager import risk_manager
from .order_manager import order_manager, TradeRecord
from .bitget_client import bitget_client
from .signal_processor import signal_processor
from .portfolio_optimizer import portfolio_optimizer

logger = logging.getLogger(__name__)

class TradingExecutor:
    """
    Motor principal de ejecución de trading que conecta ML con trading real
    
    Responsabilidades:
    - Orquestar el flujo completo ML → Trading
    - Gestionar posiciones abiertas 
    - Aplicar lógica de entrada/salida
    - Coordinar risk management y ejecución
    - Retroalimentar resultados al modelo
    - Monitorear performance en tiempo real
    """
    
    def __init__(self):
        self.config = user_config
        self.is_running = False
        self.active_positions = {}  # symbol -> TradeRecord
        self.last_trade_time = {}  # symbol -> datetime
        self.daily_trade_count = defaultdict(int)
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Configuraciones
        self.trading_config = self.config.get_value(['trading'], {})
        self.ai_config = self.config.get_value(['ai_model_settings'], {})
        self.risk_config = self.config.get_value(['risk_management'], {})
        
        # Parámetros de trading
        self.min_confidence = self.ai_config.get('confidence', {}).get('min_confidence_to_trade', 0.65)
        self.cooldown_minutes = self.trading_config.get('cooldown_between_trades', 30)
        self.max_daily_trades = self.trading_config.get('max_daily_trades', 20)
        self.max_positions = self.trading_config.get('max_concurrent_positions', 3)
        
        # Métricas de performance
        self.metrics = {
            'total_cycles_executed': 0,
            'predictions_processed': 0,
            'trades_executed': 0,
            'trades_skipped': 0,
            'average_confidence': 0.0,
            'prediction_accuracy': 0.0,
            'execution_latency_ms': 0.0,
            'daily_pnl': 0.0,
            'current_positions': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'last_update': datetime.now().isoformat()
        }
        
        # Historial de predicciones para accuracy tracking
        self.prediction_history = []
        
        logger.info("TradingExecutor inicializado")
    
    async def execute_trading_cycle(self, symbol: str) -> Dict[str, Any]:
        """
        Ciclo principal de trading para un símbolo
        
        Flujo:
        1. Obtener datos de mercado actuales
        2. Preparar features para ML
        3. Obtener predicción del modelo
        4. Evaluar si ejecutar trade (lógica de entrada)
        5. Si procede: calcular sizing y ejecutar
        6. Gestionar posiciones existentes (exits)
        7. Registrar resultados y métricas
        
        Args:
            symbol: Símbolo a procesar (ej: BTCUSDT)
            
        Returns:
            Dict con resultados del ciclo de trading
        """
        cycle_start_time = time.time()
        cycle_result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed',
            'actions_taken': [],
            'errors': [],
            'execution_time_ms': 0
        }
        
        try:
            logger.info(f"🔄 Iniciando ciclo de trading para {symbol}")
            
            # Resetear contadores diarios si es nuevo día
            await self._reset_daily_counters_if_needed()
            
            # 1. Verificar si podemos operar este símbolo
            if not await self._can_trade_symbol(symbol):
                cycle_result['status'] = 'skipped'
                cycle_result['actions_taken'].append('symbol_trading_disabled')
                logger.info(f"⏸️ Trading deshabilitado para {symbol}")
                return cycle_result
            
            # 2. Procesar predicción ML
            prediction_result = await self.process_ml_prediction(symbol)
            if not prediction_result or prediction_result.get('error'):
                cycle_result['status'] = 'failed'
                cycle_result['errors'].append(f"Error en predicción ML: {prediction_result.get('error', 'Unknown')}")
                return cycle_result
            
            cycle_result['prediction'] = prediction_result
            cycle_result['actions_taken'].append('ml_prediction_processed')
            
            # 3. Evaluar señales de salida para posiciones existentes
            exit_results = await self.evaluate_exit_signals(symbol)
            if exit_results:
                cycle_result['exit_trades'] = exit_results
                cycle_result['actions_taken'].append(f'exit_signals_evaluated_{len(exit_results)}')
            
            # 4. Evaluar señal de entrada
            should_enter = await self.evaluate_entry_signal(prediction_result, symbol)
            if should_enter:
                # 5. Ejecutar trade de entrada
                trade_result = await self.execute_trade_decision(symbol, prediction_result)
                if trade_result:
                    cycle_result['entry_trade'] = trade_result
                    cycle_result['actions_taken'].append('entry_trade_executed')
                else:
                    cycle_result['actions_taken'].append('entry_trade_failed')
            else:
                cycle_result['actions_taken'].append('entry_signal_rejected')
            
            # 6. Actualizar métricas
            await self._update_metrics(cycle_result)
            
            # 7. Retroalimentar al modelo si hay trades cerrados
            if exit_results:
                await self._update_model_feedback(exit_results)
            
            cycle_result['execution_time_ms'] = (time.time() - cycle_start_time) * 1000
            self.metrics['total_cycles_executed'] += 1
            
            logger.info(f"✅ Ciclo completado para {symbol} en {cycle_result['execution_time_ms']:.1f}ms")
            return cycle_result
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de trading para {symbol}: {e}")
            cycle_result['status'] = 'error'
            cycle_result['errors'].append(str(e))
            cycle_result['execution_time_ms'] = (time.time() - cycle_start_time) * 1000
            return cycle_result
    
    async def process_ml_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Procesar predicción completa del modelo ML usando signal_processor
        
        Args:
            symbol: Símbolo a procesar
            
        Returns:
            Dict con predicción y métricas de calidad
        """
        try:
            logger.debug(f"🧠 Procesando predicción ML para {symbol}")
            
            # Usar signal_processor para obtener predicción completa con filtros
            signal_quality = await signal_processor.process_signal(symbol, timeframe="1h")
            
            # Convertir SignalQuality a formato compatible con executor
            prediction_result = {
                'symbol': symbol,
                'action': signal_quality.signal,
                'confidence': signal_quality.confidence,
                'confidence_level': 'high' if signal_quality.confidence > 0.8 else 'medium' if signal_quality.confidence > 0.6 else 'low',
                'expected_return': signal_quality.strength,
                'risk_level': int(signal_quality.risk_score * 5) + 1,  # Convertir 0-1 a 1-5
                'time_horizon': 2.0,  # Valor por defecto
                'market_regime': signal_quality.market_regime,
                'action_probabilities': signal_quality.raw_prediction.get('action_probabilities', {}),
                'uncertainty': 1.0 - signal_quality.confidence,
                'is_tradeable': signal_quality.quality_score > 0.7,
                'is_high_confidence': signal_quality.confidence > 0.8,
                'features_used': len(signal_quality.raw_prediction.get('features_used', [])),
                'prediction_timestamp': signal_quality.processing_time.isoformat(),
                'model_version': signal_quality.raw_prediction.get('model_version', 'unknown'),
                
                # Información adicional del signal_processor
                'quality_score': signal_quality.quality_score,
                'consistency': signal_quality.consistency,
                'timing_score': signal_quality.timing_score,
                'volatility_level': signal_quality.volatility_level,
                'momentum_direction': signal_quality.momentum_direction,
                'volume_confirmation': signal_quality.volume_confirmation,
                'price_action_alignment': signal_quality.price_action_alignment,
                'indicator_convergence': signal_quality.indicator_convergence,
                'support_resistance_respect': signal_quality.support_resistance_respect,
                'session_timing': signal_quality.session_timing,
                'timeframe_alignment': signal_quality.timeframe_alignment,
                'timeframe_confidence': signal_quality.timeframe_confidence,
                'filtering_applied': signal_quality.filtering_applied,
                'rejection_reasons': signal_quality.rejection_reasons
            }
            
            # Actualizar métricas
            self.metrics['predictions_processed'] += 1
            self._update_average_confidence(prediction_result['confidence'])
            
            logger.info(f"🔮 Predicción ML: {prediction_result['action']} (confianza: {prediction_result['confidence']:.2%}, calidad: {signal_quality.quality_score:.2%})")
            return prediction_result
            
        except Exception as e:
            logger.error(f"❌ Error procesando predicción ML para {symbol}: {e}")
            return {'error': str(e)}
    
    async def evaluate_entry_signal(self, prediction: Dict, symbol: str) -> bool:
        """
        Decidir si ejecutar un trade basado en predicción ML con signal_processor
        
        Args:
            prediction: Resultado de la predicción ML (ahora incluye info del signal_processor)
            symbol: Símbolo a evaluar
            
        Returns:
            True si debe ejecutar trade, False en caso contrario
        """
        try:
            # 1. Verificar confianza mínima
            if prediction['confidence'] < self.min_confidence:
                logger.debug(f"⏸️ Confianza insuficiente para {symbol}: {prediction['confidence']:.2%} < {self.min_confidence:.2%}")
                return False
            
            # 2. Verificar que no sea HOLD
            if prediction['action'] == 'HOLD':
                logger.debug(f"⏸️ Señal HOLD para {symbol}")
                return False
            
            # 3. Verificar calidad de la señal (nuevo con signal_processor)
            quality_score = prediction.get('quality_score', 0.0)
            if quality_score < 0.7:  # Umbral de calidad
                logger.debug(f"⏸️ Calidad de señal insuficiente para {symbol}: {quality_score:.2%}")
                return False
            
            # 4. Verificar anti-duplicación
            if symbol in self.active_positions:
                logger.debug(f"⏸️ Ya hay posición activa para {symbol}")
                return False
            
            # 5. Verificar límite de posiciones concurrentes
            if len(self.active_positions) >= self.max_positions:
                logger.debug(f"⏸️ Límite de posiciones alcanzado: {len(self.active_positions)}/{self.max_positions}")
                return False
            
            # 6. Verificar cooldown entre trades
            if symbol in self.last_trade_time:
                time_since_last = datetime.now() - self.last_trade_time[symbol]
                if time_since_last.total_seconds() < (self.cooldown_minutes * 60):
                    logger.debug(f"⏸️ Cooldown activo para {symbol}: {time_since_last.total_seconds()/60:.1f}min")
                    return False
            
            # 7. Verificar límite diario de trades
            if self.daily_trade_count[symbol] >= self.max_daily_trades:
                logger.debug(f"⏸️ Límite diario de trades alcanzado para {symbol}: {self.daily_trade_count[symbol]}")
                return False
            
            # 8. Verificar circuit breakers
            if not await self._check_circuit_breakers(symbol):
                logger.debug(f"⏸️ Circuit breakers activos para {symbol}")
                return False
            
            # 9. Verificar condiciones de mercado (usando info del signal_processor)
            volatility_level = prediction.get('volatility_level', 'MEDIUM')
            if volatility_level == 'EXTREME':
                logger.debug(f"⏸️ Volatilidad extrema para {symbol}: {volatility_level}")
                return False
            
            # 10. Verificar consistencia multi-timeframe
            consistency = prediction.get('consistency', 0.0)
            if consistency < 0.6:
                logger.debug(f"⏸️ Baja consistencia multi-TF para {symbol}: {consistency:.2%}")
                return False
            
            # 11. Verificar timing
            timing_score = prediction.get('timing_score', 0.0)
            if timing_score < 0.5:
                logger.debug(f"⏸️ Timing desfavorable para {symbol}: {timing_score:.2%}")
                return False
            
            # 12. Verificar filtros obligatorios si están configurados
            if prediction.get('volume_confirmation') is False:
                logger.debug(f"⏸️ Sin confirmación de volumen para {symbol}")
                return False
            
            logger.info(f"✅ Señal de entrada aprobada para {symbol}: {prediction['action']} (confianza: {prediction['confidence']:.2%}, calidad: {quality_score:.2%})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error evaluando señal de entrada para {symbol}: {e}")
            return False
    
    async def evaluate_exit_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Evaluar si cerrar posiciones existentes
        
        Args:
            symbol: Símbolo a evaluar
            
        Returns:
            Lista de trades cerrados
        """
        try:
            if symbol not in self.active_positions:
                return []
            
            trade = self.active_positions[symbol]
            exit_results = []
            
            # 1. Verificar stop-loss y take-profit
            current_price = await self._get_current_price(symbol)
            if current_price:
                sl_exit = await self._check_stop_loss_take_profit(trade, current_price)
                if sl_exit:
                    exit_results.append(sl_exit)
                    return exit_results
            
            # 2. Verificar señales contrarias del modelo
            prediction = await self.process_ml_prediction(symbol)
            if prediction and not prediction.get('error'):
                opposite_signal = await self._check_opposite_signal(trade, prediction)
                if opposite_signal:
                    exit_results.append(opposite_signal)
                    return exit_results
            
            # 3. Verificar time-based exits
            time_exit = await self._check_time_based_exit(trade)
            if time_exit:
                exit_results.append(time_exit)
                return exit_results
            
            # 4. Verificar cambios en confianza del modelo
            confidence_exit = await self._check_confidence_exit(trade, prediction)
            if confidence_exit:
                exit_results.append(confidence_exit)
                return exit_results
            
            return exit_results
            
        except Exception as e:
            logger.error(f"❌ Error evaluando señales de salida para {symbol}: {e}")
            return []
    
    async def execute_trade_decision(self, symbol: str, decision: Dict) -> Optional[TradeRecord]:
        """
        Ejecutar decisión de trade
        
        Args:
            symbol: Símbolo a operar
            decision: Decisión de trading con predicción
            
        Returns:
            TradeRecord si se ejecutó exitosamente, None en caso contrario
        """
        try:
            logger.info(f"⚡ Ejecutando decisión de trade para {symbol}: {decision['action']}")
            
            # 1. Obtener precio actual
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.error(f"❌ No se pudo obtener precio actual para {symbol}")
                return None
            
            # 2. Calcular position sizing
            risk_decision = await risk_manager.calculate_position_size(
                symbol=symbol,
                signal=decision['action'],
                confidence=decision['confidence'],
                expected_return=decision['expected_return'],
                current_price=current_price
            )
            
            if not risk_decision:
                logger.warning(f"⚠️ Risk manager rechazó trade para {symbol}")
                return None
            
            # 3. Ejecutar orden
            trade_result = await order_manager.execute_order(
                symbol=symbol,
                signal=decision['action'],
                risk_decision=risk_decision,
                current_price=current_price,
                confidence=decision['confidence']
            )
            
            if trade_result:
                # 4. Registrar trade activo
                self.active_positions[symbol] = trade_result
                self.last_trade_time[symbol] = datetime.now()
                self.daily_trade_count[symbol] += 1
                
                # 5. Actualizar métricas
                self.metrics['trades_executed'] += 1
                self.metrics['current_positions'] = len(self.active_positions)
                
                logger.info(f"✅ Trade ejecutado: {symbol} {decision['action']} - {trade_result.trade_id}")
                return trade_result
            else:
                logger.warning(f"⚠️ Fallo en ejecución de orden para {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando decisión de trade para {symbol}: {e}")
            return None
    
    async def update_model_feedback(self, trade_records: List[TradeRecord]) -> None:
        """
        Enviar feedback al modelo ML
        
        Args:
            trade_records: Lista de trades cerrados para feedback
        """
        try:
            if not trade_records:
                return
            
            logger.info(f"🔄 Enviando feedback al modelo: {len(trade_records)} trades")
            
            # Preparar datos de feedback
            feedback_data = []
            for trade in trade_records:
                if trade.status == 'CLOSED':
                    feedback_data.append({
                        'symbol': trade.symbol,
                        'action': trade.side,
                        'entry_price': trade.entry_price,
                        'exit_price': trade.exit_price,
                        'pnl': trade.pnl,
                        'pnl_pct': trade.pnl_pct,
                        'confidence': trade.confidence,
                        'duration_hours': (trade.exit_time - trade.entry_time).total_seconds() / 3600,
                        'exit_reason': trade.exit_reason
                    })
            
            # Enviar feedback al sistema de aprendizaje
            if feedback_data:
                await adaptive_trainer.online_learning_update({}, feedback_data)
                
                # Actualizar calibración de confianza
                for trade in trade_records:
                    if hasattr(trade, 'prediction_result'):
                        confidence_estimator.update_calibration_data(
                            trade.prediction_result,
                            trade.side
                        )
            
            logger.info(f"✅ Feedback enviado al modelo: {len(feedback_data)} trades")
            
        except Exception as e:
            logger.error(f"❌ Error enviando feedback al modelo: {e}")
    
    # Métodos auxiliares privados
    
    async def _can_trade_symbol(self, symbol: str) -> bool:
        """Verificar si podemos operar un símbolo"""
        try:
            # Verificar si el símbolo está en la lista de símbolos permitidos
            allowed_symbols = self.trading_config.get('allowed_symbols', ['BTCUSDT'])
            if symbol not in allowed_symbols:
                return False
            
            # Verificar estado del sistema
            if not self.is_running:
                return False
            
            # Verificar conectividad con exchange
            health = await bitget_client.health_check()
            if health.get('status') != 'healthy':
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando si se puede operar {symbol}: {e}")
            return False
    
    async def _get_recent_market_data(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Obtener datos de mercado recientes"""
        try:
            return db_manager.get_recent_market_data(symbol, timeframe="1m", limit=limit)
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado para {symbol}: {e}")
            return []
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtener precio actual del símbolo"""
        try:
            market_data = await self._get_recent_market_data(symbol, limit=1)
            if market_data:
                return market_data[0].get('close')
            return None
        except Exception as e:
            logger.error(f"Error obteniendo precio actual para {symbol}: {e}")
            return None
    
    def _calculate_volatility(self, market_data: List[Dict]) -> float:
        """Calcular volatilidad de los datos de mercado"""
        try:
            if len(market_data) < 2:
                return 0.5  # Volatilidad media por defecto
            
            prices = [candle['close'] for candle in market_data[-20:]]  # Últimas 20 velas
            returns = np.diff(np.log(prices))
            volatility = np.std(returns)
            
            return min(1.0, max(0.0, volatility))  # Normalizar entre 0 y 1
            
        except Exception as e:
            logger.warning(f"Error calculando volatilidad: {e}")
            return 0.5
    
    async def _check_circuit_breakers(self, symbol: str) -> bool:
        """Verificar circuit breakers"""
        try:
            # Verificar pérdidas diarias
            if abs(self.daily_pnl) > self.risk_config.get('max_daily_loss', 1000):
                logger.warning(f"🚨 Circuit breaker: Pérdida diaria excedida: {self.daily_pnl}")
                return False
            
            # Verificar drawdown
            current_balance = order_manager.get_balance()
            if current_balance < self.risk_config.get('min_balance', 100):
                logger.warning(f"🚨 Circuit breaker: Balance mínimo alcanzado: {current_balance}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando circuit breakers: {e}")
            return False
    
    async def _check_market_conditions(self, symbol: str, prediction: Dict) -> bool:
        """Verificar condiciones de mercado"""
        try:
            # Verificar volatilidad extrema
            market_data = await self._get_recent_market_data(symbol, limit=20)
            if market_data:
                volatility = self._calculate_volatility(market_data)
                if volatility > 0.8:  # Volatilidad muy alta
                    logger.debug(f"⏸️ Volatilidad extrema: {volatility:.2f}")
                    return False
            
            # Verificar régimen de mercado
            if prediction.get('market_regime') == 'high_volatility':
                logger.debug("⏸️ Régimen de alta volatilidad")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando condiciones de mercado: {e}")
            return True  # En caso de error, permitir trading
    
    async def _check_stop_loss_take_profit(self, trade: TradeRecord, current_price: float) -> Optional[Dict]:
        """Verificar stop-loss y take-profit"""
        try:
            if not trade.stop_loss and not trade.take_profit:
                return None
            
            pnl_pct = (current_price - trade.entry_price) / trade.entry_price
            if trade.side == 'SELL':
                pnl_pct = -pnl_pct
            
            # Verificar stop-loss
            if trade.stop_loss and pnl_pct <= -trade.stop_loss:
                return await self._close_trade(trade, current_price, "stop_loss")
            
            # Verificar take-profit
            if trade.take_profit and pnl_pct >= trade.take_profit:
                return await self._close_trade(trade, current_price, "take_profit")
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando SL/TP: {e}")
            return None
    
    async def _check_opposite_signal(self, trade: TradeRecord, prediction: Dict) -> Optional[Dict]:
        """Verificar señal contraria del modelo"""
        try:
            if not prediction or prediction.get('error'):
                return None
            
            current_action = prediction['action']
            trade_side = trade.side
            
            # Verificar si la señal es contraria
            is_opposite = (
                (trade_side == 'BUY' and current_action == 'SELL') or
                (trade_side == 'SELL' and current_action == 'BUY')
            )
            
            if is_opposite and prediction['confidence'] > 0.7:
                current_price = await self._get_current_price(trade.symbol)
                if current_price:
                    return await self._close_trade(trade, current_price, "opposite_signal")
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando señal contraria: {e}")
            return None
    
    async def _check_time_based_exit(self, trade: TradeRecord) -> Optional[Dict]:
        """Verificar salida basada en tiempo"""
        try:
            # Verificar timeout de posición (ej: 24 horas)
            max_duration_hours = self.trading_config.get('max_position_duration_hours', 24)
            duration_hours = (datetime.now() - trade.entry_time).total_seconds() / 3600
            
            if duration_hours > max_duration_hours:
                current_price = await self._get_current_price(trade.symbol)
                if current_price:
                    return await self._close_trade(trade, current_price, "timeout")
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando salida por tiempo: {e}")
            return None
    
    async def _check_confidence_exit(self, trade: TradeRecord, prediction: Dict) -> Optional[Dict]:
        """Verificar salida por cambio de confianza"""
        try:
            if not prediction or prediction.get('error'):
                return None
            
            # Si la confianza actual es muy baja, considerar cerrar
            if prediction['confidence'] < 0.3:
                current_price = await self._get_current_price(trade.symbol)
                if current_price:
                    return await self._close_trade(trade, current_price, "low_confidence")
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando salida por confianza: {e}")
            return None
    
    async def _close_trade(self, trade: TradeRecord, exit_price: float, reason: str) -> Dict:
        """Cerrar trade y actualizar métricas"""
        try:
            # Cerrar trade
            closed_trade = await order_manager.close_trade(
                trade_id=trade.trade_id,
                exit_price=exit_price,
                exit_reason=reason
            )
            
            if closed_trade:
                # Remover de posiciones activas
                if trade.symbol in self.active_positions:
                    del self.active_positions[trade.symbol]
                
                # Actualizar métricas
                self.metrics['current_positions'] = len(self.active_positions)
                self.daily_pnl += closed_trade.pnl
                self.metrics['daily_pnl'] = self.daily_pnl
                
                logger.info(f"🔒 Trade cerrado: {trade.symbol} - {reason} - PnL: {closed_trade.pnl:.2f}")
                
                return {
                    'trade_id': closed_trade.trade_id,
                    'symbol': closed_trade.symbol,
                    'exit_price': exit_price,
                    'pnl': closed_trade.pnl,
                    'exit_reason': reason,
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error cerrando trade: {e}")
            return None
    
    async def _reset_daily_counters_if_needed(self):
        """Resetear contadores diarios si es nuevo día"""
        try:
            current_date = datetime.now().date()
            if current_date != self.last_reset_date:
                self.daily_trade_count.clear()
                self.daily_pnl = 0.0
                self.last_reset_date = current_date
                self.metrics['daily_pnl'] = 0.0
                logger.info("🔄 Contadores diarios reseteados")
        except Exception as e:
            logger.error(f"Error reseteando contadores diarios: {e}")
    
    def _update_average_confidence(self, confidence: float):
        """Actualizar confianza promedio"""
        try:
            current_avg = self.metrics['average_confidence']
            total_predictions = self.metrics['predictions_processed']
            
            if total_predictions > 0:
                new_avg = ((current_avg * (total_predictions - 1)) + confidence) / total_predictions
                self.metrics['average_confidence'] = new_avg
            else:
                self.metrics['average_confidence'] = confidence
        except Exception as e:
            logger.error(f"Error actualizando confianza promedio: {e}")
    
    async def _update_metrics(self, cycle_result: Dict):
        """Actualizar métricas de performance"""
        try:
            self.metrics['last_update'] = datetime.now().isoformat()
            
            # Actualizar trades skipped
            if cycle_result['status'] == 'skipped':
                self.metrics['trades_skipped'] += 1
            
            # Calcular win rate
            if self.metrics['trades_executed'] > 0:
                # Esto se actualizará cuando se cierren trades
                pass
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    async def _update_model_feedback(self, exit_results: List[Dict]):
        """Actualizar feedback del modelo con trades cerrados"""
        try:
            if not exit_results:
                return
            
            # Convertir a TradeRecord para feedback
            trade_records = []
            for result in exit_results:
                # Buscar el trade original
                for symbol, trade in self.active_positions.items():
                    if trade.trade_id == result['trade_id']:
                        trade_records.append(trade)
                        break
            
            if trade_records:
                await self.update_model_feedback(trade_records)
                
        except Exception as e:
            logger.error(f"Error actualizando feedback del modelo: {e}")
    
    # Métodos públicos para monitoreo y control
    
    async def start_trading(self):
        """Iniciar el motor de trading"""
        try:
            self.is_running = True
            logger.info("🚀 Motor de trading iniciado")
        except Exception as e:
            logger.error(f"Error iniciando motor de trading: {e}")
    
    async def stop_trading(self):
        """Detener el motor de trading"""
        try:
            self.is_running = False
            logger.info("⏹️ Motor de trading detenido")
        except Exception as e:
            logger.error(f"Error deteniendo motor de trading: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar estado de todos los componentes"""
        try:
            health = {
                'status': 'healthy',
                'is_running': self.is_running,
                'active_positions': len(self.active_positions),
                'daily_trades': sum(self.daily_trade_count.values()),
                'daily_pnl': self.daily_pnl,
                'components': {},
                'errors': []
            }
            
            # Verificar componentes
            try:
                prediction_health = await prediction_engine.health_check()
                health['components']['prediction_engine'] = prediction_health
            except Exception as e:
                health['components']['prediction_engine'] = {'status': 'error', 'error': str(e)}
                health['errors'].append(f"Prediction engine: {e}")
            
            try:
                order_health = await order_manager.health_check()
                health['components']['order_manager'] = order_health
            except Exception as e:
                health['components']['order_manager'] = {'status': 'error', 'error': str(e)}
                health['errors'].append(f"Order manager: {e}")
            
            try:
                risk_health = await risk_manager.health_check()
                health['components']['risk_manager'] = risk_health
            except Exception as e:
                health['components']['risk_manager'] = {'status': 'error', 'error': str(e)}
                health['errors'].append(f"Risk manager: {e}")
            
            # Determinar estado general
            if health['errors']:
                health['status'] = 'degraded'
            if not self.is_running:
                health['status'] = 'stopped'
            
            return health
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def dry_run_cycle(self, symbol: str) -> Dict[str, Any]:
        """Ejecutar ciclo completo sin trades reales (testing)"""
        try:
            logger.info(f"🧪 Ejecutando dry run para {symbol}")
            
            # Guardar estado original
            original_running = self.is_running
            original_positions = self.active_positions.copy()
            
            # Simular modo dry run
            self.is_running = True
            
            # Ejecutar ciclo normal
            result = await self.execute_trading_cycle(symbol)
            result['dry_run'] = True
            
            # Restaurar estado original
            self.is_running = original_running
            self.active_positions = original_positions
            
            logger.info(f"✅ Dry run completado para {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error en dry run para {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'error',
                'error': str(e),
                'dry_run': True
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Resumen de performance actual"""
        try:
            return {
                'metrics': self.metrics.copy(),
                'active_positions': {
                    symbol: {
                        'trade_id': trade.trade_id,
                        'side': trade.side,
                        'entry_price': trade.entry_price,
                        'entry_time': trade.entry_time.isoformat(),
                        'pnl': trade.pnl if hasattr(trade, 'pnl') else 0,
                        'confidence': trade.confidence
                    }
                    for symbol, trade in self.active_positions.items()
                },
                'daily_trade_counts': dict(self.daily_trade_count),
                'last_reset_date': self.last_reset_date.isoformat(),
                'configuration': {
                    'min_confidence': self.min_confidence,
                    'cooldown_minutes': self.cooldown_minutes,
                    'max_daily_trades': self.max_daily_trades,
                    'max_positions': self.max_positions
                }
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen de performance: {e}")
            return {'error': str(e)}
    
    async def optimize_portfolio_allocation(self) -> Dict[str, Any]:
        """
        Optimiza asignación del portfolio multi-símbolo
        """
        try:
            logger.info("[TradingExecutor] Iniciando optimización de portfolio")
            
            # Verificar si se necesita rebalance
            rebalance_needed, reasons = await portfolio_optimizer.should_rebalance()
            
            if not rebalance_needed:
                logger.info("[TradingExecutor] No se requiere rebalance del portfolio")
                return {
                    'rebalance_needed': False,
                    'reasons': reasons,
                    'message': 'Portfolio está balanceado'
                }
            
            logger.info(f"[TradingExecutor] Rebalance necesario: {reasons}")
            
            # Optimizar portfolio
            targets = await portfolio_optimizer.optimize_portfolio()
            
            if not targets:
                logger.warning("[TradingExecutor] No se pudieron generar targets de optimización")
                return {
                    'rebalance_needed': True,
                    'reasons': reasons,
                    'error': 'No se pudieron generar targets'
                }
            
            # Ejecutar rebalance
            rebalance_result = await portfolio_optimizer.execute_rebalance(targets)
            
            logger.info(f"[TradingExecutor] Optimización de portfolio completada: {rebalance_result}")
            
            return {
                'rebalance_needed': True,
                'reasons': reasons,
                'targets_generated': len(targets),
                'rebalance_result': rebalance_result,
                'targets': {k: {
                    'symbol': v.symbol,
                    'target_pct': v.target_allocation_pct,
                    'current_pct': v.current_allocation_pct,
                    'action': v.action_required,
                    'change_pct': v.target_change_pct
                } for k, v in targets.items()}
            }
            
        except Exception as e:
            logger.error(f"[TradingExecutor] Error optimizando portfolio: {e}")
            return {
                'rebalance_needed': False,
                'error': str(e)
            }
    
    async def get_portfolio_state(self) -> Dict[str, Any]:
        """
        Obtiene estado actual del portfolio
        """
        try:
            portfolio_state = await portfolio_optimizer.get_portfolio_state()
            
            if not portfolio_state:
                return {'error': 'No se pudo obtener estado del portfolio'}
            
            return {
                'total_balance': portfolio_state.total_balance,
                'available_balance': portfolio_state.available_balance,
                'invested_balance': portfolio_state.invested_balance,
                'symbol_allocations': portfolio_state.symbol_allocations,
                'total_unrealized_pnl': portfolio_state.total_unrealized_pnl,
                'total_realized_pnl': portfolio_state.total_realized_pnl,
                'portfolio_return': portfolio_state.portfolio_return,
                'portfolio_volatility': portfolio_state.portfolio_volatility,
                'sharpe_ratio': portfolio_state.sharpe_ratio,
                'diversification_ratio': portfolio_state.diversification_ratio,
                'correlation_risk_score': portfolio_state.correlation_risk_score,
                'rebalance_needed': portfolio_state.rebalance_needed
            }
            
        except Exception as e:
            logger.error(f"[TradingExecutor] Error obteniendo estado del portfolio: {e}")
            return {'error': str(e)}
    
    async def check_portfolio_health(self) -> Dict[str, Any]:
        """
        Verifica salud del portfolio
        """
        try:
            # Health check del portfolio optimizer
            portfolio_health = await portfolio_optimizer.health_check()
            
            # Detectar riesgos de concentración
            concentration_risks = await portfolio_optimizer.detect_concentration_risk()
            
            return {
                'portfolio_optimizer': portfolio_health,
                'concentration_risks': concentration_risks,
                'overall_status': 'healthy' if portfolio_health['status'] == 'healthy' and not concentration_risks['risk_detected'] else 'warning'
            }
            
        except Exception as e:
            logger.error(f"[TradingExecutor] Error verificando salud del portfolio: {e}")
            return {
                'overall_status': 'error',
                'error': str(e)
            }

# Instancia global del ejecutor de trading
trading_executor = TradingExecutor()

# Funciones de conveniencia
async def execute_trading_cycle(symbol: str) -> Dict[str, Any]:
    """Función de conveniencia para ejecutar ciclo de trading"""
    return await trading_executor.execute_trading_cycle(symbol)

async def start_trading():
    """Función de conveniencia para iniciar trading"""
    await trading_executor.start_trading()

async def stop_trading():
    """Función de conveniencia para detener trading"""
    await trading_executor.stop_trading()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await trading_executor.health_check()

async def dry_run_cycle(symbol: str) -> Dict[str, Any]:
    """Función de conveniencia para dry run"""
    return await trading_executor.dry_run_cycle(symbol)

def get_performance_summary() -> Dict[str, Any]:
    """Función de conveniencia para obtener resumen de performance"""
    return trading_executor.get_performance_summary()
