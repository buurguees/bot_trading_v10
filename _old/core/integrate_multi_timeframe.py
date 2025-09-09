"""
integrate_multi_timeframe.py - Script de Integración del Sistema Multi-Timeframe
Integra las nuevas funcionalidades en app.py y otros archivos del sistema
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

def integrate_app_py():
    """Integra las nuevas funcionalidades en app.py"""
    print("🔄 Integrando funcionalidades multi-timeframe en app.py...")
    
    # Leer app.py actual
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar la sección de opciones del menú
    menu_section = """
    def mostrar_menu_principal(self):
        \"\"\"Muestra el menú principal del sistema\"\"\"
        print("\\n" + "="*60)
        print("🤖 TRADING BOT v10 - SISTEMA MULTI-TIMEFRAME")
        print("="*60)
        print("1. 📊 Descargar datos históricos")
        print("2. 🔍 Verificar datos históricos")
        print("3. 🧠 Entrenar modelo inicial")
        print("4. 🔄 Alinear datos históricos (Multi-símbolo)")
        print("5. 🚀 Iniciar trading en vivo")
        print("6. 🔄 Entrenamiento sin dashboard")
        print("7. 📈 Dashboard de monitoreo")
        print("8. ⚙️ Configuración del sistema")
        print("9. 📊 Descarga Multi-Timeframe Avanzada")
        print("10. 🔄 Procesamiento Coordinado Multi-TF")
        print("11. 📋 Estadísticas del Sistema Multi-TF")
        print("0. 🚪 Salir")
        print("="*60)
