#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para descarga y reparación automática de datos históricos al iniciar el bot.
Descarga desde 01/09/2024, repara gaps/duplicados, guarda en data/{symbol}/trading_bot.db.
Llama core/data/collector.py y core/data/database.py.
Retorna JSON para bot.py.
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root
root_path = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, root_path)
os.chdir(root_path)

# Importar ConfigLoader
from config.unified_config import get_config_manager

# Cargar .env
load_dotenv()

# Logging enterprise
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_data.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurar encoding para Windows
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except AttributeError:
        # Si ya está configurado, no hacer nada
        pass

class DownloadDataEnterprise:
    """Gestión enterprise de descarga de datos"""

    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config = get_config_manager()
        self.collector = None
        self.db_manager = None
        self.session_id = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()

    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True, parents=True)
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)

    def _update_progress(self, progress: int, current_symbol: str, status: str = "En curso"):
        if self.progress_id:
            try:
                progress_path = Path("data/tmp") / f"{self.progress_id}.json"
                # Crear directorio si no existe
                progress_path.parent.mkdir(parents=True, exist_ok=True)
                
                bar_length = 10
                filled = int(progress / 100 * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
                
                # Escribir de forma segura
                with open(progress_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                    f.flush()  # Asegurar que se escriba
                    
            except Exception as e:
                # Si hay error, solo logear, no fallar
                print(f"⚠️ Error actualizando progreso: {e}")

    def _update_progress_safe(self, progress: int, current_symbol: str, status: str = "En curso"):
        """Versión segura del método _update_progress"""
        self._update_progress(progress, current_symbol, status)

    async def initialize(self) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.data.collector import BitgetDataCollector
                from core.data.database import db_manager
                self.collector = BitgetDataCollector()
                self.db_manager = db_manager
                self._update_progress_safe(10, "Inicializando", "Configurando core/")
                logger.info("✅ Collector y DB inicializados")
                return True
            except Exception as e:
                logger.error(f"❌ Error inicializando (intento {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def execute(self, symbols: List[str] = None, timeframes: List[str] = None, start_date: datetime = None) -> Dict:
        """Ejecuta descarga y reparación desde start_date"""
        try:
            if not await self.initialize():
                return {"status": "error", "message": "No se pudo inicializar collector o DB"}

            symbols = symbols or self.config.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or self.config.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            start_date = start_date or datetime(2024, 9, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)

            download_results = {}
            reports_by_symbol = []
            total_symbols = len(symbols)
            step = 0

            for symbol in symbols:
                self._update_progress_safe(int((step / total_symbols) * 90) + 10, symbol)
                symbol_results = {}
                for tf in timeframes:
                    try:
                        # Verificar datos existentes
                        last_ts = self.db_manager.get_last_timestamp(symbol, tf)
                        start_ts = int(start_date.timestamp() * 1000)
                        if last_ts:
                            start_ts = max(start_ts, last_ts)
                        data = await self.collector.download_historical_data(symbol, tf, start_ts, int(end_date.timestamp() * 1000))
                        if data.get("success"):
                            count = len(data.get("data", []))
                            self.db_manager.store_historical_data(symbol, tf, data["data"])
                            symbol_results[tf] = {"count": count, "status": "downloaded"}
                            # Reparar datos
                            self.db_manager.repair_data(symbol, tf)
                        else:
                            symbol_results[tf] = {"count": 0, "status": "error"}
                    except Exception as e:
                        logger.error(f"❌ {symbol} {tf}: {e}")
                        symbol_results[tf] = {"count": 0, "status": "error"}
                download_results[symbol] = symbol_results
                reports_by_symbol.append(self._generate_symbol_report(symbol, symbol_results))
                step += 1

            self._update_progress_safe(100, "Completado", "completed")
            self.db_manager.log_download_session(self.session_id, symbols, timeframes, download_results)
            return {
                "status": "success",
                "report": reports_by_symbol,
                "session_id": self.session_id,
                "total_downloaded": sum(sum(r["count"] for r in sym_results.values()) for sym_results in download_results.values())
            }

        except Exception as e:
            logger.error(f"❌ Error descarga enterprise: {e}")
            self._update_progress_safe(0, "Error", "error")
            return {"status": "error", "message": str(e)}

    def _generate_symbol_report(self, symbol: str, results: Dict) -> str:
        downloaded = sum(r["count"] for r in results.values() if r["status"] in ["downloaded", "repaired"])
        errors = sum(1 for r in results.values() if r["status"] == "error")
        total_records = sum(r["count"] for r in results.values())
        report = f"""
<b>📥 {symbol}:</b>
• Total registros: {total_records:,}
• Descargados/Reparados: {downloaded:,} registros
• Errores: {errors}/{len(results)}
• Detalles por TF:
"""
        for tf, res in results.items():
            status_emoji = "✅" if res["status"] in ["downloaded", "repaired"] else "❌"
            status_text = res["status"].replace("_", " ").title()
            report += f"  • {tf}: {res['count']:,} {status_emoji} ({status_text})\n"
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = DownloadDataEnterprise(progress_id=args.progress_id)
    try:
        result = await script.execute()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("status") != "success":
            sys.exit(1)
    finally:
        if hasattr(script, 'collector') and script.collector:
            await script.collector.close()

if __name__ == "__main__":
    asyncio.run(main())