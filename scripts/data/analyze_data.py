#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /analyze_data - Enterprise: Analiza issues (gaps, duplicados).
Llama core/data/history_analyzer.py.
Progreso por símbolo.
Retorna JSON para handlers.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root PRIMERO
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Ahora importar módulos locales
from config.unified_config import get_config_manager

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/analyze_data.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AnalyzeDataEnterprise:
    """Análisis enterprise de datos"""
    
    def __init__(self, progress_id: str = None, auto_repair: bool = True):
        self.progress_id = progress_id
        self.auto_repair = auto_repair
        self.config = get_config_manager()
        self.analyzer = None
        self._init_progress_file()
    
    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "Analizando"):
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
                
                self.analyzer = HistoryAnalyzer()
                
                self._update_progress(10, "Inicializando analyzer", "Configurando core/")
                logger.info("✅ Analyzer inicializado")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Retry {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        return False
    
    async def execute(self) -> Dict[str, Any]:
        try:
            self._update_progress(0, "Iniciando análisis", "starting")
            logger.info("🚀 Análisis enterprise iniciado")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando analyzer"}
            
            symbols = self.config.get_symbols()
            timeframes = self.config.get_timeframes()
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No config"}
            
            self._update_progress(20, f"Analizando {len(symbols)} símbolos", "Detectando issues")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes}")
            
            total_steps = len(symbols)
            step = 0
            issues_by_symbol = {}
            reports_by_symbol = []
            total_issues = 0
            
            for symbol in symbols:
                self._update_progress(30 + (step / total_steps * 50), symbol, "Analizando símbolo")
                try:
                    # Detectar issues via analyzer
                    issues = await self.analyzer.detect_data_issues([symbol], timeframes=timeframes)
                    sym_issues = issues.get("symbols", {}).get(symbol, {})
                    total_issues += sym_issues.get("total_issues", 0)
                    
                    # Reparar si auto_repair
                    if self.auto_repair:
                        repair = await self.analyzer.repair_data_issues(
                            [symbol], repair_duplicates=True, fill_gaps=True, timeframes=timeframes
                        )
                        sym_issues["repairs"] = repair.get("successful_repairs", 0)
                    
                    issues_by_symbol[symbol] = sym_issues
                    sym_report = self._generate_symbol_report(symbol, sym_issues)
                    reports_by_symbol.append(sym_report)
                    step += 1
                except Exception as e:
                    logger.error(f"❌ {symbol}: {e}")
                    issues_by_symbol[symbol] = {"total_issues": 0, "status": "error"}
                    step += 1
            
            self._update_progress(100, "Completado", "completed")
            
            return {
                "status": "success",
                "report": reports_by_symbol,
                "total_issues": total_issues,
                "issues_by_symbol": issues_by_symbol
            }
            
        except Exception as e:
            logger.error(f"❌ Error análisis: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_symbol_report(self, symbol: str, issues: Dict) -> str:
        gaps = issues.get("gaps", 0)
        duplicates = issues.get("duplicates", 0)
        invalid = issues.get("invalid_ohlcv", 0)
        repairs = issues.get("repairs", 0)
        report = f"""
<b>🔍 {symbol}:</b>
• Gaps: {gaps}
• Duplicados: {duplicates}
• Inválidos: {invalid}
• Reparados: {repairs}
• Estado: {'✅ Limpio' if issues.get("total_issues", 0) == 0 else '⚠️ Issues encontrados'}
        """
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    parser.add_argument("--no-repair", action="store_true")
    args = parser.parse_args()
    
    script = AnalyzeDataEnterprise(progress_id=args.progress_id, auto_repair=not args.no_repair)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())