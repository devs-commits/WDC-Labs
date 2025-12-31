"""
Docstring for backend.main
"""

import os
import io
import mimetypes
import requests

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
from ai_engine.services.chat_service import use_chat, get_model
from ai_engine.utils import load_md


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

class Submission(BaseModel):
    taskId: int
    userId: str
    fileUrl: str
    fileName: str
    taskTitle: str | None = None
    taskContent: str | None = None
    chatHistory: list | None = None

class TaskGenerationRequest(BaseModel):
    track: str
    experience_level: str
    task_number: int    
    previous_task_performance: str | None = None
    user_city: str | None = None        # e.g., "Lagos"
    user_country: str | None = None     # e.g., "Nigeria"
    user_country_code: str | None = None  # e.g., "NG"


class HintRequest(BaseModel):
    taskId: int
    taskTitle: str
    taskContent: str
    userContext: str | None = None

class CVGenerationRequest(BaseModel):
    user_id: str
    user_name: str
    track: str
    start_date: str  # e.g., "2025-12-01"
    end_date: str | None = None  # Optional, use "Present" if ongoing
    tasks: List[dict]
    feedback: List[dict]


@app.post("/chat")
async def chat(payload: ChatMessage):
    """Handle chat messages using Gemini model with frontend-provided location."""

    user_info = payload.user_info
    raw_location = user_info.get("location")

    # Normalize location into standard fields
    if isinstance(raw_location, dict):
        city = raw_location.get("city") or raw_location.get("City") or "your city"
        country = raw_location.get("country") or raw_location.get("Country") or "your country"
        country_code = raw_location.get("country_code") or raw_location.get("countryCode") or ""
    elif isinstance(raw_location, str):
        # If frontend sends a string like "Lagos, Nigeria"
        parts = [p.strip() for p in raw_location.split(",")]
        city = parts[0] if len(parts) > 0 else "your city"
        country = parts[1] if len(parts) > 1 else "your country"
        country_code = ""
    else:
        # No location provided
        city = "your city"
        country = "your country"
        country_code = ""

    # Inject clean location fields into user_info (for use in prompt)
    user_info.update({
        "city": city,
        "country": country,
        "country_code": country_code,
        "location_summary": f"{city}, {country}" + (f" ({country_code})" if country_code else "")
    })

    # Optional: Log for debugging
    print(f"[LOCATION] User in: {city}, {country} ({country_code})")

    # Pass to your existing use_chat (no other changes needed)
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


