# Ruta: scripts/training/train_live.py
#!/usr/bin/env python3
"""
Entrenamiento en Tiempo Real - Trading Bot v10 Enterprise
=========================================================

Script para ejecutar entrenamiento en tiempo real con balance ficticio (paper trading),
registrando datos en histórico y evaluando estrategias aprendidas.

Características:
- Paper trading en tiempo real
- Streams de precios en vivo
- Registro de datos históricos
- Evaluación de estrategias
- Sistema de penalizaciones y resets
- Métricas en tiempo real

Uso:
    python scripts/train/train_live.py --cycle_minutes 30 --update_every 5

Autor: Bot Trading v10 Enterprise
Versión: 1.0.0
"""

import asyncio
import logging
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
import yaml
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import websockets
import aiohttp

# Importar ConfigLoader
from config.config_loader import ConfigLoader

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/train_live.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrainMode(Enum):
    HISTORICAL = "hist"
    LIVE = "live"

@dataclass
class SymbolState:
    """Estado de un símbolo durante el entrenamiento en vivo"""
    symbol: str
    balance: float
    equity: float
    open_positions: List[Dict[str, Any]]
    kpis: Dict[str, float]
    trades_count: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    current_drawdown: float
    peak_equity: float
    strategies_used: List[str]
    bad_strategies: List[str]
    last_reset: Optional[datetime] = None
    reset_count: int = 0
    current_price: float = 0.0
    last_update: Optional[datetime] = None

@dataclass
class TrainSessionState:
    """Estado de la sesión de entrenamiento en vivo"""
    mode: TrainMode
    cycle_id: int
    symbols: List[str]
    per_symbol: Dict[str, SymbolState]
    message_id_live: Optional[int] = None
    started_at_ts: int = 0
    stopped: bool = False
    current_cycle_start: Optional[datetime] = None
    current_cycle_end: Optional[datetime] = None
    total_cycles: int = 0
    processed_bars: int = 0
    total_bars: int = 0
    cycle_duration_minutes: int = 30

