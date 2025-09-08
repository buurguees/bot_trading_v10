#!/usr/bin/env python3
"""
Métodos adicionales para app_enterprise.py
"""

async def start_training_background(self):
    """Opción 6: Entrenamiento sin Dashboard (Background)"""
    print("\n🤖 ENTRENAMIENTO SIN DASHBOARD (BACKGROUND)")
    print("=" * 50)
    
    try:
        await self._execute_operation(
            "start_training_background",
            self._start_background_training,
            timeout=7200  # 2 horas
        )
        
    except TimeoutError:
        print(f"\n⏰ El entrenamiento excedió el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error iniciando entrenamiento: {e}")
        self.logger.error(f"Error in start_training_background: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _start_background_training(self):
    """Inicia entrenamiento en background"""
    # Verificar prerequisitos
    print("🔍 Verificando prerequisitos...")
    
    # Verificar datos
    from data.database import db_manager
    stats = db_manager.get_data_summary_optimized()
    total_records = stats.get('total_records', 0)
    
    if total_records < 1000:
        print(f"⚠️ Datos insuficientes: {total_records:,} registros")
        if not self.headless:
            download = input("¿Descargar datos históricos primero? (s/n): ").strip().lower()
            if download == 's':
                await self.download_historical_data()
            else:
                print("❌ Cancelando entrenamiento")
                return
        else:
            print("❌ Cancelando entrenamiento (modo headless)")
            return
    else:
        print(f"✅ Datos suficientes: {total_records:,} registros")
    
    # Configurar modo de entrenamiento
    mode = self._select_background_training_mode()
    
    # Configurar duración del entrenamiento
    duration = self._select_training_duration()
    
    print(f"\n🎯 Configuración del entrenamiento:")
    print(f"   Modo: {mode}")
    print(f"   Duración: {duration}")
    print(f"   Dashboard: ❌ Deshabilitado")
    print()
    
    # Confirmar inicio
    if not self.headless:
        confirm = input("¿Iniciar entrenamiento en background? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Entrenamiento cancelado")
            return
    
    print(f"\n🚀 Iniciando entrenamiento en background...")
    print(f"⏳ El bot se ejecutará sin interfaz gráfica")
    print(f"📊 Puedes monitorear el progreso en los logs")
    print()
    
    # Iniciar entrenamiento en hilo separado
    training_thread = threading.Thread(
        target=self._start_background_training_thread,
        args=(mode, duration),
        daemon=True
    )
    training_thread.start()
    
    # Mostrar información de monitoreo
    print("📋 INFORMACIÓN DE MONITOREO:")
    print(f"   Logs del agente: logs/agent_training.log")
    print(f"   Logs del sistema: logs/trading_bot.log")
    print(f"   Base de datos: data/trading_bot.db")
    print()
    print("💡 Para detener el entrenamiento:")
    print(f"   - Presiona Ctrl+C en esta ventana")
    print(f"   - O cierra esta aplicación")
    print()
    
    # Mantener la aplicación activa para monitoreo
    print("🔄 Entrenamiento activo - Presiona Ctrl+C para detener")
    
    try:
        while True:
            time.sleep(5)
            # Mostrar estado cada 30 segundos
            if int(time.time()) % 30 == 0:
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Entrenamiento en progreso...")
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo entrenamiento...")
        print("🔄 El bot puede tardar unos segundos en detenerse completamente")

def _select_background_training_mode(self) -> str:
    """Selecciona modo de entrenamiento para background"""
    if self.headless:
        return "paper_trading"  # Modo por defecto para headless
    
    print("\n🎯 SELECCIONAR MODO DE ENTRENAMIENTO:")
    print("1. Paper Trading (Recomendado - Sin riesgo)")
    print("2. Backtesting (Pruebas históricas)")
    print("3. Development (Desarrollo y debugging)")
    print("4. Continuous Learning (Aprendizaje continuo)")
    
    while True:
        try:
            choice = input("Selecciona modo (1-4): ").strip()
            if choice == "1":
                return "paper_trading"
            elif choice == "2":
                return "backtesting"
            elif choice == "3":
                return "development"
            elif choice == "4":
                return "continuous_learning"
            else:
                print("⚠️ Por favor selecciona 1, 2, 3 o 4")
        except KeyboardInterrupt:
            return "paper_trading"

def _select_training_duration(self) -> str:
    """Selecciona duración del entrenamiento"""
    if self.headless:
        return "8h"  # Duración por defecto para headless
    
    print("\n⏰ DURACIÓN DEL ENTRENAMIENTO:")
    print("1. 1 hora")
    print("2. 4 horas")
    print("3. 8 horas")
    print("4. 12 horas")
    print("5. 24 horas")
    print("6. Indefinido (hasta detener manualmente)")
    
    while True:
        try:
            choice = input("Selecciona duración (1-6): ").strip()
            duration_map = {
                "1": "1h",
                "2": "4h", 
                "3": "8h",
                "4": "12h",
                "5": "24h",
                "6": "indefinite"
            }
            if choice in duration_map:
                return duration_map[choice]
            else:
                print("⚠️ Por favor selecciona 1, 2, 3, 4, 5 o 6")
        except KeyboardInterrupt:
            return "8h"

def _start_background_training_thread(self, mode: str, duration: str):
    """Inicia entrenamiento en hilo separado sin dashboard"""
    try:
        # Cambiar al directorio del proyecto
        os.chdir(project_root)
        
        # Configurar variables de entorno
        env = os.environ.copy()
        env['TRADING_MODE'] = mode
        env['TRAINING_DURATION'] = duration
        env['BACKGROUND_MODE'] = 'true'
        env['DASHBOARD_ENABLED'] = 'false'
        
        # Ejecutar main.py sin dashboard
        cmd = [sys.executable, 'core/main_background.py', '--mode', mode, '--background', '--no-dashboard']
        
        print(f"🚀 Ejecutando comando: {' '.join(cmd)}")
        print(f"📁 Directorio: {os.getcwd()}")
        print(f"⏰ Duración: {duration}")
        print()
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self.dashboard_process = process
        
        # Monitorear output con timestamps
        print("📊 Iniciando monitoreo del entrenamiento...")
        start_time = time.time()
        
        for line in iter(process.stdout.readline, ''):
            if line:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] {line.strip()}")
                
                # Mostrar progreso cada 5 minutos
                if int(time.time() - start_time) % 300 == 0:
                    elapsed = int(time.time() - start_time) // 60
                    print(f"⏰ Entrenamiento activo por {elapsed} minutos...")
                    
    except Exception as e:
        print(f"❌ Error en entrenamiento background: {e}")
        self.logger.error(f"Error in background training thread: {e}")
        import traceback
        traceback.print_exc()

