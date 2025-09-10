#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para leer operaciones abiertas en Bitget Futuros USDT-M
Integra con Bot Trading v10 Enterprise - Usa credenciales de .env
"""

import os
import sys
from dotenv import load_dotenv
import ccxt
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging (similar a tu proyecto)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_env():
    """Carga credenciales de .env (usa python-dotenv si está instalado)"""
    # Cargar .env desde la raíz del proyecto
    try:
        load_dotenv()
    except Exception:
        pass
    api_key = os.getenv('BITGET_API_KEY')
    secret_key = os.getenv('BITGET_SECRET_KEY')
    passphrase = os.getenv('BITGET_PASSPHRASE')
    
    if not all([api_key, secret_key, passphrase]):
        logger.error("❌ Credenciales incompletas en .env. Verifica BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE.")
        return None
    
    logger.info("✅ Credenciales cargadas correctamente.")
    return {
        'apiKey': api_key,
        'secret': secret_key,
        'password': passphrase,
        'sandbox': False,  # Cambia a True para test
        'enableRateLimit': True,
        'rateLimit': 100,
        'options': {
            'defaultType': 'swap',  # Para USDT-M Futures
            'adjustForTimeDifference': True,
        },
        'timeout': 30000,
    }


def read_open_positions(config):
    """Lee posiciones abiertas en USDT-M Futures usando CCXT."""
    try:
        exchange = ccxt.bitget(config)
        logger.info("🔗 Conectando a Bitget API (USDT-M Futures)...")
        
        # Asegurar mercados cargados
        exchange.load_markets()
        
        # Fetch posiciones abiertas (usa endpoint /api/v2/mix/position/all-position)
        positions = exchange.fetch_positions(symbols=None)  # None para todas las posiciones
        
        if not positions:
            logger.info("ℹ️ No hay posiciones abiertas en USDT-M Futures.")
            return []
        
        logger.info(f"✅ Encontradas {len(positions)} posiciones abiertas.")
        return positions
        
    except ccxt.AuthenticationError as e:
        logger.error(f"❌ Error de autenticación: {e}")
        logger.error("Verifica API Key, Secret y Passphrase en Bitget (permisos 'Read' para Futures).")
        return None
    except ccxt.NetworkError as e:
        logger.error(f"❌ Error de red/conexión: {e}")
        logger.error("Verifica conexión a internet o rate limit.")
        return None
    except Exception as e:
        logger.error(f"❌ Error general: {e}")
        return None


def display_positions(positions):
    """Muestra detalles de las posiciones."""
    if positions is None:
        print("Error obteniendo posiciones.")
        return
    if not positions:
        print("No hay posiciones para mostrar.")
        return
    
    # Asegurar UTF-8 en Windows para emojis/acentos
    try:
        if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("\n📊 OPERACIONES ABIERTAS EN BITGET FUTUROS USDT-M")
    print("=" * 60)
    
    for pos in positions:
        try:
            if pos.get('contracts', 0) > 0:
                print(f"\n🛡️ Símbolo: {pos.get('symbol')}")
                side = pos.get('side')
                print(f"📍 Lado: {'LONG' if side == 'long' else 'SHORT'}")
                print(f"📏 Tamaño: {pos.get('contracts')} contratos")
                print(f"💰 Margen: {float(pos.get('notional', 0)):.2f} USDT")
                print(f"📈 Precio Apertura: {float(pos.get('entryPrice', 0)):.4f}")
                print(f"🎯 PnL No Realizado: {float(pos.get('unrealizedPnl', 0)):.2f} USDT ({float(pos.get('percentage', 0)):.2f}%)")
                print(f"⚖️ Leverage: {float(pos.get('leverage', 0)):.1f}x")
                lp = pos.get('liquidationPrice')
                print(f"💸 Precio Liquidación: {float(lp) if lp is not None else 0:.4f}")
                mm = pos.get('marginMode')
                print(f"🔄 Modo: {mm} (Margin: {mm})")
                ts = pos.get('timestamp') or pos.get('datetime')
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts/1000)
                else:
                    dt = datetime.utcnow()
                print(f"📅 Actualizado: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception:
            continue


def save_to_log(positions):
    """Opcional: Guarda en logs del proyecto."""
    if positions is None:
        return
    log_path = Path("logs/positions.log")
    log_path.parent.mkdir(exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n--- Posiciones abiertas - {datetime.now().isoformat()} ---\n")
        for pos in positions:
            try:
                if pos.get('contracts', 0) > 0:
                    f.write(f"Símbolo: {pos.get('symbol')}, Lado: {pos.get('side')}, PnL: {float(pos.get('unrealizedPnl', 0)):.2f} USDT\n")
            except Exception:
                continue
    logger.info(f"💾 Posiciones guardadas en {log_path}")


if __name__ == "__main__":
    # Cargar config
    config = load_env()
    if not config:
        raise SystemExit(1)
    
    # Leer posiciones
    positions = read_open_positions(config)
    
    if positions is None:
        raise SystemExit(1)
    
    # Mostrar y guardar
    display_positions(positions)
    save_to_log(positions)
    
    print("\n✅ Consulta completada. Si hay errores, verifica credenciales en .env.")


