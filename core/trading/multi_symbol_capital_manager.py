#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Symbol Capital Manager - Bot Trading v10 Enterprise
=========================================================
Gestor de capital centralizado para trading multi-símbolo.

Características:
- Distribución inteligente del balance inicial entre símbolos
- Gestión centralizada de capital
- Rebalanceo dinámico basado en performance
- Control de riesgo agregado
- Tracking de PnL por símbolo y total

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)

class AllocationMethod(Enum):
    """Métodos de asignación de capital"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    PERFORMANCE_BASED = "performance_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_OPTIMAL = "kelly_optimal"

@dataclass
class SymbolAllocation:
    """Asignación de capital para un símbolo"""
    symbol: str
    allocated_balance: float
    current_balance: float
    allocation_pct: float
    performance_score: float
    risk_score: float
    last_rebalance: datetime
    max_allocation_pct: float = 0.25  # Máximo 25% por símbolo
    min_allocation_pct: float = 0.05  # Mínimo 5% por símbolo

@dataclass
class CapitalMetrics:
    """Métricas de capital agregadas"""
    total_balance: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    max_drawdown: float
    current_drawdown: float
    peak_balance: float
    active_symbols: int
    best_performer: str
    worst_performer: str
    last_updated: datetime

class MultiSymbolCapitalManager:
    """
    Gestor de Capital Multi-Símbolo
    ===============================
    
    Gestiona la distribución y control de capital entre múltiples símbolos
    para optimizar el rendimiento total del portfolio.
    """
    
    def __init__(self, 
                 initial_balance: float = 1000.0,
                 allocation_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT,
                 rebalance_threshold: float = 0.05,  # 5% desviación para rebalancear
                 max_risk_per_symbol: float = 0.02,  # 2% máximo por símbolo
                 min_allocation_pct: float = 0.05,   # 5% mínimo
                 max_allocation_pct: float = 0.25):  # 25% máximo
        """
        Inicializa el gestor de capital
        
        Args:
            initial_balance: Balance inicial total
            allocation_method: Método de asignación
            rebalance_threshold: Umbral para rebalanceo
            max_risk_per_symbol: Riesgo máximo por símbolo
            min_allocation_pct: Asignación mínima por símbolo
            max_allocation_pct: Asignación máxima por símbolo
        """
        self.initial_balance = initial_balance
        self.current_total_balance = initial_balance
        self.peak_balance = initial_balance
        
        self.allocation_method = allocation_method
        self.rebalance_threshold = rebalance_threshold
        self.max_risk_per_symbol = max_risk_per_symbol
        self.min_allocation_pct = min_allocation_pct
        self.max_allocation_pct = max_allocation_pct
        
        # Asignaciones por símbolo
        self.symbol_allocations: Dict[str, SymbolAllocation] = {}
        
        # Métricas agregadas
        self.capital_metrics = CapitalMetrics(
            total_balance=initial_balance,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            daily_pnl=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            peak_balance=initial_balance,
            active_symbols=0,
            best_performer="",
            worst_performer="",
            last_updated=datetime.now()
        )
        
        # Historial de rebalanceos
        self.rebalance_history: List[Dict[str, Any]] = []
        
        # Directorio de datos
        self.data_dir = Path("data/capital_management")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"💰 MultiSymbolCapitalManager inicializado con ${initial_balance:,.2f}")
    
    def initialize_symbols(self, symbols: List[str], 
                          symbol_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        """
        Inicializa asignaciones para los símbolos dados
        
        Args:
            symbols: Lista de símbolos a operar
            symbol_configs: Configuraciones específicas por símbolo
            
        Returns:
            Diccionario con balance asignado por símbolo
        """
        try:
            if not symbols:
                logger.warning("⚠️ No se proporcionaron símbolos para inicializar")
                return {}
            
            # Limpiar asignaciones previas
            self.symbol_allocations.clear()
            
            # Calcular asignaciones según método
            if self.allocation_method == AllocationMethod.EQUAL_WEIGHT:
                allocations = self._calculate_equal_weight_allocations(symbols)
            elif self.allocation_method == AllocationMethod.RISK_PARITY:
                allocations = self._calculate_risk_parity_allocations(symbols, symbol_configs)
            elif self.allocation_method == AllocationMethod.PERFORMANCE_BASED:
                allocations = self._calculate_performance_based_allocations(symbols)
            elif self.allocation_method == AllocationMethod.VOLATILITY_ADJUSTED:
                allocations = self._calculate_volatility_adjusted_allocations(symbols, symbol_configs)
            else:
                allocations = self._calculate_equal_weight_allocations(symbols)
            
            # Crear asignaciones
            for symbol in symbols:
                allocated_balance = allocations.get(symbol, 0.0)
                allocation_pct = allocated_balance / self.initial_balance
                
                # Aplicar configuraciones específicas del símbolo
                max_pct = self.max_allocation_pct
                min_pct = self.min_allocation_pct
                
                if symbol_configs and symbol in symbol_configs:
                    symbol_config = symbol_configs[symbol]
                    max_pct = symbol_config.get('max_position_size_pct', self.max_allocation_pct) / 100
                    min_pct = symbol_config.get('min_position_size_pct', self.min_allocation_pct) / 100
                
                # Para distribución igual, mantener la asignación calculada
                # Los límites se aplicarán solo si es necesario en el futuro
                # (por ahora, mantener la distribución igual pura)
                
                # NO recalcular allocated_balance - ya está correcto desde allocations
                
                self.symbol_allocations[symbol] = SymbolAllocation(
                    symbol=symbol,
                    allocated_balance=allocated_balance,
                    current_balance=allocated_balance,
                    allocation_pct=allocation_pct,
                    performance_score=0.0,
                    risk_score=0.0,
                    last_rebalance=datetime.now(),
                    max_allocation_pct=max_pct,
                    min_allocation_pct=min_pct
                )
            
            # Actualizar métricas
            self._update_capital_metrics()
            
            logger.info(f"🎯 Inicializadas asignaciones para {len(symbols)} símbolos")
            logger.info(f"📊 Balance total distribuido: ${sum(a.allocated_balance for a in self.symbol_allocations.values()):,.2f}")
            
            return {symbol: allocation.allocated_balance for symbol, allocation in self.symbol_allocations.items()}
            
        except Exception as e:
            logger.error(f"❌ Error inicializando símbolos: {e}")
            return {}
    
    def _calculate_equal_weight_allocations(self, symbols: List[str]) -> Dict[str, float]:
        """Calcula asignaciones de peso igual"""
        try:
            balance_per_symbol = self.initial_balance / len(symbols)
            return {symbol: balance_per_symbol for symbol in symbols}
        except Exception as e:
            logger.error(f"❌ Error calculando asignaciones iguales: {e}")
            return {}
    
    def _calculate_risk_parity_allocations(self, symbols: List[str], 
                                         symbol_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        """Calcula asignaciones de paridad de riesgo"""
        try:
            # Por ahora, usar pesos iguales (en el futuro se puede implementar riesgo real)
            # Esto requeriría datos históricos de volatilidad
            return self._calculate_equal_weight_allocations(symbols)
        except Exception as e:
            logger.error(f"❌ Error calculando asignaciones de paridad de riesgo: {e}")
            return self._calculate_equal_weight_allocations(symbols)
    
    def _calculate_performance_based_allocations(self, symbols: List[str]) -> Dict[str, float]:
        """Calcula asignaciones basadas en performance (para futuras implementaciones)"""
        try:
            # Por ahora, usar pesos iguales
            # En el futuro, esto se basaría en el historial de performance
            return self._calculate_equal_weight_allocations(symbols)
        except Exception as e:
            logger.error(f"❌ Error calculando asignaciones basadas en performance: {e}")
            return self._calculate_equal_weight_allocations(symbols)
    
    def _calculate_volatility_adjusted_allocations(self, symbols: List[str], 
                                                 symbol_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        """Calcula asignaciones ajustadas por volatilidad"""
        try:
            # Por ahora, usar pesos iguales
            # En el futuro, esto se basaría en la volatilidad histórica
            return self._calculate_equal_weight_allocations(symbols)
        except Exception as e:
            logger.error(f"❌ Error calculando asignaciones ajustadas por volatilidad: {e}")
            return self._calculate_equal_weight_allocations(symbols)
    
    def update_symbol_balance(self, symbol: str, new_balance: float, pnl: float = 0.0) -> bool:
        """
        Actualiza el balance de un símbolo específico
        
        Args:
            symbol: Símbolo a actualizar
            new_balance: Nuevo balance del símbolo
            pnl: PnL del símbolo en este ciclo
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            if symbol not in self.symbol_allocations:
                logger.warning(f"⚠️ Símbolo {symbol} no encontrado en asignaciones")
                return False
            
            allocation = self.symbol_allocations[symbol]
            old_balance = allocation.current_balance
            allocation.current_balance = new_balance
            
            # Actualizar score de performance
            if old_balance > 0:
                performance_pct = (new_balance - old_balance) / old_balance
                allocation.performance_score = performance_pct
            
            # Actualizar balance total
            self._update_total_balance()
            
            # Verificar si necesita rebalanceo
            if self._should_rebalance():
                self._rebalance_allocations()
            
            logger.debug(f"📊 Balance actualizado para {symbol}: ${old_balance:.2f} -> ${new_balance:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando balance de {symbol}: {e}")
            return False
    
    def _update_total_balance(self):
        """Actualiza el balance total agregado"""
        try:
            self.current_total_balance = sum(allocation.current_balance for allocation in self.symbol_allocations.values())
            
            # Actualizar peak balance
            if self.current_total_balance > self.peak_balance:
                self.peak_balance = self.current_total_balance
            
            # Calcular drawdown
            self.capital_metrics.current_drawdown = (self.peak_balance - self.current_total_balance) / self.peak_balance
            self.capital_metrics.max_drawdown = max(self.capital_metrics.max_drawdown, self.capital_metrics.current_drawdown)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando balance total: {e}")
    
    def _should_rebalance(self) -> bool:
        """Determina si se necesita rebalanceo"""
        try:
            if not self.symbol_allocations:
                return False
            
            # Calcular desviación promedio de las asignaciones
            target_allocations = [allocation.allocation_pct for allocation in self.symbol_allocations.values()]
            current_allocations = [allocation.current_balance / self.current_total_balance 
                                 for allocation in self.symbol_allocations.values()]
            
            deviations = [abs(target - current) for target, current in zip(target_allocations, current_allocations)]
            avg_deviation = np.mean(deviations)
            
            return avg_deviation > self.rebalance_threshold
            
        except Exception as e:
            logger.error(f"❌ Error verificando necesidad de rebalanceo: {e}")
            return False
    
    def _rebalance_allocations(self):
        """Rebalancea las asignaciones entre símbolos"""
        try:
            logger.info("🔄 Iniciando rebalanceo de asignaciones")
            
            # Guardar estado previo
            prev_allocations = {symbol: allocation.current_balance for symbol, allocation in self.symbol_allocations.items()}
            
            # Recalcular asignaciones
            symbols = list(self.symbol_allocations.keys())
            new_allocations = self._calculate_equal_weight_allocations(symbols)
            
            # Aplicar nuevas asignaciones
            for symbol, allocation in self.symbol_allocations.items():
                new_balance = new_allocations.get(symbol, allocation.current_balance)
                allocation.current_balance = new_balance
                allocation.last_rebalance = datetime.now()
            
            # Registrar rebalanceo
            rebalance_record = {
                "timestamp": datetime.now().isoformat(),
                "prev_allocations": prev_allocations,
                "new_allocations": new_allocations,
                "total_balance": self.current_total_balance,
                "method": self.allocation_method.value
            }
            self.rebalance_history.append(rebalance_record)
            
            logger.info("✅ Rebalanceo completado")
            
        except Exception as e:
            logger.error(f"❌ Error en rebalanceo: {e}")
    
    def _update_capital_metrics(self):
        """Actualiza las métricas de capital agregadas"""
        try:
            if not self.symbol_allocations:
                return
            
            # Calcular métricas básicas
            total_balance = sum(allocation.current_balance for allocation in self.symbol_allocations.values())
            total_pnl = total_balance - self.initial_balance
            total_pnl_pct = (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
            
            # Encontrar mejor y peor performer
            performances = {symbol: allocation.performance_score for symbol, allocation in self.symbol_allocations.items()}
            best_performer = max(performances, key=performances.get) if performances else ""
            worst_performer = min(performances, key=performances.get) if performances else ""
            
            # Actualizar métricas
            self.capital_metrics = CapitalMetrics(
                total_balance=total_balance,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                daily_pnl=0.0,  # Se actualizará por el sistema de trading
                max_drawdown=self.capital_metrics.max_drawdown,
                current_drawdown=self.capital_metrics.current_drawdown,
                peak_balance=self.peak_balance,
                active_symbols=len([a for a in self.symbol_allocations.values() if a.current_balance > 0]),
                best_performer=best_performer,
                worst_performer=worst_performer,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas de capital: {e}")
    
    def get_symbol_balance(self, symbol: str) -> float:
        """Obtiene el balance actual de un símbolo"""
        try:
            if symbol in self.symbol_allocations:
                return self.symbol_allocations[symbol].current_balance
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance de {symbol}: {e}")
            return 0.0
    
    def get_total_balance(self) -> float:
        """Obtiene el balance total agregado"""
        return self.current_total_balance
    
    def get_capital_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de capital agregadas"""
        try:
            return asdict(self.capital_metrics)
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas de capital: {e}")
            return {}
    
    def get_symbol_allocations(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene asignaciones de todos los símbolos"""
        try:
            return {
                symbol: asdict(allocation) 
                for symbol, allocation in self.symbol_allocations.items()
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo asignaciones: {e}")
            return {}
    
    def save_state(self):
        """Guarda el estado del gestor de capital"""
        try:
            state = {
                "initial_balance": self.initial_balance,
                "current_total_balance": self.current_total_balance,
                "peak_balance": self.peak_balance,
                "allocation_method": self.allocation_method.value,
                "symbol_allocations": self.get_symbol_allocations(),
                "capital_metrics": self.get_capital_metrics(),
                "rebalance_history": self.rebalance_history[-100:],  # Últimos 100 rebalanceos
                "last_saved": datetime.now().isoformat()
            }
            
            state_file = self.data_dir / "capital_manager_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            logger.info("💾 Estado del gestor de capital guardado")
            
        except Exception as e:
            logger.error(f"❌ Error guardando estado del gestor de capital: {e}")
    
    def load_state(self) -> bool:
        """Carga el estado previo del gestor de capital"""
        try:
            state_file = self.data_dir / "capital_manager_state.json"
            
            if not state_file.exists():
                logger.info("📁 No se encontró estado previo del gestor de capital")
                return False
            
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Restaurar estado básico
            self.initial_balance = state.get('initial_balance', 1000.0)
            self.current_total_balance = state.get('current_total_balance', self.initial_balance)
            self.peak_balance = state.get('peak_balance', self.initial_balance)
            
            # Restaurar asignaciones
            symbol_allocations_data = state.get('symbol_allocations', {})
            for symbol, allocation_data in symbol_allocations_data.items():
                self.symbol_allocations[symbol] = SymbolAllocation(**allocation_data)
            
            # Restaurar historial de rebalanceos
            self.rebalance_history = state.get('rebalance_history', [])
            
            logger.info("📚 Estado del gestor de capital cargado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando estado del gestor de capital: {e}")
            return False

# Factory function
def create_capital_manager(initial_balance: float = 1000.0, 
                         allocation_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT) -> MultiSymbolCapitalManager:
    """Crea una instancia de MultiSymbolCapitalManager"""
    return MultiSymbolCapitalManager(initial_balance, allocation_method)
