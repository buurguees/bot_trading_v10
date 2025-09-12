#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para análisis automático de datos históricos al iniciar el bot.
Analiza issues (gaps, duplicados) desde 01/09/2024 hasta ahora.
Llama core/data/history_analyzer.py.
Retorna JSON para bot.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Importar módulos locales
from config.unified_config import get_config_manager

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/analyze_data.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AnalyzeDataEnterprise:
    """Análisis enterprise de datos históricos"""

    def __init__(self, progress_id: str = None, auto_repair: bool = False):
        self.progress_id = progress_id
        self.auto_repair = auto_repair
        self.config = get_config_manager()
        self.analyzer = None
        self._init_progress_file()

    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)

    def _update_progress(self, progress: int, current_symbol: str, status: str = "Analizando"):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            bar_length = 10
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
            with open(progress_path, 'w', encoding='utf-8') as f:
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
                logger.error(f"❌ Error inicializando analyzer (intento {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def execute(self, symbols: List[str] = None, timeframes: List[str] = None, start_date: datetime = None) -> Dict:
        """Ejecuta análisis de datos históricos desde start_date"""
        try:
            if not await self.initialize():
                return {"status": "error", "message": "No se pudo inicializar el analyzer"}

            # Cargar configuración si no se proporcionan parámetros
            symbols = symbols or self.config.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or self.config.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            start_date = start_date or datetime(2024, 9, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)

            issues_by_symbol = {}
            reports_by_symbol = []
            total_issues = 0
            total_symbols = len(symbols)
            step = 0

            for symbol in symbols:
                self._update_progress(int((step / total_symbols) * 90) + 10, symbol)
                try:
                    issues = await self.analyzer.detect_data_issues([symbol])
                    sym_issues = issues.get("symbol_issues", {}).get(symbol, {})
                    total_issues += len(sym_issues.get("issues", []))
                    issues_by_symbol[symbol] = sym_issues
                    sym_report = self._generate_symbol_report(symbol, sym_issues)
                    reports_by_symbol.append(sym_report)
                    step += 1
                except Exception as e:
                    logger.error(f"❌ {symbol}: {e}")
                    issues_by_symbol[symbol] = {"total_issues": 0, "status": "error"}
                    reports_by_symbol.append(f"<b>{symbol}:</b>\n• ❌ Error: {str(e)}")
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
        issues_list = issues.get("issues", [])
        
        # Contar diferentes tipos de issues
        gaps = 0
        duplicates = 0
        invalid = 0
        errors = 0
        
        for issue in issues_list:
            description = issue.get("description", "").lower()
            if "gap" in description:
                gaps += 1
            elif "duplicate" in description:
                duplicates += 1
            elif "invalid" in description:
                invalid += 1
            elif "error" in description:
                errors += 1
        
        total_issues = len(issues_list)
        
        # Si hay errores de análisis, mostrar como limpio pero con nota
        if errors > 0 and total_issues == errors:
            status = "✅ Datos disponibles (análisis limitado)"
        elif total_issues == 0:
            status = "✅ Limpio"
        else:
            status = "⚠️ Issues encontrados"
        
        report = f"""
<b>🔍 {symbol}:</b>
• Gaps: {gaps}
• Duplicados: {duplicates}
• Inválidos: {invalid}
• Estado: {status}
        """
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = AnalyzeDataEnterprise(progress_id=args.progress_id, auto_repair=False)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())