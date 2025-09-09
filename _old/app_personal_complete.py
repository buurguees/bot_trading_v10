#!/usr/bin/env python3
"""
Bot Trading v10 Personal - Orquestador Principal
================================================

Sistema de trading personal optimizado para uso individual con:
- Soporte multi-exchange (Bitget + Binance)
- Arbitraje automático
- Optimización de latencia <50ms
- Dashboard personal
- Monitoreo simplificado

Uso:
    python app_personal_complete.py --mode live --symbols BTCUSDT,ETHUSDT
    python app_personal_complete.py --mode paper --arbitrage
    python app_personal_complete.py --mode hft --symbols BTCUSDT
    python app_personal_complete.py --dashboard
    python app_personal_complete.py --benchmark

Autor: Bot Trading v10 Personal
Versión: 10.0.0
"""

import asyncio
import argparse
import logging
import sys
import os
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.personal.multi_exchange import MultiExchangeManager, ArbitrageDetector, ExchangeSyncManager
from src.core.personal.latency import LatencyOptimizer
from src.core.config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/personal_trading.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PersonalTradingBot:
    """Bot de trading personal optimizado"""
    
    def __init__(self, config_path: str = "config/personal/exchanges.yaml"):
        self.config_path = config_path
        self.config_manager = EnterpriseConfigManager(config_path)
        self.exchange_manager = None
        self.arbitrage_detector = None
        self.sync_manager = None
        self.latency_optimizer = None
        self.is_running = False
        
        # Crear directorio de logs
        Path("logs").mkdir(exist_ok=True)
        
        logger.info("🤖 Personal Trading Bot v10 inicializado")
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema personal"""
        try:
            logger.info("🚀 Inicializando sistema personal...")
            
            # Cargar configuración
            config = self.config_manager.load_config()
            logger.info("✅ Configuración cargada")
            
            # Inicializar gestor de exchanges
            self.exchange_manager = MultiExchangeManager(self.config_path)
            await self.exchange_manager.start()
            logger.info("✅ Gestor de exchanges inicializado")
            
            # Inicializar detector de arbitraje
            arbitrage_config = config.get('arbitrage', {})
            self.arbitrage_detector = ArbitrageDetector(self.exchange_manager, arbitrage_config)
            await self.arbitrage_detector.start()
            logger.info("✅ Detector de arbitraje inicializado")
            
            # Inicializar gestor de sincronización
            sync_config = config.get('sync', {})
            self.sync_manager = ExchangeSyncManager(self.exchange_manager, sync_config)
            await self.sync_manager.start()
            logger.info("✅ Gestor de sincronización inicializado")
            
            # Inicializar optimizador de latencia
            latency_config = config.get('latency', {})
            self.latency_optimizer = LatencyOptimizer(self.exchange_manager, latency_config)
            await self.latency_optimizer.start()
            logger.info("✅ Optimizador de latencia inicializado")
            
            self.is_running = True
            logger.info("🎉 Sistema personal inicializado completamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema personal: {e}")
            raise
    
    async def run_live_trading(self, symbols: List[str], leverage: int = 10):
        """Ejecuta trading en vivo"""
        try:
            logger.info(f"💰 Iniciando trading en vivo")
            logger.info(f"📊 Símbolos: {', '.join(symbols)}")
            logger.info(f"⚡ Leverage: {leverage}x")
            
            # Verificar conexiones
            connection_status = self.exchange_manager.get_connection_status()
            for exchange_id, status in connection_status.items():
                if status:
                    logger.info(f"✅ {exchange_id} conectado")
                else:
                    logger.warning(f"⚠️ {exchange_id} desconectado")
            
            # Iniciar trading continuo
            await self._continuous_trading(symbols, leverage)
            
        except Exception as e:
            logger.error(f"❌ Error en trading en vivo: {e}")
            raise
    
    async def run_paper_trading(self, symbols: List[str], leverage: int = 10):
        """Ejecuta trading simulado"""
        try:
            logger.info(f"📝 Iniciando trading simulado")
            logger.info(f"📊 Símbolos: {', '.join(symbols)}")
            logger.info(f"⚡ Leverage: {leverage}x")
            
            # Iniciar trading simulado
            await self._continuous_paper_trading(symbols, leverage)
            
        except Exception as e:
            logger.error(f"❌ Error en trading simulado: {e}")
            raise
    
    async def run_arbitrage_trading(self, symbols: List[str]):
        """Ejecuta trading de arbitraje"""
        try:
            logger.info(f"🔄 Iniciando trading de arbitraje")
            logger.info(f"📊 Símbolos: {', '.join(symbols)}")
            
            # Iniciar arbitraje continuo
            await self._continuous_arbitrage(symbols)
            
        except Exception as e:
            logger.error(f"❌ Error en trading de arbitraje: {e}")
            raise
    
    async def run_hft_trading(self, symbols: List[str]):
        """Ejecuta trading de alta frecuencia"""
        try:
            logger.info(f"⚡ Iniciando trading de alta frecuencia")
            logger.info(f"📊 Símbolos: {', '.join(symbols)}")
            
            # Iniciar HFT
            await self._continuous_hft(symbols)
            
        except Exception as e:
            logger.error(f"❌ Error en trading HFT: {e}")
            raise
    
    async def _continuous_trading(self, symbols: List[str], leverage: int):
        """Trading continuo en vivo"""
        while self.is_running:
            try:
                for symbol in symbols:
                    # Obtener order book optimizado
                    order_book = await self.latency_optimizer.get_order_book_optimized(symbol)
                    
                    if order_book.get('success'):
                        # Aquí implementarías tu estrategia de trading
                        logger.debug(f"Order book obtenido para {symbol}: {order_book['latency_ms']:.2f}ms")
                
                await asyncio.sleep(1)  # Trading cada segundo
                
            except Exception as e:
                logger.error(f"Error en trading continuo: {e}")
                await asyncio.sleep(5)
    
    async def _continuous_paper_trading(self, symbols: List[str], leverage: int):
        """Trading simulado continuo"""
        while self.is_running:
            try:
                for symbol in symbols:
                    # Simular análisis de mercado
                    order_book = await self.latency_optimizer.get_order_book_optimized(symbol)
                    
                    if order_book.get('success'):
                        # Simular decisión de trading
                        logger.debug(f"Simulando análisis para {symbol}: {order_book['latency_ms']:.2f}ms")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error en trading simulado: {e}")
                await asyncio.sleep(5)
    
    async def _continuous_arbitrage(self, symbols: List[str]):
        """Arbitraje continuo"""
        while self.is_running:
            try:
                # Obtener oportunidades de arbitraje
                opportunities = self.arbitrage_detector.get_opportunities()
                
                for opportunity in opportunities:
                    if opportunity.symbol in symbols:
                        logger.info(f"💰 Oportunidad de arbitraje: {opportunity.symbol} "
                                  f"Spread: {opportunity.spread_pct:.2f}% "
                                  f"Profit: ${opportunity.profit_usdt:.2f}")
                        
                        # Ejecutar arbitraje (opcional)
                        # result = await self.arbitrage_detector.execute_arbitrage(opportunity)
                
                await asyncio.sleep(5)  # Verificar cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error en arbitraje: {e}")
                await asyncio.sleep(10)
    
    async def _continuous_hft(self, symbols: List[str]):
        """Trading de alta frecuencia continuo"""
        while self.is_running:
            try:
                for symbol in symbols:
                    # Obtener order book con latencia optimizada
                    order_book = await self.latency_optimizer.get_order_book_optimized(symbol)
                    
                    if order_book.get('success') and order_book['latency_ms'] < 50:
                        # Ejecutar trades de alta frecuencia
                        logger.debug(f"HFT {symbol}: {order_book['latency_ms']:.2f}ms")
                
                await asyncio.sleep(0.1)  # HFT cada 100ms
                
            except Exception as e:
                logger.error(f"Error en HFT: {e}")
                await asyncio.sleep(1)
    
    async def run_benchmark(self, operations: int = 100):
        """Ejecuta benchmark de rendimiento"""
        try:
            logger.info(f"🏁 Iniciando benchmark con {operations} operaciones...")
            
            # Benchmark de latencia
            benchmark_result = await self.latency_optimizer.benchmark_latency(operations)
            
            logger.info("📊 Resultados del benchmark:")
            logger.info(f"   Operaciones: {benchmark_result['operations']}")
            logger.info(f"   Operaciones exitosas: {benchmark_result['successful_operations']}")
            logger.info(f"   Tasa de éxito: {benchmark_result['success_rate']:.2%}")
            logger.info(f"   Latencia promedio: {benchmark_result['avg_latency_ms']:.2f}ms")
            logger.info(f"   Latencia P95: {benchmark_result['p95_latency_ms']:.2f}ms")
            logger.info(f"   Latencia P99: {benchmark_result['p99_latency_ms']:.2f}ms")
            
            return benchmark_result
            
        except Exception as e:
            logger.error(f"❌ Error en benchmark: {e}")
            raise
    
    async def run_dashboard(self):
        """Inicia el dashboard personal"""
        try:
            logger.info("📊 Iniciando dashboard personal...")
            
            # Aquí implementarías el dashboard web
            # Por ahora, mostramos métricas en consola
            await self._show_metrics()
            
        except Exception as e:
            logger.error(f"❌ Error en dashboard: {e}")
            raise
    
    async def _show_metrics(self):
        """Muestra métricas del sistema"""
        try:
            while self.is_running:
                # Limpiar pantalla
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 80)
                print("🤖 BOT TRADING V10 PERSONAL - DASHBOARD")
                print("=" * 80)
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                # Estado de exchanges
                print("📊 ESTADO DE EXCHANGES:")
                connection_status = self.exchange_manager.get_connection_status()
                for exchange_id, status in connection_status.items():
                    status_icon = "✅" if status else "❌"
                    print(f"   {status_icon} {exchange_id.upper()}: {'CONECTADO' if status else 'DESCONECTADO'}")
                print()
                
                # Métricas de latencia
                print("⚡ MÉTRICAS DE LATENCIA:")
                perf_stats = self.latency_optimizer.get_performance_stats()
                print(f"   Latencia promedio: {perf_stats['avg_latency_ms']:.2f}ms")
                print(f"   Latencia P95: {perf_stats['p95_latency_ms']:.2f}ms")
                print(f"   Latencia P99: {perf_stats['p99_latency_ms']:.2f}ms")
                print(f"   Tasa de éxito: {perf_stats['success_rate']:.2%}")
                print()
                
                # Oportunidades de arbitraje
                print("💰 OPORTUNIDADES DE ARBITRAJE:")
                opportunities = self.arbitrage_detector.get_opportunities()
                if opportunities:
                    for opp in opportunities[:5]:  # Mostrar top 5
                        print(f"   {opp.symbol}: {opp.spread_pct:.2f}% spread, ${opp.profit_usdt:.2f} profit")
                else:
                    print("   No hay oportunidades detectadas")
                print()
                
                # Estado de sincronización
                print("🔄 ESTADO DE SINCRONIZACIÓN:")
                sync_status = self.sync_manager.get_sync_status()
                for exchange_id, status in sync_status.items():
                    sync_icon = "✅" if status['is_synced'] else "⚠️"
                    print(f"   {sync_icon} {exchange_id.upper()}: {'SINCRONIZADO' if status['is_synced'] else 'DESINCRONIZADO'}")
                print()
                
                print("=" * 80)
                print("Presiona Ctrl+C para salir")
                
                await asyncio.sleep(5)  # Actualizar cada 5 segundos
                
        except KeyboardInterrupt:
            logger.info("Dashboard detenido por el usuario")
        except Exception as e:
            logger.error(f"Error en dashboard: {e}")
    
    async def shutdown(self):
        """Cierra el sistema de forma segura"""
        try:
            logger.info("🛑 Cerrando sistema personal...")
            self.is_running = False
            
            if self.latency_optimizer:
                await self.latency_optimizer.stop()
            
            if self.sync_manager:
                await self.sync_manager.stop()
            
            if self.arbitrage_detector:
                await self.arbitrage_detector.stop()
            
            if self.exchange_manager:
                await self.exchange_manager.stop()
            
            logger.info("✅ Sistema personal cerrado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando sistema: {e}")

async def main():
    """Función principal del bot personal"""
    parser = argparse.ArgumentParser(
        description="Bot Trading v10 Personal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python app_personal_complete.py --mode live --symbols BTCUSDT,ETHUSDT --leverage 10
  python app_personal_complete.py --mode paper --symbols BTCUSDT,ETHUSDT,ADAUSDT
  python app_personal_complete.py --mode arbitrage --symbols BTCUSDT,ETHUSDT
  python app_personal_complete.py --mode hft --symbols BTCUSDT
  python app_personal_complete.py --dashboard
  python app_personal_complete.py --benchmark --operations 100
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['live', 'paper', 'arbitrage', 'hft'],
        help='Modo de operación del bot'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Símbolos a tradear (separados por comas)'
    )
    
    parser.add_argument(
        '--leverage',
        type=int,
        default=10,
        help='Leverage a utilizar (5-30)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/personal/exchanges.yaml',
        help='Ruta al archivo de configuración'
    )
    
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Iniciar dashboard personal'
    )
    
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Ejecutar benchmark de rendimiento'
    )
    
    parser.add_argument(
        '--operations',
        type=int,
        default=100,
        help='Número de operaciones para benchmark'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del bot
    bot = PersonalTradingBot(args.config)
    
    # Configurar manejo de señales
    def signal_handler(signum, frame):
        logger.info("Señal de interrupción recibida")
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Inicializar sistema
        await bot.initialize()
        
        # Ejecutar comando solicitado
        if args.dashboard:
            await bot.run_dashboard()
        
        elif args.benchmark:
            await bot.run_benchmark(args.operations)
        
        elif args.mode:
            if not args.symbols:
                logger.error("❌ Se requiere especificar símbolos con --symbols")
                return
            
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
            
            # Validar leverage
            if not (5 <= args.leverage <= 30):
                logger.error("❌ Leverage debe estar entre 5 y 30")
                return
            
            if args.mode == 'live':
                await bot.run_live_trading(symbols, args.leverage)
            elif args.mode == 'paper':
                await bot.run_paper_trading(symbols, args.leverage)
            elif args.mode == 'arbitrage':
                await bot.run_arbitrage_trading(symbols)
            elif args.mode == 'hft':
                await bot.run_hft_trading(symbols)
        
        else:
            logger.info("ℹ️ Usa --help para ver las opciones disponibles")
            await bot.run_dashboard()
    
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupción del usuario")
    
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Ejecutar bot
    asyncio.run(main())
