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


# =====================================================================
# Phase 2 (Sep 18) — Authentication schemas
# =====================================================================

class SignupRequest(BaseModel):
    email: str
    password: str


class SignupResponse(BaseModel):
    email: str
    message: str = "Account created successfully."


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str


# ---------------------------------------------------------------
# REMINDER schemas
# ---------------------------------------------------------------
class ReminderCreate(BaseModel):
    task: str
    date: str
    time: str
    priority: str = "green"
    completed: int = 0
    category: str | None = None

class ReminderResponse(BaseModel):
    id: int
    task: str
    date: str
    time: str
    priority: str
    completed: int
    category: str | None
    last_modified: str

# ---------------------------------------------------------------
# NOTE schemas
# ---------------------------------------------------------------
class NoteCreate(BaseModel):
    title: str
    content: str | None = None
    created_at: str

class NoteResponse(BaseModel):
    id: int
    title: str
    content: str | None
    created_at: str
    last_modified: str

# ---------------------------------------------------------------
# OBJECT LOCATION schemas
# ---------------------------------------------------------------
class ObjectLocationCreate(BaseModel):
    object_name: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None

class ObjectLocationResponse(BaseModel):
    id: int
    object_name: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    last_modified: str

# ---------------------------------------------------------------
# SYNC schemas
#
# UPDATED Sep 28: each sync item now also carries its OWN
# last_modified (the timestamp from the PHONE's local copy). This is
# what lets the server compare "how new is the phone's version?"
# against its own last_modified, and decide whether to accept the
# phone's update or reject it as stale (conflict resolution).
# ---------------------------------------------------------------
class SyncReminderItem(BaseModel):
    id: int | None = None
    task: str
    date: str
    time: str
    priority: str = "green"
    completed: int = 0
    category: str | None = None
    last_modified: str | None = None

class SyncNoteItem(BaseModel):
    id: int | None = None
    title: str
    content: str | None = None
    created_at: str
    last_modified: str | None = None

class SyncObjectLocationItem(BaseModel):
    id: int | None = None
    object_name: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    last_modified: str | None = None

class SyncRequest(BaseModel):
    reminders: list[SyncReminderItem] = []
    notes: list[SyncNoteItem] = []
    object_locations: list[SyncObjectLocationItem] = []

class SyncResponse(BaseModel):
    reminders: list[ReminderResponse]
    notes: list[NoteResponse]
    object_locations: list[ObjectLocationResponse]


# =====================================================================
# Oct — Multi-caregiver / family view schemas
# =====================================================================

class InviteCodeResponse(BaseModel):
    code: str
    expires_at: str


class RedeemCodeRequest(BaseModel):
    code: str


class CaregiverLinkResponse(BaseModel):
    patient_id: int
    patient_email: str
    caregiver_id: int
    caregiver_email: str
    created_at: str