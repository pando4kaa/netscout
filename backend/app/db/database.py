"""
Database connection and session.

PostgreSQL only. `DATABASE_URL` is read from `.env`
(default in docker-compose.yml).
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import DATABASE_URL

from .models import Base

logger = logging.getLogger(__name__)


def _get_engine_url() -> str:
    """Return PostgreSQL URL with the explicit psycopg2 driver suffix."""
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is required. Set it in .env "
            "(e.g. postgresql://netscout:netscout@localhost:5432/netscout)"
        )
    url = DATABASE_URL.strip()
    if "postgresql://" in url and "postgresql+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


engine = create_engine(
    _get_engine_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},  # fail fast if PostgreSQL is down
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Lightweight ad-hoc schema migrations executed on startup. They are
# idempotent (`IF NOT EXISTS`) so safe to re-run; once Alembic is wired
# up, this block should be removed.
_INLINE_MIGRATIONS = (
    "ALTER TABLE scans ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
    "ALTER TABLE scheduled_scans ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
    "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS share_token VARCHAR(36)",
    "ALTER TABLE investigations ADD COLUMN IF NOT EXISTS share_expires_at TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT FALSE",
)

_NOTIFICATIONS_DDL = """
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        domain VARCHAR(255) NOT NULL,
        scan_id VARCHAR(64),
        scan_id_prev VARCHAR(64),
        type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        message TEXT,
        details JSONB,
        severity VARCHAR(20) DEFAULT 'info',
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW()
    )
"""


def init_db() -> None:
    """Create ORM tables and run inline schema migrations."""
    Base.metadata.create_all(bind=engine)

    for stmt in _INLINE_MIGRATIONS:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Inline migration failed (%s): %s", stmt[:60], exc)

    try:
        with engine.begin() as conn:
            conn.execute(text(_NOTIFICATIONS_DDL))
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_notifications_domain ON notifications(domain)")
            )
    except Exception as exc:
        logger.warning("notifications DDL failed: %s", exc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a SQLAlchemy session and close it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
