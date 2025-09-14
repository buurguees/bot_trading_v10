#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/setup/setup_telegram_for_tests.py
=========================================
Configuración de Telegram para Pruebas

Configura Telegram específicamente para las pruebas del sistema mejorado,
incluyendo validación de conexión y envío de mensajes de prueba.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.telegram.trade_reporter import TelegramTradeReporter, TelegramConfig
from core.metrics.trade_metrics import DetailedTradeMetric, TradeAction, ConfidenceLevel

def print_banner():
    """Muestra el banner de configuración"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    📱 CONFIGURACIÓN DE TELEGRAM PARA PRUEBAS 📱            ║
║                    Bot Trading v10 Enterprise                              ║
║                                                                              ║
║  🔧 Configuración automática de credenciales                              ║
║  🧪 Envío de mensajes de prueba                                           ║
║  📊 Validación de formato de reportes                                     ║
║  ⚡ Configuración optimizada para testing                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

async def test_telegram_connection(bot_token: str, chat_id: str) -> bool:
    """Prueba la conexión con Telegram"""
    print("🧪 Probando conexión con Telegram...")
    
    try:
        # Crear configuración
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        # Crear reporter
        reporter = TelegramTradeReporter(config)
        
        # Enviar mensaje de prueba
        success = await reporter.send_performance_alert(
            "TEST",
            "🧪 Mensaje de prueba del Sistema de Validación\n\n✅ Conexión exitosa con Telegram!",
            "INFO"
        )
        
        if success:
            print("✅ Conexión con Telegram exitosa!")
            print("📱 Revisa tu chat de Telegram para ver el mensaje de prueba")
            return True
        else:
            print("❌ Error enviando mensaje de prueba")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")
        return False

async def test_trade_reporting(bot_token: str, chat_id: str) -> bool:
    """Prueba el reporte de trades individuales"""
    print("📊 Probando reporte de trades individuales...")
    
    try:
        # Crear configuración
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        # Crear reporter
        reporter = TelegramTradeReporter(config)
        
        # Crear trade de prueba
        trade_data = {
            'action': 'LONG',
            'entry_price': 50000.0,
            'exit_price': 51000.0,
            'quantity': 0.1,
            'leverage': 1.0,
            'entry_time': datetime.now(),
            'exit_time': datetime.now(),
            'duration_candles': 12,
            'balance_before': 1000.0,
            'follow_plan': True,
            'exit_reason': 'TAKE_PROFIT',
            'slippage': 0.0,
            'commission': 0.5,
            'timeframe': '5m'
        }
        
        technical_analysis = {
            'confidence_level': 'HIGH',
            'strategy_name': 'test_strategy',
            'confluence_score': 0.8,
            'risk_reward_ratio': 2.0,
            'indicators': {'rsi': 65.0, 'macd': 0.1},
            'support_resistance': {'support': 49500.0, 'resistance': 51500.0},
            'trend_strength': 0.7,
            'momentum_score': 0.6
        }
        
        market_context = {
            'market_regime': 'TRENDING_UP',
            'volatility_level': 0.02,
            'volume_confirmation': True,
            'market_session': 'EUROPEAN',
            'news_impact': None
        }
        
        # Crear métrica de trade
        trade_metric = DetailedTradeMetric.create_from_trade_data(
            trade_data=trade_data,
            agent_symbol='BTCUSDT',
            cycle_id=1,
            technical_analysis=technical_analysis,
            market_context=market_context
        )
        
        # Enviar reporte de trade
        success = await reporter.send_individual_trade_alert(trade_metric)
        
        if success:
            print("✅ Reporte de trade individual enviado exitosamente!")
            return True
        else:
            print("❌ Error enviando reporte de trade individual")
            return False
            
    except Exception as e:
        print(f"❌ Error probando reporte de trades: {e}")
        return False

async def test_cycle_summary(bot_token: str, chat_id: str) -> bool:
    """Prueba el resumen de ciclo"""
    print("📈 Probando resumen de ciclo...")
    
    try:
        # Crear configuración
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        # Crear reporter
        reporter = TelegramTradeReporter(config)
        
        # Crear métricas de portfolio simuladas
        from core.sync.enhanced_metrics_aggregator import PortfolioMetrics
        
        portfolio_metrics = PortfolioMetrics(
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
            avg_trade_duration=2.0,
            best_performing_agent="BTCUSDT",
            worst_performing_agent="ETHUSDT",
            strategy_effectiveness={"strategy_1": 0.8, "strategy_2": 0.6},
            avg_quality_score=75.0,
            high_quality_trades_pct=0.6,
            avg_confluence_score=0.7,
            correlation_matrix={"BTCUSDT": {"ETHUSDT": 0.3}},
            agent_contributions={"BTCUSDT": 0.6, "ETHUSDT": 0.4},
            avg_cycle_duration=2.0,
            trades_per_hour=2.5,
            efficiency_score=0.8
        )
        
        # Crear resúmenes de agentes simulados
        agent_summaries = {
            "BTCUSDT": {
                "pnl": 100.0,
                "pnl_pct": 10.0,
                "trades": 3,
                "win_rate": 0.67,
                "drawdown": 2.5,
                "avg_quality": 85.0
            },
            "ETHUSDT": {
                "pnl": 50.0,
                "pnl_pct": 5.0,
                "trades": 2,
                "win_rate": 0.5,
                "drawdown": 1.8,
                "avg_quality": 75.0
            }
        }
        
        # Enviar resumen de ciclo
        success = await reporter.send_cycle_summary(portfolio_metrics, agent_summaries)
        
        if success:
            print("✅ Resumen de ciclo enviado exitosamente!")
            return True
        else:
            print("❌ Error enviando resumen de ciclo")
            return False
            
    except Exception as e:
        print(f"❌ Error probando resumen de ciclo: {e}")
        return False

async def run_comprehensive_test(bot_token: str, chat_id: str) -> Dict[str, bool]:
    """Ejecuta prueba comprensiva de Telegram"""
    print("🧪 Ejecutando prueba comprensiva de Telegram...")
    
    results = {}
    
    # 1. Prueba de conexión
    results['connection'] = await test_telegram_connection(bot_token, chat_id)
    
    # 2. Prueba de reporte de trades
    results['trade_reporting'] = await test_trade_reporting(bot_token, chat_id)
    
    # 3. Prueba de resumen de ciclo
    results['cycle_summary'] = await test_cycle_summary(bot_token, chat_id)
    
    # 4. Prueba de alertas
    print("🚨 Probando alertas...")
    try:
        config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enable_individual_trades=True,
            enable_cycle_summaries=True,
            enable_alerts=True
        )
        
        reporter = TelegramTradeReporter(config)
        
        success = await reporter.send_performance_alert(
            "BTCUSDT",
            "🚨 Alerta de prueba del sistema de validación\n\n⚠️ Esta es una alerta de prueba",
            "WARNING"
        )
        
        results['alerts'] = success
        
        if success:
            print("✅ Alertas funcionando correctamente!")
        else:
            print("❌ Error enviando alertas")
            
    except Exception as e:
        print(f"❌ Error probando alertas: {e}")
        results['alerts'] = False
    
    return results

def create_test_config(bot_token: str, chat_id: str) -> bool:
    """Crea archivo de configuración para pruebas"""
    print("⚙️ Creando configuración para pruebas...")
    
    try:
        # Crear archivo .env para pruebas
        env_content = f"""# Bot Trading v10 Enterprise - Configuración de Telegram para Pruebas
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}

