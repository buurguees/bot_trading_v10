#!/usr/bin/env python3
"""
Script de Inicio con Métricas
=============================

Este script inicia el bot con el sistema de métricas integrado.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent))

from bot import TradingBot
from core.monitoring.metrics_sender import MetricsSender

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotWithMetrics:
    """Bot con sistema de métricas integrado"""
    
    def __init__(self):
        self.bot = None
        self.metrics_sender = None
        self.metrics_task = None
        self.is_running = False
        
    async def start(self, mode: str = "paper", symbols: list = None, telegram_enabled: bool = True):
        """Iniciar bot con métricas"""
        try:
            # Crear instancia del bot
            self.bot = TradingBot()
            await self.bot.initialize(telegram_enabled=telegram_enabled)
            
            # Iniciar trading
            await self.bot.start_trading(mode=mode, symbols=symbols)
            
            # Iniciar sistema de métricas
            self.metrics_sender = MetricsSender()
            self.metrics_task = asyncio.create_task(
                self.metrics_loop()
            )
            
            self.is_running = True
            logger.info("🚀 Bot con métricas iniciado exitosamente")
            
            # Mantener ejecutándose
            try:
                while self.is_running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Interrupción recibida")
                
        except Exception as e:
            logger.error(f"❌ Error iniciando bot: {e}")
            raise
        finally:
            await self.stop()
    
    async def metrics_loop(self):
        """Loop de métricas"""
        while self.is_running:
            try:
                # Obtener métricas del bot
                status = await self.bot.get_status()
                
                # Simular métricas (en producción vendrían de Redis/TimescaleDB)
                metrics = {
                    'trades': 42,
                    'win_rate': 0.65,
                    'daily_pnl': 125.50,
                    'balance': 10500.75,
                    'balance_pct': 0.12,
                    'total_pnl': 2500.25,
                    'max_drawdown': 0.08,
                    'sharpe_ratio': 1.85,
                    'active_positions': 3,
                    'max_positions': 10,
                    'risk_per_trade': 2.0,
                    'cpu_usage': 45.2,
                    'memory_usage': 67.8,
                    'latency_ms': 25,
                    'data_points': 15000,
                    'cache_hits': 1200,
                    'cache_misses': 150,
                    'bot_active': status.get('is_running', False)
                }
                
                # Enviar métricas
                await self.metrics_sender.send_training_update(metrics)
                
                # Esperar intervalo
                await asyncio.sleep(60)  # 60 segundos
                
            except Exception as e:
                logger.error(f"Error en loop de métricas: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Detener bot y métricas"""
        try:
            self.is_running = False
            
            if self.metrics_task:
                self.metrics_task.cancel()
                try:
                    await self.metrics_task
                except asyncio.CancelledError:
                    pass
            
            if self.bot:
                await self.bot.shutdown()
            
            logger.info("✅ Bot detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot: {e}")

async def main():
    """Función principal"""
    print("🤖 Bot Trading v10 Enterprise con Métricas")
    print("=" * 50)
    
    # Verificar variables de entorno
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("❌ TELEGRAM_BOT_TOKEN no configurado")
        return
    
    if not os.getenv("TELEGRAM_CHAT_ID"):
        print("❌ TELEGRAM_CHAT_ID no configurado")
        return
    
    print(f"✅ Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN')[:10]}...")
    print(f"✅ Chat ID: {os.getenv('TELEGRAM_CHAT_ID')}")
    print()
    
    # Crear e iniciar bot
    bot_with_metrics = BotWithMetrics()
    
    try:
        await bot_with_metrics.start(
            mode="paper",
            symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT"],
            telegram_enabled=True
        )
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
