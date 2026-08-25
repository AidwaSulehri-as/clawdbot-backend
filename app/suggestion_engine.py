"""
=====================================================================
 suggestion_engine.py — the "notice patterns in what the user does"
 logic. This is the brain behind Clawd Bot's proactive suggestions.

 This is NOT a trained machine learning model - it's simple counting
 and grouping (statistics), computed fresh every time.
=====================================================================
"""

from collections import defaultdict
from datetime import datetime


def analyze_patterns(
    past_reminders: list[dict],
    nearby_object: str | None = None,
) -> list[dict]:
    """
    Takes a list of the user's past reminders and looks for repeating
    patterns, returning a list of suggestion dicts.

    UPDATED Aug 24: added an optional `nearby_object` parameter. When
    the app detects the user is physically near a saved location
    (e.g. "pharmacy"), it can pass that object's name here. Location
    DETECTION happens entirely on the phone via geolocator - the
    backend just factors the match into suggestion priority.

    NOTE: matching is purely text-based (does the object name share a
    word with the task?). "medicine" matches task "buy medicine", but
    "pharmacy" would NOT match "buy medicine" since they share no
    words - a known Phase 1 limitation (no semantic understanding).
    """

    grouped_by_task = defaultdict(list)
    for reminder in past_reminders:
        task_key = reminder["task"].strip().lower()
        grouped_by_task[task_key].append(reminder)

    suggestions = []

    for task_key, reminders_for_task in grouped_by_task.items():

        if len(reminders_for_task) < 3:
            continue

        hours = [int(r["time"].split(":")[0]) for r in reminders_for_task]

        hour_counts = defaultdict(int)
        for hour in hours:
            hour_counts[hour] += 1

        most_common_hour = max(hour_counts, key=hour_counts.get)
        most_common_count = hour_counts[most_common_hour]

        consistency = most_common_count / len(reminders_for_task)

        if consistency >= 0.6 and most_common_count >= 3:
            if most_common_count >= 5:
                priority = "red"
            elif most_common_count >= 4:
                priority = "yellow"
            else:
                priority = "green"

            hour_12 = most_common_hour % 12
            hour_12 = 12 if hour_12 == 0 else hour_12
            am_pm = "AM" if most_common_hour < 12 else "PM"

            task_lower = reminders_for_task[0]["task"].lower()
            if nearby_object and (
                nearby_object.lower() in task_lower
                or task_lower in nearby_object.lower()
            ):
                priority = "red"
                suggestion_text = (
                    f"You're near '{nearby_object}' and often set a "
                    f"reminder for '{reminders_for_task[0]['task']}' "
                    f"around {hour_12} {am_pm}. Want to set one now?"
                )
            else:
                suggestion_text = (
                    f"You often set a reminder for "
                    f"'{reminders_for_task[0]['task']}' around "
                    f"{hour_12} {am_pm}. Want to set one now?"
                )

            suggestions.append({
                "text": suggestion_text,
                "priority": priority,
            })

    if nearby_object:
        already_suggested = any(
            nearby_object.lower() in s["text"].lower() for s in suggestions
        )
        if not already_suggested:
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
                    break

    return suggestions


if __name__ == "__main__":
    fake_past_reminders = [
        {"task": "take medicine", "date": "2026-08-10", "time": "18:00"},
        {"task": "take medicine", "date": "2026-08-11", "time": "18:15"},
        {"task": "take medicine", "date": "2026-08-12", "time": "18:00"},
        {"task": "take medicine", "date": "2026-08-13", "time": "19:30"},
        {"task": "take medicine", "date": "2026-08-14", "time": "18:00"},
        {"task": "walk the dog", "date": "2026-08-12", "time": "07:00"},
        {"task": "buy groceries", "date": "2026-08-05", "time": "10:00"},
    ]

    results = analyze_patterns(fake_past_reminders)

    print("Suggestions found:")
    for s in results:
        print(f"  [{s['priority'].upper()}] {s['text']}")

    if not results:
        print("  (none - not enough repeating patterns in this fake data)")