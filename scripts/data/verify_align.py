#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /verify_align - Enterprise: Verifica y alinea temporalmente.
Llama core/data/temporal_alignment.py y core/data/database.py.
Progreso por símbolo/TF.
Retorna JSON para handlers.py.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any
from datetime import datetime, timedelta

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
    handlers=[logging.FileHandler('logs/verify_align.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class VerifyAlignEnterprise:
    """Verificación y alineación enterprise"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config_loader = ConfigLoader("config/user_settings.yaml")
        self.config = self.config_loader.load_config()
        self.aligner = None
        self.db = None
        self.session_id = f"align_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "Verificando"):
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
                from core.data.temporal_alignment import TemporalAlignment
                from core.data.database import db_manager
                from core.data.historical_data_adapter import get_historical_data
                
                self.aligner = TemporalAlignment()
                self.db = db_manager
                self.get_data = get_historical_data  # Para cargar datos
                
                self._update_progress(10, "Inicializando aligner y DB", "Configurando core/")
                logger.info("✅ Core/ inicializado")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Retry {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        return False
    
    async def execute(self) -> Dict[str, Any]:
        try:
            self._update_progress(0, "Iniciando verificación", "starting")
            logger.info("🚀 Verificación/alineación enterprise iniciada")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando core/data/"}
            
            symbols = self.config.get("trading_settings", {}).get("symbols", [])
            timeframes = self.config.get("trading_settings", {}).get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            years = self.config.get("data_collection", {}).get("historical", {}).get("years", 1)
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No config"}
            
            self._update_progress(20, f"Verificando {len(symbols)} símbolos", "Cargando datos")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes} | Años: {years}")
            
            total_steps = len(symbols) * len(timeframes)
            step = 0
            align_results = {}
            reports_by_symbol = []
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            for symbol in symbols:
                self._update_progress(30 + (step / total_steps * 40), symbol, "Verificando símbolo")
                sym_align = {}
                start_dt, end_dt = None, None
                total_records = 0
                
                for tf in timeframes:
                    try:
                        # Cargar datos via core/data/historical_data_adapter.py
                        df = self.get_data(symbol=symbol, timeframe=tf, start=start_date, end=end_date)
                        if df is not None and not df.empty:
                            # Alinear via core/data/temporal_alignment.py
                            aligned_df = await self.aligner.align_temporal_data(df, tf)
                            if aligned_df is not None:
                                count = len(aligned_df)
                                sym_align[tf] = {"aligned": count, "status": "success"}
                                total_records += count
                                
                                # Actualizar rangos
                                if start_dt is None:
                                    start_dt = aligned_df.index.min()
                                    end_dt = aligned_df.index.max()
                                else:
                                    start_dt = min(start_dt, aligned_df.index.min())
                                    end_dt = max(end_dt, aligned_df.index.max())
                                
                                # Guardar via DB
                                self.db.store_aligned_data({symbol: aligned_df}, tf, self.session_id)
                                step += 1
                            else:
                                sym_align[tf] = {"aligned": 0, "status": "no_data"}
                                step += 1
                        else:
                            sym_align[tf] = {"aligned": 0, "status": "empty"}
                            step += 1
                    except Exception as e:
                        logger.error(f"❌ {symbol} {tf}: {e}")
                        sym_align[tf] = {"aligned": 0, "status": "error"}
                        step += 1
                
                align_results[symbol] = sym_align
                if total_records > 0:
                    sym_report = self._generate_symbol_report(symbol, sym_align, start_dt, end_dt, total_records)
                else:
                    sym_report = f"<b>{symbol}:</b>\n• ❌ Sin datos para alinear"
                reports_by_symbol.append(sym_report)
            
            self._update_progress(100, "Completado", "completed")
            
            self.db.log_alignment_session(self.session_id, symbols, timeframes, align_results)
            
            return {
                "status": "success",
                "report": reports_by_symbol,
                "session_id": self.session_id,
                "total_aligned": sum(sum(r["aligned"] for r in sym_align.values()) for sym_align in align_results.values())
            }
            
        except Exception as e:
            logger.error(f"❌ Error alineación: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_symbol_report(self, symbol: str, aligns: Dict, start_dt, end_dt, total: int) -> str:
        aligned_total = sum(r["aligned"] for r in aligns.values())
        errors = sum(1 for r in aligns.values() if r["status"] == "error")
        report = f"""
<b>🔗 {symbol}:</b>
• Total alineado: {aligned_total:,} registros
• Errores: {errors}/{len(aligns)}
• Rango: {start_dt} a {end_dt} ({total:,} total)
• Detalles por TF:
"""
        for tf, r in aligns.items():
            status_emoji = "✅" if r["status"] == "success" else "⚠️" if r["status"] == "no_data" else "❌"
            report += f"  • {tf}: {r['aligned']:,} {status_emoji}\n"
        return report.strip()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = VerifyAlignEnterprise(progress_id=args.progress_id)
    result = await script.execute()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())