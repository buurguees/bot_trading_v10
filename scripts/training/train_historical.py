# -*- coding: utf-8 -*-
"""
scripts/training/train_historical.py
====================================
Bot Trading v10 Enterprise - Entrenamiento Histórico Paralelo

Entrenamiento paralelo de agentes usando timestamps sincronizados.
Calcula métricas conjuntas y almacena mejores/peores estrategias y runs.

Autor: Bot Trading v10 Enterprise
Fecha: 2025-09-12
Versión: 1.0.0
"""

import asyncio
import json
import logging
import pickle
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import uuid

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

# Imports del proyecto

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from config.unified_config import get_config_manager
from core.data.database import DatabaseManager

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/train_historical.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TrainHistoricalEnterprise:
    """
    Clase principal para entrenamiento histórico paralelo de agentes.
    
    Características:
    - Entrenamiento paralelo de todos los símbolos
    - Uso de timestamps sincronizados del master_timeline.json
    - Cálculo de métricas conjuntas por run
    - Almacenamiento de mejores/peores estrategias y runs
    - Seguimiento de progreso en tiempo real
    """
    
    def __init__(self, progress_id: str, training_mode: str = None):
        """
        Inicializa el entrenador histórico.
        
        Args:
            progress_id: ID único para seguimiento de progreso
            training_mode: Modo de entrenamiento (ultra_fast, fast, optimized, complete)
        """
        self.progress_id = progress_id
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.config_manager = get_config_manager()
        self.db_manager = None
        self.symbols = []
        self.timeframes = []
        
        # Configuración de modo de entrenamiento
        self.training_mode = training_mode or self.config_manager.get('training_objectives', {}).get('default_training_mode', 'fast')
        self.training_config = self._load_training_mode_config()
        
        self.symbol_configs = {}  # Configuraciones por símbolo
        self.master_timeline = []
        
        # Fechas basadas en el modo de entrenamiento
        data_period_days = self.training_config.get('data_period_days', 90)
        self.start_date = datetime.now(timezone.utc) - timedelta(days=data_period_days)
        self.end_date = datetime.now(timezone.utc)
        
        # Directorios de trabajo
        self.agents_dir = Path("agents")
        self.tmp_dir = Path("data/tmp")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de análisis jerárquico (específica del modo de entrenamiento)
        self.hierarchical_config = self.training_config.get('hierarchical_analysis', {})
        
        # Métricas conjuntas
        self.joint_metrics = {}
        self.agent_results = {}
        
        logger.info(f"🚀 TrainHistoricalEnterprise inicializado - Run ID: {self.run_id}")
        logger.info(f"⚙️ Modo de entrenamiento: {self.training_config.get('name', 'Desconocido')}")
        logger.info(f"📅 Período de datos: {data_period_days} días")
    
    def _load_training_mode_config(self) -> Dict:
        """Carga la configuración del modo de entrenamiento"""
        try:
            training_modes = self.config_manager.get('training_objectives', {}).get('training_modes', {})
            mode_config = training_modes.get(self.training_mode, training_modes.get('fast', {}))
            
            if not mode_config:
                logger.warning(f"⚠️ Modo de entrenamiento '{self.training_mode}' no encontrado, usando 'fast'")
                mode_config = training_modes.get('fast', {})
            
            return mode_config
            
        except Exception as e:
            logger.error(f"❌ Error cargando configuración de modo de entrenamiento: {e}")
            return {}
    
    async def initialize(self) -> bool:
        """
        Inicializa las dependencias del entrenador.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Inicializar base de datos
            self.db_manager = DatabaseManager()
            
            # Cargar configuración
            self.symbols = self.config_manager.get_symbols()
            # Usar solo los timeframes de ejecución (real_time + analysis + strategic)
            all_timeframes = self.config_manager.get_timeframes()
            self.timeframes = all_timeframes  # Todos los timeframes para entrenamiento
            self.training_config = self.config_manager.get('training_objectives', {})
            
            # Cargar configuraciones por símbolo (incluyendo leverage_range)
            symbols_config = self.config_manager.get('symbols', {})
            self.symbol_configs = symbols_config.get('symbol_configs', {})
            
            # Cargar sistema de rewards
            self.rewards_config = self.config_manager.get_rewards_config()
            logger.info(f"✅ Sistema de rewards cargado: {len(self.rewards_config)} secciones")
            
            # Configurar fechas
            self.start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
            self.end_date = datetime.now(timezone.utc)
            
            # Cargar timeline maestro
            await self._load_master_timeline()
            
            # Crear directorios de agentes
            for symbol in self.symbols:
                agent_dir = self.agents_dir / symbol
                agent_dir.mkdir(parents=True, exist_ok=True)
                (agent_dir / "metrics").mkdir(exist_ok=True)
                (agent_dir / "metadata").mkdir(exist_ok=True)
            
            logger.info(f"✅ Inicialización completada - {len(self.symbols)} símbolos, {len(self.timeframes)} timeframes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en inicialización: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def _load_master_timeline(self) -> None:
        """Carga el timeline maestro desde master_timeline.json"""
        try:
            timeline_path = Path("data/sync/master_timeline.json")
            if not timeline_path.exists():
                raise FileNotFoundError("master_timeline.json no encontrado")
            
            with open(timeline_path, 'r') as f:
                data = json.load(f)
                self.master_timeline = data.get('timestamps', [])
            
            # Filtrar timestamps dentro del rango de fechas
            start_ts = int(self.start_date.timestamp())
            end_ts = int(self.end_date.timestamp())
            self.master_timeline = [ts for ts in self.master_timeline if start_ts <= ts <= end_ts]
            
            logger.info(f"📅 Timeline maestro cargado: {len(self.master_timeline)} timestamps")
            
        except Exception as e:
            logger.error(f"❌ Error cargando timeline maestro: {e}")
            raise
    
    async def load_historical_data(self, symbols: List[str], timeframe: str, 
                                 start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """
        Carga datos históricos alineados para todos los símbolos.
        
        Args:
            symbols: Lista de símbolos
            timeframe: Timeframe a cargar
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Dict con datos por símbolo
        """
        data = {}
        
        for symbol in symbols:
            try:
                symbol_data = self.db_manager.get_historical_data(
                    symbol, timeframe, start_date, end_date
                )
                data[symbol] = symbol_data
                logger.info(f"📊 {symbol} {timeframe}: {len(symbol_data)} registros cargados")
                
            except Exception as e:
                logger.error(f"❌ Error cargando datos para {symbol} {timeframe}: {e}")
                data[symbol] = []
        
        return data
    
    async def train_agent(self, symbol: str, data: List[Dict], timeframe: str) -> Dict[str, Any]:
        """
        Entrena un agente para un símbolo específico.
        
        Args:
            symbol: Símbolo a entrenar
            data: Datos históricos
            timeframe: Timeframe de los datos
            
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            if not data:
                return {
                    "status": "error",
                    "message": "No hay datos disponibles",
                    "metrics": {},
                    "trades": [],
                    "model_path": None
                }
            
            # Convertir datos a DataFrame
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp').sort_index()
            
            # Calcular indicadores técnicos
            df = self._calculate_technical_indicators(df)
            
            # Preparar datos para entrenamiento
            X, y = self._prepare_training_data(df)
            
            if len(X) == 0:
                return {
                    "status": "error",
                    "message": "Datos insuficientes para entrenamiento",
                    "metrics": {},
                    "trades": [],
                    "model_path": None
                }
            
            # Entrenar modelo
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X, y)
            
            # Simular trading
            trades = self._simulate_trading(df, model, symbol)
            
            # Calcular métricas
            metrics = self._calculate_metrics(trades, df)
            
            # Guardar modelo
            model_path = self._save_model(symbol, model)
            
            # Actualizar estrategias y runs
            await self._update_strategies_and_runs(symbol, metrics, trades)
            
            return {
                "status": "success",
                "metrics": metrics,
                "trades": trades,
                "model_path": model_path
            }
            
        except Exception as e:
            logger.error(f"❌ Error entrenando agente {symbol}: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": str(e),
                "metrics": {},
                "trades": [],
                "model_path": None
            }
    
    async def train_chronological_agent(self, symbol: str) -> Dict[str, Any]:
        """
        Entrena un agente que recorre el histórico cronológicamente,
        analizando todos los timeframes simultáneamente en cada momento
        y ejecutando trades solo en timeframes de ejecución (1m, 5m)
        
        Args:
            symbol: Símbolo a entrenar
            
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            logger.info(f"🔄 Entrenando agente cronológico para {symbol}")
            print(f"🔄 [AGENTE] {symbol} - Cargando datos cronológicos...")
            
            # Obtener timeframes de ejecución
            execution_timeframes = self.config_manager.get('symbols', {}).get('timeframes', {}).get('real_time', ['1m', '5m'])
            
            # Cargar datos de todos los timeframes
            multi_timeframe_data = {}
            for timeframe in self.timeframes:
                data = await self.load_historical_data([symbol], timeframe, self.start_date, self.end_date)
                if symbol in data and data[symbol]:
                    multi_timeframe_data[timeframe] = data[symbol]
                    print(f"  📊 {timeframe}: {len(data[symbol])} registros")
            
            if not multi_timeframe_data:
                return {
                    "status": "error",
                    "message": "No hay datos disponibles",
                    "metrics": {},
                    "trades": [],
                    "model_path": None
                }
            
            # Crear timeline cronológico unificado
            print(f"  🔧 Creando timeline cronológico unificado para {symbol}...")
            chronological_data = self._create_chronological_timeline(multi_timeframe_data)
            
            if chronological_data.empty:
                return {
                    "status": "error",
                    "message": "Datos insuficientes para timeline cronológico",
                    "metrics": {},
                    "trades": [],
                    "model_path": None
                }
            
            # Entrenar modelo con datos cronológicos
            print(f"  🚀 Entrenando modelo cronológico para {symbol}...")
            X, y = self._prepare_chronological_training_data(chronological_data)
            
            if len(X) == 0:
                return {
                    "status": "error",
                    "message": "Datos insuficientes para entrenamiento cronológico",
                    "metrics": {},
                    "trades": [],
                    "model_path": None
                }
            
            # Las características ya se guardaron en _prepare_chronological_training_data
            logger.info(f"🔧 Características de entrenamiento: {len(self.training_feature_columns)}")
            logger.info(f"🔧 Columnas de entrenamiento: {self.training_feature_columns[:5]}...")  # Primeras 5 para debug
            
            # Entrenar modelo con configuración del modo
            model_config = self.training_config.get('model_config', {})
            model = RandomForestRegressor(
                n_estimators=model_config.get('n_estimators', 50),
                max_depth=model_config.get('max_depth', 8),
                random_state=42,
                n_jobs=model_config.get('n_jobs', -1)
            )
            model.fit(X, y)
            
            # Simular trading cronológico con análisis jerárquico
            print(f"  ⚡ Simulando trading cronológico con análisis jerárquico...")
            trades = self._simulate_hierarchical_trading(chronological_data, model, symbol, execution_timeframes)
            
            # Calcular métricas
            if trades:
                metrics = self._calculate_metrics(trades, chronological_data)
                metrics['total_rewards'] = sum(t.get('reward', 0) for t in trades)
                metrics['execution_timeframes'] = execution_timeframes
                metrics['analysis_timeframes'] = list(multi_timeframe_data.keys())
                metrics['chronological_analysis'] = True
            else:
                metrics = {
                    'pnl': 0.0,
                    'win_rate': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'trade_count': 0,
                    'avg_daily_pnl': 0.0,
                    'total_rewards': 0.0,
                    'execution_timeframes': execution_timeframes,
                    'analysis_timeframes': list(multi_timeframe_data.keys()),
                    'chronological_analysis': True
                }
            
            # Guardar modelo
            model_path = self._save_model(symbol, model)
            
            # Actualizar estrategias y runs
            self._update_strategies_and_runs(symbol, metrics, trades)
            
            # Guardar metadata
            self._save_metadata(symbol, "chronological", metrics, model_path)
            
            print(f"  ✅ {symbol} completado: {len(trades)} trades, PnL: ${metrics.get('pnl', 0):.2f}")
            
            return {
                "status": "success",
                "metrics": metrics,
                "trades": trades,
                "model_path": model_path
            }
            
        except Exception as e:
            logger.error(f"❌ Error en train_chronological_agent para {symbol}: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": str(e),
                "metrics": {},
                "trades": [],
                "model_path": None
            }
    
    def _prepare_multi_timeframe_data(self, multi_timeframe_data: Dict[str, List[Dict]]) -> pd.DataFrame:
        """Prepara datos multi-timeframe combinando información de todos los timeframes"""
        try:
            # Crear DataFrame base con el timeframe más granular (1m)
            base_timeframe = '1m'
            if base_timeframe not in multi_timeframe_data:
                base_timeframe = min(multi_timeframe_data.keys())
            
            base_data = multi_timeframe_data[base_timeframe]
            df = pd.DataFrame(base_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp').sort_index()
            
            # Agregar indicadores técnicos del timeframe base
            df = self._calculate_technical_indicators(df)
            
            # Agregar prefijos para identificar el timeframe base
            for col in ['rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'volatility', 'volume_sma']:
                if col in df.columns:
                    df[f'{base_timeframe}_{col}'] = df[col]
                    df = df.drop(columns=[col])
            
            # Agregar datos de otros timeframes (resampleados al timeframe base)
            for timeframe, data in multi_timeframe_data.items():
                if timeframe == base_timeframe:
                    continue
                
                tf_df = pd.DataFrame(data)
                tf_df['timestamp'] = pd.to_datetime(tf_df['timestamp'], unit='s')
                tf_df = tf_df.set_index('timestamp').sort_index()
                
                # Calcular indicadores técnicos para este timeframe
                tf_df = self._calculate_technical_indicators(tf_df)
                
                # Resamplear al timeframe base
                tf_resampled = tf_df.resample('1T').ffill()  # Forward fill cada minuto
                
                # Agregar indicadores con prefijo del timeframe
                for col in ['rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'volatility', 'volume_sma']:
                    if col in tf_resampled.columns:
                        df[f'{timeframe}_{col}'] = tf_resampled[col]
            
            # Eliminar filas con NaN
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error preparando datos multi-timeframe: {e}")
            return pd.DataFrame()
    
    def _simulate_multi_timeframe_trading(self, exec_df: pd.DataFrame, model: RandomForestRegressor, 
                                        symbol: str, multi_timeframe_data: Dict[str, List[Dict]]) -> List[Dict]:
        """Simula trading usando información multi-timeframe pero ejecutando solo en el timeframe de ejecución"""
        try:
            trades = []
            balance = 1000.0
            position = 0.0
            position_price = 0.0
            position_type = None
            trade_count = 0
            total_rewards = 0.0
            consecutive_losses = 0
            
            # Obtener configuración de leverage
            symbol_config = self.symbol_configs.get(symbol, {})
            leverage_range = symbol_config.get('leverage_range', [1, 10])
            min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
            max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
            
            # Preparar características para predicción (incluyendo multi-timeframe)
            feature_cols = []
            for col in exec_df.columns:
                if col.startswith(('1m_', '5m_', '15m_', '1h_', '4h_', '1d_')):
                    feature_cols.append(col)
            
            for i in range(len(exec_df) - 1):
                try:
                    current_price = exec_df['close'].iloc[i]
                    next_price = exec_df['close'].iloc[i + 1]
                    price_change_pct = (next_price - current_price) / current_price
                    
                    # Preparar características multi-timeframe
                    current_features = []
                    for col in feature_cols:
                        if col in exec_df.columns:
                            try:
                                current_features.append(exec_df[col].iloc[i])
                            except (KeyError, IndexError):
                                current_features.append(0.0)
                        else:
                            current_features.append(0.0)
                    
                    if len(current_features) == 0:
                        continue
                    
                    # Predicción del modelo
                    predicted_price = model.predict([current_features])[0]
                    
                    # Calcular leverage dinámico
                    try:
                        volatility = exec_df['volatility'].iloc[i] if 'volatility' in exec_df.columns else 0.02
                    except (KeyError, IndexError):
                        volatility = 0.02
                    
                    volatility_factor = 5.0
                    calculated_leverage = 1.0 / (volatility * volatility_factor)
                    leverage = max(min_leverage, min(max_leverage, calculated_leverage))
                    
                    # Estrategia de trading con información multi-timeframe
                    if price_change_pct > 0.01 and position == 0:  # LONG
                        position = (balance * leverage) / current_price
                        position_price = current_price
                        position_type = 'long'
                        balance = balance - (position * current_price)
                        trade_count += 1
                        
                        trades.append({
                            'timestamp': exec_df.index[i],
                            'type': 'buy',
                            'side': 'long',
                            'price': current_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'predicted_price': predicted_price,
                            'trade_id': trade_count,
                            'volatility': volatility,
                            'timeframe': 'multi-timeframe'
                        })
                    
                    elif price_change_pct < -0.01 and position == 0:  # SHORT
                        position = (balance * leverage) / current_price
                        position_price = current_price
                        position_type = 'short'
                        balance = balance + (position * current_price)
                        trade_count += 1
                        
                        trades.append({
                            'timestamp': exec_df.index[i],
                            'type': 'sell',
                            'side': 'short',
                            'price': current_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'predicted_price': predicted_price,
                            'trade_id': trade_count,
                            'volatility': volatility,
                            'timeframe': 'multi-timeframe'
                        })
                    
                    elif position > 0:  # Cerrar posición
                        if position_type == 'long':
                            balance = balance + (position * next_price)
                            pnl = (position * next_price) - (position * position_price)
                        else:  # SHORT
                            balance = balance - (position * next_price)
                            pnl = (position * position_price) - (position * next_price)
                        
                        # Calcular reward del trade
                        trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                        total_rewards += trade_reward
                        
                        # Penalty por pérdidas consecutivas
                        if pnl < 0:
                            consecutive_losses += 1
                            if consecutive_losses >= 3:
                                penalty = self.rewards_config.get('risk_penalties', {}).get('consecutive_losses', -1.0)
                                total_rewards += penalty
                        else:
                            consecutive_losses = 0
                        
                        trade_duration = (exec_df.index[i + 1] - exec_df.index[i]).total_seconds() / 3600
                        price_change_trade = (next_price - position_price) / position_price
                        
                        trades.append({
                            'timestamp': exec_df.index[i + 1],
                            'type': 'close',
                            'side': position_type,
                            'price': next_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'pnl': pnl,
                            'pnl_pct': pnl / (position * position_price) * 100,
                            'trade_duration_hours': trade_duration,
                            'price_change_pct': price_change_trade * 100,
                            'trade_id': trade_count,
                            'volatility': volatility,
                            'reward': trade_reward,
                            'consecutive_losses': consecutive_losses,
                            'timeframe': 'multi-timeframe'
                        })
                        
                        position = 0
                        position_price = 0
                        position_type = None
                
                except Exception as e:
                    logger.warning(f"⚠️ Error en simulación multi-timeframe en índice {i}: {e}")
                    continue
            
            # Cerrar posición final si existe
            if position > 0:
                final_price = exec_df['close'].iloc[-1]
                if position_type == 'long':
                    balance = balance + (position * final_price)
                    pnl = (position * final_price) - (position * position_price)
                else:  # SHORT
                    balance = balance - (position * final_price)
                    pnl = (position * position_price) - (position * final_price)
                
                trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                total_rewards += trade_reward
                
                trade_duration = (exec_df.index[-1] - exec_df.index[-2]).total_seconds() / 3600
                price_change_trade = (final_price - position_price) / position_price
                
                trades.append({
                    'timestamp': exec_df.index[-1],
                    'type': 'close',
                    'side': position_type,
                    'price': final_price,
                    'amount': position,
                    'leverage': leverage,
                    'balance': balance,
                    'pnl': pnl,
                    'pnl_pct': pnl / (position * position_price) * 100,
                    'trade_duration_hours': trade_duration,
                    'price_change_pct': price_change_trade * 100,
                    'trade_id': trade_count,
                    'volatility': volatility,
                    'reward': trade_reward,
                    'timeframe': 'multi-timeframe'
                })
            
            # Agregar reward total al último trade
            if trades:
                trades[-1]['total_rewards'] = total_rewards
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error en simulación multi-timeframe: {e}")
            return []
    
    def _create_chronological_timeline(self, multi_timeframe_data: Dict[str, List[Dict]]) -> pd.DataFrame:
        """Crea un timeline cronológico unificado con todos los timeframes"""
        try:
            # Usar el timeframe más granular como base (1m)
            base_timeframe = '1m'
            if base_timeframe not in multi_timeframe_data:
                base_timeframe = min(multi_timeframe_data.keys())
            
            # Crear DataFrame base con timestamps de 1m
            base_data = multi_timeframe_data[base_timeframe]
            df = pd.DataFrame(base_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp').sort_index()
            
            # Agregar datos de otros timeframes alineados cronológicamente
            for timeframe, data in multi_timeframe_data.items():
                if timeframe == base_timeframe:
                    continue
                
                tf_df = pd.DataFrame(data)
                tf_df['timestamp'] = pd.to_datetime(tf_df['timestamp'], unit='s')
                tf_df = tf_df.set_index('timestamp').sort_index()
                
                # Calcular indicadores técnicos para este timeframe
                tf_df = self._calculate_technical_indicators(tf_df)
                
                # Alinear con el timeframe base usando forward fill
                for col in ['open', 'high', 'low', 'close', 'volume', 'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'volatility', 'volume_sma']:
                    if col in tf_df.columns:
                        # Resamplear al timeframe base y forward fill
                        resampled = tf_df[col].resample('1T').ffill()
                        df[f'{timeframe}_{col}'] = resampled
            
            # Eliminar filas con NaN
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error creando timeline cronológico: {e}")
            return pd.DataFrame()
    
    def _prepare_chronological_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepara datos de entrenamiento cronológicos"""
        try:
            # Crear características multi-timeframe
            feature_cols = []
            for col in df.columns:
                if col.startswith(('1m_', '5m_', '15m_', '1h_', '4h_', '1d_')):
                    feature_cols.append(col)
            
            if not feature_cols:
                return pd.DataFrame(), pd.Series()
            
            # Preparar características como DataFrame
            X = df[feature_cols].copy()
            
            # Crear target (precio futuro del timeframe de ejecución)
            # Usar el precio de cierre del timeframe más granular (1m)
            if '1m_close' in df.columns:
                y = df['1m_close'].shift(-1)  # Precio futuro
            else:
                y = df['close'].shift(-1)
            
            # Eliminar NaN
            valid_mask = ~(X.isnull().any(axis=1) | y.isnull())
            X = X[valid_mask]
            y = y[valid_mask]
            
            # Guardar las características exactas usadas para el entrenamiento
            self.training_feature_columns = list(X.columns)
            
            logger.info(f"🔧 Datos de entrenamiento: {len(X)} muestras, {len(X.columns)} características")
            return X, y
            
        except Exception as e:
            logger.error(f"❌ Error preparando datos cronológicos: {e}")
            return pd.DataFrame(), pd.Series()
    
    def _simulate_chronological_trading(self, df: pd.DataFrame, model: RandomForestRegressor, 
                                      symbol: str, execution_timeframes: List[str]) -> List[Dict]:
        """Simula trading cronológico analizando todos los timeframes en cada momento"""
        try:
            trades = []
            balance = 1000.0
            position = 0.0
            position_price = 0.0
            position_type = None
            trade_count = 0
            total_rewards = 0.0
            consecutive_losses = 0
            
            # Obtener configuración de leverage
            symbol_config = self.symbol_configs.get(symbol, {})
            leverage_range = symbol_config.get('leverage_range', [1, 10])
            min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
            max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
            
            # Preparar características para predicción
            feature_cols = []
            for col in df.columns:
                if col.startswith(('1m_', '5m_', '15m_', '1h_', '4h_', '1d_')):
                    feature_cols.append(col)
            
            print(f"    🔍 Analizando {len(df)} momentos cronológicos...")
            
            for i in range(len(df) - 1):
                try:
                    # Obtener datos del momento actual
                    current_timestamp = df.index[i]
                    current_price = df['1m_close'].iloc[i] if '1m_close' in df.columns else df['close'].iloc[i]
                    next_price = df['1m_close'].iloc[i + 1] if '1m_close' in df.columns else df['close'].iloc[i + 1]
                    
                    # Análisis multi-timeframe en este momento
                    analysis = self._analyze_multi_timeframe_moment(df.iloc[i])
                    
                    # Solo ejecutar trades en timeframes de ejecución
                    if self._should_execute_trade(current_timestamp, execution_timeframes):
                        # Preparar características para predicción
                        current_features = []
                        for col in feature_cols:
                            if col in df.columns:
                                try:
                                    current_features.append(df[col].iloc[i])
                                except (KeyError, IndexError):
                                    current_features.append(0.0)
                            else:
                                current_features.append(0.0)
                        
                        if len(current_features) == 0:
                            continue
                        
                        # Predicción del modelo
                        predicted_price = model.predict([current_features])[0]
                        
                        # Calcular leverage dinámico
                        volatility = analysis.get('volatility', 0.02)
                        volatility_factor = 5.0
                        calculated_leverage = 1.0 / (volatility * volatility_factor)
                        leverage = max(min_leverage, min(max_leverage, calculated_leverage))
                        
                        # Estrategia de trading basada en análisis multi-timeframe
                        price_change_pct = (next_price - current_price) / current_price
                        
                        # Detectar dirección en timeframes altos (1d, 4h)
                        high_tf_direction = analysis.get('high_tf_direction', 0)
                        # Confirmar en timeframes medios (1h, 15m)
                        medium_tf_confirmation = analysis.get('medium_tf_confirmation', 0)
                        
                        # Ejecutar trade solo si hay confirmación multi-timeframe
                        if (high_tf_direction > 0 and medium_tf_confirmation > 0 and 
                            price_change_pct > 0.01 and position == 0):  # LONG
                            
                            position = (balance * leverage) / current_price
                            position_price = current_price
                            position_type = 'long'
                            balance = balance - (position * current_price)
                            trade_count += 1
                            
                            trades.append({
                                'timestamp': current_timestamp,
                                'type': 'buy',
                                'side': 'long',
                                'price': current_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'predicted_price': predicted_price,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'high_tf_direction': high_tf_direction,
                                'medium_tf_confirmation': medium_tf_confirmation,
                                'timeframe': 'chronological'
                            })
                        
                        elif (high_tf_direction < 0 and medium_tf_confirmation < 0 and 
                              price_change_pct < -0.01 and position == 0):  # SHORT
                            
                            position = (balance * leverage) / current_price
                            position_price = current_price
                            position_type = 'short'
                            balance = balance + (position * current_price)
                            trade_count += 1
                            
                            trades.append({
                                'timestamp': current_timestamp,
                                'type': 'sell',
                                'side': 'short',
                                'price': current_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'predicted_price': predicted_price,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'high_tf_direction': high_tf_direction,
                                'medium_tf_confirmation': medium_tf_confirmation,
                                'timeframe': 'chronological'
                            })
                        
                        elif position > 0:  # Cerrar posición
                            if position_type == 'long':
                                balance = balance + (position * next_price)
                                pnl = (position * next_price) - (position * position_price)
                            else:  # SHORT
                                balance = balance - (position * next_price)
                                pnl = (position * position_price) - (position * next_price)
                            
                            # Calcular reward del trade
                            trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                            total_rewards += trade_reward
                            
                            # Penalty por pérdidas consecutivas
                            if pnl < 0:
                                consecutive_losses += 1
                                if consecutive_losses >= 3:
                                    penalty = self.rewards_config.get('risk_penalties', {}).get('consecutive_losses', -1.0)
                                    total_rewards += penalty
                            else:
                                consecutive_losses = 0
                            
                            trade_duration = (df.index[i + 1] - df.index[i]).total_seconds() / 3600
                            price_change_trade = (next_price - position_price) / position_price
                            
                            trades.append({
                                'timestamp': df.index[i + 1],
                                'type': 'close',
                                'side': position_type,
                                'price': next_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'pnl': pnl,
                                'pnl_pct': pnl / (position * position_price) * 100,
                                'trade_duration_hours': trade_duration,
                                'price_change_pct': price_change_trade * 100,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'reward': trade_reward,
                                'consecutive_losses': consecutive_losses,
                                'timeframe': 'chronological'
                            })
                            
                            position = 0
                            position_price = 0
                            position_type = None
                
                except Exception as e:
                    logger.warning(f"⚠️ Error en simulación cronológica en índice {i}: {e}")
                    continue
            
            # Cerrar posición final si existe
            if position > 0:
                final_price = df['1m_close'].iloc[-1] if '1m_close' in df.columns else df['close'].iloc[-1]
                if position_type == 'long':
                    balance = balance + (position * final_price)
                    pnl = (position * final_price) - (position * position_price)
                else:  # SHORT
                    balance = balance - (position * final_price)
                    pnl = (position * position_price) - (position * final_price)
                
                trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                total_rewards += trade_reward
                
                trade_duration = (df.index[-1] - df.index[-2]).total_seconds() / 3600
                price_change_trade = (final_price - position_price) / position_price
                
                trades.append({
                    'timestamp': df.index[-1],
                    'type': 'close',
                    'side': position_type,
                    'price': final_price,
                    'amount': position,
                    'leverage': leverage,
                    'balance': balance,
                    'pnl': pnl,
                    'pnl_pct': pnl / (position * position_price) * 100,
                    'trade_duration_hours': trade_duration,
                    'price_change_pct': price_change_trade * 100,
                    'trade_id': trade_count,
                    'volatility': volatility,
                    'reward': trade_reward,
                    'timeframe': 'chronological'
                })
            
            # Agregar reward total al último trade
            if trades:
                trades[-1]['total_rewards'] = total_rewards
            
            print(f"    ✅ {symbol}: {len(trades)} trades ejecutados cronológicamente")
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error en simulación cronológica: {e}")
            return []
    
    def _analyze_multi_timeframe_moment(self, moment_data: pd.Series) -> Dict[str, float]:
        """Analiza un momento específico usando todos los timeframes"""
        try:
            analysis = {}
            
            # Análisis de timeframes altos (1d, 4h) - Detectar direcciones
            high_tf_direction = 0.0
            if '1d_rsi' in moment_data and '4h_rsi' in moment_data:
                # Dirección basada en RSI de timeframes altos
                rsi_1d = moment_data.get('1d_rsi', 50)
                rsi_4h = moment_data.get('4h_rsi', 50)
                high_tf_direction = (rsi_1d - 50) + (rsi_4h - 50)
            
            # Análisis de timeframes medios (1h, 15m) - Confirmar direcciones
            medium_tf_confirmation = 0.0
            if '1h_rsi' in moment_data and '15m_rsi' in moment_data:
                rsi_1h = moment_data.get('1h_rsi', 50)
                rsi_15m = moment_data.get('15m_rsi', 50)
                medium_tf_confirmation = (rsi_1h - 50) + (rsi_15m - 50)
            
            # Volatilidad promedio
            volatility = 0.02
            volatility_cols = [col for col in moment_data.index if 'volatility' in col]
            if volatility_cols:
                volatility = np.mean([moment_data[col] for col in volatility_cols if not pd.isna(moment_data[col])])
            
            analysis.update({
                'high_tf_direction': high_tf_direction,
                'medium_tf_confirmation': medium_tf_confirmation,
                'volatility': volatility
            })
            
            return analysis
            
        except Exception as e:
            logger.warning(f"⚠️ Error analizando momento multi-timeframe: {e}")
            return {'high_tf_direction': 0.0, 'medium_tf_confirmation': 0.0, 'volatility': 0.02}
    
    def _should_execute_trade(self, timestamp: pd.Timestamp, execution_timeframes: List[str]) -> bool:
        """Determina si se debe ejecutar un trade en este timestamp"""
        try:
            # Para timeframes de ejecución (1m, 5m), ejecutar en cada momento
            # En un sistema real, esto se filtraría por el timeframe específico
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Error determinando ejecución de trade: {e}")
            return True
    
    def _simulate_hierarchical_trading(self, df: pd.DataFrame, model: RandomForestRegressor, 
                                     symbol: str, execution_timeframes: List[str]) -> List[Dict]:
        """Simula trading con análisis jerárquico de timeframes"""
        try:
            trades = []
            balance = 1000.0
            position = 0.0
            position_price = 0.0
            position_type = None
            trade_count = 0
            total_rewards = 0.0
            consecutive_losses = 0
            
            # Obtener configuración de leverage
            symbol_config = self.symbol_configs.get(symbol, {})
            leverage_range = symbol_config.get('leverage_range', [1, 10])
            min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
            max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
            
            # Configuración de análisis jerárquico
            analysis_levels = self.hierarchical_config.get('analysis_levels', {})
            decision_logic = self.hierarchical_config.get('decision_logic', {})
            
            # Aplicar muestreo según el modo de entrenamiento
            sampling_interval = self.training_config.get('sampling_interval', 1)
            if sampling_interval > 1:
                df = df.iloc[::sampling_interval]
            
            print(f"    🔍 Analizando {len(df)} momentos con análisis jerárquico...")
            
            for i in range(len(df) - 1):
                try:
                    # Obtener datos del momento actual
                    current_timestamp = df.index[i]
                    current_price = df['1m_close'].iloc[i] if '1m_close' in df.columns else df['close'].iloc[i]
                    next_price = df['1m_close'].iloc[i + 1] if '1m_close' in df.columns else df['close'].iloc[i + 1]
                    
                    # Análisis jerárquico completo
                    hierarchical_analysis = self._perform_hierarchical_analysis(df.iloc[i], analysis_levels)
                    
                    # Solo ejecutar trades en timeframes de ejecución
                    if self._should_execute_trade(current_timestamp, execution_timeframes):
                        # Preparar características para predicción usando las mismas del entrenamiento
                        try:
                            # Usar las características exactas del entrenamiento
                            if not hasattr(self, 'training_feature_columns') or not self.training_feature_columns:
                                continue
                            
                            # Preparar características en el mismo orden que el entrenamiento
                            current_features = []
                            for col in self.training_feature_columns:
                                if col in df.columns:
                                    try:
                                        current_features.append(df[col].iloc[i])
                                    except (KeyError, IndexError):
                                        current_features.append(0.0)
                                else:
                                    current_features.append(0.0)
                            
                            if len(current_features) != len(self.training_feature_columns):
                                logger.warning(f"⚠️ Características inconsistentes: {len(current_features)} vs {len(self.training_feature_columns)}")
                                continue
                            
                            # Predicción del modelo
                            predicted_price = model.predict([current_features])[0]
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error preparando características en índice {i}: {e}")
                            continue
                        
                        # Calcular leverage dinámico
                        volatility = hierarchical_analysis.get('volatility', 0.02)
                        volatility_factor = 5.0
                        calculated_leverage = 1.0 / (volatility * volatility_factor)
                        leverage = max(min_leverage, min(max_leverage, calculated_leverage))
                        
                        # Decisión jerárquica de trading
                        price_change_pct = (next_price - current_price) / current_price
                        
                        # Obtener señales jerárquicas
                        strategic_signal = hierarchical_analysis.get('strategic_signal', 0)
                        tactical_signal = hierarchical_analysis.get('tactical_signal', 0)
                        execution_signal = hierarchical_analysis.get('execution_signal', 0)
                        
                        # Lógica de decisión jerárquica
                        should_buy = self._evaluate_hierarchical_decision(
                            strategic_signal, tactical_signal, execution_signal, 
                            price_change_pct, 'buy', decision_logic
                        )
                        
                        should_sell = self._evaluate_hierarchical_decision(
                            strategic_signal, tactical_signal, execution_signal, 
                            price_change_pct, 'sell', decision_logic
                        )
                        
                        # Ejecutar trades basados en análisis jerárquico
                        if should_buy and position == 0:  # LONG
                            position = (balance * leverage) / current_price
                            position_price = current_price
                            position_type = 'long'
                            balance = balance - (position * current_price)
                            trade_count += 1
                            
                            trades.append({
                                'timestamp': current_timestamp,
                                'type': 'buy',
                                'side': 'long',
                                'price': current_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'predicted_price': predicted_price,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'strategic_signal': strategic_signal,
                                'tactical_signal': tactical_signal,
                                'execution_signal': execution_signal,
                                'timeframe': 'hierarchical'
                            })
                        
                        elif should_sell and position == 0:  # SHORT
                            position = (balance * leverage) / current_price
                            position_price = current_price
                            position_type = 'short'
                            balance = balance + (position * current_price)
                            trade_count += 1
                            
                            trades.append({
                                'timestamp': current_timestamp,
                                'type': 'sell',
                                'side': 'short',
                                'price': current_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'predicted_price': predicted_price,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'strategic_signal': strategic_signal,
                                'tactical_signal': tactical_signal,
                                'execution_signal': execution_signal,
                                'timeframe': 'hierarchical'
                            })
                        
                        elif position > 0:  # Cerrar posición
                            if position_type == 'long':
                                balance = balance + (position * next_price)
                                pnl = (position * next_price) - (position * position_price)
                            else:  # SHORT
                                balance = balance - (position * next_price)
                                pnl = (position * position_price) - (position * next_price)
                            
                            # Calcular reward del trade
                            trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                            total_rewards += trade_reward
                            
                            # Penalty por pérdidas consecutivas
                            if pnl < 0:
                                consecutive_losses += 1
                                if consecutive_losses >= 3:
                                    penalty = self.rewards_config.get('risk_penalties', {}).get('consecutive_losses', -1.0)
                                    total_rewards += penalty
                            else:
                                consecutive_losses = 0
                            
                            trade_duration = (df.index[i + 1] - df.index[i]).total_seconds() / 3600
                            price_change_trade = (next_price - position_price) / position_price
                            
                            trades.append({
                                'timestamp': df.index[i + 1],
                                'type': 'close',
                                'side': position_type,
                                'price': next_price,
                                'amount': position,
                                'leverage': leverage,
                                'balance': balance,
                                'pnl': pnl,
                                'pnl_pct': pnl / (position * position_price) * 100,
                                'trade_duration_hours': trade_duration,
                                'price_change_pct': price_change_trade * 100,
                                'trade_id': trade_count,
                                'volatility': volatility,
                                'reward': trade_reward,
                                'consecutive_losses': consecutive_losses,
                                'timeframe': 'hierarchical'
                            })
                            
                            position = 0
                            position_price = 0
                            position_type = None
                
                except Exception as e:
                    logger.warning(f"⚠️ Error en simulación jerárquica en índice {i}: {e}")
                    continue
            
            # Cerrar posición final si existe
            if position > 0:
                final_price = df['1m_close'].iloc[-1] if '1m_close' in df.columns else df['close'].iloc[-1]
                if position_type == 'long':
                    balance = balance + (position * final_price)
                    pnl = (position * final_price) - (position * position_price)
                else:  # SHORT
                    balance = balance - (position * final_price)
                    pnl = (position * position_price) - (position * final_price)
                
                trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                total_rewards += trade_reward
                
                trade_duration = (df.index[-1] - df.index[-2]).total_seconds() / 3600
                price_change_trade = (final_price - position_price) / position_price
                
                trades.append({
                    'timestamp': df.index[-1],
                    'type': 'close',
                    'side': position_type,
                    'price': final_price,
                    'amount': position,
                    'leverage': leverage,
                    'balance': balance,
                    'pnl': pnl,
                    'pnl_pct': pnl / (position * position_price) * 100,
                    'trade_duration_hours': trade_duration,
                    'price_change_pct': price_change_trade * 100,
                    'trade_id': trade_count,
                    'volatility': volatility,
                    'reward': trade_reward,
                    'timeframe': 'hierarchical'
                })
            
            # Agregar reward total al último trade
            if trades:
                trades[-1]['total_rewards'] = total_rewards
            
            print(f"    ✅ {symbol}: {len(trades)} trades ejecutados con análisis jerárquico")
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error en simulación jerárquica: {e}")
            return []
    
    def _perform_hierarchical_analysis(self, moment_data: pd.Series, analysis_levels: Dict) -> Dict[str, float]:
        """Realiza análisis jerárquico completo de un momento"""
        try:
            analysis = {}
            
            # Análisis estratégico (1d, 4h)
            strategic_level = analysis_levels.get('strategic', {})
            strategic_timeframes = strategic_level.get('timeframes', ['1d', '4h'])
            strategic_weight = strategic_level.get('weight', 0.4)
            
            strategic_signal = 0.0
            for tf in strategic_timeframes:
                rsi_col = f'{tf}_rsi'
                if rsi_col in moment_data:
                    rsi_value = moment_data[rsi_col]
                    if not pd.isna(rsi_value):
                        strategic_signal += (rsi_value - 50) / 50  # Normalizar RSI
            
            strategic_signal = strategic_signal / len(strategic_timeframes) if strategic_timeframes else 0
            analysis['strategic_signal'] = strategic_signal * strategic_weight
            
            # Análisis táctico (1h, 15m)
            tactical_level = analysis_levels.get('tactical', {})
            tactical_timeframes = tactical_level.get('timeframes', ['1h', '15m'])
            tactical_weight = tactical_level.get('weight', 0.3)
            
            tactical_signal = 0.0
            for tf in tactical_timeframes:
                rsi_col = f'{tf}_rsi'
                if rsi_col in moment_data:
                    rsi_value = moment_data[rsi_col]
                    if not pd.isna(rsi_value):
                        tactical_signal += (rsi_value - 50) / 50
            
            tactical_signal = tactical_signal / len(tactical_timeframes) if tactical_timeframes else 0
            analysis['tactical_signal'] = tactical_signal * tactical_weight
            
            # Análisis de ejecución (5m, 1m)
            execution_level = analysis_levels.get('execution', {})
            execution_timeframes = execution_level.get('timeframes', ['5m', '1m'])
            execution_weight = execution_level.get('weight', 0.3)
            
            execution_signal = 0.0
            for tf in execution_timeframes:
                rsi_col = f'{tf}_rsi'
                if rsi_col in moment_data:
                    rsi_value = moment_data[rsi_col]
                    if not pd.isna(rsi_value):
                        execution_signal += (rsi_value - 50) / 50
            
            execution_signal = execution_signal / len(execution_timeframes) if execution_timeframes else 0
            analysis['execution_signal'] = execution_signal * execution_weight
            
            # Volatilidad promedio
            volatility = 0.02
            volatility_cols = [col for col in moment_data.index if 'volatility' in col]
            if volatility_cols:
                volatility_values = [moment_data[col] for col in volatility_cols if not pd.isna(moment_data[col])]
                if volatility_values:
                    volatility = np.mean(volatility_values)
            
            analysis['volatility'] = volatility
            
            return analysis
            
        except Exception as e:
            logger.warning(f"⚠️ Error en análisis jerárquico: {e}")
            return {'strategic_signal': 0.0, 'tactical_signal': 0.0, 'execution_signal': 0.0, 'volatility': 0.02}
    
    def _evaluate_hierarchical_decision(self, strategic_signal: float, tactical_signal: float, 
                                      execution_signal: float, price_change_pct: float, 
                                      action: str, decision_logic: Dict) -> bool:
        """Evalúa si se debe ejecutar una acción basada en análisis jerárquico"""
        try:
            # Obtener umbrales de decisión
            strategic_config = decision_logic.get('strategic_direction', {})
            tactical_config = decision_logic.get('tactical_confirmation', {})
            execution_config = decision_logic.get('execution_conditions', {})
            
            bullish_threshold = strategic_config.get('bullish_threshold', 0.2)
            bearish_threshold = strategic_config.get('bearish_threshold', -0.2)
            required_agreement = tactical_config.get('required_agreement', 0.6)
            min_volatility = execution_config.get('min_volatility', 0.01)
            max_volatility = execution_config.get('max_volatility', 0.05)
            
            # Evaluar condiciones jerárquicas
            if action == 'buy':
                # Debe haber señal alcista en estratégico
                strategic_bullish = strategic_signal > bullish_threshold
                # Debe haber confirmación táctica
                tactical_confirm = tactical_signal > 0
                # Debe haber señal de ejecución
                execution_confirm = execution_signal > 0
                # Debe haber movimiento de precio positivo
                price_confirm = price_change_pct > 0.01
                
                return (strategic_bullish and tactical_confirm and 
                       execution_confirm and price_confirm)
            
            elif action == 'sell':
                # Debe haber señal bajista en estratégico
                strategic_bearish = strategic_signal < bearish_threshold
                # Debe haber confirmación táctica
                tactical_confirm = tactical_signal < 0
                # Debe haber señal de ejecución
                execution_confirm = execution_signal < 0
                # Debe haber movimiento de precio negativo
                price_confirm = price_change_pct < -0.01
                
                return (strategic_bearish and tactical_confirm and 
                       execution_confirm and price_confirm)
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error evaluando decisión jerárquica: {e}")
            return False
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Obtiene las columnas de características según la configuración"""
        try:
            # Si tenemos características guardadas del entrenamiento, usarlas
            if hasattr(self, 'training_feature_columns') and self.training_feature_columns:
                logger.info(f"🔧 Usando {len(self.training_feature_columns)} características guardadas del entrenamiento")
                return self.training_feature_columns
            
            # Si no, usar todas las columnas numéricas del DataFrame
            feature_cols = []
            for col in df.columns:
                if col not in ['timestamp', 'created_at']:  # Excluir columnas no numéricas
                    if df[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                        feature_cols.append(col)
            
            logger.info(f"🔧 Usando {len(feature_cols)} características para entrenamiento/predicción")
            return feature_cols
            
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo columnas de características: {e}")
            return []
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos para el DataFrame"""
        try:
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], 14)
            
            # SMA
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
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
            df['volatility'] = df['close'].pct_change().rolling(window=20).std()
            
            # Volumen
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            
            return df.dropna()
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores técnicos: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula el RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"❌ Error calculando RSI: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara datos para entrenamiento del modelo"""
        try:
            # Seleccionar características
            feature_cols = [
                'open', 'high', 'low', 'close', 'volume',
                'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal',
                'bb_upper', 'bb_lower', 'volatility', 'volume_sma'
            ]
            
            # Filtrar columnas disponibles
            available_cols = [col for col in feature_cols if col in df.columns]
            X = df[available_cols].values
            
            # Target: precio futuro (1 período adelante)
            y = df['close'].shift(-1).dropna().values
            
            # Ajustar X para que coincida con y
            X = X[:-1]
            
            # Eliminar NaN
            mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X = X[mask]
            y = y[mask]
            
            return X, y
            
        except Exception as e:
            logger.error(f"❌ Error preparando datos de entrenamiento: {e}")
            return np.array([]), np.array([])
    
    def _simulate_trading(self, df: pd.DataFrame, model: RandomForestRegressor, symbol: str = "BTCUSDT") -> List[Dict]:
        """Simula trading usando el modelo entrenado con métricas avanzadas y sistema de rewards"""
        try:
            trades = []
            balance = 1000.0  # Balance inicial
            position = 0.0
            position_price = 0.0
            position_type = None  # 'long' o 'short'
            trade_count = 0
            total_rewards = 0.0  # Sistema de rewards
            consecutive_losses = 0  # Para penalties de pérdidas consecutivas
            
            # Obtener configuración de leverage para el símbolo
            symbol_config = self.symbol_configs.get(symbol, {})
            leverage_range = symbol_config.get('leverage_range', [1, 10])  # Default: 1x a 10x
            min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
            max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
            
            # Preparar características para predicción
            feature_cols = [
                'open', 'high', 'low', 'close', 'volume',
                'rsi', 'sma_20', 'sma_50', 'macd', 'macd_signal',
                'bb_upper', 'bb_lower', 'volatility', 'volume_sma'
            ]
            available_cols = [col for col in feature_cols if col in df.columns]
            
            for i in range(20, len(df) - 1):  # Empezar después de los indicadores
                try:
                    # Obtener características actuales de forma segura
                    try:
                        feature_values = []
                        for col in available_cols:
                            if col in df.columns:
                                feature_values.append(df[col].iloc[i])
                            else:
                                feature_values.append(0.0)
                        current_features = np.array(feature_values).reshape(1, -1)
                    except (KeyError, IndexError) as e:
                        logger.warning(f"⚠️ Error accediendo a características en índice {i}: {e}")
                        continue
                    
                    # Predecir precio futuro
                    predicted_price = model.predict(current_features)[0]
                    current_price = df['close'].iloc[i]
                    next_price = df['close'].iloc[i + 1]
                    
                    # Calcular cambio de precio predicho
                    price_change_pct = (predicted_price - current_price) / current_price
                    
                    # Calcular leverage dinámico basado en volatilidad y configuración
                    try:
                        volatility = df['volatility'].iloc[i] if 'volatility' in df.columns else 0.02
                    except (KeyError, IndexError):
                        volatility = 0.02
                    
                    # Leverage dinámico: más volatilidad = menos leverage
                    # Fórmula: leverage = max(min_leverage, min(max_leverage, 1 / (volatility * factor)))
                    volatility_factor = 5.0  # Factor de ajuste (ajustable)
                    calculated_leverage = 1.0 / (volatility * volatility_factor)
                    leverage = max(min_leverage, min(max_leverage, calculated_leverage))
                    
                    # Estrategia mejorada con long/short
                    if price_change_pct > 0.01 and position == 0:  # Señal de compra (LONG)
                        position = (balance * leverage) / current_price
                        position_price = current_price
                        position_type = 'long'
                        balance = balance - (position * current_price)  # Balance disponible
                        trade_count += 1
                        
                        trades.append({
                            'timestamp': df.index[i],
                            'type': 'buy',
                            'side': 'long',
                            'price': current_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'predicted_price': predicted_price,
                            'trade_id': trade_count,
                            'volatility': volatility
                        })
                    
                    elif price_change_pct < -0.01 and position == 0:  # Señal de venta (SHORT)
                        position = (balance * leverage) / current_price
                        position_price = current_price
                        position_type = 'short'
                        balance = balance + (position * current_price)  # Balance disponible
                        trade_count += 1
                        
                        trades.append({
                            'timestamp': df.index[i],
                            'type': 'sell',
                            'side': 'short',
                            'price': current_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'predicted_price': predicted_price,
                            'trade_id': trade_count,
                            'volatility': volatility
                        })
                    
                    elif position > 0:  # Cerrar posición existente
                        if position_type == 'long':
                            # Cerrar LONG
                            balance = balance + (position * next_price)
                            pnl = (position * next_price) - (position * position_price)
                        else:  # Cerrar SHORT
                            balance = balance - (position * next_price)
                            pnl = (position * position_price) - (position * next_price)
                        
                        # Calcular métricas del trade
                        trade_duration = (df.index[i + 1] - df.index[i]).total_seconds() / 3600  # horas
                        price_change_trade = (next_price - position_price) / position_price
                        
                        # Calcular reward del trade
                        trade_reward = self._calculate_trade_reward(pnl, position_type, confidence=0.5)
                        total_rewards += trade_reward
                        
                        # Penalty por pérdidas consecutivas
                        if pnl < 0:
                            consecutive_losses += 1
                            if consecutive_losses >= 3:  # 3 pérdidas consecutivas
                                penalty = self.rewards_config.get('risk_penalties', {}).get('consecutive_losses', -1.0)
                                total_rewards += penalty
                        else:
                            consecutive_losses = 0
                        
                        trades.append({
                            'timestamp': df.index[i + 1],
                            'type': 'close',
                            'side': position_type,
                            'price': next_price,
                            'amount': position,
                            'leverage': leverage,
                            'balance': balance,
                            'pnl': pnl,
                            'pnl_pct': pnl / (position * position_price) * 100,
                            'trade_duration_hours': trade_duration,
                            'price_change_pct': price_change_trade * 100,
                            'trade_id': trade_count,
                            'volatility': volatility,
                            'reward': trade_reward,
                            'consecutive_losses': consecutive_losses
                        })
                        
                        position = 0
                        position_price = 0
                        position_type = None
                
                except Exception as e:
                    logger.warning(f"⚠️ Error en simulación de trading en índice {i}: {e}")
                    continue
            
            # Cerrar posición final si existe
            if position > 0:
                final_price = df['close'].iloc[-1]
                if position_type == 'long':
                    balance = balance + (position * final_price)
                    pnl = (position * final_price) - (position * position_price)
                else:  # SHORT
                    balance = balance - (position * final_price)
                    pnl = (position * position_price) - (position * final_price)
                
                trade_duration = (df.index[-1] - df.index[-2]).total_seconds() / 3600
                price_change_trade = (final_price - position_price) / position_price
                
                trades.append({
                    'timestamp': df.index[-1],
                    'type': 'close',
                    'side': position_type,
                    'price': final_price,
                    'amount': position,
                    'leverage': leverage,
                    'balance': balance,
                    'pnl': pnl,
                    'pnl_pct': pnl / (position * position_price) * 100,
                    'trade_duration_hours': trade_duration,
                    'price_change_pct': price_change_trade * 100,
                    'trade_id': trade_count,
                    'volatility': volatility
                })
            
            # Calcular achievement rewards al final
            if trades:
                closed_trades = [t for t in trades if t.get('type') == 'close']
                if closed_trades:
                    total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
                    win_rate = len([t for t in closed_trades if t.get('pnl', 0) > 0]) / len(closed_trades)
                    achievement_reward = self._calculate_achievement_rewards(balance, win_rate, total_pnl)
                    total_rewards += achievement_reward
                    
                    # Agregar reward total al último trade
                    if trades:
                        trades[-1]['total_rewards'] = total_rewards
                        trades[-1]['achievement_reward'] = achievement_reward
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error en simulación de trading: {e}")
            return []
    
    def _calculate_metrics(self, trades: List[Dict], df: pd.DataFrame) -> Dict[str, float]:
        """Calcula métricas avanzadas del agente"""
        try:
            if not trades:
                return {
                    'pnl': 0.0,
                    'win_rate': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'trade_count': 0,
                    'avg_daily_pnl': 0.0,
                    'long_trades': 0,
                    'short_trades': 0,
                    'long_pnl': 0.0,
                    'short_pnl': 0.0,
                    'avg_leverage': 0.0,
                    'max_leverage': 0.0,
                    'avg_trade_duration': 0.0,
                    'profit_factor': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'largest_win': 0.0,
                    'largest_loss': 0.0,
                    'consecutive_wins': 0,
                    'consecutive_losses': 0,
                    'volatility_avg': 0.0
                }
            
            # Filtrar trades cerrados
            closed_trades = [trade for trade in trades if trade.get('type') == 'close']
            
            if not closed_trades:
                return {
                    'pnl': 0.0,
                    'win_rate': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'trade_count': 0,
                    'avg_daily_pnl': 0.0,
                    'long_trades': 0,
                    'short_trades': 0,
                    'long_pnl': 0.0,
                    'short_pnl': 0.0,
                    'avg_leverage': 0.0,
                    'max_leverage': 0.0,
                    'avg_trade_duration': 0.0,
                    'profit_factor': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'largest_win': 0.0,
                    'largest_loss': 0.0,
                    'consecutive_wins': 0,
                    'consecutive_losses': 0,
                    'volatility_avg': 0.0
                }
            
            # Métricas básicas
            total_pnl = sum(trade.get('pnl', 0) for trade in closed_trades)
            profitable_trades = [trade for trade in closed_trades if trade.get('pnl', 0) > 0]
            losing_trades = [trade for trade in closed_trades if trade.get('pnl', 0) < 0]
            win_rate = len(profitable_trades) / len(closed_trades) if closed_trades else 0
            
            # Trades por tipo
            long_trades = [trade for trade in closed_trades if trade.get('side') == 'long']
            short_trades = [trade for trade in closed_trades if trade.get('side') == 'short']
            long_pnl = sum(trade.get('pnl', 0) for trade in long_trades)
            short_pnl = sum(trade.get('pnl', 0) for trade in short_trades)
            
            # Leverage
            leverages = [trade.get('leverage', 1.0) for trade in closed_trades]
            avg_leverage = np.mean(leverages) if leverages else 0.0
            max_leverage = np.max(leverages) if leverages else 0.0
            
            # Duración de trades
            durations = [trade.get('trade_duration_hours', 0) for trade in closed_trades]
            avg_trade_duration = np.mean(durations) if durations else 0.0
            
            # Profit Factor
            total_wins = sum(trade.get('pnl', 0) for trade in profitable_trades)
            total_losses = abs(sum(trade.get('pnl', 0) for trade in losing_trades))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
            
            # Ganancia/pérdida promedio
            avg_win = np.mean([trade.get('pnl', 0) for trade in profitable_trades]) if profitable_trades else 0.0
            avg_loss = np.mean([trade.get('pnl', 0) for trade in losing_trades]) if losing_trades else 0.0
            
            # Mayor ganancia/pérdida
            largest_win = max([trade.get('pnl', 0) for trade in profitable_trades]) if profitable_trades else 0.0
            largest_loss = min([trade.get('pnl', 0) for trade in losing_trades]) if losing_trades else 0.0
            
            # Consecutivos
            consecutive_wins = self._calculate_consecutive_wins(closed_trades)
            consecutive_losses = self._calculate_consecutive_losses(closed_trades)
            
            # Volatilidad promedio
            volatilities = [trade.get('volatility', 0) for trade in closed_trades]
            volatility_avg = np.mean(volatilities) if volatilities else 0.0
            
            # Drawdown
            balances = [trade.get('balance', 1000) for trade in trades]
            max_drawdown = self._calculate_max_drawdown(balances)
            
            # Sharpe ratio
            returns = [trade.get('pnl', 0) for trade in closed_trades]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            
            # PnL diario promedio
            if df is not None and len(df) > 0:
                days = (df.index[-1] - df.index[0]).days
                avg_daily_pnl = total_pnl / days if days > 0 else 0
            else:
                avg_daily_pnl = 0
            
            return {
                'pnl': total_pnl,
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'trade_count': len(closed_trades),
                'avg_daily_pnl': avg_daily_pnl,
                'long_trades': len(long_trades),
                'short_trades': len(short_trades),
                'long_pnl': long_pnl,
                'short_pnl': short_pnl,
                'avg_leverage': avg_leverage,
                'max_leverage': max_leverage,
                'avg_trade_duration': avg_trade_duration,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'consecutive_wins': consecutive_wins,
                'consecutive_losses': consecutive_losses,
                'volatility_avg': volatility_avg,
                'total_rewards': total_rewards  # Agregar rewards totales
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando métricas: {e}")
            return {
                'pnl': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'trade_count': 0,
                'avg_daily_pnl': 0.0,
                'long_trades': 0,
                'short_trades': 0,
                'long_pnl': 0.0,
                'short_pnl': 0.0,
                'avg_leverage': 0.0,
                'max_leverage': 0.0,
                'avg_trade_duration': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'volatility_avg': 0.0
            }
    
    def _calculate_consecutive_wins(self, trades: List[Dict]) -> int:
        """Calcula el máximo número de ganancias consecutivas"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade.get('pnl', 0) > 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_consecutive_losses(self, trades: List[Dict]) -> int:
        """Calcula el máximo número de pérdidas consecutivas"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade.get('pnl', 0) < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_max_drawdown(self, balances: List[float]) -> float:
        """Calcula el máximo drawdown"""
        if not balances:
            return 0.0
        
        peak = balances[0]
        max_drawdown = 0.0
        
        for balance in balances:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calcula el Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Asumiendo risk-free rate = 0
        return mean_return / std_return
    
    def _calculate_trade_reward(self, trade_pnl: float, trade_type: str, confidence: float = 0.5) -> float:
        """Calcula el reward de un trade individual basado en rewards.yaml"""
        try:
            rewards = self.rewards_config.get('profit_rewards', {})
            penalties = self.rewards_config.get('risk_penalties', {})
            ml_rewards = self.rewards_config.get('ml_rewards', {})
            
            reward = 0.0
            
            # Rewards por profit
            if trade_pnl > 0:
                if trade_pnl < 10:
                    reward += rewards.get('small_profit', 1.0)
                elif trade_pnl < 50:
                    reward += rewards.get('medium_profit', 2.0)
                else:
                    reward += rewards.get('large_profit', 3.0)
                
                # ML rewards por predicción correcta
                if confidence > 0.7:
                    reward += ml_rewards.get('high_confidence_correct', 2.0)
                else:
                    reward += ml_rewards.get('correct_prediction', 1.0)
            else:
                # Penalties por pérdidas
                if trade_pnl < -50:
                    reward += penalties.get('large_loss', -2.0)
                else:
                    reward += penalties.get('stop_loss', -0.5)
                
                # ML penalty por predicción incorrecta
                reward += ml_rewards.get('wrong_prediction', -0.5)
            
            return reward
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando reward: {e}")
            return 0.0
    
    def _calculate_achievement_rewards(self, balance: float, win_rate: float, total_pnl: float) -> float:
        """Calcula rewards basados en logros y objetivos"""
        try:
            achievement_rewards = self.rewards_config.get('achievement_rewards', {})
            objective_rewards = self.rewards_config.get('objective_based_rewards', {})
            training_config = self.training_config.get('financial_targets', {})
            
            reward = 0.0
            
            # Rewards por milestones de balance
            target_balance = training_config.get('balance', {}).get('target', 100000.0)
            initial_balance = training_config.get('balance', {}).get('initial', 1000.0)
            
            # ROI progress reward
            roi_progress = (balance - initial_balance) / (target_balance - initial_balance)
            roi_multiplier = objective_rewards.get('roi_progress', {}).get('multiplier', 0.1)
            reward += roi_progress * roi_multiplier
            
            # Win rate progress reward
            target_winrate = training_config.get('performance_targets', {}).get('win_rate', 0.6)
            winrate_progress = win_rate / target_winrate
            bonus_threshold = objective_rewards.get('winrate_progress', {}).get('bonus_threshold_pct', 90.0) / 100.0
            
            if winrate_progress >= bonus_threshold:
                bonus_multiplier = objective_rewards.get('winrate_progress', {}).get('bonus_multiplier', 2.0)
                reward += winrate_progress * bonus_multiplier
            else:
                reward += winrate_progress
            
            # Achievement rewards
            if balance >= target_balance * 0.1:  # 10% del target
                reward += achievement_rewards.get('milestone_reached', 5.0)
            
            if win_rate >= target_winrate:
                reward += achievement_rewards.get('target_winrate_reached', 3.0)
            
            if total_pnl >= (target_balance - initial_balance) * 0.5:  # 50% del ROI target
                reward += achievement_rewards.get('target_roi_reached', 10.0)
            
            return reward
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando achievement rewards: {e}")
            return 0.0
    
    def _save_model(self, symbol: str, model: RandomForestRegressor) -> str:
        """Guarda el modelo entrenado"""
        try:
            model_path = self.agents_dir / symbol / f"model_{self.run_id}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"💾 Modelo guardado: {model_path}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"❌ Error guardando modelo para {symbol}: {e}")
            return ""
    
    def _save_metadata(self, symbol: str, timeframe: str, metrics: Dict, model_path: str) -> None:
        """Guarda metadata del entrenamiento"""
        try:
            agent_dir = self.agents_dir / symbol
            metadata_file = agent_dir / "metadata" / f"run_{self.run_id}.json"
            
            metadata = {
                "run_id": self.run_id,
                "timestamp": datetime.now().isoformat(),
                "timeframe": timeframe,
                "metrics": metrics,
                "model_path": model_path,
                "training_params": {
                    "model_type": "RandomForestRegressor",
                    "n_estimators": 100,
                    "max_depth": 10
                }
            }
            
            self._save_json_file(metadata_file, metadata)
            
        except Exception as e:
            logger.error(f"❌ Error guardando metadata para {symbol}: {e}")
    
    async def _update_strategies_and_runs(self, symbol: str, metrics: Dict, trades: List[Dict]) -> None:
        """Actualiza mejores/peores estrategias y runs"""
        try:
            agent_dir = self.agents_dir / symbol
            
            # Actualizar estrategias
            strategies_file = agent_dir / "strategies.json"
            strategies = self._load_json_file(strategies_file, {"best": [], "worst": []})
            
            strategy_data = {
                "run_id": self.run_id,
                "pnl": metrics.get('pnl', 0),
                "win_rate": metrics.get('win_rate', 0),
                "trade_count": metrics.get('trade_count', 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Actualizar mejores estrategias
            strategies["best"].append(strategy_data)
            strategies["best"].sort(key=lambda x: x.get('pnl', 0), reverse=True)
            strategies["best"] = strategies["best"][:10]  # Mantener top 10
            
            # Actualizar peores estrategias
            strategies["worst"].append(strategy_data)
            strategies["worst"].sort(key=lambda x: x.get('pnl', 0))
            strategies["worst"] = strategies["worst"][:10]  # Mantener top 10
            
            self._save_json_file(strategies_file, strategies)
            
            # Actualizar run history
            run_history_file = agent_dir / "run_history.json"
            run_history = self._load_json_file(run_history_file, {"runs": []})
            
            run_data = {
                "run_id": self.run_id,
                "metrics": metrics,
                "trade_count": len(trades),
                "timestamp": datetime.now().isoformat()
            }
            
            run_history["runs"].append(run_data)
            run_history["runs"].sort(key=lambda x: x.get('metrics', {}).get('pnl', 0), reverse=True)
            run_history["runs"] = run_history["runs"][:10]  # Mantener top 10
            
            self._save_json_file(run_history_file, run_history)
            
            # Guardar metadata
            metadata_file = agent_dir / "metadata" / f"run_{self.run_id}.json"
            metadata = {
                "run_id": self.run_id,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "trades": trades,
                "training_params": {
                    "model_type": "RandomForestRegressor",
                    "n_estimators": 100,
                    "max_depth": 10
                }
            }
            
            self._save_json_file(metadata_file, metadata)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estrategias y runs para {symbol}: {e}")
    
    def _load_json_file(self, file_path: Path, default: Any = None) -> Any:
        """Carga un archivo JSON con valor por defecto"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default or {}
        except Exception as e:
            logger.warning(f"⚠️ Error cargando {file_path}: {e}")
            return default or {}
    
    def _save_json_file(self, file_path: Path, data: Any) -> None:
        """Guarda datos en un archivo JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error guardando {file_path}: {e}")
    
    async def _update_progress(self, progress: int, current_symbol: str = "", status: str = "") -> None:
        """Actualiza el progreso en el archivo temporal"""
        try:
            progress_data = {
                "progress": progress,
                "current_symbol": current_symbol,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            
            progress_file = self.tmp_dir / f"{self.progress_id}.json"
            self._save_json_file(progress_file, progress_data)
            
        except Exception as e:
            logger.warning(f"⚠️ Error actualizando progreso: {e}")
    
    async def execute(self) -> Dict[str, Any]:
        """
        Método principal para ejecutar el entrenamiento.
        
        Returns:
            Dict con resultados del entrenamiento
        """
        try:
            logger.info("🚀 Iniciando entrenamiento histórico paralelo")
            print("🚀 INICIANDO ENTRENAMIENTO HISTÓRICO PARALELO")
            print("=" * 60)
            
            # Inicializar
            if not await self.initialize():
                return {
                    "status": "error",
                    "message": "Error en inicialización",
                    "report": "❌ Error en inicialización del entrenador",
                    "joint_metrics": {},
                    "run_id": self.run_id
                }
            
            await self._update_progress(10, "Inicializando", "Cargando configuración...")
            
            # Entrenar agentes multi-timeframe en paralelo
            print(f"📊 Símbolos: {len(self.symbols)}")
            print(f"🎯 Timeframes de análisis: {', '.join(self.timeframes)}")
            print(f"⚡ Timeframes de ejecución: {', '.join(self.config_manager.get('symbols', {}).get('timeframes', {}).get('real_time', ['1m', '5m']))}")
            print("=" * 60)
            
            # Entrenar agentes cronológicos en paralelo
            tasks = [
                self.train_chronological_agent(symbol)
                for symbol in self.symbols
            ]
            
            print(f"🚀 Iniciando entrenamiento cronológico de {len(tasks)} agentes...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            all_results = {}
            for i, symbol in enumerate(self.symbols):
                if isinstance(results[i], Exception):
                    logger.error(f"❌ Error en {symbol}: {results[i]}")
                    all_results[symbol] = {
                        "status": "error",
                        "message": str(results[i]),
                        "metrics": {}
                    }
                else:
                    all_results[symbol] = results[i]
            
            # Calcular métricas conjuntas
            await self._update_progress(80, "Calculando métricas", "Procesando resultados...")
            self.joint_metrics = self._calculate_joint_metrics(all_results)
            
            # Generar reporte
            report = self._generate_multi_timeframe_report(all_results)
            
            # Guardar métricas conjuntas
            await self._save_joint_metrics()
            
            # Log de sesión
            await self._log_training_session(all_results)
            
            await self._update_progress(100, "Completado", "Entrenamiento finalizado")
            
            logger.info("✅ Entrenamiento histórico completado exitosamente")
            
            return {
                "status": "success",
                "report": report,
                "joint_metrics": self.joint_metrics,
                "run_id": self.run_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error en ejecución: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            return {
                "status": "error",
                "message": str(e),
                "report": f"❌ Error en entrenamiento: {e}",
                "joint_metrics": {},
                "run_id": self.run_id
            }
    
    def _calculate_joint_metrics(self, all_results: Dict) -> Dict[str, float]:
        """Calcula métricas conjuntas de todos los agentes"""
        try:
            all_metrics = []
            total_trades = 0
            total_pnl = 0
            
            for timeframe, results in all_results.items():
                for symbol, result in results.items():
                    if result.get("status") == "success" and "metrics" in result:
                        metrics = result["metrics"]
                        all_metrics.append(metrics)
                        total_trades += metrics.get("trade_count", 0)
                        total_pnl += metrics.get("pnl", 0)
            
            if not all_metrics:
                return {
                    "avg_daily_pnl": 0.0,
                    "balance_to_target": -100000.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "trade_count": 0
                }
            
            # Calcular métricas conjuntas
            avg_daily_pnl = np.mean([m.get("avg_daily_pnl", 0) for m in all_metrics])
            win_rate = np.mean([m.get("win_rate", 0) for m in all_metrics])
            max_drawdown = np.max([m.get("max_drawdown", 0) for m in all_metrics])
            sharpe_ratio = np.mean([m.get("sharpe_ratio", 0) for m in all_metrics])
            
            # Balance to target
            target_balance = self.training_config.get("financial_targets", {}).get("balance", {}).get("target", 100000.0)
            balance_to_target = total_pnl - target_balance
            
            return {
                "avg_daily_pnl": float(avg_daily_pnl),
                "balance_to_target": float(balance_to_target),
                "win_rate": float(win_rate),
                "max_drawdown": float(max_drawdown),
                "sharpe_ratio": float(sharpe_ratio),
                "trade_count": int(total_trades)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando métricas conjuntas: {e}")
            return {
                "avg_daily_pnl": 0.0,
                "balance_to_target": -100000.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "trade_count": 0
            }
    
    def _generate_report(self, all_results: Dict) -> str:
        """Genera reporte de entrenamiento con métricas avanzadas"""
        try:
            report_lines = []
            
            for timeframe, results in all_results.items():
                report_lines.append(f"<b>📊 Timeframe {timeframe}:</b>")
                
                for symbol, result in results.items():
                    if result.get("status") == "success" and "metrics" in result:
                        metrics = result["metrics"]
                        
                        # Obtener rango de leverage para el símbolo
                        symbol_config = self.symbol_configs.get(symbol, {})
                        leverage_range = symbol_config.get('leverage_range', [1, 10])
                        min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
                        max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
                        
                        report_lines.append(
                            f"<b>{symbol}:</b>\n"
                            f"• PnL Total: ${metrics.get('pnl', 0):.2f}\n"
                            f"• Tasa de Éxito: {metrics.get('win_rate', 0)*100:.1f}%\n"
                            f"• Trades: {metrics.get('trade_count', 0)} "
                            f"(L: {metrics.get('long_trades', 0)} | S: {metrics.get('short_trades', 0)})\n"
                            f"• PnL Long: ${metrics.get('long_pnl', 0):.2f} | "
                            f"PnL Short: ${metrics.get('short_pnl', 0):.2f}\n"
                            f"• Leverage: {metrics.get('avg_leverage', 0):.1f}x "
                            f"(Max: {metrics.get('max_leverage', 0):.1f}x)\n"
                            f"• Rango Configurado: {min_leverage}x - {max_leverage}x\n"
                            f"• Duración Promedio: {metrics.get('avg_trade_duration', 0):.1f}h\n"
                            f"• Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"
                            f"• Ganancia Promedio: ${metrics.get('avg_win', 0):.2f} | "
                            f"Pérdida Promedio: ${metrics.get('avg_loss', 0):.2f}\n"
                            f"• Mayor Ganancia: ${metrics.get('largest_win', 0):.2f} | "
                            f"Mayor Pérdida: ${metrics.get('largest_loss', 0):.2f}\n"
                            f"• Racha Ganadora: {metrics.get('consecutive_wins', 0)} | "
                            f"Racha Perdedora: {metrics.get('consecutive_losses', 0)}\n"
                            f"• Sharpe: {metrics.get('sharpe_ratio', 0):.2f} | "
                            f"Drawdown: {metrics.get('max_drawdown', 0)*100:.1f}%\n"
                            f"• Volatilidad: {metrics.get('volatility_avg', 0)*100:.2f}%\n"
                            f"• 🎯 Total Rewards: {metrics.get('total_rewards', 0):.2f}"
                        )
                    else:
                        report_lines.append(f"<b>{symbol}:</b> ❌ Error")
                
                report_lines.append("")  # Línea en blanco
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return "❌ Error generando reporte"
    
    def _generate_multi_timeframe_report(self, all_results: Dict) -> str:
        """Genera reporte de entrenamiento cronológico"""
        try:
            report_lines = []
            report_lines.append("<b>🚀 ENTRENAMIENTO CRONOLÓGICO</b>")
            report_lines.append("=" * 50)
            
            for symbol, result in all_results.items():
                if result.get("status") == "success" and "metrics" in result:
                    metrics = result["metrics"]
                    
                    # Obtener rango de leverage para el símbolo
                    symbol_config = self.symbol_configs.get(symbol, {})
                    leverage_range = symbol_config.get('leverage_range', [1, 10])
                    min_leverage = leverage_range[0] if len(leverage_range) >= 1 else 1
                    max_leverage = leverage_range[1] if len(leverage_range) >= 2 else 10
                    
                    # Obtener timeframes de análisis y ejecución
                    analysis_tfs = metrics.get('analysis_timeframes', [])
                    execution_tfs = metrics.get('execution_timeframes', [])
                    
                    report_lines.append(f"<b>{symbol}:</b>")
                    report_lines.append(f"• PnL Total: ${metrics.get('pnl', 0):.2f}")
                    report_lines.append(f"• Tasa de Éxito: {metrics.get('win_rate', 0)*100:.1f}%")
                    report_lines.append(f"• Trades: {metrics.get('trade_count', 0)} (L: {metrics.get('long_trades', 0)} | S: {metrics.get('short_trades', 0)})")
                    report_lines.append(f"• PnL Long: ${metrics.get('long_pnl', 0):.2f} | PnL Short: ${metrics.get('short_pnl', 0):.2f}")
                    report_lines.append(f"• Leverage: {metrics.get('avg_leverage', 0):.1f}x (Max: {metrics.get('max_leverage', 0):.1f}x)")
                    report_lines.append(f"• Rango Configurado: {min_leverage}x - {max_leverage}x")
                    report_lines.append(f"• Duración Promedio: {metrics.get('avg_trade_duration', 0):.1f}h")
                    report_lines.append(f"• Profit Factor: {metrics.get('profit_factor', 0):.2f}")
                    report_lines.append(f"• Ganancia Promedio: ${metrics.get('avg_win', 0):.2f} | Pérdida Promedio: ${metrics.get('avg_loss', 0):.2f}")
                    report_lines.append(f"• Mayor Ganancia: ${metrics.get('largest_win', 0):.2f} | Mayor Pérdida: ${metrics.get('largest_loss', 0):.2f}")
                    report_lines.append(f"• Racha Ganadora: {metrics.get('consecutive_wins', 0)} | Racha Perdedora: {metrics.get('consecutive_losses', 0)}")
                    report_lines.append(f"• Sharpe: {metrics.get('sharpe_ratio', 0):.2f} | Drawdown: {metrics.get('max_drawdown', 0)*100:.1f}%")
                    report_lines.append(f"• Volatilidad: {metrics.get('volatility_avg', 0)*100:.2f}%")
                    report_lines.append(f"• 🎯 Total Rewards: {metrics.get('total_rewards', 0):.2f}")
                    report_lines.append(f"• 📊 Análisis: {', '.join(analysis_tfs)}")
                    report_lines.append(f"• ⚡ Ejecución: {', '.join(execution_tfs)}")
                    report_lines.append(f"• 🔄 Análisis Cronológico: {'Sí' if metrics.get('chronological_analysis', False) else 'No'}")
                    report_lines.append("")
                else:
                    report_lines.append(f"<b>{symbol}:</b> ❌ Error")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte multi-timeframe: {e}")
            return "❌ Error generando reporte multi-timeframe"
    
    async def _save_joint_metrics(self) -> None:
        """Guarda métricas conjuntas"""
        try:
            metrics_file = self.tmp_dir / f"joint_metrics_{self.run_id}.json"
            self._save_json_file(metrics_file, self.joint_metrics)
        except Exception as e:
            logger.error(f"❌ Error guardando métricas conjuntas: {e}")
    
    async def _log_training_session(self, all_results: Dict) -> None:
        """Registra la sesión de entrenamiento en la base de datos"""
        try:
            if self.db_manager:
                # Contar resultados exitosos
                successful_runs = 0
                total_runs = 0
                
                for timeframe, results in all_results.items():
                    for symbol, result in results.items():
                        total_runs += 1
                        if result.get("status") == "success":
                            successful_runs += 1
                
                # Log de sesión simplificado
                logger.info(f"📊 Sesión de entrenamiento {self.run_id}: {successful_runs}/{total_runs} exitosos")
                
        except Exception as e:
            logger.error(f"❌ Error registrando sesión de entrenamiento: {e}")


async def main():
    """Función principal"""
    try:
        # Obtener progress_id de los argumentos
        progress_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
        
        # Crear y ejecutar entrenador
        trainer = TrainHistoricalEnterprise(progress_id)
        result = await trainer.execute()
        
        # Imprimir resultado JSON para control/handlers.py
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        error_result = {
            "status": "error",
            "message": str(e),
            "report": f"❌ Error crítico: {e}",
            "joint_metrics": {},
            "run_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
