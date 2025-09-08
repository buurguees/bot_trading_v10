#!/usr/bin/env python3
"""
test_robust_systems.py - Prueba de Sistemas Robustos
Script para verificar que todos los sistemas robustos funcionan correctamente
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Agregar el directorio raíz al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Importar sistemas robustos
from core.health_checker import health_checker, check_system_health
from core.config_manager import config_manager, get_config
from core.error_handler import error_handler, log_error, get_error_stats
from core.thread_manager import thread_manager, get_thread_stats

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_health_checker():
    """Prueba el sistema de health checks"""
    print("\n🔍 PROBANDO HEALTH CHECKER...")
    print("=" * 50)
    
    try:
        # Ejecutar health checks
        health_results = await health_checker.run_all_checks()
        system_status = health_checker.get_system_status(health_results)
        
        print(f"Estado general del sistema: {'✅ SALUDABLE' if system_status['system_ready'] else '❌ NO SALUDABLE'}")
        print(f"Checks totales: {system_status['total_checks']}")
        print(f"Checks exitosos: {system_status['passed_checks']}")
        print(f"Checks fallidos: {system_status['failed_checks']}")
        
        if system_status['critical_failures']:
            print(f"Fallos críticos: {system_status['critical_failures']}")
        
        # Mostrar detalles de cada check
        for check_name, result in health_results.items():
            status_icon = "✅" if result.status else "❌"
            print(f"  {status_icon} {check_name}: {result.message}")
            if result.details:
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
        
        return system_status['system_ready']
        
    except Exception as e:
        print(f"❌ Error en health checker: {e}")
        return False

def test_config_manager():
    """Prueba el sistema de configuración"""
    print("\n⚙️ PROBANDO CONFIG MANAGER...")
    print("=" * 50)
    
    try:
        # Cargar configuración
        config = get_config()
        
        print(f"Entorno: {config.environment}")
        print(f"Debug: {config.debug}")
        print(f"Log level: {config.log_level}")
        print(f"Símbolos: {config.symbols}")
        print(f"Timeframes: {config.timeframes}")
        print(f"Paper trading: {config.paper_trading}")
        print(f"Dashboard: {config.dashboard_host}:{config.dashboard_port}")
        
        # Validar configuración
        errors = config.validate()
        if errors:
            print(f"❌ Errores de validación: {errors}")
            return False
        else:
            print("✅ Configuración válida")
            return True
        
    except Exception as e:
        print(f"❌ Error en config manager: {e}")
        return False

def test_error_handler():
    """Prueba el sistema de manejo de errores"""
    print("\n🚨 PROBANDO ERROR HANDLER...")
    print("=" * 50)
    
    try:
        # Probar diferentes tipos de errores
        test_errors = [
            ValueError("Error de validación de prueba"),
            RuntimeError("Error de runtime de prueba"),
            ConnectionError("Error de conexión de prueba")
        ]
        
        for error in test_errors:
            context = log_error(error, {"test": True, "timestamp": datetime.now().isoformat()})
            print(f"  Error registrado: {context.error_type} - {context.message}")
        
        # Obtener estadísticas
        stats = get_error_stats()
        print(f"Total errores registrados: {stats['total_errors']}")
        print(f"Errores recientes: {stats['recent_errors']}")
        
        if stats['severity_counts']:
            print("Conteo por severidad:")
            for severity, count in stats['severity_counts'].items():
                print(f"  {severity}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en error handler: {e}")
        return False

def test_thread_manager():
    """Prueba el sistema de threading"""
    print("\n🧵 PROBANDO THREAD MANAGER...")
    print("=" * 50)
    
    try:
        # Iniciar thread manager
        thread_manager.start()
        
        # Función de prueba
        def test_function(name, delay=1):
            import time
            time.sleep(delay)
            return f"Task {name} completed"
        
        # Enviar tareas de prueba
        task_ids = []
        for i in range(3):
            task_id = thread_manager.submit_task(
                name=f"test_task_{i}",
                function=test_function,
                f"test_{i}",
                delay=0.5
            )
            task_ids.append(task_id)
            print(f"  Tarea {i} enviada: {task_id}")
        
        # Esperar a que terminen las tareas
        import time
        time.sleep(2)
        
        # Verificar resultados
        for i, task_id in enumerate(task_ids):
            status = thread_manager.get_task_status(task_id)
            result = thread_manager.get_task_result(task_id)
            print(f"  Tarea {i}: {status} - {result}")
        
        # Obtener estadísticas
        stats = get_thread_stats()
        print(f"Tareas activas: {stats['active_tasks']}")
        print(f"Tareas completadas: {stats['completed_tasks']}")
        print(f"Tiempo promedio de ejecución: {stats['average_execution_time']}s")
        
        # Detener thread manager
        thread_manager.shutdown()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en thread manager: {e}")
        return False

async def test_integration():
    """Prueba de integración de todos los sistemas"""
    print("\n🔗 PROBANDO INTEGRACIÓN...")
    print("=" * 50)
    
    try:
        # Verificar que todos los sistemas estén funcionando
        health_ok = await test_health_checker()
        config_ok = test_config_manager()
        error_ok = test_error_handler()
        thread_ok = test_thread_manager()
        
        all_systems_ok = all([health_ok, config_ok, error_ok, thread_ok])
        
        print(f"\n📊 RESUMEN DE PRUEBAS:")
        print(f"  Health Checker: {'✅' if health_ok else '❌'}")
        print(f"  Config Manager: {'✅' if config_ok else '❌'}")
        print(f"  Error Handler: {'✅' if error_ok else '❌'}")
        print(f"  Thread Manager: {'✅' if thread_ok else '❌'}")
        print(f"  INTEGRACIÓN: {'✅ TODOS LOS SISTEMAS OK' if all_systems_ok else '❌ ALGUNOS SISTEMAS FALLARON'}")
        
        return all_systems_ok
        
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        return False

async def main():
    """Función principal de prueba"""
    print("🚀 INICIANDO PRUEBAS DE SISTEMAS ROBUSTOS")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Directorio: {project_root}")
    print()
    
    try:
        # Ejecutar todas las pruebas
        success = await test_integration()
        
        if success:
            print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
            print("El sistema robusto está funcionando correctamente.")
        else:
            print("\n⚠️ ALGUNAS PRUEBAS FALLARON")
            print("Revisar los logs para más detalles.")
        
        return success
        
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO EN LAS PRUEBAS: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
