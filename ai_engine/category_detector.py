"""
Docstring for ai_engine.category_detector
"""

def detect_category(message: str) -> str:
    m = message.lower() if message else ""

    if any(k in m for k in ["task", "assignment", "deadline", "project", "todo", "deliverable"]):
        return "task_templates"

    if any(k in m for k in ["policy", "policies", "rule", "rules", "compliance", "wdc policy"]):
        return "wdc_policies"

    return "system_emem"


def get_md_for_category(category: str) -> str:
    """
    Return a project-relative path to the markdown file for a category.
    Paths are relative to the project root and suitable for `load_md()`.
    """
    mapping = {
        "task_templates": "ai_engine/knowledge/task_templates.md",
        "wdc_policies": "ai_engine/prompts/wdc_policies.md",
        "system_emem": "ai_engine/prompts/system_emem.md",
    }

    return mapping.get(category, mapping["system_emem"])
