"""
main.py
Punto de entrada principal del Trading Bot Autónomo v10
Ubicación: C:\TradingBot_v10\main.py

Este es el archivo principal que orquesta todo el sistema de trading.
Ejecutar con: python main.py
"""

import asyncio
import signal
import sys
import argparse
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import threading
import time
import numpy as np

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports del proyecto
from config.settings import config, Environment, setup_logging
from config.config_loader import user_config
from data.database import db_manager
from data.collector import data_collector, collect_and_save_historical_data
from data.preprocessor import data_preprocessor
from models.predictor import predictor
from trading.execution_engine import execution_engine
from trading.risk_manager import risk_manager
from trading.order_manager import order_manager
from agents.trading_agent import TradingAgent

logger = logging.getLogger(__name__)

class TradingBotOrchestrator:
    """Orquestador principal del bot de trading"""
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.running = False
        self.threads = []
        self.tasks = []
        
        # Configurar entorno
        config.environment = environment
        user_config.apply_to_base_config()
        
        # Configuración del bot
        self.bot_name = user_config.get_bot_name()
        self.symbol = user_config.get_trading_settings()['primary_symbol']
        
        # Inicializar Agente de IA
        self.ai_agent = TradingAgent()
        
        # Control de ciclo de vida
        self._stop_event = threading.Event()
        self._setup_signal_handlers()
        
        logger.info(f"🤖 {self.bot_name} inicializado en modo {environment.value}")
        logger.info(f"📊 Trading symbol: {self.symbol}")
        logger.info(f"🧠 Agente de IA: {self.ai_agent.__class__.__name__}")
    
    def _setup_signal_handlers(self):
        """Configura manejadores de señales para cierre limpio"""
        def signal_handler(signum, frame):
            logger.info(f"Recibida señal {signum}, iniciando cierre limpio...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def validate_configuration(self) -> bool:
        """Valida la configuración antes de iniciar"""
        try:
            logger.info("🔍 Validando configuración...")
            
            # Validar configuración base
            base_errors = config.validate_config()
            if base_errors:
                logger.error(f"Errores en configuración base: {base_errors}")
                return False
            
            # Validar configuración de usuario
            user_errors = user_config.validate_config()
            if user_errors:
                logger.error(f"Errores en configuración de usuario: {user_errors}")
                return False
            
            # Validar base de datos
            db_stats = db_manager.get_database_stats()
            logger.info(f"📊 Base de datos: {db_stats}")
            
            # Validar recolector de datos
            health_check = await data_collector.health_check()
            if not health_check['credentials_configured']:
                logger.error("❌ Credenciales de Bitget no configuradas")
                return False
            
            # Inicializar Agente de IA
            agent_initialized = await self.ai_agent.initialize()
            if not agent_initialized:
                logger.error("❌ Error inicializando Agente de IA")
                return False
            
            logger.info("✅ Configuración validada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando recolección de datos: {e}")
    
    def _handle_tick_data(self, tick_data: dict):
        """Maneja datos de tick en tiempo real"""
        try:
            # Log del precio actual
            price = tick_data.get('price', 0)
            if price > 0:
                logger.debug(f"💰 {self.symbol}: ${price:,.2f}")
            
            # Aquí se puede añadir lógica adicional para procesar ticks
            
        except Exception as e:
            logger.error(f"Error procesando tick data: {e}")
    
    def _handle_kline_data(self, kline_data: dict):
        """Maneja datos de kline en tiempo real"""
        try:
            # Log de nueva vela completada
            close_price = kline_data.get('close', 0)
            volume = kline_data.get('volume', 0)
            timestamp = datetime.now()
            
            logger.info(f"📊 Nueva vela {self.symbol}: Close=${close_price:,.2f}, Vol={volume:,.0f}")
            
            # Triggear análisis del modelo ML y ejecución
            asyncio.create_task(self._process_trading_signal(kline_data, timestamp))
            
        except Exception as e:
            logger.error(f"Error procesando kline data: {e}")
    
    async def _process_trading_signal(self, kline_data: dict, timestamp: datetime):
        """Procesa señal de trading usando el Agente de IA"""
        try:
            close_price = kline_data.get('close', 0)
            volume = kline_data.get('volume', 0)
            high = kline_data.get('high', close_price)
            low = kline_data.get('low', close_price)
            open_price = kline_data.get('open', close_price)
            
            logger.info(f"📊 Nueva vela {self.symbol}: Close=${close_price:,.2f}, Vol={volume:,.0f}")
            
            # El agente de IA maneja todo el proceso de trading de forma autónoma
            # Solo necesitamos pasarle los datos de la vela
            market_data = {
                'klines': [kline_data],
                'symbol': self.symbol,
                'timestamp': timestamp
            }
            
            # El agente procesará los datos y tomará decisiones autónomas
            # No necesitamos intervenir en el proceso
            logger.info("🧠 Agente de IA procesando datos de mercado...")
            
        except Exception as e:
            logger.error(f"Error procesando señal de trading: {e}")
    
    def _calculate_atr(self, df, period=14):
        """Calcula Average True Range"""
        try:
            if len(df) < period:
                return 0.01  # ATR por defecto si no hay suficientes datos
            
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # Calcular True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            
            # Calcular ATR como media móvil simple
            atr = np.mean(tr[-period:])
            
            return atr if not np.isnan(atr) else 0.01
            
        except Exception as e:
            logger.error(f"Error calculando ATR: {e}")
            return 0.01
    
    async def start_ml_training(self):
        """Inicia entrenamiento del modelo ML"""
        try:
            logger.info("🧠 Iniciando entrenamiento del modelo ML...")
            
            # Preparar datos para entrenamiento
            X, y, df = data_preprocessor.prepare_training_data(
                symbol=self.symbol,
                days_back=60,
                target_method="classification"
            )
            
            if X.shape[0] > 0:
                logger.info(f"📊 Datos preparados: {X.shape[0]} muestras, {X.shape[2]} features")
                # TODO: Implementar entrenamiento del modelo cuando esté listo
                logger.info("⏳ Modelo ML pendiente de implementación")
            else:
                logger.warning("⚠️ No se pudieron preparar datos para entrenamiento")
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento ML: {e}")
    
    async def start_trading_engine(self):
        """Inicia el motor de trading"""
        try:
            logger.info("⚡ Iniciando motor de trading...")
            
            # Inicializar componentes de trading
            logger.info("🔧 Inicializando componentes de trading...")
            
            # Mostrar resumen de configuración
            risk_summary = risk_manager.get_risk_summary()
            execution_summary = execution_engine.get_execution_summary()
            trade_summary = order_manager.get_trade_summary()
            
            logger.info(f"📊 Configuración de riesgo: {risk_summary}")
            logger.info(f"⚙️ Configuración de ejecución: {execution_summary}")
            logger.info(f"💰 Estado de trading: {trade_summary}")
            
            logger.info("✅ Motor de trading iniciado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando motor de trading: {e}")
    
    async def start_ai_agent(self):
        """Inicia el Agente de IA autónomo"""
        try:
            logger.info("🧠 Iniciando Agente de IA...")
            
            # El agente ya está inicializado en validate_configuration
            # Solo necesitamos iniciar el trading autónomo
            await self.ai_agent.start_autonomous_trading()
            
            logger.info("✅ Agente de IA iniciado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Agente de IA: {e}")
    
    async def start_monitoring_dashboard(self):
        """Inicia el dashboard de monitoreo"""
        try:
            monitoring_settings = user_config.get_monitoring_settings()
            
            if monitoring_settings['dashboard']['enabled']:
                logger.info("📱 Dashboard de monitoreo pendiente de implementación")
                # TODO: Implementar dashboard cuando esté listo
            else:
                logger.info("📱 Dashboard deshabilitado en configuración")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando dashboard: {e}")
    
    async def run_health_checks(self):
        """Ejecuta chequeos de salud periódicos"""
        try:
            while self.running and not self._stop_event.is_set():
                # Health check del data collector
                health = await data_collector.health_check()
                
                if not health['rest_api_ok']:
                    logger.warning("⚠️ API REST no disponible")
                
                if not health['websocket_ok']:
                    logger.warning("⚠️ WebSocket desconectado")
                
                if not health['data_freshness_ok']:
                    logger.warning("⚠️ Datos no están actualizados")
                
                # Health check de la base de datos
                db_stats = db_manager.get_database_stats()
                if db_stats.get('file_size_mb', 0) > 1000:  # 1GB
                    logger.warning("⚠️ Base de datos grande, considerar limpieza")
                
                # Esperar antes del siguiente check (5 minutos)
                await asyncio.sleep(300)
                
        except Exception as e:
            logger.error(f"❌ Error en health checks: {e}")
    
    def print_startup_banner(self):
        """Imprime banner de inicio"""
        banner = f"""
        
🤖 =====================================================
   TRADING BOT AUTÓNOMO v10 - {self.environment.value.upper()}
   =====================================================
   
   Bot Name: {self.bot_name}
   Symbol: {self.symbol}
   Environment: {self.environment.value}
   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   
   Features Enabled:
   ✅ Auto Trading: {user_config.is_feature_enabled('auto_trading')}
   ✅ Auto Retraining: {user_config.is_feature_enabled('auto_retraining')}
   ✅ Risk Management: {user_config.is_feature_enabled('risk_management')}
   ✅ Stop on Drawdown: {user_config.is_feature_enabled('stop_on_drawdown')}
   
   Trading Mode: {user_config.get_trading_mode().upper()}
   
🤖 =====================================================
        """
        print(banner)
        logger.info("Bot iniciado exitosamente")
    
    async def start(self):
        """Inicia el bot completo"""
        try:
            self.running = True
            self.print_startup_banner()
            
            # 1. Validar configuración
            if not await self.validate_configuration():
                logger.error("❌ Configuración inválida, abortando inicio")
                return False
            
            # 2. Inicializar datos
            if not await self.initialize_data():
                logger.error("❌ Error inicializando datos, abortando inicio")
                return False
            
            # 3. Crear tareas asíncronas
            tasks = [
                asyncio.create_task(self.start_data_collection()),
                asyncio.create_task(self.start_ml_training()),
                asyncio.create_task(self.start_trading_engine()),
                asyncio.create_task(self.start_ai_agent()),
                asyncio.create_task(self.start_monitoring_dashboard()),
                asyncio.create_task(self.run_health_checks())
            ]
            
            self.tasks = tasks
            
            # 4. Ejecutar todas las tareas
            logger.info("🚀 Iniciando todos los componentes...")
            
            if self.environment == Environment.DEVELOPMENT:
                # En desarrollo, solo ejecutar por tiempo limitado
                logger.info("🔧 Modo desarrollo: ejecutando por 5 minutos")
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=300  # 5 minutos
                )
            else:
                # En producción, ejecutar indefinidamente
                await asyncio.gather(*tasks, return_exceptions=True)
            
            return True
            
        except asyncio.TimeoutError:
            logger.info("⏰ Tiempo de ejecución completado (modo desarrollo)")
            return True
        except Exception as e:
            logger.error(f"❌ Error crítico en el bot: {e}")
            return False
        finally:
            await self.stop()
    
    async def stop(self):
        """Detiene el bot de forma limpia"""
        if not self.running:
            return
        
        logger.info("🛑 Deteniendo bot...")
        self.running = False
        self._stop_event.set()
        
        # Detener recolección de datos
        data_collector.stop_websocket_stream()
        
        # Cancelar tareas asyncio
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Crear backup de la base de datos
        try:
            db_manager.backup_database()
            logger.info("💾 Backup de base de datos creado")
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
        
        logger.info("✅ Bot detenido correctamente")

