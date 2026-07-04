// Referencias UI de la pantalla Setup
const setupScreen = document.getElementById('setup-screen');
const chatScreen = document.getElementById('chat-screen');
const createAgentBtn = document.getElementById('create-agent-btn');
const loadAgentFile = document.getElementById('load-agent-file');

// Referencias UI del Chat
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const contextJson = document.getElementById('context-json');
const promptTokensEl = document.getElementById('prompt-tokens');
const completionTokensEl = document.getElementById('completion-tokens');
const totalTokensEl = document.getElementById('total-tokens');
const chatAgentName = document.getElementById('chat-agent-name');
const backBtn = document.getElementById('back-btn');
const saveAgentBtn = document.getElementById('save-agent-btn');
const imageInput = document.getElementById('image-input');
const clearImgBtn = document.getElementById('clear-img-btn');

// ESTADO GLOBAL DEL AGENTE
let currentAgent = {
    name: "",
    systemPrompt: "",
    template: "",
    contextText: "",
    history: []
};

// ==========================================
// 1. LÓGICA DE LA PANTALLA DE CONFIGURACIÓN
// ==========================================

createAgentBtn.addEventListener('click', async () => {
    const name = document.getElementById('agent-name').value.trim();
    const sysPrompt = document.getElementById('system-prompt').value.trim();
    const template = document.getElementById('prompt-template').value.trim();
    const contextFileInput = document.getElementById('context-file');

    // Validaciones básicas
    if (!name) return alert("Por favor, ponle un nombre al agente.");
    if (!template.includes("{context}") || !template.includes("{user_input}")) {
        return alert("El Prompt Template DEBE contener '{context}' y '{user_input}'.");
    }
    if (contextFileInput.files.length === 0) {
        return alert("Por favor, sube un archivo para el contexto del agente.");
    }

    const selectedFile = contextFileInput.files[0];

    // Mostrar estado de carga en el botón
    createAgentBtn.textContent = "Procesando archivo con MarkItDown...";
    createAgentBtn.disabled = true;

    // PREPARAR EL FORM DATA (Para enviar archivos binarios al backend)
    const formData = new FormData();
    formData.append('agent_name', name);
    formData.append('system_prompt', sysPrompt);
    formData.append('template', template);
    formData.append('file', selectedFile); // Mandamos el archivo real entero

    try {
        const response = await fetch('http://127.0.0.1:6661/save_agent', {
            method: 'POST',
            body: formData 
            // NOTA: No añadimos 'Content-Type' en los headers. 
            // Al pasarle un FormData, el navegador configura automáticamente el 'multipart/form-data' correcto.
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Error en el servidor");
        }

        // Para mantener el estado en local (guardar archivo .agente luego)
        // Guardamos una referencia temporal, el texto real limpio ya vive en el servidor.
        currentAgent = {
            name: name,
            systemPrompt: sysPrompt,
            template: template,
            contextText: `[Archivo procesado en servidor: ${selectedFile.name}]`, 
            history: [] 
        };

        startChatSession();

    } catch(e) {
        alert("Hubo un error al procesar el agente: " + e.message);
        console.error(e);
    } finally {
        createAgentBtn.textContent = "Crear Agente";
        createAgentBtn.disabled = false;
    }
});

// ==========================================
// 2. GUARDAR Y CARGAR AGENTE (Archivos Locales)
// ==========================================

// Guardar: Descarga el JSON disfrazado de .agente
saveAgentBtn.addEventListener('click', () => {
    const dataStr = JSON.stringify(currentAgent, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentAgent.name.replace(/\s+/g, '_')}.agente`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Cargar: Lee el archivo .agente
loadAgentFile.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        const fileContent = await file.text();
        const loadedAgent = JSON.parse(fileContent);
        
        // Validación básica para asegurar que es nuestro formato
        if (!loadedAgent.template || !loadedAgent.name) throw new Error("Archivo inválido.");
        
        currentAgent = loadedAgent;
        startChatSession();
    } catch (e) {
        alert("Error al cargar el archivo del agente. Asegúrate de que es un archivo .agente válido.");
        console.error(e);
    }
    event.target.value = ''; // Limpiar el input
});

// ==========================================
// 3. CAMBIO DE PANTALLAS Y RENDERIZADO
// ==========================================

function startChatSession() {
    // Cambiar vista
    setupScreen.style.display = 'none';
    chatScreen.style.display = 'flex';
    
    // Configurar UI
    chatAgentName.textContent = currentAgent.name;
    chatContainer.innerHTML = '';
    contextJson.textContent = "Esperando interacción...";
    promptTokensEl.textContent = "-";
    completionTokensEl.textContent = "-";
    totalTokensEl.textContent = "-";

    // Si había historial (agente cargado), re-dibujarlo
    if (currentAgent.history.length > 0) {
        currentAgent.history.forEach(msg => {
            let contentToDisplay = msg.content;
            if (Array.isArray(msg.content)) {
                const textObj = msg.content.find(item => item.type === "text");
                contentToDisplay = textObj ? textObj.text + " [📷 Imagen]" : "[📷 Imagen]";
            }
            appendMessage(msg.role, contentToDisplay);
        });
        updateContextExplorer(currentAgent.history[currentAgent.history.length - 2]?.content || "Historial cargado");
    }
}

backBtn.addEventListener('click', () => {
    if(confirm("¿Seguro que quieres salir? Asegúrate de guardar el agente si hay cambios.")) {
        chatScreen.style.display = 'none';
        setupScreen.style.display = 'block';
    }
});

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

// ==========================================
// 4. LÓGICA DE MENSAJES (COMUNICACIÓN CON BACKEND)
// ==========================================

// Para simular en pantalla lo que el backend arma y envía al LLM.
function updateContextExplorer(userText) {
    // Rellenamos el template temporalmente solo para mostrarlo en el frontend
    const filledPrompt = currentAgent.template
        .replace('{context}', currentAgent.contextText)
        .replace('{user_input}', userText);
    
    const payloadQueVeElLLM = {
        system_message: currentAgent.systemPrompt,
        messages_history: currentAgent.history,
        final_prompt_sent: filledPrompt
    };

    contextJson.textContent = JSON.stringify(payloadQueVeElLLM, null, 2);
}

async function sendMessage() {
    const text = userInput.value.trim();
    const files = imageInput.files; 
    
    if (!text && files.length === 0) return;
    
    userInput.value = '';
    let userMsgContent;
    let displayMessage = text;
    
    if (files.length > 0) {
        userMsgContent = [{ type: "text", text: text || "¿Qué hay en estas imágenes?" }];
        const filePromises = Array.from(files).map(file => {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve({ type: "image_url", image_url: { url: reader.result } });
                reader.readAsDataURL(file);
            });
        });
        const imageObjects = await Promise.all(filePromises);
        userMsgContent.push(...imageObjects);
        displayMessage = (text || "Imágenes enviadas") + ` [📷 ${files.length} adjunta/s]`;
        
        imageInput.value = ''; 
        clearImgBtn.style.display = 'none';
    } else {
        userMsgContent = text;
    }
    
    // Guardar en el historial del agente
    const userMsg = { role: 'user', content: userMsgContent };
    currentAgent.history.push(userMsg);
    
    appendMessage('user', displayMessage);
    
    // Actualizamos el explorador de contexto para que se vea el Template rellenado
    updateContextExplorer(text);
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.textContent = 'escribiendo...';
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        /*
          NOTA PARA EL BACKEND:
          Ahora el backend recibirá el texto, el contexto, el template y el historial.
          Debes ajustar tu FastAPI para procesar este body:
        */
        // NUEVO PAYLOAD (Solo manda el nombre, historial y mensaje nuevo)
        const requestPayload = {
            agent_name: currentAgent.name,
            history: currentAgent.history,
            user_input: userMsgContent
        };

        const response = await fetch('http://127.0.0.1:6661/chat', { // Asegúrate que el puerto es correcto
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestPayload)
        });
        
        if (!response.ok) throw new Error('Error en la respuesta del servidor');
        
        const data = await response.json();
        chatContainer.removeChild(typingDiv);
        
        const assistantMsg = { role: 'assistant', content: data.response };
        currentAgent.history.push(assistantMsg);
        
        appendMessage('assistant', data.response);
        
        promptTokensEl.textContent = data.usage?.prompt_tokens || 0;
        completionTokensEl.textContent = data.usage?.completion_tokens || 0;
        totalTokensEl.textContent = data.usage?.total_tokens || 0;

        // 👇 AÑADE ESTO: Actualiza la caja negra con la VERDADERA info que construyó el backend 👇
        const payloadReal = {
            system_message: currentAgent.systemPrompt,
            // Mostramos el historial (sin contar el mensaje que acabamos de enviar ni la respuesta)
            messages_history: currentAgent.history.slice(0, -2), 
            final_prompt_sent: data.final_prompt_sent // <--- Aquí viene el texto GIGANTE de FastAPI
        };
        contextJson.textContent = JSON.stringify(payloadReal, null, 2);
        // 👆 HASTA AQUÍ 👆
        
    } catch (error) {
        console.error('Error:', error);
        chatContainer.removeChild(typingDiv);
        appendMessage('assistant', 'Error de conexión. Revisa FastAPI.');
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

imageInput.addEventListener('change', () => {
    clearImgBtn.style.display = imageInput.files.length > 0 ? 'inline-block' : 'none';
});

clearImgBtn.addEventListener('click', () => {
    imageInput.value = ''; 
    clearImgBtn.style.display = 'none';
});