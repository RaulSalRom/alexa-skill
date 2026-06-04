#!/bin/bash
# Script para iniciar el webhook de Alexa

set -e

echo "=== Iniciando Jarvis Alexa Webhook ==="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no encontrado"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Crear virtual environment si no existe
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Creando virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activar venv y instalar dependencias
echo "Instalando dependencias..."
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Configurar puerto
PORT=${PORT:-5000}
HOST=${HOST:-0.0.0.0}

echo ""
echo "=== INFORMACIÓN ==="
echo "Webhook URL: http://$HOST:$PORT/alexa"
echo "Health check: http://$HOST:$PORT/health"
echo "Test interface: http://$HOST:$PORT/test"
echo ""
echo "Para Alexa Skill Development:"
echo "1. Usa ngrok para HTTPS: ngrok http $PORT"
echo "2. O Tailscale funnel: tailscale funnel 443"
echo "3. Endpoint: https://TU_URL/alexa"
echo ""
echo "=== INICIANDO SERVICIO ==="

# Iniciar servicio
python "$PROJECT_DIR/src/webhook.py"