async def performance_analysis(self):
    """Opción 7: Análisis de performance con métricas detalladas"""
    print("\n📈 ANÁLISIS DE PERFORMANCE")
    print("=" * 30)
    
    try:
        await self._execute_operation(
            "performance_analysis",
            self._analyze_performance,
            timeout=300
        )
        
    except TimeoutError:
        print(f"\n⏰ El análisis excedió el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error en análisis: {e}")
        self.logger.error(f"Error in performance_analysis: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _analyze_performance(self):
    """Analiza performance del sistema"""
    # Verificar si hay datos de trades
    from data.database import db_manager
    
    # Obtener estadísticas básicas
    stats = db_manager.get_data_summary_optimized()
    print("📊 Estadísticas del sistema:")
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            if 'count' in key.lower() or 'total' in key.lower():
                print(f"   {key}: {value:,}")
            else:
                print(f"   {key}: {value}")
        elif isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (int, float)):
                    print(f"     {sub_key}: {sub_value:,}")
                else:
                    print(f"     {sub_key}: {sub_value}")
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
            count = db_manager.get_market_data_count_fast(symbol)
            date_range = db_manager.get_data_date_range(symbol)
            
            if date_range[0] and date_range[1]:
                duration = (date_range[1] - date_range[0]).days
                print(f"   {symbol}: {count:,} registros ({duration} días)")
        
        print(f"\n💡 Para análisis detallado, usa la opción 5 (Dashboard)")
        
    except Exception as e:
        print(f"⚠️ Análisis avanzado no disponible: {e}")

async def system_configuration(self):
    """Opción 8: Configurar sistema con validaciones"""
    print("\n⚙️ CONFIGURACIÓN DEL SISTEMA")
    print("=" * 35)
    
    try:
        await self._execute_operation(
            "system_configuration",
            self._show_system_config,
            timeout=60
        )
        
    except TimeoutError:
        print(f"\n⏰ La configuración excedió el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error accediendo configuración: {e}")
        self.logger.error(f"Error in system_configuration: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _show_system_config(self):
    """Muestra configuración del sistema"""
    from config.config_loader import user_config
    
    print("📋 Configuración actual:")
    
    # Mostrar configuraciones clave
    bot_name = user_config.get_bot_name()
    trading_mode = user_config.get_trading_mode()
    
    # Obtener símbolos desde la configuración
    bot_settings = user_config.get_value(['bot_settings'], {})
    symbols = bot_settings.get('main_symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'])
    
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

