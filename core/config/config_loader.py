"""
Wrapper de compatibilidad para el cargador legacy.
Redirige llamadas al nuevo UnifiedConfigManager v2 (config/unified_config.py).
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Wrapper legacy para compatibilidad con el código existente."""

    def __init__(self):
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            try:
                from config.unified_config import get_config_manager
                self._manager = get_config_manager()
            except Exception as e:
                logger.error(f"No se pudo inicializar UnifiedConfigManager v2: {e}")
                self._manager = self._create_fallback()
        return self._manager

    def _create_fallback(self):
        class _Fallback:
            def get_symbols(self): return ["BTCUSDT", "ETHUSDT"]
            def get_timeframes(self): return ["1m", "5m", "15m", "1h", "4h", "1d"]
            def get(self, *_args, default=None, **_kwargs): return default
            def get_telegram_config(self): return {}
            def get_training_objectives(self): return {}
            def get_risk_limits(self): return {}
        return _Fallback()

    # ===== Métodos de compatibilidad mínimos =====
    def get_symbols(self) -> List[str]:
        return self.manager.get_symbols()

    def get_timeframes(self) -> List[str]:
        return self.manager.get_timeframes()

    def get_trading_mode(self) -> str:
        return self.manager.get('trading.mode', 'paper_trading')

    def get_config(self, _file: str, key_path: str = None, default: Any = None) -> Any:
        # Compatibilidad: permite key_path directo contra el manager v2
        if key_path:
            return self.manager.get(key_path, default)
        return default

    # Compatibilidad superficial para llamadas existentes
    def get_main_config(self) -> Dict[str, Any]:
        return {}

    def get_control_config(self) -> Dict[str, Any]:
        return {}

    def get_data_config(self) -> Dict[str, Any]:
        return {}

    def get_agents_config(self) -> Dict[str, Any]:
        return {}

    def get_logging_config(self) -> Dict[str, Any]:
        return {}

    def get_security_config(self) -> Dict[str, Any]:
        return {}

    def get_validation_status(self) -> Dict[str, Any]:
        return {}


# Instancia global para compatibilidad
config_loader = ConfigLoader()

# Funciones de conveniencia
def get_config(config_file: str, key_path: str = None, default: Any = None) -> Any:
    return config_loader.get_config(config_file, key_path, default)

def get_symbols() -> List[str]:
    return config_loader.get_symbols()

def get_timeframes() -> List[str]:
    return config_loader.get_timeframes()

def get_trading_mode() -> str:
    return config_loader.get_trading_mode()
