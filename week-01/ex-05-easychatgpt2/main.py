import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import tiktoken

load_dotenv()

app = FastAPI()

# Configuración segura de CORS para Streaming (allow_credentials=False evita bloqueos de navegador)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializamos el cliente de OpenAI con Timeout para evitar bloqueos infinitos
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_ENDPOINT"),
    timeout=10.0
)

# Cargamos el codificador estándar para calcular los tokens reales del prompt
encoder = tiktoken.get_encoding("cl100k_base")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        messages = [msg.model_dump() for msg in request.messages]
        
        # Llamada con stream=True a NVIDIA
        response = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=messages,
            stream=True
        )
        
        # Función generadora (El Proxy trabajando en tiempo real)
        def generate():
            # 1. Calculamos EXACTAMENTE los tokens del texto de entrada (Prompt)
            prompt_text = " ".join([m["content"] for m in messages])
            prompt_tokens_real = len(encoder.encode(prompt_text))
            
            completion_tokens_real = 0
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        # 2. Cada fragmento recibido equivale exactamente a 1 token real de salida
                        completion_tokens_real += 1 
                        yield f"data: {json.dumps({'type': 'content', 'text': delta})}\n\n"
                
            # 3. Al terminar el flujo, el proxy inyecta el conteo final auditado
            usage_data = {
                "prompt_tokens": prompt_tokens_real,
                "completion_tokens": completion_tokens_real,
                "total_tokens": prompt_tokens_real + completion_tokens_real
            }
            yield f"data: {json.dumps({'type': 'usage', 'usage': usage_data})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Puerto interno 8000 (el docker-compose lo mapeará hacia afuera en el 6661)
    uvicorn.run(app, host="0.0.0.0", port=8000)