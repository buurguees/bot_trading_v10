# Ruta: core/trading/enterprise/futures_execution_engine.py
# futures_execution_engine.py - Motor de Ejecución de Futuros Enterprise
# Ubicación: C:\TradingBot_v10\core\trading\enterprise\futures_execution_engine.py

"""
Motor de Ejecución de Futuros Enterprise
Unifica order_manager.py, order_executor.py, executor.py, y futures_engine.py

Características principales:
- Trading autónomo 24/7 para futuros
- Leverage dinámico 5x-125x
- Long/Short positions automáticas
- Risk management enterprise
- Real-time inference <100ms
- Portfolio management inteligente
- Redis caching para performance
- Prometheus metrics
- Alertas Telegram
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import json
import ccxt.async_support as ccxt
import redis
from prometheus_client import Counter, Gauge, Histogram, Summary
from control.telegram_bot import telegram_bot
from core.data.database import db_manager
from core.trading.enterprise.trading_signal import TradingSignal, SignalType, SignalStrength
from core.trading.enterprise.leverage_calculator import LeverageCalculator, LeverageResult
from core.trading.enterprise.position_manager import PositionManager, Position
from core.trading.enterprise.market_analyzer import MarketAnalyzer, MarketCondition
from core.sync.parallel_executor import ParallelExecutor, CycleResult
from core.sync.metrics_aggregator import MetricsAggregator, DailyMetrics
# Evitar dependencias fuertes al loader legacy: usar lazy import del unified manager
def _get_cfg():
    try:
        from config.unified_config import get_config_manager
        return get_config_manager()
    except Exception:
        return None

logger = logging.getLogger(__name__)

# Prometheus metrics
trades_total = Counter('futures_trades_total', 'Total trades executed', ['symbol', 'side'])
pnl_gauge = Gauge('futures_pnl', 'Realized PnL', ['symbol'])
leverage_gauge = Gauge('futures_leverage_ratio', 'Leverage ratio', ['symbol'])
execution_time_histogram = Histogram('futures_execution_time_seconds', 'Execution time', ['symbol'])
account_balance_gauge = Gauge('futures_account_balance', 'Account balance', ['currency'])
unrealized_pnl_gauge = Gauge('futures_unrealized_pnl', 'Unrealized PnL', ['symbol'])
circuit_breaker_active = Gauge('futures_circuit_breaker', 'Circuit breaker status')
api_calls_total = Counter('futures_api_calls_total', 'Total API calls', ['endpoint', 'status'])

@dataclass
class Trade:
    """Estructura de trade unificada"""
    trade_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: Optional[float]
    leverage: float
    pnl: float
    fees: float
    entry_time: int
    exit_time: Optional[int]
    status: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_used: str = "default"
    metadata: Dict[str, Any] = None

@dataclass
class ExecutionMetrics:
    """Métricas de ejecución unificadas"""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    unrealized_pnl: float
    win_rate: float
    avg_execution_time: float
    max_execution_time: float
    min_execution_time: float
    api_calls_made: int
    api_errors: int
    cache_hit_rate: float
    circuit_breaker_activations: int
    total_volume_traded: float
    sharpe_ratio: float
    max_drawdown: float

@dataclass
class TradingSummary:
    """Resumen de trading"""
    timestamp: datetime
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    unrealized_pnl: float
    win_rate: float
    best_trade: Optional[Trade]
    worst_trade: Optional[Trade]
    active_positions: int
    account_balance: float
    recommendations: List[str]

class FuturesExecutionEngine:
    """Motor unificado para ejecución de futuros en Bitget"""
    
    def __init__(self, config: Dict[str, Any] = None, max_workers: int = 4):
        # Cargar config desde UnifiedConfig v2 si no se pasa explícita
        if config is None:
            cfg_mgr = _get_cfg()
            if cfg_mgr:
                # Construir dict mínimo esperado por este motor
                config = {
                    'trading': {
                        'symbols': cfg_mgr.get_symbols(),
                        'timeframes': cfg_mgr.get_timeframes()
                    },
                    'risk_management': cfg_mgr.get('features.risk_management', {}),
                    'exchanges': cfg_mgr.get('core.exchanges', {}),
                    'execution_delay_ms': int(cfg_mgr.get('features.trading.execution_delay_ms', 100)),
                }
            else:
                config = {}
        self.config = config
        self.max_workers = max_workers
        self.execution_queue = asyncio.Queue()
        self.results_queue = asyncio.Queue()
        self.metrics = ExecutionMetrics(0, 0, 0, 0, 0, 0, 0, 0, float('inf'), 0, 0, 0, 0, 0, 0, 0)
        self.running = False
        self.circuit_breaker_active = False
        self.positions: Dict[str, Position] = {}
        self.open_trades: Dict[str, Trade] = {}
        
        # Componentes integrados
        self.leverage_calculator = LeverageCalculator(config)
        self.position_manager = PositionManager(config)
        self.market_analyzer = MarketAnalyzer(config)
        self.parallel_executor = ParallelExecutor(max_workers, config.get('execution_delay_ms', 100))
        self.metrics_aggregator = MetricsAggregator(config)
        
        # Conexiones
        self.redis_client = None
        self.exchange = None
        self.lock = asyncio.Lock()
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Configuración
        self.symbols = config.get('trading', {}).get('symbols', ['BTCUSDT', 'ETHUSDT'])
        self.timeframes = config.get('trading', {}).get('timeframes', ['1m', '5m', '1h'])
        self.max_risk_per_trade = config.get('risk_management', {}).get('max_risk_per_trade', 0.02)
        self.max_daily_loss = config.get('risk_management', {}).get('max_daily_loss', 0.1)
        
        self._setup_redis()
        logger.info("FuturesExecutionEngine inicializado")
    
    def _setup_redis(self):
        """Configura Redis para caching"""
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            logger.info("Conexión a Redis establecida")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
    
    async def initialize_exchange(self):
        """Inicializa conexión con Bitget"""
        try:
            self.exchange = ccxt.bitget({
                'apiKey': self.config['exchanges']['bitget']['authentication']['api_key'],
                'secret': self.config['exchanges']['bitget']['authentication']['secret_key'],
                'password': self.config['exchanges']['bitget']['authentication']['passphrase'],
                'enableRateLimit': True,
                'rateLimit': 100,
                'sandbox': self.config.get('trading', {}).get('paper_trading', False)
            })
            await self.exchange.load_markets()
            
            # Configurar modo de posición (one-way/hedge)
            await self._set_position_mode()
            
            logger.info("Conexión con Bitget establecida")
            await telegram_bot.send_message("🚀 FuturesExecutionEngine conectado a Bitget")
            
        except Exception as e:
            logger.error(f"Error inicializando Bitget: {e}")
            await telegram_bot.send_message(f"⚠️ Error inicializando Bitget: {e}")
    
    async def _set_position_mode(self):
        """Configura modo de posición (one-way/hedge)"""
        try:
            # Leer configuración desde futures_config.yaml
            position_config = self.config.get('exchanges', {}).get('bitget', {}).get('position_mode', {})
            if not position_config.get('enabled', False):
                logger.info("Modo de posición deshabilitado en configuración")
                return
                
            position_mode = position_config.get('default_mode', 'one_way')
            supported_modes = position_config.get('supported_modes', ['one_way'])
            
            if position_mode not in supported_modes:
                logger.warning(f"Modo {position_mode} no soportado, usando one_way")
                position_mode = 'one_way'
            
            if position_mode == 'hedge':
                await self.exchange.set_position_mode('hedge')
                logger.info("Modo de posición configurado: hedge")
                await telegram_bot.send_message("🔄 Modo de posición configurado: HEDGE")
            else:
                await self.exchange.set_position_mode('one-way')
                logger.info("Modo de posición configurado: one-way")
                await telegram_bot.send_message("🔄 Modo de posición configurado: ONE-WAY")
                
        except Exception as e:
            logger.warning(f"No se pudo configurar modo de posición: {e}")
            await telegram_bot.send_message(f"⚠️ Error configurando modo de posición: {e}")
    
    async def execute_trading_cycle(self, signals: List[TradingSignal], timeline: pd.DataFrame) -> Dict[str, Any]:
        """Ejecuta ciclo de trading para múltiples señales"""
        try:
            if self.circuit_breaker_active:
                logger.warning("Circuit breaker activo - saltando ciclo de trading")
                return {'status': 'circuit_breaker', 'message': 'Circuit breaker activo'}
            
            self.running = True
            start_time = time.time()
            
            # Análisis de mercado
            market_analysis = await self.market_analyzer.analyze_market()
            
            # Filtrar señales según condiciones de mercado
            filtered_signals = await self._filter_signals_by_market_condition(signals, market_analysis)
            
            if not filtered_signals:
                logger.info("No hay señales válidas después del filtrado")
                return {'status': 'no_signals', 'signals_filtered': len(signals)}
            
            # Ejecutar trades en paralelo
            results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for signal in filtered_signals:
                    cache_key = f"trade_{signal.symbol}_{signal.timestamp}"
                    cached_result = await self._get_cached_trade(cache_key)
                    if cached_result:
                        self.cache_hits += 1
                        results.append(cached_result)
                        continue
                    
                    self.cache_misses += 1
                    futures.append(executor.submit(self._execute_trade, signal, timeline, market_analysis))
                    await asyncio.sleep(self.config.get('execution_delay_ms', 100) / 1000.0)
                
                for future in as_completed(futures):
                    try:
                        trade = future.result()
                        results.append(trade)
                        await self.results_queue.put(trade)
                        
                        # Actualizar métricas Prometheus
                        await self._update_prometheus_metrics(trade)
                        
                        # Cachear resultado
                        await self._cache_trade(cache_key, trade)
                        
                        # Persistir en SQLite
                        await self._persist_trade(trade)
                        
                        # Actualizar posiciones
                        await self._update_positions(trade)
                    
                    except Exception as e:
                        logger.error(f"Error en trade: {e}")
                        self.metrics.failed_trades += 1
                        self.metrics.api_errors += 1
                        api_calls_total.labels(endpoint='create_order', status='error').inc()
                
                await self._update_metrics(results)
            
            # Generar recomendaciones
            recommendations = await self._generate_recommendations(results, market_analysis)
            
            # Enviar alertas via Telegram
            await self._send_telegram_alerts(recommendations, results)
            
            # Verificar circuit breaker
            await self._check_circuit_breaker(results)
            
            execution_time = time.time() - start_time
            logger.info(f"Ciclo de trading completado en {execution_time:.2f}s - {len(results)} trades")
            
            return await self._generate_summary(results, market_analysis)
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
            self.metrics.circuit_breaker_activations += 1
            circuit_breaker_active.set(1)
            return {'status': 'error', 'message': str(e)}
        finally:
            self.running = False
    
    async def _filter_signals_by_market_condition(self, signals: List[TradingSignal], market_analysis) -> List[TradingSignal]:
        """Filtra señales según condiciones de mercado"""
        try:
            filtered_signals = []
            for signal in signals:
                # Ajustar confianza según volatilidad
                if market_analysis.condition == MarketCondition.EXTREME_VOLATILITY:
                    if signal.confidence < 0.8:  # Mayor confianza requerida
                        continue
                elif market_analysis.condition == MarketCondition.HIGH_VOLATILITY:
                    if signal.confidence < 0.6:
                        continue
                
                # Ajustar leverage según riesgo
                if market_analysis.risk_score > 0.7:
                    signal.leverage = min(signal.leverage, 5.0)  # Reducir leverage
                
                filtered_signals.append(signal)
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error filtrando señales: {e}")
            return signals
    
    async def _execute_trade(self, signal: TradingSignal, timeline: pd.DataFrame, market_analysis) -> Trade:
        """Ejecuta un trade basado en señal"""
        try:
            start_time = time.time()
            trade_id = f"{signal.symbol}_{int(start_time)}_{signal.signal_type.value}"
            
            # Calcular leverage dinámico
            leverage_result = self.leverage_calculator.calculate_leverage(
                symbol=signal.symbol,
                confidence=signal.confidence,
                volatility=market_analysis.volatility,
                correlation=market_analysis.correlation_matrix.get(signal.symbol, {}),
                drawdown=self.metrics.max_drawdown
            )
            
            # Preparar parámetros de orden
            order_params = {
                'symbol': signal.symbol,
                'side': signal.signal_type.value.lower(),
                'type': 'market',
                'amount': signal.quantity,
                'leverage': leverage_result.leverage,
                'params': {
                    'stopPrice': signal.stop_loss,
                    'takeProfitPrice': signal.take_profit
                }
            }
            
            # Ejecutar orden
            response = await self.exchange.create_order(**order_params)
            api_calls_total.labels(endpoint='create_order', status='success').inc()
            
            trade = Trade(
                trade_id=trade_id,
                symbol=signal.symbol,
                side=signal.signal_type.value,
                quantity=signal.quantity,
                entry_price=float(response['price']),
                exit_price=None,
                leverage=leverage_result.leverage,
                pnl=0.0,
                fees=float(response['fee']['cost']),
                entry_time=int(start_time),
                exit_time=None,
                status='open',
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy_used=signal.strategy_name or 'default',
                metadata={
                    'confidence': signal.confidence,
                    'volatility': market_analysis.volatility,
                    'risk_score': market_analysis.risk_score,
                    'leverage_reasoning': leverage_result.reasoning
                }
            )
            
            # Actualizar métricas
            async with self.lock:
                self.metrics.total_trades += 1
                self.metrics.successful_trades += 1
                self.metrics.total_volume_traded += trade.quantity * trade.entry_price
                self.metrics.api_calls_made += 1
                
                execution_time = time.time() - start_time
                self.metrics.avg_execution_time = (
                    (self.metrics.avg_execution_time * (self.metrics.total_trades - 1) + execution_time) 
                    / self.metrics.total_trades
                )
                self.metrics.max_execution_time = max(self.metrics.max_execution_time, execution_time)
                self.metrics.min_execution_time = min(self.metrics.min_execution_time, execution_time)
            
            return trade
            
        except Exception as e:
            logger.error(f"Error ejecutando trade {signal.symbol}: {e}")
            api_calls_total.labels(endpoint='create_order', status='error').inc()
            
            return Trade(
                trade_id=trade_id,
                symbol=signal.symbol,
                side=signal.signal_type.value,
                quantity=signal.quantity,
                entry_price=0.0,
                exit_price=None,
                leverage=1.0,
                pnl=0.0,
                fees=0.0,
                entry_time=int(time.time()),
                exit_time=None,
                status='failed',
                metadata={'error': str(e)}
            )
    
    async def _update_prometheus_metrics(self, trade: Trade):
        """Actualiza métricas de Prometheus"""
        try:
            trades_total.labels(symbol=trade.symbol, side=trade.side).inc()
            pnl_gauge.labels(symbol=trade.symbol).set(trade.pnl)
            leverage_gauge.labels(symbol=trade.symbol).set(trade.leverage)
            execution_time_histogram.labels(symbol=trade.symbol).observe(trade.entry_time - int(time.time()))
        except Exception as e:
            logger.error(f"Error actualizando métricas Prometheus: {e}")
    
    async def _cache_trade(self, cache_key: str, trade: Trade):
        """Cachea trade en Redis"""
        try:
            if self.redis_client:
                self.redis_client.setex(cache_key, 3600, json.dumps(asdict(trade), default=str))
        except Exception as e:
            logger.error(f"Error cacheando trade: {e}")
    
    async def _get_cached_trade(self, cache_key: str) -> Optional[Trade]:
        """Obtiene trade desde cache"""
        try:
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return Trade(**json.loads(cached_data))
        except Exception as e:
            logger.error(f"Error obteniendo trade desde cache: {e}")
        return None
    
    async def _persist_trade(self, trade: Trade):
        """Persiste trade en SQLite"""
        try:
            await db_manager.save_trade(trade)
        except Exception as e:
            logger.error(f"Error persistiendo trade: {e}")
    
    async def _update_positions(self, trade: Trade):
        """Actualiza posiciones activas"""
        try:
            if trade.status == 'open':
                position = Position(
                    symbol=trade.symbol,
                    side=trade.side,
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    leverage=trade.leverage,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    entry_time=trade.entry_time
                )
                self.positions[trade.trade_id] = position
                self.open_trades[trade.trade_id] = trade
        except Exception as e:
            logger.error(f"Error actualizando posiciones: {e}")
    
    async def _update_metrics(self, trades: List[Trade]):
        """Actualiza métricas basadas en trades"""
        try:
            async with self.lock:
                self.metrics.cache_hit_rate = (
                    self.cache_hits / (self.cache_hits + self.cache_misses) 
                    if (self.cache_hits + self.cache_misses) > 0 else 0
                )
                self.metrics.win_rate = (
                    self.metrics.successful_trades / self.metrics.total_trades 
                    if self.metrics.total_trades > 0 else 0
                )
                
                # Calcular PnL no realizado
                self.metrics.unrealized_pnl = sum(
                    (pos.current_price - pos.entry_price) * pos.quantity * pos.leverage
                    for pos in self.positions.values()
                )
                
                # Actualizar gauge de PnL no realizado
                for symbol in self.symbols:
                    symbol_pnl = sum(
                        (pos.current_price - pos.entry_price) * pos.quantity * pos.leverage
                        for pos in self.positions.values() if pos.symbol == symbol
                    )
                    unrealized_pnl_gauge.labels(symbol=symbol).set(symbol_pnl)
                
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    async def _check_circuit_breaker(self, trades: List[Trade]):
        """Verifica condiciones para activar circuit breaker"""
        try:
            # Verificar pérdidas diarias
            daily_pnl = await self._get_daily_pnl()
            if daily_pnl < -self.max_daily_loss:
                self.circuit_breaker_active = True
                circuit_breaker_active.set(1)
                await telegram_bot.send_message(f"🚨 Circuit breaker activado - Pérdida diaria: {daily_pnl:.2f}%")
                logger.warning("Circuit breaker activado por pérdida diaria excesiva")
            
            # Verificar tasa de error
            error_rate = self.metrics.api_errors / max(self.metrics.api_calls_made, 1)
            if error_rate > 0.5:  # 50% de errores
                self.circuit_breaker_active = True
                circuit_breaker_active.set(1)
                await telegram_bot.send_message(f"🚨 Circuit breaker activado - Tasa de error: {error_rate:.2%}")
                logger.warning("Circuit breaker activado por alta tasa de errores")
            
        except Exception as e:
            logger.error(f"Error verificando circuit breaker: {e}")
    
    async def _get_daily_pnl(self) -> float:
        """Obtiene PnL diario desde SQLite"""
        try:
            today = datetime.now().date()
            trades = await db_manager.get_trades_by_date(today)
            return sum(trade.pnl for trade in trades)
        except Exception as e:
            logger.error(f"Error obteniendo PnL diario: {e}")
            return 0.0
    
    async def _generate_recommendations(self, trades: List[Trade], market_analysis) -> List[str]:
        """Genera recomendaciones basadas en métricas y análisis de mercado"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en métricas
            if self.metrics.successful_trades < self.metrics.total_trades * 0.8:
                recommendations.append("🔧 Revisar configuración de señales - tasa de éxito baja")
            
            if self.metrics.avg_execution_time > 1.0:
                recommendations.append("⚡ Optimizar ejecución - latencia alta")
            
            if self.metrics.total_pnl < 0:
                recommendations.append("⚠️ Revisar parámetros de trading - PnL negativo")
            
            if self.metrics.cache_hit_rate < 0.5:
                recommendations.append("💾 Optimizar caching - tasa de acierto baja")
            
            # Recomendaciones basadas en análisis de mercado
            if market_analysis.condition == MarketCondition.EXTREME_VOLATILITY:
                recommendations.append("🌪️ Volatilidad extrema - considerar reducir posiciones")
            
            if market_analysis.risk_score > 0.7:
                recommendations.append("⚠️ Riesgo alto - revisar estrategias")
            
            if market_analysis.alerts:
                for alert in market_analysis.alerts:
                    recommendations.append(f"🚨 {alert}")
            
            if not recommendations:
                recommendations.append("✅ Rendimiento óptimo - no se requieren cambios")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return ["❌ Error generando recomendaciones"]
    
    async def _send_telegram_alerts(self, recommendations: List[str], trades: List[Trade]):
        """Envía alertas via Telegram"""
        try:
            for rec in recommendations:
                await telegram_bot.send_message(f"📊 Recomendación: {rec}")
            
            # Resumen de trades
            if trades:
                successful_trades = [t for t in trades if t.status == 'open']
                total_pnl = sum(t.pnl for t in trades)
                await telegram_bot.send_message(
                    f"📈 Resumen de trades: {len(successful_trades)}/{len(trades)} exitosos, PnL: {total_pnl:.2f}"
                )
                
        except Exception as e:
            logger.error(f"Error enviando alertas Telegram: {e}")
    
    async def _generate_summary(self, trades: List[Trade], market_analysis) -> Dict[str, Any]:
        """Genera resumen de ejecución"""
        try:
            if not trades:
                return {'status': 'no_trades', 'trades': []}
            
            best_trade = max(trades, key=lambda x: x.pnl) if trades else None
            worst_trade = min(trades, key=lambda x: x.pnl) if trades else None
            
            # Obtener balance de cuenta
            account_balance = await self._get_account_balance()
            
            summary = TradingSummary(
                timestamp=datetime.now(),
                total_trades=len(trades),
                successful_trades=sum(1 for t in trades if t.status == 'open'),
                failed_trades=sum(1 for t in trades if t.status == 'failed'),
                total_pnl=sum(t.pnl for t in trades),
                unrealized_pnl=self.metrics.unrealized_pnl,
                win_rate=self.metrics.win_rate,
                best_trade=best_trade,
                worst_trade=worst_trade,
                active_positions=len(self.positions),
                account_balance=account_balance,
                recommendations=await self._generate_recommendations(trades, market_analysis)
            )
            
            return {
                'status': 'success',
                'summary': asdict(summary),
                'metrics': asdict(self.metrics),
                'market_analysis': {
                    'condition': market_analysis.condition.value,
                    'volatility': market_analysis.volatility,
                    'risk_score': market_analysis.risk_score,
                    'alerts': market_analysis.alerts
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _get_account_balance(self) -> float:
        """Obtiene balance de cuenta"""
        try:
            if self.exchange:
                balance = await self.exchange.fetch_balance()
                account_balance_gauge.labels(currency='USDT').set(balance['USDT']['free'])
                return balance['USDT']['free']
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
        return 0.0
    
    async def get_trading_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de trading"""
        try:
            return {
                'status': 'success',
                'metrics': asdict(self.metrics),
                'active_positions': len(self.positions),
                'open_trades': len(self.open_trades),
                'circuit_breaker_active': self.circuit_breaker_active,
                'account_balance': await self._get_account_balance(),
                'cache_hit_rate': self.metrics.cache_hit_rate,
                'win_rate': self.metrics.win_rate
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def close_position(self, trade_id: str) -> bool:
        """Cierra una posición específica"""
        try:
            if trade_id not in self.open_trades:
                return False
            
            trade = self.open_trades[trade_id]
            order_params = {
                'symbol': trade.symbol,
                'side': 'sell' if trade.side == 'BUY' else 'buy',
                'type': 'market',
                'amount': trade.quantity
            }
            
            response = await self.exchange.create_order(**order_params)
            api_calls_total.labels(endpoint='close_order', status='success').inc()
            
            # Actualizar trade
            trade.exit_price = float(response['price'])
            trade.exit_time = int(time.time())
            trade.status = 'closed'
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity * trade.leverage - trade.fees
            
            # Actualizar métricas
            async with self.lock:
                self.metrics.total_pnl += trade.pnl
                if trade_id in self.positions:
                    del self.positions[trade_id]
                del self.open_trades[trade_id]
            
            # Persistir cambios
            await self._persist_trade(trade)
            
            logger.info(f"Posición cerrada: {trade_id} - PnL: {trade.pnl:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición {trade_id}: {e}")
            api_calls_total.labels(endpoint='close_order', status='error').inc()
            return False
    
    async def close_all_positions(self) -> int:
        """Cierra todas las posiciones abiertas"""
        try:
            closed_count = 0
            for trade_id in list(self.open_trades.keys()):
                if await self.close_position(trade_id):
                    closed_count += 1
                    await asyncio.sleep(0.1)  # Delay entre cierres
            
            logger.info(f"Cerradas {closed_count} posiciones")
            await telegram_bot.send_message(f"🔒 Cerradas {closed_count} posiciones")
            return closed_count
            
        except Exception as e:
            logger.error(f"Error cerrando todas las posiciones: {e}")
            return 0
    
    async def reset_circuit_breaker(self):
        """Resetea el circuit breaker"""
        try:
            self.circuit_breaker_active = False
            circuit_breaker_active.set(0)
            self.metrics.circuit_breaker_activations += 1
            logger.info("Circuit breaker reseteado")
            await telegram_bot.send_message("🔄 Circuit breaker reseteado")
        except Exception as e:
            logger.error(f"Error reseteando circuit breaker: {e}")
    
    async def cleanup(self):
        """Limpia recursos"""
        try:
            if self.exchange:
                await self.exchange.close()
            if self.redis_client:
                self.redis_client.close()
            self.running = False
            logger.info("FuturesExecutionEngine limpiado")
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance"""
        try:
            return {
                'execution_metrics': asdict(self.metrics),
                'active_positions': len(self.positions),
                'open_trades': len(self.open_trades),
                'circuit_breaker_active': self.circuit_breaker_active,
                'cache_hit_rate': self.metrics.cache_hit_rate,
                'win_rate': self.metrics.win_rate,
                'total_volume_traded': self.metrics.total_volume_traded,
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'max_drawdown': self.metrics.max_drawdown
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de performance: {e}")
            return {}
