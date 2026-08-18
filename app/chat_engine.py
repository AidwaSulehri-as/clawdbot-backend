"""
=====================================================================
 chat_engine.py — the core "understand what the user wants" logic
 for the /chat endpoint. This is the chatbot's brain.

 THE IDEA IN PLAIN ENGLISH:
 A user might type all kinds of things: "remind me to call mom",
 "where are my keys", "what do I have today", or just "hi". We need
 to figure out WHICH of these categories (an "intent") the message
 falls into, then respond appropriately.

 We use simple KEYWORD MATCHING for this, not a trained ML model -
 this is the same "pre-trained model + rule-based logic" approach
 used in nlp_utils.py and suggestion_engine.py, consistent with our
 Phase 1 scope.

 THE 5 INTENTS WE RECOGNIZE:
   1. create_reminder - "remind me to...", "don't forget to..."
   2. find_object      - "where is my...", "where are my..."
   3. find_note        - "what did I write about...", "find my note..."
   4. list_tasks        - "what do I have today", "show my reminders"
   5. general_chat       - anything else (greetings, small talk, etc.)

 IMPORTANT: for find_object, find_note, and list_tasks, the actual
 DATA lives on the phone (local sqflite database), not on this
 backend. So for these intents, we just recognize WHAT the user
 wants, and send back an "action" telling the Flutter app to search
 its local data - the app does the actual lookup.
=====================================================================
"""

from app.nlp_utils import extract_reminder


CREATE_REMINDER_KEYWORDS = [
    "remind me", "reminder", "set a reminder", "don't forget",
    "need to remember", "please remind",
]

FIND_OBJECT_KEYWORDS = [
    "where is", "where's", "where are", "find my", "locate my",
    "i lost", "can't find", "cant find",
]

FIND_NOTE_KEYWORDS = [
    "what did i write", "show me my note", "find note",
    "read my note", "what does my note say", "find my note",
]

LIST_TASKS_KEYWORDS = [
    "what do i have", "show my tasks", "list my reminders",
    "what's on my schedule", "whats on my schedule",
    "what are my reminders", "show me my reminders", "list reminders",
    "what do i have today", "what's on today",
]

QUERY_FILLER_WORDS = {"my", "the", "is", "are", "a", "an"}


def _extract_query(text: str, matched_keyword: str) -> str:
    """
    After we know WHICH keyword phrase matched (e.g. "where are"),
    this pulls out whatever comes after it as the actual search term
    (e.g. "my keys" -> "keys").
    """
    lower_text = text.lower()
    idx = lower_text.find(matched_keyword)
    remainder = text[idx + len(matched_keyword):].strip()

    words = [w for w in remainder.split() if w.lower() not in QUERY_FILLER_WORDS]
    query = " ".join(words).strip(" ?.!,")
    return query if query else remainder.strip(" ?.!,")


def _find_matching_keyword(text_lower: str, keyword_list: list[str]) -> str | None:
    """Returns the first keyword from the list found in the text, or None."""
    for keyword in keyword_list:
        if keyword in text_lower:
            return keyword
    return None


def handle_chat(message: str) -> dict:
    """
    The main function. Takes the user's raw message, figures out the
    intent, and returns a dict with 'reply' (text to show/speak) and
    'action' (instruction for the app, or None for plain conversation).
    """
    text_lower = message.lower().strip()

    keyword = _find_matching_keyword(text_lower, CREATE_REMINDER_KEYWORDS)
    if keyword:
        parsed = extract_reminder(message)
        reply = f"Got it — I'll remind you to {parsed['task']} on {parsed['date']} at {parsed['time']}."
        return {
            "reply": reply,
            "action": {
                "action": "create_reminder",
                "data": {
                    "task": parsed["task"],
                    "date": parsed["date"],
                    "time": parsed["time"],
                    "priority": "yellow",
                },
            },
        }

    keyword = _find_matching_keyword(text_lower, FIND_OBJECT_KEYWORDS)
    if keyword:
        query = _extract_query(message, keyword)
        return {
            "reply": f"Let me check where you last saved '{query}'.",
            "action": {
                "action": "find_object",
                "data": {"query": query},
            },
        }

    keyword = _find_matching_keyword(text_lower, FIND_NOTE_KEYWORDS)
    if keyword:
        query = _extract_query(message, keyword)
        return {
            "reply": f"Let me look through your notes for '{query}'.",
            "action": {
                "action": "find_note",
                "data": {"query": query},
            },
        }

    keyword = _find_matching_keyword(text_lower, LIST_TASKS_KEYWORDS)
    if keyword:
        return {
            "reply": "Here's what you've got coming up.",
            "action": {
                "action": "list_tasks",
                "data": {},
            },
        }

    return {
        "reply": _general_chat_reply(text_lower),
        "action": None,
    }


def _general_chat_reply(text_lower: str) -> str:
    """
    Simple canned responses for casual conversation. Not a trained
    conversational model - just friendly, honest, predictable replies
    for a Phase 1 demo. Real open-ended conversation is future work.
    """
    if any(greeting in text_lower for greeting in ["hi", "hello", "hey"]):
        return "Hi! I'm Clawd Bot. You can ask me to set reminders, find things you've saved, or show your tasks."
    if "thank" in text_lower:
        return "You're welcome! Let me know if you need anything else."
    if "help" in text_lower:
        return "I can help you set reminders, find where you saved things, or show your upcoming tasks. Just tell me what you need."
    return "I'm not sure I understood that. Try asking me to set a reminder, find something, or show your tasks."