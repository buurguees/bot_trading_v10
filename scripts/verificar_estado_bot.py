#!/usr/bin/env python3
"""
🔍 Verificador de Estado del Trading Bot v10
============================================

Script para verificar si el bot está:
- Tradeando en vivo o en modo paper trading
- En modo aprendizaje o ejecutando trades
- Configurado correctamente
- Funcionando correctamente

Uso: python verificar_estado_bot.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del bot
from config.config_loader import user_config
from trading.executor import trading_executor
from trading.position_manager import position_manager
from models.adaptive_trainer import adaptive_trainer
from agents.self_learning_system import SelfLearningSystem
from data.database import db_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_status.log')
    ]
)
logger = logging.getLogger(__name__)

class BotStatusChecker:
    """Verificador de estado del bot"""
    
    def __init__(self):
        self.status = {}
        self.config = user_config
    
    async def check_all_status(self) -> Dict[str, Any]:
        """Verifica el estado completo del bot"""
        print("🔍 VERIFICANDO ESTADO DEL TRADING BOT v10")
        print("=" * 50)
        
        # 1. Verificar configuración
        await self._check_configuration()
        
        # 2. Verificar modo de trading
        await self._check_trading_mode()
        
        # 3. Verificar estado de componentes
        await self._check_components_status()
        
        # 4. Verificar base de datos
        await self._check_database_status()
        
        # 5. Verificar sistema de aprendizaje
        await self._check_learning_system()
        
        # 6. Verificar trades recientes
        await self._check_recent_activity()
        
        # 7. Generar resumen
        self._generate_summary()
        
        return self.status
    
    async def _check_configuration(self):
        """Verifica la configuración del bot"""
        print("\n📋 1. CONFIGURACIÓN DEL BOT")
        print("-" * 30)
        
        try:
            # Modo de trading
            trading_mode = self.config.get_value(['trading', 'mode'], 'unknown')
            print(f"   Modo de Trading: {trading_mode}")
            
            # Símbolo principal
            primary_symbol = self.config.get_value(['trading_settings', 'primary_symbol'], 'unknown')
            print(f"   Símbolo Principal: {primary_symbol}")
            
            # Confianza mínima
            min_confidence = self.config.get_value(['trading', 'min_confidence'], 0.0)
            print(f"   Confianza Mínima: {min_confidence*100:.1f}%")
            
            # Balance inicial
            initial_balance = self.config.get_value(['trading', 'initial_balance'], 0.0)
            print(f"   Balance Inicial: ${initial_balance:,.2f}")
            
            # Auto trading
            auto_trading = self.config.get_value(['bot_settings', 'features', 'auto_trading'], False)
            print(f"   Auto Trading: {'✅ Activado' if auto_trading else '❌ Desactivado'}")
            
            # Auto retraining
            auto_retraining = self.config.get_value(['bot_settings', 'features', 'auto_retraining'], False)
            print(f"   Auto Retraining: {'✅ Activado' if auto_retraining else '❌ Desactivado'}")
            
            self.status['configuration'] = {
                'trading_mode': trading_mode,
                'primary_symbol': primary_symbol,
                'min_confidence': min_confidence,
                'initial_balance': initial_balance,
                'auto_trading': auto_trading,
                'auto_retraining': auto_retraining
            }
            
        except Exception as e:
            print(f"   ❌ Error verificando configuración: {e}")
            self.status['configuration'] = {'error': str(e)}
    
    async def _check_trading_mode(self):
        """Verifica el modo de trading actual"""
        print("\n🎯 2. MODO DE TRADING")
        print("-" * 30)
        
        try:
            trading_mode = self.config.get_value(['trading', 'mode'], 'unknown')
            
            if trading_mode == 'live_trading':
                print("   🚨 MODO LIVE TRADING - DINERO REAL")
                print("   ⚠️  El bot está operando con dinero real")
                print("   💰 Cada trade afecta tu balance real")
                
            elif trading_mode == 'paper_trading':
                print("   📄 MODO PAPER TRADING - SIMULACIÓN")
                print("   ✅ El bot está en modo simulación")
                print("   🎮 No hay riesgo de dinero real")
                
            elif trading_mode == 'backtesting':
                print("   📊 MODO BACKTESTING - PRUEBAS HISTÓRICAS")
                print("   🔍 El bot está probando con datos históricos")
                print("   📈 No ejecuta trades reales")
                
            elif trading_mode == 'development':
                print("   🛠️  MODO DESARROLLO - CONFIGURACIÓN")
                print("   ⚙️  El bot está en modo configuración")
                print("   🚫 No ejecuta trades")
                
            else:
                print(f"   ❓ MODO DESCONOCIDO: {trading_mode}")
            
            # Verificar si está en modo aprendizaje
            auto_retraining = self.config.get_value(['bot_settings', 'features', 'auto_retraining'], False)
            if auto_retraining:
                print("   🧠 MODO APRENDIZAJE ACTIVO")
                print("   📚 El bot está aprendiendo de cada trade")
            else:
                print("   🎯 MODO EJECUCIÓN PURA")
                print("   ⚡ El bot solo ejecuta trades, no aprende")
            
            self.status['trading_mode'] = {
                'mode': trading_mode,
                'is_live': trading_mode == 'live_trading',
                'is_learning': auto_retraining,
                'is_safe': trading_mode in ['paper_trading', 'backtesting', 'development']
            }
            
        except Exception as e:
            print(f"   ❌ Error verificando modo de trading: {e}")
            self.status['trading_mode'] = {'error': str(e)}
    
    async def _check_components_status(self):
        """Verifica el estado de los componentes principales"""
        print("\n🔧 3. ESTADO DE COMPONENTES")
        print("-" * 30)
        
        components = {}
        
        try:
            # Trading Executor
            try:
                executor_health = await trading_executor.health_check()
                components['trading_executor'] = executor_health.get('status', 'unknown')
                print(f"   Trading Executor: {'✅' if executor_health.get('status') == 'healthy' else '❌'} {executor_health.get('status', 'unknown')}")
            except Exception as e:
                components['trading_executor'] = 'error'
                print(f"   Trading Executor: ❌ Error - {e}")
            
            # Position Manager
            try:
                position_health = await position_manager.health_check()
                components['position_manager'] = position_health.get('status', 'unknown')
                print(f"   Position Manager: {'✅' if position_health.get('status') == 'healthy' else '❌'} {position_health.get('status', 'unknown')}")
            except Exception as e:
                components['position_manager'] = 'error'
                print(f"   Position Manager: ❌ Error - {e}")
            
            # Adaptive Trainer
            try:
                trainer_health = await adaptive_trainer.health_check()
                components['adaptive_trainer'] = trainer_health.get('status', 'unknown')
                print(f"   Adaptive Trainer: {'✅' if trainer_health.get('status') == 'healthy' else '❌'} {trainer_health.get('status', 'unknown')}")
            except Exception as e:
                components['adaptive_trainer'] = 'error'
                print(f"   Adaptive Trainer: ❌ Error - {e}")
            
            self.status['components'] = components
            
        except Exception as e:
            print(f"   ❌ Error verificando componentes: {e}")
            self.status['components'] = {'error': str(e)}
    
    async def _check_database_status(self):
        """Verifica el estado de la base de datos"""
        print("\n🗄️  4. ESTADO DE BASE DE DATOS")
        print("-" * 30)
        
        try:
            # Estadísticas de la base de datos
            db_stats = db_manager.get_database_stats()
            
            print(f"   Archivo BD: {db_manager.db_path}")
            print(f"   Tamaño: {db_stats.get('file_size_mb', 0):.2f} MB")
            print(f"   Datos de mercado: {db_stats.get('market_data_count', 0):,} registros")
            print(f"   Trades: {db_stats.get('trades_count', 0):,} registros")
            print(f"   Métricas modelo: {db_stats.get('model_metrics_count', 0):,} registros")
            
            # Verificar datos recientes
            latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
            if not latest_data.empty:
                last_update = latest_data.index[-1]
                hours_ago = (datetime.now() - last_update.tz_localize(None)).total_seconds() / 3600
                print(f"   Última actualización: {hours_ago:.1f} horas atrás")
                
                if hours_ago < 1:
                    print("   ✅ Datos actualizados (menos de 1 hora)")
                elif hours_ago < 24:
                    print("   ⚠️  Datos algo antiguos (menos de 24 horas)")
                else:
                    print("   ❌ Datos muy antiguos (más de 24 horas)")
            else:
                print("   ❌ No hay datos de mercado disponibles")
            
            self.status['database'] = {
                'file_size_mb': db_stats.get('file_size_mb', 0),
                'market_data_count': db_stats.get('market_data_count', 0),
                'trades_count': db_stats.get('trades_count', 0),
                'last_update_hours': hours_ago if not latest_data.empty else None
            }
            
        except Exception as e:
            print(f"   ❌ Error verificando base de datos: {e}")
            self.status['database'] = {'error': str(e)}
    
    async def _check_learning_system(self):
        """Verifica el estado del sistema de aprendizaje"""
        print("\n🧠 5. SISTEMA DE APRENDIZAJE")
        print("-" * 30)
        
        try:
            # Verificar si el sistema de aprendizaje está activo
            auto_retraining = self.config.get_value(['bot_settings', 'features', 'auto_retraining'], False)
            
            if auto_retraining:
                print("   ✅ Sistema de aprendizaje ACTIVO")
                print("   📚 El bot aprende de cada trade")
                
                # Obtener estadísticas de aprendizaje
                try:
                    learning_stats = adaptive_trainer.get_learning_statistics()
                    print(f"   Episodios totales: {learning_stats.get('learning_metrics', {}).get('total_episodes', 0)}")
                    print(f"   Patrones identificados: {learning_stats.get('patterns_count', 0)}")
                    print(f"   Adaptaciones aplicadas: {learning_stats.get('adaptations_count', 0)}")
                except Exception as e:
                    print(f"   ⚠️  No se pudieron obtener estadísticas: {e}")
            else:
                print("   ❌ Sistema de aprendizaje DESACTIVADO")
                print("   🎯 El bot solo ejecuta trades, no aprende")
            
            self.status['learning_system'] = {
                'active': auto_retraining,
                'learning_stats': learning_stats if auto_retraining else None
            }
            
        except Exception as e:
            print(f"   ❌ Error verificando sistema de aprendizaje: {e}")
            self.status['learning_system'] = {'error': str(e)}
    
    async def _check_recent_activity(self):
        """Verifica la actividad reciente del bot"""
        print("\n📊 6. ACTIVIDAD RECIENTE")
        print("-" * 30)
        
        try:
            # Trades recientes
            recent_trades = db_manager.get_trades(limit=10)
            
            if not recent_trades.empty:
                print(f"   Trades recientes: {len(recent_trades)} en total")
                
                # Trades de las últimas 24 horas
                from datetime import datetime, timedelta
                yesterday = datetime.now() - timedelta(days=1)
                recent_trades_24h = recent_trades[recent_trades['entry_time'] >= yesterday]
                
                print(f"   Trades últimas 24h: {len(recent_trades_24h)}")
                
                if len(recent_trades_24h) > 0:
                    # Trades abiertos
                    open_trades = recent_trades_24h[recent_trades_24h['status'] == 'open']
                    print(f"   Trades abiertos: {len(open_trades)}")
                    
                    # Trades cerrados
                    closed_trades = recent_trades_24h[recent_trades_24h['status'] == 'closed']
                    print(f"   Trades cerrados: {len(closed_trades)}")
                    
                    if len(closed_trades) > 0:
                        # Performance de trades cerrados
                        total_pnl = closed_trades['pnl'].sum()
                        winning_trades = len(closed_trades[closed_trades['pnl'] > 0])
                        win_rate = (winning_trades / len(closed_trades)) * 100
                        
                        print(f"   PnL total 24h: ${total_pnl:.2f}")
                        print(f"   Win rate 24h: {win_rate:.1f}%")
                        
                        if total_pnl > 0:
                            print("   📈 Performance positiva en 24h")
                        else:
                            print("   📉 Performance negativa en 24h")
                else:
                    print("   ⏸️  No hay trades en las últimas 24 horas")
            else:
                print("   📭 No hay trades registrados")
            
            self.status['recent_activity'] = {
                'total_trades': len(recent_trades),
                'trades_24h': len(recent_trades_24h) if not recent_trades.empty else 0,
                'open_trades': len(open_trades) if not recent_trades.empty else 0,
                'closed_trades': len(closed_trades) if not recent_trades.empty else 0,
                'total_pnl_24h': total_pnl if not recent_trades.empty and len(closed_trades) > 0 else 0,
                'win_rate_24h': win_rate if not recent_trades.empty and len(closed_trades) > 0 else 0
            }
            
        except Exception as e:
            print(f"   ❌ Error verificando actividad reciente: {e}")
            self.status['recent_activity'] = {'error': str(e)}
    
    def _generate_summary(self):
        """Genera un resumen del estado del bot"""
        print("\n📋 RESUMEN DEL ESTADO")
        print("=" * 50)
        
        try:
            # Estado general
            trading_mode = self.status.get('trading_mode', {}).get('mode', 'unknown')
            is_live = self.status.get('trading_mode', {}).get('is_live', False)
            is_learning = self.status.get('trading_mode', {}).get('is_learning', False)
            
            print(f"🎯 Modo de Trading: {trading_mode}")
            
            if is_live:
                print("🚨 ESTADO: LIVE TRADING - DINERO REAL")
                print("⚠️  ADVERTENCIA: El bot está operando con dinero real")
            else:
                print("✅ ESTADO: MODO SEGURO - Sin riesgo de dinero real")
            
            if is_learning:
                print("🧠 APRENDIZAJE: ACTIVO - El bot está aprendiendo")
            else:
                print("🎯 APRENDIZAJE: INACTIVO - Solo ejecuta trades")
            
            # Recomendaciones
            print("\n💡 RECOMENDACIONES:")
            
            if is_live:
                print("   ⚠️  Si es tu primera vez, cambia a 'paper_trading'")
                print("   📊 Monitorea el bot constantemente")
                print("   💰 Establece límites de pérdida estrictos")
            else:
                print("   ✅ Modo seguro activado")
                print("   🎮 Puedes experimentar sin riesgo")
                print("   📈 Cuando estés listo, cambia a 'live_trading'")
            
            if not is_learning:
                print("   🧠 Considera activar 'auto_retraining' para que aprenda")
            
            # Estado de componentes
            components = self.status.get('components', {})
            healthy_components = sum(1 for comp in components.values() if comp == 'healthy')
            total_components = len(components)
            
            print(f"\n🔧 Componentes: {healthy_components}/{total_components} funcionando correctamente")
            
            if healthy_components == total_components:
                print("   ✅ Todos los componentes funcionan correctamente")
            else:
                print("   ⚠️  Algunos componentes tienen problemas")
            
        except Exception as e:
            print(f"❌ Error generando resumen: {e}")

async def main():
    """Función principal"""
    checker = BotStatusChecker()
    await checker.check_all_status()
    
    print("\n" + "=" * 50)
    print("✅ Verificación completada")
    print("📝 Log guardado en: bot_status.log")

if __name__ == "__main__":
    asyncio.run(main())
