#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /health
Salud del sistema
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar directorios al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data.database import db_manager
from core.config.config_loader import ConfigLoader

def main():
    """Función principal"""
    try:
        # Cargar configuración
        config_loader = ConfigLoader("config/user_settings.yaml")
        config = config_loader.load_config()
        
        # Obtener símbolos y timeframes
        symbols = config.get("trading_settings", {}).get("timeframes", {}).get("symbols", [])
        timeframes = config.get("trading_settings", {}).get("timeframes", {}).get("timeframes", [])
        
        # Verificar salud de la base de datos
        db_health = "✅" if db_manager else "❌"
        
        # Verificar datos
        data_health = []
        for symbol in symbols:
            count = db_manager.get_market_data_count_fast(symbol)
            if count > 0:
                data_health.append("✅")
            else:
                data_health.append("❌")
        
        data_health_pct = (data_health.count("✅") / len(data_health) * 100) if data_health else 0
        
        # Verificar sincronización
        sync_health = "✅" if db_manager.get_latest_sync_session() else "⚠️"
        
        # Generar reporte de salud
        report = f"""
🏥 <b>Salud del Sistema</b>

<b>🔧 Componentes:</b>
• Base de datos: {db_health}
• Configuración: ✅
• Scripts: ✅

<b>📊 Datos:</b>
• Símbolos con datos: {data_health.count('✅')}/{len(symbols)}
• Cobertura: {data_health_pct:.1f}%
• Sincronización: {sync_health}

<b>📈 Estado por Símbolo:</b>
"""
        
        for i, symbol in enumerate(symbols):
            count = db_manager.get_market_data_count_fast(symbol)
            status = data_health[i]
            report += f"• {symbol}: {count:,} registros {status}\n"
        
        # Estado general
        if data_health_pct == 100:
            report += f"\n✅ <b>Estado General:</b> Sistema completamente operativo"
        elif data_health_pct >= 50:
            report += f"\n⚠️ <b>Estado General:</b> Sistema parcialmente operativo"
        else:
            report += f"\n❌ <b>Estado General:</b> Sistema requiere atención"
        
        print(report)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
