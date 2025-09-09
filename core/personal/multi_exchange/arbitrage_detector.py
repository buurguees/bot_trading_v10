# Ruta: core/personal/multi_exchange/arbitrage_detector.py
"""
Arbitrage Detector - Bot Trading v10 Personal
=============================================

Detector de oportunidades de arbitraje entre exchanges con:
- Análisis en tiempo real de spreads
- Cálculo de profitabilidad neta
- Gestión de costos de transacción
- Alertas automáticas
- Ejecución de arbitraje
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge
import numpy as np

logger = logging.getLogger(__name__)

# Métricas Prometheus
arbitrage_opportunities = Counter('trading_bot_arbitrage_opportunities_total', 'Oportunidades de arbitraje detectadas', ['symbol', 'exchange_pair'])
arbitrage_trades = Counter('trading_bot_arbitrage_trades_total', 'Trades de arbitraje ejecutados', ['symbol', 'exchange_pair'])
arbitrage_profit = Gauge('trading_bot_arbitrage_profit_usdt', 'Profit de arbitraje en USDT', ['symbol', 'exchange_pair'])
arbitrage_latency = Histogram('trading_bot_arbitrage_latency_seconds', 'Latencia de detección de arbitraje', ['symbol'])

@dataclass
class ArbitrageOpportunity:
    """Oportunidad de arbitraje detectada"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    profit_usdt: float
    min_amount: float
    max_amount: float
    timestamp: datetime
    confidence: float

