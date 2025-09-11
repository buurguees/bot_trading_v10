# Ruta: core/compliance/enterprise/risk_reporting.py
#!/usr/bin/env python3
"""
Risk Reporting Enterprise - Reportes de Riesgo
=============================================

Este módulo implementa reportes de exposición de riesgo para cumplimiento
regulatorio y gestión de riesgo interna.

Características:
- Reportes de exposición de riesgo
- Análisis de VaR y Expected Shortfall
- Reportes de concentración de portfolio
- Análisis de correlación
- Reportes regulatorios de riesgo

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from core.compliance.enterprise.audit_logger import AuditLogger, EventType
from core.config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class RiskMetricType(Enum):
    """Tipos de métricas de riesgo"""
    VAR = "var"
    EXPECTED_SHORTFALL = "expected_shortfall"
    MAX_DRAWDOWN = "max_drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    BETA = "beta"
    CORRELATION = "correlation"
    CONCENTRATION = "concentration"
    LEVERAGE = "leverage"
    MARGIN_RATIO = "margin_ratio"

@dataclass
class RiskSnapshot:
    """Snapshot de riesgo en un momento específico"""
    timestamp: datetime
    portfolio_value: float
    total_exposure: float
    exposure_percentage: float
    margin_used: float
    margin_available: float
    margin_ratio: float
    var_95: float
    var_99: float
    expected_shortfall: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    beta: float
    correlation_risk: float
    concentration_risk: float
    leverage_risk: float
    liquidity_risk: float
    market_risk: float
    operational_risk: float
    overall_risk_score: float

@dataclass
class RiskReport:
    """Reporte de riesgo"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    risk_snapshots: List[RiskSnapshot]
    max_risk_score: float
    min_risk_score: float
    avg_risk_score: float
    risk_events: List[Dict[str, Any]]
    recommendations: List[str]
    compliance_status: str

