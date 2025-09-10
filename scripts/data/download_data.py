#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /download_data - Enterprise: Descarga, alinea y guarda datos históricos.
Llama core/data/collector.py y core/data/database.py.
Actualiza progreso por símbolo/TF.
Retorna JSON para handlers.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Any

# Importar ConfigLoader
from config.config_loader import ConfigLoader

# Cargar .env
load_dotenv()

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Logging enterprise
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/download_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DownloadDataEnterprise:
    """Gestión enterprise de descarga de datos"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.collector = None
        self.db_manager = None
        self.session_id = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        """Inicializa progreso"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "En curso"):
        """Actualiza progreso JSON"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            bar_length = 10
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
            with open(progress_path, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Progreso: {progress}% - {current_symbol}")
    
    async def initialize(self) -> bool:
        """Inicializa core/ con retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.data.collector import BitgetDataCollector
                from core.data.database import db_manager
                
                self.collector = BitgetDataCollector()
                self.db_manager = db_manager
                
                self._update_progress(10, "Inicializando collector y DB", "Configurando core/")
                logger.info("✅ Core/ inicializado (retry {}/{})".format(attempt + 1, max_retries))
                return True
            except Exception as e:
                logger.warning(f"⚠️ Error en intento {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        
        return False
    
    async def execute(self) -> Dict[str, Any]:
        """Ejecución enterprise con progreso por símbolo/TF"""
        try:
            self._update_progress(0, "Iniciando descarga", "starting")
            logger.info("🚀 Descarga enterprise iniciada")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando core/data/"}
            
            symbols = self.config.get("trading_settings", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            years = self.config.get("data_collection", {}).get("historical", {}).get("years", 1)
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No symbols/timeframes en config"}
            
            self._update_progress(20, f"Descargando {len(symbols)} símbolos", "Cargando datos")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes} | Años: {years}")
            
            total_steps = len(symbols) * len(timeframes)
            step = 0
            download_results = {}
            reports_by_symbol = []  # Para delays en handlers
            
            for symbol in symbols:
                self._update_progress(30 + (step / total_steps * 40), symbol, "Descargando símbolo")
                symbol_results = {}
                
                for tf in timeframes:
                    try:
                        # Descargar via core/data/collector.py
                        data = await self.collector.download_historical_data(symbol, tf, days_back=years * 365)
                        if data and data.get("success"):
                            count = data.get("records", 0)
                            symbol_results[tf] = {"status": "downloaded", "count": count}
                            # Guardar via core/data/database.py
                            session_saved = self.db_manager.store_historical_data(data["data"], symbol, tf, self.session_id)
                            if session_saved:
                                logger.info(f"✅ {symbol} {tf}: {count} registros guardados")
                            step += 1
                        else:
                            symbol_results[tf] = {"status": "error", "count": 0}
                            logger.warning(f"⚠️ Error descargando {symbol} {tf}")
                            step += 1
                    except Exception as e:
                        logger.error(f"❌ Error {symbol} {tf}: {e}")
                        symbol_results[tf] = {"status": "error", "count": 0}
                        step += 1
                
                download_results[symbol] = symbol_results
                # Reporte por símbolo
                sym_report = self._generate_symbol_report(symbol, symbol_results)
                reports_by_symbol.append(sym_report)
            
            self._update_progress(100, "Completado", "completed")
            
            # Log en DB
            self.db_manager.log_download_session(self.session_id, symbols, timeframes, download_results)
            
            return {
                "status": "success",
                "report": reports_by_symbol,  # Lista para delays
                "session_id": self.session_id,
                "total_downloaded": sum(sum(r["count"] for r in sym_results.values()) for sym_results in download_results.values())
            }
            
        except Exception as e:
            logger.error(f"❌ Error descarga enterprise: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_symbol_report(self, symbol: str, results: Dict) -> str:
        """Reporte detallado por símbolo"""
        downloaded = sum(r["count"] for r in results.values() if r["status"] == "downloaded")
        errors = sum(1 for r in results.values() if r["status"] == "error")
        report = f"""
<b>📥 {symbol}:</b>
• Descargados: {downloaded:,} registros total
• Errores: {errors}/{len(results)}
• Detalles por TF:
"""
        for tf, res in results.items():
            status_emoji = "✅" if res["status"] == "downloaded" else "❌"
            report += f"  • {tf}: {res['count']:,} {status_emoji}\n"
        return report.strip()
    
    def _generate_report(self, results: Dict, session_id: str) -> str:
        """Reporte global (usado si no por símbolo)"""
        total_downloaded = sum(sum(r["count"] for r in sym_results.values()) for sym_results in results.values())
        total_errors = sum(len([r for r in sym_results.values() if r["status"] == "error"]) for sym_results in results.values())
        report = f"""
📊 <b>Reporte Global de Descarga</b>

📈 Total descargado: {total_downloaded:,} registros
❌ Errores: {total_errors}
🆔 Sesión: {session_id}
✅ Estado: Completado enterprise
        """
        return report.strip()

async def main():
    """Entrada: Parse --progress_id"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = DownloadDataEnterprise(progress_id=args.progress_id)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))  # Para handlers
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())