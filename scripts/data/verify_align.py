#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para alineación automática de timeframes al iniciar el bot.
Verifica y alinea temporalmente, guarda en aligned_market_data.
Llama core/data/temporal_alignment.py y core/data/database.py.
Retorna JSON para bot.py.
"""

import asyncio
import sys
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Importar configuración
from config.unified_config import get_config_manager

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/verify_align.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class VerifyAlignEnterprise:
    """Verificación y alineación enterprise"""

    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config = get_config_manager()
        self.aligner = None
        self.db = None
        self.session_id = f"align_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()

    def _init_progress_file(self):
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True)
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)

    def _update_progress(self, progress: int, current_symbol: str, status: str = "Verificando"):
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
                from core.data.temporal_alignment import TemporalAlignment
                from core.data.database import db_manager
                self.aligner = TemporalAlignment()
                self.db = db_manager
                self._update_progress(10, "Inicializando aligner", "Configurando core/")
                logger.info("✅ Aligner y DB inicializados")
                return True
            except Exception as e:
                logger.error(f"❌ Error inicializando (intento {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def execute(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict:
        """Ejecuta alineación de timeframes por símbolo"""
        try:
            if not await self.initialize():
                return {"status": "error", "message": "No se pudo inicializar aligner o DB"}

            symbols = symbols or self.config.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or self.config.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)

            align_results = {}
            reports_by_symbol = []
            total_symbols = len(symbols)
            step = 0

            for symbol in symbols:
                self._update_progress(int((step / total_symbols) * 90) + 10, symbol)
                sym_align = {}
                total_records = 0
                start_dt = start_date.strftime('%Y-%m-%d')
                end_dt = end_date.strftime('%Y-%m-%d')
                try:
                    for tf in timeframes:
                        try:
                            data = self.db.get_historical_data(symbol, tf, start_date, end_date)
                            if data and len(data) > 0:
                                # Convertir DataFrame a formato esperado por align_symbol_data
                                df = pd.DataFrame(data)
                                
                                # Verificar que tenemos las columnas necesarias
                                if 'timestamp' not in df.columns:
                                    logger.error(f"❌ {symbol} {tf}: No timestamp column found")
                                    sym_align[tf] = {"aligned": 0, "status": "no_timestamp"}
                                    continue
                                
                                # Convertir timestamp a datetime y establecer como índice
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                                df = df.set_index('timestamp')
                                
                                # Crear timeline maestra para este timeframe
                                master_timeline = self.aligner.create_master_timeline(tf, start_date, end_date)
                                
                                # Alinear datos del símbolo
                                symbol_data = {symbol: df}
                                aligned_data = self.aligner.align_symbol_data(symbol_data, master_timeline, tf)
                                
                                if symbol in aligned_data and not aligned_data[symbol].empty:
                                    # Convertir de vuelta a formato de lista para almacenar
                                    aligned_df = aligned_data[symbol].reset_index()
                                    
                                    # El índice se convierte en una columna con el nombre del índice original
                                    # Necesitamos renombrar la columna del índice a 'timestamp'
                                    # Cuando se hace reset_index(), la columna del índice se llama 'index'
                                    if 'index' in aligned_df.columns:
                                        aligned_df = aligned_df.rename(columns={'index': 'timestamp'})
                                    elif 'timestamp' in aligned_df.columns:
                                        # Ya tiene la columna timestamp
                                        pass
                                    else:
                                        # Buscar la columna que contiene timestamps
                                        for col in aligned_df.columns:
                                            if aligned_df[col].dtype.name.startswith('datetime'):
                                                aligned_df = aligned_df.rename(columns={col: 'timestamp'})
                                                break
                                    
                                    # Convertir timestamp a segundos
                                    if 'timestamp' in aligned_df.columns:
                                        aligned_df['timestamp'] = aligned_df['timestamp'].astype('int64') // 10**9  # Convertir a segundos
                                    
                                    aligned_list = aligned_df.to_dict('records')
                                    
                                    self.db.store_aligned_data(symbol, tf, aligned_list, self.session_id)
                                    total_records += len(aligned_list)
                                    sym_align[tf] = {"aligned": len(aligned_list), "status": "success"}
                                else:
                                    sym_align[tf] = {"aligned": 0, "status": "no_aligned_data"}
                            else:
                                sym_align[tf] = {"aligned": 0, "status": "no_data"}
                        except Exception as e:
                            logger.error(f"❌ {symbol} {tf}: {e}")
                            import traceback
                            logger.error(f"❌ {symbol} {tf} traceback: {traceback.format_exc()}")
                            sym_align[tf] = {"aligned": 0, "status": "error"}
                    align_results[symbol] = sym_align
                    sym_report = self._generate_symbol_report(symbol, sym_align, start_dt, end_dt, total_records)
                    reports_by_symbol.append(sym_report)
                    step += 1
                except Exception as e:
                    logger.error(f"❌ {symbol}: {e}")
                    align_results[symbol] = {"status": "error"}
                    reports_by_symbol.append(f"<b>{symbol}:</b>\n• ❌ Error: {str(e)}")
                    step += 1

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

    def _generate_symbol_report(self, symbol: str, aligns: Dict, start_dt: str, end_dt: str, total: int) -> str:
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