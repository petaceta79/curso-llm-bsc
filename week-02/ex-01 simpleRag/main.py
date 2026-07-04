import os
import json
import re
import shutil
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union
from openai import OpenAI
from dotenv import load_dotenv
from markitdown import MarkItDown  # <-- Nueva librería

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

# Instanciamos MarkItDown
md = MarkItDown()

# ==========================================
# MODELOS DE DATOS (Pydantic para el Chat)
# ==========================================
class Message(BaseModel):
    role: str
    content: Union[str, list]

class ChatRequest(BaseModel):
    agent_name: str
    history: List[Message]
    user_input: Union[str, list]

# ==========================================
# FUNCIÓN DE LIMPIEZA ADICIONAL
# ==========================================
def clean_text(text: str) -> str:
    """Elimina espacios en blanco excesivos que puedan quedar."""
    return re.sub(r'\s+', ' ', text).strip()

# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/save_agent")
async def save_agent(
    agent_name: str = Form(...),
    system_prompt: str = Form(...),
    template: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Recibe cualquier archivo por formulario, extrae su texto usando MarkItDown,
    y guarda la configuración del agente.
    """
    try:
        os.makedirs("agents_data", exist_ok=True)
        filename = f"agents_data/{agent_name}.json"
        
        # 1. Guardar temporalmente el archivo subido para que MarkItDown lo pueda leer
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Usar MarkItDown para convertir el archivo (PDF, DOCX, XLSX, etc.) a Markdown
        try:
            result = md.convert(temp_file_path)
            extracted_text = result.text_content
        except Exception as conversion_error:
            raise Exception(f"MarkItDown no pudo procesar este archivo: {conversion_error}")
        finally:
            # Eliminar siempre el archivo temporal del disco
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        # 3. Opcional: Limpieza final de espacios
        cleaned_context = clean_text(extracted_text)
        
        # 4. Guardar la estructura en el JSON del agente
        agent_data = {
            "systemPrompt": system_prompt,
            "template": template,
            "contextText": cleaned_context
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(agent_data, f, ensure_ascii=False, indent=4)
            
        return {"status": f"Agente '{agent_name}' creado con éxito usando MarkItDown."}
        
    except Exception as e:
        print(f"❌ ERROR AL CREAR AGENTE: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """Permanece igual: carga el JSON del agente y ejecuta el LLM"""
    try:
        filename = f"agents_data/{request.agent_name}.json"
        
        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail="No tengo cargado a ese agente.")
            
        with open(filename, "r", encoding="utf-8") as f:
            agent_config = json.load(f)
            
        template = agent_config["template"]
        context_text = agent_config["contextText"]
        system_prompt = agent_config["systemPrompt"]
        
        final_user_content = None
        text_sent = ""
        
        if isinstance(request.user_input, str):
            text_sent = template.replace("{context}", context_text).replace("{user_input}", request.user_input)
            final_user_content = text_sent
            
        elif isinstance(request.user_input, list):
            final_user_content = []
            for item in request.user_input:
                if item.get("type") == "text":
                    text_sent = template.replace("{context}", context_text).replace("{user_input}", item.get("text", ""))
                    final_user_content.append({"type": "text", "text": text_sent})
                else:
                    final_user_content.append(item)
        
        messages_for_llm = [{"role": "system", "content": system_prompt}]
        for msg in request.history:
            messages_for_llm.append(msg.model_dump())
            
        messages_for_llm.append({"role": "user", "content": final_user_content})

        response = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=messages_for_llm,
            stream=False
        )
        
        return {
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "final_prompt_sent": text_sent
        }
    except Exception as e:
        print(f"❌ ERROR EXACTO EN EL BACKEND: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)