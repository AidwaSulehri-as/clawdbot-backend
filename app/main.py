from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import (
    ChatRequest, ChatResponse, ParseReminderRequest, ParseReminderResponse,
    SuggestionsRequest, SuggestionsResponse, Suggestion, ReminderAction,
    SignupRequest, SignupResponse, LoginRequest, TokenResponse, UserResponse,
    ReminderCreate, ReminderResponse,
    NoteCreate, NoteResponse,
    ObjectLocationCreate, ObjectLocationResponse,
    SyncRequest, SyncResponse,
)
from app.nlp_utils import extract_reminder
from app.chat_engine import handle_chat
from app.suggestion_engine import analyze_patterns
from app.database import get_db, Base, engine
from app import db_models
from app.db_models import User, Reminder, Note, ObjectLocation
from app.auth_utils import (
    hash_password, verify_password, create_access_token, get_current_user_email,
    is_locked_out, record_failed_attempt, clear_failed_attempts, LOCKOUT_MINUTES,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Clawd Bot Backend", description="Backend for Clawd Bot FYP", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "clawd-bot-backend"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user_email: str = Depends(get_current_user_email)):
    result = handle_chat(request.message)
    return ChatResponse(**result)


@app.post("/parse_reminder", response_model=ParseReminderResponse)
def parse_reminder(request: ParseReminderRequest):
    result = extract_reminder(request.text)
    return ParseReminderResponse(**result)


@app.post("/suggestions", response_model=SuggestionsResponse)
def suggestions(request: SuggestionsRequest, current_user_email: str = Depends(get_current_user_email)):
    history_as_dicts = [{"task": i.task, "date": i.date, "time": i.time} for i in request.reminder_history]
    results = analyze_patterns(history_as_dicts, nearby_object=request.nearby_object)
    return SuggestionsResponse(suggestions=[Suggestion(**s) for s in results])


# =====================================================================
# AUTH ENDPOINTS
# =====================================================================

@app.post("/auth/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
    new_user = User(email=request.email, hashed_password=hash_password(request.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return SignupResponse(email=new_user.email)


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    if is_locked_out(request.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again in {LOCKOUT_MINUTES} minutes.",
        )
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        record_failed_attempt(request.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    clear_failed_attempts(request.email)
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse(id=user.id, email=user.email)


# ---------------------------------------------------------------
# Small helper - every endpoint below needs the numeric user id,
# not just the email, to filter rows by user_id. This looks up
# the logged-in user's row and returns it (or 404s if somehow
# missing, which should never normally happen).
# ---------------------------------------------------------------
def get_current_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


# =====================================================================
# REMINDER ENDPOINTS
# =====================================================================

@app.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    request: ReminderCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    new_reminder = Reminder(
        user_id=user.id,
        task=request.task,
        date=request.date,
        time=request.time,
        priority=request.priority,
        completed=request.completed,
        category=request.category,
    )
    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)
    return ReminderResponse(
        id=new_reminder.id,
        task=new_reminder.task,
        date=new_reminder.date,
        time=new_reminder.time,
        priority=new_reminder.priority,
        completed=new_reminder.completed,
        category=new_reminder.category,
        last_modified=new_reminder.last_modified.isoformat(),
    )


@app.get("/reminders", response_model=list[ReminderResponse])
def list_reminders(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    reminders = db.query(Reminder).filter(Reminder.user_id == user.id).order_by(Reminder.id.desc()).all()
    return [
        ReminderResponse(
            id=r.id,
            task=r.task,
            date=r.date,
            time=r.time,
            priority=r.priority,
            completed=r.completed,
            category=r.category,
            last_modified=r.last_modified.isoformat(),
        )
        for r in reminders
    ]


# =====================================================================
# NOTE ENDPOINTS
# =====================================================================

@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    request: NoteCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    new_note = Note(
        user_id=user.id,
        title=request.title,
        content=request.content,
        created_at=request.created_at,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return NoteResponse(
        id=new_note.id,
        title=new_note.title,
        content=new_note.content,
        created_at=new_note.created_at,
        last_modified=new_note.last_modified.isoformat(),
    )


@app.get("/notes", response_model=list[NoteResponse])
def list_notes(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    notes = db.query(Note).filter(Note.user_id == user.id).order_by(Note.id.desc()).all()
    return [
        NoteResponse(
            id=n.id,
            title=n.title,
            content=n.content,
            created_at=n.created_at,
            last_modified=n.last_modified.isoformat(),
        )
        for n in notes
    ]


# =====================================================================
# OBJECT LOCATION ENDPOINTS
# =====================================================================

@app.post("/object_locations", response_model=ObjectLocationResponse, status_code=status.HTTP_201_CREATED)
def create_object_location(
    request: ObjectLocationCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    new_location = ObjectLocation(
        user_id=user.id,
        object_name=request.object_name,
        location_name=request.location_name,
        latitude=request.latitude,
        longitude=request.longitude,
    )
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return ObjectLocationResponse(
        id=new_location.id,
        object_name=new_location.object_name,
        location_name=new_location.location_name,
        latitude=new_location.latitude,
        longitude=new_location.longitude,
        last_modified=new_location.last_modified.isoformat(),
    )


@app.get("/object_locations", response_model=list[ObjectLocationResponse])
def list_object_locations(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    locations = db.query(ObjectLocation).filter(ObjectLocation.user_id == user.id).order_by(ObjectLocation.id.desc()).all()
    return [
        ObjectLocationResponse(
            id=l.id,
            object_name=l.object_name,
            location_name=l.location_name,
            latitude=l.latitude,
            longitude=l.longitude,
            last_modified=l.last_modified.isoformat(),
        )
        for l in locations
    ]


# =====================================================================
# REMINDER — UPDATE & DELETE
# =====================================================================

@app.put("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: int,
    request: ReminderCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user.id)
        .first()
    )
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")

    reminder.task = request.task
    reminder.date = request.date
    reminder.time = request.time
    reminder.priority = request.priority
    reminder.completed = request.completed
    reminder.category = request.category
    # last_modified updates automatically (onupdate=datetime.utcnow in db_models.py)

    db.commit()
    db.refresh(reminder)
    return ReminderResponse(
        id=reminder.id,
        task=reminder.task,
        date=reminder.date,
        time=reminder.time,
        priority=reminder.priority,
        completed=reminder.completed,
        category=reminder.category,
        last_modified=reminder.last_modified.isoformat(),
    )


@app.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user.id)
        .first()
    )
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    db.delete(reminder)
    db.commit()
    return None


# =====================================================================
# NOTE — UPDATE & DELETE
# =====================================================================

@app.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    request: NoteCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == user.id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")

    note.title = request.title
    note.content = request.content
    note.created_at = request.created_at

    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        last_modified=note.last_modified.isoformat(),
    )


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == user.id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    db.delete(note)
    db.commit()
    return None


# =====================================================================
# OBJECT LOCATION — UPDATE & DELETE
# =====================================================================

@app.put("/object_locations/{location_id}", response_model=ObjectLocationResponse)
def update_object_location(
    location_id: int,
    request: ObjectLocationCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    location = (
        db.query(ObjectLocation)
        .filter(ObjectLocation.id == location_id, ObjectLocation.user_id == user.id)
        .first()
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object location not found.")

    location.object_name = request.object_name
    location.location_name = request.location_name
    location.latitude = request.latitude
    location.longitude = request.longitude

    db.commit()
    db.refresh(location)
    return ObjectLocationResponse(
        id=location.id,
        object_name=location.object_name,
        location_name=location.location_name,
        latitude=location.latitude,
        longitude=location.longitude,
        last_modified=location.last_modified.isoformat(),
    )


@app.delete("/object_locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object_location(
    location_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)
    location = (
        db.query(ObjectLocation)
        .filter(ObjectLocation.id == location_id, ObjectLocation.user_id == user.id)
        .first()
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object location not found.")
    db.delete(location)
    db.commit()
    return None


# ---------------------------------------------------------------
# NEW Sep 28: helper for conflict resolution. Parses the phone's
# ISO-format last_modified string into a real datetime so it can be
# compared against the server's own last_modified. If parsing fails
# or the phone didn't send one, returns None - callers treat that as
# "no timestamp info, apply the update anyway" (old behaviour).
# ---------------------------------------------------------------
def _parse_client_timestamp(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# =====================================================================
# SYNC ENDPOINT
# =====================================================================
# UPDATED Sep 28: CONFLICT RESOLUTION ("server wins on stale write").
#
# The phone sends its full local list. For each item WITH an id that
# already exists on the server:
#   - if the phone's last_modified is NEWER than the server's copy,
#     the phone's version is accepted and overwrites the server's.
#   - if the server's copy is the SAME AGE OR NEWER, the phone's
#     update is REJECTED (silently skipped) - the server's existing
#     version is kept as-is, since it's already at least as new.
# This protects against an old, stale edit (e.g. from a phone that
# was offline for a while) accidentally overwriting a newer edit that
# already reached the server from another device.
#
# Items with no id (brand new, never synced before) are always
# inserted - there's nothing to conflict with yet.
# =====================================================================

@app.post("/sync", response_model=SyncResponse)
def sync_data(
    request: SyncRequest,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = get_current_user(db, current_user_email)

    # ---- REMINDERS ----
    for item in request.reminders:
        existing = None
        if item.id is not None:
            existing = (
                db.query(Reminder)
                .filter(Reminder.id == item.id, Reminder.user_id == user.id)
                .first()
            )
        if existing is not None:
            incoming_time = _parse_client_timestamp(item.last_modified)
            if incoming_time is not None and incoming_time <= existing.last_modified:
                # Server's copy is already as new or newer - reject
                # this stale update and keep the server's version.
                continue
            existing.task = item.task
            existing.date = item.date
            existing.time = item.time
            existing.priority = item.priority
            existing.completed = item.completed
            existing.category = item.category
        else:
            db.add(Reminder(
                user_id=user.id,
                task=item.task,
                date=item.date,
                time=item.time,
                priority=item.priority,
                completed=item.completed,
                category=item.category,
            ))

    # ---- NOTES ----
    for item in request.notes:
        existing = None
        if item.id is not None:
            existing = (
                db.query(Note)
                .filter(Note.id == item.id, Note.user_id == user.id)
                .first()
            )
        if existing is not None:
            incoming_time = _parse_client_timestamp(item.last_modified)
            if incoming_time is not None and incoming_time <= existing.last_modified:
                continue
            existing.title = item.title
            existing.content = item.content
            existing.created_at = item.created_at
        else:
            db.add(Note(
                user_id=user.id,
                title=item.title,
                content=item.content,
                created_at=item.created_at,
            ))

    # ---- OBJECT LOCATIONS ----
    for item in request.object_locations:
        existing = None
        if item.id is not None:
            existing = (
                db.query(ObjectLocation)
                .filter(ObjectLocation.id == item.id, ObjectLocation.user_id == user.id)
                .first()
            )
        if existing is not None:
            incoming_time = _parse_client_timestamp(item.last_modified)
            if incoming_time is not None and incoming_time <= existing.last_modified:
                continue
            existing.object_name = item.object_name
            existing.location_name = item.location_name
            existing.latitude = item.latitude
            existing.longitude = item.longitude
        else:
            db.add(ObjectLocation(
                user_id=user.id,
                object_name=item.object_name,
                location_name=item.location_name,
                latitude=item.latitude,
                longitude=item.longitude,
            ))

    db.commit()

    # ---- Build the full, up-to-date response ----
    final_reminders = db.query(Reminder).filter(Reminder.user_id == user.id).order_by(Reminder.id.desc()).all()
    final_notes = db.query(Note).filter(Note.user_id == user.id).order_by(Note.id.desc()).all()
    final_locations = db.query(ObjectLocation).filter(ObjectLocation.user_id == user.id).order_by(ObjectLocation.id.desc()).all()

    return SyncResponse(
        reminders=[
            ReminderResponse(
                id=r.id, task=r.task, date=r.date, time=r.time,
                priority=r.priority, completed=r.completed, category=r.category,
                last_modified=r.last_modified.isoformat(),
            )
            for r in final_reminders
        ],
        notes=[
            NoteResponse(
                id=n.id, title=n.title, content=n.content,
                created_at=n.created_at, last_modified=n.last_modified.isoformat(),
            )
            for n in final_notes
        ],
        object_locations=[
            ObjectLocationResponse(
                id=l.id, object_name=l.object_name, location_name=l.location_name,
                latitude=l.latitude, longitude=l.longitude,
                last_modified=l.last_modified.isoformat(),
            )
            for l in final_locations
        ],
    )