async def run_development_mode():
    """Ejecuta el bot en modo desarrollo"""
    bot = TradingBotOrchestrator(Environment.DEVELOPMENT)
    success = await bot.start()
    return success

async def run_backtesting_mode():
    """Ejecuta el bot en modo backtesting"""
    logger.info("📊 Modo backtesting pendiente de implementación")
    # TODO: Implementar backtesting
    return True

async def run_paper_trading_mode():
    """Ejecuta el bot en modo paper trading"""
    bot = TradingBotOrchestrator(Environment.PAPER_TRADING)
    success = await bot.start()
    return success

async def run_live_trading_mode():
    """Ejecuta el bot en modo live trading"""
    # Confirmación adicional para trading real
    confirmation = input("⚠️ ¿Estás seguro de que quieres iniciar TRADING REAL? (escribir 'SI CONFIRMO'): ")
    if confirmation != "SI CONFIRMO":
        logger.info("Trading real cancelado por el usuario")
        return False
    
    bot = TradingBotOrchestrator(Environment.LIVE_TRADING)
    success = await bot.start()
    return success

def setup_argument_parser():
    """Configura el parser de argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Trading Bot Autónomo v10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                          # Modo desarrollo (por defecto)
  python main.py --mode development       # Modo desarrollo explícito
  python main.py --mode backtesting       # Ejecutar backtesting
  python main.py --mode paper-trading     # Paper trading (simulado)
  python main.py --mode live-trading      # Trading real (¡CUIDADO!)
  
  python main.py --collect-data           # Solo recolectar datos históricos
  python main.py --train-model            # Solo entrenar modelo
  python main.py --health-check           # Verificar estado del sistema
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['development', 'backtesting', 'paper-trading', 'live-trading'],
        default='development',
        help='Modo de ejecución del bot (default: development)'
    )
    
    parser.add_argument(
        '--collect-data', '-c',
        action='store_true',
        help='Solo recolectar datos históricos y salir'
    )
    
    parser.add_argument(
        '--train-model', '-t',
        action='store_true',
        help='Solo entrenar modelo ML y salir'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Verificar estado del sistema y salir'
    )
    
    parser.add_argument(
        '--symbol', '-s',
        default='BTCUSDT',
        help='Symbol a operar (default: BTCUSDT)'
    )
    
    parser.add_argument(
        '--days-back', '-d',
        type=int,
        default=30,
        help='Días de historia a recolectar (default: 30)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Logging detallado (DEBUG level)'
    )
    
    return parser

async def collect_data_only(symbol: str, days_back: int):
    """Solo recolectar datos históricos"""
    logger.info(f"📥 Recolectando datos históricos para {symbol}...")
    
    saved_count = await collect_and_save_historical_data(
        symbol=symbol,
        timeframe="1h",
        days_back=days_back
    )
    
    logger.info(f"✅ Recolectados {saved_count} registros para {symbol}")
    return True

async def train_model_only(symbol: str):
    """Solo entrenar modelo ML"""
    logger.info(f"🧠 Entrenando modelo para {symbol}...")
    
    X, y, df = data_preprocessor.prepare_training_data(
        symbol=symbol,
        days_back=60,
        target_method="classification"
    )
    
    if X.shape[0] > 0:
        logger.info(f"📊 Datos preparados: {X.shape[0]} muestras, {X.shape[2]} features")
        logger.info("⏳ Entrenamiento del modelo pendiente de implementación")
        return True
    else:
        logger.error("❌ No se pudieron preparar datos para entrenamiento")
        return False

async def health_check_only():
    """Solo verificar estado del sistema"""
    logger.info("🔍 Verificando estado del sistema...")
    
    # Check base de datos
    db_stats = db_manager.get_database_stats()
    logger.info(f"📊 Base de datos: {db_stats}")
    
    # Check data collector
    health = await data_collector.health_check()
    logger.info(f"🔄 Data collector: {health}")
    
    # Check configuración
    config_errors = user_config.validate_config()
    if config_errors:
        logger.warning(f"⚠️ Errores de configuración: {config_errors}")
    else:
        logger.info("✅ Configuración válida")
    
    logger.info("✅ Health check completado")
    return True

async def main():
    """Función principal"""
    # Setup logging inicial
    setup_logging()
    
    # Parse argumentos
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configurar logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🔧 Logging detallado activado")
    
    try:
        # Ejecutar funciones específicas si se solicitan
        if args.collect_data:
            return await collect_data_only(args.symbol, args.days_back)
        
        if args.train_model:
            return await train_model_only(args.symbol)
        
        if args.health_check:
            return await health_check_only()
        
        # Ejecutar bot en modo especificado
        mode_functions = {
            'development': run_development_mode,
            'backtesting': run_backtesting_mode,
            'paper-trading': run_paper_trading_mode,
            'live-trading': run_live_trading_mode
        }
        
        mode_function = mode_functions.get(args.mode)
        if mode_function:
            success = await mode_function()
            return success
        else:
            logger.error(f"❌ Modo desconocido: {args.mode}")
            return False
            
    except KeyboardInterrupt:
        logger.info("⏹️ Detenido por el usuario")
        return True
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        return False

if __name__ == "__main__":
    # Verificar versión de Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ requerido")
        sys.exit(1)
    
    # Ejecutar main
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
    
    async def initialize_data(self) -> bool:
        """Inicializa datos históricos si es necesario"""
        try:
            logger.info("📈 Inicializando datos...")
            
            # Verificar si tenemos datos recientes
            latest_data = db_manager.get_latest_market_data(self.symbol, 1)
            
            if latest_data.empty:
                logger.info("📥 No hay datos históricos, descargando...")
                saved_count = await collect_and_save_historical_data(
                    symbol=self.symbol,
                    timeframe="1h",
                    days_back=60  # 60 días de historia inicial
                )
                logger.info(f"📊 Descargados {saved_count} registros históricos")
            else:
                last_update = latest_data.index[-1]
                hours_since_update = (datetime.now() - last_update.tz_localize(None)).total_seconds() / 3600
                
                if hours_since_update > 24:
                    logger.info("🔄 Actualizando datos históricos...")
                    saved_count = await collect_and_save_historical_data(
                        symbol=self.symbol,
                        timeframe="1h",
                        days_back=7  # Solo última semana
                    )
                    logger.info(f"📊 Actualizados {saved_count} registros")
                else:
                    logger.info(f"✅ Datos actualizados (última actualización: {last_update})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando datos: {e}")
            return False
    
    async def start_data_collection(self):
        """Inicia la recolección de datos en tiempo real"""
        try:
            logger.info("🔄 Iniciando recolección de datos en tiempo real...")
            
            # Añadir callbacks para datos en tiempo real
            data_collector.add_tick_callback(self._handle_tick_data)
            data_collector.add_kline_callback(self._handle_kline_data)
            
            # Iniciar WebSocket stream
            await data_collector.start_websocket_stream()
            
        except Exception as e:
            logger.error(f"❌ Error iniciando recolección de datos en tiempo real: {e}")
        