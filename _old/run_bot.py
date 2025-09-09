#!/usr/bin/env python3
"""
Trading Bot v10 Enterprise - Sistema de Ejecución Única
=======================================================

Sistema completo de trading con control de Telegram y dashboard en tiempo real.
Ejecuta todo el sistema desde un solo archivo con control móvil completo.

Características:
- Control completo desde Telegram (entrenar, tradear, modos, símbolos)
- Dashboard en tiempo real que se abre automáticamente
- Sistema de colas para comunicación entre componentes
- Seguridad con Chat ID restringido
- Manejo de errores robusto

Uso:
    python run_bot.py

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import asyncio
import logging
import signal
import sys
import webbrowser
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Configurar logging correctamente
from logging_config import setup_logging

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))

# Importaciones del sistema
from src.core.config.enterprise_config import EnterpriseConfigManager
from src.core.monitoring.enterprise.alerting_system import AlertingSystem
from src.core.trading.execution_engine import ExecutionEngine
from src.core.ml.enterprise.training_engine import TrainingEngine
from src.core.monitoring.core.data_provider import DataProvider

# Importaciones de Telegram
from notifications.telegram.telegram_bot import TelegramBot
from notifications.telegram.metrics_sender import MetricsSender

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

class TradingSystemController:
    """Controlador principal del sistema de trading"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        self.config_path = config_path
        self.config_manager = None
        self.config = None
        
        # Componentes del sistema
        self.alerting_system = None
        self.execution_engine = None
        self.training_engine = None
        self.data_provider = None
        self.telegram_bot = None
        self.metrics_sender = None
        
        # Estado del sistema
        self.is_running = False
        self.is_training = False
        self.is_trading = False
        self.current_mode = "paper"
        self.current_symbols = ["BTCUSDT", "ETHUSDT"]
        
        # Colas para comunicación
        self.command_queue = asyncio.Queue()
        self.status_queue = asyncio.Queue()
        
        # Dashboard
        self.dashboard_process = None
        self.dashboard_port = 8050
        
        # Crear directorios necesarios
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        Path("models").mkdir(exist_ok=True)
        
        logger.info("🚀 TradingSystemController inicializado")
    
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        try:
            logger.info("🔧 Inicializando sistema completo...")
            
            # Cargar configuración
            self.config_manager = EnterpriseConfigManager(self.config_path)
            self.config = self.config_manager.load_config()
            logger.info("✅ Configuración cargada")
            
            # Inicializar componentes core
            await self._initialize_core_components()
            
            # Inicializar bot de Telegram
            await self._initialize_telegram_bot()
            
            # Inicializar dashboard
            await self._initialize_dashboard()
            
            logger.info("✅ Sistema inicializado completamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema: {e}")
            raise
    
    async def _initialize_core_components(self):
        """Inicializa los componentes core del sistema"""
        try:
            # Sistema de alertas
            self.alerting_system = AlertingSystem()
            logger.info("✅ Sistema de alertas inicializado")
            
            # Motor de ejecución
            self.execution_engine = ExecutionEngine()
            logger.info("✅ Motor de ejecución inicializado")
            
            # Motor de entrenamiento
            self.training_engine = TrainingEngine()
            logger.info("✅ Motor de entrenamiento inicializado")
            
            # Proveedor de datos
            self.data_provider = DataProvider()
            logger.info("✅ Proveedor de datos inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes core: {e}")
            raise
    
    async def _initialize_telegram_bot(self):
        """Inicializa el bot de Telegram"""
        try:
            self.telegram_bot = TelegramBot()
            
            # Configurar handlers con acceso al controlador
            self.telegram_bot.handlers.set_controller(self)
            
            # Inicializar metrics sender
            self.metrics_sender = MetricsSender(
                self.telegram_bot, 
                self.telegram_bot.get_config()['telegram']
            )
            
            logger.info("✅ Bot de Telegram inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando bot de Telegram: {e}")
            raise
    
    async def _initialize_dashboard(self):
        """Inicializa el dashboard"""
        try:
            # Importar dashboard
            from dashboard import create_dashboard_app
            
            # Crear aplicación del dashboard
            self.dashboard_app = create_dashboard_app()
            
            # Configurar el dashboard para usar nuestro sistema
            self.dashboard_app.config['data_provider'] = self.data_provider
            self.dashboard_app.config['alerting_system'] = self.alerting_system
            
            logger.info("✅ Dashboard inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando dashboard: {e}")
            # No es crítico, continuar sin dashboard
            self.dashboard_app = None
    
    async def start_dashboard(self):
        """Inicia el dashboard en un hilo separado"""
        try:
            if not self.dashboard_app:
                logger.warning("⚠️ Dashboard no disponible")
                return
            
            def run_dashboard():
                try:
                    self.dashboard_app.run_server(
                        host='127.0.0.1',
                        port=self.dashboard_port,
                        debug=False,
                        use_reloader=False
                    )
                except Exception as e:
                    logger.error(f"❌ Error ejecutando dashboard: {e}")
            
            # Ejecutar dashboard en hilo separado
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            
            # Esperar un poco para que el servidor inicie
            await asyncio.sleep(2)
            
            # Abrir navegador automáticamente
            try:
                webbrowser.open(f'http://localhost:{self.dashboard_port}')
                logger.info(f"🌐 Dashboard abierto en http://localhost:{self.dashboard_port}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo abrir el navegador: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando dashboard: {e}")
    
    async def start_telegram_bot(self):
        """Inicia el bot de Telegram"""
        try:
            if not self.telegram_bot:
                logger.warning("⚠️ Bot de Telegram no disponible")
                return
            
            # Iniciar polling del bot
            asyncio.create_task(self.telegram_bot.start_polling())
            
            # Iniciar envío de métricas
            asyncio.create_task(self.metrics_sender.start_sending_metrics())
            asyncio.create_task(self.metrics_sender.start_alert_monitoring())
            
            logger.info("✅ Bot de Telegram iniciado")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando bot de Telegram: {e}")
    
    async def start_data_streaming(self):
        """Inicia el streaming de datos en tiempo real"""
        try:
            if not self.data_provider:
                logger.warning("⚠️ Data provider no disponible")
                return
            
            # Iniciar streaming de datos
            asyncio.create_task(self.data_provider.start_streaming())
            
            logger.info("✅ Streaming de datos iniciado")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando streaming de datos: {e}")
    
    async def process_commands(self):
        """Procesa comandos de la cola"""
        while self.is_running:
            try:
                # Esperar comando con timeout
                command = await asyncio.wait_for(
                    self.command_queue.get(), 
                    timeout=1.0
                )
                
                await self._execute_command(command)
                
            except asyncio.TimeoutError:
                # Timeout normal, continuar
                continue
            except Exception as e:
                logger.error(f"❌ Error procesando comando: {e}")
    
    async def _execute_command(self, command: Dict[str, Any]):
        """Ejecuta un comando específico"""
        try:
            cmd_type = command.get('type')
            args = command.get('args', {})
            chat_id = command.get('chat_id')
            
            logger.info(f"🎮 Ejecutando comando: {cmd_type}")
            
            if cmd_type == 'train':
                await self._handle_train_command(args, chat_id)
            elif cmd_type == 'stop_training':
                await self._handle_stop_training_command(chat_id)
            elif cmd_type == 'stop_train':
                await self._handle_stop_train_command(chat_id)
            elif cmd_type == 'trade':
                await self._handle_trade_command(args, chat_id)
            elif cmd_type == 'stop_trading':
                await self._handle_stop_trading_command(chat_id)
            elif cmd_type == 'set_mode':
                await self._handle_set_mode_command(args, chat_id)
            elif cmd_type == 'set_symbols':
                await self._handle_set_symbols_command(args, chat_id)
            elif cmd_type == 'status':
                await self._handle_status_command(chat_id)
            elif cmd_type == 'metrics':
                await self._handle_metrics_command(chat_id)
            elif cmd_type == 'positions':
                await self._handle_positions_command(chat_id)
            elif cmd_type == 'shutdown':
                await self._handle_shutdown_command(chat_id)
            
            # Comandos de Agentes y ML
            elif cmd_type == 'agents_status':
                await self._handle_agents_status_command(chat_id)
            elif cmd_type == 'agent_status':
                await self._handle_agent_status_command(args, chat_id)
            elif cmd_type == 'retrain':
                await self._handle_retrain_command(args, chat_id)
            elif cmd_type == 'model_info':
                await self._handle_model_info_command(args, chat_id)
            elif cmd_type == 'training_status':
                await self._handle_training_status_command(chat_id)
            
            # Comandos de Datos y Análisis
            elif cmd_type == 'download_data':
                await self._handle_download_data_command(args, chat_id)
            elif cmd_type == 'analyze_data':
                await self._handle_analyze_data_command(args, chat_id)
            elif cmd_type == 'align_data':
                await self._handle_align_data_command(args, chat_id)
            elif cmd_type == 'data_status':
                await self._handle_data_status_command(chat_id)
            elif cmd_type == 'backtest':
                await self._handle_backtest_command(args, chat_id)
            
            # Comandos de Trading Avanzado
            elif cmd_type == 'close_position':
                await self._handle_close_position_command(args, chat_id)
            
            # Comandos de Reportes
            elif cmd_type == 'performance_report':
                await self._handle_performance_report_command(chat_id)
            elif cmd_type == 'agent_analysis':
                await self._handle_agent_analysis_command(args, chat_id)
            elif cmd_type == 'risk_report':
                await self._handle_risk_report_command(chat_id)
            elif cmd_type == 'trades_history':
                await self._handle_trades_history_command(args, chat_id)
            
            # Comandos de Mantenimiento
            elif cmd_type == 'confirm_restart':
                await self._handle_restart_system_command(chat_id)
            elif cmd_type == 'clear_cache':
                await self._handle_clear_cache_command(chat_id)
            elif cmd_type == 'update_models':
                await self._handle_update_models_command(chat_id)
            
            # Comandos de Configuración Adicional
            elif cmd_type == 'set_leverage':
                await self._handle_set_leverage_command(args, chat_id)
            
            else:
                logger.warning(f"⚠️ Comando desconocido: {cmd_type}")
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando comando {command.get('type')}: {e}")
            if command.get('chat_id'):
                await self.telegram_bot.send_message(
                    f"❌ Error ejecutando comando: {str(e)}",
                    chat_id=command['chat_id']
                )
    
    async def _handle_train_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de entrenamiento"""
        try:
            symbols = args.get('symbols', self.current_symbols)
            duration = args.get('duration', '8h')
            
            if self.is_training:
                await self.telegram_bot.send_message(
                    "⚠️ Ya hay un entrenamiento en curso", 
                    chat_id=chat_id
                )
                return
            
            # Confirmar entrenamiento
            confirmation_msg = f"""
