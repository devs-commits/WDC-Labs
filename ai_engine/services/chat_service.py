# ai_engine/services/chat_service.py

import traceback
from datetime import date
import time
import random
from google.api_core.exceptions import ResourceExhausted
import os
import google.generativeai as genai

from ai_engine.utils import load_md
from ai_engine.category_detector import detect_category, get_md_for_category
from backend import mock_methods

""" 
ai_engine.services.chat_service. This module should not perform network or API calls at import time. 
The Generative AI model and chats are initialized lazily inside `use_chat` to avoid failures during application startup. 
"""

GREETING_RULES = (
    "If greeted_today = false, you may introduce yourself briefly. - "
    "If greeted_today = true, DO NOT introduce yourself again."
)

# Model name can be configured via `GENAI_MODEL` env var. If not set, use
# gemini-2.5-flash (faster, cheaper, better free-tier quota than pro models).
DEFAULT_MODEL = os.environ.get("GENAI_MODEL", "gemini-2.5-flash")

def get_model(model_name: str | None = None):
    name = model_name or DEFAULT_MODEL
    return genai.GenerativeModel(model_name=name)

def use_chat(payload):
    try:
        print(f"[DEBUG] Received message: {payload.message}")

        user_msg = payload.message
        user_info = payload.user_info
        user_chat_history = payload.chat_history
        greeted_today = payload.greeted_today

        # Detect category and load appropriate knowledge
        category = detect_category(user_msg)
        system_prompt = load_md("ai_engine/prompts/system_emem.md")
        md_path = get_md_for_category(category)
        knowledge = load_md(md_path)

        # Build final prompt sections ...
        prompt_sections = []
        if system_prompt:
            prompt_sections.append("# System Prompt:\n" + system_prompt)
        if knowledge:
            prompt_sections.append("# Knowledge:\n" + knowledge)
        # Clean, structured user context — lets the system prompt do its job
            user_name = user_info.get('name', 'Intern')
            task_title = user_info.get('task_title', 'current assignment')
            city = user_info.get('city', 'your city')
            country = user_info.get('country', 'your country')
            country_code = user_info.get('country_code', '')

            location_context = f"{city}, {country}"
            if country_code:
                location_context += f" ({country_code})"

            # Only include location if it's meaningful
            if "your city" in city.lower() or "your country" in country.lower():
                location_line = "Location: Not specified."
            else:
                location_line = f"Location: {location_context}."

            prompt_sections.append(f"""Current Intern Context:
            - Name: {user_name}
            - Current Task: {task_title}
            - {location_line}
            """)
        prompt_sections.append(f"Previous Chat history: {user_chat_history}")
        prompt_sections.append("# User Message:\n" + user_msg)
        # prompt_sections.append(" The tasks for the current week the user is in are: \n" + str(week_task))
        prompt_sections.append(f"Greeting rules: {GREETING_RULES} greeted_today: {greeted_today}")

        final_prompt = "\n\n".join(prompt_sections)
        # Initialize model lazily and count tokens
        model = get_model()
        # Count tokens (best-effort; don't fail the whole request if it errors)
        try:
            token_info = model.count_tokens(final_prompt)
            print("=== TOKEN LOG ===")
            print(f"Prompt tokens: {token_info.total_tokens}")
            print("=================")
        except Exception:
            print("[WARN] token counting failed; continuing without token log")
        # Send with retries on rate-limit (ResourceExhausted / 429)
        max_retries = 5
        base_delay = 1.0
        resp = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = model.start_chat().send_message(final_prompt)
                break
            except ResourceExhausted:
                # If last attempt, raise so outer handler logs it; else backoff and retry
                wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"[WARN] Rate limited (attempt {attempt}/{max_retries}). Retrying in {wait:.1f}s")
                if attempt == max_retries:
                    raise
                time.sleep(wait)
        print(f"[DEBUG] Category: {category}, MD used: {md_path}")
        print(f"[DEBUG] Response: {resp.text}")
        return {"reply": resp.text, "meta": {"category": category, "md_used": md_path}}
    
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return {"reply": "Something went wrong, please try again"}