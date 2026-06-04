#!/usr/bin/env python3
"""
Alexa Webhook para Jarvis Assistant
Endpoint que recibirá requests de Alexa Skill
Proxy a OpenClaw Gateway vía API OpenAI-compatible
"""

import json
import logging
from flask import Flask, request, jsonify
import sys
import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de OpenClaw
OPENCLAW_URL = os.environ.get(
    "OPENCLAW_URL",
    "http://192.168.1.80:18789/v1/chat/completions"
)
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")
OPENCLAW_MODEL = os.environ.get("OPENCLAW_MODEL", "openclaw/default")

if not OPENCLAW_TOKEN:
    logger.warning(
        "OPENCLAW_TOKEN no configurado. "
        "Usando respuestas locales como fallback."
    )

def process_jarvis_request(question, user_id="draken"):
    """
    Procesa pregunta y devuelve respuesta de Jarvis
    Respuestas predefinidas para Alexa Skill
    """
    question_lower = question.lower()
    
    # Respuestas predefinidas para DAW estudiante
    responses = {
        "hola": "¡Hola Draken! Soy Jarvis, tu asistente DAW. ¿En qué puedo ayudarte hoy?",
        "cómo estás": "Estoy funcionando perfectamente en el servidor. Lista para ayudarte con tus proyectos DAW.",
        "qué puedes hacer": "Puedo ayudarte con: 1. Tus tareas DAW, 2. Base de datos MySQL, 3. Proyectos Java, 4. Recordatorios, 5. Información del servidor.",
        "servidor": "Servidor: Ubuntu 24.04, CPU: Intel U7300, RAM: 3.8GB, MySQL: 5.7, Docker activo. IP Tailscale: 100.78.237.50.",
        "mysql": "MySQL 5.7 corriendo en puerto 3306. Base de datos 'daw_db' activa. Usuario: draken. Acceso vía phpMyAdmin: puerto 8080.",
        "tareas": "Revisa tu repositorio CFGS-DAW en GitHub. Tienes proyectos Java en 1º-Curso/ y ejercicios SQL.",
        "hora": "No tengo acceso a hora actual en este endpoint. Usa 'date' en terminal o consulta tu dispositivo.",
        "adiós": "¡Hasta luego Draken! Recuerda: 'git commit -m \"mensaje claro\"' para buenas prácticas.",
        "java": "Para aprender Java visita W3Schools. Tu servidor está listo para proyectos Java con MySQL.",
        "alexa": "Skill Alexa en desarrollo. Webhook activo en puerto 5000. Usa 'Alexa, abre Jarvis' o 'Alexa, pregunta a Jarvis [tu pregunta]'.",
        "tailscale": "Tailscale configurado. IP: 100.78.237.50. Acceso remoto seguro a MySQL y phpMyAdmin.",
        "proyectos": "Tus proyectos DAW en ~/daw-projects/. MySQL disponible en puerto 3306. Java pendiente instalar JDK.",
        "github": "Tu repositorio CFGS-DAW clonado. Cuenta GitHub: jarvisclaw-dev para colaboración por PRs."
    }
    
    # Buscar respuesta
    for key in responses:
        if key in question_lower:
            return responses[key]
    
    # Respuesta por defecto
    return f"He recibido tu pregunta: '{question}'. Como Jarvis, puedo ayudarte con: Java, MySQL, proyectos DAW, servidor info, o tareas. ¿Puedes ser más específico?"



def ask_openclaw(question, user_id="alexa"):
    """
    Envía pregunta a OpenClaw vía API OpenAI-compatible
    y devuelve la respuesta. Usa respuestas locales como fallback.
    """
    logger.info(f"Consultando OpenClaw: '{question[:80]}...'")

    if not OPENCLAW_TOKEN:
        logger.warning("OpenClaw no configurado, usando fallback local")
        return process_jarvis_request(question, user_id)

    try:
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
            timeout=60
        )
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
            logger.info(f"OpenClaw respondió ({len(text)} chars)")
            return text

        logger.warning("OpenClaw no devolvió contenido")
        return process_jarvis_request(question, user_id)

    except requests.exceptions.Timeout:
        logger.error("OpenClaw timeout (60s), usando fallback local")
        return process_jarvis_request(question, user_id)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"OpenClaw no accesible: {e}, usando fallback local")
        return process_jarvis_request(question, user_id)
    except Exception as e:
        logger.error(f"Error con OpenClaw: {e}, usando fallback local")
        return process_jarvis_request(question, user_id)