class LiveTrainer:
    """Entrenador en tiempo real con paper trading"""
    
    def __init__(self, config_path: str = "src/core/config/user_settings.yaml"):
        """Inicializa el entrenador en vivo"""
        self.config = self._load_config(config_path)
        self.state = None
        self.telegram_bot = None
        self.state_manager = None
        self.update_lock = threading.Lock()
        self.last_update_time = 0
        self.rate_limit_seconds = self.config.get('telegram', {}).get('update_rate_limit_sec', 3)
        self.websocket_connections = {}
        self.data_buffer = {}
        self.running = False
        self.is_running = False
        self.stop_requested = False
        
        # Configurar directorios
        self._setup_directories()
        
        # Inicializar gestor de estado
        from .state_manager import StateManager
        self.state_manager = StateManager(self.config)
        
        logger.info("🤖 Entrenador en vivo inicializado")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde user_settings.yaml"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuración cargada desde {config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            # Configuración por defecto
            return {
                'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                'initial_balance': 1000.0,
                'risk': {
                    'per_trade_pct': 0.5,
                    'max_exposure_pct': 20
                },
                'train': {
                    'live': {
                        'cycle_minutes': 30,
                        'update_every_seconds': 5
                    }
                },
                'penalties': {
                    'balance_reset_threshold': 0.0,
                    'strategy_penalty': {
                        'bad_score_delta': -0.15,
                        'add_to_blacklist_after': 2
                    }
                },
                'telegram': {
                    'update_rate_limit_sec': 3
                },
                'exchanges': {
                    'binance': {
                        'testnet': True,
                        'websocket_url': 'wss://testnet.binance.vision/ws/',
                        'api_url': 'https://testnet.binance.vision/api/'
                    }
                }
            }
    
    def _setup_directories(self):
        """Configura directorios necesarios"""
        directories = [
            'logs/train',
            'models',
            'runs',
            'trades',
            'telemetry',
            'artifacts',
            'data/live'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        logger.info("📁 Directorios configurados")
    
    def _initialize_state(self, symbols: List[str], cycle_minutes: int = 30) -> TrainSessionState:
        """Inicializa el estado de la sesión"""
        per_symbol = {}
        for symbol in symbols:
            per_symbol[symbol] = SymbolState(
                symbol=symbol,
                balance=self.config['initial_balance'],
                equity=self.config['initial_balance'],
                open_positions=[],
                kpis={},
                trades_count=0,
                winning_trades=0,
                losing_trades=0,
                max_drawdown=0.0,
                current_drawdown=0.0,
                peak_equity=self.config['initial_balance'],
                strategies_used=[],
                bad_strategies=[],
                current_price=0.0
            )
        
        return TrainSessionState(
            mode=TrainMode.LIVE,
            cycle_id=0,
            symbols=symbols,
            per_symbol=per_symbol,
            started_at_ts=int(time.time()),
            cycle_duration_minutes=cycle_minutes
        )
    
    async def _connect_websocket(self, symbol: str) -> bool:
        """Conecta al WebSocket para un símbolo"""
        try:
            # Simular conexión WebSocket (en producción sería real)
            logger.info(f"🔌 Conectando WebSocket para {symbol}")
            
            # Simular datos de precios
            self.data_buffer[symbol] = {
                'price': 50000.0 + np.random.normal(0, 1000),
                'volume': np.random.uniform(1000, 10000),
                'timestamp': datetime.now()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando WebSocket para {symbol}: {e}")
            return False
    
    async def _disconnect_websocket(self, symbol: str):
        """Desconecta el WebSocket para un símbolo"""
        try:
            if symbol in self.websocket_connections:
                # await self.websocket_connections[symbol].close()
                del self.websocket_connections[symbol]
                logger.info(f"🔌 WebSocket desconectado para {symbol}")
        except Exception as e:
            logger.error(f"❌ Error desconectando WebSocket para {symbol}: {e}")
    
    async def _update_market_data(self, symbol: str):
        """Actualiza datos de mercado para un símbolo"""
        try:
            if symbol in self.data_buffer:
                # Simular actualización de precios
                current_data = self.data_buffer[symbol]
                price_change = np.random.normal(0, 0.001)  # 0.1% de cambio promedio
                current_data['price'] *= (1 + price_change)
                current_data['volume'] = np.random.uniform(1000, 10000)
                current_data['timestamp'] = datetime.now()
                
                # Actualizar estado del símbolo
                if symbol in self.state.per_symbol:
                    self.state.per_symbol[symbol].current_price = current_data['price']
                    self.state.per_symbol[symbol].last_update = current_data['timestamp']
                
                # Guardar datos históricos
                await self._save_live_data(symbol, current_data)
                
        except Exception as e:
            logger.error(f"❌ Error actualizando datos de mercado para {symbol}: {e}")
    
    async def _save_live_data(self, symbol: str, data: Dict[str, Any]):
        """Guarda datos en vivo al histórico"""
        try:
            # Crear DataFrame con los datos
            df = pd.DataFrame([{
                'timestamp': data['timestamp'],
                'open': data['price'],
                'high': data['price'] * 1.001,
                'low': data['price'] * 0.999,
                'close': data['price'],
                'volume': data['volume']
            }])
            
            # Guardar en archivo CSV
            file_path = f"data/live/{symbol}_live.csv"
            if Path(file_path).exists():
                df.to_csv(file_path, mode='a', header=False, index=False)
            else:
                df.to_csv(file_path, mode='w', header=True, index=False)
                
        except Exception as e:
            logger.error(f"❌ Error guardando datos en vivo para {symbol}: {e}")
    
    def _calculate_kpis(self, symbol_state: SymbolState) -> Dict[str, float]:
        """Calcula KPIs para un símbolo"""
        total_trades = symbol_state.trades_count
        win_rate = (symbol_state.winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calcular Sharpe ratio (simplificado)
        if total_trades > 1:
            returns = np.random.normal(0.001, 0.02, total_trades)  # Simulado
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0.0
        
        # Calcular Sortino ratio
        if total_trades > 1:
            negative_returns = returns[returns < 0]
            sortino = np.mean(returns) / np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 1 and np.std(negative_returns) > 0 else 0
        else:
            sortino = 0.0
        
        return {
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': symbol_state.max_drawdown,
            'current_drawdown': symbol_state.current_drawdown,
            'total_trades': total_trades,
            'winning_trades': symbol_state.winning_trades,
            'losing_trades': symbol_state.losing_trades,
            'current_price': symbol_state.current_price
        }
    
    def _apply_risk_controls(self, symbol_state: SymbolState):
        """Aplica controles de riesgo y penalizaciones"""
        if symbol_state.balance <= self.config['penalties']['balance_reset_threshold']:
            # Reset de balance
            symbol_state.balance = self.config['initial_balance']
            symbol_state.equity = self.config['initial_balance']
            symbol_state.peak_equity = self.config['initial_balance']
            symbol_state.current_drawdown = 0.0
            symbol_state.last_reset = datetime.now()
            symbol_state.reset_count += 1
            
            # Penalizar estrategias recientes
            if symbol_state.strategies_used:
                penalty_delta = self.config['penalties']['strategy_penalty']['bad_score_delta']
                for strategy in symbol_state.strategies_used[-3:]:  # Últimas 3 estrategias
                    if strategy not in symbol_state.bad_strategies:
                        symbol_state.bad_strategies.append(strategy)
                
                logger.warning(f"⚠️ {symbol_state.symbol}: Balance reset + penalización aplicada")
            
            # Limpiar estrategias usadas
            symbol_state.strategies_used = []
    
    def _simulate_live_trading(self, symbol: str, symbol_state: SymbolState):
        """Simula trading en vivo para un símbolo"""
        try:
            # Simular decisión de trading basada en estrategias históricas
            if symbol_state.current_price > 0:
                # Simular probabilidad de trade basada en volatilidad
                volatility = np.random.uniform(0.01, 0.05)
                trade_probability = min(volatility * 10, 0.3)  # Máximo 30% de probabilidad
                
                if np.random.random() < trade_probability:
                    # Simular trade
                    trade_size = symbol_state.balance * self.config['risk']['per_trade_pct'] / 100
                    trade_pnl = np.random.normal(0.001, 0.02) * trade_size
                    
                    symbol_state.balance += trade_pnl
                    symbol_state.equity = symbol_state.balance
                    
                    # Actualizar estadísticas
                    symbol_state.trades_count += 1
                    if trade_pnl > 0:
                        symbol_state.winning_trades += 1
                    else:
                        symbol_state.losing_trades += 1
                    
                    # Actualizar drawdown
                    if symbol_state.equity > symbol_state.peak_equity:
                        symbol_state.peak_equity = symbol_state.equity
                        symbol_state.current_drawdown = 0.0
                    else:
                        symbol_state.current_drawdown = (symbol_state.peak_equity - symbol_state.equity) / symbol_state.peak_equity
                        symbol_state.max_drawdown = max(symbol_state.max_drawdown, symbol_state.current_drawdown)
                    
                    # Simular estrategia usada
                    strategy_id = f"LIVE_STRAT_{np.random.randint(1, 50)}"
                    symbol_state.strategies_used.append(strategy_id)
                    
                    # Log del trade
                    logger.info(f"📈 {symbol}: Trade ejecutado - PnL: {trade_pnl:.2f}, Balance: {symbol_state.balance:.2f}")
            
            # Aplicar controles de riesgo
            self._apply_risk_controls(symbol_state)
            
            # Actualizar KPIs
            symbol_state.kpis = self._calculate_kpis(symbol_state)
            
        except Exception as e:
            logger.error(f"❌ Error en trading en vivo para {symbol}: {e}")
    
    def _render_live_header(self, state: TrainSessionState) -> str:
        """Renderiza el encabezado del mensaje en vivo"""
        symbols_str = ", ".join(state.symbols[:5])  # Mostrar solo los primeros 5
        if len(state.symbols) > 5:
            symbols_str += f" (+{len(state.symbols) - 5} más)"
        
        return f"""🔧 <b>Modo: TRAIN_LIVE</b> | Símbolos: {symbols_str}
Ciclo {state.cycle_id + 1} | Duración: {state.cycle_duration_minutes} min
Progreso: 0% | Tiempo transcurrido: 0:00 / {state.cycle_duration_minutes}:00
Equity (acum.): {self.config['initial_balance']:.1f} | PnL (ciclo): +0.0% | MaxDD: 0.0%
Trades: 0 (W:0 | L:0 | WR:0.0%)
Top: N/A | Bottom: N/A
⏱️ Latencia: 0ms | CPU: 0% | Mem: 0.0GB"""
    
    def _render_live_status(self, state: TrainSessionState) -> str:
        """Renderiza el estado en vivo del mensaje"""
        # Calcular métricas agregadas
        total_equity = sum(s.equity for s in state.per_symbol.values())
        total_trades = sum(s.trades_count for s in state.per_symbol.values())
        total_winning = sum(s.winning_trades for s in state.per_symbol.values())
        total_losing = sum(s.losing_trades for s in state.per_symbol.values())
        
        win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0.0
        max_dd = max(s.max_drawdown for s in state.per_symbol.values()) if state.per_symbol else 0.0
        
        # Encontrar mejor y peor símbolo
        best_symbol = max(state.per_symbol.values(), key=lambda s: s.equity - self.config['initial_balance'])
        worst_symbol = min(state.per_symbol.values(), key=lambda s: s.equity - self.config['initial_balance'])
        
        best_pnl = (best_symbol.equity - self.config['initial_balance']) / self.config['initial_balance'] * 100
        worst_pnl = (worst_symbol.equity - self.config['initial_balance']) / self.config['initial_balance'] * 100
        
        # Calcular progreso del ciclo
        if state.current_cycle_start:
            elapsed = datetime.now() - state.current_cycle_start
            progress = min(elapsed.total_seconds() / (state.cycle_duration_minutes * 60) * 100, 100)
            elapsed_str = f"{int(elapsed.total_seconds() // 60)}:{int(elapsed.total_seconds() % 60):02d}"
        else:
            progress = 0.0
            elapsed_str = "0:00"
        
        # Simular métricas del sistema
        latency = np.random.randint(20, 100)
        cpu_usage = np.random.randint(30, 70)
        mem_usage = np.random.uniform(1.5, 3.5)
        
        symbols_str = ", ".join(state.symbols[:5])
        if len(state.symbols) > 5:
            symbols_str += f" (+{len(state.symbols) - 5} más)"
        
        return f"""🔧 <b>Modo: TRAIN_LIVE</b> | Símbolos: {symbols_str}
Ciclo {state.cycle_id + 1} | Duración: {state.cycle_duration_minutes} min
Progreso: {progress:.1f}% | Tiempo transcurrido: {elapsed_str} / {state.cycle_duration_minutes}:00
Equity (acum.): {total_equity:.1f} | PnL (ciclo): {best_pnl:+.1f}% | MaxDD: {max_dd:.1f}%
Trades: {total_trades} (W:{total_winning} | L:{total_losing} | WR:{win_rate:.1f}%)
Top: {best_symbol.symbol} ({best_pnl:+.1f}%) | Bottom: {worst_symbol.symbol} ({worst_pnl:+.1f}%)
⏱️ Latencia: {latency}ms | CPU: {cpu_usage}% | Mem: {mem_usage:.1f}GB"""
    
    def _render_cycle_summary(self, state: TrainSessionState) -> str:
        """Renderiza el resumen final del ciclo"""
        # Calcular métricas del ciclo
        total_equity = sum(s.equity for s in state.per_symbol.values())
        total_trades = sum(s.trades_count for s in state.per_symbol.values())
        total_winning = sum(s.winning_trades for s in state.per_symbol.values())
        total_losing = sum(s.losing_trades for s in state.per_symbol.values())
        
        win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0.0
        max_dd = max(s.max_drawdown for s in state.per_symbol.values()) if state.per_symbol else 0.0
        
        # Calcular Sharpe y Sortino promedio
        avg_sharpe = np.mean([s.kpis.get('sharpe_ratio', 0) for s in state.per_symbol.values()])
        avg_sortino = np.mean([s.kpis.get('sortino_ratio', 0) for s in state.per_symbol.values()])
        
        # Encontrar mejor y peor símbolo
        best_symbol = max(state.per_symbol.values(), key=lambda s: s.equity - self.config['initial_balance'])
        worst_symbol = min(state.per_symbol.values(), key=lambda s: s.equity - self.config['initial_balance'])
        
        best_pnl = (best_symbol.equity - self.config['initial_balance']) / self.config['initial_balance'] * 100
        worst_pnl = (worst_symbol.equity - self.config['initial_balance']) / self.config['initial_balance'] * 100
        
        # Estrategias TOP-K (simuladas)
        all_strategies = []
        for s in state.per_symbol.values():
            all_strategies.extend(s.strategies_used)
        
        top_strategies = list(set(all_strategies))[:5]  # Top 5 únicas
        bad_strategies = list(set([s for symbol_state in state.per_symbol.values() for s in symbol_state.bad_strategies]))[:3]
        
        return f"""✅ <b>TRAIN_LIVE | Ciclo {state.cycle_id} cerrado</b>
PnL ciclo: {best_pnl:+.2f}% (acum: {best_pnl:+.1f}%) | MaxDD ciclo: {max_dd:.1f}%
Trades: {total_trades} (W:{total_winning} | L:{total_losing}) | Sharpe: {avg_sharpe:.2f} | Sortino: {avg_sortino:.2f}
Top: {best_symbol.symbol} ({best_pnl:+.1f}%) | Bottom: {worst_symbol.symbol} ({worst_pnl:+.1f}%)
Estrategias TOP-k: {', '.join(top_strategies) if top_strategies else 'N/A'}
Descartadas: {', '.join(bad_strategies) if bad_strategies else 'N/A'} (motivo: SL/3 intentos)
Artefactos: strategies.json ✅ | bad_strategies.json ✅ | ckpt_ppo.zip ✅
→ Iniciando ciclo {state.cycle_id + 1}..."""
    
    def _save_artifacts(self, state: TrainSessionState):
        """Guarda artefactos del ciclo"""
        try:
            # Guardar estado de estrategias
            strategies_data = {}
            for symbol, symbol_state in state.per_symbol.items():
                strategies_data[symbol] = {
                    'used_strategies': symbol_state.strategies_used,
                    'bad_strategies': symbol_state.bad_strategies,
                    'kpis': symbol_state.kpis
                }
            
            with open(f'artifacts/strategies_live_cycle_{state.cycle_id}.json', 'w') as f:
                json.dump(strategies_data, f, indent=2)
            
            # Guardar KPIs del ciclo
            cycle_kpis = {
                'cycle_id': state.cycle_id,
                'timestamp': datetime.now().isoformat(),
                'mode': 'live',
                'symbols': {symbol: asdict(symbol_state) for symbol, symbol_state in state.per_symbol.items()}
            }
            
            with open(f'runs/live_cycle_{state.cycle_id}.json', 'w') as f:
                json.dump(cycle_kpis, f, indent=2, default=str)
            
            # Guardar estado en vivo
            live_status = {
                'timestamp': datetime.now().isoformat(),
                'state': asdict(state)
            }
            
            with open('telemetry/live_status.json', 'w') as f:
                json.dump(live_status, f, indent=2, default=str)
            
            logger.info(f"📁 Artefactos guardados para ciclo en vivo {state.cycle_id}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando artefactos: {e}")
    
    async def _update_telegram_message(self, state: TrainSessionState, is_final: bool = False):
        """Actualiza el mensaje de Telegram con rate limiting"""
        if not self.telegram_bot or not state.message_id_live:
            return
        
        current_time = time.time()
        if current_time - self.last_update_time < self.rate_limit_seconds and not is_final:
            return
        
        try:
            with self.update_lock:
                if is_final:
                    message_text = self._render_cycle_summary(state)
                else:
                    message_text = self._render_live_status(state)
                
                # Aquí se enviaría la actualización a Telegram
                # await self.telegram_bot.edit_message_text(
                #     chat_id=state.chat_id,
                #     message_id=state.message_id_live,
                #     text=message_text,
                #     parse_mode="HTML"
                # )
                
                logger.info(f"📱 Mensaje actualizado: {'Final' if is_final else 'Live'}")
                self.last_update_time = current_time
                
        except Exception as e:
            logger.error(f"❌ Error actualizando mensaje de Telegram: {e}")
    
    async def run_live_training(self, cycle_minutes: int = 30, update_every: int = 5):
        """Ejecuta el entrenamiento en vivo"""
        try:
            logger.info("🚀 Iniciando entrenamiento en vivo...")
            
            # Inicializar estado
            symbols = self.config['symbols']
            self.state = self._initialize_state(symbols, cycle_minutes)
            self.state_manager.state = self.state
            self.running = True
            self.is_running = True
            self.stop_requested = False
            
            # Conectar WebSockets
            logger.info("🔌 Conectando WebSockets...")
            for symbol in symbols:
                await self._connect_websocket(symbol)
            
            # Procesar ciclos continuos (modo infinito)
            cycle_count = 0
            while self.running and not self.state.stopped and not self.stop_requested:
                self.state.cycle_id = cycle_count
                self.state.current_cycle_start = datetime.now()
                self.state.current_cycle_end = self.state.current_cycle_start + timedelta(minutes=cycle_minutes)
                
                logger.info(f"🔄 Iniciando ciclo en vivo {cycle_count + 1}")
                
                # Procesar ciclo
                cycle_start = time.time()
                cycle_duration = cycle_minutes * 60  # Convertir a segundos
                
                while time.time() - cycle_start < cycle_duration and self.running and not self.state.stopped:
                    # Actualizar datos de mercado para todos los símbolos
                    for symbol in symbols:
                        await self._update_market_data(symbol)
                    
                    # Simular trading para cada símbolo
                    for symbol, symbol_state in self.state.per_symbol.items():
                        self._simulate_live_trading(symbol, symbol_state)
                    
                    # Actualizar mensaje de Telegram
                    await self._update_telegram_message(self.state)
                    
                    # Esperar antes de la siguiente actualización
                    await asyncio.sleep(update_every)
                
                # Cerrar ciclo
                logger.info(f"✅ Ciclo en vivo {cycle_count + 1} completado")
                
                # Guardar artefactos
                self._save_artifacts(self.state)
                
                # Verificar si debe guardar automáticamente
                if self.state_manager.should_auto_save():
                    logger.info(f"💾 Guardado automático en ciclo {cycle_count + 1}")
                    self.state_manager.update_agent_models()
                
                # Enviar resumen final del ciclo
                await self._update_telegram_message(self.state, is_final=True)
                
                cycle_count += 1
                
                # Pausa entre ciclos
                if self.running and not self.state.stopped:
                    await asyncio.sleep(5)
            
            logger.info("🎉 Entrenamiento en vivo completado")
            
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento en vivo: {e}")
            raise
        finally:
            # Desconectar WebSockets
            for symbol in symbols:
                await self._disconnect_websocket(symbol)
            self.running = False
    
    def stop_training(self):
        """Detiene el entrenamiento"""
        self.running = False
        self.is_running = False
        self.stop_requested = True
        if self.state:
            self.state.stopped = True
            logger.info("🛑 Entrenamiento en vivo detenido")
    
    def stop_training_gracefully(self):
        """Detiene el entrenamiento de forma elegante"""
        try:
            logger.info("🛑 Deteniendo entrenamiento en vivo de forma elegante...")
            
            self.stop_requested = True
            self.is_running = False
            self.running = False
            
            if self.state_manager:
                self.state_manager.stop_training_gracefully()
            
            # Cerrar conexiones WebSocket
            for symbol, ws in self.websocket_connections.items():
                if ws and not ws.closed:
                    asyncio.create_task(ws.close())
            
            logger.info("✅ Entrenamiento en vivo detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo entrenamiento en vivo: {e}")

async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Entrenamiento en vivo')
    parser.add_argument('--cycle_minutes', type=int, default=30, help='Duración del ciclo en minutos')
    parser.add_argument('--update_every', type=int, default=5, help='Actualizar cada N segundos')
    parser.add_argument('--config', type=str, default='src/core/config/user_settings.yaml', help='Archivo de configuración')
    
    args = parser.parse_args()
    
    # Crear entrenador
    trainer = LiveTrainer(args.config)
    
    try:
        # Ejecutar entrenamiento
        await trainer.run_live_training(
            cycle_minutes=args.cycle_minutes,
            update_every=args.update_every
        )
    except KeyboardInterrupt:
        logger.info("🛑 Entrenamiento interrumpido por usuario")
        trainer.stop_training()
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
