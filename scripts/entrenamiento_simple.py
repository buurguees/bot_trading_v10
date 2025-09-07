#!/usr/bin/env python3
"""
🌙 Entrenamiento Simple del Trading Bot v10
==========================================

Versión simplificada sin emojis para evitar problemas de Unicode en Windows.

Uso: python scripts/entrenamiento_simple.py
"""

import asyncio
import logging
import sys
import os
import yaml
import pandas as pd
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

# Configurar logging sin emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/entrenamiento_simple_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class EntrenamientoSimple:
    """Sistema de entrenamiento simple sin emojis"""
    
    def __init__(self):
        self.config = user_config
        self.training_config = self._load_training_config()
        self.symbols = self.training_config['entrenamiento']['símbolos']
        self.years_to_try = self.training_config['entrenamiento']['años_historicos']
        self.current_year = None
        self.training_results = {}
        self.realtime_learning = False
        self.websocket_running = False
        
        # Configurar para entrenamiento
        self._setup_training_config()
        
        logger.info("Entrenamiento Simple inicializado")
    
    def _load_training_config(self) -> Dict:
        """Carga la configuración específica de entrenamiento"""
        try:
            config_path = os.path.join(project_root, 'config', 'entrenamiento_nocturno.yaml')
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración específica: {e}")
            # Configuración por defecto
            return {
                'entrenamiento': {
                    'símbolos': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT'],
                    'años_historicos': [5, 4, 3, 2, 1],
                    'timeframes': ['1h', '4h', '1d']
                }
            }
    
    def _setup_training_config(self):
        """Configura el bot para entrenamiento"""
        try:
            # Configurar para modo desarrollo durante entrenamiento
            self.config.set_value(['trading', 'mode'], 'development')
            self.config.set_value(['bot_settings', 'features', 'auto_trading'], False)
            self.config.set_value(['bot_settings', 'features', 'auto_retraining'], True)
            
            logger.info("Configuración de entrenamiento aplicada")
        except Exception as e:
            logger.error(f"Error configurando entrenamiento: {e}")
    
    async def ejecutar_entrenamiento_completo(self):
        """Ejecuta el entrenamiento completo con fallback automático"""
        print("INICIANDO ENTRENAMIENTO SIMPLE")
        print("=" * 50)
        print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Símbolos: {', '.join(self.symbols)}")
        print(f"Años a probar: {self.years_to_try}")
        print()
        
        try:
            # 1. Verificar conectividad
            await self._verificar_conectividad()
            
            # 2. Entrenar con datos históricos
            await self._entrenar_con_historico()
            
            # 3. Iniciar aprendizaje en tiempo real
            await self._iniciar_aprendizaje_tiempo_real()
            
            # 4. Monitorear continuamente
            await self._monitorear_continuamente()
            
        except KeyboardInterrupt:
            logger.info("Entrenamiento interrumpido por usuario")
            await self._limpiar_recursos()
        except Exception as e:
            logger.error(f"Error crítico en entrenamiento: {e}")
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
    
    async def _entrenar_con_historico(self):
        """Entrena con datos históricos con fallback automático"""
        print("ENTRENAMIENTO CON DATOS HISTORICOS")
        print("-" * 40)
        
        for years in self.years_to_try:
            try:
                print(f"\nIntentando entrenar con {years} años de datos...")
                
                # Descargar datos históricos
                await self._descargar_datos_historicos(years)
                
                # Entrenar modelo
                await self._entrenar_modelo_historico(years)
                
                # Si llegamos aquí, el entrenamiento fue exitoso
                self.current_year = years
                print(f"   [OK] Entrenamiento exitoso con {years} años de datos")
                break
                
            except Exception as e:
                print(f"   [ERROR] Error con {years} años: {e}")
                logger.error(f"Error entrenando con {years} años: {e}")
                
                if years == self.years_to_try[-1]:  # Último intento
                    print("   [ERROR] Todos los intentos fallaron")
                    raise Exception("No se pudo entrenar con ningún período histórico")
                else:
                    print(f"   [INFO] Intentando con {years-1} años...")
                    continue
        
        print(f"\n[OK] Entrenamiento histórico completado con {self.current_year} años")
        print()
    
    async def _descargar_datos_historicos(self, years: int):
        """Descarga datos históricos para el período especificado"""
        print(f"   Descargando {years} años de datos históricos...")
        
        try:
            total_downloaded = 0
            
            for symbol in self.symbols:
                print(f"      Descargando {symbol}...")
                
                # Descargar datos para múltiples timeframes
                timeframes = ['1h', '4h', '1d']
                
                for timeframe in timeframes:
                    try:
                        # Calcular días basado en timeframe
                        if timeframe == '1h':
                            days = years * 365
                        elif timeframe == '4h':
                            days = years * 365
                        else:  # 1d
                            days = years * 365
                        
                        # Descargar datos
                        df = await data_collector.fetch_historical_data(
                            symbol, timeframe, days
                        )
                        
                        if not df.empty:
                            # Guardar en base de datos
                            saved_count = await self._save_historical_data(df)
                            total_downloaded += saved_count
                            print(f"         [OK] {timeframe}: {saved_count} registros")
                        else:
                            print(f"         [WARN] {timeframe}: Sin datos")
                            
                    except Exception as e:
                        print(f"         [ERROR] {timeframe}: Error - {e}")
                        continue
                
                print(f"      [OK] {symbol} completado")
            
            print(f"   Total descargado: {total_downloaded:,} registros")
            
            if total_downloaded < 1000:
                raise Exception(f"Datos insuficientes: solo {total_downloaded} registros")
            
        except Exception as e:
            logger.error(f"Error descargando datos históricos: {e}")
            raise
    
    async def _save_historical_data(self, df: pd.DataFrame) -> int:
        """Guarda datos históricos en la base de datos"""
        try:
            if df.empty:
                return 0
            
            # Convertir DataFrame a MarketData objects
            market_data_list = []
            for _, row in df.iterrows():
                market_data = {
                    'symbol': row.get('symbol', 'UNKNOWN'),
                    'timestamp': int(row.name.timestamp() * 1000) if hasattr(row.name, 'timestamp') else int(datetime.now().timestamp() * 1000),
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
                    # Usar el método correcto del DatabaseManager
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
    
    async def _entrenar_modelo_historico(self, years: int):
        """Entrena el modelo con datos históricos"""
        print(f"   Entrenando modelo con {years} años de datos...")
        
        try:
            training_results = {}
            
            for symbol in self.symbols:
                print(f"      Entrenando {symbol}...")
                
                try:
                    # Entrenar modelo inicial
                    result = await adaptive_trainer.train_initial_model(
                        symbol=symbol,
                        days_back=years * 365
                    )
                    
                    if result.get('status') == 'completed':
                        training_results[symbol] = result
                        accuracy = result.get('validation_accuracy', 0)
                        print(f"         [OK] {symbol}: Accuracy {accuracy:.3f}")
                    else:
                        print(f"         [ERROR] {symbol}: Error - {result.get('error', 'Unknown')}")
                        raise Exception(f"Error entrenando {symbol}")
                        
                except Exception as e:
                    print(f"         [ERROR] {symbol}: Error - {e}")
                    raise
            
            # Guardar resultados
            self.training_results = training_results
            
            # Calcular accuracy promedio
            accuracies = [r.get('validation_accuracy', 0) for r in training_results.values()]
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
            
            print(f"   Accuracy promedio: {avg_accuracy:.3f}")
            
            if avg_accuracy < 0.6:
                raise Exception(f"Accuracy muy baja: {avg_accuracy:.3f}")
            
        except Exception as e:
            logger.error(f"Error entrenando modelo histórico: {e}")
            raise
    
    async def _iniciar_aprendizaje_tiempo_real(self):
        """Inicia el aprendizaje en tiempo real"""
        print("INICIANDO APRENDIZAJE EN TIEMPO REAL")
        print("-" * 40)
        
        try:
            # Configurar para modo paper trading
            self.config.set_value(['trading', 'mode'], 'paper_trading')
            self.config.set_value(['bot_settings', 'features', 'auto_trading'], True)
            
            print("   [OK] Configuración actualizada para tiempo real")
            
            # Inicializar sistema de aprendizaje
            learning_system = SelfLearningSystem()
            await learning_system.initialize()
            
            print("   [OK] Sistema de aprendizaje inicializado")
            
            # Marcar como activo
            self.realtime_learning = True
            
            print("   [OK] Aprendizaje en tiempo real activado")
            print()
            
        except Exception as e:
            logger.error(f"Error iniciando aprendizaje tiempo real: {e}")
            raise
    
    async def _monitorear_continuamente(self):
        """Monitorea el sistema continuamente"""
        print("MONITOREO CONTINUO ACTIVO")
        print("-" * 30)
        print("   El bot está entrenando y aprendiendo...")
        print("   Analizando mercado en tiempo real...")
        print("   Aplicando aprendizaje continuo...")
        print("   Presiona Ctrl+C para detener")
        print()
        
        try:
            while True:
                # Mostrar estado cada 5 minutos
                await asyncio.sleep(300)  # 5 minutos
                
                await self._mostrar_estado_actual()
                
        except KeyboardInterrupt:
            logger.info("Monitoreo interrumpido por usuario")
        except Exception as e:
            logger.error(f"Error en monitoreo: {e}")
    
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
        """Guarda el estado final del entrenamiento"""
        try:
            estado_final = {
                'timestamp': datetime.now().isoformat(),
                'años_entrenados': self.current_year,
                'símbolos': self.symbols,
                'resultados_entrenamiento': self.training_results,
                'aprendizaje_tiempo_real': self.realtime_learning,
                'websocket_activo': self.websocket_running
            }
            
            with open(f'logs/estado_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w', encoding='utf-8') as f:
                json.dump(estado_final, f, indent=2, ensure_ascii=False)
            
            logger.info("Estado final guardado")
            
        except Exception as e:
            logger.error(f"Error guardando estado final: {e}")

async def main():
    """Función principal"""
    entrenamiento = EntrenamientoSimple()
    await entrenamiento.ejecutar_entrenamiento_completo()

if __name__ == "__main__":
    print("TRADING BOT v10 - ENTRENAMIENTO SIMPLE")
    print("=" * 50)
    print("Este script entrenará el bot con datos históricos")
    print("y continuará aprendiendo en tiempo real.")
    print()
    print("IMPORTANTE:")
    print("- El bot estará en modo PAPER TRADING (sin riesgo)")
    print("- Aprenderá continuamente del mercado en vivo")
    print("- Se reentrenará automáticamente si es necesario")
    print("- Presiona Ctrl+C para detener en cualquier momento")
    print()
    
    input("Presiona Enter para continuar...")
    
    asyncio.run(main())
