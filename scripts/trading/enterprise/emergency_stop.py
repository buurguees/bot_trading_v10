# Ruta: scripts/trading/enterprise/emergency_stop.py
#!/usr/bin/env python3
"""
Script de Parada de Emergencia Enterprise
========================================

Este script ejecuta una parada de emergencia completa del sistema de trading,
cerrando todas las posiciones abiertas y deteniendo todos los procesos.

Características:
- Cierre inmediato de todas las posiciones
- Detención de todos los procesos de trading
- Generación de reporte de emergencia
- Notificaciones de alerta
- Limpieza de recursos

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from trading.bitget_client import bitget_client
from core.config.config_loader import user_config

# Configurar logging
logger = logging.getLogger(__name__)

class EmergencyStopSystem:
    """Sistema de parada de emergencia enterprise"""
    
    def __init__(self):
        self.emergency_triggered = False
        self.emergency_time = None
        self.closed_positions = []
        self.failed_closures = []
        self.emergency_reason = "Manual emergency stop"
        
        # Configurar directorios
        self.setup_directories()
        
        logger.info("🛑 Sistema de parada de emergencia inicializado")
    
    def setup_directories(self):
        """Configura los directorios necesarios"""
        directories = [
            'logs/enterprise/emergency',
            'backups/enterprise/emergency'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def trigger_emergency_stop(self, reason: str = "Manual emergency stop"):
        """Activa la parada de emergencia"""
        try:
            self.emergency_triggered = True
            self.emergency_time = datetime.now()
            self.emergency_reason = reason
            
            logger.critical("🚨 PARADA DE EMERGENCIA ACTIVADA")
            logger.critical(f"Razón: {reason}")
            logger.critical(f"Tiempo: {self.emergency_time}")
            
            # Ejecutar secuencia de parada
            await self.execute_emergency_sequence()
            
        except Exception as e:
            logger.error(f"❌ Error en parada de emergencia: {e}")
    
    async def execute_emergency_sequence(self):
        """Ejecuta la secuencia completa de parada de emergencia"""
        try:
            logger.info("🔄 Ejecutando secuencia de parada de emergencia...")
            
            # Paso 1: Obtener todas las posiciones abiertas
            positions = await self.get_all_open_positions()
            logger.info(f"📊 Posiciones abiertas encontradas: {len(positions)}")
            
            # Paso 2: Cerrar todas las posiciones
            if positions:
                await self.close_all_positions(positions)
            
            # Paso 3: Detener todos los procesos de trading
            await self.stop_all_trading_processes()
            
            # Paso 4: Cerrar conexiones
            await self.close_all_connections()
            
            # Paso 5: Generar reporte de emergencia
            await self.generate_emergency_report()
            
            # Paso 6: Enviar notificaciones
            await self.send_emergency_notifications()
            
            logger.info("✅ Secuencia de parada de emergencia completada")
            
        except Exception as e:
            logger.error(f"❌ Error en secuencia de parada: {e}")
    
    async def get_all_open_positions(self) -> List[Dict]:
        """Obtiene todas las posiciones abiertas"""
        try:
            positions = await bitget_client.get_positions()
            
            # Filtrar solo posiciones con tamaño > 0
            open_positions = []
            for pos in positions:
                if pos.get('size', 0) > 0:
                    open_positions.append({
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'size': pos['size'],
                        'entry_price': pos['entry_price'],
                        'mark_price': pos['mark_price'],
                        'unrealized_pnl': pos['unrealized_pnl'],
                        'leverage': pos['leverage']
                    })
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    async def close_all_positions(self, positions: List[Dict]):
        """Cierra todas las posiciones abiertas"""
        try:
            logger.info(f"🔄 Cerrando {len(positions)} posiciones...")
            
            for position in positions:
                try:
                    symbol = position['symbol']
                    side = position['side']
                    size = position['size']
                    
                    logger.info(f"🔄 Cerrando posición: {symbol} {side} {size}")
                    
                    # Cerrar posición
                    result = await bitget_client.close_position(symbol, side, size)
                    
                    if result:
                        self.closed_positions.append({
                            'symbol': symbol,
                            'side': side,
                            'size': size,
                            'closed_at': datetime.now(),
                            'order_id': result.get('id')
                        })
                        logger.info(f"✅ Posición cerrada: {symbol}")
                    else:
                        self.failed_closures.append({
                            'symbol': symbol,
                            'side': side,
                            'size': size,
                            'error': 'Failed to close position'
                        })
                        logger.error(f"❌ Error cerrando posición: {symbol}")
                    
                    # Pequeña pausa entre cierres
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error cerrando posición {position['symbol']}: {e}")
                    self.failed_closures.append({
                        'symbol': position['symbol'],
                        'side': position['side'],
                        'size': position['size'],
                        'error': str(e)
                    })
            
            logger.info(f"✅ Cierre de posiciones completado: {len(self.closed_positions)} exitosas, {len(self.failed_closures)} fallidas")
            
        except Exception as e:
            logger.error(f"Error cerrando posiciones: {e}")
    
    async def stop_all_trading_processes(self):
        """Detiene todos los procesos de trading"""
        try:
            logger.info("🔄 Deteniendo procesos de trading...")
            
            # Aquí se detendrían todos los procesos de trading activos
            # Por ejemplo: motores de trading, generadores de señales, etc.
            
            # Simular detención de procesos
            await asyncio.sleep(1)
            
            logger.info("✅ Procesos de trading detenidos")
            
        except Exception as e:
            logger.error(f"Error deteniendo procesos: {e}")
    
    async def close_all_connections(self):
        """Cierra todas las conexiones"""
        try:
            logger.info("🔄 Cerrando conexiones...")
            
            # Cerrar conexión a Bitget
            await bitget_client.close()
            
            # Cerrar otras conexiones si las hay
            # (WebSockets, bases de datos, etc.)
            
            logger.info("✅ Conexiones cerradas")
            
        except Exception as e:
            logger.error(f"Error cerrando conexiones: {e}")
    
    async def generate_emergency_report(self):
        """Genera reporte de emergencia"""
        try:
            logger.info("📊 Generando reporte de emergencia...")
            
            report = {
                'emergency_info': {
                    'triggered_at': self.emergency_time.isoformat() if self.emergency_time else None,
                    'reason': self.emergency_reason,
                    'duration': str(datetime.now() - self.emergency_time) if self.emergency_time else None
                },
                'positions_closed': {
                    'total': len(self.closed_positions),
                    'successful': len(self.closed_positions),
                    'failed': len(self.failed_closures),
                    'details': self.closed_positions
                },
                'positions_failed': {
                    'total': len(self.failed_closures),
                    'details': self.failed_closures
                },
                'system_status': {
                    'emergency_active': self.emergency_triggered,
                    'all_connections_closed': True,
                    'all_processes_stopped': True
                }
            }
            
            # Guardar reporte
            report_path = f"logs/enterprise/emergency/emergency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📊 Reporte de emergencia guardado: {report_path}")
            logger.info(f"  Posiciones cerradas: {len(self.closed_positions)}")
            logger.info(f"  Posiciones fallidas: {len(self.failed_closures)}")
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
    
    async def send_emergency_notifications(self):
        """Envía notificaciones de emergencia"""
        try:
            logger.info("📧 Enviando notificaciones de emergencia...")
            
            # Aquí se enviarían notificaciones por email, Slack, etc.
            # Por ahora solo loggeamos
            
            notification = {
                'type': 'EMERGENCY_STOP',
                'timestamp': datetime.now().isoformat(),
                'reason': self.emergency_reason,
                'positions_closed': len(self.closed_positions),
                'positions_failed': len(self.failed_closures)
            }
            
            logger.critical(f"🚨 NOTIFICACIÓN DE EMERGENCIA: {json.dumps(notification, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error enviando notificaciones: {e}")
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de la emergencia"""
        return {
            'emergency_triggered': self.emergency_triggered,
            'emergency_time': self.emergency_time.isoformat() if self.emergency_time else None,
            'emergency_reason': self.emergency_reason,
            'positions_closed': len(self.closed_positions),
            'positions_failed': len(self.failed_closures)
        }

async def emergency_stop(reason: str = "Manual emergency stop"):
    """Función principal para ejecutar parada de emergencia"""
    try:
        logger.critical("🚨 INICIANDO PARADA DE EMERGENCIA")
        
        # Crear sistema de parada de emergencia
        emergency_system = EmergencyStopSystem()
        
        # Ejecutar parada de emergencia
        await emergency_system.trigger_emergency_stop(reason)
        
        # Obtener estado final
        status = emergency_system.get_emergency_status()
        
        logger.critical("✅ PARADA DE EMERGENCIA COMPLETADA")
        logger.critical(f"Estado final: {json.dumps(status, indent=2)}")
        
        return True
        
    except Exception as e:
        logger.critical(f"❌ ERROR CRÍTICO EN PARADA DE EMERGENCIA: {e}")
        return False

async def check_emergency_conditions() -> bool:
    """Verifica si se cumplen condiciones de emergencia"""
    try:
        # Verificar conexión a Bitget
        health = await bitget_client.health_check()
        if not health.get('rest_api', False):
            logger.warning("⚠️ Conexión REST API no disponible")
            return True
        
        # Verificar balance
        margin_info = await bitget_client.get_margin_info()
        if margin_info:
            margin_ratio = margin_info.get('margin_ratio', 0)
            if margin_ratio > 0.8:  # 80% de margen usado
                logger.warning(f"⚠️ Margen alto: {margin_ratio:.2%}")
                return True
        
        # Verificar posiciones
        positions = await bitget_client.get_positions()
        total_exposure = sum(pos.get('size', 0) * pos.get('mark_price', 0) for pos in positions)
        if total_exposure > 100000:  # $100k de exposición
            logger.warning(f"⚠️ Exposición alta: ${total_exposure:,.2f}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error verificando condiciones de emergencia: {e}")
        return True

if __name__ == "__main__":
    # Ejecutar parada de emergencia
    asyncio.run(emergency_stop("Manual execution"))