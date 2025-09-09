#!/usr/bin/env python3
"""
Script de Reparación de Datos Históricos - Trading Bot v10 Enterprise
====================================================================

Script para reparar y depurar datos históricos existentes.
Se ejecuta desde Telegram con el comando /repair_history.

Características:
- Pipeline completo de limpieza por archivo
- Eliminación de duplicados y corrección de orden
- Detección y relleno de gaps precisos
- Alineación temporal perfecta por símbolo
- Reportes detallados de alineación
- Resiliencia con backoff exponencial

Uso:
    python scripts/history/repair_history.py

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.data.repair_manager import RepairManager, RepairStatus

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/repair_history.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HistoryRepairer:
    """Reparador de datos históricos con mensajes en vivo"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el reparador"""
        self.repair_manager = RepairManager(config_path)
        self.telegram_bot = None
        self.chat_id = None
        self.is_running = False
        
        logger.info("🔧 Reparador de datos históricos inicializado")
    
    def set_telegram_bot(self, telegram_bot, chat_id: str):
        """Configura el bot de Telegram para mensajes"""
        self.telegram_bot = telegram_bot
        self.chat_id = chat_id
    
    async def repair_all_historical_data(self):
        """Repara todos los datos históricos"""
        try:
            self.is_running = True
            start_time = datetime.now()
            
            # Obtener símbolos y timeframes
            symbols, timeframes = self.repair_manager.list_symbols_and_tfs()
            total_tasks = len(symbols) * len(timeframes)
            
            # Inicializar estado
            self.status = RepairStatus(
                total_symbols=len(symbols),
                total_timeframes=len(timeframes),
                completed_tasks=0,
                current_symbol="",
                current_timeframe="",
                current_action="Iniciando...",
                progress_percentage=0.0,
                start_time=start_time,
                elapsed_time="00:00:00",
                current_stats=None,
                alignment_status="OK"
            )
            
            # Enviar mensaje inicial
            await self._send_initial_message()
            
            # Iniciar hilo de actualizaciones en vivo
            update_thread = threading.Thread(target=self._update_live_messages, daemon=True)
            update_thread.start()
            
            # Ejecutar reparación
            summary = self.repair_manager.repair_all_historical_data()
            
            # Enviar mensaje final
            await self._send_final_message(summary)
            
            logger.info("✅ Reparación de datos históricos completada")
            
        except Exception as e:
            logger.error(f"❌ Error en reparación de datos históricos: {e}")
            if self.telegram_bot and self.chat_id:
                await self.telegram_bot.send_message(f"❌ Error en reparación: {str(e)}", self.chat_id)
        finally:
            self.is_running = False
    
    async def _send_initial_message(self):
        """Envía mensaje inicial"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = """
🔧 <b>Iniciando Reparación de Datos Históricos</b>

• Pipeline completo de limpieza
• Eliminación de duplicados
• Corrección de orden temporal
• Detección y relleno de gaps
• Alineación multi-timeframe
• Validación de integridad

Los mensajes se actualizarán en tiempo real.
        """
        
        await self.telegram_bot.send_message(message, self.chat_id)
    
    def _update_live_messages(self):
        """Actualiza mensajes en vivo (ejecuta en hilo separado)"""
        last_message_id = None
        
        while self.is_running:
            try:
                if self.telegram_bot and self.chat_id and hasattr(self, 'status'):
                    message = self.repair_manager.render_live_repair(self.status)
                    
                    if last_message_id:
                        # Editar mensaje existente
                        asyncio.run_coroutine_threadsafe(
                            self.telegram_bot.edit_message(message, self.chat_id, last_message_id),
                            asyncio.get_event_loop()
                        )
                    else:
                        # Enviar nuevo mensaje
                        future = asyncio.run_coroutine_threadsafe(
                            self.telegram_bot.send_message(message, self.chat_id),
                            asyncio.get_event_loop()
                        )
                        result = future.result(timeout=5)
                        if result and hasattr(result, 'message_id'):
                            last_message_id = result.message_id
                
                time.sleep(self.repair_manager.update_rate_sec)
                
            except Exception as e:
                logger.error(f"❌ Error actualizando mensaje en vivo: {e}")
                time.sleep(5)
    
    async def _send_final_message(self, summary: Dict[str, Any]):
        """Envía mensaje final"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = self.repair_manager.render_final_repair(summary)
        await self.telegram_bot.send_message(message, self.chat_id)

async def main():
    """Función principal"""
    try:
        repairer = HistoryRepairer()
        await repairer.repair_all_historical_data()
        
    except KeyboardInterrupt:
        logger.info("🛑 Reparación interrumpida por usuario")
    except Exception as e:
        logger.error(f"❌ Error en reparación principal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
