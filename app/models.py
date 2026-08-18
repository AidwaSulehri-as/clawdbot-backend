"""
=====================================================================
 models.py — the API CONTRACT between your backend (Python) and
 Person B's Flutter app.

 WHAT IS A "MODEL" HERE?
 A "model" in this file is just a description of the SHAPE of data —
 what fields exist, and what type each field is (text, number,
 true/false, etc). We use a library called "Pydantic" to define these
 shapes as Python classes. FastAPI then automatically:
   1. Checks incoming requests match the shape (rejects bad data)
   2. Converts your Python objects into JSON to send back
   3. Generates the interactive docs page (/docs) for free
=====================================================================
"""

from typing import Optional, Literal, Any
from pydantic import BaseModel


# =====================================================================
# SECTION 1: Shapes used by the  /chat  endpoint
# =====================================================================

class ChatRequest(BaseModel):
    """
    This describes what the Flutter app must SEND when it calls /chat.
    Example JSON that matches this shape:
        { "message": "remind me to take medicine at 6pm", "user_id": "default" }
    """
    message: str
    user_id: str = "default"


class ReminderAction(BaseModel):
    """
    Sometimes, after chatting, the app needs to DO something — like
    saving a new reminder, or searching for an object/note/task list.
    This shape describes that instruction.

    UPDATED Aug 19: added find_object, find_note, and list_tasks as
    valid actions, alongside the original create_reminder/create_note.

    Example:
        { "action": "create_reminder",
          "data": { "task": "take medicine", "date": "2026-08-14", "time": "18:00" } }
    """
    action: Literal["create_reminder", "create_note", "find_object", "find_note", "list_tasks", "none"]
    data: dict[str, Any]


class ChatResponse(BaseModel):
    """
    This describes what YOUR SERVER sends BACK after /chat is called.
    """
    reply: str
    action: Optional[ReminderAction] = None


# =====================================================================
# SECTION 2: Shapes used by the  /parse_reminder  endpoint
# =====================================================================

class ParseReminderRequest(BaseModel):
    """What the app sends: raw text like "remind me to call mom tomorrow at 5pm"."""
    text: str


class ParseReminderResponse(BaseModel):
    """
    What we send back: the same sentence, but broken into structured
    pieces the app can save directly into its reminders table.
    """
    task: str
    date: str
    time: str
    confidence: float


# =====================================================================
# SECTION 3: Shapes used by the  /suggestions  endpoint
# =====================================================================

class Suggestion(BaseModel):
    """One single suggestion card the app will display."""
    text: str
    priority: Literal["green", "yellow", "red"]


class SuggestionsResponse(BaseModel):
    """A list of suggestion cards — this is the whole /suggestions response."""
    suggestions: list[Suggestion]