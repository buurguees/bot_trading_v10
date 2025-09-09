"""
Módulo Enterprise Compliance - Bot Trading v10
=============================================

Este módulo contiene todos los componentes de cumplimiento regulatorio
para trading de futuros con auditoría inmutable y reportes regulatorios.

Componentes principales:
- AuditLogger: Logging de auditoría inmutable con checksums
- TradeReporting: Reportes de trades para reguladores
- RiskReporting: Reportes de exposición de riesgo
- RegulatoryCompliance: Cumplimiento MiFID II/GDPR

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

from .audit_logger import AuditLogger
from .trade_reporting import TradeReporting
from .risk_reporting import RiskReporting
from .regulatory_compliance import RegulatoryCompliance

__all__ = [
    'AuditLogger',
    'TradeReporting', 
    'RiskReporting',
    'RegulatoryCompliance'
]

__version__ = '1.0.0'
__author__ = 'Bot Trading v10 Enterprise'
