#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /train_hist
Entrenamiento histórico con agentes en paralelo sincronizados
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

from core.sync.parallel_executor import ParallelExecutor
from core.data.database import db_manager
from config.config_loader import ConfigLoader
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainHistScript:
    """Script para entrenamiento histórico"""
    
    def __init__(self):
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.executor = None
        
    async def initialize(self):
        """Inicializar componentes"""
        try:
            # Inicializar executor
            self.executor = ParallelExecutor()
            
            logger.info("✅ Componentes de entrenamiento inicializados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    async def execute(self, args=None):
        """Ejecutar entrenamiento histórico"""
        try:
            logger.info("🚀 Iniciando entrenamiento histórico...")
            
            # Inicializar componentes
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando componentes"}
            
            # Obtener configuración
            symbols = self.config.get("trading_settings", {}).get("timeframes", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", {}).get("timeframes", [])
            
            if not symbols or not timeframes:
                logger.error("❌ Configuración de símbolos o timeframes no encontrada")
                return {"status": "error", "message": "Configuración no encontrada"}
            
            logger.info(f"📊 Símbolos: {symbols}")
            logger.info(f"📊 Timeframes: {timeframes}")
            
            # Obtener datos sincronizados
            logger.info("🔍 Obteniendo datos sincronizados...")
            sync_data = await self._get_sync_data_from_db(symbols, timeframes)
            
            if not sync_data["success"]:
                logger.error(f"❌ Error obteniendo datos sincronizados: {sync_data['message']}")
                return {"status": "error", "message": sync_data["message"]}
            
            logger.info("✅ Datos sincronizados obtenidos correctamente")
            
            # Crear timeline maestro
            master_timeline = sync_data["master_timeline"]
            logger.info(f"📅 Timeline maestro: {len(master_timeline)} períodos")
            
            # Ejecutar entrenamiento en paralelo
            logger.info("🤖 Iniciando entrenamiento en paralelo...")
            training_result = await self.executor.execute_agents_parallel(
                symbols=symbols,
                timeframes=timeframes,
                master_timeline=master_timeline,
                max_workers=4,
                delay_ms=100
            )
            
            if not training_result["success"]:
                logger.error(f"❌ Error en entrenamiento: {training_result['message']}")
                return {"status": "error", "message": training_result["message"]}
            
            logger.info("✅ Entrenamiento completado")
            
            # Agregar métricas de entrenamiento
            logger.info("📊 Agregando métricas de entrenamiento...")
            aggregated_metrics = await self._aggregate_training_metrics(training_result["results"])
            
            # Guardar resultados del entrenamiento
            session_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self._save_training_results(training_result["results"], symbols, session_id)
            
            # Generar reporte final
            report = self._generate_training_report(aggregated_metrics, training_result, session_id)
            
            return {
                "status": "success",
                "message": "Entrenamiento completado",
                "session_id": session_id,
                "results": training_result["results"],
                "metrics": aggregated_metrics,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_sync_data_from_db(self, symbols, timeframes):
        """Obtener datos sincronizados desde la base de datos"""
        try:
            # Obtener la última sesión de sincronización
            latest_session = db_manager.get_latest_sync_session()
            
            if not latest_session:
                return {
                    "success": False,
                    "message": "No se encontraron datos sincronizados. Ejecute /sync_symbols primero."
                }
            
            # Obtener metadatos de la sesión
            metadata = db_manager.get_sync_metadata(latest_session)
            
            if not metadata:
                return {
                    "success": False,
                    "message": "No se pudieron obtener metadatos de sincronización"
                }
            
            # Obtener timeline maestro
            master_timeline = metadata.get("master_timeline", [])
            
            if not master_timeline:
                return {
                    "success": False,
                    "message": "Timeline maestro no encontrado en metadatos"
                }
            
            logger.info(f"✅ Datos sincronizados obtenidos de sesión: {latest_session}")
            
            return {
                "success": True,
                "session_id": latest_session,
                "master_timeline": master_timeline,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos sincronizados: {e}")
            return {
                "success": False,
                "message": f"Error obteniendo datos sincronizados: {str(e)}"
            }
    
    async def _aggregate_training_metrics(self, results):
        """Agregar métricas de entrenamiento"""
        try:
            if not results:
                return {}
            
            total_pnl = sum(r.pnl for r in results if r.pnl is not None)
            total_trades = sum(r.trades_count for r in results if r.trades_count is not None)
            successful_cycles = len([r for r in results if r.status == "success"])
            total_cycles = len(results)
            
            win_rates = [r.win_rate for r in results if r.win_rate is not None]
            avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0
            
            execution_times = [r.execution_time for r in results if r.execution_time is not None]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            return {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "successful_cycles": successful_cycles,
                "total_cycles": total_cycles,
                "win_rate": avg_win_rate,
                "avg_execution_time": avg_execution_time,
                "success_rate": (successful_cycles / total_cycles * 100) if total_cycles > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error agregando métricas: {e}")
            return {}
    
    async def _save_training_results(self, results, symbols, session_id):
        """Guardar resultados del entrenamiento"""
        try:
            # Crear directorio de resultados si no existe
            results_dir = Path("data/training_results")
            results_dir.mkdir(exist_ok=True)
            
            # Guardar resultados por símbolo
            for symbol in symbols:
                symbol_results = [r for r in results if r.symbol == symbol]
                
                if symbol_results:
                    symbol_file = results_dir / f"{symbol}_{session_id}.json"
                    
                    # Convertir resultados a diccionario
                    symbol_data = []
                    for result in symbol_results:
                        symbol_data.append({
                            "cycle_id": result.cycle_id,
                            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                            "symbol": result.symbol,
                            "timeframe": result.timeframe,
                            "execution_time": result.execution_time,
                            "pnl": result.pnl,
                            "trades_count": result.trades_count,
                            "win_rate": result.win_rate,
                            "strategy_used": result.strategy_used,
                            "status": result.status,
                            "error_message": result.error_message
                        })
                    
                    # Guardar archivo
                    with open(symbol_file, 'w', encoding='utf-8') as f:
                        json.dump(symbol_data, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"✅ Resultados guardados para {symbol}: {symbol_file}")
            
            # Guardar resumen general
            summary_file = results_dir / f"summary_{session_id}.json"
            summary_data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "symbols": symbols,
                "total_results": len(results),
                "successful_results": len([r for r in results if r.status == "success"])
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Resumen guardado: {summary_file}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {e}")
    
    def _generate_training_report(self, aggregated_metrics, training_result, session_id):
        """Generar reporte final de entrenamiento"""
        try:
            results = training_result["results"]
            
            total_pnl = aggregated_metrics.get("total_pnl", 0)
            total_trades = aggregated_metrics.get("total_trades", 0)
            win_rate = aggregated_metrics.get("win_rate", 0)
            successful_cycles = aggregated_metrics.get("successful_cycles", 0)
            total_cycles = aggregated_metrics.get("total_cycles", 0)
            success_rate = aggregated_metrics.get("success_rate", 0)
            
            # Obtener configuración de balance
            initial_balance = self.config.get("capital_management", {}).get("initial_balance", 1000.0)
            target_balance = self.config.get("capital_management", {}).get("target_balance", 100000.0)
            daily_profit_target = self.config.get("capital_management", {}).get("daily_profit_target", 5.0)
            
            final_balance = initial_balance + total_pnl
            balance_growth_pct = ((final_balance - initial_balance) / initial_balance) * 100
            target_progress = (final_balance / target_balance) * 100
            
            report = f"""
🎉 <b>Reporte de Entrenamiento Histórico</b>

💰 <b>Gestión de Capital:</b>
• Balance inicial: ${initial_balance:,.2f}
• Balance final: ${final_balance:,.2f}
• Objetivo: ${target_balance:,.2f}
• Crecimiento: {balance_growth_pct:+.1f}%
• Progreso objetivo: {target_progress:.1f}%

📊 <b>Métricas de Trading:</b>
• PnL total: ${total_pnl:+,.2f}
• Total trades: {total_trades:,}
• Win rate: {win_rate:.1f}%
• Objetivo diario: ${daily_profit_target:.2f}

⚡ <b>Rendimiento del Sistema:</b>
• Ciclos exitosos: {successful_cycles:,}/{total_cycles:,}
• Tasa de éxito: {success_rate:.1f}%
• Tiempo promedio: {aggregated_metrics.get('avg_execution_time', 0):.2f}s

🆔 <b>Sesión:</b> {session_id}
✅ <b>Estado:</b> Entrenamiento completado exitosamente
            """
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "❌ Error generando reporte"

async def main():
    """Función principal"""
    script = TrainHistScript()
    result = await script.execute()
    
    if result["status"] == "success":
        print("✅ Entrenamiento completado exitosamente")
        print(result["report"])
    else:
        print(f"❌ Error: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())