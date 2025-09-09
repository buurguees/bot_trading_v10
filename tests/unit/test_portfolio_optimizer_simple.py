#!/usr/bin/env python3
"""
🧪 test_portfolio_optimizer_simple.py - Test Simple del Portfolio Optimizer

Test básico del optimizador de portfolio sin dependencias circulares.

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
from datetime import datetime
from trading.portfolio_optimizer import PortfolioState, AllocationTarget, PortfolioOptimizer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_portfolio_optimizer_simple():
    """Test simple del portfolio optimizer"""
    
    print("🧠 PORTFOLIO OPTIMIZER - TEST SIMPLE")
    print("=" * 50)
    print(f"⏰ Iniciado: {datetime.now()}")
    print()
    
    try:
        # Crear instancia del optimizador
        optimizer = PortfolioOptimizer()
        
        # 1. Test de creación de PortfolioState
        print("1️⃣ Test de PortfolioState...")
        portfolio_state = PortfolioState(
            total_balance=10000.0,
            available_balance=5000.0,
            invested_balance=5000.0,
            symbol_allocations={"BTCUSDT": 0.4, "ETHUSDT": 0.3, "ADAUSDT": 0.2, "SOLUSDT": 0.1},
            symbol_pnl={"BTCUSDT": 100.0, "ETHUSDT": -50.0, "ADAUSDT": 25.0, "SOLUSDT": 10.0},
            symbol_exposure={"BTCUSDT": 4000.0, "ETHUSDT": 3000.0, "ADAUSDT": 2000.0, "SOLUSDT": 1000.0},
            active_positions={"BTCUSDT": 1, "ETHUSDT": 1, "ADAUSDT": 1, "SOLUSDT": 0},
            position_details={},
            total_unrealized_pnl=85.0,
            total_realized_pnl=200.0,
            portfolio_return=0.0285,
            portfolio_volatility=0.15,
            sharpe_ratio=0.19,
            max_drawdown=0.05,
            correlation_matrix={},
            correlation_risk_score=0.3,
            diversification_ratio=0.8,
            concentration_risk=0.2,
            last_rebalance=datetime.now(),
            rebalance_needed=False
        )
        
        print(f"   Balance total: ${portfolio_state.total_balance:,.2f}")
        print(f"   P&L no realizado: ${portfolio_state.total_unrealized_pnl:,.2f}")
        print(f"   Retorno: {portfolio_state.portfolio_return:.2%}")
        print(f"   Volatilidad: {portfolio_state.portfolio_volatility:.2%}")
        print(f"   Sharpe: {portfolio_state.sharpe_ratio:.2f}")
        print()
        
        # 2. Test de creación de AllocationTarget
        print("2️⃣ Test de AllocationTarget...")
        target = AllocationTarget(
            symbol="BTCUSDT",
            target_allocation_pct=0.45,
            current_allocation_pct=0.40,
            max_allocation_pct=0.50,
            min_allocation_pct=0.10,
            expected_return=0.12,
            volatility=0.20,
            correlation_penalty=0.05,
            momentum_score=0.15,
            ml_confidence_avg=0.85,
            action_required="INCREASE",
            target_change_pct=0.05,
            priority_score=0.75
        )
        
        print(f"   Símbolo: {target.symbol}")
        print(f"   Asignación actual: {target.current_allocation_pct:.1%}")
        print(f"   Asignación objetivo: {target.target_allocation_pct:.1%}")
        print(f"   Cambio necesario: {target.target_change_pct:+.1%}")
        print(f"   Acción: {target.action_required}")
        print(f"   Prioridad: {target.priority_score:.3f}")
        print()
        
        # 3. Test de métricas de diversificación
        print("3️⃣ Test de métricas de diversificación...")
        test_allocations = {"BTCUSDT": 0.4, "ETHUSDT": 0.3, "ADAUSDT": 0.2, "SOLUSDT": 0.1}
        diversification = optimizer.calculate_diversification_metrics(test_allocations)
        
        print(f"   Ratio de diversificación: {diversification['diversification_ratio']:.2f}")
        print(f"   Índice de concentración: {diversification['concentration_index']:.2f}")
        print(f"   Posiciones efectivas: {diversification['effective_positions']:.1f}")
        print()
        
        # 4. Test de health check
        print("4️⃣ Test de health check...")
        health = await optimizer.health_check()
        
        print(f"   Status: {health['status']}")
        print(f"   Componentes: {health['components']}")
        if health['errors']:
            print(f"   Errores: {health['errors']}")
        print()
        
        # 5. Test de detección de riesgos de concentración
        print("5️⃣ Test de detección de riesgos...")
        risks = await optimizer.detect_concentration_risk()
        
        print(f"   Riesgo detectado: {'SÍ' if risks['risk_detected'] else 'NO'}")
        if risks['risks']:
            for risk in risks['risks']:
                print(f"   - {risk['type']}: {risk['description']}")
        print()
        
        # 6. Test de resumen de optimización
        print("6️⃣ Test de resumen...")
        summary = optimizer.get_optimization_summary()
        
        print(f"   Ejecuciones: {summary['optimization_metrics']['optimization_runs']}")
        print(f"   Símbolos: {len(summary['symbols_tracked'])}")
        print(f"   Threshold: {summary['rebalance_threshold']:.1f}%")
        print()
        
        print("✅ Test simple completado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        logger.error(f"Error en test simple: {e}")

async def main():
    """Función principal"""
    print("🚀 INICIANDO TEST SIMPLE DEL PORTFOLIO OPTIMIZER")
    print("=" * 60)
    
    await test_portfolio_optimizer_simple()
    
    print("\n🏁 Test simple completado!")
    print(f"⏰ Finalizado: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())