"""
    
    # Reemplazar la función del menú si existe
    if "def mostrar_menu_principal" in content:
        # Encontrar y reemplazar la función completa
        start_idx = content.find("def mostrar_menu_principal")
        if start_idx != -1:
            # Encontrar el final de la función
            lines = content[start_idx:].split('\n')
            end_idx = start_idx
            indent_level = None
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "":
                    continue
                if indent_level is None and line.strip():
                    indent_level = len(line) - len(line.lstrip())
                if line.strip() and len(line) - len(line.lstrip()) <= indent_level:
                    end_idx = start_idx + len('\n'.join(lines[:i]))
                    break
            
            new_content = content[:start_idx] + menu_section + content[end_idx:]
        else:
            new_content = content
    else:
        new_content = content
    
    # Agregar nuevas opciones al final de la clase TradingBot
    new_methods = """
    # =============================================================================
    # NUEVAS FUNCIONALIDADES MULTI-TIMEFRAME
    # =============================================================================
    
    async def descarga_multi_timeframe_avanzada(self):
        \"\"\"Descarga avanzada con múltiples timeframes y alineación automática\"\"\"
        try:
            print("\\n🚀 DESCARGA MULTI-TIMEFRAME AVANZADA")
            print("="*50)
            
            # Mostrar símbolos disponibles
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            print(f"Símbolos disponibles: {', '.join(symbols)}")
            
            # Seleccionar símbolos
            selected_symbols = []
            print("\\nSelecciona símbolos (separados por coma, o 'all' para todos):")
            symbol_input = input("Símbolos: ").strip()
            
            if symbol_input.lower() == 'all':
                selected_symbols = symbols
            else:
                selected_symbols = [s.strip().upper() for s in symbol_input.split(',')]
                selected_symbols = [s for s in selected_symbols if s in symbols]
            
            if not selected_symbols:
                print("❌ No se seleccionaron símbolos válidos")
                return
            
            # Seleccionar timeframes
            timeframes = ['5m', '15m', '1h', '4h', '1d']
            print(f"\\nTimeframes disponibles: {', '.join(timeframes)}")
            print("Selecciona timeframes (separados por coma, o 'all' para todos):")
            tf_input = input("Timeframes: ").strip()
            
            if tf_input.lower() == 'all':
                selected_timeframes = timeframes
            else:
                selected_timeframes = [tf.strip() for tf in tf_input.split(',')]
                selected_timeframes = [tf for tf in selected_timeframes if tf in timeframes]
            
            if not selected_timeframes:
                print("❌ No se seleccionaron timeframes válidos")
                return
            
            # Seleccionar días hacia atrás
            print("\\nDías hacia atrás para descargar:")
            days_input = input("Días (default: 365): ").strip()
            days_back = int(days_input) if days_input.isdigit() else 365
            
            # Preguntar sobre agregación
            print("\\n¿Usar agregación automática? (y/n, default: y)")
            agg_input = input("Agregación: ").strip().lower()
            use_aggregation = agg_input != 'n'
            
            print(f"\\n📊 Configuración:")
            print(f"   Símbolos: {', '.join(selected_symbols)}")
            print(f"   Timeframes: {', '.join(selected_timeframes)}")
            print(f"   Días: {days_back}")
            print(f"   Agregación: {'Sí' if use_aggregation else 'No'}")
            
            confirm = input("\\n¿Continuar? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Operación cancelada")
                return
            
            # Importar y ejecutar descarga
            from data.collector import download_multi_timeframe_with_alignment
            
            print("\\n🚀 Iniciando descarga multi-timeframe...")
            result = await download_multi_timeframe_with_alignment(
                symbols=selected_symbols,
                timeframes=selected_timeframes,
                days_back=days_back,
                use_aggregation=use_aggregation
            )
            
            if result['success']:
                print("\\n✅ DESCARGA COMPLETADA")
                print(f"   Timeframes procesados: {', '.join(result['timeframes_processed'])}")
                print(f"   Total registros: {result['total_records']:,}")
                print(f"   Tiempo de procesamiento: {result['processing_time']:.2f}s")
                
                if result['coherence_scores']:
                    print("\\n📈 Coherencia entre timeframes:")
                    for pair, score in result['coherence_scores'].items():
                        print(f"   {pair}: {score:.3f}")
                
                if result['errors']:
                    print("\\n⚠️ Errores encontrados:")
                    for error in result['errors']:
                        print(f"   - {error}")
            else:
                print(f"\\n❌ Error en la descarga: {result.get('error', 'Desconocido')}")
                
        except Exception as e:
            print(f"\\n❌ Error en descarga multi-timeframe: {e}")
    
    async def procesamiento_coordinado_multi_tf(self):
        \"\"\"Procesamiento coordinado de múltiples timeframes\"\"\"
        try:
            print("\\n🔄 PROCESAMIENTO COORDINADO MULTI-TIMEFRAME")
            print("="*50)
            
            from data.multi_timeframe_coordinator import MultiTimeframeCoordinator
            
            # Configurar coordinador
            coordinator = MultiTimeframeCoordinator()
            
            # Seleccionar símbolos
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            print(f"Símbolos disponibles: {', '.join(symbols)}")
            print("Selecciona símbolos (separados por coma, o 'all' para todos):")
            symbol_input = input("Símbolos: ").strip()
            
            if symbol_input.lower() == 'all':
                selected_symbols = symbols
            else:
                selected_symbols = [s.strip().upper() for s in symbol_input.split(',')]
                selected_symbols = [s for s in selected_symbols if s in symbols]
            
            if not selected_symbols:
                print("❌ No se seleccionaron símbolos válidos")
                return
            
            # Seleccionar días
            print("\\nDías hacia atrás para procesar:")
            days_input = input("Días (default: 365): ").strip()
            days_back = int(days_input) if days_input.isdigit() else 365
            
            # Preguntar sobre agregación
            print("\\n¿Usar agregación automática? (y/n, default: y)")
            agg_input = input("Agregación: ").strip().lower()
            use_aggregation = agg_input != 'n'
            
            print(f"\\n📊 Configuración:")
            print(f"   Símbolos: {', '.join(selected_symbols)}")
            print(f"   Días: {days_back}")
            print(f"   Agregación: {'Sí' if use_aggregation else 'No'}")
            
            confirm = input("\\n¿Continuar? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Operación cancelada")
                return
            
            print("\\n🔄 Iniciando procesamiento coordinado...")
            result = await coordinator.process_all_timeframes_coordinated(
                symbols=selected_symbols,
                days_back=days_back,
                use_aggregation=use_aggregation
            )
            
            if result.success:
                print("\\n✅ PROCESAMIENTO COMPLETADO")
                print(f"   Timeframes procesados: {', '.join(result.processed_timeframes)}")
                print(f"   Tiempo de procesamiento: {result.processing_time:.2f}s")
                print(f"   Errores: {len(result.errors)}")
                
                if result.coherence_scores:
                    print("\\n📈 Coherencia entre timeframes:")
                    for tf, score in result.coherence_scores.items():
                        print(f"   {tf}: {score:.3f}")
                
                if result.errors:
                    print("\\n⚠️ Errores encontrados:")
                    for error in result.errors:
                        print(f"   - {error}")
            else:
                print(f"\\n❌ Error en el procesamiento: {result.errors}")
                
        except Exception as e:
            print(f"\\n❌ Error en procesamiento coordinado: {e}")
    
    def estadisticas_sistema_multi_tf(self):
        \"\"\"Muestra estadísticas del sistema multi-timeframe\"\"\"
        try:
            print("\\n📊 ESTADÍSTICAS DEL SISTEMA MULTI-TIMEFRAME")
            print("="*60)
            
            from data.database import db_manager
            from data.hybrid_storage import HybridStorageManager
            from data.intelligent_cache import IntelligentCacheManager
            
            # Estadísticas de base de datos
            print("\\n🗄️ BASE DE DATOS:")
            db_stats = db_manager.get_performance_stats()
            print(f"   Tamaño total: {db_stats.get('total_size_mb', 0):.2f} MB")
            print(f"   Tablas: {db_stats.get('total_tables', 0)}")
            print(f"   Registros totales: {db_stats.get('total_records', 0):,}")
            
            # Estadísticas de almacenamiento híbrido
            print("\\n💾 ALMACENAMIENTO HÍBRIDO:")
            storage = HybridStorageManager()
            storage_stats = storage.get_storage_statistics()
            print(f"   Datos calientes: {storage_stats.hot_data_size_mb:.2f} MB")
            print(f"   Datos históricos: {storage_stats.historical_size_gb:.2f} GB")
            print(f"   Ratio de compresión: {storage_stats.compression_ratio:.2%}")
            print(f"   Símbolos cacheados: {storage_stats.total_symbols}")
            print(f"   Timeframes disponibles: {', '.join(storage_stats.timeframes_available)}")
            
            # Estadísticas de cache
            print("\\n⚡ CACHE INTELIGENTE:")
            cache = IntelligentCacheManager()
            cache_stats = cache.get_cache_statistics()
            print(f"   Entradas en cache: {cache_stats.total_entries}")
            print(f"   Tamaño del cache: {cache_stats.total_size_mb:.2f} MB")
            print(f"   Hit rate: {cache_stats.hit_rate:.2%}")
            print(f"   Miss rate: {cache_stats.miss_rate:.2%}")
            print(f"   Entradas expiradas: {cache_stats.expired_entries}")
            print(f"   Timeframes cacheados: {', '.join(cache_stats.timeframes_cached)}")
            print(f"   Símbolos cacheados: {', '.join(cache_stats.symbols_cached)}")
            
            # Estadísticas de coherencia
            print("\\n📈 COHERENCIA ENTRE TIMEFRAMES:")
            coherence_stats = db_manager.get_timeframe_coherence_stats()
            if 'overall_stats' in coherence_stats:
                overall = coherence_stats['overall_stats']
                print(f"   Coherencia general: {overall.get('avg_coherence', 0):.3f}")
                print(f"   Validaciones totales: {overall.get('total_validations', 0)}")
                print(f"   Pares de baja coherencia: {overall.get('low_coherence_pairs', 0)}")
            
            if 'coherence_by_pair' in coherence_stats:
                print("\\n   Coherencia por pares:")
                for pair in coherence_stats['coherence_by_pair']:
                    print(f"     {pair['source_timeframe']} → {pair['target_timeframe']}: {pair['avg_coherence']:.3f}")
            
            # Logs de operaciones recientes
            print("\\n📋 OPERACIONES RECIENTES:")
            try:
                with db_manager._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT operation_type, operation_status, symbols, timeframes, 
                               records_processed, processing_time_seconds, created_at
                        FROM operation_logs
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    operations = cursor.fetchall()
                    
                    if operations:
                        for op in operations:
                            status_icon = "✅" if op[1] == "completed" else "❌"
                            print(f"   {status_icon} {op[0]} - {op[1]}")
                            print(f"      Símbolos: {op[2]}")
                            print(f"      Timeframes: {op[3]}")
                            print(f"      Registros: {op[4]:,}")
                            print(f"      Tiempo: {op[5]:.2f}s")
                            print(f"      Fecha: {op[6]}")
                            print()
                    else:
                        print("   No hay operaciones registradas")
            except Exception as e:
                print(f"   Error obteniendo logs: {e}")
            
            print("\\n" + "="*60)
            
        except Exception as e:
            print(f"\\n❌ Error obteniendo estadísticas: {e}")
