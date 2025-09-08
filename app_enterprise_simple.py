#!/usr/bin/env python3
"""
app_enterprise_simple.py - Sistema Enterprise Simplificado
========================================================

Sistema enterprise que funciona con las dependencias actuales del proyecto.

Características:
- Entrenamiento avanzado con checkpoints
- Monitoreo en tiempo real
- Configuración flexible
- Logging estructurado
- Manejo de errores robusto

"""

import asyncio
import os
import sys
import logging
import argparse
import signal
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import threading
import subprocess

# Añadir directorio del proyecto al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configurar logging enterprise
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise_simple.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseTrainingEngine:
    """Motor de entrenamiento enterprise simplificado"""
    
    def __init__(self):
        self.config = self.load_config()
        self.checkpoint_dir = Path('checkpoints/enterprise')
        self.checkpoint_dir.mkdir(exist_ok=True)
        
    def load_config(self) -> Dict[str, Any]:
        """Cargar configuración"""
        return {
            'training': {
                'duration': 3600,  # 1 hora
                'checkpoint_interval': 600,  # 10 minutos
                'max_epochs': 100,
                'batch_size': 32,
                'learning_rate': 0.001,
                'test_size': 0.2,
                'random_state': 42
            },
            'model': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'random_state': 42
            },
            'features': {
                'sequence_length': 60,
                'n_features': 20
            }
        }
    
    def generate_synthetic_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generar datos sintéticos para entrenamiento"""
        logger.info(f"📊 Generando {n_samples} muestras sintéticas...")
        
        np.random.seed(42)
        
        # Generar datos de trading sintéticos
        data = []
        base_price = 50000  # Precio base BTC
        
        for i in range(n_samples):
            # Simular precio con tendencia y ruido
            trend = np.sin(i / 100) * 1000
            noise = np.random.normal(0, 500)
            price = base_price + trend + noise
            
            # Generar OHLCV
            high = price * (1 + abs(np.random.normal(0, 0.02)))
            low = price * (1 - abs(np.random.normal(0, 0.02)))
            open_price = price + np.random.normal(0, 100)
            close = price
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': datetime.now().timestamp() + i * 3600,  # 1 hora entre datos
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        logger.info(f"✅ Datos generados: {df.shape}")
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crear características técnicas"""
        logger.info("🔧 Creando características técnicas...")
        
        # Calcular indicadores técnicos
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad
        df['volatility'] = df['close'].rolling(window=20).std()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price change
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_20'] = df['close'].pct_change(20)
        
        # High-Low spread
        df['hl_spread'] = (df['high'] - df['low']) / df['close']
        
        # Open-Close spread
        df['oc_spread'] = (df['close'] - df['open']) / df['open']
        
        # Drop NaN values
        df = df.dropna()
        
        logger.info(f"✅ Características creadas: {df.shape}")
        return df
    
    def create_sequences(self, df: pd.DataFrame) -> tuple:
        """Crear secuencias para entrenamiento"""
        logger.info("🔄 Creando secuencias de entrenamiento...")
        
        # Seleccionar características
        feature_cols = [
            'sma_5', 'sma_20', 'sma_50', 'rsi', 'macd', 'macd_signal',
            'bb_upper', 'bb_middle', 'bb_lower', 'volatility',
            'volume_ratio', 'price_change', 'price_change_5', 'price_change_20',
            'hl_spread', 'oc_spread'
        ]
        
        features = df[feature_cols].values
        target = df['close'].values
        
        # Verificar datos
        logger.info(f"📊 Features shape: {features.shape}")
        logger.info(f"📊 Target shape: {target.shape}")
        
        # Verificar NaN e infinitos
        nan_count = np.isnan(features).sum()
        inf_count = np.isinf(features).sum()
        logger.info(f"📊 NaN count: {nan_count}, Inf count: {inf_count}")
        
        # Limpiar datos
        features = np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)
        target = np.nan_to_num(target, nan=0.0, posinf=1e6, neginf=-1e6)
        
        # Normalizar características
        scaler = RobustScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Crear secuencias
        sequence_length = self.config['features']['sequence_length']
        X, y = [], []
        
        for i in range(sequence_length, len(features_scaled)):
            X.append(features_scaled[i-sequence_length:i])
            y.append(target[i])
        
        X = np.array(X)
        y = np.array(y)
        
        # Reshape para RandomForest
        X = X.reshape(X.shape[0], -1)
        
        logger.info(f"✅ Secuencias creadas: X={X.shape}, y={y.shape}")
        return X, y, scaler
    
    async def train_model(self, duration: int = 3600) -> Dict[str, Any]:
        """Entrenar modelo enterprise"""
        logger.info(f"🚀 Iniciando entrenamiento enterprise de {duration} segundos...")
        
        start_time = time.time()
        checkpoint_interval = self.config['training']['checkpoint_interval']
        last_checkpoint = start_time
        
        try:
            # Generar datos
            df = self.generate_synthetic_data(10000)
            df_features = self.create_features(df)
            
            # Crear secuencias
            X, y, scaler = self.create_sequences(df_features)
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config['training']['test_size'],
                random_state=self.config['training']['random_state']
            )
            
            logger.info(f"📊 Datos de entrenamiento: {X_train.shape}")
            logger.info(f"📊 Datos de prueba: {X_test.shape}")
            
            # Crear modelo
            model = RandomForestRegressor(
                n_estimators=self.config['model']['n_estimators'],
                max_depth=self.config['model']['max_depth'],
                min_samples_split=self.config['model']['min_samples_split'],
                min_samples_leaf=self.config['model']['min_samples_leaf'],
                random_state=self.config['model']['random_state'],
                n_jobs=-1
            )
            
            # Entrenar modelo
            logger.info("🎯 Entrenando modelo...")
            model.fit(X_train, y_train)
            
            # Evaluar modelo
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Guardar modelo y scaler
            model_path = self.checkpoint_dir / 'enterprise_model.pkl'
            scaler_path = self.checkpoint_dir / 'enterprise_scaler.pkl'
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            # Crear checkpoint
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'duration': time.time() - start_time,
                'metrics': {
                    'mse': float(mse),
                    'mae': float(mae),
                    'r2': float(r2)
                },
                'model_path': str(model_path),
                'scaler_path': str(scaler_path),
                'data_shape': {
                    'X_train': X_train.shape,
                    'X_test': X_test.shape,
                    'y_train': y_train.shape,
                    'y_test': y_test.shape
                }
            }
            
            # Guardar checkpoint
            checkpoint_path = self.checkpoint_dir / f'checkpoint_{int(time.time())}.json'
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            
            logger.info(f"✅ Modelo entrenado exitosamente!")
            logger.info(f"📊 MSE: {mse:.4f}")
            logger.info(f"📊 MAE: {mae:.4f}")
            logger.info(f"📊 R²: {r2:.4f}")
            logger.info(f"💾 Modelo guardado: {model_path}")
            logger.info(f"💾 Scaler guardado: {scaler_path}")
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            raise
    
    async def resume_training(self, checkpoint_path: str) -> Dict[str, Any]:
        """Reanudar entrenamiento desde checkpoint"""
        logger.info(f"🔄 Reanudando entrenamiento desde: {checkpoint_path}")
        
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)
            
            # Cargar modelo y scaler
            model = joblib.load(checkpoint['model_path'])
            scaler = joblib.load(checkpoint['scaler_path'])
            
            logger.info(f"✅ Checkpoint cargado: {checkpoint['timestamp']}")
            logger.info(f"📊 Métricas anteriores: {checkpoint['metrics']}")
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"❌ Error cargando checkpoint: {e}")
            raise

