"""
=====================================================================
 chat_engine.py — the core "understand what the user wants" logic
 for the /chat endpoint. This is the chatbot's brain.

 THE 5 INTENTS WE RECOGNIZE:
   1. create_reminder - "remind me to...", "don't forget to..."
   2. find_object      - "where is my...", "where are my..."
   3. find_note        - "what did I write about...", "find my note..."
   4. list_tasks        - "what do I have today", "show my reminders"
   5. general_chat       - anything else (greetings, small talk, etc.)
=====================================================================
"""

from app.nlp_utils import extract_reminder


CREATE_REMINDER_KEYWORDS = [
    "remind me", "set a reminder", "don't forget",
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
    "what reminders", "reminders do i have", "reminders have i set",
    "what have i set", "what i have to do",
]

QUERY_FILLER_WORDS = {"my", "the", "is", "are", "a", "an"}


def _extract_query(text: str, matched_keyword: str) -> str:
    lower_text = text.lower()
    idx = lower_text.find(matched_keyword)
    remainder = text[idx + len(matched_keyword):].strip()

    words = [w for w in remainder.split() if w.lower() not in QUERY_FILLER_WORDS]
    query = " ".join(words).strip(" ?.!,")
    return query if query else remainder.strip(" ?.!,")


def _find_matching_keyword(text_lower: str, keyword_list: list[str]) -> str | None:
    for keyword in keyword_list:
        if keyword in text_lower:
            return keyword
    return None


def handle_chat(message: str) -> dict:
    text_lower = message.lower().strip()

    # ---- Aug 21 hardening: handle empty/near-empty input specially ----
    if len(text_lower) < 2:
        return {
            "reply": "I didn't catch that — could you tell me a bit more? "
                     "I can set reminders, find things you've saved, or show your tasks.",
            "action": None,
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

    return {
        "reply": _general_chat_reply(text_lower),
        "action": None,
    }


def _general_chat_reply(text_lower: str) -> str:
    if any(greeting in text_lower for greeting in ["hi", "hello", "hey"]):
        return "Hi! I'm Clawd Bot. You can ask me to set reminders, find things you've saved, or show your tasks."
    if "thank" in text_lower:
        return "You're welcome! Let me know if you need anything else."
    if "help" in text_lower:
        return "I can help you set reminders, find where you saved things, or show your upcoming tasks. Just tell me what you need."
    return "I'm not sure I understood that. Try asking me to set a reminder, find something, or show your tasks."