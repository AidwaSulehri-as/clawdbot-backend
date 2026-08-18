"""
=====================================================================
 main.py — the actual FastAPI SERVER file.

 This is the file you "run" to start your backend. When it's running,
 it listens for incoming web requests (like a mini website, but it
 returns JSON data instead of HTML pages) and responds according to
 the functions below.

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
    STUB for Aug 13 - always returns a fixed sample response so Person B
    can build the chat UI today without waiting on real NLP.
    Real intent recognition (spaCy/NLTK) gets built Aug 19.
    """
    return ChatResponse(
        reply=f"(stub) I heard: '{request.message}'. Real NLP coming Aug 19.",
        action=ReminderAction(
            action="create_reminder",
            data={
                "task": "Sample reminder",
                "date": "2026-08-14",
                "time": "18:00",
                "priority": "yellow",
            },
        ),
    )


@app.post("/parse_reminder", response_model=ParseReminderResponse)
def parse_reminder(request: ParseReminderRequest):
    """
    Takes free text like "remind me to take medicine tomorrow at 6pm"
    and extracts a structured task/date/time.

    UPDATED Aug 15: this is now REAL logic (see app/nlp_utils.py),
    not a stub anymore.
    """
    result = extract_reminder(request.text)
    return ParseReminderResponse(**result)


@app.get("/suggestions", response_model=SuggestionsResponse)
def suggestions(user_id: str = "default"):
    """
    STUB for Aug 13. Real frequency/timing rule logic gets built Aug 23.
    """
    return SuggestionsResponse(
        suggestions=[
            Suggestion(
                text="(stub) You usually set a reminder around this time.",
                priority="green",
            )
        ]
    )