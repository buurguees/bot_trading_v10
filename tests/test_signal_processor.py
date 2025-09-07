#!/usr/bin/env python3
"""
🧪 test_signal_processor.py - Ejemplo de uso del SignalProcessor

Este script demuestra cómo usar el procesador inteligente de señales
para mejorar la calidad de las decisiones de trading.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime
from trading.signal_processor import signal_processor, SignalQuality

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_signal_processing():
    """Test completo del procesamiento de señales"""
    
    print("🚀 Iniciando test del SignalProcessor")
    print("=" * 60)
    
    # Símbolo a probar
    symbol = "BTCUSDT"
    
    try:
        # 1. Health check
        print("\n1️⃣ Verificando salud del sistema...")
        health = await signal_processor.health_check()
        print(f"   ✅ Base de datos: {'OK' if health.get('db_ok') else 'ERROR'}")
        print(f"   ✅ Features: {'OK' if health.get('features_ok') else 'ERROR'}")
        
        # 2. Procesar señal completa
        print(f"\n2️⃣ Procesando señal para {symbol}...")
        signal_quality = await signal_processor.process_signal(symbol, timeframe="1h")
        
        # 3. Mostrar resultados detallados
        print(f"\n📊 RESULTADOS DE LA SEÑAL:")
        print(f"   🎯 Señal: {signal_quality.signal}")
        print(f"   🎯 Confianza: {signal_quality.confidence:.2%}")
        print(f"   ⭐ Score de calidad: {signal_quality.quality_score:.2%}")
        print(f"   🔗 Consistencia multi-TF: {signal_quality.consistency:.2%}")
        print(f"   ⏰ Timing score: {signal_quality.timing_score:.2%}")
        print(f"   ⚠️ Risk score: {signal_quality.risk_score:.2%}")
        
        print(f"\n🌍 CONTEXTO DE MERCADO:")
        print(f"   📈 Régimen: {signal_quality.market_regime}")
        print(f"   📊 Volatilidad: {signal_quality.volatility_level}")
        print(f"   🎯 Momentum: {signal_quality.momentum_direction}")
        print(f"   🕐 Sesión: {signal_quality.session_timing}")
        
        print(f"\n🔍 FILTROS APLICADOS:")
        print(f"   📊 Volumen confirmado: {'✅' if signal_quality.volume_confirmation else '❌'}")
        print(f"   📈 Price action alineado: {'✅' if signal_quality.price_action_alignment else '❌'}")
        print(f"   🔄 Indicadores convergentes: {'✅' if signal_quality.indicator_convergence else '❌'}")
        print(f"   🎯 Niveles respetados: {'✅' if signal_quality.support_resistance_respect else '❌'}")
        
        print(f"\n⏱️ ANÁLISIS MULTI-TIMEFRAME:")
        for tf, signal in signal_quality.timeframe_alignment.items():
            conf = signal_quality.timeframe_confidence.get(tf, 0.0)
            print(f"   {tf:>3}: {signal:>4} (confianza: {conf:.2%})")
        
        # 4. Decisión de ejecución
        print(f"\n🤔 DECISIÓN DE EJECUCIÓN:")
        should_execute, reason = await signal_processor.should_execute_signal(signal_quality)
        print(f"   {'✅ EJECUTAR' if should_execute else '❌ NO EJECUTAR'}")
        print(f"   📝 Razón: {reason}")
        
        # 5. Test de confluencias
        print(f"\n🔗 CONFLUENCIAS TÉCNICAS:")
        confluences = await signal_processor.check_confluences(symbol, signal_quality.signal)
        for name, status in confluences.items():
            print(f"   {name}: {'✅' if status else '❌'}")
        
        # 6. Métricas del procesador
        print(f"\n📈 MÉTRICAS DEL PROCESADOR:")
        summary = signal_processor.get_processing_summary()
        print(f"   Señales procesadas: {summary['processed']}")
        print(f"   Señales aprobadas: {summary['approved']}")
        print(f"   Señales rechazadas: {summary['rejected']}")
        print(f"   Score promedio: {summary['avg_score']:.2%}")
        print(f"   Consistencia promedio: {summary['avg_consistency']:.2%}")
        print(f"   Latencia promedio: {summary['latency_ms']:.1f}ms")
        
        # 7. Test de análisis multi-timeframe
        print(f"\n🔄 ANÁLISIS MULTI-TIMEFRAME DETALLADO:")
        mtf_analysis = await signal_processor.analyze_multi_timeframe(symbol)
        print(f"   Consistencia: {mtf_analysis['consistency_score']:.2%}")
        print(f"   Señal dominante: {mtf_analysis['dominant_signal']}")
        print(f"   Divergencias: {len(mtf_analysis['divergences'])}")
        
        # 8. Test de contexto de mercado
        print(f"\n🌍 CONTEXTO DE MERCADO DETALLADO:")
        context = await signal_processor.detect_market_context(symbol)
        print(f"   Régimen: {context['regime']}")
        print(f"   Volatilidad: {context['volatility_level']}")
        print(f"   Momentum: {context['momentum']}")
        print(f"   Sesión: {context['session']}")
        print(f"   Factor horario: {context['hours_factor']:.2f}")
        print(f"   Fuerza de tendencia: {context['trend_strength']:.2f}")
        
        print(f"\n✅ Test completado exitosamente!")
        
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        print(f"\n❌ Error en test: {e}")

async def test_signal_quality_comparison():
    """Compara diferentes tipos de señales"""
    
    print("\n" + "=" * 60)
    print("🔍 COMPARACIÓN DE CALIDAD DE SEÑALES")
    print("=" * 60)
    
    symbol = "BTCUSDT"
    
    # Simular diferentes condiciones
    test_cases = [
        {"name": "Señal BUY normal", "expected": "BUY"},
        {"name": "Señal SELL normal", "expected": "SELL"},
        {"name": "Señal HOLD", "expected": "HOLD"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ {case['name']}:")
        try:
            signal_quality = await signal_processor.process_signal(symbol, timeframe="1h")
            
            print(f"   Resultado: {signal_quality.signal}")
            print(f"   Calidad: {signal_quality.quality_score:.2%}")
            print(f"   Confianza: {signal_quality.confidence:.2%}")
            print(f"   Timing: {signal_quality.timing_score:.2%}")
            
            should_execute, reason = await signal_processor.should_execute_signal(signal_quality)
            print(f"   Ejecutar: {'✅' if should_execute else '❌'} - {reason}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

async def main():
    """Función principal"""
    print("🧠 SIGNAL PROCESSOR - TEST COMPLETO")
    print("=" * 60)
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test principal
    await test_signal_processing()
    
    # Test de comparación
    await test_signal_quality_comparison()
    
    print(f"\n🏁 Test finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
