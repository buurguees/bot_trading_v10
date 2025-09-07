#!/usr/bin/env python3
"""
Script para Eliminar TESTUSDT - Trading Bot v10
==============================================

Elimina todos los datos de TESTUSDT de la base de datos ya que son solo datos de prueba.

Uso: python scripts/eliminar_testusdt.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import db_manager
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def eliminar_testusdt():
    """Elimina todos los datos de TESTUSDT de la base de datos"""
    print("🗑️ ELIMINANDO DATOS DE TESTUSDT - TRADING BOT v10")
    print("=" * 55)
    print("⚠️  ADVERTENCIA: Se eliminarán TODOS los datos de TESTUSDT")
    print()
    
    try:
        # Verificar datos existentes de TESTUSDT
        print("🔍 Verificando datos existentes de TESTUSDT...")
        
        # Contar registros antes de eliminar usando conexión directa
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            count_query = "SELECT COUNT(*) as count FROM market_data WHERE symbol = 'TESTUSDT'"
            cursor.execute(count_query)
            count_before = cursor.fetchone()[0]
            print(f"📊 Registros de TESTUSDT encontrados: {count_before}")
            
            if count_before == 0:
                print("✅ No hay datos de TESTUSDT para eliminar")
                return
            
            # Confirmar eliminación
            confirm = input(f"\n¿Eliminar {count_before} registros de TESTUSDT? (s/N): ").strip().lower()
            
            if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
                print("❌ Eliminación cancelada por el usuario")
                return
            
            # Eliminar datos de TESTUSDT
            print("\n🗑️ Eliminando datos de TESTUSDT...")
            
            delete_query = "DELETE FROM market_data WHERE symbol = 'TESTUSDT'"
            cursor.execute(delete_query)
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            print(f"✅ Eliminados {deleted_count} registros de TESTUSDT")
            
            # Verificar eliminación
            print("\n🔍 Verificando eliminación...")
            cursor.execute(count_query)
            count_after = cursor.fetchone()[0]
            
            if count_after == 0:
                print("✅ TESTUSDT eliminado completamente")
            else:
                print(f"⚠️ Quedan {count_after} registros de TESTUSDT")
        
        # Mostrar resumen final
        print("\n📊 RESUMEN FINAL")
        print("=" * 20)
        print(f"✅ Registros eliminados: {deleted_count}")
        print(f"📈 Base de datos limpia de datos de prueba")
            
    except Exception as e:
        print(f"❌ Error eliminando TESTUSDT: {e}")
        logger.error(f"Error eliminando TESTUSDT: {e}")

def verificar_estado_final():
    """Verifica el estado final de la base de datos"""
    print("\n🔍 VERIFICACIÓN FINAL DE LA BASE DE DATOS")
    print("=" * 45)
    
    try:
        # Obtener resumen de todos los símbolos
        summary_query = """
        SELECT 
            symbol,
            COUNT(*) as count,
            MIN(timestamp) as start_ts,
            MAX(timestamp) as end_ts
        FROM market_data 
        GROUP BY symbol
        ORDER BY symbol
        """
        
        # Usar conexión directa para la consulta
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(summary_query)
            results = cursor.fetchall()
            
            if results:
                print("📊 Símbolos en la base de datos:")
                print("-" * 40)
                
                total_records = 0
                testusdt_found = False
                
                for row in results:
                    symbol = row[0]
                    count = row[1]
                    start_date = row[2]
                    end_date = row[3]
                    
                    # Convertir timestamps a fechas legibles
                    from datetime import datetime
                    start_str = datetime.fromtimestamp(start_date).strftime('%Y-%m-%d %H:%M')
                    end_str = datetime.fromtimestamp(end_date).strftime('%Y-%m-%d %H:%M')
                    
                    print(f"📈 {symbol}:")
                    print(f"   📊 Registros: {count:,}")
                    print(f"   📅 Desde: {start_str}")
                    print(f"   📅 Hasta: {end_str}")
                    print()
                    
                    total_records += count
                    
                    if symbol == 'TESTUSDT':
                        testusdt_found = True
                
                print(f"📊 TOTAL: {total_records:,} registros")
                
                # Verificar que TESTUSDT no esté presente
                if not testusdt_found:
                    print("✅ TESTUSDT eliminado exitosamente")
                else:
                    print("⚠️ TESTUSDT aún presente en la base de datos")
                    
            else:
                print("❌ Error obteniendo resumen de la base de datos")
            
    except Exception as e:
        print(f"❌ Error en verificación final: {e}")

def main():
    """Función principal"""
    try:
        eliminar_testusdt()
        verificar_estado_final()
        
        print("\n🎉 PROCESO COMPLETADO")
        print("La base de datos está limpia de datos de prueba")
        
    except KeyboardInterrupt:
        print("\n⏹️ Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
