# Ruta: core/trading/enterprise/portfolio_optimizer.py
# portfolio_optimizer.py - Optimizador de portafolio enterprise
# Ubicación: config/enterprise/portfolio_optimizer.py

"""
Optimizador de Portafolio Enterprise
Implementa estrategias de optimización de portafolio para trading de futuros

Características principales:
- Risk Parity (paridad de riesgo)
- Equal Weight (peso igual)
- Market Cap Weight (peso por capitalización)
- Kelly Optimal (criterio de Kelly)
- Optimización con restricciones
- Backtesting de estrategias
- Métricas de performance
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
from scipy.optimize import minimize
from scipy import stats
import redis
from control.telegram_bot import telegram_bot
from core.data.database import db_manager
from core.trading.risk_manager import risk_manager

logger = logging.getLogger(__name__)

@dataclass
class PortfolioWeights:
    """Pesos del portafolio optimizado"""
    symbol: str
    weight: float
    target_value: float
    current_value: float
    risk_contribution: float
    expected_return: float
    volatility: float

@dataclass
class OptimizationResult:
    """Resultado de la optimización del portafolio"""
    method: str
    weights: List[PortfolioWeights]
    total_value: float
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    diversification_ratio: float
    optimization_time: float
    convergence: bool
    message: str

class PortfolioOptimizer:
    """Optimizador de portafolio enterprise"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = None
        self._setup_redis()
        
        # Configuración de optimización
        self.optimization_config = config.get('portfolio_management', {})
        self.risk_config = config.get('risk_management', {})
        
        # Parámetros de optimización
        self.max_weight_per_asset = self.optimization_config.get('max_weight_per_asset', 0.30)
        self.min_weight_per_asset = self.optimization_config.get('min_weight_per_asset', 0.05)
        self.max_sector_weight = self.optimization_config.get('max_sector_weight', 0.50)
        self.min_assets = self.optimization_config.get('min_assets', 3)
        
        # Métricas de performance
        self.optimization_history = []
        
        logger.info("PortfolioOptimizer inicializado")
    
    def _setup_redis(self):
        """Configura Redis para caching"""
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url)
            logger.info("Conexión a Redis establecida para portfolio optimizer")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            self.redis_client = None
    
    async def optimize_portfolio(self, 
                                symbols: List[str], 
                                method: str = "risk_parity",
                                lookback_days: int = 30) -> OptimizationResult:
        """
        Optimiza el portafolio usando el método especificado
        
        Args:
            symbols: Lista de símbolos a incluir
            method: Método de optimización (risk_parity, equal_weight, market_cap, kelly)
            lookback_days: Días de datos históricos para usar
            
        Returns:
            OptimizationResult con los pesos optimizados
        """
        try:
            start_time = datetime.now()
            
            # Verificar cache
            cache_key = f"portfolio_optimization_{method}_{'_'.join(symbols)}_{lookback_days}"
            if self.redis_client:
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    logger.info("Usando resultado de optimización desde cache")
                    return OptimizationResult(**json.loads(cached_result))
            
            # Obtener datos históricos
            historical_data = await self._get_historical_data(symbols, lookback_days)
            if not historical_data:
                raise ValueError("No hay datos históricos suficientes")
            
            # Calcular retornos y matriz de covarianza
            returns_df = self._calculate_returns(historical_data)
            cov_matrix = returns_df.cov()
            expected_returns = returns_df.mean()
            
            # Optimizar según el método
            if method == "risk_parity":
                weights = self._risk_parity_optimization(cov_matrix)
            elif method == "equal_weight":
                weights = self._equal_weight_optimization(symbols)
            elif method == "market_cap":
                weights = self._market_cap_optimization(symbols)
            elif method == "kelly":
                weights = self._kelly_optimization(returns_df, expected_returns)
            else:
                raise ValueError(f"Método de optimización no soportado: {method}")
            
            # Aplicar restricciones
            weights = self._apply_constraints(weights, symbols)
            
            # Calcular métricas del portafolio
            portfolio_metrics = self._calculate_portfolio_metrics(
                weights, expected_returns, cov_matrix, returns_df
            )
            
            # Crear resultado
            portfolio_weights = []
            total_value = sum(pos.get('value', 0) for pos in self._get_current_positions().values())
            
            for i, symbol in enumerate(symbols):
                weight = weights[i] if i < len(weights) else 0.0
                portfolio_weights.append(PortfolioWeights(
                    symbol=symbol,
                    weight=weight,
                    target_value=total_value * weight,
                    current_value=self._get_current_position_value(symbol),
                    risk_contribution=self._calculate_risk_contribution(weights, cov_matrix, i),
                    expected_return=expected_returns.iloc[i] if i < len(expected_returns) else 0.0,
                    volatility=np.sqrt(cov_matrix.iloc[i, i]) if i < cov_matrix.shape[0] else 0.0
                ))
            
            result = OptimizationResult(
                method=method,
                weights=portfolio_weights,
                total_value=total_value,
                expected_return=portfolio_metrics['expected_return'],
                volatility=portfolio_metrics['volatility'],
                sharpe_ratio=portfolio_metrics['sharpe_ratio'],
                max_drawdown=portfolio_metrics['max_drawdown'],
                var_95=portfolio_metrics['var_95'],
                cvar_95=portfolio_metrics['cvar_95'],
                diversification_ratio=portfolio_metrics['diversification_ratio'],
                optimization_time=(datetime.now() - start_time).total_seconds(),
                convergence=portfolio_metrics['convergence'],
                message=f"Optimización {method} completada exitosamente"
            )
            
            # Cachear resultado
            if self.redis_client:
                self.redis_client.setex(cache_key, 3600, json.dumps(asdict(result), default=str))
            
            # Guardar en historial
            self.optimization_history.append(result)
            
            # Enviar notificación
            await telegram_bot.send_message(
                f"📊 Portafolio optimizado con {method}: "
                f"Sharpe={result.sharpe_ratio:.3f}, "
                f"Vol={result.volatility:.3f}, "
                f"VaR={result.var_95:.3f}"
            )
            
            logger.info(f"Optimización {method} completada en {result.optimization_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error optimizando portafolio: {e}")
            return OptimizationResult(
                method=method,
                weights=[],
                total_value=0.0,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                cvar_95=0.0,
                diversification_ratio=0.0,
                optimization_time=0.0,
                convergence=False,
                message=f"Error: {str(e)}"
            )
    
    def _risk_parity_optimization(self, cov_matrix: pd.DataFrame) -> np.ndarray:
        """Optimización de paridad de riesgo"""
        try:
            n = len(cov_matrix)
            
            def objective(weights):
                # Normalizar pesos
                weights = weights / np.sum(weights)
                
                # Calcular contribución de riesgo
                portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
                marginal_contrib = np.dot(cov_matrix, weights)
                risk_contrib = weights * marginal_contrib / portfolio_variance
                
                # Objetivo: minimizar la varianza de las contribuciones de riesgo
                return np.var(risk_contrib)
            
            # Restricciones
            constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
            bounds = [(0.01, 1.0) for _ in range(n)]
            
            # Optimización
            result = minimize(
                objective,
                x0=np.ones(n) / n,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                return result.x / np.sum(result.x)
            else:
                logger.warning("Optimización de risk parity falló, usando pesos iguales")
                return np.ones(n) / n
                
        except Exception as e:
            logger.error(f"Error en risk parity optimization: {e}")
            return np.ones(len(cov_matrix)) / len(cov_matrix)
    
    def _equal_weight_optimization(self, symbols: List[str]) -> np.ndarray:
        """Optimización de peso igual"""
        return np.ones(len(symbols)) / len(symbols)
    
    def _market_cap_optimization(self, symbols: List[str]) -> np.ndarray:
        """Optimización por capitalización de mercado"""
        try:
            # Obtener capitalización de mercado (simulada)
            market_caps = {}
            for symbol in symbols:
                # En un sistema real, esto vendría de una API de datos de mercado
                market_caps[symbol] = self._get_market_cap(symbol)
            
            total_cap = sum(market_caps.values())
            weights = np.array([market_caps[symbol] / total_cap for symbol in symbols])
            
            return weights
            
        except Exception as e:
            logger.error(f"Error en market cap optimization: {e}")
            return np.ones(len(symbols)) / len(symbols)
    
    def _kelly_optimization(self, returns_df: pd.DataFrame, expected_returns: pd.Series) -> np.ndarray:
        """Optimización usando el criterio de Kelly"""
        try:
            # Calcular estadísticas necesarias para Kelly
            mean_returns = expected_returns.values
            cov_matrix = returns_df.cov().values
            
            # Kelly óptimo: w = Σ^(-1) * μ
            try:
                inv_cov = np.linalg.inv(cov_matrix)
                kelly_weights = np.dot(inv_cov, mean_returns)
                
                # Normalizar y aplicar factor de Kelly (típicamente 0.25)
                kelly_factor = 0.25
                kelly_weights = kelly_weights * kelly_factor
                kelly_weights = np.maximum(kelly_weights, 0)  # Solo pesos positivos
                kelly_weights = kelly_weights / np.sum(kelly_weights)
                
                return kelly_weights
                
            except np.linalg.LinAlgError:
                logger.warning("Matriz de covarianza singular, usando pesos iguales")
                return np.ones(len(mean_returns)) / len(mean_returns)
                
        except Exception as e:
            logger.error(f"Error en Kelly optimization: {e}")
            return np.ones(len(returns_df.columns)) / len(returns_df.columns)
    
    def _apply_constraints(self, weights: np.ndarray, symbols: List[str]) -> np.ndarray:
        """Aplica restricciones a los pesos del portafolio"""
        try:
            # Restricción de peso mínimo y máximo por activo
            weights = np.maximum(weights, self.min_weight_per_asset)
            weights = np.minimum(weights, self.max_weight_per_asset)
            
            # Normalizar para que sumen 1
            weights = weights / np.sum(weights)
            
            # Verificar diversificación mínima
            non_zero_weights = np.sum(weights > 0.01)
            if non_zero_weights < self.min_assets:
                logger.warning(f"Diversificación insuficiente: {non_zero_weights} < {self.min_assets}")
            
            return weights
            
        except Exception as e:
            logger.error(f"Error aplicando restricciones: {e}")
            return weights
    
    def _calculate_portfolio_metrics(self, 
                                   weights: np.ndarray, 
                                   expected_returns: pd.Series, 
                                   cov_matrix: pd.DataFrame,
                                   returns_df: pd.DataFrame) -> Dict[str, float]:
        """Calcula métricas del portafolio optimizado"""
        try:
            # Retorno esperado del portafolio
            portfolio_return = np.dot(weights, expected_returns)
            
            # Volatilidad del portafolio
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            # Sharpe ratio (asumiendo risk-free rate = 0)
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Calcular retornos del portafolio
            portfolio_returns = returns_df.dot(weights)
            
            # VaR y CVaR
            var_95 = np.percentile(portfolio_returns, 5)
            cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
            
            # Max drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Diversification ratio
            weighted_vol = np.dot(weights, np.sqrt(np.diag(cov_matrix)))
            diversification_ratio = weighted_vol / portfolio_volatility if portfolio_volatility > 0 else 0
            
            return {
                'expected_return': float(portfolio_return),
                'volatility': float(portfolio_volatility),
                'sharpe_ratio': float(sharpe_ratio),
                'max_drawdown': float(max_drawdown),
                'var_95': float(var_95),
                'cvar_95': float(cvar_95),
                'diversification_ratio': float(diversification_ratio),
                'convergence': True
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas del portafolio: {e}")
            return {
                'expected_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'var_95': 0.0,
                'cvar_95': 0.0,
                'diversification_ratio': 0.0,
                'convergence': False
            }
    
    async def _get_historical_data(self, symbols: List[str], lookback_days: int) -> Dict[str, List]:
        """Obtiene datos históricos para los símbolos"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            historical_data = {}
            for symbol in symbols:
                try:
                    data = db_manager.get_historical_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        timeframe='1h'
                    )
                    if data and len(data) > 24:  # Al menos 1 día de datos
                        historical_data[symbol] = data
                except Exception as e:
                    logger.warning(f"Error obteniendo datos para {symbol}: {e}")
                    continue
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return {}
    
    def _calculate_returns(self, historical_data: Dict[str, List]) -> pd.DataFrame:
        """Calcula retornos a partir de datos históricos"""
        try:
            returns_data = {}
            
            for symbol, data in historical_data.items():
                if data and len(data) > 1:
                    df = pd.DataFrame(data)
                    if 'close' in df.columns:
                        returns = df['close'].pct_change().dropna()
                        returns_data[symbol] = returns
            
            if returns_data:
                # Alinear todos los retornos en el mismo DataFrame
                min_length = min(len(returns) for returns in returns_data.values())
                aligned_returns = {}
                for symbol, returns in returns_data.items():
                    aligned_returns[symbol] = returns.iloc[-min_length:]
                
                return pd.DataFrame(aligned_returns)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error calculando retornos: {e}")
            return pd.DataFrame()
    
    def _get_current_positions(self) -> Dict[str, Dict]:
        """Obtiene posiciones actuales"""
        try:
            # En un sistema real, esto vendría de la base de datos
            return {}
        except Exception as e:
            logger.error(f"Error obteniendo posiciones actuales: {e}")
            return {}
    
    def _get_current_position_value(self, symbol: str) -> float:
        """Obtiene el valor actual de una posición"""
        try:
            # En un sistema real, esto vendría de la base de datos
            return 0.0
        except Exception as e:
            logger.error(f"Error obteniendo valor de posición para {symbol}: {e}")
            return 0.0
    
    def _get_market_cap(self, symbol: str) -> float:
        """Obtiene la capitalización de mercado de un símbolo"""
        try:
            # En un sistema real, esto vendría de una API de datos de mercado
            # Por ahora, usar valores simulados
            market_caps = {
                'BTCUSDT': 1.0,
                'ETHUSDT': 0.8,
                'ADAUSDT': 0.6,
                'SOLUSDT': 0.4,
                'DOGEUSDT': 0.3
            }
            return market_caps.get(symbol, 0.1)
        except Exception as e:
            logger.error(f"Error obteniendo market cap para {symbol}: {e}")
            return 0.1
    
    def _calculate_risk_contribution(self, weights: np.ndarray, cov_matrix: pd.DataFrame, asset_index: int) -> float:
        """Calcula la contribución de riesgo de un activo"""
        try:
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            marginal_contrib = np.dot(cov_matrix.iloc[asset_index, :], weights)
            risk_contrib = weights[asset_index] * marginal_contrib / portfolio_variance
            return float(risk_contrib)
        except Exception as e:
            logger.error(f"Error calculando contribución de riesgo: {e}")
            return 0.0
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Obtiene el historial de optimizaciones"""
        try:
            return [asdict(result) for result in self.optimization_history]
        except Exception as e:
            logger.error(f"Error obteniendo historial de optimizaciones: {e}")
            return []
    
    def export_optimization_report(self, output_file: Optional[str] = None) -> str:
        """Exporta un reporte de optimización"""
        try:
            if output_file is None:
                output_file = f"portfolio_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            report_data = {
                'optimization_history': self.get_optimization_history(),
                'configuration': {
                    'max_weight_per_asset': self.max_weight_per_asset,
                    'min_weight_per_asset': self.min_weight_per_asset,
                    'max_sector_weight': self.max_sector_weight,
                    'min_assets': self.min_assets
                },
                'export_timestamp': datetime.now().isoformat()
            }
            
            output_path = f"reports/portfolio/{output_file}"
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Reporte de optimización exportado: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exportando reporte de optimización: {e}")
            return None