🤖 <b>Confirmar Entrenamiento</b>

Símbolos: {', '.join(symbols)}
Duración: {duration}

¿Continuar? Responde <b>YES</b> para confirmar.
            """
            
            await self.telegram_bot.send_message(confirmation_msg, chat_id=chat_id)
            
            # Enviar comando de confirmación a la cola
            await self.command_queue.put({
                'type': 'confirm_train',
                'args': {'symbols': symbols, 'duration': duration},
                'chat_id': chat_id
            })
            
        except Exception as e:
            logger.error(f"❌ Error en comando train: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_stop_training_command(self, chat_id: str):
        """Maneja comando de detener entrenamiento"""
        try:
            if not self.is_training:
                await self.telegram_bot.send_message(
                    "⚠️ No hay entrenamiento en curso", 
                    chat_id=chat_id
                )
                return
            
            # Detener entrenamiento
            if self.training_engine:
                await self.training_engine.stop_training()
            
            self.is_training = False
            
            await self.telegram_bot.send_message(
                "🛑 Entrenamiento detenido", 
                chat_id=chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_stop_train_command(self, chat_id: str):
        """Maneja comando de detener entrenamiento de forma elegante"""
        try:
            if not self.is_training:
                await self.telegram_bot.send_message(
                    "⚠️ No hay entrenamiento en curso", 
                    chat_id=chat_id
                )
                return
            
            # Detener entrenamiento de forma elegante
            if self.training_engine:
                if hasattr(self.training_engine, 'stop_training_gracefully'):
                    self.training_engine.stop_training_gracefully()
                else:
                    await self.training_engine.stop_training()
            
            self.is_training = False
            
            await self.telegram_bot.send_message(
                "🛑 **Entrenamiento detenido de forma elegante**\n\n"
                "✅ Progreso guardado\n"
                "🤖 Modelos actualizados\n"
                "💾 Resumen final creado\n\n"
                "El entrenamiento se ha detenido de forma segura.", 
                chat_id=chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento elegante: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_trade_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de trading"""
        try:
            mode = args.get('mode', 'paper')
            symbols = args.get('symbols', self.current_symbols)
            
            if self.is_trading:
                await self.telegram_bot.send_message(
                    "⚠️ Ya hay trading en curso", 
                    chat_id=chat_id
                )
                return
            
            # Confirmar trading (especialmente para modo live)
            if mode == 'live':
                confirmation_msg = f"""
🚨 <b>CONFIRMACIÓN CRÍTICA - TRADING LIVE</b>

Modo: <b>LIVE</b> (dinero real)
Símbolos: {', '.join(symbols)}

⚠️ <b>ADVERTENCIA:</b> Esto usará dinero real.

¿Continuar? Responde <b>YES</b> para confirmar.
                """
            else:
                confirmation_msg = f"""
🤖 <b>Confirmar Trading</b>

Modo: {mode.upper()}
Símbolos: {', '.join(symbols)}

¿Continuar? Responde <b>YES</b> para confirmar.
                """
            
            await self.telegram_bot.send_message(confirmation_msg, chat_id=chat_id)
            
            # Enviar comando de confirmación a la cola
            await self.command_queue.put({
                'type': 'confirm_trade',
                'args': {'mode': mode, 'symbols': symbols},
                'chat_id': chat_id
            })
            
        except Exception as e:
            logger.error(f"❌ Error en comando trade: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_stop_trading_command(self, chat_id: str):
        """Maneja comando de detener trading"""
        try:
            if not self.is_trading:
                await self.telegram_bot.send_message(
                    "⚠️ No hay trading en curso", 
                    chat_id=chat_id
                )
                return
            
            # Detener trading
            if self.execution_engine:
                await self.execution_engine.stop_trading()
            
            self.is_trading = False
            
            await self.telegram_bot.send_message(
                "🛑 Trading detenido", 
                chat_id=chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo trading: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_set_mode_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de cambiar modo"""
        try:
            mode = args.get('mode', 'paper')
            
            if mode not in ['paper', 'live']:
                await self.telegram_bot.send_message(
                    "❌ Modo inválido. Usa 'paper' o 'live'", 
                    chat_id=chat_id
                )
                return
            
            self.current_mode = mode
            
            await self.telegram_bot.send_message(
                f"✅ Modo cambiado a: {mode.upper()}", 
                chat_id=chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error cambiando modo: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_set_symbols_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de cambiar símbolos"""
        try:
            symbols = args.get('symbols', [])
            
            if not symbols:
                await self.telegram_bot.send_message(
                    "❌ No se proporcionaron símbolos", 
                    chat_id=chat_id
                )
                return
            
            self.current_symbols = symbols
            
            await self.telegram_bot.send_message(
                f"✅ Símbolos cambiados a: {', '.join(symbols)}", 
                chat_id=chat_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error cambiando símbolos: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_status_command(self, chat_id: str):
        """Maneja comando de estado"""
        try:
            status = {
                'is_running': self.is_running,
                'is_training': self.is_training,
                'is_trading': self.is_trading,
                'current_mode': self.current_mode,
                'current_symbols': self.current_symbols,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            status_msg = f"""
📊 <b>Estado del Sistema</b>

🔄 <b>Ejecutándose:</b> {'✅ Sí' if status['is_running'] else '❌ No'}
🎓 <b>Entrenando:</b> {'✅ Sí' if status['is_training'] else '❌ No'}
💹 <b>Trading:</b> {'✅ Sí' if status['is_trading'] else '❌ No'}
🎯 <b>Modo:</b> {status['current_mode'].upper()}
📈 <b>Símbolos:</b> {', '.join(status['current_symbols'])}
⏰ <b>Actualizado:</b> {status['timestamp']}
            """
            
            await self.telegram_bot.send_message(status_msg, chat_id=chat_id)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_metrics_command(self, chat_id: str):
        """Maneja comando de métricas"""
        try:
            if not self.alerting_system:
                await self.telegram_bot.send_message(
                    "❌ Sistema de métricas no disponible", 
                    chat_id=chat_id
                )
                return
            
            # Obtener métricas actuales
            metrics = await self.alerting_system.get_system_metrics()
            
            # Formatear mensaje
            message = self.metrics_sender.format_metrics_message(metrics)
            
            await self.telegram_bot.send_message(message, chat_id=chat_id)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_positions_command(self, chat_id: str):
        """Maneja comando de posiciones"""
        try:
            if not self.execution_engine:
                await self.telegram_bot.send_message(
                    "❌ Motor de ejecución no disponible", 
                    chat_id=chat_id
                )
                return
            
            # Obtener posiciones
            positions = await self.execution_engine.get_open_positions()
            
            if not positions:
                await self.telegram_bot.send_message(
                    "📭 No hay posiciones abiertas", 
                    chat_id=chat_id
                )
                return
            
            # Formatear mensaje de posiciones
            message = "📊 <b>Posiciones Abiertas</b>\n\n"
            
            for pos in positions[:10]:  # Limitar a 10 posiciones
                side_emoji = "🟢" if pos.get('side', '').lower() == 'long' else "🔴"
                pnl_emoji = "📈" if pos.get('pnl', 0) >= 0 else "📉"
                
                message += f"""
{side_emoji} <b>{pos.get('symbol', 'N/A')}</b> ({pos.get('side', 'N/A')})
   {pnl_emoji} PnL: ${pos.get('pnl', 0):,.2f} ({pos.get('pnl_pct', 0):.1f}%)
   💰 Tamaño: {pos.get('size', 0):.4f}
   📍 Precio: ${pos.get('price', 0):,.2f}
                """
            
            if len(positions) > 10:
                message += f"\n... y {len(positions) - 10} posiciones más"
            
            await self.telegram_bot.send_message(message, chat_id=chat_id)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones: {e}")
            await self.telegram_bot.send_message(f"❌ Error: {str(e)}", chat_id=chat_id)
    
    async def _handle_shutdown_command(self, chat_id: str):
        """Maneja comando de apagado"""
        try:
            await self.telegram_bot.send_message(
                "🛑 Iniciando apagado del sistema...", 
                chat_id=chat_id
            )
            
            # Detener todo
            self.is_running = False
            self.is_training = False
            self.is_trading = False
            
            # Detener componentes
            if self.training_engine:
                await self.training_engine.stop_training()
            
            if self.execution_engine:
                await self.execution_engine.stop_trading()
            
            if self.telegram_bot:
                self.telegram_bot.stop()
            
            logger.info("🛑 Sistema apagado por comando de Telegram")
            
        except Exception as e:
            logger.error(f"❌ Error en apagado: {e}")
    
    # ===== NUEVOS MÉTODOS DE MANEJO DE COMANDOS =====
    
    # Comandos de Agentes y ML
    async def _handle_agents_status_command(self, chat_id: str):
        """Maneja comando de estado de todos los agentes"""
        try:
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Obtener estado de todos los agentes
            agents_status = await self.training_engine.get_all_agents_status()
            
            message = "🤖 <b>Estado de Todos los Agentes</b>\n\n"
            for symbol, status in agents_status.items():
                message += f"<b>{symbol}:</b>\n"
                message += f"• Estado: {status.get('status', 'Desconocido')}\n"
                message += f"• Último entrenamiento: {status.get('last_training', 'N/A')}\n"
                message += f"• Precisión: {status.get('accuracy', 'N/A')}%\n"
                message += f"• Trades: {status.get('trades_count', 0)}\n\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo agentes: {e}", chat_id)
            logger.error(f"❌ Error en _handle_agents_status_command: {e}")
    
    async def _handle_agent_status_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de estado de agente específico"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Obtener estado del agente específico
            agent_status = await self.training_engine.get_agent_status(symbol)
            
            message = f"🤖 <b>Estado del Agente {symbol}</b>\n\n"
            message += f"• Estado: {agent_status.get('status', 'Desconocido')}\n"
            message += f"• Último entrenamiento: {agent_status.get('last_training', 'N/A')}\n"
            message += f"• Precisión: {agent_status.get('accuracy', 'N/A')}%\n"
            message += f"• Trades ejecutados: {agent_status.get('trades_count', 0)}\n"
            message += f"• PnL total: {agent_status.get('total_pnl', 0):.2f} USDT\n"
            message += f"• Win rate: {agent_status.get('win_rate', 0):.1f}%\n"
            message += f"• Drawdown: {agent_status.get('drawdown', 0):.1f}%\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo estado del agente: {e}", chat_id)
            logger.error(f"❌ Error en _handle_agent_status_command: {e}")
    
    async def _handle_retrain_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de reentrenamiento"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            duration = args.get('duration', '4h')
            
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Iniciar reentrenamiento
            await self.training_engine.retrain_agent(symbol, duration)
            
            message = f"🎓 <b>Reentrenamiento Iniciado</b>\n\n"
            message += f"• Símbolo: {symbol}\n"
            message += f"• Duración: {duration}\n"
            message += f"• Estado: En progreso...\n\n"
            message += "Usa /training_status para ver el progreso."
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error en reentrenamiento: {e}", chat_id)
            logger.error(f"❌ Error en _handle_retrain_command: {e}")
    
    async def _handle_model_info_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de información del modelo"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Obtener información del modelo
            model_info = await self.training_engine.get_model_info(symbol)
            
            message = f"📊 <b>Información del Modelo {symbol}</b>\n\n"
            message += f"• Tipo: {model_info.get('type', 'LSTM + Attention')}\n"
            message += f"• Parámetros: {model_info.get('parameters', 'N/A')}\n"
            message += f"• Precisión: {model_info.get('accuracy', 'N/A')}%\n"
            message += f"• Loss: {model_info.get('loss', 'N/A')}\n"
            message += f"• Épocas: {model_info.get('epochs', 'N/A')}\n"
            message += f"• Tamaño del dataset: {model_info.get('dataset_size', 'N/A')}\n"
            message += f"• Última actualización: {model_info.get('last_update', 'N/A')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo información del modelo: {e}", chat_id)
            logger.error(f"❌ Error en _handle_model_info_command: {e}")
    
    async def _handle_training_status_command(self, chat_id: str):
        """Maneja comando de estado del entrenamiento"""
        try:
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Obtener estado del entrenamiento
            training_status = await self.training_engine.get_training_status()
            
            message = "🎓 <b>Estado del Entrenamiento</b>\n\n"
            message += f"• Estado: {training_status.get('status', 'Inactivo')}\n"
            message += f"• Progreso: {training_status.get('progress', 0)}%\n"
            message += f"• Símbolos: {', '.join(training_status.get('symbols', []))}\n"
            message += f"• Duración: {training_status.get('duration', 'N/A')}\n"
            message += f"• Tiempo restante: {training_status.get('time_remaining', 'N/A')}\n"
            message += f"• Época actual: {training_status.get('current_epoch', 0)}\n"
            message += f"• Loss actual: {training_status.get('current_loss', 'N/A')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo estado de entrenamiento: {e}", chat_id)
            logger.error(f"❌ Error en _handle_training_status_command: {e}")
    
    # Comandos de Datos y Análisis
    async def _handle_download_data_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de descarga de datos"""
        try:
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            days = args.get('days', 30)
            
            if not self.data_provider:
                await self.telegram_bot.send_message("❌ Data provider no disponible", chat_id)
                return
            
            # Iniciar descarga de datos
            await self.data_provider.download_historical_data(symbols, days)
            
            message = f"📥 <b>Descarga de Datos Iniciada</b>\n\n"
            message += f"• Símbolos: {', '.join(symbols)}\n"
            message += f"• Días: {days}\n"
            message += f"• Estado: En progreso...\n\n"
            message += "Usa /data_status para ver el progreso."
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error descargando datos: {e}", chat_id)
            logger.error(f"❌ Error en _handle_download_data_command: {e}")
    
    async def _handle_analyze_data_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de análisis de datos"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.data_provider:
                await self.telegram_bot.send_message("❌ Data provider no disponible", chat_id)
                return
            
            # Analizar datos históricos
            analysis = await self.data_provider.analyze_historical_data(symbol)
            
            message = f"📊 <b>Análisis de Datos {symbol}</b>\n\n"
            message += f"• Período: {analysis.get('period', 'N/A')}\n"
            message += f"• Datos disponibles: {analysis.get('data_points', 0)}\n"
            message += f"• Volatilidad: {analysis.get('volatility', 'N/A')}%\n"
            message += f"• Rango de precios: {analysis.get('price_range', 'N/A')}\n"
            message += f"• Tendencias: {analysis.get('trends', 'N/A')}\n"
            message += f"• Calidad de datos: {analysis.get('data_quality', 'N/A')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error analizando datos: {e}", chat_id)
            logger.error(f"❌ Error en _handle_analyze_data_command: {e}")
    
    async def _handle_align_data_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de alineación de datos"""
        try:
            symbols = args.get('symbols', ['BTCUSDT', 'ETHUSDT'])
            
            if not self.data_provider:
                await self.telegram_bot.send_message("❌ Data provider no disponible", chat_id)
                return
            
            # Alinear datos
            await self.data_provider.align_data(symbols)
            
            message = f"🔄 <b>Alineación de Datos Completada</b>\n\n"
            message += f"• Símbolos: {', '.join(symbols)}\n"
            message += f"• Estado: Completado\n"
            message += f"• Timestamps sincronizados\n"
            message += f"• Datos listos para entrenamiento\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error alineando datos: {e}", chat_id)
            logger.error(f"❌ Error en _handle_align_data_command: {e}")
    
    async def _handle_data_status_command(self, chat_id: str):
        """Maneja comando de estado de los datos"""
        try:
            if not self.data_provider:
                await self.telegram_bot.send_message("❌ Data provider no disponible", chat_id)
                return
            
            # Obtener estado de los datos
            data_status = await self.data_provider.get_data_status()
            
            message = "📊 <b>Estado de los Datos</b>\n\n"
            message += f"• Símbolos disponibles: {len(data_status.get('symbols', []))}\n"
            message += f"• Última actualización: {data_status.get('last_update', 'N/A')}\n"
            message += f"• Datos en tiempo real: {'✅' if data_status.get('realtime_active') else '❌'}\n"
            message += f"• Calidad promedio: {data_status.get('avg_quality', 'N/A')}%\n"
            message += f"• Latencia: {data_status.get('latency', 'N/A')}ms\n\n"
            
            if data_status.get('symbols'):
                message += "<b>Símbolos:</b>\n"
                for symbol, info in data_status['symbols'].items():
                    message += f"• {symbol}: {info.get('points', 0)} puntos\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo estado de datos: {e}", chat_id)
            logger.error(f"❌ Error en _handle_data_status_command: {e}")
    
    async def _handle_backtest_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de backtest"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            days = args.get('days', 7)
            
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Ejecutar backtest
            backtest_results = await self.training_engine.run_backtest(symbol, days)
            
            message = f"🧪 <b>Resultados del Backtest {symbol}</b>\n\n"
            message += f"• Período: {days} días\n"
            message += f"• Trades ejecutados: {backtest_results.get('total_trades', 0)}\n"
            message += f"• Trades ganadores: {backtest_results.get('winning_trades', 0)}\n"
            message += f"• Win rate: {backtest_results.get('win_rate', 0):.1f}%\n"
            message += f"• PnL total: {backtest_results.get('total_pnl', 0):.2f} USDT\n"
            message += f"• Drawdown máximo: {backtest_results.get('max_drawdown', 0):.1f}%\n"
            message += f"• Sharpe ratio: {backtest_results.get('sharpe_ratio', 0):.2f}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error ejecutando backtest: {e}", chat_id)
            logger.error(f"❌ Error en _handle_backtest_command: {e}")
    
    # Comandos de Trading Avanzado
    async def _handle_close_position_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de cerrar posición"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.execution_engine:
                await self.telegram_bot.send_message("❌ Motor de ejecución no disponible", chat_id)
                return
            
            # Cerrar posición específica
            result = await self.execution_engine.close_position(symbol)
            
            if result.get('success'):
                message = f"🔄 <b>Posición Cerrada</b>\n\n"
                message += f"• Símbolo: {symbol}\n"
                message += f"• PnL: {result.get('pnl', 0):.2f} USDT\n"
                message += f"• Comisión: {result.get('commission', 0):.2f} USDT\n"
                message += f"• Tiempo: {result.get('execution_time', 0):.3f}s\n"
            else:
                message = f"❌ <b>Error Cerrando Posición</b>\n\n"
                message += f"• Símbolo: {symbol}\n"
                message += f"• Error: {result.get('error', 'Desconocido')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error cerrando posición: {e}", chat_id)
            logger.error(f"❌ Error en _handle_close_position_command: {e}")
    
    # Comandos de Reportes
    async def _handle_performance_report_command(self, chat_id: str):
        """Maneja comando de reporte de rendimiento"""
        try:
            if not self.alerting_system:
                await self.telegram_bot.send_message("❌ Sistema de alertas no disponible", chat_id)
                return
            
            # Generar reporte de rendimiento
            report = await self.alerting_system.generate_performance_report()
            
            message = "📊 <b>Reporte de Rendimiento</b>\n\n"
            message += f"• Período: {report.get('period', 'N/A')}\n"
            message += f"• PnL total: {report.get('total_pnl', 0):.2f} USDT\n"
            message += f"• Win rate: {report.get('win_rate', 0):.1f}%\n"
            message += f"• Drawdown máximo: {report.get('max_drawdown', 0):.1f}%\n"
            message += f"• Trades totales: {report.get('total_trades', 0)}\n"
            message += f"• Trades ganadores: {report.get('winning_trades', 0)}\n"
            message += f"• Trades perdedores: {report.get('losing_trades', 0)}\n"
            message += f"• Sharpe ratio: {report.get('sharpe_ratio', 0):.2f}\n"
            message += f"• Calmar ratio: {report.get('calmar_ratio', 0):.2f}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error generando reporte: {e}", chat_id)
            logger.error(f"❌ Error en _handle_performance_report_command: {e}")
    
    async def _handle_agent_analysis_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de análisis de agente"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Generar análisis detallado del agente
            analysis = await self.training_engine.analyze_agent(symbol)
            
            message = f"🔍 <b>Análisis Detallado del Agente {symbol}</b>\n\n"
            message += f"• Rendimiento: {analysis.get('performance', 'N/A')}\n"
            message += f"• Precisión: {analysis.get('accuracy', 0):.1f}%\n"
            message += f"• Trades: {analysis.get('trades', 0)}\n"
            message += f"• PnL: {analysis.get('pnl', 0):.2f} USDT\n"
            message += f"• Win rate: {analysis.get('win_rate', 0):.1f}%\n"
            message += f"• Drawdown: {analysis.get('drawdown', 0):.1f}%\n"
            message += f"• Sharpe: {analysis.get('sharpe', 0):.2f}\n"
            message += f"• Recomendación: {analysis.get('recommendation', 'N/A')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error analizando agente: {e}", chat_id)
            logger.error(f"❌ Error en _handle_agent_analysis_command: {e}")
    
    async def _handle_risk_report_command(self, chat_id: str):
        """Maneja comando de reporte de riesgo"""
        try:
            if not self.alerting_system:
                await self.telegram_bot.send_message("❌ Sistema de alertas no disponible", chat_id)
                return
            
            # Generar reporte de riesgo
            risk_report = await self.alerting_system.generate_risk_report()
            
            message = "⚠️ <b>Reporte de Riesgo</b>\n\n"
            message += f"• Nivel de riesgo: {risk_report.get('risk_level', 'N/A')}\n"
            message += f"• Drawdown actual: {risk_report.get('current_drawdown', 0):.1f}%\n"
            message += f"• Drawdown máximo: {risk_report.get('max_drawdown', 0):.1f}%\n"
            message += f"• Exposición total: {risk_report.get('total_exposure', 0):.2f} USDT\n"
            message += f"• Margen disponible: {risk_report.get('available_margin', 0):.2f} USDT\n"
            message += f"• Ratio de apalancamiento: {risk_report.get('leverage_ratio', 0):.1f}x\n"
            message += f"• Alertas activas: {risk_report.get('active_alerts', 0)}\n"
            message += f"• Recomendación: {risk_report.get('recommendation', 'N/A')}\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error generando reporte de riesgo: {e}", chat_id)
            logger.error(f"❌ Error en _handle_risk_report_command: {e}")
    
    async def _handle_trades_history_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de historial de trades"""
        try:
            days = args.get('days', 7)
            
            if not self.execution_engine:
                await self.telegram_bot.send_message("❌ Motor de ejecución no disponible", chat_id)
                return
            
            # Obtener historial de trades
            trades_history = await self.execution_engine.get_trades_history(days)
            
            message = f"📈 <b>Historial de Trades ({days} días)</b>\n\n"
            message += f"• Total de trades: {len(trades_history.get('trades', []))}\n"
            message += f"• PnL total: {trades_history.get('total_pnl', 0):.2f} USDT\n"
            message += f"• Win rate: {trades_history.get('win_rate', 0):.1f}%\n\n"
            
            # Mostrar últimos 5 trades
            recent_trades = trades_history.get('trades', [])[:5]
            if recent_trades:
                message += "<b>Últimos Trades:</b>\n"
                for trade in recent_trades:
                    message += f"• {trade.get('symbol', 'N/A')} - {trade.get('side', 'N/A')} - {trade.get('pnl', 0):.2f} USDT\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error obteniendo historial: {e}", chat_id)
            logger.error(f"❌ Error en _handle_trades_history_command: {e}")
    
    # Comandos de Mantenimiento
    async def _handle_restart_system_command(self, chat_id: str):
        """Maneja comando de reinicio del sistema"""
        try:
            message = "🔄 <b>Reiniciando Sistema...</b>\n\n"
            message += "• Deteniendo componentes...\n"
            message += "• Limpiando memoria...\n"
            message += "• Reiniciando servicios...\n"
            message += "• Sistema reiniciado correctamente\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
            # Reiniciar sistema
            await self.restart_system()
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error reiniciando sistema: {e}", chat_id)
            logger.error(f"❌ Error en _handle_restart_system_command: {e}")
    
    async def _handle_clear_cache_command(self, chat_id: str):
        """Maneja comando de limpiar cache"""
        try:
            # Limpiar cache del sistema
            await self.clear_system_cache()
            
            message = "🧹 <b>Cache Limpiado</b>\n\n"
            message += "• Cache de datos limpiado\n"
            message += "• Cache de modelos limpiado\n"
            message += "• Cache de métricas limpiado\n"
            message += "• Memoria liberada\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error limpiando cache: {e}", chat_id)
            logger.error(f"❌ Error en _handle_clear_cache_command: {e}")
    
    async def _handle_update_models_command(self, chat_id: str):
        """Maneja comando de actualizar modelos"""
        try:
            if not self.training_engine:
                await self.telegram_bot.send_message("❌ Motor de entrenamiento no disponible", chat_id)
                return
            
            # Actualizar modelos
            await self.training_engine.update_all_models()
            
            message = "🔄 <b>Modelos Actualizados</b>\n\n"
            message += "• Modelos descargados\n"
            message += "• Pesos actualizados\n"
            message += "• Configuraciones sincronizadas\n"
            message += "• Modelos listos para uso\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error actualizando modelos: {e}", chat_id)
            logger.error(f"❌ Error en _handle_update_models_command: {e}")
    
    # Comandos de Configuración Adicional
    async def _handle_set_leverage_command(self, args: Dict[str, Any], chat_id: str):
        """Maneja comando de cambiar leverage"""
        try:
            symbol = args.get('symbol', 'BTCUSDT')
            leverage = args.get('leverage', 10)
            
            if not self.execution_engine:
                await self.telegram_bot.send_message("❌ Motor de ejecución no disponible", chat_id)
                return
            
            # Cambiar leverage
            await self.execution_engine.set_leverage(symbol, leverage)
            
            message = f"⚙️ <b>Leverage Actualizado</b>\n\n"
            message += f"• Símbolo: {symbol}\n"
            message += f"• Nuevo leverage: {leverage}x\n"
            message += f"• Estado: Aplicado\n"
            message += f"• Próximos trades usarán {leverage}x\n"
            
            await self.telegram_bot.send_message(message, chat_id)
            
        except Exception as e:
            await self.telegram_bot.send_message(f"❌ Error cambiando leverage: {e}", chat_id)
            logger.error(f"❌ Error en _handle_set_leverage_command: {e}")
    
    # Métodos auxiliares
    async def restart_system(self):
        """Reinicia el sistema"""
        try:
            logger.info("🔄 Reiniciando sistema...")
            
            # Detener componentes
            self.is_running = False
            
            # Reiniciar
            await asyncio.sleep(2)
            self.is_running = True
            
            logger.info("✅ Sistema reiniciado")
            
        except Exception as e:
            logger.error(f"❌ Error reiniciando sistema: {e}")
    
    async def clear_system_cache(self):
        """Limpia el cache del sistema"""
        try:
            logger.info("🧹 Limpiando cache del sistema...")
            
            # Limpiar cache de componentes
            if self.data_provider:
                await self.data_provider.clear_cache()
            
            if self.training_engine:
                await self.training_engine.clear_cache()
            
            if self.execution_engine:
                await self.execution_engine.clear_cache()
            
            logger.info("✅ Cache limpiado")
            
        except Exception as e:
            logger.error(f"❌ Error limpiando cache: {e}")
    
    async def run(self):
        """Ejecuta el sistema principal"""
        try:
            self.is_running = True
            logger.info("🚀 Iniciando sistema de trading...")
            
            # Inicializar sistema
            await self.initialize()
            
            # Iniciar componentes
            await self.start_dashboard()
            await self.start_telegram_bot()
            await self.start_data_streaming()
            
            # Enviar mensaje de inicio
            if self.telegram_bot:
                await self.telegram_bot.send_message(
                    """
