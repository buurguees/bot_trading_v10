#!/usr/bin/env python3
"""
Script de Descarga de Datos Históricos - Trading Bot v10 Enterprise
==================================================================

Script para descargar, auditar y reparar datos históricos.
Se ejecuta desde Telegram con el comando /download_history.

Características:
- Descarga automática por símbolo y timeframe
- Auditoría de duplicados y gaps
- Reparación automática de datos faltantes
- Mensajes en vivo a Telegram
- Reportes detallados

Uso:
    python scripts/history/download_history.py

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.data.history_manager import HistoryManager, DownloadStatus

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_history.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HistoryDownloader:
    """Descargador de datos históricos con mensajes en vivo"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el descargador"""
        self.history_manager = HistoryManager(config_path)
        self.telegram_bot = None
        self.chat_id = None
        self.status = None
        self.is_running = False
        
        logger.info("📥 Descargador de datos históricos inicializado")
    
    def set_telegram_bot(self, telegram_bot, chat_id: str):
        """Configura el bot de Telegram para mensajes"""
        self.telegram_bot = telegram_bot
        self.chat_id = chat_id
    
    async def download_all_historical_data(self):
        """Descarga todos los datos históricos"""
        try:
            self.is_running = True
            start_time = datetime.now()
            
            # Obtener símbolos y timeframes
            symbols, timeframes = self.history_manager.list_symbols_and_tfs()
            total_tasks = len(symbols) * len(timeframes)
            
            # Inicializar estado
            self.status = DownloadStatus(
                total_symbols=len(symbols),
                total_timeframes=len(timeframes),
                completed_tasks=0,
                current_symbol="",
                current_timeframe="",
                current_action="Iniciando...",
                progress_percentage=0.0,
                start_time=start_time,
                elapsed_time="00:00:00",
                rate_limit_ok=True,
                retries_count=0,
                new_candles=0,
                duplicates_removed=0,
                gaps_repaired=0
            )
            
            # Enviar mensaje inicial
            await self._send_initial_message()
            
            # Iniciar hilo de actualizaciones en vivo
            update_thread = threading.Thread(target=self._update_live_messages, daemon=True)
            update_thread.start()
            
            # Procesar cada símbolo y timeframe
            results = {}
            
            for symbol in symbols:
                if not self.is_running:
                    break
                
                results[symbol] = {}
                
                for timeframe in timeframes:
                    if not self.is_running:
                        break
                    
                    # Actualizar estado
                    self.status.current_symbol = symbol
                    self.status.current_timeframe = timeframe
                    self.status.current_action = f"Procesando {symbol} {timeframe}"
                    
                    # Procesar símbolo/timeframe
                    tf_results = await self._process_symbol_timeframe(symbol, timeframe)
                    results[symbol][timeframe] = tf_results
                    
                    # Actualizar progreso
                    self.status.completed_tasks += 1
                    self.status.progress_percentage = (self.status.completed_tasks / total_tasks) * 100
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
            
            # Calcular duración total
            total_duration = datetime.now() - start_time
            results['total_duration'] = str(total_duration).split('.')[0]
            
            # Enviar mensaje final
            await self._send_final_message(results)
            
            logger.info("✅ Descarga de datos históricos completada")
            
        except Exception as e:
            logger.error(f"❌ Error en descarga de datos históricos: {e}")
            if self.telegram_bot and self.chat_id:
                await self.telegram_bot.send_message(f"❌ Error en descarga: {str(e)}", self.chat_id)
        finally:
            self.is_running = False
    
    async def _process_symbol_timeframe(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Procesa un símbolo y timeframe específico"""
        try:
            # Construir ruta del archivo
            file_path = self.history_manager.historical_root / symbol / f"{timeframe}.csv"
            
            # Leer datos existentes
            existing_df = self.history_manager.read_csv_or_empty(str(file_path))
            
            # Calcular rango de tiempo objetivo
            end_time = int(time.time() * 1000)
            start_time = end_time - (self.history_manager.download_window_years * 365 * 24 * 60 * 60 * 1000)
            
            new_candles = 0
            duplicates_removed = 0
            gaps_repaired = 0
            
            if existing_df.empty:
                # Descarga completa
                self.status.current_action = f"Descargando {symbol} {timeframe} (completo)"
                df = self.history_manager.fetch_klines(symbol, timeframe, start_time, end_time)
                new_candles = len(df)
            else:
                # Auditoría y reparación
                self.status.current_action = f"Auditando {symbol} {timeframe}"
                
                # Eliminar duplicados
                df_clean, dupes = self.history_manager.dedupe_by_open_time(existing_df)
                duplicates_removed = dupes
                
                # Detectar gaps
                gaps = self.history_manager.detect_gaps(df_clean, timeframe)
                gaps_repaired = len(gaps)
                
                if gaps:
                    # Re-descargar gaps
                    self.status.current_action = f"Reparando gaps en {symbol} {timeframe}"
                    gap_data = self.history_manager.redownload_ranges(symbol, timeframe, gaps)
                    if not gap_data.empty:
                        df_clean = self.history_manager.merge_and_sort(df_clean, gap_data)
                
                df = df_clean
            
            # Validar datos
            validation = self.history_manager.validate_schema_and_ranges(df, timeframe)
            
            if validation['valid']:
                # Guardar datos
                self.status.current_action = f"Guardando {symbol} {timeframe}"
                self.history_manager.write_csv_atomic(df, str(file_path))
                
                # Actualizar contadores
                self.status.new_candles += new_candles
                self.status.duplicates_removed += duplicates_removed
                self.status.gaps_repaired += gaps_repaired
                
                return {
                    'status': 'success',
                    'new_candles': new_candles,
                    'duplicates_removed': duplicates_removed,
                    'gaps_repaired': gaps_repaired,
                    'total_rows': len(df),
                    'integrity_score': validation['integrity_score']
                }
            else:
                logger.warning(f"⚠️ Datos inválidos para {symbol} {timeframe}: {validation['errors']}")
                return {
                    'status': 'warning',
                    'new_candles': new_candles,
                    'duplicates_removed': duplicates_removed,
                    'gaps_repaired': gaps_repaired,
                    'total_rows': len(df),
                    'integrity_score': validation['integrity_score'],
                    'errors': validation['errors']
                }
                
        except Exception as e:
            logger.error(f"❌ Error procesando {symbol} {timeframe}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'new_candles': 0,
                'duplicates_removed': 0,
                'gaps_repaired': 0,
                'total_rows': 0,
                'integrity_score': 0.0
            }
    
    async def _send_initial_message(self):
        """Envía mensaje inicial"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = f"""
📥 <b>Iniciando Descarga de Datos Históricos</b>

• Símbolos: {', '.join(self.history_manager.config.get('symbols', []))}
• Timeframes: {', '.join(self.history_manager.config.get('timeframes', []))}
• Años de datos: {self.history_manager.download_window_years}
• Estado: Iniciando...

• Verificando datos existentes...
• Descargando datos faltantes...
• Auditando duplicados y gaps...
• Reparando inconsistencias...

Los mensajes se actualizarán en tiempo real.
        """
        
        await self.telegram_bot.send_message(message, self.chat_id)
    
    def _update_live_messages(self):
        """Actualiza mensajes en vivo (ejecuta en hilo separado)"""
        last_message_id = None
        
        while self.is_running:
            try:
                if self.telegram_bot and self.chat_id and self.status:
                    message = self.history_manager.render_live_download(self.status)
                    
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
    
    async def _send_final_message(self, results: Dict[str, Any]):
        """Envía mensaje final"""
        if not self.telegram_bot or not self.chat_id:
            return
        
        message = self.history_manager.render_final_download(results)
        await self.telegram_bot.send_message(message, self.chat_id)

async def main():
    """Función principal"""
    try:
        downloader = HistoryDownloader()
        await downloader.download_all_historical_data()
        
    except KeyboardInterrupt:
        logger.info("🛑 Descarga interrumpida por usuario")
    except Exception as e:
        logger.error(f"❌ Error en descarga principal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
