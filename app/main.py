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
    SuggestionsRequest,
    SuggestionsResponse,
    Suggestion,
    ReminderAction,
)

from app.nlp_utils import extract_reminder
from app.chat_engine import handle_chat
from app.suggestion_engine import analyze_patterns

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


@app.post("/suggestions", response_model=SuggestionsResponse)
def suggestions(request: SuggestionsRequest):
    """
    Takes the user's reminder history (sent by the app, since that
    data lives in the phone's local database, not here) and looks for
    repeating patterns using the rule-based logic in
    app/suggestion_engine.py.

    UPDATED Aug 23: this is now REAL logic, not a stub. Also changed
    from GET to POST, since a GET request has no good way to carry a
    whole list of past reminders in its body.
    """
    history_as_dicts = [
        {"task": item.task, "date": item.date, "time": item.time}
        for item in request.reminder_history
    ]

    results = analyze_patterns(history_as_dicts)

    return SuggestionsResponse(
        suggestions=[Suggestion(**s) for s in results]
    )