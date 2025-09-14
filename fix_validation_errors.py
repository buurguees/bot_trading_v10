#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_validation_errors.py
========================
Script de Corrección de Errores de Validación

Corrige los errores encontrados en el sistema de validación.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import os
import sys
from pathlib import Path

def fix_requirements():
    """Corrige el archivo requirements-enhanced.txt"""
    print("🔧 Corrigiendo requirements-enhanced.txt...")
    
    requirements_file = Path("requirements-enhanced.txt")
    if requirements_file.exists():
        content = requirements_file.read_text(encoding='utf-8')
        
        # Remover sqlite3 que está incluido en Python
        content = content.replace("sqlite3  # Built-in with Python\n", "")
        
        requirements_file.write_text(content, encoding='utf-8')
        print("✅ requirements-enhanced.txt corregido")
    else:
        print("❌ Archivo requirements-enhanced.txt no encontrado")

def fix_telegram_tests():
    """Corrige los scripts de prueba de Telegram"""
    print("🔧 Corrigiendo scripts de prueba de Telegram...")
    
    # Corregir setup_telegram_for_tests.py
    setup_file = Path("scripts/setup/setup_telegram_for_tests.py")
    if setup_file.exists():
        content = setup_file.read_text(encoding='utf-8')
        
        # Corregir método de envío de trade individual
        content = content.replace(
            "success = await reporter.send_individual_trade_report(trade_metric)",
            "success = await reporter.send_individual_trade_alert(trade_metric)"
        )
        
        # Corregir creación de PortfolioMetrics
        old_portfolio = """portfolio_metrics = PortfolioMetrics(
            cycle_id=1,
            total_trades=5,
            winning_trades=3,
            total_pnl_usdt=150.0,
            total_volume_usdt=5000.0,
            win_rate=0.6,
            avg_pnl_per_trade=30.0,
            max_drawdown=0.05,
            sharpe_ratio=1.2,
            profit_factor=1.5,
            avg_trade_duration_hours=2.0,
            best_trade_pnl=100.0,
            worst_trade_pnl=-20.0,
            consecutive_wins=2,
            consecutive_losses=1,
            trades_by_symbol={'BTCUSDT': 3, 'ETHUSDT': 2},
            pnl_by_symbol={'BTCUSDT': 100.0, 'ETHUSDT': 50.0},
            strategy_performance={'strategy_1': {'trades': 3, 'pnl': 100.0}},
            risk_metrics={'var_95': 50.0, 'max_drawdown': 0.05},
            quality_metrics={'avg_quality': 75.0, 'high_quality_ratio': 0.6}
        )"""
        
        new_portfolio = """portfolio_metrics = PortfolioMetrics(
            cycle_id=1,
            timestamp=datetime.now(),
            total_pnl_usdt=150.0,
            portfolio_return_pct=15.0,
            sharpe_ratio=1.2,
            max_drawdown_pct=5.0,
            win_rate=0.6,
            correlation_avg=0.3,
            diversification_score=0.8,
            var_95=50.0,
            concentration_risk=0.2,
            total_trades=5,
            avg_trade_duration=2.0
        )"""
        
        content = content.replace(old_portfolio, new_portfolio)
        
        setup_file.write_text(content, encoding='utf-8')
        print("✅ setup_telegram_for_tests.py corregido")
    else:
        print("❌ Archivo setup_telegram_for_tests.py no encontrado")

def fix_quick_validation():
    """Corrige el script de validación rápida"""
    print("🔧 Corrigiendo script de validación rápida...")
    
    # El error de Optional ya se corrigió, pero vamos a verificar
    quick_file = Path("scripts/testing/quick_validation_test.py")
    if quick_file.exists():
        content = quick_file.read_text(encoding='utf-8')
        
        if "from typing import Dict, List, Any, Optional" in content:
            print("✅ quick_validation_test.py ya tiene Optional importado")
        else:
            print("❌ Error: Optional no está importado en quick_validation_test.py")
    else:
        print("❌ Archivo quick_validation_test.py no encontrado")

def create_simple_test():
    """Crea un script de prueba simple para verificar que todo funciona"""
    print("🔧 Creando script de prueba simple...")
    
    simple_test_content = '''#!/usr/bin/env python3
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
        print(f"\\n🔍 Ejecutando: {test_name}")
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name}: EXITOSO")
                passed += 1
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\\n📊 RESUMEN:")
    print(f"✅ Pruebas exitosas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")
    
    if passed == total:
        print("\\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        return 0
    else:
        print("\\n⚠️ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''
    
    with open("simple_test.py", "w", encoding="utf-8") as f:
        f.write(simple_test_content)
    
    print("✅ simple_test.py creado")

def main():
    """Función principal de corrección"""
    print("🔧 Iniciando corrección de errores de validación...")
    
    # Corregir archivos
    fix_requirements()
    fix_telegram_tests()
    fix_quick_validation()
    create_simple_test()
    
    print("\\n✅ Corrección de errores completada")
    print("\\n💡 Próximos pasos:")
    print("1. Ejecutar: python simple_test.py")
    print("2. Si funciona, ejecutar: python run_complete_validation.py --quick")
    print("3. Si hay errores, revisar logs en logs/")

if __name__ == "__main__":
    main()
