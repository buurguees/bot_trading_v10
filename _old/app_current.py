#!/usr/bin/env python3
"""
app.py - Punto de Entrada Principal del Trading Bot v10
======================================================

SISTEMA DE MENÚ INTERACTIVO COMPLETO

Uso: python app.py

Funcionalidades:
1. Descargar históricos completos
2. Analizar datos históricos
3. Validar datos históricos
4. Alinear datos históricos (Multi-símbolo)
5. Entrenamiento corto (6 horas)
6. Entrenamiento infinito con dashboard
7. Trading en papel
8. Trading en vivo
9. Dashboard independiente
10. Análisis de performance
11. Estado del sistema
12. Salir

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
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
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

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
        self.symbols = self._load_symbols_from_config()
        
    def _load_symbols_from_config(self):
        """Carga símbolos automáticamente desde los archivos .yaml"""
        try:
            from config.config_loader import user_config
            symbols = user_config.get_symbols()
            if symbols:
                logger.info(f"Símbolos cargados desde configuración: {', '.join(symbols)}")
                return symbols
            else:
                # Fallback a símbolos por defecto
                default_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
                logger.warning(f"No se encontraron símbolos en configuración, usando por defecto: {', '.join(default_symbols)}")
                return default_symbols
        except Exception as e:
            logger.error(f"Error cargando símbolos: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    def show_banner(self):
        """Muestra banner de bienvenida"""
        print("\n" + "="*70)
        print("     🤖 TRADING BOT v10 - SISTEMA AUTÓNOMO DE TRADING 🤖")
        print("="*70)
        print(f"     Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     Entorno: Python {sys.version_info.major}.{sys.version_info.minor}")
        print(f"     Directorio: {project_root}")
        print(f"     Símbolos: {', '.join(self.symbols)}")
        print("="*70)
        print()
    
    def show_main_menu(self):
        """Muestra el menú principal"""
        print("📋 MENÚ PRINCIPAL - ENTERPRISE EDITION")
        print("-" * 40)
        print("1. 📥 Descargar datos históricos")
        print("2. 🔍 Analizar datos históricos")
        print("3. ✅ Validar datos históricos")
        print("4. 🔄 Alinear datos históricos (Multi-símbolo)")
        print("5. 🚀 Entrenamiento corto (6 horas)")
        print("6. ⚡ Entrenamiento infinito con dashboard")
        print("7. 📊 Trading en papel")
        print("8. 💰 Trading en vivo")
        print("9. 📈 Dashboard independiente")
        print("10. 📊 Análisis de performance")
        print("11. 📱 Estado del sistema")
        print("12. ❌ Salir")
        print()
        
        # Mostrar estado del sistema
        print("🏢 Sistema Enterprise: ✅ Disponible")
        print(f"📊 Símbolos configurados: {len(self.symbols)} - {', '.join(self.symbols[:3])}{'...' if len(self.symbols) > 3 else ''}")
        print()
    
    def get_user_choice(self) -> str:
        """Obtiene la elección del usuario"""
        try:
            choice = input("Selecciona una opción (1-12): ").strip()
            return choice
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            return "12"
        except Exception:
            return ""
    
    async def download_historical_data(self):
        """Opción 1: Descargar datos históricos"""
        print("\n📥 DESCARGA DE DATOS HISTÓRICOS")
        print("=" * 40)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Usar el bot.py para descargar datos
            cmd = [sys.executable, 'bot.py', '--mode', 'download-historical', '--symbols', ','.join(self.symbols)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Esto puede tomar varios minutos...")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Descarga completada exitosamente")
                print(process.stdout)
            else:
                print("❌ Error durante la descarga")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante la descarga: {e}")
            logger.error(f"Error en descarga: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def analyze_historical_data(self):
        """Opción 2: Analizar datos históricos"""
        print("\n🔍 ANÁLISIS DE DATOS HISTÓRICOS")
        print("=" * 40)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Usar el bot.py para analizar datos
            cmd = [sys.executable, 'bot.py', '--mode', 'analyze', '--symbols', ','.join(self.symbols)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Análisis completado exitosamente")
                print(process.stdout)
            else:
                print("❌ Error durante el análisis")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante el análisis: {e}")
            logger.error(f"Error en análisis: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def validate_historical_data(self):
        """Opción 3: Validar datos históricos"""
        print("\n✅ VALIDACIÓN DE DATOS HISTÓRICOS")
        print("=" * 40)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Usar el bot.py para validar datos
            cmd = [sys.executable, 'bot.py', '--mode', 'validate', '--symbols', ','.join(self.symbols)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Validación completada exitosamente")
                print(process.stdout)
            else:
                print("❌ Error durante la validación")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante la validación: {e}")
            logger.error(f"Error en validación: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def align_historical_data(self):
        """Opción 4: Alinear datos históricos para análisis multi-símbolo"""
        print("\n🔄 ALINEACIÓN DE DATOS HISTÓRICOS")
        print("=" * 45)
        print("Esta función sincroniza los datos de todos los símbolos")
        print("para permitir análisis simultáneo y trading multi-símbolo.")
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Crear script temporal para alineación
            align_script = """
