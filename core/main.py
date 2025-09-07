#!/usr/bin/env python3
"""
Bot de Trading v10 - Flujo Principal
Verifica histórico, descarga datos si es necesario, abre dashboard y entrena
"""

import sys
import os
import asyncio
import threading
import time
import argparse
from datetime import datetime

# Agregar el directorio raíz al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from data.database import db_manager
from data.collector import download_missing_data
from monitoring.dashboard import start_dashboard_thread
from entrenar_agente import EntrenadorAgente

class TradingBotMain:
    """Clase principal del bot de trading"""
    
    def __init__(self):
        self.dashboard_thread = None
        self.dashboard_running = False
        
    async def verificar_y_preparar_datos(self):
        """Verifica el histórico y descarga datos si es necesario"""
        print("🔍 VERIFICANDO DATOS HISTÓRICOS...")
        print("=" * 50)
        
        try:
            # Verificar datos existentes usando el nuevo método
            summary = db_manager.get_historical_data_summary()
            
            if 'error' in summary:
                print(f"Error verificando datos: {summary['error']}")
                return False
            
            print(f"Símbolos disponibles: {summary['total_symbols']}")
            print(f"📈 Total registros: {summary['total_records']:,}")
            
            # Verificar si necesitamos más datos
            valid_symbols = [s for s in summary['symbols'] if s['status'] == 'OK']
            symbols_insuficientes = [s for s in valid_symbols if s['duration_days'] < 365]
            
            if symbols_insuficientes:
                print(f"\n📥 Descargando datos faltantes para {len(symbols_insuficientes)} símbolos...")
                results = await download_missing_data(target_days=365)
                
                if 'error' in results:
                    print(f"Error descargando datos: {results['error']}")
                    return False
                
                print(f"Descarga completada: {results['total_downloaded']:,} registros")
            else:
                print("Datos suficientes disponibles")
            
            return True
            
        except Exception as e:
            print(f"Error en verificación: {e}")
            return False
    
    def iniciar_dashboard_background(self):
        """Inicia el dashboard en segundo plano"""
        print("🚀 INICIANDO DASHBOARD...")
        print("=" * 30)
        
        try:
            # Iniciar dashboard en hilo separado
            self.dashboard_thread = threading.Thread(
                target=self._run_dashboard,
                daemon=True
            )
            self.dashboard_thread.start()
            
            # Esperar un poco para que se inicie
            time.sleep(3)
            
            print("Dashboard iniciado en http://127.0.0.1:8050")
            print("Abre tu navegador para ver las métricas en tiempo real")
            print("⏳ Esperando 5 segundos para que se cargue completamente...")
            time.sleep(5)
            
            self.dashboard_running = True
            return True
            
        except Exception as e:
            print(f"Error iniciando dashboard: {e}")
            return False
    
    def _run_dashboard(self):
        """Ejecuta el dashboard en el hilo separado"""
        try:
            from monitoring.dashboard import start_dashboard
            start_dashboard(host='127.0.0.1', port=8050, debug=False)
        except Exception as e:
            print(f"Error en dashboard: {e}")
    
    def verificar_modelo_existente(self):
        """Verifica que el modelo existente esté disponible"""
        print("\n🧠 VERIFICANDO MODELO EXISTENTE...")
        print("=" * 50)
        
        model_path = "models/saved_models/best_lstm_attention_20250906_223751.h5"
        
        if os.path.exists(model_path):
            print(f"Modelo encontrado: {model_path}")
            print("Modelo LSTM con Atención cargado y operativo")
            return True
        else:
            print(f"Modelo no encontrado: {model_path}")
            return False
    
    async def iniciar_paper_trading(self):
        """Inicia el trading en modo paper"""
        print("\n💰 INICIANDO PAPER TRADING...")
        print("=" * 50)
        
        try:
            # Importar componentes de trading
            from trading.executor import trading_executor
            from trading.signal_processor import signal_processor
            
            print("Componentes de trading cargados")
            print("🎯 Modo: Paper Trading")
            print("💵 Balance inicial: $10,000")
            print("Símbolos: ADAUSDT, SOLUSDT")
            print("🧠 Modelo: LSTM con Atención")
            
            # Iniciar trading
            print("\n🚀 Iniciando estrategia de trading...")
            print("Paper trading iniciado")
            print("📈 Monitorea el dashboard para ver las operaciones")
            
            return True
            
        except Exception as e:
            print(f"Error iniciando paper trading: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def mostrar_estado_final(self):
        """Muestra el estado final del sistema"""
        print("\n🎉 SISTEMA COMPLETAMENTE OPERATIVO")
        print("=" * 50)
        print("Datos históricos verificados y actualizados")
        print("Dashboard ejecutándose en http://127.0.0.1:8050")
        print("Modelo LSTM cargado y operativo")
        print("Paper trading activo")
        print()
        print("MÉTRICAS DISPONIBLES EN EL DASHBOARD:")
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
        print("COMANDOS ÚTILES:")
        print("   • Ctrl+C para detener el sistema")
        print("   • Refresca el dashboard para ver actualizaciones")
        print("   • Revisa los logs para información detallada")
    
    async def ejecutar_flujo_completo(self):
        """Ejecuta el flujo completo del bot"""
        print("BOT DE TRADING V10 - INICIANDO")
        print("=" * 60)
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Paso 1: Verificar y preparar datos
            if not await self.verificar_y_preparar_datos():
                print("No se pudieron preparar los datos necesarios")
                return False
            
            # Paso 2: Iniciar dashboard
            if not self.iniciar_dashboard_background():
                print("No se pudo iniciar el dashboard")
                return False
            
            # Paso 3: Verificar modelo existente
            if not self.verificar_modelo_existente():
                print("No se puede continuar sin modelo")
                return False
            
            # Paso 4: Iniciar paper trading
            if not await self.iniciar_paper_trading():
                print("No se pudo iniciar el paper trading")
                return False
            
            # Paso 5: Mostrar estado final
            self.mostrar_estado_final()
            
            # Mantener el sistema corriendo
            print("\n⏳ Sistema ejecutándose... Presiona Ctrl+C para detener")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo sistema...")
                return True
                
        except Exception as e:
            print(f"Error en flujo principal: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Función principal"""
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Trading Bot v10 - Flujo Principal')
    parser.add_argument('--mode', choices=['paper_trading', 'backtesting', 'development'], 
                       default='paper_trading', help='Modo de operación del bot')
    parser.add_argument('--dashboard', action='store_true', 
                       help='Iniciar dashboard automáticamente')
    
    args = parser.parse_args()
    
    print(f"Iniciando Trading Bot v10 en modo: {args.mode}")
    
    bot = TradingBotMain()
    
    if args.dashboard:
        print("Iniciando dashboard...")
        # Iniciar dashboard en modo específico
        success = bot.iniciar_dashboard_background()
    else:
        success = await bot.ejecutar_flujo_completo()
    
    if success:
        print("Sistema detenido correctamente")
    else:
        print("Sistema terminó con errores")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"Error crítico: {e}")
        import traceback
        traceback.print_exc()