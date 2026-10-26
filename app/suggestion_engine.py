"""
=====================================================================
 suggestion_engine.py — the "notice patterns in what the user does"
 logic. This is the brain behind Clawd Bot's proactive suggestions.

 This is NOT a trained machine learning model - it's simple counting
 and grouping (statistics) plus a few context rules, computed fresh
 every time.

 THE SUGGESTIONS, FROM MOST TO LEAST HISTORY NEEDED:
   1. Strong habit  - the same task set 3+ times around the same hour.
   2. Early habit   - the same task set twice around the same hour.
   3. Set once      - a task set ONCE in the last 7 days and not set
                      again today ("Yesterday you set X. Set it again?").
   4. Coming up     - a reminder due in the next 24 hours (not done yet).
   5. Nearby object - the user is near a saved location.
   6. Starter tip   - a time-of-day idea, or a welcome for a brand-new
                      user. So even a user with NO history gets a
                      useful suggestion (no cold-start problem).

 Tasks that already repeat every day (repeat_daily = 1) are left out of
 the habit / set-once suggestions, because the user has already solved
 that one.
=====================================================================
"""

from collections import defaultdict
from datetime import datetime, timedelta


def _hour_label(hour_24: int) -> str:
    hour_12 = hour_24 % 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    return f"{hour_12} {'AM' if hour_24 < 12 else 'PM'}"


def _clock_label(dt: datetime) -> str:
    hour_12 = dt.hour % 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    return f"{hour_12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def _parse_when(reminder: dict) -> datetime | None:
    """Turns a reminder's date + time text into a datetime, or None
    (place-only reminders have no date/time)."""
    date_text = (reminder.get("date") or "").strip()
    time_text = (reminder.get("time") or "").strip()
    if not date_text or ":" not in time_text:
        return None
    try:
        return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _when_label(days_ago: int) -> str:
    if days_ago == 1:
        return "Yesterday"
    return f"{days_ago} days ago"


def _hours_of(reminders: list[dict]) -> list[int]:
    hours = []
    for r in reminders:
        time_text = (r.get("time") or "").strip()
        if ":" not in time_text:
            continue
        try:
            hours.append(int(time_text.split(":")[0]))
        except ValueError:
            continue
    return hours


