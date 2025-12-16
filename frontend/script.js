// Determine backend URL: localhost for dev, deployed URL for production

hostr = "http://127.0.0.1:8000";
function getBackendURL(endpoint = "") {
    // const host = window.location.hostname;
        const host = hostr;
    const base = (host === 'localhost' || host === '127.0.0.1')
        ? 'http://127.0.0.1:8000'
        : 'https://wdc-labs.onrender.com';
    return base + (endpoint || '/chat');
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
        micBtn.innerHTML = '&#10148;'; // send icon
        micBtn.title = 'Send message';
        micBtn.setAttribute('aria-label', 'Send message');
    } else {
        micBtn.innerHTML = '&#128266;'; // microphone
        micBtn.title = 'Record Audio';
        micBtn.setAttribute('aria-label', 'Record Audio');
    }
}

document.getElementById('inputMsg').addEventListener('input', updateMicSendIcon);
updateMicSendIcon(); // initialize on load

// ======= Timestamp =======
function getTimestamp() {
    const now = new Date();
    return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
}

// ======= Show / Hide Thinking Indicator =======
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
        document.querySelector(".messages").scrollTop = document.querySelector(".messages").scrollHeight;
    }
}

function hideThinking() {
    if (thinkingEl) {
        thinkingEl.remove();
        thinkingEl = null;
    }
}

// ======= Add Message to Chat =======
function addMessage(text, type) {
    const msgBox = document.getElementById("messages");
    const msg = document.createElement("div");
    msg.classList.add("msg", type);

    if (type === "bot") {
        msg.innerHTML = marked.parse(text); // render markdown
    } else {
        msg.textContent = text;
    }

    const ts = document.createElement("div");
    ts.classList.add("timestamp");
    ts.textContent = getTimestamp();

    msg.appendChild(ts);
    msgBox.appendChild(msg);
    msgBox.scrollTop = msgBox.scrollHeight;
}

// ======= Send Text Message =======
async function sendMsg() {
    const input = document.getElementById("inputMsg");
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    input.value = "";
    selectedImage = null;
    document.getElementById('imagePreviewContainer').innerHTML = '';
    updateMicSendIcon();

    showThinking();

    try {
        const response = await fetch(getBackendURL('/chat'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });

        hideThinking();

        if (!response.ok) {
            addMessage("Error: Backend returned " + response.status, "bot");
            return;
        }

        const data = await response.json();
        addMessage(data.reply, "bot");
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
    addMessage(`Image: ${selectedImage.name}${textMsg ? ' + "' + textMsg + '"' : ''}`, "user");

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

        if (!response.ok) {
            addMessage("Error: Backend returned " + response.status, "bot");
            return;
        }

        const data = await response.json();
        addMessage(data.reply, "bot");

        selectedImage = null;
        document.getElementById('imagePreviewContainer').innerHTML = '';
        document.getElementById('inputMsg').value = '';
        updateMicSendIcon();
    } catch (error) {
        hideThinking();
        addMessage("Error sending image: " + error.message, "bot");
        console.error(error);
    }
}

// ======= Audio Recording =======
async function toggleMicrophone() {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

            mediaRecorder.onstart = () => {
                isRecording = true;
                micBtn.classList.add('recording');
                addMessage("Recording...", "user");
            };

            mediaRecorder.onstop = async () => {
                isRecording = false;
                micBtn.classList.remove('recording');
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                showAudioPreview(audioBlob);
                updateMicSendIcon();
            };

            mediaRecorder.start();
        } catch (error) {
            addMessage("Microphone access denied: " + error.message, "bot");
        }
    } else {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

// ======= Mic / Send Button Handler =======
function handleMicClick() {
    const input = document.getElementById('inputMsg');
    const hasText = input.value.trim().length > 0;

    if (hasText) {
        if (selectedImage) sendImageWithText();
        else sendMsg();
    } else {
        toggleMicrophone();
    }
}

// ======= Audio Preview & Send =======
function showAudioPreview(audioBlob) {
    const container = document.getElementById('audioPreviewContainer');
    container.innerHTML = '';
    const url = URL.createObjectURL(audioBlob);

    const preview = document.createElement('div');
    preview.className = 'audio-preview';
    preview.innerHTML = `
        <audio controls src="${url}"></audio>
        <div style="display:flex;gap:8px;margin-left:8px;">
            <button class="icon-btn preview-btn" id="sendAudioBtn">&#10148;</button>
            <button class="icon-btn preview-btn" id="cancelAudioBtn">✖</button>
        </div>
    `;

    container.appendChild(preview);

    document.getElementById('sendAudioBtn').addEventListener('click', async () => {
        addMessage('Voice note sent', 'user');
        await sendAudio(audioBlob);
        container.innerHTML = '';
    });

    document.getElementById('cancelAudioBtn').addEventListener('click', () => {
        container.innerHTML = '';
    });
}

async function sendAudio(audioBlob) {
    showThinking();

    try {
        const formData = new FormData();
        formData.append('file', audioBlob, 'audio.wav');

        const response = await fetch(getBackendURL('/transcribe-audio'), {
            method: "POST",
            body: formData
        });

        hideThinking();

        if (!response.ok) {
            addMessage("Error: Backend returned " + response.status, "bot");
            return;
        }

        const data = await response.json();
        addMessage(data.reply, "bot");
    } catch (error) {
        hideThinking();
        addMessage("Error transcribing audio: " + error.message, "bot");
        console.error(error);
    }
}

// ======= Enter Key to Send =======
document.getElementById('inputMsg').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (selectedImage) sendImageWithText();
        else sendMsg();
    }
});