import pandas as pd
import os
from pathlib import Path
import json

def align_data():
    symbols = {symbols}
    data_dir = Path('data/historical')
    alignments_dir = Path('data/alignments')
    alignments_dir.mkdir(exist_ok=True)
    
    print(f"Procesando {len(symbols)} símbolos...")
    
    aligned_data = {{}}
    common_start = None
    common_end = None
    
    # Cargar datos de cada símbolo
    for symbol in symbols:
        file_path = data_dir / f"{{symbol}}_1m.csv"
        if file_path.exists():
            df = pd.read_csv(file_path, parse_dates=['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            if common_start is None:
                common_start = df.index.min()
                common_end = df.index.max()
            else:
                common_start = max(common_start, df.index.min())
                common_end = min(common_end, df.index.max())
            
            aligned_data[symbol] = df
            print(f"  {{symbol}}: {{len(df)}} registros")
        else:
            print(f"  {{symbol}}: ❌ Archivo no encontrado")
    
    if common_start and common_end:
        # Crear timestamps comunes
        common_timestamps = pd.date_range(start=common_start, end=common_end, freq='1min')
        print(f"Timestamps comunes: {{len(common_timestamps)}}")
        
        # Alinear todos los datos
        for symbol, df in aligned_data.items():
            aligned_df = df.reindex(common_timestamps, method='ffill')
            aligned_data[symbol] = aligned_df
            print(f"  {{symbol}} alineado: {{len(aligned_df)}} registros")
        
        # Guardar datos alineados
        output_file = alignments_dir / 'multi_symbol_aligned.json'
        with open(output_file, 'w') as f:
            # Convertir DataFrames a dict para JSON
            json_data = {{}}
            for symbol, df in aligned_data.items():
                json_data[symbol] = {{
                    'data': df.to_dict('records'),
                    'start': common_start.isoformat(),
                    'end': common_end.isoformat()
                }}
            json.dump(json_data, f, indent=2)
        
        print(f"✅ Datos alineados guardados en: {{output_file}}")
        print(f"Período común: {{common_start.strftime('%Y-%m-%d')}} a {{common_end.strftime('%Y-%m-%d')}}")
    else:
        print("❌ No se encontraron datos para alinear")

if __name__ == "__main__":
    align_data()
""".format(symbols=self.symbols)
            
            # Guardar script temporal
            temp_script = Path('temp_align.py')
            with open(temp_script, 'w', encoding='utf-8') as f:
                f.write(align_script)
            
            # Ejecutar script
            cmd = [sys.executable, str(temp_script)]
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            # Limpiar script temporal
            temp_script.unlink()
            
            if process.returncode == 0:
                print("✅ Alineación completada exitosamente")
                print(process.stdout)
            else:
                print("❌ Error durante la alineación")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante la alineación: {e}")
            logger.error(f"Error en alineación: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_short_training(self):
        """Opción 5: Entrenamiento corto (6 horas)"""
        print("\n🚀 ENTRENAMIENTO CORTO (6 HORAS)")
        print("=" * 40)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Usar el bot.py para entrenamiento corto
            cmd = [sys.executable, 'bot.py', '--mode', 'train-short', '--symbols', ','.join(self.symbols)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Esto puede tomar varias horas...")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Entrenamiento corto completado exitosamente")
                print(process.stdout)
            else:
                print("❌ Error durante el entrenamiento")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante el entrenamiento: {e}")
            logger.error(f"Error en entrenamiento: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_infinite_training_with_dashboard(self):
        """Opción 6: Entrenamiento infinito con dashboard"""
        print("\n⚡ ENTRENAMIENTO INFINITO CON DASHBOARD")
        print("=" * 45)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Usar el bot.py para entrenamiento infinito
            cmd = [sys.executable, 'bot.py', '--mode', 'train-infinite', '--symbols', ','.join(self.symbols)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Esto iniciará el entrenamiento y el dashboard...")
            print("🌐 Dashboard estará disponible en: http://127.0.0.1:8050")
            print()
            
            # Ejecutar en hilo separado
            def run_training():
                process = subprocess.run(cmd, cwd=project_root)
                return process
            
            training_thread = threading.Thread(target=run_training, daemon=True)
            training_thread.start()
            
            # Esperar un poco y abrir navegador
            time.sleep(5)
            try:
                webbrowser.open('http://127.0.0.1:8050')
                print("🌐 Dashboard abierto en: http://127.0.0.1:8050")
            except Exception:
                print("🌐 Abre manualmente: http://127.0.0.1:8050")
            
            print("\n📊 Entrenamiento infinito activo")
            print("💡 Presiona Ctrl+C para detener")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏹️ Deteniendo entrenamiento...")
                
        except Exception as e:
            print(f"❌ Error durante el entrenamiento infinito: {e}")
            logger.error(f"Error en entrenamiento infinito: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_paper_trading(self):
        """Opción 7: Trading en papel"""
        print("\n📊 TRADING EN PAPEL")
        print("=" * 25)
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        try:
            # Seleccionar leverage
            while True:
                try:
                    leverage_input = input("Selecciona leverage (5-30, por defecto 10): ").strip()
                    leverage = int(leverage_input) if leverage_input else 10
                    if 5 <= leverage <= 30:
                        break
                    else:
                        print("⚠️ Por favor ingresa un leverage entre 5 y 30")
                except ValueError:
                    print("⚠️ Por favor ingresa un número válido")
            
            # Usar el bot.py para trading en papel
            cmd = [sys.executable, 'bot.py', '--mode', 'paper', '--symbols', ','.join(self.symbols), '--leverage', str(leverage)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Iniciando trading en papel...")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Trading en papel completado")
                print(process.stdout)
            else:
                print("❌ Error durante el trading en papel")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante el trading en papel: {e}")
            logger.error(f"Error en trading en papel: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_live_trading(self):
        """Opción 8: Trading en vivo"""
        print("\n💰 TRADING EN VIVO")
        print("=" * 25)
        print("⚠️ ADVERTENCIA: Esta opción ejecutará trading real con dinero real")
        print(f"Símbolos: {', '.join(self.symbols)}")
        print()
        
        # Confirmar trading en vivo
        confirm = input("¿Estás seguro de que quieres iniciar trading en vivo? (escribe 'SI' para confirmar): ").strip()
        if confirm != 'SI':
            print("❌ Trading en vivo cancelado")
            input("\nPresiona Enter para continuar...")
            return
        
        try:
            # Seleccionar leverage
            while True:
                try:
                    leverage_input = input("Selecciona leverage (5-30, por defecto 10): ").strip()
                    leverage = int(leverage_input) if leverage_input else 10
                    if 5 <= leverage <= 30:
                        break
                    else:
                        print("⚠️ Por favor ingresa un leverage entre 5 y 30")
                except ValueError:
                    print("⚠️ Por favor ingresa un número válido")
            
            # Usar el bot.py para trading en vivo
            cmd = [sys.executable, 'bot.py', '--mode', 'live', '--symbols', ','.join(self.symbols), '--leverage', str(leverage)]
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("⏳ Iniciando trading en vivo...")
            print("⚠️ MONITOREAR CUIDADOSAMENTE")
            print()
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if process.returncode == 0:
                print("✅ Trading en vivo completado")
                print(process.stdout)
            else:
                print("❌ Error durante el trading en vivo")
                print(process.stderr)
                
        except Exception as e:
            print(f"❌ Error durante el trading en vivo: {e}")
            logger.error(f"Error en trading en vivo: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def start_dashboard(self):
        """Opción 9: Dashboard independiente"""
        print("\n📈 DASHBOARD INDEPENDIENTE")
        print("=" * 30)
        print("Iniciando dashboard en puerto 8050...")
        print()
        
        try:
            # Usar el dashboard.py
            cmd = [sys.executable, 'dashboard.py', '--port', '8050']
            
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            print("🌐 Dashboard estará disponible en: http://127.0.0.1:8050")
            print()
            
            # Ejecutar en hilo separado
            def run_dashboard():
                process = subprocess.run(cmd, cwd=project_root)
                return process
            
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            
            # Esperar un poco y abrir navegador
            time.sleep(3)
            try:
                webbrowser.open('http://127.0.0.1:8050')
                print("🌐 Dashboard abierto en: http://127.0.0.1:8050")
            except Exception:
                print("🌐 Abre manualmente: http://127.0.0.1:8050")
            
            print("\n📊 Dashboard activo")
            print("💡 Presiona Ctrl+C para detener")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏹️ Deteniendo dashboard...")
                
        except Exception as e:
            print(f"❌ Error durante el dashboard: {e}")
            logger.error(f"Error en dashboard: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def performance_analysis(self):
        """Opción 10: Análisis de performance"""
        print("\n📊 ANÁLISIS DE PERFORMANCE")
        print("=" * 30)
        
        try:
            # Verificar archivos de reportes
            reports_dir = Path('reports')
            if reports_dir.exists():
                print("📁 Reportes disponibles:")
                for report_file in reports_dir.glob('*.json'):
                    print(f"   📄 {report_file.name}")
                
                # Mostrar análisis si existe
                analysis_file = reports_dir / 'analysis.json'
                if analysis_file.exists():
                    import json
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    print(f"\n📈 Análisis de datos:")
                    for symbol, data in analysis_data.items():
                        if isinstance(data, dict):
                            print(f"   {symbol}:")
                            for key, value in data.items():
                                if isinstance(value, (int, float)):
                                    print(f"     {key}: {value}")
                                else:
                                    print(f"     {key}: {value}")
            else:
                print("❌ No se encontraron reportes")
                print("💡 Ejecuta primero 'Analizar datos históricos' para generar reportes")
            
            # Verificar modelos
            models_dir = Path('models')
            if models_dir.exists():
                model_files = list(models_dir.glob('*_model.json'))
                print(f"\n🧠 Modelos entrenados: {len(model_files)}")
                for model_file in model_files:
                    print(f"   📄 {model_file.name}")
            else:
                print("\n❌ No se encontraron modelos")
                print("💡 Ejecuta primero 'Entrenamiento corto' para generar modelos")
                
        except Exception as e:
            print(f"❌ Error durante el análisis: {e}")
            logger.error(f"Error en análisis: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    async def system_status(self):
        """Opción 11: Estado del sistema"""
        print("\n📱 ESTADO DEL SISTEMA")
        print("=" * 25)
        
        try:
            # Estado general
            print("🖥️ Sistema:")
            print(f"   Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            print(f"   Directorio: {project_root}")
            print(f"   Tiempo de ejecución: {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Símbolos configurados: {len(self.symbols)}")
            
            # Estado de archivos críticos
            print(f"\n📁 Archivos críticos:")
            critical_files = [
                'bot.py',
                'dashboard.py',
                'config/user_settings.yaml',
                '.env',
                'requirements.txt'
            ]
            
            for file_path in critical_files:
                full_path = Path(project_root) / file_path
                status = "✅" if full_path.exists() else "❌"
                print(f"   {status} {file_path}")
            
            # Estado de directorios de datos
            print(f"\n📊 Directorios de datos:")
            data_dirs = ['data/historical', 'data/alignments', 'models', 'reports', 'logs']
            for dir_path in data_dirs:
                full_path = Path(project_root) / dir_path
                if full_path.exists():
                    file_count = len(list(full_path.glob('*')))
                    print(f"   ✅ {dir_path} ({file_count} archivos)")
                else:
                    print(f"   ❌ {dir_path}")
            
            # Verificar APIs
            print(f"\n🔑 APIs:")
            api_key = os.getenv('BITGET_API_KEY')
            if api_key and api_key != 'your_bitget_api_key_here':
                print(f"   ✅ Bitget API: Configurada")
            else:
                print(f"   ❌ Bitget API: No configurada")
            
            # Estado de procesos
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
                    await self.analyze_historical_data()
                elif choice == "3":
                    await self.validate_historical_data()
                elif choice == "4":
                    await self.align_historical_data()
                elif choice == "5":
                    await self.start_short_training()
                elif choice == "6":
                    await self.start_infinite_training_with_dashboard()
                elif choice == "7":
                    await self.start_paper_trading()
                elif choice == "8":
                    await self.start_live_trading()
                elif choice == "9":
                    await self.start_dashboard()
                elif choice == "10":
                    await self.performance_analysis()
                elif choice == "11":
                    await self.system_status()
                elif choice == "12":
                    self.running = False
                    print("\n👋 ¡Hasta luego!")
                else:
                    print("\n⚠️ Opción no válida. Por favor selecciona 1-12.")
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
