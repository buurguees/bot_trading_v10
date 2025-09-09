"""
Multi-Exchange Sync Script - Bot Trading v10 Personal
=====================================================

Script para sincronización de exchanges con:
- Sincronización de balances
- Sincronización de posiciones
- Detección de anomalías
- Recuperación automática
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.personal.multi_exchange import MultiExchangeManager, ExchangeSyncManager
from src.core.config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/multi_exchange_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MultiExchangeSync:
    """Script de sincronización multi-exchange"""
    
    def __init__(self, config_path: str = "config/personal/exchanges.yaml"):
        self.config_path = config_path
        self.config_manager = EnterpriseConfigManager(config_path)
        self.exchange_manager = None
        self.sync_manager = None
        
        logger.info("MultiExchangeSync inicializado")
    
    async def initialize(self):
        """Inicializa los componentes necesarios"""
        try:
            logger.info("Inicializando MultiExchangeSync...")
            
            # Cargar configuración
            config = self.config_manager.load_config()
            
            # Inicializar gestor de exchanges
            self.exchange_manager = MultiExchangeManager(self.config_path)
            await self.exchange_manager.start()
            
            # Inicializar gestor de sincronización
            sync_config = config.get('sync', {})
            self.sync_manager = ExchangeSyncManager(self.exchange_manager, sync_config)
            await self.sync_manager.start()
            
            logger.info("MultiExchangeSync inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando MultiExchangeSync: {e}")
            raise
    
    async def sync_all_exchanges(self):
        """Sincroniza todos los exchanges"""
        try:
            logger.info("Iniciando sincronización de todos los exchanges...")
            
            # Forzar sincronización
            result = await self.sync_manager.force_sync()
            
            # Mostrar resultados
            for exchange_id, sync_result in result.items():
                if isinstance(sync_result, dict) and 'error' not in sync_result:
                    logger.info(f"✅ {exchange_id}: Sincronizado correctamente")
                else:
                    logger.error(f"❌ {exchange_id}: Error en sincronización")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sincronizando exchanges: {e}")
            raise
    
    async def sync_specific_exchange(self, exchange_id: str):
        """Sincroniza un exchange específico"""
        try:
            logger.info(f"Sincronizando exchange específico: {exchange_id}")
            
            result = await self.sync_manager.force_sync(exchange_id)
            
            if exchange_id in result and 'error' not in result[exchange_id]:
                logger.info(f"✅ {exchange_id}: Sincronizado correctamente")
            else:
                logger.error(f"❌ {exchange_id}: Error en sincronización")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sincronizando {exchange_id}: {e}")
            raise
    
    async def check_sync_status(self):
        """Verifica el estado de sincronización"""
        try:
            logger.info("Verificando estado de sincronización...")
            
            sync_status = self.sync_manager.get_sync_status()
            
            print("\n" + "="*60)
            print("ESTADO DE SINCRONIZACIÓN")
            print("="*60)
            
            for exchange_id, status in sync_status.items():
                print(f"\n📊 {exchange_id.upper()}:")
                print(f"   Última sincronización: {status['last_sync']}")
                print(f"   Estado: {'✅ SINCRONIZADO' if status['is_synced'] else '❌ DESINCRONIZADO'}")
                print(f"   Deriva de balance: {status['balance_drift']:.2f} USDT")
                print(f"   Deriva de posición: {status['position_drift']:.2f} USDT")
                print(f"   Deriva de precio: {status['price_drift']:.4f}")
                print(f"   Errores: {status['error_count']}")
                if status['last_error']:
                    print(f"   Último error: {status['last_error']}")
            
            return sync_status
            
        except Exception as e:
            logger.error(f"Error verificando estado de sincronización: {e}")
            raise
    
    async def detect_anomalies(self):
        """Detecta anomalías en la sincronización"""
        try:
            logger.info("Detectando anomalías...")
            
            anomalies = await self.sync_manager.detect_anomalies()
            
            if anomalies:
                print("\n" + "="*60)
                print("ANOMALÍAS DETECTADAS")
                print("="*60)
                
                for anomaly in anomalies:
                    severity_icon = "🔴" if anomaly['severity'] == 'high' else "🟡"
                    print(f"\n{severity_icon} {anomaly['type'].upper()}")
                    print(f"   Exchange: {anomaly['exchange']}")
                    print(f"   Valor: {anomaly['value']}")
                    print(f"   Umbral: {anomaly['threshold']}")
                    print(f"   Severidad: {anomaly['severity']}")
            else:
                print("\n✅ No se detectaron anomalías")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías: {e}")
            raise
    
    async def get_sync_statistics(self):
        """Obtiene estadísticas de sincronización"""
        try:
            logger.info("Obteniendo estadísticas de sincronización...")
            
            stats = self.sync_manager.get_sync_statistics()
            
            print("\n" + "="*60)
            print("ESTADÍSTICAS DE SINCRONIZACIÓN")
            print("="*60)
            print(f"Total de exchanges: {stats['total_exchanges']}")
            print(f"Exchanges sincronizados: {stats['synced_exchanges']}")
            print(f"Tasa de sincronización: {stats['sync_rate']:.2%}")
            print(f"Total de errores: {stats['total_errors']}")
            print(f"Deriva promedio de balance: {stats['avg_balance_drift']:.2f} USDT")
            print(f"Deriva promedio de posición: {stats['avg_position_drift']:.2f} USDT")
            print(f"Deriva promedio de precio: {stats['avg_price_drift']:.4f}")
            print(f"Sistema ejecutándose: {'✅' if stats['is_running'] else '❌'}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            raise
    
    async def shutdown(self):
        """Cierra el sistema de forma segura"""
        try:
            logger.info("Cerrando MultiExchangeSync...")
            
            if self.sync_manager:
                await self.sync_manager.stop()
            
            if self.exchange_manager:
                await self.exchange_manager.stop()
            
            logger.info("MultiExchangeSync cerrado correctamente")
            
        except Exception as e:
            logger.error(f"Error cerrando MultiExchangeSync: {e}")

async def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Multi-Exchange Sync Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python multi_exchange_sync.py --sync-all
  python multi_exchange_sync.py --sync-exchange bitget
  python multi_exchange_sync.py --check-status
  python multi_exchange_sync.py --detect-anomalies
  python multi_exchange_sync.py --statistics
        """
    )
    
    parser.add_argument(
        '--sync-all',
        action='store_true',
        help='Sincronizar todos los exchanges'
    )
    
    parser.add_argument(
        '--sync-exchange',
        type=str,
        help='Sincronizar un exchange específico'
    )
    
    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Verificar estado de sincronización'
    )
    
    parser.add_argument(
        '--detect-anomalies',
        action='store_true',
        help='Detectar anomalías'
    )
    
    parser.add_argument(
        '--statistics',
        action='store_true',
        help='Mostrar estadísticas'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/personal/exchanges.yaml',
        help='Ruta al archivo de configuración'
    )
    
    args = parser.parse_args()
    
    # Crear instancia del script
    sync_script = MultiExchangeSync(args.config)
    
    try:
        # Inicializar sistema
        await sync_script.initialize()
        
        # Ejecutar comando solicitado
        if args.sync_all:
            await sync_script.sync_all_exchanges()
        
        elif args.sync_exchange:
            await sync_script.sync_specific_exchange(args.sync_exchange)
        
        elif args.check_status:
            await sync_script.check_sync_status()
        
        elif args.detect_anomalies:
            await sync_script.detect_anomalies()
        
        elif args.statistics:
            await sync_script.get_sync_statistics()
        
        else:
            logger.info("ℹ️ Usa --help para ver las opciones disponibles")
            await sync_script.check_sync_status()
    
    except KeyboardInterrupt:
        logger.info("Script detenido por el usuario")
    
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    
    finally:
        await sync_script.shutdown()

if __name__ == "__main__":
    # Ejecutar script
    asyncio.run(main())
