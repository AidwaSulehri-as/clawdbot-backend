"""
=====================================================================
 main.py — the actual FastAPI SERVER file.

 HOW TO RUN THIS FILE:
   uvicorn app.main:app --host 0.0.0.0 --port 8000
=====================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    ChatRequest,
    ChatResponse,
    ParseReminderRequest,
    ParseReminderResponse,
    SuggestionsResponse,
    Suggestion,
    ReminderAction,
)

from app.nlp_utils import extract_reminder
from app.chat_engine import handle_chat

app = FastAPI(
    title="Clawd Bot Backend",
    description="NLP chatbot, reminder parsing, and context-aware suggestions for Clawd Bot",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    """Quick endpoint to confirm the server is alive."""
    return {"status": "ok", "service": "clawd-bot-backend"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Takes a user message (typed, or transcribed from voice), figures
    out the intent (create_reminder, find_object, find_note,
    list_tasks, or general_chat), and returns a natural-language
    reply plus an optional action for the app to execute locally.

    UPDATED Aug 19: this is now REAL intent recognition (see
    app/chat_engine.py), not a stub anymore.
    """
    result = handle_chat(request.message)
    return ChatResponse(**result)


@app.post("/parse_reminder", response_model=ParseReminderResponse)
def parse_reminder(request: ParseReminderRequest):
    """
    Takes free text like "remind me to take medicine tomorrow at 6pm"
    and extracts a structured task/date/time.
    """
    result = extract_reminder(request.text)
    return ParseReminderResponse(**result)


@app.get("/suggestions", response_model=SuggestionsResponse)
def suggestions(user_id: str = "default"):
    """
    STUB. Real frequency/timing rule logic (see app/suggestion_engine.py)
    gets wired in on Aug 23 once the app can send its reminder history.
    """
    return SuggestionsResponse(
        suggestions=[
            Suggestion(
                text="(stub) You usually set a reminder around this time.",
                priority="green",
            )
        ]
    )