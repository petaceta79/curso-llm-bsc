import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_ENDPOINT")
)

class Message(BaseModel):
    role: str
    content: Union[str, list]

class ChatRequest(BaseModel):
    messages: List[Message]

class SaveRequest(BaseModel):
    username: str
    messages: List[Message]

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        messages = [msg.model_dump() for msg in request.messages]
        response = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=messages,
            stream=False
        )
        
        return {
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save")
async def save_history(request: SaveRequest):
    try:
        # 1. Le decimos a Python que cree la carpeta si no existe (exist_ok=True evita errores si ya está creada)
        os.makedirs("historiales", exist_ok=True)
        
        # 2. Añadimos "historiales/" a la ruta del archivo
        filename = f"historiales/historial_{request.username}.json"
        
        msgs_dict = [msg.model_dump() for msg in request.messages]
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(msgs_dict, f, ensure_ascii=False, indent=4)
            
        return {"status": "Guardado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load/{username}")
async def load_history(username: str):
    try:
        # Buscamos en la nueva carpeta
        filename = f"historiales/historial_{username}.json"
        
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                saved_messages = json.load(f)
            return {"messages": saved_messages}
        else:
            return {"messages": []} 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users")
async def list_saved_users():
    try:
        usuarios_guardados = []
        
        # Primero comprobamos que la carpeta existe para que no dé error al buscar
        if os.path.exists("historiales"):
            # Buscamos los archivos DENTRO de la carpeta 'historiales'
            archivos = os.listdir('historiales')
            
            for archivo in archivos:
                if archivo.startswith("historial_") and archivo.endswith(".json"):
                    nombre = archivo.replace("historial_", "").replace(".json", "")
                    usuarios_guardados.append(nombre)
                    
        return {"users": usuarios_guardados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)