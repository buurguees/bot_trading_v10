#!/usr/bin/env python3
"""
Entrenamiento Simple Autónomo
=============================

Script simplificado para ejecutar entrenamiento de forma autónoma
sin dependencias complejas del sistema enterprise.
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
        logging.FileHandler('logs/simple_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleTrainingManager:
    """Gestor de entrenamiento simple"""
    
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
        """Genera datos de entrenamiento sintéticos"""
        self.logger.info("Generando datos de entrenamiento...")
        
        # Generar datos de trading sintéticos
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=n_samples, freq='1H')
        
        # Simular precios con tendencia y volatilidad
        base_price = 50000
        trend = np.linspace(0, 0.3, n_samples)  # Tendencia alcista
        noise = np.random.normal(0, 0.02, n_samples)  # Ruido
        price_changes = trend + noise
        
        prices = [base_price]
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Crear OHLCV
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': dates[i],
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.to_csv('data/training_data.csv', index=False)
        
        self.logger.info(f"Datos generados: {len(df)} registros")
        return df
    
    def create_features(self, df):
        """Crea características técnicas"""
        self.logger.info("Creando características técnicas...")
        
        # Media móvil simple
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad
        df['volatility'] = df['close'].rolling(window=20).std()
        
        # Retornos
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Remover NaN
        df = df.dropna()
        
        self.logger.info(f"Características creadas: {len(df.columns)} columnas")
        return df
    
    def create_sequences(self, df, sequence_length=60, prediction_horizon=1):
        """Crea secuencias para entrenamiento"""
        self.logger.info("Creando secuencias de entrenamiento...")
        
        # Seleccionar características
        feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_20', 'sma_50', 'rsi', 'macd', 'volatility']
        features = df[feature_columns].values
        
        # Normalizar características
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Crear secuencias
        X, y = [], []
        for i in range(sequence_length, len(features_scaled) - prediction_horizon + 1):
            X.append(features_scaled[i-sequence_length:i])
            y.append(features_scaled[i+prediction_horizon-1, 3])  # Precio de cierre
        
        X = np.array(X)
        y = np.array(y)
        
        self.logger.info(f"Secuencias creadas: {len(X)} muestras")
        return X, y, scaler
    
    def train_simple_model(self, X, y):
        """Entrena un modelo simple"""
        self.logger.info("Iniciando entrenamiento del modelo...")
        
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Reshape para RandomForest
            X_train_reshaped = X_train.reshape(X_train.shape[0], -1)
            X_test_reshaped = X_test.reshape(X_test.shape[0], -1)
            
            # Entrenar modelo
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.logger.info("Entrenando RandomForest...")
            model.fit(X_train_reshaped, y_train)
            
            # Evaluar modelo
            y_pred = model.predict(X_test_reshaped)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            self.logger.info(f"Modelo entrenado - MSE: {mse:.4f}, R²: {r2:.4f}")
            
            # Guardar modelo
            import joblib
            joblib.dump(model, 'checkpoints/simple_model.pkl')
            joblib.dump(scaler, 'checkpoints/scaler.pkl')
            
            return {
                'model': model,
                'mse': mse,
                'r2': r2,
                'n_samples': len(X),
                'n_features': X.shape[2]
            }
            
        except Exception as e:
            self.logger.error(f"Error entrenando modelo: {e}")
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
            self.logger.info("🚀 Iniciando entrenamiento simple autónomo...")
            self.is_running = True
            self.start_time = datetime.now()
            
            # Iniciar monitoreo en background
            monitoring_thread = threading.Thread(target=self.start_monitoring)
            monitoring_thread.daemon = True
            monitoring_thread.start()
            
            # Paso 1: Generar datos
            df = self.generate_training_data(5000)  # Datos más pequeños para demo
            
            # Paso 2: Crear características
            df_features = self.create_features(df)
            
            # Paso 3: Crear secuencias
            X, y, scaler = self.create_sequences(df_features)
            
            # Paso 4: Entrenar modelo
            results = self.train_simple_model(X, y)
            
            if results:
                self.logger.info("✅ Entrenamiento completado exitosamente!")
                self.logger.info(f"📊 Resultados: MSE={results['mse']:.4f}, R²={results['r2']:.4f}")
                
                # Guardar resultados
                self.save_results(results)
            else:
                self.logger.error("❌ Error en el entrenamiento")
            
        except Exception as e:
            self.logger.error(f"Error en entrenamiento: {e}")
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
    ║                🤖 ENTRENAMIENTO SIMPLE AUTÓNOMO 🤖            ║
    ║                                                              ║
    ║  🚀 Sistema de entrenamiento simplificado y automatizado     ║
    ║     con RandomForest y características técnicas              ║
    ║                                                              ║
    ║  📊 Características:                                        ║
    ║     • Datos sintéticos de trading                            ║
    ║     • Características técnicas (SMA, RSI, MACD, etc.)       ║
    ║     • Modelo RandomForest                                    ║
    ║     • Monitoreo del sistema                                 ║
    ║     • Logging completo                                      ║
    ║                                                              ║
    ║  ⏰ Tiempo estimado: 10-15 minutos                          ║
    ║  📁 Logs: logs/simple_training.log                          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main():
    """Función principal"""
    print_banner()
    
    # Crear gestor de entrenamiento
    manager = SimpleTrainingManager()
    
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
