# Ruta: core/trading/signal_processor.py
"""
trading/signal_processor.py
Procesador inteligente de señales de trading con filtrado avanzado.

Funciones clave:
- Procesamiento de señales ML con filtros de calidad
- Análisis multi-timeframe con consistencia ponderada
- Optimización del timing de entrada/salida
- Scoring detallado y explicable
- Adaptación a condiciones de mercado (régimen/volatilidad/sesiones)
- Métricas y utilidades de testing/validación

Requisitos (ya presentes en el proyecto):
- data/database.py -> db_manager.get_recent_market_data(...)
- data/preprocessor.py -> data_preprocessor.prepare_features_for_prediction(...)
- models/prediction_engine.py -> prediction_engine.predict(...)
- models/confidence_estimator.py -> confidence_estimator.estimate_confidence(...)
- trading/risk_manager.py -> risk_manager (opcional: detect_market_regime, calculate_volatility_regime)
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd
import talib

from core.config.config_loader import ConfigLoader
from core.data.database import db_manager
from core.data.preprocessor import data_preprocessor
from core.data.symbol_database_manager import symbol_db_manager
from core.data.historical_data_adapter import get_historical_data
from core.ml.enterprise.prediction_engine import PredictionEngine
from core.ml.enterprise.confidence_estimator import ConfidenceEstimator
from .risk_manager import risk_manager

logger = logging.getLogger(__name__)

# ----------------------------- Parámetros adaptativos -----------------------------

VOLATILITY_ADJUSTMENTS = {
    "LOW":    {"min_confidence": 0.60, "min_score": 0.65},
    "MEDIUM": {"min_confidence": 0.70, "min_score": 0.75},
    "HIGH":   {"min_confidence": 0.80, "min_score": 0.85},
    "EXTREME":{"min_confidence": 0.90, "min_score": 0.95},
}

SESSION_ADJUSTMENTS = {
    "ASIAN":    {"liquidity_factor": 0.7, "volatility_factor": 0.8},
    "EUROPEAN": {"liquidity_factor": 0.9, "volatility_factor": 1.0},
    "US":       {"liquidity_factor": 1.0, "volatility_factor": 1.2},
    "OVERLAP":  {"liquidity_factor": 1.1, "volatility_factor": 1.1},
}

# Anti-overtrading (aplícalos donde corresponda, p. ej. en executor)
MAX_SIGNALS_PER_HOUR = 2
MAX_SIGNALS_PER_DAY = 10

VOLATILITY_LIMITS = {
    "EXTREME": {"max_position_size": 0.005, "min_confidence": 0.95},
    "HIGH":    {"max_position_size": 0.010, "min_confidence": 0.85},
}

SESSION_FILTERS = {
    "ASIAN":   {"reduce_sizing": 0.7, "increase_confidence": 1.1},
    "WEEKEND": {"block_signals": True},
}

# ----------------------------- Data classes -----------------------------

@dataclass
class SignalQuality:
    """
    Representa la calidad y características de una señal de trading
    """
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    quality_score: float  # 0.0 - 1.0 (score combinado de calidad)
    strength: float  # 0.0 - 1.0
    consistency: float  # 0.0 - 1.0 (consistencia entre timeframes)
    timing_score: float  # 0.0 - 1.0
    risk_score: float  # 0.0 - 1.0

    # Análisis multi-timeframe
    timeframe_alignment: Dict[str, str] = field(default_factory=dict)
    timeframe_confidence: Dict[str, float] = field(default_factory=dict)

    # Condiciones de mercado
    market_regime: str = "UNKNOWN"  # TRENDING, RANGING, VOLATILE, CONSOLIDATING
    volatility_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, EXTREME
    momentum_direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL

    # Factores de calidad
    volume_confirmation: bool = False
    price_action_alignment: bool = False
    indicator_convergence: bool = False
    support_resistance_respect: bool = False

    # Timing
    session_timing: str = "UNKNOWN"  # ASIAN, EUROPEAN, US, OVERLAP
    market_hours_factor: float = 1.0  # Ajuste por horario de mercado

    # Metadata
    processing_time: datetime = field(default_factory=datetime.now)
    raw_prediction: Dict[str, Any] = field(default_factory=dict)
    filtering_applied: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)


# ----------------------------- Procesador de Señales -----------------------------

class SignalProcessor:
    """
    Procesador inteligente de señales de trading con filtrado avanzado

    Responsabilidades:
    - Procesar señales ML con filtros de calidad
    - Combinar análisis multi-timeframe
    - Optimizar timing de entrada/salida
    - Aplicar lógica de trading avanzada
    - Adaptar filtros a condiciones de mercado
    - Scoring detallado de señales
    """

    def __init__(self) -> None:
        self.config = ConfigLoader().get_main_config()
        self.signal_config = self.config.get_value(["signal_processing"], {})
        self.trading_config = self.config.get_trading_settings()

        # Configuración de filtros
        self.min_quality_score = float(self.signal_config.get("min_quality_score", 0.70))
        self.multi_timeframe_weight = float(self.signal_config.get("multi_timeframe_weight", 0.20))
        self.volume_confirmation_required = bool(self.signal_config.get("volume_confirmation", True))
        self.trend_alignment_required = bool(self.signal_config.get("trend_alignment", True))
    
    async def _get_market_data_sqlite(self, symbol: str, start_time: datetime, end_time: datetime, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtiene datos de mercado usando el nuevo sistema SQLite"""
        try:
            # Intentar obtener datos del timeframe más apropiado
            timeframes = ['1h', '4h', '1d', '15m', '5m', '1m']
            
            for timeframe in timeframes:
                try:
                    data = get_historical_data(symbol, timeframe, start_time, end_time)
                    if not data.empty and len(data) >= min(limit // 4, 10):  # Mínimo 10 registros
                        return data.head(limit)
                except Exception as e:
                    logger.debug(f"Error obteniendo datos {symbol}_{timeframe}: {e}")
                    continue
            
            # Fallback: usar datos más recientes disponibles
            if symbol in symbol_db_manager.get_all_symbols():
                timeframes_available = symbol_db_manager.get_symbol_timeframes(symbol)
                if timeframes_available:
                    timeframe = timeframes_available[0]
                    data = symbol_db_manager.get_latest_data(symbol, timeframe, limit=limit)
                    if not data.empty:
                        return data
            
            return None
            
        except Exception as e:
            logger.debug(f"Error obteniendo datos SQLite para {symbol}: {e}")
            return None

        # Timeframes
        self.timeframes: List[str] = ["1m", "5m", "15m", "1h", "4h"]
        self.primary_timeframe: str = self.config.get('timeframes', {}).get('primary', '1h')

        # Métricas de tracking
        self.metrics: Dict[str, Any] = {
            "signals_processed": 0,
            "signals_approved": 0,
            "signals_rejected": 0,
            "average_quality_score": 0.0,
            "filter_rejection_reasons": defaultdict(int),
            "timeframe_consistency_avg": 0.0,
            "processing_latency_ms": 0.0,
            "signals_by_regime": defaultdict(int),
            "accuracy_by_score_bucket": defaultdict(list),
            "volume_confirmation_rate": 0.0,
        }

        # Cache
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        self.market_context_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout_sec = 300  # 5 min

        logger.info(f"[SignalProcessor] Inicializado | min_quality_score={self.min_quality_score:.2f}")

    # ----------------------------- Pipeline principal -----------------------------

    async def process_signal(self, symbol: str, timeframe: str = "1h") -> SignalQuality:
        """
        Procesa una señal completa con todos los filtros y devuelve un SignalQuality.
        """
        t0 = time.time()
        self.metrics["signals_processed"] += 1

        try:
            # 1) Predicción base ML (+ calibración)
            raw_prediction = await self._get_ml_prediction(symbol, timeframe)
            if not raw_prediction:
                return self._create_null_signal("No ML prediction available")

            # 2) Multi-timeframe
            timeframe_analysis = await self.analyze_multi_timeframe(symbol)

            # 3) Contexto de mercado
            market_context = await self.detect_market_context(symbol)

            # 4) Filtros de calidad
            filters_results = await self.apply_quality_filters(raw_prediction, symbol)

            # 5) Timing
            timing_score = await self.calculate_timing_score(symbol, raw_prediction.get("action", "HOLD"))

            # 6) Señal: normalización BUY/SELL/HOLD
            action = str(raw_prediction.get("action", "HOLD")).upper()
            if action in ("LONG", "BUY"):
                action = "BUY"
            elif action in ("SHORT", "SELL"):
                action = "SELL"
            else:
                action = "HOLD"

            # 7) Construir SignalQuality preliminar
            sq = SignalQuality(
                signal=action,
                confidence=float(raw_prediction.get("confidence", 0.0)),
                quality_score=0.0,  # se calcula ahora
                strength=float(raw_prediction.get("expected_return", 0.0)),
                consistency=float(timeframe_analysis.get("consistency_score", 0.0)),
                timing_score=float(timing_score),
                risk_score=float(filters_results.get("risk_score", 0.5)),
                timeframe_alignment=timeframe_analysis.get("alignment", {}),
                timeframe_confidence=timeframe_analysis.get("confidence", {}),
                market_regime=str(market_context.get("regime", "UNKNOWN")),
                volatility_level=str(market_context.get("volatility_level", "MEDIUM")),
                momentum_direction=str(market_context.get("momentum", "NEUTRAL")),
                volume_confirmation=bool(filters_results.get("volume_confirmed", False)),
                price_action_alignment=bool(filters_results.get("price_action_aligned", False)),
                indicator_convergence=bool(filters_results.get("indicators_converged", False)),
                support_resistance_respect=bool(filters_results.get("levels_respected", False)),
                session_timing=str(market_context.get("session", "UNKNOWN")),
                market_hours_factor=float(market_context.get("hours_factor", 1.0)),
                processing_time=datetime.now(),
                raw_prediction=raw_prediction,
                filtering_applied=list(filters_results.get("filters_applied", [])),
            )

            # 8) Scoring final
            sq.quality_score = self.calculate_signal_score(
                filters_results=filters_results,
                context=market_context,
                timeframe_analysis=timeframe_analysis,
                base_confidence=sq.confidence,
                timing_score=sq.timing_score,
            )

            # 9) Métricas
            latency_ms = (time.time() - t0) * 1000.0
            self._update_metrics(sq, latency_ms)

            logger.info(
                f"[SignalProcessor] {symbol} → {sq.signal} | "
                f"score={sq.quality_score:.2%}, conf={sq.confidence:.2%}, "
                f"consistency={sq.consistency:.2%}, timing={sq.timing_score:.2%}, "
                f"regime={sq.market_regime}, vol={sq.volatility_level}"
            )
            return sq

        except Exception as e:
            logger.exception(f"[SignalProcessor] Error procesando señal: {e}")
            return self._create_null_signal(f"Processing error: {e}")

    # ----------------------------- Multi-timeframe -----------------------------

    async def analyze_multi_timeframe(self, symbol: str) -> Dict[str, Any]:
        """
        Analiza señales en múltiples timeframes y mide su consistencia.
        Timeframes: 1m, 5m, 15m, 1h, 4h
        """
        try:
            alignment: Dict[str, str] = {}
            confidence_by_tf: Dict[str, float] = {}

            # Predicciones por TF con caché
            for tf in self.timeframes:
                pred = await self._get_ml_prediction(symbol, tf)
                if pred:
                    action = str(pred.get("action", "HOLD")).upper()
                    if action in ("LONG", "BUY"):
                        action = "BUY"
                    elif action in ("SHORT", "SELL"):
                        action = "SELL"
                    else:
                        action = "HOLD"
                    alignment[tf] = action
                    confidence_by_tf[tf] = float(pred.get("confidence", 0.0))
                else:
                    alignment[tf] = "HOLD"
                    confidence_by_tf[tf] = 0.5

            consistency_score = self._calculate_timeframe_consistency(alignment)
            dominant_signal = self._get_dominant_signal(alignment, confidence_by_tf)
            divergences = self._detect_timeframe_divergences(alignment)

            return {
                "alignment": alignment,
                "confidence": confidence_by_tf,
                "consistency_score": consistency_score,
                "dominant_signal": dominant_signal,
                "divergences": divergences,
            }
        except Exception as e:
            logger.exception(f"[SignalProcessor] Error en análisis multi-TF: {e}")
            return {
                "alignment": {},
                "confidence": {},
                "consistency_score": 0.0,
                "dominant_signal": "HOLD",
                "divergences": [],
            }

    def _calculate_timeframe_consistency(self, signals: Dict[str, str]) -> float:
        """
        Consistencia ponderada:
        - 1m & 5m alineados (peso 0.30)
        - 15m & 1h confirman dirección (peso 0.40)
        - 4h da contexto general (peso 0.30)
        """
        score = 0.0

        def same(a: str, b: str) -> bool:
            return a == b and a in ("BUY", "SELL")

        if same(signals.get("1m", "HOLD"), signals.get("5m", "HOLD")):
            score += 0.30
        if same(signals.get("15m", "HOLD"), signals.get("1h", "HOLD")):
            score += 0.40
        # 4h: coincide con 1h o es neutral
        if signals.get("4h", "HOLD") in (signals.get("1h", "HOLD"), "HOLD"):
            score += 0.30

        return float(np.clip(score, 0.0, 1.0))

    def _get_dominant_signal(self, alignment: Dict[str, str], conf: Dict[str, float]) -> str:
        """
        Dominante por votación ponderada:
        corto (1m,5m) peso 0.3, medio (15m,1h) peso 0.5, largo (4h) peso 0.2
        """
        weights = {"1m": 0.15, "5m": 0.15, "15m": 0.25, "1h": 0.25, "4h": 0.20}
        buy_w = sum(weights.get(tf, 0.0) * (conf.get(tf, 0.5)) for tf, s in alignment.items() if s == "BUY")
        sell_w = sum(weights.get(tf, 0.0) * (conf.get(tf, 0.5)) for tf, s in alignment.items() if s == "SELL")
        if buy_w > sell_w and buy_w > 0.1:
            return "BUY"
        if sell_w > buy_w and sell_w > 0.1:
            return "SELL"
        return "HOLD"

    def _detect_timeframe_divergences(self, alignment: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        Detecta pares de TF con señales opuestas relevantes.
        """
        pairs = [("1m", "5m"), ("5m", "15m"), ("15m", "1h"), ("1h", "4h")]
        divs = []
        for a, b in pairs:
            sa, sb = alignment.get(a, "HOLD"), alignment.get(b, "HOLD")
            if sa != "HOLD" and sb != "HOLD" and sa != sb:
                divs.append((a, b))
        return divs

    # ----------------------------- Filtros de calidad -----------------------------

    async def apply_quality_filters(self, raw_signal: Dict, symbol: str) -> Dict[str, Any]:
        """
        Aplica batería de filtros de calidad y devuelve dict con resultados.
        """
        results: Dict[str, Any] = {
            "filters_applied": [],
            "volume_confirmed": False,
            "volatility_ok": True,
            "trend_aligned": True,
            "timing_ok": True,
            "levels_respected": True,
            "indicators_converged": False,
            "price_action_aligned": False,
            "risk_score": 0.5,
            "confidence": float(raw_signal.get("confidence", 0.0)),
        }
        try:
            signal = str(raw_signal.get("action", "HOLD")).upper()

            vol_ok, vol_level, vol_score = await self.volatility_regime_filter(symbol)
            results["volatility_ok"] = vol_ok
            results["volatility_level"] = vol_level
            results["filters_applied"].append("volatility_filter")

            vol_conf, vol_conf_score = await self.volume_confirmation_filter(symbol, signal)
            results["volume_confirmed"] = vol_conf
            results["filters_applied"].append("volume_filter")

            trend_ok, trend_score = await self.trend_alignment_filter(symbol, signal)
            results["trend_aligned"] = trend_ok
            results["filters_applied"].append("trend_filter")

            levels_ok, levels_score = await self._check_support_resistance(symbol, signal)
            results["levels_respected"] = levels_ok
            results["filters_applied"].append("levels_filter")

            conv_ok, conv_score = await self._check_indicator_convergence(symbol, signal)
            results["indicators_converged"] = conv_ok
            results["filters_applied"].append("convergence_filter")

            pa_ok, pa_score = await self._check_price_action(symbol, signal)
            results["price_action_aligned"] = pa_ok
            results["filters_applied"].append("price_action_filter")

            # Score de riesgo / confluencia
            parts = [vol_score, vol_conf_score, trend_score, levels_score, conv_score, pa_score]
            results["risk_score"] = float(np.clip(np.mean([p for p in parts if p is not None]), 0.0, 1.0))

            return results
        except Exception as e:
            logger.exception(f"[SignalProcessor] Error aplicando filtros: {e}")
            return results

    async def volume_confirmation_filter(self, symbol: str, signal: str) -> Tuple[bool, float]:
        """
        Verifica confirmación por volumen relativo y dirección.
        """
        try:
            # Obtener datos de los últimos 60 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=60)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=60)
            if df is None or df.empty or len(df) < 21:
                return False, 0.0
            if "volume" not in df.columns:
                return False, 0.0

            vol = df["volume"].astype(float)
            current = float(vol.iloc[-1])
            avg20 = float(vol.rolling(20).mean().iloc[-1])
            ratio = current / avg20 if avg20 > 0 else 1.0
            confirmed = ratio > 1.2  # 20% por encima de la media

            score = min(ratio / 2.0, 1.0)  # 0..1
            # Bonus direccional simple
            if "close" in df.columns and len(df) >= 2:
                close = df["close"].astype(float)
                up_move = float(close.iloc[-1] - close.iloc[-2]) > 0
                if (signal in ("BUY", "LONG") and up_move) or (signal in ("SELL", "SHORT") and not up_move):
                    score = min(score * 1.15, 1.0)

            return confirmed, float(score)
        except Exception as e:
            logger.debug(f"[SignalProcessor] volume filter fallback: {e}")
            return False, 0.0

    async def volatility_regime_filter(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Determina si se puede operar según volatilidad (via ATR).
        """
        try:
            # Si el risk_manager tiene cálculo propio, úsalo
            if hasattr(risk_manager, "calculate_volatility_regime"):
                regime = risk_manager.calculate_volatility_regime(symbol)
                level = str(regime).upper()
            else:
                level = await self._calculate_volatility_level_from_data(symbol)

            ok = level != "EXTREME"
            # Score inverso al exceso de volatilidad percibida
            score_map = {"LOW": 0.9, "MEDIUM": 0.8, "HIGH": 0.6, "EXTREME": 0.2}
            return ok, level, score_map.get(level, 0.7)
        except Exception as e:
            logger.debug(f"[SignalProcessor] volatility filter fallback: {e}")
            return True, "MEDIUM", 0.7

    async def trend_alignment_filter(self, symbol: str, signal: str) -> Tuple[bool, float]:
        """
        Verifica alineación con tendencia (EMA20/50/100).
        """
        try:
            # Obtener datos de los últimos 200 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=200)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=200)
            if df is None or df.empty or len(df) < 100:
                return True, 0.5
            if "close" not in df.columns:
                return True, 0.5

            close = df["close"].values.astype(float)
            ema20 = talib.EMA(close, timeperiod=20)
            ema50 = talib.EMA(close, timeperiod=50)
            ema100 = talib.EMA(close, timeperiod=100)

            if any(np.isnan(x) for x in (ema20[-1], ema50[-1], ema100[-1])):
                return True, 0.5

            bull = ema20[-1] > ema50[-1] > ema100[-1]
            bear = ema20[-1] < ema50[-1] < ema100[-1]

            if signal in ("BUY", "LONG") and bull:
                return True, 0.9
            if signal in ("SELL", "SHORT") and bear:
                return True, 0.9
            if not bull and not bear:
                return True, 0.5  # mercado lateral: no bloquees pero penaliza
            return False, 0.2
        except Exception as e:
            logger.debug(f"[SignalProcessor] trend filter fallback: {e}")
            return True, 0.5

    async def _check_support_resistance(self, symbol: str, signal: str) -> Tuple[bool, float]:
        """
        Comprueba respeto/choque con niveles clave (pivots simples + niveles psicológicos).
        """
        try:
            # Obtener datos de los últimos 120 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=120)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=120)
            if df is None or df.empty or len(df) < 50:
                return True, 0.5
            if "close" not in df.columns:
                return True, 0.5

            levels = await self._get_key_levels(df)
            price = float(df["close"].iloc[-1])

            nearest = min((abs(price - lv) for lv in levels["all_levels"]), default=math.inf)
            # Si estás comprando y el precio está chocando muy cerca de una R fuerte, penaliza
            threshold = max(price * 0.002,  # 0.2%
                            np.std(df["close"].tail(50)) if "close" in df.columns and len(df) >= 50 else price * 0.002)

            if signal in ("BUY", "LONG"):
                ok = not any(abs(price - r) < threshold for r in levels["resistance"])
                score = 0.9 if ok else 0.3
                return ok, score
            if signal in ("SELL", "SHORT"):
                ok = not any(abs(price - s) < threshold for s in levels["support"])
                score = 0.9 if ok else 0.3
                return ok, score

            # HOLD
            ok = nearest > threshold
            return ok, (0.7 if ok else 0.4)
        except Exception as e:
            logger.debug(f"[SignalProcessor] levels filter fallback: {e}")
            return True, 0.5

    async def _check_indicator_convergence(self, symbol: str, signal: str) -> Tuple[bool, float]:
        """
        Convergencia básica: RSI + MACD + BB en la misma dirección.
        """
        try:
            # Obtener datos de los últimos 200 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=200)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=200)
            if df is None or df.empty or len(df) < 50:
                return False, 0.5
            if "close" not in df.columns:
                return False, 0.5

            close = df["close"].values.astype(float)
            high = df["high"].values.astype(float) if "high" in df.columns else close
            low = df["low"].values.astype(float) if "low" in df.columns else close

            rsi = talib.RSI(close, timeperiod=14)
            macd, macdsig, _ = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

            ok = False
            score = 0.5
            if not np.isnan([rsi[-1], macd[-1], macdsig[-1], upper[-1], lower[-1]]).any():
                if signal in ("BUY", "LONG"):
                    ok = (rsi[-1] > 50) and (macd[-1] > macdsig[-1]) and (close[-1] > middle[-1])
                elif signal in ("SELL", "SHORT"):
                    ok = (rsi[-1] < 50) and (macd[-1] < macdsig[-1]) and (close[-1] < middle[-1])
                score = 0.9 if ok else 0.4

            return ok, score
        except Exception as e:
            logger.debug(f"[SignalProcessor] convergence filter fallback: {e}")
            return False, 0.5

    async def _check_price_action(self, symbol: str, signal: str) -> Tuple[bool, float]:
        """
        Comprobación simple de PA: vela impulsiva a favor, cuerpo proporcional, mechas no excesivas.
        """
        try:
            # Obtener datos de los últimos 20 períodos de 15m
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=20*15)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=20)
            if df is None or df.empty or len(df) < 5:
                return False, 0.5
            if not all(col in df.columns for col in ["open", "high", "low", "close"]):
                return False, 0.5

            last = df.iloc[-1]
            body = abs(float(last["close"] - last["open"]))
            range_ = float(last["high"] - last["low"])
            if range_ <= 0:
                return False, 0.5

            body_ratio = body / range_
            bullish = last["close"] > last["open"]

            if signal in ("BUY", "LONG"):
                ok = bullish and body_ratio > 0.55
                return ok, (0.85 if ok else 0.45)
            if signal in ("SELL", "SHORT"):
                ok = (not bullish) and body_ratio > 0.55
                return ok, (0.85 if ok else 0.45)

            return False, 0.5
        except Exception as e:
            logger.debug(f"[SignalProcessor] price action filter fallback: {e}")
            return False, 0.5

    # ----------------------------- Contexto de mercado -----------------------------

    async def detect_market_context(self, symbol: str) -> Dict[str, Any]:
        """
        Detecta régimen, volatilidad, momentum y sesión con caché corta.
        """
        try:
            key = f"{symbol}_context"
            item = self.market_context_cache.get(key)
            if item and (datetime.now() - item["ts"]).total_seconds() < self.cache_timeout_sec:
                return item["data"]

            # Régimen y volatilidad vía risk_manager si existen
            regime = None
            volatility_level = None
            if hasattr(risk_manager, "detect_market_regime"):
                try:
                    regime = str(risk_manager.detect_market_regime(symbol)).upper()
                except Exception:
                    regime = None
            if hasattr(risk_manager, "calculate_volatility_regime"):
                try:
                    volatility_level = str(risk_manager.calculate_volatility_regime(symbol)).upper()
                except Exception:
                    volatility_level = None

            # Fallbacks por datos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=240)
            df_1h = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=240)
            
            if regime is None:
                regime = await self._detect_market_regime(df_1h)
            if volatility_level is None:
                volatility_level = await self._calculate_volatility_level(df_1h)

            momentum = await self._detect_momentum_direction(df_1h)
            session = self._get_trading_session()
            hours_factor = self._calculate_market_hours_factor(session)
            trend_strength = self._calculate_trend_strength(df_1h)
            levels = await self._get_key_levels(df_1h)

            ctx = {
                "regime": regime,
                "volatility_level": volatility_level,
                "momentum": momentum,
                "session": session,
                "hours_factor": hours_factor,
                "trend_strength": trend_strength,
                "support_resistance": levels,
            }

            self.market_context_cache[key] = {"data": ctx, "ts": datetime.now()}
            return ctx
        except Exception as e:
            logger.exception(f"[SignalProcessor] Error detectando contexto: {e}")
            return self._default_market_context()

    async def calculate_timing_score(self, symbol: str, signal: str) -> float:
        """
        Optimiza el timing combinando niveles, sesión, volatilidad, momentum y confluencias.
        """
        try:
            scores = []
            w = []

            scores.append(await self._calculate_levels_proximity(symbol, signal))
            w.append(0.25)

            scores.append(self._calculate_session_timing_factor())
            w.append(0.15)

            scores.append(await self._calculate_volatility_timing_factor(symbol))
            w.append(0.20)

            scores.append(await self._calculate_momentum_timing_factor(symbol, signal))
            w.append(0.25)

            scores.append(await self._calculate_confluence_factor(symbol, signal))
            w.append(0.15)

            timing = float(np.clip(np.average(scores, weights=w), 0.0, 1.0))
            return timing
        except Exception as e:
            logger.debug(f"[SignalProcessor] timing score fallback: {e}")
            return 0.5

    async def check_confluences(self, symbol: str, signal: str) -> Dict[str, bool]:
        """
        Confluencias técnicas simples (puedes ampliar con tus SMC).
        """
        ok_pa, _ = await self._check_price_action(symbol, signal)
        ok_conv, _ = await self._check_indicator_convergence(symbol, signal)
        trend_ok, _ = await self.trend_alignment_filter(symbol, signal)

        return {
            "price_action": ok_pa,
            "indicators": ok_conv,
            "trend": trend_ok,
        }

    # ----------------------------- Scoring & decisión -----------------------------

    def calculate_signal_score(
        self,
        filters_results: Dict[str, Any],
        context: Dict[str, Any],
        timeframe_analysis: Dict[str, Any],
        base_confidence: float,
        timing_score: float,
    ) -> float:
        """
        score = (
            confidence * 0.25 +
            multi_timeframe_consistency * 0.20 +
            volume_confirmation * 0.15 +
            timing_quality * 0.15 +
            trend_alignment * 0.10 +
            confluence_strength * 0.10 +
            volatility_adjustment * 0.05
        )
        """
        try:
            # Valores de entrada
            consistency = float(timeframe_analysis.get("consistency_score", 0.5))
            volume_score = 1.0 if filters_results.get("volume_confirmed", False) else 0.3
            trend_score = 1.0 if filters_results.get("trend_aligned", False) else 0.3
            confluence = float(filters_results.get("risk_score", 0.5))
            vol_adj = self._get_volatility_adjustment_score(str(context.get("volatility_level", "MEDIUM")))

            weights = {
                "confidence": 0.25,
                "consistency": 0.20,
                "volume": 0.15,
                "timing": 0.15,
                "trend": 0.10,
                "confluence": 0.10,
                "volatility": 0.05,
            }

            final_score = (
                base_confidence * weights["confidence"] +
                consistency * weights["consistency"] +
                volume_score * weights["volume"] +
                timing_score * weights["timing"] +
                trend_score * weights["trend"] +
                confluence * weights["confluence"] +
                vol_adj * weights["volatility"]
            )
            return float(np.clip(final_score, 0.0, 1.0))
        except Exception as e:
            logger.debug(f"[SignalProcessor] score fallback: {e}")
            return 0.5

    async def should_execute_signal(self, signal_quality: SignalQuality) -> Tuple[bool, str]:
        """
        Criterios:
        - Score mínimo según volatilidad
        - Confianza mínima por volatilidad
        - Filtros obligatorios (volumen/tendencia si config lo requiere)
        - Consistencia TF y timing aceptables
        """
        try:
            # Umbrales por volatilidad
            vol = signal_quality.volatility_level
            adjust = VOLATILITY_ADJUSTMENTS.get(vol, VOLATILITY_ADJUSTMENTS["MEDIUM"])
            min_score = float(adjust.get("min_score", self.min_quality_score))
            min_conf = float(adjust.get("min_confidence", 0.70))

            if signal_quality.quality_score < min_score:
                return False, f"Score insuficiente: {signal_quality.quality_score:.2%} < {min_score:.2%}"
            if signal_quality.confidence < min_conf:
                return False, f"Confianza insuficiente: {signal_quality.confidence:.2%} < {min_conf:.2%}"

            if self.volume_confirmation_required and not signal_quality.volume_confirmation:
                return False, "Confirmación de volumen requerida"
            if self.trend_alignment_required and not signal_quality.price_action_alignment:
                return False, "Alineación de tendencia/PA requerida"

            if signal_quality.volatility_level == "EXTREME":
                return False, "Volatilidad extrema"

            if signal_quality.consistency < 0.6:
                return False, f"Baja consistencia multi-TF: {signal_quality.consistency:.2%}"
            if signal_quality.timing_score < 0.5:
                return False, f"Timing desfavorable: {signal_quality.timing_score:.2%}"

            return True, f"Señal aprobada | score={signal_quality.quality_score:.2%}"
        except Exception as e:
            logger.debug(f"[SignalProcessor] decision fallback: {e}")
            return False, f"Error en evaluación: {e}"

    # ----------------------------- Auxiliares ML / caché -----------------------------

    async def _get_ml_prediction(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve {'action','confidence','expected_return','probabilities','features_importance',...}
        con caché de 60s + calibración (confidence_estimator) si está disponible.
        """
        try:
            key = f"{symbol}_{timeframe}"
            item = self.prediction_cache.get(key)
            if item and (datetime.now() - item["ts"]).total_seconds() < 60:
                return item["pred"]

            # Obtener datos y preparar features
            df = data_preprocessor.get_raw_data(symbol, days_back=30, timeframe=timeframe)
            if df.empty:
                return None
            features = data_preprocessor.prepare_prediction_data(df)
            if features is None or len(features) == 0:
                return None

            pred = await PredictionEngine.predict(symbol, features)
            if not pred:
                return None

            # Calibración de confianza si está disponible
            try:
                conf_info =  ConfidenceEstimator.estimate_confidence(pred, market_context={'volatility': 0.5})
                if conf_info and "calibrated_confidence" in conf_info:
                    # Mezcla simple: media ponderada con la original (0.6/0.4)
                    pred["confidence"] = float(np.clip(0.6 * float(pred.get("confidence", 0.0)) +
                                                       0.4 * float(conf_info["calibrated_confidence"]), 0.0, 1.0))
                    pred["uncertainty"] = float(conf_info.get("uncertainty", pred.get("uncertainty", 0.0)))
                    pred["calibration_quality"] = float(conf_info.get("calibration_quality", 0.0))
            except Exception as _:
                pass

            self.prediction_cache[key] = {"pred": pred, "ts": datetime.now()}
            return pred
        except Exception as e:
            logger.debug(f"[SignalProcessor] pred cache fallback: {e}")
            return None

    # ----------------------------- Detección de contexto (interno) -----------------------------

    async def _detect_market_regime(self, df: Optional[pd.DataFrame]) -> str:
        """TRENDING / RANGING / VOLATILE / CONSOLIDATING (heurístico simple)."""
        try:
            if df is None or df.empty or "close" not in df.columns:
                return "UNKNOWN"

            close = df["close"].values.astype(float)
            if len(close) < 60:
                return "UNKNOWN"

            adx = talib.ADX(
                df["high"].values.astype(float),
                df["low"].values.astype(float),
                close,
                timeperiod=14,
            )
            adx_last = adx[-1] if len(adx) else np.nan

            if not np.isnan(adx_last):
                if adx_last > 25:
                    return "TRENDING"
                if adx_last < 15:
                    return "RANGING"

            # Fallback con bandas de Bollinger (squeeze)
            upper, middle, lower = talib.BBANDS(close, timeperiod=20)
            width = (upper - lower) / middle
            width_last = width[-1] if len(width) else np.nan

            if not np.isnan(width_last):
                if width_last > 0.1:
                    return "VOLATILE"
                if width_last < 0.03:
                    return "CONSOLIDATING"

            return "RANGING"
        except Exception:
            return "UNKNOWN"

    async def _calculate_volatility_level_from_data(self, symbol: str) -> str:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=120)
        df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=120)
        return await self._calculate_volatility_level(df)

    async def _calculate_volatility_level(self, df: Optional[pd.DataFrame]) -> str:
        try:
            if df is None or df.empty or "close" not in df.columns:
                return "MEDIUM"

            high = df["high"].values.astype(float) if "high" in df.columns else df["close"].values.astype(float)
            low = df["low"].values.astype(float) if "low" in df.columns else df["close"].values.astype(float)
            close = df["close"].values.astype(float)
            atr = talib.ATR(high, low, close, timeperiod=14)
            if len(atr) < 20 or np.isnan(atr[-1]):
                return "MEDIUM"

            current = float(atr[-1])
            avg = float(np.nanmean(atr[-50:])) if len(atr) >= 50 else current
            ratio = current / avg if avg > 0 else 1.0

            if ratio < 0.5:
                return "LOW"
            if ratio < 1.5:
                return "MEDIUM"
            if ratio < 2.5:
                return "HIGH"
            return "EXTREME"
        except Exception:
            return "MEDIUM"

    async def _detect_momentum_direction(self, df: Optional[pd.DataFrame]) -> str:
        try:
            if df is None or df.empty or "close" not in df.columns:
                return "NEUTRAL"
            close = df["close"].values.astype(float)
            macd, macdsig, _ = talib.MACD(close, 12, 26, 9)
            rsi = talib.RSI(close, timeperiod=14)
            if np.isnan(macd[-1]) or np.isnan(macdsig[-1]) or np.isnan(rsi[-1]):
                return "NEUTRAL"
            if macd[-1] > macdsig[-1] and rsi[-1] > 50:
                return "BULLISH"
            if macd[-1] < macdsig[-1] and rsi[-1] < 50:
                return "BEARISH"
            return "NEUTRAL"
        except Exception:
            return "NEUTRAL"

    def _get_trading_session(self) -> str:
        """
        Aproximación de sesiones en UTC.
        ASIAN: 00:00-08:00, EUROPEAN: 07:00-15:00, US: 13:00-21:00, OVERLAP: 13:00-15:00
        """
        now_utc = datetime.utcnow().time()
        h = now_utc.hour
        if 13 <= h < 15:
            return "OVERLAP"
        if 13 <= h < 21:
            return "US"
        if 7 <= h < 15:
            return "EUROPEAN"
        return "ASIAN"

    def _calculate_market_hours_factor(self, session: str) -> float:
        adj = SESSION_ADJUSTMENTS.get(session, SESSION_ADJUSTMENTS["EUROPEAN"])
        return float(adj.get("liquidity_factor", 1.0))

    def _calculate_trend_strength(self, df: Optional[pd.DataFrame]) -> float:
        try:
            if df is None or df.empty or "close" not in df.columns:
                return 0.5
            close = df["close"].values.astype(float)
            ema = talib.EMA(close, timeperiod=50)
            if len(close) < 60 or np.isnan(ema[-1]):
                return 0.5
            # Fuerza por distancia relativa al EMA
            rel = abs(close[-1] - ema[-1]) / max(1e-9, ema[-1])
            return float(np.clip(rel * 5.0, 0.0, 1.0))
        except Exception:
            return 0.5

    async def _get_key_levels(self, df: Optional[pd.DataFrame]) -> Dict[str, List[float]]:
        """
        Niveles básicos: pivots recientes + niveles psicológicos (00, 50).
        """
        try:
            if df is None or len(df) == 0:
                return {"support": [], "resistance": [], "all_levels": []}

            highs = df["high"].tail(50) if "high" in df.columns else pd.Series([])
            lows = df["low"].tail(50) if "low" in df.columns else pd.Series([])
            levels_r = sorted([float(x) for x in highs.nlargest(3).values]) if len(highs) else []
            levels_s = sorted([float(x) for x in lows.nsmallest(3).values]) if len(lows) else []

            # Psicológicos cercanos
            last_price = float(df["close"].iloc[-1]) if "close" in df.columns else None
            psycho = []
            if last_price:
                base = int(last_price)
                for k in (-200, -100, -50, -20, -10, -5, 0, 5, 10, 20, 50, 100, 200):
                    lvl = base + k
                    if lvl > 0:
                        psycho.append(float(lvl))

            all_levels = sorted(set(levels_r + levels_s + psycho))
            return {"support": levels_s, "resistance": levels_r, "all_levels": all_levels}
        except Exception:
            return {"support": [], "resistance": [], "all_levels": []}

    # ----------------------------- Timing factors -----------------------------

    async def _calculate_levels_proximity(self, symbol: str, signal: str) -> float:
        try:
            # Obtener datos de los últimos 120 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=120)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=120)
            if df is None or df.empty or len(df) < 50:
                return 0.5
            if "close" not in df.columns:
                return 0.5
                
            levels = await self._get_key_levels(df)
            price = float(df["close"].iloc[-1])

            nearest_r = min((abs(price - r) for r in levels["resistance"]), default=math.inf)
            nearest_s = min((abs(price - s) for s in levels["support"]), default=math.inf)
            width = max(price * 0.002, np.std(df["close"].tail(50)) if len(df) >= 50 else price * 0.002)

            if signal in ("BUY", "LONG"):
                # Mejor lejos de resistencia
                score = float(np.clip(nearest_r / (width * 2.0), 0.0, 1.0))
                return score
            if signal in ("SELL", "SHORT"):
                # Mejor lejos de soporte
                score = float(np.clip(nearest_s / (width * 2.0), 0.0, 1.0))
                return score
            return 0.5
        except Exception:
            return 0.5

    def _calculate_session_timing_factor(self) -> float:
        ses = self._get_trading_session()
        adj = SESSION_ADJUSTMENTS.get(ses, SESSION_ADJUSTMENTS["EUROPEAN"])
        # Liquidity factor directamente como score básico
        return float(np.clip(adj.get("liquidity_factor", 1.0), 0.5, 1.1) / 1.1)

    async def _calculate_volatility_timing_factor(self, symbol: str) -> float:
        try:
            # Obtener datos de los últimos 120 períodos
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=120)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=120)
            if df is None or df.empty or len(df) < 50:
                return 0.5
            if not all(col in df.columns for col in ["high", "low", "close"]):
                return 0.5
                
            high = df["high"].values.astype(float)
            low = df["low"].values.astype(float)
            close = df["close"].values.astype(float)
            atr = talib.ATR(high, low, close, timeperiod=14)
            if len(atr) < 20 or np.isnan(atr[-1]):
                return 0.5
            current = float(atr[-1])
            avg = float(np.nanmean(atr[-50:])) if len(atr) >= 50 else current
            ratio = current / avg if avg > 0 else 1.0
            # Preferible ratio en torno a 1.0 (ni muy bajo ni extremo)
            return float(np.clip(1.5 - abs(ratio - 1.0), 0.0, 1.0))
        except Exception:
            return 0.5

    async def _calculate_momentum_timing_factor(self, symbol: str, signal: str) -> float:
        try:
            # Obtener datos de los últimos 100 períodos de 15m
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=100*15)
            df = await self._get_market_data_sqlite(symbol, start_time, end_time, limit=100)
            if df is None or df.empty or len(df) < 50:
                return 0.5
            if "close" not in df.columns:
                return 0.5
                
            close = df["close"].values.astype(float)
            macd, macdsig, _ = talib.MACD(close, 12, 26, 9)
            if np.isnan(macd[-1]) or np.isnan(macdsig[-1]):
                return 0.5
            bull = macd[-1] > macdsig[-1]
            if signal in ("BUY", "LONG"):
                return 0.85 if bull else 0.35
            if signal in ("SELL", "SHORT"):
                return 0.85 if not bull else 0.35
            return 0.5
        except Exception:
            return 0.5

    async def _calculate_confluence_factor(self, symbol: str, signal: str) -> float:
        c = await self.check_confluences(symbol, signal)
        # 3 confluencias: PA, indicadores, tendencia
        return float(np.clip((0.34 * c["price_action"]) + (0.33 * c["indicators"]) + (0.33 * c["trend"]), 0.0, 1.0))

    def _get_volatility_adjustment_score(self, level: str) -> float:
        return {"LOW": 0.9, "MEDIUM": 0.8, "HIGH": 0.6, "EXTREME": 0.2}.get(level, 0.8)

    # ----------------------------- Métricas & resumen -----------------------------

    def _update_metrics(self, sq: SignalQuality, latency_ms: float) -> None:
        try:
            self.metrics["processing_latency_ms"] = (
                0.9 * float(self.metrics.get("processing_latency_ms", 0.0)) + 0.1 * float(latency_ms)
            )
            # Media móvil simple del quality_score
            self.metrics["average_quality_score"] = (
                0.98 * float(self.metrics.get("average_quality_score", 0.0)) + 0.02 * float(sq.quality_score)
            )
            self.metrics["timeframe_consistency_avg"] = (
                0.98 * float(self.metrics.get("timeframe_consistency_avg", 0.0)) + 0.02 * float(sq.consistency)
            )
            if sq.volume_confirmation:
                prev = float(self.metrics.get("volume_confirmation_rate", 0.0))
                self.metrics["volume_confirmation_rate"] = 0.98 * prev + 0.02 * 1.0

            # buckets de calidad (para futuras validaciones)
            if sq.quality_score > 0.80:
                self.metrics["accuracy_by_score_bucket"]["high_quality"].append(sq.quality_score)
            elif sq.quality_score > 0.60:
                self.metrics["accuracy_by_score_bucket"]["medium_quality"].append(sq.quality_score)
            else:
                self.metrics["accuracy_by_score_bucket"]["low_quality"].append(sq.quality_score)

            self.metrics["signals_by_regime"][sq.market_regime] += 1
        except Exception:
            pass

    def get_processing_summary(self) -> Dict[str, Any]:
        return {
            "processed": self.metrics.get("signals_processed", 0),
            "approved": self.metrics.get("signals_approved", 0),
            "rejected": self.metrics.get("signals_rejected", 0),
            "avg_score": round(float(self.metrics.get("average_quality_score", 0.0)), 4),
            "avg_consistency": round(float(self.metrics.get("timeframe_consistency_avg", 0.0)), 4),
            "latency_ms": round(float(self.metrics.get("processing_latency_ms", 0.0)), 2),
            "by_regime": dict(self.metrics.get("signals_by_regime", {})),
        }

    # ----------------------------- Testing & validación -----------------------------

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica que componentes básicos respondan.
        """
        ok_db = True
        ok_pred = True
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)
            _ = await self._get_market_data_sqlite(self.trading_config.get("symbol", "BTCUSDT"), start_time, end_time, limit=2)
        except Exception:
            ok_db = False
        try:
            # intento de features mínimo (no bloqueante si falla)
            df = data_preprocessor.get_raw_data(self.trading_config.get("symbol", "BTCUSDT"), days_back=1, timeframe="1h")
            if not df.empty:
                _ = data_preprocessor.prepare_prediction_data(df)
        except Exception:
            ok_pred = False
        return {"db_ok": ok_db, "features_ok": ok_pred}

    async def test_signal_processing(self, symbol: str) -> Dict[str, Any]:
        sq = await self.process_signal(symbol, timeframe=self.primary_timeframe)
        should, reason = await self.should_execute_signal(sq)
        return {
            "signal": sq.signal,
            "confidence": round(sq.confidence, 4),
            "score": round(sq.quality_score, 4),
            "consistency": round(sq.consistency, 4),
            "timing": round(sq.timing_score, 4),
            "volatility": sq.volatility_level,
            "regime": sq.market_regime,
            "should_execute": should,
            "reason": reason,
            "filters": sq.filtering_applied,
        }

    async def validate_filters_performance(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Placeholder simple: en producción, evalúa señales históricas vs desempeño.
        """
        return {
            "window_days": days_back,
            "most_effective_filters": {
                "trend_filter": 0.78,
                "volume_filter": 0.72,
                "levels_filter": 0.69,
            },
            "notes": "Para validación real, cruzar con outcomes de trades históricos.",
        }

    async def analyze_rejected_signals(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Placeholder simple: en producción, consulta señales rechazadas persistidas.
        """
        top_reasons = sorted(
            self.metrics["filter_rejection_reasons"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        return {
            "window_days": days_back,
            "top_rejection_reasons": top_reasons,
            "notes": "Conectar a tu storage de señales rechazadas si lo tienes.",
        }

    # ----------------------------- Utilidades privadas -----------------------------

    def _default_market_context(self) -> Dict[str, Any]:
        return {
            "regime": "UNKNOWN",
            "volatility_level": "MEDIUM",
            "momentum": "NEUTRAL",
            "session": self._get_trading_session(),
            "hours_factor": self._calculate_market_hours_factor(self._get_trading_session()),
            "trend_strength": 0.5,
            "support_resistance": {"support": [], "resistance": [], "all_levels": []},
        }

    def _create_null_signal(self, reason: str) -> SignalQuality:
        self.metrics["signals_rejected"] += 1
        self.metrics["filter_rejection_reasons"][reason] += 1
        return SignalQuality(
            signal="HOLD",
            confidence=0.0,
            quality_score=0.0,
            strength=0.0,
            consistency=0.0,
            timing_score=0.0,
            risk_score=0.0,
            rejection_reasons=[reason],
        )


# Instancia global
signal_processor = SignalProcessor()
