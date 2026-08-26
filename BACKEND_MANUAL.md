# Clawd Bot — Backend Manual

This document covers the backend service that powers Clawd Bot's chatbot, reminder parsing, and suggestion features. It's written for inclusion in the final project manual/report.

## 1. Overview

The backend is a Python service built with **FastAPI** that provides three capabilities to the Clawd Bot mobile app:

1. **Natural language reminder parsing** — extracts a task, date, and time from free text like "remind me to take medicine tomorrow at 6pm."
2. **Conversational chatbot** — recognizes user intent (create a reminder, find a saved object, find a note, list tasks, or general conversation) and responds accordingly.
3. **Context-aware suggestions** — analyzes the user's own reminder history for repeating patterns and proactively suggests reminders, optionally factoring in the user's physical location.

The backend does **not** use a trained machine learning model. Intent recognition and suggestion logic are built on pre-trained NLP libraries (spaCy's language model, `dateparser`) combined with rule-based logic that the team designed and implemented. This is a deliberate, documented Phase 1 scope decision — a genuine trained ML pipeline would require a labeled dataset and training time outside this project's 19-day sprint window (see Section 5, Known Limitations).

## 2. Technology Stack

| Component | Technology |
|---|---|
| Web framework | FastAPI |
| Server | Uvicorn |
| Data validation | Pydantic |
| Date/time extraction | `dateparser` |
| NLP support | spaCy (installed, available for future intent-recognition upgrades) |
| Deployment (development) | ngrok tunnel to a locally-run server |
| Version control | Git / GitHub |

## 3. Project Structure

```
clawdbot-backend/
├── app/
│   ├── main.py              # FastAPI app and route definitions
│   ├── models.py             # Pydantic request/response schemas (the API contract)
│   ├── nlp_utils.py          # Reminder text parsing (task/date/time extraction)
│   ├── chat_engine.py        # Chatbot intent recognition and response generation
│   └── suggestion_engine.py  # Pattern-detection logic for proactive suggestions
├── requirements.txt          # Python dependencies
├── API_CONTRACT.md           # Full API reference for the mobile app team
├── README.md                 # Setup and run instructions
└── BACKEND_MANUAL.md         # This document
```

## 4. API Endpoints

### `GET /`
Health check. Returns `{"status": "ok", "service": "clawd-bot-backend"}`. Used to confirm the server is reachable.

### `POST /chat`
The core chatbot endpoint. Accepts a user's message (typed or transcribed from voice) and returns a natural-language reply plus an optional structured "action" instructing the mobile app to create a reminder, search for an object or note, or list tasks. Full request/response format is documented in `API_CONTRACT.md`.

Intent recognition works via keyword matching across five categories, checked in a specific priority order: read-only intents (list tasks, find object, find note) are checked **before** the data-writing intent (create reminder). This ordering was a deliberate fix made during QA (Aug 20/22) after discovering that ambiguous phrasing could otherwise cause the system to silently create incorrect reminder data — read-only intents are the safe default when the system isn't sure.

### `POST /parse_reminder`
Takes free text and extracts a structured task, date, and time using the `dateparser` library combined with custom filtering logic. Used both directly and internally by `/chat` when a reminder-creation intent is detected.

### `POST /suggestions`
Takes the user's reminder history (sent by the app, since that data lives in the phone's local database) and returns a list of proactive suggestions based on detected patterns — for example, noticing that the user sets a "take medicine" reminder around 6pm most days. Optionally accepts a `nearby_object` field, populated when the app's on-device location check detects the user is near a saved location; this factors into suggestion priority (see Section 4.1).

Suggestions are generated fresh on every request using simple statistical rules (frequency counts, consistency percentages) — not a cached or pre-trained model.

#### 4.1 Location-Aware Suggestions
When `nearby_object` is provided, the suggestion engine checks whether the object's name shares a word with any pattern-matched reminder's task text. If it does, the suggestion's priority is escalated (the combination of an established habit and being physically at the relevant location is treated as a strong signal). This matching is **text-based only** — it checks for shared words, not semantic meaning. See Section 5 for the specific limitation this creates.

## 5. Known Limitations

These are documented deliberately, as part of an honest account of Phase 1 scope decisions rather than hidden gaps:

