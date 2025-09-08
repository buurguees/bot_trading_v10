#!/bin/bash
# Script de inicio para entrenamiento autónomo en Linux/Mac
# ========================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                🤖 ENTRENAMIENTO AUTÓNOMO ENTERPRISE 🤖        ║"
echo "║                                                              ║"
echo "║  Configurando y ejecutando entrenamiento enterprise          ║"
echo "║  completamente automatizado mientras cenas 🍽️                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no encontrado. Instala Python 3.8+ primero."
    exit 1
fi

echo "✅ Python detectado: $(python3 --version)"

# Configurar entorno
echo ""
echo "🔧 Configurando entorno..."
python3 setup_autonomous_training.py
if [ $? -ne 0 ]; then
    echo "❌ Error en configuración. Revisa los errores arriba."
    exit 1
fi

echo ""
echo "🚀 Iniciando entrenamiento autónomo..."
echo ""
echo "📋 Información importante:"
echo "   • El entrenamiento correrá en background"
echo "   • Logs: logs/autonomous_training.log"
echo "   • Métricas: http://localhost:8000/metrics"
echo "   • Tiempo estimado: 2-4 horas"
echo "   • ¡Disfruta tu cena! 🍽️"
echo ""

# Iniciar entrenamiento
python3 run_autonomous_training.py

echo ""
echo "🏁 Entrenamiento finalizado"
echo "📊 Revisa los logs para ver los resultados"
