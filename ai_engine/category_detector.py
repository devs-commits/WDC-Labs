from typing import Tuple


def detect_category(message: str) -> str:
    m = message.lower() if message else ""

    if any(k in m for k in ["task", "assignment", "deadline", "project", "todo", "deliverable"]):
        return "task"

    if any(k in m for k in ["policy", "policies", "rule", "rules", "compliance", "wdc policy"]):
        return "policies"

    if any(k in m for k in ["onboard", "onboarding", "first day", "orientation", "how do i start", "i am new", "how do i begin"]):
        return "onboarding"

    if any(k in m for k in ["email", "write message", "compose", "draft", "dm", "slack"]):
        return "communication"

    if any(k in m for k in ["help", "confused", "don' t understand", "dont understand", "faq", "question", "how do i", "stuck"]):
        return "faq"

    return "default"


def get_md_for_category(category: str) -> str:
    """Return a project-relative path to the markdown file for a category.

    Paths are relative to the project root and suitable for `load_md()`.
    """
    mapping = {
        "task": "ai_engine/knowledge/task_templates.md",
        "policies": "ai_engine/knowledge/wdc_policies.md",
        "onboarding": "ai_engine/prompts/onboarding_template.md",
        "communication": "ai_engine/knowledge/files.md",
        "faq": "ai_engine/knowledge/faq.md",
        "default": "ai_engine/knowledge/files.md",
    }
    return mapping.get(category, mapping["default"])
