# EASY-CHATGPT Proxy

Proxy de FastAPI para interactuar con el modelo Gemma-4-31B-IT de NVIDIA.

## Cómo ejecutar
1. Crear un archivo `.env` con las siguientes variables:
   - OPENAI_API_KEY=...
   - OPENAI_ENDPOINT=...
   - MODEL=...
2. Levantar con Docker:
   ```bash
   docker compose up --build
   ```
3. Acceder en el navegador: http://127.0.0.1:6661
