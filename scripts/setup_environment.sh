#!/bin/bash
# Bot Trading v10 Enterprise - Script de Configuración
# ====================================================

echo ""
echo "🤖 Bot Trading v10 Enterprise - Configuración del Entorno"
echo "========================================================"
echo ""

# Verificar Python
echo "📋 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instala Python 3.8+ desde https://python.org"
    exit 1
fi

python3 --version

# Crear entorno virtual
echo ""
echo "🔧 Creando entorno virtual..."
if [ -d "venv" ]; then
    echo "⚠️  El entorno virtual ya existe. Eliminando..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Error creando entorno virtual"
    exit 1
fi

# Activar entorno virtual
echo ""
echo "🚀 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "📦 Actualizando pip..."
python -m pip install --upgrade pip

# Instalar dependencias
echo ""
echo "📥 Instalando dependencias..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

# Crear archivo .env si no existe
echo ""
echo "🔐 Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    cp env.example .env
    echo "✅ Archivo .env creado desde env.example"
    echo "⚠️  IMPORTANTE: Edita .env con tus credenciales antes de usar el bot"
else
    echo "✅ Archivo .env ya existe"
fi

# Crear directorios necesarios
echo ""
echo "📁 Creando directorios necesarios..."
mkdir -p data/logs
mkdir -p data/models
mkdir -p data/historical
mkdir -p data/checkpoints
mkdir -p data/alignments

# Crear archivos .gitkeep
touch data/logs/.gitkeep
touch data/models/.gitkeep
touch data/historical/.gitkeep
touch data/checkpoints/.gitkeep
touch data/alignments/.gitkeep

echo ""
echo "✅ Configuración completada exitosamente!"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Edita .env con tus credenciales"
echo "   2. Configura config/user_settings.yaml"
echo "   3. Configura control/config.yaml"
echo "   4. Ejecuta: python bot.py --mode paper --telegram-enabled"
echo ""
echo "🎯 Para activar el entorno virtual en el futuro:"
echo "   source venv/bin/activate"
echo ""
