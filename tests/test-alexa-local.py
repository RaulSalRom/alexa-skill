#!/usr/bin/env python3
"""
Testing framework LOCAL para Alexa Skill
NO necesita cuenta Amazon
"""

import json
import requests
import unittest
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

# URL del webhook local
WEBHOOK_URL = "http://localhost:5000/alexa"

def create_alexa_request(intent_name="AskJarvisIntent", question="", request_type="IntentRequest"):
    """Crea request Alexa simulado"""
    if request_type == "LaunchRequest":
        return {
            "version": "1.0",
            "session": {
                "new": True,
                "sessionId": "session123",
                "application": {
                    "applicationId": "amzn1.ask.skill.test.local"
                },
                "user": {
                    "userId": "test-user-draken"
                }
            },
            "request": {
                "type": "LaunchRequest",
                "requestId": "request123",
                "timestamp": "2024-01-01T00:00:00Z",
                "locale": "es-ES"
            }
        }
    
    elif request_type == "IntentRequest":
        slots = {}
        if question:
            slots = {
                "question": {
                    "name": "question",
                    "value": question
                }
            }
        
        return {
            "version": "1.0",
            "session": {
                "new": True,
                "sessionId": "session123",
                "application": {
                    "applicationId": "amzn1.ask.skill.test.local"
                },
                "user": {
                    "userId": "test-user-draken"
                }
            },
            "request": {
                "type": "IntentRequest",
                "requestId": "request123",
                "timestamp": "2024-01-01T00:00:00Z",
                "locale": "es-ES",
                "intent": {
                    "name": intent_name,
                    "slots": slots
                }
            }
        }
    
    elif request_type == "SessionEndedRequest":
        return {
            "version": "1.0",
            "session": {
                "new": False,
                "sessionId": "session123",
                "application": {
                    "applicationId": "amzn1.ask.skill.test.local"
                },
                "user": {
                    "userId": "test-user-draken"
                }
            },
            "request": {
                "type": "SessionEndedRequest",
                "requestId": "request123",
                "timestamp": "2024-01-01T00:00:00Z",
                "locale": "es-ES",
                "reason": "USER_INITIATED"
            }
        }

def test_alexa_endpoint():
    """Testea el endpoint Alexa localmente"""
    print("🔍 Testing Alexa Webhook Local...")
    
    # Verificar webhook corriendo
    try:
        health = requests.get("http://localhost:5000/health", timeout=5)
        if health.status_code != 200:
            print("❌ Webhook no responde")
            return False
        print("✅ Webhook activo")
    except:
        print("❌ No se puede conectar al webhook")
        print("   Ejecuta: cd alexa-jarvis && ./start.sh")
        return False
    
    # Test 1: LaunchRequest
    print("\n1. Testing LaunchRequest...")
    launch_req = create_alexa_request(request_type="LaunchRequest")
    response = requests.post(WEBHOOK_URL, json=launch_req, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        speech = data.get('response', {}).get('outputSpeech', {}).get('text', '')
        print(f"   ✅ Respuesta: {speech[:50]}...")
    else:
        print(f"   ❌ Error: {response.status_code}")
        return False
    
    # Test 2: Pregunta específica
    print("\n2. Testing AskJarvisIntent...")
    test_questions = [
        ("hola", "¡Hola Draken!"),
        ("mysql", "MySQL"),
        ("servidor", "servidor"),
        ("tareas", "tareas")
    ]
    
    all_passed = True
    for question, expected in test_questions:
        req = create_alexa_request(question=question)
        response = requests.post(WEBHOOK_URL, json=req, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            speech = data.get('response', {}).get('outputSpeech', {}).get('text', '')
            
            if expected.lower() in speech.lower():
                print(f"   ✅ '{question}': OK")
            else:
                print(f"   ⚠️  '{question}': Esperaba '{expected}', obtuve '{speech[:30]}...'")
                all_passed = False
        else:
            print(f"   ❌ '{question}': Error {response.status_code}")
            all_passed = False
    
    # Test 3: SessionEndedRequest
    print("\n3. Testing SessionEndedRequest...")
    end_req = create_alexa_request(request_type="SessionEndedRequest")
    response = requests.post(WEBHOOK_URL, json=end_req, timeout=10)
    
    if response.status_code == 200:
        print("   ✅ Sesión terminada correctamente")
    else:
        print(f"   ⚠️  Error terminando sesión: {response.status_code}")
    
    return all_passed

def run_interactive_test():
    """Modo interactivo para testing manual"""
    print("\n🎤 MODO INTERACTIVO - Alexa Skill Testing")
    print("Escribe preguntas para Jarvis (o 'salir' para terminar)")
    print("-" * 50)
    
    while True:
        try:
            question = input("\nTu pregunta: ").strip()
            
            if question.lower() in ['salir', 'exit', 'quit']:
                print("👋 Saliendo del modo interactivo")
                break
            
            if not question:
                continue
            
            # Crear request
            req = create_alexa_request(question=question)
            
            # Enviar al webhook
            response = requests.post(WEBHOOK_URL, json=req, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                speech = data.get('response', {}).get('outputSpeech', {}).get('text', '')
                card = data.get('response', {}).get('card', {}).get('content', '')
                
                print(f"\n🤖 JARVIS responde:")
                print(f"   🔊: {speech}")
                if card:
                    print(f"   📋: {card}")
                
                # Verificar si termina sesión
                should_end = data.get('response', {}).get('shouldEndSession', False)
                if should_end:
                    print("   ⏹️  Sesión terminada")
                    break
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text[:200])
                
        except KeyboardInterrupt:
            print("\n👋 Interrumpido por usuario")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def main():
    print("=" * 60)
    print("ALEXA SKILL TESTING LOCAL - SIN CUENTA AMAZON")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        run_interactive_test()
    else:
        # Test automático
        success = test_alexa_endpoint()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 TODOS LOS TESTS PASARON")
            print("✅ Skill Alexa funcionando correctamente")
            print("\n📋 Resumen:")
            print("1. Webhook activo en puerto 5000")
            print("2. Respuestas predefinidas funcionando")
            print("3. Listo para conectar a Amazon Console")
            print("\n🚀 Siguiente paso:")
            print("   Usa ngrok para HTTPS: ngrok http 5000")
            print("   Luego crea Skill en Amazon Developer Console")
        else:
            print("⚠️  ALGUNOS TESTS FALLARON")
            print("Revisa el webhook y vuelve a intentar")
        
        print("\n💡 Para modo interactivo:")
        print("   python test-alexa-local.py interactive")

if __name__ == "__main__":
    main()