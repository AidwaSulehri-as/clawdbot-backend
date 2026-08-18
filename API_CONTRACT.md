# Clawd Bot API Contract (v0.2 - Aug 19)

Base URL (local dev): http://localhost:8000
(Android emulator note: use http://10.0.2.2:8000 instead of localhost to reach your laptop's server from the emulator.)

## POST /chat
Request: { "message": "remind me to take medicine at 6pm", "user_id": "default" }
Response: { "reply": "...", "action": { "action": "create_reminder", "data": { "task": "...", "date": "YYYY-MM-DD", "time": "HH:MM", "priority": "yellow" } } }

action is null if no action is needed (general conversation).

action.action can be one of:
- create_reminder — data: { task, date, time, priority }
- find_object — data: { query } — app should search its local object_locations table for this query
- find_note — data: { query } — app should search its local notes table for this query
- list_tasks — data: {} — app should display today's/upcoming reminders from its local database
- none — just conversation, no action needed

## POST /parse_reminder
Request: { "text": "remind me to take medicine tomorrow at 6pm" }
Response: { "task": "...", "date": "YYYY-MM-DD", "time": "HH:MM", "confidence": 0.0 }

## GET /suggestions?user_id=default
Response: { "suggestions": [ { "text": "...", "priority": "green" } ] }
priority is one of green | yellow | red.
STILL A STUB as of Aug 19 - real logic wires in Aug 23.

## Notes for Person B
- All dates are ISO format (YYYY-MM-DD), all times are 24-hour (HH:MM).
- As of Aug 19: /chat and /parse_reminder are REAL (not stubs). /suggestions is still a stub.
- For find_object/find_note/list_tasks actions: the backend does NOT have access to your local data. It only recognizes the user's intent and sends back a "query" - your app must do the actual local database search/lookup and display the result.