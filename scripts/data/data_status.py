#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /data_status
Estado detallado de los datos
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data.database import db_manager
from config.config_loader import ConfigLoader

def main():
    """Función principal"""
    try:
        # Cargar configuración
        config_loader = ConfigLoader("config/user_settings.yaml")
        config = config_loader.load_config()
        
        # Obtener símbolos y timeframes
        symbols = config.get("trading_settings", {}).get("timeframes", {}).get("symbols", [])
        timeframes = config.get("trading_settings", {}).get("timeframes", {}).get("timeframes", [])
        
        # Verificar estado de datos por símbolo y timeframe
        report = f"""
📊 <b>Estado Detallado de Datos</b>

<b>🔧 Configuración:</b>
• Símbolos: {', '.join(symbols)}
• Timeframes: {', '.join(timeframes)}

<b>📈 Datos por Símbolo y Timeframe:</b>
"""
        
        total_records = 0
        for symbol in symbols:
            report += f"\n<b>{symbol}:</b>\n"
            for timeframe in timeframes:
                count = db_manager.get_market_data_count_fast(symbol)
                status_icon = "✅" if count > 0 else "❌"
                report += f"  • {timeframe}: {count:,} registros {status_icon}\n"
                total_records += count
        
        report += f"\n<b>📊 Total de registros:</b> {total_records:,}\n"
        
        # Verificar datos sincronizados
        latest_session = db_manager.get_latest_sync_session()
        if latest_session:
            report += f"\n<b>🔄 Última sincronización:</b> {latest_session}\n"
        else:
            report += f"\n<b>🔄 Sincronización:</b> No disponible\n"
        
        if total_records > 0:
            report += "\n✅ <b>Estado:</b> Datos disponibles"
        else:
            report += "\n⚠️ <b>Estado:</b> Sin datos - Ejecute /download_data"
        
        print(report)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()