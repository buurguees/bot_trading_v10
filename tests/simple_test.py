#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simple_test.py
==============
Prueba simple para verificar que el sistema funciona

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

async def test_imports():
    """Prueba que todos los módulos se importen correctamente"""
    print("🧪 Probando imports...")
    
    try:
        from core.metrics.trade_metrics import DetailedTradeMetric, TradeAction, ConfidenceLevel
        from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
        from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
        from core.agents.enhanced_trading_agent import EnhancedTradingAgent
        
        print("✅ Todos los imports exitosos")
        return True
        
    except ImportError as e:
        print(f"❌ Error de import: {e}")
        return False

async def test_telegram_config():
    """Prueba la configuración de Telegram"""
    print("🧪 Probando configuración de Telegram...")
    
    try:
        from core.telegram.trade_reporter import TelegramConfig, TelegramTradeReporter
        
        # Crear configuración de prueba
        config = TelegramConfig(
            bot_token="test_token",
            chat_id="test_chat",
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        # Crear reporter
        reporter = TelegramTradeReporter(config)
        
        print("✅ Configuración de Telegram exitosa")
        return True
        
    except Exception as e:
        print(f"❌ Error en configuración de Telegram: {e}")
        return False

async def test_metrics_aggregator():
    """Prueba el agregador de métricas"""
    print("🧪 Probando agregador de métricas...")
    
    try:
        from core.sync.enhanced_metrics_aggregator import EnhancedMetricsAggregator
        
        # Crear agregador
        aggregator = EnhancedMetricsAggregator(initial_capital=1000.0)
        
        print("✅ Agregador de métricas exitoso")
        return True
        
    except Exception as e:
        print(f"❌ Error en agregador de métricas: {e}")
        return False

async def main():
    """Función principal de prueba"""
    print("🚀 Iniciando prueba simple del sistema...")
    
    tests = [
        ("Imports", test_imports),
        ("Configuración Telegram", test_telegram_config),
        ("Agregador de Métricas", test_metrics_aggregator)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Ejecutando: {test_name}")
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name}: EXITOSO")
                passed += 1
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 RESUMEN:")
    print(f"✅ Pruebas exitosas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        return 0
    else:
        print("\n⚠️ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
