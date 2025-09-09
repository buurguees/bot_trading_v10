# Ruta: core/data/enterprise/data_validator.py
# data_validator.py - Validador de datos enterprise
# Ubicación: C:\TradingBot_v10\data\enterprise\data_validator.py

import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from config.enterprise_config import get_enterprise_config
from .stream_collector import MarketTick

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Resultado de validación de datos"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    confidence_score: float = 0.0

class DataValidator:
    """Validador de datos enterprise"""
    
    def __init__(self):
        """Inicializar el validador de datos"""
        self.config = get_enterprise_config()
        self.validation_config = self.config.get_validation_config()
        
        # Configuración de validación
        self.price_config = self.validation_config.get("price", {})
        self.volume_config = self.validation_config.get("volume", {})
        self.timestamp_config = self.validation_config.get("timestamp", {})
        
        # Historial para detección de outliers
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        
        # Métricas
        self.metrics = {
            "validations_total": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "outliers_detected": 0,
            "duplicates_detected": 0,
            "timestamps_out_of_order": 0,
            "last_validation_time": None,
            "errors_total": 0
        }
        
        logger.info("DataValidator inicializado")
    
    def validate_tick(self, tick: MarketTick) -> ValidationResult:
        """Validar tick de mercado"""
        try:
            self.metrics["validations_total"] += 1
            self.metrics["last_validation_time"] = datetime.now(timezone.utc)
            
            errors = []
            warnings = []
            confidence_score = 1.0
            
            # Validar precio
            price_result = self._validate_price(tick.symbol, tick.price)
            if not price_result.is_valid:
                errors.extend(price_result.errors)
                confidence_score *= 0.5
            warnings.extend(price_result.warnings)
            
            # Validar volumen
            volume_result = self._validate_volume(tick.symbol, tick.volume)
            if not volume_result.is_valid:
                errors.extend(volume_result.errors)
                confidence_score *= 0.5
            warnings.extend(volume_result.warnings)
            
            # Validar timestamp
            timestamp_result = self._validate_timestamp(tick.timestamp)
            if not timestamp_result.is_valid:
                errors.extend(timestamp_result.errors)
                confidence_score *= 0.3
            warnings.extend(timestamp_result.warnings)
            
            # Validar bid/ask
            if tick.bid and tick.ask:
                bid_ask_result = self._validate_bid_ask(tick.bid, tick.ask)
                if not bid_ask_result.is_valid:
                    errors.extend(bid_ask_result.errors)
                    confidence_score *= 0.8
                warnings.extend(bid_ask_result.warnings)
            
            # Validar símbolo
            symbol_result = self._validate_symbol(tick.symbol)
            if not symbol_result.is_valid:
                errors.extend(symbol_result.errors)
                confidence_score *= 0.2
            warnings.extend(symbol_result.warnings)
            
            # Determinar si es válido
            is_valid = len(errors) == 0
            
            if is_valid:
                self.metrics["validations_passed"] += 1
            else:
                self.metrics["validations_failed"] += 1
                self.metrics["errors_total"] += 1
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error validando tick {tick.symbol}: {e}")
            self.metrics["errors_total"] += 1
            return ValidationResult(
                is_valid=False,
                errors=[f"Error interno de validación: {str(e)}"],
                warnings=[],
                confidence_score=0.0
            )
    
    def _validate_price(self, symbol: str, price: float) -> ValidationResult:
        """Validar precio"""
        errors = []
        warnings = []
        
        try:
            # Validar que el precio sea positivo
            if price <= 0:
                errors.append(f"Precio debe ser positivo: {price}")
                return ValidationResult(False, errors, warnings)
            
            # Validar umbrales de cambio
            min_change = self.price_config.get("min_change_threshold", 0.0001)
            max_change = self.price_config.get("max_change_threshold", 0.2)
            
            if symbol in self.price_history and len(self.price_history[symbol]) > 0:
                last_price = self.price_history[symbol][-1]
                price_change = abs(price - last_price) / last_price
                
                if price_change < min_change:
                    warnings.append(f"Cambio de precio muy pequeño: {price_change:.6f}")
                
                if price_change > max_change:
                    errors.append(f"Cambio de precio muy grande: {price_change:.6f}")
                    return ValidationResult(False, errors, warnings)
                
                # Detección de outliers
                if self.price_config.get("outlier_detection", True):
                    outlier_result = self._detect_price_outlier(symbol, price)
                    if outlier_result:
                        errors.append(f"Precio outlier detectado: {price}")
                        self.metrics["outliers_detected"] += 1
                        return ValidationResult(False, errors, warnings)
            
            # Actualizar historial
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(price)
            
            # Mantener solo los últimos 1000 precios
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando precio {symbol}: {e}")
            return ValidationResult(False, [f"Error validando precio: {str(e)}], warnings)
    
    def _validate_volume(self, symbol: str, volume: float) -> ValidationResult:
        """Validar volumen"""
        errors = []
        warnings = []
        
        try:
            # Validar que el volumen sea no negativo
            if volume < 0:
                errors.append(f"Volumen no puede ser negativo: {volume}")
                return ValidationResult(False, errors, warnings)
            
            # Validar volumen mínimo
            min_volume = self.volume_config.get("min_volume", 0.01)
            if volume < min_volume:
                warnings.append(f"Volumen muy pequeño: {volume}")
            
            # Validar cambio de volumen
            max_volume_change = self.volume_config.get("max_volume_change", 10.0)
            
            if symbol in self.volume_history and len(self.volume_history[symbol]) > 0:
                last_volume = self.volume_history[symbol][-1]
                if last_volume > 0:
                    volume_change = abs(volume - last_volume) / last_volume
                    
                    if volume_change > max_volume_change:
                        warnings.append(f"Cambio de volumen muy grande: {volume_change:.2f}")
            
            # Actualizar historial
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            
            self.volume_history[symbol].append(volume)
            
            # Mantener solo los últimos 1000 volúmenes
            if len(self.volume_history[symbol]) > 1000:
                self.volume_history[symbol] = self.volume_history[symbol][-1000:]
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando volumen {symbol}: {e}")
            return ValidationResult(False, [f"Error validando volumen: {str(e)}], warnings)
    
    def _validate_timestamp(self, timestamp: datetime) -> ValidationResult:
        """Validar timestamp"""
        errors = []
        warnings = []
        
        try:
            now = datetime.now(timezone.utc)
            
            # Validar que el timestamp no sea del futuro
            if timestamp > now:
                errors.append(f"Timestamp en el futuro: {timestamp}")
                return ValidationResult(False, errors, warnings)
            
            # Validar delay máximo
            max_delay = self.timestamp_config.get("max_delay_seconds", 30)
            delay = (now - timestamp).total_seconds()
            
            if delay > max_delay:
                warnings.append(f"Timestamp con delay alto: {delay:.2f}s")
            
            # Validar que no sea muy antiguo
            max_age = 3600  # 1 hora
            if delay > max_age:
                errors.append(f"Timestamp muy antiguo: {delay:.2f}s")
                return ValidationResult(False, errors, warnings)
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando timestamp: {e}")
            return ValidationResult(False, [f"Error validando timestamp: {str(e)}], warnings)
    
    def _validate_bid_ask(self, bid: float, ask: float) -> ValidationResult:
        """Validar bid/ask"""
        errors = []
        warnings = []
        
        try:
            # Validar que bid y ask sean positivos
            if bid <= 0 or ask <= 0:
                errors.append(f"Bid/ask deben ser positivos: bid={bid}, ask={ask}")
                return ValidationResult(False, errors, warnings)
            
            # Validar que ask > bid
            if ask <= bid:
                errors.append(f"Ask debe ser mayor que bid: bid={bid}, ask={ask}")
                return ValidationResult(False, errors, warnings)
            
            # Validar spread razonable
            spread = (ask - bid) / bid
            max_spread = 0.1  # 10%
            
            if spread > max_spread:
                warnings.append(f"Spread muy grande: {spread:.4f}")
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando bid/ask: {e}")
            return ValidationResult(False, [f"Error validando bid/ask: {str(e)}], warnings)
    
    def _validate_symbol(self, symbol: str) -> ValidationResult:
        """Validar símbolo"""
        errors = []
        warnings = []
        
        try:
            # Validar que el símbolo no esté vacío
            if not symbol or not symbol.strip():
                errors.append("Símbolo no puede estar vacío")
                return ValidationResult(False, errors, warnings)
            
            # Validar formato básico
            if len(symbol) < 3 or len(symbol) > 20:
                errors.append(f"Símbolo con longitud inválida: {len(symbol)}")
                return ValidationResult(False, errors, warnings)
            
            # Validar que contenga solo caracteres válidos
            if not symbol.replace("USDT", "").replace("BTC", "").replace("ETH", "").isalnum():
                warnings.append(f"Símbolo con caracteres inusuales: {symbol}")
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando símbolo {symbol}: {e}")
            return ValidationResult(False, [f"Error validando símbolo: {str(e)}], warnings)
    
    def _detect_price_outlier(self, symbol: str, price: float) -> bool:
        """Detectar outlier en precio"""
        try:
            if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
                return False
            
            prices = np.array(self.price_history[symbol])
            mean_price = np.mean(prices)
            std_price = np.std(prices)
            
            if std_price == 0:
                return False
            
            # Calcular z-score
            z_score = abs(price - mean_price) / std_price
            threshold = self.price_config.get("outlier_threshold", 3.0)
            
            return z_score > threshold
            
        except Exception as e:
            logger.error(f"Error detectando outlier de precio: {e}")
            return False
    
    def validate_ohlcv_data(self, ohlcv_data: Dict[str, Any]) -> ValidationResult:
        """Validar datos OHLCV"""
        errors = []
        warnings = []
        
        try:
            # Validar campos requeridos
            required_fields = ["open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in ohlcv_data or ohlcv_data[field] is None:
                    errors.append(f"Campo requerido faltante: {field}")
            
            if errors:
                return ValidationResult(False, errors, warnings)
            
            # Validar que high >= low
            if ohlcv_data["high"] < ohlcv_data["low"]:
                errors.append("High debe ser >= Low")
            
            # Validar que high >= open y high >= close
            if ohlcv_data["high"] < ohlcv_data["open"] or ohlcv_data["high"] < ohlcv_data["close"]:
                errors.append("High debe ser >= Open y Close")
            
            # Validar que low <= open y low <= close
            if ohlcv_data["low"] > ohlcv_data["open"] or ohlcv_data["low"] > ohlcv_data["close"]:
                errors.append("Low debe ser <= Open y Close")
            
            # Validar que todos los valores sean positivos
            for field in required_fields:
                if ohlcv_data[field] <= 0:
                    errors.append(f"{field} debe ser positivo: {ohlcv_data[field]}")
            
            # Validar volumen
            if ohlcv_data["volume"] < 0:
                errors.append(f"Volumen no puede ser negativo: {ohlcv_data['volume']}")
            
            is_valid = len(errors) == 0
            return ValidationResult(is_valid, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando datos OHLCV: {e}")
            return ValidationResult(False, [f"Error validando datos OHLCV: {str(e)}], warnings)
    
    def validate_technical_features(self, features: Dict[str, Any]) -> ValidationResult:
        """Validar features técnicos"""
        errors = []
        warnings = []
        
        try:
            # Validar RSI
            if "rsi_14" in features and features["rsi_14"] is not None:
                rsi = features["rsi_14"]
                if rsi < 0 or rsi > 100:
                    errors.append(f"RSI fuera de rango [0, 100]: {rsi}")
            
            # Validar MACD
            if "macd" in features and features["macd"] is not None:
                macd = features["macd"]
                if not isinstance(macd, (int, float)):
                    errors.append(f"MACD debe ser numérico: {macd}")
            
            # Validar Bollinger Bands
            if all(field in features for field in ["bollinger_upper", "bollinger_lower", "bollinger_middle"]):
                upper = features["bollinger_upper"]
                lower = features["bollinger_lower"]
                middle = features["bollinger_middle"]
                
                if upper is not None and lower is not None and middle is not None:
                    if upper < lower:
                        errors.append("Bollinger Upper debe ser >= Lower")
                    
                    if upper < middle or lower > middle:
                        errors.append("Bollinger Bands inválidas")
            
            # Validar que todos los valores numéricos sean finitos
            for key, value in features.items():
                if isinstance(value, (int, float)) and not np.isfinite(value):
                    errors.append(f"Valor no finito en {key}: {value}")
            
            is_valid = len(errors) == 0
            return ValidationResult(is_valid, errors, warnings)
            
        except Exception as e:
            logger.error(f"Error validando features técnicos: {e}")
            return ValidationResult(False, [f"Error validando features técnicos: {str(e)}], warnings)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del validador"""
        return self.metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del validador"""
        return {
            "is_running": True,
            "price_history_symbols": len(self.price_history),
            "volume_history_symbols": len(self.volume_history),
            "metrics": self.get_metrics()
        }
    
    def reset_metrics(self):
        """Resetear métricas"""
        self.metrics = {
            "validations_total": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "outliers_detected": 0,
            "duplicates_detected": 0,
            "timestamps_out_of_order": 0,
            "last_validation_time": None,
            "errors_total": 0
        }
    
    def cleanup_old_history(self, max_age_hours: int = 24):
        """Limpiar historial antiguo"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Limpiar historial de precios (mantener solo los últimos 1000)
            for symbol in list(self.price_history.keys()):
                if len(self.price_history[symbol]) > 1000:
                    self.price_history[symbol] = self.price_history[symbol][-1000:]
            
            # Limpiar historial de volúmenes (mantener solo los últimos 1000)
            for symbol in list(self.volume_history.keys()):
                if len(self.volume_history[symbol]) > 1000:
                    self.volume_history[symbol] = self.volume_history[symbol][-1000:]
            
            logger.info("Historial antiguo limpiado")
            
        except Exception as e:
            logger.error(f"Error limpiando historial antiguo: {e}")

# Función de conveniencia para crear validador
def create_data_validator() -> DataValidator:
    """Crear instancia del validador de datos"""
    return DataValidator()

if __name__ == "__main__":
    # Test del validador
    def test_validator():
        validator = DataValidator()
        
        # Test de tick válido
        tick = MarketTick(
            timestamp=datetime.now(timezone.utc),
            symbol="BTCUSDT",
            price=50000.0,
            volume=1.5,
            bid=49999.0,
            ask=50001.0
        )
        
        result = validator.validate_tick(tick)
        print(f"Tick válido: {result.is_valid}")
        print(f"Errores: {result.errors}")
        print(f"Warnings: {result.warnings}")
        print(f"Confidence: {result.confidence_score}")
        
        # Test de tick inválido
        bad_tick = MarketTick(
            timestamp=datetime.now(timezone.utc),
            symbol="",
            price=-1000.0,
            volume=-1.0
        )
        
        result = validator.validate_tick(bad_tick)
        print(f"\nTick inválido: {result.is_valid}")
        print(f"Errores: {result.errors}")
        
        # Mostrar métricas
        print("\n=== MÉTRICAS DEL VALIDADOR ===")
        metrics = validator.get_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")
    
    # Ejecutar test
    test_validator()
