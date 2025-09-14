#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
message_queue.py
================
Sistema de Cola de Mensajes para Telegram

Maneja el envío de mensajes con control de flood y cola inteligente.

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QueuedMessage:
    """Mensaje en cola para envío"""
    message: str
    parse_mode: str = "HTML"
    priority: int = 1  # 1=alta, 2=media, 3=baja
    created_at: datetime = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class TelegramMessageQueue:
    """Cola inteligente de mensajes para Telegram con control de flood"""
    
    def __init__(self, bot, max_queue_size: int = 100, base_delay: float = 2.0):
        self.bot = bot
        self.max_queue_size = max_queue_size
        self.base_delay = base_delay
        self.queue: List[QueuedMessage] = []
        self.is_processing = False
        self.last_send_time = datetime.now()
        self.min_interval = timedelta(seconds=base_delay)
        
    async def add_message(self, message: str, parse_mode: str = "HTML", priority: int = 1):
        """Agregar mensaje a la cola"""
        if len(self.queue) >= self.max_queue_size:
            # Remover mensaje más antiguo de menor prioridad
            self.queue.sort(key=lambda x: (x.priority, x.created_at))
            removed = self.queue.pop(0)
            logger.warning(f"⚠️ Cola llena, removiendo mensaje: {removed.message[:50]}...")
        
        queued_msg = QueuedMessage(
            message=message,
            parse_mode=parse_mode,
            priority=priority
        )
        
        self.queue.append(queued_msg)
        logger.debug(f"📝 Mensaje agregado a cola (prioridad {priority}): {message[:50]}...")
        
        # Iniciar procesamiento si no está activo
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        """Procesar cola de mensajes con control de flood"""
        if self.is_processing:
            return
            
        self.is_processing = True
        logger.info("🔄 Iniciando procesamiento de cola de mensajes...")
        
        try:
            while self.queue:
                # Ordenar por prioridad y tiempo de creación
                self.queue.sort(key=lambda x: (x.priority, x.created_at))
                
                # Verificar intervalo mínimo entre mensajes
                time_since_last = datetime.now() - self.last_send_time
                if time_since_last < self.min_interval:
                    wait_time = (self.min_interval - time_since_last).total_seconds()
                    logger.debug(f"⏳ Esperando {wait_time:.1f}s para evitar flood control...")
                    await asyncio.sleep(wait_time)
                
                # Tomar siguiente mensaje
                queued_msg = self.queue.pop(0)
                
                # Intentar enviar mensaje
                success = await self._send_message_safe(queued_msg)
                
                if not success:
                    # Reintentar si no es el último intento
                    queued_msg.retry_count += 1
                    if queued_msg.retry_count < 3:
                        logger.warning(f"⚠️ Reintentando mensaje (intento {queued_msg.retry_count + 1})")
                        self.queue.insert(0, queued_msg)  # Volver al inicio de la cola
                        await asyncio.sleep(5)  # Esperar antes del reintento
                    else:
                        logger.error(f"❌ Mensaje falló después de 3 intentos: {queued_msg.message[:50]}...")
                
                self.last_send_time = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Error procesando cola: {e}")
        finally:
            self.is_processing = False
            logger.info("✅ Procesamiento de cola completado")
    
    async def _send_message_safe(self, queued_msg: QueuedMessage) -> bool:
        """Enviar mensaje de forma segura con manejo de errores"""
        try:
            await self.bot.send_message(
                queued_msg.message,
                queued_msg.parse_mode
            )
            logger.debug(f"✅ Mensaje enviado: {queued_msg.message[:50]}...")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "flood control" in error_msg or "too many requests" in error_msg:
                # Flood control - esperar más tiempo
                wait_time = self.base_delay * (2 ** queued_msg.retry_count)
                logger.warning(f"⚠️ Flood control detectado, esperando {wait_time}s...")
                await asyncio.sleep(wait_time)
                return False
            else:
                logger.warning(f"⚠️ Error enviando mensaje: {e}")
                return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Obtener estado de la cola"""
        return {
            "queue_size": len(self.queue),
            "is_processing": self.is_processing,
            "last_send_time": self.last_send_time.isoformat(),
            "messages_by_priority": {
                "alta": len([m for m in self.queue if m.priority == 1]),
                "media": len([m for m in self.queue if m.priority == 2]),
                "baja": len([m for m in self.queue if m.priority == 3])
            }
        }
    
    async def clear_queue(self):
        """Limpiar cola de mensajes"""
        self.queue.clear()
        logger.info("🗑️ Cola de mensajes limpiada")
    
    async def wait_for_empty_queue(self, timeout: int = 30):
        """Esperar a que la cola esté vacía"""
        start_time = datetime.now()
        
        while self.queue and (datetime.now() - start_time).seconds < timeout:
            await asyncio.sleep(1)
        
        if self.queue:
            logger.warning(f"⚠️ Timeout esperando cola vacía, {len(self.queue)} mensajes pendientes")
        else:
            logger.info("✅ Cola vacía")
