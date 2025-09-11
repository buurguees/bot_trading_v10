#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /sync_symbols - Enterprise: Sincroniza timestamps, ejecuta paralelo, actualiza progreso.
Llama core/sync/* y core/data/database.py.
Retorna JSON para handlers.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any

# Importar ConfigLoader
from core.config.config_loader import ConfigLoader

# Cargar .env
load_dotenv()

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Logging enterprise a archivo específico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/sync_symbols.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SyncSymbolsEnterprise:
    """Gestión enterprise de sincronización de símbolos"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.synchronizer = None
        self.executor = None
        self.aggregator = None
        self.session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        """Inicializa archivo de progreso"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "En curso"):
        """Actualiza progreso en JSON temporal"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            bar_length = 10
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            data = {
                "progress": progress,
                "bar": bar,
                "current_symbol": current_symbol,
                "status": status
            }
            with open(progress_path, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Progreso actualizado: {progress}% - {current_symbol}")
    
    async def initialize(self) -> bool:
        """Inicializa componentes de core/ con retry enterprise"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.sync.symbol_synchronizer import SymbolSynchronizer
                from core.sync.parallel_executor import ParallelExecutor
                from core.sync.metrics_aggregator import MetricsAggregator
                from core.data.database import db_manager
                
                self.synchronizer = SymbolSynchronizer()
                self.executor = ParallelExecutor()
                self.aggregator = MetricsAggregator()
                
                self._update_progress(10, "Inicializando componentes", "Configurando core/")
                logger.info("✅ Componentes de core/ inicializados (retry {}/{})".format(attempt + 1, max_retries))
                return True
            except ImportError as e:
                logger.warning(f"⚠️ Import error en intento {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
            except Exception as e:
                logger.error(f"❌ Error inicializando en intento {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        
        logger.error("❌ Fallo después de {} retries".format(max_retries))
        return False
    
    async def execute(self) -> Dict[str, Any]:
        """Ejecución enterprise con progreso detallado"""
        try:
            self._update_progress(0, "Iniciando sincronización", "starting")
            logger.info("🚀 Iniciando sincronización enterprise...")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando componentes de core/"}
            
            # Config de user_settings.yaml
            sync_config = self.config.get("data_collection", {}).get("sync", {})
            symbols = sync_config.get("symbols", self.config.get("trading_settings", {}).get("symbols", []))
            timeframes = sync_config.get("timeframes", self.config.get("trading_settings", {}).get("timeframes", []))
            max_workers = sync_config.get("max_workers", 4)  # Enterprise: Límite para evitar rate limit
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No symbols/timeframes en config/user_settings.yaml"}
            
            self._update_progress(20, f"Procesando {len(symbols)} símbolos", "Cargando datos")
            logger.info(f"📊 Símbolos: {symbols} | Timeframes: {timeframes} | Workers: {max_workers}")
            
            # Sincronizar timestamps via core/sync/
            sync_results = await self.synchronizer.synchronize_symbols(symbols, timeframes)
            self._update_progress(40, "Sincronizando timestamps", "Alineando datos")
            
            if not sync_results.get("success"):
                return {"status": "error", "message": f"Error en sincronización: {sync_results.get('error', 'Desconocido')}"}
            
            # Ejecutar paralelo via core/sync/parallel_executor.py
            execution_result = await self.executor.execute_parallel(symbols, timeframes, max_workers=max_workers)
            self._update_progress(70, "Ejecutando paralelo", "Procesando trades")
            
            # Agregar métricas via core/sync/metrics_aggregator.py
            metrics_result = await self.aggregator.aggregate_metrics(execution_result["results"])
            self._update_progress(90, "Agregando métricas", "Calculando PnL/Win Rate")
            
            # Guardar en DB via core/data/database.py
            from core.data.database import db_manager
            session_saved = db_manager.log_sync_session(
                self.session_id, symbols, timeframes, execution_result, metrics_result
            )
            if not session_saved:
                logger.warning("⚠️ No se pudo guardar sesión en DB")
            
            self._update_progress(100, "Completado", "completed")
            
            # Generar reporte detallado por símbolo
            report = self._generate_report(execution_result, metrics_result, self.session_id)
            reports_by_symbol = self._split_report_by_symbol(report, symbols)  # Lista de reportes por símbolo
            
            return {
                "status": "success",
                "report": reports_by_symbol,  # Lista para delays en handlers
                "session_id": self.session_id,
                "execution_results": execution_result["results"],
                "metrics": metrics_result["metrics"]
            }
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización enterprise: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_report(self, execution_result: Dict, metrics_result: Dict, session_id: str) -> str:
        """Reporte enterprise detallado"""
        results = execution_result["results"]
        metrics = metrics_result["metrics"]
        
        total_cycles = len(results)
        successful_cycles = len([r for r in results if r.get("status") == "success"])
        total_pnl = sum(r.get("pnl", 0) for r in results)
        total_trades = sum(r.get("trades_count", 0) for r in results)
        avg_win_rate = sum(r.get("win_rate", 0) for r in results if r.get("win_rate")) / max(1, successful_cycles)
        
        initial_balance = self.config.get("capital_management", {}).get("initial_balance", 1000.0)
        final_balance = initial_balance + total_pnl
        growth_pct = (total_pnl / initial_balance) * 100
        
        report = f"""
🔄 <b>Reporte Enterprise de Sincronización</b>

📊 <b>Estadísticas Globales:</b>
• Ciclos: {total_cycles:,} | Exitosos: {successful_cycles:,} ({(successful_cycles/total_cycles*100):.1f}%)
• PnL Total: ${total_pnl:+,.2f} | Trades: {total_trades:,}
• Win Rate Promedio: {avg_win_rate:.1f}%
• Balance Final: ${final_balance:,.2f} (Crecimiento: {growth_pct:+.1f}%)

🎯 <b>Métricas Detalladas:</b>
• Mejor Estrategia: {metrics.get('best_strategy', 'N/A')} (PnL: ${metrics.get('best_pnl', 0):+.2f})
• Peor Estrategia: {metrics.get('worst_strategy', 'N/A')} (PnL: ${metrics.get('worst_pnl', 0):+.2f})
• Sharpe Ratio Promedio: {metrics.get('avg_sharpe', 0):.2f}

🆔 <b>Sesión:</b> {session_id} | <b>Estado:</b> Completado
        """
        return report.strip()
    
    def _split_report_by_symbol(self, report: str, symbols: List[str]) -> List[str]:
        """Divide reporte en bloques por símbolo para delays en Telegram"""
        # Simula división (en producción, genera por símbolo en execute)
        return [f"<b>{symbol}:</b>\n{report.splitlines()[i:i+5]}\n" for i, symbol in enumerate(symbols)]

async def main():
    """Entrada principal - Parse args para progress_id"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True, help="ID para progreso")
    args = parser.parse_args()
    
    script = SyncSymbolsEnterprise(progress_id=args.progress_id)
    result = await script.execute()
    
    # Retornar JSON a stdout para handlers.py
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())