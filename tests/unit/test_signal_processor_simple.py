#!/usr/bin/env python3
"""
🧪 test_signal_processor_simple.py - Test Simple del SignalProcessor

Test básico que no requiere datos reales de mercado.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime
from trading.signal_processor import signal_processor, SignalQuality

# Configurar logging sin emojis para evitar problemas de encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_signal_processor_basic():
    """Test básico del signal processor"""
    
    print("🚀 Test Básico del SignalProcessor")
    print("=" * 50)
    
    symbol = "BTCUSDT"
    
    try:
        # 1. Health check
        print("\n1️⃣ Verificando salud del sistema...")
        health = await signal_processor.health_check()
        print(f"   Base de datos: {'OK' if health.get('db_ok') else 'ERROR'}")
        print(f"   Features: {'OK' if health.get('features_ok') else 'ERROR'}")
        
        # 2. Test de procesamiento (puede fallar sin datos)
        print(f"\n2️⃣ Procesando señal para {symbol}...")
        try:
            signal_quality = await signal_processor.process_signal(symbol, timeframe="1h")
            
            print(f"\n📊 RESULTADOS DE LA SEÑAL:")
            print(f"   Señal: {signal_quality.signal}")
            print(f"   Confianza: {signal_quality.confidence:.2%}")
            print(f"   Score de calidad: {signal_quality.quality_score:.2%}")
            print(f"   Consistencia multi-TF: {signal_quality.consistency:.2%}")
            print(f"   Timing score: {signal_quality.timing_score:.2%}")
            print(f"   Risk score: {signal_quality.risk_score:.2%}")
            
            print(f"\n🌍 CONTEXTO DE MERCADO:")
            print(f"   Régimen: {signal_quality.market_regime}")
            print(f"   Volatilidad: {signal_quality.volatility_level}")
            print(f"   Momentum: {signal_quality.momentum_direction}")
            print(f"   Sesión: {signal_quality.session_timing}")
            
            print(f"\n🔍 FILTROS APLICADOS:")
            print(f"   Volumen confirmado: {'SI' if signal_quality.volume_confirmation else 'NO'}")
            print(f"   Price action alineado: {'SI' if signal_quality.price_action_alignment else 'NO'}")
            print(f"   Indicadores convergentes: {'SI' if signal_quality.indicator_convergence else 'NO'}")
            print(f"   Niveles respetados: {'SI' if signal_quality.support_resistance_respect else 'NO'}")
            
            # 3. Decisión de ejecución
            print(f"\n🤔 DECISIÓN DE EJECUCIÓN:")
            should_execute, reason = await signal_processor.should_execute_signal(signal_quality)
            print(f"   {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
            print(f"   Razón: {reason}")
            
        except Exception as e:
            print(f"   ⚠️ Error procesando señal: {e}")
            print("   (Esto es normal si no hay datos de mercado)")
        
        # 4. Test de confluencias
        print(f"\n🔗 CONFLUENCIAS TÉCNICAS:")
        try:
            confluences = await signal_processor.check_confluences(symbol, "BUY")
            for name, status in confluences.items():
                print(f"   {name}: {'SI' if status else 'NO'}")
        except Exception as e:
            print(f"   ⚠️ Error en confluencias: {e}")
        
        # 5. Métricas del procesador
        print(f"\n📈 MÉTRICAS DEL PROCESADOR:")
        summary = signal_processor.get_processing_summary()
        print(f"   Señales procesadas: {summary['processed']}")
        print(f"   Señales aprobadas: {summary['approved']}")
        print(f"   Señales rechazadas: {summary['rejected']}")
        print(f"   Score promedio: {summary['avg_score']:.2%}")
        print(f"   Consistencia promedio: {summary['avg_consistency']:.2%}")
        print(f"   Latencia promedio: {summary['latency_ms']:.1f}ms")
        
        print(f"\n✅ Test básico completado!")
        
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        print(f"\n❌ Error en test: {e}")

async def test_signal_quality_creation():
    """Test de creación de SignalQuality"""
    
    print("\n" + "=" * 50)
    print("🔍 TEST DE CREACIÓN DE SIGNALQUALITY")
    print("=" * 50)
    
    # Crear SignalQuality manualmente
    signal_quality = SignalQuality(
        signal="BUY",
        confidence=0.85,
        quality_score=0.78,
        strength=0.03,
        consistency=0.82,
        timing_score=0.75,
        risk_score=0.25,
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
    
    print(f"📊 SignalQuality creado:")
    print(f"   Señal: {signal_quality.signal}")
    print(f"   Confianza: {signal_quality.confidence:.2%}")
    print(f"   Score de calidad: {signal_quality.quality_score:.2%}")
    print(f"   Consistencia: {signal_quality.consistency:.2%}")
    print(f"   Timing: {signal_quality.timing_score:.2%}")
    print(f"   Risk: {signal_quality.risk_score:.2%}")
    print(f"   Régimen: {signal_quality.market_regime}")
    print(f"   Volatilidad: {signal_quality.volatility_level}")
    print(f"   Momentum: {signal_quality.momentum_direction}")
    print(f"   Sesión: {signal_quality.session_timing}")
    
    # Test de decisión
    should_execute, reason = await signal_processor.should_execute_signal(signal_quality)
    print(f"\n🤔 Decisión: {'EJECUTAR' if should_execute else 'NO EJECUTAR'}")
    print(f"   Razón: {reason}")
    
    print(f"\n✅ Test de SignalQuality completado!")

async def main():
    """Función principal"""
    print("🧠 SIGNAL PROCESSOR - TEST SIMPLE")
    print("=" * 50)
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test básico
    await test_signal_processor_basic()
    
    # Test de SignalQuality
    await test_signal_quality_creation()
    
    print(f"\n🏁 Test finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
