#!/usr/bin/env python3
import pytesseract
from PIL import Image
import sys

image_path = "/home/draken/.openclaw/media/inbound/file_1---64a220e6-2399-451a-9379-3d4d4a0922e3.jpg"

try:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang='spa+eng')
    print("TEXTO EXTRAÍDO:")
    print("=" * 60)
    print(text)
    print("=" * 60)
    
    # Análisis simple
    text_lower = text.lower()
    
    print("\nANÁLISIS:")
    if 'tailscale' in text_lower:
        print("✅ Contiene: Tailscale")
    if 'https' in text_lower or 'http' in text_lower:
        print("✅ Contiene: URL/HTTP")
    if 'certificate' in text_lower or 'certificado' in text_lower:
        print("✅ Contiene: Certificado SSL")
    if 'serve' in text_lower:
        print("✅ Contiene: Serve")
    if 'funnel' in text_lower:
        print("✅ Contiene: Funnel")
    if 'ngrok' in text_lower:
        print("✅ Contiene: ngrok")
    if 'alexa' in text_lower:
        print("✅ Contiene: Alexa")
    if 'amazon' in text_lower:
        print("✅ Contiene: Amazon")
    if 'enable' in text_lower or 'habilitar' in text_lower:
        print("✅ Contiene: Habilitar/Enable")
    if 'error' in text_lower or 'denied' in text_lower:
        print("⚠️  Contiene: Error/Denegado")
    if 'success' in text_lower or 'correcto' in text_lower:
        print("🎉 Contiene: Éxito/Success")
        
    # Buscar URLs
    lines = text.split('\n')
    print("\nPOSIBLES URLs:")
    for line in lines:
        if 'http' in line.lower() or '.ts.net' in line.lower() or '.ngrok.io' in line.lower():
            print(f"  {line.strip()}")
            
except Exception as e:
    print(f"Error: {e}")