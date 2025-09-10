#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /repair_data - Enterprise: Repara duplicados, gaps y alinea.
Llama core/data/history_analyzer.py y core/data/database.py.
Progreso por símbolo/TF.
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
    handlers=[logging.FileHandler('logs/repair_data.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class RepairDataEnterprise:
    """Reparación enterprise de datos"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.analyzer = None
        self.db = None
        self.session_id = f"repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "Reparando"):
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
                from core.data.history_analyzer import HistoryAnalyzer
                from core.data.database import db_manager
                
                self.analyzer = HistoryAnalyzer()
                self.db = db_manager
                
                self._update_progress(10, "Inicializando analyzer y DB", "Configurando core/")
                logger.info("✅ Core/ inicializado")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Retry {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        return False
    
    async def execute(self) -> Dict[str, Any]:
        try:
            self._update_progress(0, "Iniciando reparación", "starting")
            logger.info("🚀 Reparación enterprise iniciada")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando core/data/"}
            
            symbols = self.config.get("trading_settings", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No config"}
            
            self._update_progress(20, f"Analizando {len(symbols)} símbolos", "Detectando issues")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes}")
            
            total_steps = len(symbols) * len(timeframes)
            step = 0
            repair_results = {}
            reports_by_symbol = []
            
            # Detectar issues via core/data/history_analyzer.py
            issues = await self.analyzer.detect_data_issues(symbols)
            self._update_progress(40, "Detectando gaps/duplicados", "Análisis")
            
            for symbol in symbols:
                self._update_progress(50 + (step / total_steps * 30), symbol, "Reparando símbolo")
                sym_repairs = {}
                
                for tf in timeframes:
                    try:
                        # Reparar via analyzer
                        repair = await self.analyzer.repair_data_issues(
                            symbols=[symbol], repair_duplicates=True, fill_gaps=True, timeframe=tf
                        )
                        count_fixed = repair.get("successful_repairs", 0)
                        sym_repairs[tf] = {"fixed": count_fixed, "status": "success" if count_fixed > 0 else "no_issues"}
                        
                        # Guardar via DB
                        self.db.log_repair_session(self.session_id, symbol, tf, repair)
                        step += 1
                    except Exception as e:
                        logger.error(f"❌ {symbol} {tf}: {e}")
                        sym_repairs[tf] = {"fixed": 0, "status": "error"}
                        step += 1
                
                repair_results[symbol] = sym_repairs
                sym_report = self._generate_symbol_report(symbol, sym_repairs)
                reports_by_symbol.append(sym_report)
            
            self._update_progress(100, "Completado", "completed")
            
            return {
                "status": "success",
                "report": reports_by_symbol,
                "session_id": self.session_id,
                "total_fixed": sum(sum(r["fixed"] for r in sym_repairs.values()) for sym_repairs in repair_results.values())
            }
            
        except Exception as e:
            logger.error(f"❌ Error reparación: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_symbol_report(self, symbol: str, repairs: Dict) -> str:
        fixed_total = sum(r["fixed"] for r in repairs.values())
        errors = sum(1 for r in repairs.values() if r["status"] == "error")
        report = f"""
<b>🧹 {symbol}:</b>
• Total reparado: {fixed_total}
• Errores: {errors}/{len(repairs)}
• Detalles por TF:
"""
        for tf, r in repairs.items():
            status_emoji = "✅" if r["status"] == "success" else "⚠️" if r["status"] == "no_issues" else "❌"
            report += f"  • {tf}: {r['fixed']} {status_emoji}\n"
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = RepairDataEnterprise(progress_id=args.progress_id)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())