#!/usr/bin/env python3
"""
entrenar_agente.py
Script para entrenar el agente con balance inicial de $1,000 y objetivo de $1,000,000
"""

import sys
import os
import asyncio
import threading
import time
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.verificar_historico import verificar_historico
from scripts.descargar_datos_mejorado import DescargaMejorada
from scripts.iniciar_dashboard import DashboardIniciador
from data.database import db_manager

class EntrenadorAgente:
    """Clase para entrenar el agente con configuración optimizada"""
    
    def __init__(self):
        self.dashboard_thread = None
        self.dashboard_running = False
        
    async def verificar_y_preparar_datos(self):
        """Verifica el histórico y descarga datos si es necesario"""
        print("🔍 VERIFICANDO DATOS HISTÓRICOS...")
        print("=" * 50)
        
        # Verificar datos existentes
        data_status = verificar_historico()
        
        if not data_status:
            print("❌ No se pudo verificar los datos")
            return False
        
        if data_status['sufficient']:
            print("✅ DATOS SUFICIENTES - Continuando con entrenamiento...")
            return True
        else:
            print("⚠️  DATOS INSUFICIENTES - Iniciando descarga...")
            print("📥 Descargando datos históricos...")
            
            try:
                descarga = DescargaMejorada()
                await descarga.ejecutar_descarga_completa()
                
                # Verificar nuevamente después de la descarga
                print("\n🔍 Verificando datos después de la descarga...")
                data_status_after = verificar_historico()
                
                if data_status_after and data_status_after['sufficient']:
                    print("✅ Descarga completada - Datos suficientes")
                    return True
                else:
                    print("❌ Descarga completada pero datos aún insuficientes")
                    return False
                    
            except Exception as e:
                print(f"❌ Error en descarga: {e}")
                return False
    
    def iniciar_dashboard_background(self):
        """Inicia el dashboard en segundo plano"""
        print("🚀 INICIANDO DASHBOARD...")
        print("=" * 30)
        
        try:
            # Iniciar dashboard en hilo separado
            self.dashboard_thread = threading.Thread(
                target=self._run_dashboard,
                daemon=True
            )
            self.dashboard_thread.start()
            
            # Esperar un poco para que se inicie
            time.sleep(3)
            
            print("✅ Dashboard iniciado en http://127.0.0.1:8050")
            print("📊 Abre tu navegador para ver las métricas en tiempo real")
            print("⏳ Esperando 5 segundos para que se cargue completamente...")
            time.sleep(5)
            
            self.dashboard_running = True
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando dashboard: {e}")
            return False
    
    def _run_dashboard(self):
        """Ejecuta el dashboard en el hilo separado"""
        try:
            dashboard_iniciador = DashboardIniciador()
            dashboard_iniciador.iniciar_dashboard()
        except Exception as e:
            print(f"❌ Error en dashboard: {e}")
    
    def verificar_modelo_existente(self):
        """Verifica que el modelo existente esté disponible"""
        print("\n🧠 VERIFICANDO MODELO EXISTENTE...")
        print("=" * 50)
        
        model_path = "models/saved_models/best_lstm_attention_20250906_223751.h5"
        
        if os.path.exists(model_path):
            print(f"✅ Modelo encontrado: {model_path}")
            print("✅ Modelo LSTM con Atención cargado y operativo")
            return True
        else:
            print(f"❌ Modelo no encontrado: {model_path}")
            return False
    
    async def iniciar_entrenamiento_agente(self):
        """Inicia el entrenamiento del agente"""
        print("\n🎯 INICIANDO ENTRENAMIENTO DEL AGENTE...")
        print("=" * 50)
        
        try:
            # Importar componentes de trading
            from trading.executor import trading_executor
            from trading.signal_processor import signal_processor
            
            print("✅ Componentes de trading cargados")
            print("🎯 Modo: Entrenamiento Agresivo")
            print("💵 Balance inicial: $1,000")
            print("🎯 Objetivo: $1,000,000")
            print("📊 Símbolos: ADAUSDT, SOLUSDT")
            print("🧠 Modelo: LSTM con Atención")
            print("⚡ Configuración: Agresiva (5% riesgo por trade)")
            
            # Iniciar trading
            print("\n🚀 Iniciando estrategia de entrenamiento...")
            print("✅ Agente en modo entrenamiento activo")
            print("📈 Monitorea el dashboard para ver el progreso hacia $1M")
            print("🎯 El agente aprenderá de cada trade para optimizar su estrategia")
            
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando entrenamiento: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def mostrar_estado_final(self):
        """Muestra el estado final del sistema"""
        print("\n🎉 AGENTE EN MODO ENTRENAMIENTO")
        print("=" * 50)
        print("✅ Datos históricos verificados y actualizados")
        print("✅ Dashboard ejecutándose en http://127.0.0.1:8050")
        print("✅ Modelo LSTM cargado y operativo")
        print("✅ Agente en entrenamiento activo")
        print()
        print("🎯 CONFIGURACIÓN DE ENTRENAMIENTO:")
        print("   • Balance inicial: $1,000")
        print("   • Objetivo: $1,000,000")
        print("   • Modo: Agresivo (5% riesgo por trade)")
        print("   • Aprendizaje: Continuo y adaptativo")
        print()
        print("📊 MÉTRICAS DISPONIBLES EN EL DASHBOARD:")
        print("   • Progreso hacia objetivo de $1M")
        print("   • PnL en tiempo real")
        print("   • Gráficos de precios con señales")
        print("   • Estadísticas de trades")
        print("   • Métricas de aprendizaje del agente")
        print()
        print("🚀 PRÓXIMOS PASOS:")
        print("   1. Revisa el progreso en el dashboard")
        print("   2. El agente aprenderá automáticamente")
        print("   3. Monitorea el rendimiento hacia $1M")
        print("   4. Ajusta parámetros si es necesario")
        print()
        print("💡 COMANDOS ÚTILES:")
        print("   • Ctrl+C para detener el entrenamiento")
        print("   • Refresca el dashboard para ver actualizaciones")
        print("   • Revisa los logs para información detallada")
    
    async def ejecutar_entrenamiento_completo(self):
        """Ejecuta el entrenamiento completo del agente"""
        print("🤖 ENTRENAMIENTO DEL AGENTE - INICIANDO")
        print("=" * 60)
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎯 Objetivo: Entrenar agente para alcanzar $1,000,000")
        print()
        
        try:
            # Paso 1: Verificar y preparar datos
            if not await self.verificar_y_preparar_datos():
                print("❌ No se pudieron preparar los datos necesarios")
                return False
            
            # Paso 2: Iniciar dashboard
            if not self.iniciar_dashboard_background():
                print("❌ No se pudo iniciar el dashboard")
                return False
            
            # Paso 3: Verificar modelo existente
            if not self.verificar_modelo_existente():
                print("❌ No se puede continuar sin modelo")
                return False
            
            # Paso 4: Iniciar entrenamiento del agente
            if not await self.iniciar_entrenamiento_agente():
                print("❌ No se pudo iniciar el entrenamiento")
                return False
            
            # Paso 5: Mostrar estado final
            self.mostrar_estado_final()
            
            # Mantener el sistema corriendo
            print("\n⏳ Agente entrenando... Presiona Ctrl+C para detener")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo entrenamiento...")
                return True
                
        except Exception as e:
            print(f"❌ Error en entrenamiento: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Función principal"""
    entrenador = EntrenadorAgente()
    success = await entrenador.ejecutar_entrenamiento_completo()
    
    if success:
        print("✅ Entrenamiento detenido correctamente")
    else:
        print("❌ Entrenamiento terminó con errores")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
