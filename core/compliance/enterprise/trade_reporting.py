# Ruta: core/compliance/enterprise/trade_reporting.py
#!/usr/bin/env python3
"""
Trade Reporting Enterprise - Reportes Regulatorios
=================================================

Este módulo implementa reportes de trades para cumplimiento regulatorio
con formatos estándar para MiFID II y otros reguladores.

Características:
- Reportes de trades en formato estándar
- Exportación a CSV/Excel para reguladores
- Cumplimiento MiFID II
- Reportes de transacciones
- Análisis de cumplimiento

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from core.compliance.enterprise.audit_logger import AuditLogger, EventType
from core.config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class ReportFormat(Enum):
    """Formatos de reporte"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    XML = "xml"

class ReportType(Enum):
    """Tipos de reporte"""
    TRADE_REPORT = "trade_report"
    TRANSACTION_REPORT = "transaction_report"
    POSITION_REPORT = "position_report"
    COMPLIANCE_REPORT = "compliance_report"
    RISK_REPORT = "risk_report"

@dataclass
class TradeRecord:
    """Registro de trade para reportes"""
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str
    size: float
    price: float
    value: float
    leverage: float
    fees: float
    pnl: float
    strategy: str
    user_id: str
    session_id: str
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None

@dataclass
class ComplianceReport:
    """Reporte de cumplimiento"""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_trades: int
    total_volume: float
    total_fees: float
    total_pnl: float
    compliance_score: float
    violations: List[Dict[str, Any]]
    recommendations: List[str]

