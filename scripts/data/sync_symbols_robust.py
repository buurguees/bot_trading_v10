#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script robusto para sincronización automática de timestamps al iniciar el bot.
Versión completamente resistente a errores de I/O.
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
import pandas as pd
import sqlite3

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Importar módulos locales
from config.unified_config import get_config_manager

# Configurar encoding para Windows de forma segura
if sys.platform == "win32":
    try:
        import io
        if not hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, Exception):
        # Si hay error, continuar sin modificar
        pass

# Configuración de logging completamente robusta
def setup_logging():
    """Configuración de logging robusta"""
    try:
        # Crear directorio de logs si no existe
        Path("logs").mkdir(exist_ok=True, parents=True)
        
        # Configurar logging con manejo de errores
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/sync_symbols.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return True
    except Exception as e:
        # Si hay error, usar configuración mínima
        try:
            logging.basicConfig(level=logging.INFO)
            return True
        except Exception:
            # Si incluso esto falla, usar print
            return False

# Configurar logging
if not setup_logging():
    # Usar print como fallback
    def log_info(msg): print(f"INFO: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")
else:
    log_info = logging.info
    log_error = logging.error
    log_warning = logging.warning

logger = logging.getLogger(__name__)

class SyncSymbolsRobust:
    """Sincronización robusta de timestamps para agentes paralelos"""

    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config = get_config_manager()
        self.session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.master_timeline = None
        self.sync_quality = 0.0
        self._init_progress_file()

    def _init_progress_file(self):
        """Inicializar archivo de progreso de forma segura"""
        if self.progress_id:
            try:
                progress_path = Path("data/tmp") / f"{self.progress_id}.json"
                Path("data/tmp").mkdir(exist_ok=True, parents=True)
                with open(progress_path, 'w', encoding='utf-8') as f:
                    json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
                    f.flush()
            except Exception as e:
                log_warning(f"⚠️ Error inicializando progreso: {e}")

    def _update_progress_safe(self, progress: int, current_symbol: str, status: str = "En curso"):
        """Versión completamente segura del método _update_progress"""
        if self.progress_id:
            try:
                progress_path = Path("data/tmp") / f"{self.progress_id}.json"
                # Crear directorio si no existe
                progress_path.parent.mkdir(parents=True, exist_ok=True)
                
                bar_length = 10
                filled = int(progress / 100 * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                data = {"progress": progress, "bar": bar, "current_symbol": current_symbol, "status": status}
                
                # Escribir de forma completamente segura
                with open(progress_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                    f.flush()  # Asegurar que se escriba
                    
            except Exception as e:
                # Si hay error, solo logear, no fallar
                log_warning(f"⚠️ Error actualizando progreso: {e}")

    async def execute(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict:
        """Ejecuta sincronización de timestamps de forma robusta"""
        try:
            from core.data.database import db_manager
            symbols = symbols or self.config.get_symbols() or ['BTCUSDT']
            timeframes = timeframes or self.config.get_timeframes() or ['1m', '5m', '15m', '1h', '4h', '1d']
            start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)

            self._update_progress_safe(10, "Inicializando sincronización")
            total_symbols = len(symbols)
            step = 0
            master_timeline = {'total_points': 0, 'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(), 'symbol_data_info': {}}
            sync_data = {}

            for symbol in symbols:
                self._update_progress_safe(int((step / total_symbols) * 90) + 10, symbol)
                try:
                    data = db_manager.get_historical_data(symbol, timeframes[0], start_date, end_date)
                    if data and len(data) > 0:
                        # Los timestamps ya están en segundos en la base de datos
                        timestamps = [d['timestamp'] for d in data]
                        sync_data[symbol] = timestamps
                        master_timeline['symbol_data_info'][symbol] = {'count': len(timestamps)}
                    step += 1
                except Exception as e:
                    log_error(f"❌ {symbol}: {e}")
                    step += 1

            # Crear timeline maestro
            if sync_data:
                common_timestamps = set(sync_data[symbols[0]])
                for symbol in symbols[1:]:
                    if symbol in sync_data:
                        common_timestamps.intersection_update(sync_data[symbol])
                master_timeline['total_points'] = len(common_timestamps)
                if sync_data:
                    min_timestamps = min(len(sync_data[s]) for s in sync_data)
                    master_timeline['sync_quality'] = (len(common_timestamps) / min_timestamps) * 100 if min_timestamps > 0 else 0
                else:
                    master_timeline['sync_quality'] = 0

                # Guardar timeline maestro de forma completamente segura
                try:
                    Path("data/sync").mkdir(exist_ok=True, parents=True)
                    with open("data/sync/master_timeline.json", 'w', encoding='utf-8') as f:
                        json.dump({'timestamps': list(common_timestamps)}, f)
                        f.flush()  # Asegurar que se escriba
                except Exception as e:
                    log_warning(f"⚠️ Error guardando timeline maestro: {e}")
                    # Continuar sin fallar

            self._update_progress_safe(100, "Completado", "completed")
            report = self._generate_sync_report(master_timeline, master_timeline.get('sync_quality', 0), symbols, timeframes)
            return {
                "status": "success",
                "report": report,
                "session_id": self.session_id,
                "sync_quality": master_timeline.get('sync_quality', 0)
            }

        except Exception as e:
            log_error(f"❌ Error sincronización: {e}")
            self._update_progress_safe(0, "Error", "error")
            return {"status": "error", "message": str(e)}

    def _generate_sync_report(self, master_timeline: Dict[str, Any], sync_quality: float, symbols: List[str], timeframes: List[str]) -> str:
        """Genera reporte de sincronización"""
        try:
            total_points = master_timeline['total_points']
            start_date = master_timeline['start_date'][:10]
            end_date = master_timeline['end_date'][:10]
            timeline_quality = master_timeline.get('sync_quality', 0)
            symbol_stats = [f"• {symbol}: {master_timeline['symbol_data_info'].get(symbol, {}).get('count', 0):,} timestamps" for symbol in symbols]
            report = f"""
🔄 <b>Reporte de Sincronización de Timestamps</b>
📊 <b>Timeline Maestro:</b>
• Puntos de sincronización: {total_points:,}
• Período: {start_date} → {end_date}
• Calidad del timeline: {timeline_quality:.1f}%
• Calidad de sincronización: {sync_quality:.1f}%
🎯 <b>Configuración para Agentes:</b>
• Símbolos sincronizados: {len(symbols)}
• Timeframes: {', '.join(timeframes)}
• Archivo de sync: data/sync/master_timeline.json
📈 <b>Estadísticas por Símbolo:</b>
{chr(10).join(symbol_stats)}
✅ <b>Estado:</b> Los agentes pueden trabajar en paralelo con timestamps sincronizados
🆔 <b>Sesión:</b> {self.session_id}
"""
            return report.strip()
        except Exception as e:
            return f"❌ Error generando reporte: {e}"

async def main():
    """Función principal"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True)
    args = parser.parse_args()
    
    script = SyncSymbolsRobust(progress_id=args.progress_id)
    try:
        result = await script.execute()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("status") != "success":
            sys.exit(1)
    except Exception as e:
        log_error(f"❌ Error en main: {e}")
        error_result = {"status": "error", "message": str(e)}
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
