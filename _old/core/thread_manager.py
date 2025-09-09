"""
core/thread_manager.py - Gestor de Threading Seguro
Sistema robusto para manejo de hilos y tareas concurrentes
"""

import threading
import asyncio
import queue
import time
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from enum import Enum
import weakref
import signal
import sys

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Estados de tareas"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Prioridades de tareas"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskInfo:
    """Información de una tarea"""
    task_id: str
    name: str
    function: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[Exception] = None
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

class SafeThreadManager:
    """Gestor seguro de hilos y tareas"""
    
    def __init__(self, max_workers: int = 4, max_processes: int = 2):
        self.max_workers = max_workers
        self.max_processes = max_processes
        
        # Executors
        self.thread_executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        
        # Control de tareas
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue = queue.PriorityQueue()
        self.completed_tasks: List[TaskInfo] = []
        
        # Locks y eventos
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._worker_threads: List[threading.Thread] = []
        
        # Configuración
        self.task_timeout = 300  # 5 minutos por defecto
        self.cleanup_interval = 60  # 1 minuto
        self.max_completed_tasks = 1000
        
        # Estadísticas
        self.stats = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_execution_time': 0.0
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Configurar manejo de señales
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Inicia el gestor de hilos"""
        with self._lock:
            if self.thread_executor is not None:
                self.logger.warning("Thread manager already started")
                return
            
            self.logger.info(f"Starting thread manager with {self.max_workers} workers")
            
            # Crear executors
            self.thread_executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="TradingBot"
            )
            
            self.process_executor = ProcessPoolExecutor(
                max_workers=self.max_processes
            )
            
            # Iniciar hilos de trabajo
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"Worker-{i}",
                    daemon=True
                )
                worker.start()
                self._worker_threads.append(worker)
            
            # Hilo de limpieza
            cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="Cleanup",
                daemon=True
            )
            cleanup_thread.start()
            self._worker_threads.append(cleanup_thread)
            
            self.logger.info("Thread manager started successfully")
    
    def shutdown(self, timeout: float = 30.0):
        """Detiene el gestor de hilos de forma segura"""
        with self._lock:
            if self.thread_executor is None:
                return
            
            self.logger.info("Shutting down thread manager...")
            
            # Señalar parada
            self._shutdown_event.set()
            
            # Cancelar tareas pendientes
            self._cancel_pending_tasks()
            
            # Cerrar executors
            if self.thread_executor:
                self.thread_executor.shutdown(wait=True, timeout=timeout)
                self.thread_executor = None
            
            if self.process_executor:
                self.process_executor.shutdown(wait=True, timeout=timeout)
                self.process_executor = None
            
            # Esperar a que terminen los hilos de trabajo
            for worker in self._worker_threads:
                if worker.is_alive():
                    worker.join(timeout=5.0)
            
            self.logger.info("Thread manager shutdown complete")
    
    def submit_task(self, 
                   name: str,
                   function: Callable,
                   *args,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: Optional[float] = None,
                   max_retries: int = 3,
                   use_process: bool = False,
                   **kwargs) -> str:
        """Envía una tarea para ejecución"""
        with self._lock:
            if self._shutdown_event.is_set():
                raise RuntimeError("Thread manager is shutting down")
            
            task_id = f"{name}_{int(time.time() * 1000)}"
            
            task = TaskInfo(
                task_id=task_id,
                name=name,
                function=function,
                args=args,
                kwargs=kwargs,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                timeout=timeout or self.task_timeout,
                max_retries=max_retries
            )
            
            self.tasks[task_id] = task
            self.task_queue.put((priority.value, task_id, task))
            self.stats['tasks_created'] += 1
            
            self.logger.debug(f"Task {task_id} submitted with priority {priority.value}")
            return task_id
    
    def submit_async_task(self,
                         name: str,
                         coro,
                         *args,
                         priority: TaskPriority = TaskPriority.NORMAL,
                         timeout: Optional[float] = None,
                         **kwargs) -> str:
        """Envía una tarea async para ejecución"""
        def async_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro(*args, **kwargs))
            finally:
                loop.close()
        
        return self.submit_task(
            name=name,
            function=async_wrapper,
            priority=priority,
            timeout=timeout
        )
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Obtiene el estado de una tarea"""
        with self._lock:
            task = self.tasks.get(task_id)
            return task.status if task else None
    
    def get_task_result(self, task_id: str) -> Any:
        """Obtiene el resultado de una tarea"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            if task.status == TaskStatus.COMPLETED:
                return task.result
            elif task.status == TaskStatus.FAILED:
                raise task.error
            else:
                return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancela una tarea"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.stats['tasks_cancelled'] += 1
            
            self.logger.info(f"Task {task_id} cancelled")
            return True
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Espera a que una tarea termine y devuelve el resultado"""
        start_time = time.time()
        
        while True:
            with self._lock:
                task = self.tasks.get(task_id)
                if not task:
                    raise ValueError(f"Task {task_id} not found")
                
                if task.status == TaskStatus.COMPLETED:
                    return task.result
                elif task.status == TaskStatus.FAILED:
                    raise task.error
                elif task.status == TaskStatus.CANCELLED:
                    raise RuntimeError(f"Task {task_id} was cancelled")
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")
            
            time.sleep(0.1)
    
    def _worker_loop(self):
        """Loop principal de los hilos de trabajo"""
        while not self._shutdown_event.is_set():
            try:
                # Obtener tarea de la cola
                try:
                    priority, task_id, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Verificar si la tarea fue cancelada
                with self._lock:
                    if task.status == TaskStatus.CANCELLED:
                        continue
                
                # Ejecutar tarea
                self._execute_task(task)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(1.0)
    
    def _execute_task(self, task: TaskInfo):
        """Ejecuta una tarea"""
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        try:
            # Ejecutar función
            if task.timeout:
                future = self.thread_executor.submit(task.function, *task.args, **task.kwargs)
                result = future.result(timeout=task.timeout)
            else:
                result = task.function(*task.args, **task.kwargs)
            
            # Tarea completada exitosamente
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                
                if task.started_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    self.stats['total_execution_time'] += execution_time
                
                self.stats['tasks_completed'] += 1
                self.completed_tasks.append(task)
            
            self.logger.debug(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            # Tarea falló
            with self._lock:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error = e
                self.stats['tasks_failed'] += 1
            
            self.logger.error(f"Task {task.task_id} failed: {e}")
            
            # Reintentar si es posible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                self.task_queue.put((task.priority.value, task.task_id, task))
                self.logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
    
    def _cancel_pending_tasks(self):
        """Cancela todas las tareas pendientes"""
        with self._lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    self.stats['tasks_cancelled'] += 1
    
    def _cleanup_loop(self):
        """Loop de limpieza de tareas completadas"""
        while not self._shutdown_event.is_set():
            try:
                time.sleep(self.cleanup_interval)
                
                with self._lock:
                    # Limpiar tareas completadas antiguas
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    self.completed_tasks = [
                        task for task in self.completed_tasks
                        if task.completed_at and task.completed_at > cutoff_time
                    ]
                    
                    # Limitar número de tareas completadas
                    if len(self.completed_tasks) > self.max_completed_tasks:
                        self.completed_tasks = self.completed_tasks[-self.max_completed_tasks:]
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de hilos"""
        with self._lock:
            active_tasks = sum(1 for task in self.tasks.values() 
                             if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING])
            
            avg_execution_time = (
                self.stats['total_execution_time'] / max(self.stats['tasks_completed'], 1)
            )
            
            return {
                'active_tasks': active_tasks,
                'completed_tasks': len(self.completed_tasks),
                'total_created': self.stats['tasks_created'],
                'total_completed': self.stats['tasks_completed'],
                'total_failed': self.stats['tasks_failed'],
                'total_cancelled': self.stats['tasks_cancelled'],
                'average_execution_time': round(avg_execution_time, 2),
                'is_running': self.thread_executor is not None
            }

# Instancia global
thread_manager = SafeThreadManager()

# Funciones de conveniencia
def submit_task(name: str, function: Callable, *args, **kwargs) -> str:
    """Envía una tarea para ejecución"""
    return thread_manager.submit_task(name, function, *args, **kwargs)

def submit_async_task(name: str, coro, *args, **kwargs) -> str:
    """Envía una tarea async para ejecución"""
    return thread_manager.submit_async_task(name, coro, *args, **kwargs)

def wait_for_task(task_id: str, timeout: Optional[float] = None) -> Any:
    """Espera a que una tarea termine"""
    return thread_manager.wait_for_task(task_id, timeout)

def get_task_status(task_id: str) -> Optional[TaskStatus]:
    """Obtiene el estado de una tarea"""
    return thread_manager.get_task_status(task_id)

def get_thread_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del gestor de hilos"""
    return thread_manager.get_stats()

def start_thread_manager():
    """Inicia el gestor de hilos"""
    thread_manager.start()

def shutdown_thread_manager():
    """Detiene el gestor de hilos"""
    thread_manager.shutdown()
