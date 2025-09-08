#!/usr/bin/env python3
"""
app_enterprise.py - Punto de Entrada Enterprise del Trading Bot v10
===============================================================

SISTEMA ENTERPRISE COMPLETO CON ML AVANZADO

Uso: python app_enterprise.py [--mode MODE] [--duration DURATION] [--headless]

Modos disponibles:
- train: Entrenamiento enterprise con ML avanzado
- monitor: Monitoreo en tiempo real
- deploy: Despliegue de modelos
- analyze: Análisis de performance
- config: Configuración del sistema

Características Enterprise:
- Distributed training con PyTorch Lightning
- MLflow para experiment tracking
- Prometheus/Grafana para monitoreo
- Hyperparameter tuning con Optuna
- Fault tolerance y graceful shutdown
- Security y compliance features
- Testing exhaustivo
- CI/CD pipeline

"""

import asyncio
import os
import sys
import logging
import argparse
import signal
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Añadir directorio del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configurar logging enterprise
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseTradingBot:
    """Sistema Enterprise del Trading Bot v10"""
    
    def __init__(self):
        self.running = True
        self.config = self.load_enterprise_config()
        self.setup_signal_handlers()
        
    def load_enterprise_config(self) -> Dict[str, Any]:
        """Cargar configuración enterprise"""
        try:
            from core.enterprise_config import EnterpriseConfigManager
            config_manager = EnterpriseConfigManager()
            return config_manager.get_config()
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración enterprise: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'training': {
                'duration': 3600,  # 1 hora por defecto
                'checkpoint_interval': 600,  # 10 minutos
                'max_epochs': 100,
                'batch_size': 32,
                'learning_rate': 0.001
            },
            'monitoring': {
                'prometheus_port': 9090,
                'grafana_port': 3000,
                'dashboard_port': 8050
            },
            'security': {
                'encryption_enabled': True,
                'audit_logging': True,
                'compliance_mode': True
            }
        }
    
    def setup_signal_handlers(self):
        """Configurar manejo de señales para shutdown graceful"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Manejar señales del sistema"""
        logger.info(f"Recibida señal {signum}, iniciando shutdown graceful...")
        self.running = False
    
    def show_banner(self):
        """Mostrar banner enterprise"""
        print("\n" + "="*80)
        print("🚀 TRADING BOT v10 - ENTERPRISE EDITION")
        print("="*80)
        print("🏢 Sistema Enterprise con ML Avanzado")
        print("⚡ Distributed Training | 🔍 MLflow | 📊 Prometheus/Grafana")
        print("🛡️ Security & Compliance | 🧪 Testing Exhaustivo")
        print("="*80)
    
    def show_menu(self):
        """Mostrar menú enterprise"""
        print("\n📋 MENÚ ENTERPRISE:")
        print("1. 🚀 Entrenamiento Enterprise (1 hora)")
        print("2. ⚡ Entrenamiento Rápido (15 min)")
        print("3. 📊 Monitoreo en Tiempo Real")
        print("4. 🔧 Configuración del Sistema")
        print("5. 📈 Análisis de Performance")
        print("6. 🚀 Despliegue de Modelos")
        print("7. 🧪 Testing Suite")
        print("8. 📊 Dashboard Web")
        print("9. 🔍 Logs y Debugging")
        print("0. 🚪 Salir")
        print("-" * 50)
    
    async def run_training_enterprise(self, duration: int = 3600):
        """Ejecutar entrenamiento enterprise"""
        try:
            logger.info(f"🚀 Iniciando entrenamiento enterprise de {duration} segundos...")
            
            # Importar sistema enterprise de entrenamiento
            from models.enterprise.training_engine import EnterpriseTrainingEngine
            from models.enterprise.monitoring_system import EnterpriseMonitoringSystem
            
            # Inicializar sistemas
            training_engine = EnterpriseTrainingEngine()
            monitoring_system = EnterpriseMonitoringSystem()
            
            # Configurar monitoreo
            await monitoring_system.start()
            
            # Ejecutar entrenamiento
            results = await training_engine.train(
                duration=duration,
                config=self.config['training']
            )
            
            logger.info(f"✅ Entrenamiento completado: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento enterprise: {e}")
            raise
    
    async def run_quick_training(self):
        """Ejecutar entrenamiento rápido"""
        try:
            logger.info("⚡ Iniciando entrenamiento rápido...")
            
            # Usar el sistema enterprise pero con configuración rápida
            from models.enterprise.training_engine import EnterpriseTrainingEngine
            
            training_engine = EnterpriseTrainingEngine()
            quick_config = {
                'duration': 900,  # 15 minutos
                'max_epochs': 20,
                'batch_size': 64,
                'learning_rate': 0.01
            }
            
            results = await training_engine.train(
                duration=quick_config['duration'],
                config=quick_config
            )
            
            logger.info(f"✅ Entrenamiento rápido completado: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento rápido: {e}")
            raise
    
    async def start_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        try:
            logger.info("📊 Iniciando monitoreo enterprise...")
            
            from models.enterprise.monitoring_system import EnterpriseMonitoringSystem
            
            monitoring = EnterpriseMonitoringSystem()
            await monitoring.start()
            
            # Mantener corriendo
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
            raise
    
    async def run_analysis(self):
        """Ejecutar análisis de performance"""
        try:
            logger.info("📈 Iniciando análisis de performance...")
            
            from models.enterprise.analysis_engine import EnterpriseAnalysisEngine
            
            analysis_engine = EnterpriseAnalysisEngine()
            results = await analysis_engine.analyze_performance()
            
            logger.info(f"✅ Análisis completado: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            raise
    
    async def run_testing_suite(self):
        """Ejecutar suite de testing"""
        try:
            logger.info("🧪 Iniciando testing suite...")
            
            import subprocess
            result = subprocess.run(['pytest', 'tests/', '-v', '--cov=models/enterprise'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Todos los tests pasaron")
            else:
                logger.error(f"❌ Tests fallaron: {result.stderr}")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"❌ Error en testing: {e}")
            raise
    
    def show_config(self):
        """Mostrar configuración actual"""
        print("\n🔧 CONFIGURACIÓN ENTERPRISE:")
        print(f"⏱️  Duración de entrenamiento: {self.config['training']['duration']}s")
        print(f"💾 Intervalo de checkpoints: {self.config['training']['checkpoint_interval']}s")
        print(f"🎯 Máximo de epochs: {self.config['training']['max_epochs']}")
        print(f"📦 Batch size: {self.config['training']['batch_size']}")
        print(f"📚 Learning rate: {self.config['training']['learning_rate']}")
        print(f"🔒 Encryption: {self.config['security']['encryption_enabled']}")
        print(f"📝 Audit logging: {self.config['security']['audit_logging']}")
    
    async def start_dashboard(self):
        """Iniciar dashboard web"""
        try:
            logger.info("📊 Iniciando dashboard web...")
            
            import subprocess
            import threading
            
            def run_dashboard():
                subprocess.run(['python', 'monitoring/main_dashboard.py'])
            
            # Ejecutar en hilo separado
            dashboard_thread = threading.Thread(target=run_dashboard)
            dashboard_thread.daemon = True
            dashboard_thread.start()
            
            logger.info("✅ Dashboard iniciado en http://localhost:8050")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando dashboard: {e}")
            raise
    
    async def show_logs(self):
        """Mostrar logs recientes"""
        try:
            log_file = 'logs/enterprise_app.log'
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print("\n📝 ÚLTIMOS LOGS:")
                    print("-" * 50)
                    for line in lines[-20:]:  # Últimas 20 líneas
                        print(line.strip())
            else:
                print("❌ No se encontraron logs")
                
        except Exception as e:
            logger.error(f"❌ Error leyendo logs: {e}")
    
    async def run_interactive_mode(self):
        """Modo interactivo"""
        self.show_banner()
        
        while self.running:
            try:
                self.show_menu()
                choice = input("\n🎯 Selecciona una opción: ").strip()
                
                if choice == '1':
                    duration = input("⏱️  Duración en segundos (3600 para 1 hora): ").strip()
                    duration = int(duration) if duration else 3600
                    await self.run_training_enterprise(duration)
                    
                elif choice == '2':
                    await self.run_quick_training()
                    
                elif choice == '3':
                    await self.start_monitoring()
                    
                elif choice == '4':
                    self.show_config()
                    
                elif choice == '5':
                    await self.run_analysis()
                    
                elif choice == '6':
                    logger.info("🚀 Despliegue de modelos...")
                    # Implementar despliegue
                    
                elif choice == '7':
                    await self.run_testing_suite()
                    
                elif choice == '8':
                    await self.start_dashboard()
                    
                elif choice == '9':
                    await self.show_logs()
                    
                elif choice == '0':
                    logger.info("👋 Saliendo del sistema enterprise...")
                    break
                    
                else:
                    print("❌ Opción inválida")
                    
            except KeyboardInterrupt:
                logger.info("👋 Interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
    
    async def run_headless_mode(self, mode: str, duration: int = 3600):
        """Modo headless para automatización"""
        try:
            logger.info(f"🤖 Iniciando modo headless: {mode}")
            
            if mode == 'train':
                await self.run_training_enterprise(duration)
            elif mode == 'quick':
                await self.run_quick_training()
            elif mode == 'monitor':
                await self.start_monitoring()
            elif mode == 'analyze':
                await self.run_analysis()
            elif mode == 'test':
                await self.run_testing_suite()
            else:
                raise ValueError(f"Modo no válido: {mode}")
                
            logger.info("✅ Modo headless completado")
            
        except Exception as e:
            logger.error(f"❌ Error en modo headless: {e}")
            raise

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Trading Bot v10 Enterprise')
    parser.add_argument('--mode', choices=['train', 'quick', 'monitor', 'analyze', 'test'], 
                       help='Modo de ejecución')
    parser.add_argument('--duration', type=int, default=3600, 
                       help='Duración en segundos (solo para modo train)')
    parser.add_argument('--headless', action='store_true', 
                       help='Modo headless (sin interfaz)')
    
    args = parser.parse_args()
    
    # Crear directorios necesarios
    os.makedirs('logs', exist_ok=True)
    os.makedirs('checkpoints', exist_ok=True)
    os.makedirs('models/enterprise', exist_ok=True)
    
    # Inicializar sistema enterprise
    bot = EnterpriseTradingBot()
    
    try:
        if args.headless and args.mode:
            # Modo headless
            await bot.run_headless_mode(args.mode, args.duration)
        else:
            # Modo interactivo
            await bot.run_interactive_mode()
            
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        logger.info("🏁 Sistema enterprise finalizado")

if __name__ == "__main__":
    asyncio.run(main())
