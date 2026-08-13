# Clawd Bot API Contract (v0.1 - Aug 13)

Base URL (local dev): http://localhost:8000
(Android emulator note: use http://10.0.2.2:8000 instead of localhost to reach your laptop's server from the emulator.)

## POST /chat
Request: { "message": "remind me to take medicine at 6pm", "user_id": "default" }
Response: { "reply": "...", "action": { "action": "create_reminder", "data": { "task": "...", "date": "YYYY-MM-DD", "time": "HH:MM", "priority": "yellow" } } }
action is null if no action is needed.

## POST /parse_reminder
Request: { "text": "remind me to take medicine tomorrow at 6pm" }
Response: { "task": "...", "date": "YYYY-MM-DD", "time": "HH:MM", "confidence": 0.0 }

## GET /suggestions?user_id=default
Response: { "suggestions": [ { "text": "...", "priority": "green" } ] }
priority is one of green | yellow | red.

All endpoints are currently stubbed with fixed sample data. Build the Flutter UI against these exact shapes now - real logic replaces the stub values over the next few days, but the shape won't change.