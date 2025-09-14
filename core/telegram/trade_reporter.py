#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/telegram/trade_reporter.py
===============================
Sistema de Reporting Telegram Mejorado para Trades Individuales

Proporciona reportes detallados de cada trade individual y resúmenes de ciclo
con formato visual atractivo, emojis dinámicos y análisis completo.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from ..metrics.trade_metrics import DetailedTradeMetric
from ..sync.enhanced_metrics_aggregator import PortfolioMetrics

logger = logging.getLogger(__name__)

@dataclass
class TelegramConfig:
    """Configuración para Telegram"""
    bot_token: str
    chat_id: str
    rate_limit_delay: float = 0.1  # Delay entre mensajes
    max_message_length: int = 4096
    enable_individual_trades: bool = True
    enable_cycle_summaries: bool = True
    enable_alerts: bool = True

class TelegramTradeReporter:
    """Reporter especializado para trades individuales y resúmenes de ciclo"""
    
    def __init__(self, config: TelegramConfig):
        """
        Inicializa el reporter de Telegram
        
        Args:
            config: Configuración de Telegram
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self._last_message_time = datetime.min
        self._message_queue = asyncio.Queue()
        
        # Estadísticas
        self.messages_sent = 0
        self.trades_reported = 0
        self.cycles_reported = 0
        
        self.logger.info("✅ TelegramTradeReporter inicializado")
    
    async def send_individual_trade_alert(self, trade: DetailedTradeMetric) -> bool:
        """
        Envía alerta de trade individual con todos los detalles
        
        Args:
            trade: Métrica detallada del trade
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            if not self.config.enable_individual_trades:
                return True
            
            # Emojis dinámicos basados en resultado
            direction_emoji = "🟢📈" if trade.action.value in ['LONG', 'CLOSE_SHORT'] else "🔴📉"
            result_emoji = "✅💰" if trade.was_successful else "❌💸"
            
            # Emoji de calidad
            quality_emoji = self._get_quality_emoji(trade.get_quality_score())
            
            # Emoji de confianza
            confidence_emoji = self._get_confidence_emoji(trade.confidence_level.value)
            
            # Formatear duración
            duration_str = self._format_duration(trade.duration_hours)
            
            # Formatear precios
            entry_price_str = f"${trade.entry_price:,.4f}"
            exit_price_str = f"${trade.exit_price:,.4f}"
            
            # Formatear PnL
            pnl_emoji = "📈" if trade.pnl_usdt > 0 else "📉"
            pnl_str = f"{pnl_emoji} {trade.pnl_usdt:+.2f} USDT ({trade.pnl_percentage:+.2f}%)"
            
            # Formatear balance
            balance_str = f"${trade.balance_after:,.2f}"
            
            # Emoji de estrategia
            strategy_emoji = self._get_strategy_emoji(trade.strategy_name)
            
            # Emoji de mercado
            market_emoji = self._get_market_emoji(trade.market_regime.value)
            
            # Construir mensaje
            message = f"""
{result_emoji} **TRADE COMPLETADO** {direction_emoji} {quality_emoji}

🤖 **Agente:** `{trade.agent_symbol}`
📅 **Ciclo:** #{trade.cycle_id:04d}
⏰ **Tiempo:** {trade.timestamp.strftime('%H:%M:%S')}

💹 **OPERACIÓN:**
• **Dirección:** {trade.action.value} {direction_emoji}
• **Apalancamiento:** {trade.leverage}x
• **Precio entrada:** {entry_price_str}
• **Precio salida:** {exit_price_str}
• **Cantidad:** {trade.quantity:,.4f} {trade.agent_symbol.replace('USDT', '')}

⏱️ **DURACIÓN:**
• **Velas:** {trade.duration_candles} 📊
• **Tiempo:** {duration_str}

💰 **RESULTADOS:**
• **PnL:** {pnl_str}
• **Capital usado:** ${trade.balance_used:,.2f}
• **Balance nuevo:** {balance_str}

🎯 **ANÁLISIS:**
• **Confianza:** {confidence_emoji} {trade.confidence_level.value} ({trade.confluence_score:.0%})
• **Estrategia:** {strategy_emoji} {trade.strategy_name}
• **R:R Ratio:** {trade.risk_reward_ratio:.1f}
• **Salida por:** {trade.exit_reason.value}

📊 **CONTEXTO:**
• **Mercado:** {market_emoji} {trade.market_regime.value.replace('_', ' ').title()}
• **Volatilidad:** {trade.volatility_level:.1%}
• **Volumen:** {"✅" if trade.volume_confirmation else "⚠️"}
• **Timeframe:** {trade.timeframe_analyzed}

🔧 **CALIDAD:**
• **Score:** {trade.get_quality_score():.1f}/100
• **Sigue plan:** {"✅" if trade.follow_plan else "❌"}
• **Slippage:** {trade.execution_slippage:.4f}
• **Comisión:** ${trade.commission_paid:.4f}
            """.strip()
            
            # Enviar mensaje
            success = await self._send_message(message)
            
            if success:
                self.trades_reported += 1
                self.logger.info(f"✅ Trade reportado: {trade.agent_symbol} {trade.action.value} {trade.pnl_usdt:+.2f} USDT")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta de trade: {e}")
            return False
    
    async def send_cycle_summary(
        self, 
        cycle_metrics: PortfolioMetrics, 
        agent_summaries: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Envía resumen completo del ciclo
        
        Args:
            cycle_metrics: Métricas del portfolio
            agent_summaries: Resúmenes por agente
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            if not self.config.enable_cycle_summaries:
                return True
            
            # Emojis dinámicos
            pnl_emoji = "📈" if cycle_metrics.total_pnl_usdt > 0 else "📉"
            performance_emoji = self._get_performance_emoji(cycle_metrics.portfolio_return_pct)
            
            # Formatear métricas financieras
            financial_section = f"""
💰 **PERFORMANCE GLOBAL:**
• **PnL Total:** {pnl_emoji} {cycle_metrics.total_pnl_usdt:+.2f} USDT
• **Retorno:** {performance_emoji} {cycle_metrics.portfolio_return_pct:+.2f}%
• **Sharpe Ratio:** {cycle_metrics.sharpe_ratio:.2f}
• **Win Rate:** {cycle_metrics.win_rate:.1%}
• **Max DD:** {cycle_metrics.max_drawdown_pct:.1f}%
            """.strip()
            
            # Formatear métricas de riesgo
            risk_section = f"""
⚖️ **GESTIÓN DE RIESGO:**
• **Diversificación:** {cycle_metrics.diversification_score:.1%}
• **Correlación Avg:** {cycle_metrics.correlation_avg:.2f}
• **VaR 95%:** -{cycle_metrics.var_95:.2f}%
• **Concentración:** {cycle_metrics.concentration_risk:.1%}
            """.strip()
            
            # Formatear métricas operacionales
            operational_section = f"""
🔄 **OPERACIONES:**
• **Total Trades:** {cycle_metrics.total_trades}
• **Duración Media:** {cycle_metrics.avg_trade_duration:.1f}h
• **Mejor Agente:** {cycle_metrics.best_performing_agent} 🥇
• **Peor Agente:** {cycle_metrics.worst_performing_agent} ⚠️
• **Eficiencia:** {cycle_metrics.efficiency_score:.1f}
            """.strip()
            
            # Formatear métricas de calidad
            quality_section = f"""
🎯 **CALIDAD:**
• **Score Promedio:** {cycle_metrics.avg_quality_score:.1f}/100
• **Trades Alta Calidad:** {cycle_metrics.high_quality_trades_pct:.1%}
• **Confluence Promedio:** {cycle_metrics.avg_confluence_score:.1%}
            """.strip()
            
            # Formatear resumen por agente
            agent_section = "📊 **PERFORMANCE POR AGENTE:**\n"
            for symbol, metrics in agent_summaries.items():
                pnl_emoji = "📈" if metrics['pnl'] > 0 else "📉"
                quality_emoji = self._get_quality_emoji(metrics.get('avg_quality_score', 5.0))
                
                agent_section += f"""
**{symbol}:** {pnl_emoji} {quality_emoji}
├ PnL: {metrics['pnl']:+.2f} USDT
├ Trades: {metrics['trades']} (WR: {metrics['win_rate']:.0%})
└ DD: {metrics.get('drawdown', 0.0):.1f}%
                """.strip() + "\n"
            
            # Construir mensaje completo
            message = f"""
🎯 **RESUMEN CICLO #{cycle_metrics.cycle_id:04d}**
⏰ **Completado:** {cycle_metrics.timestamp.strftime('%d/%m %H:%M')}

{financial_section}

{risk_section}

{operational_section}

{quality_section}

{agent_section}
            """.strip()
            
            # Enviar mensaje
            success = await self._send_message(message)
            
            if success:
                self.cycles_reported += 1
                self.logger.info(f"✅ Resumen de ciclo #{cycle_metrics.cycle_id} enviado")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando resumen de ciclo: {e}")
            return False
    
    async def send_performance_alert(
        self, 
        alert_type: str, 
        message: str, 
        severity: str = "INFO"
    ) -> bool:
        """
        Envía alerta de performance
        
        Args:
            alert_type: Tipo de alerta
            message: Mensaje de la alerta
            severity: Severidad (INFO, WARNING, CRITICAL)
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            if not self.config.enable_alerts:
                return True
            
            # Emojis por severidad
            severity_emojis = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "CRITICAL": "🚨"
            }
            
            severity_emoji = severity_emojis.get(severity, "ℹ️")
            
            # Emojis por tipo de alerta
            type_emojis = {
                "DRAWDOWN": "📉",
                "MILESTONE": "🎯",
                "ERROR": "❌",
                "DISCOVERY": "🔍",
                "PERFORMANCE": "📊"
            }
            
            type_emoji = type_emojis.get(alert_type, "📢")
            
            alert_message = f"""
{severity_emoji} **{alert_type}** {type_emoji}

{message}

⏰ **Tiempo:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            """.strip()
            
            return await self._send_message(alert_message)
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta: {e}")
            return False
    
    def _get_quality_emoji(self, quality_score: float) -> str:
        """Obtiene emoji basado en score de calidad"""
        if quality_score >= 80:
            return "🏆"
        elif quality_score >= 60:
            return "🥇"
        elif quality_score >= 40:
            return "🥈"
        elif quality_score >= 20:
            return "🥉"
        else:
            return "⚠️"
    
    def _get_confidence_emoji(self, confidence_level: str) -> str:
        """Obtiene emoji basado en nivel de confianza"""
        emojis = {
            "VERY_HIGH": "🔥",
            "HIGH": "💪",
            "MEDIUM": "👍",
            "LOW": "👎",
            "VERY_LOW": "❌"
        }
        return emojis.get(confidence_level, "❓")
    
    def _get_strategy_emoji(self, strategy_name: str) -> str:
        """Obtiene emoji basado en nombre de estrategia"""
        strategy_lower = strategy_name.lower()
        
        if "trend" in strategy_lower:
            return "📈"
        elif "reversal" in strategy_lower:
            return "🔄"
        elif "breakout" in strategy_lower:
            return "🚀"
        elif "scalp" in strategy_lower:
            return "⚡"
        elif "swing" in strategy_lower:
            return "🌊"
        else:
            return "🎯"
    
    def _get_market_emoji(self, market_regime: str) -> str:
        """Obtiene emoji basado en régimen de mercado"""
        emojis = {
            "TRENDING_UP": "📈",
            "TRENDING_DOWN": "📉",
            "SIDEWAYS": "↔️",
            "HIGH_VOLATILITY": "⚡",
            "LOW_VOLATILITY": "😴",
            "BREAKOUT": "🚀",
            "REVERSAL": "🔄"
        }
        return emojis.get(market_regime, "❓")
    
    def _get_performance_emoji(self, return_pct: float) -> str:
        """Obtiene emoji basado en performance"""
        if return_pct >= 5:
            return "🚀"
        elif return_pct >= 2:
            return "📈"
        elif return_pct >= 0:
            return "📊"
        elif return_pct >= -2:
            return "📉"
        else:
            return "💸"
    
    def _format_duration(self, hours: float) -> str:
        """Formatea duración en formato legible"""
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        else:
            days = int(hours // 24)
            remaining_hours = hours % 24
            return f"{days}d {remaining_hours:.1f}h"
    
    async def _send_message(self, message: str) -> bool:
        """
        Envía mensaje a Telegram con rate limiting
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Rate limiting
            now = datetime.now()
            time_since_last = (now - self._last_message_time).total_seconds()
            
            if time_since_last < self.config.rate_limit_delay:
                await asyncio.sleep(self.config.rate_limit_delay - time_since_last)
            
            # Truncar mensaje si es muy largo
            if len(message) > self.config.max_message_length:
                message = message[:self.config.max_message_length - 3] + "..."
            
            # TODO: Implementar envío real a Telegram
            # Por ahora solo logueamos
            self.logger.info(f"📱 Telegram Message:\n{message}")
            
            self._last_message_time = datetime.now()
            self.messages_sent += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del reporter"""
        return {
            'messages_sent': self.messages_sent,
            'trades_reported': self.trades_reported,
            'cycles_reported': self.cycles_reported,
            'last_message_time': self._last_message_time.isoformat(),
            'queue_size': self._message_queue.qsize()
        }
    
    async def send_batch_trades(self, trades: List[DetailedTradeMetric]) -> int:
        """
        Envía múltiples trades en lote
        
        Args:
            trades: Lista de trades a enviar
            
        Returns:
            int: Número de trades enviados exitosamente
        """
        try:
            success_count = 0
            
            for trade in trades:
                success = await self.send_individual_trade_alert(trade)
                if success:
                    success_count += 1
                
                # Pequeño delay entre trades
                await asyncio.sleep(0.05)
            
            self.logger.info(f"✅ Lote de {len(trades)} trades enviado: {success_count} exitosos")
            return success_count
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando lote de trades: {e}")
            return 0
    
    async def send_daily_summary(
        self, 
        daily_metrics: Dict[str, Any], 
        top_trades: List[DetailedTradeMetric],
        worst_trades: List[DetailedTradeMetric]
    ) -> bool:
        """
        Envía resumen diario completo
        
        Args:
            daily_metrics: Métricas del día
            top_trades: Mejores trades del día
            worst_trades: Peores trades del día
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Emojis dinámicos
            daily_pnl = daily_metrics.get('total_pnl_usdt', 0)
            pnl_emoji = "📈" if daily_pnl > 0 else "📉"
            
            # Construir mensaje
            message = f"""
🌅 **RESUMEN DIARIO** {pnl_emoji}

📊 **MÉTRICAS:**
• **PnL Total:** {daily_pnl:+.2f} USDT
• **Trades:** {daily_metrics.get('total_trades', 0)}
• **Win Rate:** {daily_metrics.get('win_rate', 0):.1%}
• **Sharpe:** {daily_metrics.get('sharpe_ratio', 0):.2f}

🏆 **TOP TRADES:**
            """.strip()
            
            # Agregar mejores trades
            for i, trade in enumerate(top_trades[:3], 1):
                message += f"""
{i}. {trade.agent_symbol} {trade.action.value} {trade.pnl_usdt:+.2f} USDT
   {trade.strategy_name} ({trade.get_quality_score():.1f}/100)
                """.strip()
            
            message += "\n\n💸 **WORST TRADES:**"
            
            # Agregar peores trades
            for i, trade in enumerate(worst_trades[:3], 1):
                message += f"""
{i}. {trade.agent_symbol} {trade.action.value} {trade.pnl_usdt:+.2f} USDT
   {trade.strategy_name} ({trade.get_quality_score():.1f}/100)
                """.strip()
            
            return await self._send_message(message)
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando resumen diario: {e}")
            return False
