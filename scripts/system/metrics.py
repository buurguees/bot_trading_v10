#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para el comando /metrics
Métricas detalladas del sistema
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
        
        # Calcular métricas
        total_records = 0
        symbol_metrics = {}
        
        for symbol in symbols:
            count = db_manager.get_market_data_count_fast(symbol)
            symbol_metrics[symbol] = count
            total_records += count
        
        # Verificar datos sincronizados
        latest_session = db_manager.get_latest_sync_session()
        
        # Generar reporte de métricas
        report = f"""
📊 <b>Métricas Detalladas del Sistema</b>

<b>🔧 Configuración:</b>
• Símbolos activos: {len(symbols)}
• Timeframes configurados: {len(timeframes)}
• Total de registros: {total_records:,}

<b>📈 Datos por Símbolo:</b>
"""
        
        for symbol, count in symbol_metrics.items():
            status_icon = "✅" if count > 0 else "❌"
            percentage = (count / total_records * 100) if total_records > 0 else 0
            report += f"• {symbol}: {count:,} registros ({percentage:.1f}%) {status_icon}\n"
        
        report += f"\n<b>🔄 Sincronización:</b>\n"
        if latest_session:
            report += f"• Última sesión: {latest_session}\n"
            report += f"• Estado: ✅ Datos sincronizados disponibles\n"
        else:
            report += f"• Estado: ⚠️ Sin datos sincronizados\n"
            report += f"• Acción: Ejecute /sync_symbols\n"
        
        report += f"\n<b>📊 Resumen:</b>\n"
        report += f"• Cobertura de datos: {(len([s for s in symbol_metrics.values() if s > 0]) / len(symbols) * 100):.1f}%\n"
        report += f"• Promedio de registros por símbolo: {total_records // len(symbols):,}\n"
        
        if total_records > 0:
            report += f"\n✅ <b>Estado:</b> Sistema operativo con datos"
        else:
            report += f"\n⚠️ <b>Estado:</b> Sistema sin datos - Ejecute /download_data"
        
        print(report)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
