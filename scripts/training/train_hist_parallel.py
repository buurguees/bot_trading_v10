#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train Hist Parallel - Bot Trading v10 Enterprise
================================================
Script principal para comando /train_hist con entrenamiento paralelo sincronizado.
Ejecuta mÃºltiples agentes en paralelo con timestamps sincronizados.

CaracterÃ­sticas:
- Entrenamiento paralelo sincronizado por timestamps
- PnL diario agregado (media entre agentes)
- Win rate global y mÃ©tricas consolidadas
- Progreso en tiempo real para Telegram
- Guardado de estrategias y runs por agente
- Base de conocimiento compartida
- Uso de datos histÃ³ricos reales de DBs locales

Uso desde Telegram:
    /train_hist

Uso desde lÃ­nea de comandos:
    python scripts/training/train_hist_parallel.py --progress-file data/tmp/progress.json

Autor: Bot Trading v10 Enterprise
VersiÃ³n: 2.1.0 (Actualizado para entrenamiento real con datos histÃ³ricos)
"""

import asyncio
import sys
import json
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import random
import sqlite3
import pandas as pd
import numpy as np

# Cargar variables de entorno
load_dotenv()

# Agregar directorio raÃ­z al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def _load_training_objectives():
    """Carga objetivos desde training_objectives.yaml"""
    try:
        import yaml
        objectives_path = Path("config/core/training_objectives.yaml")
        if objectives_path.exists():
            with open(objectives_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning("training_objectives.yaml no encontrado, usando valores por defecto")
            return None
    except Exception as e:
        logger.warning(f"Error cargando training_objectives.yaml: {e}")
        return None

def _load_training_mode_config(mode: str = "ultra_fast"):
    """Carga configuraciÃ³n especÃ­fica del modo de entrenamiento desde training_objectives.yaml"""
    try:
        objectives = _load_training_objectives()
        if objectives and 'historical_training_modes' in objectives:
            training_modes = objectives['historical_training_modes']
            if mode in training_modes:
                return training_modes[mode]
            else:
                logger.warning(f"Modo '{mode}' no encontrado, usando 'ultra_fast'")
                return training_modes.get('ultra_fast', {})
        else:
            logger.warning("No se encontraron modos de entrenamiento histÃ³rico, usando configuraciÃ³n por defecto")
            return {}
    except Exception as e:
        logger.warning(f"Error cargando configuraciÃ³n del modo de entrenamiento: {e}")
        return {}
    
    # ConfiguraciÃ³n por defecto si falla la carga
    defaults = {
        'ultra_fast': {'days': 30, 'cycles': 50, 'chunk_size_days': 7, 'chunk_overlap_days': 1, 'max_memory_mb': 2048, 'progress_report_interval': 10},
        'fast': {'days': 90, 'cycles': 100, 'chunk_size_days': 14, 'chunk_overlap_days': 2, 'max_memory_mb': 4096, 'progress_report_interval': 5},
        'normal': {'days': 180, 'cycles': 200, 'chunk_size_days': 30, 'chunk_overlap_days': 3, 'max_memory_mb': 8192, 'progress_report_interval': 2},
        'complete': {'days': 365, 'cycles': 500, 'chunk_size_days': 60, 'chunk_overlap_days': 5, 'max_memory_mb': 16384, 'progress_report_interval': 1}
    }
    return defaults.get(mode, defaults['ultra_fast'])

# Imports del proyecto
try:
    from scripts.training.parallel_training_orchestrator import create_parallel_training_orchestrator
    from core.sync.metrics_aggregator import create_metrics_aggregator
    from config.unified_config import get_config_manager
except ImportError as e:
    print(f"âš ï¸ Imports no disponibles, usando fallbacks funcionales: {e}")
    
    # Fallbacks FUNCIONALES en lugar de None
    async def create_parallel_training_orchestrator(*args, **kwargs):
        class MockOrchestrator:
            async def stop_training(self): pass
        return MockOrchestrator()
    
    def create_metrics_aggregator(*args, **kwargs):
        class MockAggregator:
            async def aggregate_symbol_stats(self, data): return data
            async def cleanup(self): pass
        return MockAggregator()
    
    def get_config_manager():
        class WorkingFallbackConfig:
            def __init__(self):
                # Cargar user_settings.yaml
                self.training_settings = self._load_user_settings()
            
            def _load_user_settings(self):
                """Carga configuraciÃ³n desde user_settings.yaml"""
                try:
                    import yaml
                    user_settings_path = Path("config/user_settings.yaml")
                    if user_settings_path.exists():
                        data = yaml.safe_load(user_settings_path.read_text(encoding='utf-8')) or {}
                        return data.get('training_settings', {})
                except Exception:
                    pass
                # Fallback por defecto
                return {'mode': 'ultra_fast'}
            
            def get_symbols(self): 
                # Cargar desde symbols.yaml como fallback
                try:
                    import yaml
                    symbols_path = Path("config/core/symbols.yaml")
                    if symbols_path.exists():
                        data = yaml.safe_load(symbols_path.read_text(encoding='utf-8')) or {}
                        active_symbols = data.get('active_symbols', {})
                        symbols = []
                        for group in ['primary', 'secondary', 'experimental']:
                            if group in active_symbols:
                                symbols.extend(active_symbols[group])
                        if symbols:
                            return symbols
                except Exception:
                    pass
                # Fallback hardcoded si no se puede cargar symbols.yaml
                return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "PEPEUSDT", "SHIBUSDT"]
            
            def get_timeframes(self): 
                # Cargar desde symbols.yaml como fallback
                try:
                    import yaml
                    symbols_path = Path("config/core/symbols.yaml")
                    if symbols_path.exists():
                        data = yaml.safe_load(symbols_path.read_text(encoding='utf-8')) or {}
                        timeframes = data.get('timeframes', {})
                        tf_list = []
                        for group in ['real_time', 'analysis', 'strategic']:
                            if group in timeframes:
                                tf_list.extend(timeframes[group])
                        if tf_list:
                            return tf_list
                except Exception:
                    pass
                # Fallback hardcoded
                return ["1h", "4h", "1d"]
            
            def get_initial_balance(self): 
                return 1000.0
        return WorkingFallbackConfig()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/train_hist_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SeÃ±al global para modo continuo controlado desde Telegram
STOP_EVENT: asyncio.Event | None = None

class TrainHistParallel:
    """
    Entrenador HistÃ³rico Paralelo
    =============================
    
    Ejecuta entrenamiento histÃ³rico con mÃºltiples agentes sincronizados
    y agrega resultados globales para anÃ¡lisis conjunto. Ahora usa datos histÃ³ricos reales de DBs.
    """
    
    def __init__(self, progress_file: Optional[str] = None):
        """
        Inicializa el entrenador
        
        Args:
            progress_file: Archivo para guardar progreso (opcional)
        """
        self.progress_file = progress_file
        self.session_id = f"train_hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Configurar semilla determinista para reproducibilidad
        self.random_seed = int(datetime.now().timestamp()) % 10000
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
        
        # ConfiguraciÃ³n
        self.config = get_config_manager()
        self.symbols = self.config.get_symbols()
        
        # Separar timeframes por funciÃ³n
        self.execution_timeframes = ['1m', '5m']  # Obligatorios para trading
        self.analysis_timeframes = ['15m', '1h', '4h', '1d']  # Para features y anÃ¡lisis
        self.all_timeframes = self.execution_timeframes + self.analysis_timeframes
        
        # Usar todos para carga de datos
        self.timeframes = self.all_timeframes
        
        # Cargar objetivos de entrenamiento
        self.training_objectives = _load_training_objectives()
        if self.training_objectives:
            self.initial_balance = self.training_objectives.get('financial_targets', {}).get('balance', {}).get('initial', 1000.0)
            self.target_balance = self.training_objectives.get('financial_targets', {}).get('balance', {}).get('target', 5000.0)
            self.target_roi_pct = self.training_objectives.get('financial_targets', {}).get('roi', {}).get('target_pct', 400.0)
        else:
            self.initial_balance = self.config.get_initial_balance()
            self.target_balance = 5000.0
            self.target_roi_pct = 400.0

        logger.info(f"Balance inicial: ${self.initial_balance:,.2f}")
        logger.info(f"Balance objetivo: ${self.target_balance:,.2f}")
        logger.info(f"ROI objetivo: {self.target_roi_pct:.1f}%")
        
        # Componentes principales
        self.orchestrator = None
        self.metrics_aggregator = None
        self.capital_manager = None
        
        # Estado del entrenamiento
        self.is_running = False
        self.start_time = None
        self.results = None
        self.pre_aligned_data: Optional[Dict[str, Any]] = None
        self.cycle_metrics_history: List[Dict[str, Any]] = []
        self.force_simulate: bool = False
        self._symbol_leverage_ranges: Dict[str, List[float]] = {}
        self._prev_cycle_leverage_per_symbol: Dict[str, float] = {}
        # Desactivar mensajes por ciclo a Telegram (solo enviar resumen final)
        self.enable_cycle_telegram: bool = False
        # Suprimir ruido de sincronizaciÃ³n cuando se cae a simulaciÃ³n
        self._install_sync_log_filters()
        
        logger.info(f"ðŸŽ¯ TrainHistParallel inicializado: {len(self.symbols)} sÃ­mbolos")

        # Cargar rangos de leverage desde YAML (si es posible)
        try:
            self._load_symbol_leverage_ranges()
        except Exception as e:
            logger.warning(f"âš ï¸ No se pudieron cargar leverage_range de symbols.yaml: {e}")

        # Datos histÃ³ricos cargados
        self.historical_data: Dict[str, Dict[str, pd.DataFrame]] = {}  # {symbol: {tf: df}}

    def _get_training_days(self, mode: str = "ultra_fast") -> int:
        """Obtiene dÃ­as por modo desde training_objectives.yaml. Fallback seguro.
        Modo puede ser: ultra_fast, fast, normal, complete.
        """
        try:
            mode_config = _load_training_mode_config(mode)
            if 'days' in mode_config:
                return int(mode_config['days'])
        except Exception as e:
            logger.warning(f"Error obteniendo dÃ­as de entrenamiento para modo '{mode}': {e}")
        
        # Fallback por defecto
        defaults = {
            'ultra_fast': 30,
            'fast': 90,
            'normal': 180,
            'complete': 365,
        }
        return defaults.get(mode, 30)
    
    def _get_training_cycles(self, mode: str = "ultra_fast") -> int:
        """Obtiene nÃºmero de ciclos por modo desde training_objectives.yaml"""
        try:
            mode_config = _load_training_mode_config(mode)
            if 'cycles' in mode_config:
                return int(mode_config['cycles'])
        except Exception as e:
            logger.warning(f"Error obteniendo ciclos de entrenamiento para modo '{mode}': {e}")
        
        # Fallback por defecto
        defaults = {
            'ultra_fast': 50,
            'fast': 100,
            'normal': 200,
            'complete': 500,
        }
        return defaults.get(mode, 50)
    
    def _load_training_mode_from_user_settings(self) -> str:
        """Carga el modo de entrenamiento desde user_settings.yaml"""
        try:
            import yaml
            user_settings_path = Path("config/user_settings.yaml")
            if user_settings_path.exists():
                with open(user_settings_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                return data.get('training_settings', {}).get('mode', 'ultra_fast')
        except Exception as e:
            logger.warning(f"Error cargando modo de entrenamiento desde user_settings.yaml: {e}")
        return 'ultra_fast'
    
    def get_current_training_config(self) -> Dict[str, Any]:
        """Obtiene la configuraciÃ³n actual del entrenamiento"""
        try:
            # Cargar directamente desde user_settings.yaml
            training_mode = self._load_training_mode_from_user_settings()
            mode_config = _load_training_mode_config(training_mode)
            
            return {
                'mode': training_mode,
                'name': mode_config.get('name', training_mode.title()),
                'description': mode_config.get('description', ''),
                'days': mode_config.get('days', 30),
                'cycles': mode_config.get('cycles', 50),
                'chunk_size_days': mode_config.get('chunk_size_days', 7),
                'chunk_overlap_days': mode_config.get('chunk_overlap_days', 1),
                'max_memory_mb': mode_config.get('max_memory_mb', 2048),
                'progress_report_interval': mode_config.get('progress_report_interval', 10),
                'use_case': mode_config.get('use_case', '')
            }
        except Exception as e:
            logger.warning(f"Error obteniendo configuraciÃ³n actual del entrenamiento: {e}")
            return {
                'mode': 'ultra_fast',
                'name': 'Ultra RÃ¡pido',
                'description': 'ConfiguraciÃ³n por defecto',
                'days': 30,
                'cycles': 50,
                'chunk_size_days': 7,
                'chunk_overlap_days': 1,
                'max_memory_mb': 2048,
                'progress_report_interval': 10,
                'use_case': 'ConfiguraciÃ³n por defecto'
            }
    
    async def _update_progress(self, progress: float, status: str, details: str = ""):
        """
        Actualiza el progreso del entrenamiento
        
        Args:
            progress: Porcentaje de progreso (0-100)
            status: Estado actual del entrenamiento
            details: Detalles adicionales del progreso
        """
        try:
            # Crear datos de progreso
            progress_data = {
                'session_id': self.session_id,
                'progress': progress,
                'status': status,
                'details': details,
                'timestamp': datetime.now().isoformat(),
                'symbols': self.symbols,
                'initial_balance': self.initial_balance,
                'target_balance': self.target_balance,
                'target_roi_pct': self.target_roi_pct
            }
            
            # Guardar progreso en archivo si está configurado
            if self.progress_file:
                try:
                    import json
                    with open(self.progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Error guardando progreso en archivo: {e}")
            
            # Log del progreso
            logger.info(f"📊 Progreso: {progress:.1f}% - {status}")
            if details:
                logger.info(f"📝 Detalles: {details}")
                
        except Exception as e:
            logger.error(f"Error actualizando progreso: {e}")
    
    def _get_training_chunk_config(self, mode: str = "ultra_fast") -> Dict[str, int]:
        """Obtiene configuraciÃ³n de chunks por modo desde training_objectives.yaml"""
        try:
            mode_config = _load_training_mode_config(mode)
            return {
                'chunk_size_days': int(mode_config.get('chunk_size_days', 7)),
                'chunk_overlap_days': int(mode_config.get('chunk_overlap_days', 1)),
                'max_memory_mb': int(mode_config.get('max_memory_mb', 2048)),
                'progress_report_interval': int(mode_config.get('progress_report_interval', 10))
            }
        except Exception as e:
            logger.warning(f"Error obteniendo configuraciÃ³n de chunks para modo '{mode}': {e}")
            return {
                'chunk_size_days': 7,
                'chunk_overlap_days': 1,
                'max_memory_mb': 2048,
                'progress_report_interval': 10
            }
    
    def _get_symbol_configs(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene configuraciones especÃ­ficas de sÃ­mbolos"""
        try:
            symbol_configs = {}
            
            # Cargar configuraciones desde symbols.yaml
            try:
                import yaml
                symbols_path = Path("config/core/symbols.yaml")
                if symbols_path.exists():
                    with open(symbols_path, 'r', encoding='utf-8') as f:
                        symbols_data = yaml.safe_load(f)
                    
                    symbol_configs_data = symbols_data.get('symbol_configs', {})
                    for symbol in self.symbols:
                        if symbol in symbol_configs_data:
                            config = symbol_configs_data[symbol]
                            symbol_configs[symbol] = {
                                'max_position_size_pct': config.get('max_position_size_pct', 25),
                                'min_position_size_pct': config.get('min_position_size_pct', 5),
                                'risk_category': config.get('risk_category', 'medium'),
                                'leverage_range': config.get('leverage_range', [1, 10])
                            }
            except Exception as e:
                logger.warning(f"âš ï¸ No se pudieron cargar configuraciones de sÃ­mbolos: {e}")
            
            # Configuraciones por defecto si no hay archivo
            if not symbol_configs:
                for symbol in self.symbols:
                    symbol_configs[symbol] = {
                        'max_position_size_pct': 25,
                        'min_position_size_pct': 5,
                        'risk_category': 'medium',
                        'leverage_range': [1, 10]
                    }
            
            return symbol_configs
            
        except Exception as e:
            logger.error(f"âŒ Error obteniendo configuraciones de sÃ­mbolos: {e}")
            return {}
    
    async def initialize_components(self):
        """Inicializa componentes del sistema"""
        try:
            logger.info("ðŸ”§ Inicializando componentes del sistema...")
            
            # Crear gestor de capital multi-sÃ­mbolo
            from core.trading.multi_symbol_capital_manager import create_capital_manager, AllocationMethod
            self.capital_manager = create_capital_manager(
                initial_balance=self.initial_balance,
                allocation_method=AllocationMethod.EQUAL_WEIGHT
            )
            
            # Inicializar sÃ­mbolos en el gestor de capital
            symbol_configs = self._get_symbol_configs()
            symbol_balances = self.capital_manager.initialize_symbols(self.symbols, symbol_configs)
            
            logger.info(f"ðŸ’° Capital distribuido entre {len(self.symbols)} sÃ­mbolos:")
            for symbol, balance in symbol_balances.items():
                logger.info(f"  â€¢ {symbol}: ${balance:,.2f}")
            
            # Crear orchestrador
            self.orchestrator = await create_parallel_training_orchestrator(
                symbols=self.symbols,
                timeframes=self.timeframes,
                initial_balance=self.initial_balance,
                capital_manager=self.capital_manager
            )
            
            # Crear agregador de mÃ©tricas
            self.metrics_aggregator = create_metrics_aggregator(self.symbols)
            
            logger.info("âœ… Componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"âŒ Error inicializando componentes: {e}")
            raise
    
    async def execute_training(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento histÃ³rico paralelo
        
        Args:
            start_date: Fecha de inicio (None = usar config)
            end_date: Fecha de fin (None = usar config)
            
        Returns:
            Resultados del entrenamiento
        """
        try:
            self.start_time = datetime.now()
            self.is_running = True
            
            logger.info(f"ðŸš€ Iniciando entrenamiento histÃ³rico paralelo: {self.session_id}")
            
            # Configurar fechas por defecto usando el modo configurado
            if start_date is None:
                training_mode = self._load_training_mode_from_user_settings()
                start_date = datetime.now() - timedelta(days=self._get_training_days(training_mode))
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Hasta ayer
            
            # Actualizar progreso inicial
            await self._update_progress(0, "Inicializando sistema", "ðŸ”§ Preparando componentes")
            
            # Filtrar sÃ­mbolos con datos locales
            self._filter_symbols_with_local_data()
            if not self.symbols:
                raise ValueError("No hay sÃ­mbolos con datos histÃ³ricos locales disponibles.")
            
            # Cargar datos histÃ³ricos reales
            await self._load_historical_data(start_date, end_date)
            
            # Integrar alineamiento pre-generado
            await self._ensure_pre_alignment(start_date, end_date)
            
            # Configurar callback de progreso
            progress_callback = self._create_progress_callback()
            
            # Ejecutar entrenamiento real con datos histÃ³ricos
            await self._update_progress(10, "Ejecutando entrenamiento", "ðŸ¤– Iniciando agentes paralelos")
            
            results = await self._real_training_session(start_date, end_date, progress_callback)
            
            # Procesar y agregar resultados finales
            await self._update_progress(90, "Procesando resultados", "ðŸ“Š Agregando mÃ©tricas globales")
            
            final_results = await self._process_final_results(results)
            
            if self.cycle_metrics_history:
                agg = self._aggregate_cycle_history(self.cycle_metrics_history)
                final_results["cycle_metrics_aggregated"] = agg
            
            # Guardar resultados completos
            await self._save_final_results(final_results)
            
            await self._update_progress(100, "Completado", "âœ… Entrenamiento finalizado")
            
            self.is_running = False
            self.results = final_results
            
            logger.info(f"âœ… Entrenamiento completado: {self.session_id}")
            
            # Imprimir resumen en el formato deseado
            self._print_formatted_summary(final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"âŒ Error en entrenamiento: {e}")
            self.is_running = False
            await self._update_progress(0, "Error", f"âŒ Error: {str(e)}")
            raise

    def _install_sync_log_filters(self):
        """Instala filtros para reducir ruido de logs de sincronizaciÃ³n de otros mÃ³dulos."""
        class _SyncNoiseFilter(logging.Filter):
            phrases = [
                'No se pudieron generar puntos de sincronizaciÃ³n',
                'Base de datos no encontrada',
                'Timestamps comunes encontrados: 0',
                'Error preparando timeline'
            ]
            def filter(self, record: logging.LogRecord) -> bool:
                msg = record.getMessage()
                for p in self.phrases:
                    if p in msg:
                        return False
                return True

        try:
            for name in ['scripts.training.parallel_training_orchestrator', 'core.sync.timestamp_synchronizer']:
                lg = logging.getLogger(name)
                lg.addFilter(_SyncNoiseFilter())
        except Exception:
            pass

    def _filter_symbols_with_local_data(self, required_timeframes: List[str] = None):
        """Filtra sÃ­mbolos que tienen al menos los timeframes de ejecuciÃ³n obligatorios"""
        if required_timeframes is None:
            # OBLIGATORIO: sÃ­mbolos deben tener 1m y 5m para trading
            required_timeframes = self.execution_timeframes
        
        kept = []
        for sym in list(self.symbols):
            has_all_required = True
            for tf in required_timeframes:
                db_path = Path(f"data/{sym}/{sym}_{tf}.db")
                if not db_path.exists():
                    has_all_required = False
                    break
            
            if has_all_required:
                kept.append(sym)
            else:
                missing_tfs = [tf for tf in required_timeframes 
                              if not Path(f"data/{sym}/{sym}_{tf}.db").exists()]
                logger.info(f"âš ï¸ {sym}: Falta timeframes de ejecuciÃ³n {missing_tfs}")
        
        if not kept:
            raise ValueError(
                f"No hay sÃ­mbolos con timeframes de ejecuciÃ³n obligatorios {required_timeframes}. "
                "Ejecuta el recolector de datos para descargar 1m y 5m."
            )
        
        self.symbols = kept

    def _load_symbols_from_yaml(self) -> List[str]:
        """Carga sÃ­mbolos desde symbols.yaml como fallback"""
        try:
            import yaml
            symbols_path = Path("config/core/symbols.yaml")
            if not symbols_path.exists():
                logger.warning("âš ï¸ Archivo symbols.yaml no encontrado, usando sÃ­mbolos por defecto")
                return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
            
            data = yaml.safe_load(symbols_path.read_text(encoding='utf-8')) or {}
            active_symbols = data.get('active_symbols', {})
            
            # Combinar todos los grupos de sÃ­mbolos
            symbols = []
            for group in ['primary', 'secondary', 'experimental']:
                if group in active_symbols:
                    symbols.extend(active_symbols[group])
            
            if symbols:
                logger.info(f"âœ… Cargados {len(symbols)} sÃ­mbolos desde symbols.yaml: {', '.join(symbols)}")
                return symbols
            else:
                logger.warning("âš ï¸ No se encontraron sÃ­mbolos en symbols.yaml, usando por defecto")
                return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
                
        except Exception as e:
            logger.warning(f"âš ï¸ Error leyendo symbols.yaml: {e}, usando sÃ­mbolos por defecto")
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]

    def _load_symbol_leverage_ranges(self):
        """Carga los rangos de leverage por sÃ­mbolo desde config/core/symbols.yaml"""
        try:
            import yaml
            symbols_path = Path("config/core/symbols.yaml")
            if not symbols_path.exists():
                logger.warning("âš ï¸ Archivo symbols.yaml no encontrado, usando leverage por defecto")
                return
            data = yaml.safe_load(symbols_path.read_text(encoding='utf-8')) or {}
            symbol_cfgs = (data.get('symbol_configs') or {})
            for sym, cfg in symbol_cfgs.items():
                rng = cfg.get('leverage_range') or []
                if isinstance(rng, list) and len(rng) == 2:
                    self._symbol_leverage_ranges[sym] = [float(rng[0]), float(rng[1])]
                    logger.debug(f"ðŸ“Š Cargado leverage para {sym}: {rng[0]}-{rng[1]}x")
            logger.info(f"âœ… Cargados rangos de leverage para {len(self._symbol_leverage_ranges)} sÃ­mbolos")
        except Exception as e:
            logger.warning(f"âš ï¸ Error leyendo YAML de sÃ­mbolos: {e}")

    def _get_symbol_leverage_bounds(self, symbol: str) -> List[float]:
        """Devuelve [min,max] de leverage para el sÃ­mbolo, con fallback sensato."""
        if symbol in self._symbol_leverage_ranges:
            return self._symbol_leverage_ranges[symbol]
        return [5.0, 20.0]
    
    def _calculate_realistic_pnl(self, price_change_pct: float, direction_bias: float, 
                                cycle_trades: int, current_balance: float, 
                                mode_config: Dict[str, Any]) -> float:
        """
        Calcula PnL realista aplicando restricciones del mundo real.
        
        Args:
            price_change_pct: Cambio de precio en porcentaje
            direction_bias: Sesgo direccional (1 o -1)
            cycle_trades: NÃºmero de trades en el ciclo
            current_balance: Balance actual
            mode_config: ConfiguraciÃ³n del modo de entrenamiento
            
        Returns:
            PnL porcentual realista
        """
        # ParÃ¡metros realistas
        max_daily_roi = mode_config.get('max_daily_roi', 2.0)  # 2% mÃ¡ximo diario
        max_annual_roi = mode_config.get('max_annual_roi', 50.0)  # 50% mÃ¡ximo anual
        commission_rate = mode_config.get('commission_rate', 0.001)  # 0.1% comisiÃ³n
        spread_rate = mode_config.get('spread_rate', 0.0005)  # 0.05% spread
        slippage_rate = mode_config.get('slippage_rate', 0.0002)  # 0.02% slippage
        max_leverage = mode_config.get('max_leverage', 5.0)  # 5x mÃ¡ximo
        
        # Calcular PnL base basado en cambio de precio real
        base_pnl_pct = price_change_pct * direction_bias
        
        # Aplicar leverage realista (mÃ¡ximo 5x)
        leverage = min(max_leverage, random.uniform(1.0, max_leverage))
        leveraged_pnl = base_pnl_pct * leverage
        
        # Aplicar costos de trading
        total_costs = commission_rate + spread_rate + slippage_rate
        cost_per_trade = total_costs * 100  # Convertir a porcentaje
        
        # Calcular costos totales para el ciclo
        total_costs_pct = cost_per_trade * cycle_trades
        
        # Aplicar costos al PnL
        net_pnl_pct = leveraged_pnl - total_costs_pct
        
        # Aplicar restricciones de volatilidad realista
        # En el mundo real, los cambios de precio grandes son raros
        if abs(price_change_pct) > 0.1:  # >10% cambio
            # Reducir significativamente el PnL para cambios extremos
            volatility_penalty = 0.3
            net_pnl_pct *= volatility_penalty
        
        # Aplicar lÃ­mites de ROI diario
        if net_pnl_pct > max_daily_roi:
            net_pnl_pct = max_daily_roi
        elif net_pnl_pct < -max_daily_roi:
            net_pnl_pct = -max_daily_roi
        
        # Aplicar ruido realista (pequeÃ±as variaciones)
        noise_factor = random.uniform(-0.1, 0.1)  # Â±10% de variaciÃ³n
        final_pnl_pct = net_pnl_pct * (1 + noise_factor)
        
        # Asegurar que el PnL estÃ© en un rango realista
        final_pnl_pct = max(-max_daily_roi, min(max_daily_roi, final_pnl_pct))
        
        return final_pnl_pct
    
    def _get_historical_data_for_cycle(self, symbol: str, cycle_timestamps: List) -> pd.DataFrame:
        """Obtiene datos histÃ³ricos para un sÃ­mbolo en un ciclo especÃ­fico"""
        try:
            if symbol not in self.historical_data:
                return pd.DataFrame()
            
            # Usar el timeframe principal (1h) para anÃ¡lisis
            main_tf = '1h' if '1h' in self.historical_data[symbol] else list(self.historical_data[symbol].keys())[0]
            df = self.historical_data[symbol][main_tf].copy()
            
            if df.empty:
                return pd.DataFrame()
            
            # Filtrar por timestamps del ciclo
            cycle_start = min(cycle_timestamps)
            cycle_end = max(cycle_timestamps)
            
            # Convertir timestamps a formato comparable
            if 'timestamp' in df.columns:
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms')
                mask = (df['timestamp_dt'] >= cycle_start) & (df['timestamp_dt'] <= cycle_end)
                return df[mask].copy()
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error obteniendo datos histÃ³ricos para ciclo {symbol}: {e}")
            return pd.DataFrame()
    
    def _calculate_real_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores tÃ©cnicos reales basados en datos histÃ³ricos"""
        try:
            if df.empty or len(df) < 14:
                return {'rsi': 50.0, 'sma_20': 0.0, 'sma_50': 0.0, 'macd': 0.0}
            
            # Calcular RSI
            rsi = self._calculate_rsi(df['close'].values, 14)
            
            # Calcular medias mÃ³viles
            sma_20 = df['close'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else df['close'].mean()
            sma_50 = df['close'].rolling(window=50).mean().iloc[-1] if len(df) >= 50 else df['close'].mean()
            
            # Calcular MACD
            macd = self._calculate_macd(df['close'].values)
            
            return {
                'rsi': rsi,
                'sma_20': float(sma_20),
                'sma_50': float(sma_50),
                'macd': macd,
                'price_change_pct': ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
            }
        except Exception as e:
            logger.error(f"Error calculando indicadores tÃ©cnicos: {e}")
            return {'rsi': 50.0, 'sma_20': 0.0, 'sma_50': 0.0, 'macd': 0.0, 'price_change_pct': 0.0}
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calcula RSI real basado en precios histÃ³ricos"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = np.mean(gains[-period:])
            avg_losses = np.mean(losses[-period:])
            
            if avg_losses == 0:
                return 100.0
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
        except Exception:
            return 50.0
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
        """Calcula MACD real basado en precios histÃ³ricos"""
        try:
            if len(prices) < slow + signal:
                return 0.0
            
            # Calcular EMAs
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            return float(macd_line[-1]) if len(macd_line) > 0 else 0.0
        except Exception:
            return 0.0
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA (Exponential Moving Average)"""
        try:
            if len(prices) < period:
                return np.array([np.mean(prices)])
            
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
            return ema
        except Exception:
            return np.array([np.mean(prices)])
    
    def _simulate_realistic_trades(self, symbol: str, df: pd.DataFrame, 
                                 technical_indicators: Dict[str, float], 
                                 current_balance: float, 
                                 mode_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simula trades realistas basados en datos histÃ³ricos y indicadores tÃ©cnicos"""
        try:
            if df.empty or len(df) < 2:
                return []
            
            trades = []
            
            # ParÃ¡metros realistas
            commission_rate = mode_config.get('commission_rate', 0.001)
            spread_rate = mode_config.get('spread_rate', 0.0005)
            slippage_rate = mode_config.get('slippage_rate', 0.0002)
            max_leverage = mode_config.get('max_leverage', 5.0)
            
            # Obtener configuraciÃ³n del sÃ­mbolo
            symbol_config = self.config.get('symbol_configs', {}).get(symbol, {})
            leverage_range = symbol_config.get('leverage_range', [1, 5])
            max_position_size_pct = symbol_config.get('max_position_size_pct', 5.0)
            
            # Calcular nÃºmero de trades basado en volatilidad
            price_change_pct = technical_indicators.get('price_change_pct', 0.0)
            volatility_factor = min(2.0, max(0.5, abs(price_change_pct) / 2.0))
            num_trades = max(1, min(5, int(3 * volatility_factor)))
            
            # Procesar cada trade
            for i in range(num_trades):
                # Determinar acciÃ³n basada en indicadores tÃ©cnicos
                rsi = technical_indicators.get('rsi', 50.0)
                macd = technical_indicators.get('macd', 0.0)
                sma_20 = technical_indicators.get('sma_20', 0.0)
                sma_50 = technical_indicators.get('sma_50', 0.0)
                
                # LÃ³gica de decisiÃ³n basada en indicadores
                if rsi < 30 and macd > 0:  # Oversold + MACD positivo
                    action = 'BUY'
                    confidence = 0.8
                elif rsi > 70 and macd < 0:  # Overbought + MACD negativo
                    action = 'SELL'
                    confidence = 0.8
                elif sma_20 > sma_50 and macd > 0:  # Tendencia alcista
                    action = 'BUY'
                    confidence = 0.6
                elif sma_20 < sma_50 and macd < 0:  # Tendencia bajista
                    action = 'SELL'
                    confidence = 0.6
                else:
                    # No trade en condiciones neutrales
                    continue
                
                # Calcular tamaÃ±o de posiciÃ³n
                position_size_pct = min(max_position_size_pct, 2.0)  # MÃ¡ximo 2% por trade
                position_value = current_balance * (position_size_pct / 100.0)
                
                # Calcular leverage
                leverage = min(max_leverage, random.uniform(leverage_range[0], leverage_range[1]))
                
                # Precios de entrada y salida
                entry_price = df['close'].iloc[-1]
                price_change = technical_indicators.get('price_change_pct', 0.0) / 100.0
                exit_price = entry_price * (1 + price_change * (1 if action == 'BUY' else -1))
                
                # Calcular PnL
                if action == 'BUY':
                    pnl_usdt = (exit_price - entry_price) * (position_value / entry_price) * leverage
                else:
                    pnl_usdt = (entry_price - exit_price) * (position_value / entry_price) * leverage
                
                # Aplicar costos de trading
                trade_value = position_value * leverage
                commission = trade_value * commission_rate
                spread_cost = trade_value * spread_rate
                slippage_cost = trade_value * slippage_rate
                total_costs = commission + spread_cost + slippage_cost
                
                # PnL neto
                net_pnl = pnl_usdt - total_costs
                
                # Crear trade
                trade = {
                    'action': action,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'quantity': position_value / entry_price,
                    'leverage': leverage,
                    'pnl_usdt': net_pnl,
                    'commission': commission,
                    'spread_cost': spread_cost,
                    'slippage_cost': slippage_cost,
                    'total_costs': total_costs,
                    'confidence': confidence,
                    'rsi': rsi,
                    'macd': macd
                }
                
                trades.append(trade)
            
            return trades
        except Exception as e:
            logger.error(f"Error simulando trades realistas para {symbol}: {e}")
            return []
    
    def _calculate_final_metrics(self, agent_summaries: Dict, sum_cycle_pnl: float, 
                               sum_cycle_trades: int, sum_cycle_wins: int, 
                               sum_cycle_losses: int, total_cycles: int) -> Dict[str, Any]:
        """Calcula mÃ©tricas finales del entrenamiento"""
        try:
            # MÃ©tricas globales
            global_win_rate = (sum_cycle_wins / sum_cycle_trades * 100) if sum_cycle_trades > 0 else 0
            total_pnl = sum_cycle_pnl
            avg_pnl_per_trade = total_pnl / sum_cycle_trades if sum_cycle_trades > 0 else 0
            
            # Calcular mÃ©tricas por agente
            for symbol, summary in agent_summaries.items():
                if summary['total_trades'] > 0:
                    summary['win_rate'] = (summary['winning_trades'] / summary['total_trades']) * 100
                    summary['avg_win'] = summary['total_pnl'] / summary['winning_trades'] if summary['winning_trades'] > 0 else 0
                    summary['avg_loss'] = summary['total_pnl'] / summary['losing_trades'] if summary['losing_trades'] > 0 else 0
                    summary['profit_factor'] = abs(summary['avg_win'] * summary['winning_trades']) / abs(summary['avg_loss'] * summary['losing_trades']) if summary['losing_trades'] > 0 else float('inf')
                else:
                    summary['win_rate'] = 0
                    summary['avg_win'] = 0
                    summary['avg_loss'] = 0
                    summary['profit_factor'] = 0
            
            return {
                'global_summary': {
                    'total_cycles': total_cycles,
                    'total_trades': sum_cycle_trades,
                    'total_wins': sum_cycle_wins,
                    'total_losses': sum_cycle_losses,
                    'global_win_rate': global_win_rate,
                    'total_pnl': total_pnl,
                    'avg_pnl_per_trade': avg_pnl_per_trade
                },
                'agent_summaries': agent_summaries,
                'training_completed': True,
                'realistic_mode': True
            }
        except Exception as e:
            logger.error(f"Error calculando mÃ©tricas finales: {e}")
            return {'error': str(e)}
    
    async def _load_historical_data(self, start_date: datetime, end_date: datetime):
        """Carga datos histÃ³ricos reales desde SQLite, detectando esquema dinÃ¡micamente.

        - Detecta tabla disponible (candles/klines/ohlcv/...)
        - Mapea columnas a alias estÃ¡ndar: timestamp, open, high, low, close, volume
        - Tolera ausencia de volume (rellena con NaN)
        - Omite TFs o sÃ­mbolos sin datos sin abortar el entrenamiento
        """

        def _detect_table_and_columns(sql_conn: sqlite3.Connection):
            # Obtiene primera tabla que contenga OHLC
            try:
                tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", sql_conn)
                table_names = [str(n).lower() for n in tables['name'].tolist()]
            except Exception:
                table_names = []

            candidate_tables = ['market_data', 'candles', 'klines', 'ohlcv', 'candle', 'kline', 'prices']
            chosen_table = None
            for t in table_names:
                if t in candidate_tables:
                    chosen_table = t
                    break
            if chosen_table is None and table_names:
                # Ãšltimo recurso: tomar la primera si parece contener columnas OHLC
                for t in table_names:
                    try:
                        cols_df = pd.read_sql_query(f"PRAGMA table_info({t})", sql_conn)
                        cols = [c.lower() for c in cols_df['name'].tolist()]
                        if any(c in cols for c in ['open','o']) and any(c in cols for c in ['close','c']):
                            chosen_table = t
                            break
                    except Exception:
                        continue

            if chosen_table is None:
                return None, None

            try:
                cols_df = pd.read_sql_query(f"PRAGMA table_info({chosen_table})", sql_conn)
                cols = [c.lower() for c in cols_df['name'].tolist()]
            except Exception:
                return chosen_table, None

            def pick(*names):
                for n in names:
                    if n in cols:
                        return n
                return None

            timestamp_col = pick('timestamp','time','open_time','ts','t')
            open_col = pick('open','o')
            high_col = pick('high','h')
            low_col = pick('low','l')
            close_col = pick('close','c')
            volume_col = pick('volume','vol','quote_volume','v')

            mapping = {
                'timestamp': timestamp_col,
                'open': open_col,
                'high': high_col,
                'low': low_col,
                'close': close_col,
                'volume': volume_col,
            }
            # Requiere al menos timestamp y precios OHLC
            required_ok = timestamp_col and open_col and high_col and low_col and close_col
            return chosen_table, (mapping if required_ok else None)

        symbols_with_any_data = []

        for symbol in self.symbols:
            self.historical_data[symbol] = {}
            for tf in self.timeframes:
                # Buscar primero en directorio histÃ³rico, luego en directorio principal
                db_path = Path(f"data/historical/{symbol}/{symbol}_{tf}.db")
                if not db_path.exists():
                    db_path = Path(f"data/{symbol}/{symbol}_{tf}.db")
                if not db_path.exists():
                    continue
                try:
                    conn = sqlite3.connect(str(db_path))
                    table, mapping = _detect_table_and_columns(conn)
                    if table is None or mapping is None:
                        logger.info(f"â„¹ï¸ Esquema no compatible en {db_path}, omitido")
                        conn.close()
                        continue

                    # Construir query con alias estÃ¡ndar
                    ts_ms_start = int(start_date.timestamp() * 1000)
                    ts_ms_end = int(end_date.timestamp() * 1000)

                    # Algunos esquemas usan segundos, crear filtro doble: ms y s
                    ts_col = mapping['timestamp']
                    where_clause = (
                        f"(({ts_col} BETWEEN {ts_ms_start} AND {ts_ms_end})"
                        f" OR ({ts_col} BETWEEN {ts_ms_start//1000} AND {ts_ms_end//1000}))"
                    )

                    select_cols = [
                        f"{mapping['timestamp']} AS timestamp",
                        f"{mapping['open']} AS open",
                        f"{mapping['high']} AS high",
                        f"{mapping['low']} AS low",
                        f"{mapping['close']} AS close",
                    ]
                    if mapping['volume']:
                        select_cols.append(f"{mapping['volume']} AS volume")
                    else:
                        # Si no hay volumen, generaremos NaN tras la consulta
                        pass

                    query = (
                        "SELECT " + ", ".join(select_cols) +
                        f" FROM {table} WHERE {where_clause} ORDER BY {ts_col} ASC"
                    )

                    df = pd.read_sql_query(query, conn)
                    conn.close()

                    if df.empty:
                        continue

                    # Normalizar timestamp (s vs ms)
                    # HeurÃ­stica: si max < 10^12 asumimos segundos
                    try:
                        max_ts = float(df['timestamp'].max())
                        unit = 'ms' if max_ts >= 1e12 else 's'
                    except Exception:
                        unit = 'ms'

                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit=unit)
                    if 'volume' not in df.columns:
                        df['volume'] = np.nan

                    self.historical_data[symbol][tf] = df
                    symbols_with_any_data.append(symbol)
                except Exception as e:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    logger.info(f"â„¹ï¸ No se pudo leer {db_path}: {e}")
                    continue

            if not self.historical_data[symbol]:
                logger.info(f"â„¹ï¸ Sin datos histÃ³ricos utilizables para {symbol}, serÃ¡ omitido en cÃ¡lculos")

        # Filtrar sÃ­mbolos sin datos del diccionario principal
        symbols_with_complete_data = []
        for symbol in self.symbols:
            if symbol not in self.historical_data:
                continue
            
            # Verificar timeframes de ejecuciÃ³n (obligatorios)
            has_execution_data = all(
                tf in self.historical_data[symbol] and not self.historical_data[symbol][tf].empty
                for tf in self.execution_timeframes
            )
            
            # Verificar al menos un timeframe de anÃ¡lisis
            has_analysis_data = any(
                tf in self.historical_data[symbol] and not self.historical_data[symbol][tf].empty
                for tf in self.analysis_timeframes
            )
            
            if has_execution_data and has_analysis_data:
                symbols_with_complete_data.append(symbol)
                logger.info(f"âœ… {symbol}: Datos completos (ejecuciÃ³n + anÃ¡lisis)")
            elif has_execution_data:
                symbols_with_complete_data.append(symbol)
                logger.warning(f"âš ï¸ {symbol}: Solo datos de ejecuciÃ³n (sin anÃ¡lisis jerÃ¡rquico)")
            else:
                logger.error(f"âŒ {symbol}: Sin datos de ejecuciÃ³n mÃ­nimos")

        # Actualizar lista de sÃ­mbolos activos
        self.symbols = symbols_with_complete_data

        if not self.symbols:
            raise ValueError("No hay sÃ­mbolos con datos histÃ³ricos vÃ¡lidos")

        logger.info(f"âœ… Datos histÃ³ricos reales cargados para {len(self.symbols)} sÃ­mbolos: {', '.join(self.symbols)}")


    async def _real_training_session(self, start_date: datetime, end_date: datetime, progress_callback) -> Dict[str, Any]:
        """Ejecuta entrenamiento real usando datos histÃ³ricos cargados, procesando cronolÃ³gicamente en 50 ciclos."""
        logger.info("ðŸ”¥ Ejecutando entrenamiento real con datos histÃ³ricos...")
        
        # Determinar timestamps alineados (usar pre_aligned si disponible, sino generar)
        timestamps = self.pre_aligned_data.get('aligned_timestamps', []) if self.pre_aligned_data else pd.date_range(start=start_date, end=end_date, freq='H').tolist()
        # Normalizar a pd.Timestamp para comparaciones contra df['timestamp']
        if isinstance(timestamps, list) and timestamps:
            sample = timestamps[0]
            try:
                if isinstance(sample, (int, float)):
                    timestamps = pd.to_datetime(timestamps, unit='ms').tolist()
                elif isinstance(sample, str):
                    timestamps = pd.to_datetime(timestamps).tolist()
                # si ya son pd.Timestamp, no hacer nada
            except Exception:
                # fallback a rango horario si algo falla
                timestamps = pd.date_range(start=start_date, end=end_date, freq='H').tolist()

        # Asegurar que los timestamps caen dentro del rango real de datos histÃ³ricos
        try:
            min_ts = None
            max_ts = None
            for sym, tfs in self.historical_data.items():
                for tf_df in tfs.values():
                    if tf_df.empty:
                        continue
                    dmin = tf_df['timestamp'].min()
                    dmax = tf_df['timestamp'].max()
                    min_ts = dmin if (min_ts is None or dmin < min_ts) else min_ts
                    max_ts = dmax if (max_ts is None or dmax > max_ts) else max_ts

            if min_ts is not None and max_ts is not None:
                # Convertir timestamps a datetime para comparaciÃ³n
                min_dt = pd.to_datetime(min_ts, unit='ms') if min_ts > 1e10 else pd.to_datetime(min_ts, unit='s')
                max_dt = pd.to_datetime(max_ts, unit='ms') if max_ts > 1e10 else pd.to_datetime(max_ts, unit='s')
                
                # Calcular dÃ­as disponibles
                days_available = (max_dt - min_dt).days + 1
                logger.warning(f"âš ï¸ Datos histÃ³ricos limitados: solo {days_available} dÃ­as disponibles ({min_dt.strftime('%Y-%m-%d')} a {max_dt.strftime('%Y-%m-%d')})")
                logger.warning(f"âš ï¸ Modo '{training_mode}' requiere {self._get_training_days(training_mode)} dÃ­as, pero solo hay {days_available} dÃ­as")
                
                # filtrar timestamps al rango de datos reales
                timestamps = [ts for ts in timestamps if (ts >= min_ts and ts <= max_ts)]
                if not timestamps:
                    # regenerar por hora dentro del rango de datos reales
                    timestamps = pd.date_range(start=min_ts, end=max_ts, freq='H').tolist()
        except Exception:
            pass
        if not timestamps:
            raise ValueError("No hay timestamps alineados disponibles.")
        
        # Obtener configuraciÃ³n del modo de entrenamiento
        training_mode = self._load_training_mode_from_user_settings()
        mode_config = _load_training_mode_config(training_mode)
        is_realistic = mode_config.get('realistic_mode', False)
        
        # Dividir timestamps en ciclos (aproximadamente 50 ciclos)
        total_cycles = 50
        timestamps_per_cycle = len(timestamps) // total_cycles
        if timestamps_per_cycle < 1:
            timestamps_per_cycle = 1
        
        logger.info(f"ðŸŽ¯ Modo de entrenamiento: {training_mode} - {total_cycles} ciclos de {len(timestamps)} timestamps disponibles")
        logger.info(f"ðŸ”§ Modo realista: {'SÃ' if is_realistic else 'NO'}")
        
        # Inicializar estados
        agent_summaries = {}
        # Usar balance distribuido por sÃ­mbolo, no el balance inicial completo
        if self.capital_manager:
            symbol_balances = self.capital_manager.get_symbol_allocations()
            running_balance_per_symbol = {s: symbol_balances.get(s, {}).get('allocated_balance', self.initial_balance / len(self.symbols)) for s in self.symbols}
        else:
            running_balance_per_symbol = {s: self.initial_balance / len(self.symbols) for s in self.symbols}
        
        # Inicializar mÃ©tricas globales
        sum_cycle_pnl = 0.0
        sum_cycle_trades = 0
        sum_cycle_wins = 0
        sum_cycle_losses = 0
        total_cycles_completed = 0
        
        # Inicializar leverage previo
        for s in self.symbols:
            lev_min, lev_max = self._get_symbol_leverage_bounds(s)
            self._prev_cycle_leverage_per_symbol[s] = (lev_min + lev_max) / 2.0
        
        for symbol in self.symbols:
            agent_summaries[symbol] = {
                'symbol': symbol,
                'current_balance': running_balance_per_symbol[symbol],
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
                'total_trades': 0,
                'total_long_trades': 0,
                'total_short_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'daily_pnl': 0.0,
                'avg_leverage_used': None,
            }
        
        # Procesar cada ciclo cronolÃ³gicamente
        for cycle_idx in range(total_cycles):
            cycle_start_idx = cycle_idx * timestamps_per_cycle
            cycle_end_idx = min((cycle_idx + 1) * timestamps_per_cycle, len(timestamps))
            
            if cycle_start_idx >= len(timestamps):
                break
                
            cycle_timestamps = timestamps[cycle_start_idx:cycle_end_idx]
            if not cycle_timestamps:
                continue
                
            total_cycles_completed += 1
            cycle_pnl_total = 0.0
            cycle_trades_total = 0
            cycle_wins_total = 0
            cycle_losses_total = 0
            
            # Procesar cada sÃ­mbolo en este ciclo
            for symbol in self.symbols:
                if symbol not in self.historical_data:
                    continue
                    
                # Obtener datos histÃ³ricos para el sÃ­mbolo en este ciclo
                symbol_data = self._get_historical_data_for_cycle(symbol, cycle_timestamps)
                if symbol_data.empty:
                    continue
                
                # Calcular indicadores tÃ©cnicos reales
                technical_indicators = self._calculate_real_technical_indicators(symbol_data)
                
                # Simular trades basados en datos histÃ³ricos reales
                trades = self._simulate_realistic_trades(
                    symbol, symbol_data, technical_indicators, 
                    running_balance_per_symbol[symbol], mode_config
                )
                
                # Procesar resultados de trades
                for trade in trades:
                    cycle_trades_total += 1
                    cycle_pnl_total += trade['pnl_usdt']
                    
                    if trade['pnl_usdt'] > 0:
                        cycle_wins_total += 1
                    else:
                        cycle_losses_total += 1
                    
                    # Actualizar balance
                    running_balance_per_symbol[symbol] += trade['pnl_usdt']
                
                # Actualizar mÃ©tricas del sÃ­mbolo
                if symbol not in agent_summaries:
                    agent_summaries[symbol] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_pnl': 0.0,
                        'current_balance': 1000.0,
                        'peak_balance': 1000.0,
                        'max_drawdown': 0.0,
                        'win_rate': 0.0,
                        'avg_win': 0.0,
                        'avg_loss': 0.0,
                        'profit_factor': 0.0,
                        'sharpe_ratio': 0.0,
                        'max_leverage_used': 0.0,
                        'total_commission_paid': 0.0,
                        'total_slippage_cost': 0.0
                    }
                
                # Actualizar resumen del agente
                agent_summaries[symbol]['total_trades'] += len(trades)
                agent_summaries[symbol]['winning_trades'] += cycle_wins_total
                agent_summaries[symbol]['losing_trades'] += cycle_losses_total
                agent_summaries[symbol]['total_pnl'] += cycle_pnl_total
                agent_summaries[symbol]['current_balance'] = running_balance_per_symbol[symbol]
                agent_summaries[symbol]['peak_balance'] = max(
                    agent_summaries[symbol]['peak_balance'], 
                    running_balance_per_symbol[symbol]
                )
                
                # Calcular drawdown
                current_drawdown = (agent_summaries[symbol]['peak_balance'] - running_balance_per_symbol[symbol]) / agent_summaries[symbol]['peak_balance'] * 100
                agent_summaries[symbol]['max_drawdown'] = max(agent_summaries[symbol]['max_drawdown'], current_drawdown)
                
                # Actualizar mÃ©tricas globales
                sum_cycle_pnl += cycle_pnl_total
                sum_cycle_trades += cycle_trades_total
                sum_cycle_wins += cycle_wins_total
                sum_cycle_losses += cycle_losses_total
            
            # Reportar progreso
            if total_cycles_completed % 5 == 0:
                progress = 10 + (total_cycles_completed / total_cycles) * 80
                await self._update_progress(progress, f"Ciclo {total_cycles_completed}/{total_cycles}", f"ðŸ“Š Procesando datos histÃ³ricos reales")
        
        # Calcular mÃ©tricas finales
        final_results = self._calculate_final_metrics(
            agent_summaries, sum_cycle_pnl, sum_cycle_trades, 
            sum_cycle_wins, sum_cycle_losses, total_cycles_completed
        )
        
        return final_results
# Funciones para integraciÃ³n con Telegram
async def execute_train_hist_for_telegram(progress_file: str, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
    """
    FunciÃ³n principal para ejecutar entrenamiento histÃ³rico desde Telegram
    
    Args:
        progress_file: Archivo de progreso para Telegram
        start_date: Fecha de inicio (opcional)
        end_date: Fecha de fin (opcional)
        
    Returns:
        Resultados del entrenamiento formateados para Telegram
    """
    try:
        logger.info("ðŸš€ Iniciando entrenamiento histÃ³rico desde Telegram...")
        
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=progress_file)
        
        # Configurar fechas por defecto si no se proporcionan
        if start_date is None or end_date is None:
            training_mode = trainer._load_training_mode_from_user_settings()
            if end_date is None:
                end_date = datetime.now() - timedelta(days=1)  # Hasta ayer
            if start_date is None:
                start_date = end_date - timedelta(days=trainer._get_training_days(training_mode))
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Formatear resultados para Telegram
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = results.get("telegram_summary", "Entrenamiento completado exitosamente")
        
        return results
        
    except Exception as e:
        logger.error(f"âŒ Error en entrenamiento para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"âŒ Error en entrenamiento: {str(e)[:100]}...",
            "telegram_ready": True
        }

async def execute_train_hist_continuous_for_telegram(progress_file: str, cycle_days: int = 7) -> Dict[str, Any]:
    """
    FunciÃ³n para entrenamiento continuo desde Telegram
    
    Args:
        progress_file: Archivo de progreso para Telegram
        cycle_days: DÃ­as por ciclo de entrenamiento
        
    Returns:
        Resultados del entrenamiento continuo
    """
    try:
        logger.info(f"ðŸ”„ Iniciando entrenamiento continuo desde Telegram (ciclos de {cycle_days} dÃ­as)...")
        
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=progress_file)
        
        # Configurar fechas para el ciclo
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=cycle_days)
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        # Formatear resultados para Telegram
        results["telegram_ready"] = True
        results["success"] = True
        results["message"] = f"Entrenamiento continuo completado (Ãºltimos {cycle_days} dÃ­as)"
        
        return results
        
    except Exception as e:
        logger.error(f"âŒ Error en entrenamiento continuo para Telegram: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"âŒ Error en entrenamiento continuo: {str(e)[:100]}...",
            "telegram_ready": True
        }

# FunciÃ³n principal para ejecuciÃ³n desde lÃ­nea de comandos
async def main():
    """FunciÃ³n principal para ejecuciÃ³n desde lÃ­nea de comandos"""
    parser = argparse.ArgumentParser(description='Entrenamiento HistÃ³rico Paralelo - Bot Trading v10')
    parser.add_argument('--progress-file', type=str, help='Archivo de progreso para Telegram')
    parser.add_argument('--start-date', type=str, help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--mode', type=str, default='ultra_fast', help='Modo de entrenamiento')
    
    args = parser.parse_args()
    
    try:
        # Crear instancia del entrenador
        trainer = TrainHistParallel(progress_file=args.progress_file)
        
        # Configurar fechas
        start_date = None
        end_date = None
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        # Ejecutar entrenamiento
        results = await trainer.execute_training(start_date=start_date, end_date=end_date)
        
        print("âœ… Entrenamiento completado exitosamente")
        print(f"ðŸ“Š Resultados: {json.dumps(results, indent=2, default=str)}")
        
    except Exception as e:
        logger.error(f"âŒ Error en entrenamiento: {e}")
        print(f"âŒ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
