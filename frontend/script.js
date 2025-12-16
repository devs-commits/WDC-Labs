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

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let selectedImage = null;
    const micBtn = document.getElementById('micBtn');

    // Initialize image input handler
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

    // Update mic/send icon based on input content
    function updateMicSendIcon() {
        const input = document.getElementById('inputMsg');
        const hasText = input.value.trim().length > 0;
        if (hasText) {
            micBtn.innerHTML = '&#10148;'; // send icon
            micBtn.title = 'Send message';
            micBtn.setAttribute('aria-label', 'Send message');
        } else {
            micBtn.innerHTML = '&#128266;'; // microphone (restored original glyph)
            micBtn.title = 'Record Audio';
            micBtn.setAttribute('aria-label', 'Record Audio');
        }
    }

    // Listen for typing to swap icon
    document.getElementById('inputMsg').addEventListener('input', updateMicSendIcon);
    // Initialize icon on load
    updateMicSendIcon();

    function getTimestamp() {
        const now = new Date();
        return now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    }

    async function sendMsg() {
        const input = document.getElementById("inputMsg");
        const msg = input.value.trim();
        if (!msg) return;

        addMessage(msg, "user");
        input.value = "";
        selectedImage = null;
        document.getElementById('imagePreviewContainer').innerHTML = '';

        try {
            const response = await fetch(getBackendURL('/chat'), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: msg })
            });

            if (!response.ok) {
                addMessage("Error: Backend returned " + response.status, "bot");
                return;
            }

            const data = await response.json();
            addMessage(data.reply, "bot");
        } catch (error) {
            addMessage("Error: Could not connect to backend.", "bot");
            console.error(error);
        }
    }

    async function sendImageWithText() {
        if (!selectedImage) {
            return;
        }

        const textMsg = document.getElementById("inputMsg").value.trim();
        addMessage(`Image: ${selectedImage.name}${textMsg ? ' + "' + textMsg + '"' : ''}`, "user");

        try {
            const formData = new FormData();
            formData.append('file', selectedImage);
            if (textMsg) formData.append('message', textMsg);

            const response = await fetch(getBackendURL('/image-and-text'), {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                addMessage("Error: Backend returned " + response.status, "bot");
                return;
            }

            const data = await response.json();
            addMessage(data.reply, "bot");

            // Clear image preview
            selectedImage = null;
            document.getElementById('imagePreviewContainer').innerHTML = '';
            document.getElementById('inputMsg').value = '';
        } catch (error) {
            addMessage("Error sending image: " + error.message, "bot");
            console.error(error);
        }
    }

    async function toggleMicrophone() {
        if (!isRecording) {
            // Start recording
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

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
            // Stop recording
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    // Handle click on the mic/send button: send text when there's text, otherwise toggle mic
    function handleMicClick() {
        const input = document.getElementById('inputMsg');
        const hasText = input.value.trim().length > 0;
        if (hasText) {
            if (selectedImage) {
                sendImageWithText();
            } else {
                sendMsg();
            }
        } else {
            toggleMicrophone();
        }
    }

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
            // show as user message
            addMessage('Voice note sent', 'user');
            await sendAudio(audioBlob);
            container.innerHTML = '';
        });

        document.getElementById('cancelAudioBtn').addEventListener('click', () => {
            container.innerHTML = '';
        });
    }

    async function sendAudio(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'audio.wav');

            const response = await fetch(getBackendURL('/transcribe-audio'), {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                addMessage("Error: Backend returned " + response.status, "bot");
                return;
            }

            const data = await response.json();
            addMessage(data.reply, "bot");
        } catch (error) {
            addMessage("Error transcribing audio: " + error.message, "bot");
            console.error(error);
        }
    }

    function addMessage(text, type) {
    const msgBox = document.getElementById("messages");
    const msg = document.createElement("div");
    msg.classList.add("msg", type);

    // 👇 render markdown for bot, plain text for user
    if (type === "bot") {
        msg.innerHTML = marked.parse(text);
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


    // Listen for Enter key to send message
    document.getElementById('inputMsg').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (selectedImage) {
                sendImageWithText();
            } else {
                sendMsg();
            }
        }
    });