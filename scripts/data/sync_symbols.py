#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /sync_symbols
Sincroniza timestamps de todos los símbolos para ejecución paralela
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.sync.symbol_synchronizer import SymbolSynchronizer
from core.sync.parallel_executor import ParallelExecutor
from core.sync.metrics_aggregator import MetricsAggregator
from core.data.database import db_manager
from config.config_loader import ConfigLoader

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncSymbolsScript:
    """Script para sincronización de símbolos"""
    
    def __init__(self):
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.synchronizer = None
        self.executor = None
        self.aggregator = None
        
    async def initialize(self):
        """Inicializar componentes"""
        try:
            # Inicializar componentes
            self.synchronizer = SymbolSynchronizer()
            self.executor = ParallelExecutor()
            self.aggregator = MetricsAggregator()
            
            logger.info("✅ Componentes de sincronización inicializados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    async def execute(self, args=None):
        """Ejecutar sincronización de símbolos"""
        try:
            logger.info("🚀 Iniciando sincronización de símbolos...")
            
            # Inicializar componentes
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando componentes"}
            
            # Obtener configuración
            sync_config = self.config.get("data_collection", {}).get("sync", {})
            symbols = sync_config.get("symbols", [])
            timeframes = sync_config.get("timeframes", [])
            max_workers = sync_config.get("max_workers", 4)
            delay_ms = sync_config.get("delay_ms", 100)
            
            if not symbols or not timeframes:
                logger.error("❌ Configuración de símbolos o timeframes no encontrada")
                return {"status": "error", "message": "Configuración no encontrada"}
            
            logger.info(f"📊 Símbolos: {symbols}")
            logger.info(f"📊 Timeframes: {timeframes}")
            logger.info(f"⚙️ Workers: {max_workers}, Delay: {delay_ms}ms")
            
            # Validar datos disponibles
            logger.info("🔍 Validando datos disponibles...")
            validation_result = self.synchronizer._validate_data_availability(symbols, timeframes)
            
            if not validation_result["valid"]:
                missing_data = validation_result.get("missing_data", [])
                logger.error(f"❌ Datos insuficientes: {missing_data}")
                return {
                    "status": "error", 
                    "message": f"Datos insuficientes: {missing_data}",
                    "missing_data": missing_data
                }
            
            logger.info("✅ Datos validados correctamente")
            
            # Sincronizar todos los símbolos
            logger.info("🔄 Iniciando sincronización...")
            sync_result = await self.synchronizer.sync_all_symbols(symbols, timeframes)
            
            if not sync_result["success"]:
                logger.error(f"❌ Error en sincronización: {sync_result['message']}")
                return {"status": "error", "message": sync_result["message"]}
            
            logger.info("✅ Sincronización completada")
            
            # Crear timeline maestro
            logger.info("📅 Creando timeline maestro...")
            master_timeline = self.synchronizer._create_master_timeline(symbols, timeframes)
            
            if not master_timeline:
                logger.error("❌ Error creando timeline maestro")
                return {"status": "error", "message": "Error creando timeline maestro"}
            
            logger.info(f"✅ Timeline maestro creado: {len(master_timeline)} períodos")
            
            # Ejecutar agentes en paralelo
            logger.info("🤖 Ejecutando agentes en paralelo...")
            execution_result = await self.executor.execute_agents_parallel(
                symbols=symbols,
                timeframes=timeframes,
                master_timeline=master_timeline,
                max_workers=max_workers,
                delay_ms=delay_ms
            )
            
            if not execution_result["success"]:
                logger.error(f"❌ Error en ejecución paralela: {execution_result['message']}")
                return {"status": "error", "message": execution_result["message"]}
            
            logger.info("✅ Ejecución paralela completada")
            
            # Agregar métricas
            logger.info("📊 Agregando métricas...")
            metrics_result = await self.aggregator.aggregate_cycle_metrics(
                execution_result["results"],
                symbols,
                timeframes
            )
            
            if not metrics_result["success"]:
                logger.error(f"❌ Error agregando métricas: {metrics_result['message']}")
                return {"status": "error", "message": metrics_result["message"]}
            
            logger.info("✅ Métricas agregadas correctamente")
            
            # Guardar metadatos de sincronización
            session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            metadata = {
                "session_id": session_id,
                "symbols": symbols,
                "timeframes": timeframes,
                "master_timeline_length": len(master_timeline),
                "execution_results": execution_result["results"],
                "metrics": metrics_result["metrics"],
                "timestamp": datetime.now().isoformat()
            }
            
            db_manager.store_alignment_metadata(session_id, metadata)
            logger.info(f"✅ Metadatos guardados: {session_id}")
            
            # Generar reporte final
            report = self._generate_report(execution_result, metrics_result, session_id)
            
            return {
                "status": "success",
                "message": "Sincronización completada",
                "session_id": session_id,
                "execution_results": execution_result["results"],
                "metrics": metrics_result["metrics"],
                "report": report
            }
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")
            return {"status": "error", "message": str(e)}
    
    def _generate_report(self, execution_result, metrics_result, session_id):
        """Generar reporte final de sincronización"""
        try:
            results = execution_result["results"]
            metrics = metrics_result["metrics"]
            
            total_cycles = len(results)
            successful_cycles = len([r for r in results if r.status == "success"])
            total_pnl = sum(r.pnl for r in results if r.pnl is not None)
            total_trades = sum(r.trades_count for r in results if r.trades_count is not None)
            avg_win_rate = sum(r.win_rate for r in results if r.win_rate is not None) / max(1, successful_cycles)
            
            report = f"""
🔄 <b>Reporte de Sincronización de Símbolos</b>

📊 <b>Estadísticas de Ejecución:</b>
• Ciclos totales: {total_cycles:,}
• Ciclos exitosos: {successful_cycles:,}
• Tasa de éxito: {(successful_cycles/total_cycles*100):.1f}%
• PnL total: ${total_pnl:+,.2f}
• Total trades: {total_trades:,}
• Win rate promedio: {avg_win_rate:.1f}%

🎯 <b>Métricas Agregadas:</b>
• Estrategias identificadas: {len(metrics.get('strategy_rankings', []))}
• Mejor estrategia: {metrics.get('best_strategy', 'N/A')}
• Peor estrategia: {metrics.get('worst_strategy', 'N/A')}

🆔 <b>Sesión:</b> {session_id}
✅ <b>Estado:</b> Sincronización completada exitosamente
            """
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "❌ Error generando reporte"

async def main():
    """Función principal"""
    script = SyncSymbolsScript()
    result = await script.execute()
    
    if result["status"] == "success":
        print("✅ Sincronización completada exitosamente")
        print(result["report"])
    else:
        print(f"❌ Error: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())