#!/usr/bin/env python3
"""
Script simple para /data_status - Estado de datos
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Path al root
root_path = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, root_path)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Estado simple de datos"""
    try:
        from core.data.database import db_manager
        from config.unified_config import get_config_manager
        
        cfg = get_config_manager()
        symbols = cfg.get_symbols()
        timeframes = cfg.get_timeframes() or ["1m", "5m", "15m", "1h", "4h"]
        
        report = {
            "status": "success",
            "data": {},
            "summary": {
                "total_symbols": len(symbols),
                "total_timeframes": len(timeframes),
                "total_records": 0
            }
        }
        
        for symbol in symbols:
            report["data"][symbol] = {}
            symbol_total = 0
            
            for tf in timeframes:
                try:
                    db_path = f"data/{symbol}/trading_bot.db"
                    if Path(db_path).exists():
                        with db_manager._get_connection(db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT COUNT(*) FROM market_data WHERE symbol = ? AND timeframe = ?",
                                (symbol, tf)
                            )
                            count = cursor.fetchone()[0]
                            symbol_total += count
                            
                            # Obtener rango de fechas
                            cursor.execute(
                                "SELECT MIN(timestamp), MAX(timestamp) FROM market_data WHERE symbol = ? AND timeframe = ?",
                                (symbol, tf)
                            )
                            min_ts, max_ts = cursor.fetchone()
                            
                            report["data"][symbol][tf] = {
                                "count": count,
                                "min_timestamp": min_ts,
                                "max_timestamp": max_ts,
                                "min_date": datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d %H:%M') if min_ts else None,
                                "max_date": datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M') if max_ts else None
                            }
                    else:
                        report["data"][symbol][tf] = {
                            "count": 0,
                            "min_timestamp": None,
                            "max_timestamp": None,
                            "min_date": None,
                            "max_date": None
                        }
                except Exception as e:
                    report["data"][symbol][tf] = {
                        "count": 0,
                        "error": str(e)
                    }
            
            report["summary"]["total_records"] += symbol_total
        
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()