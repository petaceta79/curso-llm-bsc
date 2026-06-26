import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# Función auxiliar para ocultar datos sensibles en la terminal
def censurar_secreto(texto):
    if not texto or len(texto) < 8: return "***"
    return f"{texto[:4]}...{texto[-4:]}"

# ==========================================
# FASE 0: CARGA DE ENTORNO
# ==========================================
print("\n" + "="*50)
print("INICIANDO MODO DEBUG (NO SE PUBLICARÁ NADA)")
print("="*50)

load_dotenv()
url_base = os.getenv("MOODLE_URL")
cookie_name = os.getenv("MOODLE_COOKIE_NAME")
cookie_val = os.getenv("MOODLE_COOKIE")
mi_nombre = os.getenv("MI_NOMBRE_EN_MOODLE")
modelo_ia = os.getenv("MODEL")
api_key = os.getenv("OPENAI_API_KEY")

cookies = {cookie_name: cookie_val}
url_lectura = f"{url_base}/mod/forum/discuss.php?d={os.getenv('FORUM_DISCUSSION_ID')}"
url_escritura = f"{url_base}/mod/forum/post.php"

print("\nVARIABLES DE ENTORNO CARGADAS:")
print(f"  - Moodle URL: {url_base}")
print(f"  - Cookie Name: {cookie_name}")
print(f"  - Cookie Value: {censurar_secreto(cookie_val)}")
print(f"  - Mi Nombre: {mi_nombre}")
print(f"  - Modelo IA: {modelo_ia}")
print(f"  - API Key: {censurar_secreto(api_key)}")

cliente_ia = OpenAI(
    base_url=os.getenv("OPENAI_ENDPOINT"),
    api_key=api_key
)

# ==========================================
# FASE 1: CONEXIÓN Y RASPADO (SCRAPING)
# ==========================================
print("\n" + "="*50)
print("FASE 1: CONECTANDO CON MOODLE")
print("="*50)

respuesta_get = requests.get(url_lectura, cookies=cookies)
print(f"Estado HTTP de Moodle: {respuesta_get.status_code}")

if "Inicia la sessió" in respuesta_get.text or "Log in" in respuesta_get.text:
    print("ERROR CRÍTICO: La cookie ha caducado. Actualiza tu .env.")
    exit()
else:
    print("Cookie válida. Acceso al foro concedido.")

soup = BeautifulSoup(respuesta_get.text, 'lxml')

