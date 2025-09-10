# Ruta: core/trading/risk_manager.py
"""
trading/risk_manager.py
Sistema de gestión de riesgo para trading (LONG/SHORT, spot/futures)

Mejoras:
- Awareness de side (BUY/LONG y SELL/SHORT)
- Rounding por símbolo (lotStep/tickSize) y chequeo de minNotional
- Leverage derivado de config y límites de exposición/margen
- Buffer por comisiones ida+vuelta
- Límite diario y drawdown con peak_equity in-memory (y BD si está disponible)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext
from scipy import stats

from config.config_loader import user_config
from core.data.database import db_manager

logger = logging.getLogger(__name__)
getcontext().prec = 28  # evitar problemas de precisión en Decimal


@dataclass
class RiskDecision:
    """Decisión de riesgo calculada para una operación"""
    size_qty: float
    stop_loss: float
    take_profit: float
    leverage: float
    max_position_value: float
    risk_amount: float
    risk_percentage: float
    trailing_config: Optional[Dict] = None


class RiskManager:
    """Gestor de riesgo para operaciones de trading"""

    def __init__(self):
        self.config = user_config

        self.risk_config = self.config.get_value(["risk_management"], {})
        self.trading_config = self.config.get_value(["trading"], {})
        self.symbol = self.trading_config.get("symbol", "BTCUSDT")

        # Símbolo / filtros
        sym_cfg = self.config.get_value(["symbols", self.symbol], {})
        filters = (sym_cfg or {}).get("filters", {})
        self.min_notional = float(filters.get("minNotional", 5.0))
        self.lot_step = float(filters.get("lotStep", 0.0001))
        self.tick_size = float(filters.get("tickSize", 0.01))

        # Límites de riesgo
        self.max_risk_per_trade = float(self.risk_config.get("max_risk_per_trade", 0.02))  # 2%
        self.max_daily_loss_pct = float(self.risk_config.get("max_daily_loss_pct", 0.05))  # 5%
        self.max_drawdown_pct = float(self.risk_config.get("max_drawdown_pct", 0.10))      # 10%
        self.max_leverage = float(self.risk_config.get("max_leverage", 3.0))               # ≤3x
        self.max_exposure_pct = float(self.risk_config.get("max_exposure_pct", 0.50))      # 50% del balance

        # SL/TP por defecto
        self.default_sl_pct = float(self.risk_config.get("default_sl_pct", 0.02))          # 2%
        self.tp_r_multiple = float(self.risk_config.get("tp_r_multiple", 2.0))             # TP = 2R

        # Volatilidad → ajuste por ATR
        self.min_sl_atr_mult = float(self.risk_config.get("min_sl_atr_mult", 0.0))         # ej. 1.0 → SL >= 1*ATR
        self.atr_target_fraction = float(self.risk_config.get("atr_target_fraction", 0.5)) # 50% del rango relativo

        # Confianza
        self.min_signal_conf = float(self.risk_config.get("min_signal_confidence", 0.5))
        self.confidence_risk_gamma = float(self.risk_config.get("confidence_risk_gamma", 1.0))

        # Fees ida+vuelta
        fee_maker = float(self.trading_config.get("maker_fee", 0.001))
        fee_taker = float(self.trading_config.get("taker_fee", 0.001))
        self.roundtrip_fee = 2.0 * max(fee_maker, fee_taker)  # conservador

        # Trading mode
        self.trading_mode = self.trading_config.get("mode", "paper_trading")
        self.is_futures = bool(self.trading_config.get("futures", False))
        self.default_leverage = float(self.trading_config.get("default_leverage", 3.0 if self.is_futures else 1.0))

        # Estado para DD
        self.peak_equity: Optional[float] = None

        # Trailing desde config (si existe)
        trailing_cfg = self.risk_config.get("trailing", {})
        self.trailing_defaults = {
            "enabled": bool(trailing_cfg.get("enabled", True)),
            "activation_pct": float(trailing_cfg.get("activation_pct", 0.01)),
            "trail_pct": float(trailing_cfg.get("trail_pct", 0.005)),
            "min_trail_pct": float(trailing_cfg.get("min_trail_pct", 0.01)),
        }

        logger.info(
            f"[RiskManager] Modo={self.trading_mode} | Futures={self.is_futures} | "
            f"Symbol={self.symbol} | lotStep={self.lot_step} tickSize={self.tick_size} minNotional={self.min_notional}"
        )

    # ----------------------------- Helpers de precisión -----------------------------

    def _round_down_to_step(self, value: float, step: float) -> float:
        if step <= 0:
            return float(value)
        quant = Decimal(str(step))
        return float((Decimal(str(value)) / quant).to_integral_value(rounding=ROUND_DOWN) * quant)

    def _round_price_to_tick(self, price: float) -> float:
        return self._round_to_step(price, self.tick_size)

    def _round_to_step(self, value: float, step: float) -> float:
        # Para precios preferimos half-up a la malla de ticks
        if step <= 0:
            return float(value)
        quant = Decimal(str(step))
        return float((Decimal(str(value)) / quant).to_integral_value(rounding=ROUND_HALF_UP) * quant)

    # ----------------------------- API pública -----------------------------

    def validate_signal(self, signal: str, confidence: float) -> bool:
        if confidence < self.min_signal_conf:
            logger.warning(f"[RISK] Confianza insuficiente: {confidence:.2%} < {self.min_signal_conf:.0%}")
            return False
        if signal not in ["BUY", "SELL", "HOLD", "LONG", "SHORT"]:
            logger.warning(f"[RISK] Señal inválida: {signal}")
            return False
        return True

    def calculate_position_size(
        self,
        current_price: float,
        atr: float,
        balance: float,
        side: str,
        stop_loss_pct: Optional[float] = None,
        confidence: float = 1.0
    ) -> RiskDecision:
        """
        Calcula tamaño, SL, TP y leverage en base a riesgo.
        - Soporta LONG (BUY) y SHORT (SELL)
        - Cumple minNotional/lotStep/tickSize
        """
        try:
            # Validación de inputs
            if current_price <= 0 or balance <= 0:
                return self._reject("Inputs inválidos (precio/balance)")

            if atr is None or atr <= 0:
                logger.debug("[RISK] ATR no válido; se ignora ajuste por volatilidad.")
                atr = 0.0

            # Límite diario y DD
            if not self._check_daily_limits(balance):
                return self._reject("Límites diarios o drawdown excedidos")

            # Normalizar side
            side = side.upper()
            if side == "BUY":
                side = "LONG"
            elif side == "SELL":
                side = "SHORT"
            if side not in ["LONG", "SHORT"]:
                return self._reject(f"Side inválido: {side}")

            # SL por defecto y ajuste por ATR mínimo (opcional)
            sl_pct = float(stop_loss_pct if stop_loss_pct is not None else self.default_sl_pct)
            if self.min_sl_atr_mult > 0 and atr > 0:
                sl_pct = max(sl_pct, (atr / current_price) * self.min_sl_atr_mult)

            # Riesgo base en USD ajustado por confianza
            risk_usd = balance * self.max_risk_per_trade
            if self.confidence_risk_gamma != 1.0:
                risk_usd *= float(confidence ** self.confidence_risk_gamma)
            else:
                risk_usd *= float(confidence)

            # Distancia monetaria al SL por unidad (incluye fees ida+vuelta como buffer)
            # Nota: para LONG y SHORT el módulo de la distancia es el mismo: price * sl_pct
            risk_per_unit = current_price * sl_pct
            fees_buffer = current_price * self.roundtrip_fee
            risk_per_unit += fees_buffer

            if risk_per_unit <= 0:
                return self._reject("Stop loss inválido / fees mal configurados")

            # Tamaño inicial por riesgo puro
            qty_raw = risk_usd / risk_per_unit

            # Ajuste por volatilidad relativa (cap si ATR muy alto)
            if atr > 0 and self.atr_target_fraction > 0:
                rel_atr = atr / current_price  # fracción del precio
                vol_factor = min(1.0, self.atr_target_fraction / max(rel_atr, 1e-12))
                qty_raw *= vol_factor

            # Límite por exposición (notional)
            # Spot: notional <= balance * max_exposure_pct
            # Futures: notional <= balance * max_exposure_pct * leverage_elegido
            leverage = 1.0
            if self.is_futures:
                leverage = max(1.0, min(self.max_leverage, self.default_leverage))

            max_notional = balance * self.max_exposure_pct * leverage
            qty_cap_by_exposure = max_notional / current_price if current_price > 0 else 0.0

            qty_capped = min(qty_raw, qty_cap_by_exposure)

            # Redondeos por símbolo
            qty_rounded = self._round_down_to_step(qty_capped, self.lot_step)

            # Precios SL/TP según side
            if side == "LONG":
                sl_price = current_price * (1.0 - sl_pct)
                tp_price = current_price * (1.0 + self.tp_r_multiple * sl_pct)
            else:
                sl_price = current_price * (1.0 + sl_pct)
                tp_price = current_price * (1.0 - self.tp_r_multiple * sl_pct)

            sl_price = self._round_to_step(sl_price, self.tick_size)
            tp_price = self._round_to_step(tp_price, self.tick_size)

            if qty_rounded <= 0:
                return self._reject("Tamaño de posición resultó 0 tras límites/rounding")

            # minNotional: si queda por debajo, podemos escalar (siempre respetando exposición)
            notional = qty_rounded * current_price
            if notional < self.min_notional:
                # Intentar subir al mínimo
                needed_qty = self._round_down_to_step((self.min_notional / current_price), self.lot_step)
                # Aun así, respetar exposición
                needed_qty = min(needed_qty, qty_cap_by_exposure)
                if needed_qty <= 0:
                    return self._reject("No se puede alcanzar minNotional sin violar exposición")
                qty_rounded = needed_qty
                notional = qty_rounded * current_price

            # Métricas finales de riesgo
            # Distancia al SL por unidad (sin signo)
            sl_distance = abs(current_price - sl_price)
            risk_amount = qty_rounded * sl_distance
            risk_pct = risk_amount / balance if balance > 0 else 0.0

            decision = RiskDecision(
                size_qty=float(qty_rounded),
                stop_loss=float(sl_price),
                take_profit=float(tp_price),
                leverage=float(leverage),
                max_position_value=float(max_notional),
                risk_amount=float(risk_amount),
                risk_percentage=float(risk_pct),
                trailing_config=dict(self.trailing_defaults),
            )

            logger.info(
                f"[RISK] {side} qty={decision.size_qty:.6f} SL={decision.stop_loss:.2f} "
                f"TP={decision.take_profit:.2f} lev={decision.leverage:.2f} "
                f"risk={decision.risk_percentage:.2%} notional≈{notional:.2f}"
            )
            return decision

        except Exception as e:
            logger.exception(f"[RISK] Error calculando posición: {e}")
            return self._reject(f"Error en cálculo: {e}")

    def get_risk_summary(self) -> Dict:
        return {
            "symbol": self.symbol,
            "max_risk_per_trade": self.max_risk_per_trade,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_leverage": self.max_leverage,
            "max_exposure_pct": self.max_exposure_pct,
            "default_sl_pct": self.default_sl_pct,
            "tp_r_multiple": self.tp_r_multiple,
            "trading_mode": self.trading_mode,
            "is_futures": self.is_futures,
            "lot_step": self.lot_step,
            "tick_size": self.tick_size,
            "min_notional": self.min_notional,
        }

    # ----------------------------- Límites diarios / DD -----------------------------

    def _check_daily_limits(self, current_balance: float) -> bool:
        try:
            today = date.today()
            daily_pnl = self._get_daily_pnl(today)

            max_daily_loss = current_balance * self.max_daily_loss_pct
            if daily_pnl < -max_daily_loss:
                logger.warning(f"[RISK] Límite de pérdida diaria excedido: {daily_pnl:.2f} < -{max_daily_loss:.2f}")
                return False

            # Peak equity in-memory (si la BD tiene pico histórico, podría consultarse)
            if self.peak_equity is None:
                self.peak_equity = float(current_balance)
            else:
                self.peak_equity = max(self.peak_equity, float(current_balance))

            # Drawdown vs pico de la sesión
            dd_abs = self.peak_equity - float(current_balance)
            if dd_abs > (self.max_drawdown_pct * self.peak_equity):
                logger.warning(
                    f"[RISK] Drawdown máximo excedido: {dd_abs:.2f} > {self.max_drawdown_pct*100:.2f}% de {self.peak_equity:.2f}"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"[RISK] Error verificando límites diarios: {e}")
            # En caso de error de BD, se prefiere ser conservador y bloquear
            return False

    def _get_daily_pnl(self, day: date) -> float:
        """Consulta PnL del día en la BD. Fallback: 0.0 si no hay estructura."""
        try:
            # Si el db_manager expone un helper específico:
            if hasattr(db_manager, "get_daily_pnl"):
                return float(db_manager.get_daily_pnl(self.symbol, day))

            # Fallback SQL genérico (ajusta a tu esquema real)
            # Se asume una tabla 'trades' con columnas: symbol, close_time (ISO), pnl
            rows = db_manager.query(
                "SELECT COALESCE(SUM(pnl), 0) FROM trades "
                "WHERE symbol = ? AND DATE(close_time) = DATE(?)",
                (self.symbol, day.isoformat()),
            )
            total = rows[0][0] if rows and rows[0] and rows[0][0] is not None else 0.0
            return float(total)
        except Exception as e:
            logger.debug(f"[RISK] Fallback daily PnL (0.0) por error: {e}")
            return 0.0

    # ----------------------------- Utilidades internas -----------------------------

    def _reject(self, reason: str) -> RiskDecision:
        logger.warning(f"[RISK] Operación rechazada: {reason}")
        return RiskDecision(
            size_qty=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            leverage=1.0,
            max_position_value=0.0,
            risk_amount=0.0,
            risk_percentage=0.0,
            trailing_config=None,
        )

    def calculate_var(self, returns: List[float], confidence_level: float = 0.95) -> float:
        """
        Calcula Value at Risk (VaR) usando el método histórico
        
        Args:
            returns: Lista de retornos históricos
            confidence_level: Nivel de confianza (0.95 = 95%)
            
        Returns:
            VaR como porcentaje negativo
        """
        try:
            if not returns or len(returns) < 30:
                logger.warning("Datos insuficientes para calcular VaR")
                return -0.05  # 5% por defecto
            
            returns_array = np.array(returns)
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(returns_array, var_percentile)
            
            logger.info(f"VaR {confidence_level*100}%: {var_value:.4f}")
            return float(var_value)
            
        except Exception as e:
            logger.error(f"Error calculando VaR: {e}")
            return -0.05

    def calculate_cvar(self, returns: List[float], confidence_level: float = 0.95) -> float:
        """
        Calcula Conditional Value at Risk (CVaR) o Expected Shortfall
        
        Args:
            returns: Lista de retornos históricos
            confidence_level: Nivel de confianza (0.95 = 95%)
            
        Returns:
            CVaR como porcentaje negativo
        """
        try:
            if not returns or len(returns) < 30:
                logger.warning("Datos insuficientes para calcular CVaR")
                return -0.08  # 8% por defecto
            
            returns_array = np.array(returns)
            var_value = self.calculate_var(returns, confidence_level)
            
            # CVaR es el promedio de retornos peores que VaR
            tail_returns = returns_array[returns_array <= var_value]
            cvar_value = np.mean(tail_returns) if len(tail_returns) > 0 else var_value
            
            logger.info(f"CVaR {confidence_level*100}%: {cvar_value:.4f}")
            return float(cvar_value)
            
        except Exception as e:
            logger.error(f"Error calculando CVaR: {e}")
            return -0.08

    def calculate_portfolio_var(self, positions: Dict[str, Dict], confidence_level: float = 0.95) -> Dict[str, float]:
        """
        Calcula VaR del portafolio considerando correlaciones
        
        Args:
            positions: Dict con posiciones {symbol: {size, price, side}}
            confidence_level: Nivel de confianza
            
        Returns:
            Dict con VaR individual y del portafolio
        """
        try:
            if not positions:
                return {"portfolio_var": 0.0, "individual_var": {}}
            
            # Obtener retornos históricos para cada símbolo
            returns_data = {}
            for symbol in positions.keys():
                try:
                    # Obtener datos históricos de los últimos 30 días
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    
                    historical_data = db_manager.get_historical_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        timeframe='1h'
                    )
                    
                    if historical_data and len(historical_data) > 24:  # Al menos 1 día de datos
                        df = pd.DataFrame(historical_data)
                        if 'close' in df.columns:
                            returns = df['close'].pct_change().dropna().tolist()
                            returns_data[symbol] = returns
                            
                except Exception as e:
                    logger.warning(f"Error obteniendo datos para {symbol}: {e}")
                    continue
            
            if not returns_data:
                logger.warning("No hay datos suficientes para calcular VaR del portafolio")
                return {"portfolio_var": 0.0, "individual_var": {}}
            
            # Calcular VaR individual
            individual_var = {}
            for symbol, returns in returns_data.items():
                individual_var[symbol] = self.calculate_var(returns, confidence_level)
            
            # Calcular VaR del portafolio usando matriz de correlación
            if len(returns_data) > 1:
                # Crear DataFrame con retornos de todos los símbolos
                max_length = min(len(returns) for returns in returns_data.values())
                aligned_returns = {}
                for symbol, returns in returns_data.items():
                    aligned_returns[symbol] = returns[-max_length:]
                
                returns_df = pd.DataFrame(aligned_returns)
                correlation_matrix = returns_df.corr()
                
                # Calcular pesos del portafolio
                total_value = sum(pos['size'] * pos['price'] for pos in positions.values())
                weights = {}
                for symbol, pos in positions.items():
                    if symbol in returns_data:
                        weights[symbol] = (pos['size'] * pos['price']) / total_value
                
                # Calcular VaR del portafolio
                portfolio_variance = 0.0
                for i, (symbol1, weight1) in enumerate(weights.items()):
                    for j, (symbol2, weight2) in enumerate(weights.items()):
                        if symbol1 in correlation_matrix.columns and symbol2 in correlation_matrix.columns:
                            corr = correlation_matrix.loc[symbol1, symbol2]
                            var1 = individual_var.get(symbol1, 0)
                            var2 = individual_var.get(symbol2, 0)
                            portfolio_variance += weight1 * weight2 * var1 * var2 * corr
                
                portfolio_var = np.sqrt(portfolio_variance)
            else:
                # Un solo símbolo
                symbol = list(returns_data.keys())[0]
                portfolio_var = individual_var.get(symbol, 0)
            
            logger.info(f"VaR del portafolio {confidence_level*100}%: {portfolio_var:.4f}")
            return {
                "portfolio_var": float(portfolio_var),
                "individual_var": individual_var
            }
            
        except Exception as e:
            logger.error(f"Error calculando VaR del portafolio: {e}")
            return {"portfolio_var": 0.0, "individual_var": {}}

    def calculate_stress_test(self, positions: Dict[str, Dict], stress_scenarios: List[float] = None) -> Dict[str, float]:
        """
        Realiza stress test del portafolio con diferentes escenarios de mercado
        
        Args:
            positions: Dict con posiciones {symbol: {size, price, side}}
            stress_scenarios: Lista de shocks de mercado (por defecto: -5%, -10%, -20%)
            
        Returns:
            Dict con resultados del stress test
        """
        try:
            if stress_scenarios is None:
                stress_scenarios = [-0.05, -0.10, -0.20]  # -5%, -10%, -20%
            
            stress_results = {}
            total_portfolio_value = sum(pos['size'] * pos['price'] for pos in positions.values())
            
            for scenario in stress_scenarios:
                scenario_loss = 0.0
                for symbol, pos in positions.items():
                    # Calcular pérdida para cada posición
                    position_value = pos['size'] * pos['price']
                    if pos['side'].upper() in ['BUY', 'LONG']:
                        # Posición larga: pérdida si el precio baja
                        loss = position_value * abs(scenario)
                    else:
                        # Posición corta: pérdida si el precio sube
                        loss = position_value * abs(scenario)
                    
                    scenario_loss += loss
                
                # Calcular pérdida como porcentaje del portafolio
                loss_percentage = (scenario_loss / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
                stress_results[f"shock_{int(scenario*100)}%"] = {
                    "absolute_loss": scenario_loss,
                    "percentage_loss": loss_percentage
                }
            
            logger.info(f"Stress test completado: {stress_results}")
            return stress_results
            
        except Exception as e:
            logger.error(f"Error en stress test: {e}")
            return {}

    def get_risk_metrics(self, positions: Dict[str, Dict]) -> Dict[str, float]:
        """
        Obtiene métricas de riesgo consolidadas
        
        Args:
            positions: Dict con posiciones actuales
            
        Returns:
            Dict con todas las métricas de riesgo
        """
        try:
            metrics = {}
            
            # VaR y CVaR del portafolio
            var_results = self.calculate_portfolio_var(positions, 0.95)
            metrics.update(var_results)
            
            # Stress test
            stress_results = self.calculate_stress_test(positions)
            metrics["stress_test"] = stress_results
            
            # Métricas adicionales
            total_exposure = sum(pos['size'] * pos['price'] for pos in positions.values())
            metrics["total_exposure"] = total_exposure
            
            # Diversificación (número de símbolos únicos)
            unique_symbols = len(set(pos.get('symbol', '') for pos in positions.values()))
            metrics["diversification"] = unique_symbols
            
            # Concentración máxima (símbolo con mayor exposición)
            if positions:
                max_exposure = max(pos['size'] * pos['price'] for pos in positions.values())
                max_concentration = (max_exposure / total_exposure) * 100 if total_exposure > 0 else 0
                metrics["max_concentration"] = max_concentration
            
            logger.info(f"Métricas de riesgo calculadas: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
            return {}


# Instancia global
risk_manager = RiskManager()
