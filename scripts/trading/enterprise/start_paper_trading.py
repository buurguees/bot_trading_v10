# Ruta: scripts/trading/enterprise/start_paper_trading.py
#!/usr/bin/env python3
"""
Script de Paper Trading Enterprise
=================================

Este script ejecuta el sistema de trading enterprise en modo simulado
para pruebas y desarrollo sin riesgo de pérdidas reales.

Características:
- Simulación completa del mercado
- Gestión de posiciones virtuales
- Señales ML en tiempo real
- Monitoreo y logging completo
- Interfaz web para supervisión

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from trading.enterprise import (
    FuturesEngine, SignalGenerator, PositionManager, 
    OrderExecutor, LeverageCalculator, MarketAnalyzer
)
from trading.bitget_client import bitget_client
from core.config.config_loader import user_config

# Configurar logging
logger = logging.getLogger(__name__)

class PaperTradingSystem:
    """Sistema de paper trading enterprise"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbols = config.get('symbols', [])
        self.leverage = config.get('leverage', 10)
        self.risk_percent = config.get('risk_percent', 2.0)
        self.max_positions = config.get('max_positions', 5)
        self.dry_run = config.get('dry_run', True)
        
        # Estado del sistema
        self.is_running = False
        self.start_time = None
        self.virtual_balance = 10000.0  # Balance virtual inicial
        self.initial_balance = 10000.0
        
        # Componentes del sistema
        self.futures_engine = None
        self.signal_generator = None
        self.position_manager = None
        self.order_executor = None
        self.leverage_calculator = None
        self.market_analyzer = None
        
        # Métricas
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Configurar directorios
        self.setup_directories()
        
        logger.info("📊 Sistema de Paper Trading inicializado")
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/paper_trading',
            'data/enterprise/paper_trading',
            'backups/enterprise/paper_trading'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def initialize_components(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("🔧 Inicializando componentes del sistema...")
            
            # Inicializar calculadora de leverage
            self.leverage_calculator = LeverageCalculator(
                max_leverage=30,
                min_leverage=1,
                risk_percent=self.risk_percent
            )
            
            # Inicializar analizador de mercado
            self.market_analyzer = MarketAnalyzer(
                symbols=self.symbols,
                timeframe='1m'
            )
            
            # Inicializar generador de señales
            self.signal_generator = SignalGenerator(
                symbols=self.symbols,
                model_path='models/enterprise/lstm_attention_model.pth',
                features=['price', 'volume', 'rsi', 'macd', 'bb_upper', 'bb_lower']
            )
            
            # Inicializar gestor de posiciones
            self.position_manager = PositionManager(
                max_positions=self.max_positions,
                risk_percent=self.risk_percent,
                leverage_calculator=self.leverage_calculator
            )
            
            # Inicializar ejecutor de órdenes (modo paper)
            self.order_executor = OrderExecutor(
                client=bitget_client,
                mode='paper_trading',
                virtual_balance=self.virtual_balance
            )
            
            # Inicializar motor de futuros
            self.futures_engine = FuturesEngine(
                symbols=self.symbols,
                signal_generator=self.signal_generator,
                position_manager=self.position_manager,
                order_executor=self.order_executor,
                market_analyzer=self.market_analyzer,
                leverage_calculator=self.leverage_calculator
            )
            
            logger.info("✅ Componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    async def start_data_collection(self):
        """Inicia la recolección de datos en tiempo real"""
        try:
            logger.info("📡 Iniciando recolección de datos...")
            
            # Callback para procesar datos de mercado
            async def market_data_callback(data):
                try:
                    if data.get('data'):
                        # Procesar datos de kline
                        for kline_data in data['data']:
                            symbol = kline_data.get('instId')
                            if symbol in self.symbols:
                                # Procesar con analizador de mercado
                                await self.market_analyzer.process_tick(kline_data)
                                
                                # Generar señales ML
                                signal = await self.signal_generator.generate_signal(symbol, kline_data)
                                if signal:
                                    # Procesar señal con el motor de futuros
                                    await self.futures_engine.process_signal(symbol, signal)
                
                except Exception as e:
                    logger.error(f"Error procesando datos de mercado: {e}")
            
            # Iniciar streaming WebSocket
            success = await bitget_client.start_websocket_streaming(
                symbols=self.symbols,
                callback=market_data_callback,
                topics=['kline', 'ticker']
            )
            
            if success:
                logger.info("✅ Recolección de datos iniciada")
                return True
            else:
                logger.error("❌ Error iniciando recolección de datos")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en recolección de datos: {e}")
            return False
    
    async def run_trading_loop(self):
        """Loop principal de trading"""
        try:
            logger.info("🔄 Iniciando loop de trading...")
            
            while self.is_running:
                try:
                    # Verificar estado del sistema
                    await self.check_system_health()
                    
                    # Actualizar métricas
                    await self.update_metrics()
                    
                    # Verificar posiciones existentes
                    await self.manage_existing_positions()
                    
                    # Generar nuevas señales
                    await self.generate_new_signals()
                    
                    # Esperar antes de la siguiente iteración
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error en loop de trading: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Error en loop de trading: {e}")
    
    async def check_system_health(self):
        """Verifica la salud del sistema"""
        try:
            # Verificar conexión a Bitget
            health = await bitget_client.health_check()
            if not health.get('rest_api', False):
                logger.warning("⚠️ Conexión REST API no disponible")
            
            # Verificar componentes
            if not self.futures_engine:
                logger.error("❌ Motor de futuros no disponible")
                self.is_running = False
            
        except Exception as e:
            logger.error(f"Error verificando salud del sistema: {e}")
    
    async def update_metrics(self):
        """Actualiza las métricas del sistema"""
        try:
            # Obtener posiciones actuales
            positions = await self.position_manager.get_all_positions()
            
            # Calcular PnL total
            total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
            self.total_pnl = total_pnl
            
            # Calcular drawdown
            current_balance = self.initial_balance + total_pnl
            if current_balance > self.initial_balance:
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.initial_balance - current_balance) / self.initial_balance * 100
                self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
            
            # Log de métricas cada 60 segundos
            if int(time.time()) % 60 == 0:
                logger.info(f"📊 Métricas - PnL: ${total_pnl:.2f}, Drawdown: {self.current_drawdown:.2f}%")
                
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    async def manage_existing_positions(self):
        """Gestiona las posiciones existentes"""
        try:
            positions = await self.position_manager.get_all_positions()
            
            for position in positions:
                symbol = position['symbol']
                side = position['side']
                size = position['size']
                entry_price = position['entry_price']
                
                # Obtener precio actual
                ticker = await bitget_client.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker['last']
                
                # Calcular PnL
                if side == 'long':
                    pnl = (current_price - entry_price) * size
                else:
                    pnl = (entry_price - current_price) * size
                
                # Verificar stop loss y take profit
                stop_loss = position.get('stop_loss')
                take_profit = position.get('take_profit')
                
                if stop_loss and ((side == 'long' and current_price <= stop_loss) or 
                                 (side == 'short' and current_price >= stop_loss)):
                    logger.info(f"🛑 Stop loss activado: {symbol}")
                    await self.position_manager.close_position(symbol, side, size)
                    self.losing_trades += 1
                
                elif take_profit and ((side == 'long' and current_price >= take_profit) or 
                                     (side == 'short' and current_price <= take_profit)):
                    logger.info(f"🎯 Take profit activado: {symbol}")
                    await self.position_manager.close_position(symbol, side, size)
                    self.winning_trades += 1
                
        except Exception as e:
            logger.error(f"Error gestionando posiciones: {e}")
    
    async def generate_new_signals(self):
        """Genera nuevas señales de trading"""
        try:
            for symbol in self.symbols:
                # Verificar si ya tenemos posición en este símbolo
                existing_position = await self.position_manager.get_position(symbol)
                if existing_position:
                    continue
                
                # Generar señal
                signal = await self.signal_generator.generate_signal(symbol)
                if signal and signal['confidence'] > 0.7:
                    # Procesar señal
                    await self.futures_engine.process_signal(symbol, signal)
                    
        except Exception as e:
            logger.error(f"Error generando señales: {e}")
    
    async def start(self):
        """Inicia el sistema de paper trading"""
        try:
            logger.info("🚀 Iniciando sistema de paper trading...")
            
            # Inicializar componentes
            if not await self.initialize_components():
                return False
            
            # Iniciar recolección de datos
            if not await self.start_data_collection():
                return False
            
            # Marcar como ejecutándose
            self.is_running = True
            self.start_time = datetime.now()
            
            # Iniciar loop de trading
            await self.run_trading_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando sistema: {e}")
            return False
    
    async def stop(self):
        """Detiene el sistema de paper trading"""
        try:
            logger.info("⏹️ Deteniendo sistema de paper trading...")
            
            self.is_running = False
            
            # Cerrar todas las posiciones
            positions = await self.position_manager.get_all_positions()
            for position in positions:
                await self.position_manager.close_position(
                    position['symbol'], 
                    position['side'], 
                    position['size']
                )
            
            # Cerrar conexiones
            await bitget_client.close()
            
            # Generar reporte final
            await self.generate_final_report()
            
            logger.info("✅ Sistema detenido correctamente")
            
        except Exception as e:
            logger.error(f"Error deteniendo sistema: {e}")
    
    async def generate_final_report(self):
        """Genera reporte final del sistema"""
        try:
            runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
            
            report = {
                'runtime': str(runtime),
                'initial_balance': self.initial_balance,
                'final_balance': self.initial_balance + self.total_pnl,
                'total_pnl': self.total_pnl,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
                'max_drawdown': self.max_drawdown,
                'current_drawdown': self.current_drawdown
            }
            
            # Guardar reporte
            report_path = f"logs/enterprise/paper_trading/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info("📊 Reporte final generado:")
            logger.info(f"  Runtime: {runtime}")
            logger.info(f"  Balance inicial: ${self.initial_balance:.2f}")
            logger.info(f"  Balance final: ${report['final_balance']:.2f}")
            logger.info(f"  PnL total: ${self.total_pnl:.2f}")
            logger.info(f"  Total trades: {self.total_trades}")
            logger.info(f"  Win rate: {report['win_rate']:.2%}")
            logger.info(f"  Max drawdown: {self.max_drawdown:.2f}%")
            
        except Exception as e:
            logger.error(f"Error generando reporte final: {e}")

async def start_paper_trading(config: Dict[str, Any]):
    """Función principal para iniciar paper trading"""
    try:
        # Crear sistema de paper trading
        system = PaperTradingSystem(config)
        
        # Iniciar sistema
        success = await system.start()
        
        if not success:
            logger.error("❌ Error iniciando sistema de paper trading")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en paper trading: {e}")
        return False

if __name__ == "__main__":
    # Configuración de ejemplo
    config = {
        'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        'leverage': 10,
        'risk_percent': 2.0,
        'max_positions': 3,
        'dry_run': True
    }
    
    # Ejecutar sistema
    asyncio.run(start_paper_trading(config))