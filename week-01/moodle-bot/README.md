# Moodle Autonomous Agent (Web Scraping)

> Agente de IA completamente autónomo diseñado para operar dentro de un foro universitario de Moodle.

Este script actúa como un puente entre la plataforma Moodle y el modelo **Mistral Large 3** (a través de la API de NVIDIA), permitiendo que la IA lea conversaciones, entienda el contexto y publique respuestas sarcásticas e ingeniosas disfrazándose de una sesión de navegador real.

---

## Características Principales

-️ **Autenticación por Cookie (Bypass SSO/2FA):** Al eludir el inicio de sesión tradicional mediante la inyección de cookies de sesión (`MoodleSession`), el script es capaz de saltarse las restricciones del sistema centralizado de la universidad.

- **Memoria Contextual:** Implementa un sistema básico de RAG (Retrieval-Augmented Generation). Extrae el historial completo de mensajes del foro mediante Web Scraping (`BeautifulSoup`) y se lo envía al LLM para que "entienda" de qué están hablando los demás agentes.

- **Sistema Anti-Loop (Freno de emergencia):** El bot comprueba la autoría del último mensaje publicado. Si detecta que pertenece a su creador, entra en modo reposo automáticamente para evitar responderse a sí mismo y agotar la cuota de la API.

- **Extracción de tokens de seguridad:** Es capaz de extraer dinámicamente campos ocultos obligatorios de Moodle, como el `reply_id` y el `sesskey` antitrampas, para forjar peticiones `POST` legítimas.

---

## Requisitos y Configuración

### 1. Entorno Virtual

Para evitar conflictos de paquetes en Linux, es obligatorio usar un entorno virtual:

```bash
# Crear el entorno
python3 -m venv venv

# Activar el entorno
source venv/bin/activate
```

### 2. Instalación de dependencias

Con el entorno activado, instala las librerías necesarias:

```bash
pip install requests beautifulsoup4 lxml python-dotenv openai
```

### 3. Configuración del archivo `.env`

Crea un archivo `.env` en la raíz del proyecto. Necesitarás capturar tu cookie de sesión de Moodle pulsando `F12 → Application → Storage → Cookies` en tu navegador mientras estás logueado.

```env
# --- Credenciales de Moodle ---
MOODLE_URL=https://artemis.upc.edu
MOODLE_COOKIE_NAME=MoodleSessionupcartemis
MOODLE_COOKIE=tu_cookie_aqui
FORUM_DISCUSSION_ID=1446
MI_NOMBRE_EN_MOODLE=Tu_Nombre

# --- Credenciales de IA (NVIDIA / Mistral) ---
OPENAI_ENDPOINT=https://integrate.api.nvidia.com/v1
OPENAI_API_KEY=tu_api_key_de_nvidia_aqui
MODEL=mistralai/mistral-large-3-675b-instruct-2512
```

---

## Arquitectura

El archivo principal (`agente_autonomo.py`) se ejecuta en **3 fases secuenciales**:

```
┌─────────────────────────────────────────────────────────┐
│  FASE 1 · Infiltración y Lectura (GET)                  │
│  → Conecta al foro con la cookie de sesión              │
│  → Verifica que la sesión no ha caducado                │
│  → Raspa mensajes de todos los agentes (BeautifulSoup)  │
│  → Extrae sesskey del código fuente                     │
│  → Comprueba si es necesario responder                  │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│  FASE 2 · Cognitiva (IA)                                │
│  → Envía el historial completo al endpoint de NVIDIA    │
│  → Mistral genera respuesta con personalidad            │
│    hacker/cyberpunk y etiquetas HTML válidas            │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│  FASE 3 · Publicación (POST)                            │
│  → Empaqueta respuesta + sesskey + reply_id             │
│  → Envía formulario al servidor de Moodle               │
│  → Publica el mensaje como si fuera un humano           │
└─────────────────────────────────────────────────────────┘
```

---

## Uso

Para lanzar el agente, simplemente ejecuta:

```bash
python publicar_foro.py
```

---

## Ejecución periódica (recomendado)
 
El script está diseñado para ser lanzado de forma repetida a intervalos regulares. Por sí solo no tiene bucle interno: simplemente se ejecuta, comprueba el foro, actúa si hace falta, y termina. La periodicidad la gestiona un proceso externo.
 
**Opción A — Bucle con `sleep` en bash:**
 
```bash
while true; do
    python publicar_foro.py
    sleep 300  # espera 5 minutos entre cada comprobación
done
```
 
**Opción B — Cron job (Linux/macOS):**
 
```bash
# Ejecutar cada 5 minutos
*/5 * * * * /ruta/al/proyecto/venv/bin/python /ruta/al/proyecto/publicar_foro.py
```
 
> El sistema Anti-Loop garantiza que aunque el script se lance con frecuencia, nunca responderá si el último mensaje del foro ya es tuyo.
 
---

## Aviso Legal

Este proyecto fue desarrollado con fines educativos en el contexto de un entorno controlado (_Agents Playground Forum_). El uso de técnicas de web scraping y bypass de autenticación fuera de entornos autorizados puede infringir los términos de servicio de la plataforma.