# Configuración optimizada para testing
TELEGRAM_RATE_LIMIT_DELAY=0.1
TELEGRAM_MAX_MESSAGE_LENGTH=4096
TELEGRAM_ENABLE_INDIVIDUAL_TRADES=true
TELEGRAM_ENABLE_CYCLE_SUMMARIES=true
TELEGRAM_ENABLE_ALERTS=true

# Configuración de testing
TEST_MODE=true
TEST_TELEGRAM_ENABLED=true
TEST_VERBOSE_LOGGING=true
"""
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Archivo .env creado para pruebas")
        
        # Crear archivo de configuración específico para pruebas
        test_config_content = f"""# Configuración específica para pruebas de Telegram
telegram:
  bot_token: "{bot_token}"
  chat_id: "{chat_id}"
  enabled: true
  rate_limit_delay: 0.1
  max_message_length: 4096
  enable_individual_trades: true
  enable_cycle_summaries: true
  enable_alerts: true

testing:
  telegram_test_mode: true
  verbose_logging: true
  test_message_prefix: "🧪 TEST: "
"""
        
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)
        
        with open('config/telegram_test_config.yaml', 'w', encoding='utf-8') as f:
            f.write(test_config_content)
        
        print("✅ Archivo de configuración de pruebas creado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando configuración: {e}")
        return False

def show_telegram_help():
    """Muestra ayuda para obtener credenciales de Telegram"""
    print("""