@app.post("/analyze-submission")
def analyze_submission(submission: Submission):
    """Analyze a file submission (image or text) from a URL."""
    try:
        print(f"Analyzing submission for Task {submission.taskId}. URL: {submission.fileUrl}")
        
        # Download the file using requests
        response = requests.get(submission.fileUrl, headers={'User-Agent': 'WDC-Labs-Backend/1.0'})
        
        if response.status_code != 200:
            return {"reply": f"Error downloading file: HTTP {response.status_code} - {response.text[:200]}"}
            
        file_data = response.content
            
        # Determine file type
        mime_type, _ = mimetypes.guess_type(submission.fileName)
        
        grading_system = load_md("ai_engine/prompts/grading_sytem.md")

        # Construct prompt
        task_context = ""
        if submission.taskTitle:
            task_context += f"Task Title: {submission.taskTitle}\n"
        if submission.taskContent:
            task_context += f"Task Description: {submission.taskContent}\n"
            
        history_context = ""
        if submission.chatHistory:
             history_context = f"Previous Chat History:\n{submission.chatHistory}\n"

        prompt = (
            f"You are an expert mentor. A student has submitted the following file "
            f"for Task ID {submission.taskId}.\n\n"
            f"{task_context}\n"
            f"{history_context}\n"
            f"Please analyze the submission against the task requirements. "
            f"Provide constructive feedback, highlighting what is good and what needs improvement. "
            f"Be professional.\n\n"
            f"Use the following grading system guide:\n{grading_system}\n\n"
            f"IMPORTANT: At the very end of your response, you MUST include a JSON object with the score and completion status. "
            f"Format: ```json\n{{\"score\": <0-100>, \"completed\": <true/false>}}\n```. "
            f"Mark 'completed': true ONLY if the score is greater than 80."
        )
        
        content = [prompt]
        
        if mime_type and mime_type.startswith('image'):
            try:
                image = Image.open(io.BytesIO(file_data))
                content.append(image)
            except Exception:
                 return {"reply": "Error: The file appears to be an image but could not be opened."}
        elif mime_type == 'application/pdf':
            content.append({
                "mime_type": "application/pdf",
                "data": file_data
            })
        elif mime_type and (mime_type.startswith('audio') or mime_type.startswith('video')):
             content.append({
                "mime_type": mime_type,
                "data": file_data
            })
        else:
            # Assume text/code
            try:
                text_content = file_data.decode('utf-8')
                content.append(f"File Content ({submission.fileName}):\n{text_content}")
            except UnicodeDecodeError:
                # Fallback for other binary types that might be supported by Gemini (e.g. CSV if not detected as text)
                # or just to give a better error message.
                return {"reply": f"Error: The file '{submission.fileName}' ({mime_type}) is not a supported text, image, PDF, audio, or video file."}

        model = get_model()
        response = model.generate_content(content)
        
        # Extract JSON from response if present
        import re
        import json
        
        reply_text = response.text
        completed = False
        score = 0
        
        # Look for JSON block at the end
        json_match = re.search(r"```json\n(.*?)\n```", reply_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                score = data.get("score", 0)
                completed = data.get("completed", False)
                # Remove the JSON block from the visible reply so the user doesn't see raw JSON
                reply_text = reply_text.replace(json_match.group(0), "").strip()
            except:
                pass

        return {
            "reply": reply_text,
            "score": score,
            "completed": completed
        }

    except Exception as e:
        return {"reply": f"Error analyzing submission: {str(e)}"}


@app.post("/generate-tasks")
def generate_tasks(request: TaskGenerationRequest):
    try:
        # Load the prompt template
        prompt_template = load_md("ai_engine/prompts/task_generation.md")
        
        if not prompt_template:
            return {"error": "Could not load task generation prompt."}

        # Fill in the original placeholders
        prompt = prompt_template.replace("{track}", request.track)
        prompt = prompt_template.replace("{experience_level}", request.experience_level)
        prompt = prompt_template.replace("{task_number}", str(request.task_number))
        prompt = prompt_template.replace("{previous_performance}", request.previous_task_performance or "N/A (First Task)")

        # === NEW: Add location context to the prompt ===
        city = request.user_city or "an unspecified city"
        country = request.user_country or "an unspecified country"
        country_code = request.user_country_code or ""

        location_context = f"{city}, {country}"
        if country_code:
            location_context += f" ({country_code})"

        # Only add location if it's meaningful
        if "unspecified" not in city.lower() and "unspecified" not in country.lower():
            location_line = f"The intern is located in {location_context}."
        else:
            location_line = "The intern's location is not specified."

        # Insert location info clearly into the prompt
        prompt += f"\n\n=== INTERN LOCATION CONTEXT ===\n{location_line}\nUse this to select real, existing local companies and context-appropriate scenarios."

        # Optional: Log for debugging
        print(f"[TASK GEN] Generating task for intern in: {location_context}")

        # Get model with JSON output
        model = genai.GenerativeModel(
            model_name=os.environ.get("GENAI_MODEL", "gemini-2.5-flash"),
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(prompt)
        
        import json
        try:
            tasks_data = json.loads(response.text)
            return tasks_data
        except json.JSONDecodeError as e:
            return {"error": "Failed to parse AI response", "raw": response.text, "parse_error": str(e)}

    except Exception as e:
        return {"error": f"Error generating tasks: {str(e)}"}

@app.post("/get-hint")
def get_hint(request: HintRequest):
    """Generate a hint for a specific task."""
    try:
        prompt_template = load_md("ai_engine/prompts/hint.md")
        if not prompt_template:
            return {"error": "Could not load hint prompt."}
        
        prompt = prompt_template.replace("{task_title}", request.taskTitle)
        prompt = prompt.replace("{task_content}", request.taskContent)
        prompt = prompt.replace("{user_context}", request.userContext or "No specific question asked.")
        
        model = get_model()
        response = model.generate_content(prompt)
        
        return {"hint": response.text}
    except Exception as e:
        return {"error": f"Error generating hint: {str(e)}"}


@app.post("/generate-cv")
def generate_cv(request: CVGenerationRequest):
    try:
        # 1. Load the CV prompt template
        prompt_template = load_md("ai_engine/prompts/cv.md")
        if not prompt_template:
            return {"error": "Could not load CV generation prompt."}

        # 2. Use tasks and feedback from the request directly
        tasks = request.tasks or []
        feedback_by_task = {f['task_id']: f for f in (request.feedback or [])}

        # 3. Build formatted task + feedback list
        tasks_context = []
        for task in tasks:
            feedback = feedback_by_task.get(task.get('id'), {})
            feedback_text = feedback.get('feedback', 'No detailed feedback recorded.')
            grade = feedback.get('grade', 'Not graded')

            tasks_context.append(
                f"- Task: {task.get('title')}\n"
                f"  Description: {task.get('brief_content')}\n"
                f"  Feedback: {feedback_text}\n"
                f"  Grade/Outcome: {grade}"
            )

        tasks_section = "\n\n".join(tasks_context) if tasks_context else "No tasks completed yet."

        # 4. Overall summary
        completion_rate = f"{len(tasks)} tasks completed"
        overall_notes = f"Intern showed {'strong' if len(tasks) >= 8 else 'developing'} independence and professionalism in the {request.track} track."

        # 5. Build full prompt
        full_prompt = f"""
        {prompt_template}

        === INTERN CONTEXT ===
        Name: {request.user_name}
        Track: {request.track}
        Internship Period: {request.start_date} – {request.end_date or "Present"}

        Completed Tasks and Feedback:
        {tasks_section}

        Overall Performance Notes:
        - {completion_rate}
        - {overall_notes}
        """

        # 6. Call Gemini
        model = genai.GenerativeModel(
            model_name=os.environ.get("GENAI_MODEL", "gemini-2.5-flash")
        )
        response = model.generate_content(full_prompt)
        cv_markdown = response.text.strip()

        return {
            "cv_content": cv_markdown
        }

    except Exception as e:
        import traceback
        print(f"[CV ERROR] {traceback.format_exc()}")
        return {"error": f"Failed to generate CV: {str(e)}"}


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


