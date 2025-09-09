# start_8h_training.py - Script de entrenamiento de 8 horas
# Ubicación: C:\TradingBot_v10\training_scripts\enterprise\start_8h_training.py

"""
Script principal para ejecutar entrenamiento enterprise de 8 horas.

Características:
- Entrenamiento distribuido de 8 horas
- Recolección de datos en tiempo real simultánea
- MLflow tracking automático
- Hyperparameter tuning opcional
- Monitoreo con Prometheus
- Recovery automático ante fallos
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import yaml
import signal
import os

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.enterprise.training_engine import EnterpriseTrainingEngine
from models.enterprise.hyperparameter_tuner import HyperparameterTuner
from config.enterprise_config import EnterpriseConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise/training/8h_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EightHourTrainingManager:
    """Gestor de entrenamiento de 8 horas"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el gestor de entrenamiento
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = config_path or "config/enterprise/training.yaml"
        self.config_manager = EnterpriseConfigManager(self.config_path)
        self.config = self.config_manager.load_config()
        
        # Componentes
        self.training_engine = None
        self.hyperparameter_tuner = None
        
        # Estado
        self.is_running = False
        self.start_time = None
        self.end_time = None
        
        # Configurar signal handlers
        self.setup_signal_handlers()
        
        logger.info("EightHourTrainingManager inicializado")
    
    def setup_signal_handlers(self):
        """Configura handlers para graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Iniciando parada segura...")
            self.stop_training()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_training(
        self,
        symbols: Optional[List[str]] = None,
        model_architecture: str = "lstm_attention",
        enable_hyperparameter_tuning: bool = False,
        enable_data_collection: bool = True,
        duration_hours: int = 8
    ) -> Dict[str, Any]:
        """
        Inicia el entrenamiento de 8 horas
        
        Args:
            symbols: Lista de símbolos para entrenar
            model_architecture: Arquitectura del modelo
            enable_hyperparameter_tuning: Si habilitar tuning de hiperparámetros
            enable_data_collection: Si habilitar recolección de datos simultánea
            duration_hours: Duración del entrenamiento en horas
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            logger.info(f"🚀 Iniciando entrenamiento enterprise de {duration_hours} horas")
            
            # Configurar tiempo
            self.start_time = datetime.now()
            self.end_time = self.start_time + timedelta(hours=duration_hours)
            self.is_running = True
            
            # Configurar símbolos
            if symbols is None:
                symbols = self.config.training.data.symbols
            
            logger.info(f"Símbolos a entrenar: {symbols}")
            logger.info(f"Arquitectura del modelo: {model_architecture}")
            logger.info(f"Hyperparameter tuning: {enable_hyperparameter_tuning}")
            logger.info(f"Data collection: {enable_data_collection}")
            
            # Crear motor de entrenamiento
            self.training_engine = EnterpriseTrainingEngine(self.config_path)
            
            # Crear hyperparameter tuner si está habilitado
            if enable_hyperparameter_tuning:
                self.hyperparameter_tuner = HyperparameterTuner(
                    self.config.hyperparameters
                )
            
            # Ejecutar entrenamiento
            results = await self.training_engine.train_enterprise(
                duration_hours=duration_hours,
                symbols=symbols,
                model_architecture=model_architecture,
                enable_data_collection=enable_data_collection,
                enable_hyperparameter_tuning=enable_hyperparameter_tuning
            )
            
            # Procesar resultados
            processed_results = self._process_results(results)
            
            # Generar reporte final
            self._generate_final_report(processed_results)
            
            logger.info("✅ Entrenamiento de 8 horas completado exitosamente")
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento de 8 horas: {e}")
            raise
        finally:
            self.is_running = False
            self._cleanup()
    
    def _process_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa y enriquece los resultados del entrenamiento"""
        processed = {
            'training_summary': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat(),
                'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0,
                'total_symbols': len(results),
                'successful_training': len([r for r in results.values() if isinstance(r, dict) and 'error' not in r]),
                'failed_training': len([r for r in results.values() if isinstance(r, dict) and 'error' in r])
            },
            'model_results': results,
            'performance_metrics': self._calculate_performance_metrics(results),
            'recommendations': self._generate_recommendations(results)
        }
        
        return processed
    
    def _calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas de rendimiento agregadas"""
        metrics = {
            'total_training_time_seconds': 0,
            'average_accuracy': 0,
            'best_accuracy': 0,
            'worst_accuracy': 1,
            'average_training_time_per_symbol': 0,
            'model_sizes_mb': []
        }
        
        successful_results = [r for r in results.values() if isinstance(r, dict) and 'error' not in r]
        
        if not successful_results:
            return metrics
        
        # Calcular métricas agregadas
        total_time = sum(r.get('training_time_seconds', 0) for r in successful_results)
        accuracies = [r.get('test_results', {}).get('test_accuracy', 0) for r in successful_results]
        
        metrics['total_training_time_seconds'] = total_time
        metrics['average_accuracy'] = sum(accuracies) / len(accuracies) if accuracies else 0
        metrics['best_accuracy'] = max(accuracies) if accuracies else 0
        metrics['worst_accuracy'] = min(accuracies) if accuracies else 1
        metrics['average_training_time_per_symbol'] = total_time / len(successful_results)
        
        return metrics
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en los resultados"""
        recommendations = []
        
        successful_results = [r for r in results.values() if isinstance(r, dict) and 'error' not in r]
        
        if not successful_results:
            recommendations.append("❌ No se completó ningún entrenamiento exitoso")
            return recommendations
        
        # Análisis de accuracy
        accuracies = [r.get('test_results', {}).get('test_accuracy', 0) for r in successful_results]
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        if avg_accuracy > 0.8:
            recommendations.append("✅ Excelente rendimiento general del modelo")
        elif avg_accuracy > 0.6:
            recommendations.append("⚠️ Rendimiento moderado, considerar más datos o ajustes")
        else:
            recommendations.append("❌ Rendimiento bajo, revisar arquitectura y datos")
        
        # Análisis de tiempo de entrenamiento
        training_times = [r.get('training_time_seconds', 0) for r in successful_results]
        avg_training_time = sum(training_times) / len(training_times)
        
        if avg_training_time > 3600:  # Más de 1 hora por símbolo
            recommendations.append("⚠️ Tiempo de entrenamiento alto, considerar optimizaciones")
        else:
            recommendations.append("✅ Tiempo de entrenamiento eficiente")
        
        # Análisis de errores
        failed_count = len([r for r in results.values() if isinstance(r, dict) and 'error' in r])
        if failed_count > 0:
            recommendations.append(f"⚠️ {failed_count} entrenamientos fallaron, revisar logs")
        
        return recommendations
    
    def _generate_final_report(self, results: Dict[str, Any]):
        """Genera reporte final del entrenamiento"""
        try:
            # Crear directorio de reportes
            report_dir = Path("reports/training/8h_training")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"8h_training_report_{timestamp}.json"
            
            # Guardar reporte
            import json
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte final guardado en {report_file}")
            
            # Generar resumen en consola
            self._print_summary(results)
            
        except Exception as e:
            logger.error(f"Error generando reporte final: {e}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Imprime resumen del entrenamiento en consola"""
        summary = results.get('training_summary', {})
        metrics = results.get('performance_metrics', {})
        recommendations = results.get('recommendations', [])
        
        print("\n" + "="*60)
        print("           RESUMEN DEL ENTRENAMIENTO DE 8 HORAS")
        print("="*60)
        
        print(f"⏱️  Duración total: {summary.get('duration_hours', 0):.2f} horas")
        print(f"📊 Símbolos entrenados: {summary.get('successful_training', 0)}/{summary.get('total_symbols', 0)}")
        print(f"🎯 Accuracy promedio: {metrics.get('average_accuracy', 0):.4f}")
        print(f"🏆 Mejor accuracy: {metrics.get('best_accuracy', 0):.4f}")
        print(f"⏰ Tiempo promedio por símbolo: {metrics.get('average_training_time_per_symbol', 0)/60:.1f} minutos")
        
        print("\n📋 RECOMENDACIONES:")
        for rec in recommendations:
            print(f"  {rec}")
        
        print("="*60)
    
    def stop_training(self):
        """Detiene el entrenamiento de forma segura"""
        logger.info("🛑 Deteniendo entrenamiento...")
        self.is_running = False
        
        if self.training_engine:
            self.training_engine.stop_training()
    
    def _cleanup(self):
        """Limpia recursos al finalizar"""
        try:
            if self.training_engine:
                self.training_engine.cleanup()
            
            logger.info("✅ Cleanup completado")
            
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Entrenamiento enterprise de 8 horas")
    parser.add_argument("--symbols", nargs="+", help="Símbolos para entrenar")
    parser.add_argument("--architecture", default="lstm_attention", 
                       choices=["lstm_attention", "transformer", "cnn_lstm", "gru_simple"],
                       help="Arquitectura del modelo")
    parser.add_argument("--hyperparameter-tuning", action="store_true",
                       help="Habilitar tuning de hiperparámetros")
    parser.add_argument("--no-data-collection", action="store_true",
                       help="Deshabilitar recolección de datos")
    parser.add_argument("--duration", type=int, default=8,
                       help="Duración del entrenamiento en horas")
    parser.add_argument("--config", help="Ruta al archivo de configuración")
    
    args = parser.parse_args()
    
    # Crear gestor de entrenamiento
    manager = EightHourTrainingManager(args.config)
    
    try:
        # Ejecutar entrenamiento
        results = await manager.start_training(
            symbols=args.symbols,
            model_architecture=args.architecture,
            enable_hyperparameter_tuning=args.hyperparameter_tuning,
            enable_data_collection=not args.no_data_collection,
            duration_hours=args.duration
        )
        
        print(f"\n✅ Entrenamiento completado exitosamente")
        print(f"📊 Resultados: {len(results.get('model_results', {}))} modelos entrenados")
        
    except KeyboardInterrupt:
        print("\n⚠️ Entrenamiento interrumpido por el usuario")
        manager.stop_training()
    except Exception as e:
        print(f"\n❌ Error en entrenamiento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
