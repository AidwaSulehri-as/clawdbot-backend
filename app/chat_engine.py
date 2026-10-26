"""
=====================================================================
 chat_engine.py — the core "understand what the user wants" logic
 for the /chat endpoint. This is the chatbot's brain.

 THE 5 INTENTS WE RECOGNIZE:
   1. create_reminder - "remind me to...", "don't forget to..."
   2. find_object      - "where is my...", "where are my..."
   3. find_note        - "what did I write about...", "find my note...",
                         "what is in grocery list"
   4. list_tasks        - "what do I have today", "show my reminders"
   5. general_chat       - anything else (greetings, small talk, etc.)

 UPDATED Oct 24: the note check now runs BEFORE the object check.
 Before, "find my note ..." matched the object keyword "find my"
 first, so notes were never searched. "about" was also added to the
 filler words so "find my note about doctor" searches for "doctor",
 and a few more phrases were added for notes and tasks.

 UPDATED Oct 26: questions like "what is in grocery list" or
 "what's inside my medicine list" are now understood as a note
 search (the note's title is the search word). Also, when the user
 just asks for all notes ("what is in my notes"), the search word is
 left empty so the app shows every note.
=====================================================================
"""

from app.nlp_utils import extract_reminder
import re


CREATE_REMINDER_KEYWORDS = [
    "remind me", "set a reminder", "don't forget",
    "need to remember", "please remind",
]

FIND_OBJECT_KEYWORDS = [
    "where is", "where's", "where are", "find my", "locate my",
    "i lost", "can't find", "cant find",
    "where did i put", "where did i leave", "where did i keep",
]

FIND_NOTE_KEYWORDS = [
    "what did i write", "show me my note", "find note",
    "read my note", "what does my note say", "find my note",
    "what is inside my notes", "what is in my notes",
    "show my notes", "list my notes", "show me my notes",
]

LIST_TASKS_KEYWORDS = [
    "what do i have", "show my tasks", "list my reminders",
    "what's on my schedule", "whats on my schedule",
    "what are my reminders", "show me my reminders", "list reminders",
    "what do i have today", "what's on today",
    "what reminders", "reminders do i have", "reminders have i set",
    "what have i set", "what i have to do", "do i have anything",
    "what are my tasks", "list my tasks", "show me my tasks",
]

QUERY_FILLER_WORDS = {"my", "the", "is", "are", "a", "an", "about"}

# NEW (Oct 26): phrases like "what is in X", "what's inside X",
# "open X", "read X" - the user is asking for the CONTENT of a note
# whose title is X.
NOTE_CONTENT_PATTERN = re.compile(
    r"\b(?:what is|what's|whats|what are)\s+(?:in|inside)\b|\b(?:open|read)\b"
)

# If the "search word" is just one of these, the user wants ALL notes.
ALL_NOTES_WORDS = {"notes", "note", "all notes", "all my notes"}


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


def _note_reply(query: str) -> str:
    if query:
        return f"Let me look through your notes for '{query}'."
    return "Here are your notes."


def handle_chat(message: str) -> dict:
    """
    The main function. Takes the user's raw message, figures out the
    intent, and returns a dict with 'reply' (text to show/speak) and
    'action' (instruction for the app, or None for plain conversation).
    """
    text_lower = message.lower().strip()

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

    # Notes are checked BEFORE objects, because "find my note" also
    # contains the object keyword "find my".
    keyword = _find_matching_keyword(text_lower, FIND_NOTE_KEYWORDS)
    if keyword:
        query = _extract_query(message, keyword)
        if query.lower() in ALL_NOTES_WORDS:
            query = ""
        return {
            "reply": _note_reply(query),
            "action": {
                "action": "find_note",
                "data": {"query": query},
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

    # NEW (Oct 26): "what is in grocery list" -> search notes by title.
    # Checked AFTER the object keywords so "where is ..." still finds
    # objects, and BEFORE create_reminder (read-only before write).
    match = NOTE_CONTENT_PATTERN.search(text_lower)
    if match:
        query = _extract_query(message, match.group(0))
        if query.lower() in ALL_NOTES_WORDS:
            query = ""
        if query or "note" in text_lower:
            return {
                "reply": _note_reply(query),
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
    """
    UPDATED Aug 22 QA fix: switched from naive substring matching to
    WORD-BOUNDARY matching. Naive "hi" in text checks match "hi"
    hiding inside unrelated words like "anyTHIng", "beHInd", or
    "susHI" - causing those messages to be wrongly treated as a
    greeting. Word-boundary matching only counts "hi" as a real,
    standalone word.
    """
    if re.search(r"\b(hi|hello|hey)\b", text_lower):
        return "Hi! I'm Clawd Bot. You can ask me to set reminders, find things you've saved, or show your tasks."
    if re.search(r"\bthank", text_lower):
        return "You're welcome! Let me know if you need anything else."
    if re.search(r"\bhelp\b", text_lower):
        return "I can help you set reminders, find where you saved things, or show your upcoming tasks. Just tell me what you need."
    return "I'm not sure I understood that. Try asking me to set a reminder, find something, or show your tasks."