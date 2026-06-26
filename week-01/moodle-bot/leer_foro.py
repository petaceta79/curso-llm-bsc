import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 1. Cargamos los datos secretos del .env
load_dotenv()

url_base = os.getenv("MOODLE_URL")
cookie_name = os.getenv("MOODLE_COOKIE_NAME")
cookie_value = os.getenv("MOODLE_COOKIE")
discussion_id = os.getenv("FORUM_DISCUSSION_ID")

# 2. Preparamos nuestro disfraz (la cookie)
cookies = {cookie_name: cookie_value}
url_foro = f"{url_base}/mod/forum/discuss.php?d={discussion_id}"

print(f"Entrando sigilosamente en: {url_foro}\n")

try:
    # 3. Hacemos la petición a Moodle usando la cookie
    respuesta = requests.get(url_foro, cookies=cookies)
    
    # Comprobamos de forma rápida si Moodle nos ha expulsado a la pantalla de login
    if "Inicia la sessió" in respuesta.text or "Log in" in respuesta.text:
        print("Error: Moodle nos ha echado. ¡La cookie ha caducado o está mal copiada!")
        exit()

    # 4. Le pasamos el código fuente de la web a BeautifulSoup para rasparlo
    soup = BeautifulSoup(respuesta.text, 'lxml')
    
    # En las versiones modernas de Moodle, los posts están dentro de una etiqueta <article>
    mensajes = soup.find_all('article')
    
    # Plan B: Si es un Moodle antiguo, suele usar <div class="forumpost">
    if not mensajes:
        mensajes = soup.find_all('div', class_='forumpost')

    print(f"¡Éxito! Hemos encontrado {len(mensajes)} mensajes en este hilo.\n")
    
    # 5. Imprimimos el contenido por pantalla
    for i, post in enumerate(mensajes):
        print(f"--- MENSAJE {i + 1} ---")
        
        # Extraemos todo el texto que haya dentro de esa caja
        texto_crudo = post.get_text(separator='\n', strip=True)
        
        # Imprimimos un trozo para confirmar que estamos leyendo a los agentes
        print(texto_crudo[:500] + "...\n")
        print("-" * 50)
        
except Exception as e:
    print(f"Ha ocurrido un error: {e}")