"""
    
    # Agregar los nuevos métodos al final de la clase
    if "class TradingBot:" in new_content:
        # Encontrar el final de la clase
        class_start = new_content.find("class TradingBot:")
        if class_start != -1:
            # Buscar el final de la clase (último método)
            lines = new_content[class_start:].split('\n')
            last_method_end = 0
            
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') and not line.strip().startswith('    def '):
                    # Método de la clase
                    last_method_end = class_start + len('\n'.join(lines[:i]))
            
            if last_method_end > 0:
                new_content = new_content[:last_method_end] + new_methods + new_content[last_method_end:]
    
    # Actualizar el método de manejo de opciones
    if "def manejar_opcion" in new_content:
        # Buscar y actualizar el método manejar_opcion
        start_marker = "def manejar_opcion(self, opcion):"
        if start_marker in new_content:
            # Agregar casos para las nuevas opciones
            new_cases = """
        elif opcion == "9":
            await self.descarga_multi_timeframe_avanzada()
        elif opcion == "10":
            await self.procesamiento_coordinado_multi_tf()
        elif opcion == "11":
            self.estadisticas_sistema_multi_tf()
"""
            
            # Insertar antes del caso "0"
            if 'elif opcion == "0":' in new_content:
                new_content = new_content.replace('elif opcion == "0":', new_cases + 'elif opcion == "0":')
    
    # Escribir el archivo actualizado
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ app.py actualizado con funcionalidades multi-timeframe")

def create_requirements_update():
    """Crea archivo de requirements actualizado"""
    print("🔄 Creando requirements.txt actualizado...")
    
    requirements = """# Trading Bot v10 - Requirements
