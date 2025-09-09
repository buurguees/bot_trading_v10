"""
📊 model_evaluator.py - Evaluador de Performance de Modelos

Sistema de evaluación que monitorea y evalúa el performance de los modelos ML,
calculando métricas financieras y de ML para optimización continua.

Autor: Alex B
Fecha: 2025-01-07
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
import json
import os
from pathlib import Path
from collections import defaultdict

# Imports del proyecto
from core.data.database import db_manager
from core.config.config_loader import user_config

logger = logging.getLogger(__name__)

class ModelEvaluator:
    """
    Evaluador de performance de modelos ML para trading.
    
    Responsabilidades:
    - Calcular métricas financieras (Sharpe, Sortino, Calmar, etc.)
    - Calcular métricas de ML (Accuracy, Precision, Recall, F1, etc.)
    - Monitorear performance en tiempo real
    - Detectar degradación del modelo
    - Generar reportes de evaluación
    - Comparar diferentes versiones de modelos
    """
    
    def __init__(self):
        self.config = user_config
        self.evaluation_history = []
        self.current_metrics = {}
        self.performance_alerts = []
        
        # Configuración de evaluación
        self.evaluation_config = self.config.get_value(['ai_model_settings', 'evaluation'], {})
        self.evaluation_frequency = self.evaluation_config.get('frequency', 24)  # Cada 24 horas
        self.performance_thresholds = self.evaluation_config.get('thresholds', {
            'min_accuracy': 0.6,
            'min_sharpe_ratio': 1.0,
            'max_drawdown': 0.15,
            'min_win_rate': 0.5
        })
        
        logger.info("ModelEvaluator inicializado")
    
    async def evaluate_model_performance(self, symbol: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Evalúa el performance del modelo para un símbolo específico
        
        Args:
            symbol: Símbolo a evaluar
            days_back: Días hacia atrás para evaluación
            
        Returns:
            Dict con métricas de evaluación
        """
        try:
            logger.info(f"Evaluando performance del modelo para {symbol} ({days_back} días)")
            
            # Obtener datos de trades
            trades_data = await self._get_trades_data(symbol, days_back)
            
            if len(trades_data) == 0:
                return {
                    'symbol': symbol,
                    'status': 'no_data',
                    'message': 'No hay datos de trades para evaluar',
                    'evaluation_time': datetime.now().isoformat()
                }
            
            # Calcular métricas financieras
            financial_metrics = self._calculate_financial_metrics(trades_data)
            
            # Calcular métricas de ML
            ml_metrics = self._calculate_ml_metrics(trades_data)
            
            # Calcular métricas de riesgo
            risk_metrics = self._calculate_risk_metrics(trades_data)
            
            # Calcular métricas de consistencia
            consistency_metrics = self._calculate_consistency_metrics(trades_data)
            
            # Combinar todas las métricas
            evaluation_result = {
                'symbol': symbol,
                'evaluation_period_days': days_back,
                'total_trades': len(trades_data),
                'evaluation_time': datetime.now().isoformat(),
                'financial_metrics': financial_metrics,
                'ml_metrics': ml_metrics,
                'risk_metrics': risk_metrics,
                'consistency_metrics': consistency_metrics,
                'overall_score': self._calculate_overall_score(financial_metrics, ml_metrics, risk_metrics),
                'status': 'completed'
            }
            
            # Guardar evaluación
            self.evaluation_history.append(evaluation_result)
            self.current_metrics[symbol] = evaluation_result
            
            # Verificar alertas de performance
            await self._check_performance_alerts(symbol, evaluation_result)
            
            logger.info(f"Evaluación completada para {symbol}. Score: {evaluation_result['overall_score']:.3f}")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"❌ Error evaluando performance: {e}")
            return {
                'symbol': symbol,
                'status': 'failed',
                'error': str(e),
                'evaluation_time': datetime.now().isoformat()
            }
    
    async def _get_trades_data(self, symbol: str, days_back: int) -> List[Dict]:
        """Obtiene datos de trades desde la base de datos"""
        try:
            # Obtener trades de la base de datos
            trades = db_manager.get_trades_by_symbol(symbol, days_back)
            
            # Convertir a formato estándar
            trades_data = []
            for trade in trades:
                trade_data = {
                    'trade_id': trade.get('trade_id'),
                    'symbol': trade.get('symbol'),
                    'side': trade.get('side'),
                    'entry_price': trade.get('entry_price'),
                    'exit_price': trade.get('exit_price'),
                    'quantity': trade.get('quantity'),
                    'entry_time': trade.get('entry_time'),
                    'exit_time': trade.get('exit_time'),
                    'pnl': trade.get('pnl', 0),
                    'pnl_pct': trade.get('pnl_pct', 0),
                    'confidence': trade.get('confidence', 0),
                    'model_prediction': trade.get('model_prediction'),
                    'actual_result': trade.get('actual_result'),
                    'fees': trade.get('fees', 0),
                    'status': trade.get('status'),
                    'exit_reason': trade.get('exit_reason')
                }
                trades_data.append(trade_data)
            
            return trades_data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de trades: {e}")
            return []
    
    def _calculate_financial_metrics(self, trades_data: List[Dict]) -> Dict[str, float]:
        """Calcula métricas financieras"""
        try:
            if len(trades_data) == 0:
                return {}
            
            # Extraer datos financieros
            pnl_values = [trade['pnl'] for trade in trades_data if trade['pnl'] is not None]
            pnl_pct_values = [trade['pnl_pct'] for trade in trades_data if trade['pnl_pct'] is not None]
            
            if len(pnl_values) == 0:
                return {}
            
            # Métricas básicas
            total_pnl = sum(pnl_values)
            total_trades = len(trades_data)
            profitable_trades = sum(1 for pnl in pnl_values if pnl > 0)
            losing_trades = sum(1 for pnl in pnl_values if pnl < 0)
            
            # Win rate
            win_rate = profitable_trades / total_trades if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum(pnl for pnl in pnl_values if pnl > 0)
            gross_loss = abs(sum(pnl for pnl in pnl_values if pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Retornos
            returns = np.array(pnl_pct_values) / 100  # Convertir a decimal
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Sharpe ratio
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
            
            # Sortino ratio (solo desviación negativa)
            negative_returns = returns[returns < 0]
            downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 0
            sortino_ratio = avg_return / downside_std if downside_std > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = np.min(drawdowns)
            
            # Calmar ratio
            calmar_ratio = avg_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Average win/loss
            avg_win = np.mean([pnl for pnl in pnl_values if pnl > 0]) if profitable_trades > 0 else 0
            avg_loss = np.mean([pnl for pnl in pnl_values if pnl < 0]) if losing_trades > 0 else 0
            
            # Win/Loss ratio
            win_loss_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else 0
            
            return {
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_return': avg_return,
                'std_return': std_return,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar_ratio,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'win_loss_ratio': win_loss_ratio
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas financieras: {e}")
            return {}
    
    def _calculate_ml_metrics(self, trades_data: List[Dict]) -> Dict[str, float]:
        """Calcula métricas de machine learning"""
        try:
            if len(trades_data) == 0:
                return {}
            
            # Extraer predicciones y resultados reales
            predictions = []
            actuals = []
            confidences = []
            
            for trade in trades_data:
                if trade.get('model_prediction') is not None and trade.get('actual_result') is not None:
                    predictions.append(trade['model_prediction'])
                    actuals.append(trade['actual_result'])
                    confidences.append(trade.get('confidence', 0))
            
            if len(predictions) == 0:
                return {}
            
            predictions = np.array(predictions)
            actuals = np.array(actuals)
            confidences = np.array(confidences)
            
            # Accuracy
            accuracy = np.mean(predictions == actuals)
            
            # Precision, Recall, F1 para cada clase
            classes = [0, 1, 2]  # SELL, HOLD, BUY
            class_names = ['SELL', 'HOLD', 'BUY']
            
            precision_scores = []
            recall_scores = []
            f1_scores = []
            
            for i, class_name in enumerate(class_names):
                # Precision
                true_positives = np.sum((predictions == i) & (actuals == i))
                false_positives = np.sum((predictions == i) & (actuals != i))
                precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
                precision_scores.append(precision)
                
                # Recall
                false_negatives = np.sum((predictions != i) & (actuals == i))
                recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
                recall_scores.append(recall)
                
                # F1 Score
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                f1_scores.append(f1)
            
            # Macro averages
            macro_precision = np.mean(precision_scores)
            macro_recall = np.mean(recall_scores)
            macro_f1 = np.mean(f1_scores)
            
            # Confidence calibration
            confidence_accuracy = self._calculate_confidence_calibration(predictions, actuals, confidences)
            
            # Prediction distribution
            prediction_dist = {
                'SELL': np.sum(predictions == 0),
                'HOLD': np.sum(predictions == 1),
                'BUY': np.sum(predictions == 2)
            }
            
            return {
                'accuracy': accuracy,
                'macro_precision': macro_precision,
                'macro_recall': macro_recall,
                'macro_f1': macro_f1,
                'precision_by_class': dict(zip(class_names, precision_scores)),
                'recall_by_class': dict(zip(class_names, recall_scores)),
                'f1_by_class': dict(zip(class_names, f1_scores)),
                'confidence_calibration': confidence_accuracy,
                'prediction_distribution': prediction_dist,
                'total_predictions': len(predictions)
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas ML: {e}")
            return {}
    
    def _calculate_risk_metrics(self, trades_data: List[Dict]) -> Dict[str, float]:
        """Calcula métricas de riesgo"""
        try:
            if len(trades_data) == 0:
                return {}
            
            # Extraer datos de riesgo
            pnl_values = [trade['pnl'] for trade in trades_data if trade['pnl'] is not None]
            pnl_pct_values = [trade['pnl_pct'] for trade in trades_data if trade['pnl_pct'] is not None]
            
            if len(pnl_values) == 0:
                return {}
            
            returns = np.array(pnl_pct_values) / 100
            
            # VaR (Value at Risk) - 95% confidence
            var_95 = np.percentile(returns, 5)
            
            # Expected Shortfall (Conditional VaR)
            es_95 = np.mean(returns[returns <= var_95])
            
            # Maximum consecutive losses
            consecutive_losses = self._calculate_consecutive_losses(pnl_values)
            
            # Volatility
            volatility = np.std(returns)
            
            # Skewness y Kurtosis
            skewness = self._calculate_skewness(returns)
            kurtosis = self._calculate_kurtosis(returns)
            
            return {
                'var_95': var_95,
                'expected_shortfall_95': es_95,
                'max_consecutive_losses': consecutive_losses,
                'volatility': volatility,
                'skewness': skewness,
                'kurtosis': kurtosis
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
            return {}
    
    def _calculate_consistency_metrics(self, trades_data: List[Dict]) -> Dict[str, float]:
        """Calcula métricas de consistencia"""
        try:
            if len(trades_data) == 0:
                return {}
            
            # Agrupar por día
            daily_pnl = defaultdict(float)
            for trade in trades_data:
                if trade['exit_time']:
                    date = trade['exit_time'].date()
                    daily_pnl[date] += trade['pnl']
            
            daily_returns = list(daily_pnl.values())
            
            if len(daily_returns) == 0:
                return {}
            
            # Consistencia de retornos diarios
            daily_returns = np.array(daily_returns)
            positive_days = np.sum(daily_returns > 0)
            negative_days = np.sum(daily_returns < 0)
            neutral_days = np.sum(daily_returns == 0)
            
            # Estabilidad de retornos
            return_stability = 1 - (np.std(daily_returns) / (np.mean(np.abs(daily_returns)) + 1e-8))
            
            # Tendencia de performance
            if len(daily_returns) > 1:
                performance_trend = np.polyfit(range(len(daily_returns)), daily_returns, 1)[0]
            else:
                performance_trend = 0
            
            return {
                'total_days': len(daily_returns),
                'positive_days': positive_days,
                'negative_days': negative_days,
                'neutral_days': neutral_days,
                'daily_win_rate': positive_days / len(daily_returns) if len(daily_returns) > 0 else 0,
                'return_stability': return_stability,
                'performance_trend': performance_trend
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de consistencia: {e}")
            return {}
    
    def _calculate_confidence_calibration(self, predictions: np.ndarray, actuals: np.ndarray, confidences: np.ndarray) -> float:
        """Calcula calibración de confianza"""
        try:
            if len(confidences) == 0:
                return 0.0
            
            # Agrupar por rangos de confianza
            confidence_bins = np.linspace(0, 1, 11)  # 10 bins
            bin_accuracies = []
            
            for i in range(len(confidence_bins) - 1):
                bin_mask = (confidences >= confidence_bins[i]) & (confidences < confidence_bins[i + 1])
                if np.sum(bin_mask) > 0:
                    bin_accuracy = np.mean(predictions[bin_mask] == actuals[bin_mask])
                    bin_accuracies.append(bin_accuracy)
                else:
                    bin_accuracies.append(0.0)
            
            # Calcular ECE (Expected Calibration Error)
            ece = np.mean(np.abs(np.array(bin_accuracies) - confidence_bins[:-1]))
            
            return 1 - ece  # Mayor es mejor
            
        except Exception as e:
            logger.error(f"Error calculando calibración de confianza: {e}")
            return 0.0
    
    def _calculate_consecutive_losses(self, pnl_values: List[float]) -> int:
        """Calcula máximo número de pérdidas consecutivas"""
        try:
            max_consecutive = 0
            current_consecutive = 0
            
            for pnl in pnl_values:
                if pnl < 0:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            return max_consecutive
            
        except Exception as e:
            logger.error(f"Error calculando pérdidas consecutivas: {e}")
            return 0
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calcula skewness de los retornos"""
        try:
            if len(returns) < 3:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            skewness = np.mean(((returns - mean_return) / std_return) ** 3)
            return skewness
            
        except Exception as e:
            logger.error(f"Error calculando skewness: {e}")
            return 0.0
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calcula kurtosis de los retornos"""
        try:
            if len(returns) < 4:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
            return kurtosis
            
        except Exception as e:
            logger.error(f"Error calculando kurtosis: {e}")
            return 0.0
    
    def _calculate_overall_score(self, financial_metrics: Dict, ml_metrics: Dict, risk_metrics: Dict) -> float:
        """Calcula score general del modelo"""
        try:
            score = 0.0
            weight = 0.0
            
            # Score financiero (40% peso)
            if 'sharpe_ratio' in financial_metrics:
                sharpe_score = min(financial_metrics['sharpe_ratio'] / 2.0, 1.0)  # Normalizar a [0,1]
                score += sharpe_score * 0.4
                weight += 0.4
            
            # Score de ML (30% peso)
            if 'accuracy' in ml_metrics:
                accuracy_score = ml_metrics['accuracy']
                score += accuracy_score * 0.3
                weight += 0.3
            
            # Score de riesgo (30% peso)
            if 'max_drawdown' in risk_metrics:
                drawdown_score = max(0, 1 + risk_metrics['max_drawdown'])  # Drawdown negativo = mejor
                score += drawdown_score * 0.3
                weight += 0.3
            
            # Normalizar por peso total
            if weight > 0:
                return score / weight
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculando score general: {e}")
            return 0.0
    
    async def _check_performance_alerts(self, symbol: str, evaluation_result: Dict):
        """Verifica alertas de performance"""
        try:
            alerts = []
            
            # Verificar umbrales
            thresholds = self.performance_thresholds
            
            if 'accuracy' in evaluation_result.get('ml_metrics', {}):
                accuracy = evaluation_result['ml_metrics']['accuracy']
                if accuracy < thresholds.get('min_accuracy', 0.6):
                    alerts.append(f"Accuracy baja: {accuracy:.3f} < {thresholds['min_accuracy']}")
            
            if 'sharpe_ratio' in evaluation_result.get('financial_metrics', {}):
                sharpe = evaluation_result['financial_metrics']['sharpe_ratio']
                if sharpe < thresholds.get('min_sharpe_ratio', 1.0):
                    alerts.append(f"Sharpe ratio bajo: {sharpe:.3f} < {thresholds['min_sharpe_ratio']}")
            
            if 'max_drawdown' in evaluation_result.get('risk_metrics', {}):
                drawdown = evaluation_result['risk_metrics']['max_drawdown']
                if abs(drawdown) > thresholds.get('max_drawdown', 0.15):
                    alerts.append(f"Drawdown alto: {drawdown:.3f} > {thresholds['max_drawdown']}")
            
            if 'win_rate' in evaluation_result.get('financial_metrics', {}):
                win_rate = evaluation_result['financial_metrics']['win_rate']
                if win_rate < thresholds.get('min_win_rate', 0.5):
                    alerts.append(f"Win rate bajo: {win_rate:.3f} < {thresholds['min_win_rate']}")
            
            # Guardar alertas
            if alerts:
                alert_data = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'alerts': alerts,
                    'evaluation_result': evaluation_result
                }
                self.performance_alerts.append(alert_data)
                logger.warning(f"⚠️ Alertas de performance para {symbol}: {alerts}")
            
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
    
    async def get_evaluation_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de evaluaciones"""
        try:
            return {
                'total_evaluations': len(self.evaluation_history),
                'current_metrics': self.current_metrics,
                'performance_alerts': len(self.performance_alerts),
                'recent_alerts': self.performance_alerts[-5:] if self.performance_alerts else [],
                'last_evaluation': self.evaluation_history[-1] if self.evaluation_history else None
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica salud del evaluador"""
        try:
            return {
                'status': 'healthy',
                'evaluations_count': len(self.evaluation_history),
                'alerts_count': len(self.performance_alerts),
                'thresholds_configured': bool(self.performance_thresholds)
            }
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Instancia global del evaluador
model_evaluator = ModelEvaluator()

# Funciones de conveniencia
async def evaluate_model_performance(symbol: str, days_back: int = 30) -> Dict[str, Any]:
    """Función de conveniencia para evaluar performance"""
    return await model_evaluator.evaluate_model_performance(symbol, days_back)

async def get_evaluation_summary() -> Dict[str, Any]:
    """Función de conveniencia para obtener resumen"""
    return await model_evaluator.get_evaluation_summary()

async def health_check() -> Dict[str, Any]:
    """Función de conveniencia para health check"""
    return await model_evaluator.health_check()
