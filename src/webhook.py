import json
import logging
from flask import Flask, request, jsonify
import sys
import os
import re
import time
import base64
import datetime
import threading
import requests
from dotenv import load_dotenv
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "")
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")
OPENCLAW_MODEL = os.environ.get("OPENCLAW_MODEL", "openclaw/default")

# Verificación de la firma de Alexa. Pon ALEXA_VERIFY_SIGNATURE=0 en .env
# solo para pruebas locales (curl), nunca en producción.
ALEXA_VERIFY_SIGNATURE = os.environ.get("ALEXA_VERIFY_SIGNATURE", "1") != "0"
# Opcional: si lo rellenas, se comprueba además el applicationId del skill.
ALEXA_SKILL_ID = os.environ.get("ALEXA_SKILL_ID", "").strip()

if not OPENCLAW_TOKEN:
    logger.warning(
        "OPENCLAW_TOKEN no configurado. "
        "Usando respuestas locales como fallback."
    )

if not ALEXA_VERIFY_SIGNATURE:
    logger.warning(
        "ALEXA_VERIFY_SIGNATURE=0: NO se verifica la firma de Alexa. "
        "No uses esto en producción."
    )


_pending_responses = {}
_pending_fetches = set()
_cache_lock = threading.Lock()

_CACHE_TTL = 120  # segundos que sobrevive una respuesta diferida
_cert_cache = {}
_cert_lock = threading.Lock()
_CERT_URL_RE = re.compile(r"^https://s3\.amazonaws\.com(:443)?/echo\.api/.*\.pem$")


def process_jarvis_request(question, user_id="default"):
    question_lower = question.lower()

    responses = {
        "hola": "¡Hola! Soy Jarvis, tu asistente. ¿En qué puedo ayudarte hoy?",
        "cómo estás": "Estoy funcionando perfectamente. Listo para ayudarte.",
        "qué puedes hacer": "Puedo ayudarte con información general, responder preguntas, y asistirte en diversas tareas. Si conectas OpenClaw, mis respuestas serán mucho más inteligentes.",
        "servidor": "El servidor está funcionando correctamente. Para más detalles, conecta el webhook con OpenClaw.",
        "mysql": "MySQL está disponible. Consulta la documentación de tu servidor para más detalles.",
        "tareas": "Revisa tu sistema de tareas o conecta OpenClaw para integración completa.",
        "hora": "No tengo acceso a hora actual en este endpoint. Usa 'date' en terminal o consulta tu dispositivo.",
        "adiós": "¡Hasta luego! Recuerda hacer commit con frecuencia: 'git commit -m \"mensaje claro\"'.",
        "java": "Java está disponible en el servidor. Consulta la documentación para más información.",
        "alexa": "Skill Alexa en desarrollo. Webhook activo. Usa 'Alexa, abre Jarvis' o 'Alexa, pregunta a Jarvis [tu pregunta]'.",
        "ayuda": "Puedes preguntarme sobre cualquier tema. Si tienes OpenClaw configurado, obtendrás respuestas de IA inteligentes.",
    }

    for key in responses:
        if key in question_lower:
            return responses[key]

    return f"He recibido tu pregunta: '{question}'. Si necesitas respuestas más inteligentes, configura OpenClaw en tu .env."


