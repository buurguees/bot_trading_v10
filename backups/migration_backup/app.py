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
        print("4. 🔄 Alinear datos históricos (Multi-símbolo)")
        print("5. 🚀 Empezar entrenamiento + Dashboard")
        print("6. 🤖 Entrenamiento sin Dashboard (Background)")
        print("7. 📈 Análisis de performance")
        print("8. ⚙️  Configurar sistema")
        print("9. 🧪 Modo de pruebas rápidas")
        print("10. 📱 Estado del sistema")
        print("11. ❌ Salir")
        print()
    
    def get_user_choice(self) -> str:
        """Obtiene la elección del usuario"""
        try:
            choice = input("Selecciona una opción (1-11): ").strip()
            return choice
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            return "10"
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
                is_calibrated = conf_health.get('is_calibrated', False)
                print(f"\n💪 Estimador de confianza:")
                print(f"   Calibrado: {'✅ Sí' if is_calibrated else '❌ No'}")
                print(f"   Última calibración: {conf_health.get('last_calibration', 'Nunca')}")
                
                # Si no está calibrado, calibrar automáticamente
                if not is_calibrated:
                    print(f"\n🔧 Calibrando estimador de confianza...")
                    calibration_result = await confidence_estimator.calibrate()
                    if calibration_result.get('status') == 'success':
                        print(f"   ✅ Calibración exitosa: {calibration_result.get('calibration_samples', 0)} muestras")
                        print(f"   📊 Puntos de datos: {calibration_result.get('calibration_data_points', 0)}")
                    else:
                        print(f"   ❌ Error en calibración: {calibration_result.get('error', 'Desconocido')}")
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
                    count = db_manager.get_market_data_count_fast(symbol)
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
    
    async def align_historical_data(self):
        """Opción 4: Alinear datos históricos para análisis multi-símbolo"""
        print("\n🔄 ALINEACIÓN DE DATOS HISTÓRICOS")
        print("=" * 45)
        print("Esta función sincroniza los datos de todos los símbolos")
        print("para permitir análisis simultáneo y trading multi-símbolo.")
        print()
        
        try:
            from core.manage_data import DataManager
            from data.database import db_manager
            import pandas as pd
            from datetime import datetime, timedelta
            
            # Obtener símbolos
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            timeframes = ['1h', '4h', '1d']
            
            print("🔍 Analizando datos existentes...")
            
            # Analizar cobertura de datos por símbolo y timeframe
            coverage_analysis = {}
            min_start_date = None
            max_end_date = None
            
            for symbol in symbols:
                coverage_analysis[symbol] = {}
                try:
                    # Obtener datos directamente con SQL
                    with db_manager._get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Obtener conteo y rango de fechas
                        cursor.execute("""
                            SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
                            FROM market_data 
                            WHERE symbol = ?
                        """, (symbol,))
                        
                        count, min_ts, max_ts = cursor.fetchone()
                        
                        if count > 0 and min_ts and max_ts:
                            # Convertir timestamps (verificar si son segundos o milisegundos)
                            try:
                                # Probar si es timestamp en segundos
                                start_date = datetime.fromtimestamp(min_ts)
                                end_date = datetime.fromtimestamp(max_ts)
                            except (ValueError, OSError):
                                try:
                                    # Probar si es timestamp en milisegundos
                                    start_date = datetime.fromtimestamp(min_ts / 1000)
                                    end_date = datetime.fromtimestamp(max_ts / 1000)
                                except (ValueError, OSError):
                                    print(f"   ⚠️ Timestamps inválidos para {symbol}: {min_ts}, {max_ts}")
                                    coverage_analysis[symbol] = None
                                    continue
                            
                            coverage_analysis[symbol] = {
                                'start': start_date,
                                'end': end_date,
                                'count': count
                            }
                            
                            # Encontrar el símbolo con el historial más lejano (referencia)
                            if min_start_date is None or start_date < min_start_date:
                                min_start_date = start_date
                                reference_symbol = symbol
                            
                            # Encontrar la fecha más reciente común
                            if max_end_date is None or end_date < max_end_date:
                                max_end_date = end_date
                        else:
                            coverage_analysis[symbol] = None
                                
                except Exception as e:
                    print(f"   ⚠️ Error analizando {symbol}: {e}")
                    coverage_analysis[symbol] = None
            
            print(f"\n📊 Análisis de cobertura:")
            print(f"   Símbolo de referencia: {reference_symbol if 'reference_symbol' in locals() else 'N/A'}")
            print(f"   Período de referencia: {min_start_date} a {max_end_date}")
            
            if min_start_date and max_end_date:
                common_duration = (max_end_date - min_start_date).days
                print(f"   Duración total: {common_duration} días")
            
            # Mostrar cobertura por símbolo
            print(f"\n📈 Cobertura por símbolo:")
            for symbol in symbols:
                print(f"\n   {symbol}:")
                if coverage_analysis[symbol]:
                    data = coverage_analysis[symbol]
                    print(f"     Registros: {data['count']:,}")
                    print(f"     Desde: {data['start'].strftime('%Y-%m-%d %H:%M')}")
                    print(f"     Hasta: {data['end'].strftime('%Y-%m-%d %H:%M')}")
                    duration = (data['end'] - data['start']).days
                    print(f"     Duración: {duration} días")
                else:
                    print(f"     ❌ Sin datos")
            
            # Crear datos alineados
            print(f"\n🔄 Creando datos alineados...")
            
            if min_start_date and max_end_date and 'reference_symbol' in locals():
                # Generar timestamps de referencia (cada hora desde el símbolo más antiguo)
                reference_timestamps = pd.date_range(
                    start=min_start_date,
                    end=max_end_date,
                    freq='H'  # Cada hora
                )
                
                print(f"   Timestamps de referencia: {len(reference_timestamps):,}")
                print(f"   Desde: {min_start_date.strftime('%Y-%m-%d %H:%M')}")
                print(f"   Hasta: {max_end_date.strftime('%Y-%m-%d %H:%M')}")
                
                # Crear DataFrame alineado
                aligned_data = {}
                
                for symbol in symbols:
                    print(f"\n   Procesando {symbol}...")
                    symbol_data = {}
                    
                    # Obtener datos del símbolo directamente con SQL
                    try:
                        with db_manager._get_connection() as conn:
                            cursor = conn.cursor()
                            
                            # Obtener datos del símbolo
                            cursor.execute("""
                                SELECT timestamp, open, high, low, close, volume
                                FROM market_data 
                                WHERE symbol = ? 
                                AND timestamp >= ? 
                                AND timestamp <= ?
                                ORDER BY timestamp
                            """, (symbol, int(min_start_date.timestamp()), int(max_end_date.timestamp())))
                            
                            results = cursor.fetchall()
                            
                            if results:
                                # Crear DataFrame
                                df = pd.DataFrame(results, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                                df.set_index('datetime', inplace=True)
                                df.drop('timestamp', axis=1, inplace=True)
                                
                                # Obtener fechas de inicio y fin del símbolo
                                symbol_start = df.index.min()
                                symbol_end = df.index.max()
                                
                                print(f"     Datos disponibles: {symbol_start.strftime('%Y-%m-%d')} a {symbol_end.strftime('%Y-%m-%d')}")
                                print(f"     Registros originales: {len(df):,}")
                                
                                # Crear timestamps alineados para este símbolo
                                # Comenzar desde donde empieza este símbolo, no desde la referencia
                                symbol_timestamps = pd.date_range(
                                    start=symbol_start,
                                    end=min(symbol_end, max_end_date),
                                    freq='h'  # Usar 'h' en lugar de 'H' para evitar warning
                                )
                                
                                print(f"     Timestamps del símbolo: {len(symbol_timestamps):,}")
                                
                                # Reindexar datos del símbolo a sus propios timestamps
                                aligned_df = df.reindex(symbol_timestamps, method='ffill')
                                
                                # Guardar datos alineados (usar '1h' como timeframe base)
                                symbol_data['1h'] = aligned_df
                                
                                print(f"     Registros alineados: {len(aligned_df):,}")
                                
                                # Crear timeframes adicionales por agregación
                                for tf in ['4h', '1d']:
                                    if tf == '4h':
                                        # Agregar a 4 horas
                                        tf_data = aligned_df.resample('4h').agg({
                                            'open': 'first',
                                            'high': 'max',
                                            'low': 'min',
                                            'close': 'last',
                                            'volume': 'sum'
                                        }).dropna()
                                    elif tf == '1d':
                                        # Agregar a 1 día
                                        tf_data = aligned_df.resample('1d').agg({
                                            'open': 'first',
                                            'high': 'max',
                                            'low': 'min',
                                            'close': 'last',
                                            'volume': 'sum'
                                        }).dropna()
                                    
                                    symbol_data[tf] = tf_data
                                    print(f"     {tf}: {len(tf_data):,} registros")
                                
                                aligned_data[symbol] = symbol_data
                                
                            else:
                                print(f"     ❌ Sin datos para alinear")
                                aligned_data[symbol] = {}
                            
                    except Exception as e:
                        print(f"     ❌ Error procesando {symbol}: {e}")
                        aligned_data[symbol] = {}
                
                # Guardar datos alineados
                print(f"\n💾 Guardando datos alineados...")
                
                # Crear tabla para datos alineados
                try:
                    with db_manager._get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Crear tabla si no existe
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS aligned_market_data (
                                id INTEGER PRIMARY KEY,
                                symbol TEXT NOT NULL,
                                timeframe TEXT NOT NULL,
                                timestamp INTEGER NOT NULL,
                                open REAL,
                                high REAL,
                                low REAL,
                                close REAL,
                                volume REAL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(symbol, timeframe, timestamp) ON CONFLICT REPLACE
                            )
                        """)
                        
                        # Crear índices
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_aligned_symbol_tf 
                            ON aligned_market_data(symbol, timeframe)
                        """)
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_aligned_timestamp 
                            ON aligned_market_data(timestamp)
                        """)
                        
                        conn.commit()
                
                except Exception as e:
                    print(f"   ⚠️ Error creando tabla alineada: {e}")
                    return
                
                # Insertar datos alineados
                total_inserted = 0
                
                for symbol, timeframes_data in aligned_data.items():
                    for tf, df in timeframes_data.items():
                        if not df.empty:
                            # Preparar datos para inserción
                            records = []
                            for timestamp, row in df.iterrows():
                                if pd.notna(row['close']):  # Solo filas con datos válidos
                                    records.append((
                                        symbol,
                                        tf,
                                        int(timestamp.timestamp()),
                                        float(row['open']) if pd.notna(row['open']) else None,
                                        float(row['high']) if pd.notna(row['high']) else None,
                                        float(row['low']) if pd.notna(row['low']) else None,
                                        float(row['close']) if pd.notna(row['close']) else None,
                                        float(row['volume']) if pd.notna(row['volume']) else None
                                    ))
                            
                            # Insertar en lotes
                            if records:
                                with db_manager._get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.executemany("""
                                        INSERT OR REPLACE INTO aligned_market_data 
                                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, records)
                                    conn.commit()
                                
                                total_inserted += len(records)
                                print(f"     {symbol}-{tf}: {len(records):,} registros insertados")
                
                print(f"\n✅ Alineación completada:")
                print(f"   Total registros alineados: {total_inserted:,}")
                print(f"   Símbolos procesados: {len(symbols)}")
                print(f"   Timeframes: {', '.join(timeframes)}")
                print(f"   Período: {min_start_date.strftime('%Y-%m-%d')} a {max_end_date.strftime('%Y-%m-%d')}")
                
                # Verificar datos alineados
                print(f"\n🔍 Verificando datos alineados...")
                with db_manager._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM aligned_market_data")
                    total_aligned = cursor.fetchone()[0]
                    print(f"   Total en tabla alineada: {total_aligned:,}")
                    
                    # Mostrar distribución por símbolo
                    cursor.execute("""
                        SELECT symbol, timeframe, COUNT(*) 
                        FROM aligned_market_data 
                        GROUP BY symbol, timeframe 
                        ORDER BY symbol, timeframe
                    """)
                    
                    print(f"\n📊 Distribución por símbolo:")
                    for symbol, tf, count in cursor.fetchall():
                        print(f"   {symbol}-{tf}: {count:,} registros")
                
            else:
                print("❌ No se pudo determinar un período común para alinear")
                
        except Exception as e:
            print(f"❌ Error alineando datos: {e}")
            logger.error(f"Error en alineación de datos: {e}")
        
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
            stats = db_manager.get_data_summary_optimized()
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
    
    async def start_training_background(self):
        """Opción 5: Entrenamiento sin Dashboard (Background)"""
        print("\n🤖 ENTRENAMIENTO SIN DASHBOARD (BACKGROUND)")
        print("=" * 50)
        
        try:
            # Verificar prerequisitos
            print("🔍 Verificando prerequisitos...")
            
            # Verificar datos
            from data.database import db_manager
            stats = db_manager.get_data_summary_optimized()
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
                
        except Exception as e:
            print(f"❌ Error iniciando entrenamiento: {e}")
            logger.error(f"Error en entrenamiento background: {e}")
        
        input("\nPresiona Enter para continuar...")
    
    def _select_background_training_mode(self) -> str:
        """Selecciona modo de entrenamiento para background"""
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
            import traceback
            traceback.print_exc()
    
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
            
            print(f"🚀 Ejecutando comando: {' '.join(cmd)}")
            print(f"📁 Directorio: {os.getcwd()}")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combinar stderr con stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.dashboard_process = process
            
            # Monitorear output
            print("📊 Iniciando monitoreo del dashboard...")
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[DASHBOARD] {line.strip()}")
                    
        except Exception as e:
            print(f"❌ Error en dashboard: {e}")
            import traceback
            traceback.print_exc()
    
    async def performance_analysis(self):
        """Opción 5: Análisis de performance"""
        print("\n📈 ANÁLISIS DE PERFORMANCE")
        print("=" * 30)
        
        try:
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
                    await self.align_historical_data()
                elif choice == "5":
                    await self.start_training_and_dashboard()
                elif choice == "6":
                    await self.start_training_background()
                elif choice == "7":
                    await self.performance_analysis()
                elif choice == "8":
                    await self.system_configuration()
                elif choice == "9":
                    await self.quick_tests()
                elif choice == "10":
                    await self.system_status()
                elif choice == "11":
                    self.running = False
                    print("\n👋 ¡Hasta luego!")
                else:
                    print("\n⚠️ Opción no válida. Por favor selecciona 1-11.")
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
    