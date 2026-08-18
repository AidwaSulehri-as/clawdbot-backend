"""
=====================================================================
 nlp_utils.py — the actual "understand what the user typed" logic.

 Today's job: take free text like
     "remind me to take medicine tomorrow at 6pm"
 and pull out:
     task = "take medicine"
     date = "2026-08-19"
     time = "18:00"
=====================================================================
"""

from dateparser.search import search_dates
import dateparser
from datetime import datetime


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

MIN_MATCH_LENGTH = 3

TRAILING_CONNECTORS = {"at", "on", "in", "by", "for"}


def extract_reminder(text: str) -> dict:
    found = search_dates(
        text,
        settings={"PREFER_DATES_FROM": "future"},
    ) or []

    good_matches = [
        (phrase, dt) for phrase, dt in found
        if len(phrase.strip()) >= MIN_MATCH_LENGTH
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

    if parsed_datetime:
        confidence = 0.85
    else:
        parsed_datetime = datetime.now()
        confidence = 0.2
        matched_phrases = []

    task_text = text
    for phrase in matched_phrases:
        task_text = task_text.replace(phrase, "")

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