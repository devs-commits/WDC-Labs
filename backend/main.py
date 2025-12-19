
import os
import io

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
from ai_engine.services.chat_service import use_chat, get_model

from backend import mock_methods

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load `.env` from project root so GEMINI_API_KEY can be set there for local dev
load_dotenv()

# Configure Gemini API key from environment (now loaded from .env)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise Exception("GEMINI_API_KEY not set in environment variables! Create a .env with GEMINI_API_KEY=<your_key>")

genai.configure(api_key=api_key)

# Pydantic model for chat endpoint
class ChatMessage(BaseModel):
    message: str
    user_info: dict
    chat_history: list
    greeted_today: bool

# Define API routes BEFORE mounting static files
@app.post("/chat")
async def chat(payload: ChatMessage):
    """Handle chat messages using Gemini model."""

    response = use_chat(payload)
    
    return {
        "role": "assistant",
        "content": response["reply"]
    }

@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    """Analyze an uploaded image using Gemini vision."""
    try:
        # Read image file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Send image to Gemini for analysis
        response = get_model().generate_content([
            "Analyze this image and provide insights professionally.",
            image
        ])
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error analyzing image: {str(e)}"}


@app.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio and analyze it."""
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Upload file to Gemini (using File API)
        audio_file = genai.upload_file(io.BytesIO(audio_data), mime_type=file.content_type)
        
        # Send audio to Gemini for transcription and analysis
        chat_prompt = "Transcribe this audio and provide a response as Miss Emem."
        response = get_model().generate_content([chat_prompt, audio_file])
        
        # Clean up uploaded file
        genai.delete_file(audio_file.name)
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error transcribing audio: {str(e)}"}


@app.post("/image-and-text")
async def image_and_text(file: UploadFile = File(...), message: str = ""):
    """Analyze image with accompanying text message."""
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        prompt = message if message else "Analyze this image."
        response = get_model().generate_content([prompt, image])
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error processing image and text: {str(e)}"}


# Serve frontend static files and index if available
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
try:
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
except Exception:
    pass


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="12" ry="12" fill="#2a4fff"/>'
        '<circle cx="32" cy="32" r="14" fill="#fff"/></svg>'
    )
    from fastapi.responses import Response
    return Response(content=svg, media_type='image/svg+xml')


"""
@app.get("/", include_in_schema=False)
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type='text/html')
    return {"status": "ok", "message": "WDC Labs API is running!"}
"""

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "message": "WDC Labs API is running!"}


