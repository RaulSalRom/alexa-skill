# Jarvis Assistant - Alexa Skill

Skill de Amazon Alexa para asistente personal DAW con webhook self-hosted.

## Arquitectura

```
Usuario → Alexa Skill → HTTPS (ngrok/Tailscale) → Webhook Python → Respuesta JSON
```

- **No requiere AWS Lambda** — el skill apunta a un webhook HTTP self-hosted
- **No requiere ASK SDK** — comunicación directa mediante JSON sobre HTTPS
- **Hosting propio** — servidor Ubuntu con Python Flask

## Estructura

```
alexa-skill/
├── src/
│   ├── webhook.py            # Webhook principal (Flask)
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

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/alexa` | POST | Endpoint principal para Alexa Skill |
| `/health` | GET | Health check del servicio |
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
| `AskJarvisIntent` | Pregunta genérica (slot `question` tipo `AMAZON.SearchQuery`) |
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

## Despliegue

El webhook está diseñado para ejecutarse en un servidor Ubuntu y exponerse mediante:
- **ngrok** — túnel HTTPS público (`ngrok http 5000`)
- **Tailscale Funnel** — túnel HTTPS sobre Tailscale (`tailscale funnel 443`)

## Licencia

Uso personal y educativo.
