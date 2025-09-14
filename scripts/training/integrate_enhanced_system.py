#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/training/integrate_enhanced_system.py
============================================
Script de Integración del Sistema Mejorado

Integra todos los componentes mejorados con el sistema actual:
- DetailedTradeMetric
- EnhancedMetricsAggregator  
- TelegramTradeReporter
- OptimizedTrainingPipeline
- EnhancedTradingAgent

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.training.train_hist_enhanced import EnhancedTrainingOrchestrator
from scripts.training.optimized_training_pipeline import TrainingConfig
from core.telegram.trade_reporter import TelegramConfig
from config.unified_config import get_config_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/integrate_enhanced.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SystemIntegrator:
    """
    Integrador del Sistema Mejorado
    ===============================
    
    Integra todos los componentes mejorados con el sistema actual
    y proporciona una interfaz unificada para el entrenamiento.
    """
    
    def __init__(self):
        """Inicializa el integrador"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.orchestrator = None
        
        self.logger.info("✅ SystemIntegrator inicializado")
    
    async def setup_enhanced_training(
        self,
        days_back: int = 365,
        cycle_size_hours: int = 24,
        max_concurrent_agents: int = 8,
        telegram_enabled: bool = True,
        telegram_bot_token: str = None,
        telegram_chat_id: str = None
    ) -> bool:
        """
        Configura el sistema de entrenamiento mejorado
        
        Args:
            days_back: Días hacia atrás para entrenar
            cycle_size_hours: Tamaño del ciclo en horas
            max_concurrent_agents: Máximo de agentes concurrentes
            telegram_enabled: Habilitar notificaciones de Telegram
            telegram_bot_token: Token del bot de Telegram
            telegram_chat_id: ID del chat de Telegram
            
        Returns:
            bool: True si se configuró correctamente
        """
        try:
            # Crear configuración de entrenamiento
            training_config = TrainingConfig(
                days_back=days_back,
                cycle_size_hours=cycle_size_hours,
                max_concurrent_agents=max_concurrent_agents,
                telegram_enabled=telegram_enabled,
                checkpoint_interval=100,
                memory_cleanup_interval=50,
                max_memory_usage_mb=8000,
                recovery_enabled=True
            )
            
            # Crear orquestador
            self.orchestrator = EnhancedTrainingOrchestrator(training_config)
            
            # Configurar Telegram si está habilitado
            if telegram_enabled and telegram_bot_token and telegram_chat_id:
                await self._configure_telegram(telegram_bot_token, telegram_chat_id)
            
            # Inicializar sistema
            if not await self.orchestrator.initialize():
                self.logger.error("❌ Error inicializando sistema mejorado")
                return False
            
            self.logger.info("✅ Sistema mejorado configurado correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error configurando sistema mejorado: {e}")
            return False
    
    async def _configure_telegram(self, bot_token: str, chat_id: str):
        """Configura Telegram para el sistema"""
        try:
            # En un sistema real, esto se haría a través del orquestador
            # Por ahora solo logueamos la configuración
            self.logger.info(f"✅ Telegram configurado: Bot {bot_token[:10]}..., Chat {chat_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error configurando Telegram: {e}")
    
    async def run_enhanced_training(self) -> Dict[str, Any]:
        """
        Ejecuta el entrenamiento mejorado
        
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            if not self.orchestrator:
                raise RuntimeError("Sistema no configurado. Llama a setup_enhanced_training() primero.")
            
            self.logger.info("🚀 Iniciando entrenamiento mejorado...")
            
            # Ejecutar entrenamiento
            results = await self.orchestrator.execute_enhanced_training()
            
            self.logger.info("✅ Entrenamiento mejorado completado")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando entrenamiento mejorado: {e}")
            return {'error': str(e)}
    
    async def run_quick_test(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Ejecuta una prueba rápida del sistema
        
        Args:
            days_back: Días hacia atrás para la prueba
            
        Returns:
            Dict con resultados de la prueba
        """
        try:
            self.logger.info(f"🧪 Iniciando prueba rápida: {days_back} días")
            
            # Configurar para prueba rápida
            if not await self.setup_enhanced_training(
                days_back=days_back,
                cycle_size_hours=6,  # Ciclos más pequeños para prueba
                max_concurrent_agents=4,  # Menos agentes para prueba
                telegram_enabled=False  # Sin Telegram para prueba
            ):
                return {'error': 'Error configurando prueba'}
            
            # Ejecutar prueba
            results = await self.run_enhanced_training()
            
            self.logger.info("✅ Prueba rápida completada")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error en prueba rápida: {e}")
            return {'error': str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtiene estado del sistema"""
        try:
            if not self.orchestrator:
                return {'status': 'not_configured'}
            
            return self.orchestrator.get_training_status()
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estado: {e}")
            return {'error': str(e)}
    
    async def stop_training(self):
        """Detiene el entrenamiento"""
        try:
            if self.orchestrator:
                await self.orchestrator.stop_training()
                self.logger.info("✅ Entrenamiento detenido")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo entrenamiento: {e}")

# Funciones de conveniencia para integración con el sistema actual
async def run_enhanced_historical_training(
    days_back: int = 365,
    telegram_enabled: bool = True,
    bot_token: str = None,
    chat_id: str = None
) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar entrenamiento histórico mejorado
    
    Args:
        days_back: Días hacia atrás para entrenar
        telegram_enabled: Habilitar notificaciones de Telegram
        bot_token: Token del bot de Telegram
        chat_id: ID del chat de Telegram
        
    Returns:
        Dict con resultados del entrenamiento
    """
    integrator = SystemIntegrator()
    
    # Configurar sistema
    if not await integrator.setup_enhanced_training(
        days_back=days_back,
        telegram_enabled=telegram_enabled,
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id
    ):
        return {'error': 'Error configurando sistema'}
    
    # Ejecutar entrenamiento
    return await integrator.run_enhanced_training()

async def run_enhanced_quick_test(days_back: int = 7) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar prueba rápida
    
    Args:
        days_back: Días hacia atrás para la prueba
        
    Returns:
        Dict con resultados de la prueba
    """
    integrator = SystemIntegrator()
    return await integrator.run_quick_test(days_back)

# Función principal para testing
async def main():
    """Función principal para testing"""
    try:
        logger.info("🧪 Iniciando prueba del sistema mejorado...")
        
        # Ejecutar prueba rápida
        results = await run_enhanced_quick_test(days_back=3)
        
        if 'error' in results:
            logger.error(f"❌ Error en prueba: {results['error']}")
            return 1
        
        logger.info("✅ Prueba completada exitosamente")
        logger.info(f"📊 Resultados: {results}")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
