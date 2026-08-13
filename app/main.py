"""
=====================================================================
 main.py — the actual FastAPI SERVER file.

 This is the file you "run" to start your backend. When it's running,
 it listens for incoming web requests (like a mini website, but it
 returns JSON data instead of HTML pages) and responds according to
 the functions below.

 HOW TO RUN THIS FILE:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

 "uvicorn" is a program that RUNS FastAPI apps.
 "app.main:app" means: "look inside the app folder, in main.py,
   for a variable called 'app'" — that's the FastAPI object we
   create just below.
 "--reload" means: automatically restart the server whenever you
   save changes to this file, so you don't have to stop/start it
   manually while developing.
=====================================================================
"""

# Import the FastAPI class itself — this is the core of the framework.
from fastapi import FastAPI

# CORS = Cross-Origin Resource Sharing. By default, web browsers block
# an app running on one address from calling a server on a different
# address, for security reasons. Since our Flutter app and our backend
# run on different addresses, we need to explicitly ALLOW that here.
from fastapi.middleware.cors import CORSMiddleware

# Import all the "shapes" we defined in models.py, so we can use them
# as the expected request/response formats below.
from app.models import (
    ChatRequest,
    ChatResponse,
    ParseReminderRequest,
    ParseReminderResponse,
    SuggestionsResponse,
    Suggestion,
    ReminderAction,
)

# Create the FastAPI application object. Everything below attaches
# routes (URLs) to this single "app" object.
app = FastAPI(
    title="Clawd Bot Backend",
    description="NLP chatbot, reminder parsing, and context-aware suggestions for Clawd Bot",
    version="0.1.0",
)

# ---------------------------------------------------------------
# Turn on CORS so the Flutter app (running on a phone/emulator,
# which counts as a "different origin" from this server) is allowed
# to send requests to us. allow_origins=["*"] means "allow requests
# from anywhere" — fine for development. Once you have a real
# deployed backend URL, you can tighten this to just your app's
# actual origin for better security (not required for your FYP demo).
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# ROUTE 1: Health check
# =====================================================================
# The "@app.get("/")" line above the function is called a DECORATOR.
# It tells FastAPI: "when someone visits the root URL ('/') using an
# HTTP GET request, run the function directly below me, and send back
# whatever it returns (as JSON automatically)."
@app.get("/")
def health_check():
    """
    A tiny endpoint with no real purpose except letting you (or your
    phone, or your demo) quickly check "is the server alive right now?"
    Also useful for waking up a sleeping free-tier server before a demo
    — just visit this URL in a browser a few minutes early.
    """
    # FastAPI automatically converts this Python dictionary into JSON
    # before sending it back. You don't have to do that conversion
    # yourself — this is one of the things FastAPI does for you.
    return {"status": "ok", "service": "clawd-bot-backend"}


# =====================================================================
# ROUTE 2: /chat
# =====================================================================
# "@app.post(...)" means this only responds to POST requests (used for
# sending data TO the server, unlike GET which is for just fetching
# data). "response_model=ChatResponse" tells FastAPI to validate that
# whatever we return matches the ChatResponse shape from models.py —
# if we accidentally forget a field, FastAPI will error loudly instead
# of silently sending broken JSON to the app.
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Takes a user message (typed, or transcribed from voice) and returns:
      - a natural-language reply to show/speak back to the user
      - an optional `action` the Flutter app should execute locally
        (e.g. write a new reminder to its sqflite database)

    HOW DOES `request: ChatRequest` WORK?
    FastAPI reads the incoming JSON body, checks it matches the
    ChatRequest shape from models.py, and hands it to you here as a
    normal Python object. So `request.message` gives you the text the
    user typed — no manual JSON-parsing needed.

    TODAY'S STATUS (Aug 13): this is a STUB. It always returns the
    same fixed sample data, no matter what the user actually typed.
    That's on purpose — it lets Person B start building/testing the
    chat screen today without waiting for real NLP logic, which we
    build for real on Aug 19.
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


# =====================================================================
# ROUTE 3: /parse_reminder
# =====================================================================
@app.post("/parse_reminder", response_model=ParseReminderResponse)
def parse_reminder(request: ParseReminderRequest):
    """
    Takes free text like "remind me to take medicine tomorrow at 6pm"
    and extracts a structured task/date/time.

    TODAY'S STATUS (Aug 13): STUB. Always returns the same fake sample.
    Real spaCy + dateparser logic replaces this on Aug 15 — but the
    SHAPE of the response (task/date/time/confidence) will stay the
    same, so nothing in the Flutter app needs to change later.
    """
    return ParseReminderResponse(
        task="Sample task extracted from text",
        date="2026-08-14",
        time="18:00",
        confidence=0.0,  # 0.0 is a signal to Person B: "this is fake data, don't trust it yet"
    )


# =====================================================================
# ROUTE 4: /suggestions
# =====================================================================
# Note this one is a GET (not POST) because the app is just asking
# "what are my current suggestions?" — it isn't sending new data to
# be saved, just requesting data back. "user_id: str = 'default'"
# below means this can be passed as a URL parameter, e.g.
# /suggestions?user_id=default — and if it's left out, it defaults
# to "default" automatically.
@app.get("/suggestions", response_model=SuggestionsResponse)
def suggestions(user_id: str = "default"):
    """
    Returns a prioritized list of proactive suggestions based on the
    user's own reminder/note history. (That history actually lives on
    the PHONE, in its local sqflite database — not here on the server
    — so eventually the app will need to SEND its recent activity
    along with this request. We'll design that properly on Aug 23.)

    TODAY'S STATUS (Aug 13): STUB. Always returns one fake suggestion.
    """
    return SuggestionsResponse(
        suggestions=[
            Suggestion(
                text="(stub) You usually set a reminder around this time.",
                priority="green",
            )
        ]
    )