class ArbitrageDetector:
    """Detector de oportunidades de arbitraje entre exchanges"""
    
    def __init__(self, exchange_manager, config: Dict[str, Any]):
        self.exchange_manager = exchange_manager
        self.config = config
        self.opportunities = []
        self.is_running = False
        self.last_analysis = {}
        
        # Configuración de arbitraje
        self.min_profit_pct = config.get('min_profit_pct', 0.1)
        self.max_position_size = config.get('max_position_size', 1000)
        self.symbols = config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        
        # Costos de transacción (estimados)
        self.trading_fees = {
            'bitget': 0.001,  # 0.1%
            'binance': 0.001,  # 0.1%
        }
        
        # Historial de spreads para análisis
        self.spread_history = {}
        
        logger.info("ArbitrageDetector inicializado")
    
    async def start(self):
        """Inicia el detector de arbitraje"""
        try:
            logger.info("Iniciando ArbitrageDetector...")
            self.is_running = True
            
            # Iniciar análisis continuo
            asyncio.create_task(self._continuous_analysis())
            
            logger.info("ArbitrageDetector iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando ArbitrageDetector: {e}")
            raise
    
    async def stop(self):
        """Detiene el detector de arbitraje"""
        try:
            logger.info("Deteniendo ArbitrageDetector...")
            self.is_running = False
            logger.info("ArbitrageDetector detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo ArbitrageDetector: {e}")
    
    async def _continuous_analysis(self):
        """Análisis continuo de oportunidades de arbitraje"""
        while self.is_running:
            try:
                await self._analyze_all_symbols()
                await asyncio.sleep(5)  # Análisis cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error en análisis continuo: {e}")
                await asyncio.sleep(10)
    
    async def _analyze_all_symbols(self):
        """Analiza todas las oportunidades de arbitraje"""
        for symbol in self.symbols:
            try:
                await self._analyze_symbol(symbol)
            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
    
    async def _analyze_symbol(self, symbol: str):
        """Analiza oportunidades de arbitraje para un símbolo específico"""
        start_time = time.time()
        
        try:
            # Obtener order books de todos los exchanges
            order_books = await self.exchange_manager.get_order_book(symbol)
            
            if len(order_books) < 2:
                return  # Necesitamos al menos 2 exchanges
            
            # Encontrar mejores precios
            best_prices = self._find_best_prices(order_books)
            
            if not best_prices:
                return
            
            # Calcular oportunidad de arbitraje
            opportunity = self._calculate_arbitrage_opportunity(symbol, best_prices)
            
            if opportunity and opportunity.spread_pct >= self.min_profit_pct:
                # Registrar oportunidad
                self.opportunities.append(opportunity)
                
                # Actualizar métricas
                arbitrage_opportunities.labels(
                    symbol=symbol,
                    exchange_pair=f"{opportunity.buy_exchange}-{opportunity.sell_exchange}"
                ).inc()
                
                arbitrage_profit.labels(
                    symbol=symbol,
                    exchange_pair=f"{opportunity.buy_exchange}-{opportunity.sell_exchange}"
                ).set(opportunity.profit_usdt)
                
                # Log de oportunidad
                logger.info(
                    f"💰 Arbitraje detectado: {symbol} "
                    f"Comprar en {opportunity.buy_exchange} a {opportunity.buy_price:.4f} "
                    f"Vender en {opportunity.sell_exchange} a {opportunity.sell_price:.4f} "
                    f"Spread: {opportunity.spread_pct:.2f}% "
                    f"Profit: ${opportunity.profit_usdt:.2f}"
                )
                
                # Actualizar historial de spreads
                self._update_spread_history(symbol, opportunity)
            
            # Calcular latencia
            latency = time.time() - start_time
            arbitrage_latency.labels(symbol=symbol).observe(latency)
            
        except Exception as e:
            logger.error(f"Error analizando arbitraje para {symbol}: {e}")
    
    def _find_best_prices(self, order_books: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Encuentra los mejores precios de compra y venta"""
        best_bid = None
        best_ask = None
        
        for exchange_id, order_book in order_books.items():
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                continue
            
            bids = order_book['bids']
            asks = order_book['asks']
            
            if not bids or not asks:
                continue
            
            # Mejor bid (precio de venta más alto)
            bid_price, bid_amount = bids[0]
            if best_bid is None or bid_price > best_bid['price']:
                best_bid = {
                    'exchange': exchange_id,
                    'price': bid_price,
                    'amount': bid_amount
                }
            
            # Mejor ask (precio de compra más bajo)
            ask_price, ask_amount = asks[0]
            if best_ask is None or ask_price < best_ask['price']:
                best_ask = {
                    'exchange': exchange_id,
                    'price': ask_price,
                    'amount': ask_amount
                }
        
        if best_bid and best_ask and best_bid['exchange'] != best_ask['exchange']:
            return {
                'best_bid': best_bid,
                'best_ask': best_ask
            }
        
        return None
    
    def _calculate_arbitrage_opportunity(self, symbol: str, best_prices: Dict[str, Any]) -> Optional[ArbitrageOpportunity]:
        """Calcula la oportunidad de arbitraje"""
        best_bid = best_prices['best_bid']
        best_ask = best_prices['best_ask']
        
        # Precios
        buy_price = best_ask['price']
        sell_price = best_bid['price']
        
        # Spread básico
        spread_pct = ((sell_price - buy_price) / buy_price) * 100
        
        if spread_pct < self.min_profit_pct:
            return None
        
        # Calcular costos de transacción
        buy_fee = self.trading_fees.get(best_ask['exchange'], 0.001)
        sell_fee = self.trading_fees.get(best_bid['exchange'], 0.001)
        
        # Spread neto considerando fees
        net_spread_pct = spread_pct - (buy_fee + sell_fee) * 100
        
        if net_spread_pct < self.min_profit_pct:
            return None
        
        # Calcular profit en USDT
        max_amount = min(best_ask['amount'], best_bid['amount'], self.max_position_size)
        profit_usdt = (sell_price - buy_price) * max_amount - (buy_price * max_amount * buy_fee) - (sell_price * max_amount * sell_fee)
        
        # Calcular confianza basada en historial
        confidence = self._calculate_confidence(symbol, spread_pct)
        
        return ArbitrageOpportunity(
            symbol=symbol,
            buy_exchange=best_ask['exchange'],
            sell_exchange=best_bid['exchange'],
            buy_price=buy_price,
            sell_price=sell_price,
            spread_pct=net_spread_pct,
            profit_usdt=profit_usdt,
            min_amount=0.001,  # Mínimo para evitar dust
            max_amount=max_amount,
            timestamp=datetime.now(),
            confidence=confidence
        )
    
    def _calculate_confidence(self, symbol: str, spread_pct: float) -> float:
        """Calcula la confianza de la oportunidad basada en historial"""
        if symbol not in self.spread_history:
            return 0.5  # Confianza media para nuevos símbolos
        
        history = self.spread_history[symbol]
        if len(history) < 5:
            return 0.5
        
        # Calcular confianza basada en consistencia del spread
        recent_spreads = history[-10:]  # Últimos 10 spreads
        mean_spread = np.mean(recent_spreads)
        std_spread = np.std(recent_spreads)
        
        # Confianza alta si el spread actual es consistente con el historial
        if std_spread == 0:
            return 0.9
        
        z_score = abs(spread_pct - mean_spread) / std_spread
        confidence = max(0.1, min(0.9, 1.0 - (z_score / 3.0)))  # Normalizar entre 0.1 y 0.9
        
        return confidence
    
    def _update_spread_history(self, symbol: str, opportunity: ArbitrageOpportunity):
        """Actualiza el historial de spreads para un símbolo"""
        if symbol not in self.spread_history:
            self.spread_history[symbol] = []
        
        self.spread_history[symbol].append(opportunity.spread_pct)
        
        # Mantener solo los últimos 100 spreads
        if len(self.spread_history[symbol]) > 100:
            self.spread_history[symbol] = self.spread_history[symbol][-100:]
    
    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Ejecuta una oportunidad de arbitraje"""
        try:
            logger.info(f"🚀 Ejecutando arbitraje: {opportunity.symbol}")
            
            # Calcular cantidad a tradear
            amount = min(opportunity.max_amount, self.max_position_size)
            
            # Ejecutar trades simultáneamente
            tasks = [
                self.exchange_manager.execute_trade(
                    opportunity.buy_exchange,
                    opportunity.symbol,
                    'buy',
                    amount
                ),
                self.exchange_manager.execute_trade(
                    opportunity.sell_exchange,
                    opportunity.symbol,
                    'sell',
                    amount
                )
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verificar resultados
            buy_result = results[0]
            sell_result = results[1]
            
            if (isinstance(buy_result, Exception) or 
                isinstance(sell_result, Exception) or
                not buy_result.get('success', False) or
                not sell_result.get('success', False)):
                
                logger.error(f"❌ Error ejecutando arbitraje: {opportunity.symbol}")
                return {
                    'success': False,
                    'error': 'Error ejecutando trades de arbitraje'
                }
            
            # Actualizar métricas
            arbitrage_trades.labels(
                symbol=opportunity.symbol,
                exchange_pair=f"{opportunity.buy_exchange}-{opportunity.sell_exchange}"
            ).inc()
            
            logger.info(f"✅ Arbitraje ejecutado exitosamente: {opportunity.symbol}")
            
            return {
                'success': True,
                'buy_order': buy_result['order'],
                'sell_order': sell_result['order'],
                'profit_estimated': opportunity.profit_usdt,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando arbitraje: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_opportunities(self, symbol: str = None, min_confidence: float = 0.0) -> List[ArbitrageOpportunity]:
        """Obtiene las oportunidades de arbitraje detectadas"""
        opportunities = self.opportunities
        
        if symbol:
            opportunities = [opp for opp in opportunities if opp.symbol == symbol]
        
        if min_confidence > 0:
            opportunities = [opp for opp in opportunities if opp.confidence >= min_confidence]
        
        # Ordenar por profit descendente
        opportunities.sort(key=lambda x: x.profit_usdt, reverse=True)
        
        return opportunities
    
    def get_spread_statistics(self, symbol: str) -> Dict[str, Any]:
        """Obtiene estadísticas de spreads para un símbolo"""
        if symbol not in self.spread_history:
            return {}
        
        spreads = self.spread_history[symbol]
        
        return {
            'symbol': symbol,
            'count': len(spreads),
            'mean': np.mean(spreads),
            'std': np.std(spreads),
            'min': np.min(spreads),
            'max': np.max(spreads),
            'current': spreads[-1] if spreads else 0
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de rendimiento del detector"""
        total_opportunities = len(self.opportunities)
        profitable_opportunities = len([opp for opp in self.opportunities if opp.profit_usdt > 0])
        
        return {
            'total_opportunities': total_opportunities,
            'profitable_opportunities': profitable_opportunities,
            'success_rate': profitable_opportunities / total_opportunities if total_opportunities > 0 else 0,
            'total_profit_estimated': sum(opp.profit_usdt for opp in self.opportunities),
            'symbols_monitored': len(self.symbols),
            'is_running': self.is_running
        }
