"""
Scheduler service - runs scheduled scans in the background.
"""

import logging
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ScheduledScan
from app.services.scan_service import run_scan

logger = logging.getLogger(__name__)

_MIN_INTERVAL_HOURS = 1
_MAX_INTERVAL_HOURS = 168
_scheduler: Optional[BackgroundScheduler] = None


def _run_scheduled_scan(schedule_id: int, domain: str, user_id: int) -> None:
    """Execute a scheduled scan (called by APScheduler)."""
    db = SessionLocal()
    try:
        run_scan(domain, db, user_id=user_id)
        record = db.query(ScheduledScan).filter(ScheduledScan.id == schedule_id).first()
        if record:
            record.last_run_at = datetime.utcnow()
            db.commit()
    except Exception as exc:
        logger.warning("Scheduled scan %s for %s failed: %s", schedule_id, domain, exc)
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start scheduler and load jobs from DB."""
    scheduler = get_scheduler()
    if scheduler.running:
        return
    db = SessionLocal()
    try:
        records = db.query(ScheduledScan).filter(
            ScheduledScan.enabled.is_(True),
            ScheduledScan.user_id.isnot(None),
        ).all()
        for record in records:
            scheduler.add_job(
                _run_scheduled_scan,
                trigger=IntervalTrigger(hours=record.interval_hours),
                id=f"sched_{record.id}",
                args=[record.id, record.domain, record.user_id],
                replace_existing=True,
            )
        scheduler.start()
    finally:
        db.close()


def _clamp_interval(value: int) -> int:
    return max(_MIN_INTERVAL_HOURS, min(_MAX_INTERVAL_HOURS, int(value)))


def add_scheduled_scan(db: Session, user_id: int, domain: str, interval_hours: int = 24) -> ScheduledScan:
    """Add a new scheduled scan (requires user_id)."""
    record = ScheduledScan(
        user_id=user_id,
        domain=domain,
        interval_hours=_clamp_interval(interval_hours),
        enabled=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.add_job(
            _run_scheduled_scan,
            trigger=IntervalTrigger(hours=record.interval_hours),
            id=f"sched_{record.id}",
            args=[record.id, record.domain, record.user_id],
        )
    return record


def remove_scheduled_scan(db: Session, schedule_id: int, user_id: int) -> bool:
    """Remove a scheduled scan (only by its owner)."""
    record = db.query(ScheduledScan).filter(
        ScheduledScan.id == schedule_id, ScheduledScan.user_id == user_id
    ).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    scheduler = get_scheduler()
    if scheduler.running:
        try:
            scheduler.remove_job(f"sched_{schedule_id}")
        except Exception as exc:
            logger.debug("Job sched_%s already removed: %s", schedule_id, exc)
    return True


def update_scheduled_scan(
    db: Session,
    schedule_id: int,
    user_id: int,
    *,
    domain: Optional[str] = None,
    interval_hours: Optional[int] = None,
    enabled: Optional[bool] = None,
) -> Optional[ScheduledScan]:
    """Update fields and resync the APScheduler job (only by owner)."""
    record = db.query(ScheduledScan).filter(
        ScheduledScan.id == schedule_id, ScheduledScan.user_id == user_id
    ).first()
    if not record:
        return None
    if domain is not None:
        record.domain = domain
    if interval_hours is not None:
        record.interval_hours = _clamp_interval(interval_hours)
    if enabled is not None:
        record.enabled = enabled
    db.commit()
    db.refresh(record)

    scheduler = get_scheduler()
    if scheduler.running:
        try:
            scheduler.remove_job(f"sched_{schedule_id}")
        except Exception as exc:
            logger.debug("Job sched_%s not in scheduler: %s", schedule_id, exc)
        if record.enabled:
            scheduler.add_job(
                _run_scheduled_scan,
                trigger=IntervalTrigger(hours=record.interval_hours),
                id=f"sched_{record.id}",
                args=[record.id, record.domain, record.user_id],
            )
    return record


def toggle_scheduled_scan(db: Session, schedule_id: int, enabled: bool, user_id: int) -> Optional[ScheduledScan]:
    """Enable or disable a scheduled scan (only by owner)."""
    return update_scheduled_scan(db, schedule_id, user_id, enabled=enabled)


def list_scheduled_scans(db: Session, user_id: int) -> List[dict]:
    """List scheduled scans for ``user_id``."""
    records = (
        db.query(ScheduledScan)
        .filter(ScheduledScan.user_id == user_id)
        .order_by(ScheduledScan.created_at.desc())
        .all()
    )
    return [
        {
            "id": record.id,
            "domain": record.domain,
            "interval_hours": record.interval_hours,
            "enabled": record.enabled,
            "last_run_at": record.last_run_at.isoformat() if record.last_run_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]
