"""
models/enterprise/observability.py - Enterprise Observability and Monitoring
Sistema completo de observabilidad para modelos ML enterprise
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import asyncio
from pathlib import Path

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when prometheus is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    class CollectorRegistry:
        def __init__(self): pass
    def start_http_server(*args, **kwargs): pass

# OpenTelemetry tracing
try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Mock classes
    class trace:
        @staticmethod
        def get_tracer(*args): return MockTracer()
        @staticmethod
        def get_current_span(): return MockSpan()
    class MockTracer:
        def start_span(self, *args, **kwargs): return MockSpan()
    class MockSpan:
        def set_attribute(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"

@dataclass
class Alert:
    """Alert definition"""
    name: str
    condition: str
    threshold: float
    severity: str = "warning"
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

class MLMetricsCollector:
    """Comprehensive ML metrics collection"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._lock = threading.RLock()
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Custom metrics storage
        self.custom_metrics = defaultdict(list)
        self.metric_history = deque(maxlen=10000)
        
        # Alerting
        self.alerts = {}
        self.alert_history = deque(maxlen=1000)
        
        logger.info("MLMetricsCollector initialized")
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus not available, using mock metrics")
            return
        
        # Prediction metrics
        self.predictions_total = Counter(
            'ml_predictions_total',
            'Total number of predictions made',
            ['model_version', 'symbol', 'outcome', 'fallback_used'],
            registry=self.registry
        )
        
        self.prediction_latency = Histogram(
            'ml_prediction_duration_seconds',
            'Time spent making predictions',
            ['model_version', 'symbol'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )
        
        self.prediction_errors = Counter(
            'ml_prediction_errors_total',
            'Total number of prediction errors',
            ['model_version', 'symbol', 'error_type'],
            registry=self.registry
        )
        
        # Model metrics
        self.model_accuracy = Gauge(
            'ml_model_accuracy',
            'Current model accuracy',
            ['model_version', 'timeframe', 'symbol'],
            registry=self.registry
        )
        
        self.model_confidence = Histogram(
            'ml_model_confidence',
            'Prediction confidence distribution',
            ['model_version', 'symbol'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Feature metrics
        self.feature_drift = Gauge(
            'ml_feature_drift_score',
            'Feature drift detection score',
            ['feature_name', 'model_version'],
            registry=self.registry
        )
        
        self.feature_importance = Gauge(
            'ml_feature_importance',
            'Feature importance score',
            ['feature_name', 'model_version'],
            registry=self.registry
        )
        
        # System metrics
        self.model_memory_usage = Gauge(
            'ml_model_memory_usage_bytes',
            'Memory usage of models',
            ['model_version'],
            registry=self.registry
        )
        
        self.model_load_time = Histogram(
            'ml_model_load_duration_seconds',
            'Time to load models',
            ['model_version'],
            registry=self.registry
        )
        
        # Business metrics
        self.trading_pnl = Gauge(
            'trading_pnl_total',
            'Total P&L from ML-driven trades',
            ['symbol', 'strategy', 'model_version'],
            registry=self.registry
        )
        
        self.trade_volume = Counter(
            'trading_volume_total',
            'Total trading volume',
            ['symbol', 'action', 'model_version'],
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'ml_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['circuit_name'],
            registry=self.registry
        )
        
        self.circuit_breaker_failures = Counter(
            'ml_circuit_breaker_failures_total',
            'Circuit breaker failures',
            ['circuit_name', 'failure_type'],
            registry=self.registry
        )
        
        # Fallback metrics
        self.fallback_usage = Counter(
            'ml_fallback_usage_total',
            'Fallback strategy usage',
            ['fallback_type', 'strategy_name', 'success'],
            registry=self.registry
        )
    
    def record_prediction(self, 
                         model_version: str,
                         symbol: str,
                         outcome: str,
                         confidence: float,
                         latency_seconds: float,
                         fallback_used: bool = False):
        """Record prediction metrics"""
        with self._lock:
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.predictions_total.labels(
                    model_version=model_version,
                    symbol=symbol,
                    outcome=outcome,
                    fallback_used=str(fallback_used)
                ).inc()
                
                self.prediction_latency.labels(
                    model_version=model_version,
                    symbol=symbol
                ).observe(latency_seconds)
                
                self.model_confidence.labels(
                    model_version=model_version,
                    symbol=symbol
                ).observe(confidence)
            
            # Custom metrics
            self.custom_metrics['predictions'].append({
                'timestamp': datetime.now(),
                'model_version': model_version,
                'symbol': symbol,
                'outcome': outcome,
                'confidence': confidence,
                'latency_seconds': latency_seconds,
                'fallback_used': fallback_used
            })
            
            # Store in history
            self.metric_history.append(MetricPoint(
                timestamp=datetime.now(),
                name='prediction_latency',
                value=latency_seconds,
                labels={'model_version': model_version, 'symbol': symbol}
            ))
    
    def record_prediction_error(self,
                               model_version: str,
                               symbol: str,
                               error_type: str):
        """Record prediction error"""
        with self._lock:
            if PROMETHEUS_AVAILABLE:
                self.prediction_errors.labels(
                    model_version=model_version,
                    symbol=symbol,
                    error_type=error_type
                ).inc()
            
            self.custom_metrics['errors'].append({
                'timestamp': datetime.now(),
                'model_version': model_version,
                'symbol': symbol,
                'error_type': error_type
            })
    
    def record_model_accuracy(self,
                             model_version: str,
                             timeframe: str,
                             symbol: str,
                             accuracy: float):
        """Record model accuracy"""
        with self._lock:
            if PROMETHEUS_AVAILABLE:
                self.model_accuracy.labels(
                    model_version=model_version,
                    timeframe=timeframe,
                    symbol=symbol
                ).set(accuracy)
            
            self.custom_metrics['accuracy'].append({
                'timestamp': datetime.now(),
                'model_version': model_version,
                'timeframe': timeframe,
                'symbol': symbol,
                'accuracy': accuracy
            })
    
    def record_feature_drift(self,
                            feature_name: str,
                            model_version: str,
                            drift_score: float):
        """Record feature drift score"""
        with self._lock:
            if PROMETHEUS_AVAILABLE:
                self.feature_drift.labels(
                    feature_name=feature_name,
                    model_version=model_version
                ).set(drift_score)
            
            self.custom_metrics['feature_drift'].append({
                'timestamp': datetime.now(),
                'feature_name': feature_name,
                'model_version': model_version,
                'drift_score': drift_score
            })
    
    def record_circuit_breaker_state(self,
                                   circuit_name: str,
                                   state: str):
        """Record circuit breaker state"""
        with self._lock:
            state_value = {'closed': 0, 'open': 1, 'half_open': 2}.get(state, -1)
            
            if PROMETHEUS_AVAILABLE:
                self.circuit_breaker_state.labels(
                    circuit_name=circuit_name
                ).set(state_value)
            
            self.custom_metrics['circuit_breakers'].append({
                'timestamp': datetime.now(),
                'circuit_name': circuit_name,
                'state': state,
                'state_value': state_value
            })
    
    def record_fallback_usage(self,
                            fallback_type: str,
                            strategy_name: str,
                            success: bool):
        """Record fallback usage"""
        with self._lock:
            if PROMETHEUS_AVAILABLE:
                self.fallback_usage.labels(
                    fallback_type=fallback_type,
                    strategy_name=strategy_name,
                    success=str(success)
                ).inc()
            
            self.custom_metrics['fallbacks'].append({
                'timestamp': datetime.now(),
                'fallback_type': fallback_type,
                'strategy_name': strategy_name,
                'success': success
            })
    
    def record_business_metric(self,
                              metric_name: str,
                              value: float,
                              labels: Dict[str, str] = None):
        """Record business metric"""
        with self._lock:
            labels = labels or {}
            
            if metric_name == 'trading_pnl' and PROMETHEUS_AVAILABLE:
                self.trading_pnl.labels(**labels).set(value)
            elif metric_name == 'trade_volume' and PROMETHEUS_AVAILABLE:
                self.trade_volume.labels(**labels).inc(value)
            
            self.custom_metrics['business'].append({
                'timestamp': datetime.now(),
                'metric_name': metric_name,
                'value': value,
                'labels': labels
            })
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filter recent metrics
            recent_predictions = [
                m for m in self.custom_metrics['predictions']
                if m['timestamp'] > cutoff_time
            ]
            
            recent_errors = [
                m for m in self.custom_metrics['errors']
                if m['timestamp'] > cutoff_time
            ]
            
            recent_accuracy = [
                m for m in self.custom_metrics['accuracy']
                if m['timestamp'] > cutoff_time
            ]
            
            # Calculate summary statistics
            total_predictions = len(recent_predictions)
            total_errors = len(recent_errors)
            error_rate = total_errors / total_predictions if total_predictions > 0 else 0
            
            avg_confidence = 0
            avg_latency = 0
            if recent_predictions:
                avg_confidence = sum(m['confidence'] for m in recent_predictions) / len(recent_predictions)
                avg_latency = sum(m['latency_seconds'] for m in recent_predictions) / len(recent_predictions)
            
            avg_accuracy = 0
            if recent_accuracy:
                avg_accuracy = sum(m['accuracy'] for m in recent_accuracy) / len(recent_accuracy)
            
            return {
                'time_period_hours': hours,
                'total_predictions': total_predictions,
                'total_errors': total_errors,
                'error_rate': error_rate,
                'average_confidence': avg_confidence,
                'average_latency_seconds': avg_latency,
                'average_accuracy': avg_accuracy,
                'fallback_usage': len([m for m in self.custom_metrics['fallbacks'] if m['timestamp'] > cutoff_time]),
                'circuit_breaker_changes': len([m for m in self.custom_metrics['circuit_breakers'] if m['timestamp'] > cutoff_time])
            }
    
    def add_alert(self, alert: Alert):
        """Add alert definition"""
        self.alerts[alert.name] = alert
        logger.info(f"Added alert: {alert.name}")
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alerts and return triggered ones"""
        triggered_alerts = []
        
        with self._lock:
            for alert_name, alert in self.alerts.items():
                if not alert.enabled:
                    continue
                
                try:
                    # Simple threshold checking (can be extended)
                    if alert.condition == 'error_rate_high':
                        summary = self.get_metrics_summary(hours=1)
                        if summary['error_rate'] > alert.threshold:
                            triggered_alerts.append(self._trigger_alert(alert))
                    
                    elif alert.condition == 'latency_high':
                        summary = self.get_metrics_summary(hours=1)
                        if summary['average_latency_seconds'] > alert.threshold:
                            triggered_alerts.append(self._trigger_alert(alert))
                    
                    elif alert.condition == 'confidence_low':
                        summary = self.get_metrics_summary(hours=1)
                        if summary['average_confidence'] < alert.threshold:
                            triggered_alerts.append(self._trigger_alert(alert))
                
                except Exception as e:
                    logger.error(f"Error checking alert {alert_name}: {e}")
        
        return triggered_alerts
    
    def _trigger_alert(self, alert: Alert) -> Dict[str, Any]:
        """Trigger an alert"""
        alert.trigger_count += 1
        alert.last_triggered = datetime.now()
        
        alert_data = {
            'name': alert.name,
            'condition': alert.condition,
            'threshold': alert.threshold,
            'severity': alert.severity,
            'triggered_at': datetime.now().isoformat(),
            'trigger_count': alert.trigger_count
        }
        
        self.alert_history.append(alert_data)
        logger.warning(f"Alert triggered: {alert.name} - {alert.condition}")
        
        return alert_data

class DistributedTracing:
    """Distributed tracing for ML pipeline"""
    
    def __init__(self, service_name: str = "ml-models", jaeger_endpoint: str = None):
        self.service_name = service_name
        self.tracer = None
        
        if OPENTELEMETRY_AVAILABLE:
            self._setup_tracing(jaeger_endpoint)
        else:
            logger.warning("OpenTelemetry not available, using mock tracing")
            self.tracer = trace.get_tracer(service_name)
    
    def _setup_tracing(self, jaeger_endpoint: str = None):
        """Setup OpenTelemetry tracing"""
        try:
            # Create tracer provider
            resource = Resource.create({"service.name": self.service_name})
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            # Setup Jaeger exporter
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    agent_host_name=jaeger_endpoint.split(':')[0],
                    agent_port=int(jaeger_endpoint.split(':')[1]) if ':' in jaeger_endpoint else 6831,
                )
                
                span_processor = BatchSpanProcessor(jaeger_exporter)
                trace.get_tracer_provider().add_span_processor(span_processor)
            
            self.tracer = trace.get_tracer(self.service_name)
            logger.info(f"Distributed tracing initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Error setting up tracing: {e}")
            self.tracer = trace.get_tracer(self.service_name)
    
    def trace_prediction(self, func, *args, **kwargs):
        """Trace ML prediction with full context"""
        if not self.tracer:
            return func(*args, **kwargs)
        
        with self.tracer.start_span(f"ml_prediction_{func.__name__}") as span:
            # Add context attributes
            span.set_attribute("model.version", kwargs.get('model_version', 'unknown'))
            span.set_attribute("symbol", kwargs.get('symbol', 'unknown'))
            span.set_attribute("request_id", kwargs.get('request_id', 'unknown'))
            
            try:
                result = func(*args, **kwargs)
                
                # Add result attributes
                if hasattr(result, 'confidence'):
                    span.set_attribute("prediction.confidence", result.confidence)
                if hasattr(result, 'prediction'):
                    span.set_attribute("prediction.action", result.prediction)
                
                return result
                
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    
    def trace_model_loading(self, func, *args, **kwargs):
        """Trace model loading operations"""
        if not self.tracer:
            return func(*args, **kwargs)
        
        with self.tracer.start_span(f"model_loading_{func.__name__}") as span:
            span.set_attribute("model_id", kwargs.get('model_id', 'unknown'))
            span.set_attribute("operation", func.__name__)
            
            try:
                result = func(*args, **kwargs)
                span.set_attribute("success", True)
                return result
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

class BusinessMetricsTracker:
    """Track business-relevant ML metrics"""
    
    def __init__(self):
        self.metrics_buffer = deque(maxlen=10000)
        self.alert_thresholds = {
            'accuracy_degradation': 0.05,
            'latency_increase': 2.0,
            'feature_drift': 0.3,
            'prediction_confidence_drop': 0.15,
            'error_rate_spike': 0.1
        }
        
        self.performance_history = deque(maxlen=1000)
        self.baseline_metrics = {}
        
        logger.info("BusinessMetricsTracker initialized")
    
    def track_prediction_outcome(self, 
                               prediction: Dict[str, Any], 
                               actual_outcome: float,
                               timestamp: datetime = None):
        """Track prediction vs actual outcome"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calculate prediction error
        predicted_value = prediction.get('regression_value', 0.0)
        prediction_error = abs(predicted_value - actual_outcome)
        
        # Calculate accuracy for classification
        predicted_action = prediction.get('prediction', 'hold')
        actual_action = self._convert_outcome_to_action(actual_outcome)
        is_correct = predicted_action == actual_action
        
        # Store metrics
        metric_data = {
            'timestamp': timestamp,
            'prediction_error': prediction_error,
            'is_correct': is_correct,
            'confidence': prediction.get('confidence', 0.0),
            'predicted_action': predicted_action,
            'actual_action': actual_action,
            'symbol': prediction.get('symbol', 'unknown'),
            'model_version': prediction.get('model_version', 'unknown')
        }
        
        self.metrics_buffer.append(metric_data)
        
        # Update performance history
        self.performance_history.append({
            'timestamp': timestamp,
            'accuracy': 1.0 if is_correct else 0.0,
            'error': prediction_error,
            'confidence': prediction.get('confidence', 0.0)
        })
    
    def _convert_outcome_to_action(self, outcome: float) -> str:
        """Convert numeric outcome to action"""
        if outcome > 0.01:
            return 'buy'
        elif outcome < -0.01:
            return 'sell'
        else:
            return 'hold'
    
    def detect_model_degradation(self) -> List[Dict[str, Any]]:
        """Detect various forms of model degradation"""
        alerts = []
        
        if len(self.performance_history) < 10:
            return alerts
        
        # Get recent performance
        recent_performance = list(self.performance_history)[-50:]  # Last 50 predictions
        baseline_performance = list(self.performance_history)[-200:-50] if len(self.performance_history) > 200 else []
        
        if not baseline_performance:
            return alerts
        
        # Calculate metrics
        recent_accuracy = sum(p['accuracy'] for p in recent_performance) / len(recent_performance)
        baseline_accuracy = sum(p['accuracy'] for p in baseline_performance) / len(baseline_performance)
        
        recent_confidence = sum(p['confidence'] for p in recent_performance) / len(recent_performance)
        baseline_confidence = sum(p['confidence'] for p in baseline_performance) / len(baseline_performance)
        
        recent_error = sum(p['error'] for p in recent_performance) / len(recent_performance)
        baseline_error = sum(p['error'] for p in baseline_performance) / len(baseline_performance)
        
        # Check for accuracy degradation
        accuracy_degradation = baseline_accuracy - recent_accuracy
        if accuracy_degradation > self.alert_thresholds['accuracy_degradation']:
            alerts.append({
                'type': 'accuracy_degradation',
                'severity': 'warning',
                'message': f'Accuracy degraded by {accuracy_degradation:.3f}',
                'baseline': baseline_accuracy,
                'current': recent_accuracy,
                'degradation': accuracy_degradation
            })
        
        # Check for confidence drop
        confidence_drop = baseline_confidence - recent_confidence
        if confidence_drop > self.alert_thresholds['prediction_confidence_drop']:
            alerts.append({
                'type': 'confidence_drop',
                'severity': 'warning',
                'message': f'Confidence dropped by {confidence_drop:.3f}',
                'baseline': baseline_confidence,
                'current': recent_confidence,
                'drop': confidence_drop
            })
        
        # Check for error increase
        error_increase = recent_error - baseline_error
        if error_increase > self.alert_thresholds['error_rate_spike']:
            alerts.append({
                'type': 'error_rate_spike',
                'severity': 'critical',
                'message': f'Error rate increased by {error_increase:.3f}',
                'baseline': baseline_error,
                'current': recent_error,
                'increase': error_increase
            })
        
        return alerts
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_buffer
            if m['timestamp'] > cutoff_time
        ]
        
        if not recent_metrics:
            return {'total_predictions': 0}
        
        total_predictions = len(recent_metrics)
        correct_predictions = sum(1 for m in recent_metrics if m['is_correct'])
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
        
        avg_error = sum(m['prediction_error'] for m in recent_metrics) / total_predictions
        avg_confidence = sum(m['confidence'] for m in recent_metrics) / total_predictions
        
        # Action distribution
        action_counts = {}
        for m in recent_metrics:
            action = m['predicted_action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_predictions': total_predictions,
            'accuracy': accuracy,
            'average_error': avg_error,
            'average_confidence': avg_confidence,
            'action_distribution': action_counts,
            'time_period_hours': hours
        }

class ObservabilityManager:
    """Central observability manager"""
    
    def __init__(self, 
                 prometheus_port: int = 8000,
                 jaeger_endpoint: str = None,
                 service_name: str = "ml-models"):
        self.metrics_collector = MLMetricsCollector()
        self.tracing = DistributedTracing(service_name, jaeger_endpoint)
        self.business_tracker = BusinessMetricsTracker()
        
        # Start Prometheus server
        if PROMETHEUS_AVAILABLE:
            try:
                start_http_server(prometheus_port, registry=self.metrics_collector.registry)
                logger.info(f"Prometheus metrics server started on port {prometheus_port}")
            except Exception as e:
                logger.error(f"Failed to start Prometheus server: {e}")
        
        # Setup default alerts
        self._setup_default_alerts()
        
        logger.info("ObservabilityManager initialized")
    
    def _setup_default_alerts(self):
        """Setup default alerting rules"""
        default_alerts = [
            Alert(
                name="high_error_rate",
                condition="error_rate_high",
                threshold=0.1,
                severity="warning"
            ),
            Alert(
                name="high_latency",
                condition="latency_high",
                threshold=1.0,
                severity="warning"
            ),
            Alert(
                name="low_confidence",
                condition="confidence_low",
                threshold=0.3,
                severity="warning"
            )
        ]
        
        for alert in default_alerts:
            self.metrics_collector.add_alert(alert)
    
    def get_comprehensive_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            'ml_metrics': self.metrics_collector.get_metrics_summary(hours),
            'business_metrics': self.business_tracker.get_performance_summary(hours),
            'alerts': self.metrics_collector.check_alerts(),
            'degradation_alerts': self.business_tracker.detect_model_degradation()
        }
    
    def export_metrics(self, file_path: str):
        """Export metrics to file"""
        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'ml_metrics': self.metrics_collector.get_metrics_summary(24),
                'business_metrics': self.business_tracker.get_performance_summary(24),
                'custom_metrics': dict(self.metrics_collector.custom_metrics)
            }
            
            with open(file_path, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

# Global observability manager
observability_manager = ObservabilityManager()

# Convenience functions
def record_prediction(model_version: str, symbol: str, outcome: str, 
                     confidence: float, latency_seconds: float, fallback_used: bool = False):
    """Record prediction metrics"""
    observability_manager.metrics_collector.record_prediction(
        model_version, symbol, outcome, confidence, latency_seconds, fallback_used
    )

def record_prediction_error(model_version: str, symbol: str, error_type: str):
    """Record prediction error"""
    observability_manager.metrics_collector.record_prediction_error(
        model_version, symbol, error_type
    )

def track_prediction_outcome(prediction: Dict[str, Any], actual_outcome: float):
    """Track prediction outcome"""
    observability_manager.business_tracker.track_prediction_outcome(prediction, actual_outcome)

def get_metrics_summary(hours: int = 24) -> Dict[str, Any]:
    """Get metrics summary"""
    return observability_manager.get_comprehensive_metrics(hours)

def trace_prediction(func):
    """Decorator for tracing predictions"""
    return observability_manager.tracing.trace_prediction(func)
