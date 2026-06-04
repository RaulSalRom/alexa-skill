#!/usr/bin/env python3
"""
Alexa Webhook SIMPLIFICADO - Sin Flask, solo pruebas
"""

import json
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import sys

PORT = 5000

def process_jarvis_request(question):
    """Procesa pregunta - respuestas estáticas"""
    question_lower = question.lower()
    
    responses = {
        "hola": "¡Hola Draken! Soy Jarvis. Endpoint Alexa funcionando.",
        "cómo estás": "El webhook está activo en puerto 5000. Listo para Alexa Skill.",
        "alexa": "Endpoint configurado para Alexa Skill. Necesitas HTTPS para producción.",
        "mysql": "MySQL 5.7 corriendo. Base de datos 'daw_db' disponible.",
        "servidor": "Servidor Ubuntu con IP Tailscale 100.78.237.50",
        "prueba": "✅ Webhook funcionando correctamente."
    }
    
    for key in responses:
        if key in question_lower:
            return responses[key]
    
    return f"Pregunta recibida: '{question}'. Webhook Alexa activo."

class AlexaHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Maneja GET requests (health check, test)"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'service': 'Jarvis Alexa Webhook (Simple)',
                'endpoint': '/alexa (POST)',
                'test': '/test?q=tu_pregunta'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif parsed.path == '/test':
            # Interface de testing simple
            query = parse_qs(parsed.query)
            question = query.get('q', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            if question:
                answer = process_jarvis_request(question)
                html = f"""
                <h1>Jarvis Alexa Webhook Test</h1>
                <p><strong>Pregunta:</strong> {question}</p>
                <p><strong>Respuesta:</strong> {answer}</p>
                <p><a href="/test">Nueva pregunta</a></p>
                """
            else:
                html = """
                <h1>Jarvis Alexa Webhook Test</h1>
                <form action="/test" method="get">
                    <input type="text" name="q" placeholder="Escribe tu pregunta">
                    <input type="submit" value="Preguntar">
                </form>
                <p>Ejemplos: ?q=hola, ?q=mysql, ?q=servidor</p>
                """
            
            self.wfile.write(html.encode())
            
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <h1>Jarvis Alexa Webhook</h1>
            <p>Endpoints:</p>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/test">/test</a> - Test interface</li>
                <li>/alexa - Alexa endpoint (POST only)</li>
            </ul>
            <p>Para Alexa Skill: POST JSON a /alexa</p>
            """
            self.wfile.write(html.encode())
    
    def do_POST(self):
        """Maneja POST requests (Alexa webhook)"""
        if self.path != '/alexa':
            self.send_response(404)
            self.end_headers()
            return
            
        try:
            # Leer JSON
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data)
            
            # Log simple
            print(f"Alexa request: {json.dumps(request_data, indent=2)[:200]}...")
            
            # Respuesta básica
            response = {
                'version': '1.0',
                'response': {
                    'outputSpeech': {
                        'type': 'PlainText',
                        'text': '✅ Webhook Jarvis funcionando. Integración Alexa en progreso.'
                    },
                    'shouldEndSession': True
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                'error': str(e),
                'status': 'error'
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def log_message(self, format, *args):
        """Log simplificado"""
        print(f"HTTP {self.address_string()} - {format % args}")

def main():
    print(f"🚀 Iniciando Jarvis Alexa Webhook en puerto {PORT}")
    print(f"📡 Endpoints:")
    print(f"  GET  http://localhost:{PORT}/health")
    print(f"  GET  http://localhost:{PORT}/test")
    print(f"  POST http://localhost:{PORT}/alexa")
    print(f"")
    print(f"📝 Para Alexa Skill:")
    print(f"  1. Usa ngrok: ngrok http {PORT}")
    print(f"  2. O Tailscale: tailscale funnel {PORT}")
    print(f"  3. Endpoint HTTPS: https://TU_URL/alexa")
    
    try:
        with socketserver.TCPServer(("", PORT), AlexaHandler) as httpd:
            print(f"✅ Servidor activo en puerto {PORT}")
            print(f"🔄 Presiona Ctrl+C para detener")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()