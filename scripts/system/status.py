#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /status
Estado del sistema
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
        
        # Verificar estado de datos
        data_status = {}
        for symbol in symbols:
            count = db_manager.get_market_data_count_fast(symbol)
            data_status[symbol] = count
        
        # Generar reporte
        report = f"""
📊 <b>Estado del Sistema</b>

<b>🔧 Configuración:</b>
• Símbolos: {', '.join(symbols)}
• Timeframes: {', '.join(timeframes)}

<b>📈 Datos por Símbolo:</b>
"""
        
        for symbol, count in data_status.items():
            status_icon = "✅" if count > 0 else "❌"
            report += f"• {symbol}: {count:,} registros {status_icon}\n"
        
        total_records = sum(data_status.values())
        report += f"\n<b>📊 Total de registros:</b> {total_records:,}\n"
        
        if total_records > 0:
            report += "\n✅ <b>Estado:</b> Sistema operativo"
        else:
            report += "\n⚠️ <b>Estado:</b> Sin datos - Ejecute /download_data"
        
        print(report)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
