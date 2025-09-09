# Ruta: core/monitoring/metrics_sender.py
#!/usr/bin/env python3
"""
Sistema de Métricas Enterprise para Telegram
===========================================

Este módulo maneja el envío de métricas de entrenamiento y trading
a Telegram cada 60 segundos, con integración completa con Redis,
TimescaleDB y Kafka.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from telegram import Bot
from telegram.error import TelegramError
import json

# Configuración de logging
logger = logging.getLogger(__name__)

class MetricsSender:
    """Clase para enviar métricas de entrenamiento a Telegram"""
    
    def __init__(self):
        """Inicializar el sender de métricas"""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.metrics_interval = int(os.getenv("METRICS_INTERVAL", 60))
        self.message_id = None
        self.last_update = None
        self.metrics_history = []
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID deben estar configurados")
        
        self.bot = Bot(token=self.bot_token)
        logger.info(f"MetricsSender inicializado - Chat ID: {self.chat_id}")
    
    async def send_training_update(self, metrics: Dict[str, Any]) -> bool:
        """Enviar o actualizar mensaje de Telegram con métricas de entrenamiento"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Formatear métricas
            message = self._format_training_message(metrics, timestamp)
            
            # Enviar nuevo mensaje o editar existente
            if self.message_id is None:
                sent_message = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                self.message_id = sent_message.message_id
                logger.info("Nuevo mensaje de métricas enviado a Telegram")
            else:
                await self.bot.edit_message_text(
                    text=message,
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    parse_mode='Markdown'
                )
                logger.info("Mensaje de métricas actualizado en Telegram")
            
            # Guardar historial
            self.metrics_history.append({
                'timestamp': timestamp,
                'metrics': metrics.copy()
            })
            
            # Mantener solo últimos 100 registros
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]
            
            self.last_update = datetime.now()
            return True
            
        except TelegramError as e:
            logger.error(f"Error enviando actualización a Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en send_training_update: {e}")
            return False
    
    def _format_training_message(self, metrics: Dict[str, Any], timestamp: str) -> str:
        """Formatear mensaje de métricas para Telegram"""
        
        # Métricas básicas
        trades = metrics.get('trades', 0)
        win_rate = metrics.get('win_rate', 0.0)
        daily_pnl = metrics.get('daily_pnl', 0.0)
        balance = metrics.get('balance', 0.0)
        balance_pct = metrics.get('balance_pct', 0.0)
        
        # Métricas de rendimiento
        total_pnl = metrics.get('total_pnl', 0.0)
        max_drawdown = metrics.get('max_drawdown', 0.0)
        sharpe_ratio = metrics.get('sharpe_ratio', 0.0)
        
        # Métricas de trading
        active_positions = metrics.get('active_positions', 0)
        max_positions = metrics.get('max_positions', 10)
        risk_per_trade = metrics.get('risk_per_trade', 2.0)
        
        # Métricas de sistema
        cpu_usage = metrics.get('cpu_usage', 0.0)
        memory_usage = metrics.get('memory_usage', 0.0)
        latency_ms = metrics.get('latency_ms', 0)
        
        # Métricas de datos
        data_points = metrics.get('data_points', 0)
        cache_hits = metrics.get('cache_hits', 0)
        cache_misses = metrics.get('cache_misses', 0)
        
        # Emojis para mejor visualización
        status_emoji = "🟢" if daily_pnl >= 0 else "🔴"
        trend_emoji = "📈" if balance_pct >= 0 else "📉"
        
        message = f"""
🤖 **Bot Trading v10 Enterprise** {status_emoji}
⏰ **Actualización:** {timestamp}

📊 **MÉTRICAS DE TRADING**
• Trades: `{trades:,}`
• Win Rate: `{win_rate:.2%}`
• PnL Diario: `{daily_pnl:+.2f} USDT`
• Balance: `{balance:,.2f} USDT`
• Cambio: `{balance_pct:+.2%}` {trend_emoji}

💰 **RENDIMIENTO**
• PnL Total: `{total_pnl:+.2f} USDT`
• Max Drawdown: `{max_drawdown:.2%}`
• Sharpe Ratio: `{sharpe_ratio:.2f}`

🎯 **POSICIONES**
• Activas: `{active_positions}/{max_positions}`
• Riesgo por Trade: `{risk_per_trade:.1f}%`

⚡ **SISTEMA**
• CPU: `{cpu_usage:.1f}%`
• Memoria: `{memory_usage:.1f}%`
• Latencia: `{latency_ms}ms`

📈 **DATOS**
• Puntos: `{data_points:,}`
• Cache Hits: `{cache_hits:,}`
• Cache Misses: `{cache_misses:,}`

🔄 **Estado:** {'🟢 Activo' if metrics.get('bot_active', True) else '🔴 Inactivo'}
        """.strip()
        
        return message
    
    async def send_alert(self, alert_type: str, message: str, severity: str = "INFO") -> bool:
        """Enviar alerta específica a Telegram"""
        try:
            # Emojis por severidad
            severity_emojis = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🚨",
                "SUCCESS": "✅"
            }
            
            emoji = severity_emojis.get(severity, "ℹ️")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            alert_message = f"""
{emoji} **{alert_type.upper()}** - {timestamp}

{message}

🤖 Bot Trading v10 Enterprise
            """.strip()
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=alert_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Alerta {severity} enviada: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")
            return False
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """Enviar notificación de trade específico"""
        try:
            symbol = trade_data.get('symbol', 'N/A')
            side = trade_data.get('side', 'N/A')
            amount = trade_data.get('amount', 0.0)
            price = trade_data.get('price', 0.0)
            pnl = trade_data.get('pnl', 0.0)
            timestamp = trade_data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            side_emoji = "🟢" if side.upper() == "BUY" else "🔴"
            pnl_emoji = "📈" if pnl >= 0 else "📉"
            
            message = f"""
{side_emoji} **NUEVO TRADE** - {timestamp}

• Símbolo: `{symbol}`
• Lado: `{side.upper()}`
• Cantidad: `{amount:,.4f}`
• Precio: `{price:,.4f}`
• PnL: `{pnl:+.2f} USDT` {pnl_emoji}

🤖 Bot Trading v10 Enterprise
            """.strip()
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Notificación de trade enviada: {symbol} {side}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando notificación de trade: {e}")
            return False
    
    async def get_metrics_from_redis(self, redis_manager) -> Dict[str, Any]:
        """Obtener métricas desde Redis"""
        try:
            if not redis_manager:
                return {}
            
            # Obtener métricas básicas
            metrics = {}
            
            # Métricas de trading
            metrics['trades'] = await redis_manager.get('trading:trades_count', 0)
            metrics['win_rate'] = await redis_manager.get('trading:win_rate', 0.0)
            metrics['daily_pnl'] = await redis_manager.get('trading:daily_pnl', 0.0)
            metrics['balance'] = await redis_manager.get('trading:balance', 0.0)
            metrics['balance_pct'] = await redis_manager.get('trading:balance_pct', 0.0)
            
            # Métricas de rendimiento
            metrics['total_pnl'] = await redis_manager.get('performance:total_pnl', 0.0)
            metrics['max_drawdown'] = await redis_manager.get('performance:max_drawdown', 0.0)
            metrics['sharpe_ratio'] = await redis_manager.get('performance:sharpe_ratio', 0.0)
            
            # Métricas de sistema
            metrics['cpu_usage'] = await redis_manager.get('system:cpu_usage', 0.0)
            metrics['memory_usage'] = await redis_manager.get('system:memory_usage', 0.0)
            metrics['latency_ms'] = await redis_manager.get('system:latency_ms', 0)
            
            # Métricas de datos
            metrics['data_points'] = await redis_manager.get('data:points_count', 0)
            metrics['cache_hits'] = await redis_manager.get('cache:hits', 0)
            metrics['cache_misses'] = await redis_manager.get('cache:misses', 0)
            
            # Estado del bot
            metrics['bot_active'] = await redis_manager.get('bot:active', True)
            metrics['active_positions'] = await redis_manager.get('trading:active_positions', 0)
            metrics['max_positions'] = await redis_manager.get('trading:max_positions', 10)
            metrics['risk_per_trade'] = await redis_manager.get('trading:risk_per_trade', 2.0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de Redis: {e}")
            return {}
    
    async def get_metrics_from_timescale(self, timescale_manager) -> Dict[str, Any]:
        """Obtener métricas desde TimescaleDB"""
        try:
            if not timescale_manager:
                return {}
            
            # Obtener métricas de rendimiento
            performance_metrics = await timescale_manager.get_performance_metrics()
            
            # Obtener métricas de trading
            trading_metrics = await timescale_manager.get_trading_metrics()
            
            # Combinar métricas
            metrics = {**performance_metrics, **trading_metrics}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de TimescaleDB: {e}")
            return {}
    
    async def metrics_loop(self, redis_manager=None, timescale_manager=None):
        """Loop principal para enviar métricas periódicamente"""
        logger.info(f"Iniciando loop de métricas cada {self.metrics_interval} segundos")
        
        while True:
            try:
                # Obtener métricas desde Redis (prioridad)
                metrics = await self.get_metrics_from_redis(redis_manager)
                
                # Si no hay métricas en Redis, intentar TimescaleDB
                if not metrics and timescale_manager:
                    metrics = await self.get_metrics_from_timescale(timescale_manager)
                
                # Si no hay métricas, usar valores por defecto
                if not metrics:
                    metrics = {
                        'trades': 0,
                        'win_rate': 0.0,
                        'daily_pnl': 0.0,
                        'balance': 0.0,
                        'balance_pct': 0.0,
                        'bot_active': True
                    }
                
                # Enviar actualización
                await self.send_training_update(metrics)
                
            except Exception as e:
                logger.error(f"Error en loop de métricas: {e}")
                
                # Enviar alerta de error
                await self.send_alert(
                    "ERROR_METRICS",
                    f"Error en loop de métricas: {str(e)}",
                    "ERROR"
                )
            
            # Esperar antes de la siguiente iteración
            await asyncio.sleep(self.metrics_interval)
    
    async def start(self, redis_manager=None, timescale_manager=None):
        """Iniciar el sistema de métricas"""
        logger.info("Iniciando sistema de métricas...")
        
        # Enviar mensaje de inicio
        await self.send_alert(
            "SYSTEM_START",
            "Sistema de métricas iniciado correctamente",
            "SUCCESS"
        )
        
        # Iniciar loop de métricas
        await self.metrics_loop(redis_manager, timescale_manager)
    
    async def stop(self):
        """Detener el sistema de métricas"""
        logger.info("Deteniendo sistema de métricas...")
        
        # Enviar mensaje de parada
        await self.send_alert(
            "SYSTEM_STOP",
            "Sistema de métricas detenido",
            "INFO"
        )

# Función de conveniencia para uso directo
async def send_training_update(metrics: Dict[str, Any]) -> bool:
    """Función de conveniencia para enviar actualización de entrenamiento"""
    sender = MetricsSender()
    return await sender.send_training_update(metrics)

# Función para iniciar el sistema
async def start_metrics_system(redis_manager=None, timescale_manager=None):
    """Iniciar el sistema de métricas"""
    sender = MetricsSender()
    await sender.start(redis_manager, timescale_manager)
