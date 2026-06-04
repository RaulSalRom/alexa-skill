#!/bin/bash
# Testing completo SIN cuenta Amazon

echo "🎤 ALEXA SKILL TESTING - INDEPENDIENTE"
echo "========================================"

# 1. Iniciar webhook si no está corriendo
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "1. Verificando webhook..."
if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ⚠️  Webhook no activo. Iniciando..."
    "$SCRIPT_DIR/start.sh" > /tmp/webhook.log 2>&1 &
    WEBHOOK_PID=$!
    sleep 5
    echo "   ✅ Webhook iniciado (PID: $WEBHOOK_PID)"
else
    echo "   ✅ Webhook ya activo"
fi

# 2. Ejecutar tests
echo ""
echo "2. Ejecutando tests locales..."
source "$PROJECT_DIR/venv/bin/activate"
python "$PROJECT_DIR/tests/test-alexa-local.py"

# 3. Mostrar información
echo ""
echo "3. INFORMACIÓN PARA DEPLOYMENT:"
echo "   📍 Webhook local: http://localhost:5000/alexa"
echo "   📍 Health check: http://localhost:5000/health"
echo "   📍 Test UI: http://localhost:5000/test"
echo ""
echo "4. PARA HTTPS (cuando quieras conectar a Alexa real):"
echo "   a) En tu Mac: ngrok http 5000"
echo "   b) Copia URL HTTPS (ej: https://abc123.ngrok.io)"
echo "   c) Crea Skill en: https://developer.amazon.com"
echo "   d) Endpoint: https://TU_URL_NGROK/alexa"
echo ""
echo "5. TESTING INTERACTIVO (opcional):"
echo "   ./test-all.sh interactive"

# Modo interactivo si se solicita
if [ "$1" = "interactive" ]; then
    echo ""
    echo "🎤 MODO INTERACTIVO ACTIVADO"
    source "$PROJECT_DIR/venv/bin/activate"
    python "$PROJECT_DIR/tests/test-alexa-local.py" interactive
fi

echo ""
echo "========================================"
echo "✅ Testing completado SIN cuenta Amazon"
echo "🎯 Skill lista para cuando quieras crear cuenta"