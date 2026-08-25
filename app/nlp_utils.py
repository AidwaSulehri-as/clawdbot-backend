"""
=====================================================================
 nlp_utils.py — the "understand what the user typed" logic.
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

QUALIFIER_WORDS = {"next", "last", "this", "coming", "upcoming"}


def _looks_like_real_date(phrase: str) -> bool:
    if re.search(r"\d", phrase):
        return True
    words = re.findall(r"[a-zA-Z]+", phrase.lower())
    return any(word in DATE_KEYWORDS for word in words)


def _extend_with_qualifier(text: str, phrase: str) -> str:
    """
    If a qualifier word (like "next", "last", "this") sits right
    before this matched phrase in the original text, returns the
    phrase WITH that qualifier attached - purely for cleanly removing
    it from the task text later. Does NOT affect date calculation.
    """
    idx = text.lower().find(phrase.lower())
    if idx > 0:
        preceding_text = text[:idx].rstrip()
        preceding_words = preceding_text.split()
        if preceding_words and preceding_words[-1].lower() in QUALIFIER_WORDS:
            return f"{preceding_words[-1]} {phrase}"
    return phrase


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
    # matched_phrases holds the ORIGINAL phrases (used for date math).
    matched_phrases = []
    # removal_phrases holds the qualifier-EXTENDED versions (used only
    # to cleanly strip text from the task) - kept separate so a
    # failed re-parse of an extended phrase never costs us an
    # already-correct date (see Aug 26 QA note below).
    removal_phrases = []

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

        # UPDATED Aug 26 QA fix: build the removal list SEPARATELY
        # from date calculation. Earlier version tried to re-parse
        # the qualifier-extended phrase (e.g. "next Monday at 2pm")
        # to get the date - but dateparser.parse() sometimes fails on
        # that exact combined form even though the original phrase
        # ("Monday at 2pm") parsed fine. That failure was silently
        # discarding our qualifier extension and falling back to the
        # ORIGINAL phrase without "next" - leaving it dangling in the
        # task text. Now we keep the date from the original phrase
        # (which we know already parsed correctly) and use the
        # extended version ONLY for text removal, which doesn't need
        # to be re-parsed at all.
        removal_phrases = [_extend_with_qualifier(text, p) for p in matched_phrases]

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
                    # UPDATED Aug 26 (second fix): apply the same
                    # qualifier-word extension here too. This fallback
                    # path runs when search_dates only found noise
                    # (like matching "to"/"on" instead of "Tuesday"),
                    # so a lone keyword gets found this way instead -
                    # but without this line, a qualifier word right
                    # before it (e.g. "coming Tuesday") would be
                    # missed here just like it was in the main path.
                    removal_phrases = [_extend_with_qualifier(text, word)]
                    break

    if parsed_datetime:
        confidence = 0.85
    else:
        parsed_datetime = datetime.now()
        confidence = 0.2
        removal_phrases = []

    task_text = text
    for phrase in removal_phrases:
        task_text = re.sub(re.escape(phrase), "", task_text, flags=re.IGNORECASE)

    task_text_lower = task_text.lower()
    best_cut_index = -1
    for prefix in FILLER_PREFIXES:
        idx = task_text_lower.find(prefix)
        if idx != -1:
            end_of_prefix = idx + len(prefix)
            if end_of_prefix > best_cut_index:
                best_cut_index = end_of_prefix
    if best_cut_index != -1:
        task_text = task_text[best_cut_index:].strip()

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
