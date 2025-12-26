// ================= BACKEND URL =================
function getBackendURL(endpoint = "/chat") {
    return "http://127.0.0.1:8000" + endpoint;
}

// ======= Global Variables =======
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let selectedImage = null;
let thinkingEl = null;

const micBtn = document.getElementById('micBtn');

// ======= Image Input Handling =======
document.getElementById('imageInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            selectedImage = file;
            const preview = document.getElementById('imagePreviewContainer');
            preview.innerHTML = `<img id="imagePreview" src="${event.target.result}" />`;
        };
        reader.readAsDataURL(file);
    }
});

// ======= Update Mic / Send Icon =======
function updateMicSendIcon() {
    const input = document.getElementById('inputMsg');
    const hasText = input.value.trim().length > 0;
    if (hasText) {
        micBtn.innerHTML = '&#10148;';
        micBtn.title = 'Send message';
    } else {
        micBtn.innerHTML = '&#128266;';
        micBtn.title = 'Record Audio';
    }
}

document.getElementById('inputMsg').addEventListener('input', updateMicSendIcon);
updateMicSendIcon();

// ======= Timestamp =======
function getTimestamp() {
    const now = new Date();
    return now.getHours().toString().padStart(2,'0') + ':' +
           now.getMinutes().toString().padStart(2,'0');
}

// ======= Thinking Indicator now *Typing* =======
function showThinking() {
    if (!thinkingEl) {
        thinkingEl = document.createElement("div");
        thinkingEl.className = "msg bot thinking";
        thinkingEl.innerHTML = `
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        `;
        document.querySelector(".messages").appendChild(thinkingEl);
    }
}

function hideThinking() {
    if (thinkingEl) {
        thinkingEl.remove();
        thinkingEl = null;
    }
}

// ======= Add Message =======
function addMessage(text, type) {
    const msgBox = document.getElementById("messages");
    const msg = document.createElement("div");
    msg.classList.add("msg", type);

    if (type === "bot") msg.innerHTML = marked.parse(text);
    else msg.textContent = text;

    const ts = document.createElement("div");
    ts.classList.add("timestamp");
    ts.textContent = getTimestamp();

    msg.appendChild(ts);
    msgBox.appendChild(msg);
    msgBox.scrollTop = msgBox.scrollHeight;
}

// ======= Send Text Message =======
async function sendMsg(payload, chat_history) {
    const input = document.getElementById("inputMsg");
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    input.value = "";
    updateMicSendIcon();
    showThinking();

    try {
        const response = await fetch(getBackendURL("/chat"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: msg,
                user_info: {
                    role: "intern",
                    source: "web"
                },
                chat_history: chat_history,
                greeted_today: false
            })
        });

        hideThinking();

        const data = await response.json();
        addMessage(data.content || data.reply, "bot");
    } catch (error) {
        hideThinking();
        addMessage("Error: Could not connect to backend.", "bot");
        console.error(error);
    }
}

// ======= Send Image + Text =======
async function sendImageWithText() {
    if (!selectedImage) return;

    const textMsg = document.getElementById("inputMsg").value.trim();
    addMessage(`Image sent${textMsg ? ": " + textMsg : ""}`, "user");
    showThinking();

    try {
        const formData = new FormData();
        formData.append('file', selectedImage);
        if (textMsg) formData.append('message', textMsg);

        const response = await fetch(getBackendURL('/image-and-text'), {
            method: "POST",
            body: formData
        });

        hideThinking();
        const data = await response.json();
        addMessage(data.reply, "bot");

        selectedImage = null;
        document.getElementById('imagePreviewContainer').innerHTML = '';
        document.getElementById('inputMsg').value = '';
        updateMicSendIcon();
    } catch (error) {
        hideThinking();
        addMessage("Error sending image.", "bot");
    }
}

// ======= Audio Recording =======
async function toggleMicrophone() {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
            isRecording = false;
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await sendAudio(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        addMessage("Recording...", "user");
    } else {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
}

// ======= Send Audio =======
async function sendAudio(audioBlob) {
    showThinking();

    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');

    try {
        const response = await fetch(getBackendURL('/transcribe-audio'), {
            method: "POST",
            body: formData
        });

        hideThinking();
        const data = await response.json();
        addMessage(data.reply, "bot");
    } catch (error) {
        hideThinking();
        addMessage("Audio transcription failed.", "bot");
    }
}

// ======= Mic / Send Button =======
function handleMicClick() {
    const input = document.getElementById('inputMsg');
    if (input.value.trim()) {
        selectedImage ? sendImageWithText() : sendMsg();
    } else {
        toggleMicrophone();
    }
}

// ======= Enter to Send =======
document.getElementById('inputMsg').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        selectedImage ? sendImageWithText() : sendMsg();
    }
});
