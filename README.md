# Clawd Bot Backend

FastAPI service for the Clawd Bot mobile app - handles NLP chatbot,
reminder text parsing, and context-aware suggestions.

## Setup

```bash
cd clawdbot-backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/docs in a browser to test each endpoint.

## Project structure
clawdbot-backend/
├── app/
│ ├── init.py
│ ├── main.py # FastAPI app + route definitions
│ ├── models.py # Pydantic request/response models (the API contract)
│ ├── nlp_utils.py # Reminder text parsing logic (task/date/time extraction)
│ └── suggestion_engine.py # Pattern-based suggestion logic
├── requirements.txt
├── API_CONTRACT.md
└── README.md

## Known Limitations (Phase 1)

- Vague relative time phrases ("next week", "soon") are not reliably detected by the date parser. Specific phrases ("tomorrow", "Friday", "6pm", "next Monday") work reliably.
- This is a limitation of the underlying dateparser library's handling of ambiguous relative periods, documented here rather than left as a silent bug.