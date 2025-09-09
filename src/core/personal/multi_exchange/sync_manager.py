"""
Exchange Sync Manager - Bot Trading v10 Personal
================================================

Gestión de sincronización entre exchanges con:
- Sincronización de balances
- Sincronización de posiciones
- Gestión de diferencias de precios
- Alertas de desincronización
- Recuperación automática
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from prometheus_client import Counter, Gauge, Histogram
import numpy as np

logger = logging.getLogger(__name__)

# Métricas Prometheus
sync_operations = Counter('trading_bot_sync_operations_total', 'Operaciones de sincronización', ['operation', 'exchange'])
sync_errors = Counter('trading_bot_sync_errors_total', 'Errores de sincronización', ['operation', 'exchange'])
sync_drift = Gauge('trading_bot_sync_drift_usdt', 'Deriva de sincronización en USDT', ['exchange', 'symbol'])
sync_latency = Histogram('trading_bot_sync_latency_seconds', 'Latencia de sincronización', ['operation'])

@dataclass
class SyncStatus:
    """Estado de sincronización de un exchange"""
    exchange_id: str
    last_sync: datetime
    balance_drift: float
    position_drift: float
    price_drift: float
    is_synced: bool
    error_count: int
    last_error: Optional[str]

class ExchangeSyncManager:
    """Gestor de sincronización entre exchanges"""
    
    def __init__(self, exchange_manager, config: Dict[str, Any]):
        self.exchange_manager = exchange_manager
        self.config = config
        self.sync_status = {}
        self.is_running = False
        self.sync_interval = config.get('sync_interval', 30)  # segundos
        self.max_drift_threshold = config.get('max_drift_threshold', 10.0)  # USDT
        
        # Historial de sincronización
        self.sync_history = {}
        
        logger.info("ExchangeSyncManager inicializado")
    
    async def start(self):
        """Inicia el gestor de sincronización"""
        try:
            logger.info("Iniciando ExchangeSyncManager...")
            self.is_running = True
            
            # Inicializar estado de sincronización
            await self._initialize_sync_status()
            
            # Iniciar sincronización continua
            asyncio.create_task(self._continuous_sync())
            
            logger.info("ExchangeSyncManager iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando ExchangeSyncManager: {e}")
            raise
    
    async def stop(self):
        """Detiene el gestor de sincronización"""
        try:
            logger.info("Deteniendo ExchangeSyncManager...")
            self.is_running = False
            logger.info("ExchangeSyncManager detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo ExchangeSyncManager: {e}")
    
    async def _initialize_sync_status(self):
        """Inicializa el estado de sincronización para todos los exchanges"""
        for exchange_id in self.exchange_manager.get_available_exchanges():
            self.sync_status[exchange_id] = SyncStatus(
                exchange_id=exchange_id,
                last_sync=datetime.now(),
                balance_drift=0.0,
                position_drift=0.0,
                price_drift=0.0,
                is_synced=True,
                error_count=0,
                last_error=None
            )
    
    async def _continuous_sync(self):
        """Sincronización continua de todos los exchanges"""
        while self.is_running:
            try:
                await self._sync_all_exchanges()
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error en sincronización continua: {e}")
                await asyncio.sleep(10)
    
    async def _sync_all_exchanges(self):
        """Sincroniza todos los exchanges"""
        tasks = []
        for exchange_id in self.exchange_manager.get_available_exchanges():
            tasks.append(self._sync_exchange(exchange_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for exchange_id, result in zip(self.exchange_manager.get_available_exchanges(), results):
            if isinstance(result, Exception):
                logger.error(f"Error sincronizando {exchange_id}: {result}")
                self._update_sync_error(exchange_id, str(result))
            else:
                self._update_sync_success(exchange_id, result)
    
    async def _sync_exchange(self, exchange_id: str) -> Dict[str, Any]:
        """Sincroniza un exchange específico"""
        start_time = time.time()
        
        try:
            # Obtener datos del exchange
            balance = await self.exchange_manager.get_balance(exchange_id)
            positions = await self._get_positions(exchange_id)
            
            # Calcular deriva
            drift_info = await self._calculate_drift(exchange_id, balance, positions)
            
            # Actualizar estado
            self.sync_status[exchange_id].last_sync = datetime.now()
            self.sync_status[exchange_id].balance_drift = drift_info['balance_drift']
            self.sync_status[exchange_id].position_drift = drift_info['position_drift']
            self.sync_status[exchange_id].price_drift = drift_info['price_drift']
            self.sync_status[exchange_id].is_synced = drift_info['is_synced']
            
            # Actualizar métricas
            sync_operations.labels(operation='sync', exchange=exchange_id).inc()
            
            # Calcular latencia
            latency = time.time() - start_time
            sync_latency.labels(operation='sync').observe(latency)
            
            # Log de sincronización
            if drift_info['is_synced']:
                logger.debug(f"✅ {exchange_id} sincronizado correctamente")
            else:
                logger.warning(f"⚠️ {exchange_id} con deriva: {drift_info['balance_drift']:.2f} USDT")
            
            return drift_info
            
        except Exception as e:
            logger.error(f"Error sincronizando {exchange_id}: {e}")
            sync_errors.labels(operation='sync', exchange=exchange_id).inc()
            raise
    
    async def _get_positions(self, exchange_id: str) -> List[Dict[str, Any]]:
        """Obtiene las posiciones de un exchange"""
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            positions = await exchange.fetch_positions()
            
            # Filtrar solo posiciones abiertas
            open_positions = [pos for pos in positions if float(pos.get('contracts', 0)) != 0]
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones de {exchange_id}: {e}")
            return []
    
    async def _calculate_drift(self, exchange_id: str, balance: Dict[str, Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula la deriva de sincronización"""
        try:
            # Calcular deriva de balance
            balance_drift = 0.0
            if 'USDT' in balance and 'free' in balance['USDT']:
                current_balance = float(balance['USDT']['free'])
                expected_balance = self._get_expected_balance(exchange_id)
                balance_drift = abs(current_balance - expected_balance)
            
            # Calcular deriva de posiciones
            position_drift = 0.0
            for position in positions:
                if position.get('unrealizedPnl'):
                    position_drift += abs(float(position['unrealizedPnl']))
            
            # Calcular deriva de precios (comparar con otros exchanges)
            price_drift = await self._calculate_price_drift(exchange_id)
            
            # Determinar si está sincronizado
            is_synced = (balance_drift < self.max_drift_threshold and 
                        position_drift < self.max_drift_threshold and
                        price_drift < 0.01)  # 1% de deriva de precio
            
            return {
                'balance_drift': balance_drift,
                'position_drift': position_drift,
                'price_drift': price_drift,
                'is_synced': is_synced,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error calculando deriva para {exchange_id}: {e}")
            return {
                'balance_drift': float('inf'),
                'position_drift': float('inf'),
                'price_drift': float('inf'),
                'is_synced': False,
                'timestamp': datetime.now()
            }
    
    def _get_expected_balance(self, exchange_id: str) -> float:
        """Obtiene el balance esperado de un exchange"""
        # En una implementación real, esto vendría de un sistema de contabilidad
        # Por ahora, retornamos 0 para simplificar
        return 0.0
    
    async def _calculate_price_drift(self, exchange_id: str) -> float:
        """Calcula la deriva de precios comparando con otros exchanges"""
        try:
            # Obtener precios de todos los exchanges
            all_balances = await self.exchange_manager.get_balance()
            
            if len(all_balances) < 2:
                return 0.0
            
            # Calcular precio promedio de USDT
            usdt_prices = []
            for ex_id, balance in all_balances.items():
                if 'USDT' in balance and 'free' in balance['USDT']:
                    usdt_prices.append(float(balance['USDT']['free']))
            
            if len(usdt_prices) < 2:
                return 0.0
            
            # Calcular desviación estándar como medida de deriva
            price_std = np.std(usdt_prices)
            price_mean = np.mean(usdt_prices)
            
            if price_mean == 0:
                return 0.0
            
            return price_std / price_mean
            
        except Exception as e:
            logger.error(f"Error calculando deriva de precios: {e}")
            return 0.0
    
    def _update_sync_success(self, exchange_id: str, drift_info: Dict[str, Any]):
        """Actualiza el estado de sincronización exitosa"""
        self.sync_status[exchange_id].error_count = 0
        self.sync_status[exchange_id].last_error = None
        
        # Actualizar métricas de deriva
        sync_drift.labels(exchange=exchange_id, symbol='USDT').set(drift_info['balance_drift'])
    
    def _update_sync_error(self, exchange_id: str, error: str):
        """Actualiza el estado de error de sincronización"""
        self.sync_status[exchange_id].error_count += 1
        self.sync_status[exchange_id].last_error = error
        self.sync_status[exchange_id].is_synced = False
        
        sync_errors.labels(operation='sync', exchange=exchange_id).inc()
    
    async def force_sync(self, exchange_id: str = None) -> Dict[str, Any]:
        """Fuerza la sincronización de un exchange específico o todos"""
        try:
            if exchange_id:
                result = await self._sync_exchange(exchange_id)
                return {exchange_id: result}
            else:
                return await self._sync_all_exchanges()
                
        except Exception as e:
            logger.error(f"Error en sincronización forzada: {e}")
            return {'error': str(e)}
    
    def get_sync_status(self, exchange_id: str = None) -> Dict[str, Any]:
        """Obtiene el estado de sincronización"""
        if exchange_id:
            if exchange_id not in self.sync_status:
                return {}
            
            status = self.sync_status[exchange_id]
            return {
                'exchange_id': status.exchange_id,
                'last_sync': status.last_sync.isoformat(),
                'balance_drift': status.balance_drift,
                'position_drift': status.position_drift,
                'price_drift': status.price_drift,
                'is_synced': status.is_synced,
                'error_count': status.error_count,
                'last_error': status.last_error
            }
        else:
            return {
                ex_id: {
                    'exchange_id': status.exchange_id,
                    'last_sync': status.last_sync.isoformat(),
                    'balance_drift': status.balance_drift,
                    'position_drift': status.position_drift,
                    'price_drift': status.price_drift,
                    'is_synced': status.is_synced,
                    'error_count': status.error_count,
                    'last_error': status.last_error
                }
                for ex_id, status in self.sync_status.items()
            }
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de sincronización"""
        total_exchanges = len(self.sync_status)
        synced_exchanges = len([status for status in self.sync_status.values() if status.is_synced])
        
        total_errors = sum(status.error_count for status in self.sync_status.values())
        
        avg_balance_drift = np.mean([status.balance_drift for status in self.sync_status.values()])
        avg_position_drift = np.mean([status.position_drift for status in self.sync_status.values()])
        avg_price_drift = np.mean([status.price_drift for status in self.sync_status.values()])
        
        return {
            'total_exchanges': total_exchanges,
            'synced_exchanges': synced_exchanges,
            'sync_rate': synced_exchanges / total_exchanges if total_exchanges > 0 else 0,
            'total_errors': total_errors,
            'avg_balance_drift': avg_balance_drift,
            'avg_position_drift': avg_position_drift,
            'avg_price_drift': avg_price_drift,
            'is_running': self.is_running
        }
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detecta anomalías en la sincronización"""
        anomalies = []
        
        for exchange_id, status in self.sync_status.items():
            # Detectar deriva excesiva
            if status.balance_drift > self.max_drift_threshold * 2:
                anomalies.append({
                    'type': 'excessive_balance_drift',
                    'exchange': exchange_id,
                    'value': status.balance_drift,
                    'threshold': self.max_drift_threshold * 2,
                    'severity': 'high'
                })
            
            # Detectar muchos errores
            if status.error_count > 5:
                anomalies.append({
                    'type': 'excessive_errors',
                    'exchange': exchange_id,
                    'value': status.error_count,
                    'threshold': 5,
                    'severity': 'medium'
                })
            
            # Detectar desincronización prolongada
            if not status.is_synced and (datetime.now() - status.last_sync).seconds > 300:  # 5 minutos
                anomalies.append({
                    'type': 'prolonged_desync',
                    'exchange': exchange_id,
                    'value': (datetime.now() - status.last_sync).seconds,
                    'threshold': 300,
                    'severity': 'high'
                })
        
        return anomalies
