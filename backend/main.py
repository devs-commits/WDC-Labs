# backend/main.py
'''
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Configure Gemini API key
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Use a dummy model if API key not set for local testing
class DummyModel:
    def start_chat(self):
        return self
    def send_message(self, msg):
        return type("Resp", (), {"text": f"Miss Emem says: {msg}"})

model = DummyModel() if not api_key else genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    system_instruction="""
    You are Miss Emem Obong, the Digital Marketing Director at Wild Fusion Digital Centre.
    Speak in a professional, stern, crisp tone, as if training a junior intern.
    """
)

@app.post("/chat")
async def chat(payload: dict):
    user_msg = payload.get("message", "")
    try:
        resp = model.start_chat().send_message(user_msg)
        return {"reply": resp.text}
    except Exception as e:
        # Return error as reply so frontend never gets 404
        return {"reply": f"Error from AI: {str(e)}"}

'''

import os
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

# Configure Gemini API key from environment
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise Exception("GEMINI_API_KEY not set in environment variables!")

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

# Serve frontend last (so it doesn't intercept API routes)
# app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

