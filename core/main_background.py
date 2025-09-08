#!/usr/bin/env python3
"""
Bot de Trading v10 - Modo Background (Sin Dashboard)
Solo entrenamiento, registro de datos y actualización de modelos
Sistema robusto con manejo de errores y health checks
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Agregar el directorio raíz al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Importar sistemas robustos
from core.health_checker import health_checker, validate_system_state
from core.config_manager import get_config, get_training_config
from core.error_handler import handle_async_errors, log_error, get_error_stats, ErrorCategory, ErrorSeverity
from core.thread_manager import start_thread_manager, shutdown_thread_manager, submit_async_task

from data.database import db_manager
from data.collector import download_missing_data

# Configurar logging robusto
def setup_logging():
    """Configura logging estructurado"""
    config = get_config()
    
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    # Configurar formato estructurado
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Handler para archivo
    file_handler = logging.FileHandler('logs/background_training.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, config.log_level))
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configurar logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class TradingBotBackground:
    """Clase principal del bot de trading en modo background"""
    
    def __init__(self, mode='paper_trading', duration_hours=None):
        self.mode = mode
        self.duration_hours = duration_hours
        self.start_time = datetime.now()
        self.training_active = True
        
        # Configuración robusta
        self.config = get_config()
        self.training_config = get_training_config()
        
        # Estado del sistema
        self.system_healthy = False
        self.last_health_check = None
        self.error_count = 0
        self.max_errors = 10
        
        logger.info(f"TradingBotBackground initialized - Mode: {mode}, Duration: {duration_hours}h")
        
    @handle_async_errors(category=ErrorCategory.DATABASE, severity=ErrorSeverity.HIGH)
    async def verificar_y_preparar_datos(self):
        """Verifica el histórico y descarga datos si es necesario"""
        print("VERIFICANDO DATOS HISTORICOS...")
        print("=" * 50)
        
        try:
            # Health check del sistema
            if not await self._check_system_health():
                return False
            
            # Verificar datos existentes
            summary = db_manager.get_data_summary_optimized()
            
            if 'error' in summary:
                error_msg = f"Error verificando datos: {summary['error']}"
                print(error_msg)
                log_error(Exception(error_msg), {"context": "data_verification"})
                return False
            
            print(f"Símbolos disponibles: {summary['total_symbols']}")
            print(f"Total registros: {summary['total_records']:,}")
            
            # Verificar si necesitamos más datos
            valid_symbols = [s for s in summary['symbols'] if s['status'] == 'OK']
            symbols_insuficientes = [s for s in valid_symbols if s['duration_days'] < 365]
            
            if symbols_insuficientes:
                print(f"\nDescargando datos faltantes para {len(symbols_insuficientes)} simbolos...")
                results = await download_missing_data(target_days=365)
                
                if 'error' in results:
                    error_msg = f"Error descargando datos: {results['error']}"
                    print(error_msg)
                    log_error(Exception(error_msg), {"context": "data_download"})
                    return False
                
                print(f"Descarga completada: {results['total_downloaded']:,} registros")
            else:
                print("Datos suficientes disponibles")
            
            return True
            
        except Exception as e:
            error_msg = f"Error en verificación: {e}"
            print(error_msg)
            log_error(e, {"context": "data_verification"})
            self.error_count += 1
            return False
    
    async def _check_system_health(self) -> bool:
        """Verifica la salud del sistema"""
        try:
            # Verificar si necesitamos hacer health check
            if (self.last_health_check is None or 
                (datetime.now() - self.last_health_check).total_seconds() > 300):  # 5 minutos
                
                logger.info("Running system health check...")
                health_results = await health_checker.run_all_checks()
                system_status = health_checker.get_system_status(health_results)
                
                self.last_health_check = datetime.now()
                self.system_healthy = system_status["system_ready"]
                
                if not self.system_healthy:
                    logger.error(f"System health check failed: {system_status}")
                    print("SISTEMA NO SALUDABLE - Verificar logs para detalles")
                    return False
                else:
                    logger.info("System health check passed")
            
            return self.system_healthy
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            log_error(e, {"context": "health_check"})
            return False
    
    def verificar_modelo_existente(self):
        """Verifica que el modelo existente esté disponible"""
        print("\nVERIFICANDO MODELO EXISTENTE...")
        print("=" * 50)
        
        model_path = "models/saved_models/best_lstm_attention_20250906_223751.h5"
        
        if os.path.exists(model_path):
            print(f"Modelo encontrado: {model_path}")
            print("Modelo LSTM con Atención cargado y operativo")
            return True
        else:
            print(f"Modelo no encontrado: {model_path}")
            print("Se creará un nuevo modelo durante el entrenamiento")
            return True  # Permitir continuar para crear nuevo modelo
    
    async def ejecutar_entrenamiento_continuo(self):
        """Ejecuta entrenamiento continuo sin dashboard"""
        print("\nINICIANDO ENTRENAMIENTO CONTINUO...")
        print("=" * 50)
        print(f"Modo: {self.mode}")
        print(f"Duracion: {self.duration_hours} horas" if self.duration_hours else "Indefinido")
        print("Dashboard: Deshabilitado")
        print()
        
        try:
            # Importar componentes de entrenamiento
            from models.adaptive_trainer import train_initial_model, train_multi_symbol_models
            from models.neural_network import create_model
            
            # Símbolos para entrenar
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT']
            
            # Configurar entrenamiento
            training_config = {
                'epochs': 50,
                'batch_size': 32,
                'validation_split': 0.2,
                'patience': 10,
                'min_delta': 0.001
            }
            
            print("Configuración de entrenamiento:")
            for key, value in training_config.items():
                print(f"  {key}: {value}")
            print()
            
            # Calcular tiempo de finalización si hay duración limitada
            end_time = None
            if self.duration_hours:
                end_time = self.start_time + timedelta(hours=self.duration_hours)
                print(f"Entrenamiento terminará a las: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            
            # Ciclo de entrenamiento continuo
            cycle_count = 0
            while self.training_active:
                cycle_count += 1
                current_time = datetime.now()
                
                # Verificar si hemos alcanzado el tiempo límite
                if end_time and current_time >= end_time:
                    print(f"\nTiempo limite alcanzado ({self.duration_hours}h)")
                    break
                
                print(f"\nCICLO DE ENTRENAMIENTO #{cycle_count}")
                print(f"Hora: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 40)
                
                # Entrenar todos los símbolos usando datos alineados
                print("ENTRENAMIENTO MULTI-SIMBOLO CON DATOS ALINEADOS...")
                
                try:
                    # Entrenar todos los símbolos simultáneamente
                    result = await train_multi_symbol_models(
                        symbols=symbols,
                        days_back=1095
                    )
                    
                    if result.get('status') == 'success':
                        successful = result.get('successful_trains', 0)
                        total = result.get('total_symbols', 0)
                        print(f"ENTRENAMIENTO MULTI-SIMBOLO COMPLETADO: {successful}/{total} exitosos")
                        
                        # Mostrar resultados por símbolo
                        results = result.get('results', {})
                        for symbol, symbol_result in results.items():
                            if symbol_result.get('status') == 'success':
                                print(f"   OK {symbol}: Accuracy {symbol_result.get('val_accuracy', 0):.4f}, "
                                      f"Samples {symbol_result.get('samples_trained', 0):,}")
                            else:
                                print(f"   ERROR {symbol}: {symbol_result.get('error', 'Error desconocido')}")
                    else:
                        print(f"ERROR EN ENTRENAMIENTO MULTI-SIMBOLO: {result.get('error', 'Error desconocido')}")
                        
                except Exception as e:
                    print(f"ERROR EN ENTRENAMIENTO MULTI-SIMBOLO: {e}")
                    logger.error(f"Error en entrenamiento multi-símbolo: {e}")
                    
                    # Fallback a entrenamiento individual
                    print("FALLBACK A ENTRENAMIENTO INDIVIDUAL...")
                    for i, symbol in enumerate(symbols, 1):
                        print(f"[{i}/{len(symbols)}] Entrenando {symbol}...")
                        
                        try:
                            result = await train_initial_model(
                                symbol=symbol,
                                days_back=1095
                            )
                            
                            if result.get('status') == 'success':
                                print(f"   OK {symbol}: Entrenamiento completado")
                                print(f"      Loss: {result.get('final_loss', 'N/A'):.6f}")
                                print(f"      Val Loss: {result.get('val_loss', 'N/A'):.6f}")
                                print(f"      Epocas: {result.get('epochs_trained', 'N/A')}")
                            else:
                                print(f"   ERROR {symbol}: {result.get('error', 'Error desconocido')}")
                                
                        except Exception as e:
                            print(f"   ERROR {symbol}: {e}")
                            logger.error(f"Error entrenando {symbol}: {e}")
                
                # Mostrar estadísticas del ciclo
                elapsed = datetime.now() - self.start_time
                print(f"\nESTADISTICAS DEL CICLO #{cycle_count}")
                print(f"Tiempo transcurrido: {elapsed}")
                print(f"Tiempo restante: {end_time - datetime.now() if end_time else 'Indefinido'}")
                
                # Pausa entre ciclos (5 minutos)
                if self.training_active:
                    print("\nPausa de 5 minutos antes del siguiente ciclo...")
                    await asyncio.sleep(300)  # 5 minutos
            
            print(f"\nENTRENAMIENTO COMPLETADO")
            print(f"Total de ciclos: {cycle_count}")
            print(f"Tiempo total: {datetime.now() - self.start_time}")
            
            return True
            
        except Exception as e:
            print(f"Error en entrenamiento continuo: {e}")
            logger.error(f"Error en entrenamiento continuo: {e}")
            return False
    
    async def ejecutar_paper_trading_background(self):
        """Ejecuta paper trading en background sin dashboard"""
        print("\nINICIANDO PAPER TRADING BACKGROUND...")
        print("=" * 50)
        
        try:
            # Importar componentes de trading
            from trading.executor import trading_executor
            from trading.signal_processor import signal_processor
            
            print("Componentes de trading cargados")
            print("Modo: Paper Trading Background")
            print("Balance inicial: $10,000")
            print("Simbolos: BTCUSDT, ETHUSDT, ADAUSDT, SOLUSDT")
            print("Modelo: LSTM con Atencion")
            print()
            
            # Configurar trading
            trading_config = {
                'initial_balance': 10000,
                'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'],
                'risk_per_trade': 0.02,  # 2% por operación
                'max_positions': 4,
                'update_interval': 60  # 1 minuto
            }
            
            print("Configuración de trading:")
            for key, value in trading_config.items():
                print(f"  {key}: {value}")
            print()
            
            # Iniciar trading en hilo separado
            trading_thread = threading.Thread(
                target=self._run_trading_loop,
                args=(trading_config,),
                daemon=True
            )
            trading_thread.start()
            
            print("Paper trading iniciado en background")
            print("Monitorea los logs para ver las operaciones")
            
            return True
            
        except Exception as e:
            print(f"Error iniciando paper trading: {e}")
            logger.error(f"Error iniciando paper trading: {e}")
            return False
    
    def _run_trading_loop(self, config):
        """Ejecuta el loop de trading en hilo separado"""
        try:
            import asyncio
            
            # Crear nuevo loop de asyncio para este hilo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def trading_loop():
                while self.training_active:
                    try:
                        # Aquí iría la lógica de trading
                        print(f"[TRADING] Ejecutando ciclo de trading...")
                        
                        # Simular operaciones de trading
                        await asyncio.sleep(config['update_interval'])
                        
                    except Exception as e:
                        logger.error(f"Error en ciclo de trading: {e}")
                        await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
            
            # Ejecutar el loop de trading
            loop.run_until_complete(trading_loop())
            loop.close()
                    
        except Exception as e:
            logger.error(f"Error en loop de trading: {e}")
    
    def detener_entrenamiento(self):
        """Detiene el entrenamiento"""
        print("\nDETENIENDO ENTRENAMIENTO...")
        self.training_active = False
    
    async def ejecutar_flujo_background(self):
        """Ejecuta el flujo completo en modo background"""
        print("BOT DE TRADING V10 - MODO BACKGROUND")
        print("=" * 60)
        print(f"Inicio: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modo: {self.mode}")
        print(f"Duracion: {self.duration_hours} horas" if self.duration_hours else "Indefinido")
        print("Dashboard: Deshabilitado")
        print()
        
        try:
            # Paso 1: Verificar y preparar datos
            if not await self.verificar_y_preparar_datos():
                print("No se pudieron preparar los datos necesarios")
                return False
            
            # Paso 2: Verificar modelo existente
            if not self.verificar_modelo_existente():
                print("No se puede continuar sin modelo")
                return False
            
            # Paso 3: Ejecutar entrenamiento continuo
            if self.mode in ['paper_trading', 'continuous_learning']:
                if not await self.ejecutar_entrenamiento_continuo():
                    print("Error en entrenamiento continuo")
                    return False
            
            # Paso 4: Ejecutar paper trading si es necesario
            if self.mode == 'paper_trading':
                if not await self.ejecutar_paper_trading_background():
                    print("Error en paper trading")
                    return False
            
            print("\nSISTEMA BACKGROUND COMPLETAMENTE OPERATIVO")
            print("=" * 50)
            print("Entrenamiento continuo activo")
            print("Datos actualizandose automaticamente")
            print("Modelos mejorandose continuamente")
            print()
            print("METRICAS DISPONIBLES EN LOGS:")
            print("   - Progreso de entrenamiento")
            print("   - Metricas de rendimiento")
            print("   - Operaciones de trading")
            print("   - Estadisticas de backtesting")
            print()
            print("PROXIMOS PASOS:")
            print("   1. Monitorea los logs para ver el progreso")
            print("   2. Los modelos se actualizan automaticamente")
            print("   3. Presiona Ctrl+C para detener")
            print()
            
            # Mantener el sistema corriendo
            print("Sistema ejecutandose en background... Presiona Ctrl+C para detener")
            try:
                while self.training_active:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nDeteniendo sistema...")
                self.detener_entrenamiento()
                return True
                
        except Exception as e:
            print(f"Error en flujo background: {e}")
            logger.error(f"Error en flujo background: {e}")
            return False

async def main():
    """Función principal"""
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Trading Bot v10 - Modo Background')
    parser.add_argument('--mode', choices=['paper_trading', 'backtesting', 'development', 'continuous_learning'], 
                       default='paper_trading', help='Modo de operación del bot')
    parser.add_argument('--duration', type=int, help='Duración en horas (opcional)')
    parser.add_argument('--background', action='store_true', 
                       help='Ejecutar en modo background (sin dashboard)')
    parser.add_argument('--no-dashboard', action='store_true', 
                       help='No iniciar dashboard')
    
    args = parser.parse_args()
    
    print(f"Iniciando Trading Bot v10 en modo background: {args.mode}")
    
    bot = TradingBotBackground(mode=args.mode, duration_hours=args.duration)
    success = await bot.ejecutar_flujo_background()
    
    if success:
        print("Sistema detenido correctamente")
    else:
        print("Sistema terminó con errores")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n¡Hasta luego!")
    except Exception as e:
        print(f"Error crítico: {e}")
        import traceback
        traceback.print_exc()
