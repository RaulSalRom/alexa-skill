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

# Configuración de OpenClaw (opcional)
# Si no se configura, el webhook usa respuestas locales como fallback
export OPENCLAW_URL="${OPENCLAW_URL:-}"
export OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-}"
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-openclaw/default}"

echo ""
echo "=== INFORMACIÓN ==="
echo "Webhook URL: http://$HOST:$PORT/alexa"
echo "Health check: http://$HOST:$PORT/health"
echo "Test interface: http://$HOST:$PORT/test"
if [ -n "$OPENCLAW_TOKEN" ]; then
    echo "OpenClaw: CONECTADO a $OPENCLAW_URL"
else
    echo "OpenClaw: NO CONFIGURADO (usando respuestas locales)"
    echo "  Configura OPENCLAW_URL y OPENCLAW_TOKEN para conectar con OpenClaw"
fi
echo ""
echo "Para Alexa Skill Development:"
echo "1. Usa ngrok para HTTPS: ngrok http $PORT"
echo "2. O Tailscale funnel: tailscale funnel 443"
echo "3. Endpoint: https://TU_URL/alexa"
echo ""
echo "=== INICIANDO SERVICIO ==="

# Iniciar servicio
python "$PROJECT_DIR/src/webhook.py"