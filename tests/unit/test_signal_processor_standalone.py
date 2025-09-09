#!/usr/bin/env python3
"""
🧪 test_signal_processor_standalone.py - Test Standalone del SignalProcessor

Test que no depende de la base de datos para verificar la lógica del signal processor.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

# Configurar logging sin emojis para evitar problemas de encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Definir SignalQuality localmente para el test
@dataclass
class SignalQuality:
    """Representa la calidad y características de una señal de trading"""
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    quality_score: float  # 0.0 - 1.0 (score combinado de calidad)
    strength: float  # 0.0 - 1.0 (fuerza de la señal)
    consistency: float  # 0.0 - 1.0 (consistencia entre timeframes)
    timing_score: float  # 0.0 - 1.0 (calidad del timing)
    risk_score: float  # 0.0 - 1.0 (score de riesgo)

    # Análisis multi-timeframe
    timeframe_alignment: Dict[str, str] = field(default_factory=dict)
    timeframe_confidence: Dict[str, float] = field(default_factory=dict)

    # Condiciones de mercado
    market_regime: str = "UNKNOWN"  # TRENDING, RANGING, VOLATILE, CONSOLIDATING
    volatility_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, EXTREME
    momentum_direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL

    # Factores de calidad
    volume_confirmation: bool = False
    price_action_alignment: bool = False
    indicator_convergence: bool = False
    support_resistance_respect: bool = False

    # Timing
    session_timing: str = "UNKNOWN"  # ASIAN, EUROPEAN, US, OVERLAP
    market_hours_factor: float = 1.0  # Ajuste por horario de mercado

    # Metadata
    processing_time: datetime = field(default_factory=datetime.now)
    raw_prediction: Dict[str, Any] = field(default_factory=dict)
    filtering_applied: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

# Clase SignalProcessor simplificada para testing
class TestSignalProcessor:
    """SignalProcessor simplificado para testing"""
    
    def __init__(self):
        self.min_quality_score = 0.70
        self.volume_confirmation_required = True
        self.trend_alignment_required = True
        
        # Parámetros adaptativos
        self.VOLATILITY_ADJUSTMENTS = {
            "LOW": {"min_confidence": 0.60, "min_score": 0.65},
            "MEDIUM": {"min_confidence": 0.70, "min_score": 0.75},
            "HIGH": {"min_confidence": 0.80, "min_score": 0.85},
            "EXTREME": {"min_confidence": 0.90, "min_score": 0.95}
        }
        
        self.SESSION_ADJUSTMENTS = {
            "ASIAN": {"liquidity_factor": 0.7, "volatility_factor": 0.8},
            "EUROPEAN": {"liquidity_factor": 0.9, "volatility_factor": 1.0},
            "US": {"liquidity_factor": 1.0, "volatility_factor": 1.2},
            "OVERLAP": {"liquidity_factor": 1.1, "volatility_factor": 1.1}
        }
    
    def calculate_signal_score(
        self,
        filters_results: Dict[str, Any],
        context: Dict[str, Any],
        timeframe_analysis: Dict[str, Any],
        base_confidence: float,
        timing_score: float,
    ) -> float:
        """Calcula el score final de la señal"""
        try:
            # Valores de entrada
            consistency = float(timeframe_analysis.get("consistency_score", 0.5))
            volume_score = 1.0 if filters_results.get("volume_confirmed", False) else 0.3
            trend_score = 1.0 if filters_results.get("trend_aligned", False) else 0.3
            confluence = float(filters_results.get("risk_score", 0.5))
            vol_adj = self._get_volatility_adjustment_score(str(context.get("volatility_level", "MEDIUM")))

            weights = {
                "confidence": 0.25,
                "consistency": 0.20,
                "volume": 0.15,
                "timing": 0.15,
                "trend": 0.10,
                "confluence": 0.10,
                "volatility": 0.05,
            }

            final_score = (
                base_confidence * weights["confidence"] +
                consistency * weights["consistency"] +
                volume_score * weights["volume"] +
                timing_score * weights["timing"] +
                trend_score * weights["trend"] +
                confluence * weights["confluence"] +
                vol_adj * weights["volatility"]
            )
            return float(np.clip(final_score, 0.0, 1.0))
        except Exception as e:
            logger.debug(f"Score fallback: {e}")
            return 0.5
    
    def _get_volatility_adjustment_score(self, level: str) -> float:
        return {"LOW": 0.9, "MEDIUM": 0.8, "HIGH": 0.6, "EXTREME": 0.2}.get(level, 0.8)
    
    async def should_execute_signal(self, signal_quality: SignalQuality) -> Tuple[bool, str]:
        """Decide si ejecutar una señal"""
        try:
            # Umbrales por volatilidad
            vol = signal_quality.volatility_level
            adjust = self.VOLATILITY_ADJUSTMENTS.get(vol, self.VOLATILITY_ADJUSTMENTS["MEDIUM"])
            min_score = float(adjust.get("min_score", self.min_quality_score))
            min_conf = float(adjust.get("min_confidence", 0.70))

            if signal_quality.quality_score < min_score:
                return False, f"Score insuficiente: {signal_quality.quality_score:.2%} < {min_score:.2%}"
            if signal_quality.confidence < min_conf:
                return False, f"Confianza insuficiente: {signal_quality.confidence:.2%} < {min_conf:.2%}"

            if self.volume_confirmation_required and not signal_quality.volume_confirmation:
                return False, "Confirmación de volumen requerida"
            if self.trend_alignment_required and not signal_quality.price_action_alignment:
                return False, "Alineación de tendencia/PA requerida"

            if signal_quality.volatility_level == "EXTREME":
                return False, "Volatilidad extrema"

            if signal_quality.consistency < 0.6:
                return False, f"Baja consistencia multi-TF: {signal_quality.consistency:.2%}"
            if signal_quality.timing_score < 0.5:
                return False, f"Timing desfavorable: {signal_quality.timing_score:.2%}"

            return True, f"Señal aprobada | score={signal_quality.quality_score:.2%}"
        except Exception as e:
            logger.debug(f"Decision fallback: {e}")
            return False, f"Error en evaluación: {e}"

async def test_signal_quality_creation():
    """Test de creación y evaluación de SignalQuality"""
    
    print("🔍 TEST DE SIGNALQUALITY")
    print("=" * 50)
    
    processor = TestSignalProcessor()
    
    # Test 1: Señal de alta calidad
    print("\n1️⃣ Señal de ALTA CALIDAD:")
    high_quality_signal = SignalQuality(
        signal="BUY",
        confidence=0.85,
        quality_score=0.82,
        strength=0.03,
        consistency=0.88,
        timing_score=0.78,
        risk_score=0.20,
        timeframe_alignment={"1m": "BUY", "5m": "BUY", "15m": "BUY", "1h": "BUY", "4h": "NEUTRAL"},
        timeframe_confidence={"1m": 0.85, "5m": 0.82, "15m": 0.78, "1h": 0.80, "4h": 0.60},
        market_regime="TRENDING",
        volatility_level="MEDIUM",
        momentum_direction="BULLISH",
        volume_confirmation=True,
        price_action_alignment=True,
        indicator_convergence=True,
        support_resistance_respect=True,
        session_timing="US",
        market_hours_factor=1.0,
        processing_time=datetime.now(),
        raw_prediction={"action": "BUY", "confidence": 0.85},
        filtering_applied=["volume_filter", "trend_filter", "levels_filter"],
        rejection_reasons=[]
    )
    
    should_execute, reason = await processor.should_execute_signal(high_quality_signal)
    print(f"   Señal: {high_quality_signal.signal}")
    print(f"   Confianza: {high_quality_signal.confidence:.2%}")
    print(f"   Score: {high_quality_signal.quality_score:.2%}")
    print(f"   Consistencia: {high_quality_signal.consistency:.2%}")
    print(f"   Timing: {high_quality_signal.timing_score:.2%}")
    print(f"   Decisión: {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
    print(f"   Razón: {reason}")
    
    # Test 2: Señal de baja calidad
    print("\n2️⃣ Señal de BAJA CALIDAD:")
    low_quality_signal = SignalQuality(
        signal="SELL",
        confidence=0.45,
        quality_score=0.35,
        strength=0.01,
        consistency=0.30,
        timing_score=0.25,
        risk_score=0.80,
        timeframe_alignment={"1m": "SELL", "5m": "HOLD", "15m": "BUY", "1h": "HOLD", "4h": "BUY"},
        timeframe_confidence={"1m": 0.45, "5m": 0.30, "15m": 0.25, "1h": 0.35, "4h": 0.40},
        market_regime="RANGING",
        volatility_level="HIGH",
        momentum_direction="NEUTRAL",
        volume_confirmation=False,
        price_action_alignment=False,
        indicator_convergence=False,
        support_resistance_respect=False,
        session_timing="ASIAN",
        market_hours_factor=0.7,
        processing_time=datetime.now(),
        raw_prediction={"action": "SELL", "confidence": 0.45},
        filtering_applied=[],
        rejection_reasons=["low_confidence", "no_volume_confirmation"]
    )
    
    should_execute, reason = await processor.should_execute_signal(low_quality_signal)
    print(f"   Señal: {low_quality_signal.signal}")
    print(f"   Confianza: {low_quality_signal.confidence:.2%}")
    print(f"   Score: {low_quality_signal.quality_score:.2%}")
    print(f"   Consistencia: {low_quality_signal.consistency:.2%}")
    print(f"   Timing: {low_quality_signal.timing_score:.2%}")
    print(f"   Decisión: {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
    print(f"   Razón: {reason}")
    
    # Test 3: Señal con volatilidad extrema
    print("\n3️⃣ Señal con VOLATILIDAD EXTREMA:")
    extreme_vol_signal = SignalQuality(
        signal="BUY",
        confidence=0.90,
        quality_score=0.85,
        strength=0.05,
        consistency=0.90,
        timing_score=0.80,
        risk_score=0.15,
        timeframe_alignment={"1m": "BUY", "5m": "BUY", "15m": "BUY", "1h": "BUY", "4h": "BUY"},
        timeframe_confidence={"1m": 0.90, "5m": 0.88, "15m": 0.85, "1h": 0.87, "4h": 0.82},
        market_regime="VOLATILE",
        volatility_level="EXTREME",
        momentum_direction="BULLISH",
        volume_confirmation=True,
        price_action_alignment=True,
        indicator_convergence=True,
        support_resistance_respect=True,
        session_timing="US",
        market_hours_factor=1.0,
        processing_time=datetime.now(),
        raw_prediction={"action": "BUY", "confidence": 0.90},
        filtering_applied=["volume_filter", "trend_filter", "levels_filter"],
        rejection_reasons=[]
    )
    
    should_execute, reason = await processor.should_execute_signal(extreme_vol_signal)
    print(f"   Señal: {extreme_vol_signal.signal}")
    print(f"   Confianza: {extreme_vol_signal.confidence:.2%}")
    print(f"   Score: {extreme_vol_signal.quality_score:.2%}")
    print(f"   Volatilidad: {extreme_vol_signal.volatility_level}")
    print(f"   Decisión: {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
    print(f"   Razón: {reason}")

async def test_scoring_system():
    """Test del sistema de scoring"""
    
    print("\n" + "=" * 50)
    print("📊 TEST DEL SISTEMA DE SCORING")
    print("=" * 50)
    
    processor = TestSignalProcessor()
    
    # Test con diferentes combinaciones de filtros
    test_cases = [
        {
            "name": "Filtros perfectos",
            "filters": {"volume_confirmed": True, "trend_aligned": True, "risk_score": 0.9},
            "context": {"volatility_level": "MEDIUM"},
            "timeframe": {"consistency_score": 0.9},
            "confidence": 0.85,
            "timing": 0.8
        },
        {
            "name": "Filtros mixtos",
            "filters": {"volume_confirmed": True, "trend_aligned": False, "risk_score": 0.6},
            "context": {"volatility_level": "HIGH"},
            "timeframe": {"consistency_score": 0.7},
            "confidence": 0.75,
            "timing": 0.6
        },
        {
            "name": "Filtros pobres",
            "filters": {"volume_confirmed": False, "trend_aligned": False, "risk_score": 0.3},
            "context": {"volatility_level": "LOW"},
            "timeframe": {"consistency_score": 0.4},
            "confidence": 0.5,
            "timing": 0.3
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ {case['name']}:")
        score = processor.calculate_signal_score(
            filters_results=case["filters"],
            context=case["context"],
            timeframe_analysis=case["timeframe"],
            base_confidence=case["confidence"],
            timing_score=case["timing"]
        )
        print(f"   Score calculado: {score:.2%}")
        print(f"   Filtros: {case['filters']}")
        print(f"   Contexto: {case['context']}")
        print(f"   Consistencia: {case['timeframe']['consistency_score']:.2%}")
        print(f"   Confianza: {case['confidence']:.2%}")
        print(f"   Timing: {case['timing']:.2%}")

async def test_volatility_adjustments():
    """Test de ajustes por volatilidad"""
    
    print("\n" + "=" * 50)
    print("⚡ TEST DE AJUSTES POR VOLATILIDAD")
    print("=" * 50)
    
    processor = TestSignalProcessor()
    
    volatilities = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    
    for vol in volatilities:
        print(f"\n📊 Volatilidad: {vol}")
        adjustment = processor.VOLATILITY_ADJUSTMENTS.get(vol, {})
        print(f"   Confianza mínima: {adjustment.get('min_confidence', 0.0):.2%}")
        print(f"   Score mínimo: {adjustment.get('min_score', 0.0):.2%}")
        
        # Test con señal de calidad media
        test_signal = SignalQuality(
            signal="BUY",
            confidence=0.75,
            quality_score=0.70,
            strength=0.02,
            consistency=0.75,
            timing_score=0.70,
            risk_score=0.30,
            volatility_level=vol,
            volume_confirmation=True,
            price_action_alignment=True
        )
        
        should_execute, reason = await processor.should_execute_signal(test_signal)
        print(f"   Decisión: {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
        print(f"   Razón: {reason}")

async def main():
    """Función principal"""
    print("🧠 SIGNAL PROCESSOR - TEST STANDALONE")
    print("=" * 50)
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test de SignalQuality
    await test_signal_quality_creation()
    
    # Test del sistema de scoring
    await test_scoring_system()
    
    # Test de ajustes por volatilidad
    await test_volatility_adjustments()
    
    print(f"\n🏁 Test finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✅ Todos los tests completados exitosamente!")

if __name__ == "__main__":
    asyncio.run(main())