- **Vague relative time phrases** ("next week," "soon") are not reliably detected by the date parser. Specific phrases ("tomorrow," "Friday," "6pm," "next Monday") work reliably. This is a limitation of the underlying `dateparser` library's handling of ambiguous relative periods.
- **Location matching is text-based, not semantic.** A saved location named "medicine" will correctly match a reminder task "buy medicine," but a location named "pharmacy" will not, since the two share no words. True semantic matching would require a different NLP approach beyond Phase 1 scope.
- **Intent recognition is rule-based, not a trained model.** This was a deliberate scope decision given the project timeline, and is discussed further in the project's proposal and SRS documentation under "Future Work."
- **No user accounts or authentication.** The backend currently serves a single implicit user (`user_id: "default"`); multi-user support is scoped as future work.
- **Development deployment via ngrok**, not a permanent cloud host. This was a pragmatic choice during development (see Section 6) and should be revisited for any production deployment.

## 6. Deployment Notes

During development, the backend was run locally and exposed to the internet via an ngrok tunnel, rather than deployed to a permanent cloud host. This decision was made after evaluating free-tier cloud hosting options (e.g., Render) that began requiring payment card details even on their free tier — a risk the team chose to avoid for a student project. ngrok provided a genuine public HTTPS URL reachable by the mobile app without that requirement, at the cost of requiring the development machine to stay on and both the server and tunnel processes running during testing/demo sessions.

For any future production deployment, a proper cloud host with persistent uptime (rather than a developer's own machine) would be the appropriate next step.

## 7. Testing Approach

The backend was tested primarily through FastAPI's automatically generated interactive documentation (`/docs`), which allowed manual testing of each endpoint with a range of realistic and edge-case inputs (empty strings, ambiguous phrasing, garbled repeated words, and varied natural phrasings of the same intent). Several real bugs were identified and fixed this way during dedicated QA sessions, including:

- Filler-phrase stripping only working when the trigger phrase appeared at the very start of a message, rather than anywhere within it.
- Overly broad keyword matching causing the word "reminders" (a question) to be misclassified as a command to create a reminder.
- Naive substring matching causing unrelated words like "anything" to be misidentified as the greeting "hi."

Each of these was caught through systematic manual testing rather than found in production, and each fix was verified with both the failing case and a regression check against normal, previously-working inputs before being committed.
## 8. Additional Bugs Found During Extended Smoke Testing (Aug 26)
 A broader round of endpoint testing surfaced two related but distinct bugs in the date/time extraction logic, both involving qualifier words ("next," "this," "coming," etc.) placed immediately before a weekday name: 1. **Qualifier word dropped in the main parsing path.** Input like "next Monday at 2pm" correctly computed the right date, but the word "next" was left dangling in the extracted task text. Root cause: the code attempted to re-parse the combined phrase "next Monday at 2pm" to recompute the date, but dateparser.parse() failed on that exact combined string even though the original phrase ("Monday at 2pm") had parsed correctly on its own. The failed re-parse silently discarded the qualifier-extended phrase and fell back to the original, unextended one. The fix decouples date calculation from text removal: the already-correct date is preserved regardless of whether the extended phrase can be re-parsed, and the extension is used purely for cleanly removing text from the task. 2. **Qualifier word dropped in the single-keyword fallback path.** A related but separate case: input like "coming Tuesday" caused dateparser's phrase search to match only noise ("to," "on") rather than "Tuesday" itself, so the code fell back to its single-keyword scanner. However, this fallback path had not been updated with the same qualifier-extension logic as the main path, so "coming" was left behind the same way "next" had been. The fix applies the identical qualifier-extension logic to this second code path. Both fixes were verified against the specific failing case and against multiple other qualifier words ("this," "coming") and against previously-passing inputs, to confirm the fix generalized correctly without introducing regressions.

 ## 9. Input Validation Robustness
  All three endpoints were explicitly tested against malformed requests — missing required fields, wrong data types, and incomplete nested objects — to confirm the API fails safely rather than crashing. In every case, FastAPI's automatic Pydantic-based validation correctly rejected the request with a specific 422 Unprocessable Entity response identifying exactly which field was invalid and why, rather than a raw server error. This confirms the API is robust against malformed input from the mobile app, a future client, or unexpected edge cases during a live demo.