def analyze_patterns(
    past_reminders: list[dict],
    nearby_object: str | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """
    Takes a list of the user's past reminders and returns a list of
    suggestion dicts: {"text": ..., "priority": "red"|"yellow"|"green"}.

    UPDATED Aug 24: optional `nearby_object` (the saved location the
    phone is near; detection happens on the phone).

    UPDATED Oct 27: place-only reminders (no time) no longer crash it,
    and the engine no longer NEEDS history: early habits (2 repeats),
    reminders coming up soon, nearby-place prompts and starter tips
    work even for a brand-new user. A task set only ONCE recently also
    gets a "set it again today?" suggestion. Done reminders and
    tasks that already repeat daily are skipped. `now` is only for
    testing.

    NOTE: matching is purely text-based (does the object name share a
    word with the task?) - a known Phase 1 limitation.
    """
    now = now or datetime.now()

    grouped_by_task = defaultdict(list)
    for reminder in past_reminders:
        task_key = reminder["task"].strip().lower()
        grouped_by_task[task_key].append(reminder)

    suggestions = []
    habit_tasks = set()  # tasks already covered by a habit suggestion

    # ---- 1 & 2: habits (strong = 3+ repeats, early = exactly 2) ----
    for task_key, reminders_for_task in grouped_by_task.items():
        # Already repeats every day - nothing to suggest.
        if any(r.get("repeat_daily") for r in reminders_for_task):
            continue

        hours = _hours_of(reminders_for_task)
        if len(hours) < 2:
            continue

        hour_counts = defaultdict(int)
        for hour in hours:
            hour_counts[hour] += 1

        most_common_hour = max(hour_counts, key=hour_counts.get)
        most_common_count = hour_counts[most_common_hour]
        consistency = most_common_count / len(hours)
        task_name = reminders_for_task[0]["task"]

        if len(hours) >= 3 and consistency >= 0.6 and most_common_count >= 3:
            if most_common_count >= 5:
                priority = "red"
            elif most_common_count >= 4:
                priority = "yellow"
            else:
                priority = "green"

            task_lower = task_name.lower()
            if nearby_object and (
                nearby_object.lower() in task_lower
                or task_lower in nearby_object.lower()
            ):
                priority = "red"
                text = (
                    f"You're near '{nearby_object}' and often set a "
                    f"reminder for '{task_name}' around "
                    f"{_hour_label(most_common_hour)}. Want to set one now?"
                )
            else:
                text = (
                    f"You often set a reminder for '{task_name}' around "
                    f"{_hour_label(most_common_hour)}. Want to set one now?"
                )
            suggestions.append({"text": text, "priority": priority})
            habit_tasks.add(task_key)

        elif most_common_count == 2 and len(hours) == 2:
            suggestions.append({
                "text": (
                    f"You've set '{task_name}' twice around "
                    f"{_hour_label(most_common_hour)}. Want to make it a "
                    f"daily habit?"
                ),
                "priority": "green",
            })
            habit_tasks.add(task_key)

    # ---- 3: set once recently, not set again today ----
    today = now.date()
    set_once = []
    for task_key, reminders_for_task in grouped_by_task.items():
        if task_key in habit_tasks:
            continue
        if any(r.get("repeat_daily") for r in reminders_for_task):
            continue
        whens = [w for w in (_parse_when(r) for r in reminders_for_task) if w]
        if not whens:
            continue
        latest = max(whens)
        if latest.date() >= today:
            continue  # already has one for today (or later)
        days_ago = (today - latest.date()).days
        if days_ago > 7:
            continue  # too old to be worth mentioning
        set_once.append((latest, days_ago, reminders_for_task[0]["task"]))
    set_once.sort(reverse=True)
    for latest, days_ago, task in set_once[:2]:
        suggestions.append({
            "text": (
                f"{_when_label(days_ago)} you set '{task}' at "
                f"{_clock_label(latest)}. Want to set it again today?"
            ),
            "priority": "green",
        })

    # ---- 4: reminders coming up in the next 24 hours ----
    upcoming = []
    for reminder in past_reminders:
        if reminder.get("completed"):
            continue  # already done - no need to mention it
        when = _parse_when(reminder)
        if when is not None and now <= when <= now + timedelta(hours=24):
            upcoming.append((when, reminder["task"]))
    upcoming.sort()
    for when, task in upcoming[:3]:
        minutes = int((when - now).total_seconds() // 60)
        if minutes <= 60:
            suggestions.append({
                "text": f"'{task}' is coming up at {_clock_label(when)} "
                        f"(in {max(minutes, 1)} min).",
                "priority": "red",
            })
        else:
            day = "today" if when.date() == now.date() else "tomorrow"
            suggestions.append({
                "text": f"You have '{task}' {day} at {_clock_label(when)}.",
                "priority": "yellow",
            })

    # ---- 5: nearby saved place ----
    if nearby_object:
        already_suggested = any(
            nearby_object.lower() in s["text"].lower() for s in suggestions
        )
        if not already_suggested:
            matched = False
            for reminder in past_reminders:
                task_lower = reminder["task"].lower()
                if (
                    nearby_object.lower() in task_lower
                    or task_lower in nearby_object.lower()
                ):
                    suggestions.append({
                        "text": (
                            f"You're near '{nearby_object}' — you have a "
                            f"reminder for '{reminder['task']}' saved. "
                            f"Want to check it now?"
                        ),
                        "priority": "green",
                    })
                    matched = True
                    break
            if not matched:
                suggestions.append({
                    "text": (
                        f"You're near '{nearby_object}'. Want to set a "
                        f"reminder or save a note about it?"
                    ),
                    "priority": "green",
                })

    # ---- 6: starter tips (so a new user is never left with nothing) ----
    if not suggestions:
        if not past_reminders:
            suggestions.append({
                "text": (
                    "Welcome! Add your first reminder with the + button, or "
                    "tell the chatbot: 'remind me to take medicine at 8 PM'."
                ),
                "priority": "green",
            })
        else:
            hour = now.hour
            if 5 <= hour < 12:
                tip = ("Good morning! Want to set a reminder for something "
                       "you need to do today?")
            elif 12 <= hour < 17:
                tip = ("Good afternoon! Anything you should remember for "
                       "this evening? Add a reminder now.")
            elif 17 <= hour < 22:
                tip = ("Good evening! Want to plan tomorrow by setting a "
                       "reminder now?")
            else:
                tip = ("Before you sleep, set a reminder for tomorrow "
                       "morning so you don't forget.")
            suggestions.append({"text": tip, "priority": "green"})

    order = {"red": 0, "yellow": 1, "green": 2}
    suggestions.sort(key=lambda s: order.get(s["priority"], 3))
    return suggestions


if __name__ == "__main__":
    fixed_now = datetime(2026, 10, 27, 17, 30)

    print("--- Strong habit + upcoming ---")
    fake_past_reminders = [
        {"task": "take medicine", "date": "2026-10-20", "time": "18:00"},
        {"task": "take medicine", "date": "2026-10-21", "time": "18:15"},
        {"task": "take medicine", "date": "2026-10-22", "time": "18:00"},
        {"task": "take medicine", "date": "2026-10-23", "time": "19:30"},
        {"task": "take medicine", "date": "2026-10-27", "time": "18:00"},
        {"task": "walk the dog", "date": "2026-10-12", "time": "07:00"},
        {"task": "buy groceries", "date": "", "time": ""},
    ]
    for s in analyze_patterns(fake_past_reminders, now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")

    print("--- Brand-new user (no history) ---")
    for s in analyze_patterns([], now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")

    print("--- Only 2 repeats ---")
    two = [
        {"task": "call mom", "date": "2026-10-10", "time": "20:00"},
        {"task": "call mom", "date": "2026-10-11", "time": "20:10"},
    ]
    for s in analyze_patterns(two, now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")

    print("--- Set once yesterday ---")
    once = [{"task": "take medicine", "date": "2026-10-26", "time": "18:00"}]
    for s in analyze_patterns(once, now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")

    print("--- Done reminder + daily repeat are skipped ---")
    skip = [
        {"task": "call mom", "date": "2026-10-27", "time": "18:00", "completed": 1},
        {"task": "take medicine", "date": "2026-10-26", "time": "18:00", "repeat_daily": 1},
    ]
    for s in analyze_patterns(skip, now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")

    print("--- Near a place, no history ---")
    for s in analyze_patterns([], nearby_object="pharmacy", now=fixed_now):
        print(f"  [{s['priority'].upper()}] {s['text']}")