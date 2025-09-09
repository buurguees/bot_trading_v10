"""
models/enterprise/validation_system.py - Enterprise-Grade Validation System
Sistema de validación robusto con Pydantic para datos de entrada y salida
"""

import re
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Union, List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, validator, Field, ValidationError
from enum import Enum
import logging
from dataclasses import dataclass
import warnings

logger = logging.getLogger(__name__)

class PredictionAction(str, Enum):
    """Valid prediction actions"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class ModelType(str, Enum):
    """Valid model types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    MULTI_OUTPUT = "multi_output"
    ENSEMBLE = "ensemble"

class ValidationSeverity(str, Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    sanitized_data: Any = None
    validation_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.validation_metadata is None:
            self.validation_metadata = {}

class PredictionRequest(BaseModel):
    """Validated prediction request schema"""
    symbol: str = Field(..., description="Trading symbol")
    features: List[float] = Field(..., description="Feature vector")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str = Field(..., description="Unique request identifier")
    model_version: Optional[str] = Field(None, description="Specific model version")
    model_type: ModelType = Field(ModelType.CLASSIFICATION, description="Type of model")
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    max_features: int = Field(500, ge=10, le=1000, description="Maximum number of features")
    min_features: int = Field(10, ge=5, le=100, description="Minimum number of features")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate trading symbol format"""
        if not re.match(r'^[A-Z]{3,10}USDT?$', v):
            raise ValueError('Invalid symbol format. Must be like BTCUSDT, ETHUSDT, etc.')
        return v.upper()
    
    @validator('features')
    def validate_features(cls, v, values):
        """Validate feature vector"""
        if not v:
            raise ValueError('Features cannot be empty')
        
        # Check feature count
        feature_count = len(v)
        min_features = values.get('min_features', 10)
        max_features = values.get('max_features', 500)
        
        if feature_count < min_features:
            raise ValueError(f'Too few features: {feature_count} < {min_features}')
        if feature_count > max_features:
            raise ValueError(f'Too many features: {feature_count} > {max_features}')
        
        # Check for non-numeric values
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError('All features must be numeric')
        
        # Check for NaN or Inf values
        if any(np.isnan(x) or np.isinf(x) for x in v):
            raise ValueError('Features contain NaN or Inf values')
        
        # Check for extreme values (beyond 6 standard deviations)
        features_array = np.array(v)
        if len(features_array) > 1:
            mean_val = np.mean(features_array)
            std_val = np.std(features_array)
            if std_val > 0:
                z_scores = np.abs((features_array - mean_val) / std_val)
                if np.any(z_scores > 6):
                    warnings.warn('Features contain extreme outliers (>6σ)')
        
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is recent"""
        now = datetime.now(timezone.utc)
        if v > now:
            raise ValueError('Timestamp cannot be in the future')
        
        # Check if timestamp is too old (more than 1 hour)
        if (now - v).total_seconds() > 3600:
            warnings.warn('Timestamp is more than 1 hour old')
        
        return v
    
    @validator('request_id')
    def validate_request_id(cls, v):
        """Validate request ID format"""
        if not re.match(r'^[a-zA-Z0-9_-]{8,64}$', v):
            raise ValueError('Request ID must be 8-64 alphanumeric characters with - or _')
        return v

class PredictionResponse(BaseModel):
    """Validated prediction response schema"""
    request_id: str
    symbol: str
    prediction: PredictionAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    probability_distribution: Optional[Dict[str, float]] = None
    regression_value: Optional[float] = None
    model_version: str
    processing_time_ms: float = Field(..., ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('probability_distribution')
    def validate_probability_distribution(cls, v, values):
        """Validate probability distribution sums to 1.0"""
        if v is not None:
            total_prob = sum(v.values())
            if not np.isclose(total_prob, 1.0, atol=1e-6):
                raise ValueError(f'Probability distribution must sum to 1.0, got {total_prob}')
            
            # Check for negative probabilities
            if any(p < 0 for p in v.values()):
                raise ValueError('Probability distribution cannot contain negative values')
        
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence score"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v

class MarketDataValidation(BaseModel):
    """Market data validation schema"""
    symbol: str
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    
    @validator('high')
    def validate_high(cls, v, values):
        """Validate high price is highest"""
        if 'open' in values and 'close' in values:
            if v < max(values['open'], values['close']):
                raise ValueError('High price must be >= max(open, close)')
        return v
    
    @validator('low')
    def validate_low(cls, v, values):
        """Validate low price is lowest"""
        if 'open' in values and 'close' in values:
            if v > min(values['open'], values['close']):
                raise ValueError('Low price must be <= min(open, close)')
        return v
    
    @validator('volume')
    def validate_volume(cls, v):
        """Validate volume is reasonable"""
        if v < 0:
            raise ValueError('Volume cannot be negative')
        if v > 1e12:  # 1 trillion
            warnings.warn('Volume seems unusually high')
        return v

class DataSanitizer:
    """Enterprise-grade data sanitization"""
    
    @staticmethod
    def sanitize_features(features: np.ndarray, 
                         method: str = "winsorize",
                         outlier_threshold: float = 6.0) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Sanitize and normalize features with bounds checking
        
        Args:
            features: Input feature array
            method: Sanitization method ("winsorize", "clip", "remove")
            outlier_threshold: Z-score threshold for outlier detection
        
        Returns:
            Tuple of (sanitized_features, sanitization_metadata)
        """
        sanitization_metadata = {
            'original_shape': features.shape,
            'original_mean': float(np.mean(features)),
            'original_std': float(np.std(features)),
            'outliers_detected': 0,
            'outliers_removed': 0,
            'method_used': method
        }
        
        try:
            # Remove NaN and Inf values
            valid_mask = np.isfinite(features)
            if not np.all(valid_mask):
                features = features[valid_mask]
                sanitization_metadata['nan_inf_removed'] = np.sum(~valid_mask)
            
            if len(features) == 0:
                raise ValueError("All features are NaN or Inf")
            
            # Detect outliers
            if len(features) > 1:
                z_scores = np.abs((features - np.mean(features)) / np.std(features))
                outlier_mask = z_scores > outlier_threshold
                sanitization_metadata['outliers_detected'] = np.sum(outlier_mask)
                
                if method == "winsorize":
                    # Winsorize outliers to threshold
                    percentile_high = 100 - (100 * np.sum(outlier_mask) / len(features)) / 2
                    percentile_low = 100 - percentile_high
                    
                    high_bound = np.percentile(features, percentile_high)
                    low_bound = np.percentile(features, percentile_low)
                    
                    features = np.clip(features, low_bound, high_bound)
                    sanitization_metadata['winsorize_bounds'] = [float(low_bound), float(high_bound)]
                
                elif method == "clip":
                    # Clip to 6 standard deviations
                    mean_val = np.mean(features)
                    std_val = np.std(features)
                    features = np.clip(features, 
                                     mean_val - outlier_threshold * std_val,
                                     mean_val + outlier_threshold * std_val)
                
                elif method == "remove":
                    # Remove outliers
                    features = features[~outlier_mask]
                    sanitization_metadata['outliers_removed'] = np.sum(outlier_mask)
            
            # Final validation
            if len(features) == 0:
                raise ValueError("No valid features after sanitization")
            
            sanitization_metadata['final_shape'] = features.shape
            sanitization_metadata['final_mean'] = float(np.mean(features))
            sanitization_metadata['final_std'] = float(np.std(features))
            
            return features, sanitization_metadata
            
        except Exception as e:
            logger.error(f"Error in feature sanitization: {e}")
            raise ValueError(f"Feature sanitization failed: {e}")
    
    @staticmethod
    def validate_market_data(data: pd.DataFrame) -> ValidationResult:
        """
        Comprehensive market data validation
        
        Args:
            data: DataFrame with OHLCV data
        
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        sanitized_data = data.copy()
        
        try:
            # Check required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                errors.append(f"Missing required columns: {missing_columns}")
                return ValidationResult(False, errors, warnings)
            
            # Check for empty data
            if data.empty:
                errors.append("DataFrame is empty")
                return ValidationResult(False, errors, warnings)
            
            # Check for NaN values
            nan_counts = data[required_columns].isna().sum()
            if nan_counts.any():
                warnings.append(f"NaN values found: {nan_counts.to_dict()}")
                sanitized_data = data.dropna()
            
            # Validate OHLC constraints
            ohlc_errors = []
            for idx, row in sanitized_data.iterrows():
                o, h, l, c, v = row['open'], row['high'], row['low'], row['close'], row['volume']
                
                if h < max(o, c):
                    ohlc_errors.append(f"Row {idx}: High ({h}) < max(open, close) ({max(o, c)})")
                if l > min(o, c):
                    ohlc_errors.append(f"Row {idx}: Low ({l}) > min(open, close) ({min(o, c)})")
                if h < l:
                    ohlc_errors.append(f"Row {idx}: High ({h}) < Low ({l})")
                if o <= 0 or h <= 0 or l <= 0 or c <= 0:
                    ohlc_errors.append(f"Row {idx}: Non-positive price values")
                if v < 0:
                    ohlc_errors.append(f"Row {idx}: Negative volume ({v})")
            
            if ohlc_errors:
                errors.extend(ohlc_errors)
            
            # Check for suspicious price movements
            if len(sanitized_data) > 1:
                price_changes = sanitized_data['close'].pct_change().dropna()
                extreme_moves = price_changes[abs(price_changes) > 0.5]  # >50% moves
                if len(extreme_moves) > 0:
                    warnings.append(f"Extreme price movements detected: {len(extreme_moves)} moves >50%")
                
                # Check for gaps in time series
                if 'timestamp' in sanitized_data.columns:
                    time_diffs = sanitized_data['timestamp'].diff().dropna()
                    if len(time_diffs) > 0:
                        median_diff = time_diffs.median()
                        large_gaps = time_diffs > median_diff * 3
                        if large_gaps.any():
                            warnings.append(f"Large time gaps detected: {large_gaps.sum()} gaps >3x median")
            
            # Check volume consistency
            if len(sanitized_data) > 1:
                volume_changes = sanitized_data['volume'].pct_change().dropna()
                extreme_volume = volume_changes[abs(volume_changes) > 10]  # >1000% volume change
                if len(extreme_volume) > 0:
                    warnings.append(f"Extreme volume changes detected: {len(extreme_volume)} changes >1000%")
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_data=sanitized_data if is_valid else None,
                validation_metadata={
                    'total_rows': len(data),
                    'valid_rows': len(sanitized_data),
                    'ohlc_errors': len(ohlc_errors),
                    'extreme_moves': len(extreme_moves) if 'extreme_moves' in locals() else 0,
                    'validation_timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error in market data validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings
            )
    
    @staticmethod
    def validate_prediction_input(features: Union[List[float], np.ndarray], 
                                symbol: str,
                                model_type: ModelType = ModelType.CLASSIFICATION) -> ValidationResult:
        """
        Validate prediction input data
        
        Args:
            features: Feature vector
            symbol: Trading symbol
            model_type: Type of model
        
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        try:
            # Convert to numpy array
            if isinstance(features, list):
                features = np.array(features)
            
            # Basic validation
            if not isinstance(features, np.ndarray):
                errors.append("Features must be numpy array or list")
                return ValidationResult(False, errors, warnings)
            
            if features.size == 0:
                errors.append("Features cannot be empty")
                return ValidationResult(False, errors, warnings)
            
            # Check for NaN or Inf
            if not np.all(np.isfinite(features)):
                errors.append("Features contain NaN or Inf values")
                return ValidationResult(False, errors, warnings)
            
            # Check feature count
            if len(features) < 10:
                errors.append(f"Too few features: {len(features)} < 10")
            elif len(features) > 500:
                warnings.append(f"Large feature vector: {len(features)} features")
            
            # Check for extreme values
            if len(features) > 1:
                z_scores = np.abs((features - np.mean(features)) / np.std(features))
                extreme_values = np.sum(z_scores > 6)
                if extreme_values > 0:
                    warnings.append(f"Extreme values detected: {extreme_values} values >6σ")
            
            # Validate symbol
            if not re.match(r'^[A-Z]{3,10}USDT?$', symbol):
                errors.append(f"Invalid symbol format: {symbol}")
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_data=features if is_valid else None,
                validation_metadata={
                    'feature_count': len(features),
                    'feature_range': [float(np.min(features)), float(np.max(features))],
                    'feature_mean': float(np.mean(features)),
                    'feature_std': float(np.std(features)),
                    'symbol': symbol,
                    'model_type': model_type.value,
                    'validation_timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error in prediction input validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings
            )

class ValidationPipeline:
    """Complete validation pipeline for ML operations"""
    
    def __init__(self):
        self.sanitizer = DataSanitizer()
        self.validation_history = []
    
    def validate_prediction_request(self, request_data: Dict[str, Any]) -> Tuple[PredictionRequest, ValidationResult]:
        """
        Validate complete prediction request
        
        Args:
            request_data: Raw request data
        
        Returns:
            Tuple of (validated_request, validation_result)
        """
        try:
            # Validate with Pydantic
            validated_request = PredictionRequest(**request_data)
            
            # Additional sanitization
            sanitized_features, sanitization_metadata = self.sanitizer.sanitize_features(
                np.array(validated_request.features)
            )
            
            # Update request with sanitized features
            validated_request.features = sanitized_features.tolist()
            
            # Create validation result
            validation_result = ValidationResult(
                is_valid=True,
                sanitized_data=validated_request,
                validation_metadata={
                    'sanitization': sanitization_metadata,
                    'pydantic_validation': 'passed'
                }
            )
            
            # Log validation
            self.validation_history.append({
                'timestamp': datetime.now(),
                'request_id': validated_request.request_id,
                'symbol': validated_request.symbol,
                'validation_passed': True
            })
            
            return validated_request, validation_result
            
        except ValidationError as e:
            validation_result = ValidationResult(
                is_valid=False,
                errors=[f"Pydantic validation error: {str(e)}"],
                validation_metadata={'pydantic_validation': 'failed'}
            )
            
            self.validation_history.append({
                'timestamp': datetime.now(),
                'request_id': request_data.get('request_id', 'unknown'),
                'symbol': request_data.get('symbol', 'unknown'),
                'validation_passed': False,
                'error': str(e)
            })
            
            return None, validation_result
            
        except Exception as e:
            validation_result = ValidationResult(
                is_valid=False,
                errors=[f"Validation pipeline error: {str(e)}"],
                validation_metadata={'pipeline_error': True}
            )
            
            return None, validation_result
    
    def validate_market_data_batch(self, data: pd.DataFrame) -> ValidationResult:
        """Validate batch of market data"""
        return self.sanitizer.validate_market_data(data)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {'total_validations': 0}
        
        recent_validations = [
            v for v in self.validation_history 
            if (datetime.now() - v['timestamp']).total_seconds() < 3600
        ]
        
        passed = sum(1 for v in recent_validations if v['validation_passed'])
        total = len(recent_validations)
        
        return {
            'total_validations': len(self.validation_history),
            'recent_validations': total,
            'recent_success_rate': passed / total if total > 0 else 0.0,
            'last_validation': self.validation_history[-1]['timestamp'].isoformat() if self.validation_history else None
        }

# Global validation pipeline instance
validation_pipeline = ValidationPipeline()

# Convenience functions
def validate_prediction_request(request_data: Dict[str, Any]) -> Tuple[PredictionRequest, ValidationResult]:
    """Validate prediction request"""
    return validation_pipeline.validate_prediction_request(request_data)

def validate_market_data(data: pd.DataFrame) -> ValidationResult:
    """Validate market data"""
    return validation_pipeline.validate_market_data_batch(data)

def sanitize_features(features: np.ndarray, method: str = "winsorize") -> Tuple[np.ndarray, Dict[str, Any]]:
    """Sanitize features"""
    return DataSanitizer.sanitize_features(features, method)

def get_validation_stats() -> Dict[str, Any]:
    """Get validation statistics"""
    return validation_pipeline.get_validation_stats()