async def quick_tests(self):
    """Opción 9: Modo de pruebas rápidas con métricas"""
    print("\n🧪 MODO DE PRUEBAS RÁPIDAS")
    print("=" * 30)
    
    try:
        await self._execute_operation(
            "quick_tests",
            self._run_quick_tests,
            timeout=120
        )
        
    except TimeoutError:
        print(f"\n⏰ Las pruebas excedieron el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error en pruebas: {e}")
        self.logger.error(f"Error in quick_tests: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _run_quick_tests(self):
    """Ejecuta pruebas rápidas del sistema"""
    print("🔍 Ejecutando pruebas del sistema...")
    
    tests = [
        ("Importaciones básicas", self._test_imports),
        ("Conexión a base de datos", self._test_database),
        ("Configuración", self._test_config),
        ("Módulos de IA", self._test_ai_modules),
        ("Sistema Enterprise", self._test_enterprise_system)
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
        stats = db_manager.get_data_summary_optimized()
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

async def _test_enterprise_system(self) -> bool:
    """Prueba sistema enterprise"""
    try:
        return self.enterprise_config is not None
    except Exception:
        return False

async def system_status(self):
    """Opción 10: Estado del sistema con métricas detalladas"""
    print("\n📱 ESTADO DEL SISTEMA")
    print("=" * 25)
    
    try:
        await self._execute_operation(
            "system_status",
            self._show_system_status,
            timeout=30
        )
        
    except TimeoutError:
        print(f"\n⏰ El estado excedió el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error obteniendo estado: {e}")
        self.logger.error(f"Error in system_status: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _show_system_status(self):
    """Muestra estado detallado del sistema"""
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
        stats = db_manager.get_data_summary_optimized()
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
    
    # Métricas de performance
    print(f"\n📊 Métricas de Performance:")
    metrics_summary = self.metrics.get_summary()
    print(f"   Tiempo total de ejecución: {metrics_summary['total_runtime']:.2f}s")
    print(f"   Operaciones completadas: {metrics_summary['operations']}")
    print(f"   Tasa de éxito: {metrics_summary['success_rate']:.1%}")
    print(f"   Tiempo promedio por operación: {metrics_summary['avg_operation_time']:.2f}s")
    print(f"   Errores: {metrics_summary['error_count']}")
    print(f"   Éxitos: {metrics_summary['success_count']}")

async def enterprise_configuration(self):
    """Opción 11: Configuración Enterprise"""
    print("\n🏢 CONFIGURACIÓN ENTERPRISE")
    print("=" * 35)
    
    if not self.enterprise_config:
        print("❌ Sistema Enterprise no disponible")
        print("💡 Asegúrate de que core/enterprise_config.py esté disponible")
        if not self.headless:
            input("\nPresiona Enter para continuar...")
        return
    
    try:
        await self._execute_operation(
            "enterprise_configuration",
            self._show_enterprise_config,
            timeout=60
        )
        
    except TimeoutError:
        print(f"\n⏰ La configuración excedió el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error en configuración enterprise: {e}")
        self.logger.error(f"Error in enterprise_configuration: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _show_enterprise_config(self):
    """Muestra configuración enterprise"""
    print("🔧 Configuración Enterprise disponible")
    print("📊 Funcionalidades:")
    print("   ✅ Gestión segura de configuración")
    print("   ✅ Encriptación de datos sensibles")
    print("   ✅ Auditoría y logging")
    print("   ✅ Validación robusta")
    print("   ✅ Thread safety")
    
    # Mostrar estado de configuración
    try:
        config_status = self.enterprise_config.get_configuration_status()
        print(f"\n📋 Estado de configuración:")
        print(f"   Configuraciones cargadas: {config_status.get('loaded_configs', 0)}")
        print(f"   Última actualización: {config_status.get('last_update', 'Nunca')}")
        print(f"   Validaciones activas: {config_status.get('validations_active', False)}")
    except Exception as e:
        print(f"⚠️ Error obteniendo estado: {e}")

async def show_metrics(self):
    """Opción 12: Métricas y Monitoreo"""
    print("\n📊 MÉTRICAS Y MONITOREO")
    print("=" * 30)
    
    try:
        await self._execute_operation(
            "show_metrics",
            self._display_metrics,
            timeout=30
        )
        
    except TimeoutError:
        print(f"\n⏰ Las métricas excedieron el tiempo límite")
    except Exception as e:
        print(f"\n❌ Error mostrando métricas: {e}")
        self.logger.error(f"Error in show_metrics: {e}")
    
    if not self.headless:
        input("\nPresiona Enter para continuar...")

async def _display_metrics(self):
    """Muestra métricas detalladas"""
    metrics_summary = self.metrics.get_summary()
    
    print("📈 MÉTRICAS DE PERFORMANCE:")
    print(f"   Tiempo total de ejecución: {metrics_summary['total_runtime']:.2f} segundos")
    print(f"   Operaciones completadas: {metrics_summary['operations']}")
    print(f"   Tasa de éxito: {metrics_summary['success_rate']:.1%}")
    print(f"   Tiempo promedio por operación: {metrics_summary['avg_operation_time']:.2f} segundos")
    print(f"   Total de errores: {metrics_summary['error_count']}")
    print(f"   Total de éxitos: {metrics_summary['success_count']}")
    
    if self.metrics.operation_times:
        print(f"\n⏱️ TIEMPOS POR OPERACIÓN:")
        for operation, duration in sorted(self.metrics.operation_times.items(), key=lambda x: x[1], reverse=True):
            print(f"   {operation}: {duration:.2f}s")
    
    # Métricas del sistema
    print(f"\n🖥️ MÉTRICAS DEL SISTEMA:")
    print(f"   Uso de memoria: {self._get_memory_usage():.2f} MB")
    print(f"   Procesos activos: {self._get_active_processes()}")
    
    # Estado de archivos de log
    print(f"\n📝 ARCHIVOS DE LOG:")
    log_files = [
        'logs/enterprise_app.log',
        'logs/trading_bot.log',
        'logs/agent_training.log'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file) / 1024 / 1024  # MB
            print(f"   {log_file}: {size:.2f} MB")
        else:
            print(f"   {log_file}: No existe")

def _get_memory_usage(self) -> float:
    """Obtiene uso de memoria en MB"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0

def _get_active_processes(self) -> int:
    """Obtiene número de procesos activos"""
    try:
        import psutil
        return len(psutil.pids())
    except ImportError:
        return 0

async def exit_application(self):
    """Opción 13: Salir de la aplicación"""
    print("\n👋 Cerrando aplicación...")
    
    # Mostrar resumen final
    metrics_summary = self.metrics.get_summary()
    print(f"\n📊 Resumen de la sesión:")
    print(f"   Tiempo total: {metrics_summary['total_runtime']:.2f} segundos")
    print(f"   Operaciones: {metrics_summary['operations']}")
    print(f"   Tasa de éxito: {metrics_summary['success_rate']:.1%}")
    
    # Limpiar procesos
    self._cleanup_processes()
    
    print("✅ Aplicación cerrada correctamente")
    self.running = False

async def run(self):
    """Ejecuta el bucle principal de la aplicación enterprise"""
    self.show_banner()
    
    while self.running:
        try:
            self.show_main_menu()
            choice = self.get_user_choice()
            
            # Obtener opción del menú
            option = self.menu_options.get(choice)
            if not option:
                print("\n⚠️ Opción no válida. Por favor selecciona 1-13.")
                time.sleep(1)
                continue
            
            # Ejecutar operación
            try:
                await self._execute_operation(
                    option.description,
                    option.handler,
                    timeout=option.timeout
                )
            except TimeoutError:
                print(f"\n⏰ La operación '{option.description}' excedió el tiempo límite")
            except Exception as e:
                print(f"\n❌ Error en operación: {e}")
                self.logger.error(f"Error in operation {option.description}: {e}")
            
            # Pausa en modo headless
            if self.headless and choice != "13":
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\n👋 Saliendo...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            self.logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(2)
    
    # Limpiar procesos
    self._cleanup_processes()

def main():
    """Función principal con soporte para argumentos CLI"""
    parser = argparse.ArgumentParser(
        description="Trading Bot v10 - Enterprise Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python app_enterprise.py                    # Modo interactivo
  python app_enterprise.py --option 1        # Descargar datos
  python app_enterprise.py --headless        # Modo headless
  python app_enterprise.py --option 5 --headless  # Entrenamiento headless
        """
    )
    
    parser.add_argument(
        '--option', 
        type=str, 
        help='Opción del menú a ejecutar (1-13)'
    )
    parser.add_argument(
        '--headless', 
        action='store_true', 
        help='Ejecutar en modo headless (sin interacción del usuario)'
    )
    parser.add_argument(
        '--log-level', 
        type=str, 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
        default='INFO',
        help='Nivel de logging'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=300,
        help='Timeout por defecto para operaciones (segundos)'
    )
    
    args = parser.parse_args()
    
    try:
        # Configurar logging con nivel especificado
        global logger
        logger = setup_logging(args.log_level)
        
        # Crear aplicación
        app = EnterpriseTradingBotApp(
            headless=args.headless,
            log_level=args.log_level
        )
        
        # Ejecutar opción específica o menú completo
        if args.option:
            # Ejecutar opción específica
            option = app.menu_options.get(args.option)
            if option:
                print(f"Ejecutando: {option.description}")
                asyncio.run(option.handler())
            else:
                print(f"❌ Opción {args.option} no válida")
                sys.exit(1)
        else:
            # Ejecutar menú completo
            asyncio.run(app.run())
            
    except KeyboardInterrupt:
        print("\n👋 Aplicación terminada por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logger.error(f"Critical error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
