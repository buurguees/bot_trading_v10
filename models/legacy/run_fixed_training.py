#!/usr/bin/env python3
"""
Entrenamiento Corregido Autónomo
================================

Script corregido para ejecutar entrenamiento de forma autónoma
con manejo robusto de datos y errores.
"""

import asyncio
import logging
import sys
import os
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import signal
import threading

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fixed_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FixedTrainingManager:
    """Gestor de entrenamiento corregido"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.start_time = None
        
        # Configurar directorios
        self.setup_directories()
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_directories(self):
        """Configura directorios necesarios"""
        directories = ['logs', 'checkpoints', 'data']
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        self.logger.info("Directorios configurados")
    
    def signal_handler(self, signum, frame):
        """Maneja señales para shutdown graceful"""
        self.logger.info(f"Recibida señal {signum}, deteniendo entrenamiento...")
        self.is_running = False
        sys.exit(0)
    
    def generate_training_data(self, n_samples=10000):
        """Genera datos de entrenamiento sintéticos robustos"""
        self.logger.info("Generando datos de entrenamiento...")
        
        # Generar datos de trading sintéticos más robustos
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=n_samples, freq='1H')
        
        # Simular precios con tendencia y volatilidad controlada
        base_price = 50000
        trend = np.linspace(0, 0.1, n_samples)  # Tendencia más suave
        noise = np.random.normal(0, 0.01, n_samples)  # Ruido más pequeño
        price_changes = trend + noise
        
        prices = [base_price]
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            # Limitar cambios extremos
            new_price = max(new_price, prices[-1] * 0.5)  # Máximo -50%
            new_price = min(new_price, prices[-1] * 2.0)  # Máximo +100%
            prices.append(new_price)
        
        # Crear OHLCV con lógica más robusta
        data = []
        for i, price in enumerate(prices):
            # Asegurar que high >= low y que close esté entre high y low
            volatility = abs(np.random.normal(0, 0.005))  # Volatilidad controlada
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            close = price + np.random.normal(0, price * 0.001)  # Cambio pequeño
            close = max(low, min(high, close))  # Asegurar que close esté en rango
            volume = max(100, int(np.random.normal(5000, 1000)))  # Volumen positivo
            
            data.append({
                'timestamp': dates[i],
                'open': price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.to_csv('data/training_data_fixed.csv', index=False)
        
        self.logger.info(f"Datos generados: {len(df)} registros")
        return df
    
    def create_features_robust(self, df):
        """Crea características técnicas de forma robusta"""
        self.logger.info("Creando características técnicas...")
        
        # Copiar dataframe
        df = df.copy()
        
        # Media móvil simple con manejo de NaN
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
        
        # RSI con manejo de división por cero
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        
        # Evitar división por cero
        rs = gain / (loss + 1e-10)  # Agregar pequeño valor para evitar división por cero
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD con manejo de NaN
        ema_12 = df['close'].ewm(span=12, min_periods=1).mean()
        ema_26 = df['close'].ewm(span=26, min_periods=1).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, min_periods=1).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands con manejo de NaN
        df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        bb_std = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad con manejo de NaN
        df['volatility'] = df['close'].rolling(window=20, min_periods=1).std()
        
        # Retornos con manejo de división por cero
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1) + 1e-10)
        
        # Reemplazar infinitos y NaN con valores seguros
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Verificar que no hay valores infinitos o NaN
        if df.isnull().any().any():
            self.logger.warning("Aún hay valores NaN después de limpieza")
            df = df.fillna(0)
        
        if np.isinf(df.select_dtypes(include=[np.number]).values).any():
            self.logger.warning("Aún hay valores infinitos después de limpieza")
            df = df.replace([np.inf, -np.inf], 0)
        
        self.logger.info(f"Características creadas: {len(df.columns)} columnas")
        self.logger.info(f"Shape final: {df.shape}")
        self.logger.info(f"Valores NaN: {df.isnull().sum().sum()}")
        self.logger.info(f"Valores infinitos: {np.isinf(df.select_dtypes(include=[np.number]).values).sum()}")
        
        return df
    
    def create_sequences_robust(self, df, sequence_length=60, prediction_horizon=1):
        """Crea secuencias para entrenamiento de forma robusta"""
        self.logger.info("Creando secuencias de entrenamiento...")
        
        # Seleccionar características numéricas
        feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_20', 'sma_50', 'rsi', 'macd', 'volatility']
        
        # Verificar que las columnas existen
        available_columns = [col for col in feature_columns if col in df.columns]
        if len(available_columns) < 5:
            self.logger.error(f"No hay suficientes columnas disponibles: {available_columns}")
            return None, None, None
        
        features = df[available_columns].values
        
        # Verificar valores antes de normalizar
        self.logger.info(f"Valores antes de normalizar - Min: {np.min(features)}, Max: {np.max(features)}")
        self.logger.info(f"Valores NaN: {np.isnan(features).sum()}")
        self.logger.info(f"Valores infinitos: {np.isinf(features).sum()}")
        
        # Normalizar características de forma robusta
        from sklearn.preprocessing import RobustScaler
        scaler = RobustScaler()  # Más robusto que StandardScaler
        
        try:
            features_scaled = scaler.fit_transform(features)
            self.logger.info("Normalización exitosa")
        except Exception as e:
            self.logger.error(f"Error en normalización: {e}")
            return None, None, None
        
        # Verificar valores después de normalizar
        self.logger.info(f"Valores después de normalizar - Min: {np.min(features_scaled)}, Max: {np.max(features_scaled)}")
        self.logger.info(f"Valores NaN después: {np.isnan(features_scaled).sum()}")
        self.logger.info(f"Valores infinitos después: {np.isinf(features_scaled).sum()}")
        
        # Crear secuencias
        X, y = [], []
        for i in range(sequence_length, len(features_scaled) - prediction_horizon + 1):
            X.append(features_scaled[i-sequence_length:i])
            y.append(features_scaled[i+prediction_horizon-1, 3])  # Precio de cierre (índice 3)
        
        X = np.array(X)
        y = np.array(y)
        
        # Verificar secuencias finales
        self.logger.info(f"Secuencias creadas: {len(X)} muestras")
        self.logger.info(f"Shape X: {X.shape}, Shape y: {y.shape}")
        self.logger.info(f"X NaN: {np.isnan(X).sum()}, y NaN: {np.isnan(y).sum()}")
        self.logger.info(f"X infinitos: {np.isinf(X).sum()}, y infinitos: {np.isinf(y).sum()}")
        
        return X, y, scaler
    
    def train_robust_model(self, X, y):
        """Entrena un modelo robusto"""
        self.logger.info("Iniciando entrenamiento del modelo...")
        
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
            
            # Verificar datos antes de dividir
            if np.isnan(X).any() or np.isinf(X).any():
                self.logger.error("Datos X contienen NaN o infinitos")
                return None
            
            if np.isnan(y).any() or np.isinf(y).any():
                self.logger.error("Datos y contienen NaN o infinitos")
                return None
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Reshape para RandomForest
            X_train_reshaped = X_train.reshape(X_train.shape[0], -1)
            X_test_reshaped = X_test.reshape(X_test.shape[0], -1)
            
            self.logger.info(f"Datos de entrenamiento: {X_train_reshaped.shape}")
            self.logger.info(f"Datos de prueba: {X_test_reshaped.shape}")
            
            # Entrenar modelo
            model = RandomForestRegressor(
                n_estimators=50,  # Reducido para demo
                max_depth=10,
                random_state=42,
                n_jobs=-1,
                max_samples=0.8  # Usar submuestra para robustez
            )
            
            self.logger.info("Entrenando RandomForest...")
            model.fit(X_train_reshaped, y_train)
            
            # Evaluar modelo
            y_pred = model.predict(X_test_reshaped)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            self.logger.info(f"Modelo entrenado exitosamente!")
            self.logger.info(f"MSE: {mse:.4f}")
            self.logger.info(f"MAE: {mae:.4f}")
            self.logger.info(f"R²: {r2:.4f}")
            
            # Guardar modelo
            import joblib
            joblib.dump(model, 'checkpoints/robust_model.pkl')
            joblib.dump(scaler, 'checkpoints/robust_scaler.pkl')
            
            return {
                'model': model,
                'mse': mse,
                'mae': mae,
                'r2': r2,
                'n_samples': len(X),
                'n_features': X.shape[2]
            }
            
        except Exception as e:
            self.logger.error(f"Error entrenando modelo: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def start_monitoring(self):
        """Inicia monitoreo en background"""
        while self.is_running:
            try:
                # Verificar estado del sistema
                self.check_system_health()
                
                # Log de progreso
                if self.start_time:
                    elapsed = datetime.now() - self.start_time
                    self.logger.info(f"⏱️ Tiempo transcurrido: {elapsed}")
                
                time.sleep(30)  # Check cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"Error en monitoreo: {e}")
                time.sleep(10)
    
    def check_system_health(self):
        """Verifica salud del sistema"""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 90:
                self.logger.warning(f"⚠️ CPU alto: {cpu_percent}%")
            
            # Memoria
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.logger.warning(f"⚠️ Memoria alta: {memory.percent}%")
            
        except Exception as e:
            self.logger.error(f"Error verificando salud del sistema: {e}")
    
    async def run_training(self):
        """Ejecuta el entrenamiento completo"""
        try:
            self.logger.info("🚀 Iniciando entrenamiento corregido autónomo...")
            self.is_running = True
            self.start_time = datetime.now()
            
            # Iniciar monitoreo en background
            monitoring_thread = threading.Thread(target=self.start_monitoring)
            monitoring_thread.daemon = True
            monitoring_thread.start()
            
            # Paso 1: Generar datos
            df = self.generate_training_data(3000)  # Datos más pequeños para demo
            
            # Paso 2: Crear características
            df_features = self.create_features_robust(df)
            
            # Paso 3: Crear secuencias
            X, y, scaler = self.create_sequences_robust(df_features)
            
            if X is None or y is None:
                self.logger.error("❌ Error creando secuencias")
                return
            
            # Paso 4: Entrenar modelo
            results = self.train_robust_model(X, y)
            
            if results:
                self.logger.info("✅ Entrenamiento completado exitosamente!")
                self.logger.info(f"📊 Resultados: MSE={results['mse']:.4f}, MAE={results['mae']:.4f}, R²={results['r2']:.4f}")
                
                # Guardar resultados
                self.save_results(results)
            else:
                self.logger.error("❌ Error en el entrenamiento")
            
        except Exception as e:
            self.logger.error(f"Error en entrenamiento: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
        finally:
            self.is_running = False
            self.logger.info("🏁 Entrenamiento finalizado")
    
    def save_results(self, results):
        """Guarda resultados del entrenamiento"""
        try:
            results_file = f"logs/training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Preparar datos para JSON
            json_results = {
                'timestamp': datetime.now().isoformat(),
                'mse': float(results['mse']),
                'mae': float(results['mae']),
                'r2': float(results['r2']),
                'n_samples': int(results['n_samples']),
                'n_features': int(results['n_features']),
                'training_time': str(datetime.now() - self.start_time) if self.start_time else None
            }
            
            with open(results_file, 'w') as f:
                json.dump(json_results, f, indent=2)
            
            self.logger.info(f"📁 Resultados guardados en: {results_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")

def print_banner():
    """Imprime banner de inicio"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                🤖 ENTRENAMIENTO CORREGIDO AUTÓNOMO 🤖         ║
    ║                                                              ║
    ║  🚀 Sistema de entrenamiento robusto y automatizado          ║
    ║     con manejo avanzado de errores y datos                   ║
    ║                                                              ║
    ║  📊 Características:                                        ║
    ║     • Datos sintéticos robustos de trading                   ║
    ║     • Características técnicas con manejo de errores         ║
    ║     • Modelo RandomForest optimizado                         ║
    ║     • Monitoreo del sistema                                 ║
    ║     • Logging detallado                                     ║
    ║                                                              ║
    ║  ⏰ Tiempo estimado: 5-10 minutos                           ║
    ║  📁 Logs: logs/fixed_training.log                           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main():
    """Función principal"""
    print_banner()
    
    # Crear gestor de entrenamiento
    manager = FixedTrainingManager()
    
    try:
        # Iniciar entrenamiento
        await manager.run_training()
        
    except KeyboardInterrupt:
        logger.info("🛑 Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        logger.info("👋 ¡Hasta luego! El entrenamiento ha finalizado.")

if __name__ == "__main__":
    # Verificar Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        sys.exit(1)
    
    # Ejecutar entrenamiento
    asyncio.run(main())