class TradeReporting:
    """Sistema de reportes de trades enterprise"""
    
    def __init__(self, config_path: str = "config/user_settings.yaml"):
        self.config = ConfigLoader().get_main_config().get('compliance', {}).get('trade_reporting', {})
        self.audit_logger = AuditLogger()
        
        # Configuración de reportes
        self.enabled = self.config.get('enabled', True)
        self.auto_generate = self.config.get('auto_generate', True)
        self.retention_days = self.config.get('retention_days', 2555)  # 7 años
        
        # Formatos soportados
        self.supported_formats = [ReportFormat.CSV, ReportFormat.EXCEL, ReportFormat.JSON]
        
        # Directorios
        self.setup_directories()
        
        logger.info("📊 TradeReporting enterprise inicializado")
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/compliance/reports',
            'data/enterprise/compliance/reports',
            'backups/enterprise/compliance/reports',
            'exports/enterprise/compliance'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def generate_trade_report(
        self, 
        start_date: datetime, 
        end_date: datetime,
        symbols: Optional[List[str]] = None,
        format: ReportFormat = ReportFormat.CSV
    ) -> str:
        """Genera reporte de trades para un período"""
        try:
            logger.info(f"📊 Generando reporte de trades: {start_date} - {end_date}")
            
            # Obtener trades del período
            trades = await self.get_trades_by_period(start_date, end_date, symbols)
            
            if not trades:
                logger.warning("⚠️ No se encontraron trades para el período especificado")
                return ""
            
            # Generar reporte según formato
            report_path = await self._generate_report_file(trades, start_date, end_date, format)
            
            # Registrar generación de reporte
            await self.audit_logger.log_event(
                EventType.USER_ACTION,
                {
                    'action': 'trade_report_generated',
                    'report_path': str(report_path),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'trades_count': len(trades),
                    'format': format.value
                }
            )
            
            logger.info(f"✅ Reporte de trades generado: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte de trades: {e}")
            return ""
    
    async def get_trades_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime,
        symbols: Optional[List[str]] = None
    ) -> List[TradeRecord]:
        """Obtiene trades de un período específico"""
        try:
            # Obtener eventos de auditoría de trades
            trade_events = await self.audit_logger.get_events_by_type(
                EventType.TRADE_OPENED, start_date, end_date
            )
            
            close_events = await self.audit_logger.get_events_by_type(
                EventType.TRADE_CLOSED, start_date, end_date
            )
            
            # Crear diccionario de eventos de cierre por trade_id
            close_events_dict = {}
            for event in close_events:
                trade_id = event.data.get('trade_id', event.id)
                close_events_dict[trade_id] = event
            
            trades = []
            for event in trade_events:
                # Filtrar por símbolos si se especifica
                if symbols and event.data.get('symbol') not in symbols:
                    continue
                
                # Buscar evento de cierre correspondiente
                close_event = close_events_dict.get(event.id)
                
                # Crear registro de trade
                trade = TradeRecord(
                    trade_id=event.id,
                    timestamp=event.timestamp,
                    symbol=event.data.get('symbol', ''),
                    side=event.data.get('side', ''),
                    size=event.data.get('size', 0),
                    price=event.data.get('price', 0),
                    value=event.data.get('size', 0) * event.data.get('price', 0),
                    leverage=event.data.get('leverage', 1),
                    fees=event.data.get('fees', 0),
                    pnl=close_event.data.get('pnl', 0) if close_event else 0,
                    strategy=event.data.get('strategy', 'unknown'),
                    user_id=event.user_id,
                    session_id=event.session_id,
                    entry_time=event.timestamp,
                    exit_time=close_event.timestamp if close_event else None,
                    duration_minutes=close_event.data.get('duration_minutes') if close_event else None,
                    entry_price=event.data.get('price', 0),
                    exit_price=close_event.data.get('exit_price', 0) if close_event else None
                )
                
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo trades por período: {e}")
            return []
    
    async def _generate_report_file(
        self, 
        trades: List[TradeRecord], 
        start_date: datetime, 
        end_date: datetime,
        format: ReportFormat
    ) -> Path:
        """Genera archivo de reporte en el formato especificado"""
        try:
            # Crear nombre de archivo
            date_str = start_date.strftime('%Y%m%d')
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"trade_report_{date_str}_{timestamp_str}.{format.value}"
            report_path = Path(f"exports/enterprise/compliance/{filename}")
            
            if format == ReportFormat.CSV:
                await self._generate_csv_report(trades, report_path)
            elif format == ReportFormat.EXCEL:
                await self._generate_excel_report(trades, report_path)
            elif format == ReportFormat.JSON:
                await self._generate_json_report(trades, report_path)
            else:
                raise ValueError(f"Formato no soportado: {format}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"❌ Error generando archivo de reporte: {e}")
            raise
    
    async def _generate_csv_report(self, trades: List[TradeRecord], file_path: Path):
        """Genera reporte en formato CSV"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'trade_id', 'timestamp', 'symbol', 'side', 'size', 'price', 'value',
                    'leverage', 'fees', 'pnl', 'strategy', 'user_id', 'session_id',
                    'entry_time', 'exit_time', 'duration_minutes', 'entry_price', 'exit_price'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for trade in trades:
                    writer.writerow({
                        'trade_id': trade.trade_id,
                        'timestamp': trade.timestamp.isoformat(),
                        'symbol': trade.symbol,
                        'side': trade.side,
                        'size': trade.size,
                        'price': trade.price,
                        'value': trade.value,
                        'leverage': trade.leverage,
                        'fees': trade.fees,
                        'pnl': trade.pnl,
                        'strategy': trade.strategy,
                        'user_id': trade.user_id,
                        'session_id': trade.session_id,
                        'entry_time': trade.entry_time.isoformat() if trade.entry_time else '',
                        'exit_time': trade.exit_time.isoformat() if trade.exit_time else '',
                        'duration_minutes': trade.duration_minutes or '',
                        'entry_price': trade.entry_price or '',
                        'exit_price': trade.exit_price or ''
                    })
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte CSV: {e}")
            raise
    
    async def _generate_excel_report(self, trades: List[TradeRecord], file_path: Path):
        """Genera reporte en formato Excel"""
        try:
            # Convertir trades a DataFrame
            data = []
            for trade in trades:
                data.append({
                    'Trade ID': trade.trade_id,
                    'Timestamp': trade.timestamp,
                    'Symbol': trade.symbol,
                    'Side': trade.side,
                    'Size': trade.size,
                    'Price': trade.price,
                    'Value': trade.value,
                    'Leverage': trade.leverage,
                    'Fees': trade.fees,
                    'PnL': trade.pnl,
                    'Strategy': trade.strategy,
                    'User ID': trade.user_id,
                    'Session ID': trade.session_id,
                    'Entry Time': trade.entry_time,
                    'Exit Time': trade.exit_time,
                    'Duration (min)': trade.duration_minutes,
                    'Entry Price': trade.entry_price,
                    'Exit Price': trade.exit_price
                })
            
            df = pd.DataFrame(data)
            
            # Crear archivo Excel con múltiples hojas
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Hoja principal con todos los trades
                df.to_excel(writer, sheet_name='Trades', index=False)
                
                # Hoja de resumen
                summary_data = self._create_summary_data(trades)
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Hoja de estadísticas por símbolo
                symbol_stats = self._create_symbol_statistics(trades)
                symbol_df = pd.DataFrame(symbol_stats)
                symbol_df.to_excel(writer, sheet_name='Symbol Statistics', index=False)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte Excel: {e}")
            raise
    
    async def _generate_json_report(self, trades: List[TradeRecord], file_path: Path):
        """Genera reporte en formato JSON"""
        try:
            # Convertir trades a diccionarios
            trades_data = []
            for trade in trades:
                trade_dict = {
                    'trade_id': trade.trade_id,
                    'timestamp': trade.timestamp.isoformat(),
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'size': trade.size,
                    'price': trade.price,
                    'value': trade.value,
                    'leverage': trade.leverage,
                    'fees': trade.fees,
                    'pnl': trade.pnl,
                    'strategy': trade.strategy,
                    'user_id': trade.user_id,
                    'session_id': trade.session_id,
                    'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                    'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                    'duration_minutes': trade.duration_minutes,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price
                }
                trades_data.append(trade_dict)
            
            # Crear estructura completa del reporte
            report_data = {
                'report_info': {
                    'generated_at': datetime.now().isoformat(),
                    'total_trades': len(trades),
                    'format': 'json'
                },
                'trades': trades_data,
                'summary': self._create_summary_data(trades),
                'symbol_statistics': self._create_symbol_statistics(trades)
            }
            
            # Escribir archivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte JSON: {e}")
            raise
    
    def _create_summary_data(self, trades: List[TradeRecord]) -> List[Dict[str, Any]]:
        """Crea datos de resumen del reporte"""
        try:
            if not trades:
                return []
            
            total_trades = len(trades)
            total_volume = sum(trade.value for trade in trades)
            total_fees = sum(trade.fees for trade in trades)
            total_pnl = sum(trade.pnl for trade in trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            return [
                {'Metric': 'Total Trades', 'Value': total_trades},
                {'Metric': 'Total Volume', 'Value': f"${total_volume:,.2f}"},
                {'Metric': 'Total Fees', 'Value': f"${total_fees:,.2f}"},
                {'Metric': 'Total PnL', 'Value': f"${total_pnl:,.2f}"},
                {'Metric': 'Winning Trades', 'Value': winning_trades},
                {'Metric': 'Losing Trades', 'Value': losing_trades},
                {'Metric': 'Win Rate', 'Value': f"{win_rate:.2f}%"},
                {'Metric': 'Avg Trade Size', 'Value': f"${avg_trade_size:,.2f}"},
                {'Metric': 'Avg PnL', 'Value': f"${avg_pnl:,.2f}"}
            ]
            
        except Exception as e:
            logger.error(f"❌ Error creando datos de resumen: {e}")
            return []
    
    def _create_symbol_statistics(self, trades: List[TradeRecord]) -> List[Dict[str, Any]]:
        """Crea estadísticas por símbolo"""
        try:
            if not trades:
                return []
            
            # Agrupar por símbolo
            symbol_groups = {}
            for trade in trades:
                symbol = trade.symbol
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(trade)
            
            # Calcular estadísticas por símbolo
            stats = []
            for symbol, symbol_trades in symbol_groups.items():
                total_trades = len(symbol_trades)
                total_volume = sum(trade.value for trade in symbol_trades)
                total_pnl = sum(trade.pnl for trade in symbol_trades)
                winning_trades = len([t for t in symbol_trades if t.pnl > 0])
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
                
                stats.append({
                    'Symbol': symbol,
                    'Total Trades': total_trades,
                    'Total Volume': f"${total_volume:,.2f}",
                    'Total PnL': f"${total_pnl:,.2f}",
                    'Winning Trades': winning_trades,
                    'Win Rate': f"{win_rate:.2f}%",
                    'Avg Trade Size': f"${avg_trade_size:,.2f}"
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error creando estadísticas por símbolo: {e}")
            return []
    
    async def generate_compliance_report(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> ComplianceReport:
        """Genera reporte de cumplimiento"""
        try:
            logger.info(f"📋 Generando reporte de cumplimiento: {start_date} - {end_date}")
            
            # Obtener trades del período
            trades = await self.get_trades_by_period(start_date, end_date)
            
            # Calcular métricas de cumplimiento
            total_trades = len(trades)
            total_volume = sum(trade.value for trade in trades)
            total_fees = sum(trade.fees for trade in trades)
            total_pnl = sum(trade.pnl for trade in trades)
            
            # Verificar violaciones de cumplimiento
            violations = await self._check_compliance_violations(trades)
            
            # Calcular score de cumplimiento
            compliance_score = await self._calculate_compliance_score(trades, violations)
            
            # Generar recomendaciones
            recommendations = await self._generate_recommendations(trades, violations)
            
            # Crear reporte de cumplimiento
            report = ComplianceReport(
                report_id=f"COMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                report_type=ReportType.COMPLIANCE_REPORT,
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                total_trades=total_trades,
                total_volume=total_volume,
                total_fees=total_fees,
                total_pnl=total_pnl,
                compliance_score=compliance_score,
                violations=violations,
                recommendations=recommendations
            )
            
            # Guardar reporte
            await self._save_compliance_report(report)
            
            logger.info(f"✅ Reporte de cumplimiento generado: {report.report_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte de cumplimiento: {e}")
            raise
    
    async def _check_compliance_violations(self, trades: List[TradeRecord]) -> List[Dict[str, Any]]:
        """Verifica violaciones de cumplimiento"""
        try:
            violations = []
            
            # Verificar trades con leverage excesivo
            high_leverage_trades = [t for t in trades if t.leverage > 20]
            if high_leverage_trades:
                violations.append({
                    'type': 'HIGH_LEVERAGE',
                    'count': len(high_leverage_trades),
                    'description': f'Trades con leverage > 20x: {len(high_leverage_trades)}',
                    'severity': 'WARNING'
                })
            
            # Verificar trades con pérdidas excesivas
            large_loss_trades = [t for t in trades if t.pnl < -1000]
            if large_loss_trades:
                violations.append({
                    'type': 'LARGE_LOSSES',
                    'count': len(large_loss_trades),
                    'description': f'Trades con pérdidas > $1000: {len(large_loss_trades)}',
                    'severity': 'ERROR'
                })
            
            # Verificar concentración de trades en un símbolo
            symbol_counts = {}
            for trade in trades:
                symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
            
            total_trades = len(trades)
            for symbol, count in symbol_counts.items():
                concentration = (count / total_trades) * 100
                if concentration > 50:  # Más del 50% en un símbolo
                    violations.append({
                        'type': 'HIGH_CONCENTRATION',
                        'count': count,
                        'description': f'Alta concentración en {symbol}: {concentration:.1f}%',
                        'severity': 'WARNING'
                    })
            
            return violations
            
        except Exception as e:
            logger.error(f"❌ Error verificando violaciones de cumplimiento: {e}")
            return []
    
    async def _calculate_compliance_score(
        self, 
        trades: List[TradeRecord], 
        violations: List[Dict[str, Any]]
    ) -> float:
        """Calcula el score de cumplimiento (0-100)"""
        try:
            if not trades:
                return 100.0
            
            # Score base
            score = 100.0
            
            # Penalizar por violaciones
            for violation in violations:
                if violation['severity'] == 'WARNING':
                    score -= 5
                elif violation['severity'] == 'ERROR':
                    score -= 15
                elif violation['severity'] == 'CRITICAL':
                    score -= 30
            
            # Penalizar por trades con pérdidas excesivas
            large_losses = len([t for t in trades if t.pnl < -1000])
            if large_losses > 0:
                score -= min(large_losses * 2, 20)
            
            # Penalizar por alta concentración
            symbol_counts = {}
            for trade in trades:
                symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
            
            max_concentration = max(symbol_counts.values()) / len(trades) * 100
            if max_concentration > 80:
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"❌ Error calculando score de cumplimiento: {e}")
            return 0.0
    
    async def _generate_recommendations(
        self, 
        trades: List[TradeRecord], 
        violations: List[Dict[str, Any]]
    ) -> List[str]:
        """Genera recomendaciones de cumplimiento"""
        try:
            recommendations = []
            
            # Recomendaciones basadas en violaciones
            for violation in violations:
                if violation['type'] == 'HIGH_LEVERAGE':
                    recommendations.append("Considerar reducir el leverage máximo permitido")
                elif violation['type'] == 'LARGE_LOSSES':
                    recommendations.append("Implementar stop-loss más estrictos")
                elif violation['type'] == 'HIGH_CONCENTRATION':
                    recommendations.append("Diversificar más el portfolio")
            
            # Recomendaciones generales
            if len(trades) > 100:
                recommendations.append("Considerar implementar límites de trading diario")
            
            win_rate = len([t for t in trades if t.pnl > 0]) / len(trades) * 100
            if win_rate < 40:
                recommendations.append("Revisar estrategias de trading - win rate bajo")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones: {e}")
            return []
    
    async def _save_compliance_report(self, report: ComplianceReport):
        """Guarda el reporte de cumplimiento"""
        try:
            report_file = Path(f"data/enterprise/compliance/reports/compliance_{report.report_id}.json")
            
            report_data = {
                'report_id': report.report_id,
                'report_type': report.report_type.value,
                'generated_at': report.generated_at.isoformat(),
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'total_trades': report.total_trades,
                'total_volume': report.total_volume,
                'total_fees': report.total_fees,
                'total_pnl': report.total_pnl,
                'compliance_score': report.compliance_score,
                'violations': report.violations,
                'recommendations': report.recommendations
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Error guardando reporte de cumplimiento: {e}")
    
    async def close(self):
        """Cierra el sistema de reportes"""
        try:
            await self.audit_logger.close()
            logger.info("✅ TradeReporting cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando TradeReporting: {e}")

# Instancia global
trade_reporting = TradeReporting()