def _call_openclaw_api(question, timeout):
    payload = {
        "model": OPENCLAW_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres Jarvis, un asistente personal inteligente. "
                    "Responde siempre en español, de forma clara y concisa. "
                    "Máximo 2-3 oraciones a menos que necesites más detalle."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 300,
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {OPENCLAW_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = requests.post(
        OPENCLAW_URL,
        json=payload,
        headers=headers,
        timeout=timeout
    )
    resp.raise_for_status()

    data = resp.json()
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return None


def ask_openclaw(question, user_id="alexa"):
    logger.info(f"Consultando OpenClaw: '{question[:80]}...'")

    if not OPENCLAW_TOKEN:
        logger.warning("OpenClaw no configurado, usando fallback local")
        return process_jarvis_request(question, user_id)

    try:
        text = _call_openclaw_api(question, timeout=7)
        if text:
            logger.info(f"OpenClaw respondió ({len(text)} chars)")
            return text
        logger.warning("OpenClaw no devolvió contenido")
        return process_jarvis_request(question, user_id)

    except requests.exceptions.Timeout:
        logger.error("OpenClaw timeout (7s), la próxima vez se entrega diferido")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"OpenClaw no accesible: {e}, usando fallback local")
        return process_jarvis_request(question, user_id)
    except Exception as e:
        logger.error(f"Error con OpenClaw: {e}, usando fallback local")
        return process_jarvis_request(question, user_id)


def _background_fetch(question, cache_key):
    logger.info(f"Background fetch para {cache_key}: '{question[:60]}...'")
    result = "Lo siento, no pude obtener respuesta."
    if OPENCLAW_TOKEN:
        try:
            text = _call_openclaw_api(question, timeout=45)
            if text:
                result = text
        except Exception as e:
            logger.error(f"Error en background fetch: {e}")
            result = process_jarvis_request(question)
    with _cache_lock:
        _pending_responses[cache_key] = (time.time(), result)
        _pending_fetches.discard(cache_key)
    logger.info(f"Background fetch completado para {cache_key}")


def _cache_key(request_data):
    session = request_data.get('session') or {}
    user_id = (session.get('user') or {}).get('userId')
    return user_id or session.get('sessionId') or 'default'


def _prune_cache_locked():
    now = time.time()
    expired = [k for k, (ts, _) in _pending_responses.items() if now - ts > _CACHE_TTL]
    for k in expired:
        _pending_responses.pop(k, None)


def _get_alexa_certificate(cert_url):
    with _cert_lock:
        cached = _cert_cache.get(cert_url)
    if cached is not None:
        return cached

    resp = requests.get(cert_url, timeout=5)
    resp.raise_for_status()
    cert = x509.load_pem_x509_certificate(resp.content)

    with _cert_lock:
        _cert_cache[cert_url] = cert
    return cert


def _verify_alexa_signature(raw_body, headers, request_data):
    """Comprueba la autenticidad de una petición de Alexa.

    Verifica la URL del certificado, que el certificado cubra
    echo-api.amazon.com, la firma sobre el cuerpo crudo y la antigüedad
    del timestamp (150 s). Devuelve (bool, motivo).
    """
    cert_url = headers.get("SignatureCertChainUrl")
    signature = headers.get("Signature")

    if not cert_url or not signature:
        return False, "faltan las cabeceras Signature/SignatureCertChainUrl"

    if not _CERT_URL_RE.match(cert_url):
        return False, f"SignatureCertChainUrl no permitida: {cert_url}"

    try:
        cert = _get_alexa_certificate(cert_url)
    except Exception as e:
        return False, f"no se pudo obtener el certificado: {e}"

    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        dns_names = san.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        dns_names = []
    if "echo-api.amazon.com" not in dns_names:
        return False, "el certificado no cubre echo-api.amazon.com"

    try:
        cert.public_key().verify(
            base64.b64decode(signature),
            raw_body,
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
    except Exception as e:
        return False, f"firma inválida: {e}"

    timestamp = (request_data.get("request") or {}).get("timestamp")
    if timestamp:
        try:
            ts = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=datetime.timezone.utc)
            age = abs(
                (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
            )
            if age > 150:
                return False, f"timestamp fuera de la ventana permitida ({int(age)}s)"
        except ValueError:
            return False, f"timestamp con formato inválido: {timestamp}"

    if ALEXA_SKILL_ID:
        app_id = ((request_data.get("session") or {}).get("application") or {}).get("applicationId")
        if app_id != ALEXA_SKILL_ID:
            return False, "el applicationId no coincide"

    return True, "ok"


def _send_progressive_response(api_endpoint, api_access_token, request_id, text):
    """Envía una respuesta progresiva (voz de relleno) mientras se calcula la final."""
    if not api_endpoint or not api_access_token or not request_id:
        return
    try:
        requests.post(
            f"{api_endpoint.rstrip('/')}/v1/directives",
            json={
                "header": {"requestId": request_id},
                "directive": {
                    "type": "VoicePlayer.Speak",
                    "speech": text,
                    "playBehavior": "REPLACE_ALL",
                },
            },
            headers={
                "Authorization": f"Bearer {api_access_token}",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
        logger.info("Respuesta progresiva enviada")
    except Exception as e:
        logger.warning(f"No se pudo enviar la respuesta progresiva: {e}")


def _notify_progressive_thinking(request_data):
    system = (request_data.get("context") or {}).get("System") or {}
    request_id = (request_data.get("request") or {}).get("requestId")
    t = threading.Thread(
        target=_send_progressive_response,
        args=(
            system.get("apiEndpoint"),
            system.get("apiAccessToken"),
            request_id,
            "Un momento, lo estoy mirando.",
        ),
    )
    t.daemon = True
    t.start()


def validate_alexa_request(request_data):
    try:
        required_fields = ['version', 'session', 'request']
        for field in required_fields:
            if field not in request_data:
                return False, f"Missing field: {field}"

        if 'type' not in request_data['request']:
            return False, "Missing request type"

        return True, "Valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def handle_request(path):
    if request.method == 'GET':
        return handle_health()

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        if path == 'alexa' or path == '' or 'session' in payload:
            return handle_alexa()

    return jsonify({'error': 'Not found'}), 404


def handle_health():
    openclaw_status = "not_configured"
    if OPENCLAW_TOKEN:
        try:
            hc = requests.get(
                OPENCLAW_URL.replace("/v1/chat/completions", "/health"),
                timeout=5
            )
            openclaw_status = "connected" if hc.ok else "error"
        except Exception:
            openclaw_status = "unreachable"

    return jsonify({
        'status': 'healthy',
        'service': 'Jarvis Alexa Webhook',
        'version': '2.0.0',
        'openclaw': openclaw_status,
        'endpoints': ['/alexa', '/health']
    })


def handle_alexa():
    try:
        logger.info("Received Alexa request")

        request_data = request.get_json(silent=True)
        if not request_data:
            return jsonify({
                'version': '1.0',
                'response': {
                    'outputSpeech': {
                        'type': 'PlainText',
                        'text': 'Error: No JSON data received'
                    },
                    'shouldEndSession': True
                }
            })

        if ALEXA_VERIFY_SIGNATURE:
            ok, reason = _verify_alexa_signature(
                request.get_data(), request.headers, request_data
            )
            if not ok:
                logger.warning(f"Petición de Alexa rechazada: {reason}")
                return jsonify({'error': 'unauthorized'}), 401

        is_valid, message = validate_alexa_request(request_data)
        if not is_valid:
            logger.warning(f"Invalid request: {message}")

        cache_key = _cache_key(request_data)
        request_type = request_data['request']['type']
        should_end = False

        with _cache_lock:
            _prune_cache_locked()
            cached_entry = _pending_responses.pop(cache_key, None)
        cached = cached_entry[1] if cached_entry else None

        if cached:
            logger.info(f"Entregando respuesta pendiente para {cache_key}")
            response_text = cached

            if request_type == 'IntentRequest' and request_data['request']['intent']['name'] == 'AskJarvisIntent':
                slots = request_data['request']['intent'].get('slots', {})
                question_slot = slots.get('question', {})
                question = question_slot.get('value', '')
                if question and cache_key not in _pending_fetches:
                    _pending_fetches.add(cache_key)
                    t = threading.Thread(
                        target=_background_fetch,
                        args=(question, cache_key)
                    )
                    t.daemon = True
                    t.start()
                    logger.info(f"Cache entregado + lanzado bg fetch para nueva pregunta: '{question[:60]}...'")
        else:
            if request_type == 'LaunchRequest':
                response_text = "¡Hola! Soy Jarvis, tu asistente DAW. Puedes preguntarme sobre tus proyectos, MySQL, o tareas. ¿En qué puedo ayudarte?"

            elif request_type == 'IntentRequest':
                intent_name = request_data['request']['intent']['name']
                should_end = intent_name in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']

                if intent_name == 'AskJarvisIntent':
                    slots = request_data['request']['intent'].get('slots', {})
                    question_slot = slots.get('question', {})
                    question = question_slot.get('value', '')

                    if question:
                        _notify_progressive_thinking(request_data)
                        response_text = ask_openclaw(question)
                        if response_text is None:
                            with _cache_lock:
                                if cache_key not in _pending_fetches:
                                    _pending_fetches.add(cache_key)
                                    t = threading.Thread(
                                        target=_background_fetch,
                                        args=(question, cache_key)
                                    )
                                    t.daemon = True
                                    t.start()
                                    logger.info(f"Lanzado background fetch para {cache_key}")
                                else:
                                    logger.info(f"Ya hay fetch en curso para {cache_key}")
                            response_text = "Voy a tardar un poco más de lo que Alexa me deja. Vuelve a preguntármelo en unos segundos y te lo digo."
                    else:
                        response_text = "¿Qué te gustaría preguntarme?"

                elif intent_name == 'ServerStatusIntent':
                    response_text = "El servidor está funcionando correctamente y todos los servicios están activos."

                elif intent_name == 'GetTasksIntent':
                    response_text = "No tengo acceso a tu lista de tareas en este momento."

                elif intent_name == 'AMAZON.FallbackIntent':
                    logger.info("FallbackIntent")
                    response_text = "No he entendido bien. Puedes preguntarme: dime un chiste, cómo está el servidor, o qué sabes hacer."

                elif intent_name == 'AMAZON.HelpIntent':
                    response_text = "Puedes decir cosas como: dime un chiste, cómo está el servidor, o pregúntale a Jarvis cualquier cosa."

                elif intent_name in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
                    response_text = "Hasta luego."

                else:
                    logger.info(f"Intent no reconocido '{intent_name}'")
                    response_text = "No reconozco ese comando. Di: dime un chiste, cómo está el servidor, o pregúntale a Jarvis."

            elif request_type == 'SessionEndedRequest':
                should_end = True
                response_text = "Sesión terminada. ¡Hasta pronto!"
                with _cache_lock:
                    _pending_responses.pop(cache_key, None)
                    _pending_fetches.discard(cache_key)

            else:
                response_text = f"Tipo de request no reconocido: {request_type}"

        response = {
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': response_text
                },
                'card': {
                    'type': 'Simple',
                    'title': 'Jarvis Assistant',
                    'content': response_text
                },
                'shouldEndSession': should_end
            }
        }

        logger.info(f"Response: {response_text[:50]}...")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': 'Lo siento, ha ocurrido un error procesando tu solicitud.'
                },
                'shouldEndSession': True
            }
        })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')

    logger.info(f"Starting Jarvis Alexa Webhook on {host}:{port}")
    logger.info("Endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /alexa  - Alexa webhook")
    logger.info(f"OpenClaw: {'CONECTADO' if OPENCLAW_TOKEN else 'NO CONFIGURADO (usando fallback local)'}")
    if OPENCLAW_TOKEN:
        logger.info(f"OpenClaw URL: {OPENCLAW_URL}")

    app.run(host=host, port=port, debug=True)
