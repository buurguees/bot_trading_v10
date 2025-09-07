#!/usr/bin/env python3
"""
🧪 test_portfolio_optimizer.py - Test del Portfolio Optimizer

Este script demuestra y testa el optimizador inteligente de portfolio
para gestión multi-símbolo y optimización de asignación de capital.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime
from trading.portfolio_optimizer import portfolio_optimizer, PortfolioState, AllocationTarget

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_portfolio_optimizer():
    """Test completo del portfolio optimizer"""
    
    print("🧠 PORTFOLIO OPTIMIZER - TEST COMPLETO")
    print("=" * 60)
    print(f"⏰ Iniciado: {datetime.now()}")
    print()
    
    try:
        # 1. Health Check
        print("1️⃣ Verificando salud del sistema...")
        health = await portfolio_optimizer.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Componentes: {health['components']}")
        print()
        
        # 2. Obtener estado del portfolio
        print("2️⃣ Obteniendo estado del portfolio...")
        portfolio_state = await portfolio_optimizer.get_portfolio_state()
        
        if portfolio_state:
            print(f"   Balance total: ${portfolio_state.total_balance:,.2f}")
            print(f"   Balance disponible: ${portfolio_state.available_balance:,.2f}")
            print(f"   Balance invertido: ${portfolio_state.invested_balance:,.2f}")
            print(f"   P&L no realizado: ${portfolio_state.total_unrealized_pnl:,.2f}")
            print(f"   Retorno del portfolio: {portfolio_state.portfolio_return:.2%}")
            print(f"   Volatilidad: {portfolio_state.portfolio_volatility:.2%}")
            print(f"   Ratio Sharpe: {portfolio_state.sharpe_ratio:.2f}")
            print(f"   Diversificación: {portfolio_state.diversification_ratio:.2f}")
            print()
        else:
            print("   ❌ No se pudo obtener estado del portfolio")
            print()
        
        # 3. Calcular correlaciones
        print("3️⃣ Calculando correlaciones entre símbolos...")
        correlations = await portfolio_optimizer.calculate_symbol_correlations()
        
        print("   Matriz de correlaciones:")
        for symbol1 in portfolio_optimizer.symbols:
            print(f"   {symbol1}:")
            for symbol2 in portfolio_optimizer.symbols:
                corr = correlations.get(symbol1, {}).get(symbol2, 0.0)
                print(f"     {symbol2}: {corr:.3f}")
        print()
        
        # 4. Evaluar atractivo de símbolos
        print("4️⃣ Evaluando atractivo de símbolos...")
        for symbol in portfolio_optimizer.symbols:
            attractiveness = await portfolio_optimizer.evaluate_symbol_attractiveness(symbol)
            print(f"   {symbol}:")
            print(f"     Retorno esperado: {attractiveness['expected_return']:.2%}")
            print(f"     Volatilidad: {attractiveness['volatility']:.2%}")
            print(f"     Sharpe ratio: {attractiveness['sharpe_ratio']:.2f}")
            print(f"     Momentum: {attractiveness['momentum_score']:.2%}")
            print(f"     Confianza ML: {attractiveness['ml_confidence_avg']:.2%}")
        print()
        
        # 5. Optimizar portfolio
        print("5️⃣ Optimizando asignación del portfolio...")
        targets = await portfolio_optimizer.optimize_portfolio()
        
        if targets:
            print("   Targets de asignación generados:")
            for symbol, target in targets.items():
                print(f"   {symbol}:")
                print(f"     Asignación actual: {target.current_allocation_pct:.1%}")
                print(f"     Asignación objetivo: {target.target_allocation_pct:.1%}")
                print(f"     Cambio necesario: {target.target_change_pct:+.1%}")
                print(f"     Acción: {target.action_required}")
                print(f"     Prioridad: {target.priority_score:.3f}")
            print()
        else:
            print("   ❌ No se pudieron generar targets de optimización")
            print()
        
        # 6. Verificar necesidad de rebalance
        print("6️⃣ Verificando necesidad de rebalance...")
        rebalance_needed, reasons = await portfolio_optimizer.should_rebalance()
        
        print(f"   Rebalance necesario: {'SÍ' if rebalance_needed else 'NO'}")
        if reasons:
            print("   Razones:")
            for reason in reasons:
                print(f"     - {reason}")
        print()
        
        # 7. Detectar riesgos de concentración
        print("7️⃣ Detectando riesgos de concentración...")
        concentration_risks = await portfolio_optimizer.detect_concentration_risk()
        
        print(f"   Riesgo detectado: {'SÍ' if concentration_risks['risk_detected'] else 'NO'}")
        if concentration_risks['risks']:
            print("   Riesgos encontrados:")
            for risk in concentration_risks['risks']:
                print(f"     - {risk['type']}: {risk['description']} ({risk['severity']})")
                print(f"       Recomendación: {risk['recommendation']}")
        print()
        
        # 8. Test de optimización completo
        print("8️⃣ Ejecutando test de optimización completo...")
        test_results = await portfolio_optimizer.test_portfolio_optimization(portfolio_optimizer.symbols)
        
        print(f"   Test exitoso: {'SÍ' if test_results['success'] else 'NO'}")
        print(f"   Duración: {test_results['test_duration_ms']:.1f}ms")
        print(f"   Targets generados: {test_results['optimization_results'].get('targets_generated', 0)}")
        print(f"   Matriz de correlaciones: {'OK' if test_results['correlation_analysis'].get('matrix_generated', False) else 'ERROR'}")
        print(f"   Correlación máxima: {test_results['correlation_analysis'].get('max_correlation', 0.0):.3f}")
        
        if test_results['diversification_metrics']:
            div_metrics = test_results['diversification_metrics']
            print(f"   Ratio de diversificación: {div_metrics.get('diversification_ratio', 0.0):.2f}")
            print(f"   Índice de concentración: {div_metrics.get('concentration_index', 0.0):.2f}")
            print(f"   Posiciones efectivas: {div_metrics.get('effective_positions', 0.0):.1f}")
        print()
        
        # 9. Resumen de optimización
        print("9️⃣ Resumen de optimización...")
        summary = portfolio_optimizer.get_optimization_summary()
        
        print(f"   Ejecuciones de optimización: {summary['optimization_metrics']['optimization_runs']}")
        print(f"   Latencia promedio: {summary['optimization_metrics']['avg_latency_ms']:.1f}ms")
        print(f"   Violaciones de restricciones: {summary['optimization_metrics']['constraint_violations']}")
        print(f"   Símbolos trackeados: {len(summary['symbols_tracked'])}")
        print(f"   Threshold de rebalance: {summary['rebalance_threshold']:.1f}%")
        print(f"   Correlación máxima permitida: {summary['max_correlation']:.1f}")
        print()
        
        print("✅ Test del Portfolio Optimizer completado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        logger.error(f"Error en test del portfolio optimizer: {e}")

async def test_allocation_target_creation():
    """Test de creación de AllocationTarget"""
    
    print("\n🔍 TEST DE CREACIÓN DE ALLOCATIONTARGET")
    print("=" * 50)
    
    # Crear AllocationTarget de ejemplo
    target = AllocationTarget(
        symbol="BTCUSDT",
        target_allocation_pct=0.40,
        current_allocation_pct=0.25,
        max_allocation_pct=0.50,
        min_allocation_pct=0.10,
        expected_return=0.15,
        volatility=0.25,
        correlation_penalty=0.05,
        momentum_score=0.20,
        ml_confidence_avg=0.85,
        action_required="INCREASE",
        target_change_pct=0.15,
        priority_score=0.75
    )
    
    print(f"📊 AllocationTarget creado:")
    print(f"   Símbolo: {target.symbol}")
    print(f"   Asignación actual: {target.current_allocation_pct:.1%}")
    print(f"   Asignación objetivo: {target.target_allocation_pct:.1%}")
    print(f"   Cambio necesario: {target.target_change_pct:+.1%}")
    print(f"   Acción requerida: {target.action_required}")
    print(f"   Retorno esperado: {target.expected_return:.1%}")
    print(f"   Volatilidad: {target.volatility:.1%}")
    print(f"   Momentum: {target.momentum_score:.1%}")
    print(f"   Confianza ML: {target.ml_confidence_avg:.1%}")
    print(f"   Prioridad: {target.priority_score:.3f}")
    
    print("✅ Test de AllocationTarget completado!")

async def main():
    """Función principal"""
    print("🚀 INICIANDO TESTS DEL PORTFOLIO OPTIMIZER")
    print("=" * 60)
    
    await test_portfolio_optimizer()
    await test_allocation_target_creation()
    
    print("\n🏁 Todos los tests completados!")
    print(f"⏰ Finalizado: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())