def validate_alexa_request(request_data):
    """Valida que el request sea de Alexa (simplificado para desarrollo)"""
    try:
        # En producción necesitarías verificar signature, timestamp, etc.
        required_fields = ['version', 'session', 'request']
        for field in required_fields:
            if field not in request_data:
                return False, f"Missing field: {field}"
        
        # Verificar tipo de request
        if 'type' not in request_data['request']:
            return False, "Missing request type"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servicio está activo"""
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
        'openclaw_url': OPENCLAW_URL,
        'endpoints': ['/alexa', '/health']
    })

@app.route('/alexa', methods=['POST'])
def alexa_endpoint():
    """Endpoint principal para requests de Alexa"""
    try:
        # Log request
        logger.info("Received Alexa request")
        
        # Parse JSON
        request_data = request.get_json()
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
        
        # Validar request (simplificado para desarrollo)
        is_valid, message = validate_alexa_request(request_data)
        if not is_valid:
            logger.warning(f"Invalid request: {message}")
        
        # Determinar tipo de request
        request_type = request_data['request']['type']
        
        if request_type == 'LaunchRequest':
            # Usuario dice "Abre Jarvis"
            response_text = "¡Hola! Soy Jarvis, tu asistente DAW. Puedes preguntarme sobre tus proyectos, MySQL, o tareas. ¿En qué puedo ayudarte?"
            
        elif request_type == 'IntentRequest':
            # Usuario hace una pregunta
            intent_name = request_data['request']['intent']['name']
            
            if intent_name == 'AskJarvisIntent':
                # Extraer pregunta del slot
                slots = request_data['request']['intent'].get('slots', {})
                question_slot = slots.get('question', {})
                question = question_slot.get('value', '')
                
                if question:
                    # Proxy a OpenClaw, con fallback local
                    response_text = ask_openclaw(question)
                else:
                    response_text = "¿Qué te gustaría preguntarme? Por ejemplo: 'pregunta a Jarvis sobre MySQL'"
                    
            elif intent_name == 'AMAZON.HelpIntent':
                response_text = "Puedes decirme: 'pregunta a Jarvis' seguido de tu pregunta. También puedo ayudarte con: tus tareas DAW, estado del servidor, MySQL, o proyectos Java."
                
            elif intent_name in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
                response_text = "Hasta luego. ¡Buena suerte con tus estudios DAW!"
                
            else:
                response_text = f"Intent '{intent_name}' recibido. En desarrollo."
                
        elif request_type == 'SessionEndedRequest':
            response_text = "Sesión terminada. ¡Hasta pronto!"
            
        else:
            response_text = f"Tipo de request no reconocido: {request_type}"
        
        # Construir respuesta Alexa
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
                'shouldEndSession': request_type in ['SessionEndedRequest', 'AMAZON.StopIntent', 'AMAZON.CancelIntent']
            }
        }
        
        logger.info(f"Response: {response_text[:50]}...")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': f'Error procesando tu solicitud: {str(e)}'
                },
                'shouldEndSession': True
            }
        })

@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """Endpoint para testing manual"""
    if request.method == 'GET':
        return '''
        <h1>Jarvis Alexa Webhook Test</h1>
        <p>Endpoint: /alexa (POST)</p>
        <form action="/test" method="post">
            <textarea name="question" rows="3" cols="50" placeholder="Escribe tu pregunta..."></textarea><br>
            <input type="submit" value="Enviar a Jarvis">
        </form>
        '''
    else:
        question = request.form.get('question', '')
        response = ask_openclaw(question)
        return f'''
        <h1>Respuesta de Jarvis</h1>
        <p><strong>Pregunta:</strong> {question}</p>
        <p><strong>Respuesta:</strong> {response}</p>
        <p><small>Modo: {"OpenClaw" if OPENCLAW_TOKEN else "Fallback local"}</small></p>
        <a href="/test">Volver</a>
        '''

if __name__ == '__main__':
    # Configuración para desarrollo
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Jarvis Alexa Webhook on {host}:{port}")
    logger.info("Endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /alexa  - Alexa webhook")
    logger.info("  GET  /test   - Test interface")
    logger.info(f"OpenClaw: {'CONECTADO' if OPENCLAW_TOKEN else 'NO CONFIGURADO (usando fallback local)'}")
    if OPENCLAW_TOKEN:
        logger.info(f"OpenClaw URL: {OPENCLAW_URL}")
    
    app.run(host=host, port=port, debug=True)