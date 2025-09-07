#!/usr/bin/env python3
"""
app.py - Punto de Entrada Principal del Trading Bot v10
======================================================

SISTEMA DE MENÚ INTERACTIVO COMPLETO

Uso: python app.py

Funcionalidades:
1. Descargar históricos completos (2+ años)
2. Validar estado del agente IA
3. Validar histórico de símbolos
4. Empezar entrenamiento + dashboard
5. Análisis de performance
6. Configuración del sistema

"""

import asyncio
import os
import sys
import logging
from datetime import datetime
import subprocess
import threading
import time
import webbrowser

# Añadir directorio del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBotApp:
    """Aplicación principal del Trading Bot v10 con menú interactivo"""
    
    def __init__(self):
        self.running = True
        self.dashboard_process = None
        
    def show_banner(self):
        """Muestra banner de bienvenida"""
        print("\n" + "="*70)
        print("     🤖 TRADING BOT v10 - SISTEMA AUTÓNOMO DE TRADING 🤖")
        print("="*70)
        print(f"     Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     Entorno: Python {sys.version_info.major}.{sys.version_info.minor}")
        print(f"     Directorio: {project_root}")
        print("="*70)
        print()
    
    def show_main_menu(self):
        """Muestra el menú principal"""
        print("📋 MENÚ PRINCIPAL")
        print("-" * 20)
        print("1. 📥 Descargar datos históricos (2 años)")
        print("2. 🔍 Validar estado del agente IA")
        print("3. 📊 Validar histórico de símbolos")
        print("4. 🚀 Empezar entrenamiento + Dashboard")
        print("5. 📈 Análisis de performance")
        print("6. ⚙️  Configurar sistema")
        print("7. 🧪 Modo de pruebas rápidas")
        print("8. 📱 Estado del sistema")
        print("9. ❌ Salir")
        print()
    
    def get_user_choice(self) -> str:
        """Obtiene la elección del usuario"""
        try:
            choice = input("Selecciona una opción (1-9): ").strip()
            return choice
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            return "9"
        except Exception:
            return ""
    
    async def download_historical_data(self):
        """Opción 1: Descargar datos históricos completos"""
        print("\n📥 DESCARGA DE DATOS HISTÓRICOS")
        print("=" * 40)
        
        # Preguntar años de datos
        while True:
            try:
                years_input = input("¿Cuántos años de datos quieres descargar? (1-5): ").strip()
                years = int(years_input)
                if 1 <= years <= 5:
                    break
                else:
                    print("⚠️ Por favor ingresa un número entre 1 y 5")
            except ValueError:
                print("⚠️ Por favor ingresa un número válido")
        
        print(f"\n🚀 Descargando {years} años de datos históricos...")
        print("⏳ Esto puede tomar varios minutos...")
        print()
        
        try:
            # Importar después de configurar el entorno
            from core.manage_data import DataManager
            
            manager = DataManager()
            await manager.download_data(years=years)
            
            print(f"\n✅ Descarga de {years} años completada exitosamente")
            
        except Exception as e:
            print(f"\n❌ Error durante la descarga: {e}")
            logger.error(f"Error en descarga: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def validate_ai_agent(self):
        """Opción 2: Validar estado del agente IA"""
        print("\n🔍 VALIDACIÓN DEL AGENTE IA")
        print("=" * 35)
        
        try:
            # Verificar componentes del agente IA
            print("Verificando componentes del agente...")
            
            # Verificar modelos
            from models.adaptive_trainer import adaptive_trainer
            from models.prediction_engine import prediction_engine
            from models.confidence_estimator import confidence_estimator
            
            print("✅ adaptive_trainer: Disponible")
            print("✅ prediction_engine: Disponible") 
            print("✅ confidence_estimator: Disponible")
            
            # Verificar estado de entrenamiento
            training_status = await adaptive_trainer.get_training_status()
            print(f"\n📊 Estado del entrenamiento:")
            print(f"   Modelo entrenado: {'✅ Sí' if training_status.get('is_trained', False) else '❌ No'}")
            print(f"   Última actualización: {training_status.get('last_update', 'Nunca')}")
            print(f"   Precisión actual: {training_status.get('accuracy', 0):.1%}")
            
            # Verificar predicciones
            try:
                health = await prediction_engine.health_check()
                print(f"\n🧠 Motor de predicciones:")
                print(f"   Estado: {'✅ Saludable' if health.get('status') == 'healthy' else '❌ Problemas'}")
                print(f"   Último procesamiento: {health.get('last_prediction', 'Nunca')}")
            except Exception as e:
                print(f"⚠️ Error verificando predicciones: {e}")
            
            # Verificar confianza
            try:
                conf_health = await confidence_estimator.health_check()
                print(f"\n💪 Estimador de confianza:")
                print(f"   Calibrado: {'✅ Sí' if conf_health.get('calibrated', False) else '❌ No'}")
                print(f"   Última calibración: {conf_health.get('last_calibration', 'Nunca')}")
            except Exception as e:
                print(f"⚠️ Error verificando confianza: {e}")
            
        except ImportError as e:
            print(f"❌ Error importando módulos del agente: {e}")
        except Exception as e:
            print(f"❌ Error validando agente: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def validate_symbols_history(self):
        """Opción 3: Validar histórico de símbolos"""
        print("\n📊 VALIDACIÓN DE HISTÓRICO DE SÍMBOLOS")
        print("=" * 45)
        
        try:
            from core.manage_data import DataManager
            
            manager = DataManager()
            manager.verify_historical_data()
            
            # Mostrar detalles adicionales
            from data.database import db_manager
            
            print("\n🔍 ANÁLISIS DETALLADO:")
            
            # Verificar cada símbolo
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            
            for symbol in symbols:
                try:
                    count = db_manager.get_market_data_count(symbol)
                    date_range = db_manager.get_data_date_range(symbol)
                    
                    print(f"\n📈 {symbol}:")
                    print(f"   Registros: {count:,}")
                    
                    if date_range[0] and date_range[1]:
                        duration = (date_range[1] - date_range[0]).days
                        print(f"   Desde: {date_range[0].strftime('%Y-%m-%d')}")
                        print(f"   Hasta: {date_range[1].strftime('%Y-%m-%d')}")
                        print(f"   Duración: {duration} días")
                        
                        # Evaluación
                        if duration >= 730:  # 2 años
                            print("   Estado: ✅ Excelente (2+ años)")
                        elif duration >= 365:  # 1 año
                            print("   Estado: ✅ Bueno (1+ año)")
                        elif duration >= 180:  # 6 meses
                            print("   Estado: ⚠️ Suficiente (6+ meses)")
                        else:
                            print("   Estado: ❌ Insuficiente (<6 meses)")
                    else:
                        print("   Estado: ❌ Sin datos")
                        
                except Exception as e:
                    print(f"   Error: {e}")
            
        except Exception as e:
            print(f"❌ Error validando históricos: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_training_and_dashboard(self):
        """Opción 4: Empezar entrenamiento + Dashboard"""
        print("\n🚀 INICIANDO ENTRENAMIENTO + DASHBOARD")
        print("=" * 45)
        
        try:
            # Verificar prerequisitos
            print("🔍 Verificando prerequisitos...")
            
            # Verificar datos
            from data.database import db_manager
            stats = db_manager.get_database_stats()
            total_records = stats.get('total_records', 0)
            
            if total_records < 1000:
                print(f"⚠️ Datos insuficientes: {total_records:,} registros")
                download = input("¿Descargar datos históricos primero? (s/n): ").strip().lower()
                if download == 's':
                    await self.download_historical_data()
                else:
                    print("❌ Cancelando entrenamiento")
                    return
            else:
                print(f"✅ Datos suficientes: {total_records:,} registros")
            
            # Configurar modo
            mode = self._select_training_mode()
            
            print(f"\n🎯 Iniciando en modo: {mode}")
            print("⏳ Esto abrirá el dashboard en tu navegador...")
            print()
            
            # Iniciar dashboard en hilo separado
            dashboard_thread = threading.Thread(
                target=self._start_dashboard_thread,
                args=(mode,),
                daemon=True
            )
            dashboard_thread.start()
            
            # Esperar un poco y abrir navegador
            time.sleep(3)
            try:
                webbrowser.open('http://127.0.0.1:8050')
                print("🌐 Dashboard abierto en: http://127.0.0.1:8050")
            except Exception:
                print("🌐 Abre manualmente: http://127.0.0.1:8050")
            
            # Mantener el dashboard activo
            print("\n📊 Dashboard activo")
            print("💡 Presiona Ctrl+C para detener")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏹️ Deteniendo dashboard...")
                
        except Exception as e:
            print(f"❌ Error iniciando entrenamiento: {e}")
            logger.error(f"Error en entrenamiento: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    def _select_training_mode(self) -> str:
        """Selecciona modo de entrenamiento"""
        print("\n🎯 SELECCIONAR MODO DE ENTRENAMIENTO:")
        print("1. Paper Trading (Recomendado - Sin riesgo)")
        print("2. Backtesting (Pruebas históricas)")
        print("3. Development (Desarrollo y debugging)")
        
        while True:
            try:
                choice = input("Selecciona modo (1-3): ").strip()
                if choice == "1":
                    return "paper_trading"
                elif choice == "2":
                    return "backtesting"
                elif choice == "3":
                    return "development"
                else:
                    print("⚠️ Por favor selecciona 1, 2 o 3")
            except KeyboardInterrupt:
                return "paper_trading"
    
    def _start_dashboard_thread(self, mode: str):
        """Inicia dashboard en hilo separado"""
        try:
            # Cambiar al directorio del proyecto
            os.chdir(project_root)
            
            # Configurar variables de entorno
            env = os.environ.copy()
            env['TRADING_MODE'] = mode
            
            # Ejecutar main.py
            cmd = [sys.executable, 'core/main.py', '--mode', mode, '--dashboard']
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.dashboard_process = process
            
            # Monitorear output
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[DASHBOARD] {line.strip()}")
                    
        except Exception as e:
            print(f"❌ Error en dashboard: {e}")
    
    async def performance_analysis(self):
        """Opción 5: Análisis de performance"""
        print("\n📈 ANÁLISIS DE PERFORMANCE")
        print("=" * 30)
        
        try:
            # Verificar si hay datos de trades
            from data.database import db_manager
            
            # Obtener estadísticas básicas
            stats = db_manager.get_database_stats()
            print("📊 Estadísticas del sistema:")
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    if 'count' in key.lower():
                        print(f"   {key}: {value:,}")
                    else:
                        print(f"   {key}: {value}")
                else:
                    print(f"   {key}: {value}")
            
            # Análisis de trades si existe
            try:
                # Intentar análisis avanzado
                print(f"\n🔍 Ejecutando análisis avanzado...")
                
                # Simular análisis básico
                symbols = db_manager.get_symbols_list()
                print(f"\n📈 Símbolos disponibles: {len(symbols)}")
                
                for symbol in symbols[:4]:  # Mostrar primeros 4
                    count = db_manager.get_market_data_count(symbol)
                    date_range = db_manager.get_data_date_range(symbol)
                    
                    if date_range[0] and date_range[1]:
                        duration = (date_range[1] - date_range[0]).days
                        print(f"   {symbol}: {count:,} registros ({duration} días)")
                
                print(f"\n💡 Para análisis detallado, usa la opción 4 (Dashboard)")
                
            except Exception as e:
                print(f"⚠️ Análisis avanzado no disponible: {e}")
                
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def system_configuration(self):
        """Opción 6: Configurar sistema"""
        print("\n⚙️ CONFIGURACIÓN DEL SISTEMA")
        print("=" * 35)
        
        try:
            from config.config_loader import user_config
            
            print("📋 Configuración actual:")
            
            # Mostrar configuraciones clave
            bot_name = user_config.get_bot_name()
            trading_mode = user_config.get_trading_mode()
            symbols = user_config.get_trading_symbols()
            
            print(f"   Nombre del bot: {bot_name}")
            print(f"   Modo de trading: {trading_mode}")
            print(f"   Símbolos: {', '.join(symbols)}")
            
            print(f"\n📁 Archivos de configuración:")
            print(f"   config/user_settings.yaml")
            print(f"   .env")
            
            print(f"\n💡 Para modificar la configuración:")
            print(f"   1. Edita config/user_settings.yaml")
            print(f"   2. Edita .env para credenciales")
            print(f"   3. Reinicia la aplicación")
            
        except Exception as e:
            print(f"❌ Error accediendo configuración: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def quick_tests(self):
        """Opción 7: Modo de pruebas rápidas"""
        print("\n🧪 MODO DE PRUEBAS RÁPIDAS")
        print("=" * 30)
        
        print("🔍 Ejecutando pruebas del sistema...")
        
        tests = [
            ("Importaciones básicas", self._test_imports),
            ("Conexión a base de datos", self._test_database),
            ("Configuración", self._test_config),
            ("Módulos de IA", self._test_ai_modules)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                print(f"   {test_name}...", end=" ")
                result = await test_func()
                if result:
                    print("✅")
                    results.append(True)
                else:
                    print("❌")
                    results.append(False)
            except Exception as e:
                print(f"❌ ({e})")
                results.append(False)
        
        # Resumen
        passed = sum(results)
        total = len(results)
        print(f"\n📊 Resultados: {passed}/{total} pruebas pasaron")
        
        if passed == total:
            print("🎉 Sistema completamente funcional")
        elif passed >= total * 0.75:
            print("⚠️ Sistema mayormente funcional")
        else:
            print("❌ Sistema tiene problemas significativos")
        
        input("\nPresiona Enter para continuar...")
    
    async def _test_imports(self) -> bool:
        """Prueba importaciones básicas"""
        try:
            import pandas as pd
            import numpy as np
            from data.database import db_manager
            from config.config_loader import user_config
            return True
        except ImportError:
            return False
    
    async def _test_database(self) -> bool:
        """Prueba conexión a base de datos"""
        try:
            from data.database import db_manager
            stats = db_manager.get_database_stats()
            return isinstance(stats, dict)
        except Exception:
            return False
    
    async def _test_config(self) -> bool:
        """Prueba configuración"""
        try:
            from config.config_loader import user_config
            bot_name = user_config.get_bot_name()
            return isinstance(bot_name, str)
        except Exception:
            return False
    
    async def _test_ai_modules(self) -> bool:
        """Prueba módulos de IA"""
        try:
            from models.adaptive_trainer import adaptive_trainer
            return True
        except ImportError:
            return False
    
    async def system_status(self):
        """Opción 8: Estado del sistema"""
        print("\n📱 ESTADO DEL SISTEMA")
        print("=" * 25)
        
        try:
            # Estado general
            print("🖥️ Sistema:")
            print(f"   Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            print(f"   Directorio: {project_root}")
            print(f"   Tiempo de ejecución: {datetime.now().strftime('%H:%M:%S')}")
            
            # Estado de archivos críticos
            print(f"\n📁 Archivos críticos:")
            critical_files = [
                'core/main.py',
                'config/user_settings.yaml',
                '.env',
                'data/database.py',
                'models/adaptive_trainer.py'
            ]
            
            for file_path in critical_files:
                full_path = os.path.join(project_root, file_path)
                status = "✅" if os.path.exists(full_path) else "❌"
                print(f"   {status} {file_path}")
            
            # Estado de base de datos
            try:
                from data.database import db_manager
                stats = db_manager.get_database_stats()
                print(f"\n💾 Base de datos:")
                print(f"   Total registros: {stats.get('total_records', 0):,}")
                print(f"   Estado: ✅ Conectada")
            except Exception as e:
                print(f"\n💾 Base de datos: ❌ Error - {e}")
            
            # Procesos activos
            print(f"\n🔄 Procesos:")
            if self.dashboard_process and self.dashboard_process.poll() is None:
                print(f"   Dashboard: ✅ Activo (PID: {self.dashboard_process.pid})")
            else:
                print(f"   Dashboard: ❌ Inactivo")
            
        except Exception as e:
            print(f"❌ Error obteniendo estado: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def run(self):
        """Ejecuta el bucle principal de la aplicación"""
        self.show_banner()
        
        while self.running:
            try:
                self.show_main_menu()
                choice = self.get_user_choice()
                
                if choice == "1":
                    await self.download_historical_data()
                elif choice == "2":
                    await self.validate_ai_agent()
                elif choice == "3":
                    await self.validate_symbols_history()
                elif choice == "4":
                    await self.start_training_and_dashboard()
                elif choice == "5":
                    await self.performance_analysis()
                elif choice == "6":
                    await self.system_configuration()
                elif choice == "7":
                    await self.quick_tests()
                elif choice == "8":
                    await self.system_status()
                elif choice == "9":
                    self.running = False
                    print("\n👋 ¡Hasta luego!")
                else:
                    print("\n⚠️ Opción no válida. Por favor selecciona 1-9.")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo...")
                self.running = False
            except Exception as e:
                print(f"\n❌ Error inesperado: {e}")
                logger.error(f"Error en bucle principal: {e}")
                time.sleep(2)
        
        # Limpiar procesos
        if self.dashboard_process and self.dashboard_process.poll() is None:
            print("🧹 Deteniendo procesos...")
            self.dashboard_process.terminate()

def main():
    """Función principal"""
    try:
        app = TradingBotApp()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\n👋 Aplicación terminada por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logger.error(f"Error crítico en main: {e}")

if __name__ == "__main__":
    main()