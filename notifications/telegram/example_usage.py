#!/usr/bin/env python3
"""
Ejemplo de Uso del Bot de Telegram - Trading Bot v10 Enterprise
==============================================================

Este script muestra cómo usar el bot de Telegram programáticamente
y cómo integrarlo con tu sistema de trading.

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import asyncio
import logging
from pathlib import Path
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from notifications.telegram.telegram_bot import TelegramBot
from notifications.telegram.metrics_sender import MetricsSender

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def example_basic_usage():
    """Ejemplo básico de uso del bot"""
    print("🤖 Ejemplo: Uso Básico del Bot de Telegram")
    print("=" * 50)
    
    try:
        # Crear instancia del bot
        bot = TelegramBot('notifications/telegram/config.yaml')
        
        # Enviar mensaje de prueba
        message = """
🚀 <b>Bot de Telegram Iniciado</b>

✅ Sistema funcionando correctamente
📊 Métricas disponibles
🎮 Comandos listos

Usa /help para ver todos los comandos disponibles.
        """
        
        success = await bot.send_message(message)
        
        if success:
            print("✅ Mensaje enviado correctamente")
        else:
            print("❌ Error enviando mensaje")
        
        # Enviar alerta de prueba
        alert_message = "Sistema iniciado correctamente"
        await bot.send_alert(alert_message, "INFO")
        
        print("✅ Alerta enviada correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_metrics_sending():
    """Ejemplo de envío de métricas"""
    print("\n📊 Ejemplo: Envío de Métricas")
    print("=" * 50)
    
    try:
        # Crear bot y metrics sender
        bot = TelegramBot('notifications/telegram/config.yaml')
        config = bot.get_config()
        
        sender = MetricsSender(bot, config['telegram'])
        
        # Obtener métricas actuales
        metrics = await sender.get_current_metrics()
        print(f"📈 Métricas obtenidas: {len(metrics)} campos")
        
        # Formatear y enviar métricas
        message = sender.format_metrics_message(metrics)
        success = await bot.send_message(message)
        
        if success:
            print("✅ Métricas enviadas correctamente")
        else:
            print("❌ Error enviando métricas")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_alert_monitoring():
    """Ejemplo de monitoreo de alertas"""
    print("\n🚨 Ejemplo: Monitoreo de Alertas")
    print("=" * 50)
    
    try:
        bot = TelegramBot('notifications/telegram/config.yaml')
        config = bot.get_config()
        
        sender = MetricsSender(bot, config['telegram'])
        
        # Simular métricas con alertas
        test_metrics = {
            'balance': 10000.0,
            'pnl_today': 1500.0,  # PnL alto para alerta
            'win_rate': 75.0,
            'drawdown': 15.0,     # Drawdown alto para alerta
            'latency': 150.0,     # Latencia alta para alerta
            'trades_today': 10,
            'positions': 3,
            'health_score': 65.0  # Salud baja para alerta
        }
        
        # Verificar alertas
        await sender._check_pnl_alert(test_metrics)
        await sender._check_drawdown_alert(test_metrics)
        await sender._check_latency_alert(test_metrics)
        await sender._check_health_alert(test_metrics)
        
        print("✅ Alertas verificadas correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_custom_commands():
    """Ejemplo de comandos personalizados"""
    print("\n🎮 Ejemplo: Comandos Personalizados")
    print("=" * 50)
    
    try:
        bot = TelegramBot('notifications/telegram/config.yaml')
        
        # Enviar diferentes tipos de mensajes
        messages = [
            "📊 <b>Reporte Diario</b>\n\nBalance: $10,500\nPnL: +$250\nTrades: 5",
            "🎯 <b>Posiciones Activas</b>\n\nBTCUSDT: Long +$150\nETHUSDT: Short -$50",
            "⚠️ <b>Alerta de Riesgo</b>\n\nDrawdown: 8.5%\nRevisar posiciones",
            "✅ <b>Operación Exitosa</b>\n\nTrade cerrado con ganancia de $200"
        ]
        
        for i, message in enumerate(messages, 1):
            print(f"Enviando mensaje {i}/4...")
            success = await bot.send_message(message)
            
            if success:
                print(f"✅ Mensaje {i} enviado")
            else:
                print(f"❌ Error en mensaje {i}")
            
            # Esperar un poco entre mensajes
            await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_integration_with_trading():
    """Ejemplo de integración con sistema de trading"""
    print("\n🔄 Ejemplo: Integración con Trading")
    print("=" * 50)
    
    try:
        bot = TelegramBot('notifications/telegram/config.yaml')
        
        # Simular eventos de trading
        trading_events = [
            {
                'type': 'trade_opened',
                'symbol': 'BTCUSDT',
                'side': 'long',
                'price': 50000,
                'size': 0.1
            },
            {
                'type': 'trade_closed',
                'symbol': 'BTCUSDT',
                'pnl': 150.0,
                'pnl_pct': 3.0
            },
            {
                'type': 'alert',
                'level': 'warning',
                'message': 'Drawdown approaching limit'
            }
        ]
        
        for event in trading_events:
            if event['type'] == 'trade_opened':
                message = f"""
🟢 <b>Trade Abierto</b>

Símbolo: {event['symbol']}
Dirección: {event['side'].upper()}
Precio: ${event['price']:,.2f}
Tamaño: {event['size']}
                """
            elif event['type'] == 'trade_closed':
                pnl_emoji = "📈" if event['pnl'] > 0 else "📉"
                message = f"""
{pnl_emoji} <b>Trade Cerrado</b>

Símbolo: {event['symbol']}
PnL: ${event['pnl']:,.2f} ({event['pnl_pct']:+.1f}%)
                """
            elif event['type'] == 'alert':
                message = f"""
⚠️ <b>Alerta: {event['level'].upper()}</b>

{event['message']}
                """
            
            success = await bot.send_message(message)
            print(f"✅ Evento {event['type']} procesado")
            
            await asyncio.sleep(0.5)
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Función principal con todos los ejemplos"""
    print("🚀 Trading Bot v10 - Ejemplos de Telegram Bot")
    print("=" * 60)
    print()
    
    # Verificar configuración
    config_path = Path('notifications/telegram/config.yaml')
    if not config_path.exists():
        print("❌ Archivo de configuración no encontrado")
        print("Ejecuta primero: python notifications/telegram/get_chat_id.py")
        return
    
    print("📋 Ejecutando ejemplos...")
    print()
    
    # Ejecutar ejemplos
    await example_basic_usage()
    await example_metrics_sending()
    await example_alert_monitoring()
    await example_custom_commands()
    await example_integration_with_trading()
    
    print("\n✅ Todos los ejemplos completados")
    print("\n💡 Para usar el bot en producción:")
    print("   python bot.py --mode paper --symbols BTCUSDT --telegram-enabled")

if __name__ == "__main__":
    asyncio.run(main())
