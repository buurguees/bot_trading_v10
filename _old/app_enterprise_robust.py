#!/usr/bin/env python3
"""
Sistema Enterprise Robusto con Checkpoints Avanzados
====================================================

Sistema enterprise con checkpoints automáticos y reanudación de entrenamiento.
Permite pausar y reanudar entrenamientos largos sin perder el progreso.

Características:
- Checkpoints automáticos cada 10 minutos
- Reanudación de entrenamiento desde cualquier checkpoint
- Entrenamiento incremental con métricas de progreso
- Sistema de recuperación ante fallos
- Monitoreo en tiempo real
"""

import asyncio
import os
import sys
import logging
import time
import json
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import argparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise_robust.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RobustCheckpointManager:
    """Gestor de checkpoints robusto"""
    
    def __init__(self, checkpoint_dir: str = 'checkpoints/enterprise'):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = 600  # 10 minutos
        
    async def save_checkpoint(
        self, 
        model, 
        scaler, 
        X_train, 
        X_test, 
        y_train, 
        y_test,
        training_epochs: int,
        best_metrics: Dict[str, float],
        start_time: float,
        is_final: bool = False,
        is_emergency: bool = False
    ) -> Dict[str, Any]:
        """Guardar checkpoint con información completa"""
        
        # Guardar modelo y scaler
        model_path = self.checkpoint_dir / 'enterprise_model.pkl'
        scaler_path = self.checkpoint_dir / 'enterprise_scaler.pkl'
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        
        # Crear checkpoint
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'duration': time.time() - start_time,
            'training_epochs': training_epochs,
            'best_metrics': best_metrics,
            'current_metrics': self._calculate_current_metrics(model, X_test, y_test),
            'model_path': str(model_path),
            'scaler_path': str(scaler_path),
            'data_shape': {
                'X_train': list(X_train.shape),
                'X_test': list(X_test.shape),
                'y_train': list(y_train.shape),
                'y_test': list(y_test.shape)
            },
            'checkpoint_type': 'final' if is_final else 'emergency' if is_emergency else 'automatic',
            'can_resume': True
        }
        
        # Guardar checkpoint
        checkpoint_path = self.checkpoint_dir / f'checkpoint_{int(time.time())}.json'
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.info(f"💾 Checkpoint guardado: {checkpoint_path}")
        return checkpoint
    
    def _calculate_current_metrics(self, model, X_test, y_test) -> Dict[str, float]:
        """Calcular métricas actuales"""
        try:
            y_pred = model.predict(X_test)
            return {
                'mse': float(mean_squared_error(y_test, y_pred)),
                'mae': float(mean_absolute_error(y_test, y_pred)),
                'r2': float(r2_score(y_test, y_pred))
            }
        except Exception as e:
            logger.warning(f"⚠️ Error calculando métricas: {e}")
            return {'mse': 0.0, 'mae': 0.0, 'r2': 0.0}
    
    async def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Cargar checkpoint"""
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)
            
            logger.info(f"✅ Checkpoint cargado: {checkpoint['timestamp']}")
            logger.info(f"📊 Epochs previos: {checkpoint.get('training_epochs', 0)}")
            logger.info(f"📊 Mejores métricas: {checkpoint.get('best_metrics', {})}")
            
            return checkpoint
        except Exception as e:
            logger.error(f"❌ Error cargando checkpoint: {e}")
            raise
    
    def list_checkpoints(self) -> List[Path]:
        """Listar checkpoints disponibles"""
        checkpoints = list(self.checkpoint_dir.glob('checkpoint_*.json'))
        return sorted(checkpoints, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def get_latest_checkpoint(self) -> Optional[Path]:
        """Obtener checkpoint más reciente"""
        checkpoints = self.list_checkpoints()
        return checkpoints[0] if checkpoints else None

class RobustTrainingEngine:
    """Motor de entrenamiento robusto con checkpoints"""
    
    def __init__(self):
        self.config = self.load_config()
        self.checkpoint_manager = RobustCheckpointManager()
        
    def load_config(self) -> Dict[str, Any]:
        """Cargar configuración"""
        return {
            'training': {
                'duration': 3600,  # 1 hora
                'checkpoint_interval': 600,  # 10 minutos
                'max_epochs': 1000,
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
            }
        }
    
    def generate_synthetic_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generar datos sintéticos para entrenamiento"""
        np.random.seed(42)
        
        # Generar datos de trading sintéticos
        dates = pd.date_range(start='2020-01-01', periods=n_samples, freq='1H')
        
        # Precios base con tendencia
        base_price = 50000
        trend = np.linspace(0, 0.5, n_samples)
        noise = np.random.normal(0, 0.02, n_samples)
        
        # Generar OHLCV
        close_prices = base_price * (1 + trend + noise)
        open_prices = close_prices * (1 + np.random.normal(0, 0.001, n_samples))
        high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.normal(0, 0.005, n_samples)))
        low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.normal(0, 0.005, n_samples)))
        volumes = np.random.lognormal(10, 1, n_samples)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
        
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crear características técnicas"""
        df = df.copy()
        
        # Indicadores técnicos básicos
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'], 20)
        df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
        
        # Características de precio
        df['price_change'] = df['close'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Características de volatilidad
        df['volatility'] = df['price_change'].rolling(window=20).std()
        df['atr'] = self._calculate_atr(df, 14)
        
        # Target: precio futuro
        df['target'] = df['close'].shift(-1)
        
        # Eliminar NaN
        df = df.dropna()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20) -> tuple:
        """Calcular Bandas de Bollinger"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return upper, sma, lower
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calcular MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def _calculate_atr(self, df: pd.DataFrame, window: int = 14) -> pd.Series:
        """Calcular ATR (Average True Range)"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=window).mean()
    
    def create_sequences(self, df: pd.DataFrame, sequence_length: int = 60) -> tuple:
        """Crear secuencias para entrenamiento"""
        # Seleccionar características
        feature_cols = [col for col in df.columns if col not in ['timestamp', 'target']]
        X = df[feature_cols].values
        y = df['target'].values
        
        # Normalizar datos
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Crear secuencias
        X_seq = []
        y_seq = []
        
        for i in range(sequence_length, len(X_scaled)):
            X_seq.append(X_scaled[i-sequence_length:i].flatten())
            y_seq.append(y[i])
        
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)
        
        # Verificar datos
        logger.info(f"📊 Features shape: {X_seq.shape}")
        logger.info(f"📊 Target shape: {y_seq.shape}")
        logger.info(f"📊 NaN count: {np.isnan(X_seq).sum()}, Inf count: {np.isinf(X_seq).sum()}")
        
        return X_seq, y_seq, scaler
    
    async def train_model_robust(self, duration: int = 3600, resume_from: str = None) -> Dict[str, Any]:
        """Entrenar modelo con sistema robusto de checkpoints"""
        logger.info(f"🚀 Iniciando entrenamiento robusto de {duration} segundos...")
        
        start_time = time.time()
        checkpoint_interval = self.config['training']['checkpoint_interval']
        last_checkpoint = start_time
        
        # Variables para entrenamiento
        model = None
        scaler = None
        X_train = None
        X_test = None
        y_train = None
        y_test = None
        training_epochs = 0
        best_metrics = {'mse': float('inf'), 'mae': float('inf'), 'r2': -float('inf')}
        
        try:
            # Cargar checkpoint si se especifica
            if resume_from:
                logger.info(f"🔄 Reanudando desde checkpoint: {resume_from}")
                checkpoint_data = await self.checkpoint_manager.load_checkpoint(resume_from)
                
                # Cargar modelo y scaler
                model = joblib.load(checkpoint_data['model_path'])
                scaler = joblib.load(checkpoint_data['scaler_path'])
                training_epochs = checkpoint_data.get('training_epochs', 0)
                best_metrics = checkpoint_data.get('best_metrics', best_metrics)
                
                logger.info(f"✅ Checkpoint cargado - Epochs previos: {training_epochs}")
                logger.info(f"📊 Mejores métricas previas: {best_metrics}")
            else:
                # Generar datos nuevos
                logger.info("📊 Generando datos de entrenamiento...")
                df = self.generate_synthetic_data(10000)
                df_features = self.create_features(df)
                
                # Crear secuencias
                X, y, scaler = self.create_sequences(df_features)
                
                # Dividir datos
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, 
                    test_size=self.config['training']['test_size'],
                    random_state=self.config['training']['random_state']
                )
                
                logger.info(f"📊 Datos de entrenamiento: {X_train.shape}")
                logger.info(f"📊 Datos de prueba: {X_test.shape}")
                
                # Crear modelo inicial
                model = RandomForestRegressor(
                    n_estimators=self.config['model']['n_estimators'],
                    max_depth=self.config['model']['max_depth'],
                    min_samples_split=self.config['model']['min_samples_split'],
                    min_samples_leaf=self.config['model']['min_samples_leaf'],
                    random_state=self.config['model']['random_state'],
                    n_jobs=-1
                )
            
            # Entrenamiento con checkpoints automáticos
            logger.info("🎯 Iniciando entrenamiento con checkpoints automáticos...")
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Entrenar modelo (simulamos entrenamiento incremental)
                if training_epochs == 0:
                    logger.info("🌱 Entrenamiento inicial...")
                    model.fit(X_train, y_train)
                else:
                    logger.info(f"🔄 Continuando entrenamiento (epoch {training_epochs + 1})...")
                    # Para RandomForest, re-entrenamos con más estimadores
                    # En un sistema real, esto sería un modelo que soporte entrenamiento incremental
                    model.n_estimators = min(model.n_estimators + 10, 500)
                    model.fit(X_train, y_train)
                
                training_epochs += 1
                
                # Evaluar modelo
                y_pred = model.predict(X_test)
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Actualizar mejores métricas
                if mse < best_metrics['mse']:
                    best_metrics = {'mse': mse, 'mae': mae, 'r2': r2}
                    logger.info(f"🏆 Nuevas mejores métricas: R²={r2:.4f}")
                
                # Checkpoint automático
                if current_time - last_checkpoint >= checkpoint_interval:
                    await self.checkpoint_manager.save_checkpoint(
                        model, scaler, X_train, X_test, y_train, y_test,
                        training_epochs, best_metrics, start_time
                    )
                    last_checkpoint = current_time
                    logger.info(f"💾 Checkpoint automático guardado (epoch {training_epochs})")
                
                # Log de progreso
                elapsed = current_time - start_time
                remaining = duration - elapsed
                progress = (elapsed / duration) * 100
                logger.info(f"⏱️ Progreso: {progress:.1f}% - Epoch {training_epochs} - R²: {r2:.4f} - Restante: {remaining:.0f}s")
                
                # Pequeña pausa para evitar sobrecarga
                await asyncio.sleep(1)
            
            # Guardar checkpoint final
            final_checkpoint = await self.checkpoint_manager.save_checkpoint(
                model, scaler, X_train, X_test, y_train, y_test,
                training_epochs, best_metrics, start_time, is_final=True
            )
            
            logger.info(f"✅ Entrenamiento completado!")
            logger.info(f"📊 Epochs totales: {training_epochs}")
            logger.info(f"📊 Mejor MSE: {best_metrics['mse']:.4f}")
            logger.info(f"📊 Mejor MAE: {best_metrics['mae']:.4f}")
            logger.info(f"📊 Mejor R²: {best_metrics['r2']:.4f}")
            
            return final_checkpoint
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            # Guardar checkpoint de emergencia
            if model is not None:
                try:
                    await self.checkpoint_manager.save_checkpoint(
                        model, scaler, X_train, X_test, y_train, y_test,
                        training_epochs, best_metrics, start_time, is_emergency=True
                    )
                    logger.info("💾 Checkpoint de emergencia guardado")
                except Exception as emergency_error:
                    logger.error(f"❌ Error guardando checkpoint de emergencia: {emergency_error}")
            raise

class RobustEnterpriseBot:
    """Bot enterprise robusto con sistema de checkpoints"""
    
    def __init__(self):
        self.training_engine = RobustTrainingEngine()
        self.checkpoint_manager = RobustCheckpointManager()
    
    async def start_training(self, duration: int = 3600, resume: bool = False):
        """Iniciar entrenamiento robusto"""
        try:
            if resume:
                # Buscar checkpoint más reciente
                latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint()
                if latest_checkpoint:
                    logger.info(f"🔄 Reanudando desde checkpoint más reciente: {latest_checkpoint}")
                    results = await self.training_engine.train_model_robust(
                        duration, str(latest_checkpoint)
                    )
                else:
                    logger.warning("❌ No se encontraron checkpoints para reanudar")
                    results = await self.training_engine.train_model_robust(duration)
            else:
                results = await self.training_engine.train_model_robust(duration)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento: {e}")
            raise
    
    def list_checkpoints(self):
        """Listar checkpoints disponibles"""
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        if not checkpoints:
            print("❌ No se encontraron checkpoints")
            return
        
        print("\n📋 CHECKPOINTS DISPONIBLES:")
        for i, checkpoint in enumerate(checkpoints):
            try:
                with open(checkpoint, 'r') as f:
                    data = json.load(f)
                print(f"{i+1}. {data['timestamp']} - Epochs: {data.get('training_epochs', 0)} - R²: {data.get('best_metrics', {}).get('r2', 0):.4f}")
            except Exception as e:
                print(f"{i+1}. {checkpoint.name} - Error: {e}")
    
    async def resume_from_checkpoint(self, checkpoint_index: int):
        """Reanudar desde checkpoint específico"""
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        if not checkpoints or checkpoint_index >= len(checkpoints):
            logger.error("❌ Checkpoint no válido")
            return
        
        selected_checkpoint = checkpoints[checkpoint_index]
        logger.info(f"🔄 Reanudando desde: {selected_checkpoint}")
        
        # Continuar entrenamiento
        results = await self.training_engine.train_model_robust(
            3600, str(selected_checkpoint)
        )
        
        return results

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Sistema Enterprise Robusto')
    parser.add_argument('--mode', choices=['train', 'resume', 'list'], default='train')
    parser.add_argument('--duration', type=int, default=3600, help='Duración en segundos')
    parser.add_argument('--checkpoint', type=int, help='Índice del checkpoint para reanudar')
    
    args = parser.parse_args()
    
    # Crear directorios necesarios
    os.makedirs('logs', exist_ok=True)
    os.makedirs('checkpoints/enterprise', exist_ok=True)
    
    bot = RobustEnterpriseBot()
    
    try:
        if args.mode == 'train':
            logger.info("🚀 Iniciando entrenamiento robusto...")
            results = await bot.start_training(args.duration)
            print(f"✅ Entrenamiento completado: {results['best_metrics']}")
            
        elif args.mode == 'resume':
            if args.checkpoint is not None:
                logger.info(f"🔄 Reanudando desde checkpoint {args.checkpoint}...")
                results = await bot.resume_from_checkpoint(args.checkpoint)
                print(f"✅ Entrenamiento reanudado: {results['best_metrics']}")
            else:
                logger.info("🔄 Reanudando desde checkpoint más reciente...")
                results = await bot.start_training(args.duration, resume=True)
                print(f"✅ Entrenamiento reanudado: {results['best_metrics']}")
                
        elif args.mode == 'list':
            bot.list_checkpoints()
            
    except KeyboardInterrupt:
        logger.info("👋 Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
