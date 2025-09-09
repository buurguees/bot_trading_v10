#!/usr/bin/env python3
"""
Script de diagnóstico para la API de Binance
"""

import ccxt
import time
from datetime import datetime

def test_binance_api():
    """Prueba la conectividad con la API de Binance"""
    try:
        print("🔍 Probando conectividad con Binance API...")
        
        # Crear exchange con configuración conservadora
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 30000,  # 30 segundos
            'rateLimit': 1200,  # 1.2 segundos entre llamadas
        })
        
        print(f"✅ Exchange creado: {exchange.name}")
        print(f"📊 Rate limit: {exchange.rateLimit}ms")
        
        # Probar ticker simple
        print("\n🔍 Probando fetch_ticker...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Ticker obtenido: {ticker['symbol']} = ${ticker['last']}")
        
        # Probar datos históricos simples
        print("\n🔍 Probando fetch_ohlcv (últimas 100 velas)...")
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=100)
        print(f"✅ OHLCV obtenido: {len(ohlcv)} velas")
        
        if ohlcv:
            first_candle = ohlcv[0]
            last_candle = ohlcv[-1]
            print(f"   Primera vela: {datetime.fromtimestamp(first_candle[0]/1000)}")
            print(f"   Última vela: {datetime.fromtimestamp(last_candle[0]/1000)}")
            print(f"   Precio: ${last_candle[4]}")
        
        # Probar con parámetros específicos del error
        print("\n🔍 Probando fetch_ohlcv con parámetros específicos...")
        now_ms = exchange.milliseconds()
        start_ms = now_ms - (24 * 60 * 60 * 1000)  # 24 horas atrás
        
        ohlcv_specific = exchange.fetch_ohlcv(
            'BTC/USDT', 
            '1m', 
            since=start_ms, 
            limit=1000
        )
        print(f"✅ OHLCV específico obtenido: {len(ohlcv_specific)} velas")
        
        return True
        
    except ccxt.RateLimitExceeded as e:
        print(f"❌ Rate limit excedido: {e}")
        print("💡 Solución: Esperar más tiempo entre llamadas")
        return False
        
    except ccxt.NetworkError as e:
        print(f"❌ Error de red: {e}")
        print("💡 Solución: Verificar conexión a internet")
        return False
        
    except ccxt.ExchangeError as e:
        print(f"❌ Error de exchange: {e}")
        print("💡 Solución: Verificar parámetros de la llamada")
        return False
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print(f"   Tipo: {type(e).__name__}")
        return False

def test_historical_download():
    """Prueba la descarga de datos históricos como en bot.py"""
    try:
        print("\n🔍 Probando descarga histórica (método bot.py)...")
        
        exchange = ccxt.binance({'enableRateLimit': True})
        
        # Parámetros del error
        symbol = 'BTCUSDT'
        timeframe = '1m'
        years = 5
        
        market_symbol = symbol.replace('USDT', '/USDT')
        now_ms = exchange.milliseconds()
        year_ms = 365 * 24 * 60 * 60 * 1000
        start_ms = now_ms - years * year_ms
        
        print(f"📊 Descargando {years} años de {market_symbol} @ {timeframe}")
        print(f"   Desde: {datetime.fromtimestamp(start_ms/1000)}")
        print(f"   Hasta: {datetime.fromtimestamp(now_ms/1000)}")
        
        # Primera llamada
        print("🔄 Haciendo primera llamada...")
        batch = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, since=start_ms, limit=1000)
        
        if batch:
            print(f"✅ Primera llamada exitosa: {len(batch)} velas")
            print(f"   Primera vela: {datetime.fromtimestamp(batch[0][0]/1000)}")
            print(f"   Última vela: {datetime.fromtimestamp(batch[-1][0]/1000)}")
        else:
            print("❌ Primera llamada falló: sin datos")
            return False
        
        # Esperar un poco
        print("⏳ Esperando 2 segundos...")
        time.sleep(2)
        
        # Segunda llamada
        print("🔄 Haciendo segunda llamada...")
        tf_ms = exchange.parse_timeframe(timeframe) * 1000
        next_since = batch[-1][0] + tf_ms
        
        batch2 = exchange.fetch_ohlcv(market_symbol, timeframe=timeframe, since=next_since, limit=1000)
        
        if batch2:
            print(f"✅ Segunda llamada exitosa: {len(batch2)} velas")
        else:
            print("❌ Segunda llamada falló: sin datos")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en descarga histórica: {e}")
        print(f"   Tipo: {type(e).__name__}")
        return False

def main():
    """Función principal"""
    print("🧪 DIAGNÓSTICO DE API DE BINANCE")
    print("=" * 50)
    
    # Test 1: Conectividad básica
    basic_ok = test_binance_api()
    
    # Test 2: Descarga histórica
    if basic_ok:
        historical_ok = test_historical_download()
    else:
        historical_ok = False
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN")
    print("=" * 50)
    print(f"Conectividad básica: {'✅ OK' if basic_ok else '❌ FALLO'}")
    print(f"Descarga histórica: {'✅ OK' if historical_ok else '❌ FALLO'}")
    
    if not basic_ok:
        print("\n💡 SOLUCIONES:")
        print("1. Verificar conexión a internet")
        print("2. Verificar que Binance API esté disponible")
        print("3. Revisar configuración de proxy/firewall")
    elif not historical_ok:
        print("\n💡 SOLUCIONES:")
        print("1. Reducir el período de descarga (menos años)")
        print("2. Aumentar el delay entre llamadas")
        print("3. Usar un timeframe mayor (1h en lugar de 1m)")
        print("4. Verificar límites de la API de Binance")
    
    return basic_ok and historical_ok

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
