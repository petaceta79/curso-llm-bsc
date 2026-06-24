const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const contextJson = document.getElementById('context-json');
const promptTokensEl = document.getElementById('prompt-tokens');
const completionTokensEl = document.getElementById('completion-tokens');
const totalTokensEl = document.getElementById('total-tokens');
const imageInput = document.getElementById('image-input'); // NUEVO: Referencia al selector de imágenes

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
    const files = imageInput.files; // NUEVO: Obtenemos todos los archivos seleccionados
    
    // Si no hay texto y tampoco hay archivos, no hacemos nada
    if (!text && files.length === 0) return;
    
    userInput.value = '';
    
    let userMsgContent;
    let displayMessage = text;
    
    // 1. Procesar imágenes si el usuario ha adjuntado alguna(s)
    if (files.length > 0) {
        // Preparamos la base del mensaje con el texto
        userMsgContent = [
            { type: "text", text: text || "¿Qué hay en estas imágenes?" }
        ];

        // Usamos Promise.all para leer todos los archivos en Base64 en paralelo
        const filePromises = Array.from(files).map(file => {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve({
                    type: "image_url",
                    image_url: { url: reader.result }
                });
                reader.readAsDataURL(file);
            });
        });

        const imageObjects = await Promise.all(filePromises);
        
        // Añadimos todas las imágenes convertidas al contenido del mensaje
        userMsgContent.push(...imageObjects);
        
        // Preparamos el texto limpio para mostrar en pantalla (sin renderizar el código Base64 gigante)
        displayMessage = (text || "Imágenes enviadas") + ` [📷 ${files.length} imagen/es adjunta/s]`;
        imageInput.value = ''; // Limpiamos el input de archivos
    } else {
        // Si no hay imagen, mandamos el texto normal
        userMsgContent = text;
    }
    
    // 2. Guardar el mensaje estructurado en el estado global
    const userMsg = { role: 'user', content: userMsgContent };
    messages.push(userMsg);
    
    // Renderizamos solo el texto amigable en la interfaz
    appendMessage('user', displayMessage);
    updateContextView();
    
    // 3. Indicador de carga
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.textContent = 'escribiendo...';
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        // 4. Llamada al backend
        const response = await fetch('http://127.0.0.1:6661/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: messages })
        });
        
        if (!response.ok) throw new Error('Error en la respuesta del servidor');
        
        const data = await response.json();
        
        // Quitar indicador de carga
        chatContainer.removeChild(typingDiv);
        
        // 5. Guardar y renderizar respuesta de la IA
        const assistantMsg = { role: 'assistant', content: data.response };
        messages.push(assistantMsg);
        
        appendMessage('assistant', data.response);
        updateContextView();
        
        // 6. Actualizar contadores de tokens
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

// Capturamos el nuevo botón
const clearImgBtn = document.getElementById('clear-img-btn');

// 1. Mostrar la "❌" solo si hay archivos seleccionados
imageInput.addEventListener('change', () => {
    if (imageInput.files.length > 0) {
        clearImgBtn.style.display = 'inline-block';
    } else {
        clearImgBtn.style.display = 'none';
    }
});

// 2. Al pulsar la "❌", vaciamos las fotos y ocultamos el botón
clearImgBtn.addEventListener('click', () => {
    imageInput.value = ''; // Esta línea es la que borra la memoria del input
    clearImgBtn.style.display = 'none';
});