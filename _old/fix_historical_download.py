#!/usr/bin/env python3
"""
Script para arreglar la descarga de datos históricos
"""

import asyncio
import ccxt
from datetime import datetime, timedelta
from pathlib import Path
import time

async def download_historical_fixed(symbols, timeframe='1m', years=1):
    """Descarga datos históricos con configuración más conservadora"""
    try:
        print(f"🔧 Descargando {years} año(s) de datos para {len(symbols)} símbolos...")
        
        # Crear exchange con configuración más conservadora
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 60000,  # 60 segundos
            'rateLimit': 2000,  # 2 segundos entre llamadas
        })
        
        Path('data/historical').mkdir(parents=True, exist_ok=True)
        
        for symbol in symbols:
            market_symbol = symbol.replace('USDT', '/USDT')
            output_file = Path('data/historical') / f"{symbol}_{timeframe}.csv"
            
            print(f"\n📊 Procesando {symbol}...")
            
            # Calcular fechas
            now_ms = exchange.milliseconds()
            year_ms = 365 * 24 * 60 * 60 * 1000
            start_ms = now_ms - years * year_ms
            
            # Escribir encabezado
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('timestamp,open,high,low,close,volume\n')
            
            since = start_ms
            total_rows = 0
            call_count = 0
            max_calls = 100  # Límite de seguridad
            
            try:
                while since < now_ms and call_count < max_calls:
                    print(f"   Llamada {call_count + 1}: {datetime.fromtimestamp(since/1000)}")
                    
                    batch = exchange.fetch_ohlcv(
                        market_symbol, 
                        timeframe=timeframe, 
                        since=since, 
                        limit=1000
                    )
                    
                    if not batch:
                        print(f"   ⚠️  Sin más datos para {symbol}")
                        break
                    
                    # Escribir datos
                    with open(output_file, 'a', encoding='utf-8') as f:
                        for t, o, h, l, c, v in batch:
                            f.write(f"{t},{o},{h},{l},{c},{v}\n")
                            total_rows += 1
                    
                    # Actualizar since para la siguiente llamada
                    last_ts = batch[-1][0]
                    tf_ms = exchange.parse_timeframe(timeframe) * 1000
                    since = last_ts + tf_ms
                    
                    call_count += 1
                    
                    # Pausa más larga para evitar rate limit
                    print(f"   ⏳ Esperando 3 segundos... (velas: {total_rows})")
                    await asyncio.sleep(3)
                
                print(f"✅ {symbol}: {total_rows} velas guardadas en {output_file}")
                
            except Exception as e:
                print(f"❌ Error con {symbol}: {e}")
                continue
        
        print(f"\n🎉 Descarga completada para {len(symbols)} símbolos")
        
    except Exception as e:
        print(f"❌ Error general: {e}")

async def main():
    """Función principal"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    print("🔧 ARREGLANDO DESCARGA DE DATOS HISTÓRICOS")
    print("=" * 50)
    print("Problema: 5 años de datos 1m = demasiadas llamadas API")
    print("Solución: Reducir a 1 año con pausas más largas")
    print("=" * 50)
    
    await download_historical_fixed(symbols, timeframe='1m', years=1)

if __name__ == "__main__":
    asyncio.run(main())
