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
    UserResponse,
)

from app.nlp_utils import extract_reminder
from app.chat_engine import handle_chat
from app.suggestion_engine import analyze_patterns

from app.database import get_db, Base, engine
from app import db_models
from app.db_models import User
from app.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_email,
    is_locked_out,
    record_failed_attempt,
    clear_failed_attempts,
    LOCKOUT_MINUTES,
)

Base.metadata.create_all(bind=engine)

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
def chat(
    request: ChatRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """
    UPDATED Sep 19: now requires a valid login token. The identity of
    the caller comes from the token (current_user_email) instead of
    the old hardcoded 'user_id': 'default' field.
    """
    result = handle_chat(request.message)
    return ChatResponse(**result)


@app.post("/parse_reminder", response_model=ParseReminderResponse)
def parse_reminder(request: ParseReminderRequest):
    """
    Takes free text like "remind me to take medicine tomorrow at 6pm"
    and extracts a structured task/date/time. Not user-specific, so
    left unprotected - it's a pure text-processing utility endpoint,
    called internally by /chat.
    """
    result = extract_reminder(request.text)
    return ParseReminderResponse(**result)


@app.post("/suggestions", response_model=SuggestionsResponse)
def suggestions(
    request: SuggestionsRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """
    UPDATED Sep 19: now requires a valid login token, same as /chat.

    Takes the user's reminder history (sent by the app, since that
    data lives in the phone's local database, not here) and looks for
    repeating patterns using the rule-based logic in
    app/suggestion_engine.py.
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
    already registered.
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
    signed JWT token on success.

    UPDATED Sep 21: added rate-limiting - after 5 failed attempts on
    one email within 15 minutes, further attempts are blocked with a
    429 (Too Many Requests) response, even if the correct password is
    provided. This stops brute-force password guessing.
    """
    if is_locked_out(request.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again in {LOCKOUT_MINUTES} minutes.",
        )

    user = db.query(User).filter(User.email == request.email).first()

    if user is None or not verify_password(request.password, user.hashed_password):
        record_failed_attempt(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    clear_failed_attempts(request.email)
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Returns the logged-in user's own info, based on their token.
    """
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserResponse(id=user.id, email=user.email)