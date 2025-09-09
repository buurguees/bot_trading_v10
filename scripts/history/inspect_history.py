#!/usr/bin/env python3
"""
Script de Inspección de Datos Históricos - Trading Bot v10 Enterprise
=====================================================================

Script para inspeccionar y analizar el estado de los datos históricos.
Se ejecuta desde Telegram con el comando /inspect_history.

Características:
- Análisis de cobertura por símbolo y timeframe
- Detección de gaps y duplicados
- Cálculo de integridad de datos
- Reportes detallados en CSV/JSON
- Mensajes en vivo a Telegram

Uso:
    python scripts/history/inspect_history.py

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

from core.data.history_manager import HistoryManager, FileReport

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/inspect_history.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HistoryInspector:
    """Inspector de datos históricos con mensajes en vivo"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el inspector"""
        self.history_manager = HistoryManager(config_path)
        self.telegram_bot = None
        self.chat_id = None
        self.is_running = False
        
        logger.info("🔍 Inspector de datos históricos inicializado")
    
    def set_telegram_bot(self, telegram_bot, chat_id: str):
        """Configura el bot de Telegram para mensajes"""
        self.telegram_bot = telegram_bot
        self.chat_id = chat_id
    
    async def inspect_all_historical_data(self):
        """Inspecciona todos los datos históricos"""
        try:
            self.is_running = True
            start_time = datetime.now()
            
            # Escanear archivos existentes
            files = self.history_manager.scan_historical_files()
            total_files = len(files)
            
            if total_files == 0:
                await self._send_no_files_message()
                return
            
            # Enviar mensaje inicial
            await self._send_initial_message(total_files)
            
            # Iniciar hilo de actualizaciones en vivo
            update_thread = threading.Thread(
                target=self._update_live_messages, 
                args=(total_files,),
                daemon=True
            )
            update_thread.start()
            
            # Procesar cada archivo
            reports = []
            files_processed = 0
            
            for file_info in files:
                if not self.is_running:
                    break
                
                # Inspeccionar archivo
                report = self.history_manager.inspect_file(
                    file_info['symbol'],
                    file_info['timeframe'],
                    file_info['file_path']
                )
                reports.append(report)
                files_processed += 1
                
                # Actualizar progreso para mensaje en vivo
                self._current_progress = {
                    'files_processed': files_processed,
                    'total_files': total_files,
                    'progress_percentage': (files_processed / total_files) * 100,
                    'current_file': f"{file_info['symbol']} {file_info['timeframe']}"
                }
                
                # Pequeña pausa para no sobrecargar
                await asyncio.sleep(0.1)
            
            # Agregar archivos de configuración que no existen
            symbols, timeframes = self.history_manager.list_symbols_and_tfs()
            for symbol in symbols:
                for timeframe in timeframes:
                    file_path = self.history_manager.historical_root / symbol / f"{timeframe}.csv"
                    if not file_path.exists():
                        # Crear reporte para archivo faltante
                        missing_report = FileReport(
                            symbol=symbol,
                            timeframe=timeframe,
                            file_path=str(file_path),
                            min_open_time=0,
                            max_open_time=0,
                            num_rows=0,
                            gaps_count=0,
                            max_gap_size=0,
                            duplicates_count=0,
                            coverage_percentage=0.0,
                            integrity_score=0.0,
                            status="missing"
                        )
                        reports.append(missing_report)
            
            # Agregar progreso final
            self._current_progress = {
                'files_processed': total_files,
                'total_files': total_files,
                'progress_percentage': 100.0,
                'current_file': "Completado"
            }
            
            # Generar resumen
            summary = self.history_manager.aggregate_reports(reports)
            
            # Guardar reporte
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"reports/history_inventory_{timestamp}"
            self.history_manager.write_inventory_report(summary, reports, report_path)
            
            # Enviar mensaje final
            await self._send_final_message(summary, f"{report_path}.json")
            
            logger.info("✅ Inspección de datos históricos completada")
            
        except Exception as e:
            logger.error(f"❌ Error en inspección de datos históricos: {e}")
            if self.telegram_bot and self.chat_id:
                await self.telegram_bot.send_message(f"❌ Error en inspección: {str(e)}", self.chat_id)
        finally:
            self.is_running = False
    
    async def _send_no_files_message(self):
        """Envía mensaje cuando no hay archivos"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = """
⚠️ <b>No se encontraron archivos históricos</b>

• No hay datos históricos para inspeccionar
• Usa /download_history para descargar datos
• Directorio: data/historical/
        """
        
        await self.telegram_bot.send_message(message, self.chat_id)
    
    async def _send_initial_message(self, total_files: int):
        """Envía mensaje inicial"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = f"""
🔍 <b>Iniciando Inspección de Datos Históricos</b>

• Archivos encontrados: {total_files}
• Estado: Analizando cobertura y integridad...
• Progreso: 0%

• Verificando gaps y duplicados...
• Calculando cobertura temporal...
• Validando integridad de datos...

Los mensajes se actualizarán en tiempo real.
        """
        
        await self.telegram_bot.send_message(message, self.chat_id)
    
    def _update_live_messages(self, total_files: int):
        """Actualiza mensajes en vivo (ejecuta en hilo separado)"""
        last_message_id = None
        
        while self.is_running and hasattr(self, '_current_progress'):
            try:
                if self.telegram_bot and self.chat_id:
                    progress = getattr(self, '_current_progress', {
                        'files_processed': 0,
                        'total_files': total_files,
                        'progress_percentage': 0.0,
                        'current_file': "Iniciando..."
                    })
                    
                    message = self.history_manager.render_live_inspect(
                        progress, 
                        progress.get('current_file', '')
                    )
                    
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
                
                time.sleep(self.history_manager.update_rate_sec)
                
            except Exception as e:
                logger.error(f"❌ Error actualizando mensaje en vivo: {e}")
                time.sleep(5)
    
    async def _send_final_message(self, summary: Dict[str, Any], report_path: str):
        """Envía mensaje final"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = self.history_manager.render_final_inspect(summary, report_path)
        await self.telegram_bot.send_message(message, self.chat_id)

async def main():
    """Función principal"""
    try:
        inspector = HistoryInspector()
        await inspector.inspect_all_historical_data()
        
    except KeyboardInterrupt:
        logger.info("🛑 Inspección interrumpida por usuario")
    except Exception as e:
        logger.error(f"❌ Error en inspección principal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
