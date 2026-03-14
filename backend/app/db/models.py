"""
SQLAlchemy models for scan persistence and users.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User account for auth."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    email_notifications_enabled = Column(Boolean, default=False)  # Opt-in for change notifications
    created_at = Column(DateTime, default=datetime.utcnow)


class ScanRecord(Base):
    """Stored scan result. user_id is null for anonymous scans (not persisted)."""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(64), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=False)
    results = Column(Text, nullable=True)  # JSON string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduledScan(Base):
    """Scheduled scan job. Requires authenticated user."""

    __tablename__ = "scheduled_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(255), nullable=False)
    interval_hours = Column(Integer, nullable=False, default=24)  # Run every N hours
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Change notification from scan comparison. Linked to user and domain."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    scan_id = Column(String(64), nullable=True, index=True)  # New scan that triggered the change
    scan_id_prev = Column(String(64), nullable=True)  # Previous scan we compared to
    type = Column(String(50), nullable=False)  # ssl_expired, subdomain_added, port_opened, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)  # Structured diff data
    severity = Column(String(20), default="info")  # info, warning, critical
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Investigation(Base):
    """Investigation workspace (metadata). Graph stored in Neo4j."""

    __tablename__ = "investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    share_token = Column(String(36), unique=True, nullable=True, index=True)
    share_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
