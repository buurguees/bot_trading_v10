# Ruta: core/trading/enterprise/futures_engine.py
# futures_engine.py - Motor principal de trading de futuros enterprise
# Ubicación: C:\TradingBot_v10\trading\enterprise\futures_engine.py

"""
Motor principal de trading de futuros enterprise.

Características principales:
- Trading autónomo 24/7
- Leverage dinámico 5x-30x
- Long/Short positions automáticas
- Risk management enterprise
- Real-time inference <100ms
- Portfolio management inteligente
"""

import asyncio
import logging
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import threading
import signal
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Imports de trading
import ccxt.async_support as ccxt
from dataclasses import dataclass, asdict

# Prometheus metrics
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Imports del proyecto
sys.path.append(str(Path(__file__).parent.parent.parent))
from trading.enterprise.trading_signal import TradingSignal, SignalType, SignalStrength
from trading.enterprise.position import Position
from trading.enterprise.signal_generator import MLSignalGenerator
from trading.enterprise.position_manager import PositionManager
from trading.enterprise.order_executor import OrderExecutor
from trading.enterprise.leverage_calculator import LeverageCalculator
from trading.enterprise.market_analyzer import MarketAnalyzer
from data.enterprise.stream_collector import EnterpriseDataCollector
from config.enterprise_config import EnterpriseConfigManager

logger = logging.getLogger(__name__)

