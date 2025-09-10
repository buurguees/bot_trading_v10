#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /train_hist - Enterprise: Entrenamiento histórico paralelo.
Llama core/sync/parallel_executor.py y core/ml/*.
Progreso por ciclo/símbolo.
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
from config.config_loader import ConfigLoader

# Cargar .env
load_dotenv()

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/train_hist.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TrainHistEnterprise:
    """Entrenamiento histórico enterprise"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.executor = None
        self.session_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "Entrenando"):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            bar_length = 10
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
            with open(progress_path, 'w') as f:
                json.dump(data, f)
    
    async def initialize(self) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.sync.parallel_executor import ParallelExecutor
                from core.data.database import db_manager
                
                self.executor = ParallelExecutor()
                self.db_manager = db_manager
                
                self._update_progress(10, "Inicializando executor", "Configurando core/")
                logger.info("✅ Executor inicializado")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Retry {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        return False
    
    async def execute(self) -> Dict[str, Any]:
        try:
            self._update_progress(0, "Iniciando entrenamiento", "starting")
            logger.info("🚀 Entrenamiento histórico enterprise iniciado")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando core/sync/"}
            
            symbols = self.config.get("trading_settings", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            max_workers = self.config.get("data_collection", {}).get("training", {}).get("max_workers", 4)
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No config"}
            
            self._update_progress(20, f"Entrenando {len(symbols)} símbolos", "Cargando datos históricos")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes} | Workers: {max_workers}")
            
            total_cycles = len(symbols)
            step = 0
            execution_results = {}
            reports_by_symbol = []
            
            # Entrenar paralelo via core/sync/parallel_executor.py
            for symbol in symbols:
                self._update_progress(30 + (step / total_cycles * 50), symbol, "Entrenando símbolo")
                try:
                    # Ejecutar para símbolo (llama core/ml/ si aplica)
                    result = await self.executor.execute_training_cycle(symbol, timeframes, self.session_id)
                    execution_results[symbol] = result
                    sym_report = self._generate_symbol_report(symbol, result)
                    reports_by_symbol.append(sym_report)
                    step += 1
                except Exception as e:
                    logger.error(f"❌ {symbol}: {e}")
                    execution_results[symbol] = {"status": "error", "pnl": 0, "trades_count": 0}
                    step += 1
            
            # Agregar métricas (simulado, usa core/sync/metrics_aggregator.py si existe)
            aggregated_metrics = self._aggregate_metrics(execution_results)
            self._update_progress(80, "Agregando métricas", "Calculando globales")
            
            # Log en DB
            self.db_manager.log_training_session(self.session_id, symbols, timeframes, execution_results, aggregated_metrics)
            self._update_progress(100, "Completado", "completed")
            
            return {
                "status": "success",
                "report": reports_by_symbol,
                "session_id": self.session_id,
                "aggregated_metrics": aggregated_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Error entrenamiento: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _aggregate_metrics(self, results: Dict) -> Dict:
        """Agrega métricas enterprise"""
        total_pnl = sum(r.get("pnl", 0) for r in results.values())
        total_trades = sum(r.get("trades_count", 0) for r in results.values())
        successful = sum(1 for r in results.values() if r.get("status") == "success")
        win_rate = sum(r.get("win_rate", 0) for r in results.values()) / max(1, len(results))
        return {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "successful_cycles": successful,
            "total_cycles": len(results),
            "win_rate": win_rate * 100,
            "success_rate": (successful / len(results)) * 100
        }
    
    def _generate_symbol_report(self, symbol: str, result: Dict) -> str:
        pnl = result.get("pnl", 0)
        trades = result.get("trades_count", 0)
        win_rate = result.get("win_rate", 0)
        status = "✅ Exitoso" if result.get("status") == "success" else "❌ Error"
        report = f"""
<b>🎓 {symbol}:</b>
• PnL: ${pnl:+,.2f}
• Trades: {trades:,}
• Win Rate: {win_rate:.1f}%
• Estado: {status}
        """
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = TrainHistEnterprise(progress_id=args.progress_id)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())