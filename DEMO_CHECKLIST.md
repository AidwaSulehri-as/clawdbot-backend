# Clawd Bot — Demo Day Checklist & Script (Backend)

## Before the demo (do this 15-20 minutes early)

**Important: ngrok's free tier session limits vary by version/plan and online reports conflict (some suggest a session may need refreshing after a few hours). Don't assume it will just stay up unattended — always restart server + ngrok fresh shortly before presenting, not hours in advance.**

1. **Start the backend server:**
   ```
   cd C:\Users\DELL\OneDrive\Desktop\clawdbot-backend
   venv\Scripts\activate.bat
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Wait for "Application startup complete."

2. **Start ngrok in a second window:**
   ```
   ngrok http 8000
   ```
   Confirm "Session Status: online" and note the Forwarding URL (should be `https://recede-nerd-sip.ngrok-free.dev` if the reserved subdomain is still active).

3. **Sanity check the URL works publicly:** open the ngrok URL + `/docs` in a browser on a DIFFERENT network (e.g. your phone on mobile data, not the same wifi) to confirm it's genuinely reachable from outside, not just localhost.

4. **Confirm the Flutter app points at the current URL.** Check `kBackendBaseUrl` in `chatbot_screen.dart` matches the URL from step 2 exactly.

5. **Do one live test message** through the actual app (not just /docs) — e.g. "remind me to test the demo" — to confirm the full chain (phone → ngrok → server → phone) works right before you present.

6. **Keep both terminal windows open and visible** for the rest of the demo. Do not close them, minimize is fine.

## If something goes wrong during the demo

- **ngrok URL not responding:** check both terminal windows are still open. If the ngrok tunnel dropped, restart it (`ngrok http 8000` again) — note this may give a NEW URL if your reserved subdomain isn't active; you'd need to update the app's URL and rebuild, which isn't fast — this is why the backup video (see below) matters.
- **Backend crashed:** check the server terminal for a Python traceback. Restart with the same `uvicorn` command. If you can't diagnose it live, fall back to the recorded demo video.
- **Always have the backup demo video ready to play** in case live networking fails during the actual presentation — judges/supervisors care about seeing the feature work, not necessarily live over a real network connection.

## Demo Script — What to Show and Say

### 1. Introduce the problem (30 seconds)
"Clawd Bot is a memory-assistance app for people with weak memory or mild cognitive impairment. Rather than a plain reminder app, it understands natural language, and proactively suggests reminders based on the user's own habits."

### 2. Show the chatbot creating a reminder (1 minute)
- Open the app, go to Chat.
- Type or speak: **"remind me to take my medicine at 6pm"**
- Point out: the reply confirms the extracted task, date, and time; a confirmation bubble shows it was actually saved.
- Switch to Memory or Dashboard screen — show the reminder is genuinely there, not just displayed in chat.

### 3. Show finding something (30 seconds)
- Type: **"where are my keys"** (assuming a "keys" object location was pre-saved before the demo — do this setup beforehand!)
- Point out: the bot searches the user's own saved data and responds with the actual saved location.

### 4. Show the suggestion engine (1 minute)
- Explain: "The system doesn't just react — it learns patterns from how the user actually behaves."
- Go to the Suggestions screen. If you've pre-seeded 3+ identical reminders before the demo (do this setup beforehand!), a real color-coded suggestion card should appear.
- If location is being demoed: mention the location-boost feature — being physically near a saved place bumps the suggestion's priority.

### 5. Show voice input (30 seconds)
- Tap the mic, speak a message, show it transcribing and the bot replying, optionally spoken back.
- **Do this on the real phone, not an emulator** — emulators have known microphone issues, tested and confirmed during development (worth mentioning if asked — shows real engineering judgment, not hiding a limitation).

### 6. Be ready for questions on:
- **Why not a trained ML model?** — Rule-based + pre-trained NLP libraries was a deliberate scope decision for the 19-day timeline; a genuine trained model needs a labeled dataset and training time outside this scope. This is documented in `BACKEND_MANUAL.md` as future work.
- **What bugs did you find during testing?** — Reference the QA sections in `BACKEND_MANUAL.md` (Sections 7-8) — several real bugs were caught and fixed through systematic testing, not left hidden.
- **Why ngrok instead of a real cloud deployment?** — A free-tier cloud host (Render) started requiring payment card details even on its free tier; ngrok avoided that risk for a student project while still providing a genuine public URL. Documented in `BACKEND_MANUAL.md` Section 6.

## Pre-demo data setup (do this the night before or morning of)

- [ ] Add a saved object location (e.g. "keys" → "kitchen counter") for the find_object demo.
- [ ] Create 3-4 identical reminders (e.g. "take medicine" at similar times on different days) so the Suggestions screen has something real to show.
- [ ] If demoing location-boosted suggestions, make sure the saved object name shares a word with the reminder task (e.g. object "medicine", task "buy medicine").
- [ ] Test the whole flow once, start to finish, the day before — not the morning of.
