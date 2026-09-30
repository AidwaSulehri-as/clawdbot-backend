"""
=====================================================================
 db_models.py — the actual DATABASE TABLE definitions (SQLAlchemy).
=====================================================================
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    reminders = relationship("Reminder", back_populates="owner")
    notes = relationship("Note", back_populates="owner")
    object_locations = relationship("ObjectLocation", back_populates="owner")
    context_logs = relationship("ContextLog", back_populates="owner")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task = Column(String, nullable=False)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="green")
    completed = Column(Integer, nullable=False, default=0)
    category = Column(String, nullable=True)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="reminders")


class Note(Base):
    __tablename__ = "cloud_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="notes")


class ObjectLocation(Base):
    __tablename__ = "object_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    object_name = Column(String, nullable=False)
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="object_locations")


class ContextLog(Base):
    __tablename__ = "context_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="context_logs")