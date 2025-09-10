# Ruta: core/trading/enterprise/strategy_manager.py
# strategy_manager.py - Gestor de estrategias enterprise
# Ubicación: core/trading/enterprise/strategy_manager.py

"""
Gestor de Estrategias Enterprise
Gestiona y ejecuta estrategias de trading basadas en configuraciones

Características principales:
- Gestión de múltiples estrategias (ML, momentum, mean reversion)
- Ejecución paralela de estrategias
- Monitoreo de performance por estrategia
- Integración con configuraciones .yaml
- Cache de resultados de estrategias
- Alertas y notificaciones
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
import redis
from control.telegram_bot import telegram_bot
from core.config.config_loader import config_loader
from core.trading.trading_signal import TradingSignal, SignalType, SignalStrength
from core.trading.risk_manager import risk_manager
from core.trading.enterprise.leverage_calculator import LeverageCalculator
from core.trading.enterprise.market_analyzer import MarketAnalyzer, MarketCondition
from core.sync.metrics_aggregator import metrics_aggregator

logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """Resultado de ejecución de estrategia"""
    strategy_name: str
    symbol: str
    timeframe: str
    signal: TradingSignal
    confidence: float
    execution_time: float
    market_condition: MarketCondition
    risk_score: float
    timestamp: datetime

@dataclass
class StrategyPerformance:
    """Performance de una estrategia"""
    strategy_name: str
    total_signals: int
    successful_signals: int
    win_rate: float
    avg_confidence: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    last_updated: datetime

class StrategyManager:
    """Gestor de estrategias enterprise"""
    
    def __init__(self):
        self.config_loader = config_loader
        self.risk_manager = risk_manager
        self.leverage_calculator = LeverageCalculator({})
        self.market_analyzer = MarketAnalyzer({})
        self.redis_client = None
        self.strategies = {}
        self.strategy_performance = {}
        self.running = False
        self.execution_queue = asyncio.Queue()
        self.results_queue = asyncio.Queue()
        
        # Configuración de estrategias
        self.strategies_config = {}
        self.max_concurrent_strategies = 5
        self.strategy_timeout = 30.0
        
        logger.info("StrategyManager inicializado")
    
    async def initialize(self):
        """Inicializa el gestor de estrategias"""
        try:
            # Inicializar configuraciones
            await self.config_loader.initialize()
            
            # Cargar configuración de estrategias
            self.strategies_config = self.config_loader.get_config('strategies.yaml', 'strategies', {})
            self.max_concurrent_strategies = self.strategies_config.get('execution', {}).get('max_concurrent_strategies', 5)
            
            # Configurar Redis
            await self._setup_redis()
            
            # Cargar estrategias disponibles
            await self._load_strategies()
            
            logger.info("StrategyManager inicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error inicializando StrategyManager: {e}")
            raise
    
    async def _setup_redis(self):
        """Configura Redis para cache de estrategias"""
        try:
            redis_url = self.config_loader.get_infrastructure_settings().get('redis', {}).get('url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Conexión a Redis establecida para StrategyManager")
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}")
            self.redis_client = None
    
    async def _load_strategies(self):
        """Carga estrategias disponibles desde configuración"""
        try:
            strategies = self.strategies_config.get('strategies', {})
            
            for strategy_name, strategy_config in strategies.items():
                if strategy_config.get('enabled', False):
                    self.strategies[strategy_name] = strategy_config
                    logger.info(f"Estrategia cargada: {strategy_name}")
            
            logger.info(f"Cargadas {len(self.strategies)} estrategias")
            
        except Exception as e:
            logger.error(f"Error cargando estrategias: {e}")
    
    async def execute_strategies(self, 
                                symbols: List[str], 
                                timeframes: List[str],
                                market_data: Dict[str, pd.DataFrame]) -> List[StrategyResult]:
        """
        Ejecuta todas las estrategias habilitadas
        
        Args:
            symbols: Lista de símbolos a analizar
            timeframes: Lista de timeframes a usar
            market_data: Datos de mercado por símbolo y timeframe
            
        Returns:
            Lista de resultados de estrategias
        """
        try:
            if not self.strategies:
                logger.warning("No hay estrategias habilitadas")
                return []
            
            self.running = True
            results = []
            
            # Analizar condiciones de mercado
            market_analysis = await self.market_analyzer.analyze_market(market_data)
            
            # Ejecutar estrategias en paralelo
            with ThreadPoolExecutor(max_workers=self.max_concurrent_strategies) as executor:
                futures = []
                
                for strategy_name, strategy_config in self.strategies.items():
                    for symbol in symbols:
                        for timeframe in timeframes:
                            if symbol in market_data and timeframe in market_data[symbol]:
                                future = executor.submit(
                                    self._execute_strategy,
                                    strategy_name,
                                    strategy_config,
                                    symbol,
                                    timeframe,
                                    market_data[symbol][timeframe],
                                    market_analysis
                                )
                                futures.append(future)
                
                # Procesar resultados
                for future in as_completed(futures, timeout=self.strategy_timeout):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            await self.results_queue.put(result)
                    except Exception as e:
                        logger.error(f"Error ejecutando estrategia: {e}")
            
            # Actualizar métricas de performance
            await self._update_strategy_performance(results)
            
            # Enviar notificaciones si hay señales importantes
            await self._send_strategy_notifications(results)
            
            logger.info(f"Ejecutadas {len(results)} estrategias exitosamente")
            return results
            
        except Exception as e:
            logger.error(f"Error ejecutando estrategias: {e}")
            return []
        finally:
            self.running = False
    
    def _execute_strategy(self, 
                         strategy_name: str, 
                         strategy_config: Dict[str, Any],
                         symbol: str, 
                         timeframe: str,
                         data: pd.DataFrame,
                         market_analysis: Any) -> Optional[StrategyResult]:
        """Ejecuta una estrategia específica"""
        try:
            start_time = time.time()
            
            # Verificar cache
            cache_key = f"strategy_{strategy_name}_{symbol}_{timeframe}_{int(time.time())}"
            if self.redis_client:
                try:
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        return StrategyResult(**json.loads(cached_result))
                except Exception as e:
                    logger.warning(f"Error leyendo cache: {e}")
            
            # Ejecutar estrategia según tipo
            strategy_type = strategy_config.get('type', 'ml_strategy')
            
            if strategy_type == 'ml_strategy':
                signal = self._execute_ml_strategy(strategy_config, symbol, timeframe, data)
            elif strategy_type == 'momentum_strategy':
                signal = self._execute_momentum_strategy(strategy_config, symbol, timeframe, data)
            elif strategy_type == 'mean_reversion_strategy':
                signal = self._execute_mean_reversion_strategy(strategy_config, symbol, timeframe, data)
            else:
                logger.warning(f"Tipo de estrategia no soportado: {strategy_type}")
                return None
            
            if not signal:
                return None
            
            # Calcular métricas de riesgo
            risk_score = self._calculate_risk_score(signal, data, market_analysis)
            
            # Crear resultado
            result = StrategyResult(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                signal=signal,
                confidence=signal.confidence,
                execution_time=time.time() - start_time,
                market_condition=market_analysis.condition if market_analysis else MarketCondition.NEUTRAL,
                risk_score=risk_score,
                timestamp=datetime.now()
            )
            
            # Cachear resultado
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, 300, json.dumps(asdict(result), default=str))
                except Exception as e:
                    logger.warning(f"Error guardando en cache: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando estrategia {strategy_name}: {e}")
            return None
    
    def _execute_ml_strategy(self, 
                           strategy_config: Dict[str, Any],
                           symbol: str, 
                           timeframe: str, 
                           data: pd.DataFrame) -> Optional[TradingSignal]:
        """Ejecuta estrategia ML"""
        try:
            # En un sistema real, esto cargaría el modelo ML entrenado
            # Por ahora, simulamos una estrategia ML básica
            
            if len(data) < 20:
                return None
            
            # Calcular indicadores técnicos básicos
            close_prices = data['close'].values
            sma_20 = np.mean(close_prices[-20:])
            sma_50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else sma_20
            
            current_price = close_prices[-1]
            
            # Lógica de señal ML (simplificada)
            if current_price > sma_20 > sma_50:
                signal_type = SignalType.BUY
                confidence = min(0.8, (current_price - sma_20) / sma_20 * 10)
            elif current_price < sma_20 < sma_50:
                signal_type = SignalType.SELL
                confidence = min(0.8, (sma_20 - current_price) / current_price * 10)
            else:
                signal_type = SignalType.HOLD
                confidence = 0.3
            
            # Aplicar filtros de configuración
            min_confidence = strategy_config.get('signals', {}).get('min_confidence', 0.5)
            if confidence < min_confidence:
                return None
            
            # Calcular cantidad basada en configuración
            max_position_size = strategy_config.get('trading', {}).get('max_position_size_pct', 0.1)
            quantity = current_price * max_position_size
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                quantity=quantity,
                timestamp=int(time.time()),
                timeframe=timeframe,
                strategy=strategy_config.get('name', 'ml_strategy')
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando estrategia ML: {e}")
            return None
    
    def _execute_momentum_strategy(self, 
                                 strategy_config: Dict[str, Any],
                                 symbol: str, 
                                 timeframe: str, 
                                 data: pd.DataFrame) -> Optional[TradingSignal]:
        """Ejecuta estrategia de momentum"""
        try:
            if len(data) < 20:
                return None
            
            # Calcular RSI
            close_prices = data['close'].values
            delta = np.diff(close_prices)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else 0
            avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else 0
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            current_price = close_prices[-1]
            
            # Lógica de momentum
            if rsi < 30:  # Oversold
                signal_type = SignalType.BUY
                confidence = (30 - rsi) / 30 * 0.8
            elif rsi > 70:  # Overbought
                signal_type = SignalType.SELL
                confidence = (rsi - 70) / 30 * 0.8
            else:
                return None
            
            # Aplicar filtros
            min_confidence = strategy_config.get('signals', {}).get('min_confidence', 0.5)
            if confidence < min_confidence:
                return None
            
            max_position_size = strategy_config.get('trading', {}).get('max_position_size_pct', 0.1)
            quantity = current_price * max_position_size
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                quantity=quantity,
                timestamp=int(time.time()),
                timeframe=timeframe,
                strategy=strategy_config.get('name', 'momentum_strategy')
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando estrategia de momentum: {e}")
            return None
    
    def _execute_mean_reversion_strategy(self, 
                                       strategy_config: Dict[str, Any],
                                       symbol: str, 
                                       timeframe: str, 
                                       data: pd.DataFrame) -> Optional[TradingSignal]:
        """Ejecuta estrategia de reversión a la media"""
        try:
            if len(data) < 20:
                return None
            
            close_prices = data['close'].values
            current_price = close_prices[-1]
            
            # Calcular Bollinger Bands
            sma_20 = np.mean(close_prices[-20:])
            std_20 = np.std(close_prices[-20:])
            
            upper_band = sma_20 + (2 * std_20)
            lower_band = sma_20 - (2 * std_20)
            
            # Lógica de reversión a la media
            if current_price <= lower_band:
                signal_type = SignalType.BUY
                confidence = min(0.8, (lower_band - current_price) / lower_band * 5)
            elif current_price >= upper_band:
                signal_type = SignalType.SELL
                confidence = min(0.8, (current_price - upper_band) / upper_band * 5)
            else:
                return None
            
            # Aplicar filtros
            min_confidence = strategy_config.get('signals', {}).get('min_confidence', 0.5)
            if confidence < min_confidence:
                return None
            
            max_position_size = strategy_config.get('trading', {}).get('max_position_size_pct', 0.1)
            quantity = current_price * max_position_size
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                quantity=quantity,
                timestamp=int(time.time()),
                timeframe=timeframe,
                strategy=strategy_config.get('name', 'mean_reversion_strategy')
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando estrategia de reversión a la media: {e}")
            return None
    
    def _calculate_risk_score(self, 
                            signal: TradingSignal, 
                            data: pd.DataFrame,
                            market_analysis: Any) -> float:
        """Calcula score de riesgo para una señal"""
        try:
            risk_score = 0.0
            
            # Riesgo basado en volatilidad
            if len(data) >= 20:
                returns = data['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Anualizada
                risk_score += min(1.0, volatility * 2)
            
            # Riesgo basado en confianza de la señal
            risk_score += (1.0 - signal.confidence) * 0.5
            
            # Riesgo basado en condiciones de mercado
            if market_analysis and hasattr(market_analysis, 'condition'):
                if market_analysis.condition in [MarketCondition.EXTREME_VOLATILITY, MarketCondition.CRASH]:
                    risk_score += 0.3
            
            return min(1.0, risk_score)
            
        except Exception as e:
            logger.error(f"Error calculando risk score: {e}")
            return 0.5
    
    async def _update_strategy_performance(self, results: List[StrategyResult]):
        """Actualiza métricas de performance de estrategias"""
        try:
            for result in results:
                strategy_name = result.strategy_name
                
                if strategy_name not in self.strategy_performance:
                    self.strategy_performance[strategy_name] = StrategyPerformance(
                        strategy_name=strategy_name,
                        total_signals=0,
                        successful_signals=0,
                        win_rate=0.0,
                        avg_confidence=0.0,
                        total_pnl=0.0,
                        sharpe_ratio=0.0,
                        max_drawdown=0.0,
                        last_updated=datetime.now()
                    )
                
                performance = self.strategy_performance[strategy_name]
                performance.total_signals += 1
                performance.avg_confidence = (
                    (performance.avg_confidence * (performance.total_signals - 1) + result.confidence) 
                    / performance.total_signals
                )
                performance.last_updated = datetime.now()
                
                # En un sistema real, aquí se calcularían PnL y otras métricas
                # basadas en el resultado de las operaciones
            
            # Actualizar métricas en metrics_aggregator
            for strategy_name, performance in self.strategy_performance.items():
                await metrics_aggregator.track_strategy_performance(
                    strategy_name,
                    performance.total_pnl,
                    performance.total_signals
                )
            
        except Exception as e:
            logger.error(f"Error actualizando performance de estrategias: {e}")
    
    async def _send_strategy_notifications(self, results: List[StrategyResult]):
        """Envía notificaciones de estrategias importantes"""
        try:
            high_confidence_signals = [
                r for r in results 
                if r.confidence > 0.8 and r.signal.signal_type != SignalType.HOLD
            ]
            
            if high_confidence_signals:
                message = f"🚀 Señales de alta confianza detectadas:\n\n"
                for result in high_confidence_signals[:5]:  # Máximo 5 señales
                    message += f"• {result.strategy_name}: {result.signal.signal_type.value} {result.symbol} "
                    message += f"(conf: {result.confidence:.2f}, riesgo: {result.risk_score:.2f})\n"
                
                await telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificaciones de estrategias: {e}")
    
    def get_strategy_performance(self, strategy_name: str = None) -> Dict[str, Any]:
        """Obtiene performance de estrategias"""
        try:
            if strategy_name:
                return asdict(self.strategy_performance.get(strategy_name, {}))
            else:
                return {name: asdict(perf) for name, perf in self.strategy_performance.items()}
        except Exception as e:
            logger.error(f"Error obteniendo performance de estrategias: {e}")
            return {}
    
    def get_available_strategies(self) -> List[str]:
        """Obtiene lista de estrategias disponibles"""
        return list(self.strategies.keys())
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Obtiene configuración de una estrategia específica"""
        return self.strategies.get(strategy_name, {})
    
    async def enable_strategy(self, strategy_name: str):
        """Habilita una estrategia"""
        try:
            if strategy_name in self.strategies:
                self.strategies[strategy_name]['enabled'] = True
                logger.info(f"Estrategia {strategy_name} habilitada")
            else:
                logger.warning(f"Estrategia {strategy_name} no encontrada")
        except Exception as e:
            logger.error(f"Error habilitando estrategia {strategy_name}: {e}")
    
    async def disable_strategy(self, strategy_name: str):
        """Deshabilita una estrategia"""
        try:
            if strategy_name in self.strategies:
                self.strategies[strategy_name]['enabled'] = False
                logger.info(f"Estrategia {strategy_name} deshabilitada")
            else:
                logger.warning(f"Estrategia {strategy_name} no encontrada")
        except Exception as e:
            logger.error(f"Error deshabilitando estrategia {strategy_name}: {e}")
    
    async def cleanup(self):
        """Limpia recursos del gestor de estrategias"""
        try:
            self.running = False
            
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("StrategyManager limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando StrategyManager: {e}")

# Instancia global
strategy_manager = StrategyManager()
