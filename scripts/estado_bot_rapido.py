#!/usr/bin/env python3
"""
⚡ Verificación Rápida del Estado del Bot
========================================

Script simple para verificar rápidamente:
- Si está tradeando en vivo o paper trading
- Si está en modo aprendizaje
- Estado básico del sistema

Uso: python estado_bot_rapido.py
"""

import sys
import os
from datetime import datetime

# Añadir el directorio del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

try:
    from config.config_loader import user_config
    from data.database import db_manager
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de estar en el directorio correcto del proyecto")
    sys.exit(1)

def verificar_estado_rapido():
    """Verificación rápida del estado del bot"""
    print("⚡ VERIFICACIÓN RÁPIDA DEL BOT")
    print("=" * 40)
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. Modo de Trading
        print("🎯 MODO DE TRADING:")
        trading_mode = user_config.get_value(['trading', 'mode'], 'unknown')
        
        if trading_mode == 'live_trading':
            print("   🚨 LIVE TRADING - DINERO REAL")
            print("   ⚠️  El bot está operando con dinero real")
        elif trading_mode == 'paper_trading':
            print("   📄 PAPER TRADING - SIMULACIÓN")
            print("   ✅ Modo seguro, sin riesgo de dinero real")
        elif trading_mode == 'backtesting':
            print("   📊 BACKTESTING - PRUEBAS HISTÓRICAS")
            print("   🔍 Probando con datos históricos")
        elif trading_mode == 'development':
            print("   🛠️  DESARROLLO - CONFIGURACIÓN")
            print("   ⚙️  Modo configuración")
        else:
            print(f"   ❓ MODO DESCONOCIDO: {trading_mode}")
        
        print()
        
        # 2. Sistema de Aprendizaje
        print("🧠 SISTEMA DE APRENDIZAJE:")
        auto_retraining = user_config.get_value(['bot_settings', 'features', 'auto_retraining'], False)
        auto_trading = user_config.get_value(['bot_settings', 'features', 'auto_trading'], False)
        
        if auto_retraining:
            print("   ✅ APRENDIZAJE ACTIVO")
            print("   📚 El bot aprende de cada trade")
        else:
            print("   ❌ APRENDIZAJE INACTIVO")
            print("   🎯 Solo ejecuta trades, no aprende")
        
        if auto_trading:
            print("   ✅ AUTO TRADING ACTIVO")
            print("   🤖 El bot ejecuta trades automáticamente")
        else:
            print("   ❌ AUTO TRADING INACTIVO")
            print("   ⏸️  El bot no ejecuta trades automáticamente")
        
        print()
        
        # 3. Configuración Básica
        print("⚙️  CONFIGURACIÓN:")
        primary_symbol = user_config.get_value(['trading_settings', 'primary_symbol'], 'unknown')
        min_confidence = user_config.get_value(['trading', 'min_confidence'], 0.0)
        initial_balance = user_config.get_value(['trading', 'initial_balance'], 0.0)
        
        print(f"   Símbolo: {primary_symbol}")
        print(f"   Confianza mínima: {min_confidence*100:.1f}%")
        print(f"   Balance inicial: ${initial_balance:,.2f}")
        
        print()
        
        # 4. Actividad Reciente
        print("📊 ACTIVIDAD RECIENTE:")
        try:
            # Trades recientes
            recent_trades = db_manager.get_trades(limit=5)
            
            if not recent_trades.empty:
                print(f"   Trades totales: {len(recent_trades)}")
                
                # Último trade
                last_trade = recent_trades.iloc[0]
                last_time = last_trade['entry_time']
                print(f"   Último trade: {last_time}")
                print(f"   Símbolo: {last_trade['symbol']}")
                print(f"   Acción: {last_trade['side'].upper()}")
                print(f"   Precio: ${last_trade['entry_price']:,.2f}")
                print(f"   Estado: {last_trade['status']}")
                
                if last_trade['status'] == 'closed':
                    pnl = last_trade.get('pnl', 0)
                    if pnl > 0:
                        print(f"   PnL: +${pnl:.2f} ✅")
                    else:
                        print(f"   PnL: ${pnl:.2f} ❌")
            else:
                print("   📭 No hay trades registrados")
                
        except Exception as e:
            print(f"   ❌ Error obteniendo trades: {e}")
        
        print()
        
        # 5. Resumen y Recomendaciones
        print("💡 RESUMEN:")
        
        if trading_mode == 'live_trading':
            print("   🚨 ATENCIÓN: Modo LIVE TRADING activo")
            print("   💰 Cada trade afecta tu dinero real")
            print("   📊 Monitorea constantemente el bot")
        else:
            print("   ✅ Modo seguro activado")
            print("   🎮 Puedes experimentar sin riesgo")
        
        if auto_retraining:
            print("   🧠 El bot está aprendiendo y mejorando")
        else:
            print("   🎯 El bot solo ejecuta trades")
            print("   💡 Considera activar el aprendizaje")
        
        if auto_trading:
            print("   🤖 El bot opera automáticamente")
        else:
            print("   ⏸️  El bot no opera automáticamente")
            print("   💡 Activa auto_trading para operación automática")
        
        print()
        print("=" * 40)
        print("✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error en la verificación: {e}")
        print("Revisa la configuración del bot")

if __name__ == "__main__":
    verificar_estado_rapido()
