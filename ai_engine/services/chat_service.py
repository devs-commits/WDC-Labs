"""
Docstring for ai_engine.services.chat_service
"""

import traceback
import google.generativeai as genai

from backend import mock_methods
from ai_engine.utils import load_md
from ai_engine.category_detector import detect_category, get_md_for_category

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    system_instruction="YOU ARE MISS EMEM OBONG: The kind and respectful Director of Internships at WDC Labs, an Internship portal for gaining real world experiences . Respond professionally."
)

def use_chat(payload):
    try:
        print(f"[DEBUG] Received message: {payload.message}")

        user_msg = payload.message
        user_info = mock_methods.get_user_info()
        user_chat_history = mock_methods.get_chat_history()

        # Detect category and load appropriate knowledge
        category = detect_category(user_msg)
        system_prompt = load_md("ai_engine/prompts/system_emem.md")
        md_path = get_md_for_category(category)
        knowledge = load_md(md_path)
        week_task = mock_methods.get_task()

        # Build final prompt sections ...
        prompt_sections = []
        if system_prompt:
            prompt_sections.append("# System Prompt:\n" + system_prompt)
        if knowledge:
            prompt_sections.append("# Knowledge:\n" + knowledge)
        prompt_sections.append("The User's data is: \n" + user_info)
        #prompt_sections.append("Previous Chat history: " + user_chat_history)
        prompt_sections.append("# User Message:\n" + user_msg)
        prompt_sections.append(" The tasks for the current week te user is in are: /n" + week_task)

        final_prompt = "\n\n".join(prompt_sections)

        resp = model.start_chat().send_message(final_prompt)
        print(f"[DEBUG] Category: {category}, MD used: {md_path}")
        print(f"[DEBUG] Response: {resp.text}")
        return {"reply": resp.text, "meta": {"category": category, "md_used": md_path}}
    
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return {"reply": "Something went wrong, please try again"}

