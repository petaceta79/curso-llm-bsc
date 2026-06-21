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
        // Renderiza Markdown usando marked.js
        msgDiv.innerHTML = marked.parse(content);
    } else {
        msgDiv.textContent = content;
    }
    
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateContextView() {
    // Muestra el array de mensajes actual en formato JSON
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
    
    // 2. Indicador de carga
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.textContent = 'escribiendo...';
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        // 3. Llamada al backend
        const response = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: messages })
        });
        
        if (!response.ok) throw new Error('Error en la respuesta del servidor');
        
        const data = await response.json();
        
        // Quitar indicador de carga
        chatContainer.removeChild(typingDiv);
        
        // 4. Guardar y renderizar respuesta de la IA
        const assistantMsg = { role: 'assistant', content: data.response };
        messages.push(assistantMsg);
        
        appendMessage('assistant', data.response);
        updateContextView();
        
        // 5. Actualizar contadores de tokens
        promptTokensEl.textContent = data.usage.prompt_tokens;
        completionTokensEl.textContent = data.usage.completion_tokens;
        totalTokensEl.textContent = data.usage.total_tokens;
        
    } catch (error) {
        console.error('Error:', error);
        typingDiv.textContent = 'Error al conectar con el servidor. Asegúrate de que el backend esté corriendo.';
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});