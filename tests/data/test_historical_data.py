#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_historical_data.py - SCRIPT DE PRUEBA PARA DATOS HISTÓRICOS
Script para probar la funcionalidad de verificación y descarga de datos históricos
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

async def test_historical_data_system():
    """Prueba el sistema de datos históricos"""
    print("🚀 Iniciando prueba del sistema de datos históricos...")
    
    try:
        # Importar el gestor de datos históricos
        from core.data.historical_data_manager import (
            ensure_historical_data_coverage,
            get_historical_data_report,
            quick_data_check
        )
        
        print("✅ Módulos importados correctamente")
        
        # 1. Verificación rápida
        print("\n🔍 Ejecutando verificación rápida...")
        is_ok = await quick_data_check()
        print(f"   Resultado: {'✅ OK' if is_ok else '⚠️ Necesita datos'}")
        
        # 2. Verificación completa
        print("\n📊 Ejecutando verificación completa...")
        results = await ensure_historical_data_coverage()
        
        status = results.get('status', 'unknown')
        message = results.get('message', 'Sin mensaje')
        
        print(f"   Estado: {status}")
        print(f"   Mensaje: {message}")
        
        if status == 'completed':
            download_results = results.get('download_results', {})
            total_downloaded = download_results.get('total_downloaded', 0)
            print(f"   Registros descargados: {total_downloaded:,}")
        
        # 3. Reporte detallado
        print("\n📋 Generando reporte detallado...")
        report = await get_historical_data_report()
        
        if 'error' in report:
            print(f"   ❌ Error: {report['error']}")
        else:
            config = report.get('configuration', {})
            coverage = report.get('coverage_analysis', {})
            summary = coverage.get('summary', {})
            
            print(f"   Años requeridos: {config.get('years_required', 'N/A')}")
            print(f"   Símbolos configurados: {config.get('symbols_configured', 'N/A')}")
            print(f"   Cobertura: {summary.get('coverage_percentage', 0):.1f}%")
            
            # Mostrar recomendaciones
            recommendations = report.get('recommendations', [])
            if recommendations:
                print("   Recomendaciones:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"     {i}. {rec}")
        
        print("\n✅ Prueba completada exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_script_execution():
    """Prueba la ejecución del script standalone"""
    print("\n🔧 Probando script standalone...")
    
    try:
        import subprocess
        import sys
        
        # Ejecutar el script de verificación
        result = subprocess.run([
            sys.executable, 
            'scripts/data/ensure_historical_data.py', 
            '--quick-check'
        ], capture_output=True, text=True, timeout=30)
        
        print(f"   Código de salida: {result.returncode}")
        print(f"   Salida: {result.stdout[:200]}...")
        
        if result.stderr:
            print(f"   Errores: {result.stderr[:200]}...")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"   ❌ Error ejecutando script: {e}")
        return False

async def main():
    """Función principal de prueba"""
    print("=" * 80)
    print("🧪 PRUEBA DEL SISTEMA DE DATOS HISTÓRICOS")
    print("=" * 80)
    
    # Prueba 1: Sistema de datos históricos
    test1_success = await test_historical_data_system()
    
    # Prueba 2: Script standalone
    test2_success = await test_script_execution()
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 80)
    print(f"✅ Sistema de datos históricos: {'PASÓ' if test1_success else 'FALLÓ'}")
    print(f"✅ Script standalone: {'PASÓ' if test2_success else 'FALLÓ'}")
    
    if test1_success and test2_success:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        return 0
    else:
        print("\n⚠️ Algunas pruebas fallaron")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
