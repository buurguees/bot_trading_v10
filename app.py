#!/usr/bin/env python3
"""
app.py - Punto de Entrada Único - Trading Bot v10
================================================

Aplicación principal que consolida todas las funcionalidades del bot de trading.
Punto de entrada único para todas las operaciones.

Uso:
    python app.py --mode verify          # Verificar datos históricos
    python app.py --mode download        # Descargar datos faltantes
    python app.py --mode train           # Entrenar modelo
    python app.py --mode paper-trading   # Modo paper trading
    python app.py --mode dashboard       # Solo dashboard
    python app.py --mode full            # Flujo completo (default)
"""

import sys
import os
import asyncio
import argparse
import threading
import time
from datetime import datetime
import logging

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBotApp:
    """Aplicación principal del Trading Bot v10"""
    
    def __init__(self):
        self.dashboard_thread = None
        self.dashboard_running = False
        
    def print_banner(self):
        """Muestra el banner de la aplicación"""
        print("🤖" + "=" * 60)
        print("🤖 TRADING BOT v10 - APLICACIÓN PRINCIPAL")
        print("🤖" + "=" * 60)
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    async def verify_data(self):
        """Verifica el estado de los datos históricos"""
        print("🔍 VERIFICANDO DATOS HISTÓRICOS")
        print("=" * 40)
        
        try:
            from data.database import db_manager
            
            summary = db_manager.get_historical_data_summary()
            
            if 'error' in summary:
                print(f"❌ Error: {summary['error']}")
                return False
            
            print(f"📊 Símbolos disponibles: {summary['total_symbols']}")
            print(f"📈 Total registros: {summary['total_records']:,}")
            print()
            
            for symbol_info in summary['symbols']:
                symbol = symbol_info['symbol']
                count = symbol_info['count']
                status = symbol_info['status']
                
                if status == 'OK':
                    start_date = symbol_info['start_date']
                    end_date = symbol_info['end_date']
                    duration = symbol_info['duration_days']
                    
                    print(f"📈 {symbol}:")
                    print(f"   📊 Registros: {count:,}")
                    print(f"   📅 Desde: {start_date}")
                    print(f"   📅 Hasta: {end_date}")
                    print(f"   ⏱️  Duración: {duration} días")
                else:
                    print(f"❌ {symbol}: {status}")
                print()
            
            print("💡 RECOMENDACIONES:")
            for rec in summary['recommendations']:
                print(f"   {rec}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
            return False
    
    async def download_data(self, years: int = 2):
        """Descarga datos históricos faltantes"""
        print(f"📥 DESCARGANDO DATOS HISTÓRICOS ({years} años)")
        print("=" * 45)
        
        try:
            from data.collector import download_missing_data
            
            results = await download_missing_data(target_days=years * 365)
            
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
                return False
            
            print(f"📊 Símbolos verificados: {results['symbols_checked']}")
            print(f"✅ Símbolos OK: {results['symbols_ok']}")
            print(f"🔄 Símbolos actualizados: {results['symbols_updated']}")
            print(f"📈 Total descargado: {results['total_downloaded']:,} registros")
            print()
            
            for symbol, details in results['details'].items():
                status = details['status']
                if status == 'OK':
                    print(f"✅ {symbol}: {details['message']}")
                elif status == 'UPDATED':
                    print(f"🔄 {symbol}: {details['downloaded']} registros descargados")
                elif status == 'NEW':
                    print(f"🆕 {symbol}: {details['downloaded']} registros descargados")
                else:
                    print(f"❌ {symbol}: {details.get('error', 'Error desconocido')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en descarga: {e}")
            return False
    
    def start_dashboard(self, background: bool = False):
        """Inicia el dashboard"""
        print("🚀 INICIANDO DASHBOARD")
        print("=" * 25)
        
        try:
            if background:
                # Iniciar en hilo separado
                self.dashboard_thread = threading.Thread(
                    target=self._run_dashboard,
                    daemon=True
                )
                self.dashboard_thread.start()
                time.sleep(3)
                print("✅ Dashboard iniciado en http://127.0.0.1:8050")
                self.dashboard_running = True
                return True
            else:
                # Iniciar en primer plano
                from monitoring.dashboard import start_dashboard
                start_dashboard(host='127.0.0.1', port=8050, debug=False)
                return True
                
        except Exception as e:
            print(f"❌ Error iniciando dashboard: {e}")
            return False
    
    def _run_dashboard(self):
        """Ejecuta el dashboard en hilo separado"""
        try:
            from monitoring.dashboard import start_dashboard
            start_dashboard(host='127.0.0.1', port=8050, debug=False)
        except Exception as e:
            print(f"❌ Error en dashboard: {e}")
    
    async def train_model(self):
        """Entrena el modelo de IA"""
        print("🧠 ENTRENANDO MODELO DE IA")
        print("=" * 30)
        
        try:
            from core.entrenar_agente import EntrenadorAgente
            
            entrenador = EntrenadorAgente()
            success = await entrenador.ejecutar_entrenamiento_completo()
            
            if success:
                print("✅ Entrenamiento completado exitosamente")
                return True
            else:
                print("❌ Error en el entrenamiento")
                return False
                
        except Exception as e:
            print(f"❌ Error entrenando modelo: {e}")
            return False
    
    async def paper_trading(self):
        """Inicia el trading en modo paper"""
        print("💰 INICIANDO PAPER TRADING")
        print("=" * 30)
        
        try:
            from core.main_paper_trading import PaperTradingBot
            
            bot = PaperTradingBot()
            success = await bot.ejecutar_paper_trading()
            
            if success:
                print("✅ Paper trading iniciado exitosamente")
                return True
            else:
                print("❌ Error iniciando paper trading")
                return False
                
        except Exception as e:
            print(f"❌ Error en paper trading: {e}")
            return False
    
    async def full_flow(self):
        """Ejecuta el flujo completo del bot"""
        print("🚀 FLUJO COMPLETO DEL BOT")
        print("=" * 30)
        
        try:
            # Paso 1: Verificar datos
            if not await self.verify_data():
                print("❌ Error verificando datos")
                return False
            
            # Paso 2: Descargar datos si es necesario
            print("\n📥 Verificando si necesitamos más datos...")
            if not await self.download_data():
                print("❌ Error descargando datos")
                return False
            
            # Paso 3: Iniciar dashboard en segundo plano
            if not self.start_dashboard(background=True):
                print("❌ Error iniciando dashboard")
                return False
            
            # Paso 4: Verificar modelo existente
            print("\n🧠 Verificando modelo existente...")
            model_path = "models/saved_models/best_lstm_attention_20250906_223751.h5"
            if not os.path.exists(model_path):
                print("❌ Modelo no encontrado, iniciando entrenamiento...")
                if not await self.train_model():
                    print("❌ Error entrenando modelo")
                    return False
            
            # Paso 5: Iniciar paper trading
            print("\n💰 Iniciando paper trading...")
            if not await self.paper_trading():
                print("❌ Error iniciando paper trading")
                return False
            
            # Mostrar estado final
            self.show_final_status()
            
            # Mantener el sistema corriendo
            print("\n⏳ Sistema ejecutándose... Presiona Ctrl+C para detener")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo sistema...")
                return True
                
        except Exception as e:
            print(f"❌ Error en flujo completo: {e}")
            return False
    
    def show_final_status(self):
        """Muestra el estado final del sistema"""
        print("\n🎉 SISTEMA COMPLETAMENTE OPERATIVO")
        print("=" * 50)
        print("✅ Datos históricos verificados y actualizados")
        print("✅ Dashboard ejecutándose en http://127.0.0.1:8050")
        print("✅ Modelo LSTM cargado y operativo")
        print("✅ Paper trading activo")
        print()
        print("📊 MÉTRICAS DISPONIBLES EN EL DASHBOARD:")
        print("   • Rendimiento del modelo")
        print("   • Gráficos de precios en tiempo real")
        print("   • Señales de trading")
        print("   • Estadísticas de backtesting")
        print("   • Métricas de riesgo")
        print()
        print("🚀 PRÓXIMOS PASOS:")
        print("   1. Revisa las métricas en el dashboard")
        print("   2. Ajusta parámetros si es necesario")
        print("   3. Monitorea las operaciones en el dashboard")
        print("   4. Monitorea el rendimiento en tiempo real")
        print()
        print("💡 COMANDOS ÚTILES:")
        print("   • Ctrl+C para detener el sistema")
        print("   • Refresca el dashboard para ver actualizaciones")
        print("   • Revisa los logs para información detallada")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Trading Bot v10 - Aplicación Principal')
    parser.add_argument('--mode', 
                       choices=['verify', 'download', 'train', 'paper-trading', 'dashboard', 'full'],
                       default='full',
                       help='Modo de operación (default: full)')
    parser.add_argument('--years', type=int, default=2, help='Años de datos a descargar')
    parser.add_argument('--background', action='store_true', help='Ejecutar dashboard en segundo plano')
    
    args = parser.parse_args()
    
    app = TradingBotApp()
    app.print_banner()
    
    try:
        if args.mode == 'verify':
            success = asyncio.run(app.verify_data())
        elif args.mode == 'download':
            success = asyncio.run(app.download_data(args.years))
        elif args.mode == 'train':
            success = asyncio.run(app.train_model())
        elif args.mode == 'paper-trading':
            success = asyncio.run(app.paper_trading())
        elif args.mode == 'dashboard':
            success = app.start_dashboard(background=args.background)
        elif args.mode == 'full':
            success = asyncio.run(app.full_flow())
        else:
            print(f"❌ Modo no reconocido: {args.mode}")
            success = False
        
        if success:
            print("\n✅ Operación completada exitosamente")
        else:
            print("\n❌ Operación terminó con errores")
            
    except KeyboardInterrupt:
        print("\n⏹️ Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