class RiskReporting:
    """Sistema de reportes de riesgo enterprise"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = ConfigLoader().get_main_config().get('compliance', {}).get('risk_reporting', {})
        self.audit_logger = AuditLogger()
        
        # Configuración de reportes
        self.enabled = self.config.get('enabled', True)
        self.auto_generate = self.config.get('auto_generate', True)
        self.retention_days = self.config.get('retention_days', 2555)  # 7 años
        
        # Umbrales de riesgo
        self.risk_thresholds = self.config.get('risk_thresholds', {
            'high_var': 0.05,  # 5%
            'critical_var': 0.10,  # 10%
            'high_drawdown': 0.15,  # 15%
            'critical_drawdown': 0.25,  # 25%
            'high_concentration': 0.50,  # 50%
            'critical_concentration': 0.80,  # 80%
            'high_leverage': 20,  # 20x
            'critical_leverage': 30,  # 30x
            'high_margin_ratio': 0.80,  # 80%
            'critical_margin_ratio': 0.95  # 95%
        })
        
        # Directorios
        self.setup_directories()
        
        logger.info("⚠️ RiskReporting enterprise inicializado")
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/compliance/risk_reports',
            'data/enterprise/compliance/risk_reports',
            'backups/enterprise/compliance/risk_reports',
            'exports/enterprise/compliance/risk'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def generate_risk_report(
        self, 
        start_date: datetime, 
        end_date: datetime,
        symbols: Optional[List[str]] = None
    ) -> RiskReport:
        """Genera reporte de riesgo para un período"""
        try:
            logger.info(f"⚠️ Generando reporte de riesgo: {start_date} - {end_date}")
            
            # Obtener snapshots de riesgo del período
            risk_snapshots = await self.get_risk_snapshots_by_period(start_date, end_date)
            
            if not risk_snapshots:
                logger.warning("⚠️ No se encontraron snapshots de riesgo para el período")
                return self._create_empty_risk_report(start_date, end_date)
            
            # Calcular métricas agregadas
            risk_scores = [snapshot.overall_risk_score for snapshot in risk_snapshots]
            max_risk_score = max(risk_scores) if risk_scores else 0
            min_risk_score = min(risk_scores) if risk_scores else 0
            avg_risk_score = np.mean(risk_scores) if risk_scores else 0
            
            # Identificar eventos de riesgo
            risk_events = await self._identify_risk_events(risk_snapshots)
            
            # Generar recomendaciones
            recommendations = await self._generate_risk_recommendations(risk_snapshots, risk_events)
            
            # Determinar estado de cumplimiento
            compliance_status = await self._assess_compliance_status(risk_snapshots, risk_events)
            
            # Crear reporte de riesgo
            report = RiskReport(
                report_id=f"RISK_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                risk_snapshots=risk_snapshots,
                max_risk_score=max_risk_score,
                min_risk_score=min_risk_score,
                avg_risk_score=avg_risk_score,
                risk_events=risk_events,
                recommendations=recommendations,
                compliance_status=compliance_status
            )
            
            # Guardar reporte
            await self._save_risk_report(report)
            
            # Registrar generación de reporte
            await self.audit_logger.log_event(
                EventType.USER_ACTION,
                {
                    'action': 'risk_report_generated',
                    'report_id': report.report_id,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'snapshots_count': len(risk_snapshots),
                    'max_risk_score': max_risk_score,
                    'compliance_status': compliance_status
                }
            )
            
            logger.info(f"✅ Reporte de riesgo generado: {report.report_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte de riesgo: {e}")
            raise
    
    async def get_risk_snapshots_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[RiskSnapshot]:
        """Obtiene snapshots de riesgo de un período específico"""
        try:
            # Por ahora, crear snapshots simulados
            # En una implementación real, estos vendrían de la base de datos
            snapshots = []
            
            current_date = start_date
            while current_date <= end_date:
                # Crear snapshot simulado
                snapshot = RiskSnapshot(
                    timestamp=current_date,
                    portfolio_value=10000.0,
                    total_exposure=5000.0,
                    exposure_percentage=50.0,
                    margin_used=2000.0,
                    margin_available=8000.0,
                    margin_ratio=0.25,
                    var_95=100.0,
                    var_99=200.0,
                    expected_shortfall=150.0,
                    max_drawdown=5.0,
                    current_drawdown=2.0,
                    sharpe_ratio=1.5,
                    beta=1.2,
                    correlation_risk=0.3,
                    concentration_risk=0.4,
                    leverage_risk=0.2,
                    liquidity_risk=0.1,
                    market_risk=0.6,
                    operational_risk=0.1,
                    overall_risk_score=45.0
                )
                
                snapshots.append(snapshot)
                current_date += timedelta(hours=1)  # Snapshots cada hora
            
            return snapshots
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo snapshots de riesgo: {e}")
            return []
    
    def _create_empty_risk_report(self, start_date: datetime, end_date: datetime) -> RiskReport:
        """Crea un reporte de riesgo vacío"""
        return RiskReport(
            report_id=f"RISK_EMPTY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            risk_snapshots=[],
            max_risk_score=0,
            min_risk_score=0,
            avg_risk_score=0,
            risk_events=[],
            recommendations=["No hay datos de riesgo disponibles para el período"],
            compliance_status="UNKNOWN"
        )
    
    async def _identify_risk_events(self, snapshots: List[RiskSnapshot]) -> List[Dict[str, Any]]:
        """Identifica eventos de riesgo en los snapshots"""
        try:
            events = []
            
            for snapshot in snapshots:
                # Verificar VaR alto
                if snapshot.var_99 > self.risk_thresholds['critical_var']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_VAR',
                        'severity': 'CRITICAL',
                        'value': snapshot.var_99,
                        'threshold': self.risk_thresholds['critical_var'],
                        'description': f'VaR 99% excedido: {snapshot.var_99:.2f}%'
                    })
                elif snapshot.var_95 > self.risk_thresholds['high_var']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_VAR',
                        'severity': 'WARNING',
                        'value': snapshot.var_95,
                        'threshold': self.risk_thresholds['high_var'],
                        'description': f'VaR 95% excedido: {snapshot.var_95:.2f}%'
                    })
                
                # Verificar drawdown alto
                if snapshot.current_drawdown > self.risk_thresholds['critical_drawdown']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_DRAWDOWN',
                        'severity': 'CRITICAL',
                        'value': snapshot.current_drawdown,
                        'threshold': self.risk_thresholds['critical_drawdown'],
                        'description': f'Drawdown crítico: {snapshot.current_drawdown:.2f}%'
                    })
                elif snapshot.current_drawdown > self.risk_thresholds['high_drawdown']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_DRAWDOWN',
                        'severity': 'WARNING',
                        'value': snapshot.current_drawdown,
                        'threshold': self.risk_thresholds['high_drawdown'],
                        'description': f'Drawdown alto: {snapshot.current_drawdown:.2f}%'
                    })
                
                # Verificar concentración alta
                if snapshot.concentration_risk > self.risk_thresholds['critical_concentration']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_CONCENTRATION',
                        'severity': 'CRITICAL',
                        'value': snapshot.concentration_risk,
                        'threshold': self.risk_thresholds['critical_concentration'],
                        'description': f'Concentración crítica: {snapshot.concentration_risk:.2f}%'
                    })
                elif snapshot.concentration_risk > self.risk_thresholds['high_concentration']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_CONCENTRATION',
                        'severity': 'WARNING',
                        'value': snapshot.concentration_risk,
                        'threshold': self.risk_thresholds['high_concentration'],
                        'description': f'Concentración alta: {snapshot.concentration_risk:.2f}%'
                    })
                
                # Verificar ratio de margen alto
                if snapshot.margin_ratio > self.risk_thresholds['critical_margin_ratio']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_MARGIN_RATIO',
                        'severity': 'CRITICAL',
                        'value': snapshot.margin_ratio,
                        'threshold': self.risk_thresholds['critical_margin_ratio'],
                        'description': f'Ratio de margen crítico: {snapshot.margin_ratio:.2f}%'
                    })
                elif snapshot.margin_ratio > self.risk_thresholds['high_margin_ratio']:
                    events.append({
                        'timestamp': snapshot.timestamp,
                        'type': 'HIGH_MARGIN_RATIO',
                        'severity': 'WARNING',
                        'value': snapshot.margin_ratio,
                        'threshold': self.risk_thresholds['high_margin_ratio'],
                        'description': f'Ratio de margen alto: {snapshot.margin_ratio:.2f}%'
                    })
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error identificando eventos de riesgo: {e}")
            return []
    
    async def _generate_risk_recommendations(
        self, 
        snapshots: List[RiskSnapshot], 
        events: List[Dict[str, Any]]
    ) -> List[str]:
        """Genera recomendaciones de gestión de riesgo"""
        try:
            recommendations = []
            
            # Analizar eventos de riesgo
            critical_events = [e for e in events if e['severity'] == 'CRITICAL']
            warning_events = [e for e in events if e['severity'] == 'WARNING']
            
            if critical_events:
                recommendations.append("Implementar circuit breakers inmediatamente")
                recommendations.append("Revisar límites de riesgo críticos")
            
            if warning_events:
                recommendations.append("Monitorear métricas de riesgo más frecuentemente")
                recommendations.append("Considerar reducir exposición en áreas de alto riesgo")
            
            # Analizar métricas agregadas
            if snapshots:
                avg_var_99 = np.mean([s.var_99 for s in snapshots])
                if avg_var_99 > self.risk_thresholds['high_var']:
                    recommendations.append("Considerar reducir VaR objetivo")
                
                avg_drawdown = np.mean([s.current_drawdown for s in snapshots])
                if avg_drawdown > self.risk_thresholds['high_drawdown']:
                    recommendations.append("Implementar stop-loss más estrictos")
                
                avg_concentration = np.mean([s.concentration_risk for s in snapshots])
                if avg_concentration > self.risk_thresholds['high_concentration']:
                    recommendations.append("Diversificar portfolio para reducir concentración")
                
                avg_margin_ratio = np.mean([s.margin_ratio for s in snapshots])
                if avg_margin_ratio > self.risk_thresholds['high_margin_ratio']:
                    recommendations.append("Aumentar capital disponible o reducir exposición")
            
            # Recomendaciones generales
            recommendations.append("Implementar monitoreo de riesgo en tiempo real")
            recommendations.append("Establecer límites de riesgo por símbolo")
            recommendations.append("Crear planes de contingencia para escenarios de riesgo")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones de riesgo: {e}")
            return []
    
    async def _assess_compliance_status(
        self, 
        snapshots: List[RiskSnapshot], 
        events: List[Dict[str, Any]]
    ) -> str:
        """Evalúa el estado de cumplimiento de riesgo"""
        try:
            if not snapshots:
                return "UNKNOWN"
            
            # Contar eventos por severidad
            critical_events = len([e for e in events if e['severity'] == 'CRITICAL'])
            warning_events = len([e for e in events if e['severity'] == 'WARNING'])
            
            # Calcular score de cumplimiento
            total_snapshots = len(snapshots)
            critical_ratio = critical_events / total_snapshots
            warning_ratio = warning_events / total_snapshots
            
            # Determinar estado
            if critical_ratio > 0.1:  # Más del 10% con eventos críticos
                return "NON_COMPLIANT"
            elif critical_ratio > 0.05 or warning_ratio > 0.2:  # 5% críticos o 20% warnings
                return "AT_RISK"
            elif warning_ratio > 0.1:  # Más del 10% con warnings
                return "WARNING"
            else:
                return "COMPLIANT"
            
        except Exception as e:
            logger.error(f"❌ Error evaluando estado de cumplimiento: {e}")
            return "UNKNOWN"
    
    async def _save_risk_report(self, report: RiskReport):
        """Guarda el reporte de riesgo"""
        try:
            report_file = Path(f"data/enterprise/compliance/risk_reports/risk_{report.report_id}.json")
            
            # Convertir snapshots a diccionarios
            snapshots_data = []
            for snapshot in report.risk_snapshots:
                snapshots_data.append({
                    'timestamp': snapshot.timestamp.isoformat(),
                    'portfolio_value': snapshot.portfolio_value,
                    'total_exposure': snapshot.total_exposure,
                    'exposure_percentage': snapshot.exposure_percentage,
                    'margin_used': snapshot.margin_used,
                    'margin_available': snapshot.margin_available,
                    'margin_ratio': snapshot.margin_ratio,
                    'var_95': snapshot.var_95,
                    'var_99': snapshot.var_99,
                    'expected_shortfall': snapshot.expected_shortfall,
                    'max_drawdown': snapshot.max_drawdown,
                    'current_drawdown': snapshot.current_drawdown,
                    'sharpe_ratio': snapshot.sharpe_ratio,
                    'beta': snapshot.beta,
                    'correlation_risk': snapshot.correlation_risk,
                    'concentration_risk': snapshot.concentration_risk,
                    'leverage_risk': snapshot.leverage_risk,
                    'liquidity_risk': snapshot.liquidity_risk,
                    'market_risk': snapshot.market_risk,
                    'operational_risk': snapshot.operational_risk,
                    'overall_risk_score': snapshot.overall_risk_score
                })
            
            report_data = {
                'report_id': report.report_id,
                'generated_at': report.generated_at.isoformat(),
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'risk_snapshots': snapshots_data,
                'max_risk_score': report.max_risk_score,
                'min_risk_score': report.min_risk_score,
                'avg_risk_score': report.avg_risk_score,
                'risk_events': report.risk_events,
                'recommendations': report.recommendations,
                'compliance_status': report.compliance_status
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Error guardando reporte de riesgo: {e}")
    
    async def generate_risk_summary(self, days: int = 30) -> Dict[str, Any]:
        """Genera resumen de riesgo de los últimos N días"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Obtener snapshots de riesgo
            snapshots = await self.get_risk_snapshots_by_period(start_date, end_date)
            
            if not snapshots:
                return {"error": "No hay datos de riesgo disponibles"}
            
            # Calcular métricas agregadas
            risk_scores = [s.overall_risk_score for s in snapshots]
            var_95_values = [s.var_95 for s in snapshots]
            var_99_values = [s.var_99 for s in snapshots]
            drawdowns = [s.current_drawdown for s in snapshots]
            margin_ratios = [s.margin_ratio for s in snapshots]
            
            summary = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'risk_metrics': {
                    'avg_risk_score': float(np.mean(risk_scores)),
                    'max_risk_score': float(np.max(risk_scores)),
                    'min_risk_score': float(np.min(risk_scores)),
                    'avg_var_95': float(np.mean(var_95_values)),
                    'max_var_95': float(np.max(var_95_values)),
                    'avg_var_99': float(np.mean(var_99_values)),
                    'max_var_99': float(np.max(var_99_values)),
                    'avg_drawdown': float(np.mean(drawdowns)),
                    'max_drawdown': float(np.max(drawdowns)),
                    'avg_margin_ratio': float(np.mean(margin_ratios)),
                    'max_margin_ratio': float(np.max(margin_ratios))
                },
                'compliance': {
                    'status': await self._assess_compliance_status(snapshots, []),
                    'thresholds_exceeded': await self._count_threshold_violations(snapshots)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generando resumen de riesgo: {e}")
            return {"error": str(e)}
    
    async def _count_threshold_violations(self, snapshots: List[RiskSnapshot]) -> Dict[str, int]:
        """Cuenta violaciones de umbrales de riesgo"""
        try:
            violations = {
                'high_var': 0,
                'critical_var': 0,
                'high_drawdown': 0,
                'critical_drawdown': 0,
                'high_concentration': 0,
                'critical_concentration': 0,
                'high_margin_ratio': 0,
                'critical_margin_ratio': 0
            }
            
            for snapshot in snapshots:
                if snapshot.var_99 > self.risk_thresholds['critical_var']:
                    violations['critical_var'] += 1
                elif snapshot.var_95 > self.risk_thresholds['high_var']:
                    violations['high_var'] += 1
                
                if snapshot.current_drawdown > self.risk_thresholds['critical_drawdown']:
                    violations['critical_drawdown'] += 1
                elif snapshot.current_drawdown > self.risk_thresholds['high_drawdown']:
                    violations['high_drawdown'] += 1
                
                if snapshot.concentration_risk > self.risk_thresholds['critical_concentration']:
                    violations['critical_concentration'] += 1
                elif snapshot.concentration_risk > self.risk_thresholds['high_concentration']:
                    violations['high_concentration'] += 1
                
                if snapshot.margin_ratio > self.risk_thresholds['critical_margin_ratio']:
                    violations['critical_margin_ratio'] += 1
                elif snapshot.margin_ratio > self.risk_thresholds['high_margin_ratio']:
                    violations['high_margin_ratio'] += 1
            
            return violations
            
        except Exception as e:
            logger.error(f"❌ Error contando violaciones de umbrales: {e}")
            return {}
    
    async def close(self):
        """Cierra el sistema de reportes de riesgo"""
        try:
            await self.audit_logger.close()
            logger.info("✅ RiskReporting cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando RiskReporting: {e}")

# Instancia global
risk_reporting = RiskReporting()
