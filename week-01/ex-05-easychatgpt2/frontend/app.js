const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const contextJson = document.getElementById('context-json');
const promptTokensEl = document.getElementById('prompt-tokens');
const completionTokensEl = document.getElementById('completion-tokens');
const totalTokensEl = document.getElementById('total-tokens');

// Estado global de la conversación
let messages = [];

function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role === 'user' ? 'user' : 'assistant'}`;
    
    if (role === 'assistant') {
        msgDiv.innerHTML = marked.parse(content);
    } else {
        msgDiv.textContent = content;
    }
    
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateContextView() {
    contextJson.textContent = JSON.stringify(messages, null, 2);
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    
    userInput.value = '';
    
    // 1. Guardar y renderizar mensaje del usuario
    const userMsg = { role: 'user', content: text };
    messages.push(userMsg);
    appendMessage('user', text);
    updateContextView();
    
    // 2. Preparamos el contenedor visual en el chat para el streaming de la IA
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant';
    msgDiv.textContent = '...'; // Indicador temporal de carga
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    let assistantContent = ""; // Acumulador del texto en streaming
    
    try {
        // 3. Petición al backend apuntando al puerto externo de docker (6661)
        const response = await fetch('http://127.0.0.1:6661/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: messages })
        });
        
        if (!response.ok) throw new Error('Error en la respuesta del servidor');
        
        // 4. Leer el flujo de datos (Stream) línea por línea
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        msgDiv.textContent = ""; // Quitamos los puntos de carga suspensivos
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);
                        
                        if (data.type === 'content') {
                            // Añadimos el token recibido y procesamos Markdown en vivo
                            assistantContent += data.text;
                            msgDiv.innerHTML = marked.parse(assistantContent);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                            
                        } else if (data.type === 'usage') {
                            // Al terminar el stream, pintamos el gasto real auditado por el proxy
                            promptTokensEl.textContent = data.usage.prompt_tokens;
                            completionTokensEl.textContent = data.usage.completion_tokens;
                            totalTokensEl.textContent = data.usage.total_tokens;
                        }
                    } catch (e) {
                        // Fragmento JSON incompleto debido al buffering del stream, se ignora y se une en el siguiente ciclo
                    }
                }
            }
        }
        
        // 5. Guardar la respuesta final completa en el historial global de la memoria
        messages.push({ role: 'assistant', content: assistantContent });
        updateContextView();
        
    } catch (error) {
        console.error('Error:', error);
        msgDiv.textContent = 'Error al conectar con el servidor en modo stream.';
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});