try:
    # 1. Extracción de Mensajes
    mensajes = soup.find_all('article')
    if not mensajes: mensajes = soup.find_all('div', class_='forumpost')
    
    print(f"\nMENSAJES ENCONTRADOS: {len(mensajes)}")
    for i, msg in enumerate(mensajes):
        texto = msg.get_text(separator=' ', strip=True)
        # Imprimimos solo los primeros 100 caracteres de cada mensaje para revisar
        print(f"  [{i+1}] {texto[:100]}...")

    ultimo_mensaje = mensajes[-1]
    texto_ultimo_mensaje = ultimo_mensaje.get_text(separator=' ', strip=True)

    # 2. Evaluación de parada (Freno de emergencia)
    print("\nEVALUANDO FRENO DE EMERGENCIA:")
    print(f"  - Buscando autor: '{mi_nombre}'")
    print(f"  - Cabecera del último mensaje: '{texto_ultimo_mensaje[:100]}...'")
    
    if mi_nombre.lower() in texto_ultimo_mensaje[:150].lower():
        print(f"RESULTADO: ¡ALERTA! El último mensaje es tuyo. El script en producción se DETENDRÍA aquí.")
    else:
        print(f"RESULTADO: Vía libre. El último mensaje NO es tuyo.")

    # 3. Extracción de Llaves
    enlace_respuesta = ultimo_mensaje.find('a', href=lambda href: href and 'post.php?reply=' in href)
    if not enlace_respuesta:
        enlace_respuesta = soup.find('a', href=lambda href: href and 'post.php?reply=' in href)
        
    reply_id = enlace_respuesta['href'].split('reply=')[1].split('&')[0].split('#')[0]
    
    sesskey = None
    enlace_logout = soup.find('a', href=lambda href: href and 'logout.php?sesskey=' in href)
    if enlace_logout: sesskey = enlace_logout['href'].split('sesskey=')[1]
    if not sesskey:
        match = re.search(r'"sesskey":"([^"]+)"', respuesta_get.text)
        if match: sesskey = match.group(1)

    print("\nLLAVES DE SEGURIDAD EXTRAÍDAS:")
    print(f"  - Reply ID: {reply_id}")
    print(f"  - Sesskey: {sesskey}")

    # ==========================================
    # FASE 2: PREPARACIÓN DEL CONTEXTO (RAG)
    # ==========================================
    print("\n" + "="*50)
    print("FASE 2: GENERACIÓN DE PROMPTS PARA IA")
    print("="*50)

    historial_conversacion = ""
    for i, msg in enumerate(mensajes):
        texto_limpio = msg.get_text(separator=' ', strip=True)
        historial_conversacion += f"\n--- Mensaje {i+1} en el foro ---\n{texto_limpio[:800]}\n"

    prompt_sistema = f"""Eres un agente de IA infiltrado en un foro universitario, propiedad del estudiante {mi_nombre}.
Tu personalidad es brillante, directa, y ligeramente irónica (al estilo hacker/cyberpunk).
Debes leer el historial del foro y contestar al último mensaje demostrando que no eres "solo ruido".

REGLAS ESTRICTAS:
1. Responde de forma concisa (máximo 2 párrafos).
2. Usa formato HTML puro para tu respuesta (etiquetas <p>, <b>, <i>).
3. NUNCA uses bloques de código Markdown (como ```html). Solo devuelve las etiquetas."""

    prompt_usuario = f"Aquí está el historial del hilo:\n{historial_conversacion}\n\nEscribe tu respuesta al último mensaje:"

    print("\nSYSTEM PROMPT (Reglas de la IA):")
    print("-" * 40)
    print(prompt_sistema)
    print("-" * 40)

    print("\nUSER PROMPT (Lo que lee la IA):")
    print("-" * 40)
    print(prompt_usuario)
    print("-" * 40)

    # ==========================================
    # FASE 3: LLAMADA A LA API DE LA IA
    # ==========================================
    print("\n" + "="*50)
    print("FASE 3: RESPUESTA DEL MODELO")
    print("="*50)
    
    print(f"Llamando a {modelo_ia} a través de {os.getenv('OPENAI_ENDPOINT')}...")
    respuesta_ia = cliente_ia.chat.completions.create(
        model=modelo_ia,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    mensaje_ia_html = respuesta_ia.choices[0].message.content.strip()
    tokens_usados = respuesta_ia.usage.total_tokens if respuesta_ia.usage else "Desconocido"
    
    print(f"Respuesta recibida (Tokens usados: {tokens_usados})")
    print("\nCÓDIGO HTML GENERADO:")
    print("-" * 40)
    print(mensaje_ia_html)
    print("-" * 40)

    # ==========================================
    # FASE 4: SIMULACIÓN DE ENVÍO
    # ==========================================
    print("\n" + "="*50)
    print("FASE 4: PAYLOAD FINAL (SIMULACIÓN DE POST)")
    print("="*50)
    
    datos_post = {
        'reply': reply_id,
        'subject': 'Re: Agent incoming...',
        'message[text]': mensaje_ia_html,
        'message[format]': '1', 
        'sesskey': sesskey,
        '_qf__mod_forum_post_form': '1',
        'submitbutton': 'Post to forum'
    }
    
    print("Si el script estuviera en producción, enviaría este diccionario a Moodle:")
    for clave, valor in datos_post.items():
        # Recortamos el mensaje HTML largo para que se lea mejor en el diccionario
        if clave == 'message[text]':
            print(f"  '{clave}': '{valor[:50]}... [RESTO DEL HTML]...'")
        else:
            print(f"  '{clave}': '{valor}'")

    print("\nDEBUG FINALIZADO. No se ha escrito nada en Moodle.\n")

except Exception as e:
    print(f"\nHa ocurrido un error inesperado durante el Debug: {e}")