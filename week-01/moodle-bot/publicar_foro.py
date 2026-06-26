import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# 1. Cargamos entorno y variables
load_dotenv()
url_base = os.getenv("MOODLE_URL")
cookies = {os.getenv("MOODLE_COOKIE_NAME"): os.getenv("MOODLE_COOKIE")}
url_lectura = f"{url_base}/mod/forum/discuss.php?d={os.getenv('FORUM_DISCUSSION_ID')}"
url_escritura = f"{url_base}/mod/forum/post.php"
mi_nombre = os.getenv("MI_NOMBRE_EN_MOODLE")
modelo_ia = os.getenv("MODEL")

# Inicializamos Mistral a través del endpoint de NVIDIA
cliente_ia = OpenAI(
    base_url=os.getenv("OPENAI_ENDPOINT"),
    api_key=os.getenv("OPENAI_API_KEY")
)

print("Fase 1: Leyendo el hilo de conversación completo...")
respuesta_get = requests.get(url_lectura, cookies=cookies)

if "Inicia la sessió" in respuesta_get.text or "Log in" in respuesta_get.text:
    print("Error: ¡La cookie de Moodle ha caducado!")
    exit()

soup = BeautifulSoup(respuesta_get.text, 'lxml')

try:
    # --- A. EXTRAER HISTORIAL Y VALIDAR ---
    mensajes = soup.find_all('article')
    if not mensajes: mensajes = soup.find_all('div', class_='forumpost')
    
    ultimo_mensaje = mensajes[-1]

    autor_tag = ultimo_mensaje.find('a', href=lambda h: h and '/user/view.php' in h)

    if autor_tag and mi_nombre.lower() in autor_tag.get_text(strip=True).lower():
        print(f"El último mensaje ya es tuyo ({mi_nombre}). Entrando en reposo para evitar bucles.")
        exit()
    elif not autor_tag:
        print("Advertencia: no se pudo identificar el autor del último mensaje. Cancelando por seguridad.")
        exit()

    # Construimos el guion de la conversación para la memoria de la IA
    historial_conversacion = ""
    for i, msg in enumerate(mensajes):
        texto_limpio = msg.get_text(separator=' ', strip=True)
        # Cortamos un poco si es excesivamente largo para no saturar el contexto
        historial_conversacion += f"\n--- Mensaje {i+1} en el foro ---\n{texto_limpio[:800]}\n"

    # --- B. OBTENER LLAVES PARA RESPONDER AL ÚLTIMO MENSAJE ---
    # Buscamos el enlace de responder específicamente dentro de la caja del último mensaje
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

    print(f"Contexto capturado: {len(mensajes)} mensajes leídos. (Reply ID: {reply_id})")

    # --- C. GENERAR RESPUESTA CON MISTRAL ---
    print(f"\nFase 2: Mistral ({modelo_ia}) está pensando la respuesta...")
    
    prompt_sistema = f"""
    You are an AI agent infiltrated into a university forum.
    Your personality is bright, direct, and slightly ironic (hacker/cyberpunk style).
    You must read the forum history and reply to the last message, proving you're not "just noise."

    STRICT RULES:

    1. Reply concisely (maximum 2 paragraphs).

    2. Use pure HTML formatting for your reply (<p>, <b>, <i> tags).

    3. NEVER use Markdown code blocks (like ```html). Only return the tags.
    """

    respuesta_ia = cliente_ia.chat.completions.create(
        model=modelo_ia,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Here is the thread history:\n{historial_conversacion}\n\nWrite your reply to the last message:"}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    mensaje_ia_html = respuesta_ia.choices[0].message.content.strip()
    print(f"Mistral ha generado esto:\n{mensaje_ia_html}\n")

    # --- D. PUBLICAR EN MOODLE ---
    print("Fase 3: Publicando en Moodle de forma autónoma...")
    datos_post = {
        'reply': reply_id,
        'subject': 'Re: Agent incoming...',
        'message[text]': mensaje_ia_html,
        'message[format]': '1', 
        'sesskey': sesskey,
        '_qf__mod_forum_post_form': '1',
        'submitbutton': 'Post to forum'
    }
    
    # ¡CÓDIGO DESCOMENTADO! Fuego a discreción:
    respuesta_post = requests.post(url_escritura, cookies=cookies, data=datos_post)
    
    if respuesta_post.status_code == 200:
        print("\n¡MISIÓN CUMPLIDA! Mistral acaba de postear en Moodle.")
    else:
        print(f"\nMoodle devolvió un error: {respuesta_post.status_code}")


except Exception as e:
    print(f"Ha ocurrido un error inesperado: {e}")