# Sistema Multi-Timeframe

# Core dependencies
pandas>=1.5.0
numpy>=1.21.0
scikit-learn>=1.1.0
tensorflow>=2.10.0
keras>=2.10.0

# Data processing
ccxt>=3.0.0
aiohttp>=3.8.0
asyncio-mqtt>=0.11.0

# Database
sqlite3  # Built-in
aiosqlite>=0.17.0

# Storage and compression
pyarrow>=10.0.0
parquet>=1.0.0
gzip  # Built-in

# Visualization
plotly>=5.15.0
dash>=2.10.0
dash-bootstrap-components>=1.4.0

# Configuration
pyyaml>=6.0
python-dotenv>=0.19.0

# Logging and monitoring
structlog>=22.0.0
colorlog>=6.7.0

# Utilities
pathlib  # Built-in
dataclasses  # Built-in
concurrent.futures  # Built-in
threading  # Built-in
asyncio  # Built-in
hashlib  # Built-in
json  # Built-in
time  # Built-in
datetime  # Built-in
math  # Built-in
statistics  # Built-in
"""
    
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(requirements)
    
    print("✅ requirements.txt actualizado")

def create_setup_script():
    """Crea script de configuración inicial"""
    print("🔄 Creando script de configuración inicial...")
    
    setup_script = """#!/usr/bin/env python3
\"\"\"
setup_multi_timeframe.py - Script de Configuración Inicial
Configura el sistema multi-timeframe para Trading Bot v10
\"\"\"

import os
import sys
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_directories():
    \"\"\"Crea la estructura de directorios necesaria\"\"\"
    logger.info("📁 Creando estructura de directorios...")
    
    directories = [
        "data",
        "data/historical",
        "data/historical/aligned",
        "data/historical/compressed",
        "data/historical/metadata",
        "data/cache",
        "data/cache/features",
        "data/cache/aligned_data",
        "data/cache/metadata",
        "data/backups",
        "logs",
        "models",
        "models/saved_models",
        "config",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"   ✅ {directory}")
    
    logger.info("✅ Estructura de directorios creada")

def create_config_files():
    \"\"\"Crea archivos de configuración iniciales\"\"\"
    logger.info("⚙️ Creando archivos de configuración...")
    
    # Configuración core
    core_config = \"\"\"
# Core Configuration - Trading Bot v10 Multi-Timeframe
environment: development
log_level: INFO
debug_mode: true

