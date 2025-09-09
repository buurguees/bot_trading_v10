# Ruta: core/trading/enterprise/market_analyzer.py
# market_analyzer.py - Analizador de mercado en tiempo real
# Ubicación: C:\TradingBot_v10\trading\enterprise\market_analyzer.py

"""
Analizador de mercado en tiempo real para trading enterprise.

Características principales:
- Análisis de condiciones de mercado
- Detección de volatilidad extrema
- Análisis de correlación entre activos
- Detección de tendencias y reversiones
- Análisis de volumen y liquidez
- Alertas de condiciones anómalas
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path

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
        
        # Símbolos a analizar
        self.symbols = [s['symbol'] for s in config.trading.symbols.primary]
        
        # Historial de análisis
        self.analysis_history: List[MarketAnalysis] = []
        self.symbol_analysis_history: Dict[str, List[SymbolAnalysis]] = {}
        
        # Configuración de análisis
        self.analysis_config = {
            'volatility_thresholds': {
                'extreme': 0.10,  # 10%
                'high': 0.05,     # 5%
                'low': 0.01       # 1%
            },
            'volume_thresholds': {
                'high': 2.0,      # 2x volumen promedio
                'low': 0.5        # 0.5x volumen promedio
            },
            'correlation_thresholds': {
                'high': 0.8,      # 80% correlación
                'low': 0.3        # 30% correlación
            },
            'trend_thresholds': {
                'strong': 0.7,    # 70% fuerza de tendencia
                'weak': 0.3       # 30% fuerza de tendencia
            }
        }
        
        # Cache de datos
        self.price_cache: Dict[str, List[float]] = {}
        self.volume_cache: Dict[str, List[float]] = {}
        self.correlation_cache: Dict[str, Dict[str, float]] = {}
        
        # Métricas de performance
        self.total_analyses = 0
        self.avg_analysis_time = 0.0
        self.alert_count = 0
        
        logger.info("MarketAnalyzer inicializado")
    
    async def analyze_market(self) -> MarketAnalysis:
        """
        Analiza las condiciones generales del mercado
        
        Returns:
            Análisis completo del mercado
        """
        start_time = datetime.now()
        
        try:
            self.total_analyses += 1
            
            # Obtener datos de todos los símbolos
            symbol_data = await self._get_symbol_data()
            
            # Analizar volatilidad general
            volatility = await self._analyze_volatility(symbol_data)
            
            # Analizar tendencias
            trend_direction = await self._analyze_trends(symbol_data)
            
            # Analizar volumen
            volume_ratio = await self._analyze_volume(symbol_data)
            
            # Analizar correlaciones
            correlation_matrix = await self._analyze_correlations(symbol_data)
            
            # Calcular liquidez
            liquidity_score = await self._calculate_liquidity_score(symbol_data)
            
            # Calcular momentum
            momentum_score = await self._calculate_momentum_score(symbol_data)
            
            # Calcular riesgo
            risk_score = await self._calculate_risk_score(volatility, correlation_matrix, liquidity_score)
            
            # Determinar condición del mercado
            condition = await self._determine_market_condition(
                volatility, trend_direction, volume_ratio, risk_score
            )
            
            # Generar alertas
            alerts = await self._generate_alerts(volatility, correlation_matrix, volume_ratio, risk_score)
            
            # Generar recomendaciones
            recommendations = await self._generate_recommendations(condition, risk_score, alerts)
            
            # Crear análisis
            analysis = MarketAnalysis(
                timestamp=start_time,
                condition=condition,
                volatility=volatility,
                trend_direction=trend_direction,
                volume_ratio=volume_ratio,
                correlation_matrix=correlation_matrix,
                liquidity_score=liquidity_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                alerts=alerts,
                recommendations=recommendations
            )
            
            # Agregar al historial
            self.analysis_history.append(analysis)
            self._cleanup_history()
            
            # Actualizar métricas
            analysis_time = (datetime.now() - start_time).total_seconds()
            self.avg_analysis_time = (self.avg_analysis_time * (self.total_analyses - 1) + analysis_time) / self.total_analyses
            
            if alerts:
                self.alert_count += len(alerts)
            
            logger.debug(f"Análisis de mercado completado en {analysis_time:.3f}s")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando mercado: {e}")
            # Retornar análisis por defecto en caso de error
            return MarketAnalysis(
                timestamp=start_time,
                condition=MarketCondition.NORMAL,
                volatility=0.02,
                trend_direction=TrendDirection.NEUTRAL,
                volume_ratio=1.0,
                correlation_matrix={},
                liquidity_score=0.5,
                momentum_score=0.0,
                risk_score=0.5,
                alerts=["Error en análisis de mercado"],
                recommendations=["Verificar conectividad de datos"]
            )
    
    async def analyze_symbol(self, symbol: str) -> Optional[SymbolAnalysis]:
        """
        Analiza un símbolo específico
        
        Args:
            symbol: Símbolo a analizar
            
        Returns:
            Análisis del símbolo
        """
        try:
            # Obtener datos del símbolo
            symbol_data = await self._get_symbol_data(symbol)
            if not symbol_data:
                return None
            
            # Calcular cambios de precio
            price_changes = await self._calculate_price_changes(symbol_data)
            
            # Calcular volatilidad
            volatility = await self._calculate_symbol_volatility(symbol_data)
            
            # Calcular volumen
            volume_metrics = await self._calculate_volume_metrics(symbol_data)
            
            # Calcular indicadores técnicos
            technical_indicators = await self._calculate_technical_indicators(symbol_data)
            
            # Calcular soporte y resistencia
            support_resistance = await self._calculate_support_resistance(symbol_data)
            
            # Calcular fuerza de tendencia
            trend_strength = await self._calculate_trend_strength(symbol_data)
            
            # Crear análisis
            analysis = SymbolAnalysis(
                symbol=symbol,
                price_change_1h=price_changes['1h'],
                price_change_4h=price_changes['4h'],
                price_change_24h=price_changes['24h'],
                volatility_24h=volatility,
                volume_24h=volume_metrics['volume_24h'],
                volume_ratio=volume_metrics['volume_ratio'],
                rsi=technical_indicators['rsi'],
                macd_signal=technical_indicators['macd_signal'],
                bollinger_position=technical_indicators['bollinger_position'],
                trend_strength=trend_strength,
                support_resistance=support_resistance
            )
            
            # Agregar al historial del símbolo
            if symbol not in self.symbol_analysis_history:
                self.symbol_analysis_history[symbol] = []
            self.symbol_analysis_history[symbol].append(analysis)
            
            # Limpiar historial del símbolo
            if len(self.symbol_analysis_history[symbol]) > 1000:
                self.symbol_analysis_history[symbol] = self.symbol_analysis_history[symbol][-500:]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando símbolo {symbol}: {e}")
            return None
    
    async def _get_symbol_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene datos de los símbolos"""
        try:
            if symbol:
                # Obtener datos de un símbolo específico
                # En un sistema real, esto vendría del data collector
                return await self._simulate_symbol_data(symbol)
            else:
                # Obtener datos de todos los símbolos
                data = {}
                for sym in self.symbols:
                    data[sym] = await self._simulate_symbol_data(sym)
                return data
                
        except Exception as e:
            logger.error(f"Error obteniendo datos de símbolos: {e}")
            return {}
    
    async def _simulate_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """Simula datos de un símbolo (para testing)"""
        try:
            # Generar datos simulados
            base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.0
            
            # Generar precios con tendencia y ruido
            trend = np.random.normal(0, 0.001)  # Tendencia suave
            noise = np.random.normal(0, 0.02)   # Ruido del 2%
            price_change = trend + noise
            
            current_price = base_price * (1 + price_change)
            
            # Generar datos OHLCV
            high = current_price * (1 + abs(np.random.normal(0, 0.01)))
            low = current_price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 10000)
            
            return {
                'symbol': symbol,
                'price': current_price,
                'high': high,
                'low': low,
                'volume': volume,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error simulando datos para {symbol}: {e}")
            return {}
    
    async def _analyze_volatility(self, symbol_data: Dict[str, Any]) -> float:
        """Analiza la volatilidad general del mercado"""
        try:
            volatilities = []
            
            for symbol, data in symbol_data.items():
                if 'price' in data:
                    # Calcular volatilidad basada en cambio de precio
                    price_change = abs(data.get('price_change', 0.02))
                    volatilities.append(price_change)
            
            if volatilities:
                return np.mean(volatilities)
            else:
                return 0.02  # 2% por defecto
                
        except Exception as e:
            logger.error(f"Error analizando volatilidad: {e}")
            return 0.02
    
    async def _analyze_trends(self, symbol_data: Dict[str, Any]) -> TrendDirection:
        """Analiza las tendencias del mercado"""
        try:
            trend_scores = []
            
            for symbol, data in symbol_data.items():
                if 'price_change' in data:
                    trend_scores.append(data['price_change'])
            
            if trend_scores:
                avg_trend = np.mean(trend_scores)
                trend_strength = abs(avg_trend)
                
                if trend_strength > self.analysis_config['trend_thresholds']['strong']:
                    if avg_trend > 0:
                        return TrendDirection.STRONG_UP
                    else:
                        return TrendDirection.STRONG_DOWN
                elif trend_strength > self.analysis_config['trend_thresholds']['weak']:
                    if avg_trend > 0:
                        return TrendDirection.WEAK_UP
                    else:
                        return TrendDirection.WEAK_DOWN
                else:
                    return TrendDirection.NEUTRAL
            else:
                return TrendDirection.NEUTRAL
                
        except Exception as e:
            logger.error(f"Error analizando tendencias: {e}")
            return TrendDirection.NEUTRAL
    
    async def _analyze_volume(self, symbol_data: Dict[str, Any]) -> float:
        """Analiza el volumen del mercado"""
        try:
            volume_ratios = []
            
            for symbol, data in symbol_data.items():
                if 'volume' in data:
                    # Simular ratio de volumen
                    volume_ratio = np.random.uniform(0.5, 2.0)
                    volume_ratios.append(volume_ratio)
            
            if volume_ratios:
                return np.mean(volume_ratios)
            else:
                return 1.0  # Volumen normal
                
        except Exception as e:
            logger.error(f"Error analizando volumen: {e}")
            return 1.0
    
    async def _analyze_correlations(self, symbol_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Analiza correlaciones entre símbolos"""
        try:
            correlation_matrix = {}
            
            symbols = list(symbol_data.keys())
            
            for i, symbol1 in enumerate(symbols):
                correlation_matrix[symbol1] = {}
                
                for j, symbol2 in enumerate(symbols):
                    if i == j:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        # Simular correlación
                        correlation = np.random.uniform(0.2, 0.8)
                        correlation_matrix[symbol1][symbol2] = correlation
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"Error analizando correlaciones: {e}")
            return {}
    
    async def _calculate_liquidity_score(self, symbol_data: Dict[str, Any]) -> float:
        """Calcula el score de liquidez del mercado"""
        try:
            liquidity_scores = []
            
            for symbol, data in symbol_data.items():
                if 'volume' in data:
                    # Score de liquidez basado en volumen
                    volume = data['volume']
                    liquidity_score = min(volume / 5000, 1.0)  # Normalizar
                    liquidity_scores.append(liquidity_score)
            
            if liquidity_scores:
                return np.mean(liquidity_scores)
            else:
                return 0.5  # Liquidez media
                
        except Exception as e:
            logger.error(f"Error calculando liquidez: {e}")
            return 0.5
    
    async def _calculate_momentum_score(self, symbol_data: Dict[str, Any]) -> float:
        """Calcula el score de momentum del mercado"""
        try:
            momentum_scores = []
            
            for symbol, data in symbol_data.items():
                if 'price_change' in data:
                    # Score de momentum basado en cambio de precio
                    price_change = data['price_change']
                    momentum_score = np.tanh(price_change * 10)  # Normalizar entre -1 y 1
                    momentum_scores.append(momentum_score)
            
            if momentum_scores:
                return np.mean(momentum_scores)
            else:
                return 0.0  # Momentum neutro
                
        except Exception as e:
            logger.error(f"Error calculando momentum: {e}")
            return 0.0
    
    async def _calculate_risk_score(
        self,
        volatility: float,
        correlation_matrix: Dict[str, Dict[str, float]],
        liquidity_score: float
    ) -> float:
        """Calcula el score de riesgo del mercado"""
        try:
            # Riesgo por volatilidad
            volatility_risk = min(volatility / 0.1, 1.0)  # Normalizar
            
            # Riesgo por correlación (alta correlación = mayor riesgo)
            avg_correlation = 0.0
            correlation_count = 0
            
            for symbol1, correlations in correlation_matrix.items():
                for symbol2, correlation in correlations.items():
                    if symbol1 != symbol2:
                        avg_correlation += correlation
                        correlation_count += 1
            
            if correlation_count > 0:
                avg_correlation /= correlation_count
                correlation_risk = avg_correlation
            else:
                correlation_risk = 0.5
            
            # Riesgo por liquidez (baja liquidez = mayor riesgo)
            liquidity_risk = 1.0 - liquidity_score
            
            # Score de riesgo combinado
            risk_score = (volatility_risk * 0.4 + correlation_risk * 0.3 + liquidity_risk * 0.3)
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando score de riesgo: {e}")
            return 0.5
    
    async def _determine_market_condition(
        self,
        volatility: float,
        trend_direction: TrendDirection,
        volume_ratio: float,
        risk_score: float
    ) -> MarketCondition:
        """Determina la condición general del mercado"""
        try:
            # Condición por volatilidad
            if volatility > self.analysis_config['volatility_thresholds']['extreme']:
                return MarketCondition.EXTREME_VOLATILITY
            elif volatility > self.analysis_config['volatility_thresholds']['high']:
                return MarketCondition.HIGH_VOLATILITY
            elif volatility < self.analysis_config['volatility_thresholds']['low']:
                return MarketCondition.LOW_VOLATILITY
            
            # Condición por tendencia
            if trend_direction == TrendDirection.STRONG_UP:
                return MarketCondition.TRENDING_UP
            elif trend_direction == TrendDirection.STRONG_DOWN:
                return MarketCondition.TRENDING_DOWN
            elif trend_direction == TrendDirection.NEUTRAL:
                return MarketCondition.SIDEWAYS
            
            # Condición por volumen
            if volume_ratio > self.analysis_config['volume_thresholds']['high']:
                return MarketCondition.BREAKOUT
            elif volume_ratio < self.analysis_config['volume_thresholds']['low']:
                return MarketCondition.STABLE
            
            # Condición por riesgo
            if risk_score > 0.8:
                return MarketCondition.EXTREME_VOLATILITY
            elif risk_score < 0.2:
                return MarketCondition.STABLE
            
            return MarketCondition.NORMAL
            
        except Exception as e:
            logger.error(f"Error determinando condición del mercado: {e}")
            return MarketCondition.NORMAL
    
    async def _generate_alerts(
        self,
        volatility: float,
        correlation_matrix: Dict[str, Dict[str, float]],
        volume_ratio: float,
        risk_score: float
    ) -> List[str]:
        """Genera alertas basadas en el análisis"""
        try:
            alerts = []
            
            # Alerta por volatilidad extrema
            if volatility > self.analysis_config['volatility_thresholds']['extreme']:
                alerts.append(f"Volatilidad extrema detectada: {volatility:.2%}")
            
            # Alerta por alta correlación
            high_correlations = 0
            for symbol1, correlations in correlation_matrix.items():
                for symbol2, correlation in correlations.items():
                    if symbol1 != symbol2 and correlation > self.analysis_config['correlation_thresholds']['high']:
                        high_correlations += 1
            
            if high_correlations > 3:
                alerts.append(f"Alta correlación entre activos: {high_correlations} pares")
            
            # Alerta por volumen anómalo
            if volume_ratio > self.analysis_config['volume_thresholds']['high']:
                alerts.append(f"Volumen anómalamente alto: {volume_ratio:.1f}x")
            elif volume_ratio < self.analysis_config['volume_thresholds']['low']:
                alerts.append(f"Volumen anómalamente bajo: {volume_ratio:.1f}x")
            
            # Alerta por alto riesgo
            if risk_score > 0.8:
                alerts.append(f"Alto riesgo de mercado: {risk_score:.2f}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generando alertas: {e}")
            return []
    
    async def _generate_recommendations(
        self,
        condition: MarketCondition,
        risk_score: float,
        alerts: List[str]
    ) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        try:
            recommendations = []
            
            # Recomendaciones por condición del mercado
            if condition == MarketCondition.EXTREME_VOLATILITY:
                recommendations.append("Reducir tamaño de posiciones")
                recommendations.append("Aumentar stop losses")
                recommendations.append("Evitar nuevas posiciones")
            
            elif condition == MarketCondition.HIGH_VOLATILITY:
                recommendations.append("Usar leverage conservador")
                recommendations.append("Monitorear posiciones de cerca")
            
            elif condition == MarketCondition.TRENDING_UP:
                recommendations.append("Considerar posiciones long")
                recommendations.append("Aprovechar momentum alcista")
            
            elif condition == MarketCondition.TRENDING_DOWN:
                recommendations.append("Considerar posiciones short")
                recommendations.append("Cuidado con reversiones")
            
            elif condition == MarketCondition.SIDEWAYS:
                recommendations.append("Estrategias de range trading")
                recommendations.append("Evitar breakout trades")
            
            # Recomendaciones por riesgo
            if risk_score > 0.7:
                recommendations.append("Reducir exposición total")
                recommendations.append("Aumentar diversificación")
            
            elif risk_score < 0.3:
                recommendations.append("Condiciones favorables para trading")
                recommendations.append("Considerar aumentar exposición")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return []
    
    # Métodos auxiliares para análisis de símbolos
    async def _calculate_price_changes(self, symbol_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula cambios de precio en diferentes timeframes"""
        try:
            # Simular cambios de precio
            return {
                '1h': np.random.normal(0, 0.01),   # 1% cambio promedio
                '4h': np.random.normal(0, 0.02),   # 2% cambio promedio
                '24h': np.random.normal(0, 0.05)   # 5% cambio promedio
            }
        except Exception as e:
            logger.error(f"Error calculando cambios de precio: {e}")
            return {'1h': 0.0, '4h': 0.0, '24h': 0.0}
    
    async def _calculate_symbol_volatility(self, symbol_data: Dict[str, Any]) -> float:
        """Calcula la volatilidad de un símbolo"""
        try:
            # Simular volatilidad
            return abs(np.random.normal(0, 0.02))  # 2% volatilidad promedio
        except Exception as e:
            logger.error(f"Error calculando volatilidad del símbolo: {e}")
            return 0.02
    
    async def _calculate_volume_metrics(self, symbol_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula métricas de volumen"""
        try:
            volume = symbol_data.get('volume', 1000)
            return {
                'volume_24h': volume,
                'volume_ratio': np.random.uniform(0.5, 2.0)
            }
        except Exception as e:
            logger.error(f"Error calculando métricas de volumen: {e}")
            return {'volume_24h': 1000, 'volume_ratio': 1.0}
    
    async def _calculate_technical_indicators(self, symbol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula indicadores técnicos"""
        try:
            return {
                'rsi': np.random.uniform(20, 80),
                'macd_signal': 'bullish' if np.random.random() > 0.5 else 'bearish',
                'bollinger_position': np.random.uniform(0, 1)
            }
        except Exception as e:
            logger.error(f"Error calculando indicadores técnicos: {e}")
            return {'rsi': 50, 'macd_signal': 'neutral', 'bollinger_position': 0.5}
    
    async def _calculate_support_resistance(self, symbol_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula niveles de soporte y resistencia"""
        try:
            price = symbol_data.get('price', 100)
            return {
                'support_1': price * 0.95,
                'support_2': price * 0.90,
                'resistance_1': price * 1.05,
                'resistance_2': price * 1.10
            }
        except Exception as e:
            logger.error(f"Error calculando soporte y resistencia: {e}")
            return {'support_1': 0, 'support_2': 0, 'resistance_1': 0, 'resistance_2': 0}
    
    async def _calculate_trend_strength(self, symbol_data: Dict[str, Any]) -> float:
        """Calcula la fuerza de la tendencia"""
        try:
            # Simular fuerza de tendencia
            return np.random.uniform(0, 1)
        except Exception as e:
            logger.error(f"Error calculando fuerza de tendencia: {e}")
            return 0.5
    
    def _cleanup_history(self):
        """Limpia el historial de análisis"""
        try:
            # Mantener solo los últimos 1000 análisis
            if len(self.analysis_history) > 1000:
                self.analysis_history = self.analysis_history[-500:]
        except Exception as e:
            logger.error(f"Error limpiando historial: {e}")
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del estado del mercado"""
        try:
            if not self.analysis_history:
                return {'status': 'no_data'}
            
            latest_analysis = self.analysis_history[-1]
            
            return {
                'timestamp': latest_analysis.timestamp.isoformat(),
                'condition': latest_analysis.condition.value,
                'volatility': latest_analysis.volatility,
                'trend_direction': latest_analysis.trend_direction.value,
                'volume_ratio': latest_analysis.volume_ratio,
                'liquidity_score': latest_analysis.liquidity_score,
                'momentum_score': latest_analysis.momentum_score,
                'risk_score': latest_analysis.risk_score,
                'alerts_count': len(latest_analysis.alerts),
                'recommendations_count': len(latest_analysis.recommendations)
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
                }
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
            
            # Preparar datos para exportación
            export_data = {
                'market_analysis_history': [asdict(analysis) for analysis in self.analysis_history],
                'symbol_analysis_history': {
                    symbol: [asdict(analysis) for analysis in analyses]
                    for symbol, analyses in self.symbol_analysis_history.items()
                },
                'performance_metrics': self.get_performance_metrics(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            # Guardar archivo
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Historial de análisis exportado: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exportando historial de análisis: {e}")
            return None
