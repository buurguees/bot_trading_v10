# Ruta: core/personal/latency/__init__.py
"""
Latency Optimization Module - Bot Trading v10 Personal
======================================================

Optimización de latencia para trading de alta frecuencia personal con:
- Optimización de latencia <50ms
- Pre-carga de datos
- Cache inteligente
- Optimización de red
- Métricas de rendimiento
"""

from .latency_optimizer import LatencyOptimizer
from .hft_engine import HFTEngine
from .performance_monitor import PerformanceMonitor

__all__ = [
    'LatencyOptimizer',
    'HFTEngine', 
    'PerformanceMonitor'
]
