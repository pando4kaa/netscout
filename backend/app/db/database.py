"""
Database connection and session.
PostgreSQL only. DATABASE_URL in .env (default matches docker compose).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from src.config.settings import DATABASE_URL
from .models import Base


def _get_engine_url() -> str:
    """Return PostgreSQL URL with psycopg2 driver."""
    url = DATABASE_URL.strip()
    if not url:
        raise ValueError("DATABASE_URL is required. Set it in .env (e.g. postgresql://netscout:netscout@localhost:5432/netscout)")
    if "postgresql://" in url and "postgresql+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


engine = create_engine(
    _get_engine_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},  # Fail fast if PostgreSQL is down
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create tables and run migrations for new columns."""
    Base.metadata.create_all(bind=engine)
    # Migration: add columns if missing (for existing DBs)
    for stmt in [
        "ALTER TABLE scans ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE scheduled_scans ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS share_token VARCHAR(36)",
        "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS share_expires_at TIMESTAMP",
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass  # Column may already exist or table structure differs


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