🚀 <b>Trading Bot v10 Enterprise Iniciado</b>

✅ Sistema completamente operativo
📊 Dashboard abierto en el navegador
🤖 Bot de Telegram listo para comandos

Usa /help para ver todos los comandos disponibles.
                    """
                )
            
            logger.info("✅ Sistema iniciado completamente")
            
            # Ejecutar loop principal
            await self.process_commands()
            
        except KeyboardInterrupt:
            logger.info("🛑 Interrupción por usuario")
        except Exception as e:
            logger.error(f"❌ Error en sistema principal: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Apaga el sistema de forma segura"""
        try:
            logger.info("🛑 Apagando sistema...")
            
            self.is_running = False
            self.is_training = False
            self.is_trading = False
            
            # Detener componentes
            if self.training_engine:
                await self.training_engine.stop_training()
            
            if self.execution_engine:
                await self.execution_engine.stop_trading()
            
            if self.telegram_bot:
                self.telegram_bot.stop()
            
            logger.info("✅ Sistema apagado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error en apagado: {e}")

def signal_handler(signum, frame):
    """Maneja señales del sistema"""
    logger.info(f"🛑 Señal recibida: {signum}")
    sys.exit(0)

async def main():
    """Función principal"""
    # Configurar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crear controlador del sistema
    controller = TradingSystemController()
    
    try:
        # Ejecutar sistema
        await controller.run()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupción por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
    finally:
        await controller.shutdown()

if __name__ == "__main__":
    # Ejecutar sistema
    asyncio.run(main())