class EnterpriseFuturesEngine:
    """
    Motor principal de trading de futuros enterprise
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el motor de trading enterprise
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        # Configuración
        self.config_manager = EnterpriseConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Estado del trading
        self.is_trading = False
        self.start_time = None
        self.positions: Dict[str, Position] = {}
        self.account_balance = 0.0
        self.total_pnl = 0.0
        
        # Componentes del sistema
        self.signal_generator = MLSignalGenerator(self.config)
        self.position_manager = PositionManager(self.config)
        self.order_executor = OrderExecutor(self.config)
        self.leverage_calculator = LeverageCalculator(self.config)
        self.market_analyzer = MarketAnalyzer(self.config)
        
        # Exchange client
        self.exchange = None
        self.setup_exchange()
        
        # Data collector
        symbols = [s['symbol'] for s in self.config.trading.symbols.primary]
        self.data_collector = EnterpriseDataCollector(symbols)
        
        # Threading y control
        self.trading_thread = None
        self.stop_trading_event = threading.Event()
        
        # Prometheus metrics
        self.setup_prometheus_metrics()
        
        # Signal handlers
        self.setup_signal_handlers()
        
        logger.info("EnterpriseFuturesEngine inicializado")
    
    def setup_exchange(self):
        """Configura el cliente del exchange"""
        try:
            self.exchange = ccxt.bitget({
                'apiKey': os.getenv('BITGET_API_KEY'),
                'secret': os.getenv('BITGET_SECRET_KEY'),
                'password': os.getenv('BITGET_PASSPHRASE'),
                'sandbox': self.config.trading.mode == 'paper_trading',
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Futuros
                    'marginMode': 'isolated'
                }
            })
            
            logger.info("Exchange configurado exitosamente")
            
        except Exception as e:
            logger.error(f"Error configurando exchange: {e}")
            raise
    
    def setup_prometheus_metrics(self):
        """Configura métricas de Prometheus"""
        # Métricas de trading
        self.trades_total = Counter(
            'trades_executed_total',
            'Total de trades ejecutados',
            ['symbol', 'side', 'status']
        )
        
        self.account_balance_gauge = Gauge(
            'account_balance_usd',
            'Balance de cuenta en USD'
        )
        
        self.unrealized_pnl_gauge = Gauge(
            'unrealized_pnl_usd',
            'PnL no realizado en USD'
        )
        
        self.open_positions_gauge = Gauge(
            'open_positions_count',
            'Número de posiciones abiertas',
            ['symbol', 'side']
        )
        
        self.signal_confidence_histogram = Histogram(
            'signal_confidence',
            'Distribución de confianza de señales ML',
            ['symbol', 'action']
        )
        
        self.order_execution_time = Histogram(
            'order_execution_time_seconds',
            'Tiempo de ejecución de órdenes',
            ['symbol', 'order_type'],
            buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        )
        
        # Iniciar servidor Prometheus
        if self.config.trading.prometheus.enabled:
            port = self.config.trading.prometheus.port
            start_http_server(port)
            logger.info(f"Prometheus metrics server iniciado en puerto {port}")
    
    def setup_signal_handlers(self):
        """Configura handlers para graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Iniciando graceful shutdown...")
            self.stop_trading()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_autonomous_trading(
        self,
        duration_hours: Optional[int] = None,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Inicia trading autónomo enterprise
        
        Args:
            duration_hours: Duración del trading (None para indefinido)
            symbols: Lista de símbolos para tradear
            
        Returns:
            Resumen de resultados del trading
        """
        try:
            logger.info("🚀 Iniciando trading autónomo enterprise")
            
            # Preparar configuración
            self.start_time = datetime.now()
            end_time = None
            if duration_hours:
                end_time = self.start_time + timedelta(hours=duration_hours)
            
            if symbols is None:
                symbols = [s['symbol'] for s in self.config.trading.symbols.primary]
            
            # Validaciones previas
            await self.pre_trading_checks()
            
            # Inicializar account balance
            await self.update_account_balance()
            
            # Iniciar data collection
            await self.data_collector.start_collection()
            
            # Iniciar loop principal de trading
            self.is_trading = True
            
            def trading_worker():
                """Worker function para trading"""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(
                        self.trading_loop(symbols, end_time)
                    )
                except Exception as e:
                    logger.error(f"Error en trading worker: {e}")
                finally:
                    loop.close()
            
            # Iniciar hilo de trading
            self.trading_thread = threading.Thread(
                target=trading_worker,
                daemon=True
            )
            self.trading_thread.start()
            
            logger.info("✅ Trading autónomo iniciado exitosamente")
            
            # Monitorear hasta que termine
            while self.is_trading and self.trading_thread.is_alive():
                await asyncio.sleep(10)
                await self.update_metrics()
            
            # Obtener resultados finales
            results = await self.get_trading_summary()
            
            logger.info("🏁 Trading autónomo completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en trading autónomo: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def trading_loop(
        self,
        symbols: List[str],
        end_time: Optional[datetime]
    ):
        """
        Loop principal de trading
        """
        logger.info("🔄 Iniciando loop principal de trading")
        
        while self.is_trading and not self.stop_trading_event.is_set():
            try:
                # Verificar si hemos alcanzado el tiempo límite
                if end_time and datetime.now() >= end_time:
                    logger.info("⏰ Tiempo de trading completado")
                    break
                
                # Análisis de mercado
                market_conditions = await self.market_analyzer.analyze_market()
                
                # Generar señales para todos los símbolos
                signals = await self.generate_signals(symbols)
                
                # Filtrar señales según condiciones de mercado
                filtered_signals = await self.filter_signals(signals, market_conditions)
                
                # Ejecutar trades basados en señales
                await self.execute_signal_trades(filtered_signals)
                
                # Gestionar posiciones existentes
                await self.manage_existing_positions()
                
                # Actualizar métricas
                await self.update_metrics()
                
                # Log de estado
                await self.log_trading_status()
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(self.config.trading.timing.analysis_frequency_seconds)
                
            except Exception as e:
                logger.error(f"Error en trading loop: {e}")
                await asyncio.sleep(30)  # Pausa en caso de error
    
    async def generate_signals(self, symbols: List[str]) -> List[TradingSignal]:
        """
        Genera señales de trading para todos los símbolos
        """
        signals = []
        
        for symbol in symbols:
            try:
                # Obtener datos actuales del mercado
                market_data = await self.data_collector.get_latest_data(symbol)
                
                if market_data is None:
                    continue
                
                # Generar señal ML
                signal_start_time = time.time()
                ml_signal = await self.signal_generator.generate_signal(
                    symbol, market_data
                )
                signal_time = time.time() - signal_start_time
                
                # Verificar que la inferencia sea rápida (<100ms)
                if signal_time > 0.1:
                    logger.warning(f"Señal ML lenta para {symbol}: {signal_time:.3f}s")
                
                if ml_signal:
                    signals.append(ml_signal)
                    
                    # Actualizar métricas Prometheus
                    self.signal_confidence_histogram.labels(
                        symbol=symbol,
                        action=ml_signal.action
                    ).observe(ml_signal.confidence)
                
            except Exception as e:
                logger.error(f"Error generando señal para {symbol}: {e}")
        
        return signals
    
    async def filter_signals(
        self,
        signals: List[TradingSignal],
        market_conditions: Dict[str, Any]
    ) -> List[TradingSignal]:
        """
        Filtra señales según condiciones de mercado y riesgo
        """
        filtered_signals = []
        
        for signal in signals:
            try:
                # Filtro de confianza mínima
                min_confidence = self.config.trading.strategies.ml_strategy.signals.min_confidence
                if signal.confidence < min_confidence:
                    continue
                
                # Filtro de volatilidad extrema
                if market_conditions.get('volatility', 0) > 0.1:  # >10% volatilidad
                    if signal.action != 'HOLD':
                        logger.info(f"Señal {signal.action} filtrada por alta volatilidad")
                        continue
                
                # Filtro de volumen mínimo
                volume_24h = market_conditions.get('volume_24h', 0)
                if volume_24h < 1000000:  # <$1M volumen
                    continue
                
                # Verificar si ya hay posición en este símbolo
                if signal.symbol in self.positions:
                    # Si hay posición contraria con alta confianza, permitir
                    current_position = self.positions[signal.symbol]
                    if ((current_position.side == 'long' and signal.action == 'SELL') or
                        (current_position.side == 'short' and signal.action == 'BUY')):
                        if signal.confidence > 0.8:  # Solo con alta confianza
                            filtered_signals.append(signal)
                    continue
                
                filtered_signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error filtrando señal {signal.symbol}: {e}")
        
        return filtered_signals
    
    async def execute_signal_trades(self, signals: List[TradingSignal]):
        """
        Ejecuta trades basados en las señales filtradas
        """
        for signal in signals:
            try:
                if signal.action == 'HOLD':
                    continue
                
                # Calcular tamaño de posición
                position_size_usd = await self.calculate_position_size(signal)
                
                if position_size_usd < self.get_min_position_size(signal.symbol):
                    continue
                
                # Calcular leverage dinámico
                leverage = await self.leverage_calculator.calculate_optimal_leverage(
                    symbol=signal.symbol,
                    confidence=signal.confidence,
                    volatility=signal.predicted_volatility
                )
                
                # Ejecutar trade
                await self.execute_trade(
                    symbol=signal.symbol,
                    action=signal.action,
                    size_usd=position_size_usd,
                    leverage=leverage,
                    signal=signal
                )
                
            except Exception as e:
                logger.error(f"Error ejecutando trade para señal {signal.symbol}: {e}")
    
    async def execute_trade(
        self,
        symbol: str,
        action: str,
        size_usd: float,
        leverage: int,
        signal: TradingSignal,
        order_type: str = 'MARKET'
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta un trade individual
        """
        try:
            execution_start_time = time.time()
            
            # Verificar si hay que cerrar posición existente primero
            if symbol in self.positions:
                await self.close_position(self.positions[symbol], "signal_change")
            
            # Configurar leverage
            await self.exchange.set_leverage(leverage, symbol)
            
            # Obtener precio actual
            ticker = await self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            
            # Calcular cantidad en contratos
            contract_size = self.get_contract_size(symbol)
            quantity = (size_usd / price) / contract_size
            
            # Redondear a tamaño mínimo válido
            quantity = self.round_to_valid_quantity(symbol, quantity)
            
            # Determinar side para futures
            side = 'buy' if action == 'BUY' else 'sell'
            position_side = 'long' if action == 'BUY' else 'short'
            
            # Preparar parámetros de orden
            order_params = {
                'marginMode': 'isolated',
                'positionSide': position_side
            }
            
            # Ejecutar orden usando order_executor
            order = await self.order_executor.execute_order(
                symbol=symbol,
                side=side,
                amount=quantity,
                order_type=order_type,
                params=order_params
            )
            
            execution_time = time.time() - execution_start_time
            
            # Actualizar métricas
            self.trades_total.labels(
                symbol=symbol,
                side=side,
                status='filled' if order and order.get('status') == 'closed' else 'error'
            ).inc()
            
            self.order_execution_time.labels(
                symbol=symbol,
                order_type=order_type.lower()
            ).observe(execution_time)
            
            # Actualizar posición local si se ejecutó correctamente
            if order and order.get('status') == 'closed':
                await self.update_position_from_order(order, leverage, signal)
                
                # Configurar stop loss y take profit
                await self.set_stop_loss_take_profit(symbol, order, leverage)
            
            logger.info(
                f"✅ Trade ejecutado: {action} {quantity} {symbol} "
                f"@ {price} (Leverage: {leverage}x) en {execution_time:.3f}s"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando trade {action} {symbol}: {e}")
            
            # Métrica de error
            self.trades_total.labels(
                symbol=symbol,
                side=action.lower(),
                status='error'
            ).inc()
            
            return None
    
    async def manage_existing_positions(self):
        """
        Gestiona posiciones existentes (stop loss, take profit, etc.)
        """
        for symbol, position in list(self.positions.items()):
            try:
                # Actualizar precio actual
                ticker = await self.exchange.fetch_ticker(symbol)
                position.current_price = ticker['last']
                
                # Calcular PnL actualizado
                await self.update_position_pnl(position)
                
                # Verificar condiciones de salida
                should_close, reason = await self.should_close_position(position)
                
                if should_close:
                    await self.close_position(position, reason)
                    continue
                
                # Actualizar trailing stop
                if position.stop_loss:
                    new_stop_loss = await self.calculate_trailing_stop(position)
                    if new_stop_loss and new_stop_loss != position.stop_loss:
                        await self.update_stop_loss(position, new_stop_loss)
                
                # Verificar duración máxima
                max_duration = self.config.trading.futures.positions.max_position_duration_hours
                if position.duration_hours > max_duration:
                    await self.close_position(position, "max_duration_exceeded")
                
            except Exception as e:
                logger.error(f"Error gestionando posición {symbol}: {e}")
    
    async def should_close_position(self, position: Position) -> Tuple[bool, str]:
        """
        Determina si una posición debe cerrarse
        """
        # Verificar stop loss
        if position.stop_loss:
            if position.side == 'long' and position.current_price <= position.stop_loss:
                return True, "stop_loss_triggered"
            elif position.side == 'short' and position.current_price >= position.stop_loss:
                return True, "stop_loss_triggered"
        
        # Verificar take profit
        if position.take_profit:
            if position.side == 'long' and position.current_price >= position.take_profit:
                return True, "take_profit_triggered"
            elif position.side == 'short' and position.current_price <= position.take_profit:
                return True, "take_profit_triggered"
        
        # Verificar señal ML contraria
        latest_signal = await self.signal_generator.get_latest_signal(position.symbol)
        if latest_signal:
            if (position.side == 'long' and latest_signal.action == 'SELL' and 
                latest_signal.confidence > 0.8):
                return True, "ml_signal_exit"
            elif (position.side == 'short' and latest_signal.action == 'BUY' and 
                  latest_signal.confidence > 0.8):
                return True, "ml_signal_exit"
        
        # Verificar riesgo de margen
        margin_ratio = await self.calculate_margin_ratio(position)
        if margin_ratio > 0.8:  # 80% del margen usado
            return True, "margin_risk"
        
        return False, ""
    
    async def close_position(self, position: Position, reason: str):
        """
        Cierra una posición
        """
        try:
            symbol = position.symbol
            
            # Usar order_executor para cerrar posición
            order = await self.order_executor.close_position(position)
            
            if order:
                # Calcular PnL realizado
                if position.side == 'long':
                    realized_pnl = (position.current_price - position.entry_price) * position.size
                else:
                    realized_pnl = (position.entry_price - position.current_price) * position.size
                
                # Aplicar leverage al PnL
                realized_pnl *= position.leverage
                
                # Actualizar total PnL
                self.total_pnl += realized_pnl
                
                # Remover posición
                del self.positions[symbol]
                
                # Actualizar métricas
                self.open_positions_gauge.labels(
                    symbol=symbol,
                    side=position.side
                ).set(0)
                
                logger.info(
                    f"🔒 Posición cerrada: {symbol} {position.side} "
                    f"PnL: ${realized_pnl:.2f} Razón: {reason}"
                )
            
        except Exception as e:
            logger.error(f"Error cerrando posición {position.symbol}: {e}")
    
    async def calculate_position_size(self, signal: TradingSignal) -> float:
        """
        Calcula el tamaño de posición basado en la señal y risk management
        """
        # Configuración de risk management
        max_risk_per_trade = self.config.risk_management.capital_management.max_risk_per_trade_pct
        
        # Ajustar por confianza
        confidence_multiplier = min(signal.confidence * 1.5, 1.0)
        
        # Calcular tamaño base
        base_size = self.account_balance * max_risk_per_trade * confidence_multiplier
        
        # Obtener límites por símbolo
        max_position_size = self.get_max_position_size(signal.symbol)
        min_position_size = self.get_min_position_size(signal.symbol)
        
        # Aplicar límites
        position_size = max(min(base_size, max_position_size), min_position_size)
        
        return position_size
    
    async def set_stop_loss_take_profit(
        self,
        symbol: str,
        order: Dict[str, Any],
        leverage: int
    ):
        """
        Configura stop loss y take profit para una posición
        """
        try:
            entry_price = order['price']
            side = order['side']
            
            # Calcular stop loss basado en volatilidad
            volatility = await self.get_symbol_volatility(symbol)
            stop_loss_distance = volatility * 2.0  # 2x volatilidad
            
            # Ajustar por leverage (mayor leverage = stop loss más cercano)
            stop_loss_distance *= (10 / leverage)  # Base leverage 10
            
            if side == 'buy':  # Long position
                stop_loss_price = entry_price * (1 - stop_loss_distance)
                take_profit_price = entry_price * (1 + stop_loss_distance * 2)  # R:R 1:2
            else:  # Short position
                stop_loss_price = entry_price * (1 + stop_loss_distance)
                take_profit_price = entry_price * (1 - stop_loss_distance * 2)
            
            # Usar order_executor para crear órdenes SL/TP
            await self.order_executor.set_stop_loss_take_profit(
                symbol, order, stop_loss_price, take_profit_price
            )
            
            # Actualizar posición local
            if symbol in self.positions:
                self.positions[symbol].stop_loss = stop_loss_price
                self.positions[symbol].take_profit = take_profit_price
            
            logger.info(
                f"🛡️ SL/TP configurado para {symbol}: "
                f"SL: ${stop_loss_price:.4f} TP: ${take_profit_price:.4f}"
            )
            
        except Exception as e:
            logger.error(f"Error configurando SL/TP para {symbol}: {e}")
    
    # Métodos auxiliares y de utilidad
    async def update_account_balance(self):
        """Actualiza el balance de la cuenta"""
        try:
            balance = await self.exchange.fetch_balance()
            self.account_balance = balance['USDT']['total']
        except Exception as e:
            logger.error(f"Error obteniendo balance de cuenta: {e}")
    
    async def pre_trading_checks(self):
        """Verificaciones previas al inicio del trading"""
        logger.info("🔍 Ejecutando verificaciones previas...")
        
        # Verificar conexión al exchange
        try:
            await self.exchange.load_markets()
            logger.info("✅ Conexión al exchange verificada")
        except Exception as e:
            raise Exception(f"Error conectando al exchange: {e}")
        
        # Verificar balance mínimo
        await self.update_account_balance()
        min_balance = self.config.risk_management.capital_management.min_balance_usd
        if self.account_balance < min_balance:
            raise Exception(f"Balance insuficiente: ${self.account_balance} < ${min_balance}")
        
        logger.info(f"✅ Balance verificado: ${self.account_balance}")
        
        # Verificar modelos ML
        model_status = await self.signal_generator.health_check()
        if not model_status.get('healthy', False):
            raise Exception("Modelos ML no están saludables")
        
        logger.info("✅ Modelos ML verificados")
        
        logger.info("✅ Todas las verificaciones previas completadas")
    
    def stop_trading(self):
        """Detiene el trading de forma gradual"""
        logger.info("🛑 Deteniendo trading...")
        self.is_trading = False
        self.stop_trading_event.set()
    
    async def emergency_stop(self):
        """Parada de emergencia - cierra todas las posiciones"""
        logger.warning("🚨 PARADA DE EMERGENCIA ACTIVADA")
        
        # Detener trading
        self.stop_trading()
        
        # Cerrar todas las posiciones
        for position in list(self.positions.values()):
            await self.close_position(position, "emergency_stop")
        
        # Cancelar todas las órdenes pendientes
        symbols = [s['symbol'] for s in self.config.trading.symbols.primary]
        for symbol in symbols:
            try:
                orders = await self.exchange.fetch_open_orders(symbol)
                for order in orders:
                    await self.exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                logger.error(f"Error cancelando órdenes {symbol}: {e}")
    
    # Métodos auxiliares adicionales
    def get_contract_size(self, symbol: str) -> float:
        """Obtiene el tamaño del contrato para un símbolo"""
        contract_sizes = {
            'BTCUSDT': 0.001,
            'ETHUSDT': 0.01,
            'ADAUSDT': 1.0,
            'SOLUSDT': 0.1,
            'DOGEUSDT': 100.0
        }
        return contract_sizes.get(symbol, 1.0)
    
    def round_to_valid_quantity(self, symbol: str, quantity: float) -> float:
        """Redondea la cantidad a un valor válido para el exchange"""
        # Implementar lógica de redondeo según las reglas del exchange
        return round(quantity, 3)
    
    def get_max_position_size(self, symbol: str) -> float:
        """Obtiene el tamaño máximo de posición para un símbolo"""
        for s in self.config.trading.symbols.primary:
            if s['symbol'] == symbol:
                return s['max_position_size_usd']
        return 1000.0  # Default
    
    def get_min_position_size(self, symbol: str) -> float:
        """Obtiene el tamaño mínimo de posición para un símbolo"""
        for s in self.config.trading.symbols.primary:
            if s['symbol'] == symbol:
                return s['min_position_size_usd']
        return 10.0  # Default
    
    async def update_position_pnl(self, position: Position):
        """Actualiza el PnL de una posición"""
        if position.side == 'long':
            pnl = (position.current_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - position.current_price) * position.size
        
        position.unrealized_pnl = pnl * position.leverage
        position.unrealized_pnl_pct = (position.unrealized_pnl / (position.entry_price * position.size)) * 100
    
    async def calculate_trailing_stop(self, position: Position) -> Optional[float]:
        """Calcula el nuevo trailing stop para una posición"""
        # Implementar lógica de trailing stop
        return None
    
    async def update_stop_loss(self, position: Position, new_stop_loss: float):
        """Actualiza el stop loss de una posición"""
        position.stop_loss = new_stop_loss
        # Actualizar en el exchange usando order_executor
    
    async def calculate_margin_ratio(self, position: Position) -> float:
        """Calcula el ratio de margen usado para una posición"""
        # Implementar cálculo de ratio de margen
        return 0.0
    
    async def get_symbol_volatility(self, symbol: str) -> float:
        """Obtiene la volatilidad actual de un símbolo"""
        # Implementar cálculo de volatilidad
        return 0.02  # 2% default
    
    async def update_position_from_order(self, order: Dict[str, Any], leverage: int, signal: TradingSignal):
        """Actualiza la posición local desde una orden ejecutada"""
        # Implementar actualización de posición
        pass
    
    async def update_metrics(self):
        """Actualiza las métricas de Prometheus"""
        # Actualizar balance
        self.account_balance_gauge.set(self.account_balance)
        
        # Actualizar PnL no realizado
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.unrealized_pnl_gauge.set(total_unrealized_pnl)
        
        # Actualizar posiciones abiertas
        for symbol, position in self.positions.items():
            self.open_positions_gauge.labels(
                symbol=symbol,
                side=position.side
            ).set(1)
    
    async def log_trading_status(self):
        """Log del estado actual del trading"""
        logger.info(
            f"📊 Estado: Balance: ${self.account_balance:.2f} | "
            f"Posiciones: {len(self.positions)} | "
            f"PnL Total: ${self.total_pnl:.2f}"
        )
    
    async def get_trading_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de resultados del trading"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': datetime.now().isoformat(),
            'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
            'total_trades': self.trades_total._value.sum(),
            'total_pnl': self.total_pnl,
            'final_balance': self.account_balance,
            'positions_closed': len(self.positions),
            'success_rate': 0.0  # Calcular basado en trades exitosos
        }
    
    async def cleanup(self):
        """Limpieza al finalizar el trading"""
        try:
            # Detener data collection
            if self.data_collector:
                await self.data_collector.stop_collection()
            
            # Cerrar conexión del exchange
            if self.exchange:
                await self.exchange.close()
            
            logger.info("✅ Cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")
