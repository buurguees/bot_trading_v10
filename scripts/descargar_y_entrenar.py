#!/usr/bin/env python3
"""
📊 Descarga y Entrenamiento Completo - Trading Bot v10
=====================================================

Script que:
1. Descarga 5 años de datos históricos para múltiples timeframes
2. Verifica la calidad y completitud de los datos
3. Entrena el modelo con los datos descargados
4. Ejecuta en modo paper trading

Uso: python scripts/descargar_y_entrenar.py
"""

import asyncio
import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback
import json
import time

# Añadir el directorio del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Imports del bot
from config.config_loader import user_config
from models.adaptive_trainer import adaptive_trainer
from data.collector import data_collector
from data.database import db_manager
from trading.executor import trading_executor
from agents.self_learning_system import SelfLearningSystem

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/descarga_entrenamiento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DescargaYEntrenamiento:
    """Sistema completo de descarga y entrenamiento"""
    
    def __init__(self):
        self.config = user_config
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        self.timeframes = ['1h', '4h', '1d']
        self.years = 5
        self.downloaded_data = {}
        self.training_results = {}
        
        # Configurar para modo paper trading
        self._setup_paper_trading()
        
        logger.info("Sistema de descarga y entrenamiento inicializado")
    
    def _setup_paper_trading(self):
        """Configura el bot para modo paper trading"""
        try:
            self.config.set_value(['trading', 'mode'], 'paper_trading')
            self.config.set_value(['bot_settings', 'features', 'auto_trading'], True)
            self.config.set_value(['bot_settings', 'features', 'auto_retraining'], True)
            
            logger.info("Configuración de paper trading aplicada")
        except Exception as e:
            logger.error(f"Error configurando paper trading: {e}")
    
    async def ejecutar_proceso_completo(self):
        """Ejecuta el proceso completo de descarga y entrenamiento"""
        print("TRADING BOT v10 - DESCARGA Y ENTRENAMIENTO")
        print("=" * 60)
        print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Símbolos: {', '.join(self.symbols)}")
        print(f"Timeframes: {', '.join(self.timeframes)}")
        print(f"Años: {self.years}")
        print()
        
        try:
            # 1. Verificar conectividad
            await self._verificar_conectividad()
            
            # 2. Descargar datos históricos
            await self._descargar_datos_historicos()
            
            # 3. Verificar calidad de datos
            await self._verificar_calidad_datos()
            
            # 4. Entrenar modelos
            await self._entrenar_modelos()
            
            # 5. Iniciar paper trading
            await self._iniciar_paper_trading()
            
            # 6. Monitorear sistema
            await self._monitorear_sistema()
            
        except KeyboardInterrupt:
            logger.info("Proceso interrumpido por usuario")
            await self._limpiar_recursos()
        except Exception as e:
            logger.error(f"Error crítico: {e}")
            logger.error(traceback.format_exc())
            await self._limpiar_recursos()
    
    async def _verificar_conectividad(self):
        """Verifica conectividad con APIs"""
        print("VERIFICANDO CONECTIVIDAD")
        print("-" * 30)
        
        try:
            # Verificar collector
            collector_health = await data_collector.health_check()
            if collector_health.get('rest_api_ok'):
                print("   [OK] API REST funcionando")
            else:
                print("   [ERROR] API REST no disponible")
                raise Exception("API REST no disponible")
            
            # Verificar base de datos
            db_stats = db_manager.get_database_stats()
            print(f"   [OK] Base de datos: {db_stats.get('file_size_mb', 0):.2f} MB")
            
            # Verificar componentes ML
            trainer_health = await adaptive_trainer.health_check()
            if trainer_health.get('status') == 'healthy':
                print("   [OK] Sistema ML funcionando")
            else:
                print("   [ERROR] Sistema ML con problemas")
                raise Exception("Sistema ML no disponible")
            
            print("   [OK] Conectividad verificada")
            print()
            
        except Exception as e:
            logger.error(f"Error verificando conectividad: {e}")
            raise
    
    async def _descargar_datos_historicos(self):
        """Descarga 5 años de datos históricos"""
        print("DESCARGANDO DATOS HISTORICOS")
        print("-" * 35)
        print(f"Descargando {self.years} años de datos...")
        print()
        
        try:
            total_downloaded = 0
            
            for symbol in self.symbols:
                print(f"Descargando {symbol}...")
                symbol_data = {}
                
                for timeframe in self.timeframes:
                    try:
                        print(f"   {timeframe}...", end=" ")
                        
                        # Calcular días basado en timeframe
                        days = self.years * 365
                        
                        # Descargar datos
                        df = await data_collector.fetch_historical_data(
                            symbol, timeframe, days
                        )
                        
                        if not df.empty:
                            # Guardar en base de datos
                            saved_count = await self._save_historical_data(df, symbol, timeframe)
                            symbol_data[timeframe] = {
                                'data': df,
                                'saved_count': saved_count,
                                'date_range': (df.index.min(), df.index.max())
                            }
                            total_downloaded += saved_count
                            print(f"[OK] {saved_count:,} registros")
                        else:
                            print("[ERROR] Sin datos")
                            
                    except Exception as e:
                        print(f"[ERROR] {e}")
                        continue
                
                self.downloaded_data[symbol] = symbol_data
                print(f"   {symbol} completado")
                print()
            
            print(f"TOTAL DESCARGADO: {total_downloaded:,} registros")
            print()
            
            if total_downloaded < 10000:
                raise Exception(f"Datos insuficientes: solo {total_downloaded} registros")
            
        except Exception as e:
            logger.error(f"Error descargando datos históricos: {e}")
            raise
    
    async def _save_historical_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                return 0
            
            # Convertir DataFrame a MarketData objects
            market_data_list = []
            for timestamp, row in df.iterrows():
                market_data = {
                    'symbol': symbol,
                    'timestamp': int(timestamp.timestamp() * 1000),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
                market_data_list.append(market_data)
            
            # Insertar en base de datos
            saved_count = 0
            for data in market_data_list:
                try:
                    success = db_manager.insert_market_data(data)
                    if success:
                        saved_count += 1
                except Exception as e:
                    logger.error(f"Error insertando dato: {e}")
                    continue
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error guardando datos históricos: {e}")
            return 0
    
    async def _verificar_calidad_datos(self):
        """Verifica la calidad y completitud de los datos descargados"""
        print("VERIFICANDO CALIDAD DE DATOS")
        print("-" * 35)
        
        try:
            for symbol in self.symbols:
                print(f"Verificando {symbol}...")
                
                if symbol not in self.downloaded_data:
                    print(f"   [ERROR] Sin datos para {symbol}")
                    continue
                
                symbol_data = self.downloaded_data[symbol]
                
                for timeframe in self.timeframes:
                    if timeframe not in symbol_data:
                        print(f"   [ERROR] Sin datos para {timeframe}")
                        continue
                    
                    data_info = symbol_data[timeframe]
                    df = data_info['data']
                    
                    # Verificar completitud
                    expected_records = self._calcular_registros_esperados(timeframe)
                    actual_records = len(df)
                    completeness = (actual_records / expected_records) * 100
                    
                    # Verificar calidad
                    quality_score = self._calcular_calidad_datos(df)
                    
                    print(f"      {timeframe}: {actual_records:,} registros ({completeness:.1f}% completitud)")
                    print(f"      {timeframe}: Calidad {quality_score:.2f}/10")
                    
                    # Verificar rangos de fechas
                    date_range = data_info['date_range']
                    days_span = (date_range[1] - date_range[0]).days
                    print(f"      {timeframe}: Rango {days_span} días")
                    
                    if completeness < 80:
                        print(f"      [WARN] {timeframe} incompleto ({completeness:.1f}%)")
                    if quality_score < 7:
                        print(f"      [WARN] {timeframe} calidad baja ({quality_score:.2f})")
                
                print()
            
            print("   [OK] Verificación de calidad completada")
            print()
            
        except Exception as e:
            logger.error(f"Error verificando calidad de datos: {e}")
            raise
    
    def _calcular_registros_esperados(self, timeframe: str) -> int:
        """Calcula el número esperado de registros para un timeframe"""
        if timeframe == '1h':
            return self.years * 365 * 24
        elif timeframe == '4h':
            return self.years * 365 * 6
        elif timeframe == '1d':
            return self.years * 365
        else:
            return 0
    
    def _calcular_calidad_datos(self, df: pd.DataFrame) -> float:
        """Calcula un score de calidad para los datos"""
        try:
            score = 10.0
            
            # Verificar valores nulos
            null_count = df.isnull().sum().sum()
            if null_count > 0:
                score -= (null_count / len(df)) * 5
            
            # Verificar valores negativos
            negative_count = (df < 0).sum().sum()
            if negative_count > 0:
                score -= (negative_count / len(df)) * 3
            
            # Verificar volatilidad anómala
            returns = df['close'].pct_change().dropna()
            if len(returns) > 0:
                extreme_returns = (abs(returns) > 0.5).sum()
                if extreme_returns > 0:
                    score -= (extreme_returns / len(returns)) * 2
            
            # Verificar volumen
            zero_volume = (df['volume'] == 0).sum()
            if zero_volume > 0:
                score -= (zero_volume / len(df)) * 1
            
            return max(0, min(10, score))
            
        except Exception:
            return 0.0
    
    async def _entrenar_modelos(self):
        """Entrena los modelos con los datos descargados"""
        print("ENTRENANDO MODELOS")
        print("-" * 25)
        
        try:
            for symbol in self.symbols:
                print(f"Entrenando {symbol}...")
                
                try:
                    # Entrenar modelo inicial
                    result = await adaptive_trainer.train_initial_model(
                        symbol=symbol,
                        days_back=self.years * 365
                    )
                    
                    if result.get('status') == 'completed':
                        self.training_results[symbol] = result
                        accuracy = result.get('validation_accuracy', 0)
                        print(f"   [OK] {symbol}: Accuracy {accuracy:.3f}")
                    else:
                        print(f"   [ERROR] {symbol}: {result.get('error', 'Unknown error')}")
                        raise Exception(f"Error entrenando {symbol}")
                        
                except Exception as e:
                    print(f"   [ERROR] {symbol}: {e}")
                    raise
            
            # Calcular accuracy promedio
            accuracies = [r.get('validation_accuracy', 0) for r in self.training_results.values()]
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
            
            print(f"\nAccuracy promedio: {avg_accuracy:.3f}")
            
            if avg_accuracy < 0.6:
                print(f"[WARN] Accuracy baja: {avg_accuracy:.3f}")
            else:
                print(f"[OK] Accuracy aceptable: {avg_accuracy:.3f}")
            
            print()
            
        except Exception as e:
            logger.error(f"Error entrenando modelos: {e}")
            raise
    
    async def _iniciar_paper_trading(self):
        """Inicia el paper trading"""
        print("INICIANDO PAPER TRADING")
        print("-" * 30)
        
        try:
            # Verificar configuración
            trading_mode = self.config.get_value(['trading', 'mode'])
            auto_trading = self.config.get_value(['bot_settings', 'features', 'auto_trading'])
            
            print(f"   Modo de trading: {trading_mode}")
            print(f"   Auto trading: {auto_trading}")
            
            if trading_mode != 'paper_trading':
                print("   [ERROR] No está en modo paper trading")
                raise Exception("Modo de trading incorrecto")
            
            if not auto_trading:
                print("   [ERROR] Auto trading desactivado")
                raise Exception("Auto trading desactivado")
            
            # Inicializar sistema de aprendizaje
            learning_system = SelfLearningSystem()
            await learning_system.initialize()
            
            print("   [OK] Sistema de aprendizaje inicializado")
            print("   [OK] Paper trading activado")
            print()
            
        except Exception as e:
            logger.error(f"Error iniciando paper trading: {e}")
            raise
    
    async def _monitorear_sistema(self):
        """Monitorea el sistema en funcionamiento"""
        print("MONITOREO DEL SISTEMA")
        print("-" * 25)
        print("   El bot está operando en modo paper trading...")
        print("   Aprendiendo continuamente del mercado...")
        print("   Presiona Ctrl+C para detener")
        print()
        
        try:
            cycle_count = 0
            while True:
                # Ejecutar ciclo de trading
                await self._ejecutar_ciclo_trading()
                
                cycle_count += 1
                
                # Mostrar estado cada 10 ciclos
                if cycle_count % 10 == 0:
                    await self._mostrar_estado_actual()
                
                # Esperar entre ciclos
                await asyncio.sleep(60)  # 1 minuto
                
        except KeyboardInterrupt:
            logger.info("Monitoreo interrumpido por usuario")
        except Exception as e:
            logger.error(f"Error en monitoreo: {e}")
    
    async def _ejecutar_ciclo_trading(self):
        """Ejecuta un ciclo de trading"""
        try:
            for symbol in self.symbols:
                # Ejecutar ciclo de trading para cada símbolo
                await trading_executor.execute_trading_cycle(symbol)
                
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
    
    async def _mostrar_estado_actual(self):
        """Muestra el estado actual del sistema"""
        try:
            print(f"\nESTADO ACTUAL - {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 40)
            
            # Verificar trades recientes
            recent_trades = db_manager.get_trades(limit=5)
            if not recent_trades.empty:
                print(f"   Trades recientes: {len(recent_trades)}")
                last_trade = recent_trades.iloc[0]
                print(f"   Último trade: {last_trade['symbol']} {last_trade['side']}")
            else:
                print("   Sin trades recientes")
            
            # Verificar datos de mercado
            latest_data = db_manager.get_latest_market_data('BTCUSDT', 1)
            if not latest_data.empty:
                last_update = latest_data.index[-1]
                hours_ago = (datetime.now() - last_update.tz_localize(None)).total_seconds() / 3600
                print(f"   Datos mercado: {hours_ago:.1f}h atrás")
            
            print()
            
        except Exception as e:
            logger.error(f"Error mostrando estado: {e}")
    
    async def _limpiar_recursos(self):
        """Limpia recursos al finalizar"""
        print("\nLIMPIANDO RECURSOS")
        print("-" * 20)
        
        try:
            # Guardar estado final
            await self._guardar_estado_final()
            
            print("   [OK] Recursos limpiados")
            print("   [OK] Logs guardados en logs/")
            
        except Exception as e:
            logger.error(f"Error limpiando recursos: {e}")
    
    async def _guardar_estado_final(self):
        """Guarda el estado final del proceso"""
        try:
            estado_final = {
                'timestamp': datetime.now().isoformat(),
                'años_descargados': self.years,
                'símbolos': self.symbols,
                'timeframes': self.timeframes,
                'datos_descargados': {
                    symbol: {
                        tf: {
                            'registros': data['saved_count'],
                            'rango_fechas': [
                                data['date_range'][0].isoformat(),
                                data['date_range'][1].isoformat()
                            ]
                        } for tf, data in symbol_data.items()
                    } for symbol, symbol_data in self.downloaded_data.items()
                },
                'resultados_entrenamiento': self.training_results,
                'modo_trading': 'paper_trading'
            }
            
            with open(f'logs/estado_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                json.dump(estado_final, f, indent=2, ensure_ascii=False)
            
            logger.info("Estado final guardado")
            
        except Exception as e:
            logger.error(f"Error guardando estado final: {e}")

async def main():
    """Función principal"""
    descarga_entrenamiento = DescargaYEntrenamiento()
    await descarga_entrenamiento.ejecutar_proceso_completo()

if __name__ == "__main__":
    print("TRADING BOT v10 - DESCARGA Y ENTRENAMIENTO")
    print("=" * 60)
    print("Este script:")
    print("1. Descargará 5 años de datos históricos")
    print("2. Verificará la calidad de los datos")
    print("3. Entrenará los modelos ML")
    print("4. Iniciará paper trading")
    print("5. Monitoreará el sistema continuamente")
    print()
    print("IMPORTANTE:")
    print("- El bot estará en modo PAPER TRADING (sin riesgo)")
    print("- Aprenderá continuamente del mercado en vivo")
    print("- Se reentrenará automáticamente si es necesario")
    print("- Presiona Ctrl+C para detener en cualquier momento")
    print()
    
    input("Presiona Enter para continuar...")
    
    asyncio.run(main())
