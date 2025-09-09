#!/usr/bin/env python3
"""
Monitor de Riesgo Enterprise - Tiempo Real
=========================================

Este módulo implementa monitoreo de riesgo en tiempo real con alertas
automáticas y gestión de límites de riesgo.

Características:
- Monitoreo de drawdown en tiempo real
- Alertas de margen y exposición
- Gestión de límites de riesgo
- Circuit breakers automáticos
- Análisis de correlación de posiciones

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import numpy as np
import pandas as pd
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from prometheus_client.core import CollectorRegistry

from trading.bitget_client import bitget_client
from config.config_loader import user_config

# Configurar logging
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Niveles de riesgo"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    """Métricas de riesgo en tiempo real"""
    timestamp: datetime
    portfolio_value: float
    total_exposure: float
    exposure_percentage: float
    margin_used: float
    margin_available: float
    margin_ratio: float
    current_drawdown: float
    max_drawdown: float
    var_95: float
    var_99: float
    expected_shortfall: float
    sharpe_ratio: float
    calmar_ratio: float
    max_position_size: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    market_risk: float
    operational_risk: float
    risk_score: float
    risk_level: RiskLevel
    alerts_count: int
    circuit_breaker_active: bool

class RiskMonitor:
    """Monitor de riesgo enterprise en tiempo real"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = user_config.get_value(['risk_management'], {})
        self.bitget_client = bitget_client
        
        # Métricas de Prometheus
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Estado del monitor
        self.is_running = False
        self.start_time = None
        self.last_metrics = None
        self.risk_history = []
        self.max_history = 10000
        
        # Configuración de riesgo
        self.risk_limits = self.config.get('risk_limits', {})
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        self.circuit_breakers = self.config.get('circuit_breakers', {})
        
        # Estado de circuit breakers
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        self.circuit_breaker_time = None
        
        # Directorios
        self.setup_directories()
        
        logger.info("⚠️ RiskMonitor enterprise inicializado")
    
    def _setup_prometheus_metrics(self):
        """Configura las métricas de Prometheus"""
        # Métricas de exposición
        self.exposure_gauge = Gauge(
            'risk_total_exposure', 
            'Total portfolio exposure in USDT',
            registry=self.registry
        )
        
        self.exposure_pct_gauge = Gauge(
            'risk_exposure_percentage', 
            'Portfolio exposure percentage',
            registry=self.registry
        )
        
        # Métricas de margen
        self.margin_used_gauge = Gauge(
            'risk_margin_used', 
            'Margin used in USDT',
            registry=self.registry
        )
        
        self.margin_available_gauge = Gauge(
            'risk_margin_available', 
            'Margin available in USDT',
            registry=self.registry
        )
        
        self.margin_ratio_gauge = Gauge(
            'risk_margin_ratio', 
            'Margin ratio',
            registry=self.registry
        )
        
        # Métricas de drawdown
        self.current_drawdown_gauge = Gauge(
            'risk_current_drawdown', 
            'Current drawdown percentage',
            registry=self.registry
        )
        
        self.max_drawdown_gauge = Gauge(
            'risk_max_drawdown', 
            'Maximum drawdown percentage',
            registry=self.registry
        )
        
        # Métricas de VaR
        self.var_95_gauge = Gauge(
            'risk_var_95', 
            'Value at Risk 95%',
            registry=self.registry
        )
        
        self.var_99_gauge = Gauge(
            'risk_var_99', 
            'Value at Risk 99%',
            registry=self.registry
        )
        
        self.expected_shortfall_gauge = Gauge(
            'risk_expected_shortfall', 
            'Expected Shortfall',
            registry=self.registry
        )
        
        # Métricas de riesgo
        self.risk_score_gauge = Gauge(
            'risk_score', 
            'Overall risk score (0-100)',
            registry=self.registry
        )
        
        self.correlation_risk_gauge = Gauge(
            'risk_correlation', 
            'Correlation risk score',
            registry=self.registry
        )
        
        self.concentration_risk_gauge = Gauge(
            'risk_concentration', 
            'Concentration risk score',
            registry=self.registry
        )
        
        self.liquidity_risk_gauge = Gauge(
            'risk_liquidity', 
            'Liquidity risk score',
            registry=self.registry
        )
        
        self.market_risk_gauge = Gauge(
            'risk_market', 
            'Market risk score',
            registry=self.registry
        )
        
        self.operational_risk_gauge = Gauge(
            'risk_operational', 
            'Operational risk score',
            registry=self.registry
        )
        
        # Métricas de circuit breakers
        self.circuit_breaker_gauge = Gauge(
            'risk_circuit_breaker_active', 
            'Circuit breaker active (1=yes, 0=no)',
            registry=self.registry
        )
        
        # Contadores de alertas
        self.alerts_counter = Counter(
            'risk_alerts_total', 
            'Total number of risk alerts',
            ['severity', 'type'],
            registry=self.registry
        )
        
        # Histogramas
        self.risk_score_histogram = Histogram(
            'risk_score_distribution', 
            'Risk score distribution',
            buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            registry=self.registry
        )
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/risk_monitoring',
            'data/enterprise/risk_monitoring',
            'backups/enterprise/risk_monitoring'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Inicializa el monitor de riesgo"""
        try:
            logger.info("🔧 Inicializando RiskMonitor...")
            
            # Iniciar servidor Prometheus
            prometheus_port = self.config.get('prometheus_port', 8004)
            start_http_server(prometheus_port, registry=self.registry)
            logger.info(f"📊 Servidor Prometheus iniciado en puerto {prometheus_port}")
            
            # Cargar historial de riesgo
            await self.load_risk_history()
            
            logger.info("✅ RiskMonitor inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando RiskMonitor: {e}")
            return False
    
    async def start_monitoring(self):
        """Inicia el monitoreo de riesgo en tiempo real"""
        try:
            logger.info("🚀 Iniciando monitoreo de riesgo...")
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Loop principal de monitoreo
            while self.is_running:
                try:
                    # Recopilar métricas de riesgo
                    metrics = await self.collect_risk_metrics()
                    
                    # Actualizar métricas de Prometheus
                    self.update_prometheus_metrics(metrics)
                    
                    # Guardar en historial
                    self.risk_history.append(metrics)
                    if len(self.risk_history) > self.max_history:
                        self.risk_history.pop(0)
                    
                    # Verificar límites de riesgo
                    await self.check_risk_limits(metrics)
                    
                    # Verificar circuit breakers
                    await self.check_circuit_breakers(metrics)
                    
                    # Guardar métricas en archivo
                    await self.save_risk_metrics_to_file(metrics)
                    
                    self.last_metrics = metrics
                    
                    # Esperar antes de la siguiente actualización
                    await asyncio.sleep(5)  # Monitoreo cada 5 segundos
                    
                except Exception as e:
                    logger.error(f"Error en loop de monitoreo de riesgo: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Error en monitoreo de riesgo: {e}")
        finally:
            self.is_running = False
    
    async def collect_risk_metrics(self) -> RiskMetrics:
        """Recopila métricas de riesgo en tiempo real"""
        try:
            # Obtener información de la cuenta
            balance_info = await self.bitget_client.get_margin_info()
            portfolio_value = balance_info.get('total_balance', 0) if balance_info else 0
            
            # Obtener posiciones
            positions = await self.bitget_client.get_positions()
            
            # Calcular exposición total
            total_exposure = sum(
                pos.get('size', 0) * pos.get('mark_price', 0) 
                for pos in positions
            )
            
            exposure_percentage = (total_exposure / portfolio_value * 100) if portfolio_value > 0 else 0
            
            # Calcular métricas de margen
            margin_used = balance_info.get('used_balance', 0) if balance_info else 0
            margin_available = balance_info.get('free_balance', 0) if balance_info else 0
            margin_ratio = balance_info.get('margin_ratio', 0) if balance_info else 0
            
            # Calcular drawdown
            current_drawdown = await self.calculate_current_drawdown()
            max_drawdown = await self.calculate_max_drawdown()
            
            # Calcular VaR
            var_95 = await self.calculate_var(0.95)
            var_99 = await self.calculate_var(0.99)
            expected_shortfall = await self.calculate_expected_shortfall()
            
            # Calcular ratios de riesgo
            sharpe_ratio = await self.calculate_sharpe_ratio()
            calmar_ratio = await self.calculate_calmar_ratio()
            
            # Calcular métricas de riesgo específicas
            max_position_size = await self.calculate_max_position_size(positions)
            correlation_risk = await self.calculate_correlation_risk(positions)
            concentration_risk = await self.calculate_concentration_risk(positions)
            liquidity_risk = await self.calculate_liquidity_risk(positions)
            market_risk = await self.calculate_market_risk(positions)
            operational_risk = await self.calculate_operational_risk()
            
            # Calcular score de riesgo general
            risk_score = await self.calculate_risk_score(
                current_drawdown, max_drawdown, var_95, var_99,
                correlation_risk, concentration_risk, liquidity_risk,
                market_risk, operational_risk
            )
            
            # Determinar nivel de riesgo
            risk_level = self.determine_risk_level(risk_score)
            
            # Contar alertas activas
            alerts_count = await self.count_active_alerts()
            
            # Crear objeto de métricas
            metrics = RiskMetrics(
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                total_exposure=total_exposure,
                exposure_percentage=exposure_percentage,
                margin_used=margin_used,
                margin_available=margin_available,
                margin_ratio=margin_ratio,
                current_drawdown=current_drawdown,
                max_drawdown=max_drawdown,
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                max_position_size=max_position_size,
                correlation_risk=correlation_risk,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk,
                market_risk=market_risk,
                operational_risk=operational_risk,
                risk_score=risk_score,
                risk_level=risk_level,
                alerts_count=alerts_count,
                circuit_breaker_active=self.circuit_breaker_active
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recopilando métricas de riesgo: {e}")
            # Retornar métricas por defecto en caso de error
            return RiskMetrics(
                timestamp=datetime.now(),
                portfolio_value=0,
                total_exposure=0,
                exposure_percentage=0,
                margin_used=0,
                margin_available=0,
                margin_ratio=0,
                current_drawdown=0,
                max_drawdown=0,
                var_95=0,
                var_99=0,
                expected_shortfall=0,
                sharpe_ratio=0,
                calmar_ratio=0,
                max_position_size=0,
                correlation_risk=0,
                concentration_risk=0,
                liquidity_risk=0,
                market_risk=0,
                operational_risk=0,
                risk_score=0,
                risk_level=RiskLevel.LOW,
                alerts_count=0,
                circuit_breaker_active=False
            )
    
    async def calculate_current_drawdown(self) -> float:
        """Calcula el drawdown actual"""
        try:
            # Implementar cálculo de drawdown actual
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando drawdown actual: {e}")
            return 0.0
    
    async def calculate_max_drawdown(self) -> float:
        """Calcula el drawdown máximo"""
        try:
            # Implementar cálculo de drawdown máximo
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando drawdown máximo: {e}")
            return 0.0
    
    async def calculate_var(self, confidence_level: float) -> float:
        """Calcula el Value at Risk"""
        try:
            # Implementar cálculo de VaR
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando VaR: {e}")
            return 0.0
    
    async def calculate_expected_shortfall(self) -> float:
        """Calcula el Expected Shortfall (CVaR)"""
        try:
            # Implementar cálculo de Expected Shortfall
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando Expected Shortfall: {e}")
            return 0.0
    
    async def calculate_sharpe_ratio(self) -> float:
        """Calcula el ratio de Sharpe"""
        try:
            # Implementar cálculo de Sharpe ratio
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando Sharpe ratio: {e}")
            return 0.0
    
    async def calculate_calmar_ratio(self) -> float:
        """Calcula el ratio de Calmar"""
        try:
            # Implementar cálculo de Calmar ratio
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando Calmar ratio: {e}")
            return 0.0
    
    async def calculate_max_position_size(self, positions: List[Dict]) -> float:
        """Calcula el tamaño máximo de posición"""
        try:
            if not positions:
                return 0.0
            
            max_size = max(pos.get('size', 0) for pos in positions)
            return max_size
        except Exception as e:
            logger.error(f"Error calculando tamaño máximo de posición: {e}")
            return 0.0
    
    async def calculate_correlation_risk(self, positions: List[Dict]) -> float:
        """Calcula el riesgo de correlación"""
        try:
            # Implementar cálculo de riesgo de correlación
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando riesgo de correlación: {e}")
            return 0.0
    
    async def calculate_concentration_risk(self, positions: List[Dict]) -> float:
        """Calcula el riesgo de concentración"""
        try:
            if not positions:
                return 0.0
            
            # Calcular índice de Herfindahl-Hirschman
            total_value = sum(pos.get('size', 0) * pos.get('mark_price', 0) for pos in positions)
            if total_value <= 0:
                return 0.0
            
            hhi = sum(
                (pos.get('size', 0) * pos.get('mark_price', 0) / total_value) ** 2
                for pos in positions
            )
            
            return hhi * 100  # Convertir a porcentaje
        except Exception as e:
            logger.error(f"Error calculando riesgo de concentración: {e}")
            return 0.0
    
    async def calculate_liquidity_risk(self, positions: List[Dict]) -> float:
        """Calcula el riesgo de liquidez"""
        try:
            # Implementar cálculo de riesgo de liquidez
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando riesgo de liquidez: {e}")
            return 0.0
    
    async def calculate_market_risk(self, positions: List[Dict]) -> float:
        """Calcula el riesgo de mercado"""
        try:
            # Implementar cálculo de riesgo de mercado
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando riesgo de mercado: {e}")
            return 0.0
    
    async def calculate_operational_risk(self) -> float:
        """Calcula el riesgo operacional"""
        try:
            # Implementar cálculo de riesgo operacional
            return 0.0
        except Exception as e:
            logger.error(f"Error calculando riesgo operacional: {e}")
            return 0.0
    
    async def calculate_risk_score(
        self, current_drawdown: float, max_drawdown: float, var_95: float, var_99: float,
        correlation_risk: float, concentration_risk: float, liquidity_risk: float,
        market_risk: float, operational_risk: float
    ) -> float:
        """Calcula el score de riesgo general (0-100)"""
        try:
            # Ponderar diferentes tipos de riesgo
            weights = {
                'drawdown': 0.25,
                'var': 0.20,
                'correlation': 0.15,
                'concentration': 0.15,
                'liquidity': 0.10,
                'market': 0.10,
                'operational': 0.05
            }
            
            # Normalizar métricas a escala 0-100
            drawdown_score = min(current_drawdown * 2, 100)  # 50% drawdown = 100 score
            var_score = min(var_99 * 10, 100)  # Ajustar según el rango de VaR
            correlation_score = correlation_risk
            concentration_score = concentration_risk
            liquidity_score = liquidity_risk
            market_score = market_risk
            operational_score = operational_risk
            
            # Calcular score ponderado
            risk_score = (
                weights['drawdown'] * drawdown_score +
                weights['var'] * var_score +
                weights['correlation'] * correlation_score +
                weights['concentration'] * concentration_score +
                weights['liquidity'] * liquidity_score +
                weights['market'] * market_score +
                weights['operational'] * operational_score
            )
            
            return min(max(risk_score, 0), 100)
        except Exception as e:
            logger.error(f"Error calculando score de riesgo: {e}")
            return 0.0
    
    def determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determina el nivel de riesgo basado en el score"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def count_active_alerts(self) -> int:
        """Cuenta las alertas activas"""
        try:
            # Implementar conteo de alertas activas
            return 0
        except Exception as e:
            logger.error(f"Error contando alertas activas: {e}")
            return 0
    
    async def check_risk_limits(self, metrics: RiskMetrics):
        """Verifica los límites de riesgo"""
        try:
            # Verificar límite de drawdown
            max_drawdown_limit = self.risk_limits.get('max_drawdown', 15.0)
            if metrics.current_drawdown > max_drawdown_limit:
                await self.send_risk_alert(
                    "DRAWDOWN_LIMIT_EXCEEDED",
                    f"Drawdown actual: {metrics.current_drawdown:.2f}% (límite: {max_drawdown_limit}%)",
                    "critical"
                )
            
            # Verificar límite de exposición
            max_exposure_limit = self.risk_limits.get('max_exposure', 80.0)
            if metrics.exposure_percentage > max_exposure_limit:
                await self.send_risk_alert(
                    "EXPOSURE_LIMIT_EXCEEDED",
                    f"Exposición: {metrics.exposure_percentage:.2f}% (límite: {max_exposure_limit}%)",
                    "warning"
                )
            
            # Verificar límite de margen
            max_margin_limit = self.risk_limits.get('max_margin_ratio', 0.8)
            if metrics.margin_ratio > max_margin_limit:
                await self.send_risk_alert(
                    "MARGIN_LIMIT_EXCEEDED",
                    f"Ratio de margen: {metrics.margin_ratio:.2f} (límite: {max_margin_limit})",
                    "warning"
                )
            
            # Verificar límite de concentración
            max_concentration_limit = self.risk_limits.get('max_concentration', 50.0)
            if metrics.concentration_risk > max_concentration_limit:
                await self.send_risk_alert(
                    "CONCENTRATION_LIMIT_EXCEEDED",
                    f"Riesgo de concentración: {metrics.concentration_risk:.2f}% (límite: {max_concentration_limit}%)",
                    "warning"
                )
            
        except Exception as e:
            logger.error(f"Error verificando límites de riesgo: {e}")
    
    async def check_circuit_breakers(self, metrics: RiskMetrics):
        """Verifica los circuit breakers"""
        try:
            # Circuit breaker por drawdown crítico
            critical_drawdown = self.circuit_breakers.get('critical_drawdown', 25.0)
            if metrics.current_drawdown > critical_drawdown and not self.circuit_breaker_active:
                await self.activate_circuit_breaker(
                    "CRITICAL_DRAWDOWN",
                    f"Drawdown crítico: {metrics.current_drawdown:.2f}%"
                )
            
            # Circuit breaker por pérdida diaria
            daily_loss_limit = self.circuit_breakers.get('daily_loss_limit', 5000.0)
            if metrics.portfolio_value < (10000 - daily_loss_limit) and not self.circuit_breaker_active:
                await self.activate_circuit_breaker(
                    "DAILY_LOSS_LIMIT",
                    f"Pérdida diaria excedida: ${10000 - metrics.portfolio_value:.2f}"
                )
            
            # Circuit breaker por VaR excesivo
            max_var_limit = self.circuit_breakers.get('max_var', 2000.0)
            if metrics.var_99 > max_var_limit and not self.circuit_breaker_active:
                await self.activate_circuit_breaker(
                    "EXCESSIVE_VAR",
                    f"VaR excesivo: ${metrics.var_99:.2f}"
                )
            
        except Exception as e:
            logger.error(f"Error verificando circuit breakers: {e}")
    
    async def activate_circuit_breaker(self, reason: str, details: str):
        """Activa un circuit breaker"""
        try:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = reason
            self.circuit_breaker_time = datetime.now()
            
            logger.critical(f"🚨 CIRCUIT BREAKER ACTIVADO: {reason} - {details}")
            
            # Enviar alerta crítica
            await self.send_risk_alert(
                "CIRCUIT_BREAKER_ACTIVATED",
                f"{reason}: {details}",
                "critical"
            )
            
            # Aquí se implementaría la lógica para detener el trading
            # Por ejemplo, cerrar todas las posiciones, cancelar órdenes, etc.
            
        except Exception as e:
            logger.error(f"Error activando circuit breaker: {e}")
    
    async def deactivate_circuit_breaker(self):
        """Desactiva el circuit breaker"""
        try:
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""
            self.circuit_breaker_time = None
            
            logger.info("✅ Circuit breaker desactivado")
            
            await self.send_risk_alert(
                "CIRCUIT_BREAKER_DEACTIVATED",
                "Circuit breaker desactivado manualmente",
                "info"
            )
            
        except Exception as e:
            logger.error(f"Error desactivando circuit breaker: {e}")
    
    async def send_risk_alert(self, alert_type: str, message: str, severity: str):
        """Envía una alerta de riesgo"""
        try:
            logger.warning(f"⚠️ ALERTA DE RIESGO {severity.upper()}: {alert_type} - {message}")
            
            # Incrementar contador de alertas
            self.alerts_counter.labels(severity=severity, type=alert_type).inc()
            
            # Aquí se implementaría el envío de alertas por email/Slack/etc.
            # Por ahora solo loggeamos
            
        except Exception as e:
            logger.error(f"Error enviando alerta de riesgo: {e}")
    
    def update_prometheus_metrics(self, metrics: RiskMetrics):
        """Actualiza las métricas de Prometheus"""
        try:
            # Exposición
            self.exposure_gauge.set(metrics.total_exposure)
            self.exposure_pct_gauge.set(metrics.exposure_percentage)
            
            # Margen
            self.margin_used_gauge.set(metrics.margin_used)
            self.margin_available_gauge.set(metrics.margin_available)
            self.margin_ratio_gauge.set(metrics.margin_ratio)
            
            # Drawdown
            self.current_drawdown_gauge.set(metrics.current_drawdown)
            self.max_drawdown_gauge.set(metrics.max_drawdown)
            
            # VaR
            self.var_95_gauge.set(metrics.var_95)
            self.var_99_gauge.set(metrics.var_99)
            self.expected_shortfall_gauge.set(metrics.expected_shortfall)
            
            # Riesgo
            self.risk_score_gauge.set(metrics.risk_score)
            self.correlation_risk_gauge.set(metrics.correlation_risk)
            self.concentration_risk_gauge.set(metrics.concentration_risk)
            self.liquidity_risk_gauge.set(metrics.liquidity_risk)
            self.market_risk_gauge.set(metrics.market_risk)
            self.operational_risk_gauge.set(metrics.operational_risk)
            
            # Circuit breaker
            self.circuit_breaker_gauge.set(1 if metrics.circuit_breaker_active else 0)
            
            # Histogramas
            self.risk_score_histogram.observe(metrics.risk_score)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas de Prometheus: {e}")
    
    async def save_risk_metrics_to_file(self, metrics: RiskMetrics):
        """Guarda las métricas de riesgo en archivo"""
        try:
            metrics_file = Path("data/enterprise/risk_monitoring/risk_metrics.json")
            
            # Convertir métricas a diccionario
            metrics_dict = {
                'timestamp': metrics.timestamp.isoformat(),
                'portfolio_value': metrics.portfolio_value,
                'total_exposure': metrics.total_exposure,
                'exposure_percentage': metrics.exposure_percentage,
                'margin_used': metrics.margin_used,
                'margin_available': metrics.margin_available,
                'margin_ratio': metrics.margin_ratio,
                'current_drawdown': metrics.current_drawdown,
                'max_drawdown': metrics.max_drawdown,
                'var_95': metrics.var_95,
                'var_99': metrics.var_99,
                'expected_shortfall': metrics.expected_shortfall,
                'sharpe_ratio': metrics.sharpe_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'max_position_size': metrics.max_position_size,
                'correlation_risk': metrics.correlation_risk,
                'concentration_risk': metrics.concentration_risk,
                'liquidity_risk': metrics.liquidity_risk,
                'market_risk': metrics.market_risk,
                'operational_risk': metrics.operational_risk,
                'risk_score': metrics.risk_score,
                'risk_level': metrics.risk_level.value,
                'alerts_count': metrics.alerts_count,
                'circuit_breaker_active': metrics.circuit_breaker_active
            }
            
            # Guardar en archivo
            with open(metrics_file, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando métricas de riesgo: {e}")
    
    async def load_risk_history(self):
        """Carga el historial de métricas de riesgo"""
        try:
            metrics_file = Path("data/enterprise/risk_monitoring/risk_metrics.json")
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    # Procesar datos históricos si es necesario
                    
        except Exception as e:
            logger.error(f"Error cargando historial de métricas de riesgo: {e}")
    
    async def stop_monitoring(self):
        """Detiene el monitoreo de riesgo"""
        try:
            logger.info("⏹️ Deteniendo monitoreo de riesgo...")
            self.is_running = False
            
            # Guardar métricas finales
            if self.last_metrics:
                await self.save_risk_metrics_to_file(self.last_metrics)
            
            logger.info("✅ Monitoreo de riesgo detenido correctamente")
            
        except Exception as e:
            logger.error(f"Error deteniendo monitoreo de riesgo: {e}")
    
    def get_current_risk_metrics(self) -> Optional[RiskMetrics]:
        """Obtiene las métricas de riesgo actuales"""
        return self.last_metrics
    
    def get_risk_history(self) -> List[RiskMetrics]:
        """Obtiene el historial de métricas de riesgo"""
        return self.risk_history.copy()
    
    def is_circuit_breaker_active(self) -> bool:
        """Verifica si el circuit breaker está activo"""
        return self.circuit_breaker_active

# Instancia global
risk_monitor = RiskMonitor()
