# Ruta: core/monitoring/core/performance_tracker.py
"""
monitoring/core/performance_tracker.py
Seguimiento de Rendimiento - Trading Bot v10

Esta clase maneja el cálculo, seguimiento y análisis de métricas de rendimiento
del bot de trading. Proporciona análisis avanzados de performance, riesgo
y optimización de estrategias.
"""

import logging
import threading
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
from pathlib import Path

# Importaciones para cálculos financieros
try:
    import scipy.stats as stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy no disponible - algunas métricas avanzadas estarán limitadas")

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento calculadas"""
    symbol: str
    period_start: datetime
    period_end: datetime
    
    # Métricas básicas
    total_return: float
    total_return_pct: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Métricas de riesgo
    max_drawdown: float
    max_drawdown_duration: int  # días
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    beta: Optional[float]
    
    # Métricas de trading
    total_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    
    # Métricas avanzadas
    information_ratio: Optional[float]
    treynor_ratio: Optional[float]
    jensen_alpha: Optional[float]
    tracking_error: Optional[float]
    
    # Ratios de consistencia
    win_loss_ratio: float
    consecutive_wins: int
    consecutive_losses: int
    largest_win: float
    largest_loss: float

@dataclass
class RiskMetrics:
    """Métricas específicas de riesgo"""
    symbol: str
    timestamp: datetime
    
    # Riesgo de mercado
    portfolio_value: float
    position_value: float
    exposure_pct: float
    leverage: float
    
    # Riesgo de concentración
    symbol_weight: float
    correlation_risk: float
    
    # Riesgo de liquidez
    avg_daily_volume: float
    position_to_volume_ratio: float
    
    # Métricas de stress
    stress_test_1d: float  # Pérdida en escenario 1 día
    stress_test_1w: float  # Pérdida en escenario 1 semana
    monte_carlo_var: float

@dataclass
class PerformanceComparison:
    """Comparación de rendimiento entre períodos"""
    symbol: str
    current_period: PerformanceMetrics
    previous_period: PerformanceMetrics
    benchmark_comparison: Optional[Dict[str, float]]
    
    # Cambios relativos
    return_change: float
    sharpe_change: float
    drawdown_change: float
    winrate_change: float
    
    # Ranking y percentiles
    symbol_ranking: Optional[int]
    performance_percentile: Optional[float]

class PerformanceTracker:
    """
    Tracker de rendimiento avanzado para el Trading Bot v10
    
    Calcula y mantiene métricas de rendimiento en tiempo real,
    análisis de riesgo y comparaciones de performance.
    """
    
    def __init__(self, data_provider=None):
        """
        Inicializa el tracker de rendimiento
        
        Args:
            data_provider: Proveedor de datos para integración
        """
        self.data_provider = data_provider
        
        # Estado del tracker
        self._active = False
        self._last_update = None
        self._calculation_thread = None
        
        # Configuración
        self.config = self._load_config()
        
        # Cache de métricas calculadas
        self.performance_cache = {}
        self.risk_cache = {}
        self.comparison_cache = {}
        
        # Buffers para cálculos en tiempo real
        self.returns_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.trades_buffer = defaultdict(lambda: deque(maxlen=500))
        self.price_buffer = defaultdict(lambda: deque(maxlen=1000))
        
        # Datos de benchmark (índices de referencia)
        self.benchmark_data = {}
        
        # Lock para thread safety
        self._lock = threading.RLock()
        
        # Estadísticas del tracker
        self.stats = {
            'calculations_performed': 0,
            'last_calculation_time': None,
            'calculation_duration': 0,
            'errors': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("PerformanceTracker inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración del tracker de rendimiento"""
        return {
            'update_interval': 300,  # 5 minutos
            'calculation_lookback_days': 90,
            'min_trades_for_metrics': 10,
            'risk_free_rate': 0.02,  # 2% anual
            'confidence_level': 0.95,
            'monte_carlo_simulations': 1000,
            'benchmark_symbols': ['SPY', 'BTC'],  # Benchmarks de referencia
            'cache_ttl': 600,  # 10 minutos
            'enable_advanced_metrics': SCIPY_AVAILABLE,
            'stress_test_scenarios': {
                'market_crash_1d': -0.10,  # -10% en 1 día
                'market_crash_1w': -0.20,  # -20% en 1 semana
                'volatility_spike': 3.0     # 3x volatilidad normal
            }
        }
    
    def start(self):
        """Inicia el tracker de rendimiento"""
        if self._active:
            logger.warning("PerformanceTracker ya está activo")
            return
        
        try:
            self._active = True
            
            # Inicializar datos de benchmark
            self._initialize_benchmarks()
            
            # Iniciar thread de cálculo
            self._calculation_thread = threading.Thread(
                target=self._calculation_worker, 
                daemon=True
            )
            self._calculation_thread.start()
            
            logger.info("PerformanceTracker iniciado correctamente")
            
        except Exception as e:
            self._active = False
            logger.error(f"Error al iniciar PerformanceTracker: {e}")
            raise
    
    def stop(self):
        """Detiene el tracker de rendimiento"""
        if not self._active:
            return
        
        logger.info("Deteniendo PerformanceTracker...")
        
        self._active = False
        
        # Esperar que el thread termine
        if self._calculation_thread and self._calculation_thread.is_alive():
            self._calculation_thread.join(timeout=10)
        
        logger.info("PerformanceTracker detenido")
    
    def is_active(self) -> bool:
        """Verifica si el tracker está activo"""
        return self._active
    
    def _calculation_worker(self):
        """Worker principal para cálculos de rendimiento"""
        while self._active:
            try:
                start_time = time.time()
                
                # Actualizar datos desde el proveedor
                self._update_data_buffers()
                
                # Calcular métricas para todos los símbolos
                self._calculate_all_metrics()
                
                # Actualizar comparaciones
                self._update_comparisons()
                
                # Limpiar cache antiguo
                self._cleanup_cache()
                
                # Estadísticas
                calculation_time = time.time() - start_time
                self.stats['calculations_performed'] += 1
                self.stats['last_calculation_time'] = datetime.now()
                self.stats['calculation_duration'] = calculation_time
                self._last_update = datetime.now()
                
                logger.debug(f"Cálculo de rendimiento completado en {calculation_time:.2f}s")
                
                time.sleep(self.config['update_interval'])
                
            except Exception as e:
                logger.error(f"Error en calculation worker: {e}")
                self.stats['errors'] += 1
                time.sleep(60)  # Esperar más tiempo en caso de error
        
        logger.info("Calculation worker detenido")
    
    def _initialize_benchmarks(self):
        """Inicializa datos de benchmarks de referencia"""
        try:
            # Aquí se cargarían datos reales de benchmarks
            # Por ahora generamos datos sintéticos
            benchmarks = self.config['benchmark_symbols']
            
            for benchmark in benchmarks:
                # Generar retornos sintéticos del benchmark
                returns = np.random.normal(0.0008, 0.02, 252)  # Retornos diarios anuales
                dates = pd.date_range(
                    start=datetime.now() - timedelta(days=365),
                    end=datetime.now(),
                    freq='D'
                )[:len(returns)]
                
                self.benchmark_data[benchmark] = pd.Series(returns, index=dates)
            
            logger.info(f"Benchmarks inicializados: {benchmarks}")
            
        except Exception as e:
            logger.error(f"Error al inicializar benchmarks: {e}")
    
    def _update_data_buffers(self):
        """Actualiza buffers de datos desde el proveedor"""
        if not self.data_provider:
            return
        
        try:
            symbols = self.data_provider.get_configured_symbols()
            
            for symbol in symbols:
                # Obtener trades recientes
                recent_trades = self.data_provider.get_recent_trades(symbol, 100)
                
                with self._lock:
                    self.trades_buffer[symbol].clear()
                    for trade in recent_trades:
                        self.trades_buffer[symbol].append(trade)
                
                # Calcular retornos desde trades
                if len(recent_trades) > 1:
                    returns = self._calculate_returns_from_trades(recent_trades)
                    self.returns_buffer[symbol].extend(returns)
                
                # Obtener precios históricos para cálculos avanzados
                historical_data = self.data_provider.get_historical_data(symbol, '1h', 168)  # Última semana
                if not historical_data.empty:
                    with self._lock:
                        self.price_buffer[symbol].clear()
                        for _, row in historical_data.iterrows():
                            self.price_buffer[symbol].append({
                                'timestamp': row.name,
                                'close': row.get('close', 0),
                                'volume': row.get('volume', 0)
                            })
                            
        except Exception as e:
            logger.error(f"Error al actualizar buffers de datos: {e}")
    
    def _calculate_all_metrics(self):
        """Calcula métricas para todos los símbolos configurados"""
        if not self.data_provider:
            return
        
        symbols = self.data_provider.get_configured_symbols()
        
        for symbol in symbols:
            try:
                # Calcular métricas de rendimiento
                performance_metrics = self._calculate_performance_metrics(symbol)
                if performance_metrics:
                    with self._lock:
                        self.performance_cache[symbol] = performance_metrics
                
                # Calcular métricas de riesgo
                risk_metrics = self._calculate_risk_metrics(symbol)
                if risk_metrics:
                    with self._lock:
                        self.risk_cache[symbol] = risk_metrics
                        
            except Exception as e:
                logger.error(f"Error al calcular métricas para {symbol}: {e}")
    
    def _calculate_performance_metrics(self, symbol: str) -> Optional[PerformanceMetrics]:
        """Calcula métricas de rendimiento para un símbolo"""
        try:
            with self._lock:
                trades = list(self.trades_buffer[symbol])
                returns = list(self.returns_buffer[symbol])
            
            if len(trades) < self.config['min_trades_for_metrics']:
                return None
            
            # Filtrar trades cerrados
            closed_trades = [t for t in trades if t.status == 'closed' and t.pnl is not None]
            if len(closed_trades) < self.config['min_trades_for_metrics']:
                return None
            
            # Calcular métricas básicas
            pnls = [t.pnl for t in closed_trades]
            returns_pct = [t.pnl_percentage for t in closed_trades if t.pnl_percentage is not None]
            
            if not pnls or not returns_pct:
                return None
            
            # Período de análisis
            period_start = min(t.entry_time for t in closed_trades)
            period_end = max(t.exit_time for t in closed_trades if t.exit_time)
            period_days = (period_end - period_start).days
            
            # Retorno total
            total_return = sum(pnls)
            total_return_pct = sum(returns_pct)
            
            # Retorno anualizado
            if period_days > 0:
                annualized_return = (total_return_pct / 100) * (365 / period_days) * 100
            else:
                annualized_return = 0
            
            # Volatilidad
            if len(returns_pct) > 1:
                volatility = np.std(returns_pct) * np.sqrt(252)  # Anualizada
            else:
                volatility = 0
            
            # Sharpe Ratio
            if volatility > 0:
                excess_return = annualized_return - self.config['risk_free_rate'] * 100
                sharpe_ratio = excess_return / volatility
            else:
                sharpe_ratio = 0
            
            # Sortino Ratio
            negative_returns = [r for r in returns_pct if r < 0]
            if negative_returns:
                downside_deviation = np.std(negative_returns) * np.sqrt(252)
                if downside_deviation > 0:
                    sortino_ratio = (annualized_return - self.config['risk_free_rate'] * 100) / downside_deviation
                else:
                    sortino_ratio = 0
            else:
                sortino_ratio = float('inf') if annualized_return > 0 else 0
            
            # Maximum Drawdown
            cumulative_returns = np.cumsum(returns_pct)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = running_max - cumulative_returns
            max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
            
            # Calmar Ratio
            if max_drawdown > 0:
                calmar_ratio = annualized_return / max_drawdown
            else:
                calmar_ratio = float('inf') if annualized_return > 0 else 0
            
            # Métricas de trading
            winning_trades = [p for p in pnls if p > 0]
            losing_trades = [p for p in pnls if p < 0]
            
            win_rate = (len(winning_trades) / len(pnls)) * 100 if pnls else 0
            avg_win = np.mean(winning_trades) if winning_trades else 0
            avg_loss = np.mean(losing_trades) if losing_trades else 0
            
            # Profit Factor
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Expectancy
            expectancy = (avg_win * win_rate / 100) + (avg_loss * (100 - win_rate) / 100)
            
            # Value at Risk
            var_95 = np.percentile(returns_pct, 5) if returns_pct else 0
            cvar_95 = np.mean([r for r in returns_pct if r <= var_95]) if returns_pct else 0
            
            # Métricas avanzadas (si SciPy está disponible)
            information_ratio = None
            treynor_ratio = None
            jensen_alpha = None
            tracking_error = None
            beta = None
            
            if self.config['enable_advanced_metrics'] and len(returns_pct) > 30:
                try:
                    # Calcular beta contra benchmark
                    benchmark_returns = self._get_benchmark_returns('BTC', period_start, period_end)
                    if benchmark_returns is not None and len(benchmark_returns) == len(returns_pct):
                        correlation_matrix = np.corrcoef(returns_pct, benchmark_returns)
                        correlation = correlation_matrix[0, 1]
                        beta = correlation * (np.std(returns_pct) / np.std(benchmark_returns))
                        
                        # Jensen's Alpha
                        benchmark_return = np.mean(benchmark_returns) * 252  # Anualizado
                        jensen_alpha = annualized_return - (self.config['risk_free_rate'] * 100 + 
                                                          beta * (benchmark_return - self.config['risk_free_rate'] * 100))
                        
                        # Treynor Ratio
                        if beta != 0:
                            treynor_ratio = (annualized_return - self.config['risk_free_rate'] * 100) / beta
                        
                        # Tracking Error
                        tracking_error = np.std(np.array(returns_pct) - np.array(benchmark_returns)) * np.sqrt(252)
                        
                        # Information Ratio
                        if tracking_error > 0:
                            information_ratio = (annualized_return - benchmark_return) / tracking_error
                            
                except Exception as e:
                    logger.debug(f"Error al calcular métricas avanzadas para {symbol}: {e}")
            
            # Ratios de consistencia
            win_loss_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else float('inf')
            
            # Rachas consecutivas
            consecutive_wins, consecutive_losses = self._calculate_consecutive_streaks(pnls)
            
            # Operaciones más grandes
            largest_win = max(pnls) if pnls else 0
            largest_loss = min(pnls) if pnls else 0
            
            # Duración del drawdown máximo
            max_dd_duration = self._calculate_max_drawdown_duration(cumulative_returns)
            
            return PerformanceMetrics(
                symbol=symbol,
                period_start=period_start,
                period_end=period_end,
                total_return=total_return,
                total_return_pct=total_return_pct,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                max_drawdown_duration=max_dd_duration,
                var_95=var_95,
                cvar_95=cvar_95,
                beta=beta,
                total_trades=len(closed_trades),
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                expectancy=expectancy,
                information_ratio=information_ratio,
                treynor_ratio=treynor_ratio,
                jensen_alpha=jensen_alpha,
                tracking_error=tracking_error,
                win_loss_ratio=win_loss_ratio,
                consecutive_wins=consecutive_wins,
                consecutive_losses=consecutive_losses,
                largest_win=largest_win,
                largest_loss=largest_loss
            )
            
        except Exception as e:
            logger.error(f"Error al calcular métricas de rendimiento para {symbol}: {e}")
            return None
    
    def _calculate_risk_metrics(self, symbol: str) -> Optional[RiskMetrics]:
        """Calcula métricas de riesgo para un símbolo"""
        try:
            if not self.data_provider:
                return None
            
            # Obtener métricas del símbolo
            symbol_metrics = self.data_provider.get_symbol_metrics(symbol)
            
            # Calcular métricas de riesgo
            portfolio_value = symbol_metrics.current_balance
            position_value = portfolio_value * 0.1  # Asumiendo 10% por posición
            exposure_pct = (position_value / portfolio_value) * 100
            
            # Leverage (simplificado)
            leverage = 1.0  # Sin leverage por defecto
            
            # Peso del símbolo en portfolio
            all_symbols = self.data_provider.get_configured_symbols()
            symbol_weight = 1.0 / len(all_symbols) * 100  # Distribución equitativa
            
            # Riesgo de correlación (simplificado)
            correlation_risk = self._calculate_correlation_risk(symbol)
            
            # Volumen promedio diario
            with self._lock:
                prices = list(self.price_buffer[symbol])
            
            if prices:
                volumes = [p['volume'] for p in prices[-24:]]  # Últimas 24 horas
                avg_daily_volume = np.mean(volumes) if volumes else 0
                position_to_volume_ratio = (position_value / avg_daily_volume) * 100 if avg_daily_volume > 0 else 0
            else:
                avg_daily_volume = 0
                position_to_volume_ratio = 0
            
            # Stress tests
            stress_1d = self._calculate_stress_test(symbol, '1d')
            stress_1w = self._calculate_stress_test(symbol, '1w')
            monte_carlo_var = self._calculate_monte_carlo_var(symbol)
            
            return RiskMetrics(
                symbol=symbol,
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                position_value=position_value,
                exposure_pct=exposure_pct,
                leverage=leverage,
                symbol_weight=symbol_weight,
                correlation_risk=correlation_risk,
                avg_daily_volume=avg_daily_volume,
                position_to_volume_ratio=position_to_volume_ratio,
                stress_test_1d=stress_1d,
                stress_test_1w=stress_1w,
                monte_carlo_var=monte_carlo_var
            )
            
        except Exception as e:
            logger.error(f"Error al calcular métricas de riesgo para {symbol}: {e}")
            return None
    
    def _calculate_returns_from_trades(self, trades: List) -> List[float]:
        """Calcula retornos porcentuales desde una lista de trades"""
        returns = []
        for trade in trades:
            if trade.status == 'closed' and trade.pnl_percentage is not None:
                returns.append(trade.pnl_percentage)
        return returns
    
    def _get_benchmark_returns(self, benchmark: str, start_date: datetime, end_date: datetime) -> Optional[List[float]]:
        """Obtiene retornos del benchmark para un período específico"""
        try:
            if benchmark not in self.benchmark_data:
                return None
            
            benchmark_series = self.benchmark_data[benchmark]
            period_data = benchmark_series[
                (benchmark_series.index >= start_date) & 
                (benchmark_series.index <= end_date)
            ]
            
            return period_data.tolist() if len(period_data) > 0 else None
            
        except Exception as e:
            logger.error(f"Error al obtener retornos del benchmark {benchmark}: {e}")
            return None
    
    def _calculate_consecutive_streaks(self, pnls: List[float]) -> Tuple[int, int]:
        """Calcula rachas consecutivas de ganancias y pérdidas"""
        if not pnls:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for pnl in pnls:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0
        
        return max_wins, max_losses
    
    def _calculate_max_drawdown_duration(self, cumulative_returns: np.ndarray) -> int:
        """Calcula la duración del drawdown máximo en días"""
        if len(cumulative_returns) == 0:
            return 0
        
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        
        # Encontrar el período del drawdown máximo
        max_dd_end = np.argmax(drawdowns)
        max_dd_start = np.argmax(cumulative_returns[:max_dd_end + 1])
        
        return max_dd_end - max_dd_start
    
    def _calculate_correlation_risk(self, symbol: str) -> float:
        """Calcula el riesgo de correlación simplificado"""
        try:
            # Simplificado: retorna un valor base según volatilidad histórica
            with self._lock:
                returns = list(self.returns_buffer[symbol])
            
            if len(returns) > 10:
                volatility = np.std(returns)
                # Riesgo de correlación basado en volatilidad
                return min(volatility * 10, 100)  # Máximo 100%
            else:
                return 20  # Valor por defecto
                
        except Exception:
            return 20
    
    def _calculate_stress_test(self, symbol: str, scenario: str) -> float:
        """Calcula pérdida en escenario de stress"""
        try:
            if not self.data_provider:
                return 0
            
            symbol_metrics = self.data_provider.get_symbol_metrics(symbol)
            position_value = symbol_metrics.current_balance * 0.1  # 10% del balance
            
            if scenario == '1d':
                stress_factor = self.config['stress_test_scenarios']['market_crash_1d']
            elif scenario == '1w':
                stress_factor = self.config['stress_test_scenarios']['market_crash_1w']
            else:
                stress_factor = -0.05  # -5% por defecto
            
            return position_value * abs(stress_factor)
            
        except Exception:
            return 0
    
    def _calculate_monte_carlo_var(self, symbol: str) -> float:
        """Calcula VaR usando simulación Monte Carlo"""
        try:
            with self._lock:
                returns = list(self.returns_buffer[symbol])
            
            if len(returns) < 30:
                return 0
            
            # Parámetros históricos
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Simulación Monte Carlo
            simulations = self.config['monte_carlo_simulations']
            simulated_returns = np.random.normal(mean_return, std_return, simulations)
            
            # VaR al 95%
            var_95 = np.percentile(simulated_returns, 5)
            
            # Convertir a valor monetario
            if self.data_provider:
                symbol_metrics = self.data_provider.get_symbol_metrics(symbol)
                position_value = symbol_metrics.current_balance * 0.1
                return abs(var_95 * position_value / 100)
            
            return abs(var_95)
            
        except Exception as e:
            logger.debug(f"Error en Monte Carlo VaR para {symbol}: {e}")
            return 0
    
    def _update_comparisons(self):
        """Actualiza comparaciones de rendimiento entre períodos"""
        try:
            for symbol in self.performance_cache.keys():
                # Aquí se implementaría la lógica de comparación temporal
                # Por ahora mantenemos un placeholder
                pass
                
        except Exception as e:
            logger.error(f"Error al actualizar comparaciones: {e}")
    
    def _cleanup_cache(self):
        """Limpia cache antiguo"""
        try:
            current_time = time.time()
            ttl = self.config['cache_ttl']
            
            # Implementar lógica de limpieza si es necesario
            # Por ahora el cache se mantiene hasta próxima actualización
            
        except Exception as e:
            logger.error(f"Error al limpiar cache: {e}")
    
    # API pública
    def get_performance_metrics(self, symbol: str) -> Optional[PerformanceMetrics]:
        """Obtiene métricas de rendimiento para un símbolo"""
        with self._lock:
            metrics = self.performance_cache.get(symbol)
            if metrics:
                self.stats['cache_hits'] += 1
            else:
                self.stats['cache_misses'] += 1
            return metrics
    
    def get_risk_metrics(self, symbol: str) -> Optional[RiskMetrics]:
        """Obtiene métricas de riesgo para un símbolo"""
        with self._lock:
            return self.risk_cache.get(symbol)
    
    def get_all_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Obtiene métricas de rendimiento para todos los símbolos"""
        with self._lock:
            return self.performance_cache.copy()
    
    def get_all_risk_metrics(self) -> Dict[str, RiskMetrics]:
        """Obtiene métricas de riesgo para todos los símbolos"""
        with self._lock:
            return self.risk_cache.copy()
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Obtiene resumen consolidado del portfolio"""
        try:
            if not self.data_provider:
                return {}
            
            symbols = self.data_provider.get_configured_symbols()
            portfolio_metrics = {
                'total_symbols': len(symbols),
                'total_value': 0,
                'total_pnl': 0,
                'avg_sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'risk_score': 0,
                'symbols_performance': {}
            }
            
            sharpe_ratios = []
            win_rates = []
            drawdowns = []
            
            for symbol in symbols:
                perf_metrics = self.get_performance_metrics(symbol)
                risk_metrics = self.get_risk_metrics(symbol)
                
                if perf_metrics:
                    portfolio_metrics['total_pnl'] += perf_metrics.total_return
                    sharpe_ratios.append(perf_metrics.sharpe_ratio)
                    win_rates.append(perf_metrics.win_rate)
                    drawdowns.append(perf_metrics.max_drawdown)
                    
                    portfolio_metrics['symbols_performance'][symbol] = {
                        'return': perf_metrics.total_return,
                        'return_pct': perf_metrics.total_return_pct,
                        'sharpe': perf_metrics.sharpe_ratio,
                        'win_rate': perf_metrics.win_rate,
                        'trades': perf_metrics.total_trades
                    }
                
                if risk_metrics:
                    portfolio_metrics['total_value'] += risk_metrics.portfolio_value
            
            # Promedios del portfolio
            if sharpe_ratios:
                portfolio_metrics['avg_sharpe_ratio'] = np.mean(sharpe_ratios)
            if win_rates:
                portfolio_metrics['win_rate'] = np.mean(win_rates)
            if drawdowns:
                portfolio_metrics['max_drawdown'] = max(drawdowns)
            
            # Score de riesgo consolidado (0-100)
            portfolio_metrics['risk_score'] = self._calculate_portfolio_risk_score()
            
            return portfolio_metrics
            
        except Exception as e:
            logger.error(f"Error al obtener resumen del portfolio: {e}")
            return {}
    
    def get_top_performers(self, metric: str = 'sharpe_ratio', limit: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene los mejores performers según una métrica específica
        
        Args:
            metric (str): Métrica para ranking ('sharpe_ratio', 'total_return', 'win_rate', etc.)
            limit (int): Número máximo de resultados
            
        Returns:
            List[Dict]: Lista de símbolos ordenados por rendimiento
        """
        try:
            performers = []
            
            with self._lock:
                for symbol, metrics in self.performance_cache.items():
                    if hasattr(metrics, metric):
                        value = getattr(metrics, metric)
                        performers.append({
                            'symbol': symbol,
                            'metric_value': value,
                            'total_return': metrics.total_return,
                            'win_rate': metrics.win_rate,
                            'sharpe_ratio': metrics.sharpe_ratio,
                            'total_trades': metrics.total_trades
                        })
            
            # Ordenar por métrica descendente
            performers.sort(key=lambda x: x['metric_value'], reverse=True)
            
            return performers[:limit]
            
        except Exception as e:
            logger.error(f"Error al obtener top performers: {e}")
            return []
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Genera reporte consolidado de riesgo"""
        try:
            risk_report = {
                'timestamp': datetime.now(),
                'overall_risk_level': 'Medium',  # Low, Medium, High
                'total_exposure': 0,
                'concentration_risk': {},
                'correlation_risks': {},
                'stress_test_results': {},
                'recommendations': []
            }
            
            total_portfolio_value = 0
            exposures = []
            correlations = []
            
            with self._lock:
                for symbol, risk_metrics in self.risk_cache.items():
                    total_portfolio_value += risk_metrics.portfolio_value
                    exposures.append(risk_metrics.exposure_pct)
                    correlations.append(risk_metrics.correlation_risk)
                    
                    # Stress test consolidado
                    risk_report['stress_test_results'][symbol] = {
                        'stress_1d': risk_metrics.stress_test_1d,
                        'stress_1w': risk_metrics.stress_test_1w,
                        'monte_carlo_var': risk_metrics.monte_carlo_var
                    }
            
            # Exposición total
            risk_report['total_exposure'] = sum(exposures)
            
            # Nivel de riesgo general
            avg_correlation = np.mean(correlations) if correlations else 0
            max_exposure = max(exposures) if exposures else 0
            
            if max_exposure > 50 or avg_correlation > 70:
                risk_report['overall_risk_level'] = 'High'
            elif max_exposure > 30 or avg_correlation > 50:
                risk_report['overall_risk_level'] = 'Medium'
            else:
                risk_report['overall_risk_level'] = 'Low'
            
            # Recomendaciones automáticas
            risk_report['recommendations'] = self._generate_risk_recommendations(risk_report)
            
            return risk_report
            
        except Exception as e:
            logger.error(f"Error al generar reporte de riesgo: {e}")
            return {}
    
    def _calculate_portfolio_risk_score(self) -> float:
        """Calcula score de riesgo del portfolio (0-100)"""
        try:
            risk_factors = []
            
            with self._lock:
                for symbol, risk_metrics in self.risk_cache.items():
                    # Factores de riesgo individuales
                    exposure_risk = min(risk_metrics.exposure_pct / 20 * 100, 100)  # 20% = 100% riesgo
                    correlation_risk = risk_metrics.correlation_risk
                    liquidity_risk = min(risk_metrics.position_to_volume_ratio, 100)
                    
                    symbol_risk = (exposure_risk + correlation_risk + liquidity_risk) / 3
                    risk_factors.append(symbol_risk)
            
            if risk_factors:
                return np.mean(risk_factors)
            else:
                return 50  # Riesgo medio por defecto
                
        except Exception:
            return 50
    
    def _generate_risk_recommendations(self, risk_report: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones automáticas de gestión de riesgo"""
        recommendations = []
        
        try:
            # Análisis de exposición
            if risk_report['total_exposure'] > 80:
                recommendations.append("⚠️ Exposición total muy alta. Considere reducir posiciones.")
            elif risk_report['total_exposure'] > 60:
                recommendations.append("📊 Exposición moderada-alta. Monitoree posiciones activamente.")
            
            # Análisis de correlación
            high_correlation_symbols = []
            for symbol, risk_metrics in self.risk_cache.items():
                if risk_metrics.correlation_risk > 70:
                    high_correlation_symbols.append(symbol)
            
            if high_correlation_symbols:
                recommendations.append(f"🔗 Alta correlación detectada en: {', '.join(high_correlation_symbols)}")
            
            # Análisis de stress tests
            high_stress_symbols = []
            for symbol, stress_results in risk_report['stress_test_results'].items():
                if stress_results['monte_carlo_var'] > 1000:  # Valor ejemplo
                    high_stress_symbols.append(symbol)
            
            if high_stress_symbols:
                recommendations.append(f"💥 Alto riesgo de stress en: {', '.join(high_stress_symbols)}")
            
            # Recomendaciones generales
            if risk_report['overall_risk_level'] == 'High':
                recommendations.append("🚨 Nivel de riesgo alto. Revise estrategia de gestión de riesgo.")
            elif risk_report['overall_risk_level'] == 'Low':
                recommendations.append("✅ Nivel de riesgo bajo. Portfolio bien diversificado.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error al generar recomendaciones: {e}")
            return ["Error al generar recomendaciones automáticas"]
    
    def calculate_optimal_position_size(self, symbol: str, risk_tolerance: float = 0.02) -> Dict[str, float]:
        """
        Calcula tamaño óptimo de posición usando Kelly Criterion
        
        Args:
            symbol (str): Símbolo a analizar
            risk_tolerance (float): Tolerancia al riesgo (2% por defecto)
            
        Returns:
            Dict[str, float]: Recomendaciones de tamaño de posición
        """
        try:
            perf_metrics = self.get_performance_metrics(symbol)
            if not perf_metrics:
                return {'kelly_percentage': 0, 'recommended_size': 0, 'max_safe_size': 0}
            
            # Kelly Criterion: f = (bp - q) / b
            # donde b = avg_win/avg_loss, p = win_rate/100, q = 1-p
            
            if perf_metrics.avg_loss == 0 or perf_metrics.win_rate == 0:
                return {'kelly_percentage': 0, 'recommended_size': 0, 'max_safe_size': 0}
            
            b = abs(perf_metrics.avg_win / perf_metrics.avg_loss)
            p = perf_metrics.win_rate / 100
            q = 1 - p
            
            kelly_f = (b * p - q) / b
            kelly_percentage = max(0, min(kelly_f * 100, 25))  # Máximo 25%
            
            # Ajustar por volatilidad
            volatility_adjustment = 1 - (perf_metrics.volatility / 100)
            adjusted_kelly = kelly_percentage * volatility_adjustment
            
            # Tamaño recomendado basado en tolerancia al riesgo
            recommended_size = min(adjusted_kelly, risk_tolerance * 100)
            
            # Tamaño máximo seguro (50% del Kelly)
            max_safe_size = kelly_percentage * 0.5
            
            return {
                'kelly_percentage': round(kelly_percentage, 2),
                'recommended_size': round(recommended_size, 2),
                'max_safe_size': round(max_safe_size, 2),
                'volatility_adjusted': round(adjusted_kelly, 2)
            }
            
        except Exception as e:
            logger.error(f"Error al calcular tamaño óptimo para {symbol}: {e}")
            return {'kelly_percentage': 0, 'recommended_size': 0, 'max_safe_size': 0}
    
    def get_performance_attribution(self, symbol: str) -> Dict[str, Any]:
        """Análisis de atribución de rendimiento"""
        try:
            perf_metrics = self.get_performance_metrics(symbol)
            if not perf_metrics:
                return {}
            
            attribution = {
                'symbol': symbol,
                'period': {
                    'start': perf_metrics.period_start,
                    'end': perf_metrics.period_end,
                    'days': (perf_metrics.period_end - perf_metrics.period_start).days
                },
                'returns_breakdown': {
                    'total_return': perf_metrics.total_return,
                    'annualized_return': perf_metrics.annualized_return,
                    'risk_adjusted_return': perf_metrics.sharpe_ratio,
                    'downside_adjusted_return': perf_metrics.sortino_ratio
                },
                'risk_contribution': {
                    'volatility': perf_metrics.volatility,
                    'max_drawdown': perf_metrics.max_drawdown,
                    'var_95': perf_metrics.var_95,
                    'cvar_95': perf_metrics.cvar_95
                },
                'trading_efficiency': {
                    'win_rate': perf_metrics.win_rate,
                    'profit_factor': perf_metrics.profit_factor,
                    'expectancy': perf_metrics.expectancy,
                    'avg_trade_return': perf_metrics.total_return / perf_metrics.total_trades if perf_metrics.total_trades > 0 else 0
                },
                'consistency_metrics': {
                    'consecutive_wins': perf_metrics.consecutive_wins,
                    'consecutive_losses': perf_metrics.consecutive_losses,
                    'win_loss_ratio': perf_metrics.win_loss_ratio,
                    'largest_win': perf_metrics.largest_win,
                    'largest_loss': perf_metrics.largest_loss
                }
            }
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error en análisis de atribución para {symbol}: {e}")
            return {}
    
    def export_performance_report(self, format_type: str = 'json') -> str:
        """
        Exporta reporte completo de rendimiento
        
        Args:
            format_type (str): Formato de exportación ('json', 'csv')
            
        Returns:
            str: Ruta del archivo exportado
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Recopilar todos los datos
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'portfolio_summary': self.get_portfolio_summary(),
                'risk_report': self.get_risk_report(),
                'performance_metrics': {},
                'risk_metrics': {},
                'top_performers': self.get_top_performers(),
                'system_stats': self.get_stats()
            }
            
            # Añadir métricas por símbolo
            with self._lock:
                for symbol, metrics in self.performance_cache.items():
                    report_data['performance_metrics'][symbol] = asdict(metrics)
                
                for symbol, metrics in self.risk_cache.items():
                    report_data['risk_metrics'][symbol] = asdict(metrics)
            
            # Exportar según formato
            output_dir = Path('logs/performance_reports')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == 'json':
                filename = f'performance_report_{timestamp}.json'
                filepath = output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, default=str)
                    
            elif format_type.lower() == 'csv':
                filename = f'performance_report_{timestamp}.csv'
                filepath = output_dir / filename
                
                # Convertir a DataFrame para CSV
                df_data = []
                for symbol, metrics in report_data['performance_metrics'].items():
                    row = {'symbol': symbol}
                    row.update(metrics)
                    df_data.append(row)
                
                df = pd.DataFrame(df_data)
                df.to_csv(filepath, index=False)
            
            logger.info(f"Reporte de rendimiento exportado: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error al exportar reporte: {e}")
            return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del PerformanceTracker"""
        return {
            'is_active': self._active,
            'last_update': self._last_update,
            'calculations_performed': self.stats['calculations_performed'],
            'last_calculation_time': self.stats['last_calculation_time'],
            'calculation_duration': self.stats['calculation_duration'],
            'errors': self.stats['errors'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cached_symbols': len(self.performance_cache),
            'scipy_available': SCIPY_AVAILABLE,
            'advanced_metrics_enabled': self.config['enable_advanced_metrics']
        }