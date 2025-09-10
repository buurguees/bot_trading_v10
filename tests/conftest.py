# -*- coding: utf-8 -*-
"""
Configuración de Pytest
=======================
Fixtures y configuración global para todas las pruebas
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def project_root_path():
    """Ruta del directorio raíz del proyecto"""
    return project_root

@pytest.fixture(scope="session")
def test_data_dir():
    """Directorio temporal para datos de prueba"""
    temp_dir = tempfile.mkdtemp(prefix="bot_trading_test_")
    yield Path(temp_dir)
    # Limpiar después de las pruebas
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="session")
def mock_config():
    """Configuración mock para pruebas"""
    return {
        'bot_settings': {
            'name': 'TestBot',
            'trading_mode': 'test'
        },
        'trading': {
            'mode': 'paper_trading',
            'min_confidence': 0.7
        },
        'data_collection': {
            'real_time': {
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframes': ['1m', '5m']
            }
        }
    }

@pytest.fixture
def mock_database():
    """Base de datos mock para pruebas"""
    mock_db = Mock()
    mock_db.execute_query.return_value = []
    mock_db.execute_update.return_value = True
    return mock_db

@pytest.fixture
def mock_telegram_bot():
    """Bot de Telegram mock para pruebas"""
    mock_bot = Mock()
    mock_bot.send_message.return_value = Mock()
    mock_bot.edit_message_text.return_value = Mock()
    return mock_bot

@pytest.fixture
def mock_ml_model():
    """Modelo de ML mock para pruebas"""
    mock_model = Mock()
    mock_model.predict.return_value = [0.8, 0.7, 0.9]
    mock_model.fit.return_value = None
    mock_model.score.return_value = 0.85
    return mock_model

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Configurar entorno de prueba antes de cada test"""
    # Configurar variables de entorno
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'WARNING'  # Reducir logs en pruebas
    
    yield
    
    # Limpiar después del test
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

@pytest.fixture
def sample_market_data():
    """Datos de mercado de muestra para pruebas"""
    return [
        {
            'symbol': 'BTCUSDT',
            'timestamp': 1640995200000,
            'open': 50000.0,
            'high': 51000.0,
            'low': 49500.0,
            'close': 50500.0,
            'volume': 100.0
        },
        {
            'symbol': 'ETHUSDT',
            'timestamp': 1640995200000,
            'open': 4000.0,
            'high': 4100.0,
            'low': 3950.0,
            'close': 4050.0,
            'volume': 1000.0
        }
    ]

@pytest.fixture
def sample_trading_signal():
    """Señal de trading de muestra para pruebas"""
    return {
        'symbol': 'BTCUSDT',
        'side': 'buy',
        'confidence': 0.85,
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'timestamp': 1640995200000
    }
