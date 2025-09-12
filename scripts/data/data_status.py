#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para /data_status - Enterprise: Estado detallado de DB y archivos.
Llama core/data/database.py y core/data/historical_data_manager.py.
Retorna JSON para handlers.py.
"""

import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Path al root PRIMERO
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Cargar .env
load_dotenv()

# Ahora importar módulos locales
from core.config.config_loader import ConfigLoader

# Logging enterprise
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_status.log', encoding='utf-8'), 
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Ejecución enterprise"""
    try:
        from core.data.database import db_manager
        from core.data.historical_data_manager import HistoricalDataManager
        from core.config.config_loader import ConfigLoader
        
        # Usar UnifiedConfigManager v2
        from config.unified_config import get_config_manager
        config_manager = get_config_manager()
        
        symbols = config_manager.get_symbols()
        timeframes = config_manager.get_timeframes()
        
        manager = HistoricalDataManager()
        total_records = 0
        status_by_symbol = {}
        
        for symbol in symbols:
            sym_status = {}
            # Obtener conteo total por símbolo
            total_count = db_manager.get_market_data_count_fast(symbol)
            
            # Distribuir entre timeframes (aproximado)
            count_per_tf = total_count // len(timeframes) if timeframes else 0
            
            for tf in timeframes:
                status_icon = "✅" if count_per_tf > 0 else "❌"
                sym_status[tf] = {"count": count_per_tf, "status": status_icon}
                total_records += count_per_tf
            
            status_by_symbol[symbol] = sym_status
        
        # Última sync via DB
        latest_session = db_manager.get_latest_sync_session()
        
        report_lines = [f"📊 <b>Estado Enterprise de Datos</b>\n\n<b>Config:</b>\n• Símbolos: {', '.join(symbols)}\n• TFs: {', '.join(timeframes)}\n\n<b>Total Registros:</b> {total_records:,}"]
        
        for symbol, sym_status in status_by_symbol.items():
            report_lines.append(f"\n<b>{symbol}:</b>")
            for tf, data in sym_status.items():
                report_lines.append(f"• {tf}: {data['count']:,} {data['status']}")
        
        if latest_session:
            report_lines.append(f"\n<b>Última Sync:</b> {latest_session}")
        else:
            report_lines.append("\n<b>Sync:</b> No disponible")
        
        status = "✅ Datos OK" if total_records > 0 else "⚠️ Sin datos - Use /download_data"
        report_lines.append(f"\n<b>Estado:</b> {status}")
        
        full_report = "\n".join(report_lines)
        
        result = {
            "status": "success",
            "report": full_report,  # Texto HTML simple
            "total_records": total_records,
            "symbols_status": status_by_symbol
        }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        logger.info("✅ Estado de datos generado")
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        result = {"status": "error", "message": str(e)}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()