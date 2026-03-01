from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, func
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    timezone = Column(String, default="Europe/Moscow")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    events = relationship("Event", back_populates="user")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=True)
    recurrence = Column(String, nullable=True)  # например, cron-выражение
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="events")

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    sent = Column(Boolean, default=False)

class MessageLog(Base):
    __tablename__ = "message_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())