class EnterpriseMonitoringSystem:
    """Sistema de monitoreo enterprise"""
    
    def __init__(self):
        self.metrics = {}
        self.running = False
        
    async def start(self):
        """Iniciar sistema de monitoreo"""
        logger.info("📊 Iniciando sistema de monitoreo...")
        self.running = True
        
        # Iniciar dashboard en hilo separado
        dashboard_thread = threading.Thread(target=self._start_dashboard)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        logger.info("✅ Sistema de monitoreo iniciado")
    
    def _start_dashboard(self):
        """Iniciar dashboard web"""
        try:
            subprocess.run(['python', 'monitoring/main_dashboard.py'])
        except Exception as e:
            logger.error(f"❌ Error iniciando dashboard: {e}")
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """Actualizar métricas"""
        self.metrics.update(metrics)
        logger.info(f"📊 Métricas actualizadas: {metrics}")

class EnterpriseTradingBot:
    """Sistema Enterprise del Trading Bot v10"""
    
    def __init__(self):
        self.running = True
        self.training_engine = EnterpriseTrainingEngine()
        self.monitoring_system = EnterpriseMonitoringSystem()
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Configurar manejo de señales"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Manejar señales del sistema"""
        logger.info(f"Recibida señal {signum}, iniciando shutdown graceful...")
        self.running = False
    
    def show_banner(self):
        """Mostrar banner enterprise"""
        print("\n" + "="*80)
        print("🚀 TRADING BOT v10 - ENTERPRISE SIMPLE")
        print("="*80)
        print("🏢 Sistema Enterprise Simplificado")
        print("⚡ Entrenamiento Avanzado | 📊 Monitoreo en Tiempo Real")
        print("🛡️ Checkpoints Automáticos | 🔧 Configuración Flexible")
        print("="*80)
    
    def show_menu(self):
        """Mostrar menú enterprise"""
        print("\n📋 MENÚ ENTERPRISE:")
        print("1. 🚀 Entrenamiento Enterprise (1 hora)")
        print("2. ⚡ Entrenamiento Rápido (15 min)")
        print("3. 📊 Monitoreo en Tiempo Real")
        print("4. 🔧 Configuración del Sistema")
        print("5. 📈 Análisis de Performance")
        print("6. 🔄 Reanudar Entrenamiento")
        print("7. 📊 Dashboard Web")
        print("8. 🔍 Logs y Debugging")
        print("0. 🚪 Salir")
        print("-" * 50)
    
    async def run_training_enterprise(self, duration: int = 3600):
        """Ejecutar entrenamiento enterprise"""
        try:
            # Iniciar monitoreo
            await self.monitoring_system.start()
            
            # Ejecutar entrenamiento
            results = await self.training_engine.train_model(duration)
            
            # Actualizar métricas
            self.monitoring_system.update_metrics(results['metrics'])
            
            logger.info("✅ Entrenamiento enterprise completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento enterprise: {e}")
            raise
    
    async def run_quick_training(self):
        """Ejecutar entrenamiento rápido"""
        try:
            logger.info("⚡ Iniciando entrenamiento rápido...")
            
            # Configurar entrenamiento rápido
            quick_config = self.training_engine.config.copy()
            quick_config['training']['duration'] = 900  # 15 minutos
            quick_config['model']['n_estimators'] = 50
            
            results = await self.training_engine.train_model(900)
            
            logger.info("✅ Entrenamiento rápido completado")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento rápido: {e}")
            raise
    
    async def start_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        try:
            await self.monitoring_system.start()
            
            # Mantener corriendo
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
            raise
    
    def show_config(self):
        """Mostrar configuración actual"""
        print("\n🔧 CONFIGURACIÓN ENTERPRISE:")
        config = self.training_engine.config
        
        print(f"⏱️  Duración de entrenamiento: {config['training']['duration']}s")
        print(f"💾 Intervalo de checkpoints: {config['training']['checkpoint_interval']}s")
        print(f"🎯 Máximo de epochs: {config['training']['max_epochs']}")
        print(f"📦 Batch size: {config['training']['batch_size']}")
        print(f"📚 Learning rate: {config['training']['learning_rate']}")
        print(f"🌳 N estimators: {config['model']['n_estimators']}")
        print(f"📏 Max depth: {config['model']['max_depth']}")
    
    async def run_analysis(self):
        """Ejecutar análisis de performance"""
        try:
            logger.info("📈 Iniciando análisis de performance...")
            
            # Buscar checkpoints recientes
            checkpoint_dir = Path('checkpoints/enterprise')
            checkpoints = list(checkpoint_dir.glob('checkpoint_*.json'))
            
            if not checkpoints:
                logger.warning("❌ No se encontraron checkpoints")
                return
            
            # Cargar checkpoint más reciente
            latest_checkpoint = max(checkpoints, key=lambda x: x.stat().st_mtime)
            
            with open(latest_checkpoint, 'r') as f:
                checkpoint = json.load(f)
            
            print("\n📊 ANÁLISIS DE PERFORMANCE:")
            print(f"📅 Fecha: {checkpoint['timestamp']}")
            print(f"⏱️  Duración: {checkpoint['duration']:.2f}s")
            print(f"📊 MSE: {checkpoint['metrics']['mse']:.4f}")
            print(f"📊 MAE: {checkpoint['metrics']['mae']:.4f}")
            print(f"📊 R²: {checkpoint['metrics']['r2']:.4f}")
            print(f"📊 Datos: {checkpoint['data_shape']}")
            
            logger.info("✅ Análisis completado")
            
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            raise
    
    async def resume_training(self):
        """Reanudar entrenamiento desde checkpoint"""
        try:
            logger.info("🔄 Reanudando entrenamiento...")
            
            # Buscar checkpoints
            checkpoint_dir = Path('checkpoints/enterprise')
            checkpoints = list(checkpoint_dir.glob('checkpoint_*.json'))
            
            if not checkpoints:
                logger.warning("❌ No se encontraron checkpoints")
                return
            
            # Mostrar checkpoints disponibles
            print("\n📋 CHECKPOINTS DISPONIBLES:")
            for i, checkpoint in enumerate(checkpoints):
                with open(checkpoint, 'r') as f:
                    data = json.load(f)
                print(f"{i+1}. {data['timestamp']} - R²: {data['metrics']['r2']:.4f}")
            
            # Seleccionar checkpoint
            choice = input("\n🎯 Selecciona checkpoint (número): ").strip()
            try:
                selected_checkpoint = checkpoints[int(choice) - 1]
                results = await self.training_engine.resume_training(str(selected_checkpoint))
                logger.info("✅ Entrenamiento reanudado")
                return results
            except (ValueError, IndexError):
                logger.error("❌ Selección inválida")
                
        except Exception as e:
            logger.error(f"❌ Error reanudando entrenamiento: {e}")
            raise
    
    async def start_dashboard(self):
        """Iniciar dashboard web"""
        try:
            logger.info("📊 Iniciando dashboard web...")
            
            import subprocess
            import threading
            
            def run_dashboard():
                subprocess.run(['python', 'monitoring/main_dashboard.py'])
            
            # Ejecutar en hilo separado
            dashboard_thread = threading.Thread(target=run_dashboard)
            dashboard_thread.daemon = True
            dashboard_thread.start()
            
            logger.info("✅ Dashboard iniciado en http://localhost:8050")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando dashboard: {e}")
            raise
    
    async def show_logs(self):
        """Mostrar logs recientes"""
        try:
            log_file = 'logs/enterprise_simple.log'
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print("\n📝 ÚLTIMOS LOGS:")
                    print("-" * 50)
                    for line in lines[-20:]:  # Últimas 20 líneas
                        print(line.strip())
            else:
                print("❌ No se encontraron logs")
                
        except Exception as e:
            logger.error(f"❌ Error leyendo logs: {e}")
    
    async def run_interactive_mode(self):
        """Modo interactivo"""
        self.show_banner()
        
        while self.running:
            try:
                self.show_menu()
                choice = input("\n🎯 Selecciona una opción: ").strip()
                
                if choice == '1':
                    duration = input("⏱️  Duración en segundos (3600 para 1 hora): ").strip()
                    duration = int(duration) if duration else 3600
                    await self.run_training_enterprise(duration)
                    
                elif choice == '2':
                    await self.run_quick_training()
                    
                elif choice == '3':
                    await self.start_monitoring()
                    
                elif choice == '4':
                    self.show_config()
                    
                elif choice == '5':
                    await self.run_analysis()
                    
                elif choice == '6':
                    await self.resume_training()
                    
                elif choice == '7':
                    await self.start_dashboard()
                    
                elif choice == '8':
                    await self.show_logs()
                    
                elif choice == '0':
                    logger.info("👋 Saliendo del sistema enterprise...")
                    break
                    
                else:
                    print("❌ Opción inválida")
                    
            except KeyboardInterrupt:
                logger.info("👋 Interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
    
    async def run_headless_mode(self, mode: str, duration: int = 3600):
        """Modo headless para automatización"""
        try:
            logger.info(f"🤖 Iniciando modo headless: {mode}")
            
            if mode == 'train':
                await self.run_training_enterprise(duration)
            elif mode == 'quick':
                await self.run_quick_training()
            elif mode == 'monitor':
                await self.start_monitoring()
            elif mode == 'analyze':
                await self.run_analysis()
            else:
                raise ValueError(f"Modo no válido: {mode}")
                
            logger.info("✅ Modo headless completado")
            
        except Exception as e:
            logger.error(f"❌ Error en modo headless: {e}")
            raise

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Trading Bot v10 Enterprise Simple')
    parser.add_argument('--mode', choices=['train', 'quick', 'monitor', 'analyze'], 
                       help='Modo de ejecución')
    parser.add_argument('--duration', type=int, default=3600, 
                       help='Duración en segundos (solo para modo train)')
    parser.add_argument('--headless', action='store_true', 
                       help='Modo headless (sin interfaz)')
    
    args = parser.parse_args()
    
    # Crear directorios necesarios
    os.makedirs('logs', exist_ok=True)
    os.makedirs('checkpoints/enterprise', exist_ok=True)
    
    # Inicializar sistema enterprise
    bot = EnterpriseTradingBot()
    
    try:
        if args.headless and args.mode:
            # Modo headless
            await bot.run_headless_mode(args.mode, args.duration)
        else:
            # Modo interactivo
            await bot.run_interactive_mode()
            
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        logger.info("🏁 Sistema enterprise finalizado")

if __name__ == "__main__":
    asyncio.run(main())
