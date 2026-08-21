"""
=====================================================================
 models.py — the API CONTRACT between your backend (Python) and
 Person B's Flutter app.
=====================================================================
"""

from typing import Optional, Literal, Any
from pydantic import BaseModel


# =====================================================================
# SECTION 1: Shapes used by the  /chat  endpoint
# =====================================================================

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ReminderAction(BaseModel):
    action: Literal["create_reminder", "create_note", "find_object", "find_note", "list_tasks", "none"]
    data: dict[str, Any]


class ChatResponse(BaseModel):
    reply: str
    action: Optional[ReminderAction] = None


# =====================================================================
# SECTION 2: Shapes used by the  /parse_reminder  endpoint
# =====================================================================

class ParseReminderRequest(BaseModel):
    text: str


class ParseReminderResponse(BaseModel):
    task: str
    date: str
    time: str
    confidence: float


# =====================================================================
# SECTION 3: Shapes used by the  /suggestions  endpoint
# =====================================================================

class ReminderHistoryItem(BaseModel):
    """
    One past reminder, sent by the app so the backend can look for
    patterns in it. This data lives on the PHONE (local sqflite), not
    here on the server - the app sends its own history along with
    each /suggestions request.
    """
    task: str
    date: str   # YYYY-MM-DD
    time: str   # HH:MM


class SuggestionsRequest(BaseModel):
    """
    UPDATED Aug 23: /suggestions changed from GET to POST, because it
    now needs the app to actually SEND its reminder history for the
    backend to analyze - a GET request has no good way to carry a
    whole list of past reminders.
    """
    user_id: str = "default"
    reminder_history: list[ReminderHistoryItem] = []


class Suggestion(BaseModel):
    text: str
    priority: Literal["green", "yellow", "red"]


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion]