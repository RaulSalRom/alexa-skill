#!/bin/bash
# Script simplificado para iniciar webhook

echo "=== Jarvis Alexa Webhook (Simple) ==="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado"
    exit 1
fi

# Puerto
PORT=${1:-5000}

echo "📡 Iniciando en puerto: $PORT"
echo ""
echo "🌐 URLs:"
echo "  Health:    http://localhost:$PORT/health"
echo "  Test:      http://localhost:$PORT/test"
echo "  Alexa:     http://localhost:$PORT/alexa (POST)"
echo ""
echo "🔧 Para Alexa Skill:"
echo "  1. En otra terminal: ngrok http $PORT"
echo "  2. O: tailscale funnel $PORT"
echo "  3. Usar URL HTTPS proporcionada"
echo ""
echo "🚀 Iniciando servidor..."
echo "🔄 Presiona Ctrl+C para detener"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Iniciar servidor
python3 "$PROJECT_DIR/src/webhook-simple.py"