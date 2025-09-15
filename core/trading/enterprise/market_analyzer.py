# Ruta: core/trading/enterprise/market_analyzer.py
# market_analyzer.py - Analizador de mercado en tiempo real
# Ubicación: C:\TradingBot_v10\core\trading\enterprise\market_analyzer.py

"""
Analizador de mercado en tiempo real para trading enterprise.

Características principales:
- Análisis de condiciones de mercado
- Detección de volatilidad extrema
- Análisis de correlación entre activos
- Detección de tendencias y reversiones
- Análisis de volumen y liquidez
- Alertas de condiciones anómalas via Telegram
- Redis caching para análisis
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
import redis
try:
    import talib
except ImportError:
    talib = None
from core.data.database import db_manager
from control.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """Condiciones del mercado"""
    EXTREME_VOLATILITY = "extreme_volatility"
    HIGH_VOLATILITY = "high_volatility"
    NORMAL = "normal"
    LOW_VOLATILITY = "low_volatility"
    STABLE = "stable"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"

class TrendDirection(Enum):
    """Dirección de la tendencia"""
    STRONG_UP = "strong_up"
    WEAK_UP = "weak_up"
    NEUTRAL = "neutral"
    WEAK_DOWN = "weak_down"
    STRONG_DOWN = "strong_down"

@dataclass
class MarketAnalysis:
    """Resultado del análisis de mercado"""
    timestamp: datetime
    condition: MarketCondition
    volatility: float
    trend_direction: TrendDirection
    volume_ratio: float
    correlation_matrix: Dict[str, Dict[str, float]]
    liquidity_score: float
    momentum_score: float
    risk_score: float
    alerts: List[str]
    recommendations: List[str]

@dataclass
class SymbolAnalysis:
    """Análisis de un símbolo específico"""
    symbol: str
    price_change_1h: float
    price_change_4h: float
    price_change_24h: float
    volatility_24h: float
    volume_24h: float
    volume_ratio: float
    rsi: float
    macd_signal: str
    bollinger_position: float
    trend_strength: float
    support_resistance: Dict[str, float]
    ichimoku_signal: str  # Añadido para Ichimoku Cloud

class MarketAnalyzer:
    """
    Analizador de mercado en tiempo real para trading enterprise
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el analizador de mercado
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.symbols = config.trading.symbols
        self.analysis_history: List[MarketAnalysis] = []
        self.symbol_analysis_history: Dict[str, List[SymbolAnalysis]] = {s: [] for s in self.symbols}
        self.total_analyses = 0
        self.alert_count = 0
        self.avg_analysis_time = 0.0
        
        # Redis para caching
        self.redis_client = None
        self._setup_redis()
        
        logger.info(f"MarketAnalyzer inicializado para símbolos: {self.symbols}")
    
    def _setup_redis(self):
        """Configura Redis para caching de análisis"""
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            logger.info("Conexión a Redis establecida para caching")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
    
    async def analyze_market(self) -> MarketAnalysis:
        """Realiza análisis completo del mercado"""
        try:
            start_time = time.time()
            analysis_timestamp = datetime.now()
            symbol_analyses = {}
            
            # Analizar cada símbolo
            for symbol in self.symbols:
                analysis = await self.analyze_symbol(symbol)
                symbol_analyses[symbol] = analysis
                self.symbol_analysis_history[symbol].append(analysis)
            
            # Calcular volatilidad del mercado
            volatilities = [a.volatility_24h for a in symbol_analyses.values()]
            market_volatility = np.mean(volatilities) if volatilities else 0.0
            
            # Determinar condición del mercado
            condition = self._determine_market_condition(market_volatility, symbol_analyses)
            
            # Calcular correlaciones
            correlation_matrix = await self._calculate_correlation_matrix(symbol_analyses)
            
            # Calcular momentum y liquidez
            momentum_score = np.mean([a.trend_strength for a in symbol_analyses.values()]) if symbol_analyses else 0.0
            liquidity_score = np.mean([a.volume_ratio for a in symbol_analyses.values()]) if symbol_analyses else 0.0
            
            # Calcular riesgo
            risk_score = self._calculate_risk_score(symbol_analyses, market_volatility)
            
            # Generar alertas y recomendaciones
            alerts = self._generate_alerts(market_volatility, symbol_analyses)
            recommendations = self._generate_recommendations(condition, symbol_analyses)
            
            analysis = MarketAnalysis(
                timestamp=analysis_timestamp,
                condition=condition,
                volatility=market_volatility,
                trend_direction=self._determine_trend_direction(symbol_analyses),
                volume_ratio=liquidity_score,
                correlation_matrix=correlation_matrix,
                liquidity_score=liquidity_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                alerts=alerts,
                recommendations=recommendations
            )
            
            # Cachear análisis en Redis
            if self.redis_client:
                cache_key = f"market_analysis_{analysis_timestamp.isoformat()}"
                self.redis_client.setex(cache_key, 300, json.dumps(asdict(analysis)))
            
            self.analysis_history.append(analysis)
            self.total_analyses += 1
            self.avg_analysis_time = ((self.avg_analysis_time * (self.total_analyses - 1)) + (time.time() - start_time)) / self.total_analyses
            
            # Enviar alertas via Telegram
            if alerts:
                self.alert_count += len(alerts)
                for alert in alerts:
                    # await telegram_bot.send_message(f"⚠️ Alerta de Mercado: {alert}")
                    logger.info(f"⚠️ Alerta de Mercado: {alert}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de mercado: {e}")
            return MarketAnalysis(
                timestamp=datetime.now(),
                condition=MarketCondition.NORMAL,
                volatility=0.0,
                trend_direction=TrendDirection.NEUTRAL,
                volume_ratio=0.0,
                correlation_matrix={},
                liquidity_score=0.0,
                momentum_score=0.0,
                risk_score=0.0,
                alerts=[f"Error en análisis: {str(e)}"],
                recommendations=[]
            )
    
    async def analyze_symbol(self, symbol: str) -> SymbolAnalysis:
        """Analiza un símbolo específico"""
        try:
            # Verificar cache en Redis
            if self.redis_client:
                cache_key = f"symbol_analysis_{symbol}"
                cached_analysis = self.redis_client.get(cache_key)
                if cached_analysis:
                    return SymbolAnalysis(**json.loads(cached_analysis))
            
            # Obtener datos históricos
            data = await db_manager.get_recent_market_data(symbol, timeframe='1h', limit=100)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calcular métricas
            price_change_1h = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100 if len(df) >= 2 else 0.0
            price_change_4h = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) * 100 if len(df) >= 5 else 0.0
            price_change_24h = (df['close'].iloc[-1] / df['close'].iloc[-25] - 1) * 100 if len(df) >= 25 else 0.0
            volatility_24h = np.std(df['close'].pct_change().dropna()) * np.sqrt(24) if len(df) > 1 else 0.0
            volume_24h = df['volume'].iloc[-25:].sum() if len(df) >= 25 else 0.0
            volume_ratio = volume_24h / df['volume'].iloc[-50:-25].sum() if len(df) >= 50 else 1.0
            
            # Indicadores técnicos
            rsi = talib.RSI(df['close'], timeperiod=14)[-1] if len(df) >= 14 else 50.0
            macd, signal, _ = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
            macd_signal = 'BUY' if macd[-1] > signal[-1] else 'SELL' if macd[-1] < signal[-1] else 'NEUTRAL'
            bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=20)
            bollinger_position = (df['close'].iloc[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1]) if bb_upper[-1] != bb_lower[-1] else 0.5
            
            # Ichimoku Cloud
            tenkan_sen = talib.MAX(df['high'], timeperiod=9)[-1] + talib.MIN(df['low'], timeperiod=9)[-1] / 2
            kijun_sen = talib.MAX(df['high'], timeperiod=26)[-1] + talib.MIN(df['low'], timeperiod=26)[-1] / 2
            ichimoku_signal = 'BUY' if df['close'].iloc[-1] > max(tenkan_sen, kijun_sen) else 'SELL' if df['close'].iloc[-1] < min(tenkan_sen, kijun_sen) else 'NEUTRAL'
            
            # Soporte y resistencia
            support_resistance = self._calculate_support_resistance(df)
            trend_strength = self._calculate_trend_strength(df)
            
            analysis = SymbolAnalysis(
                symbol=symbol,
                price_change_1h=price_change_1h,
                price_change_4h=price_change_4h,
                price_change_24h=price_change_24h,
                volatility_24h=volatility_24h,
                volume_24h=volume_24h,
                volume_ratio=volume_ratio,
                rsi=rsi,
                macd_signal=macd_signal,
                bollinger_position=bollinger_position,
                trend_strength=trend_strength,
                support_resistance=support_resistance,
                ichimoku_signal=ichimoku_signal
            )
            
            # Cachear análisis
            if self.redis_client:
                self.redis_client.setex(cache_key, 300, json.dumps(asdict(analysis)))
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando símbolo {symbol}: {e}")
            return SymbolAnalysis(
                symbol=symbol,
                price_change_1h=0.0,
                price_change_4h=0.0,
                price_change_24h=0.0,
                volatility_24h=0.0,
                volume_24h=0.0,
                volume_ratio=1.0,
                rsi=50.0,
                macd_signal='NEUTRAL',
                bollinger_position=0.5,
                trend_strength=0.0,
                support_resistance={'support': 0.0, 'resistance': 0.0},
                ichimoku_signal='NEUTRAL'
            )
    
    def _determine_market_condition(self, volatility: float, symbol_analyses: Dict[str, SymbolAnalysis]) -> MarketCondition:
        """Determina la condición del mercado"""
        if volatility > 0.05:
            return MarketCondition.EXTREME_VOLATILITY
        elif volatility > 0.03:
            return MarketCondition.HIGH_VOLATILITY
        elif volatility < 0.01:
            return MarketCondition.LOW_VOLATILITY
        elif any(a.price_change_24h > 5.0 for a in symbol_analyses.values()):
            return MarketCondition.BREAKOUT
        elif any(a.rsi > 70 or a.rsi < 30 for a in symbol_analyses.values()):
            return MarketCondition.REVERSAL
        return MarketCondition.NORMAL
    
    def _determine_trend_direction(self, symbol_analyses: Dict[str, SymbolAnalysis]) -> TrendDirection:
        """Determina la dirección de la tendencia del mercado"""
        avg_trend = np.mean([a.trend_strength for a in symbol_analyses.values()]) if symbol_analyses else 0.0
        if avg_trend > 0.7:
            return TrendDirection.STRONG_UP
        elif avg_trend > 0.3:
            return TrendDirection.WEAK_UP
        elif avg_trend < -0.7:
            return TrendDirection.STRONG_DOWN
        elif avg_trend < -0.3:
            return TrendDirection.WEAK_DOWN
        return TrendDirection.NEUTRAL
    
    async def _calculate_correlation_matrix(self, symbol_analyses: Dict[str, SymbolAnalysis]) -> Dict[str, Dict[str, float]]:
        """Calcula la matriz de correlación entre símbolos"""
        try:
            # Obtener datos históricos para correlación
            data = {}
            for symbol in self.symbols:
                df = pd.DataFrame(
                    await db_manager.get_recent_market_data(symbol, timeframe='1h', limit=100),
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                data[symbol] = df['close'].pct_change().dropna()
            
            # Calcular matriz de correlación
            df_all = pd.DataFrame(data)
            corr_matrix = df_all.corr().to_dict()
            return corr_matrix
        except Exception as e:
            logger.error(f"Error calculando matriz de correlación: {e}")
            return {}
    
    def _calculate_risk_score(self, symbol_analyses: Dict[str, SymbolAnalysis], market_volatility: float) -> float:
        """Calcula el puntaje de riesgo del mercado"""
        try:
            risk_factors = [
                market_volatility * 100,  # Normalizar volatilidad
                sum(1 for a in symbol_analyses.values() if a.rsi > 70 or a.rsi < 30) / len(symbol_analyses),  # Sobrecompra/sobreventa
                max(abs(a.price_change_24h) for a in symbol_analyses.values()) if symbol_analyses else 0.0  # Movimientos extremos
            ]
            return np.mean(risk_factors) if risk_factors else 0.0
        except Exception as e:
            logger.error(f"Error calculando puntaje de riesgo: {e}")
            return 0.0
    
    def _generate_alerts(self, market_volatility: float, symbol_analyses: Dict[str, SymbolAnalysis]) -> List[str]:
        """Genera alertas basadas en condiciones del mercado"""
        alerts = []
        if market_volatility > 0.05:
            alerts.append("Volatilidad extrema detectada")
        for symbol, analysis in symbol_analyses.items():
            if analysis.rsi > 80:
                alerts.append(f"Sobrecompra en {symbol}: RSI = {analysis.rsi:.2f}")
            elif analysis.rsi < 20:
                alerts.append(f"Sobreventa en {symbol}: RSI = {analysis.rsi:.2f}")
            if abs(analysis.price_change_24h) > 10:
                alerts.append(f"Movimiento extremo en {symbol}: {analysis.price_change_24h:.2f}% en 24h")
        return alerts
    
    def _generate_recommendations(self, condition: MarketCondition, symbol_analyses: Dict[str, SymbolAnalysis]) -> List[str]:
        """Genera recomendaciones basadas en condiciones del mercado"""
        recommendations = []
        if condition == MarketCondition.EXTREME_VOLATILITY:
            recommendations.append("Reducir leverage y tamaño de posiciones")
        elif condition == MarketCondition.BREAKOUT:
            recommendations.append("Considerar entradas en dirección de la tendencia")
        elif condition == MarketCondition.REVERSAL:
            recommendations.append("Evaluar oportunidades de reversión")
        for symbol, analysis in symbol_analyses.items():
            if analysis.ichimoku_signal == 'BUY':
                recommendations.append(f"Posible entrada LONG en {symbol} (Ichimoku)")
            elif analysis.ichimoku_signal == 'SELL':
                recommendations.append(f"Posible entrada SHORT en {symbol} (Ichimoku)")
        return recommendations
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula niveles de soporte y resistencia"""
        try:
            highs = df['high'].rolling(window=20).max()
            lows = df['low'].rolling(window=20).min()
            return {
                'support': lows.iloc[-1] if not np.isnan(lows.iloc[-1]) else 0.0,
                'resistance': highs.iloc[-1] if not np.isnan(highs.iloc[-1]) else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculando soporte/resistencia: {e}")
            return {'support': 0.0, 'resistance': 0.0}
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calcula la fuerza de la tendencia usando ADX"""
        try:
            adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
            return adx[-1] / 100 if not np.isnan(adx[-1]) else 0.0
        except Exception as e:
            logger.error(f"Error calculando fuerza de tendencia: {e}")
            return 0.0
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen del análisis del mercado"""
        try:
            latest_analysis = self.analysis_history[-1] if self.analysis_history else await self.analyze_market()
            return {
                'status': 'success',
                'timestamp': latest_analysis.timestamp.isoformat(),
                'market_condition': latest_analysis.condition.value,
                'volatility': latest_analysis.volatility,
                'trend_direction': latest_analysis.trend_direction.value,
                'volume_ratio': latest_analysis.volume_ratio,
                'liquidity_score': latest_analysis.liquidity_score,
                'momentum_score': latest_analysis.momentum_score,
                'risk_score': latest_analysis.risk_score,
                'alerts': latest_analysis.alerts,
                'recommendations': latest_analysis.recommendations
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen del mercado: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de performance del analizador"""
        try:
            return {
                'total_analyses': self.total_analyses,
                'avg_analysis_time': self.avg_analysis_time,
                'alert_count': self.alert_count,
                'history_size': len(self.analysis_history),
                'symbol_analyses': {
                    symbol: len(analyses) 
                    for symbol, analyses in self.symbol_analysis_history.items()
                },
                'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de performance: {e}")
            return {}
    
    def export_analysis_history(self, output_file: Optional[str] = None) -> str:
        """Exporta el historial de análisis"""
        try:
            if output_file is None:
                output_file = f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_path = Path("logs/enterprise/trading/market_analysis") / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'market_analysis_history': [asdict(analysis) for analysis in self.analysis_history],
                'symbol_analysis_history': {
                    symbol: [asdict(analysis) for analysis in analyses]
                    for symbol, analyses in self.symbol_analysis_history.items()
                },
                'performance_metrics': self.get_performance_metrics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Historial de análisis exportado: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando historial de análisis: {e}")
            return None