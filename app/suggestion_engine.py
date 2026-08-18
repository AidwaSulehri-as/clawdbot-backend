"""
=====================================================================
 suggestion_engine.py — the "notice patterns in what the user does"
 logic. This is the brain behind Clawd Bot's proactive suggestions.

 IMPORTANT CONTEXT: today (Aug 16) we're only DESIGNING and WRITING
 this logic - it's not wired into the /suggestions API endpoint yet.
 That wiring happens on Aug 23, once Person B's app can actually send
 us the user's reminder history to analyze. Today, we write the
 function and test it with FAKE sample data to prove the logic works.

 THE IDEA IN PLAIN ENGLISH:
 If a user has set the same kind of reminder around the same time on
 several different days (e.g. "take medicine" around 6pm, 4 days out
 of the last 7), that's a PATTERN. We surface a suggestion like
 "You often set a reminder for this around this time - want one now?"

 This is NOT a trained machine learning model - it's simple counting
 and grouping (statistics), computed fresh every time. That's a
 completely legitimate design choice for Phase 1, and it's honest to
 describe as "pattern-based" rather than "AI/ML".
=====================================================================
"""

from collections import defaultdict
from datetime import datetime


def analyze_patterns(past_reminders: list[dict]) -> list[dict]:
    """
    Takes a list of the user's past reminders and looks for repeating
    patterns, returning a list of suggestion dicts.

    INPUT FORMAT - each item in past_reminders should look like:
        {
            "task": "take medicine",
            "date": "2026-08-10",
            "time": "18:00",
        }

    OUTPUT FORMAT - a list of dicts matching our Suggestion shape:
        {"text": "...", "priority": "green" | "yellow" | "red"}
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

            suggestions.append({
                "text": (
                    f"You often set a reminder for "
                    f"'{reminders_for_task[0]['task']}' around "
                    f"{hour_12} {am_pm}. Want to set one now?"
                ),
                "priority": priority,
            })

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