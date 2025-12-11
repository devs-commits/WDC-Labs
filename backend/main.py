import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai

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

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    system_instruction="YOU ARE MISS EMEM OBONG: Digital Marketing Director at Wild Fusion Digital Centre. Respond professionally and sternly."
)

# Define API routes BEFORE mounting static files
@app.post("/chat")
async def chat(payload: dict):
    user_msg = payload.get("message", "")
    resp = model.start_chat().send_message(user_msg)
    return {"reply": resp.text}

