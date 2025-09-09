#!/usr/bin/env python3
"""
Metrics Sender para Telegram Bot - Trading Bot v10 Enterprise
============================================================

Sistema de envío de métricas periódicas y monitoreo de alertas.
Envía métricas del sistema cada X minutos y verifica alertas automáticamente.

Características:
- Envío periódico de métricas
- Monitoreo de alertas automático
- Formateo personalizado de mensajes
- Manejo de errores robusto
- Configuración flexible de intervalos

Autor: Bot Trading v10 Enterprise
Versión: 10.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class MetricsSender:
    """Sistema de envío de métricas periódicas"""
    
    def __init__(self, telegram_bot, config: Dict[str, Any]):
        self.telegram_bot = telegram_bot
        self.config = config
        self.alerting_system = None
        self.data_provider = None
        self.trading_engine = None
        
        # Configuración
        self.metrics_interval = config.get('metrics_interval', 300)  # 5 minutos por defecto
        self.alert_thresholds = config.get('alert_thresholds', {})
        self.is_running = False
        
        # Inicializar componentes
        self._init_components()
        
        # Historial de alertas para evitar spam
        self.alert_history = {}
        self.alert_cooldown = 300  # 5 minutos entre alertas del mismo tipo
        
        logger.info("📊 MetricsSender inicializado")
    
    def _init_components(self):
        """Inicializa los componentes del sistema"""
        try:
            # Importar componentes de forma lazy
            from src.core.monitoring.enterprise.alerting_system import AlertingSystem
            from src.core.monitoring.core.data_provider import DataProvider
            from src.core.trading.execution_engine import ExecutionEngine
            
            self.alerting_system = AlertingSystem()
            self.data_provider = DataProvider()
            self.trading_engine = ExecutionEngine()
            
        except ImportError as e:
            logger.warning(f"⚠️ No se pudieron importar algunos componentes: {e}")
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
    
    async def start_sending_metrics(self):
        """Inicia el envío periódico de métricas"""
        self.is_running = True
        logger.info(f"📊 Iniciando envío de métricas cada {self.metrics_interval} segundos")
        
        while self.is_running:
            try:
                # Obtener métricas actuales
                metrics = await self.get_current_metrics()
                
                # Formatear y enviar mensaje
                message = self.format_metrics_message(metrics)
                await self.telegram_bot.send_message(message)
                
                logger.info("📤 Métricas enviadas correctamente")
                
            except Exception as e:
                logger.error(f"❌ Error enviando métricas: {e}")
            
            # Esperar antes del siguiente envío
            await asyncio.sleep(self.metrics_interval)
    
    async def start_alert_monitoring(self):
        """Inicia el monitoreo de alertas"""
        logger.info("🚨 Iniciando monitoreo de alertas")
        
        while self.is_running:
            try:
                await self.check_alerts()
            except Exception as e:
                logger.error(f"❌ Error verificando alertas: {e}")
            
            # Verificar alertas cada minuto
            await asyncio.sleep(60)
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas actuales del sistema"""
        try:
            if self.alerting_system and hasattr(self.alerting_system, 'get_system_metrics'):
                return await self.alerting_system.get_system_metrics()
            else:
                # Fallback con datos simulados
                return self._get_simulated_metrics()
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas: {e}")
            return self._get_simulated_metrics()
    
    def _get_simulated_metrics(self) -> Dict[str, Any]:
        """Genera métricas simuladas para testing"""
        import random
        
        return {
            'balance': 10000.0 + random.uniform(-500, 500),
            'pnl_today': random.uniform(-200, 300),
            'win_rate': random.uniform(60, 85),
            'drawdown': random.uniform(0, 5),
            'latency': random.uniform(30, 80),
            'trades_today': random.randint(0, 20),
            'positions': random.randint(0, 5),
            'health_score': random.uniform(85, 98)
        }
    
    def format_metrics_message(self, metrics: Dict[str, Any]) -> str:
        """Formatea las métricas en un mensaje legible"""
        try:
            # Determinar emoji de estado
            pnl = metrics.get('pnl_today', 0)
            if pnl > 0:
                pnl_emoji = "📈"
            elif pnl < 0:
                pnl_emoji = "📉"
            else:
                pnl_emoji = "➡️"
            
            # Determinar emoji de salud
            health = metrics.get('health_score', 0)
            if health >= 90:
                health_emoji = "🟢"
            elif health >= 70:
                health_emoji = "🟡"
            else:
                health_emoji = "🔴"
            
            # Formatear mensaje
            message = f"""
📊 <b>Métricas del Sistema</b>
⏰ {datetime.now().strftime('%H:%M:%S')}

💰 <b>Balance:</b> ${metrics.get('balance', 0):,.2f}
{pnl_emoji} <b>PnL Hoy:</b> ${pnl:,.2f}
🎯 <b>Win Rate:</b> {metrics.get('win_rate', 0):.1f}%
📉 <b>Drawdown:</b> {metrics.get('drawdown', 0):.1f}%
⚡ <b>Latencia:</b> {metrics.get('latency', 0):.1f}ms
🔄 <b>Trades:</b> {metrics.get('trades_today', 0)}
📊 <b>Posiciones:</b> {metrics.get('positions', 0)}
{health_emoji} <b>Salud:</b> {health:.1f}%
            """
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"❌ Error formateando métricas: {e}")
            return "❌ Error obteniendo métricas del sistema"
    
    async def check_alerts(self):
        """Verifica si hay alertas que enviar"""
        try:
            metrics = await self.get_current_metrics()
            
            # Verificar alerta de PnL
            await self._check_pnl_alert(metrics)
            
            # Verificar alerta de drawdown
            await self._check_drawdown_alert(metrics)
            
            # Verificar alerta de latencia
            await self._check_latency_alert(metrics)
            
            # Verificar alerta de salud
            await self._check_health_alert(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error verificando alertas: {e}")
    
    async def _check_pnl_alert(self, metrics: Dict[str, Any]):
        """Verifica alerta de PnL"""
        pnl_threshold = self.alert_thresholds.get('pnl_alert', 1000)
        pnl_today = metrics.get('pnl_today', 0)
        
        if abs(pnl_today) >= pnl_threshold:
            alert_key = f"pnl_{pnl_today > 0}"
            
            if self._should_send_alert(alert_key):
                if pnl_today > 0:
                    message = f"🎉 <b>¡Excelente PnL!</b>\n\nPnL del día: ${pnl_today:,.2f}"
                else:
                    message = f"⚠️ <b>Pérdida significativa</b>\n\nPnL del día: ${pnl_today:,.2f}"
                
                await self.telegram_bot.send_alert(message, "PNL")
                self._record_alert(alert_key)
    
    async def _check_drawdown_alert(self, metrics: Dict[str, Any]):
        """Verifica alerta de drawdown"""
        drawdown_threshold = self.alert_thresholds.get('risk_alert', 10)
        drawdown = metrics.get('drawdown', 0)
        
        if drawdown >= drawdown_threshold:
            alert_key = "drawdown"
            
            if self._should_send_alert(alert_key):
                message = f"🚨 <b>Drawdown Alto</b>\n\nDrawdown actual: {drawdown:.1f}%\nLímite: {drawdown_threshold}%"
                await self.telegram_bot.send_alert(message, "RISK")
                self._record_alert(alert_key)
    
    async def _check_latency_alert(self, metrics: Dict[str, Any]):
        """Verifica alerta de latencia"""
        latency_threshold = self.alert_thresholds.get('latency_alert', 100)
        latency = metrics.get('latency', 0)
        
        if latency >= latency_threshold:
            alert_key = "latency"
            
            if self._should_send_alert(alert_key):
                message = f"🐌 <b>Latencia Alta</b>\n\nLatencia actual: {latency:.1f}ms\nLímite: {latency_threshold}ms"
                await self.telegram_bot.send_alert(message, "PERFORMANCE")
                self._record_alert(alert_key)
    
    async def _check_health_alert(self, metrics: Dict[str, Any]):
        """Verifica alerta de salud del sistema"""
        health = metrics.get('health_score', 100)
        
        if health < 70:  # Salud crítica
            alert_key = "health_critical"
            
            if self._should_send_alert(alert_key):
                message = f"🔴 <b>Salud Crítica</b>\n\nHealth Score: {health:.1f}%\nEl sistema necesita atención inmediata"
                await self.telegram_bot.send_alert(message, "CRITICAL")
                self._record_alert(alert_key)
        
        elif health < 85:  # Salud baja
            alert_key = "health_low"
            
            if self._should_send_alert(alert_key):
                message = f"🟡 <b>Salud Baja</b>\n\nHealth Score: {health:.1f}%\nMonitorea el sistema"
                await self.telegram_bot.send_alert(message, "WARNING")
                self._record_alert(alert_key)
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Verifica si se debe enviar una alerta (evita spam)"""
        now = datetime.now()
        
        if alert_key in self.alert_history:
            last_sent = self.alert_history[alert_key]
            if (now - last_sent).total_seconds() < self.alert_cooldown:
                return False
        
        return True
    
    def _record_alert(self, alert_key: str):
        """Registra el envío de una alerta"""
        self.alert_history[alert_key] = datetime.now()
    
    def stop(self):
        """Detiene el envío de métricas"""
        self.is_running = False
        logger.info("🛑 MetricsSender detenido")
    
    def update_config(self, new_config: Dict[str, Any]):
        """Actualiza la configuración"""
        self.config = new_config
        self.metrics_interval = new_config.get('metrics_interval', 300)
        self.alert_thresholds = new_config.get('alert_thresholds', {})
        logger.info("✅ Configuración de MetricsSender actualizada")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado del MetricsSender"""
        return {
            'is_running': self.is_running,
            'metrics_interval': self.metrics_interval,
            'alert_thresholds': self.alert_thresholds,
            'last_alert': max(self.alert_history.values()) if self.alert_history else None,
            'total_alerts_sent': len(self.alert_history)
        }
