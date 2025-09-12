#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /download_data - Enterprise: Descarga, alinea y guarda datos históricos.
Llama core/data/collector.py y core/data/database.py.
Analiza datos existentes, repara gaps/duplicados, guarda en data/{symbol}/trading_bot.db.
Retorna JSON para handlers.py.
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any

# Path al root
root_path = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, root_path)
os.chdir(root_path)

# Importar ConfigLoader después de cambiar directorio
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

# Configurar encoding para Windows
if sys.platform == "win32":
    import io
    import codecs
    # Configurar stdout y stderr con encoding UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)

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
        """Inicializa progreso"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True, parents=True)
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
            logger.debug(f"Progreso: {progress}% - {current_symbol} - {status}")
    
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
                logger.info(f"✅ Core/ inicializado (retry {attempt + 1}/{max_retries})")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Error en intento {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)
        logger.error("❌ Fallo al inicializar core/")
        return False
    
    async def execute(self) -> Dict[str, Any]:
        """Ejecución enterprise con análisis, reparación y descarga"""
        try:
            self._update_progress(0, "Iniciando descarga", "starting")
            logger.info("🚀 Descarga enterprise iniciada")
            
            if not await self.initialize():
                return {"status": "error", "message": "Error inicializando core/data/"}
            
            # Cargar configuración desde archivos YAML
            symbols = self.config.get_symbols()
            
            # Usar configuración de data_sources.yaml como mínimo
            data_sources_config = self.config.get("data_sources", {})
            historical_config = data_sources_config.get("data_collection", {}).get("historical", {})
            
            # Configuración mínima desde YAML
            min_years = int(historical_config.get("years", 1))
            min_timeframes = historical_config.get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            
            # Usar timeframes configurados o mínimo
            timeframes = self.config.get_timeframes() or min_timeframes
            years = min_years
            
            logger.info(f"📋 Configuración mínima: {min_years} años, {min_timeframes}")
            logger.info(f"📋 Configuración activa: {years} años, {timeframes}")
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No symbols/timeframes en config"}
            
            self._update_progress(20, f"Procesando {len(symbols)} símbolos", "Cargando datos")
            logger.info(f"Símbolos: {symbols} | TFs: {timeframes} | Años: {years}")
            
            total_steps = len(symbols) * len(timeframes)
            step = 0
            download_results = {}
            reports_by_symbol = []
            
            for symbol in symbols:
                symbol_results = {}
                db_path = f"data/{symbol}/trading_bot.db"
                
                for tf in timeframes:
                    self._update_progress(30 + (step / total_steps * 40), f"{symbol} {tf}", "Analizando datos")
                    step += 1
                    
                    try:
                        # Verificar si existe DB
                        db_exists = Path(db_path).exists()
                        
                        if db_exists:
                            # Analizar datos existentes
                            analysis = self.db_manager.analyze_historical_data(symbol, tf, db_path)
                            
                            # Calcular días de datos actuales
                            records_per_day = 24 if tf == "1h" else 6 if tf == "4h" else 1440 if tf == "1m" else 288 if tf == "5m" else 96 if tf == "15m" else 1
                            current_days = analysis["total_records"] / records_per_day
                            expected_days = years * 365
                            
                            logger.info(f"📊 {symbol} {tf}: {current_days:.1f} días actuales vs {expected_days} días esperados")
                            
                            # Verificar si necesita descargar datos mínimos
                            if current_days < expected_days * 0.8:  # Menos del 80% de los datos mínimos
                                logger.info(f"📥 {symbol} {tf}: Solo {current_days:.1f} días, descargando {expected_days} días mínimos")
                                # Descarga mínima garantizada
                                data = await self.collector.download_historical_data(symbol, tf, days_back=years * 365)
                                if data.get("success"):
                                    self.db_manager.store_historical_data(data["data"], symbol, tf, db_path)
                                    symbol_results[tf] = {"status": "downloaded", "count": len(data["data"])}
                                    logger.info(f"✅ {symbol} {tf}: Descargados {len(data['data'])} registros mínimos")
                                else:
                                    symbol_results[tf] = {"status": "error", "count": 0}
                                    logger.warning(f"⚠️ Error descargando {symbol} {tf}")
                            elif analysis.get("gaps") or analysis.get("duplicates"):
                                logger.info(f"🛠️ Reparando {symbol} {tf}: {len(analysis['gaps'])} gaps, {len(analysis['duplicates'])} duplicados")
                                self.db_manager.repair_historical_data(symbol, tf, analysis["gaps"], analysis["duplicates"], db_path)
                                
                                # Descargar datos para gaps
                                if analysis.get("gaps"):
                                    for start_ts, end_ts in analysis["gaps"]:
                                        start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                                        end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
                                        data = await self.collector.download_historical_data(symbol, tf, start=start, end=end)
                                        if data.get("success"):
                                            self.db_manager.store_historical_data(data["data"], symbol, tf, db_path)
                                            symbol_results[tf] = {"status": "repaired", "count": len(data["data"])}
                                            logger.info(f"✅ {symbol} {tf}: Reparados {len(data['data'])} registros")
                                        else:
                                            symbol_results[tf] = {"status": "error", "count": 0}
                                            logger.warning(f"⚠️ Error reparando {symbol} {tf}")
                                else:
                                    symbol_results[tf] = {"status": "repaired", "count": analysis["total_records"]}
                                    logger.info(f"✅ {symbol} {tf}: Duplicados eliminados, {analysis['total_records']} registros")
                            else:
                                symbol_results[tf] = {"status": "no_gaps", "count": analysis["total_records"]}
                                logger.info(f"✅ {symbol} {tf}: Datos completos ({analysis['total_records']} registros, {current_days:.1f} días)")
                        else:
                            # Descarga completa
                            data = await self.collector.download_historical_data(symbol, tf, days_back=years * 365)
                            if data.get("success"):
                                self.db_manager.store_historical_data(data["data"], symbol, tf, db_path)
                                symbol_results[tf] = {"status": "downloaded", "count": len(data["data"])}
                                logger.info(f"✅ {symbol} {tf}: Descargados {len(data['data'])} registros")
                            else:
                                symbol_results[tf] = {"status": "error", "count": 0}
                                logger.warning(f"⚠️ Error descargando {symbol} {tf}")
                    except Exception as e:
                        logger.error(f"❌ Error procesando {symbol} {tf}: {e}")
                        symbol_results[tf] = {"status": "error", "count": 0}
                
                download_results[symbol] = symbol_results
                reports_by_symbol.append(self._generate_symbol_report(symbol, symbol_results))
            
            self._update_progress(100, "Completado", "completed")
            
            # Log en DB
            self.db_manager.log_download_session(self.session_id, symbols, timeframes, download_results)
            
            return {
                "status": "success",
                "report": reports_by_symbol,
                "session_id": self.session_id,
                "total_downloaded": sum(sum(r["count"] for r in sym_results.values()) for sym_results in download_results.values())
            }
            
        except Exception as e:
            logger.error(f"❌ Error descarga enterprise: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    def _generate_symbol_report(self, symbol: str, results: Dict) -> str:
        """Reporte detallado por símbolo"""
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
            status_emoji = "✅" if res["status"] in ["downloaded", "repaired", "no_gaps"] else "❌"
            status_text = res["status"].replace("_", " ").title()
            report += f"  • {tf}: {res['count']:,} {status_emoji} ({status_text})\n"
        return report.strip()

async def main():
    """Entrada: Parse --progress_id"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = DownloadDataEnterprise(progress_id=args.progress_id)
    try:
        result = await script.execute()
        # Asegurar encoding UTF-8 para la salida
        import sys
        if sys.platform == "win32":
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") != "success":
            sys.exit(1)
    finally:
        # Cerrar sesión aiohttp
        if hasattr(script, 'collector') and script.collector:
            await script.collector.close()

if __name__ == "__main__":
    asyncio.run(main())