📚 CÓMO OBTENER CREDENCIALES DE TELEGRAM:

1. 🤖 CREAR BOT:
   - Abre Telegram y busca @BotFather
   - Envía /newbot
   - Sigue las instrucciones para crear tu bot
   - Copia el Bot Token que te proporciona

2. 💬 OBTENER CHAT ID:
   - Agrega tu bot al chat/grupo donde quieres recibir mensajes
   - Envía un mensaje al bot (cualquier mensaje)
   - Visita: https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   - Busca 'chat':{'id': -1001234567890} en la respuesta
   - El número es tu Chat ID

3. 🔧 CONFIGURAR PERMISOS:
   - Asegúrate de que el bot tenga permisos para enviar mensajes
   - Si es un grupo, promueve el bot a administrador
   - Si es un chat privado, inicia una conversación con el bot

4. 🧪 PROBAR CONFIGURACIÓN:
   - Ejecuta este script para probar la configuración
   - Verifica que recibas los mensajes de prueba
   - Revisa el formato de los mensajes

💡 CONSEJOS:
   - Usa un chat privado para pruebas iniciales
   - Mantén las credenciales seguras
   - No compartas el Bot Token públicamente
   - Usa diferentes bots para desarrollo y producción
    """)

async def main():
    """Función principal de configuración"""
    print_banner()
    
    print("📋 Opciones disponibles:")
    print("1. Configurar Telegram para pruebas")
    print("2. Probar configuración existente")
    print("3. Mostrar ayuda para obtener credenciales")
    print("4. Salir")
    
    choice = input("\n🔢 Selecciona una opción (1-4): ").strip()
    
    if choice == '1':
        print("\n🔧 Configurando Telegram para pruebas...")
        
        # Solicitar credenciales
        bot_token = input("🔑 Bot Token: ").strip()
        if not bot_token:
            print("❌ Bot Token es requerido")
            return 1
        
        chat_id = input("💬 Chat ID: ").strip()
        if not chat_id:
            print("❌ Chat ID es requerido")
            return 1
        
        # Crear configuración
        if create_test_config(bot_token, chat_id):
            print("✅ Configuración creada exitosamente!")
            
            # Probar configuración
            print("\n🧪 Probando configuración...")
            results = await run_comprehensive_test(bot_token, chat_id)
            
            # Mostrar resultados
            print(f"\n📊 RESULTADOS DE PRUEBA:")
            for test_name, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {status} {test_name}")
            
            if all(results.values()):
                print("\n🎉 ¡Configuración de Telegram exitosa!")
                print("✅ El sistema está listo para las pruebas")
                return 0
            else:
                print("\n⚠️ Algunas pruebas fallaron")
                print("❌ Revisa la configuración y vuelve a intentar")
                return 1
        else:
            print("❌ Error creando configuración")
            return 1
    
    elif choice == '2':
        print("\n🧪 Probando configuración existente...")
        
        # Cargar configuración desde .env
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ No se encontraron credenciales en .env")
            print("💡 Ejecuta la opción 1 para configurar Telegram")
            return 1
        
        # Probar configuración
        results = await run_comprehensive_test(bot_token, chat_id)
        
        # Mostrar resultados
        print(f"\n📊 RESULTADOS DE PRUEBA:")
        for test_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}")
        
        if all(results.values()):
            print("\n🎉 ¡Configuración de Telegram funcionando correctamente!")
            return 0
        else:
            print("\n⚠️ Algunas pruebas fallaron")
            print("❌ Revisa la configuración y vuelve a intentar")
            return 1
    
    elif choice == '3':
        show_telegram_help()
        return 0
    
    elif choice == '4':
        print("\n👋 ¡Hasta luego!")
        return 0
    
    else:
        print("\n❌ Opción inválida")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Configuración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