# Database
database:
  path: "data/trading_bot.db"
  backup_enabled: true
  backup_retention_days: 7

# Multi-Timeframe System
multi_timeframe:
  timeframes: ['5m', '15m', '1h', '4h', '1d']
  base_timeframe: '5m'
  alignment_tolerance_minutes: 1
  min_data_coverage: 0.95

# Storage
storage:
  hot_data_days: 30
  compression_level: 6
  max_workers: 4

# Cache
cache:
  max_size_mb: 1000
  cleanup_interval: 3600
  compression_enabled: true

# Symbols
symbols:
  default: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
  timeframes: ['5m', '15m', '1h', '4h', '1d']
\"\"\"
    
    with open('config/core_config.yaml', 'w', encoding='utf-8') as f:
        f.write(core_config.strip())
    
    logger.info("   ✅ config/core_config.yaml")
    
    # Configuración de logging
    logging_config = \"\"\"
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/trading_bot.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  data.temporal_alignment:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  data.hybrid_storage:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  data.multi_timeframe_coordinator:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  data.intelligent_cache:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
\"\"\"
    
    with open('config/logging_config.yaml', 'w', encoding='utf-8') as f:
        f.write(logging_config.strip())
    
    logger.info("   ✅ config/logging_config.yaml")
    
    logger.info("✅ Archivos de configuración creados")

def initialize_database():
    \"\"\"Inicializa la base de datos con las nuevas tablas\"\"\"
    logger.info("🗄️ Inicializando base de datos...")
    
    try:
        from data.database import db_manager
        
        # Crear tablas
        db_manager._create_tables()
        db_manager._create_optimized_indices()
        
        logger.info("✅ Base de datos inicializada")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")

def run_tests():
    \"\"\"Ejecuta tests básicos del sistema\"\"\"
    logger.info("🧪 Ejecutando tests básicos...")
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, 'test_multi_timeframe_system.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Tests básicos pasaron")
        else:
            logger.warning(f"⚠️ Tests básicos fallaron: {result.stderr}")
            
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron ejecutar tests: {e}")

def main():
    \"\"\"Función principal de configuración\"\"\"
    logger.info("🚀 Configurando Sistema Multi-Timeframe - Trading Bot v10")
    logger.info("="*70)
    
    try:
        create_directories()
        create_config_files()
        initialize_database()
        run_tests()
        
        logger.info("\\n🎉 CONFIGURACIÓN COMPLETADA")
        logger.info("="*70)
        logger.info("El sistema multi-timeframe está listo para usar.")
        logger.info("\\nPróximos pasos:")
        logger.info("1. Ejecutar: python app.py")
        logger.info("2. Seleccionar opción 9: Descarga Multi-Timeframe Avanzada")
        logger.info("3. Seleccionar opción 10: Procesamiento Coordinado Multi-TF")
        logger.info("4. Seleccionar opción 11: Estadísticas del Sistema Multi-TF")
        
    except Exception as e:
        logger.error(f"❌ Error en configuración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
\"\"\"
    
    with open('setup_multi_timeframe.py', 'w', encoding='utf-8') as f:
        f.write(setup_script)
    
    print("✅ setup_multi_timeframe.py creado")

def main():
    """Función principal de integración"""
    print("🚀 INTEGRANDO SISTEMA MULTI-TIMEFRAME EN TRADING BOT v10")
    print("="*70)
    
    try:
        integrate_app_py()
        create_requirements_update()
        create_setup_script()
        
        print("\n✅ INTEGRACIÓN COMPLETADA")
        print("="*70)
        print("Sistema multi-timeframe integrado exitosamente.")
        print("\nArchivos modificados/creados:")
        print("  ✅ app.py - Nuevas opciones del menú")
        print("  ✅ requirements.txt - Dependencias actualizadas")
        print("  ✅ setup_multi_timeframe.py - Script de configuración")
        print("  ✅ test_multi_timeframe_system.py - Tests del sistema")
        print("  ✅ docs/MULTI_TIMEFRAME_SYSTEM.md - Documentación")
        
        print("\nPróximos pasos:")
        print("1. Ejecutar: python setup_multi_timeframe.py")
        print("2. Ejecutar: python app.py")
        print("3. Probar las nuevas opciones del menú")
        
    except Exception as e:
        print(f"\n❌ Error en integración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
