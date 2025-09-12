#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simplificado para /sync_symbols - Sincroniza timestamps para agentes paralelos.
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
import sqlite3

# Path al root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Importar configuración
from config.unified_config import get_config_manager

# Configurar encoding para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_symbols.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SyncSymbolsSimple:
    """Sincronización simple de timestamps para agentes paralelos"""
    
    def __init__(self, progress_id: str = None):
        self.progress_id = progress_id
        self.config = get_config_manager()
        self.session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_progress_file()
    
    def _init_progress_file(self):
        """Inicializa archivo de progreso"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            Path("data/tmp").mkdir(exist_ok=True, parents=True)
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump({"progress": 0, "bar": "░░░░░░░░░░", "current_symbol": "Iniciando", "status": "starting"}, f)
    
    def _update_progress(self, progress: int, current_symbol: str, status: str = "En curso"):
        """Actualiza progreso"""
        if self.progress_id:
            progress_path = Path("data/tmp") / f"{self.progress_id}.json"
            bar_length = 10
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            data = {
                "progress": progress,
                "bar": bar,
                "current_symbol": current_symbol,
                "status": status
            }
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            logger.debug(f"Progreso: {progress}% - {current_symbol}")
    
    async def execute(self) -> Dict[str, Any]:
        """Ejecuta sincronización de timestamps"""
        try:
            self._update_progress(0, "Iniciando", "starting")
            logger.info("🔄 Iniciando sincronización de timestamps...")
            
            # Obtener configuración
            symbols = self.config.get_symbols()
            timeframes = self.config.get_timeframes()
            
            if not symbols or not timeframes:
                return {"status": "error", "message": "No symbols/timeframes en configuración"}
            
            self._update_progress(20, f"Analizando {len(symbols)} símbolos", "Cargando")
            logger.info(f"📊 Símbolos: {symbols} | Timeframes: {timeframes}")
            
            # Crear timeline maestro
            master_timeline = await self._create_master_timeline(symbols, timeframes)
            if not master_timeline:
                return {"status": "error", "message": "No se pudo crear timeline maestro"}
            
            self._update_progress(60, "Timeline creado", "Sincronizando")
            logger.info(f"✅ Timeline maestro: {len(master_timeline['timestamps'])} puntos")
            
            # Crear archivo de sincronización
            sync_file_created = await self._create_sync_file(master_timeline, symbols, timeframes)
            if not sync_file_created:
                return {"status": "error", "message": "No se pudo crear archivo de sincronización"}
            
            self._update_progress(80, "Archivo creado", "Finalizando")
            
            # Generar reporte
            report = self._generate_report(master_timeline, symbols, timeframes)
            
            self._update_progress(100, "Completado", "completed")
            
            return {
                "status": "success",
                "report": report,
                "session_id": self.session_id,
                "master_timeline": master_timeline,
                "sync_file": "data/sync/master_timeline.json"
            }
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")
            self._update_progress(0, "Error", "error")
            return {"status": "error", "message": str(e)}
    
    async def _create_master_timeline(self, symbols: List[str], timeframes: List[str]) -> Optional[Dict[str, Any]]:
        """Crea timeline maestro unificado"""
        try:
            logger.info("🔄 Creando timeline maestro...")
            
            # Obtener timestamps comunes
            all_timestamps = set()
            symbol_data_info = {}
            
            for symbol in symbols:
                symbol_timestamps = set()
                for timeframe in timeframes:
                    db_path = f"data/{symbol}/trading_bot.db"
                    if Path(db_path).exists():
                        timestamps = await self._get_symbol_timestamps(symbol, timeframe, db_path)
                        symbol_timestamps.update(timestamps)
                
                symbol_data_info[symbol] = {
                    'timestamps': list(symbol_timestamps),
                    'count': len(symbol_timestamps)
                }
                
                if not all_timestamps:
                    all_timestamps = symbol_timestamps.copy()
                else:
                    all_timestamps = all_timestamps.intersection(symbol_timestamps)
            
            if not all_timestamps:
                logger.error("❌ No se encontraron timestamps comunes")
                return None
            
            # Ordenar timestamps
            sorted_timestamps = sorted(list(all_timestamps))
            
            # Calcular rango de fechas
            start_ts = min(sorted_timestamps)
            end_ts = max(sorted_timestamps)
            start_date = datetime.fromtimestamp(start_ts, tz=timezone.utc)
            end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc)
            
            master_timeline = {
                'timestamps': sorted_timestamps,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_points': len(sorted_timestamps),
                'symbols': symbols,
                'timeframes': timeframes,
                'created_at': datetime.now().isoformat(),
                'symbol_data_info': symbol_data_info
            }
            
            logger.info(f"✅ Timeline maestro: {len(sorted_timestamps)} puntos")
            logger.info(f"📅 Rango: {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")
            
            return master_timeline
            
        except Exception as e:
            logger.error(f"❌ Error creando timeline: {e}")
            return None
    
    async def _get_symbol_timestamps(self, symbol: str, timeframe: str, db_path: str) -> List[int]:
        """Obtiene timestamps de un símbolo"""
        try:
            with sqlite3.connect(db_path) as conn:
                query = """
                SELECT DISTINCT timestamp
                FROM market_data 
                WHERE timeframe = ?
                ORDER BY timestamp
                """
                
                cursor = conn.execute(query, [timeframe])
                timestamps = [row[0] for row in cursor.fetchall()]
                return timestamps
                
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo timestamps de {symbol} {timeframe}: {e}")
            return []
    
    async def _create_sync_file(self, master_timeline: Dict[str, Any], symbols: List[str], timeframes: List[str]) -> bool:
        """Crea archivo de sincronización para agentes"""
        try:
            sync_dir = Path("data/sync")
            sync_dir.mkdir(exist_ok=True, parents=True)
            
            sync_file_path = sync_dir / "master_timeline.json"
            
            sync_data = {
                'master_timeline': master_timeline,
                'sync_config': {
                    'symbols': symbols,
                    'timeframes': timeframes,
                    'current_cycle': 0,
                    'total_cycles': len(master_timeline['timestamps']),
                    'sync_enabled': True
                },
                'created_at': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            with open(sync_file_path, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Archivo de sincronización creado: {sync_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando archivo: {e}")
            return False
    
    def _generate_report(self, master_timeline: Dict[str, Any], symbols: List[str], timeframes: List[str]) -> str:
        """Genera reporte de sincronización"""
        try:
            total_points = master_timeline['total_points']
            start_date = master_timeline['start_date'][:10]
            end_date = master_timeline['end_date'][:10]
            
            # Estadísticas por símbolo
            symbol_stats = []
            for symbol in symbols:
                symbol_info = master_timeline['symbol_data_info'].get(symbol, {})
                symbol_count = symbol_info.get('count', 0)
                symbol_stats.append(f"• {symbol}: {symbol_count:,} timestamps")
            
            report = f"""
🔄 <b>Reporte de Sincronización de Timestamps</b>

📊 <b>Timeline Maestro:</b>
• Puntos de sincronización: {total_points:,}
• Período: {start_date} → {end_date}

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
            logger.error(f"❌ Error generando reporte: {e}")
            return f"❌ Error generando reporte: {e}"

async def main():
    """Entrada principal"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress_id", required=True, help="ID para progreso")
    args = parser.parse_args()
    
    script = SyncSymbolsSimple(progress_id=args.progress_id)
    try:
        result = await script.execute()
        
        # Retornar JSON a stdout
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") != "success":
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        error_result = {"status": "error", "message": str(e)}
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
