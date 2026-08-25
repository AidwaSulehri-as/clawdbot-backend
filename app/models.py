"""
=====================================================================
 models.py — the API CONTRACT between your backend (Python) and
 Person B's Flutter app.
=====================================================================
"""

from typing import Optional, Literal, Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ReminderAction(BaseModel):
    action: Literal["create_reminder", "create_note", "find_object", "find_note", "list_tasks", "none"]
    data: dict[str, Any]


class ChatResponse(BaseModel):
    reply: str
    action: Optional[ReminderAction] = None


class ParseReminderRequest(BaseModel):
    text: str


class ParseReminderResponse(BaseModel):
    task: str
    date: str
    time: str
    confidence: float


class ReminderHistoryItem(BaseModel):
    task: str
    date: str
    time: str


class SuggestionsRequest(BaseModel):
    """
    UPDATED Aug 24: added optional nearby_object - when the app's
    on-device geolocator detects the user is near a saved location,
    it sends that object's name here so the backend can factor it
    into suggestion priority. None/omitted if no location match.
    """
    user_id: str = "default"
    reminder_history: list[ReminderHistoryItem] = []
    nearby_object: str | None = None


class Suggestion(BaseModel):
    text: str
    priority: Literal["green", "yellow", "red"]


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion]