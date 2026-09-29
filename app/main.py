"""
=====================================================================
 main.py — the actual FastAPI SERVER file.

 HOW TO RUN THIS FILE:
   uvicorn app.main:app --host 0.0.0.0 --port 8000
=====================================================================
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.models import (
    ChatRequest,
    ChatResponse,
    ParseReminderRequest,
    ParseReminderResponse,
    SuggestionsRequest,
    SuggestionsResponse,
    Suggestion,
    ReminderAction,
    SignupRequest,
    SignupResponse,
    LoginRequest,
    TokenResponse,
)

from app.nlp_utils import extract_reminder
from app.chat_engine import handle_chat
from app.suggestion_engine import analyze_patterns

from app.database import get_db
from app.db_models import User
from app.auth_utils import hash_password, verify_password, create_access_token

app = FastAPI(
    title="Clawd Bot Backend",
    description="NLP chatbot, reminder parsing, and context-aware suggestions for Clawd Bot",
    version="0.1.0",
)
from app.database import Base, engine
from app import db_models

Base.metadata.create_all(bind=engine)
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

    UPDATED Aug 24: now also accepts an optional nearby_object from
    the app's on-device location check, factored into priority.
    """
    history_as_dicts = [
        {"task": item.task, "date": item.date, "time": item.time}
        for item in request.reminder_history
    ]

    results = analyze_patterns(history_as_dicts, nearby_object=request.nearby_object)

    return SuggestionsResponse(
        suggestions=[Suggestion(**s) for s in results]
    )


# =====================================================================
# Phase 2 (Sep 18) — Authentication endpoints
# =====================================================================

@app.post("/auth/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Creates a new user account. Rejects the request if the email is
    already registered - this is the check the Flutter app's
    'email already registered' error message comes from.
    """
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    new_user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return SignupResponse(email=new_user.email)


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Verifies email + password against the stored hash, and returns a
    signed JWT token on success. The same generic error message is
    used whether the email doesn't exist OR the password is wrong -
    this is deliberate: telling an attacker "that email doesn't
    exist" vs "wrong password" leaks which emails are registered.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return TokenResponse(access_token=access_token)