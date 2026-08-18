"""
=====================================================================
 nlp_utils.py — the "understand what the user typed" logic.

 UPDATED Aug 18: dateparser's automatic phrase-detection sometimes
 misses obvious dates (like a lone "Friday") or matches noisy
 fragments inside unrelated words. To make this more reliable, we now
 only TRUST a matched phrase if it contains a recognizable date/time
 KEYWORD (like "tomorrow", "friday", "6pm", a digit, etc.) - this is
 a whitelist approach, safer than trying to guess every possible way
 dateparser might misfire.
=====================================================================
"""

from dateparser.search import search_dates
import dateparser
from datetime import datetime
import re


FILLER_PREFIXES = [
    "remind me to",
    "remind me",
    "set a reminder to",
    "set a reminder for",
    "reminder to",
    "reminder for",
    "please remind me to",
    "i need to",
    "don't forget to",
]

TRAILING_CONNECTORS = {"at", "on", "in", "by", "for"}

DATE_KEYWORDS = {
    "today", "tomorrow", "tonight", "yesterday", "now",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "mon", "tue", "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "next", "last", "this", "coming", "upcoming",
    "week", "weeks", "month", "months", "year", "years",
    "day", "days", "hour", "hours", "minute", "minutes",
    "am", "pm", "noon", "midnight",
    "morning", "afternoon", "evening", "night",
}


def _looks_like_real_date(phrase: str) -> bool:
    """Returns True only if the phrase contains a recognizable
    date/time keyword or a digit - our safety filter."""
    if re.search(r"\d", phrase):
        return True
    words = re.findall(r"[a-zA-Z]+", phrase.lower())
    return any(word in DATE_KEYWORDS for word in words)


def extract_reminder(text: str) -> dict:
    """
    Takes raw user text, returns a dictionary with
    task/date/time/confidence — matching the ParseReminderResponse
    shape in models.py.
    """

    found = search_dates(
        text,
        settings={"PREFER_DATES_FROM": "future"},
    ) or []

    good_matches = [
        (phrase, dt) for phrase, dt in found
        if len(phrase.strip()) >= 3 and _looks_like_real_date(phrase)
    ]

    parsed_datetime = None
    matched_phrases = []

    if good_matches:
        good_matches.sort(key=lambda pair: text.find(pair[0]))
        matched_phrases = [phrase for phrase, _ in good_matches]

        combined_phrase = " ".join(matched_phrases)
        parsed_datetime = dateparser.parse(
            combined_phrase,
            settings={"PREFER_DATES_FROM": "future"},
        )

        if not parsed_datetime:
            longest_phrase, parsed_datetime = max(
                good_matches, key=lambda pair: len(pair[0])
            )
            matched_phrases = [longest_phrase]

    if not parsed_datetime:
        words = re.findall(r"[a-zA-Z]+", text.lower())
        for word in words:
            if word in DATE_KEYWORDS and word not in TRAILING_CONNECTORS:
                candidate = dateparser.parse(
                    word, settings={"PREFER_DATES_FROM": "future"}
                )
                if candidate:
                    parsed_datetime = candidate
                    matched_phrases = [word]
                    break

    if parsed_datetime:
        confidence = 0.85
    else:
        parsed_datetime = datetime.now()
        confidence = 0.2
        matched_phrases = []

    task_text = text
    for phrase in matched_phrases:
        task_text = re.sub(re.escape(phrase), "", task_text, flags=re.IGNORECASE)

    task_text_lower = task_text.lower().strip()
    for prefix in FILLER_PREFIXES:
        if task_text_lower.startswith(prefix):
            task_text = task_text[len(prefix):].strip()
            break

    task_text = " ".join(task_text.split())
    task_text = task_text.strip(" ,.-")

    words = task_text.split()
    if words and words[-1].lower() in TRAILING_CONNECTORS:
        task_text = " ".join(words[:-1])

    if not task_text:
        task_text = text.strip()
        confidence = min(confidence, 0.3)

    return {
        "task": task_text,
        "date": parsed_datetime.strftime("%Y-%m-%d"),
        "time": parsed_datetime.strftime("%H:%M"),
        "confidence": confidence,
    }