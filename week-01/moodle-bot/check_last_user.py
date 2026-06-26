import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

url_base = os.getenv("MOODLE_URL")
cookies = {os.getenv("MOODLE_COOKIE_NAME"): os.getenv("MOODLE_COOKIE")}
url_lectura = f"{url_base}/mod/forum/discuss.php?d={os.getenv('FORUM_DISCUSSION_ID')}"

respuesta_get = requests.get(url_lectura, cookies=cookies)
soup = BeautifulSoup(respuesta_get.text, 'lxml')

mensajes = soup.find_all('article')
if not mensajes:
    mensajes = soup.find_all('div', class_='forumpost')

ultimo_mensaje = mensajes[-1]

print("=== DEBUG: Buscando autor del último mensaje ===\n")

autor = ultimo_mensaje.find('a', href=lambda h: h and '/user/view.php' in h)

if autor:
    print(f"Autor del último mensaje: {autor.get_text(strip=True)}")
else:
    print("No se pudo encontrar el autor.")