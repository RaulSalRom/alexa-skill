# Jarvis Assistant - Alexa Skill

Skill de Amazon Alexa para asistente personal con webhook self-hosted.
Se conecta a **OpenClaw Gateway** mediante API OpenAI-compatible para respuestas con IA real,
con fallback a respuestas locales si OpenClaw no está disponible.

## Arquitectura

```
Usuario → Alexa Skill → HTTPS (ngrok/Tailscale) → Webhook Python
                                                       │
                                          ┌────────────┴────────────┐
                                          ▼                         ▼
                                   OpenClaw Gateway          Fallback local
                                   (IA real via API)      (respuestas fijas)
```

- **No requiere AWS Lambda** — el skill apunta a un webhook HTTP self-hosted
- **No requiere ASK SDK** — comunicación directa mediante JSON sobre HTTPS
- **OpenClaw opcional** — si no se configura, usa respuestas locales predefinidas
- **Hosting propio** — servidor Ubuntu con Python Flask

## Estructura

```
alexa-skill/
├── src/
│   ├── webhook.py            # Webhook principal (Flask) con proxy a OpenClaw
│   └── webhook-simple.py     # Versión simplificada (sin Flask)
├── scripts/
│   ├── start.sh              # Inicio con venv + dependencias
│   ├── start-simple.sh       # Inicio rápido (sin dependencias)
│   ├── test-all.sh           # Batería de tests automatizada
│   └── setup-alexa-easy.sh   # Guía interactiva de configuración
├── tests/
│   └── test-alexa-local.py   # Framework de tests sin cuenta Amazon
├── utils/
│   └── analyze-screenshot.py # OCR para capturas de ngrok/Tailscale
├── .env.example              # Plantilla de configuración OpenClaw
├── requirements.txt          # Dependencias Python
├── alexa-skill-config.json   # Modelo de interacción del skill
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.8+
- Flask 3.0+ (para webhook.py)
- ngrok o Tailscale Funnel (para exponer HTTPS)
- Cuenta de Amazon Developer (para publicar el skill)
- OpenClaw Gateway (opcional) — para respuestas con IA real

## Inicio rápido

```bash
# 1. Clonar e instalar
git clone <repo-url>
cd alexa-skill
./scripts/start.sh

# 2. Exponer con ngrok (en otra terminal)
ngrok http 5000

# 3. Ejecutar tests locales
./scripts/test-all.sh
```

## Configuración de OpenClaw (opcional)

Para que Alexa responda usando tu agente de OpenClaw:

### 1. Activar API en OpenClaw

En el servidor donde corre OpenClaw, añade esto a `~/.openclaw/openclaw.json`
dentro del bloque `gateway`:

```json
"http": {
  "endpoints": {
    "chatCompletions": {
      "enabled": true
    }
  }
}
```

Reinicia el gateway:

```bash
systemctl --user restart openclaw-gateway
```

Verifica que funciona:

```bash
curl -X POST http://localhost:18789/v1/chat/completions \
  -H 'Authorization: Bearer TU_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw/default","messages":[{"role":"user","content":"Hola"}]}'
```

### 2. Configurar el webhook

Copia y edita el archivo de entorno:

```bash
cp .env.example .env
```

Configura las variables en `.env`:

```env
# URL del Gateway de OpenClaw
OPENCLAW_URL=http://IP_DEL_SERVIDOR:18789/v1/chat/completions

# Token de autenticación (de gateway.auth.token en openclaw.json)
OPENCLAW_TOKEN=tu_token_aqui
```

O pásalas directamente al iniciar:

```bash
OPENCLAW_URL=http://IP_DEL_SERVIDOR:18789/v1/chat/completions \
OPENCLAW_TOKEN=tu_token \
./scripts/start.sh
```

> **Nota**: Si no se configura OpenClaw, el webhook usa respuestas locales
> predefinidas como fallback. El skill funciona igualmente.

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/alexa` | POST | Endpoint principal para Alexa Skill |
| `/health` | GET | Health check del servicio (muestra estado de OpenClaw) |
| `/test` | GET/POST | Interfaz de prueba manual |

## Configuración del Skill

1. Crea un skill en [Amazon Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Nombre de invocación: `jarvis asistente`
3. Tipo: Custom → Provision your own
4. Endpoint HTTPS: `https://tu-url.ngrok.io/alexa`
5. Copia el contenido de `alexa-skill-config.json` en el editor de interacción

## Intents

| Intent | Descripción |
|--------|-------------|
| `AskJarvisIntent` | Pregunta genérica (slot `question` tipo `AMAZON.SearchQuery`) — proxy a OpenClaw |
| `GetTasksIntent` | Consultar tareas pendientes |
| `ServerStatusIntent` | Estado del servidor y bases de datos |
| `AMAZON.HelpIntent` | Ayuda |
| `AMAZON.StopIntent` / `CancelIntent` | Cierre de sesión |

## Testing local

```bash
# Tests automáticos
./scripts/test-all.sh

# Modo interactivo
./scripts/test-all.sh interactive
# o
python tests/test-alexa-local.py interactive
```

El framework de tests simula requests de Alexa sin necesidad de cuenta Amazon.
Si OpenClaw está configurado, los tests validan respuestas reales de IA.

## Despliegue

El webhook está diseñado para ejecutarse en un servidor Ubuntu y exponerse mediante:
- **ngrok** — túnel HTTPS público (`ngrok http 5000`)
- **Tailscale Funnel** — túnel HTTPS sobre Tailscale (`tailscale funnel 443`)

## Variables de entorno

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `OPENCLAW_URL` | URL del endpoint OpenAI-compatible de OpenClaw | — |
| `OPENCLAW_TOKEN` | Token de autenticación del Gateway | — |
| `OPENCLAW_MODEL` | Modelo a usar en OpenClaw | `openclaw/default` |
| `PORT` | Puerto del webhook | `5000` |
| `HOST` | Host del webhook | `0.0.0.0` |

## Licencia

Uso personal y educativo. Aclaramos que somos estudiantes y solo es un proyecto abierto.
