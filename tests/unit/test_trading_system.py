"""
🧪 test_trading_system.py - Tests del Sistema de Trading

Tests mínimos para validar:
- Risk sizing
- Anti-duplicados
- Paper fills
- Circuit breakers

Autor: Alex B
Fecha: 2025-01-07
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del proyecto
from config.config_loader import user_config
from trading.risk_manager import risk_manager
from trading.execution_engine import execution_engine
from trading.order_manager import order_manager
from trading.bitget_client import bitget_client

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSystemTester:
    """Tester para el sistema de trading"""
    
    def __init__(self):
        self.test_results = {}
    
    async def run_all_tests(self) -> Dict:
        """Ejecuta todos los tests del sistema de trading"""
        logger.info("🧪 Iniciando tests del sistema de trading...")
        
        try:
            # Test 1: Risk sizing
            await self.test_risk_sizing()
            
            # Test 2: Anti-duplicados
            await self.test_anti_duplicates()
            
            # Test 3: Paper fills
            await self.test_paper_fills()
            
            # Test 4: Circuit breakers
            await self.test_circuit_breakers()
            
            # Test 5: Bitget client
            await self.test_bitget_client()
            
            # Mostrar resultados
            self.print_test_results()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Error en tests: {e}")
            return {'error': str(e)}
    
    async def test_risk_sizing(self) -> bool:
        """Test de sizing de riesgo"""
        logger.info("💰 Test 1: Risk sizing...")
        
        try:
            # Test con diferentes escenarios
            test_cases = [
                {
                    'current_price': 50000.0,
                    'atr': 1000.0,
                    'balance': 10000.0,
                    'stop_loss_pct': 0.02,
                    'confidence': 0.8
                },
                {
                    'current_price': 50000.0,
                    'atr': 1000.0,
                    'balance': 1000.0,  # Balance bajo
                    'stop_loss_pct': 0.02,
                    'confidence': 0.8
                },
                {
                    'current_price': 50000.0,
                    'atr': 1000.0,
                    'balance': 10000.0,
                    'stop_loss_pct': 0.01,  # SL más estricto
                    'confidence': 0.6
                }
            ]
            
            for i, case in enumerate(test_cases):
                decision = risk_manager.calculate_position_size(
                    current_price=case['current_price'],
                    atr=case['atr'],
                    balance=case['balance'],
                    stop_loss_pct=case['stop_loss_pct'],
                    confidence=case['confidence']
                )
                
                # Verificar que la decisión es válida
                assert decision is not None, f"Decisión nula en caso {i+1}"
                assert decision.size_qty > 0, f"Tamaño de posición inválido en caso {i+1}"
                assert decision.stop_loss > 0, f"Stop loss inválido en caso {i+1}"
                assert decision.take_profit > 0, f"Take profit inválido en caso {i+1}"
                
                # Verificar que el tamaño es razonable
                position_value = decision.size_qty * case['current_price']
                max_position_value = case['balance'] * 0.1  # Máximo 10% del balance
                assert position_value <= max_position_value, f"Posición demasiado grande en caso {i+1}"
            
            self.test_results['risk_sizing'] = True
            logger.info("✅ Test de risk sizing: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de risk sizing: FAILED - {e}")
            self.test_results['risk_sizing'] = False
            return False
    
    async def test_anti_duplicates(self) -> bool:
        """Test de anti-duplicados"""
        logger.info("🚫 Test 2: Anti-duplicados...")
        
        try:
            symbol = "BTCUSDT"
            signal = "BUY"
            current_price = 50000.0
            atr = 1000.0
            balance = 10000.0
            timestamp = datetime.now()
            
            # Test 1: Primera señal debe pasar
            result1 = await execution_engine.route_signal(
                symbol=symbol,
                signal=signal,
                confidence=0.8,
                current_price=current_price,
                atr=atr,
                balance=balance,
                bar_timestamp=timestamp
            )
            
            # Test 2: Segunda señal del mismo lado debe ser rechazada
            result2 = await execution_engine.route_signal(
                symbol=symbol,
                signal=signal,  # Mismo lado
                confidence=0.8,
                current_price=current_price,
                atr=atr,
                balance=balance,
                bar_timestamp=timestamp  # Misma barra
            )
            
            # Test 3: Señal del lado opuesto debe pasar
            result3 = await execution_engine.route_signal(
                symbol=symbol,
                signal="SELL",  # Lado opuesto
                confidence=0.8,
                current_price=current_price,
                atr=atr,
                balance=balance,
                bar_timestamp=timestamp  # Misma barra
            )
            
            # Verificar resultados
            assert result1 is not None, "Primera señal debería pasar"
            assert result2 is None, "Segunda señal del mismo lado debería ser rechazada"
            assert result3 is not None, "Señal del lado opuesto debería pasar"
            
            self.test_results['anti_duplicates'] = True
            logger.info("✅ Test de anti-duplicados: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de anti-duplicados: FAILED - {e}")
            self.test_results['anti_duplicates'] = False
            return False
    
    async def test_paper_fills(self) -> bool:
        """Test de fills en modo paper"""
        logger.info("📄 Test 3: Paper fills...")
        
        try:
            # Verificar que estamos en modo paper
            assert order_manager.trading_mode == 'paper_trading', "Debe estar en modo paper"
            
            # Crear una decisión de riesgo
            risk_decision = risk_manager.calculate_position_size(
                current_price=50000.0,
                atr=1000.0,
                balance=10000.0,
                stop_loss_pct=0.02,
                confidence=0.8
            )
            
            # Ejecutar orden en modo paper
            trade_record = await order_manager.execute_order(
                symbol="BTCUSDT",
                signal="BUY",
                risk_decision=risk_decision,
                current_price=50000.0,
                confidence=0.8
            )
            
            # Verificar que la orden se ejecutó
            assert trade_record is not None, "Orden debería ejecutarse en modo paper"
            assert trade_record.status == "FILLED", "Orden debería estar filled"
            assert trade_record.fees > 0, "Debería tener comisiones"
            
            # Verificar que el balance se actualizó
            new_balance = order_manager.get_balance()
            assert new_balance < 10000.0, "Balance debería disminuir después de compra"
            
            # Test de cierre de posición
            closed_trade = await order_manager.close_trade(
                trade_id=trade_record.trade_id,
                exit_price=51000.0,  # Precio más alto
                exit_reason="MANUAL"
            )
            
            assert closed_trade is not None, "Trade debería cerrarse"
            assert closed_trade.pnl > 0, "Debería tener PnL positivo"
            
            self.test_results['paper_fills'] = True
            logger.info("✅ Test de paper fills: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de paper fills: FAILED - {e}")
            self.test_results['paper_fills'] = False
            return False
    
    async def test_circuit_breakers(self) -> bool:
        """Test de circuit breakers"""
        logger.info("⚡ Test 4: Circuit breakers...")
        
        try:
            # Simular pérdidas consecutivas
            for i in range(5):  # Más del límite de 3
                await execution_engine.update_daily_loss(-100.0)  # Pérdida de $100
            
            # Verificar que el circuit breaker se activa
            balance = 10000.0
            circuit_breaker_active = not await execution_engine._check_circuit_breakers(balance)
            
            assert circuit_breaker_active, "Circuit breaker debería activarse con pérdidas consecutivas"
            
            # Resetear contadores
            execution_engine.reset_daily_counters()
            
            # Verificar que se resetea
            circuit_breaker_reset = await execution_engine._check_circuit_breakers(balance)
            assert circuit_breaker_reset, "Circuit breaker debería resetearse"
            
            self.test_results['circuit_breakers'] = True
            logger.info("✅ Test de circuit breakers: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de circuit breakers: FAILED - {e}")
            self.test_results['circuit_breakers'] = False
            return False
    
    async def test_bitget_client(self) -> bool:
        """Test del cliente de Bitget"""
        logger.info("🌐 Test 5: Bitget client...")
        
        try:
            # Test de inicialización
            assert bitget_client is not None, "Cliente Bitget debería inicializarse"
            
            # Test de health check
            health = await bitget_client.health_check()
            assert isinstance(health, dict), "Health check debería retornar dict"
            assert 'rest_api' in health, "Health check debería incluir rest_api"
            assert 'websocket' in health, "Health check debería incluir websocket"
            
            # Test de estado de conexión
            status = bitget_client.get_connection_status()
            assert isinstance(status, dict), "Estado debería ser dict"
            assert 'trading_mode' in status, "Estado debería incluir trading_mode"
            
            self.test_results['bitget_client'] = True
            logger.info("✅ Test de Bitget client: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test de Bitget client: FAILED - {e}")
            self.test_results['bitget_client'] = False
            return False
    
    def print_test_results(self) -> None:
        """Imprime los resultados de los tests"""
        logger.info("\n" + "="*60)
        logger.info("🧪 RESULTADOS DE TESTS DEL SISTEMA DE TRADING")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name.upper()}: {status}")
        
        logger.info("-"*60)
        logger.info(f"TOTAL: {passed_tests}/{total_tests} tests pasaron")
        
        if passed_tests == total_tests:
            logger.info("🎉 ¡TODOS LOS TESTS PASARON! El sistema está listo.")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests fallaron. Revisar implementación.")
        
        logger.info("="*60)

async def main():
    """Función principal de testing"""
    logger.info("🚀 Iniciando tests del sistema de trading...")
    
    # Crear tester
    tester = TradingSystemTester()
    
    # Ejecutar tests
    results = await tester.run_all_tests()
    
    # Verificar si todos los tests pasaron
    all_passed = all(result for result in results.values() if isinstance(result, bool))
    
    if all_passed:
        logger.info("🎉 ¡Todos los tests del sistema de trading pasaron exitosamente!")
        return 0
    else:
        logger.error("❌ Algunos tests del sistema de trading fallaron.")
        return 1

if __name__ == "__main__":
    # Ejecutar tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
