from pathlib import Path

def load_md(rel_path: str) -> str:
    """Load a markdown file relative to project root and return its text.
    Example: load_md('ai_engine/knowledge/task_templates.md')
    """
    root = Path(__file__).resolve().parent.parent
    path = root / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
