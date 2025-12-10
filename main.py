"""
Project root ASGI wrapper so `uvicorn main:app` works when run from project root.
This simply imports the FastAPI `app` instance from `backend.main`.
"""

from backend.main import app

__all__ = ("app",)
